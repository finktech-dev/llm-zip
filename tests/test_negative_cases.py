import io
import typing
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from llmzip.api.dependencies import get_config
from llmzip.config.loader import AppConfig


@pytest.fixture
def client() -> typing.Generator[typing.Any, None, None]:
    mock_config = AppConfig(
        port=8000,
        api_key=None,
        deploy_mode="monolith",
        models_url="http://localhost:8001",
        max_tokens=128000,
        min_tokens_to_compress=500,
        default_ratio=0.5,
        default_model="gpt-4o-mini",
        max_batch_size=25,
        batch_workers=4,
        chunk_size=400,
        compression_model="bert-base",
        scorer_model="paraphrase-multilingual-MiniLM-L12-v2",
        scorer_timeout=30,
        inference_timeout=300,
        pricing_cache_ttl=3600,
        cache_dir=None,
        rate_limit_enabled=False,
        rate_limit_rpm=60,
        rate_limit_rpd=10000,
        max_file_size_mb=50,
        file_conversion_enabled=True,
        lang="en",
    )

    with (
        patch("llmzip.api.app.load", return_value=mock_config),
        patch("llmzip.api.app.LinguaAdapter"),
        patch("llmzip.api.app.SemanticScorer"),
        patch("llmzip.api.app.set_models_loaded"),
    ):
        from llmzip.api.app import create_app

        app = create_app()

        with TestClient(app) as c:
            mock_lingua = MagicMock()
            mock_lingua.compress.return_value = MagicMock(
                compressed_text="compressed text",
                original_tokens=100,
                compressed_tokens=50,
                compression_ratio=2.0,
                warning=None,
            )
            c.app.state.lingua = mock_lingua  # type: ignore
            c.app.state.scorer = MagicMock()  # type: ignore
            c.app.state.scorer.score.return_value = 0.95  # type: ignore
            c.app.dependency_overrides = {}
            yield c


def test_text_exceeds_max_tokens(client: typing.Any) -> None:
    mock_config = MagicMock()
    mock_config.max_tokens = 100
    mock_config.default_model = "gpt-4o-mini"
    mock_config.min_tokens_to_compress = 10
    client.app.dependency_overrides[get_config] = lambda: mock_config

    res = client.post("/v1/compress", json={"text": "word " * 200, "ratio": 0.5})
    assert res.status_code == 413


def test_pydantic_ratio_validation(client: typing.Any) -> None:
    res = client.post("/v1/compress", json={"text": "some text", "ratio": 1.5})
    assert res.status_code == 422


def test_invalid_model_name_does_not_crash(client: typing.Any) -> None:
    res = client.post(
        "/v1/compress", json={"text": "short", "model": "ghost-model-999", "ratio": 0.5}
    )
    assert res.status_code == 200
    assert res.json()["skipped"] is True


def test_compress_file_unsupported(client: typing.Any) -> None:
    file = io.BytesIO(b"fake data")
    res = client.post(
        "/v1/compress/file",
        files={"file": ("malicious.exe", file, "application/x-msdownload")},
        data={"ratio": 0.5},
    )
    assert res.status_code == 400


def test_batch_oversized_item(client: typing.Any) -> None:
    mock_config = MagicMock()
    mock_config.max_tokens = 50
    mock_config.max_batch_size = 10
    mock_config.batch_workers = 4  # Valor numérico real para ThreadPoolExecutor
    mock_config.default_model = "gpt-4o-mini"
    mock_config.min_tokens_to_compress = 5
    client.app.dependency_overrides[get_config] = lambda: mock_config

    res = client.post(
        "/v1/compress/batch", json={"texts": [{"text": "short"}, {"text": "very " * 100}]}
    )
    assert res.status_code == 200
    results = res.json()["results"]
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "error"
    assert results[1]["reason"] == "above_max_tokens"
