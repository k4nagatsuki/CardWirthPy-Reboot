#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree

import base
import content

import cw


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

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Event")
            e = cw.data.make_element("Ignitions")
            e.append(cw.data.make_element("Number", cw.util.encodetextlist([str(i) for i in self.ignitions])
                                                    if self.ignitions else ""))
            e.append(cw.data.make_element("KeyCodes", self.keycodes))
            self.data.append(e)
            e = cw.data.make_element("Contents")
            for content in self.contents:
                e.append(content.get_data())
            self.data.append(e)
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

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

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Event")
            e = cw.data.make_element("Contents")
            for content in self.contents:
                e.append(content.get_data())
            self.data.append(e)
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

    def get_xmldict(self, indent):
        d = {"contents": self.get_childrentext(self.contents, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
