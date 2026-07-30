import pytest

from app.modules.documents.application.extraction import ExtractedPage
from app.modules.documents.domain.chunking import chunk_pages


def test_chunks_pages_deterministically_with_overlap() -> None:
    pages = (
        ExtractedPage(
            page_number=1,
            text="one two three four five six seven",
        ),
        ExtractedPage(page_number=2, text="second page"),
    )

    chunks = chunk_pages(pages, max_characters=14, overlap_characters=4)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].content == "one two three"
    assert chunks[-1].page_number == 2
    assert chunks[-1].content == "second page"


def test_skips_pages_without_extractable_text() -> None:
    chunks = chunk_pages((ExtractedPage(page_number=1, text=" \n\t "),))

    assert chunks == ()


@pytest.mark.parametrize(
    ("size", "overlap"),
    ((0, 0), (100, 100), (100, -1)),
)
def test_rejects_invalid_chunk_configuration(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_pages((), max_characters=size, overlap_characters=overlap)
