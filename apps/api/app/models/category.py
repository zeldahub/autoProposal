"""T-07. proposal_category."""
from datetime import datetime

from sqlalchemy import Integer, SmallInteger, String, TIMESTAMP, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class ProposalCategory(Base):
    __tablename__ = "proposal_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name_ko: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer)
    slide_template_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=text("CURRENT_TIMESTAMP")
    )
