"""cancel_patch.py — self-verifying workaround for python-sdk#2610
=====================================================================
The bug that took the previous server down: when a client cancels an
in-flight request over stdio, `mcp.shared.session.RequestResponder.__exit__`
still calls its cancel scope's own `__exit__` unconditionally. anyio's cancel
scope re-raises the `CancelledError` it was holding at that point even though
the responder had already sent its response — and that exception then
escapes the request-handling task. Because that task is a sibling of the
task group running the stdio receive loop, an unhandled exception from it
brings the whole task group down, not just that one request. One cancelled
tool call was enough to end the entire conversation with no further
diagnosis than "hangs, then disconnects."

https://github.com/modelcontextprotocol/python-sdk/issues/2610

Upstream's own fix (python-sdk#2624, not yet released as of mcp 1.30.0)
wraps the cancel-scope exit so a `CancelledError` is swallowed exactly when
the responder had already completed:

    try:
        self._cancel_scope.__exit__(exc_type, exc_val, exc_tb)
    except BaseException as exc:
        if not (self._completed and isinstance(exc, anyio.get_cancelled_exc_class())):
            raise

`apply()` below installs that exact fix as a monkeypatch of
`RequestResponder.__exit__`, but only after `is_needed()` has empirically
confirmed — by actually constructing a responder and exercising it, not by
reading a version number — that the installed SDK still has the bug. On a
release that already carries the upstream fix (or a future major version
that restructures this away entirely, the way mcp 2.x did), `is_needed()`
returns False and `apply()` is a deliberate no-op: patching an already-fixed
method, or a method that no longer exists, is its own risk.

This module has exactly one job and must stay importable standalone (no
dependency on the rest of mcp_server/) so `tests/test_mcp_server.py` can
exercise it in isolation, the same way upstream's own regression test
(tests/shared/test_session.py in python-sdk#2624) exercises the responder
directly rather than driving a real stdio transport end to end.
"""

from __future__ import annotations

import logging
from typing import Any, cast

logger = logging.getLogger("mcp_server.cancel_patch")

_PATCHED = False


class _RaisingCancelScope:
    """A stand-in cancel scope whose __exit__ always raises the same
    CancelledError anyio itself would raise on a genuinely cancelled scope.
    Used only to probe RequestResponder.__exit__'s behavior — never a real
    cancel scope, never installed into a real responder outside this probe.
    """

    def __exit__(self, exc_type, exc_val, exc_tb):
        import anyio

        raise anyio.get_cancelled_exc_class()()


async def _make_probe_responder():
    """Build one real RequestResponder with a completed, cancelled-looking
    state — the exact shape python-sdk#2624's own test constructs.
    `RequestResponder.__init__` itself opens a real `anyio.CancelScope()`,
    which requires a running event loop (upstream's own test is
    `@pytest.mark.anyio` for the same reason) — this must be awaited from
    inside one, never called bare."""
    from mcp.shared.session import RequestResponder
    from mcp import types

    responder = RequestResponder(
        request_id=1,
        request_meta=None,
        request=types.ClientRequest(types.PingRequest()),
        session=cast(Any, object()),
        on_complete=lambda _r: None,
    )
    responder._completed = True  # noqa: SLF001 — mirrors upstream's own test
    responder._cancel_scope = cast(Any, _RaisingCancelScope())  # noqa: SLF001
    return responder


async def _probe_async() -> bool:
    """True if exiting a completed probe responder still lets a
    CancelledError from its cancel scope escape (the bug); False if it's
    swallowed (fixed) or the probe itself misbehaves in some other shape."""
    import anyio

    responder = await _make_probe_responder()
    try:
        responder.__exit__(None, None, None)
    except BaseException as exc:  # noqa: BLE001 — this is exactly what we're probing for
        if isinstance(exc, anyio.get_cancelled_exc_class()):
            return True
        logger.warning(
            "cancel_patch: probe raised an unexpected %s instead of a "
            "cancellation — not applying the python-sdk#2610 workaround.",
            type(exc).__name__,
        )
        return False
    return False


def is_needed() -> bool:
    """True if the installed SDK still exhibits the bug: exiting a completed
    responder whose cancel scope raises CancelledError still propagates that
    exception instead of swallowing it. False if the class doesn't exist
    (a restructured SDK, e.g. mcp 2.x, where this bug's exact code path is
    gone) or if the exception is already swallowed (fix landed upstream)."""
    try:
        from mcp.shared.session import RequestResponder  # noqa: F401
    except ImportError:
        logger.info(
            "cancel_patch: mcp.shared.session.RequestResponder not found — "
            "this SDK's internals no longer match python-sdk#2610's affected "
            "code path. No patch applied."
        )
        return False

    import anyio

    return anyio.run(_probe_async)


def apply() -> bool:
    """Install the upstream fix if, and only if, is_needed() confirms this
    process's installed SDK actually has the bug. Idempotent — calling it
    twice patches once. Returns whether the patch is active (either just
    installed, or already installed by an earlier call)."""
    global _PATCHED
    if _PATCHED:
        return True

    if not is_needed():
        return False

    from mcp.shared.session import RequestResponder
    import anyio

    _original_exit = RequestResponder.__exit__

    def _patched_exit(self, exc_type, exc_val, exc_tb):
        """Verbatim upstream fix from python-sdk#2624: run the normal
        completion/cleanup path, then exit the cancel scope, swallowing a
        CancelledError only when this request had already completed."""
        try:
            if self._completed:  # noqa: SLF001
                self._on_complete(self)  # noqa: SLF001
        finally:
            self._entered = False  # noqa: SLF001
            if not self._cancel_scope:  # pragma: no cover
                raise RuntimeError("No active cancel scope")
            try:
                self._cancel_scope.__exit__(exc_type, exc_val, exc_tb)  # noqa: SLF001
            except BaseException as exc:  # noqa: BLE001
                if not (self._completed and isinstance(exc, anyio.get_cancelled_exc_class())):  # noqa: SLF001
                    raise

    RequestResponder.__exit__ = _patched_exit
    _PATCHED = True
    logger.warning(
        "cancel_patch: python-sdk#2610 workaround installed — the installed "
        "mcp SDK still drops the whole server on a cancelled in-flight "
        "request over stdio. Safe to delete this module once upstream ships "
        "python-sdk#2624 and this process's mcp version includes it — "
        "is_needed() will then return False on its own and apply() becomes "
        "a no-op, so nothing else needs to change when that day comes."
    )
    return True
