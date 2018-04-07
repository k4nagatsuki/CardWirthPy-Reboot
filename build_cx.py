#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import subprocess
import sys
import time
import zipfile

from cx_Freeze import setup, Executable

version = "3.0"

dist_dir = "CardWirthPy"
script = "cardwirth.py"
srcfile_name = "src.zip"

def compress_src(zpath):
    fnames = ("cardwirth.py", "build_cx.py", "build_py2exe.py", "build_pyi.py",
              "dailybuild.py", "CardWirthPy.ico",
              "CardWirthPy.manifest", "file_version_info.txt", "cardwirthpy.sh",
              "fix_movies.sh", "License.txt",
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

def build_exe():
    if os.path.isdir(dist_dir):
        print("*** Remove old files ***\n")
        for fname in os.listdir(dist_dir):
            fpath = os.path.join(dist_dir, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
            else:
                shutil.rmtree(fpath)

    # ビルド情報を生成する
    print("Create versioninfo.py.")
    date = datetime.datetime.today()
    s = "build_datetime = \"%s\"\n" % (date.strftime("%Y-%m-%d %H:%M:%S"))
    with open("versioninfo.py", "w") as f:
        f.write(s)

    # cx_Freezeによるビルド
    include_files = (
        "License.txt",
        "bass.dll",
    #    "bass_fx.dll",
    #    "bassmidi.dll",
    #    ("x64", "x64"),
        "ChangeLog.txt",
        "ReadMe.txt",
        ("Data/SoundFont", "Data/SoundFont"),
        ("Data/SkinBase", "Data/SkinBase"),
        ("Data/Debugger", "Data/Debugger"),
        ("Data/Materials", "Data/Materials"),
        ("Data/Compatibility.xml", "Data/Compatibility.xml"),
        ("Data/SystemCoupons.xml", "Data/SystemCoupons.xml"),
        ("Data/SearchEngines.xml", "Data/SearchEngines.xml"),
        ("Data/Sites.xml", "Data/Sites.xml"),
        ("Data/UpdateInfo.xml", "Data/UpdateInfo.xml"),
    )

    # BUG: cx_FreezeによるコピーでUnicodeDecodeError
    extra_data = (
        "bass_fx.dll",
        "bassmidi.dll",
        "x64",
    )

    extra_dirs = (
        "Scenario", "Yado", "Data/Temp", "Data/Skin",
         "Data/Face/Common", "Data/Face/Common-ADT", "Data/Face/Common-CHD", "Data/Face/Common-OLD", "Data/Face/Common-YNG",
         "Data/Face/Female", "Data/Face/Female-ADT", "Data/Face/Female-CHD", "Data/Face/Female-OLD", "Data/Face/Female-YNG",
         "Data/Face/Male", "Data/Face/Male-ADT", "Data/Face/Male-CHD", "Data/Face/Male-OLD", "Data/Face/Male-YNG"
     )

    options = {
        "build_exe": dist_dir,
        "optimize": 2,
        "include_files": include_files
    }

    for arg in sys.argv[1:]:
        if arg.startswith("-chm="):
            chmfile = arg[5:].strip("\"")
            sys.argv.remove(arg)
            break
    else:
        chmfile = ""

    if sys.platform == "win32":
        base = "Win32GUI"
        targetName = "CardWirthPy.exe"
    else:
        base = None
        targetName = "CardWirthPy"

    exe = Executable(script="cardwirth.py",
                     targetName=targetName,
                     base=base,
                     icon="CardWirthPy.ico")

    sys.argv = [sys.argv[0], "build"]
    setup(name="CardWirthPy",
          version=version,
          description="CardWirthPy",
          url="https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot/",
          executables=[exe],
          options={"build_exe": options})

    # 必要なファイルとフォルダをコピー・生成する
    print("\n*** Copying extra data ***")

    for dname in extra_dirs:
        path = os.path.join(dist_dir, dname)
        print("Creating %s" % (os.path.abspath(path)))
        os.makedirs(path)

    print("\n*** Creating new directory ***")

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

    if chmfile:
        path = os.path.basename(chmfile)
        print("Copying %s" % path)
        path = os.path.join(dist_dir, path)
        shutil.copy(chmfile, path)

    print("Remove versioninfo.py.")
    os.remove("versioninfo.py")

    print("\n*** Extra works ***")

    # BUG: sqlite3.dll が lib 以下にないと
    #      作業フォルダが実行ファイルの場所と異なる時に起動エラー
    #      VCRUNTIME140.dllはVCランタイムライブラリが無い環境で
    #      CardWirthPy.exeと同じフォルダに必要
    mvfiles = (
        ("sqlite3.dll", "lib/sqlite3.dll"),
        ("lib/VCRUNTIME140.dll", "VCRUNTIME140.dll"),
    )
    for src, dst in mvfiles:
        print("Moving %s to %s" % (src, dst))
        src = os.path.join(dist_dir, src)
        dst = os.path.join(dist_dir, dst)
        os.rename(src, dst)

    print("")

    # BUG: lib以下に不要なpython36.dll等が生成される
    rmfiles = (
        "lib/python36.dll",
        "lib/_ssl.pyd",
        "lib/wx/python36.dll",
        "lib/wx/libcairo-2.dll",
        "lib/wx/libexpat-1.dll",
        "lib/wx/_propgrid.cp36-win32.pyd",
        "lib/wx/wxmsw30u_propgrid_vc140.dll",
        "lib/wx/_ribbon.cp36-win32.pyd",
        "lib/wx/wxmsw30u_ribbon_vc140.dll",
        "lib/wx/wxmsw30u_webview_vc140.dll",
        "lib/wx/locale/af",
        "lib/wx/locale/an",
        "lib/wx/locale/ar",
        "lib/wx/locale/ca",
        "lib/wx/locale/ca@valencia",
        "lib/wx/locale/cs",
        "lib/wx/locale/da",
        "lib/wx/locale/de",
        "lib/wx/locale/el",
        "lib/wx/locale/es",
        "lib/wx/locale/eu",
        "lib/wx/locale/fi",
        "lib/wx/locale/fr",
        "lib/wx/locale/gl_ES",
        "lib/wx/locale/hi",
        "lib/wx/locale/hu",
        "lib/wx/locale/id",
        "lib/wx/locale/it",
        "lib/wx/locale/ko_KR",
        "lib/wx/locale/lt",
        "lib/wx/locale/lv",
        "lib/wx/locale/ms",
        "lib/wx/locale/nb",
        "lib/wx/locale/ne",
        "lib/wx/locale/nl",
        "lib/wx/locale/pl",
        "lib/wx/locale/pt",
        "lib/wx/locale/pt_BR",
        "lib/wx/locale/ro",
        "lib/wx/locale/ru",
        "lib/wx/locale/sk",
        "lib/wx/locale/sl",
        "lib/wx/locale/sq",
        "lib/wx/locale/sv",
        "lib/wx/locale/ta",
        "lib/wx/locale/tr",
        "lib/wx/locale/uk",
        "lib/wx/locale/vi",
        "lib/wx/locale/zh_CN",
        "lib/wx/locale/zh_TW",
        "lib/wx/VCRUNTIME140.dll",
        "lib/pygame/docs",
        "lib/pygame/tests",
        "lib/pygame/examples",
        "lib/pygame/python36.dll",
        "lib/pygame/VCRUNTIME140.dll",
        "lib/win32com/shell/python36.dll",
        "lib/win32com/shell/pythoncom36.dll",
        "lib/win32com/shell/pywintypes36.dll",
        "lib/win32com/shell/VCRUNTIME140.dll",
        "lib/pydoc_data",
    )
    for fname in rmfiles:
        print("Deleting %s" % fname)
        fpath = os.path.join(dist_dir, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
        else:
            shutil.rmtree(fpath)

    # 空ディレクトリの削除
    empties = []
    for dpath, dnames, fnames in os.walk(os.path.join(dist_dir, "lib")):
        if not dnames and not fnames:
            empties.append(dpath)
    for dpath in empties:
        print("Deleting %s" % dpath)
        while True:
            shutil.rmtree(dpath)
            dpath = os.path.dirname(dpath)
            if os.listdir(dpath):
                break

    print("\nCreating src.zip")
    compress_src(os.path.join(dist_dir, srcfile_name))

    print("\nCompleted build.")


if __name__ == '__main__':
    build_exe()
