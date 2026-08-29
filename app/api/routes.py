from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.scheduler import scheduler
from app.agent.state import AgentState

router = APIRouter()


class RunRequest(BaseModel):
    task: str = Field(min_length=1)


class RunAccepted(BaseModel):
    run_id: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/run", response_model=RunAccepted, status_code=202)
def submit_task(request: RunRequest) -> RunAccepted:
    run_id = scheduler.submit(request.task)
    return RunAccepted(run_id=run_id)


@router.get("/run/{run_id}", response_model=AgentState)
def get_run_status(run_id: str) -> AgentState:
    state = scheduler.get_status(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown run_id")
    return state