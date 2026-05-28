"""Small standard-library web app for the TexeToSpeech MVP."""

from __future__ import annotations

import json
import mimetypes
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .audio import build_voice_profile, convert_to_wav
from .dataset import PROMPTS, append_metadata
from .engine import evaluate_text
from .errors import TexeToSpeechError
from .speech import speak_text, transcribe_audio


@dataclass(frozen=True)
class WebConfig:
    audio_dir: Path = Path("audio/web")
    upload_dir: Path = Path("uploads")
    dataset_dir: Path = Path("recordings/browser_dataset")
    profile_dir: Path = Path("voice_profiles/default")

    @property
    def default_voice_reference(self) -> Path:
        return self.profile_dir / "speaker_reference.wav"


class TexeToSpeechServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        config: WebConfig,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.config = config


class TexeToSpeechHandler(BaseHTTPRequestHandler):
    server: TexeToSpeechServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML)
            return
        if parsed.path == "/api/prompts":
            self._send_json({"prompts": PROMPTS})
            return
        if parsed.path.startswith("/audio/"):
            self._serve_audio(parsed.path.removeprefix("/audio/"))
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/text":
                self._handle_text()
            elif parsed.path == "/api/tts":
                self._handle_tts()
            elif parsed.path == "/api/listen":
                self._handle_listen(parsed.query)
            elif parsed.path == "/api/dataset/record":
                self._handle_dataset_record()
            elif parsed.path == "/api/profile/build":
                self._handle_profile_build()
            else:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except TexeToSpeechError as exc:
            self._send_json({"error": exc.user_message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json(
                {"error": f"Terjadi kesalahan internal: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _handle_text(self) -> None:
        payload = self._read_json()
        text = str(payload.get("text", "")).strip()
        result = evaluate_text(text)
        response: dict[str, object] = {"evaluation": result.to_dict()}

        if payload.get("speak"):
            audio_url, backend = self._create_tts_audio(
                result.answer_text,
                use_voice_profile=bool(payload.get("useVoiceProfile")),
            )
            response["audio_url"] = audio_url
            response["tts_backend"] = backend

        self._send_json(response)

    def _handle_tts(self) -> None:
        payload = self._read_json()
        text = str(payload.get("text", "")).strip()
        audio_url, backend = self._create_tts_audio(
            text,
            use_voice_profile=bool(payload.get("useVoiceProfile")),
        )
        self._send_json({"audio_url": audio_url, "tts_backend": backend})

    def _handle_listen(self, query: str) -> None:
        content_type = self.headers.get("Content-Type", "")
        body = self._read_body()
        if content_type.startswith("application/json"):
            payload = json.loads(body.decode("utf-8"))
            transcript_text = str(payload.get("transcript", "")).strip()
            transcript_backend = "manual-transcript"
        else:
            suffix = _suffix_for_content_type(content_type)
            upload_path = self._write_binary(
                self.server.config.upload_dir,
                f"stt-{uuid.uuid4().hex}{suffix}",
                body,
            )
            transcript = transcribe_audio(upload_path)
            transcript_text = transcript.text
            transcript_backend = transcript.backend

        result = evaluate_text(transcript_text)
        response: dict[str, object] = {
            "transcript": transcript_text,
            "stt_backend": transcript_backend,
            "evaluation": result.to_dict(),
        }
        params = parse_qs(query)
        if params.get("speak", ["0"])[0] == "1":
            audio_url, backend = self._create_tts_audio(result.answer_text)
            response["audio_url"] = audio_url
            response["tts_backend"] = backend
        self._send_json(response)

    def _handle_dataset_record(self) -> None:
        index = int(self.headers.get("X-Prompt-Index", "0"))
        prompt = unquote(self.headers.get("X-Prompt-Text", "")).strip()
        if index < 1 or not prompt:
            raise TexeToSpeechError("Prompt dataset tidak valid.")

        content_type = self.headers.get("Content-Type", "")
        suffix = _suffix_for_content_type(content_type)
        dataset_dir = self.server.config.dataset_dir
        raw_path = self._write_binary(dataset_dir / "raw", f"{index:03d}{suffix}", self._read_body())
        wav_path = dataset_dir / f"{index:03d}.wav"
        convert_to_wav(raw_path, wav_path)
        metadata_path = append_metadata(
            dataset_dir,
            index=index,
            prompt=prompt,
            audio_path=wav_path,
            backend="browser-mediarecorder",
        )
        self._send_json(
            {
                "audio_path": str(wav_path),
                "metadata_path": str(metadata_path),
                "prompt": prompt,
            }
        )

    def _handle_profile_build(self) -> None:
        profile = build_voice_profile(
            self.server.config.dataset_dir,
            self.server.config.profile_dir,
            name="browser",
        )
        self._send_json({"profile": profile.to_dict()})

    def _create_tts_audio(
        self,
        text: str,
        *,
        use_voice_profile: bool = False,
    ) -> tuple[str, str]:
        audio_dir = self.server.config.audio_dir
        output_name = f"tts-{uuid.uuid4().hex}.wav"
        output_path = audio_dir / output_name
        voice_reference = None
        if use_voice_profile and self.server.config.default_voice_reference.exists():
            voice_reference = self.server.config.default_voice_reference
        result = speak_text(text, output_path=output_path, voice_reference=voice_reference)
        return f"/audio/{output_name}", result.backend

    def _read_json(self) -> dict[str, object]:
        body = self._read_body()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

    def _send_json(
        self,
        payload: dict[str, object],
        *,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_audio(self, requested_name: str) -> None:
        safe_name = Path(unquote(requested_name)).name
        audio_path = (self.server.config.audio_dir / safe_name).resolve()
        audio_root = self.server.config.audio_dir.resolve()
        if audio_root not in audio_path.parents or not audio_path.exists():
            self._send_json({"error": "Audio tidak ditemukan."}, status=HTTPStatus.NOT_FOUND)
            return
        body = audio_path.read_bytes()
        mime_type = mimetypes.guess_type(audio_path.name)[0] or "audio/wav"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_binary(self, directory: Path, filename: str, body: bytes) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        output_path = directory / filename
        output_path.write_bytes(body)
        return output_path


def run_web_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    config: WebConfig | None = None,
) -> None:
    """Run the local web app until interrupted."""

    web_config = config or WebConfig()
    web_config.audio_dir.mkdir(parents=True, exist_ok=True)
    web_config.upload_dir.mkdir(parents=True, exist_ok=True)
    web_config.dataset_dir.mkdir(parents=True, exist_ok=True)
    web_config.profile_dir.mkdir(parents=True, exist_ok=True)
    server = TexeToSpeechServer((host, port), TexeToSpeechHandler, web_config)
    print(f"TexeToSpeech web app berjalan di http://{host}:{port}")
    server.serve_forever()


def _suffix_for_content_type(content_type: str) -> str:
    normalized = content_type.split(";", 1)[0].strip().lower()
    mapping = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "text/plain": ".txt",
    }
    return mapping.get(normalized, ".bin")


INDEX_HTML = r"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TexeToSpeech</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --line: #d9dde4;
      --text: #18202a;
      --muted: #5d6876;
      --accent: #0f766e;
      --accent-strong: #0b5f59;
      --danger: #b42318;
      --warn: #a15c07;
      --ok: #16794c;
      --focus: #1d4ed8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    .topbar {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }
    .status {
      color: var(--muted);
      font-size: 14px;
      min-width: 180px;
      text-align: right;
    }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto 48px;
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
      gap: 18px;
    }
    section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 16px;
      letter-spacing: 0;
    }
    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }
    textarea, input[type="text"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: inherit;
      resize: vertical;
      min-height: 110px;
      color: var(--text);
      background: #fff;
    }
    textarea:focus, input:focus, button:focus {
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }
    .row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin-top: 12px;
    }
    button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #fff;
      border-radius: 6px;
      min-height: 38px;
      padding: 0 14px;
      font: inherit;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--accent-strong);
    }
    button.warning {
      border-color: var(--warn);
      background: var(--warn);
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .toggle {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      color: var(--text);
      font-size: 14px;
    }
    .toggle input { width: 16px; height: 16px; }
    .output {
      border: 1px solid var(--line);
      background: #fbfcfd;
      border-radius: 6px;
      padding: 12px;
      min-height: 96px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 14px;
    }
    .output.ok { border-color: #8fd1b1; }
    .output.error { border-color: #f2a7a0; color: var(--danger); }
    audio {
      width: 100%;
      margin-top: 12px;
    }
    .grid {
      display: grid;
      gap: 18px;
    }
    .prompt-box {
      border-left: 4px solid var(--accent);
      background: #f2fbf8;
      border-radius: 6px;
      padding: 12px;
      min-height: 82px;
    }
    .prompt-index {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }
    .meter {
      display: grid;
      grid-template-columns: repeat(16, 1fr);
      gap: 3px;
      height: 34px;
      align-items: end;
      margin-top: 12px;
    }
    .meter span {
      display: block;
      min-height: 5px;
      border-radius: 3px;
      background: #b6c2cf;
    }
    .meter.recording span:nth-child(3n) { background: #0f766e; height: 30px; }
    .meter.recording span:nth-child(3n + 1) { background: #d97706; height: 20px; }
    .meter.recording span:nth-child(3n + 2) { background: #1d4ed8; height: 25px; }
    .small {
      color: var(--muted);
      font-size: 13px;
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .status { text-align: left; min-width: auto; }
      .topbar { align-items: flex-start; flex-direction: column; padding: 12px 0; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <h1>TexeToSpeech</h1>
      <div class="status" id="status">Siap</div>
    </div>
  </header>

  <main>
    <div class="grid">
      <section>
        <h2>Text to Speech Aritmetika</h2>
        <label for="textInput">Input operasi</label>
        <textarea id="textInput">satu tambah dua tambah tiga</textarea>
        <div class="row">
          <button id="textRun">Hitung</button>
          <button class="secondary" id="textSpeak">Hitung + Audio</button>
          <label class="toggle"><input type="checkbox" id="useVoice"> pakai voice profile jika ada</label>
        </div>
        <div class="row">
          <div class="output" id="textOutput">Belum ada hasil.</div>
        </div>
        <audio id="textAudio" controls hidden></audio>
      </section>

      <section>
        <h2>Speech to Text to Speech</h2>
        <div class="row">
          <button id="recordStt">Mulai Rekam</button>
          <button class="secondary" id="uploadButton">Upload Audio</button>
          <input id="audioFile" type="file" accept="audio/*" hidden>
        </div>
        <div class="meter" id="sttMeter" aria-hidden="true"></div>
        <div class="row">
          <div class="output" id="sttOutput">Rekam atau upload audio berisi operasi aritmetika.</div>
        </div>
        <audio id="sttAudio" controls hidden></audio>
      </section>
    </div>

    <div class="grid">
      <section>
        <h2>Dataset Suara Saya</h2>
        <div class="prompt-box">
          <div class="prompt-index" id="promptIndex">Prompt 001</div>
          <div id="promptText">Memuat prompt...</div>
        </div>
        <div class="row">
          <button id="recordDataset">Rekam Prompt</button>
          <button class="secondary" id="nextPrompt">Berikutnya</button>
          <button class="secondary" id="prevPrompt">Sebelumnya</button>
        </div>
        <div class="meter" id="datasetMeter" aria-hidden="true"></div>
        <div class="row">
          <div class="output" id="datasetOutput">Rekaman akan disimpan ke recordings/browser_dataset.</div>
        </div>
      </section>

      <section>
        <h2>Voice Profile</h2>
        <p class="small">Bangun speaker_reference.wav dari rekaman dataset. Backend voice cloning akan memakainya jika package TTS/XTTS tersedia.</p>
        <div class="row">
          <button id="buildProfile" class="warning">Build Profile</button>
        </div>
        <div class="row">
          <div class="output" id="profileOutput">Belum ada profile yang dibuat.</div>
        </div>
      </section>
    </div>
  </main>

  <script>
    const statusEl = document.getElementById('status');
    const textOutput = document.getElementById('textOutput');
    const sttOutput = document.getElementById('sttOutput');
    const datasetOutput = document.getElementById('datasetOutput');
    const profileOutput = document.getElementById('profileOutput');
    const textAudio = document.getElementById('textAudio');
    const sttAudio = document.getElementById('sttAudio');
    const sttMeter = document.getElementById('sttMeter');
    const datasetMeter = document.getElementById('datasetMeter');

    let prompts = [];
    let promptCursor = 0;
    let recorder = null;
    let chunks = [];
    let activeStopHandler = null;

    for (const meter of [sttMeter, datasetMeter]) {
      for (let i = 0; i < 16; i += 1) {
        meter.appendChild(document.createElement('span'));
      }
    }

    function setStatus(message) {
      statusEl.textContent = message;
    }

    function setOutput(el, message, isError = false) {
      el.textContent = message;
      el.classList.toggle('error', isError);
      el.classList.toggle('ok', !isError);
    }

    async function postJson(path, payload) {
      const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Request gagal');
      return data;
    }

    async function postAudio(path, blob, headers = {}) {
      const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': blob.type || 'audio/webm', ...headers },
        body: blob
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Request gagal');
      return data;
    }

    function renderEvaluation(result) {
      const ev = result.evaluation;
      const lines = [
        `Ekspresi: ${ev.expression}`,
        `Hasil: ${ev.result} (${ev.result_words})`,
        `Jawaban: ${ev.answer_text}`
      ];
      if (result.transcript) lines.unshift(`Transkrip: ${result.transcript}`);
      if (result.stt_backend) lines.push(`STT: ${result.stt_backend}`);
      if (result.tts_backend) lines.push(`TTS: ${result.tts_backend}`);
      return lines.join('\n');
    }

    function showAudio(audioEl, url) {
      if (!url) {
        audioEl.hidden = true;
        return;
      }
      audioEl.src = `${url}?t=${Date.now()}`;
      audioEl.hidden = false;
      audioEl.play().catch(() => {});
    }

    async function runText(speak) {
      setStatus('Memproses teks...');
      textAudio.hidden = true;
      try {
        const data = await postJson('/api/text', {
          text: document.getElementById('textInput').value,
          speak,
          useVoiceProfile: document.getElementById('useVoice').checked
        });
        setOutput(textOutput, renderEvaluation(data));
        showAudio(textAudio, data.audio_url);
        setStatus('Siap');
      } catch (error) {
        setOutput(textOutput, error.message, true);
        setStatus('Perlu diperiksa');
      }
    }

    async function startRecording(meter, onStop) {
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        throw new Error('Browser belum mendukung MediaRecorder.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      recorder = new MediaRecorder(stream);
      activeStopHandler = onStop;
      recorder.ondataavailable = event => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        meter.classList.remove('recording');
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        const handler = activeStopHandler;
        recorder = null;
        activeStopHandler = null;
        await handler(blob);
      };
      meter.classList.add('recording');
      recorder.start();
    }

    function stopRecording() {
      if (recorder && recorder.state !== 'inactive') recorder.stop();
    }

    document.getElementById('textRun').addEventListener('click', () => runText(false));
    document.getElementById('textSpeak').addEventListener('click', () => runText(true));

    document.getElementById('recordStt').addEventListener('click', async event => {
      if (recorder) {
        event.target.textContent = 'Mulai Rekam';
        stopRecording();
        return;
      }
      setStatus('Merekam STT...');
      event.target.textContent = 'Stop Rekam';
      try {
        await startRecording(sttMeter, async blob => {
          try {
            const data = await postAudio('/api/listen?speak=1', blob);
            setOutput(sttOutput, renderEvaluation(data));
            showAudio(sttAudio, data.audio_url);
            setStatus('Siap');
          } catch (error) {
            setOutput(sttOutput, error.message, true);
            setStatus('Perlu backend STT');
          } finally {
            event.target.textContent = 'Mulai Rekam';
          }
        });
      } catch (error) {
        setOutput(sttOutput, error.message, true);
        setStatus('Perlu izin mikrofon');
        event.target.textContent = 'Mulai Rekam';
      }
    });

    document.getElementById('uploadButton').addEventListener('click', () => {
      document.getElementById('audioFile').click();
    });
    document.getElementById('audioFile').addEventListener('change', async event => {
      const file = event.target.files[0];
      if (!file) return;
      setStatus('Memproses audio...');
      try {
        const data = await postAudio('/api/listen?speak=1', file);
        setOutput(sttOutput, renderEvaluation(data));
        showAudio(sttAudio, data.audio_url);
        setStatus('Siap');
      } catch (error) {
        setOutput(sttOutput, error.message, true);
        setStatus('Perlu backend STT');
      }
    });

    function renderPrompt() {
      if (!prompts.length) return;
      document.getElementById('promptIndex').textContent = `Prompt ${String(promptCursor + 1).padStart(3, '0')}`;
      document.getElementById('promptText').textContent = prompts[promptCursor];
    }

    document.getElementById('nextPrompt').addEventListener('click', () => {
      promptCursor = Math.min(promptCursor + 1, prompts.length - 1);
      renderPrompt();
    });
    document.getElementById('prevPrompt').addEventListener('click', () => {
      promptCursor = Math.max(promptCursor - 1, 0);
      renderPrompt();
    });

    document.getElementById('recordDataset').addEventListener('click', async event => {
      if (recorder) {
        event.target.textContent = 'Rekam Prompt';
        stopRecording();
        return;
      }
      setStatus('Merekam dataset...');
      event.target.textContent = 'Stop Rekam';
      try {
        await startRecording(datasetMeter, async blob => {
          const index = promptCursor + 1;
          const prompt = prompts[promptCursor];
          try {
            const data = await postAudio('/api/dataset/record', blob, {
              'X-Prompt-Index': String(index),
              'X-Prompt-Text': encodeURIComponent(prompt)
            });
            setOutput(datasetOutput, `Tersimpan: ${data.audio_path}\nPrompt: ${data.prompt}`);
            promptCursor = Math.min(promptCursor + 1, prompts.length - 1);
            renderPrompt();
            setStatus('Siap');
          } catch (error) {
            setOutput(datasetOutput, error.message, true);
            setStatus('Gagal simpan dataset');
          } finally {
            event.target.textContent = 'Rekam Prompt';
          }
        });
      } catch (error) {
        setOutput(datasetOutput, error.message, true);
        setStatus('Perlu izin mikrofon');
        event.target.textContent = 'Rekam Prompt';
      }
    });

    document.getElementById('buildProfile').addEventListener('click', async () => {
      setStatus('Membangun profile...');
      try {
        const data = await postJson('/api/profile/build', {});
        setOutput(profileOutput, JSON.stringify(data.profile, null, 2));
        setStatus('Profile siap');
      } catch (error) {
        setOutput(profileOutput, error.message, true);
        setStatus('Profile belum siap');
      }
    });

    fetch('/api/prompts')
      .then(response => response.json())
      .then(data => {
        prompts = data.prompts || [];
        renderPrompt();
      })
      .catch(error => setOutput(datasetOutput, error.message, true));
  </script>
</body>
</html>
"""
