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
import threading
import hashlib
import StringIO
import io

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

    def play(self, path):
        path = self.get_path(path)
        self._play(path)

    def _play(self, path):
        if not pygame.mixer or self.path == path:
            return

        if not os.path.isfile(path):
            self.stop()
        else:
            self.path = path
            self.set_volume()
            load_bgm(path)
            pygame.mixer.music.play(-1)

    def stop(self):
        if not pygame.mixer:
            return

        pygame.mixer.music.stop()
        self.path = ""
        # pygame.mixer.musicで読み込んだ音楽ファイルを解放する
        path = "DefReset" + cw.cwpy.rsrc.ext_bgm
        path = join_paths(cw.cwpy.setting.skindir, "Bgm", path)
        load_bgm(path)

    def set_volume(self, volume=None):
        if not pygame.mixer:
            return

        if volume is None:
            ext = os.path.splitext(self.path)[1].lower()

            if ext == ".mid" or ext == ".midi":
                volume = cw.cwpy.setting.vol_midi * cw.cwpy.setting.vol_bgm
            else:
                volume = cw.cwpy.setting.vol_bgm

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

def init(size=(640, 480), title=""):
    """pygame初期化。"""
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    scr = pygame.display.set_mode(size)
    clock = pygame.time.Clock()

    if title:
        pygame.display.set_caption(title)

    pygame.mixer.set_num_channels(2)
    pygame.event.set_blocked(None)
    pygame.event.set_allowed([KEYDOWN, MOUSEBUTTONUP, USEREVENT])
    return scr, clock

def convert_maskpos(maskpos, width, height):
    """maskposが座標ではなくキーワード'center'または'right'
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
            f = io.BytesIO(data)
            image = pygame.image.load(f)
            f.close()
        else:
            if not os.path.isfile(path):
                return pygame.Surface((0, 0)).convert()
            encoding = sys.getfilesystemencoding()
            image = pygame.image.load(path.encode(encoding))
    except:
        print u"画像が読み込めません", path
        return pygame.Surface((0, 0)).convert()

    # アルファチャンネルを持った透過画像を読み込んだ場合は
    # SRCALPHA(0x00010000)のフラグがONになっている
    if image.get_flags() & SRCALPHA:
        image = image.convert_alpha()
    else:
        image = image.convert()

        # GIFなどアルファチャンネルを持たない透過画像を読み込んだ場合は
        # すでにマスクカラーが指定されているので注意
        if mask and not image.get_colorkey():
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

def load_bgm(path):
    """Pathの音楽ファイルをBGMとして読み込む。
    リピートして鳴らす場合は、cw.audio.MusicInterface参照。
    path: 音楽ファイルのパス。
    """
    if not pygame.mixer or not os.path.isfile(path):
        return

    encoding = sys.getfilesystemencoding()

    try:
        pygame.mixer.music.load(path.encode(encoding))
    except:
        print u"BGMが読み込めません", path
        return

def load_sound(path):
    """効果音ファイルを読み込み、SoundInterfaceを返す。
    読み込めなかった場合は、無音で再生するSoundInterfaceを返す。
    path: 効果音ファイルのパス。
    """
    if not pygame.mixer or not os.path.isfile(path):
        return SoundInterface()

    encoding = sys.getfilesystemencoding()

    try:
        sound = pygame.mixer.Sound(path.encode(encoding))
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
    f= open( path, 'rb' )

    #header
    shead= struct.Struct( '>IHHHH' )
    fhead= f.read( shead.size )
    dhead= shead.unpack_from( fhead, 0 )

    #font directory
    stable= struct.Struct( '>4sIII' )
    ftable= f.read( stable.size* dhead[ 1 ] )
    for i in range( dhead[1] ): #directory records
        dtable= stable.unpack_from(
                ftable, i* stable.size )
        if dtable[0]== 'name': break
    assert dtable[0]== 'name'

    #name table
    f.seek( dtable[2] ) #at offset
    fnametable= f.read( dtable[3] ) #length
    snamehead= struct.Struct( '>HHH' ) #name table head
    dnamehead= snamehead.unpack_from( fnametable, 0 )

    sname= struct.Struct( '>HHHHHH' )
    fontname = ""

    for i in range( dnamehead[1] ): #name table records
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

    f.close()
    return fontname

def get_md5(path):
    """MD5を使ったハッシュ値を返す。
    path: ハッシュ値を求めるファイルのパス。
    """
    m = hashlib.md5()
    f = open(path, 'rb')

    while True:
        data = f.read(32768)

        if not data:
            break

        m.update(data)

    f.close()
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
          "  ..##.##..##.####.     ",
          " .####.####.######.     ",
          ".#####.#####.#..##.     ",
          ".#####.#####.#####.     ",
          ".#####.#####.#..##.     ",
          ".#####.#####.#####.     ",
          ".####...####.#####.     ",
          ".....###.....#####.     ",
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

    return path

def repl_dischar(fname):
    """
    ファイル名使用不可文字を代替文字に置換し、
    両端に空白があった場合は削除する。
    """
    d = {'\\': u'￥', '/': u'／', ':': u'：', ',': u'，', ';': u'；',
         '*': u'＊', '?': u'？','"': u'”', '<': u'＜', '>': u'＞','|': u'｜'}

    for key, value in d.iteritems():
        fname = fname.replace(key, value)

    return fname.strip()

def check_dischar(s):
    """
    ファイル名使用不可文字を含んでいるかチェックする。
    """
    seq = ('\\', '/', ':', ',', ';', '*', '?','"', '<', '>', '|')

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

    if os.path.isfile(temppath):
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

def decompress_zip(path, dstdir, dname=""):
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

            f = open(fpath, "wb")
            f.write(data)
            f.close()

    z.close()
    return dstdir

def decode_zipname(name):
    if not isinstance(name, unicode):
        try:
            name = name.decode("cp932")
        except UnicodeDecodeError:
            try:
                name = name.decode("euc-jp")
            except UnicodeDecodeError:
                name = name.decode("utf-8")

    return name

def read_zipdata(zfile, name):
    try:
        data = zfile.read(name)
    except KeyError:
        try:
            data = zfile.read(name.encode("cp932"))
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
    z = zipfile.ZipFile(zpath, "r")
    data = read_zipdata(z, name)
    z.close()
    f = StringIO.StringIO(data)
    element = cw.data.xml2element(name, tag, file=f)
    f.close()
    return element

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

def decodewrap(s):
    """\nを改行コードに戻す。"""
    r = []
    bs = False
    for c in s:
        if bs:
            if c == 'n':
                r.append('\n')
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

def txtwrap(s, mode, width=30, wrapschars=""):
    """引数の文字列を任意の文字数で改行する(全角は2文字として数える)。
    mode=1: カード解説。
    mode=2: 画像付きメッセージ（台詞）用。
    mode=3: 画像なしメッセージ用。
    mode=4: キャラクタ情報ダイアログの解説文・張り紙説明用。
    mode=5: 素質解説文用。
    """
    if mode == 1:
        wrapschars = u"｡|､|，|、|。|．|）|」|』|〕|｝|】"
        width = 37
    elif mode == 2:
        wrapschars = ""
        width = 32
    elif mode == 3:
        wrapschars = ""
        width = 42
    elif mode == 4:
        wrapschars = u"｡|､|，|、|。|．|）|」|』|〕|｝|】"
        width = 36
    elif mode == 5:
        wrapschars = u"｡|､|，|、|。|．|）|」|』|〕|｝|】"
        width = 24

    # \\nを改行コードに戻す
    s = s.replace("\\n", "\n")
    # 半角文字集合
    r_hwchar = re.compile(u"[ -~]|[｡-ﾟ]")
    # 行頭禁止文字集合
    r_wchar = re.compile(wrapschars) if wrapschars else None
    # 特殊文字記号集合
    r_spchar = re.compile("#[a-z]|&[a-z]") if mode in (2, 3) else None
    cnt = 0
    asciicnt = 0
    wraped = False
    skip = False
    seq = []

    for index, char in enumerate(s):
        if r_spchar:
            if skip:
                skip = False
                continue

            chars = char + get_char(s, index + 1)

            if r_spchar.match(chars.lower()):
                seq.append(chars)
                skip = True
                continue

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

            if char == " ":
                asciicnt = 0
            else:
                asciicnt += 1

        # 行頭禁止文字・改行記号・半角文字以外
        else:
            seq.append(char)
            cnt += 2
            asciicnt = 0

        # 行折り返し処理
        if cnt > width:
            if width >= asciicnt > 0:
                seq.insert(-asciicnt, "\n")
                cnt = asciicnt
            elif not get_char(s, index + 1) == "\n":
                seq.append("\n")
                cnt = 0
                asciicnt = 0
                wraped = False

    return "".join(seq)

def get_char(s, index):
    try:
        return s[index]
    except:
        return ""

#-------------------------------------------------------------------------------
# wx汎用関数
#-------------------------------------------------------------------------------

def load_wxbmp(name="", mask=False, image=None, maskpos=(0, 0), f=None):
    """pos(0,0)にある色でマスクしたwxBitmapを返す。"""
    if not f and not os.path.isfile(name) and not image:
        return wx.EmptyBitmap(0, 0)

    if mask:
        if not image:
            try:
                if f:
                    image = wx.ImageFromStream(f, wx.BITMAP_TYPE_ANY, -1)
                else:
                    image = wx.Image(name, wx.BITMAP_TYPE_ANY, -1)
            except:
                print u"画像が読み込めません。", name
                return wx.EmptyBitmap(0, 0)

        if not image.HasAlpha() and not image.HasMask():
            maskpos = convert_maskpos(maskpos, image.Width, image.Height)
            r = image.GetRed(maskpos[0], maskpos[1])
            g = image.GetGreen(maskpos[0], maskpos[1])
            b = image.GetBlue(maskpos[0], maskpos[1])
            image.SetMaskColour(r, g, b)

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

def main():
    pass

if __name__ == "__main__":
    main()
