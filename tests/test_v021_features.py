import typing
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from llmzip.api.app import create_app
from llmzip.config.loader import AppConfig


@pytest.fixture
def client() -> typing.Generator[typing.Any, None, None]:
    with patch("llmzip.api.app.load") as mock_load, \
         patch("llmzip.api.app.LinguaAdapter"), \
         patch("llmzip.api.app.SemanticScorer"), \
         patch("llmzip.api.app.set_models_loaded"):
        cfg = AppConfig(
            port=8000, api_key=None, deploy_mode="monolith", models_url="...",
            max_tokens=1000, min_tokens_to_compress=50, default_ratio=0.5,
            default_model="gpt-4o-mini", max_batch_size=10, batch_workers=1,
            chunk_size=400, compression_model="bert-base", scorer_model="...",
            scorer_timeout=10, pricing_cache_ttl=3600, cache_dir=None, rate_limit_enabled=False,
            rate_limit_rpm=60, rate_limit_rpd=10000, max_file_size_mb=1,
            file_conversion_enabled=True, lang="en"
        )
        mock_load.return_value = cfg
        app = create_app()
        with TestClient(app) as c:
            yield c

def test_health_live(client: typing.Any) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_ready_503(client: typing.Any) -> None:
    from llmzip.api.routes.health import set_models_loaded
    set_models_loaded(False)
    response = client.get("/health/ready")
    assert response.status_code == 503

def test_info_endpoint(client: typing.Any) -> None:
    with patch("llmzip.api.routes.info.version", return_value="0.2.1"):
        response = client.get("/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "0.2.1"
        assert "features" in data
        assert "limits" in data

def test_file_size_validation(client: typing.Any) -> None:
    # Create a dummy file larger than 1MB
    large_content = b"a" * (2 * 1024 * 1024)
    response = client.post(
        "/v1/compress/file",
        files={"file": ("test.txt", large_content)},
        headers={"content-length": str(len(large_content))}
    )
    assert response.status_code == 413
