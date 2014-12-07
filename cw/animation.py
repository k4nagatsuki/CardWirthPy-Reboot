#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import pygame

import cw


def animate_sprite(sprite, anitype, clearevent=True, background=False):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        return

    if clearevent:
        lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy.lock_menucards = True

    sprite.old_status = sprite.status
    sprite.status = anitype

    skip = _get_skipstatus(clearevent)

    cw.cwpy.draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and sprite.status == anitype:
        clip = pygame.Rect(sprite.rect)
        sprite.update(cw.cwpy.scr_draw)
        clip.union_ip(sprite.rect)

        skip |= _get_skipstatus(clearevent)
        clip = _inputevent(clip, clearevent)

        if not skip:
            if background:
                cw.cwpy.draw()
            else:
                cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

    cw.cwpy.input(inputonly=clearevent)
    cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

    if clearevent and cw.cwpy.lock_menucards:
        cw.cwpy.lock_menucards = lock_menucards

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

    if clearevent:
        lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy.lock_menucards = True

    for sprite, anitype in sprandanimes:
        sprite.old_status = sprite.status
        sprite.status = anitype

    animating = True
    skip = _get_skipstatus(clearevent)

    cw.cwpy.draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        clip = None
        for sprite, anitype in sprandanimes:
            if sprite.status <> anitype:
                continue
            if clip:
                clip.union_ip(sprite.rect)
            else:
                clip = pygame.Rect(sprite.rect)
            sprite.update(cw.cwpy.scr_draw)
            clip.union_ip(sprite.rect)

        skip |= _get_skipstatus(clearevent)
        clip = _inputevent(clip, clearevent)

        if not skip:
            cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

        animating = False

        for sprite, anitype in sprandanimes:
            if sprite.status == anitype:
                animating = True
                break

    cw.cwpy.input(inputonly=clearevent)
    cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

    if clearevent and cw.cwpy.lock_menucards:
        cw.cwpy.lock_menucards = lock_menucards

def _inputevent(clip, clearevent):
    cw.cwpy.update_mousepos()
    sel = cw.cwpy.selection
    cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
    if sel <> cw.cwpy.selection:
        clip.union_ip(cw.cwpy.statusbar.rect)
    cw.cwpy.input(inputonly=clearevent)
    cw.cwpy.eventhandler.run()
    return clip

def _get_skipstatus(clearevent):
    if not clearevent:
        return False

    keyin = cw.cwpy.keyevent.get_pressed()
    breakflag = pygame.event.peek((pygame.locals.MOUSEBUTTONDOWN,
                                   pygame.locals.MOUSEBUTTONUP,
                                   pygame.locals.KEYDOWN,
                                   pygame.locals.KEYUP))

    if breakflag or keyin[pygame.locals.K_RETURN] > cw.cwpy.keyevent.threshold:
        return True

    return False

def main():
    pass

if __name__ == "__main__":
    main()
