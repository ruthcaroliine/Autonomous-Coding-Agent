import os
import tempfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, ImageNotFound, NotFound

from app.agent.state import ExecutionObservation
from app.config import Settings, settings


class SandboxInfrastructureError(RuntimeError):
    """Raised when Docker infrastructure fails before user code can run."""


class DockerSandboxExecutor:
    """Execute generated Python in an isolated Docker container.

    Partial generated files are read back even when a run times out or is
    OOM-killed. Those files are useful diagnostic signal for the next retry,
    even when they are incomplete.
    """

    def __init__(self, app_settings: Settings = settings) -> None:
        self.image = app_settings.sandbox_image
        self.max_execution_seconds = app_settings.max_execution_seconds
        self.memory_limit_mb = app_settings.memory_limit_mb
        self.cpu_limit = app_settings.cpu_limit
        self.network_enabled = app_settings.network_enabled

    def execute(self, code: str) -> ExecutionObservation:
        container = None

        with tempfile.TemporaryDirectory(prefix="coding-agent-run-") as workspace:
            workspace_path = Path(workspace)
            script_path = workspace_path / "script.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                client = docker.from_env()
                container = client.containers.run(
                    image=self.image,
                    command=["python", "/workspace/script.py"],
                    detach=True,
                    working_dir="/workspace",
                    volumes={
                        os.path.abspath(workspace): {
                            "bind": "/workspace",
                            "mode": "rw",
                        }
                    },
                    mem_limit=f"{self.memory_limit_mb}m",
                    nano_cpus=int(self.cpu_limit * 1_000_000_000),
                    network_disabled=not self.network_enabled,
                    read_only=True,
                    tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
                    cap_drop=["ALL"],
                    security_opt=["no-new-privileges"],
                    environment={
                        "HOME": "/workspace",
                        "MPLCONFIGDIR": "/workspace/.mplconfig",
                        "PYTHONUNBUFFERED": "1",
                    },
                )

                timed_out = False
                exit_code: int | None
                try:
                    wait_result = container.wait(timeout=self.max_execution_seconds)
                    exit_code = self._extract_exit_code(wait_result)
                except Exception as exc:
                    if not self._is_wait_timeout(exc):
                        raise
                    timed_out = True
                    container.kill()
                    wait_result = container.wait()
                    exit_code = self._extract_exit_code(wait_result)

                stdout = self._container_logs(container, stdout=True, stderr=False)
                stderr = self._container_logs(container, stdout=False, stderr=True)
                container.reload()
                inspect_data = container.attrs
                state = inspect_data.get("State", {})

                if state.get("OOMKilled") and "oom" not in stderr.lower():
                    stderr = self._append_stderr_note(stderr, "Container was OOM-killed.")

                return ExecutionObservation(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    generated_files=self._generated_files(workspace_path),
                    timed_out=timed_out,
                )
            except (ImageNotFound, NotFound) as exc:
                raise SandboxInfrastructureError(
                    f"Sandbox image '{self.image}' is not available. "
                    "Build it with: docker build -f docker/sandbox.Dockerfile "
                    "-t coding-agent-sandbox ."
                ) from exc
            except DockerException as exc:
                raise SandboxInfrastructureError(
                    f"Docker sandbox infrastructure failed: {exc}"
                ) from exc
            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except DockerException:
                        pass

    def _extract_exit_code(self, wait_result: Any) -> int | None:
        if isinstance(wait_result, dict):
            status_code = wait_result.get("StatusCode")
            return int(status_code) if status_code is not None else None
        return None

    def _container_logs(self, container: Any, stdout: bool, stderr: bool) -> str:
        raw_logs = container.logs(stdout=stdout, stderr=stderr)
        return raw_logs.decode("utf-8", errors="replace")

    def _generated_files(self, workspace_path: Path) -> list[str]:
        generated_files: list[str] = []
        ignored = {"script.py"}
        ignored_dirs = {".mplconfig", "__pycache__"}

        for path in workspace_path.rglob("*"):
            if not path.is_file():
                continue
            relative_path = path.relative_to(workspace_path)
            if relative_path.parts[0] in ignored_dirs or relative_path.name in ignored:
                continue
            generated_files.append(relative_path.as_posix())

        return sorted(generated_files)

    def _is_wait_timeout(self, exc: Exception) -> bool:
        return exc.__class__.__name__ in {"ReadTimeout", "Timeout", "TimeoutError"}

    def _append_stderr_note(self, stderr: str, note: str) -> str:
        if stderr and not stderr.endswith("\n"):
            stderr += "\n"
        return f"{stderr}{note}\n"
