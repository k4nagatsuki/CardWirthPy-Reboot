#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
from . import base
from .. import character

import typing
from typing import Dict, Iterable, List, Optional, Tuple, Union


class CWPyCard(base.SelectableSprite):
    layer: Tuple[int, int, int, int]
    index: int
    reversed: bool

    def __init__(self, status: str, flag: Optional[str] = None) -> None:
        base.SelectableSprite.__init__(self)
        self.alpha: Optional[int] = None
        # 状態
        self.status = status
        self._clicking = False
        self.debug_only = False
        self.old_status = status
        self.rect = cw.s(pygame.Rect(0, 0, 0, 0))
        self._pos_noscale: Optional[Tuple[int, int]] = None
        self._center_noscale: Optional[Tuple[int, int]] = None
        # 前に表示中のカード
        self.inusecardimg: Optional[cw.sprite.background.InuseCardImage] = None
        # アニメ用フレーム数
        self.frame = 0
        # ズーム画像のリスト。(イメージ本体, 位置とサイズ)のタプル。
        self.zoomimgs: List[Tuple[pygame.surface.Surface, pygame.rect.Rect]] = []
        self.zoomsize_noscale = (0, 0)
        # 裏返し状態か否か
        self.reversed = False
        # カード使用のターゲットか否か
        self.cardtarget = False
        # 対応フラグ名
        self.flag = flag
        # スケール
        self.scale = 100
        # アクションの有無
        self.actions = {7: False}
        # Trueなら高速でアニメーションする
        self.highspeed = False
        # Trueなら戦闘時のアニメーション速度設定を使用する
        self.battlespeed = False
        # Trueの間はカード消去で使用中カードをクリアしない
        self.hide_inusecardimg = True
        # アニメーション速度の上書き(-1でプレイヤー設定値)
        self.dealspeed = -1
        # 名前にある特殊文字の展開の有無
        self.spchars = False
        # カードイメージ
        self._cardimg: Optional[cw.image.CardImage] = None

        # MenuCardの特殊コマンド
        self.command = ""
        self.arg = ""

    @property
    def cardimg(self) -> cw.image.CardImage:
        assert self._cardimg
        return self._cardimg

    def has_cardimg(self) -> bool:
        return self._cardimg is not None

    def get_showingname(self) -> str:
        return ""

    def is_flagtrue(self) -> bool:
        mcardflag = cw.cwpy.sdata.get_flagvalue(self.flag) if self.flag is not None else True
        mcardflag &= bool(not self.debug_only or cw.cwpy.is_debugmode())
        if mcardflag and self.command == "ShowDialog" and self.arg == "INFOVIEW":
            mcardflag &= bool(cw.cwpy.is_playingscenario() and cw.cwpy.sdata.has_infocards())
        elif mcardflag and self.command in ("MoveCard", "ShowDialog") and self.arg == "BACKPACK":
            mcardflag &= cw.cwpy.sdata.party_environment_backpack
        elif not cw.cwpy.setting.show_sell_with_premiercard and\
                mcardflag and self.command == "MoveCard" and self.arg in ("PAWNSHOP", "TRASHBOX"):
            mcardflag &= cw.cwpy.is_debugmode() or not cw.cwpy.setting.protect_premiercard or\
                         not cw.cwpy.selectedheader or cw.cwpy.selectedheader.premium != "Premium"
        return mcardflag

    @staticmethod
    def is_flagtrue_static(data: cw.data.CWPyElement) -> bool:
        flag = data.gettext("Property/Flag", "")
        mcardflag = bool(cw.cwpy.sdata.get_flagvalue(flag))
        if mcardflag:
            debug_only = data.getbool(".", "debugOnly", False)
            mcardflag &= bool(not debug_only or cw.cwpy.is_debugmode())
        if mcardflag:
            command = data.getattr(".", "command", "")
            if command == "ShowDialog" and data.getattr(".", "arg", "") == "INFOVIEW":
                mcardflag &= bool(cw.cwpy.is_playingscenario() and cw.cwpy.sdata.has_infocards())
            elif command in ("MoveCard", "ShowDialog") and data.getattr(".", "arg", "") == "BACKPACK":
                mcardflag &= cw.cwpy.sdata.party_environment_backpack
            elif not cw.cwpy.setting.show_sell_with_premiercard and\
                    command == "MoveCard" and data.getattr(".", "arg", "") in ("PAWNSHOP", "TRASHBOX"):
                mcardflag &= cw.cwpy.is_debugmode() or not cw.cwpy.setting.protect_premiercard or\
                             not cw.cwpy.selectedheader or cw.cwpy.selectedheader.premium != "Premium"
        return mcardflag

    def get_unselectedimage(self) -> pygame.surface.Surface:
        if self.status == "click":
            return self.image
        else:
            return self.get_animeimage()

    def get_selectedimage(self) -> pygame.surface.Surface:
        return cw.imageretouch.to_negative_for_card(self.get_animeimage())

    def set_alpha(self, alpha: Optional[int]) -> None:
        self.alpha = alpha
        for img, _rect in self.zoomimgs:
            img.set_alpha(alpha)
        self.image.set_alpha(alpha)
        self._image.set_alpha(alpha)

    def get_animeimage(self) -> pygame.surface.Surface:
        if self.zoomimgs:
            return self.zoomimgs[-1][0]
        else:
            return self._image

    def get_animerect(self) -> pygame.rect.Rect:
        if self.zoomimgs:
            return self.zoomimgs[-1][1]
        else:
            return self._rect

    def get_baserect(self) -> pygame.rect.Rect:
        return self._rect

    def _get_dealingscales(self) -> List[int]:
        if cw.cwpy.force_dealspeed != -1:
            return cw.cwpy.setting.create_dealingscales(cw.cwpy.force_dealspeed)
        elif self.dealspeed != -1:
            return cw.cwpy.setting.create_dealingscales(self.dealspeed)
        elif cw.cwpy.override_dealspeed != -1:
            return cw.cwpy.setting.create_dealingscales(cw.cwpy.override_dealspeed)
        elif self.battlespeed and cw.cwpy.setting.use_battlespeed:
            return cw.cwpy.setting.dealing_scales_battle
        else:
            return cw.cwpy.setting.dealing_scales

    def get_dealspeed(self, battlespeed: bool) -> int:
        """このカードがアニメーションする速度を返す。"""
        if cw.cwpy.force_dealspeed != -1:
            return cw.cwpy.force_dealspeed
        elif self.dealspeed != -1:
            return self.dealspeed
        elif cw.cwpy.override_dealspeed != -1:
            return cw.cwpy.override_dealspeed
        else:
            return cw.cwpy.setting.get_dealspeed(battlespeed)

    def _get_dealspeed(self) -> int:
        return self.get_dealspeed(self.battlespeed and cw.cwpy.setting.use_battlespeed)

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self) -> None:
        self.update_selection()

    def update_delete(self) -> None:
        pass

    def update_reversed(self) -> None:
        # デバッグモード時、またはキャンプ時(私有カード操作ができる場合)は反転中でも選択可能
        # ただしカード使用の選択対象にはならない
        if (cw.cwpy.is_debugmode() or (cw.cwpy.setting.show_personal_cards and isinstance(self, cw.character.Player) and
                                       cw.cwpy.areaid == cw.AREA_CAMP)) and not cw.cwpy.selectedheader:
            assert isinstance(self, cw.sprite.card.CWPyCard)
            self.update_selection()

    def update_hidden(self) -> None:
        pass

    def update_reverse(self) -> None:
        """
        カードをひっくり返す。
        """
        if self.old_status == "hidden":
            self.reversed = not self.reversed
            self._reverse()
            self.status = "hidden"
            return

        self.hide_inusecardimg = False
        cardtarget = self.cardtarget
        self.update_hide()
        self.cardtarget = cardtarget
        self.hide_inusecardimg = True

        if self.status == "hidden":
            cw.cwpy.wait_frame(1)
            self.reversed = not self.reversed

            self._reverse()

            cw.animation.animate_sprite(self, "deal")

            if self.reversed:
                self.status = "reversed"

    def reverse(self) -> None:
        """
        アニメーション無しでカードをひっくり返す。
        """
        self.reversed = not self.reversed
        self._reverse()

    def _reverse(self) -> None:
        # 表←→裏の画像切り替え
        if self.reversed:
            image = cw.cwpy.rsrc.cardbgs["REVERSE"]

            if not self.scale == 100:
                scale = self.scale / 100.0
                image = cw.image.zoomcard(image, scale)
            else:
                image = image.copy()

            image.set_alpha(self.alpha)
            self._image: pygame.surface.Surface = image
            if self.zoomimgs:
                self.rect = pygame.Rect(self.zoomimgs[-1][1])

            for i, t in enumerate(self.zoomimgs):
                img, rect = t
                # 最大の一枚のみは長時間表示される
                # 可能性があるためスムージングする
                if i + 1 == len(self.zoomimgs) and cw.cwpy.setting.smoothing_card_up:
                    img = cw.image.smoothscale_card(image, rect.size)
                else:
                    img = pygame.transform.scale(image, rect.size)
                self.zoomimgs[i] = (img, rect)

        else:
            self.update_image()

    def update_click(self) -> None:
        """
        クリック時のアニメーションを呼び出すメソッド。
        """
        assert self._cardimg
        lifebars = cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_FRONT_LIFEBAR)
        lifebar: Optional[cw.sprite.background.LifeBar] = None
        if lifebars:
            sprite = lifebars[0]
            assert isinstance(sprite, cw.sprite.background.LifeBar)
            if sprite.ccard is self:
                lifebar = sprite
        if self.frame < 3 and not self._clicking:
            if lifebar:
                lifebar.click()
            if self.reversed:
                self.image = self.cardimg.get_clickedimg(self.get_animerect(), image=self.image).copy()
            else:
                self.image = self.cardimg.get_clickedimg(self.get_animerect()).copy()
            self.image.set_alpha(self.alpha)
            self.rect = self.image.get_rect(center=self.get_animerect().center)
            self.status = "click"
            self._clicking = True
        elif 3 <= self.frame:
            if lifebar:
                lifebar.declick()
            self.status = self.old_status
            self._clicking = False
            self.image = self.get_selectedimage()
            self.rect = pygame.Rect(self.get_animerect())
            self.frame = 0
            return

        self.frame += 1

    def update_deal(self) -> None:
        """
        カード表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(self._get_dealingscales()):
            self.deal()
            self.frame = 0
            return

        if self.frame == 0 and self._cardimg and self.cardimg.is_modifiedfile():
            self.update_image()

        n = self._get_dealingscales()[::-1][self.frame]
        rect = self.get_animerect()
        size = rect.w * n // 100, rect.h
        self.image = pygame.transform.scale(self.get_animeimage(), size)

        # 反転表示中
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)

        self.rect = self.image.get_rect(center=rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def deal(self) -> None:
        """カードをアニメーション無しで表示する。"""
        if self.reversed:
            self.status = "reversed"
        else:
            self.status = "normal"
        if self._cardimg and (self.cardimg.is_modifiedfile() or self.image.get_width() <= 0):
            self.update_image()
        self.image = self.get_animeimage()
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)
        self.rect = pygame.Rect(self.get_animerect())

    def update_hide(self) -> None:
        """
        カード非表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(self._get_dealingscales()):
            self.hide()
            self.frame = 0
            return

        n = self._get_dealingscales()[self.frame]
        rect = self.get_animerect()
        size = rect.w * n // 100, rect.h
        self.image = pygame.transform.scale(self.get_animeimage(), size)

        # 反転表示中
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)

        self.rect = self.image.get_rect(center=rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def hide(self) -> None:
        """カードをアニメーション無しで非表示にする。"""
        self.status = "hidden"
        self.clear_image()
        if self.hide_inusecardimg:
            cw.cwpy.clear_inusecardimg(self)
        self.clear_cardtarget()

    def update_lateralvibe(self) -> None:
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
        mx = 2  # 最大移動量
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
        else:
            assert False

        val = int(round(val))

        self.rect = pygame.Rect(self.get_animerect())
        self.rect.move_ip(cw.s(val), cw.s(0))
        self.frame += 1

    def update_axialvibe(self) -> None:
        """
        縦振動させる。
        実際には横幅の周期的変動によって表現される。
        """
        n = (self._get_dealspeed()+1) * 3
        if self.frame >= n:
            self.rect = pygame.Rect(self.get_animerect())
            if self.image.get_size() != self.rect.size:
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
        mx = self._rect.width // 20  # 最大縮小量
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

    def update_zoomin(self) -> None:
        """
        カードを拡大する。
        """
        self._update_zoominout(self._get_dealspeed()+1, True)

    def update_zoomin_slow(self) -> None:
        """
        カードをゆっくりと拡大する。
        """
        self._update_zoominout(self._get_dealspeed()*2+1, True)

    def update_zoomout(self) -> None:
        """
        カードを縮小する。
        """
        self._update_zoominout(self._get_dealspeed()+1, False)

    def update_zoomout_slow(self) -> None:
        """
        カードをゆっくりと縮小する。
        """
        self._update_zoominout(self._get_dealspeed()*2+1, False)

    def _update_zoominout(self, ds: int, inout: bool) -> None:
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
            def calc_zoom(zoom_val: int) -> int:
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
            self.image = cw.image.smoothscale_card(self.zoomimgs[0][0], (w, h))
        else:
            self.image = pygame.transform.scale(self.zoomimgs[0][0], (w, h))
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

    def clear_zoomimgs(self) -> None:
        del self.zoomimgs[:]
        if self.status == "hidden":
            self.clear_image(move=False)

    def update_shiftup(self) -> None:
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
            if rect is not self.rect:
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

    def update_shiftdown(self) -> None:
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

    def update_scale(self) -> None:
        if not self.is_initialized():
            return
        if not self.cardimg:
            return

        zoom = 0 < len(self.zoomimgs)

        if zoom and self.status not in ("zoomin", "zoomout"):
            if self.status != "zoomout":
                self.old_status = self.status
                self.status = "zoomout"
            while self.status == "zoomout":
                self.update_zoomout()

        self.cardimg.update_scale()
        self.update_image()
        if self._pos_noscale or self._center_noscale:
            self.set_pos_noscale(self._pos_noscale, self._center_noscale)

        if zoom and self.status not in ("zoomin", "zoomout"):
            if self.status != "zoomin":
                self.old_status = self.status
                self.status = "zoomin"
            while self.status == "zoomin":
                self.update_zoomin()

        if self.status == "hidden":
            self.clear_image(True)

    def update_image(self, update_statusimg: bool = False,
                     is_runningevent: Optional[bool] = None) -> Optional[pygame.rect.Rect]:
        """
        画像を再構成する。
        """
        if not self._cardimg:
            return None

        # 画像参照
        if update_statusimg:
            assert isinstance(self._cardimg, cw.image.CharacterCardImage)
            assert isinstance(self, (PlayerCard, EnemyCard, FriendCard))
            clip = self._cardimg.update_statusimg(self, is_runningevent=is_runningevent)
            if not clip:
                return None
        else:
            if hasattr(self, "test_aptitude"):
                assert isinstance(self._cardimg, cw.image.CharacterCardImage)
                assert isinstance(self, (PlayerCard, EnemyCard, FriendCard))
                self._cardimg.update(self, self.test_aptitude)
            else:
                self.cardimg.update(self)
            clip = pygame.Rect(self.rect)

        image = self.cardimg.get_image().copy()
        image.set_alpha(self.alpha)
        rect = self.cardimg.rect

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
        self._rect: pygame.rect.Rect = pygame.Rect(self.rect)
        self._rect.topleft = rect.topleft

        if self.reversed:
            # リバース状態
            self._reverse()
            if not self.zoomimgs:
                self.image = self._image
        elif self.zoomimgs:
            # ズーム画像も更新
            self.zoomimgs[0] = self._image, self.zoomimgs[0][1]
            for i, t in enumerate(self.zoomimgs[1:]):
                rect = t[1]
                w = rect[2]
                h = rect[3]
                # 最大の一枚のみは長時間表示される
                # 可能性があるためスムージングする
                if i + 1 == len(self.zoomimgs)-1 and cw.cwpy.setting.smoothing_card_up:
                    image = cw.image.smoothscale_card(self._image, (w, h))
                else:
                    image = pygame.transform.scale(self._image, (w, h))
                self.zoomimgs[i+1] = image, rect
            self.image = self.zoomimgs[-1][0]
            self.rect = pygame.Rect(self.zoomimgs[-1][1])

        if self.status == "hidden":
            self.clear_image(False)

        return clip

    def clear_image(self, move: bool = True) -> None:
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        if move:
            topleft = self.rect.topleft
            self.rect = self.image.get_rect()
            self.rect.topleft = topleft

    def set_pos_noscale(self, pos_noscale: Optional[Tuple[int, int]] = None,
                        center_noscale: Optional[Tuple[int, int]] = None) -> None:
        """画面の拡大率を考慮せずに座標を設定する。"""
        if pos_noscale:
            self._pos_noscale = pos_noscale
        elif center_noscale:
            self._center_noscale = center_noscale
        pos = cw.s(pos_noscale) if pos_noscale else None
        center = cw.s(center_noscale) if center_noscale else None
        self.set_pos(pos, center)

    def set_pos(self, pos: Optional[Tuple[int, int]] = None, center: Optional[Tuple[int, int]] = None) -> None:
        """画面の拡大率を反映済みの座標を設定する。"""
        if pos:
            self._rect.topleft = pos
        elif center:
            self._rect.center = center

        self.rect.center = self._rect.center
        if self.zoomimgs:
            for image, zrect in self.zoomimgs:
                zrect.center = self._rect.center

        if self._cardimg:
            self.cardimg.rect.topleft = self._rect.topleft

    def get_pos_noscale(self) -> Tuple[int, int]:
        assert self._pos_noscale
        return self._pos_noscale

    def set_scale(self, scale: int) -> None:
        if scale == self.scale:
            return
        for image, zrect in self.zoomimgs:
            zrect.width = int(zrect.width * (float(scale) / self.scale))
            zrect.height = int(zrect.height * (float(scale) / self.scale))
        self.scale = scale
        self.update_image()

    def set_cardtarget(self) -> None:
        if not self.cardtarget:
            self.cardtarget = True
            self.update_image()
            cw.cwpy.add_lazydraw(clip=self.rect)

    def clear_cardtarget(self) -> None:
        if self.cardtarget:
            self.cardtarget = False
            self.update_image()
            cw.cwpy.add_lazydraw(clip=self.rect)


# ------------------------------------------------------------------------------
# プレイヤーカードスプライト
# ------------------------------------------------------------------------------

class PlayerCard(CWPyCard, character.Player):
    def __init__(self, data: cw.data.CWPyElementTree, pos_noscale: Tuple[int, int] = (0, 0),
                 status: str = "hidden", index: int = 0) -> None:
        CWPyCard.__init__(self, status)
        self.zoomsize_noscale = (16, 22)
        # CharacterCard初期化
        character.Player.__init__(self, data)
        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find_exists("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.join_paths(cw.cwpy.yadodir, path), base=info))

        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        self._cardimg: cw.image.CharacterCardImage =\
            cw.image.CharacterCardImage(self, pos_noscale=pos_noscale, can_loaded_scaledimage=can_loaded_scaledimage)
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
        if not self.has_coupon("＠ＥＰ"):
            self.set_coupon("＠ＥＰ", 0)

        # "：Ｒ"クーポンを所持していたら反転フラグON
        if self.has_coupon("：Ｒ"):
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

    def set_pos(self, pos: Optional[Tuple[int, int]] = None, center: Optional[Tuple[int, int]] = None) -> None:
        CWPyCard.set_pos(self, pos, center)
        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(cw.s(0), cw.s(+150))

    @property
    def cardimg(self) -> cw.image.CharacterCardImage:
        assert self._cardimg
        return self._cardimg

    def get_showingname(self) -> str:
        return self.name

    def set_name(self, name: str) -> None:
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
        character.Player.set_name(self, name)
        self.cardimg.set_nameimg(self.get_name())

    def set_images(self, paths: List[cw.image.ImageInfo]) -> List[cw.image.ImageInfo]:
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
        paths = character.Player.set_images(self, paths)
        self.imgpaths = []
        for info in paths:
            self.imgpaths.append(cw.image.ImageInfo(cw.util.join_paths(cw.cwpy.yadodir, info.path), base=info))
        self.cardimg.set_faceimgs(self.imgpaths, can_loaded_scaledimage=True)

        def func() -> None:
            def func() -> None:
                num = cw.cwpy.get_pcards().index(self)+1
                cw.cwpy.update_pcimage(num, deal=True)
            cw.cwpy.exec_func(func)
        cw.cwpy.exec_func(func)

        return self.imgpaths

    def update_levelup(self) -> None:
        """レベルアップ処理。"""
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
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

    def update_delete(self) -> None:
        """パーティから外す。"""
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.ydata.party.remove(self)

    def update_vanish(self) -> None:
        """仮の対象消去。clear_vanish()で復元する事ができる。"""
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.pcards.remove(self)

    def lclick_event(self) -> None:
        """左クリックイベント。"""
        if self.reversed and not (cw.cwpy.setting.show_personal_cards and cw.cwpy.areaid == cw.AREA_CAMP):
            self.rclick_event()

        # CARDPOCKETダイアログを開く(通常)
        elif not cw.cwpy.is_curtained():
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")

            if cw.cwpy.is_battlestatus():
                if self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                elif self.is_autoselectedpenalty() and not cw.cwpy.is_debugmode():
                    s = cw.cwpy.msgs["selected_penalty"]
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                elif self.deck.hand:
                    cw.cwpy.call_modaldlg("HANDVIEW")
            else:
                if self.is_inactive() and cw.cwpy.areaid not in cw.AREAS_TRADE:
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("CARDPOCKET")

        # カード移動操作
        elif cw.cwpy.areaid in cw.AREAS_TRADE and cw.cwpy.selectedheader:
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
                _select_action(self)

        # パーティ離脱
        elif cw.cwpy.areaid == -3:
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.dissolve_party(self)

        # キャンプ
        elif cw.cwpy.areaid == cw.AREA_CAMP:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self) -> None:
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")
        cw.cwpy.call_modaldlg("CHARAINFO")

    def set_level(self, value: int, regulate: bool = False, debugedit: bool = False,
                  backpack_party: Optional[cw.data.Party] = None, revert_cardpocket: bool = True) -> None:
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
        character.Player.set_level(self, value, regulate, debugedit, backpack_party, revert_cardpocket)
        self.cardimg.set_levelimg(self.level)

    def adjust_level(self, fromscenario: bool) -> bool:
        """経験点を確認し、条件を満たしていれば
        レベルアップ・ダウン処理を行う。
        fromscenarioがTrueであれば同時に完全回復も行う。
        状態が変化すればTrueを返す。
        """
        assert cw.cwpy.ydata
        result = False
        if fromscenario and cw.cwpy.is_debugmode() and\
                cw.cwpy.setting.no_levelup_in_debugmode:
            levelup = 0
        else:
            levelup = self.check_level()
            if fromscenario:
                # シナリオクリア時にはレベルダウンしない
                levelup = max(0, levelup)

        level = self.level  # 再調節に使用

        # レベルアップ
        if levelup != 0:
            base = self.get_specialcoupons()["＠レベル原点"]
            n = base + levelup
            if fromscenario:
                if 1 < levelup:
                    # 複数回レベルアップした場合はその分回転表示する
                    cw.animation.animate_sprite(self, "levelup")
                    for i in range(levelup - 1):
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
        if fromscenario or levelup != 0:
            result = True
            cw.cwpy.play_sound("harvest", True)
            cw.animation.animate_sprite(self, "hide")
            if fromscenario:
                self.set_fullrecovery()
            self.update_image()
            cw.animation.animate_sprite(self, "deal")

        # レベルアップメッセージ
        if fromscenario and 0 < levelup:
            assert cw.cwpy.ydata.party
            text = cw.cwpy.msgs["level_up"]
            names = [(0, cw.cwpy.msgs["ok"])]
            infos: List[Tuple[cw.image.ImageInfo, bool, Optional[Union[cw.character.Character, cw.header.CardHeader]],
                              Dict[int, pygame.surface.Surface]]] = []
            can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
            for info in self.imgpaths:
                infos.append((cw.image.ImageInfo(path=info.path, pcnumber=info.pcnumber, base=info,
                                                 basecardtype="LargeCard"),
                              can_loaded_scaledimage, self, {}))
            mwin = cw.sprite.message.MessageWindow(text, names, infos, self,
                                                   versionhint=self.versionhint,
                                                   centering_x=False, centering_y=True, boundarycheck=True)
            cw.cwpy.show_message(mwin)
            if base != level or cw.cwpy.ydata.party.is_suspendlevelup:
                # レベル調節中だった場合は再調節
                # レベルアップ停止中であれば元のレベルへ調節
                cw.animation.animate_sprite(self, "hide")
                self.set_level(level, regulate=True)
                self.update_image()
                cw.animation.animate_sprite(self, "deal")

        return result

    def lost(self) -> None:
        cw.character.Player.lost(self)
        for pocket in self.cardpocket:
            for card in pocket[:]:
                cw.cwpy.trade("TRASHBOX", header=card, from_event=True, sort=False)


def _select_action(sprite: "cw.sprite.card.CWPyCard") -> None:
    """戦闘行動選択エリアで対象を左クリックした時の処理。"""
    header = cw.cwpy.selectedheader
    assert header
    owner = header.get_owner()
    assert isinstance(owner, cw.character.Character)
    owner.set_action(sprite, header)
    cw.cwpy.clear_specialarea(redraw=False)
    if cw.cwpy.selection == sprite:
        # 自分を狙う戦闘行動を不透明状態で再描画する
        assert isinstance(owner, cw.sprite.card.CWPyCard)
        cw.cwpy.change_selection(sprite, forceredraw=owner)


# ------------------------------------------------------------------------------
# エネミーカードスプライト
# ------------------------------------------------------------------------------

class EnemyCard(CWPyCard, character.Enemy):
    def __init__(self, mcarddata: cw.data.CWPyElement, pos_noscale: Tuple[int, int] = (0, 0),
                 status: str = "hidden", addgroup: bool = True, index: int = 0,
                 moveddata: Optional[Tuple[int, int, int, int]] = None) -> None:
        CWPyCard.__init__(self, status)
        self.zoomsize_noscale = (16, 22)
        self.index = index
        self.mcarddata = mcarddata
        if moveddata:
            self._init_pos_noscale: Optional[Tuple[int, int]] = (moveddata[0], moveddata[1])
        else:
            self._init_pos_noscale = pos_noscale
        # フラグ
        self.flag = mcarddata.gettext("Property/Flag", "")
        # カードグループ
        self.cardgroup = mcarddata.gettext("Property/CardGroup", "")
        # 逃走の有無(Wsn.3以前)
        self.actions[7] = mcarddata.getbool(".", "escape", False)
        # アクションの有無(Wsn.4)
        e_actions = mcarddata.find("Property/Actions")
        if e_actions is not None:
            for e_action in e_actions:
                if e_action.tag != "Action":
                    continue
                actid = e_action.getint(".", "id")
                self.actions[actid] = e_action.getbool(".", True)
        # 名前にある特殊文字の展開の有無
        self.spchars = False
        # スケール
        if moveddata and moveddata[2] != -1:
            self.scale = moveddata[2]
        elif cw.cwpy.is_autospread():
            self.scale = 100
        else:
            s = mcarddata.getattr("Property/Size", "scale", "100%")
            self.scale = int(s.rstrip("%"))

        # アニメーション速度
        dealspeed = mcarddata.gettext("Property/DealingSpeed", "Default")
        if dealspeed == "Default":
            self.dealspeed = -1
        else:
            self.dealspeed = cw.util.numwrap(int(dealspeed), 0, 10)

        self.spchars = mcarddata.getbool("Property/Name", "override", False)

        self._init = False

        # 表示するまでデータを作らない
        if status == "hidden":
            self._rect = cw.s(pygame.Rect(0, 0, 0, 0))
            self.clear_image()
        else:
            if not self.initialize():
                raise Exception()

        if moveddata and moveddata[3] != -1:
            layer = moveddata[3]
        else:
            layer = mcarddata.getint("Property/Layer", -1)
        if layer < 0:
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and (cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_SCENARIO)) or
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
            if self.spchars:
                cw.cwpy.mcards_expandspchars.add(self)

    def initialize(self) -> bool:
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
            cw.cwpy.mcards_expandspchars.discard(self)
            cw.cwpy.file_updates.discard(self)
            return False
        self.data = cw.data.xml2etree(element=e)
        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Enemy.__init__(self, self.data)
        self.update_skin()
        self.deck.set(self, draw=False)

        if self.spchars:
            self._name = self.mcarddata.gettext("Property/Name", "")
            override_name = cw.sprite.message.rpl_specialstr(self._name, expandsharps=False, localvariables=False)[0]
        else:
            self._name = self.data.gettext("Property/Name", "")
            override_name = ""

        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find_exists("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.get_materialpath(path, cw.M_IMG), base=info))

        # イメージの上書き(Wsn.4)
        is_override_image = self.mcarddata.getbool("Property/ImagePaths", "override", False)
        if is_override_image:
            override_infos = cw.image.get_imageinfos(self.mcarddata.find_exists("Property"), pcnumber=True)
            override_images = imageinfos_to_pathdata(override_infos)
        else:
            override_images = [], []

        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        assert self._init_pos_noscale
        self._cardimg: cw.image.CharacterCardImage =\
            cw.image.CharacterCardImage(self, pos_noscale=self._init_pos_noscale,
                                        can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=True,
                                        is_override_name=self.spchars, override_name=override_name,
                                        is_override_image=is_override_image,
                                        override_images=override_images)
        self.set_pos_noscale(pos_noscale=self._init_pos_noscale)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()
        return True

    def is_initialized(self) -> bool:
        return self._init

    def update_skin(self) -> None:
        if cw.cwpy.classicdata:
            act0 = self.actions.get(0, True)
            items = self.cardpocket[cw.POCKET_ITEM]
            if len(items) and items[0].name == cw.cwpy.rsrc.actioncards[0].name:
                # BUG: 一枚目のアイテムカードの名前が「カード交換」と同じだった場合、
                #      本来の「カード交換」が配布されない CardWirth 1.50
                self.actions[0] = False
            else:
                self.actions[0] = True
            if self.actions[0] != act0:
                self.deck.set(self, draw=False)

    @property
    def cardimg(self) -> cw.image.CharacterCardImage:
        assert self._cardimg
        return self._cardimg

    def get_showingname(self) -> str:
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
        self.initialize()
        if self.spchars:
            return self.cardimg.override_name
        else:
            return self._name

    def update_name(self) -> None:
        assert isinstance(self.cardimg, cw.image.CharacterCardImage)
        if not self._init:
            return
        if self.spchars:
            in_inusecardevent = cw.cwpy.event.in_inusecardevent
            try:
                cw.cwpy.event.in_inusecardevent = False
                name = cw.sprite.message.rpl_specialstr(self._name, expandsharps=False, localvariables=False)[0]
                if self.cardimg.override_name != name:
                    self.cardimg.override_name = name
                    self.cardimg.set_nameimg(name)
                    self.update_image()
            finally:
                cw.cwpy.event.in_inusecardevent = in_inusecardevent

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        if self.status != "hidden" and not self._init:
            if not self.initialize():
                return
        CWPyCard.update(self, *args, **kwargs)

    def update_delete(self) -> None:
        if self.old_status == "hidden":
            self.hide()
        else:
            self.update_hide()

        if self.frame == 0:
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.mcards.remove(self)
            cw.cwpy.mcards_expandspchars.discard(self)
            cw.cwpy.file_updates.discard(self)

    def lclick_event(self) -> None:
        """左クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        # CARDPOCKETダイアログを開く(通常)
        if (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if cw.cwpy.is_battlestatus():
                if self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                elif self.deck.hand:
                    cw.cwpy.call_modaldlg("HANDVIEW")

        # カード使用。戦闘行動を設定する。
        elif cw.cwpy.selectedheader:
            if cw.cwpy.is_battlestatus():
                _select_action(self)

    def rclick_event(self) -> None:
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")

    def get_pos_noscale(self) -> Tuple[int, int]:
        if self.is_initialized():
            return CWPyCard.get_pos_noscale(self)
        else:
            assert self._init_pos_noscale
            return self._init_pos_noscale

    def set_pos_noscale(self, pos_noscale: Optional[Tuple[int, int]] = None,
                        center_noscale: Optional[Tuple[int, int]] = None) -> None:
        if self.is_initialized():
            CWPyCard.set_pos_noscale(self, pos_noscale, center_noscale)
        else:
            self._init_pos_noscale = pos_noscale

    def set_scale(self, scale: int) -> None:
        if self.is_initialized():
            CWPyCard.set_scale(self, scale)
        else:
            self.scale = scale


# ------------------------------------------------------------------------------
# フレンドカードスプライト
# ------------------------------------------------------------------------------

class FriendCard(CWPyCard, character.Friend):
    def __init__(self, data: Union[cw.data.CWPyElement, cw.data.CWPyElementTree], index: int = 0) -> None:
        CWPyCard.__init__(self, "hidden")
        self.zoomsize_noscale = (32, 42)
        self.index = index
        self.layer = (cw.LAYER_FCARDS, cw.LTYPE_FCARDS, self.index, 0)
        self.layer_t = (cw.LAYER_FCARDS_T, cw.LTYPE_FCARDS, self.index, 0)

        if isinstance(data, cw.data.CWPyElement):
            data = cw.data.xml2etree(element=data)
        self.data = data
        self.id = self.data.getint("Property/Id", 1)

        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Friend.__init__(self, data)
        self.deck.set(self, draw=False)
        # カード画像
        self.imgpaths = []
        for info in cw.image.get_imageinfos(self.data.find_exists("Property")):
            path = info.path
            self.imgpaths.append(cw.image.ImageInfo(cw.util.get_materialpath(path, cw.M_IMG), base=info))
        can_loaded_scaledimage = self.data.getbool(".", "scaledimage", False)
        self._cardimg: cw.image.CharacterCardImage =\
            cw.image.CharacterCardImage(self, can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=True)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()

    @property
    def cardimg(self) -> cw.image.CharacterCardImage:
        assert self._cardimg
        return self._cardimg

    def get_showingname(self) -> str:
        return self.name

    def update_delete(self) -> None:
        if self in cw.cwpy.sdata.friendcards:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            cw.cwpy.sdata.friendcards.remove(self)

        self.status = "hidden"

    def lclick_event(self) -> None:
        """左クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if cw.cwpy.is_battlestatus():
            if self.is_inactive():
                s = cw.cwpy.msgs["inactive"] % self.name
                cw.cwpy.call_modaldlg("NOTICE", text=s)
            elif self.is_autoselectedpenalty() and not cw.cwpy.is_debugmode():
                s = cw.cwpy.msgs["selected_penalty"]
                cw.cwpy.call_modaldlg("NOTICE", text=s)
            elif self.deck.hand:
                cw.cwpy.call_modaldlg("HANDVIEW")
        elif (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if not cw.cwpy.is_battlestatus():
                cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self) -> None:
        """右クリックイベント。"""
        cw.cwpy.play_sound("click")
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")


# ------------------------------------------------------------------------------
# メニューカードスプライト
# ------------------------------------------------------------------------------

class MenuCard(CWPyCard):
    def __init__(self, data: cw.data.CWPyElement, pos_noscale: Tuple[int, int] = (0, 0), status: str = "hidden",
                 addgroup: bool = True, index: int = 0, moveddata: Optional[Tuple[int, int, int, int]] = None,
                 splayer: Optional[bool] = None) -> None:
        """
        メニューカード用のスプライトを作成。
        """
        CWPyCard.__init__(self, status)
        assert hasattr(self, "alpha")
        # カード情報
        self.index = index
        self._data: Optional[cw.data.CWPyElement] = data
        if moveddata:
            self._pos_noscale2: Optional[Tuple[int, int]] = (moveddata[0], moveddata[1])
        else:
            self._pos_noscale2 = pos_noscale
        self._cardimg: Optional[cw.image.CardImage] = None
        self._name = data.gettext("Property/Name", "")
        self.desc = data.gettext("Property/Description", "")
        self.flag = data.gettext("Property/Flag", "")
        self.cardgroup = data.gettext("Property/CardGroup", "")
        self.debug_only = data.getbool(".", "debugOnly", False)
        self.author = ""
        self.scenario = ""
        self.negaflag = False
        self._is_backpack = False
        self._is_storehouse = False

        # 名前にある特殊文字の展開の有無
        self.spchars = data.getbool("Property/Name", "spchars", False)

        # システムカード用の特殊パラメータ
        self.command = data.getattr(".", "command", "")
        self.arg = data.getattr(".", "arg", "")

        # スケール
        if moveddata and moveddata[2] != -1:
            self.scale = moveddata[2]
        elif cw.cwpy.is_autospread():
            self.scale = 100
        else:
            s = data.getattr("Property/Size", "scale", "100%")
            self.scale = int(s.rstrip("%"))

        # アニメーション速度
        dealspeed = data.gettext("Property/DealingSpeed", "Default")
        if dealspeed == "Default":
            self.dealspeed = -1
        else:
            self.dealspeed = cw.util.numwrap(int(dealspeed), 0, 10)

        self._init = False

        # 表示するまでデータを作らない
        if status == "hidden":
            self._rect = cw.s(pygame.Rect(0, 0, 0, 0))
            self.clear_image()
        else:
            self.initialize()

        if moveddata and moveddata[3] != -1:
            layer = moveddata[3]
        else:
            layer = data.getint("Property/Layer", -1)
        if layer < 0:
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
            if cw.cwpy.sdata and (cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_SCENARIO)) or
                                  cw.cwpy.sct.zindexmode(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA))):
                layer = cw.LAYER_MCARDS_120
            else:
                layer = cw.LAYER_MCARDS

        if splayer is None:
            splayer = cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP

        if splayer:
            self.layer = (layer+cw.LAYER_SP_LAYER, cw.LTYPE_MCARDS, self.index, 0)
        else:
            self.layer = (layer, cw.LTYPE_MCARDS, self.index, 0)

        if addgroup:
            # spritegroupに追加
            cw.cwpy.cardgrp.add(self, layer=self.layer)
            cw.cwpy.mcards.append(self)
            if self.spchars:
                cw.cwpy.mcards_expandspchars.add(self)

    def initialize(self) -> bool:
        if self._init:
            return True
        assert self._data is not None

        self._init = True

        self.update_name()

        # イベント
        self.events = cw.event.EventEngine(self._data.getfind("Events"))

        is_scenariocard = 0 <= cw.cwpy.areaid and cw.cwpy.is_playingscenario()
        infos = cw.image.get_imageinfos(self._data.find_exists("Property"), pcnumber=True)

        # 通常イメージ。LargeMenuCardはサイズ大のメニューカード作成
        paths, can_loaded_scaledimages = imageinfos_to_pathdata(infos)

        if self._data.tag == "LargeMenuCard":
            self._cardimg = cw.image.LargeCardImage(paths, "NORMAL", self.name,
                                                    can_loaded_scaledimage=can_loaded_scaledimages,
                                                    is_scenariocard=is_scenariocard)
        else:
            self._cardimg = cw.image.CardImage(paths, "NORMAL", self.name,
                                               can_loaded_scaledimage=can_loaded_scaledimages,
                                               is_scenariocard=is_scenariocard)

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

    def get_showingname(self) -> str:
        return self.name

    def update_name(self) -> None:
        if not self._init:
            return
        if self.spchars:
            self.name = cw.sprite.message.rpl_specialstr(self._name, expandsharps=False, localvariables=False)[0]
        else:
            self.name = self._name
        if self._cardimg and self._cardimg.name != self.name:
            self._cardimg.name = self.name
            self._cardimg.clear_cache()
            self.update_image()

    @property
    def cardimg(self) -> cw.image.CardImage:
        if not self._init:
            self.initialize()
        assert self._cardimg
        return self._cardimg

    def is_initialized(self) -> bool:
        return self._init

    def is_backpack(self) -> bool:
        return self._is_backpack

    def is_storehouse(self) -> bool:
        return self._is_storehouse

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        if self.status != "hidden" and not self._init:
            self.initialize()
        CWPyCard.update(self, *args, **kwargs)

    def lclick_event(self) -> None:
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
        elif cw.cwpy.areaid in cw.AREAS_TRADE and cw.cwpy.selectedheader:
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
                _select_action(self)

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

    def rclick_event(self) -> None:
        """右クリックイベント。"""
        if not cw.cwpy.is_showingdlg():
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            if self.desc:
                cw.cwpy.call_modaldlg("MENUCARDINFO")

    def get_pos_noscale(self) -> Tuple[int, int]:
        if self.is_initialized():
            return CWPyCard.get_pos_noscale(self)
        else:
            assert self._pos_noscale2
            return self._pos_noscale2

    def set_pos_noscale(self, pos_noscale: Optional[Tuple[int, int]] = None,
                        center_noscale: Optional[Tuple[int, int]] = None) -> None:
        if self.is_initialized():
            CWPyCard.set_pos_noscale(self, pos_noscale, center_noscale)
        else:
            self._pos_noscale2 = pos_noscale

    def set_scale(self, scale: int) -> None:
        if self.is_initialized():
            CWPyCard.set_scale(self, scale)
        else:
            self.scale = scale


def imageinfos_to_pathdata(infos: Iterable[cw.image.ImageInfo]) -> Tuple[List[cw.image.ImageInfo], List[bool]]:
    """
    infosを実際に表示するファイルのパスとスケーリング可否情報に変換する。
    """
    paths = []
    can_loaded_scaledimages = []
    for info in infos:
        if info.path:
            paths.append(cw.image.ImageInfo(info.path, base=info))
            can_loaded_scaledimages.append(cw.cwpy.areaid < 0 or cw.cwpy.sdata.can_loaded_scaledimage)
        elif info.pcnumber:
            # メニューカードにPCの画像を表示(1.30)
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            pcards = cw.cwpy.ydata.party.members
            pi = info.pcnumber - 1
            if 0 <= pi and pi < len(pcards):
                can_loaded_scaledimage = pcards[pi].getbool(".", "scaledimage", False)
                for info2 in cw.image.get_imageinfos(pcards[pi].find_exists("Property")):
                    path = info2.path
                    if path:
                        path = cw.util.join_yadodir(path)
                    paths.append(cw.image.ImageInfo(path, info.pcnumber, base=info2, basecardtype="LargeCard"))
                    can_loaded_scaledimages.append(can_loaded_scaledimage)
    return paths, can_loaded_scaledimages


def main() -> None:
    pass


if __name__ == "__main__":
    main()
