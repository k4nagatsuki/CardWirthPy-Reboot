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

    def unconv(self, f, data):
        pass # TODO

def main():
    pass

if __name__ == "__main__":
    main()
