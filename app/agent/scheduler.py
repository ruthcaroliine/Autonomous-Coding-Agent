from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.agent.controller import AgentController
from app.agent.state import AgentState
from app.config import settings


class TaskScheduler:
    """
    In-process task queue + worker pool. Each submitted task gets a run_id
    immediately; a pool of worker threads executes AgentController.run()
    concurrently. Job state lives in memory only (phase 6 will swap this
    for persisted storage, e.g. Redis).
    """

    def __init__(self, num_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._jobs: dict[str, AgentState] = {}
        self._lock = threading.Lock()

    def submit(self, task: str) -> str:
        run_id = str(uuid4())
        placeholder = AgentState(run_id=run_id, task=task, max_retry_attempts=settings.max_retry_attempts)
        with self._lock:
            self._jobs[run_id] = placeholder

        self._executor.submit(self._execute, run_id, task)
        return run_id

    def _execute(self, run_id: str, task: str) -> None:
        controller = AgentController()
        result_state = controller.run(task)
        result_state.run_id = run_id  # keep the id assigned at submit time
        with self._lock:
            self._jobs[run_id] = result_state

    def get_status(self, run_id: str) -> AgentState | None:
        with self._lock:
            return self._jobs.get(run_id)


scheduler = TaskScheduler()