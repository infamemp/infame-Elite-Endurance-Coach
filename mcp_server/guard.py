"""guard.py — the structural safety net every tool handler goes through
==========================================================================
Two more bugs killed the previous server (archive/RESTORE_POINT_v6.5.md §2),
independent of the stdio cancellation bug `cancel_patch.py` targets:

1. `sys.exit()` — used throughout the reused CLI modules for user-facing
   errors (e.g. `fetch_athlete_data.py` checking `ICU_API_KEY` at import
   time) — raises `SystemExit`, which does NOT inherit from `Exception`. A
   bare `except Exception` inside a tool handler let it through, and it took
   down the whole server process, not just that call.
2. A `print()` anywhere in that reused code — and `fetch_one()` and
   `build_profile.build()` both print unconditionally — corrupts stdout,
   which doubles as the MCP protocol's own wire channel on the stdio
   transport. This produced the "hangs, then disconnects" symptom actually
   observed in production last time.

Both fixes were real but were found and patched ad hoc, mid-session, the
first time. Here they're structural: every tool is wrapped through
`@guarded` (below) rather than trusted to remember the pattern, and a test
in `tests/test_mcp_server.py` proves both failure modes are actually caught
before any tool ships.

A third property added this time, not present before: `@guarded` calls are
serialized through one process-wide lock. `contextlib.redirect_stdout`
swaps `sys.stdout` for the whole process — if two tool calls ever run
concurrently in different threads (sync tool functions are commonly run in
a worker thread by the SDK), their redirections would race and could leak
output onto the real stdout mid-response. This system is single-coach,
single-conversation by design (per athlete, per macrocycle) — there is no
real concurrency to give up by serializing, only a class of bug to remove.
"""

from __future__ import annotations

import contextlib
import functools
import io
import logging
import threading
from typing import Any, Callable, TypeVar

logger = logging.getLogger("mcp_server.guard")

_CALL_LOCK = threading.Lock()

F = TypeVar("F", bound=Callable[..., Any])


class ToolError(RuntimeError):
    """Raised by tool bodies for an expected, user-facing failure (bad
    input, athlete not found, hard-constraint failure). Distinguished from
    an unexpected crash only so callers/tests can tell "the tool did its
    job and reported a problem" apart from "the tool itself broke" —
    `@guarded` catches and reports both, identically safely, either way."""


def guarded(fn: F) -> F:
    """Wrap a tool function so nothing it does — or anything it calls into,
    including sys.exit() deep inside fetch_athlete_data/build_state/
    build_profile/coach — can take down the server process or corrupt its
    stdout. Returns a plain dict on failure instead of raising, so the tool
    result is always well-formed MCP output, never a dead connection."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # TEMP DIAGNOSTIC (remove once the validate_block stdio hang is
        # root-caused): checkpoint lines to stderr, which Desktop's
        # per-server log file already captures. Each logger.info() call
        # flushes on emit (logging.StreamHandler default), so a checkpoint
        # is durable on disk immediately, even if the process hangs right
        # after it.
        logger.info("CHECKPOINT guard: received call to %s (args=%r kwargs=%r)",
                    fn.__name__, args, kwargs)
        buf = io.StringIO()
        with _CALL_LOCK, contextlib.redirect_stdout(buf):
            logger.info("CHECKPOINT guard: about to invoke %s", fn.__name__)
            try:
                result = fn(*args, **kwargs)
                logger.info("CHECKPOINT guard: %s returned normally", fn.__name__)
            except SystemExit as exc:
                # sys.exit() from reused CLI code — never inherits from
                # Exception, so it needs its own branch or it kills the
                # server exactly the way it did before.
                message = str(exc.code) if exc.code is not None else ""
                logger.error("tool %s: SystemExit(%r)", fn.__name__, message)
                logger.info("CHECKPOINT guard: about to return (SystemExit path) for %s",
                            fn.__name__)
                return _error(fn.__name__, "SystemExit", message, buf.getvalue())
            except ToolError as exc:
                logger.info("CHECKPOINT guard: about to return (ToolError path) for %s",
                            fn.__name__)
                return _error(fn.__name__, "ToolError", str(exc), buf.getvalue())
            except Exception as exc:  # noqa: BLE001 — the whole point is to catch everything
                logger.exception("tool %s raised", fn.__name__)
                logger.info("CHECKPOINT guard: about to return (Exception path) for %s",
                            fn.__name__)
                return _error(fn.__name__, type(exc).__name__, str(exc), buf.getvalue())
        captured = buf.getvalue()
        if captured.strip():
            # Not a failure — just visibility. Every print() the reused CLI
            # code did during a successful call is logged here instead of
            # reaching real stdout, so nothing is silently lost, and a
            # future leak is visible in the server's own log rather than
            # only manifesting as a corrupted protocol stream.
            logger.debug("tool %s stdout (captured, not leaked):\n%s", fn.__name__, captured)
        logger.info("CHECKPOINT guard: about to return (success path) for %s", fn.__name__)
        return result

    return wrapper


def _error(tool: str, kind: str, message: str, captured_stdout: str) -> dict:
    out = {"ok": False, "tool": tool, "error_type": kind, "error": message}
    if captured_stdout.strip():
        out["captured_output"] = captured_stdout
    return out
