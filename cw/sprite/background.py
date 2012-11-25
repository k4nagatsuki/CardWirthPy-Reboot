#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pygame
from pygame.locals import BLEND_MIN, BLEND_ADD

import cw
import base
import card


#-------------------------------------------------------------------------------
#　背景スプライト
#-------------------------------------------------------------------------------

class BackGround(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self.bgs = []
        self.image = pygame.Surface(cw.SIZE_AREA).convert()
        self.rect = self.image.get_rect()
        # spritegroupに追加
        cw.cwpy.bggrp.add(self)

    def load_surface(self, path, mask, size, flag):
        """背景サーフェスを作成。
        path: 背景画像ファイルのパス。
        mask: (0, 0)の色でマスクするか否か。透過画像を使う場合は無視。
        size: 背景のサイズ。
        flag: 背景に対応するフラグ。
        """
        # 対応フラグチェック
        if not cw.cwpy.sdata.flags.get(flag, True):
            return None

        # 画像読み込み
        ext = os.path.splitext(path)[1].lower()

        if ext == ".jptx":
            image = cw.effectbooster.JptxImage(path, mask).get_image()
        elif ext == ".jpdc":
            image = cw.effectbooster.JpdcImage(mask, path).get_image()
        elif ext == ".jpy1":
            image = cw.effectbooster.JpyImage(path).get_image()
        else:
            image = cw.util.load_image(path, mask)

        # 指定したサイズに拡大縮小する
        if not image.get_size() in (size, (0, 0)):
            if cw.cwpy.setting.smoothscale_bg:
                image = pygame.transform.smoothscale(image, size)
            else:
                image = pygame.transform.scale(image, size)

        return image

    def load(self, elements, bginhrt, ttype=("Default", "Default")):
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
            self.image = pygame.Surface(cw.SIZE_SCR).convert()
            self.bgs = []

        # 背景構築
        for e in elements:
            left = e.getint("Location", "left")
            top = e.getint("Location", "top")
            pos = (left, top)
            width = e.getint("Size", "width")
            height = e.getint("Size", "height")
            size = (width, height)
            mask = e.getbool("", "mask", False)
            flag = e.gettext("Flag", "")
            path = e.gettext("ImagePath", "")

            if cw.cwpy.is_playingscenario() and cw.cwpy.areaid > 0:
                path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
            else:
                path = cw.util.join_paths(cw.cwpy.skindir, path)

            if not os.path.isfile(path):
                fname = os.path.basename(path)
                fname = os.path.splitext(fname)[0] + cw.cwpy.rsrc.ext_img
                path = cw.util.join_paths(cw.cwpy.skindir, "Table", fname)

            image = self.load_surface(path, mask, size, flag)

            if image:
                self.image.blit(image, pos)
                self.bgs.append((path, mask, size, pos, flag, True))
            else:
                self.bgs.append((path, mask, size, pos, flag, False))
                oldbgs.append((path, mask, size, pos, flag, False))

        # エフェクトブースターの一時描画で使ったスプライトはすべて削除
        cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")

        # トランジション効果で画面入り
        if transitspr and not oldbgs == self.bgs:
            transitspr.add(cw.cwpy.bggrp)
            cw.animation.animate_sprite(transitspr, "transition")
            transitspr.remove(cw.cwpy.bggrp)

    def reload(self, ttype=("Default", "Default")):
        """背景画面を再構成する。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        # 背景処理する前に、トランジション用スプライト作成
        transitspr = cw.sprite.transition.get_transition(ttype)
        oldbgs = list(self.bgs)
        # 背景再構築
        self.image = pygame.Surface(cw.SIZE_SCR).convert()
        bgs = []

        for path, mask, size, pos, flag, visible in self.bgs:
            image = self.load_surface(path, mask, size, flag)

            if image:
                self.image.blit(image, pos)
                bgs.append((path, mask, size, pos, flag, True))
            else:
                bgs.append((path, mask, size, pos, flag, False))
                oldbgs.append((path, mask, size, pos, flag, False))

        self.bgs = bgs
        # エフェクトブースターの一時描画で使ったスプライトはすべて削除
        cw.cwpy.topgrp.remove_sprites_of_layer("jpytemporal")

        # トランジション効果で画面入り
        if transitspr and not oldbgs == self.bgs:
            transitspr.add(cw.cwpy.bggrp)
            cw.animation.animate_sprite(transitspr, "transition")
            transitspr.remove(cw.cwpy.bggrp)

class Curtain(base.SelectableSprite):
    def __init__(self, spritegrp, size=(632, 420), pos=(0, 0), alpha=128):
        """半透明のブルーバックスプライト。右クリックで解除。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        size: スプライトのサイズ。
        pos: 表示位置。
        alpha: 透明度。
        """
        # 半透明のブルーバック
        base.SelectableSprite.__init__(self)
        self.image = pygame.Surface(size).convert()
        self.image.fill((0, 0, 80))
        self.image.set_alpha(alpha)
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # spritegroupに追加
        spritegrp.add(self, layer="curtain")

    def rclick_event(self):
        cw.cwpy.sounds[u"システム・クリック"].play()

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
        self.set_pos(center=(316, 142))
        self.clear_image()
        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer="battlecard")

    def update_battlestart(self):
        cw.animation.animate_sprite(self, "deal", 1.5)
        self.zoomsize = (5, 8)
        cw.animation.animate_sprite(self, "zoomin", 1.5)
        cw.animation.animate_sprite(self, "hide", 1.5)
        cw.animation.animate_sprite(self, "deal", 1.5)
        self.zoomsize = (8, 12)
        cw.animation.animate_sprite(self, "zoomin", 1.5)
        cw.animation.animate_sprite(self, "hide", 1.5)
        cw.animation.animate_sprite(self, "deal", 1.5)
        self.zoomsize = (12, 16)
        cw.animation.animate_sprite(self, "zoomin", 1.5)
        cw.animation.animate_sprite(self, "hide", 1.5)
        cw.animation.animate_sprite(self, "deal", 1.5)
        self.zoomsize = (16, 21)
        cw.animation.animate_sprite(self, "zoomin", 1.5)
        pygame.time.wait(cw.cwpy.setting.frametime * 30)
        cw.animation.animate_sprite(self, "hide")

    def update_image(self):
        pass

    def update_selection(self):
        pass

class InuseCardImage(card.CWPyCard):
    def __init__(self, user, header, status="normal", center=False):
        """使用中のカード画像スプライト。
        user: Character。
        header: 使用するカードのCardHeader。
        status: すぐ表示したくない場合は"hidden"を指定。
        center: 画面中央に表示するかどうか。
        """
        card.CWPyCard.__init__(self, status)
        self.zoomsize = (32, 42)
        image = header.get_cardimg()
        self.image = self._image = image
        self.rect = self._rect = image.get_rect()

        if not user.scale == 100 and not center:
            scale = user.scale / 100.0
            self.image = pygame.transform.rotozoom(self.image, 0, scale)
            self.rect.size = self.image.get_size()

        if center:
            self.set_pos(center=(316, 142))
        else:
            self.set_pos(center=user.rect.center)

        if status == "hidden":
            self.clear_image()

        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self, layer="inusecard")

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
        self.rect.topleft = (target.rect.right - 30, target.rect.bottom - 30)
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

def main():
    pass

if __name__ == "__main__":
    main()
