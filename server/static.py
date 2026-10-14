"""The React build (web/dist) behind the API: hashed assets, then an SPA fallback for every other path."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fairshare.db import ROOT

DIST = ROOT / "web" / "dist"


def mount(app: FastAPI) -> None:
    assets = DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path == "api" or path.startswith("api/"):
            return JSONResponse({"code": "not_found", "message": "No such API route."}, status_code=404)
        index = DIST / "index.html"
        if not index.is_file():
            return JSONResponse({"code": "no_web_build", "message": "The web app has not been built yet. Run npm run build in web/."}, status_code=503)
        if path:
            target = (DIST / path).resolve()
            if target.is_file() and DIST.resolve() in target.parents:
                return FileResponse(target)
        return FileResponse(index, headers={"Cache-Control": "no-store"})
