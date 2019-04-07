#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import pygame

import cw


class CWPySprite(pygame.sprite.DirtySprite):
    def __init__(self, *groups):
        pygame.sprite.DirtySprite.__init__(self, *groups)
        self.dirty = 2

        self.status = ""
        self.old_status = ""
        self.anitype = ""
        self.start_animation = 0
        self.skipped = False
        self.frame = 0

    def is_initialized(self):
        return True

    def update_scale(self):
        pass

    def get_frame(self):
        """
        システムタイマから計算した処理中のフレームを返す。
        処理落ちが発生した場合は途中が飛ばされる可能性もある。
        """
        tick = pygame.time.get_ticks()
        if self.start_animation == 0:
            self.start_animation = tick - (1000//cw.cwpy.setting.fps)
        if tick < self.start_animation:
            p_frame = self.frame + 1
        else:
            p_frame = (tick - self.start_animation) * cw.cwpy.setting.fps // 1000
            p_frame = max(self.frame+1, p_frame)
        return p_frame


class StopTheWorld(object):
    """最小化時にカウントを止める機能を持つ経過時間カウンタ。"""
    def __init__(self, start_ticks, waittime):
        self.start_ticks = start_ticks
        self.waittime = waittime
        self._stop_tick = None

    def is_waiting(self):
        return not self.is_done()

    def is_done(self):
        if cw.cwpy.setting.stop_the_world_with_iconized:
            if cw.cwpy.frame.is_iconized:
                self._stop()
                return False
            elif not self._stop_tick is None:
                self._resume()
        return self.start_ticks + self.waittime <= pygame.time.get_ticks()

    def _stop(self):
        if self._stop_tick is None:
            self._stop_tick = pygame.time.get_ticks()

    def _resume(self):
        if not self._stop_tick is None and cw.cwpy.setting.stop_the_world_with_iconized:
            self.start_ticks += pygame.time.get_ticks() - self._stop_tick
        self._stop_tick = None


class MouseHandlerSprite(CWPySprite):
    def __init__(self, *groups):
        CWPySprite.__init__(self, *groups)
        self.handling_rect = None
        self.handling = False

    def update(self, scr):
        self.update_selection()

    def update_selection(self):
        if not self.handling_rect or not cw.cwpy.mousemotion:
            return

        handling = self.handling
        if 0 <= cw.cwpy.mousepos[0] and 0 <= cw.cwpy.mousepos[1]:
            rect = self.handling_rect.move(self.rect.topleft)
            handling = rect.collidepoint(cw.cwpy.mousepos)
        else:
            handling = False

        if handling != self.handling:
            self.handling = handling
            self.update_image()

class SelectableSprite(CWPySprite):
    def __init__(self, *groups):
        self.selectable_on_event = False
        self.is_statusctrl = False
        CWPySprite.__init__(self, *groups)

        # 通常のスプライト選択処理の外にある
        # スプライトが選択状態にあるか。
        # タッチ操作用のタイルで使用する。
        self.is_pointed = False

    def lclick_event(self):
        """左クリックイベント。"""
        pass

    def rclick_event(self):
        """右クリックイベント。"""
        pass

    def ldown_event(self):
        """マウス左ボタン押下イベント。"""
        pass

    def get_selectedimage(self):
        return self.image

    def get_unselectedimage(self):
        return self.image

    def update(self, scr):
        if not cw.cwpy.is_lockmenucards(self):
            self.update_selection()

    def update_selection(self):
        if not cw.cwpy.is_lockmenucards(self):
            if cw.cwpy.pointed_tile:
                return
            if self.is_selection():
                if not self.is_pointed:
                    cw.cwpy.lazy_selection = self

            elif self is cw.cwpy.selection:
                cw.cwpy.clear_selection()

    def is_selection(self):
        """選択中スプライトか判定。"""
        if cw.cwpy.is_dealing() and not self.selectable_on_event:
            return False
        # 戦闘行動中時
        elif not cw.cwpy.is_runningevent()\
                        and cw.cwpy.battle and not cw.cwpy.battle.is_ready()\
                        and not self.selectable_on_event:
            return False
        # イベント中時、メッセージ選択バー以外
        elif cw.cwpy.is_runningevent() and not self.selectable_on_event:
            return False

        elif not self.is_pointed and cw.cwpy.keyevent.flick_status == cw.frame.FLICK_START and\
                time.process_time()-cw.cwpy.keyevent.flick_start_time <= cw.cwpy.setting.flick_time_msec/1000.0:
            # フリック操作中
            return self is cw.cwpy.keyevent.flick_sprite

        else:
            # 通常の衝突判定
            if not cw.cwpy.mousemotion and cw.cwpy.index >= 0 and cw.cwpy.index < len(cw.cwpy.list):
                if self is cw.cwpy.list[cw.cwpy.index]:
                    return True

            elif 0 <= cw.cwpy.mousepos[0] and 0 <= cw.cwpy.mousepos[1] and\
                    self.rect.collidepoint(cw.cwpy.mousepos):
                if cw.cwpy.mousemotion:
                    cw.cwpy.index = -1
                return True

        return False

def main():
    pass

if __name__ == "__main__":
    main()
