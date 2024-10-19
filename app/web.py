import dataclasses
from base64 import b64encode
from typing import TYPE_CHECKING

from aiohttp import web

from app.models import NetworkUser

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

        # Create a NetworkUser object from the submitted form data.
        user = NetworkUser(
            user_id=b64encode(form["username"].encode()).decode(),
            name=form["username"],
            role=form["role"].capitalize(),
            mac=form["mac"].replace("-", ":").upper(),
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

        web.run_app(self.app, host="0.0.0.0", port=80)
