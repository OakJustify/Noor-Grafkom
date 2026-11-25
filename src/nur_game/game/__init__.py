"""NUR v4 continuous game controller.

Public names stay at ``nur_game.game.<name>``.  Responsibilities are split into
:mod:`controller` (simulation), :mod:`presentation` (drawing), :mod:`persistence`
(checkpoints), :mod:`finale` (legacy adapter) and :mod:`cli` (launcher).
"""

from ..baseline_game import EVENT_SOUNDS, _source_hashes
from .cli import main
from .controller import Game
from .finale import LocalFinale

__all__ = ["EVENT_SOUNDS", "Game", "LocalFinale", "_source_hashes", "main"]
