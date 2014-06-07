#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import itertools
import wx
import wx.aui

import cw


SETTINGS_WIDTH = 250

class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"設定")
        self.note = wx.Notebook(self)
        self.pane_gene = GeneralSettingPanel(self.note)
        self.pane_draw = DrawingSettingPanel(self.note)
        self.pane_sound = AudioSettingPanel(self.note)
        self.pane_scenario = ScenarioSettingPanel(self.note)
        self.pane_ui = UISettingPanel(self.note)
        self.note.AddPage(self.pane_gene, u"一般")
        self.note.AddPage(self.pane_draw, u"描画")
        self.note.AddPage(self.pane_sound, u"音声")
        self.note.AddPage(self.pane_scenario, u"シナリオ")
        self.note.AddPage(self.pane_ui, u"操作")
        self.btn_ok = wx.Button(self, wx.ID_OK, u"OK")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, u"キャンセル")
        self.btn_dflt = wx.Button(self, wx.ID_DEFAULT, u"デフォルト")
        self.note.SetSelection(cw.cwpy.settingtab)
        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self.OnDefault, id=wx.ID_DEFAULT)

    def OnDefault(self, event):
        selpane = self.note.GetSelection()
        if selpane == 0:
            self.pane_gene.cb_nolevelup.SetValue(False)
            self.pane_gene.cb_storeskinoneachbase.SetValue(True)
            self.pane_gene.cb_fullscreen.SetValue(True)
            self.pane_gene.makeExpandInfo()
            self.pane_gene.cb_smoothexpand.SetValue(True)
        elif selpane == 1:
            self.pane_draw.cb_smooth_bg.SetValue(False)
            self.pane_draw.sl_deal.SetValue(6)
            self.pane_draw.sl_msgs.SetValue(4)
            self.pane_draw.ch_tran.SetSelection(0)
            self.pane_draw.sl_tran.SetValue(5)
            self.pane_draw.sc_mwin.SetValue(180)
            self.pane_draw.cs_mwin.SetColour((0, 0, 80))
            self.pane_draw.sc_mframe.SetValue(255)
            self.pane_draw.cs_mframe.SetColour((128, 0, 0))
            self.pane_draw.cs_blwin.SetColour((80, 80, 80))
            self.pane_draw.cs_blframe.SetColour((128, 128, 128))
        elif selpane == 2:
            self.pane_sound.cb_playbgm.SetValue(True)
            self.pane_sound.cb_playsound.SetValue(True)
            self.pane_sound.sl_sound.SetValue(100)
            self.pane_sound.sl_midi.SetValue(80)
            self.pane_sound.sl_music.SetValue(100)
            self.pane_sound.list_soundfont.Clear()
            self.pane_sound.list_soundfont.Append(cw.DEFAULT_SOUNDFONT)
        elif selpane == 3:
            # スキン毎のシナリオ開始位置の設定は変更しない
            self.pane_scenario.cb_selectscenariofromtype.SetValue(True)
            self.pane_scenario.cb_showunfitnessscenario.SetValue(True)
            self.pane_scenario.cb_showcompletedscenario.SetValue(True)
            self.pane_scenario.cb_showinvisiblescenario.SetValue(False)
        elif selpane == 4:
            self.pane_ui.cb_quickdeal.SetValue(True)
            self.pane_ui.cb_allquickdeal.SetValue(False)
            self.pane_ui.cb_showallselectedcards.SetValue(True)
            self.pane_ui.cb_showstatustime.SetValue(True)

            self.pane_ui.cb_cautionbeforesaving.SetValue(True)
            self.pane_ui.cb_showbackpackcard.SetValue(True)
            self.pane_ui.cb_revertcardpocket.SetValue(True)
            self.pane_ui.cb_showlogwithwheelup.SetValue(True)
            self.pane_ui.cb_confirmbeforeusingcard.SetValue(True)
            self.pane_ui.cb_showsavedmessage.SetValue(True)
            self.pane_ui.cb_confirmbeforesaving.SetValue(True)

    def OnOk(self, event):
        # 設定変更前はレベル上昇が可能な状態だったか
        can_levelup = not (cw.cwpy.is_debugmode() and cw.cwpy.setting.no_levelup_in_debugmode)
        updatecardimg = False # カードイメージの更新が必要か

        # 一般
        value = self.pane_gene.cb_debug.GetValue()
        if not value == cw.cwpy.setting.debug:
            cw.cwpy.exec_func(cw.cwpy.set_debug, value)

        value = self.pane_gene.cb_nolevelup.GetValue()
        cw.cwpy.setting.no_levelup_in_debugmode = value
        value = self.pane_gene.cb_storeskinoneachbase.GetValue()
        cw.cwpy.setting.store_skinoneachbase = value

        # 拡大倍率
        value = self.pane_gene.cb_smoothexpand.GetValue()
        cw.cwpy.setting.smoothexpand = value
        if self.pane_gene.cb_fullscreen.IsChecked():
            value = "FullScreen"
        elif self.pane_gene.sl_expand.GetValue() == 10: # 1倍 == 拡大なし
            value = "None"
        elif self.pane_gene.sl_expand.GetValue() % 10 == 0: # 整数倍
            value = self.pane_gene.sl_expand.GetValue() / 10
        else:
            value = float(self.pane_gene.sl_expand.GetValue()) / 10
        expanddrawing = int(2 ** self.pane_gene.ch_expanddrawing.GetSelection())
        if str(value) <> str(cw.cwpy.setting.expandmode) or expanddrawing <> cw.cwpy.setting.expanddrawing:
            if cw.cwpy.is_expanded():
                # 一旦拡大状態を解除
                def func(value):
                    cw.cwpy.setting.expandmode = value
                    cw.cwpy.setting.expanddrawing = expanddrawing
                    cw.cwpy.set_expanded(False)
                cw.cwpy.exec_func(func, value)
            else:
                cw.cwpy.setting.expandmode = value
                cw.cwpy.setting.expanddrawing = expanddrawing

        # 描画
        value = self.pane_draw.cb_smooth_bg.GetValue()
        cw.cwpy.setting.smoothscale_bg = value
        value = self.pane_draw.sl_deal.GetValue()
        cw.cwpy.setting.set_dealspeed(value)
        value = self.pane_draw.sl_msgs.GetValue()
        cw.cwpy.setting.messagespeed = value
        value = self.pane_draw.ch_tran.GetSelection()
        value = self.pane_draw.transitions[value]
        cw.cwpy.setting.transition = value
        value = self.pane_draw.sl_tran.GetValue()
        cw.cwpy.setting.transitionspeed = value
        # オーディオ
        value = self.pane_sound.cb_playbgm.GetValue()
        cw.cwpy.setting.play_bgm = value
        value = self.pane_sound.cb_playsound.GetValue()
        cw.cwpy.setting.play_sound = value
        value = self.pane_sound.sl_sound.GetValue()
        value = cw.cwpy.setting.wrap_volumevalue(value)
        cw.cwpy.setting.vol_sound = value
        value = self.pane_sound.sl_midi.GetValue()
        value = cw.cwpy.setting.wrap_volumevalue(value)
        cw.cwpy.setting.vol_midi = value
        value = self.pane_sound.sl_music.GetValue()
        value = cw.cwpy.setting.wrap_volumevalue(value)
        cw.cwpy.setting.vol_bgm = value
        cw.cwpy.music.set_volume()
        soundfonts = []
        for soundfont in self.pane_sound.list_soundfont.GetItems():
            soundfonts.append(soundfont)
        if cw.cwpy.setting.soundfonts <> soundfonts:
            cw.cwpy.setting.soundfonts = soundfonts
            if cw.bassplayer.is_alivable():
                cw.bassplayer.dispose_bass()
            if soundfonts:
                cw.bassplayer.init_bass(soundfonts)
            cw.cwpy.exec_func(cw.cwpy.music.play, cw.cwpy.music.path, updatepredata=False, restart=True)
        # 配色(メッセージ)
        alpha = self.pane_draw.sc_mwin.GetValue()
        colour = self.pane_draw.cs_mwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.mwincolour = colour
        alpha = self.pane_draw.sc_mframe.GetValue()
        colour = self.pane_draw.cs_mframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.mwinframecolour = colour
        # 配色(バックログ)
        alpha = self.pane_draw.sc_mwin.GetValue()
        colour = self.pane_draw.cs_blwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.blwincolour = colour
        alpha = self.pane_draw.sc_mframe.GetValue()
        colour = self.pane_draw.cs_blframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.blwinframecolour = colour
        # スキン
        skin = self.pane_gene.ch_skin.GetSelection()
        skin = self.pane_gene.skins[skin]
        if cw.cwpy.setting.skindirname <> skin:
            cw.cwpy.exec_func(cw.cwpy.update_skin, skin)

        # レベル調節
        def check_levelup(can_levelup_old):
            if cw.cwpy.is_playingscenario():
                return

            can_levelup = not (cw.cwpy.is_debugmode() and cw.cwpy.setting.no_levelup_in_debugmode)
            if not can_levelup_old and can_levelup:
                # レベルアップが可能な設定になったので
                # レベル上昇処理を行う
                for pcard in cw.cwpy.get_pcards():
                    if 0 < pcard.check_level():
                        pcard.adjust_level(False)
        cw.cwpy.exec_func(check_levelup, can_levelup)

        # シナリオ
        value = self.pane_scenario.cb_selectscenariofromtype.GetValue()
        cw.cwpy.setting.selectscenariofromtype = value
        value = self.pane_scenario.cb_showunfitnessscenario.GetValue()
        cw.cwpy.setting.show_unfitnessscenario = value
        value = self.pane_scenario.cb_showcompletedscenario.GetValue()
        cw.cwpy.setting.show_completedscenario = value
        value = self.pane_scenario.cb_showinvisiblescenario.GetValue()
        cw.cwpy.setting.show_invisiblescenario = value

        cw.cwpy.setting.folderoftype = []
        for row in xrange(self.pane_scenario.grid_folderoftype.GetNumberRows() - 1):
            skintype = self.pane_scenario.grid_folderoftype.GetCellValue(row, 0)
            folder = self.pane_scenario.grid_folderoftype.GetCellValue(row, 1)
            cw.cwpy.setting.folderoftype.append((skintype, folder))

        # 操作
        value = self.pane_ui.cb_quickdeal.GetValue()
        cw.cwpy.setting.quickdeal = value
        value = self.pane_ui.cb_allquickdeal.GetValue()
        cw.cwpy.setting.all_quickdeal = value
        value = self.pane_ui.cb_showallselectedcards.GetValue()
        cw.cwpy.setting.show_allselectedcards = value
        value = self.pane_ui.cb_showstatustime.GetValue()
        if cw.cwpy.setting.show_statustime <> value:
            cw.cwpy.setting.show_statustime = value
            updatecardimg = True

        value = self.pane_ui.cb_showlogwithwheelup.GetValue()
        if value:
            cw.cwpy.setting.wheelup_operation = cw.setting.WHEEL_SHOWLOG
        else:
            cw.cwpy.setting.wheelup_operation = cw.setting.WHEEL_SELECTION

        value = self.pane_ui.cb_cautionbeforesaving.GetValue()
        cw.cwpy.setting.caution_beforesaving = value
        value = self.pane_ui.cb_showbackpackcard.GetValue()
        cw.cwpy.setting.show_backpackcard = value
        value = self.pane_ui.cb_revertcardpocket.GetValue()
        cw.cwpy.setting.revert_cardpocket = value
        value = self.pane_ui.cb_confirmbeforesaving.GetValue()
        cw.cwpy.setting.confirm_beforesaving = value
        value = self.pane_ui.cb_showsavedmessage.GetValue()
        cw.cwpy.setting.show_savedmessage = value
        value = self.pane_ui.cb_confirmbeforeusingcard.GetValue()
        cw.cwpy.setting.confirm_beforeusingcard = value

        # イメージの更新
        if updatecardimg:
            def func():
                for ccard in itertools.chain(cw.cwpy.get_pcards("unreversed"),\
                                             cw.cwpy.get_ecards("unreversed"),\
                                             cw.cwpy.get_fcards("unreversed")):
                    ccard.update_image()
            cw.cwpy.exec_func(func)

        self.Close()

    def OnClose(self, event):
        # 開いたタブを記憶
        cw.cwpy.settingtab = self.note.GetSelection()
        self.Destroy()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.btn_ok, 0, 0, 0)
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT, 5)
        sizer_btn.Add(self.btn_dflt, 0, wx.LEFT, 5)

        sizer.Add(self.note, 0, 0, 0)
        sizer.Add(sizer_btn, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class GeneralSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # デバッグモード
        self.box_gene = wx.StaticBox(self, -1, "")
        self.cb_debug = wx.CheckBox(self, -1, u"デバッグモードでプレイする")
        self.cb_debug.SetValue(cw.cwpy.debug)
        self.cb_nolevelup = wx.CheckBox(
            self, -1, u"デバッグ中はレベル上昇を停止する")
        self.cb_nolevelup.SetValue(cw.cwpy.setting.no_levelup_in_debugmode)

        # 基本的なオプション
        self.cb_storeskinoneachbase = wx.CheckBox(
            self, -1, u"拠点ごとにスキンを記憶する")
        self.cb_storeskinoneachbase.SetValue(cw.cwpy.setting.store_skinoneachbase)

        # スキン
        self.box_skin = wx.StaticBox(self, -1, u"スキン",)
        self.skins = []
        self.skin_summarys = {}

        for name in os.listdir(u"Data/Skin"):
            path = cw.util.join_paths(u"Data/Skin", name)
            skinpath = cw.util.join_paths(u"Data/Skin", name, "Skin.xml")

            if os.path.isdir(path) and os.path.isfile(skinpath):
                self.skins.append(name)
                try:
                    e = cw.data.xml2element(skinpath, "Property")
                    skintype = e.gettext("Type", "")
                    skinname = e.gettext("Name", "")
                    author = e.gettext("Author", "")
                    desc = e.gettext("Description", "")
                    desc = cw.util.txtwrap(desc, 1)
                    self.skin_summarys[name] = (skintype, skinname, author, desc)
                except Exception:
                    # エラーのあるスキンは無視
                    cw.util.print_ex()

        self.ch_skin = wx.Choice(self, -1, size=(120, -1), choices=self.skins)
        n = self.skins.index(cw.cwpy.setting.skindirname)
        self.ch_skin.SetSelection(n)
        s = u"種別: %s\n名前: %s\n作者: %s\n" + "-" * 45 + "\n%s"
        s = s % self.skin_summarys[cw.cwpy.setting.skindirname]
        self.st_skin = wx.StaticText(self, -1, s)

        # 拡大表示モード
        self.box_expandmode = wx.StaticBox(self, -1, u"拡大表示方式(F4キーで拡大)")
        self.st_expandscr = wx.StaticText(self, -1, u"描画倍率:")
        self.st_expandwin = wx.StaticText(self, -1, u"表示倍率:")

        # 最大倍率を概算
        x, y = wx.DisplaySize()
        x = 10 * x / cw.SIZE_SCR[0]
        y = 10 * y / cw.SIZE_SCR[1]
        if cw.cwpy.setting.expandmode == "FullScreen" or cw.cwpy.setting.expandmode == "None":
            n = 10 # FullScreen中はスライドを1.0倍に仮設定
        else:
            n = int(10 * float(cw.cwpy.setting.expandmode))
        max = x if x < y else y
        if max < 10:
            max = 10
        if max < n:
            n = max

        self.ch_expanddrawing = wx.ComboBox(self, -1, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        i = 0
        val = 1
        while True:
            self.ch_expanddrawing.Append(u"%s倍" % (val))
            if cw.cwpy.setting.expanddrawing == val:
                self.ch_expanddrawing.Select(i)
            i += 1
            val *= 2
            if max < val*10:
                break
        if self.ch_expanddrawing.GetSelection() == -1:
            self.ch_expanddrawing.Select(0)

        self.sl_expand = wx.Slider(
            self, -1, n, 10, max, size=(120, -1),
            style=wx.SL_HORIZONTAL)
        self.st_expand = wx.StaticText(self, -1)
        self.cb_fullscreen = wx.CheckBox(self, -1, u"フルスクリーン")
        self.cb_fullscreen.SetValue(cw.cwpy.setting.expandmode == "FullScreen")

        self.makeExpandInfo()

        self.ln_expand = wx.StaticLine(self, -1, style=wx.HORIZONTAL)
        self.cb_smoothexpand = wx.CheckBox(self, -1,
                                           u"拡大後の画面を滑らかにする")
        self.cb_smoothexpand.SetValue(cw.cwpy.setting.smoothexpand)

        self._do_layout()
        self._bind()

    def _bind(self):
        ##self.cb_debug.Bind(wx.EVT_CHECKBOX, self.OnDebugCheck)
        self.ch_skin.Bind(wx.EVT_CHOICE, self.OnSkinChoice)
        self.sl_expand.Bind(wx.EVT_SLIDER, self.OnExpandChange)
        self.cb_fullscreen.Bind(wx.EVT_CHECKBOX, self.OnExpandChange)

    ##def OnDebugCheck(self, event):
    ##    if cw.cwpy.is_playingscenario():
    ##        self.cb_debug.SetValue(not self.cb_debug.GetValue())
    ##        dlg = cw.dialog.message.Message(
    ##            self.Parent.Parent, cw.cwpy.msgs["message"],
    ##            u"シナリオプレイ中はデバッグモードの切替はできません。")
    ##        cw.cwpy.frame.move_dlg(dlg)
    ##        cw.cwpy.sounds["error"].play()
    ##        dlg.ShowModal()

    def OnSkinChoice(self, event):
        skin = self.skins[self.ch_skin.GetSelection()]
        s = u"種別: %s\n名前: %s\n作者: %s\n" + "-" * 45 + "\n%s"
        self.st_skin.SetLabel(s % self.skin_summarys[skin])

    def makeExpandInfo(self):
        if self.cb_fullscreen.IsChecked():
            self.sl_expand.Disable()
            self.st_expand.SetLabel(u"フルスクリーン")
        else:
            self.sl_expand.Enable()
            n = self.sl_expand.GetValue()
            x = cw.SIZE_GAME[0] * n / 10
            y = cw.SIZE_GAME[1] * n / 10
            s = u"%d.%d倍 (%dx%d)" % (n/10, n%10, x, y)
            self.st_expand.SetLabel(s)

    def OnExpandChange(self, event):
        self.makeExpandInfo()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_skin = wx.StaticBoxSizer(self.box_skin, wx.VERTICAL)
        bsizer_expandmode = wx.StaticBoxSizer(self.box_expandmode, wx.VERTICAL)
        bsizer_expandmode_in = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_expandmode_draw = wx.BoxSizer(wx.HORIZONTAL)

        bsizer_gene.Add(self.cb_debug, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_nolevelup, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_storeskinoneachbase, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))
        bsizer_skin.Add(self.ch_skin, 0, wx.CENTER, 0)
        bsizer_skin.Add(self.st_skin, 0, wx.CENTER|wx.ALL, 3)
        bsizer_skin.SetMinSize((SETTINGS_WIDTH, 200))

        bsizer_expandmode_draw.Add(self.st_expandscr, 0, wx.RIGHT|wx.CENTER, 3)
        bsizer_expandmode_draw.Add(self.ch_expanddrawing, 0, wx.CENTER, 0)
        bsizer_expandmode_in.Add(self.st_expandwin, 0, wx.RIGHT|wx.CENTER, 3)
        bsizer_expandmode_in.Add(self.st_expand, 1, wx.CENTER, 3)
        bsizer_expandmode.Add(bsizer_expandmode_draw, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(bsizer_expandmode_in, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_expandmode.Add(self.sl_expand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(self.cb_fullscreen, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, 3)
        bsizer_expandmode.Add(self.ln_expand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(self.cb_smoothexpand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_expandmode.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_skin, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_expandmode, 0, wx.EXPAND, 0)
        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class DrawingSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.box_gene = wx.StaticBox(self, -1, "")
        # 背景拡大縮小補正
        self.cb_smooth_bg = wx.CheckBox(
            self, -1, u"拡大縮小した背景画像を滑らかにする")
        self.cb_smooth_bg.SetValue(cw.cwpy.setting.smoothscale_bg)
        # トランジション効果
        self.box_tran = wx.StaticBox(
            self, -1, u"背景の切り替え方式(速い⇔遅い)")
        self.transitions = [
            "None", "Fade", "PixelDissolve", "Blinds"]
        self.choices_tran = [
            u"アニメーションなし", u"フェード式",
            u"ピクセルディゾルブ式", u"ブラインド式"]
        self.ch_tran = wx.Choice(
            self, -1, size=(150, -1), choices=self.choices_tran)
        n = self.transitions.index(cw.cwpy.setting.transition)
        self.ch_tran.SetSelection(n)
        self.sl_tran = wx.Slider(
            self, -1, cw.cwpy.setting.transitionspeed, 0, 10,
            size=(SETTINGS_WIDTH-10, -1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_tran.SetTickFreq(1, 1)
        # カード描画速度
        self.box_deal = wx.StaticBox(
            self, -1, u"カード描画速度(速い⇔遅い)")
        self.sl_deal = wx.Slider(
            self, -1, cw.cwpy.setting.dealspeed - 1, 0, 10, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_deal.SetTickFreq(1, 1)
        # メッセージ表示速度
        self.box_msgs = wx.StaticBox(
            self, -1, u"メッセージ表示速度(速い⇔遅い)")
        self.sl_msgs = wx.Slider(
            self, -1, cw.cwpy.setting.messagespeed, 0, 10, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_msgs.SetTickFreq(1, 1)

        # メッセージウィンドウ背景色
        self.box_mwin = wx.StaticBox(self, -1, u"メッセージウィンドウ背景")
        self.st_mwin = wx.StaticText(self, -1, u"カラー")
        self.cs_mwin = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.mwincolour)
        self.st_blwin = wx.StaticText(self, -1, u"ログ")
        self.cs_blwin = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.blwincolour)
        self.st_mwin2 = wx.StaticText(self, -1, u"アルファ値")
        self.sc_mwin = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.sc_mwin.SetRange(0, 255)
        self.sc_mwin.SetValue(cw.cwpy.setting.mwincolour[3])
        # メッセージウィンドウ枠色
        self.box_mframe = wx.StaticBox(self, -1, u"メッセージウィンドウ枠")
        self.st_mframe = wx.StaticText(self, -1, u"カラー")
        self.cs_mframe = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.mwinframecolour)
        self.st_blframe = wx.StaticText(self, -1, u"ログ")
        self.cs_blframe = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.blwinframecolour)
        self.st_mframe2 = wx.StaticText(self, -1, u"アルファ値")
        self.sc_mframe = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.sc_mframe.SetRange(0, 255)
        self.sc_mframe.SetValue(cw.cwpy.setting.mwinframecolour[3])

        self._do_layout()
        self._bind()

    def _bind(self):
        pass

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_tran = wx.StaticBoxSizer(self.box_tran, wx.VERTICAL)
        bsizer_deal = wx.StaticBoxSizer(self.box_deal, wx.VERTICAL)
        bsizer_msgs = wx.StaticBoxSizer(self.box_msgs, wx.VERTICAL)

        bsizer_gene.Add(self.cb_smooth_bg, 0, wx.ALL, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))
        bsizer_tran.Add(self.ch_tran, 0, wx.BOTTOM, 5)
        bsizer_tran.Add(self.sl_tran, 0, wx.EXPAND, 0)
        bsizer_deal.Add(self.sl_deal, 0, wx.EXPAND, 0)
        bsizer_msgs.Add(self.sl_msgs, 0, wx.EXPAND, 0)

        bsizer_mwin = wx.StaticBoxSizer(self.box_mwin, wx.HORIZONTAL)
        gsizer_mwin = wx.GridBagSizer()
        gsizer_mwin.Add(self.st_mwin, pos=(0, 0), flag=wx.RIGHT|wx.CENTER, border=3)
        gsizer_mwin.Add(self.cs_mwin, pos=(0, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        gsizer_mwin.Add(self.st_blwin, pos=(1, 0), flag=wx.RIGHT|wx.CENTER, border=3)
        gsizer_mwin.Add(self.cs_blwin, pos=(1, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        bsizer_mwin.Add(gsizer_mwin, 0, wx.CENTER|wx.LEFT, 5)
        bsizer_mwin.Add(self.st_mwin2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mwin.Add(self.sc_mwin, 0, wx.CENTER|wx.RIGHT, 3)

        bsizer_mframe = wx.StaticBoxSizer(self.box_mframe, wx.HORIZONTAL)
        gsizer_mframe = wx.GridBagSizer()
        gsizer_mframe.Add(self.st_mframe, pos=(0, 0), flag=wx.RIGHT|wx.CENTER, border=3)
        gsizer_mframe.Add(self.cs_mframe, pos=(0, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        gsizer_mframe.Add(self.st_blframe, pos=(1, 0), flag=wx.RIGHT|wx.CENTER, border=3)
        gsizer_mframe.Add(self.cs_blframe, pos=(1, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        bsizer_mframe.Add(gsizer_mframe, 0, wx.CENTER|wx.LEFT, 5)
        bsizer_mframe.Add(self.st_mframe2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mframe.Add(self.sc_mframe, 0, wx.CENTER|wx.RIGHT, 3)

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_tran, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_deal, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_msgs, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_mwin, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_mframe, 0, wx.EXPAND, 0)
        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class AudioSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.box_gene = wx.StaticBox(self, -1, "")
        # 音楽を再生する
        self.cb_playbgm = wx.CheckBox(
            self, -1, u"音楽を再生する")
        self.cb_playbgm.SetValue(cw.cwpy.setting.play_bgm)
        # 効果音を再生する
        self.cb_playsound = wx.CheckBox(
            self, -1, u"効果音を再生する")
        self.cb_playsound.SetValue(cw.cwpy.setting.play_sound)

        # 音量
        self.box_music = wx.StaticBox(self, -1, u"ミュージック音量")
        n = int(cw.cwpy.setting.vol_bgm * 100)
        self.sl_music = wx.Slider(
            self, -1, n, 0, 100, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_music.SetTickFreq(10, 1)

        # midi音量
        self.box_midi = wx.StaticBox(self, -1, u"MIDIミュージック音量")
        n = int(cw.cwpy.setting.vol_midi * 100)
        self.sl_midi = wx.Slider(
            self, -1, n, 0, 100, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_midi.SetTickFreq(10, 1)

        # 効果音音量
        self.box_sound = wx.StaticBox(self, -1, u"効果音音量")
        n = int(cw.cwpy.setting.vol_sound * 100)
        self.sl_sound = wx.Slider(
            self, -1, n, 0, 100, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_sound.SetTickFreq(10, 1)

        # サウンドフォント
        self.box_soundfont = wx.StaticBox(self, -1, u"MIDIサウンドフォント")
        self.btn_addsoundfont = wx.Button(self, -1, u"追加...")
        self.btn_rmvsoundfont = wx.Button(self, -1, u"削除")
        self.btn_upsoundfont = wx.Button(self, -1, u"↑", size=(25, -1))
        self.btn_downsoundfont = wx.Button(self, -1, u"↓", size=(25, -1))
        self.list_soundfont = wx.ListBox(self, -1, size=(-1, -1), style=wx.MULTIPLE|wx.VSCROLL|wx.HSCROLL)
        for soundfont in cw.cwpy.setting.soundfonts:
            self.list_soundfont.Append(soundfont)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnAddSoundFontBtn, self.btn_addsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveSoundFontBtn, self.btn_rmvsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnUpSoundFontBtn, self.btn_upsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnDownSoundFontBtn, self.btn_downsoundfont)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_music = wx.StaticBoxSizer(self.box_music, wx.VERTICAL)
        bsizer_midi = wx.StaticBoxSizer(self.box_midi, wx.VERTICAL)
        bsizer_sound = wx.StaticBoxSizer(self.box_sound, wx.VERTICAL)
        bsizer_soundfont = wx.StaticBoxSizer(self.box_soundfont, wx.VERTICAL)

        bsizer_gene.Add(self.cb_playbgm, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_playsound, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_soundfontbtns = wx.BoxSizer(wx.HORIZONTAL)
        sizer_soundfontbtns.Add(self.btn_addsoundfont, 0, wx.RIGHT, 5)
        sizer_soundfontbtns.Add(self.btn_rmvsoundfont, 0, wx.RIGHT, 5)
        sizer_soundfontbtns.Add(self.btn_upsoundfont, 0, wx.RIGHT, 5)
        sizer_soundfontbtns.Add(self.btn_downsoundfont, 0, 0, 0)

        bsizer_music.Add(self.sl_music, 0, wx.EXPAND, 0)
        bsizer_midi.Add(self.sl_midi, 0, wx.EXPAND, 0)
        bsizer_sound.Add(self.sl_sound, 0, wx.EXPAND, 0)
        bsizer_soundfont.Add(sizer_soundfontbtns, 0, wx.ALL, 5)
        bsizer_soundfont.Add(self.list_soundfont, 1, wx.EXPAND|wx.LEFT|wx.BOTTOM|wx.RIGHT, 5)

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_music, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_midi, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_sound, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_soundfont, 1, wx.EXPAND, 0)

        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnAddSoundFontBtn(self, event):
        dlg = wx.FileDialog(self.GetTopLevelParent(), u"MIDIの演奏に使用するサウンドフォント選択", u"Data/SoundFont", "", "*.sf2", wx.FD_OPEN|wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            exists = set()
            for soundfont in self.list_soundfont.GetItems():
                exists.add(soundfont.lower())
            for fname in dlg.GetFilenames():
                fpath = os.path.join(dlg.GetDirectory(), fname)
                try:
                    rel = cw.util.relpath(fpath, u"")
                    if not rel.startswith(u".."):
                        fpath = rel
                except:
                    cw.util.print_ex()
                fpath = cw.util.join_paths(fpath)
                if fpath.lower() in exists:
                    continue
                self.list_soundfont.Append(fpath)

    def OnRemoveSoundFontBtn(self, event):
        for index in reversed(self.list_soundfont.GetSelections()):
            self.list_soundfont.Delete(index)

    def OnUpSoundFontBtn(self, event):
        for index in self.list_soundfont.GetSelections():
            if index == 0:
                return
            item = self.list_soundfont.GetString(index)
            self.list_soundfont.Delete(index)
            self.list_soundfont.Insert(item, index - 1)
            self.list_soundfont.Select(index - 1)

    def OnDownSoundFontBtn(self, event):
        for index in reversed(self.list_soundfont.GetSelections()):
            if index + 1 == self.list_soundfont.GetCount():
                return
            item = self.list_soundfont.GetString(index)
            self.list_soundfont.Delete(index)
            self.list_soundfont.Insert(item, index + 1)
            self.list_soundfont.Select(index + 1)

class ScenarioSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # シナリオのオプション
        self.box_gene = wx.StaticBox(self, -1, u"")
        self.cb_selectscenariofromtype = wx.CheckBox(self, -1, u"シナリオの選択開始位置をスキン毎に変更する")
        self.cb_selectscenariofromtype.SetValue(cw.cwpy.setting.selectscenariofromtype)
        self.cb_showunfitnessscenario = wx.CheckBox(self, -1, u"適正レベル以外のシナリオを表示する")
        self.cb_showunfitnessscenario.SetValue(cw.cwpy.setting.show_unfitnessscenario)
        self.cb_showcompletedscenario = wx.CheckBox(self, -1, u"終了済シナリオを表示する")
        self.cb_showcompletedscenario.SetValue(cw.cwpy.setting.show_completedscenario)
        self.cb_showinvisiblescenario = wx.CheckBox(self, -1, u"隠蔽シナリオを表示する")
        self.cb_showinvisiblescenario.SetValue(cw.cwpy.setting.show_invisiblescenario)

        # スキンタイプ毎の初期フォルダ
        self.box_folderoftype = wx.StaticBox(self, -1, u"シナリオフォルダ(スキンタイプ別)")
        self.btn_reffolder = wx.Button(self, -1, u"参照...")
        self.btn_removefolder = wx.Button(self, -1, u"削除")
        self.btn_upfolder = wx.Button(self, -1, u"↑", size=(25, -1))
        self.btn_downfolder = wx.Button(self, -1, u"↓", size=(25, -1))
        self.grid_folderoftype = wx.grid.Grid(self, -1, style=wx.BORDER)
        self.grid_folderoftype.CreateGrid(len(cw.cwpy.setting.folderoftype) + 1, 2)
        #self.grid_folderoftype.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        self.grid_folderoftype.SetColLabelSize(0)
        self.grid_folderoftype.SetRowLabelSize(0)
        self.grid_folderoftype.SetColSize(0, 100)
        self.grid_folderoftype.SetColSize(1, 150)

        types = set()
        for name, t in self.Parent.Parent.pane_gene.skin_summarys.iteritems():
            skintype, skinname, author, desc = t
            types.add(skintype)

        types = list(types)
        types.sort()

        colattr = wx.grid.GridCellAttr()
        colattr.SetEditor(wx.grid.GridCellChoiceEditor(types, allowOthers=True))
        self.grid_folderoftype.SetColAttr(0, colattr)

        for row in xrange(self.grid_folderoftype.GetNumberRows() - 1):
            skintype, folder = cw.cwpy.setting.folderoftype[row]
            self.grid_folderoftype.SetCellValue(row, 0, skintype)
            self.grid_folderoftype.SetCellValue(row, 1, folder)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnRefFolderBtn, self.btn_reffolder)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveFolderBtn, self.btn_removefolder)
        self.Bind(wx.EVT_BUTTON, self.OnUpFolderBtn, self.btn_upfolder)
        self.Bind(wx.EVT_BUTTON, self.OnDownFolderBtn, self.btn_downfolder)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnGridCellChange, self.grid_folderoftype)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_folderoftype = wx.StaticBoxSizer(self.box_folderoftype, wx.VERTICAL)

        bsizer_gene.Add(self.cb_selectscenariofromtype, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_showunfitnessscenario, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)
        bsizer_gene.Add(self.cb_showcompletedscenario, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)
        bsizer_gene.Add(self.cb_showinvisiblescenario, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_folderbtns = wx.BoxSizer(wx.HORIZONTAL)
        sizer_folderbtns.Add(self.btn_reffolder, 0, wx.RIGHT, 5)
        sizer_folderbtns.Add(self.btn_removefolder, 0, wx.RIGHT, 5)
        sizer_folderbtns.Add(self.btn_upfolder, 0, wx.RIGHT, 5)
        sizer_folderbtns.Add(self.btn_downfolder, 0, 0, 0)

        bsizer_folderoftype.Add(sizer_folderbtns, 0, wx.ALL, 5)
        bsizer_folderoftype.Add(self.grid_folderoftype, 1, wx.EXPAND|wx.LEFT|wx.BOTTOM|wx.RIGHT, 5)

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_folderoftype, 1, wx.EXPAND, 0)

        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnGridCellChange(self, event):
        if event.Col == 0 and event.Row + 1 == self.grid_folderoftype.GetNumberRows() and\
                self.grid_folderoftype.GetCellValue(event.Row, 0):
            self.grid_folderoftype.AppendRows(1)

    def OnRefFolderBtn(self, event):
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1:
            return

        type = self.grid_folderoftype.GetCellValue(row, 0)
        if not type:
            type = u"(指定無し)"

        dpath = os.path.abspath("Scenario")
        dlg = wx.DirDialog(self.TopLevelParent, u"「%s」タイプのスキンでプレイするシナリオのフォルダを選択してください。" % (type), dpath, style=wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            dpath = dlg.GetPath()
            relpath = cw.util.relpath(dpath, ".")
            if not relpath.startswith(".."):
                dpath = relpath
            self.grid_folderoftype.SetCellValue(row, 1, cw.util.join_paths(dpath))

    def OnRemoveFolderBtn(self, event):
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or row + 1 == self.grid_folderoftype.GetNumberRows():
            return
        self.grid_folderoftype.DeleteRows(row)

    def OnUpFolderBtn(self, event):
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or row == 0:
            return
        for col in xrange(self.grid_folderoftype.GetNumberCols()):
            value1 = self.grid_folderoftype.GetCellValue(row, col)
            value2 = self.grid_folderoftype.GetCellValue(row - 1, col)
            self.grid_folderoftype.SetCellValue(row, col, value2)
            self.grid_folderoftype.SetCellValue(row - 1, col, value1)
        self.grid_folderoftype.SetGridCursor(row - 1, self.grid_folderoftype.GetGridCursorCol())

    def OnDownFolderBtn(self, event):
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or self.grid_folderoftype.GetNumberRows() <= row + 2:
            return
        for col in xrange(self.grid_folderoftype.GetNumberCols()):
            value1 = self.grid_folderoftype.GetCellValue(row, col)
            value2 = self.grid_folderoftype.GetCellValue(row + 1, col)
            self.grid_folderoftype.SetCellValue(row, col, value2)
            self.grid_folderoftype.SetCellValue(row + 1, col, value1)
        self.grid_folderoftype.SetGridCursor(row + 1, self.grid_folderoftype.GetGridCursorCol())

class UISettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # 描画オプション
        self.box_draw = wx.StaticBox(self, -1, "")
        self.cb_quickdeal = wx.CheckBox(
            self, -1, u"キャンプモードへ高速で切り替える")
        self.cb_quickdeal.SetValue(cw.cwpy.setting.quickdeal)
        self.cb_allquickdeal = wx.CheckBox(
            self, -1, u"全てのシステムカードを高速表示する")
        self.cb_allquickdeal.SetValue(cw.cwpy.setting.all_quickdeal)
        self.cb_showallselectedcards = wx.CheckBox(
            self, -1, u"戦闘行動を全員分表示する")
        self.cb_showallselectedcards.SetValue(cw.cwpy.setting.show_allselectedcards)
        self.cb_showstatustime = wx.CheckBox(
            self, -1, u"状態の残り時間をカード上に表示する")
        self.cb_showstatustime.SetValue(cw.cwpy.setting.show_statustime)

        # インタフェースオプション
        self.box_gene = wx.StaticBox(self, -1, "")
        self.cb_showbackpackcard = wx.CheckBox(
            self, -1, u"荷物袋のカードを一時的に取り出して使えるようにする")
        self.cb_showbackpackcard.SetValue(cw.cwpy.setting.show_backpackcard)
        self.cb_revertcardpocket = wx.CheckBox(
            self, -1, u"レベル調節で手放したカードを自動的に戻す")
        self.cb_revertcardpocket.SetValue(cw.cwpy.setting.revert_cardpocket)
        self.cb_showlogwithwheelup = wx.CheckBox(
            self, -1, u"マウスホイールを上に回すとログを表示")
        self.cb_showlogwithwheelup.SetValue(cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG)

        # ダイアログオプション
        self.box_dlg = wx.StaticBox(self, -1, "")
        self.cb_cautionbeforesaving = wx.CheckBox(
            self, -1, u"保存せずに終了しようとしたら警告する")
        self.cb_cautionbeforesaving.SetValue(cw.cwpy.setting.store_skinoneachbase)
        self.cb_confirmbeforesaving = wx.CheckBox(
            self, -1, u"セーブ前に確認ダイアログを表示")
        self.cb_confirmbeforesaving.SetValue(cw.cwpy.setting.confirm_beforesaving)
        self.cb_showsavedmessage = wx.CheckBox(
            self, -1, u"セーブ完了時に確認ダイアログを表示")
        self.cb_showsavedmessage.SetValue(cw.cwpy.setting.show_savedmessage)
        self.cb_confirmbeforeusingcard = wx.CheckBox(
            self, -1, u"カード使用時に確認ダイアログを表示")
        self.cb_confirmbeforeusingcard.SetValue(cw.cwpy.setting.confirm_beforeusingcard)

        self._do_layout()
        self._bind()

    def _bind(self):
        pass

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_draw = wx.StaticBoxSizer(self.box_draw, wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_dlg = wx.StaticBoxSizer(self.box_dlg, wx.VERTICAL)

        bsizer_draw.Add(self.cb_quickdeal, 0, wx.ALL, 3)
        bsizer_draw.Add(self.cb_allquickdeal, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.Add(self.cb_showallselectedcards, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.Add(self.cb_showstatustime, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_gene.Add(self.cb_showbackpackcard, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_revertcardpocket, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_showlogwithwheelup, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_dlg.Add(self.cb_cautionbeforesaving, 0, wx.ALL, 3)
        bsizer_dlg.Add(self.cb_confirmbeforesaving, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.Add(self.cb_showsavedmessage, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.Add(self.cb_confirmbeforeusingcard, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_v1.Add(bsizer_draw, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_dlg, 0, wx.EXPAND, 0)
        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
