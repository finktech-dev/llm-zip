import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from llmzip.i18n import t
from llmzip.config.loader import load
from llmzip.core.lingua_adapter import LinguaAdapter
from llmzip.core.savings_calculator import calculate_savings
from llmzip.core.semantic_scorer import SemanticScorer
from llmzip.core.token_counter import count_tokens
from llmzip.core.featured_models import FEATURED_MODELS
from llmzip.pricing.fallback import FALLBACK_PRICES

logger = logging.getLogger(__name__)


def _load_models(config) -> tuple[LinguaAdapter, SemanticScorer]:
    models_dir = Path("models")
    lingua = LinguaAdapter(
        model_name=config.compression_model,
        models_dir=models_dir,
        chunk_size=config.chunk_size,
    )
    lingua.load()
    scorer = SemanticScorer(models_dir=models_dir, model_id=config.scorer_model)
    scorer.load()
    return lingua, scorer


def _read_input(source: Path | None) -> str:
    if source is not None:
        return source.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    typer.echo(t("compress.error.no_input"), err=True)
    raise typer.Exit(code=2)


def _maybe_convert(text: str, source: Path | None, config) -> str:
    if source is None:
        return text
    suffix = source.suffix.lower()
    from llmzip.conversion.file_converter import SUPPORTED_EXTENSIONS
    if suffix not in SUPPORTED_EXTENSIONS or suffix == ".txt":
        return text
    if not config.file_conversion_enabled:
        typer.echo(t("compress.warning.conversion_disabled"), err=True)
        return text
    from llmzip.conversion.file_converter import convert
    result = convert(source)
    if result.warning:
        typer.echo(t("compress.warning.generic", warning=result.warning), err=True)
    
    if not result.text or len(result.text.strip()) < 10:
        typer.echo("File conversion produced no extractable text.", err=True)
        raise typer.Exit(code=2)
        
    return result.text


def compress(
    source: Optional[Path] = typer.Argument(
        default=None,
        help="File to compress. Omit to read from stdin.",
    ),
    ratio: Optional[float] = typer.Option(
        None, "--ratio", "-r", min=0.1, max=0.9,
        help="Compression ratio (0.1–0.9).",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Target model for savings estimation.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Write compressed text to file instead of stdout.",
    ),
    json_output: bool = typer.Option(
        False, "--json",
        help="Output full JSON response including metrics.",
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Fill missing arguments interactively with arrow keys.",
    ),
) -> None:
    config = load()

    if interactive:
        source, ratio, model, output = _fill_interactively(source, ratio, model, output)

    ratio = ratio if ratio is not None else config.default_ratio
    model = model if model is not None else config.default_model

    lingua, scorer = _load_models(config)

    raw = _read_input(source)
    text = _maybe_convert(raw, source, config)

    original_tokens, accuracy = count_tokens(text, model)

    if original_tokens > config.max_tokens:
        typer.echo(
            t("compress.error.above_max_tokens",
              max_tokens=config.max_tokens, tokens=original_tokens),
            err=True,
        )
        raise typer.Exit(code=2)

    if original_tokens < config.min_tokens_to_compress:
        if not json_output:
            typer.echo(
                f"⚠ Skipped: text has {original_tokens:,} tokens, "
                f"below MIN_TOKENS_TO_COMPRESS. Returning original text.",
                err=True,
            )
        _write_output(text, output)
        raise typer.Exit(code=0)

    result = lingua.compress(text, ratio, model)
    score = scorer.score(text, result.compressed_text)
    savings = calculate_savings(text, result.compressed_text, model)

    if result.warning:
        typer.echo(t("compress.warning.generic", warning=result.warning), err=True)

    if not json_output:
        typer.echo(
            t("compress.metrics",
              original=result.original_tokens,
              compressed=result.compressed_tokens,
              ratio=result.compression_ratio,
              score=score,
              saving=savings.estimated_savings.get(model, "n/a"),
              model=model),
            err=True,
        )

    if json_output:
        payload = {
            "compressed": result.compressed_text,
            "original_tokens": result.original_tokens,
            "compressed_tokens": result.compressed_tokens,
            "compression_ratio": result.compression_ratio,
            "preservation_score": score,
            "estimated_savings": savings.estimated_savings,
            "pricing_accuracy": accuracy,
            "pricing_note": savings.pricing_note,
            "skipped": False,
            "warning": result.warning,
        }
        _write_output(json.dumps(payload, indent=2), output)
    else:
        _write_output(result.compressed_text, output)


def _write_output(text: str, destination: Path | None) -> None:
    if destination is not None:
        destination.write_text(text, encoding="utf-8")
        typer.echo(t("compress.written", path=destination), err=True)
    else:
        typer.echo(text, nl=False)


def _fill_interactively(
    source: Path | None,
    ratio: float | None,
    model: str | None,
    output: Path | None,
) -> tuple[Path | None, float | None, str | None, Path | None]:
    try:
        import questionary
    except ImportError:
        typer.echo("Install questionary for interactive mode: pip install questionary", err=True)
        raise typer.Exit(1)

    # source
    if source is None:
        source_choice = questionary.select(
            t("interactive.select_source"),
            choices=[t("interactive.source_file"), t("interactive.source_stdin")],
        ).ask()
        if source_choice == t("interactive.source_file"):
            path_str = questionary.path(t("interactive.enter_filepath")).ask()
            if path_str:
                source = Path(path_str)

    # ratio
    if ratio is None:
        ratio_choices = [
            t("interactive.ratio_aggressive"),
            t("interactive.ratio_balanced"),
            t("interactive.ratio_light"),
            t("interactive.ratio_very_light"),
            t("interactive.ratio_custom"),
        ]
        ratio_map = {
            t("interactive.ratio_aggressive"): 0.3,
            t("interactive.ratio_balanced"): 0.5,
            t("interactive.ratio_light"): 0.6,
            t("interactive.ratio_very_light"): 0.7,
        }
        ratio_choice = questionary.select(
            t("interactive.select_ratio"), choices=ratio_choices
        ).ask()
        if ratio_choice == t("interactive.ratio_custom"):
            raw = questionary.text(t("interactive.enter_ratio")).ask()
            try:
                ratio = float(raw)
            except (TypeError, ValueError):
                ratio = 0.5
        else:
            ratio = ratio_map.get(ratio_choice, 0.5)

    # model
    if model is None:
        model_choices = FEATURED_MODELS + [t("interactive.model_other")]
        model_choice = questionary.select(
            t("interactive.select_model"), choices=model_choices
        ).ask()
        if model_choice == t("interactive.model_other"):
            model = questionary.text(t("interactive.enter_model")).ask()
        else:
            model = model_choice

    # output
    if output is None:
        out_choice = questionary.select(
            t("interactive.select_output"),
            choices=[t("interactive.output_stdout"), t("interactive.output_file")],
        ).ask()
        if out_choice == t("interactive.output_file"):
            path_str = questionary.path(t("interactive.enter_filepath")).ask()
            if path_str:
                output = Path(path_str)

    return source, ratio, model, output
