#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import itertools
import wx

import cw


#-------------------------------------------------------------------------------
#  キャラクター情報編集ダイアログ
#-------------------------------------------------------------------------------

class CharacterEditDialog(wx.Dialog):

    def __init__(self, parent, selected=-1, create=False):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの情報の編集",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = True
        self.SetDoubleBuffered(True)
        self.create = create

        if self.create:
            self.infos = [CharaInfo(None)]
            selected = 0
        else:
            self.pcards = cw.cwpy.get_pcards()
            self.infos = [CharaInfo(pcard) for pcard in self.pcards]

        # 対象者
        self.targets = [u"全員"]
        for info in self.infos:
            self.targets.append(info.name)
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(max(selected, -1) + 1)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL_dbg"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL_dbg"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)
        if self.create:
            self.target.Hide()
            self.leftbtn.Hide()
            self.rightbtn.Hide()

        self.note = wx.Notebook(self)
        self.pane_req = CharaRequirementPanel(self.note, self.infos, self.create)
        self.pane_sel = CharaSelectablePanel(self.note, self.infos, self.create)
        self.note.AddPage(self.pane_req, u"必須情報")
        self.note.AddPage(self.pane_sel, u"選択情報")

        if self.create:
            self.recalc_maxlife = None
            self.recalc_parameter = None
            self.recalc_coupons = None
        else:
            self.recalc_maxlife = wx.CheckBox(self, -1, u"生命点を新しい情報に合わせて再設定する",
                                                style=wx.CHK_3STATE)
            self.recalc_parameter = wx.CheckBox(self, -1, u"能力値(カスタムの場合のみ)と属性を新しい情報に合わせて再設定する",
                                                style=wx.CHK_3STATE)
            self.recalc_coupons = wx.CheckBox(self, -1, u"初期クーポンを新しい情報に合わせて再設定する",
                                              style=wx.CHK_3STATE)

        # 標準
        self.stdbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"標準")
        # 自動
        self.autobtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"自動")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        if create:
            self.okbtn.Disable()
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        self.select_target()

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnStandardType, self.stdbtn)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_CHECKBOX, self.OnReCalcMaxLife, self.recalc_maxlife)
        self.Bind(wx.EVT_CHECKBOX, self.OnReCalcParameter, self.recalc_parameter)
        self.Bind(wx.EVT_CHECKBOX, self.OnReCalcCoupons, self.recalc_coupons)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        if not self.create:
            sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
            sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
            sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=cw.ppis(5))
            sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
            sizer_left.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=cw.ppis(5))
        sizer_left.Add(self.note, 1, flag=wx.EXPAND)

        if not self.create:
            sizer_recalc = wx.BoxSizer(wx.VERTICAL)
            sizer_recalc.Add(self.recalc_maxlife, 0, 0, cw.ppis(0))
            sizer_recalc.Add(self.recalc_parameter, 0, wx.TOP, cw.ppis(1))
            sizer_recalc.Add(self.recalc_coupons, 0, wx.TOP, cw.ppis(1))
            sizer_left.Add(sizer_recalc, 0, wx.TOP, cw.ppis(5))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.stdbtn, 0, wx.EXPAND)
        sizer_right.Add(self.autobtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def _get_infos(self):
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            return self.infos
        else:
            # 誰か一人
            return [self.infos[cindex-1]]

    def OnReCalcMaxLife(self, event):
        s3 = self.recalc_maxlife.Get3StateValue()
        if s3 == wx.CHK_UNDETERMINED:
            return
        checked = (s3 == wx.CHK_CHECKED)
        for info in self._get_infos():
            info.recalc_maxlife = checked

    def OnReCalcParameter(self, event):
        s3 = self.recalc_parameter.Get3StateValue()
        if s3 == wx.CHK_UNDETERMINED:
            return
        checked = (s3 == wx.CHK_CHECKED)
        for info in self._get_infos():
            info.recalc_parameter = checked

    def OnReCalcCoupons(self, event):
        s3 = self.recalc_coupons.Get3StateValue()
        if s3 == wx.CHK_UNDETERMINED:
            return
        checked = (s3 == wx.CHK_CHECKED)
        for info in self._get_infos():
            info.recalc_coupons = checked

    def OnLeftBtn(self, event):
        index = self.target.GetSelection()
        if index <= 0:
            self.target.SetSelection(len(self.infos))
        else:
            self.target.SetSelection(index - 1)
        self.select_target()

    def OnRightBtn(self, event):
        index = self.target.GetSelection()
        if len(self.infos) <= index:
            self.target.SetSelection(0)
        else:
            self.target.SetSelection(index + 1)
        self.select_target()

    def OnSelectTarget(self, event):
        self.select_target()

    def OnStandardType(self, event):
        seq = [u"カスタム"]
        for sample in cw.cwpy.setting.sampletypes:
            seq.append(sample.name)
        selected = seq.index(self.pane_req.type.GetLabel())
        if selected <= -1:
            selected = 0
        dlg = cw.dialog.edit.ComboEditDialog(self.TopLevelParent, u"能力型",
                                             u"能力型", seq, selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            cindex = self.target.GetSelection()
            if 0 < dlg.selected:
                ctype = cw.cwpy.setting.sampletypes[dlg.selected-1]
            else:
                ctype = None
            if cindex == 0:
                for info in self.infos:
                    info.type = ctype
            else:
                self.infos[cindex-1].type = ctype
            self.pane_req.select_target(cindex)

    def OnAutoBtn(self, event):
        self.pane_req.set_random()
        self.pane_sel.set_random()

    def OnOkBtn(self, event):
        if self.create:
            self.fpath = self.infos[0].create_adventurer()
        else:
            def func(updates, pcards):
                for i in updates:
                    pcard = pcards[i]
                    cw.cwpy.play_sound("harvest")
                    cw.animation.animate_sprite(pcard, "hide")
                    pcard.cardimg.set_levelimg(pcard.level)
                    pcard.update_image()
                    cw.animation.animate_sprite(pcard, "deal")
                if not updates:
                    cw.cwpy.play_sound("harvest")

            updates = []
            for i, info in enumerate(self.infos):
                if info.put_params(self.pcards[i]):
                    updates.append(i)
            cw.cwpy.exec_func(func, updates, self.pcards)

        self.EndModal(wx.ID_OK)

    def select_target(self):
        cindex = self.target.GetSelection()
        self.pane_req.select_target(cindex)
        self.pane_sel.select_target(cindex)

        recalc_maxlife = None
        recalc_parameter = None
        recalc_coupons = None
        for info in self._get_infos():
            if recalc_maxlife is None:
                recalc_maxlife = info.recalc_maxlife
            elif recalc_maxlife <> info.recalc_maxlife:
                recalc_maxlife = wx.CHK_UNDETERMINED

            if recalc_parameter is None:
                recalc_parameter = info.recalc_parameter
            elif recalc_parameter <> info.recalc_parameter:
                recalc_parameter = wx.CHK_UNDETERMINED

            if recalc_coupons is None:
                recalc_coupons = info.recalc_coupons
            elif recalc_coupons <> info.recalc_coupons:
                recalc_coupons = wx.CHK_UNDETERMINED

        if self.recalc_maxlife:
            self.recalc_maxlife.Set3StateValue(recalc_maxlife)
        if self.recalc_parameter:
            self.recalc_parameter.Set3StateValue(recalc_parameter)
        if self.recalc_coupons:
            self.recalc_coupons.Set3StateValue(recalc_coupons)

class CharaInfo(object):

    def __init__(self, pcard):
        if pcard:
            self.name = pcard.name
            self.race = pcard.get_race()
            self.imgpaths = []
            imgpaths = pcard.get_imagepaths()
            for info in imgpaths:
                self.imgpaths.append(cw.image.ImageInfo(cw.util.join_yadodir(info.path), base=info, basecardtype="LargeCard"))
            self.imgpaths_base = self.imgpaths
            self.can_loaded_scaledimage = pcard.data.getbool(".", "scaledimage", False)
            self.can_loaded_scaledimage_base = self.can_loaded_scaledimage
            self.level = pcard.level
            self.sex = pcard.get_sex()
            self.age = pcard.get_age()
            self.talent = pcard.get_talent()
            self.makings = pcard.get_makings()
            self.type = self.get_paramtype(pcard)
            self.physical = pcard.physical
            self.mental = pcard.mental
            self._calc_params()
            levelmax = pcard.get_levelmax()
            self.recalc_maxlife = pcard.maxlife == cw.character.calc_maxlife(pcard.physical["vit"], pcard.physical["min"], pcard.level)
            self.recalc_parameter = \
                pcard.physical["agl"] == self.agl and\
                pcard.physical["dex"] == self.dex and\
                pcard.physical["int"] == self.int and\
                pcard.physical["min"] == self.min and\
                pcard.physical["str"] == self.str and\
                pcard.physical["vit"] == self.vit and\
                pcard.mental["aggressive"] == self.aggressive and\
                pcard.mental["brave"] == self.brave and\
                pcard.mental["cautious"] == self.cautious and\
                pcard.mental["cheerful"] == self.cheerful and\
                pcard.mental["trickish"] == self.trickish and\
                pcard.feature["automaton"] == self.race.automaton and\
                pcard.feature["constructure"] == self.race.constructure and\
                pcard.feature["undead"] == self.race.undead and\
                pcard.feature["unholy"] == self.race.unholy and\
                pcard.noeffect["magic"] == self.race.noeffect_magic and\
                pcard.noeffect["weapon"] == self.race.noeffect_weapon and\
                pcard.resist["fire"] == self.race.resist_fire and\
                pcard.resist["ice"] == self.race.resist_ice and\
                pcard.weakness["fire"] == self.race.weakness_fire and\
                pcard.weakness["ice"] == self.race.weakness_ice and\
                pcard.enhance["avoid"] == self.race.avoid and\
                pcard.enhance["resist"] == self.race.resist and\
                pcard.enhance["defense"] == self.race.defense and\
                levelmax == self.levelmax

            init_coupons = {}
            for coupon in self.race.coupons:
                init_coupons[coupon[0]] = coupon[1]
            for f in cw.cwpy.setting.periods:
                if self.age == u"＿" + f.name:
                    for coupon in f.coupons:
                        init_coupons[coupon[0]] = coupon[1]
                    break
            self.recalc_coupons = True
            for coupon, value in init_coupons.iteritems():
                if not pcard.has_coupon(coupon) or pcard.get_couponvalue(coupon) <> value:
                    self.recalc_coupons = False
                    break
        else:
            self.name = ""
            self.race = cw.cwpy.setting.unknown_race
            self.imgpaths = []
            self.imgpaths_base = ""
            self.can_loaded_scaledimage = True
            self.can_loaded_scaledimage_base = self.can_loaded_scaledimage
            self.level = 1
            self.sex = cw.cwpy.setting.sexcoupons[0]
            self.age = cw.cwpy.setting.periodcoupons[0]
            self.talent = cw.cwpy.setting.naturecoupons[0]
            self.makings = set()
            self.type = None
            self._calc_params()
            self.recalc_maxlife = True
            self.recalc_parameter = True
            self.recalc_coupons = True

        self.recalc_maxlife_init = self.recalc_maxlife
        self.recalc_parameter_init = self.recalc_parameter
        self.recalc_coupons_init = self.recalc_coupons
        self.input_name = self.name

    def set_randomfeatures(self):
        """ランダムに特性を設定する。
        """
        self.race = cw.cwpy.dice.choice(cw.cwpy.setting.races) if cw.cwpy.setting.races else cw.cwpy.setting.unknown_race

        self.sex = cw.cwpy.dice.choice(cw.cwpy.setting.sexcoupons)
        self.age = cw.cwpy.dice.choice(cw.cwpy.setting.periodcoupons)
        faces = []
        for values in cw.util.get_facepaths(self.sex, self.age).itervalues():
            faces.extend(values)
        self.imgpaths = [cw.image.ImageInfo(cw.cwpy.dice.choice(faces), postype="Center")] if faces else []
        self.can_loaded_scaledimage = True

        natures = []
        for nature in cw.cwpy.setting.natures:
            if not nature.special:
                natures.append(nature)
        self.talent = u"＿" + cw.cwpy.dice.choice(natures).name

        self.makings.clear()
        self.makings.update(cw.dialog.create.get_randommakings())

        self.type = None

    def get_paramtype(self, info):
        for ctype in cw.cwpy.setting.sampletypes:
            if self.race.agl + ctype.aglbonus == info.physical["agl"] and\
               self.race.dex + ctype.dexbonus == info.physical["dex"] and\
               self.race.int + ctype.intbonus == info.physical["int"] and\
               self.race.min + ctype.minbonus == info.physical["min"] and\
               self.race.str + ctype.strbonus == info.physical["str"] and\
               self.race.vit + ctype.vitbonus == info.physical["vit"] and\
               self.race.aggressive + ctype.aggressive == info.mental["aggressive"] and\
               self.race.brave      + ctype.brave      == info.mental["brave"] and\
               self.race.cautious   + ctype.cautious   == info.mental["cautious"] and\
               self.race.cheerful   + ctype.cheerful   == info.mental["cheerful"] and\
               self.race.trickish   + ctype.trickish   == info.mental["trickish"]:
                return ctype
        return None

    def _calc_params(self):
        # 能力値の再計算
        race = self.race
        self.maxdex = race.dex + 6
        self.maxagl = race.agl + 6
        self.maxint = race.int + 6
        self.maxstr = race.str + 6
        self.maxvit = race.vit + 6
        self.maxmin = race.min + 6
        if self.type:
            self.agl = race.agl + self.type.aglbonus
            self.dex = race.dex + self.type.dexbonus
            self.int = race.int + self.type.intbonus
            self.min = race.min + self.type.minbonus
            self.str = race.str + self.type.strbonus
            self.vit = race.vit + self.type.vitbonus
            self.aggressive = self.race.aggressive + self.type.aggressive
            self.brave      = self.race.brave      + self.type.brave
            self.cautious   = self.race.cautious   + self.type.cautious
            self.cheerful   = self.race.cheerful   + self.type.cheerful
            self.trickish   = self.race.trickish   + self.type.trickish
        else:
            self.agl = race.agl
            self.dex = race.dex
            self.int = race.int
            self.min = race.min
            self.str = race.str
            self.vit = race.vit
            self.aggressive = race.aggressive
            self.brave      = race.brave
            self.cautious   = race.cautious
            self.cheerful   = race.cheerful
            self.trickish   = race.trickish
            for f in cw.cwpy.setting.sexes:
                if self.sex == u"＿" + f.name:
                    f.modulate(self)
                    break
            for f in cw.cwpy.setting.periods:
                if self.age == u"＿" + f.name:
                    f.modulate(self)
                    break
            for f in cw.cwpy.setting.natures:
                if self.talent == u"＿" + f.name:
                    f.modulate(self)
                    break
            for f in cw.cwpy.setting.makings:
                if u"＿" + f.name in self.makings:
                    f.modulate(self)
        cw.features.wrap_ability(self)

        self.physical = {
            "agl":self.agl,
            "dex":self.dex,
            "int":self.int,
            "min":self.min,
            "str":self.str,
            "vit":self.vit
        }
        self.mental = {
            "aggressive":self.aggressive,
            "brave":self.brave,
            "cautious":self.cautious,
            "cheerful":self.cheerful,
            "trickish":self.trickish
        }

        self.levelmax = 10
        for f in cw.cwpy.setting.natures:
            if self.talent == u"＿" + f.name:
                self.levelmax = f.levelmax
                break
        for f in cw.cwpy.setting.races:
            if race == f:
                for coupon in f.coupons:
                    if coupon[0] == u"＠レベル上限":
                        self.levelmax = max(self.levelmax, coupon[1])
                        break
                break

    def put_params(self, pcard):
        self._calc_params()

        updatebase = (self.recalc_parameter and not self.recalc_parameter_init) or\
                     (self.recalc_coupons and not self.recalc_coupons_init) or\
                     self.race <> pcard.get_race() or\
                     self.sex <> pcard.get_sex() or\
                     self.age <> pcard.get_age() or\
                     self.talent <> pcard.get_talent() or\
                     self.makings <> pcard.get_makings() or\
                     self.type <> self.get_paramtype(pcard)
        updateetc  = self.name <> pcard.name or\
                     self.imgpaths <> self.imgpaths_base or\
                     self.can_loaded_scaledimage <> self.can_loaded_scaledimage_base or\
                     self.level <> pcard.level

        if updatebase:
            racecoupons = set()
            for period in itertools.chain(cw.cwpy.setting.periods, cw.cwpy.setting.races):
                for coupon in period.coupons:
                    if coupon[0] == u"＠ＥＰ":
                        # "＠ＥＰ"は種族を変更しても変化しない
                        continue
                    racecoupons.add(coupon[0])

            syscoupons = set()
            for coupon in cw.cwpy.setting.sexcoupons:
                syscoupons.add(coupon)
            for coupon in cw.cwpy.setting.periodcoupons:
                syscoupons.add(coupon)
            for coupon in cw.cwpy.setting.naturecoupons:
                syscoupons.add(coupon)
            for coupon in cw.cwpy.setting.makingcoupons:
                syscoupons.add(coupon)

            def create_parentmatcher(s):
                index = s.find("%s")
                left = s[:index]
                right = s[index+len("%s"):]
                return left, right

            father_m = create_parentmatcher(cw.cwpy.msgs["father_coupon"])
            mother_m = create_parentmatcher(cw.cwpy.msgs["mother_coupon"])
            etccoupons = [] # システム称号の後にある称号
            parentcoupons = []
            throughted_parents = False
            setlevelmax = False
            for e in pcard.data.getfind("Property/Coupons"):
                name = e.text
                if name in syscoupons or name.startswith(u"＠Ｒ"):
                    if not (self.recalc_parameter and name == u"＠レベル上限"):
                        continue

                value = e.getint(".", "value", 0)

                if self.recalc_parameter and name == u"＠レベル上限":
                    value = self.levelmax
                    setlevelmax = True

                if not throughted_parents:
                    if name.startswith(father_m[0]) and name.endswith(father_m[1]):
                        parentcoupons.append((name, value))
                        continue
                    elif name.startswith(mother_m[0]) and name.endswith(mother_m[1]):
                        parentcoupons.append((name, value))
                        continue
                    elif not name.startswith(u"＠"):
                        throughted_parents = True

                etccoupons.append((name, value))

            if not setlevelmax:
                if self.recalc_parameter:
                    etccoupons.append((u"＠レベル上限", self.levelmax))
                else:
                    etccoupons.append((u"＠レベル上限", pcard.get_levelmax()))

            desc_bef = pcard.get_description()
            desc_bef_d = cw.dialog.create.create_description(pcard.get_talent(), pcard.get_makings())
            # desc_bef: 変更前の解説
            # desc_bef_d: 変更前のデフォルト解説（策士型　都会育ち…）

            makings = self.get_makingslist()
            desc_aft_d = cw.dialog.create.create_description(self.talent, makings)
            # desc_aft_d: 変更後のデフォルト解説

            pcard.set_race(self.race)
            pcard.set_age(self.age)
            pcard.set_sex(self.sex)
            pcard.set_talent(self.talent)
            pcard.set_makings(makings)

            # 解説文の変更は、以下に当てはまる場合だけ。該当箇所のみ書き替える
            # 　変更前の解説文に、デフォ解説が丸ごと、ないし最初の１行残っている
            # 解説文にプレイヤーの自作文章が入っている場合に上書きして消さないための処置
            if desc_bef_d in desc_bef:
                desc_aft = desc_bef.replace(desc_bef_d , desc_aft_d)
                pcard.set_description(desc_aft)
            elif desc_bef_d.split("\n")[0] in desc_bef:
                desc_aft = desc_bef.replace(desc_bef_d.split("\n")[0] , desc_aft_d.split("\n")[0])
                pcard.set_description(desc_aft)

            if self.recalc_parameter:
                pcard.set_physical("agl", self.agl)
                pcard.set_physical("dex", self.dex)
                pcard.set_physical("int", self.int)
                pcard.set_physical("min", self.min)
                pcard.set_physical("str", self.str)
                pcard.set_physical("vit", self.vit)
                pcard.set_mental("aggressive", self.aggressive)
                pcard.set_mental("brave",      self.brave)
                pcard.set_mental("cautious",   self.cautious)
                pcard.set_mental("cheerful",   self.cheerful)
                pcard.set_mental("trickish",   self.trickish)

                # 属性
                pcard.set_feature("automaton", self.race.automaton)
                pcard.set_feature("constructure", self.race.constructure)
                pcard.set_feature("undead", self.race.undead)
                pcard.set_feature("unholy", self.race.unholy)
                pcard.set_noeffect("magic", self.race.noeffect_magic)
                pcard.set_noeffect("weapon", self.race.noeffect_weapon)
                pcard.set_resist("fire", self.race.resist_fire)
                pcard.set_resist("ice", self.race.resist_ice)
                pcard.set_weakness("fire", self.race.weakness_fire)
                pcard.set_weakness("ice", self.race.weakness_ice)
                pcard.set_enhance("avoid", self.race.avoid)
                pcard.set_enhance("resist", self.race.resist)
                pcard.set_enhance("defense", self.race.defense)

            # 父母などの称号→年代などの称号→その他の称号
            # の順で登録する
            seq = []
            seq.extend(parentcoupons)

            seq.append((self.sex, 0))
            seq.append((self.age, 0))
            if not isinstance(self.race, cw.header.UnknownRaceHeader):
                seq.append((u"＠Ｒ" + self.race.name, 0))
            if self.recalc_coupons:
                for coupon in self.race.coupons:
                    seq.append(coupon)

            seq.append((self.talent, 0))
            for making in makings:
                seq.append((making, 0))

            if self.recalc_coupons:
                for f in cw.cwpy.setting.periods:
                    if self.age == u"＿" + f.name:
                        for coupon in f.coupons:
                            seq.append(coupon)
                        break

                for coupon in etccoupons:
                    if not coupon[0] in racecoupons or coupon[0] == u"＠レベル上限":
                        seq.append(coupon)

            else:
                seq.extend(etccoupons)

            coupons = seq

            pcard.replace_allcoupons(coupons, syscoupons=None)

            self.recalc_parameter_init = self.recalc_parameter
            self.recalc_coupons_init = self.recalc_coupons

        if self.name <> pcard.name:
            pcard.set_name(self.name)

        if self.imgpaths <> self.imgpaths_base or self.can_loaded_scaledimage <> self.can_loaded_scaledimage_base:
            pcard.set_images(self.imgpaths)

        if updatebase or self.level <> pcard.level:
            pcard.set_level(self.level, debugedit=True)

        if self.recalc_maxlife:
            maxlife = cw.character.calc_maxlife(pcard.physical["vit"], pcard.physical["min"], pcard.level)
            updatelife = pcard.maxlife <> maxlife
            if updatelife:
                pcard.set_maxlife(maxlife)
        else:
            if self.recalc_parameter:
                # この呼び出しにより係数を初期化する
                pcard.set_maxlife(pcard.maxlife)
            updatelife = False

        return updatebase or updateetc or updatelife

    def create_adventurer(self, setlevel=True):
        makings = self.get_makingslist()

        data = cw.dialog.create.AdventurerData()
        data.set_name(self.name)
        data.set_parents(None, None)
        #遺伝情報、レベル上限、性別、年代、型、特徴、熟練の順で配布
        data.set_gene(self.talent)
        data.set_sex(self.sex)
        data.set_age(self.age)
        data.set_race(self.race)
        data.set_images(self.imgpaths)
        data.set_talent(self.talent)
        data.set_attributes(makings)
        data.set_aging(self.age)
        if setlevel:
            data.set_level(self.level)
        if self.type:
            data.agl = self.race.agl + self.type.aglbonus
            data.dex = self.race.dex + self.type.dexbonus
            data.int = self.race.int + self.type.intbonus
            data.min = self.race.min + self.type.minbonus
            data.str = self.race.str + self.type.strbonus
            data.vit = self.race.vit + self.type.vitbonus
            data.aggressive = self.race.aggressive + self.type.aggressive
            data.brave      = self.race.brave      + self.type.brave
            data.cautious   = self.race.cautious   + self.type.cautious
            data.cheerful   = self.race.cheerful   + self.type.cheerful
            data.trickish   = self.race.trickish   + self.type.trickish
        data.set_desc(self.talent, makings)
        data.set_specialcoupon()
        data.set_life()
        cw.features.wrap_ability(data)
        data.avoid = cw.util.numwrap(data.avoid, -10, 10)
        data.resist = cw.util.numwrap(data.resist, -10, 10)
        data.defense = cw.util.numwrap(data.defense, -10, 10)
        return cw.xmlcreater.create_adventurer(data)

    def get_makingslist(self):
        # 特徴の順序が不定になっているため、定義順にする
        makings = []
        for making in cw.cwpy.setting.makingcoupons:
            if making in self.makings:
                makings.append(making)
        return makings

class CharaRequirementPanel(wx.Panel):

    def __init__(self, parent, infos, create):
        wx.Panel.__init__(self, parent, -1)
        self.infos = infos
        self.create = create
        self.cindex = 0
        self._proc = False

        self._dropfiles = []

        # すでに特殊型のキャラクタがいる場合のみ特殊型を表示する
        self.show_specialtalent = False
        specialtalents = set()
        for f in cw.cwpy.setting.natures:
            if f.special:
                specialtalents.add(u"＿" + f.name)
        for info in infos:
            if info.talent in specialtalents:
                self.show_specialtalent = True
                break

        self.namebox = wx.StaticBox(self, -1, u"名前")
        self.name = wx.TextCtrl(self, size=(cw.ppis(125), -1))
        self.name.SetMaxLength(14)
        self.autoname = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (cw.ppis(50), -1), name=u"自動")

        self.imgbox = wx.StaticBox(self, -1, u"イメージ")
        self.imgbox.DragAcceptFiles(True)
        path = u"Resource/Image/Card/BATTLE"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self.defaultface = cw.ppis(cw.util.load_wxbmp(path, mask=True, can_loaded_scaledimage=True, up_scr=cw.dpi_level))
        self.img = cw.util.CWPyStaticBitmap(self, -1, [self.defaultface], [self.defaultface], size=cw.ppis(cw.SIZE_CARDIMAGE),
                                            ss=cw.ppis)
        self.imgcombo = wx.ComboBox(self, -1, size=(cw.ppis(125), -1), style=wx.CB_READONLY)
        self.imgpathlist = []

        self.lvlbox = wx.StaticBox(self, -1, u"レベル")
        self.levelbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"Lv ―")

        self.typbox = wx.StaticBox(self, -1, u"能力型")
        self.type = wx.StaticText(self, -1, u"―――", size=(cw.ppis(80), -1), style=wx.ALIGN_CENTRE|wx.ST_NO_AUTORESIZE)

        assert 1 <= len(cw.cwpy.setting.races)
        if 1 == len(cw.cwpy.setting.races) and isinstance(cw.cwpy.setting.races[0], cw.header.UnknownRaceHeader):
            self.racebox = None
            self.race = None
        else:
            self.racebox = wx.StaticBox(self, -1, u"種族")
            array = map(lambda race: race.name, cw.cwpy.setting.races)
            self.race = wx.Choice(self, -1, choices=array)

        array = [f.name for f in cw.cwpy.setting.sexes]
        self.sexes = wx.RadioBox(self, -1, u"性別", choices=array,
                                 style=wx.RA_VERTICAL, majorDimension=2)

        array = [f.name for f in cw.cwpy.setting.periods]
        self.periods = wx.RadioBox(self, -1, u"年代", choices=array,
                                   style=wx.RA_VERTICAL, majorDimension=2)

        array = []
        for f in cw.cwpy.setting.natures:
            if not f.special or self.show_specialtalent:
                array.append(f.name)
        self.natures = wx.RadioBox(self, -1, u"素質", choices=array,
                                   style=wx.RA_VERTICAL, majorDimension=len(array)/3)

        self.autobtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), u"自動選択")

        self._bind()
        self._do_layout()

    def _bind(self):
        self.Bind(wx.EVT_TEXT, self.OnName, self.name)
        self.Bind(wx.EVT_BUTTON, self.OnAutoName, self.autoname)
        self.Bind(wx.EVT_BUTTON, self.OnLevelBtn, self.levelbtn)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectImage, self.imgcombo)
        if self.race:
            self.Bind(wx.EVT_CHOICE, self.OnRace, self.race)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectSex, self.sexes)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectAge, self.periods)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectTalent, self.natures)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)
        self.imgbox.Bind(wx.EVT_DROP_FILES, self.OnImgBoxDropFiles)

    def _do_layout(self):
        sizer_name = wx.StaticBoxSizer(self.namebox, wx.HORIZONTAL)
        sizer_name.AddSpacer(cw.ppis((5, 0)))
        sizer_name.Add(self.name, 1, wx.RIGHT|wx.BOTTOM|wx.CENTER, cw.ppis(2))
        sizer_name.Add(self.autoname, 0, wx.RIGHT|wx.BOTTOM|wx.CENTER, cw.ppis(5))

        sizer_image = wx.StaticBoxSizer(self.imgbox, wx.VERTICAL)
        sizer_image.AddStretchSpacer(1)
        sizer_image.Add(self.img, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, cw.ppis(5))
        sizer_image.AddStretchSpacer(1)
        sizer_image.Add(self.imgcombo, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND|wx.ALIGN_CENTER, cw.ppis(5))

        sizer_level = wx.StaticBoxSizer(self.lvlbox, wx.VERTICAL)
        sizer_level.Add(self.levelbtn, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, cw.ppis(5))

        sizer_type = wx.StaticBoxSizer(self.typbox, wx.VERTICAL)
        sizer_type2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_type2.Add(self.type, 1, wx.ALIGN_CENTER, cw.ppis(0))
        sizer_type.Add(sizer_type2, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, cw.ppis(5))

        sizer_lefttop = wx.BoxSizer(wx.VERTICAL)
        sizer_lefttop.Add(sizer_name, 0, wx.EXPAND)
        if self.race:
            sizer_leveltype = wx.BoxSizer(wx.HORIZONTAL)
            sizer_leveltype.Add(sizer_level, 0, wx.EXPAND, border=cw.ppis(5))
            sizer_leveltype.Add(sizer_type, 0, wx.EXPAND|wx.LEFT, border=cw.ppis(5))

            sizer_lefttop.Add(sizer_leveltype, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

            sizer_race = wx.StaticBoxSizer(self.racebox, wx.VERTICAL)
            sizer_race.Add(self.race, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_CENTER, cw.ppis(5))
            sizer_lefttop.Add(sizer_race, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        else:
            sizer_lefttop.Add(sizer_level, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
            sizer_lefttop.Add(sizer_type, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer_bottom = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bottom.Add(self.sexes, 0)
        sizer_bottom.Add(self.periods, 0, wx.LEFT, cw.ppis(5))
        sizer_bottom.Add(self.natures, 0, wx.LEFT, cw.ppis(5))

        sizer_main = wx.GridBagSizer()
        sizer_main.Add(sizer_lefttop, pos=(0, 0), flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=cw.ppis(5))
        sizer_main.Add(sizer_image, pos=(0, 1), flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.EXPAND, border=cw.ppis(5))
        sizer_main.Add(sizer_bottom, pos=(1, 0), span=(1, 2), flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_main, 1, wx.EXPAND|wx.ALL, cw.ppis(5))
        sizer.AddStretchSpacer(0)
        sizer.Add(self.autobtn, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnName(self, event):
        if self._proc:
            return
        self.Parent.Parent.okbtn.Enable(False)
        for info in self._get_infos():
            info.name = self.name.GetValue()
            info.input_name = info.name
        self._update_okbtn()

    def OnAutoName(self, event):
        if self._proc:
            return
        self._proc = True
        name = None
        for info in self._get_infos():
            if info.sex in cw.cwpy.setting.sexcoupons:
                sindex = cw.cwpy.setting.sexcoupons.index(info.sex)
                randomname = cw.dialog.create.get_randomname(cw.cwpy.setting.sexsubnames[sindex])
                if randomname:
                    info.name = randomname
                    info.input_name = u""
            if name is None:
                name = info.name
            if name <> info.name:
                name = u""
        self.name.SetValue(name)
        self._update_okbtn()
        self._proc = False

    def _update_okbtn(self):
        for info in self._get_infos():
            self.Parent.Parent.okbtn.Enable(0 < len(info.name.strip()))

    def OnLevelBtn(self, event):
        infos = self._get_infos()

        level = 1
        for i, info in enumerate(infos):
            force = (i == 0)
            if force:
                level = info.level
            elif level <> info.level:
                level = 1
                break

        dlg = cw.dialog.edit.NumberEditDialog(self.TopLevelParent,
                                              u"レベルの設定", level, 1, 15)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for info in infos:
                info.level = dlg.value
            self.levelbtn.SetLabel("Lv %s" % (dlg.value))

    def OnSelectImage(self, event):
        infos = self._get_infos()

        if self.imgcombo.GetSelection() == 0:
            for info in infos:
                info.imgpaths = info.imgpaths_base
                info.can_loaded_scaledimage = info.can_loaded_scaledimage_base
        else:
            fpath = self.imgpathlist[self.imgcombo.GetSelection()-1]
            for info in infos:
                info.imgpaths = [cw.image.ImageInfo(fpath, postype="Center")]
                info.can_loaded_scaledimage = True

        self._select_image()

    def OnImgBoxDropFiles(self, event):
        files = event.GetFiles()
        seq = []
        for fpath in files:
            ext = os.path.splitext(fpath)[1].lower()
            if ext in cw.EXTS_IMG:
                fpath = cw.util.find_noscalepath(fpath)
                seq.append(fpath)

        if seq:
            self._dropfiles = seq
            img = [cw.image.ImageInfo(seq[0], postype="Center")]
            self._update_images(img)
            infos = self._get_infos()
            for info in infos:
                info.imgpaths = img
                info.can_loaded_scaledimage = True

    def OnRace(self, event):
        for info in self._get_infos():
            info.race = cw.cwpy.setting.races[self.race.GetSelection()]

    def OnSelectSex(self, event):
        for info in self._get_infos():
            info.sex = u"＿" + self.sexes.GetStringSelection()
        self._update_images()

    def OnSelectAge(self, event):
        for info in self._get_infos():
            info.age = u"＿" + self.periods.GetStringSelection()
        self._update_images()

    def OnSelectTalent(self, event):
        for info in self._get_infos():
            info.talent = u"＿" + self.natures.GetStringSelection()
        self._update_images()

    def OnAutoBtn(self, event):
        self.set_random()

    def _update_images(self, img=[][:]):
        self.Freeze()
        fpaths = set()
        if not img:
            if 0 >= self.imgcombo.GetSelection():
                img = []
            else:
                img = [cw.image.ImageInfo(self.imgpathlist[self.imgcombo.GetSelection()-1], postype="Center")]

        infos = self._get_infos()

        # 使用可能なイメージの一覧を取得
        drops = []
        for drop in self._dropfiles:
            key = (u"/drop_files", u"<ドロップされたイメージ> %s" % (os.path.basename(drop)), drop)
            drops.append(key)
        for info in infos:
            for dpaths, paths in cw.util.get_facepaths(info.sex, info.age).iteritems():
                fpaths.update(map(lambda a: (dpaths[0], cw.util.join_paths(dpaths[1], os.path.basename(a)), a), paths))
        flist = list(fpaths)
        cw.util.sort_by_attr(flist)
        flist = drops + flist
        self.imgpathlist = map(lambda a: a[2], flist)
        flist = map(lambda a: a[1], flist)
        flist.insert(0, cw.cwpy.msgs["no_change"])
        self.imgcombo.SetItems(flist)
        cw.util.adjust_dropdownwidth(self.imgcombo)

        if len(img) == 1 and img[0].path in self.imgpathlist:
            # 一覧に選択済みのイメージが含まれていれば復元
            self.imgcombo.SetSelection(self.imgpathlist.index(img[0].path)+1)
        else:
            # 一覧に選択済みのイメージが無ければ[変更しない]を選択
            self.imgcombo.SetSelection(0)
        self._select_image()
        self.Thaw()

    def _select_image(self):
        infos = self._get_infos()

        if self.imgcombo.GetSelection() == 0:
            # [変更しない]
            img = []
            can_loaded_scaledimage = False
            for i, info in enumerate(infos):
                force = (i == 0)
                if force:
                    img = info.imgpaths
                    can_loaded_scaledimage = info.can_loaded_scaledimage
                elif img <> info.imgpaths or can_loaded_scaledimage <> info.can_loaded_scaledimage:
                    img = []
                    can_loaded_scaledimage = False
                    break
            if img:
                # 全員のイメージが一致
                bmps = []
                bmps_bmpdepthkey = []
                for info in img:
                    bmp = cw.util.load_wxbmp(info.path, mask=True, can_loaded_scaledimage=True, up_scr=cw.dpi_level)
                    bmps.append(cw.ppis(bmp))
                    bmps_bmpdepthkey.append(bmp)
                self.img.SetBitmap(bmps, bmps_bmpdepthkey, img)
            else:
                # イメージが一致しないか未設定
                self.img.SetBitmap([self.defaultface], [self.defaultface])
        else:
            # パスを選択
            img = self.imgpathlist[self.imgcombo.GetSelection()-1]
            bmp = cw.util.load_wxbmp(img, mask=True, can_loaded_scaledimage=True, up_scr=cw.dpi_level)
            self.img.SetBitmap([cw.ppis(bmp)], [bmp], infos=[cw.image.ImageInfo(img, postype="Center")])

    def _get_infos(self):
        if self.cindex == 0:
            # 全員
            return self.infos
        else:
            # 誰か一人
            return [self.infos[self.cindex-1]]

    def select_target(self, cindex):
        self._proc = True
        self.cindex = cindex
        name = ""
        level = u"―"
        imgpaths = []
        ctype = None
        sex = ""
        age = ""
        talent = ""
        race = cw.cwpy.setting.unknown_race

        infos = self._get_infos()

        for i, info in enumerate(infos):
            force = (i == 0)
            if force:
                name = info.name
                level = str(info.level)
                imgpaths = info.imgpaths
                ctype = info.type
                sex = info.sex
                age = info.age
                talent = info.talent
                race = info.race
            else:
                if name <> info.name:
                    name = ""
                if level <> str(info.level):
                    level = u"―"
                if imgpaths <> info.imgpaths:
                    imgpaths = []
                if ctype <> info.type:
                    ctype = u"―――"
                if sex <> info.sex:
                    sex = ""
                if age <> info.age:
                    age = ""
                if talent <> info.talent:
                    talent = ""
                if race <> info.race:
                    race = cw.cwpy.setting.unknown_race

        self.name.SetValue(name)
        self.levelbtn.SetLabel("Lv %s" % (level))
        if isinstance(ctype, cw.features.SampleType):
            self.type.SetLabel(ctype.name)
        elif ctype:
            self.type.SetLabel(ctype)
        else:
            self.type.SetLabel(u"カスタム")

        if self.race:
            index = cw.cwpy.setting.races.index(race)
            self.race.SetSelection(index)

        if sex:
            index = self.sexes.FindString(sex[1:])
        else:
            index = -1
        if index <= -1:
            index = 0
        self.sexes.SetSelection(index)

        if age:
            index = self.periods.FindString(age[1:])
        else:
            index = -1
        if index <= -1:
            index = 0
        self.periods.SetSelection(index)

        if talent:
            index = self.natures.FindString(talent[1:])
        else:
            index = -1
        if index <= -1:
            index = 0
        self.natures.SetSelection(index)

        self._update_images(imgpaths)
        self.Layout()
        self._proc = False

    def set_random(self):
        infos = self._get_infos()

        for info in infos:
            arr = cw.cwpy.setting.races
            info.race = arr[cw.cwpy.dice.roll(1, len(arr))-1]
            arr = cw.cwpy.setting.sexcoupons
            info.sex = arr[cw.cwpy.dice.roll(1, len(arr))-1]
            arr = cw.cwpy.setting.periodcoupons
            info.age = arr[cw.cwpy.dice.roll(1, len(arr))-1]
            arr = []
            for nature in cw.cwpy.setting.natures:
                if not nature.special or self.show_specialtalent:
                    arr.append(u"＿" + nature.name)
            info.talent = arr[cw.cwpy.dice.roll(1, len(arr))-1]

            seq = []
            for paths in cw.util.get_facepaths(info.sex, info.age).itervalues():
                seq.extend(paths)

            fpath = cw.cwpy.dice.choice(seq)
            info.imgpaths = [cw.image.ImageInfo(fpath, postype="Center")]
            info.can_loaded_scaledimage = True

            if not info.input_name:
                for sex in cw.cwpy.setting.sexes:
                    if info.sex == u"＿" + sex.name:
                        name = cw.dialog.create.get_randomname(sex.subname)
                        if name:
                            info.name = name
                        break

        self.select_target(self.cindex)
        self._update_okbtn()

class CharaSelectablePanel(wx.Panel):

    def __init__(self, parent, infos, create):
        wx.Panel.__init__(self, parent, -1)
        self.infos = infos
        self.create = create
        self.cindex = 0

        self.mkgbox = wx.StaticBox(self, -1, u"特性")

        self.makings = []
        for f in cw.cwpy.setting.makings:
            check = wx.CheckBox(self, -1, f.name, style=wx.CHK_3STATE)
            self.makings.append(check)

        self.autobtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), u"自動選択")
        self.clearbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), u"クリア")

        self._bind()
        self._do_layout()

    def _bind(self):
        for check in self.makings:
            self.Bind(wx.EVT_CHECKBOX, self.OnCheck, check)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClearBtn, self.clearbtn)

    def _do_layout(self):
        cols = 4
        sizer_checks = wx.GridBagSizer()
        for i, check in enumerate(self.makings):
            row = i / cols
            col = i % cols
            flag = wx.EXPAND
            if 0 < row:
                flag |= wx.TOP
            if 0 < col:
                flag |= wx.LEFT
            sizer_checks.Add(check, pos=(row, col), flag=flag, border=cw.ppis(5))

        sizer_box = wx.StaticBoxSizer(self.mkgbox, wx.HORIZONTAL)
        sizer_box.Add(sizer_checks, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, cw.ppis(5))

        sizer_buttons = wx.GridSizer(1, 2, 5, 5)
        sizer_buttons.Add(self.autobtn)
        sizer_buttons.Add(self.clearbtn)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_box, 1, wx.EXPAND|wx.ALL, cw.ppis(5))
        sizer.AddStretchSpacer(0)
        sizer.Add(sizer_buttons, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnCheck(self, event):
        check = event.GetEventObject()
        value = event.IsChecked()

        infos = self._get_infos()

        making = u"＿" + check.GetLabel()
        for info in infos:
            if making in info.makings and not value:
                info.makings.remove(making)
            elif not making in info.makings and value:
                info.makings.add(making)

        if value:
            index = self.makings.index(check)
            if index % 2 == 1:
                index -= 1
            else:
                index += 1
            if index < len(self.makings):
                check = self.makings[index]
                check.SetValue(False)
                making = u"＿" + check.GetLabel()
                for info in infos:
                    if making in info.makings:
                        info.makings.remove(making)

    def OnAutoBtn(self, event):
        self.set_random()

    def OnClearBtn(self, event):
        for info in self._get_infos():
            info.makings.clear()
        self.select_target(self.cindex)

    def _get_infos(self):
        if self.cindex == 0:
            # 全員
            return self.infos
        else:
            # 誰か一人
            return [self.infos[self.cindex-1]]

    def select_target(self, cindex):
        self.cindex = cindex
        if self.cindex == 0:
            # 全員
            for i, _info in enumerate(self.infos):
                force = (i == 0)
                for check in self.makings:
                    making = u"＿" + check.GetLabel()
                    value = making in self.infos[cindex-1].makings
                    if force:
                        check.SetValue(value)
                    elif check.GetValue() <> value:
                        check.Set3StateValue(wx.CHK_UNDETERMINED)
                        break
        else:
            # 誰か一人
            for check in self.makings:
                making = u"＿" + check.GetLabel()
                check.SetValue(making in self.infos[cindex-1].makings)

    def set_random(self):
        # 特徴をランダムに設定する
        for info in self._get_infos():
            info.makings.clear()
            info.makings.update(cw.dialog.create.get_randommakings())

        self.select_target(self.cindex)

def main():
    pass

if __name__ == "__main__":
    main()
