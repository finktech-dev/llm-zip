#!/usr/bin/env python3
"""
llm-zip project scaffold
Creates all directories and placeholder files.
Run once after cloning: python scripts/scaffold.py
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

DIRS = [
    # core business logic
    "llmzip/core",
    "llmzip/pricing",
    "llmzip/conversion",
    "llmzip/config",
    # api
    "llmzip/api/routes",
    # cli
    "llmzip/cli",
    # tests mirror llmzip structure
    "tests/core",
    "tests/pricing",
    "tests/conversion",
    "tests/config",
    "tests/api",
    "tests/cli",
    # scripts
    "scripts",
    # docker
    "docker",
]

FILES = [
    # package inits
    "llmzip/__init__.py",
    "llmzip/core/__init__.py",
    "llmzip/pricing/__init__.py",
    "llmzip/conversion/__init__.py",
    "llmzip/config/__init__.py",
    "llmzip/api/__init__.py",
    "llmzip/api/routes/__init__.py",
    "llmzip/cli/__init__.py",
    # core
    "llmzip/core/lingua_adapter.py",
    "llmzip/core/semantic_scorer.py",
    "llmzip/core/token_counter.py",
    "llmzip/core/savings_calculator.py",
    # pricing
    "llmzip/pricing/fetcher.py",
    "llmzip/pricing/fallback.py",
    "llmzip/pricing/resolver.py",
    # conversion
    "llmzip/conversion/file_converter.py",
    # config
    "llmzip/config/loader.py",
    # api
    "llmzip/api/app.py",
    "llmzip/api/schemas.py",
    "llmzip/api/routes/compress.py",
    "llmzip/api/routes/compress_file.py",
    "llmzip/api/routes/models.py",
    "llmzip/api/routes/health.py",
    # cli
    "llmzip/cli/compress_cmd.py",
    "llmzip/cli/prices_cmd.py",
    # tests
    "tests/__init__.py",
    "tests/core/__init__.py",
    "tests/core/test_lingua_adapter.py",
    "tests/core/test_semantic_scorer.py",
    "tests/core/test_token_counter.py",
    "tests/core/test_savings_calculator.py",
    "tests/pricing/__init__.py",
    "tests/pricing/test_resolver.py",
    "tests/conversion/__init__.py",
    "tests/conversion/test_file_converter.py",
    "tests/config/__init__.py",
    "tests/config/test_loader.py",
    "tests/api/__init__.py",
    "tests/api/test_compress.py",
    "tests/api/test_compress_file.py",
    "tests/api/test_health.py",
    "tests/cli/__init__.py",
    "tests/cli/test_compress_cmd.py",
]

GITKEEP_DIRS = [
    "docker",
    "scripts",
]


def scaffold() -> None:
    created_dirs = 0
    created_files = 0

    for dir_path in DIRS:
        full = ROOT / dir_path
        full.mkdir(parents=True, exist_ok=True)
        created_dirs += 1

    for dir_path in GITKEEP_DIRS:
        gitkeep = ROOT / dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    for file_path in FILES:
        full = ROOT / file_path
        if not full.exists():
            full.touch()
            created_files += 1

    print(f"✓ {created_dirs} directories ready")
    print(f"✓ {created_files} files created")
    print()
    print("Next steps:")
    print("  1. cp .llmzip.config.example .llmzip.config")
    print("  2. cp .llmzipignore.example .llmzipignore")
    print("  3. cp .llmzipignore.local.example .llmzipignore.local")
    print("  4. docker-compose run llmzip download-models")
    print("  5. docker-compose up")


if __name__ == "__main__":
    scaffold()
