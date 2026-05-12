import time
from google import genai
from google.genai import errors as genai_errors
from config import logger, GEMINI_API_KEY, GEMINI_MODELS


_client = genai.Client(api_key=GEMINI_API_KEY)


def _get_error_code(error: Exception):
    return (
        getattr(error, "code", None)
        or getattr(error, "status_code", None)
    )


def _is_retryable_error(error: Exception) -> bool:
    code = _get_error_code(error)
    msg = str(error).lower()

    return (
        code in (429, 500, 502, 503, 504)
        or "overloaded" in msg
        or "unavailable" in msg
        or "high demand" in msg
        or "temporarily" in msg
    )


def generate_with_fallback(prompt: str, max_retries_per_model: int = 2) -> str:
    """
    Try each Gemini model in GEMINI_MODELS.
    If one model is overloaded or unavailable, retry with backoff.
    Then fallback to next model.
    """

    last_err: Exception | None = None

    for model in GEMINI_MODELS:
        for attempt in range(1, max_retries_per_model + 1):
            try:
                logger.info(f"Gemini call: model={model}, attempt={attempt}")

                response = _client.models.generate_content(
                    model=model,
                    contents=prompt,
                )

                text = (getattr(response, "text", None) or "").strip()

                if text:
                    return text

                logger.warning(f"{model}: хоосон хариу ирлээ.")
                break

            except genai_errors.APIError as e:
                last_err = e
                code = _get_error_code(e)

                if _is_retryable_error(e):
                    wait = 2 ** attempt
                    logger.warning(
                        f"{model} түр алдаа/ачаалалтай байна "
                        f"(code={code}). {wait}s хүлээгээд дахин оролдоно."
                    )
                    time.sleep(wait)
                    continue

                logger.error(f"{model} retry хийх боломжгүй алдаа: {e}")
                break

            except Exception as e:
                last_err = e
                logger.error(f"{model} гэнэтийн алдаа: {e}", exc_info=True)
                break

        logger.info(f"{model} амжилтгүй — дараагийн загвар руу шилжиж байна.")

    raise RuntimeError(f"Бүх Gemini загвар амжилтгүй боллоо: {last_err}")