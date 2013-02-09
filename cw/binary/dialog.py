#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree

import base

import cw


class Dialog(base.CWBinaryBase):
    """台詞データ"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.coupons = f.string()
        self.text = f.string(True)

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Dialog")
            e = cw.data.make_element("RequiredCoupons", self.coupons)
            self.data.append(e)
            e = cw.data.make_element("Text", self.text)
            self.data.append(e)
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

    def get_xmldict(self, indent):
        d = {"coupons": self.coupons,
             "text": self.text,
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
