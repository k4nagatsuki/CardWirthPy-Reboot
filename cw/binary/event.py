#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    @staticmethod
    def unconv(f, data):
        contents = []
        ignitions = []
        keycodes = ""

        for e in data:
            if e.tag == "Ignitions":
                for ig in e:
                    if ig.tag == "Number":
                        for num in cw.util.decodetextlist(ig.text):
                            ignitions.append(int(num))
                    elif ig.tag == "KeyCodes":
                        keycodes = ig.text
            elif e.tag == "Contents":
                contents = e

        f.write_dword(len(contents))
        for content in contents:
            content.Content.unconv(f, content)
        f.write_dword(len(ignitions))
        for ignition in ignitions:
            f.write_dword(ignition)
        f.write_string(keycodes)

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

    @staticmethod
    def unconv(f, data):
        contents = []

        for e in data:
            if e.tag == "Contents":
                contents = e

        f.write_dword(len(contents))
        for ct in contents:
            content.Content.unconv(f, ct)

def main():
    pass

if __name__ == "__main__":
    main()
