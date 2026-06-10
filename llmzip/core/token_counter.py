from functools import lru_cache

import tiktoken

# chars per token ratios for non-OpenAI models (approximation)
_CHARS_PER_TOKEN: dict[str, float] = {
    "claude": 3.5,
    "gemini": 4.0,
    "deepseek": 4.0,
    "default": 4.0,
}

@lru_cache(maxsize=32)
def _get_encoding(model: str) -> tiktoken.Encoding | None:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return None

def count_tokens(
    text: str, 
    model: str, 
    cache: dict[str, int] | None = None
) -> tuple[int, str]:
    """
    Returns (token_count, accuracy) where accuracy is "exact" or "estimated±10%".
    Uses tiktoken for OpenAI models, character ratio heuristic for others.
    Optionally accepts a temporary cache dict to avoid re-tokenizing identical text 
    for models that share the same encoding family.
    """
    model_lower = model.lower()
    enc = _get_encoding(model_lower)

    # Tiktoken (Exact)
    if enc is not None:
        if cache is not None and enc.name in cache:
            return cache[enc.name], "exact"
            
        count = max(1, len(enc.encode(text)))
        if cache is not None:
            cache[enc.name] = count
        return count, "exact"

    # Heuristic Fallback (Estimated)
    for provider, ratio in _CHARS_PER_TOKEN.items():
        if provider == "default":
            continue
        if model_lower.startswith(provider):
            if cache is not None and provider in cache:
                return cache[provider], "estimated±10%"
                
            count = _count_with_ratio(text, ratio)
            if cache is not None:
                cache[provider] = count
            return count, "estimated±10%"

    # Default Heuristic
    if cache is not None and "default" in cache:
        return cache["default"], "estimated±10%"
        
    count = _count_with_ratio(text, _CHARS_PER_TOKEN["default"])
    if cache is not None:
        cache["default"] = count
    return count, "estimated±10%"

def _count_with_ratio(text: str, chars_per_token: float) -> int:
    return max(1, int(len(text) / chars_per_token))
