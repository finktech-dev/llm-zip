# llmzip/core/ignore.py
import fnmatch
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_IGNORE_FILES = [".llmzipignore", ".llmzipignore.local"]


def _load_patterns() -> list[str]:
    patterns: list[str] = []
    for fname in _IGNORE_FILES:
        p = Path(fname)
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
            except Exception as e:
                logger.warning("Could not read ignore file %s: %s", fname, e)
    return patterns


_patterns: list[str] | None = None


def reload_patterns() -> None:
    """Force re-loading patterns from disk (useful for testing)."""
    global _patterns
    _patterns = _load_patterns()


def _get_patterns() -> list[str]:
    global _patterns
    if _patterns is None:
        reload_patterns()
    return _patterns if _patterns is not None else []


def should_skip(text: str, filename: str | None = None) -> bool:
    """
    Returns True if the text or filename matches any ignore pattern.
    Patterns are matched against the filename (if provided) using fnmatch glob rules.
    Text-based matching checks if the text starts with any pattern line (for system prompts).
    """
    for pattern in _get_patterns():
        if filename and fnmatch.fnmatch(filename, pattern):
            logger.debug("Skipping '%s' — matches ignore pattern '%s'", filename, pattern)
            return True
        # Text prefix match for system prompts (e.g. "You are an expert*")
        if pattern.endswith("*") and text.startswith(pattern[:-1]):
            logger.debug("Skipping text — matches ignore pattern '%s'", pattern)
            return True
    return False
