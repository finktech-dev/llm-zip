import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import numpy as np
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_ID = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 180  # words — keeps tokenized length safely under 512 tokens
CHUNK_OVERLAP = 20


class SemanticScorer:
    def __init__(
        self,
        models_dir: Path | None = None,
        model_id: str = MODEL_ID,
        timeout: int = 30,
    ) -> None:
        self._model: SentenceTransformer | None = None
        self._models_dir = models_dir or Path("models")
        self._model_id = model_id
        self._timeout = timeout

    def load(self) -> None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading semantic scorer: %s", self._model_id)
        self._model = SentenceTransformer(
            self._model_id, cache_folder=str(self._models_dir)
        )
        logger.info("Semantic scorer loaded")

    def score(self, original: str, compressed: str) -> float | None:
        if self._model is None:
            raise RuntimeError("SemanticScorer not loaded — call load() first")

        if self._timeout == 0:
            return self._calculate_score(original, compressed)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._calculate_score, original, compressed)
            try:
                return future.result(timeout=self._timeout)
            except TimeoutError:
                logger.warning(
                    "Semantic scoring timed out after %ds", self._timeout
                )
                return None

    def _calculate_score(self, original: str, compressed: str) -> float:
        original_embedding = self._embed(original)
        compressed_embedding = self._embed(compressed)
        similarity = float(_cosine_similarity(original_embedding, compressed_embedding))
        return round(max(0.0, min(1.0, similarity)), 4)

    def _embed(self, text: str) -> "np.ndarray":
        import numpy as np
        chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            chunks = [text]
        embeddings = self._model.encode(chunks, show_progress_bar=False)  # type: ignore[union-attr]
        # mean pooling across chunks → single vector representing the full text
        return cast(np.ndarray, np.mean(embeddings, axis=0))


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap

    return chunks


def _cosine_similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    import numpy as np
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
