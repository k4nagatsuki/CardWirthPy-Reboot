#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import bgimage
import dialog
import effectmotion
import xmltemplate

import cw


class ContentBase(base.CWBinaryBase):
    def __init__(self, parent, f, tag, type):
        base.CWBinaryBase.__init__(self, parent, f)
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
            Content_unconv(f, child)
        # 宿データの埋め込みカードのコンテントは
        # 子コンテントデータの後ろに"dword()"(4)が埋め込まれている。
        f.write_dword(4)

class StartContent(ContentBase):
    pass

class LinkStartContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["link"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("link"))

class StartBattleContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class EndContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["complete"] = f.bool()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_bool(cw.util.str2bool(data.get("complete")))

class EndBadEndContent(ContentBase):
    pass

class ChangeAreaContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class TalkMessageContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["path"] = self.get_materialpath(f.string())
        self.text = f.string(True)

    def get_data(self):
        if self.data is None:
            self.data = ContentBase.get_data(self)
            self.data.append(cw.data.make_element("Text", self.text))
        return self.data

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        text = ""
        for e in data:
            if e.tag == "Text":
                text= e.text
                break
        f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
        f.write_string(text, True)

class PlayBgmContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["path"] = self.get_materialpath(f.string())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(base.CWBinaryBase.materialpath(data.get("path")))

class ChangeBgImageContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        bgimgs_num = f.dword()
        self.bgimgs = [bgimage.BgImage(self, f) for cnt in xrange(bgimgs_num)]

    def get_data(self):
        if self.data is None:
            self.data = ContentBase.get_data(self)
            e = cw.data.make_element("BgImages")
            for bgimg in self.bgimgs:
                e.append(bgimg.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        bgimgs = []
        for e in data:
            if e.tag == "BgImages":
                bgimgs = e
                break
        f.write_dword(len(bgimgs))
        for bgimg in bgimgs:
            bgimage.BgImage.unconv(f, bgimg)

class PlaySoundContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["path"] = self.get_materialpath(f.string())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(base.CWBinaryBase.materialpath(data.get("path")))

class WaitContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class EffectContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["level"] = f.dword()
        targetm = f.byte()

        # 効果コンテントの適用メンバには"選択中以外のメンバ"は存在しない。
        # 代わりに"パーティ全体"となる。
        if targetm == 2:
            targetm = 6

        self.properties["targetm"] = self.conv_target_member(targetm)
        self.properties["effecttype"] = self.conv_card_effecttype(f.byte())
        self.properties["resisttype"] = self.conv_card_resisttype(f.byte())
        self.properties["successrate"] = f.dword()
        self.properties["sound"] = self.get_materialpath(f.string())
        self.properties["visual"] = self.conv_card_visualeffect(f.byte())
        motions_num = f.dword()
        self.motions = [effectmotion.EffectMotion(self, f, dataversion=self.version)
                                        for cnt in xrange(motions_num)]

    def get_data(self):
        if self.data is None:
            self.data = ContentBase.get_data(self)
            e = cw.data.make_element("Motions")
            for motion in self.motions:
                e.append(motion.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
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

class BranchSelectContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["targetall"] = f.bool()
        self.properties["random"] = f.bool()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_bool(cw.util.str2bool(data.get("targetall")))
        f.write_bool(cw.util.str2bool(data.get("random")))

class BranchAbilityContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()
        self.properties["targetm"] = self.conv_target_member(f.byte())
        self.properties["physical"] = self.conv_card_physicalability(f.dword())
        self.properties["mental"] = self.conv_card_mentalability(f.dword())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))
        f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
        f.write_dword(base.CWBinaryBase.unconv_card_physicalability(data.get("physical")))
        f.write_dword(base.CWBinaryBase.unconv_card_mentalability(data.get("mental")))

class BranchRandomContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class BranchFlagContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["flag"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("flag"))

class SetFlagContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["flag"] = f.string()
        self.properties["value"] = f.bool()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("flag"))
        f.write_bool(cw.util.str2bool(data.get("value")))

class BranchMultiStepContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["step"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("step"))

class SetStepContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["step"] = f.string()
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("step"))
        f.write_dword(int(data.get("value")))

class BranchCastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class BranchItemContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class BranchSkillContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class BranchInfoContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class BranchBeastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class BranchMoneyContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class BranchCouponContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["coupon"] = f.string()
        f.dword() # 得点(不使用)
        self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("coupon"))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class GetCastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class GetItemContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class GetSkillContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class GetInfoContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class GetBeastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class GetMoneyContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class GetCouponContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["coupon"] = f.string()
        self.properties["value"] = f.dword()
        self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("coupon"))
        f.write_dword(int(data.get("value")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class LoseCastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class LoseItemContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class LoseSkillContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class LoseInfoContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))

class LoseBeastContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["id"] = f.dword()
        if self.version <= 2:
            self.properties["number"] = 1
            self.properties["targets"] = self.conv_target_scope(4)
        else:
            self.properties["number"] = f.dword()
            self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("id")))
        f.write_dword(int(data.get("number")))
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class LoseMoneyContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class LoseCouponContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["coupon"] = f.string()
        f.dword() # 得点(不使用)
        self.properties["targets"] = self.conv_target_scope(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("coupon"))
        f.write_dword(0)
        f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))

class TalkDialogContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["targetm"] = self.conv_target_member(f.byte())
        dialogs_num = f.dword()
        self.dialogs = [cw.binary.dialog.Dialog(self, f) for cnt in xrange(dialogs_num)]

    def get_data(self):
        if self.data is None:
            self.data = ContentBase.get_data(self)
            e = cw.data.make_element("Dialogs")
            for dialog in self.dialogs:
                e.append(dialog.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
        dialogs = []
        for e in data:
            if e.tag == "Dialogs":
                dialogs = e
                break
        f.write_dword(len(dialogs))
        for dialog in dialogs:
            cw.binary.dialog.Dialog.unconv(f, dialog)

class SetStepUpContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["step"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("step"))

class SetStepDownContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["step"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("step"))

class ReverseFlagContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["flag"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("flag"))

class BranchStepContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["step"] = f.string()
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("step"))
        f.write_dword(int(data.get("value")))

class ElapseTimeContent(ContentBase):
    pass

class BranchLevelContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["average"] = f.bool()
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_bool(cw.util.str2bool(data.get("average")))
        f.write_dword(int(data.get("value")))

class BranchStatusContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["status"] = self.conv_statustype(f.byte())
        self.properties["targetm"] = self.conv_target_member(f.byte())

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_byte(base.CWBinaryBase.unconv_statustype(data.get("status")))
        f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))

class BranchPartyNumberContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["value"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("value")))

class ShowPartyContent(ContentBase):
    pass

class HidePartyContent(ContentBase):
    pass

class EffectBreakContent(ContentBase):
    pass

class CallStartContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["call"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("call"))

class LinkPackageContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["link"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("link")))

class CallPackageContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["call"] = f.dword()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_dword(int(data.get("call")))

class BranchAreaContent(ContentBase):
    pass

class BranchBattleContent(ContentBase):
    pass

class BranchCompleteStampContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["scenario"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("scenario"))

class GetCompleteStampContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["scenario"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("scenario"))

class LoseCompleteStampContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["scenario"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("scenario"))

class BranchGossipContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["gossip"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("gossip"))

class GetGossipContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["gossip"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("gossip"))

class LoseGossipContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["gossip"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("gossip"))

class BranchIsBattleContent(ContentBase):
    pass

class RedisplayContent(ContentBase):
    pass

class CheckFlagContent(ContentBase):
    def __init__(self, parent, f, tag, type):
        ContentBase.__init__(self, parent, f, tag, type)
        self.properties["flag"] = f.string()

    @staticmethod
    def unconv(f, data):
        ContentBase.unconv(f, data)
        f.write_string(data.get("flag"))

def Content(parent, f):
    """Contentファクトリ。
    parent: CWBinaryBase
    f: CWFile
    """
    type = f.byte()
    tag, type = parent.conv_contenttype(type)
    return globals()[tag + type + "Content"](parent, f, tag, type)

def Content_unconv(f, data):
    tag = data.tag
    type = data.get("type", "")
    return globals()[tag + type + "Content"].unconv(f, data)

def main():
    pass

if __name__ == "__main__":
    main()
