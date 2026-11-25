"""F3 sanity API: state, perception effects and render-only phantoms."""

from .core import SanityManager
from .effects import HallucinationAudio, HallucinationVisuals
from .phantoms import Phantom, PhantomDirector

__all__ = [
    "HallucinationAudio", "HallucinationVisuals", "Phantom",
    "PhantomDirector", "SanityManager",
]
