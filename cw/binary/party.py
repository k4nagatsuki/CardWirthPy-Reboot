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
        f.byte()
        f.byte()
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
                    path = card.create_xml(cdpath)
                    carddb.insert_card(path, commit=False, cardorder=order)
                    order += 1
                else:
                    self.errorcards.append(card)
        carddb.commit()
        carddb.close()

        return path

    @staticmethod
    def unconv(f, data):
        pass # TODO

class PartyMembers(base.CWBinaryBase):
    """wptファイル(type=3)。パーティメンバと
    荷物袋に入っているカードリストを格納している。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 3
        self.fname = self.get_fname()
        adventurers_num = f.byte() - 30
        f.dword()
        self.adventurers = [adventurer.AdventurerWithImage(self, f)
                                        for cnt in xrange(adventurers_num)]
        vanisheds_num = f.byte()
        f.byte()
        f.byte()
        self.vanisheds = [adventurer.AdventurerWithImage(self, f)
                                        for cnt in xrange(vanisheds_num)]
        self.name = f.string()
        # 荷物袋にあるカードリスト
        cards_num = f.dword()
        self.cards = [BackpackCard(self, f) for cnt in xrange(cards_num)]

    def create_xml(self, dpath):
        """adventurercardだけxml化する。"""
        for adventurer in self.adventurers:
            adventurer.create_xml(dpath)

    @staticmethod
    def unconv(f, data):
        pass # TODO

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
    def unconv(f, data):
        pass # TODO

def main():
    pass

if __name__ == "__main__":
    main()
