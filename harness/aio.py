"""One event loop for the process. asyncio.run() makes a fresh loop per call and the OpenAI async client keeps
connections bound to the loop it was created on; the second call then fails with "Event loop is closed"."""
import asyncio
import threading

_loop = None
_lock = threading.Lock()


def run(coro):
    global _loop
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
        return _loop.run_until_complete(coro)
