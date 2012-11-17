#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class Coupon(base.CWBinaryBase):
    """クーポンデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.value = f.dword()

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
