from __future__ import annotations

import json

import httpx

from app.core.config import get_settings, model_map
from app.models.crm import CrmContact, CrmDeal
from app.services.crm import board_stats, heuristic_score


def _chat(system: str, user: str) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key:
        return ""
    response = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": settings.sweety_public_url,
            "X-Title": f"{settings.app_name} CRM",
        },
        json={
            "model": model_map()["chat"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        },
        timeout=45,
    )
    if response.status_code >= 400:
        return ""
    data = response.json()
    return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


def score_contact(contact: CrmContact) -> dict:
    score, temp, reasons = heuristic_score(contact)
    ai = _chat(
        "You are a B2B CRM scoring assistant. Reply with JSON only: "
        '{"signal_score": 0-100, "temperature": "ice|cool|warm|hot|star", "reasons": "short", "next_action": "one concrete next step"}.',
        json.dumps(
            {
                "name": contact.name,
                "title": contact.title,
                "company": contact.company,
                "email": contact.email,
                "channel": contact.channel,
                "notes": contact.notes,
                "next_action": contact.next_action,
                "current_score": contact.signal_score,
            }
        ),
    )
    if ai:
        try:
            start = ai.find("{")
            end = ai.rfind("}")
            parsed = json.loads(ai[start : end + 1]) if start >= 0 and end > start else {}
            score = max(0, min(100, int(parsed.get("signal_score", score))))
            temp = parsed.get("temperature") or temp
            reasons = parsed.get("reasons") or reasons
            next_action = parsed.get("next_action") or contact.next_action
            return {
                "signal_score": score,
                "temperature": temp,
                "reasons": reasons,
                "next_action": next_action,
                "source": "ai",
            }
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
    return {
        "signal_score": score,
        "temperature": temp,
        "reasons": reasons,
        "next_action": contact.next_action
        or "Send a short, specific follow-up referencing their last interest.",
        "source": "heuristic",
    }


def coach_deal(deal: CrmDeal, contact: CrmContact | None) -> dict:
    fallback = {
        "next_action": "Book a 20-minute working session and confirm budget owner.",
        "risk": "Stage may stall without a dated next step.",
        "talking_points": [
            "Confirm the decision date",
            "Name the economic buyer",
            "Offer a scoped pilot",
        ],
        "source": "heuristic",
    }
    ai = _chat(
        "You are an enterprise sales coach. Reply JSON only: "
        '{"next_action": "...", "risk": "...", "talking_points": ["...","...","..."]}.',
        json.dumps(
            {
                "deal": deal.name,
                "stage": deal.stage,
                "value_usd": str(deal.value_usd),
                "probability": deal.probability,
                "close_date": deal.close_date,
                "notes": deal.notes,
                "contact": {
                    "name": contact.name if contact else "",
                    "title": contact.title if contact else "",
                    "next_action": contact.next_action if contact else "",
                },
            }
        ),
    )
    if not ai:
        return fallback
    try:
        start = ai.find("{")
        end = ai.rfind("}")
        parsed = json.loads(ai[start : end + 1])
        return {
            "next_action": parsed.get("next_action") or fallback["next_action"],
            "risk": parsed.get("risk") or fallback["risk"],
            "talking_points": parsed.get("talking_points") or fallback["talking_points"],
            "source": "ai",
        }
    except (ValueError, TypeError, json.JSONDecodeError):
        return fallback


def pipeline_brief(db, brand_id, brand_name: str) -> dict:
    stats = board_stats(db, brand_id)
    fallback = (
        f"## {brand_name} pipeline\n"
        f"- Open deals: {stats['open_deals']}\n"
        f"- Pipeline: ${stats['pipeline_usd']}\n"
        f"- Weighted: ${stats['weighted_pipeline_usd']}\n"
        f"- Overdue follow-ups: {stats['overdue']}\n\n"
        "Focus this week on overdue hot leads and anything in commit without a close date."
    )
    ai = _chat(
        "You are a VP Sales. Write a tight markdown briefing: snapshot, risks, 5 actions for this week.",
        json.dumps({k: (str(v) if not isinstance(v, (int, float, dict)) else v) for k, v in stats.items()}),
    )
    return {"brief": ai.strip() or fallback, "source": "ai" if ai.strip() else "heuristic", "stats": {
        "open_deals": stats["open_deals"],
        "pipeline_usd": str(stats["pipeline_usd"]),
        "weighted_pipeline_usd": str(stats["weighted_pipeline_usd"]),
        "overdue": stats["overdue"],
    }}
