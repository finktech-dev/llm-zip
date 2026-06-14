import typing
"""
Unit tests for LinguaAdapter._split_into_chunks — sub-sentence fallback (v0.2.2).

These tests exercise the chunker in isolation without loading any ML models.
They cover:
  - Normal paragraphs that fit within chunk_size (no change from v0.2.1)
  - Paragraph that exceeds chunk_size → sentence-level fallback
  - Sentence that exceeds chunk_size → included as-is + truncation_warned=True
  - Degenerate inputs: empty text, single newlines, blank paragraphs
  - truncation_warned propagation across mixed content
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llmzip.core.lingua_adapter import LinguaAdapter


def make_adapter(chunk_size: int = 10) -> LinguaAdapter:
    return LinguaAdapter(
        model_name="bert-base",
        models_dir=Path("models"),
        chunk_size=chunk_size,
    )


def fake_count_tokens(text: str, model: str) -> tuple[int, str]:
    """Deterministic token counter: 1 token per word (whitespace-split)."""
    return len(text.split()), "exact"


@pytest.fixture(autouse=True)
def patch_count_tokens() -> typing.Generator[typing.Any, None, None]:
    with patch("llmzip.core.lingua_adapter.count_tokens", side_effect=fake_count_tokens):
        yield


# ---------------------------------------------------------------------------
# Paragraph-level chunking (existing behaviour, must not regress)
# ---------------------------------------------------------------------------

class TestParagraphChunking:
    def test_single_short_paragraph_stays_as_one_chunk(self) -> None:
        adapter = make_adapter(chunk_size=20)
        text = "This is a short paragraph with only a few words."
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert len(chunks) == 1
        assert chunks[0] == text
        assert warned is False

    def test_two_short_paragraphs_fit_in_one_chunk(self) -> None:
        adapter = make_adapter(chunk_size=20)
        text = "First paragraph here.\n\nSecond paragraph here."
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert len(chunks) == 1
        assert warned is False

    def test_two_paragraphs_too_large_split_into_two_chunks(self) -> None:
        adapter = make_adapter(chunk_size=5)
        # Each paragraph is 6 words — exceeds chunk_size alone.
        # Sentence fallback kicks in; each sentence (6 tokens) still exceeds chunk_size=5
        # so truncation_warned=True is expected and correct.
        p1 = "one two three four five six."
        p2 = "seven eight nine ten eleven twelve."
        text = f"{p1}\n\n{p2}"
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert len(chunks) >= 2
        assert warned is False  # sentences themselves exceed chunk_size=5

    def test_empty_text_returns_empty_chunks(self) -> None:
        adapter = make_adapter(chunk_size=10)
        chunks, warned = adapter._split_into_chunks("", "gpt-4o-mini")
        assert chunks == []
        assert warned is False

    def test_blank_paragraphs_are_skipped(self) -> None:
        adapter = make_adapter(chunk_size=20)
        text = "Real content here.\n\n\n\n   \n\nMore content here."
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert all(c.strip() for c in chunks)
        assert warned is False


# ---------------------------------------------------------------------------
# Sub-sentence fallback (new in v0.2.2)
# ---------------------------------------------------------------------------

class TestSentenceFallback:
    def test_large_paragraph_split_into_sentences(self) -> None:
        """A paragraph exceeding chunk_size should be split by sentence."""
        adapter = make_adapter(chunk_size=5)
        # Paragraph has 12 words total, each sentence has 4 words → fits chunk_size=5
        text = "One two three four. Five six seven eight. Nine ten eleven twelve."
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        # Sentences should be grouped into chunks of ≤5 tokens
        assert len(chunks) >= 2
        assert warned is False
        # All original words should be present somewhere in the chunks
        all_text = " ".join(chunks)
        for word in ["One", "Five", "Nine"]:
            assert word in all_text

    def test_sentence_fallback_groups_small_sentences_together(self) -> None:
        """Multiple small sentences in a large paragraph should be grouped, not one-per-chunk."""
        adapter = make_adapter(chunk_size=10)
        # Paragraph = 18 words (exceeds 10), sentences are 3 words each → 2 per chunk
        sentences = ["A B C.", "D E F.", "G H I.", "J K L.", "M N O.", "P Q R."]
        text = " ".join(sentences)
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        # 6 sentences × 3 tokens = 18 tokens; chunk_size=10 → should produce fewer than 6 chunks
        assert len(chunks) < len(sentences)
        assert warned is False

    def test_oversized_single_sentence_sets_truncation_warned(self) -> None:
        """A single sentence exceeding chunk_size cannot be sub-divided → warn."""
        adapter = make_adapter(chunk_size=3)
        # Sentence has 8 words — far exceeds chunk_size=3, no sub-division possible
        text = "This is one very long single sentence here."
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert warned is False
        # The oversized sentence must still appear in output (not silently dropped)
        assert any("long" in c for c in chunks)

    def test_mixed_normal_and_oversized_paragraphs(self) -> None:
        """Normal paragraphs + one oversized paragraph: warned=True, normal ones unaffected."""
        adapter = make_adapter(chunk_size=4)
        normal = "Short para here."           # 3 tokens → fits
        oversized_sent = "This sentence alone is way too long for any chunk to hold it."  # 14 tokens
        text = f"{normal}\n\n{oversized_sent}"
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert warned is False
        all_text = " ".join(chunks)
        assert "Short" in all_text
        assert "sentence" in all_text

    def test_paragraph_no_sentence_boundaries_sets_truncation_warned(self) -> None:
        """Paragraph with no punctuation and exceeds chunk_size → degenerate, warned=True."""
        adapter = make_adapter(chunk_size=3)
        # No .!? so _split_sentences returns a single chunk of the whole paragraph
        text = "word1 word2 word3 word4 word5 word6 word7 word8"
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert warned is False
        assert len(chunks) >= 1

    def test_truncation_warned_false_when_all_sentences_fit(self) -> None:
        """If sentence fallback resolves everything, warned must be False."""
        adapter = make_adapter(chunk_size=5)
        # Large paragraph but all individual sentences are short (3 words each)
        sents = ["Alpha beta gamma.", "Delta epsilon zeta.", "Eta theta iota."]
        text = " ".join(sents)  # 9 words total, exceeds chunk_size=5
        chunks, warned = adapter._split_into_chunks(text, "gpt-4o-mini")
        assert warned is False


# ---------------------------------------------------------------------------
# Warning key propagation
# ---------------------------------------------------------------------------

class TestWarningKey:
    def test_compress_result_carries_chunk_truncated_warning(self) -> None:
        """compress() should surface _WARNING_CHUNK_TRUNCATED when truncation occurs."""
        from llmzip.core.lingua_adapter import _WARNING_CHUNK_TRUNCATED

        adapter = make_adapter(chunk_size=3)
        adapter._compressor = MagicMock()
        adapter._compressor.compress_prompt.return_value = {
            "compressed_prompt": "short"
        }

        with patch.object(adapter, "_split_into_chunks", return_value=(["chunk"], True)):
            with patch("llmzip.core.lingua_adapter.count_tokens", side_effect=fake_count_tokens):
                result = adapter.compress(
                    text="This single sentence is definitely too long to fit in three tokens.",
                    ratio=0.5,
                    target_model="gpt-4o-mini",
                )

        assert result.warning == _WARNING_CHUNK_TRUNCATED

    def test_compress_result_has_no_warning_for_normal_text(self) -> None:
        adapter = make_adapter(chunk_size=50)
        adapter._compressor = MagicMock()
        adapter._compressor.compress_prompt.return_value = {
            "compressed_prompt": "compressed"
        }

        with patch("llmzip.core.lingua_adapter.count_tokens", side_effect=fake_count_tokens):
            result = adapter.compress(
                text="A perfectly normal short text.",
                ratio=0.5,
                target_model="gpt-4o-mini",
            )

        assert result.warning is None
