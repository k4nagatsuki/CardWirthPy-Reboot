#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import beast

import cw


class EffectMotion(base.CWBinaryBase):
    """効果モーションのデータ。
    効果コンテントやスキル・アイテム・召喚獣カード等で使う。
    """
    def __init__(self, parent, f, yadodata=False, dataversion=4):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.tabtype = f.byte()

        if 2 < dataversion:
            # 不明なバイト列(8,5,0,0,0)。読み飛ばし。
            for _cnt in xrange(5):
                _b = f.byte()

        self.element = f.byte()

        # 大分類が召喚の場合は、byteを読み込まない。
        if self.tabtype == 8:
            self.type = 0
        else:
            self.type = f.byte()

        # 初期化
        self.properties = {}
        self.beasts = None

        # 生命力, 肉体
        if self.tabtype in (0, 1):
            s = self.conv_effectmotion_damagetype(f.byte())
            self.properties["damagetype"] = s
            self.properties["value"] = f.dword()
        # 精神, 魔法
        elif self.tabtype in (3, 4):
            if 2 < dataversion:
                self.properties["duration"] = f.dword()
            else:
                self.properties["duration"] = 10
        # 能力
        elif self.tabtype == 5:
            self.properties["value"] = f.dword()
            if 2 < dataversion:
                self.properties["duration"] = f.dword()
            else:
                self.properties["duration"] = 10
        # 技能, 消滅, カード
        elif self.tabtype in (2, 6, 7):
            pass
        # 召喚(BeastCardインスタンスを生成)
        elif self.tabtype == 8:
            beasts_num = f.dword()
            self.beasts = [beast.BeastCard(self, f, summoneffect=True)
                                            for _cnt in xrange(beasts_num)]
        else:
            raise ValueError(self.fpath)

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Motion")
            self.data.set("type", self.conv_effectmotion_type(self.tabtype, self.type))
            self.data.set("element", self.conv_effectmotion_element(self.element))
            for key, value in self.properties.iteritems():
                if isinstance(value, (str, unicode)):
                    self.data.set(key, value)
                else:
                    self.data.set(key, str(value))
            if self.beasts:
                e = cw.data.make_element("Beasts")
                for beast in self.beasts:
                    e.append(beast.get_data())
                self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        tabtype, mtype = base.CWBinaryBase.unconv_effectmotion_type(data.get("type"), f)
        element = base.CWBinaryBase.unconv_effectmotion_element(data.get("element"))

        f.write_byte(tabtype)

        # 不明なバイト列
        f.write_byte(8)
        f.write_byte(5)
        f.write_byte(0)
        f.write_byte(0)
        f.write_byte(0)

        f.write_byte(element)

        # 大分類が召喚の場合は、typeを飛ばす
        if tabtype <> 8:
            f.write_byte(mtype)

        # 生命力, 肉体
        if tabtype in (0, 1):
            f.write_byte(base.CWBinaryBase.unconv_effectmotion_damagetype(data.get("damagetype")))
            f.write_dword(int(data.get("value", "0")))
        # 精神, 魔法
        elif tabtype in (3, 4):
            f.write_dword(int(data.get("duration", "10")))
        # 能力
        elif tabtype == 5:
            f.write_dword(int(data.get("value", "0")))
            f.write_dword(int(data.get("duration", "10")))
        # 技能
        elif tabtype == 2:
            if not data.get("damagetype", "Max") in ("", "Max"):
                f.check_wsnversion("1")
        # 消滅, カード
        elif tabtype in (6, 7):
            pass
        # 召喚(BeastCardインスタンスを生成)
        elif tabtype == 8:
            beasts = []
            for e in data:
                if e.tag == "Beasts":
                    beasts = e
            f.write_dword(len(beasts))
            for card in beasts:
                beast.BeastCard.unconv(f, card, False)
        else:
            raise ValueError(tabtype)

def main():
    pass

if __name__ == "__main__":
    main()
