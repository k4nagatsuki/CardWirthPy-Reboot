#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree

import base
import event
import bgimage

import cw


class Area(base.CWBinaryBase):
    """widファイルのエリアデータ。"""
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = f.byte()

        # データバージョンによって処理を分岐する
        b = f.byte()
        if b == ord('B'):
            f.read(69) # 不明
            self.name = f.string()
            idl = f.dword()
            if idl < 19999:
                dataversion = 0
                self.id = idl
            else:
                dataversion = 2
                self.id = idl - 20000
        else:
            dataversion = 4
            f.byte() # 不明
            f.byte() # 不明
            f.byte() # 不明
            self.name = f.string()
            self.id = f.dword() - 40000

        if nameonly:
            return

        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.spreadtype = f.byte()
        mcards_num = f.dword()
        self.mcards = [MenuCard(self, f, dataversion=dataversion) for cnt in xrange(mcards_num)]
        bgimgs_num = f.dword()
        self.bgimgs = [bgimage.BgImage(self, f) for cnt in xrange(bgimgs_num)]

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Area")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("BgImages")
            for bgimg in self.bgimgs:
                e.append(bgimg.get_data())
            self.data.append(e)
            e = cw.data.make_element("MenuCards")
            e.set("spreadtype", self.conv_spreadtype(self.spreadtype))
            for mcard in self.mcards:
                e.append(mcard.get_data())
            self.data.append(e)
            e = cw.data.make_element("Events")
            for event in self.events:
                e.append(event.get_data())
            self.data.append(e)
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "bgimgs": self.get_childrentext(self.bgimgs, indent + 2),
             "menucards": self.get_childrentext(self.mcards, indent + 2),
             "events": self.get_childrentext(self.events, indent + 2),
             "spreadtype": self.conv_spreadtype(self.spreadtype),
             "indent": self.get_indent(indent)
             }
        return d

class MenuCard(base.CWBinaryBase):
    """メニューカードのデータ。"""
    def __init__(self, parent, f, yadodata=False, dataversion=4):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        f.byte() # 不明
        self.image = f.image()
        self.name = f.string()
        f.dword() # 不明
        self.description = f.string(True)
        events_num = f.dword()
        self.events = [event.Event(self, f) for cnt in xrange(events_num)]
        self.flag = f.string()
        self.scale = f.dword()
        self.left = f.dword()
        self.top = f.dword()
        if dataversion <= 2:
            self.imgpath = ""
        else:
            self.imgpath = f.string()

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = self.get_materialpath(self.imgpath)
            self.data = cw.data.make_element("MenuCard")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            e = cw.data.make_element("Flag", self.flag)
            prop.append(e)
            e = cw.data.make_element("Location")
            e.set("left", str(self.left))
            e.set("top", str(self.top))
            prop.append(e)
            e = cw.data.make_element("Size")
            e.set("scale", "%s%%" % (self.scale))
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("Events")
            for event in self.events:
                e.append(event.get_data())
            self.data.append(e)
        return self.data

    # FIXME
    def get_xmltext(self, indent):
        data = self.get_data()
        text = xml.etree.ElementTree.tostring(element=data, encoding="utf-8", method="xml")
        return text

    def get_xmldict(self, indent):
        d = {"name": self.name,
             "imgpath": self.get_materialpath(self.imgpath),
             "description": self.description,
             "flag": self.flag,
             "scale": self.scale,
             "left": self.left,
             "top": self.top,
             "events": self.get_childrentext(self.events, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
