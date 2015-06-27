#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import base

import cw


class Environment(base.CWBinaryBase):
    """Environment.wyd(type=-1)
    システム設定とかゴシップとか終了印とかいろいろまとめているデータ。
    """
    def __init__(self, parent, f, yadodata=False, versiononly=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = os.path.basename(os.path.dirname(self.fpath))
        self.type = -1
        self.dataversion = f.string()
        if self.dataversion.startswith("DATAVERSION_"):
            self.dataversion_int = int(self.dataversion[len("DATAVERSION_"):])
        else:
            self.dataversion_int = 0

        if versiononly:
            return

        self.yadotype = f.byte() # 宿タイプ(1:通常, 2:デバッグ)
        self.drawcard_speed = f.dword() # カード速度
        self.drawbg_speed = f.dword() # 背景速度
        self.message_speed = f.dword() # メッセージ速度
        self.play_bgm = f.bool() # BGM再生
        self.play_sound = f.bool() # 効果音再生
        if 10 <= self.dataversion_int:
            self.correct_scaledown = f.bool() # カードのスムージング(縮小)
            self.correct_scaleup = f.bool() # カードのスムージング(拡大)
        else:
            _b = f.bool() # レアリティのないカードも買い戻せるようにする
            _b = f.bool() # 売却・破棄時に確認メッセージの表示
        self.autoselect_party = f.bool() # 宿を開いた時に最後のパーティを選択
        self.clickcancel = f.bool() # 背景右クリックでキャンセル
        if 10 <= self.dataversion_int:
            self.effect_getmoney = f.bool() # 所持金増減時に点滅させる
            self.clickjump = f.bool() # 右クリックで待機時間を飛ばす
            self.keep_levelmax = f.bool() # レベルを最大値に維持する
        if 11 <= self.dataversion_int:
            self.bgeffectatselmode = f.bool() # 選択モードでカーテンをかける
        else:
            self.bgeffectatselmode = True
        self.viewtype_poster = f.byte() # 貼紙の表示条件
        self.bgcolor_message = f.dword() # メッセージ背景濃度
        self.use_decofont = f.bool() # 装飾フォントの使用
        self.changetype_bg = f.byte() # 背景切替方式
        self.compstamps = f.string(True) # 終了印のリスト
        self.scenarioname = f.string() # 選択中パーティのいるシナリオ名(用途不明)
        self.gossips = f.string(True) # ゴシップのリスト
        if 10 <= self.dataversion_int:
            # 1.28以降
            # カード置場のカードデータ
            unusedcards_num = f.dword()
            self.unusedcards = [UnusedCard(self, f)
                                        for _cnt in xrange(unusedcards_num)]
            # カード置場と荷物袋のカードヘッダ
            yadocards_num = f.dword()
            self.yadocards = [YadoCard(self, f) for _cnt in xrange(yadocards_num)]
            # 宿の資金
            self.money = f.dword()
        else:
            # 1.20
            self.unusedcards = []
            self.yadocards = []
            self.money = 0
        # 選択中のパーティ名
        self.partyname = f.string()

        # CardWirthPyにおける選択中パーティ
        # パーティ変換後に操作する
        self.cwpypartyname = ""
        # スキンタイプ。読み込み後に操作する
        self.skintype = ""
        # スキンディレクトリ。現在の設定を使用
        self.skinname = cw.cwpy.setting.skindirname
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
                    try:
                        unusedcard.create_xml2(self.get_dir(), cardorder=i)
                    except Exception:
                        cw.util.print_ex()
                        self.errorcards.append(unusedcard)
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

        # 設定を可能なだけ反映
        if cw.cwpy.setting.transition == "None":
            changetype_bg = 0
        elif cw.cwpy.setting.transition == "Blinds":
            changetype_bg = 1
        elif cw.cwpy.setting.transition == "Fade":
            changetype_bg = 2
        elif cw.cwpy.setting.transition == "PixelDissolve":
            changetype_bg = 3

        def roundval(value):
            return int(round((value-5) / 10.0 * 8.0)) + 4
        drawcard_speed = roundval(cw.cwpy.setting.get_dealspeed(False))
        drawbg_speed = roundval(cw.cwpy.setting.transitionspeed)
        message_speed = roundval(cw.cwpy.setting.messagespeed)

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Cashbox":
                        money = int(prop.text)
                        money = cw.util.numwrap(money, 0, 999999)
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
        f.write_string(compstamps, True)
        f.write_string(scenarioname)
        f.write_string(gossips, True)
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
        if f:
            self.fname = f.rawstring()
            self.uselimit = f.dword()
            f.byte()
        else:
            self.fname = ""
            self.uselimit = 0
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
        f.write_rawstring(cw.util.splitext(fname)[0])
        f.write_dword(data.getint("Property/UseLimit", 0))
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
        name = data.gettext("Property/Name", "")
        description = data.gettext("Property/Description", "")
        if data.tag == "SkillCard":
            restype = 1
        elif data.tag == "ItemCard":
            restype = 2
        elif data.tag == "BeastCard":
            restype = 3
        number = 1

        f.write_byte(0)
        f.write_byte(0)
        f.write_string(name)
        f.write_string(description, True)
        f.write_byte(restype)
        f.write_rawstring(cw.util.splitext(fname)[0])
        f.write_dword(number)

def main():
    pass

if __name__ == "__main__":
    main()
