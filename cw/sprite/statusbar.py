#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import pygame.locals

import cw
import base


LAYER_BASE = 0
LAYER_STATUS_ITEM = 1
LAYER_STATUS_PROGRESS = 2
LAYER_MESSAGE = 3
LAYER_MESSAGE_LOG_CURTAIN = 4
LAYER_MESSAGE_LOG = 5
LAYER_VOLUME_BAR = 6
LAYER_DESC = 7

class StatusBar(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self.image = pygame.Surface(cw.s((632, 33))).convert()
        self.yadomoney = None
        self.partymoney = None
        self.autostart = None
        self.debugger = None
        self.backlog = None
        self.settings = None
        self.infocards = None
        self.friendcards = None
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 420))
        self.showbuttons = False
        self._statusbarmask = cw.cwpy.setting.statusbarmask
        self.maskmode = None
        self.loading = False
        self.volumebar = VolumeBar()
        cw.cwpy.sbargrp.add(self.volumebar, layer=LAYER_VOLUME_BAR)
        self._init_image()
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer=LAYER_BASE)

    def _init_image(self):
        self.image = pygame.Surface(cw.s((632, 33))).convert()
        subimg = cw.cwpy.rsrc.get_statusbtnbmp(2, 0)
        self.maskmode = not self.showbuttons and self._statusbarmask and cw.cwpy.is_statusbarmask()
        if self.maskmode:
            subimg.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
        self.image.fill((240, 240, 240))
        self.image.blit(subimg, cw.s((0, 0)))
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 420))

    def update_scale(self):
        self._init_image()
        self.clear_volumebar()
        self.change(self.showbuttons)

    def change(self, showbuttons=True, encounter=False):
        self.clear()
        in_camp = cw.cwpy.areaid in (cw.AREA_CAMP, cw.AREA_TRADE3)
        if showbuttons and (pygame.event.peek(pygame.locals.USEREVENT) or cw.cwpy.expanding) and not in_camp:
            showbuttons = False

        self.showbuttons = showbuttons
        maskmode = not self.showbuttons and self._statusbarmask and cw.cwpy.is_statusbarmask()

        if self.maskmode <> maskmode:
            self.maskmode = maskmode
            subimg = cw.cwpy.rsrc.get_statusbtnbmp(2, 0)
            if maskmode:
                subimg.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
            self.image.fill((240, 240, 240))
            self.image.blit(subimg, cw.s((0, 0)))

        if cw.cwpy.expanding:
            ExpandView(self, cw.s((10, 6)))

        showbuttons &= not cw.cwpy.is_showingbacklog() and not cw.cwpy.sdata.in_f9

        left = cw.s(602)
        rmargin = cw.s(0)
        self._create_settings((left, cw.s(3)))

        if cw.cwpy.setting.backlogmax:
            left -= cw.s(28)
            rmargin += cw.s(27)
            self._create_backlog((left, cw.s(3)))

        if cw.cwpy.is_debugmode():
            left -= cw.s(28)
            rmargin += cw.s(27)
            self._create_debugger((left, cw.s(3)))

        if encounter:
            EncounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif (cw.cwpy.is_curtained() and cw.cwpy.areaid <> cw.AREA_CAMP) or cw.cwpy.selectedheader:
            if cw.cwpy.status == "Yado":
                if not cw.cwpy.expanding:
                    self._create_yadomoney(cw.s((10, 6)))
                    CancelButton(self, cw.s((133, 6)))
                    if cw.cwpy.ydata.party:
                        self._create_partymoney((cw.s(474) - rmargin, cw.s(6)))
            else:
                if cw.cwpy.is_battlestatus() and cw.cwpy.setting.show_roundautostartbutton:
                    self._create_autostart(cw.s((5, 3)))
                    left = cw.s(36)
                else:
                    left = cw.s(10)
                if showbuttons:
                    CancelButton(self, (left, cw.s(6)))
                if cw.cwpy.status == "Scenario":
                    self._create_partymoney((cw.s(474) - rmargin, cw.s(6)))
                elif cw.cwpy.is_battlestatus():
                    RoundCounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
        elif cw.cwpy.status == "Yado":
            if not cw.cwpy.expanding:
                self._create_yadomoney(cw.s((10, 6)))
            if cw.cwpy.ydata.party:
                self._create_partymoney((cw.s(474) - rmargin, cw.s(6)))
        elif cw.cwpy.status == "Scenario":
            if showbuttons:
                lmargin = 10
                CampButton(self, cw.s((lmargin, 6)))
                lmargin += 123
                TableButton(self, cw.s((lmargin, 6)))
                lmargin += 123
            self._create_partymoney((cw.s(474) - rmargin, cw.s(6)))
            rmargin += cw.s(34)
            if showbuttons and cw.cwpy.is_playingscenario() and cw.cwpy.sdata.has_infocards():
                self._create_infocards((cw.s(474) - rmargin, cw.s(3)))
        elif cw.cwpy.is_battlestatus():
            if cw.cwpy.setting.show_roundautostartbutton:
                self._create_autostart(cw.s((5, 3)))
                left = cw.s(36)
            else:
                left = cw.s(10)
            if showbuttons:
                btn = ActionButton(self, (left, cw.s((6))))
                if self.autostart:
                    self.autostart.actionbtn = btn
                RunAwayButton(self, (cw.s(123) + left, cw.s((6))))
            RoundCounterPanel(self, (cw.s(474) - rmargin, cw.s(6)))
            rmargin += cw.s(34)
            if showbuttons and cw.cwpy.is_debugmode() and\
                    cw.cwpy.battle.is_ready() and cw.cwpy.get_fcards():
                self._create_friendcards((cw.s(474) - rmargin, cw.s(3)))

        if self.infocards and not cw.cwpy.is_playingscenario():
            self.infocards.notice = False

        if showbuttons:
            self.loading = False

        if not cw.cwpy.sdata or not cw.cwpy.sdata.in_f9:
            # デバッガのツールが使用可能かどうかを更新
            cw.cwpy.event.refresh_tools()

    def clear(self):
        cw.cwpy.sbargrp.remove_sprites_of_layer(LAYER_STATUS_ITEM)
        cw.cwpy.sbargrp.remove_sprites_of_layer(LAYER_STATUS_PROGRESS)
        cw.cwpy.sbargrp.remove_sprites_of_layer(LAYER_DESC)

    def _create_autostart(self, pos):
        if self.autostart:
            self.autostart.reset(pos)
        else:
            self.autostart = AutoStartButton(self, pos)

    def _create_debugger(self, pos):
        if self.debugger:
            self.debugger.reset(pos)
        else:
            self.debugger = DebuggerButton(self, pos)

    def _create_backlog(self, pos):
        if self.backlog:
            self.backlog.reset(pos)
        else:
            self.backlog = BacklogButton(self, pos)

    def _create_settings(self, pos):
        if self.settings:
            self.settings.reset(pos)
        else:
            self.settings = SettingsButton(self, pos)

    def _create_yadomoney(self, pos):
        if self.yadomoney:
            self.yadomoney.reset(self, pos, cw.s((120, 22)))
        else:
            self.yadomoney = YadoMoneyPanel(self, pos)

    def _create_partymoney(self, pos):
        if self.partymoney:
            self.partymoney.reset(self, pos, cw.s((120, 22)))
        else:
            self.partymoney = PartyMoneyPanel(self, pos)

    def _create_infocards(self, pos):
        if self.infocards:
            notice = self.infocards.notice
            self.infocards.reset(pos)
            if not self.loading and notice <> self.infocards.notice and self.infocards.notice:
                cw.animation.start_animation(self.infocards, "blink")
        else:
            self.infocards = InfoCardsButton(self, pos)
            if not self.loading and self.infocards.notice:
                cw.animation.start_animation(self.infocards, "blink")

    def _create_friendcards(self, pos):
        if self.friendcards:
            self.friendcards.reset(pos)
        else:
            self.friendcards = ShowFriendCardsButton(self, pos)

    def update_volumebar(self):
        """全体音量バーの表示を更新する。
        全体音量バーが表示中でない場合は、表示する。
        """
        self.volumebar.update_scale()

    def clear_volumebar(self):
        """全体音量バーの表示をクリアする。"""
        return self.volumebar.clear_image()

    def is_showingvolumebar(self):
        """全体音量バーが表示中か。"""
        return 0 < self.volumebar.rect.width

    def layered_draw_ex(self, layered_updates, surface, draw_desc):
        rects = []
        srect = surface.get_rect()
        clip = surface.get_clip()
        if clip:
            srect = clip

        sprites = layered_updates.sprites()
        h = cw.SIZE_GAME[1]-cw.SIZE_AREA[1]
        sbarclip = cw.s(pygame.Rect(0, cw.SIZE_AREA[1], cw.SIZE_GAME[0], h))
        for sprite in sprites:
            if srect.colliderect(sprite.rect):
                if isinstance(sprite, (VolumeBar, Desc)):
                    if not draw_desc:
                        continue
                    surface.set_clip(srect.clip(sprite.rect))
                else:
                    surface.set_clip(srect.clip(sprite.rect).clip(sbarclip))
                rect = surface.blit(sprite.image, sprite.rect)
                rects.append(rect)
        surface.set_clip(clip)
        return rects

class VolumeBar(base.CWPySprite):

    def __init__(self):
        base.CWPySprite.__init__(self)
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.volume = cw.cwpy.setting.vol_master
        self.upscr = cw.UP_SCR

    def update_scale(self):
        if self.volume == cw.cwpy.setting.vol_master and self.upscr == cw.UP_SCR and self.rect.width:
            return
        self.volume = cw.cwpy.setting.vol_master
        self.upscr = cw.UP_SCR

        padw = 8
        padw2 = 2
        padh = 5
        barh = 200

        font = cw.cwpy.rsrc.fonts["sbarprogress"]
        tsize = font.size(u"100%")
        tsize2 = font.size(u"音量")
        tw = max(tsize[0], tsize2[0])
        self.rect = pygame.Rect(cw.s(560), cw.s(60), tw+cw.s(padw2)*2, cw.s(barh)+cw.s(1)*2+cw.s(padh)*4+tsize[1]*2)
        self.image = pygame.Surface(self.rect.size).convert_alpha()
        self.image.fill((0, 0, 0, 128))
        self.image.fill((0, 0, 0, 192), pygame.Rect(cw.s(padw), cw.s(padh)*2+tsize[1], self.rect.width-cw.s(padw)*2, cw.s(barh)+cw.s(2)))
        n = cw.s(barh - int(cw.cwpy.setting.vol_master * barh))
        self.image.fill((0, 128, 128, 192), pygame.Rect(cw.s(padw)+cw.s(1), cw.s(padh)*2+tsize[1]+cw.s(1)+n, self.rect.width-cw.s(padw)*2-cw.s(2), cw.s(barh)-n))

        subimg = font.render("%s%%" % (int(cw.cwpy.setting.vol_master * 100)), True, (255, 255, 255))
        self.image.blit(subimg, ((self.rect.width-tsize[0])/2+tsize[0]-subimg.get_width(), cw.s(padh)*2+tsize[1]+cw.s(barh)+cw.s(padh)))
        subimg = font.render(u"音量", True, (255, 255, 255))
        self.image.blit(subimg, ((self.rect.width-tsize2[0])/2, cw.s(padh)))

        cw.cwpy.draw(clip=self.rect)

    def clear_image(self):
        if not self.rect.width:
            return False
        rect = self.rect
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        self.rect = pygame.Rect(0, 0, 0, 0)
        cw.cwpy.draw(clip=rect)
        return True

class ProgressView(base.CWPySprite):
    def __init__(self, parent, pos, size=None, text="", nmax=0, nmin=100, current=0):
        base.CWPySprite.__init__(self)
        if size is None:
            size = cw.s((300, 22))
        self.text = text
        self.max = nmax
        self.min = nmin
        self.current = current
        self._last_params = None
        self.rect = pygame.Rect(pos, size)
        self.rect.top = parent.rect.top + pos[1]
        self.rect.left = parent.rect.left + pos[0]
        self.update(None)

        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer=LAYER_STATUS_PROGRESS)

    def update(self, scr):
        params = (self.text, self.max, self.min, self.current)
        if self._last_params <> params:
            self.update_image()
            cw.cwpy.has_inputevent = True

    def update_image(self):
        self._last_params = (self.text, self.max, self.min, self.current)

        image = pygame.Surface(self.rect.size).convert_alpha()
        image.fill((0, 0, 0))
        w, h = self.rect.size
        rect = pygame.Rect(cw.s(1), cw.s(1), w-cw.s(2), h-cw.s(2))
        image.fill((255, 255, 255), rect)
        w = self.rect.width - cw.s(2)

        font = cw.cwpy.rsrc.fonts["sbarprogress"]
        subimg = font.render(self.text, cw.cwpy.setting.fontsmoothing_statusbar, (0, 0, 0))
        if w-cw.s(4) < subimg.get_width():
            subimg = cw.image.smoothscale(subimg.convert_alpha(), (w-cw.s(4), subimg.get_height()),
                                          smoothing=cw.cwpy.setting.fontsmoothing_statusbar)
        x = (image.get_width() - subimg.get_width()) / 2
        y = (image.get_height() - subimg.get_height()) / 2

        g = w / float(self.max - self.min)
        curw = int(self.current * g) + cw.s(1)
        rect = (cw.s(1), cw.s(1), curw, self.rect.height-cw.s(2))
        image.fill((0, 0, 128), rect)

        curw = curw - (x-cw.s(1))
        rect = (cw.s(0), cw.s(0), min(curw, subimg.get_width()), subimg.get_height())
        subimg.fill((255, 255, 255, 0), rect, special_flags=pygame.locals.BLEND_RGBA_ADD)

        image.blit(subimg, (x, y))
        _draw_edge(image)
        self.image = image

class ExpandView(ProgressView):
    def __init__(self, parent, pos):
        text = cw.cwpy.expanding
        nmax = cw.cwpy.expanding_max
        nmin = cw.cwpy.expanding_min
        current = cw.cwpy.expanding_cur
        ProgressView.__init__(self, parent, pos, text=text, nmax=nmax, nmin=nmin, current=current)

    def update(self, scr):
        self.text = cw.cwpy.expanding
        self.max = cw.cwpy.expanding_max
        self.min = cw.cwpy.expanding_min
        self.current = cw.cwpy.expanding_cur
        ProgressView.update(self, scr)

class StatusBarPanel(base.MouseHandlerSprite):
    def __init__(self, parent, color, pos, size=None, icon=None, desc=u""):
        self.parent = parent
        if size is None:
            size = cw.s((120, 22))
        base.MouseHandlerSprite.__init__(self)
        # panelimg
        self._color = color
        self._create_paneimg(pos, size, icon)
        self.desc = desc
        self._desc = None

    def _create_paneimg(self, pos, size, icon):
        self.icon = icon
        self.panelimg = pygame.Surface(size).convert_alpha()
        self.panelimg.fill((0, 0, 0))
        rect = self.panelimg.get_rect()
        rect.topleft = cw.s((1, 1))
        rect.size = (size[0] - cw.s(2), size[1] - cw.s(2))
        self.panelimg.fill(self._color, rect)
        _draw_edge(self.panelimg)

        if self.icon:
            self.panelimg.blit(self.icon, cw.s((3, 3)))
            self.handling_rect = pygame.Rect(cw.s(3), cw.s(3), self.icon.get_width(), self.icon.get_height())

        # image
        self.image = self.panelimg.copy()
        self.noimg = pygame.Surface(cw.s((0, 0))).convert()
        # rect
        self.rect = self.image.get_rect()
        self.rect.top = self.parent.rect.top + pos[1]
        self.rect.left = self.parent.rect.left + pos[0]
        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer=LAYER_STATUS_ITEM)

    def get_icon(self):
        return None

    def reset(self, parent, pos, size):
        self.parent = parent
        self._create_paneimg(pos, size, self.get_icon())
        if self._desc:
            cw.cwpy.sbargrp.remove(self._desc)
            cw.cwpy.draw(clip=self._desc.rect)
            self._desc = None
        self.update_image()

    def set_desc(self, desc):
        self.desc = desc
        if self._desc:
            cw.cwpy.sbargrp.remove(self._desc)
            rect = self._desc.rect
            self._desc = None
            self._desc = Desc(self, u"", self.desc, u"", arrowpos=cw.s(3)+self.icon.get_width()//2)
            cw.cwpy.sbargrp.add(self._desc, layer=LAYER_DESC)
            cw.cwpy.draw(clip=self._desc.rect)

    def update_image(self):
        if cw.cwpy.setting.show_btndesc and self.handling and self.desc and not cw.cwpy.is_showingdlg():
            if not self._desc:
                self._desc = Desc(self, u"", self.desc, u"", arrowpos=cw.s(3)+self.icon.get_width()//2)
                cw.cwpy.sbargrp.add(self._desc, layer=LAYER_DESC)
                cw.cwpy.draw(clip=self._desc.rect)
        else:
            if self._desc:
                cw.cwpy.sbargrp.remove(self._desc)
                cw.cwpy.draw(clip=self._desc.rect)
                self._desc = None
                cw.cwpy.has_inputevent = True

    def set_backcolor(self, color):
        self._color = color
        rect = self.panelimg.get_rect()
        size = rect.size
        rect.topleft = cw.s((1, 1))
        rect.size = (size[0] - cw.s(2), size[1] - cw.s(2))
        self.panelimg.fill(color, rect)
        if self.icon:
            self.panelimg.blit(self.icon, cw.s((3, 3)))
        _draw_edge(self.panelimg)

    def get_scaledimage(self, image):
        """imageの横幅が大きすぎる場合は
        パネル内に収まるようにリサイズして返す。
        """
        wmax = self.panelimg.get_width() - cw.s(5) - cw.s(5)
        if self.icon:
            wmax = wmax - self.icon.get_width() - cw.s(3)

        rect = image.get_rect()
        if wmax < rect.width:
            rect.width = wmax
            image = cw.image.smoothscale(image.convert_alpha(), rect.size,
                                         smoothing=cw.cwpy.setting.fontsmoothing_statusbar)
        return image

def _draw_edge(image):
    def put(x, y):
        rect = pygame.Rect((x, y), (1, 1))
        image.fill((0, 0, 0), rect)
        image.fill((0, 0, 0, 192), rect, special_flags=pygame.locals.BLEND_RGBA_SUB)
    def put_inside(x, y):
        rect = pygame.Rect((x, y), (1, 1))
        image.fill((192, 192, 192), rect, special_flags=pygame.locals.BLEND_RGB_MULT)
    w, h = image.get_size()

    put(0, 0)
    put(w-1, 0)
    put(0, h-1)
    put(w-1, h-1)

    put_inside(cw.s(1), cw.s(1))
    put_inside(w-1-cw.s(1), cw.s(1))
    put_inside(cw.s(1), h-1-cw.s(1))
    put_inside(w-1-cw.s(1), h-1-cw.s(1))

class YadoMoneyPanel(StatusBarPanel):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["MONEYY"]
        desc = cw.cwpy.msgs["desc_base_money"]
        StatusBarPanel.__init__(self, parent, (0, 69, 0), pos, icon=image, desc=desc)
        self.text = self.get_money()
        self.currency = "%s"
        self.up_scr = 0
        self.update(None)

    def reset(self, parent, pos, size):
        self.text = self.get_money()
        self.desc = cw.cwpy.msgs["desc_base_money"]
        self.update_color()
        StatusBarPanel.reset(self, parent, pos, size)

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["MONEYY"]

    def need_update(self, text, currency):
        return self.text <> text or self.currency <> currency or self.up_scr <> cw.UP_SCR

    def put_updatekey(self, text, currency):
        self.text = text
        self.currency = currency
        self.up_scr = cw.UP_SCR

    def update(self, scr):
        StatusBarPanel.update(self, scr)

        if self.status == "blink":
            return

        if self.need_update(self.get_money(), cw.cwpy.msgs["currency"]):
            self.put_updatekey(self.get_money(), cw.cwpy.msgs["currency"])
            self.update_image()

    def get_money(self):
        return cw.cwpy.ydata.money if cw.cwpy.ydata else 0

    def update_image(self):
        StatusBarPanel.update_image(self)

        s = self.currency % (self.text)
        font = cw.cwpy.rsrc.fonts["sbarpanel"]
        image = font.render(s, cw.cwpy.setting.fontsmoothing_statusbar, (255, 255, 255))
        image = self.get_scaledimage(image)

        rect = image.get_rect()
        rect.left = self.rect.w - (rect.w + cw.s(5))
        rect.top = (self.rect.h - rect.h) / 2

        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

    def update_color(self):
        pass

    def update_blink(self):
        if 30 <= self.frame or not cw.cwpy.setting.blink_partymoney:
            self.status = self.old_status
            self.frame = 0
            self.put_updatekey(self.get_money(), cw.cwpy.msgs["currency"])
            self.update_image()
            return

        if self.frame / 5 % 2 == 1:
            text = ""
            currency = "%s"
        else:
            text = self.get_money()
            currency = cw.cwpy.msgs["currency"]

        if self.need_update(text, currency):
            self.update_color()
            self.put_updatekey(text, currency)
            self.update_image()

class PartyMoneyPanel(YadoMoneyPanel):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["MONEYP"]
        desc = cw.cwpy.msgs["desc_party_money"]
        StatusBarPanel.__init__(self, parent, (0, 0, 128), pos, icon=image, desc=desc)
        self.text = self.get_money()
        self.currency = "%s"
        self.up_scr = 0
        self.update(None)

    def reset(self, parent, pos, size):
        self.text = self.get_money()
        self.desc = cw.cwpy.msgs["desc_party_money"]
        StatusBarPanel.reset(self, parent, pos, size)

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["MONEYP"]

    def get_money(self):
        return cw.cwpy.ydata.party.money if cw.cwpy.ydata and cw.cwpy.ydata.party else 0

    def update_color(self):
        if self.get_money() == 0:
            self.set_backcolor((128, 0, 0))
        else:
            self.set_backcolor((0, 0, 128))

    def update(self, scr):
        StatusBarPanel.update(self, scr)

        if self.status == "blink":
            self.update_color()
            return
        if cw.cwpy.ydata.party:
            if self.need_update(self.get_money(), cw.cwpy.msgs["currency"]):
                self.put_updatekey(self.get_money(), cw.cwpy.msgs["currency"])
                self.update_color()
                self.update_image()

        else:
            self.image = self.noimg
            self.text = ""

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

        font = cw.cwpy.rsrc.fonts["sbarpanel"]
        image = font.render(s, cw.cwpy.setting.fontsmoothing_statusbar, (255, 255, 255))
        image = self.get_scaledimage(image)
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
        font = cw.cwpy.rsrc.fonts["sbarpanel"]
        image = font.render(s, cw.cwpy.setting.fontsmoothing_statusbar, (255, 255, 255))
        image = self.get_scaledimage(image)
        rect = image.get_rect()
        rect.left = (self.rect.w - rect.w) / 2
        rect.top = (self.rect.h - rect.h) / 2
        self.image = self.panelimg.copy()
        self.image.blit(image, rect.topleft)

class StatusBarButton(base.SelectableSprite):
    def __init__(self, parent, name, pos, sizetype=0,
                 icon=None, enabled=True, is_pushed=False,
                 notice=False, number=None, is_emphasize=False,
                 desc=u"", hotkey=u""):
        base.SelectableSprite.__init__(self)
        self.parent = parent
        # 各種データ
        self.name = name
        self.sizetype = sizetype
        self.status = "normal"
        self.frame = 0
        self.is_showing = lambda: True
        self.maskmode = None

        self.desc = desc
        self.hotkey = hotkey
        self._desc = None

        self._upscr = 0
        self._blink_notice = False

        self.is_pushed = is_pushed
        self.is_emphasize = is_emphasize
        self.enabled = enabled
        self.notice = notice
        self.number = number
        self._create_paneimg(pos, icon)

    def _create_paneimg(self, pos, icon):
        # ボタン画像
        self.btnimg = {}

        # ボタンアイコン・ラベル
        if icon:
            self.icon = icon
        else:
            font = cw.cwpy.rsrc.fonts["sbarbtn"]
            self.icon = font.render(self.name, cw.cwpy.setting.fontsmoothing_statusbar, (0, 0, 0))

        if not self.enabled:
            self.icon = cw.imageretouch.to_disabledsurface(self.icon)

        # image
        self.image = self.get_unselectedimage()
        self.noimg = pygame.Surface(cw.s((0, 0))).convert()
        # rect
        self.rect = self.image.get_rect()
        self.rect.top = self.parent.rect.top + pos[1]
        self.rect.left = self.parent.rect.left + pos[0]

        # spritegroupに追加
        cw.cwpy.sbargrp.add(self, layer=LAYER_STATUS_ITEM)

    def get_icon(self):
        return None

    def reset(self, pos):
        self._create_paneimg(pos, self.get_icon())
        self._upscr = 0
        if self._desc:
            cw.cwpy.sbargrp.remove(self._desc)
            self._desc = None
        self.update(None)

    def _is_notice(self):
        if self.status == "blink":
            return self._blink_notice
        else:
            return self.notice

    def get_btnimg(self, flags):
        maskmode = cw.cwpy.statusbar.maskmode

        if self.maskmode <> maskmode:
            self.maskmode = maskmode
            self.btnimg.clear()

        key = (flags, cw.cwpy.statusbar.showbuttons)
        if key in self.btnimg:
            return self.btnimg[key]
        else:
            bmp = cw.cwpy.rsrc.get_statusbtnbmp(self.sizetype, flags)
            if maskmode:
                bmp.fill((64, 64, 64), special_flags=pygame.locals.BLEND_RGB_SUB)
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
            elif flags & cw.setting.SB_EMPHASIZE:
                icon = icon.convert_alpha()
                if flags & cw.setting.SB_PRESSED:
                    r = 96
                else:
                    r = 128
                icon.fill((r, 0, 0, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
            if not self.number is None:
                icon = cw.util.put_number(icon, self.number)
            bmp.blit(icon, rect.topleft)
            self.btnimg[key] = bmp
            return bmp

    def get_unselectedimage(self):
        flags = 0
        if self.enabled:
            if self.is_pushed:
                flags |= cw.setting.SB_PRESSED
            if self._is_notice():
                flags |= cw.setting.SB_NOTICE
            if self.is_emphasize:
                flags |= cw.setting.SB_EMPHASIZE
        else:
            flags |= cw.setting.SB_DISABLE

        return self.get_btnimg(flags)

    def get_selectedimage(self):
        flags = cw.setting.SB_CURRENT
        if self.enabled:
            if self.is_pushed:
                flags |= cw.setting.SB_PRESSED
            if self._is_notice():
                flags |= cw.setting.SB_NOTICE
            if self.is_emphasize:
                flags |= cw.setting.SB_EMPHASIZE
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

    def update_blink(self):
        sel = cw.cwpy.selection
        mousein = cw.cwpy.mousein[0]
        self.update_selection()

        if cw.cwpy.selection == self and cw.cwpy.mousein[0]:
            self.is_pushed = True
        else:
            self.is_pushed = False
        update = sel <> cw.cwpy.selection or mousein <> cw.cwpy.mousein[0]

        if 30 <= self.frame or not cw.cwpy.setting.blink_statusbutton:
            self.status = self.old_status
            self.frame = 0
            self.update_image()
            return

        blink_notice = self.frame / 5 % 2 == 0

        if self.need_update(blink_notice) or update:
            self.put_updatekey(blink_notice)
            self.update_image()

    def need_update(self, blink_notice):
        return self._blink_notice <> blink_notice or self._upscr <> cw.UP_SCR

    def put_updatekey(self, blink_notice):
        self._blink_notice = blink_notice
        self._upscr = cw.UP_SCR

    def set_desc(self, desc):
        self.desc = desc
        if self._desc:
            cw.cwpy.sbargrp.remove(self._desc)
            rect = self._desc.rect
            self._desc = None
            self._desc = Desc(self, self.name, self.desc, self.hotkey)
            cw.cwpy.sbargrp.add(self._desc, layer=LAYER_DESC)

    def is_selection(self):
        # FIXME: メッセージの選択肢と重なった領域でマウスポインタを
        #        動かすと解説表示が出たり消えたりするのを避ける。
        #        本来はすでに選択中のスプライトがselfより前にあれば
        #        マウスポインタ位置による選択を行わないという判定を
        #        SelectableSpriteに実装するべきだが、
        #        前後の判定が簡単ではないのでここで暫定的に対処する。
        b = cw.sprite.base.SelectableSprite.is_selection(self)
        if b and cw.cwpy.selection and isinstance(cw.cwpy.selection, cw.sprite.message.SelectionBar):
            return False
        return b

    def update_image(self):
        if not self.enabled:
            return

        if self.is_showing and not self.is_showing():
            self.image = self.noimg
            return

        if cw.cwpy.setting.show_btndesc and self.is_selection() and self.desc and not cw.cwpy.is_showingdlg():
            if not self._desc:
                self._desc = Desc(self, self.name, self.desc, self.hotkey)
                cw.cwpy.sbargrp.add(self._desc, layer=LAYER_DESC)
        else:
            if self._desc:
                cw.cwpy.sbargrp.remove(self._desc)
                self._desc = None
                cw.cwpy.has_inputevent = True

        flags = 0
        if self.is_pushed:
            flags |= cw.setting.SB_PRESSED
        if self.is_selection():
            flags |= cw.setting.SB_CURRENT
            cw.cwpy.has_inputevent = True
        if self._is_notice():
            flags |= cw.setting.SB_NOTICE
        if self.is_emphasize:
            flags |= cw.setting.SB_EMPHASIZE

        self.image = self.get_btnimg(flags)

    def lclick_event(self):
        cw.cwpy.stop_animation(self)
        cw.animation.animate_sprite(self, "click", statusbutton=True)

        if self._desc:
            cw.cwpy.sbargrp.remove(self._desc)
            self._desc = None

    def rclick_event(self):
        pass

class Desc(base.CWPySprite):
    def __init__(self, parent, name, desc, hotkey, arrowpos=None):
        base.CWPySprite.__init__(self)
        self.parent = parent
        self.name = name
        self.desc = desc
        self.hotkey = hotkey
        if self.name and self.hotkey:
            title = u"%s(%s)" % (self.name, self.hotkey)

        font = cw.cwpy.rsrc.fonts["sbardesc"]
        tfont = cw.cwpy.rsrc.fonts["sbardesctitle"]
        h = font.get_height()

        # 必要サイズを計算
        lines = self.desc.splitlines()
        spx = cw.s(8)
        spy = cw.s(4)
        tw, th = cw.s(1), spy*2
        # 表題
        if self.name and self.hotkey:
            th += cw.s(3)  # 表題と本文の間
            fw, fh = tfont.size(title)
            tw = max(tw, fw + spx*2)
            th += h
        # 本文
        for line in lines:
            fw, fh = font.size(line)
            tw = max(tw, fw + spx*2)
            th += h

        # 解説画像を作成
        arroww = cw.s(8)
        arrowh = cw.s(12)
        self.image = pygame.Surface((tw, th+arrowh)).convert_alpha()
        color = (255, 255, 200)
        self.image.fill(color)
        self.image.fill((0, 0, 0, 255), (cw.s(0), th, tw, arrowh), special_flags=pygame.locals.BLEND_RGBA_SUB)
        linecolor = (0, 0, 0)
        cw.setting.Resource.draw_frame(self.image, pygame.Rect(cw.s(0), cw.s(0), tw, th), linecolor)
        self.rect = self.image.get_rect()
        x, y = spx, spy
        if self.name and self.hotkey:
            # 表題
            subimg = tfont.render(title, True, linecolor)
            self.image.blit(subimg, (x, y))
            y += tfont.get_height() + cw.s(1)
            pygame.draw.line(self.image, linecolor, (x, y), (x+tw-spx*2, y), cw.s(1))
            y += cw.s(2)
        # 本文
        for line in lines:
            subimg = font.render(line, True, linecolor)
            self.image.blit(subimg, (x, y))
            y += h

        # ボタンに合わせて位置を調節
        if arrowpos is None:
            self.rect.center = self.parent.rect.center
        else:
            self.rect.left = self.parent.rect.left+arrowpos - self.rect.width//2
        _px, py = self.parent.rect.topleft
        self.rect.top = py - th - cw.s(5)

        # 画面内に収める
        if self.rect.left < cw.s(2):
            self.rect.left = cw.s(2)
        gw = cw.s(cw.SIZE_GAME[0])
        if gw <= self.rect.left + self.rect.width:
            self.rect.left = gw - cw.s(2) - self.rect.width

        # ボタンを指す部分
        if arrowpos is None:
            x = self.parent.rect.center[0]-self.rect.left
        else:
            x = self.parent.rect.left+arrowpos
            x -= self.rect.left
        y = th-1
        pl = [(x-arroww/2, y), (x, y+arrowh), (x+arroww/2, y)]
        pygame.draw.polygon(self.image, color, pl)
        pygame.draw.aalines(self.image, linecolor, False, pl)

        self.image.fill((255, 255, 255, 224), special_flags=pygame.locals.BLEND_RGBA_MULT)

class CampButton(StatusBarButton):
    def __init__(self, parent, pos):
        is_pushed = cw.cwpy.areaid in (-4, -5)
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["camp"], pos, is_pushed=is_pushed)
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

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
        if cw.cwpy.areaid >= 0:
            cw.cwpy.play_sound("click")
            cw.cwpy.change_specialarea(-4)
        elif cw.cwpy.areaid == -4:
            cw.cwpy.play_sound("click")
            cw.cwpy.clear_specialarea()

class TableButton(StatusBarButton):
    def __init__(self, parent, pos):
        is_pushed = not cw.cwpy.areaid in (-4, -5)
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["table"], pos, is_pushed=is_pushed)
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

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
            cw.cwpy.play_sound("click")
            cw.cwpy.clear_specialarea()
        elif cw.cwpy.areaid >= 0:
            cw.cwpy.play_sound("click")
            cw.cwpy.change_specialarea(-4)

class ActionButton(StatusBarButton):
    def __init__(self, parent, pos):
        autostart = cw.cwpy.setting.show_roundautostartbutton and\
            cw.cwpy.is_playingscenario() and\
            cw.cwpy.sdata.autostart_round
        StatusBarButton.__init__(self, parent, cw.cwpy.msgs["start_action"], pos,
                                 is_emphasize=autostart)
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

    def update(self, scr):
        if cw.cwpy.battle and cw.cwpy.battle.is_running() or cw.cwpy.areaid < 0:
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
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

    def update(self, scr):
        if cw.cwpy.battle and cw.cwpy.battle.is_running() or cw.cwpy.areaid < 0:
            self.image = self.noimg
        else:
            StatusBarButton.update(self, scr)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)

        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.call_modaldlg("RUNAWAY")

class CancelButton(StatusBarButton):
    def __init__(self, parent, pos):
        if cw.cwpy.areaid == cw.AREA_BREAKUP:
            s = cw.cwpy.msgs["complete"]
        else:
            s = cw.cwpy.msgs["entry_cancel"]
        StatusBarButton.__init__(self, parent, s, pos)
        self.selectable_on_event = False

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.cancel_cardcontrol()

class ShowFriendCardsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.s(cw.cwpy.rsrc.pygamedebugs["EVT_GET_CAST_noscale"])
        name = cw.cwpy.msgs["show_fcards"]
        desc = cw.cwpy.msgs["desc_show_friend_card"]
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image,
                                 is_pushed=cw.cwpy.setting.show_fcardsinbattle, desc=desc,
                                 hotkey=u"F6")
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

    def get_icon(self):
        return cw.s(cw.cwpy.rsrc.pygamedebugs["EVT_GET_CAST_noscale"])

    def update(self, scr):
        self.update_selection()

        self.is_pushed = cw.cwpy.setting.show_fcardsinbattle

        self.update_image()

    def lclick_event(self):
        cw.cwpy.play_sound("page")
        if cw.cwpy.is_battlestatus() and cw.cwpy.battle.is_ready():
            cw.cwpy.setting.show_fcardsinbattle = not cw.cwpy.setting.show_fcardsinbattle
            cw.cwpy.battle.update_showfcards()

class AutoStartButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["AUTO_START"]
        name = cw.cwpy.msgs["autostart_round"]
        if cw.cwpy.is_playingscenario():
            pushed = cw.cwpy.sdata.autostart_round
        else:
            pushed = False
        if pushed:
            desc = cw.cwpy.msgs["desc_auto_start_round"]
        else:
            desc = cw.cwpy.msgs["desc_manual_start_round"]
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image,
                                 is_pushed=pushed, desc=desc, hotkey=u"F7")
        self.selectable_on_event = True
        self.actionbtn = None
        self.is_showing = cw.cwpy.is_battlestatus

    def reset(self, pos):
        if cw.cwpy.is_playingscenario() and cw.cwpy.sdata.autostart_round:
            self.desc = cw.cwpy.msgs["desc_auto_start_round"]
        else:
            self.desc = cw.cwpy.msgs["desc_manual_start_round"]
        StatusBarButton.reset(self, pos)

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["AUTO_START"]

    def update(self, scr):
        self.update_selection()

        if cw.cwpy.is_playingscenario():
            self.is_pushed = cw.cwpy.sdata.autostart_round
        else:
            self.is_pushed = False

        self.update_image()

    def lclick_event(self):
        if cw.cwpy.is_playingscenario() and cw.cwpy.is_battlestatus():
            cw.cwpy.play_sound("page")
            if cw.cwpy.sdata.autostart_round:
                self.set_desc(cw.cwpy.msgs["desc_manual_start_round"])
                cw.cwpy.sdata.autostart_round = False
            else:
                self.set_desc(cw.cwpy.msgs["desc_auto_start_round"])
                cw.cwpy.sdata.autostart_round = True
            if self.actionbtn:
                autostart = cw.cwpy.setting.show_roundautostartbutton and\
                    cw.cwpy.is_playingscenario() and\
                    cw.cwpy.sdata.autostart_round
                self.actionbtn.is_emphasize = autostart
                self.actionbtn.update_image()

class InfoCardsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["INFOVIEW"]
        name = cw.cwpy.msgs["info_card"]
        desc = cw.cwpy.msgs["desc_info_cards"]
        notice = cw.cwpy.sdata.notice_infoview
        number = cw.cwpy.sdata.count_infocards()
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image,
                                 notice=notice, number=number, desc=desc, hotkey=u"F6")
        self.is_showing = cw.cwpy.is_playingscenario
        self.selectable_on_event = False

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["INFOVIEW"]

    def reset(self, pos):
        self.notice = cw.cwpy.sdata.notice_infoview
        self.number = cw.cwpy.sdata.count_infocards()
        StatusBarButton.reset(self, pos)

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.play_sound("click")
        cw.cwpy.clear_selection()
        cw.content.PostEventContent.do_action("ShowDialog", "INFOVIEW")

class SettingsButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["SETTINGS"]
        name = u"設定"
        desc = u"%sの設定を行います" % (cw.APP_NAME)
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image, desc=desc, hotkey=u"F2")
        self.selectable_on_event = True
        if self.is_selection():
            self.update_image()

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["SETTINGS"]

    def lclick_event(self):
        StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f2key_event()

class DebuggerButton(StatusBarButton):
    def __init__(self, parent, pos):
        image = cw.cwpy.rsrc.pygamedialogs["STATUS12"]
        name = u"デバッガ"
        desc = u"デバッガを表示します"
        pushed = cw.cwpy.is_showingdebugger()
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image, desc=desc,
                                 is_pushed=pushed, hotkey=u"F3")
        self.selectable_on_event = True
        self.is_showing = cw.cwpy.is_debugmode

    def update(self, scr):
        self.update_selection()

        self.is_pushed = cw.cwpy.is_showingdebugger()
        if self.is_pushed:
            self.set_desc(u"デバッガを閉じます")
        else:
            self.set_desc(u"デバッガを表示します")

        self.update_image()

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["STATUS12"]

    def lclick_event(self):
        cw.cwpy.eventhandler.f3key_event()

class BacklogButton(StatusBarButton):
    def __init__(self, parent, pos):
        enabled = cw.cwpy.has_backlog()
        pushed = cw.cwpy.setting.is_logscrollable() and cw.cwpy.is_showingbacklog()
        image = cw.cwpy.rsrc.pygamedialogs["BACKLOG"]
        name = cw.cwpy.msgs["message_log"]
        if pushed:
            desc = cw.cwpy.msgs["desc_close_message_log"]
        else:
            desc = cw.cwpy.msgs["desc_message_log"]
        StatusBarButton.__init__(self, parent, name, pos, 1, icon=image, enabled=enabled,
                                 desc=desc, hotkey=u"F5", is_pushed=pushed)
        self.selectable_on_event = enabled
        if enabled and self.is_selection():
            self.update_image()

    def update(self, scr):
        if self.status <> "normal":
            StatusBarButton.update(self, scr)
            return
        self.update_selection()

        self.is_pushed = cw.cwpy.setting.is_logscrollable() and cw.cwpy.is_showingbacklog()
        if self.is_pushed:
            desc = cw.cwpy.msgs["desc_close_message_log"]
        else:
            desc = cw.cwpy.msgs["desc_message_log"]
        self.set_desc(desc)

        self.update_image()

    def reset(self, pos):
        self.enabled = cw.cwpy.has_backlog()
        self.selectable_on_event = self.enabled

        self.is_pushed = cw.cwpy.setting.is_logscrollable() and cw.cwpy.is_showingbacklog()
        if self.is_pushed:
            desc = cw.cwpy.msgs["desc_close_message_log"]
        else:
            desc = cw.cwpy.msgs["desc_message_log"]
        StatusBarButton.reset(self, pos)

    def get_icon(self):
        return cw.cwpy.rsrc.pygamedialogs["BACKLOG"]

    def lclick_event(self):
        if not self.enabled:
            return
        if not cw.cwpy.setting.is_logscrollable():
            StatusBarButton.lclick_event(self)
        cw.cwpy.eventhandler.f5key_event()

def main():
    pass

if __name__ == "__main__":
    main()
