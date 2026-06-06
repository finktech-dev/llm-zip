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


@dataclass
class CompressionResult:
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    warning: str | None = None


class LinguaAdapter:
    def __init__(self, model_name: str, models_dir: Path, device: str = "cpu") -> None:
        self._model_name = model_name
        self._models_dir = models_dir
        self._device = device
        self._compressor: PromptCompressor | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
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
            with self._lock:
                result = self._compressor.compress_prompt(
                    text,
                    rate=ratio,
                    force_tokens=["
"],
                )
            compressed = result["compressed_prompt"]
            compressed_tokens, _ = count_tokens(compressed, target_model)
            actual_ratio = (
                original_tokens / compressed_tokens if compressed_tokens > 0 else 1.0
            )
            return CompressionResult(
                compressed_text=compressed,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=round(actual_ratio, 2),
            )
        except Exception as exc:
            logger.warning("Compression failed: %s", exc)
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                warning="compression_failed",
            )
