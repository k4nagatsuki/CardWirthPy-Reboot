#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import zipfile
import operator
import datetime

import build_exe

def compress_all(zpath, targ):
    encoding = sys.getfilesystemencoding()
    z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)

    for dpath, dnames, fnames in os.walk(targ):
        for dname in dnames:
            fpath = os.path.join(dpath, dname).encode(encoding)
            mtime = time.localtime(os.path.getmtime(fpath))[:6]
            zinfo = zipfile.ZipInfo(fpath + "/", mtime)
            z.writestr(zinfo, "")

        for fname in fnames:
            fpath = os.path.join(dpath, fname).encode(encoding)
            z.write(fpath, fpath)

    z.close()
    return zpath

if __name__ == '__main__':
    if operator.lt(len(sys.argv), 2):
        sys.argv.append('py2exe')
    exe = build_exe.BuildExe()
    exe.run()

    # フォントは別配布するため削除
    shutil.rmtree("CardWirthPy/Data/Font")

    fpath = datetime.datetime.today().strftime("%Y%m%d")

    mark = "a"
    if os.path.isfile("dailybuild.log"):
        f = open("dailybuild.log", "r")
        lines = f.readlines()
        f.close()
        if lines[0] == fpath:
            mark = lines[1][0]
            mark = ord(mark) + 1

    f = open("dailybuild.log", "w")
    f.write(fpath + "\n" + mark + "\n")
    f.close()

    if mark == "a":
        mark = ""
    fpath = "cardwirthpy_%s%s.zip" % (fpath, mark)
    compress_all(fpath, exe.dist_dir)

    print ""
    print "Created %s." % (fpath)
    print "Completed daily build."
