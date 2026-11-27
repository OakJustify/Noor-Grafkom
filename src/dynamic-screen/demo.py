"""Demo: responsive window."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pygame
from detect import get_monitor_size
from window import create_window

pygame.init()
w, h = get_monitor_size()
screen = create_window()
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
    screen.fill((20, 20, 30))
    pygame.display.flip()
pygame.quit()