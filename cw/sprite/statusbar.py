#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import wx
import pygame

import cw
import base


class StatusBar(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self.image = pygame.Surface(cw.s((632, 33))).convert()
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 420))
        self._init_image()
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self)
        self.showbuttons = False

    def _init_image(self):
        self.image = pygame.Surface(cw.s((632, 33))).convert()
        subimg = cw.cwpy.rsrc.get_statusbtnbmp(2, 0)
        self.image.fill((240, 240, 240))
        self.image.blit(subimg, cw.s((0, 0)))
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

        if cw.cwpy.setting.backlogmax:
            left -= cw.s(28)
            rmargin += cw.s(27)
            hasbacklog = cw.cwpy.has_backlog()
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
                lmargin = 10
                CampButton(self, cw.s((lmargin, 6)))
                lmargin += 123
                TableButton(self, cw.s((lmargin, 6)))
                lmargin += 123
            PartyMoneyPanel(self, (cw.s(474) - rmargin, cw.s(6)))
            rmargin += cw.s(34)
            if showbuttons and cw.cwpy.is_playingscenario() and cw.cwpy.sdata.infocards:
                InfoCardsButton(self, (cw.s(474) - rmargin, cw.s(3)))
        elif cw.cwpy.is_battlestatus():
            if showbuttons:
                ActionButton(self, cw.s((10, 6)))
                RunAwayButton(self, cw.s((133, 6)))
            RoundCounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
            rmargin += cw.s(34)
            if showbuttons and cw.cwpy.is_debugmode() and\
                    cw.cwpy.battle.is_ready() and cw.cwpy.get_fcards():
                ShowFriendCardsButton(self, (cw.s(474) - rmargin, cw.s(3)))

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
        self.panelimg.fill(color, rect)
        if self.icon:
            self.panelimg.blit(self.icon, cw.s((3, 3)))

class YadoMoneyPanel(StatusBarPanel):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["MONEYY"]
        StatusBarPanel.__init__(self, parent, (0, 69, 0), pos, icon=image)
        self.text = None
        self.update(None)

    def update(self, scr):
        if not self.text == cw.cwpy.ydata.money:
            self.text = cw.cwpy.ydata.money
            self.update_image()

    def update_image(self):
        s = cw.cwpy.msgs["currency"] % (self.text)

        if len(s) > 10:
            s = s[-10::]

        image = self.font.render(s, True, (255, 255, 255))
        rect = image.get_rect()
        rect.left = self.rect.w - (rect.w + cw.s(5))
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

class PartyMoneyPanel(YadoMoneyPanel):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["MONEYP"]
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
                 toggle=False, icon=None, enabled=True, is_pushed=False,
                 notice=False, number=None):
        base.SelectableSprite.__init__(self)
        # 各種データ
        self.name = name
        self.sizetype = sizetype
        self.status = "normal"
        self.frame = 0
        self.is_pushed = is_pushed
        self.enabled = enabled
        self.notice = notice
        # ボタン画像
        self.btnimg = {}

        # ボタンアイコン・ラベル
        if icon:
            if not number is None:
                self.icon = cw.util.put_number(icon, number)
            else:
                self.icon = icon
        else:
            font = cw.cwpy.rsrc.fonts["sbarbtn"]
            self.icon = font.render(name, True, (0, 0, 0))

        if not self.enabled:
            self.icon = cw.imageretouch.to_disabledsurface(self.icon)

        # image
        self.image = self.get_unselectedimage()
        self.noimg = pygame.Surface(cw.s((0, 0))).convert()
        # rect
        self.rect = self.image.get_rect()
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]

        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer="button")

    def get_btnimg(self, flags):
        if flags in self.btnimg:
            return self.btnimg[flags]
        else:
            bmp = cw.cwpy.rsrc.get_statusbtnbmp(self.sizetype, flags)
            brect = bmp.get_rect()
            rect = self.icon.get_rect()
            rect.centerx = brect.centerx - brect.left
            rect.centery = brect.centery - brect.top
            if flags & cw.setting.SB_PRESSED:
                rect.top += 1
                rect.left += 1
            icon = self.icon
            if flags & cw.setting.SB_NOTICE:
                icon = icon.convert_alpha()
                icon.fill((0, 0, 0, 96), special_flags=pygame.locals.BLEND_RGBA_SUB)
            bmp.blit(icon, rect.topleft)
            self.btnimg[flags] = bmp
            return bmp

    def get_unselectedimage(self):
        flags = 0
        if self.enabled:
            if self.is_pushed:
                flags |= cw.setting.SB_PRESSED
            if self.notice:
                flags |= cw.setting.SB_NOTICE
        else:
            flags |= cw.setting.SB_DISABLE

        return self.get_btnimg(flags)

    def get_selectedimage(self):
        flags = cw.setting.SB_CURRENT
        if self.enabled:
            if self.is_pushed:
                flags |= cw.setting.SB_PRESSED
            if self.notice:
                flags |= cw.setting.SB_NOTICE
        else:
            flags |= cw.setting.SB_DISABLE

        return self.get_btnimg(flags)

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
        if not self.enabled:
            return

        flags = 0
        if self.is_pushed:
            flags |= cw.setting.SB_PRESSED
        if self.is_selection():
            flags |= cw.setting.SB_CURRENT
            cw.cwpy.has_inputevent = True
        if self.notice:
            flags |= cw.setting.SB_NOTICE

        self.image = self.get_btnimg(flags)

    def lclick_event(self):
        cw.animation.animate_sprite(self, "click")

    def rclick_event(self):
        pass

class CampButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["camp"], pos, toggle=True, is_pushed=False)

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
        elif cw.cwpy.areaid == -4:
            cw.cwpy.sounds["click"].play()
            cw.cwpy.clear_specialarea()

class TableButton(StatusBarButton):
    def __init__(self, parent, pos):
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["table"], pos, toggle=True, is_pushed=True)

    def update(self, scr):
        self.update_selection()

        if cw.cwpy.selection == self and cw.cwpy.mousein[0]:
            self.is_pushed = True
        elif cw.cwpy.areaid in (-4, -5):
            self.is_pushed = False
        else:
            self.is_pushed = True

        self.update_image()

    def lclick_event(self):
        if cw.cwpy.areaid == -4:
            cw.cwpy.sounds["click"].play()
            cw.cwpy.clear_specialarea()
        elif cw.cwpy.areaid > 0:
            cw.cwpy.sounds["click"].play()
            cw.cwpy.change_specialarea(-4)

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
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["entry_cancel"], pos)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.cancel_cardcontrol()

class ShowFriendCardsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.s(cw.cwpy.rsrc.pygamedebugs["EVT_GET_CAST"])
        name = cw.cwpy.msgs["show_fcards"]
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image, toggle=True,
                                 is_pushed=cw.cwpy.setting.show_fcardsinbattle)

    def update(self, scr):
        self.update_selection()

        self.is_pushed = cw.cwpy.setting.show_fcardsinbattle

        self.update_image()

    def lclick_event(self):
        cw.cwpy.sounds["page"].play()
        if cw.cwpy.is_battlestatus():
            cw.cwpy.setting.show_fcardsinbattle = not cw.cwpy.setting.show_fcardsinbattle
            cw.cwpy.battle.update_showfcards()

class InfoCardsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.s(cw.cwpy.rsrc.pygamedebugs["INFOVIEW"])
        name = cw.cwpy.msgs["info_card"]
        notice = cw.cwpy.sdata.notice_infoview
        number = len(cw.cwpy.sdata.infocards)
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image,
                                 notice=notice, number=number)

    def lclick_event(self):
        cw.cwpy.sounds["click"].play()
        cw.cwpy.clear_selection()
        cw.content.PostEventContent.do_action("ShowDialog", "INFOVIEW")

class SettingsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["SETTINGS"]
        name = u"設定"
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f2key_event()

class DebuggerButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["STATUS12"]
        name = u"デバッガ"
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image)
        self._selectable_on_event = True

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f3key_event()

class BacklogButton(StatusBarButton):
    def __init__(self, parent, pos, enabled):
        image = cw.s(cw.cwpy.rsrc.pygamedebugs["BACKLOG"])
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
