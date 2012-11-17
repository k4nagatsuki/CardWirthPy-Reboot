#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import item
import skill
import beast
import coupon


class CastCard(base.CWBinaryBase):
    """キャストデータ(widファイル)。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = f.byte()
        self.image = f.image()
        self.name = f.string()
        self.id = f.dword() % 10000

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

        # クーポン
        coupons_num = f.dword()
        self.coupons = [coupon.Coupon(self, f) for cnt in xrange(coupons_num)]

    def get_xmldict(self, indent):
        d = {"id": self.id,
             "name": self.name,
             "description": self.description,

             "level": self.level,
             "money": self.money,
             "life": self.life,
             "maxlife": self.maxlife,

             "noeffect_weapon": self.noeffect_weapon,
             "noeffect_magic": self.noeffect_magic,
             "undead": self.undead,
             "automaton": self.automaton,
             "unholy": self.unholy,
             "constructure": self.constructure,
             "resist_fire": self.resist_fire,
             "resist_ice": self.resist_ice,
             "weakness_fire": self.weakness_fire,
             "weakness_ice": self.weakness_ice,

             "dex": self.dex,
             "agl": self.agl,
             "int": self.int,
             "str": self.str,
             "vit": self.vit,
             "min": self.min,

             "aggressive": self.aggressive,
             "cheerful": self.cheerful,
             "brave": self.brave,
             "cautious": self.cautious,
             "trickish": self.trickish,

             "avoid": self.avoid,
             "resist": self.resist,
             "defense": self.defense,

             "mentality": self.conv_mentality(self.mentality),
             "duration_mentality": self.duration_mentality,
             "paralyze": self.paralyze,
             "poison": self.poison,
             "bind": self.duration_bind,
             "silence": self.duration_silence,
             "faceup": self.duration_faceup,
             "antimagic": self.duration_antimagic,

             "enhance_action": self.enhance_action,
             "duration_enhance_action": self.duration_enhance_action,
             "enhance_avoid": self.enhance_avoid,
             "duration_enhance_avoid": self.duration_enhance_avoid,
             "enhance_resist": self.enhance_resist,
             "duration_enhance_resist": self.duration_enhance_resist,
             "enhance_defense": self.enhance_defense,
             "duration_enhance_defense": self.duration_enhance_defense,

             "coupons": self.get_childrentext(self.coupons, indent + 3),
             "items": self.get_childrentext(self.items, indent + 2),
             "skills": self.get_childrentext(self.skills, indent + 2),
             "beasts": self.get_childrentext(self.beasts, indent + 2),

             "indent": self.get_indent(indent)
             }
        return d

def main():
    pass

if __name__ == "__main__":
    main()
