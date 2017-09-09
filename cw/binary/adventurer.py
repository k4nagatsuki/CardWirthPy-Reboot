#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

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
    def __init__(self, parent, f, yadodata=False, nameonly=False, album120=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)

        def add_128coupons():
            epc = coupon.Coupon(self, None)
            epc.name = u"＠ＥＰ"
            epc.value = max(0, self.level - 1) * 10
            self.coupons.insert(0, epc)
            lbc = coupon.Coupon(self, None)
            lbc.name = u"＠レベル原点"
            lbc.value = self.level
            self.coupons.insert(0, lbc)

        if album120:
            # 1.20のアルバムデータ
            self.id = 0

            _dw = f.dword() # 不明
            _dw = f.dword() # 不明(表示順？)
            self.name = f.string()
            self.imgpath = ""
            self.level = f.dword()
            self.money = f.dword()
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

            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明
            _dw = f.dword() # 不明

            self.image = f.image()
            self.description = f.string(True).replace("TEXT\\n", "", 1)

            # 体力を計算
            vit = max(1, self.vit)
            minval = max(1, self.min)
            self.life = cw.character.calc_maxlife(vit, minval, self.level)
            self.maxlife = self.life

            # クーポン
            self.is_dead = False
            coupons_num = f.dword()
            self.coupons = []
            for _cnt in xrange(coupons_num):
                c = coupon.Coupon(self, f, dataversion=4)
                if c.name == u"＿死亡":
                    self.is_dead = True
                self.coupons.append(c)
            add_128coupons()

            # 精神状態
            self.mentality = 0
            self.duration_mentality = 0

            # 状態異常の値(持続ターン数)
            self.paralyze = 0
            self.poison = 0

            # 各状態異常の持続ターン数
            self.duration_bind = 0
            self.duration_silence = 0
            self.duration_faceup = 0
            self.duration_antimagic = 0

            # 能力修正値(効果モーション)
            self.enhance_action = 0
            self.duration_enhance_action = 0
            self.enhance_avoid = 0
            self.duration_enhance_avoid = 0
            self.enhance_resist = 0
            self.duration_enhance_resist = 0
            self.enhance_defense = 0
            self.duration_enhance_defense = 0

            # 所持カード
            self.items = []
            self.skills = []
            self.beasts = []

            self.data = None
            self.f9data = None

            return

        self.image = None
        self.name = f.string()
        if nameonly:
            return

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

        self.imgpath = ""

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
        if dataversion <= 4:
            self.money = f.dword()
        else:
            self.money = 0
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
        self.items = [item.ItemCard(self, f) for _cnt in xrange(items_num)]
        skills_num = f.dword()
        self.skills = [skill.SkillCard(self, f) for _cnt in xrange(skills_num)]
        beasts_num = f.dword()
        self.beasts = [beast.BeastCard(self, f) for _cnt in xrange(beasts_num)]

        # クーポン
        coupons_num = f.dword()
        self.coupons = [coupon.Coupon(self, f, dataversion=dataversion) for _cnt in xrange(coupons_num)]
        if dataversion <= 4:
            add_128coupons()

        self.data = None
        self.f9data = None

    def get_data(self):
        return self._get_data(False)

    def get_f9data(self):
        return self._get_data(True)

    def _get_data(self, f9data):
        if f9data:
            data = self.f9data
        else:
            data = self.data

        if data is None:
            if not self.imgpath:
                if self.image:
                    self.imgpath = self.export_image()
                else:
                    self.imgpath = ""

            data = cw.data.make_element("Adventurer")

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
            if f9data:
                # u"＿１"などの番号クーポン以降を除去
                numcoupons = set([u"＿１", u"＿２", u"＿３", u"＿４", u"＿５", u"＿６"])
                coupons = self.coupons
                cut = False
                for i, coupon in enumerate(coupons):
                    if coupon.name in numcoupons:
                        coupons = coupons[:i]
                        cut = True
                        break

                if not cut and cw.cwpy.msgs["number_1_coupon"] <> u"＿１":
                    # バリアントによってはu"＿１"が別の文字列に置換されている
                    # 可能性があるので、それを加えて再度判断する
                    numcoupons.add(cw.cwpy.msgs["number_1_coupon"])
                    for i, coupon in enumerate(coupons):
                        if coupon.name in numcoupons:
                            coupons = coupons[:i]
                            break

                # '＾'で始まるクーポンは'＾'を取り除く
                for coupon in coupons:
                    if coupon.name.startswith(u"＾"):
                        cdata = coupon.get_data()
                        cdata.text = coupon.name[1:]
                        ce.append(cdata)
                    else:
                        ce.append(coupon.get_data())
            else:
                # '＾'で始まるクーポンはシナリオ内で削除済みのもの
                for coupon in self.coupons:
                    if not coupon.name.startswith(u"＾"):
                        ce.append(coupon.get_data())

            prop.append(ce)

            data.append(prop)

            e = cw.data.make_element("ItemCards")
            for card in self.items:
                if not f9data or card.premium <= 2:
                    card.set_image_export(False, f9data)
                    e.append(card.get_data())
            data.append(e)

            e = cw.data.make_element("SkillCards")
            for card in self.skills:
                if not f9data or card.premium <= 2:
                    card.set_image_export(False, f9data)
                    e.append(card.get_data())
            data.append(e)

            e = cw.data.make_element("BeastCards")
            for card in self.beasts:
                if not f9data or card.premium <= 2:
                    if f9data and card.attachment:
                        continue
                    card.set_image_export(False, f9data)
                    e.append(card.get_data())
            data.append(e)

            if f9data:
                ccard = cw.character.Character(cw.data.CWPyElementTree(element=data))
                ccard.set_fullrecovery()

        if f9data:
            self.f9data = data
        else:
            self.data = data

        return data

    def create_xml(self, dpath):
        path = base.CWBinaryBase.create_xml(self, dpath)
        yadodb = self.get_root().yadodb
        if yadodb:
            yadodb.insert_adventurer(path, album=False, commit=False)
        return path

    @staticmethod
    def unconv(f, data, logdata):
        if not logdata is None:
            # 変換用にクーポンを整理
            coupons = cw.data.make_element("Coupons")
            coupons1 = {}
            coupons2 = set()
            for e in data.getfind("Property/Coupons"):
                coupons1[e.text] = e
                coupons2.add(e)

            for e in logdata.getfind("Property/Coupons"):
                if e.text in coupons1:
                    coupons.append(e)
                    coupons2.remove(coupons1[e.text])
                    del coupons1[e.text]
                else:
                    # 削除されたクーポン
                    coupons.append(cw.data.make_element("Coupon", u"＾" + e.text, { "value":e.get("value", "0") }))
            # 追加されたクーポン
            for e in data.getfind("Property/Coupons"):
                if e in coupons2:
                    coupons.append(e)
        else:
            coupons = data.find("Property/Coupons")

        name = ""
        resid = 0

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
        stre = 0
        vit = 0
        mind = 0

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

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Id":
                        resid = int(prop.text)
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
                                undead = cw.util.str2bool(fe.get("undead"))
                                automaton = cw.util.str2bool(fe.get("automaton"))
                                unholy = cw.util.str2bool(fe.get("unholy"))
                                constructure = cw.util.str2bool(fe.get("constructure"))
                            elif fe.tag == "NoEffect":
                                noeffect_weapon = cw.util.str2bool(fe.get("weapon"))
                                noeffect_magic = cw.util.str2bool(fe.get("magic"))
                            elif fe.tag == "Resist":
                                resist_fire = cw.util.str2bool(fe.get("fire"))
                                resist_ice = cw.util.str2bool(fe.get("ice"))
                            elif fe.tag == "Weakness":
                                weakness_fire = cw.util.str2bool(fe.get("fire"))
                                weakness_ice = cw.util.str2bool(fe.get("ice"))
                    elif prop.tag == "Ability":
                        for ae in prop:
                            if ae.tag == "Physical":
                                dex = int(ae.get("dex"))
                                agl = int(ae.get("agl"))
                                inte = int(ae.get("int"))
                                stre = int(ae.get("str"))
                                vit = int(ae.get("vit"))
                                mind = int(ae.get("min"))
                            elif ae.tag == "Mental":
                                aggressive = int(float(ae.get("aggressive")))
                                cheerful = int(float(ae.get("cheerful")))
                                brave = int(float(ae.get("brave")))
                                cautious = int(float(ae.get("cautious")))
                                trickish = int(float(ae.get("trickish")))
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
                        # このメソッドの冒頭を参照
                        pass

            elif e.tag == "ItemCards":
                items = e

            elif e.tag == "SkillCards":
                skills = e

            elif e.tag == "BeastCards":
                beasts = e

        f.write_string(name)
        f.write_dword(resid + 50000)

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
        f.write_string("TEXT\n" + (description if description else u""), True)
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
        f.write_dword(stre)
        f.write_dword(vit)
        f.write_dword(mind)

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

        lenpos = f.tell()
        f.write_dword(0)
        cardslen = 0
        for card in items:
            try:
                pos = f.tell()
                item.ItemCard.unconv(f, card, True)
                cardslen += 1
            except cw.binary.cwfile.UnsupportedError:
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は対象エンジンで使用できないため、変換しません。\n" % (name, cardname)
                    f.write_errorlog(s)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は変換できませんでした。\n" % (name, cardname)
                    f.write_errorlog(s)
        tell = f.tell()
        f.seek(lenpos)
        f.write_dword(cardslen)
        f.seek(tell)

        lenpos = f.tell()
        f.write_dword(0)
        cardslen = 0
        for card in skills:
            try:
                pos = f.tell()
                skill.SkillCard.unconv(f, card, True)
                cardslen += 1
            except cw.binary.cwfile.UnsupportedError:
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は対象エンジンで使用できないため、変換しません。\n" % (name, cardname)
                    f.write_errorlog(s)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は変換できませんでした。\n" % (name, cardname)
                    f.write_errorlog(s)
        tell = f.tell()
        f.seek(lenpos)
        f.write_dword(cardslen)
        f.seek(tell)

        lenpos = f.tell()
        f.write_dword(0)
        cardslen = 0
        for card in beasts:
            try:
                pos = f.tell()
                beast.BeastCard.unconv(f, card, True)
                cardslen += 1
            except cw.binary.cwfile.UnsupportedError:
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は対象エンジンで使用できないため、変換しません。\n" % (name, cardname)
                    f.write_errorlog(s)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                f.seek(pos)
                if f.write_errorlog:
                    cardname = card.gettext("Property/Name", "")
                    s = u"%s の所持する %s は変換できませんでした。\n" % (name, cardname)
                    f.write_errorlog(s)
        tell = f.tell()
        f.seek(lenpos)
        f.write_dword(cardslen)
        f.seek(tell)

        f.write_dword(len(coupons))
        for cp in coupons:
            coupon.Coupon.unconv(f, cp)

        f.truncate()

class AdventurerCard(base.CWBinaryBase):
    """wcpファイル(type=1)。冒険者データが中に入っているだけ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 1
        self.fname = self.get_fname()

        if f:
            # 不明(0,0,0,0,0)
            for _cnt in xrange(5):
                _b = f.byte()

            self.adventurer = Adventurer(self, f, yadodata=yadodata)

        else:
            self.adventurer = None

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
        Adventurer.unconv(f, data, None)

class AdventurerWithImage(base.CWBinaryBase):
    """埋め込み画像付き冒険者データ。
    パーティデータを読み込むときに使う。
    """
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        image = f.image()
        self.adventurer = Adventurer(self, f)
        self.adventurer.image = image

    def get_data(self):
        return self.adventurer.get_data()

    def get_f9data(self):
        return self.adventurer.get_f9data()

    def create_xml(self, dpath):
        """adventurerのデータだけxml化する。"""
        path = self.adventurer.create_xml(dpath)
        self.xmlpath = self.adventurer.xmlpath
        return path

    @staticmethod
    def unconv(f, data, logdata):
        e = data.find("Property/ImagePaths")
        if e is None:
            e = data.find("Property/ImagePath")
        f.write_image(base.CWBinaryBase.import_image(f, e, defpostype="Center"))
        if logdata is None:
            cw.character.Character(data=cw.data.xml2etree(element=data)).set_fullrecovery()
        Adventurer.unconv(f, data, logdata)

class AdventurerHeader(base.CWBinaryBase):
    """wchファイル(type=0)。おそらく宿帳表示用の簡易データと思われる。
    必要なデータは埋め込み画像くらい？
    """
    def __init__(self, parent, f, yadodata=False, dataversion=10):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.type = 0
        self.fname = self.get_fname()
        if 10 <= dataversion:
            # 1.28以降
            _b = f.byte() # 不明(0)
            _b = f.byte() # 不明(0)
            self.name = f.string()
            self.image = f.image()
            self.level = f.byte()
            _b = f.byte() # 不明(0)
            self.coupons = f.string(True)
            _w = f.word() # 不明(0)
            # ここからは16ビット符号付き整数が並んでると思われるが面倒なので
            self.ep = f.byte()
            _b = f.byte()
            self.dex = f.byte()
            _b = f.byte()
            self.agl = f.byte()
            _b = f.byte()
            self.int = f.byte()
            _b = f.byte()
            self.str = f.byte()
            _b = f.byte()
            self.vit = f.byte()
            _b = f.byte()
            self.min = f.byte()
            _b = f.byte()
        else:
            # 1.20
            _dataversion = f.string()
            self.name = f.string()
            self.image = f.image()
            self.level = f.dword()
            _dw = f.dword() # 不明(F)
            self.coupons = []
            couponnum = f.dword()
            for _i in xrange(couponnum):
                self.coupons.append(f.string())
            self.ep = self.level * 10

    @staticmethod
    def unconv(f, data, fname):
        name = ""
        image = None
        level = 0
        coupons = ""
        dex = 0
        agl = 0
        inte = 0
        stre = 0
        vit = 0
        mind = 0
        ep = 0

        for e in data:
            if e.tag == "Property":
                for prop in e:
                    if prop.tag == "Name":
                        name = prop.text
                    elif prop.tag in ("ImagePath", "ImagePaths"):
                        image = base.CWBinaryBase.import_image(f, prop, defpostype="Center")
                    elif prop.tag == "Level":
                        level = int(prop.text)
                    elif prop.tag == "Ability":
                        for ae in prop:
                            if ae.tag == "Physical":
                                dex = int(ae.get("dex"))
                                agl = int(ae.get("agl"))
                                inte = int(ae.get("int"))
                                stre = int(ae.get("str"))
                                vit = int(ae.get("vit"))
                                mind = int(ae.get("min"))
                    elif prop.tag == "Coupons":
                        seq = []
                        for ce in prop:
                            seq.append(ce.text)
                            if ce.text == u"＠ＥＰ":
                                ep = int(ce.get("value", "0"))
                        coupons = cw.util.encodetextlist(seq)

        f.write_word(0) # 不明
        f.write_string(name)
        f.write_image(image)
        f.write_word(level)
        f.write_string(coupons, True)
        f.write_word(0) # 不明
        f.write_word(ep)
        f.write_word(dex)
        f.write_word(agl)
        f.write_word(inte)
        f.write_word(stre)
        f.write_word(vit)
        f.write_word(mind)

def main():
    pass

if __name__ == "__main__":
    main()
