# -*- mode: python -*-
# -*- coding: utf-8 -*-
# PyInstaller用の設定ファイル。以下のようにして実行します。
# python pyinstaller.py cardwirth.spec

import os
import shutil

distdir = 'CardWirthPy'
includes = [
    'Data/Debugger',
    'Data/Font',
    'Data/SkinBase',
    'ChangeLog.txt',
    'License.txt',
    'ReadMe.txt'
]

if os.path.exists(distdir):
    shutil.rmtree(distdir)
for file in includes:
    dist = os.path.join(distdir, file)
    if os.path.isfile(file):
        shutil.copyfile(file, dist)
    else:
        dir = os.path.dirname(dist)
        if not os.path.exists(dir):
            os.makedirs(dir)
        shutil.copytree(file, dist)

a = Analysis(['cardwirth.py'],
             pathex=['./'],
             hiddenimports=[],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts + [('O','','OPTION')],
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join(distdir, 'CardWirthPy.exe'),
          icon='CardWirthPy.ico',
          manifest='CardWirthPy.manifest',
          debug=False,
          upx=False,
          console=False )
