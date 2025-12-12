from pydantic import BaseModel
from typing import Optional

class Note(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    owner_id: int
    date_created: str
    date_modified: str
    tags: Optional[list[str]] = None