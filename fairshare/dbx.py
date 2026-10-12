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
