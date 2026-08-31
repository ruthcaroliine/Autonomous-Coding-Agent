from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from enum import Enum

class AttemptOutcome(StrEnum):
    SUCCESS = "success"
    RUNTIME_ERROR = "runtime_error"
    INVALID_RESULT = "invalid_result"

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class ExecutionObservation(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    generated_files: list[str] = Field(default_factory=list)
    timed_out: bool = False


class Attempt(BaseModel):
    attempt_number: int
    code: str
    observation: ExecutionObservation
    outcome: AttemptOutcome
    diagnosis: str


class AgentState(BaseModel):
    """State for one agent run.

    max_retry_attempts is a single shared retry budget across runtime errors
    and invalid-result diagnoses. A script crash and a "ran successfully but
    produced the wrong output" failure both consume one attempt, matching the
    single "Attempts left?" decision node in the architecture flowchart.
    """

    run_id: UUID = Field(default_factory=uuid4)
    task: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: list[Attempt] = Field(default_factory=list)
    max_retry_attempts: int
    final_answer: str | None = None
    succeeded: bool = False
    status: RunStatus = RunStatus.PENDING

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def attempts_remaining(self) -> int:
        return max(self.max_retry_attempts - self.attempts_used, 0)

    def add_attempt(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)
        if attempt.outcome == AttemptOutcome.SUCCESS:
            self.succeeded = True
