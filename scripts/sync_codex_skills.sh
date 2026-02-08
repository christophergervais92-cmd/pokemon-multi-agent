#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SRC="${CODEX_HOME}/skills/"
DST="${REPO_ROOT}/codex_skills/"

mkdir -p "$DST"

# Mirror local Codex skills into the repo, excluding heavyweight or generated dirs.
rsync -a --delete \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '.DS_Store' \
  "${SRC}" "${DST}"

export REPO_ROOT
python3 - <<'PY'
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(os.environ["REPO_ROOT"])
SKILLS_DIR = ROOT / "codex_skills"
OUT = ROOT / ".cursor" / "rules" / "codex-skills-index.mdc"


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)\s*$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if (len(v) >= 2) and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        data[k] = v
    return data


def ascii_punct(text: str) -> str:
    # Keep output ASCII; normalize common punctuation found in skill descriptions.
    repl = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201A": "'",
        "\u201B": "'",
        "\u2032": "'",
        "\u2035": "'",
        "\u201C": '"',
        "\u201D": '"',
        "\u201E": '"',
        "\u201F": '"',
        "\u2033": '"',
        "\u2036": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
    }
    out = text
    for k, v in repl.items():
        out = out.replace(k, v)
    return out.encode("ascii", "ignore").decode("ascii")


skills: list[tuple[str, str, str]] = []
for skill_md in SKILLS_DIR.rglob("SKILL.md"):
    rel = skill_md.relative_to(ROOT)
    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    name = ascii_punct((fm.get("name") or rel.parent.name).strip())
    desc = ascii_punct((fm.get("description") or "").strip())
    skills.append((name, desc, rel.as_posix()))

skills.sort(key=lambda t: t[0].lower())

OUT.parent.mkdir(parents=True, exist_ok=True)
lines: list[str] = []
lines.append("# Codex Skills (Vendored)")
lines.append("")
lines.append("This repo vendors the Codex desktop app skills under `codex_skills/` so Cursor can use the same playbooks.")
lines.append("")
lines.append("## Usage")
lines.append("")
lines.append("- If the user mentions a skill by name (example: `openai-docs`), open the matching `SKILL.md` from the **File** path below and follow it.")
lines.append("- If multiple skills are mentioned, apply them in the order mentioned.")
lines.append("- Keep context small: do not load every skill body. Only open the skill(s) needed for the current task.")
lines.append("")
lines.append("## Skills")
lines.append("")
for name, desc, path in skills:
    if desc:
        lines.append(f"- `{name}`: {desc} (file: `{path}`)")
    else:
        lines.append(f"- `{name}` (file: `{path}`)")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"updated {OUT} ({len(skills)} skills)")
PY

echo "synced skills into: $DST"
