import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from llmzip.api.app import app
from llmzip.api.dependencies import get_config
import io

@pytest.fixture(autouse=True)
def mock_heavy_loaders():
    with patch("llmzip.core.lingua_adapter.LinguaAdapter.load", return_value=None), \
         patch("llmzip.core.semantic_scorer.SemanticScorer.load", return_value=None):
        yield

@pytest.fixture
def client():
    app.dependency_overrides = {}
    with TestClient(app) as c:
        mock_lingua = MagicMock()
        mock_lingua.compress.return_value = MagicMock(
            compressed_text="compressed text",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=2.0,
            warning=None
        )
        c.app.state.lingua = mock_lingua
        c.app.state.scorer = MagicMock()
        c.app.state.scorer.score.return_value = 0.95
        yield c

def test_text_exceeds_max_tokens(client):
    mock_config = MagicMock()
    mock_config.max_tokens = 100
    mock_config.default_model = "gpt-4o-mini"
    mock_config.min_tokens_to_compress = 10
    app.dependency_overrides[get_config] = lambda: mock_config

    res = client.post("/v1/compress", json={
        "text": "word " * 200,
        "ratio": 0.5
    })
    assert res.status_code == 413

def test_pydantic_ratio_validation(client):
    res = client.post("/v1/compress", json={
        "text": "some text",
        "ratio": 1.5
    })
    assert res.status_code == 422

def test_invalid_model_name_does_not_crash(client):
    res = client.post("/v1/compress", json={
        "text": "short",
        "model": "ghost-model-999",
        "ratio": 0.5
    })
    assert res.status_code == 200
    assert res.json()["skipped"] is True

def test_compress_file_unsupported(client):
    file = io.BytesIO(b"fake data")
    res = client.post(
        "/v1/compress/file",
        files={"file": ("malicious.exe", file, "application/x-msdownload")},
        data={"ratio": 0.5}
    )
    assert res.status_code == 400

def test_batch_oversized_item(client):
    mock_config = MagicMock()
    mock_config.max_tokens = 50
    mock_config.max_batch_size = 10
    mock_config.batch_workers = 4 # Valor numérico real para ThreadPoolExecutor
    mock_config.default_model = "gpt-4o-mini"
    mock_config.min_tokens_to_compress = 5
    app.dependency_overrides[get_config] = lambda: mock_config

    res = client.post("/v1/compress/batch", json={
        "texts": [
            {"text": "short"},
            {"text": "very " * 100} 
        ]
    })
    assert res.status_code == 200
    results = res.json()["results"]
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "error"
    assert results[1]["reason"] == "above_max_tokens"
