from dataclasses import dataclass
@dataclass(frozen=True)
class AdminUser:
    username: str = "admin"
    email: str = "admin@example.com"
    password: str = "admin"
    is_admin: int = 1