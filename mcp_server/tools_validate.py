"""tools_validate.py — validate_block
=======================================
Runs verify/validate_block.py as a subprocess, deliberately — never
imported and called in-process. A subprocess's stdout can never corrupt
this server's own stdout, which doubles as the stdio transport's protocol
channel; an in-process call to a module that prints unconditionally (which
several reused CLI modules do) would need the same `redirect_stdout`
discipline `guard.py` already applies, but with an extra, avoidable way to
get it wrong. This was the original design's own reasoning
(archive/RESTORE_POINT_v6.5.md §2) and it still holds.

Every flag `verify/validate_block.py` accepts on the command line is
exposed here too — `--tss`, `--tolerance`, `--athlete`, `--quiet` were all
real, working options that neither `coach.py check` nor any manual ever
surfaced (see WORKFLOW_ACTUAL.md §5); there's no reason for this tool to
repeat that gap.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import date

from .common import OUT, ROOT, ensure_import_paths, safe_out_dir
from .guard import ToolError, guarded

logger = logging.getLogger("mcp_server.tools_validate")


@guarded
def validate_block(
    athlete_id: str | None = None,
    file_path: str | None = None,
    fill_tss: bool = False,
    methodology: str | None = None,
    discipline: str | None = None,
    expected_tss: float | None = None,
    tolerance: float | None = None,
    quiet: bool = False,
    athlete_name: str | None = None,
) -> dict:
    """Validate a block. Pass file_path explicitly, or athlete_id alone to
    validate today's file saved by save_block
    (out/<athlete>/blocks/<today>_bloque.md).

    Exit code 0 = upload-safe, 1 = blocked, matching the CLI exactly — this
    tool never repairs or interprets the result, only reports it. Uploading
    to Intervals.icu is a separate, deliberately manual step regardless of
    this result (see push_block)."""
    ensure_import_paths()

    if not file_path:
        if not athlete_id:
            raise ToolError("Pass either file_path or athlete_id.")
        out_dir = safe_out_dir(athlete_id, athlete_name)
        file_path = os.path.join(out_dir, "blocks", f"{date.today().isoformat()}_bloque.md")
        if not os.path.exists(file_path):
            raise ToolError(
                f"No block saved today for '{athlete_id}' at "
                f"{os.path.relpath(file_path, os.path.dirname(OUT))} — "
                f"call save_block first, or pass file_path explicitly."
            )
    else:
        # A relative file_path must never be resolved against the current
        # process's working directory: os.getcwd() at server runtime is
        # not reliable, confirmed on Windows via Claude Desktop — the
        # configured claude_desktop_config.json "cwd" field did not
        # actually govern the launched process's real working directory,
        # so a relative path that worked from an interactive shell
        # launched at ROOT failed with "File not found" from the live
        # server despite the file existing exactly there. Every other
        # path this module touches (out_dir below, ROOT/verify/... for
        # the script itself) is already absolute by construction; a
        # caller-supplied file_path is the one place a relative string
        # could slip through unresolved, so it's anchored to ROOT
        # explicitly here rather than trusted.
        if not os.path.isabs(file_path):
            file_path = os.path.join(ROOT, file_path)
        if not os.path.exists(file_path):
            raise ToolError(f"File not found: {file_path}")

    script = os.path.join(ROOT, "verify", "validate_block.py")
    cmd = [sys.executable, script, file_path]
    if fill_tss:
        cmd.append("--fill-tss")
    if methodology:
        cmd += ["--methodology", methodology]
    if discipline:
        cmd += ["--discipline", discipline]
    if expected_tss is not None:
        cmd += ["--tss", str(expected_tss)]
    if tolerance is not None:
        cmd += ["--tolerance", str(tolerance)]
    if athlete_id:
        cmd += ["--athlete", str(athlete_id)]
    if quiet:
        cmd.append("--quiet")

    # encoding="utf-8" below only controls how THIS process decodes the
    # pipe's bytes — it says nothing about what encoding the CHILD process
    # uses to encode its own stdout in the first place. On Windows, a
    # Python process whose stdout is a pipe (not a real console) defaults
    # to the legacy ANSI codepage (cp1252) unless told otherwise, and
    # validate_block.py prints Unicode box-drawing/em-dash characters in
    # its session headers that cp1252 cannot encode — the child crashes
    # with UnicodeEncodeError before it can report anything, which then
    # surfaces here as a plain exit code 1, indistinguishable from a real
    # hard-constraint failure. PYTHONIOENCODING forces the child's own
    # stdout/stderr to UTF-8 regardless of console/codepage; PYTHONUTF8
    # additionally puts the whole child interpreter in UTF-8 mode. Confirmed
    # reproducible on Windows: validate_block.py run directly in a console
    # (which does handle Unicode) passes cleanly; the identical file run
    # through this subprocess call failed every time before this fix.
    # tests/run_tests.py's own subprocess calls into this same script
    # already carry this exact guard, for the exact same reason.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    # TEMP DIAGNOSTIC (remove once the validate_block stdio hang is
    # root-caused): checkpoints around the one call in this tool that can
    # actually block — subprocess.run() — to see whether the hang is inside
    # the subprocess itself or somewhere else in the tool/guard/transport
    # stack.
    logger.info("CHECKPOINT validate_block: about to subprocess.run cmd=%r cwd=%r", cmd, ROOT)
    # stdin=DEVNULL is deliberate, not a default: without it, the child
    # inherits this process's own stdin — which, under the stdio MCP
    # transport, is the live pipe Desktop writes JSON-RPC requests into.
    # validate_block.py never reads stdin, so this changes nothing when
    # things work, but it removes an inherited handle to the server's own
    # protocol channel for the subprocess's whole lifetime — a real
    # difference from a standalone CLI invocation (which has no such pipe)
    # that was left unexplained before this fix.
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
    )
    logger.info("CHECKPOINT validate_block: subprocess.run returned exit_code=%r",
                result.returncode)
    report = (result.stdout or "") + (result.stderr or "")
    logger.info("CHECKPOINT validate_block: about to build return dict")
    return {
        "ok": True,
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "file": os.path.relpath(file_path, ROOT),
        "fill_tss_requested": fill_tss,
        "report": report,
    }
