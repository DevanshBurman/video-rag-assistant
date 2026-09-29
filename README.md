# Video RAG Assistant 🎥⚡

> **Multimodal Video Intelligence Studio**: Sub-second acoustic transcription, structured executive deliverables via Mistral 7B, and timestamp-grounded Q&A via ChromaDB vector retrieval.

---

## 🌟 Key Capabilities

- **Universal Ingestion**: Stream extraction from YouTube URLs (Shorts, long-form videos, live stream VODs) or direct file uploads (`.mp4`, `.mp3`, `.wav`, `.m4a`, `.webm`, `.flac`).
- **Acoustic Normalization & Slicing**: Normalizes incoming streams to 16kHz mono audio and partitions recordings into parallelizable 10-minute acoustic chunks with zero clip degradation.
- **Whisper AI Speech Recognition**: High-precision transformer-based phoneme decoding with natural punctuation restoration and multi-speaker preservation.
- **Mistral 7B Structured Synthesis**: Generates four discrete deliverables:
  - 📋 **Executive Briefing & Summary**: Core takeaway synthesis without filler.
  - ☑️ **Action Items**: Discrete, checkable commitments and deliverables.
  - 🏛️ **Key Decisions**: Explicitly agreed outcomes and strategic directions.
  - ❓ **Open Questions**: Unresolved topics and follow-up inquiries.
- **Timestamp-Grounded ChromaDB Vector RAG**: Transcript chunks are converted into dense vector embeddings. Interactive chat queries retrieve semantic passages to provide factual answers citing exact timestamps (e.g. `[04:12 - 04:35]`).
- **Dual-Theme Studio Interface**: Full dark and light mode adaptation with smooth view transitions, progress tracking, and one-click PDF/TXT report exports.

---

## 🏗️ Architecture

```
[ YouTube URL / Local Media ]
              │
              ▼
   [ Audio Extraction & 16kHz Slicing ]
              │
              ▼
   [ Whisper AI Transcription ]
         │                │
         ▼                ▼
[ Mistral 7B LLM ]   [ ChromaDB Vector Space ]
         │                        │
         ▼                        ▼
[ Structured Deliverables ]  [ Grounded RAG Chat ]
(Summary, Actions, Decisions)  (Timestamp Citations)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- FFmpeg installed and available on your system `PATH`

### 2. Clone the Repository
```bash
git clone https://github.com/DevanshBurman/video-rag-assistant.git
cd video-rag-assistant
```

### 3. Set Up Virtual Environment
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=open-mistral-7b
WHISPER_MODEL=base
```

### 6. Run the Studio Server
```bash
python server.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## ☁️ Cloud Deployment

### Deploy on Render (Recommended)
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New → Web Service**.
2. Connect your GitHub repository: `DevanshBurman/video-rag-assistant`.
3. Select **Docker** as the runtime (Render will automatically detect the [`Dockerfile`](Dockerfile)).
4. Under **Instance Type**, select **Starter** (or higher, since Whisper + PyTorch benefits from 1GB+ RAM).
5. Under **Environment Variables**, add:
   - `MISTRAL_API_KEY`: Your Mistral AI API key
   - `MISTRAL_MODEL`: `open-mistral-7b`
   - `WHISPER_MODEL`: `base`
6. Click **Deploy Web Service**!

### Deploy on Railway
1. Go to [Railway Dashboard](https://railway.app/) and click **New Project → Deploy from GitHub repo**.
2. Select `video-rag-assistant`.
3. In service **Variables**, add:
   - `MISTRAL_API_KEY`: Your Mistral AI API key
   - `MISTRAL_MODEL`: `open-mistral-7b`
   - `WHISPER_MODEL`: `base`
4. Railway will automatically build the Dockerfile with FFmpeg pre-installed and assign a live public domain!

---

## 📦 Project Structure

```
├── core/                   # Core pipeline modules
│   ├── downloader.py       # yt-dlp & file ingestion
│   ├── transcriber.py      # Whisper acoustic decoding & segmenting
│   ├── summarizer.py       # Mistral 7B extraction & synthesis
│   └── rag_engine.py       # ChromaDB vector indexing & retrieval
├── static/                 # Frontend assets
│   ├── index.html          # Studio UI
│   ├── styles.css          # Design system & dark/light theme tokens
│   ├── app.js              # Client state & interactive controller
│   └── assets/             # Icons & UI preview snapshots
├── utils/                  # Exporters & formatters (PDF/TXT)
├── server.py               # FastAPI backend & asynchronous tasks
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
└── README.md
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
