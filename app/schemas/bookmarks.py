"""Pydantic v2 schemas for bookmark CRUD operations."""

import json

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator


class BookmarkCreate(BaseModel):
    """Request body for creating a bookmark."""

    label: str
    target_hash: int  # JavaScript sends as decimal string; coerced by validator

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        """Accept string target_hash from JavaScript frontend.

        JavaScript BigInt cannot be safely represented as a JSON number
        (IEEE-754 double loses precision for values > 2^53). The frontend
        sends the hash as a decimal string; this validator converts it to int.
        """
        if isinstance(v, str):
            return int(v)
        return v

    fen: str
    moves: list[str]
    color: str | None = None
    match_side: str = "full"
    is_flipped: bool = False


class BookmarkUpdate(BaseModel):
    """Request body for updating a bookmark (all fields optional)."""

    label: str | None = None
    sort_order: int | None = None


class BookmarkReorderRequest(BaseModel):
    """Request body for bulk reorder: ordered list of bookmark IDs."""

    ids: list[int]


class BookmarkResponse(BaseModel):
    """Response schema for a single bookmark."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    target_hash: str  # returned as string to avoid JS precision loss

    @field_serializer("target_hash")
    def serialize_target_hash(self, v: int) -> str:
        return str(v)

    fen: str
    moves: list[str]  # deserialized from JSON string stored in DB
    color: str | None
    match_side: str
    is_flipped: bool
    sort_order: int

    @model_validator(mode="before")
    @classmethod
    def deserialize_moves(cls, data: object) -> object:
        """Deserialize moves from JSON string (ORM) or pass through list (dict input)."""
        if hasattr(data, "moves"):
            # ORM object — deserialize moves from JSON string
            raw = data.moves
            if isinstance(raw, str):
                # Return a dict-like object by extracting attributes
                return {
                    "id": data.id,
                    "label": data.label,
                    "target_hash": str(data.target_hash),
                    "fen": data.fen,
                    "moves": json.loads(raw),
                    "color": data.color,
                    "match_side": data.match_side,
                    "is_flipped": data.is_flipped,
                    "sort_order": data.sort_order,
                }
        if isinstance(data, dict) and "moves" in data:
            if isinstance(data["moves"], str):
                data = dict(data)
                data["moves"] = json.loads(data["moves"])
        return data
