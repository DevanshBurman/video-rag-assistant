"""
AI Video Assistant — URL Router & Safe Ingestion Engine
======================================================
Classifies incoming video/meeting URLs into:
  1. YouTube (standard pipeline)
  2. Direct media files (.mp4, .mp3, .wav, audio/*, video/*)
  3. Cloud-share links (Google Drive, Dropbox, OneDrive)
  4. Generic video sites (Vimeo, Loom, Zoom, Facebook, etc. via yt-dlp)

Includes strict SSRF protection blocking private, loopback, link-local,
and reserved IP ranges on both initial domain resolution and subsequent redirects.
"""

import os
import re
import socket
import ipaddress
import urllib.parse
import uuid
import logging
import requests

logger = logging.getLogger("url_router")
logger.setLevel(logging.INFO)

DIRECT_MEDIA_EXTENSIONS = {
    ".mp4", ".mp3", ".wav", ".m4a", ".webm",
    ".mov", ".mkv", ".ogg", ".flac", ".aac"
}

class SSRFBlockedError(Exception):
    """Raised when a URL attempts to access private/local/reserved networks."""
    pass

class MediaDownloadError(Exception):
    """Raised when streaming or downloading a media URL fails."""
    def __init__(self, message: str, code: str = "DOWNLOAD_FAILED", technical_details: str = ""):
        super().__init__(message)
        self.code = code
        self.technical_details = technical_details

# ── 1. SSRF Protection ────────────────────────────────────────────────────────

def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Check if an IP address belongs to localhost, private, link-local,
    multicast, or reserved address spaces.
    Blocks:
      - 127.0.0.0/8 (loopback)
      - 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7 (private)
      - 169.254.0.0/16, fe80::/10 (link-local)
      - ::1 (IPv6 loopback)
      - 0.0.0.0, :: (unspecified)
      - 224.0.0.0/4, ff00::/8 (multicast)
      - 240.0.0.0/4 (reserved)
    """
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_reserved
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    )

def validate_safe_url(url: str) -> str:
    """
    Validate that the given URL uses http/https and does NOT resolve
    to localhost or internal private/reserved IP ranges (SSRF defense).
    Returns normalized clean URL or raises SSRFBlockedError.
    """
    if not url or not isinstance(url, str):
        raise SSRFBlockedError("Invalid URL supplied.")

    clean_url = url.strip()
    parsed = urllib.parse.urlparse(clean_url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFBlockedError(f"Unsupported protocol scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedError("URL must contain a valid hostname.")

    hostname_clean = hostname.lower().strip("[]")
    if hostname_clean in ("localhost", "127.0.0.1", "::1"):
        raise SSRFBlockedError(f"Access to local host '{hostname_clean}' is prohibited.")

    # Resolve hostname via DNS and check all returned IP records
    try:
        resolved_records = socket.getaddrinfo(hostname_clean, None)
    except socket.gaierror as e:
        raise SSRFBlockedError(f"Cannot resolve domain '{hostname_clean}': {e}") from e

    resolved_ips = set()
    for record in resolved_records:
        sockaddr = record[4]
        ip_str = sockaddr[0]
        resolved_ips.add(ip_str)

    if not resolved_ips:
        raise SSRFBlockedError(f"No IP records found for hostname '{hostname_clean}'.")

    for ip_str in resolved_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                raise SSRFBlockedError(
                    f"Blocked SSRF attempt: domain '{hostname_clean}' resolves to private/restricted IP ({ip_str})."
                )
        except ValueError:
            raise SSRFBlockedError(f"Invalid resolved IP format '{ip_str}'.")

    return clean_url

def safe_http_request(
    method: str,
    url: str,
    max_redirects: int = 5,
    timeout: int = 30,
    stream: bool = False,
    session: requests.Session | None = None
) -> requests.Response:
    """
    Execute HTTP request while validating EVERY redirect hop against SSRF before connecting.
    Prevents open-redirect attacks pointing to internal/metadata endpoints.
    """
    sess = session or requests.Session()
    sess.headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    current_url = url
    for _ in range(max_redirects + 1):
        validate_safe_url(current_url)
        resp = sess.request(method, current_url, timeout=timeout, stream=stream, allow_redirects=False)
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            if not location:
                return resp
            current_url = urllib.parse.urljoin(current_url, location)
            validate_safe_url(current_url)
        else:
            return resp

    raise MediaDownloadError("Too many redirects while accessing media URL.", code="TOO_MANY_REDIRECTS")

# ── 2. Cloud-Share URL Converters ─────────────────────────────────────────────

def extract_google_drive_file_id(url: str) -> str | None:
    """Extract Google Drive file ID from view or share URLs."""
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def convert_google_drive_url(url: str) -> str:
    """Convert Google Drive share link to direct download URL."""
    file_id = extract_google_drive_file_id(url)
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url

def convert_dropbox_url(url: str) -> str:
    """Convert Dropbox share link to direct download URL (dl=1)."""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params["dl"] = ["1"]
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))

def convert_onedrive_url(url: str) -> str:
    """Ensure OneDrive link has download parameter."""
    if "download=1" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}download=1"
    return url

# ── 3. URL Classification & Routing ───────────────────────────────────────────

def classify_url(url: str) -> dict:
    """
    Classifies a pasted URL into one of:
      - 'youtube' (existing pipeline, unchanged)
      - 'direct_media' (.mp4, .mp3, .wav, or media Content-Type)
      - 'cloud_share' (Google Drive, Dropbox, OneDrive)
      - 'generic_video' (Vimeo, Loom, Zoom, Teams, Facebook, Twitter, etc.)
    """
    safe_url = validate_safe_url(url)
    parsed = urllib.parse.urlparse(safe_url)
    domain = (parsed.hostname or "").lower()
    path = parsed.path.lower()

    # 1. YouTube
    if any(yt in domain for yt in ("youtube.com", "youtu.be")):
        return {
            "type": "youtube",
            "platform": "youtube",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": "YouTube Video"
        }

    # 2. Cloud Share: Google Drive
    if "drive.google.com" in domain or "docs.google.com" in domain:
        direct_url = convert_google_drive_url(safe_url)
        return {
            "type": "cloud_share",
            "platform": "google_drive",
            "original_url": safe_url,
            "target_url": direct_url,
            "label": "Google Drive Recording"
        }

    # 3. Cloud Share: Dropbox
    if "dropbox.com" in domain:
        direct_url = convert_dropbox_url(safe_url)
        return {
            "type": "cloud_share",
            "platform": "dropbox",
            "original_url": safe_url,
            "target_url": direct_url,
            "label": "Dropbox Media"
        }

    # 4. Cloud Share: OneDrive
    if "1drv.ms" in domain or "onedrive.live.com" in domain:
        direct_url = convert_onedrive_url(safe_url)
        return {
            "type": "cloud_share",
            "platform": "onedrive",
            "original_url": safe_url,
            "target_url": direct_url,
            "label": "OneDrive Recording"
        }

    # 5. Direct Media by file extension in URL path
    clean_path = path.split("?")[0]
    ext = os.path.splitext(clean_path)[1]
    if ext in DIRECT_MEDIA_EXTENSIONS:
        return {
            "type": "direct_media",
            "platform": "direct",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": f"Direct {ext.upper()[1:]} Media Stream"
        }

    # 6. Meeting platforms (Zoom, Teams, Google Meet)
    if "zoom.us" in domain:
        return {
            "type": "generic_video",
            "platform": "zoom",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": "Zoom Meeting Recording"
        }
    if "teams.microsoft.com" in domain or "teams.live.com" in domain:
        return {
            "type": "generic_video",
            "platform": "teams",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": "Microsoft Teams Recording"
        }
    if "loom.com" in domain:
        return {
            "type": "generic_video",
            "platform": "loom",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": "Loom Video"
        }
    if "vimeo.com" in domain:
        return {
            "type": "generic_video",
            "platform": "vimeo",
            "original_url": safe_url,
            "target_url": safe_url,
            "label": "Vimeo Video"
        }

    # 7. Safe HEAD probe to detect media Content-Type without downloading body
    try:
        head_resp = safe_http_request("HEAD", safe_url, max_redirects=3, timeout=5)
        c_type = (head_resp.headers.get("Content-Type") or "").lower()
        if c_type.startswith("video/") or c_type.startswith("audio/"):
            return {
                "type": "direct_media",
                "platform": "direct",
                "original_url": safe_url,
                "target_url": safe_url,
                "label": f"Direct Media Stream ({c_type.split(';')[0]})"
            }
    except Exception as e:
        logger.debug(f"[Router Head Probe] Could not probe URL headers: {e}")

    # 8. Fallback to generic yt-dlp extractor
    return {
        "type": "generic_video",
        "platform": "generic",
        "original_url": safe_url,
        "target_url": safe_url,
        "label": f"Web Video ({domain or 'Online'})"
    }

# ── 4. Streaming Direct Downloader with Limits & SSRF Defense ──────────────────

def download_direct_media_stream(
    url: str,
    output_directory: str = "downloads",
    max_mb: int = 200,
    timeout_seconds: int = 45
) -> tuple[str, str]:
    """
    Download direct media or cloud share link with chunked streaming.
    Enforces SSRF validation on every redirect hop, max size limits,
    and checks for private/login pages.
    Returns (downloaded_file_path, file_title).
    """
    safe_url = validate_safe_url(url)
    os.makedirs(output_directory, exist_ok=True)
    max_bytes = max_mb * 1024 * 1024

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    # Fetch with safe redirect traversal
    resp = safe_http_request(
        "GET",
        safe_url,
        max_redirects=5,
        timeout=timeout_seconds,
        stream=True,
        session=session
    )

    # Check status codes
    if resp.status_code in (401, 403):
        domain = (urllib.parse.urlparse(safe_url).hostname or "").lower()
        if any(m in domain for m in ("zoom", "teams", "meet")):
            raise MediaDownloadError(
                "This meeting recording requires a sign-in or is private (Zoom, Teams, and Meet recordings usually need a login). Please download the recording and use Upload File.",
                code="LOGIN_REQUIRED"
            )
        raise MediaDownloadError("This link is private. Please download the recording and use Upload File.", code="LINK_PRIVATE")
    if resp.status_code != 200:
        raise MediaDownloadError(f"HTTP {resp.status_code} while fetching recording from {url}.", code="HTTP_ERROR")

    # Handle Google Drive large-file virus scan confirmation page
    content_type = (resp.headers.get("Content-Type") or "").lower()
    if ("drive.google.com" in safe_url or "google.com" in safe_url) and "text/html" in content_type:
        html_sample = resp.iter_content(chunk_size=16384)
        sample_text = b"".join([next(html_sample, b"") for _ in range(4)]).decode("utf-8", errors="replace")

        # Extract confirm token if present in HTML or cookies
        confirm_token = None
        m_confirm = re.search(r'confirm=([0-9A-Za-z_-]+)', sample_text) or re.search(r'name="confirm"\s+value="([^"]+)"', sample_text)
        if m_confirm:
            confirm_token = m_confirm.group(1)

        for cookie in session.cookies:
            if "download_warning" in cookie.name:
                confirm_token = cookie.value

        file_id = extract_google_drive_file_id(safe_url)
        if file_id and confirm_token:
            confirm_url = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
            resp = safe_http_request(
                "GET",
                confirm_url,
                max_redirects=5,
                timeout=timeout_seconds,
                stream=True,
                session=session
            )
            content_type = (resp.headers.get("Content-Type") or "").lower()

    # Detect HTML login / permission pages masquerading as media
    if "text/html" in content_type:
        chunk = next(resp.iter_content(chunk_size=4096), b"")
        text_preview = chunk.decode("utf-8", errors="replace").lower()
        domain = (urllib.parse.urlparse(safe_url).hostname or "").lower()
        is_meeting = any(m in domain for m in ("zoom", "teams", "meet"))

        if any(w in text_preview for w in ("sign in", "login", "unauthorized", "access denied", "private video")):
            if is_meeting:
                raise MediaDownloadError(
                    "This meeting recording requires a sign-in or is private (Zoom, Teams, and Meet recordings usually need a login). Please download the recording and use Upload File.",
                    code="LOGIN_REQUIRED"
                )
            raise MediaDownloadError("This link is private. Please download the recording and use Upload File.", code="LINK_PRIVATE")
        raise MediaDownloadError("This link returned a webpage instead of an audio/video file. Please use Upload File or Paste Transcript.", code="NOT_A_MEDIA_STREAM")

    # Content-Length check upfront
    content_len = resp.headers.get("Content-Length")
    if content_len and content_len.isdigit():
        size_bytes = int(content_len)
        if size_bytes > max_bytes:
            raise MediaDownloadError(
                f"File size ({int(size_bytes // (1024 * 1024))} MB) exceeds limit of {max_mb} MB. Please trim or upload a shorter file.",
                code="FILE_TOO_LARGE"
            )

    # Determine destination filename
    cd_header = resp.headers.get("Content-Disposition") or ""
    filename = None
    if "filename=" in cd_header:
        m_fn = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd_header)
        if m_fn:
            filename = m_fn.group(1).strip()

    if not filename:
        parsed_p = urllib.parse.urlparse(safe_url).path
        base = os.path.basename(parsed_p)
        if base and any(base.lower().endswith(ext) for ext in DIRECT_MEDIA_EXTENSIONS):
            filename = base
        else:
            filename = f"media_{uuid.uuid4().hex[:8]}.mp4"

    clean_filename = re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)
    dest_path = os.path.join(output_directory, clean_filename)
    title = os.path.splitext(clean_filename)[0].replace("_", " ").strip()

    # Stream write in 64KB chunks and enforce maximum download size
    downloaded_bytes = 0
    try:
        with open(dest_path, "wb") as f_out:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > max_bytes:
                        f_out.close()
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        raise MediaDownloadError(
                            f"Downloaded content exceeded maximum size limit of {max_mb} MB. Please trim or upload a shorter file.",
                            code="FILE_TOO_LARGE"
                        )
                    f_out.write(chunk)
    except Exception as e:
        if os.path.exists(dest_path) and downloaded_bytes > max_bytes:
            os.remove(dest_path)
        if isinstance(e, MediaDownloadError):
            raise e
        raise MediaDownloadError(f"Streaming download interrupted: {e}", code="DOWNLOAD_INTERRUPTED") from e

    if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
        raise MediaDownloadError("Downloaded media file was empty.", code="EMPTY_FILE")

    logger.info(f"[Downloader] Successfully downloaded stream to {dest_path} ({downloaded_bytes // 1024} KB)")
    return dest_path, title
