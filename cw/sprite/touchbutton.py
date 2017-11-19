#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import pygame.locals

import cw
import base


class TouchButton(base.SelectableSprite):
    """
    タッチ操作を想定した大きめのボタン。
    アイコン、ボタン名、簡単な解説を表示する。
    """

    def __init__(self, icon, name, desc, hotkey, func, width=0):
        assert name
        assert desc
        assert func

        base.SelectableSprite.__init__(self)
        self.selectable_on_event = True
        self.is_statusctrl = True
        self.status = "normal"
        self.frame = 0

        self.icon = icon
        self.name = name
        self.desc = desc
        self.hotkey = hotkey
        self.func = func
        self.width = width

        self.shift_top = cw.s(0)
        self._shift_start_top = None

        self.update_scale()

    def update_scale(self):
        assert self.name
        if self.hotkey:
            title = u"%s(%s)" % (self.name, self.hotkey)
        else:
            title = self.name

        font = cw.cwpy.rsrc.fonts["sbardesc"]
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        h = font.get_height()

        # 必要サイズを計算
        lines = self.desc.splitlines()
        spx = cw.s(8)
        spy = cw.s(4)
        tw, th = max(cw.s(1), self.width), spy*2
        # 表題
        th += cw.s(3)  # 表題と本文の間
        fw, fh = tfont.size(title)
        tw = max(tw, fw + spx*2)
        th += h
        # 本文
        for line in lines:
            fw, fh = font.size(line)
            tw = max(tw, fw + spx*2)
            th += h

        # 画像を作成
        self.image = pygame.Surface((tw, th)).convert_alpha()
        color = (0, 0, 0, 192)
        linecolor = (255, 255, 255)
        tcolor = (255, 255, 255)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        x, y = spx, spy
        # 表題
        subimg = tfont.render(title, True, tcolor)
        self.image.blit(subimg, (x, y))
        y += tfont.get_height() + cw.s(1)
        pygame.draw.line(self.image, linecolor, (x, y), (x+tw-spx*2, y), cw.s(1))
        y += cw.s(2)
        # 本文
        for line in lines:
            subimg = font.render(line, True, tcolor)
            self.image.blit(subimg, (x, y))
            y += h

        self._unselectedimage = self.image
        self._selectedimage = self.image.copy()
        self._selectedimage.fill((128, 128, 128), special_flags=pygame.locals.BLEND_RGB_ADD)

    def get_selectedimage(self):
        return self._selectedimage

    def get_unselectedimage(self):
        return self._unselectedimage

    @staticmethod
    def calc_width(icon, name, desc, hotkey):
        """表示に必要な幅を計算する。"""
        font = cw.cwpy.rsrc.fonts["sbardesc"]
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        lines = desc.splitlines()
        spx = cw.s(8)
        tw = cw.s(1)
        # 本文
        for line in lines:
            fw, _fh = font.size(line)
            tw = max(tw, fw + spx*2)
        return tw

    def update(self, scr):
        if self.status <> "shiftup":
            self._shift_start_top = None
        base.SelectableSprite.update(self, scr)

    def update_selection(self):
        base.SelectableSprite.update_selection(self)
        if cw.cwpy.selection is self:
            self.image = self.get_selectedimage()
        else:
            self.image = self.get_unselectedimage()

    def update_shiftup(self):
        FRAME = 5

        if self._shift_start_top is None:
            self._shift_start_top = self.rect.top

        if FRAME <= self.frame or not cw.cwpy.setting.shiftup_touchbutton:
            self.status = self.old_status
            self.frame = 0
            self.rect.top = self.shift_top
            self._shift_start_top = None
            return

        d = self.shift_top - self._shift_start_top
        p = d * self.frame // FRAME

        self.rect.top = self._shift_start_top + p

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.stop_animation(self)
        cw.cwpy.statusbar.hide_touchbuttons()
        self.func()

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.play_sound(u"click")
        cw.cwpy.stop_animation(self)
        cw.cwpy.statusbar.hide_touchbuttons()


def main():
    pass


if __name__ == "__main__":
    main()
