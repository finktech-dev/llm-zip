import typing
from unittest.mock import MagicMock, patch

import pytest

from llmzip.conversion.file_converter import (
    SUPPORTED_EXTENSIONS,
    convert,
)


def test_supported_extensions_not_empty() -> None:
    assert len(SUPPORTED_EXTENSIONS) > 0
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS


def test_unsupported_extension_raises(tmp_path) -> None:  # type: ignore
    fake = tmp_path / "file.xyz"
    fake.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file format"):
        convert(fake)


@patch("llmzip.conversion.file_converter._assert_markitdown_available")
def test_convert_returns_result_on_success(mock_check: typing.Any, tmp_path) -> None:  # type: ignore
    fake_file = tmp_path / "doc.pdf"
    fake_file.write_bytes(b"fake pdf content")

    mock_result = MagicMock()
    mock_result.text_content = "extracted text from document"

    mock_md_instance = MagicMock()
    mock_md_instance.convert.return_value = mock_result

    with patch("markitdown.MarkItDown", return_value=mock_md_instance):
        result = convert(fake_file)

    assert result.text == "extracted text from document"
    assert result.source_format == ".pdf"
    assert result.warning is None


@patch("llmzip.conversion.file_converter._assert_markitdown_available")
def test_convert_returns_warning_on_empty_text(mock_check: typing.Any, tmp_path) -> None:  # type: ignore
    fake_file = tmp_path / "empty.docx"
    fake_file.write_bytes(b"")

    mock_result = MagicMock()
    mock_result.text_content = "   "

    mock_md_instance = MagicMock()
    mock_md_instance.convert.return_value = mock_result

    with patch("markitdown.MarkItDown", return_value=mock_md_instance):
        result = convert(fake_file)

    assert result.warning == "compress.warning.file_empty_text"


def test_markitdown_unavailable_raises_runtime_error() -> None:
    with patch.dict("sys.modules", {"markitdown": None}):
        with pytest.raises(RuntimeError, match="MarkItDown is not installed"):
            from llmzip.conversion.file_converter import _assert_markitdown_available
            _assert_markitdown_available()
