#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct

import io
import util

import cw.util


class CWFile(io.BufferedReader):
    """fileクラスを継承し、CardWirthの生成した
    バイナリファイルを読み込むためのメソッドを追加したクラス。
    import binary
    binary.CWFile("test/Area1.wid", "rb")
    とやるとインスタンスオブジェクトが生成できる。
    """
    def __init__(self, path, mode, decodewrap=False, f=None):
        if f:
            io.BufferedReader.__init__(self, f)
        else:
            f = io.FileIO(path, mode)
            io.BufferedReader.__init__(self, f)
        f.name = path
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

        if not self.decodewrap:
            s = cw.util.encodewrap(s)

        return s

    def rawstring(self):
        dword = self.dword()

        if dword:
            return unicode(self.read(dword), "mbcs").strip("\x00")
        else:
            return ""

    def byte(self):
        """byteの値を符号付きで返す。"""
        raw_data = self.read(1)
        data = struct.unpack("b", raw_data)
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

def main():
    pass

if __name__ == "__main__":
    main()
