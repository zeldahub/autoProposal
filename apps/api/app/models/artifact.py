"""T-04. artifact."""
from datetime import datetime

from sqlalchemy import BigInteger, CHAR, Enum, ForeignKey, Integer, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class Artifact(Base):
    __tablename__ = "artifact"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project.id"))
    type: Mapped[str] = mapped_column(Enum("PPTX", "XLSX"))
    version: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    llm_call_log_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mongo_draft_id: Mapped[str | None] = mapped_column(CHAR(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
