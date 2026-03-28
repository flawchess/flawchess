from sqlalchemy import Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Opening(Base):
    __tablename__ = "openings"
    __table_args__ = (
        UniqueConstraint("eco", "name", "pgn", name="uq_openings_eco_name_pgn"),
        Index("ix_openings_eco_name", "eco", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eco: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    ply_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fen: Mapped[str] = mapped_column(String(100), nullable=False)
