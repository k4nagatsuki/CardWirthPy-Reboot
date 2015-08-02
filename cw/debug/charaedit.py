#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
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
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (20, 20), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL_dbg"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (20, 20), bmp=bmp)
        if self.create:
            self.target.Hide()
            self.leftbtn.Hide()
            self.rightbtn.Hide()

        self.note = wx.Notebook(self)
        self.pane_req = CharaRequirementPanel(self.note, self.infos)
        self.pane_sel = CharaSelectablePanel(self.note, self.infos)
        self.note.AddPage(self.pane_req, u"必須情報")
        self.note.AddPage(self.pane_sel, u"選択情報")

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

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        if not self.create:
            sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
            sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
            sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
            sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
            sizer_left.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=5)
        sizer_left.Add(self.note, 1, flag=wx.EXPAND)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.stdbtn, 0, wx.EXPAND)
        sizer_right.Add(self.autobtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=5)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=5)
        sizer.Add(sizer_right, 0, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

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
                    cw.cwpy.sounds["harvest"].play()
                    cw.animation.animate_sprite(pcard, "hide")
                    pcard.cardimg.set_levelimg(pcard.level)
                    pcard.update_image()
                    cw.animation.animate_sprite(pcard, "deal")
                if not updates:
                    cw.cwpy.sounds["harvest"].play()

            updates = []
            for i, info in enumerate(self.infos):
                if info.put_params(self.pcards[i]):
                    updates.append(i)
            cw.cwpy.exec_func(func, updates, self.pcards)

        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def select_target(self):
        cindex = self.target.GetSelection()
        self.pane_req.select_target(cindex)
        self.pane_sel.select_target(cindex)

class CharaInfo(object):

    def __init__(self, pcard):
        if pcard:
            self.name = pcard.name
            self.race = pcard.get_race()
            self.imgpath = pcard.get_imagepath()
            if self.imgpath:
                self.imgpath = cw.util.join_yadodir(self.imgpath)
            self.imgpath_base = self.imgpath
            self.level = pcard.level
            self.sex = pcard.get_sex()
            self.age = pcard.get_age()
            self.talent = pcard.get_talent()
            self.makings = pcard.get_makings()
            self.type = self.get_paramtype(pcard)
            self.physical = pcard.physical
            self.mental = pcard.mental
        else:
            self.name = ""
            self.race = cw.cwpy.setting.unknown_race
            self.imgpath = ""
            self.imgpath_base = ""
            self.level = 1
            self.sex = cw.cwpy.setting.sexcoupons[0]
            self.age = cw.cwpy.setting.periodcoupons[0]
            self.talent = cw.cwpy.setting.naturecoupons[0]
            self.makings = set()
            self.type = None
            self.physical = {
                "agl":self.race.agl,
                "dex":self.race.dex,
                "int":self.race.int,
                "min":self.race.min,
                "str":self.race.str,
                "vit":self.race.vit
            }
            self.mental = {
                "aggressive":self.race.aggressive,
                "brave":self.race.brave,
                "cautious":self.race.cautious,
                "cheerful":self.race.cheerful,
                "trickish":self.race.trickish
            }

    def set_randomfeatures(self):
        """ランダムに特性を設定する。
        """
        self.race = cw.cwpy.dice.choice(cw.cwpy.setting.races) if cw.cwpy.setting.races else cw.cwpy.setting.unknown_race

        self.sex = cw.cwpy.dice.choice(cw.cwpy.setting.sexcoupons)
        self.age = cw.cwpy.dice.choice(cw.cwpy.setting.periodcoupons)
        faces = []
        for values in cw.util.get_facepaths(self.sex, self.age, rel=True).itervalues():
            faces.extend(values)
        self.imgpath = cw.cwpy.dice.choice(faces) if faces else u""

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

    def put_params(self, pcard):
        updatebase = self.sex <> pcard.get_sex() or\
                     self.age <> pcard.get_age() or\
                     self.talent <> pcard.get_talent() or\
                     self.makings <> pcard.get_makings() or\
                     self.type <> self.get_paramtype(pcard)
        updateetc  = self.name <> pcard.name or\
                     self.imgpath <> self.imgpath_base or\
                     self.level <> pcard.level

        if updatebase:
            desc_bef = pcard.get_description()
            desc_bef_d = cw.dialog.create.create_description(pcard.get_talent(), pcard.get_makings())
            # desc_bef: 変更前の解説
            # desc_bef_d: 変更前のデフォルト解説（策士型　都会育ち…）

            makings = self.get_makingslist()
            desc_aft_d = cw.dialog.create.create_description(self.talent, makings)
            # desc_aft_d: 変更後のデフォルト解説

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

            # 能力値の再計算
            race = pcard.get_race()
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

        if self.name <> pcard.name:
            pcard.set_name(self.name)

        if self.imgpath <> self.imgpath_base:
            pcard.set_image(self.imgpath)

        if updatebase or self.level <> pcard.level:
            pcard.set_level(self.level, debugedit=True)

        return updatebase or updateetc

    def create_adventurer(self, setlevel=True):
        makings = self.get_makingslist()

        data = cw.dialog.create.AdventurerData()
        data.set_name(self.name)
        data.set_age(self.age)
        if setlevel:
            data.set_level(self.level)
        data.set_sex(self.sex)
        data.set_image(self.imgpath)
        data.set_race(self.race)
        data.set_parents(None, None)
        data.set_talent(self.talent)
        data.set_attrbutes(makings)
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

    def __init__(self, parent, infos):
        wx.Panel.__init__(self, parent, -1)
        self.infos = infos
        self.cindex = 0
        self._proc = False

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
        self.name = wx.TextCtrl(self, size=(125, -1))
        self.name.SetMaxLength(14)

        self.imgbox = wx.StaticBox(self, -1, u"イメージ")
        path = u"Resource/Image/Card/BATTLE"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self.defaultface = cw.util.load_wxbmp(path, mask=True)
        self.img = cw.util.CWPyStaticBitmap(self, -1, self.defaultface, size=(74, 94))
        self.imgcombo = wx.ComboBox(self, -1, size=(125, -1), style=wx.CB_READONLY)

        self.lvlbox = wx.StaticBox(self, -1, u"レベル")
        self.levelbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"Lv ―")

        self.typbox = wx.StaticBox(self, -1, u"能力型")
        self.type = wx.StaticText(self, -1, u"―――", size=(125, -1), style=wx.ALIGN_CENTRE|wx.ST_NO_AUTORESIZE)

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
        self.Bind(wx.EVT_BUTTON, self.OnLevelBtn, self.levelbtn)
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectImage, self.imgcombo)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectSex, self.sexes)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectAge, self.periods)
        self.Bind(wx.EVT_RADIOBOX, self.OnSelectTalent, self.natures)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)

    def _do_layout(self):

        sizer_name = wx.StaticBoxSizer(self.namebox, wx.VERTICAL)
        sizer_name.Add(self.name, 0, wx.ALL, 5)

        sizer_image = wx.StaticBoxSizer(self.imgbox, wx.VERTICAL)
        sizer_image.AddStretchSpacer(1)
        sizer_image.Add(self.img, 0, wx.ALL|wx.ALIGN_CENTER, 5)
        sizer_image.AddStretchSpacer(1)
        sizer_image.Add(self.imgcombo, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND|wx.ALIGN_CENTER, 5)

        sizer_level = wx.StaticBoxSizer(self.lvlbox, wx.VERTICAL)
        sizer_level.Add(self.levelbtn, 1, wx.EXPAND|wx.ALL, 5)

        sizer_type = wx.StaticBoxSizer(self.typbox, wx.VERTICAL)
        sizer_type.Add(self.type, 1, wx.EXPAND|wx.ALL|wx.ALIGN_CENTER, 5)

        sizer_lefttop = wx.BoxSizer(wx.VERTICAL)
        sizer_lefttop.Add(sizer_name, 0, wx.EXPAND)
        sizer_lefttop.Add(sizer_level, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_lefttop.Add(sizer_type, 0, wx.EXPAND|wx.TOP, border=5)

        sizer_bottom = wx.BoxSizer()
        sizer_bottom.Add(self.sexes, 0)
        sizer_bottom.Add(self.periods, 0, wx.LEFT, 5)
        sizer_bottom.Add(self.natures, 0, wx.LEFT, 5)

        sizer_main = wx.GridBagSizer()
        sizer_main.Add(sizer_lefttop, pos=(0, 0), flag=wx.ALL|wx.EXPAND, border=5)
        sizer_main.Add(sizer_image, pos=(0, 1), flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.EXPAND, border=5)
        sizer_main.Add(sizer_bottom, pos=(1, 0), span=(1, 2), flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_main, 1, wx.EXPAND|wx.ALL, 5)
        sizer.AddStretchSpacer(0)
        sizer.Add(self.autobtn, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnName(self, event):
        if self._proc:
            return
        self.Parent.Parent.okbtn.Enable(False)
        for info in self._get_infos():
            info.name = self.name.GetValue().strip()
            self.Parent.Parent.okbtn.Enable(0 < len(info.name))

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
                info.imgpath = info.imgpath_base
        else:
            facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
            fpath = self.imgcombo.GetValue()
            if not os.path.isabs(fpath):
                fpath = cw.util.join_paths(facedir, fpath)
            for info in infos:
                info.imgpath = fpath

        self._select_image()

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

    def _update_images(self):
        fpaths = set()
        if 0 >= self.imgcombo.GetSelection():
            img = ""
        else:
            img = self.imgcombo.GetValue()

        infos = self._get_infos()

        # 使用可能なイメージの一覧を取得
        for info in infos:
            for paths in cw.util.get_facepaths(info.sex, info.age, rel=True).itervalues():
                fpaths.update(paths)
        flist = list(fpaths)
        flist.sort()
        flist.insert(0, cw.cwpy.msgs["no_change"])
        self.imgcombo.SetItems(flist)
        cw.util.adjust_dropdownwidth(self.imgcombo)

        if img in fpaths:
            # 一覧に選択済みのイメージが含まれていれば復元
            self.imgcombo.SetValue(img)
        else:
            # 一覧に選択済みのイメージが無ければ[変更しない]を選択
            self.imgcombo.SetSelection(0)
        self._select_image()

    def _select_image(self):
        infos = self._get_infos()

        if self.imgcombo.GetSelection() == 0:
            # [変更しない]
            img = ""
            for i, info in enumerate(infos):
                force = (i == 0)
                if force:
                    img = info.imgpath
                elif img <> info.imgpath:
                    img = ""
                    break
            if img:
                # 全員のイメージが一致
                self.img.SetBitmap(cw.util.load_wxbmp(img, mask=True))
            else:
                # イメージが一致しないか未設定
                self.img.SetBitmap(self.defaultface)
        else:
            # パスを選択
            facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
            img = self.imgcombo.GetValue()
            if not os.path.isabs(img):
                img = cw.util.join_paths(facedir, img)
            self.img.SetBitmap(cw.util.load_wxbmp(img, mask=True))

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
        imgpath = ""
        ctype = None
        sex = ""
        age = ""
        talent = ""

        infos = self._get_infos()

        for i, info in enumerate(infos):
            force = (i == 0)
            if force:
                name = info.name
                level = str(info.level)
                imgpath = info.imgpath
                ctype = info.type
                sex = info.sex
                age = info.age
                talent = info.talent
            else:
                if name <> info.name:
                    name = ""
                if level <> str(info.level):
                    level = u"―"
                if imgpath <> info.imgpath:
                    imgpath = ""
                if ctype <> info.type:
                    ctype = u"―――"
                if sex <> info.sex:
                    sex = ""
                if age <> info.age:
                    age = ""
                if talent <> info.talent:
                    talent = ""

        self.name.SetValue(name)
        self.levelbtn.SetLabel("Lv %s" % (level))
        if imgpath:
            if os.path.abspath(imgpath):
                fpath = imgpath
            else:
                facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
                fpath = cw.util.relpath(imgpath, facedir)
                fpath = cw.util.join_paths(fpath)
            # SetValue()を有効にするため一時的に追加
            # _update_images()で上書きされる
            self.imgcombo.Append(fpath)
            self.imgcombo.SetValue(fpath)
        else:
            self.imgcombo.SetSelection(0)
        if isinstance(ctype, cw.features.SampleType):
            self.type.SetLabel(ctype.name)
        elif ctype:
            self.type.SetLabel(ctype)
        else:
            self.type.SetLabel(u"カスタム")

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

        self._update_images()
        self.Layout()
        self._proc = False

    def set_random(self):
        infos = self._get_infos()

        for info in infos:
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
            for paths in cw.util.get_facepaths(info.sex, info.age, rel=True).itervalues():
                seq.extend(paths)

            info.imgpath = cw.cwpy.dice.choice(seq)

        self.select_target(self.cindex)

class CharaSelectablePanel(wx.Panel):

    def __init__(self, parent, infos):
        wx.Panel.__init__(self, parent, -1)
        self.infos = infos
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
            sizer_checks.Add(check, pos=(row, col), flag=flag, border=5)

        sizer_box = wx.StaticBoxSizer(self.mkgbox, wx.HORIZONTAL)
        sizer_box.Add(sizer_checks, 1, wx.EXPAND|wx.ALL, 5)

        sizer_buttons = wx.GridSizer(1, 2, 5, 5)
        sizer_buttons.Add(self.autobtn)
        sizer_buttons.Add(self.clearbtn)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_box, 1, wx.EXPAND|wx.ALL, 5)
        sizer.AddStretchSpacer(0)
        sizer.Add(sizer_buttons, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, 5)

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
