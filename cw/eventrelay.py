#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw

import wx
import pygame
from pygame.locals import K_RETURN, K_ESCAPE, K_LEFT, K_RIGHT, K_UP, K_DOWN,\
                          K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8, K_F9, K_F10, K_F11, K_F12,\
                          K_LSHIFT, K_PRINT, K_SPACE, KEYUP, KEYDOWN


class KeyEventRelay(object):
    def __init__(self):
        # WXKeyとpygameKeyの対応表
        self.keymap = {
            wx.WXK_NUMPAD_ENTER : K_RETURN,
            wx.WXK_RETURN : K_RETURN,
            wx.WXK_ESCAPE : K_ESCAPE,
            wx.WXK_SPACE : K_SPACE,
            wx.WXK_F1 : K_F1,
            wx.WXK_F2 : K_F2,
            wx.WXK_F3 : K_F3,
            wx.WXK_F4 : K_F4,
            wx.WXK_F5 : K_F5,
            wx.WXK_F6 : K_F6,
            wx.WXK_F7 : K_F7,
            wx.WXK_F8 : K_F8,
            wx.WXK_F9 : K_F9,
            wx.WXK_F10 : K_F10,
            wx.WXK_F11 : K_F11,
            wx.WXK_F12 : K_F12,
            wx.WXK_UP : K_UP,
            wx.WXK_DOWN : K_DOWN,
            wx.WXK_LEFT : K_LEFT,
            wx.WXK_RIGHT : K_RIGHT,
            wx.WXK_SNAPSHOT : K_PRINT,
            wx.WXK_SHIFT : K_LSHIFT}
        # キー入力(pygame用)
        self.keyin = [0 for _cnt in xrange(322)]
        # マウス入力。EventHandlerから受信
        self.mousein = [0, 0, 0]
        # キー押しっぱなし閾値
        self.threshold = 1

    def clear(self):
        self.keyin = [0 for _cnt in xrange(322)]
        self.mousein = [0, 0, 0]

    def keydown(self, keycode):
        key = self.keymap.get(keycode, None)

        if key:
            if self.keyin[key] == 0:
                event = pygame.event.Event(KEYDOWN, key=key)
                pygame.event.post(event)

            if self.keyin[key] <= self.threshold:
                self.keyin[key] += 1

    def keyup(self, keycode):
        key = self.keymap.get(keycode, None)

        if key:
            event = pygame.event.Event(KEYUP, key=key)
            pygame.event.post(event)
            self.keyin[key] = 0

    def get_pressed(self):
        return tuple(self.keyin)

    def is_keyin(self, keycode):
        return self.threshold < self.keyin[keycode]

    def is_mousein(self, button):
        if cw.cwpy.setting.can_repeatlclick:
            button -= 1
            pressed = pygame.mouse.get_pressed()
            if 0 <= button and button < len(self.mousein) and 0 < self.mousein[button]:
                if 0 <= button and button < len(pressed) and pressed[button]:
                    # マウスボタン押下時間閾値
                    mousethreshold = 1.0 / cw.cwpy.setting.fps * 1000 * 30
                    return self.mousein[button] + mousethreshold <= pygame.time.get_ticks()
                else:
                    # 押されていない
                    self.mousein[button] = 0
        return False

def main():
    pass

if __name__ == "__main__":
    main()
