import os

_embedding_function = None

def get_embedding_model():
    """Initialize and cache the embedding function lazily."""
    global _embedding_function
    if _embedding_function is not None:
        return _embedding_function

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        print("Loading HuggingFaceEmbeddings ('sentence-transformers/all-MiniLM-L6-v2')...")
        _embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return _embedding_function
    except Exception as e:
        print(f"Notice: HuggingFaceEmbeddings not available ({e}).")

    return None

def create_vector_store(transcript: str, collection_name: str = "meeting_rag"):
    """
    Split the transcript and index into a local ephemeral Chroma store.
    """
    if not transcript or not transcript.strip():
        print("Warning: Empty transcript provided to vector store.")
        return None

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    docs = splitter.create_documents([transcript])
    print(f"Created {len(docs)} text chunk(s) for RAG.")

    embeddings = get_embedding_model()
    if embeddings is not None:
        try:
            return Chroma.from_documents(
                documents=docs,
                embedding=embeddings,
                collection_name=collection_name
            )
        except Exception as e:
            print(f"Chroma with embeddings notice: {e}")

    # Fallback to Chroma default ONNX embeddings
    try:
        return Chroma.from_documents(
            documents=docs,
            collection_name=collection_name
        )
    except Exception as e:
        print(f"Chroma default initialization error: {e}")
        return None
