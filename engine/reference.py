"""
reference.py — the coach's reference files, served on demand (v7.31).

Until v7.30 these files sat in the Claude Project, so every conversation
loaded all of them (~100 KB, about 25,000 tokens) whether it needed them or
not. Now the coach asks for the one part it needs:

  zones          one methodology's zone table, with the reading guide of its
                 sport (output format, floors, the standard classes)
  architectures  the session-shape library, filtered by class and discipline
  intake         the athlete intake script (Phase 1)
  profile_template  the declared-profile template (config/athletes/_template.yaml)

Nothing here computes anything: it cuts the existing files at their headings
and returns the text as written. The files themselves are unchanged and are
still built by build_zone_tables.py.

Version: 1.0 (v7.31)
"""

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED = os.path.join(ROOT, "generated")
AUTHORS = os.path.join(ROOT, "config", "authors")
ATHLETES = os.path.join(ROOT, "config", "athletes")

ZONE_FILES = {"cycling": "Simple_Table_Cycling_Training_Zones.md",
              "running": "Simple_Table_Running_Training_Zones.md"}
TOPICS = ("zones", "architectures", "intake", "profile_template")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def methodologies():
    """{id: (name, sport)} for every author file."""
    out = {}
    for fn in sorted(os.listdir(AUTHORS)):
        if fn.endswith(".yaml") and not fn.startswith("_"):
            a = yaml.safe_load(_read(os.path.join(AUTHORS, fn))) or {}
            out[fn[:-5]] = (a.get("name"), a.get("sport"))
    return out


def _guide(text):
    """The reading guide at the top of a zone file, without the build notice
    (it speaks to whoever edits the repo, not to the coach)."""
    head = text[:text.index("## Methodology:")].rstrip().rstrip("-").rstrip()
    return re.sub(r"\n\*\*GENERATED FILE — DO NOT EDIT\.\*\*.*?(?=\n\n)", "", head, flags=re.S)


def zones(methodology):
    known = methodologies()
    mid = str(methodology or "").strip().lower()
    if mid not in known:
        raise ValueError(f"Unknown methodology '{methodology}'. Known: {', '.join(known)}.")
    name, sport = known[mid]
    text = _read(os.path.join(GENERATED, ZONE_FILES[sport]))
    start = text.find(f"## Methodology: {name}\n")
    if start < 0:
        raise ValueError(f"'{mid}' is not in {ZONE_FILES[sport]} — run: python build_zone_tables.py build")
    end = text.find("\n## Methodology:", start + 1)
    section = text[start:end if end > 0 else len(text)].rstrip().rstrip("-").rstrip()
    return {"methodology": mid, "sport": sport,
            "markdown": _guide(text) + "\n\n---\n\n" + section + "\n"}


def _norm(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def architectures(session_class=None, discipline=None):
    """The shape library. With a class and/or a discipline, only the
    architectures whose own Classes / Disciplines include them (the rule the
    prompt gives for choosing one); the combinations section always comes."""
    text = _read(os.path.join(GENERATED, "Session_Architectures.md"))
    cls, disc = _norm(session_class), _norm(discipline)
    first = text.index("\n## `")
    intro = re.sub(r"\n> GENERATED FILE.*?\n", "\n", text[:first]).strip()
    combo_at = text.find("\n## Combining architectures")
    body = text[first:combo_at if combo_at > 0 else len(text)]
    combos = text[combo_at:].strip() if combo_at > 0 else ""

    rows = {}
    for line in intro.splitlines():
        m = re.match(r"^\| `([a-z_]+)` — [^|]+\| ([^|]+)\| ([^|]+)\|", line)
        if m:
            rows[m.group(1)] = ({c.strip() for c in m.group(2).split(",")},
                                {d.strip() for d in m.group(3).split(",")})
    keep = [a for a, (cs, ds) in rows.items()
            if (not cls or cls in cs) and (not disc or disc in ds)]
    if not keep and (cls or disc):
        raise ValueError(f"No architecture lists class '{session_class}' and discipline "
                         f"'{discipline}'. Use a custom: shape and say why.")

    sections = re.split(r"\n(?=## `)", body.strip())
    picked = [s for s in sections if re.match(r"## `([a-z_]+)`", s)
              and re.match(r"## `([a-z_]+)`", s).group(1) in keep]
    lines = [l for l in intro.splitlines()
             if not re.match(r"^\| `([a-z_]+)`", l) or re.match(r"^\| `([a-z_]+)`", l).group(1) in keep]
    return {"session_class": session_class, "discipline": discipline, "architectures": keep,
            "markdown": "\n".join(lines) + "\n\n" + "\n\n".join(picked) + "\n\n" + combos + "\n"}


def get(topic, methodology=None, session_class=None, discipline=None):
    t = _norm(topic)
    if t == "zones":
        if not methodology:
            ms = methodologies()
            return {"topic": "zones", "methodologies":
                    [{"id": k, "name": n, "sport": s} for k, (n, s) in ms.items()]}
        return {"topic": "zones", **zones(methodology)}
    if t == "architectures":
        return {"topic": "architectures", **architectures(session_class, discipline)}
    if t == "intake":
        return {"topic": "intake", "markdown": _read(os.path.join(ATHLETES, "ATHLETE_INTAKE.md"))}
    if t == "profile_template":
        return {"topic": "profile_template",
                "yaml": _read(os.path.join(ATHLETES, "_template.yaml"))}
    raise ValueError(f"Unknown topic '{topic}'. Topics: {', '.join(TOPICS)}.")
