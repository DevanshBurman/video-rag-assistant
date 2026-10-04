import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

DEFAULT_MISTRAL_MODEL = "mistral-small-latest"

def get_mistral_llm(temperature: float = 0.2):
    """Initialize ChatMistralAI with configured model and temperature."""
    api_key = (os.getenv("MISTRAL_API_KEY") or "").strip()
    if not api_key:
        return None
    model_name = (os.getenv("MISTRAL_MODEL") or DEFAULT_MISTRAL_MODEL).strip()
    try:
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(model=model_name, api_key=api_key, temperature=temperature, max_retries=3)
    except Exception as e:
        print(f"[LLM Warning] Failed to initialize ChatMistralAI: {e}")
        return None

def invoke_with_retry(chain, inputs, max_retries: int = 5, base_delay: float = 2.0):
    """
    Invoke a LangChain runnable with exponential backoff on rate limits (429) or transient errors.
    """
    for attempt in range(max_retries):
        try:
            return chain.invoke(inputs)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "rate limit" in err_str or "capacity" in err_str or "status code 429" in err_str
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0.2, 0.8)
                print(f"[LLM Retry] Rate limit 429 detected. Backing off for {sleep_time:.2f}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(sleep_time)
                continue
            if attempt < max_retries - 1 and ("timeout" in err_str or "connection" in err_str):
                time.sleep(1.5)
                continue
            raise

def split_text_chunks(text: str, chunk_size: int = 8000, overlap: int = 1000) -> list[str]:
    """
    Split long text into overlapping chunks respecting paragraph or sentence boundaries where possible.
    """
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    total_len = len(text)

    while start < total_len:
        end = min(start + chunk_size, total_len)
        if end < total_len:
            # Try to snap to newline or period within the last 500 chars of the chunk
            search_window = text[max(start, end - 500):end]
            last_break = max(search_window.rfind("\n"), search_window.rfind(". "))
            if last_break != -1:
                end = max(start, end - 500) + last_break + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= total_len:
            break
        start = max(start + 1, end - overlap)

    return chunks

def map_reduce_chain(
    text: str,
    llm,
    map_system_prompt: str,
    map_user_template: str,
    reduce_system_prompt: str,
    reduce_user_template: str,
    chunk_size: int = 8000,
    overlap: int = 1000,
    max_workers: int = 3,
) -> str:
    """
    Executes a Map-Reduce pipeline over long transcripts:
    1. Splits transcript into chunks of ~8000 characters.
    2. Runs map prompt concurrently on each chunk (concurrency limited to avoid 429s).
    3. Merges and deduplicates mapped outputs via a reduce prompt.
    """
    if not text or not text.strip():
        return ""

    # Single chunk bypass: if text is short enough, run reduce prompt directly on it
    chunks = split_text_chunks(text, chunk_size=chunk_size, overlap=overlap)
    if len(chunks) == 1:
        prompt = ChatPromptTemplate.from_messages([
            ("system", reduce_system_prompt),
            ("user", reduce_user_template)
        ])
        chain = prompt | llm | StrOutputParser()
        return invoke_with_retry(chain, {"text": chunks[0]}).strip()

    # Step 1: Map stage
    map_prompt = ChatPromptTemplate.from_messages([
        ("system", map_system_prompt),
        ("user", map_user_template)
    ])
    map_chain = map_prompt | llm | StrOutputParser()

    mapped_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(invoke_with_retry, map_chain, {"text": chunk, "part_idx": i + 1, "total_parts": len(chunks)})
            for i, chunk in enumerate(chunks)
        ]
        for f in futures:
            res = f.result()
            if res and res.strip():
                mapped_results.append(res.strip())

    combined_map_output = "\n\n--- SECTION BREAK ---\n\n".join(mapped_results)

    # Step 2: Reduce stage
    reduce_prompt = ChatPromptTemplate.from_messages([
        ("system", reduce_system_prompt),
        ("user", reduce_user_template)
    ])
    reduce_chain = reduce_prompt | llm | StrOutputParser()

    return invoke_with_retry(reduce_chain, {"text": combined_map_output}).strip()
