import asyncio
from io import BytesIO

from pypdf import PdfReader

from app.modules.documents.application.extraction import ExtractedPage


class PyPdfTextExtractor:
    async def extract(self, content: bytes) -> tuple[ExtractedPage, ...]:
        return await asyncio.to_thread(self._extract_sync, content)

    @staticmethod
    def _extract_sync(content: bytes) -> tuple[ExtractedPage, ...]:
        reader = PdfReader(BytesIO(content), strict=True)
        return tuple(
            ExtractedPage(page_number=index, text=page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        )
