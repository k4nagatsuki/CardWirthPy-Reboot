#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class BgImage(base.CWBinaryBase):
    """背景のセルデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.left = f.dword()
        self.top = f.dword()
        self.width = f.dword()
        if self.width <= 39999:
            dataversion = 2
        else:
            dataversion = 4
            self.width -= 40000
        self.height = f.dword()
        self.imgpath = f.string()
        self.mask = f.bool()
        if 2 < dataversion:
            self.flag = f.string()
            self.unknown = f.byte()
        else:
            self.flag = ""
            self.unknown = 0

    def get_xmldict(self, indent):
        d = {"mask": self.mask,
             "flag": self.flag,
             "left": self.left,
             "top": self.top,
             "width": self.width,
             "height": self.height,
             "imgpath": self.get_materialpath(self.imgpath),
             "indent": self.get_indent(indent),
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
