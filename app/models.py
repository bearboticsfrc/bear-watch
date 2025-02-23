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


@dataclass
class NetworkUser:
    """
    Represents a user on the network.

    Attributes:
        id (str): Unique identifier for the user.
        name (str): Name of the user.
        role (UserRole): Role of the user (Student, Mentor, Other).
        mac (str): MAC address of the user's device.
        first_seen (float): Timestamp of the first time the user was seen.
        last_seen (float): Timestamp of the last time the user was seen.
        logged_in (bool): Indicates if the user is currently logged in.
    """

    id: str
    name: str
    role: UserRole
    mac: str
    first_seen: float = None
    last_seen: float = None
    logged_in: bool = False

    def set_last_seen(self, time: float) -> None:
        """Updates the last seen timestamp."""
        if self.first_seen is None:
            self.first_seen = time

        self.last_seen = time

    def set_logged_in(self, logged_in: bool) -> None:
        """Sets the logged-in status of the user."""
        if logged_in is False:
            self.first_seen = None

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
            id=row["id"],
            name=row["name"],
            role=UserRole(row["role"]),
            mac=row["mac"],
            first_seen=row["last_seen"],
            last_seen=row["last_seen"],
            logged_in=bool(row["is_logged_in"]),
        )
