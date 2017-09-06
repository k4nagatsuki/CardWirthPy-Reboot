#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import os
import re
import pygame
import pygame.locals

import cw
import base


class MessageWindow(base.CWPySprite):
    def __init__(self, text, names, imgpaths=[][:], talker=None,
                 pos_noscale=None, size_noscale=None,
                 nametable={}.copy(), namesubtable={}.copy(), flagtable={}.copy(), steptable={}.copy(),
                 backlog=False, result=None, showing_result=-1, versionhint="", specialchars=None,
                 trim_top_noscale=0, columns=1, spcharinfo=None, centering_x=False, centering_y=False,
                 boundarycheck=False):
        base.CWPySprite.__init__(self)
        if pos_noscale is None:
            pos_noscale = (81, 50)
        if size_noscale is None:
            size_noscale = (470, 180)
        self.trim_top_noscale = trim_top_noscale
        self.columns = columns
        self.centering_x = centering_x
        self.centering_y = centering_y
        self.boundarycheck = boundarycheck

        self.backlog = backlog
        self._barspchr = True

        self.name_table = nametable
        self.name_subtable = namesubtable
        self.flag_table = flagtable
        self.step_table = steptable
        self.specialchars = specialchars if specialchars else cw.cwpy.rsrc.specialchars.copy()

        # メッセージの選択結果
        self.result = result
        self.showing_result = showing_result
        # data
        self.names = names
        self.names_log = []
        self.imgpaths = imgpaths
        self.text = text
        self.text_log = u""
        self.spcharinfo = spcharinfo

        # 話者(CardHeader or Character)
        self.talker = talker
        if talker:
            self.talker_name = talker.name
        else:
            self.talker_name = None

        self.versionhint = versionhint
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_MESSAGE, self.versionhint)

        if not self.name_table:
            self.name_table = _create_nametable(True, self.talker)
        if not self.name_subtable:
            self.name_subtable = _create_nametable(False, self.talker)

        self._init_image(size_noscale, pos_noscale)

        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs(init=True)
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed
        # SelectionBarインスタンスリスト
        self.selections = []
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
            cw.cwpy.backloggrp.add(self, layer=cw.LAYER_LOG)
        else:
            if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
                layer = cw.LAYER_SPMESSAGE
            else:
                layer = cw.LAYER_MESSAGE
            cw.cwpy.cardgrp.add(self, layer=layer)

    def _init_image(self, size_noscale, pos_noscale):
        # image
        self.image = pygame.Surface(cw.s(size_noscale)).convert_alpha()
        if self.backlog:
            wincolour = cw.cwpy.setting.blwincolour
        else:
            wincolour = cw.cwpy.setting.mwincolour
        self.image.fill(wincolour)
        # rect
        self.rect_noscale = pygame.Rect(pos_noscale, size_noscale)
        self.rect = cw.s(self.rect_noscale)
        self.top_noscale = size_noscale[1]
        self.bottom_noscale = 0
        # 外枠描画
        draw_frame(self.image, cw.s(size_noscale), cw.s((0, 0)), self.backlog)
        # 話者画像
        talkersize_noscale = []
        self.talker_image = []
        if self.imgpaths:
            for info, can_loaded_scaledimage, basetalker, scaledimagedict in self.imgpaths:
                if scaledimagedict:
                    talker_image_noscale = scaledimagedict.get(1, None)
                    scale = int(math.pow(2, int(math.log(cw.UP_SCR, 2))))
                    while 2 <= scale:
                        if scale in scaledimagedict:
                            talker_image_noscale = scaledimagedict[scale]
                            break
                        scale /= 2
                else:
                    path = info.path
                    if not cw.binary.image.path_is_code(path):
                        lpath = path.lower()
                        if lpath.startswith(cw.cwpy.yadodir.lower()) or \
                                lpath.startswith(cw.cwpy.tempdir.lower()):
                            path = cw.util.get_yadofilepath(path)
                    talker_image_noscale = cw.util.load_image(path, True, can_loaded_scaledimage=can_loaded_scaledimage)

                if talker_image_noscale and talker_image_noscale.get_width():
                    self.talker_image.append((cw.s(talker_image_noscale), info))
                    w, h = talker_image_noscale.get_size()
                    scr_scale = talker_image_noscale.scr_scale if hasattr(talker_image_noscale, "scr_scale") else 1
                    w /= scr_scale
                    h /= scr_scale
                    talkersize_noscale.append(((w, h), info))

        self.talker_top_noscale = 0x7fffffff
        self.talker_bottom_noscale = -0x7fffffff - 1

        for size, info in talkersize_noscale:
            tih = size[1]
            baserect = info.calc_basecardposition(size, noscale=True)
            y = (180 - tih) // 2
            y -= self.trim_top_noscale

            self.top_noscale = max(0, min(y-9, self.top_noscale))
            self.bottom_noscale = min(size_noscale[1], max(y+tih+9, self.bottom_noscale))

            self.talker_top_noscale = max(0, min(y, self.talker_top_noscale))
            self.talker_bottom_noscale = min(size_noscale[1], max(y+tih, self.talker_bottom_noscale))

        xmove = cw.s(0)
        for talker_image, info in self.talker_image:
            baserect = info.calc_basecardposition(talker_image.get_size(), noscale=False)
            if info.basecardtype == "LargeCard":
                baserect.x -= cw.s(11) # LargeCardとNormalCardのサイズ差に合わせた調節
            xmove = max(-baserect.x, xmove)

        for talker_image, info in self.talker_image:
            baserect = info.calc_basecardposition(talker_image.get_size(), noscale=False)
            if info.basecardtype == "LargeCard":
                baserect.x -= cw.s(11) # LargeCardとNormalCardのサイズ差に合わせた調節
            y = (cw.s(180) - baserect.height) // 2
            y -= cw.s(self.trim_top_noscale)
            if info.basecardtype:
                x = cw.s(15) + baserect.x
            elif info.postype == "Center":
                x = (self.rect.width-baserect.width) // 2
            else:
                x = cw.s(15)
            x += xmove
            y += baserect.y
            cw.imageretouch.blit_2bitbmp_to_message(self.image, talker_image, (x, y), wincolour)

        self._back = None
        self._fore = None

    def update_scale(self):
        if self.specialchars:
            self.specialchars.reset()
        self._init_image(self.rect_noscale.size, self.rect_noscale.topleft)
        self.charimgs = self.create_charimgs(init=False)
        self.selections = []

        self.is_drawing = True
        self.frame = 0
        self.draw_all()

    @staticmethod
    def clear_selections():
        cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_1)
        cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_1)
        cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_2)
        cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_2)
        cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_BAR)
        cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE_LOG)

    def update(self, scr):
        if self.is_drawing:
            self.draw_char()    # テキスト描画

    @staticmethod
    def is_sbold():
        return cw.cwpy.setting.fonttypes["message"][3 if cw.UP_SCR <= 1 else 4]

    @staticmethod
    def get_messagestyledata():
        return (MessageWindow.is_sbold(), cw.cwpy.setting.fonttypes["message"],
                cw.UP_SCR, cw.cwpy.setting.decorationfont)

    def draw_all(self):
        while self.is_drawing:
            self.draw_char()

    def draw_char(self):
        if self.speed and self.frame % self.speed:
            self.frame += 1
            return

        if self.charimgs and not self._fore:
            if self.centering_y:
                # 中央寄せ時の縦幅 = 描画した文字の下端-上端
                h = self.blockbottom_noscale-self.blocktop_noscale
            else:
                # 通常描画時の縦幅 = メッセージウィンドウのサイズ
                # ただしログ表示時はウィンドウの上下が削られて縮められているので
                # 削られた上端の分だけは追加しておく
                h = self.rect_noscale[3]
            self._fore = pygame.Surface(cw.s((470, h))).convert_alpha()
            self._fore.fill((0, 0, 0, 0))
            self._back = self._fore.copy()

        chridx = self.frame / self.speed
        if chridx < len(self.charimgs):
            font = cw.cwpy.rsrc.fonts["message"]
            lineheight = font.get_height()
            sbold = MessageWindow.is_sbold()

            pos, txtimg, txtimg2, txtimg3, linerect = self.charimgs[chridx]
            size = None

            if self.centering_x:
                shiftx = (self.rect.width - linerect.width) // 2
            else:
                shiftx = 0

            if self.centering_y:
                shifty = cw.s((180 - (self.blockbottom_noscale-self.blocktop_noscale)) // 2)
                shifty -= cw.s(self.blocktop_noscale)
                bt = cw.s(self.blocktop_noscale)
            else:
                shifty = cw.s(0)
                bt = cw.s(self.trim_top_noscale)
            tt = cw.s(self.trim_top_noscale)

            if txtimg2:
                if self.backlog:
                    wincolour = cw.cwpy.setting.blwincolour
                else:
                    wincolour = cw.cwpy.setting.mwincolour
                pos2 = (pos[0] + shiftx, pos[1] - tt + shifty)
                cw.imageretouch.blit_2bitbmp_to_message(self.image, txtimg2, pos2, wincolour)
                size = txtimg2.get_size()

            # 通常のテキスト描画
            if txtimg3:
                for x in xrange(pos[0]-1, pos[0]+2):
                    for y in xrange(pos[1]-1, pos[1]+2):
                        self._back.blit(txtimg3, (x, y-bt))
                        if sbold:
                            self._back.blit(txtimg3, (x+1, y-bt))

            if txtimg:
                self._fore.blit(txtimg, (pos[0], pos[1]-bt))
                if sbold:
                    self._fore.blit(txtimg, (pos[0]+1, pos[1]-bt))

                size = txtimg.get_size()

            if size:
                area1 = pygame.Rect(pos[0]-1, pos[1]-1, size[0]+3, size[1]+2)
                area2 = pygame.Rect(area1)
                if self.centering_y:
                    area2.top -= cw.s(self.blocktop_noscale)
                    area1.top += shifty
                else:
                    area2.top -= cw.s(self.trim_top_noscale)
                area1.left += shiftx
                area1.top -= tt
                self.image.blit(self._back, area1.topleft, area2)
                self.image.blit(self._fore, area1.topleft, area2)
            self.frame += 1
        else:
            self.is_drawing = False
            cw.cwpy.has_inputevent = True
            self.frame = 0
            self.create_selectionbar()
            self._fore = None
            self._back = None

    def create_selectionbar(self):
        # SelectionBarを描画
        if not self.backlog:
            cw.cwpy.list = self.selections
        x_noscale, y_noscale = self.rect_noscale.left, self.rect_noscale.bottom

        for index, name in enumerate(self.names):
            # 互換動作: 1.30以前は選択肢に特殊文字を使用しない
            if not self.backlog and self._barspchr and not cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
                name = (name[0], self.rpl_specialstr(False, name[1], self.name_subtable))
            pos_noscale = (x_noscale, y_noscale)
            rest = 1 if (index % self.columns) < (self.rect_noscale.width % self.columns) else 0
            size_noscale = ((self.rect_noscale.width // self.columns) + rest, 25)
            selected = 1 < len(self.names) and self.backlog and self.showing_result == index
            sbar = SelectionBar(index, name, pos_noscale, size_noscale, backlog=self.backlog, selected=selected)
            self.selections.append(sbar)
            sbar.update()
            self.names_log.append(name)

            if (index+1) % self.columns == 0:
                # 次の行
                x_noscale = self.rect_noscale.left
                y_noscale += size_noscale[1]
            else:
                x_noscale += size_noscale[0]

    def create_charimgs(self, pos_noscale=None, init=True):
        if pos_noscale is None:
            if self.centering_x:
                pos_noscale = (-1, 9)
            else:
                pos_noscale = (14, 9)
        pos = cw.s(pos_noscale)
        log_seq = []
        if self.talker_image:
            if not self.backlog and init:
                self.text, self.spcharinfo = self.rpl_specialstr(True, self.text)
                if self.boundarycheck:
                    self.text = cw.util.wordwrap(self.text, 32+1, spcharinfo=self.spcharinfo)
                else:
                    self.text = cw.util.txtwrap(self.text, 2, encodedtext=False, spcharinfo=self.spcharinfo)
            # 互換動作: 1.28以前は話者画像のサイズによって本文の位置がずれる
            if cw.cwpy.sct.lessthan("1.28", self.versionhint):
                def calc_w((bmp, info)):
                    return bmp.get_width()
                w = max(map(calc_w, self.talker_image))
            else:
                w = cw.s(74)
            if self.centering_x:
                posp = pos = cw.s(-26) + w, pos[1]
            else:
                posp = pos = pos[0] + cw.s(25) + w, pos[1]
        else:
            if not self.backlog and init:
                self.text, self.spcharinfo = self.rpl_specialstr(True, self.text)
                if self.boundarycheck:
                    self.text = cw.util.wordwrap(self.text, 42+1, spcharinfo=self.spcharinfo)
                else:
                    self.text = cw.util.txtwrap(self.text, 3, encodedtext=False, spcharinfo=self.spcharinfo)
            posp = pos

        yp_noscale = pos_noscale[1]

        r_specialfont = re.compile("#.") # 特殊文字(#)の集合
        # 文字色変更文字(&)の集合
        r_changecolour = re.compile("&[\x20-\x7E]")
        # フォントデータ
        font = cw.cwpy.rsrc.fonts["message"]
        colour = (255, 255, 255)
        lineheight_noscale = 22
        lineheight = cw.s(lineheight_noscale)
        cheight = font.size("#")[1]
        # 各種変数
        cnt = 0
        skip = False
        images = []
        self._linerect = None

        # 左右接続のために伸ばす文字
        r_join = re.compile(u"[―─＿￣]")

        # 縦方向中央寄せのための基準位置
        self.blocktop_noscale = 0x7fffffff
        self.blockbottom_noscale = -0x7fffffff - 1

        bottom = self.rect_noscale[3]-yp_noscale-lineheight_noscale*7

        def put_xinfo(x, width):
            linerect2 = pygame.Rect(x, 0, width, 1)
            if self._linerect:
                self._linerect.union_ip(linerect2)
            else:
                self._linerect = linerect2

        def put_topbottom(y, height):
            self.top_noscale = min(y-yp_noscale, self.top_noscale)
            self.bottom_noscale = max(y+height+bottom, self.bottom_noscale)
            self.top_noscale = max(0, self.top_noscale)
            self.bottom_noscale = min(self.rect_noscale[3], self.bottom_noscale)

            self.blocktop_noscale = min(y, self.blocktop_noscale)
            self.blockbottom_noscale = max(y+height, self.blockbottom_noscale)

        y_noscale = yp_noscale
        for index, char in enumerate(self.text):
            # 改行処理
            if char == "\n":
                cnt += 1
                pos = posp[0], lineheight * cnt + posp[1]
                y_noscale = lineheight_noscale * cnt + yp_noscale
                log_seq.append(u"\n")
                self._linerect = None

                # 8行以下の文字列は表示しない
                if cnt > 6 and not self.centering_y:
                    break
                else:
                    continue

            # 特殊文字を使った後は一文字スキップする
            elif skip:
                skip = False
                continue

            orig_chars = self.text[index:index+2]
            chars = "".join(orig_chars).lower()

            # 特殊文字
            image2 = None
            if self.specialchars and index in self.spcharinfo:
                if r_specialfont.match(chars):
                    specialchars = self.specialchars
                    if chars in specialchars:
                        charimg, userfont = specialchars[chars]
                        w, h = charimg.get_size()
                        scr_scale = charimg.scr_scale if hasattr(charimg, "scr_scale") else 1
                        w //= scr_scale
                        h //= scr_scale

                        if userfont:
                            cpos = (pos[0]+cw.s(1), pos[1]+cw.s(1))
                            put_xinfo(pos[0], cw.s(charimg.get_width()))
                            put_topbottom(y_noscale+1, h)
                            images.append((cpos, None, cw.s(charimg), None, self._linerect))
                            pos = pos[0] + cw.s(20), pos[1]
                            skip = True
                            log_seq.append(orig_chars)
                            continue

                        put_xinfo(pos[0], cw.s(charimg.get_width()))
                        put_topbottom(y_noscale-1, lineheight_noscale+2)
                        image2 = cw.s(charimg)
                        image2 = image2.convert_alpha()
                        image2.fill(colour, special_flags=pygame.locals.BLEND_RGBA_MULT)
                        images.append((pos, None, decorate(image2, basecolour=colour), None, self._linerect))
                        pos = pos[0] + cw.s(20), pos[1]
                        skip = True
                        log_seq.append(orig_chars)
                        continue

                # 文字色変更
                elif r_changecolour.match(chars):
                    colour = self.get_fontcolour(chars[1])
                    if chars[1] <> '\n':
                        skip = True
                    continue

            log_seq.append(char)
            # 半角文字だったら文字幅は半分にする
            if cw.util.is_hw(char):
                cwidth = cw.s(10)
            else:
                cwidth = cw.s(20)

            if char:
                put_xinfo(pos[0], cwidth)
            if char and not char.isspace():
                put_topbottom(y_noscale-1, lineheight_noscale+2)

                # 通常文字
                image = font.render(char, cw.cwpy.setting.fontsmoothing_message, colour)
                image = decorate(image, basecolour=colour)
                image3 = font.render(char, cw.cwpy.setting.fontsmoothing_message, (0, 0, 0))

                # u"―"の場合、左右の線が繋がるように補完する
                if r_join.match(char):
                    rect = image.get_rect()
                    size = (rect.w + cw.s(20), rect.h)
                    image = pygame.transform.scale(image, size)
                    image3 = pygame.transform.scale(image3, size)
                    image = image.subsurface((10, 0, min(rect.w, cw.s(20)), rect.h))
                    image3 = image3.subsurface((10, 0, min(rect.w, cw.s(20)), rect.h))

                px = pos[0]
                py = pos[1]

                if image:
                    px += (cwidth-image.get_width() + cw.s(2)) / 2
                py += (lineheight-cheight) / 2
                images.append(((px, py), image, image2, image3, self._linerect))

            pos = pos[0] + cwidth, pos[1]

        if self.centering_y:
            top = (180 - (self.blockbottom_noscale - self.blocktop_noscale)) // 2
            self.top_noscale = top - 9
            self.bottom_noscale = top + (self.blockbottom_noscale - self.blocktop_noscale) + 9

            self.top_noscale = max(0, self.top_noscale)
            self.bottom_noscale = min(self.rect_noscale[3], self.bottom_noscale)

        if self.blockbottom_noscale <= self.blocktop_noscale:
            self.top_noscale = 9
            self.bottom_noscale = self.rect_noscale[3] - bottom

        if self.bottom_noscale <= self.top_noscale:
            self.top_noscale = 0
            self.bottom_noscale = yp_noscale + bottom

        self.text_log = u"".join(log_seq)
        self._linerect = None
        return images

    def rpl_specialstr(self, full, s, nametable=None):
        """
        特殊文字列(#, $)を置換した文字列を返す。
        """
        if not nametable:
            nametable = self.name_table
        text, spcharinfo, _namelist, _namelistindex = _rpl_specialstr(full, s, nametable, self.get_stepvalue, self.get_flagvalue)
        if full:
            return text, spcharinfo
        else:
            return text

    def get_stepvalue(self, key, full, name_table, basenamelist, startindex, spcharinfo, namelist, namelistindex, stack):
        if self.backlog:
            if key in self.step_table:
                v = self.step_table[key]
            else:
                return None, namelistindex
        elif key in cw.cwpy.sdata.steps:
            v = cw.cwpy.sdata.steps[key]
        else:
            v = _get_spstep(key)
            if v is None:
                return None, namelistindex

        self.step_table[key] = v
        s = v.get_valuename()
        if stack <= 0 and v.spchars:
            # 特殊文字の展開(Wsn.2)
            s, _, _, namelistindex = _rpl_specialstr(full, s, name_table, self.get_stepvalue, self.get_flagvalue,
                                                     basenamelist, startindex, spcharinfo, namelist, namelistindex, stack+1)
        return s, namelistindex

    def get_flagvalue(self, key, full, name_table, basenamelist, startindex, spcharinfo, namelist, namelistindex, stack):
        if self.backlog:
            if key in self.flag_table:
                v = self.flag_table[key]
            else:
                return None, namelistindex
        elif key in cw.cwpy.sdata.flags:
            v = cw.cwpy.sdata.flags[key]
        else:
            return None, namelistindex

        self.flag_table[key] = v
        s = v.get_valuename()
        if stack <= 0 and v.spchars:
            # 特殊文字の展開(Wsn.2)
            s, _, _, namelistindex = _rpl_specialstr(full, s, name_table, self.get_stepvalue, self.get_flagvalue,
                                                     basenamelist, startindex, spcharinfo, namelist, namelistindex, stack+1)
        return s, namelistindex

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
        if not cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
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
                 backlog=False, result=None, showing_result=-1, columns=1, barspchr=True,
                 nametable={}.copy(), namesubtable={}.copy(), flagtable={}.copy(), steptable={}.copy()):
        base.CWPySprite.__init__(self)
        if pos_noscale is None:
            pos_noscale = (81, 50)
        if size_noscale is None:
            size_noscale = (470, 40)
        self.trim_top_noscale = 0
        self.columns = columns
        self.centering_x = False
        self.centering_y = False
        self.boundarycheck = False
        self.blocktop_noscale = 0
        self.blockbottom_noscale = size_noscale[1]
        self.talker_top_noscale = 0
        self.talker_bottom_noscale = size_noscale[1]

        self.name_table = nametable
        self.name_subtable = namesubtable
        self.flag_table = flagtable
        self.step_table = steptable

        self.backlog = backlog
        self._barspchr = barspchr
        if not self.name_table:
            self.name_table = _create_nametable(True, None)
        if not self.name_subtable:
            self.name_subtable = _create_nametable(False, None)
        self.talker_image = []
        self.versionhint = None
        self.specialchars = None

        # メッセージの選択結果
        self.result = result
        self.showing_result = showing_result
        # data
        self.names = names
        self.names_log = []
        self.imgpaths = []
        self.text = cw.cwpy.msgs["select_message"] if not text else text
        self.text_log = u""
        self.spcharinfo = set()
        self.talker = None
        self.talker_name = None
        self._init_image(size_noscale, pos_noscale)
        # 描画する文字画像のリスト作成
        self.charimgs = self.create_charimgs((14, 9), init=True)
        # frame
        self.frame = 0
        # メッセージスピード
        self.speed = cw.cwpy.setting.messagespeed or 1
        # メッセージ描画中か否かのフラグ
        self.is_drawing = True
        # SelectionBarインスタンスリスト
        self.selections = []
        # メッセージ全て表示
        self.draw_all()
        # spritegroupに追加
        if self.backlog:
            cw.cwpy.backloggrp.add(self, layer=cw.LAYER_LOG)
        else:
            if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
                layer = cw.LAYER_SPMESSAGE
            else:
                layer = cw.LAYER_MESSAGE
            cw.cwpy.cardgrp.add(self, layer=layer)

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
        self.top_noscale = size_noscale[1]
        self.bottom_noscale = 0
        # 外枠描画
        draw_frame(self.image, cw.s(size_noscale), cw.s((0, 0)), self.backlog)

        self._back = None
        self._fore = None

    def update_scale(self):
        self._init_image(self.rect_noscale.size, self.rect_noscale.topleft)
        self.charimgs = self.create_charimgs((14, 9), init=False)
        self.selections = []

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
            size_noscale = (470, 40)
        self.selectmembers = pcards
        names = [(index, pcard.name)
                        for index, pcard in enumerate(self.selectmembers)]
        names.append((len(names), cw.cwpy.msgs["cancel"]))
        text = cw.cwpy.msgs["select_member_message"]
        SelectWindow.__init__(self, names, text, pos_noscale, size_noscale, barspchr=False)

class SelectionBar(base.SelectableSprite):
    def __init__(self, showing_index, name, pos_noscale, size_noscale, backlog=False, selected=False):
        base.SelectableSprite.__init__(self)
        self.selectable_on_event = True
        # 各種データ
        self.backlog = backlog
        self.selected = selected
        self.index = name[0]
        self.showing_index = showing_index
        self.name = name[1]
        # 通常画像
        self.size_noscale = size_noscale
        size = cw.s(self.size_noscale)
        self._image = self.get_image(size)
        # rect
        self.rect = self._image.get_rect()
        self.pos_noscale = pos_noscale
        self.rect.topleft = cw.s(self.pos_noscale)
        self.rect_noscale = pygame.Rect(self.pos_noscale, self.size_noscale)
        # image
        self.image = self._image
        # status
        self.status = "normal"
        # frame
        self.frame = 0
        # spritegroupに追加
        if self.backlog:
            self.group = cw.cwpy.backloggrp
            self.group.add(self, layer=cw.LAYER_LOG_BAR)
        else:
            self.group = cw.cwpy.cardgrp
            if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
                layer = cw.LAYER_SPSELECTIONBAR_1
            else:
                layer = cw.LAYER_SELECTIONBAR_1
            self.group.add(self, layer=layer)

        # 半ば画面外へ出る選択肢は特別措置としてステータスバー上にも表示する
        if cw.s(cw.SIZE_AREA[1]) <= self.rect.bottom:
            if backlog:
                if cw.cwpy.setting.messagelog_type == cw.setting.LOG_SINGLE:
                    cw.cwpy.sbargrp.add(self, layer=cw.sprite.statusbar.LAYER_MESSAGE_LOG)
            else:
                cw.cwpy.sbargrp.add(self, layer=cw.sprite.statusbar.LAYER_MESSAGE)

        # 完全に画面外に出る選択肢は表示禁止
        if cw.s(cw.SIZE_AREA[1]) < self.rect.top:
            self.rect.height = cw.s(0)
            self.rect_noscale.height = 0

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
        if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
            layer1 = cw.LAYER_SPSELECTIONBAR_1
            layer2 = cw.LAYER_SPSELECTIONBAR_2
        else:
            layer1 = cw.LAYER_SELECTIONBAR_1
            layer2 = cw.LAYER_SELECTIONBAR_2
        if self.frame == 0:
            self.rect.move_ip(cw.s(0), cw.s(+1))
            self.status = "click"
            self.group.change_layer(self, layer2)
        elif self.frame == 6:
            self.status = "normal"
            self.rect.move_ip(cw.s(0), cw.s(-1))
            self.frame = 0
            self.group.change_layer(self, layer1)
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
        nameimg = font.render(self.name, cw.cwpy.setting.fontsmoothing_message, (255, 255, 255))
        nameimg = decorate(nameimg, angle=16, basecolour=(255, 255, 255))
        nameimg2 = font.render(self.name, cw.cwpy.setting.fontsmoothing_message, (0, 0, 0))
        w = size[0] - cw.s(10)
        if w < nameimg.get_width():
            nameimg = cw.image.smoothscale(nameimg, (w, nameimg.get_height()))
            nameimg2 = cw.image.smoothscale(nameimg2, (w, nameimg2.get_height()))
        w, h = nameimg.get_size()
        pos = (cw.s(self.size_noscale[0])-w)/2, (cw.s(self.size_noscale[1])-h)/2
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

        cw.cwpy.play_sound("click", True)

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

        mwin.showing_result = self.showing_index

class BacklogData(object):
    def __init__(self, base):
        """メッセージログ表示用のデータ。
        """
        if isinstance(base, SelectWindow):
            self.type = 1
        else:
            self.type = 0
        self.text = base.text
        self.text_log = base.text_log
        self.spcharinfo = base.spcharinfo
        self.names = base.names
        self.names_log = base.names_log
        self.imgpaths = base.imgpaths
        self.talker_name = base.talker_name
        self.rect_noscale = base.rect_noscale
        self.top_noscale = base.top_noscale
        self.bottom_noscale = base.bottom_noscale
        self.name_table = base.name_table
        self.name_subtable = base.name_subtable
        self.columns = base.columns
        self.flag_table = base.flag_table
        self.step_table = base.step_table
        self.showing_result = base.showing_result
        self.versionhint = base.versionhint
        self.specialchars = base.specialchars
        self.centering_x = base.centering_x
        self.centering_y = base.centering_y
        self.boundarycheck = base.boundarycheck
        self.talker_top_noscale = base.talker_top_noscale
        self.talker_bottom_noscale = base.talker_bottom_noscale

    def get_height_noscale(self):
        """メッセージと選択肢の表示高さを計算して返す。
        """
        if cw.cwpy.setting.messagelog_type == cw.setting.LOG_COMPRESS:
            if self.type == 0:
                h = max(self.talker_bottom_noscale+9, self.bottom_noscale) - min(self.talker_top_noscale-9, self.top_noscale)
                height_noscale = min(self.rect_noscale.height, h)
                if len(self.names_log) == 1 and self.columns == 1 and self.names_log[0][1] == cw.cwpy.msgs["ok"]:
                    num = 0
                else:
                    num = 1
                return height_noscale + num*25
            else:
                return self.rect_noscale.height + 25
        else:
            return self.rect_noscale.height + ((len(self.names_log)+(self.columns-1)) // self.columns)*25

    @property
    def _from_index(self):
        return self.showing_result // self.columns * self.columns

    @property
    def _to_index(self):
        return min(len(self.names_log), self._from_index + self.columns)

    def create_message(self):
        if self.type == 0:
            if cw.cwpy.setting.messagelog_type == cw.setting.LOG_COMPRESS:
                h = max(self.talker_bottom_noscale+9, self.bottom_noscale) - min(self.talker_top_noscale-9, self.top_noscale)
                trim_top = min(self.talker_top_noscale-9, self.top_noscale)

                size_noscale = (self.rect_noscale.width, min(self.rect_noscale.height, h))
                if len(self.names_log) == 1 and self.columns == 1 and self.names_log[0][1] == cw.cwpy.msgs["ok"]:
                    # 高さ圧縮時はデフォルト選択肢を表示しない
                    names = []
                    showing_result = -1
                else:
                    # 選択された項目のある行のみ表示
                    names = self.names_log[self._from_index:self._to_index]
                    showing_result = self.showing_result - self._from_index
            else:
                size_noscale = self.rect_noscale.size
                trim_top = 0
                names = self.names_log
                showing_result = self.showing_result
            base = MessageWindow(self.text, names, self.imgpaths, None,
                                 self.rect_noscale.topleft, size_noscale,
                                 self.name_table, self.name_subtable, self.flag_table, self.step_table,
                                 True, None, showing_result, self.versionhint, self.specialchars,
                                 trim_top_noscale=trim_top, columns=self.columns,
                                 spcharinfo=self.spcharinfo,
                                 centering_x=self.centering_x, centering_y=self.centering_y,
                                 boundarycheck=self.boundarycheck)
        else:
            if cw.cwpy.setting.messagelog_type == cw.setting.LOG_COMPRESS:
                names = self.names_log[self._from_index:self._to_index]
                showing_result = self.showing_result - self._from_index
            else:
                names = self.names_log
                showing_result = self.showing_result
            base = SelectWindow(names, self.text, self.rect_noscale.topleft, self.rect_noscale.size,
                                True, None, showing_result, columns=self.columns,
                                nametable=self.name_table, namesubtable=self.name_subtable,
                                flagtable=self.flag_table, steptable=self.step_table)

        return base

class BacklogCurtain(base.CWPySprite):
    def __init__(self, spritegrp, layer, size_noscale, pos_noscale, color=None):
        """メッセージログ用の半透明黒背景スプライト。
        spritegrp: 登録するSpriteGroup。"curtain"レイヤに追加される。
        alpha: 透明度。
        """
        base.CWPySprite.__init__(self)
        if color:
            self.color = color
        else:
            self.color = cw.cwpy.setting.blcurtaincolour
        self.size_noscale = size_noscale
        self.pos_noscale = pos_noscale
        self.image = pygame.Surface(cw.s(self.size_noscale)).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(self.pos_noscale)
        # spritegroupに追加
        spritegrp.add(self, layer=layer)

    def update_scale(self):
        self.image = pygame.Surface(cw.s(self.size_noscale)).convert()
        self.image.fill(self.color[:3])
        self.image.set_alpha(self.color[3])
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(self.pos_noscale)

class BacklogPage(base.CWPySprite):
    def __init__(self, page, pagemax, spritegrp):
        """バックログの何ページ目を見ているかを表示するスプライト。
        page: 現在見ているページ。
        pagemax: ページの最大数。
        spritegrp: 登録するSpriteGroup。"backlogpage"レイヤに追加される。
        """
        base.CWPySprite.__init__(self)
        self.update_page(page, pagemax)
        # spritegroupに追加
        spritegrp.add(self, layer=cw.LAYER_LOG_PAGE)

    def update_page(self, page, pagemax):
        """バックログの何ページ目を見ているかの情報を更新する。
        page: 現在見ているページ。
        pagemax: ページの最大数。
        """
        self.page = page
        self.max = pagemax
        self.update_scale()

    def update_scale(self):
        font = cw.cwpy.rsrc.fonts["backlog_page"]
        s = "%s/%s" % (self.page, self.max)
        w, h = font.size(s)
        w += 2
        h += 2

        self.image = pygame.Surface((w, h)).convert_alpha()
        self.image.fill((0, 0, 0, 0))
        x = 1
        y = 1
        subimg = font.render(s, True, (0, 0, 0))
        for xi in xrange(x-1, x+2):
            for yi in xrange(y-1, y+2):
                if xi <> x or yi <> y:
                    self.image.blit(subimg, (xi, yi))
        subimg = font.render(s, True, (255, 255, 255))
        self.image.blit(subimg, (x, y))

        self.rect = self.image.get_rect()
        if cw.cwpy.setting.is_logscrollable():
            left = cw.s(18)
        else:
            left = cw.s(10)
        pos = (cw.s(cw.SIZE_AREA[0]) - self.rect.width - left, cw.s(10))
        self.rect.topleft = pos

_decorate_cache = {}
_decorate_cache_upscr = 0

def decorate(image, angle=8, basecolour=(255, 255, 255)):
    """
    imageに装飾フォント処理を適用する。
    """
    global _decorate_cache, _decorate_cache_upscr

    if _decorate_cache_upscr <> cw.UP_SCR:
        _decorate_cache_upscr = cw.UP_SCR
        _decorate_cache = {}

    if cw.cwpy.setting.decorationfont:
        key = (image.get_height(), angle, basecolour)
        decoimg = _decorate_cache.get(key, None)
        if not decoimg:
            # グラデーションのかかった台紙を作成
            h = image.get_height()
            decoimg = pygame.Surface((h, h)).convert_alpha()
            decoimg.fill(basecolour)

            w = decoimg.get_width()
            mid = decoimg.get_height()/2

            if sum(basecolour) < 128*3:
                # 暗くなりすぎると見えなくなるので明るくしておく
                decoimg.fill((16, 16, 16, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)

            for y in xrange(1, mid, 1):
                # グラデーション
                rect = (0, mid-y, w, 1)
                c = max(0, y-cw.s(1))*angle
                if cw.UP_SCR <> 1:
                    c = int(float(c) / cw.UP_SCR)
                color = (c, c, c, 0)
                decoimg.fill(color, rect, special_flags=pygame.locals.BLEND_RGBA_SUB)
                rect = (0, mid+y, w, 1)
                decoimg.fill(color, rect, special_flags=pygame.locals.BLEND_RGBA_SUB)

            _decorate_cache[key] = decoimg

        if not (image.get_flags() & pygame.locals.SRCALPHA):
            image = image.convert_alpha()

        image.blit(decoimg, image.get_rect(), decoimg.get_rect(), special_flags=pygame.locals.BLEND_RGBA_MIN)

    return image

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

def rpl_specialstr(s, basenamelist=None):
    """
    テキストセルや選択肢のテキスト内の
    特殊文字列(#, $)を置換した文字列を返す。
    """
    name_table = _create_nametable(False, None)
    r = _rpl_specialstr(False, s, name_table, _get_stepvalue, _get_flagvalue, basenamelist=basenamelist)
    return r[0], r[2]

class _NameGetter(object):
    def __init__(self, func):
        self.func = func
        self.names = []
        self.count = 0

    def reset(self):
        self.count = 0

    def get_name(self):
        if self.count < len(self.names):
            name = self.names[self.count]
        else:
            name = self.func()
            self.names.append(name)
        self.count += 1
        return name

def _reset_nametable(nametable):
    for name in nametable.itervalues():
        if isinstance(name, _NameGetter):
            name.reset()

class NameListItem(object):
    """パーティ名やキャラクター名が変更された時に
    後からテキストセルの内容を書き換えるため、
    内容を記録しておく。
    """
    def __init__(self, data, name):
        self.data = data
        self.name = name

def _get_namefromlist(index, namelist):
    item = namelist[index]
    if isinstance(item.data, (str, unicode)):
        name = item.data
    else:
        name = item.data.name if not item.data is None else item.name
    index += 1
    return index, name

def _get_namefromtable(nc, nametable, namelist):
    data = nametable.get(u"#" + nc, "")
    if isinstance(data, _NameGetter):
        data = data.get_name()

    if isinstance(data, (str, unicode)):
        name = data
    else:
        name = data.name if not data is None else ""

    namelist.append(NameListItem(data, name))

    return name

def _create_nametable(full, talker):
    def get_random():
        return cw.cwpy.event.get_targetmember("Random")
    selected = cw.cwpy.event.get_targetmember("Selected")\
               if cw.cwpy.event.has_selectedmember() else u""
    unselected = cw.cwpy.event.get_targetmember("Unselected")
    if full:
        inusecard = cw.cwpy.event.get_targetmember("Inusecard")
    party = cw.cwpy.ydata.party
    yado = cw.cwpy.ydata

    name_table = {
        "#m" : selected,   # 選択中のキャラ名(#i=#m というわけではない)
        "#r" : _NameGetter(get_random),     # ランダム選択キャラ名
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

def _get_stepvalue(key, full, name_table, basenamelist, startindex, spcharinfo, namelist, namelistindex, stack):
    if key in cw.cwpy.sdata.steps:
        v = cw.cwpy.sdata.steps[key]
    else:
        v = _get_spstep(key)
        if v is None:
            return None, namelistindex

    s = v.get_valuename()
    if stack <= 0 and v.spchars:
        # 特殊文字の展開(Wsn.2)
        s, _, _, namelistindex = _rpl_specialstr(full, s, name_table, _get_stepvalue, _get_flagvalue,
                                                 basenamelist, startindex, spcharinfo, namelist, namelistindex, stack+1)
    return s, namelistindex

def _get_spstep(name):
    if cw.cwpy.event.in_inusecardevent:
        cardversion = cw.cwpy.event.get_inusecard().wsnversion
    else:
        cardversion = None

    if cw.cwpy.sdata.is_wsnversion('2', cardversion):
        lname = name.lower()
        if lname in u"??selectedplayer":
            # 選択メンバのパーティ内の番号(Wsn.2)
            # パーティ内の選択メンバがいない場合は"0"
            if cw.cwpy.event.has_selectedmember():
                sel = cw.cwpy.event.get_selectedmember()
            else:
                sel = None
            pcards = cw.cwpy.get_pcards()
            if sel and sel in pcards:
                pn = u"%d" % (pcards.index(sel)+1)
                return cw.data.Step(0, u"", [pn], u"", False)
            else:
                return cw.data.Step(0, u"", [u"0"], u"", False)
        else:
            # プレイヤーキャラクターの名前(??Player1～6)(Wsn.2)
            pcards = cw.cwpy.get_pcards()
            players = map(lambda a: u"??player%d" % a, xrange(1, len(pcards)+1))
            if lname in players:
                pcard = pcards[players.index(lname)]
                return cw.data.Step(0, u"", [pcard.name], u"", False)

        if lname.startswith(u"??"):
            return cw.data.Step(0, u"", [u""], u"", False)

    return None

def _get_flagvalue(key, full, name_table, basenamelist, startindex, spcharinfo, namelist, namelistindex, stack):
    if key in cw.cwpy.sdata.flags:
        v = cw.cwpy.sdata.flags[key]
    else:
        return None, namelistindex

    s = v.get_valuename()
    if stack <= 0 and v.spchars:
        # 特殊文字の展開(Wsn.2)
        s, _, _, namelistindex = _rpl_specialstr(full, s, name_table, _get_stepvalue, _get_flagvalue,
                                                 basenamelist, startindex, spcharinfo, namelist, namelistindex, stack+1)
    return s, namelistindex

def _rpl_specialstr(full, s, name_table, get_step, get_flag, basenamelist=None,
                    startindex=0, spcharinfo=None, namelist=None, namelistindex=0, stack=0):
    """
    特殊文字列(#, $)を置換した文字列を返す。
    """
    if spcharinfo is None:
        _reset_nametable(name_table)
    if namelist is None:
        namelist = []
    buf = []
    buflen = startindex
    if spcharinfo is None:
        spcharinfo = set()
    skip = 0
    for i, c in enumerate(s):
        if 0 < skip:
            skip -= 1
            continue

        def get_varvalue(get, c, namelistindex):
            if i+1 == len(s):
                return 0, namelistindex
            nextpos = s[i+1:].find(c)
            if nextpos < 0:
                return 0, namelistindex
            fl = s[i+1:i+1+nextpos]
            val, namelistindex = get(fl, full, name_table, basenamelist, buflen, spcharinfo, namelist, namelistindex, stack)
            if val is None:
                if not full:
                    # BUG: 存在しない状態変数を表示しようとすると
                    #      先頭の文字が欠ける(CardWirth 1.50)
                    buf.append(c[1:])
                return 0 if full else -1, namelistindex
            skip = 1 + nextpos
            buf.append(val)
            return skip, namelistindex

        if c == '#':
            if i + 1 == len(s) or s[i+1] == '\n':
                buf.append(c)
                buflen += len(c)
                continue
            nc = s[i+1].lower()
            if full and '#' + nc in cw.cwpy.rsrc.specialchars:
                spcharinfo.add(buflen)
                buf.append(c)
                buflen += len(c)
                continue
            if full:
                if nc in ('m', 'r', 'u', 'c', 'i', 't', 'y'):
                    if basenamelist is None:
                        buf.append(_get_namefromtable(nc, name_table, namelist))
                    else:
                        namelistindex, name = _get_namefromlist(namelistindex, basenamelist)
                        buf.append(name)
                    buflen += len(buf[-1])
                    skip = 1
                else:
                    buf.append(c)
                    buflen += len(c)
            else:
                if nc in ('m', 'r', 'u', 't', 'y'):
                    if basenamelist is None:
                        buf.append(_get_namefromtable(nc, name_table, namelist))
                    else:
                        namelistindex, name = _get_namefromlist(namelistindex, basenamelist)
                        buf.append(name)
                    buflen += len(buf[-1])
                    skip = 1
                else:
                    buf.append(c)
                    buflen += len(c)
        elif c == '%':
            skip, namelistindex = get_varvalue(get_flag, '%', namelistindex)
            if skip:
                buflen += len(buf[-1])
            else:
                buf.append(c)
                buflen += len(c)
        elif c == '$':
            skip, namelistindex = get_varvalue(get_step, '$', namelistindex)
            if skip:
                buflen += len(buf[-1])
            else:
                buf.append(c)
                buflen += len(c)
        else:
            if full and c == '&':
                spcharinfo.add(buflen)
            buf.append(c)
            buflen += len(c)

    if not basenamelist is None:
        namelist = basenamelist
    return "".join(buf), spcharinfo, namelist, namelistindex

def get_messagelogtext(mwins, lastline=True):
    """メッセージまたはログをプレイヤー向けのテキストデータに変換する。
    """
    lines = []
    for mwin in mwins:
        name = mwin.talker_name
        if name is None:
            seq = []
            for info, _can_loaded_scaledimage2, _basetalker, _scaledimagedict in mwin.imgpaths:
                if info.path:
                    seq.append(os.path.basename(info.path))
            if seq:
                name = u" ".join(seq)

        if name:
            s = u"--< %s >--" % (name)
        else:
            s = u"--"

        slen = cw.util.get_strlen(s)
        if slen < cw.LOG_SEPARATOR_LEN_SHORT:
            s += u"-" * (cw.LOG_SEPARATOR_LEN_SHORT-slen)
        lines.append(s)
        lines.append(mwin.text_log.strip(u"\n"))
        if mwin.names_log and not (len(mwin.names_log) == 1 and mwin.columns == 1 and mwin.names_log[0][1] == cw.cwpy.msgs["ok"]):
            lines.append("")
            for i, sel in enumerate(mwin.names_log):
                if i == mwin.showing_result and 1 < len(mwin.names_log):
                    s = u">>[ %s " % (sel[1])
                else:
                    s = u"  [ %s " % (sel[1])
                slen = cw.util.get_strlen(s)
                if slen < (cw.LOG_SEPARATOR_LEN_SHORT-1):
                    s += u" " * ((cw.LOG_SEPARATOR_LEN_SHORT-1)-slen)
                s += u"]"
                lines.append(s)

    if lastline:
        lines.append(u"-" * cw.LOG_SEPARATOR_LEN_SHORT)
        lines.append("")

    return u"\n".join(lines)


def store_messagelogimage(path, can_loaded_scaledimage):
    """メッセージログ内でpathが使用されている箇所があれば
    pathが上書きされた場合に備えて各スケールのイメージを読み込んでおく。
    """
    if path.startswith(cw.cwpy.tempdir):
        path = path.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
    dict = None
    fdict = None

    for log in cw.cwpy.sdata.backlog:
        for i, (info, can_loaded_scaledimage2, basetalker, scaledimagedict) in enumerate(log.imgpaths):
            def load_with_scaled(dict, scaledimagedict):
                scaledimagedict.clear()
                if dict:
                    for key, value in dict.iteritems():
                        scaledimagedict[key] = value
                else:
                    dict = scaledimagedict
                    fpath = path
                    if not cw.binary.image.path_is_code(fpath):
                        lpath = fpath.lower()
                        if lpath.startswith(cw.cwpy.yadodir.lower()) or \
                                lpath.startswith(cw.cwpy.tempdir.lower()):
                            fpath = cw.util.get_yadofilepath(fpath)
                    bmp = cw.util.load_image(fpath, True, noscale=True)
                    scaledimagedict[1] = bmp
                    if can_loaded_scaledimage2:
                        spext = os.path.splitext(fpath)
                        for scale in cw.SCALE_LIST:
                            fname = u"%s.x%s%s" % (spext[0], scale, spext[1])
                            if os.path.isfile(fname):
                                bmp = cw.util.Depth1Surface(cw.util.load_image(fname, True, noscale=True), scale)
                                scaledimagedict[scale] = bmp
                return dict

            if os.path.normcase(info.path) == os.path.normcase(path):
                dict = load_with_scaled(dict, scaledimagedict)
                log.imgpaths[i] = (info, can_loaded_scaledimage, basetalker, scaledimagedict)

            if cw.cwpy.is_playingscenario():
                for name in list(log.specialchars.iterkeys()):
                    fpath = u"font_%s.bmp" % name[1]
                    fpath = cw.util.get_materialpath(fpath, cw.M_IMG, scedir=cw.cwpy.sdata.scedir, findskin=False)
                    # リソースの読込メソッドの差し替えを行い、予めメモリ上に読み込んだ実体を返すようにする
                    # 以前に差し替えが行われているかどうかをLazyResource#argsの長さで見分ける
                    if os.path.normcase(path) == os.path.normcase(fpath) and len(log.specialchars.dic[name].args):
                        fdict2 = {}
                        fdict = load_with_scaled(fdict, fdict2)
                        def load():
                            image_noscale = fdict2.get(1, None)
                            scale = int(math.pow(2, int(math.log(cw.UP_SCR, 2))))
                            while 2 <= scale:
                                if scale in fdict2:
                                    image_noscale = fdict2[scale]
                                    break
                                scale /= 2
                            return image_noscale, True
                        log.specialchars.set(name, load)
                        break

def main():
    pass

if __name__ == "__main__":
    main()
