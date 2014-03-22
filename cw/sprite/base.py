#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw


class CWPySprite(pygame.sprite.DirtySprite):
    def __init__(self, *groups):
        pygame.sprite.DirtySprite.__init__(self, *groups)
        self.dirty = 2

class SelectableSprite(CWPySprite):
    def __init__(self, *groups):
        self._selectable_on_event = False
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
        if not cw.cwpy.lock_menucards:
            self.update_selection()

    def update_selection(self):
        if not cw.cwpy.lock_menucards and not cw.cwpy.is_showingdlg() and not pygame.event.peek(pygame.locals.USEREVENT):
            if self.is_selection():
                if self is not cw.cwpy.selection:
                    cw.cwpy.change_selection(self)

            elif self is cw.cwpy.selection:
                cw.cwpy.clear_selection()

    def is_selection(self):
        """選択中スプライトか判定。"""
        if cw.cwpy.is_dealing():
            return False
        # 戦闘行動中時
        elif not cw.cwpy.is_runningevent()\
                        and cw.cwpy.battle and cw.cwpy.battle.is_running():
            return False
        # イベント中時、メッセージ選択バー以外
        elif cw.cwpy.is_runningevent() and not self._selectable_on_event:
            return False
        # 通常の衝突判定
        elif not cw.cwpy.mousemotion and cw.cwpy.index >= 0:
            if self is cw.cwpy.list[cw.cwpy.index]:
                return True

        elif self.rect.collidepoint(cw.cwpy.mousepos):
            return True

        return False

def main():
    pass

if __name__ == "__main__":
    main()
