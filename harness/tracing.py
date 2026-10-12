"""Traces for every answer. Agent Framework emits OpenTelemetry GenAI spans; there is no MLflow autolog for it
(checked Oct 11, 2026), so spans go out over OTLP/HTTP to wherever OTEL_EXPORTER_OTLP_TRACES_ENDPOINT points:

  Databricks MLflow (the demo):   https://<workspace-host>/api/2.0/otel/v1/traces
                                  OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer%20<PAT>,X-Databricks-UC-Table-Name=aa_demo.ops.traces
                                  (MLflow 3.14+ on the workspace side; the table is created on first write)
  Local MLflow (fallback):        mlflow server --port 5000 ; endpoint http://127.0.0.1:5000/v1/traces
                                  OTEL_EXPORTER_OTLP_HEADERS=x-mlflow-experiment-id=<id>
  Console (debug):                ENABLE_CONSOLE_EXPORTERS=true

Nothing is configured when the endpoint variable is absent, so tests and offline runs stay quiet.
"""
import os

_done = False


def setup() -> bool:
    global _done
    if _done:
        return True
    if not (os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            or os.environ.get("ENABLE_CONSOLE_EXPORTERS")):
        return False
    from agent_framework.observability import configure_otel_providers
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    configure_otel_providers(service_name="fairshare-sales-agent",
                             enable_sensitive_data=os.environ.get("OTEL_SENSITIVE", "true").lower() == "true")
    _done = True
    return True
