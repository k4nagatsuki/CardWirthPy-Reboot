#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import sys
import array
import struct
import threading
import wx
import pygame
from pygame.locals import *

import cw
from wx import IMAGE_QUALITY_HIGH


class Image(object):
    def __init__(self, image):
        self.image = image

    def get_image(self):
        return self.image

    def get_negaimg(self):
        image = self.get_image()
        return cw.imageretouch.to_negative(image)

#-------------------------------------------------------------------------------
# カード関係
#-------------------------------------------------------------------------------

class CardImage(Image):
    def __init__(self, path, bgtype, name="", premium="", scaleinfo=None):
        """
        カード画像と背景画像とカード名を合成・加工し、
        wxPythonとPygame両方で使える画像オブジェクトを生成する。
        """
        self.name = name
        self.path = path
        self.bgtype = bgtype
        self.image_mtime = 0
        self.premium = premium
        self.scaleinfo = scaleinfo

        self.update_scale()

    def update_scale(self):
        self.cardbg = cw.cwpy.rsrc.cardbgs[self.bgtype]
        self.rect = self.cardbg.get_rect()
        wxsize = cw.wins(cw.setting.SIZE_RESOURCES["CardBg/" + self.bgtype])
        self.wxrect = pygame.Rect(0, 0, wxsize[0], wxsize[1])

    @property
    def wxcardbg(self):
        return cw.cwpy.rsrc.wxcardbgs[self.bgtype]

    def is_modifiedfile(self):
        if cw.binary.image.path_is_code(self.path):
            return False
        else:
            path = cw.util.get_yadofilepath(self.path)

        if not path:
            path = self.path
        if not os.path.isfile(path):
            return False

        return self.image_mtime <> os.path.getmtime(path)

    def get_image(self):
        image = self.cardbg.copy()

        # プレミア画像
        if self.premium == "Rare":
            subimg = cw.cwpy.rsrc.cardbgs["RARE"]
            image.blit(subimg, cw.s((64, 5)))
            image.blit(subimg, cw.s((5, 64)))
        elif self.premium == "Premium":
            subimg = cw.cwpy.rsrc.cardbgs["PREMIER"]
            image.blit(subimg, cw.s((64, 5)))
            image.blit(subimg, cw.s((5, 41)))

        pisc = cw.binary.image.path_is_code(self.path)
        if pisc:
            path = self.path
        else:
            path = cw.util.get_yadofilepath(self.path)

        if not path:
            path = self.path

        if not pisc and os.path.isfile(path):
            self.image_mtime = os.path.getmtime(path)
        else:
            self.image_mtime = 0

        subimg = cw.s((cw.util.load_image(path, True), cw.SIZE_CARDIMAGE, self.scaleinfo))
        image.blit(subimg, cw.s((3, 13)))
        font = cw.cwpy.rsrc.fonts["mcard_name"]
        subimg = font.render(self.name, True, (0, 0, 0))
        w, h = subimg.get_size()

        left = cw.s(5)
        if w + left*2 > self.rect.w:
            size = (self.rect.w - left*2, h)
            subimg = pygame.transform.smoothscale(subimg, size)

        image.blit(subimg, (left, cw.s(5)))
        return image

    def get_cardimg(self, header):
        if header.negaflag:
            image = self.get_negaimg()
        else:
            image = self.get_image()

        if not hasattr(header, "type"):
            return image

        if header.type in ("ItemCard", "BeastCard"):
            uselimit, maxn = header.get_uselimit()

            # 使用回数(数字)
            if maxn or (header.type == "BeastCard" and not header.attachment):
                font = cw.cwpy.rsrc.fonts["card_uselimit"]
                s = str(uselimit)
                pos = cw.s((5, 90))
                for c in s:
                    subimg = font.render(c, True, (0, 0, 0))
                    image.blit(subimg, (pos[0]+1, pos[1]-1))
                    image.blit(subimg, (pos[0],   pos[1]-1))
                    image.blit(subimg, (pos[0]-1, pos[1]-1))
                    image.blit(subimg, (pos[0]-1, pos[1]))
                    image.blit(subimg, (pos[0]+1, pos[1]))
                    image.blit(subimg, (pos[0]+1, pos[1]+1))
                    image.blit(subimg, (pos[0],   pos[1]+1))
                    image.blit(subimg, (pos[0]-1, pos[1]+1))

                    if header.recycle:
                        colour = (255, 255, 0)
                    else:
                        colour = (255, 255, 255)

                    subimg = font.render(c, True, colour)
                    image.blit(subimg, pos)
                    pos = pos[0] + cw.s(10), pos[1]

        owner = header.get_owner()
        if isinstance(owner, cw.character.Character):
            # 適性値
            key = "HAND" + str(header.get_vocation_level(owner))
            subimg = cw.cwpy.rsrc.stones[key]
            image.blit(subimg, cw.s((60, 90)))

            # 使用回数(画像)
            if header.type == "SkillCard":
                key = "HAND" + str(header.get_uselimit_level() + 5)
                subimg = cw.cwpy.rsrc.stones[key]
                image.blit(subimg, cw.s((60, 75)))

            # ホールド
            if header.ref_original() and header.ref_original().hold:
                subimg = cw.cwpy.rsrc.cardbgs["HOLD"]
                image.blit(subimg, cw.s((0, 0)))

            # ペナルティ
            if header.penalty:
                subimg = cw.cwpy.rsrc.cardbgs["PENALTY"]
                image.blit(subimg, cw.s((0, 0)))

        return image

    def get_negaimg(self):
        # カード画像の外枠は色反転しない
        image = self.get_image()
        return cw.imageretouch.to_negative_for_card(image)

    def get_clickedimg(self, rect=None, image=None):
        if not rect:
            rect = self.rect

        size = (rect.w * 9 / 10, rect.h * 9 / 10)
        if image:
            negaimg = image
        else:
            negaimg = self.get_negaimg()
        return pygame.transform.scale(negaimg, size)

    def get_wxbmp(self):
        w, h = self.wxrect.size
        bmp = wx.EmptyBitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.DrawBitmap(self.wxcardbg, 0, 0, False)

        # プレミア画像
        if self.premium == "Rare":
            subimg = cw.cwpy.rsrc.wxcardbgs["RARE"]
            dc.DrawBitmap(subimg, cw.wins(64), cw.wins(5), True)
            dc.DrawBitmap(subimg, cw.wins(5), cw.wins(64), True)
        elif self.premium == "Premium":
            subimg = cw.cwpy.rsrc.wxcardbgs["PREMIER"]
            dc.DrawBitmap(subimg, cw.wins(64), cw.wins(5), True)
            dc.DrawBitmap(subimg, cw.wins(5), cw.wins(41), True)

        pisc = cw.binary.image.path_is_code(self.path)
        if pisc:
            path = self.path
        else:
            path = cw.util.get_yadofilepath(self.path)

        if not path:
            path = self.path

        cw.util.t_start()
        subimg = cw.util.load_wxbmp(path, True)
        subimg = cw.wins((subimg, cw.SIZE_CARDIMAGE, self.scaleinfo))
        dc.DrawBitmap(subimg, cw.wins(3), cw.wins(13), True)
        font = cw.cwpy.rsrc.get_wxfont("cardname", pixelsize=cw.wins(14)*2, weight=wx.BOLD)
        dc.SetFont(font)
        w, h = dc.GetTextExtent(self.name)
        subimg = wx.EmptyBitmap(w, h)
        dc.SelectObject(subimg)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawRectangle(-1, -1, w + 2, h + 2)
        dc.SetTextForeground(wx.WHITE)
        dc.DrawText(self.name, cw.wins(0), cw.wins(0))
        dc.SelectObject(bmp)
        subimg = subimg.ConvertToImage()
        subimg.ConvertColourToAlpha(0, 0, 0)

        left = cw.wins(5)
        if w/2 + left*2 > self.wxrect.width:
            size = (self.wxrect.width - left*2, h/2)
            subimg = subimg.Rescale(size[0], h/2, quality=IMAGE_QUALITY_HIGH)
        else:
            subimg = subimg.Rescale(w/2, h/2, quality=IMAGE_QUALITY_HIGH)

        subimg = subimg.ConvertToBitmap()

        dc.DrawBitmap(subimg, left, cw.wins(5))

        dc.SelectObject(wx.NullBitmap)

        return bmp

    def get_cardwxbmp(self, header):
        if header.negaflag:
            image = self.get_wxnegabmp()
        else:
            image = self.get_wxbmp()

        if not hasattr(header, "type"):
            return image

        dc = wx.MemoryDC()
        dc.SelectObject(image)

        if header.type in ("ItemCard", "BeastCard"):
            uselimit, maxn = header.get_uselimit()

            # 使用回数(数字)
            if maxn or (header.type == "BeastCard" and not header.attachment):
                font = cw.cwpy.rsrc.get_wxfont("uselimit", pixelsize=cw.wins(18), weight=wx.NORMAL)
                dc.SetFont(font)
                s = str(uselimit)
                pos = cw.wins((5, 90))
                for c in s:
                    dc.SetTextForeground(wx.BLACK)
                    dc.DrawText(c, pos[0]+1, pos[1]-1)
                    dc.DrawText(c, pos[0],   pos[1]-1)
                    dc.DrawText(c, pos[0]-1, pos[1]-1)
                    dc.DrawText(c, pos[0]-1, pos[1])
                    dc.DrawText(c, pos[0]+1, pos[1])
                    dc.DrawText(c, pos[0]+1, pos[1]+1)
                    dc.DrawText(c, pos[0],   pos[1]+1)
                    dc.DrawText(c, pos[0]-1, pos[1]+1)

                    if header.recycle:
                        dc.SetTextForeground(wx.YELLOW)
                    else:
                        dc.SetTextForeground(wx.WHITE)

                    dc.DrawText(c, pos[0], pos[1])
                    pos = pos[0] + cw.wins(10), pos[1]

        owner = header.get_owner()
        if isinstance(owner, cw.character.Character):
            # 適性値
            key = "HAND" + str(header.get_vocation_level(owner))
            subimg = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(subimg, cw.wins(60), cw.wins(90), True)

            # 使用回数(画像)
            if header.type == "SkillCard":
                key = "HAND" + str(header.get_uselimit_level() + 5)
                subimg = cw.cwpy.rsrc.wxstones[key]
                dc.DrawBitmap(subimg, cw.wins(60), cw.wins(75), True)

            # ホールド
            if header.ref_original() and header.ref_original().hold:
                subimg = cw.cwpy.rsrc.wxcardbgs["HOLD"]
                dc.DrawBitmap(subimg, cw.wins(0), cw.wins(0), True)

            # ペナルティ
            if header.penalty:
                subimg = cw.cwpy.rsrc.wxcardbgs["PENALTY"]
                dc.DrawBitmap(subimg, cw.wins(0), cw.wins(0), True)

        dc.SelectObject(wx.NullBitmap)

        return image

    def get_wxnegabmp(self):
        image = self.get_wxbmp()
        return cw.imageretouch.to_negative_for_wxcard(image)

    def get_wxclickedbmp(self, header, wxbmp):
        size = (self.wxrect.width * 9 / 10, self.wxrect.height * 9 / 10)
        if wxbmp:
            negaimg = wxbmp
        else:
            negaimg = self.get_cardwxbmp(header)

        # FIXME: この処理がないとnegaimg.ConvertToImage()の時点で化ける
        w, h = negaimg.GetWidth(), negaimg.GetHeight()
        buf = array.array('B', [0] * (w*h * 3))
        negaimg.CopyToBuffer(buf)
        negaimg = wx.BitmapFromBuffer(w, h, buf)

        image = negaimg.ConvertToImage()
        image = image.Rescale(size[0], size[1], quality=IMAGE_QUALITY_HIGH)
        return image.ConvertToBitmap()

    def update(self, card):
        pass

class LargeCardImage(CardImage):
    def __init__(self, path, bgtype, name="", premium="", scaleinfo=None):
        CardImage.__init__(self, path, "LARGE", name, premium, scaleinfo)

    def get_image(self):
        image = self.cardbg.copy()

        # プレミア画像
        if self.premium == "Rare":
            subimg = cw.cwpy.rsrc.cardbgs["RARE"]
            image.blit(subimg, cw.s((64, 5)))
            image.blit(subimg, cw.s((5, 64)))
        elif self.premium == "Premium":
            subimg = cw.cwpy.rsrc.cardbgs["PREMIER"]
            image.blit(subimg, cw.s((64, 5)))
            image.blit(subimg, cw.s((5, 41)))

        subimg = cw.s((cw.util.load_image(self.path, True), cw.SIZE_CARDIMAGE, self.scaleinfo))
        image.blit(subimg, cw.s((10, 23)))
        font = cw.cwpy.rsrc.fonts["mcard_name"]
        subimg = font.render(self.name, True, (0, 0, 0))
        w, h = subimg.get_size()

        if w + cw.s(3) > self.rect.w:
            size = (self.rect.w - cw.s(12), h)
            subimg = pygame.transform.smoothscale(subimg, size)

        image.blit(subimg, cw.s((6, 6)))
        return image

class CharacterCardImage(CardImage):
    def __init__(self, ccard, pos_noscale=(0, 0), scaleinfo=None):
        self.ccard = ccard
        self._pos_noscale = pos_noscale
        self.scaleinfo = scaleinfo
        self.image_mtime = 0
        self.update_scale()

    def update_scale(self):
        # カード画像
        self.set_faceimg(self.ccard.imgpath)
        # フォント画像(カード名)
        self.set_nameimg(self.ccard.name)
        # フォント画像(レベル)
        self.set_levelimg(self.ccard.level)
        # ライフバー画像
        guagesize = cw.setting.SIZE_RESOURCES["Status/LIFEGUAGE"]
        self.lifeimg = pygame.Surface(guagesize).convert()
        guage = cw.cwpy.rsrc.statuses["LIFEGUAGE"]
        self.lifeguage = guage
        self.lifebar = cw.cwpy.rsrc.statuses["LIFEBAR"]
        self.lifeimg.set_colorkey(guage.get_at((0, 0)), RLEACCEL)
        # rect
        self.rect = pygame.Rect(cw.s(self._pos_noscale), cw.s((95, 130)))

    def set_faceimg(self, path):
        self.path = path
        if not cw.binary.image.path_is_code(self.path):
            path = cw.util.get_yadofilepath(path)
        self.cardimg = cw.s((cw.util.load_image(path, True), cw.SIZE_CARDIMAGE, self.scaleinfo))

    def set_nameimg(self, name):
        font = cw.cwpy.rsrc.fonts["pcard_name"]
        self.nameimg = font.render(name, True, (0, 0, 0))
        w, h = self.nameimg.get_size()

        if w + cw.s(14) > cw.s(95):
            size = (cw.s(95 - 14), h)
            self.nameimg = pygame.transform.smoothscale(self.nameimg, size)

    def set_levelimg(self, level):
        font = cw.cwpy.rsrc.fonts["pcard_level"]
        s = str(level)
        w = 0
        h = 0
        for c in s:
            size = font.size(c)
            w += max(size[0], cw.s(18))
            h = max(size[1], h)
        size = (w, h)
        self.levelimg = pygame.Surface(size, SRCALPHA).convert_alpha()

        for index, char in enumerate(reversed(s)):
            subimg = font.render(char, True, (0, 0, 0))
            self.levelimg.blit(subimg, (w - subimg.get_width(), cw.s(0)))
            w -= cw.s(18)

        for x in xrange(size[0]):
            for y in xrange(size[1]):
                color = self.levelimg.get_at((x, y))
                if color[3] <> 0:
                    color[3] = color[3] / 2
                    self.levelimg.set_at((x, y), color)

    def update(self, ccard, header=None):
        # 画像合成
        bgname = self.get_cardbgname(ccard)
        self.image = cw.cwpy.rsrc.cardbgs[bgname].copy()

        # レベル
        if ccard.is_analyzable():
            self.image.blit(self.levelimg, (cw.s(90) - self.levelimg.get_width(), cw.s(2)))

        # カード画像
        insets_n = cw.s(18)
        insets_e = cw.s(10)
        insets_s = cw.s(18)
        insets_w = cw.s(10)
        bw = cw.s(95) - insets_w - insets_e
        bh = cw.s(130) - insets_n - insets_s
        dw = self.cardimg.get_width()
        dh = self.cardimg.get_height()
        x = insets_w + (bw - dw) / 2
        y = insets_n + (bh - dh) / 2
        self.image.blit(self.cardimg, (x, y))

        # 名前
        self.image.blit(self.nameimg, cw.s((7, 4)))

        # ライフ
        if ccard.is_analyzable():
            guagesize = cw.setting.SIZE_RESOURCES["Status/LIFEGUAGE"]
            lifeper = ccard.get_lifeper()
            self.lifeimg.blit(self.lifebar, (int(0.79 * (lifeper - 100)), 1))
            self.lifeimg.blit(self.lifeguage, (0, 0))
            self.image.blit(cw.s((self.lifeimg, guagesize)), cw.s((9, 111)))

        # ステータス画像追加
        self.update_statusimg(ccard)

        if header:
            # 適性表示(カード移動時)
            key = "HAND" + str(header.get_vocation_level(ccard))
            subimg = cw.cwpy.rsrc.stones[key]
            self.image.blit(subimg, cw.s((73, 95)))

    def update_statusimg(self, ccard):
        seq = []
        az = ccard.is_analyzable()

        beastnum = ccard.has_beast()
        if beastnum: # 召喚獣所持(付帯召喚以外)
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["SUMMON"], beastnum, True))
        if ccard.is_poison(): # 中毒
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["BODY0"], ccard.poison if az else 0))
        if cw.cwpy.setting.show_statustime and ccard.is_paralyze(): # 麻痺
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["BODY1"], ccard.paralyze if az else 0))
        if cw.cwpy.setting.show_statustime and ccard.is_sleep(): # 睡眠
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND1"], ccard.mentality_dur if az else 0))
        if ccard.is_confuse(): # 混乱
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND2"], ccard.mentality_dur if az else 0))
        elif ccard.is_overheat(): # 激昂
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND3"], ccard.mentality_dur if az else 0))
        elif ccard.is_brave(): # 勇敢
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND4"], ccard.mentality_dur if az else 0))
        elif ccard.is_panic(): # 恐慌
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND5"], ccard.mentality_dur if az else 0))
        if cw.cwpy.setting.show_statustime and ccard.is_bind(): # 呪縛
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC0"], ccard.bind if az else 0))
        if ccard.is_silence(): # 沈黙
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC1"], ccard.silence if az else 0))
        if ccard.is_faceup(): # 暴露
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC2"], ccard.faceup if az else 0))
        if ccard.is_antimagic(): # 魔法無効化
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC3"], ccard.antimagic if az else 0))
        if ccard.enhance_act > 0: # 行動力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP0"], ccard.enhance_act, ccard.enhance_act_dur if az else 0)
        elif ccard.enhance_act < 0: # 行動力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN0"], ccard.enhance_act, ccard.enhance_act_dur if az else 0)
        if ccard.enhance_avo > 0: # 回避力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP1"], ccard.enhance_avo, ccard.enhance_avo_dur if az else 0)
        elif ccard.enhance_avo < 0: # 回避力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN1"], ccard.enhance_avo, ccard.enhance_avo_dur if az else 0)
        if ccard.enhance_res > 0: # 抵抗力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP2"], ccard.enhance_res, ccard.enhance_res_dur if az else 0)
        elif ccard.enhance_res < 0: # 抵抗力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN2"], ccard.enhance_res, ccard.enhance_res_dur if az else 0)
        if ccard.enhance_def > 0: # 防御力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP3"], ccard.enhance_def, ccard.enhance_def_dur if az else 0)
        elif ccard.enhance_def < 0: # 防御力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN3"], ccard.enhance_def, ccard.enhance_def_dur if az else 0)

        x = cw.s(7)
        if ccard.is_analyzable():
            y = cw.s(92)
        else:
            y = cw.s(107)

        index = 0
        for subimg in seq:
            pos = (x + index / 5 * cw.s(17), y - index * cw.s(17) + index / 5 * cw.s(85))
            if type(subimg) is pygame.Surface:
                self.image.blit(subimg, pos)
                index += 1
            else:
                self.image.fill(subimg[0], pygame.Rect(pos, subimg[1]))

    def _put_number(self, image, num, always=False):
        if (always or cw.cwpy.setting.show_statustime) and num:
            image = cw.util.put_number(image, num)
        return image

    def _put_enhanceimg(self, seq, bmp, value, duration):
        size = (bmp.get_width(), bmp.get_height())
        if value >= 10:
            seq.append((pygame.Color(255, 0, 0), size))
        elif value >= 7:
            seq.append((pygame.Color(175, 0, 0), size))
        elif value >= 4:
            seq.append((pygame.Color(127, 0, 0), size))
        elif value >= 1:
            seq.append((pygame.Color(79, 0, 0), size))
        elif value <= -10:
            seq.append((pygame.Color(0, 0, 51), size))
        elif value <= -7:
            seq.append((pygame.Color(0, 0, 85), size))
        elif value <= -4:
            seq.append((pygame.Color(0, 0, 136), size))
        elif value <= -1:
            seq.append((pygame.Color(0, 0, 187), size))
        bmp = self._put_number(bmp, duration)
        seq.append(bmp)

    def get_cardbgname(self, ccard):
        if ccard.is_unconscious():
            return "FAINT"  # 意識不明
        elif ccard.is_petrified():
            return "PETRIF" # 石化
        elif ccard.is_paralyze():
            return "PARALY" # 麻痺
        elif ccard.is_sleep():
            return "SLEEP"  # 睡眠
        elif ccard.is_bind():
            return "BIND"   # 呪縛
        elif ccard.is_heavyinjured():
            return "DANGER" # 重傷
        elif ccard.is_injured():
            return "INJURY" # 負傷
        else:
            return "LARGE"  # 正常

    def get_image(self):
        return self.image

    def get_cardwxbmp(self, header):
        return self.get_wxbmp()

    def get_cardimg(self, header):
        return self.get_image()

#-------------------------------------------------------------------------------
# 背景セル関係
#-------------------------------------------------------------------------------

def create_type2textcell(text, face, size, color,
        bold, italic, uline, sline, vertical,
        cellsize, bcolor, bwidth):
    """縁取りType2のテキストセルを作成する。
    """
    img = pygame.Surface(cellsize).convert_alpha()
    img.fill((0, 0, 0, 0))

    w = cellsize[0]
    h = cellsize[1]

    # text
    font, lineheight = get_textcellfont(size, face, color, bold,
                                        italic, uline, vertical, False)

    lines = text.splitlines()
    if vertical:
        x = w - lineheight
    else:
        x = 0
    y = 0
    for line in lines:
        subimg = font.render(line, True, color)
        # 取消線
        if sline:
            subimg2 = font.render(u"―", False, color)
            size = (subimg.get_width() + cw.s(10), subimg.get_height())
            subimg2 = pygame.transform.scale(subimg2, size)
            subimg.blit(subimg2, cw.s((-5, 0)))

        if vertical:
            subimg = pygame.transform.rotate(subimg, -90)

        img.blit(subimg, (x, y))
        if vertical:
            x -= lineheight
        else:
            y += lineheight

    # border
    cw.imageretouch.add_border(img, bcolor, bwidth)

    return img

def draw_textcell(image, rect, text, face, size, color,
        bold, italic, uline, sline, vertical, bcolor=None):
    """縁取りType2以外のテキストセルを描画する。
    """
    img = pygame.Surface(rect.size).convert_alpha()
    img.fill((0, 0, 0, 0))
    font, lineheight = get_textcellfont(size, face, color, bold,
                                       italic, uline, vertical, True)
    lines = text.splitlines()
    if vertical:
        x = rect.width
        x -= lineheight
    else:
        x = 0
    y = 0

    for line in lines:
        if bcolor:
            subimg = font.render(line, True, bcolor)
            if sline:
                subimg2 = font.render(u"―", False, bcolor)
                size = (subimg.get_width() + cw.s(10), lineheight)
                subimg2 = pygame.transform.scale(subimg2, size)
                subimg.blit(subimg2, cw.s((-5, 0)))
            if vertical:
                subimg = pygame.transform.rotate(subimg, -90)
            for xx in xrange(-1, 2):
                for yy in xrange(-1, 2):
                    if xx == 0 and yy == 0:
                        continue
                    img.blit(subimg, (x+xx, y+yy))
        subimg = font.render(line, True, color)
        if sline:
            subimg2 = font.render(u"―", False, color)
            size = (subimg.get_width() + cw.s(10), lineheight)
            subimg2 = pygame.transform.scale(subimg2, size)
            subimg.blit(subimg2, cw.s((-5, 0)))
        if vertical:
            subimg = pygame.transform.rotate(subimg, -90)

        if vertical:
            x -= lineheight

        img.blit(subimg, (x, y))

        if not vertical:
            y += lineheight

    image.blit(img, rect.topleft)

def get_textcellfont(size, face, color, bold, italic,
                     uline, vertical, antialiased):
    """テキストセル用のフォントを生成し、
    (font, lineheight)を返す。
    """
    if size % 2 == 0:
        # BUG: CardWirthでは偶数サイズは1px小さなサイズと同じになる
        size -= 1

    font = cw.imageretouch.Font(face, size+cw.s(1), bold, italic)
    if uline:
        font.set_underline(True)

    return font, font.get_height()

def create_colorcell(size, color1, gradient, color2):
    """ブレンド前のカラーセルを生成し、
    pygame.Surfaceのインスタンスを返す。
    size: セルのサイズ
    color1: 基本色
    gradient: グラデーション方向。
              "None","LeftToRight","TopToBottom"のいずれか
    color2: 終端色
    """
    image = pygame.Surface(size).convert_alpha()

    def calc_per(mn, mx, per):
        if mn == mx:
            return mn
        c = mx - mn
        return min(255, max(0, int(mn + c * per)))

    w = image.get_width()
    h = image.get_height()
    if gradient == "LeftToRight":
        for x in xrange(w):
            per = float(x) / w
            r = calc_per(color1[0], color2[0], per)
            g = calc_per(color1[1], color2[1], per)
            b = calc_per(color1[2], color2[2], per)
            a = calc_per(color1[3], color2[3], per)
            pygame.draw.line(image, (r, g, b, a), (x, 0), (x, h), 1)
    elif gradient == "TopToBottom":
        for y in xrange(h):
            per = float(h - y) / h
            r = calc_per(color2[0], color1[0], per) # 縦グラデーションは色の方向が逆
            g = calc_per(color2[1], color1[1], per)
            b = calc_per(color2[2], color1[2], per)
            a = calc_per(color2[3], color1[3], per)
            pygame.draw.line(image, (r, g, b, a), (0, y), (w, y), 1)
    else:
        image.fill(color1)
    return image

#-------------------------------------------------------------------------------
# 画像変換用関数
#-------------------------------------------------------------------------------

def conv2wxbmp(image, maskpos=(0, 0)):
    """pygame.Surfaceをwx.Bitmapに変換する。
    image: pygame.Surface
    """
    w, h = image.get_size()

    if (image.get_flags() & SRCALPHA) or image.get_colorkey():
        buf = pygame.image.tostring(image, "RGBA")
        wxbmp = wx.BitmapFromBufferRGBA(w, h, buf)
    else:
        buf = pygame.image.tostring(image, "RGB")
        wxbmp = wx.BitmapFromBuffer(w, h, buf)

    if image.get_colorkey():
        r, g, b, a = image.get_at(maskpos)
        wxbmp.SetMaskColour(wx.Colour(r, g, b))

    return wxbmp

def conv2surface(wxbmp):
    """wx.Bitmapをpygame.Surfaceに変換する。
    wxbmp: wx.Bitmap
    """
    w, h = wxbmp.GetSize()
    wximg = wxbmp.ConvertToImage()

    if wxbmp.HasAlpha():
        data = wximg.GetData()
        r_data = data[0::3]
        g_data = data[1::3]
        b_data = data[2::3]
        a_data = wximg.GetAlphaData()
        seq = []

        for cnt in xrange(w * h):
            seq.append((r_data[cnt] + g_data[cnt] + b_data[cnt] + a_data[cnt]))

        buf = "".join(seq)
        image = pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()
    else:
        wximg = wxbmp.ConvertToImage()
        buf = wximg.GetData()
        image = pygame.image.frombuffer(buf, (w, h), "RGB").convert()

    if wximg.HasMask():
        image.set_colorkey(wximg.GetOrFindMaskColour(), RLEACCEL)

    return image

#-------------------------------------------------------------------------------
# ユーティリティ
#-------------------------------------------------------------------------------

def fix_cwnext16bitbitmap(data):
    """一部バージョンのCardWirthNextが生成するBitmap(16 bit)は
    bfOffBitsが壊れているので予め訂正する。
    FIXME: 末尾に余計なデータがついている画像は却って上手くいかない可能性があるが、
           非常にレアなケースなのでまず問題にはならないと思われる。
    """
    if len(data) < 14 + 40:
        return data, True
    s = struct.unpack("<BBIhhIIIiHHiIIIII", data[0:14+40])
    if s[0] <> ord('B'):
        return data, True
    if s[1] <> ord('M'):
        return data, True
    bfSize = s[2]
    bfReserved1 = s[3]
    bfReserved2 = s[4]
    bfOffBits = s[5]
    if bfOffBits == 0:
        return data, True
    biSize = s[6]
    if biSize <> 40:
        return data, True
    biWidth = s[7]
    biHeight = s[8]
    biPlanes = s[9]
    biBitCount = s[10]
    biCompression = s[11]
    biSizeImage = s[12]
    biXPixPerMeter = s[13]
    biYPixPerMeter = s[14]
    biClrUsed = s[15]
    biClrImporant = s[16]
    lineSize = ((biWidth * biBitCount + 31) / 32) * 4
    height = -biHeight if biHeight < 0 else biHeight
    if len(data) - bfOffBits <> lineSize * height:
        if threading.currentThread() <> cw.cwpy:
            # wxPythonは無理やり読み込んで壊れた画像を作ってしまうので
            # pygame側でエラーが出るか調べる
            with io.BytesIO(data) as f:
                try:
                    pygame.image.load(f)
                    return data, True
                except:
                    pass
        # bfOffBitsをヘッダ直後に修正
        bfOffBits = 14 + 40
        if biCompression == 3:
            # ビットフィールド情報がある場合
            bfOffBits += 4 * 3
        b = struct.pack("<I", bfOffBits)
        data = data[0:10] + b + data[14:]
        return data, False
    return data, True

def main():
    pass

if __name__ == "__main__":
    main()
