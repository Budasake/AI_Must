from datetime import datetime
from config import MAX_HISTORY

user_histories: dict[int, list[dict]] = {}


def get_history(user_id: int) -> list[dict]:
    return user_histories.get(user_id, [])


def add_to_history(user_id: int, role: str, text: str) -> None:
    user_histories.setdefault(user_id, []).append({
        "role": role,
        "text": text,
        "time": datetime.now().strftime("%H:%M"),
    })
    if len(user_histories[user_id]) > MAX_HISTORY:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY:]


def clear_history(user_id: int) -> None:
    user_histories.pop(user_id, None)


def format_history_for_prompt(user_id: int, last_n: int = 6) -> str:
    history = get_history(user_id)[-last_n:]
    if not history:
        return ""
    lines = []
    for h in history:
        label = "Оюутан" if h["role"] == "user" else "Туслах"
        lines.append(f"{label}: {h['text']}")
    return "\n".join(lines)
