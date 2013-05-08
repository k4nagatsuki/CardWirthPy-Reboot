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
        # spritegroupに追加
        cw.cwpy.bggrp.add(self)

    def update_scale(self):
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert()
        self.rect = self.image.get_rect()
        self.reload(doanime=False, ttype=("None", "None"))

    def update_skin(self, oldskindir, newskindir):
        for i, t in enumerate(self.bgs):
            type, d = t
            if type == BG_IMAGE:
                path, mask, size, pos, flag, visible = d
                if path.startswith(oldskindir):
                    path = path.replace(oldskindir, newskindir, 1)
                d = path, mask, size, pos, flag, visible
            self.bgs[i] = type, d

    def load_surface(self, path, mask, size, flag, doanime):
        """背景サーフェスを作成。
        path: 背景画像ファイルのパス。
        mask: (0, 0)の色でマスクするか否か。透過画像を使う場合は無視。
        size: 背景のサイズ。
        flag: 背景に対応するフラグ。
        """
        # 対応フラグチェック
        if not cw.cwpy.sdata.flags.get(flag, True):
            return None, False
        anime = False

        if cw.cwpy.is_playingscenario() and (path, size, mask) in cw.cwpy.sdata.cache:
            return cw.cwpy.sdata.cache[(path, size, mask)], False

        # 画像読み込み
        ext = os.path.splitext(path)[1].lower()

        if ext == ".jptx":
            image = cw.effectbooster.JptxImage(path, mask).get_image()
        elif ext == ".jpdc":
            image = cw.effectbooster.JpdcImage(mask, path).get_image()
        elif ext == ".jpy1":
            image = cw.effectbooster.JpyImage(path, mask, doanime=doanime).get_image()
            anime = True
        else:
            image = cw.util.load_image(path, mask)

        # 指定したサイズに拡大縮小する
        if not image.get_size() in (size, cw.s((0, 0))):
            if cw.cwpy.setting.smoothscale_bg:
                image = pygame.transform.smoothscale(image, size)
            else:
                image = pygame.transform.scale(image, size)

        if not anime and cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.cache[(path, size, mask)] = image

        return image, anime

    def load(self, elements, bginhrt, doanime=True, ttype=("Default", "Default")):
        """背景画面を構成する。
        elements: BgImageElementのリスト。
        bginhrt: Trueなら背景継承。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # 背景処理する前に、トランジション用スプライト作成
        transitspr = cw.sprite.transition.get_transition(ttype)
        oldbgs = list(self.bgs)

        # 背景継承するか否か
        if not bginhrt:
            self.bgs = []

        # 背景構築
        animated = False
        blitlist = []
        for e in elements:
            left = e.getint("Location", "left")
            top = e.getint("Location", "top")
            pos = (left, top)
            width = e.getint("Size", "width")
            height = e.getint("Size", "height")
            size = (width, height)
            flag = e.gettext("Flag", "")
            visible = cw.cwpy.sdata.flags.get(flag, True)

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

                if cw.cwpy.is_playingscenario() and cw.cwpy.areaid > 0:
                    path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
                else:
                    path = cw.util.join_paths(cw.cwpy.skindir, path)

                if not os.path.isfile(path):
                    fname = os.path.basename(path)
                    fname = os.path.splitext(fname)[0] + cw.cwpy.rsrc.ext_img
                    path = cw.util.join_paths(cw.cwpy.skindir, "Table", fname)

                d = (path, mask, size, pos, flag, visible)
                animated |= self._add_imagecell(blitlist, self.bgs, oldbgs, d, doanime)

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

                d = (text, face, tsize, color, bold, italic, underline, strike, vertical,
                     btype, bcolor, bwidth, size, pos, flag, visible)
                self._add_textcell(blitlist, self.bgs, oldbgs, d)

            elif e.tag == "ColorCell":
                # カラーセル
                blend = e.gettext("BlendMode", "Normal")
                color1 = getcolor(e, "Color", 255, 255, 255, 255)
                gradient = e.getattr("Gradient", "direction", "None")
                color2 = getcolor(e, "Gradient/EndColor", 0, 0, 0, 255)

                d = blend, color1, gradient, color2, size, pos, flag, visible
                self._add_colorcell(blitlist, self.bgs, oldbgs, d)

            else:
                assert False

        self._load_after(bginhrt, blitlist, animated, transitspr, oldbgs)

    def reload(self, doanime=True, ttype=("Default", "Default")):
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
        for type, d in self.bgs:
            if type == BG_IMAGE:
                # 背景画像
                animated |= self._add_imagecell(blitlist, bgs, oldbgs, d, doanime)

            elif type == BG_TEXT:
                # テキストセル
                self._add_textcell(blitlist, bgs, oldbgs, d)

            elif type == BG_COLOR:
                # カラーセル
                self._add_colorcell(blitlist, bgs, oldbgs, d)

            else:
                assert False

        self.bgs = bgs
        self._load_after(False, blitlist, animated, transitspr, oldbgs)

    def _add_imagecell(self, blitlist, bgs, oldbgs, d, doanime):
        path, mask, size, pos, flag, visible = d
        image, anime = self.load_surface(path, mask, cw.s(size), flag, doanime=doanime)

        if image:
            blitlist.append((BG_IMAGE, (image, pos, 0)))
            bgs.append((BG_IMAGE, (path, mask, size, pos, flag, True)))
        else:
            bgs.append((BG_IMAGE, (path, mask, size, pos, flag, False)))
            oldbgs.append((BG_IMAGE, (path, mask, size, pos, flag, False)))

        return anime

    def _add_textcell(self, blitlist, bgs, oldbgs, d):
        text, face, tsize, color, bold, italic, underline, strike, vertical,\
            btype, bcolor, bwidth, size, pos, flag, visible = d
        visible = cw.cwpy.sdata.flags.get(flag, True)
        d = (text, face, tsize, color, bold, italic, underline, strike, vertical,
             btype, bcolor, bwidth, size, pos, flag, visible)
        if visible:
            text = cw.sprite.message.rpl_specialstr(text)
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

    def _add_colorcell(self, blitlist, bgs, oldbgs, d):
        blend, color1, gradient, color2, size, pos, flag, visible = d
        visible = cw.cwpy.sdata.flags.get(flag, True)
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

    def _load_after(self, bginhrt, blitlist, animated, transitspr, oldbgs):
        # 背景を更新する(呼び出し時点でエフェクトブースターは実行済み)
        if not bginhrt:
            self.image = pygame.Surface(cw.s(cw.SIZE_SCR)).convert()

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
        if not animated and transitspr and not oldbgs == self.bgs:
            transitspr.add(cw.cwpy.bggrp)
            cw.animation.animate_sprite(transitspr, "transition")
            transitspr.remove(cw.cwpy.bggrp)

class Curtain(base.SelectableSprite):
    def __init__(self, spritegrp, size_noscale, pos_noscale, alpha=128):
        """半透明のブルーバックスプライト。右クリックで解除。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        size: スプライトのサイズ。
        pos: 表示位置。
        alpha: 透明度。
        """
        self.alpha = alpha
        base.SelectableSprite.__init__(self)
        self._pos_noscale = pos_noscale
        self._size_noscale = size_noscale
        self.image = pygame.Surface(cw.s(size_noscale)).convert()
        self.image.fill((0, 0, 80))
        self.image.set_alpha(self.alpha)
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(pos_noscale)
        # spritegroupに追加
        spritegrp.add(self, layer="curtain")

    def update_scale(self):
        self.image = pygame.Surface(cw.s(self._size_noscale)).convert()
        self.image.fill((0, 0, 80))
        self.image.set_alpha(self.alpha)
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(self._pos_noscale)

    def rclick_event(self):
        cw.cwpy.sounds["click"].play()

        # カード移動選択エリアだったら、事前に開いていたダイアログを開く
        if cw.cwpy.areaid in cw.AREAS_TRADE:
            cw.cwpy.call_predlg()
        # それ以外だったら特殊エリアをクリアする
        else:
            cw.cwpy.clear_specialarea()

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
        cw.cwpy.pcardgrp.add(self, layer="battlecard")

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
        waitrate = cw.cwpy.setting.dealspeed * 4
        cw.cwpy.wait_frame(waitrate)
        cw.animation.animate_sprite(self, "hide")

    def update_image(self):
        pass

    def update_selection(self):
        pass

class InuseCardImage(card.CWPyCard):
    def __init__(self, user, header, status="normal", center=False, layer="inusecard"):
        """使用中のカード画像スプライト。
        user: Character。
        header: 使用するカードのCardHeader。
        status: すぐ表示したくない場合は"hidden"を指定。
        center: 画面中央に表示するかどうか。
        """
        card.CWPyCard.__init__(self, status)
        self.status = status
        self.user = user
        self.header = header
        self.center = center
        self.zoomsize_noscale = (32, 42)

        self.update_scale()

        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer=layer)

    def update_scale(self):
        image = self.header.get_cardimg()
        self.image = self._image = image
        self.rect = self._rect = image.get_rect()

        if not self.user.scale == 100 and not self.center:
            scale = self.user.scale / 100.0
            self.image = pygame.transform.rotozoom(self.image, 0, scale)
            self.rect.size = self.image.get_size()

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
    def __init__(self, path, layer, y_noscale, iscard):
        """起動画面のアニメーションに使用するスプライト。
        path: 表示するイメージのパス。
        y: Y座標。X位置は常に画面中央となる。
        """
        base.CWPySprite.__init__(self)
        self.layer = layer
        self.path = path
        self.y_noscale = y_noscale
        self.iscard = iscard
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

    def lclick_event(self):
        cw.cwpy.cut_animation = True

    def rclick_event(self):
        cw.cwpy.cut_animation = True

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

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

def main():
    pass

if __name__ == "__main__":
    main()
