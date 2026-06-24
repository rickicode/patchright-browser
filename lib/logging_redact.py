"""Structured logging with sensitive data redaction for patchright-mcp-bridge."""
from __future__ import annotations

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

# ---------- redaction ----------

# Patterns that indicate sensitive data. Match is greedy to next quote/space/end.
_PATTERNS = [
    # password-like fields
    (re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*"?([^"\s,}]+)'), r"\1=<redacted>"),
    # token-like fields
    (re.compile(r'(?i)(token|access_token|refresh_token|api_key|secret)\s*[=:]\s*"?([^"\s,}]+)"?'), r"\1=<redacted>"),
    # Authorization: Bearer xxx
    # Authorization: Bearer <token>
    (re.compile(r"(?i)(Authorization:\s*Bearer\s+)([A-Za-z0-9._\-+/=]+)"), r"\1<redacted>"),
    # Standalone Bearer token (in body text)
    (re.compile(r"\bBearer\s+([A-Za-z0-9._\-+/=]{16,})\b"), "Bearer <redacted>"),
    # sk-..., ghp_..., AKIA..., key-...
    (re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"), "<api-key-redacted>"),
    (re.compile(r"\b(ghp_[A-Za-z0-9]{20,})\b"), "<github-pat-redacted>"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "<aws-key-redacted>"),
    # OTP-like: "code" "123456" or "otp=123456" (4-8 digits)
    (re.compile(r'(?i)(code|otp|pin|verification)\s*[=:]\s*"?(\d{4,8})"?'), r"\1=<otp-redacted>"),
    # Cookie value: "session=abc123def456"
    (re.compile(r'(?i)(session|sid|jwt)\s*[=:]\s*"?([A-Za-z0-9._\-]{16,})"?'), r"\1=<cookie-redacted>"),
]


def redact(text: str) -> str:
    """Apply all redaction patterns to a string. Returns sanitized copy."""
    if not isinstance(text, str):
        text = str(text)
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


class RedactFilter(logging.Filter):
    """Logging filter that redacts any %-formatted args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            else:
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        record.msg = redact(record.msg)
        return True


# ---------- setup ----------


def setup_logging(log_path: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with rotating file + stderr handler. Returns logger.

    Default log path: ~/.patchright-mcp/logs/bridge.log
    """
    if log_path is None:
        root = os.environ.get("PATCHRIGHT_MCP_HOME") or os.path.expanduser("~/.patchright-mcp")
        log_path = os.environ.get("PATCHRIGHT_BRIDGE_LOG") or os.path.join(root, "logs", "bridge.log")

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger = logging.getLogger("patchright_bridge")
    logger.setLevel(level)
    logger.propagate = False  # don't double-log via root

    # Avoid double-setup
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03dZ %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    fmt.converter = __import__("time").gmtime  # UTC timestamps

    redactor = RedactFilter()

    # Rotating file
    fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.addFilter(redactor)
    logger.addHandler(fh)

    # Stderr (also redacted)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.addFilter(redactor)
    logger.addHandler(sh)

    return logger


def log_tool_call(logger: logging.Logger, profile: str, tool: str, args_summary: str,
                   duration_ms: int | None = None, error: str | None = None) -> None:
    """Standard tool-call log line."""
    if error:
        logger.error(f"[{profile}] {tool} FAILED duration={duration_ms}ms err={redact(error)}")
    elif duration_ms is not None:
        logger.info(f"[{profile}] {tool} ok duration={duration_ms}ms args={redact(args_summary)}")
    else:
        logger.info(f"[{profile}] {tool} start args={redact(args_summary)}")


if __name__ == "__main__":
    # Smoke test redaction
    samples = [
        'password=hunter2 hunter2',
        'api_key="sk-abc123def456ghi789jkl012mno345pqr"',
        'Authorization: Bearer ghp_xxxxxxxxxxxxxxxxxxxx',
        'user typed otp=123456 in field',
        'session=abc123def456ghi789jkl012mno345',
    ]
    print("=== redaction smoke test ===")
    for s in samples:
        print(f"  in:  {s}")
        print(f"  out: {redact(s)}")
        print()
