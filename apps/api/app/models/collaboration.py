"""T-COLLAB. project_share + project_comment."""
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Text, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_maria import Base


class ProjectShare(Base):
    __tablename__ = "project_share"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(Enum("READ", "EDIT"), default="READ")
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class ProjectComment(Base):
    __tablename__ = "project_comment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"))
    body: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=text("CURRENT_TIMESTAMP")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
