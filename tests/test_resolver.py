import typing
from unittest.mock import patch

import pytest

from llmzip.pricing.fallback import FALLBACK_PRICES
from llmzip.pricing.resolver import resolve_prices


@pytest.fixture(autouse=True)
def reset_resolver() -> typing.Generator[typing.Any, None, None]:
    import llmzip.pricing.resolver as resolver
    resolver._cache_prices = {}
    resolver._cache_meta = {}
    resolver._cache_timestamp = 0.0
    resolver._last_fetch_attempt = 0.0
    with patch("llmzip.pricing.resolver.disk_load", return_value=None), \
         patch("llmzip.pricing.resolver.disk_save"):
        yield


@patch("llmzip.pricing.resolver.fetch_prices", return_value=None)
def test_falls_back_when_fetch_fails(mock_fetch: typing.Any) -> None:
    prices, meta = resolve_prices()
    # must contain at least the fallback models
    for model in FALLBACK_PRICES:
        assert model in prices


@patch("llmzip.pricing.resolver.fetch_prices")
def test_uses_fetched_prices_when_available(mock_fetch: typing.Any) -> None:
    mock_prices = {"some-model": {"input": 1.0, "output": 2.0}}
    mock_meta = {"note": "test"}
    mock_fetch.return_value = (mock_prices, mock_meta)
    
    prices, meta = resolve_prices()
    assert "some-model" in prices
    assert meta["note"] == "test"


@patch("llmzip.pricing.resolver.fetch_prices", return_value=None)
def test_fallback_includes_meta_note(mock_fetch: typing.Any) -> None:
    prices, meta = resolve_prices()
    assert "note" in meta
