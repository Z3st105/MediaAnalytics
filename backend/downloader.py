"""Download audio from Bilibili using yt-dlp."""
import os
import re
import subprocess

# Resolve project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOWNLOADS_DIR = os.path.join(PROJECT_ROOT, "downloads")

# ffmpeg path - configurable via environment variable
FFMPEG_PATH = os.environ.get("FFMPEG_EXE", r"D:\biliive-tool\resources\app.asar.unpacked\resources\bin\ffmpeg.exe")


def extract_bvid(url: str) -> str:
    """Extract BV id from Bilibili URL."""
    match = re.search(r'(BV[\w]+)', url)
    if match:
        return match.group(1)
    raise ValueError(f"Cannot extract BV id from: {url}")


def download_audio(url: str, output_dir: str = None) -> str:
    """Download audio from Bilibili video URL.

    Returns path to downloaded audio file.
    """
    bvid = extract_bvid(url)
    output_dir = output_dir or DOWNLOADS_DIR
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{bvid}.mp3")

    if os.path.exists(output_path):
        print(f"Audio already exists: {output_path}")
        return output_path

    cmd = [
        "yt-dlp",
        "-x",                     # Extract audio
        "--audio-format", "mp3",  # Convert to mp3
        "--audio-quality", "0",   # Best quality
        "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
        "-o", output_path,
        url
    ]

    print(f"Downloading: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr}")

    print(f"Downloaded: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <bilibili_url>")
        sys.exit(1)
    path = download_audio(sys.argv[1])
    print(f"Saved to: {path}")
