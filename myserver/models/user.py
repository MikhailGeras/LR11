from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    email: str
    password: str
    is_admin: bool = False

class UserLogin(BaseModel):
    email: str
    password: str