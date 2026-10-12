"""Tests run offline: local DuckDB, no model, no tracing, whatever .env says."""
import os

os.environ["FAIRSHARE_BACKEND"] = "duckdb"
os.environ["FAIRSHARE_TRACES"] = ""
os.environ["FAIRSHARE_MODEL"] = "none"
