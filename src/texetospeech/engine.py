"""High-level application flow from text input to answer text."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .calculator import evaluate_expression
from .errors import TexeToSpeechError
from .number_words import int_to_words
from .parser import parse_problem


@dataclass(frozen=True)
class EvaluationResult:
    input_text: str
    normalized_text: str
    expression: str
    expression_speech: str
    result: int
    result_words: str
    answer_text: str
    expected_answer: int | None = None
    is_answer_check: bool = False
    is_correct: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_text(text: str) -> EvaluationResult:
    """Parse, calculate, and create a spoken Indonesian answer."""

    problem = parse_problem(text)
    result = evaluate_expression(problem.expression)
    result_words = int_to_words(result)
    expression_speech = problem.expression.to_speech_text()
    is_answer_check = problem.expected_answer is not None
    is_correct = (
        None if problem.expected_answer is None else problem.expected_answer == result
    )

    if is_correct is True:
        answer_text = f"Jawaban benar. {expression_speech} sama dengan {result_words}."
    elif is_correct is False:
        answer_text = f"Jawaban salah. Hasil yang benar adalah {result_words}."
    else:
        answer_text = f"{expression_speech} sama dengan {result_words}."

    return EvaluationResult(
        input_text=text,
        normalized_text=problem.normalized_text,
        expression=problem.expression.to_symbol_string(),
        expression_speech=expression_speech,
        result=result,
        result_words=result_words,
        answer_text=answer_text,
        expected_answer=problem.expected_answer,
        is_answer_check=is_answer_check,
        is_correct=is_correct,
    )


def respond_to_text(text: str) -> str:
    """Return a user-facing answer for valid or invalid arithmetic text."""

    try:
        return evaluate_text(text).answer_text
    except TexeToSpeechError as exc:
        return exc.user_message

