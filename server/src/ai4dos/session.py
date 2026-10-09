from dataclasses import dataclass, field
from enum import Enum
import secrets


class Role(str, Enum):
    ROLE_USER = "user"
    ROLE_AI = "ai"
    ROLE_SYSTEM = "system"


@dataclass(frozen=True)
class Message:
    role: Role
    text: str


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: secrets.token_hex(6))
    history: list = field(default_factory=list)
    max_exchanges: int = 10

    def record(self, user_text, ai_text):
        self.history.extend([Message(Role.ROLE_USER, user_text), Message(Role.ROLE_AI, ai_text)])
        del self.history[:max(0, len(self.history) - self.max_exchanges * 2)]

    def request(self, user_text):
        return [*self.history, Message(Role.ROLE_USER, user_text)]
