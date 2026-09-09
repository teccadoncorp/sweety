import json
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "skills"

SKILLS = [
    ("email-lifecycle", "Email Lifecycle", ["email", "lifecycle", "cmo", "copywriter"], "Design welcome, nurture, and win-back email sequences as artifacts."),
    ("paid-media", "Paid Media", ["media", "analyst", "cmo"], "Plan paid mix, audiences, budgets, and creative tests without spending live."),
    ("community-ops", "Community Ops", ["community", "social", "cmo"], "Draft replies, rituals, and moderation notes that stay on-brand."),
    ("pr-outreach", "PR Outreach", ["pr", "cmo", "strategist"], "Build media lists, pitches, and embargo notes for board approval."),
    ("seo-content", "SEO Content", ["seo", "strategist", "copywriter"], "Turn keyword research into outlines, titles, and on-page briefs."),
    ("landing-page", "Landing Page", ["copywriter", "designer", "seo", "cmo"], "Structure landing pages: promise, proof, offer, and CTA."),
    ("influencer-brief", "Influencer Brief", ["social", "pr", "cmo"], "Write creator briefs with talking points, usage rights, and deliverables."),
    ("crm-pipeline", "CRM Pipeline", ["crm", "lifecycle", "cmo", "analyst"], "Score leads, log touches, and move deals with CRM tools."),
    ("competitor-watch", "Competitor Watch", ["strategist", "analyst", "cmo", "pr"], "Scan competitors and summarize threats, gaps, and moves."),
    ("content-calendar", "Content Calendar", ["social", "copywriter", "cmo"], "Build a two-week calendar with platforms, ratios, and owners."),
    ("video-script", "Video Script", ["video", "copywriter", "social"], "Write short-form scripts, shot lists, and HeyGen briefs."),
    ("ab-test", "A/B Test", ["analyst", "media", "cmo"], "Design experiments with hypothesis, variants, and success metrics."),
    ("retention-play", "Retention Play", ["lifecycle", "email", "crm", "cmo"], "Design activation and win-back plays across CRM and email."),
    ("launch-checklist", "Launch Checklist", ["cmo", "lifecycle", "strategist"], "Turn a launch into a sequenced, owner-assigned checklist."),
    ("crisis-comms", "Crisis Comms", ["pr", "cmo", "community"], "Draft holding statements and escalation paths. Never post live unaided."),
    ("newsletter", "Newsletter", ["email", "copywriter", "cmo"], "Plan and draft newsletters with a single sharp idea per issue."),
    ("ads-creative", "Ads Creative", ["media", "designer", "copywriter"], "Pair hooks, bodies, and platform-correct visuals for ads."),
    ("customer-voice", "Customer Voice", ["analyst", "strategist", "crm"], "Synthesize reviews and interviews into language the brand can use."),
    ("partnership-dev", "Partnership Dev", ["pr", "cmo", "crm"], "Map partner targets, offers, and co-marketing one-pagers."),
    ("webinar-play", "Webinar Play", ["lifecycle", "email", "cmo"], "Plan webinar funnel: invite, run-of-show, and follow-up."),
    ("ugc-brief", "UGC Brief", ["social", "designer", "cmo"], "Brief creators for UGC: hook, product proof, and usage rights."),
    ("localization", "Localization", ["copywriter", "cmo", "strategist"], "Adapt copy for markets without flattening the brand voice."),
    ("faq-voice", "FAQ Voice", ["copywriter", "community", "cmo"], "Turn objections into on-brand FAQs and reply macros."),
    ("event-activation", "Event Activation", ["pr", "lifecycle", "cmo"], "Plan event moments, capture, and follow-up plays."),
    ("affiliate", "Affiliate", ["media", "crm", "cmo"], "Design partner/affiliate offers, tracking notes, and creative."),
    ("sms-lifecycle", "SMS Lifecycle", ["email", "lifecycle", "cmo"], "Draft SMS journeys that stay short, useful, and opt-in clean."),
    ("podcast-brief", "Podcast Brief", ["video", "pr", "cmo"], "Write guest briefs, talking tracks, and clip plans."),
    ("store-launch", "Store Launch", ["cmo", "lifecycle", "designer"], "Checklist a store or drop launch across channels."),
    ("onboarding-ux", "Onboarding UX", ["lifecycle", "designer", "copywriter"], "Map first-run copy and screens that activate a new user."),
    ("pricing-page", "Pricing Page", ["copywriter", "strategist", "cmo"], "Structure pricing narrative, tiers, and objection handling."),
]


def main() -> None:
    for slug, name, roles, desc in SKILLS:
        folder = root / slug
        folder.mkdir(exist_ok=True)
        (folder / "manifest.json").write_text(
            json.dumps(
                {
                    "slug": slug,
                    "name": name,
                    "version": "1.0.0",
                    "allowed_roles": roles,
                    "description": desc,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (folder / "SKILL.md").write_text(
            f"""# {name}

{desc}

## How to work
1. Read brand context and the assigned task.
2. Research only if it changes the recommendation.
3. Post a markdown artifact the board can approve.
4. Delegate follow-ups with create_task / delegate_task.
5. Use CRM tools when the work is about leads, deals, or touches.
6. Request approval before anything live (publish, spend, outreach).

## Output
- Title the artifact clearly
- Include owners, timing, and next action
- Stay in brand voice
""",
            encoding="utf-8",
        )
    print(f"wrote {len(SKILLS)} skills into {root}")


if __name__ == "__main__":
    main()
