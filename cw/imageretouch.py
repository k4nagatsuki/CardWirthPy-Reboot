#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import wx
import pygame
from pygame.locals import *

import cw

try:
    import _imageretouch
except ImportError, ex:
    print "failed to load _imageretouch module. %s" % (ex.message)


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

def to_negative_for_card(image):
    """色反転したpygame.Surfaceを返す。
    カード画像用なので外枠1ピクセルは色反転しない。
    image: pygame.Surface
    """
    w, h = image.get_size()

    if w < cw.s(3) or h < cw.s(3):
        return image.copy()

    rect = pygame.Rect(cw.s((1, 1)), (w - cw.s(2), h - cw.s(2)))
    outimage = image.copy()

    if image.get_flags() & SRCALPHA:
        outimage.fill((255, 255, 255), rect, BLEND_RGB_ADD)
    else:
        outimage.fill((255, 255, 255), rect)

    outimage.blit(image.subsurface(rect), cw.s((1, 1)), None, BLEND_RGB_SUB)
    return outimage

def add_lightness(image, value):
    """明度を調整する。
    image: pygame.Surface
    value: 明暗値(-255～255)
    """
    value = cw.util.numwrap(value, -255, 255)
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
    except NameError:
        return _add_mosaic(image, value)

    return _retouch(func, image, value)

def _add_mosaic(image, value):
    value = cw.util.numwrap(value, 0, 255)
    image = image.copy()

    if not value:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        n = (x / value) * value
        seq = []

        for y, px in enumerate(pxs):
            n2 = (y / value) * value
            seq.append(pxarray[n][n2])

        pxarray[x] = seq

    return image

def to_binaryformat(image, value):
    """二値化する。
    image: pygame.Surface
    value: 閾値(0～255)
    """
    try:
        func = _imageretouch.to_binaryformat
    except NameError:
        return _to_binaryformat(image, value)

    return _retouch(func, image, value)

def _to_binaryformat(image, value):
    value = cw.util.numwrap(value, 0, 255)
    image = image.copy()

    if not value:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)

            if r <= value and g <= value and b <= value:
                seq.append(0x0)
            else:
                seq.append(0xFFFFFF)

        pxarray[x] = seq

    return image

def add_noise(image, value, colornoise=False):
    """ノイズを入れる。
    image: pygame.Surface
    value: ノイズの度合い(-1～255)
    colornoise: カラーノイズか否か
    """
    try:
        func = _imageretouch.add_noise
    except NameError:
        return _add_noise(image, value, colornoise)

    return _retouch(func, image, value, colornoise)

def _add_noise(image, value, colornoise=False):
    value = cw.util.numwrap(value, -1, 255)
    image = image.copy()

    if not value:
        return image

    if value < 0:
        randmax = 256
    else:
        randmax = value * 2 + 1
    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)

            if colornoise:
                if value < 0:
                    r = random.randint(0, randmax)
                    g = random.randint(0, randmax)
                    b = random.randint(0, randmax)
                else:
                    r += random.randint(0, randmax) - value
                    g += random.randint(0, randmax) - value
                    b += random.randint(0, randmax) - value
            else:
                if value < 0:
                    n = random.randint(0, randmax)
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

    return image

def exchange_rgbcolor(image, colormodel):
    """RGB入れ替えしたpygame.Surfaceを返す。
    image: pygame.Surface
    colormodel: "r", "g", "b"を組み合わせた文字列。
    """
    colormodel = colormodel.lower()

    try:
        func = _imageretouch.exchange_rgbcolor
    except NameError:
        return _exchange_rgbcolor(image, colormodel)

    return _retouch(func, image, colormodel)

def _exchange_rgbcolor(image, colormodel):
    colormodel = colormodel.lower()
    image = image.copy()

    if colormodel == "gbr":
        func = lambda r, g, b: (g, b, r)
    elif colormodel == "brg":
        func = lambda r, g, b: (b, r, g)
    elif colormodel == "grb":
        func = lambda r, g, b: (g, r, b)
    elif colormodel == "bgr":
        func = lambda r, g, b: (b, g, r)
    elif colormodel == "rbg":
        func = lambda r, g, b: (r, b, g)
    else:
        return image

    pxarray = pygame.PixelArray(image)

    for x, pxs in enumerate(pxarray):
        seq = []

        for px in pxs:
            r, g, b = hex2color(px)
            seq.append(func(r, g, b))

        pxarray[x] = seq

    return image

def to_grayscale(image):
    """グレイスケール化したpygame.Surfaceを返す。
    image: pygame.Surface
    """
    try:
        func = _imageretouch.to_sepiatone
    except NameError:
        return to_sepiatone(image, (0, 0, 0))

    return _retouch(func, image, (0, 0, 0))

def to_sepiatone(image, color=(30, 0, -30)):
    """褐色系の画像に変換したpygame.Surfaceを返す。
    image: pygame.Surface
    color: グレイスケール化した画像に付加する色。(r, g, b)のタプル
    """
    try:
        func = _imageretouch.to_sepiatone
    except NameError:
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

    return image

def spread_pixels(image):
    """ピクセル拡散させたpygame.Surfaceを返す。
    image: pygame.Surface
    """
    try:
        func = _imageretouch.spread_pixels
    except NameError:
        return _spread_pixels(image)

    return _retouch(func, image)

def _spread_pixels(image):
    out_image = image.copy()
    out_pxarray = pygame.PixelArray(out_image)
    pxarray = pygame.PixelArray(image)
    w, h = image.get_size()

    for x in xrange(w):
        n = int(x - random.randint(0, 4) + 2)
        n = cw.util.numwrap(n, 0, w - 1)
        seq = []

        for y in xrange(h):
            n2 = int(y - random.randint(0, 4) + 2)
            n2 = cw.util.numwrap(n2, 0, h - 1)
            seq.append(pxarray[n][n2])

        out_pxarray[x] = seq

    return out_image

def _filter(image, weight, offset=0, div=1):
    """フィルタを適用する。
    weight: 重み付け係数。
    offset: オフセット(整数)
    div: 除数(整数)
    """
    try:
        func = _imageretouch.filter
    except NameError:
        return __filter(image, weight, offset, div)

    return _retouch(func, image, weight, offset, div)

def __filter(image, weight, offset=0, div=1):
    out_image = image.copy()
    out_pxarray = pygame.PixelArray(out_image)
    pxarray = pygame.PixelArray(image)
    w, h = image.get_size()

    for x in xrange(w):
        seq = []

        for y in xrange(h):
            r, g, b = 0, 0, 0

            for n in xrange(3):
                for n2 in xrange(3):
                    try:
                        temp_px = pxarray[x + n - 1]
                    except:
                        temp_px = pxarray[x]

                    try:
                        temp_px = temp_px[y + n2 - 1]
                    except:
                        temp_px = temp_px[y]

                    temp_r, temp_g, temp_b = hex2color(temp_px)
                    r += temp_r * weight[n][n2]
                    g += temp_g * weight[n][n2]
                    b += temp_b * weight[n][n2]

            r = r / div + offset
            g = g / div + offset
            b = b / div + offset
            r = cw.util.numwrap(r, 0, 255)
            g = cw.util.numwrap(g, 0, 255)
            b = cw.util.numwrap(b, 0, 255)
            seq.append((r, g, b))

        out_pxarray[x] = seq

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
        (-1, -2, -1),
        (0, 0, 0),
        (1, 2, 1)
    )
    offset = 0
    div = 1
    return _filter(image, weight, offset, div)

def add_transparentline(image, vline, hline):
    """透明色ラインを入れる。
    image: pygame.Surface
    vline: bool値。Trueなら縦線を入れる。
    hline: bool値。Trueなら横線を入れる。
    """
    image = image.copy().convert_alpha()
    w, h = image.get_size()

    if vline:
        for cnt in xrange(w / 2 - 1):
            x = cnt * 2
            pygame.draw.line(image, (0, 0, 0, 0), (x, 0), (x, h))

    if hline:
        for cnt in xrange(h / 2 - 1):
            y = cnt * 2
            pygame.draw.line(image, (0, 0, 0, 0), (0, y), (w, y))

    return image

def add_border(wxdc, wxbmp, textcolor, borderwidth):
    """textcolorの領域を縁取りする。
    この処理はwxPythonのインスタンスに対して行う。
    wxbmp: wx.DC
    wxbmp: wx.Bitmap
    textcolor: 色(R,G,B)。
    borderwidth: 縁取りの太さ。
    """
    try:
        func = _imageretouch.bordering
    except NameError:
        func = _bordering

    wximg = wxbmp.ConvertToImage()
    buf = wximg.GetDataBuffer()
    w = wximg.GetWidth()
    h = wximg.GetHeight()
    points = func(buf, (w, h), textcolor[:3])
    hbw = borderwidth / 2
    for i in xrange(0, len(points), 2):
        x = points[i+0]
        y = points[i+1]
        if borderwidth == 1:
            wxdc.DrawPoint(x, y)
        elif borderwidth == 2:
            wxdc.DrawRectangle(x - 1, y - 1, 2, 2)
        else:
            wxdc.DrawEllipse(x - hbw, y - hbw, borderwidth, borderwidth)

def _bordering(data, size, textcolor):
    w = size[0]
    h = size[1]

    color = [0] * (w * h)
    left = w
    right = 0
    top = h
    bottom = 0
    for i in xrange(w * h):
        iData = i * 3
        color[i] = (ord(data[iData+0]), ord(data[iData+1]), ord(data[iData+2])) == textcolor
        if color[i]:
            x = i % w
            y = i / w
            left = min(left, max(x - 1, 0))
            right = max(right, min(x + 2, w))
            top = min(top, max(y - 1, 0))
            bottom = max(bottom, min(y + 2, h))

    if left >= right:
        return []

    seq = []
    for x in xrange(left, right):
        for y in xrange(top, bottom):
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

def hex2color(hexnum):
    """RGBデータの16進数を(r, g, b)のタプルで返す。
    hexnum: 16進数。
    """
    b = int(hexnum & 0xFF)
    g = int((hexnum >> 8) & 0xFF)
    r = int((hexnum >> 16) & 0xFF)
    return r, g, b

def main():
    pass

if __name__ == "__main__":
    main()
