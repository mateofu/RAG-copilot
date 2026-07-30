import re
from dataclasses import dataclass

from app.modules.documents.application.extraction import ExtractedPage

WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    page_number: int
    char_start: int
    char_end: int
    content: str


def chunk_pages(
    pages: tuple[ExtractedPage, ...],
    max_characters: int = 1500,
    overlap_characters: int = 200,
) -> tuple[TextChunk, ...]:
    if max_characters <= 0 or not 0 <= overlap_characters < max_characters:
        raise ValueError("invalid chunk size")

    chunks: list[TextChunk] = []
    for page in pages:
        text = WHITESPACE.sub(" ", page.text).strip()
        start = 0
        while start < len(text):
            end = min(start + max_characters, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary
            content = text[start:end].strip()
            if content:
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        page_number=page.page_number,
                        char_start=start,
                        char_end=end,
                        content=content,
                    )
                )
            if end == len(text):
                break
            start = max(end - overlap_characters, start + 1)
    return tuple(chunks)
