# llmzip/core/ignore.py
import fnmatch
import logging
import threading
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
_patterns_lock = threading.Lock()


def _get_patterns() -> list[str]:
    """Return cached patterns, loading from disk on first call.

    Uses double-checked locking so that BATCH_WORKERS=N threads don't all
    race to read the ignore files simultaneously on startup. CPython's GIL
    makes the bare assignment atomic, but the three disk reads are not — this
    lock eliminates the redundant I/O without affecting the hot path.
    """
    global _patterns
    if _patterns is None:
        with _patterns_lock:
            if _patterns is None:  # second check inside lock
                _patterns = _load_patterns()
    return _patterns if _patterns is not None else []


def reload_patterns() -> None:
    """Invalidate the pattern cache. Useful in tests without module hackery."""
    global _patterns
    with _patterns_lock:
        _patterns = None


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
