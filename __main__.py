from __future__ import annotations

import asyncio
import os
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
    login_time: datetime

    def from_row(row: asqlite.Row) -> User:
        return User(row["user_id"], 
                    row["username"], 
                    datetime.fromtimestamp(int(row["login_time"])))

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
        self.task = asyncio.create_task(self.logout_task())

        return self

    async def __aexit__(self, *_) -> None:
        self.task.cancel()

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

        if self.current_users:
            print(
                "\n".join(f"{user.name} - {user.login_time.strftime('%I:%M %p')}" 
                          for _, user in self.current_users.items()),
                end="\n" * 2)

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


    async def get_username(self, user_id: str) -> None:
        async with self.connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE user_id = ?", user_id)
            row = await cursor.fetchone()

            return row["username"] if row else None

    async def logout(self, user_id: str) -> None:
        if user_id == "*":
            statement = ("""UPDATE logins SET logout_time = strftime('%s', 'now') WHERE logout_time IS NULL;""",)
        else:
            statement = ("""UPDATE logins
                            SET logout_time = strftime('%s', 'now')
                            WHERE login_id = (
                                SELECT MAX(login_id)
                                FROM logins
                                WHERE user_id = ? AND logout_time IS NULL
                            );""", user_id)

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
                """SELECT * FROM logins WHERE user_id = ? AND logout_time IS NULL;""", user_id)
            login = await cursor.fetchone()
            
            if login is not None:
                raise LoggedInUser(username=username)

            await cursor.execute("INSERT INTO logins (user_id) VALUES(?);", user_id)
            await cursor.execute(
                "SELECT * FROM logins, users WHERE users.user_id = logins.user_id AND users.user_id = (?);",user_id)

            await self.connection.commit()
            user = await cursor.fetchone()

        self.current_users[user_id] = User.from_row(user)
        
        return username

    def _compute_timedelta(self, dt: datetime) -> float:
        if dt.tzinfo is None:
            dt = dt.astimezone()

        now = datetime.now(timezone.utc)
        
        return max((dt - now).total_seconds(), 0)

    async def logout_task(self) -> None:
        while True:
            when = datetime.now().replace(hour=FORCE_LOGOUT_HOUR, minute=0, second=0)

            if datetime.now().hour >= FORCE_LOGOUT_HOUR:
                when += datetime.timedelta(days=1)

            await asyncio.sleep(self._compute_timedelta(when))
            await self.logout("*")

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
            else:
                print(f"Welcome, {username}!")

            await asyncio.sleep(PRINT_DELAY)

async def main() -> None:
    async with asqlite.connect("users.db") as connection, BearWatch(connection=connection) as watcher:
        await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())