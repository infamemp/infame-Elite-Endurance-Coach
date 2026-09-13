"""server.py — the 8 tools, wired to a stdio MCP server
==========================================================
Not what Claude Desktop should actually be configured to launch — see
`run_server.py` for that. This module only builds the tool surface and
knows how to run it; the supervisor around it is a separate, deliberately
tiny file so a bug in one can never hide a bug in the other.

Logging goes to stderr, never stdout — stdout is the stdio transport's own
protocol channel, and a stray print() reaching it is exactly what produced
the "hangs, then disconnects" symptom the first time
(archive/RESTORE_POINT_v6.5.md §2). `guard.py` already redirects every
tool's own stdout into this logger; nothing in this file should ever call
print() directly either.
"""

from __future__ import annotations

import logging
import sys

from . import cancel_patch
from .tools_push import push_block
from .tools_read import get_athlete_state, get_athlete_profile, list_roster
from .tools_validate import validate_block
from .tools_write import save_block, save_continuity, save_race_result

logger = logging.getLogger("mcp_server")


def _configure_logging() -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_app():
    """Construct the FastMCP app and register all 8 tools. Deferred inside
    a function (rather than at import time) so importing this module for
    introspection or testing never requires the `mcp` package to already be
    on the path — only actually building or running the server does."""
    from mcp.server.fastmcp import FastMCP

    app = FastMCP(
        name="infame-coach",
        instructions=(
            "Deterministic engine access for the Infame Elite Endurance "
            "Coach. Every tool here calls the same engine code coach.py "
            "does — nothing is computed differently. push_block is the one "
            "exception to 'these tools do what the CLI already does': it "
            "defaults to dry_run and will not send anything to "
            "Intervals.icu unless both dry_run=False and confirm=True are "
            "passed explicitly. Uploading is a deliberate, manual action, "
            "same as it has always been."
        ),
    )

    # get_athlete_state / get_athlete_profile / list_roster — read-only,
    # no side effects beyond the same local files coach.py prep already
    # writes.
    app.tool()(get_athlete_state)
    app.tool()(get_athlete_profile)
    app.tool()(list_roster)

    # save_continuity / save_race_result / save_block — write the three
    # files a head coach otherwise pastes by hand.
    app.tool()(save_continuity)
    app.tool()(save_race_result)
    app.tool()(save_block)

    # validate_block — runs the existing gate as a subprocess.
    app.tool()(validate_block)

    # push_block — see tools_push.py's own module docstring for why this
    # one is treated differently from the other seven.
    app.tool()(push_block)

    return app


def main() -> None:
    _configure_logging()
    patched = cancel_patch.apply()
    logger.info(
        "infame-coach MCP server starting (stdio). "
        "python-sdk#2610 workaround %s.",
        "active" if patched else "not needed for this SDK version",
    )
    app = build_app()
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
