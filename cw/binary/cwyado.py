#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import stat
import shutil

import util
import cw
import cwfile
import environment
import adventurer
import party
import album
import skill
import item
import beast


class CWYado(object):
    """pathの宿データをxmlに変換、yadoディレクトリに保存する。
    その他ファイルもコピー。
    """
    def __init__(self, path, dstpath, skintype=""):
        self.name = os.path.basename(path)
        self.path = path
        self.dir = util.join_paths(dstpath, os.path.basename(path))
        self.dir = util.check_duplicate(self.dir)
        self.skintype = skintype
        # progress dialog data
        self.message = ""
        self.curnum = 0
        self.maxnum = 1
        # 読み込んだデータリスト
        self.datalist = []
        self.wyd = None
        self.wchs = []
        self.wcps = []
        self.wrms = []
        self.wpls = []
        self.wpts = []
        # エラーログ
        self.errorlog = ""
        # pathにあるファイル・ディレクトリを
        # (宿ファイル,シナリオファイル,その他のファイル,ディレクトリ)に種類分け。
        exts_yado = set(["wch", "wcp", "wpl", "wpt", "wrm"])
        exts_sce  = set(["wsm", "wid"])
        self.yadofiles = []
        self.cardfiles = []
        self.otherfiles = []
        self.otherdirs = []
        self.environmentpath = None

        for name in os.listdir(self.path):
            path = util.join_paths(self.path, name)

            if os.path.isfile(path):
                ext = os.path.splitext(name)[1].lstrip(".").lower()

                if name == "Environment.wyd" and not self.environmentpath:
                    self.environmentpath = path
                    self.yadofiles.append(path)
                elif ext in exts_yado:
                    self.yadofiles.append(path)
                elif ext in exts_sce:
                    self.cardfiles.append(path)
                else:
                    self.otherfiles.append(path)

            else:
                self.otherdirs.append(path)

    def write_errorlog(self, s):
        self.errorlog += s + "\n"

    def is_convertible(self):
        if not self.environmentpath:
            return False

        try:
            data = self.load_yadofile(self.environmentpath)
        except:
            return False

        self.wyd = None

        if data.dataversion_int in (10, 11):
            return True
        else:
            return False

    def convert(self):
        if not self.datalist:
            self.load()

        self.curnum = 0

        # 宿データをxmlに変換
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        yadodb = cw.yadodb.YadoDB(self.dir)
        for data in self.datalist:
            data.yadodb = yadodb
            self.message = u"%s を変換中" % (os.path.basename(data.fpath))
            self.curnum += 1

            try:
                data.create_xml(self.dir)
            except:
                s = os.path.basename(data.fpath)
                s = u"%s は変換できませんでした。\n" % (s)
                self.write_errorlog(s)

        yadodb.commit()
        yadodb.close()

        # その他のファイルを宿ディレクトリにコピー
        for path in self.otherfiles:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum += 1
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copy2(path, dst)

            if not os.access(dst, os.R_OK|os.W_OK|os.X_OK):
                os.chmod(dst, stat.S_IWRITE|stat.S_IREAD)

        # ディレクトリを宿ディレクトリにコピー
        for path in self.otherdirs:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum += 1
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copytree(path, dst)

            if not os.access(dst, os.R_OK|os.W_OK|os.X_OK):
                os.chmod(dst, stat.S_IWRITE|stat.S_IREAD)

        # 存在しないディレクトリを作成
        dnames = ("Adventurer", "Album", "BeastCard", "ItemCard", "SkillCard",
                                                                    "Party")

        for dname in dnames:
            path = util.join_paths(self.dir, dname)

            if not os.path.isdir(path):
                os.makedirs(path)

        self.curnum = self.maxnum
        return self.dir

    def load(self):
        """宿ファイルのを読み込む。
        種類はtypeで判別できる(wydは"-1"、wptは"4"となっている)。
        """
        # 各種データ初期化
        self.datalist = []
        self.wyd = None
        self.wchs = []
        self.wcps = []
        self.wpls = []
        self.wpts = []

        for path in self.yadofiles:
            try:
                data = self.load_yadofile(path)
            except:
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

        # ファイルネームからカードの種類を判別する辞書を作成し、
        # カードデータを読み込む
        cardtypes = self.wyd.get_cardtypedict()
        carddatadict = {}

        for path in self.cardfiles:
            try:
                data = self.load_cardfile(path, cardtypes)
                carddatadict[data.fname] = data
            except:
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

    #---------------------------------------------------------------------------
    # ここからxml変換するためのもろもろのデータ加工
    #---------------------------------------------------------------------------

        # wchの埋め込み画像をwcpに格納する。
        for wch in self.wchs:
            for wcp in self.wcps:
                if wch.fname == wcp.fname:
                    wcp.set_image(wch.image)

        # wptの荷物袋のカードリストをwplに格納する
        for wpt in self.wpts:
            for wpl in self.wpls:
                if wpt.fname == wpl.fname:
                    wpl.cards = wpt.cards

        # wplの荷物袋のカードリストにカードデータ(wid)と種類のデータを付与する。
        for wpl in self.wpls:
            for card in wpl.cards:
                card.type = cardtypes.get(card.fname)
                card.data = carddatadict.get(card.fname)

        # wydのカード置き場のカードリストにカードデータ(wid)と
        # 種類のデータを付与する。
        for card in self.wyd.unusedcards:
            card.type = cardtypes.get(card.fname)
            card.data = carddatadict.get(card.fname)

    #---------------------------------------------------------------------------
    # ここまで
    #---------------------------------------------------------------------------

        # データリスト作成
        self.datalist = [self.wyd]
        self.datalist.extend(self.wcps)
        self.datalist.extend(self.wpls)
        self.datalist.extend(self.wpts)
        self.datalist.extend(self.wrms)

        self.maxnum = len(self.datalist)
        self.maxnum += len(self.otherfiles)
        self.maxnum += len(self.otherdirs)

    def load_yadofile(self, path):
        """ファイル("wch", "wcp", "wpl", "wpt", "wyd", "wrm")を読み込む。"""
        f = cwfile.CWFile(path, "rb")

        if path.endswith(".wyd"):
            data = environment.Environment(None, f, True)
            data.skintype = self.skintype
            self.wyd = data
        elif path.endswith(".wch"):
            data = adventurer.AdventurerHeader(None, f, True)
            self.wchs.append(data)
        elif path.endswith(".wcp"):
            data = adventurer.AdventurerCard(None, f, True)
            self.wcps.append(data)
        elif path.endswith(".wrm"):
            data = album.Album(None, f, True)
            self.wrms.append(data)
        elif path.endswith(".wpl"):
            data = party.Party(None, f, True)
            self.wpls.append(data)
        elif path.endswith(".wpt"):
            data = party.PartyMembers(None, f, True)
            self.wpts.append(data)
        else:
            raise ValueError(path)

        f.close()
        return data

    def load_cardfile(self, path, d):
        """引数のファイル(wid, wsmファイル)を読み込む。
        読み込みに際し、wydファイルから作成できる
        ファイルネームでカードの種類を判別する辞書が必要。
        """
        f = cwfile.CWFile(path, "rb")
        # 1:スキル, 2:アイテム, 3:召喚獣
        fname = os.path.basename(path)
        type = d.get(os.path.splitext(fname)[0])

        if type == 1:
            data = skill.SkillCard(None, f, True)
        elif type == 2:
            data = item.ItemCard(None, f, True)
        elif type == 3:
            data = beast.BeastCard(None, f, True)
        else:
            raise ValueError(path)

        f.close()
        return data

def main():
    pass

if __name__ == "__main__":
    main()
