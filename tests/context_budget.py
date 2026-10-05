"""
context_budget.py — what a coaching conversation loads before any design work.

Measures, from the repository itself:
  1. the Project instructions (the prompt);
  2. the Project knowledge files listed in the restore point's manifest;
  3. the MCP tool definitions the server sends to the model (needs `mcp`);
  4. one get_athlete_state answer, for a synthetic test athlete.

Tokens are estimated as characters / 4, the usual rule of thumb for English
text. The point is the before/after comparison, not the exact count.

Usage:
    python tests/context_budget.py
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tokens(chars):
    return round(chars / 4)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def project_files():
    rp = sorted(glob.glob(os.path.join(ROOT, "RESTORE_POINT_v*.md")))[-1]
    text = read(rp)
    block = text[text.index("## What the Project must contain"):text.index("## Machines")]
    start = block.index("Knowledge files")
    knowledge = block[start:block.index("\n- **", start)]
    return re.findall(r"`([^`]+\.(?:md|yaml))`", knowledge)


def tool_definitions():
    try:
        import asyncio
        sys.path.insert(0, ROOT)
        from mcp_server.server import build_app
    except Exception:  # noqa: BLE001 — optional: the mcp package may be absent
        return None
    tools = asyncio.run(build_app().list_tools())
    return sum(len(json.dumps(t.model_dump(exclude_none=True))) for t in tools), len(tools)


def state_answer():
    """Size of get_athlete_state for a synthetic athlete (no network)."""
    try:
        sys.path.insert(0, ROOT)
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import contextlib
        import io
        import make_fixtures
        with contextlib.redirect_stdout(io.StringIO()):
            make_fixtures.main()
        for sub in ("engine", "verify"):
            sys.path.insert(0, os.path.join(ROOT, sub))
        import build_state
        import shutil
        aid = "_budget_probe"
        dest = os.path.join(ROOT, "data", aid)
        os.makedirs(dest, exist_ok=True)
        shutil.copy2(os.path.join(ROOT, "tests", "fixtures", "cyclist_building", "athlete_data.json"),
                     os.path.join(dest, "athlete_data.json"))
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                build_state.build(aid, build_state.load_thresholds(), quiet=True)
            return len(read(os.path.join(dest, "state.md")))
        finally:
            shutil.rmtree(dest, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        print(f"   (state answer not measured: {exc})")
        return None


def main():
    rows = []
    prompt = read(os.path.join(ROOT, "Prompt", "infame_elite_endurance_coach.md"))
    rows.append(("Project instructions (prompt)", len(prompt)))
    total_files = 0
    for f in project_files():
        path = os.path.join(ROOT, f)
        n = len(read(path)) if os.path.exists(path) else 0
        total_files += n
    rows.append((f"Project knowledge files ({len(project_files())})", total_files))
    td = tool_definitions()
    if td:
        rows.append((f"MCP tool definitions ({td[1]} tools)", td[0]))
    st = state_answer()
    if st:
        rows.append(("get_athlete_state (#STATE, test athlete)", st))

    print("Context loaded at the start of a coaching conversation (approximate)\n")
    print(f"{'Part':45s} {'chars':>8s} {'~tokens':>8s}")
    for name, n in rows:
        print(f"{name:45s} {n:8d} {tokens(n):8d}")
    total = sum(n for _, n in rows)
    print(f"{'TOTAL':45s} {total:8d} {tokens(total):8d}")


if __name__ == "__main__":
    main()
