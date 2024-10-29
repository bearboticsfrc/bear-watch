from csv import writer
import dataclasses
from base64 import b64encode
from io import StringIO
from typing import TYPE_CHECKING

from aiohttp import web

from app.models import NetworkUser
from config import SCAN_INTERVAL, SCAN_TIMEOUT

if TYPE_CHECKING:
    from app.watcher import Watcher


class Web:
    """
    Handles web application routes and responses using the aiohttp framework.

    Sets up routes for serving HTML pages, processing user data, and returning
    user information in JSON format.
    """

    ROUTES = web.RouteTableDef()
    WEB_BASE = "www/"

    def __init__(self) -> None:
        """
        Initializes the Web application and adds routes.
        """
        self.app = web.Application()
        self.app.add_routes(self.ROUTES)

    @ROUTES.get("/")
    async def get_index(request: web.Request) -> None:
        """
        Serves the index HTML page.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: The index HTML page.
        """
        return web.FileResponse(Web.WEB_BASE + "html/index.html")

    @ROUTES.get("/favicon.ico")
    async def get_favicon(request: web.Request) -> None:
        """
        Serves the favicon image.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: The favicon image.
        """
        return web.FileResponse(Web.WEB_BASE + "images/bearbotics.png")

    @ROUTES.get("/mac")
    async def get_mac(request: web.Request) -> None:
        """
        Serves the MAC address input HTML page.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: The MAC address input HTML page.
        """
        return web.FileResponse(Web.WEB_BASE + "html/mac.html")

    @ROUTES.post("/user")
    async def post_user(request: web.Request) -> None:
        """
        Processes user creation from a form submission.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: A success HTML page.
        """
        form = await request.post()

        id = b64encode(form["name"].encode()).decode()
        name = form["name"]
        role = form["role"].capitalize()
        mac = form["mac"].replace("-", ":").upper()

        # Create a NetworkUser object from the submitted form data.
        user = NetworkUser(
            id=id,
            name=name,
            role=role,
            mac=mac,
        )

        watcher: Watcher = request.app["watcher"]
        await watcher.create_user(user=user)

        return web.FileResponse(Web.WEB_BASE + "html/success.html")

    @ROUTES.get("/user")
    async def get_user(request: web.Request) -> None:
        """
        Returns a JSON response containing all users.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.json_response: A JSON response with user data.
        """
        watcher: Watcher = request.app["watcher"]
        data = dict(
            users=[dataclasses.asdict(user) for user in watcher.get_user("*").values()]
        )

        return web.json_response(data)

    @ROUTES.get("/users")
    async def get_users(request: web.Request) -> None:
        """
        Serves the users HTML page.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: The users HTML page.
        """
        return web.FileResponse(Web.WEB_BASE + "html/users.html")

    @ROUTES.get("/config")
    async def get_config(request: web.Request) -> None:
        """
        Returns a JSON response of the current configuration for the application.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: A JSON response of the configuration data.
        """
        configuration = dict(refresh_interval=SCAN_INTERVAL + SCAN_TIMEOUT)

        return web.json_response(configuration)

    @ROUTES.get("/users/csv")
    async def get_config(request: web.Request) -> None:
        """
        Returns a JSON response of the current configuration for the application.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: A JSON response of the configuration data.
        """
        watcher: Watcher = request.app["watcher"]
        hours = await watcher.get_total_hours()

        output = StringIO()
        csv_writer = writer(output)
        csv_writer.writerow(("Name", "Role", "Total Hours"))
        csv_writer.writerows(hours)
        output.seek(0)

        return web.Response(
            body=output.getvalue(),
            content_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=bearbotics-hours.csv"
            },
        )

    def start(self, *, startup_hook=None, cleanup_hook=None) -> None:
        """
        Starts the web application.

        Args:
            startup_hook (callable, optional): A callable to be executed on startup.
            cleanup_hook (callable, optional): A callable to be executed on cleanup.
        """
        self.app.on_startup.append(startup_hook)
        self.app.on_cleanup.append(cleanup_hook)

        self.app.router.add_static("/www", "www")

        web.run_app(self.app, port=80, access_log=None)
