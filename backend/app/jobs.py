"""In-process background jobs with progress reporting for long backtests and research runs.

Jobs run on a small thread pool and are kept in memory (they are lost on restart); completed
results are persisted through :class:`backend.app.store.RunStore`, which survives restarts.
"""
from __future__ import annotations

import logging
import threading
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

log = logging.getLogger("fxlab.jobs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobManager:
    def __init__(self, workers: int = 2, max_history: int = 200):
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fxlab-job")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._max_history = max_history

    def submit(self, kind: str, work: Callable[[Callable[[str, float], None]], dict[str, Any]], meta: dict[str, Any] | None = None) -> dict[str, Any]:
        job_id = str(uuid4())
        job = {"job_id": job_id, "kind": kind, "status": "queued", "stage": "queued", "progress": 0.0,
               "created_at": _now(), "started_at": None, "finished_at": None, "error": None, "result": None, **(meta or {})}
        with self._lock:
            self._jobs[job_id] = job
            self._trim()

        def progress(stage: str, fraction: float) -> None:
            with self._lock:
                job["stage"] = stage
                job["progress"] = max(job["progress"], min(1.0, float(fraction)))

        def runner() -> None:
            with self._lock:
                job["status"], job["started_at"] = "running", _now()
            try:
                outcome = work(progress)
                with self._lock:
                    job.update({"status": "done", "stage": "done", "progress": 1.0, "finished_at": _now(), "result": outcome})
            except Exception as exc:  # noqa: BLE001 - surface any failure to the client
                log.exception("job %s failed", job_id)
                with self._lock:
                    job.update({"status": "failed", "finished_at": _now(), "error": str(exc), "traceback": traceback.format_exc()[-4000:]})

        self._executor.submit(runner)
        return self.public(job_id)

    def public(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {k: v for k, v in job.items() if k not in {"traceback"}}

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{k: v for k, v in job.items() if k not in {"traceback", "result"}} for job in sorted(self._jobs.values(), key=lambda j: j["created_at"], reverse=True)]

    def _trim(self) -> None:
        finished = [job for job in self._jobs.values() if job["status"] in {"done", "failed"}]
        if len(self._jobs) > self._max_history:
            for job in sorted(finished, key=lambda j: j["created_at"])[: len(self._jobs) - self._max_history]:
                self._jobs.pop(job["job_id"], None)
