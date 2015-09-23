#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
        self.frame = 0

    def is_initialized(self):
        return True

    def update_scale(self):
        pass

class SelectableSprite(CWPySprite):
    def __init__(self, *groups):
        self.selectable_on_event = False
        CWPySprite.__init__(self, *groups)

    def lclick_event(self):
        """左クリックイベント。"""
        pass

    def rclick_event(self):
        """右クリックイベント。"""
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
            if self.is_selection():
                if self is not cw.cwpy.selection:
                    cw.cwpy.change_selection(self)

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
        # 通常の衝突判定
        elif not cw.cwpy.mousemotion and cw.cwpy.index >= 0 and cw.cwpy.index < len(cw.cwpy.list):
            if self is cw.cwpy.list[cw.cwpy.index]:
                return True

        elif 0 <= cw.cwpy.mousepos[0] and 0 <= cw.cwpy.mousepos[1] and\
                self.rect.collidepoint(cw.cwpy.mousepos):
            return True

        return False

def main():
    pass

if __name__ == "__main__":
    main()
