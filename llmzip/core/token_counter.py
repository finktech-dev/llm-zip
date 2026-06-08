import tiktoken

# chars per token ratios for non-OpenAI models (approximation)
_CHARS_PER_TOKEN: dict[str, float] = {
    "claude": 3.5,
    "gemini": 4.0,
    "deepseek": 4.0,
    "default": 4.0,
}


def count_tokens(text: str, model: str) -> tuple[int, str]:
    """
    Returns (token_count, accuracy) where accuracy is "exact" or "estimated±10%".
    Uses tiktoken for OpenAI models, character ratio heuristic for others.
    """
    model_lower = model.lower()

    # Try tiktoken first (accurate for OpenAI models)
    try:
        enc = tiktoken.encoding_for_model(model_lower)
        count = len(enc.encode(text))
        return max(1, count), "exact"
    except Exception:
        # Fall back to provider-based ratio if model is unknown to tiktoken
        pass

    for provider, ratio in _CHARS_PER_TOKEN.items():
        if provider == "default":
            continue
        if model_lower.startswith(provider):
            return _count_with_ratio(text, ratio), "estimated±10%"

    return _count_with_ratio(text, _CHARS_PER_TOKEN["default"]), "estimated±10%"


def _count_with_ratio(text: str, chars_per_token: float) -> int:
    return max(1, int(len(text) / chars_per_token))
