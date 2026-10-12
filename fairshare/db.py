"""One query function, two backends.

FAIRSHARE_BACKEND=duckdb      local file data/out/fairshare.duckdb, attached as catalog aa_demo (default; works offline)
FAIRSHARE_BACKEND=databricks  a SQL warehouse via databricks-sql-connector, needs DATABRICKS_SERVER_HOSTNAME,
                              DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN in the environment or in .env

SQL is written once with three-part names (aa_demo.gold.table) and runs on both. MEASURE() queries are
Databricks only; callers check `is_databricks()` before using them.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DUCKDB_FILE = ROOT / "data" / "out" / "fairshare.duckdb"
STATE_FILE = ROOT / "data" / "out" / "app_state.duckdb"   # local stand-in for aa_demo.ops.summaries (DuckDB allows one writer per file)

_conn = None


def backend() -> str:
    return os.environ.get("FAIRSHARE_BACKEND", "duckdb").lower()


def is_databricks() -> bool:
    return backend() == "databricks"


def _duckdb():
    """Read-only unless FAIRSHARE_WRITE=1 (lakehouse/run.py sets it), so the app, tests and the benchmark can share the file.
    A rebuild needs the app stopped: DuckDB gives a writer exclusive access."""
    global _conn
    if _conn is None:
        import duckdb
        _conn = duckdb.connect()  # in-memory session, the file is attached as the catalog name the SQL uses
        mode = "" if os.environ.get("FAIRSHARE_WRITE") else " (READ_ONLY)"
        _conn.execute(f"ATTACH '{DUCKDB_FILE}' AS aa_demo{mode}")
    return _conn


def _databricks():
    global _conn
    if _conn is None:
        from databricks import sql
        from fairshare.dbx import header_factory
        token = os.environ.get("DATABRICKS_TOKEN", "").strip()
        kw = {"access_token": token} if token and not token.startswith("FILL") else {"credentials_provider": header_factory}
        _conn = sql.connect(server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"], http_path=os.environ["DATABRICKS_HTTP_PATH"], **kw)
    return _conn


def query(sql: str) -> pd.DataFrame:
    """Run one SELECT and return a DataFrame."""
    if is_databricks():
        with _databricks().cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    return _duckdb().execute(sql).df()


def execute(sql: str) -> None:
    """Run one statement with no result. On Databricks this goes through the Statement Execution API (status, errors,
    and a bounded wait) rather than the SQL connector, which blocked without end on DDL on Oct 11, 2026."""
    if is_databricks():
        import time
        from fairshare.dbx import workspace_client
        w = workspace_client()
        wh = os.environ["DATABRICKS_HTTP_PATH"].rsplit("/", 1)[-1]
        r = w.statement_execution.execute_statement(warehouse_id=wh, statement=sql, wait_timeout="50s")
        while r.status and r.status.state.value in ("PENDING", "RUNNING"):
            time.sleep(2)
            r = w.statement_execution.get_statement(r.statement_id)
        if r.status and r.status.state.value != "SUCCEEDED":
            msg = r.status.error.message if r.status.error else r.status.state.value
            raise RuntimeError(f"{msg}\n-- statement:\n{sql[:400]}")
        return
    _duckdb().execute(sql)


def statements(path: Path):
    """Split a .sql file into statements. Comment lines are dropped first so a ';' in a comment is harmless."""
    text = "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("--"))
    out = []
    for s in text.split(";\n"):
        s = s.strip().rstrip(";").strip()
        if s:
            out.append(s)
    return out


# ---- small mutable state (summary runs and their approval status) ----
SUMMARIES = "aa_demo.ops.summaries"


def state_execute(statements_: list[str]) -> None:
    """Writes to the summaries table. Databricks: the warehouse. DuckDB: a short-lived connection to app_state.duckdb,
    so no process holds a lock on it for longer than the write."""
    if is_databricks():
        for s in statements_:
            execute(s)
        return
    import duckdb
    con = duckdb.connect(str(STATE_FILE))
    try:
        for s in statements_:
            con.execute(s.replace(SUMMARIES, "summaries"))
    finally:
        con.close()


def state_query(sql: str) -> pd.DataFrame:
    if is_databricks():
        return query(sql)
    import duckdb
    if not STATE_FILE.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(STATE_FILE), read_only=True)
    try:
        return con.execute(sql.replace(SUMMARIES, "summaries")).df()
    finally:
        con.close()
