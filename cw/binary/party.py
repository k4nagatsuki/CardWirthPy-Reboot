#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import adventurer


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

    def get_xmldict(self, indent):
        cards = []

        for card in self.cards:
            if card.mine:
                cards.append(card)
                # rootが違うデータのためディレクトリを設定しておく
                card.data.set_dir(self.get_dir())

        d = {"yadoname": self.yadoname,
             "name": self.name,
             "money": self.money,
             "nowadventuring": self.nowadventuring,
             "backpack": self.get_childrentext(cards, indent + 2),
             "indent": self.get_indent(indent)
             }

        # メンバー
        seq = [""]

        for member in self.memberslist:
            if member:
                s = "%s   <Member>%s</Member>" % (d["indent"], member)
                seq.append(s)

        d["members"] = "\n".join(seq)
        return d

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

    def create_xml(self, dpath):
        """self.data.create_xml()"""
        self.data.limit = self.uselimit
        return self.data.create_xml(dpath)

    def get_xmltext(self, indent):
        """self.data.get_xmltext()"""
        self.data.limit = self.uselimit
        s = self.data.get_xmltext(indent)
        return s

def main():
    pass

if __name__ == "__main__":
    main()
