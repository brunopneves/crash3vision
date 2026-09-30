from __future__ import annotations

from app.i18n import get_language


def parse_float(value: object, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise ValueError("Numeric value is required.")
        return float(default)

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        if default is None:
            raise ValueError("Numeric value is required.")
        return float(default)

    text = text.replace(" ", "")

    if "," in text and "." in text:
        last_comma = text.rfind(",")
        last_dot = text.rfind(".")

        if last_comma > last_dot:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")

    return float(text)


def format_float(
    value: object,
    decimals: int = 2,
    default: str = "-",
    suffix: str = "",
) -> str:
    if value is None:
        return default

    number = parse_float(value)
    text = f"{number:.{decimals}f}"

    if get_language() == "pt":
        text = text.replace(".", ",")

    return f"{text}{suffix}"
