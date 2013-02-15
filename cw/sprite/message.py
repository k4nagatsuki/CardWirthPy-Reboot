#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import wx
import pygame
from pygame.locals import *

import cw
import base


class MessageWindow(base.CWPySprite):
    def __init__(self, text, names, path="", talker=None,
                 pos=(80, 50), size=(470, 180), talkerimage=None,
                 nametable={}, flagtable={}, steptable={},
                 backlog=False, result=None):
        base.CWPySprite.__init__(self)
        self.backlog = backlog

        # クラシックスタイルか
        self.classicstyletext = cw.cwpy.setting.classicstyletext
        # クラシックスタイルのテキスト描画用
        if self.classicstyletext and "message_classic" in cw.cwpy.rsrc.fonts:
            self.wxcanvas = wx.EmptyBitmap(22, 22)
            self.wxdc = wx.MemoryDC(self.wxcanvas)
            self.wxdc.SetFont(cw.cwpy.rsrc.fonts["message_classic"])
        else:
            self.wxcanvas = None
            self.wxdc = None

        self.name_table = nametable
        self.flag_table = flagtable
        self.step_table = steptable

        # メッセージの選択結果
        self.result = result
        # data
        self.names = names
        self.path = path
        self.text = text
        # image
        self.image = pygame.Surface(size).convert_alpha()
        if self.backlog:
            self.image.fill(cw.cwpy.setting.blwincolour)
        else:
            self.image.fill(cw.cwpy.setting.mwincolour)
        # rect
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # 外枠描画
        draw_frame(self.image, size, (0, 0), self.backlog)
        # 話者(CardHeader or Character)
        # 名前のみ使用
        self.talker = talker

        self._init_nametable()

        # 話者画像
        if talkerimage:
            self.talker_image = talkerimage
        elif self.path:
            self.talker_image = cw.util.load_image(self.path, True)
        else:
            self.talker_image = None

        if self.talker_image:
            self.image.blit(self.talker_image, (18, 38))

        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs()
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed
        # SelectionBarインスタンスリスト
        self.selections = []
        self.selection_pos = (80, 230)
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
            cw.cwpy.pcardgrp.add(self, layer="message")

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

        chridx = self.frame / self.speed
        if chridx < len(self.charimgs):
            pos, txtimg, txtimg2 = self.charimgs[chridx]

            if isinstance(txtimg2, tuple):
                # 通常のテキスト描画。
                if isinstance(txtimg2, pygame.Surface) or txtimg2[1] == (False, False):
                    for x in xrange(pos[0]-1, pos[0]+2):
                        for y in xrange(pos[1]-1, pos[1]+2):
                            self.image.blit(txtimg2[0], (x, y))
                # u"―"描画時の処理。両脇の影を描画するかどうか。
                else:
                    txtimg2, join_flags = txtimg2

                    if not join_flags[0]:
                        for y in xrange(pos[1]-1, pos[1]+2):
                            self.image.blit(txtimg2, (pos[0] - 1, y))

                    if not join_flags[1]:
                        for y in xrange(pos[1]-1, pos[1]+2):
                            self.image.blit(txtimg2, (pos[0] + 1, y))

                    self.image.blit(txtimg2, (pos[0], pos[1] + 1))
                    self.image.blit(txtimg2, (pos[0], pos[1] - 1))

            self.image.blit(txtimg, pos)
            self.frame += 1
        else:
            self.is_drawing = False
            cw.cwpy.has_inputevent = True
            self.frame = 0

            if self.wxdc:
                self.wxdc.EndDrawing()

            # SelectionBarを描画
            if not self.backlog:
                cw.cwpy.list = self.selections
            x, y = self.selection_pos

            for index, name in enumerate(self.names):
                pos = (x, 25 * index + y)
                selected = 1 < len(self.names) and self.backlog and self.result == index
                sbar = SelectionBar(name, pos, backlog=self.backlog, selected=selected)
                self.selections.append(sbar)
                sbar.update()

    def create_charimgs(self, pos=(15, 13)):
        if self.path:
            self.text = self.rpl_specialstr(self.text)
            self.text = cw.util.txtwrap(self.text, 2)
            posp = pos = pos[0] + 100, pos[1]
        else:
            self.text = self.rpl_specialstr(self.text)
            self.text = cw.util.txtwrap(self.text, 3)
            posp = pos

        r_join = re.compile(u"[―─～]")          # 左右で接続する文字の集合
        r_halfwidth = re.compile(u"[ -~｡-ﾟ]")    # 半角文字の集合
        r_specialfont = re.compile("#.")     # 特殊文字(#)の集合
        r_changecolour = re.compile("&[a-z]")    # 文字色変更文字(&)の集合
        # フォントデータ
        font = cw.cwpy.rsrc.fonts["message"]
        colour = (255, 255, 255)
        h = font.get_height() - 1
        # 各種変数
        cnt = 0
        skip = False
        images = []

        for index, char in enumerate(self.text):
            # 改行処理
            if char == "\n":
                cnt += 1
                pos = posp[0], h * cnt + posp[1]

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
                if chars in cw.cwpy.rsrc.specialchars:
                    charimg, userfont = cw.cwpy.rsrc.specialchars[chars]

                    if userfont:
                        images.append((pos, charimg, None))
                        pos = pos[0] + 20, pos[1]
                        skip = True
                        continue

                    size = charimg.get_size()
                    image = pygame.Surface(size).convert()
                    image.fill(colour)
                    image.blit(charimg, (0, 0))
                    image.set_colorkey(image.get_at((0,0)), RLEACCEL)
                    images.append((pos, image, None))
                    pos = pos[0] + 20, pos[1]
                    skip = True
                    continue

            # 文字色変更
            elif r_changecolour.match(chars):
                colour = self.get_fontcolour(chars[1])
                skip = True
                continue

            # 通常文字
            if self.wxdc:
                # クラシック形式
                self.wxdc.SetPen(wx.BLACK_PEN)
                self.wxdc.SetBrush(wx.BLACK_BRUSH)
                self.wxdc.DrawRectangle(0, 0, self.wxcanvas.Width, self.wxcanvas.Height)
                self.wxdc.SetTextForeground(colour)
                self.wxdc.DrawText(char, 0, 0)
                image = cw.image.conv2surface(self.wxcanvas)
                black = pygame.Color(0, 0, 0)
                image.set_colorkey(wx.BLACK, RLEACCEL)

                self.wxdc.SetPen(wx.Pen(colour))
                self.wxdc.SetBrush(wx.Brush(colour))
                self.wxdc.DrawRectangle(0, 0, self.wxcanvas.Width, self.wxcanvas.Height)
                self.wxdc.SetTextForeground(wx.BLACK)
                self.wxdc.DrawText(char, 0, 0)
                image2 = cw.image.conv2surface(self.wxcanvas)
                image2.set_colorkey(colour, RLEACCEL)

                # u"―"やu"～"の場合、左右の線が繋がるように補完する
                join_left = False
                join_right = False
                if r_join.match(char):
                    if index > 0 and r_join.match(self.text[index-1]):
                        join_left = True
                    else:
                        join_left = False

                    if index + 1 < len(self.text) and r_join.match(self.text[index+1]):
                        join_right = True
                    else:
                        join_right = False

                image2 = (image2, (join_left, join_right))

            else:
                # CardWirthPy形式
                image = font.render(char, True, colour)
                image2 = font.render(char, True, (0, 0, 0))

                # u"ー"の場合、左右の線が繋がるように補完する
                if char == u"―":
                    if index > 0 and self.text[index-1] == u"―":
                        join_left = True
                    else:
                        join_left = False

                    if len(chars) > 1 and self.text[index+1] == u"―":
                        join_right = True
                    else:
                        join_right = False

                    if join_left or join_right:
                        rect = image.get_rect()
                        size = (rect.w + 20, rect.h)
                        image = pygame.transform.scale(image, size)
                        image2 = pygame.transform.scale(image2, size)

                        if join_left and join_right:
                            rect.left += 10
                        elif join_left:
                            rect.left += 20

                        image = image.subsurface(rect)
                        image2 = (image2.subsurface(rect), (join_left, join_right))

                # u"…"の場合、両脇を1ピクセル詰める
                elif char == u"…":
                    w, h = image.get_size()
                    rect = pygame.Rect((0, 0), (6, h))
                    subimg = image.subsurface(rect).copy()
                    image.fill((0, 0, 0, 0), rect)
                    image.blit(subimg, (1, 0))
                    subimg = image2.subsurface(rect).copy()
                    image2.fill((0, 0, 0, 0), rect)
                    image2.blit(subimg, (1, 0))
                    rect = pygame.Rect((w - 6, 0), (6, h))
                    subimg = image.subsurface(rect).copy()
                    image.fill((0, 0, 0, 0), rect)
                    image.blit(subimg, (w - 7, 0))
                    subimg = image2.subsurface(rect).copy()
                    image2.fill((0, 0, 0, 0), rect)
                    image2.blit(subimg, (w - 7, 0))

            images.append((pos, image, image2))

            # 半角文字だったら文字幅は半分にする
            if r_halfwidth.match(char):
                pos = pos[0] + 10, pos[1]
            else:
                pos = pos[0] + 20, pos[1]

        return images

    def _init_nametable(self):
        if self.name_table:
            return

        random = cw.cwpy.event.get_targetmember("Random")
        random = random.name if random else ""
        selected = cw.cwpy.event.get_targetmember("Selected")
        selected = selected.name if selected else ""
        unselected = cw.cwpy.event.get_targetmember("Unselected")
        unselected = unselected.name if unselected else ""
        inusecard = cw.cwpy.event.get_targetmember("Inusecard")
        inusecard = inusecard.name if inusecard else ""
        talker = self.talker.name if self.talker else ""
        party = cw.cwpy.ydata.party.name if cw.cwpy.ydata.party else ""
        yado = cw.cwpy.ydata.name

        self.name_table = {
             "#c" : inusecard,  # 使用カード名(カード使用イベント時のみ)
             "#i" : talker,     # 話者の名前(表示イメージのキャラやカード名)
             "#m" : selected,   # 選択中のキャラ名(#i=#m というわけではない)
             "#r" : random,     # ランダム選択キャラ名
             "#u" : unselected, # 非選択中キャラ名
             "#y" : yado,       # 宿の名前
             "#t" : party       # パーティの名前
        }

    def rpl_specialstr(self, s):
        """
        特殊文字列(#, $)を置換した文字列を返す
        """
        for key, value in self.name_table.iteritems():
            if key in cw.cwpy.rsrc.specialchars:
                continue

            s = s.replace(key, value)
            s = s.replace(key.upper(), value)

        # ステップ変数名の置換
        r_step = re.compile(r"\$(.*?)\$")  # ステップ変数参照($)の集合
        s = r_step.sub(self.rpl_stepvalue, s)
        # フラグ変数名の置換
        r_flag = re.compile(r"\%(.*?)\%")  # フラグ変数参照(%)の集合
        s = r_flag.sub(self.rpl_flagvalue, s)
        return s

    def rpl_stepvalue(self, m):
        key = m.group(1)
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

    def rpl_flagvalue(self, m):
        key = m.group(1)
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
        else:
            return (255, 255, 255)

class SelectWindow(MessageWindow):
    def __init__(self, names, text="", pos=(80, 50), size=(470, 38), backlog=False, result=None):
        base.CWPySprite.__init__(self)
        self.backlog = backlog
        self.name_table = {}
        self.flag_table = {}
        self.step_table = {}

        # クラシックスタイルか
        self.classicstyletext = cw.cwpy.setting.classicstyletext
        # クラシックスタイルのテキスト描画用
        if self.classicstyletext and "message_classic" in cw.cwpy.rsrc.fonts:
            self.wxcanvas = wx.EmptyBitmap(22, 22)
            self.wxdc = wx.MemoryDC(self.wxcanvas)
            self.wxdc.SetFont(cw.cwpy.rsrc.fonts["message_classic"])
        else:
            self.wxcanvas = None
            self.wxdc = None

        # メッセージの選択結果
        self.result = result
        # data
        self.names = names
        self.path = ""
        self.text = cw.cwpy.msgs["select_message"] if not text else text
        self.talker = None
        # image
        if self.backlog:
            colour = cw.cwpy.setting.blwincolour
        else:
            colour = cw.cwpy.setting.mwincolour
        self.image = pygame.Surface(size).convert_alpha()
        self.image.fill(colour)
        # rect
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # 外枠描画
        draw_frame(self.image, size, (0, 0), self.backlog)
        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs((15, 9))
        # frame
        self.frame = 0
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed or 1
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # SelectionBarインスタンスリスト
        self.selections = []
        self.selection_pos = (80, 88)
        # メッセージ全て表示
        self.draw_all()
        # spritegroupに追加
        if self.backlog:
            cw.cwpy.backloggrp.add(self, layer="backlog")
        else:
            cw.cwpy.pcardgrp.add(self, layer="message")

    def update(self, scr):
        pass

class MemberSelectWindow(SelectWindow):
    def __init__(self, pcards, pos=(80, 50), size=(470, 38)):
        self.selectmembers = pcards
        names = [(index, pcard.name)
                        for index, pcard in enumerate(self.selectmembers)]
        names.append((len(names), cw.cwpy.msgs["cancel"]))
        text = cw.cwpy.msgs["select_member_message"]
        SelectWindow.__init__(self, names, text, pos, size)

class SelectionBar(base.SelectableSprite):
    def __init__(self, name, pos, size=(470, 25), backlog=False, selected=False):
        base.SelectableSprite.__init__(self)
        self._selectable_on_event = True
        # 各種データ
        self.backlog = backlog
        self.selected = selected
        self.index = name[0]
        self.name = name[1]
        # 通常画像
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
            cw.cwpy.pcardgrp.add(self, layer="selectionbar")

    def get_unselectedimage(self):
        return self._image

    def get_selectedimage(self):
        return cw.imageretouch.to_negative(self._image)

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
            self.rect.move_ip(0, +1)
            self.status = "click"
        elif self.frame == 6:
            self.status = "normal"
            self.rect.move_ip(0, -1)
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
        draw_frame(image, size, pos=(0, 0), backlog=self.backlog)
        # 選択肢描画
        font = cw.cwpy.rsrc.fonts["selectionbar"]
        nameimg = font.render(self.name, True, (255, 255, 255))
        nameimg2 = font.render(self.name, True, (0, 0, 0))
        w, h = nameimg.get_size()
        pos = (470-w)/2, (25-h)/2
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

        cw.cwpy.sounds["click"].play(True)

        # クリックした時だけ、軽く下に押されるアニメーションを行う
        if not skip:
            cw.animation.animate_sprite(self, "click")

        mwin = cw.cwpy.get_messagewindow()
        if not mwin:
            return

        # イベント再開(次コンテントへのIndexを渡す)
        if isinstance(mwin, MemberSelectWindow):
            # キャンセルをクリックした場合、イベント強制中断
            if len(mwin.selectmembers) == self.index:
                mwin.result = cw.event.EffectBreakError()
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
            self.talker_image = base.talker_image
        else:
            self.talker_image = None
        self.rect = base.rect
        self.name_table = base.name_table
        self.flag_table = base.flag_table
        self.step_table = base.step_table
        self.result = base.result

    def create_message(self):
        if self.type == 0:
            return MessageWindow(self.text, self.names, self.path, None,
                                 self.rect.topleft, self.rect.size,
                                 self.talker_image,
                                 self.name_table, self.flag_table, self.step_table,
                                 True, self.result)
        else:
            return SelectWindow(self.names, self.text, self.rect.topleft, self.rect.size,
                                True, self.result)

class BacklogCurtain(base.CWPySprite):
    def __init__(self, spritegrp, size=(632, 420), pos=(0, 0), alpha=192):
        """バックログ用の半透明黒背景スプライト。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        size: スプライトのサイズ。
        pos: 表示位置。
        alpha: 透明度。
        """
        base.CWPySprite.__init__(self)
        self.image = pygame.Surface(size).convert()
        self.image.fill((0, 0, 0))
        self.image.set_alpha(alpha)
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # spritegroupに追加
        spritegrp.add(self, layer="curtain")

def draw_frame(image, size, pos=(0, 0), backlog=False):
    """
    引数のサーフェスにメッセージウィンドウの外枠を描画。
    """
    pointlist = get_pointlist(size, (0, 0))
    colour = (0, 0, 0, 255)
    pygame.draw.lines(image, colour, False, pointlist)
    if backlog:
        colour = cw.cwpy.setting.blwinframecolour
    else:
        colour = cw.cwpy.setting.mwinframecolour
    pointlist = get_pointlist((size[0]-1, size[1]-1), (1, 1))
    pygame.draw.lines(image, colour, False, pointlist)
    pointlist = get_pointlist((size[0]-2, size[1]-2), (2, 2))
    colour = (0, 0, 0, 255)
    pygame.draw.lines(image, colour, False, pointlist)

def get_pointlist(size, pos=(0, 0)):
    """
    外枠描画のためのポイントリストを返す。
    """
    pos1 = pos
    pos2 = (pos[0], size[1]-1)
    pos3 = (size[0]-1, size[1]-1)
    pos4 = (size[0]-1, pos[1])
    pos5 = pos
    return (pos1, pos2, pos3, pos4, pos5)

def main():
    pass

if __name__ == "__main__":
    main()
