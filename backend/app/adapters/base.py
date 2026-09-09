from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass
class AdapterHealth:
    name: str
    status: str
    detail: str


@dataclass
class RunContext:
    brand_id: UUID
    agent_id: UUID
    run_id: UUID
    model: str
    system_prompt: str
    user_prompt: str
    tools: list[dict[str, Any]]
    execute_tool: Any


@dataclass
class RunResult:
    status: str
    summary: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)


class AgentAdapter(Protocol):
    name: str

    def diagnose(self) -> AdapterHealth: ...

    def execute(self, ctx: RunContext) -> RunResult: ...


_REGISTRY: dict[str, AgentAdapter] = {}


def register(adapter: AgentAdapter) -> AgentAdapter:
    _REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> AgentAdapter:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown adapter: {name}")
    return _REGISTRY[name]


def all_adapters() -> list[AgentAdapter]:
    return [get_adapter(n) for n in ("openrouter", "claude", "codex", "langchain", "langgraph")]
