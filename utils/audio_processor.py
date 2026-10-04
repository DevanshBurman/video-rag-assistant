import os
import re
import json
import uuid
import tempfile
import urllib.request
import logging
from pydub import AudioSegment
import yt_dlp

logger = logging.getLogger("audio_processor")
logger.setLevel(logging.INFO)

# Ensure static_ffmpeg binaries (ffmpeg, ffprobe) are registered in PATH
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class MediaIngestionError(Exception):
    """Clean, user-friendly exception for media ingestion failures."""
    def __init__(self, message: str, code: str = "INGESTION_FAILED", technical_details: str = ""):
        super().__init__(message)
        self.code = code
        self.technical_details = technical_details

def extract_youtube_id(url: str) -> str | None:
    """Extract the 11-character YouTube video ID from various URL formats."""
    if not url:
        return None
    patterns = [
        r'(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/shorts\/|\/live\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None

def fetch_youtube_oembed_title(video_id: str) -> str | None:
    """Fetch video title using YouTube's public oEmbed endpoint without auth or bot blocks."""
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title")
    except Exception as e:
        logger.debug(f"[oEmbed Notice] Could not fetch oEmbed title for {video_id}: {e}")
        return None

def get_proxy_config():
    """
    Construct proxy configuration for youtube_transcript_api and yt-dlp.
    Checks WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD first, then PROXY_URL.
    """
    webshare_user = (os.getenv("WEBSHARE_PROXY_USERNAME") or "").strip()
    webshare_pass = (os.getenv("WEBSHARE_PROXY_PASSWORD") or "").strip()
    proxy_url = (os.getenv("PROXY_URL") or "").strip()

    if webshare_user and webshare_pass:
        try:
            from youtube_transcript_api.proxies import WebshareProxyConfig
            return WebshareProxyConfig(proxy_username=webshare_user, proxy_password=webshare_pass)
        except Exception as e:
            logger.warning(f"[Proxy] WebshareProxyConfig failed to initialize: {e}")

    if proxy_url:
        try:
            from youtube_transcript_api.proxies import GenericProxyConfig
            return GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        except Exception as e:
            logger.warning(f"[Proxy] GenericProxyConfig failed to initialize: {e}")

    return None

def get_proxy_url_string() -> str | None:
    """Return plain string proxy URL for yt-dlp or requests."""
    webshare_user = (os.getenv("WEBSHARE_PROXY_USERNAME") or "").strip()
    webshare_pass = (os.getenv("WEBSHARE_PROXY_PASSWORD") or "").strip()
    if webshare_user and webshare_pass:
        return f"http://{webshare_user}:{webshare_pass}@p.webshare.io:80"

    proxy_url = (os.getenv("PROXY_URL") or "").strip()
    return proxy_url if proxy_url else None

def get_cookie_file_path() -> str | None:
    """Return path to cookies file if YOUTUBE_COOKIES or cookies.txt exists."""
    cookies_env = os.environ.get("YOUTUBE_COOKIES", "").strip()
    if cookies_env:
        temp_cookie_path = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
        try:
            with open(temp_cookie_path, "w", encoding="utf-8") as f:
                f.write(cookies_env)
            return temp_cookie_path
        except Exception as e:
            logger.warning(f"[Warning] Failed to write temporary cookie file: {e}")

    cookie_candidate = os.environ.get("YOUTUBE_COOKIE_FILE") or "cookies.txt"
    if os.path.exists(cookie_candidate):
        return cookie_candidate

    return None

def is_url(source: str) -> bool:
    """Check if the source string is a web / YouTube URL."""
    if not source:
        return False
    s = source.strip().lower()
    return (
        s.startswith("http://")
        or s.startswith("https://")
        or s.startswith("www.")
        or "youtube.com" in s
        or "youtu.be" in s
    )

def normalize_url(url: str) -> str:
    """Ensure URL has a valid scheme and is stripped."""
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u

# ── STAGE 1: Direct YouTube Transcript API ─────────────────────────────────────

def extract_youtube_transcript_direct(url_or_id: str, language: str = "english") -> tuple[str | None, str | None, dict]:
    """
    Stage 1: Official captions endpoint via youtube_transcript_api with proxy and exception logging.
    Preference:
      1. Manual English captions
      2. Auto-generated English captions
      3. Any language translated to English
      4. Any available caption track
    Returns (transcript_text, title, diagnostic_info).
    """
    video_id = extract_youtube_id(url_or_id)
    if not video_id:
        return None, None, {"status": "error", "error": "Invalid YouTube URL or ID"}

    title = fetch_youtube_oembed_title(video_id)
    diag = {"status": "attempted", "video_id": video_id, "stage": "youtube_transcript_api"}

    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
        try:
            from youtube_transcript_api import RequestBlocked, IpBlocked
        except ImportError:
            RequestBlocked = Exception
            IpBlocked = Exception

        proxy_cfg = get_proxy_config()
        api = YouTubeTranscriptApi(proxy_config=proxy_cfg)

        snippets = None
        selected_type = "unknown"

        try:
            t_list = api.list(video_id)

            # 1. Prefer manual English captions (or Hindi if requested)
            target_langs = ["hi", "en"] if "hin" in (language or "").lower() else ["en", "en-US", "en-GB"]
            try:
                manual_t = t_list.find_manually_created_transcript(target_langs)
                snippets = manual_t.fetch()
                selected_type = f"manual ({manual_t.language_code})"
            except Exception:
                pass

            # 2. Try auto-generated captions
            if not snippets:
                try:
                    gen_t = t_list.find_generated_transcript(target_langs)
                    snippets = gen_t.fetch()
                    selected_type = f"auto-generated ({gen_t.language_code})"
                except Exception:
                    pass

            # 3. Try any translatable caption translated to English
            if not snippets:
                for t in t_list:
                    if getattr(t, "is_translatable", False):
                        try:
                            snippets = t.translate("en").fetch()
                            selected_type = f"translated-to-en (from {t.language_code})"
                            break
                        except Exception:
                            pass

            # 4. Fallback to any transcript in the list
            if not snippets:
                for t in t_list:
                    try:
                        snippets = t.fetch()
                        selected_type = f"fallback ({t.language_code})"
                        break
                    except Exception:
                        pass

        except (RequestBlocked, IpBlocked) as e:
            logger.warning(f"[YouTubeTranscriptApi] Request/IP blocked for {video_id}: {e}")
            diag["error"] = f"IP/Request Blocked: {type(e).__name__}"
            return None, title, diag
        except TranscriptsDisabled as e:
            logger.info(f"[YouTubeTranscriptApi] Transcripts disabled for {video_id}: {e}")
            diag["error"] = "TranscriptsDisabled"
            return None, title, diag
        except NoTranscriptFound as e:
            logger.info(f"[YouTubeTranscriptApi] No transcripts found for {video_id}: {e}")
            diag["error"] = "NoTranscriptFound"
            return None, title, diag
        except VideoUnavailable as e:
            logger.warning(f"[YouTubeTranscriptApi] Video unavailable {video_id}: {e}")
            diag["error"] = "VideoUnavailable"
            return None, title, diag
        except Exception as e:
            logger.info(f"[YouTubeTranscriptApi] Transcript listing failed ({type(e).__name__}: {e}). Trying direct fetch...")
            try:
                snippets = api.fetch(video_id)
                selected_type = "direct-fetch"
            except Exception as direct_err:
                diag["error"] = f"Direct fetch failed: {type(direct_err).__name__}: {direct_err}"
                return None, title, diag

        if snippets:
            lines = []
            for s in snippets:
                txt = getattr(s, "text", "") if hasattr(s, "text") else (s.get("text", "") if isinstance(s, dict) else str(s))
                txt = txt.strip()
                if txt:
                    lines.append(txt)
            transcript = " ".join(lines).strip()
            if transcript:
                logger.info(f"[YouTubeTranscriptApi] Extracted {len(lines)} caption segments ({selected_type}) for video {video_id}.")
                diag["status"] = "success"
                diag["segments"] = len(lines)
                diag["type"] = selected_type
                return transcript, title, diag

    except Exception as e:
        logger.warning(f"[YouTubeTranscriptApi] General failure for {video_id}: {type(e).__name__}: {e}")
        diag["error"] = f"{type(e).__name__}: {e}"

    return None, title, diag

# ── STAGE 2: Fallback 1 - yt-dlp Subtitle Extraction ───────────────────────────

def _parse_json3(content: str) -> str:
    """Extract plain text from YouTube json3 subtitle format."""
    try:
        data = json.loads(content)
        lines = []
        for event in data.get("events", []):
            segs = event.get("segs", [])
            seg_text = "".join(s.get("utf8", "") for s in segs).strip()
            if seg_text and seg_text != "\n":
                lines.append(seg_text)
        return " ".join(lines).strip()
    except Exception:
        return ""

def _parse_vtt(content: str) -> str:
    """Extract and deduplicate plain text from WebVTT subtitle format."""
    lines = []
    seen = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
            continue
        cleaned = re.sub(r"<[^>]+>", "", line).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            lines.append(cleaned)
    return " ".join(lines).strip()

def extract_youtube_subtitles_ytdlp(url: str) -> tuple[str | None, str | None, dict]:
    """
    Fallback 1: yt-dlp subtitle-only extraction without downloading audio.
    Downloads subtitles in json3 or vtt format and parses to plain text.
    """
    clean_url = normalize_url(url)
    diag = {"status": "attempted", "stage": "ytdlp_subtitles"}

    with tempfile.TemporaryDirectory() as tmpdir:
        out_tmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB", "hi"],
            "subtitlesformat": "json3/vtt/best",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": 20,
            "js_runtimes": {"node": {}},
        }

        proxy_url = get_proxy_url_string()
        if proxy_url:
            ydl_opts["proxy"] = proxy_url

        cookie_file = get_cookie_file_path()
        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        title = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                if info:
                    if "entries" in info and info["entries"]:
                        info = info["entries"][0]
                    title = info.get("title")

            # Look for written subtitle files in tmpdir
            sub_files = [
                os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                if f.endswith((".json3", ".vtt", ".ttml", ".srv3"))
            ]

            if sub_files:
                # Prefer English json3/vtt
                sub_files.sort(key=lambda x: (
                    0 if ".en." in x.lower() or x.lower().endswith(".en.json3") else
                    1 if x.endswith(".json3") else
                    2 if ".en." in x.lower() else
                    3
                ))
                target_file = sub_files[0]
                with open(target_file, "r", encoding="utf-8", errors="replace") as fh:
                    raw_content = fh.read()

                if target_file.endswith(".json3"):
                    transcript = _parse_json3(raw_content)
                else:
                    transcript = _parse_vtt(raw_content)

                if transcript and len(transcript.strip()) > 30:
                    logger.info(f"[yt-dlp Subtitles] Successfully parsed subtitles from {os.path.basename(target_file)}")
                    diag["status"] = "success"
                    diag["file"] = os.path.basename(target_file)
                    return transcript, title, diag

            diag["error"] = "No subtitle files found after yt-dlp run"
        except Exception as e:
            logger.warning(f"[yt-dlp Subtitles Warning] Extraction failed: {e}")
            diag["error"] = f"{type(e).__name__}: {e}"

    return None, title, diag

# ── STAGE 3: Fallback 2 - yt-dlp Audio Download ────────────────────────────────

CLIENT_CONFIGS = [
    None,            # Default yt-dlp client list
    ["tv"],          # Smart TV client (highly resilient to datacenter IP blocks)
    ["web_safari"],  # Safari client
    ["mweb"],        # Mobile web client
]

def download_youtube_audio(url: str, max_minutes: int = 90) -> tuple[str, str]:
    """
    Fallback 2: Download YouTube audio with yt-dlp using client retry loop,
    proxy support, duration check, and Node.js JS runtime.
    Returns (wav_path, video_title).
    """
    clean_url = normalize_url(url)
    proxy_url = get_proxy_url_string()
    cookie_file = get_cookie_file_path()

    last_error = None
    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    for client_list in CLIENT_CONFIGS:
        client_name = "default" if client_list is None else "+".join(client_list)
        logger.info(f"[yt-dlp Audio] Attempting audio download with player_client config: {client_name}...")

        ydl_opts = {
            "format": "ba/b",
            "outtmpl": output_template,
            "noplaylist": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
            "js_runtimes": {"node": {}},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
        }

        if client_list:
            ydl_opts["extractor_args"] = {
                "youtube": {
                    "player_client": client_list
                }
            }

        if proxy_url:
            ydl_opts["proxy"] = proxy_url

        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Pre-check video duration to prevent overloading server
                info = ydl.extract_info(clean_url, download=False)
                if info and "entries" in info and info["entries"]:
                    info = info["entries"][0]

                title = info.get("title", "YouTube Video")
                video_id = info.get("id") or str(uuid.uuid4())[:8]
                duration = info.get("duration")

                if duration and duration > (max_minutes * 60):
                    raise MediaIngestionError(
                        f"Video duration ({int(duration // 60)} minutes) exceeds the maximum allowed limit of {max_minutes} minutes.",
                        code="DURATION_EXCEEDED"
                    )

                # Now download
                ydl.process_info(info)

                wav_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.wav")
                if not os.path.exists(wav_path):
                    base_name = os.path.splitext(ydl.prepare_filename(info))[0]
                    alt_wav = f"{base_name}.wav"
                    if os.path.exists(alt_wav):
                        wav_path = alt_wav

                if os.path.exists(wav_path):
                    logger.info(f"[yt-dlp Audio] Successfully downloaded audio to {wav_path}")
                    return wav_path, title

        except MediaIngestionError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"[yt-dlp Audio Notice] Client config '{client_name}' failed: {e}")
            continue

    raise MediaIngestionError(
        "YouTube automated audio download failed across all player clients.",
        code="YTDLP_AUDIO_FAILED",
        technical_details=str(last_error)
    )

# ── Audio Processing & Chunking ───────────────────────────────────────────────

def convert_to_wav(input_path: str) -> tuple[str, str]:
    """Convert any audio/video file to 16kHz mono WAV format using pydub. Returns (wav_path, title)."""
    title = os.path.splitext(os.path.basename(input_path))[0]
    base_dir = os.path.dirname(input_path) or DOWNLOAD_DIR
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-.]', '_', title)
    output_path = os.path.join(base_dir, f"{clean_stem}_{uuid.uuid4().hex[:6]}_16k.wav")

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path, title

def chunk_audio(wav_path: str, chunk_minutes: int = 10, max_size_mb: int = 24) -> list[str]:
    """
    Split audio into manageable chunks compressed as 16kHz mono MP3 (64kbps).
    Ensures every chunk is strictly under max_size_mb (Groq's 25MB limit).
    """
    audio = AudioSegment.from_file(wav_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    chunk_ms = chunk_minutes * 60 * 1000
    base_stem = os.path.splitext(wav_path)[0]

    # If within chunk duration limit, export single mp3 chunk
    if len(audio) <= chunk_ms:
        chunk_path = f"{base_stem}_chunk_0.mp3"
        audio.export(chunk_path, format="mp3", bitrate="64k", parameters=["-ac", "1", "-ar", "16000"])
        return [chunk_path]

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{base_stem}_chunk_{i}.mp3"
        chunk.export(chunk_path, format="mp3", bitrate="64k", parameters=["-ac", "1", "-ar", "16000"])
        chunks.append(chunk_path)

    return chunks

# ── High-Level Ingestion Orchestrator ──────────────────────────────────────────

def process_media_source(
    source: str = None,
    language: str = "english",
    uploaded_file_path: str = None,
    pasted_transcript: str = None,
    max_video_minutes: int = 90
) -> dict:
    """
    Orchestrates ingestion across all fallback tiers:
    1. Pasted transcript (immediate)
    2. YouTube URL:
       - Tier 1: youtube_transcript_api direct
       - Tier 2: yt-dlp subtitle-only extraction
       - Tier 3: yt-dlp audio download + chunking
    3. Uploaded local file:
       - Audio conversion + chunking
    4. If automated YouTube ingestion fails completely, raises clean MediaIngestionError.
    """
    # Option A: Direct pasted transcript
    if pasted_transcript and pasted_transcript.strip():
        first_line = pasted_transcript.strip().splitlines()[0][:60]
        title = f"Pasted Transcript ({first_line}...)" if len(first_line) > 20 else "Pasted Video Transcript"
        return {
            "type": "transcript",
            "transcript": pasted_transcript.strip(),
            "title": title,
            "stage_used": "pasted_text"
        }

    # Option B: Uploaded file
    if uploaded_file_path and os.path.exists(uploaded_file_path):
        wav_path, title = convert_to_wav(uploaded_file_path)
        chunks = chunk_audio(wav_path)
        return {
            "type": "audio_chunks",
            "chunks": chunks,
            "title": title,
            "stage_used": "file_upload",
            "raw_file": wav_path
        }

    # Option C: Web / YouTube URL
    if source and is_url(source):
        clean_url = normalize_url(source)

        # Tier 1: youtube_transcript_api
        logger.info("[Ingestion] Tier 1: Attempting direct youtube_transcript_api extraction...")
        transcript, title, diag1 = extract_youtube_transcript_direct(clean_url, language)
        if transcript and transcript.strip():
            return {
                "type": "transcript",
                "transcript": transcript.strip(),
                "title": title or "YouTube Video",
                "stage_used": "youtube_transcript_api"
            }

        # Tier 2: yt-dlp subtitles
        logger.info("[Ingestion] Tier 2: Attempting yt-dlp subtitle-only extraction...")
        transcript, y_title, diag2 = extract_youtube_subtitles_ytdlp(clean_url)
        if transcript and transcript.strip():
            return {
                "type": "transcript",
                "transcript": transcript.strip(),
                "title": y_title or title or "YouTube Video",
                "stage_used": "ytdlp_subtitles"
            }

        # Tier 3: yt-dlp audio download
        logger.info("[Ingestion] Tier 3: Attempting yt-dlp audio download...")
        try:
            wav_path, a_title = download_youtube_audio(clean_url, max_minutes=max_video_minutes)
            chunks = chunk_audio(wav_path)
            return {
                "type": "audio_chunks",
                "chunks": chunks,
                "title": a_title or title or "YouTube Video",
                "stage_used": "ytdlp_audio",
                "raw_file": wav_path
            }
        except MediaIngestionError as e:
            if e.code == "DURATION_EXCEEDED":
                raise e
            logger.error(f"[Ingestion Error] Automated audio download failed: {e.technical_details}")

        # Fallback 3: User-facing clean guidance
        raise MediaIngestionError(
            "YouTube blocked automated access from cloud servers for this video. "
            "Please: (1) Upload the audio/video file directly using 'Upload File', or "
            "(2) Paste the transcript text into the 'Paste Transcript' tab.",
            code="YOUTUBE_INGESTION_BLOCKED"
        )

    raise ValueError("No valid input provided. Supply a YouTube URL, upload an audio/video file, or paste a transcript.")

# Backwards compatibility helper
def process_input(source: str) -> list[str]:
    """Legacy helper for downloading/chunking audio."""
    res = process_media_source(source=source)
    if res["type"] == "audio_chunks":
        return res["chunks"]
    return []