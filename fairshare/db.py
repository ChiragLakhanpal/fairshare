"""One query function, three backends.

FAIRSHARE_BACKEND=duckdb      local file data/out/fairshare.duckdb, attached as catalog aa_demo (default; works offline)
FAIRSHARE_BACKEND=databricks  a SQL warehouse via databricks-sql-connector, needs DATABRICKS_HOST and DATABRICKS_HTTP_PATH
                              (or DATABRICKS_WAREHOUSE_ID) in the environment or in .env; auth as in fairshare/dbx.py
FAIRSHARE_BACKEND=spark       the Spark session of the Databricks compute this process runs on (a job task, a notebook):
                              no warehouse connection, no token; lakehouse/job_tasks.py sets it

SQL is written once with three-part names (aa_demo.gold.table) and runs on all three. MEASURE() queries are
Databricks only (warehouse or spark); callers check `is_databricks()` before using them.
"""
import os
import threading
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DUCKDB_FILE = ROOT / "data" / "out" / "fairshare.duckdb"
STATE_FILE = ROOT / "data" / "out" / "app_state.duckdb"   # local stand-in for aa_demo.ops.summaries (DuckDB allows one writer per file)

_duck = None                      # the one DuckDB session (queries use a cursor each, so threads can share it)
_conns: dict = {}                 # viewer token -> (warehouse connection, lock); None is the laptop's own connection
_conns_lock = threading.Lock()


def backend() -> str:
    return os.environ.get("FAIRSHARE_BACKEND", "duckdb").lower()


def is_databricks() -> bool:
    return backend() in ("databricks", "spark")


def _spark():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


def _duckdb():
    """Read-only unless FAIRSHARE_WRITE=1 (lakehouse/run.py sets it), so the app, tests and the benchmark can share the file.
    A rebuild needs the app stopped: DuckDB gives a writer exclusive access."""
    global _duck
    if _duck is None:
        import duckdb
        _duck = duckdb.connect()  # in-memory session, the file is attached as the catalog name the SQL uses
        mode = "" if os.environ.get("FAIRSHARE_WRITE") else " (READ_ONLY)"
        _duck.execute(f"ATTACH '{DUCKDB_FILE}' AS aa_demo{mode}")
    return _duck


def _databricks():
    """The warehouse connection for the current identity: one per viewer token (the token is baked in, the connector
    is not documented thread-safe, so each connection carries a lock), one for the laptop. ponytail: at most 8 kept,
    the oldest viewer's is closed; a pool if the app ever has more viewers than that at once."""
    from fairshare.dbx import header_factory, http_path, server_hostname, user_token
    token = user_token()
    with _conns_lock:
        hit = _conns.get(token)
        if hit:
            return hit
        from databricks import sql
        if token:
            kw = {"access_token": token}
        else:
            pat = os.environ.get("DATABRICKS_TOKEN", "").strip()
            kw = {"access_token": pat} if pat and not pat.startswith("FILL") else {"credentials_provider": header_factory}
        conn = sql.connect(server_hostname=server_hostname(), http_path=http_path(), **kw)
        if len(_conns) >= 8:
            old, _ = _conns.pop(next(iter(_conns)))
            try:
                old.close()
            except Exception:
                pass
        _conns[token] = (conn, threading.Lock())
        return _conns[token]


def query(sql: str) -> pd.DataFrame:
    """Run one SELECT and return a DataFrame."""
    if backend() == "spark":
        return _spark().sql(sql).toPandas()
    if is_databricks():
        conn, lock = _databricks()
        with lock, conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    return _duckdb().cursor().execute(sql).df()


def execute(sql: str) -> None:
    """Run one statement with no result. On Databricks this goes through the Statement Execution API (status, errors,
    and a bounded wait) rather than the SQL connector, which blocked without end on DDL on Oct 11, 2026."""
    if backend() == "spark":
        _spark().sql(sql)  # commands run eagerly
        return
    if is_databricks():
        import time
        from fairshare.dbx import warehouse_id, workspace_client
        w = workspace_client()
        r = w.statement_execution.execute_statement(warehouse_id=warehouse_id(), statement=sql, wait_timeout="50s")
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
