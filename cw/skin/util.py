#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import sys
import shutil
import subprocess

import cw

from typing import Callable, Dict, List, Optional, Tuple


def find_skin(name: str, author: str, skintype: str = "") -> List[str]:
    """
    名前と作者名でインストールされたスキンを検索し、
    フォルダ名の一覧を返す。
    """
    seq = []
    for dname in sorted(os.listdir("Data/Skin")):
        path = cw.util.join_paths("Data/Skin", dname)
        skininfo = get_skininfo(path)
        if skininfo:
            name2, author2, skintype2 = skininfo
            if name2 is not None and name == name2 and author2 is not None and author == author2 and\
                    (skintype == "" or (skintype2 is not None and skintype == skintype2)):
                seq.append(dname)

    return seq


def get_skininfo(path: str) -> Optional[Tuple[str, str, str]]:
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
                    skintype = prop.properties.get("Type", "")
                    return (name, author, skintype)
            except Exception:
                # エラーのあるスキンは無視
                cw.util.print_ex()
    else:
        lpath = path.lower()
        if lpath.endswith(".zip") or lpath.endswith(".lzh"):
            with cw.util.zip_file(path, "r") as z:
                names = [(name, info) for name, info in zip(z.namelist(), z.infolist())
                         if os.path.basename(name) == "Skin.xml"]

                for name, info in names:
                    data = z.read(name)
                    with io.BytesIO(data) as f:
                        prop = cw.header.GetProperty(stream=f)
                        f.close()
                    if prop.attrs.get(None, {}).get("dataVersion", "0") in cw.SUPPORTED_SKIN:
                        name = prop.properties.get("Name", "")
                        author = prop.properties.get("Author", "")
                        skintype = prop.properties.get("Type", "")
                        return (name, author, skintype)
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


def is_skin(path: str) -> bool:
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
                for zname, info in zip(z.namelist(), z.infolist()):
                    name = cw.util.decode_zipfilename(zname, info)
                    if os.path.basename(name) == "Skin.xml":
                        return True
            except Exception:
                cw.util.print_ex()
                print(path)
            finally:
                if z:
                    z.close()

        elif lpath.endswith(".cab"):
            return bool(cw.util.cab_hasfile(path, "Skin.xml"))

    return False


class SkinInstallError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


INSTALL_PROGRESS = 3
INSTALL_PROGRESS_ARCHIVE = 5


def _progress_with_msg(msg: str, progress: int = 1) -> None:
    pass


def install_skin(path: str, tempdir: str, progress: Callable[[str, int], None] = _progress_with_msg) -> str:
    """
    pathのスキンをインストールする。
    """
    tempdir2: Optional[str] = None
    try:
        if os.path.isfile(path):
            # アーカイブを展開する
            iscab = False

            def decompress(path: str, tempdir: str, startup: Callable[[int], None],
                           progress: Callable[[int], bool]) -> str:
                if iscab:
                    return cw.util.decompress_zip(path, tempdir, startup=startup, progress=progress)
                else:
                    return cw.util.decompress_cab(path, tempdir, startup=startup, progress=progress)

            progress("%s を展開中..." % os.path.basename(path), 1)
            lpath = path.lower()
            if lpath.endswith(".zip") or lpath.endswith(".lzh"):
                iscab = False
            elif lpath.endswith(".cab"):
                iscab = True
            else:
                raise SkinInstallError("%s はスキンではありません。" % os.path.basename(path))

            class ProgressObj(object):
                def __init__(self) -> None:
                    self.file_count = 0
                    self.decompress_count = 0
            obj = ProgressObj()

            def startup(num: int) -> None:
                obj.file_count = num
                s = "%s を展開中... (%s/%s)" % (os.path.basename(path), obj.decompress_count, obj.file_count)
                progress(s, 1)

            def progress_arc(num: int) -> bool:
                obj.decompress_count = num
                s = "%s を展開中... (%s/%s)" % (os.path.basename(path), obj.decompress_count, obj.file_count)
                progress(s, 1)
                return False

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

        progress("スキン情報を読み込んでいます...", 1)
        rootattrs: Dict[str, str] = {}
        try:
            etree = cw.data.xml2etree(skinpath, tag="Property")
        except Exception:
            cw.util.print_ex()
            raise SkinInstallError("%s のスキン情報の読み込みに失敗しました。" % os.path.basename(path))
        if not rootattrs.get("dataVersion", "0") in cw.SUPPORTED_SKIN:
            raise SkinInstallError("%s は未対応のデータバージョンです。CardWirthPy本体をアップグレードしてください。" % os.path.basename(path))

        sname = etree.gettext("Name", "(無名のスキン)")
        sauthor = etree.gettext("Author", "")
        if sauthor:
            sname += "(%s)" % sauthor

        basedata = etree.find("BaseSkin")
        if basedata is not None:
            assert isinstance(basedata, cw.data.CWPyElement)
            name = basedata.gettext("Name", "")
            author = basedata.gettext("Author", "")
            skintype = basedata.gettext("Type", "")
            base_l = find_skin(name, author, skintype)
            if base_l:
                base: Optional[str] = cw.util.join_paths("Data/Skin", base_l[0])
            else:
                baseinfo = " スキン名 = %s" % (name if name else "(無し)")
                baseinfo += "\n 作者名 = %s" % (author if author else "(無し)")
                if skintype:
                    baseinfo += "\n タイプ = %s" % skintype
                raise SkinInstallError("%s のベースとなるスキンが見つかりません。\n%s" % (os.path.basename(path), baseinfo))
        else:
            base = None

        dname = os.path.basename(os.path.dirname(skinpath))
        dpath = cw.util.join_paths("Data/Skin", dname)
        dpath = cw.util.dupcheck_plus(dpath, False)
        try:
            if base:
                progress("「%s」のベーススキンをコピーしています..." % sname, 1)
                shutil.copytree(base, dpath)
                progress("「%s」のデータをコピーしています..." % sname, 1)
                cw.util.copytree_overwrite(os.path.dirname(skinpath), dpath)
            else:
                progress("「%s」のデータをコピーしています..." % sname, 2)
                shutil.copytree(os.path.dirname(skinpath), dpath)
            return dpath
        except Exception:
            cw.util.print_ex()
            cw.util.remove(dpath)
            raise SkinInstallError("%s のコピーに失敗しました。" % os.path.basename(path))

    finally:
        if tempdir2:
            progress("一時ファイルを削除しています...", 1)
            cw.util.remove(tempdir2)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
