#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes
import hashlib
import math
import struct
import shutil
import weakref
import array
import re
import threading
import copy
import configparser
import time
import wx
import pygame
import pygame.locals

import cw

import typing
from typing import List, Callable, Dict, KeysView, Generator, Generic, Iterable, NoReturn, Optional, Sequence, Set,\
    Tuple, TypeVar, Union


_KeyType = TypeVar("_KeyType")
_ResType = TypeVar("_ResType")


CWXEDITOR_RESOURCES: Dict[str, str]


class NoFontError(ValueError):
    pass


if sys.platform != "win32":
    # wx.Appのロード前にフォントをインストールしなければならない
    DATA_PATH = "Data"
    if sys.platform == "darwin":
        try:
            fontconfig = ctypes.CDLL("/opt/X11/lib/libfontconfig.dylib")
        except Exception:
            fontconfig = None
        # application bundle に入っている場合は、application bundle と同じ位置にあるDataディレクトリを使う
        if 'RESOURCEPATH' in os.environ:
            data_path = os.path.join(os.environ['RESOURCEPATH'], '..', '..', '..', 'Data')
            if os.path.isdir(data_path):
                DATA_PATH = data_path
    else:
        try:
            fontconfig = ctypes.CDLL("libfontconfig.so")
        except Exception:
            try:
                fontconfig = ctypes.CDLL("libfontconfig.so.1")
            except Exception:
                fontconfig = None
    if fontconfig:
        fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
        fcconfig = fontconfig.FcConfigGetCurrent()
        for dpath, dnames, fnames in os.walk(DATA_PATH):
            for fname in fnames:
                if fname.lower().endswith(".ttf"):
                    path = os.path.join(dpath, fname)
                    if os.path.isfile(path):
                        encoding = sys.getfilesystemencoding()
                        fontconfig.FcConfigAppFontAddFile(ctypes.c_void_p(fcconfig),
                                                          ctypes.c_char_p(path.encode(encoding)))

# マウスホイールを上回転させた時の挙動
WHEEL_SELECTION = "Selection"  # カードや選択肢を選ぶ
WHEEL_SHOWLOG = "ShowLog"  # バックログを表示

# カーソルのタイプ
CURSOR_BLACK = "Black"  # 黒いカーソル(デフォルト)
CURSOR_WHITE = "White"  # 白いカーソル

# メッセージログの表示形式
LOG_SINGLE = "Single"
LOG_LIST = "List"
LOG_COMPRESS = "Compress"

# 起動時の挙動
OPEN_TITLE = "Title"
OPEN_LAST_BASE = "LastBase"

# 保存前のダイアログ表示の有無
CONFIRM_BEFORESAVING_YES = "True"
CONFIRM_BEFORESAVING_NO = "False"
CONFIRM_BEFORESAVING_BASE = "BaseOnly"  # 宿にいる時に限り表示

# カードの売却・破棄確認ダイアログ表示の有無
CONFIRM_DUMPCARD_ALWAYS = "Always"
CONFIRM_DUMPCARD_SENDTO = "SendOnly"
CONFIRM_DUMPCARD_NO = "False"

# ステータスバーのボタン状態
SB_PRESSED = 0b00000001  # 押下
SB_CURRENT = 0b00000010  # カーソル下
SB_DISABLE = 0b00000100  # 無効状態
SB_NOTICE = 0b00001000  # 通知
SB_EMPHASIZE = 0b00010000  # 強調

# フォントの表示例
FONT_EXAMPLE_FORMAT_INIT = "%fontface%\\nAaあぁアァ亜宇"
FONT_EXAMPLE_PIXEL_SIZE_INIT = 24


class LocalSetting(object):

    def __init__(self) -> None:
        """スキンで上書き可能な設定。"""
        pass

    def init(self) -> None:
        self.important_draw = False
        self.important_draw_init = self.important_draw
        self.important_font = False
        self.important_font_init = self.important_font

        self.mwincolour = (0, 0, 80, 180)
        self.mwincolour_init = self.mwincolour
        self.mwinframecolour = (128, 0, 0, 255)
        self.mwinframecolour_init = self.mwinframecolour
        self.blwincolour = (80, 80, 80, 180)
        self.blwincolour_init = self.blwincolour
        self.blwinframecolour = (128, 128, 128, 255)
        self.blwinframecolour_init = self.blwinframecolour
        self.curtaincolour = (0, 0, 80, 128)
        self.curtaincolour_init = self.curtaincolour
        self.blcurtaincolour = (0, 0, 0, 192)
        self.blcurtaincolour_init = self.blcurtaincolour
        self.fullscreenbackgroundtype = 2
        self.fullscreenbackgroundtype_init = self.fullscreenbackgroundtype
        self.fullscreenbackgroundfile = "Resource/Image/Dialog/PAD"
        self.fullscreenbackgroundfile_init = self.fullscreenbackgroundfile

        self.decorationfont = False
        self.decorationfont_init = self.decorationfont
        self.bordering_cardname = True
        self.bordering_cardname_init = self.bordering_cardname
        self.fontsmoothing_message = False
        self.fontsmoothing_message_init = self.fontsmoothing_message
        self.fontsmoothing_cardname = False
        self.fontsmoothing_cardname_init = self.fontsmoothing_cardname
        self.fontsmoothing_statusbar = True
        self.fontsmoothing_statusbar_init = self.fontsmoothing_statusbar

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
            "targetlevel": ("pmincho", "", -1, True, True, True),
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
            "screenshot": ("pmincho", "", 18, False, False, False),
        }
        self.msg_exfonts = {
            "fw_symbol": ("inherit", "", 22, True, True, False),
            "fw_number": ("inherit", "", 22, True, True, False),
            "fw_latin": ("inherit", "", 22, True, True, False),
            "hiragana": ("inherit", "", 22, True, True, False),
            "katakana": ("inherit", "", 22, True, True, False),
            "hw_katakana": ("inherit", "", 22, True, True, False),
            "greek_and_cyrillic": ("inherit", "", 22, True, True, False),
            "jis_kanji_1": ("inherit", "", 22, True, True, False),
            "jis_kanji_2": ("inherit", "", 22, True, True, False),
            "etc_kanji": ("inherit", "", 22, True, True, False),
            "symbol": ("inherit", "", 22, True, True, False),
            "number": ("inherit", "", 22, True, True, False),
            "latin": ("inherit", "", 22, True, True, False),
        }

        # Windowsのフォントが使用可能であれば優先して使用する
        facenames = set(wx.FontEnumerator().GetFacenames())
        if "MS UI Gothic" in facenames:
            self.basefont["uigothic"] = "MS UI Gothic"
        if "ＭＳ 明朝" in facenames:
            self.basefont["mincho"] = "ＭＳ 明朝"
        if "ＭＳ Ｐ明朝" in facenames:
            self.basefont["pmincho"] = "ＭＳ Ｐ明朝"
        if "ＭＳ ゴシック" in facenames:
            self.basefont["gothic"] = "ＭＳ ゴシック"
        if "ＭＳ Ｐゴシック" in facenames:
            self.basefont["pgothic"] = "ＭＳ Ｐゴシック"

        self.basefont_init = self.basefont.copy()
        self.fonttypes_init = self.fonttypes.copy()
        self.msg_exfonts_init = self.msg_exfonts.copy()

    def load(self, data: Union[cw.data.CWPyElementTree, cw.data.CWPyElement]) -> None:
        """dataから設定をロードする。"""
        self.basefont = self.basefont_init.copy()
        self.fonttypes = self.fonttypes_init.copy()
        self.msg_exfonts = self.msg_exfonts_init.copy()

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

        def read_font(e: cw.data.CWPyElement, table: Dict[str, Tuple[str, str, int, bool, bool, bool]],
                      table_init: Dict[str, Tuple[str, str, int, bool, bool, bool]]) -> None:
            key = e.getattr(".", "key", "")
            if not key or key not in table_init:
                return
            _deftype, _defname, defpixels, defbold, defbold_upscr, defitalic = table_init[key]

            fonttype = e.getattr(".", "type", "")
            name = e.text if e.text else ""
            pixels = e.getint(".", "pixels", defpixels)
            bold_s = e.getattr(".", "bold", "")
            if bold_s == "":
                bold = defbold
            else:
                bold = cw.util.str2bool(bold_s)
            bold_upscr_s = e.getattr(".", "expandedbold", "")
            if bold_upscr_s == "":
                bold_upscr = defbold_upscr
            else:
                bold_upscr = cw.util.str2bool(bold_upscr_s)
            italic_s = e.getattr(".", "italic", "")
            if italic_s == "":
                italic = defitalic
            else:
                italic = cw.util.str2bool(italic_s)
                table[key] = (fonttype, name, pixels, bold, bold_upscr, italic)

        # 役割別フォント
        for e in data.getfind("Fonts", raiseerror=False):
            read_font(e, self.fonttypes, self.fonttypes_init)
        # メッセージ用混植フォント
        e_synthfont = data.find("SyntheticFonts")
        if e_synthfont is not None and e_synthfont.getattr(".", "key", "") == "message":
            for e in e_synthfont:
                read_font(e, self.msg_exfonts, self.msg_exfonts_init)

        # フルスクリーン時の背景タイプ(0:無し,1:ファイル指定,2:スキン)
        self.fullscreenbackgroundtype = data.getint("FullScreenBackgroundType", self.fullscreenbackgroundtype_init)
        # フルスクリーン時の背景ファイル
        self.fullscreenbackgroundfile = data.gettext("FullScreenBackgroundFile", self.fullscreenbackgroundfile_init)

    def copy(self) -> "LocalSetting":
        return copy.deepcopy(self)


class Setting(object):
    skintype: str
    skinname: str
    initialcash: int

    msgs: "MsgDict"

    sexes: List[cw.features.Sex]
    sexcoupons: List[str]
    sexnames: List[str]
    sexsubnames: List[str]
    periods: List[cw.features.Period]
    periodcoupons: List[str]
    periodnames: List[str]
    natures: List[cw.features.Nature]
    naturecoupons: List[str]
    naturenames: List[str]
    makings: List[cw.features.Making]
    makingnames: List[str]
    makingcoupons: List[str]
    races: List["cw.header.RaceHeader"]
    unknown_race: "cw.header.UnknownRaceHeader"
    sampletypes: List[cw.features.SampleType]

    skinsyscoupons: "SystemCoupons"

    _classicstyletext: bool

    def __init__(self) -> None:
        # フレームレート
        self.fps = 60
        # 1frame分のmillseconds
        self.frametime = 1000 // self.fps

        self.skin_local = LocalSetting()
        self.local = LocalSetting()

    def init_settings(self, loadfile: Optional[str] = None, init: bool = True) -> None:
        path = cw.util.join_paths("Data/SkinBase/Skin.xml")
        basedata = cw.data.xml2etree(path)

        self.skin_local.init()
        self.local.init()

        # "Settings.xml"がなかったら新しく作る
        self.show_advancedsettings = False
        self.show_advancedsettings_init = self.show_advancedsettings
        self.editor = "cwxeditor"
        self.editor_init = self.editor
        self.startupscene = OPEN_TITLE
        self.startupscene_init = self.startupscene
        self.lastyado = ""
        self.lastyado_init = self.lastyado
        self.lastscenario: List[str] = []
        self.lastscenario_init = self.lastscenario[:]
        self.lastscenariopath = ""
        self.lastscenariopath_init = self.lastscenariopath
        self.lastfindresult: List[Union[cw.header.ScenarioHeader, str, cw.dialog.scenarioselect.FindResult]] = []
        self.lastfindresult_init = self.lastfindresult[:]
        self.window_position: Tuple[Optional[int], Optional[int]] = (None, None)
        self.window_position_init = self.window_position
        self.expanddrawing = 1.0
        self.expanddrawing_init = self.expanddrawing
        self.expandmode = "FullScreen"
        self.expandmode_init = self.expandmode
        self.is_expanded = False
        self.is_expanded_init = self.is_expanded
        self.smoothexpand = True
        self.smoothexpand_init = self.smoothexpand
        self.debug = False
        self.debug_init = self.debug
        self.debug_saved = False
        self.debug_saved_init = self.debug_saved
        self.no_levelup_in_debugmode = False
        self.no_levelup_in_debugmode_init = self.no_levelup_in_debugmode
        self.play_bgm = True
        self.play_bgm_init = self.play_bgm
        self.play_sound = True
        self.play_sound_init = self.play_sound
        self.vol_master = 0.75
        self.vol_master_init = self.vol_master
        self.vol_bgm = 0.4
        self.vol_bgm_init = self.vol_bgm
        self.vol_bgm_midi = 0.4
        self.vol_bgm_midi_init = self.vol_bgm_midi
        self.vol_sound = 0.4
        self.vol_sound_init = self.vol_sound
        self.vol_sound_midi = 0.4
        self.vol_sound_midi_init = self.vol_sound_midi
        self.soundfonts = [(cw.DEFAULT_SOUNDFONT, True, 100)]
        self.soundfonts_init = self.soundfonts[:]
        self.bassmidi_sample32bit = True
        self.bassmidi_sample32bit_init = self.bassmidi_sample32bit
        self.sdlmixer_enabled = False
        self.sdlmixer_enabled_init = self.sdlmixer_enabled
        self.messagespeed = 5
        self.messagespeed_init = self.messagespeed
        # メッセージで句読点の後に空白時間を入れる
        self.wait_after_punctuation_mark = True
        self.wait_after_punctuation_mark_init = self.wait_after_punctuation_mark
        self.dealspeed = 5
        self.dealspeed_init = self.dealspeed
        self.dealspeed_battle = 5
        self.dealspeed_battle_init = self.dealspeed_battle
        self.wait_usecard = True
        self.wait_usecard_init = self.wait_usecard
        self.zoomout_friend = True
        self.zoomout_friend_init = self.zoomout_friend
        self.enlarge_beastcardzoomingratio = True
        self.enlarge_beastcardzoomingratio_init = self.enlarge_beastcardzoomingratio
        self.use_battlespeed = False
        self.use_battlespeed_init = self.use_battlespeed
        self.transition = "Fade"
        self.transition_init = self.transition
        self.transitionspeed = 5
        self.transitionspeed_init = self.transitionspeed
        self.smoothscale_bg = False
        self.smoothscale_bg_init = self.smoothscale_bg
        self.smoothing_card_up = True
        self.smoothing_card_up_init = self.smoothing_card_up
        self.smoothing_card_down = True
        self.smoothing_card_down_init = self.smoothing_card_down
        self.caution_beforesaving = True
        self.caution_beforesaving_init = self.caution_beforesaving
        self.revert_cardpocket = True
        self.revert_cardpocket_init = self.revert_cardpocket
        self.quickdeal = True
        self.quickdeal_init = self.quickdeal
        self.all_quickdeal = False
        self.all_quickdeal_init = self.all_quickdeal
        self.skindirname = "Classic"
        self.skindirname_init = self.skindirname
        self.vocation120 = False
        self.vocation120_init = self.vocation120
        self.sort_yado = "None"
        self.sort_yado_init = self.sort_yado
        self.sort_standbys = "None"
        self.sort_standbys_init = self.sort_standbys
        self.sort_parties = "None"
        self.sort_parties_init = self.sort_parties
        self.sort_cards = "None"
        self.sort_cards_init = self.sort_cards
        self.sort_cardswithstar = True
        self.sort_cardswithstar_init = self.sort_cardswithstar
        self.card_narrow = ""
        self.card_narrow_init = self.card_narrow
        self.card_narrowtype = 1
        self.card_narrowtype_init = self.card_narrowtype
        self.edit_star = False
        self.edit_star_init = self.edit_star
        self.yado_narrowtype = 1
        self.yado_narrowtype_init = self.yado_narrowtype
        self.standbys_narrowtype = 1
        self.standbys_narrowtype_init = self.standbys_narrowtype
        self.parties_narrowtype = 1
        self.parties_narrowtype_init = self.parties_narrowtype
        self.infoview_narrowtype = 1
        self.infoview_narrowtype_init = self.infoview_narrowtype
        self.backlogmax = 100
        self.backlogmax_init = self.backlogmax
        self.messagelog_type = LOG_COMPRESS
        self.messagelog_type_init = self.messagelog_type
        self.display_bill_in_messagelog = True
        self.display_bill_in_messagelog_init = self.display_bill_in_messagelog
        self.showfps = False
        self.showfps_init = self.showfps
        self.selectscenariofromtype = True
        self.selectscenariofromtype_init = self.selectscenariofromtype
        self.show_unfitnessscenario = True
        self.show_unfitnessscenario_init = self.show_unfitnessscenario
        self.show_completedscenario = True
        self.show_completedscenario_init = self.show_completedscenario
        self.show_invisiblescenario = False
        self.show_invisiblescenario_init = self.show_invisiblescenario
        self.wheelup_operation = WHEEL_SHOWLOG
        self.wheelup_operation_init = self.wheelup_operation
        self.show_allselectedcards = True
        self.show_allselectedcards_init = self.show_allselectedcards
        self.show_aim = True
        self.show_aim_init = self.show_aim
        self.confirm_beforeusingcard = True
        self.confirm_beforeusingcard_init = self.confirm_beforeusingcard
        self.confirm_beforesaving = CONFIRM_BEFORESAVING_YES
        self.confirm_beforesaving_init = self.confirm_beforesaving
        self.confirm_dumpcard = CONFIRM_DUMPCARD_ALWAYS
        self.confirm_dumpcard_init = self.confirm_dumpcard
        self.show_savedmessage = True
        self.show_savedmessage_init = self.show_savedmessage
        self.show_backpackcard = True
        self.show_backpackcard_init = self.show_backpackcard
        self.show_backpackcardatend = False
        self.show_backpackcardatend_init = self.show_backpackcardatend
        self.show_statustime = "NotEventTime"
        self.show_statustime_init = self.show_statustime
        self.noticeimpossibleaction = True
        self.noticeimpossibleaction_init = self.noticeimpossibleaction
        self.initmoneyamount = basedata.getint("Property/InitialCash", 4000)
        self.initmoneyamount_init = self.initmoneyamount
        self.initmoneyisinitialcash = True
        self.initmoneyisinitialcash_init = self.initmoneyisinitialcash
        self.autosave_partyrecord = True
        self.autosave_partyrecord_init = self.autosave_partyrecord
        self.overwrite_partyrecord = True
        self.overwrite_partyrecord_init = self.overwrite_partyrecord
        self.folderoftype: List[Tuple[str, str]] = []
        self.folderoftype_init = self.folderoftype[:]
        self.scenario_narrow = ""
        self.scenario_narrow_init = self.scenario_narrow
        self.scenario_narrowtype = 1
        self.scenario_narrowtype_init = self.scenario_narrowtype
        self.scenario_sorttype = 0
        self.scenario_sorttype_init = self.scenario_sorttype
        self.ssinfoformat = "[%scenario%[(%author%)] - ][%party% at ]%yado%"
        self.ssinfoformat_init = self.ssinfoformat
        self.ssfnameformat = \
            "ScreenShot/[%yado%/[%party%_]]%year%%month%%day%_%hour%%minute%%second%[_in_%scenario%].png"
        self.ssfnameformat_init = self.ssfnameformat
        self.cardssfnameformat = \
            "ScreenShot/[%yado%/[%party%_]]%year%%month%%day%_%hour%%minute%%second%[_in_%scenario%].png"
        self.cardssfnameformat_init = self.cardssfnameformat
        self.sswithstatusbar = True
        self.sswithstatusbar_init = self.sswithstatusbar
        self.titleformat = "%application% %skin%[ - %yado%[ %scenario%]]"
        self.titleformat_init = self.titleformat
        self.playlogformat = "PlayLog/%yado%/%party%_%year%%month%%day%_%hour%%minute%%second%_%scenario%.txt"
        self.playlogformat_init = self.playlogformat
        self.ssinfofontcolor = (0, 0, 0)
        self.ssinfofontcolor_init = self.ssinfofontcolor
        self.ssinfobackcolor = (255, 255, 255)
        self.ssinfobackcolor_init = self.ssinfobackcolor
        self.ssinfobackimage = ""
        self.ssinfobackimage_init = self.ssinfobackimage
        self.show_lifebar_on_selection = True
        self.show_lifebar_on_selection_init = self.show_lifebar_on_selection
        self.show_fcardsinbattle = False
        self.show_fcardsinbattle_init = self.show_fcardsinbattle
        self.statusbarmask = True
        self.statusbarmask_init = self.statusbarmask
        self.show_experiencebar = True
        self.show_experiencebar_init = self.show_experiencebar
        self.show_roundautostartbutton = True
        self.show_roundautostartbutton_init = self.show_roundautostartbutton
        self.show_autobuttoninentrydialog = True
        self.show_autobuttoninentrydialog_init = self.show_autobuttoninentrydialog
        self.unconvert_targetfolder = "UnconvertedYado"
        self.unconvert_targetfolder_init = self.unconvert_targetfolder
        self.show_tiles = False
        self.show_tiles_init = self.show_tiles
        self.enabled_right_flick = False
        self.enabled_right_flick_init = self.enabled_right_flick
        self.can_repeatlclick = False
        self.can_repeatlclick_init = self.can_repeatlclick
        self.shiftup_touchbutton = True  # タッチボタンをスライド表示する
        self.shiftup_touchbutton_init = self.shiftup_touchbutton
        self.flick_time_msec = 300
        self.flick_time_msec_init = self.flick_time_msec
        self.flick_distance = 30
        self.flick_distance_init = self.flick_distance
        self.can_skipwait = True
        self.can_skipwait_init = self.can_skipwait
        self.can_skipanimation = True
        self.can_skipanimation_init = self.can_skipanimation
        self.can_skipwait_with_wheel = True
        self.can_skipwait_with_wheel_init = self.can_skipwait_with_wheel
        self.can_forwardmessage_with_wheel = True
        self.can_forwardmessage_with_wheel_init = self.can_forwardmessage_with_wheel
        self.cursor_type = CURSOR_WHITE
        self.cursor_type_init = self.cursor_type
        self.autoenter_on_sprite = False
        self.autoenter_on_sprite_init = self.autoenter_on_sprite
        self.blink_statusbutton = True
        self.blink_statusbutton_init = self.blink_statusbutton
        self.blink_partymoney = True
        self.blink_partymoney_init = self.blink_partymoney
        self.show_btndesc = True
        self.show_btndesc_init = self.show_btndesc
        self.protect_staredcard = True
        self.protect_staredcard_init = self.protect_staredcard
        self.protect_premiercard = True
        self.protect_premiercard_init = self.protect_premiercard
        self.show_cardkind = True
        self.show_cardkind_init = self.show_cardkind
        self.show_premiumicon = False
        self.show_premiumicon_init = self.show_premiumicon
        self.can_clicksidesofcardcontrol = True
        self.can_clicksidesofcardcontrol_init = self.can_clicksidesofcardcontrol
        self.radius_notdetectmovement = 5
        self.radius_notdetectmovement_init = self.radius_notdetectmovement
        self.show_paperandtree = False
        self.show_paperandtree_init = self.show_paperandtree
        self.filer_dir = ""
        self.filer_dir_init = self.filer_dir
        self.filer_file = ""
        self.filer_file_init = self.filer_file
        self.recenthistory_limit = 5  # 展開したシナリオを取っておく数
        self.recenthistory_limit_init = self.recenthistory_limit
        self.volume_increment = 5  # ホイールによる全体音量調節での増減量
        self.volume_increment_init = self.volume_increment
        self.show_debuglogdialog = True
        self.show_debuglogdialog_init = self.show_debuglogdialog
        self.enabled_timekeeper = True
        self.enabled_timekeeper_init = self.enabled_timekeeper
        self.write_playlog = False
        self.write_playlog_init = self.write_playlog
        self.move_repeat = 250  # 移動ボタン押しっぱなしの速度
        self.move_repeat_init = self.move_repeat
        self.open_lastscenario = True  # 最後に表示したシナリオを開くか
        self.open_lastscenario_init = self.open_lastscenario
        self.open_lastfindresult = False  # 最後の検索結果を再表示するか
        self.open_lastfindresult_init = self.open_lastfindresult
        self.spend_noeffectcard = True  # キーコード等の効果が無くても常にカードを消費するか
        self.spend_noeffectcard_init = self.spend_noeffectcard
        # シナリオ選択ダイアログへシナリオをドロップした時はインストールダイアログを表示する
        # Falseの場合は常に検索結果として表示
        self.can_installscenariofromdrop = False
        self.can_installscenariofromdrop_init = self.can_installscenariofromdrop
        # シナリオのインストールに成功したら元ファイルを削除する
        self.delete_sourceafterinstalled = False
        self.delete_sourceafterinstalled_init = self.delete_sourceafterinstalled
        # シナリオのインストール時にシナリオ以外のファイルもコピーする
        self.install_notscenariofiles = True
        self.install_notscenariofiles_init = self.install_notscenariofiles
        # アップデートに伴うファイルの自動移動・削除を行う
        self.auto_update_files = True
        self.auto_update_files_init = self.auto_update_files
        # フォント表示例のフォーマット
        self.fontexampleformat = FONT_EXAMPLE_FORMAT_INIT
        self.fontexampleformat_init = self.fontexampleformat
        self.fontexamplepixelsize = FONT_EXAMPLE_PIXEL_SIZE_INIT
        self.fontexamplepixelsize_init = self.fontexamplepixelsize
        # 最小化中に完全に停止する
        self.stop_the_world_with_iconized = True
        self.stop_the_world_with_iconized_init = self.stop_the_world_with_iconized
        # 送り先のカードが一杯の時は交換ダイアログを開く
        self.replacecard_when_sendfullcardpocket = True
        self.replacecard_when_sendfullcardpocket_init = self.replacecard_when_sendfullcardpocket
        # プレミアカード選択中でも売却と破棄を表示する
        self.show_sell_with_premiercard = True
        self.show_sell_with_premiercard_init = self.show_sell_with_premiercard
        # 荷物袋にあるカードのキャラクターごとの私有を許可する
        self.show_personal_cards = True
        self.show_personal_cards_init = self.show_personal_cards
        # 私物入れの容量がレベル調節の影響を受けるようにする
        self.level_adjustment_affect_personal_pocket = True
        self.level_adjustment_affect_personal_pocket_init = self.level_adjustment_affect_personal_pocket

        # 宿の表示順序
        self.yado_order: Dict[str, int] = {}
        self.yado_order_init = self.yado_order.copy()

        # 絞り込み・整列などのコントロールの表示有無
        self.show_additional_yado = False
        self.show_additional_yado_init = self.show_additional_yado
        self.show_additional_player = False
        self.show_additional_player_init = self.show_additional_player
        self.show_additional_party = False
        self.show_additional_party_init = self.show_additional_party
        self.show_additional_scenario = False
        self.show_additional_scenario_init = self.show_additional_scenario
        self.show_additional_card = False
        self.show_additional_card_init = self.show_additional_card
        # 表示有無切替ボタン自体の表示有無
        self.show_addctrlbtn = True
        self.show_addctrlbtn_init = self.show_addctrlbtn

        # カード選択ダイアログの移動モードの背景色を変更する
        self.trademode_cardholder_color = (32, 32, 64)
        self.trademode_cardholder_color_init = self.trademode_cardholder_color

        # カード種の表示・非表示
        self.show_cardtype = [True] * 3
        self.show_cardtype_init = self.show_cardtype[:]
        # カード選択ダイアログで選択中のカード種別
        self.last_cardpocket = 0
        self.last_cardpocket_init = self.last_cardpocket
        # カード選択ダイアログでの転送先
        self.last_sendto = 0
        self.last_sendto_init = self.last_sendto
        # カード選択ダイアログでのページ
        self.last_storehousepage = 0
        self.last_storehousepage_init = self.last_storehousepage
        self.last_backpackpage = 0
        self.last_backpackpage_init = self.last_backpackpage
        self.last_cardpocketbpage = [0] * 3  # 荷物袋からの使用
        self.last_cardpocketbpage_init = self.last_cardpocketbpage[:]

        # 一覧表示
        self.show_multiplebases = False
        self.show_multiplebases_init = self.show_multiplebases
        self.show_multipleparties = False
        self.show_multipleparties_init = self.show_multipleparties
        self.show_multipleplayers = False
        self.show_multipleplayers_init = self.show_multipleplayers
        self.show_scenariotree = False
        self.show_scenariotree_init = self.show_scenariotree

        # シナリオのインストール先(キー=ルートディレクトリ毎)
        self.installed_dir: Dict[str, List[str]] = {}
        self.installed_dir_init = self.installed_dir.copy()

        # カード編集ダイアログのブックマーク
        self.bookmarks_for_cardedit: List[Tuple[str, str]] = []
        self.bookmarks_for_cardedit_init = self.bookmarks_for_cardedit[:]

        if not init:
            return

        cw.fsync.sync()
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
        self.show_advancedsettings = data.getbool("ShowAdvancedSettings", self.show_advancedsettings_init)

        # シナリオエディタ
        self.editor = data.gettext("ScenarioEditor", self.editor_init)

        # 起動時の動作
        self.startupscene = data.gettext("StartupScene", self.startupscene_init)
        # 最後に選択した宿
        self.lastyado = data.gettext("LastYado", self.lastyado_init)
        # 最後に選択したシナリオ(ショートカットがあるため経路を記憶)
        self.lastscenario = []
        self.lastscenariopath = ""  # 経路が辿れない時に使用するフルパス
        # ウィンドウ位置
        win_x: Optional[int] = data.getint("WindowPosition", "left", -sys.maxsize - 1)
        win_y: Optional[int] = data.getint("WindowPosition", "top", -sys.maxsize - 1)
        if -sys.maxsize - 1 == win_x:
            win_x = None
        if -sys.maxsize - 1 == win_y:
            win_y = None
        self.window_position = (win_x, win_y)
        # 拡大モード
        self.expandmode = data.gettext("ExpandMode", self.expandmode_init)
        if self.expandmode == "None":
            self.is_expanded = False
        else:
            self.is_expanded = data.getbool("ExpandMode", "expanded", self.is_expanded_init)
        self.smoothexpand = data.getbool("ExpandMode", "smooth", self.smoothexpand_init)
        # 描画倍率
        if self.expandmode in ("None", "FullScreen"):
            self.expanddrawing = 1.0
        else:
            try:
                self.expanddrawing = float(self.expandmode)
            except Exception:
                self.expanddrawing = 1.0
        self.expanddrawing = data.getfloat("ExpandDrawing", self.expanddrawing_init)
        if self.expanddrawing % 1.0 == 0.0:
            self.expanddrawing = float(int(self.expanddrawing))
        # デバッグモードかどうか
        self.debug = data.getbool("DebugMode", self.debug_init)
        self.debug_saved = self.debug
        if not loadfile:
            if cw.OPTIONS.getbool("debug"):
                # 強制デバッグモード起動
                self.debug = True
            cw.OPTIONS.setbool("debug", False)
        # シナリオの終了時にデバッグ情報を表示する
        self.show_debuglogdialog = data.getbool("ShowDebugLogDialog", self.show_debuglogdialog_init)
        # シナリオのプレイ時間を記録する(隠しオプション)
        self.enabled_timekeeper = data.getbool("EnabledTimekeepr", self.enabled_timekeeper_init)
        # デバッグ時はレベル上昇しない
        self.no_levelup_in_debugmode = data.getbool("NoLevelUpInDebugMode", self.no_levelup_in_debugmode_init)
        # 音楽を再生する
        self.play_bgm = data.getbool("PlayBgm", self.play_bgm_init)
        # 効果音を再生する
        self.play_sound = data.getbool("PlaySound", self.play_sound_init)
        # 音声全体のボリューム(0～1.0)
        self.vol_master = data.getint("MasterVolume", int(self.vol_master_init * 100))
        # 音楽のボリューム(0～1.0)
        self.vol_bgm = data.getint("BgmVolume", int(self.vol_bgm_init * 100))
        # midi音楽のボリューム(0～1.0)
        self.vol_bgm_midi = data.getint("BgmVolume", "midi", int(self.vol_bgm_init * 100))
        # 効果音ボリューム
        self.vol_sound = data.getint("SoundVolume", int(self.vol_sound_init * 100))
        # midi効果音のボリューム(0～1.0)
        self.vol_sound_midi = data.getint("SoundVolume", "midi", int(self.vol_sound_init * 100))
        # 音量の単位変更(0～100 to 0～1)
        self.vol_master = Setting.wrap_volumevalue(self.vol_master)
        self.vol_bgm = Setting.wrap_volumevalue(self.vol_bgm)
        self.vol_bgm_midi = Setting.wrap_volumevalue(self.vol_bgm_midi)
        self.vol_sound = Setting.wrap_volumevalue(self.vol_sound)
        self.vol_sound_midi = Setting.wrap_volumevalue(self.vol_sound_midi)
        # MIDIサウンドフォント
        elements = data.find("SoundFonts")
        if elements is not None:
            self.soundfonts = []
            for e in elements:
                assert isinstance(e, cw.data.CWPyElement)
                use = e.getbool(".", "enabled", True)
                volume = e.getint(".", "volume", 100)
                self.soundfonts.append((e.text, use, volume))
        # 32bitオプションでMIDIを再生する
        self.bassmidi_sample32bit = data.getbool("Bassmidi32bit", self.bassmidi_sample32bit_init)
        # BASS Audioが使えない時にSDL_mixerを使用する
        self.sdlmixer_enabled = data.getbool("SDLMixerIsEnabled", self.sdlmixer_enabled_init)
        # メッセージスピード(数字が小さいほど速い)(0～100)
        self.messagespeed = data.getint("MessageSpeed", self.messagespeed_init)
        self.messagespeed = cw.util.numwrap(self.messagespeed, 0, 100)
        # カードの表示スピード(数字が小さいほど速い)(1～100)
        dealspeed = data.getint("CardDealingSpeed", self.dealspeed_init)
        # 戦闘行動の表示スピード(数字が小さいほど速い)(1～100)
        dealspeed_battle = data.getint("CardDealingSpeedInBattle", self.dealspeed_battle_init)
        use_battlespeed = data.getbool("CardDealingSpeedInBattle", "enabled", self.use_battlespeed_init)
        self.set_dealspeed(dealspeed, dealspeed_battle, use_battlespeed)
        # メッセージで句読点の後に空白時間を入れる
        self.wait_after_punctuation_mark = data.getbool("WaitAfterPunctuationMark",
                                                        self.wait_after_punctuation_mark_init)
        # カードの使用前に空白時間を入れる
        self.wait_usecard = data.getbool("WaitUseCard", self.wait_usecard_init)
        # 同行キャストの行動後に縮小処理を行う
        self.zoomout_friend = data.getbool("ZoomOutFriendCard", self.zoomout_friend_init)
        # 召喚獣カードの拡大率を大きくする
        self.enlarge_beastcardzoomingratio = data.getbool("EnlargeBeastCardZoomingRatio",
                                                          self.enlarge_beastcardzoomingratio_init)
        # トランジション効果の種類
        self.transition = data.gettext("Transition", self.transition_init)
        self.transitionspeed = data.getint("Transition", "speed", self.transitionspeed_init)
        self.transitionspeed = cw.util.numwrap(self.transitionspeed, 0, 10)
        # 背景のスムーススケーリング
        self.smoothscale_bg = data.getbool("SmoothScaling", "bg", self.smoothscale_bg_init)
        self.smoothing_card_up = data.getbool("SmoothScaling", "upcard", self.smoothing_card_up_init)
        self.smoothing_card_down = data.getbool("SmoothScaling", "downcard", self.smoothing_card_down_init)
        # 保存せずに終了しようとしたら警告
        self.caution_beforesaving = data.getbool("CautionBeforeSaving", self.caution_beforesaving_init)
        # レベル調節で手放したカードを自動的に戻す
        self.revert_cardpocket = data.getbool("RevertCardPocket", self.revert_cardpocket_init)
        # キャンプ等に高速で切り替える
        self.quickdeal = data.getbool("QuickDeal", self.quickdeal_init)
        # 全てのシステムカードを高速表示する
        self.all_quickdeal = data.getbool("AllQuickDeal", self.all_quickdeal_init)
        # ソート基準
        self.sort_yado = data.getattr("SortKey", "yado", self.sort_yado_init)
        self.sort_standbys = data.getattr("SortKey", "standbys", self.sort_standbys_init)
        self.sort_parties = data.getattr("SortKey", "parties", self.sort_parties_init)
        self.sort_cards = data.getattr("SortKey", "cards", self.sort_cards_init)
        self.sort_cardswithstar = data.getbool("SortKey", "cardswithstar", self.sort_cardswithstar_init)
        # 拠点絞込条件
        self.yado_narrowtype = data.getint("YadoNarrowType", self.yado_narrowtype_init)
        # 宿帳絞込条件
        self.standbys_narrowtype = data.getint("StandbysNarrowType", self.standbys_narrowtype_init)
        # パーティ絞込条件
        self.parties_narrowtype = data.getint("PartiesNarrowType", self.parties_narrowtype_init)
        # カード絞込条件
        self.card_narrowtype = data.getint("CardNarrowType", self.card_narrowtype_init)
        # 情報カード絞込条件
        self.infoview_narrowtype = data.getint("InfoViewNarrowType", self.infoview_narrowtype_init)
        # メッセージログ最大数
        self.backlogmax = data.getint("MessageLogMax", self.backlogmax_init)
        # メッセージログ表示形式
        self.messagelog_type = data.gettext("MessageLogType", self.messagelog_type_init)
        # メッセージログに貼紙を表示する
        self.display_bill_in_messagelog = data.getbool("DisplayBillInMessageLog", self.display_bill_in_messagelog_init)

        self.showfps = False

        # スキンによってシナリオの選択開始位置を変更する
        self.selectscenariofromtype = data.getbool("SelectScenarioFromType", self.selectscenariofromtype_init)
        # 適正レベル以外のシナリオを表示する
        self.show_unfitnessscenario = data.getbool("ShowUnfitnessScenario", self.show_unfitnessscenario_init)
        # 隠蔽シナリオを表示する
        self.show_completedscenario = data.getbool("ShowCompletedScenario", self.show_completedscenario_init)
        # 終了済シナリオを表示する
        self.show_invisiblescenario = data.getbool("ShowInvisibleScenario", self.show_invisiblescenario_init)

        # マウスホイールを上回転させた時の挙動
        self.wheelup_operation = data.gettext("WheelUpOperation", self.wheelup_operation_init)
        # 戦闘行動を全員分表示する
        self.show_allselectedcards = data.getbool("ShowAllSelectedCards", self.show_allselectedcards_init)
        # 選択キャラクターを対象とする行動を表示する
        self.show_aim = data.getbool("ShowAim", self.show_aim_init)
        # カード使用時に確認ダイアログを表示
        self.confirm_beforeusingcard = data.getbool("ConfirmBeforeUsingCard", self.confirm_beforeusingcard_init)
        # セーブ前に確認ダイアログを表示
        self.confirm_beforesaving = data.gettext("ConfirmBeforeSaving", self.confirm_beforesaving_init)
        # セーブ完了時に確認ダイアログを表示
        self.show_savedmessage = data.getbool("ShowSavedMessage", self.show_savedmessage_init)
        # カードの売却と破棄で確認ダイアログを表示
        self.confirm_dumpcard = data.gettext("ConfirmBeforeDumpCard", self.confirm_dumpcard_init)

        # 不可能な行動を選択した時に警告を表示
        self.noticeimpossibleaction = data.getbool("NoticeImpossibleAction", self.noticeimpossibleaction_init)

        # 荷物袋のカードを一時的に取り出して使えるようにする
        self.show_backpackcard = data.getbool("ShowBackpackCard", self.show_backpackcard_init)
        # 荷物袋カードを最後に配置する
        self.show_backpackcardatend = data.getbool("ShowBackpackCardAtEnd", self.show_backpackcardatend_init)
        # 各種ステータスの残り時間を表示する
        self.show_statustime = data.gettext("ShowStatusTime", self.show_statustime_init)

        # パーティ結成時の持出金額
        self.initmoneyamount = data.getint("InitialMoneyAmount", self.initmoneyamount_init)
        self.initmoneyisinitialcash = data.getbool("InitialMoneyAmount", "sameasbase", self.initmoneyisinitialcash_init)

        # 解散時、自動的にパーティ情報を記録する
        self.autosave_partyrecord = data.getbool("AutoSavePartyRecord", self.autosave_partyrecord_init)
        # 自動記録時、同名のパーティ記録へ上書きする
        self.overwrite_partyrecord = data.getbool("OverwritePartyRecord", self.overwrite_partyrecord_init)

        # シナリオフォルダ(スキンタイプ別)
        for e_folder in data.getfind("ScenarioFolderOfSkinType", False):
            skintype = e_folder.getattr(".", "skintype", "")
            folder = e_folder.gettext(".", "")
            self.folderoftype.append((skintype, folder))

        # シナリオ絞込・整列条件
        self.scenario_narrowtype = data.getint("ScenarioNarrowType", self.scenario_narrowtype_init)
        self.scenario_sorttype = data.getint("ScenarioSortType", self.scenario_sorttype_init)

        # スクリーンショット情報
        self.ssinfoformat = data.gettext("ScreenShotInformationFormat", self.ssinfoformat_init)
        # スクリーンショット情報の色
        r = data.getint("ScreenShotInformationFontColor", "red", self.ssinfofontcolor_init[0])
        g = data.getint("ScreenShotInformationFontColor", "green", self.ssinfofontcolor_init[1])
        b = data.getint("ScreenShotInformationFontColor", "blue", self.ssinfofontcolor_init[2])
        self.ssinfofontcolor = (r, g, b)
        r = data.getint("ScreenShotInformationBackgroundColor", "red", self.ssinfobackcolor_init[0])
        g = data.getint("ScreenShotInformationBackgroundColor", "green", self.ssinfobackcolor_init[1])
        b = data.getint("ScreenShotInformationBackgroundColor", "blue", self.ssinfobackcolor_init[2])
        self.ssinfobackcolor = (r, g, b)
        # スクリーンショット情報の背景イメージ
        self.ssinfobackimage = data.gettext("ScreenShotInformationBackgroundImage", self.ssinfobackimage_init)

        # スクリーンショットのファイル名
        self.ssfnameformat = data.gettext("ScreenShotFileNameFormat", self.ssfnameformat_init)
        # 所持カード撮影情報のファイル名
        self.cardssfnameformat = data.gettext("ScreenShotOfCardsFileNameFormat", self.cardssfnameformat_init)

        # スクリーンショットにステータスバーを含める
        self.sswithstatusbar = data.getbool("ScreenShotWithStatusBar", self.sswithstatusbar_init)

        # イベント中にステータスバーの色を変える
        self.statusbarmask = data.getbool("StatusBarMask", self.statusbarmask_init)

        # 次のレベルアップまでの割合を表示する
        self.show_experiencebar = data.getbool("ShowExperienceBar", self.show_experiencebar_init)

        # バトルラウンドを自動開始可能にする
        self.show_roundautostartbutton = data.getbool("ShowRoundAutoStartButton", self.show_roundautostartbutton_init)

        # 新規登録ダイアログに自動ボタンを表示する
        self.show_autobuttoninentrydialog = data.getbool("ShowAutoButtonInEntryDialog",
                                                         self.show_autobuttoninentrydialog_init)

        # 逆変換先ディレクトリ
        self.unconvert_targetfolder = data.gettext("UnconvertTargetFolder", self.unconvert_targetfolder_init)

        # タッチ操作用のタイルを表示する
        self.show_tiles = data.getbool("ShowTiles", self.show_tiles_init)
        # 右フリックで右クリック相当の操作を行う
        self.enabled_right_flick = data.getbool("EnabledRightFlick", self.enabled_right_flick_init)
        # 一定時間タッチし続けた時は連打状態にする
        self.can_repeatlclick = data.getbool("CanRepeatLClick", self.can_repeatlclick_init)

        # 空白時間をスキップ可能にする
        self.can_skipwait = data.getbool("CanSkipWait", self.can_skipwait_init)
        # アニメーションをスキップ可能にする
        self.can_skipanimation = data.getbool("CanSkipAnimation", self.can_skipanimation_init)
        # マウスのホイールで空白時間とアニメーションをスキップする
        self.can_skipwait_with_wheel = data.getbool("CanSkipWaitWithWheel", self.can_skipwait_with_wheel_init)
        # マウスのホイールでメッセージ送りを行う
        self.can_forwardmessage_with_wheel = data.getbool("CanForwardMessageWithWheel",
                                                          self.can_forwardmessage_with_wheel_init)
        # 方向キーやホイールの選択中にマウスカーソルの移動を検知しない半径
        self.radius_notdetectmovement = data.getint("RadiusForNotDetectingCursorMovement",
                                                    self.radius_notdetectmovement_init)
        # カーソルタイプ
        self.cursor_type = data.gettext("CursorType", self.cursor_type_init)
        # 連打状態の時、カードなどの選択を自動的に決定する
        self.autoenter_on_sprite = data.getbool("AutoEnterOnSprite", self.autoenter_on_sprite_init)
        # 通知のあるステータスボタンを点滅させる
        self.blink_statusbutton = data.getbool("BlinkStatusButton", self.blink_statusbutton_init)
        # 所持金が増減した時に所持金欄を点滅させる
        self.blink_partymoney = data.getbool("BlinkPartyMoney", self.blink_partymoney_init)
        # ステータスバーのボタンの解説を表示する
        self.show_btndesc = data.getbool("ShowButtonDescription", self.show_btndesc_init)
        # スターつきのカードの売却や破棄を禁止する
        self.protect_staredcard = data.getbool("ProtectStaredCard", self.protect_staredcard_init)
        # プレミアカードの売却や破棄を禁止する
        self.protect_premiercard = data.getbool("ProtectPremierCard", self.protect_premiercard_init)
        # プレミアカード選択中でも売却と破棄を表示する
        self.show_sell_with_premiercard = data.getbool("ShowSellAndDumpWithPremierCard",
                                                       self.show_sell_with_premiercard_init)
        # 荷物袋にあるカードのキャラクターごとの私有を許可する
        self.show_personal_cards = data.getbool("ShowPersonalCards", self.show_personal_cards_init)
        # 私物入れの容量がレベル調節の影響を受けるようにする
        self.level_adjustment_affect_personal_pocket = data.getbool("LevelAdjustmentAffectPersonalPocket",
                                                                    self.level_adjustment_affect_personal_pocket_init)
        # カード置場と荷物袋でカードの種類を表示する
        self.show_cardkind = data.getbool("ShowCardKind", self.show_cardkind_init)
        # カードの希少度をアイコンで表示する
        self.show_premiumicon = data.getbool("ShowPremiumIcon", self.show_premiumicon_init)
        # カード選択ダイアログの背景クリックで左右移動を行う
        self.can_clicksidesofcardcontrol = data.getbool("CanClickSidesOfCardControl",
                                                        self.can_clicksidesofcardcontrol_init)
        # シナリオ選択ダイアログで貼紙と一覧を同時に表示する
        self.show_paperandtree = data.getbool("ShowPaperAndTree", self.show_paperandtree_init)
        # シナリオ選択ダイアログでのファイラー
        self.filer_dir = data.gettext("FilerDirectory", self.filer_dir_init)
        self.filer_file = data.gettext("FilerFile", self.filer_file_init)

        # 圧縮されたシナリオの展開データ保存数
        self.recenthistory_limit = data.getint("RecentHistoryLimit", self.recenthistory_limit_init)

        # マウスホイールによる全体音量の増減量
        self.volume_increment = data.getint("VolumeIncrement", self.volume_increment_init)

        # キーコード等の効果が無くても常にカードを消費するか
        self.spend_noeffectcard = data.getbool("SpendNoEffectCard", self.spend_noeffectcard_init)

        # 一覧表示
        self.show_multiplebases = data.getbool("ShowMultipleItems", "base", self.show_multiplebases_init)
        self.show_multipleparties = data.getbool("ShowMultipleItems", "party", self.show_multipleparties_init)
        self.show_multipleplayers = data.getbool("ShowMultipleItems", "player", self.show_multipleplayers_init)
        self.show_scenariotree = data.getbool("ShowMultipleItems", "scenario", self.show_scenariotree_init)

        # タイトルバーの表示内容
        self.titleformat = data.gettext("TitleFormat", self.titleformat_init)

        # 宿の表示順
        for e_yadoorder in data.getfind("YadoOrder", raiseerror=False):
            if e_yadoorder.tag != "Order":
                continue
            name = e_yadoorder.getattr(".", "name")
            order = int(e_yadoorder.text)
            ypath = cw.util.join_paths("Yado", name, "Environment.xml")
            if os.path.isfile(ypath):
                self.yado_order[name] = order

        # 絞り込み・整列などのコントロールの表示有無
        self.show_additional_yado = data.getbool("ShowAdditionalControls", "yado", self.show_additional_yado_init)
        self.show_additional_player = data.getbool("ShowAdditionalControls", "player", self.show_additional_player_init)
        self.show_additional_party = data.getbool("ShowAdditionalControls", "party", self.show_additional_party_init)
        self.show_additional_scenario = data.getbool("ShowAdditionalControls", "scenario",
                                                     self.show_additional_scenario_init)
        self.show_additional_card = data.getbool("ShowAdditionalControls", "card", self.show_additional_card_init)
        # 絞り込み等の表示切替ボタンを表示する
        self.show_addctrlbtn = data.gettext("ShowAdditionalControls",
                                            "" if self.show_addctrlbtn_init else "Hidden") != "Hidden"

        # シナリオのプレイログを出力する
        self.write_playlog = data.getbool("WritePlayLog", self.write_playlog_init)
        # プレイログのフォーマット
        self.playlogformat = data.gettext("PlayLogFormat", self.playlogformat_init)

        # 最小化中に完全に停止する
        self.stop_the_world_with_iconized = data.getbool("StopTheWorldWithIconization",
                                                         self.stop_the_world_with_iconized_init)

        # 最後に選んだシナリオを開始位置にする
        self.open_lastscenario = data.getbool("OpenLastScenario", self.open_lastscenario_init)
        # 最後のシナリオ検索結果を再表示する
        self.open_lastfindresult = data.getbool("OpenFindScenarioResult", self.open_lastfindresult_init)
        # ドロップによるシナリオのインストールを可能にする
        self.can_installscenariofromdrop = data.getbool("CanInstallScenarioFromDrop",
                                                        self.can_installscenariofromdrop_init)
        # シナリオのインストールに成功したら元ファイルを削除する
        self.delete_sourceafterinstalled = data.getbool("DeleteSourceAfterInstalled",
                                                        self.delete_sourceafterinstalled_init)
        # シナリオのインストール時にシナリオ以外のファイルもコピーする
        self.install_notscenariofiles = data.getbool("InstallNotScenarioFiles", self.install_notscenariofiles_init)

        # アップデートに伴うファイルの自動移動・削除を行う
        self.auto_update_files = data.getbool("AutoUpdateFiles", self.auto_update_files_init)

        # フォント表示例のフォーマット
        self.fontexampleformat = data.gettext("FontExampleFormat", self.fontexampleformat_init)
        self.fontexamplepixelsize = data.getint("FontExamplePixelSize", self.fontexamplepixelsize_init)

        # シナリオのインストール先(キー=ルートディレクトリ)
        e_installedpaths = data.find("InstalledPaths")
        if e_installedpaths is not None:
            for e_paths in e_installedpaths:
                assert isinstance(e_paths, cw.data.CWPyElement)
                rootdir = e_paths.getattr(".", "root", "")
                if not rootdir:
                    continue
                dirstack = []
                for e_path in e_paths:
                    if e_path.text:
                        dirstack.append(e_path.text)
                self.installed_dir[rootdir] = dirstack

        # カード編集ダイアログのブックマーク
        e_bookmarkforcardeditor = data.find("BookmarksForCardEditor")
        if e_bookmarkforcardeditor is not None:
            for e_bookmark in e_bookmarkforcardeditor:
                assert isinstance(e_bookmark, cw.data.CWPyElement)
                fpath = e_bookmark.text
                name = e_bookmark.getattr(".", "name", "")
                self.bookmarks_for_cardedit.append((fpath, name))

        # スキン
        self.skindirname = data.gettext("Skin", self.skindirname_init)

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
                if not self.local.fontsmoothing_cardname and \
                        (self.local.fonttypes["cardname"] != self.local.fonttypes_init["cardname"] or
                         self.local.fonttypes["ccardname"] != self.local.fonttypes_init["ccardname"]):
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

            if int(settings_version) < 4:
                # バージョン3→4でMIDI音量をその他の音量と独立した設定に変更
                # 以前の設定に合わせた音量に変更していおく
                self.vol_bgm_midi = self.vol_bgm * self.vol_bgm_midi

    def init_skin(self, basedata: Optional[cw.data.CWPyElementTree] = None) -> None:
        optskin = cw.OPTIONS.getstr("skin")
        cw.OPTIONS.setstr("skin", "")
        if optskin:
            # 起動オプションで差し替え
            skinpath = cw.util.join_paths("Data/Skin", optskin, "Skin.xml")
            if os.path.isfile(skinpath):
                self.skindirname = optskin

        self.skindir = cw.util.join_paths("Data/Skin", self.skindirname)
        if self.auto_update_files:
            cw.update.update_files(self.skindir, self.skindirname)
        if not os.path.isdir(self.skindir):
            self.skindirname = "Classic"
            self.skindir = cw.util.join_paths("Data/Skin", self.skindirname)

            if not os.path.isdir(self.skindir):
                # Classicが無いので手当たり次第にスキンを探す
                for path in os.listdir("Data/Skin"):
                    dpath = cw.util.join_paths("Data/Skin", path)
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
        try:
            data = self._update_skin(path)
        except Exception:
            cw.util.print_ex(file=sys.stderr)
            err = "スキン(%s)のロードに失敗しました。\n" % self.skindirname + \
                  "スキンのデータが破損している可能性があります。\n" + \
                  "手動での修復を試みるか、スキンを再導入してください。"
            dlg = wx.MessageDialog(None, err, "スキンチェックエラー", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            raise Exception()

        err = self._check_skin()
        self.skindata = data
        if err:
            dlg = wx.MessageDialog(None, err, "スキンチェックエラー", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            raise Exception()
        self.skinname = data.gettext("Property/Name", "")
        self.skintype = data.gettext("Property/Type", "")
        self.vocation120 = data.getbool("Property/CW120VocationLevel", False)
        self._classicstyletext = data.getbool("Property/ClassicStyleText", False)  # 設定バージョンアップデート用
        self.initialcash = data.getint("Property/InitialCash", basedata.getint("Property/InitialCash", 4000))
        # スキン・種族
        self.races = [cw.header.RaceHeader(e) for e in data.getfind("Races")]

        # 特性
        self.sexes = [cw.features.Sex(e) for e in data.getfind("Sexes")]
        self.sexnames = [f.name for f in self.sexes]
        self.sexsubnames = [f.subname for f in self.sexes]
        self.sexcoupons = ["＿" + f.name for f in self.sexes]
        self.periods = [cw.features.Period(e) for e in data.getfind("Periods")]
        self.periodnames = [f.name for f in self.periods]
        self.periodsubnames = [f.subname for f in self.periods]
        self.periodcoupons = ["＿" + f.name for f in self.periods]
        self.natures = [cw.features.Nature(e) for e in data.getfind("Natures")]
        self.naturenames = [f.name for f in self.natures]
        self.naturecoupons = ["＿" + f.name for f in self.natures]
        self.makings = [cw.features.Making(e) for e in data.getfind("Makings")]
        self.makingnames = [f.name for f in self.makings]
        self.makingcoupons = ["＿" + f.name for f in self.makings]

        # デバグ宿で簡易生成を行う際の能力型
        sampletypedescs = {}
        for e in basedata.getfind("SampleTypes"):
            sampletype = cw.features.SampleType(e)
            sampletypedescs[sampletype.name] = sampletype.description
        self.sampletypes = [cw.features.SampleType(e) for e in data.getfind("SampleTypes")]
        for sampletype in self.sampletypes:
            # 古いスキンでサンプルタイプの解説が無い場合があるので
            # 同一名称のサンプルタイプがSkinBaseにあるようなら解説をコピーする
            if sampletype.description == "":
                sampletype.description = sampletypedescs.get(sampletype.name, "")

        # 音声とメッセージは、選択中のスキンに
        # 定義されていなければスキンベースのもので代替する

        # 音声
        self.sound_table = {}
        for e in basedata.getfind("Sounds"):
            self.sound_table[e.getattr(".", "key", "")] = e.gettext(".", "")
        for e in data.getfind("Sounds"):
            self.sound_table[e.getattr(".", "key", "")] = e.gettext(".", "")
        # メッセージ
        self.msgs = MsgDict()
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
        local_data = data.find("Settings")
        if local_data is None:
            self.skin_local = self.local.copy()
        else:
            self.skin_local.load(local_data)

    def _update_skin(self, path: str) -> cw.data.CWPyElementTree:
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

                def update_mental(e: cw.data.CWPyElement) -> None:
                    me = e.find_exists("Mental")
                    cautious = me.getattr(".", "cautious")
                    cheerful = me.getattr(".", "cheerful")
                    me.attrib["cautious"] = cheerful
                    me.attrib["cheerful"] = cautious

                for e in data.getfind("Sexes", raiseerror=False):
                    update_mental(e)
                for e in data.getfind("Periods", raiseerror=False):
                    update_mental(e)
                for e in data.getfind("Natures", raiseerror=False):
                    update_mental(e)
                for e in data.getfind("Makings", raiseerror=False):
                    update_mental(e)
                ste = data.find("SampleTypes")
                if ste is not None:
                    def check_sampletype(ste: cw.data.CWPyElement, name: str, cautious: float, cheerful: float) -> bool:
                        # SampleTypeがSkinBaseの内容そのままかチェックする
                        return ste.gettext("Name") == name and \
                               ste.getfloat("Mental", "cautious") == cautious and \
                               ste.getfloat("Mental", "cheerful") == cheerful

                    if len(ste) != 5 or \
                            not check_sampletype(ste[0], "バランス", 0.0, 0.0) or \
                            not check_sampletype(ste[1], "ファイター", -0.5, 0.0) or \
                            not check_sampletype(ste[2], "シーフ", 0.5, 0.0) or \
                            not check_sampletype(ste[3], "プリースト", 0.0, 0.5) or \
                            not check_sampletype(ste[4], "メイジ", 0.5, -0.5):
                        # SkinBaseの内容そのままでない場合は入れ替え発生
                        for e in ste:
                            update_mental(e)
                    for e in ste:
                        me = e.find_exists("Mental")
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
                for dname in ("GameOver", "Scenario", "Title", "Yado"):
                    dpath = cw.util.join_paths(self.skindir, "Resource/Xml", dname)
                    dst = "%s_v%s" % (dpath, iver)
                    dst = cw.util.dupcheck_plus(dst, yado=False)
                    shutil.copytree(dpath, dst)

                for dname in ("GameOver", "Scenario", "Title", "Yado"):
                    dpath = cw.util.join_paths(self.skindir, "Resource/Xml", dname)
                    for fname in os.listdir(dpath):
                        ext = cw.util.splitext(fname)[1].lower()
                        if ext != ".xml":
                            continue
                        fpath = cw.util.join_paths(dpath, fname)
                        etree = cw.data.xml2etree(fpath)
                        updatemcards = False
                        for me in etree.getfind("MenuCards"):
                            events: Optional[cw.data.CWPyElement] = me.find("Events")
                            if events is None or 1 != len(events):
                                continue
                            ignum = events.gettext("Event/Ignitions/Number", "")
                            igkeycode = events.gettext("Event/Ignitions/KeyCodes", "")
                            if ignum != "1" or igkeycode != "":
                                continue
                            post = me.find_exists("Events/Event/Contents/Start/Contents/Post")
                            posttype = post.getattr(".", "type", "")
                            if posttype != "Event":
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
                            etree.write_file()

            if skinversion <= 6:
                # dataVersion=6までは標準混乱カードの効果が
                # 回避・抵抗共に-5だったが、CardWirthでは-10なので
                # 7以降それに合わせる。
                update = True

                # バックアップを作成
                iver = skinversion
                if iver % 1 == 0:
                    iver = int(iver)
                fpath = cw.util.join_paths(self.skindir, "Resource/Xml/ActionCard/-1_Confuse.xml")
                dst = "%s.v%s" % (fpath, iver)
                dst = cw.util.dupcheck_plus(dst, yado=False)
                shutil.copy2(fpath, dst)
                etree = cw.data.xml2etree(fpath)
                avoid = etree.getint("Property/Enhance", "avoid", -10)
                if avoid == -5:
                    etree.edit("Property/Enhance", "-10", "avoid")
                resist = etree.getint("Property/Enhance", "resist", -10)
                if resist == -5:
                    etree.edit("Property/Enhance", "-10", "resist")
                etree.write_file()

            if skinversion <= 8:
                # dataVersion=8までは`03_YadoInitial.xml`
                # (データ無し宿で表示されるエリア)が存在しなかったので生成。
                # タイトル画面のカード位置も調節する。
                update = True

                fpath = cw.util.join_paths(self.skindir, "Resource/Xml/Title/01_Title.xml")
                if os.path.isfile(fpath):
                    # タイトル画面のカード位置を調節
                    etree = cw.data.xml2etree(fpath)
                    e_mcards = etree.find("MenuCards")
                    if e_mcards is not None and len(e_mcards) == 2 and \
                            e_mcards.getattr(".", "spreadtype", "") == "Custom" and \
                            e_mcards[0].getint("Property/Location", "left", 0) == 231 and \
                            e_mcards[0].getint("Property/Location", "top", 0) == 156 and \
                            e_mcards[1].getint("Property/Location", "left", 0) == 316 and \
                            e_mcards[1].getint("Property/Location", "top", 0) == 156:
                        # バックアップを作成
                        iver = skinversion
                        if iver % 1 == 0:
                            iver = int(iver)
                        dst = "%s.v%s" % (fpath, iver)
                        dst = cw.util.dupcheck_plus(dst, yado=False)
                        shutil.copy2(fpath, dst)
                        etree.edit("MenuCards/MenuCard[1]/Property/Location", "233", "left")
                        etree.edit("MenuCards/MenuCard[1]/Property/Location", "150", "top")
                        etree.edit("MenuCards/MenuCard[2]/Property/Location", "318", "left")
                        etree.edit("MenuCards/MenuCard[2]/Property/Location", "150", "top")
                        etree.write_file()

                fpath1 = "Data/SkinBase/Resource/Xml/Yado/03_YadoInitial.xml"
                fpath2 = cw.util.join_paths(self.skindir, "Resource/Xml/Yado/03_YadoInitial.xml")
                if not os.path.isfile(fpath2):
                    shutil.copy2(fpath1, fpath2)
                    fpath3 = cw.util.join_paths(self.skindir, "Resource/Xml/Yado/01_Yado.xml")
                    if os.path.isfile(fpath3):
                        etree = cw.data.xml2etree(fpath2)
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
                        if e_playerselect is not None:
                            etree.edit("MenuCards/MenuCard[1]/Property/Name",
                                       e_playerselect.gettext("Property/Name"))
                            etree.edit("MenuCards/MenuCard[1]/Property/ImagePath",
                                       e_playerselect.gettext("Property/ImagePath"))
                            etree.edit("MenuCards/MenuCard[1]/Property/Description",
                                       e_playerselect.gettext("Property/Description"))
                        if e_returntitle is not None:
                            etree.edit("MenuCards/MenuCard[2]/Property/Name",
                                       e_returntitle.gettext("Property/Name"))
                            etree.edit("MenuCards/MenuCard[2]/Property/ImagePath",
                                       e_returntitle.gettext("Property/ImagePath"))
                            etree.edit("MenuCards/MenuCard[2]/Property/Description",
                                       e_returntitle.gettext("Property/Description"))
                        e_bgimgs = e3.find("BgImages")
                        if e_bgimgs is not None:
                            etree.remove(".", etree.find("BgImages"))
                            etree.insert(".", e_bgimgs, 1)
                        e_event = e3.find("Events")
                        if e_event is not None:
                            etree.remove(".", etree.find("Events"))
                            etree.append(".", e_event)
                        etree.write_file()

            if skinversion <= 9:
                fpath1 = "Data/SkinBase/Resource/Xml/Animation/Opening.xml"
                fpath2 = cw.util.join_paths(self.skindir, "Resource/Xml/Animation/Opening.xml")
                if not os.path.isfile(fpath2):
                    dpath = os.path.dirname(fpath2)
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    shutil.copy2(fpath1, fpath2)
                update = True

            if skinversion <= 11:
                # 学園バリアントに限り、BGMに`.mid`でない拡張子のファイルが含まれているので
                # エディタのスキン付属リソース拡張子自動変換を支援するため、情報を付加する
                if data.gettext("Property/Type", "") == "School":
                    fpath = cw.util.join_paths(self.skindir, "Bgm/chime.mp3")
                    if os.path.isfile(fpath):
                        e_source = data.find("Property/SourceOfMaterialsIsClassicEngine")
                        if e_source is None:
                            e_source = cw.data.make_element("SourceOfMaterialsIsClassicEngine", str(True))
                            data.find_exists("Property").append(e_source)
                            update = True

            if update:
                data.edit(".", "12", "dataVersion")
                data.write_file()

            return data

        finally:
            cw.util.release_mutex()

    def _check_skin(self) -> str:
        """
        必須リソースが欠けていないかチェックする。
        今のところ、全てのリソースをチェックしているのではなく、
        過去のアップデートで追加されたリソースのみ確認している。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Xml/Yado")
        if not os.path.isdir(dpath):
            return dpath + "が見つかりません。"
        for fname in os.listdir(dpath):
            fpath = cw.util.join_paths(dpath, fname)
            rid = int(cw.header.GetName(fpath, tagname="Id").name)
            if rid == 3:
                break
        else:
            return "スキンにデータバージョン「9」で導入された「初期拠点」エリアが存在しません。\n" + \
                   "スキンの自動アップデートに失敗した可能性があります。\n" + \
                   "手動での修復を試みるか、スキンを再導入してください。"

        fpath = cw.util.join_paths(self.skindir, "Resource/Xml/Animation/Opening.xml")
        if not os.path.isfile(fpath):
            return "スキンにデータバージョン「10」で導入されたオープニングアニメーション定義が存在しません。\n" + \
                   "スキンの自動アップデートに失敗した可能性があります。\n" + \
                   "手動での修復を試みるか、スキンを再導入してください。"

        return ""

    def set_dealspeed(self, value: int, battlevalue: int, usebattle: bool) -> None:
        self.dealspeed = value
        self.dealspeed = cw.util.numwrap(self.dealspeed, 0, 10)
        self.dealing_scales = self.create_dealingscales(self.dealspeed)

        self.dealspeed_battle = battlevalue
        self.dealspeed_battle = cw.util.numwrap(self.dealspeed_battle, 0, 10)
        self.dealing_scales_battle = self.create_dealingscales(self.dealspeed_battle)

        self.use_battlespeed = usebattle

    def get_dealspeed(self, isbattle: bool = False) -> int:
        if isbattle and self.use_battlespeed:
            return self.dealspeed_battle
        else:
            return self.dealspeed

    def create_dealingscales(self, dealspeed: int) -> List[int]:
        dealspeed = cw.util.numwrap(dealspeed, 0, 10)
        scales_len = dealspeed + 1
        dealing_scales = [
            int(math.cos(math.radians(90.0 * i / scales_len)) * 100)
            for i in range(scales_len)
            if i
        ]
        return dealing_scales

    def get_drawsetting(self) -> LocalSetting:
        if self.local.important_draw or not self.skin_local.important_draw:
            return self.local
        else:
            return self.skin_local

    def get_fontsetting(self) -> LocalSetting:
        if self.local.important_font or not self.skin_local.important_font:
            return self.local
        else:
            return self.skin_local

    def get_inusecardalpha(self, sprite: "cw.sprite.card.CWPyCard") -> int:
        alpha = 160
        if sprite.alpha is not None:
            alpha = min(alpha, sprite.alpha)
        return alpha

    @property
    def mwincolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().mwincolour

    @property
    def mwinframecolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().mwinframecolour

    @property
    def blwincolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().blwincolour

    @property
    def blwinframecolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().blwinframecolour

    @property
    def curtaincolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().curtaincolour

    @property
    def blcurtaincolour(self) -> Tuple[int, int, int, int]:
        return self.get_drawsetting().blcurtaincolour

    @property
    def fullscreenbackgroundtype(self) -> int:
        return self.get_drawsetting().fullscreenbackgroundtype

    @property
    def fullscreenbackgroundfile(self) -> str:
        return self.get_drawsetting().fullscreenbackgroundfile

    @property
    def bordering_cardname(self) -> bool:
        return self.get_fontsetting().bordering_cardname

    @property
    def decorationfont(self) -> bool:
        return self.get_fontsetting().decorationfont

    @property
    def fontsmoothing_message(self) -> bool:
        return self.get_fontsetting().fontsmoothing_message

    @property
    def fontsmoothing_cardname(self) -> bool:
        return self.get_fontsetting().fontsmoothing_cardname

    @property
    def fontsmoothing_statusbar(self) -> bool:
        return self.get_fontsetting().fontsmoothing_statusbar

    @property
    def basefont(self) -> Dict[str, str]:
        return self.get_fontsetting().basefont

    @property
    def fonttypes(self) -> Dict[str, Tuple[str, str, int, bool, bool, bool]]:
        return self.get_fontsetting().fonttypes

    @property
    def msg_exfonts(self) -> Dict[str, Tuple[str, str, int, bool, bool, bool]]:
        return self.get_fontsetting().msg_exfonts

    def is_logscrollable(self) -> bool:
        return self.messagelog_type != LOG_SINGLE

    def write(self) -> None:
        cw.xmlcreater.create_settings(self)

    @staticmethod
    def wrap_volumevalue(value: int) -> float:
        return cw.util.numwrap(value, 0, 100) / 100.0

    @staticmethod
    def wrap_colorvalue(r: int, g: int, b: int, a: int) -> Tuple[int, int, int, int]:
        r = cw.util.numwrap(r, 0, 255)
        g = cw.util.numwrap(g, 0, 255)
        b = cw.util.numwrap(b, 0, 255)
        a = cw.util.numwrap(a, 0, 255)
        return (r, g, b, a)

    def get_scedir(self, skintype: Optional[str] = None) -> str:
        if skintype is None:
            skintype = self.skintype

        scedir = "Scenario"
        # 設定に応じて初期位置を変更する
        if self.selectscenariofromtype:
            for skintype2, folder in self.folderoftype:
                if skintype2 == skintype:
                    folder = cw.util.get_linktarget(folder)
                    if os.path.isdir(folder):
                        scedir = folder
                    break
        return scedir

    def insert_yadoorder(self, yadodirname: str) -> None:
        seq = []
        for dname, order in self.yado_order.items():
            seq.append((order, dname))
        self.yado_order.clear()
        self.yado_order[yadodirname] = 0
        o = 1
        for _, dname in sorted(seq):
            if dname == yadodirname:
                continue
            self.yado_order[dname] = o
            o += 1
        pass


class MsgDict(object):
    def __init__(self) -> None:
        """
        メッセージテーブル(dict[ID, Msg])。
        存在しないメッセージIDが指定された時はエラーダイアログを表示する。
        """
        self._d: Dict[str, str] = {}
        self._error_keys: Set[str] = set()

    def __setitem__(self, key: str, msg: str) -> None:
        self._d[key] = msg

    def __getitem__(self, key: str) -> str:
        if key not in self._d:
            if key not in self._error_keys:
                def func() -> None:
                    if cw.cwpy.frame:
                        s = "メッセージID[%s]に該当するメッセージがありません。\n"\
                            "デイリービルド版でこのエラーが発生した場合は、"\
                            "「Data/SkinBase」以下のリソースが最新版になっていない"\
                            "可能性があります。" % (key)
                        sys.stderr.write("Message [%s] is not found." % key)
                        dlg = cw.dialog.message.ErrorMessage(None, s)
                        dlg.ShowModal()
                        dlg.Destroy()

                cw.cwpy.frame.exec_func(func)
                self._error_keys.add(key)
            return "*ERROR*"
        return self._d[key]

    def get(self, key: str, defvalue: str) -> str:
        return self._d.get(key, defvalue)


class Resource(object):
    ext_img: int
    fonts: "ResourceTable[str, cw.imageretouch.Font]"
    msg_exfonts: "ResourceTable[str, cw.imageretouch.Font]"
    facenames_lower: Set[str]
    fontnames_init: Dict[str, str]
    facenames_init: Dict[str, str]
    cardbgs: "ResourceTable[str, pygame.Surface]"
    wxcardbgs: "ResourceTable[str, wx.Bitmap]"
    statuses: "ResourceTable[str, pygame.Surface]"
    stones: "ResourceTable[str, pygame.Surface]"
    wxstones: "ResourceTable[str, wx.Bitmap]"
    cardnamecolorhints: "ResourceTable[str, int]"
    dialogs: "ResourceTable[str, wx.Bitmap]"
    pygamedialogs: "ResourceTable[str, pygame.Surface]"
    buttons: "ResourceTable[str, wx.Bitmap]"
    debugs: "ResourceTable[str, wx.Bitmap]"
    pygamedebugs: "ResourceTable[str, pygame.Surface]"
    cursors: "ResourceTable[str, wx.Cursor]"
    specialchars: "ResourceTable[str, Tuple[pygame.Surface, bool]]"
    specialchars_is_changed: bool

    def __init__(self, setting: Optional[Setting]) -> None:
        if setting:
            self.init(setting)
        else:
            self._init = False

    def __bool__(self) -> bool:
        return self._init

    def init(self, setting: Setting) -> None:
        self._init = True
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
        self.buttons = ResourceTable[str, wx.Bitmap]("Button", {}, empty_wxbmp)
        # カード背景画像(辞書)
        self.cardbgs = self.get_cardbgs(cw.util.load_image)
        self.cardnamecolorhints = self.get_cardnamecolorhints(self.cardbgs)
        # wxダイアログで使う画像(辞書)
        self.pygamedialogs = self.get_dialogs(cw.util.load_image)
        # wx版。wxスレッドから初期化
        self.dialogs = ResourceTable[str, wx.Bitmap]("Dialog", {}, empty_wxbmp)
        # デバッガで使う画像(辞書)
        self.pygamedebugs = self.get_debugs(cw.util.load_image, cw.s)
        # wx版。wxスレッドから初期化
        self.debugs = ResourceTable[str, wx.Bitmap]("Debug", {}, empty_wxbmp)
        # ダイアログで使うカーソル(辞書)
        # wxスレッドから初期化
        self.cursors = ResourceTable[str, wx.Cursor]("Cursor", {}, empty_wxbmp)
        # 特殊文字の画像(辞書)
        self.specialchars_is_changed = False
        self.specialchars = self.get_specialchars()
        # プレイヤカードのステータス画像(辞書)
        self.statuses = self.get_statuses(cw.util.load_image)
        # 適性値・使用回数値画像(辞書)
        self.stones = self.get_stones()
        # wx版。wxスレッドから初期化
        self.wxstones = ResourceTable[str, wx.Bitmap]("Stone", {}, empty_wxbmp)
        # 使用フォント(辞書)。スプライトを作成するたびにフォントインスタンスを
        # 新規作成すると重いのであらかじめ用意しておく(wxスレッドから初期化)
        self.fonts, self.msg_exfonts = self.create_fonts()
        # StatusBarで使用するボタンイメージ
        self._statusbtnbmp0: Dict[int, pygame.Surface] = {}
        self._statusbtnbmp1: Dict[int, pygame.Surface] = {}
        self._statusbtnbmp2: Dict[int, pygame.Surface] = {}

        self.actioncards: Dict[int, cw.header.CardHeader] = {}
        self.backpackcards: Dict[str, cw.header.CardHeader] = {}

        self.ignorecase_table = {}

        cw.cwpy.frame.exec_func(self.init_wxresources)
        if os.path.normcase("A") != "a":
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

    def get_filepath(self, fpath: str) -> str:
        if cw.fsync.is_waiting(fpath):
            cw.fsync.sync()
        if not fpath or cw.binary.image.path_is_code(fpath) or os.path.isfile(fpath):
            return fpath

        if self.ignorecase_table or (cw.cwpy.sdata and cw.cwpy.sdata.ignorecase_table):
            lpath = fpath.lower()
            if lpath in self.ignorecase_table:
                fpath = self.ignorecase_table.get(lpath, fpath)
            elif cw.cwpy.sdata and cw.cwpy.sdata.ignorecase_table:
                fpath = cw.cwpy.sdata.ignorecase_table.get(lpath, fpath)

        return fpath

    def dispose(self) -> None:
        for key in self.fonts.keys():
            if self.fonts.is_loaded(key):
                font = self.fonts[key]
                if isinstance(font, cw.imageretouch.Font):
                    font.dispose()
        self._init = False

    @property
    def cardnamecolorborder(self) -> int:
        if cw.cwpy.setting.bordering_cardname:
            return 92
        else:
            return 116

    def update_winscale(self) -> None:
        self.init_wxresources()

    def init_sounds(self) -> None:
        setting = self.setting()
        assert setting
        # その他のスキン付属効果音(辞書)
        self.skinsounds = self.get_skinsounds()
        # システム効果音(辞書)
        self.sounds = self.get_sounds(setting, self.skinsounds)

    def init_wxresources(self) -> None:
        """wx側のリソースを初期化。"""
        # wxダイアログのボタン画像(辞書)
        self.buttons = self.get_buttons()
        # wxダイアログで使う画像(辞書)
        self.dialogs = self.get_dialogs(cw.util.load_wxbmp)
        # デバッガで使う画像(辞書)
        self.debugs = self.get_debugs(cw.util.load_wxbmp, cw.ppis)
        self.debugs_wx = self.get_debugs(cw.util.load_wxbmp, cw.wins)

        def ss(num: cw.Scalable) -> cw.Scalable:
            return num
        self.debugs_noscale = self.get_debugs(cw.util.load_wxbmp, ss, can_loaded_scaledimage=False)
        # ダイアログで使うカーソル(辞書)
        self.cursors = self.get_cursors()
        # 適性値・使用回数値画像(辞書)
        self.wxstones = self.get_wxstones()
        # プレイヤカードのステータス画像(辞書)
        self.wxstatuses = self.get_statuses(cw.util.load_wxbmp)
        # カード背景画像(辞書)
        self.wxcardbgs = self.get_cardbgs(cw.util.load_wxbmp)

    def init_debugicon(self) -> None:
        """エディタ情報変更によりデバッグアイコンを再読込する"""

        def func() -> None:
            self.pygamedebugs = self.get_debugs(cw.util.load_image, cw.s)

        cw.cwpy.exec_func(func)
        self.debugs = self.get_debugs(cw.util.load_wxbmp, cw.ppis)
        self.debugs_wx = self.get_debugs(cw.util.load_wxbmp, cw.wins)

        def ss(num: cw.Scalable) -> cw.Scalable:
            return num
        self.debugs_noscale = self.get_debugs(cw.util.load_wxbmp, ss, can_loaded_scaledimage=False)

    def get_fontpaths(self) -> Dict[str, str]:
        """
        フォントパス(辞書)
        """
        fontdir = "Data/Font"
        fontdir_skin = cw.util.join_paths(self.skindir, "Resource/Font")
        fnames = (("gothic.ttf", "ＭＳ ゴシック"), ("uigothic.ttf", "MS UI Gothic"),
                  ("mincho.ttf", "ＭＳ 明朝"), ("pgothic.ttf", "ＭＳ Ｐゴシック"),
                  ("pmincho.ttf", "ＭＳ Ｐ明朝"))
        d = {}
        self.facenames = set(wx.FontEnumerator().GetFacenames())
        self.facenames_lower = set([name.lower() for name in self.facenames])

        for fname, alt in fnames:
            path = cw.util.join_paths(fontdir_skin, fname)

            if not os.path.isfile(path):
                path = cw.util.join_paths(fontdir, fname)

                if not os.path.isfile(path):
                    if alt in self.facenames:
                        continue
                    else:
                        # IPAフォントも代替フォントも存在しない場合はエラー
                        raise NoFontError(fname + " not found.")

            d[cw.util.splitext(fname)[0]] = path

        return d

    @staticmethod
    def get_fontpaths_s(fontdir: str, facenames: Set[str]) -> Dict[str, str]:
        d = {}
        fnames = (("gothic.ttf", "ＭＳ ゴシック"), ("uigothic.ttf", "MS UI Gothic"),
                  ("mincho.ttf", "ＭＳ 明朝"), ("pgothic.ttf", "ＭＳ Ｐゴシック"),
                  ("pmincho.ttf", "ＭＳ Ｐ明朝"))
        for fname, alt in fnames:
            path = cw.util.join_paths(fontdir, fname)
            if not os.path.isfile(path):
                if alt in facenames:
                    continue
                else:
                    # IPAフォントも代替フォントも存在しない場合はエラー
                    raise NoFontError(fname + " not found.")

            d[cw.util.splitext(fname)[0]] = path

        return d

    @staticmethod
    def install_defaultfonts(fontpaths: Dict[str, str], facenames: Set[str], d: Dict[str, str]) -> None:
        if sys.platform == "win32":
            winplatform = sys.getwindowsversion()[3]

            for name, path in fontpaths.items():
                fontname = cw.util.get_truetypefontname(path)
                if fontname in facenames or \
                        fontname == "IPAUIGothic" and ("IPA UIゴシック" in facenames) or \
                        fontname == "IPAGothic" and ("IPAゴシック" in facenames) or \
                        fontname == "IPAPGothic" and ("IPA Pゴシック" in facenames) or \
                        fontname == "IPAMincho" and ("IPA明朝" in facenames) or \
                        fontname == "IPAPMincho" and ("IPA P明朝" in facenames):
                    d[name] = fontname
                    continue

                def func() -> None:
                    import ctypes
                    gdi32 = ctypes.WinDLL("gdi32")
                    if winplatform == 2:
                        import ctypes.wintypes
                        gdi32.AddFontResourceExW.argtypes = (ctypes.c_wchar_p, ctypes.wintypes.DWORD, ctypes.c_void_p)
                        gdi32.AddFontResourceExW(path, 0x10, 0)
                    else:
                        gdi32.AddFontResourceW.argtypes = (ctypes.c_wchar_p,)
                        gdi32.AddFontResourceW(path)
                        user32 = ctypes.windll.user32
                        HWND_BROADCAST = 0xFFFF
                        WM_FONTCHANGE = 0x001D
                        user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)

                thr = threading.Thread(target=func)
                thr.start()

                if fontname:
                    if d is not None:
                        d[name] = fontname
                else:
                    raise ValueError("Failed to get facename from %s" % name)

    def set_systemfonttable(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        システムフォントテーブルの設定を行う。
        設定したフォント名をフォントファイル名がkeyの辞書で返す。
        """
        setting = self.setting()
        assert setting

        d: Dict[str, str] = {}

        if sys.platform == "win32":
            Resource.install_defaultfonts(self.fontpaths, self.facenames, d)
            self.facenames = set(wx.FontEnumerator().GetFacenames())
        else:
            d["gothic"] = "IPAゴシック"
            d["uigothic"] = "IPA UIゴシック"
            d["mincho"] = "IPA明朝"
            d["pmincho"] = "IPA P明朝"
            d["pgothic"] = "IPA Pゴシック"

            for value in d.values():
                if value not in self.facenames:
                    raise ValueError("IPA font not found: " + value)

        init = d.copy()

        # 設定に応じた差し替え
        for basetype in d.keys():
            font = setting.local.basefont[basetype]
            if font:
                d[basetype] = font

        return d, init

    def clear_systemfonttable(self) -> None:
        if sys.platform == "win32" and not sys.getwindowsversion()[3] == 2:
            gdi32 = ctypes.WinDLL("gdi32")
            gdi32.RemoveFontResourceA.argtypes = (ctypes.c_wchar_p,)

            for path in self.fontpaths.values():
                gdi32.RemoveFontResourceA(path)

            user32 = ctypes.windll.user32
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            user32.SendMessageA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)

    def get_fontfromtype(self, name: str, fontinfo: Optional[Tuple[str, str, int, bool, bool, bool]] = None)\
            -> Tuple[str, int, bool, bool, bool]:
        """フォントタイプ名から抽象フォント名を取得する。"""
        setting = self.setting()
        assert setting
        if fontinfo is None:
            fontinfo = setting.fonttypes.get(name, (name, "", -1, False, False, False))
        assert fontinfo
        basename, fontname, pixels, bold, bold_upscr, italic = fontinfo
        if basename:
            fontname = setting.basefont[basename]
            if not fontname:
                fontname = self.fontnames.get(basename, "")
        return fontname, pixels, bold, bold_upscr, italic

    def get_wxfont(self, name: str = "uigothic", size: Optional[int] = None, pixelsize: Optional[int] = None,
                   family: int = wx.DEFAULT, style: int = wx.NORMAL, weight: int = wx.BOLD,
                   encoding: int = wx.FONTENCODING_SYSTEM, adjustsize: bool = False, adjustsizewx3: bool = True,
                   pointsize: Optional[int] = None) -> wx.Font:
        if size is None and pixelsize is None:
            pixelsize = cw.wins(14)

        fontname, _pixels, bold, bold_upscr, italic = self.get_fontfromtype(name)

        if cw.UP_SCR <= 1.0:
            if bold is not None:
                weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
        else:
            if bold_upscr is not None:
                weight = wx.FONTWEIGHT_BOLD if bold_upscr else wx.FONTWEIGHT_NORMAL
        if italic is not None:
            style = wx.ITALIC if italic else wx.FONTSTYLE_NORMAL

        if pointsize is None:
            # FIXME: ピクセルサイズで指定しないと96DPIでない時にゲーム画面が
            #        おかしくなるので暫定的に96DPI相当のサイズに強制変換
            if not pixelsize:
                assert size is not None
                pixelsize = int((1.0 / 72 * 96) * size + 0.5)
            elif adjustsizewx3:
                # FIXME: wxPython 3.0.1.1でフォントが1ピクセル大きくなってしまった
                pixelsize -= 1

            # BUG: フォントサイズとテキストによっては
            #      ツリーアイテムの後方が欠ける事がある
            if (name in ("tree", "slider") or adjustsize) and 15 < pixelsize and pixelsize % 2 == 1:
                pixelsize += 1

            wxfont = wx.Font(wx.Size(0, pixelsize), family, style, weight, 0, fontname, encoding)
        else:
            wxfont = wx.Font(pointsize, family, style, weight, 0, fontname, encoding)

        return wxfont

    def create_font(self, ftype: str, basetype: str, fontname: str, size_noscale: int, defbold: bool,
                    defbold_upscr: bool, defitalic: bool, pixelsadd: int = 0, nobold: bool = False,
                    fontinfo: Optional[Tuple[str, str, int, bool, bool, bool]] = None) -> "cw.imageretouch.Font":
        fontname, pixels_noscale, bold, bold_upscr, italic = self.get_fontfromtype(ftype, fontinfo)
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

        if cw.UP_SCR > 1.0:
            bold = bold_upscr

        return cw.imageretouch.Font(fontname, -cw.s(pixels_noscale), bold=bold, italic=italic)

    def create_exfont(self, ftype: str, fontinfo: Tuple[str, str, int, bool, bool, bool],
                      basetable: Dict[str, "cw.imageretouch.Font"], nobold: bool) -> "cw.imageretouch.Font":
        if fontinfo[0] == "inherit":
            return basetable[ftype]
        else:
            t = fontinfo
            return self.create_font("", t[0], t[1], t[2], t[3], t[4], t[5], nobold=nobold, fontinfo=fontinfo)

    def create_fonts(self) -> Tuple["ResourceTable[str, cw.imageretouch.Font]",
                                    "ResourceTable[str, cw.imageretouch.Font]"]:
        """ゲーム内で頻繁に使用するpygame.Fontはここで設定する。"""
        # 使用フォント(辞書)
        setting = self.setting()
        assert setting

        def defvalue() -> NoReturn:
            raise Exception()
        fonts = ResourceTable[str, cw.imageretouch.Font]("Font", {}, defvalue)
        msg_exfonts = ResourceTable[str, cw.imageretouch.Font]("SyntheticFontsForMessage", {}, defvalue)
        # 所持カードの使用回数描画用
        t = setting.fonttypes["uselimit"]
        fonts.set("card_uselimit", self.create_font, "uselimit", t[0], t[1], t[2], t[3], t[4], t[5])
        # メニューカードの名前描画用
        t = setting.fonttypes["cardname"]
        fonts.set("mcard_name", self.create_font, "cardname", t[0], t[1], t[2], t[3], t[4], t[5])
        # プレイヤカードの名前描画用
        t = setting.fonttypes["ccardname"]
        fonts.set("pcard_name", self.create_font, "ccardname", t[0], t[1], t[2], t[3], t[4], t[5])
        # プレイヤカードのレベル描画用
        t = setting.fonttypes["level"]
        fonts.set("pcard_level", self.create_font, "level", t[0], t[1], t[2], t[3], t[4], t[5])
        # メッセージウィンドウのテキスト描画用
        t = setting.fonttypes["message"]
        fonts.set("message", self.create_font, "message", t[0], t[1], t[2], t[3], t[4], t[5], nobold=True)
        # メッセージ用混植フォント
        for extype in ("fw_symbol", "fw_number", "fw_latin", "hiragana", "katakana", "hw_katakana",
                       "greek_and_cyrillic", "jis_kanji_1", "jis_kanji_2", "etc_kanji", "symbol",
                       "number", "latin"):
            t = setting.msg_exfonts[extype]
            msg_exfonts.set(extype, self.create_exfont, "message", fontinfo=t, basetable=fonts, nobold=True)
        # メッセージウィンドウの選択肢描画用
        t = setting.fonttypes["selectionbar"]
        fonts.set("selectionbar", self.create_font, "selectionbar", t[0], t[1], t[2], t[3], t[4], t[5])
        # 貼紙のシナリオ名描画用
        t = setting.fonttypes["scenario"]
        fonts.set("scenario", self.create_font, "scenario", t[0], t[1], 21-1, t[3], t[4], t[5])
        # 貼紙の本文描画用
        t = setting.fonttypes["dlglist"]
        fonts.set("scenariodesc", self.create_font, "dlglist", t[0], t[1], 14-1, t[3], t[4], t[5])
        # 貼紙の対象レベル描画用
        t = setting.fonttypes["targetlevel"]
        fonts.set("targetlevel", self.create_font, "targetlevel", t[0], t[1], 16-1, t[3], t[4], t[5])
        # メッセージログのページ表示描画用
        t = setting.fonttypes["logpage"]
        fonts.set("backlog_page", self.create_font, "logpage", t[0], t[1], t[2], t[3], t[4], t[5])
        # カード価格表示用
        t = setting.fonttypes["price"]
        fonts.set("price", self.create_font, "price", t[0], t[1], t[2], t[3], t[4], t[5])
        # カード枚数描画用
        t = setting.fonttypes["numcards"]
        fonts.set("numcards", self.create_font, "numcards", t[0], t[1], t[2], t[3], t[4], t[5])
        fonts.set("numcards_personal", self.create_font, "numcards", t[0], t[1], t[2], t[3], t[4], t[5],
                  pixelsadd=min(0, -min(t[2]//2, t[2]-16)))
        # ステータスバーパネル描画用
        t = setting.fonttypes["sbarpanel"]
        fonts.set("sbarpanel", self.create_font, "sbarpanel", t[0], t[1], t[2], t[3], t[4], t[5])
        # 進行状況・音量バー描画用
        t = setting.fonttypes["sbarprogress"]
        fonts.set("sbarprogress", self.create_font, "sbarprogress", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン描画用
        t = setting.fonttypes["sbarbtn"]
        fonts.set("sbarbtn", self.create_font, "sbarbtn", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン解説描画用
        t = setting.fonttypes["sbardesc"]
        fonts.set("sbardesc", self.create_font, "sbardesc", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータスバーボタン解説の表題描画用
        t = setting.fonttypes["sbardesctitle"]
        fonts.set("sbardesctitle", self.create_font, "sbardesctitle", t[0], t[1], t[2], t[3], t[4], t[5])
        # ステータス画像の召喚回数描画用
        t = setting.fonttypes["statusnum"]
        fonts.set("statusimg1", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5])
        t = setting.fonttypes["statusnum"]
        fonts.set("statusimg2", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5], pixelsadd=-2)
        fonts.set("statusimg3", self.create_font, "statusnum", t[0], t[1], t[2], t[3], t[4], t[5], pixelsadd=-4)
        t = setting.fonttypes["screenshot"]
        fonts.set("screenshot", self.create_font, "screenshot", t[0], t[1], t[2], t[3], t[4], t[5])
        return fonts, msg_exfonts

    def create_wxbutton(self, parent: wx.Panel, cid: int, size: Tuple[int, int], name: Optional[str] = None,
                        bmp: Optional[wx.Bitmap] = None, chain: bool = False) -> Union[wx.BitmapButton, wx.Button]:
        if bmp:
            button = wx.BitmapButton(parent, cid, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)
            if name:
                button.SetToolTip(name)
        else:
            button = wx.Button(parent, cid, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("button"))

        if chain:
            # ボタンを押し続けた時に一定間隔で押下イベントを発生させる
            timer = wx.Timer(button)
            timer.running = False

            def starttimer(event: wx.TimerEvent) -> None:
                if not timer.running:
                    timer.running = True
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
                    button.ProcessEvent(btnevent)

                timer.Start(cw.cwpy.setting.move_repeat, wx.TIMER_ONE_SHOT)

            def timerfunc(event: wx.TimerEvent) -> None:
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
                button.ProcessEvent(btnevent)
                starttimer(event)

            def stoptimer(event: wx.MouseEvent) -> None:
                timer.Stop()
                event.Skip()
                timer.running = False

            button.Bind(wx.EVT_TIMER, timerfunc)
            button.Bind(wx.EVT_LEFT_DOWN, starttimer)
            button.Bind(wx.EVT_LEFT_UP, stoptimer)
            button.Bind(wx.EVT_LEAVE_WINDOW, stoptimer)

        return button

    def create_wxbutton_dbg(self, parent: wx.Panel, cid: int, size: Tuple[int, int], name: Optional[str] = None,
                            bmp: Optional[wx.Bitmap] = None) -> Union[wx.BitmapButton, wx.Button]:
        if bmp:
            button = wx.BitmapButton(parent, cid, bmp)
            button.SetMinSize(size)
            bmp = cw.imageretouch.to_disabledimage(bmp)
            button.SetBitmapDisabled(bmp)
            if name:
                button.SetToolTip(name)
        else:
            button = wx.Button(parent, cid, name, size=size)
            button.SetMinSize(size)
            button.SetFont(self.get_wxfont("button", pointsize=9))

        return button

    @staticmethod
    def create_cornerimg(rgb: Tuple[int, int, int])\
            -> Tuple[pygame.Surface, pygame.Surface, pygame.Surface, pygame.Surface]:
        r, g, b = rgb
        linedata = struct.pack(
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB",
            r, g, b, 255, r, g, b, 255, r, g, b, 255, r, g, b, 255, r, g, b, 255, r, g, b, 255,
            r, g, b, 255, r, g, b, 255, r, g, b, 224, r, g, b, 128, r, g, b, 68, r, g, b, 40,
            r, g, b, 255, r, g, b, 224, r, g, b, 68, r, g, b, 0, r, g, b, 0, r, g, b, 0,
            r, g, b, 255, r, g, b, 128, r, g, b, 0, r, g, b, 0, r, g, b, 0, r, g, b, 0,
            r, g, b, 255, r, g, b, 68, r, g, b, 0, r, g, b, 0, r, g, b, 0, r, g, b, 0,
            r, g, b, 255, r, g, b, 40, r, g, b, 0, r, g, b, 0, r, g, b, 0, r, g, b, 0
        )

        topleft = pygame.image.fromstring(linedata, (6, 6), "RGBA")
        topright = pygame.transform.flip(topleft, True, False)
        bottomleft = pygame.transform.flip(topleft, False, True)
        bottomright = pygame.transform.flip(topleft, True, True)
        return topleft, topright, bottomleft, bottomright

    @staticmethod
    def draw_frame(bmp: pygame.Surface, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        topleft, topright, bottomleft, bottomright = Resource.create_cornerimg(color)
        pygame.draw.rect(bmp, color, rect, 1)
        x, y, w, h = rect
        bmp.blit(topleft, (x, y))
        bmp.blit(topright, (x + w - 6, y))
        bmp.blit(bottomleft, (x, y + h - 6))
        bmp.blit(bottomright, (x + w - 6, y + h - 6))
        Resource.draw_corneroutimg(bmp, rect)

    @staticmethod
    def draw_corneroutimg(bmp: pygame.Surface, rect: Optional[pygame.Rect] = None, outframe: int = 0) -> None:
        outdata = struct.pack(
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB"
            "BBBB BBBB BBBB BBBB BBBB BBBB",
            0, 0, 0, 255, 0, 0, 0, 255, 0, 0, 0, 188, 0, 0, 0, 128, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 255, 0, 0, 0, 128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 188, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 128, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        )
        topleft = pygame.image.fromstring(outdata, (6, 6), "RGBA")
        topright = pygame.transform.flip(topleft, True, False)
        bottomleft = pygame.transform.flip(topleft, False, True)
        bottomright = pygame.transform.flip(topleft, True, True)

        if not rect:
            rect = bmp.get_rect()
        x, y, w, h = rect
        o = outframe
        bmp.blit(topleft, (x + o, y + o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(topright, (x + w - 6 - o, y + o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(bottomleft, (x + o, y + h - 6 - o), special_flags=pygame.locals.BLEND_RGBA_SUB)
        bmp.blit(bottomright, (x + w - 6 - o, y + h - 6 - o), special_flags=pygame.locals.BLEND_RGBA_SUB)

    def _create_statusbtnbmp(self, w: int, h: int, flags: int = 0) -> pygame.Surface:
        """ボタン風の画像を生成する。"""
        topleft, topright, bottomleft, bottomright = Resource.create_cornerimg((208, 208, 208))

        def subtract_corner(value: int) -> None:
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
            mid = h // 2
            for y in range(0, mid + 1, 1):
                bmp.fill((r1 - y // 4, g1 - y // 4, b1 - y // 4), pygame.Rect(0, mid - y, w, 1))
                bmp.fill((r2 - y, g2 - y, b2 - y), pygame.Rect(0, mid + y, w, 1))

        # 枠の部分。四隅には角丸の画像を描写する
        if flags & SB_PRESSED:
            # 押下済みの画像であれば上と左の縁を暗くする
            if not (flags & SB_CURRENT):
                subtract_corner(8)
                color = (200, 200, 200)
            else:
                color = (208, 208, 208)
            pygame.draw.line(bmp, color, (2, 3), (w - 4, 3))
            subtract_corner(8)
            bmp.blit(topleft, (2, 3))
            bmp.blit(topright, (w - 6 - 1, 3))

            if not (flags & SB_CURRENT):
                color = (192, 192, 192)
            else:
                color = (200, 200, 200)
            pygame.draw.rect(bmp, color, (2, 2, w - 3, h - 3), 1)
            bmp.blit(topleft, (2, 2))
            bmp.blit(topright, (w - 6 - 1, 2))
            bmp.blit(bottomleft, (2, h - 6 - 1))
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
            color = (color[0], max(0, color[1] - 128), max(0, color[2] - 128))

            emcolor = (96, 0, 0, 0)
            topleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            topright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            bottomleft.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            bottomright.fill(emcolor, special_flags=pygame.locals.BLEND_RGBA_ADD)
            color = (min(255, color[0] + 96), color[1], color[2])

        if not (flags & SB_CURRENT) and not (flags & SB_DISABLE):
            opacity = 92
            lightcolor = (0, 0, 0, opacity)
            topleft.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            topright.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomleft.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            bottomright.fill(lightcolor, special_flags=pygame.locals.BLEND_RGBA_SUB)
            linecolor: Union[Tuple[int, int, int, int],
                             Tuple[int, int, int]] = (color[0], color[1], color[2], 255 - opacity)
        else:
            linecolor = color

        pygame.draw.rect(bmp, linecolor, (1, 1, w - 2, h - 2), 1)
        bmp.blit(topleft, (1, 1))
        bmp.blit(topright, (w - 6 - 1, 1))
        bmp.blit(bottomleft, (1, h - 6 - 1))
        bmp.blit(bottomright, (w - 6 - 1, h - 6 - 1))

        if not (flags & SB_PRESSED):
            # ハイライトをつける
            linedata = struct.pack(
                "BBBB BBBB BBBB BBBB BBBB BBBB"
                "BBBB BBBB BBBB BBBB BBBB BBBB"
                "BBBB BBBB BBBB BBBB BBBB BBBB"
                "BBBB BBBB BBBB BBBB BBBB BBBB"
                "BBBB BBBB BBBB BBBB BBBB BBBB"
                "BBBB BBBB BBBB BBBB BBBB BBBB",
                r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 128, r1, g1, b1, 255, r1, g1, b1, 255, r1, g1, b1, 255,
                r1, g1, b1, 0, r1, g1, b1, 196, r1, g1, b1, 224, r1, g1, b1, 128, r1, g1, b1, 68, r1, g1, b1, 40,
                r1, g1, b1, 128, r1, g1, b1, 224, r1, g1, b1, 68, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0,
                r1, g1, b1, 255, r1, g1, b1, 128, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0,
                r1, g1, b1, 255, r1, g1, b1, 68, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0,
                r1, g1, b1, 255, r1, g1, b1, 40, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0, r1, g1, b1, 0
            )
            hl_topleft = pygame.image.fromstring(linedata, (6, 6), "RGBA")
            hl_topright = pygame.transform.flip(hl_topleft, True, False)
            hl_bottomleft = pygame.transform.flip(hl_topleft, False, True)
            hl_bottomright = pygame.transform.flip(hl_topleft, True, True)
            color = (r1, g1, b1)
            pygame.draw.line(bmp, color, (2 + 6, 2), (w - 6 - 3, 2))
            pygame.draw.line(bmp, color, (2 + 6, h - 3), (w - 6 - 3, h - 3))
            pygame.draw.line(bmp, color, (2, 2 + 6), (2, h - 6 - 3))
            pygame.draw.line(bmp, color, (w - 3, 2 + 6), (w - 3, h - 6 - 3))
            bmp.blit(hl_topleft, (2, 2))
            bmp.blit(hl_topright, (w - 6 - 2, 2))
            bmp.blit(hl_bottomleft, (2, h - 6 - 2))
            bmp.blit(hl_bottomright, (w - 6 - 2, h - 6 - 2))

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

    def get_statusbtnbmp(self, sizetype: int, flags: int = 0) -> Optional[pygame.Surface]:
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

    def get_resources(self, func: Callable[..., _ResType], dpath1: str, dpath2: str, ext: int,
                      mask: Optional[bool] = None,
                      ss: Optional[Callable[["cw.Scalable"], "cw.Scalable"]] = None,
                      noresize: Iterable[str] = (), nodbg: bool = False,
                      emptyfunc: Optional[Callable[[], _ResType]] = None, editor_res: Optional[str] = None,
                      warning: bool = True, can_loaded_scaledimage: bool = True) -> "ResourceTable[str, _ResType]":
        """
        各種リソースデータを辞書で返す。
        ファイル名から拡張子を除いたのがkey。
        """

        def nokeyfunc(key: str) -> Union[pygame.Surface, wx.Bitmap]:
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
                    def errfunc(dname: str, key: str) -> None:
                        if cw.cwpy.frame:
                            s = "リソース [%s/%s] が見つかりません。\n" \
                                "デイリービルド版でこのエラーが発生した場合は、" \
                                "「Data/SkinBase」以下のリソースが最新版になっていない" \
                                "可能性があります。" % (dname, key)
                            sys.stderr.write("Resource [%s/%s] is not found." % (dname, key))
                            dlg = cw.dialog.message.ErrorMessage(None, s)
                            dlg.ShowModal()
                            dlg.Destroy()

                    cw.cwpy.frame.exec_func(errfunc, os.path.basename(dpath1), key)
                assert emptyfunc
                return emptyfunc()

            if mask is None:
                res = func(fpath)
            else:
                if ss == cw.ppis and func == cw.util.load_wxbmp:
                    res = func(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=cw.dpi_level)
                else:
                    res = func(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

            if not noscale:
                if not dbg and ss and key not in noresize:
                    assert isinstance(res, (pygame.Surface, wx.Bitmap))
                    img = ss(res)
                    assert isinstance(img, type(res))
                    res = img
                elif dbg and ss:
                    assert isinstance(res, (pygame.Surface, wx.Bitmap))
                    img = cw.ppis(res)
                    assert isinstance(img, type(res))
                    res = img

            return res

        d = ResourceTable(dpath1, {}, emptyfunc, nokeyfunc=nokeyfunc)
        return d

    def get_sounds(self, setting: Setting, skinsounds: "ResourceTable[str, cw.util.SoundInterface]")\
            -> "ResourceTable[str, cw.util.SoundInterface]":
        """
        システム効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        d = ResourceTable[str, cw.util.SoundInterface]("SystemSound", {}, empty_sound)
        key: str
        sound: str
        for key, sound in list(setting.sound_table.items()):
            if sound in skinsounds:
                def func(sound: str) -> None:
                    d.set(key, lambda: skinsounds[sound])
                func(sound)
            else:
                d.set(key, empty_sound)
        return d

    def get_skinsounds(self) -> "ResourceTable[str, cw.util.SoundInterface]":
        """
        スキン付属の効果音を読み込んで、
        pygameのsoundインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Sound")
        d = self.get_resources(cw.util.load_sound, "Data/SkinBase/Sound", dpath, self.ext_snd, emptyfunc=empty_sound,
                               warning=False)
        dpath = cw.util.join_paths(self.skindir, "BgmAndSound")
        d2 = self.get_resources(cw.util.load_sound, "Data/SkinBase/BgmAndSound", dpath, self.ext_snd,
                                emptyfunc=empty_sound, warning=False)
        d.merge(d2)

        return d

    def get_msgs(self, setting: Setting) -> MsgDict:
        """
        システムメッセージを辞書で返す。
        """
        return setting.msgs

    def get_buttons(self) -> "ResourceTable[str, pygame.Surface]":
        """
        ダイアログのボタン画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Button")
        return self.get_resources(cw.util.load_wxbmp, "Data/SkinBase/Resource/Image/Button", dpath, self.ext_img, True,
                                  cw.wins, emptyfunc=empty_wxbmp)

    def get_cursors(self) -> "ResourceTable[str, wx.Cursor]":
        """
        ダイアログで使用されるカーソルを読み込んで、
        wxCursorのインスタンスの辞書で返す。
        """

        def get_cursor(name: str) -> wx.Cursor:
            fname = name + ".cur"
            dpaths = ("Data/SkinBase/Resource/Image/Cursor",
                      cw.util.join_paths(self.skindir, "Resource/Image/Cursor"))
            for dpath in dpaths:
                fpath = cw.util.join_paths(dpath, fname)
                if os.path.isfile(fpath):
                    return wx.Cursor(fpath, wx.BITMAP_TYPE_CUR)
            if name == "CURSOR_BACK":
                return wx.Cursor(wx.CURSOR_POINT_LEFT)
            elif name == "CURSOR_FORE":
                return wx.Cursor(wx.CURSOR_POINT_RIGHT)
            elif name == "CURSOR_FINGER":
                return wx.Cursor(wx.CURSOR_HAND)
            elif name == "CURSOR_ARROW":
                return wx.NullCursor
            else:
                return wx.NullCursor

        d = ResourceTable[str, wx.Cursor]("Resource/Image/Cursor", {}, lambda: wx.Cursor(wx.CURSOR_ARROW),
                                          nokeyfunc=get_cursor)
        return d

    def get_stones(self) -> "ResourceTable[str, pygame.Surface]":
        """
        適性・カード残り回数の画像を読み込んで、
        pygameのサーフェスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(cw.util.load_image, "Data/SkinBase/Resource/Image/Stone", dpath, self.ext_img,
                                  True, cw.s, emptyfunc=empty_image)

    def get_wxstones(self) -> "ResourceTable[str, wx.Bitmap]":
        """
        適性・カード残り回数の画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Stone")
        return self.get_resources(cw.util.load_wxbmp, "Data/SkinBase/Resource/Image/Stone", dpath, self.ext_img,
                                  True, cw.wins, emptyfunc=empty_wxbmp)

    def get_statuses(self, load_image: Callable[..., _ResType]) -> "ResourceTable[str, _ResType]":
        """
        ステータス表示に使う画像を読み込んで、
        ("LIFEGUAGE", "TARGET", "LIFE", "UP*", "DOWN*"はマスクする)
        pygameのサーフェスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc = empty_wxbmp
        else:
            ss = cw.s
            emptyfunc = empty_image

        def load_image2(fpath: str, mask: bool = False, can_loaded_scaledimage: bool = True,
                        up_scr: Optional[int] = None) -> pygame.Surface:
            fname = os.path.basename(fpath)
            key = cw.util.splitext(fname)[0]
            if key in ("LIFE", "UP0", "UP1", "UP2", "UP3", "DOWN0", "DOWN1", "DOWN2", "DOWN3"):
                return load_image(fpath, mask=True, maskpos=(1, 1), can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            elif key == "TARGET":
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            elif key == "LIFEGUAGE":
                return load_image(fpath, mask=True, maskpos=(5, 5), can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            elif key == "LIFEGUAGE2":
                return load_image(fpath, mask=True, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEGUAGE2_MASK":
                return load_image(fpath, mask=True, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "LIFEBAR":
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            else:
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Status")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/Status", dpath, self.ext_img, False, ss,
                                  emptyfunc=emptyfunc)

    def get_dialogs(self, load_image: Callable[..., _ResType]) -> "ResourceTable[str, pygame.Surface]":
        """
        ダイアログで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc = empty_wxbmp
        else:
            ss = cw.s
            emptyfunc = empty_image

        def load_image2(fpath: str, mask: bool = False, can_loaded_scaledimage: bool = True,
                        up_scr: Optional[int] = None) -> pygame.Surface:
            fname = os.path.basename(fpath)
            key = cw.util.splitext(fname)[0]
            if key in ("LINK", "MONEYY"):
                return load_image(fpath, mask=False, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            elif key == "STATUS8":
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            elif key in ("CAUTION", "INVISIBLE"):
                return load_image(fpath, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)
            else:
                return load_image(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Dialog")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/Dialog", dpath, self.ext_img, True, ss,
                                  emptyfunc=emptyfunc)

    def get_debugs(self, load_image: Callable[..., _ResType], ss: Callable[["cw.Scalable"], "cw.Scalable"],
                   can_loaded_scaledimage: bool = True) -> "ResourceTable[str, _ResType]":
        """
        デバッガで使う画像を読み込んで、
        wxBitmapのインスタンスの辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            emptyfunc = empty_wxbmp
        else:
            emptyfunc = empty_image

        dpath = "Data/Debugger"

        # 可能ならcwxeditor/resourceからアイコンを読み込む
        setting = self.setting()
        assert setting
        editor_res: Optional[str] = os.path.dirname(os.path.abspath(setting.editor))
        assert editor_res is not None
        editor_res = cw.util.join_paths(editor_res, "resource")
        if not os.path.isdir(editor_res):
            editor_res = None

        return self.get_resources(load_image, dpath, "", cw.M_IMG, True, ss, emptyfunc=emptyfunc, editor_res=editor_res,
                                  can_loaded_scaledimage=can_loaded_scaledimage)

    def get_cardbgs(self, load_image: Callable[..., _ResType]) -> "ResourceTable[str, pygame.Surface]":
        """
        カードの背景画像を読み込んで、pygameのサーフェス
        ("PREMIER", "RARE", "HOLD", "PENALTY"はマスクする)
        の辞書で返す。
        """
        if load_image == cw.util.load_wxbmp:
            ss = cw.wins
            emptyfunc = empty_wxbmp
        else:
            ss = cw.s
            emptyfunc = empty_image

        def load_image2(fpath: str, mask: bool = False, can_loaded_scaledimage: bool = True,
                        up_scr: Optional[int] = None) -> pygame.Surface:
            fname = os.path.basename(fpath)
            key = cw.util.splitext(fname)[0]
            if key in ("HOLD", "PENALTY"):
                return load_image(fpath, mask=True, maskpos="center", can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            elif key in ("PREMIER", "RARE"):
                return load_image(fpath, mask=True, maskpos="right", can_loaded_scaledimage=can_loaded_scaledimage,
                                  up_scr=up_scr)
            else:
                return load_image(fpath, mask=mask, can_loaded_scaledimage=can_loaded_scaledimage, up_scr=up_scr)

        dpath = cw.util.join_paths(self.skindir, "Resource/Image/CardBg")
        return self.get_resources(load_image2, "Data/SkinBase/Resource/Image/CardBg", dpath, self.ext_img, False,
                                  ss, nodbg=True, emptyfunc=emptyfunc)

    def get_cardnamecolorhints(self, cardbgs: "ResourceTable[str, int]") -> "ResourceTable[str, int]":
        """
        カードの各台紙について、文字描画領域の色を
        平均化した辞書を作成する。
        """
        d = ResourceTable[str, int]("CardBgColorHints", {}, lambda: 255)
        for key in ("ACTION", "BEAST", "BIND", "DANGER", "FAINT", "INFO", "INJURY", "ITEM",
                    "LARGE", "NORMAL", "OPTION", "PARALY", "PETRIF", "SKILL", "SLEEP"):
            def func(key: str) -> None:
                d.set(key, lambda: self.calc_cardnamecolorhint(cardbgs[key]))
            func(key)
        return d

    def calc_cardnamecolorhint(self, bmp: pygame.Surface) -> int:
        """文字描画領域の色を平均化した値を返す。
        """
        if bmp.get_width() <= cw.s(10) or bmp.get_height() <= cw.s(20):
            return 255
        rect = pygame.Rect(cw.s(5), cw.s(5), bmp.get_width() - cw.s(10), cw.s(15))
        sub = bmp.subsurface(rect)
        buf = pygame.image.tostring(sub, "RGB")
        buf = array.array('B', buf)
        rgb = sum(buf) // len(buf)
        return rgb

    def calc_wxcardnamecolorhint(self, wxbmp: wx.Bitmap) -> int:
        """文字描画領域の色を平均化した値を返す。
        """
        if wxbmp.GetWidth() <= cw.s(10) or wxbmp.GetHeight() <= cw.s(20):
            return 255
        rect = wx.Rect(cw.s(5), cw.s(5), wxbmp.GetWidth() - cw.s(10), cw.s(15))
        sub = wxbmp.GetSubBitmap(rect)
        buf = array.array('B', '\0' * (rect[2] * rect[3] * 3))
        sub.CopyToBuffer(buf, format=wx.BitmapBufferFormat_RGB)
        rgb = sum(buf) // len(buf)
        return rgb

    def get_actioncards(self) -> Dict[int, "cw.header.CardHeader"]:
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

    def get_backpackcards(self) -> Dict[str, "cw.header.CardHeader"]:
        """
        "Resource/Xml/SpecialCard/UseCardInBackpack.xml"のカードを読み込み、
        cw.header.CardHeaderインスタンスの辞書で返す。
        """
        fpath = cw.util.join_paths(self.skindir, "Resource/Xml/SpecialCard/UseCardInBackpack.xml")
        if not os.path.isfile(fpath):
            # 旧バージョンのスキンには存在しないのでSkinBaseを使用
            fpath = "Data/SkinBase/Resource/Xml/SpecialCard/UseCardInBackpack.xml"
        carddata = cw.data.xml2element(fpath)

        d = {}
        for cardtype in ("ItemCard", "BeastCard"):
            d[cardtype] = cw.header.CardHeader(carddata=carddata, bgtype=cardtype.upper().replace("CARD", ""))
        return d

    def get_specialchars(self) -> "ResourceTable[str, Tuple[pygame.Surface, bool]]":
        """
        特殊文字の画像を読み込んで、
        pygameのサーフェスの辞書で返す(特殊文字がkey)
        """
        self.specialchars_is_changed = False
        dpath = cw.util.join_paths(self.skindir, "Resource/Image/Font")

        ndict = {"ANGRY": "#a",
                 "CLUB": "#b",
                 "DIAMOND": "#d",
                 "EASY": "#e",
                 "FLY": "#f",
                 "GRIEVE": "#g",
                 "HEART": "#h",
                 "JACK": "#j",
                 "KISS": "#k",
                 "LAUGH": "#l",
                 "NIKO": "#n",
                 "ONSEN": "#o",
                 "PUZZLE": "#p",
                 "QUICK": "#q",
                 "SPADE": "#s",
                 "WORRY": "#w",
                 "X": "#x",
                 "ZAP": "#z",
                 }

        d = ResourceTable[str, Tuple[pygame.Surface, bool]]("Resource/Image/Font", {}, empty_image)

        def load(key: str, name: str) -> Tuple[pygame.Surface, bool]:
            fpath = cw.util.find_resource(cw.util.join_paths(dpath, key), self.ext_img)
            image = cw.util.load_image(fpath, mask=True, can_loaded_scaledimage=True)
            return image, False

        for key, name in ndict.items():
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


def get_resourcesize(path: str) -> Tuple[int, int]:
    """指定されたリソースの標準サイズを返す。"""
    dpath = os.path.basename(os.path.dirname(path))
    fpath = cw.util.splitext(os.path.basename(path))[0]
    key = "%s/%s" % (dpath, fpath)
    if key in SIZE_RESOURCES:
        return SIZE_RESOURCES[key]
    else:
        assert False


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
    "LOCAL_FLAG": "flag_l.png",
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
    "LOCAL_STEP": "step_l.png",
    "UPDATE": "refresh.png",
    "VARIANT": "variant.png",
    "LOCAL_VARIANT": "variant_l.png",
    "YADO": "sc_y.png",
    "VARIABLES": "flagdir.png",

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
    "EVT_CHANGE_ENVIRONMENT": "evt_ch_env.png",  # 状況設定(Wsn.4)

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
    "EVT_SET_VARIANT": "evt_set_var.png",  # コモン設定(Wsn.4)
    "EVT_BRANCH_VARIANT": "evt_br_var.png",  # コモン分岐(Wsn.4)
    "EVT_CHECK_VARIANT": "evt_chk_var.png",  # コモン判定(Wsn.4)

    # Utility
    "EVT_BRANCH_SELECT": "evt_br_member.png",  # メンバ選択
    "EVT_BRANCH_ABILITY": "evt_br_power.png",  # 能力判定分岐
    "EVT_BRANCH_RANDOM": "evt_br_random.png",  # ランダム分岐
    "EVT_BRANCH_MULTIRANDOM": "evt_br_multi_random.png",  # ランダム多岐分岐
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
    "EVT_MOVE_CARD": "evt_mv_card.png",  # カード再配置
    "EVT_MOVE_BGIMAGE": "evt_mv_back.png",  # 背景再配置
    "EVT_REPLACE_BGIMAGE": "evt_rpl_back.png",  # 背景置換
    "EVT_LOSE_BGIMAGE": "evt_lose_back.png",  # 背景削除
    "EVT_REDISPLAY": "evt_refresh.png",  # 画面の再構築
}


def empty_wxbmp() -> wx.Bitmap:
    """空のwx.Bitmapを返す。"""
    wxbmp = cw.util.empty_bitmap(1, 1)
    image = wxbmp.ConvertToImage()
    r = image.GetRed(0, 0)
    g = image.GetGreen(0, 0)
    b = image.GetBlue(0, 0)
    image.SetMaskColour(r, g, b)
    return image.ConvertToBitmap()


def empty_image() -> pygame.Surface:
    """空のpygame.Surfaceを返す。"""
    image = pygame.Surface((1, 1)).convert()
    image.set_colorkey(image.get_at((0, 0)), pygame.locals.RLEACCEL)
    return image


def empty_sound() -> cw.util.SoundInterface:
    """空のcw.util.SoundInterfaceを返す。"""
    return cw.util.SoundInterface(None, "")


class LazyResource(Generic[_ResType]):
    def __init__(self, func: Callable[..., _ResType], args: Sequence[typing.Any],
                 kwargs: Dict[typing.Any, typing.Any]) -> None:
        """リソースをfunc(*args, **kwargs)によって
        遅延読み込みする。
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._res: Optional[_ResType] = None
        self.load = False
        self.failure = False

    def clear(self) -> None:
        self.load = False
        self._res = None

    def get_res(self) -> _ResType:
        if not self.load:
            try:
                self._res = self.func(*self.args, **self.kwargs)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                self.failure = True
            self.load = True
        assert self._res is not None
        return self._res


class ResourceTable(Generic[_KeyType, _ResType]):
    def __init__(self, name: str, init: Optional[Dict[_KeyType, LazyResource[_ResType]]] = None,
                 deffunc: Optional[Callable[[], _ResType]] = None,
                 nokeyfunc: Optional[Callable[[_KeyType], _ResType]] = None) -> None:
        """文字列をキーとしたリソーステーブル。
        各リソースは必要になった時に遅延読み込みされる。
        """
        if init is None:
            init = {}
        self.name = name
        self.dic = init

        self.nokeyfunc = nokeyfunc

        self.deffunc = deffunc
        self.defvalue: Optional[_ResType] = None
        self.defload = False

    def reset(self) -> None:
        for lazy in self.dic.values():
            lazy.clear()

    def merge(self, d: "ResourceTable[_KeyType, _ResType]") -> None:
        for key, value in self.dic.items():
            if key not in self.dic:
                self.dic[key] = value

    def __getitem__(self, key: _KeyType) -> _ResType:
        self._put_nokeyvalue(key)
        lazy = self.dic.get(key, None)
        if lazy:
            first = not lazy.load
            val = lazy.get_res()
            if lazy.failure:
                if first:
                    s = "リソース [%s/%s] の読み込みに失敗しました。\n" % (self.name, key)
                    sys.stderr.write(s)
                if not self.deffunc:
                    raise Exception(s)
                return self.get_defvalue()
            else:
                return val
        else:
            if not self.defload:
                s = "リソース [%s/%s] が見つかりません。\n" % (self.name, key)
                sys.stderr.write(s)
                if not self.deffunc:
                    raise Exception(s)
            return self.get_defvalue()

    def get_defvalue(self) -> _ResType:
        if not self.deffunc:
            raise Exception()
        if not self.defload:
            self.defvalue = self.deffunc()
            self.defload = True
        assert self.defvalue is not None
        return self.defvalue

    def _put_nokeyvalue(self, key: _KeyType) -> None:
        if self.nokeyfunc and key not in self.dic:
            def func() -> _ResType:
                assert self.nokeyfunc
                return self.nokeyfunc(key)
            self.dic[key] = LazyResource(func, (), {})

    def get(self, key: _KeyType, defvalue: Optional[_ResType] = None) -> Optional[_ResType]:
        self._put_nokeyvalue(key)
        if key in self.dic:
            return self[key]
        return defvalue

    def set(self, key: _KeyType, func: Callable[..., _ResType], *args: typing.Any, **kwargs: typing.Any) -> None:
        self.dic[key] = LazyResource(func, args, kwargs)

    def remove(self, key: _KeyType) -> None:
        del self.dic[key]

    def __contains__(self, key: _KeyType) -> bool:
        self._put_nokeyvalue(key)
        return key in self.dic

    def copy(self) -> "ResourceTable[_KeyType, _ResType]":
        tbl = ResourceTable[_KeyType, _ResType](self.name, self.dic.copy(), self.deffunc, self.nokeyfunc)
        tbl.defvalue = self.defvalue
        tbl.defload = self.defload
        return tbl

    def iterkeys(self) -> Generator[_KeyType, None, None]:
        for key in self.dic.keys():
            yield key

    def is_loaded(self, key: _KeyType) -> bool:
        self._put_nokeyvalue(key)
        return self.dic[key].load

    def keys(self) -> KeysView[_KeyType]:
        return self.dic.keys()


class RecentHistory(object):
    def __init__(self, tempdir: str, ydata: cw.data.YadoData) -> None:
        """起動してから開いたシナリオの情報を
        (wsn・zipファイルのパス, 最終更新日, "Data/Temp"に展開したフォルダパス)の
        形式で保存し、管理するクラス。
        古い順から"Data/Temp"のフォルダを削除していく。
        ただし以下の条件で削除順は多少前後する。
         * 済印つきのシナリオは優先して削除する
         * ブックマークされているシナリオはできるだけ削除しない
        tempdir: シナリオの一時展開先
        ydata: シナリオキャッシュを保持する宿
        """
        self.ydata = ydata
        self.scelist = []
        temppaths = set()
        limit = cw.cwpy.setting.recenthistory_limit

        fpath = cw.util.join_paths(tempdir, "RecentHistory.xml")
        if cw.fsync.is_waiting(fpath):
            cw.fsync.sync()
        if os.path.isfile(fpath):
            self.data = cw.data.xml2etree(fpath)
        else:
            self.data = cw.data.CWPyElementTree(element=cw.data.make_element("RecentHistory", ""))
            self.data.fpath = fpath
            self.data.write_file()

        # キャッシュ履歴を読み込み、
        # キャシュ元とキャッシュ本体が実在するものだけリストに追加する
        for e in self.data.getfind("."):
            if e.tag == "Scenario":
                name = e.gettext("Name", "")
                path = e.gettext("WsnPath", "")
                temppath = e.gettext("TempPath", "")
                md5 = e.get("md5")

                if os.path.isfile(path) and os.path.isdir(temppath) and md5:
                    self.scelist.append((path, md5, temppath, name))
                    temppath = os.path.normpath(temppath)
                    temppath = os.path.normcase(temppath)
                    temppaths.add(temppath)

        # キャッシュ元が消滅しているなど使用不能になっているキャッシュを削除する
        if os.path.isdir(tempdir):
            for name in os.listdir(tempdir):
                path = cw.util.join_paths(tempdir, name)
                if os.path.isdir(path):
                    path = os.path.normpath(path)
                    path = os.path.normcase(path)

                    if path not in temppaths:
                        cw.util.remove(path)

        self.set_limit(limit)

    def update_scenariopath(self, from_normpath: str, to_path: str) -> None:
        seq = []

        s = set()
        for path, md5, temppath, name in self.scelist:
            normpath2 = cw.util.get_keypath(path)
            if normpath2 == from_normpath:
                if normpath2 in s:
                    cw.util.remove(temppath)
                    continue
                else:
                    s.add(normpath2)
                    path = to_path
                    if os.path.isfile(from_normpath):
                        md5 = cw.util.get_md5(from_normpath)
                    elif os.path.isfile(to_path):
                        md5 = cw.util.get_md5(to_path)

            seq.append((path, md5, temppath, name))
        self.scelist = seq
        self.write()

    def write(self) -> None:
        # シナリオ履歴
        data = self.data.getroot()

        while len(data):
            data.remove(data[-1])

        for path, md5, temppath, name in self.scelist:
            e_sce = cw.data.make_element("Scenario", "", {"md5": str(md5)})
            e = cw.data.make_element("WsnPath", path)
            e_sce.append(e)
            e = cw.data.make_element("TempPath", temppath)
            e_sce.append(e)
            if name:
                e = cw.data.make_element("Name", name)
                e_sce.append(e)
            data.append(e_sce)

        self.data.write_file()

    def set_limit(self, value: int) -> None:
        """
        保持履歴数を設定する。
        履歴数を超えたデータは古い順(先頭)から削除。
        """
        self.limit = value

        if self._remove_old():
            self.write()

    def _remove_old(self, exclude: Optional[str] = None) -> bool:
        if not self.limit:
            return False
        if not self.ydata:
            return False

        # ブックマークつきのシナリオをリストから除外しておく
        bookmarks = set()
        for _bookmark, bookmarkpath in self.ydata.bookmarks:
            bookmarks.add(cw.util.get_keypath(bookmarkpath))
        b_seq = []
        seq = []
        for t in self.scelist:
            if cw.util.get_keypath(t[0]) in bookmarks:
                b_seq.append(t)
            else:
                seq.append(t)

        if len(seq) > self.limit:
            self._sort_scelist(seq, exclude=exclude)
            while len(seq) > self.limit:
                self.remove(save=False, scelist=seq)
            self.scelist.clear()
            self.scelist.extend(seq)
            self.scelist.extend(b_seq)
            return True
        else:
            return False

    def _sort_scelist(self, scelist: List[Tuple[str, str, str, str]], exclude: Optional[str] = None) -> None:
        """
        済印つきのシナリオをリストの先頭へ移動する。
        """
        stamps = self.ydata.get_compstamps()
        seq = scelist[:]
        scelist.clear()
        scelist.extend(filter(lambda t: t[3] in stamps and t[0] != exclude, seq))
        scelist.extend(filter(lambda t: t[3] not in stamps or t[0] == exclude, seq))

    def moveend(self, path: str) -> None:
        """
        引数のpathのデータを一番下に移動する。
        """
        seq = [i for i in self.scelist if i[0] == path]

        for i in seq:
            self.scelist.remove(i)
            self.scelist.append(i)

        self.write()

    def append(self, name: str, path: str, temppath: str, md5: Optional[str] = None) -> None:
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
        self.scelist.append((path, md5, temppath, name))

        self._remove_old(exclude=path)
        self.write()

    def remove(self, path: str = "", save: bool = True,
               scelist: Optional[List[Tuple[str, str, str, str]]] = None) -> None:
        """
        path: 登録削除するwsn・zipファイルのパス。
        空の場合は一番先頭にあるデータの登録を削除する。
        """
        if scelist is None:
            scelist = self.scelist

        if not path:
            cw.util.remove(scelist[0][2])
            scelist.remove(scelist[0])
        else:
            path = path.replace("\\", "/")
            seq = [i for i in scelist if i[0] == path]

            for i in seq:
                cw.util.remove(i[2])
                scelist.remove(i)

        if save:
            self.write()

    def check(self, path: str, md5: Optional[str] = None) -> Optional[str]:
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

        i_temppath: str
        for i_path, i_md5, i_temppath, name in seq:
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

    def __init__(self, fpath: str = "Data/SystemCoupons.xml", data: Optional[cw.data.CWPyElement] = None) -> None:
        self._normal = set()  # 固定値
        self._regexes = []  # 正規表現
        self._ats = True  # u"＠"で始まる称号のみが含まれる場合はTrue
        if data is None and os.path.isfile(fpath):
            data = cw.data.xml2element(path=fpath)
        if data is not None:
            for e in data:
                if self._ats and not e.text.startswith("＠"):
                    self._ats = False

                regex = e.getbool(".", "regex", False)
                if regex:
                    self._regexes.append(re.compile(e.text))
                else:
                    self._normal.add(e.text)

    def match(self, coupon: str) -> bool:
        """couponがシステムクーポンに含まれている場合はTrueを返す。
        """
        if self._ats and not coupon.startswith("＠"):
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
    $ [string]::concat(([Security.Cryptography.MD5]::Create()
        .ComputeHash((gi Summary.wsm).OpenRead())|%{$_.ToString('x2')}))

    Pythonでは次のようにして取得できる。
    >>> import hashlib
    >>> hashlib.md5(open("Summary.wsm", "rb").read()).hexdigest()
    """

    def __init__(self) -> None:
        self.table: Dict[str, Tuple[str, str, bool, bool, bool]] = {}

    def init(self) -> None:
        if os.path.isfile("Data/Compatibility.xml"):
            data = cw.data.xml2element(path="Data/Compatibility.xml")
            for e in data:
                key = e.get("md5", "")
                zindexmode = e.getattr(".", "zIndexMode", "")
                vanishmembercancellation = e.getbool(".", "enableVanishMemberCancellation", False)
                # F9でもゴシップや終了印が復元されない挙動の再現は
                # セキュリティホールになるため無効にする
                # gossiprestoration = e.getbool(".", "disableGossipRestoration", False)
                # compstamprestoration = e.getbool(".", "disableCompleteStampRestoration", False)
                gossiprestoration = False
                compstamprestoration = False
                if key and (e.text or zindexmode or vanishmembercancellation or gossiprestoration or
                            compstamprestoration):
                    self.table[key] = (e.text, zindexmode, vanishmembercancellation, gossiprestoration,
                                       compstamprestoration)

    def get_versionhint(self, fpath: Optional[str] = None,
                        filedata: Optional[bytes] = None) -> Optional[Tuple[str, str, bool, bool, bool]]:
        """fpathのファイル内容またはfiledataから、
        本来そのファイルが再生されるべきCardWirthの
        バージョンを取得する。
        """
        if filedata:
            key = hashlib.md5(filedata).hexdigest()
        else:
            assert fpath is not None
            key = cw.util.get_md5(fpath)

        return self.table.get(key, None)

    def lessthan(self, versionhint: str, currentversion: Optional[Tuple[str, str, bool, bool, bool]]) -> bool:
        """currentversionがversionhint以下であればTrueを返す。"""
        if not currentversion:
            return False
        if not currentversion[0]:
            return False
        if not versionhint:
            return False

        try:
            return float(currentversion[0]) <= float(versionhint)
        except Exception:
            return False

    def zindexmode(self, currentversion: Optional[Tuple[str, str, bool, bool, bool]]) -> bool:
        """メニューカードをプレイヤーカードより前に配置するモードで
        あればTrueを返す。
        """
        if not currentversion:
            return False

        if currentversion[1]:
            try:
                return float(currentversion[1]) <= float("1.20")
            except Exception:
                return False
        else:
            return self.lessthan("1.20", currentversion)

    def enable_vanishmembercancellation(self, currentversion: Optional[Tuple[str, str, bool, bool, bool]]) -> bool:
        """パーティメンバが再配置される前であれば
        対象消去がキャンセルされるモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[2]

    def disable_gossiprestration(self, currentversion: Optional[Tuple[str, str, bool, bool, bool]]) -> bool:
        """F9でのゴシップ復元を無効にする問題を
        再現するモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[3]

    def disable_compstamprestration(self, currentversion: Optional[Tuple[str, str, bool, bool, bool]]) -> bool:
        """F9での終了印復元を無効にする問題を
        再現するモードであればTrueを返す。
        """
        if not currentversion:
            return False

        return currentversion[4]

    def merge_versionhints(self, hint1: Optional[Tuple[str, str, bool, bool, bool]],
                           hint2: Optional[Tuple[str, str, bool, bool, bool]])\
            -> Optional[Tuple[str, str, bool, bool, bool]]:
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

    def from_basehint(self, basehint: str) -> Tuple[str, str, bool, bool, bool]:
        """basehintから複合情報を生成する。"""
        return (basehint, "", False, False, False)

    def to_basehint(self, versionhint: Optional[Tuple[str, str, bool, bool, bool]]) -> str:
        """複合情報versionhintから最も基本的な情報を取り出す。"""
        if versionhint:
            return versionhint[0] if versionhint[0] else ""
        else:
            return ""

    def read_modeini(self, fpath: str) -> Optional[Tuple[str, str, bool, bool, bool]]:
        """クラシックなシナリオのmode.iniから互換性情報を読み込む。
        互換性情報が無いか、読込に失敗した場合はNoneを返す。
        """
        try:
            conf = configparser.SafeConfigParser()
            conf.read(fpath)

            try:
                engine = conf.get("Compatibility", "engine")
            except Exception:
                engine = ""

            try:
                zindexmode = conf.get("Compatibility", "zIndexMode")
            except Exception:
                zindexmode = ""

            try:
                vanishmembercancellation_s = conf.get("Compatibility", "enableVanishMemberCancellation")
                vanishmembercancellation = cw.util.str2bool(vanishmembercancellation_s)
            except Exception:
                vanishmembercancellation = False

            # F9でもゴシップや終了印が復元されない挙動の再現は
            # セキュリティホールになるため無効にする
            gossiprestration = False
            # try:
            #     gossiprestration = conf.get("Compatibility", "disableGossipRestoration")
            #     gossiprestration = cw.util.str2bool(gossiprestration)
            # except:
            #     gossiprestration = False

            compstamprestration = False
            # try:
            #     compstamprestration = conf.get("Compatibility", "disableCompleteStampRestoration")
            #     compstamprestration = cw.util.str2bool(compstamprestration)
            # except:
            #     compstamprestration = False

            if engine or zindexmode or vanishmembercancellation or gossiprestration or compstamprestration:
                return (engine, zindexmode, vanishmembercancellation, gossiprestration, compstamprestration)
        except Exception:
            cw.util.print_ex()
        return None
