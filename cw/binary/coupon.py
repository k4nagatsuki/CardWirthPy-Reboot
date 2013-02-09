#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree

import base

import cw


class Coupon(base.CWBinaryBase):
    """クーポンデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.value = f.dword()

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Coupon", self.name)
            self.data.set("value", str(self.value))
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "value": self.value,
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
