"""The app as a Databricks App: the FastAPI server (server/) over the React build (web/dist), running inside the lakehouse
with the viewer's own permissions. Build the web app first (cd web && npm run build); deploy refuses to sync without it.

  python lakehouse/app_deploy.py create   # once: the app, its resources (warehouse, Genie space, model) and the user-authorization scopes
  python lakehouse/app_deploy.py update   # after changing DATABRICKS_MODEL or the scopes (then deploy)
  python lakehouse/app_deploy.py deploy   # upload the repo (allowlist below) to the workspace and deploy a snapshot; prints the URL
  python lakehouse/app_deploy.py start    # Free Edition stops apps 24 hours after a start or deploy: run this before a demo
  python lakehouse/app_deploy.py status   # compute state, last deployment, URL

Free Edition facts (Oct 13, 2026): 3 apps per account; outbound internet limited to trusted domains, so the model is a
Databricks serving endpoint (DATABRICKS_MODEL), not Foundry; an app's service principal pays for Genie, a user does not,
hence user authorization for everything.
"""
import io
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare.dbx import warehouse_id, workspace_client  # noqa: E402

NAME = "fairshare"
MODEL = os.environ.get("DATABRICKS_MODEL", "databricks-qwen3-next-80b-a3b-instruct")
SCOPES = ["sql", "genie", "model-serving"]
INCLUDE = ["app.yaml", "requirements.txt", "server", "harness", "fairshare", "data/contracts", "web/dist", "app/cache", "evals/results/latest.json"]
LINKS = ["DASHBOARD_URL", "GENIE_SPACE_URL", "JOB_URL", "MLFLOW_TRACES_URL", "FOUNDRY_PROJECT_URL", "REPO_URL", "DATABRICKS_APP_URL"]  # /api/me hands them to the app
# What the app needs, nothing more: the agent-framework metapackage drags in thirty integrations and its install failed in the
# Apps runtime (Oct 13, 2026); mlflow, duckdb and pytest are laptop-only (tracing is off inside the app, the data is the warehouse).
APP_REQUIREMENTS = """fastapi
uvicorn
sse-starlette
databricks-sdk
databricks-sql-connector
pandas
pyarrow
pyyaml
python-dotenv
agent-framework-core>=1.21
agent-framework-openai>=1.16
"""


def files():
    for item in INCLUDE:
        p = ROOT / item
        paths = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
        for q in paths:
            if "__pycache__" in q.parts or q.suffix in (".pyc", ".duckdb", ".parquet") or q.name == "secrets.toml":
                continue
            yield q


def manifest() -> bytes:
    """app.yaml plus the link variables from .env (URLs only, never a key), so Under the hood has them inside the app too."""
    text = (ROOT / "app.yaml").read_text()
    for var in LINKS:
        v = os.environ.get(var, "").strip()
        if v:
            text += f'  - name: {var}\n    value: "{v}"\n'
    return text.encode()


def source_path(w) -> str:
    return f"/Users/{w.current_user.me().user_name}/{NAME}-app"


def sync(w) -> str:
    from databricks.sdk.service.workspace import ImportFormat
    base = source_path(w)
    w.workspace.mkdirs(base)
    seen = set()
    for q in files():
        rel = q.relative_to(ROOT).as_posix()
        folder = f"{base}/{rel}".rsplit("/", 1)[0]
        if folder not in seen:
            w.workspace.mkdirs(folder)
            seen.add(folder)
        content = manifest() if rel == "app.yaml" else APP_REQUIREMENTS.encode() if rel == "requirements.txt" else q.read_bytes()
        w.workspace.upload(f"{base}/{rel}", io.BytesIO(content), format=ImportFormat.AUTO, overwrite=True)
    print(f"synced {len(list(files()))} files to {base}")
    return "/Workspace" + base


def resources():
    from databricks.sdk.service.apps import (AppResource, AppResourceGenieSpace, AppResourceGenieSpaceGenieSpacePermission,
                                             AppResourceServingEndpoint, AppResourceServingEndpointServingEndpointPermission,
                                             AppResourceSqlWarehouse, AppResourceSqlWarehouseSqlWarehousePermission)
    return [
        AppResource(name="warehouse", sql_warehouse=AppResourceSqlWarehouse(id=warehouse_id(), permission=AppResourceSqlWarehouseSqlWarehousePermission.CAN_USE)),
        AppResource(name="genie", genie_space=AppResourceGenieSpace(name=NAME, space_id=os.environ["GENIE_SPACE_ID"], permission=AppResourceGenieSpaceGenieSpacePermission.CAN_RUN)),
        AppResource(name="model", serving_endpoint=AppResourceServingEndpoint(name=MODEL, permission=AppResourceServingEndpointServingEndpointPermission.CAN_QUERY)),
    ]


def create(w):
    from databricks.sdk.service.apps import App
    app = w.apps.create_and_wait(App(name=NAME, description="fairshare: one sales agent, one semantic layer, every number with its query.",
                                     resources=resources(), user_api_scopes=SCOPES), timeout=timedelta(minutes=10))
    print("created", app.name, app.url, app.compute_status.state.value if app.compute_status else "")
    write_env("DATABRICKS_APP_URL", app.url or "")


def update(w):
    """Re-point the resources (a different model, say) and the scopes; deploy afterwards so the env picks them up."""
    from databricks.sdk.service.apps import App
    app = w.apps.update(NAME, App(name=NAME, resources=resources(), user_api_scopes=SCOPES))
    print("updated resources:", [r.name + ":" + (r.serving_endpoint.name if r.serving_endpoint else "") for r in app.resources or []])


def deploy(w):
    from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode
    if not (ROOT / "web" / "dist" / "index.html").exists():
        sys.exit("web/dist/index.html is missing: run `cd web && npm run build` first")
    path = sync(w)
    app = w.apps.get(NAME)
    if not app.compute_status or app.compute_status.state.value != "ACTIVE":
        start(w)  # a stopped app (24-hour stop) refuses a deployment
    while w.apps.get(NAME).pending_deployment is not None:  # a start redeploys the last snapshot first; the API refuses a second deployment meanwhile
        time.sleep(10)
    d = w.apps.deploy_and_wait(NAME, AppDeployment(source_code_path=path, mode=AppDeploymentMode.SNAPSHOT), timeout=timedelta(minutes=20))
    print("deployment", d.status.state.value if d.status else "", (d.status.message if d.status else "")[:400])
    app = w.apps.get(NAME)
    write_env("DATABRICKS_APP_URL", app.url or "")
    print("url", app.url)


def start(w):
    app = w.apps.start_and_wait(NAME, timeout=timedelta(minutes=10))
    print("compute", app.compute_status.state.value if app.compute_status else "", app.url)


def status(w):
    app = w.apps.get(NAME)
    print("compute:", app.compute_status.state.value if app.compute_status else "?", "|", app.compute_status.message if app.compute_status else "")
    print("app:", app.app_status.state.value if app.app_status else "?", "|", app.app_status.message if app.app_status else "")
    d = app.active_deployment or app.pending_deployment
    print("deployment:", d.status.state.value if d and d.status else "none", "|", (d.status.message if d and d.status else "")[:300])
    print("scopes:", app.effective_user_api_scopes, "| url:", app.url)


def write_env(key: str, value: str):
    import re
    p = ROOT / ".env"
    s = p.read_text()
    s, n = re.subn(rf"^{key}=.*$", f"{key}={value}", s, flags=re.M)
    p.write_text(s if n else s.rstrip("\n") + f"\n{key}={value}\n")
    os.environ[key] = value


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    w = workspace_client()
    {"create": create, "update": update, "deploy": deploy, "start": start, "status": status, "sync": sync}.get(cmd, lambda w: sys.exit(__doc__))(w)
