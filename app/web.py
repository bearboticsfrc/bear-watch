from base64 import b64encode

from aiohttp import web

from app.utils import NetworkUser


class BearWeb:
    ROUTES = web.RouteTableDef()
    WEB_BASE = "www/"
    
    
    def __init__(self) -> None:
        self.app = web.Application()
        self.app.add_routes(self.ROUTES)
        
    @ROUTES.get("/")
    async def get_index(request: web.Request) -> None:
        return web.FileResponse(BearWeb.WEB_BASE + "html/index.html")

    @ROUTES.get("/favicon.ico")
    async def get_favicon(request: web.Request) -> None:
        return web.FileResponse(BearWeb.WEB_BASE + "images/bearbotics.png")

    @ROUTES.get("/mac")
    async def get_mac(request: web.Request) -> None:
        return web.FileResponse(BearWeb.WEB_BASE + "html/mac.html")

    @ROUTES.post("/user")
    async def post_user(request: web.Request) -> None:
        form = await request.post()

        # A user id isn't needed in this configuration, but I'm keeping it for future purposes
        user = NetworkUser(
                user_id=b64encode(form["username"].encode()).decode(),
                name=form["username"], 
                role=form["role"], 
                mac=form["mac"].replace("-", ":").upper())
        
        await request.app["watcher"].create(user)

        return web.FileResponse(BearWeb.WEB_BASE + "html/success.html")
    
    @ROUTES.get("/user")
    async def get_user(request: web.Request) -> None:
        data = {"current": request.app["tracker"].logged_in_users, 
                "known": request.app["tracker"].all_users}

        return web.json_response(data)
    
    @ROUTES.get("/users")
    async def get_users(request: web.Request) -> None:
        return web.FileResponse(BearWeb.WEB_BASE + "html/users.html")
    
    def start(self, *, startup_hook = None, cleanup_hook = None) -> None:
        self.app.on_startup.append(startup_hook)
        self.app.on_cleanup.append(cleanup_hook)

        self.app.router.add_static("/www", "www")

        web.run_app(self.app, host="0.0.0.0", port=80)