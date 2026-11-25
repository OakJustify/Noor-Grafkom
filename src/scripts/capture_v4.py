"""Actual-input visual review: opaque depth, real button death, dimming/recovery."""

import json
import math
import os

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame

from nur_game import config
from nur_game.engine import DT
from nur_game.game import Game, _source_hashes
from nur_game.physics import NurInput
from scripts.playtest_continuum import ContinuousPilot


def main():
    output=config.ROOT/'docs'/'verification'/'captures'
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    images=[]

    def capture(game,name):
        image=game.draw().copy()
        pygame.image.save(image,str(output/f'{name}.png'))
        records.append({'file':f'{name}.png','simulation':game.snapshot()})
        images.append(image)

    for name,sprint in (('01-walk',False),('02-run',True)):
        game=Game(muted=True,persist=False)
        try:
            for _ in range(100):
                game.update(DT,NurInput(move=1,sprint=sprint))
            capture(game,name)
        finally:
            game.audio.close()

    # Walk from the true new-game spawn, deliberately step on the button and
    # stop. No assigned player position, light budget, trap phase or quest flags.
    game=Game(muted=True,persist=False)
    pilot=ContinuousPilot(sprint=False)
    space=game.world.space
    try:
        game.update(DT,NurInput(action=True))
        capture(game,'03-wick-station')
        trap=game.world.hazards.machines[0]
        warning=False
        for _ in range(8000):
            x,y=game.world.player.position
            if x>trap.x-115:
                control=NurInput(move=1 if x<trap.x-4 else 0)
            else:
                control=pilot.route_control(game)
            game.update(DT,control)
            if trap.state=='warning' and not warning:
                capture(game,'04-button-warning')
                warning=True
            if game.world.dead:
                capture(game,'05-presser-death')
                break
        else:
            raise RuntimeError('Input route did not demonstrate presser death')
        if not warning or game.world.hazards.last_hit!='PRESSER':
            raise RuntimeError('Wrong death mechanism')
        for _ in range(150):
            game.update(DT,NurInput())
        if game.world.space is not space or game.world.dead:
            raise RuntimeError('Retry did not preserve the world')
        capture(game,'06-retry-same-world')
    finally:
        game.audio.close()

    # Exercise the optional lookout with real jumps, collect its ribbon and
    # carry it to the next unattended station. No solved inventory assignments.
    game=Game(muted=True,persist=False)
    pilot=ContinuousPilot(sprint=False)
    r=game.world.hazards.machines[0]
    ribbon_x=r.x-240
    try:
        game.update(DT,NurInput(action=True))
        collected=False
        for _ in range(12000):
            x,y=game.world.player.position
            if not collected and x>ribbon_x-340:
                jump=any(rect.h<30 and -12<rect.x-x<65 and rect.y<y+24
                         for rect in game.world.terrain_rects())
                action=abs(x-ribbon_x)<42 and abs(y-328)<38
                control=NurInput(move=1,jump=jump,action=action)
            else:
                control=pilot.control(game)
            game.update(DT,control)
            if game.world.dead:
                raise RuntimeError('Optional ribbon route died: '+game.world.death_reason)
            if game.refuges.threads and not collected:
                capture(game,'13-ribbon-on-lookout')
                collected=True
            if game.refuges.delivered:
                capture(game,'14-ribbon-deposited')
                break
        else:
            raise RuntimeError('Optional ribbon route did not collect/deposit its ribbon')
    finally:
        game.audio.close()

    game=Game(muted=True,persist=False)
    try:
        capture(game,'07-bright')
        for threshold,name in ((.65,'08-uncertain'),(.35,'09-fractured'),(.09,'10-near-dark'),(0,'11-blackout')):
            for _ in range(8000):
                game.update(DT,NurInput(focus=True))
                if game.lantern.charge<=threshold:
                    break
            else:
                raise RuntimeError('Focus did not drain light')
            capture(game,name)
        game.update(DT,NurInput(action=True))
        capture(game,'12-recovery')
    finally:
        game.audio.close()
    sheet=pygame.Surface((1440,270*math.ceil(len(images)/3)))
    for i,image in enumerate(images):
        sheet.blit(pygame.transform.smoothscale(image,(480,270)),((i%3)*480,(i//3)*270))
    pygame.image.save(sheet,str(output/'preview.png'))
    (output/'captures.json').write_text(json.dumps({
        'kind':'Actual D, Shift, E, jump and F inputs from new-game spawn; intentional button death; no position/light/trap assignments',
        'records':records,'sources':_source_hashes()},indent=2,ensure_ascii=False)+'\n')
    print(f'Saved {len(images)} actual-input captures to {output}')
    pygame.quit()


if __name__=='__main__':
    main()
