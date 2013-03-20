#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import base
import adventurer

import cw


class Party(base.CWBinaryBase):
    """wplファイル(type=2)。パーティの見出しデータ。
    パーティの所持金や名前はここ。
    宿の画像も格納しているが必要ないと思うので破棄。
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
        self.money = f.dword()
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
            if card.mine:
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
    def unconv(f, data, table):
        yadoname = table["yadoname"]
        imgpath = "Resource/Image/Card/COMMAND0" + cw.cwpy.rsrc.ext_img
        imgpath = cw.util.join_paths(cw.cwpy.skindir, imgpath)
        image = base.CWBinaryBase.import_image(imgpath, fullpath=True)
        memberslist = ""
        name = ""
        money = 0
        nowadventuring = False

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
        dw = f.dword() # 不明。ランダムな値に見える。メモリ上のゴミ？
        self.adventurers = [adventurer.AdventurerWithImage(self, f)
                                        for cnt in xrange(adventurers_num)]
        vanisheds_num = f.byte()
        w = f.word() # 不明(0)
        self.vanisheds = [adventurer.AdventurerWithImage(self, f)
                                        for cnt in xrange(vanisheds_num)]
        self.name = f.string()
        # 荷物袋にあるカードリスト
        cards_num = f.dword()
        self.cards = [BackpackCard(self, f) for cnt in xrange(cards_num)]
        money = f.dword() # パーティの所持金(*.wplにもある)
        # 以降は存在を確信できないため読み込まない
        #dw = f.dword() # 不明(0)
        #dw = f.dword() # 不明(0)
        #b = f.byte() # 不明(0)

    def create_xml(self, dpath):
        """adventurercardだけxml化する。"""
        for adventurer in self.adventurers:
            adventurer.create_xml(dpath)

    @staticmethod
    def unconv(f, party, table):
        adventurers = []
        vanisheds = []
        name = ""
        cards = []

        for member in party.members:
            if member.getbool("Property", "lost", False):
                vanisheds.append(member.find("."))
            else:
                adventurers.append(member.find("."))
        name = party.name

        f.write_byte(len(adventurers) + 30)
        f.write_dword(0) # 不明
        for member in adventurers:
            adventurer.AdventurerWithImage.unconv(f, member)
        f.write_byte(len(vanisheds))
        f.write_word(0) # 不明
        for member in vanisheds:
            adventurer.AdventurerWithImage.unconv(f, member)
        f.write_string(name)
        f.write_dword(len(party.backpack) + len(party.backpack_moved))
        btbl = table["yadocards"]
        for header in party.backpack:
            fpath, data = btbl[header.fpath]
            cards.append(BackpackCard.unconv(f, data, fpath, True))
        for header in party.backpack_moved:
            fpath, data = btbl[header.fpath]
            cards.append(BackpackCard.unconv(f, data, fpath, False))
        f.write_dword(party.money) # パーティの所持金
        f.write_dword(0) # 不明(0)
        f.write_dword(0) # 不明(0)
        f.write_byte(0) # 不明(0)

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
