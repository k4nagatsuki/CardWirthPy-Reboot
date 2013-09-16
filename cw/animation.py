#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import gc
import pygame
from pygame.locals import *

import cw


def animate_sprite(sprite, anitype, clearevent=True, background=False):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        return

    sprite.old_status = sprite.status
    sprite.status = anitype

    skip = _get_skipstatus(clearevent)

    gc.disable()
    cw.cwpy.draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and sprite.status == anitype:
        clip = sprite.rect
        sprite.update(cw.cwpy.scr)
        clip = clip.union(sprite.rect)

        skip = _get_skipstatus(clearevent)
        if not skip:
            if background:
                cw.cwpy.draw()
            else:
                cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

        if not clearevent:
            cw.cwpy.update_mousepos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

    gc.enable()

    cw.cwpy.input(inputonly=True)
    cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

def animate_sprites(sprites, anitype, clearevent=True):
    """spritesに含まれる全てのスプライトをanitypeの
    アニメーションで動かす。
    """
    sprandanimes = map(lambda s: (s, anitype), sprites)
    animate_sprites2(sprandanimes, clearevent)

def animate_sprites2(sprandanimes, clearevent=True):
    """スプライト毎にアニメーション内容を指定する。
    """
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

    gc.disable()
    cw.cwpy.draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        clip = None
        for sprite, anitype in sprandanimes:
            if clip:
                clip.union_ip(sprite.rect)
            else:
                clip = pygame.Rect(sprite.rect)
            sprite.update(cw.cwpy.scr)
            clip.union_ip(sprite.rect)

        skip = _get_skipstatus(clearevent)
        if not skip:
            cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

        if not clearevent:
            cw.cwpy.update_mousepos()
            cw.cwpy.events = pygame.event.get()
            cw.cwpy.eventhandler.run()

        animating = False

        for sprite, anitype in sprandanimes:
            if sprite.status == anitype:
                animating = True
                break

    gc.enable()

    cw.cwpy.input(inputonly=True)
    cw.cwpy.eventhandler.run()

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
