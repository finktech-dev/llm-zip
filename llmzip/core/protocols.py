from typing import Protocol

from llmzip.core.lingua_adapter import CompressionResult


class Compressor(Protocol):
    def load(self) -> None: ...
    def compress(
        self,
        text: str,
        ratio: float,
        target_model: str,
        preserve_tokens: list[str] | None = None,
    ) -> CompressionResult: ...


class Scorer(Protocol):
    def load(self) -> None: ...
    def score(self, original: str, compressed: str) -> float | None: ...
