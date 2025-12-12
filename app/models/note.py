from pydantic import BaseModel

class Note(BaseModel):
    id: int
    title: str
    content: str
    owner_id: int
    date_created: str
    date_modified: str
    tags: list[str]