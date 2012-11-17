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
    import zipfile
except ImportError, message:
    raise SystemExit,  "Unable to load module. %s" % message


class BuildExe(object):
    def __init__(self):
        #Name of starting .py
        self.script = "cardwirth.py"

        #Name of program
        self.project_name = "CardWirthPy"

        #Project url
        self.project_url = "http://sites.google.com/site/cardwirthpy/"

        #Version of program
        self.project_version = "0.12"

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
        self.extra_datas = ["Data/Font", "Data/Skin", "Data/Debugger",
            "License.txt", "msvcr90.dll", "msvcp90.dll", "gdiplus.dll",
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
        self.extra_dirs = ["Scenario", "Yado", "Data/Temp",
            "Data/EffectBooster"]

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
            shutil.rmtree(self.dist_dir)

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
        if self.icon_file == None:
            path = os.path.split(pygame.__file__)[0]
            self.icon_file = os.path.join(path, 'pygame.ico')

        #List all data files to add
        extra_datas = []
        for data in self.extra_datas:
            if os.path.isdir(data):
                extra_datas.extend(self.find_data_files(data, '*'))
            else:
                extra_datas.append(('.', [data]))

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
                                  'dist_dir': self.dist_dir,} },
            zipfile = self.zipfile_name,
            data_files = extra_datas,
            )

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

if __name__ == '__main__':
    if operator.lt(len(sys.argv), 2):
        sys.argv.append('py2exe')
    BuildExe().run() #Run generation
    raw_input("\nPress any key to continue") #Pause to let user see that things ends

