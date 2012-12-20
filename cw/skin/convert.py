#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import shutil
import struct
import threading

import cw

from win32res import get_bitmap, get_rcdata

class Converter(threading.Thread):
    def __init__(self, exe):
        threading.Thread.__init__(self)

        self.maximum = 60
        self.curnum = 0
        self.message = u"変換を開始しています..."
        self.failure = False
        self.complete = False
        self.errormessage = ""

        self.init(exe)

    def init(self, exe):
        self.exe = exe
        if self.exe:
            f = open(self.exe, "rb")
            self.exebinary = f.read()
            f.close()

        self.datadir = self.find_datadir()
        self.scenariodir = self.find_scenariodir()

        self.data = cw.data.xml2etree(u"Data/SkinBase/Skin.xml")
        self.data.find2("Property/Name").text = self.find_skinname()
        self.data.find2("Property/Type").text = self.find_type()
        self.data.find2("Property/Author").text = self.find_author()
        self.data.find2("Property/Description").text = cw.util.encodewrap(self.find_description())

        self.actioncard = self._get_resources(u"ActionCard")
        self.gameover = self._get_resources(u"GameOver")
        self.scenario = self._get_resources(u"Scenario")
        self.title = self._get_resources(u"Title")
        self.yado = self._get_resources(u"Yado")

        self._get_features()
        self._get_sounds()

    def _get_resources(self, dir):
        dir = cw.util.join_paths(u"Data/SkinBase/Resource/Xml/", dir)
        rsrc = {}
        for path in os.listdir(dir):
            if path.lower().endswith(".xml"):
                name = os.path.splitext(path)[0]
                path = cw.util.join_paths(dir, path)
                rsrc[name] = cw.data.xml2etree(path)
        return rsrc

    def _write_data(self, dir, table):
        for data in table.values():
            data.fpath = cw.util.join_paths(dir, os.path.relpath(data.fpath, u"Data/SkinBase/"))
            data.write()

    def find_skinname(self):
        if self.exe:
            exebasename = os.path.basename(self.exe)
            return os.path.splitext(exebasename)[0]
        else:
            return "Default"

    def find_description(self):
        if self.exe:
            exebasename = os.path.basename(self.exe)
            return (u"%sをベースに自動生成したスキン。") % exebasename
        else:
            return u""

    def find_datadir(self):
        if self.exe:
            key = "\\Midi\\DefReset.mid"
            index = self.exebinary.find(key)
            try:
                return unicode(self.exebinary[index-4:index], "ms932")
            except:
                pass
        return u"Data"

    def find_scenariodir(self):
        if self.exe:
            key = "\0\\\0\\\0\\Summary.wsm\0\\\0\\\0.wid\0"
            index = self.exebinary.find(key)
            try:
                index = index + len(key)
                return unicode(self.exebinary[index:index+8], "ms932")
            except:
                pass
        return u"Scenario"

    def find_type(self):
        if self.exe:
            # TODO
            return u"MedievalFantasy"
        else:
            return u"MedievalFantasy"

    def find_author(self):
        return u""

    def _get_features(self):
        # バイナリ断片を手がかりにして特性値を探す。
        if not self.exe:
            return
        key = "TStatusItem\x81\x89" # "TStatusItem♂"
        index = self.exebinary.find(key) + len(key) - len("\x81\x89")

        physical = struct.Struct("<hhhhhh")
        mental = struct.Struct("<hhhhh")

        try:
            def set_params(data, index):
                # 特性名
                n = self.exebinary[index:index+20]
                index += 20
                i = n.find("\0")
                if 0 <= i:
                    name = n[:i]
                else:
                    name = n
                data.find("./Name").text = unicode(name, "ms932")

                # 身体能力
                p = physical.unpack(self.exebinary[index:index+2*6])
                index += 2*6
                e = data.find("./Physical")
                e.set("dex", str(p[0]))
                e.set("agl", str(p[1]))
                e.set("int", str(p[2]))
                e.set("str", str(p[3]))
                e.set("vit", str(p[4]))
                e.set("min", str(p[5]))

                # 精神能力
                p = mental.unpack(self.exebinary[index:index+2*5])
                index += 2*5
                e = data.find("./Mental")
                e.set("aggressive", str(p[0]))
                e.set("cheerful", str(p[1]))
                e.set("brave", str(p[2]))
                e.set("cautious", str(p[3]))
                e.set("trickish", str(p[4]))

                return index

            for e in self.data.getfind("Sexes"):
                index = set_params(e, index)
            for e in self.data.getfind("Periods"):
                index = set_params(e, index)
            # 使用されていない年代「古老」を飛ばす
            index += 20 + 2*6 + 2*5
            for e in self.data.getfind("Natures"):
                index = set_params(e, index)
            for e in self.data.getfind("Makings"):
                index = set_params(e, index)

            # 型の派生元を設定
            # 英明型 <- 標準型,万能型
            e = self.data.find("Natures/Nature[8]/BaseNatures/BaseNature[1]")
            e.text = self.data.find("Natures/Nature[1]/Name").text
            e = self.data.find("Natures/Nature[8]/BaseNatures/BaseNature[2]")
            e.text = self.data.find("Natures/Nature[2]/Name").text
            # 無双型 <- 勇将型,豪傑型
            e = self.data.find("Natures/Nature[9]/BaseNatures/BaseNature[1]")
            e.text = self.data.find("Natures/Nature[3]/Name").text
            e = self.data.find("Natures/Nature[9]/BaseNatures/BaseNature[2]")
            e.text = self.data.find("Natures/Nature[4]/Name").text
            # 天才型 <- 知将型,策士型
            e = self.data.find("Natures/Nature[10]/BaseNatures/BaseNature[1]")
            e.text = self.data.find("Natures/Nature[5]/Name").text
            e = self.data.find("Natures/Nature[10]/BaseNatures/BaseNature[2]")
            e.text = self.data.find("Natures/Nature[6]/Name").text

            # 解説文
            entrydlg = cw.skin.win32res.get_rcdata(self.exe, "TENTRYDLG")
            if entrydlg:
                typesheet = entrydlg["EntryDlg"]["PageControl"]["TypeSheet"]
                # 標準型
                e = self.data.find("Natures/Nature[1]/Description")
                e.text = typesheet["Type3Label"]["Caption"]
                # 万能型
                e = self.data.find("Natures/Nature[2]/Description")
                e.text = typesheet["Type2Label"]["Caption"]
                # 勇将型
                e = self.data.find("Natures/Nature[3]/Description")
                e.text = typesheet["Type1Label"]["Caption"]
                # 豪傑型
                e = self.data.find("Natures/Nature[4]/Description")
                e.text = typesheet["Type0Label"]["Caption"]
                # 知将型
                e = self.data.find("Natures/Nature[5]/Description")
                e.text = typesheet["Type4Label"]["Caption"]
                # 策士型
                e = self.data.find("Natures/Nature[6]/Description")
                e.text = typesheet["Type5Label"]["Caption"]

        except:
            pass

    def _get_sounds(self):
        # バイナリ断片を手がかりにして音声ファイル名を探す。
        if not self.exe:
            return
        try:
            sounds = self.data.getfind("Sounds")
            def get_keybefore(e, key, length, less=0):
                index = self.exebinary.find(key)
                if 0 <= index:
                    index -= less
                    e.text = unicode(self.exebinary[index-length:index], "ms932")
            def get_keyafter(e, key, length, than=0):
                index = self.exebinary.find(key)
                if 0 <= index:
                    index += len(key)
                    index += than
                    e.text = unicode(self.exebinary[index:index+length], "ms932")

            # システム・エラー
            # ".wav\0は、行動不能です。"
            key = ".wav\0\x82\xCD\x81\x41\x8D\x73\x93\xAE\x95\x73\x94\x5C\x82\xC5\x82\xB7\x81\x42\x00"
            get_keybefore(sounds[0], key, 16)
            # システム・クリック
            get_keybefore(sounds[1], key, 18, less=16+5)
            # システム・シグナル
            # ".wav\0本アプリケーションは『小さいフォント』に対応しています。"
            key = ".wav\0\x96\x7B\x83\x41\x83\x76\x83\x8A\x83\x50\x81\x5B\x83\x56\x83\x87\x83\x93\x82\xCD\x81\x77\x8F\xAC\x82\xB3\x82\xA2\x83\x74\x83\x48\x83\x93\x83\x67\x81\x78\x82\xC9\x91\xCE\x89\x9E\x82\xB5\x82\xC4\x82\xA2\x82\xDC\x82\xB7\x81\x42"
            get_keybefore(sounds[2], key, 18)
            # システム・初期化
            get_keybefore(sounds[6], key, 16, less=18+8)
            # システム・回避
            # "死者有効\0抵抗有効\0"
            key = "\x8E\x80\x8E\xD2\x97\x4C\x8C\xF8\x00\x92\xEF\x8D\x52\x97\x4C\x8C\xF8\x00"
            get_keyafter(sounds[3], key, 14)
            # システム・無効
            get_keyafter(sounds[11], key, 14, than=14+5)
            # システム・改ページ
            key = ".wav\0CHECK_FIXED\0CHECK_TARGET\0"
            get_keybefore(sounds[4], key, 18)
            # システム・収穫
            # "TMainWindow\0TBookDlg\0状態\0"
            key = ".wav\0TMainWindow\0TBookDlg\0\x8F\xF3\x91\xD4\x00"
            get_keybefore(sounds[5], key, 14)
            # システム・戦闘
            key = ".wav\0Encounter\0\x30\0\0Round\x20\0"
            get_keybefore(sounds[7], key, 14)
            # システム・装備
            # "\0＿２\0＿３\0＿４\0＿５\0＿６\0異常発生\0"
            key = "\x00\x81\x51\x82\x51\x00\x81\x51\x82\x52\x00\x81\x51\x82\x53\x00\x81\x51\x82\x54\x00\x81\x51\x82\x55\x00\x88\xD9\x8F\xED\x94\xAD\x90\xB6\x00"
            get_keyafter(sounds[8], key, 14)
            # システム・逃走
            key = ".wav\0TITLE_CARD1\0TITLE_CARD1\0TITLE_CARD2\0"
            get_keybefore(sounds[9], key, 14, less=16+5)
            # システム・破棄
            # "\0を捨てます。よろしいですか？\0"
            key = "\x00\x82\xF0\x8E\xCC\x82\xC4\x82\xDC\x82\xB7\x81\x42\x82\xE6\x82\xEB\x82\xB5\x82\xA2\x82\xC5\x82\xB7\x82\xA9\x81\x48\x00"
            get_keyafter(sounds[10], key, 14)
        except:
            pass

    def run(self):
        """クラシックなエンジンからリソースを取り出し、新規スキンを生成する。"""
        self.curnum = 0
        self.message = u"スキンのベースをコピー中..."

        dir = self.data.gettext("Property/Name", "")
        dir = cw.binary.util.check_filename(dir)
        dir = cw.util.join_paths(u"Data/Skin", dir)
        dir = cw.binary.util.check_duplicate(dir)
        shutil.copytree(u"Data/SkinBase", dir)
        f = None
        try:
            # Resource
            self.curnum = 10
            self.message = u"リソースを抽出中..."

            self.data.fpath = cw.util.join_paths(dir, u"Skin.xml")
            self.data.write()

            self._write_data(dir, self.actioncard)
            self._write_data(dir, self.gameover)
            self._write_data(dir, self.scenario)
            self._write_data(dir, self.title)
            self._write_data(dir, self.yado)

            imgtbl = {
                "BUTTON_ARROW":"Button/ARROW",
                "BUTTON_CAST":"Button/CAST",
                "BUTTON_DECK":"Button/DECK",
                "BUTTON_DOWN":"Button/DOWN",
                "BUTTON_LJUMP":"Button/LJUMP",
                "BUTTON_LMOVE":"Button/LMOVE",
                "BUTTON_LSMALL":"Button/LSMALL",
                "BUTTON_RJUMP":"Button/RJUMP",
                "BUTTON_RMOVE":"Button/RMOVE",
                "BUTTON_RSMALL":"Button/RSMALL",
                "BUTTON_SACK":"Button/SACK",
                "BUTTON_SHELF":"Button/SHELF",
                "BUTTON_TRUSH":"Button/TRUSH",
                "BUTTON_UP":"Button/UP",
                "IMAGE_ACTION0":"Card/ACTION0",
                "IMAGE_ACTION1":"Card/ACTION1",
                "IMAGE_ACTION2":"Card/ACTION2",
                "IMAGE_ACTION3":"Card/ACTION3",
                "IMAGE_ACTION4":"Card/ACTION4",
                "IMAGE_ACTION5":"Card/ACTION5",
                "IMAGE_ACTION6":"Card/ACTION6",
                "IMAGE_ACTION7":"Card/ACTION7",
                "IMAGE_ACTION9":"Card/ACTION9",
                "IMAGE_ALARM":"Card/ALARM",
                "IMAGE_BATTLE":"Card/BATTLE",
                "IMAGE_COMMAND0":"Card/COMMAND0",
                "IMAGE_COMMAND1":"Card/COMMAND1",
                "IMAGE_COMMAND2":"Card/COMMAND2",
                "IMAGE_COMMAND3":"Card/COMMAND3",
                "IMAGE_COMMAND4":"Card/COMMAND4",
                "IMAGE_COMMAND5":"Card/COMMAND5",
                "IMAGE_COMMAND6":"Card/COMMAND6",
                "IMAGE_COMMAND7":"Card/COMMAND7",
                "IMAGE_COMMAND8":"Card/COMMAND8",
                "IMAGE_COMMAND9":"Card/COMMAND9",
                "IMAGE_COMMAND10":"Card/COMMAND10",
                "IMAGE_COMMAND11":"Card/COMMAND11",
                "IMAGE_DEBUG":"Card/DEBUG",
                "IMAGE_FATHER":"Card/FATHER",
                "IMAGE_MOTHER":"Card/MOTHER",
                "IMAGE_OVER":"Card/OVER",
                "IMAGE_SHELF":"Card/SHELF",
                "IMAGE_TRUSH":"Card/TRUSH",
                "CARD_ACTION":"CardBg/ACTION",
                "CARD_BEAST":"CardBg/BEAST",
                "CARD_BIND":"CardBg/BIND",
                "CARD_DANGER":"CardBg/DANGER",
                "CARD_FAINT":"CardBg/FAINT",
                "SIGN_HOLD":"CardBg/HOLD",
                "CARD_INFO":"CardBg/INFO",
                "CARD_INJURY":"CardBg/INJURY",
                "CARD_ITEM":"CardBg/ITEM",
                "CARD_LARGE":"CardBg/LARGE",
                "CARD_NORMAL":"CardBg/NORMAL",
                "CARD_OPTION":"CardBg/OPTION",
                "CARD_PARALY":"CardBg/PARALY",
                "SIGN_PENALTY":"CardBg/PENALTY",
                "CARD_PETRIF":"CardBg/PETRIF",
                "SIGN_PREMIER":"CardBg/PREMIER",
                "SIGN_RARE":"CardBg/RARE",
                "CARD_REVERSE":"CardBg/REVERSE",
                "CARD_SKILL":"CardBg/SKILL",
                "CARD_SLEEP":"CardBg/SLEEP",
                "TABLE_CAUTION":"Dialog/CAUTION",
                "CHECK_COMPLETE":"Dialog/COMPLETE",
                "CHECK_FIXED":"Dialog/FIXED",
                "CHECK_FOLDER":"Dialog/FOLDER",
                "CHECK_INVISIBLE":"Dialog/INVISIBLE",
                "CHECK_LINK":"Dialog/LINK",
                "TABLE_PAD":"Dialog/PAD",
                "CHECK_PLAYING":"Dialog/PLAYING",
                "CHECK_SELECT":"Dialog/SELECT",
                "TABLE_STATUS":"Dialog/STATUS",
                "MARK_STATUS0":"Dialog/STATUS0",
                "MARK_STATUS1":"Dialog/STATUS1",
                "MARK_STATUS2":"Dialog/STATUS2",
                "MARK_STATUS3":"Dialog/STATUS3",
                "MARK_STATUS4":"Dialog/STATUS4",
                "MARK_STATUS5":"Dialog/STATUS5",
                "MARK_STATUS6":"Dialog/STATUS6",
                "MARK_STATUS7":"Dialog/STATUS7",
                "MARK_STATUS8":"Dialog/STATUS8",
                "MARK_STATUS9":"Dialog/STATUS9",
                "MARK_STATUS10":"Dialog/STATUS10",
                "MARK_STATUS11":"Dialog/STATUS11",
                "MARK_STATUS12":"Dialog/STATUS12",
                "MARK_STATUS13":"Dialog/STATUS13",
                "CHECK_UTILITY":"Dialog/UTILITY",
                "FONT_ANGRY":"Font/ANGRY",
                "FONT_CLUB":"Font/CLUB",
                "FONT_DIAMOND":"Font/DIAMOND",
                "FONT_EASY":"Font/EASY",
                "FONT_FLY":"Font/FLY",
                "FONT_GRIEVE":"Font/GRIEVE",
                "FONT_HEART":"Font/HEART",
                "FONT_JACK":"Font/JACK",
                "FONT_KISS":"Font/KISS",
                "FONT_LAUGH":"Font/LAUGH",
                "FONT_NIKO":"Font/NIKO",
                "FONT_ONSEN":"Font/ONSEN",
                "FONT_PUZZLE":"Font/PUZZLE",
                "FONT_QUICK":"Font/QUICK",
                "FONT_SPADE":"Font/SPADE",
                "FONT_WORRY":"Font/WORRY",
                "FONT_X":"Font/X",
                "FONT_ZAP":"Font/ZAP",
                "TITLE_CELL3":"Other/TITLE_CELL3",
                "TITLE_SHADOW":"Other/TITLE_SHADOW",
                "STATUS_BODY0":"Status/BODY0",
                "STATUS_BODY1":"Status/BODY1",
                "STATUS_DOWN0":"Status/DOWN0",
                "STATUS_DOWN1":"Status/DOWN1",
                "STATUS_DOWN2":"Status/DOWN2",
                "STATUS_DOWN3":"Status/DOWN3",
                "STATUS_LIFE":"Status/LIFE",
                "STATUS_LIFEBAR":"Status/LIFEBAR",
                "STATUS_LIFEGUAGE":"Status/LIFEGUAGE",
                "STATUS_MAGIC0":"Status/MAGIC0",
                "STATUS_MAGIC1":"Status/MAGIC1",
                "STATUS_MAGIC2":"Status/MAGIC2",
                "STATUS_MAGIC3":"Status/MAGIC3",
                "STATUS_MIND0":"Status/MIND0",
                "STATUS_MIND1":"Status/MIND1",
                "STATUS_MIND2":"Status/MIND2",
                "STATUS_MIND3":"Status/MIND3",
                "STATUS_MIND4":"Status/MIND4",
                "STATUS_MIND5":"Status/MIND5",
                "STATUS_SUMMON":"Status/SUMMON",
                "CHECK_TARGET":"Status/TARGET",
                "STATUS_UP0":"Status/UP0",
                "STATUS_UP1":"Status/UP1",
                "STATUS_UP2":"Status/UP2",
                "STATUS_UP3":"Status/UP3",
                "STONE_HAND0":"Stone/HAND0",
                "STONE_HAND1":"Stone/HAND1",
                "STONE_HAND2":"Stone/HAND2",
                "STONE_HAND3":"Stone/HAND3",
                "STONE_HAND4":"Stone/HAND4",
                "STONE_HAND5":"Stone/HAND5",
                "STONE_HAND6":"Stone/HAND6",
                "STONE_HAND7":"Stone/HAND7",
                "STONE_HAND8":"Stone/HAND8",
                "STONE_HAND9":"Stone/HAND9",
            }
            glyphtbl = {
                "TCARDDLG/CardDlg/TablePanel/SpeedPanel/BeastBtn/Glyph.Data":"Button/BEAST",
                "TCARDDLG/CardDlg/TablePanel/SpeedPanel/ItemBtn/Glyph.Data":"Button/ITEM",
                "TCARDDLG/CardDlg/TablePanel/SpeedPanel/SkillBtn/Glyph.Data":"Button/SKILL",
                "TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/PursePanel/PurseImage/Picture.Data":"Dialog/MONEYP",
                "TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/VaultPanel/VaultImage/Picture.Data":"Dialog/MONEYY",
                "TMAINWINDOW/MainWindow/SystemBtn/Glyph.Data":"Dialog/SETTINGS",
            }

            # Resource/Image/*
            for resname, target in imgtbl.items():
                res = get_bitmap(self.exe, resname)
                fpath = cw.util.join_paths(dir, "Resource/Image", target + ".bmp")
                resdir = os.path.dirname(fpath)
                if not os.path.isdir(resdir):
                    os.makedirs(resdir)
                f = open(fpath, "wb")
                f.write(res)
                f.close()
                f = None
            for respath, target in glyphtbl.items():
                respaths = respath.split("/")
                resname = respaths[0]
                res = get_rcdata(self.exe, resname)

                for name in respaths[1:]:
                    res = res[name]
                fpath = cw.util.join_paths(dir, "Resource/Image", target + ".bmp")
                resdir = os.path.dirname(fpath)
                if not os.path.isdir(resdir):
                    os.makedirs(resdir)
                if str(res[1:8]) == "TBitmap":
                    res = str(res[12:])
                else:
                    res = str(res[4:])
                f = open(fpath, "wb")
                f.write(res)
                f.close()
                f = None
            # TODO 各種リソース内のテキスト
            # TODO 各種カード名・テキスト
            # TODO サウンド
            # TODO 特性名・解説・能力値

            if not os.path.isabs(self.datadir):
                datadir = cw.util.join_paths(os.path.dirname(self.exe), self.datadir)

            # Bgm
            self.curnum = 20
            self.message = u"BGMフォルダをコピー中..."
            shutil.copytree(cw.util.join_paths(datadir, u"Midi"), cw.util.join_paths(dir, u"Bgm"))

            # Face
            self.curnum = 30
            self.message = u"カード画像フォルダをコピー中..."
            shutil.copytree(cw.util.join_paths(datadir, u"Face"), cw.util.join_paths(dir, u"Face"))

            # Wave
            self.curnum = 40
            self.message = u"効果音フォルダをコピー中..."
            shutil.copytree(cw.util.join_paths(datadir, u"Wave"), cw.util.join_paths(dir, u"Sound"))

            # Table
            self.curnum = 50
            self.message = u"背景画像フォルダをコピー中..."
            shutil.copytree(cw.util.join_paths(datadir, u"Table"), cw.util.join_paths(dir, u"Table"))

            self.curnum = 60
            self.message = u"スキンの生成が完了しました。"

            self.complete = True

        except Exception, ex:
            self.failure = True
            self.complete = True
            self.errormessage = u"スキンの自動生成に失敗しました。"
            shutil.rmtree(dir)
            raise ex

        finally:
            if f:
                f.close()

