"""Parser for Indonesian arithmetic expressions."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import InvalidExpressionError
from .normalizer import normalize_text, tokenize
from .number_words import int_to_words, words_to_int


OPERATOR_TOKENS: dict[str, str] = {
    "tambah": "+",
    "plus": "+",
    "kurang": "-",
    "minus": "-",
    "kali": "*",
    "dikali": "*",
    "bagi": "/",
    "dibagi": "/",
}

OPERATOR_WORDS: dict[str, str] = {
    "+": "tambah",
    "-": "kurang",
    "*": "kali",
    "/": "bagi",
}


@dataclass(frozen=True)
class ParsedExpression:
    operands: list[int]
    operators: list[str]

    def to_symbol_string(self) -> str:
        parts: list[str] = [str(self.operands[0])]
        for operator, operand in zip(self.operators, self.operands[1:]):
            parts.extend([operator, str(operand)])
        return " ".join(parts)

    def to_speech_text(self) -> str:
        parts: list[str] = [int_to_words(self.operands[0])]
        for operator, operand in zip(self.operators, self.operands[1:]):
            parts.extend([OPERATOR_WORDS[operator], int_to_words(operand)])
        return " ".join(parts)


@dataclass(frozen=True)
class ParsedProblem:
    source_text: str
    normalized_text: str
    expression: ParsedExpression
    expected_answer: int | None = None


def parse_problem(text: str) -> ParsedProblem:
    """Parse text with optional `sama dengan` answer into a problem."""

    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    if not tokens:
        raise InvalidExpressionError("Input kosong.")

    equality = _find_equality(tokens)
    if equality is None:
        lhs_tokens = tokens
        rhs_tokens: list[str] = []
    else:
        start, end = equality
        lhs_tokens = tokens[:start]
        rhs_tokens = tokens[end:]

    expression = parse_expression(lhs_tokens)
    expected = words_to_int(rhs_tokens) if rhs_tokens else None
    return ParsedProblem(text, normalized, expression, expected)


def parse_expression(tokens: list[str]) -> ParsedExpression:
    """Parse tokens into operands and operators."""

    if not tokens:
        raise InvalidExpressionError("Ekspresi aritmetika kosong.")

    operands: list[int] = []
    operators: list[str] = []
    number_tokens: list[str] = []

    for token in tokens:
        if token in OPERATOR_TOKENS:
            if not number_tokens:
                raise InvalidExpressionError("Operator tidak memiliki angka sebelumnya.")
            operands.append(words_to_int(number_tokens))
            number_tokens = []
            operators.append(OPERATOR_TOKENS[token])
        else:
            number_tokens.append(token)

    if not number_tokens:
        raise InvalidExpressionError("Ekspresi belum lengkap.")

    operands.append(words_to_int(number_tokens))

    if len(operands) != len(operators) + 1:
        raise InvalidExpressionError()

    return ParsedExpression(operands, operators)


def _find_equality(tokens: list[str]) -> tuple[int, int] | None:
    matches: list[tuple[int, int]] = []
    index = 0
    while index < len(tokens):
        if (
            tokens[index] == "sama"
            and index + 1 < len(tokens)
            and tokens[index + 1] == "dengan"
        ):
            matches.append((index, index + 2))
            index += 2
        else:
            index += 1

    if len(matches) > 1:
        raise InvalidExpressionError("Terlalu banyak frasa sama dengan.")
    return matches[0] if matches else None
