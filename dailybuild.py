#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import zipfile
import datetime

import build_cx
import dirdiff


def compress_all(zpath, targ):
    z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)

    for dpath, dnames, fnames in os.walk(targ):
        dpath2 = os.path.relpath(dpath, os.path.dirname(targ))
        for dname in dnames:
            fpath = os.path.join(dpath, dname)
            fpath2 = os.path.join(dpath2, dname)
            mtime = time.localtime(os.path.getmtime(fpath))[:6]
            zinfo = zipfile.ZipInfo(fpath2 + "/", mtime)
            z.writestr(zinfo, "")

        for fname in fnames:
            fpath = os.path.join(dpath, fname)
            fpath2 = os.path.join(dpath2, fname)
            z.write(fpath, fpath2)

    z.close()
    return zpath


if __name__ == '__main__':
    if 2 <= len(sys.argv):
        dir = sys.argv[1]
    else:
        dir = "."

    for arg in sys.argv:
        if arg.startswith("-diff-base="):
            diffbase = arg[11:].strip("\"")
            sys.argv.remove(arg)
            break
    else:
        diffbase = ""

    build_cx.build_exe()

    # フォント類は別配布するため削除
    shutil.rmtree(os.path.join(build_cx.dist_dir, "Data/SoundFont"))

    if diffbase and os.path.isdir(diffbase):
        distdir = os.path.join("dailybuild_tmp", build_cx.dist_dir)
        if os.path.isdir(distdir):
            shutil.rmtree(distdir)
        os.makedirs(distdir)
        dirdiff.create_dirdiff(dpath1=build_cx.dist_dir, dpath2=diffbase, target=distdir)
        shutil.copyfile(os.path.join(build_cx.dist_dir, "ReadMe.txt"), os.path.join(distdir, "ReadMe.txt"))
        shutil.copyfile(os.path.join(build_cx.dist_dir, "License.txt"), os.path.join(distdir, "License.txt"))
    else:
        distdir = build_cx.dist_dir

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
    compress_all(fpath, distdir)

    print("")
    print("Created %s." % (fpath))
    print("Completed daily build.")
