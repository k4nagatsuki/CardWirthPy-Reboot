#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import event


class Package(base.CWBinaryBase):
    """widファイルの情報カードのデータ。
    type:InfoCardと区別が付くように、Packageは暫定的に"7"とする。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 7
        f.dword() # 不明
        self.name = f.string()
        self.id = f.dword()
        if nameonly:
            return
        events_num = f.dword()
        self.events = [event.SimpleEvent(self, f) for cnt in xrange(events_num)]

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "events": self.get_childrentext(self.events, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
