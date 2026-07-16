import logging
from typing import cast

import httpx

logger = logging.getLogger(__name__)


class RemoteSemanticScorer:
    """Same interface as SemanticScorer but delegates to llmzip-models via HTTP."""

    def __init__(self, models_url: str, timeout: float = 60.0) -> None:
        self._url = models_url.rstrip("/")
        self._timeout = timeout
        # Persistent client with connection pooling — same rationale as
        # RemoteLinguaAdapter: avoids a new TCP handshake per scoring call.
        self._client = httpx.Client(
            timeout=self._timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    def load(self) -> None:
        # Models are assumed to be loaded in the remote service.
        pass

    def close(self) -> None:
        """Close the underlying HTTP client. Called from app.py lifespan shutdown."""
        self._client.close()

    def score(self, original: str, compressed: str) -> float | None:
        try:
            response = self._client.post(
                f"{self._url}/infer/score",
                json={"original": original, "compressed": compressed},
            )
            response.raise_for_status()
            data = response.json()
            return cast(float | None, data.get("score"))
        except Exception as e:
            logger.error("Remote scoring failed: %s", e)
            return None
