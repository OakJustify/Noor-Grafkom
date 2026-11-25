"""Stable illustrated scenery: opaque objects, restrained scale, anchored chunks."""

import math
import random
from functools import lru_cache

import pygame

from .illustration import Ink

TILE = 960
PROP_LIMIT = 120  # Below 2× the visible player's hood-to-cloak height (~88 px).


def foliage(art, x, y, radius, colour):
    # Overlapping opaque lobes read as one crown, not translucent cloud fragments.
    for dx, dy, scale in ((-.55,.05,.7),(.5,.12,.75),(0,-.32,.85),(0,.3,.8)):
        r = radius * scale
        art.ellipse(colour,(x+dx*radius-r,y+dy*radius-r*.7,r*2,r*1.4))


def sapling(art, x, ground, height, colour=(98,139,121)):
    art.poly((93,110,104),[(x-4,ground),(x-2,ground-height*.8),
                         (x+3,ground-height*.8),(x+6,ground)])
    art.line((93,110,104),(x,ground-height*.45),(x-18,ground-height*.7),3)
    foliage(art,x,ground-height*.72,height*.28,colour)
    foliage(art,x+5,ground-height*.88,height*.21,(125,157,127))


def building(art,x,bottom,width,height,colour):
    top=bottom-height
    shade=tuple(max(0,c-20) for c in colour)
    art.rect(colour,(x,top,width,height))
    art.poly(shade,[(x+width*.82,top),(x+width,top-6),(x+width,bottom),(x+width*.82,bottom)])
    art.poly((95,114,125),[(x-16,top+2),(x+width*.42,top-55),
                         (x+width+15,top+2),(x+width+12,top+12),(x-14,top+12)])
    art.line((166,167,151),(x-14,top+3),(x+width*.42,top-50),3)
    for offset in range(32,round(width)-30,72):
        art.rect((111,142,150),(x+offset,top+42,40,81),radius=16)
        art.rect((202,213,191),(x+offset+5,top+48,30,68),radius=12)
        art.line((133,153,151),(x+offset+20,top+50),(x+offset+20,top+114),2)
        art.line((133,153,151),(x+offset+5,top+84),(x+offset+35,top+84),2)
        art.rect(shade,(x+offset-3,top+124,46,5))
    for y in range(round(top)+155,bottom,29):
        art.line(tuple(max(0,c-6) for c in colour),(x,y),(x+width*.81,y),1)
    art.rect(shade,(x+width*.43,bottom-78,43,78),radius=16)
    art.line((169,174,154),(x,bottom),(x+width,bottom),3)


@lru_cache(maxsize=32)
def scenery_tile(plane, chunk, seed, forest):
    rng=random.Random(seed+chunk*371+plane*7919)
    art=Ink((TILE,540))
    if plane==4:
        # Everything here is large-scale. Continuous hill endpoints use global x.
        for depth,base,amplitude,colour in (
            (0,255,51,(155,183,181)),(1,314,40,(125,162,164)),
            (2,371,23,(103,148,151))):
            points=[(0,540)]
            for x in range(0,TILE+1,16):
                u=x+chunk*TILE
                y=base+math.sin(u*.003+depth*2)*amplitude+math.sin(u*.008+depth)*9
                points.append((x,y))
            points.append((TILE,540))
            art.poly(colour,points)
        if forest:
            for x in range(70,950,110):
                height=rng.randrange(165,265)
                sapling(art,x,434,height,(92,133,131))
        else:
            building(art,92,422,290,186,(179+rng.randrange(-7,8),192,176))
            building(art,490,437,360,235,(191+rng.randrange(-7,8),191,171))
            sapling(art,420,438,165,(106,146,137))
        # Opaque water/ground mass; broad quiet space behind the playable silhouette.
        art.rect((117,159,157),(0,445,TILE,95))
        for x in range(30,TILE,110):
            art.line((151,180,164),(x,464),(x+55,464),1)
    elif plane==3:
        for slot,x in enumerate((105,280,465,650,830)):
            ground=449
            kind=(chunk+slot)%5
            if kind==0:  # Table, 108×56; no walls or building facades.
                art.rect((143,129,104),(x-52,ground-54,104,9),radius=2)
                art.rect((112,115,101),(x-44,ground-45,6,45))
                art.rect((112,115,101),(x+38,ground-45,6,45))
                art.ellipse((184,169,134),(x-10,ground-68,21,14))
                art.rect((181,164,130),(x-8,ground-69,17,12),radius=2)
            elif kind==1:
                sapling(art,x,ground,108)
            elif kind==2:
                art.rect((130,137,112),(x-28,ground-45,56,9),radius=2)
                art.rect((111,121,107),(x-24,ground-36,5,36))
                art.rect((111,121,107),(x+19,ground-36,5,36))
                art.rect((139,146,118),(x-27,ground-79,54,27),radius=3)
                for dx in (-21,21):
                    art.line((112,127,111),(x+dx,ground-55),(x+dx,ground-35),3)
            elif kind==3:
                art.poly((171,136,109),[(x-24,ground-32),(x+24,ground-32),
                                      (x+17,ground),(x-17,ground)])
                art.line((204,162,117),(x-26,ground-32),(x+26,ground-32),4)
                foliage(art,x,ground-54,26,(114,151,118))
            else:
                art.rect((118,131,119),(x-25,ground-44,50,44),radius=3)
                for y in (ground-32,ground-16):
                    art.line((169,175,138),(x-21,y),(x+21,y),2)
                art.ellipse((171,153,116),(x-9,ground-60,18,16))
    else:  # Layer 1 frames the image. No player-dependent alpha erasure.
        dark=(36,65,70)
        art.poly(dark,[(64,0),(82,0),(86,540),(67,540)])
        art.line((74,99,95),(70,0),(75,537),3)
        if forest:
            art.line(dark,(75,14),(275,45),12)
            art.line(dark,(180,31),(320,96),7)
            for x,y in ((105,31),(182,44),(267,59),(317,94)):
                foliage(art,x,y,50,dark)
        else:
            art.line(dark,(82,30),(930,53),3)
        for x in (160,535,760):
            for dx in (-15,0,12):
                art.poly((41,78,76),[(x+dx,540),(x+dx-16,492-abs(dx)),
                                      (x+dx+3,513),(x+dx+5,540)])
    return art.finish()


def sky_surface(size, seed):
    art=pygame.Surface(size)
    top,bottom=(116,174,185),(247,217,175)
    for y in range(size[1]):
        t=y/(size[1]-1)
        colour=tuple(round(a+(b-a)*t) for a,b in zip(top,bottom))
        pygame.draw.line(art,colour,(0,y),(size[0],y))
    pygame.draw.circle(art,(253,233,188),(680+seed%90,155),43)
    clouds=Ink(size)
    for x,y,w in ((62,146,160),(349,113,198),(757,187,110)):
        clouds.ellipse((224,217,191),(x,y,w,17))
        clouds.ellipse((227,222,197),(x+w*.23,y-10,w*.6,25))
    art.blit(clouds.finish(),(0,0))
    return art
