#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import pygame

import cw
import base


class StatusBar(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self._init_image()
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self)
        self.showbuttons = False

    def _init_image(self):
        wxbmp = cw.cwpy.rsrc.get_wxbtnbmp(2)
        subimg = cw.image.conv2surface(wxbmp)
        image = pygame.Surface(cw.s((632, 33)))
        image.fill((255, 255, 255))
        image.blit(subimg, cw.s((0, 0)))
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 420))

    def update_scale(self):
        self._init_image()
        self.change(self.showbuttons)

    def change(self, showbuttons=True, encounter=False):
        self.clear()
        if showbuttons and (pygame.event.peek(pygame.locals.USEREVENT)):
            showbuttons = False

        self.showbuttons = showbuttons

        left = cw.s(602)
        rmargin = cw.s(0)
        SettingsButton(self, (left, cw.s(3)))

        left -= cw.s(28)
        rmargin += cw.s(27)
        hasbacklog = cw.cwpy.is_playingscenario()
        BacklogButton(self, (left, cw.s(3)), hasbacklog)

        if cw.cwpy.is_debugmode():
            left -= cw.s(28)
            rmargin += cw.s(27)
            DebuggerButton(self, (left, cw.s(3)))

        if encounter:
            EncounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif (cw.cwpy.is_curtained() and cw.cwpy.areaid <> cw.AREA_CAMP) or cw.cwpy.selectedheader:
            if cw.cwpy.status == "Yado":
                YadoMoneyPanel(self, cw.s((10, 6)))
                if showbuttons:
                    CancelButton(self, cw.s((133, 6)))
                PartyMoneyPanel(self, (cw.s(474) - rmargin, cw.s(6)))
            else:
                if showbuttons:
                    CancelButton(self, cw.s((10, 6)))
                if cw.cwpy.status == "Scenario":
                    PartyMoneyPanel(self, (cw.s(474) - rmargin, cw.s(6)))
                elif cw.cwpy.is_battlestatus():
                    RoundCounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif cw.cwpy.status == "Yado":
            YadoMoneyPanel(self, cw.s((10, 6)))
            PartyMoneyPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif cw.cwpy.status == "Scenario":
            if showbuttons:
                CampButton(self, cw.s((10, 6)))
                TableButton(self, cw.s((133, 6)))
            PartyMoneyPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif cw.cwpy.is_battlestatus():
            if showbuttons:
                ActionButton(self, cw.s((10, 6)))
                RunAwayButton(self, cw.s((133, 6)))
            RoundCounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))

        # デバッガのツールが使用可能かどうかを更新
        cw.cwpy.event.refresh_tools()

    def clear(self):
        cw.cwpy.sbargrp.remove_sprites_of_layer("panel")
        cw.cwpy.sbargrp.remove_sprites_of_layer("button")

class StatusBarPanel(base.CWPySprite):
    def __init__(self, parent, color, pos, size=None, icon=None):
        if size is None:
            size = cw.s((120, 22))
        base.CWPySprite.__init__(self)
        self.font = cw.cwpy.rsrc.fonts["sbarpanel"]
        self.icon = icon
        # panelimg
        self.panelimg = pygame.Surface(size).convert()
        self.panelimg.fill((0, 0, 0))
        rect = self.panelimg.get_rect()
        rect.topleft = cw.s((1, 1))
        rect.size = (size[0] - cw.s(2), size[1] - cw.s(2))
        self.panelimg.fill(color, rect)

        if self.icon:
            self.panelimg.blit(self.icon, cw.s((3, 3)))

        # image
        self.image = self.panelimg.copy()
        self.noimg = pygame.Surface(cw.s((0, 0))).convert()
        # rect
        self.rect = self.image.get_rect()
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer="panel")

    def set_backcolor(self, color):
        rect = self.panelimg.get_rect()
        size = rect.size
        rect.topleft = cw.s((1, 1))
        rect.size = (size[0] - cw.s(2), size[1] - cw.s(2))
        if self.icon:
            self.panelimg.blit(self.icon, cw.s((3, 3)))
        self.panelimg.fill(color, rect)

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
        s = cw.cwpy.msgs["currency"] % (self.text)

        if len(s) > 9:
            s = s[-9::]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = self.rect.w - (rect.w + cw.s(5))
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
                if cw.cwpy.ydata.party.money == 0:
                    self.set_backcolor((128, 0, 0))
                else:
                    self.set_backcolor((0, 0, 128))
                self.update_image()

        else:
            self.image = self.noimg
            self.text = None

class EncounterPanel(StatusBarPanel):
    def __init__(self, parent, pos):
        StatusBarPanel.__init__(self, parent, (0, 0, 128), pos)
        self.text = None
        self.update(None)

    def update(self, scr):
        if not self.text == cw.cwpy.msgs["encounter"]:
            self.text = cw.cwpy.msgs["encounter"]
            self.update_image()

    def update_image(self):
        s = cw.cwpy.msgs["encounter"]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = (self.rect.w - rect.w) / 2
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

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
        s = cw.cwpy.msgs["round"] % (self.text)

        if len(s) > 9:
            s = s[:9]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = (self.rect.w - rect.w) / 2
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

class StatusBarButton(base.SelectableSprite):
    def __init__(self, parent, name, pos, sizetype=0,
                 toggle=False, icon=None, enabled=True):
        base.SelectableSprite.__init__(self)
        # 各種データ
        self.name = name
        self.status = "normal"
        self.frame = 0
        self.is_pushed = False
        # ボタン画像
        wxbmp = cw.cwpy.rsrc.get_wxbtnbmp(sizetype)
        self.btnimg = cw.image.conv2surface(wxbmp)
        if enabled:
            wxbmp = cw.cwpy.rsrc.get_wxbtnbmp(sizetype, wx.CONTROL_PRESSED)
            self.btnimg2 = cw.image.conv2surface(wxbmp)
            wxbmp = cw.cwpy.rsrc.get_wxbtnbmp(sizetype, wx.CONTROL_CURRENT)
            self.btnimg3 = cw.image.conv2surface(wxbmp)
        else:
            self.btnimg2 = self.btnimg
            self.btnimg3 = self.btnimg
        # rect
        self.rect = self.btnimg.get_rect()
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]
        # image
        self.image = self.btnimg
        self.noimg = pygame.Surface(cw.s((0, 0))).convert()

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
        rect.top += cw.s(1)
        rect.left += cw.s(1)
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
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["camp"], pos, toggle=True)
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
            cw.cwpy.sounds["click"].play()
            cw.cwpy.change_specialarea(-4)

class TableButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["table"], pos, toggle=True)
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
            cw.cwpy.sounds["click"].play()
            cw.cwpy.clear_specialarea()

class ActionButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["start_action"], pos)

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
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["runaway"], pos)

    def update(self, scr):
        if cw.cwpy.battle and cw.cwpy.battle.is_running() or cw.cwpy.areaid <= 0:
            self.image = self.noimg
        else:
            StatusBarButton.update(self, scr)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)

        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.call_modaldlg("RUNAWAY")

class CancelButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["entry_cancel"], pos, toggle=False)
        self.is_pushed = False

    def update(self, scr):
        self.update_selection()
        self.update_image()

    def lclick_event(self):
        cw.cwpy.cancel_cardcontrol()

class SettingsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["SETTINGS"])
        name = u"設定"
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f2key_event()

class DebuggerButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["STATUS12"])
        name = u"デバッガ"
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f3key_event()

class BacklogButton(StatusBarButton):
    def __init__(self, parent, pos, enabled):
        self.enabled = enabled
        image = cw.s(cw.image.conv2surface(cw.cwpy.rsrc.debugs["BACKLOG"]))
        if not self.enabled:
            image = cw.imageretouch.to_binaryformat(image, 0)
        name = u"バックログ"
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image, enabled=enabled)
        self._selectable_on_event = enabled

    def lclick_event(self):
        if not self.enabled:
            return
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f5key_event()

def main():
    pass

if __name__ == "__main__":
    main()
