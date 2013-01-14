#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
        self.pane_req = CharaRequirementPanel(self.note)
        self.pane_sel = CharaSelectablePanel(self.note)
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
        self.Bind(wx.EVT_BUTTON, self.OnAuto, self.autobtn)
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

    def OnAuto(self, event):
        pass # TODO

    def OnOkBtn(self, event):
        pass # TODO

    def _select_target(self):
        pass # TODO

class CharaRequirementPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.namebox = wx.StaticBox(self, -1, u"名前")
        self.name = wx.TextCtrl(self, size=(125, -1))
        self.name.SetMaxLength(14)

        self.imgbox = wx.StaticBox(self, -1, u"イメージ")
        path = "Resource/Image/Card/BATTLE" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        self.defaultface = cw.util.load_wxbmp(path, mask=True)
        self.img = wx.StaticBitmap(self, -1, self.defaultface, size=(74, 94))
        self.imgcombo = wx.ComboBox(self, -1)

        self.lvlbox = wx.StaticBox(self, -1, u"レベル")
        self.level = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"Lv ―")

        self.typbox = wx.StaticBox(self, -1, u"能力型")
        self.type = wx.StaticText(self, -1, u"―――", style=wx.ALIGN_CENTRE)

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

    def _get_paramtype(self, pcard):
        for type in cw.cwpy.setting.sampletypes:
            if type.aglbonus + 6 == pcard.physical["agl"] and\
               type.dexbonus + 6 == pcard.physical["dex"] and\
               type.intbonus + 6 == pcard.physical["int"] and\
               type.minbonus + 6 == pcard.physical["min"] and\
               type.strbonus + 6 == pcard.physical["str"] and\
               type.vitbonus + 6 == pcard.physical["vit"] and\
               type.aggressive == pcard.mental["aggressive"] and\
               type.brave      == pcard.mental["brave"] and\
               type.cautious   == pcard.mental["cautious"] and\
               type.cheerful   == pcard.mental["cheerful"] and\
               type.trickish   == pcard.mental["trickish"]:
                return type.name
        return u"カスタム"

    def _bind(self):
        pass # TODO

    def _do_layout(self):

        sizer_name = wx.StaticBoxSizer(self.namebox, wx.VERTICAL)
        sizer_name.Add(self.name, 0, wx.ALL, 5)

        sizer_image = wx.StaticBoxSizer(self.imgbox, wx.VERTICAL)
        sizer_image.Add(self.img, 1, wx.ALL|wx.ALIGN_CENTER, 5)
        sizer_image.Add(self.imgcombo, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND|wx.ALIGN_CENTER, 5)

        sizer_level = wx.StaticBoxSizer(self.lvlbox, wx.VERTICAL)
        sizer_level.Add(self.level, 1, wx.EXPAND|wx.ALL, 5)

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

class CharaSelectablePanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.mkgbox = wx.StaticBox(self, -1, u"特性")

        self.makings = []
        for f in cw.cwpy.setting.makings:
            check = wx.CheckBox(self, -1, f.name)
            self.makings.append(check)

        self.autobtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), u"自動選択")

        self._bind()
        self._do_layout()

    def _bind(self):
        pass # TODO

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

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_box, 1, wx.EXPAND|wx.ALL, 5)
        sizer.AddStretchSpacer(0)
        sizer.Add(self.autobtn, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()
