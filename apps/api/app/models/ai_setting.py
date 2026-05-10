"""T-05. ai_provider_setting."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, LargeBinary, Numeric, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class AiProviderSetting(Base):
    __tablename__ = "ai_provider_setting"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"))
    provider: Mapped[str] = mapped_column(Enum("OPENAI", "GEMINI", "ANTHROPIC"))
    alias: Mapped[str | None] = mapped_column(String(80), nullable=True)
    api_key_cipher: Mapped[bytes] = mapped_column(LargeBinary(512))
    key_iv: Mapped[bytes] = mapped_column(LargeBinary(16))
    key_tag: Mapped[bytes] = mapped_column(LargeBinary(16))
    default_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=Decimal("0.40"))
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[int] = mapped_column(SmallInteger, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=text("CURRENT_TIMESTAMP")
    )
