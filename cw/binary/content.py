#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import bgimage
import dialog
import effectmotion
import xmltemplate

import cw


class Content(base.CWBinaryBase):
    def __init__(self, parent, f):
        base.CWBinaryBase.__init__(self, parent, f)

        tag, type = self.conv_contenttype(f.byte())

        self.xmltype = "Content"
        self.tag = tag
        self.type = type
        self.name = f.string()
        children_num = f.dword()
        if children_num <= 39999:
            self.version = 2
        elif children_num <= 49999:
            self.version = 4
            children_num -= 40000
        else:
            self.version = 5
            children_num -= 50000

        self.children = [Content(self, f) for cnt in xrange(children_num)]

        # 宿データの埋め込みカードのコンテントは
        # 子コンテントデータの後ろに"dword()"(4)が埋め込まれている。
        if 5 <= self.version:
            f.dword()

        self.properties = {}

        if self.tag == "Start" and self.type == "":
            pass
        elif self.tag == "Link" and self.type == "Start":
            self.properties["link"] = f.string()
        elif self.tag == "Start" and self.type == "Battle":
            self.properties["id"] = f.dword()
        elif self.tag == "End" and self.type == "":
            self.properties["complete"] = f.bool()
        elif self.tag == "End" and self.type == "BadEnd":
            pass
        elif self.tag == "Change" and self.type == "Area":
            self.properties["id"] = f.dword()
        elif self.tag == "Talk" and self.type == "Message":
            self.properties["path"] = self.get_materialpath(f.string())
            self.text = f.string(True)
        elif self.tag == "Play" and self.type == "Bgm":
            self.properties["path"] = self.get_materialpath(f.string())
        elif self.tag == "Change" and self.type == "BgImage":
            bgimgs_num = f.dword()
            self.bgimgs = [bgimage.BgImage(self, f) for cnt in xrange(bgimgs_num)]
        elif self.tag == "Play" and self.type == "Sound":
            self.properties["path"] = self.get_materialpath(f.string())
        elif self.tag == "Wait" and self.type == "":
            self.properties["value"] = f.dword()
        elif self.tag == "Effect" and self.type == "":
            self.properties["level"] = f.dword()
            targetm = f.byte()
            self.properties["targetm"] = self.conv_target_member(targetm)
            self.properties["effecttype"] = self.conv_card_effecttype(f.byte())
            self.properties["resisttype"] = self.conv_card_resisttype(f.byte())
            self.properties["successrate"] = f.dword()
            self.properties["sound"] = self.get_materialpath(f.string())
            self.properties["visual"] = self.conv_card_visualeffect(f.byte())
            motions_num = f.dword()
            self.motions = [effectmotion.EffectMotion(self, f, dataversion=self.version)
                                            for cnt in xrange(motions_num)]
        elif self.tag == "Branch" and self.type == "Select":
            self.properties["targetall"] = f.bool()
            self.properties["random"] = f.bool()
        elif self.tag == "Branch" and self.type == "Ability":
            self.properties["value"] = f.dword()
            targetm = f.byte()
            self.properties["targetm"] = self.conv_target_member(targetm)
            self.properties["physical"] = self.conv_card_physicalability(f.dword())
            self.properties["mental"] = self.conv_card_mentalability(f.dword())
        elif self.tag == "Branch" and self.type == "Random":
            self.properties["value"] = f.dword()
        elif self.tag == "Branch" and self.type == "Flag":
            self.properties["flag"] = f.string()
        elif self.tag == "Set" and self.type == "Flag":
            self.properties["flag"] = f.string()
            self.properties["value"] = f.bool()
        elif self.tag == "Branch" and self.type == "MultiStep":
            self.properties["step"] = f.string()
        elif self.tag == "Set" and self.type == "Step":
            self.properties["step"] = f.string()
            self.properties["value"] = f.dword()
        elif self.tag == "Branch" and self.type == "Cast":
            self.properties["id"] = f.dword()
        elif self.tag == "Branch" and self.type == "Item":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Branch" and self.type == "Skill":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Branch" and self.type == "Info":
            self.properties["id"] = f.dword()
        elif self.tag == "Branch" and self.type == "Beast":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Branch" and self.type == "Money":
            self.properties["value"] = f.dword()
        elif self.tag == "Branch" and self.type == "Coupon":
            self.properties["coupon"] = f.string()
            f.dword() # 得点(不使用)
            self.properties["targets"] = self.conv_target_scope_coupon(f.byte())
        elif self.tag == "Get" and self.type == "Cast":
            self.properties["id"] = f.dword()
        elif self.tag == "Get" and self.type == "Item":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Get" and self.type == "Skill":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Get" and self.type == "Info":
            self.properties["id"] = f.dword()
        elif self.tag == "Get" and self.type == "Beast":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Get" and self.type == "Money":
            self.properties["value"] = f.dword()
        elif self.tag == "Get" and self.type == "Coupon":
            self.properties["coupon"] = f.string()
            self.properties["value"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Lose" and self.type == "Cast":
            self.properties["id"] = f.dword()
        elif self.tag == "Lose" and self.type == "Item":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Lose" and self.type == "Skill":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Lose" and self.type == "Info":
            self.properties["id"] = f.dword()
        elif self.tag == "Lose" and self.type == "Beast":
            self.properties["id"] = f.dword()
            if self.version <= 2:
                self.properties["number"] = 1
                self.properties["targets"] = self.conv_target_scope(4)
            else:
                self.properties["number"] = f.dword()
                self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Lose" and self.type == "Money":
            self.properties["value"] = f.dword()
        elif self.tag == "Lose" and self.type == "Coupon":
            self.properties["coupon"] = f.string()
            f.dword() # 得点(不使用)
            self.properties["targets"] = self.conv_target_scope(f.byte())
        elif self.tag == "Talk" and self.type == "Dialog":
            member = self.conv_target_member_dialog(f.byte())
            self.properties["targetm"] = member
            if member == "Valued":
                coupons_num = f.dword()
                self.coupons = [cw.binary.coupon.Coupon(self, f) for cnt in xrange(coupons_num)]
                if self.coupons and self.coupons[0].name == "":
                    self.properties["initialValue"] = self.coupons[0].value
                    self.coupons = self.coupons[1:]
                else:
                    self.properties["initialValue"] = 0
            dialogs_num = f.dword()
            self.dialogs = [cw.binary.dialog.Dialog(self, f) for cnt in xrange(dialogs_num)]
        elif self.tag == "Set" and self.type == "StepUp":
            self.properties["step"] = f.string()
        elif self.tag == "Set" and self.type == "StepDown":
            self.properties["step"] = f.string()
        elif self.tag == "Reverse" and self.type == "Flag":
            self.properties["flag"] = f.string()
        elif self.tag == "Branch" and self.type == "Step":
            self.properties["step"] = f.string()
            self.properties["value"] = f.dword()
        elif self.tag == "Elapse" and self.type == "Time":
            pass
        elif self.tag == "Branch" and self.type == "Level":
            self.properties["average"] = f.bool()
            self.properties["value"] = f.dword()
        elif self.tag == "Branch" and self.type == "Status":
            self.properties["status"] = self.conv_statustype(f.byte())
            targetm = f.byte()
            self.properties["targetm"] = self.conv_target_member(targetm)
        elif self.tag == "Branch" and self.type == "PartyNumber":
            self.properties["value"] = f.dword()
        elif self.tag == "Show" and self.type == "Party":
            pass
        elif self.tag == "Hide" and self.type == "Party":
            pass
        elif self.tag == "Effect" and self.type == "Break":
            pass
        elif self.tag == "Call" and self.type == "Start":
            self.properties["call"] = f.string()
        elif self.tag == "Link" and self.type == "Package":
            self.properties["link"] = f.dword()
        elif self.tag == "Call" and self.type == "Package":
            self.properties["call"] = f.dword()
        elif self.tag == "Branch" and self.type == "Area":
            pass
        elif self.tag == "Branch" and self.type == "Battle":
            pass
        elif self.tag == "Branch" and self.type == "CompleteStamp":
            self.properties["scenario"] = f.string()
        elif self.tag == "Get" and self.type == "CompleteStamp":
            self.properties["scenario"] = f.string()
        elif self.tag == "Lose" and self.type == "CompleteStamp":
            self.properties["scenario"] = f.string()
        elif self.tag == "Branch" and self.type == "Gossip":
            self.properties["gossip"] = f.string()
        elif self.tag == "Get" and self.type == "Gossip":
            self.properties["gossip"] = f.string()
        elif self.tag == "Lose" and self.type == "Gossip":
            self.properties["gossip"] = f.string()
        elif self.tag == "Branch" and self.type == "IsBattle":
            pass
        elif self.tag == "Redisplay" and self.type == "":
            pass
        elif self.tag == "Check" and self.type == "Flag":
            self.properties["flag"] = f.string()
        elif self.tag == "Substitute" and self.type == "Step": # 1.30
            self.properties["from"] = f.string()
            self.properties["to"] = f.string()
        elif self.tag == "Substitute" and self.type == "Flag": # 1.30
            self.properties["from"] = f.string()
            self.properties["to"] = f.string()
        elif self.tag == "Branch" and self.type == "StepValue": # 1.30
            self.properties["from"] = f.string()
            self.properties["to"] = f.string()
        elif self.tag == "Branch" and self.type == "FlagValue": # 1.30
            self.properties["from"] = f.string()
            self.properties["to"] = f.string()
        elif self.tag == "Branch" and self.type == "RandomSelect": # 1.30
            self.castranges = self.conv_castranges(f.byte())
            style = f.byte()
            if (style & 0b01) <> 0:
                self.properties["levelmin"] = f.dword()
                self.properties["levelmax"] = f.dword()
            if (style & 0b10) <> 0:
                self.properties["status"] = self.conv_statustype(f.byte())
        elif self.tag == "Branch" and self.type == "KeyCode": # 1.50
            self.properties["targetkc"] = self.conv_keycoderange(f.byte())
            self.properties["effectCardType"] = self.conv_effectcardtype(f.byte())
            self.properties["keyCode"] = f.string()
        elif self.tag == "Check" and self.type == "Step": # 1.50
            self.properties["step"] = f.string()
            self.properties["value"] = f.dword()
            self.properties["comparison"] = self.conv_comparison4(f.byte())
        elif self.tag == "Branch" and self.type == "Round": # 1.50
            self.properties["comparison"] = self.conv_comparison3(f.byte())
            self.properties["round"] = f.dword()
        else:
            raise ValueError(self.tag + ", " + self.type)

        self.data = None

    def get_data(self):
        if self.data is None:
            self.data = cw.data.make_element(self.tag)
            if self.type:
                self.data.set("type", self.type)
            self.data.set("name", self.name)
            for key, value in self.properties.iteritems():
                if isinstance(value, (str, unicode)):
                    self.data.set(key, value)
                else:
                    self.data.set(key, str(value))
            e = cw.data.make_element("Contents")
            for child in self.children:
                e.append(child.get_data())
            self.data.append(e)

            if self.tag == "Talk" and self.type == "Message":
                self.data.append(cw.data.make_element("Text", self.text))
            elif self.tag == "Change" and self.type == "BgImage":
                e = cw.data.make_element("BgImages")
                for bgimg in self.bgimgs:
                    e.append(bgimg.get_data())
                self.data.append(e)
            elif self.tag == "Effect" and self.type == "":
                e = cw.data.make_element("Motions")
                for motion in self.motions:
                    e.append(motion.get_data())
                self.data.append(e)
            elif self.tag == "Talk" and self.type == "Dialog":
                if self.properties["targetm"] == "Valued":
                    e = cw.data.make_element("Coupons")
                    for coupon in self.coupons:
                        e.append(coupon.get_data())
                    self.data.append(e)
                e = cw.data.make_element("Dialogs")
                for dialog in self.dialogs:
                    e.append(dialog.get_data())
                self.data.append(e)
            elif self.tag == "Branch" and self.type == "RandomSelect": # 1.30
                e = cw.data.make_element("CastRanges")
                for range in self.castranges:
                    e.append(cw.data.make_element("CastRange", range))
                self.data.append(e)

        return self.data

    @staticmethod
    def unconv(f, data):
        tag = data.tag
        type = data.get("type", "")
        name = data.get("name", "")
        children = []

        for e in data:
            if e.tag == "Contents":
                children = e

        f.write_byte(base.CWBinaryBase.unconv_contenttype(tag, type))
        f.write_string(name)
        f.write_dword(len(children) + 50000)
        for child in children:
            Content.unconv(f, child)
        # 宿データの埋め込みカードのコンテントは
        # 子コンテントデータの後ろに"dword()"(4)が埋め込まれている。
        f.write_dword(4)

        if tag == "Start" and type == "":
            pass
        elif tag == "Link" and type == "Start":
            f.write_string(data.get("link"))
        elif tag == "Start" and type == "Battle":
            f.write_dword(int(data.get("id")))
        elif tag == "End" and type == "":
            f.write_bool(cw.util.str2bool(data.get("complete")))
        elif tag == "End" and type == "BadEnd":
            pass
        elif tag == "Change" and type == "Area":
            if data.get("transition", "Default") <> "Default" or\
                    data.get("transitionspeed", "Default") <> "Default":
                f.check_version("CardWirthPy 0.12")
            f.write_dword(int(data.get("id")))
        elif tag == "Talk" and type == "Message":
            text = ""
            for e in data:
                if e.tag == "Text":
                    text= e.text
                    break
            f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
            f.write_string(text, True)
        elif tag == "Play" and type == "Bgm":
            f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
        elif tag == "Change" and type == "BgImage":
            if data.get("transition", "Default") <> "Default" or\
                    data.get("transitionspeed", "Default") <> "Default":
                f.check_version("CardWirthPy 0.12")
            bgimgs = []
            for e in data:
                if e.tag == "BgImages":
                    bgimgs = e
                    break
            f.write_dword(len(bgimgs))
            for bgimg in bgimgs:
                bgimage.BgImage.unconv(f, bgimg)
        elif tag == "Play" and type == "Sound":
            f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
        elif tag == "Wait" and type == "":
            f.write_dword(int(data.get("value")))
        elif tag == "Effect" and type == "":
            f.write_dword(int(data.get("level")))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
            f.write_byte(base.CWBinaryBase.unconv_card_effecttype(data.get("effecttype")))
            f.write_byte(base.CWBinaryBase.unconv_card_resisttype(data.get("resisttype")))
            f.write_dword(int(data.get("successrate")))
            f.write_string(base.CWBinaryBase.materialpath(data.get("sound")))
            f.write_byte(base.CWBinaryBase.unconv_card_visualeffect(data.get("visual")))
            motions = []
            for e in data:
                if e.tag == "Motions":
                    motions = e
                    break
            f.write_dword(len(motions))
            for motion in motions:
                effectmotion.EffectMotion.unconv(f, motion)
        elif tag == "Branch" and type == "Select":
            f.write_bool(cw.util.str2bool(data.get("targetall")))
            f.write_bool(cw.util.str2bool(data.get("random")))
        elif tag == "Branch" and type == "Ability":
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
            f.write_dword(base.CWBinaryBase.unconv_card_physicalability(data.get("physical")))
            f.write_dword(base.CWBinaryBase.unconv_card_mentalability(data.get("mental")))
        elif tag == "Branch" and type == "Random":
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and type == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Set" and type == "Flag":
            f.write_string(data.get("flag"))
            f.write_bool(cw.util.str2bool(data.get("value")))
        elif tag == "Branch" and type == "MultiStep":
            f.write_string(data.get("step"))
        elif tag == "Set" and type == "Step":
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and type == "Cast":
            f.write_dword(int(data.get("id")))
        elif tag == "Branch" and type == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and type == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and type == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Branch" and type == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and type == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and type == "Coupon":
            f.write_string(data.get("coupon"))
            f.write_dword(0)
            f.write_byte(base.CWBinaryBase.unconv_target_scope_coupon(data.get("targets"), f))
        elif tag == "Get" and type == "Cast":
            f.write_dword(int(data.get("id")))
        elif tag == "Get" and type == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and type == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and type == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Get" and type == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and type == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Get" and type == "Coupon":
            f.write_string(data.get("coupon"))
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and type == "Cast":
            f.write_dword(int(data.get("id")))
        elif tag == "Lose" and type == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and type == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and type == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Lose" and type == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and type == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Lose" and type == "Coupon":
            f.write_string(data.get("coupon"))
            f.write_dword(0)
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Talk" and type == "Dialog":
            targetm = data.get("targetm")
            f.write_byte(base.CWBinaryBase.unconv_target_member_dialog(targetm, f))
            if targetm == "Valued":
                coupons = []
                initvalue = data.get("initialValue", "0")
                coupons.append(cw.data.make_element("Coupon", "", attrs={"value": initvalue}))
                for e in data:
                    if e.tag == "Coupons":
                        for e_coupon in e:
                            coupons.append(e_coupon)
                f.write_dword(len(coupons))
                for coupon in coupons:
                    cw.binary.coupon.Coupon.unconv(f, coupon)
            dialogs = []
            for e in data:
                if e.tag == "Dialogs":
                    dialogs = e
                    break
            f.write_dword(len(dialogs))
            for dialog in dialogs:
                cw.binary.dialog.Dialog.unconv(f, dialog)
        elif tag == "Set" and type == "StepUp":
            f.write_string(data.get("step"))
        elif tag == "Set" and type == "StepDown":
            f.write_string(data.get("step"))
        elif tag == "Reverse" and type == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Branch" and type == "Step":
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
        elif tag == "Elapse" and type == "Time":
            pass
        elif tag == "Branch" and type == "Level":
            f.write_bool(cw.util.str2bool(data.get("average")))
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and type == "Status":
            f.write_byte(base.CWBinaryBase.unconv_statustype(data.get("status"), f))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
        elif tag == "Branch" and type == "PartyNumber":
            f.write_dword(int(data.get("value")))
        elif tag == "Show" and type == "Party":
            pass
        elif tag == "Hide" and type == "Party":
            pass
        elif tag == "Effect" and type == "Break":
            pass
        elif tag == "Call" and type == "Start":
            f.write_string(data.get("call"))
        elif tag == "Link" and type == "Package":
            f.write_dword(int(data.get("link")))
        elif tag == "Call" and type == "Package":
            f.write_dword(int(data.get("call")))
        elif tag == "Branch" and type == "Area":
            pass
        elif tag == "Branch" and type == "Battle":
            pass
        elif tag == "Branch" and type == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Get" and type == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Lose" and type == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Branch" and type == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Get" and type == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Lose" and type == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Branch" and type == "IsBattle":
            pass
        elif tag == "Redisplay" and type == "":
            if data.get("transition", "Default") <> "Default" or\
                    data.get("transitionspeed", "Default") <> "Default":
                f.check_version("CardWirthPy 0.12")
        elif tag == "Check" and type == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Substitute" and type == "Step": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Substitute" and type == "Flag": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and type == "StepValue": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and type == "FlagValue": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and type == "RandomSelect": # 1.30
            f.check_version(1.30)
            f.write_byte(base.CWBinaryBase.unconv_castranges(data.find("CastRanges")))
            levelmin = data.get("levelmin", None)
            levelmax = data.get("levelmax", None)
            status = data.get("status", None)
            style = 0
            if not (levelmin is None and levelmax is None):
                style |= 0b01
            if not status is None:
                style |= 0b10
            f.write_byte(style)
            if (style & 0b01) <> 0:
                f.write_dword(levelmin)
                f.write_dword(levelmax)
            if (style & 0b10) <> 0:
                f.write_byte(base.CWBinaryBase.unconv_statustype(status, f))
        elif tag == "Branch" and type == "KeyCode": # 1.50
            f.check_version(1.50)
            f.write_byte(base.CWBinaryBase.unconv_keycoderange(data.get("targetkc")))
            f.write_byte(base.CWBinaryBase.unconv_effectcardtype(data.get("effectCardType")))
            f.write_string(data.get("keyCode"))
        elif tag == "Check" and type == "Step": # 1.50
            f.check_version(1.50)
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_comparison4(data.get("comparison")))
        elif tag == "Branch" and type == "Round": # 1.50
            f.check_version(1.50)
            f.write_byte(base.CWBinaryBase.unconv_comparison3(data.get("comparison")))
            f.write_dword(int(data.get("round")))
        else:
            raise ValueError(tag + ", " + type)

def main():
    pass

if __name__ == "__main__":
    main()
