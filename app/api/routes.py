from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.controller import AgentController
from app.agent.state import AgentState
from app.sandbox.executor import SandboxInfrastructureError

router = APIRouter()


class RunRequest(BaseModel):
    task: str = Field(min_length=1)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/run", response_model=AgentState)
def run_agent(request: RunRequest) -> AgentState:
    controller = AgentController()
    try:
        return controller.run(request.task)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except SandboxInfrastructureError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc