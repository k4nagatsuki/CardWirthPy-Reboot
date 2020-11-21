#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes

from typing import List, Optional, Tuple


"""色を反転する。
"""
def to_negative(buf: bytearray, size: Tuple[int, int]) -> None: ...


"""モザイクをかける。
value: モザイクをかける度合い(0～255)
"""
def add_mosaic(buf: bytes, size: Tuple[int, int], value: int) -> bytes: ...


"""二値化する。
value: 閾値(-1～255)。-1の場合はbasecolor以外が黒になる
basecolor: 閾値が-1の時に使用され、この色以外が黒になる
"""
def to_binaryformat(buf: bytes, size: Tuple[int, int], value: int, basecolor: Tuple[int, int, int]) -> bytes: ...


"""ノイズを入れる。
value: ノイズの度合い(-1～255)
colornoise: カラーノイズか否か
"""
def add_noise(buf: bytes, size: Tuple[int, int], value: int, colornoise: bool = False) -> bytes: ...


"""RGB入れ替えを行う。
colormodel: "r", "g", "b"を組み合わせた文字列。
"""
def exchange_rgbcolor(buf: bytes, size: Tuple[int, int], colormodel: str) -> bytes: ...


"""グレイスケール化ないし褐色系の画像に変換する。
image: 対象イメージ
"""
def to_sepiatone(buf: bytes, size: Tuple[int, int], color: Tuple[int, int, int]) -> bytes: ...


"""ピクセル拡散を行う。
"""
def spread_pixels(buf: bytes, size: Tuple[int, int]) -> bytes: ...


"""各種のフィルターを適用する。
"""
def filter(buf: bytes, size: Tuple[int, int],
           weights: Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]], offset: int,
           div: int) -> bytes: ...


"""色領域を縁取りする。
"""
def bordering(buf: bytes, size: Tuple[int, int]) -> List[int]: ...


"""CardWirth 1.50の挙動に合わせて加算合成を行う。
"""
def blend_add_1_50(buf: bytes, sbuf: bytes) -> bytes: ...


"""CardWirth 1.50の挙動に合わせて減算合成を行う。
"""
def blend_sub_1_50(buf: bytes, sbuf: bytes) -> bytes: ...


"""CardWirth 1.50の挙動に合わせて乗算合成を行う。
"""
def blend_mult_1_50(buf: bytes, sbuf: bytes) -> bytes: ...


"""通常時のボタン画像からdisabled用の画像を作る。
RGB値の範囲を 0～255 から min～max に変更する。
"""
def to_disabledimage(buf: bytearray, size: Tuple[int, int]) -> None: ...


"""イメージに明るさを加える。
"""
def add_lightness(buf: bytearray, size: Tuple[int, int], lightness: int) -> None: ...


"""Windows BitmapのRLE4データをデコードする。
"""
def decode_rle4data(data: bytes, h: int, bpl: int) -> bytes: ...


"""RGBA列の中に0以外のα値があるかを返す。
"""
def has_alphabmp32(buf: bytes) -> bool: ...


"""RGBA列の中に255以外のα値があるかを返す。
"""
def has_alpha(buf: bytes) -> bool: ...


"""alpha/255分まで、RGBA列のアルファ値を減少させる。"""
def mul_alphaonly(buf: bytearray, alpha: int) -> None: ...


"""RGBA列のAND合成を行う。
"""
def blend_and(buf: bytes, size: Tuple[int, int], sbuf: bytes) -> bytes: ...


"""wincolourの領域に対してRGBA列のAND合成を行う。
"""
def blend_and_msg(buf: bytes, size: Tuple[int, int], sbuf: bytes, wincolour: Tuple[int, int, int, int]) -> bytes: ...


"""RGB列のAND合成を行う。
"""
def blend_and_rgb(dbuf: bytearray, size: Tuple[int, int], buf: bytes) -> None: ...


_FontInfo = ctypes.c_void_p


"""フォント情報を生成する。
不要になった場合は必ずfont_del()で削除する必要がある。
"""
def font_new(face: bytes, pixels: int, bold: bool, italic: bool) -> Optional[_FontInfo]: ...


"""フォント情報を削除する。
"""
def font_del(font: _FontInfo) -> None: ...


"""フォントを太字にする。
"""
def font_bold(font: _FontInfo, v: bool) -> None: ...


"""フォントを斜体にする。
"""
def font_italic(font: _FontInfo, v: bool) -> None: ...


"""フォントを下線付きにする。
"""
def font_underline(font: _FontInfo, v: bool) -> None: ...


"""行の高さを返す。
"""
def font_height(font: _FontInfo) -> int: ...


"""文字列のサイズを返す。
"""
def font_size(font: _FontInfo, text: bytes) -> Tuple[int, int]: ...


"""文字列の実際の描画サイズを返す。
斜体の場合、傾きによって横幅が通常のサイズより増える可能性がある。
"""
def font_imagesize(font: _FontInfo, text: bytes, antialias: bool) -> Tuple[int, int]: ...


"""文字列を描画したイメージを返す。
イメージのサイズはfont_imagesize(font, text, antialias)の結果と同一になる。
"""
def font_render(font: _FontInfo, text: bytes, antialias: bool, colour: Tuple[int, int, int]) -> bytes: ...
