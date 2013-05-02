#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import pygame
from pygame.locals import *

import cw


def animate_sprite(sprite, anitype, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        return

    sprite.old_status = sprite.status
    sprite.status = anitype

    skip = _get_skipstatus(clearevent)

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and sprite.status == anitype:
        sprite.update(cw.cwpy.scr)

        skip = _get_skipstatus(clearevent)
        if not skip:
            cw.cwpy.draw()
            cw.cwpy.tick_clock()

        if clearevent:
            pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

def animate_sprites(sprites, anitype, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if [spr for spr in sprites if not hasattr(spr, "update_" + anitype)]:
        print "Not found " + anitype + " animation."
        return

    for sprite in sprites:
        sprite.old_status = sprite.status
        sprite.status = anitype

    animating = True
    skip = _get_skipstatus(clearevent)

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        for sprite in sprites:
            sprite.update(cw.cwpy.scr)

        skip = _get_skipstatus(clearevent)
        if not skip:
            cw.cwpy.draw()
            cw.cwpy.tick_clock()

        if clearevent:
            pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

        animating = False

        for sprite in sprites:
            if sprite.status == anitype:
                animating = True
                break

    if skip:
        cw.cwpy.draw()

def animate_sprites2(sprandanimes, clearevent=True):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    for spr, anitype in sprandanimes:
        if not hasattr(spr, "update_" + anitype):
            print "Not found " + anitype + " animation."
            return

    for sprite, anitype in sprandanimes:
        sprite.old_status = sprite.status
        sprite.status = anitype

    animating = True
    skip = _get_skipstatus(clearevent)

    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        for sprite, anitype in sprandanimes:
            sprite.update(cw.cwpy.scr)

        skip = _get_skipstatus(clearevent)
        if not skip:
            cw.cwpy.draw()
            cw.cwpy.tick_clock()

        if clearevent:
            pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
        else:
            cw.cwpy.mousepos = pygame.mouse.get_pos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

        animating = False

        for sprite, anitype in sprandanimes:
            if sprite.status == anitype:
                animating = True
                break

    if skip:
        cw.cwpy.draw()

def _get_skipstatus(clearevent):
    if not clearevent:
        return False

    keyin = cw.cwpy.keyevent.get_pressed()
    breakflag = pygame.event.peek((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))

    if breakflag or keyin[K_RETURN] > cw.cwpy.keyevent.threshold:
        return True

    return False

def main():
    pass

if __name__ == "__main__":
    main()
