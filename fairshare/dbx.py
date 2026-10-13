"""One WorkspaceClient for the whole repo, always as a user, never as a service principal (that is what keeps Genie free on
Free Edition and what makes Unity Catalog row filters apply):

  inside the Databricks App   the token Databricks forwards for the signed-in viewer (user authorization; app/common.py
                              hands it over on every request with set_user_token)
  DATABRICKS_TOKEN set        a personal access token
  otherwise                   OAuth as you through the system browser (auth_type external-browser), cached by the SDK in
                              ~/.databricks/token-cache.json
"""
import os
from functools import lru_cache

from dotenv import load_dotenv

from fairshare.db import ROOT

load_dotenv(ROOT / ".env")

_user_token = None  # ponytail: one process-wide token is right for the single-viewer demo app; per-viewer means threading it through RunContext


def set_user_token(token):
    global _user_token
    _user_token = (token or "").strip() or None


def user_token():
    return _user_token


def host() -> str:
    h = os.environ["DATABRICKS_HOST"].rstrip("/")
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
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if token and not token.startswith("FILL"):
        return WorkspaceClient(host=host(), token=token)
    os.environ.pop("DATABRICKS_TOKEN", None)
    return WorkspaceClient(host=host(), auth_type="external-browser")


def workspace_client():
    if _user_token:  # a fresh client per call: the app forwards a new token on every request, construction is free
        from databricks.sdk import WorkspaceClient
        return WorkspaceClient(host=host(), token=_user_token)
    return _cached_client()


def header_factory():
    """For databricks-sql-connector: a callable returning the current auth headers, resolved on every request."""
    return lambda: workspace_client().config.authenticate()


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
