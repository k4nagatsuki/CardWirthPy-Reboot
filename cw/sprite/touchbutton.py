#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import pygame.locals

import cw
from . import base


class TouchButton(base.SelectableSprite):
    """
    タッチ操作を想定した大きめのボタン。
    アイコン、ボタン名、簡単な解説を表示する。
    """

    def __init__(self, icon, name, desc, hotkey, func, is_enabled, width=0):
        assert func
        assert is_enabled

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
        self.is_enabled = is_enabled
        self.width = width

        self.shift_top = cw.s(0)
        self._shift_start_top = None

        self.update_scale()

    def update_scale(self):
        assert self.name
        if self.hotkey:
            title = "%s(%s)" % (self.name, self.hotkey)
        else:
            title = self.name

        font = cw.cwpy.rsrc.fonts["sbardesc"]
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        h = font.get_height()

        # 必要サイズを計算
        lines = self.desc.splitlines()
        spx = cw.s(8)
        spy = cw.s(2)
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
            th += fh

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
        self._disabledimage = self.image.copy()
        self._disabledimage.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
        if not self.is_enabled():
            self.image = self._disabledimage

    def get_selectedimage(self):
        return self._selectedimage

    def get_unselectedimage(self):
        return self._unselectedimage

    def update_image(self):
        if self.is_enabled():
            if self.is_selection():
                self.image = self._selectedimage
            else:
                self.image = self._unselectedimage
        else:
            self.image = self._disabledimage

    @staticmethod
    def calc_width(icon, name, desc, hotkey):
        """表示に必要な幅を計算する。"""
        font = cw.cwpy.rsrc.fonts["sbardesc"]
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        lines = desc.splitlines()
        spx = cw.s(8)
        # 表題
        if hotkey:
            title = "%s(%s)" % (name, hotkey)
        else:
            title = name
        fw, fh = tfont.size(title)
        tw = fw + spx*2
        # 本文
        for line in lines:
            fw, _fh = font.size(line)
            tw = max(tw, fw + spx*2)
        return tw+cw.s(2)

    def update(self, scr):
        if self.status != "shiftup":
            self._shift_start_top = None
        base.SelectableSprite.update(self, scr)

    def update_selection(self):
        base.SelectableSprite.update_selection(self)
        image = self.image
        if self.is_enabled():
            if cw.cwpy.selection is self:
                self.image = self.get_selectedimage()
            else:
                self.image = self.get_unselectedimage()
        else:
            self.image = self._disabledimage
        if image is not self.image:
            cw.cwpy.add_lazydraw(clip=self.rect)

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
        if self.is_enabled():
            cw.cwpy.statusbar.hide_touchbuttons()
            self.func()

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.statusbar.hide_touchbuttons()


class _PointableTile(TouchButton):
    """
    通常の選択は発生せず、マウスポインタが合った時に
    self.is_pointedがTrueになるタイル。
    """
    def __init__(self, icon, name, desc, hotkey, func, is_enabled, width=0):
        TouchButton.__init__(self, icon, name, desc, hotkey, func, is_enabled, width)

    def update_selection(self):
        if self.status != "normal":
            return

        if not cw.cwpy.is_lockmenucards(self):
            if self.is_pointed != self.is_selection():
                self.is_pointed = not self.is_pointed
                if self.is_pointed:
                    self.image = self.get_selectedimage()
                    cw.cwpy.pointed_tile = self
                    if cw.cwpy.index == -1:
                        cw.cwpy.clear_selection()
                else:
                    self.image = self.get_unselectedimage()
                    if cw.cwpy.pointed_tile is self:
                        cw.cwpy.pointed_tile = None
                if not self.is_enabled():
                    self.image = self._disabledimage
                cw.cwpy.add_lazydraw(clip=self.rect)

    def is_selection(self):
        # 通常の衝突判定
        if 0 <= cw.cwpy.mousepos[0] and 0 <= cw.cwpy.mousepos[1] and\
                self.rect.collidepoint(cw.cwpy.mousepos):
            return True
        return False


def _calc_singlelinetileheight():
    """
    タイルの縦幅を普通のタイルに合わせて計算する。
    """
    font = cw.cwpy.rsrc.fonts["sbardesc"]
    tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
    spy = cw.s(4)
    th = spy*2
    # 表題
    th += cw.s(3)
    fh = tfont.size("#")[1]
    h = font.get_height()
    th += h
    # 本文
    th += h
    return th


class SwitchSpriteTile(_PointableTile):
    """
    画面上のスプライトを順番に選択するタイル。
    """
    def __init__(self, icon, move_count, width=0):
        _PointableTile.__init__(self, icon, "", "", "", lambda: None, can_selectsprite, width=width)
        self.move_count = move_count

    def update_scale(self):
        th = _calc_singlelinetileheight()

        # 画像を作成
        self.image = pygame.Surface((self.width, th)).convert_alpha()
        color = (0, 0, 0, 192)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        iw, ih = self.icon.get_size()
        x = (self.width-iw)//2
        y = (th-ih)//2
        self.image.blit(self.icon, (x, y))

        self._unselectedimage = self.image
        self._selectedimage = self.image.copy()
        self._selectedimage.fill((128, 128, 128), special_flags=pygame.locals.BLEND_RGB_ADD)
        self._disabledimage = self.image.copy()
        self._disabledimage.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
        if not self.is_enabled():
            self.image = self._disabledimage

    def lclick_event(self):
        """左クリックイベント。"""
        if self.is_enabled():
            if cw.cwpy.interrupt_eventhandler:
                eventhandler = cw.cwpy.interrupt_eventhandler
            else:
                eventhandler = cw.cwpy.eventhandler
            eventhandler.dirkey_event(x=self.move_count, sidechange=True, hidetouchmenu=False)
            self.is_pointed = False
            self.update_selection()
            cw.cwpy.statusbar.update_tiles()


class SimplePointableTile(_PointableTile):
    """
    選択されたスプライトのクリックイベントを発生させるタイル。
    """
    def __init__(self, icon, name, func, is_enabled, width=0):
        _PointableTile.__init__(self, icon, name, "", "", func, is_enabled, width=width)

    def update_scale(self):
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        th = _calc_singlelinetileheight()

        # 画像を作成
        self.image = pygame.Surface((self.width, th)).convert_alpha()
        color = (0, 0, 0, 192)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        iw, ih = tfont.size(self.name)
        if self.icon:
            iw += cw.s(2) + self.icon.get_width()
        x = (self.width-iw)//2
        y = (th-ih)//2
        tcolor = (255, 255, 255)
        if self.icon:
            self.image.blit(self.icon, (x, (th-self.icon.get_height())//2))
            x += cw.s(2) + self.icon.get_width()
        subimg = tfont.render(self.name, True, tcolor)
        self.image.blit(subimg, (x, y))

        self._unselectedimage = self.image
        self._selectedimage = self.image.copy()
        self._selectedimage.fill((128, 128, 128), special_flags=pygame.locals.BLEND_RGB_ADD)
        self._disabledimage = self.image.copy()
        self._disabledimage.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
        if not self.is_enabled():
            self.image = self._disabledimage


def can_selectsprite():
    """
    画面上のスプライトがマウスやキーボードで選択可能な状態か。
    """
    if cw.cwpy.is_showingbacklog():
        return False
    elif cw.cwpy.is_showingmessage():
        return True
    else:
        return not cw.cwpy.is_runningevent()


class VolumeTile(TouchButton):
    """
    タッチ操作で音量調節を行うタイル。
    """

    def __init__(self, width=0):
        icon = cw.cwpy.rsrc.pygamedialogs["VOLUME"]
        TouchButton.__init__(self, icon, "", "", "", lambda: None, lambda: True, width=width)

    def update_scale(self):
        font = cw.cwpy.rsrc.fonts["sbarprogress"]
        spx = cw.s(10)
        spx2 = cw.s(5)
        spy = cw.s(5)
        fspy = cw.s(1)
        h = max(cw.s(16), font.get_height()+fspy*2, self.icon.get_height()) + spy*2

        # 画像を作成
        self.image = pygame.Surface((self.width, h+cw.s(2))).convert_alpha()
        color = (0, 0, 0, 192)
        self.image.fill(color)
        self.rect = self.image.get_rect()

        # アイコン
        self.image.blit(self.icon, (spx, (h-self.icon.get_height())//2))

        # バーの配置
        padx = spx+self.icon.get_width()+spx2
        pady = spy
        padw = self.rect.width - padx - spx
        padh = h - spy*2
        self.padrect = pygame.Rect(padx, pady, padw, padh)

        self.update_image()

    def update_image(self):
        font = cw.cwpy.rsrc.fonts["sbarprogress"]
        volrect = self.padrect.copy()  # 現在の音量
        volrect.width = int(volrect.width * cw.cwpy.setting.vol_master)

        self._selectedimage = self.image.copy()
        self._unselectedimage = self.image
        self._disabledimage = self.image

        for padcolor, volcolor, image in (((0, 0, 0, 232), (0, 128, 128, 232), self.image),
                                          ((16, 16, 16, 232), (64, 192, 192, 232), self._selectedimage)):
            # バーを描画
            image.fill(padcolor, self.padrect)
            image.fill(volcolor, volrect)

            # 音量文字列
            s = "%s%%" % int(cw.cwpy.setting.vol_master*100)
            tw, th = font.size(s)
            tx = self.padrect.x + (self.padrect.width-tw)//2
            ty = self.padrect.y + (self.padrect.height-th)//2
            subimg = font.render(s, True, (0, 0, 0))
            subimg.fill((0, 0, 0, 96), special_flags=pygame.locals.BLEND_RGBA_SUB)
            for tx2 in (-1, 0, 1):
                for ty2 in (-1, 0, 1):
                    if tx2 != 0 or ty2 != 0:
                        image.blit(subimg, (tx+tx2, ty+ty2))
            subimg = font.render(s, True, (255, 255, 255))
            image.blit(subimg, (tx, ty))

        if self.is_selection():
            self.image = self._selectedimage
        else:
            self.image = self._unselectedimage

    def update_selection(self):
        TouchButton.update_selection(self)
        if cw.cwpy.mousemotion and cw.cwpy.mousein[0] and cw.cwpy.selection is self:
            self._moved()

    def ldown_event(self):
        self._moved()

    def _moved(self):
        x, y = cw.cwpy.mousepos
        x -= self.rect.x
        x -= self.padrect.x
        y -= self.rect.y
        y -= self.padrect.y

        volume = 1.0 - float(self.padrect.width-x)/self.padrect.width
        volume = cw.util.numwrap(volume, 0.0, 1.0)
        volume = round(volume, 2)
        if int(cw.cwpy.setting.vol_master*100) == int(volume*100):
            return
        cw.cwpy.setting.vol_master = volume

        volume = int(cw.cwpy.setting.vol_master*100)
        cw.cwpy.set_mastervolume(volume)

        self.update_image()
        cw.cwpy.add_lazydraw(clip=self.rect)

    def lclick_event(self):
        pass  # 何もしない


def main():
    pass


if __name__ == "__main__":
    main()
