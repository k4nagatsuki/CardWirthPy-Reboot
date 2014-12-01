#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import event

import cw


class Package(base.CWBinaryBase):
    """widファイルの情報カードのデータ。
    type:InfoCardと区別が付くように、Packageは暫定的に"7"とする。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = 7
        f.dword() # 不明
        self.name = f.string()
        self.id = f.dword()
        if nameonly:
            return
        events_num = f.dword()
        self.events = [event.SimpleEvent(self, f) for _cnt in xrange(events_num)]

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Package")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("Events")
            for event in self.events:
                e.append(event.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        name = ""
        resid = 0
        events = []

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        resid = int(prop.text)
                    elif prop.tag == "Name":
                        name = prop.text
            elif e.tag == "Events":
                events = e

        f.write_dword(0) # 不明
        f.write_string(name)
        f.write_dword(resid)
        f.write_dword(len(events))
        for evt in events:
            event.SimpleEvent.unconv(f, evt)

def main():
    pass

if __name__ == "__main__":
    main()
