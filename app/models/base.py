import datetime

from sqlalchemy import BIGINT, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        int: BIGINT,
        datetime.datetime: DateTime(timezone=True),
    }
