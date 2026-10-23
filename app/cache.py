import hashlib
import os
from pathlib import Path

from app import config
from app.log import log
from app.schemas import AnalysisResponse

cache_dir = Path(config.CACHE_DIR)


def sha256(data) -> str:
    return hashlib.sha256(data).hexdigest()


def path_for(sha) -> Path:
    settings = (config.LLM_MODEL, config.PROMPT_VERSION, config.DROP_UNVERIFIED,
                config.LLM_TEMPERATURE, config.LLM_FREQUENCY_PENALTY, config.LLM_REASONING_EFFORT,
                config.PII_MASKING, config.PII_NAMES,
                config.QUOTE_THRESHOLD, config.QUOTE_THRESHOLD_OCR)
    key = hashlib.sha256(f"{sha}:{settings}".encode()).hexdigest()
    return cache_dir / f"{key}.json"


def get(sha) -> AnalysisResponse | None:
    path = path_for(sha)
    if not path.exists():
        return None
    try:
        return AnalysisResponse.model_validate_json(path.read_text("utf-8"))
    except Exception:
        path.unlink(missing_ok=True)
        return None


def put(sha, resp):
    path = path_for(sha)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp.write_text(resp.model_dump_json(), "utf-8")
        tmp.replace(path)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        log(event="cache_write", status="failed", error=type(e).__name__)
