"""Draft briefs between "write" and "approve", in memory. ponytail: one process, two-hour TTL, fifty at most;
a table if drafts ever need to survive a restart."""
import threading
import time

TTL_S = 2 * 3600
MAX = 50
_items: dict[str, dict] = {}
_lock = threading.Lock()


def put(res: dict, writer: str) -> None:
    with _lock:
        now = time.time()
        for k in [k for k, v in _items.items() if v["expires"] < now]:
            _items.pop(k)
        while len(_items) >= MAX:
            _items.pop(next(iter(_items)))
        _items[res["run_id"]] = {"expires": now + TTL_S, "res": res, "writer": writer, "status": "draft"}


def get(run_id: str) -> dict | None:
    with _lock:
        item = _items.get(run_id)
        if item and item["expires"] < time.time():
            _items.pop(run_id)
            return None
        return item


def approve(run_id: str) -> None:
    with _lock:
        if run_id in _items:
            _items[run_id]["status"] = "approved"
