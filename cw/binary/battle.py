#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import event


class Battle(base.CWBinaryBase):
    """widファイルのバトルデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = f.byte()
        f.dword() # 不明
        self.name = f.string()
        self.id = f.dword() % 10000
        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.spreadtype = f.byte()
        ecards_num = f.dword()
        self.ecards = [EnemyCard(self, f) for cnt in xrange(ecards_num)]
        self.bgm = f.string()

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "bgm": self.get_materialpath(self.bgm),
             "enemycards": self.get_childrentext(self.ecards, indent + 2),
             "events": self.get_childrentext(self.events, indent + 2),
             "spreadtype": self.conv_spreadtype(self.spreadtype),
             "indent": self.get_indent(indent)
             }
        return d

class EnemyCard(base.CWBinaryBase):
    """エネミーカード。
    主要なデータはキャストカードを参照する。
    escape:逃走フラグ(真偽値)。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.cast_id = f.dword()
        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.flag = f.string()
        self.scale = f.dword()
        self.left = f.dword()
        self.top = f.dword()
        self.escape = f.bool()

    def get_xmldict(self, indent):
        d = {"castid": self.cast_id,
             "flag": self.flag,
             "scale": self.scale,
             "left": self.left,
             "top": self.top,
             "escape": self.escape,
             "events": self.get_childrentext(self.events, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
