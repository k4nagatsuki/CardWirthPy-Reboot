#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import pygame
from pygame.locals import *

import cw
import base


class MessageWindow(base.CWPySprite):
    def __init__(self, text, names, path="", talker=None,
                 pos_noscale=None, size_noscale=None, talkerimage=None,
                 nametable={}, namesubtable={}, flagtable={}, steptable={},
                 backlog=False, result=None, versionhint="", specialchars=None):
        base.CWPySprite.__init__(self)
        if pos_noscale is None:
            pos_noscale = (81, 50)
        if size_noscale is None:
            size_noscale = (470, 180)

        self.backlog = backlog
        self._barspchr = True

        self.name_table = nametable
        self.name_subtable = namesubtable
        self.flag_table = flagtable
        self.step_table = steptable
        self.specialchars = specialchars

        # メッセージの選択結果
        self.result = result
        # data
        self.names = names
        self.path = path
        self.text = text

        # 話者(CardHeader or Character)
        self.talker = talker

        self.backlog_versionhint = versionhint
        self.versionhint = None
        if not self.backlog and self.talker and cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_MESSAGE, talker.versionhint)

        if not self.backlog:
            self.versionhint = cw.cwpy.sdata.get_versionhint(cw.HINT_MESSAGE)

        if not self.name_table:
            self.name_table = _create_nametable(True, self.talker)
        if not self.name_subtable:
            self.name_subtable = _create_nametable(False, self.talker)

        self.talker_image_noscale = talkerimage
        self._init_style()
        self._init_image(size_noscale, pos_noscale)

        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs()
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed
        # SelectionBarインスタンスリスト
        self.selections = []
        self.selection_pos = cw.s((81, 230))
        # frame
        self.frame = 0
        if not self.backlog:
            # cwpylist, indexクリア
            cw.cwpy.list = []
            cw.cwpy.index = -1

        # スピードが0かバックログの場合、最初から全て描画
        if self.speed == 0 or self.backlog:
            self.speed = 1
            self.draw_all()

        # spritegroupに追加
        if self.backlog:
            cw.cwpy.backloggrp.add(self, layer="backlog")
        else:
            cw.cwpy.topgrp.add(self, layer="message")

    def _init_style(self):
        # クラシックスタイルか
        self.classicstyletext = cw.UP_SCR == 1 and cw.cwpy.setting.classicstyletext and "message_classic" in cw.cwpy.rsrc.fonts

    def _init_image(self, size_noscale, pos_noscale):
        # image
        self.image = pygame.Surface(cw.s(size_noscale)).convert_alpha()
        if self.backlog:
            self.image.fill(cw.cwpy.setting.blwincolour)
        else:
            self.image.fill(cw.cwpy.setting.mwincolour)
        # rect
        self.rect_noscale = pygame.Rect(pos_noscale, size_noscale)
        self.rect = cw.s(self.rect_noscale)
        # 外枠描画
        draw_frame(self.image, cw.s(size_noscale), cw.s((0, 0)), self.backlog)
        # 話者画像
        if self.talker_image_noscale:
            self.talker_image = cw.s(self.talker_image_noscale)
        elif self.path:
            path = self.path
            if not cw.binary.image.path_is_code(self.path):
                lpath = path.lower()
                if lpath.startswith(cw.cwpy.yadodir.lower()) or\
                        lpath.startswith(cw.cwpy.tempdir.lower()):
                    path = cw.util.get_yadofilepath(path)
            self.talker_image_noscale = cw.util.load_image(path, True)
            if self.talker_image_noscale and self.talker_image_noscale.get_width():
                # TODO scaleinfo
                self.talker_image = cw.s((self.talker_image_noscale, cw.SIZE_CARDIMAGE))
            else:
                self.talker_image_noscale = None
                self.talker_image = None
        else:
            self.talker_image_noscale = None
            self.talker_image = None

        if self.talker_image:
            y = (self.rect.height - self.talker_image.get_height()) / 2
            self.image.blit(self.talker_image, (cw.s(15), y))

        self._fore = pygame.Surface(cw.s(size_noscale)).convert_alpha()
        self._fore.fill((0, 0, 0, 0))
        self._back = self.image.copy()

    def update_scale(self):
        self._init_style()
        self._init_image(self.rect_noscale.size, self.rect_noscale.topleft)
        self.charimgs = self.create_charimgs()
        if self.backlog:
            cw.cwpy.backloggrp.remove_sprites_of_layer("backlogbar")
        else:
            cw.cwpy.topgrp.remove_sprites_of_layer("selectionbar")
        self.selections = []
        self.selection_pos = cw.s((81, 230))

        self.is_drawing = True
        self.frame = 0
        self.draw_all()

    def update(self, scr):
        if self.is_drawing:
            self.draw_char()    # テキスト描画

    def draw_all(self):
        while self.is_drawing:
            self.draw_char()

    def draw_char(self):
        if self.speed and self.frame % self.speed:
            self.frame += 1
            return

        font = cw.cwpy.rsrc.fonts["message"]
        lineheight = font.get_height()
        chridx = self.frame / self.speed
        sbold = (not cw.cwpy.setting.classicstyletext or\
                 not "message_classic" in cw.cwpy.rsrc.fonts) and\
                lineheight <= 24
        if chridx < len(self.charimgs):
            pos, txtimg, txtimg2 = self.charimgs[chridx]

            # 通常のテキスト描画
            if txtimg2:
                for x in xrange(pos[0]-1, pos[0]+2):
                    for y in xrange(pos[1]-1, pos[1]+2):
                        self._back.blit(txtimg2, (x, y))
                        if sbold:
                            self._back.blit(txtimg2, (x+1, y))

            self._fore.blit(txtimg, pos)
            if sbold:
                self._fore.blit(txtimg, (pos[0]+1, pos[1]))

            size = txtimg.get_size()
            area = pygame.Rect(pos[0]-1, pos[1]-1, size[0]+3, size[1]+2)
            self.image.fill((0, 0, 0, 0), rect=area)
            self.image.blit(self._back, area, area)
            self.image.blit(self._fore, area, area)
            self.frame += 1
        else:
            self.is_drawing = False
            cw.cwpy.has_inputevent = True
            self.frame = 0

            # SelectionBarを描画
            if not self.backlog:
                cw.cwpy.list = self.selections
            x, y = self.selection_pos

            for index, name in enumerate(self.names):
                # 互換動作: 1.30以前は選択肢に特殊文字を使用しない
                if not self.backlog and self._barspchr and not cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
                    name = (name[0], self.rpl_specialstr(False, name[1], self.name_subtable))
                pos = (x, cw.s(25) * index + y)
                selected = 1 < len(self.names) and self.backlog and self.result == index
                sbar = SelectionBar(name, pos, backlog=self.backlog, selected=selected)
                self.selections.append(sbar)
                sbar.update()

    def create_charimgs(self, pos=None):
        if pos is None:
            pos = cw.s((14, 12))
        if self.talker_image:
            if not self.backlog:
                self.text = self.rpl_specialstr(True, self.text)
                self.text = cw.util.txtwrap(self.text, 2)
            # 互換動作: 1.28以前は話者画像のサイズによって本文の位置がずれる
            if self.backlog:
                versionhint = self.backlog_versionhint
            else:
                versionhint = cw.cwpy.sdata.get_versionhint(cw.HINT_MESSAGE)
            if cw.cwpy.sct.lessthan("1.28", versionhint):
                w = self.talker_image.get_width()
            else:
                w = cw.s(74)
            posp = pos = pos[0] + cw.s(26) + w, pos[1]
        else:
            if not self.backlog:
                self.text = self.rpl_specialstr(True, self.text)
                self.text = cw.util.txtwrap(self.text, 3)
            posp = pos

        r_halfwidth = re.compile(u"[ -~｡-ﾟ]") # 半角文字の集合
        r_specialfont = re.compile("#.") # 特殊文字(#)の集合
        # 文字色変更文字(&)の集合
        r_changecolour = re.compile("&[\x20-\x7E\n]")
        # フォントデータ
        if self.classicstyletext:
            font = cw.cwpy.rsrc.fonts["message_classic"]
        else:
            font = cw.cwpy.rsrc.fonts["message"]
        colour = (255, 255, 255)
        lineheight = font.get_height() - 1
        # 各種変数
        cnt = 0
        skip = False
        images = []

        # 左右接続のために伸ばす文字
        r_join = re.compile(u"[―─＿￣]")

        for index, char in enumerate(self.text):
            # 改行処理
            if char == "\n":
                cnt += 1
                pos = posp[0], lineheight * cnt + posp[1]

                # 8行以下の文字列は表示しない
                if cnt > 6:
                    break
                else:
                    continue

            # 特殊文字を使った後は一文字スキップする
            elif skip:
                skip = False
                continue

            chars = "".join(self.text[index:index+2]).lower()

            # 特殊文字
            if r_specialfont.match(chars):
                specialchars = self.specialchars if self.specialchars else cw.cwpy.rsrc.specialchars
                if chars in specialchars:
                    charimg, userfont = specialchars[chars]

                    if userfont:
                        # TODO scaleinfo
                        images.append((pos, cw.s(charimg), None))
                        pos = pos[0] + cw.s(20), pos[1]
                        skip = True
                        continue

                    size = charimg.get_size()
                    image = pygame.Surface(size).convert()
                    image.fill(colour)
                    image.blit(charimg, (0, 0))
                    image.set_colorkey(image.get_at((0, 0)), RLEACCEL)
                    images.append((pos, cw.s((image, cw.setting.SIZE_SPFONT)), None))
                    pos = pos[0] + cw.s(20), pos[1]
                    skip = True
                    continue

            # 文字色変更
            elif r_changecolour.match(chars):
                colour = self.get_fontcolour(chars[1])
                if chars[1] <> '\n':
                    skip = True
                continue

            # 通常文字
            if self.classicstyletext:
                # クラシック形式
                image = font.render(char, False, colour)
                image2 = font.render(char, False, (0, 0, 0))

            else:
                # CardWirthPy形式
                image = font.render(char, True, colour)
                image2 = font.render(char, True, (0, 0, 0))

                # u"―"の場合、左右の線が繋がるように補完する
                if r_join.match(char):
                    rect = image.get_rect()
                    size = (rect.w + cw.s(20), rect.h)
                    image = pygame.transform.scale(image, size)
                    image2 = pygame.transform.scale(image2, size)
                    image = image.subsurface((10, 0, rect.w, rect.h))
                    image2 = image2.subsurface((10, 0, rect.w, rect.h))

            images.append((pos, image, image2))

            # 半角文字だったら文字幅は半分にする
            if r_halfwidth.match(char):
                pos = pos[0] + cw.s(10), pos[1]
            else:
                pos = pos[0] + cw.s(20), pos[1]

        return images

    def rpl_specialstr(self, full, s, nametable=None):
        """
        特殊文字列(#, $)を置換した文字列を返す。
        """
        if not nametable:
            nametable = self.name_table
        return _rpl_specialstr(full, s, nametable, self.get_stepvalue, self.get_flagvalue)

    def get_stepvalue(self, key):
        if self.backlog:
            if key in self.step_table:
                return self.step_table[key]
            else:
                return ""

        if key in cw.cwpy.sdata.steps:
            s = cw.cwpy.sdata.steps[key].get_valuename()
        else:
            s = ""

        self.step_table[key] = s
        return s

    def get_flagvalue(self, key):
        if self.backlog:
            if key in self.flag_table:
                return self.flag_table[key]
            else:
                return ""

        if key in cw.cwpy.sdata.flags:
            s = cw.cwpy.sdata.flags[key].get_valuename()
        else:
            s = ""

        self.flag_table[key] = s
        return s

    def get_fontcolour(self, s):
        """引数の文字列からフォントカラーを返す。"""
        if s == "r":
            return (255,   0,   0)
        elif s == "g":
            return (  0, 255,   0)
        elif s == "b":
            return (  0, 255, 255)
        elif s == "y":
            return (255, 255,   0)
        elif s == "w":
            return (255, 255, 255)

        # 互換動作: 1.30以前はO,P,L,Dの各色が無い
        if not cw.cwpy.sct.lessthan("1.50", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
            if s == "o": # 1.50
                return (255, 165, 0)
            elif s == "p": # 1.50
                return (204, 136, 255)
            elif s == "l": # 1.50
                return (169, 169, 169)
            elif s == "d": # 1.50
                return (105, 105, 105)

        return (255, 255, 255)

class SelectWindow(MessageWindow):
    def __init__(self, names, text="", pos_noscale=None, size_noscale=None,
                 backlog=False, result=None):
        base.CWPySprite.__init__(self)
        if pos_noscale is None:
            pos_noscale = (81, 50)
        if size_noscale is None:
            size_noscale = (470, 38)

        self.backlog = backlog
        self._barspchr = False
        self.name_table = {}
        self.name_subtable = {}
        self.flag_table = {}
        self.step_table = {}
        self.talker_image = None
        self.versionhint = None
        self.backlog_versionhint = None

        self._init_style()

        # メッセージの選択結果
        self.result = result
        # data
        self.names = names
        self.path = ""
        self.text = cw.cwpy.msgs["select_message"] if not text else text
        self.talker = None
        self._init_image(size_noscale, pos_noscale)
        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs(cw.s((15, 9)))
        # frame
        self.frame = 0
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed or 1
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # SelectionBarインスタンスリスト
        self.selections = []
        self.selection_pos = cw.s((81, 88))
        # メッセージ全て表示
        self.draw_all()
        # spritegroupに追加
        if self.backlog:
            cw.cwpy.backloggrp.add(self, layer="backlog")
        else:
            cw.cwpy.topgrp.add(self, layer="message")

    def _init_image(self, size_noscale, pos_noscale):
        # image
        if self.backlog:
            colour = cw.cwpy.setting.blwincolour
        else:
            colour = cw.cwpy.setting.mwincolour
        self.image = pygame.Surface(cw.s(size_noscale)).convert_alpha()
        self.image.fill(colour)
        # rect
        self.rect_noscale = pygame.Rect(pos_noscale, size_noscale)
        self.rect = cw.s(self.rect_noscale)
        # 外枠描画
        draw_frame(self.image, cw.s(size_noscale), cw.s((0, 0)), self.backlog)

        self._fore = pygame.Surface(cw.s(size_noscale)).convert_alpha()
        self._fore.fill((0, 0, 0, 0))
        self._back = self.image.copy()

    def update_scale(self):
        self._init_style()
        self._init_image(self.rect_noscale.size, self.rect_noscale.topleft)
        self.charimgs = self.create_charimgs()
        if self.backlog:
            cw.cwpy.backloggrp.remove_sprites_of_layer("backlogbar")
        else:
            cw.cwpy.topgrp.remove_sprites_of_layer("selectionbar")
        self.selections = []
        self.selection_pos = cw.s((81, 88))

        self.is_drawing = True
        self.frame = 0
        self.draw_all()

    def update(self, scr):
        pass

class MemberSelectWindow(SelectWindow):
    def __init__(self, pcards, pos_noscale=None, size_noscale=None):
        if pos_noscale is None:
            pos_noscale = (81, 50)
        if size_noscale is None:
            size_noscale = (470, 38)
        self.selectmembers = pcards
        names = [(index, pcard.name)
                        for index, pcard in enumerate(self.selectmembers)]
        names.append((len(names), cw.cwpy.msgs["cancel"]))
        text = cw.cwpy.msgs["select_member_message"]
        SelectWindow.__init__(self, names, text, pos_noscale, size_noscale)

class SelectionBar(base.SelectableSprite):
    def __init__(self, name, pos, backlog=False, selected=False):
        base.SelectableSprite.__init__(self)
        self._selectable_on_event = True
        # 各種データ
        self.backlog = backlog
        self.selected = selected
        self.index = name[0]
        self.name = name[1]
        # 通常画像
        size = cw.s((470, 25))
        self._image = self.get_image(size)
        # rect
        self.rect = self._image.get_rect()
        self.rect.topleft = pos
        # image
        self.image = self._image
        # status
        self.status = "normal"
        # frame
        self.frame = 0
        # spritegroupに追加
        if self.backlog:
            cw.cwpy.backloggrp.add(self, layer="backlogbar")
        else:
            cw.cwpy.topgrp.add(self, layer="selectionbar")

    def get_unselectedimage(self):
        return self._image

    def get_selectedimage(self):
        return cw.imageretouch.to_negative(self._image)

    def update_scale(self):
        pass # MessageWindowのupdate_scaleでremoveされる

    def update(self, scr=None):
        if self.backlog:
            return

        if self.status == "normal":       # 通常表示
            self.update_selection()

            if cw.cwpy.selection == self:
                cw.cwpy.index = cw.cwpy.list.index(self)

        elif self.status == "click":     # 左クリック時
            self.update_click()

    def update_click(self):
        """
        左クリック時のアニメーションを呼び出すメソッド。
        軽く下に押すアニメーション。
        """
        if self.frame == 0:
            self.rect.move_ip(cw.s(0), cw.s(+1))
            self.status = "click"
        elif self.frame == 6:
            self.status = "normal"
            self.rect.move_ip(cw.s(0), cw.s(-1))
            self.frame = 0
            return

        self.frame += 1

    def get_image(self, size):
        image = pygame.Surface(size).convert_alpha()
        if self.backlog:
            colour = cw.cwpy.setting.blwincolour
        else:
            colour = cw.cwpy.setting.mwincolour
        image.fill(colour)
        # 外枠描画
        draw_frame(image, size, pos=cw.s((0, 0)), backlog=self.backlog)
        # 選択肢描画
        font = cw.cwpy.rsrc.fonts["selectionbar"]
        nameimg = font.render(self.name, True, (255, 255, 255))
        nameimg2 = font.render(self.name, True, (0, 0, 0))
        w = size[0] - cw.s(10)
        if w < nameimg.get_width():
            nameimg = pygame.transform.smoothscale(nameimg, (w, nameimg.get_height()))
            nameimg2 = pygame.transform.smoothscale(nameimg2, (w, nameimg2.get_height()))
        w, h = nameimg.get_size()
        pos = (cw.s(470)-w)/2, (cw.s(25)-h)/2
        image.blit(nameimg2, (pos[0]+1, pos[1]))
        image.blit(nameimg2, (pos[0]-1, pos[1]))
        image.blit(nameimg2, (pos[0], pos[1]+1))
        image.blit(nameimg2, (pos[0], pos[1]-1))
        image.blit(nameimg, pos)
        if self.selected:

            image = cw.imageretouch.to_negative(image)
        return image

    def lclick_event(self, skip=False):
        """
        メッセージ選択肢のクリックイベント。
        """
        if self.backlog:
            return

        mwin = cw.cwpy.get_messagewindow()
        if not mwin:
            return

        cw.cwpy.sounds["click"].play(True)

        # クリックした時だけ、軽く下に押されるアニメーションを行う
        if not skip:
            cw.animation.animate_sprite(self, "click")

        # イベント再開(次コンテントへのIndexを渡す)
        if isinstance(mwin, MemberSelectWindow):
            # キャンセルをクリックした場合
            if len(mwin.selectmembers) == self.index:
                mwin.result = 1
            # メンバ名をクリックした場合、選択メンバを変更して、イベント続行
            else:
                pcard = mwin.selectmembers[self.index]
                cw.cwpy.event.set_selectedmember(pcard)
                mwin.result = 0

        else:
            mwin.result = self.index

class BacklogData:
    def __init__(self, base):
        """バックログ表示用のデータ。
        """
        if isinstance(base, SelectWindow):
            self.type = 1
        else:
            self.type = 0
        self.text = base.text
        self.names = base.names
        self.path = base.path
        lpath = self.path.lower()
        if lpath.startswith("yado") or lpath.startswith("data/temp"):
            self.talker_image = base.talker_image_noscale
        else:
            self.talker_image = None
        self.rect_noscale = base.rect_noscale
        self.name_table = base.name_table
        self.name_subtable = base.name_subtable
        self.flag_table = base.flag_table
        self.step_table = base.step_table
        self.result = base.result
        self.versionhint = base.versionhint
        self.specialchars = cw.cwpy.rsrc.specialchars.copy()

    def create_message(self):
        if self.type == 0:
            return MessageWindow(self.text, self.names, self.path, None,
                                 self.rect_noscale.topleft, self.rect_noscale.size,
                                 self.talker_image,
                                 self.name_table, self.name_subtable, self.flag_table, self.step_table,
                                 True, self.result, self.versionhint, self.specialchars)
        else:
            return SelectWindow(self.names, self.text, self.rect_noscale.topleft, self.rect_noscale.size,
                                True, self.result)

class BacklogCurtain(base.CWPySprite):
    def __init__(self, spritegrp, color=None):
        """バックログ用の半透明黒背景スプライト。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        alpha: 透明度。
        """
        base.CWPySprite.__init__(self)
        if color:
            self.color = color
        else:
            self.color = cw.cwpy.setting.blcurtaincolour
        self.image = pygame.Surface(cw.s((632, 420))).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 0))
        # spritegroupに追加
        spritegrp.add(self, layer=0)

    def update_scale(self):
        self.image = pygame.Surface(cw.s((632, 420))).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s((0, 0))

class BacklogPage(base.CWPySprite):
    def __init__(self, page, max, spritegrp):
        """バックログの何ページ目を見ているかを表示するスプライト。
        page: 現在見ているページ。
        max: ページの最大数。
        spritegrp: 登録するSpriteGroup。"backlogpage"レイヤに追加される。
        """
        base.CWPySprite.__init__(self)
        self.update_page(page, max)
        # spritegroupに追加
        spritegrp.add(self, layer="backlogpage")

    def update_page(self, page, max):
        """バックログの何ページ目を見ているかの情報を更新する。
        page: 現在見ているページ。
        max: ページの最大数。
        """
        self.page = page
        self.max = max
        self.update_scale()

    def update_scale(self):
        font = cw.cwpy.rsrc.fonts["backlog_page"]
        s = "%s/%s" % (self.page, self.max)
        h = font.get_height()
        w = h/2+cw.s(4)
        self.image = pygame.Surface((w*len(s), h)).convert_alpha()
        self.image.fill((0, 0, 0, 0))
        for i, c in enumerate(s):
            x = i * w
            y = cw.s(0)
            subimg = font.render(c, True, (0, 0, 0))
            for xi in xrange(x-1, x+2):
                for yi in xrange(y-1, y+2):
                    if xi <> x or yi <> y:
                        self.image.blit(subimg, (xi, yi))
            subimg = font.render(c, True, (255, 255, 255))
            self.image.blit(subimg, (x, y))
        self.rect = self.image.get_rect()
        pos = (cw.s(cw.SIZE_AREA[0]) - self.rect.width - cw.s(10), cw.s(10))
        self.rect.topleft = pos

def draw_frame(image, size, pos=None, backlog=False):
    """
    引数のサーフェスにメッセージウィンドウの外枠を描画。
    """
    if pos is None:
        pos = cw.s((0, 0))
    pointlist = get_pointlist(size, cw.s((0, 0)))
    colour = (0, 0, 0, 255)
    pygame.draw.lines(image, colour, False, pointlist)
    if backlog:
        colour = cw.cwpy.setting.blwinframecolour
    else:
        colour = cw.cwpy.setting.mwinframecolour
    pointlist = get_pointlist((size[0]-cw.s(1), size[1]-cw.s(1)), cw.s((1, 1)))
    pygame.draw.lines(image, colour, False, pointlist)
    pointlist = get_pointlist((size[0]-cw.s(2), size[1]-cw.s(2)), cw.s((2, 2)))
    colour = (0, 0, 0, 255)
    pygame.draw.lines(image, colour, False, pointlist)

def get_pointlist(size, pos=(0, 0)):
    """
    外枠描画のためのポイントリストを返す。
    """
    pos1 = pos
    pos2 = (pos[0], size[1]-cw.s(1))
    pos3 = (size[0]-cw.s(1), size[1]-cw.s(1))
    pos4 = (size[0]-cw.s(1), pos[1])
    pos5 = pos
    return (pos1, pos2, pos3, pos4, pos5)

def rpl_specialstr(s):
    """
    テキストセルや選択肢のテキスト内の
    特殊文字列(#, $)を置換した文字列を返す。
    """
    name_table = _create_nametable(False, None)
    return _rpl_specialstr(False, s, name_table, _get_stepvalue, _get_flagvalue, encodedtext=False)

def _create_nametable(full, talker):
    random = cw.cwpy.event.get_targetmember("Random")
    random = random.name if random else ""
    selected = cw.cwpy.event.get_targetmember("Selected")\
               if cw.cwpy.event.has_selectedmember() else u""
    selected = selected.name if selected else ""
    unselected = cw.cwpy.event.get_targetmember("Unselected")
    unselected = unselected.name if unselected else ""
    if full:
        inusecard = cw.cwpy.event.get_targetmember("Inusecard")
        inusecard = inusecard.name if inusecard else ""
        talker = talker.name if talker else ""
    party = cw.cwpy.ydata.party.name if cw.cwpy.ydata.party else ""
    yado = cw.cwpy.ydata.name

    name_table = {
        "#m" : selected,   # 選択中のキャラ名(#i=#m というわけではない)
        "#r" : random,     # ランダム選択キャラ名
        "#u" : unselected, # 非選択中キャラ名
        "#y" : yado,       # 宿の名前
        "#t" : party       # パーティの名前
    }
    if full:
        name_table["#c"] = inusecard # 使用カード名(カード使用イベント時のみ)
        name_table["#i"] = talker    # 話者の名前(表示イメージのキャラやカード名)

    if full:
        # シナリオ内の画像で上書き
        for key in cw.cwpy.rsrc.specialchars.iterkeys():
            if key in name_table:
                del name_table[key]
    return name_table

def _get_stepvalue(key):
    if key in cw.cwpy.sdata.steps:
        s = cw.cwpy.sdata.steps[key].get_valuename()
    else:
        s = ""
    return s

def _get_flagvalue(key):
    if key in cw.cwpy.sdata.flags:
        s = cw.cwpy.sdata.flags[key].get_valuename()
    else:
        s = ""
    return s

def _rpl_specialstr(full, s, name_table, get_step, get_flag, encodedtext=True):
    """
    特殊文字列(#, $)を置換した文字列を返す。
    """
    buf = []
    skip = 0
    if encodedtext:
        s = cw.util.decodewrap(s)
    for i, c in enumerate(s):
        if 0 < skip:
            skip -= 1
            continue

        def get_varvalue(get, c):
            if i+1 == len(s):
                return 0
            next = s[i+1:].find(c)
            if next < 0:
                return 0
            fl = s[i+1:i+1+next]
            skip = 1 + next
            buf.append(get(fl))
            return skip

        if c == '#':
            if i + 1 == len(s) or s[i+1] == '\n':
                buf.append(c)
                continue
            nc = s[i+1].lower()
            if full and '#' + nc in cw.cwpy.rsrc.specialchars:
                buf.append(c)
                continue
            if full:
                if nc in ('m', 'r', 'u', 'c', 'i', 't', 'y'):
                    buf.append(name_table.get("#" + nc, ""))
                    skip = 1
                else:
                    buf.append(c)
            else:
                if nc in ('m', 'r', 'u', 't', 'y'):
                    buf.append(name_table.get("#" + nc, ""))
                    skip = 1
                else:
                    buf.append(c)
        elif c == '%':
            skip = get_varvalue(get_flag, '%')
            if skip == 0:
                buf.append(c)
        elif c == '$':
            skip = get_varvalue(get_step, '$')
            if skip == 0:
                buf.append(c)
        else:
            buf.append(c)

    if encodedtext:
        return cw.util.encodewrap("".join(buf))
    else:
        return "".join(buf)


def main():
    pass

if __name__ == "__main__":
    main()
