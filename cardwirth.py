#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import io
import os
import sys
import time

import cw


put_errorlog = ""

if getattr(sys, 'frozen', False) or True:
    cw.exepath = sys.executable
    class WriteError(io.RawIOBase):
        def __init__(self):
            self.f = None
            self._last_time = 0
        def _open(self):
            if cw.quit:
                return
            global put_errorlog
            if not self.f:
                name = sys.executable + ".log"
                self.f = open(name, "a", encoding="utf-8")
                if 0 < self.tell():
                    self.f.write("\n")
                    self.f.write("-"*50)
                    self.f.write("\n")
                vstr = []
                for v in cw.APP_VERSION:
                    vstr.append(str(v))
                self.f.write("Version : %s" % ".".join(vstr))
                try:
                    import versioninfo
                    self.f.write(" / %s" % (versioninfo.build_datetime))
                    self.f.write("\n")
                except ImportError:
                    pass
                self._write_datetime()
                put_errorlog = os.path.basename(name)
                self._last_time = time.time()
        def _write_datetime(self):
            d = datetime.datetime.today()
            self.f.write(d.strftime("DateTime: %Y-%m-%d %H:%M:%S\n"))
        def close(self):
            if self.f:
                return self.f.close()
        @property
        def closed(self):
            if self.f:
                return self.f.closed
            else:
                return True
        def fileno(self):
            if cw.quit:
                return None
            self._open()
            return self.f.fileno()
        def flush(self):
            if self.f:
                return self.f.flush()
        def seek(self, offset, whence=io.SEEK_SET):
            if cw.quit:
                return
            self._open()
            return self.f.seek(offset, whence)
        def seekable(self):
            if cw.quit:
                return False
            self._open()
            return self.f.seekable()
        def tell(self):
            if cw.quit:
                return 0
            self._open()
            return self.f.tell()
        def truncate(self, size=None):
            if cw.quit:
                return
            self._open()
            return self.f.truncate(size)
        def writable(self):
            if cw.quit:
                return False
            self._open()
            return True
        def writelines(self, lines):
            if cw.quit:
                return
            if self.f and self._last_time + 1.0 <= time.time():
                # 前回の出力から1秒以上経っていたら時刻を再出力
                self.f.write("\n")
                self._write_datetime()
            self._open()
            r = self.f.writelines(lines)
            self.f.flush()
            if sys.__stderr__:
                sys.__stderr__.writelines(lines)
            self._last_time = time.time()
            return r
        def write(self, b):
            if cw.quit:
                return
            if self.f and self._last_time + 1.0 <= time.time():
                self.f.write("\n")
                self._write_datetime()
            self._open()
            print(b, end="")
            r = self.f.write(b)
            self.f.flush()
            if sys.__stderr__:
                sys.__stderr__.write(b)
            self._last_time = time.time()
            return r
        def __del__(self):
            if self.f:
                del self.f
    sys.stderr = WriteError()
else:
    cw.exepath = __file__

sys.setrecursionlimit(1073741824)


def main():
    if len(cw.SKIN_CONV_ARGS) > 0:
        os.chdir(os.path.dirname(sys.argv[0]) or '.')
    if sys.platform == "darwin":
        # macOS で app bundle 内から実行されたときは、app bundle がある
        # ディレクトリに chdir する
        if (os.path.dirname(sys.argv[0]).endswith(".app/Contents/Resources") and
            "RESOURCEPATH" in os.environ and
            os.path.abspath(os.environ["RESOURCEPATH"]) == os.path.dirname(os.path.abspath(sys.argv[0]))):
            os.chdir(os.path.join(os.environ["RESOURCEPATH"], "..", "..", ".."))
    try:
        app = cw.frame.MyApp()
        app.MainLoop()
    except:
        cw.util.print_ex(file=sys.stderr)
    finally:
        cw.util.clear_mutex()
        sys.stderr.close()

    if put_errorlog:
        import win32api
        import win32con
        win32api.MessageBox(None, "CardWirthPyの実行中にエラーが発生しました。\n" +
                            put_errorlog + "の内容を開発者までお知らせください。",
                            "CardWirthPyエラー", win32con.MB_OK|win32con.MB_ICONERROR)


if __name__ == "__main__":
    main()
