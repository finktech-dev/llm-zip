import typing
from llmzip.i18n import configure, t


def test_i18n_translation_keys() -> None:
    configure("en")
    assert t("pricing.accuracy.exact") == "exact"
    
    configure("es")
    assert t("pricing.accuracy.exact") == "exacto"
    
    configure("pt")
    assert t("pricing.accuracy.exact") == "exato"

def test_i18n_warning_translations() -> None:
    key = "compress.warning.chunk_truncated"
    
    configure("en")
    assert "truncated" in t(key).lower()
    
    configure("es")
    val_es = t(key).lower()
    assert val_es != key.lower()
    # Accept both "truncado" or "truncó"
    assert "trunc" in val_es

def test_i18n_fallback() -> None:
    configure("es")
    assert t("non.existent.key") == "non.existent.key"
