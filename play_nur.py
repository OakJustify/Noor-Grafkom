"""Launcher for NÜR. Run ``python play_nur.py --headless --frames 5`` for a smoke test."""

import os
import sys

# SDL reads these before pygame.initialise(); set them for headless runs.
if "--headless" in sys.argv or "--screenshot" in sys.argv or "--report" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from nur_game.game import main

raise SystemExit(main())
