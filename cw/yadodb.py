#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import threading
import time

import cw
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

            reqcommit = False

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

            # cardimageテーブルが存在しない場合は作成する(0.12.3以前との互換性維持)
            cur = self.con.execute("PRAGMA table_info('cardimage')")
            res = cur.fetchall()
            if not res:
                s = """
                    CREATE TABLE cardimage (
                        fpath TEXT,
                        numorder INTEGER,
                        imgpath TEXT,
                        postype TEXT,
                        PRIMARY KEY (fpath, numorder)
                    )
                """
                self.cur.execute(s)

            else:
                # postype列が存在しない場合は作成する(～1.1との互換性維持)
                cur = self.con.execute("PRAGMA table_info('cardimage')")
                res = cur.fetchall()
                haspostype = False
                for rec in res:
                    if rec[1] == "postype":
                        haspostype = True
                        break
                if not haspostype:
                    # 値はNone(Default扱い)
                    self.cur.execute("ALTER TABLE cardimage ADD COLUMN postype TEXT")
                    reqcommit = True

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

                # adventurerorderテーブルが存在しない場合は作成する(0.12.3以前との互換性維持)
                cur = self.con.execute("PRAGMA table_info('adventurerimage')")
                res = cur.fetchall()
                if not res:
                    s = """
                        CREATE TABLE adventurerimage (
                            fpath TEXT,
                            numorder INTEGER,
                            imgpath TEXT,
                            postype TEXT,
                            PRIMARY KEY (fpath, numorder)
                        )
                    """
                    self.cur.execute(s)

                else:
                    # postype列が存在しない場合は作成する(～1.1との互換性維持)
                    cur = self.con.execute("PRAGMA table_info('adventurerimage')")
                    res = cur.fetchall()
                    haspostype = False
                    for rec in res:
                        if rec[1] == "postype":
                            haspostype = True
                            break
                    if not haspostype:
                        # 値はNone(Default扱い)
                        self.cur.execute("ALTER TABLE adventurerimage ADD COLUMN postype TEXT")
                        reqcommit = True

                # partyorderテーブルが存在しない場合は作成する(旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('partyorder')")
                res = cur.fetchall()
                if not res:
                    s = """
                        CREATE TABLE partyorder (
                            fpath TEXT,
                            numorder INTEGER,
                            PRIMARY KEY (fpath)
                        )
                    """
                    self.cur.execute(s)

            # moved列,scenariocard列,versionhint列,star列が存在しない
            # 場合は作成する(旧バージョンとの互換性維持)
            cur = self.con.execute("PRAGMA table_info('card')")
            res = cur.fetchall()
            hasmoved = False
            hasscenariocard = False
            hasversionhint = False
            haswsnversion = False
            hasstar = False
            for rec in res:
                if rec[1] == "moved":
                    hasmoved = True
                elif rec[1] == "scenariocard":
                    hasscenariocard = True
                elif rec[1] == "versionhint":
                    hasversionhint = True
                elif rec[1] == "wsnversion":
                    haswsnversion = True
                elif rec[1] == "star":
                    hasstar = True
                if all((hasmoved, hasscenariocard, hasversionhint, haswsnversion, hasstar)):
                    break

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
            if not hasstar:
                self.cur.execute("ALTER TABLE card ADD COLUMN star INTEGER")
                self.cur.execute("UPDATE card SET star=?", (0,))
                reqcommit = True
            if not haswsnversion:
                # 値はNoneのままにしておく
                self.cur.execute("ALTER TABLE card ADD COLUMN wsnversion TEXT")
                reqcommit = True

            if self.mode == YADO:
                # desc, versionhint, wsnversion列が存在しない場合は作成する
                # (旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('adventurer')")
                res = cur.fetchall()
                hasdesc = False
                hasversionhint = False
                haswsnversion = False
                for rec in res:
                    if rec[1] == "desc":
                        hasdesc = True
                    elif rec[1] == "versionhint":
                        hasversionhint = True
                    elif rec[1] == "wsnversion":
                        haswsnversion = True
                    if all((hasdesc, hasversionhint, haswsnversion)):
                        break

                if not hasdesc:
                    self.cur.execute("ALTER TABLE adventurer ADD COLUMN desc TEXT")
                    self.cur.execute("UPDATE adventurer SET mtime=?", (0,)) # 強制更新
                    reqcommit = True

                if not hasversionhint:
                    self.cur.execute("ALTER TABLE adventurer ADD COLUMN versionhint TEXT")
                    self.cur.execute("UPDATE adventurer SET versionhint=?", ("",))
                    reqcommit = True

                if not haswsnversion:
                    # 値はNoneのままにしておく
                    self.cur.execute("ALTER TABLE adventurer ADD COLUMN wsnversion TEXT")
                    reqcommit = True

            if self.mode == YADO:
                # partyrecordテーブルが存在しない場合は作成する(旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('partyrecord')")
                res = cur.fetchall()
                if not res:
                    s = """
                        CREATE TABLE partyrecord (
                            fpath TEXT,
                            name TEXT,
                            money INTEGER,
                            members TEXT,
                            membernames TEXT,
                            backpack TEXT,
                            ctime INTEGER,
                            mtime INTEGER,
                            PRIMARY KEY (fpath)
                        )
                    """
                    self.cur.execute(s)
                    reqcommit = True

            if self.mode == YADO:
                # membernames列が存在しない場合は作成する
                # (旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('partyrecord')")
                res = cur.fetchall()
                hasmembernames = False
                for rec in res:
                    if rec[1] == "membernames":
                        hasmembernames = True
                        break

                if not hasmembernames:
                    self.cur.execute("ALTER TABLE partyrecord ADD COLUMN membernames TEXT")
                    self.cur.execute("UPDATE partyrecord SET membernames=?", ("",))
                    reqcommit = True

            if self.mode == YADO:
                # savedjpdcimageテーブルが存在しない場合は作成する
                # (旧バージョンとの互換性維持)
                cur = self.con.execute("PRAGMA table_info('savedjpdcimage')")
                res = cur.fetchall()
                if not res:
                    s = """
                        CREATE TABLE savedjpdcimage (
                            fpath TEXT,
                            scenarioname TEXT,
                            scenarioauthor TEXT,
                            dpath TEXT,
                            fpaths TEXT,
                            ctime INTEGER,
                            mtime INTEGER,
                            PRIMARY KEY (fpath)
                        )
                    """
                    self.cur.execute(s)

            if reqcommit:
                self.con.commit()

        else:
            dname = os.path.dirname(self.name)
            if not os.path.isdir(dname):
                os.makedirs(dname)
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
                    wsnversion TEXT,
                    star INTEGER,
                    ctime INTEGER,
                    mtime INTEGER,
                    PRIMARY KEY (fpath)
                )
            """
            self.cur.execute(s)

            # カードイメージ(複数あるもの)
            s = """
                CREATE TABLE cardimage (
                    fpath TEXT,
                    numorder INTEGER,
                    imgpath TEXT,
                    postype TEXT,
                    PRIMARY KEY (fpath, numorder)
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
                        desc TEXT,
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
                        wsnversion TEXT,
                        ctime INTEGER,
                        mtime INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

                # 冒険者のイメージ(複数あるもの)
                s = """
                    CREATE TABLE adventurerimage (
                        fpath TEXT,
                        numorder INTEGER,
                        imgpath TEXT,
                        postype TEXT,
                        PRIMARY KEY (fpath, numorder)
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

                # パーティの並び順
                s = """
                    CREATE TABLE partyorder (
                        fpath TEXT,
                        numorder INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

                # パーティ記録
                s = """
                    CREATE TABLE partyrecord (
                        fpath TEXT,
                        name TEXT,
                        money INTEGER,
                        members TEXT,
                        membernames TEXT,
                        backpack TEXT,
                        ctime INTEGER,
                        mtime INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

                # 保存されたJPDCイメージ
                s = """
                    CREATE TABLE savedjpdcimage (
                        fpath TEXT,
                        scenarioname TEXT,
                        scenarioauthor TEXT,
                        dpath TEXT,
                        fpaths TEXT,
                        ctime INTEGER,
                        mtime INTEGER,
                        PRIMARY KEY (fpath)
                    )
                """
                self.cur.execute(s)

    @synclock(_lock)
    def update(self, cards=True, adventurers=True, parties=True, cardorder={}.copy(),
               adventurerorder={}.copy(), partyorder={}.copy(), partyrecord=True, savedjpdcimage=True):
        """データベースを更新する。"""
        def walk(dpath, headertable, xmlname, insert, insertheader, *args):
            dname = cw.util.join_paths(self.ypath, dpath)
            if os.path.isdir(dname):
                for fname in os.listdir(dname):
                    if xmlname:
                        path = cw.util.join_paths(dpath, fname, xmlname)
                        if not os.path.isfile(cw.util.join_paths(self.ypath, path)):
                            continue
                    else:
                        if not fname.lower().endswith(".xml"):
                            continue
                        path = cw.util.join_paths(dpath, fname)
                    if not path in dbpaths:
                        if isinstance(headertable, dict) and path in headertable:
                            insertheader(headertable[path], *args)
                        else:
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
                        if isinstance(cards, dict) and path in cards:
                            self._insert_cardheader(cards[path], False)
                        else:
                            self._insert_card(path, False)
            walk("SkillCard", cards, "", self._insert_card, self._insert_cardheader, False)
            walk("ItemCard", cards, "", self._insert_card, self._insert_cardheader, False)
            walk("BeastCard", cards, "", self._insert_card, self._insert_cardheader, False)
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

        if self.mode == YADO and (isinstance(adventurers, dict) or adventurers):
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
                        if isinstance(adventurers, dict) and path in adventurers:
                            self._insert_adventurerheader(adventurers[path], bool(t[2]), False)
                        else:
                            self._insert_adventurer(path, bool(t[2]), False)
            walk("Adventurer", adventurers, "", self._insert_adventurer, self._insert_adventurerheader, False, False)
            walk("Album", {}, "", self._insert_adventurer, self._insert_adventurerheader, True, False)

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
                        if isinstance(parties, dict) and path in parties:
                            self._insert_partyheader(parties[path], False)
                        else:
                            self._insert_party(path, False)
            for dpath in os.listdir(cw.util.join_paths(self.ypath, "Party")):
                walk(cw.util.join_paths("Party", dpath), parties, "", self._insert_party, self._insert_partyheader, False)

            if partyorder:
                # 冒険者の並び順を登録する
                s = "DELETE FROM partyorder"
                self.cur.execute(s)
                for fpath, orderc in partyorder.items():
                    s = """
                        INSERT OR REPLACE INTO partyorder VALUES(
                            ?,
                            ?
                        )
                    """
                    self.cur.execute(s, (
                        fpath,
                        orderc,
                    ))

        if self.mode == YADO and partyrecord:
            s = "SELECT fpath, mtime FROM partyrecord"
            self.cur.execute(s)
            data = self.cur.fetchall()
            dbpaths = set()
            for t in data:
                path = cw.util.join_paths(self.ypath, t[0])
                if not os.path.isfile(path):
                    self._delete_partyrecord(t[0], False)
                else:
                    dbpaths.add(t[0])
                    if os.path.getmtime(path) > t[1]:
                        # 情報を更新
                        if isinstance(partyrecord, dict) and t[0] in partyrecord:
                            self._insert_partyrecordheader(partyrecord[t[0]], False)
                        else:
                            self._insert_partyrecord(path, False)
            walk("PartyRecord", partyrecord, "", self._insert_partyrecord, self._insert_partyrecordheader, False)

        if self.mode == YADO and savedjpdcimage:
            s = "SELECT fpath, mtime FROM savedjpdcimage"
            self.cur.execute(s)
            data = self.cur.fetchall()
            dbpaths = set()
            for t in data:
                path = cw.util.join_paths(self.ypath, t[0])
                if not os.path.isfile(path):
                    self._delete_savedjpdcimage(t[0], False)
                else:
                    dbpaths.add(t[0])
                    if os.path.getmtime(path) > t[1]:
                        # 情報を更新
                        if isinstance(savedjpdcimage, dict) and t[0] in savedjpdcimage:
                            self._insert_savedjpdcimageheader(savedjpdcimage[t[0]], False)
                        else:
                            self._insert_savedjpdcimage(path, False)
            walk("SavedJPDCImage", savedjpdcimage, u"SavedJPDCImage.xml", self._insert_savedjpdcimage, self._insert_savedjpdcimageheader, False)

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
            s = "VACUUM partyrecord"
            self.cur.execute(s)
            s = "VACUUM savedjpdcimage"
            self.cur.execute(s)

        if commit:
            self.con.commit()

    def _delete_card(self, path, commit=True):
        s = "DELETE FROM card WHERE fpath=?"
        self.cur.execute(s, (path,))
        s = "DELETE FROM cardimage WHERE fpath=?"
        self.cur.execute(s, (path,))
        s = "DELETE FROM cardorder WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    def _delete_adventurer(self, path, commit=True):
        s = "DELETE FROM adventurer WHERE fpath=?"
        self.cur.execute(s, (path,))
        s = "DELETE FROM adventurerimage WHERE fpath=?"
        self.cur.execute(s, (path,))
        s = "DELETE FROM adventurerorder WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    def _delete_party(self, path, commit=True):
        s = "DELETE FROM party WHERE fpath=?"
        self.cur.execute(s, (path,))
        s = "DELETE FROM partyorder WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    def _delete_partyrecord(self, path, commit=True):
        s = "DELETE FROM partyrecord WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    def _delete_savedjpdcimage(self, path, commit=True):
        s = "DELETE FROM savedjpdcimage WHERE fpath=?"
        self.cur.execute(s, (path,))
        if commit:
            self.con.commit()

    @synclock(_lock)
    def delete_savedjpdcimage(self, path, commit=True):
        self._delete_savedjpdcimage(path, commit)

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
            wsnversion,
            star,
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
            ?,
            ?,
            ?
        )
        """
        fpath = cw.util.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        if len(header.imgpaths) == 1 and header.imgpaths[0].postype == "Default":
            imgpath = header.imgpaths[0].path
        elif not header.imgpaths:
            imgpath = ""
        else:
            imgpath = None
        self.cur.execute(s, (
            fpath,
            header.type,
            header.id,
            header.name,
            imgpath,
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
            cw.cwpy.sct.to_basehint(header.versionhint),
            header.wsnversion,
            header.star,
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
        if header.imgpaths and not (len(header.imgpaths) == 1 and header.imgpaths[0].postype == "Default"):
            s = """
            DELETE FROM cardimage WHERE fpath=?
            """
            self.cur.execute(s, (fpath,))
            for i, imgpath in enumerate(header.imgpaths):
                s = """
                INSERT OR REPLACE INTO cardimage (
                    fpath,
                    numorder,
                    imgpath,
                    postype
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?
                )
                """
                if imgpath.postype == "Default":
                    postype = None
                else:
                    postype = imgpath.postype
                self.cur.execute(s, (fpath, i, imgpath.path, postype,))

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
        except Exception:
            cw.util.print_ex()

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
                wsnversion,
                star,
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

        s = """
            SELECT
                imgpath,
                postype
            FROM
                cardimage
            WHERE
                fpath = ?
            ORDER BY
                numorder
        """

        recs = self.cur.fetchall()
        for order, rec in enumerate(recs):
            if rec["imgpath"] is None:
                imgdbrec = self.cur.execute(s, (rec["fpath"],))
            else:
                imgdbrec = None
            header = cw.header.CardHeader(dbrec=rec, imgdbrec=imgdbrec, dbowner=owner)
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
            desc,
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
            wsnversion,
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
            ?
        )
        """
        fpath = cw.util.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        if len(header.imgpaths) == 1 and header.imgpaths[0].postype == "Default":
            imgpath = header.imgpaths[0].path
        elif not header.imgpaths:
            imgpath = ""
        else:
            imgpath = None
        if header.album:
            album = 1
        else:
            album= 0
        self.cur.execute(s, (
            fpath,
            header.level,
            header.name,
            header.desc,
            imgpath,
            album,
            header.lost,
            header.sex,
            header.age,
            header.ep,
            header.leavenoalbum,
            header.gene.get_str(),
            "\n".join(header.history),
            header.race,
            cw.cwpy.sct.to_basehint(header.versionhint),
            header.wsnversion,
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
        if header.imgpaths and not (len(header.imgpaths) == 1 and header.imgpaths[0].postype == "Default"):
            s = """
            DELETE FROM adventurerimage WHERE fpath=?
            """
            self.cur.execute(s, (fpath,))
            for i, imgpath in enumerate(header.imgpaths):
                s = """
                INSERT OR REPLACE INTO adventurerimage (
                    fpath,
                    numorder,
                    imgpath,
                    postype
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?
                )
                """
                if imgpath.postype == "Default":
                    postype = None
                else:
                    postype = imgpath.postype
                self.cur.execute(s, (fpath, i, imgpath.path, postype))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_adventurer(self, path, album, commit=True, adventurerorder=-1):
        return self._insert_adventurer(path, album, commit, adventurerorder)

    def _insert_adventurer(self, path, album, commit=True, adventurerorder=-1):
        try:
            header = cw.header.AdventurerHeader(fpath=path, album=album)
            header.fpath = path
            return self._insert_adventurerheader(header, commit, adventurerorder)
        except Exception:
            cw.util.print_ex()

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

        s = """
            SELECT
                imgpath,
                postype
            FROM
                adventurerimage
            WHERE
                fpath = ?
            ORDER BY
                numorder
        """

        recs = self.cur.fetchall()
        for order, rec in enumerate(recs):
            if rec["imgpath"] is None:
                imgdbrec = self.cur.execute(s, (rec["fpath"],))
            else:
                imgdbrec = None
            header = cw.header.AdventurerHeader(dbrec=rec, imgdbrec=imgdbrec)
            header.order = order
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    def get_standbys(self):
        return self.get_adventurers(False)

    def get_standbynames(self):
        s = "SELECT name FROM adventurer WHERE lost=0 AND album=? ORDER BY name"
        self.cur.execute(s, (0,))
        names = []
        for rec in self.cur:
            names.append(rec[0])
        return names

    def get_album(self):
        return self.get_adventurers(True)

    @synclock(_lock)
    def insert_partyheader(self, header, commit=True, partyorder=-1):
        return self._insert_partyheader(header, commit, partyorder)

    def _insert_partyheader(self, header, commit=True, partyorder=-1):
        """データベースにパーティを登録する。"""
        s = """
        INSERT OR REPLACE INTO party(
            fpath,
            name,
            money,
            members,
            ctime,
            mtime
        ) VALUES(
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """
        fpath = cw.util.relpath(header.fpath, self.ypath)
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

        if -1 < partyorder:
            s = """
            INSERT OR REPLACE INTO partyorder VALUES(
                ?,
                ?
            )
            """
            self.cur.execute(s, (
                fpath,
                partyorder,
            ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_party(self, path, commit=True, partyorder=-1):
        return self._insert_party(path, commit, partyorder)

    def _insert_party(self, path, commit=True, partyorder=-1):
        try:
            # 新フォーマット(ディレクトリ)
            data = cw.data.xml2etree(path)
            e = data.find("Property")
            header = cw.header.PartyHeader(e)
            header.fpath = path
            return self._insert_partyheader(header, commit, partyorder)
        except Exception:
            cw.util.print_ex()

    def get_parties(self):
        s = """
        SELECT
            *
        FROM
            party
            LEFT OUTER JOIN
                partyorder
            ON
                party.fpath = partyorder.fpath
        ORDER BY
            name
        """
        self.cur.execute(s)
        headers = []
        for rec in self.cur:
            header = cw.header.PartyHeader(dbrec=rec)
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    @synclock(_lock)
    def insert_partyrecordheader(self, header, commit=True):
        return self._insert_partyrecordheader(header, commit)

    def _insert_partyrecordheader(self, header, commit=True):
        """データベースにパーティ記録を登録する。"""
        s = """
        INSERT OR REPLACE INTO partyrecord(
            fpath,
            name,
            money,
            members,
            membernames,
            backpack,
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
            ?
        )
        """
        fpath = cw.util.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        self.cur.execute(s, (
            fpath,
            header.name,
            header.money,
            "\n".join(header.members),
            "\n".join(header.membernames),
            "\n".join(header.backpack),
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_partyrecord(self, path, commit=True):
        return self._insert_partyrecord(path, commit)

    def _insert_partyrecord(self, path, commit=True):
        try:
            header = cw.header.PartyRecordHeader(fpath=path)
            return self._insert_partyrecordheader(header, commit)
        except Exception:
            cw.util.print_ex()

    def get_partyrecord(self):
        s = "SELECT * FROM partyrecord ORDER BY name"
        self.cur.execute(s)
        headers = []
        for rec in self.cur:
            header = cw.header.PartyRecordHeader(dbrec=rec)
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            headers.append(header)
        return headers

    @synclock(_lock)
    def insert_savedjpdcimageheader(self, header, commit=True):
        return self._insert_savedjpdcimageheader(header, commit)

    def _insert_savedjpdcimageheader(self, header, commit=True):
        """データベースに保存されたJPDCイメージの情報を登録する。"""
        s = """
        INSERT OR REPLACE INTO savedjpdcimage(
            fpath,
            scenarioname,
            scenarioauthor,
            dpath,
            fpaths,
            ctime,
            mtime
        ) VALUES(
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """
        fpath = cw.util.relpath(header.fpath, self.ypath)
        fpath = cw.util.join_paths(fpath)
        ctime = time.time()
        mtime = os.path.getmtime(header.fpath)
        self.cur.execute(s, (
            fpath,
            header.scenarioname,
            header.scenarioauthor,
            header.dpath,
            "\n".join(header.fpaths),
            ctime,
            mtime,
        ))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_savedjpdcimage(self, path, commit=True):
        return self._insert_savedjpdcimage(path, commit)

    def _insert_savedjpdcimage(self, path, commit=True):
        try:
            header = cw.header.SavedJPDCImageHeader(fpath=path)
            return self._insert_savedjpdcimageheader(header, commit)
        except Exception:
            cw.util.print_ex()

    def get_savedjpdcimage(self):
        s = "SELECT * FROM savedjpdcimage"
        self.cur.execute(s)
        d = {}
        for rec in self.cur:
            header = cw.header.SavedJPDCImageHeader(dbrec=rec)
            header.fpath = cw.util.join_paths(self.ypath, header.fpath)
            d[(header.scenarioname, header.scenarioauthor)] = header
        return d

    @synclock(_lock)
    def commit(self):
        self.con.commit()

    @synclock(_lock)
    def close(self):
        self.con.close()
