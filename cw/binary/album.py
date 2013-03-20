#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import coupon

import cw


class Album(base.CWBinaryBase):
    """wrmファイル(type=4)。鬼籍に入った冒険者のデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 4
        self.fname = self.get_fname()
        f.byte()
        f.byte()
        self.name = f.string()
        self.image = f.image()
        self.level = f.word()
        f.word() # 不明
        f.word() # 不明
        f.word() # 不明
        # ここからは16ビット符号付き整数が並んでると思われるが面倒なので
        # 能力値
        self.dex = f.byte()
        f.byte()
        self.agl = f.byte()
        f.byte()
        self.int = f.byte()
        f.byte()
        self.str = f.byte()
        f.byte()
        self.vit = f.byte()
        f.byte()
        self.min = f.byte()
        f.byte()
        # 性格値
        self.aggressive = f.byte()
        f.byte()
        self.cheerful = f.byte()
        f.byte()
        self.brave = f.byte()
        f.byte()
        self.cautious = f.byte()
        f.byte()
        self.trickish = f.byte()
        f.byte()
        # 修正能力値
        self.avoid = f.byte()
        f.byte()
        self.resist = f.byte()
        f.byte()
        self.defense = f.byte()
        f.byte()
        f.dword()
        self.description = f.string().replace("TEXT\\n", "", 1)
        # クーポン
        coupons_num = f.dword()
        self.coupons = [coupon.Coupon(self, f) for cnt in xrange(coupons_num)]

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""

            self.data = cw.data.make_element("Album")

            prop = cw.data.make_element("Property")

            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            e = cw.data.make_element("Level", str(self.level))
            prop.append(e)

            ae = cw.data.make_element("Ability")
            e = cw.data.make_element("Physical")
            e.set("dex", str(self.dex))
            e.set("agl", str(self.agl))
            e.set("int", str(self.int))
            e.set("str", str(self.str))
            e.set("vit", str(self.vit))
            e.set("min", str(self.min))
            ae.append(e)
            e = cw.data.make_element("Mental")
            e.set("aggressive", str(self.aggressive))
            e.set("cheerful", str(self.cheerful))
            e.set("brave", str(self.brave))
            e.set("cautious", str(self.cautious))
            e.set("trickish", str(self.trickish))
            ae.append(e)
            e = cw.data.make_element("Enhance")
            e.set("avoid", str(self.avoid))
            e.set("resist", str(self.resist))
            e.set("defense", str(self.defense))
            ae.append(e)
            prop.append(ae)

            ce = cw.data.make_element("Coupons")
            for coupon in self.coupons:
                ce.append(coupon.get_data())
            prop.append(ce)

            self.data.append(prop)

        return self.data

    def create_xml(self, dpath):
        path = base.CWBinaryBase.create_xml(self, dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_adventurer(path, album=True, commit=False)
        return path

    @staticmethod
    def unconv(f, data):
        name = ""
        image = None
        level = 0
        dex = 0
        agl = 0
        inte = 0
        str = 0
        vit = 0
        min = 0
        aggressive = 0
        cheerful = 0
        brave = 0
        cautious = 0
        trickish = 0
        avoid = 0
        resist = 0
        defense = 0
        description = ""
        coupons = []

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "ImagePath":
                        image = base.CWBinaryBase.import_image(prop.text)
                    elif prop.tag == "Description":
                        description = prop.text
                    elif prop.tag == "Level":
                        level = int(prop.text)
                    elif prop.tag == "Ability":
                        for ae in prop:
                            if ae.tag == "Physical":
                                dex = int(ae.get("dex"))
                                agl = int(ae.get("agl"))
                                inte = int(ae.get("int"))
                                str = int(ae.get("str"))
                                vit = int(ae.get("vit"))
                                min = int(ae.get("min"))
                            elif ae.tag == "Mental":
                                aggressive = int(ae.get("aggressive"))
                                cheerful = int(ae.get("cheerful"))
                                brave = int(ae.get("brave"))
                                cautious = int(ae.get("cautious"))
                                trickish = int(ae.get("trickish"))
                            elif ae.tag == "Enhance":
                                avoid = int(ae.get("avoid"))
                                resist = int(ae.get("resist"))
                                defense = int(ae.get("defense"))
                    elif prop.tag == "Coupons":
                        coupons = prop

        f.write_byte(0)
        f.write_byte(0)
        f.write_string(name)
        f.write_image(image)
        f.write_word(level)
        f.write_word(0) # 不明
        f.write_word(0) # 不明
        f.write_word(0) # 不明
        f.write_word(dex)
        f.write_word(agl)
        f.write_word(inte)
        f.write_word(str)
        f.write_word(vit)
        f.write_word(min)
        f.write_word(aggressive)
        f.write_word(cheerful)
        f.write_word(brave)
        f.write_word(cautious)
        f.write_word(trickish)
        f.write_word(avoid)
        f.write_word(resist)
        f.write_word(defense)
        f.write_dword(0)
        f.write_string("TEXT\\n" + description)
        f.write_dword(len(coupons))
        for coupon in coupons:
            coupon.Coupon.unconv(f, coupon)

def main():
    pass

if __name__ == "__main__":
    main()
