"""Traces for every answer, in MLflow on the Databricks workspace (or a local MLflow server).

Two mechanisms, both in MLflow:
  1. mlflow.openai.autolog() captures every model call the Agent Framework client makes (it uses the openai package).
  2. @mlflow.trace spans around the harness entry point and each tool, so a trace reads: ask -> model -> tool -> model -> verify.
Agent Framework also emits OpenTelemetry GenAI spans; MLflow has no autolog for the framework itself (checked Oct 11, 2026),
and the OTLP ingest path needs a Unity Catalog trace table, so the OpenAI autolog plus explicit spans is the lighter route.

FAIRSHARE_TRACES=databricks   experiment /Users/<you>/fairshare on the workspace (OAuth or PAT from .env)
FAIRSHARE_TRACES=local        http://127.0.0.1:5000 (run `mlflow server --port 5000` first)
unset                         no tracing, nothing configured (tests, offline runs)
"""
import os

_done = False
_experiment_url = None


def setup() -> bool:
    global _done, _experiment_url
    if _done:
        return True
    mode = os.environ.get("FAIRSHARE_TRACES", "").lower()
    if mode not in ("databricks", "local"):
        return False
    import mlflow
    if mode == "databricks":
        from fairshare.dbx import workspace_client
        w = workspace_client()
        os.environ.setdefault("DATABRICKS_HOST", w.config.host)
        if not os.environ.get("DATABRICKS_TOKEN"):
            os.environ["DATABRICKS_TOKEN"] = w.config.authenticate()["Authorization"].split(" ", 1)[1]  # OAuth access token for this process
        mlflow.set_tracking_uri("databricks")
        name = f"/Users/{w.current_user.me().user_name}/fairshare"
        exp = mlflow.set_experiment(name)
        _experiment_url = f"{w.config.host}/ml/experiments/{exp.experiment_id}?compareRunsMode=TRACES"
        os.environ.setdefault("MLFLOW_TRACES_URL", _experiment_url)
    else:
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
        mlflow.set_experiment("fairshare")
    mlflow.openai.autolog()
    _done = True
    return True


def span(name: str):
    """Decorator: an MLflow span when tracing is on, a no-op otherwise."""
    def deco(fn):
        import mlflow
        return mlflow.trace(name=name)(fn)
    return deco


def experiment_url():
    return _experiment_url or os.environ.get("MLFLOW_TRACES_URL")
