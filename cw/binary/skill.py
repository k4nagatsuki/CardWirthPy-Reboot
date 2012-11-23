#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import effectmotion
import event


class SkillCard(base.CWBinaryBase):
    """widファイルのスキルカードのデータ。
    hold(真偽値):True?だと自動選択されない。
    """
    def __init__(self, parent, f, yadodata=False, nameonly=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = f.byte()
        self.image = f.image()
        self.name = f.string()
        self.id = f.dword() % 10000
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
        self.motions = [effectmotion.EffectMotion(self, f)
                                          for cnt in xrange(motions_num)]
        self.enhance_avoid = f.dword()
        self.enhance_resist = f.dword()
        self.enhance_defense = f.dword()
        self.sound_effect = f.string()
        self.sound_effect2 = f.string()
        self.keycodes = [f.string() for cnt in range(5)]
        self.premium = f.byte()
        self.scenario_name = f.string()
        self.scenario_author = f.string()
        events_num = f.dword()
        self.events = [event.SimpleEvent(self, f) for cnt in xrange(events_num)]
        self.hold = f.bool()

        # 宿データだとここに不明なデータ(4)が付加されている
        if self.is_yadodata():
            f.dword()

        self.level = f.dword()
        self.limit = f.dword()

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "description": self.description,
             "scenario": self.scenario_name,
             "author": self.scenario_author,
             "level": self.level,
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
             "keycodes": "\\n".join(self.keycodes),
             "premium": self.conv_card_premium(self.premium),
             "uselimit": self.limit,
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
