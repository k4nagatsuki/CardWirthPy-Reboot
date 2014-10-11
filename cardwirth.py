#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

import cw

sys.setrecursionlimit(1073741824)

def main():
    if len(cw.SKIN_CONV_ARGS) > 0:
        os.chdir(os.path.dirname(sys.argv[0]) or '.')

    app = cw.frame.MyApp(0)
    app.MainLoop()

if __name__ == "__main__":
    main()
