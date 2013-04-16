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

import dialog
import debug
import sprite


# CWPyThread
cwpy = None

# アプリケーション情報
APP_VERSION = (0, 1, 2)
APP_NAME = "CardWirthPy"

# サイズ
SIZE_SCR = (640, 480)
SIZE_GAME = (632, 453)
SIZE_AREA = (632, 420)

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

def s(size_or_pos_or_image):
    if UP_SCR == 1:
        return size_or_pos_or_image
    elif isinstance(size_or_pos_or_image, int):
        return size_or_pos_or_image * UP_SCR
    elif isinstance(size_or_pos_or_image, pygame.Rect):
        if len(size_or_pos_or_image) == 4:
            x = size_or_pos_or_image[0] * UP_SCR
            y = size_or_pos_or_image[1] * UP_SCR
            w = size_or_pos_or_image[2] * UP_SCR
            h = size_or_pos_or_image[3] * UP_SCR
            return pygame.Rect(x, y, w, h)
    elif isinstance(size_or_pos_or_image, tuple):
        if len(size_or_pos_or_image) == 4:
            x = size_or_pos_or_image[0] * UP_SCR
            y = size_or_pos_or_image[1] * UP_SCR
            w = size_or_pos_or_image[2] * UP_SCR
            h = size_or_pos_or_image[3] * UP_SCR
            return (x, y, w, h)
        elif len(size_or_pos_or_image) == UP_SCR:
            x = size_or_pos_or_image[0] * UP_SCR
            y = size_or_pos_or_image[1] * UP_SCR
            return (x, y)
    elif isinstance(size_or_pos_or_image, pygame.Surface):
        w = size_or_pos_or_image.get_width() * UP_SCR
        h = size_or_pos_or_image.get_height() * UP_SCR
        size = (w, h)
        return pygame.transform.scale(size_or_pos_or_image, size)
    elif isinstance(size_or_pos_or_image, wx.Bitmap):
        img = size_or_pos_or_image.ConvertToImage()
        w = img.GetWidth() * UP_SCR
        h = img.GetHeight() * UP_SCR
        img = img.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
        return img.ConvertToBitmap()
    return size_or_pos_or_image

def ds(num):
    if UP_SCR == 1:
        return num
    return num / UP_SCR

def main():
    pass

if __name__ == "__main__":
    main()

