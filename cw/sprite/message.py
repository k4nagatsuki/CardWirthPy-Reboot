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
                                                pos=(80, 50), size=(470, 180)):
        base.CWPySprite.__init__(self)
        # メッセージの選択結果
        self.result = None
        # data
        self.names = names
        self.path = path
        self.text = text
        # image
        self.image = pygame.Surface(size).convert_alpha()
        self.image.fill(cw.cwpy.setting.mwincolour)
        # rect
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # 外枠描画
        draw_frame(self.image, size, (0, 0))
        # 話者(CardHeader or Character)
        self.talker = talker

        # 話者画像
        if self.path:
            image = cw.util.load_image(self.path, True)
            self.image.blit(image, (18, 38))

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
        # cwpylist, indexクリア
        cw.cwpy.list = []
        cw.cwpy.index = -1

        # スピードが0の場合、最初から全て描画
        if self.speed == 0:
            self.speed = 1
            self.draw_all()

        # spritegroupに追加
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

        try:
            pos, txtimg, txtimg2 = self.charimgs[self.frame/self.speed]

            # 通常のテキスト描画。
            if isinstance(txtimg2, pygame.Surface):
                self.image.blit(txtimg2, (pos[0] + 1, pos[1]))
                self.image.blit(txtimg2, (pos[0] - 1, pos[1]))
                self.image.blit(txtimg2, (pos[0], pos[1] + 1))
                self.image.blit(txtimg2, (pos[0], pos[1] - 1))
            # u"―"描画時の処理。両脇の影を描画するかどうか。
            elif isinstance(txtimg2, tuple):
                txtimg2, join_flags = txtimg2

                if not join_flags[1]:
                    self.image.blit(txtimg2, (pos[0] + 1, pos[1]))

                if not join_flags[0]:
                    self.image.blit(txtimg2, (pos[0] - 1, pos[1]))

                self.image.blit(txtimg2, (pos[0], pos[1] + 1))
                self.image.blit(txtimg2, (pos[0], pos[1] - 1))

            self.image.blit(txtimg, pos)
            self.frame += 1
        except:
            self.is_drawing = False
            cw.cwpy.has_inputevent = True
            self.frame = 0
            # SelectionBarを描画
            cw.cwpy.list = self.selections
            x, y = self.selection_pos

            for index, name in enumerate(self.names):
                pos = (x, 25 * index + y)
                sbar = SelectionBar(name, pos)
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

        r_halfwidth = re.compile(u"[ -~｡-ﾟ]")    # 半角文字の集合
        r_specialfont = re.compile("#[a-z]")     # 特殊文字(#)の集合
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

    def rpl_specialstr(self, s):
        """
        特殊文字列(#, $)を置換した文字列を返す
        """
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

        d = {"#c" : inusecard,  # 使用カード名（カード使用イベント時のみ）
             "#i" : talker,     # 話者の名前（表示イメージのキャラやカード名）
             "#m" : selected,   # 選択中のキャラ名（#i=#m というわけではない）
             "#r" : random,     # ランダム選択キャラ名
             "#u" : unselected, # 非選択中キャラ名
             "#y" : yado,       # 宿の名前
             "#t" : party       # パーティの名前
        }

        for key, value in d.iteritems():
            if not value or key in cw.cwpy.rsrc.specialchars:
                continue

            s = s.replace(key, value)
            s = s.replace(key.upper(), value)

        # ステップ変数名の置換
        r_step = re.compile("\$([^\$]*)\$")  # ステップ変数参照($)の集合
        s = r_step.sub(self.rpl_stepvalue, s)
        # フラグ変数名の置換
        r_flag = re.compile("\%([^\%]*)\%")  # フラグ変数参照(%)の集合
        s = r_flag.sub(self.rpl_flagvalue, s)
        return s

    def rpl_stepvalue(self, m):
        key = m.group(1)

        if key in cw.cwpy.sdata.steps:
            s = cw.cwpy.sdata.steps[key].get_valuename()
        else:
            s = ""

        return s

    def rpl_flagvalue(self, m):
        key = m.group(1)

        if key in cw.cwpy.sdata.flags:
            s = cw.cwpy.sdata.flags[key].get_valuename()
        else:
            s = ""

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
    def __init__(self, names, text="", pos=(80, 50), size=(470, 38)):
        base.CWPySprite.__init__(self)
        # メッセージの選択結果
        self.result = None
        # data
        self.names = names
        self.path = ""
        self.text = u"どれか一つを選択してください。" if not text else text
        self.talker = None
        # image
        colour = cw.cwpy.setting.mwincolour
        self.image = pygame.Surface(size).convert_alpha()
        self.image.fill(colour)
        # rect
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        # 外枠描画
        draw_frame(self.image, size, (0, 0))
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
        cw.cwpy.pcardgrp.add(self, layer="message")

    def update(self, scr):
        pass

class MemberSelectWindow(SelectWindow):
    def __init__(self, pcards, pos=(80, 50), size=(470, 38)):
        self.selectmembers = pcards
        names = [(index, pcard.name)
                        for index, pcard in enumerate(self.selectmembers)]
        names.append((len(names), u"キャンセル"))
        text = u"メンバーを選択してください。"
        SelectWindow.__init__(self, names, text, pos, size)

class SelectionBar(base.SelectableSprite):
    def __init__(self, name, pos, size=(470, 25)):
        base.SelectableSprite.__init__(self)
        self._selectable_on_event = True
        # 各種データ
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
        cw.cwpy.pcardgrp.add(self, layer="selectionbar")

    def get_unselectedimage(self):
        return self._image

    def get_selectedimage(self):
        return cw.imageretouch.to_negative(self._image)

    def update(self, scr=None):
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
        colour = cw.cwpy.setting.mwincolour
        colour = colour
        image.fill(colour)
        # 外枠描画
        draw_frame(image, size, pos=(0, 0))
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
        return image

    def lclick_event(self, skip=False):
        """
        メッセージ選択肢のクリックイベント。
        """
        cw.cwpy.sounds[u"システム・クリック"].play()

        # クリックした時だけ、軽く下に押されるアニメーションを行う
        if not skip:
            cw.animation.animate_sprite(self, "click")

        mwin = cw.cwpy.get_messagewindow()

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

def draw_frame(image, size, pos=(0, 0)):
    """
    引数のサーフェスにメッセージウィンドウの外枠を描画。
    """
    pointlist = get_pointlist(size, (0, 0))
    colour = (0, 0, 0, 255)
    pygame.draw.lines(image, colour, False, pointlist)
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
