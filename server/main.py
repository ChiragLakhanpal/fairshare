"""python -m server.main  (or: uvicorn server.main:app). One worker; the App runtime sets DATABRICKS_APP_PORT."""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from server import api, static


@asynccontextmanager
async def lifespan(app: FastAPI):
    # a Genie wait holds a thread for up to 150 s; the default pool on a small box is a handful of threads
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=16, thread_name_prefix="fairshare"))
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="fairshare", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        body = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
        return JSONResponse(body, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({"code": "invalid", "message": "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors())}, status_code=422)

    app.include_router(api.router, prefix="/api")
    static.mount(app)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=int(os.environ.get("DATABRICKS_APP_PORT", "8000")), workers=1)
