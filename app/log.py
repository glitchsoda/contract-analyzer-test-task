import json
import logging
import sys

logger = logging.getLogger("contract")
handler = logging.StreamHandler(sys.stderr)   # stdout занят протоколом MCP
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

ALLOWED = {"event", "sha", "pages", "chars", "chunks", "cached", "ocr_pages",
           "duration_ms", "status", "error", "risks", "unverified"}


def log(**fields):
    fields = {k: v for k, v in fields.items() if k in ALLOWED}
    if "sha" in fields:
        fields["sha"] = fields["sha"][:12]
    logger.info(json.dumps(fields, ensure_ascii=False))
