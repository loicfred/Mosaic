from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Request bodies reject unknown fields and trim strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Page(BaseModel):
    total: int
    page: int
    page_size: int
