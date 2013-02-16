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
        self.old_status = status
        self.rect = pygame.Rect(0, 0, 0, 0)
        # アニメ用フレーム数
        self.frame = 0
        # ズーム画像のリスト。(Surfaice, Rect)のタプル。
        self.zoomimgs = []
        self.zoomsize = (16, 21)
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

    def get_unselectedimage(self):
        return self._image

    def get_selectedimage(self):
        return cw.imageretouch.to_negative_for_card(self._image)

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        self.update_selection()

    def update_delete(self):
        pass

    def update_reversed(self):
        pass

    def update_hidden(self):
        pass

    def update_reverse(self):
        """
        カードをひっくり返す。
        """
        self.update_hide()

        if self.status == "hidden":
            cw.cwpy.draw()
            cw.cwpy.tick_clock()
            self.reversed = not self.reversed

            # 表←→裏の画像切り替え
            if self.reversed:
                image = cw.cwpy.rsrc.cardbgs["REVERSE"]

                if not self.scale == 100:
                    image = pygame.transform.rotozoom(image, 0, scale)

                self._image = image
            else:
                self.update_image()

            cw.animation.animate_sprite(self, "deal")

            if self.reversed:
                self.status = "reversed"

    def update_click(self):
        """
        クリック時のアニメーションを呼び出すメソッド。
        """
        if self.frame == 0:
            self.image = self.cardimg.get_clickedimg(self._rect)
            self.rect = self.image.get_rect(center=self._rect.center)
            self.status = "click"
        elif self.frame == 3:
            self.status = "normal"
            self.image = self.get_selectedimage()
            self.rect = pygame.Rect(self._rect)
            self.frame = 0
            return

        self.frame += 1

    def update_deal(self):
        """
        カード表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(cw.cwpy.setting.dealing_scales):
            self.status = "normal"
            self.image = self._image
            self.rect = pygame.Rect(self._rect)
            self.frame = 0
            return

        n = cw.cwpy.setting.dealing_scales[::-1][self.frame]
        size = self._rect.w * n / 100, self._rect.h
        self.image = pygame.transform.scale(self._image, size)
        self.rect = self.image.get_rect(center=self._rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def update_hide(self):
        """
        カード非表示時のアニメーションを呼び出すメソッド。
        """
        if self.frame >= len(cw.cwpy.setting.dealing_scales):
            self.status = "hidden"
            self.clear_image()
            self.frame = 0
            return

        n = cw.cwpy.setting.dealing_scales[self.frame]
        size = self._rect.w * n / 100, self._rect.h
        self.image = pygame.transform.scale(self._image, size)
        self.rect = self.image.get_rect(center=self.rect.center)
        if self.highspeed:
            self.frame += 2
        else:
            self.frame += 1

    def update_lateralvibe(self):
        """
        横振動させる。
        """
        if self.frame == 12:
            self.rect = pygame.Rect(self._rect)
            self.status = "normal"
            self.frame = 0
            return

        if self.frame % 2 == 0:
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(5, 0)
            self.frame += 1
        else:
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(-5, 0)
            self.frame += 1

    def update_axialvibe(self):
        """
        縦振動させる。
        """
        if self.frame == 12:
            self.rect = pygame.Rect(self._rect)
            self.status = "normal"
            self.frame = 0
            return

        if self.frame % 2 == 0:
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(0, 5)
            self.frame += 1
        else:
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(0, -5)
            self.frame += 1

    def update_zoomin(self):
        """
        カードを拡大する。
        """
        if self.frame == 0:
            self.zoomimgs.append((self._image, pygame.Rect(self._rect)))

        zoom_w, zoom_h = self.zoomsize
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

        self.image = pygame.transform.scale(self.zoomimgs[0][0], (w, h))
        self.rect = pygame.Rect(self.image.get_rect())
        self.rect.center = self._rect.center
        self.zoomimgs.append((self.image, pygame.Rect(self.rect)))
        self.frame += 1

        if (w, h) == (maxw, maxh):
            self.status = self.old_status
            self.frame = 0

    def update_zoomout(self):
        """
        カードを縮小する。
        """
        if self.old_status == "hidden":
            self.image, self.rect = self.zoomimgs[0]
            self.zoomimgs = []
        else:
            self.image, self.rect = self.zoomimgs.pop()
            self.rect = pygame.Rect(self.rect)
            self.frame += 1

        if not self.zoomimgs:
            self.status = self.old_status
            self.frame = 0

    def update_image(self):
        """
        画像を再構成する。
        """
        # 画像参照
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
            self.image = self._image = image

        self.rect.size = rect.size
        self._rect = pygame.Rect(self.rect)
        self._rect.topleft = rect.topleft

        # ズーム画像も更新
        if self.zoomimgs:
            self.rect.size = self.zoomimgs[0][1].size
            self._rect = pygame.Rect(self.rect)
            self._rect.topleft = rect.topleft
            self.zoomimgs = []
            self.update_zoomin()

            while not self.frame == 0:
                self.update_zoomin()

    def clear_image(self):
        self.image = pygame.Surface((0, 0)).convert()
        self.rect = self.image.get_rect(center=self._rect.center)

    def set_pos(self, pos=None, center=None):
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
    def __init__(self, data, pos=(0, 0), status="hidden"):
        CWPyCard.__init__(self, status)
        # CWPyElementTreeインスタンス
        self.data = data
        # CharacterCard初期化
        character.Player.__init__(self)
        # カード画像
        path = self.data.gettext("Property/ImagePath", "")
        self.imgpath = cw.util.join_yadodir(path)

        self.cardimg = cw.image.CharacterCardImage(self, pos)
        self.update_image()
        # 空のイメージ
        self.image = pygame.Surface((0, 0)).convert()

        if self.status == "hidden":
            self.rect = pygame.Rect(self._rect)
            self.rect.move_ip(0, +150)

        # "：Ｒ"クーポンを所持していたら反転フラグON
        if self.has_coupon(u"：Ｒ"):
            self.reversed = True

        # spritegroupに追加
        cw.cwpy.pcardgrp.add(self)

    def set_name(self, name):
        character.Player.set_name(self, name)
        self.cardimg.set_nameimg(self.get_name())

    def set_image(self, path):
        character.Player.set_image(self, path)
        self.imgpath = cw.util.join_yadodir(self.get_imagepath())
        self.cardimg.set_faceimg(self.imgpath)

    def update_levelup(self):
        """レベルアップ処理。"""
        if self.frame % 5:
            self.image = pygame.Surface((0, 0)).convert()
        elif not self.frame % 5:
            self.image = self._image

            if self.frame == 15:
                self.status = "normal"
                self.cardimg.set_levelimg(self.level)
                self.update_image()
                self.frame = 0
                return

        self.frame += 1

    def update_delete(self):
        """パーティから外す。"""
        self.update_hide()

        if self.frame == 0:
            cw.cwpy.ydata.party.remove(self)

    def update_shiftup(self):
        """下にさげていたカードを上にあげる。"""
        speed = cw.cwpy.setting.dealspeed * 3
        if self.frame == 0:
            if self.is_reversed():
                self.image = cw.cwpy.rsrc.cardbgs["REVERSE"]
            else:
                self.image = self._image

        shift = int(150.0 / speed * self.frame)
        y = self._rect[1] + 150 - shift
        self.rect = pygame.Rect(self.rect)
        self.rect.topleft = (self.rect[0], y)

        for image, rect in self.zoomimgs:
            if not rect is self.rect:
                rect.center = self.rect.center

        if self.frame == speed:
            if self.is_reversed():
                self.status = "reversed"
            else:
                self.status = "normal"

            self.rect.topleft = self._rect.topleft
            self.frame = 0

        else:
            self.frame += 1

    def update_shiftdown(self):
        """上にあげていたカードを下にさげる。"""
        speed = cw.cwpy.setting.dealspeed * 3

        shift = int(150.0 / speed * self.frame)
        y = self._rect[1] + shift
        self.rect = pygame.Rect(self.rect)
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

    def lclick_event(self):
        """左クリックイベント。"""
        # CARDPOCKETダイアログを開く(通常)
        if not cw.cwpy.is_curtained():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")

            if cw.cwpy.is_battlestatus():
                cw.cwpy.call_dlg("HANDVIEW")
            else:
                cw.cwpy.call_dlg("CARDPOCKET")

        # カード使用。USECARDダイアログを開く
        elif cw.cwpy.selectedheader:
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")

            # USECARDダイアログを開く
            if cw.cwpy.status == "Scenario":
                cw.cwpy.call_dlg("USECARD")
            # 戦闘行動を設定する。
            elif cw.cwpy.status == "ScenarioBattle":
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea()

        # カード移動操作
        elif cw.cwpy.areaid in (-1, -2, -5):
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.trade("PLAYERCARD", self)
        # パーティ離脱
        elif cw.cwpy.areaid == -3:
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.dissolve_party(self)

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")
        cw.cwpy.call_dlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　エネミーカードスプライト
#-------------------------------------------------------------------------------

class EnemyCard(CWPyCard, character.Enemy):
    def __init__(self, mcarddata, pos=(0, 0), status="hidden"):
        CWPyCard.__init__(self, status)
        self.mcarddata = mcarddata
        self._init_pos = pos
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
            self._rect = pygame.Rect(0, 0, 0, 0)
            self.clear_image()
        else:
            self.initialize()

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
        if cw.binary.image.path_is_code(path):
            self.imgpath = path
        else:
            self.imgpath = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
        self.cardimg = cw.image.CharacterCardImage(self, self._init_pos)
        self.update_image()
        # 空のイメージ
        self.clear_image()
        # 精神力回復
        self.set_skillpower()

    def update(self, scr):
        if not self._init:
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
        if not cw.cwpy.is_curtained() and self.is_analyzable():
            if cw.cwpy.is_battlestatus():
                cw.cwpy.call_dlg("HANDVIEW")

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
            cw.cwpy.call_dlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　フレンドカードスプライト
#-------------------------------------------------------------------------------

class FriendCard(CWPyCard, character.Friend):
    def __init__(self, castid=None, data=None):
        CWPyCard.__init__(self, "hidden")
        self.zoomsize = (32, 42)

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
        if cw.binary.image.path_is_code(path):
            self.imgpath = path
        else:
            self.imgpath = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
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
            cw.cwpy.sdata.friendcards.remove(self)

        self.status = "hidden"

    def lclick_event(self):
        """左クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        if not cw.cwpy.is_curtained() and self.is_analyzable():
            if not cw.cwpy.is_battlestatus():
                cw.cwpy.call_dlg("CARDPOCKET")

    def rclick_event(self):
        """右クリックイベント。"""
        cw.cwpy.sounds["click"].play()
        cw.animation.animate_sprite(self, "click")

        if self.is_analyzable():
            cw.cwpy.call_dlg("CHARAINFO")

#-------------------------------------------------------------------------------
#　メニューカードスプライト
#-------------------------------------------------------------------------------

class MenuCard(CWPyCard):
    def __init__(self, data, pos=(0, 0), status="hidden"):
        """
        メニューカード用のスプライトを作成。
        """
        CWPyCard.__init__(self, status)
        # カード情報
        self.name = data.gettext("Property/Name", "")
        self.desc = data.gettext("Property/Description", "")
        self.flag = data.gettext("Property/Flag", "")
        self.events = cw.event.EventEngine(data.getfind("Events"))
        self.author = ""
        self.scenario = ""

        # スケール
        if cw.cwpy.is_autospread():
            self.scale = 100
        else:
            s = data.getattr("Property/Size", "scale", "100%")
            self.scale = int(s.rstrip("%"))

        # 通常イメージ。LargeMenuCardはサイズ大のメニューカード作成。
        path = data.gettext("Property/ImagePath", "")

        if path and not cw.binary.image.path_is_code(path):
            if cw.cwpy.is_playingscenario() and not cw.cwpy.areaid < 0:
                path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
            else:
                path = cw.util.join_paths(cw.cwpy.skindir, path)

        if data.tag == "LargeMenuCard":
            self.cardimg = cw.image.LargeCardImage(path, "NORMAL", self.name)
        else:
            self.cardimg = cw.image.CardImage(path, "NORMAL", self.name)

        self.update_image()
        # pos
        self.set_pos(pos)

        # 空のイメージ
        if self.status == "hidden":
            self.clear_image()

        # spritegroupに追加
        cw.cwpy.mcardgrp.add(self)

    def lclick_event(self):
        """左クリックイベント。"""
        # 通常のクリックイベント
        if not cw.cwpy.is_curtained():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)
        # カード使用イベント
        elif cw.cwpy.selectedheader:
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")

            # USECARDダイアログを開く
            if cw.cwpy.status == "Scenario":
                cw.cwpy.call_dlg("USECARD")
            # 戦闘行動を設定する
            elif cw.cwpy.status == "ScenarioBattle":
                header = cw.cwpy.selectedheader
                header.get_owner().set_action(self, header)
                cw.cwpy.clear_specialarea()

        # カード移動操作
        elif cw.cwpy.areaid in (-1, -2, -5):
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)
        # パーティ解散
        elif cw.cwpy.areaid == -3:
            cw.cwpy.sounds["page"].play()
            cw.animation.animate_sprite(self, "click")
            self.events.start(keynum=1)

    def rclick_event(self):
        """右クリックイベント。"""
        if not cw.cwpy.is_showingdlg():
            cw.cwpy.sounds["click"].play()
            cw.animation.animate_sprite(self, "click")
            cw.cwpy.call_dlg("MENUCARDINFO")

def main():
    pass

if __name__ == "__main__":
    main()
