__version__ = "0.2.1"

import llmzip.i18n as i18n

# Initialize i18n with system locale at import time.
# Can be overridden via --lang flag or LLMZIP_LANG env var.
i18n.configure()
