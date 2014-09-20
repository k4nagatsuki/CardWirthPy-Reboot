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
import lhafile
import operator
import threading
import hashlib
import subprocess
import StringIO
import io
import traceback
import datetime

if sys.platform == "win32":
    import pythoncom
    import win32com.shell.shell
    import win32com.client
    import ctypes

import wx
import wx.lib.mixins.listctrl
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
        self.movie_scr = None
        self.mastervolume = 100
        self._winmm = False
        self._bass = False
        self._movie = None

    def update_scale(self):
        if self._movie:
            self.movie_scr = pygame.Surface(cw.wins(self._movie.get_size())).convert()
            rect = cw.wins(pygame.Rect((0, 0), self._movie.get_size()))
            self._movie.set_display(self.movie_scr, rect)

    def play(self, path, updatepredata=True, restart=False):
        self._play(path, updatepredata, restart)

    def _play(self, path, updatepredata=True, restart=False):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self._play, path, updatepredata, restart)
            return

        assert threading.currentThread() == cw.cwpy
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        fpath = self.get_path(path)
        self.path = path
        if not pygame.mixer and not cw.bassplayer.is_alivablewithpath(path):
            return

        if cw.cwpy.rsrc:
            fpath = cw.cwpy.rsrc.get_filepath(fpath)

        if not os.path.isfile(fpath):
            self.stop()
        else:
            assert threading.currentThread() == cw.cwpy

            self.set_volume()
            if restart or self.fpath <> fpath:
                self.stop()
                self._winmm = False
                self._bass = False
                type = load_bgm(fpath)
                if type <> -1:
                    filesize = 0
                    if os.path.isfile(fpath):
                        try:
                            filesize = os.path.getsize(fpath)
                        except Exception, e:
                            cw.util.print_ex()

                    if type == 2:
                        volume = self._get_volumevalue(fpath)
                        try:
                            cw.bassplayer.play_bgm(fpath, volume)
                            self._bass = True
                        except Exception:
                            cw.util.print_ex()
                    elif type == 1:
                        if sys.platform == "win32":
                            name = "cwbgm"
                            mciSendStringW = ctypes.windll.winmm.mciSendStringW
                            mciSendStringW(u'open "%s" alias %s' % (fpath, name), 0, 0, 0)
                            volume = int(cw.cwpy.setting.vol_bgm * 1000)
                            mciSendStringW(u"setaudio %s volume to %s" % (name, volume), 0, 0, 0)
                            mciSendStringW(u"play %s" % (name), 0, 0, 0)
                            self._winmm = True
                        elif cw.util.splitext(fpath)[1].lower() in (".mpg", ".mpeg"):
                            try:
                                pygame.mixer.quit()
                                encoding = sys.getfilesystemencoding()
                                self._movie = pygame.movie.Movie(fpath.encode(encoding))
                                self._movie.set_volume(self._get_volumevalue(fpath))
                                self.movie_scr = pygame.Surface(cw.wins(self._movie.get_size())).convert()
                                rect = cw.wins(pygame.Rect((0, 0), self._movie.get_size()))
                                self._movie.set_display(self.movie_scr, rect)
                                self._movie.play()
                            except Exception:
                                cw.util.print_ex()
                    elif filesize == 57 and cw.util.get_md5(fpath) == "d11be4c76fc63a6ba299c2f3bd3880b0":
                        # FIXME: reset.mid
                        # 繰り返し流すとハングアップ pygame 1.9.1
                        pygame.mixer.music.play(0)
                    elif filesize == 737 and cw.util.get_md5(fpath) == "41b0a6aaa8ffefa9ce6742e80e393075":
                        # FIXME: DefReset.mid
                        # 繰り返し流すとシステムが不安定になる pygame 1.9.1
                        pygame.mixer.music.play(0)
                    elif cw.util.splitext(fpath)[1].lower() == ".mp3":
                        # 互換動作: 1.28以前はMP3がループ再生されない
                        if cw.cwpy.sct.lessthan("1.28", cw.cwpy.sdata.get_versionhint()):
                            pygame.mixer.music.play(0)
                        else:
                            pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.music.play(-1)
            self.fpath = fpath
            self.path = path

        if updatepredata and cw.cwpy.sdata and cw.cwpy.sdata.pre_battleareadata:
            areaid, bgmpath, battlebgmpath = cw.cwpy.sdata.pre_battleareadata
            bgmpath = path
            cw.cwpy.sdata.pre_battleareadata = (areaid, bgmpath, battlebgmpath)

    def stop(self):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self.stop)
            return

        assert threading.currentThread() == cw.cwpy

        if self._bass:
            if cw.bassplayer.is_alivablewithpath(self.path):
                cw.bassplayer.stop_bgm()
                self._bass = False
        elif self._winmm:
            name = "cwbgm"
            mciSendStringW = ctypes.windll.winmm.mciSendStringW
            mciSendStringW(u"stop %s" % (name), 0, 0, 0)
            mciSendStringW(u"close %s" % (name), 0, 0, 0)
            self._winmm = False
        elif self._movie:
            assert self.movie_scr
            self._movie.stop()
            self._movie = None
            self.movie_scr = None
            pygame.mixer.init(44100, -16, 2, 1024)
        else:
            if pygame.mixer:
                pygame.mixer.music.stop()
        remove_soundtempfile("Bgm")
        self.fpath = ""
        self.path = ""
        # pygame.mixer.musicで読み込んだ音楽ファイルを解放する
        if cw.cwpy.rsrc:
            path = "DefReset" + cw.cwpy.rsrc.ext_bgm
            path = join_paths(cw.cwpy.setting.skindir, "Bgm", path)
            load_bgm(path)

    def _get_volumevalue(self, fpath):
        if not cw.cwpy.setting.play_bgm:
            return 0

        ext = cw.util.splitext(fpath)[1].lower()

        if ext == ".mid" or ext == ".midi":
            volume = cw.cwpy.setting.vol_midi * cw.cwpy.setting.vol_bgm
        else:
            volume = cw.cwpy.setting.vol_bgm

        return volume * self.mastervolume / 100

    def set_volume(self, volume=None):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self.set_volume, volume)
            return

        if not pygame.mixer:
            return

        if volume is None:
            volume = self._get_volumevalue(self.fpath)

        assert threading.currentThread() == cw.cwpy
        if self._bass:
            cw.bassplayer.set_bgmvolume(volume)
        elif self._movie:
            self._movie.set_volume(volume)
        else:
            pygame.mixer.music.set_volume(volume)

    def set_mastervolume(self, volume):
        if threading.currentThread() <> cw.cwpy:
            cw.cwpy.exec_func(self.set_mastervolume, volume)
            return

        self.mastervolume = volume
        self.set_volume()

    def get_path(self, path):
        inusepath = cw.util.get_inusecardmaterialpath(path, cw.M_MSC)
        if os.path.isfile(inusepath):
            path = inusepath
        else:
            path = get_materialpath(path, cw.M_MSC, system=cw.cwpy.areaid < 0)

        return path

class SoundInterface(object):
    def __init__(self, sound=None, path=""):
        self._sound = sound
        self._path = path

    def _play_before(self, from_scenario):
        if from_scenario:
            if cw.cwpy.lastsound_scenario:
                cw.cwpy.lastsound_scenario.stop(from_scenario)
                cw.cwpy.lastsound_scenario = None
            cw.cwpy.lastsound_scenario = self
            return "Sound"
        else:
            if cw.cwpy.lastsound_system:
                cw.cwpy.lastsound_system.stop(from_scenario)
                cw.cwpy.lastsound_system = None
            cw.cwpy.lastsound_system = self
            return "SystemSound"

    def play(self, from_scenario=False):
        if self._sound:

            if cw.cwpy.setting.play_sound:
                volume = (cw.cwpy.setting.vol_sound * cw.cwpy.music.mastervolume) / 100.0
            else:
                volume = 0

            if cw.bassplayer.is_alivablewithpath(self._path):
                if threading.currentThread() <> cw.cwpy:
                    cw.cwpy.exec_func(self.play, from_scenario)
                    return
                assert threading.currentThread() == cw.cwpy
                tempbasedir = self._play_before(from_scenario)
                try:
                    path = get_soundfilepath(tempbasedir, self._sound)
                    cw.bassplayer.play_sound(path, volume, from_scenario)
                except Exception, ex:
                    cw.util.print_ex()
            elif sys.platform == "win32" and isinstance(self._sound, (str, unicode)):
                if threading.currentThread() == cw.cwpy:
                    cw.cwpy.frame.exec_func(self.play, from_scenario)
                    return
                assert threading.currentThread() <> cw.cwpy
                tempbasedir = self._play_before(from_scenario)
                if from_scenario:
                    name = "cwsnd1"
                else:
                    name = "cwsnd2"

                mciSendStringW = ctypes.windll.winmm.mciSendStringW
                path = get_soundfilepath(tempbasedir, self._sound)
                mciSendStringW(u'open "%s" alias %s' % (path, name), 0, 0, 0)
                volume = int(volume * 1000)
                mciSendStringW(u"setaudio %s volume to %s" % (name, volume), 0, 0, 0)
                mciSendStringW(u"play %s" % (name), 0, 0, 0)
            else:
                if threading.currentThread() <> cw.cwpy:
                    cw.cwpy.exec_func(self.play, from_scenario)
                    return
                assert threading.currentThread() == cw.cwpy
                tempbasedir = self._play_before(from_scenario)
                if from_scenario:
                    chan = pygame.mixer.Channel(0)
                else:
                    chan = pygame.mixer.Channel(1)

                self._sound.set_volume(volume)
                chan.play(self._sound)

    def stop(self, from_scenario):
        if self._sound:
            if from_scenario:
                tempbasedir = "Sound"
            else:
                tempbasedir = "SystemSound"

            if cw.bassplayer.is_alivablewithpath(self._path):
                if threading.currentThread() <> cw.cwpy:
                    cw.cwpy.exec_func(self.stop, from_scenario)
                    return
                assert threading.currentThread() == cw.cwpy
                try:
                    cw.bassplayer.stop_sound(from_scenario)
                    remove_soundtempfile(tempbasedir)
                except Exception, ex:
                    cw.util.print_ex()
            elif sys.platform == "win32" and isinstance(self._sound, (str, unicode)):
                if threading.currentThread() == cw.cwpy:
                    cw.cwpy.frame.exec_func(self.stop, from_scenario)
                    return
                assert threading.currentThread() <> cw.cwpy
                if from_scenario:
                    name = "cwsnd1"
                else:
                    name = "cwsnd2"

                mciSendStringW = ctypes.windll.winmm.mciSendStringW
                mciSendStringW(u"stop %s" % (name), 0, 0, 0)
                mciSendStringW(u"close %s" % (name), 0, 0, 0)
                remove_soundtempfile(tempbasedir)
            else:
                if threading.currentThread() <> cw.cwpy:
                    cw.cwpy.exec_func(self.stop, from_scenario)
                    return
                assert threading.currentThread() == cw.cwpy
                if from_scenario:
                    chan = pygame.mixer.Channel(0)
                else:
                    chan = pygame.mixer.Channel(1)

                chan.stop()

#-------------------------------------------------------------------------------
#　汎用関数
#-------------------------------------------------------------------------------

def init(size_noscale=None, title="", fullscreen=False, soundfonts=None):
    """pygame初期化。"""
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    flags = 0
    size = cw.s(size_noscale)
    if fullscreen:
        scr_fullscreen = pygame.display.set_mode((0, 0), flags)
        scr = pygame.Surface(size).convert()
        scr_draw = scr
    else:
        scr_fullscreen = None
        scr = pygame.display.set_mode(cw.wins(size_noscale), flags)
        if cw.UP_WIN == cw.UP_SCR:
            scr_draw = scr
        else:
            scr_draw = pygame.Surface(size).convert()
    clock = pygame.time.Clock()

    if title:
        pygame.display.set_caption(title)

    pygame.mixer.set_num_channels(2)
    pygame.event.set_blocked(None)
    pygame.event.set_allowed([KEYDOWN, KEYUP, MOUSEBUTTONDOWN, MOUSEBUTTONUP, USEREVENT])

    # BASS Audioを初期化(使用できない事もある)
    if soundfonts is None:
        soundfonts = [(cw.DEFAULT_SOUNDFONT, True)]
    soundfonts = [sfont[0] for sfont in soundfonts if sfont[1]]
    cw.bassplayer.init_bass(soundfonts)

    return scr, scr_draw, scr_fullscreen, clock

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

def load_image(path, mask=False, maskpos=(0, 0), f=None, retry=True, isback=False):
    """pygame.Surface(読み込めなかった場合はNone)を返す。
    path: 画像ファイルのパス。
    mask: True時、(0,0)のカラーを透過色に設定する。透過画像の場合は無視される。
    """
    #assert threading.currentThread() == cw.cwpy
    if cw.cwpy.rsrc:
        path = cw.cwpy.rsrc.get_filepath(path)
    try:
        if f:
            try:
                pos = f.tell()
                ispng = get_imageext(f.read(16)) == ".png"
                f.seek(pos)
                image = pygame.image.load(f, "")
            except:
                image = pygame.image.load(f, path)
        elif cw.binary.image.path_is_code(path):
            data = cw.binary.image.code_to_data(path)
            ispng = get_imageext(data) == ".png"
            #return pygame.Surface((0, 0)).convert()
            with io.BytesIO(data) as f2:
                image = pygame.image.load(f2)
        else:
            if not os.path.isfile(path):
                return pygame.Surface((0, 0)).convert()
            ispng = os.path.splitext(path)[1].lower() == ".png"
            with io.BufferedReader(io.FileIO(path)) as f2:
                image = pygame.image.load(f2)
    except:
        print u"画像が読み込めません(load_image)。リトライします", path
        if retry:
            try:
                if f:
                    f.seek(0)
                    data = f.read()
                elif cw.binary.image.path_is_code(path):
                    data = cw.binary.image.code_to_data(path)
                else:
                    if not os.path.isfile(path):
                        return pygame.Surface((0, 0)).convert()
                    with open(path, "rb") as f2:
                        data = f2.read()
                data = cw.image.fix_cwnext16bitbitmap(data)
                with io.BytesIO(data) as f2:
                    return load_image(path, mask, maskpos, f2, False, isback=isback)
            except:
                print u"画像が読み込めません(リトライ後)", path
        return pygame.Surface((0, 0)).convert()

    # アルファチャンネルを持った透過画像を読み込んだ場合は
    # SRCALPHA(0x00010000)のフラグがONになっている
    if image.get_flags() & SRCALPHA:
        image = image.convert_alpha()
    else:
        imageb = image
        image = image.convert()

        # カード画像がPNGの場合はマスクカラーを無視する(CardWirth 1.50の実装)
        if image.get_colorkey() and ispng and not isback:
            image.set_colorkey(None)

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
                for pixel in imageb.get_palette():
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

def put_number(image, num):
    """アイコンサイズの画像imageの上に
    numの値を表示する。
    """
    image = image.copy()
    s = str(num)
    if len(s) == 1:
        font = cw.cwpy.rsrc.fonts["statusimg1"]
    elif len(s) == 2:
        font = cw.cwpy.rsrc.fonts["statusimg2"]
    else:
        font = cw.cwpy.rsrc.fonts["statusimg3"]
    h = font.get_height()
    w = (h+1) / 2
    subimg = pygame.Surface((len(s)*w, h)).convert_alpha()
    subimg.fill((0, 0, 0, 0))
    x = image.get_width() - subimg.get_width() - cw.s(1)
    y = image.get_height() - subimg.get_height()
    pos = (x, y)
    for i, c in enumerate(s):
        cimg = font.render(c, 2 <= cw.UP_SCR, (0, 0, 0))
        image.blit(cimg, (pos[0]+1 + i*w, pos[1]+1))
        image.blit(cimg, (pos[0]+1 + i*w, pos[1]-1))
        image.blit(cimg, (pos[0]-1 + i*w, pos[1]+1))
        image.blit(cimg, (pos[0]-1 + i*w, pos[1]-1))
        image.blit(cimg, (pos[0]+1 + i*w, pos[1]))
        image.blit(cimg, (pos[0]-1 + i*w, pos[1]))
        image.blit(cimg, (pos[0] + i*w, pos[1]+1))
        image.blit(cimg, (pos[0] + i*w, pos[1]-1))
        cimg = font.render(c, 2 <= cw.UP_SCR, (255, 255, 255))
        image.blit(cimg, (pos[0] + i*w, pos[1]))
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
    """sexとageに対応したFaceディレクトリ内の画像パスを辞書で返す。
    辞書の内容は、サブディレクトリをキーにした
    当該ディレクトリ内のファイルパスのlistとなる。
    sexcoupon: 性別クーポン。
    agecoupon: 年代クーポン。
    rel: TrueならlistにFaceディレクトリからの相対パスを格納する。
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

    imgpaths = {}

    for dpath in dpaths:
        dpath2 = cw.util.join_paths(facedir, dpath)
        if not os.path.isdir(dpath2):
            continue
        for dpath3, dnames, fnames in os.walk(dpath2):
            seq = []
            for fname in fnames:
                path = join_paths(dpath3, fname)
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in cw.EXTS_IMG:
                        if rel:
                            p = relpath(path, facedir)
                            seq.append(p)
                        else:
                            seq.append(path)
            if seq:
                p = relpath(dpath3, facedir)
                imgpaths[join_paths(p)] = seq

    return imgpaths

def load_bgm(path):
    """Pathの音楽ファイルをBGMとして読み込む。
    リピートして鳴らす場合は、cw.audio.MusicInterface参照。
    pygame.mixer.music.load()が成功した場合は0、
    winmm.dllを利用して再生する場合は1(Windowsのみ)、
    bass.dllを利用して再生する場合は2、
    失敗した場合は-1を返す。
    path: 音楽ファイルのパス。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if cw.cwpy.rsrc:
        path = cw.cwpy.rsrc.get_filepath(path)

    if not pygame.mixer or not os.path.isfile(path):
        return

    if cw.util.splitext(path)[1].lower() in (".mpg", ".mpeg"):
        return 1

    if cw.bassplayer.is_alivablewithpath(path):
        return 2

    path = get_soundfilepath("Bgm", path)

    try:
        assert threading.currentThread() == cw.cwpy
        # ファイルパスを渡して読込
        encoding = sys.getfilesystemencoding()
        pygame.mixer.music.load(path.encode(encoding))
        return 0
    except Exception:
        cw.util.print_ex()
        try:
            # ストリームからの読込を試みる
            f = io.BufferedReader(io.FileIO(path))
            pygame.mixer.music.load(f)
            return 0
        except Exception:
            cw.util.print_ex()
            print u"BGMが読み込めません", path
            return -1

def load_sound(path):
    """効果音ファイルを読み込み、SoundInterfaceを返す。
    読み込めなかった場合は、無音で再生するSoundInterfaceを返す。
    path: 効果音ファイルのパス。
    """
    if threading.currentThread() <> cw.cwpy:
        raise Exception()

    if cw.cwpy.rsrc:
        path = cw.cwpy.rsrc.get_filepath(path)

    if not pygame.mixer or not os.path.isfile(path):
        return SoundInterface()

    if cw.cwpy.is_playingscenario() and path in cw.cwpy.sdata.cache:
        return cw.cwpy.sdata.cache[path]

    try:
        assert threading.currentThread() == cw.cwpy
        if cw.bassplayer.is_alivablewithpath(path):
            # BASSが使用できる場合
            sound = SoundInterface(path, path)
        elif sys.platform == "win32" and (path.lower().endswith(".wav") or\
                                        path.lower().endswith(".mp3")):
            # WinMMを使用する事でSDL_mixerの問題を避ける
            # FIXME: mp3効果音をWindows環境でしか再生できない
            sound = SoundInterface(path, path)
        else:
            with io.BufferedReader(io.FileIO(path)) as f:
                sound = pygame.mixer.Sound(f)
            sound = SoundInterface(sound, path)
    except:
        print u"サウンドが読み込めません", path
        return SoundInterface()

    if cw.cwpy.is_playingscenario():
        cw.cwpy.sdata.cache[path] = sound

    return sound

def get_soundfilepath(basedir, path):
    """宿のフォルダにある場合は問題が出るため、
    再生用のコピーを生成する。
    """
    if path and cw.cwpy.ydata and (path.startswith(cw.cwpy.ydata.yadodir) or\
                                   path.startswith(cw.cwpy.ydata.tempdir)):
        dpath = join_paths(u"Data/Temp/Playing", basedir)
        fpath = os.path.basename(path)
        fpath = join_paths(dpath, fpath)
        fpath = cw.binary.util.check_duplicate(fpath)
        if not os.path.isdir(dpath):
            os.makedirs(dpath)
        shutil.copyfile(path, fpath)
        path = fpath
    return path

def remove_soundtempfile(basedir):
    """再生用のコピーを削除する。
    """
    dpath = join_paths(u"Data/Temp/Playing", basedir)
    if os.path.isdir(dpath):
        remove(dpath)
        if not os.listdir(u"Data/Temp/Playing"):
            remove(dpath)

def sort_by_attr(seq, *attr):
    """破壊的にオブジェクトの属性でソートする。
    seq: リスト
    attr: 属性名
    """
    return seq.sort(key=operator.attrgetter(*attr))

def sorted_by_attr(seq, *attr):
    """非破壊的にオブジェクトの属性でソートする。
    seq: リスト
    attr: 属性名
    """
    return sorted(seq, key=operator.attrgetter(*attr))

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
    return "/".join(paths).replace("\\", "/").rstrip("/")

def relpath(path, start):
    if len(start) < len(path) and path.startswith(start):
        path2 = path[len(start):]
        if path2[0] == '/' or (sys.platform == "win32" and path2[0] == '\\'):
            return path2[1:]
    return os.path.relpath(path, start)
assert relpath("Data/abc", "Data") == "abc"
assert relpath("Data/abc/def", "Data").replace("\\", "/") == "abc/def"
assert relpath("Data/abc/def", "Data/abc/").replace("\\", "/") == "def"
assert relpath("Data/abc/def", "Data/abc") == os.path.relpath("Data/abc/def", "Data/abc")
assert relpath("Data/abc/def", "..").replace("\\", "/") == os.path.relpath("Data/abc/def", "..").replace("\\", "/")
assert relpath(".", "..").replace("\\", "/") == os.path.relpath(".", "..").replace("\\", "/")
assert relpath("/a", "..").replace("\\", "/") == os.path.relpath("/a", "..").replace("\\", "/")
assert relpath("a", "../bcde").replace("\\", "/") == os.path.relpath("a", "../bcde").replace("\\", "/")
assert relpath("../a", "../bcde").replace("\\", "/") == os.path.relpath("../a", "../bcde").replace("\\", "/")
assert relpath("../a", "../").replace("\\", "/") == os.path.relpath("../a", "../").replace("\\", "/")

def splitext(p):
    """パスの拡張子以外の部分と拡張子部分の分割。
    os.path.splitext()との違いは、".ext"のような
    拡張子部分だけのパスの時、(".ext", "")ではなく
    ("", ".ext")を返す事である。
    """
    p = os.path.splitext(p)
    if p[0].startswith(".") and not p[1]:
        return (p[1], p[0])
    return p

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

def print_ex():
    """例外の内容を標準出力に書き足す。
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
    print
    return

def screenshot():
    """スクリーンショットを書き出す。
    """
    date = datetime.datetime.today()

    if not os.path.isdir("ScreenShot"):
        os.mkdir("ScreenShot")

    cw.cwpy.sounds["screenshot"].play()

    filename = os.path.join("ScreenShot", date.strftime("%Y%m%d_%H%M%S_%f.png"))
    d = cw.cwpy.get_titledic()
    d["date"] = date.strftime("%Y-%m-%d")
    d["year"] = date.strftime("%Y")
    d["month"] = date.strftime("%m")
    d["day"] = date.strftime("%d")
    d["time"] = date.strftime("%H:%M:%S")
    d["hour"] = date.strftime("%H")
    d["minute"] = date.strftime("%M")
    d["second"] = date.strftime("%S")
    title = format_title(cw.cwpy.setting.ssinfoformat, d)
    if title:
        fore = cw.cwpy.setting.ssinfofontcolor
        back = cw.cwpy.setting.ssinfobackcolor
        w = cw.s(cw.SIZE_GAME[0])
        h = cw.s(cw.SIZE_GAME[1] + 20)
        bmp = pygame.Surface((w, h)).convert()
        bmp.fill(back, rect=pygame.Rect(cw.s(0), cw.s(0), w, cw.s(20)))
        bmp.blit(cw.cwpy.scr_draw, cw.s((0, 20)))
        font = cw.cwpy.rsrc.fonts["screenshot"]
        fh = font.get_height()
        subimg = font.render(title, True, fore)
        y = (cw.s(20) - fh) / 2
        swmax = w - cw.s(10)*2
        if swmax < subimg.get_width():
            size = (swmax, subimg.get_height())
            subimg = pygame.transform.smoothscale(subimg, size)
        bmp.blit(subimg, (cw.s(10), y))
    else:
        bmp = cw.cwpy.scr_draw
    pygame.image.save(bmp, filename)

    return

#-------------------------------------------------------------------------------
#　ファイル操作関連
#-------------------------------------------------------------------------------

def dupcheck_plus(path, yado=True):
    """パスの重複チェック。引数のパスをチェックし、重複していたら、
    ファイル・フォルダ名の後ろに"(n)"を付加して重複を回避する。
    宿のファイルパスの場合は、"Data/Temp/Yado"ディレクトリの重複もチェックする。
    """

    dpath, basename = os.path.split(path)
    fname, ext = cw.util.splitext(basename)
    fname = cw.binary.util.check_filename(fname.strip())
    ext = ext.strip()
    basename = fname + ext
    path = join_paths(dpath, basename)

    if yado:
        if path.startswith("Yado"):
            temppath = path.replace("Yado", "Data/Temp/Yado", 1)
        elif path.startswith("Data/Temp/Yado"):
            temppath = path.replace("Data/Temp/Yado", "Yado", 1)
        else:
            print u"宿パスの重複チェック失敗", path
            temppath = ""

    else:
        temppath = ""

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
                print u"宿パスの重複チェック失敗", path
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

    fname = fname.strip()
    if fname == "":
        fname = "noname"
    return fname

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

def get_inusecardmaterialpath(path, type, inusecard=None):
    """pathが宿からシナリオへ持ち込んだカードの
    素材を指していればそのパスを返す。
    そうでない場合は空文字列を返す。"""
    imgpath = ""
    if cw.cwpy.event.in_inusecardevent:
        if inusecard or (cw.cwpy.is_runningevent() and cw.cwpy.event.get_inusecard()):
            if not inusecard:
                inusecard = cw.cwpy.event.get_inusecard()
            if not inusecard.carddata.getbool(".", "scenariocard", False):
                imgpath = cw.util.join_yadodir(path)
                imgpath = get_materialpathfromskin(imgpath, type)
    return imgpath

def get_materialpath(path, type, scedir="", system=False):
    """pathが指す素材を、シナリオプレイ中はシナリオ内から探し、
    プレイ中でない場合や存在しない場合はスキンから探す。
    path: 素材の相対パス。
    type: 素材のタイプ。cw.M_IMG, cw.M_MSC, cw.M_SNDのいずれか。
    """
    if type == cw.M_IMG and cw.binary.image.path_is_code(path):
        return path
    if not system and cw.cwpy.is_playingscenario():
        tpath = cw.util.join_paths(u"Data/Temp/ScenarioLog/TempFile", path)
        if os.path.isfile(tpath):
            path = tpath
        else:
            if not scedir:
                scedir = cw.cwpy.sdata.scedir
            path = cw.util.join_paths(scedir, path)
    elif not os.path.isfile(path):
        path = cw.util.join_paths(cw.cwpy.skindir, path)
    return get_materialpathfromskin(path, type)

def get_materialpathfromskin(path, type):
    if not os.path.isfile(path):
        if type == cw.M_IMG:
            fname = os.path.basename(path)
            fname = cw.util.splitext(fname)[0] + cw.cwpy.rsrc.ext_img
            path = cw.util.join_paths(cw.cwpy.skindir, "Table", fname)
        elif type == cw.M_MSC:
            fname = os.path.basename(path)
            fname = cw.util.splitext(fname)[0] + cw.cwpy.rsrc.ext_bgm
            path = cw.util.join_paths(cw.cwpy.skindir, "Bgm", fname)
        elif type == cw.M_SND:
            fname = os.path.basename(path)
            fname = cw.util.splitext(fname)[0] + cw.cwpy.rsrc.ext_snd
            path = cw.util.join_paths(cw.cwpy.skindir, "Sound", fname)
    return path

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
            time.sleep(1)
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
                    if os.path.isdir(path):
                        try:
                            os.chmod(path, stat.S_IWRITE|stat.S_IREAD)
                        except WindowsError, err:
                            time.sleep(1)
                            remove_tree2(treepath)
                            return

                for fname in fnames:
                    path = join_paths(dpath, fname)
                    if os.path.isfile(path):
                        try:
                            os.chmod(path, stat.S_IWRITE|stat.S_IREAD)
                        except WindowsError, err:
                            time.sleep(1)
                            remove_tree2(treepath)
                            return

            remove_tree(treepath, retry + 1)
        elif retry < 5:
            time.sleep(1)
            remove_tree(treepath, retry + 1)
        else:
            remove_tree2(treepath)

def remove_tree2(treepath):
    # shutil.rmtree()で権限付与時にエラーになる事があるので
    # 削除方法を変えてみる
    for dpath, dnames, fnames in os.walk(treepath, topdown=False):
        for dname in dnames:
            path = join_paths(dpath, dname)
            os.rmdir(path)
        for fname in fnames:
            path = join_paths(dpath, fname)
            os.remove(path)
    os.rmdir(treepath)

def rename_file(path, dstpath):
    """pathをdstpathへ移動する。
    すでにdstpathがある場合は上書きされる。
    """
    if not os.path.isdir(os.path.dirname(dstpath)):
        os.makedirs(os.path.dirname(dstpath))
    if os.path.isfile(dstpath):
        remove_file(dstpath)
    try:
        shutil.move(path, dstpath)
    except OSError:
        # ファイルシステムが異なっていると失敗する
        # 可能性があるのでコピー&削除を試みる
        cw.util.print_ex()
        with open(path, "rb") as f1:
            with open(dstpath, "wb") as f2:
                f2.write(f1.read())
        remove_file(path)

#-------------------------------------------------------------------------------
#　ZIPファイル関連
#-------------------------------------------------------------------------------

class _LhafileWrapper(lhafile.Lhafile):
    def __init__(self, path, mode):
        # 十六進数のファイルサイズを表す文字列+Windows改行コードが
        # 冒頭に入っていることがある。
        # その場合は末尾にも余計なデータもあるため、冒頭で指定された
        # サイズにファイルを切り詰めなくてはならない。
        f = open(path, "rb")
        b = str(f.read(1))
        strnum = []
        while b in ("0123456789abcdefABCDEF"):
            strnum.append(b)
            b = str(f.read(1))
        if strnum and b == '\r' and f.read(1) == '\n':
            strnum = "".join(strnum)
            num = int(strnum, 16)
            data = f.read(num)
            f.close()
            f = io.BytesIO(data)
            lhafile.Lhafile.__init__(self, f)
            self.f = f
        else:
            f.seek(0)
            lhafile.Lhafile.__init__(self, f)
            self.f = f

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    def close(self):
        self.f.close()

def zip_file(path, mode):
    """zipfile.ZipFileのインスタンスを生成する。
    FIXME: Python 2.7のzipfile.ZipFileはアーカイブ内の
    ファイル名にあるディレクトリセパレータを'/'に置換してしまうため、
    「ソ」などのいわゆるShift JISの0x5C問題に引っかかって
    正しいファイル名が得られなくなってしまう。
    まったくスレッドセーフではない悪い方法だが、
    それを回避するには一時的にos.sepを'/'にして凌ぐしかない。"""
    if path.lower().endswith(".lzh"):
        return _LhafileWrapper(path, mode)
    else:
        sep = os.sep
        os.sep = "/"
        try:
            return zipfile.ZipFile(path, mode)
        finally:
            os.sep = sep

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

def decompress_zip(path, dstdir, dname="", avoiddup=False, startup=None, progress=None):
    """zipファイルをdstdirに解凍する。
    解凍したディレクトリのpathを返す。
    """
    try:
        z = zip_file(path, "r")
    except:
        return None

    if not dname:
        dname = cw.util.splitext(os.path.basename(path))[0]

    dstdir = join_paths(dstdir, dname)
    dstdir = dupcheck_plus(dstdir, False)

    list = z.namelist()
    if startup:
        startup(len(list))
    for i, zname in enumerate(list):
        if progress and i % 10 == 0:
            progress(i)
        name = decode_zipname(zname).replace('\\', '/')
        normpath = os.path.normpath(name)
        if normpath == ".." or normpath.startswith(".." + os.path.sep):
            continue

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

    if progress:
        progress(len(list))

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
                cw.util.remove(dstdir2)

    return dstdir

def decode_zipname(name):
    if not isinstance(name, unicode):
        try:
            name = name.decode(cw.MBCS)
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
            data = zfile.read(name.encode(cw.MBCS))
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
    with zip_file(zpath, "r") as z:
        data = read_zipdata(z, name)
    f = StringIO.StringIO(data)
    try:
        element = cw.data.xml2element(name, tag, file=f)
    finally:
        f.close()
    return element

def decompress_cab(path, dstdir, dname="", avoiddup=False, startup=None, progress=None):
    """cabファイルをdstdirに解凍する。
    解凍したディレクトリのpathを返す。
    """

    if not dname:
        dname = cw.util.splitext(os.path.basename(path))[0]

    dstdir = join_paths(dstdir, dname)
    dstdir = dupcheck_plus(dstdir, False)

    if startup or progress:
        filenum = cab_filenum(path)

    if startup:
        startup(filenum)

    try:
        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        s = "expand \"%s\" -f:* \"%s\"" % (path, dstdir)
        encoding = sys.getfilesystemencoding()
        if progress:
            class Progress(object):
                def __init__(self):
                    self.result = dstdir
                def run(self):
                    if subprocess.call(s.encode(encoding), shell=True) <> 0:
                        self.result = None

            prog = Progress()
            thr = threading.Thread(target=prog.run)
            thr.start()
            count = 0
            while thr.is_alive():
                # ファイル数カウント
                last_count = count
                count = 0
                for dpath, dnames, fnames in os.walk(dstdir):
                    count += len(fnames)
                if last_count <> count:
                    progress(count)
                p = time.time() + 0.1
                while thr.is_alive() and time.time() < p:
                    time.sleep(0.001)
        else:
            if subprocess.call(s.encode(encoding), shell=True) <> 0:
                return None
    except Exception:
        cw.util.print_ex()
        return None

    if progress:
        progress(filenum)

    if avoiddup:
        # 内部にディレクトリが一つしかない場合は
        # 最上位のディレクトリに格上げする
        list = os.listdir(dstdir)
        if 1 == len(list):
            dpath = os.path.join(dstdir, list[0])
            if os.path.isdir(dpath):
                dstdir2 = dupcheck_plus(dstdir, False)
                shutil.move(dstdir, dstdir2)
                shutil.move(os.path.join(dstdir2, list[0]), dstdir)
                cw.util.remove(dstdir2)

    return dstdir

def cab_filenum(cab):
    """CABアーカイブに含まれるファイル数を返す。"""
    dword = struct.Struct("<l")
    word = struct.Struct("<h")
    try:
        with io.BufferedReader(io.FileIO(cab, "rb")) as f:
            # ヘッダ
            buf = f.read(36)
            if buf[:4] <> "MSCF":
                return 0

            cfiles = word.unpack(buf[28:30])[0]
            return cfiles
    except Exception:
        cw.util.print_ex()
    return 0

def cab_hasfile(cab, file):
    """CABアーカイブに指定された名前のファイルが含まれているか判定する。"""
    if not os.path.isfile(cab):
        return False

    dword = struct.Struct("<l")
    word = struct.Struct("<h")
    file = os.path.normcase(file)
    encoding = "cp932"
    try:
        with io.BufferedReader(io.FileIO(cab, "rb")) as f:
            # ヘッダ
            buf = f.read(36)
            if buf[:4] <> "MSCF":
                return False

            cofffiles = dword.unpack(buf[16:20])[0]
            cfiles = word.unpack(buf[28:30])[0]
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
    except Exception:
        cw.util.print_ex()
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
        width = 42
    elif mode == 4:
        wrapschars = WRAPS_CHARS
        width = 37
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
    # 互換動作: 1.30以前はO,P,L,Dの各色が無い
    if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
        re_color = "&[wrbgy]"
    else:
        re_color = "&[wrbgyopld]"
    r_spchar = re.compile("#[abdefghjklnopqsvwxz]|" + re_color) if mode in (2, 3) else None
    cnt = 0
    asciicnt = 0
    wraped = False
    skip = False
    spchar = False
    defspchar = False
    wrapafter = False
    seq = []

    for index, char in enumerate(s):
        spchar2 = spchar
        spchar = False
        width2 = width
        wrapafter2 = wrapafter
        defspchar2 = defspchar
        defspchar = False

        if r_spchar and not defspchar2:
            if skip:
                seq.append(char)
                skip = False
                continue

            chars = char + get_char(s, index + 1)

            if r_spchar.match(chars.lower()):
                if not chars.startswith("#") or\
                   not chars[:2].lower() in cw.cwpy.rsrc.specialchars or\
                   cw.cwpy.rsrc.specialchars[chars[:2].lower()][1]:
                    seq.append(char)
                    skip = True
                    continue
                spchar = True
                if not chars.startswith("&"):
                    wrapafter = False
                    defspchar = True

        # 行頭禁止文字
        if cnt == 0 and not wraped and r_wchar and r_wchar.match(char):
            seq.insert(-1, char)
            asciicnt = 0
            wraped = True
        # 改行記号
        elif char == "\n":
            if not wrapafter:
                seq.append(char)
            cnt = 0
            asciicnt = 0
            wraped = False
            wrapafter = False
        # 半角文字
        elif r_hwchar.match(char):
            seq.append(char)
            cnt += 1
            if not (mode in (2, 3)) and not (mode == 1 and index+1 < len(s) and not r_hwchar.match(s[index+1])):
                asciicnt += 1
            if spchar2 or not (mode in (2, 3)) or len(s) <= index+1 or r_hwchar.match(s[index+1]):
                width2 += 1
            wrapafter = False

        # 行頭禁止文字・改行記号・半角文字以外
        else:
            seq.append(char)
            cnt += 2
            asciicnt = 0
            wrapafter = False
            if mode in (1, 2, 3) and index+1 < len(s) and r_hwchar.match(s[index+1]):
                width2 += 1

        # 互換動作: 1.28以降は行末に半角スペースがあると折り返し位置が変わる
        #           (イベントによるメッセージのみ)
        if cw.cwpy.sdata and not cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint()):
            if not wrapafter2 and index+1 < len(s) and s[index+1] == " " and mode in (2, 3):
                width2 += 1
                asciicnt = 0

        # 行折り返し処理
        if not spchar and cnt > width2:
            if defspchar2 and width2+1 < cnt:
                index = -(cnt - (width+1))
                if seq[-index] <> "\n":
                    seq.insert(index, "\n")
                cnt = 1
            elif width2 >= asciicnt > 0 and not defspchar2:
                if not get_char(s, index + 1) == "\n" and seq[-asciicnt] <> "\n":
                    seq.insert(-asciicnt, "\n")
                cnt = asciicnt
            elif index + 1 <= len(s) or not get_char(s, index + 1) == "\n":
                if index + 2 <= len(s) or not get_char(s, index + 2) == "\n":
                    seq.append("\n")
                    wrapafter = True
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

def format_title(format, d):
    """foobar2000の任意フォーマット文字列のような形式で
    文字列の構築を行う。
     * %%で囲われた文字列は変数となり、辞書dから得られる値に置換される。
     * []で囲われた文字列は、その内側で使用された変数がなければ丸ごと無視される。
     * \の次の文字列は常に通常文字となる。

    例えば次のようになる:
        d = { "application":"CardWirthPy", "skin":"スキン名", "yado":"宿名" }
        s = format_title("%application% %skin%[ - %yado%[ %scenario%]]", d)
        assert s == "CardWirthPy スキン名 - 宿名"
    """
    class _FormatPart(object):
        """フォーマット内の変数。"""
        def __init__(self, name):
            self.name = name

    def eat_parts(format, subsection):
        """formatを文字列とFormatPartのリストに分解。
        []で囲われた部分はサブリストとする。
        """
        list = []
        bs = False
        while format:
            c = format[0]
            format = format[1:]
            if bs:
                list.append(c)
                bs = False
            elif c == "\\":
                bs = True
            elif c == "]" and subsection:
                return format, list
            elif c == "%":
                ci = format.find("%")
                if ci <> -1:
                    list.append(_FormatPart(format[:ci]))
                    format = format[ci+1:]
            elif c == "[":
                format, list2 = eat_parts(format, True)
                list.append(list2)
            else:
                list.append(c)
        return format, list

    format, l = eat_parts(format, False)
    assert not format
    def do_format(l):
        """フォーマットを実行する。"""
        seq = []
        use = False
        for sec in l:
            if isinstance(sec, _FormatPart):
                name = d.get(sec.name, "")
                if name:
                    seq.append(name)
                    use = True
            elif isinstance(sec, list):
                str, use2 = do_format(sec)
                if use2:
                    seq.append(str)
                    use = True
            else:
                seq.append(sec)
        return "".join(seq), use

    return do_format(l)[0]

#-------------------------------------------------------------------------------
# wx汎用関数
#-------------------------------------------------------------------------------

def load_wxbmp(name="", mask=False, image=None, maskpos=(0, 0), f=None, retry=True):
    """pos(0,0)にある色でマスクしたwxBitmapを返す。"""
    if sys.platform <> "win32":
        assert threading.currentThread() <> cw.cwpy
    if not f and (not cw.binary.image.code_to_data(name) and not os.path.isfile(name)) and not image:
        return wx.EmptyBitmap(0, 0)

    if cw.cwpy.rsrc:
        name = cw.cwpy.rsrc.get_filepath(name)
    if mask:
        if not image:
            try:
                if f:
                    data = f.read()
                elif cw.binary.image.path_is_code(name):
                    data = cw.binary.image.code_to_data(name)
                else:
                    if not os.path.isfile(name):
                        return wx.EmptyBitmap(0, 0)
                    with open(name, "rb") as f2:
                        data = f2.read()

                data = cw.image.fix_cwnext16bitbitmap(data)
                with io.BytesIO(data) as f2:
                    image = wx.ImageFromStream(f2, wx.BITMAP_TYPE_ANY, -1)
            except:
                print u"画像が読み込めません(load_wxbmp)", name
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
            if not palette is None:
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
            print u"画像が読み込めません(load_wxbmp)", name
            return wx.EmptyBitmap(0, 0)

    return wxbmp

def fill_bitmap(dc, bmp, csize):
    """引数のbmpを敷き詰める。"""
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

def draw_witharound(dc, s, x, y, textcolor=wx.BLACK, framecolor=wx.WHITE):
    """テキストsを縁取りしながら描画する。"""
    for xv in xrange(x-1, x+2):
        for yv in xrange(y-1, y+2):
            if x <> xv or y <> yv:
                dc.SetTextForeground(framecolor)
                dc.DrawText(s, xv, yv)
    dc.SetTextForeground(textcolor)
    dc.DrawText(s, x, y)

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

def create_fileselection(parent, target, message, wildcard="*.*", dir=False, getbasedir=None, callback=None, winsize=False):
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
                    dpath = cw.util.relpath(dpath, base)
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
                    fpath = cw.util.relpath(fpath, base)
                target.SetValue(fpath)
                if callback:
                    callback(fpath)

    if winsize:
        size = (cw.wins(25), -1)
    else:
        size = (25, -1)
    button = wx.Button(parent, size=size, label=u"...")
    parent.Bind(wx.EVT_BUTTON, OnOpen, button)
    return button

class CWPyStaticBitmap(wx.Panel):
    """wx.StaticBitmapはアルファチャンネル付きの画像を
    正しく表示できない場合があるので代替する。
    """
    def __init__(self, parent, id, bmp, size=None):
        if not size and bmp:
            s = bmp.GetSize()
            size = (s[0], s[1])
        wx.Panel.__init__(self, parent, id, size=size)
        self.bmp = bmp
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0, True)

    def SetBitmap(self, bmp):
        self.bmp = bmp
        self.Refresh()

    def GetBitmap(self, bmp):
        return self.bmp

def abbr_longstr(dc, str, w):
    """ClientDCを使って長い文字列を省略して末尾に三点リーダを付ける。
    dc: ClientDC
    str: 編集対象の文字列
    w: 目標文字列長(pixel)
    """
    width = dc.GetTextExtent(str)[0]
    if width > w:
        while dc.GetTextExtent(str + u"...")[0] > w:
            str = str[:-1]
        str += u"..."
    return str

class CheckableListCtrl(wx.ListCtrl,
                        wx.lib.mixins.listctrl.CheckListCtrlMixin,
                        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin):
    """チェックボックス付きのリスト。"""
    def __init__(self, parent, id, size, style, colpos=0):
        wx.ListCtrl.__init__(self, parent, id, size=size, style=style|wx.LC_NO_HEADER)
        wx.lib.mixins.listctrl.CheckListCtrlMixin.__init__(self)
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)
#        w, h = self.GetImageList(wx.IMAGE_LIST_SMALL).GetSize(0)
        for i in xrange(colpos+1):
            self.InsertColumn(i, u"")

        self.InsertImageStringItem(0, u"", 0)
        rect = self.GetItemRect(0, wx.LIST_RECT_LABEL)
        self.SetColumnWidth(0, rect.x)
        self.DeleteAllItems()

        self.resizeLastColumn(0)

def add_sideclickhandlers(toppanel, leftbtn, rightbtn):
    """toppanelの左右の領域をクリックすると
    leftbtnまたはrightbtnのイベントが実行されるように
    イベントへのバインドを行う。
    """
    def _is_cursorinleft():
        rect = toppanel.GetClientRect()
        x, y = toppanel.ScreenToClient(wx.GetMousePosition())
        return x < rect.x + rect.width / 4 and leftbtn.IsEnabled()

    def _is_cursorinright():
        rect = toppanel.GetClientRect()
        x, y = toppanel.ScreenToClient(wx.GetMousePosition())
        return rect.x + rect.width / 4 * 3 < x and rightbtn.IsEnabled()

    def _update_mousepos():
        if _is_cursorinleft():
            toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_BACK"])
        elif _is_cursorinright():
            toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FORE"])
        else:
            toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])

    def OnMotion(evt):
        _update_mousepos()

    def OnLeftUp(evt):
        if _is_cursorinleft():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, leftbtn.GetId())
            leftbtn.ProcessEvent(btnevent)
        elif _is_cursorinright():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, rightbtn.GetId())
            rightbtn.ProcessEvent(btnevent)

    _update_mousepos()
    toppanel.Bind(wx.EVT_MOTION, OnMotion)
    toppanel.Bind(wx.EVT_LEFT_UP, OnLeftUp)

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

# CoInitialize()を呼び出し終えたスレッドのset
_cominit_table = set()

def _co_initialize():
    """スレッドごとにCoInitialize()を呼び出す。"""
    global _cominit_table
    if sys.platform <> "win32":
        return
    thr = threading.currentThread()
    if thr in _cominit_table:
        return # 呼び出し済み
    pythoncom.CoInitialize()
    _cominit_table.add(thr)
    # 終了したスレッドがあれば除去
    for thr2 in _cominit_table.copy():
        if not thr2.isAlive():
            _cominit_table.remove(thr2)

def get_linktarget(file):
    """fileがショートカットだった場合はリンク先を、
    そうでない場合はfileを返す。
    """
    if sys.platform <> "win32" or not file.lower().endswith(".lnk"):
        return file
    _co_initialize()
    shortcut = pythoncom.CoCreateInstance(win32com.shell.shell.CLSID_ShellLink, None,
                                          pythoncom.CLSCTX_INPROC_SERVER,
                                          win32com.shell.shell.IID_IShellLink)
    try:
        encoding = sys.getfilesystemencoding()
        STGM_READ = 0x00000000
        shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(file.encode(encoding), STGM_READ)
        file = shortcut.GetPath(win32com.shell.shell.SLGP_UNCPRIORITY)[0].decode(encoding)
    except Exception:
        print_ex()
        return file
    return join_paths(file)

def create_link(shortcutpath, targetpath):
    """targetpathへのショートカットを
    shortcutpathに作成する。
    """
    if sys.platform <> "win32":
        return
    dpath = os.path.dirname(shortcutpath)
    if not os.path.exists(dpath):
        os.makedirs(dpath)
    _co_initialize()
    targetpath = os.path.abspath(targetpath)
    shortcut = pythoncom.CoCreateInstance(win32com.shell.shell.CLSID_ShellLink, None,
                                          pythoncom.CLSCTX_INPROC_SERVER,
                                          win32com.shell.shell.IID_IShellLink)
    encoding = sys.getfilesystemencoding()
    shortcut.SetPath(targetpath.encode(encoding))
    shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(shortcutpath.encode(encoding), 0)

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

def t_reset():
    global times, dictimes
    times = map(lambda v: 0, times)
    dictimes.clear()

def t_print():
    global times, dictimes
    lines = []
    for i, t in enumerate(times):
        if 0 < t:
            s = "time[%s] = %s" % (i, t)
            lines.append(s)
            print s
    for key, t in dictimes.iteritems():
        if 0 < t:
            s = "time[%s] = %s" % (key, t)
            lines.append(s)
            print s
    if lines:
        with open("performance.txt", "w") as f:
            f.write("\n".join(lines))

def main():
    pass

if __name__ == "__main__":
    main()
