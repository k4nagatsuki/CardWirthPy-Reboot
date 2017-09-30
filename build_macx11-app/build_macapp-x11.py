#! /usr/bin/python2.7
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

from setuptools import setup
from glob import glob

import os
import sys
import shutil
import subprocess
import compileall

APP_VERSION = "2.1"
APP_NAME = "CardWirthPy"
APP_IDENT = "org.bitbucket.k4nagatsuki.cardwirth-py"
APP_COPYRIGHT = u"Copyright © 2008-2010,2014-2017 logの中の人, k4nagatsuki and contributers, All Rights Reserved"

build_dir = u"build"
dist_dir = u"."
dist_contents = os.path.join(
    dist_dir, u"%s.app" % APP_NAME, "Contents")
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
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.argv.append('py2app')
    py2app()
