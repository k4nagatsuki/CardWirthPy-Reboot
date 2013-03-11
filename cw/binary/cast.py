#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import item
import skill
import beast
import coupon

import cw


class CastCard(base.CWBinaryBase):
    """キャストデータ(widファイル)。"""
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

        # mate特有の属性値(真偽値)*10
        self.noeffect_weapon = f.bool()
        self.noeffect_magic = f.bool()
        self.undead = f.bool()
        self.automaton = f.bool()
        self.unholy = f.bool()
        self.constructure = f.bool()
        self.resist_fire = f.bool()
        self.resist_ice = f.bool()
        self.weakness_fire = f.bool()
        self.weakness_ice = f.bool()

        self.level = f.dword()
        self.money = f.dword()
        self.description = f.string(True).replace("TEXT\\n", "", 1)
        self.life = f.dword()
        self.maxlife = f.dword()

        # 状態異常の値(持続ターン数)
        self.paralyze = f.dword()
        self.poison = f.dword()

        # 能力修正値(デフォルト)
        self.avoid = f.dword()
        self.resist = f.dword()
        self.defense = f.dword()

        # 各能力値*5
        self.dex = f.dword()
        self.agl = f.dword()
        self.int = f.dword()
        self.str = f.dword()
        self.vit = f.dword()
        self.min = f.dword()

        # 性格値*5
        self.aggressive = f.dword()
        self.cheerful = f.dword()
        self.brave = f.dword()
        self.cautious = f.dword()
        self.trickish = f.dword()

        # 精神状態
        self.mentality = f.byte()
        self.duration_mentality = f.dword()

        # 各状態異常の持続ターン数
        self.duration_bind = f.dword()
        self.duration_silence = f.dword()
        self.duration_faceup = f.dword()
        self.duration_antimagic = f.dword()

        # 能力修正値(効果モーション)
        self.enhance_action = f.dword()
        self.duration_enhance_action = f.dword()
        self.enhance_avoid = f.dword()
        self.duration_enhance_avoid = f.dword()
        self.enhance_resist = f.dword()
        self.duration_enhance_resist = f.dword()
        self.enhance_defense = f.dword()
        self.duration_enhance_defense = f.dword()

        # 所持カード
        items_num = f.dword()
        self.items = [item.ItemCard(self, f) for cnt in xrange(items_num)]
        skills_num = f.dword()
        self.skills = [skill.SkillCard(self, f) for cnt in xrange(skills_num)]
        beasts_num = f.dword()
        self.beasts = [beast.BeastCard(self, f) for cnt in xrange(beasts_num)]

        if 0 < dataversion:
            # クーポン
            coupons_num = f.dword()
            self.coupons = [coupon.Coupon(self, f) for cnt in xrange(coupons_num)]
        else:
            self.coupons = []

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""

            self.data = cw.data.make_element("CastCard")

            prop = cw.data.make_element("Property")

            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            e = cw.data.make_element("Level", str(self.level))
            prop.append(e)
            e = cw.data.make_element("Money", str(self.money))
            prop.append(e)
            e = cw.data.make_element("Life", str(self.life))
            e.set("max", str(self.maxlife))
            prop.append(e)

            fe = cw.data.make_element("Feature")
            e = cw.data.make_element("Type")
            e.set("undead", str(self.undead))
            e.set("automaton", str(self.automaton))
            e.set("unholy", str(self.unholy))
            e.set("constructure", str(self.constructure))
            fe.append(e)
            e = cw.data.make_element("NoEffect")
            e.set("weapon", str(self.noeffect_weapon))
            e.set("magic", str(self.noeffect_magic))
            fe.append(e)
            e = cw.data.make_element("Resist")
            e.set("fire", str(self.resist_fire))
            e.set("ice", str(self.resist_ice))
            fe.append(e)
            e = cw.data.make_element("Weakness")
            e.set("fire", str(self.weakness_fire))
            e.set("ice", str(self.weakness_ice))
            fe.append(e)
            prop.append(fe)

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

            se = cw.data.make_element("Status")
            e = cw.data.make_element("Mentality", self.conv_mentality(self.mentality))
            e.set("duration", str(self.duration_mentality))
            se.append(e)
            e = cw.data.make_element("Paralyze", str(self.paralyze))
            se.append(e)
            e = cw.data.make_element("Poison", str(self.poison))
            se.append(e)
            e = cw.data.make_element("Bind")
            e.set("duration", str(self.duration_bind))
            se.append(e)
            e = cw.data.make_element("Silence")
            e.set("duration", str(self.duration_silence))
            se.append(e)
            e = cw.data.make_element("FaceUp")
            e.set("duration", str(self.duration_faceup))
            se.append(e)
            e = cw.data.make_element("AntiMagic")
            e.set("duration", str(self.duration_antimagic))
            se.append(e)
            prop.append(se)

            ee = cw.data.make_element("Enhance")
            e = cw.data.make_element("Action", str(self.enhance_action))
            e.set("duration", str(self.duration_enhance_action))
            ee.append(e)
            e = cw.data.make_element("Avoid", str(self.enhance_avoid))
            e.set("duration", str(self.duration_enhance_avoid))
            ee.append(e)
            e = cw.data.make_element("Resist", str(self.enhance_resist))
            e.set("duration", str(self.duration_enhance_resist))
            ee.append(e)
            e = cw.data.make_element("Defense", str(self.enhance_defense))
            e.set("duration", str(self.duration_enhance_defense))
            ee.append(e)
            prop.append(ee)

            ce = cw.data.make_element("Coupons")
            for coupon in self.coupons:
                ce.append(coupon.get_data())
            prop.append(ce)

            self.data.append(prop)

            e = cw.data.make_element("ItemCards")
            for card in self.items:
                e.append(card.get_data())
            self.data.append(e)

            e = cw.data.make_element("SkillCards")
            for card in self.skills:
                e.append(card.get_data())
            self.data.append(e)

            e = cw.data.make_element("BeastCards")
            for card in self.beasts:
                e.append(card.get_data())
            self.data.append(e)

        return self.data

    def unconv(self, f, data):
        pass # TODO

def main():
    pass

if __name__ == "__main__":
    main()
