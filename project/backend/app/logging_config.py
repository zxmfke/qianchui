"""Production-grade logging configuration.

Supports two output modes controlled by LOG_FORMAT env:
  - "text"  (default, dev-friendly colored output)
  - "json"  (machine-readable structured JSON, for production / ELK / Loki)

Optionally writes to a rotating log file via LOG_FILE env.
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        for attr in ("request_id", "method", "path", "status_code", "duration_ms",
                      "user_id", "enterprise_id", "client_ip",
                      "llm_provider", "llm_model", "prompt_tokens", "completion_tokens",
                      "total_tokens", "llm_latency_ms"):
            val = getattr(record, attr, None)
            if val is not None:
                log_entry[attr] = val

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColorTextFormatter(logging.Formatter):
    """Colored text formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"
    DIM = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]

        parts = [
            f"{self.DIM}{ts}{self.RESET}",
            f"{color}{record.levelname:<7s}{self.RESET}",
            f"{self.DIM}{record.name}{self.RESET}",
            record.getMessage(),
        ]

        extras = []
        for attr in ("method", "path", "status_code", "duration_ms",
                      "user_id", "client_ip",
                      "llm_provider", "llm_model", "total_tokens", "llm_latency_ms"):
            val = getattr(record, attr, None)
            if val is not None:
                extras.append(f"{attr}={val}")
        if extras:
            parts.append(f"{self.DIM}[{', '.join(extras)}]{self.RESET}")

        msg = " ".join(parts)
        if record.exc_info and record.exc_info[1]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


def setup_logging(log_level: str = "INFO", log_format: str = "text", log_file: str = "") -> None:
    """Configure the root logger for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = ColorTextFormatter()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)

    for noisy in ("httpx", "httpcore", "hpack", "urllib3", "asyncio",
                   "watchfiles", "multipart", "openai._base_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
