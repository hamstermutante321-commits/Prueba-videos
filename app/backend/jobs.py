"""Job system base (Phase 4): un worker a la vez (GPU), cola visible, cancelación.

Los runners pesados (story, image, video...) se registran aquí en sus fases.
Persistencia en memoria por ahora (endurecer en Phase 18).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional

from models import Job, JobStatus, JobType

Runner = Callable[["JobContext"], None]


class JobContext:
    def __init__(self, manager: "JobManager", job_id: str) -> None:
        self._manager = manager
        self.job_id = job_id

    def update(self, progress: int, message: str = "") -> None:
        self._manager._update(self.job_id, progress, message)

    def is_cancelled(self) -> bool:
        return self._manager._cancel_flags.get(self.job_id, False)

    @property
    def payload(self) -> dict:
        return self._manager._payloads.get(self.job_id, {})


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._payloads: dict[str, dict] = {}
        self._cancel_flags: dict[str, bool] = {}
        self._futures: dict[str, Future] = {}
        self._runners: dict[str, Runner] = {}
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gpu-worker")
        self.register("ping", _run_ping)

    def register(self, job_type: str, runner: Runner) -> None:
        self._runners[job_type] = runner

    def supported_types(self) -> list[str]:
        return sorted(self._runners)

    def create(self, job_type: str, payload: Optional[dict] = None) -> Job:
        if job_type not in self._runners:
            raise KeyError(f"unknown job type: {job_type}")
        job = Job(type=JobType(job_type))
        with self._lock:
            self._jobs[job.job_id] = job
            self._payloads[job.job_id] = payload or {}
            self._cancel_flags[job.job_id] = False
        fut = self._pool.submit(self._execute, job.job_id)
        with self._lock:
            self._futures[job.job_id] = fut
        return job

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            fut = self._futures.get(job_id)
        if job is None:
            return None
        self._cancel_flags[job_id] = True
        if fut is not None:
            fut.cancel()
        with self._lock:
            if job.status in (JobStatus.queued, JobStatus.running):
                job.status = JobStatus.cancelled
                job.message = "cancelled by user"
        return job

    # --- interno ---

    def _update(self, job_id: str, progress: int, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.progress = max(0, min(100, progress))
            if message:
                job.message = message

    def _execute(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if self._cancel_flags.get(job_id):
                job.status = JobStatus.cancelled
                return
            job.status = JobStatus.running
            job.message = "running"
            runner = self._runners.get(job.type.value)
        ctx = JobContext(self, job_id)
        try:
            if runner is None:
                raise RuntimeError(f"no runner for {job.type}")
            runner(ctx)
            with self._lock:
                if self._cancel_flags.get(job_id):
                    job.status = JobStatus.cancelled
                else:
                    job.status = JobStatus.done
                    job.progress = 100
                    if not job.message or job.message == "running":
                        job.message = "done"
        except Exception as exc:  # runner falla -> error entendible
            with self._lock:
                job.status = JobStatus.error
                job.message = str(exc)[:500]


def _run_ping(ctx: JobContext) -> None:
    steps = int(ctx.payload.get("steps", 5))
    for i in range(steps):
        if ctx.is_cancelled():
            return
        ctx.update(int(100 * i / max(steps, 1)), f"ping {i + 1}/{steps}")
        time.sleep(0.2)
    ctx.update(100, "pong")


manager = JobManager()
