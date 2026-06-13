import os
from pathlib import Path

import tiktoken

_CHARS_PER_TOKEN: dict[str, float] = {
    "claude": 3.5,
    "gemini": 4.0,
    "deepseek": 4.0,
    "default": 4.0,
}

_encoding_cache: dict[str, tiktoken.Encoding | None] = {}


def _ensure_tiktoken_cache() -> None:
    if "TIKTOKEN_CACHE_DIR" not in os.environ:
        cache_base = os.environ.get("LLMZIP_CACHE_DIR")
        path = (
            Path(cache_base) / "tiktoken"
            if cache_base
            else Path.home() / ".llmzip" / "tiktoken"
        )
        path.mkdir(parents=True, exist_ok=True)
        os.environ["TIKTOKEN_CACHE_DIR"] = str(path)


_ensure_tiktoken_cache()


def _get_encoding(model: str) -> tiktoken.Encoding | None:
    if model in _encoding_cache:
        return _encoding_cache[model]
    try:
        enc = tiktoken.encoding_for_model(model)
        _encoding_cache[model] = enc
        return enc
    except KeyError:
        _encoding_cache[model] = None
        return None
    except Exception:
        # Transient error (network, timeout, etc.) — do not cache, allow retry next call.
        return None


def count_tokens(
    text: str | None,
    model: str,
    cache: dict[str, int] | None = None,
) -> tuple[int, str]:
    if text is None:
        return 0, "exact"

    txt = str(text)
    if not txt:
        return 0, "exact"

    model_lower = model.lower()
    enc = _get_encoding(model_lower)

    if enc is not None:
        if cache is not None and enc.name in cache:
            return cache[enc.name], "exact"
        count = max(1, len(enc.encode(txt)))
        if cache is not None:
            cache[enc.name] = count
        return count, "exact"

    for provider, ratio in _CHARS_PER_TOKEN.items():
        if provider == "default":
            continue
        if model_lower.startswith(provider):
            if cache is not None and provider in cache:
                return cache[provider], "estimated±10%"
            count = _count_with_ratio(txt, ratio)
            if cache is not None:
                cache[provider] = count
            return count, "estimated±10%"

    if cache is not None and "default" in cache:
        return cache["default"], "estimated±10%"
    count = _count_with_ratio(txt, _CHARS_PER_TOKEN["default"])
    if cache is not None:
        cache["default"] = count
    return count, "estimated±10%"


def _count_with_ratio(text: str, chars_per_token: float) -> int:
    return max(1, int(len(text) / chars_per_token))
