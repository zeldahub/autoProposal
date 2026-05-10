"""T-09. notification — 인앱 알림."""
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, JSON, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"))
    type: Mapped[str] = mapped_column(Enum("GENERATE", "JOB", "SYSTEM", "PROJECT"))
    level: Mapped[str] = mapped_column(Enum("INFO", "SUCCESS", "WARN", "ERROR"), default="INFO")
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
