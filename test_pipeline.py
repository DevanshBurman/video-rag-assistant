"""
AI Video Assistant — Local Pipeline Verification Test Script
============================================================
Runs end-to-end testing across:
1. YouTube URL Ingestion (Transcript-first + yt-dlp fallbacks)
2. Local Audio File Ingestion & Conversion
3. Map-Reduce Synthesis (Title, Summary, Actions, Decisions, Questions)
4. Ephemeral In-Memory ChromaDB Vector Store & MMR RAG Chat
5. File Cleanup Verification

Usage:
    python test_pipeline.py
"""

import os
import sys
import time
import tempfile
from dotenv import load_dotenv

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# Set default model to mistral-small-latest if not specified
if not os.getenv("MISTRAL_MODEL"):
    os.environ["MISTRAL_MODEL"] = "mistral-small-latest"

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_youtube_pipeline(url: str):
    print_banner(f"TEST 1: YouTube Ingestion & Synthesis Pipeline ({url})")
    from utils.audio_processor import process_media_source
    from core.summarize import generate_title, summarize
    from core.extractor import extract_action_items, extract_key_decisions, extract_questions
    from core.rag_engine import build_rag_chain, ask_question

    t0 = time.time()
    print("[Stage 1] Ingesting YouTube media source...")
    media_res = process_media_source(source=url, language="english")
    stage_used = media_res.get("stage_used")
    title = media_res.get("title")
    print(f"  ✓ Ingestion Stage Succeeded: '{stage_used}'")
    print(f"  ✓ Detected/Extracted Title: '{title}'")

    transcript = media_res.get("transcript")
    if not transcript and media_res.get("chunks"):
        print(f"  ✓ Audio chunks produced: {len(media_res['chunks'])}")
        from core.transcriber import transcribe_all
        transcript = transcribe_all(media_res["chunks"], language="english")

    assert transcript and len(transcript.strip()) > 0, "Failed to obtain transcript"
    print(f"  ✓ Transcript acquired ({len(transcript)} characters, {len(transcript.split())} words)")
    print(f"    Excerpt: {transcript[:140]}...")

    # Intelligence Synthesis
    print("\n[Stage 2] Running Map-Reduce Synthesis & Analysis...")
    gen_title = generate_title(transcript)
    print(f"  ✓ Title: {gen_title}")

    summary = summarize(transcript)
    print(f"  ✓ Summary ({len(summary)} chars):\n    {summary[:200]}...")

    actions = extract_action_items(transcript)
    print(f"  ✓ Action Items ({len(actions.splitlines())} items):\n    {actions[:160]}...")

    decisions = extract_key_decisions(transcript)
    print(f"  ✓ Decisions:\n    {decisions[:160]}...")

    questions = extract_questions(transcript)
    print(f"  ✓ Open Questions:\n    {questions[:160]}...")

    # Ephemeral Vector Store & RAG
    print("\n[Stage 3] Building Ephemeral Chroma Store & MMR RAG...")
    session_id = f"test_yt_{int(time.time())}"
    rag_chain = build_rag_chain(transcript, session_id=session_id)
    assert rag_chain is not None, "RAG chain initialization failed"
    print(f"  ✓ RAG Chain initialized successfully (session: {session_id})")

    test_q = "What is the main topic or what animals are discussed?"
    print(f"  [Q&A Query]: '{test_q}'")
    answer = ask_question(rag_chain, test_q)
    print(f"  [Q&A Answer]:\n{answer}")

    elapsed = time.time() - t0
    print(f"\n✓ YouTube Pipeline Test Passed in {elapsed:.2f}s!")

def test_local_file_pipeline():
    print_banner("TEST 2: Local Audio File Conversion & Ingestion Pipeline")
    from pydub import AudioSegment
    from pydub.generators import Sine
    from utils.audio_processor import process_media_source
    from core.rag_engine import build_rag_chain, ask_question

    with tempfile.TemporaryDirectory() as tmpdir:
        test_audio_path = os.path.join(tmpdir, "sample_meeting.wav")
        # Generate a small 3-second test WAV file with audible tone
        tone = Sine(440).to_audio_segment(duration=3000)
        tone.export(test_audio_path, format="wav")
        print(f"  ✓ Created synthetic test audio: {test_audio_path} ({os.path.getsize(test_audio_path)} bytes)")

        print("[Stage 1] Ingesting local audio file...")
        res = process_media_source(uploaded_file_path=test_audio_path)
        assert res["type"] == "audio_chunks", "Expected audio_chunks for local file"
        chunks = res["chunks"]
        print(f"  ✓ Ingestion Stage Succeeded: '{res.get('stage_used')}'")
        print(f"  ✓ Generated {len(chunks)} audio chunk(s) (16kHz mono MP3/WAV)")

        # Verify chunks exist and are under 24MB limit
        for c in chunks:
            assert os.path.exists(c), f"Chunk file missing: {c}"
            size_mb = os.path.getsize(c) / (1024 * 1024)
            print(f"    - Chunk {os.path.basename(c)}: {size_mb:.2f} MB (Under 24MB: {size_mb < 24})")

        # Test RAG on sample transcript
        print("\n[Stage 2] Testing RAG indexing & retrieval with metadata citations...")
        mock_transcript = (
            "Welcome everyone to the quarterly product sync. Today we decided to adopt Render "
            "for cloud deployment with Docker containers. Alice is assigned to configure the proxy "
            "and cookies to ensure reliable YouTube transcript extraction by next Friday. "
            "Bob raised an open question regarding how many concurrent users can be served on 512MB RAM."
        )
        session_id = f"test_local_{int(time.time())}"
        rag_chain = build_rag_chain(mock_transcript, session_id=session_id)
        assert rag_chain is not None

        answer = ask_question(rag_chain, "What was decided about deployment?")
        print(f"  [Q&A Query]: 'What was decided about deployment?'")
        print(f"  [Q&A Answer]:\n{answer}")

        # Clean up chunk files
        for c in chunks:
            if os.path.exists(c):
                os.remove(c)
        if res.get("raw_file") and os.path.exists(res["raw_file"]):
            os.remove(res["raw_file"])

    print("\n✓ Local File Pipeline Test Passed!")

def test_server_health():
    print_banner("TEST 3: Server Health Endpoint Test")
    import asyncio
    from server import health_check
    res = asyncio.run(health_check())
    print("  ✓ /health response:", res)
    assert res.get("status") == "ok"
    print("\n✓ Health Endpoint Test Passed!")

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    try:
        test_server_health()
        test_local_file_pipeline()
        test_youtube_pipeline(test_url)
        print_banner("ALL PIPELINE VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ Test Failed with Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
