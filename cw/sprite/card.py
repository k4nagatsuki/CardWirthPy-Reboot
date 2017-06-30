#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import pygame

import cw
import base
from .. import character


class CWPyCard(base.SelectableSprite):
    def __init__(self, status, flag=None):
        base.SelectableSprite.__init__(self)
        self.alpha = None
        # 状態
        self.status = status
        self.debug_only = False
        self.old_status = status
        self.rect = cw.s(pygame.Rect(0, 0, 0, 0))
        self._pos_noscale = None
        self._center_noscale = None
        # 前に表示中のカード
        self.inusecardimg = None
        # アニメ用フレーム数
        self.frame = 0
        # ズーム画像のリスト。(Surfaice, Rect)のタプル。
        self.zoomimgs = []
        self.zoomsize_noscale = (0, 0)
        # 裏返し状態か否か
        self.reversed = False
        # カード使用のターゲットか否か
        self.cardtarget = False
        # 対応フラグ名
        self.flag = flag
        # スケール
        self.scale = 100
        # 逃走の有無
        self.escape = False
        # Trueなら高速でアニメーションする
        self.highspeed = False
        # Trueなら戦闘時のアニメーション速度設定を使用する
        self.battlespeed = False
        # Trueの間はカード消去で使用中カードをクリアしない
        self.hide_inusecardimg = True

        # MenuCardの特殊コマンド
        self.command = ""
        self.arg = ""
        # フラグ
        self.flag = ""

    def is_flagtrue(self):
        mcardflag = bool(cw.cwpy.sdata.flags.get(self.flag, True))
        mcardflag &= bool(not self.debug_only or cw.cwpy.is_debugmode())
        if mcardflag and self.command == "ShowDialog" and self.arg == "INFOVIEW":
            mcardflag &= bool(cw.cwpy.is_playingscenario() and cw.cwpy.sdata.has_infocards())
        return mcardflag

    @staticmethod
    def is_flagtrue_static(data):
        flag = data.gettext("Property/Flag", "")
        mcardflag = bool(cw.cwpy.sdata.flags.get(flag, True))
        if mcardflag:
            debug_only = data.getbool(".", "debugOnly", False)
            mcardflag &= bool(not debug_only or cw.cwpy.is_debugmode())
        if mcardflag:
            command = data.getattr(".", "command", "")
            if command == "ShowDialog" and data.getattr(".", "arg", "") == "INFOVIEW":
                mcardflag &= bool(cw.cwpy.is_playingscenario() and cw.cwpy.sdata.has_infocards())
        return mcardflag

    def get_unselectedimage(self):
        if self.status == "click":
            return self.image
        else:
            return self.get_animeimage()

    def get_selectedimage(self):
        return cw.imageretouch.to_negative_for_card(self.get_animeimage())

    def set_alpha(self, alpha):
        self.alpha = alpha
        for img in self.zoomimgs:
            img.set_alpha(alpha)
        self.image.set_alpha(alpha)
        self._image.set_alpha(alpha)

    def get_animeimage(self):
        if self.zoomimgs:
            return self.zoomimgs[-1][0]
        else:
            return self._image

    def get_animerect(self):
        if self.zoomimgs:
            return self.zoomimgs[-1][1]
        else:
            return self._rect

    def get_baserect(self):
        return self._rect

    def _get_dealingscales(self):
        if self.battlespeed and cw.cwpy.setting.use_battlespeed:
            return cw.cwpy.setting.dealing_scales_battle
        else:
            return cw.cwpy.setting.dealing_scales

    def _get_dealspeed(self):
        return cw.cwpy.setting.get_dealspeed(self.battlespeed and cw.cwpy.setting.use_battlespeed)

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        self.update_selection()

    def update_delete(self):
        pass

    def update_reversed(self):
        # デバッグモード時は反転中でも選択可能
        # ただしカード使用の選択対象にはならない
        if cw.cwpy.is_debugmode() and not cw.cwpy.selectedheader:
            self.update_selection()

    def update_hidden(self):
        pass

    def update_reverse(self):
        """
        カードをひっくり返す。
        """
        if self.old_status == "hidden":
            self.reversed = not self.reversed
            self._reverse()
            self.status = "hidden"
            return

        self.hide_inusecardimg = False
        self.update_hide()
        self.hide_inusecardimg = True

        if self.status == "hidden":
            cw.cwpy.draw()
            cw.cwpy.tick_clock()
            self.reversed = not self.reversed

            self._reverse()

            cw.animation.animate_sprite(self, "deal")

            if self.reversed:
                self.status = "reversed"

    def reverse(self):
        """
        アニメーション無しでカードをひっくり返す。
        """
        self.reversed = not self.reversed
        self._reverse()

    def _reverse(self):
        # 表←→裏の画像切り替え
        if self.reversed:
            image = cw.cwpy.rsrc.cardbgs["REVERSE"]

            if not self.scale == 100:
                scale = self.scale / 100.0
                image = cw.image.zoomcard(image, scale)
            else:
                image = image.copy()

            image.set_alpha(self.alpha)
            self._image = image

            for i, t in enumerate(self.zoomimgs):
                img, rect = t
                # 最大の一枚のみは長時間表示される
                # 可能性があるためスムージングする
                if i + 1 == len(self.zoomimgs) and cw.cwpy.setting.smoothing_card_up:
                    scale = cw.image.smoothscale_card
                else:
                    scale = pygame.transform.scale
                img = scale(image, rect.size)
                self.zoomimgs[i] = (img, rect)

        else:
            self.update_image()

    def update_click(self):
        """
        クリック時のアニメーションを呼び出すメソッド。
        """
        if self.frame == 0:
            if self.reversed:
                self.image = self.cardimg.get_clickedimg(self.get_animerect(), image=self.image).copy()
            else:
                self.image = self.cardimg.get_clickedimg(self.get_animerect()).copy()
            self.image.set_alpha(self.alpha)
            self.rect = self.image.get_rect(center=self.get_animerect().center)
            self.status = "click"
        elif self.frame == 3:
            self.status = self.old_status
            self.image = self.get_selectedimage()
            self.rect = pygame.Rect(self.get_animerect())
            self.frame = 0
            return

        self.frame += 1

    def update_deal(self):
        """
        カード表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(self._get_dealingscales()):
            self.deal()
            self.frame = 0
            return

        if self.frame == 0 and hasattr(self, "cardimg") and self.cardimg.is_modifiedfile():
            self.update_image()

        n = self._get_dealingscales()[::-1][self.frame]
        rect = self.get_animerect()
        size = rect.w * n / 100, rect.h
        self.image = pygame.transform.scale(self.get_animeimage(), size)

        # 反転表示中
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)

        self.rect = self.image.get_rect(center=rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def deal(self):
        """カードをアニメーション無しで表示する。"""
        if self.reversed:
            self.status = "reversed"
        else:
            self.status = "normal"
        if hasattr(self, "cardimg") and (self.cardimg.is_modifiedfile() or\
                                         self.image.get_width() <= 0):
            self.update_image()
        self.image = self.get_animeimage()
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)
        self.rect = pygame.Rect(self.get_animerect())

    def update_hide(self):
        """
        カード非表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(self._get_dealingscales()):
            self.hide()
            self.frame = 0
            return

        n = self._get_dealingscales()[self.frame]
        rect = self.get_animerect()
        size = rect.w * n / 100, rect.h
        self.image = pygame.transform.scale(self.get_animeimage(), size)

        # 反転表示中
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)

        self.rect = self.image.get_rect(center=rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def hide(self):
        """カードをアニメーション無しで非表示にする。"""
        self.status = "hidden"
        self.clear_image()
        if self.hide_inusecardimg:
            cw.cwpy.clear_inusecardimg(self)

    def update_lateralvibe(self):
        """
        横振動させる。
        """
        n = (self._get_dealspeed()+1) * 3
        if self.frame >= n:
            self.rect = pygame.Rect(self.get_animerect())
            self.status = self.old_status
            self.frame = 0
            return

        # 横位置を変動させる
        # 右へ移動→戻る→左へ移動→戻る
        # のパターンを最大6回繰り返す
        if n < 14:
            count = 2
        else:
            count = 6
        mx = 2 # 最大移動量
        nb = n / (count*4.0)
        f = max(0, int(round(self.frame / nb)) - 1)
        nx = (self.frame - nb*f) / nb * mx

        f %= 4
        if f <= 0:
            val = 0 + nx
        elif f <= 1:
            val = mx - nx
        elif f <= 2:
            val = 0 - nx
        elif f <= 3:
            val = -mx + nx

        val = int(round(val))

        self.rect = pygame.Rect(self.get_animerect())
        self.rect.move_ip(cw.s(val), cw.s(0))
        self.frame += 1

    def update_axialvibe(self):
        """
        縦振動させる。
        実際には横幅の周期的変動によって表現される。
        """
        n = (self._get_dealspeed()+1) * 3
        if self.frame >= n:
            self.rect = pygame.Rect(self.get_animerect())
            if self.image.get_size() <> self.rect.size:
                self.image = pygame.transform.scale(self.get_animeimage(), self.rect.size)
            self.status = self.old_status
            self.frame = 0
            return

        # 横幅を変動させる
        # 縮小→戻る
        # のパターンを最大4回繰り返す
        if n < 12:
            count = 2
        else:
            count = 4
        nb = n / (count*2.0)
        mx = self._rect.width / 20 # 最大縮小量
        f = max(0, int(round(self.frame / nb)) - 1)
        nx = (self.frame - nb*f) / nb * mx
        f %= 2
        if f <= 0:
            val = 0 - nx
        else:
            val = -mx + nx

        val = int(round(val))
        if val % 2 == 1:
            # 左右均等に拡縮するため、常に偶数にする
            if val < 0:
                val -= 1
            else:
                val += 1

        self.rect = self.get_animerect().inflate(cw.s(val), cw.s(0))
        self.frame += 1
        self.image = pygame.transform.scale(self.get_animeimage(), self.rect.size)

    def update_zoomin(self):
        """
        カードを拡大する。
        """
        self._update_zoominout(self._get_dealspeed()+1, True)

    def update_zoomin_slow(self):
        """
        カードをゆっくりと拡大する。
        """
        self._update_zoominout(self._get_dealspeed()*2+1, True)

    def update_zoomout(self):
        """
        カードを縮小する。
        """
        self._update_zoominout(self._get_dealspeed()+1, False)

    def update_zoomout_slow(self):
        """
        カードをゆっくりと縮小する。
        """
        self._update_zoominout(self._get_dealspeed()*2+1, False)

    def _update_zoominout(self, ds, inout):
        if self.frame == 0:
            if inout:
                self.zoomimgs.append((self.get_animeimage(), pygame.Rect(self.get_animerect())))

        if inout:
            # 拡大
            zoom_w, zoom_h = cw.s(self.zoomsize_noscale)
        else:
            # 縮小
            zoom_w, zoom_h = self.zoomimgs[-1][1].size
            zoom_w -= self.zoomimgs[0][1].width
            zoom_h -= self.zoomimgs[0][1].height
        maxw = self._rect.w + zoom_w
        maxh = self._rect.h + zoom_h

        if self.old_status == "hidden" or ds <= 1:
            if inout:
                w = maxw
                h = maxh
            else:
                w = self._rect.w
                h = self._rect.h
            self.frame = ds
        else:
            def calc_zoom(zoom_val):
                if inout:
                    # 拡大
                    f = self.frame
                else:
                    # 縮小
                    f = ds - self.frame - 1
                # 線形に拡大するのではなく、末端で減速する
                return int(round(zoom_val * ((ds * 2 - f + 1) * f / 2.0) / ((ds + 1) * ds / 2.0)))

            value = calc_zoom(zoom_w)
            if value % 2 == 1:
                value += 1 if ds//2 <= self.frame else -1
            w = cw.util.numwrap(self._rect.w + value, 0, maxw)

            value = calc_zoom(zoom_h)
            if value % 2 == 1:
                value += 1 if ds//2 <= self.frame else -1
            h = cw.util.numwrap(self._rect.h + value, 0, maxh)

            self.frame += 1

        if ds <= self.frame and cw.cwpy.setting.smoothing_card_up:
            # 最大の一枚のみは長時間表示される
            # 可能性があるためスムージングする
            scale = cw.image.smoothscale_card
        else:
            scale = pygame.transform.scale
        self.image = scale(self.zoomimgs[0][0], (w, h))
        self.rect = pygame.Rect(self.image.get_rect())
        self.rect.center = self.get_animerect().center

        if ds <= self.frame:
            if inout:
                self.zoomimgs.append((self.image, pygame.Rect(self.rect)))
            else:
                del self.zoomimgs[:]
            self.status = self.old_status
            self.frame = 0
            if self.status == "hidden":
                self.clear_image(move=False)

    def update_shiftup(self):
        """下にさげていたカードを上にあげる。"""
        speed = (self._get_dealspeed()+1) * 3
        if self.frame == 0:
            self.image = self.get_animeimage()

        shift = int(float(cw.s(150)) / speed * self.frame)
        y = self._rect[1] + cw.s(150) - shift
        if self.zoomimgs:
            y += self.zoomimgs[-1][1][1] - self.zoomimgs[0][1][1]
        self.rect = pygame.Rect(self.rect)
        self.rect.topleft = (self.rect[0], y)
        self.rect.size = self.image.get_size()

        for _image, rect in self.zoomimgs:
            if not rect is self.rect:
                rect.center = self.rect.center

        if self.frame >= speed:
            if self.reversed:
                self.status = "reversed"
            else:
                self.status = "normal"

            self.rect.topleft = self.get_animerect().topleft
            self.frame = 0

        else:
            self.frame += 1

    def update_shiftdown(self):
        """上にあげていたカードを下にさげる。"""
        speed = (self._get_dealspeed()+1) * 3

        shift = int(float(cw.s(150)) / speed * self.frame)
        y = self._rect[1] + shift
        self.rect = pygame.Rect(self.rect)
        self.rect.size = self.image.get_size()
        if self.zoomimgs:
            _image, zrect = self.zoomimgs[0]
            topleft = (zrect[0], y)
            zrect.topleft = topleft
            for _image, rect in self.zoomimgs[1:]:
                rect.center = zrect.center
            self.rect.center = zrect.center
        else:
            topleft = (self.rect[0], y)
            self.rect.topleft = topleft

        if self.frame >= speed:
            self.image = pygame.Surface((0, 0)).convert()
            self.status = "hidden"
            self.frame = 0

        else:
            self.frame += 1

    def update_scale(self):
        if not self.is_initialized():
            return
        if not (hasattr(self, "cardimg") and self.cardimg):
            return

        zoom = 0 < len(self.zoomimgs)

        if zoom and not self.status in ("zoomin", "zoomout"):
            if self.status <> "zoomout":
                self.old_status = self.status
                self.status = "zoomout"
            while self.status == "zoomout":
                self.update_zoomout()

        self.cardimg.update_scale()
        self.update_image()
        if self._pos_noscale or self._center_noscale:
            self.set_pos_noscale(self._pos_noscale, self._center_noscale)

        if zoom and not self.status in ("zoomin", "zoomout"):
            if self.status <> "zoomin":
                self.old_status = self.status
                self.status = "zoomin"
            while self.status == "zoomin":
                self.update_zoomin()

        if self.status == "hidden":
            self.clear_image(True)

    def update_image(self, update_statusimg=False, is_runningevent=None):
        """
        画像を再構成する。
        """
        if not self.cardimg:
            return None

        # 画像参照
        if update_statusimg:
            clip = self.cardimg.update_statusimg(self, is_runningevent=is_runningevent)
            if not clip:
                return None
        else:
            if hasattr(self, "test_aptitude"):
                self.cardimg.update(self, self.test_aptitude)
            else:
                self.cardimg.update(self)
            clip = pygame.Rect(self.rect)

        image = self.cardimg.get_image().copy()
        image.set_alpha(self.alpha)
        rect = self.cardimg.rect

        if not self.scale == 100:
            scale = self.scale / 100.0
            image = cw.image.zoomcard(image, scale)
            rect.size = image.get_size()

        if self.cardtarget:
            image = cw.imageretouch.to_negative_for_card(image)

        if hasattr(self, "image") and self.rect.size == (0, 0):
            self._image = image
        else:
            self._image = image
            if not self.reversed:
                self.image = self._image

        self.rect.size = rect.size
        self._rect = pygame.Rect(self.rect)
        self._rect.topleft = rect.topleft

        # ズーム画像も更新
        if self.zoomimgs:
            self.zoomimgs[0] = self._image, self.zoomimgs[0][1]
            for i, t in enumerate(self.zoomimgs[1:]):
                rect = t[1]
                w = rect[2]
                h = rect[3]
                # 最大の一枚のみは長時間表示される
                # 可能性があるためスムージングする
                if i + 1 == len(self.zoomimgs)-1 and cw.cwpy.setting.smoothing_card_up:
                    scale = cw.image.smoothscale_card
                else:
                    scale = pygame.transform.scale
                image = scale(self._image, (w, h))
                self.zoomimgs[i+1] = image, rect
            self.image = self.zoomimgs[-1][0]
            self.rect = pygame.Rect(self.zoomimgs[-1][1])

        # リバース状態
        if self.reversed:
            self._reverse()
            if not self.zoomimgs:
                self.image = self._image

        if self.status == "hidden":
            self.clear_image(False)

        if self in cw.cwpy.file_updates:
            cw.cwpy.file_updates.remove(self)

        return clip

    def clear_image(self, move=True):
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        if move:
            topleft = self.rect.topleft
            self.rect = self.image.get_rect()
            self.rect.topleft = topleft

        if self in cw.cwpy.file_updates:
            cw.cwpy.file_updates.remove(self)

    def set_pos_noscale(self, pos_noscale=None, center_noscale=None):
        """画面の拡大率を考慮せずに座標を設定する。"""
        if pos_noscale:
            self._pos_noscale = pos_noscale
        elif center_noscale:
            self._center_noscale = center_noscale
        pos = cw.s(pos_noscale) if pos_noscale else None
        center = cw.s(center_noscale) if center_noscale else None
        self.set_pos(pos, center)

    def set_pos(self, pos=None, center=None):
        """画面の拡大率を反映済みの座標を設定する。"""
        if pos:
            self._rect.topleft = pos
        elif center:
            self._rect.center = center

        self.rect.center = self._rect.center
        if self.zoomimgs:
            for image, zrect in self.zoomimgs:
                zrect.center = self._rect.center

        if hasattr(self, "cardimg"):
            self.cardimg.rect.topleft = self._rect.topleft

    def get_pos_noscale(self):
        return self._pos_noscale

    def set_cardtarget(self):
        if not self.cardtarget:
            self.cardtarget = True
            self.update_image()

    def clear_cardtarget(self):
        if self.cardtarget:
            self.cardtarget = False
            self.update_image()

#-------------------------------------------------------------------------------
#　プレイヤーカードスプライト
#-------------------------------------------------------------------------------

class PlayerCard(CWPyCard, character.Player):
    def __init__(self, data, pos_noscale=(0, 0), status="hidden", index=0):
        CWPyCard.__init__(self, status)
        self.zoomsize_noscale = (16, 22)
        # CWPyElementTreeインスタンス
        self.data = data
        # CharacterCard初期化
        character.Player.__init__(self)
        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.join_paths(cw.cwpy.yadodir, path), base=info))

        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        self.cardimg = cw.image.CharacterCardImage(self, pos_noscale=pos_noscale, can_loaded_scaledimage=can_loaded_scaledimage)
        self.update_image()
        # 空のイメージ
        self.image = pygame.Surface(cw.s((0, 0))).convert()

        self.set_pos_noscale(pos_noscale)

        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(cw.s(0), cw.s(+150))

        # スキンの種族設定とキャラクター編集ダイアログでの
        # 編集の噛み合わせで"＠ＥＰ"が消えてしまうバグがあったので
        # ここで修復する(issue #416)
        if not self.has_coupon(u"＠ＥＰ"):
            self.set_coupon(u"＠ＥＰ", 0)

        # "：Ｒ"クーポンを所持していたら反転フラグON
        if self.has_coupon(u"：Ｒ"):
            self.reversed = True
            self._reverse()

        # spritegroupに追加
        self.index = index
        if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
            self.layer = (cw.LAYER_PCARDS+cw.LAYER_SP_LAYER, cw.LTYPE_PCARDS, self.index, 0)
        else:
            self.layer = (cw.LAYER_PCARDS, cw.LTYPE_PCARDS, self.index, 0)
        cw.cwpy.cardgrp.add(self, layer=self.layer)
        cw.cwpy.pcards.insert(index, self)

    def set_pos(self, pos=None, center=None):
        CWPyCard.set_pos(self, pos, center)
        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(cw.s(0), cw.s(+150))

    def set_name(self, name):
        character.Player.set_name(self, name)
        self.cardimg.set_nameimg(self.get_name())

    def set_images(self, paths):
        paths = character.Player.set_images(self, paths)
        self.imgpaths = []
        for info in paths:
            self.imgpaths.append(cw.image.ImageInfo(cw.util.join_paths(cw.cwpy.yadodir, info.path), base=info))
        self.cardimg.set_faceimgs(self.imgpaths, can_loaded_scaledimage=True)

        def func():
            def func():
                num = cw.cwpy.get_pcards().index(self)+1
                cw.cwpy.update_pcimage(num, deal=True)
            cw.cwpy.exec_func(func)
        cw.cwpy.exec_func(func)

    def update_levelup(self):
        """レベルアップ処理。"""
        if self.frame % 5:
            self.image = pygame.Surface((0, 0)).convert()
        elif not self.frame % 5:
            self.image = self.get_animeimage()

            if self.frame == 15:
                self.status = self.old_status
                self.cardimg.set_levelimg(self.level)
                self.frame = 0
                return

        self.frame += 1

    def update_delete(self):
        """パーティから外す。"""
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.ydata.party.remove(self)

    def update_vanish(self):
        """仮の対象消去。clear_vanish()で復元する事ができる。"""
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.pcards.remove(self)

    def lclick_event(self):
        """左クリックイベント。"""
        if self.reversed:
            self.rclick_event()

        # CARDPOCKETダイアログを開く(通常)
        elif not cw.cwpy.is_curtained():
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")

            if cw.cwpy.is_battlestatus():
                if self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                elif self.is_autoselectedpenalty() and not cw.cwpy.debug:
                    s = cw.cwpy.msgs["selected_penalty"]
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("HANDVIEW")
            else:
                if self.is_inactive() and not cw.cwpy.areaid in cw.AREAS_TRADE:
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("CARDPOCKET")

        # カード移動操作
        elif cw.cwpy.areaid in (-1, -2, -5) and cw.cwpy.selectedheader:
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.trade("PLAYERCARD", self)

        # カード使用。USECARDダイアログを開く
        elif cw.cwpy.selectedheader:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")

            # USECARDダイアログを開く
            if cw.cwpy.status == "Scenario":
                cw.cwpy.call_modaldlg("USECARD")
            # 戦闘行動を設定する。
            elif cw.cwpy.status == "ScenarioBattle":
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea(redraw=False)

        # パーティ離脱
        elif cw.cwpy.areaid == -3:
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.dissolve_party(self)

        # キャンプ
        elif cw.cwpy.areaid == cw.AREA_CAMP:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")
        cw.cwpy.call_modaldlg("CHARAINFO")

    def set_level(self, value, regulate=False, debugedit=False, backpack_party=None, revert_cardpocket=True):
        character.Player.set_level(self, value, regulate, debugedit, backpack_party, revert_cardpocket)
        self.cardimg.set_levelimg(self.level)

    def adjust_level(self, fromscenario):
        """経験点を確認し、条件を満たしていれば
        レベルアップ・ダウン処理を行う。
        fromscenarioがTrueであれば同時に完全回復も行う。
        状態が変化すればTrueを返す。
        """
        result = False
        if fromscenario and cw.cwpy.is_debugmode() and\
                cw.cwpy.setting.no_levelup_in_debugmode:
            levelup = 0
        else:
            levelup = self.check_level()
            if fromscenario:
                # シナリオクリア時にはレベルダウンしない
                levelup = max(0, levelup)

        level = self.level # 再調節に使用

        # レベルアップ
        if levelup <> 0:
            base = self.get_specialcoupons()[u"＠レベル原点"]
            n = base + levelup
            if fromscenario:
                if 1 < levelup:
                    # 複数回レベルアップした場合はその分回転表示する
                    cw.animation.animate_sprite(self, "levelup")
                    for i in xrange(levelup - 1):
                        cw.animation.animate_sprite(self, "hide")
                        self.set_level(base + i + 1, revert_cardpocket=False)
                        cw.animation.animate_sprite(self, "deal")
                    self.set_level(n, revert_cardpocket=False)
                else:
                    self.set_level(n, revert_cardpocket=False)
                    cw.animation.animate_sprite(self, "levelup")
            else:
                self.set_level(n, revert_cardpocket=False)

        # 回復処理
        if fromscenario or levelup <> 0:
            result = True
            cw.cwpy.play_sound("harvest", True)
            cw.animation.animate_sprite(self, "hide")
            if fromscenario:
                self.set_fullrecovery()
            self.update_image()
            cw.animation.animate_sprite(self, "deal")

        # レベルアップメッセージ
        if fromscenario and 0 < levelup:
            text = cw.cwpy.msgs["level_up"]
            names = [(0, cw.cwpy.msgs["ok"])]
            infos = []
            can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
            for info in self.imgpaths:
                infos.append((cw.image.ImageInfo(path=info.path, pcnumber=info.pcnumber, base=info, basecardtype="LargeCard"),
                              can_loaded_scaledimage, self, {}))
            mwin = cw.sprite.message.MessageWindow(text, names, infos, self,
                                                   versionhint=self.versionhint,
                                                   centering_x=False, centering_y=True, boundarycheck=True)
            cw.cwpy.show_message(mwin)
            if base <> level or cw.cwpy.ydata.party.is_suspendlevelup:
                # レベル調節中だった場合は再調節
                # レベルアップ停止中であれば元のレベルへ調節
                cw.animation.animate_sprite(self, "hide")
                self.set_level(level, regulate=True)
                self.update_image()
                cw.animation.animate_sprite(self, "deal")

        return result

    def lost(self):
        cw.character.Player.lost(self)
        for pocket in self.cardpocket:
            for card in pocket[:]:
                cw.cwpy.trade("TRASHBOX", header=card, from_event=True, sort=False)

#-------------------------------------------------------------------------------
#　エネミーカードスプライト
#-------------------------------------------------------------------------------

class EnemyCard(CWPyCard, character.Enemy):
    def __init__(self, mcarddata, pos_noscale=(0, 0), status="hidden", addgroup=True, index=0):
        CWPyCard.__init__(self, status)
        self.zoomsize_noscale = (16, 22)
        self.index = index
        self.mcarddata = mcarddata
        self._init_pos_noscale = pos_noscale
        # フラグ
        self.flag = mcarddata.gettext("Property/Flag", "")
        # 逃走の有無
        self.escape = mcarddata.getbool(".", "escape", False)

        # スケール
        if cw.cwpy.is_autospread():
            self.scale = 100
        else:
            s = mcarddata.getattr("Property/Size", "scale", "100%")
            self.scale = int(s.rstrip("%"))

        self._init = False

        # 表示するまでデータを作らない
        if status == "hidden":
            self._rect = cw.s(pygame.Rect(0, 0, 0, 0))
            self.clear_image()
        else:
            if not self.initialize():
                raise

        layer = mcarddata.getint("Property/Layer", -1)
        if layer < 0:
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and (cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_SCENARIO)) or\
                                  cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA))):
                layer = cw.LAYER_MCARDS_120
            else:
                layer = cw.LAYER_MCARDS

        if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
            self.layer = (layer+cw.LAYER_SP_LAYER, cw.LTYPE_MCARDS, self.index, 0)
        else:
            self.layer = (layer, cw.LTYPE_MCARDS, self.index, 0)

        if addgroup:
            # spritegroupに追加
            cw.cwpy.cardgrp.add(self, layer=self.layer)
            cw.cwpy.mcards.append(self)

    def initialize(self):
        if self._init:
            return True

        self._init = True

        # イベントデータ
        self.events = cw.event.EventEngine(self.mcarddata.getfind("Events"))
        # CWPyElementTreeインスタンス
        e = cw.cwpy.sdata.get_castdata(self.mcarddata.getint("Property/Id"), nocache=True)
        if e is None:
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.mcards.remove(self)
            return False
        self.data = cw.data.xml2etree(element=e)
        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Enemy.__init__(self)
        self.deck.set(self, draw=False)
        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.get_materialpath(path, cw.M_IMG), base=info))
        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        self.cardimg = cw.image.CharacterCardImage(self, pos_noscale=self._init_pos_noscale,
                                                   can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=True)
        self.set_pos_noscale(pos_noscale=self._init_pos_noscale)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()
        return True

    def is_initialized(self):
        return self._init

    def update(self, scr):
        if self.status <> "hidden" and not self._init:
            if not self.initialize():
                return
        CWPyCard.update(self, scr)

    def update_delete(self):
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.mcards.remove(self)
            if self in cw.cwpy.file_updates:
                cw.cwpy.file_updates.remove(self)

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        # CARDPOCKETダイアログを開く(通常)
        if (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if cw.cwpy.is_battlestatus():
                if self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("HANDVIEW")

        # カード使用。戦闘行動を設定する。
        elif cw.cwpy.selectedheader:
            if cw.cwpy.is_battlestatus():
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea(redraw=False)

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　フレンドカードスプライト
#-------------------------------------------------------------------------------

class FriendCard(CWPyCard, character.Friend):
    def __init__(self, data=None, index=0):
        CWPyCard.__init__(self, "hidden")
        self.zoomsize_noscale = (32, 42)
        self.index = index
        self.layer = (cw.LAYER_FCARDS, cw.LTYPE_FCARDS, self.index, 0)

        if isinstance(data, cw.data.CWPyElement):
            data = cw.data.xml2etree(element=data)
        self.data = data
        self.id = self.data.getint("Property/Id", 1)

        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Friend.__init__(self)
        self.deck.set(self, draw=False)
        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.get_materialpath(path, cw.M_IMG), base=info))
        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        self.cardimg = cw.image.CharacterCardImage(self, can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=True)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()

    def update_delete(self):
        if self in cw.cwpy.sdata.friendcards:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            cw.cwpy.sdata.friendcards.remove(self)

        self.status = "hidden"

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if cw.cwpy.is_battlestatus():
            if self.is_inactive():
                s = cw.cwpy.msgs["inactive"] % self.name
                cw.cwpy.call_modaldlg("NOTICE", text=s)
            elif self.is_autoselectedpenalty() and not cw.cwpy.debug:
                s = cw.cwpy.msgs["selected_penalty"]
                cw.cwpy.call_modaldlg("NOTICE", text=s)
            else:
                cw.cwpy.call_modaldlg("HANDVIEW")
        elif (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if not cw.cwpy.is_battlestatus():
                cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　メニューカードスプライト
#-------------------------------------------------------------------------------

class MenuCard(CWPyCard):
    def __init__(self, data, pos_noscale=(0, 0), status="hidden", addgroup=True, index=0):
        """
        メニューカード用のスプライトを作成。
        """
        CWPyCard.__init__(self, status)
        assert hasattr(self, "alpha")
        # カード情報
        self.index = index
        self._data = data
        self._pos_noscale2 = pos_noscale
        self.name = data.gettext("Property/Name", "")
        self.desc = data.gettext("Property/Description", "")
        self.flag = data.gettext("Property/Flag", "")
        self.debug_only = data.getbool(".", "debugOnly", False)
        self.author = ""
        self.scenario = ""
        self._is_backpack = False
        self._is_storehouse = False

        # システムカード用の特殊パラメータ
        self.command = data.getattr(".", "command", "")
        self.arg = data.getattr(".", "arg", "")

        # スケール
        if cw.cwpy.is_autospread():
            self.scale = 100
        else:
            s = data.getattr("Property/Size", "scale", "100%")
            self.scale = int(s.rstrip("%"))

        self._init = False

        # 表示するまでデータを作らない
        if status == "hidden":
            self._rect = cw.s(pygame.Rect(0, 0, 0, 0))
            self.clear_image()
        else:
            self.initialize()

        layer = data.getint("Property/Layer", -1)
        if layer < 0:
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and (cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_SCENARIO)) or\
                                  cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA))):
                layer = cw.LAYER_MCARDS_120
            else:
                layer = cw.LAYER_MCARDS

        if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
            self.layer = (layer+cw.LAYER_SP_LAYER, cw.LTYPE_MCARDS, self.index, 0)
        else:
            self.layer = (layer, cw.LTYPE_MCARDS, self.index, 0)

        if addgroup:
            # spritegroupに追加
            cw.cwpy.cardgrp.add(self, layer=self.layer)
            cw.cwpy.mcards.append(self)

    def initialize(self):
        if self._init:
            return True

        self._init = True

        # イベント
        self.events = cw.event.EventEngine(self._data.getfind("Events"))

        is_scenariocard = 0 <= cw.cwpy.areaid and cw.cwpy.is_playingscenario()
        infos = cw.image.get_imageinfos(self._data.find("Property"), pcnumber=True)

        # 通常イメージ。LargeMenuCardはサイズ大のメニューカード作成
        paths = []
        can_loaded_scaledimages = []
        for info in infos:
            if info.path:
                paths.append(cw.image.ImageInfo(info.path, base=info))
                can_loaded_scaledimages.append(cw.cwpy.areaid < 0 or cw.cwpy.sdata.can_loaded_scaledimage)
            elif info.pcnumber:
                # メニューカードにPCの画像を表示(1.30)
                pcards = cw.cwpy.ydata.party.members
                pi = info.pcnumber - 1
                if 0 <= pi and pi < len(pcards):
                    can_loaded_scaledimage = pcards[pi].getbool(".", "scaledimage", False)
                    for info2 in cw.image.get_imageinfos(pcards[pi].find("Property")):
                        path = info2.path
                        if path:
                            path = cw.util.join_yadodir(path)
                        paths.append(cw.image.ImageInfo(path, info.pcnumber, base=info2, basecardtype="LargeCard"))
                        can_loaded_scaledimages.append(can_loaded_scaledimage)

        if self._data.tag == "LargeMenuCard":
            self._cardimg = cw.image.LargeCardImage(paths, "NORMAL", self.name,
                                                    can_loaded_scaledimage=can_loaded_scaledimages, is_scenariocard=is_scenariocard)
        else:
            self._cardimg = cw.image.CardImage(paths, "NORMAL", self.name,
                                               can_loaded_scaledimage=can_loaded_scaledimages, is_scenariocard=is_scenariocard)

        self.update_image()
        # pos
        self.set_pos_noscale(self._pos_noscale2)

        command = self._data.getattr(".", "command", "")
        if command == "MoveCard":
            arg = self._data.getattr(".", "arg", "")
            self._is_backpack = arg == "BACKPACK"
            self._is_storehouse = arg == "STOREHOUSE"

        # 初期化後は不要
        self._data = None
        self._pos_noscale2 = None
        return True

    @property
    def cardimg(self):
        if not self._init:
            self.initialize()
        return self._cardimg

    def is_initialized(self):
        return self._init

    def is_backpack(self):
        return self._is_backpack

    def is_storehouse(self):
        return self._is_storehouse

    def update(self, scr):
        if self.status <> "hidden" and not self._init:
            self.initialize()
        CWPyCard.update(self, scr)

    def lclick_event(self):
        """左クリックイベント。"""
        # 通常のクリックイベント
        if not cw.cwpy.is_curtained():
            cw.cwpy.play_sound("click", from_scenario=True)
            cw.animation.animate_sprite(self, "click")
            if self.command:
                cw.content.PostEventContent.do_action(self.command, self.arg)
            else:
                cw.cwpy.advlog.click_menucard(self)
                self.events.start(keynum=1)

        # カード移動操作
        elif cw.cwpy.areaid in (-1, -2, -5) and cw.cwpy.selectedheader:
            cw.animation.animate_sprite(self, "click")
            if self.command:
                cw.content.PostEventContent.do_action(self.command, self.arg)
            else:
                self.events.start(keynum=1)

        # カード使用イベント
        elif cw.cwpy.selectedheader:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")

            # USECARDダイアログを開く
            if cw.cwpy.status == "Scenario":
                cw.cwpy.call_modaldlg("USECARD")
            # 戦闘行動を設定する
            elif cw.cwpy.status == "ScenarioBattle":
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea()

        # キャンプ・パーティ解散
        elif cw.cwpy.areaid in (cw.AREA_CAMP, cw.AREA_BREAKUP):
            if cw.cwpy.areaid == cw.AREA_BREAKUP:
                cw.cwpy.play_sound("page")
            else:
                cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            if self.command:
                cw.content.PostEventContent.do_action(self.command, self.arg)
            else:
                self.events.start(keynum=1)

    def rclick_event(self):
        """右クリックイベント。"""
        if not cw.cwpy.is_showingdlg():
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            if self.desc:
                cw.cwpy.call_modaldlg("MENUCARDINFO")

def main():
    pass

if __name__ == "__main__":
    main()
