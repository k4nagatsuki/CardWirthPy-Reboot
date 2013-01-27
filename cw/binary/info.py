#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base


class InfoCard(base.CWBinaryBase):
    """widファイルの情報カードのデータ。"""
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = f.byte()
        self.image = f.image()
        self.name = f.string()
        idl = f.dword()

        if idl < 19999:
            dataversion = 0
            self.id = idl
        elif idl < 39999:
            dataversion = 2
            self.id = idl - 20000
        else:
            dataversion = 4
            self.id = idl - 40000

        if nameonly:
            return

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
