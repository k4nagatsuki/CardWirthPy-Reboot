#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import time
import threading
import wx
import wx.grid

import cw

#-------------------------------------------------------------------------------
# スキン変換ダイアログ
#-------------------------------------------------------------------------------

class SkinConversionDialog(wx.Dialog):
    def __init__(self, parent, exe, from_settings=False, get_localsettings=None):
        wx.Dialog.__init__(self, parent, -1, u"スキンの自動生成",
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.cwpy_debug = True

        if get_localsettings:
            self.local = get_localsettings()
            use_copybase = True
        elif cw.cwpy:
            get_localsettings = lambda: cw.cwpy.setting.local
            self.local = cw.cwpy.setting.local
            use_copybase = True
        else:
            self.local = cw.setting.LocalSetting()
            get_localsettings = lambda: self.local
            use_copybase = False

        self.successful = False
        self.select_skin = False
        self.skindirname = ""
        self.from_settings = from_settings

        self.conv = cw.skin.convert.Converter(exe)

        skincount, unknown_ver = cw.frame.get_skincount()
        if skincount == 0:
            if unknown_ver:
                s = u"インストールされているスキンは未知のバージョンです。\n%sをアップデートするか、対応バージョンのスキンをインストールするか、スキンの自動生成を行ってください。" % cw.APP_NAME
            else:
                s = u"スキンがインストールされていません。\nスキンを入手してインストールするか、自動生成を行なってください。"
            self.warning = wx.StaticText(self, -1, s)
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
        self.pane_draw = cw.dialog.settings.DrawingSettingPanel(self.note, for_local=True,
                                                                get_localsettings=get_localsettings,
                                                                use_copybase=use_copybase)
        self.pane_draw.load(None, self.local)
        self.pane_font = cw.dialog.settings.FontSettingPanel(self.note, for_local=True,
                                                             get_localsettings=get_localsettings,
                                                             use_copybase=use_copybase)
        self.pane_font.load(None, self.local)
        self.note.AddPage(self.pane_base, u"基本")
        self.note.AddPage(self.pane_feature, u"特性")
        self.note.AddPage(self.pane_sound, u"サウンド")
        self.note.AddPage(self.pane_message, u"メッセージ")
        self.note.AddPage(self.pane_card, u"カード")
        self.note.AddPage(self.pane_draw, u"描画")
        self.note.AddPage(self.pane_font, u"フォント")

        self.btn_ok = wx.Button(self, wx.ID_OK, u"決定")
        if not exe:
            self.btn_ok.Disable()
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
        self.conv.yadodir = self.pane_base.yadoctrl.GetValue()
        e = self.conv.data.find("Property/Name")
        e.text = self.pane_base.info.namectrl.GetValue()
        e = self.conv.data.find("Property/Type")
        e.text = self.pane_base.info.typectrl.GetValue()
        e = self.conv.data.find("Property/Author")
        e.text = self.pane_base.info.authorctrl.GetValue()
        e = self.conv.data.find("Property/Description")
        e.text = self.pane_base.info.descctrl.GetValue()
        e = self.conv.data.find("Property/CW120VocationLevel")
        e.text = str(self.pane_base.info.vocation120.GetValue())
        e = self.conv.data.find("Property/InitialCash")
        e.text = str(self.pane_base.info.initialcash.GetValue())
        e = self.conv.data.find("Settings")
        if e is None:
            e = cw.data.make_element("Settings", "")
            self.conv.data.append(e)
        else:
            e.clear()
        self.local = cw.setting.LocalSetting()
        self.pane_draw.apply_localsettings(self.local)
        self.pane_font.apply_localsettings(self.local)
        cw.xmlcreater.create_localsettings(e, self.local)

        self.conv.start()

        # プログレスダイアログ表示
        dlg = cw.dialog.progress.SysProgressDialog(self,
            u"スキンの変換 [%s]" % (self.conv.exe), "", maximum=self.conv.maximum)
        x = (dlg.Parent.GetSize()[0] - dlg.GetSize()[0]) / 2
        y = (dlg.Parent.GetSize()[1] - dlg.GetSize()[1]) / 2
        x += dlg.Parent.GetPosition()[0]
        y += dlg.Parent.GetPosition()[1]
        dlg.MoveXY(x, y)

        def progress():
            while not self.conv.complete:
                wx.CallAfter(dlg.Update, self.conv.curnum, self.conv.message)
                time.sleep(0.001)
            wx.CallAfter(dlg.Destroy)
        thread2 = threading.Thread(target=progress)
        thread2.start()
        dlg.ShowModal()

        if self.conv.scenariodir:
            try:
                if os.path.isabs(self.conv.scenariodir):
                    targ = self.conv.scenariodir
                else:
                    targ = os.path.join(os.path.dirname(self.conv.exe), self.conv.scenariodir)

                path1 = os.path.normcase(os.path.abspath(os.path.normpath(targ)))

                ##existslink = False
                ##for dpath in os.listdir(u"Scenario"):
                ##    dpath = os.path.join(u"Scenario", dpath)
                ##    path2 = os.path.normcase(os.path.abspath(os.path.normpath(cw.util.get_linktarget(dpath))))
                ##    if path1 == path2:
                ##        existslink = True
                ##        break
                ##
                ##if not existslink:
                ##    link = os.path.basename(self.conv.scenariodir)
                ##    link = cw.util.join_paths(u"Scenario", link + ".lnk")
                ##    link = cw.binary.util.check_duplicate(link)
                ##    cw.util.create_link(link, targ)

                if cw.cwpy:
                    setting = cw.cwpy.setting
                else:
                    setting = cw.setting.Setting()
                for skintype, _folder in setting.folderoftype:
                    if skintype == self.conv.skintype:
                        break # 登録済み
                else:
                    scpath = cw.util.relpath(path1, ".")
                    if scpath.startswith(".."):
                        scpath = path1

                    for skindir in os.listdir(u"Data/Skin"):
                        if skindir == self.conv.skindirname:
                            continue
                        dpath = cw.util.join_paths(u"Data/Skin", skindir)
                        if not os.path.isdir(dpath):
                            continue
                        fpath = cw.util.join_paths(dpath, "Skin.xml")
                        if not os.path.isfile(fpath):
                            continue
                        stype = cw.header.GetName(fpath, tagname="Type").name
                        if self.conv.skintype == stype:
                            # 同タイプの既存スキンが./Scenarioを参照している
                            break
                    else:
                        setting.folderoftype.append((self.conv.skintype, cw.util.join_paths(scpath)))

                setting.write()

            except:
                cw.util.print_ex()

        if self.conv.yadodir and (1, 2, 0, 0) <= self.conv.version:
            try:
                if os.path.isabs(self.conv.yadodir):
                    targ = self.conv.yadodir
                else:
                    targ = os.path.join(os.path.dirname(self.conv.exe), self.conv.yadodir)

                exists = set()
                if not os.path.isdir(u"Yado"):
                    os.makedirs(u"Yado")
                for fpath in os.listdir(u"Yado"):
                    fpath = cw.util.join_paths(u"Yado", fpath)
                    exists.add(os.path.normcase(os.path.abspath(os.path.normpath(cw.util.get_linktarget(fpath)))))

                if os.path.isdir(targ):
                    for fpath in os.listdir(targ):
                        dpath = cw.util.join_paths(targ, fpath)
                        fpath = cw.util.join_paths(dpath, "Environment.wyd")
                        cwyado = cw.binary.cwyado.CWYado(dpath, u"Yado")
                        if cwyado.is_convertible() and not os.path.normcase(os.path.abspath(os.path.normpath(dpath))) in exists:
                            link = os.path.basename(dpath)
                            link = cw.util.join_paths(u"Yado", link + ".lnk")
                            link = cw.binary.util.check_duplicate(link)
                            cw.util.create_link(link, dpath)

            except:
                cw.util.print_ex()

        if self.conv.failure:
            s = self.conv.errormessage
            wx.MessageBox(s, u"メッセージ", wx.OK|wx.ICON_EXCLAMATION, self)
        elif self.from_settings:
            self.successful = True
            self.select_skin = True
            self.skindirname = self.conv.skindirname
            self.conv.dispose()
            self.Close()
            self.Destroy()
        else:
            self.successful = True
            if 1 < cw.frame.get_skincount()[0]:
                s = u"スキンの自動生成に成功しました。生成したスキンに切り替えますか？"
                if wx.MessageBox(s, u"メッセージ", wx.YES_NO|wx.ICON_QUESTION, self) == wx.YES:
                    self.select_skin = True
                    self.skindirname = self.conv.skindirname
            else:
                self.select_skin = True
                self.skindirname = self.conv.skindirname
            self.conv.dispose()
            self.Close()
            self.Destroy()

    def OnCancel(self, event):
        if self.conv:
            self.conv.dispose()
        self.Close()
        self.Destroy()

    def _do_layout(self):
        sizer = wx.GridBagSizer()
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.btn_ok, 0, 0, cw.ppis(0))
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT, cw.ppis(5))

        row = 0
        if self.warning:
            sizer.Add(self.warning, pos=(row, 0), flag=wx.ALL, border=cw.ppis(5))
            row += 1
        sizer.Add(self.note, pos=(row, 0), flag=wx.EXPAND)
        sizer.AddGrowableRow(row)
        sizer.AddGrowableCol(0)
        row += 1
        sizer.Add(sizer_btn, pos=(row, 0), flag=wx.ALL|wx.ALIGN_RIGHT, border=cw.ppis(5))
        row += 1
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# スキン編集ダイアログ
#-------------------------------------------------------------------------------

class SkinEditDialog(wx.Dialog):
    def __init__(self, parent, skindirname, skinsummary, get_localsettings):
        wx.Dialog.__init__(self, parent, -1, u"スキンの編集",
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.cwpy_debug = True

        self.skindirname = skindirname
        self.skinsummary = skinsummary

        if cw.cwpy.setting.skindirname == self.skindirname:
            self.local = cw.cwpy.setting.skin_local
        else:
            data = cw.data.xml2element(cw.util.join_paths(u"Data/Skin", skindirname, u"Skin.xml"))
            e = data.find("Settings")
            if e is None:
                self.local = get_localsettings()
            else:
                self.local = cw.setting.LocalSetting()
                self.local.load(e)

        self.warning = wx.StaticText(self, -1, u"ここでの編集結果は、設定ダイアログでのOK・キャンセルの選択に関わらず即時に反映されます。")
        font = self.warning.GetFont()
        font = wx.Font(font.GetPointSize(), font.GetFamily(), font.GetStyle(), wx.BOLD)
        self.warning.SetFont(font)

        self.note = wx.Notebook(self)
        self.pane_info = wx.Panel(self.note, -1)
        self.box_info = wx.StaticBox(self.pane_info, -1, u"スキン情報")
        self.info = SkinInfoPanel(self.pane_info)
        skintype, skinname, author, desc, vocation120, initialcash = self.skinsummary
        self.info.typectrl.SetValue(skintype)
        self.info.namectrl.SetValue(skinname)
        self.info.authorctrl.SetValue(author)
        self.info.descctrl.SetValue(desc)
        self.info.vocation120.SetValue(vocation120)
        self.info.initialcash.SetValue(initialcash)

        self.pane_draw = cw.dialog.settings.DrawingSettingPanel(self.note, for_local=True,
                                                                get_localsettings=get_localsettings,
                                                                use_copybase=True)
        self.pane_draw.load(None, self.local)
        self.pane_font = cw.dialog.settings.FontSettingPanel(self.note, for_local=True,
                                                             get_localsettings=get_localsettings,
                                                             use_copybase=True)
        self.pane_font.load(cw.cwpy.setting, self.local)

        self.note.AddPage(self.pane_info, u"基本")
        self.note.AddPage(self.pane_draw, u"描画")
        self.note.AddPage(self.pane_font, u"フォント")

        self.btn_ok = wx.Button(self, wx.ID_OK, u"OK")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, u"キャンセル")

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)

    def OnOk(self, event):
        skintype = self.info.typectrl.GetValue()
        skinname = self.info.namectrl.GetValue()
        author = self.info.authorctrl.GetValue()
        desc = self.info.descctrl.GetValue()
        vocation120 = self.info.vocation120.GetValue()
        initialcash = self.info.initialcash.GetValue()
        self.skinsummary = (skintype, skinname, author, desc, vocation120, initialcash)

        skinpath = cw.util.join_paths(u"Data/Skin", self.skindirname, u"Skin.xml")
        e = cw.data.xml2etree(skinpath)
        e.edit("Property/Type", skintype)
        e.edit("Property/Name", skinname)
        e.edit("Property/Author", author)
        e.edit("Property/Description", desc)
        if e.find("Property/CW120VocationLevel") is None:
            prop = e.find("Property")
            prop.append(cw.data.make_element("CW120VocationLevel", str(vocation120)))
        else:
            e.edit("Property/CW120VocationLevel", str(vocation120))
        if e.find("Property/InitialCash") is None:
            prop = e.find("Property")
            prop.append(cw.data.make_element("InitialCash", str(initialcash)))
        else:
            e.edit("Property/InitialCash", str(initialcash))

        element = e.find("Settings")
        if element is None:
            element = cw.data.make_element("Settings", "")
            e.append(".", element)
        else:
            element.clear()
        self.local = cw.setting.LocalSetting()
        updatemessage, updatecurtain, updatefullscreen = self.pane_draw.apply_localsettings(self.local)
        updatefont = self.pane_font.apply_localsettings(self.local)
        cw.xmlcreater.create_localsettings(element, self.local)

        e.write(skinpath)

        if cw.cwpy.setting.skindirname == self.skindirname:
            def func(local, skinname, vocation120, initialcash):
                cw.cwpy.setting.skin_local = local
                cw.cwpy.setting.skinname = skinname
                cw.cwpy.setting.skintype = skintype
                cw.cwpy.update_titlebar()
                cw.cwpy.update_vocation120(vocation120)
                cw.cwpy.setting.initialcash = initialcash
            cw.cwpy.exec_func(func, self.local, skinname, vocation120, initialcash)

            if updatefont:
                cw.cwpy.exec_func(cw.cwpy.update_skin, self.skindirname, restartop=False)
            else:
                if updatemessage:
                    cw.cwpy.exec_func(cw.cwpy.update_messagestyle)
                if updatecurtain:
                    cw.cwpy.exec_func(cw.cwpy.update_curtainstyle)
                if updatefullscreen:
                    cw.cwpy.exec_func(cw.cwpy.update_fullscreenbackground)

        self.EndModal(wx.ID_OK)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_info = wx.StaticBoxSizer(self.box_info, wx.VERTICAL)
        sizer_info.Add(self.info, 1, wx.EXPAND, cw.ppis(0))

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_info, 1, wx.ALL|wx.EXPAND, cw.ppis(10))
        self.pane_info.SetSizer(sizer_panel)

        sizer_btn.Add(self.btn_ok, 0, 0, cw.ppis(0))
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT, cw.ppis(5))

        sizer.Add(self.warning, 0, wx.ALL, cw.ppis(3))
        sizer.Add(self.note, 1, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, cw.ppis(3))
        sizer.Add(sizer_btn, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, cw.ppis(3))
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
        self.exe = self.conv.exe

        self.box_base = wx.StaticBox(self, -1, u"本体とフォルダ")

        # 実行ファイルのパス
        self.exelabel = wx.StaticText(self, -1, u"本体")
        self.exectrl = wx.TextCtrl(self)
        self.exectrl.SetValue(conv.exe)
        self.exeref = cw.util.create_fileselection(self,
            target=self.exectrl,
            message=u"スキン生成元となるカードワース本体の選択",
            wildcard=u"カードワース本体 (*.exe)|*.exe|全てのファイル (*.*)|*.*",
            seldir=False,
            callback=self._selected_exe)
        # Dataディレクトリの名前
        self.datalabel = wx.StaticText(self, -1, u"データ")
        self.datactrl = wx.TextCtrl(self)
        self.datactrl.SetValue(conv.datadir)
        self.dataref = cw.util.create_fileselection(self,
             target=self.datactrl,
             message=u"スキン生成元のデータフォルダを選択してください。",
             seldir=True,
             getbasedir=self._get_basedir)
        # Scenarioディレクトリの名前
        self.scenariolabel = wx.StaticText(self, -1, u"シナリオ")
        self.scenarioctrl = wx.TextCtrl(self)
        self.scenarioctrl.SetValue(conv.scenariodir)
        self.scenarioref = cw.util.create_fileselection(self,
             target=self.scenarioctrl,
             message=u"スキン生成元のシナリオフォルダを選択してください。",
             seldir=True,
             getbasedir=self._get_basedir)
        # Yadoディレクトリの名前
        self.yadolabel = wx.StaticText(self, -1, u"宿")
        self.yadoctrl = wx.TextCtrl(self)
        self.yadoctrl.SetValue(conv.yadodir)
        self.yadoref = cw.util.create_fileselection(self,
             target=self.yadoctrl,
             message=u"スキン生成元の宿フォルダを選択してください。",
             seldir=True,
             getbasedir=self._get_basedir)

        self.box_info = wx.StaticBox(self, -1, u"スキン情報")
        self.info = SkinInfoPanel(self)
        self.info.typectrl.SetValue(conv.data.gettext("Property/Type", ""))
        self.info.namectrl.SetValue(conv.data.gettext("Property/Name", ""))
        self.info.authorctrl.SetValue(conv.data.gettext("Property/Author", ""))
        self.info.descctrl.SetValue(conv.data.gettext("Property/Description", ""))
        if self.conv and self.conv.version <= (1, 2, 0, 99):
            self.info.vocation120.SetValue(True)
        else:
            self.info.vocation120.SetValue(conv.data.getbool("Property/CW120VocationLevel", False))
        self.info.initialcash.SetValue(conv.initialcash)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.exectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.exectrl.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveExeCtrl)
        self.datactrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.info.typectrl.Bind(wx.EVT_TEXT, self.OnInput)
        self.info.namectrl.Bind(wx.EVT_TEXT, self.OnInput)

    def _do_layout(self):
        sizer_gb = wx.GridBagSizer()
        bsizer_base = wx.StaticBoxSizer(self.box_base, wx.VERTICAL)
        bsizer_info = wx.StaticBoxSizer(self.box_info, wx.VERTICAL)
        gbsizer_base = wx.GridBagSizer()

        def add_base(ctrl, pos):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(ctrl, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            gbsizer_base.Add(sizer, pos=pos, flag=wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))

        add_base(self.exelabel, pos=(0, 0))
        add_base(self.exectrl, pos=(0, 1))
        add_base(self.exeref, pos=(0, 2))
        add_base(self.datalabel, pos=(1, 0))
        add_base(self.datactrl, pos=(1, 1))
        add_base(self.dataref, pos=(1, 2))
        add_base(self.scenariolabel, pos=(2, 0))
        add_base(self.scenarioctrl, pos=(2, 1))
        add_base(self.scenarioref, pos=(2, 2))
        add_base(self.yadolabel, pos=(3, 0))
        add_base(self.yadoctrl, pos=(3, 1))
        add_base(self.yadoref, pos=(3, 2))
        gbsizer_base.AddGrowableCol(1, proportion=1)

        bsizer_base.Add(gbsizer_base, 0, wx.EXPAND, cw.ppis(5))
        bsizer_info.Add(self.info, 1, wx.EXPAND, cw.ppis(5))

        sizer_gb.Add(bsizer_base, pos=(0, 0), flag=wx.BOTTOM|wx.EXPAND, border=cw.ppis(5))
        sizer_gb.Add(bsizer_info, pos=(1, 0), flag=wx.EXPAND, border=cw.ppis(0))
        sizer_gb.AddGrowableRow(1)
        sizer_gb.AddGrowableCol(0)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_gb, 1, wx.ALL|wx.EXPAND, cw.ppis(10))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnLeaveExeCtrl(self, event):
        exe = self.exectrl.GetValue()
        if exe:
            self._selected_exe(exe)

    def _get_basedir(self):
        return os.path.dirname(self.exectrl.GetValue())

    def _selected_exe(self, exe):
        if not os.path.isfile(exe) or exe == self.exe:
            self.exe = exe
            return
        self.exe = exe

        s = u"%sの情報を自動抽出しますか？" % (os.path.basename(exe))
        if wx.YES <> wx.MessageBox(s, u"メッセージ", wx.YES_NO|wx.ICON_QUESTION, self):
            return

        self.conv.init(exe)

        self.datactrl.SetValue(self.conv.datadir)
        self.scenarioctrl.SetValue(self.conv.scenariodir)
        self.yadoctrl.SetValue(self.conv.yadodir)

        self.info.typectrl.SetValue(self.conv.data.gettext("Property/Type", ""))
        self.info.namectrl.SetValue(self.conv.data.gettext("Property/Name", ""))
        self.info.authorctrl.SetValue(self.conv.data.gettext("Property/Author", ""))
        self.info.descctrl.SetValue(self.conv.data.gettext("Property/Description", ""))
        self.info.vocation120.SetValue(self.conv.version <= (1, 2, 0, 99))
        self.info.initialcash.SetValue(self.conv.initialcash)

        self.Parent.Parent.pane_feature.set_values(self.conv)
        self.Parent.Parent.pane_sound.set_values(self.conv)
        self.Parent.Parent.pane_message.set_values(self.conv)
        self.Parent.Parent.pane_card.set_values(self.conv)

    def OnInput(self, event):
        exe = self.exectrl.GetValue().strip()
        data = self.datactrl.GetValue().strip()
        skintype = self.info.typectrl.GetValue().strip()
        name = self.info.namectrl.GetValue().strip()

        if exe and data and skintype and name:
            self.TopLevelParent.btn_ok.Enable()
        else:
            self.TopLevelParent.btn_ok.Disable()


#-------------------------------------------------------------------------------
# 基本情報(抽出以外)
#-------------------------------------------------------------------------------

class SkinInfoPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

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
        cw.util.sort_by_attr(self.types)

        # 種別
        self.typelabel = wx.StaticText(self, -1, u"種別")
        self.typectrl = wx.ComboBox(self, choices=self.types, style=wx.CB_DROPDOWN)
        # 名前
        self.namelabel = wx.StaticText(self, -1, u"名前")
        self.namectrl = wx.TextCtrl(self)
        # 作者
        self.authorlabel = wx.StaticText(self, -1, u"作者")
        self.authorctrl = wx.TextCtrl(self)
        # 解説
        self.desclabel = wx.StaticText(self, -1, u"解説")
        self.descctrl = wx.TextCtrl(self, size=cw.ppis((400, 100)), style=wx.TE_MULTILINE)
        # 初期資金
        self.initialcashlabel = wx.StaticText(self, -1, u"初期資金")
        self.initialcash = wx.SpinCtrl(self, -1, max=999999, min=0)
        # カードの適性計算をCardWirth 1.20に合わせるか
        self.vocation120 = wx.CheckBox(self, -1, u"CardWirth 1.20相当のカード適性計算を行う")

        self._do_layout()
        self._bind()

    def _bind(self):
        pass

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        gbsizer_info = wx.GridBagSizer()

        def add_info(ctrl, pos, colspan=1, rowspan=1, expand=True, growable=False):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            growable = wx.EXPAND if growable else 0
            sizer.Add(ctrl, 1, wx.ALIGN_CENTER_VERTICAL|growable, cw.ppis(0))
            span = wx.GBSpan(colspan=colspan, rowspan=rowspan)
            expand = wx.EXPAND if expand else 0
            gbsizer_info.Add(sizer, pos=pos, span=span, flag=wx.ALL|expand|wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))

        add_info(self.typelabel, pos=(0, 0))
        add_info(self.typectrl, pos=(0, 1), colspan=2)
        add_info(self.namelabel, pos=(1, 0))
        add_info(self.namectrl, pos=(1, 1), colspan=2)
        add_info(self.authorlabel, pos=(2, 0))
        add_info(self.authorctrl, pos=(2, 1), colspan=2)
        add_info(self.desclabel, pos=(3, 0))
        add_info(self.descctrl, pos=(3, 1), colspan=2, growable=True)
        add_info(self.initialcashlabel, pos=(4, 0))
        add_info(self.initialcash, pos=(4, 1), expand=False)
        gbsizer_info.AddGrowableCol(1)
        gbsizer_info.AddGrowableRow(3)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.vocation120, 0, wx.TOP, cw.ppis(3))
        add_info(vsizer, pos=(4, 2), colspan=1, rowspan=2, expand=False)

        sizer.Add(gbsizer_info, 1, wx.EXPAND, cw.ppis(0))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

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

        self.grid = wx.grid.Grid(self, -1, size=cw.ppis((200, 200)), style=wx.BORDER)
        self.grid.CreateGrid(len(basesexes) + len(baseperiods) +\
                             len(basenatures) + len(basemakings), 12)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, u"名称")
        self.grid.SetColLabelValue(1, u"器用")
        self.grid.SetColLabelValue(2, u"敏捷")
        self.grid.SetColLabelValue(3, u"知力")
        self.grid.SetColLabelValue(4, u"筋力")
        self.grid.SetColLabelValue(5, u"生命")
        self.grid.SetColLabelValue(6, u"精神")
        self.grid.SetColLabelValue(7, u"好戦")
        self.grid.SetColLabelValue(8, u"社交")
        self.grid.SetColLabelValue(9, u"勇猛")
        self.grid.SetColLabelValue(10, u"慎重")
        self.grid.SetColLabelValue(11, u"狡猾")

        self.grid.SetColSize(0, cw.ppis(80))
        for col in xrange(1, 7):
            self.grid.SetColFormatNumber(col)
            self.grid.SetColSize(col, cw.ppis(40))
            for row in xrange(0, self.grid.GetNumberRows()):
                self.grid.SetCellEditor(row, col, wx.grid.GridCellNumberEditor(-99, 99))
        for col in xrange(7, 12):
            self.grid.SetColFormatFloat(col, 2, 1)
            self.grid.SetColSize(col, cw.ppis(40))
            for row in xrange(0, self.grid.GetNumberRows()):
                self.grid.SetCellEditor(row, col, wx.grid.GridCellFloatEditor(4, 1))

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
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, cw.ppis(5))
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

        self.grid = wx.grid.Grid(self, -1, size=cw.ppis((200, 200)), style=wx.BORDER)
        self.grid.CreateGrid(len(basesounds), 1)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, u"ファイル名(拡張子を除く)")
        self.grid.SetColSize(0, cw.ppis(170))

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
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, cw.ppis(5))
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

        self.grid = wx.grid.Grid(self, -1, size=cw.ppis((200, 200)), style=wx.BORDER)
        self.grid.CreateGrid(len(basemsgs) + 6 + 2 + 4, 1)
        self.grid.SetRowLabelSize(cw.ppis(150))
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, u"メッセージ(\\n=改行, \\\\=\\)")
        self.grid.SetColSize(0, cw.ppis(380))

        row = 0
        for e in basemsgs:
            if e.text:
                s = cw.util.encodewrap(e.text)
            else:
                s = u"(空のテキスト)"
            self.grid.SetRowLabelValue(row, s)
            row += 1

        for e in base.getfind("Natures")[:6]:
            e = e.find("Description")
            s = cw.util.encodewrap(e.text)
            self.grid.SetRowLabelValue(row, s)
            row += 1

        e = base.find("Periods/Period[3]/Coupons/Coupon")
        self.grid.SetRowLabelValue(row, cw.util.encodewrap(e.text))
        row += 1
        e = base.find("Periods/Period[4]/Coupons/Coupon")
        self.grid.SetRowLabelValue(row, cw.util.encodewrap(e.text))
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

        for e in conv.data.getfind("Natures")[:6]:
            e = e.find("Description")
            s = cw.util.encodewrap(e.text)
            self.grid.SetCellValue(row, 0, s)
            row += 1

        e = conv.data.find("Periods/Period[3]/Coupons/Coupon")
        self.grid.SetCellValue(row, 0, cw.util.encodewrap(e.text))
        row += 1
        e = conv.data.find("Periods/Period[4]/Coupons/Coupon")
        self.grid.SetCellValue(row, 0, cw.util.encodewrap(e.text))
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

        for e in conv.data.getfind("Natures")[:6]:
            e = e.find("Description")
            e.text = cw.util.decodewrap(self.grid.GetCellValue(row, 0))
            row += 1

        e = conv.data.find("Periods/Period[3]/Coupons/Coupon")
        e.text = self.grid.GetCellValue(row, 0)
        row += 1
        e = conv.data.find("Periods/Period[4]/Coupons/Coupon")
        e.text = self.grid.GetCellValue(row, 0)
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
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, cw.ppis(5))
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

        self.grid = wx.grid.Grid(self, -1, size=cw.ppis((200, 200)))
        self.grid.CreateGrid(0, 2)
        self.grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)

        self.grid.SetColLabelValue(0, u"名称")
        self.grid.SetColLabelValue(1, u"解説(\\n=改行, \\\\=\\)")
        self.grid.SetColSize(0, cw.ppis(80))
        self.grid.SetColSize(1, cw.ppis(300))

        row = 0
        self.grid.InsertRows(row, len(baseconv.actioncard), False)
        for key in cw.util.sorted_by_attr(baseconv.actioncard.iterkeys()):
            e = baseconv.actioncard[key]
            name = e.gettext("Property/Name", "")
            self.grid.SetRowLabelValue(row, u"アクション:" + name)
            row += 1
        self.grid.InsertRows(row, len(baseconv.specialcard), False)
        for key in cw.util.sorted_by_attr(baseconv.specialcard.iterkeys()):
            e = baseconv.specialcard[key]
            name = e.gettext("Property/Name", "")
            self.grid.SetRowLabelValue(row, u"特殊カード:" + name)
            row += 1

        def put_areacards(table, row):
            for key in cw.util.sorted_by_attr(table.iterkeys()):
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

        baseconv.dispose()

    def set_values(self, conv):
        row = 0
        for key in cw.util.sorted_by_attr(conv.actioncard.iterkeys()):
            e = conv.actioncard[key]
            name = e.gettext("Property/Name", "")
            desc = e.gettext("Property/Description", "")
            self.grid.SetCellValue(row, 0, name)
            self.grid.SetCellValue(row, 1, desc)
            row += 1
        for key in cw.util.sorted_by_attr(conv.specialcard.iterkeys()):
            e = conv.specialcard[key]
            name = e.gettext("Property/Name", "")
            desc = e.gettext("Property/Description", "")
            self.grid.SetCellValue(row, 0, name)
            self.grid.SetCellValue(row, 1, desc)
            row += 1

        def put_areacards(table, row):
            for key in cw.util.sorted_by_attr(table.iterkeys()):
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
        for key in cw.util.sorted_by_attr(conv.actioncard.iterkeys()):
            e = conv.actioncard[key]
            name = self.grid.GetCellValue(row, 0)
            desc = self.grid.GetCellValue(row, 1)
            name = e.find("Property/Name").text = name
            desc = e.find("Property/Description").text = desc
            row += 1
        for key in cw.util.sorted_by_attr(conv.specialcard.iterkeys()):
            e = conv.specialcard[key]
            name = self.grid.GetCellValue(row, 0)
            desc = self.grid.GetCellValue(row, 1)
            name = e.find("Property/Name").text = name
            desc = e.find("Property/Description").text = desc
            row += 1

        def get_areacards(table, row):
            for key in cw.util.sorted_by_attr(table.iterkeys()):
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
        sizer.Add(self.grid, 0, wx.EXPAND|wx.ALL, cw.ppis(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()
