#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import base
import adventurer

import cw
import bgimage


class Party(base.CWBinaryBase):
    """wplファイル(type=2)。パーティの見出しデータ。
    パーティの所持金や名前はここ。
    宿の画像も格納しているが必要ないと思うので破棄。
    F9のためにゴシップと終了印を記憶しているような事は無い
    (その2つはF9で戻らない)。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 2
        self.fname = self.get_fname()
        w = f.word() # 不明(0)
        self.yadoname = f.string()
        f.image() # 宿の埋め込み画像は破棄。
        self.memberslist = cw.util.decodetextlist(f.string())
        self.name = f.string()
        self.money = f.dword() # 冒険中の現在値
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
            for member in self.memberslist:
                me.append(cw.data.make_element("Member", member))
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
        imgpath = "Resource/Image/Card/COMMAND0" + cw.cwpy.rsrc.ext_img
        imgpath = cw.util.join_paths(cw.cwpy.skindir, imgpath)
        image = base.CWBinaryBase.import_image(imgpath, fullpath=True)
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
                    elif prop.tag == "Members":
                        atbl = table["adventurers"]
                        seq = []
                        for me in prop:
                            if me.tag == "Member" and me.text:
                                seq.append(atbl[me.text])
                        memberslist = cw.util.encodetextlist(seq)

        f.write_word(0) # 不明
        f.write_string(yadoname)
        f.write_image(image)
        f.write_string(memberslist)
        f.write_string(name)
        f.write_dword(money)
        f.write_bool(nowadventuring)

class PartyMembers(base.CWBinaryBase):
    """wptファイル(type=3)。パーティメンバと
    荷物袋に入っているカードリストを格納している。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 3
        self.fname = self.get_fname()
        adventurers_num = f.byte() - 30
        b = f.byte() # 不明(0)
        b = f.byte() # 不明(0)
        b = f.byte() # 不明(0)
        b = f.byte() # 不明(5)
        self.adventurers = []
        vanisheds_num = 0
        for i in xrange(adventurers_num):
            self.adventurers.append(adventurer.AdventurerWithImage(self, f))
            vanisheds_num = f.byte() # 最後のメンバが消滅メンバの数を持っている？
        self.vanisheds = []
        if 0 < vanisheds_num:
            dw = f.dword() # 不明(0)
            for i in xrange(vanisheds_num):
                self.vanisheds.append(adventurer.AdventurerWithImage(self, f))
                if i + 1 < vanisheds_num:
                    b = f.byte()
            self.vanisheds.reverse()
        else:
            b = f.byte() # 不明(0)
            b = f.byte() # 不明(0)
            b = f.byte() # 不明(0)
        self.name = f.string()
        # 荷物袋にあるカードリスト
        cards_num = f.dword()
        self.cards = [BackpackCard(self, f) for cnt in xrange(cards_num)]
        # *.wplにもあるパーティの所持金(冒険中の現在値)
        money = f.dword()

        # ここから先はプレイ中のシナリオの状況が記録されている
        self.money_beforeadventure = f.dword() # 冒険前の所持金。冒険中でなければ0
        self.nowadventuring = f.bool()
        if self.nowadventuring: # 冒険中か
            w = f.word() # 不明(0)
            self.scenariopath = f.rawstring() # シナリオ
            self.areaid = f.dword()
            self.steps = self.split_variables(f.rawstring(), True)
            self.flags = self.split_variables(f.rawstring(), False)
            self.friendcards = self.split_ids(f.rawstring())
            self.infocards = self.split_ids(f.rawstring())
            self.music = f.rawstring()
            bgimgs_num = f.dword()
            self.bgimgs = [bgimage.BgImage(self, f) for cnt in xrange(bgimgs_num)]

    def split_variables(self, str, step):
        d = {}
        for l in str.splitlines():
            index = -1
            for i, c in enumerate(l):
                if c == '=':
                    index = i
                    break
            if index <> -1:
                if step:
                    d[l[:index]] = int(l[index+1:])
                else:
                    d[l[:index]] = bool(int(l[index+1:]))
        return d

    def split_ids(self, str):
        seq = []
        for l in str.splitlines():
            if l:
                seq.append(int(l))
        return seq

    def create_xml(self, dpath):
        """adventurercardだけxml化する。"""
        for adventurer in self.adventurers:
            adventurer.create_xml(dpath)

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
        name = ""
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
            nowadventuring = True
            scenariopath = e_log.gettext("Property/WsnPath", "")
            areaid = e_log.getint("Property/AreaId", 0)
            steps = PartyMembers.join_variables(e_log.getfind("Steps"))
            flags = PartyMembers.join_variables(e_log.getfind("Flags"))
            friendcards = PartyMembers.join_ids(e_log.getfind("CastCards"))
            infocards = PartyMembers.join_ids(e_log.getfind("InfoCards"))
            music = e_log.gettext("Property/MusicPath", "")
            bgimgs = e_log.find("BgImages")

            for e in e_log.getfind("LostAdventurers"):
                path = cw.util.join_yadodir(e.text)
                vanisheds.append(cw.data.xml2element(path))
            vanisheds.reverse()

        f.write_byte(len(adventurers) + 30)
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(5) # 不明
        for i, member in enumerate(adventurers):
            if logdir:
                fpath = cw.util.join_paths(logdir, "Members", os.path.basename(member.fpath))
                logdata = cw.data.xml2element(fpath)
            else:
                logdata = None
            adventurer.AdventurerWithImage.unconv(f, member, logdata)
            if i + 1 < len(adventurers):
                f.write_byte(0) # 不明
            else:
                f.write_byte(len(vanisheds)) # 消滅メンバの数？
        if vanisheds:
            f.write_dword(0) # 不明
            for i, member in enumerate(vanisheds):
                if logdir:
                    fpath = cw.util.join_paths(logdir, "Members", os.path.basename(member.fpath))
                    logdata = cw.data.xml2element(fpath)
                else:
                    logdata = None
                adventurer.AdventurerWithImage.unconv(f, member, logdata)
                if i + 1 < len(vanisheds):
                    f.write_byte(0) # 不明
        else:
            f.write_byte(0) # 不明
            f.write_byte(0) # 不明
            f.write_byte(0) # 不明
        f.write_string(name)
        f.write_dword(len(party.backpack))
        btbl = table["yadocards"]
        # CardWirthでは削除されたカードはF9でも復活しないので変換不要
        for header in party.backpack:
            fpath, data = btbl[header.fpath]
            scenariocard = cw.util.str2bool(data.get("scenariocard", "False"))
            cards.append(BackpackCard.unconv(f, data, fpath, not scenariocard))
        f.write_dword(party.money) # パーティの所持金(現在値)

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
        self.fname = f.rawstring()
        self.uselimit = f.dword()
        self.mine = f.bool()
        self.data = None

    def set_data(self, data):
        """widファイルから読み込んだカードデータを関連づける"""
        self.data = data
        data = self.data.get_data()
        if not self.mine:
            data.set("scenariocard", "True")
            self.data.set_image_export(False, True)

    def get_data(self):
        return self.data.get_data()

    def create_xml(self, dpath):
        """self.data.create_xml()"""
        self.data.limit = self.uselimit
        return self.data.create_xml(dpath)

    @staticmethod
    def unconv(f, data, fname, mine):
        f.write_rawstring(os.path.splitext(fname)[0])
        f.write_dword(int(data.findtext("Property/UseLimit", "0")))
        f.write_bool(mine)

def main():
    pass

if __name__ == "__main__":
    main()
