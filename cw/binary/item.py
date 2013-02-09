#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import effectmotion
import event

import cw


class ItemCard(base.CWBinaryBase):
    """widファイルのアイテムカードのデータ。
    hold(真偽値):True?だと自動選択されない。
    """
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
        elif idl < 49999:
            dataversion = 4
            self.id = idl - 40000
        else:
            dataversion = 5
            self.id = idl - 50000

        if nameonly:
            return

        if 5 <= dataversion:
            self.fname = self.get_fname()

        self.description = f.string(True)
        self.p_ability = f.dword()
        self.m_ability = f.dword()
        self.silence = f.bool()
        self.target_all = f.bool()
        self.target = f.byte()
        self.effect_type = f.byte()
        self.resist_type = f.byte()
        self.success_rate = f.dword()
        self.visual_effect = f.byte()
        motions_num = f.dword()
        self.motions = [effectmotion.EffectMotion(self, f, dataversion=dataversion)
                                          for cnt in xrange(motions_num)]
        self.enhance_avoid = f.dword()
        self.enhance_resist = f.dword()
        self.enhance_defense = f.dword()
        self.sound_effect = f.string()
        self.sound_effect2 = f.string()
        self.keycodes = [f.string() for cnt in xrange(5)]
        if 2 < dataversion:
            self.premium = f.byte()
            self.scenario_name = f.string()
            self.scenario_author = f.string()
            events_num = f.dword()
            self.events = [event.SimpleEvent(self, f) for cnt in xrange(events_num)]
            self.hold = f.bool()
        else:
            self.premium = 0
            self.scenario_name = ""
            self.scenario_author = ""
            self.events = []
            if 0 < dataversion:
                self.hold = f.bool()
            else:
                self.hold = False

        # 宿データだとここに不明なデータ(4)が付加されている
        if 5 <= dataversion:
            f.dword()

        self.limit = f.dword()
        self.limit_max = f.dword()
        self.price = f.dword()
        self.enhance_avoid2 = f.dword()
        self.enhance_resist2 = f.dword()
        self.enhance_defense2 = f.dword()

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""
            self.data = cw.data.make_element("ItemCard")
            prop = cw.data.make_element("Property")
            e = cw.data.make_element("Id", str(self.id))
            prop.append(e)
            e = cw.data.make_element("Name", self.name)
            prop.append(e)
            e = cw.data.make_element("ImagePath", self.imgpath)
            prop.append(e)
            e = cw.data.make_element("Description", self.description)
            prop.append(e)
            e = cw.data.make_element("Scenario", self.scenario_name)
            prop.append(e)
            e = cw.data.make_element("Author", self.scenario_author)
            prop.append(e)
            e = cw.data.make_element("Ability")
            e.set("physical", self.conv_card_physicalability(self.p_ability))
            e.set("mental", self.conv_card_mentalability(self.m_ability))
            prop.append(e)
            e = cw.data.make_element("Target", self.conv_card_target(self.target))
            e.set("allrange", str(self.target_all))
            prop.append(e)
            e = cw.data.make_element("EffectType", self.conv_card_effecttype(self.effect_type))
            e.set("spell", str(self.silence))
            prop.append(e)
            e = cw.data.make_element("ResistType", self.conv_card_resisttype(self.resist_type))
            prop.append(e)
            e = cw.data.make_element("SuccessRate", str(self.success_rate))
            prop.append(e)
            e = cw.data.make_element("VisualEffect", self.conv_card_visualeffect(self.visual_effect))
            prop.append(e)
            e = cw.data.make_element("Enhance")
            e.set("avoid", str(self.enhance_avoid))
            e.set("resist", str(self.enhance_resist))
            e.set("defense", str(self.enhance_defense))
            prop.append(e)
            e = cw.data.make_element("SoundPath", self.get_materialpath(self.sound_effect))
            prop.append(e)
            e = cw.data.make_element("SoundPath2", self.get_materialpath(self.sound_effect2))
            prop.append(e)
            e = cw.data.make_element("KeyCodes", cw.util.encodetextlist(self.keycodes))
            prop.append(e)
            e = cw.data.make_element("Premium", self.conv_card_premium(self.premium))
            prop.append(e)
            e = cw.data.make_element("UseLimit", str(self.limit))
            e.set("max", str(self.limit_max))
            prop.append(e)
            e = cw.data.make_element("Price", str(self.price))
            prop.append(e)
            e = cw.data.make_element("EnhanceOwner")
            e.set("avoid", str(self.enhance_avoid2))
            e.set("resist", str(self.enhance_resist2))
            e.set("defense", str(self.enhance_defense2))
            prop.append(e)
            e = cw.data.make_element("Hold", str(self.hold))
            prop.append(e)
            self.data.append(prop)
            e = cw.data.make_element("Motions")
            for motion in self.motions:
                e.append(motion.get_data())
            self.data.append(e)
            e = cw.data.make_element("Events")
            for event in self.events:
                e.append(event.get_data())
            self.data.append(e)
        return self.data

def main():
    pass

if __name__ == "__main__":
    main()
