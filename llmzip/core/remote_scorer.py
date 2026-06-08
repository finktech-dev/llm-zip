import logging
import httpx

logger = logging.getLogger(__name__)

class RemoteSemanticScorer:
    """Same interface as SemanticScorer but delegates to llmzip-models via HTTP."""
    
    def __init__(self, models_url: str) -> None:
        self._url = models_url.rstrip("/")
    
    def load(self) -> None:
        # Models are assumed to be loaded in the remote service.
        pass
    
    def score(self, original: str, compressed: str) -> float | None:
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self._url}/infer/score",
                    json={
                        "original": original,
                        "compressed": compressed
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("score")
        except Exception as e:
            logger.error(f"Remote scoring failed: {e}")
            return None
