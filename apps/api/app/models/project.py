"""T-02 / T-03 — project, project_attachment."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, CHAR, Enum, ForeignKey, Integer, String, TIMESTAMP, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(CHAR(36), unique=True, default=lambda: str(uuid4()))
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"))
    company_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_name: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_dev: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_ops: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(Enum("OPENAI", "GEMINI", "ANTHROPIC"), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("DRAFT", "READY", "GENERATED", "ARCHIVED"), default="DRAFT"
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=text("CURRENT_TIMESTAMP")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)


class ProjectAttachment(Base):
    __tablename__ = "project_attachment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project.id"))
    slot: Mapped[str] = mapped_column(Enum("NOTICE", "REFERENCE"))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    mongo_doc_id: Mapped[str | None] = mapped_column(CHAR(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
