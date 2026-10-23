import os

from dotenv import load_dotenv

load_dotenv()


def env_bool(name, default="false"):
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def env_list(name):
    return [x.strip() for x in os.getenv(name, "").split(",") if x.strip()]


# LLM
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
LLM_FALLBACK_MODELS = env_list("LLM_FALLBACK_MODELS")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_FREQUENCY_PENALTY = float(os.getenv("LLM_FREQUENCY_PENALTY", "0"))
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "")   # none | low | medium | high

SINGLE_PASS_CHARS = int(os.getenv("SINGLE_PASS_CHARS", "20000"))
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "12000"))
MAP_WORKERS = int(os.getenv("MAP_WORKERS", "2"))
REDUCE_GROUP = int(os.getenv("REDUCE_GROUP", "6"))

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
DROP_UNVERIFIED = env_bool("DROP_UNVERIFIED")
QUOTE_THRESHOLD = int(os.getenv("QUOTE_THRESHOLD", "90"))

CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/contract-cache")
PROMPT_VERSION = "v8"   # входит в ключ кэша

# OCR
OCR_ENABLED = env_bool("OCR_ENABLED", "true")
OCR_LANG = os.getenv("OCR_LANG", "rus+eng")
OCR_DPI = int(os.getenv("OCR_DPI", "300"))
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "30"))
QUOTE_THRESHOLD_OCR = int(os.getenv("QUOTE_THRESHOLD_OCR", "85"))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
TESSDATA_DIR = os.getenv("TESSDATA_DIR", "")

# ПДн
PII_MASKING = env_bool("PII_MASKING")
PII_NAMES = env_bool("PII_NAMES")

# очередь
ASYNC_ENABLED = env_bool("ASYNC_ENABLED")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/contract-uploads")
WORKER_MAX_JOBS = int(os.getenv("WORKER_MAX_JOBS", "2"))

# MCP
MCP_ALLOWED_DIR = os.getenv("MCP_ALLOWED_DIR", "")   # пусто = выключено
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
