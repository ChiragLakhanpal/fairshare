"""One WorkspaceClient per identity, always as a user, never as a service principal (that is what keeps Genie free on
Free Edition and what makes Unity Catalog row filters apply):

  inside the Databricks App   the token Databricks forwards for the signed-in viewer (user authorization; the server binds
                              it per request with bind()/set_user_token, so two viewers in flight never share one)
  inside a job task           the compute's own credentials, which are the job's run-as user (FAIRSHARE_BACKEND=spark)
  DATABRICKS_TOKEN set        a personal access token
  otherwise                   OAuth as you through the system browser (auth_type external-browser), cached by the SDK in
                              ~/.databricks/token-cache.json
"""
import contextlib
import os
from contextvars import ContextVar
from functools import lru_cache

from dotenv import load_dotenv

from fairshare.db import ROOT, backend

load_dotenv(ROOT / ".env")

# The viewer's token for the current request. A ContextVar follows the request through asyncio tasks and
# asyncio.to_thread / starlette's run_in_threadpool (never loop.run_in_executor, which drops the context).
_token: ContextVar = ContextVar("fairshare_user_token", default=None)


def set_user_token(token):
    """Bind a token to the current context; returns the reset token for reset_user_token."""
    return _token.set((token or "").strip() or None)


def reset_user_token(tok) -> None:
    _token.reset(tok)


@contextlib.contextmanager
def bind(token):
    tok = set_user_token(token)
    try:
        yield
    finally:
        _token.reset(tok)


def user_token():
    return _token.get()


def host() -> str:
    h = (_cached_client().config.host if backend() == "spark" else os.environ["DATABRICKS_HOST"]).rstrip("/")  # a job task knows its workspace from the runtime
    return h if "://" in h else f"https://{h}"


def http_path() -> str:
    """DATABRICKS_HTTP_PATH, or the warehouse the app's resource injects as DATABRICKS_WAREHOUSE_ID."""
    return os.environ.get("DATABRICKS_HTTP_PATH") or f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}"


def warehouse_id() -> str:
    return http_path().rsplit("/", 1)[-1]


def server_hostname() -> str:
    return os.environ.get("DATABRICKS_SERVER_HOSTNAME") or host().split("://", 1)[-1]


@lru_cache(maxsize=1)
def _cached_client():
    from databricks.sdk import WorkspaceClient
    if backend() == "spark":  # inside Databricks compute: the runtime's credentials, no configuration
        return WorkspaceClient()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if token and not token.startswith("FILL"):
        return WorkspaceClient(host=host(), token=token)
    os.environ.pop("DATABRICKS_TOKEN", None)
    return WorkspaceClient(host=host(), auth_type="external-browser")


@lru_cache(maxsize=32)
def _client_for(token: str):
    """One client per viewer token: the SDK probes the workspace on every construction, so building one per call
    would cost a round trip each time. auth_type is not optional: the Apps runtime also exports the app's own
    DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, and the SDK refuses a config with two methods unless one is named."""
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient(host=host(), token=token, auth_type="pat")


def workspace_client():
    t = user_token()
    return _client_for(t) if t else _cached_client()


def header_factory():
    """For databricks-sql-connector on the laptop: a callable returning the current auth headers, resolved on every
    request (OAuth tokens rotate, so they are read at request time, never baked into the connection)."""
    return lambda: {"Authorization": f"Bearer {user_token()}"} if user_token() else _cached_client().config.authenticate()


def bearer_token() -> str:
    """A bearer token for the OpenAI-compatible model serving endpoint (the user's own, in every case). The model client
    takes this function, not its value, so one client serves every viewer."""
    t = user_token()
    if t:
        return t
    return _cached_client().config.authenticate()["Authorization"].split(" ", 1)[1]


def warm_warehouse(timeout_s: int = 90) -> str:
    """Start the SQL warehouse if it is stopped and wait until it runs. Free Edition auto-stops after 10 minutes and
    the setting cannot be changed there; an explicit start takes about 8 seconds."""
    from datetime import timedelta
    w = workspace_client()
    wid = warehouse_id()
    state = w.warehouses.get(wid).state
    if state is not None and state.value == "RUNNING":
        return "RUNNING"
    w.warehouses.start_and_wait(wid, timeout=timedelta(seconds=timeout_s))
    return w.warehouses.get(wid).state.value
