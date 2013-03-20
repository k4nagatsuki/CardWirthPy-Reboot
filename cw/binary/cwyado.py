#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import stat
import shutil
import traceback

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

        self.curnum_n = 0
        self.curnum = 50

        # 宿データをxmlに変換
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        yadodb = cw.yadodb.YadoDB(self.dir)
        for data in self.datalist:
            data.yadodb = yadodb
            self.message = u"%s を変換中" % (os.path.basename(data.fpath))
            self.curnum_n += 1
            self.curnum = 50 + self.curnum_n * 50 / self.maxnum

            try:
                fpath = data.create_xml(self.dir)

                if isinstance(data, party.Party) and\
                        self.wyd.partyname == os.path.splitext(os.path.basename(data.fpath))[0]:
                    fpath = os.path.relpath(fpath, self.dir)
                    fpath = cw.util.join_paths(fpath)
                    self.wyd.cwpypartyname = fpath

                if hasattr(data, "errorcards"):
                    for errcard in data.errorcards:
                        s = errcard.fname
                        s = u"%s は読込できませんでした。\n" % (s)
                        self.write_errorlog(s)
            except Exception, ex:
                print ex
                s = os.path.basename(data.fpath)
                s = u"%s は変換できませんでした。\n" % (s)
                self.write_errorlog(s)

        yadodb.commit()
        yadodb.close()

        # その他のファイルを宿ディレクトリにコピー
        for path in self.otherfiles:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = 50 + self.curnum_n * 50 / self.maxnum
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copy2(path, dst)

            if not os.access(dst, os.R_OK|os.W_OK|os.X_OK):
                os.chmod(dst, stat.S_IWRITE|stat.S_IREAD)

        # ディレクトリを宿ディレクトリにコピー
        for path in self.otherdirs:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = 50 + self.curnum_n * 50 / self.maxnum
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

        self.curnum = 100
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

        self.curnum_n = 0
        self.curnum = 0
        self.maxnum = len(self.yadofiles) + len(self.cardfiles) + 1

        for path in self.yadofiles:
            self.message = u"%s を読込中" % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = self.curnum_n * 50 / self.maxnum
            try:
                data = self.load_yadofile(path)
            except Exception, ex:
                print ex
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

        # ファイルネームからカードの種類を判別する辞書を作成し、
        # カードデータを読み込む
        cardtypes = self.wyd.get_cardtypedict()
        carddatadict = {}

        for path in self.cardfiles:
            self.message = u"%s を読込中" % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = self.curnum_n * 50 / self.maxnum
            try:
                data = self.load_cardfile(path, cardtypes)
                carddatadict[data.fname] = data
            except Exception, ex:
                print ex
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

    #---------------------------------------------------------------------------
    # ここからxml変換するためのもろもろのデータ加工
    #---------------------------------------------------------------------------

        self.message = u"データリストを作成中"
        self.curnum_n += 1
        self.curnum = self.curnum_n * 50 / self.maxnum

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
        self.datalist = []
        self.datalist.extend(self.wcps)
        self.datalist.extend(self.wpls)
        self.datalist.extend(self.wpts)
        self.datalist.extend(self.wrms)
        self.datalist.append(self.wyd)

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

class UnconvCWYado(object):
    """宿データを逆変換してdstpathへ保存する。
    """
    def __init__(self, ydata, dstpath):
        self.ydata = ydata
        self.name = self.ydata.name
        self.dir = util.join_paths(dstpath, util.check_filename(self.name))
        self.dir = util.check_duplicate(self.dir)
        # progress dialog data
        self.message = ""
        self.curnum = 0
        self.maxnum = 1
        self.maxnum += len(ydata.storehouse)
        self.maxnum += len(ydata.standbys)
        self.maxnum += len(ydata.partys) * 2
        self.maxnum += len(ydata.album)
        # エラーログ
        self.errorlog = ""

    def write_errorlog(self, s):
        self.errorlog += s + "\n"

    def convert(self):
        # 変換中情報
        table = { "yadoname":self.name }

        def create_fpath(name, ext):
            fpath = util.join_paths(self.dir, util.check_filename(name) + ext)
            fpath = util.check_duplicate(fpath)
            return fpath

        def write_card(header):
            data = cw.data.xml2element(header.fpath)
            fpath = create_fpath(header.name, ".wid")
            f = cwfile.CWFileWriter(fpath, "wb")
            try:
                if header.type == "SkillCard":
                    skill.SkillCard.unconv(f, data)
                elif header.type == "ItemCard":
                    item.ItemCard.unconv(f, data)
                elif header.type == "BeastCard":
                    beast.BeastCard.unconv(f, data)
            finally:
                f.close()
            return data, fpath

        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)

        # カード置場のカード(*.wid)
        unusedcards = []
        for header in self.ydata.storehouse:
##            try:
                self.message = u"%s を変換中" % (header.name)
                self.curnum += 1
                data, fpath = write_card(header)
                unusedcards.append((os.path.basename(fpath), data))
##            except Exception, ex:
##                print ex
##                s = u"%s は変換できませんでした。\n" % (header.name)
##                self.write_errorlog(s)
        table["unusedcards"] = unusedcards

        # 待機中冒険者(*.wcp)とそのヘッダ(*.wch)
        for header in self.ydata.standbys:
##            try:
                self.message = u"%s を変換中" % (header.name)
                self.curnum += 1

                data = cw.data.xml2element(header.fpath)

                ppath = create_fpath(header.name, ".wcp")
                f = cwfile.CWFileWriter(ppath, "wb")
                try:
                    adventurer.AdventurerCard.unconv(f, data)
                finally:
                    f.close()

                hpath = create_fpath(header.name, ".wch")
                f = cwfile.CWFileWriter(hpath, "wb")
                try:
                    adventurer.AdventurerHeader.unconv(f, data, ppath)
                finally:
                    f.close()

##            except Exception, ex:
##                print ex
##                s = u"%s は変換できませんでした。\n" % (header.name)
##                self.write_errorlog(s)

        # 荷物袋のカード(*.wid)
        parties = []
        yadocards = {}
        for partyheader in self.ydata.partys:
            self.message = u"%s の荷物袋を変換中" % (partyheader.name)
            self.curnum += 1

            pt = cw.data.Party(partyheader)
            parties.append((partyheader, pt))

            for header in pt.backpack + pt.backpack_moved:
##                try:
                    data, fpath = write_card(header)

                    yadocards[header.fpath] = os.path.basename(fpath), data

##                except Exception, ex:
##                    print ex
##                    s = u"%s の %s は変換できませんでした。\n" % (partyheader.name, header.name)
##                    self.write_errorlog(s)

        table["yadocards"] = yadocards

        # パーティ(*.wpl)とパーティ内冒険者(*.wpt)
        partytable = {}
        yadodir = self.ydata.yadodir
        tempdir = self.ydata.tempdir
        for partyheader, pt in parties:
##            try:
                self.message = u"%s を変換中" % (partyheader.name)
                self.curnum += 1

                atbl = { "yadoname":self.ydata.name }
                names = partyheader.get_membernames()
                i = 0
                for member in pt.data.getfind("Property/Members"):
                    if member.tag == "Member" and member.text:
                        atbl[member.text] = names[i]
                        i += 1
                atbl["adventurers"] = atbl

                fpath = create_fpath(pt.name, ".wpl")
                f = cwfile.CWFileWriter(fpath, "wb")
                try:
                    party.Party.unconv(f, pt.data.find("."), atbl)
                finally:
                    f.close()

                fpath = create_fpath(pt.name, ".wpt")
                f = cwfile.CWFileWriter(fpath, "wb")
                try:
                    party.PartyMembers.unconv(f, pt, table)
                finally:
                    f.close()

                if partyheader.fpath.lower().startswith("yado"):
                    relpath = os.path.relpath(partyheader.fpath, yadodir)
                else:
                    relpath = os.path.relpath(partyheader.fpath, tempdir)
                relpath = cw.util.join_paths(relpath)
                partytable[relpath] = os.path.splitext(os.path.basename(fpath))[0]

##            except Exception, ex:
##                print ex
##                s = u"%s は変換できませんでした。\n" % (partyheader.name)
##                self.write_errorlog(s)

        table["party"] = partytable

        # アルバム(*.wrm)
        for header in self.ydata.album:
##            try:
                self.message = u"%s を変換中" % (header.name)
                self.curnum += 1

                data = cw.data.xml2element(header.fpath)

                fpath = create_fpath(header.name, ".wrm")
                f = cwfile.CWFileWriter(fpath, "wb")
                try:
                    album.Album.unconv(f, data)
                finally:
                    f.close()

##            except Exception, ex:
##                print ex
##                s = u"%s は変換できませんでした。\n" % (header.name)
##                self.write_errorlog(s)

        # Environment.wyd
        self.message = u"宿情報を変換中"
        self.curnum += 1
##        try:
        data = self.ydata.environment.find(".")
        fpath = cw.util.join_paths(self.dir, "Environment.wyd")
        f = cwfile.CWFileWriter(fpath, "wb")
        try:
            environment.Environment.unconv(f, data, table)
        finally:
            f.close()

##        except Exception, ex:
##            print ex
##            s = u"宿情報は変換できませんでした。\n"
##            self.write_errorlog(s)

        # TODO 過程・デバッグ

def main():
    pass

if __name__ == "__main__":
    main()
