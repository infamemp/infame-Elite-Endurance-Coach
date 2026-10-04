"""
engine/knowledge.py — Infame Elite Endurance Coach v7.16
=========================================================
Book knowledge on demand. The book KBs (Knowledge/Principles/*.md and the
Palladino file) no longer live in the Claude Project: the coach asks for
exactly what it needs through the MCP tool `get_knowledge`, which calls this
module. Only the cited entries travel into the conversation — never a whole
book — so the Project stays small and the coach reads exact passages instead
of whatever Project search happens to retrieve.

Two file formats:
  * tagged (C01-C18): entries are `### [ID] title` blocks, e.g. TRPM-C06-001.
  * numbered (older):  sections are `## N. title`, cited as §N; their
    `### subheading` blocks are the searchable entries.

Sources are found by name: an author id from config/authors (coggan,
friel_cycling, daniels…), a doctrine source id (cusick, friel_tb, uphill,
mujika…), or a file stem (Jack_Daniels_Running_Formula). With catalog=True
the same source's Catalogs/ file is read instead: the author's own worked
sessions, workouts and plans — the coach's source of session ideas.

Three ways to read:
  * refs   — exact entries or sections: ["TRPM-C06-019", "§7"].
  * query  — keyword search inside one source (or across all), ranked.
  * nothing — a short table of contents of the source.
Every answer is capped (max_chars) and says when it was cut.
"""

from __future__ import annotations

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE = os.path.join(ROOT, "Knowledge")
CONFIG = os.path.join(ROOT, "config")

_ENTRY = re.compile(r"^### \[([A-Z]+-[CL]\d{1,2}-\d{3})\]\s*(.*)$")
_SECTION = re.compile(r"^## (\d{1,2})\.\s+(.*)$")
_SUB = re.compile(r"^### (.+)$")
_WORD = re.compile(r"[a-z0-9áéíóúñü'/-]{3,}")
STOP = {"the", "and", "for", "with", "how", "what", "when", "that", "this", "from",
        "are", "does", "into", "per", "vs", "versus", "not", "its", "his", "her"}

DEFAULT_MAX_CHARS = 12000
SECTION_MAX_CHARS = 6000


# ── registry ────────────────────────────────────────────────────────

def _book_files():
    """Every servable KB file: Knowledge/Principles/*.md plus .md files at the
    root of Knowledge/ (Palladino). Catalogs/ and archives are excluded."""
    out = []
    pdir = os.path.join(KNOWLEDGE, "Principles")
    if os.path.isdir(pdir):
        out += [os.path.join("Principles", f) for f in sorted(os.listdir(pdir)) if f.endswith(".md")]
    out += [f for f in sorted(os.listdir(KNOWLEDGE))
            if f.endswith(".md") and os.path.isfile(os.path.join(KNOWLEDGE, f))]
    return out


def registry():
    """{key: relative file} for every name a source can be asked by."""
    reg = {}
    for rel in _book_files():
        stem = os.path.splitext(os.path.basename(rel))[0]
        reg[stem.lower()] = rel
    adir = os.path.join(CONFIG, "authors")
    for fn in sorted(os.listdir(adir)):
        if not fn.endswith(".yaml") or fn.startswith("_"):
            continue
        with open(os.path.join(adir, fn), encoding="utf-8") as f:
            a = yaml.safe_load(f) or {}
        kf = a.get("knowledge_file")
        if kf and kf != "none":
            reg[a["id"]] = kf
    ddir = os.path.join(CONFIG, "doctrine")
    if os.path.isdir(ddir):
        for fn in sorted(os.listdir(ddir)):
            if fn.endswith(".yaml") and not fn.startswith("_"):
                with open(os.path.join(ddir, fn), encoding="utf-8") as f:
                    d = yaml.safe_load(f) or {}
                for s in d.get("sources", []):
                    reg.setdefault(s["id"], s["knowledge_file"])
    return reg


def source_names():
    """The short names (author and doctrine ids), for messages and the tool's list."""
    names = set()
    adir = os.path.join(CONFIG, "authors")
    for fn in os.listdir(adir):
        if fn.endswith(".yaml") and not fn.startswith("_"):
            with open(os.path.join(adir, fn), encoding="utf-8") as f:
                a = yaml.safe_load(f) or {}
            if a.get("knowledge_file") not in (None, "none"):
                names.add(a["id"])
    ddir = os.path.join(CONFIG, "doctrine")
    if os.path.isdir(ddir):
        for fn in os.listdir(ddir):
            if fn.endswith(".yaml") and not fn.startswith("_"):
                with open(os.path.join(ddir, fn), encoding="utf-8") as f:
                    names |= {x["id"] for x in (yaml.safe_load(f) or {}).get("sources", [])}
    return sorted(names)


def resolve(source):
    """Relative file for a source name, or None."""
    if not source:
        return None
    key = str(source).strip()
    reg = registry()
    for k in (key, key.lower(), os.path.splitext(os.path.basename(key))[0].lower()):
        if k in reg:
            return reg[k]
    return None


# ── parsing ─────────────────────────────────────────────────────────

def _read(rel):
    with open(os.path.join(KNOWLEDGE, rel), encoding="utf-8") as f:
        return f.read()


def parse(rel):
    """(format, entries, sections) for one file.
    entries: [{"id", "title", "section", "text"}] — tagged entries, or the
    ### blocks of a numbered file (id "§N › title").
    sections: {"§N": {"title", "text"}} for numbered files, {} otherwise."""
    lines = _read(rel).splitlines()
    tagged = any(_ENTRY.match(l) for l in lines)
    entries, sections = [], {}
    cur, cur_sec, sec_buf = None, None, None

    def close_entry():
        if cur:
            cur["text"] = "\n".join(cur["lines"]).strip()
            del cur["lines"]
            entries.append(cur)

    for line in lines:
        m_sec = _SECTION.match(line)
        if m_sec:
            close_entry()
            cur = None
            if sec_buf is not None:
                sections[cur_sec["ref"]]["text"] = "\n".join(sec_buf).strip()
            cur_sec = {"ref": f"§{m_sec.group(1)}", "title": m_sec.group(2).strip()}
            sections[cur_sec["ref"]] = {"title": cur_sec["title"], "text": ""}
            sec_buf = [line]
            continue
        if line.startswith("## "):            # a non-numbered top section (C01 …)
            close_entry()
            cur = None
            if sec_buf is not None:
                sections[cur_sec["ref"]]["text"] = "\n".join(sec_buf).strip()
                sec_buf = None
            continue
        if sec_buf is not None:
            sec_buf.append(line)
        m = _ENTRY.match(line) if tagged else None
        s = _SUB.match(line) if not tagged else None
        if m or s:
            close_entry()
            if m:
                cur = {"id": m.group(1), "title": m.group(2).strip(), "section": None,
                       "lines": [line]}
            else:
                ref = cur_sec["ref"] if cur_sec else None
                cur = {"id": f"{ref} › {s.group(1).strip()}" if ref else s.group(1).strip(),
                       "title": s.group(1).strip(), "section": ref, "lines": [line]}
            continue
        if cur:
            cur["lines"].append(line)
    close_entry()
    if sec_buf is not None and cur_sec:
        sections[cur_sec["ref"]]["text"] = "\n".join(sec_buf).strip()
    if tagged:
        sections = {}
    return ("tagged" if tagged else "numbered"), entries, sections


# ── reading ─────────────────────────────────────────────────────────

def _words(text):
    return [w for w in _WORD.findall(text.lower()) if w not in STOP]


def _score(entry, terms):
    title = entry["title"].lower()
    tags = " ".join(l for l in entry["text"].splitlines() if l.startswith("tags:")).lower()
    body = entry["text"].lower()
    score = 0
    for t in terms:
        score += 4 * title.count(t) + 2 * tags.count(t) + body.count(t)
    hit = sum(1 for t in terms if t in body or t in title)
    return score * hit                     # entries matching more terms rank first


def _cap(items, max_chars):
    out, used, cut = [], 0, False
    for it in items:
        if used + len(it["text"]) > max_chars:
            if not out:                    # always return at least part of one
                it = {**it, "text": it["text"][:max_chars] + "\n[…cut]"}
                out.append(it)
            cut = True
            break
        out.append(it)
        used += len(it["text"])
    return out, cut


def toc(rel):
    fmt, entries, sections = parse(rel)
    if fmt == "numbered":
        return [{"ref": k, "title": v["title"]} for k, v in sections.items()]
    counts = {}
    for e in entries:
        chap = e["id"].split("-")[1]
        counts[chap] = counts.get(chap, 0) + 1
    titles = dict(re.findall(r"^## (C\d{2}) (.+)$", _read(rel), re.M))
    return [{"ref": c, "title": titles.get(c, ""), "entries": n} for c, n in counts.items()]


def catalog_of(rel):
    """Catalogs/<same file name> for a Principles file, or None."""
    # Always "/" — os.path.join would give "Catalogs\\..." on Windows, and the
    # path is reported to the coach and compared as text.
    path = "Catalogs/" + os.path.basename(rel)
    return path if os.path.exists(os.path.join(KNOWLEDGE, path)) else None


def get(source=None, refs=None, query=None, max_entries=6, max_chars=DEFAULT_MAX_CHARS,
        catalog=False):
    """The answer for get_knowledge. Raises ValueError with a plain message
    when the source or a reference cannot be found. catalog=True reads the
    author's catalog (worked sessions, workouts, plans) instead of the
    principles: the source of session ideas, adapted to the athlete."""
    max_entries = max(1, min(int(max_entries or 6), 15))
    if source:
        rel = resolve(source)
        if not rel:
            raise ValueError(f"Unknown source '{source}'. Known: " + ", ".join(source_names()))
        if catalog:
            rel = catalog_of(rel)
            if not rel:
                raise ValueError(f"'{source}' has no catalog file.")
        files = [rel]
    else:
        if refs:
            raise ValueError("refs need a source (e.g. source='coggan').")
        files = sorted(set(registry().values()))
        if catalog:
            files = [c for c in (catalog_of(f) for f in files) if c]

    if refs:
        fmt, entries, sections = parse(files[0])
        by_id = {e["id"]: e for e in entries}
        found, missing = [], []
        for r in refs:
            r = str(r).strip()
            if r in by_id:
                found.append({"ref": r, "title": by_id[r]["title"], "text": by_id[r]["text"]})
            elif r in sections:
                text = sections[r]["text"]
                if len(text) > SECTION_MAX_CHARS:
                    subs = [e["title"] for e in entries if e["section"] == r]
                    text = (text[:SECTION_MAX_CHARS] + "\n[…section cut. Its subsections: "
                            + "; ".join(subs) + ". Ask with query=… for one of them.]")
                found.append({"ref": r, "title": sections[r]["title"], "text": text})
            else:
                missing.append(r)
        items, cut = _cap(found, max_chars)
        return {"source": source, "file": files[0], "format": fmt, "entries": items,
                "missing": missing, "truncated": cut}

    if query:
        terms = _words(query)
        if not terms:
            raise ValueError("query has no searchable words.")
        ranked = []
        for rel in files:
            _, entries, _ = parse(rel)
            for e in entries:
                sc = _score(e, terms)
                if sc:
                    ranked.append((sc, rel, e))
        ranked.sort(key=lambda x: -x[0])
        hits = [{"ref": e["id"], "title": e["title"], "text": e["text"],
                 **({} if source else {"file": rel})} for _, rel, e in ranked[:max_entries]]
        items, cut = _cap(hits, max_chars)
        return {"source": source, "file": files[0] if source else None,
                "query": query, "entries": items, "missing": [],
                "truncated": cut or len(ranked) > max_entries,
                "more_matches": max(0, len(ranked) - len(items))}

    if not source:
        reg = registry()
        names = {}
        for k, rel in reg.items():
            names.setdefault(rel, []).append(k)
        short = set(source_names())
        return {"sources": [{"file": rel, "names": sorted(n for n in v if n in short) or sorted(v)}
                            for rel, v in sorted(names.items())]}
    fmt, _, _ = parse(files[0])
    return {"source": source, "file": files[0], "format": fmt, "contents": toc(files[0])}
