#! /usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import time
import re
from threading import Thread

import objc
from AppKit import *
from PyObjCTools import AppHelper

ALWAYS_LOG_OUTPUT = False
EXEC_FILE = "cardwirthpy"
XQUARTZ_IDENT = "org.macosforge.xquartz.X11"

APP_DIR = None
TOP_DIR = None
TERMINATE = None

def check_x11():
    if not os.path.exists("/opt/X11/lib/libX11.dylib"):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(
            u"XQuartz が見つかりません\n\n"
            u"このアプリケーションを実行する前に、https://www.xquartz.org "
            u"から XQuartz の最新版をダウンロードして、インストールしてください"
            )
        alert.runModal()
        sys.exit(1)

def set_env(varname, value):
    if isinstance(value, unicode):
        os.environ[varname] = value.encode('utf-8')
    else:
        os.environ[varname] = value
def get_env_unicode(varname):
    return unicode(os.environ[varname], 'utf-8')

def set_environment(argv0):
    global APP_DIR, TOP_DIR
    TOP_DIR = os.path.abspath(get_env_unicode("RESOURCEPATH"))
    APP_DIR = os.path.dirname(os.path.abspath(os.path.join(TOP_DIR, "..")))
    
    set_env("PYTHONPATH", ':'.join(sys.path))
    set_env("PYTHONHOME", TOP_DIR)
    
    set_env("ARGVZERO", os.path.abspath(os.path.join(TOP_DIR, EXEC_FILE)))
    set_env("_PYTHON_EXEC", os.path.abspath(
        os.path.join(TOP_DIR, "..", "MacOS", "python")))

    set_env("GTK_IM_MODULE_FILE", "/dev/null")
    set_env("GDK_PIXBUF_MODULE_FILE", "/dev/null")
    set_env("GTK_DATA_PREFIX", TOP_DIR)
    set_env("GTK_EXE_PREFIX", TOP_DIR)
    set_env("GTK_PATH", TOP_DIR)
    if not os.path.exists(os.path.join(unicode(os.environ["HOME"], 'utf-8'),
                                       ".gtkrc-2.0")):
        set_env("GTK2_RC_FILES", os.path.join(
            TOP_DIR, "etc", "gtk-2.0", "gtkrc"))

    set_env("PANGO_RC_FILE", os.path.join(TOP_DIR, "etc", "pango", "pangorc"))
    set_env("PANGO_SYSCONFDIR", os.path.join(TOP_DIR, "etc"))

    set_env("GIO_USE_VFS", "local")

    set_env("SDL_AUDIODRIVER", "disk")
    set_env("SDL_DISKAUDIOFILE", "/dev/null")

    set_env("XDG_DATA_DIRS", os.path.join(TOP_DIR, "share"))
    set_env("XDG_RUNTIME_DIR", os.environ["TMPDIR"])

    set_env("PATH", "/bin:/sbin:/usr/bin:/usr/sbin:/opt/X11/bin")
    set_env("LANG", "ja_JP.UTF-8")

class MainThread(Thread):
    def __init__(self, script, timer):
        Thread.__init__(self)
        self.script = script
        self.timer = timer

    def run(self):
        global TERMINATE
        try:
            error = False
            s = ""
            try:
                s = subprocess.call(
                    [ os.getenv("ARGVZERO"),
                      os.path.abspath(os.path.join(
                          get_env_unicode("RESOURCEPATH"), self.script)
                      ).encode('utf-8')
                    ] + sys.argv[1:],
                    stderr=subprocess.STDOUT
                )
                s = ""
            except:
                error = True
            if re.sub(r'\s', '', s) != '':
                error = True
            if ALWAYS_LOG_OUTPUT or error:
                with open(APP_DIR + ".log", "wb") as f:
                    f.write(s)
        finally:
            self.timer.stop_timer()
            if TERMINATE == False:
                TERMINATE = True
                AppHelper.stopEventLoop()

class ActivateCheck(object):
    def __init__(self):
        self.pid = os.getpid()
        self.timer = None
        self.reset_timer()

    def stop_timer(self):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None

    def reset_timer(self):
        if self.timer is not None:
            self.timer.invalidate()
        s = objc.selector(self.activecheck, signature='v@:')
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.2, self, s, None, True)

    def activecheck(self):
        workspace = NSWorkspace.sharedWorkspace()
        pid = workspace.activeApplication()['NSApplicationProcessIdentifier']
        if pid == self.pid:
            for app in workspace.runningApplications():
                if app.bundleIdentifier() == XQUARTZ_IDENT:
                    app.activateWithOptions_(
                        NSApplicationActivateAllWindows |
                        NSApplicationActivateIgnoringOtherApps)
                    break

def cocoa_main():
    global TERMINATE
    app = NSApplication.sharedApplication()
    if TERMINATE is None:
        TERMINATE = False
        AppHelper.runConsoleEventLoop(installInterrupt=True)

if __name__ == '__main__':
    check_x11()
    set_environment(sys.argv[0])
    main_thread = MainThread("cardwirth.py", ActivateCheck())
    main_thread.start()
    cocoa_main()
    main_thread.join()
