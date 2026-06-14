from pathlib import Path
from unittest.mock import patch

from llmzip.core.ignore import should_skip


def test_should_skip_no_patterns() -> None:
    with patch("llmzip.core.ignore._get_patterns", return_value=[]):
        assert not should_skip("Some text", "file.txt")


def test_should_skip_filename_match() -> None:
    patterns = ["*.md", "*.log"]
    with patch("llmzip.core.ignore._get_patterns", return_value=patterns):
        assert should_skip("Content", "README.md")
        assert should_skip("Content", "error.log")
        assert not should_skip("Content", "script.py")


def test_should_skip_text_prefix_match() -> None:
    patterns = ["You are an expert*", "System prompt:*"]
    with patch("llmzip.core.ignore._get_patterns", return_value=patterns):
        assert should_skip("You are an expert Python developer.", "script.py")
        assert should_skip("System prompt: act as a senior...", "script.py")
        assert not should_skip("You are learning Python.", "script.py")
        assert not should_skip("User: You are an expert", "script.py") # Not prefix


def test_should_skip_both_conditions_met() -> None:
    patterns = ["*.json", "Secret:*"]
    with patch("llmzip.core.ignore._get_patterns", return_value=patterns):
        assert should_skip("Secret: token=123", "config.json") # Both
        assert should_skip("Normal text", "data.json")         # Filename only
        assert should_skip("Secret: token=123", "data.txt")    # Text only
        assert not should_skip("Normal text", "data.txt")      # Neither


def test_load_patterns(tmp_path: Path) -> None:
    ignore_file1 = tmp_path / ".llmzipignore"
    ignore_file2 = tmp_path / ".llmzipignore.local"

    ignore_file1.write_text("*.txt\n\n# comment\nSystem:*", encoding="utf-8")
    ignore_file2.write_text("*.log", encoding="utf-8")

    with patch("llmzip.core.ignore._IGNORE_FILES", [str(ignore_file1), str(ignore_file2)]):
        from llmzip.core.ignore import _load_patterns
        patterns = _load_patterns()
        assert patterns == ["*.txt", "System:*", "*.log"]
