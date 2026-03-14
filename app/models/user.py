"""User model for FastAPI-Users with integer primary key and OAuth accounts."""

from typing import List

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Platform usernames (auto-saved on import, user-editable via profile)
    chess_com_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lichess_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(  # noqa: F821
        "OAuthAccount", lazy="joined"
    )
