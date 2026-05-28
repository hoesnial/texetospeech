"""Text normalization for Indonesian arithmetic speech."""

from __future__ import annotations

import re


SYMBOL_REPLACEMENTS = {
    "+": " tambah ",
    "-": " kurang ",
    "*": " kali ",
    "x": " kali ",
    "X": " kali ",
    "×": " kali ",
    "/": " bagi ",
    ":": " bagi ",
    "=": " sama dengan ",
}


def normalize_text(text: str) -> str:
    """Normalize STT or typed text into predictable lowercase tokens."""

    normalized = text.lower().strip()
    for symbol, replacement in SYMBOL_REPLACEMENTS.items():
        normalized = normalized.replace(symbol, replacement)

    replacements = [
        (r"\bsama\s*=\s*dengan\b", "sama dengan"),
        (r"\bsamadengan\b", "sama dengan"),
        (r"\bdi\s+kali\b", "dikali"),
        (r"\bdi\s+bagi\b", "dibagi"),
        (r"\bdi\s+kurang\b", "dikurang"),
        (r"\bhasil\s+nya\b", "hasilnya"),
        (r"\bjawaban\s+nya\b", "jawabannya"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = re.sub(r"[.,!?;()\[\]{}\"']", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def tokenize(text: str) -> list[str]:
    """Normalize and split text into tokens."""

    normalized = normalize_text(text)
    return normalized.split() if normalized else []

