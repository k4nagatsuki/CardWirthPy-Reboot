#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import threading
import wx

import cw


def install_skin(paths, parent, canswitch=True):
    """
    pathsに含まれるスキンをインストールする。
    """
    seq = []
    skindir = os.path.normcase(os.path.normpath(os.path.abspath("Data/Skin")))
    for path in paths:
        if os.path.normcase(os.path.normpath(os.path.abspath(os.path.dirname(path)))) == skindir:
            continue
        skininfo = cw.skin.util.get_skininfo(path)
        if skininfo:
            name, author, type = skininfo
            seq.append((name, author, type, path))

    if not seq:
        return []

    if 2 <= len(seq):
        s = "%s件のスキンをインストールします。よろしいですか？" % len(seq)
    else:
        name, author, _type, _path = seq[0]
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
    if wx.ID_YES != dlg.ShowModal():
        return []
    overwrite = dlg.get_check("overwrite")
    remove_installed = dlg.get_check("remove_installed")
    if canswitch:
        switch_skin = dlg.get_check("switch_skin")
    else:
        switch_skin = False
    dlg.Destroy()

    progdlg = cw.dialog.message.SysMessage(parent, "スキンのインストール", "スキンをインストールしています...")
    cw.cwpy.frame.move_dlg(progdlg)
    progdlg.Show()

    def change_cursor(cursor):
        cw.cwpy.exec_func(cw.cwpy.change_cursor, cursor, force=True)
    oldcursor = cw.cwpy.cursor
    change_cursor("wait")

    tempdir = "Data/Temp/SkinInstall"
    if not os.path.isdir(tempdir):
        os.makedirs(tempdir)
    errors = []
    rename_table = {}
    installed = None
    all_removes = []
    installed_skindirnames = []
    removes_table = {}
    if overwrite:
        for name, author, _type, _path in seq:
            key = (name, author)
            if not key in removes_table:
                removes_table[key] = list(cw.skin.util.find_skin(name, author))
    try:
        for name, author, type, path in seq:
            removes = removes_table[(name, author)]
            try:
                installedpath = cw.skin.util.install_skin(path, tempdir, progdlg)
                # FIXME: たまに音声が解放されずエラーになるため保留
                #if removes:
                #    if cw.cwpy.setting.skindirname == removes[0]:
                #        cw.cwpy.stop_allsounds()
                #    installedpath2 = cw.util.join_paths("Data/Skin", removes[0])
                #    rmpath = cw.util.dupcheck_plus(installedpath2, False)
                #    shutil.move(installedpath2, rmpath)
                #    shutil.move(installedpath, installedpath2)
                #    installedpath = installedpath2
                #    removes[0] = os.path.basename(rmpath)

                installed_skindirnames.append((os.path.basename(installedpath), name, author, type))
                if not installed:
                    installed = os.path.basename(installedpath)

                for rmname in removes:
                    rmpath = cw.util.join_paths("Data/Skin", rmname)
                    # CardWirthの伝統により、Faceディレクトリには
                    # ユーザ固有のデータが入っている可能性があるので
                    # 置換対象からコピーしておく
                    srcface = cw.util.join_paths(rmpath, "Face")
                    dstface = cw.util.join_paths(installedpath, "Face")
                    cw.util.copytree_overwrite(srcface, dstface, files_overwrite=False)

                    if os.path.basename(installedpath) != rename_table.get(rmname, ""):
                        rename_table[rmname] = os.path.basename(installedpath)
                    all_removes.append((rmpath, True))

                if remove_installed:
                    all_removes.append((path, False))

            except cw.skin.util.SkinInstallError as ex:
                errors.append(ex.message)

        for yado in os.listdir("Yado"):
            env = cw.util.join_paths("Yado", yado, "Environment.xml")
            if os.path.isfile(env):
                etree = cw.data.xml2etree(env)
                envskin = etree.gettext("Property/Skin", "")
                if envskin:
                    newskin = rename_table.get(envskin, "")
                    if newskin:
                        etree.edit("Property/Skin", newskin)
                        etree.write()

        def func(newskin, restartop):
            cw.cwpy.stop_allsounds()
            if newskin:
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                cw.cwpy.update_skin(newskin, restartop=restartop, switch_skin=True)
            for path, oldskin in all_removes:
                try:
                    cw.util.remove(path, trashbox=True)
                except:
                    cw.util.print_ex(file=sys.stderr)
                if oldskin:
                    # FIXME: なぜか削除に失敗する事があるのでSkin.xmlを移動して無効にする
                    skinfpath = cw.util.join_paths(path, "Skin.xml")
                    if os.path.isfile(skinfpath):
                        shutil.move(skinfpath, cw.util.join_paths(path, "Skin.xml_removed"))
            change_cursor(oldcursor)
            cw.cwpy.frame.exec_func(progdlg.Destroy)

        if switch_skin and installed:
            newskin = installed
            cw.cwpy.exec_func(func, newskin, restartop=cw.cwpy.setting.skindirname != newskin)
        else:
            newskin = rename_table.get(cw.cwpy.setting.skindirname, "")
            cw.cwpy.exec_func(func, newskin, restartop=False)

    except:
        progdlg.Destroy()
        raise

    finally:
        cw.util.remove(tempdir)

    if errors:
        s = "スキンのインストール中にエラーが発生しました。\n\n" + "\n\n".join(errors)
        dlg = cw.dialog.etc.ErrorLogDialog(parent, s)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    return installed_skindirnames


def main():
    pass


if __name__ == "__main__":
    main()
