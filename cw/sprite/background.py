#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import pygame
from pygame.locals import BLEND_MIN, BLEND_ADD, BLEND_SUB, BLEND_MULT

import cw
import base
import card


#-------------------------------------------------------------------------------
#　背景スプライト
#-------------------------------------------------------------------------------

BG_IMAGE = 0
BG_TEXT = 1
BG_COLOR = 2

class BackGround(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self.bgs = []
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert()
        self.rect = self.image.get_rect()
        self._in_playing = False
        self._elements = []
        self._doanime = False
        self._ttype = ("None", "None")
        # spritegroupに追加
        cw.cwpy.bggrp.add(self)

    def update_scale(self):
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert()
        self.rect = self.image.get_rect()
        if self._in_playing:
            # Jpy1アニメーション中の場合は再実行
            elements = self._elements
            doanime = self._doanime
            ttype = self._ttype
            def func():
                # アニメーション前の背景を復元
                self.reload(doanime=False, ttype=("None", "None"), redraw=True)
                if elements:
                    # 再実行
                    self.load(elements, doanime=doanime, ttype=ttype)
                else:
                    # 再実行
                    self.reload(doanime=doanime, ttype=ttype, redraw=True)
            cw.cwpy.exec_func(func)
        else:
            self._reload(doanime=self._doanime, ttype=("None", "None"), redraw=False, force=True)

    def update_skin(self, oldskindir, newskindir):
        pass

    def load_surface(self, path, mask, size, flag, doanime):
        """背景サーフェスを作成。
        path: 背景画像ファイルのパス。
        mask: (0, 0)の色でマスクするか否か。透過画像を使う場合は無視。
        size: 背景のサイズ。
        flag: 背景に対応するフラグ。
        """
        # 対応フラグチェック
        if not cw.cwpy.sdata.flags.get(flag, True):
            return None, False, False
        anime = False

        try:
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)
            else:
                mtime = 0

            # 画像読み込み
            ext = cw.util.splitext(path)[1].lower()

            if ext <> ".jpdc" and cw.cwpy.is_playingscenario() and (path, mtime, size, mask) in cw.cwpy.sdata.cache:
                return cw.cwpy.sdata.cache[(path, mtime, size, mask)], False, False

            if ext == ".jptx":
                image = cw.effectbooster.JptxImage(path, mask).get_image()
            elif ext == ".jpdc":
                image = cw.effectbooster.JpdcImage(mask, path).get_image()
            elif ext == ".jpy1":
                image = cw.effectbooster.JpyImage(path, mask, doanime=doanime).get_image()
                anime = True
            else:
                image = cw.util.load_image(path, mask, isback=True)
        except cw.event.EffectBreakError, ex:
            raise ex
        except cw.effectbooster.ScreenRescale, ex:
            cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")
            self._in_playing = True
            raise ex
        except Exception:
            cw.util.print_ex()
            return None, False, False

        # 指定したサイズに拡大縮小する
        if not image.get_size() in (size, cw.s((0, 0))):
            if cw.cwpy.setting.smoothscale_bg:
                if not (image.get_flags() & pygame.locals.SRCALPHA) and image.get_colorkey():
                    image = image.convert_alpha()
                image = pygame.transform.smoothscale(image, size)
            else:
                image = pygame.transform.scale(image, size)

        if not anime and cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.cache[(path, mtime, size, mask)] = image

        return image, anime, True

    def load(self, elements, doanime=True, ttype=("Default", "Default")):
        """背景画面を構成する。
        elements: BgImageElementのリスト。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        if self._in_playing:
            return False

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # 背景処理する前に、トランジション用スプライト作成
        transitspr = cw.sprite.transition.get_transition(ttype)
        oldbgs = list(self.bgs)
        self._elements = elements
        self._doanime = doanime
        self._ttype = ttype

        # 背景構築
        animated = False
        blitlist = []
        bginhrt = True
        update = False
        forcedraw = False
        for e in elements:
            left = e.getint("Location", "left")
            top = e.getint("Location", "top")
            pos = (left, top)
            width = e.getint("Size", "width")
            height = e.getint("Size", "height")
            size = (width, height)
            flag = e.gettext("Flag", "")
            visible = cw.cwpy.sdata.flags.get(flag, True) and size <> (0, 0) and\
                self.rect.colliderect(cw.s(pygame.Rect(pos, size)))

            def getcolor(e, xpath, r, g, b, a):
                r = e.getint(xpath, "r", r)
                g = e.getint(xpath, "g", g)
                b = e.getint(xpath, "b", b)
                a = e.getint(xpath, "a", a)
                return (r, g, b, a)

            if e.tag == "BgImage":
                # 背景画像
                mask = e.getbool(".", "mask", False)
                path = e.gettext("ImagePath", "")

                # 使用時イベント中なら使用したカードの素材から探す
                if e.getbool("ImagePath", "inusecard", False):
                    inusecard = True
                else:
                    imgpath = cw.util.get_inusecardmaterialpath(path, cw.M_IMG)
                    inusecard = os.path.isfile(imgpath)

                d = (path, inusecard, mask, size, pos, flag, visible)
                try:
                    animated2, update2, bginhrt2 = self._add_imagecell(blitlist, self.bgs, oldbgs, d, doanime)
                    animated |= animated2
                    bginhrt &= bginhrt2
                    update |= update2
                except cw.effectbooster.ScreenRescale:
                    return False # 中断

            elif e.tag == "TextCell":
                # テキストセル
                text = e.gettext("Text", "")
                face = e.gettext("Font", "")
                tsize = e.getint("Font", "size", 12)
                color = getcolor(e, "Color", 0, 0, 0, 255)
                bold = e.getbool("Font", "bold", False)
                italic = e.getbool("Font", "italic", False)
                underline = e.getbool("Font", "underline", False)
                strike = e.getbool("Font", "strike", False)
                vertical = e.getbool("Vertical", False)
                btype = e.getattr("Bordering", "type", "None")
                bcolor = getcolor(e, "Bordering/Color", 255, 255, 255, 255)
                bwidth = e.getint("Bordering", "width", 1)

                text = cw.sprite.message.rpl_specialstr(cw.util.decodewrap(text))

                d = (text, face, tsize, color, bold, italic, underline, strike, vertical,
                     btype, bcolor, bwidth, size, pos, flag, visible)
                if self._add_textcell(blitlist, self.bgs, oldbgs, d):
                    forcedraw = True

            elif e.tag == "ColorCell":
                # カラーセル
                blend = e.gettext("BlendMode", "Normal")
                color1 = getcolor(e, "Color", 255, 255, 255, 255)
                gradient = e.getattr("Gradient", "direction", "None")
                color2 = getcolor(e, "Gradient/EndColor", 0, 0, 0, 255)

                d = blend, color1, gradient, color2, size, pos, flag, visible
                if self._add_colorcell(blitlist, self.bgs, oldbgs, d):
                    forcedraw = True

            else:
                assert False

        update |= self.bgs <> oldbgs

        if bginhrt and not blitlist:
            update = False

        if update:
            self._load_after(bginhrt, blitlist, animated, transitspr, oldbgs, True)
        elif forcedraw:
            self._load_after(bginhrt, blitlist, animated, transitspr, oldbgs, False)
        else:
            # エフェクトブースターの一時描画で使ったスプライトはすべて削除
            cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")

        self._elements = []
        self._doanime = False
        self._ttype = ("None", "None")
        self._in_playing = False
        return update

    def reload(self, doanime=True, ttype=("Default", "Default"), redraw=True):
        return self._reload(doanime, ttype, redraw, False)

    def _reload(self, doanime=True, ttype=("Default", "Default"), redraw=True, force=False):
        """背景画面を再構成する。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        # 背景処理する前に、トランジション用スプライト作成
        transitspr = cw.sprite.transition.get_transition(ttype)
        oldbgs = list(self.bgs)
        # 背景再構築
        bgs = []

        animated = False
        blitlist = []
        bginhrt = True
        update = force
        forcedraw = False
        if doanime:
            self._doanime = doanime
            self._ttype = ttype

        for type, d in self.bgs:
            if type == BG_IMAGE:
                # 背景画像
                try:
                    animated2, update2, bginhrt2 = self._add_imagecell(blitlist, bgs, oldbgs, d, doanime)
                    animated |= animated2
                    update |= update2
                    bginhrt &= bginhrt2
                except cw.effectbooster.ScreenRescale:
                    return False # 中断

            elif type == BG_TEXT:
                # テキストセル
                if self._add_textcell(blitlist, bgs, oldbgs, d):
                    forcedraw = True

            elif type == BG_COLOR:
                # カラーセル
                if self._add_colorcell(blitlist, bgs, oldbgs, d):
                    forcedraw = True

            else:
                assert False

        update |= self.bgs <> bgs

        if bginhrt and not blitlist:
            update = False

        if update:
            self.bgs = bgs
            self._load_after(False, blitlist, animated, transitspr, oldbgs, redraw)
        elif forcedraw:
            self._load_after(False, blitlist, animated, transitspr, oldbgs, False)
        else:
            # エフェクトブースターの一時描画で使ったスプライトはすべて削除
            cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")

        self._doanime = False
        self._ttype = ("None", "None")
        self._in_playing = False
        return update

    def _add_imagecell(self, blitlist, bgs, oldbgs, d, doanime):
        path, inusecard, mask, size, pos, flag, visible = d
        basepath = path
        bginhrt = True

        if inusecard:
            path = cw.util.join_yadodir(path)
            path = cw.util.get_materialpathfromskin(path, cw.M_IMG)
        else:
            path = cw.util.get_materialpath(path, cw.M_IMG)

        if cw.cwpy.rsrc:
            path = cw.cwpy.rsrc.get_filepath(path)

        if not os.path.isfile(path):
            return False, False, bginhrt

        image, anime, update = self.load_surface(path, mask, cw.s(size), flag, doanime=doanime)

        ext = os.path.splitext(path)[1].lower()
        if ext <> ".jpdc" and pos == (0, 0) and size == cw.SIZE_AREA and visible and not mask and not flag:
            # 背景を覆ったので背景継承を取り消す
            del bgs[:]
            bginhrt = False

        if image and image.get_size() <> (0, 0):
            blitlist.append((BG_IMAGE, (image, pos, 0)))
            bgs.append((BG_IMAGE, (basepath, inusecard, mask, size, pos, flag, True)))
        else:
            bgs.append((BG_IMAGE, (basepath, inusecard, mask, size, pos, flag, False)))
            oldbgs.append((BG_IMAGE, (basepath, inusecard, mask, size, pos, flag, False)))

        return anime, update, bginhrt

    def _add_textcell(self, blitlist, bgs, oldbgs, d):
        text, face, tsize, color, bold, italic, underline, strike, vertical,\
            btype, bcolor, bwidth, size, pos, flag, visible = d
        visible = cw.cwpy.sdata.flags.get(flag, True) and size <> (0, 0) and\
            self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        d = (text, face, tsize, color, bold, italic, underline, strike, vertical,
             btype, bcolor, bwidth, size, pos, flag, visible)
        if visible:
            if btype == "Inline":
                # 縁取り形式2のみは事前にセル生成が可能
                image = cw.image.create_type2textcell(text, face, cw.s(tsize), color,
                    bold, italic, underline, strike, vertical,
                    cw.s(size), bcolor, bwidth)
                blitlist.append((BG_IMAGE, (image, pos, 0)))
            else:
                # アンチエイリアスの関係で後から描画
                if btype <> "Outline":
                    bcolor = None
                d2 = (text, face, tsize, color, bold, italic, underline, strike, vertical,
                      bcolor, size, pos)
                blitlist.append((BG_TEXT, d2))
            bgs.append((BG_TEXT, d))
        else:
            bgs.append((BG_TEXT, d))
            oldbgs.append((BG_TEXT, d))
        return visible

    def _add_colorcell(self, blitlist, bgs, oldbgs, d):
        blend, color1, gradient, color2, size, pos, flag, visible = d
        visible = cw.cwpy.sdata.flags.get(flag, True) and size <> (0, 0) and\
            self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        d = blend, color1, gradient, color2, size, pos, flag, visible
        if visible:
            image = cw.image.create_colorcell(cw.s(size), color1, gradient, color2)
            if blend == "Add":
                blendflag = BLEND_ADD
            elif blend == "Subtract":
                blendflag = BLEND_SUB
            elif blend == "Multiply":
                blendflag = BLEND_MULT
            else:
                blendflag = 0
            blitlist.append((BG_IMAGE, (image, pos, blendflag)))
            bgs.append((BG_COLOR, d))
        else:
            bgs.append((BG_COLOR, d))
            oldbgs.append((BG_COLOR, d))
        return visible

    def _load_after(self, bginhrt, blitlist, animated, transitspr, oldbgs, redraw):
        # 背景を更新する(呼び出し時点でエフェクトブースターは実行済み)
        if not bginhrt:
            self.image.fill((0, 0, 0))

        for type, d in blitlist:
            if type == BG_IMAGE:
                # 背景画像、カラーセル、縁取り形式2のテキストセル
                image, pos, flag = d
                if flag in (0, BLEND_MULT):
                    self.image.blit(image, cw.s(pos), None, flag)
                elif flag in (BLEND_ADD, BLEND_SUB):
                    cw.imageretouch.blend_1_50(self.image, cw.s(pos), image, flag)
                else:
                    assert False

            elif type == BG_TEXT:
                # 縁取り形式2以外のテキストセル
                text, face, tsize, color, bold, italic, underline, strike, vertical,\
                    bcolor, size, pos = d
                cw.image.draw_textcell(self.image, cw.s(pygame.Rect(pos, size)), text, face,
                    cw.s(tsize), color, bold, italic, underline, strike, vertical, bcolor)

            else:
                assert False

        # エフェクトブースターの一時描画で使ったスプライトはすべて削除
        cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")

        # トランジション効果で画面入り
        if redraw:
            if not animated and transitspr and not oldbgs == self.bgs:
                transitspr.add(cw.cwpy.bggrp)
                cw.animation.animate_sprite(transitspr, "transition", background=True)
                transitspr.remove(cw.cwpy.bggrp)
            else:
                cw.cwpy.draw()

class Curtain(base.SelectableSprite):
    def __init__(self, spritegrp, size_noscale, pos_noscale, color=None, cutarealist=None):
        """半透明のブルーバックスプライト。右クリックで解除。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        size: スプライトのサイズ。
        pos: 表示位置。
        color: カーテン色(不透明度含む)。
        """
        if color:
            self.color = color
        else:
            self.color = cw.cwpy.setting.curtaincolour
        base.SelectableSprite.__init__(self)
        self._pos_noscale = pos_noscale
        self._size_noscale = size_noscale
        self.image = pygame.Surface(cw.s(size_noscale)).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(pos_noscale)
        self.cutarealist = cutarealist
        self.cut_curtain()
        # spritegroupに追加
        spritegrp.add(self, layer="curtain")

    def cut_curtain(self):
        if self.cutarealist:
            self.image.set_colorkey((0, 0, 0))
            left_whole, top_whole = self.rect.topleft
            for cutarea in self.cutarealist:
                left, top, w, h = cw.s((cutarea))
                left, top = left - left_whole, top - top_whole
                self.image.fill((0, 0, 0), (left, top, w, h))

    def update_scale(self):
        self.image = pygame.Surface(cw.s(self._size_noscale)).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(self._pos_noscale)
        self.cut_curtain()

    def rclick_event(self):
        cw.cwpy.cancel_cardcontrol()

class BattleCardImage(card.CWPyCard):
    def __init__(self):
        """戦闘開始時のアニメーションに使うスプライト。
        cw.animation.battlestart を参照。
        """
        card.CWPyCard.__init__(self, "hidden")
        path = "Resource/Image/Card/BATTLE" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        # TODO scaleinfo
        cardimg = cw.image.CardImage(path, "ACTION", u"")
        image = cardimg.get_image()
        self.image = self._image = self.image_unzoomed = image
        self.rect = self._rect = self.image.get_rect()
        self.set_pos_noscale(center_noscale=(316, 142))
        self.clear_image()
        self.highspeed = True
        # spritegroupに追加
        cw.cwpy.topgrp.add(self, layer="battlecard")

    def update_battlestart(self):
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (8, 12)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (28, 40)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (56, 80)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        waitrate = (cw.cwpy.setting.dealspeed+1) * 4
        cw.cwpy.wait_frame(waitrate)
        cw.animation.animate_sprite(self, "hide")

    def update_image(self):
        pass

    def update_selection(self):
        pass

class InuseCardImage(card.CWPyCard):
    def __init__(self, user, header, status="normal", center=False, spritegrp=None, alpha=255):
        """使用中のカード画像スプライト。
        user: Character。
        header: 使用するカードのCardHeader。
        status: すぐ表示したくない場合は"hidden"を指定。
        center: 画面中央に表示するかどうか。
        spritegrp: 追加先のスプライトグループ。Noneの場合は自動選択。
        """
        card.CWPyCard.__init__(self, status)
        self.status = status
        self.user = user
        self.header = header
        self.center = center
        self.zoomsize_noscale = (32, 42)
        self.alpha = alpha

        self.update_scale()

        # spritegroupに追加
        if spritegrp:
            self.group = spritegrp
        elif center:
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
                self.group = cw.cwpy.mcardgrp
            else:
                self.group = cw.cwpy.pcardgrp
        elif isinstance(user, cw.sprite.card.PlayerCard):
            self.group = cw.cwpy.pcardgrp
        else:
            self.group = cw.cwpy.mcardgrp
        if user and not center:
            top = False
            sprites = self.group.sprites()[:]
            self.group.empty()
            index = sprites.index(user)
            self.group.add(sprites[:index+1])
            self.group.add(self)
            self.group.add(sprites[index+1:])
        else:
            self.group.add(self)

    def update_scale(self):
        self.header.negaflag = False
        image = self.header.get_cardimg()
        if self.alpha < 255:
            image.set_alpha(self.alpha)
        self.image = self._image = image
        self.rect = self._rect = image.get_rect()

        if not self.user.scale == 100 and not self.center:
            scale = self.user.scale / 100.0
            self.rect.size = (int(self.rect.width*scale), int(self.rect.height*scale))
            self.image = pygame.transform.smoothscale(self.image, self.rect.size)

        if self.center:
            self.set_pos_noscale(center_noscale=(316, 142))
        else:
            self.set_pos(center=self.user.rect.center)

        if self.status == "hidden":
            self.clear_image()

    def update_image(self):
        pass

    def update_selection(self):
        pass

class TargetArrow(base.CWPySprite):
    def __init__(self, target):
        """ターゲット選択する矢印画像スプライト。
        target: Character。
        """
        base.CWPySprite.__init__(self)
        self.target = target
        self.update_scale()
        # spritegroupに追加
        # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
            cw.cwpy.mcardgrp.add(self, layer="targetarrow")
        else:
            cw.cwpy.pcardgrp.add(self, layer="targetarrow")

    def update_scale(self):
        self.image = cw.cwpy.rsrc.statuses["TARGET"]
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.target.rect.right - cw.s(30), self.target.rect.bottom - cw.s(30))

class Jpy1TemporalSprite(base.CWPySprite):
    def __init__(self, background):
        """エフェクトブースターJpy1の一時描画用スプライト。
        Jpy1の読み込みがすべて終了したら、削除される。
        """
        base.CWPySprite.__init__(self)
        # image, rect作成。
        self.image = background
        self.rect = cw.s(pygame.Rect((0, 0), cw.SIZE_AREA))

        # spritegroupに追加
        cw.cwpy.topgrp.add(self, layer="jpytemporal")

class TitleCell(base.CWPySprite):
    def __init__(self, path, layer, y_noscale, iscard, selsprite):
        """起動画面のアニメーションに使用するスプライト。
        path: 表示するイメージのパス。
        y: Y座標。X位置は常に画面中央となる。
        """
        base.CWPySprite.__init__(self)
        self.layer = layer
        self.path = path
        self.y_noscale = y_noscale
        self.iscard = iscard
        if selsprite:
            self.selsprite = selsprite
        else:
            self.selsprite = self
        self.status = "hidden"
        self.frame = 0

        self.update_scale()

        self.animespeed = cw.cwpy.setting.fps / 3
        self.dealing_scales = [
            int(math.cos(math.radians(90.0 * i / self.animespeed)) * 100)
            for i in xrange(self.animespeed + 1)
                if i
        ]

        n = 255 / self.animespeed
        self.fade_params = [255 - n * i for i in xrange(self.animespeed + 1) if i]

    def get_selectedimage(self):
        return self.image

    def get_unselectedimage(self):
        return self.image

    def update_scale(self):
        if self.path == "white":
            self._image = pygame.surface.Surface(cw.s(cw.SIZE_AREA)).convert()
            self._image.fill((255, 255, 255))
        else:
            self._image = cw.s((cw.util.load_image(self.path, True), cw.setting.get_resourcesize(self.path)))
        self._srcalpha = bool(self._image.get_flags() & pygame.locals.SRCALPHA)
        self._rect = self._image.get_rect()
        x = (cw.s(cw.SIZE_AREA[0]) - self._rect.width) / 2
        self._rect.topleft = (x, cw.s(self.y_noscale))

        if self.iscard:
            if self.status == "hidden":
                self.clear_image()
        else:
            self.image = self._image
            self.set_imagealpha(0)
            self.rect = self._rect

        if not cw.cwpy.selection:
            cw.cwpy.selection = self.selsprite

    def lclick_event(self):
        cw.cwpy.cut_animation = True

    def rclick_event(self):
        cw.cwpy.cut_animation = True

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

        if not cw.cwpy.selection:
            cw.cwpy.selection = self.selsprite

    def update_deal(self):
        """
        カード表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame == self.animespeed:
            self.status = "normal"
            self.image = self._image
            self.rect = self._rect
            self.frame = 0
            return

        n = self.dealing_scales[::-1][self.frame]
        size = self._rect.w * n / 100, self._rect.h
        self.image = pygame.transform.scale(self._image, size)
        self.rect = self.image.get_rect(center=self._rect.center)
        self.frame += 1

    def update_hide(self):
        """
        カード非表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame == self.animespeed:
            self.status = "hidden"
            self.clear_image()
            self.frame = 0
            return

        n = self.dealing_scales[self.frame]
        size = self._rect.w * n / 100, self._rect.h
        self.image = pygame.transform.scale(self._image, size)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.frame += 1

    def update_fadein(self):
        """
        フェードインのアニメーションを呼び出すメソッド。
        """
        if self.frame == self.animespeed:
            self.status = "normal"
            self.set_imagealpha(255)
            self.frame = 0
            return

        alpha = self.fade_params[::-1][self.frame]
        self.set_imagealpha(alpha)
        self.frame += 1

    def update_fadein2(self):
        """
        倍速でフェードインする。
        """
        if self.frame >= self.animespeed:
            self.status = "normal"
            self.set_imagealpha(255)
            self.frame = 0
            return

        alpha = self.fade_params[::-1][self.frame]
        self.set_imagealpha(alpha)
        self.frame += 2

    def update_fadeout(self):
        """
        フェードアウトのアニメーションを呼び出すメソッド。
        """
        if self.frame == self.animespeed:
            self.status = "hidden"
            self.set_imagealpha(0)
            self.frame = 0
            return

        alpha = self.fade_params[self.frame]
        self.set_imagealpha(alpha)
        self.frame += 1

    def update_show(self):
        """
        ウェイト無しで表示する。
        """
        self.status = "normal"
        self.set_imagealpha(255)

    def update_vanish(self):
        """
        ウェイト無しで消去する。
        """
        self.status = "hidden"
        self.set_imagealpha(0)

    def clear_image(self):
        self.image = pygame.Surface((0, 0)).convert()
        self.rect = self.image.get_rect(center=self._rect.center)

    def set_imagealpha(self, alpha):
        if self._srcalpha:
            self.image = self._image.copy()
            self.image.fill((255, 255, 255, alpha), special_flags=pygame.locals.BLEND_RGBA_MIN)
        else:
            self.image.set_alpha(alpha)

class ClickableSprite(base.SelectableSprite):
    def __init__(self, getimage, getselimage, pos_noscale, spritegrp, lclickevent=None, rclickevent=None):
        """画面上に配置され、クリック可能なイメージ。
        """
        base.SelectableSprite.__init__(self)
        self._getimage = getimage
        self._getselimage = getselimage
        self._pos_noscale = pos_noscale
        self._lclickevent = lclickevent
        self._rclickevent = rclickevent
        self.update_scale()
        self.status = "normal"
        self.old_status = "normal"
        self.frame = 0

        spritegrp.add(self)

    def update_scale(self):
        self._image = self._getimage()
        self._clickedimage = pygame.transform.rotozoom(self._image, 0, 0.9)
        if self._getselimage:
            self._selimage = self._getselimage()
            self._selclickedimage = pygame.transform.rotozoom(self._selimage, 0, 0.9)
        else:
            self._selimage = cw.imageretouch.to_negative(self._image)
            self._selclickedimage = cw.imageretouch.to_negative(self._clickedimage)

        self.image = self._image
        self._rect = pygame.Rect(cw.s(self._pos_noscale), self._image.get_size())
        self._clickedrect = self._clickedimage.get_rect()
        self._clickedrect.center = self._rect.center
        self.rect = self._rect

    def get_unselectedimage(self):
        if self.status == "click":
            return self._clickedimage
        else:
            return self._image

    def get_selectedimage(self):
        if self.status == "click":
            return self._selclickedimage
        else:
            return self._selimage

    def lclick_event(self):
        """左クリックイベント。"""
        if self._lclickevent:
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            self._lclickevent()

    def rclick_event(self):
        """右クリックイベント。"""
        if self._rclickevent:
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            self._rclickevent()

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        self.update_selection()

    def update_click(self):
        """
        クリック時のアニメーションを呼び出すメソッド。
        """
        if self.frame == 0:
            self.image = self.get_selectedimage()
            self.rect = self._clickedrect
            self.status = "click"
        elif self.frame == 3:
            self.status = self.old_status
            self.image = self.get_selectedimage()
            self.rect = self._rect
            self.frame = 0
            return

        self.frame += 1

def main():
    pass

if __name__ == "__main__":
    main()
