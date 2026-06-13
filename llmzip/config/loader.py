import configparser
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

CONFIG_PATH = Path(".llmzip.config")

_REQUIRED = {
    "server": ["MAX_TOKENS", "MIN_TOKENS_TO_COMPRESS"],
    "compression": ["DEFAULT_RATIO", "DEFAULT_MODEL"],
}


@dataclass
class AppConfig:
    port: int
    api_key: str | None
    deploy_mode: str
    models_url: str
    max_tokens: int
    min_tokens_to_compress: int
    default_ratio: float
    default_model: str
    max_batch_size: int
    batch_workers: int
    chunk_size: int
    compression_model: str
    scorer_model: str
    scorer_timeout: int
    pricing_cache_ttl: int
    cache_dir: Path | None
    rate_limit_enabled: bool
    rate_limit_rpm: int
    rate_limit_rpd: int
    max_file_size_mb: int
    file_conversion_enabled: bool
    lang: str


def load() -> AppConfig:
    # i18n not yet configured at this point — use raw English strings for bootstrap errors
    if not CONFIG_PATH.exists():
        _fail(
            f"Config file not found: {CONFIG_PATH}\n"
            f"  Run: cp .llmzip.config.example .llmzip.config\n"
            f"  Then fill in the required values."
        )

    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")

    _validate_required(parser)

    try:
        ratio = float(parser["compression"]["DEFAULT_RATIO"])
        if not (0.1 <= ratio <= 0.9):
            _fail(f"DEFAULT_RATIO must be between 0.1 and 0.9, got: {ratio}")

        compression_model = parser.get("compression", "COMPRESSION_MODEL", fallback="bert-base")
        if compression_model not in ("bert-base", "xlm-roberta-large"):
            _fail(
                f"COMPRESSION_MODEL must be 'bert-base' or 'xlm-roberta-large', "
                f"got: {compression_model}"
            )

        api_key_val = parser.get("server", "API_KEY", fallback="").strip()
        api_key = api_key_val if api_key_val else None

        deploy_mode = os.environ.get(
            "DEPLOY_MODE",
            parser.get("server", "DEPLOY_MODE", fallback="monolith")
        ).lower()
        # Environment variable takes precedence for container linking
        models_url = os.environ.get(
            "MODELS_URL", 
            parser.get("server", "MODELS_URL", fallback="http://llmzip-models:8001")
        ).strip()

        return AppConfig(
            port=int(parser.get("server", "PORT", fallback="8000")),
            api_key=api_key,
            deploy_mode=deploy_mode,
            models_url=models_url,
            max_tokens=int(parser["server"]["MAX_TOKENS"]),
            min_tokens_to_compress=int(
                parser.get("server", "MIN_TOKENS_TO_COMPRESS", fallback="500")
            ),
            default_ratio=ratio,
            default_model=parser["compression"]["DEFAULT_MODEL"],
            max_batch_size=int(parser.get("compression", "MAX_BATCH_SIZE", fallback="25")),
            batch_workers=int(parser.get("compression", "BATCH_WORKERS", fallback="4")),
            chunk_size=int(parser.get("compression", "CHUNK_SIZE", fallback="400")),
            compression_model=compression_model,
            scorer_model=parser.get(
                "compression",
                "SCORER_MODEL",
                fallback="paraphrase-multilingual-MiniLM-L12-v2",
            ),
            scorer_timeout=int(parser.get("compression", "SCORER_TIMEOUT", fallback="30")),
            pricing_cache_ttl=int(parser.get("pricing", "CACHE_TTL", fallback="3600")),
            cache_dir=Path(
                os.environ.get(
                    "LLMZIP_CACHE_DIR",
                    parser.get("storage", "CACHE_DIR", fallback=""),
                )
            ) if os.environ.get("LLMZIP_CACHE_DIR") or parser.get("storage", "CACHE_DIR", fallback="") else None,
            rate_limit_enabled=parser.get("rate_limit", "ENABLED", fallback="false").lower()
            == "true",
            rate_limit_rpm=int(
                parser.get("rate_limit", "REQUESTS_PER_MINUTE", fallback="60")
            ),
            rate_limit_rpd=int(
                parser.get("rate_limit", "REQUESTS_PER_DAY", fallback="10000")
            ),
            max_file_size_mb=int(parser.get("server", "MAX_FILE_SIZE_MB", fallback="50")),
            file_conversion_enabled=parser.get("features", "FILE_CONVERSION", fallback="true")
            .lower()
            == "true",
            lang=parser.get("cli", "LANG", fallback="").strip(),
        )
    except ValueError as exc:
        _fail(f"Invalid config value: {exc}")


def _validate_required(parser: configparser.ConfigParser) -> None:
    missing: list[str] = []
    for section, keys in _REQUIRED.items():
        for key in keys:
            value = parser.get(section, key, fallback="").strip()
            if not value:
                missing.append(f"  [{section}] {key}")

    if missing:
        _fail(
            "Missing required config values:\n"
            + "\n".join(missing)
            + "\n\n  Edit .llmzip.config and fill in the missing values."
        )


def _fail(message: str) -> NoReturn:
    print(f"\n❌ LLMZip config error:\n   {message}\n", file=sys.stderr)
    sys.exit(1)
