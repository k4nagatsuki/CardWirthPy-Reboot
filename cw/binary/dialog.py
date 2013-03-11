#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    def unconv(self, f, data):
        pass # TODO

def main():
    pass

if __name__ == "__main__":
    main()
