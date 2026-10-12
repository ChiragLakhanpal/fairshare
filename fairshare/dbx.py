"""One WorkspaceClient for the whole repo. A personal access token when DATABRICKS_TOKEN is set; otherwise OAuth as you
through the system browser (auth_type external-browser), cached by the SDK in ~/.databricks/token-cache.json. Either
way Genie and the warehouse see the user, never a service principal, which is what keeps Genie free on Free Edition."""
import os
from functools import lru_cache

from dotenv import load_dotenv

from fairshare.db import ROOT

load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def workspace_client():
    from databricks.sdk import WorkspaceClient
    host = os.environ["DATABRICKS_HOST"]
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if token and not token.startswith("FILL"):
        return WorkspaceClient(host=host, token=token)
    os.environ.pop("DATABRICKS_TOKEN", None)
    return WorkspaceClient(host=host, auth_type="external-browser")


def header_factory():
    """For databricks-sql-connector: a callable returning the current auth headers (refreshes itself)."""
    return workspace_client().config.authenticate


def warehouse_id() -> str:
    return os.environ["DATABRICKS_HTTP_PATH"].rsplit("/", 1)[-1]


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
