#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import zipfile
import StringIO
import sqlite3
import threading
import shutil

import cw
import cw.binary


TYPE_WSN = 0
TYPE_CLASSIC = 1

class ScenariodbUpdatingThread(threading.Thread):
    _finished = False

    def __init__(self, vacuum=False):
        threading.Thread.__init__(self)
        self._vacuum = vacuum

    def run(self):
        type(self)._finished = False
        db = Scenariodb()
        db.update()

        if self._vacuum:
            db.vacuum()

        db.close()
        type(self)._finished = True

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
    def __init__(self):
        self.name = "Scenario.db"

        if os.path.isfile(self.name):
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()

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
                self.cur.execute("UPDATE scenariodb SET type=?", [TYPE_WSN])
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

    def update(self):
        """データベースを更新する。"""
        s = "SELECT dpath, fname, mtime FROM scenariodb"
        self.cur.execute(s)
        data = self.cur.fetchall()
        dbpaths = []

        for t in data:
            path = "/".join((t[0], t[1]))

            if not os.path.isfile(path):
                spath = cw.util.join_paths(path, "Summary.wsm")
                if os.path.exists(spath):
                    # クラシックなシナリオ
                    dbpaths.append(path)
                    if os.path.getmtime(spath) > t[2]:
                        # 情報を更新
                        self.insert_scenario(path, False)
                else:
                    self.delete(path, False)
            else:
                dbpaths.append(path)

                if os.path.getmtime(path) > t[2]:
                    # 情報を更新
                    self.insert_scenario(path, False)

        self.con.commit()
        dbpaths = set(dbpaths)

        for path in get_scenariopaths():
            if not path in dbpaths:
                self.insert_scenario(path, False)

        self.con.commit()

    def vacuum(self, commit=True):
        """肥大化したDBファイルのサイズを最適化する。"""
        s = "VACUUM scenariodb"
        self.cur.execute(s)

        if commit:
            self.con.commit()

    def delete(self, path, commit=True):
        path = path.replace("\\", "/")
        dpath, fname = os.path.split(path)
        s = "DELETE FROM scenariodb WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))

        if commit:
            self.con.commit()

    def insert(self, t, commit=True):
        s = """INSERT OR REPLACE INTO scenariodb
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.cur.execute(s, t)

        if commit:
            self.con.commit()

    def insert_scenario(self, path, commit=True):
        """データベースにシナリオを登録する。"""
        if path.lower().endswith(".wsn"):
            t = read_summary(path)
        else:
            t = read_summary_classic(path)

        if t:
            self.insert(t, commit)
            return True
        else:
            # 登録できなかったファイルを移動
            dname = "UnregisteredScenario"

            if not os.path.isdir(dname):
                os.makedirs(dname)

            dst = cw.util.join_paths(dname, os.path.basename(path))
            dst = cw.util.dupcheck_plus(dst, False)
            shutil.move(path, dst)
            return False

    def create_header(self, data):
        """
        データベース内のシナリオ情報からヘッダ部分を返す。
        情報が古くなっている場合は更新する。
        """
        if not data:
            return None

        header = cw.header.ScenarioHeader(data)
        path = header.get_fpath()

        if not os.path.isfile(path):
            spath = cw.util.join_paths(path, "Summary.wsm")
            if os.path.exists(spath):
                # クラシックなシナリオ
                if os.path.getmtime(spath) > header.mtime:
                    cs = read_summary_classic(path)
                    if cs and self.insert(cs, True):
                        # 更新後の情報を取得
                        header = self.search_path(path)
                        return header
                else:
                    # 更新は不要
                    return header
            self.delete(path)
            return None
        elif os.path.getmtime(path) > header.mtime:
            if self.insert_scenario(path):
                # 更新後の情報を取得
                header = self.search_path(path)
            else:
                return None

        return header

    def create_headers(self, data):
        """
        データベース内のシナリオ群のヘッダを返す。
        その際、情報が古くなっている場合は更新する。
        """
        headers = []

        for t in data:
            header = self.create_header(t)

            if header:
                headers.append(header)

        return headers

    def sort_headers(self, headers):
        cw.util.sort_by_attr(headers, "name")
        cw.util.sort_by_attr(headers, "levelmax")
        cw.util.sort_by_attr(headers, "levelmin")
        return headers

    def search_path(self, path):
        path = path.replace("\\", "/")
        dpath, fname = os.path.split(path)
        s = "SELECT * FROM scenariodb WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))
        data = self.cur.fetchone()

        if not data and os.path.isfile(path):
            if self.insert_scenario(path):
                self.cur.execute(s, (dpath, fname,))
                data = self.cur.fetchone()

        return self.create_header(data)

    def search_dpath(self, dpath):
        dpath = dpath.replace("\\", "/")
        s = "SELECT * FROM scenariodb WHERE dpath=?"
        self.cur.execute(s, (dpath,))
        data = self.cur.fetchall()
        headers = self.create_headers(data)
        # データベースに登録されていないシナリオファイルがないかチェック
        dbpaths = set([h.get_fpath() for h in headers])

        if not os.path.exists(dpath):
            os.makedirs(dpath)

        for name in os.listdir(unicode(dpath)):
            path = cw.util.join_paths(dpath, name)

            if not path in dbpaths and os.path.isfile(path)\
                                                    and name.endswith(".wsn"):
                header = self.search_path(path)

                if header:
                    headers.append(header)

        return self.sort_headers(headers)

    def search_wildcard(self, q, column):
        q = "%%%s%%" % (q)
        s = "SELECT * FROM scenariodb WHERE %s LIKE ?" % (column)
        self.cur.execute(s, (q,))
        data = self.cur.fetchall()
        headers = self.create_headers(data)
        return self.sort_headers(headers)

    def close(self):
        self.con.close()

def read_summary(path):
    try:
        z = zipfile.ZipFile(path, "r")
    except:
        return None

    names = z.namelist()
    seq = [name for name in names if name.endswith("Summary.xml")]

    if not seq:
        z.close()
        return None

    name = seq[0]
    scedir = os.path.dirname(name)
    scedir = cw.util.decode_zipname(scedir)
    fdata = z.read(name)
    f = StringIO.StringIO(fdata)
    e = cw.data.xml2element(path, "Property", file=f)
    f.close()

    try:
        imgpath, summaryinfos = parse_summarydata(e, TYPE_WSN, True)
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

def read_summary_classic(path):
    spath = cw.util.join_paths(path, "Summary.wsm")

    try:
        cw.cwpy.classicdata = cw.binary.cwscenario.CWScenario(
            path, "Data/Temp/OldScenario", cw.cwpy.setting.skintype,
            materialdir="", image_export=False)
        e = cw.data.xml2element(spath, "Property", None)
        imgpath, summaryinfos = parse_summarydata(e, TYPE_CLASSIC, False)
        imgbuf = cw.binary.image.code_to_data(imgpath)
        cw.cwpy.classicdata = None
    except Exception, ex:
        cw.cwpy.classicdata = None
        return None

    imgbuf = buffer(imgbuf)
    summaryinfos.append(imgbuf)
    return tuple(summaryinfos)

def parse_summarydata(data, type, archive):
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
    coupons = cw.util.decodewrap(coupons)
    couponsnum = int(e.get("number", 0))
    e = data.find("StartAreaId")
    startid = int(e.text) if e.text else 0
    e = data.find("Tags")
    tags = e.text or ""
    tags = cw.util.decodewrap(tags)
    ctime = time.time()
    mtime = os.path.getmtime(data.fpath)
    if archive:
        dpath, fname = os.path.split(data.fpath)
    else:
        dpath, fname = os.path.split(os.path.dirname(data.fpath))
    return (imgpath, [dpath, type, fname, name, author, desc, skintype, levelmin,
                levelmax, coupons, couponsnum, startid, tags, ctime, mtime])

def get_scenariopaths():
    for dpath, dnames, fnames in os.walk(u"Scenario"):
        for fname in fnames:
            if fname.lower().endswith(".wsn"):
                fpath = cw.util.join_paths(dpath, fname)
                yield fpath
            elif fname == "Summary.wsm":
                yield dpath

def main():
    db = Scenariodb()
    db.update()
    db.close()

if __name__ == "__main__":
    main()
