#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import beast


class EffectMotion(base.CWBinaryBase):
    """効果モーションのデータ。
    効果コンテントやスキル・アイテム・召喚獣カード等で使う。
    """
    def __init__(self, parent, f, yadodata=False, dataversion=4):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.tabtype = f.byte()

        if 2 < dataversion:
            # 不明なバイト列。読み飛ばし。
            for cnt in xrange(5):
                f.byte()

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
                                            for cnt in xrange(beasts_num)]
        else:
            raise ValueError(self.fpath)

    def get_xmldict(self, indent):
        d = {"type": self.conv_effectmotion_type(self.tabtype, self.type),
             "element": self.conv_effectmotion_element(self.element),
             "properties": self.get_propertiestext(self.properties),
             "children": " />",
             "indent": self.get_indent(indent),
             }

        if self.beasts:
            s1 = self.get_indent(indent + 1)
            s2 = self.get_childrentext(self.beasts, indent + 2)
            s3 = d["indent"]
            s = ">\n%s<Beasts>%s\n%s</Beasts>\n%s</Motion>" % (s1, s2, s1, s3)
            d["children"] = s

        return d

def main():
    pass

if __name__ == "__main__":
    main()
