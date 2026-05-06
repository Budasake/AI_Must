import os
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_file = RotatingFileHandler("bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
_file.setFormatter(_fmt)
_console = logging.StreamHandler()
_console.setFormatter(_fmt)

if not logger.handlers:
    logger.addHandler(_file)
    logger.addHandler(_console)
logger.propagate = False

TELEGRAM_TOKEN = "8585715138:AAEjK1bZ-32cBGJJiyyaK2eLLAyDxAgfXQA"
GEMINI_API_KEY = "AIzaSyDgi7tLuNTGOQ9NLR6nYOIWTZ81vM70Ko0"
LECTURE_FOLDER = os.getenv("LECTURE_FOLDER", "Lecture")
MAX_HISTORY    = int(os.getenv("MAX_HISTORY", "20"))
TOP_K_CHUNKS   = int(os.getenv("TOP_K_CHUNKS", "4"))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.08"))

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-3-flash-preview",
]

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN тохируулагдаагүй байна.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY тохируулагдаагүй байна.")
