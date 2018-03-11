#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
import sys

import cw


encoding = sys.getfilesystemencoding()
try:
    cw.exepath = __file__.decode(encoding)
except NameError:
    cw.exepath = sys.executable.decode(encoding)


sys.setrecursionlimit(1073741824)

if sys.platform <> "win32":
    # リダイレクトした場合でも UnicodeError を起こさないように
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf8')(sys.stderr)


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
    finally:
        cw.util.clear_mutex()


if __name__ == "__main__":
    main()
