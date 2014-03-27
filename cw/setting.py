#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes
import math
import md5
import wx
import pygame
from pygame.locals import *

import cw


class NoFontError(ValueError):
    pass

class Setting(object):
    def __init__(self):
        # フレームレート
        self.fps = 60
        # 1frame分のmillseconds
        self.frametime = 1000 / self.fps
        # Settings
        self.init_settings()
        # シナリオ履歴
        self.recenthistory = RecentHistory(self.data)

    def init_settings(self):
        # "Settings.xml"がなかったら新しく作る
        if not os.path.isfile("Settings.xml"):
            self.lastyado = ""
            self.lastscenario = []
            self.expandmode = "FullScreen"
            self.is_expanded = False
            self.debug = False
            self.no_levelup_in_debugmode = False
            self.vol_bgm = 1.0
            self.vol_midi = 0.8
            self.vol_sound = 1.0
            self.soundfonts = [cw.DEFAULT_SOUNDFONT]
            self.messagespeed = 4
            self.mwincolour = (0, 0, 80, 180)
            self.mwinframecolour = (128, 0, 0, 255)
            self.blwincolour = (80, 80, 80, 180)
            self.blwinframecolour = (128, 128, 128, 255)
            self.dealspeed = 7
            self.transition = "None"
            self.transitionspeed = 5
            self.smoothscale_bg = False
            self.caution_beforesaving = True
            self.store_skinoneachbase = True
            self.revert_cardpocket = True
            self.quickdeal = True
            self.skindirname = "Classic"
            self.classicstyletext = True
            self.sort_standbys = "None"
            self.sort_storehouse = "None"
            self.sort_backpack = "None"
            self.backlogmax = 100
            self.showfps = False
            self.selectscenariofromtype = True
            self.show_unfitnessscenario = True
            self.show_completedscenario = True
            self.show_invisiblescenario = False
            self.folderoftype = []
            self.write()

        self.data = cw.data.xml2etree("Settings.xml")
        data = self.data
        # 最後に選択した宿
        self.lastyado = data.gettext("LastYado", "")
        # 最後に選択したシナリオ(ショートカットがあるため経路を記憶)
        self.lastscenario = []
        # 拡大モード
        self.expandmode = data.gettext("ExpandMode", "FullScreen")
        if self.expandmode == "None":
            self.is_expanded = False
        else:
            self.is_expanded = data.getbool("ExpandMode", "expanded", False)
        # デバッグモードかどうか
        self.debug = data.getbool("DebugMode", False)
        # デバッグ時はレベル上昇しない
        self.no_levelup_in_debugmode = data.getbool("NoLevelUpInDebugMode", False)
        # 音楽のボリューム(0～1.0)
        self.vol_bgm = data.getint("BgmVolume", 100)
        self.vol_bgm = self.wrap_volumevalue(self.vol_bgm)
        # midi音楽のボリューム(0～1.0)
        self.vol_midi = data.getint("BgmVolume", "midi", 80)
        self.vol_midi = self.wrap_volumevalue(self.vol_midi)
        # 効果音ボリューム
        self.vol_sound = data.getint("SoundVolume", 100)
        self.vol_sound = self.wrap_volumevalue(self.vol_sound)
        # MIDIサウンドフォント
        self.soundfonts = [cw.DEFAULT_SOUNDFONT]
        elements = data.getfind("SoundFonts", False)
        if not elements is None:
            self.soundfonts = []
            for e in elements:
                self.soundfonts.append(e.text)
        # メッセージスピード(数字が小さいほど速い)(0～100)
        self.messagespeed = data.getint("MessageSpeed", 0)
        self.messagespeed = cw.util.numwrap(self.messagespeed, 0, 100)
        # メッセージウィンドウの色と透明度
        r = data.getint("MessageWindowColor", "red", 0)
        g = data.getint("MessageWindowColor", "green", 0)
        b = data.getint("MessageWindowColor", "blue", 80)
        a = data.getint("MessageWindowColor", "alpha", 180)
        self.mwincolour = self.wrap_colorvalue(r, g, b, a)
        r = data.getint("MessageWindowFrameColor", "red", 128)
        g = data.getint("MessageWindowFrameColor", "green", 0)
        b = data.getint("MessageWindowFrameColor", "blue", 0)
        a = data.getint("MessageWindowFrameColor", "alpha", 255)
        self.mwinframecolour = self.wrap_colorvalue(r, g, b, a)
        # バックログウィンドウの色と透明度
        r = data.getint("MessageLogWindowColor", "red", 80)
        g = data.getint("MessageLogWindowColor", "green", 80)
        b = data.getint("MessageLogWindowColor", "blue", 80)
        a = data.getint("MessageLogWindowColor", "alpha", 180)
        self.blwincolour = self.wrap_colorvalue(r, g, b, a)
        r = data.getint("MessageLogWindowFrameColor", "red", 128)
        g = data.getint("MessageLogWindowFrameColor", "green", 128)
        b = data.getint("MessageLogWindowFrameColor", "blue", 128)
        a = data.getint("MessageLogWindowFrameColor", "alpha", 255)
        self.blwinframecolour = self.wrap_colorvalue(r, g, b, a)
        # カードの表示スピード(数字が小さいほど速い)(1～100)
        dealspeed = data.getint("CardDealingSpeed", 6)
        self.set_dealspeed(dealspeed)
        # トランジション効果の種類
        self.transition = data.gettext("Transition", "Fade")
        self.transitionspeed = data.getint("Transition", "speed", 4)
        self.transitionspeed = cw.util.numwrap(self.transitionspeed, 0, 10)
        # 背景のスムーススケーリング
        self.smoothscale_bg = data.getbool("SmoothScaling", "bg", False)
        # 保存せずに終了しようとしたら警告
        self.caution_beforesaving = data.getbool("CautionBeforeSaving", True)
        # 拠点ごとにスキンを記憶
        self.store_skinoneachbase = data.getbool("StoreSkinOnEachBase", True)
        # レベル調節で手放したカードを自動的に戻す
        self.revert_cardpocket = data.getbool("RevertCardPocket", True)
        # キャンプ等に高速で切り替える
        self.quickdeal = data.getbool("QuickDeal", True)
        # ソート基準
        self.sort_standbys = data.getattr("SortKey", "standbys", "None")
        self.sort_storehouse = data.getattr("SortKey", "storehouse", "None")
        self.sort_backpack = data.getattr("SortKey", "backpack", "None")
        # バックログ最大数
        self.backlogmax = data.getint("MessageLogMax", 100)

        self.showfps = False

        # スキンによってシナリオの選択開始位置を変更する
        self.selectscenariofromtype = data.getbool("SelectScenarioFromType", True)
        # 適正レベル以外のシナリオを表示する
        self.show_unfitnessscenario = data.getbool("ShowUnfitnessScenario", True)
        # 隠蔽シナリオを表示する
        self.show_completedscenario = data.getbool("ShowCompletedScenario", True)
        # 終了済シナリオを表示する
        self.show_invisiblescenario = data.getbool("ShowInvisibleScenario", False)

        # シナリオフォルダ(スキンタイプ別)
        self.folderoftype = []
        for e_folder in data.getfind("ScenarioFolderOfSkinType", False):
            skintype = e_folder.getattr(".", "skintype", "")
            folder = e_folder.gettext(".", "")
            self.folderoftype.append((skintype, folder))

        # スキン
        self.skindirname = data.gettext("Skin", "Classic")
        self.init_skin()

    def init_skin(self):
        self.skindir = cw.util.join_paths(u"Data/Skin", self.skindirname)
        if not os.path.isdir(self.skindir):
            self.skindirname = "Classic"
            self.skindir = cw.util.join_paths(u"Data/Skin", self.skindirname)

            if not os.path.isdir(self.skindir):
                # Classicが無いので手当たり次第にスキンを探す
                for path in os.listdir(u"Data/Skin"):
                    dpath = cw.util.join_paths(u"Data/Skin", path)
                    fpath = cw.util.join_paths(dpath, "Skin.xml")
                    if os.path.isfile(fpath):
                        self.skindirname = path
                        self.skindir = dpath
                        break

            if not os.path.isdir(self.skindir):
                raise ValueError("Not found CardWirthPy skins!")

        path = cw.util.join_paths("Data/SkinBase/Skin.xml")
        basedata = cw.data.xml2etree(path)
        path = cw.util.join_paths(self.skindir, "Skin.xml")
        data = cw.data.xml2etree(path)
        self._update_skin(data)
        self.skinname = data.gettext("Property/Name", "")
        self.skintype = data.gettext("Property/Type", "")
        self.skinexts = data.getfind("Property/Extension").attrib
        self.classicstyletext = data.gettext("Property/ClassicStyleText", True)
        # スキン・種族
        self.races = [cw.header.RaceHeader(e) for e in data.getfind("Races")]

        # 特性
        self.sexes = [cw.features.Sex(e) for e in data.getfind("Sexes")]
        self.sexnames = [f.name for f in self.sexes]
        self.sexsubnames = [f.subname for f in self.sexes]
        self.sexcoupons = [u"＿" + f.name for f in self.sexes]
        self.periods = [cw.features.Period(e) for e in data.getfind("Periods")]
        self.periodnames = [f.name for f in self.periods]
        self.periodsubnames = [f.subname for f in self.periods]
        self.periodcoupons = [u"＿" + f.name for f in self.periods]
        self.natures = [cw.features.Nature(e) for e in data.getfind("Natures")]
        self.naturenames = [f.name for f in self.natures]
        self.naturecoupons = [u"＿" + f.name for f in self.natures]
        self.makings = [cw.features.Making(e) for e in data.getfind("Makings")]
        self.makingnames = [f.name for f in self.makings]
        self.makingcoupons = [u"＿" + f.name for f in self.makings]

        # デバグ宿で簡易生成を行う際の能力型
        self.sampletypes = [cw.features.SampleType(e) for e in data.getfind("SampleTypes")]

        # 音声とメッセージは、選択中のスキンに
        # 定義されていなければスキンベースのもので代替する

        # 音声
        self.sounds = {}
        for e in basedata.getfind("Sounds"):
            self.sounds[e.getattr(".", "key", "")] = e.gettext(".", "")
        for e in data.getfind("Sounds"):
            self.sounds[e.getattr(".", "key", "")] = e.gettext(".", "")
        # メッセージ
        self.msgs = {}
        for e in basedata.getfind("Messages"):
            self.msgs[e.getattr(".", "key", "")] = e.gettext(".", "")
        for e in data.getfind("Messages"):
            self.msgs[e.getattr(".", "key", "")] = e.gettext(".", "")

        # 未指定種族
        self.unknown_race = cw.header.UnknownRaceHeader(self)
        self.races.append(self.unknown_race)

    def _update_skin(self, data):
        """旧バージョンのデータの誤りを訂正する。
        """
        skinversion = float(data.getattr(".", "dataVersion", "0"))
        update = False

        if skinversion <= 1:
            # dataVersion=1まで
            #  * 社交-内向と慎重-大胆の値が入れ替わっていた
            #  * SampleTypeで精神特性の値が1/2になっていた
            #  * SkinBaseの情報を上書きしていない場合に限り、SampleTypeで
            #    社交-内向と慎重-大胆の入れ替わりは発生していない
            update = True
            def update_mental(e):
                me = e.find("Mental")
                cautious = me.getattr(".", "cautious")
                cheerful = me.getattr(".", "cheerful")
                me.attrib["cautious"] = cheerful
                me.attrib["cheerful"] = cautious
            for e in data.getfind("Sexes"):
                update_mental(e)
            for e in data.getfind("Periods"):
                update_mental(e)
            for e in data.getfind("Natures"):
                update_mental(e)
            for e in data.getfind("Makings"):
                update_mental(e)
            ste = data.getfind("SampleTypes")
            def check_sampletype(ste, name, cautious, cheerful):
                # SampleTypeがSkinBaseの内容そのままかチェックする
                return ste.gettext("Name") == name and\
                       ste.getfloat("Mental", "cautious") == cautious and\
                       ste.getfloat("Mental", "cheerful") == cheerful
            if len(ste) <> 5 or\
               not check_sampletype(ste[0], u"バランス", 0.0, 0.0) or\
               not check_sampletype(ste[1], u"ファイター", -0.5, 0.0) or\
               not check_sampletype(ste[2], u"シーフ", 0.5, 0.0) or\
               not check_sampletype(ste[3], u"プリースト", 0.0, 0.5) or\
               not check_sampletype(ste[4], u"メイジ", 0.5, -0.5):
                # SkinBaseの内容そのままでない場合は入れ替え発生
                for e in ste:
                    update_mental(e)
            for e in ste:
                me = e.find("Mental")
                aggressive = me.getfloat(".", "aggressive")
                brave = me.getfloat(".", "brave")
                cautious = me.getfloat(".", "cautious")
                cheerful = me.getfloat(".", "cheerful")
                trickish = me.getfloat(".", "trickish")
                me.attrib["aggressive"] = str(aggressive * 2)
                me.attrib["brave"] = str(brave * 2)
                me.attrib["cautious"] = str(cautious * 2)
                me.attrib["cheerful"] = str(cheerful * 2)
                me.attrib["trickish"] = str(trickish * 2)

        if update:
            data.edit(".", "2", "dataVersion")
            data.write()

    def set_dealspeed(self, value):
        self.dealspeed = value + 1
        self.dealspeed = cw.util.numwrap(self.dealspeed, 1, 11)
        scales_len = int(self.dealspeed * 1.2)
        self.dealing_scales = [
            int(math.cos(math.radians(90.0 * i / scales_len)) * 100)
            for i in xrange(scales_len)
                if i
        ]

    def write(self):
        cw.xmlcreater.create_settings(self)

    def wrap_volumevalue(self, value):
        return cw.util.numwrap(value, 0, 100) / 100.0

    def wrap_colorvalue(self, r, g, b, a):
        r = cw.util.numwrap(r, 0, 255)
        g = cw.util.numwrap(g, 0, 255)
        b = cw.util.numwrap(b, 0, 255)
        a = cw.util.numwrap(a, 0, 255)
        return (r, g, b, a)

class Resource(object):
    def __init__(self, setting):
        # 現在選択しているスキンのディレクトリ
        self.skindir = setting.skindir
        # 各種データの拡張子
        self.ext_img = setting.skinexts.get("image")
        self.ext_bgm = setting.skinexts.get("bgm")
        self.ext_snd = setting.skinexts.get("sound")
        # システムフォントテーブルの設定(wxダイアログ用)
        self.fontpaths = self.get_fontpaths()
        # wxスレッドから初期化
        self.fontnames = {}
        # その他のスキン付属効果音(辞書)
        self.skinsounds = self.get_skinsounds()
        # システム効果音(辞書)
        self.sounds = self.get_sounds(setting, self.skinsounds)
        # システムメッセージ(辞書)
        self.msgs = self.get_msgs(setting)
        # wxダイアログのボタン画像(辞書)
        # wxスレッドから初期化
        self.buttons = {}
        # カード背景画像(辞書)
        self.cardbgs = self.get_cardbgs()
        # wxダイアログで使う画像(辞書)
        self.pygamedialogs = self.get_dialogs(cw.util.load_image)
        # wx版。wxスレッドから初期化
        self.dialogs = {}
        # デバッガで使う画像(辞書)
        self.pygamedebugs = self.get_debugs(cw.util.load_image)
        # wx版。wxスレッドから初期化
        self.debugs = {}
        # 特殊文字の画像(辞書)
        self.specialchars_is_changed = False
        self.specialchars = self.get_specialchars()
        # プレイヤカードのステータス画像(辞書)
        self.statuses = self.get_statuses()
        # 適性値・使用回数値画像(辞書)
        self.stones = self.get_stones()
        # wx版。wxスレッドから初期化
        self.wxstones = {}
        # 使用フォント(辞書)。スプライトを作成するたびにフォントインスタンスを
        # 新規作成すると重いのであらかじめ用意しておく(wxスレッドから初期化)
        self.fonts = self.create_fonts()
        # "MS UI GOTHIC"が使えるかどうか
        self._msuigothic = False
        # StatusBarで使用するボタンイメージ
        # wxスレッドから初期化
        self._wxbtnbmp0 = self._create_wxbtnbmp(cw.s(120), cw.s(22), 0)
        self._wxbtnbmp0pressed = self._create_wxbtnbmp(cw.s(120), cw.s(22), wx.CONTROL_PRESSED)
        self._wxbtnbmp0current = self._create_wxbtnbmp(cw.s(120), cw.s(22), wx.CONTROL_CURRENT)
        self._wxbtnbmp1 = self._create_wxbtnbmp(cw.s(27), cw.s(27), 0)
        self._wxbtnbmp1pressed = self._create_wxbtnbmp(cw.s(27), cw.s(27), wx.CONTROL_PRESSED)
        self._wxbtnbmp1current = self._create_wxbtnbmp(cw.s(27), cw.s(27), wx.CONTROL_CURRENT)
        self._wxbtnbmp2 = self._create_wxbtnbmp(cw.s(632), cw.s(33), 0)

        self.ignorecase_table = {}

        if sys.platform == "win32":
            self.init_wxresources()
        else:
            cw.cwpy.frame.exec_func(self.init_wxresources)
            # FIXME: 大文字・小文字を区別しないシステムでリソース内のファイルの
            #        取得に失敗する事があるので、すべて小文字のパスをキーにして
            #        真のファイル名へのマッピングをしておく。
            #        主にこの問題は手書きされる'*.jpy1'内で発生する。
            for res in ("Table", "Bgm", "Sound"):
                resdir = cw.util.join_paths(self.skindir, res)
                for dpath, dnames, fnames in os.walk(resdir):
                    for fname in fnames:
                        path = cw.util.join_paths(dpath, fname)
                        self.ignorecase_table[path.lower()] = path

    def get_filepath(self, fpath):
        if not fpath or os.path.isfile(fpath) or cw.binary.image.path_is_code(fpath):
            return fpath

        if self.ignorecase_table or (cw.cwpy.sdata and cw.cwpy.sdata.ignorecase_table):
            lpath = fpath.lower()
            if lpath in self.ignorecase_table:
                fpath = self.ignorecase_table.get(lpath, fpath)
            elif cw.cwpy.sdata and cw.cwpy.sdata.ignorecase_table:
                fpath = cw.cwpy.sdata.ignorecase_table.get(lpath, fpath)

        return fpath

    def init_wxresources(self):
        """wx側のリソースを初期化。"""
        # システムフォントテーブルの設定(wxダイアログ用)
        self.fontnames = self.set_systemfonttable()
        # wxダイアログのボタン画像(辞書)
        self.buttons = self.get_buttons()
        # wxダイアログで使う画像(辞書)
        self.dialogs = self.get_dialogs(cw.util.load_wxbmp)
        # デバッガで使う画像(辞書)
        self.debugs = self.get_debugs(cw.util.load_wxbmp)
        # 適性値・使用回数値画像(辞書)
        self.wxstones = self.get_wxstones()
        # 使用フォント(辞書)
        self.fonts.update(self.create_wxfonts())
        # "MS UI GOTHIC"が使えるかどうか
        self._msuigothic = bool("MS UI Gothic" in
                                        wx.FontEnumerator.GetFacenames())

    def get_fontpaths(self):
        """
        フォントパス(辞書)
        """
        fontdir = "Data/Font"
        fontdir_skin = cw.util.join_paths(self.skindir, "Resource/Font")
        fnames = ("gothic.ttf", "uigothic.ttf", "mincho.ttf",
                                            "pgothic.ttf", "pmincho.ttf")
        d = {}

        for fname in fnames:
            path = cw.util.join_paths(fontdir_skin, fname)

            if not os.path.isfile(path):
                path = cw.util.join_paths(fontdir, fname)

                if not os.path.isfile(path):
                    raise NoFontError(fname + " not found.")

            d[os.path.splitext(fname)[0]] = path

        return d

    def set_systemfonttable(self):
        """
        システムフォントテーブルの設定を行う。
        設定したフォント名をフォントファイル名がkeyの辞書で返す。
        """
        d = {}

        if sys.platform == "win32":
            gdi32 = ctypes.windll.gdi32
            winplatform = sys.getwindowsversion()[3]

            for name, path in self.fontpaths.iteritems():
                if winplatform == 2:
                    gdi32.AddFontResourceExA(path, 0x10, 0)
                else:
                    gdi32.AddFontResourceA(path)
                    user32 = ctypes.windll.user32
                    HWND_BROADCAST = 0xFFFF
                    WM_FONTCHANGE = 0x001D
                    user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)

                fontname = cw.util.get_truetypefontname(path)

                if fontname:
                    d[name] = fontname
                else:
                    raise ValueError("Failed to get facename from %s" % name)

        else:
            d["gothic"] = u"IPAゴシック"
            d["uigothic"] = u"IPA UIゴシック"
            d["mincho"] = u"IPA明朝"
            d["pmincho"] = u"IPA P明朝"
            d["pgothic"] = u"IPA Pゴシック"
            self.facenames = set(wx.FontEnumerator().GetFacenames())

            for value in d.itervalues():
                if not value in self.facenames:
                    raise ValueError(u"IPA font not found: " + value)

        return d

    def clear_systemfonttable(self):
        if sys.platform == "win32" and not sys.getwindowsversion()[3] == 2:
            gdi32 = ctypes.windll.gdi32

            for name, path in self.fontpaths.iteritems():
                gdi32.RemoveFontResourceA(path)

            user32 = ctypes.windll.user32
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)

    def get_wxfont(self, name="uigothic", size=None,
                        family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD, encoding=wx.FONTENCODING_SYSTEM):
        if size is None:
            size = cw.s(10)
        if name == "btnfont":
            if self._msuigothic:
                fontname = "MS UI Gothic"
            else:
                fontname = u"IPA UIゴシック"
        else:
            fontname = self.fontnames[name]

        wxfont = wx.Font(size, family, style, weight, 0, fontname, encoding)
        return wxfont

    def create_fonts(self):
        """ゲーム内で頻繁に使用するpygame.Fontはここで設定する。"""
        # 使用フォント(辞書)
        fonts = {}
        # 所持カードの使用回数描画用
        font = pygame.font.Font(self.fontpaths["mincho"], cw.s(16))
        font.set_bold(True)
        fonts["card_uselimit"] = font
        # メニューカードの名前描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], cw.s(12))
        font.set_bold(True)
        fonts["mcard_name"] = font
        # プレイヤカードの名前描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], cw.s(14))
        font.set_bold(True)
        fonts["pcard_name"] = font
        # プレイヤカードのレベル描画用
        font = pygame.font.Font(self.fontpaths["mincho"], cw.s(36))
        font.set_italic(True)
        fonts["pcard_level"] = font
        # メッセージウィンドウのテキスト描画用
        font = pygame.font.Font(self.fontpaths["mincho"], cw.s(22))
        fonts["message"] = font
        # メッセージウィンドウの選択肢描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], cw.s(15))
        if cw.UP_SCR == 1:
            font.set_bold(True)
        fonts["selectionbar"] = font
        # ステータスバーパネル描画用
        font = pygame.font.Font(self.fontpaths["pmincho"], cw.s(14))
        font.set_bold(True)
        fonts["sbarpanel"] = font
        # ステータスバーボタン描画用
        fonts["sbarbtn"] = fonts["mcard_name"]
        # ステータス画像の召喚回数描画用
        fonts["statusimg"] = fonts["mcard_name"]
        return fonts

    def create_wxfonts(self):
        """ゲーム内で頻繁に使用するwx.Fontはここで設定する。"""
        # 使用フォント(辞書)
        fonts = {}
        if u"ＭＳ 明朝" in wx.FontEnumerator.GetFacenames():
            # メッセージウィンドウのテキスト描画用(クラシック)
            # これのみwx.Fontを使用する
            wxfont = wx.Font(cw.s(15), wx.DEFAULT, wx.NORMAL, wx.BOLD, 0, u"ＭＳ 明朝", wx.FONTENCODING_SYSTEM)
            fonts["message_classic"] = wxfont
        return fonts

    def create_wxbutton(self, parent, id, size, name=None, bmp=None):
        if name:
            button = wx.Button(parent, id, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("btnfont"))
        elif bmp:
            button = wx.BitmapButton(parent, id, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)

        return button

    def create_wxbutton_dbg(self, parent, id, size, name=None, bmp=None):
        if name:
            button = wx.Button(parent, id, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("btnfont", size=10))
        elif bmp:
            button = wx.BitmapButton(parent, id, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)

        return button

    def _create_wxbtnbmp(self, w, h, flags=0):
        if sys.platform == "win32":
            wxbmp = wx.EmptyBitmap(w, h)
            wxbmp.UseAlpha()
            dc = wx.MemoryDC(wxbmp)
            render = wx.RendererNative.Get()
            render.DrawPushButton(cw.cwpy.frame, dc, (cw.s(0), cw.s(0), w, h), flags)
            dc.EndDrawing()
            # RendererNativeがアルファ値を出力しなかった場合
            wximg = wxbmp.ConvertToImage()
            pixel_num = w * h

            if wximg.GetAlphaData() == "\x00" * pixel_num:
                wximg.SetAlphaData("\xFF" * pixel_num)
                wxbmp = wximg.ConvertToBitmap()

            return cw.image.conv2surface(wxbmp)
        else:
            bmp = pygame.Surface((w, h)).convert()
            c1 = 240
            c2 = 224
            mid = h / 2
            for y in xrange(0, mid+1, 1):
                bmp.fill((c1-y, c1-y, c1-y), pygame.Rect(0, mid-y, w, 1))
                bmp.fill((c2-y, c2-y, c2-y), pygame.Rect(0, mid+y, w, 1))

            r = 4
            r2 = r*2

            if (flags & wx.CONTROL_CURRENT) <> 0:
                color = (240, 240, 240)
                bmp.fill(color, pygame.Rect(r+1, 1, w-r2-2, h-2))
                bmp.fill(color, pygame.Rect(1, r+1, w-2, h-r2-2))
                pygame.draw.ellipse(bmp, color, (w-r2-2, 1, r2, r2))
                pygame.draw.ellipse(bmp, color, (1, 1, r2, r2))
                pygame.draw.ellipse(bmp, color, (1, h-r2-2, r2, r2))
                pygame.draw.ellipse(bmp, color, (w-r2-2, h-r2-2, r2, r2))

            if (flags & wx.CONTROL_PRESSED) <> 0:
                color = (196, 196, 196)
                bmp.fill(color, pygame.Rect(r+1, 1, w-r2-2, h-2))
                bmp.fill(color, pygame.Rect(1, r+1, w-2, h-r2-2))
                pygame.draw.ellipse(bmp, color, (w-r2-2, 1, r2, r2))
                pygame.draw.ellipse(bmp, color, (1, 1, r2, r2))
                pygame.draw.ellipse(bmp, color, (1, h-r2-2, r2, r2))
                pygame.draw.ellipse(bmp, color, (w-r2-2, h-r2-2, r2, r2))

            color = (128, 128, 128)

            pygame.draw.line(bmp, color, (r, 1), (w-r-1, 1))
            pygame.draw.line(bmp, color, (r, h-2), (w-r-1, h-2))
            pygame.draw.line(bmp, color, (1, r), (1, h-r-1))
            pygame.draw.line(bmp, color, (w-2, r), (w-2, h-r-1))

            r0 = math.radians(0)
            r90 = math.radians(90)
            r180 = math.radians(180)
            r270 = math.radians(270)
            r360 = math.radians(360)
            pygame.draw.arc(bmp, color, (w-r2-2, 1, r2, r2), 0, r90)
            pygame.draw.arc(bmp, color, (1, 1, r2, r2), r90, r180)
            pygame.draw.arc(bmp, color, (1, h-r2-2, r2, r2), r180, r270)
            pygame.draw.arc(bmp, color, (w-r2-2, h-r2-2, r2, r2), r270, r360)

            return bmp

    def get_wxbtnbmp(self, sizetype, flags=0):
        """StatusBarで使用するOSネイティブなボタン画像を取得する。
        sizetype: 0=(120, 22), 1=(27, 27), 2=(632, 33)
        flags: 0, wx.CONTROL_PRESSED, wx.CONTROL_CURRENT
               sizetype=0または1の時のみ有効
        """
        if sizetype == 0:
            if flags == wx.CONTROL_PRESSED:
                return self._wxbtnbmp0pressed.copy()
            elif flags == wx.CONTROL_CURRENT:
                return self._wxbtnbmp0current.copy()
            else:
                return self._wxbtnbmp0.copy()
        elif sizetype == 1:
            if flags == wx.CONTROL_PRESSED:
                return self._wxbtnbmp1pressed.copy()
            elif flags == wx.CONTROL_CURRENT:
                return self._wxbtnbmp1current.copy()
            else:
                return self._wxbtnbmp1.copy()
        elif sizetype == 2:
            return self._wxbtnbmp2.copy()

        return None

    def get_resources(self, func, dpath, ext, mask=False):
        """
        各種リソースデータを辞書で返す。
        ファイル名から拡張子を除いたのがkey。
        """
        d, dpath = {}, unicode(dpath)

        for fname in os.listdir(dpath):
            if fname.endswith(ext):
                fpath = cw.util.join_paths(dpath, fname)

                if mask:
                    resource = func(fpath, mask=mask)
                else:
                    resource = func(fpath)

                if isinstance(resource, tuple):
                    d[os.path.splitext(fname)[0]] = resource[1]
                    d[os.path.splitext(fname)[0] + "_dbg"] = resource[0]
                else:
                    d[os.path.splitext(fname)[0]] = resource

        return d

    def get_sounds(self, setting, skinsounds):
        """
        システム効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        d = {}
        for key, sound in setting.sounds.items():
            if sound in skinsounds:
                d[key] = skinsounds[sound]
            else:
                d[key] = cw.util.SoundInterface(None, "")
        return d

    def get_skinsounds(self):
        """
        スキン付属の効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        func = cw.util.load_sound
        dpath = cw.util.join_paths(self.skindir, "Sound")
        return self.get_resources(func, dpath, self.ext_snd)

    def get_msgs(self, setting):
        """
        システムメッセージを辞書で返す。
        """
        return setting.msgs

    def get_buttons(self):
        """
        ダイアログのボタン画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        def func(path, mask):
            bmp = cw.util.load_wxbmp(path, mask)
            return bmp, cw.s((bmp, get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Button")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_stones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        pygameのサーフェスの辞書で返す。
        """
        def func(path, mask):
            bmp = cw.util.load_image(path, mask)
            return bmp, cw.s((bmp, get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_wxstones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        def func(path, mask):
            bmp = cw.util.load_wxbmp(path, mask)
            return bmp, cw.s((bmp, get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_statuses(self):
        """
        ステータス表示に使う画像を読み込んで、
        ("LIFEGUAGE", "TARGET", "LIFE", "UP*", "DOWN*"はマスクする)
        pygameのサーフェスの辞書で返す。
        """
        def func(path):
            bmp = cw.util.load_image(path)
            return bmp, cw.s((bmp, get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Status")
        d = self.get_resources(func, dpath, self.ext_img)

        for name in ("LIFE", "UP0", "UP1", "UP2", "UP3", "DOWN0", "DOWN1", "DOWN2", "DOWN3"):
            path = cw.util.join_paths(dpath, name + self.ext_img)
            bmp = cw.util.load_image(path, mask=True, maskpos=(1, 1))
            d[name + "_dbg"] = bmp
            d[name] = cw.s((bmp, get_resourcesize(path)))

        name = "TARGET"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.s((cw.util.load_image(path, mask=True, maskpos="right"), get_resourcesize(path)))

        name = "LIFEGUAGE"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.util.load_image(path, mask=True, maskpos="center")

        name = "LIFEBAR"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.util.load_image(path)

        return d

    def get_dialogs(self, load_image):
        """
        ダイアログで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        def func(path, mask):
            bmp = load_image(path, mask)
            return bmp, cw.s((bmp, get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Dialog")
        d = self.get_resources(func, dpath, self.ext_img, True)

        name = "LINK"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.s((load_image(path, mask=False), get_resourcesize(path)))

        name = "MONEYY"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.s((load_image(path, mask=False), get_resourcesize(path)))

        name = "STATUS8"
        path = cw.util.join_paths(dpath, name + self.ext_img)
        d[name] = cw.s((load_image(path, mask=True, maskpos="right"), get_resourcesize(path)))

        for key in ["CAUTION", "INVISIBLE"]:
            path = cw.util.join_paths(dpath, key + self.ext_img)
            d[key] = cw.s((load_image(path), get_resourcesize(path)))
        return d

    def get_debugs(self, load_image):
        """
        デバッガで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        def func(path, mask):
            bmp = load_image(path, mask)
            return bmp, bmp
        dpath = u"Data/Debugger"
        d = self.get_resources(func, dpath, ".png", True)
        return d

    def get_cardbgs(self):
        """
        カードの背景画像を読み込んで、pygameのサーフェス
        ("PREMIER", "RARE", "HOLD", "PENALTY"はマスクする)
        の辞書で返す。
        """
        def func(path):
            return cw.s((cw.util.load_image(path), get_resourcesize(path)))
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/CardBg")
        d = self.get_resources(func, dpath, self.ext_img)

        for img in (("HOLD", "center"), ("PENALTY", "center"), ("PREMIER", "right"), ("RARE", "right")):
            name = img[0]
            path = cw.util.join_paths(dpath, name + self.ext_img)
            d[name] = cw.s((cw.util.load_image(path, True, maskpos = img[1]), get_resourcesize(path)))

        return d

    def get_actioncards(self):
        """
        "Resource/Xml/ActionCard"にあるアクションカードを読み込み、
        CWPyElementTreeインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Xml/ActionCard")
        ext = ".xml"
        d = {}

        for fname in os.listdir(dpath):
            if fname.endswith(ext):
                fpath = cw.util.join_paths(dpath, fname)
                carddata = cw.data.xml2element(fpath)
                header = cw.header.CardHeader(carddata=carddata)
                d[header.id] = header

        return d

    def get_specialchars(self):
        """
        特殊文字の画像を読み込んで、
        pygameのサーフェスの辞書で返す(特殊文字がkey)
        """
        self.specialchars_is_changed = False
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Font")
        ext = self.ext_img

        ndict = {"ANGRY" + ext   : "#a",
                 "CLUB" + ext    : "#b",
                 "DIAMOND" + ext : "#d",
                 "EASY" + ext    : "#e",
                 "FLY" + ext     : "#f",
                 "GRIEVE" + ext  : "#g",
                 "HEART" + ext   : "#h",
                 "JACK" + ext    : "#j",
                 "KISS" + ext    : "#k",
                 "LAUGH" + ext   : "#l",
                 "NIKO" + ext    : "#n",
                 "ONSEN" + ext   : "#o",
                 "PUZZLE" + ext  : "#p",
                 "QUICK" + ext   : "#q",
                 "SPADE" + ext   : "#s",
                 "WORRY" + ext   : "#w",
                 "X" + ext       : "#x",
                 "ZAP" + ext     : "#z",
                 }

        d = {}

        for fname in os.listdir(dpath):
            fpath = cw.util.join_paths(dpath, fname)

            if fname.endswith(ext) and fname in ndict:
                name = ndict[fname]
                image = cw.util.load_image(fpath)
                image.set_colorkey((255, 255, 255))
                d[name] = image, False

        return d

# リソースの標準サイズ
SIZE_SPFONT = (22, 22)
SIZE_RESOURCES = {
    "Button/ARROW": (16, 16),
    "Button/BEAST": (65, 45),
    "Button/CAST": (16, 16),
    "Button/DECK": (16, 16),
    "Button/DOWN": (14, 14),
    "Button/ITEM": (65, 45),
    "Button/LJUMP": (16, 14),
    "Button/LMOVE": (9, 14),
    "Button/LSMALL": (9, 9),
    "Button/RJUMP": (16, 14),
    "Button/RMOVE": (9, 14),
    "Button/RSMALL": (9, 9),
    "Button/SACK": (16, 16),
    "Button/SHELF": (16, 16),
    "Button/SKILL": (65, 45),
    "Button/TRUSH": (16, 16),
    "Button/UP": (14, 14),
    "CardBg/ACTION": (80, 110),
    "CardBg/BEAST": (80, 110),
    "CardBg/BIND": (95, 130),
    "CardBg/DANGER": (95, 130),
    "CardBg/FAINT": (95, 130),
    "CardBg/HOLD": (80, 110),
    "CardBg/INFO": (80, 110),
    "CardBg/INJURY": (95, 130),
    "CardBg/ITEM": (80, 110),
    "CardBg/LARGE": (95, 130),
    "CardBg/NORMAL": (80, 110),
    "CardBg/OPTION": (80, 110),
    "CardBg/PARALY": (95, 130),
    "CardBg/PENALTY": (80, 110),
    "CardBg/PETRIF": (95, 130),
    "CardBg/PREMIER": (12, 16),
    "CardBg/RARE": (12, 40),
    "CardBg/REVERSE": (95, 130),
    "CardBg/SKILL": (80, 110),
    "CardBg/SLEEP": (95, 130),
    "Dialog/CAUTION": (37, 37),
    "Dialog/COMPLETE": (100, 100),
    "Dialog/FIXED": (26, 26),
    "Dialog/FOLDER": (64, 54),
    "Dialog/INVISIBLE": (232, 29),
    "Dialog/LINK": (20, 20),
    "Dialog/MONEYP": (18, 18),
    "Dialog/MONEYY": (18, 18),
    "Dialog/PAD": (226, 132),
    "Dialog/PLAYING": (68, 146),
    "Dialog/SELECT": (16, 13),
    "Dialog/SETTINGS": (16, 16),
    "Dialog/STATUS": (220, 56),
    "Dialog/STATUS0": (14, 14),
    "Dialog/STATUS1": (14, 14),
    "Dialog/STATUS2": (14, 14),
    "Dialog/STATUS3": (14, 14),
    "Dialog/STATUS4": (14, 14),
    "Dialog/STATUS5": (14, 14),
    "Dialog/STATUS6": (14, 14),
    "Dialog/STATUS7": (14, 14),
    "Dialog/STATUS8": (14, 14),
    "Dialog/STATUS9": (14, 14),
    "Dialog/STATUS10": (14, 14),
    "Dialog/STATUS11": (14, 14),
    "Dialog/STATUS12": (14, 14),
    "Dialog/STATUS13": (14, 14),
    "Dialog/UTILITY": (128, 24),
    "Other/TITLE": (406, 99),
    "Other/TITLE_CARD1": (124, 134),
    "Other/TITLE_CARD2": (124, 134),
    "Other/TITLE_CELL1": (133, 30),
    "Other/TITLE_CELL2": (133, 46),
    "Other/TITLE_CELL3": (406, 99),
    "Status/BODY0": (16, 16),
    "Status/BODY1": (16, 16),
    "Status/DOWN0": (16, 16),
    "Status/DOWN1": (16, 16),
    "Status/DOWN2": (16, 16),
    "Status/DOWN3": (16, 16),
    "Status/LIFE": (16, 16),
    "Status/LIFEBAR": (158, 11),
    "Status/LIFEGUAGE": (79, 13),
    "Status/MAGIC0": (16, 16),
    "Status/MAGIC1": (16, 16),
    "Status/MAGIC2": (16, 16),
    "Status/MAGIC3": (16, 16),
    "Status/MIND0": (16, 16),
    "Status/MIND1": (16, 16),
    "Status/MIND2": (16, 16),
    "Status/MIND3": (16, 16),
    "Status/MIND4": (16, 16),
    "Status/MIND5": (16, 16),
    "Status/SUMMON": (16, 16),
    "Status/TARGET": (24, 22),
    "Status/UP0": (16, 16),
    "Status/UP1": (16, 16),
    "Status/UP2": (16, 16),
    "Status/UP3": (16, 16),
    "Stone/HAND0": (14, 14),
    "Stone/HAND1": (14, 14),
    "Stone/HAND2": (14, 14),
    "Stone/HAND3": (14, 14),
    "Stone/HAND4": (14, 14),
    "Stone/HAND5": (14, 14),
    "Stone/HAND6": (14, 14),
    "Stone/HAND7": (14, 14),
    "Stone/HAND8": (14, 14),
    "Stone/HAND9": (14, 14),
}

def get_resourcesize(path):
    """指定されたリソースの標準サイズを返す。"""
    dpath = os.path.basename(os.path.dirname(path))
    fpath = os.path.splitext(os.path.basename(path))[0]
    key = "%s/%s" % (dpath, fpath)
    if key in SIZE_RESOURCES:
        return SIZE_RESOURCES[key]
    else:
        return None

class RecentHistory(object):
    def __init__(self, data):
        """起動してから開いたシナリオの情報を
        (wsn・zipファイルのパス, 最終更新日, "Data/Temp"に展開したフォルダパス)の
        形式で保存し、管理するクラス。
        古い順から"Data/Temp"のフォルダを削除していく。
        data: Settings.xmlのElementTree。
        """
        self.scelist = []
        temppaths = []
        limit = 5

        if data.hasfind("RecentHistory"):
            limit = data.getint("RecentHistory", "limit", 5)
            limit = cw.util.numwrap(limit, 1, 100)

            for e in data.getfind("RecentHistory"):
                path = e.gettext("WsnPath", "")
                temppath = e.gettext("TempPath", "")
                md5 = e.get("md5")

                if os.path.isfile(path) and os.path.isdir(temppath) and md5:
                    self.scelist.append((path, md5, temppath))
                    temppaths.append(temppath)

        temppaths = set(temppaths)
        tempdir = u"Data/Temp/Scenario"

        if os.path.isdir(tempdir):
            for name in os.listdir(tempdir):
                path = cw.util.join_paths(tempdir, name)

                if not path in temppaths:
                    cw.util.remove(path)

        self.set_limit(limit)

    def set_limit(self, value):
        """
        保持履歴数を設定する。
        履歴数を超えたデータは古い順から削除。
        """
        self.limit = value

        while len(self.scelist) > self.limit:
            self.remove()

    def moveend(self, path):
        """
        引数のpathのデータを一番下に移動する。
        """
        seq = [i for i in self.scelist if i[0] == path]

        for i in seq:
            self.scelist.remove(i)
            self.scelist.append(i)

    def append(self, path, temppath, md5=None):
        """
        path: wsn・zipファイルのパス。
        temppath: "Data/Temp"に展開したフォルダパス。
        設定数以上になったら、古いデータから削除。
        """
        path = path.replace("\\", "/")

        if not md5:
            md5 = cw.util.get_md5(path)

        temppath = temppath.replace("\\", "/")
        self.remove(path)
        self.scelist.append((path, md5, temppath))

        while len(self.scelist) > self.limit:
            self.remove()

    def remove(self, path=""):
        """
        path: 登録削除するwsn・zipファイルのパス。
        空の場合は一番先頭にあるデータの登録を削除する。
        """
        if not path:
            cw.util.remove(self.scelist[0][2])
            self.scelist.remove(self.scelist[0])
        else:
            path = path.replace("\\", "/")
            seq = [i for i in self.scelist if i[0] == path]

            for i in seq:
                cw.util.remove(i[2])
                self.scelist.remove(i)

    def check(self, path, md5=None):
        """
        path: チェックするwsn・zipファイルのパス
        "Data/Temp"フォルダに展開済みのwsn・zipファイルかどうかチェックし、
        展開済みだった場合は、展開先のフォルダのパスを返す。
        """
        path = path.replace("\\", "/")

        if not md5:
            md5 = cw.util.get_md5(path)

        seq = []
        seq.extend(self.scelist)

        for i_path, i_md5, i_temppath in seq:
            if not os.path.isfile(i_path) or not os.path.isdir(i_temppath):
                self.remove(i_path)
                continue

            if i_path == path and i_md5 == md5:
                return i_temppath

        return None

class ScenarioCompatibilityTable:
    """互換性データベース。
    *.wsmまたは*.widファイルのMD5ダイジェストをキーに、
    本来そのファイルが再生されるべきCardWirthのバージョンを持つ。
    ここでの判断の優先順位はシナリオのmode.iniより低い。
    互換動作の判断は、
    (1)メッセージ表示時の話者(キャストまたはカード)→(2)使用中のカード
    →(3)エリア・バトル・パッケージ→(4)シナリオ本体
    の優先順位で行う。このデータベースの情報はいずれにも適用される。

    通常シナリオを互換モードで動かすにはSummary.wsmのMD5値をキーに
    バージョンを登録すればよい。
    Unix系列ではmd5コマンドで取得できるが、普通CardWirthのユーザは
    Windowsユーザであるため、PowerShellを使う事になる。例えば:
    $ [string]::concat(([Security.Cryptography.MD5]::Create().ComputeHash((gi Summary.wsm).OpenRead())|%{$_.ToString('x2')}))

    Pythonでは次のようにして取得できる。
    >>> import md5
    >>> md5.new(open("Summary.wsm", "rb").read()).hexdigest()
    """
    def __init__(self):
        self.table = {}
        if os.path.isfile("Data/Compatibility.xml"):
            data = cw.data.xml2element(path="Data/Compatibility.xml")
            for e in data:
                key = e.get("md5", "")
                if key:
                    self.table[key] = e.text

    def get_versionhint(self, fpath=None, filedata=None):
        """fpathのファイル内容またはfiledataから、
        本来そのファイルが再生されるべきCardWirthの
        バージョンを取得する。
        """
        if filedata:
            key = md5.new(filedata).hexdigest()
        else:
            key = cw.util.get_md5(fpath)

        return self.table.get(key, "")

    def lessthan(self, versionhint, currentversion):
        """currentversionがversionhint以下であればTrueを返す。"""
        if not currentversion:
            return False

        try:
            return float(currentversion) <= float(versionhint)
        except:
            return False
