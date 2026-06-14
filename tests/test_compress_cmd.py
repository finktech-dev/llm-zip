import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from llmzip.cli.main import app
from llmzip.core.lingua_adapter import CompressionResult
from llmzip.core.savings_calculator import SavingsResult

runner = CliRunner()

MOCK_CONFIG = MagicMock(
    max_tokens=128000,
    min_tokens_to_compress=10,
    default_model="gpt-4o-mini",
    compression_model="bert-base",
    file_conversion_enabled=True,
)

MOCK_COMPRESSION = CompressionResult(
    compressed_text="compressed output",
    original_tokens=500,
    compressed_tokens=100,
    compression_ratio=5.0,
)

MOCK_SAVINGS = SavingsResult(
    estimated_savings={"gpt-4o-mini": "$0.000005"},
    pricing_accuracy="exact",
    pricing_note="test",
)


@pytest.fixture
def txt_file(tmp_path: Path) -> Path:
    f = tmp_path / "input.txt"
    f.write_text("word " * 200)
    return f


def _patches() -> None:
    return [  # type: ignore
        patch("llmzip.cli.compress_cmd.load", return_value=MOCK_CONFIG),
        patch("llmzip.cli.compress_cmd.LinguaAdapter"),
        patch("llmzip.cli.compress_cmd.SemanticScorer"),
        patch("llmzip.cli.compress_cmd.calculate_savings", return_value=MOCK_SAVINGS),
        patch("llmzip.cli.compress_cmd.count_tokens", return_value=(500, "exact")),
    ]


def test_compress_file_exits_zero(txt_file: Path) -> None:
    lingua_mock = MagicMock()
    lingua_mock.compress.return_value = MOCK_COMPRESSION
    scorer_mock = MagicMock()
    scorer_mock.score.return_value = 0.91

    with patch("llmzip.cli.compress_cmd.load", return_value=MOCK_CONFIG), \
         patch("llmzip.cli.compress_cmd.LinguaAdapter", return_value=lingua_mock), \
         patch("llmzip.cli.compress_cmd.SemanticScorer", return_value=scorer_mock), \
         patch("llmzip.cli.compress_cmd.calculate_savings", return_value=MOCK_SAVINGS), \
         patch("llmzip.cli.compress_cmd.count_tokens", return_value=(500, "exact")):
        result = runner.invoke(app, ["compress", str(txt_file)])

    assert result.exit_code == 0


def test_compress_stdout_contains_compressed_text(txt_file: Path) -> None:
    lingua_mock = MagicMock()
    lingua_mock.compress.return_value = MOCK_COMPRESSION
    scorer_mock = MagicMock()
    scorer_mock.score.return_value = 0.91

    with patch("llmzip.cli.compress_cmd.load", return_value=MOCK_CONFIG), \
         patch("llmzip.cli.compress_cmd.LinguaAdapter", return_value=lingua_mock), \
         patch("llmzip.cli.compress_cmd.SemanticScorer", return_value=scorer_mock), \
         patch("llmzip.cli.compress_cmd.calculate_savings", return_value=MOCK_SAVINGS), \
         patch("llmzip.cli.compress_cmd.count_tokens", return_value=(500, "exact")):
        result = runner.invoke(app, ["compress", str(txt_file)])

    assert "compressed output" in result.output


def test_compress_skipped_below_threshold(txt_file: Path) -> None:
    config = MagicMock(**{**MOCK_CONFIG.__dict__, "min_tokens_to_compress": 99999})

    with patch("llmzip.cli.compress_cmd.load", return_value=config), \
         patch("llmzip.cli.compress_cmd.LinguaAdapter"), \
         patch("llmzip.cli.compress_cmd.SemanticScorer"), \
         patch("llmzip.cli.compress_cmd.count_tokens", return_value=(5, "exact")):
        result = runner.invoke(app, ["compress", str(txt_file)])

    assert result.exit_code == 0


def test_compress_writes_to_output_file(txt_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    lingua_mock = MagicMock()
    lingua_mock.compress.return_value = MOCK_COMPRESSION
    scorer_mock = MagicMock()
    scorer_mock.score.return_value = 0.91

    with patch("llmzip.cli.compress_cmd.load", return_value=MOCK_CONFIG), \
         patch("llmzip.cli.compress_cmd.LinguaAdapter", return_value=lingua_mock), \
         patch("llmzip.cli.compress_cmd.SemanticScorer", return_value=scorer_mock), \
         patch("llmzip.cli.compress_cmd.calculate_savings", return_value=MOCK_SAVINGS), \
         patch("llmzip.cli.compress_cmd.count_tokens", return_value=(500, "exact")):
        result = runner.invoke(app, ["compress", str(txt_file), "--output", str(out)])

    assert result.exit_code == 0
    assert out.exists()
    assert out.read_text() == "compressed output"


def test_compress_json_flag_returns_valid_json(txt_file: Path) -> None:
    import json
    lingua_mock = MagicMock()
    lingua_mock.compress.return_value = MOCK_COMPRESSION
    scorer_mock = MagicMock()
    scorer_mock.score.return_value = 0.91

    with patch("llmzip.cli.compress_cmd.load", return_value=MOCK_CONFIG), \
         patch("llmzip.cli.compress_cmd.LinguaAdapter", return_value=lingua_mock), \
         patch("llmzip.cli.compress_cmd.SemanticScorer", return_value=scorer_mock), \
         patch("llmzip.cli.compress_cmd.calculate_savings", return_value=MOCK_SAVINGS), \
         patch("llmzip.cli.compress_cmd.count_tokens", return_value=(500, "exact")):
        result = runner.invoke(app, ["compress", str(txt_file), "--json"])

    parsed = json.loads(result.output)
    assert "compressed" in parsed
    assert "compression_ratio" in parsed
    assert "estimated_savings" in parsed
