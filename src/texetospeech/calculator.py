"""Integer-only arithmetic evaluator."""

from __future__ import annotations

from .errors import DivisionByZeroArithmeticError, NonIntegerResultError
from .parser import ParsedExpression


def evaluate_expression(expression: ParsedExpression) -> int:
    """Evaluate with standard precedence and reject fractional division."""

    values = [expression.operands[0]]
    low_precedence_ops: list[str] = []

    for operator, operand in zip(expression.operators, expression.operands[1:]):
        if operator == "*":
            values[-1] *= operand
        elif operator == "/":
            if operand == 0:
                raise DivisionByZeroArithmeticError()
            if values[-1] % operand != 0:
                raise NonIntegerResultError()
            values[-1] //= operand
        else:
            low_precedence_ops.append(operator)
            values.append(operand)

    result = values[0]
    for operator, value in zip(low_precedence_ops, values[1:]):
        if operator == "+":
            result += value
        elif operator == "-":
            result -= value

    return result

