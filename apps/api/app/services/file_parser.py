"""업로드 파일 텍스트 추출 (PDF/DOCX/TXT/MD)."""
from io import BytesIO
from pathlib import Path


def extract_text(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pdfminer.high_level import extract_text as pdf_extract
            return pdf_extract(BytesIO(raw))
        except Exception as e:  # noqa: BLE001
            return f"(pdf 추출 실패: {e})"
    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:  # noqa: BLE001
            return f"(docx 추출 실패: {e})"
    return ""


def chunk_text(text: str, max_chars: int = 1500) -> list[dict]:
    """간단 청크 분할 (paragraph → 길이 누적)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, idx = [], [], 0
    cur_len = 0
    for p in paragraphs:
        if cur_len + len(p) > max_chars and buf:
            chunks.append({"idx": idx, "text": "\n\n".join(buf), "tokens": cur_len // 4})
            idx += 1
            buf, cur_len = [], 0
        buf.append(p)
        cur_len += len(p)
    if buf:
        chunks.append({"idx": idx, "text": "\n\n".join(buf), "tokens": cur_len // 4})
    return chunks
