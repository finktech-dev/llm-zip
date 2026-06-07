# core/featured_models.py
# Single source of truth for featured models list.
# Import this in savings_calculator.py and compress_cmd.py instead of maintaining separate copies.

FEATURED_MODELS: list[str] = [
    "gpt-4o-mini",
    "gpt-5.4-nano",
    "gemini-2.5-flash-lite",
    "deepseek-v4-flash",
    "gpt-5.4-mini",
    "claude-haiku-4-5",
    "gemini-2.5-flash",
    "claude-sonnet-4-6",
    "gpt-5.4",
]