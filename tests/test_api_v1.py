import typing
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from llmzip.api.app import app


# Bypassing the heavy model loading for unit tests
@pytest.fixture(autouse=True)
def mock_models_loading() -> typing.Generator[typing.Any, None, None]:
    with patch("llmzip.core.lingua_adapter.LinguaAdapter.load", return_value=None), \
         patch("llmzip.core.semantic_scorer.SemanticScorer.load", return_value=None):
        yield

# Usamos context manager global para el cliente si queremos disparar el lifespan (mockeado)
@pytest.fixture
def client() -> typing.Generator[typing.Any, None, None]:
    # Aseguramos que la app tenga una configuración válida para los tests
    with TestClient(app) as c:
        # Aseguramos que el estado tenga mocks si el lifespan no los puso
        if not hasattr(c.app.state, "lingua"):  # type: ignore
            c.app.state.lingua = MagicMock()  # type: ignore
        if not hasattr(c.app.state, "scorer"):  # type: ignore
            c.app.state.scorer = MagicMock()  # type: ignore
        yield c

def test_compress_skipped_logic(client: typing.Any) -> None:
    with patch("llmzip.api.routes.compress.count_tokens", return_value=(10, "exact")):
        res = client.post("/v1/compress", json={
            "text": "short",
            "model": "gpt-4o",
            "ratio": 0.5
        })
        assert res.status_code == 200
        data = res.json()
        assert data["skipped"] is True
        assert "gpt-4o" in data["estimated_savings"]

def test_batch_schema_consistency(client: typing.Any) -> None:
    with patch("llmzip.api.routes.compress.count_tokens", return_value=(10, "exact")):
        # Usamos claude-opus-4-8 que está en FALLBACK_PRICES
        res = client.post("/v1/compress/batch", json={
            "texts": [{"text": "short", "model": "claude-opus-4-8"}]
        })
        assert res.status_code == 200
        data = res.json()
        result = data["results"][0]
        assert "skipped" in result
        assert "warning" in result
        assert result["skipped"] is True
        assert "claude-opus-4-8" in result["estimated_savings"]

def test_batch_error_handling(client: typing.Any) -> None:
    with patch("llmzip.api.routes.compress.count_tokens", return_value=(1000, "exact")):
        mock_adapter = MagicMock()
        mock_adapter.compress.side_effect = Exception("Inference Error")
        client.app.state.lingua = mock_adapter
        
        res = client.post("/v1/compress/batch", json={
            "texts": [{"text": "long text enough to trigger compression"}]
        })
        data = res.json()
        assert data["results"][0]["status"] == "error"
        assert "Inference Error" in data["results"][0]["reason"]

def test_estimate_endpoint(client: typing.Any) -> None:
    with patch("llmzip.api.routes.estimate.count_tokens", return_value=(100, "exact")):
        # Mocking config to ensure deterministic threshold behavior
        client.app.state.config.min_tokens_to_compress = 500
        
        res = client.post("/v1/estimate", json={
            "text": "medium text",
            "model": "gpt-4o",
            "ratio": 0.5
        })
        assert res.status_code == 200
        data = res.json()
        assert data["original_tokens"] == 100
        assert data["estimated_compressed_tokens"] == 50
        assert data["would_compress"] is False

def test_models_endpoint(client: typing.Any) -> None:
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data

def test_info_endpoint(client: typing.Any) -> None:
    res = client.get("/v1/info")
    assert res.status_code == 200
    data = res.json()
    assert "version" in data

def test_health_endpoints(client: typing.Any) -> None:
    assert client.get("/health/live").status_code == 200
    assert client.get("/health").status_code == 200

@patch("llmzip.conversion.file_converter.convert")
@patch("llmzip.api.routes.compress_file.count_tokens")
def test_compress_file_mocked(mock_count: typing.Any, mock_convert, client: typing.Any) -> None:  # type: ignore
    mock_convert.return_value = MagicMock(text="extracted content", warning=None)
    mock_count.return_value = (10, "exact")
    
    file_content = b"fake file content"
    file = io.BytesIO(file_content)
    
    res = client.post(
        "/v1/compress/file",
        files={"file": ("test.txt", file, "text/plain")},
        data={"ratio": 0.5, "model": "gpt-4o"}
    )
    
    assert res.status_code == 200
    data = res.json()
    assert data["skipped"] is True
    assert data["compressed"] == "extracted content"
