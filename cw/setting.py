#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes
import hashlib
import inspect
import math
import struct
import shutil
import weakref
import array
import re
import threading
import copy
import ConfigParser
import time
import wx
import pygame
import pygame.locals

import cw


class NoFontError(ValueError):
    pass

if sys.platform <> "win32":
    # wx.Appのロード前にフォントをインストールしなければならない
    try:
        fontconfig = ctypes.CDLL("libfontconfig.so")
    except:
        try:
            fontconfig = ctypes.CDLL("libfontconfig.so.1")
        except:
            fontconfig = None
    if fontconfig:
        fcconfig = fontconfig.FcConfigGetCurrent()
        for dpath, dnames, fnames in os.walk(u"Data"):
            for fname in fnames:
                if fname.lower().endswith(".ttf"):
                    path = os.path.join(dpath, fname)
                    if os.path.isfile(path):
                        fontconfig.FcConfigAppFontAddFile(fcconfig, path)

# マウスホイールを上回転させた時の挙動
WHEEL_SELECTION = "Selection" # カードや選択肢を選ぶ
WHEEL_SHOWLOG   = "ShowLog"   # バックログを表示

# カーソルのタイプ
CURSOR_BLACK = "Black" # 黒いカーソル(デフォルト)
CURSOR_WHITE = "White" # 白いカーソル

# メッセージログの表示形式
LOG_SINGLE   = "Single"
LOG_LIST     = "List"
LOG_COMPRESS = "Compress"

# 起動時の挙動
OPEN_TITLE = "Title"
OPEN_LAST_BASE = "LastBase"

# 保存前のダイアログ表示の有無
CONFIRM_BEFORESAVING_YES = "True"
CONFIRM_BEFORESAVING_NO = "False"
CONFIRM_BEFORESAVING_BASE = "BaseOnly" # 宿にいる時に限り表示

# カードの売却・破棄確認ダイアログ表示の有無
CONFIRM_DUMPCARD_ALWAYS = "Always"
CONFIRM_DUMPCARD_SENDTO = "SendOnly"
CONFIRM_DUMPCARD_NO = "False"

# ステータスバーのボタン状態
SB_PRESSED   = 0b00000001 # 押下
SB_CURRENT   = 0b00000010 # カーソル下
SB_DISABLE   = 0b00000100 # 無効状態
SB_NOTICE    = 0b00001000 # 通知
SB_EMPHASIZE = 0b00010000 # 強調


class LocalSetting(object):

    def __init__(self):
        """スキンで上書き可能な設定。"""
        self.important_draw = False
        self.important_font = False

        self.mwincolour = (0, 0, 80, 180)
        self.mwinframecolour = (128, 0, 0, 255)
        self.blwincolour = (80, 80, 80, 180)
        self.blwinframecolour = (128, 128, 128, 255)
        self.curtaincolour = (0, 0, 80, 128)
        self.blcurtaincolour = (0, 0, 0, 192)
        self.fullscreenbackgroundtype = 2
        self.fullscreenbackgroundfile = u"Resource/Image/Dialog/PAD"

        self.decorationfont = False
        self.bordering_cardname = True
        self.fontsmoothing_message = False
        self.fontsmoothing_cardname = False
        self.fontsmoothing_statusbar = True

        self.basefont = {
            "gothic": "",
            "uigothic": "",
            "mincho": "",
            "pmincho": "",
            "pgothic": "",
        }
        self.fonttypes = {
            "button": ("uigothic", "", -1, True, True, False),
            "combo": ("uigothic", "", -1, False, False, False),
            "slider": ("gothic", "", -1, False, False, False),
            "spin": ("gothic", "", -1, False, False, False),
            "tree": ("gothic", "", -1, False, False, False),
            "list": ("uigothic", "", -1, False, False, False),
            "tab": ("uigothic", "", -1, True, True, False),
            "menu": ("uigothic", "", -1, False, False, False),
            "scenario": ("pmincho", "", -1, True, True, False),
            "targetlevel": ("mincho", "", -1, True, True, True),
            "paneltitle": ("uigothic", "", -1, True, True, False),
            "paneltitle2": ("uigothic", "", -1, False, False, False),
            "dlgmsg": ("uigothic", "", -1, True, True, False),
            "dlgmsg2": ("uigothic", "", -1, False, False, False),
            "dlgtitle": ("mincho", "", -1, True, True, False),
            "dlgtitle2": ("mincho", "", -1, True, True, True),
            "createtitle": ("mincho", "", -1, True, True, True),
            "inputname": ("mincho", "", -1, True, True, False),
            "datadesc": ("gothic", "", -1, False, False, False),
            "charadesc": ("mincho", "", -1, True, True, False),
            "charaparam": ("pmincho", "", -1, True, True, True),
            "charaparam2": ("uigothic", "", -1, True, True, False),
            "characre": ("pgothic", "", -1, True, True, False),
            "dlglist": ("mincho", "", -1, True, True, False),
            "uselimit": ("mincho", "", 18, False, False, False),
            "cardname": ("uigothic", "", 12, True, True, False),
            "ccardname": ("uigothic", "", 12, True, True, False),
            "level": ("mincho", "", 33, False, False, True),
            "price": ("mincho", "", 16, True, True, False),
            "numcards": ("uigothic", "", 18, False, False, False),
            "message": ("mincho", "", 22, True, True, False),
            "selectionbar": ("uigothic", "", 14, True, True, False),
            "logpage": ("mincho", "", 24, False, False, False),
            "sbarpanel": ("mincho", "", 16, True, True, False),
            "sbarprogress": ("mincho", "", 16, True, True, False),
            "sbarbtn": ("uigothic", "", 14, True, True, False),
            "statusnum": ("mincho", "", 12, True, True, False),  # 桁が増える毎に-2
            "sbardesctitle": ("pgothic", "", 14, True, True, False),
            "sbardesc": ("pgothic", "", 14, False, False, False),
            "screenshot": ("uigothic", "", 18, False, False, False),
        }

        # Windowsのフォントが使用可能であれば標準フォントを差し替える
        if u"MS UI Gothic" in wx.FontEnumerator.GetFacenames():
            self.basefont["uigothic"] = u"MS UI Gothic"
        if u"ＭＳ 明朝" in wx.FontEnumerator.GetFacenames():
            self.basefont["mincho"] = u"ＭＳ 明朝"
        if u"ＭＳ Ｐ明朝" in wx.FontEnumerator.GetFacenames():
            self.basefont["pmincho"] = u"ＭＳ Ｐ明朝"
        if u"ＭＳ ゴシック" in wx.FontEnumerator.GetFacenames():
            self.basefont["gothic"] = u"ＭＳ ゴシック"
        if u"ＭＳ Ｐゴシック" in wx.FontEnumerator.GetFacenames():
            self.basefont["pgothic"] = u"ＭＳ Ｐゴシック"

        for t in inspect.getmembers(self, lambda t: not inspect.isroutine(t)):
            if not t[0].startswith("__"):
                if isinstance(t[1], list):
                    v = t[1][:]
                elif hasattr(t[1], "copy"):
                    v = t[1].copy()
                else:
                    v = t[1]
                setattr(self, "%s_init" % (t[0]), v)

    def load(self, data):
        """dataから設定をロードする。"""
        self.basefont = self.basefont_init.copy()
        self.fonttypes = self.fonttypes_init.copy()

        # 基本設定を上書きするか。
        self.important_draw = data.getbool(".", "importantdrawing", False)
        self.important_font = data.getbool(".", "importantfont", False)

        # メッセージウィンドウの色と透明度
        r = data.getint("MessageWindowColor", "red", self.mwincolour_init[0])
        g = data.getint("MessageWindowColor", "green", self.mwincolour_init[1])
        b = data.getint("MessageWindowColor", "blue", self.mwincolour_init[2])
        a = data.getint("MessageWindowColor", "alpha", self.mwincolour_init[3])
        self.mwincolour = Setting.wrap_colorvalue(r, g, b, a)
        r = data.getint("MessageWindowFrameColor", "red", self.mwinframecolour_init[0])
        g = data.getint("MessageWindowFrameColor", "green", self.mwinframecolour_init[1])
        b = data.getint("MessageWindowFrameColor", "blue", self.mwinframecolour_init[2])
        a = data.getint("MessageWindowFrameColor", "alpha", self.mwinframecolour_init[3])
        self.mwinframecolour = Setting.wrap_colorvalue(r, g, b, a)
        # バックログウィンドウの色と透明度
        r = data.getint("MessageLogWindowColor", "red", self.blwincolour_init[0])
        g = data.getint("MessageLogWindowColor", "green", self.blwincolour_init[1])
        b = data.getint("MessageLogWindowColor", "blue", self.blwincolour_init[2])
        a = data.getint("MessageLogWindowColor", "alpha", self.blwincolour_init[3])
        self.blwincolour = Setting.wrap_colorvalue(r, g, b, a)
        r = data.getint("MessageLogWindowFrameColor", "red", self.blwinframecolour_init[0])
        g = data.getint("MessageLogWindowFrameColor", "green", self.blwinframecolour_init[1])
        b = data.getint("MessageLogWindowFrameColor", "blue", self.blwinframecolour_init[2])
        a = data.getint("MessageLogWindowFrameColor", "alpha", self.blwinframecolour_init[3])
        self.blwinframecolour = Setting.wrap_colorvalue(r, g, b, a)
        # メッセージログカーテン色
        r = data.getint("MessageLogCurtainColor", "red", self.blcurtaincolour_init[0])
        g = data.getint("MessageLogCurtainColor", "green", self.blcurtaincolour_init[1])
        b = data.getint("MessageLogCurtainColor", "blue", self.blcurtaincolour_init[2])
        a = data.getint("MessageLogCurtainColor", "alpha", self.blcurtaincolour_init[3])
        self.blcurtaincolour = (r, g, b, a)
        # カーテン色
        r = data.getint("CurtainColor", "red", self.curtaincolour_init[0])
        g = data.getint("CurtainColor", "green", self.curtaincolour_init[1])
        b = data.getint("CurtainColor", "blue", self.curtaincolour_init[2])
        a = data.getint("CurtainColor", "alpha", self.curtaincolour_init[3])
        self.curtaincolour = (r, g, b, a)

        # カード名を縁取りする
        self.bordering_cardname = data.getbool("BorderingCardName", self.bordering_cardname_init)
        # メッセージで装飾フォントを使用する
        self.decorationfont = data.getbool("DecorationFont", self.decorationfont_init)
        # メッセージの文字を滑らかにする
        self.fontsmoothing_message = data.getbool("FontSmoothingMessage", self.fontsmoothing_message_init)
        # カード名の文字を滑らかにする
        self.fontsmoothing_cardname = data.getbool("FontSmoothingCardName", self.fontsmoothing_cardname_init)
        # ステータスバーの文字を滑らかにする
        self.fontsmoothing_statusbar = data.getbool("FontSmoothingStatusBar", self.fontsmoothing_statusbar_init)

        # フォント名(空白時デフォルト)
        self.basefont["gothic"] = data.gettext("FontGothic", self.basefont_init["gothic"])
        self.basefont["uigothic"] = data.gettext("FontUIGothic", self.basefont_init["uigothic"])
        self.basefont["mincho"] = data.gettext("FontMincho", self.basefont_init["mincho"])
        self.basefont["pmincho"] = data.gettext("FontPMincho", self.basefont_init["pmincho"])
        self.basefont["pgothic"] = data.gettext("FontPGothic", self.basefont_init["pgothic"])
        # 役割別フォント
        for e in data.getfind("Fonts", raiseerror=False):
            key = e.getattr(".", "key", "")
            if not key or not key in self.fonttypes_init:
                continue
            _deftype, _defname, defpixels, defbold, defbold_upscr, defitalic = self.fonttypes_init[key]

            fonttype = e.getattr(".", "type", "")
            name = e.text if e.text else u""
            pixels = e.getint(".", "pixels", defpixels)
            bold = e.getattr(".", "bold", "")
            if bold == "":
                bold = defbold
            else:
                bold = cw.util.str2bool(bold)
            bold_upscr = e.getattr(".", "expandedbold", "")
            if bold_upscr == "":
                bold_upscr = defbold_upscr
            else:
                bold_upscr = cw.util.str2bool(bold_upscr)
            italic = e.getattr(".", "italic", "")
            if italic == "":
                italic = defitalic
            else:
                italic = cw.util.str2bool(italic)
            self.fonttypes[key] = (fonttype, name, pixels, bold, bold_upscr, italic)

        # フルスクリーン時の背景タイプ(0:無し,1:ファイル指定,2:スキン)
        self.fullscreenbackgroundtype = data.getint("FullScreenBackgroundType", self.fullscreenbackgroundtype_init)
        # フルスクリーン時の背景ファイル
        self.fullscreenbackgroundfile = data.gettext("FullScreenBackgroundFile", self.fullscreenbackgroundfile_init)

    def copy(self):
        return copy.deepcopy(self)


class Setting(object):
    def __init__(self, loadfile=None, init=True):
        # Settings
        self.init_settings(loadfile, init=init)
        # フレームレート
        self.fps = 60
        # 1frame分のmillseconds
        self.frametime = 1000 / self.fps

    def init_settings(self, loadfile=None, init=True):
        path = cw.util.join_paths("Data/SkinBase/Skin.xml")
        basedata = cw.data.xml2etree(path)

        self.skin_local = LocalSetting()

        # "Settings.xml"がなかったら新しく作る
        self.local = LocalSetting()

        self.show_advancedsettings = False
        self.editor = "cwxeditor"
        self.startupscene = OPEN_TITLE
        self.lastyado = ""
        self.lastscenario = []
        self.lastscenariopath = ""
        self.window_position = (None, None)
        self.expanddrawing = 1
        self.expandmode = "FullScreen"
        self.is_expanded = False
        self.smoothexpand = True
        self.debug = False
        self.debug_saved = False
        self.no_levelup_in_debugmode = False
        self.play_bgm = True
        self.play_sound = True
        self.vol_master = 0.75
        self.vol_bgm = 0.4
        self.vol_midi = 1.0
        self.vol_sound = 0.4
        self.soundfonts = [(cw.DEFAULT_SOUNDFONT, True)]
        self.messagespeed = 5
        self.dealspeed = 5
        self.dealspeed_battle = 5
        self.wait_usecard = True
        self.enlarge_beastcardzoomingratio = True
        self.use_battlespeed = False
        self.transition = "Fade"
        self.transitionspeed = 5
        self.smoothscale_bg = False
        self.smoothing_card_up = True
        self.smoothing_card_down = True
        self.caution_beforesaving = True
        self.revert_cardpocket = True
        self.quickdeal = True
        self.all_quickdeal = False
        self.skindirname = "Classic"
        self.vocation120 = False
        self.sort_yado = "Name"
        self.sort_standbys = "None"
        self.sort_parties = "None"
        self.sort_cards = "None"
        self.sort_cardswithstar = True
        self.card_narrow = ""
        self.card_narrowtype = 1
        self.edit_star = False
        self.yado_narrowtype = 1
        self.standbys_narrowtype = 1
        self.parties_narrowtype = 1
        self.infoview_narrowtype = 1
        self.backlogmax = 100
        self.messagelog_type = LOG_COMPRESS
        self.showfps = False
        self.selectscenariofromtype = True
        self.show_unfitnessscenario = True
        self.show_completedscenario = True
        self.show_invisiblescenario = False
        self.wheelup_operation = WHEEL_SHOWLOG
        self.show_allselectedcards = True
        self.confirm_beforeusingcard = True
        self.confirm_beforesaving = CONFIRM_BEFORESAVING_YES
        self.confirm_dumpcard = CONFIRM_DUMPCARD_ALWAYS
        self.show_savedmessage = True
        self.show_backpackcard = True
        self.show_backpackcardatend = False
        self.show_statustime = "NotEventTime"
        self.noticeimpossibleaction = True
        self.initmoneyamount = basedata.getint("Property/InitialCash", 4000)
        self.initmoneyisinitialcash = True
        self.autosave_partyrecord = True
        self.overwrite_partyrecord = True
        self.folderoftype = []
        self.scenario_narrow = ""
        self.scenario_narrowtype = 1
        self.scenario_sorttype = 0
        self.ssinfoformat = u"[%scenario%[(%author%)] - ][%party% at ]%yado%"
        self.ssfnameformat = u"ScreenShot/[%yado%/[%party%_]]%year%%month%%day%_%hour%%minute%%second%[_in_%scenario%].png"
        self.cardssfnameformat = u"ScreenShot/[%yado%/[%party%_]]%year%%month%%day%_%hour%%minute%%second%[_in_%scenario%].png"
        self.titleformat = u"%application% %skin%[ - %yado%[ %scenario%]]"
        self.playlogformat = u"PlayLog/%yado%/%party%_%year%%month%%day%_%hour%%minute%%second%_%scenario%.txt"
        self.ssinfofontcolor = (0, 0, 0, 255)
        self.ssinfobackcolor = (255, 255, 255, 255)
        self.ssinfobackimage = u""
        self.show_fcardsinbattle = False
        self.statusbarmask = True
        self.show_experiencebar = True
        self.show_roundautostartbutton = True
        self.show_autobuttoninentrydialog = True
        self.unconvert_targetfolder = u"UnconvertedYado"
        self.can_skipwait = True
        self.can_skipanimation = True
        self.can_skipwait_with_wheel = True
        self.can_forwardmessage_with_wheel = True
        self.can_repeatlclick = False
        self.cursor_type = CURSOR_WHITE
        self.autoenter_on_sprite = False
        self.blink_statusbutton = True
        self.blink_partymoney = True
        self.show_btndesc = True
        self.protect_staredcard = True
        self.protect_premiercard = True
        self.show_cardkind = True
        self.show_premiumicon = False
        self.can_clicksidesofcardcontrol = True
        self.radius_notdetectmovement = 5
        self.show_paperandtree = False
        self.filer_dir = ""
        self.filer_file = ""
        self.recenthistory_limit = 5 # 展開したシナリオを取っておく数
        self.volume_increment = 5 # ホイールによる全体音量調節での増減量
        self.show_debuglogdialog = False
        self.write_playlog = False
        self.move_repeat = 250 #移動ボタン押しっぱなしの速度
        self.open_lastscenario = True # 最後に表示したシナリオを開くか
        # シナリオ選択ダイアログへシナリオをドロップした時はインストールダイアログを表示する
        # Falseの場合は常に検索結果として表示
        self.can_installscenariofromdrop = False
        # シナリオのインストールに成功したら元ファイルを削除する
        self.delete_sourceafterinstalled = False
        # アップデートに伴うファイルの自動移動・削除を行う
        self.auto_update_files = True
        # フォント表示例のフォーマット
        self.fontexampleformat = "%fontface%"

        # 絞り込み・整列などのコントロールの表示有無
        self.show_additional_yado = False
        self.show_additional_player = False
        self.show_additional_party = False
        self.show_additional_scenario = False
        self.show_additional_card = False
        # 表示有無切替ボタン自体の表示有無
        self.show_addctrlbtn = True

        # カード種の表示・非表示
        self.show_cardtype = [True] * 3
        # カード選択ダイアログで選択中のカード種別
        self.last_cardpocket = 0
        # カード選択ダイアログでの転送先
        self.last_sendto = 0
        # カード選択ダイアログでのページ
        self.last_storehousepage = 0
        self.last_backpackpage = 0
        self.last_cardpocketbpage = [0] * 3 # 荷物袋からの使用

        # 一覧表示
        self.show_multiplebases = False
        self.show_multipleparties = False
        self.show_multipleplayers = False
        self.show_scenariotree = False

        # シナリオのインストール先(キー=ルートディレクトリ毎)
        self.installed_dir = {}

        # カード編集ダイアログのブックマーク
        self.bookmarks_for_cardedit = []

        for t in inspect.getmembers(self, lambda t: not inspect.isroutine(t)):
            if not t[0].startswith("__"):
                if isinstance(t[1], list):
                    v = t[1][:]
                elif hasattr(t[1], "copy"):
                    v = t[1].copy()
                else:
                    v = t[1]
                setattr(self, "%s_init" % (t[0]), v)

        if not init:
            return

        if not loadfile:
            if not os.path.isfile("Settings.xml"):
                self.write()
                self.init_skin()
                self.set_dealspeed(self.dealspeed, self.dealspeed_battle, self.use_battlespeed)
                self.data = cw.data.xml2etree("Settings.xml")
                return

            self.data = cw.data.xml2etree("Settings.xml")
        elif os.path.isfile(loadfile):
            self.data = cw.data.xml2etree(loadfile)
        else:
            return

        data = self.data
        settings_version = data.getattr(".", "dataVersion", "0")

        self.local.load(data)

        # 最初から詳細モードで設定を行う
        self.show_advancedsettings = data.getbool("ShowAdvancedSettings", self.show_advancedsettings)

        # シナリオエディタ
        self.editor = data.gettext("ScenarioEditor", self.editor)

        # 起動時の動作
        self.startupscene = data.gettext("StartupScene", self.startupscene)
        # 最後に選択した宿
        self.lastyado = data.gettext("LastYado", self.lastyado)
        # 最後に選択したシナリオ(ショートカットがあるため経路を記憶)
        self.lastscenario = []
        self.lastscenariopath = "" # 経路が辿れない時に使用するフルパス
        # ウィンドウ位置
        win_x = data.getint("WindowPosition", "left", -sys.maxint-1)
        win_y = data.getint("WindowPosition", "top", -sys.maxint-1)
        if -sys.maxint-1 == win_x:
            win_x = None
        if -sys.maxint-1 == win_y:
            win_y = None
        self.window_position = (win_x, win_y)
        # 拡大モード
        self.expandmode = data.gettext("ExpandMode", self.expandmode)
        if self.expandmode == "None":
            self.is_expanded = False
        else:
            self.is_expanded = data.getbool("ExpandMode", "expanded", self.is_expanded)
        self.smoothexpand = data.getbool("ExpandMode", "smooth", self.smoothexpand)
        # 描画倍率
        if self.expandmode in ("None", "FullScreen"):
            self.expanddrawing = 1.0
        else:
            try:
                self.expanddrawing = float(self.expandmode)
            except:
                self.expanddrawing = 1.0
        self.expanddrawing = data.getfloat("ExpandDrawing", self.expanddrawing)
        if self.expanddrawing % 1 == 0:
            self.expanddrawing = int(self.expanddrawing)
        # デバッグモードかどうか
        self.debug = data.getbool("DebugMode", self.debug)
        self.debug_saved = self.debug
        if not loadfile:
            if cw.OPTIONS.debug:
                # 強制デバッグモード起動
                self.debug = True
            cw.OPTIONS.debug = False
        # シナリオの終了時にデバッグ情報を表示する
        self.show_debuglogdialog = data.getbool("ShowDebugLogDialog", self.show_debuglogdialog)
        # デバッグ時はレベル上昇しない
        self.no_levelup_in_debugmode = data.getbool("NoLevelUpInDebugMode", self.no_levelup_in_debugmode)
        # 音楽を再生する
        self.play_bgm = data.getbool("PlayBgm", self.play_bgm)
        # 効果音を再生する
        self.play_sound = data.getbool("PlaySound", self.play_sound)
        # 音声全体のボリューム(0～1.0)
        self.vol_master = data.getint("MasterVolume", int(self.vol_master*100))
        self.vol_master = Setting.wrap_volumevalue(self.vol_master)
        # 音楽のボリューム(0～1.0)
        self.vol_bgm = data.getint("BgmVolume", int(self.vol_bgm*100))
        self.vol_bgm = Setting.wrap_volumevalue(self.vol_bgm)
        # midi音楽のボリューム(0～1.0)
        self.vol_midi = data.getint("BgmVolume", "midi", int(self.vol_midi*100))
        self.vol_midi = Setting.wrap_volumevalue(self.vol_midi)
        # 効果音ボリューム
        self.vol_sound = data.getint("SoundVolume", int(self.vol_sound*100))
        self.vol_sound = Setting.wrap_volumevalue(self.vol_sound)
        # MIDIサウンドフォント
        elements = data.find("SoundFonts", False)
        if not elements is None:
            self.soundfonts = []
            for e in elements:
                use = e.getbool(".", "enabled", True)
                self.soundfonts.append((e.text, use))
        # メッセージスピード(数字が小さいほど速い)(0～100)
        self.messagespeed = data.getint("MessageSpeed", self.messagespeed)
        self.messagespeed = cw.util.numwrap(self.messagespeed, 0, 100)
        # カードの表示スピード(数字が小さいほど速い)(1～100)
        dealspeed = data.getint("CardDealingSpeed", self.dealspeed)
        # 戦闘行動の表示スピード(数字が小さいほど速い)(1～100)
        dealspeed_battle = data.getint("CardDealingSpeedInBattle", self.dealspeed_battle)
        use_battlespeed = data.getbool("CardDealingSpeedInBattle", "enabled", self.use_battlespeed)
        self.set_dealspeed(dealspeed, dealspeed_battle, use_battlespeed)
        # カードの使用前に空白時間を入れる
        self.wait_usecard = data.getbool("WaitUseCard", self.wait_usecard)
        # 召喚獣カードの拡大率を大きくする
        self.enlarge_beastcardzoomingratio = data.getbool("EnlargeBeastCardZoomingRatio", self.enlarge_beastcardzoomingratio)
        # トランジション効果の種類
        self.transition = data.gettext("Transition", self.transition)
        self.transitionspeed = data.getint("Transition", "speed", self.transitionspeed)
        self.transitionspeed = cw.util.numwrap(self.transitionspeed, 0, 10)
        # 背景のスムーススケーリング
        self.smoothscale_bg = data.getbool("SmoothScaling", "bg", self.smoothscale_bg)
        self.smoothing_card_up = data.getbool("SmoothScaling", "upcard", self.smoothing_card_up)
        self.smoothing_card_down = data.getbool("SmoothScaling", "downcard", self.smoothing_card_down)
        # 保存せずに終了しようとしたら警告
        self.caution_beforesaving = data.getbool("CautionBeforeSaving", self.caution_beforesaving)
        # レベル調節で手放したカードを自動的に戻す
        self.revert_cardpocket = data.getbool("RevertCardPocket", self.revert_cardpocket)
        # キャンプ等に高速で切り替える
        self.quickdeal = data.getbool("QuickDeal", self.quickdeal)
        # 全てのシステムカードを高速表示する
        self.all_quickdeal = data.getbool("AllQuickDeal", self.all_quickdeal)
        # ソート基準
        self.sort_yado = data.getattr("SortKey", "yado", self.sort_yado)
        self.sort_standbys = data.getattr("SortKey", "standbys", self.sort_standbys)
        self.sort_parties = data.getattr("SortKey", "parties", self.sort_parties)
        self.sort_cards = data.getattr("SortKey", "cards", self.sort_cards)
        self.sort_cardswithstar = data.getbool("SortKey", "cardswithstar", self.sort_cardswithstar)
        # 拠点絞込条件
        self.yado_narrowtype = data.getint("YadoNarrowType", self.yado_narrowtype)
        # 宿帳絞込条件
        self.standbys_narrowtype = data.getint("StandbysNarrowType", self.standbys_narrowtype)
        # パーティ絞込条件
        self.parties_narrowtype = data.getint("PartiesNarrowType", self.parties_narrowtype)
        # カード絞込条件
        self.card_narrowtype = data.getint("CardNarrowType", self.card_narrowtype)
        # 情報カード絞込条件
        self.infoview_narrowtype = data.getint("InfoViewNarrowType", self.infoview_narrowtype)
        # メッセージログ最大数
        self.backlogmax = data.getint("MessageLogMax", self.backlogmax)
        # メッセージログ表示形式
        self.messagelog_type = data.gettext("MessageLogType", self.messagelog_type)

        self.showfps = False

        # スキンによってシナリオの選択開始位置を変更する
        self.selectscenariofromtype = data.getbool("SelectScenarioFromType", self.selectscenariofromtype)
        # 適正レベル以外のシナリオを表示する
        self.show_unfitnessscenario = data.getbool("ShowUnfitnessScenario", self.show_unfitnessscenario)
        # 隠蔽シナリオを表示する
        self.show_completedscenario = data.getbool("ShowCompletedScenario", self.show_completedscenario)
        # 終了済シナリオを表示する
        self.show_invisiblescenario = data.getbool("ShowInvisibleScenario", self.show_invisiblescenario)

        # マウスホイールを上回転させた時の挙動
        self.wheelup_operation = data.gettext("WheelUpOperation", self.wheelup_operation)
        # 戦闘行動を全員分表示する
        self.show_allselectedcards = data.getbool("ShowAllSelectedCards", self.show_allselectedcards)
        # カード使用時に確認ダイアログを表示
        self.confirm_beforeusingcard = data.getbool("ConfirmBeforeUsingCard", self.confirm_beforeusingcard)
        # セーブ前に確認ダイアログを表示
        self.confirm_beforesaving = data.gettext("ConfirmBeforeSaving", self.confirm_beforesaving)
        # セーブ完了時に確認ダイアログを表示
        self.show_savedmessage = data.getbool("ShowSavedMessage", self.show_savedmessage)
        # カードの売却と破棄で確認ダイアログを表示
        self.confirm_dumpcard = data.gettext("ConfirmBeforeDumpCard", self.confirm_dumpcard_init)

        # 不可能な行動を選択した時に警告を表示
        self.noticeimpossibleaction = data.getbool("NoticeImpossibleAction", self.noticeimpossibleaction)

        # 荷物袋のカードを一時的に取り出して使えるようにする
        self.show_backpackcard = data.getbool("ShowBackpackCard", self.show_backpackcard)
        # 荷物袋カードを最後に配置する
        self.show_backpackcardatend = data.getbool("ShowBackpackCardAtEnd", self.show_backpackcardatend)
        # 各種ステータスの残り時間を表示する
        self.show_statustime = data.gettext("ShowStatusTime", self.show_statustime)

        # パーティ結成時の持出金額
        self.initmoneyamount = data.getint("InitialMoneyAmount", self.initmoneyamount)
        self.initmoneyisinitialcash = data.getbool("InitialMoneyAmount", "sameasbase", self.initmoneyisinitialcash)

        # 解散時、自動的にパーティ情報を記録する
        self.autosave_partyrecord = data.getbool("AutoSavePartyRecord", self.autosave_partyrecord)
        # 自動記録時、同名のパーティ記録へ上書きする
        self.overwrite_partyrecord = data.getbool("OverwritePartyRecord", self.overwrite_partyrecord)

        # シナリオフォルダ(スキンタイプ別)
        for e_folder in data.getfind("ScenarioFolderOfSkinType", False):
            skintype = e_folder.getattr(".", "skintype", "")
            folder = e_folder.gettext(".", "")
            self.folderoftype.append((skintype, folder))

        # シナリオ絞込・整列条件
        self.scenario_narrowtype = data.getint("ScenarioNarrowType", self.scenario_narrowtype)
        self.scenario_sorttype = data.getint("ScenarioSortType", self.scenario_sorttype)

        # スクリーンショット情報
        self.ssinfoformat = data.gettext("ScreenShotInformationFormat", self.ssinfoformat)
        # スクリーンショット情報の色
        r = data.getint("ScreenShotInformationFontColor", "red", self.ssinfofontcolor[0])
        g = data.getint("ScreenShotInformationFontColor", "green", self.ssinfofontcolor[1])
        b = data.getint("ScreenShotInformationFontColor", "blue", self.ssinfofontcolor[2])
        self.ssinfofontcolor = (r, g, b, 255)
        r = data.getint("ScreenShotInformationBackgroundColor", "red", self.ssinfobackcolor[0])
        g = data.getint("ScreenShotInformationBackgroundColor", "green", self.ssinfobackcolor[1])
        b = data.getint("ScreenShotInformationBackgroundColor", "blue", self.ssinfobackcolor[2])
        self.ssinfobackcolor = (r, g, b, 255)
        # スクリーンショット情報の背景イメージ
        self.ssinfobackimage = data.gettext("ScreenShotInformationBackgroundImage", self.ssinfobackimage_init)

        # スクリーンショットのファイル名
        self.ssfnameformat = data.gettext("ScreenShotFileNameFormat", self.ssfnameformat)
        # 所持カード撮影情報のファイル名
        self.cardssfnameformat = data.gettext("ScreenShotOfCardsFileNameFormat", self.cardssfnameformat)

        # イベント中にステータスバーの色を変える
        self.statusbarmask = data.getbool("StatusBarMask", self.statusbarmask)

        # 次のレベルアップまでの割合を表示する
        self.show_experiencebar = data.getbool("ShowExperienceBar", self.show_experiencebar)

        # バトルラウンドを自動開始可能にする
        self.show_roundautostartbutton = data.getbool("ShowRoundAutoStartButton", self.show_roundautostartbutton)

        # 新規登録ダイアログに自動ボタンを表示する
        self.show_autobuttoninentrydialog = data.getbool("ShowAutoButtonInEntryDialog", self.show_autobuttoninentrydialog)

        # 逆変換先ディレクトリ
        self.unconvert_targetfolder = data.gettext("UnconvertTargetFolder", self.unconvert_targetfolder)

        # 空白時間をスキップ可能にする
        self.can_skipwait = data.getbool("CanSkipWait", self.can_skipwait)
        # アニメーションをスキップ可能にする
        self.can_skipanimation = data.getbool("CanSkipAnimation", self.can_skipanimation)
        # マウスのホイールで空白時間とアニメーションをスキップする
        self.can_skipwait_with_wheel = data.getbool("CanSkipWaitWithWheel", self.can_skipwait_with_wheel)
        # マウスのホイールでメッセージ送りを行う
        self.can_forwardmessage_with_wheel = data.getbool("CanForwardMessageWithWheel", self.can_forwardmessage_with_wheel)
        # マウスの左ボタンを押し続けた時は連打状態にする
        self.can_repeatlclick = data.getbool("CanRepeatLClick", self.can_repeatlclick)
        # 方向キーやホイールの選択中にマウスカーソルの移動を検知しない半径
        self.radius_notdetectmovement = data.getint("RadiusForNotDetectingCursorMovement", self.radius_notdetectmovement)
        # カーソルタイプ
        self.cursor_type = data.gettext("CursorType", self.cursor_type)
        # 連打状態の時、カードなどの選択を自動的に決定する
        self.autoenter_on_sprite = data.getbool("AutoEnterOnSprite", self.autoenter_on_sprite)
        # 通知のあるステータスボタンを点滅させる
        self.blink_statusbutton = data.getbool("BlinkStatusButton", self.blink_statusbutton)
        # 所持金が増減した時に所持金欄を点滅させる
        self.blink_partymoney = data.getbool("BlinkPartyMoney", self.blink_partymoney)
        # ステータスバーのボタンの解説を表示する
        self.show_btndesc = data.getbool("ShowButtonDescription", self.show_btndesc)
        # スターつきのカードの売却や破棄を禁止する
        self.protect_staredcard = data.getbool("ProtectStaredCard", self.protect_staredcard)
        # プレミアカードの売却や破棄を禁止する
        self.protect_premiercard = data.getbool("ProtectPremierCard", self.protect_premiercard)
        # カード置場と荷物袋でカードの種類を表示する
        self.show_cardkind = data.getbool("ShowCardKind", self.show_cardkind)
        # カードの希少度をアイコンで表示する
        self.show_premiumicon = data.getbool("ShowPremiumIcon", self.show_premiumicon)
        # カード選択ダイアログの背景クリックで左右移動を行う
        self.can_clicksidesofcardcontrol = data.getbool("CanClickSidesOfCardControl", self.can_clicksidesofcardcontrol)
        # シナリオ選択ダイアログで貼紙と一覧を同時に表示する
        self.show_paperandtree = data.getbool("ShowPaperAndTree", self.show_paperandtree)
        # シナリオ選択ダイアログでのファイラー
        self.filer_dir = data.gettext("FilerDirectory", self.filer_dir)
        self.filer_file = data.gettext("FilerFile", self.filer_file)

        # 圧縮されたシナリオの展開データ保存数
        self.recenthistory_limit = data.getint("RecentHistoryLimit", self.recenthistory_limit)

        # マウスホイールによる全体音量の増減量
        self.volume_increment = data.getint("VolumeIncrement", self.volume_increment)

        # 一覧表示
        self.show_multiplebases = data.getbool("ShowMultipleItems", "base", self.show_multiplebases)
        self.show_multipleparties = data.getbool("ShowMultipleItems", "party", self.show_multipleparties)
        self.show_multipleplayers = data.getbool("ShowMultipleItems", "player", self.show_multipleplayers)
        self.show_scenariotree = data.getbool("ShowMultipleItems", "scenario", self.show_scenariotree)

        # タイトルバーの表示内容
        self.titleformat = data.gettext("TitleFormat", self.titleformat)

        # 絞り込み・整列などのコントロールの表示有無
        self.show_additional_yado = data.getbool("ShowAdditionalControls", "yado", self.show_additional_yado)
        self.show_additional_player = data.getbool("ShowAdditionalControls", "player", self.show_additional_player)
        self.show_additional_party = data.getbool("ShowAdditionalControls", "party", self.show_additional_party)
        self.show_additional_scenario = data.getbool("ShowAdditionalControls", "scenario", self.show_additional_scenario)
        self.show_additional_card = data.getbool("ShowAdditionalControls", "card", self.show_additional_card)
        # 絞り込み等の表示切替ボタンを表示する
        self.show_addctrlbtn = data.gettext("ShowAdditionalControls", "" if self.show_addctrlbtn else "Hidden") <> "Hidden"

        # シナリオのプレイログを出力する
        self.write_playlog = data.getbool("WritePlayLog", self.write_playlog)
        # プレイログのフォーマット
        self.playlogformat = data.gettext("PlayLogFormat", self.playlogformat)

        # 最後に選んだシナリオを開始位置にする
        self.open_lastscenario = data.getbool("OpenLastScenario", self.open_lastscenario)
        # ドロップによるシナリオのインストールを可能にする
        self.can_installscenariofromdrop = data.getbool("CanInstallScenarioFromDrop", self.can_installscenariofromdrop)
        # シナリオのインストールに成功したら元ファイルを削除する
        self.delete_sourceafterinstalled = data.getbool("DeleteSourceAfterInstalled", self.delete_sourceafterinstalled)

        # アップデートに伴うファイルの自動移動・削除を行う
        self.auto_update_files = data.getbool("AutoUpdateFiles", self.auto_update_files_init)

        # フォント表示例のフォーマット
        self.fontexampleformat = data.gettext("FontExampleFormat", self.fontexampleformat_init)

        # シナリオのインストール先(キー=ルートディレクトリ)
        e = data.find("InstalledPaths")
        if not e is None:
            for e_paths in e:
                rootdir = e_paths.getattr(".", "root", "")
                if not rootdir:
                    continue
                dirstack = []
                for e_path in e_paths:
                    if e_path.text:
                        dirstack.append(e_path.text)
                self.installed_dir[rootdir] = dirstack

        # カード編集ダイアログのブックマーク
        e = data.find("BookmarksForCardEditor")
        if not e is None:
            for e_bookmark in e:
                fpath = e_bookmark.text
                name = e_bookmark.getattr(".", "name", u"")
                self.bookmarks_for_cardedit.append((fpath, name))

        # スキン
        self.skindirname = data.gettext("Skin", self.skindirname)
        if not loadfile:
            self.init_skin(basedata=basedata)

            # 設定バージョンの更新
            if int(settings_version) < 1:
                # バージョン0ではスキンに
                # 「メッセージでクラシックなフォントを使用する」が
                # 存在するため、それを使用中の場合に限り
                # デフォルトフォントをクラシックなものに初期化する
                if self._classicstyletext:
                    self.local.fontsmoothing_message = False
                    self.local.fonttypes["message"] = self.local.fonttypes_init["message"]
                    self.local.fonttypes["selectionbar"] = self.local.fonttypes_init["selectionbar"]
                else:
                    self.local.fontsmoothing_message = True

            if int(settings_version) < 2:
                # バージョン1ではカード名のスムージングはデフォルトでオン
                # スムージング設定がデフォルト値でカード名フォントの設定を
                # 変更している場合は、スムージングを改めてオンにする
                if not self.local.fontsmoothing_cardname and\
                        (self.local.fonttypes["cardname"] <> self.local.fonttypes_init["cardname"] or \
                         self.local.fonttypes["ccardname"] <> self.local.fonttypes_init["ccardname"]):
                    self.local.fontsmoothing_cardname = True

            if int(settings_version) < 3:
                # バージョン2→3でカードの回転速度を(dealspeed+1)*1.2からdealspeed+1に変更
                if 4 <= self.dealspeed:
                    self.dealspeed += 1
                    self.dealspeed = cw.util.numwrap(self.dealspeed, 0, 10)
                if 4 <= self.dealspeed_battle:
                    self.dealspeed_battle += 1
                    self.dealspeed_battle = cw.util.numwrap(self.dealspeed, 0, 10)
                self.set_dealspeed(self.dealspeed, self.dealspeed_battle, self.use_battlespeed)

    def init_skin(self, basedata=None):
        self.skindir = cw.util.join_paths(u"Data/Skin", self.skindirname)
        if self.auto_update_files:
            cw.update.update_files(self.skindir, self.skindirname)
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

        if basedata is None:
            path = cw.util.join_paths("Data/SkinBase/Skin.xml")
            basedata = cw.data.xml2etree(path)
        path = cw.util.join_paths(self.skindir, "Skin.xml")
        data = self._update_skin(path)
        err = self._check_skin()
        if err:
            dlg = wx.MessageDialog(None, err, u"スキンチェックエラー", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            raise
        self.skinname = data.gettext("Property/Name", "")
        self.skintype = data.gettext("Property/Type", "")
        self.vocation120 = data.getbool("Property/CW120VocationLevel", False)
        self._classicstyletext = data.getbool("Property/ClassicStyleText", False) # 設定バージョンアップデート用
        self.initialcash = data.getint("Property/InitialCash", basedata.getint("Property/InitialCash", 4000))
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
        self.msgs = _MsgDict()
        for e in basedata.getfind("Messages"):
            self.msgs[e.getattr(".", "key", "")] = e.gettext(".", "")
        for e in data.getfind("Messages"):
            self.msgs[e.getattr(".", "key", "")] = e.gettext(".", "")

        # 未指定種族
        self.unknown_race = cw.header.UnknownRaceHeader(self)
        self.races.append(self.unknown_race)

        # スキン判別用クーポン
        syscoupons = data.find("SystemCoupons")
        self.skinsyscoupons = SystemCoupons(fpath="", data=syscoupons)

        # スキンローカル設定
        data = data.find("Settings")
        if data is None:
            self.skin_local = self.local.copy()
        else:
            self.skin_local.load(data)

    def _update_skin(self, path):
        """旧バージョンのデータの誤りを訂正する。
        """
        dpath = os.path.dirname(path)
        while not cw.util.create_mutex(dpath):
            time.sleep(0.001)

        try:
            data = cw.data.xml2etree(path)

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

            if skinversion <= 5:
                # dataVersion=5までは
                # MenuCardにPostEventのパラメータを直接持たせる事はできなかった。
                # dataVersion=6以降は単純なPostEvent実行のみのMenuCardは
                # それ自体にcommandとargパラメータを持たせ、Eventsは空でよい。
                update = True

                # バックアップを作成
                iver = skinversion
                if iver % 1 == 0:
                    iver = int(iver)
                for dname in (u"GameOver", u"Scenario", u"Title", u"Yado"):
                    dpath = cw.util.join_paths(self.skindir, u"Resource/Xml", dname)
                    dst = "%s_v%s" % (dpath, iver)
                    dst = cw.util.dupcheck_plus(dst, yado=False)
                    shutil.copytree(dpath, dst)

                for dname in (u"GameOver", u"Scenario", u"Title", u"Yado"):
                    dpath = cw.util.join_paths(self.skindir, u"Resource/Xml", dname)
                    for fname in os.listdir(dpath):
                        ext = os.path.splitext(fname)[1].lower()
                        if ext <> ".xml":
                            continue
                        fpath = cw.util.join_paths(dpath, fname)
                        e = cw.data.xml2etree(fpath)
                        updatemcards = False
                        for me in e.getfind("MenuCards"):
                            events = me.getfind("Events")
                            if 1 <> len(events):
                                continue
                            ignum = events.gettext("Event/Ignitions/Number", "")
                            igkeycode = events.gettext("Event/Ignitions/KeyCodes", "")
                            if ignum <> "1" or igkeycode <> "":
                                continue
                            post = me.find("Events/Event/Contents/Start/Contents/Post")
                            posttype = post.getattr(".", "type", "")
                            if posttype <> "Event":
                                continue
                            command = post.getattr(".", "command", "")
                            arg = post.getattr(".", "arg", "")
                            if not command:
                                continue
                            me.attrib["command"] = command
                            if arg:
                                me.attrib["arg"] = arg
                            events.clear()
                            updatemcards = True
                        if updatemcards:
                            e.write()

            if skinversion <= 6:
                # dataVersion=6までは標準混乱カードの効果が
                # 回避・抵抗共に-5だったが、CardWirthでは-10なので
                # 7以降それに合わせる。
                update = True

                # バックアップを作成
                iver = skinversion
                if iver % 1 == 0:
                    iver = int(iver)
                fpath = cw.util.join_paths(self.skindir, u"Resource/Xml/ActionCard/-1_Confuse.xml")
                dst = "%s.v%s" % (fpath, iver)
                dst = cw.util.dupcheck_plus(dst, yado=False)
                shutil.copy2(fpath, dst)
                e = cw.data.xml2etree(fpath)
                avoid = e.getint("Property/Enhance", "avoid", -10)
                if avoid == -5:
                    e.edit("Property/Enhance", "-10", "avoid")
                resist = e.getint("Property/Enhance", "resist", -10)
                if resist == -5:
                    e.edit("Property/Enhance", "-10", "resist")
                e.write()

            if skinversion <= 8:
                # dataVersion=8までは`03_YadoInitial.xml`
                # (データ無し宿で表示されるエリア)が存在しなかったので生成。
                # タイトル画面のカード位置も調節する。
                update = True

                fpath = cw.util.join_paths(self.skindir, u"Resource/Xml/Title/01_Title.xml")
                if os.path.isfile(fpath):
                    # タイトル画面のカード位置を調節
                    e = cw.data.xml2etree(fpath)
                    e_mcards = e.find("MenuCards")
                    if not e_mcards is None and len(e_mcards) == 2 and\
                            e_mcards.getattr(".", "spreadtype", "") == "Custom" and\
                            e_mcards[0].getint("Property/Location", "left", 0) == 231 and\
                            e_mcards[0].getint("Property/Location", "top", 0) == 156 and\
                            e_mcards[1].getint("Property/Location", "left", 0) == 316 and\
                            e_mcards[1].getint("Property/Location", "top", 0) == 156:
                        # バックアップを作成
                        iver = skinversion
                        if iver % 1 == 0:
                            iver = int(iver)
                        dst = "%s.v%s" % (fpath, iver)
                        dst = cw.util.dupcheck_plus(dst, yado=False)
                        shutil.copy2(fpath, dst)
                        e.edit("MenuCards/MenuCard[1]/Property/Location", "233", "left")
                        e.edit("MenuCards/MenuCard[1]/Property/Location", "150", "top")
                        e.edit("MenuCards/MenuCard[2]/Property/Location", "318", "left")
                        e.edit("MenuCards/MenuCard[2]/Property/Location", "150", "top")
                        e.write()

                fpath1 = u"Data/SkinBase/Resource/Xml/Yado/03_YadoInitial.xml"
                fpath2 = cw.util.join_paths(self.skindir, u"Resource/Xml/Yado/03_YadoInitial.xml")
                if not os.path.isfile(fpath2):
                    shutil.copy2(fpath1, fpath2)
                    fpath3 = cw.util.join_paths(self.skindir, u"Resource/Xml/Yado/01_Yado.xml")
                    if os.path.isfile(fpath3):
                        e = cw.data.xml2etree(fpath2)
                        e3 = cw.data.xml2etree(fpath3)
                        e_playerselect = None
                        e_returntitle = None
                        for e_mcard in e3.getfind("MenuCards", raiseerror=False):
                            command = e_mcard.getattr(".", "command", "")
                            arg = e_mcard.getattr(".", "arg", "")
                            if command == "ShowDialog" and arg == "PLAYERSELECT":
                                e_playerselect = e_mcard
                            elif command == "ShowDialog" and arg == "RETURNTITLE":
                                e_returntitle = e_mcard
                        if not e_playerselect is None:
                            e.edit("MenuCards/MenuCard[1]/Property/Name",
                                   e_playerselect.gettext("Property/Name"))
                            e.edit("MenuCards/MenuCard[1]/Property/ImagePath",
                                   e_playerselect.gettext("Property/ImagePath"))
                            e.edit("MenuCards/MenuCard[1]/Property/Description",
                                   e_playerselect.gettext("Property/Description"))
                        if not e_returntitle is None:
                            e.edit("MenuCards/MenuCard[2]/Property/Name",
                                   e_returntitle.gettext("Property/Name"))
                            e.edit("MenuCards/MenuCard[2]/Property/ImagePath",
                                   e_returntitle.gettext("Property/ImagePath"))
                            e.edit("MenuCards/MenuCard[2]/Property/Description",
                                   e_returntitle.gettext("Property/Description"))
                        e_bgimgs = e3.find("BgImages")
                        if not e_bgimgs is None:
                            e.remove(".", e.find("BgImages"))
                            e.insert(".", e_bgimgs, 1)
                        e_event = e3.find("Events")
                        if not e_event is None:
                            e.remove(".", e.find("Events"))
                            e.append(".", e_event)
                        e.write()

            if skinversion <= 9:
                fpath1 = u"Data/SkinBase/Resource/Xml/Animation/Opening.xml"
                fpath2 = cw.util.join_paths(self.skindir, u"Resource/Xml/Animation/Opening.xml")
                if not os.path.isfile(fpath2):
                    dpath = os.path.dirname(fpath2)
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    shutil.copy2(fpath1, fpath2)
                update = True

            if update:
                data.edit(".", "10", "dataVersion")
                data.write()

            return data

        finally:
            cw.util.release_mutex()

    def _check_skin(self):
        """
        必須リソースが欠けていないかチェックする。
        今のところ、全てのリソースをチェックしているのではなく、
        過去のアップデートで追加されたリソースのみ確認している。
        """
        dpath = cw.util.join_paths(self.skindir, u"Resource/Xml/Yado")
        for fname in os.listdir(dpath):
            fpath = cw.util.join_paths(dpath, fname)
            id = int(cw.header.GetName(fpath, tagname="Id").name)
            if id == 3:
                break
        else:
            return u"スキンにデータバージョン「9」で導入された「初期拠点」エリアが存在しません。\n" +\
                   u"スキンの自動アップデートに失敗した可能性があります。\n" +\
                   u"手動での修復を試みるか、スキンを再導入してください。"

        fpath = cw.util.join_paths(self.skindir, u"Resource/Xml/Animation/Opening.xml")
        if not os.path.isfile(fpath):
            return u"スキンにデータバージョン「10」で導入されたオープニングアニメーション定義が存在しません。\n" + \
                   u"スキンの自動アップデートに失敗した可能性があります。\n" + \
                   u"手動での修復を試みるか、スキンを再導入してください。"

        return u""

    def set_dealspeed(self, value, battlevalue, usebattle):
        self.dealspeed = value
        self.dealspeed = cw.util.numwrap(self.dealspeed, 0, 10)
        scales_len = self.dealspeed + 1
        self.dealing_scales = [
            int(math.cos(math.radians(90.0 * i / scales_len)) * 100)
            for i in xrange(scales_len)
                if i
        ]

        self.dealspeed_battle = battlevalue
        self.dealspeed_battle = cw.util.numwrap(self.dealspeed_battle, 0, 10)
        scales_len = self.dealspeed_battle + 1
        self.dealing_scales_battle = [
            int(math.cos(math.radians(90.0 * i / scales_len)) * 100)
            for i in xrange(scales_len)
                if i
        ]

        self.use_battlespeed = usebattle

    def get_dealspeed(self, isbattle=False):
        if isbattle and self.use_battlespeed:
            return self.dealspeed_battle
        else:
            return self.dealspeed

    def get_drawsetting(self):
        if self.local.important_draw or not self.skin_local.important_draw:
            return self.local
        else:
            return self.skin_local

    def get_fontsetting(self):
        if self.local.important_font or not self.skin_local.important_font:
            return self.local
        else:
            return self.skin_local

    def get_inusecardalpha(self, sprite):
        alpha = 160
        if not sprite.alpha is None:
            alpha = min(alpha, sprite.alpha)
        return alpha

    @property
    def mwincolour(self):
        return self.get_drawsetting().mwincolour

    @property
    def mwinframecolour(self):
        return self.get_drawsetting().mwinframecolour

    @property
    def blwincolour(self):
        return self.get_drawsetting().blwincolour

    @property
    def blwinframecolour(self):
        return self.get_drawsetting().blwinframecolour

    @property
    def curtaincolour(self):
        return self.get_drawsetting().curtaincolour

    @property
    def blcurtaincolour(self):
        return self.get_drawsetting().blcurtaincolour

    @property
    def fullscreenbackgroundtype(self):
        return self.get_drawsetting().fullscreenbackgroundtype

    @property
    def fullscreenbackgroundfile(self):
        return self.get_drawsetting().fullscreenbackgroundfile

    @property
    def bordering_cardname(self):
        return self.get_fontsetting().bordering_cardname

    @property
    def decorationfont(self):
        return self.get_fontsetting().decorationfont

    @property
    def fontsmoothing_message(self):
        return self.get_fontsetting().fontsmoothing_message

    @property
    def fontsmoothing_cardname(self):
        return self.get_fontsetting().fontsmoothing_cardname

    @property
    def fontsmoothing_statusbar(self):
        return self.get_fontsetting().fontsmoothing_statusbar

    @property
    def basefont(self):
        return self.get_fontsetting().basefont

    @property
    def fonttypes(self):
        return self.get_fontsetting().fonttypes

    def is_logscrollable(self):
        return self.messagelog_type <> LOG_SINGLE

    def write(self):
        cw.xmlcreater.create_settings(self)

    @staticmethod
    def wrap_volumevalue(value):
        return cw.util.numwrap(value, 0, 100) / 100.0

    @staticmethod
    def wrap_colorvalue(r, g, b, a):
        r = cw.util.numwrap(r, 0, 255)
        g = cw.util.numwrap(g, 0, 255)
        b = cw.util.numwrap(b, 0, 255)
        a = cw.util.numwrap(a, 0, 255)
        return (r, g, b, a)

    def get_scedir(self, skintype=None):
        if skintype is None:
            skintype = self.skintype

        scedir = u"Scenario"
        # 設定に応じて初期位置を変更する
        if self.selectscenariofromtype:
            for skintype2, folder in self.folderoftype:
                if skintype2 == skintype:
                    folder = cw.util.get_linktarget(folder)
                    if os.path.isdir(folder):
                        scedir = folder
                    break
        return scedir

class _MsgDict(dict):
    def __init__(self):
        """
        存在しないメッセージIDが指定された時に
        エラーダイアログを表示するための拡張dict。
        """
        dict.__init__(self)
        self._error_keys = set()

    def __getitem__(self, key):
        if not key in self:
            if not key in self._error_keys:
                def func():
                    if cw.cwpy.frame:
                        s = u"メッセージID[%s]に該当するメッセージがありません。\n"\
                            u"デイリービルド版でこのエラーが発生した場合は、" \
                            u"「Data/SkinBase」以下のリソースが最新版になっていない"\
                            u"可能性があります。" % (key)
                        sys.stderr.write("Message [%s] is not found." % key)
                        dlg = cw.dialog.message.ErrorMessage(None, s)
                        dlg.ShowModal()
                        dlg.Destroy()
                cw.cwpy.frame.exec_func(func)
                self._error_keys.add(key)
            return u"*ERROR*"
        return dict.__getitem__(self, key)

class Resource(object):
    def __init__(self, setting):
        self.setting = weakref.ref(setting)
        # 現在選択しているスキンのディレクトリ
        self.skindir = setting.skindir
        # 各種データの拡張子
        self.ext_img = cw.M_IMG
        self.ext_bgm = cw.M_MSC
        self.ext_snd = cw.M_SND
        # システムフォントテーブルの設定
        self.fontpaths = self.get_fontpaths()
        self.fontnames, self.fontnames_init = self.set_systemfonttable()
        # 効果音
        self.init_sounds()
        # システムメッセージ(辞書)
        self.msgs = self.get_msgs(setting)
        # wxダイアログのボタン画像(辞書)
        # wxスレッドから初期化
        self.buttons = ResourceTable("Button", {}.copy(), empty_wxbmp)
        # カード背景画像(辞書)
        self.cardbgs = self.get_cardbgs(cw.util.load_image)
        self.cardnamecolorhints = self.get_cardnamecolorhints(self.cardbgs)
        # wxダイアログで使う画像(辞書)
        self.pygamedialogs = self.get_dialogs(cw.util.load_image)
        # wx版。wxスレッドから初期化
        self.dialogs = ResourceTable("Dialog", {}.copy(), empty_wxbmp)
        # デバッガで使う画像(辞書)
        self.pygamedebugs = self.get_debugs(cw.util.load_image, cw.s)
        # wx版。wxスレッドから初期化
        self.debugs = ResourceTable("Debug", {}.copy(), empty_wxbmp)
        # ダイアログで使うカーソル(辞書)
        # wxスレッドから初期化
        self.cursors = ResourceTable("Cursor", {}.copy(), empty_wxbmp)
        # 特殊文字の画像(辞書)
        self.specialchars_is_changed = False
        self.specialchars = self.get_specialchars()
        # プレイヤカードのステータス画像(辞書)
        self.statuses = self.get_statuses(cw.util.load_image)
        # 適性値・使用回数値画像(辞書)
        self.stones = self.get_stones()
        # wx版。wxスレッドから初期化
        self.wxstones = ResourceTable("Stone", {}.copy(), empty_wxbmp)
        # 使用フォント(辞書)。スプライトを作成するたびにフォントインスタンスを
        # 新規作成すると重いのであらかじめ用意しておく(wxスレッドから初期化)
        self.fonts = self.create_fonts()
        # StatusBarで使用するボタンイメージ
        self._statusbtnbmp0 = {}
        self._statusbtnbmp1 = {}
        self._statusbtnbmp2 = {}

        self.ignorecase_table = {}

        cw.cwpy.frame.exec_func(self.init_wxresources)
        if sys.platform <> "win32":
            # FIXME: 大文字・小文字を区別しないシステムでリソース内のファイルの
            #        取得に失敗する事があるので、すべて小文字のパスをキーにして
            #        真のファイル名へのマッピングをしておく。
            #        主にこの問題は手書きされる'*.jpy1'内で発生する。
            for res in ("Table", "Bgm", "Sound", "BgmAndSound", "Resource/Image"):
                resdir = cw.util.join_paths(self.skindir, res)
                for dpath, dnames, fnames in os.walk(resdir):
                    for fname in fnames:
                        path = cw.util.join_paths(dpath, fname)
                        if os.path.isfile(path):
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

    def dispose(self):
        for key in self.fonts.iterkeys():
            if self.fonts.is_loaded(key):
                font = self.fonts[key]
                if isinstance(font, cw.imageretouch.Font):
                    font.dispose()

    @property
    def cardnamecolorborder(self):
        if cw.cwpy.setting.bordering_cardname:
            return 92
        else:
            return 116

    def update_winscale(self):
        self.init_wxresources()

    def init_sounds(self):
        # その他のスキン付属効果音(辞書)
        self.skinsounds = self.get_skinsounds()
        # システム効果音(辞書)
        self.sounds = self.get_sounds(self.setting(), self.skinsounds)

    def init_wxresources(self):
        """wx側のリソースを初期化。"""
        # wxダイアログのボタン画像(辞書)
        self.buttons = self.get_buttons()
        # wxダイアログで使う画像(辞書)
        self.dialogs = self.get_dialogs(cw.util.load_wxbmp)
        # デバッガで使う画像(辞書)
        self.debugs = self.get_debugs(cw.util.load_wxbmp, cw.ppis)
        self.debugs_noscale = self.get_debugs(cw.util.load_wxbmp, lambda bmp: bmp)
        # ダイアログで使うカーソル(辞書)
        self.cursors = self.get_cursors()
        # 適性値・使用回数値画像(辞書)
        self.wxstones = self.get_wxstones()
        # プレイヤカードのステータス画像(辞書)
        self.wxstatuses = self.get_statuses(cw.util.load_wxbmp)
        # カード背景画像(辞書)
        self.wxcardbgs = self.get_cardbgs(cw.util.load_wxbmp)

    def init_debugicon(self):
        """エディタ情報変更によりデバッグアイコンを再読込する"""
        def func():
            self.pygamedebugs = self.get_debugs(cw.util.load_image, cw.s)
        cw.cwpy.exec_func(func)
        self.debugs = self.get_debugs(cw.util.load_wxbmp, cw.ppis)
        self.debugs_noscale = self.get_debugs(cw.util.load_wxbmp, lambda bmp: bmp)

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
            self.facenames = set(wx.FontEnumerator().GetFacenames())

            for name, path in self.fontpaths.iteritems():
                fontname = cw.util.get_truetypefontname(path)
                if fontname in self.facenames or\
                        fontname == u"IPAUIGothic" and (u"IPA UIゴシック" in self.facenames) or\
                        fontname == u"IPAGothic" and (u"IPAゴシック" in self.facenames) or\
                        fontname == u"IPAPGothic" and (u"IPA Pゴシック" in self.facenames) or\
                        fontname == u"IPAMincho" and (u"IPA明朝" in self.facenames) or\
                        fontname == u"IPAPMincho" and (u"IPA P明朝" in self.facenames):
                    d[name] = fontname
                    continue

                def func():
                    if winplatform == 2:
                        gdi32.AddFontResourceExA(path, 0x10, 0)
                    else:
                        gdi32.AddFontResourceA(path)
                        user32 = ctypes.windll.user32
                        HWND_BROADCAST = 0xFFFF
                        WM_FONTCHANGE = 0x001D
                        user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
                thr = threading.Thread(target=func)
                thr.start()

                if fontname:
                    d[name] = fontname
                else:
                    raise ValueError("Failed to get facename from %s" % name)

            self.facenames = set(wx.FontEnumerator().GetFacenames())
        else:
            self.facenames = set(wx.FontEnumerator().GetFacenames())
            d["gothic"] = u"IPAゴシック"
            d["uigothic"] = u"IPA UIゴシック"
            d["mincho"] = u"IPA明朝"
            d["pmincho"] = u"IPA P明朝"
            d["pgothic"] = u"IPA Pゴシック"

            for value in d.itervalues():
                if not value in self.facenames:
                    raise ValueError(u"IPA font not found: " + value)

        init = d.copy()

        # 設定に応じた差し替え
        for basetype in d.iterkeys():
            font = self.setting().local.basefont[basetype]
            if font:
                d[basetype] = font

        return d, init

    def clear_systemfonttable(self):
        if sys.platform == "win32" and not sys.getwindowsversion()[3] == 2:
            gdi32 = ctypes.windll.gdi32

            for path in self.fontpaths.itervalues():
                gdi32.RemoveFontResourceA(path)

            user32 = ctypes.windll.user32
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)

    def get_fontfromtype(self, name):
        """フォントタイプ名から抽象フォント名を取得する。"""
        basename = self.setting().fonttypes.get(name, (name, "", -1, None, None, None))
        basename, fontname, pixels, bold, bold_upscr, italic = basename
        if basename:
            fontname = self.setting().basefont[basename]
            if not fontname:
                fontname = self.fontnames[basename]
        return fontname, pixels, bold, bold_upscr, italic

    def get_wxfont(self, name="uigothic", size=None, pixelsize=None,
                        family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD, encoding=wx.FONTENCODING_SYSTEM,
                        adjustsize=False, adjustsizewx3=True, pointsize=None):
        if size is None and pixelsize is None:
            pixelsize = cw.wins(14)

        fontname, _pixels, bold, bold_upscr, italic = self.get_fontfromtype(name)

        if cw.UP_SCR <= 1:
            if not bold is None:
                weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
        else:
            if not bold_upscr is None:
                weight = wx.FONTWEIGHT_BOLD if bold_upscr else wx.FONTWEIGHT_NORMAL
        if not italic is None:
            style = wx.ITALIC if italic else wx.FONTSTYLE_NORMAL

        if pointsize is None:
            # FIXME: ピクセルサイズで指定しないと96DPIでない時にゲーム画面が
            #        おかしくなるので暫定的に96DPI相当のサイズに強制変換
            if not pixelsize:
                pixelsize = int((1.0/72 * 96) * size + 0.5)
            elif 3 <= wx.VERSION[0] and adjustsizewx3:
                # FIXME: wxPython 3.0.1.1でフォントが1ピクセル大きくなってしまった
                pixelsize -= 1

            # BUG: フォントサイズとテキストによっては
            #      ツリーアイテムの後方が欠ける事がある
            if (name in ("tree", "slider") or adjustsize) and 15 < pixelsize and pixelsize % 2 == 1:
                pixelsize += 1

            wxfont = wx.FontFromPixelSize((0, pixelsize), family, style, weight, 0, fontname, encoding)

        else:
            wxfont = wx.Font(pointsize, family, style, weight, 0, fontname, encoding)

        return wxfont

    def create_font(self, type, basetype, fontname, size_noscale, defbold, defbold_upscr, defitalic, pixelsadd=0, nobold=False):
        fontname, pixels_noscale, bold, bold_upscr, italic = self.get_fontfromtype(type)
        if pixels_noscale <= 0:
            pixels_noscale = size_noscale
        pixels_noscale += pixelsadd
        if bold is None:
            bold = defbold
        if bold_upscr is None:
            bold_upscr = defbold_upscr
        if italic is None:
            italic = defitalic
        if nobold:
            bold = False
            bold_upscr = False

        if cw.UP_SCR > 1:
            bold = bold_upscr

        return cw.imageretouch.Font(fontname, -cw.s(pixels_noscale), bold=bold, italic=italic)

    def create_fonts(self):
        """ゲーム内で頻繁に使用するpygame.Fontはここで設定する。"""
        # 使用フォント(辞書)
        fonts = ResourceTable("Font", {}.copy(), lambda: None)
        # 所持カードの使用回数描画用
        t = self.setting().fonttypes["uselimit"]
        fonts.set("card_uselimit", self.create_font, "uselimit", t[0], t[1], t[2], t[3], t[4], t[5])
        # メニューカードの名前描画用
        t = self.setting().fonttypes["cardname"]
        fonts.set("mcard_name", self.create_font, "cardname", t[0], t[1], t[2], t[3], t[4], t[5])
        # プレイヤカードの名前描画用
        t = self.setting().fonttypes["ccardname"]
        fonts.set("pcard_name", self.create_font, "ccardname", t[0], t[1], t[2], t[3], t[4], t[5])
        # プレイヤカードのレベル描画用
        t = self.setting().fonttypes["level"]
        fonts.set("pcard_level", self.create_font, "level", t[0], t[1], t[2], t[3], t[4], t[5])
        # メッセージウィンドウのテキスト描画用
        t = self.setting().fonttypes["message"]
        fonts.set("message", self.create_font, "message", t[0], t[1], t[2], t[3], t[4], t[5], nobold=True)
        # メッセージウィンドウの選択肢描画用
        t = self.setting().fonttypes["selectionbar"]
        fonts.set("selectionbar", self.create_font, "selectionbar", t[0], t[1], t[2], t[3], t[4], t[5])
        # メッセージログのページ表示描画用
        t = self.setting().fonttypes["logpage"]
        fonts.set("backlog_page", self.create_font, "logpage", t[0], t[1], t[2], t[3], t[4], t[5])
        # カード価格表示用
        t = self.setting().fonttypes["price"]
        fonts.set("price", self.create_font, "price", t[0], t[1], t[2], t[3], t[4], t[5])
        # カード枚数描画用
        t = self.setting().fonttypes["numcards"]
        fonts.set("numcards", self.create_font, "numcards", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーパネル描画用
        t = self.setting().fonttypes["sbarpanel"]
        fonts.set("sbarpanel", self.create_font, "sbarpanel", t[0], t[1], t[2], t[3], t[4], t[5])
        # 進行状況・音量バー描画用
        t = self.setting().fonttypes["sbarprogress"]
        fonts.set("sbarprogress", self.create_font, "sbarprogress", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン描画用
        t = self.setting().fonttypes["sbarbtn"]
        fonts.set("sbarbtn", self.create_font, "sbarbtn", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン解説描画用
        t = self.setting().fonttypes["sbardesc"]
        fonts.set("sbardesc", self.create_font, "sbardesc", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン解説の表題描画用
        t = self.setting().fonttypes["sbardesctitle"]
        fonts.set("sbardesctitle", self.create_font, "sbardesctitle", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータス画像の召喚回数描画用
        t = self.setting().fonttypes["statusnum"]
        fonts.set("statusimg1", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5])
        t = self.setting().fonttypes["statusnum"]
        fonts.set("statusimg2", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5], pixelsadd=-2)
        fonts.set("statusimg3", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5], pixelsadd=-4)
        t = self.setting().fonttypes["screenshot"]
        fonts.set("screenshot", self.create_font, "screenshot", t[0], t[1], t[2], t[3], t[4], t[5])
        return fonts

    def create_wxbutton(self, parent, cid, size, name=None, bmp=None , chain=False):
        if name:
            button = wx.Button(parent, cid, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("button"))
        elif bmp:
            button = wx.BitmapButton(parent, cid, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)

        if chain:
            # ボタンを押し続けた時に一定間隔で押下イベントを発生させる
            timer = wx.Timer(button)
            timer.running = False

            def starttimer(event):
                if not timer.running:
                    timer.running = True
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
                    button.ProcessEvent(btnevent)

                timer.Start(cw.cwpy.setting.move_repeat, wx.TIMER_ONE_SHOT)

            def timerfunc(event):
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
                button.ProcessEvent(btnevent)
                starttimer(event)

            def stoptimer(event):
                timer.Stop()
                event.Skip()
                timer.running = False

            button.Bind(wx.EVT_TIMER, timerfunc)
            button.Bind(wx.EVT_LEFT_DOWN, starttimer)
            button.Bind(wx.EVT_LEFT_UP, stoptimer)
            button.Bind(wx.EVT_LEAVE_WINDOW, stoptimer)

        return button

    def create_wxbutton_dbg(self, parent, cid, size, name=None, bmp=None):
        if name:
            button = wx.Button(parent, cid, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("button", pointsize=9))
        elif bmp:
            button = wx.BitmapButton(parent, cid, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)

        return button

    @staticmethod
    def create_cornerimg(rgb):
        r, g, b = rgb
        linedata = struct.pack(
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB",
            r,  g,  b,  255, r,  g,  b,  255, r,  g,  b,  255, r,  g,  b,  255, r,  g,  b,  255, r,  g,  b,  255,
            r,  g,  b,  255, r,  g,  b,  255, r,  g,  b,  224, r,  g,  b,  128, r,  g,  b,   68, r,  g,  b,   40,
            r,  g,  b,  255, r,  g,  b,  224, r,  g,  b,   68, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0,
            r,  g,  b,  255, r,  g,  b,  128, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0,
            r,  g,  b,  255, r,  g,  b,   68, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0,
            r,  g,  b,  255, r,  g,  b,   40, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0, r,  g,  b,    0
        )

        topleft = pygame.image.fromstring(linedata, (6, 6), "RGBA")
        topright = pygame.transform.flip(topleft, True, False)
        bottomleft = pygame.transform.flip(topleft, False, True)
        bottomright = pygame.transform.flip(topleft, True, True)
        return topleft, topright, bottomleft, bottomright

    @staticmethod
    def draw_frame(bmp, rect, color):
        topleft, topright, bottomleft, bottomright = Resource.create_cornerimg(color)
        pygame.draw.rect(bmp, color, rect, 1)
        x, y, w, h = rect
        bmp.blit(topleft, (x, y))
        bmp.blit(topright, (x+w-6, y))
        bmp.blit(bottomleft, (x, y+h-6))
        bmp.blit(bottomright, (x+w-6, y+h-6))
        Resource.draw_corneroutimg(bmp, rect)

    @staticmethod
    def draw_corneroutimg(bmp, rect=None, outframe=0):
        outdata = struct.pack(
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB"
           "BBBB BBBB BBBB BBBB BBBB BBBB",
            0,0,0,255, 0,0,0,255, 0,0,0,188, 0,0,0,128, 0,0,0,  0, 0,0,0,  0,
            0,0,0,255, 0,0,0,128, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0,
            0,0,0,188, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0,
            0,0,0,128, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0,
            0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0,
            0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0, 0,0,0,  0
        )
        topleft = pygame.image.fromstring(outdata, (6, 6), "RGBA")
        topright = pygame.transform.flip(topleft, True, False)
        bottomleft = pygame.transform.flip(topleft, False, True)
        bottomright = pygame.transform.flip(topleft, True, True)

        if not rect:
            rect = bmp.get_rect()
        x, y, w, h = rect
        o = outframe
        bmp.blit(topleft, (x+o, y+o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(topright, (x+w-6-o, y+o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(bottomleft, (x+o, y+h-6-o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(bottomright, (x+w-6-o, y+h-6-o), special_flags=pygame.locals.BLEND_RGBA_SUB)

    def _create_statusbtnbmp(self, w, h, flags=0):
        """ボタン風の画像を生成する。"""
        topleft, topright, bottomleft, bottomright = Resource.create_cornerimg((208, 208, 208))

        def subtract_corner(value):
            # 角部分の線の色を濃くする
            color = (value, value, value, 0)
            topleft.fill(color, special_flags=pygame.locals.BLEND_RGBA_SUB)
            topright.fill(color, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomleft.fill(color, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomright.fill(color, special_flags=pygame.locals.BLEND_RGBA_SUB)

        bmp = pygame.Surface((w, h)).convert_alpha()

        if flags & SB_DISABLE:
            r1 = g1 = b1 = 240
            bmp.fill((r1, g1, b1))
        else:
            # グラデーションとなるよう、全面に線を引く
            # (フラグによって明るさを変える)
            if (flags & SB_CURRENT) and (flags & SB_PRESSED):
                r1 = g1 = b1 = 234
                r2 = g2 = b2 = 222
            elif flags & SB_PRESSED:
                r1 = g1 = b1 = 220
                r2 = g2 = b2 = 208
            elif flags & SB_CURRENT:
                r1 = g1 = b1 = 255
                r2 = g2 = b2 = 250
            else:
                r1 = g1 = b1 = 255
                r2 = g2 = b2 = 232
            mid = h / 2
            for y in xrange(0, mid+1, 1):
                bmp.fill((r1-y/4, g1-y/4, b1-y/4), pygame.Rect(0, mid-y, w, 1))
                bmp.fill((r2-y, g2-y, b2-y), pygame.Rect(0, mid+y, w, 1))

        # 枠の部分。四隅には角丸の画像を描写する
        if flags & SB_PRESSED:
            # 押下済みの画像であれば上と左の縁を暗くする
            if not (flags & SB_CURRENT):
                subtract_corner(8)
                color = (200, 200, 200)
            else:
                color = (208, 208, 208)
            pygame.draw.line(bmp, color, (2, 3), (w-4, 3))
            subtract_corner(8)
            bmp.blit(topleft, (2, 3))
            bmp.blit(topright, (w-6-1, 3))

            if not (flags & SB_CURRENT):
                color = (192, 192, 192)
            else:
                color = (200, 200, 200)
            pygame.draw.rect(bmp, color, (2, 2, w-3, h-3), 1)
            bmp.blit(topleft, (2, 2))
            bmp.blit(topright, (w-6-1, 2))
            bmp.blit(bottomleft, (2, h-6-1))
            subtract_corner(64)
            color = (128, 128, 128)
        elif flags & SB_DISABLE:
            subtract_corner(16)
            color = (192, 192, 192)
        else:
            subtract_corner(72)
            color = (128, 128, 128)

        if flags & SB_EMPHASIZE:
            # 線の色を赤くする
            emcolor = (0, 128, 128, 0)
            topleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            topright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            color = (color[0], max(0, color[1]-128), max(0, color[2]-128))

            emcolor = (96, 0, 0, 0)
            topleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            topright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            bottomleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            bottomright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            color = (min(255, color[0]+96), color[1], color[2])

        if not (flags & SB_CURRENT) and not (flags & SB_DISABLE):
            opacity = 92
            lightcolor = (0, 0, 0, opacity)
            topleft.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            topright.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomleft.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomright.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            linecolor = (color[0], color[1], color[2], 255-opacity)
        else:
            linecolor = color

        pygame.draw.rect(bmp, linecolor, (1, 1, w-2, h-2), 1)
        bmp.blit(topleft, (1, 1))
        bmp.blit(topright, (w-6-1, 1))
        bmp.blit(bottomleft, (1, h-6-1))
        bmp.blit(bottomright, (w-6-1, h-6-1))

        if not (flags & SB_PRESSED):
            # ハイライトをつける
            linedata = struct.pack(
               "BBBB BBBB BBBB BBBB BBBB BBBB"
               "BBBB BBBB BBBB BBBB BBBB BBBB"
               "BBBB BBBB BBBB BBBB BBBB BBBB"
               "BBBB BBBB BBBB BBBB BBBB BBBB"
               "BBBB BBBB BBBB BBBB BBBB BBBB"
               "BBBB BBBB BBBB BBBB BBBB BBBB",
                r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,128, r1,g1,b1,255, r1,g1,b1,255, r1,g1,b1,255,
                r1,g1,b1,  0, r1,g1,b1,196, r1,g1,b1,224, r1,g1,b1,128, r1,g1,b1, 68, r1,g1,b1, 40,
                r1,g1,b1,128, r1,g1,b1,224, r1,g1,b1, 68, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0,
                r1,g1,b1,255, r1,g1,b1,128, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0,
                r1,g1,b1,255, r1,g1,b1, 68, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0,
                r1,g1,b1,255, r1,g1,b1, 40, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0, r1,g1,b1,  0
            )
            hl_topleft = pygame.image.fromstring(linedata, (6, 6), "RGBA")
            hl_topright = pygame.transform.flip(hl_topleft, True, False)
            hl_bottomleft = pygame.transform.flip(hl_topleft, False, True)
            hl_bottomright = pygame.transform.flip(hl_topleft, True, True)
            color = (r1, g1, b1)
            pygame.draw.line(bmp, color, (2+6, 2), (w-6-3, 2))
            pygame.draw.line(bmp, color, (2+6, h-3), (w-6-3, h-3))
            pygame.draw.line(bmp, color, (2, 2+6), (2, h-6-3))
            pygame.draw.line(bmp, color, (w-3, 2+6), (w-3, h-6-3))
            bmp.blit(hl_topleft, (2, 2))
            bmp.blit(hl_topright, (w-6-2, 2))
            bmp.blit(hl_bottomleft, (2, h-6-2))
            bmp.blit(hl_bottomright, (w-6-2, h-6-2))

        if flags & SB_NOTICE:
            if flags & SB_PRESSED:
                bmp.fill((64, 0, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
            else:
                bmp.fill((128, 0, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
            bmp.fill((0, 96, 96, 0), special_flags=pygame.locals.BLEND_RGBA_SUB)

        # 枠の外の部分を透明にする
        Resource.draw_corneroutimg(bmp, outframe=1)

        pygame.draw.rect(bmp, (0, 0, 0, 0), (0, 0, w, h), 1)

        return bmp

    def get_statusbtnbmp(self, sizetype, flags=0):
        """StatusBarで使用するボタン画像を取得する。
        sizetype: 0=(120, 22), 1=(27, 27), 2=(632, 33)
        flags: 0:通常, SB_PRESSED:押下時, SB_CURRENT:カーソル下,
               SB_DISABLE:無効状態, SB_NOTICE:通知
               |で組み合わせて指定する。
        """
        btn = None
        if sizetype == 0:
            if flags in self._statusbtnbmp0:
                btn = self._statusbtnbmp0[flags]
            else:
                btn = self._create_statusbtnbmp(cw.s(120), cw.s(22), flags)
                self._statusbtnbmp0[flags] = btn
        elif sizetype == 1:
            if flags in self._statusbtnbmp1:
                btn = self._statusbtnbmp1[flags]
            else:
                btn = self._create_statusbtnbmp(cw.s(27), cw.s(27), flags)
                self._statusbtnbmp1[flags] = btn
        elif sizetype == 2:
            if flags in self._statusbtnbmp2:
                btn = self._statusbtnbmp2[flags]
            else:
                btn = self._create_statusbtnbmp(cw.s(632), cw.s(33), flags)
                self._statusbtnbmp2[flags] = btn

        return btn.copy() if btn else None

    def get_resources(self, func, dpath1, dpath2, ext, mask=None, ss=None, noresize=(), nodbg=False, emptyfunc=None,
                      editor_res=None, warning=True):
        """
        各種リソースデータを辞書で返す。
        ファイル名から拡張子を除いたのがkey。
        """
        def nokeyfunc(key):
            dbg = not nodbg and key.endswith("_dbg")
            noscale = key.endswith("_noscale")
            up_scr = None
            fpath = ""

            if dbg:
                key = key[:-len("_dbg")]
                up_scr = cw.dpi_level
            if noscale:
                key = key[:-len("_noscale")]

            if editor_res:
                resname = CWXEDITOR_RESOURCES.get(key, "")
                fpath = cw.util.join_paths(editor_res, resname)
                if not os.path.isfile(fpath):
                    fpath = ""

            if not fpath and dpath2:
                fpath = cw.util.find_resource(cw.util.join_paths(dpath2, key), ext)
            if not fpath:
                fpath = cw.util.find_resource(cw.util.join_paths(dpath1, key), ext)
            if not fpath:
                if warning:
                    def errfunc(dname, key):
                        if cw.cwpy.frame:
                            s = u"リソース [%s/%s] が見つかりません。\n"\
                                u"デイリービルド版でこのエラーが発生した場合は、" \
                                u"「Data/SkinBase」以下のリソースが最新版になっていない"\
                                u"可能性があります。" % (dname, key)
                            sys.stderr.write("Resource [%s/%s] is not found." % (dname, key))
                            dlg = cw.dialog.message.ErrorMessage(None, s)
                            dlg.ShowModal()
                            dlg.Destroy()
                    cw.cwpy.frame.exec_func(errfunc, os.path.basename(dpath1), key)
                return emptyfunc()

            if mask is None:
                res = func(fpath)
            else:
                if ss == cw.ppis and func == cw.util.load_wxbmp:
                    res = func(fpath, mask=mask, can_loaded_scaledimage=True, up_scr=cw.dpi_level)
                else:
                    res = func(fpath, mask=mask, can_loaded_scaledimage=True, up_scr=up_scr)

            if not noscale:
                if not dbg and ss and not key in noresize:
                    res = ss(res)
                elif dbg and ss:
                    res = cw.ppis(res)

            return res

        d = ResourceTable(dpath1, {}.copy(), emptyfunc, nokeyfunc=nokeyfunc)
        return d

    def get_sounds(self, setting, skinsounds):
        """
        システム効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        d = ResourceTable("SystemSound", {}.copy(), empty_sound)
        for key, sound in setting.sounds.items():
            if sound in skinsounds:
                f = lambda sound: d.set(key, lambda: skinsounds[sound])
                f(sound)
            else:
                d.set(key, empty_sound)
        return d

    def get_skinsounds(self):
        """
        スキン付属の効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Sound")
        d = self.get_resources(cw.util.load_sound, "Data/SkinBase/Sound", dpath, self.ext_snd,
                               emptyfunc=empty_sound, warning=False)
        dpath = cw.util.join_paths(self.skindir, "BgmAndSound")
        d2 = self.get_resources(cw.util.load_sound, "Data/SkinBase/BgmAndSound", dpath, self.ext_snd,
                                emptyfunc=empty_sound, warning=False)
        d.merge(d2)

        return d

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
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Button")
        return self.get_resources(cw.util.load_wxbmp, "Data/SkinBase/Resource/Image/Button", dpath, self.ext_img, True, cw.wins, emptyfunc=empty_wxbmp)

    def get_cursors(self):
        """
        ダイアログで使用されるカーソルを読み込んで、
        wxCursorのインスタンスの辞書で返す。
        """
        def get_cursor(name):
            fname = name + ".cur"
            dpaths = ("Data/SkinBase/Resource/Image/Cursor",
                      cw.util.join_paths(self.skindir, "Resource/Image/Cursor"))
            for dpath in dpaths:
                fpath = cw.util.join_paths(dpath, fname)
                if os.path.isfile(fpath):
                    return wx.Cursor(fpath, wx.BITMAP_TYPE_CUR)
            if name == "CURSOR_BACK":
                return wx.StockCursor(wx.CURSOR_POINT_LEFT)
            elif name == "CURSOR_FORE":
                return wx.StockCursor(wx.CURSOR_POINT_RIGHT)
            elif name == "CURSOR_FINGER":
                return wx.StockCursor(wx.CURSOR_HAND)
            elif name == "CURSOR_ARROW":
                return wx.NullCursor
            else:
                return wx.NullCursor

        d = ResourceTable("Resource/Image/Cursor", {}.copy(), lambda: wx.StockCursor(wx.CURSOR_ARROW), nokeyfunc=get_cursor)
        return d

    def get_stones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        pygameのサーフェスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(cw.util.load_image, "Data/SkinBase/Resource/Image/Stone", dpath, self.ext_img, True, cw.s, emptyfunc=empty_image)

    def get_wxstones(self):
        """
        適性・カード残り回数の画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(cw.util.load_wxbmp, "Data/SkinBase/Resource/Image/Stone", dpath, self.ext_img, True, cw.wins, emptyfunc=empty_wxbmp)

    def get_statuses(self, load_image):
        """
        ステータス表示に使う画像を読み込んで、
        ("LIFEGUAGE", "TARGET", "LIFE", "UP*", "DOWN*"はマスクする)
        pygameのサーフェスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc=empty_wxbmp
        else:
            ss = cw.s
            emptyfunc=empty_image

        def load_image2(fpath, mask=False, can_loaded_scaledimage=True, up_scr=None):
            fname = os.path.basename(fpath)
            key = os.path.splitext(fname)[0]
            if key in ("LIFE", "UP0", "UP1", "UP2", "UP3", "DOWN0", "DOWN1", "DOWN2", "DOWN3"):
                return load_image(fpath, mask=True, maskpos=(1, 1), can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "TARGET":
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEGUAGE":
                return load_image(fpath, mask=True, maskpos=(5, 5), can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEGUAGE2":
                return load_image(fpath, mask=True, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEGUAGE2_MASK":
                return load_image(fpath, mask=True, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEBAR":
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            else:
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Status")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/Status", dpath, self.ext_img, False, ss, emptyfunc=emptyfunc)

    def get_dialogs(self, load_image):
        """
        ダイアログで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc=empty_wxbmp
        else:
            ss = cw.s
            emptyfunc=empty_image

        def load_image2(fpath, mask=False, can_loaded_scaledimage=True, up_scr=None):
            fname = os.path.basename(fpath)
            key = os.path.splitext(fname)[0]
            if key in ("LINK", "MONEYY"):
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "STATUS8":
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key in ("CAUTION", "INVISIBLE"):
                return load_image(fpath, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            else:
                return load_image(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Dialog")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/Dialog", dpath, self.ext_img, True, ss, emptyfunc=emptyfunc)

    def get_debugs(self, load_image, ss):
        """
        デバッガで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            emptyfunc=empty_wxbmp
        else:
            emptyfunc=empty_image

        dpath = u"Data/Debugger"

        # 可能ならcwxeditor/resourceからアイコンを読み込む
        editor_res = os.path.dirname(os.path.abspath(self.setting().editor))
        editor_res = cw.util.join_paths(editor_res, "resource")
        if not os.path.isdir(editor_res):
            editor_res = None

        return self.get_resources(load_image, dpath, "", cw.M_IMG, True, ss, emptyfunc=emptyfunc, editor_res=editor_res)

    def get_cardbgs(self, load_image):
        """
        カードの背景画像を読み込んで、pygameのサーフェス
        ("PREMIER", "RARE", "HOLD", "PENALTY"はマスクする)
        の辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc=empty_wxbmp
        else:
            ss = cw.s
            emptyfunc=empty_image

        def load_image2(fpath, mask=False, can_loaded_scaledimage=True, up_scr=None):
            fname = os.path.basename(fpath)
            key = os.path.splitext(fname)[0]
            if key in ("HOLD", "PENALTY"):
                return load_image(fpath, mask=True, maskpos="center", can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key in ("PREMIER", "RARE"):
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            else:
                return load_image(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/CardBg")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/CardBg", dpath, self.ext_img, False, ss, nodbg=True, emptyfunc=emptyfunc)

    def get_cardnamecolorhints(self, cardbgs):
        """
        カードの各台紙について、文字描画領域の色を
        平均化した辞書を作成する。
        """
        d = ResourceTable("CardBgColorHints", {}.copy(), lambda: 255)
        for key in ("ACTION", "BEAST", "BIND", "DANGER", "FAINT", "INFO", "INJURY", "ITEM",
                    "LARGE", "NORMAL", "OPTION", "PARALY", "PETRIF", "SKILL", "SLEEP"):
            f = lambda key: d.set(key, lambda: self.calc_cardnamecolorhint(cardbgs[key]))
            f(key)
        return d

    def calc_cardnamecolorhint(self, bmp):
        """文字描画領域の色を平均化した値を返す。
        """
        if bmp.get_width() <= cw.s(10) or bmp.get_height() <= cw.s(20):
            return
        rect = pygame.Rect(cw.s(5), cw.s(5), bmp.get_width() - cw.s(10), cw.s(15))
        sub = bmp.subsurface(rect)
        buf = pygame.image.tostring(sub, "RGB")
        buf = array.array('B', buf)
        rgb = sum(buf) / len(buf)
        return rgb

    def calc_wxcardnamecolorhint(self, wxbmp):
        """文字描画領域の色を平均化した値を返す。
        """
        if bmp.GetWidth() <= cw.s(10) or bmp.GetHeight() <= cw.s(20):
            return
        rect = wx.Rect(cw.s(5), cw.s(5), wxbmp.GetWidth() - cw.s(10), cw.s(15))
        sub = wxbmp.GetSubBitmap(rect)
        buf = array.array('B', '\0' * (rect[2] * rect[3] * 3))
        sub.CopyToBuffer(buf, format=wx.BitmapBufferFormat_RGB)
        rgb = sum(buf) / len(buf)
        return rgb

    def get_actioncards(self):
        """
        "Resource/Xml/ActionCard"にあるアクションカードを読み込み、
        cw.header.CardHeaderインスタンスの辞書で返す。
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

    def get_backpackcards(self):
        """
        "Resource/Xml/SpecialCard/UseCardInBackpack.xml"のカードを読み込み、
        cw.header.CardHeaderインスタンスの辞書で返す。
        """
        fpath = cw.util.join_paths(self.skindir, "Resource/Xml/SpecialCard/UseCardInBackpack.xml")
        if not os.path.isfile(fpath):
            # 旧バージョンのスキンには存在しないのでSkinBaseを使用
            fpath = u"Data/SkinBase/Resource/Xml/SpecialCard/UseCardInBackpack.xml"
        carddata = cw.data.xml2element(fpath)

        d = {}
        for cardtype in ("ItemCard", "BeastCard"):
            d[cardtype] = cw.header.CardHeader(carddata=carddata, bgtype=cardtype.upper().replace("CARD", ""))
        return d

    def get_specialchars(self):
        """
        特殊文字の画像を読み込んで、
        pygameのサーフェスの辞書で返す(特殊文字がkey)
        """
        self.specialchars_is_changed = False
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Font")

        ndict = {"ANGRY"   : "#a",
                 "CLUB"    : "#b",
                 "DIAMOND" : "#d",
                 "EASY"    : "#e",
                 "FLY"     : "#f",
                 "GRIEVE"  : "#g",
                 "HEART"   : "#h",
                 "JACK"    : "#j",
                 "KISS"    : "#k",
                 "LAUGH"   : "#l",
                 "NIKO"    : "#n",
                 "ONSEN"   : "#o",
                 "PUZZLE"  : "#p",
                 "QUICK"   : "#q",
                 "SPADE"   : "#s",
                 "WORRY"   : "#w",
                 "X"       : "#x",
                 "ZAP"     : "#z",
                 }

        d = ResourceTable("Resource/Image/Font", {}.copy(), empty_image)
        def load(key, name):
            fpath = cw.util.find_resource(cw.util.join_paths(dpath, key), self.ext_img)
            image = cw.util.load_image(fpath, mask=True, can_loaded_scaledimage=True)
            return image, False

        for key, name in ndict.iteritems():
            d.set(name, load, key, name)

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
    "Dialog/PLAYING_YADO": (68, 146),
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
    "Status/LIFEGUAGE2": (79, 13),
    "Status/LIFEGUAGE2_MASK": (79, 13),
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

# Data/Debuggerとcwxeditor/resource内にあるファイルとの対応表
# 該当無しのリソースはこのテーブルには含まない
CWXEDITOR_RESOURCES = {
    "AREA": "area.png",
    "BATTLE": "battle.png",
    "CARD": "cards.png",
    "COMPSTAMP": "end.png",
    "COUPON": "coupon_high.png",
    "COUPON_MINUS": "coupon_minus.png",
    "COUPON_PLUS": "coupon_plus.png",
    "COUPON_ZERO": "coupon_n.png",
    "EDITOR": "cwxeditor.png",
    "EVENT": "event_tree.png",
    "FLAG": "flag.png",
    "FRIEND": "cast.png",
    "GOSSIP": "gossip.png",
    "IGNITION": "def_start.png",
    "INFO": "info.png",
    "KEYCODE": "key_code.png",
    "LOAD": "open.png",
    "MEMBER": "party_cards.png",
    "MONEY": "money.png",
    "PACK": "package.png",
    "RECOVERY": "msn_heal.png",
    "RESET": "reload.png",
    "ROUND": "round.png",
    "SAVE": "save.png",
    "SELECTION": "sc_m.png",
    "STEP": "step.png",
    "UPDATE": "refresh.png",
    "YADO": "sc_y.png",

    # Terminal
    "EVT_START": "evt_start.png",  # スタート
    "EVT_START_BATTLE": "evt_battle.png",  # バトル開始
    "EVT_END": "evt_clear.png",  # シナリオクリア
    "EVT_END_BADEND": "evt_gameover.png",  # 敗北・ゲームオーバー
    "EVT_CHANGE_AREA": "evt_area.png",  # エリア移動
    "EVT_EFFECT_BREAK": "evt_stop.png",  # 効果中断
    "EVT_LINK_START": "evt_link_s.png",  # スタートへのリンク
    "EVT_LINK_PACKAGE": "evt_link_p.png",  # パッケージへのリンク

    # Standard
    "EVT_TALK_MESSAGE": "evt_message.png",  # メッセージ
    "EVT_TALK_DIALOG": "evt_speak.png",  # セリフ
    "EVT_PLAY_BGM": "evt_bgm.png",  # BGM変更
    "EVT_PLAY_SOUND": "evt_se.png",  # 効果音
    "EVT_CHANGE_BGIMAGE": "evt_back.png",  # 背景変更
    "EVT_ELAPSE_TIME": "evt_time.png",  # 時間経過
    "EVT_EFFECT": "evt_effect.png",  # 効果
    "EVT_WAIT": "evt_wait.png",  # 空白時間
    "EVT_CALL_PACKAGE": "evt_call_p.png",  # パッケージのコール
    "EVT_CALL_START": "evt_call_s.png",  # スタートのコール

    # Data
    "EVT_BRANCH_FLAG": "evt_br_flag.png",  # フラグ分岐
    "EVT_SET_FLAG": "evt_flag_set.png",  # フラグ変更
    "EVT_REVERSE_FLAG": "evt_flag_r.png",  # フラグ反転
    "EVT_CHECK_FLAG": "evt_flag_judge.png",  # フラグ判定
    "EVT_BRANCH_MULTISTEP": "evt_br_step_n.png",  # ステップ多岐分岐
    "EVT_BRANCH_STEP": "evt_br_step_ul.png",  # ステップ上下分岐
    "EVT_SET_STEPUP": "evt_step_plus.png",  # ステップ増加
    "EVT_SET_STEPDOWN": "evt_step_minus.png",  # ステップ減少
    "EVT_SET_STEP": "evt_step_set.png",  # ステップ変更
    "EVT_CHECK_STEP": "evt_check_step.png",  # ステップ判定
    "EVT_BRANCH_FLAGVALUE": "evt_cmpflag.png",  # フラグ比較分岐
    "EVT_BRANCH_STEPVALUE": "evt_cmpstep.png",  # ステップ比較分岐
    "EVT_SUBSTITUTE_FLAG": "evt_cpflag.png",  # フラグ代入
    "EVT_SUBSTITUTE_STEP": "evt_cpstep.png",  # ステップ代入

    # Utility
    "EVT_BRANCH_SELECT": "evt_br_member.png",  # メンバ選択
    "EVT_BRANCH_ABILITY": "evt_br_power.png",  # 能力判定分岐
    "EVT_BRANCH_RANDOM": "evt_br_random.png",  # ランダム分岐
    "EVT_BRANCH_MULTI_RANDOM": "evt_br_multi_random.png",  # ランダム多岐分岐
    "EVT_BRANCH_LEVEL": "evt_br_level.png",  # レベル判定分岐
    "EVT_BRANCH_STATUS": "evt_br_state.png",  # 状態判定分岐
    "EVT_BRANCH_PARTYNUMBER": "evt_br_num.png",  # 人数判定
    "EVT_BRANCH_AREA": "evt_br_area.png",  # エリア分岐
    "EVT_BRANCH_BATTLE": "evt_br_battle.png",  # バトル分岐
    "EVT_BRANCH_ISBATTLE": "evt_br_on_battle.png",  # バトル判定分岐
    "EVT_BRANCH_ROUND": "evt_br_round.png",  # ラウンド分岐
    "EVT_BRANCH_RANDOMSELECT": "evt_br_rndsel.png",  # ランダム選択

    # Branch
    "EVT_BRANCH_CAST": "evt_br_cast.png",  # キャスト存在分岐
    "EVT_BRANCH_ITEM": "evt_br_item.png",  # アイテム所持分岐
    "EVT_BRANCH_SKILL": "evt_br_skill.png",  # スキル所持分岐
    "EVT_BRANCH_INFO": "evt_br_info.png",  # 情報所持分岐
    "EVT_BRANCH_BEAST": "evt_br_beast.png",  # 召喚獣存在分岐
    "EVT_BRANCH_MONEY": "evt_br_money.png",  # 所持金分岐
    "EVT_BRANCH_COUPON": "evt_br_coupon.png",  # クーポン分岐
    "EVT_BRANCH_MULTI_COUPON": "evt_br_multi_coupon.png",  # クーポン多岐分岐
    "EVT_BRANCH_COMPLETESTAMP": "evt_br_end.png",  # 終了済シナリオ分岐
    "EVT_BRANCH_GOSSIP": "evt_br_gossip.png",  # ゴシップ分岐
    "EVT_BRANCH_KEYCODE": "evt_br_keycode.png",  # キーコード所持分岐

    # Get
    "EVT_GET_CAST": "cast.png",  # キャスト加入
    "EVT_GET_ITEM": "item.png",  # アイテム入手
    "EVT_GET_SKILL": "skill.png",  # スキル取得
    "EVT_GET_INFO": "info.png",  # 情報入手
    "EVT_GET_BEAST": "beast.png",  # 召喚獣獲得
    "EVT_GET_MONEY": "money.png",  # 所持金増加
    "EVT_GET_COUPON": "coupon.png",  # 称号獲得
    "EVT_GET_COMPLETESTAMP": "end.png",  # 終了シナリオ設定・貼り紙
    "EVT_GET_GOSSIP": "gossip.png",  # ゴシップ追加

    # Lost
    "EVT_LOSE_CAST": "evt_lost_cast.png",  # キャスト離脱
    "EVT_LOSE_ITEM": "evt_lost_item.png",  # アイテム喪失
    "EVT_LOSE_SKILL": "evt_lost_skill.png",  # スキル喪失
    "EVT_LOSE_INFO": "evt_lost_info.png",  # 情報喪失
    "EVT_LOSE_BEAST": "evt_lost_beast.png",  # 召喚獣喪失
    "EVT_LOSE_MONEY": "evt_lost_money.png",  # 所持金減少
    "EVT_LOSE_COUPON": "evt_lost_coupon.png",  # クーポン削除
    "EVT_LOSE_COMPLETESTAMP": "evt_lost_end.png",  # 終了シナリオ削除
    "EVT_LOSE_GOSSIP": "evt_lost_gossip.png",  # ゴシップ削除

    # Visual
    "EVT_SHOW_PARTY": "evt_show_party.png",  # パーティ表示
    "EVT_HIDE_PARTY": "evt_hide_party.png",  # パーティ隠蔽
    "EVT_MOVE_BGIMAGE": "evt_mv_back.png",  # 背景再配置
    "EVT_REPLACE_BGIMAGE": "evt_rpl_back.png",  # 背景置換
    "EVT_LOSE_BGIMAGE": "evt_lose_back.png",  # 背景削除
    "EVT_REDISPLAY": "evt_refresh.png",  # 画面の再構築
}

def empty_wxbmp():
    """空のwx.Bitmapを返す。"""
    wxbmp = wx.EmptyBitmap(1, 1)
    image = wxbmp.ConvertToImage()
    r = image.GetRed(0, 0)
    g = image.GetGreen(0, 0)
    b = image.GetBlue(0, 0)
    image.SetMaskColour(r, g, b)
    return image.ConvertToBitmap()

def empty_image():
    """空のpygame.Surfaceを返す。"""
    image = pygame.Surface((1, 1)).convert()
    image.set_colorkey(image.get_at((0, 0)), pygame.locals.RLEACCEL)
    return image

def empty_sound():
    """空のcw.util.SoundInterfaceを返す。"""
    return cw.util.SoundInterface(None, "")

class LazyResource(object):
    def __init__(self, func, args, kwargs):
        """リソースをfunc(*args, **kwargs)によって
        遅延読み込みする。
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._res = None
        self.load = False
        self.failure = False

    def clear(self):
        self.load = False
        self._res = None

    def get_res(self):
        if not self.load:
            try:
                self._res = self.func(*self.args, **self.kwargs)
            except:
                cw.util.print_ex(file=sys.stderr)
                self.failure = True
            self.load = True
        return self._res

class ResourceTable(object):
    def __init__(self, name, init={}.copy(), deffunc=None, nokeyfunc=None):
        """文字列をキーとしたリソーステーブル。
        各リソースは必要になった時に遅延読み込みされる。
        """
        self.name = name
        self.dic = init

        self.nokeyfunc = nokeyfunc

        self.deffunc = deffunc
        self.defvalue = None
        self.defload = False

    def reset(self):
        for lazy in self.dic.itervalues():
            lazy.clear()

    def merge(self, d):
        for key, value in self.dic.iteritems():
            if not key in self.dic:
                self.dic[key] = value

    def __getitem__(self, key):
        self._put_nokeyvalue(key)
        lazy = self.dic.get(key, None)
        if lazy:
            first = not lazy.load
            val = lazy.get_res()
            if lazy.failure:
                if first:
                    s = u"リソース [%s/%s] の読み込みに失敗しました。\n" % (self.name, key)
                    sys.stderr.write(s)
                return self.get_defvalue()
            else:
                return val
        else:
            if not self.defload:
                s = u"リソース [%s/%s] が見つかりません。\n" % (self.name, key)
                sys.stderr.write(s)
            val = self.get_defvalue()

    def get_defvalue(self):
        if not self.defload:
            self.defvalue = self.deffunc()
            self.defload = True
        return self.defvalue

    def _put_nokeyvalue(self, key):
        if self.nokeyfunc and not key in self.dic:
            self.dic[key] = LazyResource(lambda: self.nokeyfunc(key), (), {})

    def get(self, key, defvalue=None):
        self._put_nokeyvalue(key)
        if key in self.dic:
            return self[key]
        return defvalue

    def set(self, key, func, *args, **kwargs):
        self.dic[key] = LazyResource(func, args, kwargs)

    def __contains__(self, key):
        self._put_nokeyvalue(key)
        return key in self.dic

    def copy(self):
        tbl = ResourceTable(self.name, self.dic.copy(), self.deffunc, self.nokeyfunc)
        tbl.defvalue = self.defvalue
        tbl.defload = self.defload
        return tbl

    def iterkeys(self):
        for key in self.dic.iterkeys():
            yield key

    def is_loaded(self, key):
        self._put_nokeyvalue(key)
        return self.dic[key].load

class RecentHistory(object):
    def __init__(self, tempdir):
        """起動してから開いたシナリオの情報を
        (wsn・zipファイルのパス, 最終更新日, "Data/Temp"に展開したフォルダパス)の
        形式で保存し、管理するクラス。
        古い順から"Data/Temp"のフォルダを削除していく。
        tempdir: シナリオの一時展開先
        """
        self.scelist = []
        temppaths = set()
        limit = cw.cwpy.setting.recenthistory_limit

        fpath = cw.util.join_paths(tempdir, "RecentHistory.xml")
        if os.path.isfile(fpath):
            self.data = cw.data.xml2etree(fpath)
        else:
            self.data = cw.data.CWPyElementTree(element=cw.data.make_element("RecentHistory", ""))
            self.data.fpath = fpath
            self.data.write()

        for e in self.data.getfind("."):
            if e.tag == "Scenario":
                path = e.gettext("WsnPath", "")
                temppath = e.gettext("TempPath", "")
                md5 = e.get("md5")

                if os.path.isfile(path) and os.path.isdir(temppath) and md5:
                    self.scelist.append((path, md5, temppath))
                    temppath = os.path.normpath(temppath)
                    temppath = os.path.normcase(temppath)
                    temppaths.add(temppath)

        if os.path.isdir(tempdir):
            for name in os.listdir(tempdir):
                path = cw.util.join_paths(tempdir, name)
                if os.path.isdir(path):
                    path = os.path.normpath(path)
                    path = os.path.normcase(path)

                    if not path in temppaths:
                        cw.util.remove(path)

        self.set_limit(limit)

    def write(self):
        # シナリオ履歴
        data = self.data.getroot()

        while len(data):
            data.remove(data[-1])

        for path, md5, temppath in self.scelist:
            e_sce = cw.data.make_element("Scenario", "", {"md5": str(md5)})
            e = cw.data.make_element("WsnPath", path)
            e_sce.append(e)
            e = cw.data.make_element("TempPath", temppath)
            e_sce.append(e)
            data.append(e_sce)

        self.data.write()

    def set_limit(self, value):
        """
        保持履歴数を設定する。
        履歴数を超えたデータは古い順から削除。
        """
        self.limit = value

        if self.limit and len(self.scelist) > self.limit:
            while len(self.scelist) > self.limit:
                self.remove(save=False)
            self.write()

    def moveend(self, path):
        """
        引数のpathのデータを一番下に移動する。
        """
        seq = [i for i in self.scelist if i[0] == path]

        for i in seq:
            self.scelist.remove(i)
            self.scelist.append(i)

        self.write()

    def append(self, path, temppath, md5=None):
        """
        path: wsn・zipファイルのパス。
        temppath: "Data/Yado/<Yado>/Temp"に展開したフォルダパス。
        設定数以上になったら、古いデータから削除。
        """
        path = path.replace("\\", "/")

        if not md5:
            md5 = cw.util.get_md5(path)

        temppath = temppath.replace("\\", "/")
        self.remove(path, save=False)
        self.scelist.append((path, md5, temppath))

        while len(self.scelist) > self.limit:
            self.remove(save=False)

        self.write()

    def remove(self, path="", save=True):
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

        if save:
            self.write()

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

class SystemCoupons(object):
    """称号選択分岐で特殊処理するシステムクーポン群。
    シナリオ側からのエンジンのバージョン判定等に利用する。
    CardWirth由来の"＿１"～"＿６"や"＠ＭＰ３"は含まれない。
    """
    def __init__(self, fpath=u"Data/SystemCoupons.xml", data=None):
        self._normal = set() # 固定値
        self._regexes = [] # 正規表現
        self._ats = True # u"＠"で始まる称号のみが含まれる場合はTrue
        if data is None and os.path.isfile(fpath):
            data = cw.data.xml2element(path=fpath)
        if not data is None:
            for e in data:
                if self._ats and not e.text.startswith(u"＠"):
                    self._ats = False

                regex = e.getbool(".", "regex", False)
                if regex:
                    self._regexes.append(re.compile(e.text))
                else:
                    self._normal.add(e.text)

    def match(self, coupon):
        """couponがシステムクーポンに含まれている場合はTrueを返す。
        """
        if self._ats and not coupon.startswith(u"＠"):
            return False
        if coupon in self._normal:
            return True

        for r in self._regexes:
            if r.match(coupon):
                return True
        return False

class ScenarioCompatibilityTable(object):
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
    >>> import hashlib
    >>> hashlib.md5(open("Summary.wsm", "rb").read()).hexdigest()
    """
    def __init__(self):
        self.table = {}
        if os.path.isfile("Data/Compatibility.xml"):
            data = cw.data.xml2element(path="Data/Compatibility.xml")
            for e in data:
                key = e.get("md5", "")
                zindexmode = e.getattr(".", "zIndexMode", "")
                vanishmembercancellation = e.getbool(".", "enableVanishMemberCancellation", False)
                # F9でもゴシップや終了印が復元されない挙動の再現は
                # セキュリティホールになるため無効にする
                ##gossiprestoration = e.getbool(".", "disableGossipRestoration", False)
                ##compstamprestoration = e.getbool(".", "disableCompleteStampRestoration", False)
                gossiprestoration = False
                compstamprestoration = False
                if key and (e.text or zindexmode or vanishmembercancellation or gossiprestoration or compstamprestoration):
                    self.table[key] = (e.text, zindexmode, vanishmembercancellation, gossiprestoration, compstamprestoration)

    def get_versionhint(self, fpath=None, filedata=None):
        """fpathのファイル内容またはfiledataから、
        本来そのファイルが再生されるべきCardWirthの
        バージョンを取得する。
        """
        if filedata:
            key = hashlib.md5(filedata).hexdigest()
        else:
            key = cw.util.get_md5(fpath)

        return self.table.get(key, None)

    def lessthan(self, versionhint, currentversion):
        """currentversionがversionhint以下であればTrueを返す。"""
        if not currentversion:
            return False
        if not currentversion[0]:
            return False
        if not versionhint:
            return False

        try:
            return float(currentversion[0]) <= float(versionhint)
        except:
            return False

    def zindexmode(self, currentversion):
        """メニューカードをプレイヤーカードより前に配置するモードで
        あればTrueを返す。
        """
        if not currentversion:
            return False

        if currentversion[1]:
            try:
                return float(currentversion[1]) <= float("1.20")
            except:
                return False
        else:
            return self.lessthan("1.20", currentversion)

    def enable_vanishmembercancellation(self, currentversion):
        """パーティメンバが再配置される前であれば
        対象消去がキャンセルされるモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[2]

    def disable_gossiprestration(self, currentversion):
        """F9でのゴシップ復元を無効にする問題を
        再現するモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[3]

    def disable_compstamprestration(self, currentversion):
        """F9での終了印復元を無効にする問題を
        再現するモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[4]

    def merge_versionhints(self, hint1, hint2):
        """hint1を高優先度としてhint2とマージする。"""
        if not hint1:
            return hint2
        if not hint2:
            return hint1

        engine = hint1[0]
        if not engine:
            engine = hint2[0]
        zindexmode = hint1[1]
        if not zindexmode:
            zindexmode = hint2[1]
        vanishmembercancellation = hint1[2]
        if not vanishmembercancellation:
            vanishmembercancellation = hint2[2]
        gossiprestration = hint1[3]
        if not gossiprestration:
            gossiprestration = hint2[3]
        compstamprestration = hint1[4]
        if not compstamprestration:
            compstamprestration = hint2[4]

        return (engine, zindexmode, vanishmembercancellation, gossiprestration, compstamprestration)

    def from_basehint(self, basehint):
        """basehintから複合情報を生成する。"""
        if not basehint:
            return None
        return (basehint, "", False, False, False)

    def to_basehint(self, versionhint):
        """複合情報versionhintから最も基本的な情報を取り出す。"""
        if versionhint:
            return versionhint[0] if versionhint[0] else ""
        else:
            return ""

    def read_modeini(self, fpath):
        """クラシックなシナリオのmode.iniから互換性情報を読み込む。
        互換性情報が無いか、読込に失敗した場合はNoneを返す。
        """
        try:
            conf = ConfigParser.SafeConfigParser()
            conf.read(fpath)

            try:
                engine = conf.get("Compatibility", "engine")
            except:
                engine = ""

            try:
                zindexmode = conf.get("Compatibility", "zIndexMode")
            except:
                zindexmode = ""

            try:
                vanishmembercancellation = conf.get("Compatibility", "enableVanishMemberCancellation")
                vanishmembercancellation = cw.util.str2bool(vanishmembercancellation)
            except:
                vanishmembercancellation = False

            # F9でもゴシップや終了印が復元されない挙動の再現は
            # セキュリティホールになるため無効にする
            gossiprestration = False
            ##try:
            ##    gossiprestration = conf.get("Compatibility", "disableGossipRestoration")
            ##    gossiprestration = cw.util.str2bool(gossiprestration)
            ##except:
            ##    gossiprestration = False

            compstamprestration = False
            ##try:
            ##    compstamprestration = conf.get("Compatibility", "disableCompleteStampRestoration")
            ##    compstamprestration = cw.util.str2bool(compstamprestration)
            ##except:
            ##    compstamprestration = False

            if engine or zindexmode or vanishmembercancellation or gossiprestration or compstamprestration:
                return (engine, zindexmode, vanishmembercancellation, gossiprestration, compstamprestration)
        except Exception:
            cw.util.print_ex()
        return None
