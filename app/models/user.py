"""User model for FastAPI-Users with integer primary key and OAuth accounts."""

from typing import List

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(  # noqa: F821
        "OAuthAccount", lazy="joined"
    )
