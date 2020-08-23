#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import random
import wx
import pygame
from pygame.locals import BLEND_ADD, BLEND_SUB, BLEND_MULT, BLEND_RGB_ADD, BLEND_RGB_SUB,\
                          BLEND_RGBA_ADD, BLEND_RGBA_SUB, BLEND_RGBA_MULT, RLEACCEL, SRCALPHA

import cw

from typing import Optional, Tuple


try:
    if sys.platform == "darwin":
        from . import _imageretouch_mac as _imageretouch
    elif sys.maxsize == 0x7fffffff:
        from . import _imageretouch32 as _imageretouch
    elif sys.maxsize == 0x7fffffffffffffff:
        from . import _imageretouch64 as _imageretouch
except ImportError as ex:
    print("failed to load _imageretouch module. %s" % (ex))
    _imageretouch = object()


def _retouch(func, image, *args):
    """_imageretouchの関数のラッパ。
    func: _imageretouchの関数オブジェクト。
    image: pygame.Surface。
    *args: その他の引数。
    """
    w, h = image.get_size()

    if not w or not h:
        return image.copy()

    buf = pygame.image.tostring(image, "RGBA")
    buf = func(buf, (w, h), *args)

    if image.get_flags() & SRCALPHA:
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()
    elif image.get_alpha():
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBX").convert_alpha()
        outimage.set_alpha(image.get_alpha(), RLEACCEL)
    else:
        outimage = pygame.image.frombuffer(buf, (w, h), "RGBX").convert()

    if image.get_colorkey():
        outimage.set_colorkey(outimage.get_at((0, 0)), RLEACCEL)

    return outimage


def to_negative(image):
    """色反転したpygame.Surfaceを返す。
    image: pygame.Surface
    """
    outimage = image.copy()

    if image.get_flags() & SRCALPHA:
        outimage.fill((255, 255, 255), special_flags=BLEND_RGB_ADD)
    else:
        outimage.fill((255, 255, 255))

    outimage.blit(image, (0, 0), None, BLEND_RGB_SUB)
    return outimage


def to_negative_for_card(image, framewidth=0):
    """色反転したpygame.Surfaceを返す。
    カード画像用なので外枠nピクセルは色反転しない。
    image: pygame.Surface
    framewidth: 外枠の幅。現在は1.50に合わせて外枠無し(0)
    """
    w, h = image.get_size()

    if w < cw.s(1 + framewidth*2) or h < cw.s(1 + framewidth*2):
        return image.copy()

    rect = pygame.Rect(cw.s((framewidth, framewidth)), (w - cw.s(framewidth*2), h - cw.s(framewidth*2)))
    outimage = image.copy()

    if image.get_flags() & SRCALPHA:
        outimage.fill((255, 255, 255), rect, BLEND_RGB_ADD)
    else:
        outimage.fill((255, 255, 255), rect)

    outimage.blit(image.subsurface(rect), cw.s((framewidth, framewidth)), None, BLEND_RGB_SUB)
    return outimage


def to_negative_for_wxcard(wxbmp, framewidth=0):
    """色反転したwx.Bitmapを返す。
    カード画像用なので外枠1ピクセルは色反転しない。
    wxbmp: wx.Bitmap
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
        buf = cw.util.wxbmp_to_buffer(subbmp)
        buf = bytearray(buf)
        try:
            func = _imageretouch.to_negative
            func(buf, (w, h))
        except Exception:
            buf = bytearray([255-a for a in buf])
        wximg = wx.ImageFromBuffer(w, h, buf)
        subbmp = wx.Bitmap(wximg)
        dc.DrawBitmap(subbmp, x, y)

    dc.SelectObject(wx.NullBitmap)
    return image


def add_lightness(image, value):
    """明度を調整する。
    image: pygame.Surface
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


def add_mosaic(image, value):
    """モザイクをかける。
    image: pygame.Surface
    value: モザイクをかける度合い(0～255)
    """
    try:
        func = _imageretouch.add_mosaic
    except Exception:
        return _add_mosaic(image, value)

    return _retouch(func, image, value)


def _add_mosaic(image, value):
    value = cw.util.numwrap(value, 0, 255)
    image = image.copy()

    if not value:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        n = (x // value) * value
        seq = []

        for y, _px in enumerate(pxs):
            n2 = (y // value) * value
            seq.append(pxarray[n][n2])

        pxarray[x] = seq

    del pxarray

    return image


def to_binaryformat(image, value, basecolor=(255, 255, 255)):
    """二値化する。
    image: pygame.Surface
    value: 閾値(-1～255)。-1の場合はbasecolor以外が黒になる
    basecolor: 閾値が-1の時に使用され、この色以外が黒になる
    """
    try:
        func = _imageretouch.to_binaryformat
    except Exception:
        return _to_binaryformat(image, value, basecolor)

    return _retouch(func, image, value, basecolor)


def _to_binaryformat(image, value, basecolor):
    value = cw.util.numwrap(value, -1, 255)
    image = image.copy()

    if not value:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)

            if value == -1:
                if (r, g, b) == basecolor:
                    seq.append(0xFFFFFF)
                else:
                    seq.append(0x0)
            else:
                if r <= value and g <= value and b <= value:
                    seq.append(0x0)
                else:
                    seq.append(0xFFFFFF)

        pxarray[x] = seq

    del pxarray

    return image


def add_noise(image, value, colornoise=False):
    """ノイズを入れる。
    image: pygame.Surface
    value: ノイズの度合い(-1～255)
    colornoise: カラーノイズか否か
    """
    try:
        func = _imageretouch.add_noise
    except Exception:
        return _add_noise(image, value, colornoise)

    return _retouch(func, image, value, colornoise)


def _add_noise(image, value, colornoise=False):
    value = cw.util.numwrap(value, -1, 255)
    image = image.copy()

    if not value:
        return image

    if value < 0:
        randmax = 2
    else:
        randmax = value * 2 + 1
    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)

            if colornoise:
                if value < 0:
                    r = 0 if random.randint(0, randmax) == 0 else 255
                    g = 0 if random.randint(0, randmax) == 0 else 255
                    b = 0 if random.randint(0, randmax) == 0 else 255
                else:
                    r += random.randint(0, randmax) - value
                    g += random.randint(0, randmax) - value
                    b += random.randint(0, randmax) - value
            else:
                if value < 0:
                    n = 0 if random.randint(0, randmax) == 0 else 255
                    r = n
                    g = n
                    b = n
                else:
                    n = random.randint(0, randmax) - value
                    r += n
                    g += n
                    b += n

            r = cw.util.numwrap(r, 0, 255)
            g = cw.util.numwrap(g, 0, 255)
            b = cw.util.numwrap(b, 0, 255)
            seq.append((r, g, b))

        pxarray[x] = seq

    del pxarray

    return image


def exchange_rgbcolor(image, colormodel):
    """RGB入れ替えしたpygame.Surfaceを返す。
    image: pygame.Surface
    colormodel: "r", "g", "b"を組み合わせた文字列。
    """
    colormodel = colormodel.lower()

    try:
        func = _imageretouch.exchange_rgbcolor
    except Exception:
        return _exchange_rgbcolor(image, colormodel)

    return _retouch(func, image, colormodel)


def _exchange_rgbcolor(image, colormodel):
    colormodel = colormodel.lower()
    image = image.copy()

    if colormodel == "gbr":
        def gbr(r, g, b):
            return (g, b, r)
        func = gbr
    elif colormodel == "brg":
        def brg(r, g, b):
            return (b, r, g)
        func = brg
    elif colormodel == "grb":
        def grb(r, g, b):
            return (g, r, b)
        func = grb
    elif colormodel == "bgr":
        def bgr(r, g, b):
            return (b, g, r)
        func = bgr
    elif colormodel == "rbg":
        def rbg(r, g, b):
            return (r, b, g)
        func = rbg
    else:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)
            seq.append(func(r, g, b))

        pxarray[x] = seq

    del pxarray

    return image


def to_grayscale(image):
    """グレイスケール化したpygame.Surfaceを返す。
    image: pygame.Surface
    """
    try:
        func = _imageretouch.to_sepiatone
    except Exception:
        return to_sepiatone(image, (0, 0, 0))

    return _retouch(func, image, (0, 0, 0))


def to_sepiatone(image, color=(30, 0, -30)):
    """褐色系の画像に変換したpygame.Surfaceを返す。
    image: pygame.Surface
    color: グレイスケール化した画像に付加する色。(r, g, b)のタプル
    """
    try:
        func = _imageretouch.to_sepiatone
    except Exception:
        return _to_sepiatone(image, color)

    return _retouch(func, image, color)


def _to_sepiatone(image, color=(30, 0, -30)):
    if color == (0, 0, 0):
        return retouch_grayscale(image)

    tone_r, tone_g, tone_b = color
    image = image.copy()
    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)
            y = (r * 306 + g * 601 + b * 117) >> 10
            r = cw.util.numwrap(y + tone_r, 0, 255)
            g = cw.util.numwrap(y + tone_g, 0, 255)
            b = cw.util.numwrap(y + tone_b, 0, 255)
            seq.append((r, g, b))

        pxarray[x] = seq

    del pxarray

    return image


def retouch_grayscale(image):
    image = image.copy()
    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)
            y = (r * 306 + g * 601 + b * 117) >> 10
            r = cw.util.numwrap(y, 0, 255)
            g = cw.util.numwrap(y, 0, 255)
            b = cw.util.numwrap(y, 0, 255)
            seq.append((r, g, b))

        pxarray[x] = seq

    del pxarray

    return image


def spread_pixels(image):
    """ピクセル拡散させたpygame.Surfaceを返す。
    image: pygame.Surface
    """
    try:
        func = _imageretouch.spread_pixels
    except Exception:
        return _spread_pixels(image)

    return _retouch(func, image)


def _spread_pixels(image):
    out_image = image.copy()
    out_pxarray = pygame.PixelArray(out_image)
    pxarray = pygame.PixelArray(image)
    w, h = image.get_size()

    for x in range(w):
        n = int(x - random.randint(0, 4) + 2)
        n = cw.util.numwrap(n, 0, w - 1)
        seq = []

        for y in range(h):
            n2 = int(y - random.randint(0, 4) + 2)
            n2 = cw.util.numwrap(n2, 0, h - 1)
            seq.append(pxarray[n][n2])

        out_pxarray[x] = seq

    del out_pxarray
    del pxarray

    return out_image


def _filter(image, weight, offset=0, div=1):
    """フィルタを適用する。
    weight: 重み付け係数。
    offset: オフセット(整数)
    div: 除数(整数)
    """
    try:
        func = _imageretouch.filter
    except Exception:
        return __filter(image, weight, offset, div)

    return _retouch(func, image, weight, offset, div)


def __filter(image, weight, offset=0, div=1):
    out_image = image.copy()
    out_pxarray = pygame.PixelArray(out_image)
    pxarray = pygame.PixelArray(image)
    w, h = image.get_size()

    for x in range(w):
        seq = []

        for y in range(h):
            r, g, b = 0, 0, 0

            for n in range(3):
                for n2 in range(3):
                    try:
                        temp_px = pxarray[x + n - 1]
                    except Exception:
                        temp_px = pxarray[x]

                    try:
                        temp_px = temp_px[y + n2 - 1]
                    except Exception:
                        temp_px = temp_px[y]

                    temp_r, temp_g, temp_b = hex2color(temp_px)
                    r += temp_r * weight[n][n2]
                    g += temp_g * weight[n][n2]
                    b += temp_b * weight[n][n2]

            r = r // div + offset
            g = g // div + offset
            b = b // div + offset
            r = cw.util.numwrap(r, 0, 255)
            g = cw.util.numwrap(g, 0, 255)
            b = cw.util.numwrap(b, 0, 255)
            seq.append((r, g, b))

        out_pxarray[x] = seq

    del out_pxarray
    del pxarray

    return out_image


def filter_shape(image):
    """画像にぼかしフィルターを適用。"""
    weight = (
        (1, 1, 1),
        (1, 1, 1),
        (1, 1, 1)
    )
    offset = 0
    div = 9
    return _filter(image, weight, offset, div)


def filter_sharpness(image):
    """画像にシャープフィルターを適用。"""
    weight = (
        (-1, -1, -1),
        (-1, 24, -1),
        (-1, -1, -1)
    )
    offset = 0
    div = 16
    return _filter(image, weight, offset, div)


def filter_sunpower(image):
    """画像にサンパワーフィルターを適用。"""
    weight = (
        (1, 3, 1),
        (3, 5, 3),
        (1, 3, 1)
    )
    offset = 0
    div = 16
    return _filter(image, weight, offset, div)


def filter_emboss(image):
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


def filter_coloremboss(image):
    """画像にカラーエンボスフィルターを適用。"""
    weight = (
        (-1, -1, -1),
        (0, 1, 0),
        (1, 1, 1)
    )
    offset = 0
    div = 1
    return _filter(image, weight, offset, div)


def filter_darkemboss(image):
    """画像にダークエンボスフィルターを適用。"""
    weight = (
        (-1, -2, -1),
        (0, 0, 0),
        (1, 2, 1)
    )
    offset = 128
    div = 1
    return _filter(image, weight, offset, div)


def filter_electrical(image):
    """画像にエレクトリカルフィルターを適用。"""
    weight = (
        (1, 1, 1),
        (1, -15, 1),
        (1, 1, 1)
    )
    offset = 0
    div = 1
    return _filter(image, weight, offset, div)


def add_transparentline(image, vline, hline, rect=None, setalpha=False):
    """透明色ラインを入れる。
    image: pygame.Surface
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


def add_transparentmesh(image, rect=None, setalpha=False):
    """透明色の網の目を入れる。
    image: pygame.Surface
    """
    w, h = image.get_size()
    if not rect:
        rect = (0, 0, w, h)
    image = image.convert_alpha()
    color = image.get_at((0, 0))
    if setalpha:
        color = (color[0], color[1], color[2], 0)

    clip = image.get_clip()
    image.set_clip(rect)
    x0, y0, w, h = rect
    for cnt in range(0, w + h, 2):
        pos1 = (x0 + cnt, y0)
        pos2 = (x0 + cnt - h, y0 + h)
        pygame.draw.line(image, color, pos1, pos2)

    image.set_clip(clip)
    return image


def add_border(img, bordercolor, borderwidth):
    """textcolorの領域を縁取りする。
    この処理はwxPythonのインスタンスに対して行う。
    img: pygame.Surface。
    bordercolor: 縁取り色(R,G,B)。
    borderwidth: 縁取りの太さ。
    """
    try:
        func = _imageretouch.bordering
    except Exception:
        func = _bordering

    buf = pygame.image.tostring(img, "RGBA")
    points = func(buf, img.get_size())
    hbw = borderwidth // 2
    for i in range(0, len(points), 2):
        x = points[i+0]
        y = points[i+1]
        if borderwidth == 1:
            img.set_at((x, y), bordercolor)
        elif borderwidth == 2:
            img.fill(bordercolor, pygame.Rect(x - 1, y - 1, 2, 2))
        else:
            pygame.draw.ellipse(img, bordercolor, pygame.Rect(x - hbw, y - hbw, borderwidth, borderwidth))


def _bordering(data, size):
    w = size[0]
    h = size[1]

    color = [0] * (w * h)
    left = w
    right = 0
    top = h
    bottom = 0
    for i in range(w * h):
        iData = i * 4
        color[i] = ord(data[iData+3]) == 0
        if color[i]:
            x = i % w
            y = i // w
            left = min(left, max(x - 1, 0))
            right = max(right, min(x + 2, w))
            top = min(top, max(y - 1, 0))
            bottom = max(bottom, min(y + 2, h))

    if left >= right:
        return []

    seq = []
    for x in range(left, right):
        for y in range(top, bottom):
            yi = y * w
            i = x + yi
            if color[i]:
                continue

            find = False
            find |= 0 < x and 0 < y and color[(x - 1) + (yi - w)]
            find |= 0 < y and color[(x + 0) + (yi - w)]
            find |= x + 1 < w and 0 < y and color[(x + 1) + (yi - w)]
            find |= 0 < x and color[(x - 1) + (yi)]
            find |= x + 1 < w and color[(x + 1) + (yi)]
            find |= 0 < x and y + 1 < h and color[(x - 1) + (yi + w)]
            find |= y + 1 < h and color[(x + 0) + (yi + w)]
            find |= x + 1 < w and y + 1 < h and color[(x + 1) + (yi + w)]

            if find:
                seq.append(x)
                seq.append(y)
    return seq


def blend_1_50(dest, pos, source, flag):
    """1.50の挙動に合わせて加算または減算合成を行う。
    dest: pygame.Surface。
    pos: 合成位置。
    image: pygame.Surface。
    flag: BLEND_ADDまたはBLEND_SUBまたはBLEND_MULT
    """
    w, h = source.get_size()

    clip = dest.get_clip()
    if not clip:
        clip = dest.get_rect()

    rect = pygame.Rect(pos, (w, h))
    rect = pygame.Rect(clip.topleft, clip.size).clip(rect)
    if rect.w <= 0 or rect.h <= 0:
        return

    sub = dest.subsurface(rect)

    pos2 = (max(0, -pos[0] + clip.left), max(0, -pos[1] + clip.top))
    rect2 = pygame.Rect(pos2, rect.size)
    source2 = source.subsurface(rect2)

    try:
        if flag in (BLEND_ADD, BLEND_RGBA_ADD):
            func = _imageretouch.blend_add_1_50
        elif flag in (BLEND_SUB, BLEND_RGBA_SUB):
            func = _imageretouch.blend_sub_1_50
        elif flag in (BLEND_MULT, BLEND_RGBA_MULT):
            func = _imageretouch.blend_mult_1_50
        else:
            assert False

        sbuf = pygame.image.tostring(source2, "RGBA")

        outimage = _retouch(func, sub, sbuf)
    except Exception:
        if flag in (BLEND_ADD, BLEND_RGBA_ADD):
            func = _blend_add_1_50
        elif flag in (BLEND_SUB, BLEND_RGBA_SUB):
            func = _blend_sub_1_50
        elif flag in (BLEND_MULT, BLEND_RGBA_MULT):
            func = _blend_mult_1_50
        else:
            assert False
        outimage = func(sub, source)

    dest.blit(outimage, rect.topleft, None, 0)


def _blend_add_1_50(dest, source):
    w, h = dest.get_size()
    dbuf = pygame.image.tostring(dest, "RGBA")
    sbuf = pygame.image.tostring(source, "RGBA")

    buf = []
    for i in range(0, len(dbuf), 4):
        dr, dg, db, da = ord(dbuf[i+0]), ord(dbuf[i+1]), ord(dbuf[i+2]), ord(dbuf[i+3])
        sr, sg, sb, sa = ord(sbuf[i+0]), ord(sbuf[i+1]), ord(sbuf[i+2]), ord(sbuf[i+3])

        dr = colorwrap((dr * (255 - sa) >> 8) + (colorwrap(dr + sr) * sa >> 8))
        dg = colorwrap((dg * (255 - sa) >> 8) + (colorwrap(dg + sg) * sa >> 8))
        db = colorwrap((db * (255 - sa) >> 8) + (colorwrap(db + sb) * sa >> 8))
        da = 255

        buf.extend([chr(dr), chr(dg), chr(db), chr(da)])

    assert len(buf) == len(dbuf)
    buf = "".join(buf)
    return pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()


def _blend_sub_1_50(dest, source):
    w, h = dest.get_size()
    dbuf = pygame.image.tostring(dest, "RGBA")
    sbuf = pygame.image.tostring(source, "RGBA")

    buf = []
    for i in range(0, len(dbuf), 4):
        dr, dg, db, da = ord(dbuf[i+0]), ord(dbuf[i+1]), ord(dbuf[i+2]), ord(dbuf[i+3])
        sr, sg, sb, sa = ord(sbuf[i+0]), ord(sbuf[i+1]), ord(sbuf[i+2]), ord(sbuf[i+3])

        dr = max(colorwrap(dr * (255 - sa) >> 8), colorwrap(dr - (sr * sa >> 8)))
        dg = max(colorwrap(dg * (255 - sa) >> 8), colorwrap(dg - (sg * sa >> 8)))
        db = max(colorwrap(db * (255 - sa) >> 8), colorwrap(db - (sb * sa >> 8)))
        da = 255

        buf.extend([chr(dr), chr(dg), chr(db), chr(da)])

    assert len(buf) == len(dbuf)
    buf = "".join(buf)
    return pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()


def _blend_mult_1_50(dest, source):
    w, h = dest.get_size()
    dbuf = pygame.image.tostring(dest, "RGBA")
    sbuf = pygame.image.tostring(source, "RGBA")

    buf = []
    for i in range(0, len(dbuf), 4):
        dr, dg, db, da = ord(dbuf[i+0]), ord(dbuf[i+1]), ord(dbuf[i+2]), ord(dbuf[i+3])
        sr, sg, sb, sa = ord(sbuf[i+0]), ord(sbuf[i+1]), ord(sbuf[i+2]), ord(sbuf[i+3])

        if sa != 255:
            sr = colorwrap(((sr * sa) + (((1 << 8) - sa) << 8)) >> 8)
            sg = colorwrap(((sg * sa) + (((1 << 8) - sa) << 8)) >> 8)
            sb = colorwrap(((sb * sa) + (((1 << 8) - sa) << 8)) >> 8)
        dr = colorwrap(dr * sr >> 8)
        dg = colorwrap(dg * sg >> 8)
        db = colorwrap(db * sb >> 8)
        da = 255

        buf.extend([chr(dr), chr(dg), chr(db), chr(da)])

    assert len(buf) == len(dbuf)
    buf = "".join(buf)
    return pygame.image.frombuffer(buf, (w, h), "RGBA").convert_alpha()


def to_disabledimage(wxbmp: wx.Bitmap, maskpos: Tuple[int, int] = (0, 0)) -> wx.Bitmap:
    """
    通常時のボタン画像からdisabled用の画像を作る。
    RGB値の範囲を 0～255 から min～max に変更する。
    wxbmp: wx.Bitmap
    """
    try:
        func = _imageretouch.to_disabledimage
    except Exception:
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


def _to_disabledimage(buf, size):
    """
    通常時のボタン画像からdisabled用の画像を作る
    グレイスケール処理後、RGB値の範囲を 0～255 から min～max に変更
    wxbmp: wx.Bitmap
    """
    # 最終的なRGB値の範囲を設定
    nmin, nmax = 140, 240

    colorkey = (buf[0], buf[1], buf[2])

    for px in range(0, len(buf), 3):
        if (buf[px], buf[px+1], buf[px+2]) != colorkey:
            buf[px+0] = buf[px+0] * (nmax - nmin) // 255 + nmin
            buf[px+1] = buf[px+1] * (nmax - nmin) // 255 + nmin
            buf[px+2] = buf[px+2] * (nmax - nmin) // 255 + nmin


def to_disabledsurface(image):
    """_to_disabledimage()のpygame.Surface版。"""
    image = image.copy()
    image.fill((128, 128, 128), special_flags=pygame.locals.BLEND_RGB_ADD)
    return to_grayscale(image)


def add_lightness_for_wxbmp(wxbmp, lightness, maskpos=(0, 0)):
    """
    通常時のボタン画像からdisabled用の画像を作る。
    RGB値の範囲を 0～255 から min～max に変更する。
    wxbmp: wx.Bitmap
    """
    try:
        func = _imageretouch.add_lightness
    except Exception:
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


def _add_lightness(buf, size, lightness):
    (w, h) = size
    for i, v in enumerate(buf):
        buf[i] = cw.util.numwrap(v + lightness, 0, 255)


def hex2color(hexnum):
    """RGBデータの16進数を(r, g, b)のタプルで返す。
    hexnum: 16進数。
    """
    b = int(hexnum & 0xFF)
    g = int((hexnum >> 8) & 0xFF)
    r = int((hexnum >> 16) & 0xFF)
    return r, g, b


def colorwrap(num):
    """numを0～255の値に丸める。"""
    return cw.util.numwrap(num, 0, 255)


def decode_rle4data(data, h, bpl):
    return _imageretouch.decode_rle4data(data, h, bpl)


def patch_alphadata(image, ext, data):
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
            has_alpha = _imageretouch.has_alphabmp32
        else:
            has_alpha = _imageretouch.has_alpha

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
    _imageretouch.mul_alphaonly(buf, alpha)
    wximg.SetAlphaBuffer(buf)
    return wximg


def mul_alpha(image, alpha):
    """alpha/255分まで、imageのアルファ値を減少させる。"""
    image.fill((255, 255, 255, alpha), special_flags=pygame.locals.BLEND_RGBA_MULT)
    return image


def blit_2bitbmp_to_card(dest, source, pos):
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
        rect = pygame.Rect(pos, (w, h))
        rect = pygame.Rect((0, 0), dest.get_size()).clip(rect)
        if rect.w <= 0 or rect.h <= 0:
            return

        sub = dest.subsurface(rect)
        rect2 = pygame.Rect((max(0, -pos[0]), max(0, -pos[1])), rect.size)
        source2 = source.subsurface(rect2)

        try:
            func = _imageretouch.blend_and

            sbuf = pygame.image.tostring(source2, "RGBA")

            outimage = _retouch(func, sub, sbuf)
        except Exception:
            dest.blit(source, pos)
            return

        dest.blit(outimage, rect.topleft, None, 0)
        return

    dest.blit(source, pos)


def blit_2bitbmp_to_message(dest, source, pos, wincolour):
    if source.get_colorkey() and isinstance(source, cw.util.Depth1Surface) and source.bmpdepthis1:
        w, h = source.get_size()
        rect = pygame.Rect(pos, (w, h))
        rect = pygame.Rect((0, 0), dest.get_size()).clip(rect)
        if rect.w <= 0 or rect.h <= 0:
            return

        sub = dest.subsurface(rect)
        rect2 = pygame.Rect((max(0, -pos[0]), max(0, -pos[1])), rect.size)
        source2 = source.subsurface(rect2)

        try:
            func = _imageretouch.blend_and_msg

            sbuf = pygame.image.tostring(source2, "RGBA")

            outimage = _retouch(func, sub, sbuf, wincolour)
        except Exception:
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
        buf = wximg.GetDataBuffer()
        alphabuf = wximg.GetAlphaBuffer()
        dbuf = cw.util.wxbmp_to_buffer(sub)

        dbuf = bytearray(dbuf)
        buf = bytearray(buf)
        assert len(dbuf) == len(buf)
        assert len(dbuf) == len(alphabuf)*3
        try:
            func = _imageretouch.blend_and_rgb
            func(dbuf, (w, h), buf)

        except Exception:
            dbuf = bytearray([a_b[0] & a_b[1] for a_b in zip(buf, dbuf)])

        wximg = wx.ImageFromBuffer(rect.Width, rect.Height, dbuf, alphaBuffer=bytearray(alphabuf) if alphabuf else None)
        wxbmp = wx.Bitmap(wximg)
        dc.SelectObject(dest)
        dc.DrawBitmap(wxbmp, rect.X, rect.Y)

        return

    dc.DrawBitmap(wxbmp, x, y, useMask)


def _create_mfont(name, pixels, bold, italic, sys):
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
    def __init__(self, face, pixels, bold=False, italic=False):
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
            try:
                func = _imageretouch.font_new
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
            except Exception:
                self.font, self.font2x, self.font_notitalic = _create_mfont(face, pixels, bold, italic, sys=True)
        else:
            self.font, self.font2x, self.font_notitalic = _create_mfont(face, pixels, bold, italic, sys=True)

    def _is_cachable(self, s):
        s = str(s)
        return len(s) == 1 and (('ぁ' <= s <= 'ヶ') or (0 <= ord(s) <= 255) or ('！' <= s <= 'ﾟ'))

    def dispose(self):
        if not self.font and self.fontinfo:
            _imageretouch.font_del(self.fontinfo)
            _imageretouch.font_del(self.fontinfo2x)
            self.fontinfo = None
            self.fontinfo2x = None
            self._cache = None

    def __del__(self):
        if not self.font and self.fontinfo:
            _imageretouch.font_del(self.fontinfo)
            _imageretouch.font_del(self.fontinfo2x)
            self.fontinfo = None
            self.fontinfo2x = None
            self._cache = None

    def get_bold(self):
        if self.font:
            return self.font.get_bold()
        else:
            return self.bold

    def set_bold(self, v):
        self._cache = {}
        if self.font:
            self.font.set_bold(v)
            self.font2x.set_bold(v)
            self.font_notitalic.set_bold(v)
        else:
            self.bold = v
            _imageretouch.font_bold(self.fontinfo, v)
            _imageretouch.font_bold(self.fontinfo2x, v)

    def get_italic(self):
        if self.font:
            return self.font.get_italic()
        else:
            return self.italic

    def set_italic(self, v):
        self._cache = {}
        if self.font:
            self.font.set_italic(v)
            self.font2x.set_italic(v)
        else:
            self.italic = v
            _imageretouch.font_italic(self.fontinfo, v)
            _imageretouch.font_italic(self.fontinfo2x, v)

    def get_underline(self):
        if self.font:
            return self.font.get_underline()
        else:
            return self.underline

    def set_underline(self, v):
        self._cache = {}
        if self.font:
            self.font.set_underline(v)
            self.font2x.set_underline(v)
            self.font_notitalic.set_underline(v)
        else:
            self.underline = v
            _imageretouch.font_underline(self.fontinfo, v)
            _imageretouch.font_underline(self.fontinfo2x, v)

    def get_height(self):
        if self.font:
            return self.font.get_height()
        elif self.pixels < 0:
            return -self.pixels
        else:
            return self.pixels

    def get_linesize(self):
        if self.font:
            return self.font.get_linesize()
        else:
            return _imageretouch.font_height(self.fontinfo)

    def size(self, text):
        if self.font:
            return self.font.size(text)
        else:
            return _imageretouch.font_imagesize(self.fontinfo, text.encode("utf-8"), False)

    def size_withoutoverhang(self, text):
        if self.font:
            return self.font_notitalic.size(text)
        else:
            return _imageretouch.font_size(self.fontinfo, text.encode("utf-8"))

    def render(self, text, antialias, colour):
        return self._render_impl(text, antialias, colour, False)

    def render_sbold(self, text, antialias, colour):
        return self._render_impl(text, antialias, colour, True)

    def _render_impl(self, text, antialias, colour, sbold):
        cachable = self._is_cachable(text)
        if cachable:
            key = (text, antialias, colour)
            if key in self._cache:
                return self._cache[key].copy()

        if self.font:
            if antialias:
                image = self.font2x.render(text, antialias, colour)
                size = self.size(text)
                if sbold:
                    size2 = image.get_size()
                    size2 = (size2[0]+4, size2[1])
                    image2 = pygame.Surface(size2).convert_alpha()
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
                    image2 = pygame.Surface(size).convert_alpha()
                    image2.fill((0, 0, 0, 0))
                    image2.blit(bmp, (0, 0))
                    image2.blit(bmp, (1, 0))
                    bmp = image2
        elif antialias:
            text = text.encode("utf-8")
            size = _imageretouch.font_imagesize(self.fontinfo2x, text, antialias)
            buf = _imageretouch.font_render(self.fontinfo2x, text, antialias, colour[:3])
            # BUG: Windows 10 1709で、フォント「游明朝」で「ーム」を含む文字列のサイズが
            #      ランダムに変動してしまう不具合を暫定的に回避する
            size = (len(buf) // size[1] // 4, size[1])
            assert len(buf) == size[0]*size[1]*4
            image = pygame.image.frombuffer(buf, size, "RGBA").convert_alpha()
            size2 = _imageretouch.font_imagesize(self.fontinfo, text, antialias)
            if sbold:
                size = (size[0]+4, size[1])
                image2 = pygame.Surface(size).convert_alpha()
                image2.fill((0, 0, 0, 0))
                for x in range(4):
                    image2.blit(image, (x, 0))
                image = image2
                size2 = (size2[0]+1, size2[1])

            bmp = pygame.transform.smoothscale(image, size2)
        else:
            text = text.encode("utf-8")
            # BUG: font_render()からタプルを返そうとするとbufがGCで
            #      回収されなくなってしまうため、bufのみを返すようにし、
            #      (w, h)取得用にfont_imagesize()を用意してある
            # buf, size = _imageretouch.font_render(self.fontinfo, str, antialias, colour[:3])
            size = _imageretouch.font_imagesize(self.fontinfo, text, antialias)
            buf = _imageretouch.font_render(self.fontinfo, text, antialias, colour[:3])
            # BUG: Windows 10 1709で、フォント「游明朝」で「ーム」を含む文字列のサイズが
            #      ランダムに変動してしまう不具合を暫定的に回避する
            size = (len(buf) // size[1] // 4, size[1])
            assert len(buf) == size[0]*size[1]*4
            bmp = pygame.image.frombuffer(buf, size, "RGBA").convert_alpha()
            if sbold:
                size = bmp.get_size()
                size = (size[0]+1, size[1])
                image2 = pygame.Surface(size).convert_alpha()
                image2.fill((0, 0, 0, 0))
                image2.blit(bmp, (0, 0))
                image2.blit(bmp, (1, 0))
                bmp = image2

        if cachable:
            self._cache[key] = bmp.copy()
        return bmp


def get_fontface(fontface):
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


def main():
    pass


if __name__ == "__main__":
    main()
