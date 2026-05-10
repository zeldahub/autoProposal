"""file_parser.extract_text + chunk_text 단위 테스트."""
from app.services.file_parser import chunk_text, extract_text


class TestExtractText:
    def test_txt(self):
        raw = "Hello\n한국어 본문".encode("utf-8")
        assert extract_text("a.txt", raw) == "Hello\n한국어 본문"

    def test_md(self):
        raw = "# title\nbody".encode("utf-8")
        assert extract_text("doc.md", raw) == "# title\nbody"

    def test_unknown_ext(self):
        assert extract_text("a.zip", b"raw") == ""

    def test_invalid_pdf(self):
        # pdfminer 가 실패해야 — fallback 메시지 반환
        result = extract_text("bad.pdf", b"not really a pdf")
        assert "추출 실패" in result or result == ""

    def test_invalid_docx(self):
        result = extract_text("bad.docx", b"not zip")
        assert "추출 실패" in result or result == ""


class TestChunkText:
    def test_empty(self):
        assert chunk_text("") == []
        assert chunk_text("\n\n\n") == []

    def test_short_single_chunk(self):
        chunks = chunk_text("hello world")
        assert len(chunks) == 1
        assert chunks[0]["idx"] == 0
        assert chunks[0]["text"] == "hello world"

    def test_split_by_size(self):
        # 두 단락 — 각 1000자 → max=1500 으로 두 청크 분할
        p1 = "A" * 1000
        p2 = "B" * 1000
        chunks = chunk_text(f"{p1}\n\n{p2}", max_chars=1500)
        assert len(chunks) == 2
        assert chunks[0]["text"] == p1
        assert chunks[1]["text"] == p2
        assert chunks[0]["idx"] == 0
        assert chunks[1]["idx"] == 1

    def test_strips_blank_paragraphs(self):
        chunks = chunk_text("first\n\n\n\n  \n\nsecond")
        assert len(chunks) == 1
        joined = chunks[0]["text"]
        assert "first" in joined and "second" in joined
