#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import effectmotion
import event

import cw


class SkillCard(base.CWBinaryBase):
    """widファイルのスキルカードのデータ。
    hold(真偽値):True?だと自動選択されない。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False, materialdir="Material", image_export=True):
        base.CWBinaryBase.__init__(self, parent, f, yadodata, materialdir, image_export)
        self.type = f.byte()
        self.image = f.image()
        self.imgpath = ""
        self.name = f.string()
        idl = f.dword()

        if idl <= 19999:
            dataversion = 0
            self.id = idl
        elif idl <= 39999:
            dataversion = 2
            self.id = idl - 20000
        elif idl <= 49999:
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
                                          for _cnt in xrange(motions_num)]
        self.enhance_avoid = f.dword()
        self.enhance_resist = f.dword()
        self.enhance_defense = f.dword()
        self.sound_effect = f.string()
        self.sound_effect2 = f.string()
        self.keycodes = [f.string() for _cnt in xrange(5)]
        if 2 < dataversion:
            self.premium = f.byte()
            self.scenario_name = f.string()
            self.scenario_author = f.string()
            events_num = f.dword()
            self.events = [event.SimpleEvent(self, f) for _cnt in xrange(events_num)]
            self.hold = f.bool()
        else:
            self.scenario_name = ""
            self.scenario_author = ""
            self.events = []
            self.hold = False
            if 0 < dataversion:
                self.premium = f.byte()
            else:
                self.premium = 0

        # 宿データだとここに不明なデータ(4)が付加されている
        if 5 <= dataversion:
            _dw = f.dword()

        self.level = f.dword()
        self.limit = f.dword()

        self.data = None

    def get_data(self):
        if self.data is None:
            if 2 < self.premium:
                # シナリオで入手したカード
                self.set_image_export(False, True)
            if not self.imgpath:
                if self.image:
                    self.imgpath = self.export_image()
                else:
                    self.imgpath = ""
            self.data = cw.data.make_element("SkillCard")
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
            e = cw.data.make_element("Level", str(self.level))
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
            if 2 < self.premium:
                self.data.set("scenariocard", "True")
                e = cw.data.make_element("Premium", self.conv_card_premium(self.premium - 3))
            else:
                e = cw.data.make_element("Premium", self.conv_card_premium(self.premium))
            prop.append(e)
            e = cw.data.make_element("UseLimit", str(self.limit))
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

    @staticmethod
    def unconv(f, data, ownerisadventurer):
        restype = 0
        image = None
        name = ""
        resid = 0
        description = ""
        p_ability = 0
        m_ability = 0
        silence = False
        target_all = False
        target = 0
        effect_type = 0
        resist_type = 0
        success_rate = 0
        visual_effect = 0
        motions = []
        enhance_avoid = 0
        enhance_resist = 0
        enhance_defense = 0
        sound_effect = ""
        sound_effect2 = ""
        keycodes = []
        premium = 0
        scenario_name = ""
        scenario_author = ""
        events = []
        hold = False
        level = 0
        limit = 0
        scenariocard = cw.util.str2bool(data.get("scenariocard", "False"))

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
                    elif prop.tag == "Scenario":
                        scenario_name = prop.text
                    elif prop.tag == "Author":
                        scenario_author = prop.text
                    elif prop.tag == "Level":
                        level = int(prop.text)
                    elif prop.tag == "Ability":
                        p_ability = base.CWBinaryBase.unconv_card_physicalability(prop.get("physical"))
                        m_ability = base.CWBinaryBase.unconv_card_mentalability(prop.get("mental"))
                    elif prop.tag == "Target":
                        target = base.CWBinaryBase.unconv_card_target(prop.text)
                        target_all = cw.util.str2bool(prop.get("allrange"))
                    elif prop.tag == "EffectType":
                        effect_type = base.CWBinaryBase.unconv_card_effecttype(prop.text)
                        silence = cw.util.str2bool(prop.get("spell"))
                    elif prop.tag == "ResistType":
                        resist_type = base.CWBinaryBase.unconv_card_resisttype(prop.text)
                    elif prop.tag == "SuccessRate":
                        success_rate = int(prop.text)
                    elif prop.tag == "VisualEffect":
                        visual_effect = base.CWBinaryBase.unconv_card_visualeffect(prop.text)
                    elif prop.tag == "Enhance":
                        enhance_avoid = int(prop.get("avoid"))
                        enhance_resist = int(prop.get("resist"))
                        enhance_defense = int(prop.get("defense"))
                    elif prop.tag == "SoundPath":
                        sound_effect = base.CWBinaryBase.materialpath(prop.text)
                        f.check_soundoptions(prop)
                    elif prop.tag == "SoundPath2":
                        sound_effect2 = base.CWBinaryBase.materialpath(prop.text)
                        f.check_soundoptions(prop)
                    elif prop.tag == "KeyCodes":
                        keycodes = cw.util.decodetextlist(prop.text)
                        # 5件まで絞り込む
                        if 5 < len(keycodes):
                            keycodes2 = []
                            for keycode in keycodes:
                                if keycode:
                                    if 5 <= len(keycodes2):
                                        f.check_wsnversion("")
                                        break
                                    else:
                                        keycodes2.append(keycode)
                            keycodes = keycodes2
                        if len(keycodes) < 5:
                            keycodes.extend([""] * (5 - len(keycodes)))
                    elif prop.tag == "Premium":
                        premium = base.CWBinaryBase.unconv_card_premium(prop.text)
                        if ownerisadventurer and scenariocard:
                            premium += 3
                    elif prop.tag == "UseLimit":
                        limit = int(prop.text)
                    elif prop.tag == "Hold":
                        hold = cw.util.str2bool(prop.text)
                    elif prop.tag == "LinkId":
                        if prop.text and prop.text <> "0":
                            f.check_wsnversion("1")
            elif e.tag == "Motions":
                motions = e
            elif e.tag == "Events":
                events = e

        f.write_byte(restype)
        f.write_image(image)
        f.write_string(name)
        f.write_dword(resid + 50000)
        f.write_string(description, True)
        f.write_dword(p_ability)
        f.write_dword(m_ability)
        f.write_bool(silence)
        f.write_bool(target_all)
        f.write_byte(target)
        f.write_byte(effect_type)
        f.write_byte(resist_type)
        f.write_dword(success_rate)
        f.write_byte(visual_effect)
        f.write_dword(len(motions))
        for motion in motions:
            effectmotion.EffectMotion.unconv(f, motion)
        f.write_dword(enhance_avoid)
        f.write_dword(enhance_resist)
        f.write_dword(enhance_defense)
        f.write_string(sound_effect)
        f.write_string(sound_effect2)
        for keycode in keycodes:
            f.write_string(keycode)
        f.write_byte(premium)
        f.write_string(scenario_name)
        f.write_string(scenario_author)
        f.write_dword(len(events))
        for evt in events:
            event.SimpleEvent.unconv(f, evt)
        f.write_bool(hold)

        # 宿データだとここに不明なデータ(4)が付加されている
        f.write_dword(4)

        f.write_dword(level)
        f.write_dword(limit)

def main():
    pass

if __name__ == "__main__":
    main()
