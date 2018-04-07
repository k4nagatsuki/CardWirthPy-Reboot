#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import subprocess
import sys
import time
import zipfile

pyi = "C:\\Program Files (x86)\\Python36-32\\Scripts\\pyinstaller.exe"
dist_dir = "CardWirthPy"
script = "cardwirth.py"
srcfile_name = "src.zip"

def build_exe():
    options = (
        script,
        "--distpath " + dist_dir,
        "--onedir",
        "-w",
        "-n CardWirthPy",
        "-i CardWirthPy.ico",
        "--manifest CardWirthPy.manifest",
        "--version-file file_version_info.txt",
    )

    extra_data = (
        #"Data/Font",
        "Data/SoundFont", "Data/SkinBase",
        "Data/Debugger", "Data/Materials",
        "Data/Compatibility.xml", "Data/SystemCoupons.xml", "Data/SearchEngines.xml",
        "License.txt",# "msvcr90.dll", "msvcp90.dll", "gdiplus.dll",
        "bass.dll", "bass_fx.dll", "bassmidi.dll", "x64",
        "ChangeLog.txt",# "Microsoft.VC90.CRT.manifest",
        "ReadMe.txt"
    )
    extra_dirs = (
        "Scenario", "Yado", "Data/Temp", "Data/Skin",
         "Data/Face/Common", "Data/Face/Common-ADT", "Data/Face/Common-CHD", "Data/Face/Common-OLD", "Data/Face/Common-YNG",
         "Data/Face/Female", "Data/Face/Female-ADT", "Data/Face/Female-CHD", "Data/Face/Female-OLD", "Data/Face/Female-YNG",
         "Data/Face/Male", "Data/Face/Male-ADT", "Data/Face/Male-CHD", "Data/Face/Male-OLD", "Data/Face/Male-YNG"
     )

    for arg in sys.argv[1:]:
        if arg.startswith("-chm="):
            chmfile = arg[5:].strip("\"")
            sys.argv.remove(arg)
            break
    else:
        chmfile = ""

    def compress_src(zpath):
        fnames = ("cardwirth.py", "build_exe.py", "dailybuild.py", "CardWirthPy.ico",
                  "CardWirthPy.manifest", "file_version_info.txt", "cardwirthpy.sh",
                  "fix_movies.sh", "License.txt",# "Microsoft.VC90.CRT.manifest",
                  "ReadMe.txt", "ChangeLog.txt")
        z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)

        for fname in fnames:
            fpath = fname
            z.write(fpath, fpath)

        for dpath, dnames, fnames in os.walk("cw"):
            if os.path.basename(dpath) == "__pycache__":
                continue

            for dname in dnames:
                if dname == "__pycache__":
                    continue
                fpath = os.path.join(dpath, dname)
                mtime = time.localtime(os.path.getmtime(fpath))[:6]
                zinfo = zipfile.ZipInfo(fpath + "/", mtime)
                z.writestr(zinfo, "")

            for fname in fnames:
                ext = os.path.splitext(fname)[1]

                if ext in (".py", ".c", ".sh", ".bat", ".so", ".pyd"):
                    fpath = os.path.join(dpath, fname)
                    z.write(fpath, fpath)

        z.close()
        return zpath

    # ビルド情報を生成する
    print("Create versioninfo.py.")
    date = datetime.datetime.today()
    s = "build_datetime = \"%s\"\n" % (date.strftime("%Y-%m-%d %H:%M:%S"))
    with open("versioninfo.py", "w") as f:
        f.write(s)

    try:
        if os.path.isdir(dist_dir):
            print("*** Remove old files ***\n")
            shutil.rmtree(dist_dir)

        s = "\"" + pyi + "\" " + " ".join(options)
        print(s)
        subprocess.Popen(s).wait()

        print("\n*** Copying extra data ***")

        for fname in extra_data:
            print("Copying %s" % (fname))
            fpath = os.path.join(dist_dir, fname)
            dpath = os.path.dirname(fpath)
            if not os.path.isdir(dpath):
                os.makedirs(dpath)
            if os.path.isdir(fname):
                shutil.copytree(fname, fpath)
            else:
                shutil.copy(fname, fpath)

        print("\n*** Creating new directory ***")

        for dname in extra_dirs:
            path = os.path.join(dist_dir, dname)
            print("Creating %s" % (os.path.abspath(path)))
            os.makedirs(path)

        if chmfile:
            path = os.path.basename(chmfile)
            path = os.path.join(dist_dir, path)
            shutil.copy(chmfile, path)

        compress_src(os.path.join(dist_dir, srcfile_name))

        print("\nCompleted build.")

    finally:
        print("Remove versioninfo.py.")
        os.remove("versioninfo.py")

if __name__ == '__main__':
    build_exe()
