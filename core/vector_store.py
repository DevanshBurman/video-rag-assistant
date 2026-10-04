import os
import time
import uuid
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

# ── In-Memory Session Store with TTL ──────────────────────────────────────────
_session_stores = {}
SESSION_TTL_SECONDS = 3600  # 1 hour
MAX_SESSIONS = 50

def _cleanup_expired_sessions():
    now = time.time()
    expired = [
        sid for sid, data in _session_stores.items()
        if now - data.get("created_at", now) > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _session_stores.pop(sid, None)

    if len(_session_stores) > MAX_SESSIONS:
        sorted_s = sorted(_session_stores.items(), key=lambda x: x[1].get("created_at", 0))
        for sid, _ in sorted_s[:len(_session_stores) - MAX_SESSIONS]:
            _session_stores.pop(sid, None)

# ── Lightweight Embeddings: Mistral API + FastEmbed ONNX Fallback ──────────────

class MistralDirectEmbeddings(Embeddings):
    """Direct, lightweight Mistral API embeddings without requiring HuggingFace tokenizers."""
    def __init__(self, api_key: str, model: str = "mistral-embed"):
        try:
            from mistralai.client import Mistral
            self.client = Mistral(api_key=api_key)
        except Exception:
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Batch in chunks of 32 to respect API boundaries
        all_embeddings = []
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            res = self.client.embeddings.create(model=self.model, inputs=batch)
            all_embeddings.extend([item.embedding for item in res.data])
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        res = self.client.embeddings.create(model=self.model, inputs=[text])
        return res.data[0].embedding


class FastEmbedWrapper(Embeddings):
    """Ultra-lightweight ONNX-powered local embeddings without PyTorch or sentence-transformers."""
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [list(map(float, e)) for e in self.model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(map(float, next(self.model.embed([text]))))


def get_embedding_model():
    """
    Returns Mistral embeddings by default (if MISTRAL_API_KEY is available),
    or FastEmbed ONNX embeddings as zero-API lightweight fallback.
    Never requires PyTorch or heavy sentence-transformers.
    """
    mistral_key = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if mistral_key:
        try:
            return MistralDirectEmbeddings(api_key=mistral_key, model="mistral-embed")
        except Exception as e:
            print(f"[VectorStore Notice] Could not initialize MistralDirectEmbeddings: {e}")

    try:
        print("[VectorStore] Using FastEmbed ONNX local embeddings...")
        return FastEmbedWrapper()
    except Exception as e:
        print(f"[VectorStore Notice] FastEmbed not available: {e}")

    return None

def format_approx_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS timestamp."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def create_vector_store(transcript: str, session_id: str = None):
    """
    Split the transcript, index into a unique in-memory ephemeral Chroma store per session.
    Returns the initialized Chroma vector store instance.
    """
    if not transcript or not transcript.strip():
        print("[VectorStore Warning] Empty transcript provided to vector store.")
        return None

    _cleanup_expired_sessions()

    if not session_id:
        session_id = str(uuid.uuid4())

    collection_name = f"session_{session_id.replace('-', '_')[:28]}"

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import chromadb
    from langchain_community.vectorstores import Chroma

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    raw_chunks = splitter.split_text(transcript)
    total_chunks = len(raw_chunks)

    # Estimate timing: average speech rate ~150 words/min = 2.5 words/sec.
    # An 800-char chunk is ~130 words = ~50 seconds of speech.
    docs = []
    accumulated_words = 0
    for idx, chunk_text in enumerate(raw_chunks):
        approx_start_sec = (accumulated_words / 150.0) * 60.0
        timestamp_str = format_approx_timestamp(approx_start_sec)
        words_in_chunk = len(chunk_text.split())
        accumulated_words += words_in_chunk

        metadata = {
            "chunk_id": idx,
            "chunk_index": f"{idx + 1}/{total_chunks}",
            "part": f"Part {idx + 1} of {total_chunks} (~{timestamp_str})",
            "approx_timestamp": timestamp_str,
            "session_id": session_id,
        }
        docs.append(Document(page_content=chunk_text, metadata=metadata))

    print(f"[VectorStore] Indexing {len(docs)} text chunk(s) for session {session_id} into ephemeral collection '{collection_name}'...")

    embeddings = get_embedding_model()
    client = chromadb.EphemeralClient()

    try:
        store = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            client=client,
            collection_name=collection_name
        )
    except Exception as e:
        print(f"[VectorStore Error] Failed with primary embeddings ({e}). Attempting ONNX fallback...")
        fallback_emb = FastEmbedWrapper()
        store = Chroma.from_documents(
            documents=docs,
            embedding=fallback_emb,
            client=client,
            collection_name=collection_name
        )

    _session_stores[session_id] = {
        "store": store,
        "created_at": time.time(),
        "total_chunks": total_chunks,
    }

    return store

def get_session_store(session_id: str):
    """Retrieve vector store instance for a given session ID."""
    _cleanup_expired_sessions()
    entry = _session_stores.get(session_id)
    return entry["store"] if entry else None
