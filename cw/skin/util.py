#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import sys
import shutil
import subprocess
import threading
import time
import wx

import cw


def find_skin(name, author, type=""):
    """
    名前と作者名でインストールされたスキンを検索し、
    フォルダ名の一覧を返す。
    """
    seq = []
    for dname in sorted(os.listdir("Data/Skin")):
        path = cw.util.join_paths("Data/Skin", dname)
        skininfo = get_skininfo(path)
        if skininfo:
            name2, author2, type2 = skininfo
            if not name2 is None and name == name2 and not author2 is None and author == author2 and\
                    (type == "" or (not type2 is None and type == type2)):
                seq.append(dname)

    return seq


def get_skininfo(path):
    """
    スキンの(名前, 作者, タイプ)を返す。
    スキンでない場合はNoneを返す。
    """
    if os.path.isdir(path):
        skinpath = cw.util.join_paths(path, "Skin.xml")
        if os.path.isfile(skinpath):
            try:
                prop = cw.header.GetProperty(skinpath)
                if prop.attrs.get(None, {}).get("dataVersion", "0") in cw.SUPPORTED_SKIN:
                    name = prop.properties.get("Name", "")
                    author = prop.properties.get("Author", "")
                    type = prop.properties.get("Type", "")
                    return (name, author, type)
            except:
                # エラーのあるスキンは無視
                cw.util.print_ex()
    else:
        lpath = path.lower()
        if lpath.endswith(".zip") or lpath.endswith(".lzh"):
            with cw.util.zip_file(path, "r") as z:
                names = [(name, info) for name, info in zip(z.namelist(), z.infolist()) if os.path.basename(name) == "Skin.xml"]

                for name, info in names:
                    data = z.read(name)
                    with io.BytesIO(data) as f:
                        prop = cw.header.GetProperty(stream=f)
                        f.close()
                    if prop.attrs.get(None, {}).get("dataVersion", "0") in cw.SUPPORTED_SKIN:
                        name = prop.properties.get("Name", "")
                        author = prop.properties.get("Author", "")
                        type = prop.properties.get("Type", "")
                        return (name, author, type)
                z.close()
        elif lpath.endswith(".cab"):
            dpath = cw.util.join_paths(cw.tempdir, "Cab")
            if not os.path.isdir(dpath):
                os.makedirs(dpath)
            s = "expand \"%s\" -f:%s \"%s\"" % (path, "Skin.xml", dpath)
            try:
                if subprocess.call(s, shell=True, close_fds=True) == 0:
                    for dpath2, _dnames, fnames in os.walk(dpath):
                        for fname in fnames:
                            fname = cw.util.decode_zipname(fname)
                            if fname == "Skin.xml":
                                dpath2 = cw.util.decode_zipname(dpath2)
                                return get_skininfo(dpath2)
            finally:
                for fpath in os.listdir(dpath):
                    fpath = cw.util.decode_zipname(fpath)
                    fpath = cw.util.join_paths(dpath, fpath)
                    cw.util.remove(fpath)
    return None


def is_skin(path):
    """
    pathがスキンのフォルダないしスキンを圧縮したものか。
    """
    ltarg = cw.util.get_linktarget(path)
    if os.path.isdir(ltarg):
        spath = cw.util.join_paths(ltarg, "Skin.xml")
        return os.path.isfile(spath)
    else:
        lpath = ltarg.lower()
        if lpath.endswith(".zip") or lpath.endswith(".lzh"):
            try:
                z = cw.util.zip_file(path, "r")
                for name in z.namelist():
                    if os.path.basename(cw.util.decode_zipname(name)) == "Skin.xml":
                        return True
            except:
                cw.util.print_ex()
                print(path)
            finally:
                if z:
                    z.close()

        elif lpath.endswith(".cab"):
            return cw.util.cab_hasfile(path, "Skin.xml")

    return False


class SkinInstallError(Exception):
    def __init__(self, message):
        self.message = message


INSTALL_PROGRESS = 3
INSTALL_PROGRESS_ARCHIVE = 5


def install_skin(path, tempdir, progress=lambda msg, progress: None):
    """
    pathのスキンをインストールする。
    """
    tempdir2 = None
    try:
        if os.path.isfile(path):
            # アーカイブを展開する
            progress("%s を展開中..." % os.path.basename(path))
            lpath = path.lower()
            if lpath.endswith(".zip") or lpath.endswith(".lzh"):
                decompress = cw.util.decompress_zip
            elif lpath.endswith(".cab"):
                decompress = cw.util.decompress_cab
            else:
                raise SkinInstallError("%s はスキンではありません。" % os.path.basename(path))

            class ProgressObj(object):
                def __init__(self):
                    self.file_count = 0
                    self.decompress_count = 0
            obj = ProgressObj()

            def startup(num):
                obj.file_count = num
                s = "%s を展開中... (%s/%s)" % (os.path.basename(path), obj.decompress_count, obj.file_count)
                progress(s, progress=0)

            def progress_arc(num):
                obj.decompress_count = num
                s = "%s を展開中... (%s/%s)" % (os.path.basename(path), obj.decompress_count, obj.file_count)
                progress(s, progress=0)

            try:
                tempdir2 = decompress(path, tempdir, startup=startup, progress=progress_arc)
            except Exception as e:
                cw.util.print_ex(file=sys.stderr)
                raise SkinInstallError("%s の展開に失敗しました。" % os.path.basename(path))

            skinpath = cw.util.join_paths(tempdir2, "Skin.xml")
            if not os.path.isfile(skinpath):
                # サブディレクトリを探索
                for dpath, _dnames, fnames in os.walk(tempdir2):
                    if "Skin.xml" in fnames:
                        skinpath = cw.util.join_paths(dpath, "Skin.xml")
                        break
                else:
                    raise SkinInstallError("%s はスキンのアーカイブではありません。" % os.path.basename(path))

        else:
            skinpath = cw.util.join_paths(path, "Skin.xml")

        progress("スキン情報を読み込んでいます...")
        rootattrs = {}
        try:
            etree = cw.data.xml2etree(skinpath, tag="Property")
        except:
            cw.util.print_ex()
            raise SkinInstallError("%s のスキン情報の読み込みに失敗しました。" % os.path.basename(path))
        if not rootattrs.get("dataVersion", "0") in cw.SUPPORTED_SKIN:
            raise SkinInstallError("%s は未対応のデータバージョンです。CardWirthPy本体をアップグレードしてください。" % os.path.basename(path))

        sname = etree.gettext("Name", "(無名のスキン)")
        sauthor = etree.gettext("Author", "")
        if sauthor:
            sname += "(%s)" % sauthor

        basedata = etree.find("BaseSkin")
        if not basedata is None:
            name = basedata.gettext("Name", "")
            author = basedata.gettext("Author", "")
            type = basedata.gettext("Type", "")
            base = find_skin(name, author, type)
            if base:
                base =cw.util.join_paths("Data/Skin", base[0])
            else:
                baseinfo = " スキン名 = %s" % (name if name else "(無し)")
                baseinfo += "\n 作者名 = %s" % (author if author else "(無し)")
                if type:
                    baseinfo += "\n タイプ = %s" % type
                raise SkinInstallError("%s のベースとなるスキンが見つかりません。\n%s" % (os.path.basename(path), baseinfo))
        else:
            base = None

        dname = os.path.basename(os.path.dirname(skinpath))
        dpath = cw.util.join_paths("Data/Skin", dname)
        dpath = cw.util.dupcheck_plus(dpath, False)
        try:
            if base:
                progress("「%s」のベーススキンをコピーしています..." % sname)
                shutil.copytree(base, dpath)
                progress("「%s」のデータをコピーしています..." % sname)
                cw.util.copytree_overwrite(os.path.dirname(skinpath), dpath)
            else:
                progress("「%s」のデータをコピーしています..." % sname, progress=2)
                shutil.copytree(os.path.dirname(skinpath), dpath)
            return dpath
        except:
            cw.util.print_ex()
            cw.util.remove(dpath)
            raise SkinInstallError("%s のコピーに失敗しました。" % os.path.basename(path))

    finally:
        if tempdir2:
            progress("一時ファイルを削除しています...")
            cw.util.remove(tempdir2)
