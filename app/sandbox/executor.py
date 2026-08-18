from app.agent.state import ExecutionObservation
from app.config import Settings, settings


class DockerSandboxExecutor:
    """Stub for isolated Python execution.

    Open question for Phase 2: when a run times out or is OOM-killed, should
    partial generated files still be read back from the workspace, or should
    they be discarded to avoid returning incomplete artifacts?
    """

    def __init__(self, app_settings: Settings = settings) -> None:
        self.max_execution_seconds = app_settings.max_execution_seconds
        self.memory_limit_mb = app_settings.memory_limit_mb
        self.cpu_limit = app_settings.cpu_limit
        self.network_enabled = app_settings.network_enabled

    def execute(self, code: str) -> ExecutionObservation:
        raise NotImplementedError(
            "Phase 2 implements Docker sandbox execution. "
            "DockerSandboxExecutor.execute is a scaffold only."
        )
