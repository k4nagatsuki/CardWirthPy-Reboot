#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct

import io
from email import message

import cw.util


class UnsupportedError(Exception):
    """指定されたエンジンバージョンで使用できない機能を
    逆変換しようとした際に投げられる。
    """
    def __init__(self, msg=None):
        Exception.__init__(self)
        self.msg = msg


class CWFile(io.BufferedReader):
    """CardWirthの生成したバイナリファイルを
    読み込むためのメソッドを追加したBufferedReader。
    import cwfile
    cwfile.CWFile("test/Area1.wid", "rb")
    とやるとインスタンスオブジェクトが生成できる。
    """
    def __init__(self, path, mode, decodewrap=False, f=None):
        if f:
            io.BufferedReader.__init__(self, f)
        else:
            f = io.FileIO(path, mode)
            io.BufferedReader.__init__(self, f)
        f.name = path
        self.filedata = []
        self.decodewrap = decodewrap

    def bool(self):
        """byteの値を真偽値にして返す。"""
        if self.byte():
            return True
        else:
            return False

    def string(self, multiline=False):
        """dwordの値で読み込んだバイナリをユニコード文字列にして返す。
        dwordの値が"0"だったら空の文字列を返す。
        改行コードはxml置換用のために"\\n"に置換する。
        multiline: メッセージテクストなど改行の有効なテキストかどうか。
        """
        s = self.rawstring()

        if multiline and not self.decodewrap:
            s = cw.util.encodewrap(s)

        return s

    def rawstring(self):
        dword = self.dword()

        if dword:
            return unicode(self.read(dword), cw.MBCS).strip("\x00")
        else:
            return ""

    def byte(self):
        """byteの値を符号付きで返す。"""
        raw_data = self.read(1)
        data = struct.unpack("b", raw_data)
        return data[0]

    def ubyte(self):
        """符号無しbyteの値を符号付きで返す。"""
        raw_data = self.read(1)
        data = struct.unpack("B", raw_data)
        return data[0]

    def dword(self):
        """dwordの値(4byte)を符号付きで返す。リトルエンディアン。"""
        raw_data = self.read(4)
        data = struct.unpack("<l", raw_data)
        return data[0]

    def word(self):
        """wordの値(2byte)を符号付きで返す。リトルエンディアン。"""
        raw_data = self.read(2)
        data = struct.unpack("<h", raw_data)
        return data[0]

    def image(self):
        """dwordの値で読み込んだ画像のバイナリデータを返す。
        dwordの値が"0"だったらNoneを返す。
        """
        dword = self.dword()

        if dword:
            return self.read(dword)
        else:
            return None

    def read(self, n=None):
        raw_data = io.BufferedReader.read(self, n)
        self.filedata.append(raw_data)
        return raw_data

class CWFileWriter(io.BufferedWriter):
    """CardWirth用のバイナリファイルを読み込むための
    メソッドを追加したBufferedWriter。
    """
    def __init__(self, path, mode, decodewrap=False,
                 targetengine=None, write_errorlog=None):
        f = io.FileIO(path, mode)
        io.BufferedWriter.__init__(self, f)
        f.name = path
        self.decodewrap = decodewrap
        self.targetengine = targetengine
        self.write_errorlog = write_errorlog

    def check_version(self, engineversion):
        """指定されたエンジンバージョンよりもengineversionが
        新しければUnsupportedErrorを投げる。
        """
        if self.targetengine is None:
            return
        if isinstance(engineversion, (str, unicode)):
            raise UnsupportedError()
        else:
            if self.targetengine < engineversion:
                raise UnsupportedError()

    def check_wsnversion(self, wsnversion):
        """指定されたWSNデータバージョンにかかわらず
        UnsupportedErrorを投げる。
        """
        raise UnsupportedError()

    def check_bgmoptions(self, data):
        if data.getint(".", "volume", 100) <> 100:
            self.check_wsnversion("1")
        if data.getint(".", "loopcount", 0) <> 0:
            self.check_wsnversion("1")
        if data.getint(".", "channel", 0) <> 0:
            self.check_wsnversion("1")
        if data.getint(".", "fadein", 0) <> 0:
            self.check_wsnversion("1")

    def check_soundoptions(self, data):
        if data.getint(".", "volume", 100) <> 100:
            self.check_wsnversion("1")
        if data.getint(".", "loopcount", 1) <> 1:
            self.check_wsnversion("1")
        if data.getint(".", "channel", 0) <> 0:
            self.check_wsnversion("1")
        if data.getint(".", "fadein", 0) <> 0:
            self.check_wsnversion("1")

    def write_bool(self, b):
        self.write_byte(1 if b else 0)

    def write_string(self, s, multiline=False):
        if s is None:
            s = ""
        if multiline and not self.decodewrap:
            s = cw.util.decodewrap(s, "\r\n")
        self.write_rawstring(s)

    def write_rawstring(self, s):
        if s:
            s = (s + "\x00").encode(cw.MBCS)
            self.write_dword(len(s))
            self.write(s)
        else:
            self.write_dword(1)
            self.write_byte(0)

    def write_byte(self, b):
        self.write(struct.pack("b", b))

    def write_ubyte(self, b):
        self.write(struct.pack("B", b))

    def write_dword(self, dw):
        self.write(struct.pack("<l", dw))

    def write_word(self, w):
        self.write(struct.pack("<h", w))

    def write_image(self, image):
        if image:
            self.write_dword(len(image))
            self.write(image)
        else:
            self.write_dword(0)

def main():
    pass

if __name__ == "__main__":
    main()
