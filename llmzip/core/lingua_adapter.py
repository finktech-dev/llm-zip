import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from llmlingua import PromptCompressor

from llmzip.core.token_counter import count_tokens

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "bert-base": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    "xlm-roberta-large": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
}

_WARNING_COMPRESSION_FAILED = "compress.warning.compression_failed"


@dataclass
class CompressionResult:
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    warning: str | None = None


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

    def _split_into_chunks(self, text: str, target_model: str) -> list[str]:
        # split by double newline (paragraphs)
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            p_len, _ = count_tokens(p, target_model)

            # if a single paragraph is too large, it stays alone
            if current_len + p_len > self._chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_len = p_len
            else:
                current_chunk.append(p)
                current_len += p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def load(self) -> None:
        if self._compressor is not None:
            return

        with self._load_lock:
            if self._compressor is not None:
                return

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
            chunks = self._split_into_chunks(text, target_model)
            compressed_parts: list[str] = []
            total_compressed_tokens = 0

            # PromptCompressor (LLMLingua-2) is thread-safe for inference on CPU
            # because PyTorch forward passes do not mutate model state.
            for chunk in chunks:
                res = self._compressor.compress_prompt(
                    chunk,
                    rate=ratio,
                    force_tokens=["\n"],
                )
                comp_text = res["compressed_prompt"]
                compressed_parts.append(comp_text)
                c_tokens, _ = count_tokens(comp_text, target_model)
                total_compressed_tokens += c_tokens

            full_compressed = "\n".join(compressed_parts)
            actual_ratio = (
                original_tokens / total_compressed_tokens
                if total_compressed_tokens > 0
                else 1.0
            )

            return CompressionResult(
                compressed_text=full_compressed,
                original_tokens=original_tokens,
                compressed_tokens=total_compressed_tokens,
                compression_ratio=round(actual_ratio, 2),
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