#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import item
import skill
import beast
import coupon

import cw


class Adventurer(base.CWBinaryBase):
    """冒険者データ。埋め込み画像はないので
    wch・wptファイルから個別に引っ張ってくる必要がある。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
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
        self.description = f.string().replace("TEXT\\n", "", 1)
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

        self.data = None

    def get_data(self):
        if self.data is None:
            if self.image:
                self.imgpath = self.export_image()
            else:
                self.imgpath = ""

            # 所持スキル・召喚獣の使用回数初期化
            for skill in self.skills:
                skill.limit = 0

            for beast in self.beasts:
                beast.limit = 0

            self.data = cw.data.make_element("Adventurer")

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

             # シナリオ途中で手に入れたカード(F9で消えるカード)は変換しない
            e = cw.data.make_element("ItemCards")
            for card in self.items:
                if card.premium <= 2:
                    e.append(card.get_data())
            self.data.append(e)

            e = cw.data.make_element("SkillCards")
            for card in self.skills:
                if card.premium <= 2:
                    e.append(card.get_data())
            self.data.append(e)

            e = cw.data.make_element("BeastCards")
            for card in self.beasts:
                if card.premium <= 2:
                    e.append(card.get_data())
            self.data.append(e)

        return self.data

    def create_xml(self, dpath):
        path = base.CWBinaryBase.create_xml(self, dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_adventurer(path, album=False, commit=False)
        return path

    @staticmethod
    def unconv(f, data):
        name = ""
        id = 0

        noeffect_weapon = False
        noeffect_magic = False
        undead = False
        automaton = False
        unholy = False
        constructure = False
        resist_fire = False
        resist_ice = False
        weakness_fire = False
        weakness_ice = False

        level = 0
        description = ""
        life = 0
        maxlife = 0

        paralyze = 0
        poison = 0

        avoid = 0
        resist = 0
        defense = 0

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

        mentality = 0
        duration_mentality = 0

        duration_bind = 0
        duration_silence = 0
        duration_faceup = 0
        duration_antimagic = 0

        enhance_action = 0
        duration_enhance_action = 0
        enhance_avoid = 0
        duration_enhance_avoid = 0
        enhance_resist = 0
        duration_enhance_resist = 0
        enhance_defense = 0
        duration_enhance_defense = 0

        items = []
        skills = []
        beasts = []

        coupons = []

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        id = int(prop.text)
                    elif prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "Description":
                        description = prop.text
                    elif prop.tag == "Level":
                        level = int(prop.text)
                    elif prop.tag == "Life":
                        life = int(prop.text)
                        maxlife = int(float(prop.get("max")))
                    elif prop.tag == "Feature":
                        for fe in prop:
                            if fe.tag == "Type":
                                undead = bool(fe.get("undead"))
                                automaton = bool(fe.get("automaton"))
                                unholy = bool(fe.get("unholy"))
                                constructure = bool(fe.get("constructure"))
                            elif fe.tag == "NoEffect":
                                noeffect_weapon = bool(fe.get("noeffect_weapon"))
                                noeffect_magic = bool(fe.get("noeffect_magic"))
                            elif fe.tag == "Resist":
                                resist_fire = bool(fe.get("resist_fire"))
                                resist_ice = bool(fe.get("resist_ice"))
                            elif fe.tag == "Weakness":
                                weakness_fire = bool(fe.get("weakness_fire"))
                                weakness_ice = bool(fe.get("weakness_ice"))
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
                    elif prop.tag == "Status":
                        for se in prop:
                            if se.tag == "Mentality":
                                mentality = base.CWBinaryBase.unconv_mentality(se.text)
                                duration_mentality = int(se.get("duration"))
                            elif se.tag == "Paralyze":
                                paralyze = int(se.text)
                            elif se.tag == "Poison":
                                poison = int(se.text)
                            elif se.tag == "Bind":
                                duration_bind = int(se.get("duration"))
                            elif se.tag == "Silence":
                                duration_silence = int(se.get("duration"))
                            elif se.tag == "FaceUp":
                                duration_faceup = int(se.get("duration"))
                            elif se.tag == "AntiMagic":
                                duration_antimagic = int(se.get("duration"))
                    elif prop.tag == "Enhance":
                        for ee in prop:
                            if ee.tag == "Action":
                                enhance_action = int(ee.text)
                                duration_enhance_action = int(ee.get("duration"))
                            elif ee.tag == "Avoid":
                                enhance_avoid = int(ee.text)
                                duration_enhance_avoid = int(ee.get("duration"))
                            elif ee.tag == "Resist":
                                enhance_resist = int(ee.text)
                                duration_enhance_resist = int(ee.get("duration"))
                            elif ee.tag == "Defense":
                                enhance_defense = int(ee.text)
                                duration_enhance_defense = int(ee.get("duration"))
                    elif prop.tag == "Coupons":
                        coupons = prop

            elif e.tag == "ItemCards":
                items = e

            elif e.tag == "SkillCards":
                skills = e

            elif e.tag == "BeastCards":
                beasts = e

        f.write_string(name)
        f.write_dword(id + 50000)

        f.write_bool(noeffect_weapon)
        f.write_bool(noeffect_magic)
        f.write_bool(undead)
        f.write_bool(automaton)
        f.write_bool(unholy)
        f.write_bool(constructure)
        f.write_bool(resist_fire)
        f.write_bool(resist_ice)
        f.write_bool(weakness_fire)
        f.write_bool(weakness_ice)

        f.write_dword(level)
        f.write_string("TEXT\\n" + description)
        f.write_dword(life)
        f.write_dword(maxlife)

        f.write_dword(paralyze)
        f.write_dword(poison)

        f.write_dword(avoid)
        f.write_dword(resist)
        f.write_dword(defense)

        f.write_dword(dex)
        f.write_dword(agl)
        f.write_dword(inte)
        f.write_dword(str)
        f.write_dword(vit)
        f.write_dword(min)

        f.write_dword(aggressive)
        f.write_dword(cheerful)
        f.write_dword(brave)
        f.write_dword(cautious)
        f.write_dword(trickish)

        f.write_byte(mentality)
        f.write_dword(duration_mentality)

        f.write_dword(duration_bind)
        f.write_dword(duration_silence)
        f.write_dword(duration_faceup)
        f.write_dword(duration_antimagic)

        f.write_dword(enhance_action)
        f.write_dword(duration_enhance_action)
        f.write_dword(enhance_avoid)
        f.write_dword(duration_enhance_avoid)
        f.write_dword(enhance_resist)
        f.write_dword(duration_enhance_resist)
        f.write_dword(enhance_defense)
        f.write_dword(duration_enhance_defense)

        f.write_dword(len(items))
        for card in items:
            item.ItemCard.unconv(f, card)
        f.write_dword(len(skills))
        for card in skills:
            skill.SkillCard.unconv(f, card)
        f.write_dword(len(beasts))
        for card in beasts:
            beast.BeastCard.unconv(f, card)

        f.write_dword(len(coupons))
        for cp in coupons:
            coupon.Coupon.unconv(f, cp)

class AdventurerCard(base.CWBinaryBase):
    """wcpファイル(type=1)。冒険者データが中に入っているだけ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 1
        self.fname = self.get_fname()

        for cnt in xrange(5):
            f.byte()

        self.adventurer = Adventurer(self, f, yadodata=yadodata)

    def set_image(self, image):
        """埋め込み画像を取り込む時のメソッド。"""
        self.adventurer.image = image

    def get_data(self):
        return self.adventurer.get_data()

    def create_xml(self, dpath):
        """adventurerのデータだけxml化する。"""
        return self.adventurer.create_xml(dpath)

    @staticmethod
    def unconv(f, data):
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        f.write_byte(0) # 不明
        Adventurer.unconv(f, data)

class AdventurerWithImage(base.CWBinaryBase):
    """埋め込み画像付き冒険者データ。
    パーティデータを読み込むときに使う。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        image = f.image()
        self.adventurer = Adventurer(self, f)
        self.adventurer.image = image
        f.byte()

    def get_data(self):
        return self.adventurer.get_data()

    def create_xml(self, dpath):
        """adventurerのデータだけxml化する。"""
        self.adventurer.create_xml(dpath)

    @staticmethod
    def unconv(f, data):
        f.write_image(base.CWBinaryBase.import_image(data.findtext("Property/ImagePath")))
        Adventurer.unconv(f, data)
        f.write_byte(0)

class AdventurerHeader(base.CWBinaryBase):
    """wchファイル(type=0)。おそらく宿帳表示用の簡易データと思われる。
    必要なデータは埋め込み画像くらい？
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 0
        self.fname = self.get_fname()
        f.byte()
        f.byte()
        self.name = f.string()
        self.image = f.image()
        self.level = f.byte()
        f.byte()
        self.coupons = f.string()
        f.byte()
        f.byte()
        # ここからは16ビット符号付き整数が並んでると思われるが面倒なので
        self.ep = f.byte()
        f.byte()
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

    @staticmethod
    def unconv(f, data, fname):
        name = ""
        image = None
        level = 0
        coupons = ""
        dex = 0
        agl = 0
        inte = 0
        str = 0
        vit = 0
        min = 0
        ep = 0

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag == "ImagePath":
                        image = base.CWBinaryBase.import_image(prop.text)
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
                    elif prop.tag == "Coupons":
                        seq = []
                        for ce in prop:
                            seq.append(ce.text)
                            if ce.text == u"＠ＥＰ":
                                ep = int(ce.get("value", "0"))
                        coupons = cw.util.decodetextlist(seq)

        f.write_word(0) # 不明
        f.write_string(name)
        f.write_image(image)
        f.write_word(level)
        f.write_string(coupons)
        f.write_word(0) # 不明
        f.write_word(ep)
        f.write_word(dex)
        f.write_word(agl)
        f.write_word(inte)
        f.write_word(str)
        f.write_word(vit)
        f.write_word(min)

def main():
    pass

if __name__ == "__main__":
    main()
