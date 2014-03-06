#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
