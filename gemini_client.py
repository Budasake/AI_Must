import time
from google import genai
from google.genai import errors as genai_errors
from config import logger, GEMINI_API_KEY, GEMINI_MODELS

_client = genai.Client(api_key=GEMINI_API_KEY)


def generate_with_fallback(prompt: str, max_retries_per_model: int = 2) -> str:
    """Try each model in GEMINI_MODELS; handle 503/overload with backoff."""
    last_err: Exception | None = None
    for model in GEMINI_MODELS:
        for attempt in range(1, max_retries_per_model + 1):
            try:
                logger.info(f"Gemini call: model={model} attempt={attempt}")
                resp = _client.models.generate_content(model=model, contents=prompt)
                text = (getattr(resp, "text", None) or "").strip()
                if text:
                    return text
                logger.warning(f"{model}: хоосон хариу ирлээ.")
                break
            except genai_errors.APIError as e:
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                msg = str(e)
                last_err = e
                if code in (503, 429) or "overloaded" in msg.lower() or "unavailable" in msg.lower():
                    wait = 2 ** attempt
                    logger.warning(f"{model} ачаалал ихтэй ({code}). {wait}s хүлээж дахин оролдоно.")
                    time.sleep(wait)
                    continue
                logger.error(f"{model} алдаа: {e}")
                break
            except Exception as e:
                last_err = e
                logger.error(f"{model} гэнэтийн алдаа: {e}")
                break
        logger.info(f"{model} амжилтгүй — дараагийн загвар руу шилжиж байна.")

    raise RuntimeError(f"Бүх Gemini загвар амжилтгүй боллоо: {last_err}")
