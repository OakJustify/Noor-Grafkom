"""Command-line launcher for the continuous NUR campaign."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from .. import config
from ..baseline_game import _source_hashes
from .controller import Game


def main(argv=None):
    parser=argparse.ArgumentParser(description='NUR v4 · continuous storybook memory landscape')
    parser.add_argument('--room',type=int,choices=range(1,30),default=1,help='Debug spawn region; world remains continuous')
    parser.add_argument('--seed',type=int,default=config.SEED)
    parser.add_argument('--continue',dest='resume',action='store_true')
    for name in ('menu','mute','no-save','headless'):
        parser.add_argument('--'+name,action='store_true')
    parser.add_argument('--frames',type=int,default=0)
    parser.add_argument('--screenshot',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    headless=args.headless or args.screenshot is not None or args.report is not None
    if headless:
        os.environ.setdefault('SDL_VIDEODRIVER','dummy')
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        if args.frames<=0:
            parser.error('Headless/capture requires --frames > 0')
    game=Game(room=args.room-1,seed=args.seed,start=not args.menu,muted=args.mute,persist=not args.no_save)
    if args.resume and not game.load_save():
        game.state='menu'
    clock=pygame.time.Clock()
    frames=0
    while game.running:
        for event in pygame.event.get():
            game.event(event)
        dt=1/config.FPS if headless else min(.1,clock.tick(config.FPS)/1000)
        game.update(dt)
        canvas=game.draw()
        frames+=1
        if args.screenshot and frames==args.frames:
            args.screenshot.parent.mkdir(parents=True,exist_ok=True)
            pygame.image.save(canvas,str(args.screenshot))
        if headless and frames>=args.frames:
            break
        if not headless:
            game.display.blit(pygame.transform.smoothscale(canvas,game.display.get_size()),(0,0))
            pygame.display.flip()
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({"simulation":game.snapshot(),"sources":_source_hashes()},indent=2,ensure_ascii=False))
    game.audio.close()
    pygame.quit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
