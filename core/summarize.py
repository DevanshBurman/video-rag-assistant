import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.llm_utils import get_mistral_llm, invoke_with_retry, map_reduce_chain

def generate_title(transcript: str) -> str:
    """Generate a concise, descriptive title for the meeting/video using the first ~4000 chars."""
    if not transcript or not transcript.strip():
        return "Untitled Video / Meeting"

    llm = get_mistral_llm(temperature=0.3)
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a professional editor. Generate a concise, engaging, and descriptive title "
                    "for the following video/meeting transcript. Return ONLY the title text with no quotation marks or commentary."
                )),
                ("user", "Transcript excerpt:\n{text}\n\nTitle:")
            ])
            chain = prompt | llm | StrOutputParser()
            title = invoke_with_retry(chain, {"text": transcript[:4000]}).strip()
            return title.strip('"\'')
        except Exception as e:
            print(f"[LLM Title Warning] Generation notice: {e}")

    # Fallback if no API key or network error
    first_few_words = transcript.strip().split()[:8]
    fallback_title = " ".join(first_few_words).capitalize()
    if len(fallback_title) > 60:
        fallback_title = fallback_title[:57] + "..."
    return fallback_title or "AI Video Summary"

def summarize(transcript: str) -> str:
    """Generate an executive summary of the meeting/video transcript using Map-Reduce for long inputs."""
    if not transcript or not transcript.strip():
        return "No transcript content available to summarize."

    llm = get_mistral_llm(temperature=0.2)
    if llm:
        try:
            map_system = (
                "You are an expert executive assistant. Summarize this section of a video/meeting transcript concisely. "
                "Highlight key discussion points, main arguments, and any preliminary conclusions."
            )
            map_user = "Section {part_idx} of {total_parts}:\n{text}\n\nKey Section Insights:"

            reduce_system = (
                "You are an expert executive assistant. Provide a structured, high-quality, comprehensive Executive Summary "
                "based on the provided transcript notes.\n"
                "Your summary MUST include:\n"
                "1. Overview & Core Theme\n"
                "2. Key Discussion Points (with substantive details)\n"
                "3. Main Takeaways & Conclusion\n"
                "Keep the tone objective, clear, and professional."
            )
            reduce_user = "Transcript Analysis Material:\n{text}\n\nStructured Executive Summary:"

            return map_reduce_chain(
                text=transcript,
                llm=llm,
                map_system_prompt=map_system,
                map_user_template=map_user,
                reduce_system_prompt=reduce_system,
                reduce_user_template=reduce_user,
                chunk_size=8000,
                overlap=1000
            )
        except Exception as e:
            print(f"[LLM Summary Warning] Generation notice: {e}")

    # Fallback if MISTRAL_API_KEY is not set or failed
    preview = transcript.strip()
    if len(preview) > 600:
        preview = preview[:600] + "..."
    return (
        "⚠️ [Note: Set MISTRAL_API_KEY in .env to enable generative AI summaries with Mistral]\n\n"
        f"Transcript Preview:\n{preview}"
    )
