# Guide — Infame Elite Endurance Coach

One page: set up a machine, work with the coach, and what to do when the MCP
server is down. Replaces `OPERATIONS_MANUAL.md` and `QUICK_GUIDE.md` (v7.33;
both are in the git history).

## 1. Set up a machine (once)

1. In the repo folder: `pip install -r requirements.txt`
2. The Intervals.icu key: `setx ICU_API_KEY "your_key"`, then open a new terminal.
3. The MCP server's own environment:
   ```
   python -m venv .venv-mcp
   .venv-mcp\Scripts\pip.exe install -r requirements.txt "mcp==1.30.0"
   ```
4. Claude Desktop → Settings → Developer → Edit config. Merge in (don't replace
   the file; never save it with `Set-Content -Encoding UTF8`, the BOM breaks it):
   ```json
   {"mcpServers": {"infame-coach": {
     "command": "C:\\Dev\\Github\\infame_elite_endurance_coach\\.venv-mcp\\Scripts\\python.exe",
     "args": ["-m", "mcp_server.run_server"],
     "cwd": "C:\\Dev\\Github\\infame_elite_endurance_coach",
     "env": {"ICU_API_KEY": "your_key",
             "PYTHONPATH": "C:\\Dev\\Github\\infame_elite_endurance_coach"}}}}
   ```
5. Quit Claude Desktop from the system tray, reopen it, and check that
   `infame-coach` shows **Running**.
6. The Claude Project holds what the newest `RESTORE_POINT_v*.md` lists.

## 2. Working with the coach

Work in a plain Chat inside the Project (not Cowork or Code). You never name a
tool; you talk, the coach calls them, you approve.

| You want | Say | The coach |
|---|---|---|
| Start with an athlete | "Trabajemos con Ana" | loads `#STATE`, profile, continuity, race notes |
| A new athlete | "Nuevo atleta, id i123456" | runs the intake, shows the profile, saves it after your OK |
| A week | approve each design step | saves the week, validates it, corrects a BLOCKED week itself |
| Upload | "sí, súbela" after the dry run | sends it; a corrected week updates the same sessions |
| Redo uploaded days | "borra lo subido desde mañana" | dry run first, then removes only what it uploaded |
| Close a chat to continue later | "guarda la continuidad" | saves `#SESSION` (replaces the previous one) |
| After a race | the debrief | appends `#RACE_RESULT` to the race notes |
| Everyone at once | "¿cómo va el roster?" | one table: state, TSB, last activity, next race |

Never ask to override a BLOCKED week unless you know exactly what you bypass.
Never edit `continuity.md` or `race_notes.md` by hand.

## 3. Without the MCP server

Only when `infame-coach` is down. In PowerShell, in the repo folder:

| Step | Command |
|---|---|
| Athlete ids | `python coach.py prep --list` |
| Data for a chat | `python coach.py prep <id>` → attach `state.md`, `profile.md`, `continuity.md` from `out/<athlete>/` |
| New athlete | `python coach.py new <id>` (profile template + intake script) |
| Check a week | save it in `out/<athlete>/blocks/`, then `python coach.py check <file>` |
| Upload | paste the passed sessions into Intervals.icu's Workout Builder |
| Compare dates | `python coach.py review <id> --since <YYYY-MM-DD>` |
| What happened | `python coach.py ledger <id>` |

Continuity by hand: the `#SESSION…#END` block replaces `continuity.md`. A race
result goes at the **end** of `race_notes.md`.

## 4. Updating the code

1. Get the new files into `C:\Dev\Github\infame_elite_endurance_coach`.
2. `python tests/run_tests.py` and `.venv-mcp\Scripts\python.exe tests/test_mcp_server.py`
   — both must pass.
3. Commit and push in GitHub Desktop (GitHub runs both suites again).
4. Restart Claude Desktop. If the prompt changed, paste it into the Project.

## 5. Common problems

| You see | Do |
|---|---|
| `infame-coach` **Failed** | View logs. `No module named 'mcp_server'` → `PYTHONPATH` missing in the config |
| "Couldn't load app settings" | the config was saved with a BOM: rewrite it with `[System.IO.File]::WriteAllText($p, $json, [Text.Encoding]::ASCII)` |
| Errors about "remote-devices" | you are in Cowork/Code: use a plain Chat |
| `Missing environment variable ICU_API_KEY` | step 1.2, or the `env` block in the Desktop config |
| `Unknown athlete id` | check the id with the roster; nothing was written |
| `Unknown methodology 'X'` | the `[Methodology]` field is wrong: the coach corrects the week |
| `push_block` refuses a BLOCKED week | working as intended: correct and validate again |
| A tool hangs for minutes | pull the latest code and restart Desktop |
