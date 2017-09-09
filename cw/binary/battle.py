#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import event

import cw


class Battle(base.CWBinaryBase):
    """widファイルのバトルデータ。"""
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
            f.byte()
            f.byte()
            f.byte()
            self.name = f.string()
            self.id = f.dword() - 40000

        if nameonly:
            return

        events_num = f.dword()
        self.events = [event.Event(self, f) for _cnt in xrange(events_num)]
        self.spreadtype = f.byte()
        ecards_num = f.dword()
        self.ecards = [EnemyCard(self, f) for _cnt in xrange(ecards_num)]
        if 0 < dataversion:
            self.bgm = f.string()
        else:
            self.bgm = "DefBattle.mid"

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Battle")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("MusicPath", self.get_materialpath(self.bgm))
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("EnemyCards")
            e.set("spreadtype", self.conv_spreadtype(self.spreadtype))
            for ecard in self.ecards:
                e.append(ecard.get_data())
            self.data.append(e)
            e = cw.data.make_element("Events")
            for event in self.events:
                e.append(event.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        restype = 1
        name = ""
        resid = 0
        events = []
        spreadtype = 0
        ecards = []
        bgm = ""

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        resid = int(prop.text)
                    elif prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "MusicPath":
                        bgm = base.CWBinaryBase.materialpath(prop.text)
                        f.check_bgmoptions(prop)
            elif e.tag == "PlayerCardEvents":
                if len(e):
                    f.check_wsnversion("2")
            elif e.tag == "EnemyCards":
                ecards = e
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
        f.write_dword(len(ecards))
        for ecard in ecards:
            EnemyCard.unconv(f, ecard)
        f.write_string(bgm)

class EnemyCard(base.CWBinaryBase):
    """エネミーカード。
    主要なデータはキャストカードを参照する。
    escape:逃走フラグ(真偽値)。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.cast_id = f.dword()
        events_num = f.dword()
        self.events = [event.Event(self, f) for _cnt in xrange(events_num)]
        self.flag = f.string()
        self.scale = f.dword()
        self.left = f.dword()
        self.top = f.dword()
        self.escape = f.bool()

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("EnemyCard")
            self.data.set("escape", str(self.escape))
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.cast_id))
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
        cast_id = 0
        events = []
        flag = ""
        scale = 0
        left = 0
        top = 0
        escape = cw.util.str2bool(data.get("escape"))

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        cast_id = int(prop.text)
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

        f.write_dword(cast_id)
        f.write_dword(len(events))
        for evt in events:
            event.Event.unconv(f, evt)
        f.write_string(flag)
        f.write_dword(scale)
        f.write_dword(left)
        f.write_dword(top)
        f.write_bool(escape)

def main():
    pass

if __name__ == "__main__":
    main()
