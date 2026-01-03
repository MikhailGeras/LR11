from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    password: str
    is_admin: bool = False

class UserLogin(BaseModel):
    email: str
    password: str