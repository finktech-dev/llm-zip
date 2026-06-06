import configparser
import sys
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(".llmzip.config")

_REQUIRED = {
    "server": ["MAX_TOKENS", "MIN_TOKENS_TO_COMPRESS"],
    "compression": ["DEFAULT_RATIO", "DEFAULT_MODEL"],
}


@dataclass
class AppConfig:
    port: int
    max_tokens: int
    min_tokens_to_compress: int
    default_ratio: float
    default_model: str
    max_batch_size: int
    batch_workers: int
    compression_model: str
    pricing_cache_ttl: int
    rate_limit_enabled: bool
    rate_limit_rpm: int
    rate_limit_rpd: int
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
    parser.read(CONFIG_PATH)

    _validate_required(parser)

    try:
        ratio = float(parser["compression"]["DEFAULT_RATIO"])
        if not (0.1 <= ratio <= 0.9):
            _fail(f"DEFAULT_RATIO must be between 0.1 and 0.9, got: {ratio}")

        compression_model = parser["compression"].get("COMPRESSION_MODEL", "bert-base")
        if compression_model not in ("bert-base", "xlm-roberta-large"):
            _fail(
                f"COMPRESSION_MODEL must be 'bert-base' or 'xlm-roberta-large', "
                f"got: {compression_model}"
            )

        return AppConfig(
            port=int(parser["server"].get("PORT", "8000")),
            max_tokens=int(parser["server"]["MAX_TOKENS"]),
            min_tokens_to_compress=int(
                parser["server"].get("MIN_TOKENS_TO_COMPRESS", "500")
            ),
            default_ratio=ratio,
            default_model=parser["compression"]["DEFAULT_MODEL"],
            max_batch_size=int(parser["compression"].get("MAX_BATCH_SIZE", "25")),
            batch_workers=int(parser["compression"].get("BATCH_WORKERS", "4")),
            compression_model=compression_model,
            pricing_cache_ttl=int(parser["pricing"].get("CACHE_TTL", "3600")),
            rate_limit_enabled=parser["rate_limit"].get("ENABLED", "false").lower()
            == "true",
            rate_limit_rpm=int(
                parser["rate_limit"].get("REQUESTS_PER_MINUTE", "60")
            ),
            rate_limit_rpd=int(
                parser["rate_limit"].get("REQUESTS_PER_DAY", "10000")
            ),
            file_conversion_enabled=parser["features"]
            .get("FILE_CONVERSION", "true")
            .lower()
            == "true",
            lang=parser["cli"].get("LANG", "").strip() if parser.has_section("cli") else "",
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
