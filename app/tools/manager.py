from collections.abc import Callable
from typing import Any, Protocol


class Tool(Protocol):
    name: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class ToolManager:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def available_tools(self) -> list[str]:
        return sorted(self._tools)


def tool_from_callable(name: str, func: Callable[..., Any]) -> Tool:
    class CallableTool:
        def __init__(self) -> None:
            self.name = name

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

    return CallableTool()
