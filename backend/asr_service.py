"""ASR service using GPT-SoVITS runtime environment."""
import os
import subprocess
import sys
from datetime import datetime

# Resolve project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configurable via environment variables
GPT_SOVITS_ROOT = os.environ.get("GPT_SOVITS_ROOT", r"D:\AI音库\GPT-SoVITS-v2pro-20250604")
PYTHON_EXE = os.path.join(GPT_SOVITS_ROOT, "runtime", "python.exe")
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", r"D:\biliive-tool\resources\app.asar.unpacked\resources\bin")

TRANSCRIPTS_DIR = os.path.join(PROJECT_ROOT, "transcripts")


def log(msg):
    """Print with timestamp and flush."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def transcribe_audio(audio_path: str, language: str = "auto") -> str:
    """Transcribe audio using GPT-SoVITS's Whisper with GPU."""

    # Verify prerequisites
    if not os.path.exists(PYTHON_EXE):
        raise FileNotFoundError(f"GPT-SoVITS Python not found: {PYTHON_EXE}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio_size = os.path.getsize(audio_path) / 1024 / 1024
    log(f"Audio file: {audio_path} ({audio_size:.1f} MB)")

    # Create script that directly uses Whisper
    script = f'''
import sys
import os

os.chdir(r"{GPT_SOVITS_ROOT}")
sys.path.insert(0, r"{GPT_SOVITS_ROOT}")
os.environ["PATH"] = r"{FFMPEG_PATH}" + os.pathsep + os.environ.get("PATH", "")

from faster_whisper import WhisperModel
import torch

audio_path = r"{audio_path}"
language = "{language}"

# Model path
model_path = os.path.join(r"{GPT_SOVITS_ROOT}", "tools", "asr", "models", "faster-whisper-large-v3-turbo")

# Load model
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

print(f"Device: {{device}}", flush=True)
if device == "cuda":
    print(f"GPU: {{torch.cuda.get_device_name(0)}}", flush=True)
print(f"Model path exists: {{os.path.exists(model_path)}}", flush=True)
print(f"Compute type: {{compute_type}}", flush=True)

print("Loading Whisper model...", flush=True)
model = WhisperModel(model_path, device=device, compute_type=compute_type)
print("Model loaded!", flush=True)

lang = None if language == "auto" else language
print(f"Transcribing: {{audio_path}}", flush=True)
print(f"Language: {{lang or 'auto-detect'}}", flush=True)

print("Starting transcription...", flush=True)
segments, info = model.transcribe(
    audio=audio_path,
    beam_size=5,
    vad_filter=False,
    language=lang,
)

text = ""
segment_count = 0
for segment in segments:
    segment_count += 1
    text += segment.text
    if segment_count <= 5:
        print(f"  Seg {{segment_count}}: {{segment.text[:100]}}", flush=True)

print(f"Language: {{info.language}}", flush=True)
print(f"Total segments: {{segment_count}}", flush=True)
print(f"Total length: {{len(text)}} chars", flush=True)

# Output text to stdout (last line)
print(f"TRANSCRIPT_RESULT:{{text}}", flush=True)
'''

    # Verify paths before running
    log(f"Python: {PYTHON_EXE}")
    log(f"Exists: {os.path.exists(PYTHON_EXE)}")
    log(f"GPT-SoVITS root: {GPT_SOVITS_ROOT}")
    log(f"Root exists: {os.path.exists(GPT_SOVITS_ROOT)}")

    # Run with GPT-SoVITS's Python
    log("Launching GPT-SoVITS runtime for ASR...")
    try:
        result = subprocess.run(
            [PYTHON_EXE, "-c", script],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=GPT_SOVITS_ROOT
        )
    except FileNotFoundError as e:
        log(f"FATAL: Cannot find Python exe: {e}")
        raise
    except subprocess.TimeoutExpired:
        log("FATAL: ASR timed out after 300 seconds!")
        raise RuntimeError("ASR timed out after 300 seconds")

    # Print all output for debugging
    log("--- ASR stdout ---")
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            log(f"  | {line}")
    else:
        log("  (empty)")

    log("--- ASR stderr ---")
    if result.stderr:
        for line in result.stderr.strip().split('\n')[:20]:
            log(f"  | {line}")
    else:
        log("  (empty)")

    log(f"Return code: {result.returncode}")

    # Check for critical errors (ignore warnings)
    if result.returncode != 0 and "TRANSCRIPT_RESULT:" not in result.stdout:
        error_msg = result.stderr[:500] if result.stderr else "Unknown error"
        log(f"FATAL: ASR process failed with code {result.returncode}")
        raise RuntimeError(f"ASR failed (code {result.returncode}): {error_msg}")

    # Extract transcript from output
    transcript = ""
    for line in result.stdout.strip().split('\n'):
        if line.startswith("TRANSCRIPT_RESULT:"):
            transcript = line[len("TRANSCRIPT_RESULT:"):]

    if not transcript:
        log("WARNING: No TRANSCRIPT_RESULT found in output!")
        log(f"Full stdout:\n{result.stdout}")
        raise RuntimeError("No transcript in output")

    log(f"Transcript extracted: {len(transcript)} chars")
    return transcript


def save_transcript(bvid: str, text: str) -> str:
    """Save transcript to file."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    output_path = os.path.join(TRANSCRIPTS_DIR, f"{bvid}.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    log(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python asr_service.py <audio_path> [language]")
        sys.exit(1)

    audio = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "auto"
    text = transcribe_audio(audio, lang)
    print("\n--- Transcript ---")
    print(text[:500])
