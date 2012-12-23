#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import cw

#-------------------------------------------------------------------------------
# スキン変換ダイアログ
#-------------------------------------------------------------------------------

class SkinConversionDialog(wx.Dialog):
    def __init__(self, parent, exe):
        wx.Dialog.__init__(self, parent, -1, u"スキンの自動生成")

        self.successful = False

        self.conv = cw.skin.convert.Converter(exe)

        if cw.frame.get_skincount() == 0:
            self.warning = wx.StaticText(self, -1, u"スキンがインストールされていません。\n入手してインストールするか、自動生成を行なってください。")
            font = self.warning.GetFont()
            font = wx.Font(font.GetPointSize(), font.GetFamily(), font.GetStyle(), wx.BOLD)
            self.warning.SetFont(font)
        else:
            self.warning = None

        self.note = wx.Notebook(self)
        self.pane_base = SkinBasePanel(self.note, self.conv)
        #self.pane_feature = SkinFeaturePanel(self.note, self.conv)
        #self.pane_sound = SkinSoundPanel(self.note, self.conv)
        #self.pane_message = SkinMessagePanel(self.note, self.conv)
        #self.pane_card = SkinCardPanel(self.note, self.conv)
        self.note.AddPage(self.pane_base, u"基本")
        #self.note.AddPage(self.pane_feature, u"特性")
        #self.note.AddPage(self.pane_sound, u"サウンド")
        #self.note.AddPage(self.pane_message, u"メッセージ")
        #self.note.AddPage(self.pane_card, u"カード")

        self.btn_ok = wx.Button(self, wx.ID_OK, u"決定")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, u"中止")

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=wx.ID_CANCEL)

    def OnOk(self, event):
        # TODO 特性
        # TODO サウンド
        # TODO メッセージ
        # TODO カード

        self.conv.exe = self.pane_base.exectrl.GetValue()
        self.conv.datadir = self.pane_base.datactrl.GetValue()
        self.conv.scenariodir = self.pane_base.scenarioctrl.GetValue()
        e = self.conv.data.find2("Property/Name")
        e.text = self.pane_base.namectrl.GetValue()
        e = self.conv.data.find2("Property/Type")
        e.text = self.pane_base.typectrl.GetValue()
        e = self.conv.data.find2("Property/Author")
        e.text = self.pane_base.authorctrl.GetValue()
        e = self.conv.data.find2("Property/Description")
        e.text = self.pane_base.descctrl.GetValue()

        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            u"スキンの変換 [%s]" % (self.conv.exe), "", maximum=self.conv.maximum,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        self.conv.start()

        while not self.conv.complete:
            dlg.Update(self.conv.curnum, self.conv.message)
            wx.MilliSleep(1)
        dlg.Destroy()

        if self.conv.scenariodir:
            try:
                if os.path.isabs(self.conv.scenariodir):
                    targ = self.conv.scenariodir
                else:
                    targ = os.path.join(os.path.dirname(self.conv.exe), self.conv.scenariodir)
                link = os.path.basename(self.conv.scenariodir)
                link = cw.util.join_paths(u"Scenario", link + ".lnk")
                link = cw.binary.util.check_duplicate(link)
                cw.util.create_link(link, targ)
            except:
                pass

        if self.conv.failure:
            s = self.conv.errormessage
            wx.MessageBox(s, u"メッセージ", wx.OK | wx.ICON_EXCLAMATION, self)
        else:
            self.successful = True
            self.Close()

    def OnCancel(self, event):
        self.Close()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.btn_ok, 0, 0, 0)
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT, 5)

        if self.warning:
            sizer.Add(self.warning, 0, wx.ALL, 5)
        sizer.Add(self.note, 0, 0, 0)
        sizer.Add(sizer_btn, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# 基本情報
#-------------------------------------------------------------------------------

class SkinBasePanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)
        self.conv = conv

        # スキンタイプ一覧
        self.types = set([
            "MedievalFantasy",
            "Modern",
            "Monsters",
            "Oedo",
            "School",
            "ScienceFiction",
        ])
        if os.path.exists(u"Data/Skin"):
            for name in os.listdir(u"Data/Skin"):
                path = cw.util.join_paths(u"Data/Skin", name)
                skinpath = cw.util.join_paths(u"Data/Skin", name, "Skin.xml")
                if os.path.isdir(path) and os.path.isfile(skinpath):
                    e = cw.data.xml2element(skinpath, "Property")
                    self.types.add(e.gettext("Type", ""))
        self.types = list(self.types)
        self.types.sort(lambda x, y: cmp(x.lower(), y.lower()))

        self.box_base = wx.StaticBox(self, -1, u"本体とフォルダ")

        # 実行ファイルのパス
        self.exelabel = wx.StaticText(self, -1, u"本体")
        self.exectrl = wx.TextCtrl(self)
        self.exectrl.SetValue(conv.exe)
        self.exeref = cw.util.create_fileselection(self,
            target=self.exectrl,
            message=u"スキン生成元となるカードワース本体の選択",
            wildcard=u"カードワース本体 (*.exe)|*.exe|全てのファイル (*.*)|*.*",
            dir=False,
            callback=self._selected_exe)
        # Dataディレクトリの名前
        self.datalabel = wx.StaticText(self, -1, u"データ")
        self.datactrl = wx.TextCtrl(self)
        self.datactrl.SetValue(conv.datadir)
        self.dataref = cw.util.create_fileselection(self,
             target=self.datactrl,
             message=u"スキン生成元のデータフォルダを選択してください。",
             dir=True,
             getbasedir=self._get_basedir)
        # Scenarioディレクトリの名前
        self.scenariolabel = wx.StaticText(self, -1, u"シナリオ")
        self.scenarioctrl = wx.TextCtrl(self)
        self.scenarioctrl.SetValue(conv.scenariodir)
        self.scenarioref = cw.util.create_fileselection(self,
             target=self.scenarioctrl,
             message=u"スキン生成元のシナリオフォルダを選択してください。",
             dir=True,
             getbasedir=self._get_basedir)

        self.box_info = wx.StaticBox(self, -1, u"スキン情報")

        # 種別
        self.typelabel = wx.StaticText(self, -1, u"種別")
        self.typectrl = wx.ComboBox(self, choices=self.types, style=wx.CB_DROPDOWN)
        self.typectrl.SetValue(conv.data.gettext("Property/Type", ""))
        # 名前
        self.namelabel = wx.StaticText(self, -1, u"名前")
        self.namectrl = wx.TextCtrl(self)
        self.namectrl.SetValue(conv.data.gettext("Property/Name", ""))
        # 作者
        self.authorlabel = wx.StaticText(self, -1, u"作者")
        self.authorctrl = wx.TextCtrl(self)
        self.authorctrl.SetValue(conv.data.gettext("Property/Author", ""))
        # 解説
        self.desclabel = wx.StaticText(self, -1, u"解説")
        self.descctrl = wx.TextCtrl(self, size=(300, 100), style=wx.TE_MULTILINE)
        self.descctrl.SetValue(conv.data.gettext("Property/Description", ""))

        self._do_layout()
        self._bind()

    def _bind(self):
        self.exectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.datactrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.typectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.namectrl.Bind(wx.EVT_TEXT, self.OnInput)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_base = wx.StaticBoxSizer(self.box_base, wx.VERTICAL)
        bsizer_info = wx.StaticBoxSizer(self.box_info, wx.VERTICAL)
        gbsizer_base = wx.GridBagSizer()
        gbsizer_info = wx.GridBagSizer()

        gbsizer_base.Add(self.exelabel, pos=(0, 0), flag=wx.ALL, border=3)
        gbsizer_base.Add(self.exectrl, pos=(0, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_base.Add(self.exeref, pos=(0, 2), flag=wx.ALL, border=3)
        gbsizer_base.Add(self.datalabel, pos=(1, 0), flag=wx.ALL, border=3)
        gbsizer_base.Add(self.datactrl, pos=(1, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_base.Add(self.dataref, pos=(1, 2), flag=wx.ALL, border=3)
        gbsizer_base.Add(self.scenariolabel, pos=(2, 0), flag=wx.ALL, border=3)
        gbsizer_base.Add(self.scenarioctrl, pos=(2, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_base.Add(self.scenarioref, pos=(2, 2), flag=wx.ALL, border=3)
        gbsizer_base.AddGrowableCol(1)

        gbsizer_info.Add(self.typelabel, pos=(0, 0), flag=wx.ALL, border=3)
        gbsizer_info.Add(self.typectrl, pos=(0, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_info.Add(self.namelabel, pos=(1, 0), flag=wx.ALL, border=3)
        gbsizer_info.Add(self.namectrl, pos=(1, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_info.Add(self.authorlabel, pos=(2, 0), flag=wx.ALL, border=3)
        gbsizer_info.Add(self.authorctrl, pos=(2, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_info.Add(self.desclabel, pos=(3, 0), flag=wx.ALL, border=3)
        gbsizer_info.Add(self.descctrl, pos=(3, 1), flag=wx.ALL|wx.EXPAND, border=3)
        gbsizer_info.AddGrowableCol(1)
        gbsizer_info.AddGrowableRow(3)

        bsizer_base.Add(gbsizer_base, 0, wx.EXPAND, 5)
        bsizer_info.Add(gbsizer_info, 0, wx.EXPAND, 5)

        sizer_v1.Add(bsizer_base, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_info, 0, wx.EXPAND, 0)
        sizer.Add(sizer_v1, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def _get_basedir(self):
        return os.path.dirname(self.exectrl.GetValue())

    def _selected_exe(self, exe):
        self.conv.init(exe)

        self.datactrl.SetValue(self.conv.datadir)
        self.scenarioctrl.SetValue(self.conv.scenariodir)

        self.typectrl.SetValue(self.conv.data.gettext("Property/Type", ""))
        self.namectrl.SetValue(self.conv.data.gettext("Property/Name", ""))
        self.authorctrl.SetValue(self.conv.data.gettext("Property/Author", ""))
        self.descctrl.SetValue(self.conv.data.gettext("Property/Description", ""))

    def OnInput(self, event):
        exe = self.exectrl.GetValue().strip()
        data = self.datactrl.GetValue().strip()
        type = self.typectrl.GetValue().strip()
        name = self.namectrl.GetValue().strip()

        if exe and data and type and name:
            self.TopLevelParent.btn_ok.Enable()
        else:
            self.TopLevelParent.btn_ok.Disable()

#-------------------------------------------------------------------------------
# TODO 特性情報
#-------------------------------------------------------------------------------

class SkinFeaturePanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

#-------------------------------------------------------------------------------
# TODO サウンド情報
#-------------------------------------------------------------------------------

class SkinSoundPanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

#-------------------------------------------------------------------------------
# TODO メッセージ情報
#-------------------------------------------------------------------------------

class SkinMessagePanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

#-------------------------------------------------------------------------------
# TODO カード情報
#-------------------------------------------------------------------------------

class SkinCardPanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)
