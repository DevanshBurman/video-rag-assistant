import os
import re
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
        return ChatMistralAI(model=model_name, api_key=api_key, temperature=0.2)
    except Exception as e:
        print(f"Warning: Failed to initialize ChatMistralAI: {e}")
        return None

def extract_action_items(transcript: str) -> str:
    """Extract action items, tasks, and follow-ups from the transcript."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = _get_mistral_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an assistant specialized in meeting productivity. "
                    "Extract all action items, assigned tasks, next steps, and deadlines from the transcript. "
                    "Format each as: '- [ ] Task description (Assignee / Due date if mentioned)'. "
                    "If no clear action items are mentioned, reply with 'No specific action items identified.'"
                )),
                ("user", "Transcript:\n{text}\n\nAction Items:")
            ])
            chain = prompt | llm | StrOutputParser()
            return chain.invoke({"text": transcript[:12000]}).strip()
        except Exception as e:
            print(f"LLM Action Items extraction notice: {e}")

    # Fallback heuristic
    sentences = re.split(r'[.!?\n]', transcript)
    keywords = ["need to", "will do", "should", "action", "follow up", "todo", "assigned", "responsible"]
    matches = [s.strip() for s in sentences if any(k in s.lower() for k in keywords) and len(s.strip()) > 15]
    if matches:
        return "\n".join([f"- [ ] {m}" for m in matches[:5]])
    return "No explicit action items found in transcript. (Set MISTRAL_API_KEY in .env for full AI extraction)"

def extract_key_decisions(transcript: str) -> str:
    """Extract key decisions, consensus, and agreements from the transcript."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = _get_mistral_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an assistant specialized in business and technical meetings. "
                    "Extract all key decisions, agreements, resolutions, and conclusions reached in the transcript. "
                    "Format each decision as a concise bullet point. "
                    "If no explicit decisions were made, reply with 'No explicit decisions identified.'"
                )),
                ("user", "Transcript:\n{text}\n\nKey Decisions:")
            ])
            chain = prompt | llm | StrOutputParser()
            return chain.invoke({"text": transcript[:12000]}).strip()
        except Exception as e:
            print(f"LLM Key Decisions extraction notice: {e}")

    # Fallback heuristic
    sentences = re.split(r'[.!?\n]', transcript)
    keywords = ["decided", "agreed", "chose", "conclusion", "settled", "approved", "going with"]
    matches = [s.strip() for s in sentences if any(k in s.lower() for k in keywords) and len(s.strip()) > 15]
    if matches:
        return "\n".join([f"- {m}" for m in matches[:5]])
    return "No explicit decisions found in transcript. (Set MISTRAL_API_KEY in .env for full AI extraction)"

def extract_questions(transcript: str) -> str:
    """Extract open questions, inquiries, and unresolved topics from the transcript."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = _get_mistral_llm()
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "Extract all open questions, unanswered queries, and discussion points raised in the transcript. "
                    "Format each question as a bullet point. "
                    "If no questions were raised, reply with 'No open questions identified.'"
                )),
                ("user", "Transcript:\n{text}\n\nOpen Questions:")
            ])
            chain = prompt | llm | StrOutputParser()
            return chain.invoke({"text": transcript[:12000]}).strip()
        except Exception as e:
            print(f"LLM Questions extraction notice: {e}")

    # Fallback heuristic: find actual question sentences
    sentences = [s.strip() for s in transcript.split("\n") if "?" in s]
    if not sentences:
        sentences = [s.strip() for s in re.findall(r'[^.!?\n]+\?', transcript)]
    if sentences:
        return "\n".join([f"- {s}" for s in sentences[:5]])
    return "No open questions identified. (Set MISTRAL_API_KEY in .env for full AI extraction)"
