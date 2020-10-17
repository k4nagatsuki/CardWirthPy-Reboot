#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import struct
import threading

import cw
from . import win32res

import typing
from typing import Dict, Iterable, Optional, Sequence, Tuple, Union

IMGTBL = {
    "BUTTON_ARROW": "Button/ARROW",
    "BUTTON_CAST": "Button/CAST",
    "BUTTON_DECK": "Button/DECK",
    "BUTTON_DOWN": "Button/DOWN",
    "BUTTON_LJUMP": "Button/LJUMP",
    "BUTTON_LMOVE": "Button/LMOVE",
    "BUTTON_LSMALL": "Button/LSMALL",
    "BUTTON_RJUMP": "Button/RJUMP",
    "BUTTON_RMOVE": "Button/RMOVE",
    "BUTTON_RSMALL": "Button/RSMALL",
    "BUTTON_SACK": "Button/SACK",
    "BUTTON_SHELF": "Button/SHELF",
    "BUTTON_TRUSH": "Button/TRUSH",
    "BUTTON_UP": "Button/UP",
    "IMAGE_ACTION0": "Card/ACTION0",
    "IMAGE_ACTION1": "Card/ACTION1",
    "IMAGE_ACTION2": "Card/ACTION2",
    "IMAGE_ACTION3": "Card/ACTION3",
    "IMAGE_ACTION4": "Card/ACTION4",
    "IMAGE_ACTION5": "Card/ACTION5",
    "IMAGE_ACTION6": "Card/ACTION6",
    "IMAGE_ACTION7": "Card/ACTION7",
    "IMAGE_ACTION9": "Card/ACTION9",
    "IMAGE_ALARM": "Card/ALARM",
    "IMAGE_BATTLE": "Card/BATTLE",
    "IMAGE_COMMAND0": "Card/COMMAND0",
    "IMAGE_COMMAND1": "Card/COMMAND1",
    "IMAGE_COMMAND2": "Card/COMMAND2",
    "IMAGE_COMMAND3": "Card/COMMAND3",
    "IMAGE_COMMAND4": "Card/COMMAND4",
    "IMAGE_COMMAND5": "Card/COMMAND5",
    "IMAGE_COMMAND6": "Card/COMMAND6",
    "IMAGE_COMMAND7": "Card/COMMAND7",
    "IMAGE_COMMAND8": "Card/COMMAND8",
    "IMAGE_COMMAND9": "Card/COMMAND9",
    "IMAGE_COMMAND10": "Card/COMMAND10",
    "IMAGE_COMMAND11": "Card/COMMAND11",
    "IMAGE_DEBUG": "Card/DEBUG",
    "IMAGE_FATHER": "Card/FATHER",
    "IMAGE_MOTHER": "Card/MOTHER",
    "IMAGE_OVER": "Card/OVER",
    "IMAGE_SHELF": "Card/SHELF",
    "IMAGE_TRUSH": "Card/TRUSH",
    "CARD_ACTION": "CardBg/ACTION",
    "CARD_BEAST": "CardBg/BEAST",
    "CARD_BIND": "CardBg/BIND",
    "CARD_DANGER": "CardBg/DANGER",
    "CARD_FAINT": "CardBg/FAINT",
    "SIGN_HOLD": "CardBg/HOLD",
    "CARD_INFO": "CardBg/INFO",
    "CARD_INJURY": "CardBg/INJURY",
    "CARD_ITEM": "CardBg/ITEM",
    "CARD_LARGE": "CardBg/LARGE",
    "CARD_NORMAL": "CardBg/NORMAL",
    "CARD_OPTION": "CardBg/OPTION",
    "CARD_PARALY": "CardBg/PARALY",
    "SIGN_PENALTY": "CardBg/PENALTY",
    "CARD_PETRIF": "CardBg/PETRIF",
    "SIGN_PREMIER": "CardBg/PREMIER",
    "SIGN_RARE": "CardBg/RARE",
    "CARD_REVERSE": "CardBg/REVERSE",
    "CARD_SKILL": "CardBg/SKILL",
    "CARD_SLEEP": "CardBg/SLEEP",
    "TABLE_CAUTION": "Dialog/CAUTION",
    "CHECK_COMPLETE": "Dialog/COMPLETE",
    "CHECK_FIXED": "Dialog/FIXED",
    "CHECK_FOLDER": "Dialog/FOLDER",
    "CHECK_INVISIBLE": "Dialog/INVISIBLE",
    "CHECK_LINK": "Dialog/LINK",
    "TABLE_PAD": "Dialog/PAD",
    "CHECK_PLAYING": "Dialog/PLAYING",
    "CHECK_SELECT": "Dialog/SELECT",
    "TABLE_STATUS": "Dialog/STATUS",
    "MARK_STATUS0": "Dialog/STATUS0",
    "MARK_STATUS1": "Dialog/STATUS1",
    "MARK_STATUS2": "Dialog/STATUS2",
    "MARK_STATUS3": "Dialog/STATUS3",
    "MARK_STATUS4": "Dialog/STATUS4",
    "MARK_STATUS5": "Dialog/STATUS5",
    "MARK_STATUS6": "Dialog/STATUS6",
    "MARK_STATUS7": "Dialog/STATUS7",
    "MARK_STATUS8": "Dialog/STATUS8",
    "MARK_STATUS9": "Dialog/STATUS9",
    "MARK_STATUS10": "Dialog/STATUS10",
    "MARK_STATUS11": "Dialog/STATUS11",
    "MARK_STATUS12": "Dialog/STATUS12",
    "MARK_STATUS13": "Dialog/STATUS13",
    "CHECK_UTILITY": "Dialog/UTILITY",
    "FONT_ANGRY": "Font/ANGRY",
    "FONT_CLUB": "Font/CLUB",
    "FONT_DIAMOND": "Font/DIAMOND",
    "FONT_EASY": "Font/EASY",
    "FONT_FLY": "Font/FLY",
    "FONT_GRIEVE": "Font/GRIEVE",
    "FONT_HEART": "Font/HEART",
    "FONT_JACK": "Font/JACK",
    "FONT_KISS": "Font/KISS",
    "FONT_LAUGH": "Font/LAUGH",
    "FONT_NIKO": "Font/NIKO",
    "FONT_ONSEN": "Font/ONSEN",
    "FONT_PUZZLE": "Font/PUZZLE",
    "FONT_QUICK": "Font/QUICK",
    "FONT_SPADE": "Font/SPADE",
    "FONT_WORRY": "Font/WORRY",
    "FONT_X": "Font/X",
    "FONT_ZAP": "Font/ZAP",
    "TITLE_CARD1": "Other/TITLE_CARD1",
    "TITLE_CARD2": "Other/TITLE_CARD2",
    "TITLE_CELL1": "Other/TITLE_CELL1",
    "TITLE_CELL2": "Other/TITLE_CELL2",
    "TITLE_CELL3": "Other/TITLE_CELL3",
    "TITLE_SHADOW": "Other/TITLE_SHADOW",
    "TITLE_VERSION": "Other/TITLE_VERSION",
    "SCREENSHOT_HEADER": "Other/SCREENSHOT_HEADER",
    "STATUS_BODY0": "Status/BODY0",
    "STATUS_BODY1": "Status/BODY1",
    "STATUS_DOWN0": "Status/DOWN0",
    "STATUS_DOWN1": "Status/DOWN1",
    "STATUS_DOWN2": "Status/DOWN2",
    "STATUS_DOWN3": "Status/DOWN3",
    "STATUS_LIFE": "Status/LIFE",
    "STATUS_LIFEBAR": "Status/LIFEBAR",
    "STATUS_LIFEGUAGE": "Status/LIFEGUAGE",
    "STATUS_MAGIC0": "Status/MAGIC0",
    "STATUS_MAGIC1": "Status/MAGIC1",
    "STATUS_MAGIC2": "Status/MAGIC2",
    "STATUS_MAGIC3": "Status/MAGIC3",
    "STATUS_MIND0": "Status/MIND0",
    "STATUS_MIND1": "Status/MIND1",
    "STATUS_MIND2": "Status/MIND2",
    "STATUS_MIND3": "Status/MIND3",
    "STATUS_MIND4": "Status/MIND4",
    "STATUS_MIND5": "Status/MIND5",
    "STATUS_SUMMON": "Status/SUMMON",
    "CHECK_TARGET": "Status/TARGET",
    "STATUS_UP0": "Status/UP0",
    "STATUS_UP1": "Status/UP1",
    "STATUS_UP2": "Status/UP2",
    "STATUS_UP3": "Status/UP3",
    "STONE_HAND0": "Stone/HAND0",
    "STONE_HAND1": "Stone/HAND1",
    "STONE_HAND2": "Stone/HAND2",
    "STONE_HAND3": "Stone/HAND3",
    "STONE_HAND4": "Stone/HAND4",
    "STONE_HAND5": "Stone/HAND5",
    "STONE_HAND6": "Stone/HAND6",
    "STONE_HAND7": "Stone/HAND7",
    "STONE_HAND8": "Stone/HAND8",
    "STONE_HAND9": "Stone/HAND9",
    "SYMBOL_SKILL": "Button/SKILL",
    "SYMBOL_ITEM": "Button/ITEM",
    "SYMBOL_BEAST": "Button/BEAST",
    "SYMBOL_BACKPACK": "Button/PERSONAL",
}
IMGTBL_C = {
    "IMAGE_ACTION1": "Card/ACTION1",
    "IMAGE_ACTION2": "Card/ACTION2",
    "IMAGE_ACTION3": "Card/ACTION3",
    "IMAGE_ACTION4": "Card/ACTION4",
    "IMAGE_ACTION5": "Card/ACTION5",
    "IMAGE_ACTION6": "Card/ACTION6",
    "IMAGE_ACTION7": "Card/ACTION7",
    "IMAGE_ACTION9": "Card/ACTION9",
    "IMAGE_ALARM": "Card/ALARM",
    "IMAGE_BATTLE": "Card/BATTLE",
    "IMAGE_COMMAND0": "Card/COMMAND0",
    "IMAGE_COMMAND1": "Card/COMMAND1",
    "IMAGE_COMMAND2": "Card/COMMAND2",
    "IMAGE_COMMAND3": "Card/COMMAND3",
    "IMAGE_COMMAND4": "Card/COMMAND4",
    "IMAGE_COMMAND5": "Card/COMMAND5",
    "IMAGE_COMMAND6": "Card/COMMAND6",
    "IMAGE_COMMAND7": "Card/COMMAND7",
    "IMAGE_COMMAND8": "Card/COMMAND8",
    "IMAGE_COMMAND9": "Card/COMMAND9",
    "IMAGE_COMMAND10": "Card/COMMAND10",
    "IMAGE_COMMAND11": "Card/COMMAND11",
    "IMAGE_DEBUG": "Card/DEBUG",
    "IMAGE_FATHER": "Card/FATHER",
    "IMAGE_MOTHER": "Card/MOTHER",
    "IMAGE_OVER": "Card/OVER",
    "IMAGE_SHELF": "Card/SHELF",
    "IMAGE_TRUSH": "Card/TRUSH",
    "IMAGE_ACTION0": "Card/ACTION0",
}
CURTBL = {
    "CURSOR_BACK": "Cursor/CURSOR_BACK",
    "CURSOR_DRIVER": "Cursor/CURSOR_DRIVER",
    "CURSOR_FINGER": "Cursor/CURSOR_FINGER",
    "CURSOR_FORE": "Cursor/CURSOR_FORE",
}


class Converter(threading.Thread):
    def __init__(self, exe: str) -> None:
        threading.Thread.__init__(self)

        self.maximum = 100
        self.curnum = 0
        self.message = "変換を開始しています..."
        self.failure = False
        self.complete = False
        self.errormessage = ""

        self.res: Optional[win32res.Win32Res] = None
        self.version = (1, 2, 8, 0)
        self.init(exe)

    def __del__(self) -> None:
        self.dispose()

    def dispose(self) -> None:
        if self.res:
            self.res.dispose()

    def init(self, exe: str) -> None:
        if self.res:
            self.res.dispose()
            self.res = None

        self.exe = exe
        if self.exe:
            with open(self.exe, "rb") as f:
                self.exebinary = f.read()
                f.close()

            self.res = cw.skin.win32res.Win32Res(self.exe)
            version_rc = self.res.get_rcdata(cw.skin.win32res.RT_VERSION, 1)
            if not version_rc:
                raise Exception()
            version_t = struct.Struct("<HHHH").unpack(version_rc[48:56])
            self.version = (version_t[1], version_t[0], version_t[3], version_t[2])

        self.datadir = self.find_datadir()
        self.scenariodir = self.find_scenariodir()
        self.yadodir = self.find_yadodir()
        self.skintype = self.find_type()
        self.initialcash = self.find_initialcash()

        self.data = cw.data.xml2etree("Data/SkinBase/Skin.xml")
        self.data.find_exists("Property/Name").text = self.find_skinname()
        self.data.find_exists("Property/Type").text = self.skintype
        self.data.find_exists("Property/Author").text = self.find_author()
        self.data.find_exists("Property/Description").text = cw.util.encodewrap(self.find_description())
        self.data.find_exists("Property/InitialCash").text = str(self.initialcash)

        self.actioncard = self._get_resources("ActionCard")
        self.gameover = self._get_resources("GameOver")
        self.scenario = self._get_resources("Scenario")
        self.title = self._get_resources("Title")
        self.yado = self._get_resources("Yado")
        self.specialcard = self._get_resources("SpecialCard")

        self._get_features()
        self._get_sounds()
        self._get_messages()
        self._get_cards()
        self.adventurersinn: Optional[str] = None
        self._get_bgs()
        self.partyinfo_res: Optional[str] = None
        self._get_partyinfo()

    def _get_resources(self, dpath: str) -> Dict[str, cw.data.CWPyElementTree]:
        dpath = cw.util.join_paths("Data/SkinBase/Resource/Xml/", dpath)
        rsrc = {}
        for path in os.listdir(dpath):
            if path.lower().endswith(".xml"):
                name = cw.util.splitext(path)[0]
                path = cw.util.join_paths(dpath, path)
                rsrc[name] = cw.data.xml2etree(path)
        return rsrc

    def _write_data(self, dpath: str, table: Dict[str, cw.data.CWPyElementTree]) -> None:
        for data in list(table.values()):
            data.fpath = cw.util.join_paths(dpath, cw.util.relpath(data.fpath, "Data/SkinBase/"))
            data.write_file()

    def find_skinname(self) -> str:
        if self.exe:
            exebasename = os.path.basename(self.exe)
            return cw.util.splitext(exebasename)[0]
        else:
            return "Default"

    def find_description(self) -> str:
        if self.exe:
            exebasename = os.path.basename(self.exe)
            return ("%sをベースに自動生成したスキン。") % exebasename
        else:
            return ""

    def find_datadir(self) -> str:
        if self.exe and ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            key = b"\\Midi\\DefReset.mid"
            index = self.exebinary.find(key)
            try:
                return str(self.exebinary[index - 4:index], cw.MBCS)
            except Exception:
                pass
        return "Data"

    def find_scenariodir(self) -> str:
        if self.exe and ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            key = b"\0\\\0\\\0\\Summary.wsm\0\\\0\\\0.wid\0"
            index = self.exebinary.find(key)
            try:
                index = index + len(key)
                return str(self.exebinary[index:index + 8], cw.MBCS)
            except Exception:
                pass
        return "Scenario"

    def find_yadodir(self) -> str:
        if self.exe and ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            key = b"\\\0\\Environment.wyd\0"
            index = self.exebinary.find(key)
            try:
                index = index + len(key)
                return str(self.exebinary[index - len(key) - 4:index - len(key)], cw.MBCS)
            except Exception:
                pass
        return "Yado"

    def find_type(self) -> str:
        if self.exe:
            fname = os.path.basename(self.exe).lower()
            fname = cw.util.splitext(fname)[0]
            if fname == "s_c_wirth":
                return "School"
            elif fname == "modernwirth":
                return "Modern"
            elif fname == "darkwirth":
                return "Monsters"
            elif fname == "oedowirth":
                return "Oedo"
            elif 0 <= os.path.dirname(self.exe).lower().find("sfv"):
                return "ScienceFiction"
        return "MedievalFantasy"

    def find_author(self) -> str:
        return ""

    def find_initialcash(self) -> int:
        prop = cw.header.GetProperty("Data/SkinBase/Skin.xml")
        cash = int(prop.properties.get("InitialCash", "4000"))
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return cash
        if len(self.exebinary) < 0x31d97 + 4:
            return cash
        return struct.unpack("<I", self.exebinary[0x31d97:0x31d97 + 4])[0]

    def _get_features(self) -> None:
        # バイナリ断片を手がかりにして特性値を探す。
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        assert self.res
        key = b"TStatusItem\x81\x89"  # "TStatusItem♂"
        index = self.exebinary.find(key) + len(key) - len("\x81\x89")

        physical = struct.Struct("<hhhhhh")
        mental = struct.Struct("<hhhhh")

        try:
            def set_params(data: cw.data.CWPyElement, index: int, isnature: bool,
                           slist: Tuple[str, str, str, str, str] = ("aggressive", "cautious", "brave",
                                                                    "cheerful", "trickish"),
                           sperb: float = 2.0) -> int:
                # 特性名
                n = self.exebinary[index:index + 20]
                index += 20
                i = n.find(b"\0")
                if 0 <= i:
                    name = n[:i]
                else:
                    name = n
                data.find_exists("./Name").text = str(name, cw.MBCS).strip(" 　")

                # 身体能力
                p = physical.unpack(self.exebinary[index:index + 2 * 6])
                index += 2 * 6
                e = data.find_exists("./Physical")
                if isnature:
                    e.set("dex", str(p[0] - 6))
                    e.set("agl", str(p[1] - 6))
                    e.set("int", str(p[2] - 6))
                    e.set("str", str(p[3] - 6))
                    e.set("vit", str(p[4] - 6))
                    e.set("min", str(p[5] - 6))
                else:
                    e.set("dex", str(p[0]))
                    e.set("agl", str(p[1]))
                    e.set("int", str(p[2]))
                    e.set("str", str(p[3]))
                    e.set("vit", str(p[4]))
                    e.set("min", str(p[5]))

                # 精神能力
                p = mental.unpack(self.exebinary[index:index + 2 * 5])
                index += 2 * 5
                e = data.find_exists("./Mental")
                e.set(slist[0], str(p[0] / sperb))
                e.set(slist[1], str(p[3] / sperb))
                e.set(slist[2], str(p[2] / sperb))
                e.set(slist[3], str(p[1] / sperb))
                e.set(slist[4], str(p[4] / sperb))

                return index

            key = b"\x00\x49\x4D\x41\x47\x45\x5F\x46\x41\x54\x48\x45\x52\x00\x49\x4D\x41\x47\x45\x5F\x4D\x4F" \
                  b"\x54\x48\x45\x52\x00\x81\x40\x81\x40\x81\x40\x81\x40\x81\x40\x81\x40\x81\x40\x81\x40\x00" \
                  b"\x00\x81\x51\x00\x81\x51\x00\x81\x51\x00\x81\x51\x00\x81\x40\x00"
            index2 = self.exebinary.find(key)
            if 0 <= index2:
                index2 += len(key)
                # 大人に付加される「熟練」クーポン
                skillful, index2 = self._get_text(index2)
                e = self.data.find("Periods/Period[3]/Coupons/Coupon")
                if e is not None:
                    e.text = skillful
                # 老人に付加される「老獪」クーポン
                foxy, index2 = self._get_text(index2)
                e = self.data.find("Periods/Period[4]/Coupons/Coupon")
                if e is not None:
                    e.text = foxy

            for e in self.data.getfind("Sexes"):
                index = set_params(e, index, False)
            for e in self.data.getfind("Periods"):
                index = set_params(e, index, False)

            # 使用されていない年代「古老」を飛ばす
            index += 20 + 2 * 6 + 2 * 5
            for e in self.data.getfind("Natures"):
                index = set_params(e, index, True)
            for e in self.data.getfind("Makings"):
                index = set_params(e, index, False)

            # デバグ宿で簡易生成を行う際の能力型
            for e in self.data.getfind("SampleTypes"):
                index = set_params(e, index, True, sperb=1.0)

            # 型の派生元を設定
            # 英明型 <- 標準型,万能型
            e = self.data.find_exists("Natures/Nature[8]/BaseNatures/BaseNature[1]")
            e.text = self.data.find_exists("Natures/Nature[1]/Name").text
            e = self.data.find_exists("Natures/Nature[8]/BaseNatures/BaseNature[2]")
            e.text = self.data.find_exists("Natures/Nature[2]/Name").text
            # 無双型 <- 勇将型,豪傑型
            e = self.data.find_exists("Natures/Nature[9]/BaseNatures/BaseNature[1]")
            e.text = self.data.find_exists("Natures/Nature[3]/Name").text
            e = self.data.find_exists("Natures/Nature[9]/BaseNatures/BaseNature[2]")
            e.text = self.data.find_exists("Natures/Nature[4]/Name").text
            # 天才型 <- 知将型,策士型
            e = self.data.find_exists("Natures/Nature[10]/BaseNatures/BaseNature[1]")
            e.text = self.data.find_exists("Natures/Nature[5]/Name").text
            e = self.data.find_exists("Natures/Nature[10]/BaseNatures/BaseNature[2]")
            e.text = self.data.find_exists("Natures/Nature[6]/Name").text

            # 解説文
            entrydlg = self.res.get_tpf0form(b"TENTRYDLG")
            if entrydlg:
                typesheet = win32res.find_res(entrydlg, (b"EntryDlg", b"PageControl", b"TypeSheet"),
                                              win32res.ResTable())
                # 標準型
                e = self.data.find_exists("Natures/Nature[1]/Description")
                e.text = win32res.find_res(typesheet, (b"Type3Label", b"Caption"), e.text)
                # 万能型
                e = self.data.find_exists("Natures/Nature[2]/Description")
                e.text = win32res.find_res(typesheet, (b"Type2Label", b"Caption"), e.text)
                # 勇将型
                e = self.data.find_exists("Natures/Nature[3]/Description")
                e.text = win32res.find_res(typesheet, (b"Type1Label", b"Caption"), e.text)
                # 豪傑型
                e = self.data.find_exists("Natures/Nature[4]/Description")
                e.text = win32res.find_res(typesheet, (b"Type0Label", b"Caption"), e.text)
                # 知将型
                e = self.data.find_exists("Natures/Nature[5]/Description")
                e.text = win32res.find_res(typesheet, (b"Type4Label", b"Caption"), e.text)
                # 策士型
                e = self.data.find_exists("Natures/Nature[6]/Description")
                e.text = win32res.find_res(typesheet, (b"Type5Label", b"Caption"), e.text)
            else:
                print("TENTRYDLG")
        except Exception:
            cw.util.print_ex()

    def _get_sounds(self) -> None:
        # バイナリ断片を手がかりにして音声ファイル名を探す。
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        try:
            sounds = self.data.find_exists("Sounds")

            def get_keybefore(e: cw.data.CWPyElement, key: bytes, length: int, less: int = 0) -> None:
                index = self.exebinary.find(key)
                if 0 <= index:
                    index -= less
                    e.text = str(self.exebinary[index - length:index], cw.MBCS)

            def get_keyafter(e: cw.data.CWPyElement, key: bytes, length: int, than: int = 0) -> None:
                index = self.exebinary.find(key)
                if 0 <= index:
                    index += len(key)
                    index += than
                    e.text = str(self.exebinary[index:index + length], cw.MBCS)

            # システム・エラー
            # ".wav\0は、行動不能です。"
            key = b".wav\0\x82\xCD\x81\x41\x8D\x73\x93\xAE\x95\x73\x94\x5C\x82\xC5\x82\xB7\x81\x42\x00"
            get_keybefore(sounds[0], key, 16)
            # システム・クリック
            get_keybefore(sounds[1], key, 18, less=16 + 5)
            # システム・シグナル
            # ".wav\0本アプリケーションは『小さいフォント』に対応しています。"
            key = b".wav\0\x96\x7B\x83\x41\x83\x76\x83\x8A\x83\x50\x81\x5B\x83\x56\x83\x87\x83\x93\x82\xCD" \
                  b"\x81\x77\x8F\xAC\x82\xB3\x82\xA2\x83\x74\x83\x48\x83\x93\x83\x67\x81\x78\x82\xC9\x91\xCE" \
                  b"\x89\x9E\x82\xB5\x82\xC4\x82\xA2\x82\xDC\x82\xB7\x81\x42"
            get_keybefore(sounds[2], key, 18)
            # システム・初期化
            get_keybefore(sounds[6], key, 16, less=18 + 8)
            # システム・回避
            # "死者有効\0抵抗有効\0"
            key = b"\x8E\x80\x8E\xD2\x97\x4C\x8C\xF8\x00\x92\xEF\x8D\x52\x97\x4C\x8C\xF8\x00"
            get_keyafter(sounds[3], key, 14)
            # システム・無効
            get_keyafter(sounds[11], key, 14, than=14 + 5)
            # システム・改ページ
            key = b".wav\0CHECK_FIXED\0CHECK_TARGET\0"
            get_keybefore(sounds[4], key, 18)
            # システム・収穫
            # "TMainWindow\0TBookDlg\0状態\0"
            key = b".wav\0TMainWindow\0TBookDlg\0\x8F\xF3\x91\xD4\x00"
            get_keybefore(sounds[5], key, 14)
            # システム・戦闘
            key = b".wav\0Encounter\0\x30\0\0Round\x20\0"
            get_keybefore(sounds[7], key, 14)
            # システム・装備
            # "\0＿２\0＿３\0＿４\0＿５\0＿６\0異常発生\0"
            key = b"\x00\x81\x51\x82\x51\x00\x81\x51\x82\x52\x00\x81\x51\x82\x53\x00\x81\x51\x82\x54\x00\x81" \
                  b"\x51\x82\x55\x00\x88\xD9\x8F\xED\x94\xAD\x90\xB6\x00"
            get_keyafter(sounds[8], key, 14)
            # 効果（混乱）
            get_keyafter(sounds[12], key, 12, than=41)
            # 効果（呪縛）
            key = b"\x53\x49\x47\x4E\x5F\x50\x45\x4E\x41\x4C\x54\x59\x00\x53\x49\x47\x4E\x5F\x52\x41\x52\x45" \
                  b"\x00\x53\x49\x47\x4E\x5F\x50\x52\x45\x4D\x49\x45\x52\x00\x00"
            get_keyafter(sounds[13], key, 12, than=75)
            # システム・逃走
            key = b".wav\0TITLE_CARD1\0TITLE_CARD1\0TITLE_CARD2\0"
            get_keybefore(sounds[9], key, 14, less=16 + 5)
            # システム・破棄
            # "\0を捨てます。よろしいですか？\0"
            key = b"\x00\x82\xF0\x8E\xCC\x82\xC4\x82\xDC\x82\xB7\x81\x42\x82\xE6\x82\xEB\x82\xB5\x82\xA2\x82" \
                  b"\xC5\x82\xB7\x82\xA9\x81\x48\x00"
            get_keyafter(sounds[10], key, 14)
        except Exception:
            cw.util.print_ex()

    def _get_partyinfo(self) -> None:
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        try:
            key = b"\0IMAGE_COMMAND3\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key) + 98
                s = str(self.exebinary[index:index + 12], cw.MBCS)
                if s != "IMAGE_FATHER":
                    self.partyinfo_res = s
        except Exception:
            cw.util.print_ex()

    def _get_cards(self) -> None:
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        try:
            key = b"\0CARD_SKILL\0CARD_ACTION\0IMAGE_ACTION\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)

                # アクションカード
                # 名前・解説・音声1・音声2・標準キーコード
                # の順で文字列を取得する
                def get_actioncard(cardkey: str, index: int, keycodenum: int) -> int:
                    name, index = self._get_text(index, True)
                    desc, index = self._get_text(index, True)
                    sound1, index = self._get_text(index)
                    sound2, index = self._get_text(index)
                    keycodes = []
                    for _i in range(0, keycodenum):
                        keycode, index = self._get_text(index)
                        keycodes.append(keycode)
                    data = self.actioncard[cardkey]
                    data.find_exists("Property/Name").text = name
                    data.find_exists("Property/Description").text = desc
                    data.find_exists("Property/SoundPath").text = sound1
                    data.find_exists("Property/SoundPath2").text = sound2
                    data.find_exists("Property/KeyCodes").text = cw.util.encodewrap("\n".join(keycodes))
                    return index

                # カード交換
                index = get_actioncard("00_Exchange", index, 1)
                # 攻撃
                index = get_actioncard("01_Attack", index, 1)
                # 渾身の一撃
                index = get_actioncard("02_PowerfulAttack", index, 1)
                # 会心の一撃
                index = get_actioncard("03_CriticalAttack", index, 1)
                # フェイント
                index = get_actioncard("04_Feint", index, 2)
                # 防御
                index = get_actioncard("05_Defense", index, 1)
                # 見切り
                index = get_actioncard("06_Distance", index, 1)
                # 混乱
                index = get_actioncard("-1_Confuse", index, 1)
                # 逃走
                index = get_actioncard("07_Runaway", index, 1)

            key = b".wav\0Encounter\0\x30\0\0Round\x20\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                # 特殊エリアのメニューカード
                # 名前、解説、イメージのリソース名
                # の順で文字列を取得する
                index += len(key)

                def get_menucard(area: Iterable[Tuple[cw.data.CWPyElementTree, int]], index: int) -> int:
                    name, index = self._get_text(index, True)
                    desc, index = self._get_text(index, True)
                    _image, index = self._get_text(index)
                    for data in area:
                        e = data[0].find_exists("MenuCards/*[%s]" % (data[1]))
                        e.find_exists("Property/Name").text = name
                        e.find_exists("Property/Description").text = desc
                    return index

                # スタート
                index = get_menucard([(self.title["01_Title"], 1)], index)
                # 終了
                index = get_menucard([(self.title["01_Title"], 2)], index)
                # 宿帳を開く
                index = get_menucard([(self.yado["01_Yado"], 1),
                                      (self.yado["02_Yado2"], 1),
                                      (self.yado["03_YadoInitial"], 1)], index)
                # 冒険の再開
                index = get_menucard([(self.yado["01_Yado"], 3),
                                      (self.yado["02_Yado2"], 3)], index)
                # 貼紙を見る
                index = get_menucard([(self.yado["02_Yado2"], 5)], index)
                # カード置き場
                index = get_menucard([(self.yado["01_Yado"], 4),
                                      (self.yado["02_Yado2"], 6)], index)
                # 荷物袋
                index = get_menucard([(self.scenario["-4_Camp"], 1),
                                      (self.yado["02_Yado2"], 7)], index)
                # 情報を見る
                index = get_menucard([(self.scenario["-4_Camp"], 2)], index)
                # 冒険の中断
                index = get_menucard([(self.scenario["-4_Camp"], 5),
                                      (self.yado["02_Yado2"], 10)], index)
                # 宿を出る
                index = get_menucard([(self.yado["01_Yado"], 6),
                                      (self.yado["03_YadoInitial"], 2)], index)
                # 仲間を外す
                index = get_menucard([(self.yado["02_Yado2"], 4)], index)
                # セーブ
                index = get_menucard([(self.scenario["-4_Camp"], 4),
                                      (self.yado["01_Yado"], 5),
                                      (self.yado["02_Yado2"], 9)], index)
                # アルバム
                index = get_menucard([(self.yado["01_Yado"], 2),
                                      (self.yado["02_Yado2"], 2)], index)
                # パーティ情報
                index = get_menucard([(self.scenario["-4_Camp"], 3),
                                      (self.yado["02_Yado2"], 8)], index)
                # 荷物袋(カード移動時)
                index = get_menucard([(self.scenario["-5_TradeArea"], 1),
                                      (self.yado["-2_TradeArea2"], 2)], index)
                # カード置場(カード移動時)
                index = get_menucard([(self.yado["-1_TradeArea"], 1),
                                      (self.yado["-2_TradeArea2"], 1)], index)
                # ごみ箱(カード移動時)
                index = get_menucard([(self.scenario["-5_TradeArea"], 2),
                                      (self.yado["-1_TradeArea"], 3),
                                      (self.yado["-2_TradeArea2"], 4)], index)
                # 売却(カード移動時)
                index = get_menucard([(self.yado["-1_TradeArea"], 2),
                                      (self.yado["-2_TradeArea2"], 3)], index)
                # 解散
                index = get_menucard([(self.yado["-3_PartyBreakup"], 1)], index)
        except Exception:
            cw.util.print_ex()

    def _get_bgs(self) -> None:
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        try:
            key = b"\0\0\0MapOfWirth.bmp\0\0.bmp\0.BMP\0MapOfWirth.bmp\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                # AdventurersInn.bmp
                # 妖魔バリアントで変更されている
                index += len(key)
                self.adventurersinn, index = self._get_text(index, True)
        except Exception:
            cw.util.print_ex()

    def _get_messages(self) -> None:
        if not self.exe or not ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
            return
        assert self.res
        try:
            # ゲームオーバー
            key = b"\0IMAGE_OVER\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                msg, index = self._get_text(index)
                goyado, index = self._get_text(index)
                load, index = self._get_text(index)
                end, index = self._get_text(index)

                data = self.gameover["01_GameOver"]
                # ゲームオーバー時のメッセージコンテント
                e = data.find_exists("Events/Event//Talk")
                e.find_exists("Text").text = cw.util.encodewrap("\n\n\n" + msg)
                e.find_exists("Contents/Post[1]").set("name", goyado)
                e.find_exists("Contents/Post[2]").set("name", load)
                e.find_exists("Contents/Post[4]").set("name", end)

            msgtable = {}

            # リソースからメッセージを取得
            rsrcmsgs: Dict[str, Optional[Union[bytes,
                                               Tuple[bytes, Tuple[str, str]],
                                               Tuple[bytes, Tuple[str, str], Tuple[str, str]]]]] = {
                "message": b"TCAUTIONDLG/CautionDlg/Caption",
                "decide": b"TBOOKDLG/BookDlg/PartyPanel/Party_OpenBtn/Caption",
                "yes": b"TCAUTIONDLG/CautionDlg/YesBtn/Caption",
                "no": b"TCAUTIONDLG/CautionDlg/NoBtn/Caption",
                "close": b"TCAUTIONDLG/CautionDlg/OkBtn/Caption",
                "cancel": b"TACTIONDLG/ActionDlg/CancelBtn/Caption",
                "coution": b"TREPAIRDLG/RepairDlg/RepairBTitle/Caption",
                "sex": b"TREPAIRDLG/RepairDlg/SexGroup/Caption",
                "age": b"TREPAIRDLG/RepairDlg/AgeGroup/Caption",
                "description": b"TBILLDLG/BillDlg/WorkPanel/Work_MemoBtn/Caption",
                "extension": b"TBILLDLG/BillDlg/yadoPanel/yado_EditBtn/Caption",
                "history": b"TSTATUSDLG/StatusDlg/ChannelPanel/CareerBtn/Caption",
                "status": b"TSTATUSDLG/StatusDlg/ChannelPanel/MultiBtn/Caption",
                "skills": b"TSTATUSDLG/StatusDlg/ChannelPanel/SkillBtn/Caption",
                "items": b"TSTATUSDLG/StatusDlg/ChannelPanel/ItemBtn/Caption",
                "beasts": b"TSTATUSDLG/StatusDlg/ChannelPanel/BeastBtn/Caption",
                "delete": b"TBOOKDLG/BookDlg/MemberPanel/Member_DeleteBtn/Caption",
                "information": b"TBOOKDLG/BookDlg/MemberPanel/Member_InfoBtn/Caption",
                "new": b"TBOOKDLG/BookDlg/MemberPanel/Member_EntryBtn/Caption",
                "add_member": b"TBOOKDLG/BookDlg/MemberPanel/Member_JoinBtn/Caption",
                "members": b"TBOOKDLG/BookDlg/PartyPanel/Party_MemberBtn/Caption",
                "create_base_title": b"TSTARTDLG/StartDlg/Caption",
                "create_base_message_1": b"TSTARTDLG/StartDlg/TitleLabel/Caption",
                "create_base_message_2": b"TSTARTDLG/StartDlg/NameLabel/Caption",
                "card_control": b"TCARDDLG/CardDlg/Caption",
                "send_to": b"TCARDDLG/CardDlg/TargetPanel/TargetLabel/Caption",
                "card_information": b"TCAPTIONDLG/CaptionDlg/Caption",
                "entry_title": b"TENTRYDLG/EntryDlg/Caption",
                "entry_message": b"TENTRYDLG/EntryDlg/PageControl/DefaultSheet/DefaultTitle/Caption",
                "design_title": b"TDESIGNDLG/DesignDlg/Caption",
                "edit_character_message": b"TDESIGNDLG/DesignDlg/TitleLabel/Caption",
                "entry_name": b"TDESIGNDLG/DesignDlg/NameLabel/Caption",
                "entry_image": b"TDESIGNDLG/DesignDlg/ImageLabel/Caption",
                "entry_comment": b"TDESIGNDLG/DesignDlg/CommentLabel/Caption",
                "entry_sex": b"TENTRYDLG/EntryDlg/PageControl/DefaultSheet/SexTitle/Caption",
                "entry_age": b"TENTRYDLG/EntryDlg/PageControl/DefaultSheet/AgeTitle/Caption",
                "entry_cancel": b"TENTRYDLG/EntryDlg/ButtonPanel/CancelBtn/Caption",
                "entry_decide": b"TENTRYDLG/EntryDlg/ButtonPanel/SaveBtn/Caption",
                "entry_next": b"TENTRYDLG/EntryDlg/ButtonPanel/ForeBtn/Caption",
                "entry_previous": b"TENTRYDLG/EntryDlg/ButtonPanel/BackBtn/Caption",
                "relation_title": b"TENTRYDLG/EntryDlg/PageControl/ParentSheet/ParentTitle/Caption",
                "relation_message": b"TENTRYDLG/EntryDlg/PageControl/ParentSheet/ParentLabel/Caption",
                "father": b"TENTRYDLG/EntryDlg/PageControl/ParentSheet/FatherTitle/Caption",
                "mother": b"TENTRYDLG/EntryDlg/PageControl/ParentSheet/MotherTitle/Caption",
                "consumption_ep": (b"TENTRYDLG/EntryDlg/PageControl/ParentSheet/FatherExtra/Caption",
                                   ("60", "%s"), ("120", "%s")),
                "nature_title": b"TENTRYDLG/EntryDlg/PageControl/TypeSheet/TypeTitle/Caption",
                "nature_message": b"TENTRYDLG/EntryDlg/PageControl/TypeSheet/TypeComment/Caption",
                "making_title": b"TENTRYDLG/EntryDlg/PageControl/MarkSheet/MarkTitle/Caption",
                "making_message": b"TENTRYDLG/EntryDlg/PageControl/MarkSheet/MarkLabel/Caption",
                "character_information": b"TSTATUSDLG/StatusDlg/Caption",
                "insufficiency_title": b"TREPAIRDLG/RepairDlg/Caption",
                "insufficiency_message": b"TREPAIRDLG/RepairDlg/CommentLabel/Caption",
                "instructions": b"TMEMODLG/MemoDlg/TargetPanel/Caption",
                "referencing_file": b"TMEMODLG/MemoDlg/TargetPanel/TargetLabel/Caption",
                "party_information": b"TPARTYDLG/PartyDlg/Caption",
                "party_money": b"TPARTYDLG/PartyDlg/MoneyLabel/Caption",
                "party_name": b"TPARTYDLG/PartyDlg/NameLabel/Caption",
                "table": b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/TableBtn/Caption",
                "camp": b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/CampBtn/Caption",
                "start_action": b"TMAINWINDOW/MainWindow/ButtonControl/BattleSheet/BattleBtn/Caption",
                "runaway": b"TMAINWINDOW/MainWindow/ButtonControl/BattleSheet/EscapeBtn/Caption",
                "round": (b"TMAINWINDOW/MainWindow/ButtonControl/BattleSheet/RoundPanel/Caption", ("00", "%s")),
                "skillcard": b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/SkillBtn/Hint",
                "itemcard": b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/ItemBtn/Hint",
                "beastcard": b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/BeastBtn/Hint",
            }
            if ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
                rsrcmsgs["desc_base_money"] = \
                    b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/VaultPanel/Hint"
                rsrcmsgs["desc_party_money"] = \
                    b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/PursePanel/Hint"
            else:
                rsrcmsgs["desc_base_money"] = \
                    b"TMAINWINDOW/MainWindow/BottomBar/ButtonControl/NormalSheet/VaultPanel/Hint"
                rsrcmsgs["desc_party_money"] = \
                    b"TMAINWINDOW/MainWindow/BottomBar/ButtonControl/NormalSheet/PursePanel/Hint"

            rcdata: Dict[bytes, win32res.ResTable] = {}
            table: Optional[Union[str, win32res.ResTable]]
            for key_s, path_l in rsrcmsgs.items():
                repls: Sequence[Tuple[str, str]] = []
                if isinstance(path_l, bytes):
                    path = path_l
                else:
                    assert isinstance(path_l, tuple)
                    repls = path_l[1:]
                    path = path_l[0]
                rsrcmsgs[key_s] = None
                path_seq = path.split(b"/")
                if path_seq[0] in rcdata:
                    table = rcdata[path_seq[0]]
                else:
                    table = self.res.get_tpf0form(path_seq[0])
                    if table:
                        rcdata[path_seq[0]] = table
                if table:
                    for i in range(1, len(path_seq)):
                        if not isinstance(table, win32res.ResTable):
                            table = None
                            break
                        if path_seq[i] in table.table:
                            table_u = table.table[path_seq[i]]
                            assert isinstance(table_u, (str, win32res.ResTable))
                            table = table_u
                        else:
                            table = None
                            break
                    if isinstance(table, str):
                        for repl in repls:
                            table = table.replace(repl[0], repl[1])
                        msgtable[key_s] = table.strip(" 　")
                    else:
                        print(path_seq)
                else:
                    print(path_seq)

            # バイナリ断片を手がかりにメッセージを取得
            # (key, 0=keyの前方を探す/1=後方を探す, index移動量, Prefix)
            cribs: Dict[str, Optional[Union[Tuple[bytes, int, int], Tuple[bytes, int, int, str]]]] = {
                "select_base_title": (b"\0IMAGE_COMMAND0\0IMAGE_DEBUG\0", 0, -8),
                "cards_hand": (b"\0TABLE_PAD\0\0Cap \0/\0IMAGE_COMMAND7\0IMAGE_COMMAND5\0IMAGE_COMMAND8\0/\0",
                               0, -104, "%s"),
                "cards_backpack":
                    (b"\0TABLE_PAD\0\0Cap \0/\0IMAGE_COMMAND7\0IMAGE_COMMAND5\0IMAGE_COMMAND8\0/\0", 0, -91),
                "cards_storehouse":
                    (b"\0TABLE_PAD\0\0Cap \0/\0IMAGE_COMMAND7\0IMAGE_COMMAND5\0IMAGE_COMMAND8\0/\0", 0, -59),
                "info_card": (b"\0TABLE_PAD\0\0Cap \0/\0IMAGE_COMMAND7\0IMAGE_COMMAND5\0IMAGE_COMMAND8\0/\0",
                              0, -23),
                "mode_show":
                    (b"\x00\x92\x86\x8E\x7E\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2"
                     b"\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00",
                     0, -57),
                "mode_move":
                    (b"\x00\x92\x86\x8E\x7E\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2"
                     b"\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00",
                     0, -44),
                "mode_use":
                    (b"\x00\x92\x86\x8E\x7E\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2"
                     b"\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00",
                     0, -31),
                "mode_battle":
                    (b"\x00\x92\x86\x8E\x7E\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2"
                     b"\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00\x95\xC2\x82\xB6\x82\xE9\x00",
                     0, -18),
                "send_to_manual":
                    (b"\0BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_UP\0BUTTON_DOWN\0BUTTON_RSMALL\0BUTTON_LSMALL\0",
                     1, 0),
                "send_to_storehouse":
                    (b"\0BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_UP\0BUTTON_DOWN\0BUTTON_RSMALL\0BUTTON_LSMALL\0",
                     1, 9),
                "send_to_backpack":
                    (b"\0BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_UP\0BUTTON_DOWN\0BUTTON_RSMALL\0BUTTON_LSMALL\0",
                     1, 20),
                "send_to_shelf":
                    (b"\0BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_UP\0BUTTON_DOWN\0BUTTON_RSMALL\0BUTTON_LSMALL\0",
                     1, 27),
                "send_to_trush":
                    (b"\0BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_UP\0BUTTON_DOWN\0BUTTON_RSMALL\0BUTTON_LSMALL\0",
                     1, 32),
                "select_battle_action":
                    (b"\x00\x8D\x73\x93\xAE\x8A\x4A\x8E\x6E\x00\x49\x4D\x41\x47\x45\x5F\x42\x41\x54\x54\x4C\x45"
                     b"\x00\x93\xA6\x82\xB0\x82\xE9\x00",
                     0, -12),
                "lost_coupon_1":
                    (b"\x81\x46\x83\x8C\x83\x78\x83\x8B\x95\xE2\x90\xB3\x92\x86\x00\x81\x51\x8F\xC1\x96\xC5\x97"
                     b"\x5C\x96\xF1\x00\x81\x51\x8E\x80\x96\x53\x00",
                     1, 0),
                "currency":
                    (b"\x96\x7B\x83\x41\x83\x76\x83\x8A\x83\x50\x81\x5B\x83\x56\x83\x87\x83\x93\x82\xCD\x81\x77"
                     b"\x8F\xAC\x82\xB3\x82\xA2\x83\x74\x83\x48\x83\x93\x83\x67\x81\x78\x82\xC9\x91\xCE\x89\x9E"
                     b"\x82\xB5\x82\xC4\x82\xA2\x82\xDC\x82\xB7\x81\x42\x89\xE6\x96\xCA\x82\xCC\x83\x76\x83\x8D"
                     b"\x83\x70\x83\x65\x83\x42\x82\xF0\x8A\x4A\x82\xAB\x81\x41\x83\x74\x83\x48\x83\x93\x83\x67"
                     b"\x83\x54\x83\x43\x83\x59\x82\xF0\x81\x77\x8F\xAC\x82\xB3\x82\xA2\x83\x74\x83\x48\x83\x93"
                     b"\x83\x67\x81\x78\x82\xC9\x8E\x77\x92\xE8\x82\xB5\x82\xC4\x83\x51\x81\x5B\x83\x80\x82\xF0"
                     b"\x8D\xC4\x8A\x4A\x82\xB5\x82\xC4\x82\xAD\x82\xBE\x82\xB3\x82\xA2\x81\x42\x00",
                     1, 187, "%s"),
            }
            for key_s, crib in cribs.items():
                assert crib
                cribs[key_s] = None
                index = self.exebinary.find(crib[0])
                if 0 <= index:
                    if crib[1] == 1:
                        # 後方
                        index += len(crib[0])
                    # 位置調整
                    index += crib[2]
                    s, index = self._get_text(index)
                    if len(crib) >= 4:
                        # BUG: error: Tuple index out of range (mypy 0.782)
                        s = typing.cast(Tuple[bytes, int, int, str], crib)[3] + s
                    msgtable[key_s] = s.strip(" 　")

            # 一分テキストの調整
            for key_s in ("cards_backpack", "cards_storehouse", "info_card"):
                if key_s in msgtable:
                    s = msgtable[key_s]
                    index = s.find(" - ")
                    if 0 <= index:
                        index += len(" - ")
                        msgtable[key_s] = s[index:]

            # まとまったテキストを探す
            msglist1 = []
            key = b"\\Midi\\DefReset.mid\0\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(71):
                    s, index = self._get_text(index, True)
                    msglist1.append(s)

            msglist2 = []
            key = b"\0Male\0Female\0Child\0Young\0Adult\0Old\0BUTTON_LMOVE\0BUTTON_RMOVE\0BUTTON_LMOVE\0"\
                  b"BUTTON_RMOVE\0BUTTON_LMOVE\0BUTTON_RMOVE\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(50):
                    s, index = self._get_text(index, True)
                    msglist2.append(s)

            msglist3 = []
            key = b"\0IMAGE_COMMAND0\0IMAGE_DEBUG\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(62):
                    s, index = self._get_text(index, True)
                    msglist3.append(s)

            msglist4 = []
            key = b"\x00\x81\x69\x00\x81\x6A\x00\x8D\x73\x93\xAE\x97\xCD\x00\x89\xF1\x94\xF0\x97\xCD\x00\x92"\
                  b"\xEF\x8D\x52\x97\xCD\x00\x96\x68\x8C\xE4\x97\xCD\x00\x8F\xAC\x00\x92\x86\x00\x91\xE5\x00"\
                  b"\x8D\xC5\x91\xE5\x00\x83\x7B\x81\x5B\x83\x69\x83\x58\x00"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(30):
                    s, index = self._get_text(index, True)
                    msglist4.append(s)

            msglist5 = []
            key = b"\\Table\\Book.bmp\0 / \0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(100):
                    s, index = self._get_text(index, True)
                    msglist5.append(s)

            msglist6 = []
            key = b"\0CARD_REVERSE\0\x81\x4F\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(86):
                    s, index = self._get_text(index, True)
                    msglist6.append(s)

            msglist7 = []
            key = b"\0IMAGE_DEBUG\0IMAGE_COMMAND0\0Party\0.wpt\0.wpt\0.wpl\0.wpt\0.wpt\0.wpl"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(8):
                    s, index = self._get_text(index, True)
                    msglist7.append(s)

            msglist8 = []
            key = b"\0\x81\x46\x82\x71\0\0\0\0\0\0Default\0"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(8):
                    s, index = self._get_text(index, True)
                    msglist8.append(s)

            msglist9 = []
            key = b"\xD8\xFF\xFF\xFF\x00\x00\x05\x00\x00\x00\x00\x00\x84\x33\x4F\x00"
            index = self.exebinary.find(key)
            if 0 <= index:
                index += len(key)
                for i in range(19):
                    s, index = self._get_text(index, True)
                    msglist9.append(s)

            cribs2 = {
                "new_base": msglist3[3],
                "adventurers": msglist3[1],
                "confirm_sell": "%s" + msglist1[62] + "%s" + msglist1[63],
                "confirm_dump": "%s" + msglist1[67],
                "error_hand_be_full": "%s" + msglist1[59],
                "error_sell_premier_card": msglist1[61],
                "error_dump_premier_card": "%s" + msglist1[66],
                "confirm_use_card": "%s" + msglist1[57],
                "inactive": "%s" + msglist1[28],
                "selected_penalty": msglist1[30],
                "general_father": msglist2[21],
                "general_mother": msglist2[30],
                "entry_cancel_message": msglist2[7],
                "entry_decide_message": "%s" + msglist2[5],
                "edit_design": msglist4[21],
                "regulate_level": msglist4[22],
                "regulate_level_title": msglist4[29],
                "card_number": msglist4[6] + " %s / %s",
                "select_member_title": msglist5[0],
                "album": msglist5[72],
                "confirm_delete_character": msglist5[50] + "%s" + msglist5[51],
                "confirm_delete_character_in_album": "%s" + msglist5[98],
                "character_level": msglist5[2],
                "character_class": msglist5[3],
                "character_age": msglist5[9] + ":%s",
                "character_sex": msglist5[14] + ":%s",
                "character_ep": msglist5[16] + ":%s",
                "character_history": "【" + msglist5[21] + "】",
                "history_etc": msglist5[20],
                "confirm_grow": msglist5[32] + "%s" + msglist5[33] +
                                msglist5[34].replace(msglist6[2][1:], "%s").replace(msglist6[3][1:], "%s") +
                                msglist5[38],
                "confirm_die": msglist5[32] + "%s" + msglist5[33] + msglist5[37] + msglist5[38],
                "die_message": "%s" + msglist5[44],
                "default_party_name": "%s" + msglist5[24],
                "resume_adventure": msglist5[64],
                "select_scenario_title": msglist3[20],
                "target_level_1": msglist3[49] + "%s",
                "target_level_2": msglist3[49] + "%s ～ %s",
                "contents": msglist3[61],
                "confirm_save": msglist1[52],
                "saved": msglist1[54],
                "confirm_go_title": msglist1[51],
                "confirm_quit": msglist1[50],
                "load_scenario_failure": msglist1[45],
                "f9_message": msglist1[40],
                "confirm_runaway": msglist1[13],
                "ok": msglist1[70],
                "adventurers_team": msglist5[66],
                "adventurers_money": msglist5[68] + " %s " + msglist5[69],
                "select_member_message": msglist8[0],
                "select_message": msglist8[3],
                "number_1_coupon": msglist6[17],
                "father_coupon": msglist7[2] + "%s",
                "mother_coupon": msglist7[3] + "%s",
                "lost_coupon_2": msglist5[41],
                "level_up": "\n\n\n#I" + msglist1[69],
                "extension_title": msglist9[2] + "%s" + msglist9[3],
            }
            for key_s, msg in cribs2.items():
                msgtable[key_s] = msg.strip(" 　")

            e_message = self.data.find_exists("Messages")
            for e in e_message:
                key_s = e.get("key")
                if key_s in msgtable:
                    # ベースからメッセージを変更
                    e.text = msgtable[key_s]

        except Exception:
            cw.util.print_ex()

    def _get_text(self, index: int, cutzero: bool = False) -> Tuple[str, int]:
        end = self.exebinary.find(b'\0', index)
        s = str(self.exebinary[index:end], cw.MBCS)
        index = end + 1
        if cutzero:
            while self.exebinary[index:index + 1] == b'\0':
                index += 1
        return s, index

    def run(self) -> None:
        """クラシックなエンジンからリソースを取り出し、新規スキンを生成する。"""
        self.curnum = 0
        self.message = "スキンのベースをコピー中..."

        dpath = self.data.gettext("Property/Name", "")
        dpath = cw.binary.util.check_filename(dpath)
        dpath = cw.util.join_paths("Data/Skin", dpath)
        dpath = cw.binary.util.check_duplicate(dpath)
        self.skindirname = os.path.basename(dpath)
        if not os.path.exists("Data/Skin"):
            os.makedirs("Data/Skin")
        shutil.copytree("Data/SkinBase", dpath)
        f = None
        try:
            renames = {"Sound/System_ScreenShot.wav": "Sound/システム・スクリーンショット.wav"}
            for key, value in renames.items():
                fpath1 = cw.util.join_paths(dpath, key)
                fpath2 = cw.util.join_paths(dpath, value)
                shutil.move(fpath1, fpath2)

            # Resource
            self.curnum = 10
            self.message = "リソースを抽出中..."

            # SkinBaseから変更の無いメッセージは削除しておく
            basedata = cw.data.xml2etree("Data/SkinBase/Skin.xml")
            base_message = basedata.find_exists("Messages")
            e_message = self.data.find_exists("Messages")
            assert len(base_message) == len(e_message)
            removelist = []
            msgtable = {}
            for e in base_message:
                key = e.get("key")
                msgtable[key] = e.text
            for e in e_message:
                key = e.get("key")
                if key in msgtable and msgtable[key] == e.text:
                    removelist.append(e)
            for e in removelist:
                e_message.remove(e)
            e_source = self.data.find("Property/SourceOfMaterialsIsClassicEngine")
            if e_source is None:
                e_source = cw.data.make_element("SourceOfMaterialsIsClassicEngine")
                self.data.find_exists("Property").append(e_source)
            self.data.edit("Property/SourceOfMaterialsIsClassicEngine", str(True))

            self.data.fpath = cw.util.join_paths(dpath, "Skin.xml")

            self.data.write_file()

            self._write_data(dpath, self.actioncard)
            self._write_data(dpath, self.gameover)
            self._write_data(dpath, self.scenario)
            self._write_data(dpath, self.title)
            self._write_data(dpath, self.yado)
            self._write_data(dpath, self.specialcard)

            imgtbl: Dict[str, Union[str, Sequence[str]]] = {}
            for key, value in IMGTBL.items():
                imgtbl[key] = value

            if self.partyinfo_res:
                if self.partyinfo_res.startswith("IMAGE_"):
                    partyinfo = "Card/" + self.partyinfo_res[6:]
                else:
                    partyinfo = "Card/" + self.partyinfo_res
                imgtbl[self.partyinfo_res] = partyinfo

            curtbl = CURTBL.copy()

            if self.version <= (1, 2, 0, 99):
                for repl in (("BUTTON_ARROW", ""),
                             ("BUTTON_CAST", ""),
                             ("BUTTON_DECK", ""),
                             ("BUTTON_DOWN", ""),
                             ("BUTTON_LSMALL", ""),
                             ("BUTTON_RSMALL", ""),
                             ("BUTTON_SACK", ""),
                             ("BUTTON_SHELF", ""),
                             ("BUTTON_TRUSH", ""),
                             ("BUTTON_UP", ""),
                             ("CARD_REVERSE", ""),
                             ("CHECK_FOLDER", "IMAGE_FOLDER"),
                             ("CHECK_LINK", ""),
                             ("CHECK_UTILITY", ""),
                             ("IMAGE_COMMAND5", ""),
                             ("IMAGE_SHELF", "IMAGE_COMMAND5"),
                             ("IMAGE_ALARM", ""),
                             ("MARK_STATUS7", "MARK_STATUS4"),
                             ("MARK_STATUS8", "DBG_CARD0"),
                             ("MARK_STATUS9", "DBG_CARD1"),
                             ("MARK_STATUS10", "MARK_STATUS6"),
                             ("MARK_STATUS11", "MARK_STATUS5"),
                             ("MARK_STATUS12", ""),
                             ("MARK_STATUS13", ""),
                             ("SIGN_HOLD", ""),
                             ("SIGN_PENALTY", ""),
                             ("SIGN_PREMIER", ""),
                             ("SIGN_RARE", ""),
                             ("STATUS_BODY0", "STATUS_POISON"),
                             ("STATUS_BODY1", "STATUS_PARALY"),
                             ("STATUS_MIND0", ""),
                             ("STONE_HAND0", "MARK_HAND0"),
                             ("STONE_HAND1", "MARK_HAND1"),
                             ("STONE_HAND2", "MARK_HAND2"),
                             ("STONE_HAND3", "MARK_HAND3"),
                             ("STONE_HAND4", ""),
                             ("STONE_HAND5", "MARK_HAND4"),
                             ("STONE_HAND6", "MARK_HAND5"),
                             ("STONE_HAND7", "MARK_HAND6"),
                             ("STONE_HAND8", "MARK_HAND7"),
                             ("STONE_HAND9", "MARK_HAND8"),
                             ("TITLE_SHADOW", "TITLE_CARDWIRTH")):
                    fname = imgtbl[repl[0]]
                    del imgtbl[repl[0]]
                    if repl[1]:
                        imgtbl[repl[1]] = fname

                imgtbl["BUTTON_SKILL"] = "Button/SKILL"
                imgtbl["BUTTON_ITEM"] = "Button/ITEM"
                imgtbl["BUTTON_BEAST"] = "Button/BEAST"

                imgtbl["MARK_STATUS0"] = ("Dialog/STATUS1", "Dialog/STATUS2", "Dialog/STATUS3")
                imgtbl["MARK_STATUS1"] = "Dialog/STATUS0"
                imgtbl["MARK_STATUS2"] = "Dialog/STATUS5"
                imgtbl["MARK_STATUS3"] = "Dialog/STATUS6"
                imgtbl["MARK_HAND9"] = "Dialog/RARE_ICON"
                imgtbl["MARK_HAND10"] = "Dialog/PREMIER_ICON"

                glyphtbl = {
                    b"TMAINWINDOW/MainWindow/DebugBtn/Glyph.Data": "Dialog/STATUS12",
                    b"TMAINWINDOW/MainWindow/SystemBtn/Glyph.Data": "Dialog/SETTINGS",
                }

                curtbl = {}
            elif ((1, 2, 8, 0) <= self.version and self.version <= (1, 3, 99, 99)):
                glyphtbl = {
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/BeastBtn/Glyph.Data": "Button/BEAST",
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/ItemBtn/Glyph.Data": "Button/ITEM",
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/SkillBtn/Glyph.Data": "Button/SKILL",
                    b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/PursePanel/PurseImage/Picture.Data":
                        "Dialog/MONEYP",
                    b"TMAINWINDOW/MainWindow/ButtonControl/NormalSheet/VaultPanel/VaultImage/Picture.Data":
                        "Dialog/MONEYY",
                    b"TMAINWINDOW/MainWindow/SystemBtn/Glyph.Data": "Dialog/SETTINGS",
                }
            else:
                glyphtbl = {
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/BeastBtn/Glyph.Data": "Button/BEAST",
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/ItemBtn/Glyph.Data": "Button/ITEM",
                    b"TCARDDLG/CardDlg/TablePanel/SpeedPanel/SkillBtn/Glyph.Data": "Button/SKILL",
                    b"TMAINWINDOW/MainWindow/BottomBar/ButtonControl/NormalSheet/PursePanel/PurseImage/Picture.Data":
                        "Dialog/MONEYP",
                    b"TMAINWINDOW/MainWindow/BottomBar/ButtonControl/NormalSheet/VaultPanel/VaultImage/Picture.Data":
                        "Dialog/MONEYY",
                    b"TMAINWINDOW/MainWindow/BottomBar/SystemBtn/Glyph.Data": "Dialog/SETTINGS",
                }

            # Resource/Image/*
            for resname, target in imgtbl.items():
                assert self.res
                res_bitmap = self.res.get_bitmap(resname)
                if res_bitmap is None:
                    print("Resource not found: %s" % (resname))
                    continue
                if isinstance(target, str):
                    targets: Sequence[str] = [target]
                else:
                    targets = target
                for target2 in targets:
                    fpath = cw.util.join_paths(dpath, "Resource/Image", target2 + ".bmp")
                    resdir = os.path.dirname(fpath)
                    if not os.path.isdir(resdir):
                        os.makedirs(resdir)
                    with open(fpath, "wb") as f:
                        f.write(res_bitmap)
                        f.flush()
                        f.close()
                    f = None

            for resname, target in curtbl.items():
                assert self.res
                res_cursor = self.res.get_cursor(resname)
                if res_cursor is None:
                    print("Cursor not found: %s" % (resname))
                    continue
                fpath = cw.util.join_paths(dpath, "Resource/Image", target + ".cur")
                resdir = os.path.dirname(fpath)
                if not os.path.isdir(resdir):
                    os.makedirs(resdir)
                with open(fpath, "wb") as f:
                    f.write(res_cursor)
                    f.flush()
                    f.close()
                f = None

            for respath, target in glyphtbl.items():
                assert self.res
                respaths = respath.split(b"/")
                tpf0form = self.res.get_tpf0form(respaths[0])
                if not tpf0form:
                    print("Glyph not found: %s" % str(respath, "utf-8"))
                    continue

                res_b = win32res.find_res(tpf0form, respaths[1:], b"")
                if not res_b:
                    print("Glyph not found: %s" % str(respath, "utf-8"))
                    continue
                fpath = cw.util.join_paths(dpath, "Resource/Image", target + ".bmp")
                resdir = os.path.dirname(fpath)
                if not os.path.isdir(resdir):
                    os.makedirs(resdir)
                if res_b[1:8] == b"TBitmap":
                    res_b = res_b[12:]
                else:
                    res_b = res_b[4:]
                with open(fpath, "wb") as f:
                    f.write(res_b)
                    f.flush()
                    f.close()
                f = None

            if not os.path.isabs(self.datadir):
                datadir = cw.util.join_paths(os.path.dirname(self.exe), self.datadir)
            else:
                datadir = self.datadir

            # Bgm
            self.curnum = 20
            self.message = "BGMフォルダをコピー中..."
            folder = cw.util.join_paths(datadir, "Midi")
            target = cw.util.join_paths(dpath, "Bgm")
            if os.path.isdir(folder):
                shutil.copytree(folder, target)
            else:
                os.makedirs(target)

            # Face
            self.curnum = 30
            self.message = "カード画像フォルダをコピー中..."
            folder = cw.util.join_paths(datadir, "Face")
            target = cw.util.join_paths(dpath, "Face")
            if os.path.isdir(folder):
                shutil.copytree(folder, target)
            else:
                os.makedirs(target)

            # Wave
            self.curnum = 40
            self.message = "効果音フォルダをコピー中..."
            folder = cw.util.join_paths(datadir, "Wave")
            target = cw.util.join_paths(dpath, "Sound")
            if os.path.isdir(folder):
                for fname in os.listdir(folder):
                    fpath1 = cw.util.join_paths(folder, fname)
                    fpath2 = cw.util.join_paths(target, fname)
                    if os.path.isdir(fpath1):
                        shutil.copytree(fpath1, fpath2)
                    else:
                        shutil.copyfile(fpath1, fpath2)

            # Table
            self.curnum = 50
            self.message = "背景画像フォルダをコピー中..."
            folder = cw.util.join_paths(datadir, "Table")
            target = cw.util.join_paths(dpath, "Table")
            if os.path.isdir(folder):
                for fname in os.listdir(folder):
                    fpath1 = cw.util.join_paths(folder, fname)
                    fpath2 = cw.util.join_paths(target, fname)
                    if os.path.isdir(fpath1):
                        shutil.copytree(fpath1, fpath2)
                    else:
                        shutil.copyfile(fpath1, fpath2)

            # Scheme
            self.curnum = 60
            self.message = "エフェクトブースターファイルをコピー中..."
            folder = cw.util.join_paths(os.path.dirname(self.exe), "Scheme")
            target = cw.util.join_paths(dpath, "EffectBooster")
            if os.path.isdir(folder):
                for fname in os.listdir(folder):
                    fpath1 = cw.util.join_paths(folder, fname)
                    fpath2 = cw.util.join_paths(target, fname)
                    if os.path.isdir(fpath1):
                        shutil.copytree(fpath1, fpath2)
                    else:
                        shutil.copyfile(fpath1, fpath2)

            # Name
            self.curnum = 70
            self.message = "名前のリストをコピー中..."
            target = cw.util.join_paths(dpath, "Name")
            if not os.path.isdir(target):
                os.makedirs(target)
            names = set()
            for fname in ("MaleNames.txt", "FemaleNames.txt", "CommonNames.txt"):
                fpath = cw.util.join_paths(datadir, fname)
                if os.path.isfile(fpath) and os.path.getsize(fpath):
                    shutil.copyfile(fpath, cw.util.join_paths(target, fname))
                    names.add(fname)

            # Exampleフォルダは不要なので削除
            self.curnum = 75
            exdirpath = cw.util.join_paths(dpath, "Name/Example")
            if os.path.isdir(exdirpath):
                shutil.rmtree(exdirpath)

            # リソースオーバーライド
            self.curnum = 80
            self.message = "オーバーライドされたリソースをコピー中..."
            resdir = cw.util.join_paths(datadir, "Resource")
            for key, target in imgtbl.items():
                fpath = cw.util.join_paths(resdir, key + ".bmp")
                if os.path.isfile(fpath):
                    assert isinstance(target, str)
                    dist = cw.util.join_paths(dpath, "Resource/Image", target + ".bmp")
                    shutil.copyfile(fpath, dist)
                fpath = cw.util.join_paths(resdir, key + ".png")
                if os.path.isfile(fpath):
                    assert isinstance(target, str)
                    dist = cw.util.join_paths(dpath, "Resource/Image", target + ".png")
                    shutil.copyfile(fpath, dist)
                    # ".bmp"より".png"を優先する(アレンジパック対応)
                    dist = cw.util.join_paths(dpath, "Resource/Image", target + ".bmp")
                    if os.path.isfile(dist):
                        cw.util.remove(dist)
            for resname, target in curtbl.items():
                fpath = cw.util.join_paths(resdir, resname + ".cur")
                if os.path.isfile(fpath):
                    assert isinstance(target, str)
                    dist = cw.util.join_paths(dpath, "Resource/Image", target + ".cur")
                    shutil.copyfile(fpath, dist)

            # タイトル画面の背景セルの位置調節
            self.curnum = 90
            fpath = cw.util.join_paths(dpath, "Resource/Xml/Title/01_Title.xml")
            if os.path.isfile(fpath):
                data = cw.data.xml2etree(fpath)
                fpath = cw.util.find_resource(cw.util.join_paths(dpath, "Resource/Image/Other/TITLE_CELL3"), cw.M_IMG)
                tsize = cw.util.load_wxbmp(fpath, can_loaded_scaledimage=True).GetSize()
                fpath = cw.util.find_resource(cw.util.join_paths(dpath, "Resource/Image/Other/TITLE_VERSION"), cw.M_IMG)
                vsize = cw.util.load_wxbmp(fpath, can_loaded_scaledimage=True).GetSize()

                tleft = (cw.SIZE_AREA[0] - tsize[0]) // 2
                ttop = (cw.SIZE_AREA[1] - tsize[1]) // 2
                vleft = (cw.SIZE_AREA[0] - vsize[0]) // 2
                vtop = ttop + tsize[1] + 12

                # TITLE_SHADOW
                if tsize[0] != 0:
                    data.edit("BgImages/BgImage[2]/Location", str(tleft), "left")
                    data.edit("BgImages/BgImage[2]/Location", str(ttop), "top")
                    data.edit("BgImages/BgImage[2]/Size", str(tsize[0]), "width")
                    data.edit("BgImages/BgImage[2]/Size", str(tsize[1]), "height")

                # TITLE_CELL3
                if tsize[0] != 0:
                    data.edit("BgImages/BgImage[3]/Location", str(tleft), "left")
                    data.edit("BgImages/BgImage[3]/Location", str(ttop), "top")
                    data.edit("BgImages/BgImage[3]/Size", str(tsize[0]), "width")
                    data.edit("BgImages/BgImage[3]/Size", str(tsize[1]), "height")

                # TITLE_VERSION
                if vsize[0] != 0:
                    data.edit("BgImages/BgImage[4]/Location", str(vleft), "left")
                    data.edit("BgImages/BgImage[4]/Location", str(vtop), "top")
                    data.edit("BgImages/BgImage[4]/Size", str(vsize[0]), "width")
                    data.edit("BgImages/BgImage[4]/Size", str(vsize[1]), "height")

                data.write_file()

            # 一部バリアントで「パーティ情報」のリソースが
            # "IMAGE_FATHER"から差し替えられているのに対応
            if self.partyinfo_res:
                fpath = cw.util.join_paths(dpath, "Resource/Xml/Yado/02_Yado2.xml")
                if os.path.isfile(fpath):
                    data = cw.data.xml2etree(fpath)
                    data.edit("MenuCards/MenuCard[8]/Property/ImagePath",
                              cw.util.join_paths("Resource/Image", partyinfo))
                    data.write_file()
                fpath = cw.util.join_paths(dpath, "Resource/Xml/Scenario/-4_Camp.xml")
                if os.path.isfile(fpath):
                    data = cw.data.xml2etree(fpath)
                    data.edit("MenuCards/MenuCard[3]/Property/ImagePath",
                              cw.util.join_paths("Resource/Image", partyinfo))
                    data.write_file()

            # 妖魔バリアントでAdventurersInn.bmpが
            # ForestofImages.bmpに差し替えられているのに対応
            if self.adventurersinn:
                fpath = cw.util.join_paths(dpath, "Resource/Xml/Yado/01_Yado.xml")
                if os.path.isfile(fpath):
                    data = cw.data.xml2etree(fpath)
                    data.edit("BgImages/BgImage[2]/ImagePath", cw.util.join_paths("Table", self.adventurersinn))
                    data.write_file()
                fpath = cw.util.join_paths(dpath, "Resource/Xml/Yado/02_Yado2.xml")
                if os.path.isfile(fpath):
                    data = cw.data.xml2etree(fpath)
                    data.edit("BgImages/BgImage[2]/ImagePath", cw.util.join_paths("Table", self.adventurersinn))
                    data.write_file()
                fpath = cw.util.join_paths(dpath, "Resource/Xml/Yado/03_YadoInitial.xml")
                if os.path.isfile(fpath):
                    data = cw.data.xml2etree(fpath)
                    data.edit("BgImages/BgImage[2]/ImagePath", cw.util.join_paths("Table", self.adventurersinn))
                    data.write_file()

            cw.fsync.sync()
            self.curnum = 100
            self.message = "スキンの生成が完了しました。"

            self.complete = True

        except Exception as ex:
            cw.util.print_ex(file=sys.stderr)
            self.failure = True
            self.complete = True
            self.errormessage = "スキンの自動生成に失敗しました。"
            shutil.rmtree(dpath)
            raise ex

        finally:
            if f:
                f.close()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
