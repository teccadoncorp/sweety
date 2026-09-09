from __future__ import annotations

import json
from decimal import Decimal

import httpx

from app.adapters.base import AdapterHealth, RunContext, RunResult, register
from app.core.config import get_settings
from app.services.sanitize import sanitize_json, text_from_content


def _estimate_cost(tokens_in: int, tokens_out: int, reported: float | None) -> float:
    if reported is not None:
        return float(reported)
    return (tokens_in / 1_000_000) * 0.15 + (tokens_out / 1_000_000) * 0.60


class OpenRouterAdapter:
    name = "openrouter"

    def diagnose(self) -> AdapterHealth:
        key = get_settings().openrouter_api_key
        if not key:
            return AdapterHealth(
                name=self.name,
                status="missing_key",
                detail="OPENROUTER_API_KEY is not set. Heartbeats will be blocked.",
            )
        return AdapterHealth(name=self.name, status="ready", detail="OpenRouter key present.")

    def execute(self, ctx: RunContext) -> RunResult:
        settings = get_settings()
        if not settings.openrouter_api_key:
            return RunResult(
                status="blocked",
                summary="OPENROUTER_API_KEY is not configured.",
            )

        messages: list[dict] = [
            {"role": "system", "content": ctx.system_prompt},
            {"role": "user", "content": ctx.user_prompt},
        ]
        trace: list[dict] = []
        tokens_in = 0
        tokens_out = 0
        cost = Decimal("0")
        final_text = ""

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.sweety_public_url,
            "X-Title": "Sweety",
        }

        with httpx.Client(timeout=90.0) as client:
            for round_i in range(settings.agent_max_tool_rounds):
                payload = {
                    "model": ctx.model or settings.openrouter_default_model,
                    "messages": messages,
                    "tools": ctx.tools,
                    "tool_choice": "auto",
                }
                response = client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    detail = response.text[:800]
                    trace.append({"event": "error", "status": response.status_code, "body": detail})
                    return RunResult(
                        status="error",
                        summary=f"OpenRouter HTTP {response.status_code}: {detail}",
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=float(cost),
                        trace=trace,
                    )
                data = response.json()
                usage = data.get("usage") or {}
                tokens_in += int(usage.get("prompt_tokens") or 0)
                tokens_out += int(usage.get("completion_tokens") or 0)
                reported = usage.get("cost")
                cost += Decimal(str(_estimate_cost(int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0), reported)))

                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                safe_message = {
                    "role": message.get("role") or "assistant",
                    "content": text_from_content(message.get("content"), 12_000) or None,
                    "tool_calls": message.get("tool_calls") or None,
                }
                if not safe_message["tool_calls"]:
                    safe_message.pop("tool_calls")
                messages.append({k: v for k, v in safe_message.items() if v is not None})
                tool_calls = message.get("tool_calls") or []
                content = text_from_content(message.get("content"), 4000)
                if content:
                    final_text = content
                    trace.append({"event": "assistant", "round": round_i, "content": content[:2000]})

                if not tool_calls:
                    break

                for call in tool_calls:
                    fn = call.get("function") or {}
                    name = fn.get("name") or ""
                    raw_args = fn.get("arguments") or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args = {}
                    result = ctx.execute_tool(name, args)
                    safe_result = sanitize_json(result)
                    trace.append({"event": "tool", "name": name, "args": sanitize_json(args), "result": safe_result})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps(safe_result, default=str)[:8000],
                        }
                    )

        return RunResult(
            status="ok",
            summary=text_from_content(final_text or "Heartbeat finished with no assistant text.", 4000),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=float(cost),
            trace=trace,
        )


register(OpenRouterAdapter())
