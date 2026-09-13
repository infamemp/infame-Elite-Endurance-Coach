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
    for p in (os.path.join(ROOT, "data", AID), os.path.join(ROOT, "out", "Test_Fixture")):
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


def main():
    print("mcp_server — regression tests\n")
    if not MCP_AVAILABLE:
        print("mcp package not installed — skipping (optional dependency; "
              "see requirements.txt). Install with: pip install \"mcp==1.30.0\"")
        return 0

    try:
        for fn in (test_cancel_patch, test_guard, test_common, test_tools_read,
                   test_tools_write, test_tools_validate, test_tools_push):
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
