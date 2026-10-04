"""
AI Video Assistant — Media & Audio Ingestion Engine
===================================================
Handles multi-tier media acquisition, transcription ingestion, and audio processing:
  1. Pasted transcript text (instant zero-network path)
  2. YouTube multi-tier pipeline:
     - Tier 1: youtube_transcript_api direct
     - Tier 2: yt-dlp subtitle-only extraction (json3/vtt)
     - Tier 3: yt-dlp audio download (player_client retry loop, TV/Safari/mweb)
     - Tier 3.5: Supadata YouTube transcript API fallback (optional free tier)
  3. Direct media files (.mp4, .mp3, .wav, etc.) & Cloud Shares (Google Drive, Dropbox, OneDrive)
     - Streaming requests with MAX_DOWNLOAD_MB guard and SSRF redirection defense
     - Duration check (MAX_VIDEO_MINUTES)
     - 16kHz mono WAV conversion via ffmpeg/pydub
  4. Non-YouTube video sites (Vimeo, Loom, Zoom, Teams, etc.)
     - Generic yt-dlp extractor (default settings, no forced android client)
     - Audio-only format with UUID output filenames and auto-cleanup
  5. Local audio/video file upload (.mp4, .mp3, .wav, .mkv, .webm, etc.)
"""

import os
import re
import json
import uuid
import tempfile
import urllib.parse
import urllib.request
import logging
import requests
from pydub import AudioSegment
import yt_dlp

from utils.url_router import (
    classify_url,
    validate_safe_url,
    download_direct_media_stream,
    MediaDownloadError,
    SSRFBlockedError,
)

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
    """Check if the source string is a web / media URL."""
    if not source:
        return False
    s = source.strip().lower()
    return (
        s.startswith("http://")
        or s.startswith("https://")
        or s.startswith("www.")
        or "youtube.com" in s
        or "youtu.be" in s
        or "drive.google.com" in s
        or "dropbox.com" in s
        or "vimeo.com" in s
        or "loom.com" in s
    )

def normalize_url(url: str) -> str:
    """Ensure URL has a valid scheme and is stripped."""
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u

def get_media_duration_seconds(file_path: str) -> float | None:
    """Safely obtain audio/video duration in seconds using pydub."""
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0
    except Exception as e:
        logger.debug(f"[Duration Check] Could not measure audio duration for {file_path}: {e}")
        return None

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

            sub_files = [
                os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                if f.endswith((".json3", ".vtt", ".ttml", ".srv3"))
            ]

            if sub_files:
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

# ── STAGE 3: Fallback 2 - yt-dlp YouTube Audio Download ───────────────────────

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
                info = ydl.extract_info(clean_url, download=False)
                if info and "entries" in info and info["entries"]:
                    info = info["entries"][0]

                title = info.get("title", "YouTube Video")
                video_id = info.get("id") or str(uuid.uuid4())[:8]
                duration = info.get("duration")

                if duration and duration > (max_minutes * 60):
                    raise MediaIngestionError(
                        f"Video duration ({int(duration // 60)} minutes) exceeds the maximum allowed limit of {max_minutes} minutes. Please trim or upload a shorter file.",
                        code="DURATION_EXCEEDED"
                    )

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

# ── STAGE 3.5: Optional Free YouTube Fallback (Supadata Transcript API) ─────────

def extract_youtube_transcript_supadata(url: str) -> tuple[str | None, str | None, dict]:
    """
    Optional free YouTube fallback using the Supadata transcript API (free tier).
    Runs AFTER existing YouTube methods fail and BEFORE showing user error.
    Skipped silently if SUPADATA_API_KEY is not set.
    """
    api_key = (os.getenv("SUPADATA_API_KEY") or "").strip()
    if not api_key:
        return None, None, {"status": "skipped", "reason": "SUPADATA_API_KEY not configured"}

    clean_url = normalize_url(url)
    video_id = extract_youtube_id(clean_url)
    target_param = f"https://www.youtube.com/watch?v={video_id}" if video_id else clean_url
    title = fetch_youtube_oembed_title(video_id) if video_id else None
    diag = {"status": "attempted", "video_id": video_id, "stage": "supadata_api"}

    logger.info("[Supadata API] Attempting free transcript extraction fallback...")
    try:
        endpoint = f"https://api.supadata.ai/v1/youtube/transcript?url={urllib.parse.quote(target_param, safe='')}"
        headers = {
            "x-api-key": api_key,
            "User-Agent": "AI-Video-Assistant/2.0"
        }
        resp = requests.get(endpoint, headers=headers, timeout=25)

        if resp.status_code == 200:
            data = resp.json()
            transcript_text = ""
            content = data.get("content")
            if isinstance(content, list):
                lines = [seg.get("text", "").strip() for seg in content if isinstance(seg, dict) and seg.get("text")]
                transcript_text = " ".join(lines).strip()
            elif isinstance(content, str):
                transcript_text = content.strip()

            if transcript_text and len(transcript_text) > 20:
                logger.info(f"[Supadata API] Successfully retrieved transcript ({len(transcript_text.split())} words)")
                diag["status"] = "success"
                return transcript_text, title or "YouTube Video", diag
            else:
                diag["status"] = "empty_content"
        else:
            logger.info(f"[Supadata API] Status {resp.status_code}: {resp.text[:120]}")
            diag["status"] = f"http_{resp.status_code}"
    except Exception as e:
        logger.warning(f"[Supadata API] Request error: {e}")
        diag["error"] = str(e)

    return None, title, diag

# ── Generic Non-YouTube Video Downloader (yt-dlp) ─────────────────────────────

def download_generic_video_audio(url: str, max_minutes: int = 90) -> tuple[str, str]:
    """
    Download non-YouTube video/meeting audio with yt-dlp using default settings.
    - Does NOT force android client (or any youtube extractor_args)
    - Audio-only format (FFmpegExtractAudio -> wav)
    - Output filename based on UUID
    - Validates safe URL (SSRF protection)
    - Checks duration before downloading
    Returns (wav_path, video_title).
    """
    safe_url = validate_safe_url(url)
    clean_id = f"generic_{uuid.uuid4().hex[:10]}"
    output_template = os.path.join(DOWNLOAD_DIR, f"{clean_id}.%(ext)s")

    ydl_opts = {
        "format": "ba/b",
        "outtmpl": output_template,
        "noplaylist": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Pre-check video duration to prevent overloading server
            info = ydl.extract_info(safe_url, download=False)
            if info and "entries" in info and info["entries"]:
                info = info["entries"][0]

            title = info.get("title") or "Online Video"
            duration = info.get("duration")

            if duration and duration > (max_minutes * 60):
                raise MediaIngestionError(
                    f"Video duration ({int(duration // 60)} minutes) exceeds the maximum allowed limit of {max_minutes} minutes. Please trim or upload a shorter file.",
                    code="DURATION_EXCEEDED"
                )

            # 2. Download audio
            ydl.process_info(info)

            wav_path = os.path.join(DOWNLOAD_DIR, f"{clean_id}.wav")
            if not os.path.exists(wav_path):
                # Search for any generated wav file with matching clean_id prefix
                candidates = [
                    os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)
                    if f.startswith(clean_id) and f.endswith(".wav")
                ]
                if candidates:
                    wav_path = candidates[0]

            if os.path.exists(wav_path):
                logger.info(f"[Generic yt-dlp] Successfully downloaded audio to {wav_path}")
                return wav_path, title

            raise MediaIngestionError(
                "Unable to process audio from this link. Please download the recording and use Upload File or Paste Transcript.",
                code="EXTRACTION_FAILED"
            )

    except MediaIngestionError:
        raise
    except yt_dlp.utils.DownloadError as e:
        err_str = str(e).lower()
        domain = (urllib.parse.urlparse(safe_url).hostname or "").lower()
        is_meeting = any(m in domain for m in ("zoom", "teams", "meet", "webex"))

        if any(w in err_str for w in ("login", "sign in", "private", "permission", "unauthorized", "401", "403", "forbidden")):
            if is_meeting:
                raise MediaIngestionError(
                    "This meeting recording requires a sign-in or is private (Zoom, Teams, and Meet recordings usually need a login). Please download the recording and use Upload File.",
                    code="LOGIN_REQUIRED",
                    technical_details=str(e)
                )
            else:
                raise MediaIngestionError(
                    "This link is private. Please download the recording and use Upload File.",
                    code="LINK_PRIVATE",
                    technical_details=str(e)
                )
        elif "unsupported url" in err_str:
            raise MediaIngestionError(
                "This video website is not supported for direct extraction. Please download the recording and use Upload File or Paste Transcript.",
                code="UNSUPPORTED_SITE",
                technical_details=str(e)
            )
        else:
            logger.error(f"[Generic yt-dlp Error] {e}")
            raise MediaIngestionError(
                "Unable to extract video audio from this URL. Please download the recording and use Upload File or Paste Transcript.",
                code="EXTRACTION_FAILED",
                technical_details=str(e)
            )
    except Exception as e:
        logger.error(f"[Generic yt-dlp Unexpected Error] {e}", exc_info=True)
        raise MediaIngestionError(
            "An error occurred while processing this video link. Please use Upload File or Paste Transcript.",
            code="EXTRACTION_FAILED",
            technical_details=str(e)
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
    Orchestrates ingestion across all sources:
    1. Pasted transcript (immediate)
    2. Uploaded local file (conversion + chunking)
    3. Any URL (routed via classify_url):
       a) YouTube:
          - Tier 1: youtube_transcript_api direct
          - Tier 2: yt-dlp subtitle-only extraction
          - Tier 3: yt-dlp audio download + chunking
          - Tier 3.5: Supadata API fallback (if configured)
       b) Direct media & Cloud Share (Google Drive, Dropbox, OneDrive):
          - Streaming requests download with size guard & SSRF redirect validation
          - Duration limit check
          - 16kHz mono WAV conversion & chunking
       c) Generic video sites (Vimeo, Loom, Zoom, etc.):
          - yt-dlp default extractor (audio-only, UUID filenames)
          - Chunking and Groq transcription
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
        duration_sec = get_media_duration_seconds(uploaded_file_path)
        if duration_sec and duration_sec > (max_video_minutes * 60):
            raise MediaIngestionError(
                f"Uploaded video duration ({int(duration_sec // 60)} minutes) exceeds the maximum allowed limit of {max_video_minutes} minutes. Please trim or upload a shorter file.",
                code="DURATION_EXCEEDED"
            )

        wav_path, title = convert_to_wav(uploaded_file_path)
        chunks = chunk_audio(wav_path)
        return {
            "type": "audio_chunks",
            "chunks": chunks,
            "title": title,
            "stage_used": "file_upload",
            "raw_file": wav_path
        }

    # Option C: Web URL (YouTube, Cloud Share, Direct Media, or Generic Video)
    if source and is_url(source):
        try:
            classification = classify_url(source)
        except SSRFBlockedError as e:
            logger.warning(f"[Security SSRF Blocked] URL '{source}': {e}")
            raise MediaIngestionError(
                "Access to local or private network addresses is prohibited.",
                code="SSRF_BLOCKED",
                technical_details=str(e)
            )

        link_type = classification["type"]
        original_url = classification["original_url"]
        target_url = classification["target_url"]
        platform_label = classification.get("label", "Video Recording")

        # ── Branch 1: YouTube ────────────────────────────────────────────────
        if link_type == "youtube":
            clean_url = normalize_url(original_url)

            # Tier 1: youtube_transcript_api
            logger.info("[Ingestion] YouTube Tier 1: Attempting direct youtube_transcript_api extraction...")
            transcript, title, diag1 = extract_youtube_transcript_direct(clean_url, language)
            if transcript and transcript.strip():
                return {
                    "type": "transcript",
                    "transcript": transcript.strip(),
                    "title": title or "YouTube Video",
                    "stage_used": "youtube_transcript_api"
                }

            # Tier 2: yt-dlp subtitles
            logger.info("[Ingestion] YouTube Tier 2: Attempting yt-dlp subtitle-only extraction...")
            transcript, y_title, diag2 = extract_youtube_subtitles_ytdlp(clean_url)
            if transcript and transcript.strip():
                return {
                    "type": "transcript",
                    "transcript": transcript.strip(),
                    "title": y_title or title or "YouTube Video",
                    "stage_used": "ytdlp_subtitles"
                }

            # Tier 3: yt-dlp audio download
            logger.info("[Ingestion] YouTube Tier 3: Attempting yt-dlp audio download...")
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

            # Tier 3.5: Optional Supadata transcript API fallback
            if os.getenv("SUPADATA_API_KEY"):
                logger.info("[Ingestion] YouTube Tier 3.5: Attempting Supadata transcript API fallback...")
                supa_transcript, supa_title, diag_supa = extract_youtube_transcript_supadata(clean_url)
                if supa_transcript and supa_transcript.strip():
                    return {
                        "type": "transcript",
                        "transcript": supa_transcript.strip(),
                        "title": supa_title or title or "YouTube Video",
                        "stage_used": "supadata_api"
                    }

            # YouTube fallback guidance
            raise MediaIngestionError(
                "YouTube blocked automated access from cloud servers for this video. "
                "Please: (1) Upload the audio/video file directly using 'Upload File', or "
                "(2) Paste the transcript text into the 'Paste Transcript' tab.",
                code="YOUTUBE_INGESTION_BLOCKED"
            )

        # ── Branch 2: Direct Media & Cloud Share ─────────────────────────────
        elif link_type in ("direct_media", "cloud_share"):
            max_mb = int(os.getenv("MAX_DOWNLOAD_MB", "200"))
            logger.info(f"[Ingestion] Streaming direct media from {target_url} (limit: {max_mb} MB)...")

            try:
                raw_download_path, raw_title = download_direct_media_stream(
                    target_url,
                    output_directory=DOWNLOAD_DIR,
                    max_mb=max_mb,
                    timeout_seconds=45
                )
            except MediaDownloadError as mde:
                raise MediaIngestionError(str(mde), code=mde.code, technical_details=mde.technical_details)

            # Duration check
            duration_sec = get_media_duration_seconds(raw_download_path)
            if duration_sec and duration_sec > (max_video_minutes * 60):
                if os.path.exists(raw_download_path):
                    os.remove(raw_download_path)
                raise MediaIngestionError(
                    f"Video duration ({int(duration_sec // 60)} minutes) exceeds the maximum allowed limit of {max_video_minutes} minutes. Please trim or upload a shorter file.",
                    code="DURATION_EXCEEDED"
                )

            # Convert to 16kHz mono WAV format and chunk
            wav_path, clean_title = convert_to_wav(raw_download_path)
            if raw_download_path != wav_path and os.path.exists(raw_download_path):
                try:
                    os.remove(raw_download_path)
                except Exception:
                    pass

            chunks = chunk_audio(wav_path)
            return {
                "type": "audio_chunks",
                "chunks": chunks,
                "title": raw_title or clean_title or platform_label,
                "stage_used": link_type,
                "raw_file": wav_path
            }

        # ── Branch 3: Generic Video Site (Vimeo, Loom, Zoom, etc.) ───────────
        elif link_type == "generic_video":
            logger.info(f"[Ingestion] Attempting generic extractor for {platform_label} ({original_url})...")
            wav_path, v_title = download_generic_video_audio(original_url, max_minutes=max_video_minutes)
            chunks = chunk_audio(wav_path)
            return {
                "type": "audio_chunks",
                "chunks": chunks,
                "title": v_title or platform_label,
                "stage_used": "generic_ytdlp",
                "raw_file": wav_path
            }

    raise ValueError("No valid input provided. Supply a video or meeting URL, upload an audio/video file, or paste a transcript.")

# Backwards compatibility helper
def process_input(source: str) -> list[str]:
    """Legacy helper for downloading/chunking audio."""
    res = process_media_source(source=source)
    if res.get("type") == "audio_chunks":
        return res.get("chunks", [])
    return []