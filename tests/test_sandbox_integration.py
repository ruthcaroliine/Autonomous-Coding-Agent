import docker
import pytest
from docker.errors import DockerException, ImageNotFound, NotFound

from app.config import Settings
from app.sandbox.executor import DockerSandboxExecutor


SANDBOX_IMAGE = "coding-agent-sandbox:latest"


def docker_client_or_skip():
    try:
        client = docker.from_env()
        client.ping()
        client.images.get(SANDBOX_IMAGE)
        return client
    except ImageNotFound:
        pytest.skip(
            f"Sandbox image {SANDBOX_IMAGE!r} is not built. "
            "Run: docker build -f docker/sandbox.Dockerfile -t coding-agent-sandbox ."
        )
    except DockerException as exc:
        pytest.skip(f"Docker is not available: {exc}")


@pytest.fixture
def docker_client():
    return docker_client_or_skip()


@pytest.fixture
def executor(docker_client):
    return DockerSandboxExecutor(
        Settings(
            sandbox_image=SANDBOX_IMAGE,
            max_execution_seconds=1,
            memory_limit_mb=128,
            cpu_limit=1.0,
            network_enabled=False,
        )
    )


def assert_no_orphaned_container(docker_client, before_ids: set[str]) -> None:
    after_ids = {container.id for container in docker_client.containers.list(all=True)}
    assert after_ids == before_ids


def test_successful_script_captures_stdout(executor, docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}

    observation = executor.execute("print('hello sandbox')")

    assert observation.stdout == "hello sandbox\n"
    assert observation.stderr == ""
    assert observation.exit_code == 0
    assert observation.generated_files == []
    assert not observation.timed_out
    assert_no_orphaned_container(docker_client, before_ids)


def test_raising_script_captures_stderr(executor, docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}

    observation = executor.execute("raise ValueError('boom')")

    assert observation.exit_code != 0
    assert "ValueError: boom" in observation.stderr
    assert not observation.timed_out
    assert_no_orphaned_container(docker_client, before_ids)


def test_sleeping_script_times_out_and_container_is_removed(executor, docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}

    observation = executor.execute("import time\ntime.sleep(10)")

    assert observation.timed_out
    assert observation.exit_code is not None
    assert_no_orphaned_container(docker_client, before_ids)


def test_timeout_preserves_generated_files(executor, docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}

    observation = executor.execute(
        "from pathlib import Path\n"
        "Path('partial.csv').write_text('name,price\\nwidget,10\\n')\n"
        "while True:\n"
        "    pass\n"
    )

    assert observation.timed_out
    assert "partial.csv" in observation.generated_files
    assert_no_orphaned_container(docker_client, before_ids)


def test_memory_limit_oom_is_captured(docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}
    executor = DockerSandboxExecutor(
        Settings(
            sandbox_image=SANDBOX_IMAGE,
            max_execution_seconds=5,
            memory_limit_mb=64,
            cpu_limit=1.0,
            network_enabled=False,
        )
    )

    observation = executor.execute(
        "blocks = []\n"
        "while True:\n"
        "    blocks.append(bytearray(10 * 1024 * 1024))\n"
    )

    assert observation.exit_code != 0
    assert "oom" in observation.stderr.lower()
    assert_no_orphaned_container(docker_client, before_ids)


def test_network_disabled_blocks_network_access(executor, docker_client) -> None:
    before_ids = {container.id for container in docker_client.containers.list(all=True)}

    observation = executor.execute(
        "import requests\n"
        "requests.get('https://example.com', timeout=2)\n"
    )

    assert observation.exit_code != 0
    assert observation.stderr
    assert not observation.timed_out
    assert_no_orphaned_container(docker_client, before_ids)
