"""
AI Video Assistant — FastAPI Server
====================================
Launch:  python server.py
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
import uvicorn
import uuid
import threading
import os
import tempfile
import io

load_dotenv()

app = FastAPI(title="AI Video Assistant", description="RAG-powered video intelligence")

import time

# ── In-memory task storage with TTL ──────────────────────────────────────────
tasks = {}
TASK_TTL_SECONDS = 7200  # 2 hours

def _cleanup_old_tasks():
    now = time.time()
    expired = [
        tid for tid, data in tasks.items()
        if now - data.get("created_at", now) > TASK_TTL_SECONDS
    ]
    for tid in expired:
        tasks.pop(tid, None)
    # If still large, remove oldest
    if len(tasks) > 50:
        sorted_tasks = sorted(tasks.items(), key=lambda x: x[1].get("created_at", 0))
        for tid, _ in sorted_tasks[:len(tasks) - 50]:
            tasks.pop(tid, None)

# ── Static files & No-Cache Middleware ─────────────────────────────────────────
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def add_no_cache_header(request, call_next):
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


# ── Analysis endpoints ────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def start_analysis(
    source: str = Form(None),
    file: UploadFile = File(None),
    language: str = Form("english"),
):
    if not source and not file:
        raise HTTPException(400, "Provide a YouTube URL or upload a file")

    _cleanup_old_tasks()
    task_id = str(uuid.uuid4())[:8]

    # Persist uploaded file to a temp path
    source_path = source
    is_temp_file = False
    if file:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await file.read())
        tmp.close()
        source_path = tmp.name
        is_temp_file = True

    tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "step": "Initializing...",
        "result": None,
        "rag_chain": None,
        "created_at": time.time(),
        "is_temp": is_temp_file,
    }

    thread = threading.Thread(
        target=_run_pipeline, args=(task_id, source_path, language, is_temp_file), daemon=True
    )
    thread.start()

    return {"task_id": task_id}


def _run_pipeline(task_id: str, source: str, language: str, is_temp_file: bool = False):
    """Run the full analysis pipeline in a background thread."""
    try:
        from utils.audio_processor import process_input, get_last_media_title
        from core.transcriber import transcribe_all
        from core.summarize import summarize, generate_title
        from core.extractor import (
            extract_action_items,
            extract_key_decisions,
            extract_questions,
        )
        from core.rag_engine import build_rag_chain

        t = tasks.get(task_id)
        if not t:
            return

        t.update(step="Downloading & processing audio...", progress=5)
        chunks = process_input(source)

        t.update(step="Transcribing audio with Whisper AI...", progress=20)
        transcript = transcribe_all(chunks, language)

        t.update(step="Synthesizing intelligence & building RAG in parallel...", progress=50)

        import concurrent.futures

        media_title = get_last_media_title()

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_title = executor.submit(lambda: media_title or generate_title(transcript))
            future_summary = executor.submit(summarize, transcript)
            future_actions = executor.submit(extract_action_items, transcript)
            future_decisions = executor.submit(extract_key_decisions, transcript)
            future_questions = executor.submit(extract_questions, transcript)
            future_rag = executor.submit(build_rag_chain, transcript)

            title = future_title.result()
            t.update(progress=62)
            summary_text = future_summary.result()
            t.update(progress=74)
            action_items = future_actions.result()
            decisions = future_decisions.result()
            questions = future_questions.result()
            t.update(progress=88)
            rag_chain = future_rag.result()

        word_count = len(transcript.split()) if transcript else 0

        t["result"] = {
            "title": title,
            "transcript": transcript,
            "summary": summary_text,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
            "word_count": word_count,
            "char_count": len(transcript) if transcript else 0,
        }
        t["rag_chain"] = rag_chain
        t["status"] = "complete"
        t["progress"] = 100
        t["step"] = "Analysis complete!"

    except Exception as e:
        if task_id in tasks:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["step"] = str(e)
            tasks[task_id]["progress"] = 0
    finally:
        # Delete uploaded temp file once processing completes or fails
        if is_temp_file and source and os.path.exists(source):
            try:
                os.remove(source)
            except Exception:
                pass


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found or has expired. Please initiate a new analysis.")
    t = tasks[task_id]
    resp = {"status": t["status"], "progress": t["progress"], "step": t["step"]}
    if t["status"] == "complete" and t["result"]:
        resp["result"] = t["result"]
    return resp


# ── Chat endpoint (sync def offloaded to threadpool to avoid blocking event loop) ──

@app.post("/api/chat")
def chat(task_id: str = Form(...), question: str = Form(...)):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found or session expired. Please start a new analysis.")
    rag = tasks[task_id].get("rag_chain")
    if not rag:
        raise HTTPException(400, "RAG engine not available for this analysis")
    from core.rag_engine import ask_question

    answer = ask_question(rag, question)
    return {"answer": answer}


# ── Export endpoints ──────────────────────────────────────────────────────────

@app.get("/api/export/{task_id}/pdf")
async def export_pdf(task_id: str):
    if task_id not in tasks or not tasks[task_id].get("result"):
        raise HTTPException(404, "No result available for export")
    result = tasks[task_id]["result"]

    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 42, 58)  # Deep Navy from design system
    pdf.cell(0, 14, "AI Video Assistant - Intelligence Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_draw_color(34, 191, 192)  # Teal accent
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
        pdf.set_text_color(8, 127, 150)  # Teal deeper
        pdf.cell(0, 9, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 85, 101)  # Slate body
        body = result.get(key, "") or ""
        # Clean unicode for latin-1 font compatibility
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
    if task_id not in tasks or not tasks[task_id].get("result"):
        raise HTTPException(404, "No result available")
    r = tasks[task_id]["result"]
    content = "\n".join(
        [
            "=" * 60,
            "  AI VIDEO ASSISTANT — ANALYSIS REPORT",
            "=" * 60,
            "",
            f"TITLE: {r.get('title', 'N/A')}",
            "",
            "SUMMARY",
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
        ]
    )
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ai_video_report.txt"},
    )


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n[*] AI Video Assistant - Starting server...")
    print("    Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
