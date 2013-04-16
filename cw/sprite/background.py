#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import pygame
from pygame.locals import BLEND_MIN, BLEND_ADD, BLEND_RGBA_ADD, BLEND_RGBA_SUB, BLEND_RGBA_MULT

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
            image = cw.s(cw.util.load_image(path, mask))

        # 指定したサイズに拡大縮小する
        if not image.get_size() in (size, cw.s((0, 0))):
            if cw.cwpy.setting.smoothscale_bg:
                image = pygame.transform.smoothscale(image, size)
            else:
                image = pygame.transform.scale(image, size)

        return image, anime

    def load(self, elements, bginhrt, doanime=True, ttype=("Default", "Default")):
        """背景画面を構成する。
        elements: BgImageElementのリスト。
        bginhrt: Trueなら背景継承。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
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
            bgs.append((type, d))
        else:
            bgs.append((type, d))
            oldbgs.append((type, d))

    def _add_colorcell(self, blitlist, bgs, oldbgs, d):
        blend, color1, gradient, color2, size, pos, flag, visible = d
        visible = cw.cwpy.sdata.flags.get(flag, True)
        d = blend, color1, gradient, color2, size, pos, flag, visible
        if visible:
            image = cw.image.create_colorcell(size, color1, gradient, color2)
            if blend == "Add":
                blendflag = BLEND_RGBA_ADD
            elif blend == "Subtract":
                blendflag = BLEND_RGBA_SUB
            elif blend == "Multiply":
                blendflag = BLEND_RGBA_MULT
            else:
                blendflag = 0
            blitlist.append((BG_IMAGE, (image, pos, blendflag)))
            bgs.append((type, d))
        else:
            bgs.append((type, d))
            oldbgs.append((type, d))

    def _load_after(self, bginhrt, blitlist, animated, transitspr, oldbgs):
        # 背景を更新する(呼び出し時点でエフェクトブースターは実行済み)
        if not bginhrt:
            self.image = pygame.Surface(cw.s(cw.SIZE_SCR)).convert()

        for type, d in blitlist:
            if type == BG_IMAGE:
                # 背景画像、カラーセル、縁取り形式2のテキストセル
                image, pos, flag = d
                self.image.blit(image, cw.s(pos), None, flag)

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
    def __init__(self, spritegrp, size=None, pos=None, alpha=128):
        """半透明のブルーバックスプライト。右クリックで解除。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        size: スプライトのサイズ。
        pos: 表示位置。
        alpha: 透明度。
        """
        if size is None:
            size = cw.s((632, 420))
        if pos is None:
            pos = cw.s((0, 0))
        base.SelectableSprite.__init__(self)
        self.image = pygame.Surface(size).convert()
        self.image.fill((0, 0, 80))
        self.image.set_alpha(alpha)
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # spritegroupに追加
        spritegrp.add(self, layer="curtain")

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
        cardimg = cw.image.CardImage(path, "ACTION", u"")
        image = cardimg.get_image()
        self.image = self._image = self.image_unzoomed = image
        self.rect = self._rect = self.image.get_rect()
        self.set_pos(center=cw.s((316, 142)))
        self.clear_image()
        self.highspeed = True
        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer="battlecard")

    def update_battlestart(self):
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize = cw.s((8, 12))
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize = cw.s((28, 40))
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize = cw.s((56, 80))
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
        self.zoomsize = cw.s((32, 42))
        image = header.get_cardimg()
        self.image = self._image = image
        self.rect = self._rect = image.get_rect()

        if not user.scale == 100 and not center:
            scale = user.scale / 100.0
            self.image = pygame.transform.rotozoom(self.image, 0, scale)
            self.rect.size = self.image.get_size()

        if center:
            self.set_pos(center=cw.s((316, 142)))
        else:
            self.set_pos(center=user.rect.center)

        if status == "hidden":
            self.clear_image()

        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer=layer)

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
        self.image = cw.cwpy.rsrc.statuses["TARGET"]
        self.rect = self.image.get_rect()
        self.rect.topleft = (target.rect.right - cw.s(30), target.rect.bottom - cw.s(30))
        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer="targetarrow")

class Jpy1TemporalSprite(base.CWPySprite):
    def __init__(self, image, pos, paintmode):
        """エフェクトブースターJpy1の一時描画用スプライト。
        Jpy1の読み込みがすべて終了したら、削除される。
        """
        base.CWPySprite.__init__(self)
        # image, rect作成。
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = pos

        # ブレンドモード設定
        if paintmode == 1:
            self.blendmode = BLEND_MIN
        elif paintmode == 2:
            self.blendmode = BLEND_ADD

        # spritegroupに追加
        cw.cwpy.topgrp.add(self, layer="jpytemporal")

class TitleCell(base.CWPySprite):
    def __init__(self, path, layer, y, iscard):
        """起動画面のアニメーションに使用するスプライト。
        path: 表示するイメージのパス。
        y: Y座標。X位置は常に画面中央となる。
        """
        base.CWPySprite.__init__(self)
        self.layer = layer
        if path == "white":
            self._image = pygame.surface.Surface(cw.s(cw.SIZE_AREA)).convert()
            self._image.fill((255, 255, 255))
        else:
            self._image = cw.s(cw.util.load_image(path, True))
        self._rect = self._image.get_rect()
        x = (cw.s(cw.SIZE_AREA[0]) - self._rect.width) / 2
        self._rect.topleft = (x, y)

        if iscard:
            self.clear_image()
        else:
            self.image = self._image
            self.image.set_alpha(0)
            self.rect = self._rect

        self.status = "hidden"
        self.frame = 0

        self.animespeed = cw.cwpy.setting.fps / 3
        self.dealing_scales = [
            int(math.cos(math.radians(90.0 * i / self.animespeed)) * 100)
            for i in xrange(self.animespeed + 1)
                if i
        ]

        n = 255 / self.animespeed
        self.fade_params = [255 - n * i for i in xrange(self.animespeed + 1) if i]

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
            self.image.set_alpha(255)
            self.frame = 0
            return

        alpha = self.fade_params[::-1][self.frame]
        self.image.set_alpha(alpha)
        self.frame += 1

    def update_fadein2(self):
        """
        倍速でフェードインする。
        """
        if self.frame >= self.animespeed:
            self.status = "normal"
            self.image.set_alpha(255)
            self.frame = 0
            return

        alpha = self.fade_params[::-1][self.frame]
        self.image.set_alpha(alpha)
        self.frame += 2

    def update_fadeout(self):
        """
        フェードアウトのアニメーションを呼び出すメソッド。
        """
        if self.frame == self.animespeed:
            self.status = "hidden"
            self.image.set_alpha(0)
            self.frame = 0
            return

        alpha = self.fade_params[self.frame]
        self.image.set_alpha(alpha)
        self.frame += 1

    def update_show(self):
        """
        ウェイト無しで表示する。
        """
        self.status = "normal"
        self.image.set_alpha(255)

    def update_vanish(self):
        """
        ウェイト無しで消去する。
        """
        self.status = "hidden"
        self.image.set_alpha(0)

    def clear_image(self):
        self.image = pygame.Surface((0, 0)).convert()
        self.rect = self.image.get_rect(center=self._rect.center)

def main():
    pass

if __name__ == "__main__":
    main()
