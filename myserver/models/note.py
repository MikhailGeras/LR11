from pydantic import BaseModel
from typing import Optional

class Note(BaseModel):
    id: Optional[int] = None
    title: str
    content: Optional[str] = None
    user_id: int
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    tags: Optional[str] = None