#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
from pygame.locals import *

import cw


def animate_sprite(sprite, anitype, speedrate=1):
    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        return

    sprite.status = anitype

    framecount = 0
    while cw.cwpy.is_running() and sprite.status == anitype:
        framecount += 1
        sprite.update(cw.cwpy.scr)
        cw.cwpy.draw()
        cw.cwpy.tick_clock(speedrate=speedrate)
        pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))

def animate_sprites(sprites, anitype):
    if [spr for spr in sprites if not hasattr(spr, "update_" + anitype)]:
        print "Not found " + anitype + " animation."
        return

    for sprite in sprites:
        sprite.status = anitype

    animating = True

    while cw.cwpy.is_running() and animating:
        for sprite in sprites:
            sprite.update(cw.cwpy.scr)

        cw.cwpy.draw()
        cw.cwpy.tick_clock()
        pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))
        animating = False

        for sprite in sprites:
            if sprite.status == anitype:
                animating = True
                break

def main():
    pass

if __name__ == "__main__":
    main()
