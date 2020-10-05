#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import io
import os
import re
import sys
import time
import types

import cw

from typing import Iterable, List, Literal, Optional, TextIO, Type, Iterator

put_errorlog = ""


class WriteError(TextIO):
    def __init__(self):
        self.f: Optional[TextIO] = None
        self._last_time = 0
        self._re_fpath = re.compile("^\\s*File\\s\"(.+?)\"", re.IGNORECASE)
        self._sep = os.sep

    def _open(self) -> None:
        if cw.quit_app:
            return
        global put_errorlog
        if not self.f:
            name = cw.exepath + ".log"
            self.f = open(name, "a", encoding="utf-8")
            assert self.f is not None
            if 0 < self.tell():
                self.f.write("\n")
                self.f.write("-"*50)
                self.f.write("\n")
            vstr = []
            for v in cw.APP_VERSION:
                vstr.append(str(v))
            if sys.maxsize == 0x7fffffff:
                bits = "32-bit"
            elif sys.maxsize == 0x7fffffffffffffff:
                bits = "64-bit"
            else:
                assert False
            self.f.write("Version : %s (%s)" % (".".join(vstr), bits))
            try:
                import versioninfo
                self.f.write(" / %s" % (versioninfo.build_datetime))
                self.f.write("\n")
            except ImportError:
                pass
            self._write_datetime()
            put_errorlog = os.path.basename(name)
            self._last_time = time.process_time()

    def _write_datetime(self):
        d = datetime.datetime.today()
        self.f.write(d.strftime("DateTime: %Y-%m-%d %H:%M:%S\n"))

    def close(self) -> None:
        if self.f:
            self.f.close()

    @property
    def closed(self) -> bool:
        if self.f:
            return self.f.closed
        else:
            return True

    def fileno(self) -> int:
        if cw.quit_app:
            return 0
        self._open()
        assert self.f is not None
        return self.f.fileno()

    def flush(self) -> None:
        if self.f:
            self.f.flush()

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if cw.quit_app:
            return 0
        self._open()
        assert self.f is not None
        return self.f.seek(offset, whence)

    def seekable(self) -> bool:
        if cw.quit_app:
            return False
        self._open()
        assert self.f is not None
        return self.f.seekable()

    def tell(self) -> int:
        if cw.quit_app:
            return 0
        self._open()
        assert self.f is not None
        return self.f.tell()

    def truncate(self, size: Optional[int] = None) -> int:
        if cw.quit_app:
            return 0
        self._open()
        assert self.f is not None
        return self.f.truncate(size)

    def writable(self) -> bool:
        if cw.quit_app:
            return False
        self._open()
        assert self.f is not None
        return True

    def writelines(self, lines: Iterable[str]) -> None:
        if cw.quit_app:
            return
        if self.f and self._last_time + 1.0 <= time.process_time():
            # 前回の出力から1秒以上経っていたら時刻を再出力
            self.f.write("\n")
            self._write_datetime()
        self._open()
        assert self.f is not None
        self.f.writelines(lines)
        self.f.flush()
        if sys.__stderr__:
            sys.__stderr__.writelines(lines)
        self._last_time = time.process_time()

    def write(self, b: str) -> int:
        if cw.quit_app:
            return 0
        if self.f and self._last_time + 1.0 <= time.process_time():
            self.f.write("\n")
            self._write_datetime()
        self._open()
        assert self.f is not None
        r = self.f.write(b)
        self.f.flush()
        if sys.__stderr__:
            sys.__stderr__.write(b)
        self._last_time = time.process_time()
        return r

    def isatty(self) -> bool:
        if cw.quit_app:
            return False
        self._open()
        assert self.f is not None
        return self.f.isatty()

    def readable(self) -> bool:
        return False

    def read(self, n: int = 0) -> str:
        raise IOError()

    def readline(self, limit: int = 0) -> str:
        raise IOError()

    def readlines(self, hint: int = 0) -> List[str]:
        raise IOError()

    def __del__(self) -> None:
        if self.f:
            del self.f

    def __next__(self) -> str:
        raise IOError()

    def __iter__(self) -> Iterator[str]:
        raise IOError()

    def __enter__(self) -> TextIO:
        return TextIO.__enter__(self)

    def __exit__(self, t: Optional[Type[BaseException]], value: Optional[BaseException],
                 traceback: Optional[types.TracebackType]) -> Literal[False]:
        self.close()
        return False


if getattr(sys, 'frozen', False):
    cw.exepath = sys.executable
    sys.stderr = WriteError()
else:
    cw.exepath = __file__

sys.setrecursionlimit(1073741824)


def main() -> None:
    if len(cw.SKIN_CONV_ARGS) > 0:
        os.chdir(os.path.dirname(sys.argv[0]) or '.')
    if sys.platform == "darwin":
        # macOS で app bundle 内から実行されたときは、app bundle がある
        # ディレクトリに chdir する
        if (os.path.dirname(sys.argv[0]).endswith(".app/Contents/Resources") and
            "RESOURCEPATH" in os.environ and
                os.path.abspath(os.environ["RESOURCEPATH"]) == os.path.dirname(os.path.abspath(sys.argv[0]))):
            os.chdir(os.path.join(os.environ["RESOURCEPATH"], "..", "..", ".."))
    cw.fsync.start()
    try:
        app = cw.frame.MyApp()
        app.MainLoop()
    except Exception:
        cw.util.print_ex(file=sys.stderr)
    finally:
        cw.util.clear_mutex()
        cw.fsync.sync()
        cw.fsync.quit()
        sys.stderr.close()

    if put_errorlog:
        import win32api
        import win32con
        win32api.MessageBox(None, "CardWirthPyの実行中にエラーが発生しました。\n" +
                            put_errorlog + "の内容を開発者までお知らせください。",
                            "CardWirthPyエラー", win32con.MB_OK | win32con.MB_ICONERROR)


if __name__ == "__main__":
    main()
