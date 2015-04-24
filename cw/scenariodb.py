#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import sys
import time
import StringIO
import sqlite3
import threading
import subprocess

import cw
from cw.util import synclock


_lock = threading.Lock()

TYPE_WSN = 0
TYPE_CLASSIC = 1

DATA_TITLE = 0
DATA_DESC = 1
DATA_AUTHOR = 2
DATA_LEVEL = 3

class ScenariodbUpdatingThread(threading.Thread):
    _finished = False

    def __init__(self, setting, vacuum=False, dpath=u"Scenario", skintype=u""):
        threading.Thread.__init__(self)
        self.setting = setting
        self._vacuum = vacuum
        self._dpath = dpath
        self._skintype = skintype

    def run(self):
        type(self)._finished = False
        db = Scenariodb()
        db.update(skintype=self._skintype)
        folders = set()
        folders.add(self._dpath)
        for _skintype, folder in self.setting.folderoftype:
            if not folder in folders:
                db.update(folder, skintype=self._skintype)
                folders.add(folder)

        if self._vacuum:
            db.vacuum()

        db.close()
        type(self)._finished = True

    @staticmethod
    def is_finished():
        return ScenariodbUpdatingThread._finished

class Scenariodb(object):

    """シナリオデータベース。ロックのタイムアウトは30秒指定。
    データ種類は、
    dpath(ファイルのあるディレクトリ),
    type(シナリオのタイプ。0=wsn, 1=クラシック),
    fname(wsnファイル名、またはフォルダ名),
    name(シナリオ名),
    author(作者),
    desc(解説文),
    skintype(スキン種類),
    levelmin(最低対象レベル),
    levelmax(最高対象レベル),
    coupons(必須クーポン。"\n"が区切り),
    couponsnum(必須クーポン数),
    startid(開始エリアID),
    tags(タグ。"\n"が区切り),
    ctime(DB登録時間。エポック秒),
    mtime(ファイル最終更新時間。エポック秒),
    image(見出し画像。バイナリ)
    """
    @synclock(_lock)
    def __init__(self):
        self.name = "Scenario.db"

        if os.path.isfile(self.name):
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()
            needcommit = False

            # type列が存在しない場合は作成する(旧バージョンとの互換性維持)
            cur = self.con.execute("PRAGMA table_info('scenariodb')")
            res = cur.fetchall()
            hastype = False
            for rec in res:
                if rec[1] == "type":
                    hastype = True
                    break
            if not hastype:
                self.cur.execute("ALTER TABLE scenariodb ADD COLUMN type INTEGER")
                self.cur.execute("UPDATE scenariodb SET type=?", (TYPE_WSN,))
                needcommit = True

            cur = self.con.execute("PRAGMA index_info('scenariodb_index1')")
            res = cur.fetchall()
            if not len(res):
                self.cur.execute("CREATE INDEX scenariodb_index1 ON scenariodb(dpath)")
                needcommit = True

            cur = self.con.execute("PRAGMA table_info('scenariotype')")
            res = cur.fetchall()
            if not res:
                s = """
                    CREATE TABLE scenariotype (
                        dpath TEXT,
                        fname TEXT,
                        skintype TEXT,
                        PRIMARY KEY (dpath, fname, skintype)
                    )
                """
                self.cur.execute(s)
                needcommit = True

            if needcommit:
                self.con.commit()
        else:
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()
            # テーブル作成
            s = """CREATE TABLE scenariodb (
                   dpath TEXT, type INTEGER, fname TEXT, name TEXT, author TEXT,
                   desc TEXT, skintype TEXT, levelmin INTEGER, levelmax INTEGER,
                   coupons TEXT, couponsnum INTEGER, startid INTEGER,
                   tags TEXT, ctime INTEGER, mtime INTEGER, image BLOB,
                   PRIMARY KEY (dpath, fname))"""

            self.cur.execute(s)
            self.cur.execute("CREATE INDEX scenariodb_index1 ON scenariodb(dpath)")

            s = """
                CREATE TABLE scenariotype (
                    dpath TEXT,
                    fname TEXT,
                    skintype TEXT,
                    PRIMARY KEY (dpath, fname, skintype)
                )
            """
            self.cur.execute(s)
            self.cur.execute("CREATE INDEX scenariotype_index1 ON scenariodb(dpath, fname)")

    @synclock(_lock)
    def update(self, dpath=u"Scenario", skintype=u""):
        """データベースを更新する。"""
        if skintype:
            s = "SELECT A.dpath, A.fname, mtime, B.skintype FROM scenariodb A LEFT JOIN scenariotype B" +\
                " ON A.dpath=B.dpath AND A.fname=B.fname" +\
                " WHERE A.dpath=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (cw.util.get_linktarget(dpath),skintype,))
        else:
            s = "SELECT dpath, fname, mtime FROM scenariodb WHERE dpath=?"
            self.cur.execute(s, (cw.util.get_linktarget(dpath),))
        data = self.cur.fetchall()
        dbpaths = []

        def update_path(t, spath, path):
            if os.path.getmtime(spath) > t[2]:
                # 情報を更新
                self._insert_scenario(path, False, skintype=skintype)
            elif skintype and t[3] is None:
                # タイプ情報がないので収集
                self._insert_scenario(path, False, skintype=skintype)

        for t in data:
            path = "/".join((t[0], t[1]))
            ltarg = cw.util.get_linktarget(path)

            if not os.path.isfile(ltarg):
                spath = cw.util.join_paths(ltarg, "Summary.wsm")
                if os.path.isfile(spath):
                    # クラシックなシナリオ
                    dbpaths.append(path)
                    update_path(t, spath, path)
                    continue

                spath = cw.util.join_paths(ltarg, "Summary.xml")
                if os.path.isfile(spath):
                    # 展開済みのシナリオ
                    dbpaths.append(path)
                    update_path(t, spath, path)
                    continue

                self.delete(path, False)
            else:
                dbpaths.append(path)
                update_path(t, ltarg, path)

        self.con.commit()
        dbpaths = set(dbpaths)

        for path in get_scenariopaths(dpath):
            if not path in dbpaths:
                self._insert_scenario(path, False, skintype=skintype)

        self.con.commit()

    def vacuum(self, commit=True):
        """肥大化したDBファイルのサイズを最適化する。"""
        # 存在しないディレクトリが含まれる場合は除去
        s = "SELECT dpath FROM scenariodb GROUP BY dpath"
        self.cur.execute(s)
        res = self.cur.fetchall()
        for t in res:
            dpath = t[0]
            if not dpath or not os.path.isdir(dpath):
                s = "DELETE FROM scenariodb WHERE dpath=?"
                self.cur.execute(s, (dpath,))
                s = "DELETE FROM scenariotype WHERE dpath=?"
                self.cur.execute(s, (dpath,))

        # データ量によっては処理に秒単位で時間がかかる上、
        # 再利用可能な領域が減ってパフォーマンスが落ちるため実施しない
        ##s = "VACUUM scenariodb, scenariotype"
        ##self.cur.execute(s)
        ##s = "VACUUM scenariotype"
        ##self.cur.execute(s)

        if commit:
            self.con.commit()

    def delete(self, path, commit=True):
        path = path.replace("\\", "/")
        dpath, fname = os.path.split(path)
        s = "DELETE FROM scenariodb WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))
        s = "DELETE FROM scenariotype WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))

        if commit:
            self.con.commit()

    def insert(self, t, commit=True, skintype=u""):
        s = """INSERT OR REPLACE INTO scenariodb
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.cur.execute(s, t)
        if skintype:
            s = """INSERT OR REPLACE INTO scenariotype
                   VALUES(?, ?, ?)"""
            self.cur.execute(s, (t[0], t[2], skintype,))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_scenario(self, path, commit=True, skintype=u""):
        """データベースにシナリオを登録する。"""
        self._insert_scenario(path, commit, skintype=skintype)

    def _insert_scenario(self, path, commit=True, skintype=u""):
        t = read_summary(path)

        if t:
            self.insert(t, commit, skintype=skintype)
            return True
        elif path.startswith(u"Scenario"):
            # 登録できなかったファイルを移動
            # (Scenarioフォルダ内のみ)
            ##dname = "UnregisteredScenario"

            ##if not os.path.isdir(dname):
            ##    os.makedirs(dname)

            ##dst = cw.util.join_paths(dname, os.path.basename(path))
            ##dst = cw.util.dupcheck_plus(dst, False)
            ##shutil.move(path, dst)
            return False

    def create_header(self, data, skintype=u""):
        """
        データベース内のシナリオ情報からヘッダ部分を返す。
        情報が古くなっている場合は更新する。
        """
        if not data:
            return None

        header = cw.header.ScenarioHeader(data)
        path = header.get_fpath()
        ltarg = cw.util.get_linktarget(path)

        if not os.path.isfile(ltarg):
            def func(spath, header):
                # クラシックなシナリオ
                if os.path.getmtime(spath) > header.mtime:
                    cs = read_summary(path)
                    if cs:
                        self.insert(cs, True, skintype=skintype)
                        # 更新後の情報を取得
                        header = self._search_path(path, skintype=skintype)
                        return header
                else:
                    # 更新は不要
                    return header
            spath = cw.util.join_paths(ltarg, "Summary.wsm")
            if os.path.isfile(spath):
                return func(spath, header)
            spath = cw.util.join_paths(ltarg, "Summary.xml")
            if os.path.isfile(spath):
                return func(spath, header)
            self.delete(path)
            return None
        elif os.path.getmtime(ltarg) > header.mtime:
            if self._insert_scenario(path):
                # 更新後の情報を取得
                header = self._search_path(path, skintype=skintype)
            else:
                return None

        return header

    def create_headers(self, data, skintype=u""):
        """
        データベース内のシナリオ群のヘッダを返す。
        その際、情報が古くなっている場合は更新する。
        """
        headers = []
        names = set()

        for t in data:
            header = self.create_header(t, skintype=skintype)

            if header:
                headers.append(header)
                names.add(header.fname)

        return headers, names

    def sort_headers(self, headers):
        cw.util.sort_by_attr(headers, "name")
        cw.util.sort_by_attr(headers, "levelmax")
        cw.util.sort_by_attr(headers, "levelmin")
        return headers

    @synclock(_lock)
    def search_path(self, path, skintype=u""):
        return self._search_path(path, skintype=skintype)

    def _search_path(self, path, skintype=u""):
        path = path.replace("\\", "/")
        dpath, fname = os.path.split(path)
        self._fetch(dpath, fname, skintype)
        data = self.cur.fetchone()

        ltarg = cw.util.get_linktarget(path)
        if not data and os.path.exists(ltarg):
            if self._insert_scenario(path, skintype=skintype):
                self._fetch(dpath, fname, skintype)
                data = self.cur.fetchone()

        return self.create_header(data, skintype=skintype)

    def _fetch(self, dpath, fname, skintype):
        if skintype:
            s = "SELECT A.* FROM scenariodb A LEFT JOIN scenariotype B" +\
                " ON A.dpath=B.dpath AND A.fname=B.fname" +\
                " WHERE A.dpath=? AND A.fname=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (dpath, fname, skintype,))
        else:
            s = "SELECT * FROM scenariodb WHERE dpath=? AND fname=?"
            self.cur.execute(s, (dpath, fname,))

    @synclock(_lock)
    def search_dpath(self, dpath, create=False, skintype=u""):
        dpath = cw.util.get_linktarget(dpath).replace("\\", "/")

        if skintype:
            s = "SELECT A.* FROM scenariodb A LEFT JOIN scenariotype B" +\
                " ON A.dpath=B.dpath AND A.fname=B.fname" +\
                " WHERE A.dpath=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (dpath, skintype,))
        else:
            s = "SELECT * FROM scenariodb WHERE dpath=?"
            self.cur.execute(s, (dpath,))

        data = self.cur.fetchall()
        headers, names = self.create_headers(data, skintype=skintype)
        # データベースに登録されていないシナリオファイルがないかチェック
        dbpaths = set([h.get_fpath() for h in headers])

        if not os.path.exists(dpath):
            if create:
                os.makedirs(dpath)
            else:
                return []

        for name in os.listdir(unicode(dpath)):
            if name in names:
                continue
            path = cw.util.join_paths(dpath, name)
            ltarg = cw.util.get_linktarget(path)
            name = os.path.basename(ltarg)

            lname = name.lower()
            if not path in dbpaths and os.path.isfile(ltarg)\
                    and (lname.endswith(".wsn") or\
                         lname.endswith(".zip") or\
                         lname.endswith(".lzh") or\
                         lname.endswith(".cab")):
                header = self._search_path(path, skintype=skintype)

                if header:
                    headers.append(header)

        return self.sort_headers(headers)

    @synclock(_lock)
    def get_header(self, path, skintype=u""):
        dpath = os.path.dirname(path)
        fname = os.path.basename(path)
        self._fetch(dpath, fname, skintype)
        data = self.cur.fetchall()
        for t in data:
            return self.create_header(t, skintype=skintype)
        return None

    @synclock(_lock)
    def find_headers(self, ftype, value, skintype=u""):
        if ftype == DATA_TITLE:
            where = "name LIKE ? ESCAPE '\\'"
        elif ftype == DATA_DESC:
            where = "desc LIKE ? ESCAPE '\\'"
        elif ftype == DATA_AUTHOR:
            where = "author LIKE ? ESCAPE '\\'"
        elif ftype == DATA_LEVEL:
            where = "levelmin <= ? AND ? <= levelmax"
        else:
            raise Exception()

        def encode_like(value):
            value2 = value.replace("\\", "\\\\")
            value2 = value2.replace("%", "\\%")
            value2 = value2.replace("_", "\\_")
            value2 = '%' + value2 + '%'
            return value2

        if skintype:
            s = "SELECT A.* FROM scenariodb A LEFT JOIN scenariotype B" +\
                " ON A.dpath=B.dpath AND A.fname=B.fname" +\
                " WHERE " + where +\
                "     AND (B.skintype=? OR B.skintype IS NULL)"
            if ftype == DATA_LEVEL:
                values = (value, value, skintype,)
            else:
                values = (encode_like(value), skintype,)
        else:
            s = "SELECT * FROM scenariodb WHERE " + where
            if ftype == DATA_LEVEL:
                values = (value, value,)
            else:
                values = (encode_like(value),)

        if ftype == DATA_LEVEL:
            v = value
        else:
            v = value.lower()

        self.cur.execute(s, values)
        data = self.cur.fetchall()
        # 検索ではスキン情報は更新しない
        headers, _names = self.create_headers(data, skintype=u"")

        # 情報が更新されている可能性があるため再チェック
        seq = []
        for header in headers:
            if ftype == DATA_TITLE:
                if not v in header.name.lower():
                    continue
            elif ftype == DATA_AUTHOR:
                if not v in header.author.lower():
                    continue
            elif ftype == DATA_DESC:
                if not v in header.desc.lower():
                    continue
            elif ftype == DATA_LEVEL:
                if not (header.levelmin <= v <= header.levelmax):
                    continue
            else:
                assert False
            seq.append(header)

        return self.sort_headers(seq)

    def close(self):
        self.con.close()

def is_scenario(path):
    """
    指定されたパスがシナリオならTrueを返す。
    """
    ltarg = cw.util.get_linktarget(path)
    if os.path.isdir(ltarg):
        spath = cw.util.join_paths(ltarg, "Summary.wsm")
        if os.path.isfile(spath):
            return True
        spath = cw.util.join_paths(ltarg, "Summary.xml")
        if os.path.isfile(spath):
            return True
        return False
    else:
        lpath = ltarg.lower()
        return lpath.endswith(".wsn") or\
               lpath.endswith(".zip") or\
               lpath.endswith(".lzh") or\
               lpath.endswith(".cab")

def read_summary(basepath):
    path = cw.util.get_linktarget(basepath)
    if os.path.isdir(path):
        f = None
        try:
            spath = cw.util.join_paths(path, "Summary.wsm")
            if os.path.isfile(spath):
                with cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True) as f:
                    return read_summary_classic(basepath, spath, f)

            spath = cw.util.join_paths(path, "Summary.xml")
            if os.path.isfile(spath):
                e = cw.data.xml2element(spath, "Property")
                imgpath, summaryinfos = parse_summarydata(spath, e, TYPE_WSN, False, os.path.getmtime(spath))
                imgbuf = ""
                if imgpath:
                    imgpath = cw.util.join_paths(path, imgpath)
                    if os.path.isfile(imgpath):
                        with open(imgpath, "rb") as f2:
                            imgbuf = f2.read()
                imgbuf = buffer(imgbuf)
                summaryinfos.append(imgbuf)
                return tuple(summaryinfos)
        except:
            cw.util.print_ex()
            return None

    if path.lower().endswith(".cab"):
        try:
            if cw.util.cab_hasfile(path, "Summary.wsm"):
                dpath = cw.util.join_paths(cw.tempdir, u"Cab")
                if not os.path.isdir(dpath):
                    os.makedirs(dpath)
                s = "expand \"%s\" -I -f:%s \"%s\"" % (path, "Summary.wsm", dpath)
                encoding = sys.getfilesystemencoding()
                ret = subprocess.call(s.encode(encoding), shell=True)
                if ret == 0:
                    spath = cw.util.join_paths(dpath, os.listdir(dpath)[0])
                    f = None
                    try:
                        with cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True) as f:
                            return read_summary_classic(basepath, path, f)
                    finally:
                        os.remove(spath)
                else:
                    return None
            else:
                summpath = cw.util.cab_hasfile(path, "Summary.xml")
                if summpath:
                    scedir = os.path.dirname(summpath)
                    dpath = cw.util.join_paths(cw.tempdir, u"Cab")
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    s = "expand \"%s\" -f:%s \"%s\"" % (path, "Summary.xml", dpath)
                    encoding = sys.getfilesystemencoding()
                    ret = subprocess.call(s.encode(encoding), shell=True)
                    summpath2 = cw.util.join_paths(dpath, summpath)
                    if ret == 0 and os.path.isfile(summpath2):
                        try:
                            e = cw.data.xml2element(summpath2, "Property")

                            try:
                                imgpath, summaryinfos = parse_summarydata(basepath, e, TYPE_WSN, True, os.path.getmtime(path))
                            except:
                                return None

                            imgbuf = ""
                            if imgpath:
                                imgpath = cw.util.join_paths(scedir, imgpath)
                                s = "expand \"%s\" -f:\"%s\" \"%s\"" % (path, os.path.basename(imgpath), dpath)
                                encoding = sys.getfilesystemencoding()
                                ret = subprocess.call(s.encode(encoding), shell=True)
                                imgpath2 = cw.util.join_paths(dpath, imgpath)
                                if ret == 0 and os.path.isfile(imgpath2):
                                    with open(imgpath2, "rb") as f:
                                        imgbuf = f.read()

                            imgbuf = buffer(imgbuf)
                            summaryinfos.append(imgbuf)
                            return tuple(summaryinfos)

                        finally:
                            for p in os.listdir(dpath):
                                cw.util.remove(cw.util.join_paths(dpath, p))
                return None
        except Exception:
            cw.util.print_ex()
            return None

    try:
        z = cw.util.zip_file(path, "r")
    except:
        cw.util.print_ex()
        return None

    names = z.namelist()
    seq = [name for name in names if name.lower().endswith("summary.xml") or name.lower().endswith("summary.wsm")]

    if not seq:
        z.close()
        return None

    name = seq[0]
    if name.lower().endswith(".wsm"):
        fdata = z.read(name)
        f = cw.binary.cwfile.CWFile("", "rb", decodewrap=True, f=io.BytesIO(fdata))
        return read_summary_classic(path, path, f)

    scedir = os.path.dirname(name)
    scedir = cw.util.decode_zipname(scedir)
    fdata = z.read(name)
    f = StringIO.StringIO(fdata)
    try:
        e = cw.data.xml2element(path, "Property", stream=f)
    finally:
        f.close()

    try:
        imgpath, summaryinfos = parse_summarydata(basepath, e, TYPE_WSN, True, os.path.getmtime(path))
    except:
        z.close()
        return None

    if imgpath:
        imgpath = cw.util.join_paths(scedir, imgpath)
        imgbuf = cw.util.read_zipdata(z, imgpath)
    else:
        imgbuf = ""

    imgbuf = buffer(imgbuf)
    z.close()
    summaryinfos.append(imgbuf)
    return tuple(summaryinfos)

def parse_summarydata(basepath, data, scetype, archive, mtime):
    e = data.find("ImagePath")
    imgpath = e.text or ""
    e = data.find("Name")
    name = e.text or ""
    e = data.find("Author")
    author = e.text or ""
    e = data.find("Description")
    desc = e.text or ""
    desc = cw.util.txtwrap(desc, 4)
    e = data.find("Type")
    skintype = e.text or ""
    e = data.find("Level")
    levelmin = int(e.get("min", 0))
    levelmax = int(e.get("max", 0))
    e = data.find("RequiredCoupons")
    coupons = e.text or ""
    clist = cw.util.decodewrap(coupons)
    coupons = []
    for coupon in clist:
        if coupon:
            coupons.append(coupon)
    coupons = cw.util.encodewrap(coupons)
    couponsnum = int(e.get("number", 0))
    e = data.find("StartAreaId")
    startid = int(e.text) if e.text else 0
    e = data.find("Tags")
    tags = e.text or ""
    tags = cw.util.decodewrap(tags)
    ctime = time.time()
    if archive:
        dpath, fname = os.path.split(basepath)
    else:
        dpath, fname = os.path.split(os.path.dirname(basepath))
    return (imgpath, [dpath, scetype, fname, name, author, desc, skintype, levelmin,
                levelmax, coupons, couponsnum, startid, tags, ctime, mtime])

def read_summary_classic(basepath, spath, f=None):
    try:
        if not f:
            f = cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True)
        s = cw.binary.summary.Summary(None, f, nameonly=False, materialdir="", image_export=False)
        if 4 < s.version:
            return None
        s.skintype = ""
        imgbuf = s.image
        ctime = time.time()
        mtime = os.path.getmtime(spath)
    except Exception:
        return None

    summaryinfos = [os.path.dirname(basepath), TYPE_CLASSIC,
            os.path.basename(basepath), s.name, s.author,
            s.description, s.skintype, s.level_min, s.level_max,
            s.required_coupons, s.required_coupons_num,
            s.area_id, s.tags, ctime, mtime]
    if imgbuf:
        imgbuf = buffer(imgbuf)
    summaryinfos.append(imgbuf)
    return tuple(summaryinfos)

def get_scenariopaths(path):
    path = cw.util.get_linktarget(path)
    if not os.path.isdir(path):
        return
    for fname in os.listdir(path):
        fname = cw.util.join_paths(path, fname)
        ltarg = cw.util.get_linktarget(fname)
        if os.path.isdir(ltarg):
            fpath = cw.util.join_paths(ltarg, "Summary.wsm")
            if os.path.isfile(fpath):
                yield fname
            fpath = cw.util.join_paths(ltarg, "Summary.xml")
            if os.path.isfile(fpath):
                yield fname
        else:
            lfile = ltarg.lower()
            if lfile.endswith(".wsn") or\
               lfile.endswith(".zip") or\
               lfile.endswith(".lzh") or\
               lfile.endswith(".cab"):
                yield fname

def main():
    db = Scenariodb()
    db.update()
    db.close()

if __name__ == "__main__":
    main()
