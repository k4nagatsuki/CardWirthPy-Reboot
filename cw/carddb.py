#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import threading
import time

import cw
import cw.binary
from cw.util import synclock


_lock = threading.Lock()

class CardDB(object):

    """カードのデータベース。ロックのタイムアウトは30秒指定。"""
    @synclock(_lock)
    def __init__(self, ypath):
        self.ypath = ypath
        self.name = os.path.join(ypath, "Card.db")

        if os.path.isfile(self.name):
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()
        else:
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.cur = self.con.cursor()
            # テーブル作成
            s = """
                CREATE TABLE card (
                    fpath TEXT,
                    type INTEGER,
                    id INTEGER,
                    name TEXT,
                    desc TEXT,
                    scenario TEXT,
                    author TEXT,
                    keycodes TEXT,
                    uselimit INTEGER,
                    target TEXT,
                    allrange INTEGER,
                    premium TEXT,
                    physical TEXT,
                    mental TEXT,
                    level INTEGER,
                    maxuselimit INTEGER,
                    price INTEGER,
                    hold INTEGER,
                    enhance_avo INTEGER,
                    enhance_res INTEGER,
                    enhance_def INTEGER,
                    enhance_avo_used INTEGER,
                    enhance_res_used INTEGER,
                    enhance_def_used INTEGER,
                    attachment INTEGER,
                    imagepath TEXT,
                    ctime INTEGER,
                    mtime INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

    @synclock(_lock)
    def update(self):
        """データベースを更新する。"""
        s = "SELECT fpath, mtime FROM card"
        self.cur.execute(s)
        data = self.cur.fetchall()
        dbpaths = set()

        for t in data:
            path = cw.util.join_paths(self.ypath, t[0])

            if not os.path.isfile(path):
                self._delete(t[0], False)
            else:
                dbpaths.add(path)

                if os.path.getmtime(path) > t[1]:
                    # 情報を更新
                    self._insert(path, False)

        def walk(dpath):
            dpath = cw.util.join_paths(self.ypath, dpath)
            if os.path.isdir(dpath):
                for file in os.listdir(dpath):
                    path = cw.util.join_paths(dpath, file)
                    if not path in dbpaths:
                        self._insert(path, False)
        walk("SkillCard")
        walk("ItemCard")
        walk("BeastCard")

        self.con.commit()

    def vacuum(self, commit=True):
        """肥大化したDBファイルのサイズを最適化する。"""
        s = "VACUUM card"
        self.cur.execute(s)

        if commit:
            self.con.commit()

    def _delete(self, path, commit=True):
        s = "DELETE FROM card WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_header(self, header, commit=True):
        return self._insert_header(header, commit)

    def _insert_header(self, header, commit=True):
        """データベースにカードを登録する。"""
        s = """
        INSERT OR REPLACE INTO card VALUES(
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """
        fpath = cw.util.join_paths(os.path.relpath(header.fpath, self.ypath))
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        self.cur.execute(s, (
            fpath,
            header.type,
            header.id,
            header.name,
            header.desc,
            header.scenario,
            header.author,
            "\n".join(header.keycodes[:-1]),
            header.uselimit,
            header.target,
            header.allrange,
            header.premium,
            header.physical,
            header.mental,
            header.level,
            header.maxuselimit,
            header.price,
            header.hold,
            header.enhance_avo,
            header.enhance_res,
            header.enhance_def,
            header.enhance_avo_used,
            header.enhance_res_used,
            header.enhance_def_used,
            header.attachment,
            header.imagepath,
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert(self, path, commit=True):
        return self._insert(path, commit)

    def _insert(self, path, commit=True):
        try:
            data = cw.data.xml2element(path)
            header = cw.header.CardHeader(carddata=data)
            header.fpath = path
            return self._insert_header(header, commit)
        except Exception, ex:
            pass

    def get_cards(self):
        s = "SELECT * FROM card ORDER BY name"
        self.cur.execute(s)
        data = self.cur.fetchall()
        headers = []
        for rec in data:
            headers.append(cw.header.CardHeader(dbrec=rec))
        return headers


    @synclock(_lock)
    def close(self):
        self.con.close()
