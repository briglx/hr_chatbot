"""Document chunking — splits raw document text into overlapping chunks
suitable for embedding and storage in the vector database.

Two strategies are provided:
- fixed_size: splits by character count with overlap
- sentence: splits on sentence boundaries, groups into chunks by token estimate
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    content: str
    index: int          # position of this chunk in the original document
    char_start: int     # character offset in the original text
    char_end: int


def fixed_size(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[Chunk]:
    """Split text into fixed-size character chunks with overlap.

    Overlap ensures that context spanning a chunk boundary is not lost —
    the last `overlap` characters of each chunk are repeated at the start
    of the next.

    Args:
        text: Raw document text.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to repeat between adjacent chunks.

    Returns:
        List of Chunk objects in document order.
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end].strip()

        if content:
            chunks.append(Chunk(
                content=content,
                index=index,
                char_start=start,
                char_end=end,
            ))
            index += 1

        start += chunk_size - overlap

    return chunks


def sentence_based(
    text: str,
    max_tokens: int = 256,
    overlap_sentences: int = 1,
) -> list[Chunk]:
    """Split text on sentence boundaries, grouping into chunks by token estimate.

    Produces more semantically coherent chunks than fixed_size since sentences
    are never split in the middle. Token count is estimated at 4 chars per token.

    Args:
        text: Raw document text.
        max_tokens: Approximate maximum tokens per chunk (4 chars per token).
        overlap_sentences: Number of sentences from the end of each chunk to
                           repeat at the start of the next.

    Returns:
        List of Chunk objects in document order.
    """
    if not text or not text.strip():
        return []

    max_chars = max_tokens * 4
    sentences = _split_sentences(text)

    if not sentences:
        return []

    chunks = []
    index = 0
    i = 0

    while i < len(sentences):
        current_sentences = []
        current_length = 0

        while i < len(sentences) and current_length + len(sentences[i]) <= max_chars:
            current_sentences.append(sentences[i])
            current_length += len(sentences[i])
            i += 1

        if not current_sentences:
            # single sentence longer than max_chars — include it anyway
            current_sentences.append(sentences[i])
            i += 1

        content = " ".join(current_sentences).strip()
        char_start = text.find(current_sentences[0])

        chunks.append(Chunk(
            content=content,
            index=index,
            char_start=char_start,
            char_end=char_start + len(content),
        ))
        index += 1

        # step back by overlap_sentences for the next chunk
        if overlap_sentences > 0 and i < len(sentences):
            i = max(0, i - overlap_sentences)

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on '.', '!', '?' boundaries."""
    raw = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in raw if s.strip()]