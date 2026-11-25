"""Four depth planes: solid foreground, gameplay, small props, large scenery."""

from types import SimpleNamespace

import numpy as np
import pygame

from .art import NurArt
from .continuum import REGIONS, region_at
from .scenery import TILE, scenery_tile, sky_surface


def biome(index):
    return 0 if index < 4 else min(4, 1 + (index - 4) // 6)


class Vistas(NurArt):
    # User numbering is front-to-back; painting necessarily runs in reverse.
    layer_order = ("large_background", "small_objects", "interaction", "foreground")
    parallax = (0.12, 0.82, 1.0, 1.12)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.sky=sky_surface(self.size,self.seed)
        self._grade=pygame.Surface((240,135))
        self._haze=pygame.Surface(self.size,pygame.SRCALPHA)
        self._shade_x=np.arange(240)[:,None]*4
        self._shade_y=np.arange(135)[None,:]*4

    def set_seed(self,seed):
        super().set_seed(seed)
        self.sky=sky_surface(self.size,self.seed)

    def background(self,index):
        # Inspection API; live scenery is anchored to chunks, not region addresses.
        if index not in self._backgrounds:
            if len(self._backgrounds)>=6:
                self._backgrounds.pop(next(iter(self._backgrounds)))
            chunk=int(REGIONS[index].start*self.parallax[0]//TILE)
            forest=biome(index)==3
            self._backgrounds[index]=tuple(scenery_tile(n,chunk,self.seed,forest) for n in (4,3,1))
        return self._backgrounds[index]

    def _plane(self,screen,camera,plane,speed):
        offset=round(camera*speed)
        first=offset//TILE
        for chunk in range(first,first+2):
            # Object identity/style belongs to its world anchor. Region crossing
            # never swaps it, fades it, or moves it relative to its own plane.
            world_x=(chunk+.5)*TILE/speed
            forest=biome(region_at(world_x).index)==3
            image=scenery_tile(plane,chunk,self.seed,forest)
            screen.blit(image,(chunk*TILE-offset,0))

    def draw_background(self,screen,camera,index,time,player_x=None):
        screen.blit(self.sky,(0,0))
        self._plane(screen,camera,4,self.parallax[0])
        self._plane(screen,camera,3,self.parallax[1])

    def draw_foreground(self,screen,camera,index,player,time):
        self._plane(screen,camera,1,self.parallax[-1])

    def draw_refuge(self,screen,x,visited):
        # A compact physical wick cabinet, not a character silhouette.
        pygame.draw.rect(screen,(58,87,87),(round(x)-21,390,42,70),border_radius=4)
        pygame.draw.rect(screen,(155,145,111),(round(x)-18,395,36,54),border_radius=2)
        pygame.draw.rect(screen,(64,92,95),(round(x)-12,401,24,33),border_radius=3)
        pygame.draw.rect(screen,(228,184,113),(round(x)-4,415,8,15),border_radius=2)
        pygame.draw.ellipse(screen,(254,225,152),(round(x)-3,408,6,11))
        pygame.draw.circle(screen,(146,191,163) if visited else (247,201,123),(round(x)+13,441),3)

    def draw_world_terrain(self,screen,world,camera,light):
        for r in REGIONS:
            if r.start>camera+self.size[0]+100 or r.end<camera-100:
                continue
            view=SimpleNamespace(chapter=r.index,level=SimpleNamespace(gate=None,plate=None,
                rope=world.level.rope,saws=tuple(s for s in world.level.saws if r.start<=s[0]<r.end)),
                terrain_rects=lambda r=r:r.terrain,gate_body=None,crates=[c for c in world.crates if r.start<=c.body.position.x<r.end],
                ropes=world.ropes if r.index==3 else (),time=world.time,
                saw_positions=lambda r=r:[s for s in world.saw_positions() if r.start<=s[0]<r.end])
            self.draw_terrain(screen,view,camera,light)
            for rect in r.terrain:
                if rect.h>30:
                    colour=(171,186,127) if biome(r.index)==3 else (224,186,135)
                    pygame.draw.line(screen,colour,(rect.x-camera,rect.y),(rect.x+rect.w-camera,rect.y),3)
            gate=world.gates.get(r.index)
            if gate and not gate['open']:
                x=gate['rect'].x-camera
                pygame.draw.rect(screen,(97,121,133),(x,-20,28,480))
                for y in range(0,455,24):
                    pygame.draw.line(screen,(204,184,147),(x+3,y),(x+25,y+12),2)
            plate=r.source.level.plate
            if plate:
                pygame.draw.rect(screen,(227,190,120),(plate.x+r.start-camera,plate.y,plate.w,plate.h))
        world.hazards.draw(screen,camera)

    def grade(self,screen,origin,lantern,time):
        charge=lantern.illumination
        if charge<=0:
            screen.fill((0,0,0))
            return
        if charge<.7:
            grey=pygame.transform.grayscale(screen)
            grey.set_alpha(round((.7-charge)*140))
            screen.blit(grey,(0,0))
        distance=np.hypot(self._shade_x-origin[0],self._shade_y-origin[1])
        local=np.clip(1-distance/max(1,lantern.radius),0,1)**.7
        gain=np.clip(charge*.95+local*(1-charge*.6),.012,1)
        tint=np.array((.72+.28*charge,.75+.25*charge,.95+.05*charge))
        pixels=pygame.surfarray.pixels3d(self._grade)
        pixels[:]=np.clip(gain[:,:,None]*tint*255,0,255).astype(np.uint8)
        del pixels
        screen.blit(pygame.transform.smoothscale(self._grade,self.size),(0,0),special_flags=pygame.BLEND_RGB_MULT)
        self._haze.fill((0,0,0,0))
        for radius in range(110,0,-6):
            alpha=round((1-radius/110)**2*(22+35*charge))
            pygame.draw.circle(self._haze,(255,205,130,alpha),(round(origin[0]),round(origin[1])),radius)
        screen.blit(self._haze,(0,0))

    def draw_player(self,screen,player,camera,illumination,facing,time,velocity=(0,0),grounded=True,animation=None,carried=True):
        from .wisp import PIVOT, facing_sprite
        image=facing_sprite(animation.pose,animation.frame,1 if facing>=0 else -1,carried)
        image=pygame.transform.smoothscale(image,(135,135))
        pivot=PIVOT[0] if facing>=0 else 103-PIVOT[0]
        x,y=player[0]-camera,player[1]
        pygame.draw.ellipse(screen,(44,66,72),(round(x)-23,round(y)+18,46,9))
        screen.blit(image,(round(x-pivot*1.3),round(y-PIVOT[1]*1.3-7)))
