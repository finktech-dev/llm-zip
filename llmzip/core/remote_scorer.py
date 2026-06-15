import logging
from typing import cast

import httpx

logger = logging.getLogger(__name__)


class RemoteSemanticScorer:
    """Same interface as SemanticScorer but delegates to llmzip-models via HTTP."""

    def __init__(self, models_url: str, timeout: float = 60.0) -> None:
        self._url = models_url.rstrip("/")
        self._timeout = timeout

    def load(self) -> None:
        # Models are assumed to be loaded in the remote service.
        pass

    def score(self, original: str, compressed: str) -> float | None:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._url}/infer/score",
                    json={"original": original, "compressed": compressed},
                )
                response.raise_for_status()
                data = response.json()
                return cast(float | None, data.get("score"))
        except Exception as e:
            logger.error("Remote scoring failed: %s", e)
            return None
