import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def _get_mistral_llm():
    """Helper to initialize ChatMistralAI if API key is present."""
    api_key = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if not api_key:
        return None
    model_name = (os.getenv("MISTRAL_MODEL") or "open-mistral-7b").strip()
    try:
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(model=model_name, api_key=api_key, temperature=0.3)
    except Exception as e:
        print(f"Warning: Failed to initialize ChatMistralAI: {e}")
        return None

def generate_title(transcript: str) -> str:
    """Generate a concise, descriptive title for the meeting/video."""
    if not transcript or not transcript.strip():
        return "Untitled Video / Meeting"

    llm = _get_mistral_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a professional editor. Generate a concise, engaging, and descriptive title for the following video/meeting transcript. Return ONLY the title text with no quotation marks or commentary."),
                ("user", "Transcript excerpt:\n{text}\n\nTitle:")
            ])
            chain = prompt | llm | StrOutputParser()
            title = chain.invoke({"text": transcript[:4000]}).strip()
            return title.strip('"\'')
        except Exception as e:
            print(f"LLM Title generation notice: {e}")

    # Fallback if no API key or network error
    first_few_words = transcript.strip().split()[:8]
    fallback_title = " ".join(first_few_words).capitalize()
    if len(fallback_title) > 60:
        fallback_title = fallback_title[:57] + "..."
    return fallback_title or "AI Video Summary"

def summarize(transcript: str) -> str:
    """Generate an executive summary of the meeting/video transcript."""
    if not transcript or not transcript.strip():
        return "No transcript content available to summarize."

    llm = _get_mistral_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert executive assistant. Provide a structured, high-quality summary of the following transcript. "
                    "Include:\n"
                    "1. Overview & Core Theme\n"
                    "2. Key Discussion Points\n"
                    "3. Main Takeaways & Conclusion\n"
                    "Keep the tone objective, clear, and professional."
                )),
                ("user", "Transcript:\n{text}\n\nStructured Summary:")
            ])
            chain = prompt | llm | StrOutputParser()
            return chain.invoke({"text": transcript[:12000]}).strip()
        except Exception as e:
            print(f"LLM Summary generation notice: {e}")

    # Fallback if MISTRAL_API_KEY is not set
    preview = transcript.strip()
    if len(preview) > 600:
        preview = preview[:600] + "..."
    return (
        "⚠️ [Note: Set MISTRAL_API_KEY in .env to enable generative AI summaries with Mistral]\n\n"
        f"Transcript Preview:\n{preview}"
    )
