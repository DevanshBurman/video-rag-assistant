import os
from core.vector_store import create_vector_store
from core.llm_utils import get_mistral_llm, invoke_with_retry

def _format_docs(docs):
    """Format retrieved documents with their part index and timestamp metadata."""
    formatted = []
    for doc in docs:
        source_label = doc.metadata.get("part") or f"Chunk {doc.metadata.get('chunk_id', 0)}"
        formatted.append(f"[{source_label}]:\n{doc.page_content}")
    return "\n\n".join(formatted)

def build_rag_chain(transcript: str, session_id: str = None):
    """
    Builds the retrieval-augmented generation pipeline using ephemeral in-memory Chroma,
    MMR search, and Mistral LLM.
    """
    vector_store = create_vector_store(transcript, session_id=session_id)
    if not vector_store:
        return {"type": "empty", "transcript": transcript}

    # Use Maximal Marginal Relevance (MMR) for diverse, non-redundant context retrieval
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 10}
    )

    llm = get_mistral_llm(temperature=0.2)
    if llm:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough
            from langchain_core.output_parsers import StrOutputParser

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a helpful, precise AI assistant analyzing a video/meeting transcript.\n"
                    "Use the retrieved context excerpts below to answer the user's question accurately.\n\n"
                    "STRICT GUIDELINES:\n"
                    "1. Always explicitly cite which part of the video your answer comes from (e.g., '[From Part 2 of 5 (~01:40)]').\n"
                    "2. If the retrieved context does not contain sufficient information to answer the question, "
                    "clearly and politely state that the video transcript does not cover this topic.\n"
                    "3. Do not invent or extrapolate facts beyond what is stated in the context.\n\n"
                    "Retrieved Context:\n{context}"
                )),
                ("user", "{question}")
            ])

            chain = (
                {"context": retriever | _format_docs, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            return {"type": "lcel", "chain": chain, "retriever": retriever, "vector_store": vector_store}
        except Exception as e:
            print(f"[RAG Notice] Failed to initialize Mistral LCEL chain ({e}). Falling back to retriever.")

    return {"type": "retriever_only", "retriever": retriever, "transcript": transcript}

def ask_question(rag_chain, question: str) -> str:
    """
    Query the RAG chain with a user question and return the synthesized answer string.
    """
    if not rag_chain:
        return "RAG engine is not initialized for this session."

    if isinstance(rag_chain, dict):
        chain_type = rag_chain.get("type")
        if chain_type == "lcel":
            try:
                chain = rag_chain["chain"]
                return invoke_with_retry(chain, question, max_retries=4, base_delay=2.0)
            except Exception as e:
                print(f"[RAG Notice] LCEL chain execution notice ({e}). Falling back to retrieved snippets.")
                retriever = rag_chain.get("retriever")
                if retriever:
                    try:
                        docs = retriever.invoke(question)
                        if docs:
                            snippets = "\n\n---\n\n".join(
                                f"[{d.metadata.get('part', 'Excerpt')}]:\n{d.page_content}"
                                for d in docs[:3]
                            )
                            return f"[Retrieved from Video]:\n\n{snippets}"
                    except Exception:
                        pass
                return f"Unable to generate response: {e}"
        elif chain_type == "retriever_only":
            retriever = rag_chain.get("retriever")
            if retriever:
                try:
                    docs = retriever.invoke(question)
                    if docs:
                        snippets = "\n\n---\n\n".join(
                            f"[{d.metadata.get('part', 'Excerpt')}]:\n{d.page_content}"
                            for d in docs[:3]
                        )
                        return (
                            f"[Note: Add MISTRAL_API_KEY to .env for AI-synthesized answers]\n\n"
                            f"Most relevant transcript excerpts:\n\n{snippets}"
                        )
                except Exception as e:
                    return f"Search error: {e}"
            return "No matching content found in transcript for this query."
        elif chain_type == "empty":
            return "No transcript content available to answer questions."

    if hasattr(rag_chain, "invoke"):
        try:
            return rag_chain.invoke(question)
        except Exception as e:
            return f"Error running RAG chain: {e}"

    return "Unable to process question."
