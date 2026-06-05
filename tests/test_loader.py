import configparser
import pytest
from unittest.mock import patch
from pathlib import Path

from llmzip.config.loader import _validate_required, AppConfig


def _make_parser(overrides: dict | None = None) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read_dict({
        "server": {
            "MAX_TOKENS": "128000",
            "MIN_TOKENS_TO_COMPRESS": "500",
            "PORT": "8000",
        },
        "compression": {
            "DEFAULT_RATIO": "0.5",
            "DEFAULT_MODEL": "gpt-4o-mini",
            "MAX_BATCH_SIZE": "25",
            "BATCH_WORKERS": "4",
            "COMPRESSION_MODEL": "bert-base",
        },
        "pricing": {"CACHE_TTL": "3600"},
        "rate_limit": {
            "ENABLED": "false",
            "REQUESTS_PER_MINUTE": "60",
            "REQUESTS_PER_DAY": "10000",
        },
        "features": {"FILE_CONVERSION": "true"},
    })
    if overrides:
        for section, values in overrides.items():
            parser.read_dict({section: values})
    return parser


def test_validate_required_passes_with_valid_config() -> None:
    parser = _make_parser()
    _validate_required(parser)  # should not raise or exit


def test_validate_required_fails_on_missing_max_tokens(capsys) -> None:
    parser = _make_parser({"server": {"MAX_TOKENS": ""}})
    with pytest.raises(SystemExit):
        _validate_required(parser)
    captured = capsys.readouterr()
    assert "MAX_TOKENS" in captured.err


def test_validate_required_fails_on_missing_default_model(capsys) -> None:
    parser = _make_parser({"compression": {"DEFAULT_MODEL": ""}})
    with pytest.raises(SystemExit):
        _validate_required(parser)
    captured = capsys.readouterr()
    assert "DEFAULT_MODEL" in captured.err


def test_load_fails_when_config_file_missing(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    from llmzip.config import loader
    with pytest.raises(SystemExit):
        loader.load()
    captured = capsys.readouterr()
    assert "not found" in captured.err
