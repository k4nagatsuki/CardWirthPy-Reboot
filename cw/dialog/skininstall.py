#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import time
import threading
import wx

import cw
from cw.util import synclock

from typing import List, Tuple


def install_skin(paths: List[str], parent: wx.TopLevelWindow,
                 canswitch: bool = True) -> List[Tuple[str, str, str, str, bool]]:
    """
    pathsに含まれるスキンをインストールする。
    """
    seq = []
    skindir = cw.util.get_keypath(cw.util.get_symlinktarget("Data/Skin"))
    progmax = 3
    for path in paths:
        if cw.util.get_keypath(cw.util.get_symlinktarget(os.path.dirname(path))) == skindir:
            continue
        skininfo = cw.skin.util.get_skininfo(path)
        if skininfo:
            name, author, skintype = skininfo
            is_archive = os.path.isfile(path)
            seq.append((name, author, skintype, path, is_archive))
            if is_archive:
                progmax += cw.skin.util.INSTALL_PROGRESS_ARCHIVE
            else:
                progmax += cw.skin.util.INSTALL_PROGRESS

    if not seq:
        return []

    if 2 <= len(seq):
        s = "%s件のスキンをインストールします。よろしいですか？" % len(seq)
    else:
        name, author, _type, _path, _is_archive = seq[0]
        s = name if name else "(無名のスキン)"
        if author:
            s += "(%s)" % author
        s = "スキン「%s」をインストールします。よろしいですか？" % s

    choices = (
        ("はい(&Y)", wx.ID_YES, cw.ppis(105)),
        ("いいえ(&N)", wx.ID_NO, cw.ppis(105)),
    )
    checkboxes = [
        ("overwrite", "インストール済みの同一スキンを置換する", True),
        ("remove_installed", "インストール成功後にインストール元を削除する", True),
    ]
    if canswitch:
        checkboxes.append(("switch_skin", "インストールしたスキンに切り替える", False))
    dlg = cw.dialog.message.SysMessage(parent, "スキンのインストール", s, choices=choices, checkboxes=checkboxes)
    cw.cwpy.frame.move_dlg(dlg)
    cw.cwpy.add_showingdlg()
    if wx.ID_YES != dlg.ShowModal():
        cw.cwpy.frame.kill_dlg(dlg)
        return []
    overwrite = dlg.get_check("overwrite")
    remove_installed = dlg.get_check("remove_installed")
    if canswitch:
        switch_skin = dlg.get_check("switch_skin")
    else:
        switch_skin = False
    cw.cwpy.frame.kill_dlg(dlg)

    def change_cursor(cursor: str) -> None:
        cw.cwpy.exec_func(cw.cwpy.change_cursor, cursor, force=True)
    oldcursor = cw.cwpy.cursor
    change_cursor("wait")

    if overwrite:
        progmax += 2
        progmax += len(seq)
    if remove_installed:
        progmax += 1

    class ProgressObj(object):
        def __init__(self) -> None:
            self.msg = ""
            self.value = 0
            self.maximum = progmax
            self.errors = []
            self.installed_skindirnames = []

    obj = ProgressObj()
    lock = threading.Lock()

    @synclock(lock)
    def progress(msg, progress: int = 1) -> None:
        obj.value += progress
        obj.msg = msg

    def run() -> None:
        tempdir = "Data/Temp/SkinInstall"
        if not os.path.isdir(tempdir):
            os.makedirs(tempdir)
        errors = []
        rename_table = {}
        installed = None
        all_removes_repl = []
        all_removes_base = []
        removes_table = {}
        if overwrite:
            progress("インストール済みスキンの情報を収集しています...")
            for name, author, _type, _path, _is_archive in seq:
                key = (name, author)
                if key not in removes_table:
                    removes_table[key] = list(cw.skin.util.find_skin(name, author))
        try:
            for name, author, skintype, path, is_archive in seq:
                if overwrite:
                    removes = removes_table[(name, author)]
                else:
                    removes = ()
                oldvalue = obj.value
                try:
                    installedpath = cw.skin.util.install_skin(path, tempdir, progress)
                    # FIXME: たまに音声が解放されずエラーになるため保留
                    # if removes:
                    #     if cw.cwpy.setting.skindirname == removes[0]:
                    #         cw.cwpy.stop_allsounds(skinfileonly=True)
                    #     installedpath2 = cw.util.join_paths("Data/Skin", removes[0])
                    #     rmpath = cw.util.dupcheck_plus(installedpath2, False)
                    #     shutil.move(installedpath2, rmpath)
                    #     shutil.move(installedpath, installedpath2)
                    #     installedpath = installedpath2
                    #     removes[0] = os.path.basename(rmpath)

                    obj.installed_skindirnames.append((os.path.basename(installedpath), name, author, skintype))
                    if not installed:
                        installed = os.path.basename(installedpath)

                    s = name if name else "(無名のスキン)"
                    if author:
                        s += "(%s)" % author
                    if overwrite:
                        progress("「%s」のFaceフォルダをコピーしています..." % s)
                    elif removes:
                        progress(obj.msg)

                    for rmname in removes:
                        rmpath = cw.util.join_paths("Data/Skin", rmname)
                        # CardWirthの伝統により、Faceディレクトリには
                        # ユーザ固有のデータが入っている可能性があるので
                        # 置換対象からコピーしておく
                        srcface = cw.util.join_paths(rmpath, "Face")
                        dstface = cw.util.join_paths(installedpath, "Face")
                        cw.util.copytree_overwrite(srcface, dstface,
                                                   files_overwrite=cw.util.OVERWRITE_WITH_LATEST_FILES)

                        if os.path.basename(installedpath) != rename_table.get(rmname, ""):
                            rename_table[rmname] = os.path.basename(installedpath)
                        all_removes_repl.append(rmpath)

                    if remove_installed:
                        all_removes_base.append(path)

                except cw.skin.util.SkinInstallError as ex:
                    obj.errors.append(ex.message)
                    if is_archive:
                        obj.value = oldvalue + cw.skin.util.INSTALL_PROGRESS_ARCHIVE
                    else:
                        obj.value = oldvalue + cw.skin.util.INSTALL_PROGRESS
                    if overwrite:
                        obj.value += 1

            progress("スキンの参照情報を更新してます...")
            for yado in os.listdir("Yado"):
                env = cw.util.join_paths("Yado", yado, "Environment.xml")
                if os.path.isfile(env):
                    etree = cw.data.xml2etree(env)
                    envskin = etree.gettext("Property/Skin", "")
                    if envskin:
                        newskin = rename_table.get(envskin, "")
                        if newskin:
                            etree.edit("Property/Skin", newskin)
                            etree.write_file()
            cw.fsync.sync()

            def func(newskin: str, restartop: bool) -> None:
                progress("スキンの切り替えを行っています...")
                if newskin:
                    if cw.cwpy.ydata:
                        cw.cwpy.ydata.changed()
                    cw.cwpy.stop_allsounds(skinfileonly=True)
                    cw.cwpy.update_skin(newskin, restartop=restartop, switch_skin=True)
                if overwrite:
                    progress("置換されたスキンを削除しています...")
                    for path in all_removes_repl:
                        try:
                            cw.util.remove(path, trashbox=True)
                        except Exception:
                            cw.util.print_ex(file=sys.stderr)
                        # FIXME: なぜか削除に失敗する事があるのでSkin.xmlを移動して無効にする
                        skinfpath = cw.util.join_paths(path, "Skin.xml")
                        if os.path.isfile(skinfpath):
                            shutil.move(skinfpath, cw.util.join_paths(path, "Skin.xml_removed"))
                if remove_installed:
                    progress("インストール済みのファイルを削除しています...")
                    for path in all_removes_base:
                        try:
                            cw.util.remove(path, trashbox=True)
                        except Exception:
                            cw.util.print_ex(file=sys.stderr)
                change_cursor(oldcursor)

                def func() -> None:
                    progress("スキンのインストールが完了しました。")
                    progdlg.Destroy()
                cw.cwpy.frame.exec_func(func)

            if switch_skin and installed:
                newskin = installed
                cw.cwpy.exec_func(func, newskin, restartop=cw.cwpy.setting.skindirname != newskin)
            else:
                newskin = rename_table.get(cw.cwpy.setting.skindirname, "")
                cw.cwpy.exec_func(func, newskin, restartop=False)

        except Exception:
            progdlg.Destroy()
            raise

        finally:
            cw.util.remove(tempdir)

    thread = threading.Thread(target=run)
    thread.start()

    # プログレスダイアログ表示
    progdlg = cw.dialog.progress.SysProgressDialog(parent, "スキンのインストール",
                                                   "", maximum=obj.maximum)

    def progress_run() -> None:
        while thread.is_alive():
            wx.CallAfter(progdlg.UpdateProgress, obj.value, obj.msg)
            time.sleep(0.001)
    thread2 = threading.Thread(target=progress_run)
    thread2.start()
    cw.cwpy.frame.move_dlg(progdlg)
    progdlg.ShowModal()

    if obj.errors:
        s = "スキンのインストール中にエラーが発生しました。\n\n" + "\n\n".join(obj.errors)
        dlg = cw.dialog.etc.ErrorLogDialog(parent, s)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    return obj.installed_skindirnames


def main() -> None:
    pass


if __name__ == "__main__":
    main()
