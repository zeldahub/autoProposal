"""T-06. llm_call_log."""
from datetime import datetime

from sqlalchemy import BigInteger, CHAR, Enum, ForeignKey, Integer, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class LlmCallLog(Base):
    __tablename__ = "llm_call_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project.id"))
    provider: Mapped[str] = mapped_column(Enum("OPENAI", "GEMINI", "ANTHROPIC"))
    model: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(Enum("ANALYZE", "GEN_PPTX", "GEN_WBS", "TEST"))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mongo_session_id: Mapped[str | None] = mapped_column(CHAR(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
