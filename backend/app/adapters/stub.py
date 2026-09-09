from app.adapters.base import AdapterHealth, RunContext, RunResult, register


class StubAdapter:
    def __init__(self, name: str, detail: str):
        self.name = name
        self._detail = detail

    def diagnose(self) -> AdapterHealth:
        return AdapterHealth(name=self.name, status="not_configured", detail=self._detail)

    def execute(self, ctx: RunContext) -> RunResult:
        return RunResult(
            status="stubbed",
            summary=f"{self.name} adapter is a v1 stub. Assign this agent to openrouter to run work.",
            trace=[{"event": "stub", "adapter": self.name, "agent_id": str(ctx.agent_id)}],
        )


register(StubAdapter("claude", "Claude API adapter is stubbed in v1. Use OpenRouter."))
register(StubAdapter("codex", "Codex CLI adapter is stubbed in v1. Use OpenRouter."))
register(StubAdapter("langchain", "LangChain adapter is stubbed in v1. Interface reserved."))
register(StubAdapter("langgraph", "LangGraph adapter is stubbed in v1. Interface reserved."))
