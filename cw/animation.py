#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import pygame

import cw


def animate_sprite(sprite, anitype, clearevent=True, background=False, statusbutton=False, battlespeed=False):
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        print sprite
        return

    if clearevent:
        lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy.lock_menucards = True
        selection = cw.cwpy.selection

    sprite.old_status = sprite.status
    sprite.status = anitype
    sprite.skipped = False
    sprite.start_animation = pygame.time.get_ticks()

    if battlespeed:
        if hasattr(sprite, "battlespeed"):
            sprite.battlespeed = True

    skip = _get_skipstatus(clearevent)

    cw.cwpy.lazy_draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and sprite.status == anitype:
        clip = pygame.Rect(sprite.rect)
        sprite.skipped |= skip
        sprite.update(cw.cwpy.scr_draw)
        clip.union_ip(sprite.rect)
        if sprite.status <> anitype:
            if background:
                cw.cwpy.draw()
            else:
                cw.cwpy.draw(clip=clip)
            break

        skip |= _get_skipstatus(clearevent)

        if skip:
            cw.cwpy.add_lazydraw(clip)
        else:
            clip = _inputevent(clip, clearevent, statusbutton)
            if background:
                cw.cwpy.draw()
            else:
                cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

    sprite.skipped = False

    if battlespeed:
        if hasattr(sprite, "battlespeed"):
            sprite.battlespeed = False

    if statusbutton:
        cw.cwpy.clear_inputevents()
    else:
        cw.cwpy.update_mousepos()
        cw.cwpy.input(inputonly=clearevent)
        cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

    if clearevent and cw.cwpy.lock_menucards:
        cw.cwpy.lock_menucards = lock_menucards
    if clearevent and selection and cw.cwpy.selection <> selection:
        cw.cwpy.change_selection(selection)

    return skip

def animate_sprites(sprites, anitype, clearevent=True, battlespeed=False):
    """spritesに含まれる全てのスプライトをanitypeの
    アニメーションで動かす。
    """
    sprandanimes = map(lambda s: (s, anitype), sprites)
    animate_sprites2(sprandanimes, clearevent, battlespeed)

def animate_sprites2(sprandanimes, clearevent=True, battlespeed=False):
    """スプライト毎にアニメーション内容を指定する。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    for spr, anitype in sprandanimes:
        if not hasattr(spr, "update_" + anitype):
            print "Not found " + anitype + " animation."
            print sprandanimes
            return

    if clearevent:
        lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy.lock_menucards = True
        selection = cw.cwpy.selection

    tick = pygame.time.get_ticks()
    for sprite, anitype in sprandanimes:
        sprite.old_status = sprite.status
        sprite.status = anitype
        sprite.skipped = False
        sprite.start_animation = tick
        if battlespeed:
            if hasattr(sprite, "battlespeed"):
                sprite.battlespeed = True

    animating = True
    skip = _get_skipstatus(clearevent)

    cw.cwpy.lazy_draw()
    while cw.cwpy.is_running() and not cw.cwpy.cut_animation and animating:
        clip = None
        upd = False
        for sprite, anitype in sprandanimes:
            if sprite.status <> anitype:
                continue
            if clip:
                clip.union_ip(sprite.rect)
            else:
                clip = pygame.Rect(sprite.rect)
            sprite.skipped |= skip
            sprite.update(cw.cwpy.scr_draw)
            if sprite.status == anitype:
                upd = True
            clip.union_ip(sprite.rect)
        if not upd:
            cw.cwpy.draw(clip=clip)
            break

        skip |= _get_skipstatus(clearevent)

        if skip:
            cw.cwpy.add_lazydraw(clip)
        else:
            clip = _inputevent(clip, clearevent, False)
            cw.cwpy.draw(clip=clip)
            cw.cwpy.tick_clock()

        animating = False

        for sprite, anitype in sprandanimes:
            if sprite.status == anitype:
                animating = True
                break

    for sprite, anitype in sprandanimes:
        sprite.skipped = False
        if battlespeed:
            if hasattr(sprite, "battlespeed"):
                sprite.battlespeed = False

    cw.cwpy.update_mousepos()
    cw.cwpy.input(inputonly=clearevent)
    cw.cwpy.eventhandler.run()

    if skip:
        cw.cwpy.draw()

    if clearevent and cw.cwpy.lock_menucards:
        cw.cwpy.lock_menucards = lock_menucards
    if clearevent and not cw.cwpy.selection is selection:
        cw.cwpy.change_selection(selection)

    return skip

def _inputevent(clip, clearevent, statusbutton):
    if statusbutton:
        cw.cwpy.clear_inputevents()
    else:
        cw.cwpy.update_mousepos()
        sel = cw.cwpy.selection
        cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
        if sel <> cw.cwpy.selection:
            clip.union_ip(cw.cwpy.statusbar.rect)
        cw.cwpy.input(inputonly=clearevent)
        cw.cwpy.eventhandler.run()
    return clip

def start_animation(sprite, anitype):
    """spriteのアニメーションを開始する。
    アニメーションは他のイベント進行と平行して実行される。
    animate_sprite()と違ってフレームが進まなかったり飛んだりする
    場合があるので、update_<anitype>()の実装は、そうした場合でも
    正しく動くように行わなければならない。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if not hasattr(sprite, "update_" + anitype):
        print "Not found " + anitype + " animation."
        print sprite
        return

    if sprite.anitype == "":
        sprite.old_status = sprite.status
    sprite.status = anitype
    sprite.anitype = anitype
    sprite.start_animation = pygame.time.get_ticks()
    sprite.frame = 0

    cw.cwpy.animations.add(sprite)

def _get_skipstatus(clearevent):
    if not clearevent and (cw.cwpy.keyevent.is_keyin(pygame.locals.K_RETURN) or cw.cwpy.keyevent.is_mousein()):
        cw.cwpy.cut_animation = True
        return True

    if not clearevent or not cw.cwpy.setting.can_skipanimation:
        return False

    breakflag = False
    events = pygame.event.get((pygame.locals.MOUSEBUTTONDOWN,
                               pygame.locals.MOUSEBUTTONUP,
                               pygame.locals.KEYDOWN,
                               pygame.locals.KEYUP))
    for e in events:
        if e.type in (pygame.locals.MOUSEBUTTONDOWN, pygame.locals.MOUSEBUTTONUP,
                      pygame.locals.KEYDOWN, pygame.locals.KEYUP):
            if e.type in (pygame.locals.MOUSEBUTTONUP, pygame.locals.MOUSEBUTTONDOWN) and hasattr(e, "button"):
                if not cw.cwpy.setting.can_skipwait_with_wheel and e.button in (4, 5):
                    # ホイールによる空白時間スキップ無効の設定
                    pygame.event.post(e)
                    continue
            breakflag = True
        pygame.event.post(e)

    if not breakflag:
        breakflag = cw.cwpy.event.get_event() and cw.cwpy.event.is_stoped()

    if breakflag or cw.cwpy.keyevent.is_keyin(pygame.locals.K_RETURN) or cw.cwpy.keyevent.is_mousein():
        return True

    return False

def main():
    pass

if __name__ == "__main__":
    main()
