import typing
from unittest.mock import MagicMock, patch

import httpx
import pytest

from llmzip.core.lingua_adapter import CompressionResult
from llmzip.core.remote_lingua import RemoteLinguaAdapter
from llmzip.core.remote_scorer import RemoteSemanticScorer


@pytest.fixture
def models_url() -> typing.Generator[typing.Any, None, None]:
    return "http://test-models:8001"  # type: ignore

def test_remote_lingua_compress_success(models_url) -> None:  # type: ignore
    adapter = RemoteLinguaAdapter(models_url)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "compressed_text": "compressed",
        "original_tokens": 10,
        "compressed_tokens": 5,
        "compression_ratio": 2.0,
        "warning": None
    }
    
    with patch("httpx.Client.post", return_value=mock_response):
        result = adapter.compress("text", 0.5, "gpt-4")
        
        assert isinstance(result, CompressionResult)
        assert result.compressed_text == "compressed"
        assert result.original_tokens == 10
        assert result.compression_ratio == 2.0

def test_remote_lingua_compress_failure_fallback(models_url) -> None:  # type: ignore
    adapter = RemoteLinguaAdapter(models_url)
    
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("down")):
        # Should fallback to original text
        result = adapter.compress("original text", 0.5, "gpt-4")
        
        assert result.compressed_text == "original text"
        assert result.warning == "remote_inference_failed"

def test_remote_scorer_success(models_url) -> None:  # type: ignore
    scorer = RemoteSemanticScorer(models_url)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"score": 0.95}
    
    with patch("httpx.Client.post", return_value=mock_response):
        score = scorer.score("orig", "comp")
        assert score == 0.95

def test_remote_scorer_failure_returns_none(models_url) -> None:  # type: ignore
    scorer = RemoteSemanticScorer(models_url)
    
    with patch("httpx.Client.post", side_effect=Exception("error")):
        score = scorer.score("orig", "comp")
        assert score is None
