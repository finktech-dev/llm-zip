import pytest
from llmzip.core.token_counter import count_tokens


@pytest.mark.parametrize("model,expected_accuracy", [
    ("gpt-4o-mini", "exact"),
    ("gpt-5.5", "estimated±10%"),
    ("gpt-4.1", "exact"),
    ("claude-haiku-4-5", "estimated±10%"),
    ("claude-sonnet-4-6", "estimated±10%"),
    ("gemini-2.5-flash", "estimated±10%"),
    ("deepseek-v4-pro", "estimated±10%"),
    ("some-unknown-model", "estimated±10%"),
])
def test_accuracy_label(model: str, expected_accuracy: str) -> None:
    _, accuracy = count_tokens("hello world this is a test", model)
    assert accuracy == expected_accuracy


def test_returns_positive_count() -> None:
    count, _ = count_tokens("some text here", "gpt-4o-mini")
    assert count > 0


def test_longer_text_has_more_tokens() -> None:
    short, _ = count_tokens("hello", "gpt-4o-mini")
    long, _ = count_tokens("hello " * 100, "gpt-4o-mini")
    assert long > short


def test_empty_text_returns_one() -> None:
    count, _ = count_tokens("", "gpt-4o-mini")
    assert count >= 1
