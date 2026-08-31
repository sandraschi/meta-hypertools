import datetime
import logging
import sys
from collections import deque

import structlog

#  SOTA Bash Standards (v1.4)

# Action markers with safe fallbacks for Windows non-UTF8 terminals
BASH_ICONS = {
    "START": "\U0001f680",
    "BUILD": "\U0001f527",
    "SUCCESS": "\u2705",
    "ERROR": "\u274c",
    "STEP": "\u2794",
    "ACTION": "\u26a1",
    "SCAN": "\U0001f50d",
    "SECURITY": "\U0001f6e1\ufe0f",
    "BENNY": "\U0001f32d",
}

BASH_FALLBACKS = {
    "START": "[START]",
    "BUILD": "[BUILD]",
    "SUCCESS": "[  OK ]",
    "ERROR": "[FAIL ]",
    "STEP": "  ->",
    "ACTION": "[ACT  ]",
    "SCAN": "[SCAN ]",
    "SECURITY": "[SEC  ]",
    "BENNY": "[WURST]",
}


def get_icon(key: str) -> str:
    """Get emoji or fallback based on terminal encoding."""
    encoding = sys.stdout.encoding or "ascii"
    if encoding.lower() in ("utf-8", "utf8"):
        return BASH_ICONS.get(key, "")
    return BASH_FALLBACKS.get(key, "[*]")


#  Memory Telemetry

_MAX_MEMORY_LOGS = 1000
_memory_logs: deque[dict] = deque(maxlen=_MAX_MEMORY_LOGS)

_entry_counter = 0


class MemoryLogHandler(logging.Handler):
    """Stores recent logs for webapp telemetry."""

    def emit(self, record: logging.LogRecord) -> None:
        global _entry_counter
        try:
            _entry_counter += 1
            entry = {
                "id": f"{record.created:.6f}.{_entry_counter}",
                "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "kind": record.name,
                "detail": record.getMessage(),
                "module": record.module,
                "lineno": record.lineno,
                "meta": {"module": record.module, "lineno": record.lineno},
            }
            _memory_logs.append(entry)
        except Exception:
            self.handleError(record)


def get_recent_logs(limit: int = 50) -> list[dict]:
    """Return buffered logs for API telemetry (legacy compat)."""
    return list(_memory_logs)[-limit:]


#  SOTA Formatter


class SOTABashFormatter(logging.Formatter):
    """High-fidelity 'Print Bashing' formatter for industrial telemetry."""

    def format(self, record: logging.LogRecord) -> str:
        icon = ""
        msg = record.getMessage()

        # In-message icon mapping (e.g. "Process Server starting")
        for key in BASH_ICONS:
            placeholder = f":{key}:"
            if placeholder in msg:
                msg = msg.replace(placeholder, get_icon(key))
                break

        # Level-based icon injection
        if record.levelno >= logging.ERROR:
            icon = f"{get_icon('ERROR')} "
        elif record.levelno >= logging.WARNING:
            icon = f"{get_icon('SECURITY')} "
        elif "starting" in msg.lower() or "initializing" in msg.lower():
            icon = f"{get_icon('START')} "
        elif "success" in msg.lower() or "completed" in msg.lower():
            icon = f"{get_icon('SUCCESS')} "

        record.msg = f"{icon}{msg}"
        record.args = ()  # Clear args so super().format doesn't re-interpolate
        return super().format(record)


#  Configuration


def setup_logging(log_level: str = "INFO") -> None:
    """Configure industrialized logging stack."""
    log_level = log_level.upper()

    # Root logger configuration
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = []

    # Console Handler (High-Fidelity Bashing)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, log_level))
    formatter = SOTABashFormatter("%(asctime)s | %(levelname)-8s | %(name)s - %(message)s")
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Memory Handler (Telemetry)
    memory_handler = MemoryLogHandler()
    memory_handler.setLevel(logging.DEBUG)
    root.addHandler(memory_handler)

    # Structlog integration
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a standardized SOTA logger."""
    return structlog.get_logger(name)
