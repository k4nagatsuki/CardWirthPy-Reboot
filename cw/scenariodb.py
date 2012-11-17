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
    fname(wsnファイル名),
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
        else:
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()
            # テーブル作成
            s = """CREATE TABLE scenariodb (
                   dpath TEXT, fname TEXT, name TEXT, author TEXT, desc TEXT,
                   skintype TEXT, levelmin INTEGER, levelmax INTEGER,
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
                self.delete(path, False)
            else:
                dbpaths.append(path)

                if os.path.getmtime(path) > t[2]:
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
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.cur.execute(s, t)

        if commit:
            self.con.commit()

    def insert_scenario(self, path, commit=True):
        """データベースにシナリオを登録する。"""
        t = read_summary(path)

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
        if not data:
            return None

        header = cw.header.ScenarioHeader(data)
        path = header.get_fpath()

        if not os.path.isfile(path):
            self.delete(path)
            return None
        elif os.path.getmtime(path) > header.mtime:
            if self.insert_scenario(path):
                header = self.search_path(path)
            else:
                return None

        return header

    def create_headers(self, data):
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
        imgpath, summaryinfos = parse_summarydata(e)
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

def parse_summarydata(data):
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
    coupons = coupons.replace("\\n", "\n")
    couponsnum = int(e.get("number", 0))
    e = data.find("StartAreaId")
    startid = int(e.text) if e.text else 0
    e = data.find("Tags")
    tags = e.text or ""
    tags = tags.replace("\\n", "\n")
    ctime = time.time()
    mtime = os.path.getmtime(data.fpath)
    dpath, fname = os.path.split(data.fpath)
    return (imgpath, [dpath, fname, name, author, desc, skintype, levelmin,
                levelmax, coupons, couponsnum, startid, tags, ctime, mtime])

def get_scenariopaths():
    for dpath, dnames, fnames in os.walk(u"Scenario"):
        for fname in fnames:
            if fname.lower().endswith(".wsn"):
                fpath = cw.util.join_paths(dpath, fname)
                yield fpath

def main():
    db = Scenariodb()
    db.update()
    db.close()

if __name__ == "__main__":
    main()
