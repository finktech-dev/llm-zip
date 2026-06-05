import typer

import llmzip.i18n as i18n
from llmzip.cli.compress_cmd import compress
from llmzip.cli.prices_cmd import prices
from llmzip.cli.download_models import download_models

app = typer.Typer(
    name="llmzip",
    help="Context compression sidecar for LLM applications.",
    no_args_is_help=True,
)


@app.callback()
def main(
    lang: str | None = typer.Option(
        None,
        "--lang",
        help="Language for CLI output (en, es, pt, zh, ja).",
        is_eager=True,
    ),
) -> None:
    if lang:
        i18n.configure(lang)


app.command("compress")(compress)
app.command("prices")(prices)
app.command("download-models")(download_models)
