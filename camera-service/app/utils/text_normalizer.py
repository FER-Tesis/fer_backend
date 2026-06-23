import re
import unicodedata


def normalize_text(value: str) -> str:
    value = ''.join(
        char for char in unicodedata.normalize("NFD", value.strip().lower())
        if unicodedata.category(char) != "Mn"
    )

    return re.sub(r"\s+", " ", value)