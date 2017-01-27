#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw

import wx
import pygame
from pygame.locals import K_RETURN, K_ESCAPE, K_BACKSPACE, K_BACKSLASH, K_LEFT, K_RIGHT, K_UP, K_DOWN,\
                          K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8, K_F9, K_F10, K_F11, K_F12,\
                          K_LSHIFT, K_LCTRL, K_PRINT, K_SPACE, KEYUP, KEYDOWN, MOUSEBUTTONUP,\
                          K_PAGEUP, K_PAGEDOWN, K_HOME, K_END


class KeyEventRelay(object):
    def __init__(self):
        # WXKeyとpygameKeyの対応表
        self.keymap = {
            wx.WXK_NUMPAD_ENTER : K_RETURN,
            wx.WXK_RETURN : K_RETURN,
            wx.WXK_ESCAPE : K_ESCAPE,
            wx.WXK_BACK : K_BACKSPACE,
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
            wx.WXK_SHIFT : K_LSHIFT,
            wx.WXK_CONTROL : K_LCTRL,
            wx.WXK_PAGEUP : K_PAGEUP,
            wx.WXK_PAGEDOWN : K_PAGEDOWN,
            wx.WXK_HOME : K_HOME,
            wx.WXK_END : K_END,
            ord('\\') : K_BACKSLASH,
            ord('D') : ord('D'), # デバッグモード切り替え
            ord('P') : ord('P'), # スクリーンショット
            ord('C') : ord('C')} # メッセージのコピー
        # キー入力(pygame用)
        self.keyin = [0 for _cnt in xrange(322)]
        # マウス入力。EventHandlerから受信
        self.mousein = [0, 0, 0]
        # マウスが押下状態か
        self.mouse_buttondown = [False, False, False]
        # キー押しっぱなし閾値
        self.threshold = 1
        # 連続押下は最初の1回のみKeyUpしたかのように動作するが、
        # ダイアログを閉じた直後にその処理が誤爆する可能性があるので
        # このフラグが立っている時に限り当該処理を行わない
        self.nokeyupevent = False

    def clear(self):
        self.keyin = [0 for _cnt in xrange(322)]
        self.mousein = [0, 0, 0]
        self.nokeyupevent = False

    def peek_mousestate(self):
        """MOUSEUPイベントに対応するMOUSEDOWNイベントが
        無ければキューから取り除く。
        """
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.locals.MOUSEBUTTONUP and hasattr(e, "button") and e.button <= len(self.mouse_buttondown):
                if self.mouse_buttondown[e.button-1]:
                    cw.thread.post_pygameevent(e)
            elif e.type == pygame.locals.MOUSEBUTTONDOWN and hasattr(e, "button") and e.button <= len(self.mouse_buttondown):
                self.mouse_buttondown[e.button - 1] = True
                cw.thread.post_pygameevent(e)
            else:
                cw.thread.post_pygameevent(e)

    def keydown(self, keycode):
        key = self.keymap.get(keycode, None)

        if key:
            if self.keyin[key] == 0:
                event = pygame.event.Event(KEYDOWN, key=key)
                cw.thread.post_pygameevent(event)

            if self.keyin[key] <= self.threshold + 1:
                self.keyin[key] += 1

    def keyup(self, keycode):
        key = self.keymap.get(keycode, None)

        if key:
            event = pygame.event.Event(KEYUP, key=key)
            cw.thread.post_pygameevent(event)
            self.keyin[key] = 0
            self.nokeyupevent = False

    def get_pressed(self):
        return tuple(self.keyin)

    def is_keyin(self, keycode):
        if self.threshold + 1 == self.keyin[keycode]:
            # 連続押下は最初の1回のみKeyUpしたかのように動作する
            if not cw.cwpy.setting.autoenter_on_sprite and not self.nokeyupevent:
                event = pygame.event.Event(KEYUP, key=keycode)
                cw.thread.post_pygameevent(event)
            self.keyin[keycode] += 1
        if self.threshold < self.keyin[keycode]:
            self.nokeyupevent = False
            return True
        else:
            return False

    def is_mousein(self, button=None):
        if button is None:
            button = 1

        if cw.cwpy.setting.can_repeatlclick:
            button -= 1
            pressed = cw.cwpy.mousein[:]
            if 0 <= button and button < len(self.mousein) and 0 <> self.mousein[button]:
                if 0 <= button and button < len(pressed) and pressed[button]:
                    # マウスボタン押下時間閾値
                    if -1 <> self.mousein[button]:
                        mousethreshold = 1.0 / cw.cwpy.setting.fps * 1000 * 40
                        if self.mousein[button] + mousethreshold <= pygame.time.get_ticks():
                            # 最初の1回のみMouseUpしたかのように動作する
                            if not cw.cwpy.setting.autoenter_on_sprite:
                                event = pygame.event.Event(MOUSEBUTTONUP, button=button+1, pos=cw.cwpy.mousepos, ignoreup=True)
                                cw.thread.post_pygameevent(event)
                            self.mousein[button] = -1
                    return self.mousein[button] == -1
                else:
                    # 押されていない
                    self.mousein[button] = 0
        return False

def main():
    pass

if __name__ == "__main__":
    main()
