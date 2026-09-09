import json
from dataclasses import dataclass
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"


@dataclass
class SkillPack:
    slug: str
    name: str
    version: str
    allowed_roles: list[str]
    description: str
    instructions: str


def _parse_skill(folder: Path) -> SkillPack | None:
    manifest_path = folder / "manifest.json"
    skill_md = folder / "SKILL.md"
    if not manifest_path.exists() or not skill_md.exists():
        return None
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = skill_md.read_text(encoding="utf-8")
    first_line = next((line.strip("# ").strip() for line in body.splitlines() if line.strip()), data.get("slug", folder.name))
    return SkillPack(
        slug=data.get("slug", folder.name),
        name=data.get("name", first_line),
        version=str(data.get("version", "1.0.0")),
        allowed_roles=list(data.get("allowed_roles", [])),
        description=data.get("description", ""),
        instructions=body,
    )


def load_all_skills() -> dict[str, SkillPack]:
    packs: dict[str, SkillPack] = {}
    if not SKILLS_DIR.exists():
        return packs
    for folder in sorted(SKILLS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        pack = _parse_skill(folder)
        if pack:
            packs[pack.slug] = pack
    return packs


def skills_for_agent(role: str, slugs: list[str]) -> list[SkillPack]:
    catalog = load_all_skills()
    selected: list[SkillPack] = []
    for slug in slugs:
        pack = catalog.get(slug)
        if pack is None:
            continue
        selected.append(pack)
    return selected


def render_skill_block(role: str, slugs: list[str]) -> str:
    packs = skills_for_agent(role, slugs)
    if not packs:
        return "No skills assigned."
    parts = []
    for pack in packs:
        parts.append(f"### Skill: {pack.name} (`{pack.slug}`)\n\n{pack.instructions}")
    return "\n\n---\n\n".join(parts)
