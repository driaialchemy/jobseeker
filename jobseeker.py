"""Small runnable baseline for the Jobseeker AI Agent repository.

The module is intentionally dependency-free so a fresh clone can run a useful
smoke path before any LLM integrations are added.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass


DATA_SKILLS = {"python", "sql", "excel", "tableau", "power bi", "dashboarding"}
GENERAL_SKILLS = {"resume", "portfolio", "networking", "interviewing"}


@dataclass(frozen=True)
class JobPlan:
    target_role: str
    strengths: list[str]
    gaps: list[str]
    next_steps: list[str]


def _clean_items(items: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for item in items or []:
        value = item.strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def build_plan(target_role: str, skills: list[str] | None = None) -> JobPlan:
    role = target_role.strip()
    if not role:
        raise ValueError("target role cannot be blank")

    normalized_skills = _clean_items(skills)
    target_keywords = f"{role} {' '.join(normalized_skills)}".lower()
    required = DATA_SKILLS if any(word in target_keywords for word in ("data", "analyst", "analytics", "ai")) else GENERAL_SKILLS

    strengths = sorted(skill for skill in normalized_skills if skill in required)
    gaps = sorted(required - set(normalized_skills))
    next_steps = [
        f"Tailor resume bullets to {role} outcomes.",
        "Prepare two portfolio examples with measurable impact.",
        "Draft five interview stories using the STAR format.",
    ]

    if gaps:
        next_steps.insert(1, f"Close priority skill gaps: {', '.join(gaps[:3])}.")

    return JobPlan(
        target_role=role,
        strengths=strengths,
        gaps=gaps,
        next_steps=next_steps,
    )


def plan_to_text(plan: JobPlan) -> str:
    lines = [
        f"Target role: {plan.target_role}",
        f"Strengths: {', '.join(plan.strengths) if plan.strengths else 'none listed'}",
        f"Gaps: {', '.join(plan.gaps) if plan.gaps else 'none'}",
        "Next steps:",
    ]
    lines.extend(f"- {step}" for step in plan.next_steps)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a lightweight job search action plan.")
    parser.add_argument("target_role", help="Role to prepare for, for example 'Data Analyst'.")
    parser.add_argument("--skills", nargs="*", default=[], help="Current skills to compare against the target role.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(args.target_role, args.skills)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(asdict(plan), indent=2))
    else:
        print(plan_to_text(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
