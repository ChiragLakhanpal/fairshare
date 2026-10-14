"""Who is asking. Inside the Databricks App the runtime forwards the signed-in viewer's token and email on every
request; the token is bound to the request's context so SQL, Genie and the model all run as that person."""
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

from fairshare import dbx


@dataclass
class Viewer:
    token: str | None
    email: str | None
    user: str | None
    inside_app: bool


async def viewer(request: Request) -> Viewer:
    """An async dependency: it runs in the request's own task, so the ContextVar it sets is what the endpoint,
    its threadpool work and the agent task all see."""
    h = request.headers
    token = (h.get("x-forwarded-access-token") or "").strip() or None
    inside_app = bool(os.environ.get("DATABRICKS_CLIENT_ID"))
    if inside_app and not token:
        raise HTTPException(401, {"code": "no_viewer_token", "message": "Open the app through Databricks so it can run as you."})
    dbx.set_user_token(token)
    return Viewer(token=token, email=h.get("x-forwarded-email"), user=h.get("x-forwarded-user"), inside_app=inside_app)
