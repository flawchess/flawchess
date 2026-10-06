import datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy import text as sql_text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "source IN ('floating_button', 'milestone_ask')", name="ck_feedback_source"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)  # length capped in Pydantic, not here
    rating: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )  # 1-5 star rating; bounds enforced in Pydantic; nullable = optional
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    # Which entry point produced this row (SEED-191 #9): the floating button or the
    # milestone feedback ask. TEXT + CHECK per the low-volume domain-column rule.
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        # `text` is shadowed by the column attribute above, hence the sql_text alias.
        server_default=sql_text("'floating_button'"),
        default="floating_button",
    )
