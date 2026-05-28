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


# Variasi STT yang sering keliru di Bahasa Indonesia. Semua kunci sudah
# berformat lowercase.
PHRASE_FIXES: tuple[tuple[str, str], ...] = (
    # Whisper sering memecah "X belas" menjadi "sepuluh X". Kembalikan ke
    # bentuk standar agar parser angka mengenali.
    (r"\bsepuluh\s+satu\b", "sebelas"),
    (r"\bsepuluh\s+dua\b", "dua belas"),
    (r"\bsepuluh\s+tiga\b", "tiga belas"),
    (r"\bsepuluh\s+empat\b", "empat belas"),
    (r"\bsepuluh\s+lima\b", "lima belas"),
    (r"\bsepuluh\s+enam\b", "enam belas"),
    (r"\bsepuluh\s+tujuh\b", "tujuh belas"),
    (r"\bsepuluh\s+delapan\b", "delapan belas"),
    (r"\bsepuluh\s+sembilan\b", "sembilan belas"),
    # Variasi ejaan operator yang sering muncul di STT.
    (r"\bplas\b", "tambah"),
    (r"\bplus\b", "tambah"),
    (r"\bmines\b", "kurang"),
    (r"\bminuz\b", "kurang"),
    (r"\bdi\s+bagi\s+oleh\b", "bagi"),
    (r"\bdi\s+kali\s+oleh\b", "kali"),
    (r"\bsama\s+saja\s+dengan\b", "sama dengan"),
    (r"\bsama\s+saja\b", "sama dengan"),
    # Variasi pelafalan angka yang sering ditranskrip whisper:
    (r"\binam\b", "enam"),
    (r"\bnam\b", "enam"),
    (r"\btiha\b", "tiga"),
    (r"\bdouble\b", "dua"),
    # Whisper kadang menulis digit; biarkan normalize_text tetap menanganinya.
)


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

    # Koreksi STT spesifik (mis. whisper "sepuluh empat" -> "empat belas").
    for pattern, replacement in PHRASE_FIXES:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = re.sub(r"[.,!?;()\[\]{}\"']", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def tokenize(text: str) -> list[str]:
    """Normalize and split text into tokens."""

    normalized = normalize_text(text)
    return normalized.split() if normalized else []

