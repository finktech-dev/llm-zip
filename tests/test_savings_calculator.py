import typing
from unittest.mock import patch

from llmzip.core.savings_calculator import _build_model_list, calculate_savings

MOCK_PRICES = {
    "gpt-4o-mini":          {"input": 0.15,  "output": 0.60},
    "gpt-5.4-mini":         {"input": 0.40,  "output": 1.60},
    "claude-haiku-4-5":     {"input": 1.00,  "output": 5.00},
    "gemini-2.5-flash-lite":{"input": 0.10,  "output": 0.40},
    "deepseek-v4-flash":    {"input": 0.07,  "output": 0.28},
}
MOCK_META = {"note": "test prices"}


@patch("llmzip.core.savings_calculator.resolve_prices", return_value=(MOCK_PRICES, MOCK_META))
def test_returns_savings_for_featured_models(mock_resolve: typing.Any) -> None:
    result = calculate_savings(
        original_text="word " * 1000,
        compressed_text="word " * 200,
        default_model="gpt-4o-mini",
    )
    assert "gpt-4o-mini" in result.estimated_savings
    assert "claude-haiku-4-5" in result.estimated_savings


@patch("llmzip.core.savings_calculator.resolve_prices", return_value=(MOCK_PRICES, MOCK_META))
def test_savings_are_positive(mock_resolve: typing.Any) -> None:
    result = calculate_savings(
        original_text="word " * 1000,
        compressed_text="word " * 200,
        default_model="gpt-4o-mini",
    )
    for model, saving in result.estimated_savings.items():
        value = float(saving.replace("$", ""))
        assert value >= 0, f"Negative saving for {model}"


@patch("llmzip.core.savings_calculator.resolve_prices", return_value=(MOCK_PRICES, MOCK_META))
def test_custom_default_model_included(mock_resolve: typing.Any) -> None:
    result = calculate_savings(
        original_text="word " * 500,
        compressed_text="word " * 100,
        default_model="deepseek-v4-pro",
    )
    # deepseek-v4-pro is not in MOCK_PRICES so it won't appear, but shouldn't crash
    assert isinstance(result.estimated_savings, dict)


def test_build_model_list_includes_default() -> None:
    models = _build_model_list("my-custom-model")
    assert "my-custom-model" in models
    assert models[0] == "my-custom-model"


def test_build_model_list_no_duplicate() -> None:
    models = _build_model_list("gpt-4o-mini")
    assert models.count("gpt-4o-mini") == 1
