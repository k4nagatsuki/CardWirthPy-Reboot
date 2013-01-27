#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import effectmotion
import event

import cw.util


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
        else:
            dataversion = 4
            self.id = idl - 40000

        if nameonly:
            return

        # 宿データの埋め込みカードのイベントは子コンテント数が+50000されている
        if self.is_yadodata():
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
        self.keycodes = [f.string() for cnt in range(5)]
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
        if self.is_yadodata():
            f.dword()

        self.limit = f.dword()
        self.limit_max = f.dword()
        self.price = f.dword()
        self.enhance_avoid2 = f.dword()
        self.enhance_resist2 = f.dword()
        self.enhance_defense2 = f.dword()

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "description": self.description,
             "scenario": self.scenario_name,
             "author": self.scenario_author,
             "p_ability": self.conv_card_physicalability(self.p_ability),
             "m_ability": self.conv_card_mentalability(self.m_ability),
             "silence": self.silence,
             "target_all": self.target_all,
             "target": self.conv_card_target(self.target),
             "effecttype": self.conv_card_effecttype(self.effect_type),
             "resisttype": self.conv_card_resisttype(self.resist_type),
             "successrate": self.success_rate,
             "sound": self.get_materialpath(self.sound_effect),
             "sound2": self.get_materialpath(self.sound_effect2),
             "visual": self.conv_card_visualeffect(self.visual_effect),
             "enhance_avoid": self.enhance_avoid,
             "enhance_resist": self.enhance_resist,
             "enhance_defense": self.enhance_defense,
             "keycodes": cw.util.encodetextlist(self.keycodes),
             "premium": self.conv_card_premium(self.premium),
             "uselimit": self.limit,
             "uselimitmax": self.limit_max,
             "price": self.price,
             "enhance_avoid2": self.enhance_avoid2,
             "enhance_resist2": self.enhance_resist2,
             "enhance_defense2": self.enhance_defense2,
             "hold": self.hold,
             "motions": self.get_childrentext(self.motions, indent + 2),
             "events": self.get_childrentext(self.events, indent + 2),
             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
