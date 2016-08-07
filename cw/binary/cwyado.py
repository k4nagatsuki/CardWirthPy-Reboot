#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import stat
import shutil
import copy
import itertools

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
        self.nowadventuringparties = []
        # エラーログ
        self.errorlog = ""
        # pathにあるファイル・ディレクトリを
        # (宿ファイル,シナリオファイル,その他のファイル,ディレクトリ)に種類分け。
        exts_yado = set(["wch", "wcp", "wpl", "wpt", "wrm", "whs"])
        exts_sce  = set(["wsm", "wid", "wcl"])
        exts_ignore = set(["wck", "wci", "wcb"])
        self.yadofiles = []
        self.cardfiles = []
        self.otherfiles = []
        self.otherdirs = []
        self.environmentpath = None

        for name in os.listdir(self.path):
            path = util.join_paths(self.path, name)

            if os.path.isfile(path):
                ext = cw.util.splitext(name)[1].lstrip(".").lower()

                if name == "Environment.wyd" and not self.environmentpath:
                    self.environmentpath = path
                    self.yadofiles.append(path)
                elif ext in exts_yado:
                    self.yadofiles.append(path)
                elif ext in exts_sce:
                    self.cardfiles.append(path)
                elif not ext in exts_ignore:
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
            cw.util.print_ex()
            return False

        self.wyd = None

        if data.dataversion_int in (8, 10, 11):
            self.dataversion_int = data.dataversion_int
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
            self.message = u"%s を変換中..." % (os.path.basename(data.fpath))
            self.curnum_n += 1
            self.curnum = min(99, 50 + self.curnum_n * 50 / self.maxnum)

            try:
                fpath = data.create_xml(self.dir)

                if isinstance(data, party.Party) and\
                        self.wyd.partyname == cw.util.splitext(os.path.basename(data.fpath))[0]:
                    fpath = cw.util.relpath(fpath, self.dir)
                    fpath = cw.util.join_paths(fpath)
                    self.wyd.cwpypartyname = fpath

                if hasattr(data, "errorcards"):
                    for errcard in data.errorcards:
                        s = errcard.fname
                        s = u"%s は読込できませんでした。\n" % (s)
                        self.write_errorlog(s)
            except Exception:
                cw.util.print_ex()
                s = os.path.basename(data.fpath)
                s = u"%s は変換できませんでした。\n" % (s)
                self.write_errorlog(s)

        # 冒険中情報を変換
        for partyinfo, partymembers in self.nowadventuringparties:
            self.message = u"%s の冒険中情報を変換中..." % (partyinfo.name)
            self.curnum_n += 1
            self.curnum = min(99, 50 + self.curnum_n * 50 / self.maxnum)

            try:
                self.create_log(partyinfo, partymembers)

            except Exception:
                cw.util.print_ex()
                s = partyinfo.name
                s = u"%s の冒険中情報は変換できませんでした。\n" % (s)
                self.write_errorlog(s)

        yadodb.commit()
        yadodb.close()

        # その他のファイルを宿ディレクトリにコピー
        for path in self.otherfiles:
            self.message = u"%s をコピー中..." % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = min(99, 50 + self.curnum_n * 50 / self.maxnum)
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copy2(path, dst)

            if not os.access(dst, os.R_OK|os.W_OK|os.X_OK):
                os.chmod(dst, stat.S_IWRITE|stat.S_IREAD)

        # ディレクトリを宿ディレクトリにコピー
        for path in self.otherdirs:
            self.message = u"%s をコピー中..." % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = min(99, 50 + self.curnum_n * 50 / self.maxnum)
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
        """宿ファイルを読み込む。
        種類はtypeで判別できる(wydは"-1"、wptは"4"となっている)。
        """
        # 各種データ初期化
        self.datalist = []
        self.wyd = None
        self.wchs = []
        self.wcps = []
        self.wpls = []
        self.wpts = []

        wchwarn = False
        wptwarn = False

        self.curnum_n = 0
        self.curnum = 0
        self.maxnum = len(self.yadofiles) + len(self.cardfiles) + 1

        for path in self.yadofiles:
            self.message = u"%s を読込中..." % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = self.curnum_n * 50 / self.maxnum
            try:
                data = self.load_yadofile(path)
            except Exception:
                cw.util.print_ex()
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                s2 = u"%sが所持しているカードが破損している可能性があります。その場合、あらかじめカードを荷物袋やカード置場へ移動する事で変換が可能になるかもしれません。\n"
                if path.lower().endswith(".wch") and not wchwarn:
                    s += s2 % (u"キャラクター")
                    wchwarn = True
                elif path.lower().endswith(".wpt") and not wptwarn:
                    s += s2 % (u"パーティメンバ")
                    wptwarn = True
                self.write_errorlog(s)

        # ファイルネームからカードの種類を判別する辞書を作成し、
        # カードデータを読み込む
        cardtypes = self.wyd.get_cardtypedict()
        carddatadict = {}

        for path in self.cardfiles:
            self.message = u"%s を読込中..." % (os.path.basename(path))
            self.curnum_n += 1
            self.curnum = self.curnum_n * 50 / self.maxnum
            try:
                data = self.load_cardfile(path, cardtypes)
                carddatadict[data.fname] = data
            except Exception:
                cw.util.print_ex()
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

    #---------------------------------------------------------------------------
    # ここからxml変換するためのもろもろのデータ加工
    #---------------------------------------------------------------------------

        self.message = u"データリストを作成中..."
        self.curnum_n += 1
        self.curnum = self.curnum_n * 50 / self.maxnum

        # wchの埋め込み画像をwcpに格納する
        for wcp in self.wcps:
            for wch in self.wchs:
                if wch.fname == wcp.fname:
                    wcp.set_image(wch.image)
                    break

            # 1.20以前は個人ごとに所持金があるので、宿の金庫に集める
            if self.dataversion_int <= 8:
                self.wyd.money += wcp.adventurer.money
                wcp.adventurer.money = 0

        # wptの荷物袋のカードリストをwplに格納する
        for wpt in self.wpts:
            for wpl in self.wpls:
                if wpt.fname == wpl.fname:
                    wpl.cards = wpt.cards
                    wpt.wpl = wpl
                    if wpt.nowadventuring:
                        self.nowadventuringparties.append((wpl, wpt))
                    if self.dataversion_int <= 8:
                        # wptのパーティ名をwplに格納する
                        wpl.name = wpt.name
                        # wptの所持金データをwplに格納する
                        wpl.money = wpt.money
                    break

        # 荷物袋・カード置場に同一カードが複数存在する場合
        # ２枚目以降にはコピーしたデータを渡す。
        # 同一データを使いまわすと複数カードが同一素材を参照してしまうので
        dictrecord = set()
        def get_dictdata(cardname):
            if cardname in dictrecord:
                data = copy.deepcopy(carddatadict.get(cardname))
            else:
                data = carddatadict.get(cardname)
                dictrecord.add(cardname)
            return data

        if 10 <= self.dataversion_int:
            # wplの荷物袋のカードリストにカードデータ(wid)と種類のデータを付与する。
            for wpl in self.wpls:
                for card in wpl.cards:
                    card.type = cardtypes.get(card.fname)
                    card.set_data(get_dictdata(card.fname))

            # wydのカード置き場のカードリストにカードデータ(wid)と
            # 種類のデータを付与する。
            for card in self.wyd.unusedcards:
                card.type = cardtypes.get(card.fname)
                card.data = get_dictdata(card.fname)

        else:
            # 宿で販売されているカードをカード置場に置く
            for fname, card in carddatadict.iteritems():
                carddata = cw.binary.environment.UnusedCard(None, None, True)
                cd = {
                    ".wck":1,
                    ".wci":2,
                    ".wcb":3
                }
                type = cd.get(os.path.splitext(fname)[1], 0)
                if type:
                    carddata.type = type
                    carddata.fname = fname
                    carddata.uselimit = card.limit
                    carddata.set_data(card)
                    self.wyd.unusedcards.append(carddata)

    #---------------------------------------------------------------------------
    # ここまで
    #---------------------------------------------------------------------------

        # データリスト作成
        self.datalist = []
        self.datalist.extend(self.wcps)
        self.datalist.extend(self.wpts) # wptはwplより先に変換する必要がある
        self.datalist.extend(self.wpls)
        self.datalist.extend(self.wrms)
        self.datalist.append(self.wyd)

        self.maxnum = len(self.datalist)
        self.maxnum += len(self.otherfiles)
        self.maxnum += len(self.otherdirs)
        self.maxnum += len(self.nowadventuringparties)

    def load_yadofile(self, path):
        """ファイル("wch", "wcp", "wpl", "wpt", "wyd", "wrm")を読み込む。"""
        with cwfile.CWFile(path, "rb") as f:

            if path.endswith(".wyd"):
                data = environment.Environment(None, f, True)
                data.skintype = self.skintype
                self.wyd = data
            elif path.endswith(".wch"):
                data = adventurer.AdventurerHeader(None, f, True, dataversion=self.dataversion_int)
                self.wchs.append(data)
            elif path.endswith(".wcp"):
                data = adventurer.AdventurerCard(None, f, True)
                self.wcps.append(data)
            elif path.endswith(".wrm"):
                data = album.Album(None, f, True)
                self.wrms.append(data)
            elif path.endswith(".wpl"):
                data = party.Party(None, f, True, dataversion=self.dataversion_int)
                self.wpls.append(data)
            elif path.endswith(".wpt"):
                data = party.PartyMembers(None, f, True, dataversion=self.dataversion_int)
                self.wpts.append(data)
            elif path.endswith(".whs"):
                cards, albums = party.load_album120(None, f)
                for data in cards:
                    self.wcps.append(data)
                for albumdata in albums:
                    self.wrms.append(albumdata)
                data = None
            else:
                f.close()
                raise ValueError(path)
            f.close()

        return data

    def load_cardfile(self, path, d):
        """引数のファイル(wid, wsmファイル)を読み込む。
        読み込みに際し、wydファイルから作成できる
        ファイルネームでカードの種類を判別する辞書が必要。
        """
        with cwfile.CWFile(path, "rb") as f:
            # 1:スキル, 2:アイテム, 3:召喚獣
            fname = os.path.basename(path)
            if fname.lower().endswith(".wcl"):
                # 1.20以前の「カード購入」にあるカード
                name = os.path.splitext(path)[0]
                # 拡張子で識別する
                cd = {
                    ".wck":skill.SkillCard,
                    ".wci":item.ItemCard,
                    ".wcb":beast.BeastCard
                }
                for ext in (".wck", ".wci", ".wcb"):
                    if os.path.isfile(name + ext):
                        with cwfile.CWFile(name + ext, "rb") as f2:
                            data = cd[ext](None, f2, True)
                            f2.close()
                        _dataversion = f.string()
                        _name = f.string()
                        data.image = f.image()
                        data.fname = os.path.basename(name + ext)
                        break
                else:
                    raise ValueError(path)
            else:
                # 1.28以降のカード置場と荷物袋
                restype = d.get(cw.util.splitext(fname)[0])

                if restype == 1:
                    data = skill.SkillCard(None, f, True)
                elif restype == 2:
                    data = item.ItemCard(None, f, True)
                elif restype == 3:
                    data = beast.BeastCard(None, f, True)
                else:
                    f.close()
                    raise ValueError(path)

            f.close()

        return data

    def create_log(self, party, partymembers):
        """シナリオ進行状況とF9用データの変換を行う。"""
        if not partymembers.nowadventuring:
            return
        # log
        element = cw.data.make_element("ScenarioLog")
        # Property
        e_prop = cw.data.make_element("Property")
        element.append(e_prop)
        e = cw.data.make_element("Name", party.name)
        e_prop.append(e)
        e = cw.data.make_element("WsnPath", partymembers.scenariopath)
        e_prop.append(e)
        e = cw.data.make_element("RoundAutoStart", str(False))
        e_prop.append(e)

        e = cw.data.make_element("Debug", str(bool(self.wyd.yadotype == 2)))
        e_prop.append(e)
        e = cw.data.make_element("AreaId", str(partymembers.areaid))
        e_prop.append(e)

        e = cw.data.make_element("MusicPath", partymembers.music)
        e_prop.append(e)
        e = cw.data.make_element("Yado", self.wyd.name)
        e_prop.append(e)
        e = cw.data.make_element("Party", party.name)
        e_prop.append(e)
        # bgimages
        e_bgimgs = cw.data.make_element("BgImages")
        partymembers.set_materialdir("")
        for bgimg in partymembers.bgimgs:
            e_bgimgs.append(bgimg.get_data())
        element.append(e_bgimgs)

        # flag
        e_flag = cw.data.make_element("Flags")
        element.append(e_flag)

        for name, value in partymembers.flags.iteritems():
            e = cw.data.make_element("Flag", name, {"value": str(value)})
            e_flag.append(e)

        # step
        e_step = cw.data.make_element("Steps")
        element.append(e_step)

        for name, value in partymembers.steps.iteritems():
            e = cw.data.make_element("Step", name, {"value": str(value)})
            e_step.append(e)

        # gossip(無し)
        e_gossip = cw.data.make_element("Gossips")
        element.append(e_gossip)

        # completestamps(無し)
        e_compstamp = cw.data.make_element("CompleteStamps")
        element.append(e_compstamp)

        # InfoCard
        e_info = cw.data.make_element("InfoCards")
        element.append(e_info)

        for resid in partymembers.infocards:
            e = cw.data.make_element("InfoCard", str(resid))
            e_info.append(e)

        # FriendCard
        e_cast = cw.data.make_element("CastCards")
        element.append(e_cast)

        for resid in reversed(partymembers.friendcards):
            e_cast.append(cw.data.make_element("FriendCard", str(resid)))

        # DeletedFile(無し)
        e_del = cw.data.make_element("DeletedFiles")
        element.append(e_del)

        # LostAdventurer
        e_lost = cw.data.make_element("LostAdventurers")
        element.append(e_lost)

        partymembers.create_vanisheds_xml(partymembers.get_dir())
        for adventurer in partymembers.vanisheds:
            fpath = adventurer.xmlpath
            fpath = cw.util.relpath(fpath, adventurer.get_dir())
            fpath = cw.util.join_paths(fpath)
            e = cw.data.make_element("LostAdventurer", fpath)
            e_lost.append(e)

        # ファイル書き込み
        etree = cw.data.xml2etree(element=element)
        etree.write(cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"))

        # party
        element = cw.data.make_element("ScenarioLog")
        # Property
        e_prop = cw.data.make_element("Property")
        element.append(e_prop)
        # Name
        e_name = cw.data.make_element("Name", partymembers.name)
        e_prop.append(e_name)
        # Money
        e_money = cw.data.make_element("Money", str(partymembers.money_beforeadventure))
        e_prop.append(e_money)
        # Members
        e_members = cw.data.make_element("Members")
        e_prop.append(e_members)
        for adventurer in partymembers.adventurers + partymembers.vanisheds:
            fpath = os.path.basename(adventurer.xmlpath)
            fpath = cw.util.splitext(fpath)[0]
            e = cw.data.make_element("LostAdventurer", fpath)
            e_members.append(e)

        etree = cw.data.xml2etree(element=element)
        etree.write(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party/Party.xml"))

        # member
        os.makedirs(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members"))
        for adventurer in partymembers.adventurers + partymembers.vanisheds:
            dstpath = cw.util.join_paths(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members"),
                                                    os.path.basename(adventurer.xmlpath))
            etree = cw.data.xml2etree(element=adventurer.get_f9data())
            etree.write(dstpath)

        # 荷物袋内のカード群(ファイルパスのみ)
        element = cw.data.make_element("BackpackFiles")
        cdpath = os.path.dirname(party.xmlpath)
        carddb = cw.yadodb.YadoDB(cdpath, cw.yadodb.PARTY)
        fpaths = carddb.get_cardfpaths(scenariocard=False)
        carddb.close()
        for fpath in fpaths:
            element.append(cw.data.make_element("File", fpath))
        path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Backpack.xml")
        etree = cw.data.xml2etree(element=element)
        etree.write(path)

        # create_zip
        path = cw.util.splitext(party.xmlpath)[0] + ".wsl"
        cw.util.compress_zip(cw.util.join_paths(cw.tempdir, u"ScenarioLog"), path, unicodefilename=True)
        cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))

class UnconvCWYado(object):
    """宿データを逆変換してdstpathへ保存する。
    """
    def __init__(self, ydata, dstpath, targetengine):
        self.ydata = ydata
        self.targetengine = targetengine
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
            try:
                with cwfile.CWFileWriter(fpath, "wb",
                         targetengine=self.targetengine,
                         write_errorlog=self.write_errorlog) as f:
                    if header.type == "SkillCard":
                        skill.SkillCard.unconv(f, data, False)
                    elif header.type == "ItemCard":
                        item.ItemCard.unconv(f, data, False)
                    elif header.type == "BeastCard":
                        beast.BeastCard.unconv(f, data, False)
                    f.flush()
                    f.close()
                return data, fpath
            except Exception, ex:
                cw.util.print_ex(file=sys.stderr)
                cw.util.remove(fpath)
                raise ex

        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)

        # カード置場のカード(*.wid)
        unusedcards = []
        yadocards = {}
        for header in self.ydata.storehouse:
            try:
                self.message = u"%s を変換中..." % (header.name)
                self.curnum += 1
                data, fpath = write_card(header)
                unusedcards.append((os.path.basename(fpath), data))
                yadocards[header.fpath] = os.path.basename(fpath), data
            except cw.binary.cwfile.UnsupportedError, ex:
                if ex.msg:
                    s = ex.msg
                else:
                    s = u"%s は対象エンジンで使用できないため、変換しません。\n" % (header.name)
                self.write_errorlog(s)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                s = u"%s は変換できませんでした。\n" % (header.name)
                self.write_errorlog(s)
        table["unusedcards"] = unusedcards

        # 待機中冒険者(*.wcp)とそのヘッダ(*.wch)
        for header in self.ydata.standbys:
            try:
                self.message = u"%s を変換中..." % (header.name)
                self.curnum += 1

                data = cw.data.xml2element(header.fpath)
                cw.character.Character(data=cw.data.xml2etree(element=data)).set_fullrecovery()

                ppath = create_fpath(header.name, ".wcp")
                hpath = create_fpath(header.name, ".wch")
                with cwfile.CWFileWriter(ppath, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                    adventurer.AdventurerCard.unconv(f, data)
                    f.flush()
                    f.close()

                with cwfile.CWFileWriter(hpath, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                    adventurer.AdventurerHeader.unconv(f, data, ppath)
                    f.flush()
                    f.close()

            except cw.binary.cwfile.UnsupportedError, ex:
                if ex.msg:
                    s = ex.msg
                else:
                    s = u"%s は対象エンジンで使用できないため、変換しません。\n" % (header.name)
                self.write_errorlog(s)
                cw.util.remove(ppath)
                cw.util.remove(hpath)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                s = u"%s は変換できませんでした。\n" % (header.name)
                self.write_errorlog(s)
                cw.util.remove(ppath)
                cw.util.remove(hpath)

        # 荷物袋のカード(*.wid)
        parties = []
        for partyheader in self.ydata.partys:
            self.message = u"%s の荷物袋を変換中..." % (partyheader.name)
            self.curnum += 1

            pt = cw.data.Party(partyheader)
            parties.append((partyheader, pt))

            for header in itertools.chain(pt.backpack, pt.backpack_moved):
                try:
                    data, fpath = write_card(header)

                    yadocards[header.fpath] = os.path.basename(fpath), data

                except cw.binary.cwfile.UnsupportedError, ex:
                    if ex.msg:
                        s = ex.msg
                    else:
                        s = u"%s の所持する %s は対象エンジンで使用できないため、変換しません。\n" % (partyheader.name, header.name)
                    self.write_errorlog(s)
                except Exception:
                    cw.util.print_ex(file=sys.stderr)
                    s = u"%s の %s は変換できませんでした。\n" % (partyheader.name, header.name)
                    self.write_errorlog(s)

        table["yadocards"] = yadocards

        # パーティ(*.wpl)とパーティ内冒険者(*.wpt)
        partytable = {}
        yadodir = self.ydata.yadodir
        tempdir = self.ydata.tempdir
        for partyheader, pt in parties:
            try:
                self.message = u"%s を変換中..." % (partyheader.name)
                self.curnum += 1

                # log
                if os.path.isdir(cw.util.join_paths(cw.tempdir, u"ScenarioLog")):
                    cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
                path = cw.util.splitext(pt.data.fpath)[0] + ".wsl"
                if os.path.isfile(path):
                    cw.util.decompress_zip(path, cw.tempdir, "ScenarioLog")
                    etree = cw.data.xml2etree(cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"))
                    scenarioname = etree.gettext("Property/Name")
                    if not scenarioname:
                        scenarioname = "noname"
                    logdir = cw.util.join_paths(cw.tempdir, u"ScenarioLog")
                else:
                    scenarioname = ""
                    logdir = ""

                atbl = { "yadoname":self.ydata.name }
                names = partyheader.get_membernames()
                i = 0
                for member in partyheader.members:
                    atbl[member] = names[i]
                    i += 1
                atbl["adventurers"] = atbl

                fpath1 = create_fpath(pt.name, ".wpl")
                with cwfile.CWFileWriter(fpath1, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                    party.Party.unconv(f, pt.data.find("."), atbl, scenarioname)
                    f.flush()
                    f.close()

                fpath2 = create_fpath(pt.name, ".wpt")
                with cwfile.CWFileWriter(fpath2, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                    party.PartyMembers.unconv(f, pt, table, logdir)
                    f.flush()
                    f.close()

                if partyheader.fpath.lower().startswith("yado"):
                    relpath = cw.util.relpath(partyheader.fpath, yadodir)
                else:
                    relpath = cw.util.relpath(partyheader.fpath, tempdir)
                relpath = cw.util.join_paths(relpath)
                partytable[relpath] = cw.util.splitext(os.path.basename(fpath2))[0]

                if logdir:
                    cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
            except cw.binary.cwfile.UnsupportedError, ex:
                if ex.msg:
                    s = ex.msg
                else:
                    s = u"%s は対象エンジンで使用できないため、変換しません。\n" % (partyheader.name)
                self.write_errorlog(s)
                cw.util.remove(fpath1)
                cw.util.remove(fpath2)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                s = u"%s は変換できませんでした。\n" % (partyheader.name)
                self.write_errorlog(s)
                cw.util.remove(fpath1)
                cw.util.remove(fpath2)

        table["party"] = partytable

        # アルバム(*.wrm)
        for header in self.ydata.album:
            try:
                self.message = u"%s を変換中..." % (header.name)
                self.curnum += 1

                data = cw.data.xml2element(header.fpath)

                fpath = create_fpath(header.name, ".wrm")
                with cwfile.CWFileWriter(fpath, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                    album.Album.unconv(f, data)
                    f.flush()
                    f.close()

            except cw.binary.cwfile.UnsupportedError, ex:
                if ex.msg:
                    s = ex.msg
                else:
                    s = u"%s は対象エンジンで使用できないため、変換しません。\n" % (header.name)
                self.write_errorlog(s)
                cw.util.remove(fpath)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                s = u"%s は変換できませんでした。\n" % (header.name)
                self.write_errorlog(s)
                cw.util.remove(fpath)

        # Environment.wyd
        self.message = u"宿情報を変換中..."
        self.curnum += 1
        try:
            data = self.ydata.environment.find(".")
            fpath = cw.util.join_paths(self.dir, "Environment.wyd")
            with cwfile.CWFileWriter(fpath, "wb",
                        targetengine=self.targetengine,
                        write_errorlog=self.write_errorlog) as f:
                environment.Environment.unconv(f, data, table)
                f.flush()
                f.close()

        except Exception:
            cw.util.print_ex(file=sys.stderr)
            s = u"宿情報は変換できませんでした。\n"
            self.write_errorlog(s)

def main():
    pass

if __name__ == "__main__":
    main()
