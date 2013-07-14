#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import stat
import shutil
import re
import time
import threading
import struct
import zipfile
import operator
import pythoncom
import threading
import hashlib
import subprocess
import StringIO
import io

if sys.platform == "win32":
    import win32com.client
    import ctypes

import wx
import pygame
from pygame.locals import *

import cw
import cw.binary.image


#-------------------------------------------------------------------------------
#　汎用クラス
#-------------------------------------------------------------------------------

class MusicInterface(object):
    def __init__(self):
        self.path = ""
        self.fpath = ""

    def play(self, path, updatepredata=True):
        self._play(path, updatepredata)

    def _play(self, path, updatepredata=True):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self._play, path, updatepredata)
            return

        assert threading.currentThread() == cw.cwpy
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        fpath = self.get_path(path)
        self.path = path
        if not pygame.mixer:
            return

        if not os.path.isfile(fpath):
            self.stop()
        else:
            assert threading.currentThread() == cw.cwpy

            self.set_volume()
            if self.fpath <> fpath:
                load_bgm(fpath)

                rpath = "DefReset" + cw.cwpy.rsrc.ext_bgm
                rpath = join_paths(cw.cwpy.setting.skindir, "Bgm", rpath)
                if os.path.normcase(fpath) == os.path.normcase(rpath):
                    # FIXME: DefReset.midを繰り返し流すとシステムが不安定になる
                    pygame.mixer.music.play(0)
                elif os.path.splitext(fpath)[1].lower() == ".mp3":
                    # 互換動作: 1.28以前はMP3がループ再生されない
                    if cw.cwpy.sct.lessthan("1.28", cw.cwpy.sdata.get_versionhint()):
                        pygame.mixer.music.play(0)
                    else:
                        pygame.mixer.music.play(-1)
                else:
                    pygame.mixer.music.play(-1)
            self.fpath = fpath
            self.path = path

        if updatepredata and cw.cwpy.pre_battleareadata:
            areaid, bgmpath, battlebgmpath = cw.cwpy.pre_battleareadata
            bgmpath = path
            cw.cwpy.pre_battleareadata = (areaid, bgmpath, battlebgmpath)

    def stop(self):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self.stop)
            return

        if not pygame.mixer:
            return

        assert threading.currentThread() == cw.cwpy
        pygame.mixer.music.stop()
        self.fpath = ""
        self.path = ""
        # pygame.mixer.musicで読み込んだ音楽ファイルを解放する
        path = "DefReset" + cw.cwpy.rsrc.ext_bgm
        path = join_paths(cw.cwpy.setting.skindir, "Bgm", path)
        load_bgm(path)

    def set_volume(self, volume=None):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self.set_volume, volume)
            return

        if not pygame.mixer:
            return

        if volume is None:
            ext = os.path.splitext(self.path)[1].lower()

            if ext == ".mid" or ext == ".midi":
                volume = cw.cwpy.setting.vol_midi * cw.cwpy.setting.vol_bgm
            else:
                volume = cw.cwpy.setting.vol_bgm

        assert threading.currentThread() == cw.cwpy
        pygame.mixer.music.set_volume(volume)

    def get_path(self, path):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.areaid < 0:
            path = join_paths(cw.cwpy.sdata.scedir, path)
        else:
            path = join_paths(cw.cwpy.skindir, path)

        if not os.path.isfile(path):
            fname = os.path.splitext(os.path.basename(path))[0]
            fname = fname + cw.cwpy.rsrc.ext_bgm
            path = join_paths(cw.cwpy.skindir, "Bgm", fname)

        return path

class SoundInterface(object):
    def __init__(self, sound=None):
        self._sound = sound

    def play(self, from_scenario=False):
        if self._sound:
            if sys.platform == "win32" and isinstance(self._sound, (str, unicode)):
                if threading.currentThread() == cw.cwpy:
                    cw.cwpy.frame.exec_func(self.play, from_scenario)
                    return
                if from_scenario:
                    name = "cwsnd1"
                else:
                    name = "cwsnd2"

                mciSendStringW = ctypes.windll.winmm.mciSendStringW
                mciSendStringW(u"stop %s" % (name), 0, 0, 0)
                mciSendStringW(u"close %s" % (name), 0, 0, 0)
                mciSendStringW(u'open "%s" alias %s' % (self._sound, name), 0, 0, 0)
                volume = int(cw.cwpy.setting.vol_sound * 1000)
                mciSendStringW(u"setaudio %s volume to %s" % (name, volume), 0, 0, 0)
                mciSendStringW(u"play %s" % (name), 0, 0, 0)
            else:
                if threading.currentThread() <> cw.cwpy:
                    cw.cwpy.exec_func(self.play, from_scenario)
                    return
                assert threading.currentThread() == cw.cwpy
                if from_scenario:
                    chan = pygame.mixer.Channel(0)
                else:
                    chan = pygame.mixer.Channel(1)

                self._sound.set_volume(cw.cwpy.setting.vol_sound)
                chan.stop()
                chan.play(self._sound)

#-------------------------------------------------------------------------------
#　汎用関数
#-------------------------------------------------------------------------------

def init(size_noscale=None, title="", fullscreen=False):
    """pygame初期化。"""
    size = cw.s(size_noscale)
    pygame.mixer.pre_init(22050, -16, 2, 1024)
    pygame.init()
    flags = 0
    if fullscreen:
        flags = FULLSCREEN
    scr = pygame.display.set_mode(size, flags)
    clock = pygame.time.Clock()

    if title:
        pygame.display.set_caption(title)

    pygame.mixer.set_num_channels(2)
    pygame.event.set_blocked(None)
    pygame.event.set_allowed([KEYDOWN, KEYUP, MOUSEBUTTONDOWN, MOUSEBUTTONUP, USEREVENT])
    return scr, clock

def convert_maskpos(maskpos, width, height):
    """maskposが座標ではなくキーワード"center"または"right"
    であった場合、それぞれ画像の中央、右上の座標を返す。
    """
    if isinstance(maskpos, str):
        if maskpos == "center":
            maskpos = (width / 2, height / 2)
        elif maskpos == "right":
            maskpos = (width - 1, 0)
        else:
            raise Exception("Invalid maskpos: %s" % (maskpos))
    return maskpos

def load_image(path, mask=False, maskpos=(0, 0), f=None):
    """pygame.Surface(読み込めなかった場合はNone)を返す。
    path: 画像ファイルのパス。
    mask: True時、(0,0)のカラーを透過色に設定する。透過画像の場合は無視される。
    """
    try:
        if f:
            image = pygame.image.load(f, path)
        elif cw.binary.image.path_is_code(path):
            data = cw.binary.image.code_to_data(path)
            #return pygame.Surface((0, 0)).convert()
            with io.BytesIO(data) as f:
                image = pygame.image.load(f)
        else:
            if not os.path.isfile(path):
                return pygame.Surface((0, 0)).convert()
            with io.BufferedReader(io.FileIO(path)) as f:
                image = pygame.image.load(f)
    except:
        print u"画像が読み込めません", path
        return pygame.Surface((0, 0)).convert()

    # アルファチャンネルを持った透過画像を読み込んだ場合は
    # SRCALPHA(0x00010000)のフラグがONになっている
    if image.get_flags() & SRCALPHA:
        image = image.convert_alpha()
    else:
        imageb = image
        image = image.convert()

        # GIFなどアルファチャンネルを持たない透過画像を読み込んだ場合は
        # すでにマスクカラーが指定されているので注意
        if mask and image.get_colorkey():
            # 255色GIFなどでパレットに存在しない色が
            # マスク色に設定されている事があるので、
            # その場合は通常通り左上の色をマスク色とする
            # 将来、もしこの処理の結果問題が起きた場合は
            # このif文以降の処理を削除する必要がある
            if imageb.get_bitsize() <= 8:
                mask = image.get_masks()
                maskok = False
                for pixel in imageb.get_palette()[:255]:
                    if pixel == mask:
                        maskok = True
                        break
                if not maskok:
                    maskpos = convert_maskpos(maskpos, image.get_width(), image.get_height())
                    image.set_colorkey(image.get_at(maskpos), RLEACCEL)
        elif mask and not image.get_colorkey():
            maskpos = convert_maskpos(maskpos, image.get_width(), image.get_height())
            image.set_colorkey(image.get_at(maskpos), RLEACCEL)

    return image

def get_imageext(b):
    """dataが画像であれば対応する拡張子を返す。"""
    if 22 < len(b) and 'B' == b[0] and 'M' == b[1]:
        return ".bmp"
    if 25 <= len(b) and 0x89 == b[0] and 'P' == b[1] and 'N' == b[2] and 'G' == b[3]:
        return ".png"
    if 10 <= len(b) and 'G' == b[0] and 'I' == b[1] and 'F' == b[2]:
        return ".gif"
    if 6 <= len(b) and 0xFF == b[0] and 0xD8 == b[1]:
        return ".jpg"
    if 10 <= len(b):
        if 'M' == b[0] and 'M' == b[1] and 42 == b[3]:
            return ".tiff"
        elif 'I' == b[0] and 'I' == b[1] and 42 == b[2]:
            return ".tiff"
    return ""

def get_facepaths(sexcoupon, agecoupon, rel=False):
    """sexとageに対応したFaceディレクトリ内の画像パスをlistで返す。
    sexcoupon: 性別クーポン。
    agecoupon: 年代クーポン。
    rel: TrueならFaceディレクトリからの相対パスで返す。
    """
    sex = ""
    for f in cw.cwpy.setting.sexes:
        if sexcoupon == u"＿" + f.name:
            sex = f.subname

    age = ""
    for f in cw.cwpy.setting.periods:
        if agecoupon == u"＿" + f.name:
            age = f.abbr

    dpaths = []
    facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")

    # 性別・年代限定
    if sex and age:
        dpath = sex + "-" + age
        dpaths.append(dpath)
    # 性別限定
    if sex:
        dpath = sex
        dpaths.append(dpath)
    # 年代限定
    if age:
        dpath = "Common-" + age
        dpaths.append(dpath)
    # 汎用
    dpath = "Common"
    dpaths.append(dpath)

    imgpaths = []

    for dpath in dpaths:
        dpath2 = cw.util.join_paths(facedir, dpath)
        if not os.path.isdir(dpath2):
            continue
        for name in os.listdir(dpath2):
            path = cw.util.join_paths(dpath2, name)

            lpath = path.lower()
            if os.path.isfile(path):
                for ext in cw.EXTS_IMG:
                    if lpath.endswith(ext):
                        if rel:
                            imgpaths.append(cw.util.join_paths(dpath, name))
                        else:
                            imgpaths.append(path)
                        break

    return imgpaths

def load_bgm(path):
    """Pathの音楽ファイルをBGMとして読み込む。
    リピートして鳴らす場合は、cw.audio.MusicInterface参照。
    path: 音楽ファイルのパス。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()
    if not pygame.mixer or not os.path.isfile(path):
        return

    try:
        assert threading.currentThread() == cw.cwpy
        f = io.BufferedReader(io.FileIO(path))
        pygame.mixer.music.load(f)
    except:
        print u"BGMが読み込めません", path
        return

def load_sound(path):
    """効果音ファイルを読み込み、SoundInterfaceを返す。
    読み込めなかった場合は、無音で再生するSoundInterfaceを返す。
    path: 効果音ファイルのパス。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()
    if not pygame.mixer or not os.path.isfile(path):
        return SoundInterface()

    try:
        assert threading.currentThread() == cw.cwpy
        if sys.platform == "win32" and (path.lower().endswith(".wav") or\
                                        path.lower().endswith(".mp3")):
            sound = SoundInterface(path)
        else:
            with io.BufferedReader(io.FileIO(path)) as f:
                sound = pygame.mixer.Sound(f)
            sound = SoundInterface(sound)
    except:
        print u"サウンドが読み込めません", path
        return SoundInterface()

    return sound

def sort_by_attr(seq, attr):
    """破壊的にオブジェクトの属性でソートする。
    seq: リスト
    attr: 属性名
    """
    return seq.sort(key=operator.attrgetter(attr))

def sorted_by_attr(seq, attr):
    """非破壊的にオブジェクトの属性でソートする。
    seq: リスト
    attr: 属性名
    """
    return sorted(seq, key=operator.attrgetter(attr))

def new_order(seq, mode=1):
    """order属性を持つアイテムのlistを
    走査して新しいorderを返す。
    必要であれば、seq内のorderを振り直す。
    mode: 0=最大order。1=最小order。orderの振り直しが発生する
    """
    if mode == 0:
        order = -1
        for item in seq:
            order = max(item.order, order)
        return order + 1
    else:
        for item in seq:
            item.order += 1
        return 0

def join_paths(*paths):
    """パス結合。ディレクトリの区切り文字はプラットホームに関わらず"/"固定。
    *paths: パス結合する文字列
    """
    return "/".join(paths).replace("\\", "/").strip("/")

def str2bool(s):
    """特定の文字列をbool値にして返す。
    s: bool値に変換する文字列(true, false, 1, 0など)。
    """
    if isinstance(s, bool):
        return s
    else:
        s = s.lower()

        if s == "true":
            return True
        elif s == "false":
            return False
        elif s == "1":
            return True
        elif s == "0":
            return False
        else:
            raise ValueError("%s is incorrect value!" % (s))

def numwrap(n, min, max):
    """最小値、最大値の範囲内でnの値を返す。
    n: 範囲内で調整される値。
    min: 最小値。
    max: 最大値。
    """
    if n < min:
        n = min
    elif n > max:
        n = max

    return n

def get_truetypefontname(path):
    """引数のTrueTypeFontファイルを読み込んで、フォントネームを返す。
    ref http://mail.python.org/pipermail/python-list/2008-September/508476.html
    path: TrueTypeFontファイルのパス。
    """
    #customize path
    with open(path, "rb") as f:

        #header
        shead= struct.Struct( ">IHHHH" )
        fhead= f.read( shead.size )
        dhead= shead.unpack_from( fhead, 0 )

        #font directory
        stable= struct.Struct( ">4sIII" )
        ftable= f.read( stable.size* dhead[ 1 ] )
        for i in xrange( dhead[1] ): #directory records
            dtable= stable.unpack_from(
                    ftable, i* stable.size )
            if dtable[0]== "name": break
        assert dtable[0]== "name"

        #name table
        f.seek( dtable[2] ) #at offset
        fnametable= f.read( dtable[3] ) #length
        snamehead= struct.Struct( ">HHH" ) #name table head
        dnamehead= snamehead.unpack_from( fnametable, 0 )

        sname= struct.Struct( ">HHHHHH" )
        fontname = ""

        for i in xrange( dnamehead[1] ): #name table records
            dname= sname.unpack_from(fnametable, snamehead.size+ i* sname.size )

            if dname[3]== 4: #key == 4: "full name of font"
                s= struct.unpack_from(
                        '%is'% dname[4], fnametable,
                        dnamehead[2]+ dname[5] )[0]
                if dname[:3] == (1, 0, 0):
                    fontname = s
                elif dname[:3] == (3, 1, 1033):
                    s = s.split("\x00")
                    fontname = "".join(s)

    return fontname

def get_md5(path):
    """MD5を使ったハッシュ値を返す。
    path: ハッシュ値を求めるファイルのパス。
    """
    m = hashlib.md5()
    with open(path, "rb") as f:

        while True:
            data = f.read(32768)

            if not data:
                break

            m.update(data)

    return m.hexdigest()

def change_cursor(name="arrow"):
    """マウスカーソルを変更する。
    name: 変更するマウスカーソルの名前。
    (arrow, diamond, broken_x, tri_left, tri_right, mouse)"""
    if name == "arrow":
        pygame.mouse.set_cursor(*pygame.cursors.arrow)
    elif name == "diamond":
        pygame.mouse.set_cursor(*pygame.cursors.diamond)
    elif name == "broken_x":
        pygame.mouse.set_cursor(*pygame.cursors.broken_x)
    elif name == "tri_left":
        pygame.mouse.set_cursor(*pygame.cursors.tri_left)
    elif name == "tri_right":
        pygame.mouse.set_cursor(*pygame.cursors.tri_right)
    elif name == "mouse":
        # 24x24
        s = (
          "    .#.#...........     ",
          "    .#.#.#########.     ",
          "    .#.#.#####.###.     ",
          "  .........##.####.     ",
          " .####.####.######.     ",
          ".#####.#####.#..##.     ",
          ".#####.#####.#####.     ",
          ".#####.#####.#..##.     ",
          ".#####.#####.#####.     ",
          ".#####.#####.#####.     ",
          "......#......#####.     ",
          ".###########.#####.     ",
          ".###########.#####.     ",
          ".###########.#####.     ",
          ".###########.......     ",
          ".###########.           ",
          ".###########.           ",
          " .#########.            ",
          "  .......... ... .  .   ",
          " .###.#. .#..###.#..#.  ",
          ".#....#. .#.#....###.   ",
          ".#....#...#.#....#.#.   ",
          " .###.###.#..###.#..#.  ",
          "  .........  ... .  .   ",)

        cursor = pygame.cursors.compile(s, ".", "#", "o")
        pygame.mouse.set_cursor((24, 24), (7, 7), *cursor)

    # 一度マウスポインタを画面外へ出さないと変更されない
    pos = pygame.mouse.get_pos()
    pygame.mouse.set_pos([-1, -1])
    pygame.mouse.set_pos(pos)

def number_normalization(value, fromvalue, tovalue):
    """数値を範囲内の値に正規化する。
    value: 正規化対象の数値。
    fromvalue: 範囲の最小値。
    tovalue: 範囲の最大値+1。
    """
    if 0 == tovalue:
        return value;
    if tovalue <= value or value < fromvalue:
        value -= (value / tovalue) * tovalue;
    if value < fromvalue:
        value += tovalue;
    return value;

#-------------------------------------------------------------------------------
#　ファイル操作関連
#-------------------------------------------------------------------------------

def dupcheck_plus(path, yado=True):
    """パスの重複チェック。引数のパスをチェックし、重複していたら、
    ファイル・フォルダ名の後ろに"(n)"を付加して重複を回避する。
    宿のファイルパスの場合は、"Data/Temp/Yado"ディレクトリの重複もチェックする。
    """
    if yado:
        if path.startswith("Yado"):
            temppath = path.replace("Yado", "Data/Temp/Yado", 1)
        elif path.startswith("Data/Temp/Yado"):
            temppath = path.replace("Data/Temp/Yado", "Yado", 1)
        else:
            print "宿パスの重複チェック失敗", path
            temppath = ""

    else:
        temppath = ""

    dpath, basename = os.path.split(path)
    fname, ext = os.path.splitext(basename)
    fname = cw.binary.util.check_filename(fname.strip())
    ext = ext.strip()
    basename = fname + ext
    count = 2

    while os.path.exists(path) or os.path.exists(temppath):
        basename = "%s(%d)%s" % (fname, count, ext)
        path = join_paths(dpath, basename)

        if yado:
            if path.startswith("Yado"):
                temppath = path.replace("Yado", "Data/Temp/Yado", 1)
            elif path.startswith("Data/Temp/Yado"):
                temppath = path.replace("Data/Temp/Yado", "Yado", 1)
            else:
                print "宿パスの重複チェック失敗", path
                temppath = ""

        count += 1

    return join_paths(dpath, basename)

def repl_dischar(fname):
    """
    ファイル名使用不可文字を代替文字に置換し、
    両端に空白があった場合は削除する。
    """
    d = {'\\': u'￥', '/': u'／', ':': u'：', ',': u'，', ';': u'；',
         '*': u'＊', '?': u'？','"': u'”', '<': u'＜', '>': u'＞',
         '|': u'｜','"': u'”'}

    for key, value in d.iteritems():
        fname = fname.replace(key, value)

    return fname.strip()

def check_dischar(s):
    """
    ファイル名使用不可文字を含んでいるかチェックする。
    """
    seq = ('\\', '/', ':', ',', ';', '*', '?','"', '<', '>', '|', '"')

    for i in seq:
        if s.find(i) >= 0:
            return True

    return False

def join_yadodir(path):
    """
    引数のpathを現在読み込んでいる宿ディレクトリと結合させる。
    "Data/Temp/Yado"にパスが存在すれば、そちらを優先させる。
    """
    temppath = join_paths(cw.cwpy.tempdir, path)
    yadopath = join_paths(cw.cwpy.yadodir, path)

    if os.path.exists(temppath):
        return temppath
    else:
        return yadopath

def get_yadofilepath(path):
    """"Data/Yado"もしくは"Data/Temp/Yado"のファイルパスの存在チェックをかけ、
    存在しているパスを返す。存在していない場合は""を返す。
    "Data/Temp/Yado"にパス優先。
    """
    if not cw.cwpy.ydata:
        return ""
    elif path.startswith(cw.cwpy.tempdir):
        temppath = path
        yadopath = path.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
    elif path.startswith(cw.cwpy.yadodir):
        temppath = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
        yadopath = path
    else:
        return ""

    if yadopath in cw.cwpy.ydata.deletedpaths:
        return ""
    elif os.path.isfile(temppath):
        return temppath
    elif os.path.isfile(yadopath):
        return yadopath
    else:
        return ""

def remove_temp():
    """
    "Data/Temp/Yado"を空にする。
    """
    dpath = u"Data/Temp"

    if not os.path.exists(dpath):
        os.makedirs(dpath)

    for name in os.listdir(dpath):
        if not name == "Scenario":
            path = join_paths(dpath, name)
            remove(path)

def remove(path):
    if os.path.isfile(path):
        remove_file(path)
    elif os.path.isdir(path):
        remove_tree(path)

def remove_file(path, retry=0):
    try:
        os.remove(path)
    except WindowsError, err:
        if err.errno == 13 and retry < 5:
            os.chmod(path, stat.S_IWRITE|stat.S_IREAD)
            remove_file(path, retry + 1)
        elif retry < 5:
            remove_tree(treepath, retry + 1)
        else:
            raise err

def remove_tree(treepath, retry=0):
    try:
        shutil.rmtree(treepath)
    except WindowsError, err:
        if err.errno == 13 and retry < 5:
            for dpath, dnames, fnames in os.walk(treepath):
                for dname in dnames:
                    path = join_paths(dpath, dname)
                    os.chmod(path, stat.S_IWRITE|stat.S_IREAD)

                for fname in fnames:
                    path = join_paths(dpath, fname)
                    os.chmod(path, stat.S_IWRITE|stat.S_IREAD)

            remove_tree(treepath, retry + 1)
        elif retry < 5:
            remove_tree(treepath, retry + 1)
        else:
            raise err

#-------------------------------------------------------------------------------
#　ZIPファイル関連
#-------------------------------------------------------------------------------

def compress_zip(path, zpath):
    """pathのデータをzpathで指定したzipファイルに圧縮する。
    path: 圧縮するディレクトリパス
    """
    encoding = sys.getfilesystemencoding()
    dpath = os.path.dirname(zpath)

    if dpath and not os.path.isdir(dpath):
        os.makedirs(dpath)

    z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)
    rpl_dir = path + "/"

    for dpath, dnames, fnames in os.walk(unicode(path)):
        for dname in dnames:
            fpath = join_paths(dpath, dname)
            mtime = time.localtime(os.path.getmtime(fpath))[:6]
            zname = fpath.replace(rpl_dir, "", 1) + "/"
            zinfo = zipfile.ZipInfo(zname, mtime)
            z.writestr(zinfo, "")

        for fname in fnames:
            fpath = join_paths(dpath, fname)
            zname = fpath.replace(rpl_dir, "", 1)
            z.write(fpath.encode(encoding), zname)

    z.close()
    return zpath

def decompress_zip(path, dstdir, dname="", avoiddup=False):
    """zipファイルをdstdirに解凍する。
    解凍したディレクトリのpathを返す。
    """
    try:
        z = zipfile.ZipFile(path, "r")
    except:
        return None

    if not dname:
        dname = os.path.splitext(os.path.basename(path))[0]

    dstdir = join_paths(dstdir, dname)
    dstdir = dupcheck_plus(dstdir, False)

    for zname in z.namelist():
        name = decode_zipname(zname)

        if name.endswith("/"):
            name = name.rstrip("/")
            dpath = join_paths(dstdir, name)

            if dpath and not os.path.isdir(dpath):
                os.makedirs(dpath)

        else:
            data = z.read(zname)
            fpath = join_paths(dstdir, name)
            dpath = os.path.dirname(fpath)

            if dpath and not os.path.isdir(dpath):
                os.makedirs(dpath)

            with open(fpath, "wb") as f:
                f.write(data)

    z.close()

    if avoiddup:
        # 内部にディレクトリが一つしかない場合は
        # 最上位のディレクトリに格上げする
        list = os.listdir(dstdir)
        if 1 == len(list):
            dpath = os.path.join(dstdir, list[0])
            if os.path.isdir(dpath):
                dstdir2 = dupcheck_plus(dstdir, False)
                os.rename(dstdir, dstdir2)
                os.rename(os.path.join(dstdir2, list[0]), dstdir)
                shutil.rmtree(dstdir2)

    return dstdir

def decode_zipname(name):
    if not isinstance(name, unicode):
        try:
            name = name.decode("mbcs")
        except UnicodeDecodeError:
            try:
                name = name.decode("euc-jp")
            except UnicodeDecodeError:
                try:
                    name = name.decode("utf-8")
                except UnicodeDecodeError:
                    name = name

    return name

def read_zipdata(zfile, name):
    try:
        data = zfile.read(name)
    except KeyError:
        try:
            data = zfile.read(name.encode("mbcs"))
        except KeyError:
            try:
                data = zfile.read(name.encode("euc-jp"))
            except KeyError:
                try:
                    data = zfile.read(name.encode("utf-8"))
                except KeyError:
                    data = ""

    return data

def get_elementfromzip(zpath, name, tag=""):
    with zipfile.ZipFile(zpath, "r") as z:
        data = read_zipdata(z, name)
    f = StringIO.StringIO(data)
    try:
        element = cw.data.xml2element(name, tag, file=f)
    finally:
        f.close()
    return element

def decompress_cab(path, dstdir, dname="", avoiddup=False):
    """cabファイルをdstdirに解凍する。
    解凍したディレクトリのpathを返す。
    """

    if not dname:
        dname = os.path.splitext(os.path.basename(path))[0]

    dstdir = join_paths(dstdir, dname)
    dstdir = dupcheck_plus(dstdir, False)

    try:
        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        s = "expand \"%s\" -f:* \"%s\"" % (path, dstdir)
        encoding = sys.getfilesystemencoding()
        if subprocess.call(s.encode(encoding), shell=True) <> 0:
            return None
    except Exception, ex:
        print ex
        return None

    if avoiddup:
        # 内部にディレクトリが一つしかない場合は
        # 最上位のディレクトリに格上げする
        list = os.listdir(dstdir)
        if 1 == len(list):
            dpath = os.path.join(dstdir, list[0])
            if os.path.isdir(dpath):
                dstdir2 = dupcheck_plus(dstdir, False)
                os.rename(dstdir, dstdir2)
                os.rename(os.path.join(dstdir2, list[0]), dstdir)
                shutil.rmtree(dstdir2)

    return dstdir

def cab_hasfile(cab, file):
    """CABアーカイブに指定された名前のファイルが含まれているか判定する。"""
    if not os.path.isfile(cab):
        return False

    dword = struct.Struct("<l")
    word = struct.Struct("<h")
    file = os.path.normcase(file)
    encoding = sys.getfilesystemencoding()
    try:
        with io.BufferedReader(io.FileIO(cab, "rb")) as f:
            # ヘッダ
            buf = f.read(36)
            if buf[:4] <> "MSCF":
                return False

            cofffiles = dword.unpack(buf[16:20])[0]
            cfiles = dword.unpack(buf[28:32])[0]
            f.seek(cofffiles)

            for i in xrange(cfiles):
                buf = f.read(16)
                attribs = word.unpack(buf[14:16])[0]
                name = []
                while True:
                    c = str(f.read(1))
                    if c == '\0':
                        break
                    name.append(c)
                name = "".join(name)
                _A_NAME_IS_UTF = 0x80
                if not (attribs & _A_NAME_IS_UTF):
                    name = unicode(name, encoding);
                if file == os.path.normcase(os.path.basename(name)):
                    return True
    except Exception, ex:
        print ex
    return False

#-------------------------------------------------------------------------------
#　テキスト操作関連
#-------------------------------------------------------------------------------

def encodewrap(s):
    """改行コードを\nに置換する。"""
    r = []
    for c in s:
        if c == '\\':
            r.append("\\\\")
        elif c == '\n':
            r.append("\\n")
        elif c == '\r':
            pass
        else:
            r.append(c)
    return "".join(r)

def decodewrap(s, code="\n"):
    """\nを改行コードに戻す。"""
    r = []
    bs = False
    for c in s:
        if bs:
            if c == 'n':
                r.append(code)
            elif c == '\\':
                r.append('\\')
            else:
                r.append(c)
            bs = False
        elif c == '\\':
            bs = True
        else:
            r.append(c)
    return "".join(r)

def encodetextlist(arr):
    return encodewrap("\n".join(arr))

def decodetextlist(s):
    return decodewrap(s).split("\n")

WRAPS_CHARS = u"｡|､|，|、|。|．|）|」|』|〕|｝|】"

def txtwrap(s, mode, width=30, wrapschars=""):
    """引数の文字列を任意の文字数で改行する(全角は2文字として数える)。
    mode=1: カード解説。
    mode=2: 画像付きメッセージ（台詞）用。
    mode=3: 画像なしメッセージ用。
    mode=4: キャラクタ情報ダイアログの解説文・張り紙説明用。
    mode=5: 素質解説文用。
    mode=6: メッセージダイアログ用。
    """
    if mode == 1:
        wrapschars = WRAPS_CHARS
        width = 37
    elif mode == 2:
        wrapschars = ""
        width = 32
    elif mode == 3:
        wrapschars = ""
        width = 43
    elif mode == 4:
        wrapschars = WRAPS_CHARS
        width = 36
    elif mode == 5:
        wrapschars = WRAPS_CHARS
        width = 24
    elif mode == 6:
        wrapschars = WRAPS_CHARS
        width = 48

    # \\nを改行コードに戻す
    s = cw.util.decodewrap(s)
    # 半角文字集合
    r_hwchar = re.compile(u"[ -~]|[｡-ﾟ]")
    # 行頭禁止文字集合
    r_wchar = re.compile(wrapschars) if not mode in (2, 3) and wrapschars else None
    # 特殊文字記号集合
    r_spchar = re.compile("#[a-z]|&[a-z]") if mode in (2, 3) else None
    cnt = 0
    asciicnt = 0
    wraped = False
    skip = False
    spchar = False
    seq = []

    for index, char in enumerate(s):
        spchar = False
        if r_spchar:
            if skip:
                skip = False
                continue

            chars = char + get_char(s, index + 1)

            if r_spchar.match(chars.lower()):
                if not chars.startswith("#") or\
                   not chars[:2].lower() in cw.cwpy.rsrc.specialchars or\
                   cw.cwpy.rsrc.specialchars[chars[:2].lower()][1]:
                    seq.append(chars)
                    skip = True
                    continue
                spchar = True

        # 行頭禁止文字
        if cnt == 0 and not wraped and r_wchar and r_wchar.match(char):
            seq.insert(-1, char)
            asciicnt = 0
            wraped = True
        # 改行記号
        elif char == "\n":
            seq.append(char)
            cnt = 0
            asciicnt = 0
            wraped = False
        # 半角文字
        elif r_hwchar.match(char):
            seq.append(char)
            cnt += 1

            if mode in (2, 3) or char == " ":
                asciicnt = 0
            else:
                asciicnt += 1

        # 行頭禁止文字・改行記号・半角文字以外
        else:
            seq.append(char)
            cnt += 2
            asciicnt = 0

        # 行折り返し処理
        if not spchar and cnt > width:
            if width >= asciicnt > 0:
                if seq[-asciicnt] <> "\n":
                    seq.insert(-asciicnt, "\n")
                cnt = asciicnt
            elif not get_char(s, index + 1) == "\n":
                if not get_char(s, index + 2) == "\n":
                    seq.append("\n")
                cnt = 0
                asciicnt = 0
                wraped = False

    return "".join(seq).rstrip()

def get_char(s, index):
    try:
        if 0 <= index and index < len(s):
            return s[index]
        return ""
    except:
        return ""

#-------------------------------------------------------------------------------
# wx汎用関数
#-------------------------------------------------------------------------------

def load_wxbmp(name="", mask=False, image=None, maskpos=(0, 0), f=None):
    """pos(0,0)にある色でマスクしたwxBitmapを返す。"""
    if not f and (not cw.binary.image.code_to_data(name) and not os.path.isfile(name)) and not image:
        return wx.EmptyBitmap(0, 0)

    if mask:
        if not image:
            try:
                if f:
                    image = wx.ImageFromStream(f, wx.BITMAP_TYPE_ANY, -1)
                elif cw.binary.image.path_is_code(name):
                    data = cw.binary.image.code_to_data(name)
                    with io.BytesIO(data) as f:
                        image = wx.ImageFromStream(f, wx.BITMAP_TYPE_ANY, -1)
                else:
                    image = wx.Image(name, wx.BITMAP_TYPE_ANY, -1)
            except:
                print u"画像が読み込めません。", name
                return wx.EmptyBitmap(0, 0)

        def set_mask(image, maskpos):
            maskpos = convert_maskpos(maskpos, image.Width, image.Height)
            r = image.GetRed(maskpos[0], maskpos[1])
            g = image.GetGreen(maskpos[0], maskpos[1])
            b = image.GetBlue(maskpos[0], maskpos[1])
            image.SetMaskColour(r, g, b)

        if not image.HasAlpha() and not image.HasMask():
            set_mask(image, maskpos)

        wxbmp = image.ConvertToBitmap()

        # 255色GIFなどでパレットに存在しない色が
        # マスク色に設定されている事があるので、
        # その場合は通常通り左上の色をマスク色とする
        # 将来、もしこの処理の結果問題が起きた場合は
        # このif文以降の処理を削除する必要がある
        if mask and image.HasMask() and image.CountColours() <= 255:
            palette = wxbmp.GetPalette()
            mask = (image.GetMaskRed(), image.GetMaskGreen(), image.GetMaskBlue())
            maskok = False
            for pixel in xrange(palette.GetColoursCount()):
                if palette.GetRGB(pixel) == mask:
                    maskok = True
                    break
            if not maskok:
                set_mask(image, maskpos)
                wxbmp = image.ConvertToBitmap()

    elif image:
        wxbmp = image.ConvertToBitmap()
    else:
        try:
            wxbmp = wx.Bitmap(name)
        except:
            print u"画像が読み込めません。", name
            return wx.EmptyBitmap(0, 0)

    return wxbmp

def fill_bitmap(dc, bmp, csize):
    """引数のbmpを塗りつぶす。"""
    imgsize = bmp.GetSize()

    for cntx in xrange(csize[0] / imgsize[0] + 1):
        for cnty in xrange(csize[1] / imgsize[1] + 1):
            dc.DrawBitmap(bmp, cntx*imgsize[0], cnty*imgsize[1], 0)

def get_centerposition(size, targetpos, targetsize=(1, 1)):
    """中央取りのpositionを計算して返す。"""
    top, left = targetsize[0] / 2 , targetsize[1] / 2
    top, left = targetpos[0] + top, targetpos[1] + left
    top, left = top - size[0] / 2, left - size[1] /2
    return (top, left)

def draw_center(dc, target, pos, mask=True):
    """指定した座標にBitmap・テキストの中央を合わせて描画。
    target: wx.Bitmapかstrかunicode
    """
    if isinstance(target, (str, unicode)):
        size = dc.GetTextExtent(target)
        pos = get_centerposition(size, pos)
        dc.DrawText(target, pos[0], pos[1])
    elif isinstance(target, wx.Bitmap):
        size = target.GetSize()
        pos = get_centerposition(size, pos)
        dc.DrawBitmap(target, pos[0], pos[1], mask)

def draw_height(dc, target, height, mask=True):
    """高さのみ指定して、横幅は背景の中央に合わせてBitmap・テキストを描画。
    target: wx.Bitmapかstrかunicode
    """
    if isinstance(target, (str, unicode)):
        width = (dc.GetSize()[0] - dc.GetTextExtent(target)[0]) / 2
        dc.DrawText(target, width, height)
    elif isinstance(target, wx.Bitmap):
        width = (dc.GetSize()[0] - target.GetSize()[0]) / 2
        dc.DrawBitmap(target, width, height, mask)

def draw_box(dc, pos, size):
    """dcでStaticBoxの囲いを描画する。"""
    # ハイライト
    colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHIGHLIGHT)
    dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
    box = get_boxpointlist((pos[0] + 1, pos[1] + 1), size)
    dc.DrawLineList(box)
    # 主線
    colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)
    dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
    box = get_boxpointlist(pos, size)
    dc.DrawLineList(box)

def get_boxpointlist(pos, size):
    """StaticBoxの囲い描画用のposlistを返す。"""
    x, y = pos
    width, height = size
    poslist = []
    poslist.append((x, y, x + width, y))
    poslist.append((x, y, x, y + height))
    poslist.append((x + width, y, x + width, y + height))
    poslist.append((x, y + height, x + width, y + height))
    return poslist

def create_fileselection(parent, target, message, wildcard="*.*", dir=False, getbasedir=None, callback=None):
    """ファイルまたはディレクトリを選択する
    ダイアログを表示するボタンを生成する。
    parent: ボタンの親パネル。
    target: 選択結果を格納するコントロール。
    message: 選択時に表示されるメッセージ。
    wildcard: 選択対象の定義。
    dir: Trueの場合はディレクトリの選択を行う。
    getbasedir: 相対パスを扱う場合は基準となるパスを返す関数。
    """
    def OnOpen(event):
        fpath = target.GetValue()
        dpath = fpath
        if getbasedir and not os.path.isabs(dpath):
            dpath = os.path.join(getbasedir(), dpath)
        if dir:
            dlg = wx.DirDialog(parent.TopLevelParent, message, dpath, wx.DD_DIR_MUST_EXIST)
            if dlg.ShowModal() == wx.ID_OK:
                dpath = dlg.GetPath()
                if getbasedir:
                    base = getbasedir()
                    dpath = os.path.relpath(dpath, base)
                target.SetValue(dpath)
                if callback:
                    callback(dpath)
        else:
            dpath = os.path.dirname(fpath)
            fpath = os.path.basename(fpath)
            dlg = wx.FileDialog(parent.TopLevelParent, message, dpath, fpath, wildcard, wx.FD_OPEN)
            if dlg.ShowModal() == wx.ID_OK:
                fpath = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
                if getbasedir:
                    base = getbasedir()
                    fpath = os.path.relpath(fpath, base)
                target.SetValue(fpath)
                if callback:
                    callback(fpath)

    button = wx.Button(parent, size=(25, -1), label=u"...")
    parent.Bind(wx.EVT_BUTTON, OnOpen, button)
    return button

#-------------------------------------------------------------------------------
#  スレッド関係
#-------------------------------------------------------------------------------

"""
@synclock(_lock)
def function():
    ...
のように、ロックオブジェクトを指定して
特定関数・メソッドの排他制御を行う。
"""
def synclock(l):
    def synclock(f):
        def acquire(*args, **kw):
            l.acquire()
            try:
                return f(*args, **kw)
            finally:
                l.release()
        return acquire
    return synclock

#-------------------------------------------------------------------------------
#  ショートカット関係
#-------------------------------------------------------------------------------

def get_linktarget(file):
    """fileがショートカットだった場合はリンク先を、
    そうでない場合はfileを返す。
    """
    if sys.platform == "win32" and file.lower().endswith(".lnk"):
        pythoncom.CoInitialize()
        wsh = win32com.client.Dispatch("WScript.Shell")
        if wsh and os.path.isfile(file) and file.lower().endswith(".lnk"):
            shortcut = wsh.CreateShortcut(file)
            return join_paths(shortcut.TargetPath)
    return file

def create_link(path, target):
    if sys.platform == "win32":
        pythoncom.CoInitialize()
        wsh = win32com.client.Dispatch("WScript.Shell")
        dpath = os.path.dirname(path)
        if not os.path.exists(dpath):
            os.makedirs(dpath)
        shortcut = wsh.CreateShortcut(path)
        shortcut.TargetPath = target
        shortcut.save()

#-------------------------------------------------------------------------------
#  パフォーマンスカウンタ
#-------------------------------------------------------------------------------

dictimes = {}
times = [0.0] * 1024
timer = 0.0

def t_start():
    global timer
    timer = time.time()

def t_end(index):
    global times, timer
    times[index] += time.time() - timer
    timer = time.time()

def td_end(key):
    global dictimes, timer
    if key in dictimes:
        dictimes[key] += time.time() - timer
    else:
        dictimes[key] = time.time() - timer
    timer = time.time()

def t_print():
    global times, dictimes
    for i, t in enumerate(times):
        if 0 < t:
            print "time[%s] = %s" % (i, t)
    for key, t in dictimes.iteritems():
        if 0 < t:
            print "time[%s] = %s" % (key, t)

def main():
    pass

if __name__ == "__main__":
    main()
