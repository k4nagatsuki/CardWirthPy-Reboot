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

YADO = 0
PARTY = 1

class YadoDB(object):

    """カードのデータベース。ロックのタイムアウトは30秒指定。"""
    @synclock(_lock)
    def __init__(self, ypath, mode=YADO):
        self.ypath = ypath
        if mode == YADO:
            fname = "Yado.db"
        else:
            fname = "Card.db"
        self.name = os.path.join(ypath, fname)
        self.mode = mode

        if os.path.isfile(self.name):
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.con.row_factory = sqlite3.Row
            self.cur = self.con.cursor()

            # cardorderテーブルが存在しない場合は作成する(旧バージョンとの互換性維持)
            cur = self.con.execute("PRAGMA table_info('cardorder')")
            res = cur.fetchall()
            if not res:
                s = """
                    CREATE TABLE cardorder (
                        fpath TEXT,
                        numorder INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)
            if self.mode == YADO:
                # adventurerorderテーブルが存在しない場合は作成する(旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('adventurerorder')")
                res = cur.fetchall()
                if not res:
                    s = """
                        CREATE TABLE adventurerorder (
                            fpath TEXT,
                            numorder INTEGER,
                            PRIMARY KEY (fpath)
                        )
                    """
                    self.cur.execute(s)

            # moved列,scenariocard列,versionhint列が存在しない
            # 場合は作成する(旧バージョンとの互換性維持)
            cur = self.con.execute("PRAGMA table_info('card')")
            res = cur.fetchall()
            hasmoved = False
            hasscenariocard = False
            hasversionhint = False
            for rec in res:
                if rec[1] == "moved":
                    hasmoved = True
                elif rec[1] == "scenariocard":
                    hasscenariocard = True
                elif rec[1] == "versionhint":
                    hasversionhint = True

            reqcommit = False

            if not hasmoved:
                self.cur.execute("ALTER TABLE card ADD COLUMN moved INTEGER")
                self.cur.execute("UPDATE card SET moved=?", (0,))
                reqcommit = True
            if not hasscenariocard:
                self.cur.execute("ALTER TABLE card ADD COLUMN scenariocard INTEGER")
                self.cur.execute("UPDATE card SET scenariocard=?", (0,))
                reqcommit = True
            if not hasversionhint:
                self.cur.execute("ALTER TABLE card ADD COLUMN versionhint TEXT")
                self.cur.execute("UPDATE card SET versionhint=?", ("",))
                reqcommit = True

            if self.mode == YADO:
                # versionhint列が存在しない場合は作成する
                # (旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('adventurer')")
                res = cur.fetchall()
                hasversionhint = False
                for rec in res:
                    if rec[1] == "versionhint":
                        hasversionhint = True
                        break

                if not hasversionhint:
                    self.cur.execute("ALTER TABLE adventurer ADD COLUMN versionhint TEXT")
                    self.cur.execute("UPDATE adventurer SET versionhint=?", ("",))
                    reqcommit = True

            if reqcommit:
                self.con.commit()

        else:
            dir = os.path.dirname(self.name)
            if not os.path.isdir(dir):
                os.makedirs(dir)
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.con.row_factory = sqlite3.Row
            self.cur = self.con.cursor()
            # テーブル作成

            # カード置場のカード
            s = """
                CREATE TABLE card (
                    fpath TEXT,
                    type INTEGER,
                    id INTEGER,
                    name TEXT,
                    imgpath TEXT,
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
                    moved INTEGER,
                    scenariocard INTEGER,
                    versionhint TEXT,
                    ctime INTEGER,
                    mtime INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

            # カードの並び順
            s = """
                CREATE TABLE cardorder (
                    fpath TEXT,
                    numorder INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

            if self.mode == YADO:
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
                        versionhint TEXT,
                        ctime INTEGER,
                        mtime INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

                # 宿帳の並び順
                s = """
                    CREATE TABLE adventurerorder (
                        fpath TEXT,
                        numorder INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

                # パーティ
                s = """
                    CREATE TABLE party (
                        fpath TEXT,
                        name TEXT,
                        money INTEGER,
                        members TEXT,
                        ctime INTEGER,
                        mtime INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

    @synclock(_lock)
    def update(self, cards=True, adventurers=True, parties=True, cardorder={}, adventurerorder={}):
        """データベースを更新する。"""
        def walk(dpath, insert, *args):
            dir = cw.util.join_paths(self.ypath, dpath)
            if os.path.isdir(dir):
                for file in os.listdir(dir):
                    if not file.lower().endswith(".xml"):
                        continue
                    path = cw.util.join_paths(dpath, file)
                    if not path in dbpaths:
                        insert(cw.util.join_paths(self.ypath, path), *args)

        if cards:
            s = "SELECT fpath, mtime FROM card"
            self.cur.execute(s)
            data = self.cur.fetchall()
            dbpaths = set()
            for t in data:
                path = cw.util.join_paths(self.ypath, t[0])
                if not os.path.isfile(path):
                    self._delete_card(t[0], False)
                else:
                    dbpaths.add(t[0])
                    if os.path.getmtime(path) > t[1]:
                        # 情報を更新
                        self._insert_card(path, False)
            walk("SkillCard", self._insert_card, False)
            walk("ItemCard", self._insert_card, False)
            walk("BeastCard", self._insert_card, False)
            if cardorder:
                # カードの並び順を登録する
                s = "DELETE FROM cardorder"
                self.cur.execute(s)
                for fpath, orderc in cardorder.items():
                    s = """
                        INSERT OR REPLACE INTO cardorder VALUES(
                            ?,
                            ?
                        )
                    """
                    self.cur.execute(s, (
                        fpath,
                        orderc,
                    ))

        if self.mode == YADO and adventurers:
            s = "SELECT fpath, mtime, album FROM adventurer"
            self.cur.execute(s)
            data = self.cur.fetchall()
            dbpaths = set()
            for t in data:
                path = cw.util.join_paths(self.ypath, t[0])
                if not os.path.isfile(path):
                    self._delete_adventurer(t[0], False)
                else:
                    dbpaths.add(t[0])
                    if os.path.getmtime(path) > t[1]:
                        # 情報を更新
                        self._insert_adventurer(path, bool(t[2]), False)
            walk("Adventurer", self._insert_adventurer, False, False)
            walk("Album", self._insert_adventurer, True, False)

            if adventurerorder:
                # 冒険者の並び順を登録する
                s = "DELETE FROM adventurerorder"
                self.cur.execute(s)
                for fpath, orderc in adventurerorder.items():
                    s = """
                        INSERT OR REPLACE INTO adventurerorder VALUES(
                            ?,
                            ?
                        )
                    """
                    self.cur.execute(s, (
                        fpath,
                        orderc,
                    ))

        if self.mode == YADO and parties:
            s = "SELECT fpath, mtime FROM party"
            self.cur.execute(s)
            data = self.cur.fetchall()
            dbpaths = set()
            for t in data:
                path = cw.util.join_paths(self.ypath, t[0])
                if not os.path.isfile(path):
                    self._delete_party(t[0], False)
                else:
                    dbpaths.add(t[0])
                    if os.path.getmtime(path) > t[1]:
                        # 情報を更新
                        self._insert_party(path, False)
            for dpath in os.listdir(cw.util.join_paths(self.ypath, "Party")):
                walk(cw.util.join_paths("Party", dpath), self._insert_party, False)

        self.con.commit()

    def vacuum(self, commit=True):
        """肥大化したDBファイルのサイズを最適化する。"""
        s = "VACUUM card"
        self.cur.execute(s)
        if self.mode == YADO:
            s = "VACUUM adventurer"
            self.cur.execute(s)
            s = "VACUUM party"
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

    def _delete_party(self, path, commit=True):
        s = "DELETE FROM party WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_cardheader(self, header, commit=True, cardorder=-1):
        return self._insert_cardheader(header, commit, cardorder)

    def _insert_cardheader(self, header, commit=True, cardorder=-1):
        """データベースにカードを登録する。"""
        s = """
        INSERT OR REPLACE INTO card(
            fpath,
            type,
            id,
            name,
            imgpath,
            desc,
            scenario,
            author,
            keycodes,
            uselimit,
            target,
            allrange,
            premium,
            physical,
            mental,
            level,
            maxuselimit,
            price,
            hold,
            enhance_avo,
            enhance_res,
            enhance_def,
            enhance_avo_used,
            enhance_res_used,
            enhance_def_used,
            attachment,
            moved,
            scenariocard,
            versionhint,
            ctime,
            mtime
        ) VALUES(
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
            ?,
            ?,
            ?,
            ?
        )
        """
        fpath = os.path.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        self.cur.execute(s, (
            fpath,
            header.type,
            header.id,
            header.name,
            header.imgpath,
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
            header.moved,
            1 if header.scenariocard else 0,
            header.versionhint,
            ctime,
            mtime,
        ))
        if -1 < cardorder:
            s = """
            INSERT OR REPLACE INTO cardorder VALUES(
                ?,
                ?
            )
            """
            self.cur.execute(s, (
                fpath,
                cardorder,
            ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_card(self, path, commit=True, cardorder=-1):
        return self._insert_card(path, commit, cardorder)

    def _insert_card(self, path, commit=True, cardorder=-1):
        try:
            data = cw.data.xml2element(path)
            header = cw.header.CardHeader(carddata=data)
            header.fpath = path
            return self._insert_cardheader(header, commit, cardorder)
        except Exception, ex:
            print ex

    def get_cards(self):
        s = """
            SELECT
                card.fpath,
                type,
                id,
                name,
                imgpath,
                desc,
                scenario,
                author,
                keycodes,
                uselimit,
                target,
                allrange,
                premium,
                physical,
                mental,
                level,
                maxuselimit,
                price,
                hold,
                enhance_avo,
                enhance_res,
                enhance_def,
                enhance_avo_used,
                enhance_res_used,
                enhance_def_used,
                attachment,
                moved,
                scenariocard,
                versionhint,
                ctime,
                mtime,
                numorder
            FROM
                card
                LEFT OUTER JOIN
                    cardorder
                ON
                    card.fpath = cardorder.fpath
            ORDER BY
                numorder,
                name
        """
        self.cur.execute(s)

        headers = []
        if self.mode == YADO:
            owner = "STOREHOUSE"
        else:
            owner = "BACKPACK"
        for order, rec in enumerate(self.cur):
            header = cw.header.CardHeader(dbrec=rec, dbowner=owner)
            header.order = order
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    @synclock(_lock)
    def get_cardfpaths(self, scenariocard=True):
        s = """
            SELECT
                card.fpath
            FROM
                card
                LEFT OUTER JOIN
                    cardorder
                ON
                    card.fpath = cardorder.fpath
            WHERE
                scenariocard=?
            ORDER BY
                numorder,
                name
        """
        self.cur.execute(s, (1 if scenariocard else 0,))

        seq = []
        for rec in self.cur:
            seq.append(rec["fpath"])
        return seq

    @synclock(_lock)
    def insert_adventurerheader(self, header, commit=True, adventurerorder=-1):
        return self._insert_adventurerheader(header, commit, adventurerorder)

    def _insert_adventurerheader(self, header, commit=True, adventurerorder=-1):
        """データベースに冒険者を登録する。"""
        s = """
        INSERT OR REPLACE INTO adventurer(
            fpath,
            level,
            name,
            imgpath,
            album,
            lost,
            sex,
            age,
            ep,
            leavenoalbum,
            gene,
            history,
            race,
            versionhint,
            ctime,
            mtime
        ) VALUES(
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
        fpath = os.path.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
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
            header.versionhint,
            ctime,
            mtime,
        ))

        if -1 < adventurerorder:
            s = """
            INSERT OR REPLACE INTO adventurerorder VALUES(
                ?,
                ?
            )
            """
            self.cur.execute(s, (
                fpath,
                adventurerorder,
            ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_adventurer(self, path, album, commit=True, adventurerorder=-1):
        return self._insert_adventurer(path, album, commit, adventurerorder)

    def _insert_adventurer(self, path, album, commit=True, adventurerorder=-1):
        try:
            data = cw.data.xml2etree(path)
            e = data.find("Property")
            header = cw.header.AdventurerHeader(e, album=album)
            header.fpath = path
            return self._insert_adventurerheader(header, commit, adventurerorder)
        except Exception, ex:
            print ex

    def get_adventurers(self, album):
        if album:
            s = "SELECT * FROM adventurer WHERE album=? ORDER BY name"
            album = 1
        else:
            s = """
            SELECT
                *
            FROM
                adventurer
                LEFT OUTER JOIN
                    adventurerorder
                ON
                    adventurer.fpath = adventurerorder.fpath
            WHERE
                lost=0 AND album=?
            ORDER BY
                numorder,
                name
            """
            album = 0
        self.cur.execute(s, (album,))
        headers = []
        for order, rec in enumerate(self.cur):
            header = cw.header.AdventurerHeader(dbrec=rec)
            header.order = order
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    def get_standbys(self):
        return self.get_adventurers(False)

    def get_standbynames(self, maxcount=0):
        if 0 < maxcount:
            s = "SELECT name FROM adventurer WHERE lost=0 AND album=? ORDER BY name"
            self.cur.execute(s, (0,))
        else:
            s = "SELECT name FROM adventurer WHERE lost=0 AND album=? ORDER BY name LIMIT=?"
            self.cur.execute(s, (0, maxcount,))
        names = []
        for rec in self.cur:
            names.append(rec[0])
        return names

    def get_album(self):
        return self.get_adventurers(True)

    @synclock(_lock)
    def insert_partyheader(self, header, commit=True):
        return self._insert_partyheader(header, commit)

    def _insert_partyheader(self, header, commit=True):
        """データベースにパーティを登録する。"""
        s = """
        INSERT OR REPLACE INTO party VALUES(
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """
        fpath = os.path.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        self.cur.execute(s, (
            fpath,
            header.name,
            header.money,
            "\n".join(header.members),
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_party(self, path, commit=True):
        return self._insert_party(path, commit)

    def _insert_party(self, path, commit=True):
        try:
            # 新フォーマット(ディレクトリ)
            data = cw.data.xml2etree(path)
            e = data.find("Property")
            header = cw.header.PartyHeader(e)
            header.fpath = path
            return self._insert_partyheader(header, commit)
        except Exception, ex:
            print ex

    def get_parties(self):
        s = "SELECT * FROM party ORDER BY name"
        self.cur.execute(s)
        headers = []
        for rec in self.cur:
            header = cw.header.PartyHeader(dbrec=rec)
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    @synclock(_lock)
    def commit(self):
        self.con.commit()

    @synclock(_lock)
    def close(self):
        self.con.close()
