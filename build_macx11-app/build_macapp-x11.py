#! /usr/bin/python2.7
# -*- coding: utf-8 -*-



from setuptools import setup
from glob import glob

import os
import sys
import shutil
import subprocess
import compileall
import tempfile
import re
import zipfile
import marshal
import imp
import struct
from datetime import datetime
import time

APP_VERSION = "2.1"
APP_NAME = "CardWirthPy"
APP_IDENT = "org.bitbucket.k4nagatsuki.cardwirth-py"
APP_COPYRIGHT = "Copyright © 2008-2010,2014-2017 logの中の人, k4nagatsuki and contributers, All Rights Reserved"

build_dir = "build"
dist_dir = "."
dist_contents = os.path.join(
    dist_dir, "%s.app" % APP_NAME, "Contents")
dist_resources = os.path.join(
    dist_contents, "Resources")

MAIN_SCRIPT = os.path.join(os.path.dirname(sys.argv[0]), 'cardwirth_boot.py')

python_path = "/usr/bin/python2.7"

def py2app():
    APP = [ MAIN_SCRIPT ]
    DATA_FILES = []
    OPTIONS = {
        'iconfile': os.path.join(os.path.dirname(sys.argv[0]),
                                 'CardWirthPy.icns'),
        'optimize': '2',
        'dylib_excludes': ",".join(
            glob('/opt/X11/lib/lib*.dylib')
        ),
        'includes': "cw",
        'resources': ",".join(
            glob('lib/*.dylib') + [ "cardwirth.py" ]
        ),
        'argv_emulation': True,
        'arch': "x86_64",
        'dist_dir': dist_dir,
        'plist': {
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleGetInfoString': "CardWrithPy",
            'CFBundleIdentifier': APP_IDENT,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHumanReadableCopyright': APP_COPYRIGHT,
        }
    }

    sys.path.insert(0, '.')
    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
    sys.path.pop()

    # remove unused links
    try:
        os.remove(os.path.join(dist_resources, "include"))
    except:
        pass
    try:
        os.remove(os.path.join(dist_resources, "lib", "python2.7", "config"))
    except:
        pass
    try:
        os.remove(os.path.join(dist_contents, "MacOS", "python"))
    except:
        pass
    os.symlink(python_path, os.path.join(dist_contents, "MacOS", "python"))
    shutil.copy(
        os.path.join(os.path.dirname(sys.argv[0]), 'bundle_main'),
        os.path.join(dist_resources, "cardwirthpy"))

    app_bundle = os.path.join(dist_dir, APP_NAME + ".app")
    if not os.path.isdir(app_bundle):
        raise Exception("Application bundle %s is not found" % app_bundle)
    py2app_hack(app_bundle)

def py2app_hack(app_bundle):
    boot_py = os.path.join(app_bundle, "Contents", "Resources", "__boot__.py")
    site_package = os.path.join(
        app_bundle, "Contents", "Resources", "lib", "python2.7",
        "site-packages.zip")

    boot_py_hack(boot_py)
    replace_loader("cw/_imageretouch_mac.so", site_package)

def boot_py_hack(filename):
    """
    __boot__.pyを書き換えて、非asciiなパスにおいても実行できるようにする。
    """
    tmpfd, tmpfile = tempfile.mkstemp(dir=os.path.dirname(filename))
    os.close(tmpfd)
    with open(filename, 'r') as infile:
        with open(tmpfile, 'w') as outfile:
            for line in infile:
                outfile.write(line)
                if line.startswith("def _run():"):
                    break
            for line in infile:
                line = re.sub(r"(os\.environ['[A-Za-z0-9]+'])",
                              r"unicode(\1, 'utf-8')", line)
                if re.match(r"^    exec\(compile\(.*\)\)", line):
                    outfile.write("    path = path.encode('ascii', 'backslashreplace')\n")
                outfile.write(line)
                if line.startswith("def _setup_ctypes():"):
                    break
            for line in infile:
                outfile.write(line)
    os.remove(filename)
    os.rename(tmpfile, filename)

def replace_loader(ext, site_package):
    """
    py2app が .so を読み出すのに使っている loader スクリプトを置き換えて、
    非asciiパスでも実行できるようにする。
    """
    loader = """
def __load():
    import imp, os, sys
    ext = %r
    for path in [ unicode(s, 'utf-8') for s in sys.path ]:
        if not path.endswith(u'lib-dynload'):
            continue
        ext_path = os.path.join(path, ext)
        if os.path.exists(ext_path):
            mod = imp.load_dynamic(__name__, ext_path.encode('utf-8'))
            break
    else:
        raise ImportError(repr(ext) + " not found")
__load()
del __load
""" % ext
    pyo_name = os.path.splitext(ext)[0] + ".pyo"
    codeobject = compile(loader, pyo_name, 'exec')
    now = datetime.now()
    # python compiled file (.pyc/pyo) is based on
    new_loader = (
        imp.get_magic() +                                 # MAGIC, 
        struct.pack("<L", time.mktime(now.timetuple())) + # TIMESTAMP and,
        marshal.dumps(codeobject))                        # marshaled code

    # zip の中身を差し替える
    tmpfd, tmpzip = tempfile.mkstemp(dir=os.path.dirname(site_package))
    os.close(tmpfd)
    with zipfile.ZipFile(site_package, 'r') as zin:
        with zipfile.ZipFile(tmpzip, 'w') as zout:
            zout.comment = zin.comment
            for item in zin.infolist():
                if item.filename != pyo_name:
                    zout.writestr(item, zin.read(item.filename))
    os.remove(site_package)
    os.rename(tmpzip, site_package)
    with zipfile.ZipFile(site_package, 'a', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(pyo_name, new_loader)
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.argv.append('py2app')
    py2app()
