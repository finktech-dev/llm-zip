from unittest.mock import patch
import llmzip.core.token_counter as token_counter

def test_get_encoding_retries_after_exception():
    # Reiniciar cache para el test
    token_counter._encoding_cache = {}
    
    with patch("tiktoken.encoding_for_model") as mock_tik:
        # Primer intento: Error de red (transitorio)
        mock_tik.side_effect = Exception("Network timeout")
        res1 = token_counter._get_encoding("gpt-4o")
        assert res1 is None
        assert "gpt-4o" not in token_counter._encoding_cache
        
        # Segundo intento: Red recuperada (éxito)
        mock_tik.side_effect = None
        mock_tik.return_value = "mock_encoding"
        res2 = token_counter._get_encoding("gpt-4o")
        assert res2 == "mock_encoding"
        assert token_counter._encoding_cache["gpt-4o"] == "mock_encoding"

def test_get_encoding_permanently_caches_keyerror():
    token_counter._encoding_cache = {}
    
    with patch("tiktoken.encoding_for_model") as mock_tik:
        # Modelo desconocido (Error permanente)
        mock_tik.side_effect = KeyError("invalid-model")
        res = token_counter._get_encoding("invalid-model")
        assert res is None
        # Debe estar en cache como None para no volver a llamar a tiktoken
        assert "invalid-model" in token_counter._encoding_cache
        assert token_counter._encoding_cache["invalid-model"] is None
