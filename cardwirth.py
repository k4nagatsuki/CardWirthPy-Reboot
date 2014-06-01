#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import ctypes

import cw

sys.setrecursionlimit(1073741824)

def create_mutex():
    handle = True

    # 二重起動防止 for Windows
    if sys.platform == "win32":
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexA(None, 1, cw.APP_NAME)
        err = kernel32.GetLastError()

        if err == ERROR_ALREADY_EXISTS:
            handle = None

    return handle

def main():
    handle = create_mutex()

    if handle:
        if len(sys.argv) > 1:
            os.chdir(os.path.dirname(sys.argv[0]) or '.')

        app = cw.frame.MyApp(0)
        app.MainLoop()

if __name__ == "__main__":
    main()
