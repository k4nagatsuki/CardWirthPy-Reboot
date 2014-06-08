#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import math

import pygame
from pygame.locals import *

import cw


class ScreenRescale(Exception):
    pass

def wait_effectbooster(waittime):
    if 0 < waittime:
        tick = pygame.time.get_ticks() + waittime
    else:
        tick = 0
        cw.util.change_cursor("mouse")

    try:
        eventhandler = cw.eventhandler.EventHandlerForEffectBooster()
        cw.cwpy.clear_selection()
        while cw.cwpy.is_running() and\
                (not tick or pygame.time.get_ticks() < tick) and\
                eventhandler.running and\
                cw.cwpy.is_playingscenario():
            cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
            cw.cwpy.tick_clock(1000)
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
        self.clip = cw.s(config.get_ints(section, "clip", 4, None))
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
        self.animemove = cw.s(config.get_ints(section, "animemove", 2, None))
        self.animeclip = cw.s(config.get_ints(section, "animeclip", 4, None))
        self.animespeed = config.get_int(section, "animespeed", 0)
        self.animeposition = cw.s(config.get_ints(section, "animeposition", 2, None))
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
            if self.animeposition and self.animemove:
                pos = self.animeposition
                pos = (pos[0] + self.animemove[0], pos[1] + self.animemove[1])
            elif self.animeposition:
                pos = self.animeposition
            elif self.animemove:
                pos = self.cache.load_position()
                pos = (pos[0] + self.animemove[0], pos[1] + self.animemove[1])
            else:
                pos = self.position

            animespeed = cw.util.numwrap(self.animespeed, 0, 255)

            # 単一描画
            sprs = cw.cwpy.topgrp.get_sprites_from_layer("jpytemporal")
            if sprs:
                background = sprs[0].image
            else:
                background = cw.cwpy.background.image.copy()

                # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
                if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
                    cards = cw.cwpy.pcardgrp.sprites() + cw.cwpy.mcardgrp.sprites()
                else:
                    cards = cw.cwpy.mcardgrp.sprites() + cw.cwpy.pcardgrp.sprites()

                for card in cards:
                    if card.status <> "hidden":
                        background.blit(card.image, card.rect.topleft)
                cw.sprite.background.Jpy1TemporalSprite(background)

            if not animespeed:
                if doanime:
                    self._drawtemp_impl(background, pos)

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
                        n /= cw.UP_SCR

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
                        self._drawtemp_impl(background, pos, anime=True)

            self.cache.save_position(pos)

    def _drawtemp_impl(self, background, pos, redraw=True, anime=False):
        """backgroundのposの位置に一時描画。"""
        image = self.get_image()
        image = self.clip_tempimg(image, pos)

        rect = pygame.Rect(pos, image.get_size())
        rect = rect.clip(background.get_rect())

        if self.paintmode == 1:
            blendmode = BLEND_MIN
        elif self.paintmode == 2:
            blendmode = BLEND_ADD
        else:
            blendmode = 0

        if 0 < rect[2] and 0 < rect[3]:
            if redraw:
                if not self.animation == 1:
                    before = background.subsurface(rect).copy()

                background.blit(image, pos, special_flags=blendmode)
                cw.cwpy.draw()

                if not self.animation == 1:
                    background.blit(before, rect.topleft)
            else:
                if self.animation == 1:
                    background.blit(image, pos, special_flags=blendmode)
                    cw.cwpy.draw()

            self.wait(anime=anime)

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

    def wait(self, anime=False):
        # 指定時間だけ待機
        if self.waittime > 0:
            if anime:
                wait_effectbooster(max(1, self.waittime / cw.UP_SCR))
            else:
                wait_effectbooster(self.waittime)

        # 右クリックするまで待機
        elif self.waittime < 0:
            wait_effectbooster(0)

    def retouch(self):
        """画像加工。"""
        image = self.get_image()

        # 画像がない場合、加工しない
        if image.get_size() == cw.s((0, 0)):
            # キャッシュ (for JpyPartsImage)
            if 1 <= self.savecache <= 8:
                self.cache.save_image(self.savecache, image)
            return

        # マスク
        if self.transparent:
            colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, RLEACCEL)
            image = image.convert_alpha()
            image.set_colorkey(colorkey, RLEACCEL)
        else:
            colorkey = None
            image.set_colorkey(None)

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
                image = cw.imageretouch.to_binaryformat(image, -1, image.get_at((0, 0))[:3])
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

            if pygame.Rect((0, 0), image.get_size()).contains(rect):
                image = image.subsurface(rect)
            else:
                w = image.get_width() if image.get_width() > w + x else w + x
                h = image.get_height() if image.get_height() > h + y else h + y
                image = pygame.transform.scale(image, (w, h))
                image = image.subsurface(rect)

        # リサイズ for JpyPartsImage
        if not hasattr(self, "backcolor"):
            width = self.width if self.width > 0 else image.get_width()
            height = self.height if self.height > 0 else image.get_height()
            size = (width, height)

            if not size == image.get_size() and not size == cw.s((0, 0)):
                if self.smooth:
                    image = pygame.transform.smoothscale(image, size)
                else:
                    image = pygame.transform.scale(image, size)

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
            if image.get_flags() & pygame.locals.SRCALPHA:
                image.fill((0, 0, 0, 255 - self.alpha), special_flags=pygame.locals.BLEND_RGBA_SUB)
            else:
                image.set_alpha(self.alpha)

        # キャッシュ (for JpyPartsImage)
        if 1 <= self.savecache <= 8:
            self.cache.save_image(self.savecache, image)

        self.image = image

    def load(self, doanime):
        """画像作成。"""
        path = self.get_filepath()
        ext = cw.util.splitext(path)[1].lower()

        # ファイル読み込み
        if os.path.isfile(path):
            image = None
            mtime = 0
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)

            cachekey = (_JpySubImage, cw.UP_SCR, False, path)

            if cw.cwpy.is_playingscenario() and cachekey in cw.cwpy.sdata.cache:
                image, cachemtime = cw.cwpy.sdata.cache[cachekey]
                if cachemtime < mtime:
                    image = None

            if image is None:
    
                # 効果音ファイル
                if ext in cw.EXTS_SND:
                    if doanime:
                        sound = cw.util.load_sound(path)
    
                        if sound:
                            sound.play(True)
    
                    image = pygame.Surface((0, 0)).convert()
                # Jpy1ファイル
                elif ext == ".jpy1":
                    image = JpyImage(path, cache=self.cache, doanime=doanime, mask=False).get_image()
                    # 変化するためキャッシュ不可
                # Jpdcファイル
                elif ext == ".jpdc":
                    image = JpdcImage(False, path).get_image()
                    # 重くならないのでキャッシュ不要
                # Jptxファイル
                elif ext == ".jptx":
                    image = JptxImage(path, False).get_image()
                    cw.cwpy.sdata.cache[cachekey] = (image.copy(), mtime)
                # その他画像ファイル
                else:
                    image = cw.s(cw.util.load_image(path, False))

        # 画像キャッシュから読み込み
        elif 1 <= self.loadcache <= 8:
            image = self.cache.load_image(self.loadcache)
        # 背景画像作成 for JpyBackgroundImage
        elif hasattr(self, "backcolor"):
            width = self.width if self.width > cw.s(0) else cw.s(cw.SIZE_AREA[0])
            height = self.height if self.height > cw.s(0) else cw.s(cw.SIZE_AREA[1])
            size = (width, height)
            image = pygame.Surface(size).convert()
            image.fill(self.backcolor)
        # 背景画像作成 for JpyPartsImage
        elif not hasattr(self, "backcolor") and -1 < self.height and -1 < self.width:
            width = self.width if self.width > cw.s(0) else cw.s(cw.SIZE_AREA[0])
            height = self.height if self.height > cw.s(0) else cw.s(cw.SIZE_AREA[1])
            size = (width, height)
            image = pygame.Surface(size).convert()
            image.fill(self.color)
        # 画像なし
        else:
            image = pygame.Surface((0, 0)).convert()

        # リサイズ for JpyBackgroundImage
        if hasattr(self, "backcolor"):
            imagesize = image.get_size()
            if self.width >= cw.s(0):
                width = self.width
            elif 0 < imagesize[0]:
                width = imagesize[0]
            else:
                width = cw.s(cw.SIZE_AREA[0])
            if self.height >= cw.s(0):
                height = self.height
            elif 0 < imagesize[1]:
                height = imagesize[1]
            else:
                height = cw.s(cw.SIZE_AREA[1])
            size = (width, height)

            if not size == image.get_size():
                if image.get_width() == 0 or image.get_height() == 0:
                    image = pygame.Surface(size).convert()
                elif self.smooth:
                    image = pygame.transform.smoothscale(image, size)
                else:
                    image = pygame.transform.scale(image, size)

        self.image = image

    def get_filepath(self, dirtype=-1):
        """読み込むファイルのパスを取得する。"""
        if self.filename:
            if dirtype == -1:
                dirtype = self.dirtype
            return get_filepath_s(self.configpath, self.filename, dirtype)
        else:
            return ""

def get_filepath_s(configpath, filename, dirtype=-1):
    """dirtypeに基づいて読み込むファイルのパスを取得する。"""
    if dirtype == -1:
        dirtype = 1

    if dirtype == 1:
        dpath = os.path.dirname(configpath)
        # シナリオ内に存在しなかった場合はTable内
        if not os.path.isfile(cw.cwpy.rsrc.get_filepath(cw.util.join_paths(dpath, filename))):
            return get_filepath_s(configpath, filename, 2)
    elif dirtype == 2:
        dpath = cw.util.join_paths(cw.cwpy.skindir, "Table")
        filename = cw.util.splitext(filename)[0] + cw.cwpy.rsrc.ext_img
    elif dirtype == 3:
        dpath = "Data/EffectBooster"
    elif dirtype == 4:
        if cw.cwpy.is_runningevent() and cw.cwpy.event.get_inusecard():
            inusecard = cw.cwpy.event.get_inusecard()
            if not inusecard.carddata.getbool(".", "scenariocard", False):
                e_mates = inusecard.carddata.find("Property/Materials")
                if not e_mates is None:
                    fpath = cw.util.join_paths(e_mates.text, filename)
                    fpath = cw.util.join_yadodir(fpath)
                    if os.path.isfile(fpath):
                        return fpath

        if cw.cwpy.classicdata:
            dpath = cw.util.join_paths(cw.cwpy.sdata.scedir)
        else:
            dpath = cw.util.join_paths(cw.cwpy.sdata.scedir, "Material")
        # 指定位置に存在しなかった場合は相対位置
        if not os.path.isfile(cw.util.join_paths(dpath, filename)):
            return get_filepath_s(configpath, filename, 1)
    elif dirtype == 5:
        dpath = cw.util.join_paths(cw.cwpy.skindir, "Sound")
        filename = cw.util.splitext(filename)[0] + cw.cwpy.rsrc.ext_snd
    elif dirtype == 6:
        dpath = os.path.dirname(os.path.dirname(configpath))
    elif dirtype == 7:
        dpath = ""
    else:
        dpath = os.path.dirname(configpath)

    path = cw.util.join_paths(os.path.normpath(cw.util.join_paths(dpath, filename)))
    path = cw.cwpy.rsrc.get_filepath(path)
    return path

class JpyPartsImage(_JpySubImage):
    def __init__(self, config, section, cache, mask):
        _JpySubImage.__init__(self, config, section, cache)
        self.height = cw.s(config.get_int(section, "height", -1))
        self.width = cw.s(config.get_int(section, "width", -1))
        self.color = config.get_color(section, "color", (0, 0, 0))
        self.position = cw.s(config.get_ints(section, "position", 2, (0, 0)))
        self.savecache = config.get_int(section, "savecache", 0)
        self.visible = config.get_bool(section, "visible", True)
        self.transparent = config.get_bool(section, "transparent", True)

class JpyBackGroundImage(_JpySubImage):
    def __init__(self, config, cache, mask):
        _JpySubImage.__init__(self, config, "init", cache)
        self.backcolor = config.get_color("init", "backcolor", (0, 0, 0))
        self.width = cw.s(config.get_int("init", "backwidth", -1))
        self.height = cw.s(config.get_int("init", "backheight", -1))
        self.transparent = config.get_bool("init", "transparent", False)
        self.position = cw.s((0, 0))
        self.savecache = 0
        self.visible = False

class JpyImage(cw.image.Image):
    def __init__(self, path, mask=False, cache=None, doanime=True):
        if not cache:
            cache = JpyCache()

        config = EffectBoosterConfig(path, "init")
        back = JpyBackGroundImage(config, cache, mask)
        back.load(doanime)

        for i, section in enumerate(config.sections()):
            if not section == "init":
                parts = JpyPartsImage(config, section, cache, mask)
                parts.load(doanime)
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
    def __init__(self):
        self.pos = None
        self.img = {}

    def save_position(self, pos):
        self.pos = pos

    def load_position(self):
        if self.pos:
            return self.pos
        else:
            return cw.s((0, 0))

    def save_image(self, n, image):
        self.img[n] = image

    def load_image(self, n):
        image = self.img.get(n, None)

        if image:
            image = image.copy()
        else:
            image = pygame.Surface(cw.s((0, 0))).convert()

        return image

class JpdcImage(cw.image.Image):
    def __init__(self, mask, path):
        config = EffectBoosterConfig(path, "jpdc:init")
        x_noscale, y_noscale, w_noscale, h_noscale = config.get_ints("jpdc:init", "clip", 4, (0, 0, 632, 420))
        x, y, w, h = cw.s((x_noscale, y_noscale, w_noscale, h_noscale))
        rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA))
        copymode = config.get_int("jpdc:init", "copymode", 0)

        if not copymode:
            if cw.cwpy.topgrp.get_sprites_from_layer("jpytemporal"):
                copymode = 1
            else:
                copymode = 2

        if copymode == 3:
            self.image.fill((255, 255, 255))
        else:
            cw.cwpy.bggrp.draw(self.image)
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
                cw.cwpy.pcardgrp.draw(self.image)
                cw.cwpy.mcardgrp.draw(self.image)
            else:
                cw.cwpy.mcardgrp.draw(self.image)
                cw.cwpy.pcardgrp.draw(self.image)
            if copymode == 2:
                cw.cwpy.topgrp.draw(self.image)

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

            saveimage = self.image
            if cw.UP_SCR <> 1:
                if cw.UP_SCR % 1 == 0:
                    saveimage = pygame.transform.scale(saveimage, (w_noscale, h_noscale))
                else:
                    saveimage = pygame.transform.smoothscale(saveimage, (w_noscale, h_noscale))

            path = cw.util.join_paths(os.path.dirname(path), filename)
            encoding = sys.getfilesystemencoding()
            pygame.image.save(saveimage, path.encode(encoding))
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
        config = EffectBoosterConfig(path, "jptx:init")
        # parameters
        backcolor = config.get_color("jptx:init", "backcolor", (0, 0, 0))
        backwidth = cw.s(config.get_int("jptx:init", "backwidth", -1))
        backheight = cw.s(config.get_int("jptx:init", "backheight", -1))
        autoline = config.get_bool("jptx:init", "autoline", True)
        lineheight = config.get_int("jptx:init", "lineheight", 100)
        fontpixels = cw.s(config.get_int("jptx:init", "fontpixels", 12))
        fontcolor = config.get_color("jptx:init", "fontcolor", (255, 255, 255))
        fontface = config.get("jptx:init", "fontface", u"ＭＳ Ｐゴシック")
        antialias = config.get_bool("jptx:init", "antialias", False)
        fonttransparent = config.get_bool("jptx:init", "fonttransparent", False)
        text = config.get("jptx:begin", "jptx:end", "")

        if not autoline:
            text = text.replace("\n", "")

        text = text.replace("\t", "")
        text = re.sub(r"<[bB][rR]>\n?", "\n", text)
        # image
        width = backwidth if backwidth > cw.s(0) else cw.s(cw.SIZE_AREA[0])
        height = backheight if backheight > cw.s(0) else cw.s(cw.SIZE_AREA[0])
        self.image = pygame.Surface((width, height)).convert()
        self.image.fill(backcolor)

        if mask:
            self.image.set_colorkey(self.image.get_at((0, 0)), RLEACCEL)

        if fonttransparent:
            fontcolor = backcolor

        # text rendering
        bold = False
        underline = False
        italic = False

        class Info(object):
            def __init__(self, outer, lineheight, fontface, fontpixels, fontcolor):
                self.outer = outer
                self.lineheight = lineheight
                self.fontpixels = fontpixels
                self.fontcolor = fontcolor
                self.fontface = fontface
                self.oldfonts = []
                self.x = 0
                self.y = 0
                self.y = 0
                self.w = 0
                self.h = 0
                self.tag = ""
                self.nolinedata = True
                self.tagonly = True
                self.strike = False
                self.create_font()
                self.chars = []

            def create_font(self):
                if self.fontface in cw.cwpy.rsrc.fontnames.values():
                    fontpath = self.outer.get_fontpath(self.fontface)
                    self.font = pygame.font.Font(fontpath, self.fontpixels)
                else:
                    if not self.fontface in cw.cwpy.rsrc.facenames:
                        self.fontface = self.outer.get_fontface(self.fontface)
                    self.font = cw.imageretouch.Font(self.fontface, self.fontpixels)

            def get_height(self):
                height = self.font.get_height()
                height += cw.s(2)
                return height

            def render(self):
                if not self.chars:
                    return
                chars = "".join(self.chars)
                self.chars = []
                subimg = info.font.render(chars, antialias, info.fontcolor)
                width = info.font.size(chars)[0]
                # 取消線
                if info.strike:
                    subimg2 = info.font.render(u"―", False, info.fontcolor)
                    size = (width + cw.s(10), info.get_height())
                    subimg2 = pygame.transform.scale(subimg2, size)
                    subimg.blit(subimg2, cw.s((-5, 0)))

                self.outer.image.blit(subimg, (info.x, info.y))
                info.x += width
                info.w = info.x if info.x > info.w else info.w

        info = Info(self, lineheight, fontface, fontpixels, fontcolor)
        face_def = fontface
        pixels_def = fontpixels
        color_def = fontcolor

        for char in text:
            if char == "\n":
                info.render()
                info.x = 0
                if info.nolinedata or not info.tagonly:
                    info.y += info.get_height() * info.lineheight / 100 - cw.s(2)
                info.h = info.y
                info.nolinedata = True
                info.tagonly = True
            elif char == "<":
                info.render()
                info.nolinedata = False
                info.tag += char
            elif char == ">":
                info.nolinedata = False
                info.tag += char
                info.tag = info.tag.lower()
                start, name, attrs = self.parse_tag(info.tag)
                name = name.lower()

                if name == "b":
                    bold = start
                    info.font.set_bold(start)
                elif name == "u":
                    underline = start
                    info.font.set_underline(start)
                elif name == "i":
                    underline = start
                    info.font.set_italic(start)
                elif name == "s":
                    info.strike = start
                elif name == "shiftx":
                    if start:
                        n = cw.s(int(attrs["shiftx"]))
                        info.x += n
                elif name == "shifty":
                    if start:
                        n = cw.s(int(attrs["shifty"]))
                        info.y += n
                elif name == "lineheight":
                    info.lineheight = int(attrs["lineheight"])
                # 本家エフェクトブースターは"<fontcolor="blue">"のようなタグを、
                # タグ名=font, 属性color=blueという用に認識してしまうため注意。
                elif name.startswith("font"):
                    if start:
                        info.oldfonts.append((info.fontface, info.fontpixels, info.fontcolor))
                        if "fontpixels" in attrs:
                            info.fontpixels = cw.s(int(attrs["fontpixels"]))
                        if "pixels" in attrs:
                            info.fontpixels = cw.s(int(attrs["pixels"]))
                        info.fontface = attrs.get("fontface", face_def)
                        info.fontface = attrs.get("face", info.fontface)
                        info.create_font()
                        color = attrs.get("fontcolor")
                        color = attrs.get("color", color)
                        if color:
                            info.fontcolor = self.get_fontcolor(color, color_def)
                    else:
                        info.fontface, info.fontpixels, color = info.oldfonts.pop()
                        info.create_font()
                        info.fontcolor = color
                    info.font.set_bold(bold)
                    info.font.set_italic(italic)
                    info.font.set_underline(underline)

                info.tag = ""
            elif info.tag:
                info.render()
                info.tag += char
            else:
                info.chars.append(char)
                info.nolinedata = False
                info.tagonly = False

        info.render()

        if backheight < 0 or backwidth < 0:
            info.w = info.w if backwidth < 0 else backwidth
            info.h = info.h if backheight < 0 else backheight
            rect = self.image.get_rect()
            self.image = self.image.subsurface(rect.clip(pygame.Rect(0, 0, info.w, info.h)))

    def get_fontface(self, fontface):
        if fontface in (u"ＭＳ Ｐゴシック", "MS PGothic"):
            return cw.cwpy.rsrc.fontnames["pgothic"]
        elif fontface in (u"ＭＳ Ｐ明朝", "MS PMincho"):
            return cw.cwpy.rsrc.fontnames["pmincho"]
        elif fontface in (u"ＭＳ ゴシック", "MS Gothic"):
            return cw.cwpy.rsrc.fontnames["gothic"]
        elif fontface in (u"ＭＳ 明朝", "MS Mincho"):
            return cw.cwpy.rsrc.fontnames["mincho"]
        elif fontface in (u"ＭＳ ＵＩゴシック", "MS UI Gothic"):
            return cw.cwpy.rsrc.fontnames["uigothic"]
        else:
            return fontface

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
            except ValueError:
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
    def __init__(self, path, firstsection):
        self.path = path
        r_sec = re.compile(r'\[([^]]+)\]')
        r_opt = re.compile(r'([^:=\s][^:=]*)\s*[:=]\s*(.*)$')
        self._orderedsecs = []
        self._sections = {}
        cur_sec = {}
        jptxtxt = []
        in_jptxtxt = False

        with open(path, "rb") as f:

            for line in f:
                if not in_jptxtxt and line[0] in '#;':
                    continue

                line = line.decode(cw.MBCS).replace("\r\n", "\n")

                # jptxテキスト
                if line == "[jptx:end]\n" or line == "[jptx:end]":
                    in_jptxtxt = False
                    break
                elif line == "[jptx:begin]\n":
                    in_jptxtxt = True
                    jptxtxt.append("")
                    continue
                elif in_jptxtxt:
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
                    if val.startswith('"') and val.startswith('"'):
                        val = val[1:-1]
                    cur_sec[opt] = val
                    continue

        if jptxtxt:
            self._sections["jptx:begin"] = {"jptx:end": "".join(jptxtxt)}

        if not self._sections and firstsection <> "":
            cur_sec = {}
            self._sections[firstsection] = cur_sec
            self._orderedsecs.append(firstsection)

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
            value = self.get(section, option, default)
            if value == default:
                return default
            value = value.strip()
            if value.endswith("px"):
                return int(value[:-2])
            return int(value)
        except ValueError:
            return default

    def get_bool(self, section, option, default=None):
        return bool(self.get_int(section, option, default))

    def get_color(self, section, option, default=None):
        # 仕様にはないがCardWirthの実装では次の名称が有効
        colortable = {
                       "black":   (0x00, 0x00, 0x00),
                       "maroon":  (0x80, 0x00, 0x00),
                       "green":   (0x00, 0x80, 0x00),
                       "olive":   (0x80, 0x80, 0x00),
                       "navy":    (0x00, 0x00, 0x80),
                       "purple":  (0x80, 0x00, 0x80),
                       "teal":    (0x00, 0x80, 0x80),
                       "gray":    (0x80, 0x80, 0x80),
                       "silver":  (0xC0, 0xC0, 0xC0),
                       "red":     (0xFF, 0x00, 0x00),
                       "lime":    (0x00, 0xFF, 0x00),
                       "yellow":  (0xFF, 0xFF, 0x00),
                       "blue":    (0x00, 0x00, 0xFF),
                       "fuchsia": (0xFF, 0x00, 0xFF),
                       "aqua":    (0x00, 0xFF, 0xFF),
                       "white":   (0xFF, 0xFF, 0xFF),
                      }
        try:
            s = self.get(section, option, default)
            if s == default:
                return default
            s = s.lower()
            if s in colortable:
                return colortable[s]
            r = int(s[1:3], 16)
            g = int(s[3:5], 16)
            b = int(s[5:7], 16)
            return (r, g, b)
        except ValueError:
            return default

    def get_ints(self, section, option, length, default=None):
        try:
            s = self.get(section, option, default)
            if s == default:
                return default
            seq = [int(i.strip()) for i in s.split(",")]

            if len(seq) == length:
                return tuple(seq)
            else:
                raise ValueError()

        except ValueError:
            return default

def main():
    pass

if __name__ == "__main__":
    main()

