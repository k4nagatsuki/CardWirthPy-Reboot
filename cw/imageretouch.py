#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes

import wx
import pygame
import pygame.surface
from pygame import BLEND_ADD, BLEND_SUB, BLEND_MULT, BLEND_RGB_ADD, BLEND_RGB_SUB, BLEND_RGBA_ADD, BLEND_RGBA_SUB,\
                   BLEND_RGBA_MULT, RLEACCEL, SRCALPHA

import cw

import typing
from typing import Callable, Dict, Optional, Tuple, TypeVar


try:
    if sys.platform == "darwin":
        from . import _imageretouch_mac
    elif sys.maxsize == 0x7fffffff:
        from . import _imageretouch32
    elif sys.maxsize == 0x7fffffffffffffff:
        from . import _imageretouch64
except ImportError as ex:
    print("failed to load _imageretouch module. %s" % (ex))


_RetouchArg1 = TypeVar("_RetouchArg1")
_RetouchArg2 = TypeVar("_RetouchArg2")
_RetouchArg3 = TypeVar("_RetouchArg3")


@typing.overload
def _retouch(func: Callable[[str, Tuple[int, int]], bytes],
             image: pygame.surface.Surface) -> pygame.surface.Surface: ...


@typing.overload
def _retouch(func: Callable[[str, Tuple[int, int], _RetouchArg1], bytes], image: pygame.surface.Surface,
             __arg1: _RetouchArg1) -> pygame.surface.Surface: ...


@typing.overload
def _retouch(func: Callable[[str, Tuple[int, int], _RetouchArg1, _RetouchArg2], bytes], image: pygame.surface.Surface,
             __arg1: _RetouchArg1, __arg2: _RetouchArg2) -> pygame.surface.Surface: ...


@typing.overload
def _retouch(func: Callable[[str, Tuple[int, int], _RetouchArg1, _RetouchArg2, _RetouchArg3], bytes],
             image: pygame.surface.Surface, __arg1: _RetouchArg1, __arg2: _RetouchArg2,
             __arg3: _RetouchArg3) -> pygame.surface.Surface: ...


def _retouch(func: Callable[..., bytes], image: pygame.surface.Surface, *args: typing.Any) -> pygame.surface.Surface:
    """_imageretouchの関数のラッパ。
    func: _imageretouchの関数オブジェクト。
    image: 対象イメージ
    *args: その他の引数
    """
    w, h = image.get_size()

    if not w or not h:
        return image.copy()

    s = pygame.image.tostring(image, "RGBA")
    buf = func(s, (w, h), *args)

    if image.get_flags() & SRCALPHA:
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()
    elif image.get_alpha():
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBX").convert_alpha()
        alpha = image.get_alpha()
        assert alpha is not None
        outimage.set_alpha(alpha, RLEACCEL)
    else:
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBX").convert()

    if image.get_colorkey():
        outimage.set_colorkey(outimage.get_at((0, 0)), RLEACCEL)

    return outimage


def to_negative(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """色反転したpygame.surface.Surfaceを返す。
    image: 対象イメージ
    """
    outimage = image.copy()

    if image.get_flags() & SRCALPHA:
        outimage.fill((255, 255, 255), special_flags=BLEND_RGB_ADD)
    else:
        outimage.fill((255, 255, 255))

    outimage.blit(image, (0, 0), None, BLEND_RGB_SUB)
    return outimage


def to_negative_for_card(image: pygame.surface.Surface, framewidth: int = 0) -> pygame.surface.Surface:
    """色反転したpygame.surface.Surfaceを返す。
    カード画像用なので外枠nピクセルは色反転しない。
    image: 対象イメージ
    framewidth: 外枠の幅。現在は1.50に合わせて外枠無し(0)
    """
    w, h = image.get_size()

    if w < cw.s(1 + framewidth*2) or h < cw.s(1 + framewidth*2):
        return image.copy()

    rect = pygame.rect.Rect(cw.s((framewidth, framewidth)), (w - cw.s(framewidth*2), h - cw.s(framewidth*2)))
    outimage = image.copy()

    if image.get_flags() & SRCALPHA:
        outimage.fill((255, 255, 255), rect, BLEND_RGB_ADD)
    else:
        outimage.fill((255, 255, 255), rect)

    outimage.blit(image.subsurface(rect), cw.s((framewidth, framewidth)), None, BLEND_RGB_SUB)
    return outimage


def to_negative_for_wxcard(wxbmp: wx.Bitmap, framewidth: int = 0) -> wx.Bitmap:
    """色反転したwx.Bitmapを返す。
    カード画像用なので外枠1ピクセルは色反転しない。
    wxbmp: 対象イメージ
    framewidth: 外枠の幅。現在は1.50に合わせて外枠無し(0)
    """
    w, h = wxbmp.GetWidth(), wxbmp.GetHeight()

    dc = wx.MemoryDC()
    image = cw.util.empty_bitmap(w, h)
    dc.SelectObject(image)
    dc.DrawBitmap(wxbmp, cw.wins(0), cw.wins(0))
    if cw.wins(1 + framewidth*2) <= w and cw.wins(1 + framewidth*2) <= h:
        x, y, w, h = wx.Rect(cw.wins(framewidth), cw.wins(framewidth),
                             w - cw.wins(framewidth*2), h - cw.wins(framewidth*2))
        subbmp = wxbmp.GetSubBitmap(wx.Rect(x, y, w, h))
        buf_bytes = cw.util.wxbmp_to_buffer(subbmp)
        buf = bytearray(buf_bytes)
        if sys.platform == "darwin":
            _imageretouch_mac.to_negative(buf, (w, h))
        elif sys.maxsize == 0x7fffffff:
            _imageretouch32.to_negative(buf, (w, h))
        elif sys.maxsize == 0x7fffffffffffffff:
            _imageretouch64.to_negative(buf, (w, h))
        else:
            buf = bytearray([255-a for a in buf])
        wximg = wx.ImageFromBuffer(w, h, buf)
        subbmp = wx.Bitmap(wximg)
        dc.DrawBitmap(subbmp, x, y)

    dc.SelectObject(wx.NullBitmap)
    return image


def add_lightness(image: pygame.surface.Surface, value: int) -> pygame.surface.Surface:
    """明度を調整する。
    image: 対象イメージ
    value: 明暗値(-255～255)
    """
    value = cw.util.numwrap(value, -255, 255)
    if value == -255 or value == 255:
        outimage = image.convert()
    else:
        outimage = image.copy()

    if value < 0:
        spcflag = BLEND_RGB_SUB
        value = - value
    else:
        spcflag = BLEND_RGB_ADD

    outimage.fill((value, value, value), special_flags=spcflag)
    return outimage


def add_mosaic(image: pygame.surface.Surface, value: int) -> pygame.surface.Surface:
    """モザイクをかける。
    image: 対象イメージ
    value: モザイクをかける度合い(0～255)
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.add_mosaic
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.add_mosaic
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.add_mosaic
    else:
        return image

    return _retouch(func, image, value)


def to_binaryformat(image: pygame.surface.Surface, value: int,
                    basecolor: Tuple[int, int, int] = (255, 255, 255)) -> pygame.surface.Surface:
    """二値化する。
    image: 対象イメージ
    value: 閾値(-1～255)。-1の場合はbasecolor以外が黒になる
    basecolor: 閾値が-1の時に使用され、この色以外が黒になる
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.to_binaryformat
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.to_binaryformat
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.to_binaryformat
    else:
        return image

    return _retouch(func, image, value, basecolor)


def add_noise(image: pygame.surface.Surface, value: int, colornoise: bool = False) -> pygame.surface.Surface:
    """ノイズを入れる。
    image: 対象イメージ
    value: ノイズの度合い(-1～255)
    colornoise: カラーノイズか否か
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.add_noise
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.add_noise
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.add_noise
    else:
        return image

    return _retouch(func, image, value, colornoise)


def exchange_rgbcolor(image: pygame.surface.Surface, colormodel: str) -> pygame.surface.Surface:
    """RGB入れ替えしたpygame.surface.Surfaceを返す。
    image: 対象イメージ
    colormodel: "r", "g", "b"を組み合わせた文字列。
    """
    colormodel = colormodel.lower()

    if sys.platform == "darwin":
        func = _imageretouch_mac.exchange_rgbcolor
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.exchange_rgbcolor
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.exchange_rgbcolor
    else:
        return image

    return _retouch(func, image, colormodel)


def to_grayscale(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """グレイスケール化したpygame.surface.Surfaceを返す。
    image: 対象イメージ
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.to_sepiatone
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.to_sepiatone
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.to_sepiatone
    else:
        return image

    return _retouch(func, image, (0, 0, 0))


def to_sepiatone(image: pygame.surface.Surface, color: Tuple[int, int, int] = (30, 0, -30)) -> pygame.surface.Surface:
    """褐色系の画像に変換したpygame.surface.Surfaceを返す。
    image: 対象イメージ
    color: グレイスケール化した画像に付加する色。(r, g, b)のタプル
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.to_sepiatone
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.to_sepiatone
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.to_sepiatone
    else:
        return image

    return _retouch(func, image, color)


def spread_pixels(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """ピクセル拡散させたpygame.surface.Surfaceを返す。
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.spread_pixels
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.spread_pixels
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.spread_pixels
    else:
        return image

    return _retouch(func, image)


def _filter(image: pygame.surface.Surface,
            weight: Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]],
            offset: int = 0, div: int = 1) -> pygame.surface.Surface:
    """フィルタを適用する。
    weight: 重み付け係数。
    offset: オフセット(整数)
    div: 除数(整数)
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.filter
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.filter
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.filter
    else:
        return image

    return _retouch(func, image, weight, offset, div)


def filter_shape(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にぼかしフィルターを適用。"""
    weight = (
        (1, 1, 1),
        (1, 1, 1),
        (1, 1, 1)
    )
    offset = 0
    div = 9
    return _filter(image, weight, offset, div)


def filter_sharpness(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にシャープフィルターを適用。"""
    weight = (
        (-1, -1, -1),
        (-1, 24, -1),
        (-1, -1, -1)
    )
    offset = 0
    div = 16
    return _filter(image, weight, offset, div)


def filter_sunpower(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にサンパワーフィルターを適用。"""
    weight = (
        (1, 3, 1),
        (3, 5, 3),
        (1, 3, 1)
    )
    offset = 0
    div = 16
    return _filter(image, weight, offset, div)


def filter_emboss(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にエンボスフィルターを適用。"""
    image = to_grayscale(image)
    weight = (
        (-1, 0, 0),
        (0, 1, 0),
        (0, 0, 0)
    )
    offset = 128
    div = 1
    return _filter(image, weight, offset, div)


def filter_coloremboss(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にカラーエンボスフィルターを適用。"""
    weight = (
        (-1, -1, -1),
        (0, 1, 0),
        (1, 1, 1)
    )
    offset = 0
    div = 1
    return _filter(image, weight, offset, div)


def filter_darkemboss(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にダークエンボスフィルターを適用。"""
    weight = (
        (-1, -2, -1),
        (0, 0, 0),
        (1, 2, 1)
    )
    offset = 128
    div = 1
    return _filter(image, weight, offset, div)


def filter_electrical(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """画像にエレクトリカルフィルターを適用。"""
    weight = (
        (1, 1, 1),
        (1, -15, 1),
        (1, 1, 1)
    )
    offset = 0
    div = 1
    return _filter(image, weight, offset, div)


def add_transparentline(image: pygame.surface.Surface, vline: bool, hline: bool,
                        rect: Optional[Tuple[int, int, int, int]] = None,
                        setalpha: bool = False) -> pygame.surface.Surface:
    """透明色ラインを入れる。
    vline: bool値。Trueなら縦線を入れる。
    hline: bool値。Trueなら横線を入れる。
    """
    w, h = image.get_size()
    if not rect:
        rect = (0, 0, w, h)
    image = image.convert_alpha()
    color = image.get_at((0, 0))
    if setalpha:
        color = (color[0], color[1], color[2], 0)

    x0, y0, w, h = rect
    if vline:
        for cnt in range(w // 2 - 1):
            x = cnt * 2 + x0
            pygame.draw.line(image, color, (x, 0), (x, h))

    if hline:
        for cnt in range(h // 2 - 1):
            y = cnt * 2 + y0
            pygame.draw.line(image, color, (0, y), (w, y))

    return image


def add_transparentmesh(image: pygame.surface.Surface, rect: Optional[Tuple[int, int, int, int]] = None,
                        setalpha: bool = False) -> pygame.surface.Surface:
    """透明色の網の目を入れる。
    """
    w, h = image.get_size()
    if not rect:
        rect = (0, 0, w, h)
    image = image.convert_alpha()
    color = image.get_at((0, 0))
    if setalpha:
        color = (color[0], color[1], color[2], 0)

    clip = image.get_clip()
    image.set_clip(pygame.rect.Rect(rect))
    x0, y0, w, h = rect
    for cnt in range(0, w + h, 2):
        pos1 = (x0 + cnt, y0)
        pos2 = (x0 + cnt - h, y0 + h)
        pygame.draw.line(image, color, pos1, pos2)

    image.set_clip(clip)
    return image


def add_border(img: pygame.surface.Surface, bordercolor: Tuple[int, int, int], borderwidth: int) -> None:
    """textcolorの領域を縁取りする。
    この処理はwxPythonのインスタンスに対して行う。
    img: 描画対象。
    bordercolor: 縁取り色(R,G,B)。
    borderwidth: 縁取りの太さ。
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.bordering
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.bordering
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.bordering
    else:
        return

    buf = pygame.image.tostring(img, "RGBA")
    points = func(buf, img.get_size())
    hbw = borderwidth // 2
    for i in range(0, len(points), 2):
        x = points[i+0]
        y = points[i+1]
        if borderwidth == 1:
            img.set_at((x, y), bordercolor)
        elif borderwidth == 2:
            img.fill(bordercolor, pygame.rect.Rect(x - 1, y - 1, 2, 2))
        else:
            pygame.draw.ellipse(img, bordercolor, pygame.rect.Rect(x - hbw, y - hbw, borderwidth, borderwidth))


def blend_1_50(dest: pygame.surface.Surface, pos: Tuple[int, int], source: pygame.surface.Surface, flag: int) -> None:
    """CardWirth 1.50の挙動に合わせて加算または減算合成を行う。
    dest: 合成先のイメージ。
    pos: 合成位置。
    image: 合成するイメージ。
    flag: BLEND_ADDまたはBLEND_SUBまたはBLEND_MULT
    """
    w, h = source.get_size()

    clip = dest.get_clip()
    if not clip:
        clip = dest.get_rect()

    rect = pygame.rect.Rect(pos, (w, h))
    rect = pygame.rect.Rect(clip.topleft, clip.size).clip(rect)
    if rect.w <= 0 or rect.h <= 0:
        return

    sub = dest.subsurface(rect)

    pos2 = (max(0, -pos[0] + clip.left), max(0, -pos[1] + clip.top))
    rect2 = pygame.rect.Rect(pos2, rect.size)
    source2 = source.subsurface(rect2)

    func: Callable[[str, Tuple[int, int], str], bytes]
    if flag in (BLEND_ADD, BLEND_RGBA_ADD):
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_add_1_50
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_add_1_50
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_add_1_50
        else:
            return
    elif flag in (BLEND_SUB, BLEND_RGBA_SUB):
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_sub_1_50
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_sub_1_50
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_sub_1_50
        else:
            return
    elif flag in (BLEND_MULT, BLEND_RGBA_MULT):
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_mult_1_50
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_mult_1_50
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_mult_1_50
        else:
            return
    else:
        assert False

    sbuf = pygame.image.tostring(source2, "RGBA")
    outimage = _retouch(func, sub, sbuf)

    dest.blit(outimage, rect.topleft, None, 0)


def to_disabledimage(wxbmp: wx.Bitmap, maskpos: Tuple[int, int] = (0, 0)) -> wx.Bitmap:
    """
    通常時のボタン画像からdisabled用の画像を作る。
    RGB値の範囲を 0～255 から min～max に変更する。
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.to_disabledimage
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.to_disabledimage
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.to_disabledimage
    else:
        func = _to_disabledimage

    wximg = wxbmp.ConvertToImage().ConvertToGreyscale()
    buf = wximg.GetDataBuffer()
    buf = bytearray(buf)
    w = wximg.GetWidth()
    h = wximg.GetHeight()
    func(buf, (w, h))

    wximg = wx.ImageFromBuffer(w, h, buf)
    wxbmp = wx.Bitmap(wximg)
    x, y = maskpos
    wxbmp.SetMaskColour((wximg.GetRed(x, y), wximg.GetGreen(x, y), wximg.GetBlue(x, y)))
    return wxbmp


def _to_disabledimage(buf: bytearray, size: Tuple[int, int]) -> None:
    """
    通常時のボタン画像からdisabled用の画像を作る
    グレイスケール処理後、RGB値の範囲を 0～255 から min～max に変更
    """
    # 最終的なRGB値の範囲を設定
    nmin, nmax = 140, 240

    colorkey = (buf[0], buf[1], buf[2])

    for px in range(0, len(buf), 3):
        if (buf[px], buf[px+1], buf[px+2]) != colorkey:
            buf[px+0] = buf[px+0] * (nmax - nmin) // 255 + nmin
            buf[px+1] = buf[px+1] * (nmax - nmin) // 255 + nmin
            buf[px+2] = buf[px+2] * (nmax - nmin) // 255 + nmin


def to_disabledsurface(image: pygame.surface.Surface) -> pygame.surface.Surface:
    """_to_disabledimage()のpygame.surface.Surface版。"""
    image = image.copy()
    image.fill((128, 128, 128), special_flags=pygame.BLEND_RGB_ADD)
    return to_grayscale(image)


def add_lightness_for_wxbmp(wxbmp: wx.Bitmap, lightness: int, maskpos: Tuple[int, int] = (0, 0)) -> wx.Bitmap:
    """イメージに明るさを加える。
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.add_lightness
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.add_lightness
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.add_lightness
    else:
        func = _add_lightness

    wximg = wxbmp.ConvertToImage().ConvertToGreyscale()
    buf = wximg.GetDataBuffer()
    alphabuf = wximg.GetAlphaBuffer()
    buf = bytearray(buf)
    w = wximg.GetWidth()
    h = wximg.GetHeight()
    func(buf, (w, h), lightness)

    wximg = wx.ImageFromBuffer(w, h, buf, alphaBuffer=bytearray(alphabuf) if alphabuf else None)
    wxbmp = wx.Bitmap(wximg)
    x, y = maskpos
    wxbmp.SetMaskColour((wximg.GetRed(x, y), wximg.GetGreen(x, y), wximg.GetBlue(x, y)))
    return wxbmp


def _add_lightness(buf: bytearray, size: Tuple[int, int], lightness: int) -> None:
    (w, h) = size
    for i, v in enumerate(buf):
        buf[i] = cw.util.numwrap(v + lightness, 0, 255)


def hex2color(hexnum: int) -> Tuple[int, int, int]:
    """RGBデータの16進数を(r, g, b)のタプルで返す。
    hexnum: 16進数。
    """
    b = int(hexnum & 0xFF)
    g = int((hexnum >> 8) & 0xFF)
    r = int((hexnum >> 16) & 0xFF)
    return r, g, b


def colorwrap(num: int) -> int:
    """numを0～255の値に丸める。"""
    return cw.util.numwrap(num, 0, 255)


def decode_rle4data(data: bytes, h: int, bpl: int) -> bytes:
    """Windows BitmapのRLE4データをデコードする。
    """
    if sys.platform == "darwin":
        func = _imageretouch_mac.decode_rle4data
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.decode_rle4data
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.decode_rle4data
    else:
        raise ValueError()
    return func(data, h, bpl)


def patch_alphadata(image: pygame.surface.Surface, ext: str, data: bytes) -> pygame.surface.Surface:
    """CardWirthのビットマップデコーダは、32ビットイメージの
    各ピクセルの4バイト中、予備領域に1件でも0以外のデータがある時に限り
    予備領域をアルファ値として使用するので、それに合わせる。
    PNGイメージの場合は全て255の場合にアルファ無しと見なす。
    """
    if image.get_bitsize() == 32:
        buf = pygame.image.tostring(image, "RGBA")
        assert len(buf) % 4 == 0

        ext = ext.lower()
        if ext == ".bmp":
            if sys.platform == "darwin":
                has_alpha = _imageretouch_mac.has_alphabmp32
            elif sys.maxsize == 0x7fffffff:
                has_alpha = _imageretouch32.has_alphabmp32
            elif sys.maxsize == 0x7fffffffffffffff:
                has_alpha = _imageretouch64.has_alphabmp32
            else:
                raise ValueError()
        else:
            if sys.platform == "darwin":
                has_alpha = _imageretouch_mac.has_alpha
            elif sys.maxsize == 0x7fffffff:
                has_alpha = _imageretouch32.has_alpha
            elif sys.maxsize == 0x7fffffffffffffff:
                has_alpha = _imageretouch64.has_alpha
            else:
                raise ValueError()

        if (ext == ".bmp" and cw.image.get_bicompression(data) == 3) or not has_alpha(buf):
            # アルファ値が存在しないので予備領域を無視
            # CW 1.50ではビットフィールド方式のイメージも
            # α値が無視されるのでそれにも合わせる
            image = pygame.image.fromstring(buf, image.get_size(), "RGBX")
    return image


def mul_wxalpha(wximg: wx.Image, alpha: int) -> wx.Image:
    """alpha/255分まで、wximgのアルファ値を減少させる。"""
    if not wximg.HasAlpha():
        wximg.InitAlpha()
    buf = wximg.GetAlphaBuffer()
    assert len(buf) == wximg.GetWidth() * wximg.GetHeight()
    buf = bytearray(buf)
    if sys.platform == "darwin":
        func = _imageretouch_mac.mul_alphaonly
    elif sys.maxsize == 0x7fffffff:
        func = _imageretouch32.mul_alphaonly
    elif sys.maxsize == 0x7fffffffffffffff:
        func = _imageretouch64.mul_alphaonly
    else:
        raise ValueError()
    func(buf, alpha)
    wximg.SetAlphaBuffer(buf)
    return wximg


def mul_alpha(image: pygame.surface.Surface, alpha: int) -> pygame.surface.Surface:
    """alpha/255分まで、imageのアルファ値を減少させる。"""
    image.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return image


def blit_2bitbmp_to_card(dest: pygame.surface.Surface, source: pygame.surface.Surface, pos: Tuple[int, int]) -> None:
    """
    CardWirthの「2bit ビットマップイメージが
    半透明で表示される」バグをある程度再現する。
    ただしこのバグはtarget側の色の値が2の乗数の時に
    演算結果がおかしくなって表示が乱れるという
    さらなる問題を抱えているので、正確に再現はせず、
    より直感に合った描画を行う。
    """
    if source.get_colorkey() and isinstance(source, cw.util.Depth1Surface) and source.bmpdepthis1:
        w, h = source.get_size()
        rect = pygame.rect.Rect(pos, (w, h))
        rect = pygame.rect.Rect((0, 0), dest.get_size()).clip(rect)
        if rect.w <= 0 or rect.h <= 0:
            return

        sub = dest.subsurface(rect)
        rect2 = pygame.rect.Rect((max(0, -pos[0]), max(0, -pos[1])), rect.size)
        source2 = source.subsurface(rect2)

        func: Optional[Callable[[str, Tuple[int, int], str], bytes]]
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_and
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_and
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_and
        else:
            func = None

        if func:
            sbuf = pygame.image.tostring(source2, "RGBA")
            outimage = _retouch(func, sub, sbuf)
        else:
            dest.blit(source, pos)
            return

        dest.blit(outimage, rect.topleft, None, 0)
        return

    dest.blit(source, pos)


def blit_2bitbmp_to_message(dest: pygame.surface.Surface, source: pygame.surface.Surface, pos: Tuple[int, int],
                            wincolour: Tuple[int, int, int, int]) -> None:
    if source.get_colorkey() and isinstance(source, cw.util.Depth1Surface) and source.bmpdepthis1:
        w, h = source.get_size()
        rect = pygame.rect.Rect(pos, (w, h))
        rect = pygame.rect.Rect((0, 0), dest.get_size()).clip(rect)
        if rect.w <= 0 or rect.h <= 0:
            return

        sub = dest.subsurface(rect)
        rect2 = pygame.rect.Rect((max(0, -pos[0]), max(0, -pos[1])), rect.size)
        source2 = source.subsurface(rect2)

        func: Optional[Callable[[str, Tuple[int, int], str, Tuple[int, int, int, int]], bytes]]
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_and_msg
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_and_msg
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_and_msg
        else:
            func = None

        if func:
            sbuf = pygame.image.tostring(source2, "RGBA")
            outimage = _retouch(func, sub, sbuf, wincolour)
        else:
            dest.blit(source, pos)
            return

        dest.blit(outimage, rect.topleft)
        return

    dest.blit(source, pos)


def wxblit_2bitbmp_to_card(dc: wx.MemoryDC, dest: wx.Bitmap, wxbmp: wx.Bitmap, x: int, y: int, useMask: bool,
                           bitsizekey: Optional[wx.Bitmap] = None) -> None:
    """
    blit_2bitbmp_to_card()のwx版。
    """
    assert isinstance(dc, wx.MemoryDC)
    if bitsizekey is None:
        bitsizekey = wxbmp

    if useMask and hasattr(bitsizekey, "bmpdepthis1"):
        dw = dest.GetWidth()
        dh = dest.GetHeight()
        drect = wx.Rect(0, 0, dw, dh)
        crect = dc.GetClippingRect()
        if 0 < crect.Width and 0 < crect.Height:
            drect = drect.Intersect(crect)

        w, h = wxbmp.GetWidth(), wxbmp.GetHeight()
        rect = wx.Rect(x, y, w, h)
        rect = drect.Intersect(rect)
        if rect.Width <= 0 or rect.Height <= 0:
            return

        dc.SelectObject(wx.NullBitmap)

        if rect == wx.Rect(0, 0, dw, dh):
            sub = dest
        else:
            sub = dest.GetSubBitmap(rect)

        rect2 = wx.Rect(max(0, -x), max(0, -y), rect.Width, rect.Height)
        if rect2 == wx.Rect(0, 0, w, h):
            wxbmp2 = wxbmp
        else:
            wxbmp2 = wxbmp.GetSubBitmap(rect2)

        wximg = wxbmp2.ConvertToImage()
        if not wximg.HasAlpha():
            wximg.InitAlpha()
        buf1 = wximg.GetDataBuffer()
        alphabuf = wximg.GetAlphaBuffer()
        buf2 = cw.util.wxbmp_to_buffer(sub)

        dbuf = bytearray(buf2)
        buf = bytearray(buf1)
        assert len(dbuf) == len(buf)
        assert len(dbuf) == len(alphabuf)*3

        func: Optional[Callable[[bytearray, Tuple[int, int], bytearray], None]]
        if sys.platform == "darwin":
            func = _imageretouch_mac.blend_and_rgb
        elif sys.maxsize == 0x7fffffff:
            func = _imageretouch32.blend_and_rgb
        elif sys.maxsize == 0x7fffffffffffffff:
            func = _imageretouch64.blend_and_rgb
        else:
            func = None

        if func:
            func(dbuf, (w, h), buf)
        else:
            dbuf = bytearray([a_b[0] & a_b[1] for a_b in zip(buf, dbuf)])

        wximg = wx.ImageFromBuffer(rect.Width, rect.Height, dbuf, alphaBuffer=bytearray(alphabuf) if alphabuf else None)
        wxbmp = wx.Bitmap(wximg)
        dc.SelectObject(dest)
        dc.DrawBitmap(wxbmp, rect.X, rect.Y)

        return

    dc.DrawBitmap(wxbmp, x, y, useMask)


def _create_mfont(name: str, pixels: int, bold: bool, italic: bool,
                  sys: bool) -> Tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    if sys:
        if pixels < 0:
            # FIXME: CreateFont()で高さにマイナス値を指定した場合には
            #         行ではなく文字の高さでフォントが選択される
            pixels = -pixels
            pixels += 1
            font = pygame.sysfont.SysFont(name, pixels, bold, italic)
            h = font.get_height()
            if pixels < h:
                pixels = int(float(pixels) / h * pixels)
                font = pygame.sysfont.SysFont(name, pixels, bold, italic)
        else:
            pixels += 1
            font = pygame.sysfont.SysFont(name, pixels, bold, italic)
        font2x = pygame.sysfont.SysFont(name, pixels*2, bold, italic)
        font_notitalic = pygame.sysfont.SysFont(name, pixels, bold, italic)
    else:
        if pixels < 0:
            # FIXME: CreateFont()で高さにマイナス値を指定した場合には
            #         行ではなく文字の高さでフォントが選択される
            pixels = -pixels
            pixels += 1
            font = pygame.font.Font(name, pixels)
            h = font.get_height()
            if pixels < h:
                pixels = int(float(pixels) / h * pixels)
                font = pygame.font.Font(name, pixels)
        else:
            pixels += 1
            font = pygame.font.Font(name, pixels)
        font2x = pygame.font.Font(name, pixels*2)
        font_notitalic = pygame.font.Font(name, pixels)

    font.set_bold(bold)
    font.set_italic(italic)
    font2x.set_bold(bold)
    font2x.set_italic(italic)
    font_notitalic.set_bold(bold)

    return font, font2x, font_notitalic


class Font(object):
    font: Optional[pygame.font.Font]
    font2x: Optional[pygame.font.Font]
    font_notitalic: Optional[pygame.font.Font]
    fontinfo: Optional[ctypes.c_void_p]
    fontinfo2x: Optional[ctypes.c_void_p]
    _cache: Dict[Tuple[str, bool, Tuple[int, int, int]], pygame.surface.Surface]

    def __init__(self, face: str, pixels: int, bold: bool = False, italic: bool = False) -> None:
        self._cache = {}

        face = get_fontface(face)

        d = {("IPAゴシック", "IPAGothic"): "gothic.ttf",
             ("IPA UIゴシック", "IPAUIGothic"): "uigothic.ttf",
             ("IPA明朝", "IPAMincho"): "mincho.ttf",
             ("IPA P明朝", "IPAPMincho"): "pmincho.ttf",
             ("IPA Pゴシック", "IPAPGothic"): "pgothic.ttf"}
        for names, ttf in d.items():
            if face in names:
                path = cw.util.join_paths("Data/Font", ttf)
                if os.path.isfile(path):
                    self.font, self.font2x, self.font_notitalic = _create_mfont(path, pixels, bold, italic, sys=False)
                    return

        if sys.platform == "win32":
            func: Optional[Callable[[bytes, int, bool, bool], Optional[ctypes.c_void_p]]]
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_new
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_new
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_new
            else:
                func = None

            if func:
                self.font = None
                self.font2x = None
                self.font_notitalic = None
                self.face = face
                self.pixels = pixels
                self.bold = bold
                self.italic = italic
                self.underline = False
                self.fontinfo = func(face.encode("utf-8"), pixels, bold, italic)
                self.fontinfo2x = func(face.encode("utf-8"), pixels*2, bold, italic)
            else:
                self.font, self.font2x, self.font_notitalic = _create_mfont(face, pixels, bold, italic, sys=True)
        else:
            self.font, self.font2x, self.font_notitalic = _create_mfont(face, pixels, bold, italic, sys=True)

    def _is_cachable(self, s: str) -> bool:
        s = str(s)
        return len(s) == 1 and (('ぁ' <= s <= 'ヶ') or (0 <= ord(s) <= 255) or ('！' <= s <= 'ﾟ'))

    def dispose(self) -> None:
        if not self.font and self.fontinfo:
            assert self.fontinfo2x
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_del
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_del
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_del
            else:
                assert False
            func(self.fontinfo)
            func(self.fontinfo2x)
            self.fontinfo = None
            self.fontinfo2x = None
            self._cache = {}

    def __del__(self) -> None:
        if not self.font and self.fontinfo:
            assert self.fontinfo2x
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_del
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_del
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_del
            else:
                assert False
            func(self.fontinfo)
            func(self.fontinfo2x)
            self.fontinfo = None
            self.fontinfo2x = None
            self._cache = {}

    def get_bold(self) -> bool:
        if self.font:
            return self.font.get_bold()
        else:
            return self.bold

    def set_bold(self, v: bool) -> None:
        self._cache = {}
        if self.font:
            assert self.font2x
            assert self.font_notitalic
            self.font.set_bold(v)
            self.font2x.set_bold(v)
            self.font_notitalic.set_bold(v)
        else:
            assert self.fontinfo is not None
            assert self.fontinfo2x is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_bold
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_bold
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_bold
            else:
                assert False
            self.bold = v
            func(self.fontinfo, v)
            func(self.fontinfo2x, v)

    def get_italic(self) -> bool:
        if self.font:
            return self.font.get_italic()
        else:
            return self.italic

    def set_italic(self, v: bool) -> None:
        self._cache = {}
        if self.font:
            assert self.font2x
            self.font.set_italic(v)
            self.font2x.set_italic(v)
        else:
            assert self.fontinfo is not None
            assert self.fontinfo2x is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_italic
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_italic
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_italic
            else:
                assert False
            self.italic = v
            func(self.fontinfo, v)
            func(self.fontinfo2x, v)

    def get_underline(self) -> bool:
        if self.font:
            return self.font.get_underline()
        else:
            return self.underline

    def set_underline(self, v: bool) -> None:
        self._cache = {}
        if self.font:
            assert self.font2x
            assert self.font_notitalic
            self.font.set_underline(v)
            self.font2x.set_underline(v)
            self.font_notitalic.set_underline(v)
        else:
            assert self.fontinfo is not None
            assert self.fontinfo2x is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_underline
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_underline
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_underline
            else:
                assert False
            self.underline = v
            func(self.fontinfo, v)
            func(self.fontinfo2x, v)

    def get_height(self) -> int:
        if self.font:
            return self.font.get_height()
        elif sys.platform == "win32":
            if self.pixels < 0:
                return -self.pixels
            else:
                return self.pixels
        else:
            assert False

    def get_linesize(self) -> int:
        if self.font:
            return self.font.get_linesize()
        else:
            assert self.fontinfo is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_height
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_height
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_height
            else:
                assert False
            return func(self.fontinfo)

    def size(self, text: str) -> Tuple[int, int]:
        if self.font:
            return self.font.size(text)
        else:
            assert self.fontinfo is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_imagesize
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_imagesize
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_imagesize
            else:
                assert False
            return func(self.fontinfo, text.encode("utf-8"), False)

    def size_withoutoverhang(self, text: str) -> Tuple[int, int]:
        if self.font:
            assert self.font_notitalic
            return self.font_notitalic.size(text)
        else:
            assert self.fontinfo is not None
            if sys.platform == "darwin":
                func = _imageretouch_mac.font_size
            elif sys.maxsize == 0x7fffffff:
                func = _imageretouch32.font_size
            elif sys.maxsize == 0x7fffffffffffffff:
                func = _imageretouch64.font_size
            else:
                assert False
            return func(self.fontinfo, text.encode("utf-8"))

    def render(self, text: str, antialias: bool, colour: Tuple[int, int, int]) -> pygame.surface.Surface:
        return self._render_impl(text, antialias, colour, False)

    def render_sbold(self, text: str, antialias: bool, colour: Tuple[int, int, int]) -> pygame.surface.Surface:
        return self._render_impl(text, antialias, colour, True)

    def _render_impl(self, text: str, antialias: bool, colour: Tuple[int, int, int],
                     sbold: bool) -> pygame.surface.Surface:
        cachable = self._is_cachable(text)
        if cachable:
            key = (text, antialias, colour)
            if key in self._cache:
                return self._cache[key].copy()

        if self.font:
            assert self.font2x
            if antialias:
                image = self.font2x.render(text, antialias, colour)
                size = self.size(text)
                if sbold:
                    size2 = image.get_size()
                    size2 = (size2[0]+4, size2[1])
                    image2 = pygame.surface.Surface(size2).convert_alpha()
                    image2.fill((0, 0, 0, 0))
                    for x in range(4):
                        image2.blit(image, (x, 0))
                    image = image2
                    size = (size[0]+1, size[1])
                bmp = pygame.transform.smoothscale(image, size)
            else:
                bmp = self.font.render(text, antialias, colour)
                if sbold:
                    size = bmp.get_size()
                    size = (size[0]+1, size[1])
                    image2 = pygame.surface.Surface(size).convert_alpha()
                    image2.fill((0, 0, 0, 0))
                    image2.blit(bmp, (0, 0))
                    image2.blit(bmp, (1, 0))
                    bmp = image2
        elif antialias:
            assert self.fontinfo2x is not None
            assert self.fontinfo is not None
            if sys.platform == "darwin":
                font_imagesize = _imageretouch_mac.font_imagesize
                font_render = _imageretouch_mac.font_render
            elif sys.maxsize == 0x7fffffff:
                font_imagesize = _imageretouch32.font_imagesize
                font_render = _imageretouch32.font_render
            elif sys.maxsize == 0x7fffffffffffffff:
                font_imagesize = _imageretouch64.font_imagesize
                font_render = _imageretouch64.font_render
            else:
                assert False
            b_text = text.encode("utf-8")
            size = font_imagesize(self.fontinfo2x, b_text, antialias)
            buf = font_render(self.fontinfo2x, b_text, antialias, colour[:3])
            # BUG: Windows 10 1709で、フォント「游明朝」で「ーム」を含む文字列のサイズが
            #      ランダムに変動してしまう不具合を暫定的に回避する
            size = (len(buf) // size[1] // 4, size[1])
            assert len(buf) == size[0]*size[1]*4
            image = pygame.image.frombuffer(buf, size, "RGBA").convert_alpha()
            size2 = font_imagesize(self.fontinfo, b_text, antialias)
            if sbold:
                size = (size[0]+4, size[1])
                image2 = pygame.surface.Surface(size).convert_alpha()
                image2.fill((0, 0, 0, 0))
                for x in range(4):
                    image2.blit(image, (x, 0))
                image = image2
                size2 = (size2[0]+1, size2[1])

            bmp = pygame.transform.smoothscale(image, size2)
        else:
            assert self.fontinfo is not None
            if sys.platform == "darwin":
                font_imagesize = _imageretouch_mac.font_imagesize
                font_render = _imageretouch_mac.font_render
            elif sys.maxsize == 0x7fffffff:
                font_imagesize = _imageretouch32.font_imagesize
                font_render = _imageretouch32.font_render
            elif sys.maxsize == 0x7fffffffffffffff:
                font_imagesize = _imageretouch64.font_imagesize
                font_render = _imageretouch64.font_render
            else:
                assert False
            b_text = text.encode("utf-8")
            # BUG: font_render()からタプルを返そうとするとbufがGCで
            #      回収されなくなってしまうため、bufのみを返すようにし、
            #      (w, h)取得用にfont_imagesize()を用意してある
            # buf, size = font_render(self.fontinfo, str, antialias, colour[:3])
            size = font_imagesize(self.fontinfo, b_text, antialias)
            buf = font_render(self.fontinfo, b_text, antialias, colour[:3])
            # BUG: Windows 10 1709で、フォント「游明朝」で「ーム」を含む文字列のサイズが
            #      ランダムに変動してしまう不具合を暫定的に回避する
            size = (len(buf) // size[1] // 4, size[1])
            assert len(buf) == size[0]*size[1]*4
            bmp = pygame.image.frombuffer(buf, size, "RGBA").convert_alpha()
            if sbold:
                size = bmp.get_size()
                size = (size[0]+1, size[1])
                image2 = pygame.surface.Surface(size).convert_alpha()
                image2.fill((0, 0, 0, 0))
                image2.blit(bmp, (0, 0))
                image2.blit(bmp, (1, 0))
                bmp = image2

        if cachable:
            self._cache[key] = bmp.copy()
        return bmp


def get_fontface(fontface: str) -> str:
    """fontfaceが環境に無いフォントであれば
    差し替え用のフォント名を返す。
    存在するフォントであればfontfaceを返す。
    """
    if fontface.startswith('@'):
        return '@' + get_fontface(fontface[1:])
    if not cw.cwpy.rsrc or fontface.lower() in cw.cwpy.rsrc.facenames_lower:
        return fontface

    fontface = fontface.lower()
    if fontface in ("ＭＳ Ｐゴシック".lower(), "MS PGothic".lower()):
        return cw.cwpy.rsrc.fontnames_init["pgothic"]
    elif fontface in ("ＭＳ Ｐ明朝".lower(), "MS PMincho".lower()):
        return cw.cwpy.rsrc.fontnames_init["pmincho"]
    elif fontface in ("ＭＳ ゴシック".lower(), "MS Gothic".lower()):
        return cw.cwpy.rsrc.fontnames_init["gothic"]
    elif fontface in ("ＭＳ 明朝".lower(), "MS Mincho".lower()):
        return cw.cwpy.rsrc.fontnames_init["mincho"]
    elif fontface in ("ＭＳ ＵＩゴシック".lower(), "MS UI Gothic".lower()):
        return cw.cwpy.rsrc.fontnames_init["uigothic"]
    else:
        if "ＭＳ Ｐゴシック".lower() in cw.cwpy.rsrc.facenames_lower:
            return "ＭＳ Ｐゴシック"
        else:
            return cw.cwpy.rsrc.fontnames_init["gothic"]


def main() -> None:
    pass


if __name__ == "__main__":
    main()
