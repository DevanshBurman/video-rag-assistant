import os

_whisper_model = None

def get_whisper_model(model_size: str = None):
    """Load and cache the Whisper model in memory lazily."""
    global _whisper_model
    if model_size is None:
        model_size = os.getenv("WHISPER_MODEL", "base").strip() or "base"
    if _whisper_model is None:
        import whisper
        print(f"Loading Whisper model ('{model_size}')...")
        _whisper_model = whisper.load_model(model_size)
    return _whisper_model

def transcribe_chunk(model, chunk_path: str, language: str = "english") -> str:
    """Transcribe a single audio chunk using fast Whisper decoding."""
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
        try:
            if text:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source="auto", target="en")
                translated = translator.translate(text)
                if translated:
                    return translated
        except Exception as e:
            print(f"Translation warning: {e}. Using raw transcript.")
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
    Returns the combined transcript string.
    """
    if not chunks:
        print("No audio chunks provided for transcription.")
        return ""

    model = get_whisper_model()
    transcripts = []

    for i, chunk_path in enumerate(chunks):
        if not os.path.exists(chunk_path):
            print(f"Warning: Chunk file not found: {chunk_path}")
            continue

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")
        chunk_text = transcribe_chunk(model, chunk_path, language)
        if chunk_text:
            transcripts.append(chunk_text)

    full_transcript = " ".join(transcripts).strip()
    return full_transcript
