#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
            if idl <= 19999:
                dataversion = 0
                self.id = idl
            else:
                dataversion = 2
                self.id = idl - 20000
        else:
            dataversion = 4
            b = f.byte()
            b = f.byte()
            b = f.byte()
            self.name = f.string()
            self.id = f.dword() - 40000

        if nameonly:
            return

        events_num = f.dword()
        self.events = [event.Event(self, f) for _cnt in xrange(events_num)]
        self.spreadtype = f.byte()
        mcards_num = f.dword()
        self.mcards = [MenuCard(self, f, dataversion=dataversion) for _cnt in xrange(mcards_num)]
        bgimgs_num = f.dword()
        self.bgimgs = [bgimage.BgImage(self, f) for _cnt in xrange(bgimgs_num)]

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

    @staticmethod
    def unconv(f, data):
        restype = 0
        name = ""
        resid = 0
        events = []
        spreadtype = 0
        mcards = []
        bgimgs = []

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        resid = int(prop.text)
                    elif prop.tag == "Name":
                        name = prop.text
            elif e.tag == "BgImages":
                bgimgs = e
            elif e.tag == "PlayerCardEvents":
                if len(e):
                    f.check_wsnversion("2")
            elif e.tag == "MenuCards":
                mcards = e
                spreadtype = base.CWBinaryBase.unconv_spreadtype(e.get("spreadtype"))
            elif e.tag == "Events":
                events = e

        f.write_byte(restype)
        f.write_dword(0) # 不明
        f.write_string(name)
        f.write_dword(resid + 40000)
        f.write_dword(len(events))
        for evt in events:
            event.Event.unconv(f, evt)
        f.write_byte(spreadtype)
        f.write_dword(len(mcards))
        for mcard in mcards:
            MenuCard.unconv(f, mcard)
        f.write_dword(len(bgimgs))
        for bgimg in bgimgs:
            bgimage.BgImage.unconv(f, bgimg)

class MenuCard(base.CWBinaryBase):
    """メニューカードのデータ。"""
    def __init__(self, parent, f, yadodata=False, dataversion=4):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        _b = f.byte() # 不明
        self.image = f.image()
        self.name = f.string()
        _dw = f.dword() # 不明
        self.description = f.string(True)
        events_num = f.dword()
        self.events = [event.Event(self, f) for _cnt in xrange(events_num)]
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
            if self.imgpath in ("1", "2", "3", "4", "5", "6"):
                e = cw.data.make_element("PCNumber", self.imgpath)
            else:
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

    @staticmethod
    def unconv(f, data):
        image = None
        name = ""
        description = ""
        events = []
        flag = ""
        scale = 0
        left = 0
        top = 0
        imgpath = ""

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "ImagePath":
                        base.CWBinaryBase.check_imgpath(f, prop, "TopLeft")
                        imgpath = base.CWBinaryBase.materialpath(prop.text)
                    elif prop.tag == "ImagePaths":
                        if 1 < len(prop):
                            f.check_wsnversion("1")
                        else:
                            base.CWBinaryBase.check_imgpath(f, prop.find("ImagePath"), "TopLeft")
                            imgpath2 = prop.gettext("ImagePath", "")
                            if imgpath2:
                                imgpath = base.CWBinaryBase.materialpath(imgpath2)
                    elif prop.tag == "PCNumber":
                        f.check_version(1.50)
                        imgpath = prop.text
                    elif prop.tag == "Description":
                        description = prop.text
                    elif prop.tag == "Flag":
                        flag = prop.text
                    elif prop.tag == "Location":
                        left = int(prop.get("left"))
                        top = int(prop.get("top"))
                    elif prop.tag == "Size":
                        scale = prop.get("scale")
                        if scale.endswith("%"):
                            scale = int(scale[:-1])
                        else:
                            scale = int(scale)
            elif e.tag == "Events":
                events = e

        f.write_byte(0) # 不明
        f.write_image(image)
        f.write_string(name)
        f.write_dword(0) # 不明
        f.write_string(description, True)
        f.write_dword(len(events))
        for evt in events:
            event.Event.unconv(f, evt)
        f.write_string(flag)
        f.write_dword(scale)
        f.write_dword(left)
        f.write_dword(top)
        f.write_string(imgpath)

def main():
    pass

if __name__ == "__main__":
    main()
