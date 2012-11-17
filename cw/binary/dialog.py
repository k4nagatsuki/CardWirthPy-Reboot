#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class Dialog(base.CWBinaryBase):
    """台詞データ"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.coupons = f.string()
        self.text = f.string(True)

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
