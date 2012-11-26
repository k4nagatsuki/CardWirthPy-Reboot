#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct

import util


class CWFile(file):
    """fileクラスを継承し、CardWirthの生成した
    バイナリファイルを読み込むためのメソッドを追加したクラス。
    import binary
    binary.CWFile("test/Area1.wid", "rb")
    とやるとインスタンスオブジェクトが生成できる。
    """
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

        if multiline:
            s = util.repl_specialchar(s)

        s = util.repl_escapechar(s)
        return cw.util.encodewrap(s)

    def rawstring(self):
        dword = self.dword()

        if dword:
            return self.read(dword).decode("mbcs").strip("\x00")
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

if __name__ == '__main__':
    main()
