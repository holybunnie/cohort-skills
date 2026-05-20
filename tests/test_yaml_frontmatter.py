"""Actually parse every SKILL.md frontmatter as YAML. No visual inspection."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise ValueError("no leading '---' frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("no closing '---' frontmatter delimiter")
    return text[4:end]


def main() -> int:
    skill_files = sorted(ROOT.glob("skills/*/SKILL.md"))
    if not skill_files:
        print("no SKILL.md files found — nothing to validate", file=sys.stderr)
        return 1
    errors = 0
    for f in skill_files:
        try:
            fm_text = extract_frontmatter(f.read_text())
            fm = yaml.safe_load(fm_text)
        except Exception as e:
            print(f"FAIL  {f.relative_to(ROOT)}: {e}")
            errors += 1
            continue
        # Required keys
        for k in ("name", "description"):
            if k not in fm:
                print(f"FAIL  {f.relative_to(ROOT)}: missing key '{k}'")
                errors += 1
                break
        else:
            print(f"OK    {f.relative_to(ROOT)} — name={fm['name']!r}, desc_len={len(fm['description'])}")
    if errors:
        print(f"\n{errors} file(s) failed YAML frontmatter validation")
        return 1
    print(f"\nAll {len(skill_files)} SKILL.md frontmatter blocks parse as valid YAML.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
