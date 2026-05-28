"""Indonesian integer parsing and formatting."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .errors import UnknownNumberError


UNITS: dict[str, int] = {
    "nol": 0,
    "satu": 1,
    "dua": 2,
    "tiga": 3,
    "empat": 4,
    "lima": 5,
    "enam": 6,
    "tujuh": 7,
    "delapan": 8,
    "sembilan": 9,
}

UNIT_WORDS: dict[int, str] = {value: key for key, value in UNITS.items()}


def words_to_int(words: str | Sequence[str]) -> int:
    """Convert Indonesian number words or a digit token into an integer."""

    if isinstance(words, str):
        tokens = words.strip().lower().split()
        display = words.strip()
    else:
        tokens = [token.strip().lower() for token in words if token.strip()]
        display = " ".join(tokens)

    if not tokens:
        raise UnknownNumberError(display)

    if len(tokens) == 1 and re.fullmatch(r"[+-]?\d+", tokens[0]):
        return int(tokens[0])

    sign = 1
    if tokens and tokens[0] == "minus":
        sign = -1
        tokens = tokens[1:]

    value = _parse_positive_integer(tokens)
    return sign * value


def int_to_words(number: int) -> str:
    """Convert an integer into Indonesian words."""

    if number < 0:
        return "minus " + int_to_words(abs(number))
    if number == 0:
        return "nol"
    if number < 10:
        return UNIT_WORDS[number]
    if number == 10:
        return "sepuluh"
    if number == 11:
        return "sebelas"
    if number < 20:
        return f"{int_to_words(number - 10)} belas"
    if number < 100:
        tens, rest = divmod(number, 10)
        result = f"{int_to_words(tens)} puluh"
        return result if rest == 0 else f"{result} {int_to_words(rest)}"
    if number == 100:
        return "seratus"
    if number < 200:
        rest = number - 100
        return f"seratus {int_to_words(rest)}"
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        result = f"{int_to_words(hundreds)} ratus"
        return result if rest == 0 else f"{result} {int_to_words(rest)}"
    if number == 1000:
        return "seribu"
    if number < 2000:
        rest = number - 1000
        return f"seribu {int_to_words(rest)}"
    if number < 1_000_000:
        thousands, rest = divmod(number, 1000)
        result = f"{int_to_words(thousands)} ribu"
        return result if rest == 0 else f"{result} {int_to_words(rest)}"
    if number == 1_000_000:
        return "satu juta"
    if number < 1_000_000_000:
        millions, rest = divmod(number, 1_000_000)
        result = f"{int_to_words(millions)} juta"
        return result if rest == 0 else f"{result} {int_to_words(rest)}"
    raise ValueError("Formatter hanya mendukung angka sampai 999.999.999.")


def _parse_positive_integer(tokens: Sequence[str]) -> int:
    if not tokens:
        raise UnknownNumberError("")

    if tokens == ["seribu"]:
        return 1000

    if "juta" in tokens:
        index = tokens.index("juta")
        left = tokens[:index]
        right = tokens[index + 1 :]
        multiplier = 1 if not left else _parse_positive_integer(left)
        value = multiplier * 1_000_000
        return value if not right else value + _parse_positive_integer(right)

    if "ribu" in tokens:
        index = tokens.index("ribu")
        left = tokens[:index]
        right = tokens[index + 1 :]
        multiplier = 1 if not left else _parse_positive_integer(left)
        value = multiplier * 1000
        return value if not right else value + _parse_under_1000(right)

    return _parse_under_1000(tokens)


def _parse_under_1000(tokens: Sequence[str]) -> int:
    if not tokens:
        raise UnknownNumberError("")

    if tokens[0] == "seratus":
        rest = tokens[1:]
        return 100 if not rest else 100 + _parse_under_100(rest)

    if len(tokens) >= 2 and tokens[1] == "ratus":
        hundreds = _unit_value(tokens[0], allow_zero=False)
        rest = tokens[2:]
        value = hundreds * 100
        return value if not rest else value + _parse_under_100(rest)

    return _parse_under_100(tokens)


def _parse_under_100(tokens: Sequence[str]) -> int:
    if not tokens:
        raise UnknownNumberError("")

    if len(tokens) == 1:
        token = tokens[0]
        if token in UNITS:
            return UNITS[token]
        if token == "sepuluh":
            return 10
        if token == "sebelas":
            return 11
        raise UnknownNumberError(" ".join(tokens))

    if len(tokens) == 2 and tokens[1] == "belas":
        value = _unit_value(tokens[0], allow_zero=False)
        if value == 1:
            raise UnknownNumberError(" ".join(tokens))
        return 10 + value

    if len(tokens) >= 2 and tokens[1] == "puluh":
        tens = _unit_value(tokens[0], allow_zero=False)
        if tens == 1:
            raise UnknownNumberError(" ".join(tokens))
        rest = tokens[2:]
        value = tens * 10
        return value if not rest else value + _parse_unit_only(rest)

    raise UnknownNumberError(" ".join(tokens))


def _parse_unit_only(tokens: Sequence[str]) -> int:
    if len(tokens) != 1:
        raise UnknownNumberError(" ".join(tokens))
    return _unit_value(tokens[0], allow_zero=False)


def _unit_value(token: str, *, allow_zero: bool) -> int:
    if token not in UNITS:
        raise UnknownNumberError(token)
    value = UNITS[token]
    if value == 0 and not allow_zero:
        raise UnknownNumberError(token)
    return value

