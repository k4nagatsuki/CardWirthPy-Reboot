#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This will create a dist directory containing the executable file, all the data
# directories. All Libraries will be bundled in executable file.
#
# Run the build process by entering 'pygame2exe.py' or
# 'python pygame2exe.py' in a console prompt.
#
# To build exe, python, pygame, and py2exe have to be installed. After
# building exe none of this libraries are needed.

try:
    from distutils.core import setup
    import py2exe, pygame
    from modulefinder import Module
    import glob, fnmatch
    import sys, os, shutil
    import operator
    import time
    import datetime
    import zipfile
    import py2exe.mf
    import win32com
except ImportError, message:
    raise SystemExit,  "Unable to load module. %s" % message

for p in win32com.__path__[1:]:
    py2exe.mf.AddPackagePath("win32com", p)
for extra in ["win32com.shell"]:
    __import__(extra)
    m = sys.modules[extra]
    for p in m.__path__[1:]:
        py2exe.mf.AddPackagePath(extra, p)


class BuildExe(object):
    def __init__(self):
        #Name of starting .py
        self.script = "cardwirth.py"

        #Name of program
        self.project_name = "CardWirthPy"

        #Project url
        self.project_url = "https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot/"

        #Version of program
        self.project_version = "2.3"

        #License of the program
        self.license = "LGPL"

        #Auhor of program
        self.author_name = ""
        self.author_email = ""
        self.copyright = ""

        #Description
        self.project_description = "CardWirthPy"

        #Icon file (None will use pygame default icon)
        self.icon_file = "CardWirthPy.ico"

        #Manifest file.
        self.manifest_file = "CardWirthPy.manifest"

        #Source file name
        self.srcfile_name = "src.zip"

        #Extra files/dirs copied to game
        self.extra_datas = ["Data/Font", "Data/SoundFont", "Data/SkinBase",
            "Data/Debugger", "Data/Materials",
            "Data/Compatibility.xml", "Data/SystemCoupons.xml", "Data/SearchEngines.xml",
            "License.txt", "msvcr90.dll", "msvcp90.dll", "gdiplus.dll",
            "bass.dll", "bass_fx.dll", "bassmidi.dll", "x64",
            "ChangeLog.txt", "Microsoft.VC90.CRT.manifest",
            "ReadMe.txt", self.srcfile_name]

        #Extra/excludes python modules
        self.extra_modules = []
        self.exclude_modules = []

        #DLL Excludes
        self.exclude_dll = ["w9xpopen.exe"]

        #Zip file name (None will bundle files in exe instead of zip file)
        self.zipfile_name = None

        #Dist directory
        self.dist_dir ='CardWirthPy'

        #Extra new dirs
        self.extra_dirs = ["Scenario", "Yado", "Data/Temp", "Data/Skin",
            "Data/Face/Common", "Data/Face/Common-ADT", "Data/Face/Common-CHD", "Data/Face/Common-OLD", "Data/Face/Common-YNG",
            "Data/Face/Female", "Data/Face/Female-ADT", "Data/Face/Female-CHD", "Data/Face/Female-OLD", "Data/Face/Female-YNG",
            "Data/Face/Male", "Data/Face/Male-ADT", "Data/Face/Male-CHD", "Data/Face/Male-OLD", "Data/Face/Male-YNG"]

        #Additional modules
        self.includes = ["win32com.shell.shell", "win32com.client"]

        self.dllincludes_ex = [
            "jpeg.dll",
            "libfreetype-6.dll",
            "libogg-0.dll",
            "libpng12-0.dll",
            "libtiff.dll",
            "libvorbis-0.dll",
            "libvorbisfile-3.dll",
            "pythoncom27.dll",
            "pywintypes27.dll",
            "sdl.dll",
            "sdl_image.dll",
            "sdl_mixer.dll",
            "sdl_ttf.dll",
            "smpeg.dll",
            "sqlite3.dll",
            "wxbase28uh_net_vc.dll",
            "wxbase28uh_vc.dll",
            "wxmsw28uh_adv_vc.dll",
            "wxmsw28uh_aui_vc.dll",
            "wxmsw28uh_core_vc.dll",
            "wxmsw28uh_html_vc.dll",
            "zlib1.dll",
        ]
        self.dllexcludes_ex = [
            "oleaut32.dll",
            "user32.dll",
            "comctl32.dll",
            "shell32.dll",
            "kernel32.dll",
            "winmm.dll",
            "wsock32.dll",
            "comdlg32.dll",
            "advapi32.dll",
            "ws2_32.dll",
            "winspool.drv",
            "gdi32.dll",
            "ole32.dll",
            "rpcrt4.dll",
            "gdiplus.dll",
            "msvcp90.dll",
        ]

    ## Code from DistUtils tutorial at http://wiki.python.org/moin/Distutils/Tutorial
    ## Originally borrowed from wxPython's setup and config files
    def opj(self, *args):
        path = os.path.join(*args)
        return os.path.normpath(path)

    def find_data_files(self, srcdir, *wildcards, **kw):
        # get a list of all files under the srcdir matching wildcards,
        # returned in a format to be used for install_data
        def walk_helper(arg, dirname, files):
            if '.svn' in dirname:
                return
            names = []
            lst, wildcards = arg
            for wc in wildcards:
                wc_name = self.opj(dirname, wc)
                for f in files:
                    filename = self.opj(dirname, f)

                    if fnmatch.fnmatch(filename, wc_name) and not os.path.isdir(filename):
                        names.append(filename)
            if names:
                lst.append( (dirname, names ) )

        file_list = []
        recursive = kw.get('recursive', True)
        if recursive:
            os.path.walk(srcdir, walk_helper, (file_list, wildcards))
        else:
            walk_helper((file_list, wildcards),
                        srcdir,
                        [os.path.basename(f) for f in glob.glob(self.opj(srcdir, '*'))])
        return file_list

    def run(self):
        if os.path.isdir(self.dist_dir): #Erase previous destination dir
            try:
                shutil.rmtree(self.dist_dir)
            except Exception, ex:
                if sys.platform == "win32":
                    os.system("rmdir /S /Q %s" % (self.dist_dir))
                else:
                    raise ex

        #Create source archive file
        compress_src(self.srcfile_name)

        #Load manifest file
        if self.manifest_file:
            f = open(self.manifest_file, "rb")
            manifest = f.read()
            f.close()
        else:
            manifest = ""

        #Use the default pygame icon, if none given
        if self.icon_file is None:
            path = os.path.split(pygame.__file__)[0]
            self.icon_file = os.path.join(path, 'pygame.ico')

        #List all data files to add
        extra_datas = []
        for data in self.extra_datas:
            if os.path.isdir(data):
                extra_datas.extend(self.find_data_files(data, '*'))
            else:
                dir = os.path.dirname(data)
                extra_datas.append((dir, [data]))

        issystemdll = py2exe.build_exe.isSystemDLL
        def myissystemdll(path):
            fpath = os.path.basename(path).lower()
            if fpath in self.dllincludes_ex:
                return False
            if fpath in self.dllexcludes_ex:
                return True
            return issystemdll(path)
        py2exe.build_exe.isSystemDLL = myissystemdll

        setup(
            version = self.project_version,
            description = self.project_description,
            name = self.project_name,
            url = self.project_url,
            author = self.author_name,
            author_email = self.author_email,
            license = self.license,

            # targets to build
            windows = [{
                'author': self.author_name,
                'version': self.project_version,
                'name': self.project_name,
                'dest_base': self.project_name,
                'script': self.script,
                'icon_resources': [(1, self.icon_file)],
                'copyright': self.copyright,
                'other_resources': [(24, 1, manifest)],
            }],
            options = {'py2exe': {'optimize': 2,
                                  'bundle_files': 1,
                                  'compressed': True,
                                  'excludes': self.exclude_modules,
                                  'packages': self.extra_modules,
                                  'dll_excludes': self.exclude_dll,
                                  'dist_dir': self.dist_dir,
                                  'includes': self.includes} },
            zipfile = self.zipfile_name,
            data_files = extra_datas,
            )

        py2exe.build_exe.isSystemDLL = issystemdll

        #Create new directory
        print "\n*** creating new directory ***"

        for dname in self.extra_dirs:
            path = os.path.join(self.dist_dir, dname)
            print "creating %s" % (os.path.abspath(path))
            os.makedirs(path)

        if os.path.isdir('build'): #Clean up build dir
            shutil.rmtree('build')

def compress_src(zpath):
    fnames = ["cardwirth.py", "build_exe.py", "CardWirthPy.ico",
              "CardWirthPy.manifest"]
    encoding = sys.getfilesystemencoding()
    z = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED)

    for fname in fnames:
        fpath = fname.encode(encoding)
        z.write(fpath, fpath)

    for dpath, dnames, fnames in os.walk("cw"):
        for dname in dnames:
            fpath = os.path.join(dpath, dname).encode(encoding)
            mtime = time.localtime(os.path.getmtime(fpath))[:6]
            zinfo = zipfile.ZipInfo(fpath + "/", mtime)
            z.writestr(zinfo, "")

        for fname in fnames:
            ext = os.path.splitext(fname)[1]

            if ext in (".py", ".c", ".pyd"):
                fpath = os.path.join(dpath, fname).encode(encoding)
                z.write(fpath, fpath)

    z.close()
    return zpath

def create_versioninfo():
    # ビルド情報を生成する
    print "Create versioninfo.py."
    date = datetime.datetime.today()
    s = "build_datetime = \"%s\"\n" % (date.strftime("%Y-%m-%d %H:%M:%S"))
    with open("versioninfo.py", "w") as f:
        f.write(s)

def remove_versioninfo():
    print "Remove versioninfo.py."
    os.remove("versioninfo.py")

if __name__ == '__main__':
    if operator.lt(len(sys.argv), 2):
        sys.argv.append('py2exe')

    nokey = False # 終了時にキー入力を求めるか
    if "-nokey" in sys.argv:
        nokey = True
        sys.argv.remove("-nokey")

    create_versioninfo()

    try:
        BuildExe().run() #Run generation
    finally:
        remove_versioninfo()

    if not nokey:
        raw_input("\nPress any key to continue") #Pause to let user see that things ends
    else:
        print "\nCompleted build."
