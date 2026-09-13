"""run_server.py — what claude_desktop_config.json should actually launch
============================================================================
Not `server.py` directly — this file, so a crash always leaves a durable,
timestamped record instead of the bare "hangs, then disconnects" a head
coach saw with no explanation the first time this server existed
(archive/RESTORE_POINT_v6.5.md §2).

One honest limitation, stated here rather than glossed over: this is a
crash *logger*, not a crash *recoverer*. An MCP stdio session's identity is
the subprocess Desktop launched for it — if that process dies, the
protocol session is over regardless of what wraps it; a supervisor cannot
transparently respawn a new process into the same conversation, because
the new process would need to redo the initialize handshake Desktop's
client already completed once. Desktop's own behavior (relaunching the
configured command the next time a tool from this server is needed) is
what actually recovers from a crash — this wrapper's only job is making
sure that when it happens, there's a specific, readable reason on disk
instead of nothing, so a repeated crash is diagnosable instead of just
being retried blindly forever.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "mcp_server", "logs")


def _configure_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "server.log")

    logger = logging.getLogger("mcp_server")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)
    logger.addHandler(stderr_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def main() -> None:
    logger = _configure_logging()
    logger.info("run_server: launching mcp_server.server (pid %d)", os.getpid())
    try:
        from mcp_server import server

        server.main()
    except BaseException as exc:  # noqa: BLE001 — deliberately broad: this is the last line of defense
        crash_path = os.path.join(LOG_DIR, "last_crash.txt")
        with open(crash_path, "w", encoding="utf-8") as f:
            f.write(f"Crashed at {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"{type(exc).__name__}: {exc}\n\n")
            f.write(traceback.format_exc())
        logger.error(
            "run_server: server exited with %s: %s — full traceback written to %s",
            type(exc).__name__, exc, crash_path,
        )
        raise


if __name__ == "__main__":
    main()
