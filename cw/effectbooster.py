#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import math

import pygame

import cw

import typing
from typing import Dict, List, Literal, Optional, Tuple, Type, Union


class ScreenRescale(Exception):
    pass


def wait_effectbooster(waittime: int, doanime: "AnimationCounter") -> None:
    if waittime:
        cw.cwpy.event.refresh_activeitem()
    if 0 < waittime:
        start_ticks = pygame.time.get_ticks() - doanime.time_elapsed
        stw = cw.sprite.base.StopTheWorld(start_ticks, waittime)
    else:
        cw.cwpy.change_cursor("mouse")

    try:
        doanime.time_elapsed = 0
        eventhandler = cw.eventhandler.EventHandlerForEffectBooster()
        ie = cw.cwpy.interrupt_eventhandler
        cw.cwpy.interrupt_eventhandler = eventhandler
        cw.cwpy.clear_selection()
        while cw.cwpy.is_running() and\
                (waittime <= 0 or stw.is_waiting()) and\
                eventhandler.running and\
                cw.cwpy.is_playingscenario():
            cw.cwpy.update_groups((cw.cwpy.sbargrp,))
            cw.cwpy.wait_frame(1, framerate=1000)
            cw.cwpy.input()
            eventhandler.run()
        if 0 < waittime:
            cw.cwpy.starttick = pygame.time.get_ticks()

        if not cw.cwpy.is_playingscenario():
            raise cw.event.EffectBreakError()

        doanime.time_elapsed = 0
    except ScreenRescale as ex:
        if 0 < waittime:
            doanime.time_elapsed = pygame.time.get_ticks() - start_ticks
        else:
            doanime.time_elapsed = 0
        raise ex
    finally:
        if waittime <= 0:
            cw.cwpy.change_cursor()
        cw.cwpy.interrupt_eventhandler = ie


class AnimationCounter(object):
    def __init__(self) -> None:
        self.count = 0
        self.skip_count = 0
        self.time_elapsed = 0
        self.all_cut = False

    def get_reloadcounter(self) -> "AnimationCounter":
        counter = AnimationCounter()
        counter.skip_count = self.count - 1
        counter.time_elapsed = self.time_elapsed
        return counter

    def countup(self) -> bool:
        self.count += 1
        if not self.all_cut and self.skip_count < self.count:
            return True
        else:
            return False


class CutAnimation(AnimationCounter):
    def __init__(self) -> None:
        AnimationCounter.__init__(self)
        self.all_cut = True

    def get_reloadcounter(self) -> "CutAnimation":
        return self

    def countup(self) -> bool:
        return False


class _JpySubImage(cw.image.Image):
    image: pygame.surface.Surface
    savecache: int
    visible: bool
    position: Tuple[int, int]
    position_noscale: Tuple[int, int]

    def __init__(self, config: "EffectBoosterConfig", section: str, cache: "JpyCache") -> None:
        self.configpath = config.path
        self.configdepth = config.dirdepth
        self.cache = cache
        # 画像加工などを開始したタイミング
        self.starttick = cw.cwpy.starttick
        # image load
        self.dirtype = config.get_int(section, "dirtype", 1)
        self.filename = config.get(section, "filename", "")
        self.smooth = config.get_bool(section, "smooth", False)
        clip = config.get_ints(section, "clip", 4, None)
        self.clip = cw.s(clip) if clip else None
        self.loadcache = config.get_int(section, "loadcache", 0)
        # image retouch
        self.flip = config.get_bool(section, "flip", False)
        self.mirror = config.get_bool(section, "mirror", False)
        self.turn = config.get_int(section, "turn", 0)
        self.mask = config.get_int(section, "mask", 0)
        self.colormap = config.get_int(section, "colormap", 0)
        self.alpha = config.get_int(section, "alpha", 0)
        self.exchange = config.get_int(section, "exchange", None)
        if self.exchange is None:
            self.exchange = config.get_int(section, "colorexchange", 0)
        self.noise = config.get_int(section, "noise", 0)
        self.noisepoint = config.get_int(section, "noisepoint", 0)
        self.filter = config.get_int(section, "filter", 0)
        # image temporary draw
        self.waittime = config.get_int(section, "wait", 0)
        self.animation = config.get_int(section, "animation", 0)
        self.animemove_noscale = config.get_ints(section, "animemove", 2, None)
        self.animemove = cw.s(self.animemove_noscale) if self.animemove_noscale else None
        animeclip = config.get_ints(section, "animeclip", 4, None)
        self.animeclip = cw.s(animeclip) if animeclip else None
        self.animespeed = config.get_int(section, "animespeed", 0)
        self.animeposition_noscale: Optional[Tuple[int, int]] = config.get_ints(section, "animeposition", 2, None)
        self.animeposition = cw.s(self.animeposition_noscale) if self.animeposition_noscale else None
        self.paintmode = config.get_int(section, "paintmode", 0)

        self.defaultcopymode = 2
        self.is_cacheable = True  # アニメーションなどが無く、キャッシング可能か
        self.is_animated = False  # アニメーションが発生したか
        self.can_mask = True  # 加工でマスクが無効になっていないか

    def draw2back(self, back: "JpyBackGroundImage", mask: bool) -> None:
        """背景に描画。"""
        assert isinstance(self, (JpyPartsImage, JpyBackGroundImage))
        if self.visible:
            image = self.get_image()

            if self.paintmode == 1:
                self.is_cacheable = False
                back.image.blit(image, self.position, None, pygame.BLEND_MIN)
            elif self.paintmode == 2:
                self.is_cacheable = False
                back.image.blit(image, self.position, None, pygame.BLEND_ADD)
            elif self.paintmode != 4:
                back.image.blit(image, self.position)
                # CardWirthでは透過ライン部分は強制的に透明となる
                # (アルファ値上書き？)
                if self.mask and mask:
                    x, y = self.position
                    w, h = image.get_size()
                    rect = (x, y, w, h)
                    if self.mask == 1:
                        back.image = cw.imageretouch.add_transparentline(back.image, True, False, rect, True)
                    elif self.mask == 2:
                        back.image = cw.imageretouch.add_transparentline(back.image, False, True, rect, True)
                    elif self.mask == 3:
                        back.image = cw.imageretouch.add_transparentmesh(back.image, setalpha=True)

    def drawtemp(self, doanime: AnimationCounter) -> None:
        """一時描画。"""
        assert isinstance(self, (JpyPartsImage, JpyBackGroundImage))

        # 一時描画せずにウェイトだけ
        if self.animation == 4:
            if doanime.countup() and self.waittime != 0:
                cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)
            self.wait(doanime)
        # 一時描画
        elif self.animation:
            if self.animeposition_noscale and self.animemove:
                assert self.animemove_noscale
                pos_noscale: Tuple[int, int] = self.animeposition_noscale
                pos_noscale = (pos_noscale[0] + self.animemove_noscale[0], pos_noscale[1] + self.animemove_noscale[1])
            elif self.animeposition_noscale:
                pos_noscale = self.animeposition_noscale
            elif self.animemove_noscale:
                pos_noscale = self.cache.load_position_noscale()
                pos_noscale = (pos_noscale[0] + self.animemove_noscale[0], pos_noscale[1] + self.animemove_noscale[1])
            else:
                assert self.position_noscale is not None
                pos_noscale = self.position_noscale

            animespeed = cw.util.numwrap(self.animespeed, 0, 255)

            # 単一描画
            sprs = cw.cwpy.topgrp.get_sprites_from_layer(cw.LAYER_JPY_TEMPORAL)
            if sprs:
                background = sprs[0].image
                assert background
                self.cache.restore()
            else:
                background = cw.cwpy.background.image.copy()
                self.cache.restore()
                cw.sprite.background.layered_draw_ex(cw.cwpy.cardgrp, background)
                cw.sprite.background.Jpy1TemporalSprite(background)

            if not animespeed:
                self._drawtemp_impl(doanime, background, cw.s(pos_noscale))

            # 連続描画
            else:
                if not doanime.all_cut:
                    goalpos_noscale = pos_noscale
                    pos_noscale = self.cache.load_position_noscale()
                    x, y = pos_noscale
                    rest_x = goalpos_noscale[0] - x
                    rest_y = goalpos_noscale[1] - y
                    xdir = bool(rest_x > -1)
                    ydir = bool(rest_y > -1)

                    SPF = 8
                    i = 0
                    while rest_x or rest_y:
                        self.is_cacheable = False
                        self.is_animated = True
                        n = math.sqrt(rest_x * rest_x + rest_y * rest_y)
                        n /= animespeed

                        if n == 0:
                            n = 1

                        if rest_x:
                            x = int(pos_noscale[0] + round(rest_x / n))
                            rest_x = goalpos_noscale[0] - x

                            if (rest_x < 0 and xdir) or (rest_x > 0 and not xdir):
                                x = goalpos_noscale[0]
                                rest_x = 0

                        if rest_y:
                            y = int(pos_noscale[1] + round(rest_y / n))
                            rest_y = goalpos_noscale[1] - y

                            if (rest_y < 0 and ydir) or (rest_y > 0 and not ydir):
                                y = goalpos_noscale[1]
                                rest_y = 0

                        pos_noscale = (x, y)
                        if self.waittime <= 0 or SPF <= self.waittime:
                            self._drawtemp_impl(doanime, background, cw.s(pos_noscale), anime=True,
                                                waittime=self.waittime)
                        elif SPF <= i:
                            self._drawtemp_impl(doanime, background, cw.s(pos_noscale), anime=True,
                                                waittime=self.waittime*SPF)
                            i %= SPF
                        else:
                            if self.animation == 1:
                                self._drawtemp_impl(doanime, background, cw.s(pos_noscale), anime=True, nowait=True)
                            i += 1
                        self.starttick = pygame.time.get_ticks()

            self.cache.save_position_noscale(pos_noscale)

    def _drawtemp_impl(self, doanime: AnimationCounter, background: pygame.surface.Surface,
                       pos: Tuple[int, int], redraw: bool = True, anime: bool = False, waittime: Optional[int] = None,
                       nowait: bool = False) -> None:
        """backgroundのposの位置に一時描画。"""
        if waittime is None:
            waittime = self.waittime

        self.cache.restore()
        image = self.get_image()
        image = self.clip_tempimg(image, pos)

        rect = pygame.rect.Rect(pos, image.get_size())
        rect = rect.clip(background.get_rect())

        if self.paintmode == 1:
            blendmode = pygame.BLEND_MIN
        elif self.paintmode == 2:
            blendmode = pygame.BLEND_ADD
        else:
            blendmode = 0

        if 0 < rect[2] and 0 < rect[3]:
            if self.paintmode != 4:
                if redraw:
                    if not self.animation == 1:
                        self.cache.before = background.subsurface(rect).copy()
                        self.cache.beforeback = background
                        self.cache.beforerect = rect
                    background.blit(image, pos, special_flags=blendmode)
                    if not nowait and doanime.countup() and waittime != 0:
                        cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)
                else:
                    if self.animation == 1:
                        background.blit(image, pos, special_flags=blendmode)
                        if not nowait and doanime.countup() and waittime != 0:
                            cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)

        if not nowait:
            self.wait(doanime, anime=anime, waittime=waittime)

    def clip_tempimg(self, image: pygame.surface.Surface, pos: Tuple[int, int]) -> pygame.surface.Surface:
        if self.animeclip:
            size = image.get_size()
            x, y, w, h = self.animeclip
            rect = pygame.Rect(pos, size)
            rect2 = pygame.Rect((x, y), (w, h))

            if rect.colliderect(rect2):
                left = rect.left if rect.left > rect2.left else rect2.left
                top = rect.top if rect.top > rect2.top else rect2.top
                right = rect.right if rect.right < rect2.right else rect2.right
                bottom = rect.bottom if rect.bottom < rect2.bottom else rect2.bottom
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

    def wait(self, doanime: AnimationCounter, anime: bool = False, waittime: Optional[int] = None) -> None:
        if waittime is None:
            waittime = self.waittime

        # 指定時間だけ待機
        if waittime > 0:
            self.is_cacheable = False
            self.is_animated = True
            if doanime.countup():
                waittime2 = self._cut_waittime(waittime)
                if waittime2:
                    wait_effectbooster(waittime2, doanime=doanime)
                else:
                    cw.cwpy.wait_frame(0)

        # 右クリックするまで待機
        elif waittime < 0:
            self.is_cacheable = False
            self.is_animated = True
            if doanime.countup():
                wait_effectbooster(0, doanime=doanime)

    def _cut_waittime(self, waittime: int) -> int:
        """
        待機時間からイメージの加工等を行うのにかかった時間を差し引いて返す。
        """
        if 0 <= waittime:
            tick = pygame.time.get_ticks()
            if self.starttick is not None and self.starttick < tick:
                waittime -= min(waittime, tick-self.starttick)
        return waittime

    def retouch(self) -> None:
        """画像加工。"""
        assert isinstance(self, (JpyPartsImage, JpyBackGroundImage))
        image = self.get_image()

        # 画像がない場合、加工しない
        if image.get_size() == cw.s((0, 0)):
            # キャッシュ (for JpyPartsImage)
            if 1 <= self.savecache <= 8:
                self.cache.save_image(self.savecache, image)
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

        self.can_mask = True

        # フィルタ
        if self.filter:
            if self.filter == 1:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_shape(image)
            elif self.filter == 2:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_sharpness(image)
            elif self.filter == 3:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_sunpower(image)
            elif self.filter == 4:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_coloremboss(image)
            elif self.filter == 5:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_darkemboss(image)
            elif self.filter == 6:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_electrical(image)
            elif self.filter == 7:
                image = cw.imageretouch.to_binaryformat(image, -1, image.get_at((0, 0))[:3])
            elif self.filter == 8:
                image = cw.imageretouch.spread_pixels(image)
            elif self.filter == 9:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.to_negative(image)
            elif self.filter == 10:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.filter_emboss(image)

        # 色調変化
        if self.colormap:
            if self.paintmode != 3:
                self.can_mask = False
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
                if self.noisepoint != 0 and self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.add_lightness(image, self.noisepoint)
            elif self.noise == 2:
                if self.paintmode != 3:
                    self.can_mask = False
                if self.noisepoint < 0:
                    image.fill((255, 255, 255))
                else:
                    image = cw.imageretouch.to_binaryformat(image, self.noisepoint)
            elif self.noise == 3:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.add_noise(image, self.noisepoint)
            elif self.noise == 4:
                if self.paintmode != 3:
                    self.can_mask = False
                image = cw.imageretouch.add_noise(image, self.noisepoint, True)
            elif self.noise == 5 and self.filter != 7:
                image = cw.imageretouch.add_mosaic(image, self.noisepoint)

        # マスク
        if self.transparent and self.can_mask and 0 < self.image.get_width():
            if self.clip:
                colorkey: Optional[Tuple[int, int, int, int]] = image.get_at(self.clip[:2])
            else:
                colorkey = image.get_at((0, 0))
            assert colorkey
            image.set_colorkey(colorkey[:3], pygame.RLEACCEL)
        else:
            colorkey = None
            image.set_colorkey(None)

        # 回転
        if self.turn:
            if self.turn == 1:
                image = pygame.transform.rotate(image, 270)
            elif self.turn == 2:
                image = pygame.transform.rotate(image, 90)

        # 切り取り
        if self.clip:
            x, y, w, h = self.clip
            rect = pygame.rect.Rect((x, y), (w, h))
            clip = pygame.rect.Rect((0, 0), image.get_size())
            clip = clip.clip(rect)

            if 0 < clip.width and 0 < clip.height:
                image = image.subsurface(clip)
            else:
                image = pygame.Surface(cw.s((0, 0))).convert()

        # リサイズ for JpyPartsImage
        if not hasattr(self, "backcolor"):
            assert self.width is not None
            width = self.width if 0 <= self.width else image.get_width()
            height = self.height if 0 <= self.height else image.get_height()
            size = (width, height)

            if 0 <= width and 0 <= height:
                if width == 0 or height == 0:
                    image = pygame.Surface(cw.s((0, 0))).convert()
                elif not size == image.get_size() and not size == cw.s((0, 0)):
                    image = cw.image.smoothscale(image, size, smoothing=self.smooth)

        # 透過ライン
        if self.mask:
            setalpha = self.transparent and not self.can_mask
            if self.mask == 1:
                image = cw.imageretouch.add_transparentline(image, True, False, setalpha=setalpha)
            elif self.mask == 2:
                image = cw.imageretouch.add_transparentline(image, False, True, setalpha=setalpha)
            elif self.mask == 3:
                image = cw.imageretouch.add_transparentmesh(image, setalpha=setalpha)

        # 透明度
        if self.paintmode == 3:
            if 32 <= image.get_bitsize() and (image.get_flags() & pygame.SRCALPHA):
                image.fill((255, 255, 255, self.alpha), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                image.set_alpha(self.alpha)

        # キャッシュ (for JpyPartsImage)
        if 1 <= self.savecache <= 8:
            self.cache.save_image(self.savecache, image)

        self.image = image

    def load(self, doanime: AnimationCounter) -> None:
        """画像作成。"""
        assert isinstance(self, (JpyPartsImage, JpyBackGroundImage))
        path, can_loaded_scaledimage = self.get_filepath()
        ext = cw.util.splitext(path)[1].lower()

        # ファイル読み込み
        if os.path.isfile(path):
            image = None
            mtime = 0.0
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)

            cachekey = (_JpySubImage, cw.UP_SCR, False, path)

            if cw.cwpy.is_playingscenario() and cachekey in cw.cwpy.sdata.resource_cache:
                cache = cw.cwpy.sdata.resource_cache[cachekey]
                assert isinstance(cache, tuple)
                image, cachemtime = cache
                image = image.copy()
                if cachemtime < mtime:
                    image = None

            if image is None:

                # 効果音ファイル
                if ext in cw.EXTS_SND:
                    sound = cw.util.load_sound(path)

                    if sound:
                        self.is_cacheable = False
                        self.is_animated = True
                        if doanime.countup():
                            sound.play(True)

                    image = pygame.Surface((0, 0)).convert()
                # Jpy1ファイル
                elif ext == ".jpy1":
                    # 変化する場合はキャッシュ不可
                    jpy1 = JpyImage(path, cache=self.cache, doanime=doanime, mask=False, parent=self)
                    image = jpy1.get_image()
                    if jpy1.is_cacheable:
                        cw.cwpy.sdata.sweep_resourcecache(cw.util.calc_imagesize(image))
                        cw.cwpy.sdata.resource_cache[cachekey] = (image.copy(), mtime)
                    else:
                        self.is_cacheable = False
                    if jpy1.is_animated:
                        self.is_animated = True
                # Jpdcファイル
                elif ext == ".jpdc":
                    self.is_cacheable = False
                    image = JpdcImage(False, path, cache=self.cache, defaultcopymode=self.defaultcopymode,
                                      doanime=doanime).get_image()
                    # 重くならないのでキャッシュ不要
                # Jptxファイル
                elif ext == ".jptx":
                    image = JptxImage(path, False).get_image()
                    cw.cwpy.sdata.sweep_resourcecache(cw.util.calc_imagesize(image))
                    cw.cwpy.sdata.resource_cache[cachekey] = (image.copy(), mtime)
                # その他画像ファイル
                else:
                    image = cw.s(cw.util.load_image(path, False, isback=True,
                                                    can_loaded_scaledimage=can_loaded_scaledimage,
                                                    use_excache=cw.cwpy.background.use_excache))

        # 画像キャッシュから読み込み
        elif 1 <= self.loadcache <= 8:
            image = self.cache.load_image(self.loadcache)
        # 背景画像作成 for JpyBackGroundImage
        elif hasattr(self, "backcolor"):
            assert isinstance(self, JpyBackGroundImage)
            assert self.width is not None
            width = self.width if self.width > cw.s(0) else cw.s(cw.SIZE_AREA[0])
            height = self.height if self.height > cw.s(0) else cw.s(cw.SIZE_AREA[1])
            size = (width, height)
            image = pygame.Surface(size).convert()
            image.fill(self.backcolor)
        # 背景画像作成 for JpyPartsImage
        elif not hasattr(self, "backcolor") and -1 < self.height and self.width is not None and -1 < self.width:
            assert isinstance(self, JpyPartsImage)
            assert self.width is not None
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
            assert self.width is not None
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
                if width == 0 or height == 0:
                    image = pygame.Surface(cw.s((0, 0))).convert()
                elif image.get_width() == 0 or image.get_height() == 0:
                    image = pygame.Surface(size).convert()
                elif self.smooth:
                    image = cw.image.smoothscale(image, size)
                else:
                    image = pygame.transform.scale(image, size)

        self.image = image

    def get_filepath(self, dirtype: int = -1) -> Tuple[str, bool]:
        """読み込むファイルのパスを取得する。"""
        if self.filename:
            if dirtype == -1:
                dirtype = self.dirtype
            return get_filepath_s(self.configpath, self.configdepth, self.filename, dirtype)
        else:
            return ("", False)


def get_filepath_s(configpath: str, dirdepth: int, filename: str, dirtype: int = -1,
                   scedir: str = "") -> Tuple[str, bool]:
    """dirtypeに基づいて読み込むファイルのパスを取得する。"""
    if dirtype == -1:
        dirtype = 1

    if not scedir:
        inusecard = cw.cwpy.event.get_inusecard()
        if cw.cwpy.event.in_inusecardevent and cw.cwpy.is_runningevent() and inusecard and\
                inusecard.carddata is not None and inusecard.carddata.gettext("Property/Materials", ""):
            scedir = cw.util.join_yadodir(inusecard.carddata.gettext("Property/Materials", ""))
        else:
            scedir = cw.cwpy.sdata.scedir

    def get_mtype(fpath: str) -> int:
        ext = cw.util.splitext(fpath)[1].lower()
        if ext in cw.EXTS_SND:
            return cw.M_SND
        else:
            return cw.M_IMG

    def find_materialpath(fpath: str) -> str:
        mtype = get_mtype(fpath)
        inusecardpath = cw.util.get_inusecardmaterialpath(filename, mtype, findskin=False)
        if inusecardpath:
            fpath = inusecardpath
        else:
            fpath = cw.util.get_materialpath(filename, mtype, findskin=False, scedir=scedir)
        fpath = cw.cwpy.rsrc.get_filepath(fpath)
        return fpath

    if dirtype == 1:
        if configpath:
            dpath = os.path.dirname(configpath)
            fpath = cw.util.join_paths(dpath, filename)
            filename = cw.util.relpath(fpath, scedir)
            fpath = find_materialpath(fpath)
        else:
            fpath = ""
        if not fpath or not os.path.isfile(fpath):
            # シナリオ内に存在しなかった
            return ("", False)
        dpath = os.path.dirname(fpath)
        filename = os.path.basename(fpath)
    elif dirtype == 2:
        dpath = cw.util.join_paths(cw.cwpy.skindir, "Table")
        lfname = filename.lower()
        if lfname.endswith(".jpy1") or lfname.endswith(".jptx") or lfname.endswith(".jpdc"):
            fpath = cw.util.join_paths(dpath, filename)
            fpath = cw.cwpy.rsrc.get_filepath(fpath)
        else:
            mtype = get_mtype(filename)
            fpath = cw.util.join_paths(dpath, cw.util.splitext(filename)[0])
            fpath = cw.util.find_resource(fpath, mtype)
        return (fpath, True)
    elif dirtype == 3:
        dpath = cw.util.join_paths(cw.cwpy.skindir, "EffectBooster")
        lfname = filename.lower()
        if lfname.endswith(".jpy1") or lfname.endswith(".jptx") or lfname.endswith(".jpdc"):
            fpath = cw.util.join_paths(dpath, filename)
            fpath = cw.cwpy.rsrc.get_filepath(fpath)
        else:
            mtype = get_mtype(filename)
            fpath = cw.util.join_paths(dpath, cw.util.splitext(filename)[0])
            fpath = cw.util.find_resource(fpath, mtype)
        return (fpath, True)
    elif dirtype == 4:
        if cw.cwpy.is_runningevent() and cw.cwpy.event.in_inusecardevent and cw.cwpy.event.get_inusecard():
            inusecard = cw.cwpy.event.get_inusecard()
            assert inusecard
            assert inusecard.carddata is not None
            if not inusecard.carddata.getbool(".", "scenariocard", False):
                e_mates = inusecard.carddata.find("Property/Materials")
                can_loaded_scaledimage = inusecard.carddata.getbool(".", "scaledimage", False)
                if e_mates is not None:
                    dpath = e_mates.text
                    # dirtype=4にはdirdepthが影響する
                    for _i in range(dirdepth):
                        dpath = os.path.dirname(dpath)

                    fpath = cw.util.join_paths(dpath, filename)
                    fpath = cw.util.join_yadodir(fpath)
                    if os.path.isfile(fpath):
                        return (fpath, can_loaded_scaledimage)

        dpath = os.path.dirname(configpath)
        # dirtype=4にはdirdepthが影響する
        for _i in range(dirdepth):
            dpath = os.path.dirname(dpath)

        fpath = cw.util.join_paths(dpath, filename)
        filename = cw.util.relpath(fpath, scedir)
        fpath = find_materialpath(fpath)
        # 指定位置に存在しなかった
        if not os.path.isfile(fpath):
            return ("", False)
        cw.cwpy.background.store_filepath(fpath)

        if cw.cwpy.event.in_inusecardevent and cw.cwpy.event.get_inusecard():
            inusecard = cw.cwpy.event.get_inusecard()
            assert inusecard
            assert inusecard.carddata is not None
            can_loaded_scaledimage = inusecard.carddata.getbool(".", "scaledimage", False)
        else:
            can_loaded_scaledimage = cw.cwpy.sdata.can_loaded_scaledimage

        return (fpath, can_loaded_scaledimage)
    elif dirtype == 5:
        for dname in ("Sound", "BgmAndSound"):
            dpath = cw.util.join_paths(cw.cwpy.skindir, dname)
            mtype = get_mtype(filename)
            fpath = cw.util.join_paths(dpath, cw.util.splitext(filename)[0])
            fpath = cw.util.find_resource(fpath, mtype)
            if fpath:
                return (fpath, True)
        return ("", True)
    elif dirtype == 6:
        if not configpath:
            return ("", False)
        dpath = os.path.dirname(os.path.dirname(configpath))
    elif dirtype == 7:
        dpath = ""
    else:
        if not configpath:
            return ("", False)
        dpath = os.path.dirname(configpath)

    path = cw.util.join_paths(os.path.normpath(cw.util.join_paths(dpath, filename)))
    path = cw.cwpy.rsrc.get_filepath(path)
    cw.cwpy.background.store_filepath(path)

    if cw.cwpy.event.in_inusecardevent and cw.cwpy.event.get_inusecard():
        inusecard = cw.cwpy.event.get_inusecard()
        assert inusecard
        assert inusecard.carddata is not None
        can_loaded_scaledimage = inusecard.carddata.getbool(".", "scaledimage", False)
    else:
        can_loaded_scaledimage = cw.cwpy.sdata.can_loaded_scaledimage

    return (path, can_loaded_scaledimage)


class JpyPartsImage(_JpySubImage):
    def __init__(self, config: "EffectBoosterConfig", section: str, cache: "JpyCache", mask: bool) -> None:
        _JpySubImage.__init__(self, config, section, cache)
        self.height = cw.s(config.get_int(section, "height", -1))
        width = config.get_int(section, "width", None)
        self.width = cw.s(width) if width is not None else None
        self.haswidth = self.width is not None
        if self.width is None:
            self.width = -1
        self.color = config.get_color(section, "color", (0, 0, 0))
        self.position_noscale = config.get_ints(section, "position", 2, (0, 0))
        self.position = cw.s(self.position_noscale)
        self.savecache = config.get_int(section, "savecache", 0)
        self.visible = config.get_bool(section, "visible", True)
        self.transparent = config.get_bool(section, "transparent", True)


class JpyBackGroundImage(_JpySubImage):
    def __init__(self, config: "EffectBoosterConfig", cache: "JpyCache", mask: bool) -> None:
        _JpySubImage.__init__(self, config, "init", cache)
        self.backcolor = config.get_color("init", "backcolor", (0, 0, 0))
        width = config.get_int("init", "backwidth", None)
        self.width = cw.s(width) if width is not None else None
        self.vanish_anime = self.width is not None and self.width < 0
        if self.width is None:
            self.width = -1
        self.height = cw.s(config.get_int("init", "backheight", -1))
        self.transparent = config.get_bool("init", "transparent", False)
        self.dirdepth = config.get_int("init", "dirdepth", 0)
        self.dirdepth = max(0, self.dirdepth)
        self.configpath = os.path.abspath(config.path)
        self.configdepth = self.dirdepth
        self.position_noscale = (0, 0)
        self.position = cw.s(self.position_noscale)
        self.savecache = 0
        self.visible = False


class JpyImage(cw.image.Image):
    def __init__(self, path: str, mask: bool = False, cache: Optional["JpyCache"] = None,
                 doanime: Optional[AnimationCounter] = None, parent: Optional[_JpySubImage] = None) -> None:
        starttick = pygame.time.get_ticks()
        if not cache:
            cache = JpyCache()
        if not doanime:
            doanime = AnimationCounter()

        config = EffectBoosterConfig(path, "init")
        back = JpyBackGroundImage(config, cache, mask)

        if back.vanish_anime:
            # ドキュメントではbackwidthとbackheightは
            # 省略か-1指定で(632, 420)になると書かれているが、
            # 実際にはbackwidthが0未満だと消滅する
            self.image = pygame.Surface(cw.s((0, 0))).convert()
            self.is_cacheable = True
            self.is_animated = False

        else:
            config.path = os.path.abspath(config.path)
            config.dirdepth = back.dirdepth

            can_mask = True
            back.load(doanime)
            defaultcopymode = 1
            self.is_cacheable = not back.transparent
            self.is_animated = back.is_animated
            if parent and back.loadcache:
                self.is_cacheable = False

            for section in config.sections():
                if not section == "init":
                    parts = JpyPartsImage(config, section, cache, mask)
                    if parts.haswidth:
                        assert parts.width is not None
                        if parts.width < 0 and parts.dirtype == 2:
                            # ドキュメントではwidthとheightは
                            # 省略か-1指定で画像のサイズになると書かれているが、
                            # 実際にはwidthが0未満かつdirtype=2だと処理が中断される
                            break
                    parts.defaultcopymode = defaultcopymode
                    parts.starttick = starttick
                    parts.load(doanime)
                    parts.retouch()
                    parts.drawtemp(doanime)
                    parts.draw2back(back, mask)
                    if not parts.is_cacheable:
                        self.is_cacheable = False
                    if parts.is_animated:
                        self.is_animated = True
                    if parent and parts.loadcache:
                        self.is_cacheable = False
                    if parts.animation in (1, 2, 3):
                        defaultcopymode = 2
                    can_mask &= parts.can_mask
                    starttick = pygame.time.get_ticks()

            back.starttick = starttick
            back.retouch()
            back.drawtemp(doanime)
            if not back.is_cacheable:
                self.is_cacheable = False
            if back.is_animated:
                self.is_animated = True
            can_mask &= back.can_mask
            self.image = back.get_image()

            # 互換動作: 1.30以前はレタッチ内容によってセルとして配置した時に
            #           指定したマスク設定が無効にされてしまう場合があるが、
            #           1.50では無効にならない
            if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)) and\
                    0 < self.image.get_width():
                if mask and can_mask:
                    self.image = self.image.convert()
                    self.image.set_colorkey(self.image.get_at((0, 0)))
            else:
                if mask and (parent is None or can_mask):
                    self.image = self.image.convert()
                    self.image.set_colorkey(self.image.get_at((0, 0)))


class JpyCache(object):
    """Jpy1ファイル読み込み時に使うキャッシュ。
    最後に一時描画したポジションや、
    キャッシュした画像をセーブ・ロードする。
    """
    def __init__(self) -> None:
        self.pos_noscale: Optional[Tuple[int, int]] = None
        self.img: Dict[int, pygame.surface.Surface] = {}
        # 一時描画を削除するために描画前背景を保存する
        self.before: Optional[pygame.surface.Surface] = None
        self.beforeback: Optional[pygame.surface.Surface] = None
        self.beforerect: Optional[pygame.rect.Rect] = None  # 一時描画された領域

    def restore(self) -> None:
        if self.before:
            assert self.beforeback
            assert self.beforerect
            self.beforeback.blit(self.before, self.beforerect.topleft)
            self.before = None
            self.beforeback = None
            self.beforerect = None

    def save_position_noscale(self, pos_noscale: Tuple[int, int]) -> None:
        self.pos_noscale = pos_noscale

    def load_position_noscale(self) -> Tuple[int, int]:
        if self.pos_noscale:
            return self.pos_noscale
        else:
            return (0, 0)

    def save_image(self, n: int, image: pygame.surface.Surface) -> None:
        self.img[n] = image

    def load_image(self, n: int) -> pygame.surface.Surface:
        image = self.img.get(n, None)

        if image:
            image = image.copy()
        else:
            image = pygame.Surface(cw.s((0, 0))).convert()

        return image


class JpdcImage(cw.image.Image):
    def __init__(self, mask: bool, path: str, cache: Optional[JpyCache] = None, defaultcopymode: int = 2,
                 doanime: Optional[AnimationCounter] = None) -> None:
        if not doanime:
            doanime = AnimationCounter()
        config = EffectBoosterConfig(path, "jpdc:init")
        ints = config.get_ints("jpdc:init", "clip", 4, (0, 0, 632, 420))
        assert ints
        x_noscale, y_noscale, w_noscale, h_noscale = ints

        x_noscale = max(0, x_noscale)
        y_noscale = max(0, y_noscale)
        if w_noscale <= 0:
            w_noscale = cw.SIZE_AREA[0]
        if h_noscale <= 0:
            h_noscale = cw.SIZE_AREA[1]

        x, y, w, h = cw.s((x_noscale, y_noscale, w_noscale, h_noscale))
        rect = pygame.Rect(x, y, w, h)
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert_alpha()
        copymode = config.get_int("jpdc:init", "copymode", 0)

        # 互換動作: 1.50では`copymode=1`指定は`copymode=2`指定のように動く
        if not (cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA))):
            if copymode == 1:
                copymode = 2

        if not copymode:
            copymode = defaultcopymode

        if copymode == 3:
            self.image.fill((255, 255, 255))
        else:
            selection = cw.cwpy.selection
            cw.cwpy.clear_selection()
            cw.sprite.background.layered_draw_ex(cw.cwpy.cardgrp, self.image)
            cw.cwpy.change_selection(selection)
            if copymode == 2:
                for sprite in cw.cwpy.topgrp.get_sprites_from_layer(cw.LAYER_JPY_TEMPORAL):
                    assert sprite.image
                    assert sprite.rect
                    self.image.blit(sprite.image, sprite.rect.topleft)
            cw.cwpy.background.reload_jpdcimage = False

        rect2 = self.image.get_rect()
        if rect2.contains(rect):
            self.image = self.image.subsurface(rect)
        else:
            # 画面外
            image = self.image
            self.image = pygame.Surface(rect.size).convert_alpha()
            self.image.fill((255, 255, 255))
            if rect2.colliderect(rect):
                self.image.blit(image.subsurface(rect2.clip(rect)), cw.s((0, 0)))

        # 画像保存
        filename = config.get("jpdc:init", "savefilename", "")
        savecomment = config.get("jpdc:init", "savecomment", "")

        if doanime and not doanime.all_cut and not cw.cwpy.update_scaling and filename and cw.cwpy.is_playingscenario():
            cw.fsync.sync()
            filename = cw.util.repl_dischar(filename)
            savecomment = savecomment.replace("%file%", filename)
            savecomment = savecomment.replace("%dir%", os.path.dirname(path))

            if doanime and not doanime.all_cut:
                if savecomment:
                    cw.cwpy.set_titlebar(savecomment + " - " + cw.cwpy.create_title())
                else:
                    cw.cwpy.set_titlebar(filename + " - " + cw.cwpy.create_title())

            saveimage_noscale = self.image
            saveimage = None
            if cw.UP_SCR != 1.0:
                saveimage_noscale = cw.image.smoothscale(saveimage_noscale, (w_noscale, h_noscale))
                saveimage = self.image

            path = cw.util.join_paths(os.path.dirname(path), filename)

            # シナリオフォルダ外に保存しようとした場合は保存不可
            cpath1 = os.path.abspath(os.path.normpath(path))
            cpath2 = os.path.abspath(os.path.normpath(cw.cwpy.sdata.scedir))
            cpath1 = cw.util.join_paths(cpath1)
            cpath2 = cw.util.join_paths(cpath2) + "/"
            ncpath1 = os.path.normcase(cpath1)
            ncpath2 = os.path.normcase(cpath2)
            if ncpath1.startswith(ncpath2):
                # シナリオの不変を保つためにScenarioLog内に保存
                rel = cw.util.relpath(cpath1, cpath2)
                temppath = cw.util.join_paths(cw.tempdir, "ScenarioLog/TempFile")
                path = cw.util.join_paths(temppath, rel)
                dpath = os.path.dirname(path)
                if not os.path.isdir(dpath):
                    os.makedirs(dpath)
                cw.sprite.message.store_messagelogimage(path, True)
                spext = cw.util.splitext(path)

                npath = cw.util.get_keypath(path)
                if npath in cw.cwpy.sdata.ex_cache:
                    ex_cache: Optional[List[Optional[Union[str, bytes]]]] = None
                else:
                    ex_cache = [None] * len(cw.SCALE_LIST)

                scpath = cw.util.join_paths(cw.cwpy.sdata.scedir, rel)
                nexist = False
                if ex_cache is not None:
                    if os.path.isfile(npath):
                        ex_cache[0] = npath
                    elif os.path.isfile(scpath):
                        nexist = True
                        ex_cache[0] = scpath
                        scpathsp = cw.util.splitext(scpath)
                        for i, scale in enumerate(cw.SCALE_LIST):
                            scpathxn = "%s.x%d%s" % (scpathsp[0], scale, scpathsp[1])
                            if os.path.isfile(scpathxn):
                                ex_cache[i+1] = scpathxn

                for i, scale in enumerate(cw.SCALE_LIST):
                    pathxn = "%s.x%d%s" % (spext[0], scale, spext[1])
                    if os.path.isfile(pathxn):
                        if ex_cache is not None and not nexist:
                            ex_cache[i+1] = pathxn

                if ex_cache is not None:
                    for i, cachepath in enumerate(ex_cache):
                        if cachepath:
                            assert isinstance(cachepath, str)
                            try:
                                with open(cachepath, "rb") as f:
                                    ex_cache[i] = f.read()
                                if cw.util.is_descendant(cachepath, temppath):
                                    cw.util.remove(cachepath)
                            except IOError:
                                cw.util.print_ex()
                    cw.cwpy.sdata.ex_cache[npath] = ex_cache

                pygame.image.save(saveimage_noscale, path)

                if cw.cwpy.event.in_inusecardevent and cw.cwpy.event.get_inusecard():
                    inusecard = cw.cwpy.event.get_inusecard()
                    assert inusecard
                    assert inusecard.carddata is not None
                    can_loaded_scaledimage = inusecard.carddata.getbool(".", "scaledimage", False)
                else:
                    can_loaded_scaledimage = cw.cwpy.sdata.can_loaded_scaledimage

                if saveimage:
                    path = "%s.x%d%s" % (spext[0], cw.UP_SCR, spext[1])
                    rel2 = cw.util.relpath(path, temppath)
                    x2path = cw.util.join_paths(cw.cwpy.sdata.scedir, rel2)
                    if can_loaded_scaledimage or not os.path.isfile(x2path):
                        pygame.image.save(saveimage, path)

                # Jpy1の内部でのキャッシュヒットミスを
                # 避けるため、Jpy1のキャッシュを全て取り除く
                removekeys: List[Union[Tuple[str, str, float, Union[bool, List[bool]]],
                                       Tuple[Type["cw.effectbooster._JpySubImage"], float, bool, str]]] = []
                for cachekey in cw.cwpy.sdata.resource_cache.keys():
                    if isinstance(cachekey, tuple) and len(cachekey) == 4:
                        if isinstance(cachekey[3], str) and\
                                cw.util.splitext(cachekey[3])[1].lower() == ".jpy1":
                            removekeys.append(cachekey)
                        elif isinstance(cachekey[0], str) and\
                                cw.util.splitext(cachekey[0])[1].lower() == ".jpy1":
                            # BUG: error: Argument 1 to "append" of "list" has incompatile type "Union[Tuple[str, str,
                            #      float, Union[bool, List[bool]]], Tuple[str, float, Tuple[int, int], bool, str]]";
                            #      expected "Union[Tuple[str, str, float, Union[bol, List[bool]]],
                            #      Tuple[Type[_JpySubImage], float, bool, str]]" (mypy 0.790)
                            cachekey = typing.cast(Tuple[str, str, float, Union[bool, List[bool]]], cachekey)
                            removekeys.append(cachekey)
                for key in removekeys:
                    del cw.cwpy.sdata.resource_cache[key]

                if cw.cwpy.is_playingscenario():
                    cw.cwpy.rsrc.specialchars.reset()

                # メニューカードが更新されるものを更新リストに登録する
                if not cw.cwpy.update_scaling:
                    for mcard in cw.cwpy.get_mcards():
                        if not mcard.is_initialized():
                            continue
                        if mcard.cardimg.is_modifiedfile():
                            mcard.cardimg.clear_cache()
                            cw.cwpy.file_updates.add(mcard)
                            mcard.cardimg.use_excache = True
                    if not cw.cwpy.file_updates_bg and cw.cwpy.background.is_modifiedfile():
                        cw.cwpy.file_updates_bg = True
                        cw.cwpy.background.use_excache = True

            if doanime and not doanime.all_cut:
                cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)
                self.wait(doanime=doanime)
                cw.cwpy.update_titlebar()

            cw.cwpy.background.reload_jpdcimage = False

        if mask:
            self.image = self.image.convert()
            self.image.set_colorkey(self.image.get_at((0, 0)), pygame.RLEACCEL)

    def wait(self, doanime: AnimationCounter) -> None:
        # 右クリックするまで待機
        cw.cwpy.change_cursor("mouse")

        wait_effectbooster(0, doanime=doanime)

        cw.cwpy.change_cursor()


class JptxImage(cw.image.Image):
    def __init__(self, path: str, mask: bool) -> None:
        config = EffectBoosterConfig(path, "jptx:init", section_ignorecase=False)
        if not config.has_section("jptx:init"):
            self.image = pygame.Surface((cw.s(1), cw.s(1))).convert_alpha()
            self.image.fill((0, 0, 0, 0))
            return
        # parameters
        backcolor = config.get_color("jptx:init", "backcolor", (0, 0, 0))
        backwidth = cw.s(config.get_int("jptx:init", "backwidth", -1))
        backheight = cw.s(config.get_int("jptx:init", "backheight", -1))
        autoline = config.get_bool("jptx:init", "autoline", True)
        lineheight = config.get_int("jptx:init", "lineheight", 100)
        fontpixels_noscale = config.get_int("jptx:init", "fontpixels", 12)
        fontpixels = cw.s(fontpixels_noscale)
        fontcolor = config.get_color("jptx:init", "fontcolor", (255, 255, 255))
        fontface = config.get("jptx:init", "fontface", "ＭＳ Ｐゴシック")
        antialias = config.get_bool("jptx:init", "antialias", False)
        fonttransparent = config.get_bool("jptx:init", "fonttransparent", False)
        text = config.get("jptx:begin", "jptx:end", "")

        if not autoline:
            text = text.replace("\n", "")

        text = text.replace("\t", "")
        # image
        width = backwidth if backwidth > cw.s(0) else cw.s(cw.SIZE_AREA[0])
        height = backheight if backheight > cw.s(0) else cw.s(cw.SIZE_AREA[0])
        self.image = pygame.Surface((width, height)).convert(24)
        self.image.fill(backcolor)

        if mask:
            self.image.set_colorkey(self.image.get_at((0, 0)), pygame.RLEACCEL)

        if fonttransparent:
            self.image.fill(fontcolor, (0, 0, width, 1))

        # text rendering
        bold = False
        underline = False
        italic = False

        class Info(object):
            def __init__(self, outer: JptxImage, lineheight: int, fontface: str, fontpixels: int,
                         fontpixels_noscale: int, fontcolor: Tuple[int, int, int]) -> None:
                self.outer = outer
                self.lineheight = lineheight
                self.fontpixels = fontpixels
                self.fontpixels_noscale = fontpixels_noscale
                self.fontcolor = fontcolor
                self.fontface = fontface
                self.oldfonts: List[Tuple[str, int, int, Tuple[int, int, int]]] = []
                self.x = 0
                self.y = 0.0
                self.w = 0
                self.h = 0
                self.tag = ""
                self.nolinedata = True
                self.tagonly = True
                self.strike = False
                self.create_font()
                self.chars: List[str] = []

            def create_font(self) -> None:
                self.font = cw.imageretouch.Font(self.fontface, self.fontpixels)
                if cw.UP_SCR == 1.0:
                    self.font_noscale = self.font
                else:
                    self.font_noscale = cw.imageretouch.Font(self.fontface, self.fontpixels_noscale)

                # BUG: cwconv.dllではポイントサイズを2倍してテキストを描画し、
                #      最後に縮小する事でアンチエイリアスを実現している。
                #      ポイントサイズによって計算し、誤差も発生するため、
                #      一部サイズの結果がDPIによって様々におかしくなるが、
                #      そのバグに依存した描画を行っているシナリオが多数あるので、
                #      CardWirthが一般的に実行されていた96DPIでのサイズ計算に合せる。
                #      将来データバージョンを上げる時に修正するべきかもしれない。
                pixels = self.fontpixels_noscale
                if (pixels+2) % 4 == 0:
                    pixels += 1
                points2 = (pixels * 72 // 96) * 2
                pixels_aa = points2 * 96 // 72
                if (pixels-1) % 4 == 0:
                    pixels_aa += 3
                # -- サイズ補正ここまで
                pixels_aa_noscale = max(1, pixels_aa)
                pixels_aa = cw.s(pixels_aa_noscale)
                self.font2 = cw.imageretouch.Font(self.fontface, pixels_aa)
                if cw.UP_SCR == 1.0:
                    self.font2_noscale = self.font2
                else:
                    self.font2_noscale = cw.imageretouch.Font(self.fontface, pixels_aa_noscale)

            def get_height(self) -> int:
                height = self.fontpixels
                height += cw.s(2)
                return height

            def render(self) -> None:
                if not self.chars:
                    return
                chars = "".join(self.chars)
                self.chars = []

                if antialias:
                    subimg = info.font2.render(chars, True, info.fontcolor)
                    if cw.UP_SCR == 1.0:
                        size = info.font2.size(chars)
                    else:
                        size = cw.s(info.font2_noscale.size(chars))
                    width = size[0] // 2
                    height = size[1] // 2
                    yp = 0
                    rect = pygame.rect.Rect(int(info.x), int(info.y)+yp, width, height)
                    rect = rect.clip(self.outer.image.get_rect())
                    if 0 < rect.width and 0 < rect.height:
                        if cw.UP_SCR != 1.0 and subimg.get_size() != size:
                            # 1倍で描画した時のサイズに合せる
                            subimg = pygame.transform.smoothscale(subimg, size)
                        # 拡大した背景にBlitし、その後縮小する
                        subimg2 = self.outer.image.subsurface(rect)
                        w, h = subimg2.get_size()
                        w2 = w * 2
                        h2 = h * 2
                        subimg2 = pygame.transform.scale(subimg2, (w2, h2))
                        subimg2.blit(subimg, (0, 0))
                        # 縮小
                        subimg = pygame.transform.smoothscale(subimg2, (w, h))

                    if cw.UP_SCR == 1.0:
                        width = info.font2.size_withoutoverhang(chars)[0] // 2
                    else:
                        width = cw.s(info.font2_noscale.size_withoutoverhang(chars))[0] // 2
                else:
                    if not antialias and 22 < info.fontpixels_noscale and\
                            fontface in ("ＭＳ Ｐ明朝", "ＭＳ 明朝", "ＭＳ Ｐゴシック", "ＭＳ ゴシック", "MS UI Gothic"):
                        # cwconv.dllのバグで常にアンチエイリアスがかかる
                        antialias2 = True
                    else:
                        antialias2 = antialias

                    subimg = info.font.render(chars, antialias2, info.fontcolor)
                    if cw.UP_SCR == 1.0:
                        width = info.font.size_withoutoverhang(chars)[0]
                    else:
                        # 1倍で描画した時のサイズに合せる
                        size = cw.s(info.font_noscale.size(chars))
                        subimg = cw.image.smoothscale(subimg, size, smoothing=antialias2)
                        width = cw.s(info.font_noscale.size_withoutoverhang(chars))[0]
                    yp = cw.s(1)

                # 取消線
                if info.strike:
                    subimg2 = info.font.render("―", False, info.fontcolor)
                    size = (int(width + cw.s(10)), info.get_height())
                    subimg2 = pygame.transform.scale(subimg2, size)
                    subimg.blit(subimg2, cw.s((-5, 0)))

                self.outer.image.blit(subimg, (int(info.x), int(info.y)+yp))
                info.x = info.x + width
                info.w = int(info.x) if info.x > info.w else info.w

            def calc_lineheight(self) -> float:
                return self.fontpixels * self.lineheight / 100.0

        info = Info(self, lineheight, fontface, fontpixels, fontpixels_noscale, fontcolor)
        face_def = fontface
        color_def = fontcolor

        i = 0
        while i < len(text):
            char = text[i]
            if char == "\n":
                info.render()
                info.x = 0
                if info.nolinedata or not info.tagonly:
                    info.y = info.y + info.calc_lineheight()
                info.h = int(info.y)
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

                if name == "br":
                    info.render()
                    info.x = 0
                    info.y = info.y + info.calc_lineheight()
                    info.h = int(info.y)
                    info.nolinedata = True
                    info.tagonly = True
                    if i+1 < len(text) and text[i+1] == "\n":
                        i += 1
                elif name == "b":
                    bold = start
                    info.font.set_bold(start)
                    info.font2.set_bold(start)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_bold(start)
                        info.font2_noscale.set_bold(start)
                elif name == "u":
                    underline = start
                    info.font.set_underline(start)
                    info.font2.set_underline(start)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_underline(start)
                        info.font2_noscale.set_underline(start)
                elif name == "i":
                    italic = start
                    info.font.set_italic(start)
                    info.font2.set_italic(start)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_italic(start)
                        info.font2_noscale.set_italic(start)
                elif name == "s":
                    info.strike = start
                elif name == "shiftx":
                    if start:
                        n = cw.s(int(attrs["shiftx"]))
                        info.x += n
                elif name == "shifty":
                    if start:
                        n = cw.s(int(attrs["shifty"]))
                        info.y = info.y + n
                elif name == "lineheight":
                    info.lineheight = int(attrs["lineheight"])
                # 本家エフェクトブースターは"<fontcolor="blue">"のようなタグを、
                # タグ名=font, 属性color=blueという用に認識してしまうため注意。
                elif name.startswith("font"):
                    if start:
                        info.oldfonts.append((info.fontface, info.fontpixels, info.fontpixels_noscale, info.fontcolor))
                        if "fontpixels" in attrs:
                            info.fontpixels_noscale = int(attrs["fontpixels"])
                            info.fontpixels = cw.s(info.fontpixels_noscale)
                        if "pixels" in attrs:
                            info.fontpixels_noscale = int(attrs["pixels"])
                            info.fontpixels = cw.s(info.fontpixels_noscale)
                        info.fontface = attrs.get("fontface", face_def)
                        info.fontface = attrs.get("face", info.fontface)
                        info.create_font()
                        color_s = attrs.get("fontcolor")
                        color_s = attrs.get("color", color_s)
                        if color_s:
                            info.fontcolor = self.get_fontcolor(color_s, color_def)
                    else:
                        info.fontface, info.fontpixels, info.fontpixels_noscale, color = info.oldfonts.pop()
                        info.create_font()
                        info.fontcolor = color
                    info.font.set_bold(bold)
                    info.font2.set_bold(bold)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_bold(bold)
                        info.font2_noscale.set_bold(bold)
                    info.font.set_italic(italic)
                    info.font2.set_italic(italic)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_italic(italic)
                        info.font2_noscale.set_italic(italic)
                    info.font.set_underline(underline)
                    info.font2.set_underline(underline)
                    if cw.UP_SCR != 1.0:
                        info.font_noscale.set_underline(underline)
                        info.font2_noscale.set_underline(underline)

                info.tag = ""
            elif info.tag:
                info.render()
                info.tag += char
            else:
                info.chars.append(char)
                info.nolinedata = False
                info.tagonly = False
            i += 1

        if info.chars or not info.nolinedata:
            info.render()
            if info.nolinedata or not info.tagonly:
                info.y = info.y + info.calc_lineheight()
                info.h = int(info.y)

        if backheight < 0 or backwidth < 0:
            info.w = info.w if backwidth < 0 else backwidth
            info.h = info.h if backheight < 0 else backheight
            rect = self.image.get_rect()
            self.image = self.image.subsurface(rect.clip(pygame.Rect(0, 0, info.w, info.h)))

    def get_fontcolor(self, fontcolor: str, default: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
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

    def parse_tag(self, tag: str) -> Tuple[bool, str, Dict[str, str]]:
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
        attrs: Dict[str, str] = {}

        for group in groups:
            key, value = group.split("=")
            attrs[key.strip()] = value.strip(" \"\'")

        return start, name, attrs


class EffectBoosterConfig(object):
    def __init__(self, path: str, firstsection: str, section_ignorecase: bool = True) -> None:
        self.path = path
        self.dirdepth = 0
        r_sec = re.compile(r'\[([^]]+)]')
        r_opt = re.compile(r'([^:=\s][^:=]*)\s*[:=]\s*(.*)$')
        self._orderedsecs = []
        self._sections = {}
        cur_sec: Dict[str, str] = {}
        jptxtxt = []
        in_jptxtxt = False
        ext = cw.util.splitext(path)[1].lower()

        with open(path, "rb") as f:

            for line_b in f:
                if not in_jptxtxt and line_b[0:1] in b'#;':
                    continue

                line = str(line_b, cw.MBCS, "replace").replace("\r\n", "\n")
                lline = line.lower()
                sline = lline.strip()

                # jptxテキスト
                if sline == "[jptx:end]":
                    in_jptxtxt = False
                    break
                elif sline == "[jptx:begin]":
                    in_jptxtxt = True
                    jptxtxt.append("")
                    continue
                elif in_jptxtxt:
                    jptxtxt.append(line)
                    continue

                # セクション
                m = r_sec.match(sline)

                if m:
                    if section_ignorecase:
                        sec = m.group(1).strip().lower()
                    else:
                        sec = m.group(1)
                    cur_sec = {}
                    # 互換動作: セクション名が重複した時、セクションの内容が上書きされて
                    #           同一のセクションが複数回実行されるような挙動が発生するが、
                    #           1.30以前では後に定義されたセクションが、
                    #           1.50では先に定義されたセクションが複数回実行される
                    if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
                        self._sections[sec] = cur_sec
                    else:
                        if sec not in self._sections:
                            self._sections[sec] = cur_sec
                    self._orderedsecs.append(sec)
                    continue

                # オプション
                m = r_opt.match(line.lstrip())

                if m:
                    opt = m.group(1).strip().lower()
                    val = m.group(2).strip()
                    if val.startswith('"') and val.startswith('"'):
                        val = val[1:-1]
                    # BUG: セクション内でコマンドが重複した時、
                    #      JPY1は先の定義が優先だがJPTXは後が優先？
                    if opt not in cur_sec or ext == ".jptx":
                        cur_sec[opt] = val
                    continue
            f.close()

        if jptxtxt:
            self._sections["jptx:begin"] = {"jptx:end": "".join(jptxtxt)}

        if not self._sections and firstsection != "":
            cur_sec = {}
            self._sections[firstsection] = cur_sec
            self._orderedsecs.append(firstsection)

    def sections(self) -> List[str]:
        return self._orderedsecs

    def has_section(self, name: str) -> bool:
        return name in self._sections

    @typing.overload
    def get(self, section: str, option: str, default: str) -> str: ...

    @typing.overload
    def get(self, section: str, option: str, default: None) -> Optional[str]: ...

    def get(self, section: str, option: str, default: Optional[str] = None) -> Optional[str]:
        sec = self._sections.get(section, None)

        if sec is not None:
            result: Optional[str] = sec.get(option.lower(), default)
            return result
        else:
            return default

    @typing.overload
    def get_int(self, section: str, option: str, default: int) -> int: ...

    @typing.overload
    def get_int(self, section: str, option: str, default: None) -> Optional[int]: ...

    def get_int(self, section: str, option: str, default: Optional[int] = None) -> Optional[int]:
        try:
            s = self.get(section, option, None)
            if s is None:
                return default
            value = s.strip()
            if value.endswith("px"):
                return int(value[:-2])
            return int(value)
        except ValueError:
            return default

    def get_bool(self, section: str, option: str, default: bool) -> bool:
        return bool(self.get_int(section, option, 1 if default else 0))

    @typing.overload
    def get_color(self, section: str, option: str, default: Tuple[int, int, int]) -> Tuple[int, int, int]: ...

    @typing.overload
    def get_color(self, section: str, option: str, default: None) -> Optional[Tuple[int, int, int]]: ...

    def get_color(self, section: str, option: str,
                  default: Optional[Tuple[int, int, int]] = None) -> Optional[Tuple[int, int, int]]:
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
            s = self.get(section, option, None)
            if s is None:
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

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[2],
                 default: Tuple[int, int]) -> Tuple[int, int]: ...

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[2],
                 default: None) -> Optional[Tuple[int, int]]: ...

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[3],
                 default: Tuple[int, int, int]) -> Tuple[int, int, int]: ...

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[3],
                 default: None) -> Optional[Tuple[int, int, int]]: ...

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[4],
                 default: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]: ...

    @typing.overload
    def get_ints(self, section: str, option: str, length: Literal[4],
                 default: None) -> Optional[Tuple[int, int, int, int]]: ...

    def get_ints(self, section: str, option: str, length: int,
                 default: Optional[Tuple[int, ...]] = None) -> Optional[Tuple[int, ...]]:
        try:
            s = self.get(section, option, None)
            if s is None:
                return default

            seq = []
            for i in s.split(","):
                try:
                    seq.append(int(i.strip()))
                except ValueError:
                    seq.append(0)

            if length <= len(seq):
                return tuple(seq[:length])
            else:
                raise ValueError()

        except ValueError:
            return default


def main() -> None:
    pass


if __name__ == "__main__":
    main()
