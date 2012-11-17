#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes
import wx
import pygame
from pygame.locals import *

import cw


class Setting(object):
    def __init__(self):
        # フレームレート
        self.fps = 60
        # 1frame分のmillseconds
        self.frametime = 1000 / self.fps
        # Settings
        self._init_settings()
        # シナリオ履歴
        self.recenthistory = RecentHistory(self.data)

    def _init_settings(self):
        # "Settings.xml"がなかったら新しく作る
        if not os.path.isfile("Settings.xml"):
            self.debug = False
            self.vol_bgm = 1.0
            self.vol_midi = 0.2
            self.vol_sound = 1.0
            self.messagespeed = 4
            self.mwincolour = (0, 0, 80, 180)
            self.mwinframecolour = (128, 0, 0, 255)
            self.dealspeed = 7
            self.transition = "None"
            self.transitionspeed = 5
            self.smoothscale_bg = False
            self.skindirname = "Classic"
            self.write()

        self.data = cw.data.xml2etree("Settings.xml")
        data = self.data
        # デバッグモードかどうか
        self.debug = data.getbool("DebugMode", False)
        # 音楽のボリューム(0～1.0)
        self.vol_bgm = data.getint("BgmVolume", 100)
        self.vol_bgm = self.wrap_volumevalue(self.vol_bgm)
        # midi音楽のボリューム(0～1.0)
        self.vol_midi = data.getint("BgmVolume", "midi", 20)
        self.vol_midi = self.wrap_volumevalue(self.vol_midi)
        # 効果音ボリューム
        self.vol_sound = data.getint("SoundVolume", 100)
        self.vol_sound = self.wrap_volumevalue(self.vol_sound)
        # メッセージスピード(数字が小さいほど速い)(0～100)
        self.messagespeed = data.getint("MessageSpeed", 0)
        self.messagespeed = cw.util.numwrap(self.messagespeed, 0, 100)
        # メッセージウィンドウの色と透明度
        r = data.getint("MessageWindowColor", "red", 0)
        g = data.getint("MessageWindowColor", "green", 0)
        b = data.getint("MessageWindowColor", "blue", 80)
        a = data.getint("MessageWindowColor", "alpha", 180)
        self.mwincolour = self.wrap_colorvalue(r, g, b, a)
        r = data.getint("MessageWindowFrameColor", "red", 0)
        g = data.getint("MessageWindowFrameColor", "green", 0)
        b = data.getint("MessageWindowFrameColor", "blue", 80)
        a = data.getint("MessageWindowFrameColor", "alpha", 180)
        self.mwinframecolour = self.wrap_colorvalue(r, g, b, a)
        # カードの表示スピード(数字が小さいほど速い)(1～100)
        dealspeed = data.getint("CardDealingSpeed", 6)
        self.set_dealspeed(dealspeed)
        # トランジション効果の種類
        self.transition = data.gettext("Transition", "Fade")
        self.transitionspeed = data.getint("Transition", "speed", 4)
        self.transitionspeed = cw.util.numwrap(self.transitionspeed, 0, 10)
        # 背景のスムーススケーリング
        self.smoothscale_bg = data.getbool("SmoothScaling", "bg", False)
        # スキン
        self.skindirname = data.gettext("Skin", "Classic")
        self.skindir = cw.util.join_paths(u"Data/Skin", self.skindirname)

        if not os.path.isdir(self.skindir):
            self.skindirname = "Classic"
            self.skindir = cw.util.join_paths(u"Data/Skin", self.skindirname)

            if not os.path.isdir(self.skindir):
                raise ValueError("Not found CardWirthPy skins!")

        path = cw.util.join_paths(self.skindir, "Skin.xml")
        data = cw.data.xml2etree(path)
        self.skinname = data.gettext("/Property/Name", "")
        self.skintype = data.gettext("/Property/Type", "")
        self.skinexts = data.getfind("/Property/Extension").attrib
        # スキン・種族
        self.races = [cw.header.RaceHeader(e) for e in data.getfind("/Races")]
        self.races.append(cw.header.UnknownRaceHeader())

    def set_dealspeed(self, value):
        self.dealspeed = value + 1
        self.dealspeed = cw.util.numwrap(self.dealspeed, 1, 11)
        n = 100 / self.dealspeed
        self.dealing_scales = [100 - n * i for i in xrange(self.dealspeed) if i]

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
        self.fontnames = self.set_systemfonttable()
        # システム効果音(辞書)
        self.sounds = self.get_sounds()
        # wxダイアログのボタン画像(辞書)
        self.buttons = self.get_buttons()
        # カード背景画像(辞書)
        self.cardbgs = self.get_cardbgs()
        # wxダイアログで使う画像(辞書)
        self.dialogs = self.get_dialogs()
        # デバッガで使う画像(辞書)
        self.debugs = self.get_debugs()
        # 特殊文字の画像(辞書)
        self.specialchars_is_changed = False
        self.specialchars = self.get_specialchars()
        # プレイヤカードのステータス画像(辞書)
        self.statuses = self.get_statuses()
        # 適性値・使用回数値画像(辞書)
        self.stones = self.get_stones()
        self.wxstones = self.get_wxstones()
        # 使用フォント(辞書)。スプライトを作成するたびにフォントインスタンスを
        # 新規作成すると重いのであらかじめ用意しておく。
        self.fonts = self.create_fonts()
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
                    raise ValueError(fname + " not found.")

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
            d["gothic"] = u"IPAGothic"
            d["uigothic"] = u"IPAUIGothic"
            d["mincho"] = u"IPAMincho"
            d["pmincho"] = u"IPAPMincho"
            d["pgothic"] = u"IPAPGothic"
            facenames = wx.FontEnumerator().GetFacenames()

            for value in d.itervalues():
                if not value in facenames:
                    raise ValueError("IPA font not found.")

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

    def get_wxfont(self, name="uigothic", size=10,
                        family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD):
        if name == "btnfont" and self._msuigothic:
            fontname = "MS UI Gothic"
        else:
            fontname = self.fontnames[name]

        wxfont = wx.Font(size, family, style, weight, 0, fontname)
        return wxfont

    def create_fonts(self):
        """ゲーム内で頻繁に使用するpygame.Fontはここで設定する。"""
        # 使用フォント(辞書)
        fonts = {}
        # 所持カードの使用回数描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], 16)
        font.set_bold(True)
        fonts["card_uselimit"] = font
        # メニューカードの名前描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], 12)
        font.set_bold(True)
        fonts["mcard_name"] = font
        # プレイヤカードの名前描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], 14)
        font.set_bold(True)
        fonts["pcard_name"] = font
        # プレイヤカードのレベル描画用
        font = pygame.font.Font(self.fontpaths["mincho"], 30)
        font.set_italic(True)
        fonts["pcard_level"] = font
        # メッセージウィンドウのテキスト描画用
        font = pygame.font.Font(self.fontpaths["gothic"], 22)
        fonts["message"] = font
        # メッセージウィンドウの選択肢描画用
        font = pygame.font.Font(self.fontpaths["uigothic"], 17)
        fonts["selectionbar"] = font
        # ステータスバーパネル描画用
        fonts["sbarpanel"] = fonts["pcard_name"]
        # ステータスバーボタン描画用
        fonts["sbarbtn"] = fonts["mcard_name"]
        # ステータス画像の召喚回数描画用
        fonts["statusimg"] = fonts["mcard_name"]
        return fonts

    def create_wxbutton(self, parent, id, size, name=None, bmp=None):
        if name:
            button = wx.Button(parent, id, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("btnfont"))
        elif bmp:
            button = wx.BitmapButton(parent, id, bmp)
            button.SetMinSize(size)

        return button

    def create_wxbtnbmp(self, w, h, flags=0):
        """StatusBarで使用するOSネイティブなボタン画像をwx.Bitmapで出力する。
        w: width
        h: height
        flags: wx.CONTROL_PRESSED, wx.CONTROL_CURRENT and wx.CONTROL_ISDEFAULT
        """
        wxbmp = wx.EmptyBitmap(w, h)
        wxbmp.UseAlpha()
        dc = wx.MemoryDC(wxbmp)
        render = wx.RendererNative.Get()
        render.DrawPushButton(cw.cwpy.frame, dc, (0, 0, w, h), flags)
        dc.EndDrawing()
        # RendererNativeがアルファ値を出力しなかった場合
        wximg = wxbmp.ConvertToImage()
        pixel_num = w * h

        if wximg.GetAlphaData() == "\x00" * pixel_num:
            wximg.SetAlphaData("\xFF" * pixel_num)
            wxbmp = wximg.ConvertToBitmap()

        return wxbmp

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

                d[os.path.splitext(fname)[0]] = resource

        return d

    def get_sounds(self):
        """
        デフォルト効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        func = cw.util.load_sound
        dpath = cw.util.join_paths(self.skindir, "Sound")
        return self.get_resources(func, dpath, self.ext_snd)

    def get_buttons(self):
        """
        ダイアログのボタン画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        func = cw.util.load_wxbmp
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Button")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_stones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        pygameのサーフェスの辞書で返す。
        """
        func = cw.util.load_image
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_wxstones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        func = cw.util.load_wxbmp
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(func, dpath, self.ext_img, True)

    def get_statuses(self):
        """
        ステータス表示に使う画像を読み込んで、
        ("LIFEGUAGE", "TARGET"はマスクする)
        pygameのサーフェスの辞書で返す。
        """
        func = cw.util.load_image
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Status")
        d = self.get_resources(func, dpath, self.ext_img)

        for name in ("LIFEGUAGE", "TARGET"):
            path = cw.util.join_paths(dpath, name + self.ext_img)
            d[name] = cw.util.load_image(path, True)

        return d

    def get_dialogs(self):
        """
        ダイアログで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        func = cw.util.load_wxbmp
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Dialog")
        d = self.get_resources(func, dpath, self.ext_img, True)
        path = cw.util.join_paths(dpath, "CAUTION" + self.ext_img)
        d["CAUTION"] = cw.util.load_wxbmp(path)
        return d

    def get_debugs(self):
        """
        デバッガで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        func = cw.util.load_wxbmp
        dpath = u"Data/Debugger"
        d = self.get_resources(func, dpath, ".png", True)
        return d

    def get_cardbgs(self):
        """
        カードの背景画像を読み込んで、pygameのサーフェス
        ("PREMIER", "RARE", "HOLD", "PENALTY"はマスクする)
        の辞書で返す。
        """
        func = cw.util.load_image
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/CardBg")
        d = self.get_resources(func, dpath, self.ext_img)

        for name in ("HOLD", "PENALTY", "PREMIER", "RARE"):
            path = cw.util.join_paths(dpath, name + self.ext_img)
            d[name] = cw.util.load_image(path, True)

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

class RecentHistory(object):
    def __init__(self, data):
        """起動してから開いたシナリオの情報を
        (wsnファイルのパス, 最終更新日, "Data/Temp"に展開したフォルダパス)の
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
        path: wsnファイルのパス。
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
        path: 登録削除するwsnファイルのパス。
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
        path: チェックするwsnファイルのパス
        "Data/Temp"フォルダに展開済みのwsnファイルかどうかチェックし、
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
