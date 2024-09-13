from __future__ import annotations

from dataclasses import dataclass

import asqlite


class UserException(Exception):
    """Base Exception raised when there is an error during user login."""
    def __init__(self, username: str = "Unknown") -> None:
        super().__init__()
        self.username = username

class InvalidUser(UserException):
    """Exception raised when an invalid user ID is encountered."""

class UnknownUser(UserException):
    """Exception raised when an unknown user is encountered."""

class LoggedInUser(UserException):
    """Exception raised when an already logged in user is encountered."""

class NmapScanError(Exception):
    """Exception raised for errors in the Nmap scan process."""

@dataclass(unsafe_hash=True)
class User:
    user_id: str
    name: str
    role: str
    mac: str

    @classmethod
    def from_row(cls, row: asqlite.Row) -> User:
        return cls(user_id=row["user_id"], name=row["username"], role=row["role"], mac=row["mac"])
    
@dataclass(unsafe_hash=True)
class NetworkUser(User):
    last_seen: float = 0

    def set_last_seen(self, time: float) -> None:
        self.last_seen = time