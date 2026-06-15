import pytest

import llmzip.core.ignore as ignore_mod


@pytest.fixture(autouse=True)
def reset_ignore_patterns() -> None:
    """Ensure the global ignore patterns cache is reset before and after every test."""
    ignore_mod._patterns = None
    yield
    ignore_mod._patterns = None
