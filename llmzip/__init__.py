from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("llm-zip")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

import llmzip.i18n as i18n

# Initialize i18n with system locale at import time.
# Can be overridden via --lang flag or LLMZIP_LANG env var.
i18n.configure()
