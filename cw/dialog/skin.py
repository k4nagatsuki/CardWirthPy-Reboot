#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import wx.grid

import cw

#-------------------------------------------------------------------------------
# スキン変換ダイアログ
#-------------------------------------------------------------------------------

class SkinConversionDialog(wx.Dialog):
    def __init__(self, parent, exe):
        wx.Dialog.__init__(self, parent, -1, u"スキンの自動生成",
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

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
        self.pane_feature = SkinFeaturePanel(self.note, self.conv)
        self.pane_sound = SkinSoundPanel(self.note, self.conv)
        self.pane_message = SkinMessagePanel(self.note, self.conv)
        self.pane_card = SkinCardPanel(self.note, self.conv)
        self.note.AddPage(self.pane_base, u"基本")
        self.note.AddPage(self.pane_feature, u"特性")
        self.note.AddPage(self.pane_sound, u"サウンド")
        self.note.AddPage(self.pane_message, u"メッセージ")
        self.note.AddPage(self.pane_card, u"カード")

        self.btn_ok = wx.Button(self, wx.ID_OK, u"決定")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, u"中止")

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=wx.ID_CANCEL)

    def OnOk(self, event):
        self.pane_feature.get_values(self.conv)
        self.pane_sound.get_values(self.conv)
        self.pane_message.get_values(self.conv)
        self.pane_card.get_values(self.conv)

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

                existslink = False
                path1 = os.path.abspath(os.path.normpath(targ))
                for dpath in os.listdir(u"Scenario"):
                    dpath = os.path.join(u"Scenario", dpath)
                    path2 = os.path.abspath(os.path.normpath(cw.util.get_linktarget(dpath)))
                    if path1 == path2:
                        existslink = True
                        break

                if not existslink:
                    link = os.path.basename(self.conv.scenariodir)
                    link = cw.util.join_paths(u"Scenario", link + ".lnk")
                    link = cw.binary.util.check_duplicate(link)
                    cw.util.create_link(link, targ)
            except:
                pass

        if self.conv.failure:
            s = self.conv.errormessage
            wx.MessageBox(s, cw.cwpy.msgs["message"], wx.OK | wx.ICON_EXCLAMATION, self)
        else:
            self.successful = True
            self.Close()

    def OnCancel(self, event):
        self.Close()

    def _do_layout(self):
        sizer = wx.GridBagSizer()
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.btn_ok, 0, 0, 0)
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT, 5)

        row = 0
        if self.warning:
            sizer.Add(self.warning, pos=(row, 0), flag=wx.ALL, border=5)
            row += 1
        sizer.Add(self.note, pos=(row, 0), flag=wx.EXPAND)
        sizer.AddGrowableRow(row)
        sizer.AddGrowableCol(0)
        row += 1
        sizer.Add(sizer_btn, pos=(row, 0), flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        row += 1
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
        self.descctrl = wx.TextCtrl(self, size=(400, 100), style=wx.TE_MULTILINE)
        self.descctrl.SetValue(conv.data.gettext("Property/Description", ""))

        self._do_layout()
        self._bind()

    def _bind(self):
        self.exectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.datactrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.typectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.namectrl.Bind(wx.EVT_TEXT, self.OnInput)

    def _do_layout(self):
        sizer = wx.GridBagSizer()
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
        gbsizer_info.Add(self.descctrl, pos=(3, 1), flag=wx.ALL|wx.GROW, border=3)
        gbsizer_info.AddGrowableCol(1)
        gbsizer_info.AddGrowableRow(3)

        bsizer_base.Add(gbsizer_base, 0, wx.EXPAND, 5)
        bsizer_info.Add(gbsizer_info, 1, wx.EXPAND, 5)

        sizer.Add(bsizer_base, pos=(0, 0), flag=wx.BOTTOM|wx.EXPAND, border=5)
        sizer.Add(bsizer_info, pos=(1, 0), flag=wx.EXPAND, border=0)
        sizer.AddGrowableRow(1)
        sizer.AddGrowableCol(0)
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

        self.Parent.Parent.pane_feature.set_values(self.conv)
        self.Parent.Parent.pane_sound.set_values(self.conv)
        self.Parent.Parent.pane_message.set_values(self.conv)
        self.Parent.Parent.pane_card.set_values(self.conv)

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
# 特性情報
#-------------------------------------------------------------------------------

class SkinFeaturePanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

        base = cw.data.xml2etree(u"Data/SkinBase/Skin.xml")
        basesexes = base.getfind("Sexes")
        baseperiods = base.getfind("Periods")
        basenatures = base.getfind("Natures")
        basemakings = base.getfind("Makings")

        self.grid = wx.grid.Grid(self, -1, size=(200, 200))
        self.grid.CreateGrid(len(basesexes) + len(baseperiods) +\
                             len(basenatures) + len(basemakings), 12)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        nedit = wx.grid.GridCellNumberEditor(-99, 99)
        fedit = wx.grid.GridCellFloatEditor(4, 1)

        self.grid.SetColLabelValue(0, "名称");
        self.grid.SetColLabelValue(1, "器用");
        self.grid.SetColLabelValue(2, "敏捷");
        self.grid.SetColLabelValue(3, "知力");
        self.grid.SetColLabelValue(4, "筋力");
        self.grid.SetColLabelValue(5, "生命");
        self.grid.SetColLabelValue(6, "精神");
        self.grid.SetColLabelValue(7, "好戦");
        self.grid.SetColLabelValue(8, "社交");
        self.grid.SetColLabelValue(9, "勇猛");
        self.grid.SetColLabelValue(10, "慎重");
        self.grid.SetColLabelValue(11, "狡猾");

        self.grid.SetColSize(0, 80)
        for col in range(1, 7):
            self.grid.SetColFormatNumber(col)
            self.grid.SetColSize(col, 40)
            for row in range(0, self.grid.GetNumberRows()):
                self.grid.SetCellEditor(row, col, nedit)
        for col in range(7, 12):
            self.grid.SetColFormatFloat(col, 2, 1)
            self.grid.SetColSize(col, 40)
            for row in range(0, self.grid.GetNumberRows()):
                self.grid.SetCellEditor(row, col, fedit)

        row = 0
        for data in basesexes:
            self.grid.SetRowLabelValue(row, data.gettext("Name", ""))
            row += 1
        for data in baseperiods:
            self.grid.SetRowLabelValue(row, data.gettext("Name", ""))
            row += 1
        for data in basenatures:
            self.grid.SetRowLabelValue(row, data.gettext("Name", ""))
            row += 1
        for data in basemakings:
            self.grid.SetRowLabelValue(row, data.gettext("Name", ""))
            row += 1

        self.set_values(conv)

        self.grid.SetRowLabelSize(wx.grid.GRID_AUTOSIZE)

        self._do_layout()

    def set_values(self, conv):
        def set_rowdata(data, row):
            self.grid.SetCellValue(row, 0, data.gettext("Name", ""))
            e = data.find("Physical")
            self.grid.SetCellValue(row, 1, e.get("dex", "0"))
            self.grid.SetCellValue(row, 2, e.get("agl", "0"))
            self.grid.SetCellValue(row, 3, e.get("int", "0"))
            self.grid.SetCellValue(row, 4, e.get("str", "0"))
            self.grid.SetCellValue(row, 5, e.get("vit", "0"))
            self.grid.SetCellValue(row, 6, e.get("min", "0"))
            e = data.find("Mental")
            self.grid.SetCellValue(row, 7, e.get("aggressive", "0"))
            self.grid.SetCellValue(row, 8, e.get("cheerful", "0"))
            self.grid.SetCellValue(row, 9, e.get("brave", "0"))
            self.grid.SetCellValue(row, 10, e.get("cautious", "0"))
            self.grid.SetCellValue(row, 11, e.get("trickish", "0"))
            return row + 1

        row = 0
        for data in conv.data.getfind("Sexes"):
            row = set_rowdata(data, row)
        for data in conv.data.getfind("Periods"):
            row = set_rowdata(data, row)
        for data in conv.data.getfind("Natures"):
            row = set_rowdata(data, row)
        for data in conv.data.getfind("Makings"):
            row = set_rowdata(data, row)

    def get_values(self, conv):
        row = 0
        def get_rowdata(data, row):
            data.find("Name").text = self.grid.GetCellValue(row, 0)
            e = data.find("Physical")
            e.set("dex", self.grid.GetCellValue(row, 1))
            e.set("agl", self.grid.GetCellValue(row, 2))
            e.set("int", self.grid.GetCellValue(row, 3))
            e.set("str", self.grid.GetCellValue(row, 4))
            e.set("vit", self.grid.GetCellValue(row, 5))
            e.set("min", self.grid.GetCellValue(row, 6))
            e = data.find("Mental")
            e.set("aggressive", self.grid.GetCellValue(row, 7))
            e.set("cheerful", self.grid.GetCellValue(row, 8))
            e.set("brave", self.grid.GetCellValue(row, 9))
            e.set("cautious", self.grid.GetCellValue(row, 10))
            e.set("trickish", self.grid.GetCellValue(row, 11))
            return row + 1
        for data in conv.data.getfind("Sexes"):
            row = get_rowdata(data, row)
        for data in conv.data.getfind("Periods"):
            row = get_rowdata(data, row)
        for data in conv.data.getfind("Natures"):
            row = get_rowdata(data, row)
        for data in conv.data.getfind("Makings"):
            row = get_rowdata(data, row)

    def _do_layout(self):
        sizer = wx.GridSizer(1, 1)
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# サウンド情報
#-------------------------------------------------------------------------------

class SkinSoundPanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

        base = cw.data.xml2etree(u"Data/SkinBase/Skin.xml")
        basesounds = base.find("Sounds")

        self.grid = wx.grid.Grid(self, -1, size=(200, 200))
        self.grid.CreateGrid(len(basesounds), 1)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, "ファイル名(拡張子を除く)");
        self.grid.SetColSize(0, 170)

        for row, e in enumerate(basesounds):
            self.grid.SetRowLabelValue(row, e.text)

        self.set_values(conv)

        self.grid.SetRowLabelSize(wx.grid.GRID_AUTOSIZE)

        self._do_layout()

    def set_values(self, conv):
        for row, e in enumerate(conv.data.find("Sounds")):
            self.grid.SetCellValue(row, 0, e.text)

    def get_values(self, conv):
        for row, e in enumerate(conv.data.find("Sounds")):
            e.text = self.grid.GetCellValue(row, 0)

    def _do_layout(self):
        sizer = wx.GridSizer(1, 1)
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# メッセージ情報
#-------------------------------------------------------------------------------

class SkinMessagePanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)

        base = cw.data.xml2etree(u"Data/SkinBase/Skin.xml")
        basemsgs = base.find("Messages")

        self.grid = wx.grid.Grid(self, -1, size=(200, 200))
        self.grid.CreateGrid(len(basemsgs) + 4, 1)
        self.grid.SetRowLabelSize(150)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, "メッセージ(\\n=改行, \\\\=\\)");
        self.grid.SetColSize(0, 380)

        row = 0
        for e in basemsgs:
            s = cw.util.encodewrap(e.text)
            self.grid.SetRowLabelValue(row, s)
            row += 1

        basegameover = cw.data.xml2etree(u"Data/SkinBase/Resource/Xml/GameOver/01_GameOver.xml")
        e = basegameover.find("Events/Event//Talk")
        self.grid.SetRowLabelValue(row, e.find("Text").text)
        row += 1
        self.grid.SetRowLabelValue(row, e.find("Contents/Post[1]").get("name"))
        row += 1
        self.grid.SetRowLabelValue(row, e.find("Contents/Post[2]").get("name"))
        row += 1
        self.grid.SetRowLabelValue(row, e.find("Contents/Post[4]").get("name"))
        row += 1

        self.set_values(conv)

        self._do_layout()

    def set_values(self, conv):
        row = 0
        for e in conv.data.find("Messages"):
            s = cw.util.encodewrap(e.text)
            self.grid.SetCellValue(row, 0, s)
            row += 1

        data = conv.gameover["01_GameOver"]
        e = data.find("Events/Event//Talk")
        self.grid.SetCellValue(row, 0, e.find("Text").text)
        row += 1
        self.grid.SetCellValue(row, 0, e.find("Contents/Post[1]").get("name"))
        row += 1
        self.grid.SetCellValue(row, 0, e.find("Contents/Post[2]").get("name"))
        row += 1
        self.grid.SetCellValue(row, 0, e.find("Contents/Post[4]").get("name"))
        row += 1

    def get_values(self, conv):
        row = 0
        for e in conv.data.find("Messages"):
            e.text = cw.util.decodewrap(self.grid.GetCellValue(row, 0))
            row += 1

        data = conv.gameover["01_GameOver"]
        e = data.find("Events/Event//Talk")
        e.find("Text").text = self.grid.GetCellValue(row, 0)
        row += 1
        e.find("Contents/Post[1]").set("name", self.grid.GetCellValue(row, 0))
        row += 1
        e.find("Contents/Post[2]").set("name", self.grid.GetCellValue(row, 0))
        row += 1
        e.find("Contents/Post[4]").get("name", self.grid.GetCellValue(row, 0))
        row += 1

    def _do_layout(self):
        sizer = wx.GridSizer(1, 1)
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# カード情報
#-------------------------------------------------------------------------------

class SkinCardPanel(wx.Panel):
    def __init__(self, parent, conv):
        wx.Panel.__init__(self, parent)
        baseconv = cw.skin.convert.Converter("")

        self.grid = wx.grid.Grid(self, -1, size=(200, 200))
        self.grid.CreateGrid(0, 2)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, "名称");
        self.grid.SetColLabelValue(1, "解説(\\n=改行, \\\\=\\)");
        self.grid.SetColSize(0, 80)
        self.grid.SetColSize(1, 300)

        row = 0
        self.grid.InsertRows(row, len(baseconv.actioncard), False)
        keys = baseconv.actioncard.keys()
        keys.sort()
        for key in keys:
            e = baseconv.actioncard[key]
            name = e.gettext("Property/Name", "")
            self.grid.SetRowLabelValue(row, "アクション:" + name)
            row += 1

        def put_areacards(table, row):
            keys = table.keys()
            keys.sort()
            for key in keys:
                data = table[key]
                areaname = data.gettext("Property/Name", "")
                cards = data.getfind("MenuCards")
                self.grid.InsertRows(row, len(cards), False)
                for e in cards:
                    name = e.gettext("Property/Name", "")
                    self.grid.SetRowLabelValue(row, areaname + ": " + name)
                    row += 1
            return row

        row = put_areacards(baseconv.title, row)
        row = put_areacards(baseconv.yado, row)
        row = put_areacards(baseconv.scenario, row)
        row = put_areacards(baseconv.gameover, row)

        self.set_values(conv)

        self.grid.SetRowLabelSize(wx.grid.GRID_AUTOSIZE)

        self._do_layout()

    def set_values(self, conv):
        row = 0
        keys = conv.actioncard.keys()
        keys.sort()
        for key in keys:
            e = conv.actioncard[key]
            name = e.gettext("Property/Name", "")
            desc = e.gettext("Property/Description", "")
            self.grid.SetCellValue(row, 0, name)
            self.grid.SetCellValue(row, 1, desc)
            row += 1

        def put_areacards(table, row):
            keys = table.keys()
            keys.sort()
            for key in keys:
                data = table[key]
                cards = data.getfind("MenuCards")
                for e in cards:
                    name = e.gettext("Property/Name", "")
                    desc = e.gettext("Property/Description", "")
                    self.grid.SetCellValue(row, 0, name)
                    self.grid.SetCellValue(row, 1, desc)
                    row += 1
            return row

        row = put_areacards(conv.title, row)
        row = put_areacards(conv.yado, row)
        row = put_areacards(conv.scenario, row)
        row = put_areacards(conv.gameover, row)

    def get_values(self, conv):
        row = 0
        keys = conv.actioncard.keys()
        keys.sort()
        for key in keys:
            e = conv.actioncard[key]
            name = self.grid.GetCellValue(row, 0)
            desc = self.grid.GetCellValue(row, 1)
            name = e.find("Property/Name").text = name
            desc = e.find("Property/Description").text = desc
            row += 1

        def get_areacards(table, row):
            keys = table.keys()
            keys.sort()
            for key in keys:
                data = table[key]
                cards = data.getfind("MenuCards")
                for e in cards:
                    name = self.grid.GetCellValue(row, 0)
                    desc = self.grid.GetCellValue(row, 1)
                    e.find("Property/Name").text = name
                    e.find("Property/Description").text = desc
                    row += 1
            return row

        row = get_areacards(conv.title, row)
        row = get_areacards(conv.yado, row)
        row = get_areacards(conv.scenario, row)
        row = get_areacards(conv.gameover, row)

    def _do_layout(self):
        sizer = wx.GridSizer(1, 1)
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()
