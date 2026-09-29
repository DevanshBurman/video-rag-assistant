import os
import re
import uuid
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

    # Support optional cookie file if placed in root or passed via env
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