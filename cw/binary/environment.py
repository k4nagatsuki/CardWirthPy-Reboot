#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

import cw.util


class Environment(base.CWBinaryBase):
    """Environment.wyd(type=-1)
    システム設定とかゴシップとか終了印とかいろいろまとめているデータ。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
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
        self.yadocards = [YadoCard(self, f) for cnt in range(yadocards_num)]
        self.money = f.dword()
        self.partyname = f.string()
        # スキンタイプ。読み込み後に操作する
        self.skintype = ""

    def get_cardtypedict(self):
        d = {}

        for card in self.yadocards:
            d[card.fname] = card.type

        return d

    def get_xmldict(self, indent):
        d = {"yadotype": self.conv_yadotype(self.yadotype),
             "skintype": self.skintype,
             "cashbox": self.money,
             "selectingparty": self.partyname,
             "playingscenario": self.scenarioname,
             "drawcardspeed": self.drawcard_speed,
             "drawbgspeed": self.drawbg_speed,
             "messagespeed": self.message_speed,
             "playbgm": self.play_bgm,
             "playsound": self.play_sound,
             "scaledown": self.correct_scaledown,
             "scaleup": self.correct_scaleup,
             "autoselectparty": self.autoselect_party,
             "getmoney": self.effect_getmoney,
             "clickcancel": self.clickcancel,
             "clickjump": self.clickjump,
             "keepmaxlevel": self.keep_levelmax,
             "bgeffectatselmode": self.bgeffectatselmode,
             "posterview": self.conv_yado_summaryview(self.viewtype_poster),
             "messagebgcolor": self.bgcolor_message,
             "usedecofont": self.use_decofont,
             "effectanimation": self.conv_yado_bgchange(self.changetype_bg),
             "indent": self.get_indent(indent)
             }

        # シナリオ終了印とゴシップ
        compstamps = []
        gossips = []

        for compstamp in cw.util.decodetextlist(self.compstamps):
            if compstamp:
                s = "%s  <CompleteStamp>%s</CompleteStamp>" % (d["indent"],
                                                                    compstamp)
                compstamps.append(s)

        for gossip in cw.util.decodetextlist(self.gossips):
            if gossip:
                s = "%s  <Gossip>%s</Gossip>" % (d["indent"], gossip)
                gossips.append(s)

        d["completestamps"] = "\n".join(compstamps)
        d["gossips"] = "\n".join(gossips)

        # 保管庫のカードのxml出力
        for unusedcard in self.unusedcards:
            unusedcard.create_xml(self.get_dir())

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

    def create_xml(self, dpath):
        """self.data.create_xml()"""
        self.data.limit = self.uselimit
        path = self.data.create_xml(dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_card(path, commit=False)
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
