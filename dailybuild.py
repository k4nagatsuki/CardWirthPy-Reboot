#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import zipfile
import datetime

import build_cx


def compress_all(zpath, targ):
    z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)

    for dpath, dnames, fnames in os.walk(targ):
        for dname in dnames:
            fpath = os.path.join(dpath, dname)
            mtime = time.localtime(os.path.getmtime(fpath))[:6]
            zinfo = zipfile.ZipInfo(fpath + "/", mtime)
            z.writestr(zinfo, "")

        for fname in fnames:
            fpath = os.path.join(dpath, fname)
            z.write(fpath, fpath)

    z.close()
    return zpath

if __name__ == '__main__':
    if 2 <= len(sys.argv):
        dir = sys.argv[1]
    else:
        dir = "."

    build_cx.build_exe()

    # フォント類は別配布するため削除
    shutil.rmtree(os.path.join(build_cx.dist_dir, "Data/SoundFont"))

    fpath = datetime.datetime.today().strftime("%Y%m%d")

    if sys.maxsize == 0x7fffffff:
        logname = "dailybuild.log"
    elif sys.maxsize == 0x7fffffffffffffff:
        logname = "dailybuild_x64.log"
    else:
        assert False

    mark = "a"
    if os.path.isfile(logname):
        f = open(logname, "r")
        lines = f.readlines()
        f.close()
        if lines[0].strip() == fpath:
            mark = lines[1][0]
            mark = chr(ord(mark) + 1)

    f = open(logname, "w")
    f.write(fpath + "\n" + mark + "\n")
    f.close()

    if mark == "a":
        mark = ""
    if sys.maxsize == 0x7fffffff:
        fpath = "cardwirthpy_%s%s_x86.zip" % (fpath, mark)
    elif sys.maxsize == 0x7fffffffffffffff:
        fpath = "cardwirthpy_%s%s_x64.zip" % (fpath, mark)
    else:
        assert False
    fpath = os.path.join(dir, fpath)
    compress_all(fpath, build_cx.dist_dir)

    print("")
    print("Created %s." % (fpath))
    print("Completed daily build.")
