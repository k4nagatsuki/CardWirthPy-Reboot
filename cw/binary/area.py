#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import event
import bgimage


class Area(base.CWBinaryBase):
    """widファイルのエリアデータ。"""
    def __init__(self, parent, f, yadodata=False, nameonly=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = f.byte()
        f.dword() # 不明
        self.name = f.string()
        self.id = f.dword() % 10000
        if nameonly:
            return
        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.spreadtype = f.byte()
        mcards_num = f.dword()
        self.mcards = [MenuCard(self, f) for cnt in xrange(mcards_num)]
        bgimgs_num = f.dword()
        self.bgimgs = [bgimage.BgImage(self, f) for cnt in xrange(bgimgs_num)]

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "bgimgs": self.get_childrentext(self.bgimgs, indent + 2),
             "menucards": self.get_childrentext(self.mcards, indent + 2),
             "events": self.get_childrentext(self.events, indent + 2),
             "spreadtype": self.conv_spreadtype(self.spreadtype),
             "indent": self.get_indent(indent)
             }
        return d

class MenuCard(base.CWBinaryBase):
    """メニューカードのデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        f.byte() # 不明
        self.image = f.image()
        self.name = f.string()
        f.dword() # 不明
        self.description = f.string(True)
        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.flag = f.string()
        self.scale = f.dword()
        self.left = f.dword()
        self.top = f.dword()
        self.imgpath = f.string()

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "imgpath": self.get_materialpath(self.imgpath),
             "description": self.description,
             "flag": self.flag,
             "scale": self.scale,
             "left": self.left,
             "top": self.top,
             "events": self.get_childrentext(self.events, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
