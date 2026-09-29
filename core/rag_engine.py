import os
from core.vector_store import create_vector_store

def _format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def build_rag_chain(transcript: str):
    """
    Builds the retrieval-augmented generation pipeline using Chroma and Mistral.
    """
    vector_store = create_vector_store(transcript)
    if not vector_store:
        return {"type": "empty", "transcript": transcript}

    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    api_key = os.getenv("MISTRAL_API_KEY")
    if api_key:
        try:
            from langchain_mistralai import ChatMistralAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough
            from langchain_core.output_parsers import StrOutputParser

            model_name = (os.getenv("MISTRAL_MODEL") or "open-mistral-7b").strip()
            llm = ChatMistralAI(model=model_name, api_key=api_key.strip(), temperature=0.2)

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a helpful and knowledgeable assistant. "
                    "Use the retrieved context below from the video/meeting transcript to answer the user's question accurately. "
                    "If the answer cannot be found in the context, politely state that the meeting content does not cover it.\n\n"
                    "Context:\n{context}"
                )),
                ("user", "{question}")
            ])

            chain = (
                {"context": retriever | _format_docs, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            return {"type": "lcel", "chain": chain, "retriever": retriever}
        except Exception as e:
            print(f"Notice: Failed to initialize Mistral LCEL chain ({e}). Falling back to retriever.")

    return {"type": "retriever_only", "retriever": retriever, "transcript": transcript}

def ask_question(rag_chain, question: str) -> str:
    """
    Query the RAG chain with a user question and return the answer string.
    """
    if not rag_chain:
        return "RAG engine is not initialized."

    if isinstance(rag_chain, dict):
        chain_type = rag_chain.get("type")
        if chain_type == "lcel":
            try:
                return rag_chain["chain"].invoke(question)
            except Exception as e:
                return f"Error executing question: {e}"
        elif chain_type == "retriever_only":
            retriever = rag_chain.get("retriever")
            if retriever:
                try:
                    docs = retriever.invoke(question)
                    if docs:
                        relevant_snippets = "\n---\n".join(d.page_content for d in docs[:3])
                        return (
                            f"[Note: Add MISTRAL_API_KEY to .env for AI-synthesized answers]\n\n"
                            f"Relevant transcript excerpts for '{question}':\n\n{relevant_snippets}"
                        )
                except Exception as e:
                    return f"Search error: {e}"
            return "No matching content found in transcript."
        elif chain_type == "empty":
            return "No transcript content available to answer questions."

    if hasattr(rag_chain, "invoke"):
        try:
            return rag_chain.invoke(question)
        except Exception as e:
            return f"Error running RAG chain: {e}"

    return "Unable to process question."
