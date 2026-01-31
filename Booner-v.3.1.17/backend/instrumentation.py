import asyncio
import time
import logging
import faulthandler
import pathlib
import subprocess
import os
from collections import deque

LOG = logging.getLogger("instrumentation")
PATH = pathlib.Path("logs")
PATH.mkdir(parents=True, exist_ok=True)

# keep last N drifts
_DRIFTS = deque(maxlen=500)
_MONITOR_TASK = None

async def monitor_event_loop(threshold: float = 0.2, interval: float = 0.1):
    """Continuously measure event loop drift and record stack traces when blocked."""
    LOG.info("instrumentation: starting event loop monitor (threshold=%.3fs interval=%.3fs)", threshold, interval)
    while True:
        t = time.perf_counter()
        await asyncio.sleep(interval)
        drift = time.perf_counter() - t - interval
        _DRIFTS.append(drift)
        if drift > threshold:
            LOG.warning("Event loop blocked: %.3fs", drift)
            ts = time.strftime('%Y%m%dT%H%M%SZ')
            fname = PATH / f"loop_block_{ts}.txt"
            with open(fname, "a") as fh:
                fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} blocked {drift:.3f}s\n")
                faulthandler.dump_traceback(file=fh, all_threads=True)


def get_loop_stats():
    if not _DRIFTS:
        return {"samples": 0, "max": 0.0, "avg": 0.0}
    vals = list(_DRIFTS)
    return {"samples": len(vals), "max": max(vals), "avg": (sum(vals) / len(vals))}


# Timing middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class TimingMiddleware(BaseHTTPMiddleware):
    """Log slow requests."""
    def __init__(self, app, threshold: float = 0.5):
        super().__init__(app)
        self.threshold = threshold

    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        dur = time.perf_counter() - t0
        if dur > self.threshold:
            LOG.warning("Slow request %s %s: %.3fs", request.method, request.url.path, dur)
            with open(PATH / "slow_requests.log", "a") as fh:
                fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} {request.method} {request.url.path} {dur:.3f}\n")
        return response


def get_fd_count():
    """Return number of open fds for current process (uses lsof)."""
    try:
        out = subprocess.check_output(["lsof", "-p", str(os.getpid())], stderr=subprocess.DEVNULL, text=True)
        # lsof header + lines
        return len(out.splitlines())
    except Exception:
        try:
            # fallback: count /dev/fd on macOS
            fd_dir = f"/dev/fd"
            return len(os.listdir(fd_dir))
        except Exception:
            return -1


# helper to start monitor as background task
def start_monitor(loop=None):
    global _MONITOR_TASK
    if _MONITOR_TASK and not _MONITOR_TASK.done():
        return _MONITOR_TASK
    if loop is None:
        loop = asyncio.get_event_loop()
    _MONITOR_TASK = loop.create_task(monitor_event_loop())
    return _MONITOR_TASK
