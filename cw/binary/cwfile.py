#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import struct
import types

import cw.util

from typing import BinaryIO, Callable, List, Literal, Optional, Type, Union


class UnsupportedError(Exception):
    """指定されたエンジンバージョンで使用できない機能を
    逆変換しようとした際に投げられる。
    """
    def __init__(self, msg: Optional[str] = None, funcname: str = "") -> None:
        Exception.__init__(self)
        self.msg = msg
        self.funcname = funcname


class CWFile(object):
    """CardWirthの生成したバイナリファイルを
    読み込むためのメソッドを追加したBufferedReader。
    import cwfile
    cwfile.CWFile("test/Area1.wid", "rb")
    とやるとインスタンスオブジェクトが生成できる。
    """
    def __init__(self, path: str, mode: str, decodewrap: bool = False,
                 f: Optional[BinaryIO] = None) -> None:
        if f:
            self._f: Union[BinaryIO, io.BufferedReader] = f
        else:
            self._f = io.BufferedReader(io.FileIO(path, mode))
        self.filename = path
        self.filedata: List[bytes] = []
        self.decodewrap = decodewrap

    def __enter__(self) -> "CWFile":
        self._f.__enter__()
        return self

    def __exit__(self, t: Optional[Type[BaseException]], value: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> Literal[False]:
        self.close()
        return False

    def close(self) -> None:
        self._f.close()

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        return self._f.seek(offset, whence)

    def boolean(self) -> bool:
        """byteの値を真偽値にして返す。"""
        if self.byte():
            return True
        else:
            return False

    def string(self, multiline: bool = False) -> str:
        """dwordの値で読み込んだバイナリをユニコード文字列にして返す。
        dwordの値が"0"だったら空の文字列を返す。
        改行コードはxml置換用のために"\\n"に置換する。
        multiline: メッセージテクストなど改行の有効なテキストかどうか。
        """
        s = self.rawstring()

        if multiline and not self.decodewrap:
            s = cw.util.encodewrap(s)

        return s

    def rawstring(self) -> str:
        dword = self.dword()

        if dword:
            s = self.read(dword)
            return str(s, cw.MBCS, "replace").strip("\x00")
        else:
            return ""

    def byte(self) -> int:
        """byteの値を符号付きで返す。"""
        raw_data = self.read(1)
        value: int = struct.unpack("b", raw_data)[0]
        return value

    def ubyte(self) -> int:
        """符号無しbyteの値を符号付きで返す。"""
        raw_data = self.read(1)
        value: int = struct.unpack("B", raw_data)[0]
        return value

    def dword(self) -> int:
        """dwordの値(4byte)を符号付きで返す。リトルエンディアン。"""
        raw_data = self.read(4)
        assert len(raw_data) == 4, len(raw_data)
        value: int = struct.unpack("<l", raw_data)[0]
        return value

    def word(self) -> int:
        """wordの値(2byte)を符号付きで返す。リトルエンディアン。"""
        raw_data = self.read(2)
        value: int = struct.unpack("<h", raw_data)[0]
        return value

    def image(self) -> Optional[bytes]:
        """dwordの値で読み込んだ画像のバイナリデータを返す。
        dwordの値が"0"だったらNoneを返す。
        """
        dword = self.dword()

        if dword:
            return self.read(dword)
        else:
            return None

    def read(self, n: Optional[int] = None) -> bytes:
        if n is None:
            assert self._f.seekable()
            pos = self._f.tell()
            self._f.seek(0, io.SEEK_END)
            endpos = self._f.tell()
            self._f.seek(pos, io.SEEK_SET)
            n = endpos - pos
        raw_data = self._f.read(n)
        self.filedata.append(raw_data)
        return raw_data


class CWFileWriter(object):
    """CardWirth用のバイナリファイルを読み込むための
    メソッドを追加したBufferedWriter。
    """
    def __init__(self, path: str, mode: str, decodewrap: bool = False, targetengine: Optional[float] = None,
                 write_errorlog: Optional[Callable[[str], None]] = None) -> None:
        self._f = io.FileIO(path, mode)
        self.filename = path
        self.decodewrap = decodewrap
        self.targetengine = targetengine
        self.write_errorlog = write_errorlog

    def __enter__(self) -> "CWFileWriter":
        self._f.__enter__()
        return self

    def __exit__(self, t: Optional[Type[BaseException]], value: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> Literal[False]:
        self.close()
        return False

    def close(self) -> None:
        self._f.close()

    def tell(self) -> int:
        return self._f.tell()

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        return self._f.seek(offset, whence)

    def truncate(self, size: Optional[int] = None) -> int:
        return self._f.truncate(size)

    def flush(self) -> None:
        self._f.flush()

    def check_version(self, engineversion: float, funcname: str = "") -> None:
        """指定されたエンジンバージョンよりもengineversionが
        新しければUnsupportedErrorを投げる。
        """
        if self.targetengine is None:
            return
        if isinstance(engineversion, str):
            raise UnsupportedError(funcname=funcname)
        else:
            if self.targetengine < engineversion:
                raise UnsupportedError(funcname=funcname)

    def check_wsnversion(self, wsnversion: str, funcname: str = "") -> None:
        """指定されたWSNデータバージョンにかかわらず
        UnsupportedErrorを投げる。
        """
        raise UnsupportedError(funcname=funcname)

    def check_bgmoptions(self, data: "cw.data.CWPyElement") -> None:
        if data.getint(".", "volume", 100) != 100:
            self.check_wsnversion("1", "BGM音量の指定")
        if data.getint(".", "loopcount", 0) != 0:
            self.check_wsnversion("1", "BGMループ回数の指定")
        if data.getint(".", "channel", 0) != 0:
            self.check_wsnversion("1", "BGM再生チャンネルの指定")
        if data.getint(".", "fadein", 0) != 0:
            self.check_wsnversion("1", "BGMフェードイン")

    def check_soundoptions(self, data: "cw.data.CWPyElement") -> None:
        if data.getint(".", "volume", 100) != 100:
            self.check_wsnversion("1", "効果音音量の指定")
        if data.getint(".", "loopcount", 1) != 1:
            self.check_wsnversion("1", "効果音ループ回数の指定")
        if data.getint(".", "channel", 0) != 0:
            self.check_wsnversion("1", "効果音再生チャンネルの指定")
        if data.getint(".", "fadein", 0) != 0:
            self.check_wsnversion("1", "効果音フェードイン")

    def write_bool(self, b: bool) -> None:
        self.write_byte(1 if b else 0)

    def write_string(self, s: str, multiline: bool = False) -> None:
        if s is None:
            s = ""
        if multiline and not self.decodewrap:
            s = cw.util.decodewrap(s, "\r\n")
        self.write_rawstring(s)

    def write_rawstring(self, s: str) -> None:
        if s:
            try:
                s += "\x00"
                b = s.encode(cw.MBCS)
            except UnicodeEncodeError:
                seq = []
                for c in s:
                    try:
                        seq.append(c.encode(cw.MBCS))
                    except UnicodeEncodeError:
                        seq.append(b"?")
                b = b"".join(seq)
            self.write_dword(len(b))
            self._f.write(b)
        else:
            self.write_dword(1)
            self.write_byte(0)

    def write_byte(self, b: int) -> None:
        self._f.write(struct.pack("b", b))

    def write_ubyte(self, b: int) -> None:
        self._f.write(struct.pack("B", b))

    def write_dword(self, dw: int) -> None:
        self._f.write(struct.pack("<l", dw))

    def write_word(self, w: int) -> None:
        self._f.write(struct.pack("<h", w))

    def write_image(self, image: Optional[bytes]) -> None:
        if image:
            self.write_dword(len(image))
            self._f.write(image)
        else:
            self.write_dword(0)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
