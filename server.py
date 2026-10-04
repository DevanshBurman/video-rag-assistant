"""
AI Video Assistant — FastAPI Server
====================================
High-performance, resource-efficient backend for Video Intelligence & RAG.
Launch:  python server.py
"""

import os
import io
import time
import uuid
import glob
import shutil
import logging
import tempfile
import threading
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

app = FastAPI(
    title="AI Video Assistant",
    description="RAG-powered video intelligence studio with robust multi-stage YouTube ingestion",
    version="2.0.0"
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-Memory Task / Job Storage with TTL ──────────────────────────────────────
jobs = {}
JOB_TTL_SECONDS = 3600  # 1 hour
MAX_JOBS = 50

def _cleanup_old_jobs():
    now = time.time()
    expired = [
        jid for jid, data in jobs.items()
        if now - data.get("created_at", now) > JOB_TTL_SECONDS
    ]
    for jid in expired:
        jobs.pop(jid, None)

    if len(jobs) > MAX_JOBS:
        sorted_jobs = sorted(jobs.items(), key=lambda x: x[1].get("created_at", 0))
        for jid, _ in sorted_jobs[:len(jobs) - MAX_JOBS]:
            jobs.pop(jid, None)

def _cleanup_downloads_directory(specific_files: list[str] = None):
    """Safely remove temporary audio chunks and downloads."""
    if specific_files:
        for f in specific_files:
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                logger.debug(f"Could not remove specific temp file {f}: {e}")
    # Also clean files older than 2 hours in downloads/
    now = time.time()
    for item in glob.glob("downloads/*"):
        try:
            if os.path.isfile(item) and (now - os.path.getmtime(item)) > 7200:
                os.remove(item)
        except Exception:
            pass

# ── Static files & No-Cache Middleware ─────────────────────────────────────────
os.makedirs("static", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.get("/")
async def serve_index():
    return FileResponse(
        "static/index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    )

# ── Health & Diagnostics Endpoints ────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint for Render and monitoring services."""
    return {
        "status": "ok",
        "service": "video-rag-assistant",
        "version": "2.0.0",
        "timestamp": time.time(),
        "active_jobs": len(jobs),
    }

@app.get("/debug/youtube")
async def debug_youtube(
    url: str = Query(..., description="YouTube URL to inspect"),
    token: Optional[str] = Query(None, description="Admin verification token"),
    authorization: Optional[str] = Header(None, description="Bearer token")
):
    """
    Diagnostic endpoint protected by ADMIN_TOKEN.
    Tests each stage of YouTube ingestion and returns detailed diagnostic report.
    """
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    provided_token = token or (authorization.replace("Bearer ", "").strip() if authorization else None)

    if admin_token and provided_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing ADMIN_TOKEN")

    from utils.audio_processor import (
        extract_youtube_id,
        fetch_youtube_oembed_title,
        extract_youtube_transcript_direct,
        extract_youtube_subtitles_ytdlp,
        get_proxy_url_string,
        get_cookie_file_path,
        CLIENT_CONFIGS,
        normalize_url,
    )

    clean_url = normalize_url(url)
    video_id = extract_youtube_id(clean_url)
    if not video_id:
        return JSONResponse(status_code=400, content={"error": "Invalid YouTube URL format"})

    report = {
        "url": clean_url,
        "video_id": video_id,
        "proxy_configured": bool(get_proxy_url_string()),
        "cookies_configured": bool(get_cookie_file_path()),
        "stages": {}
    }

    # Stage 0: oEmbed Title
    oembed_title = fetch_youtube_oembed_title(video_id)
    report["stages"]["oembed"] = {
        "status": "success" if oembed_title else "failed",
        "title": oembed_title
    }

    # Stage 1: youtube_transcript_api
    t_text, t_title, diag1 = extract_youtube_transcript_direct(clean_url)
    report["stages"]["youtube_transcript_api"] = {
        "status": "success" if t_text else "failed",
        "char_count": len(t_text) if t_text else 0,
        "details": diag1
    }

    # Stage 2: yt-dlp Subtitles
    s_text, s_title, diag2 = extract_youtube_subtitles_ytdlp(clean_url)
    report["stages"]["ytdlp_subtitles"] = {
        "status": "success" if s_text else "failed",
        "char_count": len(s_text) if s_text else 0,
        "details": diag2
    }

    # Stage 3: yt-dlp Audio Client Checks
    import yt_dlp
    client_results = []
    for cl in CLIENT_CONFIGS:
        c_name = "default" if cl is None else "+".join(cl)
        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            "js_runtimes": {"node": {}},
        }
        if cl:
            opts["extractor_args"] = {"youtube": {"player_client": cl}}
        p = get_proxy_url_string()
        if p:
            opts["proxy"] = p
        c = get_cookie_file_path()
        if c:
            opts["cookiefile"] = c

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                dur = info.get("duration") if info else None
                client_results.append({"client": c_name, "status": "success", "duration_sec": dur})
        except Exception as e:
            client_results.append({"client": c_name, "status": "failed", "error": str(e)[:120]})

    report["stages"]["ytdlp_audio_clients"] = client_results
    return report

# ── Ingestion & Background Analysis Job ───────────────────────────────────────

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg", ".flac", ".mkv", ".avi"}
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

@app.post("/process")
@app.post("/api/analyze")
async def start_analysis(
    source: Optional[str] = Form(None),
    transcript_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    language: str = Form("english"),
):
    """
    Initiate background analysis pipeline.
    Accepts:
      - source: YouTube / web URL
      - file: Audio/video file upload
      - transcript_text: Pasted transcript text
    Returns job_id immediately so clients avoid gateway timeouts.
    """
    if not source and not file and not (transcript_text and transcript_text.strip()):
        raise HTTPException(400, "Provide a YouTube URL, an uploaded file, or paste a transcript.")

    _cleanup_old_jobs()
    job_id = str(uuid.uuid4())[:8]

    temp_file_path = None
    if file:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext or ".wav")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            tmp.close()
            os.remove(tmp.name)
            raise HTTPException(413, "File exceeds maximum size limit of 500MB.")
        tmp.write(content)
        tmp.close()
        temp_file_path = tmp.name

    jobs[job_id] = {
        "status": "processing",
        "stage": "downloading",
        "progress": 5,
        "step": "Ingesting media source...",
        "result": None,
        "rag_chain": None,
        "created_at": time.time(),
        "temp_file": temp_file_path,
    }

    # Offload processing to background thread
    worker = threading.Thread(
        target=_run_pipeline,
        args=(job_id, source, language, temp_file_path, transcript_text),
        daemon=True
    )
    worker.start()

    return {"job_id": job_id, "task_id": job_id, "status": "processing"}

def _run_pipeline(
    job_id: str,
    source: Optional[str],
    language: str,
    temp_file_path: Optional[str] = None,
    transcript_text: Optional[str] = None
):
    """Executes the full pipeline in background thread with clean stage reporting."""
    created_temp_files = []
    if temp_file_path:
        created_temp_files.append(temp_file_path)

    try:
        from utils.audio_processor import process_media_source, MediaIngestionError
        from core.transcriber import transcribe_all
        from core.summarize import summarize, generate_title
        from core.extractor import extract_action_items, extract_key_decisions, extract_questions
        from core.rag_engine import build_rag_chain
        import concurrent.futures

        j = jobs.get(job_id)
        if not j:
            return

        max_minutes = int(os.getenv("MAX_VIDEO_MINUTES", "90"))

        # Stage 1: Ingestion (downloading / subtitles / direct transcript)
        j.update(stage="downloading", progress=12, step="Acquiring transcript & video content...")
        media_result = process_media_source(
            source=source,
            language=language,
            uploaded_file_path=temp_file_path,
            pasted_transcript=transcript_text,
            max_video_minutes=max_minutes
        )

        title = media_result.get("title") or "Video Intelligence Report"
        if media_result.get("raw_file"):
            created_temp_files.append(media_result["raw_file"])

        # Stage 2: Transcribing (if audio chunks were extracted)
        transcript = None
        if media_result["type"] == "transcript":
            transcript = media_result["transcript"]
            j.update(stage="transcribing", progress=35, step="Transcript acquired. Preparing intelligence synthesis...")
        elif media_result["type"] == "audio_chunks":
            chunks = media_result["chunks"]
            created_temp_files.extend(chunks)
            j.update(stage="transcribing", progress=25, step=f"Transcribing {len(chunks)} audio chunk(s) with Whisper AI...")
            transcript = transcribe_all(chunks, language=language)

        if not transcript or not transcript.strip():
            raise ValueError("No transcript or audible speech could be extracted from this media source.")

        # Stage 3: Summarizing
        j.update(stage="summarizing", progress=50, step="Synthesizing executive summary with Map-Reduce...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_title = executor.submit(lambda: title if (title and "YouTube Video" not in title) else generate_title(transcript))
            future_summary = executor.submit(summarize, transcript)
            future_actions = executor.submit(extract_action_items, transcript)
            future_decisions = executor.submit(extract_key_decisions, transcript)
            future_questions = executor.submit(extract_questions, transcript)

            # Stage 4: Extracting
            j.update(stage="extracting", progress=65, step="Extracting action items, key decisions, and questions...")
            resolved_title = future_title.result()
            summary_text = future_summary.result()
            j.update(progress=75)
            action_items = future_actions.result()
            decisions = future_decisions.result()
            questions = future_questions.result()

        # Stage 5: Indexing
        j.update(stage="indexing", progress=88, step="Building ephemeral Chroma vector store with MMR retrieval...")
        rag_chain = build_rag_chain(transcript, session_id=job_id)

        word_count = len(transcript.split())

        j["result"] = {
            "title": resolved_title,
            "transcript": transcript,
            "summary": summary_text,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
            "word_count": word_count,
            "char_count": len(transcript),
        }
        j["rag_chain"] = rag_chain
        j["status"] = "complete"
        j["stage"] = "complete"
        j["progress"] = 100
        j["step"] = "Analysis complete!"

    except MediaIngestionError as mie:
        logger.error(f"[Job {job_id}] MediaIngestionError: {mie}")
        if job_id in jobs:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["step"] = str(mie)
            jobs[job_id]["progress"] = 0
            jobs[job_id]["error_code"] = mie.code
    except Exception as e:
        logger.error(f"[Job {job_id}] Pipeline exception: {e}", exc_info=True)
        if job_id in jobs:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["step"] = "Analysis failed. Please check the source or upload the audio/video file directly."
            jobs[job_id]["progress"] = 0
            jobs[job_id]["error_code"] = "PIPELINE_ERROR"
    finally:
        _cleanup_downloads_directory(created_temp_files)

# ── Status Polling ─────────────────────────────────────────────────────────────

@app.get("/status/{job_id}")
@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Poll pipeline stage and progress."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found or has expired. Please initiate a new analysis.")
    j = jobs[job_id]
    resp = {
        "job_id": job_id,
        "task_id": job_id,
        "status": j["status"],
        "stage": j.get("stage", "processing"),
        "progress": j["progress"],
        "step": j["step"]
    }
    if j.get("error_code"):
        resp["error_code"] = j["error_code"]
    if j["status"] == "complete" and j.get("result"):
        resp["result"] = j["result"]
    return resp

# ── RAG Chat ──────────────────────────────────────────────────────────────────

@app.post("/chat")
@app.post("/api/chat")
def chat(
    task_id: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None),
    question: str = Form(...)
):
    """Query RAG engine using MMR search over ephemeral indexed transcript chunks."""
    target_id = task_id or job_id
    if not target_id or target_id not in jobs:
        raise HTTPException(404, "Session not found or expired. Please start a new analysis.")

    rag = jobs[target_id].get("rag_chain")
    if not rag:
        raise HTTPException(400, "RAG engine not available for this analysis session.")

    from core.rag_engine import ask_question
    answer = ask_question(rag, question)
    return {"answer": answer}

# ── PDF & TXT Export Endpoints ────────────────────────────────────────────────

@app.get("/api/export/{task_id}/pdf")
async def export_pdf(task_id: str):
    if task_id not in jobs or not jobs[task_id].get("result"):
        raise HTTPException(404, "No result available for export")
    result = jobs[task_id]["result"]

    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(15, 42, 58)
    pdf.cell(0, 14, "AI Video Assistant - Intelligence Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_draw_color(34, 191, 192)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(7)

    sections = [
        ("Title", "title"),
        ("Executive Summary", "summary"),
        ("Action Items", "action_items"),
        ("Key Decisions", "key_decisions"),
        ("Open Questions", "open_questions"),
        ("Full Transcript", "transcript"),
    ]
    for heading, key in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(8, 127, 150)
        pdf.cell(0, 9, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 85, 101)
        body = result.get(key, "") or ""
        safe = body.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 5.5, safe)
        pdf.ln(5)

    buf = io.BytesIO(bytes(pdf.output()))
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ai_video_report.pdf"},
    )

@app.get("/api/export/{task_id}/txt")
async def export_txt(task_id: str):
    if task_id not in jobs or not jobs[task_id].get("result"):
        raise HTTPException(404, "No result available for export")
    r = jobs[task_id]["result"]
    content = "\n".join([
        "=" * 60,
        "  AI VIDEO ASSISTANT — ANALYSIS REPORT",
        "=" * 60,
        "",
        f"TITLE: {r.get('title', 'N/A')}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        r.get("summary", ""),
        "",
        "ACTION ITEMS",
        "-" * 40,
        r.get("action_items", ""),
        "",
        "KEY DECISIONS",
        "-" * 40,
        r.get("key_decisions", ""),
        "",
        "OPEN QUESTIONS",
        "-" * 40,
        r.get("open_questions", ""),
        "",
        "FULL TRANSCRIPT",
        "-" * 40,
        r.get("transcript", ""),
        "",
        "=" * 60,
    ])
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ai_video_report.txt"},
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n[*] AI Video Assistant - Starting server on port {port}...")
    print(f"    Access URL: http://0.0.0.0:{port}\n")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
