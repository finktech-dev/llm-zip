import logging
import json
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        # Add extra fields if they exist, filtering out stdlib attributes
        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'funcName', 
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message', 'msg', 'name', 
            'pathname', 'process', 'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key != 'event':
                log_record[key] = value
        return json.dumps(log_record)

class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[96m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[1;91m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = f"[%(asctime)s] {self.COLORS.get(record.levelname, '')}%(levelname)-5s{self.RESET} %(name)s  %(message)s"
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def setup_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger("llmzip")
    if root_logger.handlers: return # Already configured

    actual_log_level = os.environ.get("LOG_LEVEL", log_level)
    root_logger.setLevel(actual_log_level)

    # Stream Handler (Human)
    if os.environ.get("LOG_JSON", "false").lower() == "false":
        console = logging.StreamHandler()
        console.setFormatter(ColorFormatter())
        root_logger.addHandler(console)

    # Rotating File Handler (JSON)
    log_file = os.environ.get("LOG_FILE", "logs/llmzip.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # Silence noise
    for name in ["httpx", "httpcore", "llmlingua", "sentence_transformers", "transformers", "torch"]:
        logging.getLogger(name).setLevel(logging.WARNING)
