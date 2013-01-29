#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import pygame
from pygame.locals import *

import cw


def animate_sprite(sprite, anitype, speedrate=1, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        return

    sprite.status = anitype

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and sprite.status == anitype:
        sprite.update(cw.cwpy.scr)
        cw.cwpy.draw()
        cw.cwpy.tick_clock(speedrate=speedrate)
        if clearevent:
            pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

def animate_sprites(sprites, anitype, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if [spr for spr in sprites if not hasattr(spr, "update_" + anitype)]:
        print "Not found " + anitype + " animation."
        return

    for sprite in sprites:
        sprite.status = anitype

    animating = True

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        for sprite in sprites:
            sprite.update(cw.cwpy.scr)

        cw.cwpy.draw()
        cw.cwpy.tick_clock()
        if clearevent:
            pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()
        animating = False

        for sprite in sprites:
            if sprite.status == anitype:
                animating = True
                break

def animate_sprites2(sprandanimes, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    for spr, anitype in sprandanimes:
        if not hasattr(spr, "update_" + anitype):
            print "Not found " + anitype + " animation."
            return

    for sprite, anitype in sprandanimes:
        sprite.status = anitype

    animating = True

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        for sprite, anitype in sprandanimes:
            sprite.update(cw.cwpy.scr)

        cw.cwpy.draw()
        cw.cwpy.tick_clock()
        if clearevent:
            pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()
        animating = False

        for sprite, anitype in sprandanimes:
            if sprite.status == anitype:
                animating = True
                break

def main():
    pass

if __name__ == "__main__":
    main()
