#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

import cw


class InfoCard(base.CWBinaryBase):
    """widファイルの情報カードのデータ。"""
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = f.byte()
        self.image = f.image()
        self.name = f.string()
        idl = f.dword()

        if idl <= 19999:
            _dataversion = 0
            self.id = idl
        elif idl <= 39999:
            _dataversion = 2
            self.id = idl - 20000
        else:
            _dataversion = 4
            self.id = idl - 40000

        if nameonly:
            return

        self.description = f.string(True)

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""
            self.data = cw.data.make_element("InfoCard")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            self.data.append(prop)
        return self.data

    @staticmethod
    def unconv(f, data):
        restype = 4
        image = None
        name = ""
        resid = 0
        description = ""

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        resid = int(prop.text)
                    elif prop.tag == "Name":
                        name = prop.text
                    elif prop.tag in ("ImagePath", "ImagePaths"):
                        image = base.CWBinaryBase.import_image(f, prop)
                    elif prop.tag == "Description":
                        description = prop.text

        f.write_byte(restype)
        f.write_image(image)
        f.write_string(name)
        f.write_dword(resid + 40000)
        f.write_string(description, True)

def main():
    pass

if __name__ == "__main__":
    main()
