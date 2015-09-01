#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import wx
import pygame

import util
import battle
import yadodb
import data
import dice
import effectmotion
import event
import eventhandler
import eventrelay
import features
import scenariodb
import setting
import skin
import animation
import thread
import header
import image
import imageretouch
import frame
import deck
import character
import effectbooster
import content
import xmlcreater
import bassplayer
import binary

import dialog
import debug
import sprite

import argparser

# CWPyThread
cwpy = None

tempdir_init = u"Data/Temp/Global"
tempdir = tempdir_init

# アプリケーション情報
APP_VERSION = (0, 12, "4 Alpha 1")
APP_NAME = "CardWirthPy"

# CardWirthの標準文字コード
if sys.platform == "win32":
    MBCS = "mbcs"
else:
    MBCS = "ms932"

# コール系イベントの再期限界回数
LIMIT_RECURSE = 1000000000

# サイズ
SIZE_SCR = (640, 480)
SIZE_GAME = (632, 453)
SIZE_AREA = (632, 420)
SIZE_CARDIMAGE = (74, 94)
SIZE_BOOK = (460, 280)
SIZE_BILL = (400, 370)
RECT_STATUSBAR = (0, 420, 632, 33)

# 特殊エリアのID
AREAS_SP = (-1, -2, -3, -4, -5)
AREAS_TRADE = (-1, -2, -5)       # カード移動操作エリア
AREA_TRADE1 = -1                 # カード移動操作エリア(宿・パーティなし時)
AREA_TRADE2 = -2                 # カード移動操作エリア(宿・パーティロード中時)
AREA_TRADE3 = -5                 # カード移動操作エリア(キャンプエリア)
AREA_BREAKUP = -3                # パーティ解散エリア
AREA_CAMP = -4                   # キャンプエリア

# カードポケットのインデックス
POCKET_SKILL = 0
POCKET_ITEM = 1
POCKET_BEAST = 2

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
DEFAULT_SOUNDFONT = "Data/SoundFont/TimGM6mb.sf2"

# ゲーム画面構築の拡大率
UP_SCR = 1
# ゲーム画面・ダイアログ描画時の拡大率(UP_SCRが1の時の値)
UP_WIN = 1

# wxPythonでイメージをスムージングしつつサイズ変更する際に用いるフラグ
if 3 <= wx.VERSION[0]:
    RESCALE_QUALITY = wx.IMAGE_QUALITY_BILINEAR
else:
    RESCALE_QUALITY = wx.IMAGE_QUALITY_HIGH


# 起動オプション
_argparser = argparser.ArgParser(appname=APP_NAME,
    description=u"%s %s\n\nオープンソースのCardWirthエンジン" % (APP_NAME, ".".join(map(lambda a: str(a), APP_VERSION))))
_argparser.add_argument("-h", type=bool, nargs=0,
    help=u"このメッセージを表示して終了します。", arg2="--help")
_argparser.add_argument("-debug", type=bool, nargs=0,
    help=u"デバッグモードで起動します。")
_argparser.add_argument("-yado", type=str, nargs=1, default="",
    help=u"起動と同時に<YADO>のパスにある宿を読み込みます。")
_argparser.add_argument("-party", type=str, nargs=1, default="",
    help=u"起動と同時に<PARTY>のパスにあるパーティを読み込みます。\n"
       + u"-yadoと同時に指定しなかった場合は無視されます。")
_argparser.add_argument("-scenario", type=str, nargs=1, default="",
    help=u"起動と同時に<SCENARIO>のパスにあるシナリオを開始します。\n"
       + u"-yado及び-partyと同時に指定しなかった場合は無視されます。")
OPTIONS = _argparser.parse_args(sys.argv[1:])
if OPTIONS.help:
    _argparser.print_help()
    sys.exit(0)

_encoding = sys.getfilesystemencoding()
OPTIONS.yado = OPTIONS.yado.decode(_encoding)
OPTIONS.party = OPTIONS.party.decode(_encoding)
OPTIONS.scenario = OPTIONS.scenario.decode(_encoding)

# 起動オプション(スキン自動生成元)
SKIN_CONV_ARGS = []
for arg in OPTIONS.leftovers:
    if os.path.isfile(arg) and os.path.splitext(arg)[1].lower() == ".exe":
        SKIN_CONV_ARGS.append(arg)
        sys.argv.remove(arg)


def wins(num):
    """numを実際の表示サイズに変換する。
    num: int or 座標(x,y) or 矩形(x,y,width,height)
         or pygame.Surface or pygame.Bitmap or pygame.Image
    """
    return _s_impl(num, UP_WIN)

def s(num):
    """numを描画サイズに変換する。
    num: int or 座標(x,y) or 矩形(x,y,width,height)
         or pygame.Surface or pygame.Bitmap or pygame.Image
    """
    return _s_impl(num, UP_SCR)

def scr2win_s(num):
    """numを描画サイズから表示サイズに変換する。
    num: int or 座標(x,y) or 矩形(x,y,width,height)
         or pygame.Surface or pygame.Bitmap or pygame.Image
    """
    if UP_WIN == UP_SCR:
        return _s_impl(num, 1)
    else:
        return _s_impl(num, float(UP_WIN) / UP_SCR)

def win2scr_s(num):
    """numを表示サイズから描画サイズに変換する。
    num: int or 座標(x,y) or 矩形(x,y,width,height)
         or pygame.Surface or pygame.Bitmap or pygame.Image
    """
    if UP_WIN == UP_SCR:
        return _s_impl(num, 1)
    else:
        return _s_impl(num, float(UP_SCR) / UP_WIN)

def _s_impl(num, up_scr):
    if isinstance(num, tuple) and len(num) == 3 and num[2] is None:
        # スケール情報無し
        return _s_impl(num[:2], up_scr)

    if up_scr == 1 and not (isinstance(num, tuple) and len(num) == 3):
        # 拡大率が1倍で、スケール情報も無い
        if isinstance(num, tuple) and len(num) == 2:
            if (isinstance(num[0], pygame.Surface) or\
                isinstance(num[0], wx.Bitmap) or\
                isinstance(num[0], wx.Image)):
                # 画像はそのままのサイズで表示
                return num[0]
        # 座標等はそのまま返す
        return num

    if isinstance(num, int) or isinstance(num, float):
        # 単純な数値(座標やサイズ)
        return int(num * up_scr)

    elif isinstance(num, pygame.Rect):
        # pygameの矩形情報
        if len(num) == 4:
            x = int(num[0] * up_scr)
            y = int(num[1] * up_scr)
            w = int(num[2] * up_scr)
            h = int(num[3] * up_scr)
            return pygame.Rect(x, y, w, h)

    elif isinstance(num, tuple):
        if len(num) == 3:
            scaleinfo = num[2]
        else:
            scaleinfo = None

        if isinstance(num[0], pygame.Surface):
            bmp = num[0]
            if bmp.get_width() <= 0 or bmp.get_width() <= 0:
                return bmp
            if scaleinfo:
                # スケール情報のあるpygame.Surface
                # TODO scaleinfo
                size = _s_impl(num[1], up_scr)
                if size[0] % num[1] == 0:
                    return pygame.transform.scale(bmp, size)
                else:
                    if not (bmp.get_flags() & pygame.locals.SRCALPHA) and bmp.get_colorkey():
                        bmp = bmp.convert_alpha()
                    return image.smoothscale(bmp, size)
            else:
                # スケール情報の無いpygame.Surface(単純拡大)
                return _s_impl(bmp, up_scr)
        elif isinstance(num[0], wx.Image):
            img = num[0]
            if img.GetWidth() <= 0 or img.GetHeight() <= 0:
                return bmp
            if scaleinfo:
                # スケール情報のあるwx.Image
                # TODO scaleinfo
                size = _s_impl(num[1], up_scr)
                if size[0] % num[1] == 0:
                    return img.Rescale(size[0], size[1], wx.IMAGE_QUALITY_NORMAL)
                else:
                    if not img.HasAlpha():
                        img.InitAlpha()
                    return img.Rescale(size[0], size[1], RESCALE_QUALITY)
            else:
                # スケール情報の無いwx.Image(単純拡大)
                return _s_impl(img, up_scr)
        elif isinstance(num[0], wx.Bitmap):
            bmp = num[0]
            if bmp.GetWidth() <= 0 or bmp.GetHeight() <= 0:
                return bmp
            # wx.Bitmap
            return _s_impl((bmp.ConvertToImage(), num[1]), up_scr).ConvertToBitmap()

        elif len(num) == 4:
            # 矩形
            x = int(num[0] * up_scr)
            y = int(num[1] * up_scr)
            w = int(num[2] * up_scr)
            h = int(num[3] * up_scr)
            return (x, y, w, h)
        elif len(num) == 2:
            # 座標
            x = int(num[0] * up_scr)
            y = int(num[1] * up_scr)
            return (x, y)

    elif isinstance(num, pygame.Surface):
        # スケール情報の無いpygame.Surface(単純拡大)
        w = int(num.get_width() * up_scr)
        h = int(num.get_height() * up_scr)
        if w <= 0 or h <= 0:
            return num
        size = (w, h)
        if up_scr % 1 == 0:
            return pygame.transform.scale(num, size)
        else:
            if not (num.get_flags() & pygame.locals.SRCALPHA) and num.get_colorkey():
                num = num.convert_alpha()
            return image.smoothscale(num, size)

    elif isinstance(num, wx.Image):
        # スケール情報の無いwx.Image(単純拡大)
        w = int(num.GetWidth() * up_scr)
        h = int(num.GetHeight() * up_scr)
        if w <= 0 or h <= 0:
            return num

        if up_scr % 1 == 0:
            return num.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
        else:
            if not num.HasAlpha():
                num.InitAlpha()
            return num.Rescale(w, h, RESCALE_QUALITY)

    elif isinstance(num, wx.Bitmap):
        # スケール情報の無いwx.Bitmap(単純拡大)
        w = int(num.GetWidth() * up_scr)
        h = int(num.GetHeight() * up_scr)
        if w <= 0 or h <= 0:
            return num
        return _s_impl(num.ConvertToImage(), up_scr).ConvertToBitmap()

    return num

def main():
    pass

if __name__ == "__main__":
    main()

