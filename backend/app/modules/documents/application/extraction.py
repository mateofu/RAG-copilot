from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str


class PdfTextExtractor(Protocol):
    async def extract(self, content: bytes) -> tuple[ExtractedPage, ...]: ...
