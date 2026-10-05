"""test_mcp_server.py — regression suite for mcp_server/
==========================================================
Kept separate from tests/run_tests.py deliberately: the `mcp` SDK is an
optional dependency (see requirements.txt), and the 193 tests in
run_tests.py must keep passing with zero new dependencies for anyone who
never touches the MCP server. If `mcp` isn't installed, this file reports
that plainly and exits 0 rather than failing the whole suite over an
optional package.

Uses `config/athletes/TESTRAMP.yaml` — the repo's own committed,
non-real fixture athlete — for everything that writes files
(out/TESTRAMP/...) or validates a block. The two network-calling tools
(get_athlete_state/get_athlete_profile's fetch path, and push_block's live
send) are exercised the same way the rest of this repo already tests code
that talks to Intervals.icu: never over the real network. The fetch path is
exercised via a synthetic athlete_data.json (the same technique
tests/make_fixtures.py uses for the engine's own golden tests) that makes
the local cache fresh, so resolve_and_prep's "skip the network fetch"
branch runs for real; the live-send half of push_block is exercised with
requests.Session.post monkeypatched, never a real call, the same
verification method archive/RESTORE_POINT_v6.5.md §5 describes for the
original push_block.

Usage:
    python tests/test_mcp_server.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "verify"))

PASSED, FAILED = [], []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))


def equal(name, got, want):
    check(name, got == want, f"got {got!r}, expected {want!r}")


try:
    import mcp  # noqa: F401
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


AID = "TESTRAMP"  # the repo's own committed, non-real fixture athlete


def _seed_athlete_data(fresh: bool = True):
    """A minimal, valid athlete_data.json for TESTRAMP, shaped like
    tests/make_fixtures.py's fixtures, so build_state/build_profile can run
    on it for real without any network access. Cache freshness is keyed on
    the file's mtime (see common.is_cache_fresh's docstring for why, not
    the fetched_at field) — fresh=False backdates the file's own mtime by
    an hour past the default 60-minute window after writing it."""
    data = {
        "schema_version": 1,
        "fetched_at": date.today().isoformat(),
        "window_days": 180,
        "profile": {
            "id": AID, "name": "Test Fixture", "sex": "M", "weight": 70.0,
            "height": 178, "resting_hr": 48, "timezone": "UTC",
            "sport_settings": [{"types": ["Ride", "VirtualRide"], "ftp": 250,
                                 "lthr": 165, "max_hr": 188, "w_prime": 20000}],
        },
        "wellness": [],
        "pmc_series": [{"date": date.today().isoformat(), "ctl": 50.0, "atl": 45.0, "tsb": 5.0}],
        "activities": [],
        "curves": {},
        "events": [],
    }
    dest_dir = os.path.join(ROOT, "data", AID)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "athlete_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    if not fresh:
        old = __import__("time").time() - 30 * 86400  # 30 days ago, well past 60 minutes
        os.utime(path, (old, old))
    return dest_dir


def _cleanup():
    for p in (os.path.join(ROOT, "data", AID), os.path.join(ROOT, "out", "Test_Fixture"),
              os.path.join(ROOT, "out", "_test_relpath")):
        shutil.rmtree(p, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
# cancel_patch — verified against whatever mcp version is installed
# ══════════════════════════════════════════════════════════════════

def test_cancel_patch():
    from mcp_server import cancel_patch

    needed_before = cancel_patch.is_needed()
    applied = cancel_patch.apply()
    equal("cancel_patch: apply() reflects is_needed()'s finding", applied, needed_before)
    check("cancel_patch: apply() is idempotent", cancel_patch.apply() == applied)

    if needed_before:
        import anyio

        async def _check():
            r = await cancel_patch._make_probe_responder()  # noqa: SLF001 — testing the internal probe deliberately
            r.__exit__(None, None, None)  # must not raise once patched
            return True

        check("cancel_patch: the exact python-sdk#2610 probe no longer raises after apply()",
              anyio.run(_check))
    else:
        check("cancel_patch: correctly reports not needed on this SDK "
              "(either already fixed upstream, or RequestResponder no "
              "longer exists in this version)", True)


# ══════════════════════════════════════════════════════════════════
# guard — the SystemExit / stdout-leak / plain-exception safety net
# ══════════════════════════════════════════════════════════════════

def test_guard():
    from mcp_server.guard import ToolError, guarded

    @guarded
    def ok_fn(x):
        return {"ok": True, "x": x}

    @guarded
    def exits():
        sys.exit("simulated fatal CLI error")

    @guarded
    def blows_up():
        raise ValueError("simulated bug")

    @guarded
    def tool_error():
        raise ToolError("simulated expected failure")

    @guarded
    def noisy():
        print("this must never reach real stdout")
        return {"ok": True}

    equal("guard: a normal return passes through unchanged", ok_fn(5), {"ok": True, "x": 5})

    r = exits()
    equal("guard: SystemExit is caught, not propagated", r["ok"], False)
    equal("guard: SystemExit is reported with its own error_type", r["error_type"], "SystemExit")

    r = blows_up()
    equal("guard: a plain exception is caught, not propagated", r["ok"], False)
    equal("guard: exception type is reported", r["error_type"], "ValueError")

    r = tool_error()
    equal("guard: ToolError is caught and reported", r["ok"], False)
    equal("guard: ToolError type is reported", r["error_type"], "ToolError")

    real_stdout = sys.stdout
    capture = __import__("io").StringIO()
    sys.stdout = capture
    try:
        r = noisy()
    finally:
        sys.stdout = real_stdout
    equal("guard: a tool's own print() never reaches the real stdout", capture.getvalue(), "")
    equal("guard: the tool's own result still comes through", r, {"ok": True})


# ══════════════════════════════════════════════════════════════════
# common — cache/staleness and the resolve_and_prep orchestration
# ══════════════════════════════════════════════════════════════════

def test_common():
    from mcp_server import common

    _seed_athlete_data(fresh=True)
    check("common: a just-fetched athlete_data.json reads as cache-fresh",
          common.is_cache_fresh(AID))

    _seed_athlete_data(fresh=False)
    check("common: a 30-day-old athlete_data.json reads as stale",
          not common.is_cache_fresh(AID))

    # Re-seed fresh so resolve_and_prep's cache-hit branch actually runs —
    # this is the one branch testable without real Intervals.icu access.
    _seed_athlete_data(fresh=True)
    info = common.resolve_and_prep(AID, force_refresh=False)
    equal("common: resolve_and_prep takes the cache-hit path on fresh local data",
          info["cache_hit"], True)
    equal("common: resolve_and_prep resolves the name from cached profile data",
          info["name"], "Test Fixture")
    check("common: resolve_and_prep still renders state.md on a cache hit",
          os.path.exists(os.path.join(ROOT, "data", AID, "state.md")))
    check("common: resolve_and_prep delivers to out/<name>/",
          os.path.exists(os.path.join(info["out_dir"], "state.md")))


# ══════════════════════════════════════════════════════════════════
# tools_read — get_athlete_state / get_athlete_profile / list_roster
# ══════════════════════════════════════════════════════════════════

def test_tools_read():
    from mcp_server.tools_read import get_athlete_state, get_athlete_profile, list_roster

    _seed_athlete_data(fresh=True)
    r = get_athlete_state(AID)
    equal("tools_read: get_athlete_state succeeds on a cache-fresh fixture", r.get("ok"), True)
    equal("tools_read: get_athlete_state reports the cache hit", r.get("cache_hit"), True)
    check("tools_read: get_athlete_state's markdown is the real state.md content",
          "STATE" in (r.get("markdown") or "").upper())

    r2 = get_athlete_profile(AID)
    equal("tools_read: get_athlete_profile succeeds on the same fixture", r2.get("ok"), True)
    check("tools_read: get_athlete_profile's markdown mentions the athlete",
          "Test Fixture" in (r2.get("markdown") or ""))

    r3 = get_athlete_state("no-such-athlete-id", force_refresh=False)
    equal("tools_read: an unknown, uncached athlete_id fails cleanly rather than crashing",
          r3.get("ok"), False)

    r4 = list_roster()
    check("tools_read: list_roster returns something (either roster.md content, "
          "or a clean 'not found yet' error, never a crash)",
          "ok" in r4)


def _write_pairing_data(paired=True):
    """Add planned events and activities to the seeded TESTRAMP data, keeping
    the file's mtime fresh so the cache-hit path still runs. paired=False
    writes events without ids, the shape cached before pairing was recorded."""
    from datetime import timedelta
    path = os.path.join(ROOT, "data", AID, "athlete_data.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    day = lambda n: (date.today() - timedelta(days=n)).isoformat()
    ev = lambda i, n: dict({"date": day(n), "name": f"S{i}", "category": "WORKOUT",
                            "planned_load": 50, "planned_time": 3600},
                           **({"id": i} if paired else {}))
    data["recent_sessions"] = [ev(1, 4), ev(2, 3)]
    data["activities"] = [{"date": day(4), "type": "Ride", "training_load": 45,
                           "moving_time": 3500, "paired_event_id": 1,
                           "compliance": 90, "rpe": 6}]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_tools_roster_and_execution():
    import mcp_server.tools_read as tr

    _seed_athlete_data(fresh=True)
    tr.get_athlete_state(AID)          # writes data/TESTRAMP/state.json

    r = tr.roster_overview()
    equal("roster_overview: succeeds once an athlete has been prepared", r.get("ok"), True)
    row = next((a for a in r.get("athletes", []) if a["athlete_id"] == AID), None)
    check("roster_overview: the prepared athlete is a row, prepared, with its name",
          bool(row) and row["prepared"] is True and row["name"] == "Test Fixture", row)
    check("roster_overview: the markdown table names the athlete",
          "Test Fixture" in (r.get("markdown") or ""))

    _seed_athlete_data(fresh=True)
    _write_pairing_data(paired=True)
    r = tr.get_execution(AID, days=28)
    equal("get_execution: succeeds on a cache-fresh fixture", r.get("ok"), True)
    equal("get_execution: no refresh when the cache can already pair",
          r.get("refreshed_for_pairing"), False)
    ex = r.get("execution") or {}
    equal("get_execution: paired and unpaired sessions counted from paired_event_id",
          (ex["totals"]["paired"], ex["totals"]["unpaired"]), (1, 1))
    check("get_execution: the markdown reports planned vs done",
          "Planned vs done" in (r.get("markdown") or ""))

    # Cached data from before pairing was recorded: refreshed once, automatically.
    _seed_athlete_data(fresh=True)
    _write_pairing_data(paired=False)
    real, calls = tr.resolve_and_prep, []

    def _fake(aid, days=180, force_refresh=False):
        calls.append(force_refresh)
        if force_refresh:
            _write_pairing_data(paired=True)   # stands in for the network fetch
        return real(aid, days=days, force_refresh=False)

    tr.resolve_and_prep = _fake
    try:
        r = tr.get_execution(AID)
    finally:
        tr.resolve_and_prep = real
    equal("get_execution: cache without event ids triggers exactly one forced refresh",
          calls, [False, True])
    equal("get_execution: and reports that it refreshed", r.get("refreshed_for_pairing"), True)
    check("get_execution: after the refresh the answer is available",
          (r.get("execution") or {}).get("available") is True)

    r = tr.get_execution("no-such-athlete-id")
    equal("get_execution: an unknown, uncached athlete fails cleanly", r.get("ok"), False)


class _Resp:
    def __init__(self, data=None, status=200):
        self._d, self.status_code, self.text = data, status, json.dumps(data)

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    """Stands in for the Intervals.icu HTTP session: every call is recorded,
    nothing touches the network. `routes` maps (METHOD, path) to a callable
    (kwargs -> _Resp) or to a fixed payload."""

    def __init__(self, routes, base):
        self.routes, self.base, self.calls = routes, base, []

    def _do(self, method, url, **kw):
        path = url.replace(self.base, "")
        self.calls.append((method, path, kw))
        h = self.routes.get((method, path))
        if h is None:
            return _Resp({"error": f"no route {method} {path}"}, 404)
        return h(kw) if callable(h) else _Resp(h)

    def get(self, url, **kw): return self._do("GET", url, **kw)
    def post(self, url, **kw): return self._do("POST", url, **kw)
    def put(self, url, **kw): return self._do("PUT", url, **kw)

    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PUT")]


def _with_fake(routes):
    import fetch_athlete_data as fad
    fake = _FakeSession(routes, fad.BASE_URL)
    real = fad.make_session
    fad.make_session = lambda: fake
    return fake, lambda: setattr(fad, "make_session", real)


def test_tools_coach():
    from datetime import timedelta
    from mcp_server.tools_coach import post_activity_comment, remove_block, update_threshold
    from mcp_server import common

    # ── post_activity_comment ──
    act = {"icu_athlete_id": AID, "name": "Aerobico", "start_date_local": "2026-09-25T07:00:00",
           "type": "Ride"}
    fake, restore = _with_fake({("GET", "/activity/i55"): act,
                                ("POST", "/activity/i55/messages"): {"id": 1}})
    try:
        r = post_activity_comment(AID, "i55", "Buen trabajo hoy.")
        equal("comment: default is a dry run", (r.get("dry_run"), r.get("sent")), (True, False))
        equal("comment: dry run shows which activity it would land on",
              r["activity"]["name"], "Aerobico")
        equal("comment: dry run wrote nothing", fake.writes(), [])
        post_activity_comment(AID, "i55", "x", dry_run=False, confirm=False)
        post_activity_comment(AID, "i55", "x", dry_run=True, confirm=True)
        equal("comment: one open gate is not enough", fake.writes(), [])
        r = post_activity_comment(AID, "i55", "Buen trabajo hoy.", dry_run=False, confirm=True)
        equal("comment: both gates open posts once, with the text as given",
              [(c[0], c[1], c[2].get("json")) for c in fake.writes()],
              [("POST", "/activity/i55/messages", {"content": "Buen trabajo hoy."})])
        equal("comment: live call reports it was sent", r.get("sent"), True)
        equal("comment: an empty comment is refused",
              post_activity_comment(AID, "i55", "   ").get("ok"), False)
        equal("comment: an over-long comment is refused",
              post_activity_comment(AID, "i55", "x" * 2001).get("ok"), False)
        equal("comment: a malformed activity id is refused",
              post_activity_comment(AID, "i55/../x", "hola").get("ok"), False)
    finally:
        restore()
    fake, restore = _with_fake({("GET", "/activity/i77"): dict(act, icu_athlete_id="OTHER"),
                                ("POST", "/activity/i77/messages"): {"id": 2}})
    try:
        r = post_activity_comment(AID, "i77", "hola", dry_run=False, confirm=True)
        equal("comment: an activity of another athlete is refused, even with both gates open",
              (r.get("ok"), fake.writes()), (False, []))
    finally:
        restore()

    # ── update_threshold ──
    _seed_athlete_data(fresh=True)
    state = {"id": 9, "types": ["Ride"], "ftp": 250, "lthr": 165, "max_hr": 188,
             "threshold_pace": 3.5, "pace_units": "MINS_KM"}

    def _put(kw):
        state.update(kw["json"])
        return _Resp(dict(state))

    routes = {("GET", "/athlete/" + AID + "/sport-settings/Ride"): lambda kw: _Resp(dict(state)),
              ("PUT", "/athlete/" + AID + "/sport-settings/9"): _put}
    fake, restore = _with_fake(routes)
    try:
        r = update_threshold(AID, "Ride", "ftp", 260)
        equal("threshold: dry run shows old -> new", (r["old"], r["new"], r["sent"]), (250, 260, False))
        equal("threshold: dry run wrote nothing", fake.writes(), [])
        r = update_threshold(AID, "Ride", "ftp", 260, dry_run=False, confirm=True)
        w = fake.writes()
        equal("threshold: live call sends only the one field",
              [(c[0], c[1], c[2]["json"]) for c in w],
              [("PUT", "/athlete/" + AID + "/sport-settings/9", {"ftp": 260})])
        equal("threshold: FTP change does not recalculate HR zones",
              w[0][2]["params"]["recalcHrZones"], "false")
        equal("threshold: the change is re-read and verified", (r["verified"], r["now_in_intervals"]), (True, 260))
        check("threshold: the local cache is marked stale so #STATE re-fetches",
              r["cache_marked_stale"] is True and not common.is_cache_fresh(AID))
        n = len(fake.writes())
        r = update_threshold(AID, "Ride", "ftp", 260, dry_run=False, confirm=True)
        equal("threshold: setting the value it already has changes nothing",
              (r["changed"], len(fake.writes())), (False, n))
        update_threshold(AID, "Ride", "lthr", 170, dry_run=False, confirm=True)
        equal("threshold: LTHR change recalculates HR zones",
              fake.writes()[-1][2]["params"]["recalcHrZones"], "true")
        r = update_threshold(AID, "Ride", "threshold_pace", "4:30")
        check("threshold: M:SS in min/km becomes m/s (4:30/km = 3.7037 m/s)",
              abs(r["new"] - 3.7037) < 1e-3 and r["old_display"] == "4:46 /km", r)
        equal("threshold: an implausible value is refused",
              update_threshold(AID, "Ride", "ftp", 2600).get("ok"), False)
        equal("threshold: a field that is not allowed is refused",
              update_threshold(AID, "Ride", "w_prime", 20000).get("ok"), False)
        equal("threshold: a non-numeric value is refused",
              update_threshold(AID, "Ride", "ftp", "mucho").get("ok"), False)
        state["pace_units"] = "SECS_100M"
        equal("threshold: M:SS in a pace unit that is not min/km or min/mile is refused",
              update_threshold(AID, "Ride", "threshold_pace", "1:40").get("ok"), False)
    finally:
        restore()

    # ── remove_block ──
    day = lambda n: (date.today() + timedelta(days=n)).isoformat() + "T00:00:00"
    cal = [
        {"id": 1, "category": "WORKOUT", "start_date_local": day(1), "name": "A",
         "external_id": f"infame-{AID}-x-w1"},
        {"id": 2, "category": "WORKOUT", "start_date_local": day(3), "name": "B",
         "external_id": f"infame-{AID}-y-w1"},
        {"id": 3, "category": "WORKOUT", "start_date_local": day(2), "name": "athlete's own",
         "external_id": None},
        {"id": 4, "category": "WORKOUT", "start_date_local": day(2), "name": "other athlete's",
         "external_id": "infame-OTHER-z-w1"},
        {"id": 5, "category": "RACE_A", "start_date_local": day(9), "name": "race",
         "external_id": f"infame-{AID}-r-w1"},
        {"id": 6, "category": "WORKOUT", "start_date_local": day(0), "name": "today",
         "external_id": f"infame-{AID}-t-w1"},
    ]
    live = list(cal)

    def _bulk_delete(kw):
        gone = {d["id"] for d in kw["json"]}
        live[:] = [e for e in live if e["id"] not in gone]
        return _Resp({"eventsDeleted": len(gone)})

    ev_path = "/athlete/" + AID + "/events"
    fake, restore = _with_fake({("GET", ev_path): lambda kw: _Resp(list(live)),
                                ("PUT", ev_path + "/bulk-delete"): _bulk_delete})
    try:
        r = remove_block(AID)
        equal("remove: dry run lists only this system's WORKOUT sessions from tomorrow",
              [x["id"] for x in r["to_remove"]], [1, 2])
        equal("remove: everything else is left alone and counted", r["left_alone"], 4)
        equal("remove: dry run deleted nothing", fake.writes(), [])
        equal("remove: today is refused as a start date",
              remove_block(AID, from_date=date.today().isoformat()).get("ok"), False)
        remove_block(AID, dry_run=False, confirm=False)
        equal("remove: one open gate is not enough", fake.writes(), [])
        r = remove_block(AID, dry_run=False, confirm=True)
        equal("remove: live call deletes exactly the two uploaded sessions, by id",
              [c[2]["json"] for c in fake.writes()], [[{"id": 1}, {"id": 2}]])
        equal("remove: the calendar is re-read and the delete verified",
              (r["verified"], r["still_on_calendar"]), (True, []))
        equal("remove: the athlete's own, another athlete's, race and today survive",
              sorted(e["id"] for e in live), [3, 4, 5, 6])
        n = len(fake.writes())
        r = remove_block(AID, dry_run=False, confirm=True)
        equal("remove: nothing left to remove -> no delete call",
              (r["count"], len(fake.writes())), (0, n))
    finally:
        restore()


# ══════════════════════════════════════════════════════════════════
# tools_write — save_continuity / save_race_result / save_block
# ══════════════════════════════════════════════════════════════════

def test_tools_write():
    from mcp_server.tools_write import save_continuity, save_race_result, save_block

    r = save_continuity(AID, "not a session block at all", athlete_name="Test Fixture")
    equal("tools_write: save_continuity rejects text with no #SESSION", r.get("ok"), False)

    r = save_continuity(AID, "#SESSION\nActive Phase: 4\n", athlete_name="Test Fixture")
    equal("tools_write: save_continuity rejects a #SESSION with no #END", r.get("ok"), False)

    good = "#SESSION\nActive Phase: 4\nCurrent Block: Base 2\n#END\n"
    r = save_continuity(AID, good, athlete_name="Test Fixture")
    equal("tools_write: save_continuity accepts a well-formed #SESSION...#END block",
          r.get("ok"), True)
    with open(os.path.join(ROOT, "out", "Test_Fixture", "continuity.md"), encoding="utf-8") as f:
        written = f.read()
    check("tools_write: save_continuity's content round-trips to disk verbatim",
          "Current Block: Base 2" in written)

    r = save_race_result(AID, "not-a-date", "Finished 3rd", athlete_name="Test Fixture")
    equal("tools_write: save_race_result rejects a malformed date", r.get("ok"), False)

    r = save_race_result(AID, "2026-05-01", "Finished 3rd overall, felt strong.",
                          athlete_name="Test Fixture")
    equal("tools_write: save_race_result accepts a valid date + body", r.get("ok"), True)

    # Round-trip through coach.py's own, unmodified read_race_notes() — the
    # real determinism check: this tool's output must be readable by code
    # that was never told this tool exists.
    import coach
    from datetime import date as _date
    notes = coach.read_race_notes("Test_Fixture", _date(2026, 4, 1), _date(2026, 6, 1))
    check("tools_write: coach.py's own read_race_notes() finds the block "
          "this tool wrote, unmodified", notes is not None and len(notes) == 1)
    check("tools_write: the block content coach.py reads back is correct",
          notes is not None and "Finished 3rd overall" in notes[0])

    r = save_race_result(AID, "2026-05-01", "Date: 2026-06-01\nConflicting date on purpose",
                          athlete_name="Test Fixture")
    equal("tools_write: save_race_result rejects a body with its own conflicting Date: line",
          r.get("ok"), False)

    r = save_block(AID, "[Week] 3\n...", athlete_name="Test Fixture")
    equal("tools_write: save_block writes today's block file", r.get("ok"), True)
    expected = os.path.join(ROOT, "out", "Test_Fixture", "blocks",
                             f"{date.today().isoformat()}_bloque.md")
    check("tools_write: save_block's file exists where documented",
          os.path.exists(expected))


# ══════════════════════════════════════════════════════════════════
# tools_validate — validate_block against the repo's own known fixtures
# ══════════════════════════════════════════════════════════════════

def test_tools_validate():
    from mcp_server.tools_validate import validate_block

    good = os.path.join(ROOT, "tests", "blocks", "good_trainer_coggan.md")
    bad = os.path.join(ROOT, "tests", "blocks", "bad_road.md")

    with tempfile.TemporaryDirectory() as tmp:
        good_copy = os.path.join(tmp, "good.md")
        bad_copy = os.path.join(tmp, "bad.md")
        shutil.copy2(good, good_copy)
        shutil.copy2(bad, bad_copy)

        r = validate_block(file_path=good_copy)
        equal("tools_validate: a known-good block passes", r.get("passed"), True)
        equal("tools_validate: a known-good block exits 0", r.get("exit_code"), 0)

        r = validate_block(file_path=bad_copy)
        equal("tools_validate: a known-bad block is blocked", r.get("passed"), False)
        check("tools_validate: the report names at least one real failure code",
              "FAIL [" in (r.get("report") or ""))

        r = validate_block(file_path=good_copy, fill_tss=True)
        equal("tools_validate: --fill-tss still passes on the known-good block",
              r.get("passed"), True)
        with open(good_copy, encoding="utf-8") as f:
            filled = f.read()
        check("tools_validate: fill_tss=True actually wrote a computed TSS to disk",
              "pending" not in filled.lower() or "Estimated TSS" not in filled)

        blk = os.path.join(tmp, "flat.md")
        shutil.copy2(os.path.join(ROOT, "tests", "blocks", "load_monotony_flat.md"), blk)
        r = validate_block(file_path=blk, week_targets={"2027-03-01": 1000})
        check("tools_validate: week_targets reaches the validator and only warns",
              "Weekly TSS target" in (r.get("report") or "")
              and "CHK-LOAD-TARGET" in (r.get("report") or "") and r.get("passed") is True)
        r = validate_block(file_path=blk)
        check("tools_validate: no week_targets, no target section",
              "Weekly TSS target" not in (r.get("report") or ""))

        _test_windows_style_narrow_codec(validate_block, good)


# On Windows, a Python child process whose stdout is a pipe (not a real
# console) defaults to the legacy ANSI codepage (cp1252) unless told
# otherwise — and validate_block.py prints Unicode box-drawing characters
# ("── Session 1: ...") on every normal run, which cp1252 cannot encode.
# The child crashed with an uncaught UnicodeEncodeError before it could
# report anything, and tools_validate.py reported the resulting nonzero
# exit as `passed: False` — indistinguishable from a real hard-constraint
# failure. Fixed by forcing PYTHONIOENCODING=utf-8 (and PYTHONUTF8=1) in
# the child's own environment in tools_validate.py, rather than relying on
# the platform default.
#
# This sandbox is Linux, where a bare subprocess.run() typically doesn't
# reproduce this — which is exactly why the original test suite (developed
# and run here) didn't catch it. A forced "C" locale with Python's own
# locale coercion disabled reproduces the same class of bug portably: it
# collapses the child's stdout to a narrow, ASCII-only codec, the same
# functional condition cp1252 puts a Windows child in (a real, printed
# Unicode character the encoding can't represent), so this is a genuine
# regression test for the mechanism, not a Windows-only assertion that
# can't be checked here.
_HOSTILE_LOCALE_ENV = {
    "LC_ALL": "C", "LANG": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0",
}


def _test_windows_style_narrow_codec(validate_block, good_block_path):
    # Control: prove the vulnerability is real and this mechanism actually
    # stresses it — calling validate_block.py directly, exactly as
    # tools_validate.py used to (no PYTHONIOENCODING override), under the
    # hostile locale, must crash with an uncaught UnicodeEncodeError.
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "control.md")
        shutil.copy2(good_block_path, copy)
        script = os.path.join(ROOT, "verify", "validate_block.py")
        hostile_env = dict(os.environ, **_HOSTILE_LOCALE_ENV)
        hostile_env.pop("PYTHONIOENCODING", None)
        proc = subprocess.run(
            [sys.executable, script, copy, "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=ROOT, env=hostile_env,
        )
        check("windows-encoding control: validate_block.py itself crashes under a "
              "hostile locale with no PYTHONIOENCODING override (proves the "
              "test mechanism reproduces the real bug class)",
              proc.returncode != 0 and "UnicodeEncodeError" in proc.stderr,
              f"exit={proc.returncode}, stderr={proc.stderr[-300:]}")

    # The fix: run the same block through the real validate_block tool,
    # with the hostile locale inherited from THIS process's own
    # environment (simulating a coach's machine where Desktop launches the
    # server under exactly this kind of narrow default) — tools_validate.py
    # must still force UTF-8 on the child regardless, so the block passes
    # cleanly with no UnicodeEncodeError anywhere in the report.
    original_env = dict(os.environ)
    try:
        os.environ.update(_HOSTILE_LOCALE_ENV)
        os.environ.pop("PYTHONIOENCODING", None)
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "fixed.md")
            shutil.copy2(good_block_path, copy)
            r = validate_block(file_path=copy)
    finally:
        os.environ.clear()
        os.environ.update(original_env)

    equal("windows-encoding fix: validate_block tool still passes under a "
          "hostile inherited locale", r.get("passed"), True)
    check("windows-encoding fix: no UnicodeEncodeError anywhere in the report",
          "UnicodeEncodeError" not in (r.get("report") or ""),
          r.get("report", "")[-300:])


def test_relative_file_path_resolves_against_root():
    """A caller-supplied, relative file_path must resolve against ROOT
    (common.py's ROOT, computed from __file__ and therefore cwd-
    independent), never against the server process's own working
    directory. Confirmed on Windows via Claude Desktop: the same relative
    path that worked when validate_block() was called from a fresh
    interpreter launched at ROOT failed with "File not found" from the
    live server process, even though the file existed exactly there --
    the configured claude_desktop_config.json "cwd" field did not
    actually govern the launched process's real working directory. The
    fix must not depend on any process ever honoring "cwd" at all, so
    this test proves it works by actually changing this test process's
    own cwd to somewhere else entirely before calling either tool.

    validate_block.py and push_block.py both accept a file_path
    parameter (the only two tools in this package that do — every other
    tool builds its paths from ROOT/OUT internally and was never
    exposed to this)."""
    from mcp_server.tools_push import push_block
    from mcp_server.tools_validate import validate_block

    good = os.path.join(ROOT, "tests", "blocks", "good_trainer_coggan.md")
    # The file has to actually live somewhere under ROOT for a *relative*
    # path to be meaningful at all -- a relative path from an arbitrary
    # cwd could never reach a file under /tmp.
    rel_dir = os.path.join(ROOT, "out", "_test_relpath")
    os.makedirs(rel_dir, exist_ok=True)
    original_cwd = os.getcwd()
    try:
        dest = os.path.join(rel_dir, "block.md")
        shutil.copy2(good, dest)
        relative = os.path.relpath(dest, ROOT)

        with tempfile.TemporaryDirectory() as elsewhere:
            # cwd must be restored to original_cwd BEFORE this `with`
            # block's __exit__ tries to delete `elsewhere` — on Windows, a
            # directory cannot be deleted while it is the process's
            # current working directory (PermissionError: [WinError 32],
            # confirmed reproducible: it aborted the whole test run before
            # any pass/fail count could even print). Restoring cwd in the
            # OUTER finally, after this `with` block has already exited,
            # is too late — the delete has already failed by then. This
            # inner try/finally is what actually has to do it.
            try:
                os.chdir(elsewhere)
                check("relative file_path: the test process's cwd is "
                      "genuinely not ROOT (proves this test actually "
                      "exercises the bug)",
                      os.path.realpath(os.getcwd()) != os.path.realpath(ROOT))

                r = validate_block(file_path=relative)
                equal("validate_block: a relative file_path resolves against "
                      "ROOT, not the process cwd", r.get("passed"), True)

                r2 = push_block(AID, file_path=relative)
                equal("push_block: a relative file_path resolves against "
                      "ROOT, not the process cwd", r2.get("ok"), True)
            finally:
                os.chdir(original_cwd)
    finally:
        # Redundant with the inner restore on every path that reaches it,
        # but cheap, idempotent, and the real safety net if something
        # raised before the `with` block above was ever entered.
        os.chdir(original_cwd)
        shutil.rmtree(rel_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
# tools_push — dry-run by default, double-gated for a real send
# ══════════════════════════════════════════════════════════════════

def test_tools_push():
    from mcp_server.tools_push import push_block

    good = os.path.join(ROOT, "tests", "blocks", "good_trainer_coggan.md")
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "block.md")
        shutil.copy2(good, copy)

        r = push_block(AID, file_path=copy)
        equal("tools_push: default call (no args) never sends", r.get("sent"), False)
        equal("tools_push: default call reports dry_run=True", r.get("dry_run"), True)
        check("tools_push: dry-run still constructs at least one event", r.get("count", 0) > 0)

        # A double day: the same session written twice on one date. Before
        # the fix both got the same external_id and upsert=true kept only
        # the last one. The first keeps the original id (already-pushed
        # events still match); the second gets a -2 suffix.
        with open(good, encoding="utf-8") as f:
            one_session = f.read().strip()
        double = os.path.join(tmp, "double_day.md")
        with open(double, "w", encoding="utf-8") as f:
            f.write(one_session + "\n\n" + one_session + "\n")
        r2 = push_block(AID, file_path=double)
        ids = [e.get("external_id") for e in r2.get("events", [])]
        equal("tools_push: a double day builds two events", len(ids), 2)
        equal("tools_push: two sessions on one date never share an external_id",
              len(set(ids)), 2)
        equal("tools_push: first session of a date keeps the original id",
              ids[0] if ids else None, f"infame-{AID}-2026-08-24-w03")
        equal("tools_push: second session of that date gets a -2 suffix",
              ids[1] if len(ids) > 1 else None, f"infame-{AID}-2026-08-24-w03-2")

        r = push_block(AID, file_path=copy, dry_run=False)
        equal("tools_push: dry_run=False alone (confirm still False) still never sends",
              r.get("sent"), False)

        r = push_block(AID, file_path=copy, confirm=True)
        equal("tools_push: confirm=True alone (dry_run still True) still never sends",
              r.get("sent"), False)

        # Only with BOTH gates open, and only against a mocked POST — never
        # a real network call, the same verification method the original
        # tool's own restore point describes using.
        import fetch_athlete_data as fad
        import requests

        calls = []

        class _FakeResponse:
            status_code = 200

            def raise_for_status(self):
                return None

        def _fake_post(self, url, params=None, json=None, timeout=None):
            calls.append({"url": url, "params": params, "json": json})
            return _FakeResponse()

        original_post = requests.Session.post
        requests.Session.post = _fake_post
        try:
            r = push_block(AID, file_path=copy, dry_run=False, confirm=True)
        finally:
            requests.Session.post = original_post

        equal("tools_push: both gates open actually sends (against the mock)",
              r.get("sent"), True)
        equal("tools_push: exactly one bulk-events POST was made", len(calls), 1)
        check("tools_push: the mocked call hit the documented bulk-events endpoint",
              calls and calls[0]["url"] == f"{fad.BASE_URL}/athlete/{AID}/events/bulk")
        check("tools_push: upsert=true was passed",
              calls and calls[0]["params"] == {"upsert": "true"})
        check("tools_push: internal 'type_inferred' annotation is stripped "
              "from the actual wire payload",
              calls and all("type_inferred" not in e for e in calls[0]["json"]))


# ══════════════════════════════════════════════════════════════════
# tools_push — refuses to send a block validate_block reports BLOCKED
# ══════════════════════════════════════════════════════════════════
# Found during manual end-to-end testing on this branch: nothing stopped
# push_block(dry_run=False, confirm=True) from sending a block that had
# just been reported BLOCKED by validate_block — the two tools were fully
# independent, a gap that only mattered once validating and uploading
# stopped being two separate manual CLI commands a whole conversation turn
# apart. Confirmed directly: a real BLOCKED block (genuine HC-METRIC
# failures) was assembled and would have been sent; it was only rejected
# by Intervals.icu itself (403, invalid test credentials), not by this
# tool. push_block now runs the same check internally before its live
# send and must refuse without an explicit override.

def test_tools_push_refuses_blocked_block():
    from mcp_server.tools_push import push_block

    bad = os.path.join(ROOT, "tests", "blocks", "bad_road.md")
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "bad.md")
        shutil.copy2(bad, copy)

        import fetch_athlete_data as fad
        import requests

        calls = []

        class _FakeResponse:
            status_code = 200

            def raise_for_status(self):
                return None

        def _fake_post(self, url, params=None, json=None, timeout=None):
            calls.append({"url": url, "params": params, "json": json})
            return _FakeResponse()

        original_post = requests.Session.post
        requests.Session.post = _fake_post
        try:
            # push_block is @guarded, so the ToolError this raises internally
            # is caught at the tool boundary and comes back as an error
            # dict, not a raised exception — the same shape every other
            # tool's expected failure takes.
            r = push_block(AID, file_path=copy, dry_run=False, confirm=True)
            equal("push_block: refuses a known-BLOCKED block with both "
                  "gates open and no override", r.get("ok"), False)
            equal("push_block: the refusal is reported as a ToolError",
                  r.get("error_type"), "ToolError")
            check("push_block: the refusal names it as blocked",
                  "BLOCKED" in (r.get("error") or ""), r.get("error", "")[:200])
            equal("push_block: refusing a BLOCKED block makes no network call",
                  len(calls), 0)

            r = push_block(AID, file_path=copy, dry_run=False, confirm=True,
                            override_validation=True)
            equal("push_block: override_validation=True proceeds anyway "
                  "(against the mock)", r.get("sent"), True)
            equal("push_block: override still makes exactly one call", len(calls), 1)
        finally:
            requests.Session.post = original_post


# ══════════════════════════════════════════════════════════════════
# MCP-first workflow (v7.3) — what the prompt now relies on
# ══════════════════════════════════════════════════════════════════
# 1. get_athlete_state carries continuity.md, so one call opens a
#    conversation (no file dragging).
# 2. save_block(week=N) keeps each week in its own file; validate_block
#    and push_block default to the most recently saved one.
# 3. push_block sends ISO dates. The first real push (21-sep-2026) sent the
#    header's DD-MM-YYYY as-is and Intervals.icu answered HTTP 500.

def test_mcp_first_workflow():
    import re as _re
    import time as _time
    from mcp_server.common import latest_block_path
    from mcp_server.tools_push import _iso_date, push_block
    from mcp_server.tools_read import get_athlete_state
    from mcp_server.tools_validate import validate_block
    from mcp_server.tools_write import save_availability, save_block, save_continuity

    # 1 — continuity travels with #STATE
    _seed_athlete_data(fresh=True)
    session = "#SESSION\nActive Phase: 4\nAthlete ID: " + AID + "\n#END"
    save_continuity(AID, session, athlete_name="Test Fixture")
    r = get_athlete_state(AID)
    check("workflow: get_athlete_state returns the saved #SESSION as `continuity`",
          "#SESSION" in (r.get("continuity") or ""), r.get("continuity"))
    check("workflow: get_athlete_state has a `race_notes` key (None or text)",
          "race_notes" in r)
    check("workflow: no falsifier in #SESSION, no review_due", r.get("review_due") is None, r.get("review_due"))
    save_continuity(AID, session.replace("#END", "Would Show Wrong: long-ride decoupling above 6%\n"
                                         "Review On: 01-01-2020\nLast Review: none\n#END"),
                    athlete_name="Test Fixture")
    r = get_athlete_state(AID)
    check("workflow: a past Review On with no review comes back as review_due",
          "long-ride decoupling above 6%" in (r.get("review_due") or ""), r.get("review_due"))
    save_continuity(AID, session, athlete_name="Test Fixture")

    # 1b — stated availability is saved once and comes back with #STATE
    ra = save_availability(AID, "just some days", athlete_name="Test Fixture")
    equal("workflow: save_availability rejects text without #AVAILABILITY", ra.get("ok"), False)
    ra = save_availability(AID, "#AVAILABILITY\nAthlete ID: " + AID + "\ntue: 90\nmon: rest\n#END",
                           athlete_name="Test Fixture")
    equal("workflow: save_availability accepts a well-formed block", ra.get("ok"), True)
    r = get_athlete_state(AID)
    check("workflow: get_athlete_state returns the saved `availability`",
          "tue: 90" in (r.get("availability") or ""), r.get("availability"))

    # 1c — training age is asked once, saved by the coach, read by the engine
    from mcp_server.tools_write import save_training_age
    rt = save_training_age(AID, "ten")
    equal("workflow: save_training_age rejects a non-number", rt.get("ok"), False)
    rt = save_training_age(AID, 120)
    equal("workflow: save_training_age rejects an impossible value", rt.get("ok"), False)
    rt = save_training_age(AID, 7)
    equal("workflow: save_training_age saves a valid number", (rt.get("ok"), rt.get("training_age_years")), (True, 7))
    import importlib
    sys.path.insert(0, os.path.join(ROOT, "engine"))
    bs_t = importlib.import_module("build_state")
    equal("workflow: the engine reads the saved training age",
          bs_t.training_age(bs_t.load_declared(AID), bs_t.load_facts(AID)), 7)
    os.remove(os.path.join(ROOT, "data", AID, "facts.json"))

    # 1d — the declared profile is written by the coach, behind a dry-run gate
    import shutil as _sh
    from mcp_server.tools_write import save_declared_profile
    _tpl = open(os.path.join(ROOT, "config", "athletes", "_template.yaml"), encoding="utf-8").read()
    _pid = "TESTPROFILE"
    _ppath = os.path.join(ROOT, "config", "athletes", _pid + ".yaml")
    try:
        r = save_declared_profile(_pid, "goals: [unclosed")
        equal("profile: invalid YAML is refused", r.get("ok"), False)
        r = save_declared_profile(_pid, "goals: []\n")
        check("profile: missing template sections are refused",
              r.get("ok") is False and "Missing sections" in r.get("error", ""), r)
        r = save_declared_profile(_pid, _tpl)
        check("profile: the default call is a dry run and writes nothing",
              r.get("dry_run") is True and not os.path.exists(_ppath), r)
        r = save_declared_profile(_pid, _tpl, dry_run=False, confirm=True)
        check("profile: confirmed call writes the new profile",
              r.get("dry_run") is False and os.path.exists(_ppath), r)
        r = save_declared_profile(_pid, _tpl.replace("units: km", "units: mi"))
        check("profile: a change shows up in the dry-run diff",
              "+units: mi" in (r.get("changes") or ""), r.get("changes"))
        save_declared_profile(_pid, _tpl.replace("units: km", "units: mi"), dry_run=False, confirm=True)
        hist = os.path.join(ROOT, "data", _pid, "profile_history")
        check("profile: the previous file is kept in profile_history",
              os.path.isdir(hist) and len(os.listdir(hist)) == 1)
        r = save_declared_profile("TESTRAMP", _tpl)
        equal("profile: the committed test fixture cannot be overwritten", r.get("ok"), False)
    finally:
        if os.path.exists(_ppath):
            os.remove(_ppath)
        _sh.rmtree(os.path.join(ROOT, "data", _pid), ignore_errors=True)

    # 2 — one file per week, newest is the default target
    good = os.path.join(ROOT, "tests", "blocks", "good_trainer_coggan.md")
    with open(good, encoding="utf-8") as f:
        good_text = f.read()
    r1 = save_block(AID, good_text, athlete_name="Test Fixture", week=1)
    _time.sleep(0.05)
    r2 = save_block(AID, good_text, athlete_name="Test Fixture", week=2)
    check("workflow: save_block(week=1) and (week=2) the same day are two files",
          r1.get("ok") and r2.get("ok") and r1.get("path") != r2.get("path"),
          (r1.get("path"), r2.get("path")))
    check("workflow: week file is named <date>_bloque_w<N>.md",
          str(r2.get("path", "")).endswith(f"{date.today().isoformat()}_bloque_w2.md"),
          r2.get("path"))
    latest = latest_block_path(AID, "Test Fixture")
    check("workflow: latest_block_path picks the week just saved",
          latest.endswith("_bloque_w2.md"), latest)
    rv = validate_block(athlete_id=AID, athlete_name="Test Fixture")
    check("workflow: validate_block(athlete_id) validates the latest week without a path",
          rv.get("ok") is True and str(rv.get("file", "")).endswith("_bloque_w2.md"), rv)

    # 3 — dates Intervals.icu accepts; race days not pushed
    equal("workflow: _iso_date converts DD-MM-YYYY", _iso_date("29-09-2026"), "2026-09-29")
    equal("workflow: _iso_date keeps YYYY-MM-DD", _iso_date("2026-09-29"), "2026-09-29")
    equal("workflow: _iso_date rejects garbage", _iso_date("sometime"), None)
    rp = push_block(AID, file_path=good)
    check("workflow: every pushed start_date_local is ISO YYYY-MM-DDT00:00:00",
          rp.get("events") and all(_re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00", e["start_date_local"])
                                   for e in rp["events"]),
          [e.get("start_date_local") for e in rp.get("events", [])])
    check("workflow: every pushed event is a WORKOUT",
          all(e["category"] == "WORKOUT" for e in rp.get("events", [])))
    ev = rp["events"][0]["description"]
    with open(good, encoding="utf-8") as f:
        _gt = f.read()
    _m = re.search(r"\[Execution\]:\s*(.+)", _gt) if "re" in globals() else None
    check("workflow: the Intervals description starts with the Execution note",
          ev.startswith("Ejecución:") or ev.startswith("Execution:") or "[Execution]" not in _gt, ev[:80])
    rn = push_block(AID, file_path=good, include_notes=False)
    check("workflow: include_notes=False sends only the workout steps",
          not rn["events"][0]["description"].startswith(("Ejecución:", "Execution:")))
    import tempfile as _t2
    with _t2.TemporaryDirectory() as _d:
        _p = os.path.join(_d, "n.md")
        with open(_p, "w", encoding="utf-8") as f:
            f.write("[Week] 01 | [Date] 28-09-2026\n[Athlete ID]: x\n[Category]: Training\n[Methodology]: daniels\n"
                    "[Discipline]: road_run\n[Focus]: Base\n[Zone]: Tempo · Friel Zona 3\n[Duration] 00:10:00 | [Estimated TSS] 5\n"
                    "[Execution]: - Corre parejo en 6x\n[Nutrition]: Toma 500 ml de agua antes de salir.\n\n"
                    "```text\nMain Set\n\n- 10m 75-80% Pace [RPE 1-3]\n```\n")
        _ev0 = push_block(AID, file_path=_p)["events"][0]
        _d0 = _ev0["description"]
        _dz = _d0 + " " + _ev0["name"]
    from mcp_server.tools_push import _NOTE_LABELS, _athlete_language
    _why, _ex, _nu = _NOTE_LABELS[_athlete_language(AID)]
    check("workflow: Execution and Nutrition both reach the description, before the steps",
          f"{_nu}: Toma 500 ml de agua" in _d0 and _d0.index(_nu) < _d0.index("Main Set"), _d0)
    check("workflow: the coach-only [Zone] never reaches Intervals.icu",
          "Tempo · Friel" not in _dz and "Zone" not in _dz, _dz)
    check("workflow: a note line never starts with '-' or ends in a repeat marker",
          f"{_ex}: Corre parejo en 6x." in _d0, _d0)
    with tempfile.TemporaryDirectory() as tmp:
        race = os.path.join(tmp, "race.md")
        with open(race, "w", encoding="utf-8") as f:
            f.write(good_text.replace("[Category]: Training", "[Category]: Race", 1))
        rr = push_block(AID, file_path=race)
        check("workflow: a Race day is skipped with a stated reason, never pushed",
              any("race day" in str(sk.get("reason", "")) for sk in (rr.get("skipped") or []))
              or (rr.get("ok") is False and "race day" in str(rr)),
              rr)


def test_fatigue_curves_fetch():
    """fetch_fatigue_curves: optional data, silent when absent, never guessed.
    The fake answers have the shape of the API's ActivityPowerCurvePayload:
    {"after_kj", "secs", "curves": [{"start_date_local", "watts"}]}."""
    import fetch_athlete_data as fad
    from datetime import date, timedelta
    today = date.today()
    d = lambda n: (today - timedelta(days=n)).isoformat() + "T08:00:00"
    path = f"/athlete/{AID}/activity-power-curves"
    profile = {"sport_settings": [{"types": ["Ride"], "after_kj0": None, "after_kj1": None}]}

    def payload(kj, watts, secs=(300, 1200), curves=True):
        body = {"secs": list(secs),
                "curves": [{"id": "i1", "start_date_local": d(5), "watts": watts}] if curves else []}
        if kj is not None:
            body["after_kj"] = kj
        return _Resp(body)

    def by_fatigue(kw):
        f = kw["params"].get("fatigue")
        return {None: payload(None, [300, 250]), "kj0": payload(1500, [270, 220]),
                "kj1": payload(3000, [240, 200])}[f]

    real = fad.SESSION
    try:
        fad.SESSION = _FakeSession({("GET", path): by_fatigue}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        params = [c[2]["params"] for c in fad.SESSION.calls]
        check("fatigue curves: one fresh call plus kj0 and kj1",
              [p.get("fatigue") for p in params] == [None, "kj0", "kj1"])
        check("fatigue curves: asks for Ride at 5 and 20 minutes",
              all(p["type"] == "Ride" and p["secs"] == "300,1200" for p in params))
        equal("fatigue curves: the kJ levels come from the answer, not the settings",
              out["after_kj"], {"kj0": 1500, "kj1": 3000})
        equal("fatigue curves: best kept per level",
              (out["best"]["fresh"]["current"]["300"]["watts"],
               out["best"]["kj0"]["current"]["1200"]["watts"],
               out["best"]["kj1"]["current"]["300"]["watts"]), (300, 220, 240))
        equal("fatigue curves: the probe records what each request returned",
              (probe["fresh"]["curves"], probe["kj0"]["after_kj"]), (1, 1500))

        def reordered(kw):
            f = kw["params"].get("fatigue")
            return payload(1500 if f else None, [250, 300], secs=(1200, 300))
        fad.SESSION = _FakeSession({("GET", path): reordered}, fad.BASE_URL)
        out, _ = fad.fetch_fatigue_curves(AID, profile)
        equal("fatigue curves: watts are aligned by the answer's own secs",
              (out["best"]["fresh"]["current"]["300"]["watts"],
               out["best"]["fresh"]["current"]["1200"]["watts"]), (300, 250))

        def only_kj0(kw):
            f = kw["params"].get("fatigue")
            if f == "kj1":
                return payload(None, [], curves=False)      # no such curve defined
            return by_fatigue(kw)
        fad.SESSION = _FakeSession({("GET", path): only_kj0}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        check("fatigue curves: a fatigued curve the athlete lacks is left out",
              list(out["after_kj"]) == ["kj0"] and "kj1" not in out["best"]
              and probe["kj1"]["after_kj"] is None)

        def none_defined(kw):
            return payload(None, [300, 250] if not kw["params"].get("fatigue") else [], curves=not kw["params"].get("fatigue"))
        fad.SESSION = _FakeSession({("GET", path): none_defined}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        check("fatigue curves: no fatigued curve defined -> None, with the probe kept",
              out is None and "kj0" in probe and "kj1" in probe)

        def no_power(kw):
            return payload(None, [], curves=False)
        fad.SESSION = _FakeSession({("GET", path): no_power}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        check("fatigue curves: no power curves at all -> None after a single request",
              out is None and len(fad.SESSION.calls) == 1)

        equal("fatigue curves: no Ride settings -> None",
              fad.fetch_fatigue_curves(AID, {"sport_settings": [{"types": ["Run"]}]})[0], None)

        fad.SESSION = _FakeSession({}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        check("fatigue curves: fresh curve unreadable -> None",
              out is None and probe["fresh"] == "request failed")

        def kj1_fails(kw):
            if kw["params"].get("fatigue") == "kj1":
                return _Resp({"error": "x"}, 500)
            return by_fatigue(kw)
        fad.SESSION = _FakeSession({("GET", path): kj1_fails}, fad.BASE_URL)
        out, probe = fad.fetch_fatigue_curves(AID, profile)
        check("fatigue curves: a failed fatigued level is left out, the rest kept",
              "kj1" not in out["best"] and "kj0" in out["best"] and "fresh" in out["best"]
              and probe["kj1"] == "request failed")
    finally:
        fad.SESSION = real


def test_load_targets_tool():
    import mcp_server.tools_read as tr
    r = tr.load_targets(300, 4, cycle="3:1", growth_pct=10, recovery_pct=30)
    check("load_targets tool: returns the four weeks and a table",
          r.get("ok") is True and len(r["weeks"]) == 4 and "## Load targets" in r["markdown"])
    equal("load_targets tool: recovery week follows the last build week",
          [w["type"] for w in r["weeks"]], ["build", "build", "build", "recovery"])
    r = tr.load_targets(300, 0)
    equal("load_targets tool: a nonsensical input fails cleanly", r.get("ok"), False)


def test_what_if_tool():
    from datetime import date, timedelta
    import mcp_server.tools_read as tr
    today = date.today()
    mon = today + timedelta(days=7 - today.weekday())
    race = (today + timedelta(days=35)).isoformat()
    _seed_athlete_data(fresh=True)
    r = tr.what_if_targets(AID, {mon.isoformat(): 300}, race_date=race, event_type="road")
    check("what_if tool: answers for a prepared athlete",
          r.get("ok") is True and r.get("available") is True, str(r)[:300])
    check("what_if tool: both projections and the table come back",
          r.get("baseline") and r.get("what_if") and "With the targets" in r["markdown"])
    r = tr.what_if_targets(AID, {"2026-13-45": 300}, race_date=race)
    equal("what_if tool: a bad date fails cleanly", r.get("ok"), False)
    r = tr.what_if_targets("no-such-athlete-id", {mon.isoformat(): 300}, race_date=race)
    equal("what_if tool: an unknown athlete fails cleanly", r.get("ok"), False)


def main():
    print("mcp_server — regression tests\n")
    if not MCP_AVAILABLE:
        print("mcp package not installed — skipping (optional dependency; "
              "see requirements.txt). Install with: pip install \"mcp==1.30.0\"")
        return 0

    try:
        for fn in (test_cancel_patch, test_guard, test_common, test_tools_read, test_tools_roster_and_execution, test_tools_coach, test_fatigue_curves_fetch, test_load_targets_tool, test_what_if_tool,
                   test_tools_write, test_tools_validate,
                   test_relative_file_path_resolves_against_root, test_tools_push,
                   test_tools_push_refuses_blocked_block, test_mcp_first_workflow):
            fn()
    finally:
        _cleanup()

    print()
    for name, detail in FAILED:
        print(f"  FAIL  {name}")
        if detail:
            print(f"        {detail}")

    total = len(PASSED) + len(FAILED)
    print()
    print(f"{len(PASSED)}/{total} passed.")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
