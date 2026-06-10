import logging
import sys
from pathlib import Path

import typer

from llmzip.i18n import t

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")

_MODEL_INFO = {
    "bert-base": {
        "hf_id": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        "size": "700MB",
        "ram": "4GB RAM",
        "description": "Multilingual, CPU-friendly. Best for Spanish and other non-English content.",
        "url": "https://huggingface.co/microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    },
    "xlm-roberta-large": {
        "hf_id": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
        "size": "1.4GB",
        "ram": "8GB RAM",
        "description": "Higher precision on complex documents. Slower, requires more resources.",
        "url": "https://huggingface.co/microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    },
}


def download_models(
    serve: bool = typer.Option(
        False, "--serve", hidden=True,
        help="Keep process alive after download (used by Docker healthcheck container).",
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Select compression model interactively.",
    ),
) -> None:
    """Download LLMLingua-2 and sentence-transformer models to local storage."""
    from llmzip.config.loader import load
    config = load()

    model_name = config.compression_model

    if interactive:
        model_name = _select_model_interactive()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    typer.echo(t("download.start_compression"))
    _download_lingua(model_name)

    typer.echo(t("download.start_scorer"))
    _download_scorer()

    typer.echo(t("download.all_ready"))

    if serve:
        _serve_readiness()


def _download_lingua(model_name: str) -> None:
    from llmzip.core.lingua_adapter import LinguaAdapter
    marker = MODELS_DIR / f".lingua_{model_name}.ok"

    if marker.exists():
        typer.echo(t("download.already_done", model=model_name))
        return

    typer.echo(t("download.in_progress", model=model_name))
    try:
        adapter = LinguaAdapter(model_name=model_name, models_dir=MODELS_DIR)
        adapter.load()
        marker.touch()
        typer.echo(t("download.compression_ready", model=model_name))
    except Exception as exc:
        typer.echo(t("download.compression_failed", error=str(exc)), err=True)
        sys.exit(1)


def _download_scorer() -> None:
    from llmzip.core.semantic_scorer import MODEL_ID, SemanticScorer
    marker = MODELS_DIR / ".scorer.ok"

    if marker.exists():
        typer.echo(t("download.scorer_already_done"))
        return

    typer.echo(t("download.scorer_in_progress", model=MODEL_ID))
    try:
        scorer = SemanticScorer()
        scorer.load()
        marker.touch()
        typer.echo(t("download.scorer_ready"))
    except Exception as exc:
        typer.echo(t("download.scorer_failed", error=str(exc)), err=True)
        sys.exit(1)


def _select_model_interactive() -> str:
    try:
        import questionary
    except ImportError as e:
        typer.echo("Install questionary for interactive mode: pip install questionary", err=True)
        raise typer.Exit(1) from e

    choices = []
    for key, info in _MODEL_INFO.items():
        label = (
            f"{key}  ({info['size']}, {info['ram']})\n"
            f"    {info['description']}\n"
            f"    → {info['url']}"
        )
        choices.append(questionary.Choice(title=label, value=key))

    result = questionary.select(
        t("interactive.select_compression_model"),
        choices=choices,
    ).ask()

    if result is None:
        raise typer.Exit(0)

    return str(result)


def _serve_readiness() -> None:
    import http.server
    import socketserver

    class ReadyHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/ready":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    with socketserver.TCPServer(("", 8001), ReadyHandler) as httpd:
        typer.echo(t("download.serving"))
        httpd.serve_forever()
