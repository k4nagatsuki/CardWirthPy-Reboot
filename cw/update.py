#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

import cw


def update_files(dpath, rmname, permit=[]):
    """
    "<dpath>/UpdateInfo.xml"の情報に基づいてファイルの移動や削除を行う。
    基本的にdpathより上位のディレクトリを操作する事はないが、
    permitに含まれるパスから始まるディレクトリだけは操作を許可する。
    """
    fpath = cw.util.join_paths(dpath, u"UpdateInfo.xml")
    if not os.path.isfile(fpath):
        return

    if not cw.util.create_mutex(dpath):
        # 他のプロセスが更新中
        return

    try:
        data = cw.data.xml2etree(fpath)
        tempdpath = u"Data/Temp/%s_RemovedFiles" % rmname
        for e in data.getroot():
            if e.tag <> "UpdateFile":
                continue

            def check_targetpath(fpath):
                fpath = os.path.normpath(fpath)
                if os.path.isabs(fpath):
                    return False
                fpath = cw.util.join_paths(fpath)
                if fpath.startswith("../"):
                    if not any(map(lambda p: fpath.startswith(p), permit)):
                        return False
                return True

            if not e.text:
                continue
            fpath = cw.util.join_paths(dpath, e.text)
            if not os.path.isfile(fpath):
                continue
            if not check_targetpath(e.text):
                continue

            moveto = e.getattr(".", "moveto", "")
            if not check_targetpath(moveto):
                continue
            remove = e.getbool(".", "remove", False)
            if moveto:
                moveto = cw.util.join_paths(dpath, moveto)
                if os.path.isfile(moveto):
                    # 移動先にすでにファイルが存在する場合、
                    # 移動する必要はないので削除だけ行う
                    remove = True
                else:
                    # ファイルの移動
                    movetodir = os.path.dirname(moveto)
                    if not os.path.isdir(movetodir):
                        os.makedirs(movetodir)
                    shutil.move(fpath, moveto)
                    print u"Auto Update: Move from %s to %s." % (fpath, moveto)
                    continue

            if remove:
                # ファイルの削除
                # 一時ディレクトリに移してからまとめてゴミ箱へ送る
                md5 = e.getattr(".", "md5", "")
                if md5 <> cw.util.get_md5(fpath):
                    continue
                fpath2 = cw.util.join_paths(e.text)
                while fpath2.startswith("../"):
                    fpath2 = fpath2[len("../"):]
                temp = cw.util.join_paths(tempdpath, fpath2)
                tempdpath2 = os.path.dirname(temp)
                if not os.path.isdir(tempdpath2):
                    os.makedirs(tempdpath2)
                shutil.move(fpath, temp)
                print u"Auto Update: Move from %s to %s." % (fpath, temp)

        if os.path.isdir(tempdpath):
            # 削除対象をゴミ箱へ送る
            cw.util.remove(tempdpath, trashbox=True)
            print u"Auto Update: Remove %s." % (tempdpath)

    finally:
        cw.util.release_mutex()


def main():
    pass

if __name__ == "__main__":
    main()
