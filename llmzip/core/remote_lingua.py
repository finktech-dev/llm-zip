import logging
import httpx
from llmzip.core.lingua_adapter import CompressionResult

logger = logging.getLogger(__name__)

class RemoteLinguaAdapter:
    """Same interface as LinguaAdapter but delegates to llmzip-models via HTTP."""
    
    def __init__(self, models_url: str) -> None:
        self._url = models_url.rstrip("/")
    
    def load(self) -> None:
        # Models are assumed to be loaded in the remote service.
        # We could add a check here but app.py startup already does polling.
        pass
    
    def compress(self, text: str, ratio: float, target_model: str) -> CompressionResult:
        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    f"{self._url}/infer/compress",
                    json={
                        "text": text,
                        "ratio": ratio,
                        "target_model": target_model
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return CompressionResult(
                    compressed_text=data["compressed_text"],
                    original_tokens=data["original_tokens"],
                    compressed_tokens=data["compressed_tokens"],
                    compression_ratio=data["compression_ratio"],
                    warning=data.get("warning")
                )
        except Exception as e:
            logger.error(f"Remote compression failed: {e}")
            # Fallback to returning original text on failure to match local behavior
            from llmzip.core.token_counter import count_tokens
            original_tokens, _ = count_tokens(text, target_model)
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                warning="remote_inference_failed"
            )
