"""Pydantic v2 schemas for the import API endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class ImportRequest(BaseModel):
    platform: Literal["chess.com", "lichess"]
    username: str = Field(min_length=1, max_length=100)


class ImportStartedResponse(BaseModel):
    job_id: str
    status: str


class ImportStatusResponse(BaseModel):
    job_id: str
    platform: str
    username: str
    status: str
    games_fetched: int
    games_imported: int
    error: str | None = None
    other_importers: int = 0  # Count of other users importing from same platform (D-23)

    @classmethod
    def from_dict(cls, data: dict) -> "ImportStatusResponse":
        return cls(
            job_id=data["job_id"],
            platform=data["platform"],
            username=data["username"],
            status=data["status"],
            games_fetched=data.get("games_fetched", 0),
            games_imported=data.get("games_imported", 0),
            error=data.get("error") or data.get("error_message"),
        )


class DeleteGamesResponse(BaseModel):
    """Response for DELETE /imports/games."""

    deleted_count: int
