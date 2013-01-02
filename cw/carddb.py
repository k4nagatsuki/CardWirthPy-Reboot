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

            # カード置場のカード
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
                    imgpath TEXT,
                    ctime INTEGER,
                    mtime INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

            # 宿帳とアルバムの冒険者
            s = """
                CREATE TABLE adventurer (
                    fpath TEXT,
                    level INTEGER,
                    name TEXT,
                    imgpath TEXT,
                    album INTEGER,
                    lost INTEGER,
                    sex TEXT,
                    age TEXT,
                    ep INTEGER,
                    leavenoalbum INTEGER,
                    gene TEXT,
                    history TEXT,
                    race TEXT,
                    ctime INTEGER,
                    mtime INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

    @synclock(_lock)
    def update(self):
        """データベースを更新する。"""
        def walk(dpath, insert, *args):
            dpath = cw.util.join_paths(self.ypath, dpath)
            if os.path.isdir(dpath):
                for file in os.listdir(dpath):
                    path = cw.util.join_paths(dpath, file)
                    if not path in dbpaths:
                        insert(path, *args)

        s = "SELECT fpath, mtime FROM card"
        self.cur.execute(s)
        data = self.cur.fetchall()
        dbpaths = set()
        for t in data:
            path = cw.util.join_paths(self.ypath, t[0])
            if not os.path.isfile(path):
                self._delete_card(t[0], False)
            else:
                dbpaths.add(path)
                if os.path.getmtime(path) > t[1]:
                    # 情報を更新
                    self._insert_card(path, False)
        walk("SkillCard", self._insert_card, False)
        walk("ItemCard", self._insert_card, False)
        walk("BeastCard", self._insert_card, False)

        s = "SELECT fpath, mtime, album FROM adventurer"
        self.cur.execute(s)
        data = self.cur.fetchall()
        dbpaths = set()
        for t in data:
            path = cw.util.join_paths(self.ypath, t[0])
            if not os.path.isfile(path):
                self._delete_adventurer(t[0], False)
            else:
                dbpaths.add(path)
                if os.path.getmtime(path) > t[1]:
                    # 情報を更新
                    self._insert_adventurer(path, bool(t[2]), False)
        walk("Adventurer", self._insert_adventurer, False, False)
        walk("Album", self._insert_adventurer, True, False)

        self.con.commit()

    def vacuum(self, commit=True):
        """肥大化したDBファイルのサイズを最適化する。"""
        s = "VACUUM card"
        self.cur.execute(s)
        s = "VACUUM adventurer"
        self.cur.execute(s)

        if commit:
            self.con.commit()

    def _delete_card(self, path, commit=True):
        s = "DELETE FROM card WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    def _delete_adventurer(self, path, commit=True):
        s = "DELETE FROM adventurer WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_cardheader(self, header, commit=True):
        return self._insert_cardheader(header, commit)

    def _insert_cardheader(self, header, commit=True):
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
            os.path.relpath(header.imgpath, self.ypath),
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_card(self, path, commit=True):
        return self._insert_card(path, commit)

    def _insert_card(self, path, commit=True):
        try:
            data = cw.data.xml2element(path)
            header = cw.header.CardHeader(carddata=data)
            header.fpath = path
            return self._insert_cardheader(header, commit)
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
    def insert_adventurerheader(self, header, commit=True):
        return self._insert_adventurerheader(header, commit)

    def _insert_adventurerheader(self, header, commit=True):
        """データベースにカードを登録する。"""
        s = """
        INSERT OR REPLACE INTO adventurer VALUES(
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
        if header.album:
            album = 1
        else:
            album= 0
        self.cur.execute(s, (
            fpath,
            header.level,
            header.name,
            header.imgpath,
            album,
            header.lost,
            header.sex,
            header.age,
            header.ep,
            header.leavenoalbum,
            header.gene.get_str(),
            "\n".join(header.history),
            header.race,
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_adventurer(self, path, album, commit=True):
        return self._insert_adventurer(path, album, commit)

    def _insert_adventurer(self, path, album, commit=True):
        try:
            data = cw.data.xml2etree(path)
            e = data.find("Property")
            header = cw.header.AdventurerHeader(e, album=album)
            header.fpath = path
            return self._insert_adventurerheader(header, commit)
        except Exception, ex:
            pass

    def get_adventurers(self, album):
        s = "SELECT * FROM adventurer WHERE album=? ORDER BY name"
        if album:
            album = 1
        else:
            album = 0
        self.cur.execute(s, (album,))
        data = self.cur.fetchall()
        headers = []
        for rec in data:
            headers.append(cw.header.AdventurerHeader(dbrec=rec))
        return headers

    def get_standbys(self):
        return self.get_adventurers(False)

    def get_album(self):
        return self.get_adventurers(True)

    @synclock(_lock)
    def close(self):
        self.con.close()
