#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import io
import sqlite3
import threading
import subprocess

import cw
from cw.util import synclock

from typing import Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Union

_lock = threading.Lock()

TYPE_WSN = 0
TYPE_CLASSIC = 1

DATA_TITLE = 0
DATA_DESC = 1
DATA_AUTHOR = 2
DATA_LEVEL = 3
DATA_FNAME = 4


class ScenariodbUpdatingThread(threading.Thread):
    _finished = False

    def __init__(self, setting: "cw.setting.Setting", vacuum: bool = False, dpath: str = "Scenario",
                 skintype: str = "") -> None:
        threading.Thread.__init__(self)
        self.setting = setting
        self._vacuum = vacuum
        self._dpath = dpath
        self._skintype = skintype

    def run(self) -> None:
        type(self)._finished = False
        db = Scenariodb()
        db.update(skintype=self._skintype)
        folders = set()
        folders.add(self._dpath)
        for _skintype, folder in self.setting.folderoftype:
            if folder not in folders:
                db.update(folder, skintype=self._skintype)
                folders.add(folder)

        if self._vacuum:
            db.vacuum()

        db.close()
        type(self)._finished = True

    @staticmethod
    def is_finished() -> bool:
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
    image(見出し画像のイメージデータ),
    imgpath(見出し画像のパス),
    wsnversion(WSN形式の場合はそのバージョン)
    """
    @synclock(_lock)
    def __init__(self) -> None:
        self.name = "Scenario.db"

        if os.path.isfile(self.name):
            self.con = sqlite3.connect(self.name, timeout=30000)
            self.con.row_factory = sqlite3.Row
            self.cur = self.con.cursor()
            needcommit = False

            # type, imgpath列が存在しない場合は作成する(旧バージョンとの互換性維持)
            cur = self.con.execute("PRAGMA table_info('scenariodb')")
            res = cur.fetchall()
            hastype = False
            hasimgpath = False
            haswsnversion = False
            for rec in res:
                if rec[1] == "type":
                    hastype = True
                elif rec[1] == "imgpath":
                    hasimgpath = True
                elif rec[1] == "wsnversion":
                    haswsnversion = True
                if all((hastype, hasimgpath, haswsnversion)):
                    break
            if not hastype:
                self.cur.execute("ALTER TABLE scenariodb ADD COLUMN type INTEGER")
                self.cur.execute("UPDATE scenariodb SET type=?", (TYPE_WSN,))
                needcommit = True
            if not hasimgpath:
                # 値はNoneのままにしておく
                self.cur.execute("ALTER TABLE scenariodb ADD COLUMN imgpath TEXT")
                needcommit = True
            if not haswsnversion:
                # 値はNoneのままにしておく
                self.cur.execute("ALTER TABLE scenariodb ADD COLUMN wsnversion TEXT")
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

            # FIXME: SQLite3ではDROP COLUMNは使用できないので放置しておく
            # # imgpathが存在する場合は削除する(0.12.4αで一旦必要になったものの不要化)
            # cur = self.con.execute("PRAGMA table_info('scenariodb')")
            # res = cur.fetchall()
            # hastype = False
            # for rec in res:
            #     if rec[1] == "imgpath":
            #         hastype = True
            #         break
            #   if hastype:
            #     self.cur.execute("ALTER TABLE scenariodb DROP COLUMN imgpath")
            #     needcommit = True

            # scenarioimageテーブルが存在しない場合は作成する(0.12.3以前との互換性維持)
            cur = self.con.execute("PRAGMA table_info('scenarioimage')")
            res = cur.fetchall()
            if not res:
                s = """
                    CREATE TABLE scenarioimage (
                        dpath TEXT,
                        fname TEXT,
                        numorder INTEGER,
                        scale INTEGER,
                        image BLOB,
                        imgpath TEXT,
                        postype TEXT,
                        PRIMARY KEY (dpath, fname, numorder, scale)
                    )
                """
                self.cur.execute(s)

            else:
                # postype, imgpath, scale列が存在しない場合は作成する(～1.1との互換性維持)
                cur = self.con.execute("PRAGMA table_info('scenarioimage')")
                res = cur.fetchall()
                haspostype = False
                hasimgpath = False
                hasscale = False
                for rec in res:
                    if rec[1] == "postype":
                        haspostype = True
                    elif rec[1] == "imgpath":
                        hasimgpath = True
                    elif rec[1] == "scale":
                        hasscale = True
                    if all((haspostype, hasimgpath, hasscale)):
                        break
                if not haspostype:
                    # 値はNone(Default扱い)
                    self.cur.execute("ALTER TABLE scenarioimage ADD COLUMN postype TEXT")
                    needcommit = True
                if not hasimgpath:
                    # 値はNoneのままにしておく
                    self.cur.execute("ALTER TABLE scenarioimage ADD COLUMN imgpath TEXT")
                    needcommit = True
                if not hasscale:
                    # SQLite3では主キーの変更ができないので作り直す
                    s = """
                        CREATE TABLE scenarioimage_temp (
                            dpath TEXT,
                            fname TEXT,
                            numorder INTEGER,
                            scale INTEGER,
                            image BLOB,
                            imgpath TEXT,
                            postype TEXT,
                            PRIMARY KEY (dpath, fname, numorder, scale)
                        )
                    """
                    self.cur.execute(s)
                    s = """
                        INSERT INTO scenarioimage_temp (
                            dpath,
                            fname,
                            numorder,
                            scale,
                            image,
                            imgpath,
                            postype
                        )
                        SELECT
                            dpath,
                            fname,
                            numorder,
                            1,
                            image,
                            imgpath,
                            postype
                        FROM
                            scenarioimage
                    """
                    self.cur.execute(s)
                    s = "DROP TABLE scenarioimage"
                    self.cur.execute(s)
                    s = "ALTER TABLE scenarioimage_temp RENAME TO scenarioimage"
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
                   imgpath TEXT, wsnversion TEXT,
                   PRIMARY KEY (dpath, fname))"""

            self.cur.execute(s)
            self.cur.execute("CREATE INDEX scenariodb_index1 ON scenariodb(dpath)")

            s = """
                CREATE TABLE scenarioimage (
                    dpath TEXT,
                    fname TEXT,
                    numorder INTEGER,
                    scale INTEGER,
                    image BLOB,
                    imgpath TEXT,
                    postype TEXT,
                    PRIMARY KEY (dpath, fname, numorder)
                )
            """
            self.cur.execute(s)

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
    def update(self, dpath: str = "Scenario", skintype: str = "", commit: bool = True, update: bool = True) -> None:
        """データベースを更新する。"""
        if not update:
            return

        if skintype:
            s = "SELECT A.dpath, A.fname, mtime, B.skintype FROM scenariodb A LEFT JOIN scenariotype B" + \
                " ON A.dpath=B.dpath AND A.fname=B.fname" + \
                " WHERE A.dpath=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (cw.util.get_linktarget(dpath), skintype,))
        else:
            s = "SELECT dpath, fname, mtime FROM scenariodb WHERE dpath=?"
            self.cur.execute(s, (cw.util.get_linktarget(dpath),))
        data = self.cur.fetchall()
        dbpaths = []

        def update_path(t: sqlite3.Row, spath: str, path: str) -> None:
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

        if commit:
            self.con.commit()
        dbpaths_s = set(dbpaths)

        for path in get_scenariopaths(dpath):
            if path not in dbpaths_s:
                self._insert_scenario(path, False, skintype=skintype)

        if commit:
            self.con.commit()

    def vacuum(self, commit: bool = True) -> None:
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
                s = "DELETE FROM scenarioimage WHERE dpath=?"
                self.cur.execute(s, (dpath,))
                s = "DELETE FROM scenariotype WHERE dpath=?"
                self.cur.execute(s, (dpath,))

        # データ量によっては処理に秒単位で時間がかかる上、
        # 再利用可能な領域が減ってパフォーマンスが落ちるため実施しない
        # s = "VACUUM scenariodb, scenariotype"
        # self.cur.execute(s)
        # s = "VACUUM scenariotype"
        # self.cur.execute(s)

        if commit:
            self.con.commit()

    def delete(self, path: str, commit: bool = True) -> None:
        path = path.replace("\\", "/")
        dpath, fname = os.path.split(path)
        s = "DELETE FROM scenariodb WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))
        s = "DELETE FROM scenarioimage WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))
        s = "DELETE FROM scenariotype WHERE dpath=? AND fname=?"
        self.cur.execute(s, (dpath, fname,))

        if commit:
            self.con.commit()

    def delete_all(self, commit: bool = True) -> None:
        s = "DELETE FROM scenariodb"
        self.cur.execute(s)
        s = "DELETE FROM scenarioimage"
        self.cur.execute(s)
        s = "DELETE FROM scenariotype"
        self.cur.execute(s)

        if commit:
            self.con.commit()

    def insert(self, t: Tuple[str, int, str, str, str, str, str, int, int, str, int, int, str, float, float, str,
                              Optional[bytes], Optional[str]],
               images: List[Tuple[Optional[bytes], "cw.image.ImageInfo", int]], commit: bool = True,
               skintype: str = "") -> None:
        s = """INSERT OR REPLACE INTO scenariodb(
                    dpath, type, fname, name, author, desc, skintype,
                    levelmin, levelmax, coupons, couponsnum,
                    startid, tags, ctime, mtime, wsnversion, image, imgpath
               ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
               )"""
        self.cur.execute(s, t)
        if skintype:
            s = """INSERT OR REPLACE INTO scenariotype
                   VALUES(?, ?, ?)"""
            self.cur.execute(s, (t[0], t[2], skintype,))

        if images:
            s = """
            DELETE FROM scenarioimage WHERE dpath=? AND fname=?
            """
            self.cur.execute(s, (t[0], t[2],))
            for i, image in enumerate(images):
                s = """
                INSERT OR REPLACE INTO scenarioimage (
                    dpath,
                    fname,
                    numorder,
                    scale,
                    image,
                    imgpath,
                    postype
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """
                if image[1].postype == "Default":
                    postype = None
                else:
                    postype = image[1].postype
                self.cur.execute(s, (t[0], t[2], i, image[2], image[0], image[1].path, postype,))

        if commit:
            self.con.commit()

    @synclock(_lock)
    def insert_scenario(self, path: str, commit: bool = True, skintype: str = "") -> None:
        """データベースにシナリオを登録する。"""
        self._insert_scenario(path, commit, skintype=skintype)

    def _insert_scenario(self, path: str, commit: bool = True, skintype: str = "") -> Optional[bool]:
        t, images = read_summary(path)

        if t:
            self.insert(t, images, commit, skintype=skintype)
            return True
        else:
            return False

    def create_header(self, data: Optional[sqlite3.Row], skintype: str = "",
                      update: bool = True) -> Optional["cw.header.ScenarioHeader"]:
        """
        データベース内のシナリオ情報からヘッダ部分を返す。
        情報が古くなっている場合は更新する。
        """
        if not data:
            return None

        if data["image"] is None:
            s = """
                SELECT
                    scale,
                    image,
                    imgpath,
                    postype,
                    numorder
                FROM
                    scenarioimage
                WHERE
                    dpath=? AND fname=?
                ORDER BY
                    numorder
            """
            imgdbrec: Optional[sqlite3.Cursor] = self.cur.execute(s, (data["dpath"], data["fname"],))
        else:
            imgdbrec = None

        header = cw.header.ScenarioHeader(data, imgdbrec=imgdbrec)
        if not update:
            return header

        path = header.get_fpath()
        ltarg = cw.util.get_linktarget(path)

        if not os.path.isfile(ltarg):
            def func(spath: str, header: cw.header.ScenarioHeader) -> Optional[cw.header.ScenarioHeader]:
                # クラシックなシナリオ
                if os.path.getmtime(spath) > header.mtime:
                    cs, images = read_summary(path)
                    if cs:
                        self.insert(cs, images, True, skintype=skintype)
                        # 更新後の情報を取得
                        return self._search_path(path, skintype=skintype)
                    else:
                        return None
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
                return self._search_path(path, skintype=skintype)
            else:
                return None

        return header

    def create_headers(self, data: List[sqlite3.Row], skintype: str = "",
                       update: bool = True) -> Tuple[List["cw.header.ScenarioHeader"], Set[str]]:
        """
        データベース内のシナリオ群のヘッダを返す。
        その際、情報が古くなっている場合は更新する。
        """
        headers = []
        names = set()

        for t in data:
            header = self.create_header(t, skintype=skintype, update=update)

            if header:
                headers.append(header)
                names.add(header.fname)

        return headers, names

    def sort_headers(self, headers: List["cw.header.ScenarioHeader"]) -> List["cw.header.ScenarioHeader"]:
        cw.util.sort_by_attr(headers, "levelmin", "levelmax", "name", "author", "fname", "mtime_reversed")
        return headers

    @synclock(_lock)
    def search_path(self, path: str, skintype: str = "") -> Optional["cw.header.ScenarioHeader"]:
        return self._search_path(path, skintype=skintype)

    def _search_path(self, path: str, skintype: str = "") -> Optional["cw.header.ScenarioHeader"]:
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

    FETCH_SQL = "SELECT" + \
                "     A.dpath," + \
                "     A.type," + \
                "     A.fname," + \
                "     A.name," + \
                "     A.author," + \
                "     A.desc," + \
                "     A.skintype," + \
                "     A.levelmin," + \
                "     A.levelmax," + \
                "     A.coupons," + \
                "     A.couponsnum," + \
                "     A.startid," + \
                "     A.tags," + \
                "     A.ctime," + \
                "     A.mtime," + \
                "     A.image," + \
                "     A.imgpath," + \
                "     A.wsnversion"

    def _fetch(self, dpath: str, fname: str, skintype: str) -> None:
        if skintype:
            s = Scenariodb.FETCH_SQL + \
                " FROM scenariodb A LEFT JOIN scenariotype B" + \
                " ON A.dpath=B.dpath AND A.fname=B.fname" + \
                " WHERE A.dpath=? AND A.fname=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (dpath, fname, skintype,))
        else:
            s = Scenariodb.FETCH_SQL + \
                " FROM scenariodb A WHERE dpath=? AND fname=?"
            self.cur.execute(s, (dpath, fname,))

    def _fetch_from_name(self, name: str, author: str, skintype: str) -> None:
        if skintype:
            s = Scenariodb.FETCH_SQL + \
                " FROM scenariodb A LEFT JOIN scenariotype B" + \
                " ON A.dpath=B.dpath AND A.fname=B.fname" + \
                " WHERE A.name=? AND A.author=? AND (B.skintype=? OR B.skintype IS NULL)" + \
                " ORDER BY A.mtime DESC, A.dpath, A.fname"
            self.cur.execute(s, (name, author, skintype,))
        else:
            s = Scenariodb.FETCH_SQL + \
                " FROM scenariodb A WHERE name=? AND author=?" + \
                " ORDER BY mtime DESC, dpath, fname"
            self.cur.execute(s, (name, author,))

    @synclock(_lock)
    def search_dpath(self, dpath: str, create: bool = False, skintype: str = "",
                     update: bool = True) -> List["cw.header.ScenarioHeader"]:
        dpath = cw.util.get_linktarget(dpath).replace("\\", "/")

        if skintype:
            s = "SELECT" + \
                "     A.dpath," + \
                "     A.type," + \
                "     A.fname," + \
                "     A.name," + \
                "     A.author," + \
                "     A.desc," + \
                "     A.skintype," + \
                "     A.levelmin," + \
                "     A.levelmax," + \
                "     A.coupons," + \
                "     A.couponsnum," + \
                "     A.startid," + \
                "     A.tags," + \
                "     A.ctime," + \
                "     A.mtime," + \
                "     A.image," + \
                "     A.imgpath," + \
                "     A.wsnversion" + \
                " FROM scenariodb A LEFT JOIN scenariotype B" + \
                " ON A.dpath=B.dpath AND A.fname=B.fname" + \
                " WHERE A.dpath=? AND (B.skintype=? OR B.skintype IS NULL)"
            self.cur.execute(s, (dpath, skintype,))
        else:
            s = "SELECT" + \
                "     A.dpath," + \
                "     A.type," + \
                "     A.fname," + \
                "     A.name," + \
                "     A.author," + \
                "     A.desc," + \
                "     A.skintype," + \
                "     A.levelmin," + \
                "     A.levelmax," + \
                "     A.coupons," + \
                "     A.couponsnum," + \
                "     A.startid," + \
                "     A.tags," + \
                "     A.ctime," + \
                "     A.mtime," + \
                "     A.image," + \
                "     A.imgpath," + \
                "     A.wsnversion" + \
                " FROM scenariodb A WHERE dpath=?"
            self.cur.execute(s, (dpath,))

        data = self.cur.fetchall()
        headers, names = self.create_headers(data, skintype=skintype, update=update)
        if not update:
            return self.sort_headers(headers)

        # データベースに登録されていないシナリオファイルがないかチェック
        dbpaths = set([h.get_fpath() for h in headers])

        if not os.path.exists(dpath):
            if create:
                os.makedirs(dpath)
            else:
                return []

        if not os.path.isdir(dpath):
            return []

        for name in os.listdir(str(dpath)):
            if name in names:
                continue
            path = cw.util.join_paths(dpath, name)
            ltarg = cw.util.get_linktarget(path)
            name = os.path.basename(ltarg)

            lname = name.lower()
            if path not in dbpaths and os.path.isfile(ltarg) \
                    and (lname.endswith(".wsn") or
                         lname.endswith(".zip") or
                         lname.endswith(".lzh") or
                         lname.endswith(".cab")):
                header = self._search_path(path, skintype=skintype)

                if header:
                    headers.append(header)

        return self.sort_headers(headers)

    @synclock(_lock)
    def get_header(self, path: str, skintype: str = "") -> Optional["cw.header.ScenarioHeader"]:
        dpath = os.path.dirname(path)
        fname = os.path.basename(path)
        self._fetch(dpath, fname, skintype)
        data = self.cur.fetchall()
        for t in data:
            return self.create_header(t, skintype=skintype)
        return None

    @synclock(_lock)
    def find_headers(self, ftypes: Iterable[int], value: str, skintype: str = "") -> List["cw.header.ScenarioHeader"]:
        where = []
        values: List[Union[str, int]] = []

        def encode_like(value: str) -> str:
            value2 = value.replace("\\", "\\\\")
            value2 = value2.replace("%", "\\%")
            value2 = value2.replace("_", "\\_")
            value2 = '%' + value2 + '%'
            return value2

        for ftype in ftypes:
            if ftype == DATA_TITLE:
                where.append("name LIKE ? ESCAPE '\\'")
                values.append(encode_like(value))
            elif ftype == DATA_DESC:
                where.append("desc LIKE ? ESCAPE '\\'")
                values.append(encode_like(value))
            elif ftype == DATA_AUTHOR:
                where.append("author LIKE ? ESCAPE '\\'")
                values.append(encode_like(value))
            elif ftype == DATA_LEVEL:
                try:
                    intv: Optional[int] = int(value)
                    assert intv is not None
                    where.append("levelmin <= ? AND ? <= levelmax")
                    values.append(intv)
                    values.append(intv)
                except Exception:
                    intv = None
            elif ftype == DATA_FNAME:
                where.append("A.fname LIKE ? ESCAPE '\\'")
                values.append(encode_like(value))
            else:
                raise Exception()

        where_str = "(" + ") OR (".join(where) + ")"

        if skintype:
            s = "SELECT" + \
                "     A.dpath," + \
                "     A.type," + \
                "     A.fname," + \
                "     A.name," + \
                "     A.author," + \
                "     A.desc," + \
                "     A.skintype," + \
                "     A.levelmin," + \
                "     A.levelmax," + \
                "     A.coupons," + \
                "     A.couponsnum," + \
                "     A.startid," + \
                "     A.tags," + \
                "     A.ctime," + \
                "     A.mtime," + \
                "     A.image," + \
                "     A.imgpath," + \
                "     A.wsnversion" + \
                " FROM scenariodb A LEFT JOIN scenariotype B" + \
                " ON A.dpath=B.dpath AND A.fname=B.fname" + \
                " WHERE (" + where_str + ")" + \
                "     AND (B.skintype=? OR B.skintype IS NULL)"
            values_t = tuple(values) + (skintype,)
            self.cur.execute(s, values_t)
        else:
            s = "SELECT" + \
                "     A.dpath," + \
                "     A.type," + \
                "     A.fname," + \
                "     A.name," + \
                "     A.author," + \
                "     A.desc," + \
                "     A.skintype," + \
                "     A.levelmin," + \
                "     A.levelmax," + \
                "     A.coupons," + \
                "     A.couponsnum," + \
                "     A.startid," + \
                "     A.tags," + \
                "     A.ctime," + \
                "     A.mtime," + \
                "     A.image," + \
                "     A.imgpath," + \
                "     A.wsnversion" + \
                " FROM scenariodb A WHERE (" + where_str + ")"
            values_t2 = tuple(values)
            self.cur.execute(s, values_t2)

        data = self.cur.fetchall()
        # 検索ではスキン情報は更新しない
        headers, _names = self.create_headers(data, skintype="")

        v = value.lower()

        # 情報が更新されている可能性があるため再チェック
        paths = set()
        seq = []
        for header in headers:
            if (DATA_TITLE in ftypes and v in header.name.lower()) or \
                    (DATA_AUTHOR in ftypes and v in header.author.lower()) or \
                    (DATA_DESC in ftypes and v in header.desc.lower()) or \
                    (DATA_LEVEL in ftypes and intv is not None and (header.levelmin <= intv <= header.levelmax)) or \
                    (DATA_FNAME in ftypes and v in header.fname.lower()):
                fpath = header.get_fpath()
                fpath = cw.util.get_keypath(cw.util.get_symlinktarget(fpath))
                if fpath not in paths:
                    paths.add(fpath)
                    seq.append(header)

        return self.sort_headers(seq)

    @synclock(_lock)
    def find_scenario(self, name: str, author: str, skintype: str, ignore_dpath: str = "",
                      ignore_fname: str = "") -> List["cw.header.ScenarioHeader"]:
        """
        シナリオ名と作者名からシナリオDBを検索する。
        ただしファイルパスがignore_dpathとignore_fnameにマッチするシナリオは無視する。
        """
        self._fetch_from_name(name, author, skintype)
        data = self.cur.fetchall()
        ignore_dpath = cw.util.get_keypath(ignore_dpath)
        ignore_fname = os.path.normcase(ignore_fname)
        seq = []
        paths = set()
        for t in data:
            dpath = cw.util.get_keypath(t["dpath"])
            fname = os.path.normcase(t["fname"])
            if dpath == ignore_dpath and fname == ignore_fname:
                continue
            fpath = os.path.join(dpath, fname)
            if fpath in paths:
                continue
            paths.add(fpath)
            header = self.create_header(t, skintype=skintype)
            if header:
                seq.append(header)
        return seq

    @synclock(_lock)
    def rename_dir(self, before: str, after: str) -> None:
        """
        ディレクトリ名の変更を通知し、サブディレクトリ内の情報を更新する。
        """
        orig_before = before
        orig_after = after
        before = before.replace("%", "\\%")
        before += "/%"
        after = after.replace("%", "\\%")
        after += "/%"

        for tablename in ("scenariodb", "scenarioimage", "scenariotype"):
            s = "SELECT * FROM %s WHERE dpath LIKE ? ESCAPE '\\'" % tablename
            self.cur.execute(s, (before,))
            for d in self.cur.fetchall():
                s = "UPDATE %s SET dpath=? WHERE dpath=? AND fname=?" % tablename
                ndpath = d["dpath"].replace(orig_before + "/", orig_after + "/", 1)
                self.cur.execute(s, (ndpath, d["dpath"], d["fname"],))
            s = "UPDATE %s SET dpath=? WHERE dpath=?" % tablename
            self.cur.execute(s, (orig_after, orig_before,))

    @synclock(_lock)
    def remove_dir(self, dpath: str) -> None:
        """
        ディレクトリの削除を通知する。
        """
        orig_dpath = dpath
        dpath = dpath.replace("%", "\\%")
        dpath += "/%"
        for tablename in ("scenariodb", "scenarioimage", "scenariotype"):
            s = "DELETE FROM %s WHERE dpath LIKE ? ESCAPE '\\'" % tablename
            self.cur.execute(s, (dpath,))
        s = "DELETE FROM %s WHERE dpath=?" % tablename
        self.cur.execute(s, (orig_dpath,))

    @synclock(_lock)
    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.con.close()


def find_alldirectories(dpath: str, is_cancel: Optional[Callable[[], bool]] = None) -> Set[str]:
    """dpath以下のシナリオが存在しうる
    ディレクトリの一覧を取得する。
    シナリオのディレクトリ自体は除外される。
    """
    result: Set[str] = set()
    exclude: Set[str] = set()
    _find_alldirectories(dpath, result, exclude, is_cancel)
    return result


def _find_alldirectories(dpath: str, result: Set[str], exclude: Set[str],
                         is_cancel: Optional[Callable[[], bool]]) -> None:
    dpath = cw.util.get_linktarget(dpath)
    absval = cw.util.get_keypath(cw.util.get_symlinktarget(dpath))
    if absval in exclude:
        return
    exclude.add(absval)
    result.add(dpath)
    for fname in os.listdir(dpath):
        if is_cancel and is_cancel():
            return
        dpath2 = cw.util.join_paths(dpath, fname)
        dpath2 = cw.util.get_linktarget(dpath2)
        if not os.path.isdir(dpath2) or is_scenario(dpath2):
            continue
        _find_alldirectories(dpath2, result, exclude, is_cancel)


def is_scenario(path: str) -> bool:
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
        return lpath.endswith(".wsn") or lpath.endswith(".zip") or lpath.endswith(".lzh") or lpath.endswith(".cab")


def read_summary(basepath: str) -> Tuple[Optional[Tuple[str, int, str, str, str, str, str, int, int, str, int, int,
                                                        str, float, float, str, Optional[bytes], Optional[str]]],
                                         List[Tuple[Optional[bytes], "cw.image.ImageInfo", int]]]:
    def imgbufs_to_result(summaryinfos: Tuple[str, int, str, str, str, str, str, int, int, str, int, int, str, float,
                                              float, str],
                          imgbufs: List[Tuple[Optional[bytes], cw.image.ImageInfo, int]])\
            -> Tuple[Tuple[str, int, str, str, str, str, str, int, int, str, int, int, str, float, float, str,
                           Optional[bytes], Optional[str]],
                     List[Tuple[Optional[bytes], cw.image.ImageInfo, int]]]:
        if len(imgbufs) == 0:
            imgbuf: Optional[bytes] = None
            imgpath: Optional[str] = None
        elif len(imgbufs) == 1 and imgbufs[0][1].postype == "Default" and imgbufs[0][2] == 1:
            imgbuf = imgbufs[0][0]
            imgpath = imgbufs[0][1].path
            imgbufs = []
        else:
            imgbuf = None
            imgpath = None
        return summaryinfos + (imgbuf, imgpath), imgbufs

    path = cw.util.get_linktarget(basepath)
    if os.path.isdir(path):
        f = None
        try:
            spath = cw.util.join_paths(path, "Summary.wsm")
            if os.path.isfile(spath):
                with cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True) as f:
                    r, images = read_summary_classic(basepath, spath, f)
                    f.close()
                return r, images

            spath = cw.util.join_paths(path, "Summary.xml")
            if os.path.isfile(spath):
                rootattrs: Dict[str, str] = {}
                e = cw.data.xml2element(spath, "Property", rootattrs=rootattrs)
                can_loaded_scaledimage = cw.util.str2bool(rootattrs.get("scaledimage", "False"))
                imgpaths, summaryinfos = parse_summarydata(basepath, e, TYPE_WSN, os.path.getmtime(spath), rootattrs)
                imgbufs: List[Tuple[Optional[bytes], cw.image.ImageInfo, int]] = []
                for info in imgpaths:
                    imgpath = cw.util.join_paths(path, info.path)
                    for imgpath, scale in cw.util.get_scaledimagepaths(imgpath, can_loaded_scaledimage):
                        if os.path.isfile(imgpath):
                            with open(imgpath, "rb") as f2:
                                imgbuf = f2.read()
                                f2.close()
                            imgbuf = imgbuf
                            imgbufs.append((imgbuf, info, scale))
                        elif scale == 1:
                            imgbufs.append((None, info, scale))

                return imgbufs_to_result(summaryinfos, imgbufs)
        except Exception:
            cw.util.print_ex()
            return None, []

    if path.lower().endswith(".cab"):
        try:
            summpath = cw.util.cab_hasfile(path, "Summary.wsm")
            if summpath:
                # BUG: Windows XP付属のexpandのバージョン5とより新しいバージョン6では
                #      expandの-fオプションの挙動が違う。
                #      5ではCABアーカイブ内のパスを指定しなければ失敗し、
                #      6ではパスを指定すると失敗しファイル名を指定すると成功する。
                #      ワイルドカード指定はどちらでも成功する。
                dpath = cw.util.join_paths(cw.tempdir, "Cab")
                if not os.path.isdir(dpath):
                    os.makedirs(dpath)
                s = "expand \"%s\" -f:\"%s\" \"%s\"" % (path, "*.wsm", dpath)
                ret = subprocess.call(s, shell=True)
                if ret == 0:
                    spath = cw.util.join_paths(dpath, os.path.basename(summpath))
                    if not os.path.isfile(spath):
                        spath = cw.util.join_paths(dpath, summpath)
                    if os.path.isfile(spath):
                        f = None
                        try:
                            with cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True) as f:
                                r, images = read_summary_classic(basepath, path, f)
                                f.close()
                                return r, images
                        finally:
                            for fpath in os.listdir(dpath):
                                fpath = cw.util.decode_zipname(fpath)
                                fpath = cw.util.join_paths(dpath, fpath)
                                cw.util.remove(fpath)
                else:
                    return None, []
            else:
                summpath = cw.util.cab_hasfile(path, "Summary.xml")
                if summpath:
                    scedir = os.path.dirname(summpath)
                    dpath = cw.util.join_paths(cw.tempdir, "Cab")
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    s = "expand \"%s\" -f:%s \"%s\"" % (path, "Summary.xml", dpath)
                    ret = subprocess.call(s, shell=True)
                    summpath2 = cw.util.join_paths(dpath, summpath)
                    if ret == 0 and os.path.isfile(summpath2):
                        try:
                            rootattrs = {}
                            e = cw.data.xml2element(summpath2, "Property", rootattrs=rootattrs)
                            can_loaded_scaledimage = cw.util.str2bool(rootattrs.get("scaledimage", "False"))

                            try:
                                imgpaths, summaryinfos = parse_summarydata(basepath, e, TYPE_WSN,
                                                                           os.path.getmtime(path), rootattrs)
                            except Exception:
                                return None, []

                            imgbufs = []
                            for info in imgpaths:
                                imgpath = cw.util.join_paths(scedir, info.path)
                                for imgpath, scale in cw.util.get_scaledimagepaths(imgpath, can_loaded_scaledimage):
                                    s = "expand \"%s\" -f:\"%s\" \"%s\"" % (path, os.path.basename(imgpath), dpath)
                                    ret = subprocess.call(s, shell=True)
                                    imgpath2 = cw.util.join_paths(dpath, imgpath)
                                    if ret == 0 and os.path.isfile(imgpath2):
                                        with open(imgpath2, "rb") as ff:
                                            imgbuf = ff.read()
                                            ff.close()
                                        imgbufs.append((imgbuf, info, scale))
                                    elif scale == 1:
                                        imgbufs.append((None, info, scale))

                            return imgbufs_to_result(summaryinfos, imgbufs)

                        finally:
                            for p in os.listdir(dpath):
                                cw.util.remove(cw.util.join_paths(dpath, p))
                return None, []
        except Exception:
            cw.util.print_ex()
            return None, []

    if os.path.isdir(path):
        return None, []

    z = None
    try:
        z = cw.util.zip_file(path, "r")

        nametable = {}
        seq = []
        seq2 = []
        for zname, info in zip(z.namelist(), z.infolist()):
            name = cw.util.decode_zipfilename(zname, info)
            nametable[cw.util.join_paths(name).lower()] = zname
            if os.path.basename(name).lower() in ("summary.xml", "summary.wsm"):
                seq.append(zname)
                seq2.append(name)

        if not seq:
            z.close()
            return None, []

        name = seq[0]
        if name.lower().endswith(".wsm"):
            fdata = z.read(name)
            with cw.binary.cwfile.CWFile("", "rb", decodewrap=True, f=io.BytesIO(fdata)) as f:
                summaryinfos_c, imgbufs = read_summary_classic(basepath, path, f)
                f.close()
            return summaryinfos_c, imgbufs

        scedir = os.path.dirname(seq2[0])
        scedir = cw.util.decode_zipname(scedir)
        fdata = z.read(name)
        with io.BytesIO(fdata) as bytesio:
            rootattrs = {}
            e = cw.data.xml2element(path, "Property", stream=bytesio, rootattrs=rootattrs)

        imgpaths, summaryinfos = parse_summarydata(basepath, e, TYPE_WSN, os.path.getmtime(path), rootattrs)
        can_loaded_scaledimage = cw.util.str2bool(rootattrs.get("scaledimage", "False"))

        imgbufs = []
        for info in imgpaths:
            imgpath = cw.util.join_paths(scedir, info.path)
            for imgpath, scale in cw.util.get_scaledimagepaths(imgpath, can_loaded_scaledimage):
                imgpath = nametable.get(imgpath.lower(), b"")
                if imgpath:
                    imgbuf = cw.util.read_zipdata(z, imgpath)
                    if imgbuf:
                        imgbufs.append((imgbuf, info, scale))
                    else:
                        imgbufs.append((None, info, scale))
                elif scale == 1:
                    imgbufs.append((None, info, scale))

        z.close()

    except Exception:
        cw.util.print_ex()
        print(path)
        if z:
            z.close()
        return None, []

    return imgbufs_to_result(summaryinfos, imgbufs)


def parse_summarydata(basepath: str, data: cw.data.CWPyElement, scetype: int, mtime: float,
                      rootattrs: Dict[str, str]) -> Tuple[List["cw.image.ImageInfo"],
                                                          Tuple[str, int, str, str, str, str, str, int, int, str, int,
                                                                int, str, float, float, str]]:
    wsnversion = rootattrs.get("dataVersion", "")
    imgpaths = []
    e = data.find("ImagePath")
    if e is not None:
        etext = cw.util.validate_filepath(e.text)
        if etext:
            imgpaths.append(cw.image.ImageInfo(path=etext, postype=e.getattr(".", "positiontype", "Default")))
    e = data.find("ImagePaths")
    if e is not None:
        for e2 in e:
            e2text = cw.util.validate_filepath(e2.text)
            if e2.tag == "ImagePath" and e2text:
                imgpaths.append(cw.image.ImageInfo(path=e2text, postype=e2.getattr(".", "positiontype", "Default")))
    name = data.gettext("Name")
    author = data.gettext("Author")
    desc = data.gettext("Description")
    desc = cw.util.txtwrap(desc, 4)
    skintype = data.gettext("Type")
    levelmin = data.getint("Level", "min", 0)
    levelmax = data.getint("Level", "max", 0)
    coupons = data.gettext("RequiredCoupons", "")
    coupons = cw.util.decodewrap(coupons)
    couponsnum = data.getint("RequiredCoupons", "number", 0)
    startid = data.getint("StartAreaId", 0)
    tags = data.gettext("Tags", "")
    tags = cw.util.decodewrap(tags)
    ctime = time.time()
    dpath, fname = os.path.split(basepath)
    return (imgpaths, (dpath, scetype, fname, name, author, desc, skintype, levelmin,
                       levelmax, coupons, couponsnum, startid, tags, ctime, mtime, wsnversion))


def read_summary_classic(basepath: str, spath: str,
                         f: Optional[cw.binary.cwfile.CWFile] = None)\
        -> Tuple[Optional[Tuple[str, int, str, str, str, str, str, int, int, str, int, int, str, float, float, str,
                                Optional[bytes], Optional[str]]],
                 List[Tuple[Optional[bytes], "cw.image.ImageInfo", int]]]:
    try:
        if not f:
            f = cw.binary.cwfile.CWFile(spath, "rb", decodewrap=True)
        s = cw.binary.summary.Summary(None, f, nameonly=False, materialdir="", image_export=False)
        if 4 < s.version:
            return None, []
        s.skintype = ""
        imgbuf = s.image
        ctime = time.time()
        mtime = os.path.getmtime(spath)
    except Exception:
        cw.util.print_ex()
        return None, []

    summaryinfos: Tuple[str, int, str, str, str, str, str, int, int, str, int, int, str, float, float, str,
                        Optional[bytes], Optional[str]] = (
        os.path.dirname(basepath),
        TYPE_CLASSIC,
        os.path.basename(basepath),
        s.name,
        s.author,
        s.description,
        s.skintype,
        s.level_min,
        s.level_max,
        s.required_coupons,
        s.required_coupons_num,
        s.area_id,
        s.tags,
        ctime,
        mtime,
        "",
        imgbuf,
        None
    )
    return summaryinfos, []


def get_scenariopaths(path: str) -> Iterator[str]:
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
            if lfile.endswith(".wsn") or \
                    lfile.endswith(".zip") or \
                    lfile.endswith(".lzh") or \
                    lfile.endswith(".cab"):
                yield fname


def get_scenario(fpath: str) -> Optional[cw.data.ScenarioData]:
    """fpathのシナリオのデータを生成して返す。"""
    lfpath = fpath.lower()
    if lfpath.endswith(".wsm") or lfpath.endswith(".xml"):
        t, images = read_summary(os.path.dirname(fpath))
    else:
        t, images = read_summary(fpath)
    if not t:
        return None

    dbrec: Dict[str, Union[Optional[str], int, float, bool, Optional[bytes]]] = {
        "dpath": t[0],
        "type": t[1],
        "fname": t[2],
        "name": t[3],
        "author": t[4],
        "desc": t[5],
        "skintype": t[6],
        "levelmin": t[7],
        "levelmax": t[8],
        "coupons": t[9],
        "couponsnum": t[10],
        "startid": t[11],
        "tags": t[12],
        "ctime": t[13],
        "mtime": t[14],
        "wsnversion": t[15],
        "image": t[16],
        "imgpath": t[17]
    }
    imgdbrec: List[Dict[str, Union[int, str, Optional[bytes]]]] = []
    for numorder, (image, info, scale) in enumerate(images):
        imgdbrec.append({
            "scale": scale,
            "image": image,
            "imgpath": info.path,
            "postype": info.postype,
            "numorder": numorder
        })

    header = cw.header.ScenarioHeader(dbrec=dbrec, imgdbrec=imgdbrec)
    return cw.data.ScenarioData(header, cardonly=True)


def main() -> None:
    db = Scenariodb()
    db.update()
    db.close()


if __name__ == "__main__":
    main()
