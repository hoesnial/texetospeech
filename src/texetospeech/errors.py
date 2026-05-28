"""Application-specific exceptions with user-facing Indonesian messages."""


class TexeToSpeechError(Exception):
    """Base error for recoverable application problems."""

    default_message = "Maaf, saya belum bisa mengenali operasi tersebut."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.user_message = message or self.default_message


class InvalidExpressionError(TexeToSpeechError):
    """Raised when arithmetic text cannot be parsed."""


class UnknownNumberError(InvalidExpressionError):
    """Raised when a number word sequence is unknown."""

    def __init__(self, text: str) -> None:
        super().__init__(f"Angka tidak dikenali: {text}.")


class DivisionByZeroArithmeticError(TexeToSpeechError):
    """Raised for division by zero."""

    default_message = "Pembagian dengan nol tidak dapat diproses."


class NonIntegerResultError(TexeToSpeechError):
    """Raised when a division or final result would become fractional."""

    default_message = (
        "Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses."
    )


class SpeechBackendError(TexeToSpeechError):
    """Raised when no usable STT or TTS backend is available."""

