from __future__ import annotations

import math
import re

from app.i18n import get_language


_PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?")
_LOCALE_DEPENDENT_DECIMAL = re.compile(r"[+-]?[1-9][0-9]{0,2}(?P<separator>[.,])[0-9]{3}")
_GROUPED_NUMBER = re.compile(
    r"[+-]?[1-9][0-9]{0,2}(?P<group>[., \u00a0\u202f])[0-9]{3}"
    r"(?:(?P=group)[0-9]{3})*(?:(?P<decimal>[.,])[0-9]+)?"
)


def parse_float(
    value: object, default: float | None = None, *, language: str | None = None,
) -> float:
    """Use the active decimal separator when a single separator could also group thousands."""
    text = "" if value is None else str(value).strip()
    if isinstance(value, (int, float)):
        number = float(value)
    elif not text:
        if default is None:
            raise ValueError("Numeric value is required.")
        number = float(default)
    else:
        local_decimal = "," if (language or get_language()) == "pt" else "."
        single_separator = _LOCALE_DEPENDENT_DECIMAL.fullmatch(text)
        if single_separator and single_separator["separator"] != local_decimal:
            raise ValueError("Ambiguous decimal or thousands separator.")
        if not _PLAIN_NUMBER.fullmatch(text):
            grouped = _GROUPED_NUMBER.fullmatch(text)
            if grouped is None or grouped["group"] == grouped["decimal"]:
                raise ValueError("Invalid numeric format.")
            text = text.replace(grouped["group"], "")
        number = float(text.replace(",", "."))
    if not math.isfinite(number):
        raise ValueError("A finite numeric value is required.")
    return number


def relocalize_decimal_input(text: str, previous_language: str) -> str:
    """Preserve the meaning and digits of a valid input that depends on its locale."""
    if previous_language == get_language():
        return text
    previous_decimal, current_decimal = (",", ".") if previous_language == "pt" else (".", ",")
    match = _LOCALE_DEPENDENT_DECIMAL.fullmatch(text.strip())
    if match and match["separator"] == previous_decimal:
        return text.replace(previous_decimal, current_decimal)
    return text


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


def format_display_number(
    value: float | int | None,
    decimals: int | None = 2,
    *,
    language: str | None = None,
    significant_digits: bool = False,
    default: str = "—",
) -> str:
    """Format a UI value. Pass None for decimals to keep its ungrouped representation."""
    if value is None:
        return default
    style = "g" if significant_digits else "f"
    text = str(value) if decimals is None else f"{value:,.{decimals}{style}}"
    if (language or get_language()) == "pt":
        return text.translate(str.maketrans(",.", ".,"))
    return text
