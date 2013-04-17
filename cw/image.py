#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import pygame
from pygame.locals import *

import cw


class Image(object):
    def __init__(self, image):
        self.image = image

    def get_image(self):
        return self.image

    def get_negaimg(self):
        image = self.get_image()
        return cw.imageretouch.to_negative(image)

    def get_wxbmp(self):
        image = self.get_image()
        return conv2wxbmp(image)

    def get_wxnegabmp(self):
        image = self.get_negaimg()
        return conv2wxbmp(image)

#-------------------------------------------------------------------------------
# カード関係
#-------------------------------------------------------------------------------

class CardImage(Image):
    def __init__(self, path, bgtype, name="", premium=""):
        """
        カード画像と背景画像とカード名を合成・加工し、
        wxPythonとPygame両方で使える画像オブジェクトを生成する。
        """
        self.name = name
        self.path = path
        self.bgtype = bgtype
        # FIXME: 画像ファイル読み込みにディスクキャッシュをきかすため。
        cw.util.load_image(path)
        self.premium = premium
        self.update_scale()

    def update_scale(self):
        self.cardbg = cw.cwpy.rsrc.cardbgs[self.bgtype]
        self.rect = self.cardbg.get_rect()

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

        if cw.binary.image.path_is_code(self.path):
            path = self.path
        else:
            path = cw.util.get_yadofilepath(self.path)

        if not path:
            path = self.path

        subimg = cw.s((cw.util.load_image(path, True), cw.SIZE_CARDIMAGE))
        image.blit(subimg, cw.s((3, 13)))
        font = cw.cwpy.rsrc.fonts["mcard_name"]
        subimg = font.render(self.name, True, (0, 0, 0))
        w, h = subimg.get_size()

        left = cw.s(5)
        if w + left > self.rect.w:
            size = (self.rect.w - left*2, h)
            subimg = pygame.transform.scale(subimg, size)

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
                subimg = font.render(s, False, (0, 0, 0))
                pos = cw.s((5, 90))
                image.blit(subimg, (pos[0]+1, pos[1]))
                image.blit(subimg, (pos[0]-1, pos[1]))
                image.blit(subimg, (pos[0], pos[1]+1))
                image.blit(subimg, (pos[0], pos[1]-1))

                if header.recycle:
                    colour = (255, 255, 0)
                else:
                    colour = (255, 255, 255)

                subimg = font.render(s, False, colour)
                image.blit(subimg, pos)

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
            if header.hold:
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

    def get_clickedimg(self, rect=None):
        if not rect:
            rect = self.rect

        size = (rect.w * 9 / 10, rect.h * 9 / 10)
        negaimg = self.get_negaimg()
        return pygame.transform.scale(negaimg, size)

    def get_wxclickedbmp(self):
        image = self.get_clickedimg()
        return conv2wxbmp(image)

    def get_cardwxbmp(self, header):
        image = self.get_cardimg(header)
        return conv2wxbmp(image)

    def update(self, card):
        pass

class LargeCardImage(CardImage):
    def __init__(self, path, bgtype, name="", premium=""):
        CardImage.__init__(self, path, "LARGE", name, premium)

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

        subimg = cw.s((cw.util.load_image(self.path, True), cw.SIZE_CARDIMAGE))
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
    def __init__(self, ccard, pos=(0, 0)):
        self.ccard = ccard
        self._pos_noscale = cw.ds(pos)
        self.update_scale()

    def update_scale(self):
        # カード画像
        self.set_faceimg(self.ccard.imgpath)
        # フォント画像(カード名)
        self.set_nameimg(self.ccard.name)
        # フォント画像(レベル)
        self.set_levelimg(self.ccard.level)
        # ライフバー画像
        self.lifeimg = pygame.Surface(cw.s((79, 13))).convert()
        self.lifeguage = cw.cwpy.rsrc.statuses["LIFEGUAGE"]
        self.lifebar = cw.cwpy.rsrc.statuses["LIFEBAR"]
        self.lifeimg.set_colorkey(self.lifeguage.get_at((0, 0)), RLEACCEL)
        # rect
        self.rect = pygame.Rect(cw.s(self._pos_noscale), cw.s((95, 130)))

    def set_faceimg(self, path):
        self.path = path
        self.cardimg = cw.s((cw.util.load_image(path, True), cw.SIZE_CARDIMAGE))

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
        size = (cw.s(15 * (len(s)-1) + 20), font.size(s)[1])
        self.levelimg = pygame.Surface(size, SRCALPHA).convert_alpha()

        for index, char in enumerate(s):
            subimg = font.render(char, True, (0, 0, 0))
            self.levelimg.blit(subimg, cw.s((15 * index, 0)))

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
            lifeper = ccard.get_lifeper()
            self.lifeimg.blit(self.lifebar, cw.s((int(0.79 * (lifeper - 100)), 1)))
            self.lifeimg.blit(self.lifeguage, cw.s((0, 0)))
            self.image.blit(self.lifeimg, cw.s((9, 111)))

        # ステータス画像追加
        self.update_statusimg(ccard)

        if header:
            # 適性表示(カード移動時)
            key = "HAND" + str(header.get_vocation_level(ccard))
            subimg = cw.cwpy.rsrc.stones[key]
            self.image.blit(subimg, cw.s((73, 95)))

    def update_statusimg(self, ccard):
        seq = []
        beastnum = ccard.has_beast()

        if beastnum: # 召喚獣所持(付帯召喚以外)
            image = cw.cwpy.rsrc.statuses["SUMMON"].copy()
            font = cw.cwpy.rsrc.fonts["statusimg"]
            pos = cw.s((8, 4))
            s = str(beastnum)
            subimg = font.render(s, False, (0, 0, 0))
            image.blit(subimg, (pos[0]+1, pos[1]))
            image.blit(subimg, (pos[0]-1, pos[1]))
            image.blit(subimg, (pos[0], pos[1]+1))
            image.blit(subimg, (pos[0], pos[1]-1))
            subimg = font.render(s, False, (255, 255, 255))
            image.blit(subimg, pos)
            seq.append(image)
        if ccard.is_poison(): # 中毒
            seq.append(cw.cwpy.rsrc.statuses["BODY0"])
        if ccard.is_confuse(): # 混乱
            seq.append(cw.cwpy.rsrc.statuses["MIND2"])
        elif ccard.is_overheat(): # 激昂
            seq.append(cw.cwpy.rsrc.statuses["MIND3"])
        elif ccard.is_brave(): # 勇敢
            seq.append(cw.cwpy.rsrc.statuses["MIND4"])
        elif ccard.is_panic(): # 恐慌
            seq.append(cw.cwpy.rsrc.statuses["MIND5"])
        if ccard.is_silence(): # 沈黙
            seq.append(cw.cwpy.rsrc.statuses["MAGIC1"])
        if ccard.is_faceup(): # 暴露
            seq.append(cw.cwpy.rsrc.statuses["MAGIC2"])
        if ccard.is_antimagic(): # 魔法無効化
            seq.append(cw.cwpy.rsrc.statuses["MAGIC3"])
        if ccard.enhance_act > 0: # 行動力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP0"], ccard.enhance_act)
        elif ccard.enhance_act < 0: # 行動力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN0"], ccard.enhance_act)
        if ccard.enhance_avo > 0: # 回避力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP1"], ccard.enhance_avo)
        elif ccard.enhance_avo < 0: # 回避力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN1"], ccard.enhance_avo)
        if ccard.enhance_res > 0: # 抵抗力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP2"], ccard.enhance_res)
        elif ccard.enhance_res < 0: # 抵抗力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN2"], ccard.enhance_res)
        if ccard.enhance_def > 0: # 防御力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP3"], ccard.enhance_def)
        elif ccard.enhance_def < 0: # 防御力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN3"], ccard.enhance_def)

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

    def _put_enhanceimg(self, seq, bmp, value):
        size = (bmp.get_width(), bmp.get_height())
        if value >= 7:
            seq.append((pygame.Color(175, 0, 0), size))
        elif value >= 4:
            seq.append((pygame.Color(127, 0, 0), size))
        elif value >= 1:
            seq.append((pygame.Color(79, 0, 0), size))
        elif value <= -7:
            seq.append((pygame.Color(0, 0, 85), size))
        elif value <= -4:
            seq.append((pygame.Color(0, 0, 160), size))
        elif value <= -1:
            seq.append((pygame.Color(0, 0, 187), size))
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
    w = cellsize[0]
    h = cellsize[1]
    wxbmp = wx.EmptyBitmap(w, h)
    wxdc = wx.MemoryDC(wxbmp)

    # mat
    ni = 1 if color[0] < 128 else -1
    back = (color[0]+ni, color[1], color[2])
    while color == back or bcolor == back:
        back = (back[0]+ni, back[1], back[2])

    wxdc.SetPen(wx.Pen(back, 1, wx.SOLID))
    wxdc.SetBrush(wx.Brush(back, wx.SOLID))
    wxdc.DrawRectangle(0, 0, w, h)

    # text
    pen, lineheight = set_textcellfont(wxdc, size, face, color, bold,
                                       italic, uline, vertical, False)
    lwidth = pen.GetWidth()

    lines = text.splitlines()
    if vertical:
        x = w - lineheight
        y = 0
        for line in lines:
            wxdc.DrawRotatedText(line, x, y, -90)
            if sline:
                lpos = x - (lineheight + lwidth) / 2
                wxdc.DrawLine(lpos, y, lpos, y + wxdc.GetTextExtent(line)[0])

            x -= lineheight
    else:
        x = 0
        y = 0
        for line in lines:
            wxdc.DrawText(line, x, y)
            if sline:
                lpos = y + (lineheight + lwidth) / 2
                wxdc.DrawLine(x, lpos, x + wxdc.GetTextExtent(line)[0], lpos)

            y += lineheight

    # border
    wxdc.SetPen(wx.Pen(bcolor, 1, wx.SOLID))
    wxdc.SetBrush(wx.Brush(bcolor, wx.SOLID))
    cw.imageretouch.add_border(wxdc, wxbmp, color, bwidth)

    wxdc.SelectObject(wx.NullBitmap)
    wxbmp.SetMaskColour(back)

    return conv2surface(wxbmp)

def draw_textcell(image, rect, text, face, size, color,
        bold, italic, uline, sline, vertical, bcolor=None):
    """縁取りType2以外のテキストセルを描画する。
    """
    clip = rect.clip(pygame.Rect((0, 0), image.get_rect().size))
    xm = clip.x - rect.x
    ym = clip.y - rect.y
    if clip.width <= 0 or clip.height <= 0:
        return

    wxbmp = wx.EmptyBitmap(clip.width, clip.height)
    wxdc = wx.MemoryDC(wxbmp)
    wxdc.DrawBitmap(conv2wxbmp(image.subsurface(clip)), 0, 0)
    pen, lineheight = set_textcellfont(wxdc, size, face, color, bold,
                                       italic, uline, vertical, True)
    lwidth = pen.GetWidth()
    if bcolor:
        bpen = wx.Pen(bcolor, lwidth, wx.SOLID)
    lines = text.splitlines()
    if vertical:
        x = clip.width - xm
        y = -ym
        for line in lines:
            if bcolor:
                wxdc.SetPen(bpen)
                wxdc.SetTextForeground(bcolor)
                for xx in xrange(-1, 2):
                    for yy in xrange(-1, 2):
                        if xx == 0 and yy == 0:
                            continue
                        wxdc.DrawRotatedText(line, x+xx, y+yy, -90)
                        if sline:
                            lpos = x - (lineheight + lwidth) / 2
                            yto = y + wxdc.GetTextExtent(line)[0]
                            wxdc.DrawLine(lpos+xx, y+yy, lpos+xx, yto+yy)
                wxdc.SetPen(pen)
                wxdc.SetTextForeground(color)
            wxdc.DrawRotatedText(line, x, y, -90)
            if sline:
                lpos = x - (lineheight + lwidth) / 2
                yto = y + wxdc.GetTextExtent(line)[0]
                wxdc.DrawLine(lpos, y, lpos, yto)

            x -= lineheight
    else:
        x = -xm
        y = -ym
        for line in lines:
            if bcolor:
                wxdc.SetPen(bpen)
                wxdc.SetTextForeground(bcolor)
                for xx in xrange(-1, 2):
                    for yy in xrange(-1, 2):
                        if xx == 0 and yy == 0:
                            continue
                        wxdc.DrawText(line, x+xx, y+yy)
                        if sline:
                            lpos = y + (lineheight + lwidth) / 2
                            xto = x + wxdc.GetTextExtent(line)[0]
                            wxdc.DrawLine(x+xx, lpos+yy, xto+xx, lpos+yy)
                wxdc.SetPen(pen)
                wxdc.SetTextForeground(color)
            wxdc.DrawText(line, x, y)
            if sline:
                lpos = y + (lineheight + lwidth) / 2
                xto = x + wxdc.GetTextExtent(line)[0]
                wxdc.DrawLine(x, lpos, xto, lpos)

            y += lineheight

    wxdc.SelectObject(wx.NullBitmap)
    bmp = conv2surface(wxbmp)
    image.blit(bmp, clip.topleft)

def set_textcellfont(wxdc, size, face, color, bold, italic,
                     uline, vertical, antialiased):
    """テキストセル用のフォントをwxdcへセットし、
    (pen, lineheight)を返す。
    """
    family = wx.FONTFAMILY_DEFAULT
    style = wx.FONTSTYLE_NORMAL
    weight = wx.FONTWEIGHT_NORMAL
    encoding = wx.FONTFLAG_NOT_ANTIALIASED if antialiased else wx.FONTENCODING_DEFAULT
    if bold:
        weight = wx.FONTWEIGHT_BOLD
    if italic:
        style = wx.FONTSTYLE_ITALIC
    if vertical and not face.startswith("@"):
        face = "@" + face

    font = wx.Font(cw.s(12), family, style, weight, uline, face, encoding)
    font.SetPixelSize((0, size))
    wxdc.SetFont(font)
    te = wxdc.GetTextExtent("#")
    lwidth = max(1, size / 15)

    pen = wx.Pen(color, lwidth, wx.SOLID)
    wxdc.SetTextForeground(color)
    wxdc.SetPen(pen)
    return pen, te[1]

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
        l = min(mn, mx)
        r = max(mx, mn)
        c = r - l
        return min(255, max(0, int(l + c * per)))

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
            per = float(y) / h
            r = calc_per(color1[0], color2[0], per)
            g = calc_per(color1[1], color2[1], per)
            b = calc_per(color1[2], color2[2], per)
            a = calc_per(color1[3], color2[3], per)
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

def main():
    pass

if __name__ == "__main__":
    main()
