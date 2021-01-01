#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pygame
import pygame.locals

import cw
from . import base

from typing import Dict, List, Optional, Tuple


class Bill(object):
    """貼紙のデータ。メッセージログで使用する。"""
    def __init__(self, header: cw.header.ScenarioHeader) -> None:
        self.header = header
        self.selections: List[cw.sprite.message.SelectionBar] = []
        self.specialchars: Dict[str, Tuple[pygame.Surface, bool]] = {}

        self._bgs = {}
        self._bmps = {}

        # 画面スケールやスキン変更で内容が変化しないように、全スケールのイメージをロードしておく
        path = "Table/Bill"
        fpath = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self._bgs[1.0] = cw.util.load_image(fpath, can_loaded_scaledimage=True, noscale=True)
        self._bmps[1.0] = header.get_bmps(up_scr=1)
        spext = cw.util.splitext(fpath)
        for scale in cw.SCALE_LIST:
            fname = "%s.x%s%s" % (spext[0], scale, spext[1])
            if os.path.isfile(fname):
                self._bgs[scale] = cw.util.Depth1Surface(cw.util.load_image(fname, True, noscale=True), scale)
            bmps = header.get_bmps(up_scr=scale)
            if bmps:
                self._bmps[float(scale)] = bmps

        size = self._bgs[1].get_size()
        self._xp_noscale = 1
        self._yp_noscale = 1

        w = size[0] + self._xp_noscale*2
        h = size[1] + self._yp_noscale*2
        self.rect_noscale = pygame.Rect((cw.SIZE_AREA[0]-w) // 2, (cw.SIZE_AREA[1]-h) // 2, w, h)

    def create_image(self) -> Tuple[pygame.Surface, Tuple[int, int]]:
        up_scr = cw.UP_SCR
        subimg: Optional[pygame.Surface] = None
        bmps: Optional[Tuple[List[pygame.Surface], List[cw.image.ImageInfo]]] = None
        while 1 <= up_scr:
            if not subimg:
                subimg = self._bgs.get(up_scr, None)
            if not bmps:
                bmps = self._bmps.get(up_scr, None)
            if subimg and bmps:
                subimg = cw.s(subimg)
                break
            up_scr //= 2
        else:
            assert False  # self._bgs[1]は確実に存在するはず

        bmpw, bmph = subimg.get_size()

        xp = cw.s(self._xp_noscale)
        yp = cw.s(self._yp_noscale)
        image = pygame.Surface((bmpw + xp*2, bmph + yp*2)).convert()
        image.fill(cw.cwpy.setting.blwincolour)
        image.set_clip(pygame.Rect(xp, yp, bmpw, bmph))

        image.blit(subimg, (xp, yp))

        for bmp, info in zip(bmps[0], bmps[1]):
            # デフォルトは左上位置固定(CardWirthとの互換性維持)
            assert isinstance(info, cw.image.ImageInfo)
            baserect = info.calc_basecardposition(bmp.get_size(), noscale=False,
                                                  basecardtype="Bill",
                                                  cardpostype="NotCard")
            cw.imageretouch.blit_2bitbmp_to_card(image, cw.s(bmp), (cw.s(163) + baserect.x, cw.s(70) + baserect.y))

        # シナリオ名
        font = cw.cwpy.rsrc.fonts["scenario"]
        s = self.header.name
        subimg1 = font.render(s, True, (0, 0, 0))
        subimg2 = font.render(s, True, (255, 255, 255))
        subimg2.fill((255, 255, 255, 128), special_flags=pygame.locals.BLEND_RGBA_MULT)
        w, h = subimg1.get_size()
        maxwidth = bmpw - cw.s(5)*2
        if maxwidth < w:
            subimg1 = cw.image.smoothscale(subimg1, (maxwidth, h), True)
            subimg2 = cw.image.smoothscale(subimg2, (maxwidth, h), True)

        x = (bmpw-w)//2 + xp
        y = cw.s(35) + yp
        for xx in range(x - 1, x + 2):
            for yy in range(y - 1, y + 2):
                if xx != x or yy != y:
                    image.blit(subimg2, (xx, yy))
        image.blit(subimg1, (x, y))

        # 解説文
        font = cw.cwpy.rsrc.fonts["scenariodesc"]
        s = self.header.desc
        y = cw.s(180)
        for ln in s.splitlines():
            subimg = font.render(ln, True, (0, 0, 0))
            image.blit(subimg, (cw.s(65) + xp, y + yp))
            y += cw.s(15)

        # 対象レベル
        font = cw.cwpy.rsrc.fonts["targetlevel"]
        levelmax = str(self.header.levelmax) if self.header.levelmax else ""
        levelmin = str(self.header.levelmin) if self.header.levelmin else ""
        if levelmax or levelmin:
            if levelmin == levelmax:
                s = cw.cwpy.msgs["target_level_1"] % (levelmin)
            else:
                s = cw.cwpy.msgs["target_level_2"] % (levelmin, levelmax)

            w = font.size_withoutoverhang(s)[0]
            subimg = font.render(s, 2 <= cw.UP_SCR, (0, 128, 128))
            image.blit(subimg, ((bmpw-w)//2 + xp, cw.s(15) + yp))

        return image, cw.s(pygame.Rect(self.rect_noscale))

    def get_height_noscale(self) -> int:
        result: int = self.rect_noscale.height
        return result

    def create_message(self) -> "BillSprite":
        return BillSprite(self)


class BillSprite(base.CWPySprite):
    def __init__(self, bill: Bill) -> None:
        base.CWPySprite.__init__(self)
        self.bill = bill
        self.selections = bill.selections
        self.specialchars = bill.specialchars
        self.rect_noscale = pygame.Rect(bill.rect_noscale)
        self.update_scale()
        cw.cwpy.backloggrp.add(self, layer=cw.LAYER_LOG)

    def update_scale(self) -> None:
        self.image, _rect = self.bill.create_image()
        self.rect = cw.s(pygame.Rect(self.rect_noscale))


def get_detailtext(header: cw.header.ScenarioHeader) -> str:
    """ScenarioHeaderをテキスト表現に変換する。"""
    lines = []
    name = header.name
    if header.levelmin and header.levelmax:
        if header.levelmin == header.levelmax:
            level = "%s" % (header.levelmax)
        else:
            level = "%s～%s" % (header.levelmin, header.levelmax)
    elif header.levelmin:
        level = "%s～" % (header.levelmin)
    elif header.levelmax:
        level = "～%s" % (header.levelmax)
    else:
        level = ""
    if level:
        name = "%s (%s)" % (name, level)
    name = "[ %s ]" % name
    slen = cw.util.get_strlen(name)
    if slen < 38:
        name += "-" * (38 - slen)
    lines.append(name)
    if header.author:
        name = "(%s)" % header.author
        slen = cw.util.get_strlen(name)
        if slen < 38:
            name = " " * (38 - slen) + name
        lines.append(name)
    lines.append("")
    lines.append(header.desc)
    return "\n".join(lines)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
