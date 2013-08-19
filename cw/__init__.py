#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import dialog
import debug
import sprite


# CWPyThread
cwpy = None

# アプリケーション情報
APP_VERSION = (0, 1, 2, 1)
APP_NAME = "CardWirthPy"

# サイズ
SIZE_SCR = (640, 480)
SIZE_GAME = (632, 453)
SIZE_AREA = (632, 420)
SIZE_CARDIMAGE = (74, 94)
SIZE_BOOK = (460, 280)
SIZE_BILL = (400, 370)

# 特殊エリアのID
AREAS_SP = (0, -1, -2, -3, -4, -5)
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

# 対応拡張子
EXTS_IMG = (".bmp", ".jpg", ".jpeg", ".png", ".gif", ".pcx", ".tif", ".xpm")
EXTS_MSC = (".mid", ".midi", ".mp3", ".ogg")
EXTS_SND = (".wav", ".wave", ".ogg")

# 互換性マークのインデックス
HINT_MESSAGE = 0    # メッセージ表示時の話者(キャストまたはカード)
HINT_CARD = 1       # 使用中のカード
HINT_AREA = 2       # エリア・バトル・パッケージ
HINT_SCENARIO = 3   # シナリオ本体

# 画面の拡大率
UP_SCR = 1

def s(num):
    if isinstance(num, tuple) and len(num) == 3 and num[2] is None:
        # スケール情報無し
        return s(num[:2])

    if UP_SCR == 1 and not (isinstance(num, tuple) and len(num) == 3):
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
        return int(num * UP_SCR)

    elif isinstance(num, pygame.Rect):
        # pygameの矩形情報
        if len(num) == 4:
            x = int(num[0] * UP_SCR)
            y = int(num[1] * UP_SCR)
            w = int(num[2] * UP_SCR)
            h = int(num[3] * UP_SCR)
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
                size = s(num[1])
                return pygame.transform.scale(bmp, size)
            else:
                # スケール情報の無いpygame.Surface(単純拡大)
                return s(bmp)
        elif isinstance(num[0], wx.Image):
            img = num[0]
            if img.GetWidth() <= 0 or img.GetHeight() <= 0:
                return bmp
            if scaleinfo:
                # スケール情報のあるwx.Image
                # TODO scaleinfo
                size = s(num[1])
                return img.Rescale(size[0], size[1], wx.IMAGE_QUALITY_NORMAL)
            else:
                # スケール情報の無いwx.Image(単純拡大)
                return s(img)
        elif isinstance(num[0], wx.Bitmap):
            bmp = num[0]
            if bmp.GetWidth() <= 0 or bmp.GetHeight() <= 0:
                return bmp
            # wx.Bitmap
            size = num[1]
            return s((bmp.ConvertToImage(), size, scaleinfo)).ConvertToBitmap()

        elif len(num) == 4:
            # 矩形
            x = int(num[0] * UP_SCR)
            y = int(num[1] * UP_SCR)
            w = int(num[2] * UP_SCR)
            h = int(num[3] * UP_SCR)
            return (x, y, w, h)
        elif len(num) == 2:
            # 座標
            x = int(num[0] * UP_SCR)
            y = int(num[1] * UP_SCR)
            return (x, y)

    elif isinstance(num, pygame.Surface):
        # スケール情報の無いpygame.Surface(単純拡大)
        w = int(num.get_width() * UP_SCR)
        h = int(num.get_height() * UP_SCR)
        if w <= 0 or h <= 0:
            return num
        size = (w, h)
        return pygame.transform.scale(num, size)

    elif isinstance(num, wx.Image):
        # スケール情報の無いwx.Image(単純拡大)
        w = int(num.GetWidth() * UP_SCR)
        h = int(num.GetHeight() * UP_SCR)
        if w <= 0 or h <= 0:
            return num
        return num.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)

    elif isinstance(num, wx.Bitmap):
        # スケール情報の無いwx.Bitmap(単純拡大)
        img = num.ConvertToImage()
        w = int(img.GetWidth() * UP_SCR)
        h = int(img.GetHeight() * UP_SCR)
        if w <= 0 or h <= 0:
            return num
        img = img.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
        return img.ConvertToBitmap()

    return num

def main():
    pass

if __name__ == "__main__":
    main()

