from dataclasses import dataclass
from typing import Any, Dict
from uuid import uuid4


@dataclass
class JobStatus:
    status: str
    detail: str | None = None
    result: Any | None = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobStatus] = {}

    def create_job(self) -> str:
        job_id = str(uuid4())
        self._jobs[job_id] = JobStatus(status="queued")
        return job_id

    def update(self, job_id: str, status: str, detail: str | None = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            self._jobs[job_id].detail = detail

    def set_result(self, job_id: str, result: Any) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].status = "done"
            self._jobs[job_id].result = result

    def get(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)


job_manager = JobManager()
