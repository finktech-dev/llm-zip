import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

from llmzip.core.lingua_adapter import LinguaAdapter


def test_chunker_sliding_window_fallback() -> None:
    # Test text with no paragraphs, sentences or lines to force sliding window
    long_unstructured_text = "word" * 2000 
    
    with patch("llmzip.core.lingua_adapter.LinguaAdapter.load", return_value=None):
        adapter = LinguaAdapter(
            model_name="bert-base",
            models_dir=Path("models"),
            chunk_size=400
        )
        
        # Patching _compressor since it's used in compress() after split_into_chunks
        adapter._compressor = MagicMock()
        adapter._compressor.compress_prompt.return_value = {"compressed_prompt": "compressed"}
        
        # This triggers the cascading logic and calls split_into_chunks -> sliding_window
        res = adapter.compress(long_unstructured_text, 0.5, "gpt-4o")
        
        assert "compressed" in res.compressed_text
        assert adapter._compressor.compress_prompt.called

def test_chunker_very_long_sentences() -> None:
    # Paragraphs exist but sentences are huge
    text = ("sentence " * 600) + "\n\n" + ("another " * 600)
    
    with patch("llmzip.core.lingua_adapter.LinguaAdapter.load", return_value=None):
        adapter = LinguaAdapter(model_name="bert-base", models_dir=Path("models"))
        adapter._compressor = MagicMock()
        adapter._compressor.compress_prompt.return_value = {"compressed_prompt": "..."}
        
        res = adapter.compress(text, 0.5, "gpt-4o")
        assert res.compressed_text is not None
