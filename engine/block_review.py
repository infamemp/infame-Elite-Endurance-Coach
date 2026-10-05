"""
block_review.py — the falsifier of a block, handed back on its review date.

When a block is approved, #SESSION records what would show its design wrong
and when to look:

    Would Show Wrong:  <an observable result — something #STATE, an activity
                        or a race can show>
    Review On:         <DD-MM-YYYY>
    Last Review:       <DD-MM-YYYY> · <happened | did not happen> · <one line>

Once the review date has passed and no review has been recorded on or after
it, `review_due()` returns the coach's own words so the first reply of the
conversation can put them back in front of the head coach.

What a review is for (taken from Prova Endurance's design manual): it asks
one question — did the thing the coach said would show the design wrong
happen? It is about the prescription, never about the athlete; it attributes
nothing (sleep, work, illness and weather moved at the same time); and one
review is one observation, never evidence for a rule.

Version: 1.0 (v7.22)
"""

import re
from datetime import date, datetime

_FIELD = re.compile(r"^\s*(Would Show Wrong|Review On|Last Review)\s*:\s*(.*?)\s*$",
                    re.I | re.M)
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})")
_EMPTY = {"", "none", "-", "—", "n/a", "null", "pending", "<", "ninguno", "ninguna"}


def _parse_date(text):
    m = _DATE.search(text or "")
    if not m:
        return None
    raw = m.group(1)
    fmt = "%Y-%m-%d" if raw[4] == "-" else "%d-%m-%Y"
    try:
        return datetime.strptime(raw, fmt).date()
    except ValueError:
        return None


def fields(session_text):
    """The three review fields of a #SESSION block (last occurrence wins)."""
    out = {}
    for key, value in _FIELD.findall(session_text or ""):
        out[key.lower()] = value
    falsifier = out.get("would show wrong", "")
    if falsifier.strip().lower() in _EMPTY or falsifier.startswith("<"):
        falsifier = ""
    return {
        "would_show_wrong": falsifier,
        "review_on": _parse_date(out.get("review on")),
        "last_review_text": out.get("last review", ""),
        "last_review_on": _parse_date(out.get("last review")),
    }


def review_due(session_text, today=None):
    """None, or {would_show_wrong, review_on, days_overdue, text} when the
    review date has passed and no review was recorded on or after it."""
    today = today or date.today()
    f = fields(session_text)
    if not f["would_show_wrong"] or not f["review_on"] or f["review_on"] > today:
        return None
    if f["last_review_on"] and f["last_review_on"] >= f["review_on"]:
        return None
    overdue = (today - f["review_on"]).days
    when = "today" if overdue == 0 else f"{overdue} day(s) ago"
    return {
        "would_show_wrong": f["would_show_wrong"],
        "review_on": f["review_on"].isoformat(),
        "days_overdue": overdue,
        "text": (f"Block review due ({when}, {f['review_on'].strftime('%d-%m-%Y')}). "
                 f"The design said it would be shown wrong if: {f['would_show_wrong']}"),
    }
