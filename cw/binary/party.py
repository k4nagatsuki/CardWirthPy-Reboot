#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import sys

import base
import adventurer
import util

import cw
import cw.binary.cwfile
import cw.binary.summary
import cw.binary.album
import cw.binary.skill
import cw.binary.item
import cw.binary.beast
import bgimage


class Party(base.CWBinaryBase):
    """wplファイル(type=2)。パーティの見出しデータ。
    パーティの所持金や名前はここ。
    宿の画像も格納しているが必要ないと思うので破棄。
    F9のためにゴシップと終了印を記憶しているような事は無い
    (その2つはF9で戻らない)。
    """
    def __init__(self, parent, f, yadodata=False, dataversion=10):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 2
        self.fname = self.get_fname()
        if 10 <= dataversion:
            # 1.28以降
            _w = f.word() # 不明(0)
            _yadoname = f.string()
            f.image() # 宿の埋め込み画像は破棄
            self.memberslist = []
            for member in cw.util.decodetextlist(f.string(True)):
                if member <> "":
                    self.memberslist.append(util.check_filename(member))
            self.name = f.string()
            self.money = f.dword() # 冒険中の現在値
            self.nowadventuring = f.bool()
        else:
            # 1.20
            self.memberslist = []
            for member in cw.util.decodetextlist(f.string(True)):
                if member <> "":
                    self.memberslist.append(util.check_filename(member))
            dataversion_str = f.string()
            _scenarioname = f.string() # プレイ中のシナリオ名
            f.image() # 宿の埋め込み画像は破棄
            self.name = ""
            self.money = 0
            self.nowadventuring = f.bool()

        # 読み込み後に操作
        self.cards = []
        # データの取得に失敗したカード。変換時に追加する
        self.errorcards = []

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Party")

            prop = cw.data.make_element("Property")

            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("Money", str(self.money))
            prop.append(e)

            me = cw.data.make_element("Members")
            # メンバーの追加はwpt側で
            prop.append(me)

            self.data.append(prop)

        return self.data

    def create_xml(self, dpath):
        path = base.CWBinaryBase.create_xml(self, dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_party(path, commit=False)

        # 荷物袋内のカード
        cdpath = os.path.dirname(path)
        carddb = cw.yadodb.YadoDB(cdpath, cw.yadodb.PARTY)
        self.errorcards = []
        order = 0
        for card in self.cards:
            if card.data:
                card.data.materialbasedir = dpath
                cpath = card.create_xml(cdpath)
                carddb.insert_card(cpath, commit=False, cardorder=order)
                order += 1
            else:
                self.errorcards.append(card)
        carddb.commit()
        carddb.close()

        return path

    @staticmethod
    def unconv(f, data, table, scenarioname):
        if scenarioname:
            yadoname = scenarioname
            nowadventuring = True
        else:
            yadoname = table["yadoname"]
            nowadventuring = False
        imgpath = "Resource/Image/Card/COMMAND0"
        imgpath = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, imgpath), cw.cwpy.rsrc.ext_img)
        image = base.CWBinaryBase.import_image(f, imgpath, fullpath=True)
        memberslist = ""
        name = ""
        money = 0

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "Money":
                        money = int(prop.text)
                        money = cw.util.numwrap(money, 0, 999999)
                    elif prop.tag == "Members":
                        atbl = table["adventurers"]
                        seq = []
                        for me in prop:
                            if me.tag == "Member" and me.text and me.text in atbl:
                                seq.append(atbl[me.text])
                        memberslist = cw.util.encodetextlist(seq)

        f.write_word(0) # 不明
        f.write_string(yadoname)
        f.write_image(image)
        f.write_string(memberslist, True)
        f.write_string(name)
        f.write_dword(money)
        f.write_bool(nowadventuring)

class PartyMembers(base.CWBinaryBase):
    """wptファイル(type=3)。パーティメンバと
    荷物袋に入っているカードリストを格納している。
    """
    def __init__(self, parent, f, yadodata=False, dataversion=10):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 3
        self.fname = self.get_fname()
        if 10 <= dataversion:
            adventurers_num = f.byte() - 30
        else:
            adventurers_num = f.byte() - 10
        _b = f.byte() # 不明(0)
        _b = f.byte() # 不明(0)
        _b = f.byte() # 不明(0)
        _b = f.byte() # 不明(5)
        self.adventurers = []
        vanisheds_num = 0
        for i in xrange(adventurers_num):
            self.adventurers.append(adventurer.AdventurerWithImage(self, f))
            if 10 <= dataversion:
                vanisheds_num = f.byte() # 最後のメンバが消滅メンバの数を持っている？
            else:
                _b = f.byte() # 不明(0)
        self.vanisheds = []
        if 0 < vanisheds_num:
            _dw = f.dword() # 不明(0)
            for i in xrange(vanisheds_num):
                self.vanisheds.append(adventurer.AdventurerWithImage(self, f))
                if i + 1 < vanisheds_num:
                    _b = f.byte()
            self.vanisheds.reverse()
        else:
            _b = f.byte() # 不明(0)
            _b = f.byte() # 不明(0)
            _b = f.byte() # 不明(0)
        if 10 <= dataversion:
            # 1.28以降
            self.name = f.string() # パーティ名
            # 荷物袋にあるカードリスト
            cards_num = f.dword()
            self.cards = [BackpackCard(self, f) for _cnt in xrange(cards_num)]
        else:
            # 1.20
            f.seek(-4, io.SEEK_CUR)
            # パーティ名
            self.name = self.adventurers[0].adventurer.name + u"一行"
            # 荷物袋にあるカードリスト
            cards_num = f.dword()
            self.cards = []
            for _cnt in xrange(cards_num):
                type = f.byte()
                if type == 2:
                    carddata = cw.binary.item.ItemCard(None, f, True)
                elif type == 1:
                    carddata = cw.binary.skill.SkillCard(None, f, True)
                elif type == 3:
                    carddata = cw.binary.beast.BeastCard(None, f, True)
                else:
                    raise ValueError(self.fname)
                card = BackpackCard(self, None)
                card.fname = carddata.name
                if type in (2, 3):
                    card.uselimit = carddata.limit
                else:
                    card.uselimit = 0
                # F9で戻るカードかどうかはレアリティの部分に格納されているため処理不要
                card.mine = True
                card.set_data(carddata)
                self.cards.append(card)

        # 対応する *.wpl
        self.wpl = None

        if 10 <= dataversion:
            # *.wplにもあるパーティの所持金(冒険中の現在値)
            self.money = f.dword()

            # ここから先はプレイ中のシナリオの状況が記録されている
            self.money_beforeadventure = f.dword() # 冒険前の所持金。冒険中でなければ0
            self.nowadventuring = f.bool()
            if self.nowadventuring: # 冒険中か
                _w = f.word() # 不明(0)
                self.scenariopath = f.rawstring() # シナリオ
                self.areaid = f.dword()
                self.steps = self.split_variables(f.rawstring(), True)
                self.flags = self.split_variables(f.rawstring(), False)
                self.friendcards = self.split_ids(f.rawstring())
                self.infocards = self.split_ids(f.rawstring())
                self.music = f.rawstring()
                bgimgs_num = f.dword()
                self.bgimgs = [bgimage.BgImage(self, f) for _cnt in xrange(bgimgs_num)]
        else:
            # 1.20以前では個人別に所持金があるためパーティの財布に集める
            self.money = 0
            for adv in self.adventurers:
                self.money += adv.adventurer.money
                adv.adventurer.money = 0
            self.money_beforeadventure = self.money # 1.20ではF9で所持金が戻らない

            self.nowadventuring = f.bool()
            if self.nowadventuring: #冒険中か
                self.scenariopath = u""
                summary = cw.binary.summary.Summary(None, f, True, wpt120=True)
                self.steps = {}.copy()
                for step in summary.steps:
                    self.steps[step.name] = step.default
                self.flags = {}.copy()
                for flag in summary.flags:
                    self.flags[flag.name] = flag.default
                self.scenariopath = f.rawstring() #シナリオ
                if not os.path.isabs(self.scenariopath):
                    dpath = os.path.dirname(os.path.dirname(os.path.dirname(f.name)))
                    self.scenariopath = cw.util.join_paths(dpath, self.scenariopath)
                self.areaid = f.dword()
                self.friendcards = []
                fcardnum = f.dword()
                for _i in xrange(fcardnum):
                    self.friendcards.append(f.dword())
                self.infocards = []
                infonum = f.dword()
                for _i in xrange(infonum):
                    self.infocards.append(f.dword())
                self.music = f.rawstring()
                bgimgs_num = f.dword()
                self.bgimgs = [bgimage.BgImage(self, f) for _cnt in xrange(bgimgs_num)]

    def split_variables(self, text, step):
        d = {}
        for l in text.splitlines():
            index = l.rfind('=')
            if index <> -1:
                if step:
                    d[l[:index]] = int(l[index+1:])
                else:
                    d[l[:index]] = bool(int(l[index+1:]))
        return d

    def split_ids(self, text):
        seq = []
        for l in text.splitlines():
            if l:
                seq.append(int(l))
        return seq

    def create_xml(self, dpath):
        """adventurercardだけxml化する。"""
        wpldata = self.wpl.get_data()
        me = wpldata.find("Property/Members")
        for adventurer in self.adventurers:
            path = adventurer.create_xml(dpath)
            text = cw.util.splitext(os.path.basename(path))[0]
            me.append(cw.data.make_element("Member", text))

    def create_vanisheds_xml(self, dpath):
        for adventurer in self.vanisheds:
            data = adventurer.get_data()
            data.find("Property").set("lost", "True")
            adventurer.create_xml(dpath)

    @staticmethod
    def join_variables(data):
        seq = []
        for e in data:
            name = e.text
            value = e.get("value")
            if value == "True":
                value = "1"
            elif value == "False":
                value = "0"
            seq.append(name + "=" + value)
        if seq:
            seq.append("")
        return "\r\n".join(seq)

    @staticmethod
    def join_ids(data):
        seq = []
        for e in data:
            if e.tag == "CastCard":
                seq.append(e.find("Property/Id").text)
            else:
                seq.append(e.text)
        if seq:
            seq.append("")
        return "\r\n".join(seq)

    @staticmethod
    def unconv(f, party, table, logdir):
        adventurers = []
        vanisheds = []
        cards = []
        money_beforeadventure = 0
        nowadventuring = False
        scenariopath = ""
        areaid = 0
        steps = ""
        flags = ""
        friendcards = ""
        infocards = ""
        music = ""
        bgimgs = []

        for member in party.members:
            adventurers.append(member.find("."))
        name = party.name

        if logdir:
            # プレイ中のシナリオの状況
            e_log = cw.data.xml2etree(cw.util.join_paths(logdir, "ScenarioLog.xml"))
            e_party = cw.data.xml2etree(cw.util.join_paths(logdir, "Party/Party.xml"))
            money_beforeadventure = e_party.getint("Property/Money", party.money)
            money_beforeadventure = cw.util.numwrap(money_beforeadventure, 0, 999999)
            nowadventuring = True
            scenariopath = e_log.gettext("Property/WsnPath", "")
            areaid = e_log.getint("Property/AreaId", 0)
            steps = PartyMembers.join_variables(e_log.getfind("Steps"))
            flags = PartyMembers.join_variables(e_log.getfind("Flags"))
            friendcards = PartyMembers.join_ids(e_log.getfind("CastCards"))
            infocards = PartyMembers.join_ids(e_log.getfind("InfoCards"))
            music = e_log.gettext("Property/MusicPath", "")
            if not music:
                music = e_log.gettext("Property/MusicPaths/MusicPath", "")
            bgimgs = e_log.find("BgImages")

            for e in e_log.getfind("LostAdventurers"):
                path = cw.util.join_yadodir(e.text)
                vanisheds.append(cw.data.xml2element(path))
            vanisheds.reverse()

        advnumpos = f.tell()
        advnum = 0
        f.write_byte(len(adventurers) + 30)
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(5) # 不明
        errorlog = []
        for i, member in enumerate(adventurers):
            if logdir:
                fpath = cw.util.join_paths(logdir, "Members", os.path.basename(member.fpath))
                logdata = cw.data.xml2element(fpath)
            else:
                logdata = None
            try:
                pos = f.tell()
                adventurer.AdventurerWithImage.unconv(f, member, logdata)
                if i + 1 < len(adventurers):
                    f.write_byte(0) # 不明
                advnum += 1
            except cw.binary.cwfile.UnsupportedError:
                f.seek(pos)
                if f.write_errorlog:
                    cardname = member.gettext("Property/Name", "")
                    s = u"%s の %s は対象エンジンで使用できないため、変換しません。\n" % (name, cardname)
                    errorlog.append(s)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                f.seek(pos)
                if f.write_errorlog:
                    cardname = member.gettext("Property/Name", "")
                    s = u"%s の %s は変換できませんでした。\n" % (name, cardname)
                    errorlog.append(s)

        if advnum == 0:
            s = u"%s は全メンバが変換に失敗したため、変換しません。\n" % (name)
            raise cw.binary.cwfile.UnsupportedError(s)

        if f.write_errorlog:
            for s in errorlog:
                f.write_errorlog(s)

        tell = f.tell()
        f.seek(advnumpos)
        f.write_byte(advnum + 30)
        f.seek(tell)

        vannumpos = f.tell()
        vannum = 0
        f.write_byte(len(vanisheds)) # 消滅メンバの数？
        if vanisheds:
            f.write_dword(0) # 不明
            for i, member in enumerate(vanisheds):
                if logdir:
                    fpath = cw.util.join_paths(logdir, "Members", os.path.basename(member.fpath))
                    logdata = cw.data.xml2element(fpath)
                else:
                    logdata = None
                try:
                    pos = f.tell()
                    adventurer.AdventurerWithImage.unconv(f, member, logdata)
                    if i + 1 < len(vanisheds):
                        f.write_byte(0) # 不明
                    vannum += 1
                except cw.binary.cwfile.UnsupportedError:
                    f.seek(pos)
                    if f.write_errorlog:
                        cardname = member.gettext("Property/Name", "")
                        s = u"%s の %s(消去前データ) は対象エンジンで使用できないため、変換しません。\n" % (name, cardname)
                        f.write_errorlog(s)
                except Exception:
                    cw.util.print_ex(file=sys.stderr)
                    f.seek(pos)
                    if f.write_errorlog:
                        cardname = member.gettext("Property/Name", "")
                        s = u"%s の %s(消去前データ) は変換できませんでした。\n" % (name, cardname)
                        f.write_errorlog(s)
            tell = f.tell()
            f.seek(vannumpos)
            f.write_byte(vannum)
            f.seek(tell)

        else:
            f.write_byte(0) # 不明
            f.write_byte(0) # 不明
            f.write_byte(0) # 不明
        f.write_string(name)

        backpacknumpos = f.tell()
        backpacknum = 0
        f.write_dword(len(party.backpack))
        btbl = table["yadocards"]
        # CardWirthでは削除されたカードはF9でも復活しないので変換不要
        for header in party.backpack:
            # バージョン不一致で不変換のデータもあるので所在チェック
            if header.fpath in btbl:
                fpath, data = btbl[header.fpath]
                scenariocard = cw.util.str2bool(data.get("scenariocard", "False"))
                cards.append(BackpackCard.unconv(f, data, fpath, not scenariocard))
                backpacknum += 1
        tell = f.tell()
        f.seek(backpacknumpos)
        f.write_dword(backpacknum)
        f.seek(tell)

        f.write_dword(cw.util.numwrap(party.money, 0, 999999)) # パーティの所持金(現在値)

        # プレイ中のシナリオの状況
        if nowadventuring:
            f.write_dword(money_beforeadventure)
            f.write_bool(nowadventuring)
            f.write_word(0) # 不明(0)
            f.write_rawstring(os.path.abspath(scenariopath))
            f.write_dword(areaid)
            f.write_rawstring(steps)
            f.write_rawstring(flags)
            f.write_rawstring(friendcards)
            f.write_rawstring(infocards)
            f.write_rawstring(music)
            f.write_dword(len(bgimgs))
            for bgimg in bgimgs:
                bgimage.BgImage.unconv(f, bgimg)
        else:
            f.write_dword(0)
            f.write_bool(False)

class BackpackCard(base.CWBinaryBase):
    """荷物袋に入っているカードのデータ。
    self.dataにwidファイルから読み込んだカードデータがある。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        if f:
            self.fname = f.rawstring()
            self.uselimit = f.dword()
            self.mine = f.bool()
        else:
            self.fname = u""
            self.uselimit = 0
            self.mine = False
        self.data = None

    def set_data(self, data):
        """widファイルから読み込んだカードデータを関連づける"""
        self.data = data

    def get_data(self):
        return self.data.get_data()

    def create_xml(self, dpath):
        """self.data.create_xml()"""
        self.data.limit = self.uselimit
        if not self.mine:
            self.data.set_image_export(False, True)
        data = self.data.get_data()
        if not self.mine:
            data.set("scenariocard", "True")
        return self.data.create_xml(dpath)

    @staticmethod
    def unconv(f, data, fname, mine):
        f.write_rawstring(cw.util.splitext(fname)[0])
        f.write_dword(data.getint("Property/UseLimit", 0))
        f.write_bool(mine)

def load_album120(parent, f):
    _dw = f.dword() # 不明
    cardnum = f.dword() # アルバム人数
    cards = []
    albums = []
    for _i in xrange(cardnum):
        card = cw.binary.adventurer.AdventurerCard(parent, None, True)
        card.fname = f.name
        card.adventurer = cw.binary.adventurer.Adventurer(card, f, True, album120=True)
        if card.adventurer.is_dead:
            albumdata = cw.binary.album.Album(parent, None, True)
            albumdata.name = card.adventurer.name
            albumdata.image = card.adventurer.image
            albumdata.level = card.adventurer.level
            albumdata.dex = card.adventurer.dex
            albumdata.agl = card.adventurer.agl
            albumdata.int = card.adventurer.int
            albumdata.str = card.adventurer.str
            albumdata.vit = card.adventurer.vit
            albumdata.min = card.adventurer.min
            albumdata.aggressive = card.adventurer.aggressive
            albumdata.cheerful = card.adventurer.cheerful
            albumdata.brave = card.adventurer.brave
            albumdata.cautious = card.adventurer.cautious
            albumdata.trickish = card.adventurer.trickish
            albumdata.avoid = card.adventurer.avoid
            albumdata.resist = card.adventurer.resist
            albumdata.defense = card.adventurer.defense
            albumdata.description = card.adventurer.description
            albumdata.coupons = card.adventurer.coupons

            albums.append(albumdata)
        else:
            cards.append(card)

    return cards, albums

def main():
    pass

if __name__ == "__main__":
    main()
