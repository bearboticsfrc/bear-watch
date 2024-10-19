from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from config import DEBOUNCE_SECONDS

if TYPE_CHECKING:
    from asqlite import Row


class UserRole(StrEnum):
    """Enumeration for user roles."""

    STUDENT = "Student"
    MENTOR = "Mentor"
    OTHER = "Other"


@dataclass(unsafe_hash=True)
class NetworkUser:
    """
    Represents a user on the network.

    Attributes:
        user_id (str): Unique identifier for the user.
        name (str): Name of the user.
        role (UserRole): Role of the user (Student, Mentor, Other).
        mac (str): MAC address of the user's device.
        last_seen (float): Timestamp of the last time the user was seen.
        logged_in (bool): Indicates if the user is currently logged in.
    """

    user_id: str
    name: str
    role: UserRole
    mac: str
    last_seen: float = None
    logged_in: bool = False

    def set_last_seen(self, time: float) -> None:
        """Updates the last seen timestamp."""
        self.last_seen = time

    def set_logged_in(self, logged_in: bool) -> None:
        """Sets the logged-in status of the user."""
        self.logged_in = logged_in

    def is_inactive(self) -> bool:
        """
        Checks if the user is inactive.

        A user is considered inactive if they are logged in and the time
        since their last seen exceeds the debounce threshold.

        Returns:
            bool: True if the user is inactive, False otherwise.
        """
        return self.logged_in and (time.time() - self.last_seen) > DEBOUNCE_SECONDS

    @classmethod
    def from_row(cls, row: Row) -> NetworkUser:
        """
        Creates a NetworkUser instance from a database row.

        Args:
            row (Row): A database row containing user information.

        Returns:
            NetworkUser: An instance of the NetworkUser class.
        """
        return cls(
            user_id=row["user_id"],
            name=row["username"],
            role=UserRole(row["role"]),
            mac=row["mac"],
            last_seen=row["last_seen"],
            logged_in=bool(row["is_logged_in"]),
        )
