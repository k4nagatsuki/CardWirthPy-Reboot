#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import base

import cw


class Environment(base.CWBinaryBase):
    """Environment.wyd(type=-1)
    システム設定とかゴシップとか終了印とかいろいろまとめているデータ。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = os.path.basename(os.path.dirname(self.fpath))
        self.type = -1
        self.dataversion = f.string()
        if self.dataversion.startswith("DATAVERSION_"):
            self.dataversion_int = int(self.dataversion[len("DATAVERSION_"):])
        else:
            self.dataversion_int = 0
        self.dataversion_int
        self.yadotype = f.byte()
        self.drawcard_speed = f.dword()
        self.drawbg_speed = f.dword()
        self.message_speed = f.dword()
        self.play_bgm = f.bool()
        self.play_sound = f.bool()
        self.correct_scaledown = f.bool()
        self.correct_scaleup = f.bool()
        self.autoselect_party = f.bool()
        self.clickcancel = f.bool()
        self.effect_getmoney = f.bool()
        self.clickjump = f.bool()
        self.keep_levelmax = f.bool()
        if 11 <= self.dataversion_int:
            self.bgeffectatselmode = f.bool()
        else:
            self.bgeffectatselmode = True
        self.viewtype_poster = f.byte()
        self.bgcolor_message = f.dword()
        self.use_decofont = f.bool()
        self.changetype_bg = f.byte()
        self.compstamps = f.string()
        self.scenarioname = f.string()
        self.gossips = f.string()
        unusedcards_num = f.dword()
        self.unusedcards = [UnusedCard(self, f)
                                    for cnt in xrange(unusedcards_num)]
        yadocards_num = f.dword()
        self.yadocards = [YadoCard(self, f) for cnt in xrange(yadocards_num)]
        self.money = f.dword()
        self.partyname = f.string()
        # スキンタイプ。読み込み後に操作する
        self.skintype = ""
        # データの取得に失敗したカード。変換時に追加する
        self.errorcards = []

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Environment")

            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("Type", self.skintype)
            prop.append(e)
            e = cw.data.make_element("Cashbox", str(self.money))
            prop.append(e)
            e = cw.data.make_element("NowSelectingParty", self.scenarioname)
            prop.append(e)
            self.data.append(prop)

            e = cw.data.make_element("CompleteStamps")
            for compstamp in cw.util.decodetextlist(self.compstamps):
                e.append(cw.data.make_element("CompleteStamp", compstamp))
            self.data.append(e)

            e = cw.data.make_element("Gossips")
            for gossip in cw.util.decodetextlist(self.gossips):
                e.append(cw.data.make_element("Gossip", gossip))
            self.data.append(e)

            # 保管庫のカードのxml出力
            self.errorcards = []
            for i, unusedcard in enumerate(self.unusedcards):
                if unusedcard.data:
                    unusedcard.create_xml2(self.get_dir(), cardorder=i)
                else:
                    self.errorcards.append(unusedcard)

        return self.data

    def get_cardtypedict(self):
        d = {}

        for card in self.yadocards:
            d[card.fname] = card.type

        return d

class UnusedCard(base.CWBinaryBase):
    """カード置き場のカードのデータ。
    self.dataにwidファイルから読み込んだカードデータがある。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.fname = f.rawstring()
        self.uselimit = f.dword()
        f.byte()
        self.data = None

    def set_data(self, data):
        """widファイルから読み込んだカードデータを関連づける"""
        self.data = data

    def get_data(self):
        return self.data.get_data()

    def create_xml(self, dpath):
        return self.create_xml2(dpath, -1)

    def create_xml2(self, dpath, cardorder):
        """self.data.create_xml()"""
        self.data.limit = self.uselimit
        path = self.data.create_xml(dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_card(path, commit=False, cardorder=cardorder)
        return path

class YadoCard(base.CWBinaryBase):
    """カード置き場のカードと荷物袋のカードのデータ。
    ここのtypeで宿にあるカードのタイプ(技能・アイテム・召喚獣)を判別できる。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        f.byte()
        f.byte()
        self.name = f.string()
        self.description = f.string()
        self.type = f.byte()
        self.fname = f.rawstring()
        self.number = f.dword() # 個数

def main():
    pass

if __name__ == "__main__":
    main()
