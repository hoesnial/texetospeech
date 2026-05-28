"""STT pakai faster-whisper - free, akurat, mendukung Indonesia.

faster-whisper adalah implementasi Whisper berbasis CTranslate2 yang jauh
lebih cepat dan ringan dari openai-whisper. Berjalan offline di CPU,
mendukung Python 3.13 di Windows tanpa torch / GPU.

Install:
    pip install faster-whisper

Model akan auto-download saat pertama kali digunakan. Defaultnya `small`
(~466 MB) — balance antara akurasi tinggi dan kecepatan masuk akal di CPU.
Pilihan lain via env var `TEXETOSPEECH_WHISPER_MODEL`:

    tiny           ~75MB    tercepat, akurasi paling rendah
    base           ~139MB   ringan
    small          ~466MB   default, akurasi tinggi & cepat di CPU
    medium         ~1.5GB   akurasi sangat tinggi (RAM 4GB+)
    large-v3-turbo ~1.5GB   akurasi mendekati large-v3 (RAM 4GB+, CPU lambat)
    large-v3       ~3GB     akurasi maksimal absolut (RAM 8GB+, GPU/CPU kuat)
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path

from .errors import SpeechBackendError


DEFAULT_MODEL = "tiny"
DEFAULT_LANGUAGE = "id"


def is_installed() -> bool:
    """Cek apakah package faster_whisper sudah terpasang."""

    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    from faster_whisper import WhisperModel

    cache_dir = Path("models/whisper")
    cache_dir.mkdir(parents=True, exist_ok=True)
    # int8 cocok untuk CPU, lebih cepat dan hemat RAM dibanding float32.
    return WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        download_root=str(cache_dir),
    )


def _resolve_model_name() -> str:
    raw = os.environ.get("TEXETOSPEECH_WHISPER_MODEL", DEFAULT_MODEL).strip()
    return raw or DEFAULT_MODEL


def transcribe(audio_path: str | Path, *, language: str = DEFAULT_LANGUAGE) -> str:
    """Transkrip file audio menjadi teks Bahasa Indonesia."""

    if not is_installed():
        raise SpeechBackendError(
            "faster-whisper belum terpasang. Install dengan `pip install faster-whisper`."
        )

    model_name = _resolve_model_name()
    print(f"[info] faster-whisper memakai model `{model_name}` (CPU int8)")
    try:
        load_start = time.time()
        model = _load_model(model_name)
        print(f"[info] Model siap dalam {time.time() - load_start:.1f} detik")
    except Exception as exc:
        # Sebagian besar kegagalan: model gagal di-download atau RAM tidak
        # cukup untuk model besar. Mundur ke model lebih kecil agar pipeline
        # tetap jalan, tapi kasih tahu user.
        fallback_chain = ["small", "base", "tiny"]
        if model_name in fallback_chain:
            raise SpeechBackendError(
                f"Gagal load whisper model `{model_name}`: {exc}"
            ) from exc
        for fallback in fallback_chain:
            try:
                print(
                    f"[warn] Whisper model `{model_name}` gagal di-load ({exc}). "
                    f"Mencoba fallback `{fallback}`..."
                )
                model = _load_model(fallback)
                model_name = fallback
                break
            except Exception as inner_exc:
                exc = inner_exc
                continue
        else:
            raise SpeechBackendError(
                f"Semua whisper model gagal di-load. Penyebab terakhir: {exc}"
            ) from exc

    transcribe_start = time.time()
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        # Tuning ringan: beam 3 cukup untuk vocabulary kecil dan jaga
        # latency tetap rendah di CPU low-end. Audio pendek (<6 detik)
        # umumnya selesai dalam 5-15 detik di mesin tipikal.
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        # Bias output ke kosakata aritmetika Bahasa Indonesia. Ini secara
        # nyata menurunkan kesalahan whisper kecil seperti "sepuluh empat"
        # untuk "empat belas".
        initial_prompt=(
            "Operasi aritmetika dalam Bahasa Indonesia. "
            "Kosakata: nol satu dua tiga empat lima enam tujuh delapan sembilan "
            "sepuluh sebelas dua belas tiga belas empat belas lima belas "
            "enam belas tujuh belas delapan belas sembilan belas dua puluh "
            "tambah kurang kali bagi sama dengan."
        ),
    )
    parts: list[str] = []
    for segment in segments:
        text = (segment.text or "").strip()
        if text:
            parts.append(text)
    elapsed = time.time() - transcribe_start
    result = " ".join(parts).strip()
    print(f"[info] Transkrip selesai dalam {elapsed:.1f} detik: {result[:80]}")
    return result
