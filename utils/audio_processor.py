import os
import re
import uuid
import json
import tempfile
import urllib.request
import yt_dlp
from pydub import AudioSegment

# Ensure static_ffmpeg binaries (ffmpeg, ffprobe) are registered in PATH
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    pass

DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

_last_media_title = None

def get_last_media_title() -> str | None:
    """Return the title of the most recently processed audio/video."""
    global _last_media_title
    return _last_media_title


def set_last_media_title(title: str | None) -> None:
    """Set the title of the currently processed media."""
    global _last_media_title
    _last_media_title = title


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
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("title")
    except Exception as e:
        print(f"[Notice] Could not fetch oEmbed title: {e}")
        return None


def extract_youtube_transcript_direct(url_or_id: str, language: str = "english") -> tuple[str | None, str | None]:
    """
    Directly fetch transcripts and metadata using YouTube's official captions endpoint.
    This completely bypasses audio downloading and YouTube bot detection on cloud servers (Render, Railway, etc.).
    Returns (transcript_text, title) or (None, title_or_none) on failure.
    """
    video_id = extract_youtube_id(url_or_id)
    if not video_id:
        return None, None

    title = fetch_youtube_oembed_title(video_id)
    if title:
        set_last_media_title(title)

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()

        snippets = None
        # Preferred language codes
        lang_pref = ["en", "hi"] if "hin" in (language or "").lower() else ["en"]

        # Try fetching using transcript list if available
        try:
            transcript_list = api.list(video_id)
            for lang in lang_pref:
                try:
                    snippets = transcript_list.find_transcript([lang]).fetch()
                    break
                except Exception:
                    pass
            if not snippets:
                # Fallback to any transcript available
                for t in transcript_list:
                    snippets = t.fetch()
                    break
        except Exception:
            # Fallback to direct fetch
            snippets = api.fetch(video_id)

        if snippets:
            lines = []
            for s in snippets:
                txt = getattr(s, "text", "") if hasattr(s, "text") else (s.get("text", "") if isinstance(s, dict) else str(s))
                txt = txt.strip()
                if txt:
                    lines.append(txt)
            transcript = " ".join(lines).strip()
            if transcript:
                print(f"[YouTubeTranscriptApi] Successfully extracted {len(lines)} caption segments for video {video_id}.")
                return transcript, title
    except Exception as e:
        print(f"[YouTubeTranscriptApi] Caption extraction notice: {e}")

    return None, title


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


def download_youtube_audio(url: str) -> str:
    """
    Download audio from YouTube using yt-dlp and convert to WAV.
    Uses video ID for filename to prevent Windows filesystem issues,
    MAX_PATH truncation, or encoding errors with special/unicode characters.
    """
    global _last_media_title
    clean_url = normalize_url(url)

    output_template = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb", "tvhtml5"]
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 14; en_US) gzip",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    # Support cookies via YOUTUBE_COOKIES env var, file path env var, or local cookies.txt
    cookies_env = os.environ.get("YOUTUBE_COOKIES", "").strip()
    if cookies_env:
        temp_cookie_path = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
        try:
            with open(temp_cookie_path, "w", encoding="utf-8") as f:
                f.write(cookies_env)
            ydl_opts["cookiefile"] = temp_cookie_path
        except Exception as e:
            print(f"[Warning] Failed to write temporary cookie file: {e}")
    else:
        cookie_candidate = os.environ.get("YOUTUBE_COOKIE_FILE") or "cookies.txt"
        if os.path.exists(cookie_candidate):
            ydl_opts["cookiefile"] = cookie_candidate

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=True)
        if info and "entries" in info and info["entries"]:
            info = info["entries"][0]

        video_id = info.get("id") or str(uuid.uuid4())[:8]
        _last_media_title = info.get("title", "")

        wav_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.wav")

        # Fallback check if postprocessor output exists
        if not os.path.exists(wav_path):
            base_name = os.path.splitext(ydl.prepare_filename(info))[0]
            alt_wav = f"{base_name}.wav"
            if os.path.exists(alt_wav):
                wav_path = alt_wav

    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Failed to find downloaded audio file for video ID: {video_id}")

    return wav_path


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to 16kHz mono WAV format using pydub."""
    global _last_media_title
    _last_media_title = os.path.splitext(os.path.basename(input_path))[0]

    base_dir = os.path.dirname(input_path) or DOWNLOAD_DIR
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-.]', '_', os.path.splitext(os.path.basename(input_path))[0])
    output_path = os.path.join(base_dir, f"{clean_stem}_converted.wav")

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16kHz mono for Whisper
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    """Split audio into manageable chunks for speech recognition."""
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    base_stem = os.path.splitext(wav_path)[0]

    # If audio is within single chunk limit, export single chunk
    if len(audio) <= chunk_ms:
        chunk_path = f"{base_stem}_chunk_0.wav"
        if not os.path.exists(chunk_path):
            audio.export(chunk_path, format="wav")
        return [chunk_path]

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{base_stem}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:
    """
    Accepts either a YouTube URL or a local media file path.
    Converts and splits audio into chunks ready for transcription.
    """
    if not source:
        raise ValueError("No input source provided.")

    source_clean = source.strip()

    if is_url(source_clean):
        print(f"Detected YouTube URL. Downloading audio: {source_clean}")
        wav_path = download_youtube_audio(source_clean)
    else:
        if not os.path.exists(source_clean):
            raise FileNotFoundError(f"Input file not found: {source_clean}")
        print(f"Detected local file. Converting to WAV: {source_clean}")
        wav_path = convert_to_wav(source_clean)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks