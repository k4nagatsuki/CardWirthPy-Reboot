#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import pygame

import cw
import base


class StatusBar(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        wxbmp = cw.cwpy.rsrc.create_wxbtnbmp(632, 33)
        subimg = cw.image.conv2surface(wxbmp)
        image = pygame.Surface((632, 33))
        image.fill((255, 255, 255))
        image.blit(subimg, (0, 0))
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 420)
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self)

    def change(self, showbuttons=True):
        self.clear()

        if cw.cwpy.is_debugmode():
            DebuggerButton(self, (574, 3))
            rmargin = 27
        else:
            rmargin = 0

        SettingsButton(self, (602, 3))

        if cw.cwpy.status == "Yado":
            YadoMoneyPanel(self, (10, 6))
            PartyMoneyPanel(self, (474 - rmargin, 6))
        elif cw.cwpy.status == "Scenario":
            if showbuttons:
                CampButton(self, (10, 6))
                TableButton(self, (133, 6))
            PartyMoneyPanel(self, (474 - rmargin, 6))
        elif cw.cwpy.is_battlestatus():
            if showbuttons:
                ActionButton(self, (10, 6))
                RunAwayButton(self, (133, 6))
            RoundCounterPanel(self, (474 - rmargin, 6))

        # デバッガのツールが使用可能かどうかを更新
        cw.cwpy.event.refresh_tools()

    def clear(self):
        cw.cwpy.sbargrp.remove_sprites_of_layer("panel")
        cw.cwpy.sbargrp.remove_sprites_of_layer("button")

class StatusBarPanel(base.CWPySprite):
    def __init__(self, parent, color, pos, size=(120, 22), icon=None):
        base.CWPySprite.__init__(self)
        self.font = cw.cwpy.rsrc.fonts["sbarpanel"]
        # panelimg
        self.panelimg = pygame.Surface(size).convert()
        self.panelimg.fill((0, 0, 0))
        rect = self.panelimg.get_rect()
        rect.topleft = (1, 1)
        rect.size = (size[0] - 2, size[1] - 2)
        self.panelimg.fill(color, rect)

        if icon:
            self.panelimg.blit(icon, (3, 3))

        # image
        self.image = self.panelimg.copy()
        self.noimg = pygame.Surface((0, 0)).convert()
        # rect
        self.rect = self.image.get_rect()
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer="panel")

class YadoMoneyPanel(StatusBarPanel):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["MONEYY"])
        StatusBarPanel.__init__(self, parent, (0, 69, 0), pos, icon=image)
        self.text = None
        self.update(None)

    def update(self, scr):
        if not self.text == cw.cwpy.ydata.money:
            self.text = cw.cwpy.ydata.money
            self.update_image()

    def update_image(self):
        s = str(self.text) + "sp"

        if len(s) > 9:
            s = s[-9::]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = self.rect.w - (rect.w + 5)
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

class PartyMoneyPanel(YadoMoneyPanel):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["MONEYP"])
        StatusBarPanel.__init__(self, parent, (0, 0, 128), pos, icon=image)
        self.text = None
        self.update(None)

    def update(self, scr):
        if cw.cwpy.ydata.party:
            if not self.text == cw.cwpy.ydata.party.money:
                self.text = cw.cwpy.ydata.party.money
                self.update_image()

        else:
            self.image = self.noimg
            self.text = None

class RoundCounterPanel(YadoMoneyPanel):
    def __init__(self, parent, pos):
        StatusBarPanel.__init__(self, parent, (0, 0, 128), pos)
        self.text = None
        self.update(None)

    def update(self, scr):
        if cw.cwpy.battle:
            if not self.text == str(cw.cwpy.battle.round):
                self.text = str(cw.cwpy.battle.round)
                self.update_image()

        else:
            self.image = self.noimg
            self.text = None

    def update_image(self):
        s = "Round " + self.text

        if len(s) > 9:
            s = s[:9]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = (self.rect.w - rect.w) / 2
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

class StatusBarButton(base.SelectableSprite):
    def __init__(self, parent, name, pos, size=(120, 22),
                                                    toggle=False, icon=None):
        base.SelectableSprite.__init__(self)
        # 各種データ
        self.name = name
        self.status = "normal"
        self.frame = 0
        self.is_pushed = False
        # ボタン画像
        w, h = size
        wxbmp = cw.cwpy.rsrc.create_wxbtnbmp(w, h)
        self.btnimg = cw.image.conv2surface(wxbmp)
        wxbmp = cw.cwpy.rsrc.create_wxbtnbmp(w, h, wx.CONTROL_PRESSED)
        self.btnimg2 = cw.image.conv2surface(wxbmp)
        wxbmp = cw.cwpy.rsrc.create_wxbtnbmp(w, h, wx.CONTROL_CURRENT)
        self.btnimg3 = cw.image.conv2surface(wxbmp)
        # rect
        self.rect = self.btnimg.get_rect()
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]
        # image
        self.image = self.btnimg
        self.noimg = pygame.Surface((0, 0)).convert()

        # ボタンアイコン・ラベル
        if icon:
            image = icon
        else:
            font = cw.cwpy.rsrc.fonts["sbarbtn"]
            image = font.render(name, True, (0, 0, 0))

        rect = image.get_rect()
        rect.centerx = self.rect.centerx - self.rect.left
        rect.centery = self.rect.centery - self.rect.top
        self.btnimg.blit(image, rect.topleft)
        self.btnimg3.blit(image, rect.topleft)
        rect.top += 1
        rect.left += 1
        self.btnimg2.blit(image, rect.topleft)
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer="button")

    def get_unselectedimage(self):
        if self.is_pushed:
            return self.btnimg2
        else:
            return self.btnimg

    def get_selectedimage(self):
        if self.is_pushed:
            return self.btnimg2
        else:
            return self.btnimg3

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        self.update_selection()

        if cw.cwpy.selection == self and cw.cwpy.mousein[0]:
            self.is_pushed = True
        else:
            self.is_pushed = False

        self.update_image()

    def update_click(self):
        if self.frame == 0:
            self.is_pushed = True
            self.update_image()
        elif self.frame == 4:
            self.is_pushed = False
            self.update_image()
            self.status = "normal"
            self.frame = 0
            return

        self.frame += 1

    def update_image(self):
        if self.is_pushed:
            if not self.image == self.btnimg2:
                cw.cwpy.has_inputevent = True
                self.image = self.btnimg2

        else:
            if not self.image in (self.btnimg, self.btnimg3):
                cw.cwpy.has_inputevent = True
                self.image = self.btnimg

    def lclick_event(self):
        cw.animation.animate_sprite(self, "click")

    def rclick_event(self):
        pass

class CampButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, u"キャンプ", pos, toggle=True)
        self.is_pushed = False

    def update(self, scr):
        self.update_selection()

        if cw.cwpy.selection == self and cw.cwpy.mousein[0]:
            self.is_pushed = True
        elif cw.cwpy.areaid in (-4, -5):
            self.is_pushed = True
        else:
            self.is_pushed = False

        self.update_image()

    def lclick_event(self):
        if cw.cwpy.areaid > 0:
            cw.cwpy.sounds[u"click"].play()
            cw.cwpy.change_specialarea(-4)

class TableButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, u"テーブル", pos, toggle=True)
        self.is_pushed = True

    def update(self, scr):
        self.update_selection()

        if cw.cwpy.selection == self and cw.cwpy.mousein[0]:
            self.is_pushed = True
        elif cw.cwpy.areaid >= 0:
            self.is_pushed = True
        else:
            self.is_pushed = False

        self.update_image()

    def lclick_event(self):
        if cw.cwpy.areaid == -4:
            cw.cwpy.sounds[u"click"].play()
            cw.cwpy.clear_specialarea()

class ActionButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, u"行動開始", pos)

    def update(self, scr):
        if cw.cwpy.battle and cw.cwpy.battle.is_running() or cw.cwpy.areaid <= 0:
            self.image = self.noimg
        else:
            StatusBarButton.update(self, scr)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)

        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.battle.start()

class RunAwayButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, u"逃げる", pos)

    def update(self, scr):
        if cw.cwpy.battle and cw.cwpy.battle.is_running() or cw.cwpy.areaid <= 0:
            self.image = self.noimg
        else:
            StatusBarButton.update(self, scr)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)

        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.call_dlg("RUNAWAY")

class SettingsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["SETTINGS"])
        name = u"設定"
        StatusBarButton.__init__(self, parent, name, pos, (27, 27), icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f2key_event()

class DebuggerButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["STATUS12"])
        name = u"デバッガ"
        StatusBarButton.__init__(self, parent, name, pos, (27, 27), icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f3key_event()

def main():
    pass

if __name__ == "__main__":
    main()
