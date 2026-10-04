import os
import time

_whisper_model = None

def get_whisper_model(model_size: str = None):
    """Load and cache local Whisper model in memory lazily only when requested."""
    global _whisper_model
    if model_size is None:
        model_size = os.getenv("WHISPER_MODEL", "base").strip() or "base"
    if _whisper_model is None:
        # Lazy import of torch and whisper to prevent loading heavy libs on Render
        try:
            import whisper
            print(f"[Transcriber] Loading local Whisper model ('{model_size}')...")
            _whisper_model = whisper.load_model(model_size)
        except ImportError as e:
            raise ImportError(
                "Local Whisper backend requested, but 'openai-whisper' or 'torch' is not installed. "
                "Install them or switch to TRANSCRIBER_BACKEND=groq."
            ) from e
    return _whisper_model

def translate_text_safely(text: str, source: str = "auto", target: str = "en") -> str:
    """
    Translate text using deep_translator with automatic chunking into <=4500 character pieces.
    Google Translate endpoint fails if a single request exceeds ~5000 characters.
    """
    if not text or not text.strip():
        return text

    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source, target=target)

        if len(text) <= 4500:
            return translator.translate(text)

        # Chunk by lines / sentences to avoid cutting in the middle of words
        pieces = []
        current_chunk = []
        current_len = 0

        for line in text.splitlines(keepends=True):
            if current_len + len(line) > 4200:
                if current_chunk:
                    pieces.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                # Handle single line exceeding limit
                if len(line) > 4200:
                    words = line.split(" ")
                    w_sub = []
                    w_len = 0
                    for w in words:
                        if w_len + len(w) + 1 > 4200:
                            pieces.append(" ".join(w_sub))
                            w_sub = [w]
                            w_len = len(w)
                        else:
                            w_sub.append(w)
                            w_len += len(w) + 1
                    if w_sub:
                        pieces.append(" ".join(w_sub))
                    continue

            current_chunk.append(line)
            current_len += len(line)

        if current_chunk:
            pieces.append("".join(current_chunk))

        translated_parts = []
        for p in pieces:
            p_strip = p.strip()
            if p_strip:
                trans = translator.translate(p_strip)
                if trans:
                    translated_parts.append(trans)

        return " ".join(translated_parts).strip()
    except Exception as e:
        print(f"[Translation Warning] Deep-translator notice: {e}. Returning original text.")
        return text

def transcribe_chunk_groq(chunk_path: str, language: str = "english") -> str:
    """Transcribe an audio chunk using Groq's cloud-hosted Whisper API."""
    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Set GROQ_API_KEY in environment variables or .env, "
            "or set TRANSCRIBER_BACKEND=local if running with local PyTorch Whisper."
        )

    from groq import Groq
    client = Groq(api_key=groq_api_key)

    lang_normalized = (language or "english").lower().strip()
    # Map friendly language name to ISO 639-1 code
    lang_code = "en"
    if lang_normalized in ["hinglish", "hindi", "hi"]:
        lang_code = "hi"

    model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()

    # Retry loop with backoff for API robustness
    for attempt in range(4):
        try:
            with open(chunk_path, "rb") as file_handle:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(chunk_path), file_handle),
                    model=model_name,
                    response_format="text",
                    temperature=0.0,
                    language=lang_code if lang_code != "en" or lang_normalized == "english" else None
                )

            text = transcription if isinstance(transcription, str) else getattr(transcription, "text", str(transcription))
            text = text.strip()

            if lang_normalized in ["hinglish", "hindi", "hi"] and text:
                text = translate_text_safely(text, source="auto", target="en")

            return text
        except Exception as e:
            err_str = str(e).lower()
            if attempt < 3 and ("429" in err_str or "rate limit" in err_str or "timeout" in err_str):
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RuntimeError(f"Groq Whisper transcription failed on chunk {os.path.basename(chunk_path)}: {e}") from e

def transcribe_chunk_local(chunk_path: str, language: str = "english") -> str:
    """Transcribe a single audio chunk using local Whisper."""
    model = get_whisper_model()
    lang = (language or "english").lower().strip()

    fast_opts = {
        "fp16": False,
        "beam_size": 1,
        "best_of": 1,
        "temperature": 0,
        "condition_on_previous_text": False,
    }

    if lang in ["hinglish", "hindi", "hi"]:
        result = model.transcribe(chunk_path, **fast_opts)
        text = result.get("text", "").strip()
        if text:
            return translate_text_safely(text, source="auto", target="en")
        return text
    elif lang in ["english", "en"]:
        result = model.transcribe(chunk_path, language="en", **fast_opts)
        return result.get("text", "").strip()
    else:
        result = model.transcribe(chunk_path, **fast_opts)
        return result.get("text", "").strip()

def transcribe_all(chunks: list, language: str = "english") -> str:
    """
    Transcribe a list of audio chunk file paths.
    Routes to Groq cloud Whisper API by default (or local Whisper if TRANSCRIBER_BACKEND=local).
    """
    if not chunks:
        print("[Transcriber] No audio chunks provided for transcription.")
        return ""

    backend = (os.getenv("TRANSCRIBER_BACKEND") or "groq").lower().strip()
    transcripts = []

    for i, chunk_path in enumerate(chunks):
        if not os.path.exists(chunk_path):
            print(f"[Transcriber Warning] Chunk file not found: {chunk_path}")
            continue

        print(f"[Transcriber] Transcribing chunk {i + 1}/{len(chunks)} using backend '{backend}'...")
        if backend == "local":
            chunk_text = transcribe_chunk_local(chunk_path, language)
        else:
            try:
                chunk_text = transcribe_chunk_groq(chunk_path, language)
            except Exception as e:
                # If Groq fails (e.g. missing API key) and local whisper is available, attempt fallback
                if "GROQ_API_KEY is not set" in str(e):
                    try:
                        import whisper  # check if local whisper exists
                        print("[Transcriber] GROQ_API_KEY not set. Falling back to local Whisper...")
                        chunk_text = transcribe_chunk_local(chunk_path, language)
                    except Exception:
                        raise e
                else:
                    raise e

        if chunk_text:
            transcripts.append(chunk_text)

    return " ".join(transcripts).strip()
