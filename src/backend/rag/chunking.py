from typing import List, Tuple
import re

def chunk_text(text: str, target_tokens=250, overlap_tokens=40) -> List[Tuple[int,int,str]]:
    # simple token = whitespace split; replace with tiktoken if you prefer
    words = text.split()
    if not words: return []
    step = max(1, target_tokens - overlap_tokens)
    chunks, i = [], 0
    start_idx = 0
    while i < len(words):
        end = min(len(words), i + target_tokens)
        chunk_words = words[i:end]
        chunk = " ".join(chunk_words)
        chunks.append((start_idx, start_idx + len(chunk), chunk))
        start_idx += len(chunk) + 1
        i += step
    return chunks
