from __future__ import annotations

import asyncio
import os
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from re import compile

import asqlite

from config import FORCE_LOGOUT_HOUR, PRINT_DELAY


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

@dataclass
class User:
    user_id: int
    name: str
    login_time: float

    def from_row(row: asqlite.Row) -> User:
        return User(row["user_id"],  row["username"], row["login_time"])

class BearWatch:
    _ID_REGEX = compile(r"^\d{10}$")

    def __init__(self, connection: asqlite.Connection) -> None:
        self.connection: asqlite.Connection = connection
        self.task: asyncio.Task
        self.current_users: dict[str, datetime]

    async def __aenter__(self) -> BearWatch:
        async with self.connection.cursor() as cursor:
            with open("setup.sql") as fp:
                await cursor.executescript(fp.read())

            await self.connection.commit()
            await cursor.execute(
                "SELECT * FROM logins, users WHERE logins.user_id = users.user_id AND logout_time IS NULL;")
            
            current_users = await cursor.fetchall()

        self.current_users = {str(row["user_id"]): User.from_row(row) for row in current_users}
        self.task = asyncio.create_task(self.logout_task(), name="Bear-Watch Force Logout")

        return self

    async def __aexit__(self, *_) -> None:
        self.task.cancel()

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

        if self.current_users:
            print(
                "\n".join(f"{user.name} ({user.user_id}) - " \
                          f"{datetime.fromtimestamp(user.login_time).strftime('%I:%M %p')}" 
                          for _, user in self.current_users.items()),
                end="\n" * 2)

    def _compute_timedelta(self) -> float:
        dt = datetime.now().replace(hour=FORCE_LOGOUT_HOUR, minute=0, second=0)

        if datetime.now().hour >= FORCE_LOGOUT_HOUR:
            dt += datetime.timedelta(days=1)

        return (dt - datetime.now()).total_seconds()

    async def logout_task(self) -> None:
        while True:
            await asyncio.sleep(self._compute_timedelta())
            await self.logout("*")

    async def get_username(self, user_id: str) -> str | None:
        async with self.connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE user_id = ?", user_id)
            row = await cursor.fetchone()

            return row["username"] if row else None

    async def create(self, user_id: str, *, first: bool = True) -> None:
        if first:
            print("Unknown user ID! Creating new user...\n")
        
        name = input("Enter user's name: ")

        while (role := input("Enter user's role (mentor, student, other): ")):
            if role.casefold() in ("mentor", "student", "other"):
                break

        confirm_prompt = f"\nUser ID -> {user_id}\nUser's name -> {name}" \
                         f"\nUser's role -> {role.capitalize()}\n\nConfirm? (Y/N): "

        while (confirm := input(confirm_prompt)):
            if confirm.casefold() in ("n", "no", "y", "yes"):
                break
            
        if confirm.casefold() in ("n", "no"):
            print()
            return await self.create(user_id, first=False)

        async with self.connection.cursor() as cursor:
            await cursor.execute("INSERT INTO users VALUES(?, ?, ?);", user_id, name, role)
            await self.connection.commit()

        print(f"\nWelcome, {name}! Please re-enter your ID...")

    async def logout(self, user_id: str) -> None:
        if user_id == "*":
            statement = ("UPDATE logins SET logout_time = ? WHERE logout_time IS NULL;", time.time())
        else:
            statement = ("""UPDATE logins
                            SET logout_time = ?
                            WHERE login_id = (
                                SELECT MAX(login_id)
                                FROM logins
                                WHERE user_id = ? AND logout_time IS NULL
                            );""", (time.time(), user_id))

        async with self.connection.cursor() as cursor:
            await cursor.execute(*statement)
            await self.connection.commit()

        self.current_users.pop(user_id)

    async def login(self, user_id: str) -> str:
        if not self._ID_REGEX.match(user_id):
            raise InvalidUser

        async with self.connection.cursor() as cursor:
            username = await self.get_username(user_id)

            if not username:
                raise UnknownUser
            
            await cursor.execute(
                "SELECT * FROM logins WHERE user_id = ? AND logout_time IS NULL;", user_id)
            login = await cursor.fetchone()
            
            if login is not None:
                raise LoggedInUser(username=username)
            else:
                user = User(user_id, username, time.time())

            await cursor.execute(
                "INSERT INTO logins (user_id, login_time) VALUES(?, ?);", user.user_id, user.login_time)
            await self.connection.commit()

        self.current_users[user_id] = user

        return username

    async def run(self) -> None:
        while True:
            self._clear_screen()

            try:
                user_id = input("Enter ID: ")
            except EOFError:
                return

            if not user_id: 
                continue
            else:
                print()

            try:
                username = await self.login(user_id)
            except InvalidUser:
                print("Invalid ID!")
            except UnknownUser:
                await self.create(user_id)
            except LoggedInUser as exc:
                await self.logout(user_id)
                print(f"Goodbyte, {exc.username}!")
            except Exception as exc:
                with open("traceback.txt", "w") as fp:
                    traceback.print_exception(exc, file=fp)
                raise
            else:
                print(f"Welcome, {username}!")

            await asyncio.sleep(PRINT_DELAY)

async def main() -> None:
    async with asqlite.connect("users.db") as connection, BearWatch(connection=connection) as watcher:
        await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())