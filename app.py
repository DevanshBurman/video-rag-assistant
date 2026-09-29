"""
AI Video Assistant — Premium Streamlit UI
==========================================
Launch:  streamlit run app.py
"""

import streamlit as st
import os, io, time, tempfile
from dotenv import load_dotenv

load_dotenv()

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Root tokens ─────────────────────────────────────────────────────────── */
:root {
    --bg-base: #EDF4FB;
    --bg-card: rgba(255, 255, 255, 0.55);
    --bg-card-hover: rgba(255, 255, 255, 0.75);
    --border-glass: rgba(180, 210, 240, 0.45);
    --shadow-soft: 0 8px 32px rgba(100, 160, 220, 0.12);
    --shadow-3d: 0 20px 60px rgba(80, 140, 210, 0.18), 0 4px 12px rgba(80,140,210,0.08);
    --shadow-3d-hover: 0 30px 80px rgba(60, 130, 210, 0.22), 0 8px 20px rgba(60,130,210,0.12);
    --accent: #4A90D9;
    --accent-light: #7CB9F0;
    --accent-dark: #2E6AB0;
    --text-primary: #1A2B3D;
    --text-secondary: #4A6580;
    --text-muted: #7A95AD;
    --gradient-hero: linear-gradient(135deg, #E8F2FC 0%, #D4E8F9 30%, #C0DCF5 60%, #E0ECFA 100%);
    --gradient-accent: linear-gradient(135deg, #4A90D9, #7CB9F0);
    --gradient-card: linear-gradient(145deg, rgba(255,255,255,0.7) 0%, rgba(220,235,250,0.4) 100%);
    --radius: 20px;
    --radius-sm: 12px;
    --transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* ── Global resets ───────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-primary) !important;
}

/* ── Animated background ─────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background: var(--gradient-hero) !important;
    background-size: 400% 400% !important;
    animation: gradientShift 20s ease infinite !important;
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

[data-testid="stHeader"] {
    background: transparent !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(230,240,252,0.92) 0%, rgba(210,228,248,0.95) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid var(--border-glass) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
}

/* ── 3D Glass cards ──────────────────────────────────────────────────────── */
.glass-card {
    background: var(--gradient-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius);
    padding: 32px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-3d);
    transition: var(--transition);
    transform: perspective(1200px) rotateX(0deg) rotateY(0deg);
    transform-style: preserve-3d;
    position: relative;
    overflow: hidden;
}
.glass-card::before {
    content: '';
    position: absolute;
    top: -1px; left: -1px; right: -1px;
    height: 4px;
    border-radius: var(--radius) var(--radius) 0 0;
    background: var(--gradient-accent);
    opacity: 0;
    transition: opacity 0.4s ease;
}
.glass-card:hover {
    box-shadow: var(--shadow-3d-hover);
    transform: perspective(1200px) rotateX(1deg) translateY(-6px);
    background: var(--bg-card-hover);
}
.glass-card:hover::before {
    opacity: 1;
}

/* ── Hero banner ─────────────────────────────────────────────────────────── */
.hero-container {
    background: linear-gradient(135deg, rgba(74,144,217,0.08) 0%, rgba(124,185,240,0.12) 50%, rgba(74,144,217,0.06) 100%);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(180,210,240,0.3);
    border-radius: 28px;
    padding: 48px 40px;
    margin-bottom: 36px;
    text-align: center;
    box-shadow: 0 24px 80px rgba(74,144,217,0.1), inset 0 1px 0 rgba(255,255,255,0.6);
    position: relative;
    overflow: hidden;
    animation: heroFadeIn 1s ease-out;
}
@keyframes heroFadeIn {
    from { opacity: 0; transform: translateY(30px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hero-container::before {
    content: '';
    position: absolute;
    top: -60%; left: -30%; width: 160%; height: 160%;
    background: radial-gradient(ellipse at 30% 50%, rgba(124,185,240,0.15), transparent 70%);
    animation: auroraFloat 12s ease-in-out infinite alternate;
    pointer-events: none;
}
@keyframes auroraFloat {
    0%   { transform: translate(0, 0) rotate(0deg); }
    100% { transform: translate(40px, -20px) rotate(5deg); }
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, #2E6AB0 0%, #4A90D9 45%, #7CB9F0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 10px;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 1;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: var(--text-secondary);
    font-weight: 400;
    max-width: 620px;
    margin: 0 auto;
    line-height: 1.7;
    position: relative;
    z-index: 1;
}

/* ── Section headers ─────────────────────────────────────────────────────── */
.section-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 8px;
}
.section-icon {
    width: 44px; height: 44px;
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    background: var(--gradient-accent);
    color: white;
    box-shadow: 0 6px 20px rgba(74,144,217,0.25);
    flex-shrink: 0;
}
.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
}
.section-desc {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin: 0 0 0 58px;
    line-height: 1.5;
}

/* ── Stat pill ───────────────────────────────────────────────────────────── */
.stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(74,144,217,0.08);
    border: 1px solid rgba(74,144,217,0.15);
    border-radius: 100px;
    padding: 8px 18px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--accent-dark);
    margin: 4px;
}
.stat-pill .stat-num {
    font-weight: 700;
    color: var(--accent);
}

/* ── Chat message bubbles ────────────────────────────────────────────────── */
.chat-user {
    background: var(--gradient-accent);
    color: white;
    padding: 14px 20px;
    border-radius: 20px 20px 6px 20px;
    margin: 8px 0 8px auto;
    max-width: 75%;
    font-size: 0.95rem;
    box-shadow: 0 4px 16px rgba(74,144,217,0.2);
    width: fit-content;
    margin-left: auto;
}
.chat-bot {
    background: rgba(255,255,255,0.7);
    border: 1px solid var(--border-glass);
    color: var(--text-primary);
    padding: 14px 20px;
    border-radius: 20px 20px 20px 6px;
    margin: 8px auto 8px 0;
    max-width: 75%;
    font-size: 0.95rem;
    box-shadow: var(--shadow-soft);
    width: fit-content;
    backdrop-filter: blur(8px);
}

/* ── Pipeline step indicator ─────────────────────────────────────────────── */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 20px;
    border-radius: 14px;
    margin: 6px 0;
    font-size: 0.92rem;
    font-weight: 500;
    transition: var(--transition);
}
.pipeline-step.active {
    background: rgba(74,144,217,0.1);
    border-left: 3px solid var(--accent);
    color: var(--accent-dark);
}
.pipeline-step.done {
    background: rgba(50,180,130,0.08);
    border-left: 3px solid #32B482;
    color: #1E7A54;
}
.pipeline-step.waiting {
    background: rgba(0,0,0,0.02);
    border-left: 3px solid #D0D8E0;
    color: var(--text-muted);
}

/* ── Streamlit overrides ─────────────────────────────────────────────────── */
.stButton > button {
    background: var(--gradient-accent) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 12px 32px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    box-shadow: 0 6px 24px rgba(74,144,217,0.25) !important;
    transition: var(--transition) !important;
    letter-spacing: 0.2px !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 36px rgba(74,144,217,0.35) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}

/* download buttons keep their own style */
.stDownloadButton > button {
    background: rgba(255,255,255,0.7) !important;
    color: var(--accent-dark) !important;
    border: 1px solid var(--border-glass) !important;
    box-shadow: var(--shadow-soft) !important;
}
.stDownloadButton > button:hover {
    background: rgba(255,255,255,0.9) !important;
    transform: translateY(-2px) !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.6) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-primary) !important;
    backdrop-filter: blur(8px) !important;
    transition: var(--transition) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-light) !important;
    box-shadow: 0 0 0 3px rgba(74,144,217,0.12) !important;
}

.stSelectbox > div > div {
    background: rgba(255,255,255,0.6) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    backdrop-filter: blur(8px) !important;
}

.stFileUploader > div {
    background: rgba(255,255,255,0.45) !important;
    border: 2px dashed rgba(74,144,217,0.3) !important;
    border-radius: var(--radius) !important;
    transition: var(--transition) !important;
}
.stFileUploader > div:hover {
    border-color: var(--accent) !important;
    background: rgba(255,255,255,0.6) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px !important;
    background: rgba(255,255,255,0.3) !important;
    border-radius: 14px !important;
    padding: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-secondary) !important;
    padding: 8px 20px !important;
}
.stTabs [aria-selected="true"] {
    background: var(--gradient-accent) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(74,144,217,0.2) !important;
}

div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.45) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    backdrop-filter: blur(8px) !important;
}

.stSpinner > div > div {
    border-top-color: var(--accent) !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(74,144,217,0.2);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(74,144,217,0.4); }

/* ── Content fade-in animation ───────────────────────────────────────────── */
.fade-in {
    animation: fadeSlideUp 0.6s ease-out forwards;
    opacity: 0;
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in-delay { animation-delay: 0.15s; }
.fade-in-delay2 { animation-delay: 0.3s; }
.fade-in-delay3 { animation-delay: 0.45s; }

/* ── Floating particles (pure CSS) ───────────────────────────────────────── */
.particles {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}
.particles span {
    position: absolute;
    width: 6px; height: 6px;
    background: rgba(74,144,217,0.1);
    border-radius: 50%;
    animation: floatParticle 18s linear infinite;
}
.particles span:nth-child(1) { left: 10%; animation-delay: 0s;  width: 8px; height: 8px; }
.particles span:nth-child(2) { left: 25%; animation-delay: 3s;  width: 5px; height: 5px; }
.particles span:nth-child(3) { left: 45%; animation-delay: 6s;  width: 7px; height: 7px; }
.particles span:nth-child(4) { left: 65%; animation-delay: 2s;  width: 4px; height: 4px; }
.particles span:nth-child(5) { left: 80%; animation-delay: 8s;  width: 9px; height: 9px; }
.particles span:nth-child(6) { left: 90%; animation-delay: 4s;  width: 6px; height: 6px; }
@keyframes floatParticle {
    0%   { transform: translateY(100vh) rotate(0deg); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateY(-10vh) rotate(720deg); opacity: 0; }
}
</style>

<!-- Floating decorative particles -->
<div class="particles">
    <span></span><span></span><span></span>
    <span></span><span></span><span></span>
</div>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────

def render_hero():
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">🎬 AI Video Assistant</div>
        <div class="hero-subtitle">
            Transform any video or meeting into structured intelligence.<br>
            Powered by Whisper · Mistral AI · LangChain · ChromaDB
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_glass_card(icon, title, content_html, desc="", extra_class=""):
    st.markdown(f"""
    <div class="glass-card {extra_class}">
        <div class="section-header">
            <div class="section-icon">{icon}</div>
            <p class="section-title">{title}</p>
        </div>
        {"<p class='section-desc'>" + desc + "</p>" if desc else ""}
        <div style="margin-top:16px;">{content_html}</div>
    </div>
    """, unsafe_allow_html=True)


def render_pipeline_steps(current_step: int, steps: list[str]):
    html = ""
    for i, label in enumerate(steps):
        if i < current_step:
            icon = "✅"
            cls = "done"
        elif i == current_step:
            icon = "⏳"
            cls = "active"
        else:
            icon = "⬜"
            cls = "waiting"
        html += f'<div class="pipeline-step {cls}">{icon}&nbsp;&nbsp;{label}</div>'
    return html


def generate_pdf(result: dict) -> bytes:
    """Generate a clean PDF report of the analysis."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(46, 106, 176)
    pdf.cell(0, 14, "AI Video Assistant - Report", ln=True, align="C")
    pdf.ln(4)

    pdf.set_draw_color(74, 144, 217)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Sections
    sections = [
        ("Title", result.get("title", "")),
        ("Summary", result.get("summary", "")),
        ("Action Items", result.get("action_items", "")),
        ("Key Decisions", result.get("key_decisions", "")),
        ("Open Questions", result.get("open_questions", "")),
        ("Full Transcript", result.get("transcript", "")),
    ]

    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 43, 61)
        pdf.cell(0, 10, heading, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(74, 101, 128)
        # Encode to latin-1 safely
        safe_body = body.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 6, safe_body)
        pdf.ln(6)

    return bytes(pdf.output())


def generate_txt(result: dict) -> str:
    lines = [
        "=" * 60,
        "  AI VIDEO ASSISTANT — ANALYSIS REPORT",
        "=" * 60,
        "",
        f"TITLE: {result.get('title', 'N/A')}",
        "",
        "SUMMARY",
        "-" * 40,
        result.get("summary", ""),
        "",
        "ACTION ITEMS",
        "-" * 40,
        result.get("action_items", ""),
        "",
        "KEY DECISIONS",
        "-" * 40,
        result.get("key_decisions", ""),
        "",
        "OPEN QUESTIONS",
        "-" * 40,
        result.get("open_questions", ""),
        "",
        "FULL TRANSCRIPT",
        "-" * 40,
        result.get("transcript", ""),
        "",
        "=" * 60,
    ]
    return "\n".join(lines)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 12px 0 20px;">
        <div style="font-size:2.2rem; margin-bottom:4px;">🎬</div>
        <div style="font-size:1.1rem; font-weight:700; color:#2E6AB0;">AI Video Assistant</div>
        <div style="font-size:0.78rem; color:#7A95AD; margin-top:2px;">RAG-Powered Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Input mode
    input_mode = st.radio(
        "📥  Input Source",
        ["🔗 YouTube URL", "📁 Upload File"],
        index=0,
        help="Choose how to provide your video/audio"
    )

    youtube_url = ""
    uploaded_file = None

    if input_mode == "🔗 YouTube URL":
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            label_visibility="collapsed",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload audio / video",
            type=["mp3", "mp4", "wav", "m4a", "webm", "ogg", "flac", "mkv", "avi"],
            label_visibility="collapsed",
        )

    st.markdown("---")

    language = st.selectbox(
        "🌐  Transcript Language",
        ["english", "hinglish"],
        index=0,
        help="Select 'hinglish' for Hindi/mixed content (auto-translated to English)"
    )

    st.markdown("---")

    # Status indicator
    if "result" in st.session_state and st.session_state.result:
        st.markdown("""
        <div style="text-align:center; padding:12px; background:rgba(50,180,130,0.08);
                    border-radius:12px; border:1px solid rgba(50,180,130,0.2);">
            <div style="font-size:1.2rem;">✅</div>
            <div style="font-size:0.82rem; font-weight:600; color:#1E7A54; margin-top:4px;">
                Analysis Complete
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:12px; background:rgba(74,144,217,0.06);
                    border-radius:12px; border:1px solid rgba(74,144,217,0.12);">
            <div style="font-size:1.2rem;">💡</div>
            <div style="font-size:0.82rem; font-weight:500; color:#4A6580; margin-top:4px;">
                Provide a source & click Analyze
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#A0B4C8; text-align:center; line-height:1.7;">
        Whisper · Mistral AI · LangChain<br>
        ChromaDB · HuggingFace<br><br>
        Built with ❤️
    </div>
    """, unsafe_allow_html=True)


# ── Main area ─────────────────────────────────────────────────────────────────

# Session state defaults
if "result" not in st.session_state:
    st.session_state.result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

render_hero()

# ── Analyze button ────────────────────────────────────────────────────────────
has_source = bool(youtube_url.strip()) or (uploaded_file is not None)

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    analyze_clicked = st.button(
        "🚀  Analyze Video" if has_source else "⬅  Select a Source First",
        use_container_width=True,
        disabled=not has_source,
        key="analyze_btn",
    )

# ── Processing pipeline ──────────────────────────────────────────────────────
if analyze_clicked and has_source:
    # Reset previous
    st.session_state.result = None
    st.session_state.chat_history = []

    steps = [
        "Downloading / loading audio",
        "Chunking audio into segments",
        "Transcribing with Whisper",
        "Generating title",
        "Creating executive summary",
        "Extracting action items",
        "Extracting key decisions",
        "Extracting open questions",
        "Building RAG engine",
    ]

    # Resolve source path
    if uploaded_file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
        tmp.write(uploaded_file.read())
        tmp.flush()
        source_path = tmp.name
    else:
        source_path = youtube_url.strip()

    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    try:
        from utils.audio_processor import process_input, get_last_media_title
        from core.transcriber import transcribe_all
        from core.summarize import summarize, generate_title
        from core.extractor import extract_action_items, extract_key_decisions, extract_questions
        from core.rag_engine import build_rag_chain

        # Step 1-2: Process input
        progress_placeholder.markdown(render_pipeline_steps(0, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Downloading and processing audio...")
        chunks = process_input(source_path)

        # Step 3: Transcribe
        progress_placeholder.markdown(render_pipeline_steps(2, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Transcribing audio with Whisper AI...")
        transcript = transcribe_all(chunks, language)

        # Step 4: Title
        progress_placeholder.markdown(render_pipeline_steps(3, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Generating title...")
        media_title = get_last_media_title()
        title = media_title or generate_title(transcript)

        # Step 5: Summary
        progress_placeholder.markdown(render_pipeline_steps(4, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Creating executive summary...")
        summary_text = summarize(transcript)

        # Step 6: Action items
        progress_placeholder.markdown(render_pipeline_steps(5, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Extracting action items...")
        action_items = extract_action_items(transcript)

        # Step 7: Key decisions
        progress_placeholder.markdown(render_pipeline_steps(6, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Extracting key decisions...")
        decisions = extract_key_decisions(transcript)

        # Step 8: Open questions
        progress_placeholder.markdown(render_pipeline_steps(7, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Extracting open questions...")
        questions = extract_questions(transcript)

        # Step 9: RAG
        progress_placeholder.markdown(render_pipeline_steps(8, steps), unsafe_allow_html=True)
        status_placeholder.info("⏳ Building RAG knowledge engine...")
        rag_chain = build_rag_chain(transcript)

        # Done
        progress_placeholder.markdown(render_pipeline_steps(len(steps), steps), unsafe_allow_html=True)
        status_placeholder.success("✅ Analysis complete! Scroll down for results.")

        st.session_state.result = {
            "title": title,
            "transcript": transcript,
            "summary": summary_text,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
            "rag_chain": rag_chain,
        }

        time.sleep(1.5)
        progress_placeholder.empty()
        status_placeholder.empty()
        st.rerun()

    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.error(f"❌ Error during processing: {e}")
        st.stop()


# ── Results dashboard ─────────────────────────────────────────────────────────
result = st.session_state.result

if result:
    # ── Stats bar
    word_count = len(result["transcript"].split()) if result["transcript"] else 0
    char_count = len(result["transcript"]) if result["transcript"] else 0
    st.markdown(f"""
    <div class="glass-card fade-in" style="text-align:center; padding:20px 32px;">
        <span class="stat-pill">📌 <span class="stat-num">{len(result.get("title",""))}</span> char title</span>
        <span class="stat-pill">📝 <span class="stat-num">{word_count:,}</span> words</span>
        <span class="stat-pill">🔤 <span class="stat-num">{char_count:,}</span> characters</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Title card
    render_glass_card(
        "📌", result.get("title", "Untitled"),
        f"<p style='font-size:1.1rem; font-weight:600; color:var(--accent-dark);'>{result.get('title','')}</p>",
        extra_class="fade-in"
    )

    # ── Tabbed content
    tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript = st.tabs([
        "📋  Summary",
        "✅  Action Items",
        "🔑  Key Decisions",
        "❓  Open Questions",
        "📄  Full Transcript",
    ])

    with tab_summary:
        render_glass_card(
            "📋", "Executive Summary",
            f"<div style='white-space:pre-wrap; line-height:1.8; color:var(--text-secondary); font-size:0.95rem;'>{result.get('summary','')}</div>",
            desc="AI-generated structured summary of the content",
            extra_class="fade-in"
        )

    with tab_actions:
        render_glass_card(
            "✅", "Action Items",
            f"<div style='white-space:pre-wrap; line-height:1.8; color:var(--text-secondary); font-size:0.95rem;'>{result.get('action_items','')}</div>",
            desc="Tasks, follow-ups, and assigned responsibilities",
            extra_class="fade-in"
        )

    with tab_decisions:
        render_glass_card(
            "🔑", "Key Decisions",
            f"<div style='white-space:pre-wrap; line-height:1.8; color:var(--text-secondary); font-size:0.95rem;'>{result.get('key_decisions','')}</div>",
            desc="Agreements, conclusions, and resolutions",
            extra_class="fade-in"
        )

    with tab_questions:
        render_glass_card(
            "❓", "Open Questions",
            f"<div style='white-space:pre-wrap; line-height:1.8; color:var(--text-secondary); font-size:0.95rem;'>{result.get('open_questions','')}</div>",
            desc="Unanswered queries and unresolved discussion points",
            extra_class="fade-in"
        )

    with tab_transcript:
        render_glass_card(
            "📄", "Full Transcript",
            f"<div style='white-space:pre-wrap; line-height:1.8; color:var(--text-secondary); font-size:0.92rem; max-height:500px; overflow-y:auto; padding-right:8px;'>{result.get('transcript','')}</div>",
            desc="Complete Whisper-generated transcript",
            extra_class="fade-in"
        )

    # ── Export section
    st.markdown("<br>", unsafe_allow_html=True)
    render_glass_card(
        "💾", "Export Report",
        "",
        desc="Download your analysis as PDF or TXT",
        extra_class="fade-in fade-in-delay"
    )
    exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 1])
    with exp_col1:
        pdf_bytes = generate_pdf(result)
        st.download_button(
            "📥  Download PDF",
            data=pdf_bytes,
            file_name="ai_video_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with exp_col2:
        txt_content = generate_txt(result)
        st.download_button(
            "📥  Download TXT",
            data=txt_content,
            file_name="ai_video_report.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with exp_col3:
        st.download_button(
            "📥  Transcript Only",
            data=result.get("transcript", ""),
            file_name="transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="glass-card fade-in fade-in-delay2">
        <div class="section-header">
            <div class="section-icon">💬</div>
            <p class="section-title">Chat with Your Video</p>
        </div>
        <p class="section-desc">Ask anything — the RAG engine searches the transcript and synthesizes answers</p>
    </div>
    """, unsafe_allow_html=True)

    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bot">{msg["content"]}</div>', unsafe_allow_html=True)

    # Chat input
    user_question = st.chat_input("Ask a question about the video...", key="rag_chat_input")

    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        st.markdown(f'<div class="chat-user">{user_question}</div>', unsafe_allow_html=True)

        from core.rag_engine import ask_question

        with st.spinner("🔍 Searching transcript..."):
            answer = ask_question(result.get("rag_chain"), user_question)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.markdown(f'<div class="chat-bot">{answer}</div>', unsafe_allow_html=True)

else:
    # ── Empty state — show feature cards ──────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="glass-card fade-in" style="text-align:center; min-height:220px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">🎙️</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                Whisper Transcription
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Local AI-powered speech-to-text with support for English and Hinglish audio
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="glass-card fade-in fade-in-delay" style="text-align:center; min-height:220px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">🧠</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                Mistral AI Analysis
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Executive summaries, action items, key decisions & open questions via LLM
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="glass-card fade-in fade-in-delay2" style="text-align:center; min-height:220px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">💬</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                RAG-Powered Chat
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Ask questions — ChromaDB + LangChain retrieve context and synthesize answers
            </div>
        </div>
        """, unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown("""
        <div class="glass-card fade-in fade-in-delay" style="text-align:center; min-height:200px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">🎥</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                YouTube & Local Files
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Paste any YouTube URL or upload MP3, MP4, WAV, and more formats
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown("""
        <div class="glass-card fade-in fade-in-delay2" style="text-align:center; min-height:200px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">🌐</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                Multilingual Support
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Handles Hindi / Hinglish audio with automatic translation to English
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown("""
        <div class="glass-card fade-in fade-in-delay3" style="text-align:center; min-height:200px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">💾</div>
            <div style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                Export to PDF / TXT
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.6;">
                Download structured reports with summaries, action items, and full transcripts
            </div>
        </div>
        """, unsafe_allow_html=True)
