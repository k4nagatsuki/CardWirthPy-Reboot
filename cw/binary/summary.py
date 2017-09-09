#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

import cw


class Summary(base.CWBinaryBase):
    """見出しデータ(Summary.wsm)。
    type:見出しデータには"-1"の値を付与する。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True,
                 wpt120=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = -1
        self.image = f.image()
        self.name = f.string()
        if nameonly:
            return
        self.description = f.string()
        self.author = f.string()
        self.required_coupons = f.string(True)
        self.required_coupons_num = f.dword()
        self.area_id = f.dword()
        if self.area_id <= 19999:
            self.version = 0
        elif self.area_id <= 39999:
            self.version = 2
            self.area_id = self.area_id - 20000
        elif self.area_id <= 49999:
            self.version = 4
            self.area_id = self.area_id - 40000
        else:
            # version 5～6は存在しない
            self.version = 7
            self.area_id = self.area_id - 70000
        steps_num = f.dword()
        self.steps = [Step(self, f) for _cnt in xrange(steps_num)]
        flags_num = f.dword()
        self.flags = [Flag(self, f) for _cnt in xrange(flags_num)]
        if wpt120:
            return
        _w = f.dword() # 不明
        if 0 < self.version:
            self.level_min = f.dword()
            self.level_max = f.dword()
        else:
            self.level_min = 0
            self.level_max = 0
        # タグとスキンタイプ。読み込みが終わった後から操作する
        self.skintype = ""
        self.tags = ""

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""
            self.data = cw.data.make_element("Summary")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Author", self.author)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            e = cw.data.make_element("Level")
            e.set("min", str(self.level_min))
            e.set("max", str(self.level_max))
            prop.append(e)
            e = cw.data.make_element("RequiredCoupons", self.required_coupons)
            e.set("number", str(self.required_coupons_num))
            prop.append(e)
            e = cw.data.make_element("StartAreaId", str(self.area_id))
            prop.append(e)
            e = cw.data.make_element("Tags", self.tags)
            prop.append(e)
            e = cw.data.make_element("Type", self.skintype)
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("Flags")
            for flag in self.flags:
                e.append(flag.get_data())
            self.data.append(e)
            e = cw.data.make_element("Steps")
            for step in self.steps:
                e.append(step.get_data())
            self.data.append(e)
            e = cw.data.make_element("Labels", "")
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        image = None
        name = ""
        description = ""
        author = ""
        required_coupons = ""
        required_coupons_num = 0
        area_id = 0
        steps = []
        flags = []
        level_min = 0
        level_max = 0

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag in ("ImagePath", "ImagePaths"):
                        image = base.CWBinaryBase.import_image(f, prop)
                    elif prop.tag == "Author":
                        author = prop.text
                    elif prop.tag == "Description":
                        description = prop.text
                    elif prop.tag == "Level":
                        level_min = int(prop.get("min"))
                        level_max = int(prop.get("max"))
                    elif prop.tag == "RequiredCoupons":
                        required_coupons = prop.text
                        required_coupons_num = int(prop.get("number"))
                    elif prop.tag == "StartAreaId":
                        level_max = int(prop.text)
            elif e.tag == "Flags":
                flags = e
            elif e.tag == "Steps":
                steps = e

        f.write_image(image)
        f.write_string(name)
        f.write_string(description)
        f.write_string(author)
        f.write_string(required_coupons, True)
        f.write_dword(required_coupons_num)
        f.write_dword(area_id + 40000)
        f.write_dword(len(steps))
        for step in steps:
            Step.unconv(f, step)
        f.write_dword(len(flags))
        for flag in flags:
            Flag.unconv(f, flag)
        f.write_dword(0) # 不明
        f.write_dword(level_min)
        f.write_dword(level_max)

class Step(base.CWBinaryBase):
    """ステップ定義。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.default = f.dword()
        self.variable_names = [f.string() for _cnt in xrange(10)]

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Step")
            self.data.set("default", str(self.default))
            e = cw.data.make_element("Name", self.name)
            self.data.append(e)
            e = cw.data.make_element("Value0", self.variable_names[0])
            self.data.append(e)
            e = cw.data.make_element("Value1", self.variable_names[1])
            self.data.append(e)
            e = cw.data.make_element("Value2", self.variable_names[2])
            self.data.append(e)
            e = cw.data.make_element("Value3", self.variable_names[3])
            self.data.append(e)
            e = cw.data.make_element("Value4", self.variable_names[4])
            self.data.append(e)
            e = cw.data.make_element("Value5", self.variable_names[5])
            self.data.append(e)
            e = cw.data.make_element("Value6", self.variable_names[6])
            self.data.append(e)
            e = cw.data.make_element("Value7", self.variable_names[7])
            self.data.append(e)
            e = cw.data.make_element("Value8", self.variable_names[8])
            self.data.append(e)
            e = cw.data.make_element("Value9", self.variable_names[9])
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        name = ""
        default = int(data.get("default"))
        if data.getbool(".", "spchars", False):
            f.check_wsnversion("2")
        variable_names = [""] * 10
        for e in data:
            if e.tag == "Name":
                name = e.text
            elif e.tag.startswith("Value"):
                variable_names[int(e.tag[5:])] = e.text

        f.write_string(name)
        f.write_dword(default)
        for variable_name in variable_names:
            f.write_string(variable_name)

class Flag(base.CWBinaryBase):
    """フラグ定義。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.name = f.string()
        self.default = f.bool()
        self.variable_names = [f.string() for _cnt in xrange(2)]

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element("Flag")
            self.data.set("default", str(self.default))
            e = cw.data.make_element("Name", self.name)
            self.data.append(e)
            e = cw.data.make_element("True", self.variable_names[0])
            self.data.append(e)
            e = cw.data.make_element("False", self.variable_names[1])
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        name = ""
        default = cw.util.str2bool(data.get("default"))
        if data.getbool(".", "spchars", False):
            f.check_wsnversion("2")
        variable_names = [""] * 2
        for e in data:
            if e.tag == "Name":
                name = e.text
            elif e.tag == "True":
                variable_names[0] = e.text
            elif e.tag == "False":
                variable_names[1] = e.text

        f.write_string(name)
        f.write_bool(default)
        for variable_name in variable_names:
            f.write_string(variable_name)

def main():
    pass

if __name__ == "__main__":
    main()
