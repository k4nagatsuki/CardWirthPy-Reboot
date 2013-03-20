#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

import cw


class BgImage(base.CWBinaryBase):
    """背景のセルデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.left = f.dword()
        self.top = f.dword()
        self.width = f.dword()
        if self.width <= 39999:
            dataversion = 2
        elif self.width <= 49999:
            dataversion = 4
            self.width -= 40000
        else:
            dataversion = 5
            self.width -= 50000
        self.height = f.dword()
        self.imgpath = f.string()
        self.mask = f.bool()
        if 2 < dataversion:
            self.flag = f.string()
            self.unknown = f.byte()
        else:
            self.flag = ""
            self.unknown = 0

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("BgImage")
            self.data.set("mask", str(self.mask))
            e = cw.data.make_element("ImagePath", self.imgpath)
            self.data.append(e)
            e = cw.data.make_element("Flag", self.flag)
            self.data.append(e)
            e = cw.data.make_element("Location")
            e.set("left", str(self.left))
            e.set("top", str(self.top))
            self.data.append(e)
            e = cw.data.make_element("Size")
            e.set("width", str(self.width))
            e.set("height", str(self.height))
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        left = 0
        top = 0
        width = 0
        height = 0
        imgpath = ""
        mask = cw.util.str2bool(data.get("mask"))
        flag = ""
        unknown = 0

        for e in data:
            if e.tag == "ImagePath":
                imgpath = e.text
            elif e.tag == "Flag":
                flag = e.text
            elif e.tag == "Location":
                left = int(e.get("left"))
                top = int(e.get("top"))
            elif e.tag == "Size":
                width = int(e.get("width"))
                height = int(e.get("height"))

        f.write_dword(left)
        f.write_dword(top)
        f.write_dword(width + 50000)
        f.write_dword(height)
        f.write_string(imgpath)
        f.write_bool(mask)
        f.write_string(flag)
        f.write_byte(unknown)

def main():
    pass

if __name__ == "__main__":
    main()
