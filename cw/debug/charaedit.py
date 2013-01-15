#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import cw


#-------------------------------------------------------------------------------
#  キャラクター情報編集ダイアログ
#-------------------------------------------------------------------------------

class CharacterEditDialog(wx.Dialog):

    def __init__(self, parent, selected=-1):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの情報の編集",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.SetDoubleBuffered(True)

        self.pcards = cw.cwpy.get_pcards()
        self.infos = [CharaInfo(pcard) for pcard in self.pcards]

        # 対象者
        self.targets = [u"全員"]
        for pcard in self.pcards:
            self.targets.append(pcard.get_name())
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(max(selected, -1) + 1)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)

        self.note = wx.Notebook(self)
        self.pane_req = CharaRequirementPanel(self.note, self.infos)
        self.pane_sel = CharaSelectablePanel(self.note, self.infos)
        self.note.AddPage(self.pane_req, u"必須情報")
        self.note.AddPage(self.pane_sel, u"選択情報")

        # 標準
        self.stdbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"標準")
        # 自動
        self.autobtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"自動")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        self._select_target()

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnStandardType, self.stdbtn)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
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
            self.target.SetSelection(len(self.pcards))
        else:
            self.target.SetSelection(index - 1)
        self._select_target()

    def OnRightBtn(self, event):
        index = self.target.GetSelection()
        if len(self.pcards) <= index:
            self.target.SetSelection(0)
        else:
            self.target.SetSelection(index + 1)
        self._select_target()

    def OnSelectTarget(self, event):
        self._select_target()

    def OnStandardType(self, event):
        pass # TODO

    def OnAutoBtn(self, event):
        self.pane_req._set_random()
        self.pane_sel._set_random()

    def OnOkBtn(self, event):
        pass # TODO

    def _select_target(self):
        cindex = self.target.GetSelection()
        self.pane_req._select_target(cindex)
        self.pane_sel._select_target(cindex)

class CharaInfo(object):

    def __init__(self, pcard):
        self.name = pcard.name
        self.imgpath = cw.util.join_yadodir(pcard.get_imagepath())
        self.imgpath_base = self.imgpath
        self.level = pcard.level
        self.sex = pcard.get_sex()
        self.age = pcard.get_age()
        self.talent = pcard.get_talent()
        self.makings = pcard.get_makings()
        self.physical = pcard.physical
        self.mental = pcard.mental

class CharaRequirementPanel(wx.Panel):

    def __init__(self, parent, infos):
        wx.Panel.__init__(self, parent, -1)
        self.infos = infos
        self.cindex = 0

        self.namebox = wx.StaticBox(self, -1, u"名前")
        self.name = wx.TextCtrl(self, size=(125, -1))
        self.name.SetMaxLength(14)

        self.imgbox = wx.StaticBox(self, -1, u"イメージ")
        path = u"Resource/Image/Card/BATTLE" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        self.defaultface = cw.util.load_wxbmp(path, mask=True)
        self.img = wx.StaticBitmap(self, -1, self.defaultface, size=(74, 94))
        self.imgcombo = wx.ComboBox(self, -1, size=(125, -1), style=wx.CB_READONLY)

        self.lvlbox = wx.StaticBox(self, -1, u"レベル")
        self.levelbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"Lv ―")

        self.typbox = wx.StaticBox(self, -1, u"能力型")
        self.type = wx.StaticText(self, -1, u"―――", size=(125, -1), style=wx.ALIGN_CENTRE)

        array = [f.name for f in cw.cwpy.setting.sexes]
        self.sexes = wx.RadioBox(self, -1, u"性別", choices=array,
                                 style=wx.RA_VERTICAL, majorDimension=2)

        array = [f.name for f in cw.cwpy.setting.periods]
        self.periods = wx.RadioBox(self, -1, u"年代", choices=array,
                                   style=wx.RA_VERTICAL, majorDimension=2)

        array = []
        for f in cw.cwpy.setting.natures:
            if not f.special:
                array.append(f.name)
        self.natures = wx.RadioBox(self, -1, u"素質", choices=array,
                                   style=wx.RA_VERTICAL, majorDimension=2)

        self.autobtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), u"自動選択")

        self._bind()
        self._do_layout()

    def _get_paramtype(self, info):
        for type in cw.cwpy.setting.sampletypes:
            if type.aglbonus + 6 == info.physical["agl"] and\
               type.dexbonus + 6 == info.physical["dex"] and\
               type.intbonus + 6 == info.physical["int"] and\
               type.minbonus + 6 == info.physical["min"] and\
               type.strbonus + 6 == info.physical["str"] and\
               type.vitbonus + 6 == info.physical["vit"] and\
               type.aggressive == info.mental["aggressive"] and\
               type.brave      == info.mental["brave"] and\
               type.cautious   == info.mental["cautious"] and\
               type.cheerful   == info.mental["cheerful"] and\
               type.trickish   == info.mental["trickish"]:
                return type.name
        return u"カスタム"

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
        sizer_image.Add(self.img, 1, wx.ALL|wx.ALIGN_CENTER, 5)
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
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]
        for info in infos:
            info.name = self.name.GetValue()

    def OnLevelBtn(self, event):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

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
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

        if self.imgcombo.GetSelection() == 0:
            for info in infos:
                info.imgpath = info.imgpath_base
        else:
            facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
            fpath = self.imgcombo.GetValue()
            fpath = cw.util.join_paths(facedir, fpath)
            for info in infos:
                info.imgpath = fpath

        self._select_image()

    def OnSelectSex(self, event):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]
        for info in infos:
            info.sex = u"＿" + self.sexes.GetStringSelection()
        self._update_images()

    def OnSelectAge(self, event):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]
        for info in infos:
            info.age = u"＿" + self.periods.GetStringSelection()
        self._update_images()

    def OnSelectTalent(self, event):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]
        for info in infos:
            info.talent = u"＿" + self.natures.GetStringSelection()
        self._update_images()

    def OnAutoBtn(self, event):
        self._set_random()

    def _update_images(self):
        fpaths = set()
        if 0 >= self.imgcombo.GetSelection():
            img = ""
        else:
            img = self.imgcombo.GetValue()

        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

        # 使用可能なイメージの一覧を取得
        facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
        for info in infos:
            for fpath in cw.util.get_facepaths(info.sex, info.age):
                fpath = os.path.relpath(fpath, facedir)
                fpath = cw.util.join_paths(fpath)
                fpaths.add(fpath)
        flist = list(fpaths)
        flist.sort()
        flist.insert(0, u"[変更しない]")
        self.imgcombo.SetItems(flist)

        if img in fpaths:
            # 一覧に選択済みのイメージが含まれていれば復元
            self.imgcombo.SetValue(img)
        else:
            # 一覧に選択済みのイメージが無ければ[変更しない]を選択
            self.imgcombo.SetSelection(0)
        self._select_image()

    def _select_image(self):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

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
            path = cw.util.join_paths(facedir, img)
            self.img.SetBitmap(cw.util.load_wxbmp(path, mask=True))

        self.Layout()

    def _select_target(self, cindex):
        self.cindex = cindex
        name = ""
        level = u"―"
        imgpath = ""
        type = u"―――"
        sex = ""
        age = ""
        talent = ""

        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[cindex-1]]

        for i, info in enumerate(infos):
            force = (i == 0)
            infotype = self._get_paramtype(info)
            if force:
                name = info.name
                level = str(info.level)
                imgpath = info.imgpath
                type = infotype
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
                if type <> infotype:
                    type = u"―――"
                if sex <> info.sex:
                    sex = ""
                if age <> info.age:
                    age = ""
                if talent <> info.talent:
                    talent = ""

        self.name.SetValue(name)
        self.levelbtn.SetLabel("Lv %s" % (level))
        if imgpath:
            facedir = cw.util.join_paths(cw.cwpy.skindir, u"Face")
            fpath = os.path.relpath(imgpath, facedir)
            fpath = cw.util.join_paths(fpath)
            # SetValue()を有効にするため一時的に追加
            # _update_images()で上書きされる
            self.imgcombo.Append(fpath)
            self.imgcombo.SetValue(fpath)
        else:
            self.imgcombo.SetSelection(0)
        self.type.SetLabel(type)

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

    def _set_random(self):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[cindex-1]]

        for info in infos:
            arr = cw.cwpy.setting.sexcoupons
            info.sex = arr[cw.cwpy.dice.roll(1, len(arr))-1]
            arr = cw.cwpy.setting.periodcoupons
            info.age = arr[cw.cwpy.dice.roll(1, len(arr))-1]
            arr = []
            for nature in cw.cwpy.setting.natures:
                if not nature.special:
                    arr.append(u"＿" + nature.name)
            info.talent = arr[cw.cwpy.dice.roll(1, len(arr))-1]

            arr = cw.util.get_facepaths(info.sex, info.age)
            info.imgpath = arr[cw.cwpy.dice.roll(1, len(arr))-1]

        self._select_target(self.cindex)

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

        self.autobtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), u"自動選択")
        self.clearbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), u"クリア")

        self._bind()
        self._do_layout()

    def _bind(self):
        for check in self.makings:
            self.Bind(wx.EVT_CHECKBOX, self.OnCheck, check)
        self.Bind(wx.EVT_BUTTON, self.OnAutoBtn, self.autobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClearBtn, self.clearbtn)

    def _do_layout(self):
        rows = (len(self.makings) + 3) / 4
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

        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

        making = u"＿" + check.GetLabel()
        for info in infos:
            if making in info.makings and not value:
                info.makings.remove(making)
            elif not making in info.makings and value:
                info.makings.add(making)

    def OnAutoBtn(self, event):
        self._set_random()

    def OnClearBtn(self, event):
        if self.cindex == 0:
            # 全員
            for info in self.infos:
                info.makings.clear()
        else:
            # 誰か一人
            self.infos[self.index-1].makings.clear()
        self._select_target(self.cindex)

    def _select_target(self, cindex):
        self.cindex = cindex
        if self.cindex == 0:
            # 全員
            for i, info in enumerate(self.infos):
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

    def _set_random(self):
        if self.cindex == 0:
            # 全員
            infos = self.infos
        else:
            # 誰か一人
            infos = [self.infos[self.cindex-1]]

        # 特徴をランダムに設定する
        for info in infos:
            info.makings.clear()
            mlen = len(cw.cwpy.setting.makingcoupons)
            for i in range(0, mlen, 2):
                if i + 1 < mlen:
                    pair = cw.cwpy.setting.makingcoupons[i:i+2]
                else:
                    pair = cw.cwpy.setting.makingcoupons[i:i+1]
                n = cw.cwpy.dice.roll(1, len(pair) + 1) - 1
                if n < len(pair):
                    info.makings.add(pair[n])

        self._select_target(self.cindex)
