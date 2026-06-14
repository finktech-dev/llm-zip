import typing
import pytest

from llmzip.core.semantic_scorer import _chunk_text, _cosine_similarity


def test_chunk_text_short_text_returns_single_chunk() -> None:
    text = "short text"
    chunks = _chunk_text(text, chunk_size=256, overlap=32)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long_text_splits_correctly() -> None:
    text = " ".join(["word"] * 600)
    chunks = _chunk_text(text, chunk_size=256, overlap=32)
    assert len(chunks) > 1


def test_chunk_text_overlap_produces_shared_words() -> None:
    text = " ".join([str(i) for i in range(300)])
    chunks = _chunk_text(text, chunk_size=100, overlap=20)
    # last word of chunk N should appear in chunk N+1
    last_word = chunks[0].split()[-1]
    assert last_word in chunks[1].split()


def test_cosine_similarity_identical_vectors() -> None:
    import numpy as np
    v = np.array([1.0, 2.0, 3.0])
    assert _cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_orthogonal_vectors() -> None:
    import numpy as np
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_vector_returns_zero() -> None:
    import numpy as np
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 2.0])
    assert _cosine_similarity(a, b) == 0.0
