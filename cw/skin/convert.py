#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import shutil
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

