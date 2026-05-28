from __future__ import annotations

import unittest

from texetospeech.engine import evaluate_text, respond_to_text
from texetospeech.errors import (
    DivisionByZeroArithmeticError,
    NonIntegerResultError,
)
from texetospeech.number_words import int_to_words, words_to_int


class NumberWordsTest(unittest.TestCase):
    def test_words_to_int(self) -> None:
        cases = {
            "nol": 0,
            "satu": 1,
            "dua belas": 12,
            "dua puluh satu": 21,
            "seratus": 100,
            "seratus dua puluh tiga": 123,
            "1": 1,
            "42": 42,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(words_to_int(text), expected)

    def test_int_to_words(self) -> None:
        cases = {
            0: "nol",
            6: "enam",
            12: "dua belas",
            21: "dua puluh satu",
            100: "seratus",
            123: "seratus dua puluh tiga",
            -4: "minus empat",
        }
        for number, expected in cases.items():
            with self.subTest(number=number):
                self.assertEqual(int_to_words(number), expected)


class ArithmeticEngineTest(unittest.TestCase):
    def test_addition_chain(self) -> None:
        result = evaluate_text("satu tambah dua tambah tiga")
        self.assertEqual(result.expression, "1 + 2 + 3")
        self.assertEqual(result.result, 6)
        self.assertEqual(result.result_words, "enam")
        self.assertEqual(result.answer_text, "satu tambah dua tambah tiga sama dengan enam.")

    def test_digit_input(self) -> None:
        result = evaluate_text("1 tambah 2 tambah 3 sama dengan 6")
        self.assertTrue(result.is_correct)
        self.assertIn("Jawaban benar", result.answer_text)

    def test_wrong_answer(self) -> None:
        result = evaluate_text("satu tambah dua tambah tiga sama dengan lima")
        self.assertFalse(result.is_correct)
        self.assertEqual(result.result_words, "enam")
        self.assertIn("Jawaban salah", result.answer_text)

    def test_operator_precedence(self) -> None:
        result = evaluate_text("dua tambah tiga kali empat")
        self.assertEqual(result.result, 14)
        self.assertEqual(result.result_words, "empat belas")

    def test_integer_division(self) -> None:
        result = evaluate_text("dua puluh bagi lima")
        self.assertEqual(result.result, 4)
        self.assertEqual(result.result_words, "empat")

    def test_reject_fractional_result(self) -> None:
        with self.assertRaises(NonIntegerResultError):
            evaluate_text("lima bagi dua")
        self.assertEqual(
            respond_to_text("lima bagi dua"),
            "Hasil operasi ini bukan bilangan bulat, jadi tidak dapat diproses.",
        )

    def test_division_by_zero(self) -> None:
        with self.assertRaises(DivisionByZeroArithmeticError):
            evaluate_text("lima bagi nol")
        self.assertEqual(
            respond_to_text("lima bagi nol"),
            "Pembagian dengan nol tidak dapat diproses.",
        )

    def test_symbol_input(self) -> None:
        result = evaluate_text("2 + 3 * 4")
        self.assertEqual(result.result, 14)

    def test_trailing_equals_is_treated_as_question(self) -> None:
        result = evaluate_text("2 + 2 =")
        self.assertEqual(result.result, 4)
        self.assertFalse(result.is_answer_check)

    def test_whisper_sepuluh_x_is_normalized_to_belasan(self) -> None:
        # Whisper kadang mentranskrip "empat belas" sebagai "sepuluh empat".
        result = evaluate_text("sepuluh empat tambah dua")
        self.assertEqual(result.expression, "14 + 2")
        self.assertEqual(result.result, 16)
        self.assertEqual(result.result_words, "enam belas")


if __name__ == "__main__":
    unittest.main()
