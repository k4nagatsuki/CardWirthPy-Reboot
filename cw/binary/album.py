#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import coupon


class Album(base.CWBinaryBase):
    """wrmファイル(type=4)。鬼籍に入った冒険者のデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 4
        self.fname = self.get_fname()
        f.byte()
        f.byte()
        self.name = f.string()
        self.image = f.image()
        self.level = f.word()
        f.word() # 不明
        f.word() # 不明
        f.word() # 不明
        # ここからは16ビット符号付き整数が並んでると思われるが面倒なので
        # 能力値
        self.dex = f.byte()
        f.byte()
        self.agl = f.byte()
        f.byte()
        self.int = f.byte()
        f.byte()
        self.str = f.byte()
        f.byte()
        self.vit = f.byte()
        f.byte()
        self.min = f.byte()
        f.byte()
        # 性格値
        self.aggressive = f.byte()
        f.byte()
        self.cheerful = f.byte()
        f.byte()
        self.brave = f.byte()
        f.byte()
        self.cautious = f.byte()
        f.byte()
        self.trickish = f.byte()
        f.byte()
        # 修正能力値
        self.avoid = f.byte()
        f.byte()
        self.resist = f.byte()
        f.byte()
        self.defense = f.byte()
        f.byte()
        f.dword()
        self.description = f.string().replace("TEXT\\n", "", 1)
        # クーポン
        coupons_num = f.dword()
        self.coupons = [coupon.Coupon(self, f) for cnt in xrange(coupons_num)]

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "description": self.description,
             "level": self.level,
             "dex": self.dex,
             "agl": self.agl,
             "int": self.int,
             "str": self.str,
             "vit": self.vit,
             "min": self.min,
             "aggressive": self.aggressive,
             "cheerful": self.cheerful,
             "brave": self.brave,
             "cautious": self.cautious,
             "trickish": self.trickish,
             "avoid": self.avoid,
             "resist": self.resist,
             "defense": self.defense,
             "coupons": self.get_childrentext(self.coupons, indent + 3),
             "indent": self.get_indent(indent)
             }
        return d

    def create_xml(self, dpath):
        path = base.CWBinaryBase.create_xml(self, dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_adventurer(path, album=True, commit=False)
        return path

def main():
    pass

if __name__ == "__main__":
    main()
