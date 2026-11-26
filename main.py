"""NÜR launcher: run ``python main.py`` from anywhere in the repository.

``nur_game`` lives in ``src/`` and is not installed into the virtual
environment, so the package directory is added to ``sys.path`` relative to this
file.  That keeps the plain ``python main.py`` form working from any working
directory and without PYTHONPATH.

All command-line options are handled by the real launcher, ``src/play_nur.py``:

    python main.py                 # play
    python main.py --menu          # main menu (MODE DEVELOPER button)
    python main.py --continue      # resume the checkpoint
    python main.py --dev           # developer practice, F1-F9
    python main.py --dev --fragment F04
    python main.py --dev --ending
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# SDL reads these before pygame initialises, and the game's own launcher only
# sets them when it sees the flag in sys.argv.  Mirror that for headless runs
# started through this file.
if any(flag in sys.argv for flag in ("--headless", "--screenshot", "--report")):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from nur_game.game import main  # noqa: E402  (needs src on sys.path first)

if __name__ == "__main__":
    raise SystemExit(main())