"""Adapter that keeps the tested boss reconciliation inputs in world coords."""

from ..boss import AlzheimerBoss
from ..continuum import REGIONS


class LocalFinale:
    """Retain tested reconciliation inputs while translating the final encounter."""
    def __init__(self,seed):
        self.offset=REGIONS[-1].start
        self.local=AlzheimerBoss(REGIONS[-1].source.echoes,seed)

    def __getattr__(self,key):
        return getattr(self.local,key)

    def update(self,dt,player,action,illumination,protected):
        return self.local.update(dt,(player[0]-self.offset,player[1]),action,illumination,protected)

    def draw(self,screen,camera,illumination):
        self.local.draw(screen,camera-self.offset,illumination)


