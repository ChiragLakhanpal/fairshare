"""One event loop for the process. asyncio.run() makes a fresh loop per call and the OpenAI async client keeps
connections bound to the loop it was created on; the second call then fails with "Event loop is closed".

Inside a kernel (a serverless job task, a notebook) a loop is already running on the calling thread, and
run_until_complete refuses ("Cannot run the event loop while another loop is running"); there, ours runs on its own
thread and calls are handed over with run_coroutine_threadsafe. The fact pool is a module global, so nothing minds."""
import asyncio
import threading

_loop = None
_thread = None
_lock = threading.Lock()


def run(coro):
    global _loop, _thread
    with _lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
    try:
        asyncio.get_running_loop()
    except RuntimeError:  # the usual case: no loop on this thread, run ours here
        return _loop.run_until_complete(coro)
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_loop.run_forever, name="fairshare-aio", daemon=True)
            _thread.start()
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()
