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

    @ROUTES.get("/hours")
    async def get_hours(request: web.Request) -> None:
        """
        Serves the total user hours HTML page.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.FileResponse: The total user hours HTML page.
        """
        return web.FileResponse(Web.WEB_BASE + "html/hours.html")

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

        try:
            name = form["name"].strip()
            id = b64encode(name.encode()).decode()
            role = form["role"].capitalize()
            mac = form["mac"].replace("-", ":").upper()
        except KeyError:
            return web.Response(status=400)

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

    @ROUTES.get("/hour")
    async def get_hour(request: web.Request) -> None:
        """
        Returns a JSON response containing all user's total hours.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.json_response: A JSON response with user data.
        """
        watcher: Watcher = request.app["watcher"]
        hours = await watcher.get_total_hours()

        users = dict(
            users=[dict(name=row[0], role=row[1], total_hours=row[2]) for row in hours]
        )

        return web.json_response(data=users)

    @ROUTES.get("/config")
    async def get_config(request: web.Request) -> None:
        """
        Returns a JSON response of the current configuration for the application.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.json_response: A JSON response of the configuration data.
        """
        configuration = dict(refresh_interval=SCAN_INTERVAL + SCAN_TIMEOUT)

        return web.json_response(configuration)

    @ROUTES.get("/hours/csv")
    async def get_hours_csv(request: web.Request) -> None:
        """
        Returns a CSV response containing all user's total hours.

        Args:
            request (web.Request): The incoming request object.

        Returns:
            web.Response: A CSV response with user data.
        """
        watcher: Watcher = request.app["watcher"]
        hours = await watcher.get_total_hours()

        output = StringIO()
        csv = writer(output)
        csv.writerow(("Name", "Role", "Total Hours"))
        csv.writerows(hours)

        output.seek(0)

        return web.Response(
            body=output.getvalue(),
            content_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=bearbotics-hours.csv"
            },
        )
