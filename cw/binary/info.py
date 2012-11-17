#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class InfoCard(base.CWBinaryBase):
    """widファイルの情報カードのデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = f.byte()
        self.image = f.image()
        self.name = f.string()
        self.id = f.dword() % 10000
        self.description = f.string(True)

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "id": self.id,
             "description": self.description,
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
