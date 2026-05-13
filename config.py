import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

_log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

file_handler = RotatingFileHandler(
    "bot.log",
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8"
)
file_handler.setFormatter(_log_format)

console_handler = logging.StreamHandler()
console_handler.setFormatter(_log_format)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

logger.propagate = False

def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"{name} тохируулагдаагүй байна.")

    return value


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name, str(default))

    try:
        return int(value)
    except ValueError:
        logger.warning(f"{name} must be integer. Using default: {default}")
        return default


def get_float_env(name: str, default: float) -> float:
    value = os.getenv(name, str(default))

    try:
        return float(value)
    except ValueError:
        logger.warning(f"{name} must be float. Using default: {default}")
        return default


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in ("true", "1", "yes", "y")

TELEGRAM_TOKEN = get_required_env("TELEGRAM_TOKEN")
GEMINI_API_KEY = get_required_env("GEMINI_API_KEY")


LOCAL_MATERIALS_DIR = os.getenv("LOCAL_MATERIALS_DIR", "materials")

USE_GOOGLE_DRIVE = os.getenv("USE_GOOGLE_DRIVE", "false").lower() == "true"
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "service-account.json"
)
GOOGLE_DRIVE_ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")

CATEGORIES = {
    "class_info": "🏫 Course Info",
    "lectures": "📚 Lecture",
    "labs": "🧪 Laboratory",
}


MAX_HISTORY = get_int_env("MAX_HISTORY", 20)
TOP_K_CHUNKS = get_int_env("TOP_K_CHUNKS", 4)
MIN_SIMILARITY = get_float_env("MIN_SIMILARITY", 0.08)

CHUNK_SIZE = get_int_env("CHUNK_SIZE", 900)
CHUNK_OVERLAP = get_int_env("CHUNK_OVERLAP", 150)


GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
]

TELEGRAM_MAX_MESSAGE_LENGTH = 4096


logger.info("Config loaded successfully.")
logger.info(f"Materials folder: {LOCAL_MATERIALS_DIR}")
logger.info(f"Use Google Drive: {USE_GOOGLE_DRIVE}")
logger.info(f"Categories: {list(CATEGORIES.keys())}")
logger.info(f"TOP_K_CHUNKS={TOP_K_CHUNKS}, MIN_SIMILARITY={MIN_SIMILARITY}")