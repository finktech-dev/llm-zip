import tiktoken

# chars per token ratios for non-OpenAI models (approximation)
_CHARS_PER_TOKEN: dict[str, float] = {
    "claude": 3.5,
    "gemini": 4.0,
    "deepseek": 4.0,
    "default": 4.0,
}

# tiktoken encodings by model family
_OPENAI_ENCODINGS: dict[str, str] = {
    "gpt-5": "o200k_base",
    "gpt-4": "o200k_base",
    "o1": "o200k_base",
    "o3": "o200k_base",
}


def count_tokens(text: str, model: str) -> tuple[int, str]:
    """
    Returns (token_count, accuracy) where accuracy is "exact" or "estimated±10%".
    Uses tiktoken for OpenAI models, character ratio heuristic for others.
    """
    model_lower = model.lower()

    for prefix, encoding_name in _OPENAI_ENCODINGS.items():
        if model_lower.startswith(prefix):
            return _count_with_tiktoken(text, encoding_name), "exact"

    for provider, ratio in _CHARS_PER_TOKEN.items():
        if provider == "default":
            continue
        if model_lower.startswith(provider):
            return _count_with_ratio(text, ratio), "estimated±10%"

    return _count_with_ratio(text, _CHARS_PER_TOKEN["default"]), "estimated±10%"


def _count_with_tiktoken(text: str, encoding_name: str) -> int:
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        # fall back to ratio if tiktoken fails
        return _count_with_ratio(text, _CHARS_PER_TOKEN["default"])


def _count_with_ratio(text: str, chars_per_token: float) -> int:
    return max(1, int(len(text) / chars_per_token))
