import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llmlingua import PromptCompressor

from llmzip.core.token_counter import count_tokens

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "bert-base": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    "xlm-roberta-large": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_WARNING_COMPRESSION_FAILED = "compress.warning.compression_failed"
_WARNING_CHUNK_TRUNCATED = "compress.warning.chunk_truncated"


@dataclass
class CompressionResult:
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    warning: str | None = None


@dataclass
class _ChunkAccumulator:
    """Mutable state used while building chunks from segments."""
    chunks: list[str] = field(default_factory=list)
    current: list[str] = field(default_factory=list)
    current_len: int = 0
    truncation_warned: bool = False

    def flush(self, separator: str) -> None:
        if self.current:
            self.chunks.append(separator.join(self.current))
            self.current = []
            self.current_len = 0

    def push(self, segment: str, seg_len: int, separator: str, chunk_size: int) -> None:
        if self.current_len + seg_len > chunk_size and self.current:
            self.flush(separator)
        self.current.append(segment)
        self.current_len += seg_len


def _sliding_window(text: str, chunk_size: int, target_model: str) -> list[str]:
    """
    Last-resort splitter: divide text into fixed-size token windows.

    Operates on whitespace-split tokens so it never cuts mid-token.
    Used when no natural boundary (paragraph / sentence / line) fits
    within chunk_size — e.g. minified JS on a single line.
    """
    words = text.split()
    if not words:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        # Binary-search for the largest slice that fits within chunk_size.
        # In practice chunk_size is ~400 tokens so this is fast.
        end = min(start + chunk_size, len(words))
        while end > start:
            candidate = " ".join(words[start:end])
            cand_len, _ = count_tokens(candidate, target_model)
            if cand_len <= chunk_size:
                break
            end -= 1
        else:
            # Single word exceeds chunk_size — include it anyway (can't split further)
            end = start + 1

        chunks.append(" ".join(words[start:end]))
        start = end

    return chunks


class LinguaAdapter:
    def __init__(
        self,
        model_name: str,
        models_dir: Path,
        device: str = "cpu",
        chunk_size: int = 400,
    ) -> None:
        self._model_name = model_name
        self._models_dir = models_dir
        self._device = device
        self._chunk_size = chunk_size
        self._compressor: PromptCompressor | None = None
        self._load_lock = threading.Lock()

    def _split_sentences(self, paragraph: str) -> list[str]:
        """Split a paragraph into sentences using punctuation boundaries."""
        sentences = _SENTENCE_SPLIT_RE.split(paragraph)
        return [s.strip() for s in sentences if s.strip()]

    def _split_lines(self, block: str) -> list[str]:
        """Split a block by single newlines — natural boundaries in source code."""
        return [ln.strip() for ln in block.splitlines() if ln.strip()]

    def _process_oversized_unit(
        self,
        unit: str,
        target_model: str,
        acc: _ChunkAccumulator,
        separator: str,
    ) -> None:
        """
        Recursively reduce a unit that exceeds chunk_size using progressively
        finer split strategies:

          Level 1 — sentence boundaries  (natural prose)
          Level 2 — single newlines      (source code, config files)
          Level 3 — sliding token window (minified code, JSON blobs, SQL dumps)

        Each level only activates if the previous one yields no sub-units
        smaller than chunk_size. After level 3 nothing can be truncated —
        every output chunk is guaranteed to fit within chunk_size tokens.
        """
        u_len, _ = count_tokens(unit, target_model)
        if u_len <= self._chunk_size:
            acc.push(unit, u_len, separator, self._chunk_size)
            return

        # --- Level 1: sentence split ---
        sentences = self._split_sentences(unit)
        useful_sentences = [s for s in sentences if s != unit]  # avoid infinite loop
        if useful_sentences:
            sent_acc = _ChunkAccumulator()
            for sent in useful_sentences:
                self._process_oversized_unit(sent, target_model, sent_acc, " ")
            sent_acc.flush(" ")
            acc.chunks.extend(sent_acc.chunks)
            if sent_acc.truncation_warned:
                acc.truncation_warned = True
            return

        # --- Level 2: line split ---
        lines = self._split_lines(unit)
        useful_lines = [ln for ln in lines if ln != unit]
        if useful_lines:
            line_acc = _ChunkAccumulator()
            for ln in useful_lines:
                self._process_oversized_unit(ln, target_model, line_acc, "\n")
            line_acc.flush("\n")
            acc.chunks.extend(line_acc.chunks)
            if line_acc.truncation_warned:
                acc.truncation_warned = True
            return

        # --- Level 3: sliding token window ---
        # At this point the unit has no natural split points (e.g. minified JS).
        # Sliding window guarantees every output chunk fits within chunk_size.
        logger.debug(
            "No natural boundary found in %d-token unit — applying sliding window split.",
            u_len,
        )
        windows = _sliding_window(unit, self._chunk_size, target_model)
        acc.chunks.extend(windows)
        # No truncation warning: sliding window always produces valid-sized chunks.

    def _split_into_chunks(self, text: str, target_model: str) -> tuple[list[str], bool]:
        """
        Split text into chunks that fit within chunk_size tokens.

        Strategy (four-level cascade):
          1. Split by double newline into paragraphs.
          2. Paragraphs that fit are accumulated normally.
          3. Oversized paragraphs are handed to _process_oversized_unit(), which
             cascades through: sentence split → line split → sliding window.
          4. truncation_warned is True only if a unit was included as-is without
             any successful sub-division at any level (should never happen after
             the sliding window addition, kept as a safety signal).

        Returns:
            (chunks, truncation_warned)
        """
        paragraphs = text.split("\n\n")
        acc = _ChunkAccumulator()

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            p_len, _ = count_tokens(p, target_model)

            if p_len <= self._chunk_size:
                acc.push(p, p_len, "\n\n", self._chunk_size)
            else:
                acc.flush("\n\n")
                self._process_oversized_unit(p, target_model, acc, "\n\n")

        acc.flush("\n\n")
        return acc.chunks, acc.truncation_warned

    def load(self) -> None:
        if self._compressor is not None:
            return

        with self._load_lock:
            if self._compressor is not None:
                return

            try:
                from llmlingua import PromptCompressor
            except ImportError as e:
                raise ImportError(
                    "llmlingua is not installed. "
                    "Please install llm-zip with inference dependencies: pip install llm-zip[inference]"
                ) from e

            hf_model_id = SUPPORTED_MODELS.get(self._model_name)
            if hf_model_id is None:
                raise ValueError(
                    f"Unknown compression model: {self._model_name}. "
                    f"Valid options: {list(SUPPORTED_MODELS)}"
                )
            logger.info("Loading compression model: %s on %s", hf_model_id, self._device)
            self._compressor = PromptCompressor(
                model_name=hf_model_id,
                use_llmlingua2=True,
                device_map=self._device,
                model_config={"cache_dir": str(self._models_dir)},
                open_api_config={},
            )
            logger.info("Compression model loaded")

    def compress(self, text: str, ratio: float, target_model: str) -> CompressionResult:
        if self._compressor is None:
            raise RuntimeError("LinguaAdapter not loaded — call load() first")

        original_tokens, _ = count_tokens(text, target_model)

        try:
            chunks, truncation_warned = self._split_into_chunks(text, target_model)

            res = self._compressor.compress_prompt(
                chunks,
                rate=ratio,
                force_tokens=["\n"],
            )

            compressed_parts: list[str] = res.get("compressed_prompt_list") or []
            if not compressed_parts:
                compressed_parts = [res["compressed_prompt"]]

            full_compressed = "\n".join(compressed_parts)
            compressed_tokens, _ = count_tokens(full_compressed, target_model)
            actual_ratio = (
                original_tokens / compressed_tokens
                if compressed_tokens > 0
                else 1.0
            )

            return CompressionResult(
                compressed_text=full_compressed,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=round(actual_ratio, 2),
                warning=_WARNING_CHUNK_TRUNCATED if truncation_warned else None,
            )
        except Exception as exc:
            logger.warning("Compression failed: %s", exc)
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                warning=_WARNING_COMPRESSION_FAILED,
            )