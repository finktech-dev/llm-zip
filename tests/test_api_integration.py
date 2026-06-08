import pytest
from unittest.mock import patch, MagicMock

# Mock load before importing create_app to avoid actual config reading at module level
from llmzip.config.loader import AppConfig

MOCK_CONFIG_BASE = {
    "port": 8000,
    "api_key": None,
    "deploy_mode": "monolith",
    "models_url": "http://llmzip-models:8001",
    "max_tokens": 10000,
    "min_tokens_to_compress": 500,
    "default_ratio": 0.5,
    "default_model": "gpt-4o-mini",
    "max_batch_size": 25,
    "batch_workers": 4,
    "chunk_size": 400,
    "compression_model": "bert-base",
    "scorer_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "scorer_timeout": 30,
    "pricing_cache_ttl": 3600,
    "rate_limit_enabled": False,
    "rate_limit_rpm": 60,
    "rate_limit_rpd": 10000,
    "file_conversion_enabled": True,
    "lang": "en"
}

@pytest.fixture
def mock_load():
    with patch("llmzip.api.app.load") as m:
        m.return_value = AppConfig(**MOCK_CONFIG_BASE)
        yield m

@pytest.fixture(autouse=True)
def reset_limiter_storage():
    from llmzip.api.limiter import limiter
    limiter.limiter.storage.reset()
    # Ensure it's disabled by default between tests
    limiter.enabled = False

@pytest.fixture
def client(mock_load):
    # Mocking external dependencies in app.py
    with patch("llmzip.api.app.LinguaAdapter"), \
         patch("llmzip.api.app.SemanticScorer"), \
         patch("llmzip.api.app.set_models_loaded"):
        from llmzip.api.app import create_app
        from fastapi.testclient import TestClient
        app = create_app()
        with TestClient(app) as c:
            yield c

def test_auth_disabled_allows_all(mock_load):
    from llmzip.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/models")
        assert response.status_code == 200

def test_auth_enabled_requires_header(mock_load):
    cfg = AppConfig(**MOCK_CONFIG_BASE)
    cfg.api_key = "secret-key"
    mock_load.return_value = cfg
    
    from llmzip.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/models")
        assert response.status_code == 401

def test_auth_enabled_valid_token(mock_load):
    cfg = AppConfig(**MOCK_CONFIG_BASE)
    cfg.api_key = "secret-key"
    mock_load.return_value = cfg
    
    from llmzip.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/models", headers={"Authorization": "Bearer secret-key"})
        assert response.status_code == 200

def test_health_always_public(mock_load):
    cfg = AppConfig(**MOCK_CONFIG_BASE)
    cfg.api_key = "secret-key"
    mock_load.return_value = cfg
    
    from llmzip.api.app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

def test_rate_limiting(mock_load):
    cfg = AppConfig(**MOCK_CONFIG_BASE)
    cfg.rate_limit_enabled = True
    cfg.rate_limit_rpm = 2 # Low limit for testing
    mock_load.return_value = cfg
    
    from llmzip.api.app import create_app, app as global_app
    from llmzip.core.lingua_adapter import CompressionResult
    from fastapi.testclient import TestClient
    from llmzip.api import limiter as limiter_module
    
    global_app.state.config = cfg
    
    mock_comp = CompressionResult(
        compressed_text="comp", original_tokens=10, compressed_tokens=5, compression_ratio=2.0
    )

    with patch("llmzip.api.app.LinguaAdapter") as mock_lingua, \
         patch("llmzip.api.app.SemanticScorer") as mock_scorer, \
         patch("llmzip.api.app.set_models_loaded"), \
         patch("llmzip.api.routes.compress.calculate_savings") as mock_sav:
        
        mock_lingua.return_value.compress.return_value = mock_comp
        mock_scorer.return_value.score.return_value = 0.95
        mock_sav.return_value = MagicMock(estimated_savings={"gpt-4o-mini": "$0.01"}, pricing_note="test")

        # Set the dynamic limits before creating the app
        limiter_module.set_limits(2, 10000)

        app = create_app()
        with TestClient(app) as client:
            # First request -> 200
            response = client.post("/v1/compress", json={"text": "hello world", "ratio": 0.5})
            assert response.status_code == 200
            
            # Second request -> 200
            response = client.post("/v1/compress", json={"text": "hello world", "ratio": 0.5})
            assert response.status_code == 200
            
            # Third request -> 429
            response = client.post("/v1/compress", json={"text": "hello world", "ratio": 0.5})
            assert response.status_code == 429
