import os
import re
from core.llm_utils import get_mistral_llm, map_reduce_chain

def extract_action_items(transcript: str) -> str:
    """Extract action items, tasks, and follow-ups from the transcript using Map-Reduce for long inputs."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = get_mistral_llm(temperature=0.1)
    if llm:
        try:
            map_system = (
                "You are an assistant specialized in meeting productivity. "
                "Extract all action items, assigned tasks, next steps, and deadlines from this section of the transcript. "
                "Format each as: '- [ ] Task description (Assignee / Due date if mentioned)'. "
                "If none are mentioned in this section, reply with 'None'."
            )
            map_user = "Section {part_idx} of {total_parts}:\n{text}\n\nAction Items:"

            reduce_system = (
                "You are an assistant specialized in meeting productivity. "
                "The following are action items extracted across different sections of a transcript. "
                "Consolidate, deduplicate, and organize them into a clean, prioritized final checklist. "
                "Format each as: '- [ ] Task description (Assignee / Due date if mentioned)'. "
                "If no action items are present, reply with 'No specific action items identified.'"
            )
            reduce_user = "Extracted Section Action Items:\n{text}\n\nFinal Consolidated Action Checklist:"

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
            print(f"[LLM Action Items Warning] Extraction notice: {e}")

    # Fallback heuristic
    sentences = re.split(r'[.!?\n]', transcript)
    keywords = ["need to", "will do", "should", "action", "follow up", "todo", "assigned", "responsible", "deadline"]
    matches = [s.strip() for s in sentences if any(k in s.lower() for k in keywords) and len(s.strip()) > 15]
    if matches:
        return "\n".join([f"- [ ] {m}" for m in matches[:8]])
    return "No explicit action items found in transcript. (Set MISTRAL_API_KEY in .env for full AI extraction)"

def extract_key_decisions(transcript: str) -> str:
    """Extract key decisions, consensus, and agreements from the transcript using Map-Reduce."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = get_mistral_llm(temperature=0.1)
    if llm:
        try:
            map_system = (
                "You are an assistant specialized in business and technical meetings. "
                "Extract all key decisions, agreements, resolutions, and conclusions reached in this section. "
                "Format each decision as a concise bullet point starting with '- '. "
                "If no decisions were made in this section, reply with 'None'."
            )
            map_user = "Section {part_idx} of {total_parts}:\n{text}\n\nDecisions in this section:"

            reduce_system = (
                "You are an assistant specialized in meeting minutes and decision logging. "
                "The following are decisions extracted from multiple sections of a video/meeting transcript. "
                "Consolidate, deduplicate, and organize them into a clear, unified list of key decisions. "
                "Format each decision as a bullet point starting with '- '. "
                "If no explicit decisions were identified, reply with 'No explicit decisions identified.'"
            )
            reduce_user = "Extracted Decisions:\n{text}\n\nFinal Unified Key Decisions:"

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
            print(f"[LLM Key Decisions Warning] Extraction notice: {e}")

    # Fallback heuristic
    sentences = re.split(r'[.!?\n]', transcript)
    keywords = ["decided", "agreed", "chose", "conclusion", "settled", "approved", "going with", "resolved"]
    matches = [s.strip() for s in sentences if any(k in s.lower() for k in keywords) and len(s.strip()) > 15]
    if matches:
        return "\n".join([f"- {m}" for m in matches[:8]])
    return "No explicit decisions found in transcript. (Set MISTRAL_API_KEY in .env for full AI extraction)"

def extract_questions(transcript: str) -> str:
    """Extract open questions, inquiries, and unresolved topics from the transcript using Map-Reduce."""
    if not transcript or not transcript.strip():
        return "No transcript content provided."

    llm = get_mistral_llm(temperature=0.1)
    if llm:
        try:
            map_system = (
                "Extract all open questions, unanswered queries, uncertainties, and discussion points raised in this section. "
                "Format each question as a bullet point starting with '- '. "
                "If none were raised, reply with 'None'."
            )
            map_user = "Section {part_idx} of {total_parts}:\n{text}\n\nQuestions raised:"

            reduce_system = (
                "The following are open questions and unresolved topics extracted across various sections of a video/meeting transcript. "
                "Consolidate, deduplicate, and present a clean bulleted list of substantive open questions. "
                "Format each question as a bullet point starting with '- '. "
                "If no open questions were identified, reply with 'No open questions identified.'"
            )
            reduce_user = "Extracted Questions:\n{text}\n\nConsolidated Open Questions:"

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
            print(f"[LLM Questions Warning] Extraction notice: {e}")

    # Fallback heuristic: find actual question sentences
    sentences = [s.strip() for s in transcript.split("\n") if "?" in s]
    if not sentences:
        sentences = [s.strip() for s in re.findall(r'[^.!?\n]+\?', transcript)]
    if sentences:
        return "\n".join([f"- {s}" for s in sentences[:8]])
    return "No open questions identified. (Set MISTRAL_API_KEY in .env for full AI extraction)"
