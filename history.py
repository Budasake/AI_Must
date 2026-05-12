from datetime import datetime
from config import MAX_HISTORY, CATEGORIES


user_histories: dict[int, list[dict]] = {}
user_categories: dict[int, str] = {}

def set_user_category(user_id: int, category: str) -> bool:

    if category not in CATEGORIES:
        return False

    user_categories[user_id] = category
    return True


def get_user_category(user_id: int) -> str | None:

    return user_categories.get(user_id)


def clear_user_category(user_id: int) -> None:

    user_categories.pop(user_id, None)


def get_user_status(user_id: int) -> str:

    category = get_user_category(user_id)

    if not category:
        return "Одоогоор материалын төрөл сонгоогүй байна."

    category_name = CATEGORIES.get(category, category)

    return f"Сонгосон материалын төрөл: {category_name}"



def get_history(user_id: int) -> list[dict]:
    return user_histories.get(user_id, [])


def add_to_history(user_id: int, role: str, text: str) -> None:

    if role not in {"user", "assistant"}:
        return

    text = text.strip()

    if not text:
        return

    user_histories.setdefault(user_id, []).append({
        "role": role,
        "text": text,
        "time": datetime.now().strftime("%H:%M"),
    })

    if len(user_histories[user_id]) > MAX_HISTORY:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY:]


def clear_history(user_id: int) -> None:

    user_histories.pop(user_id, None)


def clear_all_user_state(user_id: int) -> None:

    clear_history(user_id)
    clear_user_category(user_id)


def format_history_for_prompt(user_id: int, last_n: int = 6) -> str:

    history = get_history(user_id)[-last_n:]

    if not history:
        return ""

    lines = []

    for item in history:
        label = "Оюутан" if item["role"] == "user" else "Туслах"
        lines.append(f"{label}: {item['text']}")

    return "\n".join(lines)