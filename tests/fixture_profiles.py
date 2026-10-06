"""
fixture_profiles.py — the test athletes' declared profiles (v7.33).

config/athletes/ holds real athletes' profiles and, on the head coach's
computers, is a junction to Google Drive; nothing in it is tracked by git any
more. The test athletes (TESTRAMP…) live in tests/profiles/ and are
put into config/athletes/ for the duration of a test run, then taken out.
A file that was already there is put back exactly as it was.
"""

import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tests", "profiles")
DEST = os.path.join(ROOT, "config", "athletes")


def install():
    """Copy every fixture profile in; returns what remove() needs."""
    os.makedirs(DEST, exist_ok=True)
    saved = {}
    for src in sorted(glob.glob(os.path.join(SRC, "*.yaml"))):
        dest = os.path.join(DEST, os.path.basename(src))
        saved[dest] = open(dest, "rb").read() if os.path.exists(dest) else None
        shutil.copyfile(src, dest)
    return saved


def remove(saved):
    for dest, before in (saved or {}).items():
        try:
            if before is None:
                os.remove(dest)
            else:
                with open(dest, "wb") as f:
                    f.write(before)
        except OSError:
            pass
