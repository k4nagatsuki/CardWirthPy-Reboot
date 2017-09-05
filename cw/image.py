#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import struct
import threading
import cStringIO
import wx
import pygame

import cw


class ImageInfo(object):
    def __init__(self, path="", pcnumber=0, base=None, postype="Default", basecardtype=None):
        """
        カードなどの画像の定義。
        """
        self.path = path
        self.pcnumber = pcnumber
        while base and base.base:
            base = base.base
        self.base = base
        if self.base:
            self.postype = self.base.postype
        else:
            self.postype = postype
        self.basecardtype = basecardtype

    def set_attr(self, e):
        """拡張情報をeへ登録する。
        """
        assert e.tag == "ImagePath"
        if not self.postype in ("Default", None):
            e.set("positiontype", self.postype)

    def calc_basecardposition(self, (imgwidth, imgheight), noscale=False, basecardtype=None, cardpostype=None):
        """カードに配置した時の描画位置を返す。
        ベースとなる情報が無い時はpygame.Rect(0, 0, imgwidth, imgheight)を返す。
        """
        def getsize(resname):
            if resname.endswith("_noscale"):
                resname = resname[0:-len("_noscale")]
                return cw.setting.SIZE_RESOURCES["CardBg/" + resname]
            else:
                return cw.s(cw.setting.SIZE_RESOURCES["CardBg/" + resname])
        return self._calc_basecardposition_impl(imgwidth, imgheight, noscale, basecardtype, cardpostype, cw.s, getsize)

    def calc_basecardposition_wx(self, (imgwidth, imgheight), noscale=False, basecardtype=None, cardpostype=None):
        """カードに配置した時の描画位置を返す。
        ベースとなる情報が無い時はpygame.Rect(0, 0, imgwidth, imgheight)を返す。
        """
        def getsize(resname):
            if resname.endswith("_noscale"):
                resname = resname[0:-len("_noscale")]
                return cw.setting.SIZE_RESOURCES["CardBg/" + resname]
            else:
                return cw.wins(cw.setting.SIZE_RESOURCES["CardBg/" + resname])
        return self._calc_basecardposition_impl(imgwidth, imgheight, noscale, basecardtype, cardpostype, cw.wins, getsize)

    def _calc_basecardposition_impl(self, imgwidth, imgheight, noscale, basecardtype, cardpostype, ss, getsize):
        if self.basecardtype:
            basecardtype = self.basecardtype

        if cardpostype == "LargeCard":
            x, y = (11, 18)
        elif cardpostype == "NormalCard":
            x, y = (3, 13)
        else:
            x, y = (0, 0)

        if basecardtype == "LargeCard":
            w, h = getsize("LARGE_noscale")
            bx, by = (11, 18)
            defpostype = "Center"
        elif basecardtype == "NormalCard":
            w, h = getsize("NORMAL_noscale")
            bx, by = (3, 13)
            defpostype = "TopLeft"
        elif basecardtype == "Bill": # 貼紙
            w, h = cw.SIZE_BILL
            bx, by = (163, 70)
            defpostype = "TopLeft"
        else:
            return pygame.Rect(0, 0, imgwidth, imgheight)

        if not noscale:
            x, y = ss((x, y))
            w, h = ss((w, h))
            bx, by = ss((bx, by))

        postype = self.postype
        if not postype in ("TopLeft", "Center"):
            postype = defpostype

        if postype == "Center":
            x = (w-imgwidth) // 2
            y = (h-imgheight) // 2
        elif postype == "TopLeft":
            x = bx
            y = by
        else:
            assert False

        if cardpostype:
            x -= bx
            y -= by

        return pygame.Rect(x, y, w, h)

    def __eq__(self, other):
        return isinstance(other, ImageInfo) and self.path == other.path and self.pcnumber == other.pcnumber and\
               self.postype == other.postype

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        if self.pcnumber:
            return "PC: %s" % (self.pcnumber)
        else:
            return "File: %s, Position Type: %s" % (self.path, self.postype)

def get_imageinfos(data, pcnumber=False):
    """PropertyなどのデータからImageInfoのlistを生成する。
    data: Propertyなど子に画像情報を持つ要素。
    pcnumber: プレイヤー番号イメージを使用するか。
    """
    seq = []
    if not data is None:
        if data.tag == "ImagePaths":
            for e in data: # 複数イメージの指定
                if e.tag == "ImagePath":
                    path = e.gettext(".", "")
                    if path:
                        postype = e.getattr(".", "positiontype", "Default")
                        seq.append(ImageInfo(path=path, postype=postype))
                elif pcnumber and e.tag == "PCNumber":
                    pcn = e.getint(".", 0)
                    if pcn:
                        seq.append(ImageInfo(pcnumber=pcn))
        else:
            path = data.getattr(".", "path", "") # イベントコンテントでの画像指定
            if path:
                postype = data.getattr(".", "positiontype", "Default")
                seq.append(ImageInfo(path=path, postype=postype))
            if pcnumber:
                pcn = data.getint(".", "pcNumber", 0) # イベントコンテントでのPC指定
                if pcn:
                    seq.append(ImageInfo(pcnumber=pcn))
            path = data.gettext("ImagePath", "") # 単一のパス指定
            if path:
                postype = data.getattr("ImagePath", "positiontype", "Default")
                seq.append(ImageInfo(path=path, postype=postype))
            if pcnumber:
                if path:
                    postype = data.getattr("ImagePath", "positiontype", "Default")
                    seq.append(ImageInfo(path=path, postype=postype))
                pcn = data.getint("PCNumber", 0) # 単一のPC指定
                if pcn:
                    seq.append(ImageInfo(pcnumber=pcn))
            epaths = data.find("ImagePaths") # 複数イメージの指定
            if not epaths is None:
                seq.extend(get_imageinfos(epaths, pcnumber=pcnumber))

    return seq

def get_imageinfos_p(prop, pcnumber=False):
    """cw.header.GetPropertyのインスタンスから
    ImageInfoのlistを生成する。
    """
    imgpaths = []
    imgpath = prop.properties.get("ImagePath", "")
    if imgpath:
        postype = prop.attrs.get("ImagePath", {}).get("positiontype", "Default")
        imgpaths.append(ImageInfo(imgpath, postype=postype))
    if pcnumber:
        pcn = prop.properties.get("PCNumber", "0")
        if pcn and 0 < int(pcn):
            imgpaths.append(ImageInfo(pcnumber=int(pcn)))
    for eimg, attrs, imgpath in prop.third.get("ImagePaths", []):
        if eimg == "ImagePath":
            if imgpath:
                postype = attrs.get("positiontype", "Default")
                imgpaths.append(ImageInfo(imgpath, postype=postype))
        elif eimg == "PCNumber":
            pcn = imgpath
            if pcn and 0 < int(pcn):
                imgpaths.append(ImageInfo(pcnumber=int(pcn)))

    return imgpaths

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
    def __init__(self, paths, bgtype, name="", premium="", can_loaded_scaledimage=False,
                 is_scenariocard=False, scedir="", anotherscenariocard=False):
        """
        カード画像と背景画像とカード名を合成・加工し、
        wxPythonとPygame両方で使える画像オブジェクトを生成する。
        """
        self.name = name
        self.paths = paths
        self.bgtype = bgtype
        self.image_mtime = {}
        self.premium = premium
        self.can_loaded_scaledimage = can_loaded_scaledimage
        self.anotherscenariocard = anotherscenariocard
        self.is_scenariocard = is_scenariocard
        self.scedir = scedir

        self.update_scale()

    def update_scale(self):
        self._bmp = None
        self._wxbmp = None
        self.image_mtime.clear()
        self._upwin = self._upwinmemo()
        self.cardbg = cw.cwpy.rsrc.cardbgs[self.bgtype]
        self.rect = self.cardbg.get_rect()

    def clear_cache(self):
        self._bmp = None
        self._wxbmp = None
        self.image_mtime.clear()

    def _upwinmemo(self):
        return (cw.UP_WIN, cw.UP_SCR, cw.cwpy.setting.fontsmoothing_cardname,
                 cw.cwpy.setting.basefont.copy(),
                 cw.cwpy.setting.fonttypes["cardname"],
                 cw.cwpy.setting.fonttypes["uselimit"])

    @property
    def wxcardbg(self):
        return cw.cwpy.rsrc.wxcardbgs[self.bgtype]

    @property
    def wxrect(self):
        wxsize = cw.wins(cw.setting.SIZE_RESOURCES["CardBg/" + self.bgtype])
        return pygame.Rect(0, 0, wxsize[0], wxsize[1])

    def is_modifiedfile(self):
        for info in self.paths:
            path = info.path
            if cw.binary.image.path_is_code(path):
                continue
            elif not self.is_scenariocard:
                path = cw.util.get_yadofilepath(path)

            if (not path or self.is_scenariocard) and not info.pcnumber:
                path = cw.util.get_materialpath(info.path, cw.M_IMG, system=not self.is_scenariocard,
                                                scedir=self.scedir)
            if not os.path.isfile(path):
                continue

            if self.image_mtime.get(path, 0) <> os.path.getmtime(path):
                return True
        return False

    def get_image(self):
        if self._bmp and not self.is_modifiedfile():
            return self._bmp.copy()

        image = self.cardbg.copy()
        w = image.get_width()
        h = image.get_height()

        if not cw.cwpy.setting.show_premiumicon:
            # プレミア画像
            if self.premium == "Rare":
                subimg = cw.cwpy.rsrc.cardbgs["RARE"]
                sw = subimg.get_width()
                sh = subimg.get_height()
                image.blit(subimg, (w-sw-cw.s(5), cw.s(5)))
                image.blit(subimg, (cw.s(5), h-sh-cw.s(5)))
            elif self.premium == "Premium":
                subimg = cw.cwpy.rsrc.cardbgs["PREMIER"]
                sw = subimg.get_width()
                sh = subimg.get_height()
                image.blit(subimg, (w-sw-cw.s(5), cw.s(5)))
                image.blit(subimg, (cw.s(5), h-sh-cw.s(5)))

        self.image_mtime.clear()
        for i, info in enumerate(self.paths):
            path = info.path
            pisc = cw.binary.image.path_is_code(path)
            if (not pisc and self.anotherscenariocard) or (not pisc and not self.is_scenariocard) or info.pcnumber:
                path = cw.util.get_yadofilepath(path)

            if (not path or (self.is_scenariocard and not self.anotherscenariocard)) and not info.pcnumber:
                path = cw.util.get_materialpath(info.path, cw.M_IMG, system=not self.is_scenariocard,
                                                scedir=self.scedir)

            if not pisc and os.path.isfile(path):
                self.image_mtime[path] = os.path.getmtime(path)

            if pisc or os.path.isfile(path):
                if isinstance(self.can_loaded_scaledimage, (list, tuple)):
                    can_loaded_scaledimage = self.can_loaded_scaledimage[i]
                else:
                    can_loaded_scaledimage = self.can_loaded_scaledimage
                subimg = cw.s(cw.util.load_image(path, True, can_loaded_scaledimage=can_loaded_scaledimage))

                baserect = info.calc_basecardposition(subimg.get_size(), noscale=False,
                                                      basecardtype="NormalCard",
                                                      cardpostype="NormalCard")

                cw.imageretouch.blit_2bitbmp_to_card(image, subimg, (cw.s(3)+baserect.x, cw.s(13)+baserect.y))

        font = cw.cwpy.rsrc.fonts["mcard_name"]
        colour = (0, 0, 0)
        if cw.cwpy.rsrc.cardnamecolorhints[self.bgtype] < cw.cwpy.rsrc.cardnamecolorborder:
            colour = (255, 255, 255)
        if self.name:
            subimg = font.render(self.name, cw.cwpy.setting.fontsmoothing_cardname, colour)
            w, h = subimg.get_size()

            left = cw.s(5)
            if w + left*2 > self.rect.w:
                size = (self.rect.w - left*2, h)
                subimg = cw.image.smoothscale(subimg.convert_alpha(), size, smoothing=cw.cwpy.setting.fontsmoothing_cardname)

            if cw.cwpy.setting.bordering_cardname:
                subimg2 = subimg.convert_alpha()
                if cw.cwpy.rsrc.cardnamecolorhints[self.bgtype] < cw.cwpy.rsrc.cardnamecolorborder:
                    subimg2.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_SUB)
                else:
                    subimg2.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
                subimg2 = cw.imageretouch.mul_alpha(subimg2, 92)
                for x in xrange(cw.s(5)-1, cw.s(5)+2):
                    for y in xrange(cw.s(5)-1, cw.s(5)+2):
                        if x <> cw.s(5) or y <> cw.s(5):
                            image.blit(subimg2, (x, y))

            image.blit(subimg, (left, cw.s(5)))
        self._bmp = image.copy()
        return image

    def get_cardimg(self, header):
        if header.negaflag:
            image = self.get_negaimg()
        else:
            image = self.get_image()

        if not hasattr(header, "type"):
            return image

        owner = header.get_owner()
        icony = cw.s(90)
        if isinstance(owner, cw.character.Character):
            # 適性値
            key = "HAND" + str(header.get_showed_vocation_level(owner))
            subimg = cw.cwpy.rsrc.stones[key]
            image.blit(subimg, cw.s((60, 90)))
            icony -= cw.s(15)

            # 使用回数(画像)
            if header.type == "SkillCard":
                key = "HAND" + str(header.get_uselimit_level() + 5)
                subimg = cw.cwpy.rsrc.stones[key]
                image.blit(subimg, cw.s((60, 75)))
                icony -= cw.s(15)

            # ホールド
            if header.ref_original() and header.ref_original().is_hold():
                subimg = cw.cwpy.rsrc.cardbgs["HOLD"]
                image.blit(subimg, cw.s((0, 0)))

            # ペナルティ
            if header.penalty:
                subimg = cw.cwpy.rsrc.cardbgs["PENALTY"]
                image.blit(subimg, cw.s((0, 0)))

            # ペナルティが自動選択されたため変更不可
            if owner.is_autoselectedpenalty(header):
                subimg = cw.cwpy.rsrc.pygamedialogs["FIXED"]
                image.blit(subimg, cw.s((20, 0)))

        uselimith = cw.s(0)
        if header.type in ("ItemCard", "BeastCard"):
            uselimit, maxn = header.get_uselimit()

            # 使用回数(数字)
            if maxn or header.recycle or (header.type == "BeastCard" and maxn):
                font = cw.cwpy.rsrc.fonts["card_uselimit"]
                s = str(uselimit)
                pos = (cw.s(5), self.rect[3] - font.get_height() - cw.s(4))
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
                uselimith = cw.s(font.get_height() - 2)

        if cw.cwpy.setting.show_cardkind and (not isinstance(owner, cw.character.Character) or\
                                             (cw.cwpy.selectedheader == header and cw.cwpy.areaid in cw.AREAS_TRADE)):
            # 種別アイコン(カード置場・荷物袋・移動中)
            if header.type == "SkillCard":
                icon = cw.cwpy.rsrc.pygamedialogs["STATUS8"]
            elif header.type == "ItemCard":
                icon = cw.cwpy.rsrc.pygamedialogs["STATUS9"]
            elif header.type == "BeastCard":
                icon = cw.cwpy.rsrc.pygamedialogs["STATUS10"]
            else:
                icon = None
            if icon:
                image.blit(icon, (cw.s(60), icony))

        if cw.cwpy.setting.show_premiumicon:
            if header.premium == "Premium":
                icon = cw.cwpy.rsrc.pygamedialogs["PREMIER_ICON"]
            elif header.premium == "Rare":
                icon = cw.cwpy.rsrc.pygamedialogs["RARE_ICON"]
            else:
                icon = None
            if icon:
                image.blit(icon, (cw.s(5), cw.s(90)-uselimith))

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
        if self._wxbmp and self._upwin == self._upwinmemo() and not self.is_modifiedfile():
            return cw.util.copy_wxbmp(self._wxbmp)
        self._upwin = self._upwinmemo()

        w, h = self.wxrect.size
        bmp = wx.EmptyBitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.DrawBitmap(self.wxcardbg, 0, 0, False)

        if not cw.cwpy.setting.show_premiumicon:
            # プレミア画像
            if self.premium == "Rare":
                subimg = cw.cwpy.rsrc.wxcardbgs["RARE"]
                sw = subimg.GetWidth()
                sh = subimg.GetHeight()
                dc.DrawBitmap(subimg, w-sw-cw.wins(5), cw.wins(5), True)
                dc.DrawBitmap(subimg, cw.wins(5), h-sh-cw.wins(5), True)
            elif self.premium == "Premium":
                subimg = cw.cwpy.rsrc.wxcardbgs["PREMIER"]
                sw = subimg.GetWidth()
                sh = subimg.GetHeight()
                dc.DrawBitmap(subimg, w-sw-cw.wins(5), cw.wins(5), True)
                dc.DrawBitmap(subimg, cw.wins(5), h-sh-cw.wins(5), True)

        for i, info in enumerate(self.paths):
            path = info.path
            pisc = cw.binary.image.path_is_code(path)
            if (not pisc and self.anotherscenariocard) or (not pisc and not self.is_scenariocard) or info.pcnumber:
                path = cw.util.get_yadofilepath(path)

            if (not path or (self.is_scenariocard and not self.anotherscenariocard)) and not info.pcnumber:
                path = cw.util.get_materialpath(info.path, cw.M_IMG, system=not self.is_scenariocard,
                                                scedir=self.scedir)

            if not pisc and os.path.isfile(path):
                self.image_mtime[path] = os.path.getmtime(path)

            if pisc or os.path.isfile(path):
                if isinstance(self.can_loaded_scaledimage, (list, tuple)):
                    can_loaded_scaledimage = self.can_loaded_scaledimage[i]
                else:
                    can_loaded_scaledimage = self.can_loaded_scaledimage

                # FIXME: wxPythonのメモリ上のデータからのwx.Image生成は
                #        異常に重いのでキャッシングする
                cachepath = path if not pisc else u""
                md5 = cw.util.get_md5_from_data(path) if pisc else u""
                cachekey = (cachepath, md5, cw.UP_WIN, can_loaded_scaledimage)
                if cachekey in cw.cwpy.sdata.resource_cache:
                    subimg = cw.cwpy.sdata.resource_cache[cachekey]
                else:
                    subimg = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                    cw.cwpy.sdata.sweep_resourcecache(cw.util.calc_wxbmpsize(subimg))
                    cw.cwpy.sdata.resource_cache[cachekey] = subimg

                subimg2 = cw.wins(subimg)

                baserect = info.calc_basecardposition_wx(subimg2.GetSize(), noscale=False,
                                                         basecardtype="NormalCard",
                                                         cardpostype="NormalCard")

                cw.imageretouch.wxblit_2bitbmp_to_card(dc, subimg2, cw.wins(3)+baserect.x, cw.wins(13)+baserect.y, True,
                                                       bitsizekey=subimg)

        pixelsize = cw.cwpy.setting.fonttypes["cardname"][2]
        if wx.VERSION[0] < 3:
            pixelsize += 1
        if cw.cwpy.setting.fontsmoothing_cardname:
            font = cw.cwpy.rsrc.get_wxfont("cardname", pixelsize=cw.wins(pixelsize)*2, adjustsizewx3=False)
        else:
            font = cw.cwpy.rsrc.get_wxfont("cardname", pixelsize=cw.wins(pixelsize), adjustsizewx3=False)
        dc.SetFont(font)
        if self.name:
            white = cw.cwpy.rsrc.cardnamecolorhints[self.bgtype] < cw.cwpy.rsrc.cardnamecolorborder
            quality = None if cw.cwpy.setting.fontsmoothing_cardname else (wx.IMAGE_QUALITY_NEAREST if 3 <= wx.VERSION[0] else wx.IMAGE_QUALITY_NORMAL)
            cw.util.draw_antialiasedtext(dc, self.name, cw.wins(5), cw.wins(5), white, self.wxrect.width, cw.wins(5),
                                         quality=quality, scaledown=cw.cwpy.setting.fontsmoothing_cardname,
                                         alpha=128, bordering=cw.cwpy.setting.bordering_cardname)

        dc.SelectObject(wx.NullBitmap)

        self._wxbmp = bmp
        return cw.util.copy_wxbmp(self._wxbmp)

    def get_cardwxbmp(self, header, test_aptitude=None):
        if header.negaflag:
            image = self.get_wxnegabmp()
        else:
            image = self.get_wxbmp()

        if not hasattr(header, "type"):
            return image

        dc = wx.MemoryDC()
        dc.SelectObject(image)

        owner = header.get_owner()
        icony = cw.wins(90)
        if isinstance(owner, cw.character.Character):
            # 適性値
            if test_aptitude:
                tester = test_aptitude
            else:
                tester = owner
            key = "HAND" + str(header.get_showed_vocation_level(tester))
            subimg = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(subimg, cw.wins(60), cw.wins(90), True)
            icony -= cw.wins(15)

            # 使用回数(画像)
            if header.type == "SkillCard":
                key = "HAND" + str(header.get_uselimit_level() + 5)
                subimg = cw.cwpy.rsrc.wxstones[key]
                dc.DrawBitmap(subimg, cw.wins(60), cw.wins(75), True)
                icony -= cw.wins(15)

            # ホールド
            if header.ref_original() and header.ref_original().is_hold():
                subimg = cw.cwpy.rsrc.wxcardbgs["HOLD"]
                dc.DrawBitmap(subimg, cw.wins(0), cw.wins(0), True)

            # ペナルティ
            if header.penalty:
                subimg = cw.cwpy.rsrc.wxcardbgs["PENALTY"]
                dc.DrawBitmap(subimg, cw.wins(0), cw.wins(0), True)

            # ペナルティが自動選択されたため変更不可
            if owner.is_autoselectedpenalty(header):
                subimg = cw.cwpy.rsrc.dialogs["FIXED"]
                dc.DrawBitmap(subimg, cw.wins(20), cw.wins(0), True)

        uselimith = cw.wins(0)
        if header.type in ("ItemCard", "BeastCard"):
            uselimit, maxn = header.get_uselimit()

            # 使用回数(数字)
            if maxn or header.recycle or (header.type == "BeastCard" and maxn):
                pixelsize = cw.cwpy.setting.fonttypes["uselimit"][2]
                bold = wx.BOLD if cw.cwpy.setting.fonttypes["uselimit"][3 if cw.UP_SCR <= 1 else 4] else wx.NORMAL
                italic = wx.ITALIC if cw.cwpy.setting.fonttypes["uselimit"][5] else wx.NORMAL
                if wx.VERSION[0] < 3:
                    pixelsize += 1
                font = cw.cwpy.rsrc.get_wxfont("uselimit", pixelsize=cw.wins(pixelsize), style=italic, weight=bold, adjustsizewx3=False)
                dc.SetFont(font)
                s = str(uselimit)
                pos = (cw.wins(5), self.wxrect[3] - cw.wins(pixelsize) - cw.wins(4))
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
                uselimith = cw.wins(pixelsize - 2)

        if cw.cwpy.setting.show_cardkind and (not isinstance(owner, cw.character.Character) or\
                                             (cw.cwpy.selectedheader == header and cw.cwpy.areaid in cw.AREAS_TRADE)):
            # 種別アイコン(カード置場・荷物袋・移動中)
            if header.type == "SkillCard":
                icon = cw.cwpy.rsrc.dialogs["STATUS8"]
            elif header.type == "ItemCard":
                icon = cw.cwpy.rsrc.dialogs["STATUS9"]
            elif header.type == "BeastCard":
                icon = cw.cwpy.rsrc.dialogs["STATUS10"]
            else:
                icon = None
            if icon:
                dc.DrawBitmap(icon, cw.wins(60), icony, True)
                icony -= cw.wins(16)

        if not isinstance(owner, cw.character.Character) and test_aptitude:
            # 適性値
            key = "HAND" + str(header.get_showed_vocation_level(test_aptitude))
            subimg = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(subimg, cw.wins(60), icony, True)

        if cw.cwpy.setting.show_premiumicon:
            if header.premium == "Premium":
                icon = cw.cwpy.rsrc.dialogs["PREMIER_ICON"]
            elif header.premium == "Rare":
                icon = cw.cwpy.rsrc.dialogs["RARE_ICON"]
            else:
                icon = None
            if icon:
                dc.DrawBitmap(icon, cw.wins(5), cw.wins(90)-uselimith, True)

        dc.SelectObject(wx.NullBitmap)

        return image

    def get_wxnegabmp(self):
        image = self.get_wxbmp()
        return cw.imageretouch.to_negative_for_wxcard(image)

    def get_wxclickedbmp(self, header, wxbmp, test_aptitude=None):
        size = (self.wxrect.width * 9 / 10, self.wxrect.height * 9 / 10)
        if wxbmp:
            negaimg = wxbmp
        else:
            negaimg = self.get_cardwxbmp(header, test_aptitude=test_aptitude)

        image = cw.util.convert_to_image(negaimg)
        image = image.Rescale(size[0], size[1], quality=cw.RESCALE_QUALITY)
        return image.ConvertToBitmap()

    def update(self, card):
        pass

class LargeCardImage(CardImage):
    def __init__(self, paths, bgtype, name="", premium="", can_loaded_scaledimage=False,
                 is_scenariocard=False, scedir="", anotherscenariocard=False):
        CardImage.__init__(self, paths, "LARGE", name, premium, can_loaded_scaledimage, is_scenariocard,
                           scedir=scedir, anotherscenariocard=anotherscenariocard)

    def get_image(self):
        image = self.cardbg.copy()
        w = image.get_width()
        h = image.get_height()

        # プレミア画像
        if self.premium == "Rare":
            subimg = cw.cwpy.rsrc.cardbgs["RARE"]
            sw = subimg.get_width()
            sh = subimg.get_height()
            image.blit(subimg, (w-sw-cw.s(5), cw.s(5)))
            image.blit(subimg, (cw.s(5), h-sh-cw.s(5)))
        elif self.premium == "Premium":
            subimg = cw.cwpy.rsrc.cardbgs["PREMIER"]
            sw = subimg.get_width()
            sh = subimg.get_height()
            image.blit(subimg, (w-sw-cw.s(5), cw.s(5)))
            image.blit(subimg, (cw.s(5), h-sh-cw.s(5)))

        for i, info in enumerate(self.paths):
            path = info.path
            pisc = cw.binary.image.path_is_code(path)
            if (not pisc and self.anotherscenariocard) or (not pisc and not self.is_scenariocard) or info.pcnumber:
                path = cw.util.get_yadofilepath(path)

            if (not path or (self.is_scenariocard and not self.anotherscenariocard)) and not info.pcnumber:
                path = cw.util.get_materialpath(info.path, cw.M_IMG, system=not self.is_scenariocard,
                                                scedir=self.scedir)

            if not pisc and os.path.isfile(path):
                self.image_mtime[path] = os.path.getmtime(path)

            if pisc or os.path.isfile(path):
                if isinstance(self.can_loaded_scaledimage, (list, tuple)):
                    can_loaded_scaledimage = self.can_loaded_scaledimage[i]
                else:
                    can_loaded_scaledimage = self.can_loaded_scaledimage
                subimg = cw.s(cw.util.load_image(path, True, can_loaded_scaledimage=can_loaded_scaledimage))

                baserect = info.calc_basecardposition(subimg.get_size(), noscale=False,
                                                      basecardtype="LargeCard",
                                                      cardpostype="LargeCard")

                cw.imageretouch.blit_2bitbmp_to_card(image, subimg, (cw.s(11)+baserect.x, cw.s(18)+baserect.y))

        font = cw.cwpy.rsrc.fonts["pcard_name"]
        if self.name:
            subimg = font.render(self.name, cw.cwpy.setting.fontsmoothing_cardname, (0, 0, 0))
            w, h = subimg.get_size()

            if w + cw.s(10) > self.rect.w:
                size = (self.rect.w - cw.s(10), h)
                subimg = cw.image.smoothscale(subimg.convert_alpha(), size, smoothing=cw.cwpy.setting.fontsmoothing_cardname)

            if cw.cwpy.setting.bordering_cardname:
                subimg2 = subimg.convert_alpha()
                subimg2.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
                subimg2 = cw.imageretouch.mul_alpha(subimg2, 92)
                for x in xrange(cw.s(5)-1, cw.s(5)+2):
                    for y in xrange(cw.s(5)-1, cw.s(5)+2):
                        if x <> cw.s(5) or y <> cw.s(5):
                            image.blit(subimg2, (x, y))

            image.blit(subimg, cw.s((5, 5)))

        return image

    def get_wxbmp(self):
        w = self.wxcardbg.GetWidth()
        h = self.wxcardbg.GetHeight()
        bmp = wx.EmptyBitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.DrawBitmap(self.wxcardbg, 0, 0, False)

        # プレミア画像
        if self.premium == "Rare":
            subimg = cw.cwpy.rsrc.wxcardbgs["RARE"]
            sw = subimg.GetWidth()
            sh = subimg.GetHeight()
            dc.DrawBitmap(subimg, w-sw-cw.wins(5), cw.wins(5), True)
            dc.DrawBitmap(subimg, cw.wins(5), h-sh-cw.wins(5), True)
        elif self.premium == "Premium":
            subimg = cw.cwpy.rsrc.wxcardbgs["PREMIER"]
            sw = subimg.GetWidth()
            sh = subimg.GetHeight()
            dc.DrawBitmap(subimg, w-sw-cw.wins(5), cw.wins(5), True)
            dc.DrawBitmap(subimg, cw.wins(5), h-sh-cw.wins(5), True)

        for i, info in enumerate(self.paths):
            path = info.path
            pisc = cw.binary.image.path_is_code(path)
            if (not pisc and self.anotherscenariocard) or (not pisc and not self.is_scenariocard) or info.pcnumber:
                path = cw.util.get_yadofilepath(path)

            if (not path or (self.is_scenariocard and not self.anotherscenariocard)) and not info.pcnumber:
                path = cw.util.get_materialpath(info.path, cw.M_IMG, system=not self.is_scenariocard,
                                                scedir=self.scedir)

            if not pisc and os.path.isfile(path):
                self.image_mtime[path] = os.path.getmtime(path)

            if pisc or os.path.isfile(path):
                if isinstance(self.can_loaded_scaledimage, (list, tuple)):
                    can_loaded_scaledimage = self.can_loaded_scaledimage[i]
                else:
                    can_loaded_scaledimage = self.can_loaded_scaledimage
                subimg = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                subimg2 = cw.wins(subimg)

                baserect = info.calc_basecardposition_wx(subimg2.GetSize(), noscale=False,
                                                         basecardtype="LargeCard",
                                                         cardpostype="LargeCard")

                cw.imageretouch.wxblit_2bitbmp_to_card(dc, subimg2, cw.wins(11)+baserect.x, cw.wins(18)+baserect.y, True,
                                                       bitsizekey=subimg)

        pixelsize = cw.cwpy.setting.fonttypes["ccardname"][2]
        if wx.VERSION[0] < 3:
            pixelsize += 1
        if cw.cwpy.setting.fontsmoothing_cardname:
            font = cw.cwpy.rsrc.get_wxfont("ccardname", pixelsize=cw.wins(pixelsize)*2, adjustsizewx3=False)
        else:
            font = cw.cwpy.rsrc.get_wxfont("ccardname", pixelsize=cw.wins(pixelsize), adjustsizewx3=False)
        dc.SetFont(font)
        if self.name:
            white = False
            quality = None if cw.cwpy.setting.fontsmoothing_cardname else (wx.IMAGE_QUALITY_NEAREST if 3 <= wx.VERSION[0] else wx.IMAGE_QUALITY_NORMAL)
            cw.util.draw_antialiasedtext(dc, self.name, cw.wins(5), cw.wins(5), white, w, cw.wins(6),
                                         quality=quality, scaledown=cw.cwpy.setting.fontsmoothing_cardname,
                                         alpha=128, bordering=cw.cwpy.setting.bordering_cardname)

        dc.SelectObject(wx.NullBitmap)

        return bmp

class CharacterCardImage(CardImage):
    def __init__(self, ccard, pos_noscale=(0, 0), can_loaded_scaledimage=False, is_scenariocard=False,
                 scedir=""):
        self.ccard = ccard
        self._pos_noscale = pos_noscale
        self.can_loaded_scaledimage = can_loaded_scaledimage
        self.anotherscenariocard = False
        self.is_scenariocard = is_scenariocard
        self.image_mtime = {}
        self.scedir = scedir
        self.update_scale()

    def update_scale(self):
        # カード画像
        self.set_faceimgs(self.ccard.imgpaths, self.can_loaded_scaledimage)
        # フォント画像(カード名)
        self.set_nameimg(self.ccard.name)
        # フォント画像(レベル)
        self.set_levelimg(self.ccard.level)
        # rect
        self.rect = pygame.Rect(cw.s(self._pos_noscale), cw.s((95, 130)))

    def set_faceimgs(self, paths, can_loaded_scaledimage):
        self.paths = paths
        self.can_loaded_scaledimage = can_loaded_scaledimage
        self.cardimgs = []
        for info in self.paths:
            path = info.path
            if not cw.binary.image.path_is_code(path) and isinstance(self.ccard, cw.sprite.card.PlayerCard) and\
                    not self.is_scenariocard:
                path = cw.util.get_yadofilepath(path)
            self.cardimgs.append(cw.s(cw.util.load_image(path, True, can_loaded_scaledimage=self.can_loaded_scaledimage)))

    def set_nameimg(self, name):
        if name:
            font = cw.cwpy.rsrc.fonts["pcard_name"]
            self.nameimg = font.render(name, cw.cwpy.setting.fontsmoothing_cardname, (0, 0, 0))
            w, h = self.nameimg.get_size()

            if w + cw.s(10) > cw.s(95):
                size = (cw.s(95 - 10), h)
                self.nameimg = cw.image.smoothscale(self.nameimg.convert_alpha(), size, smoothing=cw.cwpy.setting.fontsmoothing_cardname)
        else:
            self.nameimg = None

    def set_levelimg(self, level):
        font = cw.cwpy.rsrc.fonts["pcard_level"]
        bgname = self.get_cardbgname(self.ccard)
        cardbg = cw.cwpy.rsrc.cardbgs[bgname]
        w = cardbg.get_width() + cw.s(4)

        overhang = 0
        h = 0
        for n in xrange(10):
            c = str(n)
            size = font.size(c)
            h = max(h, size[1])
            if font.get_italic():
                overhang = max(overhang, size[0] - font.size_withoutoverhang(c)[0])
        size = (w, h)
        self.levelimg = pygame.Surface(size, pygame.locals.SRCALPHA).convert_alpha()

        w -= overhang
        s = str(level)
        for char in reversed(s):
            subimg = font.render(char, True, (0, 0, 0))
            w -= font.size_withoutoverhang(char)[0]
            self.levelimg.blit(subimg, (w, cw.s(0)))

        top = 0x7fffffff
        right = 0
        for x in xrange(size[0]):
            for y in xrange(size[1]):
                color = self.levelimg.get_at((x, y))
                if color[3] <> 0:
                    color[3] = color[3] / 2
                    self.levelimg.set_at((x, y), color)
                    right = max(x, right)
                    top = min(y, top)

        # 実際の文字の位置に合わせて描画位置を調節
        if font.get_italic():
            adjust = cw.s(4)
        else:
            adjust = cw.s(6)
        if cardbg.get_width()-adjust < right:
            x = (cardbg.get_width()-adjust) - right
        elif right < cardbg.get_width()-cw.s(10):
            x = cardbg.get_width()-cw.s(10) - right
        else:
            x = cw.s(0)

        y = (font.get_height()-self.levelimg.get_height()) // 2
        if y + top < cw.s(5):
            y = -top + cw.s(5)

        self.levelimg_pos = (x, y)

    def update(self, ccard, header=None):
        # 画像合成
        bgname = self.get_cardbgname(ccard)
        self.image = cw.cwpy.rsrc.cardbgs[bgname].copy()

        # レベル
        if ccard.is_analyzable():
            font = cw.cwpy.rsrc.fonts["pcard_level"]
            self.image.blit(self.levelimg, self.levelimg_pos)

        # カード画像
        for cardimg, info in zip(self.cardimgs, self.paths):

            baserect = info.calc_basecardposition(cardimg.get_size(), noscale=False,
                                                  basecardtype="LargeCard",
                                                  cardpostype="LargeCard")

            cw.imageretouch.blit_2bitbmp_to_card(self.image, cardimg, (cw.s(11)+baserect.x, cw.s(18)+baserect.y))

        # 名前
        if self.nameimg:
            if cw.cwpy.setting.bordering_cardname:
                nameimg1 = self.nameimg
                nameimg2 = self.nameimg.convert_alpha()
                nameimg2.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
                if cw.cwpy.rsrc.cardnamecolorhints[bgname] < cw.cwpy.rsrc.cardnamecolorborder:
                    nameimg1, nameimg2 = nameimg2, nameimg1
                    nameimg2 = nameimg2.convert_alpha()
                nameimg2 = cw.imageretouch.mul_alpha(nameimg2, 92)
                for x in xrange(cw.s(5)-1, cw.s(5)+2):
                    for y in xrange(cw.s(5)-1, cw.s(5)+2):
                        if x <> cw.s(5) or y <> cw.s(5):
                            self.image.blit(nameimg2, (x, y))
                self.image.blit(nameimg1, cw.s((5, 5)))
            else:
                if cw.cwpy.rsrc.cardnamecolorhints[bgname] < cw.cwpy.rsrc.cardnamecolorborder:
                    nameimg = self.nameimg.copy()
                    nameimg.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
                else:
                    nameimg = self.nameimg
                self.image.blit(nameimg, cw.s((5, 5)))

        # ライフバー
        if ccard.is_analyzable() and not ccard.is_unconscious():
            def calc_barpos(guage):
                w, h = guage.get_size()
                lifeper = float(ccard.life) / ccard.maxlife
                barpos = (int(lifeper*(w+cw.s(1)) + 0.5) - (w+cw.s(1)), cw.s(1))
                return barpos

            lifebar = cw.cwpy.rsrc.statuses["LIFEBAR"]
            fpath_guage = cw.util.join_paths(cw.cwpy.skindir, "Resource/Image/Status/LIFEGUAGE2")
            fpath_lifemask = cw.util.join_paths(cw.cwpy.skindir, "Resource/Image/Status/LIFEGUAGE2_MASK")
            if cw.util.find_resource(fpath_guage, cw.M_IMG) and cw.util.find_resource(fpath_lifemask, cw.M_IMG):
                # LIFEGUAGE2がある場合、LIFEBARの上にLIFEGUAGE2を転写した上で
                # LIFEGUAGE2_MASKのアルファ値を反映する
                guage = cw.cwpy.rsrc.statuses["LIFEGUAGE2"]
                lifemask = cw.cwpy.rsrc.statuses["LIFEGUAGE2_MASK"]
                lifeimg = pygame.Surface(guage.get_size()).convert_alpha()
                lifeimg.fill((0, 0, 0, 0))
                lifeimg.blit(lifebar, calc_barpos(guage))
                lifeimg.blit(guage, (0, 0))
                lifemask = lifemask.convert_alpha()
                lifemask.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_MAX)
                lifeimg.blit(lifemask, (0, 0), special_flags=pygame.locals.BLEND_RGBA_MULT)
            else:
                # LIFEGUAGEは(5, 5)の位置をマスク色とする。CardWirthのライフバーイメージと互換性がある
                guage = cw.cwpy.rsrc.statuses["LIFEGUAGE"]
                lifeimg = pygame.Surface(guage.get_size()).convert()
                lifeimg.set_colorkey(guage.get_at((0, 0)), pygame.locals.RLEACCEL)
                lifeimg.blit(lifebar, calc_barpos(guage))
                lifeimg.blit(guage, (0, 0))

            self.image.blit(lifeimg, cw.s((8, 110)))

        if header:
            # 適性表示(カード移動時)
            key = "HAND" + str(header.get_showed_vocation_level(ccard))
            subimg = cw.cwpy.rsrc.stones[key]
            self.image.blit(subimg, cw.s((73, 95)))

        self._no_statusimg = self.image

        # ステータス画像追加
        self.update_statusimg(ccard, None)

    def update_statusimg(self, ccard, is_runningevent=None):
        """
        イメージのステータスアイコンを更新する。
        """
        self.image = self._no_statusimg.copy()
        seq = []
        az = ccard.is_analyzable()

        beastnum = ccard.has_beast()
        if beastnum: # 召喚獣所持(付帯召喚以外)
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["SUMMON"], beastnum, True, is_runningevent=is_runningevent))
        if ccard.is_poison(): # 中毒
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["BODY0"], ccard.poison if az else 0, is_runningevent=is_runningevent))
        if cw.cwpy.setting.show_statustime in ("True", "NotEventTime") and ccard.is_paralyze(): # 麻痺
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["BODY1"], ccard.paralyze if az else 0, is_runningevent=is_runningevent))
        if cw.cwpy.setting.show_statustime in ("True", "NotEventTime") and ccard.is_sleep(): # 睡眠
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND1"], ccard.mentality_dur if az else 0, is_runningevent=is_runningevent))
        if ccard.is_confuse(): # 混乱
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND2"], ccard.mentality_dur if az else 0, is_runningevent=is_runningevent))
        elif ccard.is_overheat(): # 激昂
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND3"], ccard.mentality_dur if az else 0, is_runningevent=is_runningevent))
        elif ccard.is_brave(): # 勇敢
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND4"], ccard.mentality_dur if az else 0, is_runningevent=is_runningevent))
        elif ccard.is_panic(): # 恐慌
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MIND5"], ccard.mentality_dur if az else 0, is_runningevent=is_runningevent))
        if cw.cwpy.setting.show_statustime in ("True", "NotEventTime") and ccard.is_bind(): # 呪縛
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC0"], ccard.bind if az else 0, is_runningevent=is_runningevent))
        if ccard.is_silence(): # 沈黙
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC1"], ccard.silence if az else 0, is_runningevent=is_runningevent))
        if ccard.is_faceup(): # 暴露
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC2"], ccard.faceup if az else 0, is_runningevent=is_runningevent))
        if ccard.is_antimagic(): # 魔法無効化
            seq.append(self._put_number(cw.cwpy.rsrc.statuses["MAGIC3"], ccard.antimagic if az else 0, is_runningevent=is_runningevent))
        if ccard.enhance_act > 0: # 行動力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP0"], ccard.enhance_act, ccard.enhance_act_dur if az else 0, is_runningevent=is_runningevent)
        elif ccard.enhance_act < 0: # 行動力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN0"], ccard.enhance_act, ccard.enhance_act_dur if az else 0, is_runningevent=is_runningevent)
        if ccard.enhance_avo > 0: # 回避力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP1"], ccard.enhance_avo, ccard.enhance_avo_dur if az else 0, is_runningevent=is_runningevent)
        elif ccard.enhance_avo < 0: # 回避力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN1"], ccard.enhance_avo, ccard.enhance_avo_dur if az else 0, is_runningevent=is_runningevent)
        if ccard.enhance_res > 0: # 抵抗力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP2"], ccard.enhance_res, ccard.enhance_res_dur if az else 0, is_runningevent=is_runningevent)
        elif ccard.enhance_res < 0: # 抵抗力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN2"], ccard.enhance_res, ccard.enhance_res_dur if az else 0, is_runningevent=is_runningevent)
        if ccard.enhance_def > 0: # 防御力強化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["UP3"], ccard.enhance_def, ccard.enhance_def_dur if az else 0, is_runningevent=is_runningevent)
        elif ccard.enhance_def < 0: # 防御力弱化
            self._put_enhanceimg(seq, cw.cwpy.rsrc.statuses["DOWN3"], ccard.enhance_def, ccard.enhance_def_dur if az else 0, is_runningevent=is_runningevent)

        x = cw.s(7)
        if ccard.is_analyzable() and not ccard.is_unconscious():
            y = cw.s(92)
        else:
            y = cw.s(107)

        clip = None
        index = 0
        for subimg in seq:
            pos = (x + index / 5 * cw.s(17), y - index * cw.s(17) + index / 5 * cw.s(85))
            if isinstance(subimg, pygame.Surface):
                self.image.blit(subimg, pos)
                index += 1
                size = subimg.get_size()
            else:
                self.image.fill(subimg[0], pygame.Rect(pos, subimg[1]))
                size = subimg[1]

            clip2 = pygame.Rect(pos[0]+ccard.rect.left, pos[1]+ccard.rect.top, size[0], size[1])
            if clip:
                clip.union_ip(clip2)
            else:
                clip = clip2

        return clip

    def _put_number(self, image, num, always=False, is_runningevent=None):
        if is_runningevent is None:
            is_runningevent = cw.cwpy.is_runningevent()
        is_runningevent = bool(is_runningevent)
        is_runningevent &= cw.cwpy.is_playingscenario()
        is_runningevent &= not cw.cwpy.areaid in cw.AREAS_SP
        is_runningevent &= not (cw.cwpy.event.in_cardeffectmotion and not cw.cwpy.is_battlestatus())
        is_runningevent &= not cw.cwpy.is_reloading()
        if (always or cw.cwpy.setting.show_statustime == "True" or\
                    (cw.cwpy.setting.show_statustime == "NotEventTime" and not is_runningevent)) and num:
            image = cw.util.put_number(image, num)
        return image

    def _put_enhanceimg(self, seq, bmp, value, duration, is_runningevent):
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
        bmp = self._put_number(bmp, duration, is_runningevent=is_runningevent)
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

    def get_cardwxbmp(self, header, test_aptitude=None):
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
        subimg = font.render(line, False, color)
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
            subimg = font.render(line, False, bcolor)
            if sline:
                subimg2 = font.render(u"―", False, bcolor)
                size = (subimg.get_width() + cw.s(10), lineheight)
                subimg2 = pygame.transform.scale(subimg2, size)
                subimg.blit(subimg2, cw.s((-5, 0)))
            if vertical:
                subimg = pygame.transform.rotate(subimg, -90)
            img.blit(subimg, (x - 1, y - 1))
            img.blit(subimg, (x + 1, y - 1))
            img.blit(subimg, (x - 1, y + 1))
            img.blit(subimg, (x + 1, y + 1))
        subimg = font.render(line, False, color)
        if sline:
            subimg2 = font.render(u"―", False, color)
            size = (subimg.get_width() + cw.s(10), lineheight)
            subimg2 = pygame.transform.scale(subimg2, size)
            subimg.blit(subimg2, cw.s((-5, 0)))
        if vertical:
            subimg = pygame.transform.rotate(subimg, -90)

        img.blit(subimg, (x, y))

        if vertical:
            x -= lineheight
        else:
            y += lineheight

    image.blit(img, rect.topleft)

def get_textcellfont(size, face, color, bold, italic,
                     uline, vertical, antialiased):
    """テキストセル用のフォントを生成し、
    (font, lineheight)を返す。
    """
    font = cw.imageretouch.Font(face, -size, bold, italic)
    if uline:
        font.set_underline(True)

    return font, font.get_linesize()

def create_colorcell(size, color1, gradient, color2):
    """ブレンド前のカラーセルを生成し、
    pygame.Surfaceのインスタンスを返す。
    size: セルのサイズ
    color1: 基本色
    gradient: グラデーション方向。
              "None","LeftToRight","TopToBottom"のいずれか
    color2: 終端色
    """
    key = (size, color1, gradient, color2)
    image = cw.cwpy.sdata.resource_cache.get(key, None)
    if image:
        return image

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

    cw.cwpy.sdata.sweep_resourcecache(cw.util.calc_imagesize(image))
    cw.cwpy.sdata.resource_cache[key] = image
    return image

#-------------------------------------------------------------------------------
# ユーティリティ
#-------------------------------------------------------------------------------

def zoomcard(image, scale):
    """カードをリサイズする。"""
    if scale == 1.0:
        return image
    elif 1.0 < scale:
        smoothing = cw.cwpy.setting.smoothing_card_up
    else:
        smoothing = cw.cwpy.setting.smoothing_card_down

    w, h = image.get_size()
    w = int(w * scale)
    h = int(h * scale)
    return smoothscale(image, (w, h), smoothing=smoothing, iscard=True)

def smoothscale_card(surface, size, smoothing=True):
    return smoothscale(surface, size, smoothing=smoothing, iscard=True)

def smoothscale(surface, size, smoothing=True, iscard=False):
    """surfaceをリサイズする。
    可能であればスムージングする。
    """
    if size == surface.get_size():
        return surface
    size = map(lambda a: max(1, a), size)

    if surface.get_height() <= 1:
        # FIXME: 環境によって、高さが1の画像に
        #        pygame.transform.smoothscale()を行うと
        #        稀にアクセス違反になる事がある
        return pygame.transform.scale(surface, size)

    if smoothing and size[0] % surface.get_width() == 0 and size[1] % surface.get_height() == 0:
        smoothing = False

    if smoothing:
        w, h = surface.get_size()
        if iscard and w < size[0] and h < size[1]:
            # FIXME: pygame.transform.smoothscale()で
            #        右端・下端が欠けてしまう問題への対処。
            #        右端・下端を二重化してから拡大・縮小する。
            #        この処理によって他の問題が出るか、
            #        pygame.transform.smoothscale()の問題が
            #        解消された場合は以下の処理を削除する。
            bmp = pygame.Surface((w+1, h+1)).convert(24)
            bmp = pygame.transform.scale(surface, (w+1, h+1))
            bmp.fill((0, 0, 0, 0))
            bmp.blit(surface, (0, 0))
            bmp.blit(surface.subsurface((w-1, 0, 1, h)), (w, 0))
            bmp.blit(surface.subsurface((0, h-1, w, 1)), (h, 0))
            bmp.set_at((w, h), surface.get_at((w-1, h-1)))
        else:
            if surface.get_bitsize() < 24:
                bmp = surface.convert(24)
            else:
                bmp = surface

        return pygame.transform.smoothscale(bmp, size)
    else:
        return pygame.transform.scale(surface, size)

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
    _bfSize = s[2]
    _bfReserved1 = s[3]
    _bfReserved2 = s[4]
    bfOffBits = s[5]
    if bfOffBits == 0:
        return data, True
    biSize = s[6]
    if biSize <> 40:
        return data, True
    biWidth = s[7]
    biHeight = s[8]
    _biPlanes = s[9]
    biBitCount = s[10]
    biCompression = s[11]
    _biSizeImage = s[12]
    _biXPixPerMeter = s[13]
    _biYPixPerMeter = s[14]
    biClrUsed = s[15]
    _biClrImporant = s[16]
    lineSize = ((biWidth * biBitCount + 31) / 32) * 4
    height = -biHeight if biHeight < 0 else biHeight
    if len(data) - bfOffBits <> lineSize * height:
        if threading.currentThread() <> cw.cwpy:
            # wxPythonは無理やり読み込んで壊れた画像を作ってしまうので
            # pygame側でエラーが出るか調べる
            data = cw.image.patch_rle4bitmap(data)
            with io.BytesIO(data) as f:
                try:
                    bmp = pygame.image.load(f)
                    return conv2wximage(bmp, biBitCount), True
                except:
                    pass
                f.close()
        # bfOffBitsをヘッダ直後に修正
        bfOffBits = 14 + 40
        if biCompression == 3:
            # ビットフィールド情報がある場合
            bfOffBits += 4 * 3
        if biBitCount in (1, 4, 8):
            if biClrUsed == 0:
                biClrUsed = biBitCount * biBitCount
            bfOffBits += biClrUsed * 4
        b = struct.pack("<I", bfOffBits)
        data = data[0:10] + b + data[14:]
        data = cw.image.patch_rle4bitmap(data)
        return data, False
    data = cw.image.patch_rle4bitmap(data)
    return data, True

def conv2wximage(image, biBitCount):
    """pygame.Surfaceをwx.Bitmapに変換する。
    image: pygame.Surface
    """
    w, h = image.get_size()

    if 32 <= biBitCount:
        buf = pygame.image.tostring(image, "RGBA")
        image = wx.ImageFromBufferRGBA(w, h, buf)
    else:
        buf = pygame.image.tostring(image, "RGB")
        image = wx.ImageFromBuffer(w, h, buf)

    return image

def patch_rle4bitmap(data):
    if len(data) < 14 + 40:
        return data
    s = struct.unpack("<BBIhhIIIiHHiIIIII", data[0:14+40])
    if s[0] <> ord('B'):
        return data
    if s[1] <> ord('M'):
        return data
    _bfSize = s[2]
    _bfReserved1 = s[3]
    _bfReserved2 = s[4]
    bfOffBits = s[5]
    if bfOffBits == 0:
        return data
    biSize = s[6]
    if biSize <> 40:
        return data
    biWidth = s[7]
    biHeight = s[8]
    _biPlanes = s[9]
    biBitCount = s[10]
    biCompression = s[11]
    if biCompression == 2: # RLE4
        # FIXME: RLE4の場合、メモリアクセス違反が発生する事がある(SDL_imageのバグ？)
        #        問題を避けるために予め展開する
        bmpdata = data[bfOffBits:]
        bpl = ((biWidth * biBitCount + 31) / 32) * 4
        h = -biHeight if biHeight < 0 else biHeight
        bmpdata = cw.imageretouch.decode_rle4data(bmpdata, h, bpl)

        f = cStringIO.StringIO()
        f.write(data[:2])
        f.write(struct.pack("<I", bfOffBits + len(bmpdata)))
        f.write(data[2+4:2+4+8+16])
        f.write(struct.pack("<I", 0))
        f.write(struct.pack("<I", len(bmpdata)))
        f.write(data[2+4+8+16+4+4:bfOffBits])
        f.write(bmpdata)
        data = f.getvalue()
        f.close()

    return data


def get_bmpdepth(data):
    """
    Bitmapデータのビット深度値を返す。
    正常なBitmapデータでない場合は0を返す。
    """
    if len(data) < 14 + 40:
        return 0
    s = struct.unpack("<BBIhhIIIiHHiIIIII", data[0:14+40])
    if s[0] <> ord('B'):
        return 0
    if s[1] <> ord('M'):
        return 0
    if 40 <= s[6]:
        biBitCount = s[10]
    else:
        s = struct.unpack("<BBIhhIIHhHH", data[0:14+12])
        biBitCount = s[10]
    return biBitCount


def get_bicompression(data):
    """
    Bitmapデータの圧縮方式値を返す。
    正常なBitmapデータでない場合はNoneを返す。
    """
    if len(data) < 14 + 40:
        return 0
    s = struct.unpack("<BBIhhIIIiHHiIIIII", data[0:14+40])
    if s[0] <> ord('B'):
        return 0
    if s[1] <> ord('M'):
        return 0
    if 40 <= s[6]:
        biCompression = s[11]
    else:
        biCompression = None

    return biCompression


def has_pngalpha(data):
    """
    PNGデータがα値を持つかを返す。
    正常なPNGデータでない場合はFalseを返す。
    """
    if len(data) < 8 + 25:
        return 0
    s = struct.unpack(">BBBBBBBBIBBBBIIBBBBBI", data[0:8+25])
    if s[0] <> 0x89 or s[1] <> 0x50 or s[2] <> 0x4E or s[3] <> 0x47 or\
            s[4] <> 0x0D or s[5] <> 0x0A or s[6] <> 0x1A or s[7] <> 0x0A:
        return 0
    if s[8] <> 13:
        return 0
    if s[9] <> ord('I') or s[10] <> ord('H') or s[11] <> ord('D') or s[12] <> ord('R'):
        return 0
    colortype = s[16]
    return colortype in (4, 6)


def get_1bitpalette(data):
    s = struct.unpack("<BBIhhII", data[0:14+4])
    biSize = s[6]
    s = struct.unpack("<BBBBBBBB", data[14+biSize:14+biSize+8])
    color1 = pygame.Color(s[0], s[1], s[2])
    color2 =  pygame.Color(s[4], s[5], s[6])
    return (color1, color2)


def main():
    pass

if __name__ == "__main__":
    main()
