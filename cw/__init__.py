#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import wx
import pygame
import pygame.surface

from . import util
from . import battle
from . import yadodb
from . import data
from . import dice
from . import effectmotion
from . import event
from . import eventhandler
from . import eventrelay
from . import features
from . import scenariodb
from . import setting
from . import skin
from . import animation
import cw.thread as thread
from . import header
from . import image
from . import imageretouch
from . import frame
from . import deck
from . import character
from . import effectbooster
from . import content
from . import xmlcreater
from . import bassplayer
from . import binary
from . import advlog
from . import update
from . import calculator

from . import dialog
from . import debug
from . import sprite

from . import argparser
from . import nctype

__all__ = ["util", "battle", "yadodb", "data", "dice", "effectmotion", "event", "eventhandler", "eventrelay",
           "features", "scenariodb", "setting", "skin", "animation", "thread", "header", "image", "imageretouch",
           "frame", "deck", "character", "effectbooster", "content", "xmlcreater", "bassplayer", "binary", "advlog",
           "update", "calculator", "dialog", "debug", "sprite", "argparser", "nctype"]

import typing
from typing import List, Tuple, TypeVar

# 実行ファイルのパス
exepath = ""
quit_app = False

# ファイルパスのエンコーディング
if sys.platform == "win32":
    filesystem_encoding = "mbcs"
else:
    filesystem_encoding = sys.getfilesystemencoding()

# CWPyThread
cwpy: thread.CWPy = thread.CWPy()

# ファイル出力スレッド
fsync = util.FileSync()

# 一時ディレクトリ
tempdir_init = "Data/Temp/Global"
tempdir = tempdir_init

# アプリケーション情報
APP_VERSION = (5, "0")
APP_NAME = "CardWirthPy"

# CardWirthの標準文字コード
if sys.platform == "win32":
    MBCS = "mbcs"
else:
    MBCS = "ms932"

# ウィンドウ操作やデバッガへの反映など、ゲームの流れの外で実行されるイベント
FORCE_USEREVENT = pygame.USEREVENT+1

# コール系イベントの再期限界回数
LIMIT_RECURSE = 10000

# サイズ
SIZE_SCR = (640, 480)
SIZE_GAME = (632, 453)
SIZE_AREA = (632, 420)
SIZE_CARDIMAGE = (74, 94)
SIZE_BOOK = (460, 280)
SIZE_BILL = (400, 370)
RECT_STATUSBAR = (0, 420, 632, 33)

# 対応するWSNデータバージョン
SUPPORTED_WSN = ("", "1", "2", "3", "4", "5")
# 対応するスキンバージョン
SUPPORTED_SKIN = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")

# スケーリングされたイメージファイルを検索する時、以下のスケール値を使用する
SCALE_LIST = (2, 4, 8, 16)

# 特殊エリアのID
AREAS_SP = (-1, -2, -3, -4, -5)
AREAS_TRADE: Tuple[int, int, int] = (-1, -2, -5)    # カード移動操作エリア
AREA_TRADE1 = -1                 # カード移動操作エリア(宿・パーティなし時)
AREA_TRADE2 = -2                 # カード移動操作エリア(宿・パーティロード中時)
AREA_TRADE3 = -5                 # カード移動操作エリア(キャンプエリア)
AREA_BREAKUP = -3                # パーティ解散エリア
AREA_CAMP = -4                   # キャンプエリア

AREAS_TITLE = (1,)  # タイトル画面のエリア
AREAS_YADO = (-3, -2, -1, 1, 2, 3, 4)  # 宿のエリア

# スキン固有エリアのID上下限
SKIN_AREAS_MIN = 10001
SKIN_AREAS_MAX = 20000

# カードポケットのインデックス
POCKET_SKILL = 0
POCKET_ITEM = 1
POCKET_BEAST = 2
POCKET_PERSONAL = 3

# イベント用子コンテンツ特殊インデックス
IDX_TREEEND = -1

# 素材タイプ
M_IMG = 0
M_MSC = 1
M_SND = 2

# 対応拡張子
EXTS_IMG = (".bmp", ".jpg", ".jpeg", ".png", ".gif", ".pcx", ".tif", ".xpm")
EXTS_MSC = (".mid", ".midi", ".mp3", ".ogg")
EXTS_SND = (".wav", ".wave", ".ogg")

# 互換性マークのインデックス
HINT_MESSAGE = 0    # メッセージ表示時の話者(キャストまたはカード)
HINT_CARD = 1       # 使用中のカード
HINT_AREA = 2       # エリア・バトル・パッケージ
HINT_SCENARIO = 3   # シナリオ本体

# 標準のサウンドフォント
DEFAULT_SOUNDFONT = "Data/SoundFont/005.6mg_Aspirin_Stereo_V1.2_Bank.sf2"

# 表示レイヤ
LAYER_NUMBER_OF_CARDS = 0
LAYER_JPY_TEMPORAL = 1
LAYER_TITLE = 0

LTYPE_MESSAGE = 1
LTYPE_BACKGROUND = 2
LTYPE_BACKGROUND_CURTAIN = 3
LTYPE_MCARDS = 4
LTYPE_PCARDS = 5
LTYPE_FCARDS = 0
LTYPE_SPMESSAGE = 1
LTYPE_SPMCARDS = 4

LTYPE_MAX = 11
LTYPE2_MAX = 2

LAYER_FRONT = 0x00200000
LAYER_SP_LAYER = 0x00100000
LAYER_MAX = LAYER_SP_LAYER - 1

LAYER_BACKGROUND = 0  # 背景
LAYER_SPBACKGROUND = LAYER_SP_LAYER  # 背景
LAYER_MCARDS = 100  # メニューカード・エネミーカード
LAYER_PCARDS = 200  # プレイヤーカード
LAYER_MCARDS_120 = 300  # CardWirth 1.20でのメニューカード(PCより手前に表示)
LAYER_FCARDS_T = LAYER_FRONT  # デバッグモードで表示される戦闘中の同行キャスト
LAYER_FCARDS = 1000  # 同行キャスト

LINDEX_MAX = 0x00100000

# (layer, index, kind)
LAYER_BATTLE_START = (LAYER_FRONT, LTYPE_MAX-5, LINDEX_MAX-2, 0)  # バトル開始カード
LAYER_FRONT_INUSECARD = (LAYER_FRONT, LTYPE_MAX-4, LINDEX_MAX-2, 0)  # カーソル下のカードの使用カード
LAYER_TARGET_ARROW = (LAYER_FRONT, LTYPE_MAX-2, LINDEX_MAX-2, 0)  # 対象選択の指マーク
LAYER_FRONT_LIFEBAR = (LAYER_FRONT, LTYPE_MAX-3, LINDEX_MAX-2, 0)  # ライフバー

# index=-1は背景セル
LAYER_MESSAGE = (1000, LTYPE_MESSAGE, 0, 0)  # メッセージ
LAYER_SELECTIONBAR_1 = (1000, LTYPE_MESSAGE, 1, 0)  # メッセージ選択肢
LAYER_SELECTIONBAR_2 = (1000, LTYPE_MESSAGE, 2, 0)  # メッセージ選択肢(クリック中)

LAYER_SPMESSAGE = (LAYER_SP_LAYER+1000, LTYPE_SPMESSAGE, 0, 0)  # 特殊エリアのメッセージ
LAYER_SPSELECTIONBAR_1 = (LAYER_SP_LAYER+1000, LTYPE_MESSAGE, 1, 0)  # 特殊エリアのメッセージ選択肢
LAYER_SPSELECTIONBAR_2 = (LAYER_SP_LAYER+1000, LTYPE_MESSAGE, 2, 0)  # 特殊エリアのメッセージ選択肢(クリック中)

LAYER_TRANSITION = (LAYER_FRONT, LTYPE_MAX-1, LINDEX_MAX-2, 0)  # 背景遷移用

LAYER_LOG_CURTAIN = (2000, 0, 0, 0)  # ログ背景
LAYER_LOG = (2001, 0, 0, 0)  # メッセージログ
LAYER_LOG_BAR = (2002, 0, 0, 0)  # ログ選択肢
LAYER_LOG_PAGE = (2003, 0, 0, 0)  # ログのページ
LAYER_LOG_SCROLLBAR = (2004, 0, 0, 0)  # ログのスクロールバー

LAYER_CLICKABLE_SPRITES = 0  # topgrpに表示されるClickableSprite


def layer_val(tlayer: Tuple[int, int, int, int]) -> int:
    """レイヤの複合値を単一のintにまとめる。"""
    layer, ltype, index, ltype2 = tlayer
    assert 0 <= layer
    assert 0 <= ltype
    assert -1 <= index
    assert 0 <= ltype2
    assert layer <= LAYER_FRONT
    assert ltype < LTYPE_MAX
    if LINDEX_MAX <= index + 1:
        raise ValueError("Invalid index: " + str(LINDEX_MAX) + " <= " + str(index) + " + 1")
    if LTYPE2_MAX <= ltype2:
        raise ValueError("Invalid background index: " + str(LTYPE2_MAX) + " <= " + str(ltype2))
    return layer * (LTYPE_MAX * LINDEX_MAX * LTYPE2_MAX) + ltype * (LINDEX_MAX * LTYPE2_MAX) +\
        (index + 1) * LTYPE2_MAX + ltype2


def add_layer(grp: pygame.sprite.LayeredDirty, *sprites: pygame.sprite.Sprite, layer: int) -> None:
    """LayeredDirty.add()でlayerパラメータを指定した時の以下の型エラーを回避するための暫定ラッパ。"""
    # BUG: error: Argument "layer" to "add" of "LayeredUpdates" has incompatible type "Tuple[int, int, int, int]";
    #      expected "Dict[str, Any]" (mypy 0.790)
    grp.add(*sprites, layer=typing.cast(typing.Any, layer))


# ゲーム画面構築の拡大率
UP_SCR = 1.0
# ダイアログ描画時の拡大率(UP_SCRが1の時の値)
UP_WIN = 1.0
# ゲーム画面の拡大率
# フルスクリーン時にはダイアログを若干小さく表示するため、
# UP_WINとは異なる値になる
UP_WIN_M = 1.0

# wxPythonでイメージをスムージングしつつサイズ変更する際に用いるフラグ
RESCALE_QUALITY = wx.IMAGE_QUALITY_BILINEAR

# プレイログの区切り線の長さ
LOG_SEPARATOR_LEN_LONG = 80
LOG_SEPARATOR_LEN_MIDDLE = 60
LOG_SEPARATOR_LEN_SHORT = 45

# 起動オプション
_argparser = argparser.ArgParser(appname=APP_NAME,
                                 description="%s %s\n\nオープンソースのCardWirthエンジン" %
                                             (APP_NAME, ".".join([str(a) for a in APP_VERSION])))
_argparser.add_argument("-h", argtype=bool, nargs=0,
                        helptext="このメッセージを表示して終了します。", arg2="--help")
_argparser.add_argument("-debug", argtype=bool, nargs=0,
                        helptext="デバッグモードで起動します。")
_argparser.add_argument("-yado", argtype=str, nargs=1, default="",
                        helptext="起動と同時に<YADO>のパスにある拠点を読み込みます。")
_argparser.add_argument("-party", argtype=str, nargs=1, default="",
                        helptext="起動と同時に<PARTY>のパスにあるパーティを読み込みます。\n"
                                 + "-yadoと同時に指定しなかった場合は無視されます。")
_argparser.add_argument("-scenario", argtype=str, nargs=1, default="",
                        helptext="起動と同時に<SCENARIO>のパスにあるシナリオを開始します。\n"
                                 + "-yado及び-partyと同時に指定しなかった場合は無視されます。")
_argparser.add_argument("-skin", argtype=str, nargs=1, default="",
                        helptext="<SKIN>のパスにあるスキンで起動します。\n"
                                 + "起動と同時に拠点が開かれる場合は拠点のスキンが優先されます。")
_argparser.add_argument("--force-skin", argtype=str, nargs=1, default="", metavar="SKIN",
                        helptext="<SKIN>のパスにあるスキンで起動します。\n"
                                 + "拠点のスキンや、-skinよりも優先されます。")
_argparser.add_argument("--debug-skin", argtype=bool, nargs=0,
                        helptext="スキンデバッグモードで起動します。")

_options = _argparser.parse_args(sys.argv[1:])
if not _options or _options.getbool("help"):
    _argparser.print_help()
    sys.exit(0)

OPTIONS = _options

if OPTIONS.getstr("force_skin"):
    OPTIONS.setstr("skin", OPTIONS.getstr("force_skin"))

# 起動オプション(スキン自動生成元)
SKIN_CONV_ARGS: List[str] = []
for arg in OPTIONS.leftovers:
    if os.path.isfile(arg) and util.splitext(arg)[1].lower() == ".exe":
        SKIN_CONV_ARGS.append(arg)
        sys.argv.remove(arg)


Scalable = TypeVar("Scalable", wx.Bitmap, wx.Image, pygame.surface.Surface, pygame.rect.Rect, Tuple[int, int],
                   Tuple[int, int, int, int], int)


def wins(num: Scalable) -> Scalable:
    """numを実際の表示サイズに変換する。
    """
    return _s_impl(num, UP_WIN)


def s(num: Scalable) -> Scalable:
    """numを描画サイズに変換する。
    num: int or 座標(x,y) or 矩形(x,y,width,height)
         or pygame.surface.Surface or wx.Bitmap or wx.Image
    """
    return _s_impl(num, UP_SCR)


def scr2win_s(num: Scalable) -> Scalable:
    """numを描画サイズから表示サイズに変換する。
    """
    if UP_WIN == UP_SCR:
        return _s_impl(num, 1.0)
    else:
        return _s_impl(num, float(UP_WIN) / UP_SCR)


def win2scr_s(num: Scalable) -> Scalable:
    """numを表示サイズから描画サイズに変換する。
    """
    if UP_WIN == UP_SCR:
        return _s_impl(num, 1.0)
    else:
        return _s_impl(num, float(UP_SCR) / UP_WIN)


def scr2mwin_s(num: Scalable) -> Scalable:
    """numを描画サイズから表示サイズに変換する。
    """
    if UP_WIN_M == UP_SCR:
        return _s_impl(num, 1.0)
    else:
        return _s_impl(num, float(UP_WIN_M) / UP_SCR)


def mwin2scr_s(num: Scalable) -> Scalable:
    """numを表示サイズから描画サイズに変換する。
    """
    if UP_WIN_M == UP_SCR:
        return _s_impl(num, 1.0)
    else:
        return _s_impl(num, float(UP_SCR) / UP_WIN_M)


def _s_impl(num: Scalable, up_scr: float) -> Scalable:
    if up_scr == 1.0:
        # 拡大率が1倍なのでそのまま返す
        return num

    if isinstance(num, int):
        # 単純な数値(座標やサイズ)
        # BUG: Incompatible return value type (got "int", expected "Surface") (mypy 0.790)
        # return int(num * up_scr)
        # BUG: Redundant cast to "int" (mypy 0.790)
        # return typing.cast(Scalable, int(num * up_scr))
        return typing.cast(Scalable, typing.cast(typing.Any, int(num * up_scr)))

    elif isinstance(num, pygame.rect.Rect):
        # pygameの矩形情報
        rect: pygame.rect.Rect = num
        x = int(rect.x * up_scr)
        y = int(rect.y * up_scr)
        w = int(rect.width * up_scr)
        h = int(rect.height * up_scr)
        # BUG: error: Returning Any from function declared to return "Tuple[int, int]"
        #      error: Returning Any from function declared to return "Tuple[int, int, int, int]"
        return typing.cast(Scalable, pygame.rect.Rect(x, y, w, h))

    elif isinstance(num, tuple):
        if len(num) == 4:
            # 矩形
            # BUG: Tuple[int, int, int, int]とTuple[int, int]が混同され以下の警告が発生する(mypy 0.790)
            #      Tuple index out of range
            t: Tuple[int, ...] = num
            t4 = typing.cast(Tuple[int, int, int, int], t)
            x = int(t4[0] * up_scr)
            y = int(t4[1] * up_scr)
            w = int(t4[2] * up_scr)
            h = int(t4[3] * up_scr)
            # BUG: Tuple[int, int, int, int]とTuple[int, int]が混同され以下の警告が発生する(mypy 0.790)
            #      Incompatible return value type (got "Tuple[int, int, int, int]", expecte "Tuple[int, int]")
            # return (x, y, w, h)
            # BUG: Redundant cast to "Tuple[int, int, int, int]" (mypy 0.790)
            # return typing.cast(Scalable, (x, y, w, h))
            return typing.cast(Scalable, typing.cast(Tuple[int, ...], (x, y, w, h)))
        elif len(num) == 2:
            # 座標
            x = int(num[0] * up_scr)
            y = int(num[1] * up_scr)
            # BUG: Tuple[int, int, int, int]とTuple[int, int]が混同され以下の警告が発生する(mypy 0.790)
            #      Incompatible return value type (got "Tuple[int, int]", expected "Tuple[it, int, int, int]")
            # return (x, y)
            # BUG: Redundant cast to "Tuple[int, int]" (mypy 0.790)
            # return typing.cast(Scalable, (x, y))
            return typing.cast(Scalable, typing.cast(Tuple[int, ...], (x, y)))
        else:
            assert False

    elif isinstance(num, pygame.surface.Surface):
        # スケール情報の無いpygame.surface.Surface(単純拡大)
        bmp0 = num
        if isinstance(num, util.Depth1Surface):
            scr_scale = num.scr_scale
        else:
            scr_scale = 1.0
        up_scr /= scr_scale
        if up_scr == 1.0:
            return num
        bmp: pygame.surface.Surface = num
        w = int(bmp.get_width() * up_scr)
        h = int(bmp.get_height() * up_scr)
        if w <= 0 or h <= 0:
            return bmp
        size = (w, h)
        if up_scr % 1 == 0:
            result = pygame.transform.scale(bmp, size)
        else:
            if not (bmp.get_flags() & pygame.SRCALPHA) and bmp.get_colorkey():
                bmp = bmp.convert_alpha()
            result = image.smoothscale(bmp, size)
        if isinstance(bmp0, util.Depth1Surface):
            result = util.Depth1Surface(result, scr_scale)
            result.bmpdepthis1 = bmp0.bmpdepthis1
        return result

    elif isinstance(num, wx.Image):
        # スケール情報の無いwx.Image(単純拡大)
        bmpdepthis1 = hasattr(num, "bmpdepthis1")
        maskcolour = num.maskcolour if hasattr(num, "maskcolour") else None
        scr_scale = num.scr_scale if hasattr(num, "scr_scale") else 1
        up_scr /= scr_scale
        if up_scr == 1:
            # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
            # return num
            return typing.cast(Scalable, num)
        w = int(num.GetWidth() * up_scr)
        h = int(num.GetHeight() * up_scr)
        if w <= 0 or h <= 0:
            # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
            # return num
            return typing.cast(Scalable, num)

        if up_scr % 1 == 0 or bmpdepthis1:
            wximg = num.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
        else:
            if not num.HasAlpha():
                num.InitAlpha()
            wximg = num.Rescale(w, h, RESCALE_QUALITY)

        if bmpdepthis1:
            wximg.bmpdepthis1 = bmpdepthis1
        if maskcolour:
            wximg.maskcolour = maskcolour
            r, g, b = maskcolour
            wximg.SetMaskColour(r, g, b)

        # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
        # return wximg
        return typing.cast(Scalable, wximg)

    elif isinstance(num, wx.Bitmap):
        # スケール情報の無いwx.Bitmap(単純拡大)
        bmpdepthis1 = hasattr(num, "bmpdepthis1")
        maskcolour = num.maskcolour if hasattr(num, "maskcolour") else None
        scr_scale = num.scr_scale if hasattr(num, "scr_scale") else 1.0
        up_scr /= scr_scale
        if up_scr == 1.0:
            # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
            # return num
            return typing.cast(Scalable, num)
        w = int(num.GetWidth() * up_scr)
        h = int(num.GetHeight() * up_scr)
        if w <= 0 or h <= 0:
            # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
            # return num
            return typing.cast(Scalable, num)
        wxbmp = num
        if bmpdepthis1:
            img = util.convert_to_image(wxbmp)
        else:
            img = wxbmp.ConvertToImage()
        img = _s_impl(img, up_scr)
        wxbmp = img.ConvertToBitmap()

        if bmpdepthis1:
            wxbmp.bmpdepthis1 = bmpdepthis1
        if maskcolour:
            wxbmp.maskcolour = maskcolour
        # BUG: Returning Any from function declared to return "Surface" (mypy 0.790)
        # return wxbmp
        return typing.cast(Scalable, wxbmp)

    else:
        assert False, str(num)


dpi_level = 1


def ppis(num: Scalable) -> Scalable:
    return _s_impl(num, float(dpi_level))


def main() -> None:
    pass


if __name__ == "__main__":
    main()
