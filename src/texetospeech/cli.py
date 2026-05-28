"""Command line interface for TexeToSpeech."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .audio import build_voice_profile, record_wav
from .dataset import read_prompts, record_prompt, write_prompts, export_training_dataset
from .doctor import run_doctor
from .engine import evaluate_text
from .errors import TexeToSpeechError
from .speech import speak_text, transcribe_audio
from .webapp import run_web_app


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except TexeToSpeechError as exc:
        print(exc.user_message, file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="texetospeech",
        description="Speech to text to speech untuk aritmetika Bahasa Indonesia.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    text_parser = subparsers.add_parser("text", help="Hitung input teks aritmetika.")
    text_parser.add_argument("text", nargs="+", help="Teks aritmetika.")
    text_parser.add_argument("--json", action="store_true", help="Cetak output JSON.")
    text_parser.add_argument("--speak", action="store_true", help="Bacakan jawaban.")
    text_parser.add_argument("--out", help="Simpan audio jawaban ke file.")
    text_parser.add_argument(
        "--voice-reference",
        help="File wav referensi suara untuk backend voice cloning opsional.",
    )
    text_parser.add_argument(
        "--my-voice",
        action="store_true",
        help=(
            "Pakai suara sendiri (concatenative dari rekaman dataset). "
            "Tidak butuh model neural. Hanya butuh recordings/browser_dataset/ "
            "atau recordings/my_voice/ berisi dataset yang sudah direkam."
        ),
    )
    text_parser.set_defaults(handler=handle_text)

    listen_parser = subparsers.add_parser(
        "listen",
        help="Ubah suara menjadi teks, hitung, lalu opsional bacakan jawaban.",
    )
    listen_parser.add_argument(
        "--audio",
        help="Path audio. Untuk demo tanpa STT, boleh memakai file .txt berisi transkrip.",
    )
    listen_parser.add_argument(
        "--transcript",
        help=(
            "Transkrip teks langsung untuk skip STT (fallback saat tidak ada "
            "whisper / SpeechRecognition)."
        ),
    )
    listen_parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"],
        help=(
            "Pilih model faster-whisper. tiny=tercepat, base=balance ringan, "
            "small=akurasi tinggi, medium=akurasi sangat tinggi (RAM 4GB+), "
            "large-v3-turbo=default paling akurat dgn kecepatan oke, "
            "large-v3=akurasi maksimal absolut (RAM 8GB+)."
        ),
    )
    listen_parser.add_argument("--json", action="store_true", help="Cetak output JSON.")
    listen_parser.add_argument("--speak", action="store_true", help="Bacakan jawaban.")
    listen_parser.add_argument("--out", help="Simpan audio jawaban ke file.")
    listen_parser.add_argument(
        "--voice-reference",
        help="File wav referensi suara untuk backend voice cloning opsional.",
    )
    listen_parser.add_argument(
        "--my-voice",
        action="store_true",
        help="Pakai suara sendiri (concatenative dari rekaman dataset).",
    )
    listen_parser.set_defaults(handler=handle_listen)

    tts_parser = subparsers.add_parser("tts", help="Bacakan teks langsung.")
    tts_parser.add_argument("text", nargs="+", help="Teks yang akan dibacakan.")
    tts_parser.add_argument("--out", help="Simpan audio ke file.")
    tts_parser.add_argument(
        "--voice-reference",
        help="File wav referensi suara untuk backend voice cloning opsional.",
    )
    tts_parser.add_argument(
        "--my-voice",
        action="store_true",
        help="Pakai suara sendiri (concatenative dari rekaman dataset).",
    )
    tts_parser.set_defaults(handler=handle_tts)

    prompts_parser = subparsers.add_parser(
        "dataset-prompts",
        help="Ekspor daftar kalimat untuk dataset suara pribadi.",
    )
    prompts_parser.add_argument(
        "--out",
        default="data/dataset_prompts.txt",
        help="Path output prompt dataset.",
    )
    prompts_parser.add_argument(
        "--scope",
        choices=["full", "mvp"],
        default="full",
        help=(
            "full = semua prompt; mvp = subset minimum (angka 0..10 + operator "
            "dasar + frasa jawaban) yang langsung cocok untuk personal voice."
        ),
    )
    prompts_parser.set_defaults(handler=handle_dataset_prompts)

    record_parser = subparsers.add_parser(
        "record",
        help="Rekam audio mikrofon ke file WAV.",
    )
    record_parser.add_argument("--out", required=True, help="Path output WAV.")
    record_parser.add_argument(
        "--seconds",
        type=float,
        default=4,
        help="Durasi rekaman dalam detik.",
    )
    record_parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="Sample rate WAV.",
    )
    record_parser.set_defaults(handler=handle_record)

    record_dataset_parser = subparsers.add_parser(
        "record-dataset",
        help="Rekam dataset suara pribadi berdasarkan prompt.",
    )
    record_dataset_parser.add_argument(
        "--prompts",
        default="data/dataset_prompts.txt",
        help="File prompt dataset.",
    )
    record_dataset_parser.add_argument(
        "--out",
        default="recordings/my_voice",
        help="Folder output rekaman dataset.",
    )
    record_dataset_parser.add_argument(
        "--seconds",
        type=float,
        default=4,
        help="Durasi setiap prompt dalam detik.",
    )
    record_dataset_parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="Sample rate WAV.",
    )
    record_dataset_parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Nomor prompt awal.",
    )
    record_dataset_parser.add_argument(
        "--limit",
        type=int,
        help="Jumlah prompt yang direkam.",
    )
    record_dataset_parser.add_argument(
        "--yes",
        action="store_true",
        help="Rekam tanpa konfirmasi Enter per prompt.",
    )
    record_dataset_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tampilkan prompt tanpa merekam.",
    )
    record_dataset_parser.set_defaults(handler=handle_record_dataset)

    profile_parser = subparsers.add_parser(
        "build-profile",
        help="Buat speaker_reference.wav dari rekaman dataset.",
    )
    profile_parser.add_argument(
        "--dataset",
        default="recordings/my_voice",
        help="Folder dataset berisi file WAV.",
    )
    profile_parser.add_argument(
        "--out",
        default="voice_profiles/default",
        help="Folder output voice profile.",
    )
    profile_parser.add_argument("--name", default="default", help="Nama profil suara.")
    profile_parser.add_argument(
        "--max-files",
        type=int,
        default=20,
        help="Jumlah maksimal WAV yang digabung untuk referensi.",
    )
    profile_parser.set_defaults(handler=handle_build_profile)

    export_parser = subparsers.add_parser(
        "export-training-dataset",
        help="Export dataset rekaman ke format Piper training (LJSpeech).",
    )
    export_parser.add_argument(
        "--dataset",
        default="recordings/browser_dataset",
        help="Folder dataset berisi file WAV dan metadata.csv.",
    )
    export_parser.add_argument(
        "--out",
        default="training_export",
        help="Folder output untuk training.",
    )
    export_parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="Sample rate WAV output.",
    )
    export_parser.set_defaults(handler=handle_export_training)

    web_parser = subparsers.add_parser(
        "web",
        help="Jalankan web app lokal.",
    )
    web_parser.add_argument("--host", default="127.0.0.1", help="Host server.")
    web_parser.add_argument("--port", type=int, default=8765, help="Port server.")
    web_parser.set_defaults(handler=handle_web)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Cek kesiapan backend TTS, STT, rekaman, dan voice profile.",
    )
    doctor_parser.add_argument("--json", action="store_true", help="Cetak JSON.")
    doctor_parser.set_defaults(handler=handle_doctor)

    return parser


def _resolve_voice_reference(args: argparse.Namespace) -> str | None:
    """Pilih voice reference dari --voice-reference atau --my-voice."""

    if getattr(args, "voice_reference", None):
        return args.voice_reference
    if getattr(args, "my_voice", False):
        from . import personal_voice

        if not personal_voice.has_personal_voice_dataset():
            print(
                "[warn] --my-voice diminta tetapi dataset rekaman pribadi belum "
                "ditemukan. Rekam dulu lewat web app atau `record-dataset`.",
                file=sys.stderr,
            )
            return None
        # Path placeholder agar speak_text masuk ke jalur voice cloning. Backend
        # personal-voice akan mendeteksi dataset dan tidak butuh file ini.
        return "voice_profiles/default/speaker_reference.wav"
    return None


def handle_text(args: argparse.Namespace) -> int:
    user_text = " ".join(args.text)
    result = evaluate_text(user_text)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.answer_text)

    if args.speak or args.out:
        speech_result = speak_text(
            result.answer_text,
            output_path=args.out,
            voice_reference=_resolve_voice_reference(args),
        )
        if speech_result.output_path:
            print(f"Audio disimpan: {speech_result.output_path}")
        print(f"Backend TTS: {speech_result.backend}")
    return 0


def handle_listen(args: argparse.Namespace) -> int:
    if getattr(args, "whisper_model", None):
        os.environ["TEXETOSPEECH_WHISPER_MODEL"] = args.whisper_model

    if args.transcript:
        from .speech import TranscriptResult

        transcript = TranscriptResult(
            text=args.transcript.strip(),
            backend="manual-transcript",
            source_path=None,
        )
    else:
        if not args.audio:
            print(
                "Argumen --audio atau --transcript wajib diisi.",
                file=sys.stderr,
            )
            return 1
        transcript = transcribe_audio(args.audio)
    result = evaluate_text(transcript.text)
    payload = {
        "transcript": transcript.text,
        "stt_backend": transcript.backend,
        "evaluation": result.to_dict(),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Transkrip: {transcript.text}")
        print(result.answer_text)

    if args.speak or args.out:
        speech_result = speak_text(
            result.answer_text,
            output_path=args.out,
            voice_reference=_resolve_voice_reference(args),
        )
        if speech_result.output_path:
            print(f"Audio disimpan: {speech_result.output_path}")
        print(f"Backend TTS: {speech_result.backend}")
    return 0


def handle_tts(args: argparse.Namespace) -> int:
    text = " ".join(args.text)
    result = speak_text(
        text,
        output_path=args.out,
        voice_reference=_resolve_voice_reference(args),
    )
    if result.output_path:
        print(f"Audio disimpan: {result.output_path}")
    print(f"Backend TTS: {result.backend}")
    return 0


def handle_dataset_prompts(args: argparse.Namespace) -> int:
    output_path = write_prompts(args.out, scope=args.scope)
    print(f"Prompt dataset ({args.scope}) ditulis: {output_path}")
    return 0


def handle_record(args: argparse.Namespace) -> int:
    result = record_wav(
        args.out,
        seconds=args.seconds,
        sample_rate=args.sample_rate,
    )
    print(f"Audio direkam: {result.path}")
    print(f"Backend: {result.backend}")
    return 0


def handle_record_dataset(args: argparse.Namespace) -> int:
    prompts = read_prompts(args.prompts)
    start = max(args.start, 1)
    selected = list(enumerate(prompts, start=1))[start - 1 :]
    if args.limit is not None:
        selected = selected[: args.limit]

    if not selected:
        print("Tidak ada prompt yang perlu direkam.")
        return 0

    for index, prompt in selected:
        print(f"\nPrompt {index:03d}: {prompt}")
        if args.dry_run:
            continue
        if not args.yes:
            input("Tekan Enter untuk mulai merekam...")
        result = record_prompt(
            args.out,
            index=index,
            prompt=prompt,
            seconds=args.seconds,
            sample_rate=args.sample_rate,
        )
        print(f"Tersimpan: {result.path}")

    print(f"\nDataset selesai: {args.out}")
    return 0


def handle_build_profile(args: argparse.Namespace) -> int:
    profile = build_voice_profile(
        args.dataset,
        args.out,
        name=args.name,
        max_files=args.max_files,
    )
    print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
    return 0


def handle_export_training(args: argparse.Namespace) -> int:
    output = export_training_dataset(
        args.dataset,
        args.out,
        sample_rate=args.sample_rate,
    )
    print(f"Dataset training diekspor ke: {output}")
    print(f"Format: LJSpeech (id|text)")
    print(f"Upload folder ini ke Google Drive, lalu jalankan training di Colab.")
    print(f"Lihat docs/TRAINING_VOICE.md untuk panduan lengkap.")
    return 0


def handle_web(args: argparse.Namespace) -> int:
    run_web_app(host=args.host, port=args.port)
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    checks = run_doctor()
    if args.json:
        print(json.dumps([check.to_dict() for check in checks], ensure_ascii=False, indent=2))
        return 0

    for check in checks:
        marker = "OK" if check.ok else "--"
        print(f"[{marker}] {check.name}: {check.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
