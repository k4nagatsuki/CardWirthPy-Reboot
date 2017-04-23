#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base
import bgimage
import dialog
import effectmotion

import cw


class Content(base.CWBinaryBase):
    def __init__(self, parent, f, stratum):
        base.CWBinaryBase.__init__(self, parent, f)
        self.xmltype = "Content"

        self.children = []

        if f is None:
            return

        eventstack = []
        children = []

        if 255 < stratum:
            # ある程度以上ツリー階層が深くなったら
            # 再帰を回避する方向に切り替える
            while True:
                tag, ctype = self.conv_contenttype(f.byte())
                name = f.string()
                children_num = f.dword()
                if children_num <= 39999:
                    version = 2
                elif children_num <= 49999:
                    version = 4
                    children_num -= 40000
                else:
                    version = 5
                    children_num -= 50000

                eventstack.append((tag, ctype, name, version))

                if children_num == 0:
                    break
                elif children_num == 1:
                    # 子コンテントが1件だけの時は情報をスタックにためて再帰回避
                    continue
                else:
                    # stratumはすでにmaxであるため加算しない
                    children = [Content(self, f, stratum) for _cnt in xrange(children_num)]
                    break

            for i, (tag, ctype, name, version) in enumerate(reversed(eventstack)):
                if i+1 == len(eventstack):
                    e = self
                else:
                    e = Content(self, None, stratum)
                e._read_properties(f, tag, ctype, name, version)
                for child in children:
                    e.children.append(child)
                children = [e]
        else:
            tag, ctype = self.conv_contenttype(f.byte())
            name = f.string()
            children_num = f.dword()
            if children_num <= 39999:
                version = 2
            elif children_num <= 49999:
                version = 4
                children_num -= 40000
            else:
                version = 5
                children_num -= 50000

            self.children = [Content(self, f, stratum+1) for _cnt in xrange(children_num)]

            self._read_properties(f, tag, ctype, name, version)

    def _read_properties(self, f, tag, ctype, name, version):
        self.tag = tag
        self.type = ctype
        self.name = name
        self.version = version

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
            self.bgimgs = [bgimage.BgImage(self, f) for _cnt in xrange(bgimgs_num)]
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
            self.properties["ignite"] = False
            motions_num = f.dword()
            self.motions = [effectmotion.EffectMotion(self, f, dataversion=self.version)
                                            for _cnt in xrange(motions_num)]
        elif self.tag == "Branch" and self.type == "Select":
            self.properties["targetall"] = f.bool()
            if f.bool():
                self.properties["method"] = "Random"
            else:
                self.properties["method"] = "Manual"
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
            self.properties["startaction"] = "NextRound"
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
                self.coupons = [cw.binary.coupon.Coupon(self, f) for _cnt in xrange(coupons_num)]
                if self.coupons and self.coupons[0].name == "":
                    self.properties["initialValue"] = self.coupons[0].value
                    self.coupons = self.coupons[1:]
                else:
                    self.properties["initialValue"] = 0
            dialogs_num = f.dword()
            self.dialogs = [cw.binary.dialog.Dialog(self, f) for _cnt in xrange(dialogs_num)]
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
                self.properties["minLevel"] = f.dword()
                self.properties["maxLevel"] = f.dword()
            if (style & 0b10) <> 0:
                self.properties["status"] = self.conv_statustype(f.byte())
        elif self.tag == "Branch" and self.type == "KeyCode": # 1.50
            self.properties["targetkc"] = self.conv_keycoderange(f.byte())
            ect = self.conv_effectcardtype(f.byte())
            if ect == "All":
                self.properties["skill"] = True
                self.properties["item"] = True
                self.properties["beast"] = True
                self.properties["hand"] = True # BUG: CardWirth 1.50ではアイテムが対象にあると手札も検索される
            elif ect == "Skill":
                self.properties["skill"] = True
                self.properties["item"] = False
                self.properties["beast"] = False
                self.properties["hand"] = False
            elif ect == "Item":
                self.properties["skill"] = False
                self.properties["item"] = True
                self.properties["beast"] = False
                self.properties["hand"] = True # BUG: CardWirth 1.50ではアイテムが対象にあると手札も検索される
            elif ect == "Beast":
                self.properties["skill"] = False
                self.properties["item"] = False
                self.properties["beast"] = True
                self.properties["hand"] = False
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
        if not self.data is None:
            return self.data

        contentsline = None
        child = self
        while True:
            child.data = cw.data.make_element(child.tag)
            if child.type:
                child.data.set("type", child.type)
            child.data.set("name", child.name)

            for key, value in child.properties.iteritems():
                if isinstance(value, (str, unicode)):
                    child.data.set(key, value)
                else:
                    child.data.set(key, str(value))

            if child.tag == "Talk" and child.type == "Message":
                child.data.append(cw.data.make_element("Text", child.text))
            elif child.tag == "Change" and child.type == "BgImage":
                e = cw.data.make_element("BgImages")
                for bgimg in child.bgimgs:
                    e.append(bgimg.get_data())
                child.data.append(e)
            elif child.tag == "Effect" and child.type == "":
                e = cw.data.make_element("Motions")
                for motion in child.motions:
                    e.append(motion.get_data())
                child.data.append(e)
            elif child.tag == "Talk" and child.type == "Dialog":
                if child.properties["targetm"] == "Valued":
                    e = cw.data.make_element("Coupons")
                    for coupon in child.coupons:
                        e.append(coupon.get_data())
                    child.data.append(e)
                e = cw.data.make_element("Dialogs")
                for dialog in child.dialogs:
                    e.append(dialog.get_data())
                child.data.append(e)
            elif child.tag == "Branch" and child.type == "RandomSelect": # 1.30
                e = cw.data.make_element("CastRanges")
                for castrange in child.castranges:
                    e.append(cw.data.make_element("CastRange", castrange))
                child.data.append(e)

            if not contentsline is None:
                contentsline.append(child.data)

            if len(child.children) == 1:
                if contentsline is None:
                    contentsline = cw.data.make_element("ContentsLine")
                    contentsline.append(child.data)
                child = child.children[0]
                continue # 再帰回避
            else:
                if child.children:
                    e = cw.data.make_element("Contents")
                    for child2 in child.children:
                        e.append(child2.get_data())
                    child.data.append(e)
                break

        if contentsline is None:
            return self.data
        else:
            return contentsline

    @staticmethod
    def unconv(f, data):
        if data.tag == "ContentsLine":
            for child in data[:-1]:
                Content._unconv_header(f, child)
                f.write_dword(1 + 50000)
            Content.unconv(f, data[-1])
            for child in reversed(data[:-1]):
                Content._unconv_properties(f, child)

        else:
            Content._unconv_header(f, data)

            children = ()
            for e in data:
                if e.tag == "Contents":
                    children = e
            f.write_dword(len(children) + 50000)
            for child in children:
                Content.unconv(f, child)

            Content._unconv_properties(f, data)

    @staticmethod
    def _unconv_header(f, data):
        tag = data.tag
        ctype = data.get("type", "")
        name = data.get("name", "")
        f.write_byte(base.CWBinaryBase.unconv_contenttype(tag, ctype))
        f.write_string(name)

    @staticmethod
    def _unconv_properties(f, data):
        # 宿データの埋め込みカードのコンテントは
        # 子コンテントデータの後ろに"dword()"(4)が埋め込まれている。
        f.write_dword(4)

        tag = data.tag
        ctype = data.get("type", "")

        if tag == "Start" and ctype == "":
            pass
        elif tag == "Link" and ctype == "Start":
            f.write_string(data.get("link"))
        elif tag == "Start" and ctype == "Battle":
            f.write_dword(int(data.get("id")))
        elif tag == "End" and ctype == "":
            f.write_bool(cw.util.str2bool(data.get("complete")))
        elif tag == "End" and ctype == "BadEnd":
            pass
        elif tag == "Change" and ctype == "Area":
            if data.get("transition", "Default") <> "Default":
                f.check_wsnversion("")
            f.write_dword(int(data.get("id")))
        elif tag == "Talk" and ctype == "Message":
            if data.getint(".", "columns", 1) <> 1:
                f.check_wsnversion("1")
            if data.getbool(".", "centeringx", False):
                f.check_wsnversion("2")
            if data.getbool(".", "centeringy", False):
                f.check_wsnversion("2")
            text = ""
            for e in data:
                if e.tag == "Text":
                    text= e.text
                    break

            e_imgpaths = data.find("ImagePaths")
            if not e_imgpaths is None:
                if 1 < len(e_imgpaths):
                    f.check_wsnversion("1")
                base.CWBinaryBase.check_imgpath(f, e_imgpaths.find("ImagePath"), "TopLeft")
                imgpath2 = prop.gettext("ImagePath", "")
                if imgpath2:
                    imgpath = base.CWBinaryBase.materialpath(imgpath2)
                else:
                    imgpath = u""
            else:
                base.CWBinaryBase.check_imgpath(f, data, "TopLeft")
                imgpath = data.get("path")
            f.write_string(base.CWBinaryBase.materialpath(imgpath))
            f.write_string(text, True)
        elif tag == "Play" and ctype == "Bgm":
            f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
            f.check_bgmoptions(data)
        elif tag == "Change" and ctype == "BgImage":
            if data.get("transition", "Default") <> "Default":
                f.check_wsnversion("")
            bgimgs = []
            for e in data:
                if e.tag == "BgImages":
                    bgimgs = e
                    break
            f.write_dword(len(bgimgs))
            for bgimg in bgimgs:
                bgimage.BgImage.unconv(f, bgimg)
        elif tag == "Play" and ctype == "Sound":
            f.write_string(base.CWBinaryBase.materialpath(data.get("path")))
            f.check_soundoptions(data)
        elif tag == "Wait" and ctype == "":
            f.write_dword(int(data.get("value")))
        elif tag == "Effect" and ctype == "":
            if data.getbool(".", "refability", False):
                f.check_wsnversion("2")
            if data.getbool(".", "ignite", False):
                f.check_wsnversion("2")
            f.write_dword(int(data.get("level")))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
            f.write_byte(base.CWBinaryBase.unconv_card_effecttype(data.get("effecttype")))
            f.write_byte(base.CWBinaryBase.unconv_card_resisttype(data.get("resisttype")))
            f.write_dword(int(data.get("successrate")))
            f.write_string(base.CWBinaryBase.materialpath(data.get("sound")))
            f.write_byte(base.CWBinaryBase.unconv_card_visualeffect(data.get("visual")))
            f.check_soundoptions(data)
            motions = []
            for e in data:
                if e.tag == "Motions":
                    motions = e
                    break
            f.write_dword(len(motions))
            for motion in motions:
                effectmotion.EffectMotion.unconv(f, motion)
        elif tag == "Branch" and ctype == "Select":
            f.write_bool(cw.util.str2bool(data.get("targetall")))
            if "method" in data.attrib:
                smethod = data.get("method")
                if not smethod in ("Manual", "Random"):
                    f.check_wsnversion("1")
                f.write_bool(smethod == "Random")
            else:
                f.write_bool(cw.util.str2bool(data.get("random")))
        elif tag == "Branch" and ctype == "Ability":
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
            f.write_dword(base.CWBinaryBase.unconv_card_physicalability(data.get("physical")))
            f.write_dword(base.CWBinaryBase.unconv_card_mentalability(data.get("mental")))
        elif tag == "Branch" and ctype == "Random":
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and ctype == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Set" and ctype == "Flag":
            f.write_string(data.get("flag"))
            f.write_bool(cw.util.str2bool(data.get("value")))
        elif tag == "Branch" and ctype == "MultiStep":
            f.write_string(data.get("step"))
        elif tag == "Set" and ctype == "Step":
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and ctype == "Cast":
            f.write_dword(int(data.get("id")))
        elif tag == "Branch" and ctype == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and ctype == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and ctype == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Branch" and ctype == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Branch" and ctype == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and ctype == "Coupon":
            # Wsn.1方式
            coupon = data.get("coupon", "")
            # Wsn.2方式(couponnames)
            names =[coupon] if coupon else []
            for e in data.getfind("Coupons", raiseerror=False):
                names.append(e.text)
            if len(names) > 1:
                f.check_wsnversion("2")
            elif len(names) == 1:
                coupon = names[0]
            base.CWBinaryBase.check_coupon(f, coupon)
            f.write_string(coupon)
            f.write_dword(0)
            f.write_byte(base.CWBinaryBase.unconv_target_scope_coupon(data.get("targets"), f))
        elif tag == "Get" and ctype == "Cast":
            if data.getattr(".", "startaction", "NextRound") <> "NextRound":
                f.check_wsnversion("2")
            f.write_dword(int(data.get("id")))
        elif tag == "Get" and ctype == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and ctype == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and ctype == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Get" and ctype == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Get" and ctype == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Get" and ctype == "Coupon":
            base.CWBinaryBase.check_coupon(f, data.get("coupon"))
            f.write_string(data.get("coupon"))
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and ctype == "Cast":
            f.write_dword(int(data.get("id")))
        elif tag == "Lose" and ctype == "Item":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and ctype == "Skill":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and ctype == "Info":
            f.write_dword(int(data.get("id")))
        elif tag == "Lose" and ctype == "Beast":
            f.write_dword(int(data.get("id")))
            f.write_dword(int(data.get("number")))
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Lose" and ctype == "Money":
            f.write_dword(int(data.get("value")))
        elif tag == "Lose" and ctype == "Coupon":
            base.CWBinaryBase.check_coupon(f, data.get("coupon"))
            f.write_string(data.get("coupon"))
            f.write_dword(0)
            f.write_byte(base.CWBinaryBase.unconv_target_scope(data.get("targets")))
        elif tag == "Talk" and ctype == "Dialog":
            if data.getint(".", "columns", 1) <> 1:
                f.check_wsnversion("1")
            if data.getbool(".", "centeringx", False):
                f.check_wsnversion("2")
            if data.getbool(".", "centeringy", False):
                f.check_wsnversion("2")
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
        elif tag == "Set" and ctype == "StepUp":
            f.write_string(data.get("step"))
        elif tag == "Set" and ctype == "StepDown":
            f.write_string(data.get("step"))
        elif tag == "Reverse" and ctype == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Branch" and ctype == "Step":
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
        elif tag == "Elapse" and ctype == "Time":
            pass
        elif tag == "Branch" and ctype == "Level":
            f.write_bool(cw.util.str2bool(data.get("average")))
            f.write_dword(int(data.get("value")))
        elif tag == "Branch" and ctype == "Status":
            f.write_byte(base.CWBinaryBase.unconv_statustype(data.get("status"), f))
            f.write_byte(base.CWBinaryBase.unconv_target_member(data.get("targetm")))
        elif tag == "Branch" and ctype == "PartyNumber":
            f.write_dword(int(data.get("value")))
        elif tag == "Show" and ctype == "Party":
            pass
        elif tag == "Hide" and ctype == "Party":
            pass
        elif tag == "Effect" and ctype == "Break":
            pass
        elif tag == "Call" and ctype == "Start":
            f.write_string(data.get("call"))
        elif tag == "Link" and ctype == "Package":
            f.write_dword(int(data.get("link")))
        elif tag == "Call" and ctype == "Package":
            f.write_dword(int(data.get("call")))
        elif tag == "Branch" and ctype == "Area":
            pass
        elif tag == "Branch" and ctype == "Battle":
            pass
        elif tag == "Branch" and ctype == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Get" and ctype == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Lose" and ctype == "CompleteStamp":
            f.write_string(data.get("scenario"))
        elif tag == "Branch" and ctype == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Get" and ctype == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Lose" and ctype == "Gossip":
            f.write_string(data.get("gossip"))
        elif tag == "Branch" and ctype == "IsBattle":
            pass
        elif tag == "Redisplay" and ctype == "":
            if data.get("transition", "Default") <> "Default":
                f.check_version("CardWirthPy 0.12")
        elif tag == "Check" and ctype == "Flag":
            f.write_string(data.get("flag"))
        elif tag == "Substitute" and ctype == "Step": # 1.30
            f.check_version(1.30)
            if data.get("from", "").lower() == "??selectedplayer":
                f.check_wsnversion("2")
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Substitute" and ctype == "Flag": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and ctype == "StepValue": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and ctype == "FlagValue": # 1.30
            f.check_version(1.30)
            f.write_string(data.get("from"))
            f.write_string(data.get("to"))
        elif tag == "Branch" and ctype == "RandomSelect": # 1.30
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
        elif tag == "Branch" and ctype == "KeyCode": # 1.50
            f.check_version(1.50)
            f.write_byte(base.CWBinaryBase.unconv_keycoderange(data.get("targetkc")))
            # Wsn.1方式
            etype = data.get("effectCardType", "All")
            skill = False
            item = False
            beast = False
            hand = False
            if etype == "All":
                skill = True
                item = True
                beast = True
            elif etype == "Skill":
                skill = True
            elif etype == "Item":
                item = True
            elif etype == "Beast":
                beast = True
            # Wsn.2方式(任意の組み合わせ)
            if "skill" in data.attrib:
                skill = data.getbool(".", "skill")
            if "item" in data.attrib:
                item = data.getbool(".", "item")
            if "beast" in data.attrib:
                beast = data.getbool(".", "beast")
            if "hand" in data.attrib:
                hand = data.getbool(".", "hand")

            if skill and item and beast and hand:
                etype = "All"
            elif skill and not item and not beast and not hand:
                etype = "Skill"
            elif not skill and item and not beast and hand:
                etype = "Item"
            elif not skill and not item and beast and not hand:
                etype = "Beast"
            else:
                f.check_wsnversion("2")
            f.write_byte(base.CWBinaryBase.unconv_effectcardtype(etype))
            f.write_string(data.get("keyCode"))
        elif tag == "Check" and ctype == "Step": # 1.50
            f.check_version(1.50)
            f.write_string(data.get("step"))
            f.write_dword(int(data.get("value")))
            f.write_byte(base.CWBinaryBase.unconv_comparison4(data.get("comparison")))
        elif tag == "Branch" and ctype == "Round": # 1.50
            f.check_version(1.50)
            f.write_byte(base.CWBinaryBase.unconv_comparison3(data.get("comparison")))
            f.write_dword(int(data.get("round")))
        elif tag == "Replace" and ctype == "BgImage": # Wsn.1
            f.check_wsnversion("1")
        elif tag == "Lose" and ctype == "BgImage": # Wsn.1
            f.check_wsnversion("1")
        elif tag == "Move" and ctype == "BgImage": # Wsn.1
            f.check_wsnversion("1")
        elif tag == "Branch" and ctype == "MultiCoupon":  # Wsn.2
            f.check_wsnversion("2")
        elif tag == "Branch" and ctype == "MultiRandom":  # Wsn.2
            f.check_wsnversion("2")
        else:
            raise ValueError(tag + ", " + ctype)

def main():
    pass

if __name__ == "__main__":
    main()
