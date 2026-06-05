import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".pptx", ".ppt", ".csv", ".html", ".htm",
    ".xml", ".json", ".txt", ".md",
}


@dataclass
class ConversionResult:
    text: str
    source_format: str
    warning: str | None = None


def convert(file_path: Path) -> ConversionResult:
    _assert_markitdown_available()

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {suffix}. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    try:
        from markitdown import MarkItDown  # type: ignore[import]
        md = MarkItDown()
        result = md.convert(str(file_path))
        text = result.text_content.strip()

        if not text:
            return ConversionResult(
                text="",
                source_format=suffix,
                warning="file_produced_empty_text",
            )

        return ConversionResult(text=text, source_format=suffix)

    except Exception as exc:
        logger.error("File conversion failed for %s: %s", file_path.name, exc)
        raise RuntimeError(f"Could not convert {file_path.name}: {exc}") from exc


def convert_bytes(content: bytes, filename: str) -> ConversionResult:
    import tempfile

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(content)

    try:
        return convert(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _assert_markitdown_available() -> None:
    try:
        import markitdown  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "MarkItDown is not installed. "
            "Install it with: pip install markitdown[all]\n"
            "Or set FILE_CONVERSION=false in .llmzip.config to disable file support."
        )
