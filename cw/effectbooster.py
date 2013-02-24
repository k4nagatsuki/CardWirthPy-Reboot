#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import math

import wx
import pygame
from pygame.locals import *

import cw


def wait_effectbooster(waittime):
    if 0 < waittime:
        tick = pygame.time.get_ticks() + waittime
    else:
        tick = 0
        cw.util.change_cursor("mouse")

    try:
        eventhandler = cw.eventhandler.EventHandlerForEffectBooster()
        while cw.cwpy.is_running() and\
                (not tick or pygame.time.get_ticks() < tick) and\
                eventhandler.running and\
                cw.cwpy.is_playingscenario():
            cw.cwpy.sbargrp.update(cw.cwpy.scr)
            cw.cwpy.tick_clock()
            cw.cwpy.input()
            eventhandler.run()

    finally:
        if not tick:
            cw.util.change_cursor()

class _JpySubImage(cw.image.Image):
    def __init__(self, config, section, cache):
        self.configpath = config.path
        self.cache = cache
        # image load
        self.dirtype = config.get_int(section, "dirtype", 1)
        self.filename = config.get(section, "filename", "")
        self.smooth = config.get_bool(section, "smooth", False)
        self.clip = config.get_ints(section, "clip", 4, None)
        self.loadcache = config.get_int(section, "loadcache", 0)
        # image retouch
        self.flip = config.get_bool(section, "flip", False)
        self.mirror = config.get_bool(section, "mirror", False)
        self.turn = config.get_int(section, "turn", 0)
        self.mask = config.get_int(section, "mask", 0)
        self.colormap = config.get_int(section, "colormap", 0)
        self.alpha = config.get_int(section, "alpha", 0)
        self.exchange = config.get_int(section, "colorexchange", 0)
        self.noise = config.get_int(section, "noise", 0)
        self.noisepoint = config.get_int(section, "noisepoint", 0)
        self.filter = config.get_int(section, "filter", 0)
        # image temporary draw
        self.waittime = config.get_int(section, "wait", 0)
        self.animation = config.get_int(section, "animation", 0)
        self.animemove = config.get_ints(section, "animemove", 2, None)
        self.animeclip = config.get_ints(section, "animeclip", 4, None)
        self.animespeed = config.get_int(section, "animespeed", 0)
        self.animeposition = config.get_ints(section, "animeposition", 2, None)
        self.paintmode = config.get_int(section, "paintmode", 0)

    def draw2back(self, back):
        """背景に描画。"""
        if self.visible:
            image = self.get_image()

            if self.paintmode == 1:
                back.image.blit(image, self.position, None, BLEND_MIN)
            elif self.paintmode == 2:
                back.image.blit(image, self.position, None, BLEND_ADD)
            else:
                back.image.blit(image, self.position)

    def drawtemp(self, doanime):
        """一時描画。"""
        # 一時描画せずにウェイトだけ
        if self.animation == 4:
            if doanime:
                self.wait()
        # 一時描画
        elif self.animation:
            if self.animeposition:
                pos = self.animeposition
            elif self.animemove:
                pos = self.cache.load_position()
                pos = (pos[0] + self.animemove[0], pos[1] + self.animemove[1])
            else:
                pos = self.position

            animespeed = cw.util.numwrap(self.animespeed, 0, 255)

            # 単一描画
            if not animespeed:
                if doanime:
                    image = self.get_image()
                    image = self.clip_tempimg(image, pos)
                    spr = cw.sprite.background.Jpy1TemporalSprite(image, pos,
                                                                    self.paintmode)
                    cw.cwpy.draw()
                    self.wait()

                    if not self.animation == 1:
                        spr.remove(cw.cwpy.topgrp)

            # 連続描画
            else:
                if doanime:
                    goalpos = pos
                    pos = self.cache.load_position()
                    x, y = pos
                    rest_x = goalpos[0] - x
                    rest_y = goalpos[1] - y
                    xdir = bool(rest_x > -1)
                    ydir = bool(rest_y > -1)

                    while rest_x or rest_y:
                        n = math.sqrt(rest_x * rest_x + rest_y * rest_y)
                        n /= animespeed

                        if n == 0:
                            n = 1

                        if rest_x:
                            x = int(pos[0] + round(rest_x / n))
                            rest_x = goalpos[0] - x

                            if (rest_x < 0 and xdir) or (rest_x > 0 and not xdir):
                                x = goalpos[0]
                                rest_x = 0

                        if rest_y:
                            y = int(pos[1] + round(rest_y / n))
                            rest_y = goalpos[1] - y

                            if (rest_y < 0 and ydir) or (rest_y > 0 and not ydir):
                                y = goalpos[1]
                                rest_y = 0

                        pos = (x, y)
                        image = self.get_image()
                        image = self.clip_tempimg(image, pos)
                        spr = cw.sprite.background.Jpy1TemporalSprite(image, pos,
                                                                    self.paintmode)
                        cw.cwpy.draw()
                        self.wait()

                        if not self.animation == 1:
                            spr.remove(cw.cwpy.topgrp)

            self.cache.save_position(pos)

    def clip_tempimg(self, image, pos):
        if self.animeclip:
            size = image.get_size()
            x, y, w, h = self.animeclip
            rect = pygame.Rect(pos, size)
            rect2 = pygame.Rect((x, y), (w, h))

            if rect.colliderect(rect2):
                left = rect.left if rect.left > rect2.left else rect2.left
                top = rect.top if rect.top > rect2.top else rect2.top
                right = rect.right if rect.right < rect2.right else rect2.right
                bottom = rect.bottom if rect.bottom < rect2.bottom\
                                                            else rect2.bottom
                pos = (left - pos[0], top - pos[1])
                size = (right - left, bottom - top)
                rect = pygame.Rect(pos, size)
                subimg = image.subsurface(rect)
                image = pygame.Surface(image.get_size()).convert_alpha()
                image.fill((0, 0, 0, 0))
                image.blit(subimg, rect.topleft)
            else:
                image = pygame.Surface(image.get_size()).convert_alpha()
                image.fill((0, 0, 0, 0))

        return image

    def wait(self):
        # 指定時間だけ待機
        if self.waittime > 0:
            wait_effectbooster(self.waittime)

        # 右クリックするまで待機
        elif self.waittime < 0:
            wait_effectbooster(0)

    def retouch(self):
        """画像加工。"""
        image = self.get_image()

        # 画像がない場合、加工しない
        if image.get_size() == (0, 0):
            return

        # RGB入れ替え
        if self.exchange:
            if self.exchange == 1:
                image = cw.imageretouch.exchange_rgbcolor(image, "gbr")
            elif self.exchange == 2:
                image = cw.imageretouch.exchange_rgbcolor(image, "brg")
            elif self.exchange == 3:
                image = cw.imageretouch.exchange_rgbcolor(image, "grb")
            elif self.exchange == 4:
                image = cw.imageretouch.exchange_rgbcolor(image, "bgr")
            elif self.exchange == 5:
                image = cw.imageretouch.exchange_rgbcolor(image, "rbg")

        # フィルタ
        if self.filter:
            if self.filter == 1:
                image = cw.imageretouch.filter_shape(image)
            elif self.filter == 2:
                image = cw.imageretouch.filter_sharpness(image)
            elif self.filter == 3:
                image = cw.imageretouch.filter_sunpower(image)
            elif self.filter == 4:
                image = cw.imageretouch.filter_coloremboss(image)
            elif self.filter == 5:
                image = cw.imageretouch.filter_darkemboss(image)
            elif self.filter == 6:
                image = cw.imageretouch.filter_electrical(image)
            elif self.filter == 7:
                image = cw.imageretouch.to_binaryformat(image, 128)
            elif self.filter == 8:
                image = cw.imageretouch.spread_pixels(image)
            elif self.filter == 9:
                image = cw.imageretouch.to_negative(image)
            elif self.filter == 10:
                image = cw.imageretouch.filter_emboss(image)

        # 色調変化
        if self.colormap:
            if self.colormap == 1:      # グレイスケール
                image = cw.imageretouch.to_grayscale(image)
            elif self.colormap == 2:    # セピア
                image = cw.imageretouch.to_sepiatone(image, (30, 0, -30))
            elif self.colormap == 3:    # ピンク
                image = cw.imageretouch.to_sepiatone(image, (255, 0, 30))
            elif self.colormap == 4:    # サニィレッド
                image = cw.imageretouch.to_sepiatone(image, (255, 0, 0))
            elif self.colormap == 5:    # リーフグリーン
                image = cw.imageretouch.to_sepiatone(image, (0, 255, 0))
            elif self.colormap == 6:    # オーシャンブルー
                image = cw.imageretouch.to_sepiatone(image, (0, 0, 255))
            elif self.colormap == 7:    # ライトニング
                image = cw.imageretouch.to_sepiatone(image, (191, 191, 0))
            elif self.colormap == 8:    # パープルライト
                image = cw.imageretouch.to_sepiatone(image, (191, 0, 191))
            elif self.colormap == 9:    # アクアライト
                image = cw.imageretouch.to_sepiatone(image, (0, 191, 191))
            elif self.colormap == 10:   # クリムゾン
                image = cw.imageretouch.to_sepiatone(image, (0, -255, -255))
            elif self.colormap == 11:   # ダークグリーン
                image = cw.imageretouch.to_sepiatone(image, (-255, 0, -255))
            elif self.colormap == 12:   # ダークブルー
                image = cw.imageretouch.to_sepiatone(image, (-255, -255, 0))
            elif self.colormap == 13:   # スワンプ
                image = cw.imageretouch.to_sepiatone(image, (0, 0, -255))
            elif self.colormap == 14:   # ダークパープル
                image = cw.imageretouch.to_sepiatone(image, (0, -255, 0))
            elif self.colormap == 15:   # ダークスカイ
                image = cw.imageretouch.to_sepiatone(image, (-255, 0, 0))

        # 反転
        if self.mirror or self.flip:
            image = pygame.transform.flip(image, self.mirror, self.flip)

        # ノイズ
        if self.noise:
            if self.noise == 1:
                image = cw.imageretouch.add_lightness(image, self.noisepoint)
            elif self.noise == 2:
                image = cw.imageretouch.to_binaryformat(image, self.noisepoint)
            elif self.noise == 3:
                image = cw.imageretouch.add_noise(image, self.noisepoint)
            elif self.noise == 4:
                image = cw.imageretouch.add_noise(image, self.noisepoint, True)
            elif self.noise == 5:
                image = cw.imageretouch.add_mosaic(image, self.noisepoint)

        # 回転
        if self.turn:
            if self.turn == 1:
                image = pygame.transform.rotate(image, 270)
            elif self.turn == 2:
                image = pygame.transform.rotate(image, 90)

        # 切り取り
        if self.clip:
            x, y, w, h = self.clip
            rect = pygame.Rect((x, y), (w, h))

            try:
                image = image.subsurface(rect)
            except:
                w = image.get_width() if image.get_width() > w + x else w + x
                h = image.get_height() if image.get_height() > h + y else h + y
                image = pygame.transform.scale(image, (w, h))
                image = image.subsurface(rect)

        # リサイズ for JpyPartsImage
        if not hasattr(self, "backcolor"):
            width = self.width if self.width > 0 else image.get_width()
            height = self.height if self.height > 0 else image.get_height()
            size = (width, height)

            if not size == image.get_size() and not size == (0, 0):
                if self.smooth:
                    image = pygame.transform.smoothscale(image, size)
                else:
                    image = pygame.transform.scale(image, size)

        # マスク
        if self.transparent:
            image.set_colorkey(image.get_at((0, 0)), RLEACCEL)

        # 透過ライン
        if self.mask:
            if self.mask == 1:
                image = cw.imageretouch.add_transparentline(image, True, False)
            elif self.mask == 2:
                image = cw.imageretouch.add_transparentline(image, False, True)
            elif self.mask == 3:
                image = cw.imageretouch.add_transparentline(image, True, True)

        # 透明度
        if self.paintmode == 3:
            image.set_alpha(self.alpha)

        # キャッシュ (for JpyPartsImage)
        if 1 <= self.savecache <= 8:
            self.cache.save_image(self.savecache, image)

        self.image = image

    def load(self):
        """画像作成。"""
        path = self.get_filepath()

        # ファイル読み込み
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()

            # 効果音ファイル
            if ext in cw.EXTS_SND:
                sound = cw.util.load_sound(path)

                if sound:
                    sound.play()

                image = pygame.Surface((0, 0)).convert()
            # Jpy1ファイル
            elif ext == ".jpy1":
                image = JpyImage(path, self.cache).get_image()
            # Jpdcファイル
            elif ext == ".jpdc":
                image = JpdcImage(self.transparent, path).get_image()
            # Jptxファイル
            elif ext == ".jptx":
                image = JptxImage(path, self.transparent).get_image()
            # その他画像ファイル
            else:
                image = cw.util.load_image(path, self.transparent)

        # 画像キャッシュから読み込み
        elif 1 <= self.loadcache <= 8:
            image = self.cache.load_image(self.loadcache)
        # 背景画像作成 for JpyBackgroundImage
        elif hasattr(self, "backcolor"):
            width = self.width if self.width > 0 else cw.SIZE_AREA[0]
            height = self.height if self.height > 0 else cw.SIZE_AREA[1]
            size = (width, height)
            image = pygame.Surface(size).convert()
            image.fill(self.backcolor)
        # 画像なし
        else:
            image = pygame.Surface((0, 0)).convert()

        # リサイズ for JpyBackgroundImage
        if hasattr(self, "backcolor"):
            width = self.width if self.width > 0 else cw.SIZE_AREA[0]
            height = self.height if self.height > 0 else cw.SIZE_AREA[1]
            size = (width, height)

            if not size == image.get_size():
                if self.smooth:
                    image = pygame.transform.smoothscale(image, size)
                else:
                    image = pygame.transform.scale(image, size)

        self.image = image

    def get_filepath(self):
        """読み込むファイルのパスを取得する。"""
        if self.filename:
            filename = self.filename
        else:
            return ""

        if self.dirtype == 1:
            dpath = os.path.dirname(self.configpath)
        elif self.dirtype == 2:
            dpath = cw.util.join_paths(cw.cwpy.skindir, "Table")
            filename = os.path.splitext(filename)[0] + cw.cwpy.rsrc.ext_img
        elif self.dirtype == 3:
            dpath = "Data/EffectBooster"
        elif self.dirtype == 4:
            if cw.cwpy.classicdata:
                dpath = cw.util.join_paths(cw.cwpy.sdata.scedir)
            else:
                dpath = cw.util.join_paths(cw.cwpy.sdata.scedir, "Material")
            # シナリオ内に存在しなかった場合はTableを探す
            if not os.path.isfile(cw.util.join_paths(dpath, filename)):
                dpath = cw.util.join_paths(cw.cwpy.skindir, "Table")
                filename = os.path.splitext(filename)[0] + cw.cwpy.rsrc.ext_img
        elif self.dirtype == 5:
            dpath = cw.util.join_paths(cw.cwpy.skindir, "Sound")
            filename = os.path.splitext(filename)[0] + cw.cwpy.rsrc.ext_snd
        elif self.dirtype == 6:
            dpath = os.path.dirname(os.path.dirname(self.configpath))
        elif self.dirtype == 7:
            dpath = ""
        else:
            dpath = os.path.dirname(self.configpath)

        return cw.util.join_paths(dpath, filename)

class JpyPartsImage(_JpySubImage):
    def __init__(self, config, section, cache):
        _JpySubImage.__init__(self, config, section, cache)
        self.height = config.get_int(section, "height", -1)
        self.width = config.get_int(section, "width", -1)
        self.position = config.get_ints(section, "position", 2, (0, 0))
        self.savecache = config.get_int(section, "savecache", 0)
        self.visible = config.get_bool(section, "visible", True)
        self.transparent = config.get_bool(section, "transparent", True)

class JpyBackGroundImage(_JpySubImage):
    def __init__(self, config, cache):
        _JpySubImage.__init__(self, config, "init", cache)
        self.backcolor = config.get_color("init", "backcolor", (255, 255, 255))
        self.width = config.get_int("init", "backwidth", -1)
        self.height = config.get_int("init", "backheight", -1)
        self.transparent = config.get_bool("init", "transparent", False)
        self.position = (0, 0)
        self.savecache = 0
        self.visible = False

class JpyImage(cw.image.Image):
    def __init__(self, path, mask=False, cache=None, doanime=True):
        if not cache:
            cache = JpyCache()

        config = EffectBoosterConfig(path)
        back = JpyBackGroundImage(config, cache)
        back.load()

        for section in config.sections():
            if not section == "init":
                parts = JpyPartsImage(config, section, cache)
                parts.load()
                parts.retouch()
                parts.drawtemp(doanime)
                parts.draw2back(back)

        back.retouch()
        back.drawtemp(doanime)
        self.image = back.get_image()
        if mask:
            self.image.set_colorkey(self.image.get_at((0, 0)))

class JpyCache(object):
    """Jpy1ファイル読み込み時に使うキャッシュ。
    最後に一時描画したポジションや、
    キャッシュした画像をセーブ・ロードする。
    """
    def save_position(self, pos):
        self.pos = pos

    def load_position(self):
        return getattr(self, "pos", (0, 0))

    def save_image(self, n, image):
        setattr(self, "img" + str(n), image)

    def load_image(self, n):
        image = getattr(self, "img" + str(n), None)

        if image:
            image = image.copy()
        else:
            image = pygame.Surface((0, 0)).convert()

        return image

class JpdcImage(cw.image.Image):
    def __init__(self, mask, path):
        config = EffectBoosterConfig(path)
        x, y, w, h = config.get_ints("jpdc:init", "clip", 4, (0, 0, 632, 420))
        rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface(cw.SIZE_AREA)
        copymode = config.get_int("jpdc:init", "copymode", 0)

        if not copymode:
            if cw.cwpy.topgrp.get_sprites_from_layer("jpytemporal"):
                copymode = 1
            else:
                copymode = 2

        if copymode == 3:
            self.image.fill((255, 255, 255))
        elif copymode == 2:
            cw.cwpy.bggrp.draw(self.image)
            cw.cwpy.mcardgrp.draw(self.image)
            cw.cwpy.pcardgrp.draw(self.image)
            cw.cwpy.topgrp.draw(self.image)
        else:
            cw.cwpy.bggrp.draw(self.image)
            cw.cwpy.mcardgrp.draw(self.image)
            cw.cwpy.pcardgrp.draw(self.image)

        self.image = self.image.subsurface(rect)

        if mask:
            self.image.set_colorkey(self.image.get_at((0, 0)), RLEACCEL)

        # 画像保存
        filename = config.get("jpdc:init", "savefilename", "")
        savecomment = config.get("jpdc:init", "savecomment", "")

        if filename and cw.cwpy.is_playingscenario():
            filename = cw.util.repl_dischar(filename)
            savecomment = savecomment.replace("%file%", filename)
            savecomment = savecomment.replace("%dir%", os.path.dirname(path))

            if savecomment:
                cw.cwpy.set_titlebar(savecomment)
            else:
                cw.cwpy.set_titlebar(filename)

            path = cw.util.join_paths(os.path.dirname(path), filename)
            encoding = sys.getfilesystemencoding()
            pygame.image.save(self.image, path.encode(encoding))
            self.wait()
            s = "%s %s - %s %s" % (cw.APP_NAME, cw.cwpy.setting.skinname,
                    os.path.basename(cw.cwpy.yadodir), cw.cwpy.sdata.name)
            cw.cwpy.set_titlebar(s)

    def wait(self):
        # 右クリックするまで待機
        cw.util.change_cursor("mouse")

        wait_effectbooster(0)

        cw.util.change_cursor()

class JptxImage(cw.image.Image):
    def __init__(self, path, mask):
        config = EffectBoosterConfig(path)
        # parameters
        backcolor = config.get_color("jptx:init", "backcolor", (0, 0, 0))
        backwidth = config.get_int("jptx:init", "backwidth", -1)
        backheight = config.get_int("jptx:init", "backheight", -1)
        autoline = config.get_bool("jptx:init", "autoline", True)
        lineheight = config.get_int("jptx:init", "lineheight", 100)
        fontpixels = config.get_int("jptx:init", "fontpixels", 12)
        fontcolor = config.get_color("jptx:init", "fontcolor", (255, 255, 255))
        fontface = config.get("jptx:init", "fontface", u"ＭＳ Ｐゴシック")
        antialias = config.get_bool("jptx:init", "antialias", False)
        fonttransparent = config.get_bool("jptx:init", "fonttransparent", False)
        text = config.get("jptx:begin", "jptx:end", "")

        if not autoline:
            text = text.replace("\n", "")

        text = re.sub(r"<[bB][rR]>", "\n", text)
        # image
        width = backwidth if backwidth > 0 else cw.SIZE_AREA[0]
        height = backheight if backheight > 0 else cw.SIZE_AREA[0]
        self.image = pygame.Surface((width, height)).convert()
        self.image.fill(backcolor)

        if mask:
            self.image.set_colorkey(self.image.get_at((0, 0)), RLEACCEL)

        if fonttransparent:
            fontcolor = backcolor

        # text rendering
        self.wxcanvas = wx.EmptyBitmap(10, 10)
        self.wxdc = wx.MemoryDC(self.wxcanvas)
        bold = False
        underline = False
        italic = False
        def create_font(fontface, fontpixels):
            if fontface in cw.cwpy.rsrc.fontnames.values():
                fontpath = self.get_fontpath(fontface)
                font = pygame.font.Font(fontpath, fontpixels)
            else:
                # pygameで描画できないフォント
                font = wx.Font(12,
                               wx.FONTFAMILY_DEFAULT,
                               wx.FONTSTYLE_NORMAL,
                               wx.FONTWEIGHT_NORMAL,
                               0,
                               fontface,
                               wx.FONTFLAG_NOT_ANTIALIASED)
                font.SetPixelSize((0, fontpixels))
                self.wxdc.SetFont(font)
                size = self.wxdc.GetTextExtent("##")
                self.wxcanvas = wx.EmptyBitmap(size[0] * 2, size[1] * 2)
                self.wxdc = wx.MemoryDC(self.wxcanvas)
                self.wxdc.SetFont(font)
            return font
        def set_bold(font, start):
            if isinstance(font, pygame.font.Font):
                font.set_bold(start)
            else:
                if start:
                    font.SetWeight(wx.FONTWEIGHT_BOLD)
                else:
                    font.SetWeight(wx.FONTWEIGHT_NORMAL)
                self.wxdc.SetFont(font)
        def set_underline(font, start):
            if isinstance(font, pygame.font.Font):
                font.set_underline(start)
            else:
                font.SetUnderlined(start)
                self.wxdc.SetFont(font)
        def set_italic(font, start):
            if isinstance(font, pygame.font.Font):
                font.set_italic(start)
            else:
                if start:
                    font.SetStyle(wx.FONTSTYLE_ITALIC)
                else:
                    font.SetStyle(wx.FONTSTYLE_NORMAL)
                self.wxdc.SetFont(font)
        def get_height(font):
            if isinstance(font, pygame.font.Font):
                return font.get_height()
            else:
                w, h, lh = self.wxdc.GetMultiLineTextExtent("#")
                return lh + 2
        def font_render(font, char, antialias, fontcolor):
            if isinstance(font, pygame.font.Font):
                subimg = font.render(char, antialias, fontcolor)
                return subimg, subimg.get_width()
            else:
                backcolor = (0, 0, 0)
                if fontcolor[:3] == backcolor:
                    backcolor = (255, 255, 255)
                self.wxdc.SetPen(wx.Pen(backcolor))
                self.wxdc.SetBrush(wx.Brush(backcolor))
                self.wxdc.DrawRectangle(0, 0, self.wxcanvas.Width, self.wxcanvas.Height)
                self.wxdc.SetTextForeground(fontcolor)
                self.wxdc.DrawText(char, 0, 0)
                image = cw.image.conv2surface(self.wxcanvas)
                image.set_colorkey(backcolor, RLEACCEL)
                return image, self.wxdc.GetTextExtent(char)[0]
        font = create_font(fontface, fontpixels)
        oldfonts = []
        x = 0
        y = 0
        w = 0
        h = 0
        shiftx = 0
        shifty = 0
        tag = ""
        nolinedata = True
        tagonly = True
        strike = False
        face_def = fontface
        pixels_def = fontpixels
        color_def = fontcolor

        for char in text:
            if char == "\n":
                x = 0 + shiftx
                if nolinedata or not tagonly:
                    y += get_height(font) * lineheight / 100 - 2 + shifty
                h = y
                nolinedata = True
                tagonly = True
            elif char == "<":
                nolinedata = False
                tag += char
            elif char == ">":
                nolinedata = False
                tag += char
                tag = tag.lower()
                start, name, attrs = self.parse_tag(tag)
                name = name.lower()

                if name == "b":
                    bold = start
                    set_bold(font, start)
                elif name == "u":
                    underline = start
                    set_underline(font, start)
                elif name == "i":
                    underline = start
                    set_italic(font, start)
                elif name == "s":
                    strike = start
                elif name == "shiftx":
                    n = int(attrs["shiftx"])
                    x += n
                    shiftx = n
                elif name == "shifty":
                    n = int(attrs["shifty"])
                    y += n
                    shifty = n
                elif name == "lineheight":
                    lineheight = int(attrs["lineheight"])
                # 本家エフェクトブースターは"<fontcolor="blue">"のようなタグを、
                # タグ名=font, 属性color=blueという用に認識してしまうため注意。
                elif name.startswith("font"):
                    if start:
                        oldfonts.append((fontface, fontpixels, fontcolor))
                        fontpixels = int(attrs.get("fontpixels", fontpixels))
                        fontpixels = int(attrs.get("pixels", fontpixels))
                        fontface = attrs.get("fontface", face_def)
                        fontface = attrs.get("face", fontface)
                        font = create_font(fontface, fontpixels)
                        color = attrs.get("fontcolor")
                        color = attrs.get("color", color)
                        if color:
                            fontcolor = self.get_fontcolor(color, color_def)
                    else:
                        fontface, fontpixels, color = oldfonts.pop()
                        font = create_font(fontface, fontpixels)
                        fontcolor = color
                    set_bold(font, bold)
                    set_italic(font, italic)
                    set_underline(font, underline)

                tag = ""
            elif tag:
                tag += char
            else:
                nolinedata = False
                tagonly = False
                subimg, width = font_render(font, char, antialias, fontcolor)

                # 取消線
                if strike:
                    subimg2, width = font_render(font, u"―", antialias, fontcolor)
                    size = (subimg.get_width() + 10, get_height(font))
                    subimg2 = pygame.transform.scale(subimg2, size)
                    subimg.blit(subimg2, (-5, 0))

                self.image.blit(subimg, (x, y))
                x += width
                w = x if x > w else w

        if backheight < 0 or backwidth < 0:
            w = w if backwidth < 0 else backwidth
            h = h if backheight < 0 else backheight
            self.image = self.image.subsurface(pygame.Rect(0, 0, w, h))

        self.wxcanvas = None
        self.wxdc = None

    def get_fontpath(self, fontface):
        if fontface in (u"ＭＳ Ｐゴシック", "MS PGothic"):
            return cw.cwpy.rsrc.fontpaths["pgothic"]
        elif fontface in (u"ＭＳ Ｐ明朝", "MS PMincho"):
            return cw.cwpy.rsrc.fontpaths["pmincho"]
        elif fontface in (u"ＭＳ ゴシック", "MS Gothic"):
            return cw.cwpy.rsrc.fontpaths["gothic"]
        elif fontface in (u"ＭＳ 明朝", "MS Mincho"):
            return cw.cwpy.rsrc.fontpaths["mincho"]
        elif fontface in (u"ＭＳ ＵＩゴシック", "MS UI Gothic"):
            return cw.cwpy.rsrc.fontpaths["uigothic"]
        else:
            return cw.cwpy.rsrc.fontpaths["pgothic"]

    def get_fontcolor(self, fontcolor, default=(0, 0, 0)):
        if not fontcolor:
            return default

        fontcolor = fontcolor.strip()
        if fontcolor == "red":
            return (255, 0, 0)
        elif fontcolor == "yellow":
            return (255, 255, 0)
        elif fontcolor == "blue":
            return (0, 0, 255)
        elif fontcolor == "green":
            return (0, 128, 0)
        elif fontcolor == "white":
            return (255, 255, 255)
        elif fontcolor == "black":
            return (0, 0, 0)
        elif fontcolor == "lime":
            return (0, 255, 0)
        elif fontcolor == "aqua":
            return (0, 255, 255)
        elif fontcolor == "fuchsia":
            return (255, 0, 255)
        elif fontcolor == "maroon":
            return (128, 0, 0)
        elif fontcolor == "olive":
            return (128, 128, 0)
        elif fontcolor == "teal":
            return (0, 128, 128)
        elif fontcolor == "navy":
            return (0, 0, 128)
        elif fontcolor == "purple":
            return (128, 0, 128)
        elif fontcolor == "gray":
            return (128, 128, 128)
        elif fontcolor == "silver":
            return (192, 192, 192)
        elif fontcolor.startswith("$") and len(fontcolor) == 7:
            r = int(fontcolor[1:3], 16)
            g = int(fontcolor[3:5], 16)
            b = int(fontcolor[5:7], 16)
            return (r, g, b)
        elif fontcolor:
            try:
                value = int(fontcolor, 16)
                r = (value >> 16) & 0xff
                g = (value >> 8) & 0xff
                b = (value >> 0) & 0xff
                return (r, g, b)
            except:
                return default
        else:
            return default

    def parse_tag(self, tag):
        """HTMLタグをパースして、
        (スタートタグか否か, タグ名, 属性の辞書)のタプルを返す。
        """
        tag = tag.strip("<> ")
        # タグの名前
        m = re.match(r"^/?\s*[^\s=]+", tag)
        name = m.group().strip() if m else ""

        if name.startswith("/"):
            name = name.replace("/", "").strip()
            start = False
        else:
            start = True

        # タグの属性(辞書)
        groups = re.findall(r"[^\s=]+\s*=\s*[^\s=]+", tag)
        attrs = {}

        for group in groups:
            key, value = group.split("=")
            attrs[key.strip()] = value.strip(" \"\'")

        return start, name, attrs

class EffectBoosterConfig(object):
    def __init__(self, path):
        self.path = path
        r_sec = re.compile(r'\[([^]]+)\]')
        r_opt = re.compile(r'([^:=\s][^:=]*)\s*[:=]\s*(.*)$')
        self._orderedsecs = []
        self._sections = {}
        cur_sec = {}
        jptxtxt = []
        f = open(path, "rb")

        for line in f:
            if line[0] in '#;':
                continue

            line = line.decode("mbcs").replace("\r\n", "\n")

            # jptxテキスト
            if line == "[jptx:end]\n" or line == "[jptx:end]":
                break
            elif line == "[jptx:begin]\n":
                jptxtxt.append("")
                continue
            elif jptxtxt:
                jptxtxt.append(line)
                continue

            # セクション
            m = r_sec.match(line)

            if m:
                sec = m.group(1).strip()
                cur_sec = {}
                self._sections[sec] = cur_sec
                self._orderedsecs.append(sec)
                continue

            # オプション
            m = r_opt.match(line)

            if m:
                opt = m.group(1).strip().lower()
                val = m.group(2).strip()
                cur_sec[opt] = val
                continue

        f.close()

        if jptxtxt:
            self._sections["jptx:begin"] = {"jptx:end": "".join(jptxtxt)}

    def sections(self):
        return self._orderedsecs

    def get(self, section, option, default=None):
        sec = self._sections.get(section, None)

        if sec:
            return sec.get(option.lower(), default)
        else:
            return default

    def get_int(self, section, option, default=None):
        try:
            value = self.get(section, option, default).strip()
            if value.endswith("px"):
                return int(value[:-2])
            return int(value)
        except:
            return default

    def get_bool(self, section, option, default=None):
        return bool(self.get_int(section, option, default))

    def get_color(self, section, option, default=None):
        try:
            s = self.get(section, option, default)
            r = int(s[1:3], 16)
            g = int(s[3:5], 16)
            b = int(s[5:7], 16)
            return (r, g, b)
        except:
            return default

    def get_ints(self, section, option, length, default=None):
        try:
            s = self.get(section, option, default)
            seq = [int(i.strip()) for i in s.split(",")]

            if len(seq) == length:
                return tuple(seq)
            else:
                raise ValueError()

        except:
            return default

def main():
    pass

if __name__ == "__main__":
    main()

