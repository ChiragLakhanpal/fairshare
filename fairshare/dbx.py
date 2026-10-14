"""One WorkspaceClient for the whole repo, always as a user, never as a service principal (that is what keeps Genie free on
Free Edition and what makes Unity Catalog row filters apply):

  inside the Databricks App   the token Databricks forwards for the signed-in viewer (user authorization; app/common.py
                              hands it over on every request with set_user_token)
  inside a job task           the compute's own credentials, which are the job's run-as user (FAIRSHARE_BACKEND=spark)
  DATABRICKS_TOKEN set        a personal access token
  otherwise                   OAuth as you through the system browser (auth_type external-browser), cached by the SDK in
                              ~/.databricks/token-cache.json
"""
import os
from functools import lru_cache

from dotenv import load_dotenv

from fairshare.db import ROOT, backend

load_dotenv(ROOT / ".env")

_user_token = None  # ponytail: one process-wide token is right for the single-viewer demo app; per-viewer means threading it through RunContext


def set_user_token(token):
    global _user_token
    _user_token = (token or "").strip() or None


def user_token():
    return _user_token


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


def workspace_client():
    if _user_token:  # a fresh client per call: the app forwards a new token on every request, construction is free
        from databricks.sdk import WorkspaceClient
        # auth_type is not optional here: the Apps runtime also exports the app's own DATABRICKS_CLIENT_ID and
        # DATABRICKS_CLIENT_SECRET, and the SDK refuses a config with two methods ("oauth and pat") unless one is named.
        return WorkspaceClient(host=host(), token=_user_token, auth_type="pat")
    return _cached_client()


def header_factory():
    """For databricks-sql-connector: a callable returning the current auth headers, resolved on every request
    (the token the app forwards rotates, so it is read at request time, never baked into the connection)."""
    return lambda: {"Authorization": f"Bearer {_user_token}"} if _user_token else _cached_client().config.authenticate()


def bearer_token() -> str:
    """A bearer token for the OpenAI-compatible model serving endpoint (the user's own, in every case)."""
    if _user_token:
        return _user_token
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
