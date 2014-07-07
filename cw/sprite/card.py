#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
import cw.binary.image
import base
from .. import character


class CWPyCard(base.SelectableSprite):
    def __init__(self, status, flag=None):
        base.SelectableSprite.__init__(self)
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
        self.zoomsize_noscale = (16, 21)
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
        # Trueの間はカード消去で使用中カードをクリアしない
        self.hide_inusecardimg = True

    def is_initialized(self):
        return True

    def get_unselectedimage(self):
        return self.get_animeimage()

    def get_selectedimage(self):
        return cw.imageretouch.to_negative_for_card(self.get_animeimage())

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

    def _reverse(self):
        # 表←→裏の画像切り替え
        if self.reversed:
            image = cw.cwpy.rsrc.cardbgs["REVERSE"]

            if not self.scale == 100:
                scale = self.scale / 100.0
                image = pygame.transform.rotozoom(image, 0, scale)

            self._image = image

            for i, t in enumerate(self.zoomimgs):
                img, rect = t
                # 最大の一枚のみは長時間表示される
                # 可能性があるためスムージングする
                if i + 1 == len(self.zoomimgs):
                    scale = pygame.transform.smoothscale
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
                self.image = self.cardimg.get_clickedimg(self.get_animerect(), image=self.image)
            else:
                self.image = self.cardimg.get_clickedimg(self.get_animerect())
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
        if self.frame >= len(cw.cwpy.setting.dealing_scales):
            self.deal()
            self.frame = 0
            return

        if self.frame == 0 and hasattr(self, "cardimg") and self.cardimg.is_modifiedfile():
            self.update_image()

        n = cw.cwpy.setting.dealing_scales[::-1][self.frame]
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
        """カードをアニメーショ無しで表示する。"""
        if hasattr(self, "cardimg") and self.cardimg.is_modifiedfile():
            self.update_image()
        self.status = "normal"
        self.image = self.get_animeimage()
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)
        self.rect = pygame.Rect(self.get_animerect())

    def update_hide(self):
        """
        カード非表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(cw.cwpy.setting.dealing_scales):
            self.hide()
            self.frame = 0
            return

        n = cw.cwpy.setting.dealing_scales[self.frame]
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
        """カードをアニメーショ無しで非表示にする。"""
        self.status = "hidden"
        self.clear_image()
        if self.hide_inusecardimg:
            cw.cwpy.clear_inusecardimg(self)

    def update_lateralvibe(self):
        """
        横振動させる。
        """
        n = cw.cwpy.setting.dealspeed * 3
        if self.frame >= n:
            self.rect = pygame.Rect(self.get_animerect())
            self.status = "normal"
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
        n = cw.cwpy.setting.dealspeed * 3
        if self.frame >= n:
            self.rect = pygame.Rect(self.get_animerect())
            if self.image.get_size() <> self.rect.size:
                self.image = pygame.transform.scale(self.get_animeimage(), self.rect.size)
            self.status = "normal"
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
        if self.frame == 0:
            self.zoomimgs.append((self.get_animeimage(), pygame.Rect(self.get_animerect())))

        zoom_w, zoom_h = cw.s(self.zoomsize_noscale)
        maxw = self._rect.w + zoom_w
        maxh = self._rect.h + zoom_h

        if self.old_status == "hidden":
            w = maxw
            h = maxh
        else:
            value = zoom_w / cw.cwpy.setting.dealspeed

            if zoom_w % cw.cwpy.setting.dealspeed:
                value += 1

            w = cw.util.numwrap(self.rect.w + value, 0, maxw)

            value = zoom_h / cw.cwpy.setting.dealspeed

            if zoom_h % cw.cwpy.setting.dealspeed:
                value += 1

            h = cw.util.numwrap(self.rect.h + value, 0, maxh)

        if (w, h) == (maxw, maxh):
            # 最大の一枚のみは長時間表示される
            # 可能性があるためスムージングする
            scale = pygame.transform.smoothscale
        else:
            scale = pygame.transform.scale
        self.image = scale(self.zoomimgs[0][0], (w, h))
        self.rect = pygame.Rect(self.image.get_rect())
        self.rect.center = self.get_animerect().center
        self.zoomimgs.append((self.image, pygame.Rect(self.rect)))
        self.frame += 1

        if (w, h) == (maxw, maxh):
            self.status = self.old_status
            self.frame = 0
            if self.status == "hidden":
                self.clear_image(move=False)

    def update_zoomout(self):
        """
        カードを縮小する。
        """
        if self.old_status == "hidden":
            self.image, self.rect = self.zoomimgs[0]
            self.zoomimgs = []
            self.status = self.old_status
            self.frame = 0
            self.clear_image(move=False)
        else:
            self.image, self.rect = self.zoomimgs.pop()
            self.rect = pygame.Rect(self.rect)
            self.frame += 1

            if not self.zoomimgs:
                self.status = self.old_status
                self.frame = 0

    def update_shiftup(self):
        """下にさげていたカードを上にあげる。"""
        speed = cw.cwpy.setting.dealspeed * 3
        if self.frame == 0:
            self.image = self.get_animeimage()

        shift = int(float(cw.s(150)) / speed * self.frame)
        y = self._rect[1] + cw.s(150) - shift
        if self.zoomimgs:
            y += self.zoomimgs[-1][1][1] - self.zoomimgs[0][1][1]
        self.rect = pygame.Rect(self.rect)
        self.rect.topleft = (self.rect[0], y)
        self.rect.size = self.image.get_size()

        for image, rect in self.zoomimgs:
            if not rect is self.rect:
                rect.center = self.rect.center

        if self.frame == speed:
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
        speed = cw.cwpy.setting.dealspeed * 3

        shift = int(float(cw.s(150)) / speed * self.frame)
        y = self._rect[1] + shift
        self.rect = pygame.Rect(self.rect)
        self.rect.size = self.image.get_size()
        if self.zoomimgs:
            image, zrect = self.zoomimgs[0]
            topleft = (zrect[0], y)
            zrect.topleft = topleft
            for image, rect in self.zoomimgs[1:]:
                rect.center = zrect.center
            self.rect.center = zrect.center
        else:
            topleft = (self.rect[0], y)
            self.rect.topleft = topleft

        if self.frame == speed:
            self.image = pygame.Surface((0, 0)).convert()
            self.status = "hidden"
            self.frame = 0

        else:
            self.frame += 1

    def update_scale(self):
        if not (hasattr(self, "cardimg") and self.cardimg):
            return

        zoom = 0 < len(self.zoomimgs)

        if zoom:
            self.old_status = self.status
            self.status = "zoomout"
            while self.status == "zoomout":
                self.update_zoomout()

        self.cardimg.update_scale()
        self.update_image()
        if self._pos_noscale or self._center_noscale:
            self.set_pos_noscale(self._pos_noscale, self._center_noscale)

        if zoom:
            self.old_status = self.status
            self.status = "zoomin"
            while self.status == "zoomin":
                self.update_zoomin()

        if self.status == "hidden":
            self.clear_image(True)

    def update_image(self):
        """
        画像を再構成する。
        """
        if not self.cardimg:
            return

        # 画像参照
        if hasattr(self, "test_aptitude"):
            self.cardimg.update(self, self.test_aptitude)
        else:
            self.cardimg.update(self)

        image = self.cardimg.get_image()
        rect = self.cardimg.rect

        if not self.scale == 100:
            scale = self.scale / 100.0
            image = pygame.transform.rotozoom(image, 0, scale)
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
                if i + 1 == len(self.zoomimgs)-1:
                    scale = pygame.transform.smoothscale
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

    def clear_image(self, move=True):
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        if move:
            topleft = self.rect.topleft
            self.rect = self.image.get_rect()
            self.rect.topleft = topleft

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

        self.rect.topleft = self._rect.topleft
        if hasattr(self, "cardimg"):
            self.cardimg.rect.topleft = self._rect.topleft

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
    def __init__(self, data, pos_noscale=(0, 0), status="hidden"):
        CWPyCard.__init__(self, status)
        # CWPyElementTreeインスタンス
        self.data = data
        # CharacterCard初期化
        character.Player.__init__(self)
        # カード画像
        path = self.data.gettext("Property/ImagePath", "")
        self.imgpath = cw.util.join_paths(cw.cwpy.yadodir, path)

        # TODO scaleinfo
        self.cardimg = cw.image.CharacterCardImage(self, pos_noscale=pos_noscale)
        self.update_image()
        # 空のイメージ
        self.image = pygame.Surface(cw.s((0, 0))).convert()

        self.set_pos_noscale(pos_noscale)

        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(cw.s(0), cw.s(+150))

        # "：Ｒ"クーポンを所持していたら反転フラグON
        if self.has_coupon(u"：Ｒ"):
            self.reversed = True
            self._reverse()

        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self)

    def set_pos(self, pos=None, center=None):
        CWPyCard.set_pos(self, pos, center)
        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(cw.s(0), cw.s(+150))

    def set_name(self, name):
        character.Player.set_name(self, name)
        self.cardimg.set_nameimg(self.get_name())

    def set_image(self, path):
        character.Player.set_image(self, path)
        self.imgpath = cw.util.join_paths(cw.cwpy.yadodir, self.get_imagepath())
        self.cardimg.set_faceimg(self.imgpath)

    def update_levelup(self):
        """レベルアップ処理。"""
        if self.frame % 5:
            self.image = pygame.Surface((0, 0)).convert()
        elif not self.frame % 5:
            self.image = self.get_animeimage()

            if self.frame == 15:
                self.status = "normal"
                self.cardimg.set_levelimg(self.level)
                self.frame = 0
                return

        self.frame += 1

    def update_delete(self):
        """パーティから外す。"""
        self.update_hide()

        if self.frame == 0:
            cw.cwpy.ydata.party.remove(self)

    def lclick_event(self):
        """左クリックイベント。"""
        if self.reversed:
            self.rclick_event()

        # CARDPOCKETダイアログを開く(通常)
        elif not cw.cwpy.is_curtained():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")

            if cw.cwpy.is_battlestatus():
                if not cw.cwpy.setting.openhandviewalways and self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                elif not cw.cwpy.setting.openhandviewalways and self.is_autoselectedpenalty() and not cw.cwpy.debug:
                    s = cw.cwpy.msgs["selected_penalty"]
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("HANDVIEW")
            else:
                if not cw.cwpy.setting.openhandviewalways and self.is_inactive() and\
                        not cw.cwpy.areaid in cw.AREAS_TRADE:
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
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")

            # USECARDダイアログを開く
            if cw.cwpy.status == "Scenario":
                cw.cwpy.call_modaldlg("USECARD")
            # 戦闘行動を設定する。
            elif cw.cwpy.status == "ScenarioBattle":
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea()

        # パーティ離脱
        elif cw.cwpy.areaid == -3:
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.dissolve_party(self)

        # キャンプ
        elif cw.cwpy.areaid == cw.AREA_CAMP:
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")
        cw.cwpy.call_modaldlg("CHARAINFO")

    def set_level(self, value, regulate=False, debugedit=False, backpack_party=None):
        character.Player.set_level(self, value, regulate, debugedit, backpack_party)
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

        # レベルアップ
        if levelup <> 0:
            base = self.get_specialcoupons()[u"＠レベル原点"]
            if fromscenario:
                n = base + levelup
                if 1 < levelup:
                    # 複数回レベルアップした場合はその分回転表示する
                    cw.animation.animate_sprite(self, "levelup")
                    for i in xrange(levelup - 1):
                        cw.animation.animate_sprite(self, "hide")
                        self.set_level(base + i + 1)
                        cw.animation.animate_sprite(self, "deal")
                    self.set_level(n)
                else:
                    self.set_level(n)
                    cw.animation.animate_sprite(self, "levelup")
            else:
                self.set_level(n)

        # 回復処理
        if fromscenario or levelup <> 0:
            result = True
            cw.cwpy.sounds["harvest"].play(True)
            cw.animation.animate_sprite(self, "hide")
            if fromscenario:
                self.set_fullrecovery()
            self.update_image()
            cw.animation.animate_sprite(self, "deal")

        # レベルアップメッセージ
        if fromscenario and 0 < levelup:
            text = cw.util.encodewrap(cw.cwpy.msgs["level_up"])
            names = [(0, cw.cwpy.msgs["ok"])]
            mwin = cw.sprite.message.MessageWindow(text, names, self.imgpath, self)
            cw.cwpy.show_message(mwin)

        return result

#-------------------------------------------------------------------------------
#　エネミーカードスプライト
#-------------------------------------------------------------------------------

class EnemyCard(CWPyCard, character.Enemy):
    def __init__(self, mcarddata, pos_noscale=(0, 0), status="hidden", addgroup=True):
        CWPyCard.__init__(self, status)
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
            self.initialize()

        if addgroup:
            # spritegroupに追加
            cw.cwpy.mcardgrp.add(self)

    def initialize(self):
        if self._init:
            return

        self._init = True

        # イベントデータ
        self.events = cw.event.EventEngine(self.mcarddata.getfind("Events"))
        # CWPyElementTreeインスタンス
        path = cw.cwpy.sdata.casts[self.mcarddata.getint("Property/Id")][1]
        self.data = cw.data.xml2etree(path, nocache=True)
        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Enemy.__init__(self)
        self.deck.set(self)
        # カード画像
        path = self.data.gettext("Property/ImagePath", "")
        self.imgpath = cw.util.get_materialpath(path, cw.M_IMG)
        # TODO scaleinfo
        self.cardimg = cw.image.CharacterCardImage(self, pos_noscale=self._init_pos_noscale)
        self.set_pos_noscale(pos_noscale=self._init_pos_noscale)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()

    def is_initialized(self):
        return self._init

    def update(self, scr):
        if self.status <> "hidden" and not self._init:
            self.initialize()
        CWPyCard.update(self, scr)

    def update_delete(self):
        self.update_hide()

        if self.frame == 0:
            cw.cwpy.mcardgrp.remove(self)

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        # CARDPOCKETダイアログを開く(通常)
        if (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if cw.cwpy.is_battlestatus():
                if not cw.cwpy.setting.openhandviewalways and self.is_inactive():
                    s = cw.cwpy.msgs["inactive"] % self.name
                    cw.cwpy.call_modaldlg("NOTICE", text=s)
                else:
                    cw.cwpy.call_modaldlg("HANDVIEW")

        # カード使用。戦闘行動を設定する。
        elif cw.cwpy.selectedheader:
            if cw.cwpy.is_battlestatus():
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea()

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　フレンドカードスプライト
#-------------------------------------------------------------------------------

class FriendCard(CWPyCard, character.Friend):
    def __init__(self, castid=None, data=None):
        CWPyCard.__init__(self, "hidden")
        self.zoomsize_noscale = (32, 42)

        if castid:
            # Id
            self.id = castid
            # CWPyElementTreeインスタンス
            path = cw.cwpy.sdata.casts[self.id][1]
            self.data = cw.data.xml2etree(path, nocache=True)
        elif data:
            self.data = data
            self.id = self.data.getint("Property/Id", 1)

        self.fpath = self.data.fpath
        # CharacterCard初期化
        character.Friend.__init__(self)
        self.deck.set(self)
        # カード画像
        path = self.data.gettext("Property/ImagePath", "")
        self.imgpath = cw.util.get_materialpath(path, cw.M_IMG)
        # TODO scaleinfo
        self.cardimg = cw.image.CharacterCardImage(self)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()
        # 付帯以外の召喚獣消去
        self.set_beast(vanish=True)

    def update_delete(self):
        if self in cw.cwpy.sdata.friendcards:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            cw.cwpy.sdata.friendcards.remove(self)

        self.status = "hidden"

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        if (not cw.cwpy.is_curtained() or cw.cwpy.areaid == cw.AREA_CAMP) and self.is_analyzable():
            if not cw.cwpy.is_battlestatus():
                cw.cwpy.call_modaldlg("CARDPOCKET")

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_modaldlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　メニューカードスプライト
#-------------------------------------------------------------------------------

class MenuCard(CWPyCard):
    def __init__(self, data, pos_noscale=(0, 0), status="hidden", addgroup=True):
        """
        メニューカード用のスプライトを作成。
        """
        CWPyCard.__init__(self, status)
        # カード情報
        self._data = data
        self._pos_noscale2 = pos_noscale
        self.name = data.gettext("Property/Name", "")
        self.desc = data.gettext("Property/Description", "")
        self.flag = data.gettext("Property/Flag", "")
        self.debug_only = data.getbool(".", "debugOnly", False)
        self.author = ""
        self.scenario = ""

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

        if addgroup:
            # spritegroupに追加
            cw.cwpy.mcardgrp.add(self)

    def initialize(self):
        if self._init:
            return

        self._init = True

        # イベント
        self.events = cw.event.EventEngine(self._data.getfind("Events"))

        # 通常イメージ。LargeMenuCardはサイズ大のメニューカード作成。
        path = self._data.gettext("Property/ImagePath", "")
        pcn = ""
        if not path:
            pcn = self._data.gettext("Property/PCNumber", "")
        if pcn:
            # メニューカードにPCの画像を表示(1.30)
            pcards = cw.cwpy.ydata.party.members
            pi = int(pcn) - 1
            if pi < len(pcards):
                path = pcards[pi].gettext("Property/ImagePath", "")
                if path:
                    path = cw.util.join_yadodir(path)
        elif path:
            path = cw.util.get_materialpath(path, cw.M_IMG, system=cw.cwpy.areaid < 0)

        if self._data.tag == "LargeMenuCard":
            # TODO scaleinfo
            self._cardimg = cw.image.LargeCardImage(path, "NORMAL", self.name)
        else:
            # TODO scaleinfo
            self._cardimg = cw.image.CardImage(path, "NORMAL", self.name)

        self.update_image()
        # pos
        self.set_pos_noscale(self._pos_noscale2)

        # 初期化後は不要
        self._data = None
        self._pos_noscale2 = None

    @property
    def cardimg(self):
        if not self._init:
            self.initialize()
        return self._cardimg

    def is_initialized(self):
        return self._init

    def update(self, scr):
        if self.status <> "hidden" and not self._init:
            self.initialize()
        CWPyCard.update(self, scr)

    def lclick_event(self):
        """左クリックイベント。"""
        # 通常のクリックイベント
        if not cw.cwpy.is_curtained():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)

        # カード移動操作
        elif cw.cwpy.areaid in (-1, -2, -5) and cw.cwpy.selectedheader:
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)

        # カード使用イベント
        elif cw.cwpy.selectedheader:
            cw.cwpy.sounds["click"].play()
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
                cw.cwpy.sounds["page"].play()
            else:
                cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)

    def rclick_event(self):
        """右クリックイベント。"""
        if not cw.cwpy.is_showingdlg():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            if self.desc:
                cw.cwpy.call_modaldlg("MENUCARDINFO")

def main():
    pass

if __name__ == "__main__":
    main()
