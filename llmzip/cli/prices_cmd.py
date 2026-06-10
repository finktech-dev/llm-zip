
import typer

from llmzip.i18n import t
from llmzip.pricing.resolver import resolve_prices


def prices(
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Filter by provider prefix (e.g. anthropic, openai, google, deepseek).",
    ),
    providers: bool = typer.Option(
        False,
        "--providers",
        help="List all available providers from LiteLLM.",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Select provider interactively with arrow keys.",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all models, including known legacy models.",
    ),
) -> None:
    """Show current model prices from LiteLLM (or fallback)."""
    data = resolve_prices()
    meta = data.get("_meta", {})
    note = str(meta.get("note", "")) if isinstance(meta, dict) else ""

    if providers:
        _print_providers(data)
        return

    selected_provider: str | None = provider

    if interactive and not provider:
        selected_provider = _select_provider_interactive(data)
        if selected_provider == "__all__":
            selected_provider = None

    _print_table(data, note, selected_provider, show_all)


def _print_providers(data: dict[str, dict[str, float | str]]) -> None:
    found = _extract_providers(data)
    typer.echo(f"\n{t('prices.providers_header')}:\n")
    for p in sorted(found):
        typer.echo(f"  {p}")
    typer.echo("")


def _print_table(data: dict[str, dict[str, float | str]], note: str, provider: str | None, show_all: bool) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"\n[dim]{note}[/dim]\n")

    table = Table(show_header=True, header_style="bold blue")
    table.add_column(t('prices.header'), style="cyan", no_wrap=True)
    table.add_column(t('prices.col_input'), justify="right")
    table.add_column(t('prices.col_output'), justify="right")

    # Safe list of undeniably legacy models to hide by default
    legacy_prefixes = (
        "claude-v1",
        "claude-v2",
        "claude-instant",
        "text-davinci",
        "text-curie",
        "text-babbage",
        "text-ada",
    )

    found = False
    for model, entry in sorted(data.items()):
        if model == "_meta" or not isinstance(entry, dict):
            continue
        if provider and not model.lower().startswith(provider.lower()):
            continue
        
        # Extract the actual model name without the provider prefix (e.g. "anthropic.claude-v1" -> "claude-v1")
        clean_model_name = model.split(".")[-1] if "." in model else model.split("/")[-1]

        if not show_all and any(clean_model_name.startswith(prefix) for prefix in legacy_prefixes):
            continue

        table.add_row(
            model,
            f"{float(entry['input']):.4f}",
            f"{float(entry['output']):.4f}"
        )
        found = True

    if not found and provider:
        typer.echo(t("prices.no_results", provider=provider), err=True)
    elif found:
        console.print(table)

    typer.echo("")


def _extract_providers(data: dict[str, dict[str, float | str]]) -> list[str]:
    seen: set[str] = set()
    for model in data:
        if model == "_meta":
            continue
        prefix = model.split(".")[0] if "." in model else model.split("/")[0]
        seen.add(prefix.lower())
    return sorted(seen)


def _select_provider_interactive(data: dict[str, dict[str, float | str]]) -> str:
    try:
        import questionary
    except ImportError as e:
        typer.echo("Install questionary for interactive mode: pip install questionary", err=True)
        raise typer.Exit(1) from e

    providers = _extract_providers(data)
    choices = [t("interactive.select_provider_all")] + providers

    result = questionary.select(
        t("interactive.select_provider"),
        choices=choices,
    ).ask()

    if result is None:
        raise typer.Exit(0)

    if result == t("interactive.select_provider_all"):
        return "__all__"

    return str(result)
