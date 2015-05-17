#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import base

import cw

_120gene = re.compile(ur"\A＠Ｇ[01]{10}-[0-9]+\Z")

class Coupon(base.CWBinaryBase):
    """クーポンデータ。"""
    def __init__(self, parent, f, yadodata=False, dataversion=5):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        if f:
            self.name = f.string()
            self.value = f.dword()
            if dataversion <= 4:
                if _120gene.match(self.name):
                    self.value = int(self.name[13:])
                    self.name = self.name[:12]
        else:
            self.name = ""
            self.value = 0

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Coupon", self.name)
            self.data.set("value", str(self.value))
        return self.data

    @staticmethod
    def unconv(f, data):
        name = data.text
        value = int(data.get("value"))

        f.write_string(name)
        f.write_dword(value)

def main():
    pass

if __name__ == "__main__":
    main()
