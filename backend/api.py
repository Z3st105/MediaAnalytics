"""FastAPI backend for MediaAnalytics."""
import os
import sys
import threading
import traceback
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_connection, init_db
from downloader import download_audio, extract_bvid
from asr_service import transcribe_audio, save_transcript


def log(msg):
    """Print with timestamp and flush."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


app = FastAPI(title="MediaAnalytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task queue for parallel processing
task_queue = {}
task_lock = threading.Lock()


class VideoRequest(BaseModel):
    url: str


class AnalysisRequest(BaseModel):
    video_id: int
    analysis: str


@app.on_event("startup")
async def startup():
    log("=== Backend starting ===")
    init_db()
    log("=== Database initialized ===")
    log("=== Ready on http://127.0.0.1:8765 ===")


@app.post("/api/videos")
async def add_video(req: VideoRequest):
    """Add a video URL to the queue."""
    log(f"[NEW] Received URL: {req.url}")

    try:
        bvid = extract_bvid(req.url)
        log(f"[NEW] Extracted BV ID: {bvid}")
    except ValueError as e:
        log(f"[ERROR] Invalid URL: {e}")
        raise HTTPException(400, str(e))

    conn = get_connection()
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute("SELECT id FROM videos WHERE bvid = ?", (bvid,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        log(f"[SKIP] Video already exists: {bvid}")
        raise HTTPException(409, f"Video already exists: {bvid}")

    cursor.execute(
        "INSERT INTO videos (url, bvid, status) VALUES (?, ?, ?)",
        (req.url, bvid, "pending")
    )
    video_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log(f"[NEW] Saved to database, ID: {video_id}")

    # Start background processing
    log(f"[NEW] Starting background thread for ID: {video_id}")
    threading.Thread(
        target=process_video,
        args=(video_id, req.url, bvid),
        daemon=True
    ).start()

    return {"id": video_id, "bvid": bvid, "status": "pending"}


@app.get("/api/videos")
async def list_videos():
    """List all videos."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/api/videos/{video_id}")
async def get_video(video_id: int):
    """Get video details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Video not found")
    return dict(row)


@app.put("/api/videos/{video_id}/analysis")
async def save_analysis(video_id: int, req: AnalysisRequest):
    """Save AI analysis for a video."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE videos SET ai_analysis = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (req.analysis, video_id)
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Video not found")
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: int):
    """Delete a video."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Video not found")
    conn.commit()
    conn.close()
    return {"status": "deleted"}


def process_video(video_id: int, url: str, bvid: str):
    """Background task: download and transcribe."""
    log(f"\n{'='*50}")
    log(f"[PROCESS] Starting: {bvid} (ID: {video_id})")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Update status
        cursor.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ("downloading", video_id)
        )
        conn.commit()
        log(f"[{bvid}] Step 1/3: Status -> downloading")

        # Step 2: Download audio
        log(f"[{bvid}] Step 2/3: Downloading audio...")
        audio_path = download_audio(url)
        log(f"[{bvid}] Download OK: {audio_path}")

        cursor.execute(
            "UPDATE videos SET audio_path = ?, status = ? WHERE id = ?",
            (audio_path, "transcribing", video_id)
        )
        conn.commit()
        log(f"[{bvid}] Status -> transcribing")

        # Step 3: Transcribe
        log(f"[{bvid}] Step 3/3: Starting ASR transcription...")
        log(f"[{bvid}] (This calls GPT-SoVITS runtime, may take 10-60s...)")
        transcript = transcribe_audio(audio_path, language="auto")
        save_transcript(bvid, transcript)
        log(f"[{bvid}] ASR done! Length: {len(transcript)} chars")

        cursor.execute(
            "UPDATE videos SET transcript = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (transcript, "completed", video_id)
        )
        conn.commit()
        log(f"[{bvid}] DONE!")

    except Exception as e:
        log(f"[{bvid}] ERROR: {type(e).__name__}: {e}")
        log(f"[{bvid}] Traceback:\n{traceback.format_exc()}")
        cursor.execute(
            "UPDATE videos SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (f"error: {str(e)}", video_id)
        )
        conn.commit()
    finally:
        conn.close()
    log(f"{'='*50}\n")


if __name__ == "__main__":
    import uvicorn
    log("Starting uvicorn server...")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
