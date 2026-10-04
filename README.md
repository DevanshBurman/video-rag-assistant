# Video RAG Assistant 🎥⚡

> **Multimodal Video Intelligence Studio**: Robust multi-tier YouTube ingestion, hosted Groq Whisper speech recognition, Map-Reduce executive deliverables via Mistral AI, and timestamp-grounded Q&A via ephemeral in-memory ChromaDB MMR vector retrieval.

---

## 🌟 Key Capabilities & Architectural Upgrades

- **Cloud-Hardened YouTube Ingestion**:
  - **Tier 1 (Instant)**: Direct `youtube_transcript_api` caption fetching with proxy support (`PROXY_URL` or residential rotating `WEBSHARE_PROXY_USERNAME` / `WEBSHARE_PROXY_PASSWORD`). Bypasses datacenter IP blocks completely.
  - **Tier 2 (Fallback 1)**: Subtitle-only extraction via `yt-dlp` (`json3`/`vtt`) with zero audio download overhead and embedded Node.js JS runtime.
  - **Tier 3 (Fallback 2)**: Client retry loop (`["tv", "web_safari", "mweb"]`) with audio download, max duration guard (`MAX_VIDEO_MINUTES`), and cookie support (`YOUTUBE_COOKIES`).
  - **Tier 4 (User Guidance)**: Friendly UI fallback allowing instant audio/video file drop or direct transcript paste.
- **Render Resource Optimization (Zero-Torch in Production)**:
  - Default speech-to-text uses **Groq Whisper API** (`whisper-large-v3-turbo`) with 16kHz mono chunking (<=24MB per request).
  - Embeddings use **Mistral API** (`mistral-embed`) or lightweight **FastEmbed ONNX** (`BAAI/bge-small-en-v1.5`), completely eliminating PyTorch and sentence-transformers from memory.
  - **Ephemeral In-Memory ChromaDB**: Per-session ephemeral collections with automatic 1-hour TTL cleanup and max session count.
- **Map-Reduce Long Video Analysis**:
  - Replaces rigid string truncation with concurrent chunked Map-Reduce (8,000-character chunks with overlap) and exponential backoff retry on Mistral 429 rate limits.
  - MMR (Maximal Marginal Relevance) RAG retrieval citing specific video segments (e.g. `[From Part 2 of 5 (~01:40)]`).

---

## 🏗️ Ingestion & Processing Architecture

```
[ Ingest Request: YouTube URL / File / Pasted Text ]
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
[ Pasted Text ]  [ Uploaded File ]  [ YouTube URL ]
       │               │               │
       │               │        (Tier 1: youtube_transcript_api + proxy)
       │               │        (Tier 2: yt-dlp subtitle-only)
       │               │        (Tier 3: yt-dlp audio download)
       │               │               │
       │         [ Audio Slicing ] ◄───┘
       │         (16kHz Mono MP3)
       │               │
       │         [ Groq Whisper STT ]
       │               │
       └───────┬───────┘
               ▼
    [ Full Clean Transcript ]
               │
       ┌───────┴───────────────────────────────┐
       ▼                                       ▼
[ Map-Reduce Mistral Synthesis ]    [ Ephemeral Chroma Vector Store ]
 • Title (First 4,000 chars)         • Chunk metadata & timestamps
 • Executive Summary                 • MMR retrieval (k=4)
 • Action Items Checklist            • Grounded citations
 • Key Decisions & Questions         • Out-of-context polite fallback
```

---

## 🚀 Getting Started Locally

### 1. Prerequisites
- Python 3.10+
- FFmpeg installed and available on system `PATH`
- Node.js installed (used by yt-dlp for JavaScript challenge extraction)

### 2. Clone & Setup
```bash
git clone https://github.com/DevanshBurman/video-rag-assistant.git
cd video-rag-assistant

python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your API keys in `.env`:
```env
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-small-latest
GROQ_API_KEY=your_groq_api_key
TRANSCRIBER_BACKEND=groq
```

### 4. Run the Server
```bash
python server.py
```
Access the studio at `http://localhost:8000`.

---

## ☁️ Deployment on Render

This repository includes a production-ready `Dockerfile` and `render.yaml`.

### Step-by-Step Render Deployment
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New → Web Service**.
2. Connect your repository: `DevanshBurman/video-rag-assistant`.
3. Choose **Docker** as the environment (Render will build using `Dockerfile`).
4. Set **Health Check Path** to `/health`.
5. Under **Environment Variables**, configure:
   - `MISTRAL_API_KEY`: Your Mistral AI API key *(Required)*
   - `MISTRAL_MODEL`: `mistral-small-latest` *(Default)*
   - `GROQ_API_KEY`: Your Groq API key *(Required for audio transcription)*
   - `TRANSCRIBER_BACKEND`: `groq` *(Default)*
   - `MAX_VIDEO_MINUTES`: `90`
   - `ADMIN_TOKEN`: A secret token to protect `/debug/youtube`
   - *(Optional)* `PROXY_URL`: `http://user:pass@proxy-server:port`
   - *(Optional)* `WEBSHARE_PROXY_USERNAME` & `WEBSHARE_PROXY_PASSWORD`: Webshare residential rotating proxy
   - *(Optional)* `YOUTUBE_COOKIES`: Raw Netscape cookie content
6. Click **Deploy Web Service**!

---

## 🛡️ Setting Proxies & YouTube Cookies

Cloud hosting platforms (Render, AWS, Railway) have their IP ranges blocked by YouTube. Configure proxies or cookies to guarantee 100% extraction:

### Option 1: Webshare Rotating Residential Proxy (Recommended)
1. Sign up at [Webshare.io](https://www.webshare.io/) and purchase a **Residential Proxy** package.
2. In your Render Environment Variables, add:
   ```env
   WEBSHARE_PROXY_USERNAME=your_webshare_username
   WEBSHARE_PROXY_PASSWORD=your_webshare_password
   ```
   The application automatically initializes `WebshareProxyConfig` with rotating residential IPs.

### Option 2: Generic HTTP / SOCKS5 Proxy
If you have an HTTP, HTTPS, or SOCKS5 proxy:
```env
PROXY_URL=http://user:password@proxy.example.com:8080
```
This is passed to both `youtube_transcript_api` and `yt-dlp`.

### Option 3: YouTube Cookies
To bypass bot detection or access age-restricted videos:
1. Install a browser extension like *Get cookies.txt LOCALLY*.
2. Export your cookies for `youtube.com` in Netscape format.
3. In Render, paste the entire file contents into the `YOUTUBE_COOKIES` environment variable (or save locally as `cookies.txt`).

---

## 🧪 Testing with 3 Kinds of Video

You can verify the multi-tier pipeline using our automated test script or via the `/debug/youtube` endpoint.

### Run Automated Pipeline Tests Locally
```bash
python test_pipeline.py
```
This verifies:
1. Health endpoint (`/health`)
2. Local audio conversion, chunking, and metadata-grounded MMR RAG
3. YouTube transcript extraction, title generation, Map-Reduce summary, action item checklist, decision log, open questions, and live Q&A

### 1. Video with Captions (Instant Tier 1)
- **URL**: `https://www.youtube.com/watch?v=jNQXAC9IVRw` ("Me at the zoo")
- **Behavior**: Direct `youtube_transcript_api` fetches official English subtitles in under 2 seconds. No audio download is triggered.

### 2. Video without Captions (Tier 2 & Tier 3 Fallback)
- **Behavior**:
  - Step 1 checks for direct captions (fails gracefully and logs `NoTranscriptFound`).
  - Step 2 checks for auto-subtitles via `yt-dlp`.
  - Step 3 downloads audio via `yt-dlp` using resilient client configurations (`tv` / `web_safari`), compresses to 16kHz mono chunks, and transcribes via Groq Whisper API.

### 3. Long Video (>60 Minutes)
- **Behavior**:
  - Pre-download check validates that duration is within `MAX_VIDEO_MINUTES` (default 90 mins).
  - Splits transcript into ~8,000-character overlapping chunks.
  - Runs parallel Map prompts across chunks and reduces them into a unified Executive Summary and Action Items checklist without hitting token limits or 429 rate limit errors.

---

## 🔍 Diagnostic Endpoints

- **`GET /health`**: Returns service status and active background job count.
- **`GET /debug/youtube?url=<YOUTUBE_URL>&token=<ADMIN_TOKEN>`**: Runs a diagnostic probe testing:
  - oEmbed video metadata
  - `youtube_transcript_api` connection & proxy status
  - `yt-dlp` subtitle extraction
  - `yt-dlp` player client format availability

---

## 📦 Project Structure

```
├── core/
│   ├── extractor.py        # Map-Reduce action items, decisions & questions
│   ├── llm_utils.py        # Map-Reduce engine & Mistral 429 backoff retry
│   ├── rag_engine.py       # MMR retrieval with timestamp metadata citations
│   ├── summarize.py        # Map-Reduce executive summaries & title generator
│   ├── transcriber.py      # Groq Whisper API STT & lazy local Whisper fallback
│   └── vector_store.py     # Ephemeral in-memory ChromaDB & Mistral/FastEmbed embeddings
├── utils/
│   └── audio_processor.py  # 3-tier YouTube pipeline, proxies, cookies, and chunking
├── static/                 # Glassmorphic Studio Frontend
│   ├── index.html          # UI with URL, File Upload, and Paste Transcript tabs
│   ├── styles.css          # Design system & dark/light mode tokens
│   └── app.js              # State manager, background job polling & Q&A controller
├── server.py               # FastAPI backend with /process, /status, /health & /debug
├── test_pipeline.py        # Local end-to-end verification script
├── Dockerfile              # Multi-stage python:3.11-slim image with ffmpeg & nodejs
├── render.yaml             # Render deployment configuration
├── requirements.txt        # Pinned dependencies (zero PyTorch in production)
└── .env.example            # Environment variables reference
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
