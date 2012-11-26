#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import content


class Event(base.CWBinaryBase):
    """イベント発火条件付のイベントデータのクラス。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        contents_num = f.dword()
        self.contents = [content.Content(self, f)
                                            for cnt in xrange(contents_num)]
        ignitions_num = f.dword()
        self.ignitions = [f.dword() for cnt in xrange(ignitions_num)]
        self.keycodes = f.string()

    def get_xmldict(self, indent):
        d = {"keycodes": self.keycodes,
             "ignitions": cw.util.encodetextlist([str(i) for i in self.ignitions])
                                                    if self.ignitions else "",
             "contents": self.get_childrentext(self.contents, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

class SimpleEvent(base.CWBinaryBase):
    """イベント発火条件なしのイベントデータのクラス。
    カードイベント・パッケージ等で使う。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        contents_num = f.dword()
        self.contents = [content.Content(self, f)
                                            for cnt in xrange(contents_num)]

    def get_xmldict(self, indent):
        d = {"contents": self.get_childrentext(self.contents, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
