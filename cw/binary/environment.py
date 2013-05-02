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
        # CardWirthPyにおける選択中パーティ
        # パーティ変換後に操作する
        self.cwpypartyname = ""
        # スキンタイプ。読み込み後に操作する
        self.skintype = ""
        # スキンディレクトリ。現在の設定を使用
        self.skinname = cw.cwpy.setting.skinname
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
            e = cw.data.make_element("Skin", self.skinname)
            prop.append(e)
            e = cw.data.make_element("Cashbox", str(self.money))
            prop.append(e)
            e = cw.data.make_element("NowSelectingParty", self.cwpypartyname)
            prop.append(e)
            self.data.append(prop)

            e = cw.data.make_element("CompleteStamps")
            for compstamp in cw.util.decodetextlist(self.compstamps):
                if compstamp:
                    e.append(cw.data.make_element("CompleteStamp", compstamp))
            self.data.append(e)

            e = cw.data.make_element("Gossips")
            for gossip in cw.util.decodetextlist(self.gossips):
                if gossip:
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

    @staticmethod
    def unconv(f, data, table):
        yadotype = 1 # 常に通常宿とする
        drawcard_speed = 4 # 標準値
        drawbg_speed = 4 # 標準値
        message_speed = 4 # 標準値
        play_bgm = True
        play_sound = True
        correct_scaledown = True
        correct_scaleup = True
        autoselect_party = True
        clickcancel = True
        effect_getmoney = True
        clickjump = True
        keep_levelmax = True
        viewtype_poster = 1
        bgcolor_message = 3
        use_decofont = False
        changetype_bg = 1
        compstamps = ""
        scenarioname = ""
        gossips = ""
        money = 0
        partyname = ""

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Cashbox":
                        money = int(prop.text)
                    elif prop.tag == "NowSelectingParty":
                        partyname = table["party"].get(prop.text, "")
            elif e.tag == "CompleteStamps":
                seq = []
                for cse in e:
                    if cse.text:
                        seq.append(cse.text)
                compstamps = cw.util.encodetextlist(seq)
            elif e.tag == "Gossips":
                seq = []
                for ge in e:
                    if ge.text:
                        seq.append(ge.text)
                gossips = cw.util.encodetextlist(seq)

        f.write_string("DATAVERSION_10")
        f.write_byte(yadotype)
        f.write_dword(drawcard_speed)
        f.write_dword(drawbg_speed)
        f.write_dword(message_speed)
        f.write_bool(play_bgm)
        f.write_bool(play_sound)
        f.write_bool(correct_scaledown)
        f.write_bool(correct_scaleup)
        f.write_bool(autoselect_party)
        f.write_bool(clickcancel)
        f.write_bool(effect_getmoney)
        f.write_bool(clickjump)
        f.write_bool(keep_levelmax)
        f.write_byte(viewtype_poster)
        f.write_dword(bgcolor_message)
        f.write_bool(use_decofont)
        f.write_byte(changetype_bg)
        f.write_string(compstamps)
        f.write_string(scenarioname)
        f.write_string(gossips)
        unusedcards = table["unusedcards"]
        f.write_dword(len(unusedcards))
        for fname, card in unusedcards:
            UnusedCard.unconv(f, card, fname)
        yadocards = table["yadocards"]
        f.write_dword(len(yadocards))
        for fname, card in yadocards.values():
            YadoCard.unconv(f, card, fname)
        f.write_dword(money)
        f.write_string(partyname)

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

    @staticmethod
    def unconv(f, data, fname):
        f.write_rawstring(os.path.splitext(fname)[0])
        f.write_dword(int(data.findtext("Property/UseLimit", "0")))
        f.write_byte(0)

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

    @staticmethod
    def unconv(f, data, fname):
        name = data.findtext("Property/Name", "")
        description = data.findtext("Property/Description", "")
        if data.tag == "SkillCard":
            type = 1
        elif data.tag == "ItemCard":
            type = 2
        elif data.tag == "BeastCard":
            type = 3
        number = 1

        f.write_byte(0)
        f.write_byte(0)
        f.write_string(name)
        f.write_string(description)
        f.write_byte(type)
        f.write_rawstring(os.path.splitext(fname)[0])
        f.write_dword(number)

def main():
    pass

if __name__ == "__main__":
    main()
