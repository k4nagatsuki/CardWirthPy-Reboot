#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class Summary(base.CWBinaryBase):
    """見出しデータ(Summary.wsm)。
    type:見出しデータには"-1"の値を付与する。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = -1
        self.image = f.image()
        self.name = f.string()
        if nameonly:
            return
        self.description = f.string()
        self.author = f.string()
        self.required_coupons = f.string()
        self.required_coupons_num = f.dword()
        self.area_id = f.dword()
        self.version = self.area_id / 10000
        self.area_id %= 10000
        steps_num = f.dword()
        self.steps = [Step(self, f) for cnt in xrange(steps_num)]
        flags_num = f.dword()
        self.flags = [Flag(self, f) for cnt in xrange(flags_num)]
        f.dword() # 不明
        self.level_min = f.dword()
        self.level_max = f.dword()
        # タグとスキンタイプ。読み込みが終わった後から操作する
        self.skintype = ""
        self.tags = ""

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "author": self.author,
             "description": self.description,
             "levelmin": self.level_min,
             "levelmax": self.level_max,
             "required_coupons": self.required_coupons,
             "required_coupons_num": self.required_coupons_num,
             "startarea_id": self.area_id,
             "labels": "",
             "tags": self.tags,
             "skintype": self.skintype,
             "flags": self.get_childrentext(self.flags, indent + 2),
             "steps": self.get_childrentext(self.steps, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

class Step(base.CWBinaryBase):
    """ステップ定義。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.default = f.dword()
        self.variable_names = [f.string() for cnt in xrange(10)]

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "default": self.default,
             "valname0": self.variable_names[0],
             "valname1": self.variable_names[1],
             "valname2": self.variable_names[2],
             "valname3": self.variable_names[3],
             "valname4": self.variable_names[4],
             "valname5": self.variable_names[5],
             "valname6": self.variable_names[6],
             "valname7": self.variable_names[7],
             "valname8": self.variable_names[8],
             "valname9": self.variable_names[9],
             "indent": self.get_indent(indent)
             }
        return d

class Flag(base.CWBinaryBase):
    """フラグ定義。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.default = f.bool()
        self.variable_names = [f.string() for cnt in xrange(2)]

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "default": self.default,
             "valname0": self.variable_names[0],
             "valname1": self.variable_names[1],
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
