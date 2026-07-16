import logging

import httpx

from llmzip.core.lingua_adapter import CompressionResult

logger = logging.getLogger(__name__)


class RemoteLinguaAdapter:
    """Same interface as LinguaAdapter but delegates to llmzip-models via HTTP."""

    def __init__(self, models_url: str, timeout: float = 300.0) -> None:
        self._url = models_url.rstrip("/")
        self._timeout = timeout
        # Persistent client with connection pooling — avoids a full TCP handshake
        # per compression request. In a batch of 25 items with 4 workers that's
        # potentially 25 connections reused instead of 25 new handshakes.
        self._client = httpx.Client(
            timeout=self._timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

    def load(self) -> None:
        # Models are assumed to be loaded in the remote service.
        # We could add a check here but app.py startup already does polling.
        pass

    def close(self) -> None:
        """Close the underlying HTTP client. Called from app.py lifespan shutdown."""
        self._client.close()

    def compress(
        self,
        text: str,
        ratio: float,
        target_model: str,
        preserve_tokens: list[str] | None = None,
    ) -> CompressionResult:
        try:
            response = self._client.post(
                f"{self._url}/infer/compress",
                json={
                    "text": text,
                    "ratio": ratio,
                    "target_model": target_model,
                    "preserve_tokens": preserve_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()

            return CompressionResult(
                compressed_text=data["compressed_text"],
                original_tokens=data["original_tokens"],
                compressed_tokens=data["compressed_tokens"],
                compression_ratio=data["compression_ratio"],
                warning=data.get("warning"),
            )
        except Exception as e:
            logger.error("Remote compression failed: %s", e)
            # Fallback to returning original text on failure to match local behavior
            from llmzip.core.token_counter import count_tokens

            original_tokens, _ = count_tokens(text, target_model)
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                warning="remote_inference_failed",
            )
