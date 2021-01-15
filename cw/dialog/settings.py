#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import sys
import itertools
import wx
import wx.grid
import pygame

import cw

from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union


# build_exe.pyによって作られる一時モジュール
# cw.versioninfoからビルド時間の情報を得る
try:
    import versioninfo
except ImportError:
    versioninfo = None


def _settings_width() -> int:
    return cw.ppis(250)


def create_versioninfo(parent: Union["SimpleSettingsPanel", "SettingsPanel"]) -> None:
    """バージョン情報を表示するwx.TextCtrlを生成する。"""
    if sys.maxsize == 0x7fffffff:
        bits = "32-bit"
    elif sys.maxsize == 0x7fffffffffffffff:
        bits = "64-bit"
    else:
        assert False
    s = "%s %s (%s)" % (cw.APP_NAME, ".".join([str(a) for a in cw.APP_VERSION]), bits)
    if versioninfo:
        s = "%s\nBuild: %s" % (s, versioninfo.build_datetime)
    parent.versioninfo = wx.TextCtrl(parent, -1, s, size=(-1, -1),
                                     style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL | wx.NO_BORDER)
    parent.versioninfo.SetBackgroundColour(parent.GetBackgroundColour())
    dc = wx.ClientDC(parent.versioninfo)
    w, h, _lh = dc.GetFullMultiLineTextExtent(s)
    parent.versioninfo.SetMinSize((w + cw.ppis(15), h))


def apply_levelupparams(can_levelup: bool) -> None:
    """レベル調節に関する状況が変わった時に呼び出され、
    レベルアップ不可→可能になった時にレベル上昇処理を行う。
    """
    def check_levelup(can_levelup_old: bool) -> None:
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


if sys.platform == "win32":
    _spin_w_addition = 0
else:
    _spin_w_addition = 70


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        """設定ダイアログ。
        """
        cw.cwpy.frame.filter_event = self.OnFilterEvent
        self.panel = None
        if cw.cwpy.setting.show_advancedsettings:
            wx.Dialog.__init__(self, parent, -1, cw.APP_NAME + "の設定(詳細モード)",
                               style=wx.DEFAULT_DIALOG_STYLE | wx.MINIMIZE_BOX)
            self.panel = SettingsPanel(self)
        else:
            wx.Dialog.__init__(self, parent, -1, cw.APP_NAME + "の設定",
                               style=wx.DEFAULT_DIALOG_STYLE | wx.MINIMIZE_BOX)
            self.panel = SimpleSettingsPanel(self)
        self.cwpy_debug = True  # このダイアログではスクリーンショットの撮影を行わない

        self._bind()
        self._do_layout()

    def _bind(self) -> None:
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.panel, 1, wx.EXPAND, cw.ppis(0))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnFilterEvent(self, event: wx.Event) -> bool:
        if not self:
            return False
        if event.GetEventType() in (wx.EVT_TEXT.typeId,
                                    wx.EVT_SPINCTRL.typeId,
                                    wx.EVT_COMBOBOX.typeId,
                                    wx.EVT_CHECKBOX.typeId,
                                    wx.EVT_SLIDER.typeId,
                                    wx.EVT_CHOICE.typeId,
                                    wx.EVT_COLOURPICKER_CHANGED.typeId,
                                    wx.grid.EVT_GRID_CELL_CHANGED.typeId,
                                    wx.grid.EVT_GRID_EDITOR_SHOWN.typeId):
            obj = event.GetEventObject()
            if event.GetEventType() is wx.grid.EVT_GRID_EDITOR_SHOWN.typeId:
                if isinstance(obj, wx.grid.Grid):
                    assert isinstance(event, wx.grid.GridEvent)
                    editor = obj.GetCellEditor(event.GetRow(), event.GetCol())
                    if isinstance(editor, wx.grid.GridCellBoolEditor):
                        self.applied()
            elif isinstance(obj, wx.Window) and obj.GetTopLevelParent() is self:
                self.applied()
        return False

    def applied(self) -> None:
        if self.panel:
            self.panel.btn_apply.Enable()

    def clear_applied(self) -> None:
        if self.panel:
            self.panel.btn_apply.Disable()

    def OnClose(self, event: wx.CloseEvent) -> None:
        assert self.panel
        cw.cwpy.frame.filter_event = None
        self.panel.close()
        self.Destroy()

    def show_details(self) -> None:
        simple = self.panel
        assert isinstance(simple, SimpleSettingsPanel)
        self.panel = SettingsPanel(self)

        self.panel.pane_gene.cb_debug.SetValue(simple.cb_debug.GetValue())
        self.panel.pane_gene.skin.copy_values(simple.skin)
        self.panel.pane_gene.expand.copy_values(simple.expand)
        self.panel.pane_draw.speed.copy_values(simple.speed)
        self.panel.pane_sound.cb_playbgm.SetValue(simple.cb_playbgm.GetValue())
        self.panel.pane_sound.cb_playsound.SetValue(simple.cb_playsound.GetValue())

        simple.Destroy()
        self._do_layout()

        self.SetTitle(cw.APP_NAME + "の設定(詳細モード)")

        # モニタ内に収める
        cw.util.adjust_position(self)


class SimpleSettingsPanel(wx.Panel):
    versioninfo: wx.TextCtrl

    def __init__(self, parent: SettingsDialog) -> None:
        wx.Panel.__init__(self, parent, -1)

        self.panel = wx.Panel(self, -1, style=wx.SIMPLE_BORDER)
        if sys.platform == "win32":
            self.panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT))

        # デバッグモード
        self.box_debug = wx.StaticBox(self.panel, -1, "デバッグ")
        self.cb_debug = wx.CheckBox(self.panel, -1, "デバッグモード(Ctrl+Dでも切替可)")
        self.cb_debug.SetValue(cw.cwpy.is_debugmode())

        # スキン
        self.box_skin = wx.StaticBox(self.panel, -1, "スキン")
        self.skin = SkinPanel(self.panel, False)

        # 拡大表示モード
        self.box_expandmode = wx.StaticBox(self.panel, -1, "拡大表示方式(F4キーで拡大)")
        self.expand = ExpandPanel(self.panel, False)
        self.expand.load(cw.cwpy.setting)

        # 背景切替方式と各種速度
        self.speed: SpeedPanel = SpeedPanel(self.panel, False)
        self.speed.load(cw.cwpy.setting)

        self.box_audio = wx.StaticBox(self.panel, -1, "音声")
        # 音楽を再生する
        self.cb_playbgm: wx.CheckBox = wx.CheckBox(self.panel, -1, "音楽を再生する")
        self.cb_playbgm.SetValue(cw.cwpy.setting.play_bgm)
        # 効果音を再生する
        self.cb_playsound: wx.CheckBox = wx.CheckBox(self.panel, -1, "効果音を再生する")
        self.cb_playsound.SetValue(cw.cwpy.setting.play_sound)

        create_versioninfo(self)

        self.btn_details = wx.Button(self, wx.NewId(), "詳細設定...")
        self.btn_ok = wx.Button(self, wx.ID_OK, "OK")
        self.btn_apply: wx.Button = wx.Button(self, wx.ID_APPLY, "適用")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, "キャンセル")

        self.btn_apply.Disable()

        self._do_layout()
        self._bind()

    def _bind(self) -> None:
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self.OnDetails, id=self.btn_details.GetId())

    def OnOk(self, event: wx.CommandEvent) -> None:
        self.apply()
        if sys.platform == "win32":
            # FIXME: クローズしながらスキンを切り替えると時々エラーになる
            #        原因不明の不具合があるので、ダイアログのクローズを遅延する
            def func(self: SimpleSettingsPanel) -> None:
                def func(self: SimpleSettingsPanel) -> None:
                    if self:
                        self.Parent.Close()
                cw.cwpy.frame.exec_func(func, self)
            cw.cwpy.exec_func(func, self)
            self.Parent.Disable()
        else:
            self.Parent.Close()

    def OnApply(self, event: wx.CommandEvent) -> None:
        self.apply()

    def apply(self) -> None:
        # 設定変更前はレベル上昇が可能な状態だったか
        can_levelup = not (cw.cwpy.is_debugmode() and cw.cwpy.setting.no_levelup_in_debugmode)

        # デバッグ
        value = self.cb_debug.GetValue()
        if not value == cw.cwpy.setting.debug:
            cw.cwpy.exec_func(cw.cwpy.set_debug, value)

        # 拡大倍率
        self.expand.apply_expand(cw.cwpy.setting)

        # 描画
        updatemessage = self.speed.apply_speed(cw.cwpy.setting)
        if updatemessage:
            cw.cwpy.exec_func(cw.cwpy.update_messagestyle)

        # オーディオ
        value = self.cb_playbgm.GetValue()
        cw.cwpy.setting.play_bgm = value
        value = self.cb_playsound.GetValue()
        cw.cwpy.setting.play_sound = value
        for music in cw.cwpy.music:
            music.set_volume()

        # スキン
        self.skin.apply_skin(False)

        # レベル調節
        apply_levelupparams(can_levelup)

        debugger = cw.cwpy.is_showingdebugger()
        if debugger:
            debugger.refresh_tools()

        self.GetTopLevelParent().clear_applied()

    def OnClose(self, event: wx.CloseEvent) -> None:
        self.Parent.Close()

    def close(self) -> None:
        pass

    def OnDetails(self, event: wx.CommandEvent) -> None:
        self.Parent.show_details()

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_debug = wx.StaticBoxSizer(self.box_debug, wx.VERTICAL)
        sizer_debug.Add(self.cb_debug, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_skin = wx.StaticBoxSizer(self.box_skin, wx.VERTICAL)
        sizer_skin.Add(self.skin, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_skin.SetMinSize((cw.ppis(270), -1))
        sizer_expand = wx.StaticBoxSizer(self.box_expandmode, wx.VERTICAL)
        sizer_expand.Add(self.expand, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_audio = wx.StaticBoxSizer(self.box_audio, wx.VERTICAL)
        sizer_audio.Add(self.cb_playbgm, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_audio.Add(self.cb_playsound, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))

        sizer_left.Add(sizer_debug, 0, wx.EXPAND, cw.ppis(0))
        sizer_left.Add(sizer_skin, 1, wx.EXPAND | wx.TOP, cw.ppis(3))
        sizer_left.Add(sizer_audio, 0, wx.EXPAND | wx.TOP, cw.ppis(3))

        sizer_right.Add(sizer_expand, 0, wx.EXPAND, cw.ppis(0))
        sizer_right.Add(self.speed, 0, wx.EXPAND | wx.TOP, cw.ppis(3))

        sizer_btn.Add(self.btn_details, 0, wx.ALIGN_CENTER, cw.ppis(0))
        sizer_btn.AddStretchSpacer(1)
        sizer_btn.Add(self.versioninfo, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, cw.ppis(10))
        sizer_btn.AddStretchSpacer(1)
        sizer_btn.Add(self.btn_ok, 0, wx.ALIGN_CENTER)
        sizer_btn.Add(self.btn_apply, 0, wx.LEFT | wx.ALIGN_CENTER, cw.ppis(5))
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT | wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(5))

        sizer_h1.Add(sizer_left, 1, wx.EXPAND | wx.ALL, cw.ppis(10))
        sizer_h1.Add(sizer_right, 0, wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, cw.ppis(10))

        self.panel.SetSizer(sizer_h1)

        sizer.Add(self.panel, 0, wx.EXPAND, cw.ppis(0))
        sizer.Add(sizer_btn, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, cw.ppis(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class SettingsPanel(wx.Panel):
    versioninfo: wx.TextCtrl

    def __init__(self, parent: SettingsDialog) -> None:
        wx.Panel.__init__(self, parent, pos=(-1024, -1024))
        self.SetDoubleBuffered(True)
        self.Hide()

        self.note = wx.Notebook(self)
        self.pane_gene = GeneralSettingPanel(self.note)
        self.pane_draw = DrawingSettingPanel(self.note, for_local=False, get_localsettings=None,
                                             use_copybase=True)
        self.pane_sound = AudioSettingPanel(self.note)
        self.pane_font = FontSettingPanel(self.note, for_local=False, get_localsettings=None,
                                          use_copybase=True)
        self.pane_scenario = ScenarioSettingPanel(self.note)
        self.pane_ui = UISettingPanel(self.note)
        self.note.AddPage(self.pane_gene, "一般")
        self.note.AddPage(self.pane_draw, "描画")
        self.note.AddPage(self.pane_sound, "音声")
        self.note.AddPage(self.pane_font, "フォント")
        self.note.AddPage(self.pane_scenario, "シナリオ")
        self.note.AddPage(self.pane_ui, "詳細")
        self.pane_gene.skin.pane_scenario = self.pane_scenario

        create_versioninfo(self)

        self.btn_dflt = wx.Button(self, wx.ID_DEFAULT, "デフォルト")
        h = self.btn_dflt.GetBestSize()[1]

        self.btn_save = wx.BitmapButton(self, -1, cw.cwpy.rsrc.debugs["SETTINGS_SAVE"])
        self.btn_save.SetToolTip("設定の保存")
        self.btn_save.SetMinSize((cw.ppis(32), h))
        self.btn_load = wx.BitmapButton(self, -1, cw.cwpy.rsrc.debugs["SETTINGS_LOAD"])
        self.btn_load.SetToolTip("設定の読み込み")
        self.btn_load.SetMinSize((cw.ppis(32), h))

        self.btn_ok = wx.Button(self, wx.ID_OK, "OK")
        self.btn_apply: wx.Button = wx.Button(self, wx.ID_APPLY, "適用")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, "キャンセル")

        self.note.SetSelection(cw.cwpy.settingtab)

        self.load(cw.cwpy.setting)

        self.btn_apply.Disable()

        self._do_layout()
        self._bind()
        self.Show()

    def _bind(self) -> None:
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self.OnDefault, id=wx.ID_DEFAULT)
        self.Bind(wx.EVT_BUTTON, self.OnSave, id=self.btn_save.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnLoad, id=self.btn_load.GetId())

    def load(self, setting: cw.setting.Setting) -> None:
        self.pane_gene.load(setting)
        self.pane_draw.load(setting, setting.local)
        self.pane_sound.load(setting)
        self.pane_font.load(setting, setting.local)
        self.pane_scenario.load(setting)
        self.pane_ui.load(setting)

    def OnSave(self, event: wx.CommandEvent) -> None:
        tip = "CardWirthPy設定ファイル (*.wssx)|*.wssx|XMLドキュメント (*.xml)|*.xml|すべてのファイル (*.*)|*.*"
        dlg = wx.FileDialog(self.GetTopLevelParent(), "設定ファイルの保存",
                            "", "新規設定.wssx",
                            tip,
                            wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            fpath = dlg.GetPath()
            try:
                setting = cw.setting.Setting()
                setting.init_settings(init=False)
                self.apply(setting)
                cw.xmlcreater.create_settings(setting, writeplayingdata=False, fpath=fpath)
            except Exception:
                cw.util.print_ex()
                s = "%sの保存に失敗しました。" % (os.path.basename(fpath))
                wx.MessageBox(s, "メッセージ", wx.OK | wx.ICON_WARNING, self.GetTopLevelParent())
        dlg.Destroy()

    def OnLoad(self, event: wx.CommandEvent) -> None:
        dlg = wx.FileDialog(self.GetTopLevelParent(), "設定ファイルの読み込み",
                            "", "", "CardWirthPy設定ファイル (*.wssx)|*.wssx|XMLドキュメント (*.xml)|*.xml|すべてのファイル (*.*)|*.*",
                            wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            fpath = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            try:
                setting = cw.setting.Setting()
                setting.init_settings(loadfile=fpath)
                self.load(setting)
                self.GetTopLevelParent().applied()
            except Exception:
                cw.util.print_ex()
                s = "%sの読み込みに失敗しました。" % (os.path.basename(fpath))
                wx.MessageBox(s, "メッセージ", wx.OK | wx.ICON_WARNING, self.GetTopLevelParent())
        dlg.Destroy()

    def OnDefault(self, event: wx.CommandEvent) -> None:
        selpane = self.note.GetSelection()
        if selpane == 0:
            self.pane_gene.init_values(cw.cwpy.setting)
        elif selpane == 1:
            self.pane_draw.init_values(cw.cwpy.setting, cw.cwpy.setting.local)
        elif selpane == 2:
            self.pane_sound.init_values(cw.cwpy.setting)
        elif selpane == 3:
            self.pane_font.init_values(cw.cwpy.setting, cw.cwpy.setting.local)
        elif selpane == 4:
            # スキン毎のシナリオ開始位置の設定は変更しない
            self.pane_scenario.init_values(cw.cwpy.setting)
        elif selpane == 5:
            self.pane_ui.init_values(cw.cwpy.setting)

        self.GetTopLevelParent().applied()

    def OnOk(self, event: wx.CommandEvent) -> None:
        self.apply(cw.cwpy.setting)

        if sys.platform == "win32":
            # FIXME: クローズしながらスキンを切り替えると時々エラーになる
            #        原因不明の不具合があるので、ダイアログのクローズを遅延する
            def func(self: SettingsPanel) -> None:
                def func(self: SettingsPanel) -> None:
                    if self:
                        self.Parent.Close()
                cw.cwpy.frame.exec_func(func, self)
            cw.cwpy.exec_func(func, self)
            self.Parent.Disable()
        else:
            self.Parent.Close()

    def OnApply(self, event: wx.CommandEvent) -> None:
        self.apply(cw.cwpy.setting)

    def apply(self, setting: cw.setting.Setting) -> None:
        update = (setting == cw.cwpy.setting)

        # 設定変更前はレベル上昇が可能な状態だったか
        can_levelup = not (cw.cwpy.is_debugmode() and cw.cwpy.setting.no_levelup_in_debugmode)
        updatestatusbar = False  # ステータスバーの更新が必要か

        # フォント
        flag_fontupdate, updatecardimg, updatemcardimg, updatemessage =\
            self.pane_font.apply_localsettings(setting.local)

        # 一般
        if update:
            value = self.pane_gene.cb_debug.GetValue()
            if not value == cw.cwpy.setting.debug:
                cw.cwpy.exec_func(cw.cwpy.set_debug, value)

        value = self.pane_gene.cb_show_tiles.GetValue()
        if value != setting.show_tiles:
            setting.show_tiles = value
            updatestatusbar = True
        value = self.pane_gene.cb_enabled_right_flick.GetValue()
        setting.enabled_right_flick = value
        value = self.pane_gene.cb_can_repeatlclick.GetValue()
        setting.can_repeatlclick = value

        # value = self.pane_gene.cb_show_debuglogdialog.GetValue()
        # setting.show_debuglogdialog = value
        value = self.pane_gene.cb_nolevelup.GetValue()
        setting.no_levelup_in_debugmode = value
        value = self.pane_gene.sc_initmoneyamount.GetValue()
        setting.initmoneyamount = value
        value = self.pane_gene.cb_initmoneyisinitialcash.GetValue()
        setting.initmoneyisinitialcash = value
        value = self.pane_gene.cb_autosavepartyrecord.GetValue()
        setting.autosave_partyrecord = value
        value = self.pane_gene.cb_overwritepartyrecord.GetValue()
        setting.overwrite_partyrecord = value
        value = self.pane_gene.tx_ssinfoformat.GetValue()
        setting.ssinfoformat = value
        value = self.pane_gene.tx_ssfnameformat.GetValue()
        setting.ssfnameformat = value
        value = self.pane_gene.tx_cardssfnameformat.GetValue()
        setting.cardssfnameformat = value
        value = self.pane_gene.ch_ssinfocolor.GetSelection()
        if value == 1:
            setting.ssinfofontcolor = (255, 255, 255)
            setting.ssinfobackcolor = (0, 0, 0)
        else:
            setting.ssinfofontcolor = (0, 0, 0)
            setting.ssinfobackcolor = (255, 255, 255)
        value = self.pane_gene.tx_ssinfobackimage.GetValue()
        setting.ssinfobackimage = value
        value = self.pane_gene.cb_sswithstatusbar.GetValue()
        setting.sswithstatusbar = value
        value = self.pane_gene.ch_messagelog_type.GetSelection()
        if value == 0:
            value = cw.setting.LOG_SINGLE
        elif value == 1:
            value = cw.setting.LOG_LIST
        elif value == 2:
            value = cw.setting.LOG_COMPRESS
        setting.messagelog_type = value
        value = self.pane_gene.ch_startupscene.GetSelection()
        if value == 0:
            value = cw.setting.OPEN_TITLE
        elif value == 1:
            value = cw.setting.OPEN_LAST_BASE
        setting.startupscene = value
        value = self.pane_gene.sc_backlogmax.GetValue()
        if value != setting.backlogmax:
            if update:
                def func(backlogmax: int) -> None:
                    cw.cwpy.set_backlogmax(backlogmax)
                cw.cwpy.exec_func(func, value)
                updatestatusbar = True
            else:
                setting.backlogmax = value

        # 拡大倍率
        self.pane_gene.expand.apply_expand(setting)

        # 描画
        updatebg = False
        value = self.pane_draw.cb_smooth_bg.GetValue()
        if setting.smoothscale_bg != value:
            updatebg = True
            setting.smoothscale_bg = value

        value = self.pane_draw.cb_smoothing_card_up.GetValue()
        if setting.smoothing_card_up != value:
            updatemcardimg = True
            updatecardimg = True
            setting.smoothing_card_up = value
        value = self.pane_draw.cb_smoothing_card_down.GetValue()
        if setting.smoothing_card_down != value:
            updatemcardimg = True
            updatecardimg = True
            setting.smoothing_card_down = value

        updatemessage |= self.pane_draw.speed.apply_speed(setting)

        value = self.pane_draw.cb_whitecursor.GetValue()
        if value != (setting.cursor_type == cw.setting.CURSOR_WHITE):
            if value:
                setting.cursor_type = cw.setting.CURSOR_WHITE
            else:
                setting.cursor_type = cw.setting.CURSOR_BLACK
            if update:
                def func_cursor() -> None:
                    cw.cwpy.change_cursor(cw.cwpy.cursor, force=True)
                cw.cwpy.exec_func(func_cursor)

        # オーディオ
        value = self.pane_sound.cb_playbgm.GetValue()
        setting.play_bgm = value
        value = self.pane_sound.cb_playsound.GetValue()
        setting.play_sound = value
        value = self.pane_sound.sl_master.GetValue()
        value = cw.setting.Setting.wrap_volumevalue(value)
        setting.vol_master = value
        value = self.pane_sound.sl_sound.GetValue()
        value = cw.setting.Setting.wrap_volumevalue(value)
        if setting.vol_sound != value:
            setting.vol_sound = value
            setting.vol_sound_midi = value
        value = self.pane_sound.sl_midi.GetValue()
        value = cw.setting.Setting.wrap_volumevalue(value)
        setting.vol_bgm_midi = value
        value = self.pane_sound.sl_music.GetValue()
        value = cw.setting.Setting.wrap_volumevalue(value)
        setting.vol_bgm = value
        value = self.pane_sound.sl_master.GetValue()
        value = cw.setting.Setting.wrap_volumevalue(value)
        setting.vol_master = value
        if update:
            volume = int(setting.vol_master*100)
            cw.cwpy.exec_func(cw.cwpy.set_mastervolume, volume)
        soundfonts = []
        for row in range(self.pane_sound.grid_soundfont.GetNumberRows()):
            soundfont = self.pane_sound.get_soundfont(row)
            soundfonts.append(soundfont)
        if setting.soundfonts != soundfonts:
            sfonts1 = [(sfont[0], sfont[2]/100.0) for sfont in soundfonts if sfont[1]]
            sfonts2 = [(sfont[0], sfont[2]/100.0) for sfont in setting.soundfonts if sfont[1]]
            setting.soundfonts = soundfonts
            if update and sfonts1 != sfonts2:
                def func_sfonts() -> None:
                    if cw.bassplayer.is_alivable():
                        if cw.bassplayer.change_soundfonts(sfonts1):
                            for music in cw.cwpy.music:
                                music.play(music.path, updatepredata=False, restart=True)
                            return

                    if cw.bassplayer.is_alivable():
                        cw.bassplayer.dispose_bass()
                    if cw.cwpy.setting.sdlmixer_enabled and pygame.mixer.get_init():
                        pygame.mixer.quit()

                    if sfonts1:
                        cw.bassplayer.init_bass(sfonts1)
                    elif cw.cwpy.setting.sdlmixer_enabled:
                        cw.util.sdlmixer_init()

                    if bool(sfonts1) != bool(sfonts2):
                        cw.cwpy.init_sounds()
                    for music in cw.cwpy.music:
                        music.play(music.path, updatepredata=False, restart=True)

                cw.cwpy.exec_func(func_sfonts)

        # 配色(メッセージ)
        r_updatemessage, updatecurtain, updatefullscreen = self.pane_draw.apply_localsettings(setting.local)
        updatemessage |= r_updatemessage

        if update and updatemessage:
            cw.cwpy.exec_func(cw.cwpy.update_messagestyle)

        if update and updatecurtain:
            cw.cwpy.exec_func(cw.cwpy.update_curtainstyle)

        if update and updatefullscreen:
            def func1() -> None:
                cw.cwpy.update_fullscreenbackground()

            cw.cwpy.exec_func(func1)

        # スキン
        if update:
            if self.pane_gene.skin.apply_skin(flag_fontupdate):
                updatecardimg = False
                updatemcardimg = False
                updatebg = False

        # レベル調節
        if update:
            apply_levelupparams(can_levelup)

        # シナリオ
        value = self.pane_scenario.tx_editor.GetValue()
        setting.editor = value
        value = self.pane_scenario.cb_selectscenariofromtype.GetValue()
        setting.selectscenariofromtype = value
        value = self.pane_scenario.cb_show_paperandtree.GetValue()
        setting.show_paperandtree = value
        if setting.show_paperandtree:
            setting.show_scenariotree = False
        value = self.pane_scenario.cb_write_playlog.GetValue()
        if value != setting.write_playlog:
            setting.write_playlog = value

            def func_advlog() -> None:
                cw.cwpy.advlog.enable(setting.write_playlog)
            cw.cwpy.exec_func(func_advlog)
        value = self.pane_scenario.cb_can_installscenariofromdrop.GetValue()
        setting.can_installscenariofromdrop = value
        value = self.pane_scenario.cb_delete_sourceafterinstalled.GetValue()
        setting.delete_sourceafterinstalled = value
        value = self.pane_scenario.tx_filer_dir.GetValue()
        setting.filer_dir = value
        value = self.pane_scenario.tx_filer_file.GetValue()
        setting.filer_file = value
        value = self.pane_scenario.cb_open_lastscenario.GetValue()
        setting.open_lastscenario = value

        setting.folderoftype = []
        for row in range(self.pane_scenario.grid_folderoftype.GetNumberRows() - 1):
            skintype = self.pane_scenario.grid_folderoftype.GetCellValue(row, 0)
            folder = self.pane_scenario.grid_folderoftype.GetCellValue(row, 1)
            setting.folderoftype.append((skintype, folder))

        # 詳細
        value = self.pane_ui.cb_can_skipwait.GetValue()
        setting.can_skipwait = value
        value = self.pane_ui.cb_can_skipanimation.GetValue()
        setting.can_skipanimation = value
        value = self.pane_ui.cb_can_skipwait_with_wheel.GetValue()
        setting.can_skipwait_with_wheel = value
        value = self.pane_ui.cb_can_forwardmessage_with_wheel.GetValue()
        setting.can_forwardmessage_with_wheel = value
        value = self.pane_ui.cb_wait_usecard.GetValue()
        setting.wait_usecard = value
        value = self.pane_ui.cb_enlarge_beastcardzoomingratio.GetValue()
        setting.enlarge_beastcardzoomingratio = value
        value = self.pane_ui.cb_autoenter_on_sprite.GetValue()
        setting.autoenter_on_sprite = value

        value = self.pane_ui.cb_quickdeal.GetValue()
        setting.quickdeal = value
        value = self.pane_ui.cb_allquickdeal.GetValue()
        setting.all_quickdeal = value
        value = self.pane_ui.cb_showallselectedcards.GetValue()
        setting.show_allselectedcards = value
        value = self.pane_ui.ch_show_statustime.GetSelection()
        if value == 0:
            value = "NotEventTime"
        elif value == 1:
            value = "True"
        else:
            value = "False"
        if setting.show_statustime != value:
            setting.show_statustime = value
            updatecardimg = True
        value = self.pane_ui.cb_show_cardkind.GetValue()
        if setting.show_cardkind != value:
            setting.show_cardkind = value
            updatemcardimg = True
        value = self.pane_ui.cb_show_premiumicon.GetValue()
        if setting.show_premiumicon != value:
            setting.show_premiumicon = value
            updatemcardimg = True

        value = self.pane_ui.cb_showlogwithwheelup.GetValue()
        if value:
            setting.wheelup_operation = cw.setting.WHEEL_SHOWLOG
        else:
            setting.wheelup_operation = cw.setting.WHEEL_SELECTION

        value = self.pane_ui.cb_show_btndesc.GetValue()
        setting.show_btndesc = value
        value = self.pane_ui.cb_statusbarmask.GetValue()
        if value != setting.statusbarmask:
            setting.statusbarmask = value
            updatestatusbar = True
        value = self.pane_ui.cb_blink_statusbutton.GetValue()
        setting.blink_statusbutton = value
        value = self.pane_ui.cb_blink_partymoney.GetValue()
        setting.blink_partymoney = value

        value = self.pane_ui.cb_show_advancedsettings.GetValue()
        setting.show_advancedsettings = value
        value = self.pane_ui.cb_show_addctrlbtn.GetValue()
        setting.show_addctrlbtn = value
        value = self.pane_ui.cb_show_experiencebar.GetValue()
        setting.show_experiencebar = value
        value = self.pane_ui.cb_cautionbeforesaving.GetValue()
        setting.caution_beforesaving = value
        value = self.pane_ui.cb_show_personal_cards.GetValue()
        if setting.show_personal_cards != value:
            setting.show_personal_cards = value
            setting.last_sendto = 0
            if not value and setting.last_cardpocket == cw.POCKET_PERSONAL:
                setting.last_cardpocket = cw.POCKET_SKILL

            def func_personal() -> None:
                if cw.cwpy.ydata and cw.cwpy.ydata.party:
                    cw.cwpy.ydata.party.sort_backpack()
                if cw.cwpy.areaid in cw.AREAS_TRADE and cw.cwpy.selectedheader:
                    cw.cwpy.show_numberofcards(cw.cwpy.selectedheader.type)
            cw.cwpy.exec_func(func_personal)

        value = self.pane_ui.cb_showbackpackcard.GetValue()
        setting.show_backpackcard = value
        value = self.pane_ui.cb_showbackpackcardatend.GetValue()
        setting.show_backpackcardatend = value
        value = self.pane_ui.cb_can_clicksidesofcardcontrol.GetValue()
        setting.can_clicksidesofcardcontrol = value
        value = self.pane_ui.cb_revertcardpocket.GetValue()
        setting.revert_cardpocket = value
        value = self.pane_ui.ch_confirm_beforesaving.GetSelection()
        if value == 2:
            setting.confirm_beforesaving = cw.setting.CONFIRM_BEFORESAVING_NO
        elif value == 1:
            setting.confirm_beforesaving = cw.setting.CONFIRM_BEFORESAVING_BASE
        else:
            setting.confirm_beforesaving = cw.setting.CONFIRM_BEFORESAVING_YES
        value = self.pane_ui.cb_showsavedmessage.GetValue()
        setting.show_savedmessage = value
        value = self.pane_ui.ch_confirm_dumpcard.GetSelection()
        if value == 2:
            setting.confirm_dumpcard = cw.setting.CONFIRM_DUMPCARD_NO
        elif value == 1:
            setting.confirm_dumpcard = cw.setting.CONFIRM_DUMPCARD_SENDTO
        else:
            setting.confirm_dumpcard = cw.setting.CONFIRM_DUMPCARD_ALWAYS
        value = self.pane_ui.cb_confirmbeforeusingcard.GetValue()
        setting.confirm_beforeusingcard = value
        value = self.pane_ui.cb_noticeimpossibleaction.GetValue()
        setting.noticeimpossibleaction = value
        value = self.pane_ui.cb_showroundautostartbutton.GetValue()
        if setting.show_roundautostartbutton != value:
            setting.show_roundautostartbutton = value
            updatestatusbar = True
            if update and not setting.show_roundautostartbutton:
                def func_autostart() -> None:
                    if cw.cwpy.is_playingscenario():
                        cw.cwpy.sdata.autostart_round = False
                cw.cwpy.exec_func(func_autostart)
        value = self.pane_ui.cb_showautobuttoninentrydialog.GetValue()
        setting.show_autobuttoninentrydialog = value
        value = self.pane_ui.cb_protect_staredcard.GetValue()
        setting.protect_staredcard = value
        value = self.pane_ui.cb_protect_premiercard.GetValue()
        if setting.protect_premiercard != value:
            setting.protect_premiercard = value

            def func_redrawcard() -> None:
                if cw.cwpy.selectedheader:
                    cw.cwpy.remove_pricesprites()
                    cw.data.redraw_cards(cw.cwpy.is_debugmode())
                    cw.cwpy.set_testaptitude(cw.cwpy.selectedheader)
            cw.cwpy.exec_func(func_redrawcard)
        # value = self.pane_ui.cb_spend_noeffectcard.GetValue()
        # setting.spend_noeffectcard = value
        value = self.pane_ui.sc_radius_notdetectmovement.GetValue()
        setting.radius_notdetectmovement = value

        # 背景の更新
        if update and updatebg:
            def func_updatebg() -> None:
                if cw.cwpy.is_playingscenario():
                    cw.cwpy.sdata.resource_cache = {}
                cw.cwpy.background.reload()
            cw.cwpy.exec_func(func_updatebg)

        # イメージの更新
        if update and (updatecardimg or updatemcardimg):
            def func_updateimg() -> None:
                for pcard in cw.cwpy.get_pcards("unreversed"):
                    pcard.update_image()
                if updatemcardimg:
                    for mcard in itertools.chain(cw.cwpy.get_mcards()):
                        if mcard.is_initialized():
                            mcard.update_scale()
                else:
                    for ccard in itertools.chain(cw.cwpy.get_ecards("unreversed"), cw.cwpy.get_fcards("unreversed")):
                        assert isinstance(ccard, (cw.sprite.card.EnemyCard, cw.sprite.card.FriendCard))
                        if ccard.is_initialized():
                            ccard.update_image()
            cw.cwpy.exec_func(func_updateimg)

        # ステータスバーの更新
        if update and updatestatusbar:
            def func_statusbar() -> None:
                cw.cwpy.statusbar.change(cw.cwpy.statusbar.showbuttons)
            cw.cwpy.exec_func(func_statusbar)

        if update:
            debugger = cw.cwpy.is_showingdebugger()
            if debugger:
                debugger.refresh_tools()

        self.GetTopLevelParent().clear_applied()

    def OnClose(self, event: wx.CommandEvent) -> None:
        self.Parent.Close()

    def close(self) -> None:
        cw.cwpy.settingtab = self.note.GetSelection()

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.versioninfo, 0, wx.ALIGN_CENTER, cw.ppis(0))
        sizer_btn.AddStretchSpacer(1)
        sizer_btn.Add(self.btn_dflt, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(5))
        sizer_btn.Add(cw.ppis((10, 0)), 0, 0, cw.ppis(0))
        sizer_btn.Add(self.btn_save, 0, wx.ALIGN_CENTER, cw.ppis(0))
        sizer_btn.Add(self.btn_load, 0, wx.LEFT | wx.ALIGN_CENTER, cw.ppis(2))
        sizer_btn.Add(cw.ppis((10, 0)), 0, 0, cw.ppis(0))
        sizer_btn.Add(self.btn_ok, 0, wx.ALIGN_CENTER, cw.ppis(0))
        sizer_btn.Add(self.btn_apply, 0, wx.LEFT | wx.ALIGN_CENTER, cw.ppis(5))
        sizer_btn.Add(self.btn_cncl, 0, wx.LEFT | wx.ALIGN_CENTER, cw.ppis(5))

        sizer.Add(self.note, 0, wx.EXPAND, cw.ppis(0))
        sizer.Add(sizer_btn, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, cw.ppis(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class SkinPanel(wx.Panel):
    def __init__(self, parent: wx.Panel, editbuttons: bool) -> None:
        """スキンの選択と編集を行う。"""
        wx.Panel.__init__(self, parent)
        self.editbuttons = editbuttons
        self.pane_scenario = None

        # スキン
        self.ch_skin = wx.Choice(self, -1, size=(-1, -1))
        if self.editbuttons:
            self.btn_installskin = wx.Button(self, -1, "...", size=(cw.ppis(25), -1))
            self.btn_installskin.SetToolTip("スキンのインストール...")
        self.tx_skin = wx.TextCtrl(self, -1, size=(-1, -1), style=wx.TE_MULTILINE | wx.NO_BORDER)
        self.tx_skin.SetEditable(False)
        self.tx_skin.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

        if self.editbuttons:
            self.btn_convertskin = wx.Button(self, -1, "自動生成...")
            self.btn_editskin = wx.Button(self, -1, "編集...", size=(cw.ppis(60), -1))
            self.btn_copyskin = wx.Button(self, -1, "コピー", size=(cw.ppis(60), -1))
            self.btn_deleteskin = wx.Button(self, -1, "削除", size=(cw.ppis(60), -1))

            self.cb_show_allskin = wx.CheckBox(self, -1, "異なる種別のスキンを表示する")
            s = "スキンはそれぞれ独自のシステムを持つ場合があるため、異なる種別のスキンに切り替えると、キャラクターの情報がおかしくなったり、シナリオが正常に動かなくなるなどの問題が発生する可能性があります。"
            self.cb_show_allskin.SetToolTip(s)
            if not cw.cwpy.ydata:
                self.cb_show_allskin.SetValue(True)
                self.cb_show_allskin.Enable(False)
        else:
            self.cb_show_allskin = None
            if cw.cwpy.ydata:
                self.ch_skin.SetToolTip("異なる種別のスキンに切り替えたい場合は、タイトル画面に戻るか、詳細設定で「異なる種別のスキンを表示する」にチェックを入れてください。")

        prop = cw.header.GetProperty("Data/SkinBase/Skin.xml")
        self.basecash = int(prop.properties.get("InitialCash", "4000"))
        self.update_skins(cw.cwpy.setting.skindirname)

        self._do_layout()
        self._bind()

    def _bind(self) -> None:
        self.ch_skin.Bind(wx.EVT_CHOICE, self.OnSkinChoice)
        if self.editbuttons:
            self.btn_installskin.Bind(wx.EVT_BUTTON, self.OnInstallSkin)
            self.btn_convertskin.Bind(wx.EVT_BUTTON, self.OnConvertSkin)
            self.btn_editskin.Bind(wx.EVT_BUTTON, self.OnEditSkin)
            self.btn_copyskin.Bind(wx.EVT_BUTTON, self.OnCopySkin)
            self.btn_deleteskin.Bind(wx.EVT_BUTTON, self.OnDeleteSkin)
            self.cb_show_allskin.Bind(wx.EVT_CHECKBOX, self.OnShowAllSkin)

    def update_skins(self, skindirname: str, applied: bool = True) -> None:
        self.ch_skin.Freeze()
        self.skins = []
        self.skindirs = []
        self.skin_summarys: Dict[str, Tuple[str, str, str, str, bool, int]] = {}
        self.all_skintypes = set()

        if not cw.cwpy.ydata or (self.cb_show_allskin and self.cb_show_allskin.GetValue()):
            skintype = ""
        else:
            skintype = cw.cwpy.setting.skintype

        for name in os.listdir("Data/Skin"):
            path = cw.util.join_paths("Data/Skin", name)
            skinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml")

            if os.path.isdir(path) and os.path.isfile(skinpath):
                try:
                    prop = cw.header.GetProperty(skinpath)
                    skintype2 = prop.properties.get("Type", "")
                    self.all_skintypes.add(skintype2)
                    if skintype and skintype2 != skintype:
                        continue
                    if prop.attrs.get(None, {}).get("dataVersion", "0") in cw.SUPPORTED_SKIN:
                        self.skins.append(prop.properties.get("Name", name))
                        self.skindirs.append(name)
                except Exception:
                    # エラーのあるスキンは無視
                    cw.util.print_ex()

        self.ch_skin.SetItems(self.skins)
        if skindirname not in self.skindirs:
            skindirname = cw.cwpy.setting.skindirname
        n = self.skindirs.index(skindirname)
        self.ch_skin.SetSelection(n)
        self._choice_skin(applied=applied)
        self.ch_skin.Thaw()

    def load_allskins(self) -> None:
        for skin in self.skindirs:
            self._load_skinproperties(skin)

    def _load_skinproperties(self, name: str) -> None:
        if name in self.skin_summarys:
            return
        skinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml")
        try:
            prop = cw.header.GetProperty(skinpath)
            skintype = prop.properties.get("Type", "")
            skinname = prop.properties.get("Name", "")
            author = prop.properties.get("Author", "")
            desc = prop.properties.get("Description", "")
            vocation120 = cw.util.str2bool(prop.properties.get("CW120VocationLevel", "False"))
            initialcash = int(prop.properties.get("InitialCash", str(self.basecash)))
            self.skin_summarys[name] = (skintype, skinname, author, desc, vocation120, initialcash)
        except Exception:
            # エラーのあるスキン
            cw.util.print_ex()
            skintype = "*読込エラー*"
            skinname = "*読込エラー*"
            author = ""
            desc = "Skin.xmlの読み込みでエラーが発生しました。"
            vocation120 = False
            initialcash = self.basecash
            self.skin_summarys[name] = (skintype, skinname, author, desc, vocation120, initialcash)

    def OnSkinChoice(self, event: wx.CommandEvent) -> None:
        self._choice_skin()

    def _choice_skin(self, init: bool = False, applied: bool = True) -> None:
        skin = self.skindirs[self.ch_skin.GetSelection()]
        s = "種別: %s\n場所: %s\n作者: %s\n" + "-" * 45 + "\n%s"
        if skin not in self.skin_summarys:
            self._load_skinproperties(skin)
        skintype, _skinname, author, desc, _vocation120, _initialcash = self.skin_summarys[skin]
        desc = cw.util.txtwrap(desc, 1)
        self.tx_skin.SetValue(s % (skintype, cw.util.join_paths("Data/Skin", skin), author, desc))
        if self.editbuttons:
            self.btn_deleteskin.Enable(cw.cwpy.setting.skindirname != skin)
        if not init and applied:
            self.GetTopLevelParent().applied()

    def _get_localsettings(self) -> cw.setting.LocalSetting:
        local = cw.setting.LocalSetting()
        local.init()
        self.GetTopLevelParent().panel.pane_draw.apply_localsettings(local)
        self.GetTopLevelParent().panel.pane_font.apply_localsettings(local)
        return local

    def OnInstallSkin(self, event: wx.CommandEvent) -> None:
        pardlg = self.GetTopLevelParent()
        wildcard = "スキンファイル (*.zip; *.lzh; *.cab; Skin.xml)|*.zip;*.lzh;*.cab;Skin.xml"
        dlg = wx.FileDialog(pardlg, "インストールするスキンを選択", wildcard=wildcard,
                            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            dlg.Destroy()
            pardlg.SetCursor(wx.Cursor(wx.CURSOR_WAIT))

            def validate_path(path: str) -> str:
                if os.path.basename(path) == "Skin.xml":
                    path = os.path.dirname(path)
                d1 = cw.util.get_keypath(cw.util.get_symlinktarget(os.path.dirname(path)))
                d2 = cw.util.get_keypath(cw.util.get_symlinktarget("Data/Skin"))
                if d1 == d2:
                    return ""
                else:
                    return path
            paths = map(validate_path, paths)
            paths = filter(lambda path: path != "", paths)
            installed_skininfos = cw.dialog.skininstall.install_skin(paths, self.GetTopLevelParent(),
                                                                     canswitch=False)
            if installed_skininfos:
                skindirname, _name, _author, skintype, _is_archive = installed_skininfos[0]

                def func(self: SkinPanel) -> None:
                    def func(self: SkinPanel) -> None:
                        if not self:
                            return
                        if skintype != cw.cwpy.setting.skintype and not self.cb_show_allskin.GetValue():
                            self.cb_show_allskin.SetValue(True)
                        self.update_skins(skindirname)
                        if self.pane_scenario:
                            self.pane_scenario.celleditor = None
                    cw.cwpy.frame.exec_func(func, self)
                cw.cwpy.exec_func(func, self)
            pardlg.SetCursor(wx.NullCursor)
        else:
            dlg.Destroy()

    def OnConvertSkin(self, event: wx.CommandEvent) -> None:
        dlg = cw.dialog.skin.SkinConversionDialog(self.TopLevelParent, exe="", from_settings=True,
                                                  get_localsettings=self._get_localsettings)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        if dlg.successful:
            if dlg.conv.skintype != cw.cwpy.setting.skintype and not self.cb_show_allskin.GetValue():
                self.cb_show_allskin.SetValue(True)
            self.update_skins(dlg.skindirname)
            if self.pane_scenario:
                self.pane_scenario.celleditor = None
        dlg.Destroy()

    def OnEditSkin(self, event: wx.CommandEvent) -> None:
        skin = self.skindirs[self.ch_skin.GetSelection()]
        skinsummary = self.skin_summarys[skin]
        dlg = cw.dialog.skin.SkinEditDialog(self.TopLevelParent, skin, skinsummary,
                                            get_localsettings=self._get_localsettings)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.skin_summarys[skin] = dlg.skinsummary
            self.update_skins(skin, applied=False)
            if self.pane_scenario:
                self.pane_scenario.celleditor = None
        dlg.Destroy()

        # スキン編集ダイアログ上でフォント表示例が編集された場合に結果を反映する
        s = cw.cwpy.setting.fontexampleformat
        pixelsize = cw.cwpy.setting.fontexamplepixelsize
        self.GetTopLevelParent().panel.pane_font.tx_example.SetValue(s)
        self.GetTopLevelParent().panel.pane_font.sc_example.SetValue(pixelsize)
        self.GetTopLevelParent().panel.pane_font.update_example()

    def OnCopySkin(self, event: wx.CommandEvent) -> None:
        index = self.ch_skin.GetSelection()
        skin = self.skindirs[index]
        name = self.skins[index]
        s = "スキン「%s(%s)」をコピーしますか？" % (name, skin)
        if wx.MessageBox(s, "メッセージ", wx.OK | wx.CANCEL | wx.ICON_QUESTION, self) == wx.OK:
            src = cw.util.join_paths("Data/Skin", skin)
            dst = cw.util.dupcheck_plus(src, yado=False)
            self.TopLevelParent.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
            shutil.copytree(src, dst)
            fpath = cw.util.join_paths(dst, "Skin.xml")
            data = cw.data.xml2etree(fpath)
            data.edit("Property/Name", name + " - コピー")
            data.write_file()
            self.update_skins(os.path.basename(dst))
            self.TopLevelParent.SetCursor(wx.NullCursor)
            cw.cwpy.play_sound("harvest")

    def OnDeleteSkin(self, event: wx.CommandEvent) -> None:
        index = self.ch_skin.GetSelection()
        skin = self.skindirs[index]
        name = self.skins[index]
        if cw.cwpy.setting.skindirname == skin:
            return
        s = "スキンを削除すると元に戻すことはできません。\n「%s(%s)」を削除しますか？" % (name, skin)
        if wx.MessageBox(s, "メッセージ", wx.OK | wx.CANCEL | wx.ICON_QUESTION, self) == wx.OK:
            dpath = cw.util.join_paths("Data/Skin", skin)
            self.TopLevelParent.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
            cw.util.remove(dpath)
            self.update_skins(cw.cwpy.setting.skindirname)
            self.TopLevelParent.SetCursor(wx.NullCursor)
            if self.pane_scenario:
                self.pane_scenario.celleditor = None
            cw.cwpy.play_sound("dump")

    def OnShowAllSkin(self, event: wx.CommandEvent) -> None:
        skin = self.skindirs[self.ch_skin.GetSelection()]
        self.update_skins(skin, applied=False)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        if self.editbuttons:
            bsizer_skinbtn = wx.BoxSizer(wx.HORIZONTAL)
            bsizer_skinbtn.Add(self.btn_convertskin, 1, wx.RIGHT, cw.ppis(3))
            bsizer_skinbtn.Add(self.btn_editskin, 0, wx.RIGHT, cw.ppis(3))
            bsizer_skinbtn.Add(self.btn_copyskin, 0, wx.RIGHT, cw.ppis(3))
            bsizer_skinbtn.Add(self.btn_deleteskin, 0, 0, cw.ppis(3))

            sizer_h = wx.BoxSizer(wx.HORIZONTAL)
            sizer_h.Add(self.ch_skin, 1, wx.ALIGN_CENTER, cw.ppis(0))
            sizer_h.Add(self.btn_installskin, 0, wx.ALIGN_CENTER | wx.LEFT, cw.ppis(2))
            sizer.Add(sizer_h, 0, wx.CENTER, cw.ppis(0))
        else:
            sizer.Add(self.ch_skin, 0, wx.CENTER, cw.ppis(0))
        sizer.Add(self.tx_skin, 1, wx.CENTER | wx.TOP | wx.EXPAND, cw.ppis(3))
        if self.editbuttons:
            sizer.Add(bsizer_skinbtn, 0, wx.ALIGN_RIGHT | wx.TOP, cw.ppis(3))
            sizer.Add(self.cb_show_allskin, 0, wx.ALIGN_RIGHT | wx.TOP, cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def apply_skin(self, forceupdate: bool) -> bool:
        skinname = self.ch_skin.GetSelection()
        skinname = self.skindirs[skinname]
        if forceupdate or cw.cwpy.setting.skindirname != skinname:
            if self.editbuttons:
                self.btn_deleteskin.Disable()

            def update_skin(skindirname: str, restartop: bool) -> None:
                cw.cwpy.update_skin(skindirname, restartop=restartop, switch_skin=True)
            cw.cwpy.exec_func(cw.cwpy.update_skin, skinname, cw.cwpy.setting.skindirname != skinname)
            return True
        return False

    def copy_values(self, skin: "SkinPanel") -> None:
        if skin.skindirs[skin.ch_skin.GetSelection()] in self.skindirs:
            index = self.skindirs.index(skin.skindirs[skin.ch_skin.GetSelection()])
            self.ch_skin.SetSelection(index)
            self._choice_skin(init=True)


class ExpandPanel(wx.Panel):
    def __init__(self, parent: wx.Panel, options: bool) -> None:
        """拡大表示モードの設定を行う。"""
        wx.Panel.__init__(self, parent)
        self.options = options

        # 拡大表示モード
        self._expand_enable = True
        self.st_expandscr = wx.StaticText(self, -1, "描画倍率:")
        self.st_expandwin = wx.StaticText(self, -1, "表示倍率:")

        self.ch_expanddrawing = wx.ComboBox(self, -1, style=wx.CB_DROPDOWN | wx.CB_READONLY)

        self.sl_expand = wx.Slider(
            self, -1, 10, 10, 11, size=(cw.ppis(120), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.st_expand = wx.StaticText(self, -1)
        dc = wx.ClientDC(self.st_expand)
        s = "9倍 (9999x9999)_"
        self.st_expand.SetMinSize((dc.GetTextExtent(s)[0], -1))

        self.cb_fullscreen = wx.CheckBox(self, -1, "フルスクリーン")

        if self.options:
            self.ln_expand = wx.StaticLine(self, -1, style=wx.HORIZONTAL)
            self.cb_smoothexpand = wx.CheckBox(self, -1,
                                               "拡大後の画面を滑らかにする")

        self._do_layout()
        self._bind()

    def _bind(self) -> None:
        self.sl_expand.Bind(wx.EVT_SLIDER, self.OnExpandChange)
        self.cb_fullscreen.Bind(wx.EVT_CHECKBOX, self.OnExpandChange)

    def load(self, setting: cw.setting.Setting) -> None:
        self.cb_fullscreen.SetValue(setting.expandmode == "FullScreen")
        if self.options:
            self.cb_smoothexpand.SetValue(setting.smoothexpand)

        # 最大倍率を概算
        x, y = cw.cwpy.frame.get_displaysize()
        x = 10 * x // cw.SIZE_SCR[0]
        y = 10 * y // cw.SIZE_SCR[1]
        if setting.expandmode == "FullScreen" or setting.expandmode == "None":
            n = 10  # FullScreen中はスライドを1.0倍に仮設定
        else:
            n = int(10 * float(setting.expandmode))
        nmax = x if x < y else y
        if nmax < 10:
            nmax = 10
        if nmax < n:
            n = nmax

        i = 0
        val = 1
        self.ch_expanddrawing.Clear()
        while True:
            self.ch_expanddrawing.Append("%s倍" % (val))
            if setting.expanddrawing == val:
                self.ch_expanddrawing.Select(i)
            i += 1
            val *= 2
            if nmax < val*10 and 2 < val:
                break
        if nmax <= 10:
            self.sl_expand.SetMax(11)
            self._expand_enable = False
            n = 10
        else:
            self.sl_expand.SetMax(nmax)
            self._expand_enable = True
        self.sl_expand.SetValue(n)
        self.sl_expand.Enable(self._expand_enable)

        if self.ch_expanddrawing.GetSelection() == -1:
            self.ch_expanddrawing.Select(0)

        if nmax < int(2 ** (self.ch_expanddrawing.GetCount()-1)) * 10:
            self.ch_expanddrawing.SetToolTip("画面解像度を超える描画サイズは、環境によっては\n正常に機能しない可能性があります。")
        else:
            self.ch_expanddrawing.SetToolTip("")

        self.make_expandinfo()

    def make_expandinfo(self) -> None:
        if self.cb_fullscreen.IsChecked():
            self.sl_expand.Disable()
            self.st_expand.SetLabel("フルスクリーン")
        else:
            self.sl_expand.Enable(self._expand_enable)
            n = self.sl_expand.GetValue()
            x = cw.SIZE_GAME[0] * n // 10
            y = cw.SIZE_GAME[1] * n // 10
            s = "%d.%d倍 (%dx%d)" % (n//10, n % 10, x, y)
            self.st_expand.SetLabel(s)

    def OnExpandChange(self, event: wx.CommandEvent) -> None:
        self.make_expandinfo()

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        bsizer_expandmode_draw = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_expandmode_draw.Add(self.st_expandscr, 0, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_expandmode_draw.Add(self.ch_expanddrawing, 0, wx.CENTER | wx.RIGHT, cw.ppis(10))
        bsizer_expandmode_draw.Add(self.st_expandwin, 0, wx.CENTER, cw.ppis(0))
        bsizer_expandmode_draw.Add(self.st_expand, 0, wx.CENTER, cw.ppis(0))

        sizer.Add(bsizer_expandmode_draw, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer.Add(self.sl_expand, 0, wx.EXPAND, cw.ppis(3))
        sizer.Add(self.cb_fullscreen, 0, wx.ALIGN_RIGHT, cw.ppis(0))
        if self.options:
            sizer.Add(self.ln_expand, 0, wx.TOP | wx.EXPAND, cw.ppis(3))
            sizer.Add(self.cb_smoothexpand, 0, wx.TOP, cw.ppis(3))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def apply_expand(self, setting: cw.setting.Setting) -> None:
        """拡大設定を反映する。"""
        update = (setting == cw.cwpy.setting)
        if self.options:
            value_b = self.cb_smoothexpand.GetValue()
            setting.smoothexpand = value_b
        if self.cb_fullscreen.IsChecked():
            value: Union[str, float, int] = "FullScreen"
        elif self.sl_expand.GetValue() == 10:  # 1倍 == 拡大なし
            value = "None"
        elif self.sl_expand.GetValue() % 10 == 0:  # 整数倍
            value = self.sl_expand.GetValue() // 10
        else:
            value = float(self.sl_expand.GetValue()) / 10.0
        expanddrawing = int(2 ** self.ch_expanddrawing.GetSelection())
        if str(value) != str(setting.expandmode) or expanddrawing != setting.expanddrawing:
            value_s = str(value)
            if update and cw.cwpy.is_expanded():
                # 設定が変更されたので拡大状態を切り替え
                def func(value_s: str) -> None:
                    cw.cwpy.setting.expandmode = value_s
                    cw.cwpy.setting.expanddrawing = expanddrawing
                    if value_s == "FullScreen":
                        # FIXME: FullScreen以外の拡大設定で拡大しておき、
                        #        設定をFullScreenに変更し、その後F4キーで
                        #        拡大を解除するとウィンドウの操作が効かなくなる
                        cw.cwpy.set_expanded(False, value_s, force=True)
                    else:
                        cw.cwpy.set_expanded(True, value_s, force=True)
                cw.cwpy.exec_func(func, value_s)
            else:
                setting.expandmode = value_s
                setting.expanddrawing = expanddrawing

    def copy_values(self, expand: "ExpandPanel") -> None:
        self.ch_expanddrawing.SetSelection(min(self.ch_expanddrawing.GetCount()-1,
                                               expand.ch_expanddrawing.GetSelection()))
        self.sl_expand.SetValue(expand.sl_expand.GetValue())
        self.cb_fullscreen.SetValue(expand.cb_fullscreen.GetValue())

        self.make_expandinfo()

        if self.options and expand.options:
            self.cb_smoothexpand.SetValue(expand.cb_smoothexpand.GetValue())


class GeneralSettingPanel(wx.Panel):
    def __init__(self, parent: wx.Notebook) -> None:
        wx.Panel.__init__(self, parent)

        # タブレットモード
        self.box_tablet = wx.StaticBox(self, -1, "タブレットモード")
        self.cb_show_tiles = wx.CheckBox(self, -1, "タッチ操作用のタイルを表示する")
        self.cb_enabled_right_flick = wx.CheckBox(self, -1, "右フリックで右クリック相当の操作を行う")
        self.cb_can_repeatlclick = wx.CheckBox(self, -1, "一定時間タッチし続けた時は連打状態にする")

        # デバッグモード
        self.box_gene = wx.StaticBox(self, -1, "詳細")
        self.cb_debug = wx.CheckBox(self, -1, "デバッグモード(Ctrl+Dでも切替可)")
        self.cb_debug.SetValue(cw.cwpy.is_debugmode())
        # self.cb_show_debuglogdialog = wx.CheckBox(
        #     self, -1, "シナリオの終了時にデバッグ情報を表示する")
        self.cb_nolevelup = wx.CheckBox(
            self, -1, "デバッグ中はレベル上昇を抑止する")

        self.st_startupscene = wx.StaticText(self, -1, "起動時の動作:")
        self.ch_startupscene = wx.Choice(self, -1, choices=["タイトル画面を開く", "最後に選択した拠点を開く"])

        self.box_messagelog = wx.StaticBox(self, -1, "メッセージログ(F5キーで表示)")
        self.st_messagelog_type = wx.StaticText(self, -1, "表示形式:")
        self.ch_messagelog_type = wx.Choice(self, -1, choices=["1件ずつ表示", "並べて表示", "高さを圧縮"])
        self.st_backlogmax = wx.StaticText(self, -1, "最大数:")
        self.sc_backlogmax = wx.SpinCtrl(self, -1, size=(cw.ppis(80+_spin_w_addition), -1), max=9999, min=0)

        # スキン
        self.box_skin = wx.StaticBox(self, -1, "スキン",)
        self.skin = SkinPanel(self, True)

        # 拡大表示モード
        self.box_expandmode = wx.StaticBox(self, -1, "拡大表示方式(F4キーで拡大)")
        self.expand = ExpandPanel(self, True)

        # 持出金額
        self.box_party = wx.StaticBox(self, -1, "パーティ")
        self.st_initmoneyamount = wx.StaticText(self, -1, "結成時の持出金額:")
        self.sc_initmoneyamount = wx.SpinCtrl(self, -1, "", size=(cw.ppis(80+_spin_w_addition), -1), min=0, max=999999)
        self.cb_initmoneyisinitialcash = wx.CheckBox(self, -1, "初期資金と同額")

        self.cb_autosavepartyrecord = wx.CheckBox(
            self, -1, "解散時、自動的にパーティ情報を記録する")
        self.cb_overwritepartyrecord = wx.CheckBox(
            self, -1, "自動記録時、同名のパーティ記録へ上書きする")

        # スクリーンショット情報
        self.box_ss = wx.StaticBox(self, -1, "スクリーンショット情報(画像上部に表示)")
        self.tx_ssinfoformat = wx.TextCtrl(self, -1, size=(cw.ppis(150), -1))
        # スクリーンショット情報の色
        choices = ["黒文字", "白文字"]
        self.ch_ssinfocolor = wx.Choice(self, -1, size=(-1, -1), choices=choices)

        # 背景イメージ
        self.st_ssinfobackimage = wx.StaticText(self, -1, "背景画像:")
        self.tx_ssinfobackimage = wx.TextCtrl(self, -1, size=(-1, -1))
        tip = "画像ファイル (*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm)|*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm|全てのファイル (*.*)|*.*"
        self.ref_ssinfobackimage = cw.util.create_fileselection(
            self,
            target=self.tx_ssinfobackimage,
            message="スクリーンショット情報の背景にするファイルを選択",
            wildcard=tip
        )

        # スクリーンショットのファイル名
        self.st_ssfnameformat = wx.StaticText(self, -1, "ファイル名:")
        self.tx_ssfnameformat = wx.TextCtrl(self, -1, size=(cw.ppis(150), -1))
        # 所持カード撮影情報のファイル名
        self.st_cardssfnameformat = wx.StaticText(self, -1, "所持カード:")
        self.tx_cardssfnameformat = wx.TextCtrl(self, -1, size=(cw.ppis(150), -1))

        self.ss_tx = set()
        self.ss_tx.add(self.tx_ssinfoformat)
        self.ss_tx.add(self.tx_ssfnameformat)
        self.ss_tx.add(self.tx_cardssfnameformat)

        self.st_ssinfo_brackets = wx.StaticText(self, -1, "[ ] 内は、各種情報がある場合のみ挿入されます")

        self.sstoolbar = wx.ToolBar(self, -1, style=wx.TB_FLAT | wx.TB_NODIVIDER | wx.TB_HORZ_TEXT | wx.TB_NOICONS)
        self.sstoolbar.SetToolBitmapSize(wx.Size(cw.ppis(0), cw.ppis(0)))
        self.ti_ssins = self.sstoolbar.AddTool(
            -1, "各種情報の挿入", cw.util.empty_bitmap(cw.ppis(0), cw.ppis(0)),
            shortHelp="状況によって動的に変化する情報を挿入します。")
        self.sstoolbar.Realize()

        self.cb_sswithstatusbar = wx.CheckBox(self, -1, "ステータスバーも撮影する")

        ssdic = [
            ("application", "アプリケーション名"),
            ("version", "バージョン情報"),
            None,
            ("skin", "スキン名"),
            ("yado", "拠点名"),
            ("party", "パーティ名"),
            None,
            ("scenario", "シナリオ名"),
            ("author", "作者名"),
            ("path", "シナリオのファイルパス"),
            ("file", "シナリオのファイル名"),
            ("compatibility", "互換モード"),
            None,
            ("date", "日付"),
            ("time", "時刻"),
            ("year", "年"),
            ("month", "月"),
            ("day", "日"),
            ("hour", "時"),
            ("minute", "分"),
            ("second", "秒"),
            ("millisecond", "ミリ秒"),
            None,
            ("\\%", "%"),
            ("\\[", "["),
            ("\\]", "]"),
            ("\\\\", "\\"),
        ]
        if versioninfo:
            ssdic.insert(2, ("build", "ビルド情報"))
        self.ssdic = {}
        self.ssinsmenu = wx.Menu()
        for t in ssdic:
            if t:
                p, name = t
                if p.startswith("\\"):
                    mi = self.ssinsmenu.Append(-1, "%s = %s" % (p, name))
                else:
                    mi = self.ssinsmenu.Append(-1, "%%%s%% = %s" % (p, name))
                self.ssdic[mi.GetId()] = (mi.GetId(), p, name)
            else:
                self.ssinsmenu.AppendSeparator()

        self._ss_focus()

        self._do_layout()
        self._bind()

    def _bind(self) -> None:
        self.cb_autosavepartyrecord.Bind(wx.EVT_CHECKBOX, self.OnAutoSavePartyRecord)
        self.cb_initmoneyisinitialcash.Bind(wx.EVT_CHECKBOX, self.OnInitMoneyIsInitialCash)
        self.sstoolbar.Bind(wx.EVT_TOOL, self.OnSSTool)
        for tx in self.ss_tx:
            tx.Bind(wx.EVT_SET_FOCUS, self.OnSSFocus)
            tx.Bind(wx.EVT_KILL_FOCUS, self.OnSSFocus)

    def load(self, setting: cw.setting.Setting) -> None:
        self.cb_show_tiles.SetValue(setting.show_tiles)
        self.cb_enabled_right_flick.SetValue(setting.enabled_right_flick)
        self.cb_can_repeatlclick.SetValue(setting.can_repeatlclick)
        # self.cb_show_debuglogdialog.SetValue(setting.show_debuglogdialog)
        self.cb_nolevelup.SetValue(setting.no_levelup_in_debugmode)
        if setting.messagelog_type == cw.setting.LOG_SINGLE:
            self.ch_messagelog_type.SetSelection(0)  # 単一表示
        elif setting.messagelog_type == cw.setting.LOG_COMPRESS:
            self.ch_messagelog_type.SetSelection(2)  # 圧縮表示
        else:
            self.ch_messagelog_type.SetSelection(1)  # 並べて表示(デフォルト)
        if setting.startupscene == cw.setting.OPEN_LAST_BASE:
            self.ch_startupscene.SetSelection(1)  # 最後に選択した拠点を開く
        else:
            self.ch_startupscene.SetSelection(0)  # タイトル画面を開く
        self.sc_backlogmax.SetValue(setting.backlogmax)
        self.sc_initmoneyamount.SetValue(setting.initmoneyamount)
        self.cb_initmoneyisinitialcash.SetValue(setting.initmoneyisinitialcash)
        self.sc_initmoneyamount.Enable(not self.cb_initmoneyisinitialcash.GetValue())
        self.cb_autosavepartyrecord.SetValue(setting.autosave_partyrecord)
        self.cb_overwritepartyrecord.SetValue(setting.overwrite_partyrecord)
        self.cb_overwritepartyrecord.Enable(setting.autosave_partyrecord)
        self.tx_ssinfoformat.SetValue(setting.ssinfoformat)
        self.tx_ssfnameformat.SetValue(setting.ssfnameformat)
        self.tx_cardssfnameformat.SetValue(setting.cardssfnameformat)
        if setting.ssinfofontcolor[:3] == (255, 255, 255):
            self.ch_ssinfocolor.Select(1)
        else:
            self.ch_ssinfocolor.Select(0)
        self.tx_ssinfobackimage.SetValue(setting.ssinfobackimage)
        self.cb_sswithstatusbar.SetValue(setting.sswithstatusbar)
        self.expand.load(setting)

    def init_values(self, setting: cw.setting.Setting) -> None:
        self.cb_show_tiles.SetValue(setting.show_tiles_init)
        self.cb_enabled_right_flick.SetValue(setting.enabled_right_flick_init)
        self.cb_can_repeatlclick.SetValue(setting.can_repeatlclick_init)
        # self.cb_show_debuglogdialog.SetValue(setting.show_debuglogdialog_init)

        self.cb_nolevelup.SetValue(setting.no_levelup_in_debugmode_init)
        if setting.messagelog_type_init == cw.setting.LOG_SINGLE:
            self.ch_messagelog_type.SetSelection(0)
        elif setting.messagelog_type_init == cw.setting.LOG_LIST:
            self.ch_messagelog_type.SetSelection(1)
        elif setting.messagelog_type_init == cw.setting.LOG_COMPRESS:
            self.ch_messagelog_type.SetSelection(2)
        if setting.startupscene_init == cw.setting.OPEN_TITLE:
            self.ch_startupscene.SetSelection(0)
        elif setting.startupscene_init == cw.setting.OPEN_LAST_BASE:
            self.ch_startupscene.SetSelection(1)
        self.sc_backlogmax.SetValue(setting.backlogmax_init)
        self.expand.ch_expanddrawing.SetSelection(0)
        if setting.expandmode_init == "FullScreen":
            self.expand.cb_fullscreen.SetValue(True)
        else:
            self.expand.ch_expanddrawing.SetSelection(int(setting.expandmode_init) - 1)
            self.expand.cb_fullscreen.SetValue(False)
        self.expand.make_expandinfo()
        self.expand.cb_smoothexpand.SetValue(setting.smoothexpand_init)
        self.sc_initmoneyamount.SetValue(setting.initmoneyamount_init)
        self.cb_initmoneyisinitialcash.SetValue(setting.initmoneyisinitialcash_init)
        self.sc_initmoneyamount.Enable(not self.cb_initmoneyisinitialcash.GetValue())
        self.cb_autosavepartyrecord.SetValue(setting.autosave_partyrecord_init)
        self.cb_overwritepartyrecord.SetValue(setting.overwrite_partyrecord_init)
        self.cb_overwritepartyrecord.Enable(self.cb_autosavepartyrecord.GetValue())
        self.tx_ssinfoformat.SetValue(setting.ssinfoformat_init)
        self.tx_ssfnameformat.SetValue(setting.ssfnameformat_init)
        self.tx_cardssfnameformat.SetValue(setting.cardssfnameformat_init)
        self.ch_ssinfocolor.Select(1 if setting.ssinfofontcolor_init == (255, 255, 255) else 0)
        self.tx_ssinfobackimage.SetValue(setting.ssinfobackimage_init)
        self.cb_sswithstatusbar.SetValue(setting.sswithstatusbar_init)

    def OnSSTool(self, event: wx.CommandEvent) -> None:
        if self.ti_ssins.GetId() == event.GetId():
            self.sstoolbar.PopupMenu(self.ssinsmenu)
        else:
            t = self.ssdic.get(event.GetId(), None)
            if not t:
                return
            p = t[1]
            f = wx.Window.FindFocus()
            for tx in self.ss_tx:
                if tx is f:
                    if p.startswith("\\"):
                        tx.WriteText("%s" % (p))
                    else:
                        tx.WriteText("%%%s%%" % (p))

    def OnSSFocus(self, event: wx.FocusEvent) -> None:
        self._ss_focus()
        event.Skip()

    def _ss_focus(self) -> None:
        enable = wx.Window.FindFocus() in self.ss_tx
        self.sstoolbar.Enable(enable)

    def OnAutoSavePartyRecord(self, event: wx.CommandEvent) -> None:
        self.cb_overwritepartyrecord.Enable(self.cb_autosavepartyrecord.GetValue())

    def OnInitMoneyIsInitialCash(self, event: wx.CommandEvent) -> None:
        self.sc_initmoneyamount.Enable(not self.cb_initmoneyisinitialcash.GetValue())

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_tablet = wx.StaticBoxSizer(self.box_tablet, wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_skin = wx.StaticBoxSizer(self.box_skin, wx.VERTICAL)
        bsizer_expandmode = wx.StaticBoxSizer(self.box_expandmode, wx.VERTICAL)

        bsizer_tablet.Add(self.cb_show_tiles, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_tablet.Add(self.cb_enabled_right_flick, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_tablet.Add(self.cb_can_repeatlclick, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))

        bsizer_gene.Add(self.cb_debug, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        # bsizer_gene.Add(self.cb_show_debuglogdialog, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_nolevelup, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))

        bsizer_startup = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_startup.Add(self.st_startupscene, 0, wx.ALIGN_CENTER, cw.ppis(0))
        bsizer_startup.Add(self.ch_startupscene, 0, wx.LEFT | wx.ALIGN_CENTER, cw.ppis(3))
        bsizer_gene.Add(bsizer_startup, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))

        bsizer_gene.SetMinSize((_settings_width(), -1))

        bsizer_log = wx.StaticBoxSizer(self.box_messagelog, wx.HORIZONTAL)
        bsizer_log.Add(self.st_messagelog_type, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(3))
        bsizer_log.Add(self.ch_messagelog_type, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(5))
        bsizer_log.Add(self.st_backlogmax, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(3))
        bsizer_log.Add(self.sc_backlogmax, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER, cw.ppis(5))
        bsizer_log.SetMinSize((_settings_width(), -1))

        bsizer_skin.Add(self.skin, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skin.SetMinSize((_settings_width(), cw.ppis(180)))

        bsizer_expandmode.Add(self.expand, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        bsizer_expandmode.SetMinSize((_settings_width(), -1))

        bsizer_party = wx.StaticBoxSizer(self.box_party, wx.VERTICAL)
        bsizer_partymoney = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_partymoney.Add(self.st_initmoneyamount, 0, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_partymoney.Add(self.sc_initmoneyamount, 0, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_partymoney.Add(self.cb_initmoneyisinitialcash, 0, wx.CENTER, cw.ppis(3))
        bsizer_party.Add(bsizer_partymoney, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_party.Add(self.cb_autosavepartyrecord, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_party.Add(self.cb_overwritepartyrecord, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))

        bsizer_ss = wx.StaticBoxSizer(self.box_ss, wx.VERTICAL)
        bsizer_ssl = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_ssl.Add(self.tx_ssinfoformat, 1, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_ssl.Add(self.ch_ssinfocolor, 0, wx.CENTER, cw.ppis(3))
        bsizer_ss.Add(bsizer_ssl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(2))

        ssinfobackimage_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ssinfobackimage_sizer.Add(self.tx_ssinfobackimage, 1, wx.RIGHT | wx.CENTER, cw.ppis(3))
        ssinfobackimage_sizer.Add(self.ref_ssinfobackimage, 0, wx.CENTER, cw.ppis(0))

        gsizer_fname = wx.GridBagSizer()
        gsizer_fname.Add(self.st_ssinfobackimage, pos=(0, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                         border=cw.ppis(3))
        gsizer_fname.Add(ssinfobackimage_sizer, pos=(0, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND,
                         border=cw.ppis(3))
        gsizer_fname.Add((0, cw.ppis(3)), pos=(1, 0))
        gsizer_fname.Add(self.st_ssfnameformat, pos=(2, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                         border=cw.ppis(3))
        gsizer_fname.Add(self.tx_ssfnameformat, pos=(2, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND,
                         border=cw.ppis(3))
        gsizer_fname.Add(self.st_cardssfnameformat, pos=(3, 0), flag=wx.TOP | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                         border=cw.ppis(3))
        gsizer_fname.Add(self.tx_cardssfnameformat, pos=(3, 1), flag=wx.TOP | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND,
                         border=cw.ppis(3))
        gsizer_fname.AddGrowableCol(1, 3)

        bsizer_ss.Add(gsizer_fname, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(2)-1)
        bsizer_ss.Add(self.st_ssinfo_brackets, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, cw.ppis(3))
        bsizer_ssbtm = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_ssbtm.Add(self.cb_sswithstatusbar, 0, wx.CENTER, 0)
        bsizer_ssbtm.Add(cw.ppis((3, 0)), 1, 0, 0)
        bsizer_ssbtm.Add(self.sstoolbar, 0, wx.CENTER, 0)
        bsizer_ss.Add(bsizer_ssbtm, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        sizer_left.Add(bsizer_tablet, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_gene, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_log, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_skin, 1, wx.EXPAND, cw.ppis(3))

        sizer_right.Add(bsizer_expandmode, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_party, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_ss, 0, wx.EXPAND, cw.ppis(0))

        sizer_h1.Add(sizer_left, 0, wx.RIGHT | wx.EXPAND, cw.ppis(5))
        sizer_h1.Add(sizer_right, 1, wx.EXPAND, cw.ppis(3))

        sizer.Add(sizer_h1, 1, wx.ALL | wx.EXPAND, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class SpeedPanel(wx.Panel):
    def __init__(self, parent: wx.Panel, battlespeed: bool) -> None:
        """背景切替方式と各種速度を設定する。"""
        wx.Panel.__init__(self, parent)
        self.battlespeed = battlespeed

        # トランジション効果
        self.box_tran = wx.StaticBox(
            self, -1, "背景の切り替え方式(速い⇔遅い)")
        self.transitions = [
            "None", "Blinds", "PixelDissolve", "Fade"]
        self.choices_tran = [
            "アニメーションなし", "短冊(スレッド)式", "ドット置換(シェーブ)式",
            "色置換(フェード)式"]
        self.ch_tran = wx.Choice(
            self, -1, size=(-1, -1), choices=self.choices_tran)
        self.sl_tran = wx.Slider(
            self, -1, 0, 0, 10,
            size=(_settings_width()-cw.ppis(10), -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.sl_tran.SetTickFreq(1)
        # カード描画速度
        self.box_deal = wx.StaticBox(
            self, -1, "カード描画速度(速い⇔遅い)")
        self.sl_deal = wx.Slider(
            self, -1, 0, 0, 10, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.sl_deal.SetTickFreq(1)
        if self.battlespeed:
            # 戦闘行動描画速度
            self.box_deal_battle = wx.StaticBox(
                self, -1, "戦闘行動描画速度(速い⇔遅い)")
            self.sl_deal_battle = wx.Slider(
                self, -1, 0, 0, 10, size=(_settings_width()-cw.ppis(10), -1),
                style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
            self.sl_deal_battle.SetTickFreq(1)
            self.cb_use_battlespeed = wx.CheckBox(
                self, -1, "カード描画速度に合わせる")
        # メッセージ表示速度
        self.box_msgs = wx.StaticBox(
            self, -1, "メッセージ表示速度(速い⇔遅い)")
        self.sl_msgs = wx.Slider(
            self, -1, 0, 0, 10, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
        self.sl_msgs.SetTickFreq(1)

        self._do_layout()
        self._bind()

    def load(self, setting: cw.setting.Setting) -> None:
        n = self.transitions.index(setting.transition)
        self.ch_tran.SetSelection(n)
        self.sl_tran.SetValue(setting.transitionspeed)
        self.sl_deal.SetValue(setting.dealspeed)
        if self.battlespeed:
            self.sl_deal_battle.SetValue(setting.dealspeed_battle)
            self.cb_use_battlespeed.SetValue(not setting.use_battlespeed)
            self.sl_deal_battle.Enable(setting.use_battlespeed)
        self.sl_msgs.SetValue(setting.messagespeed)

    def _bind(self) -> None:
        if self.battlespeed:
            self.cb_use_battlespeed.Bind(wx.EVT_CHECKBOX, self.OnUseBattleSpeed, id=self.cb_use_battlespeed.GetId())

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        bsizer_tran = wx.StaticBoxSizer(self.box_tran, wx.VERTICAL)
        bsizer_deal = wx.StaticBoxSizer(self.box_deal, wx.VERTICAL)
        if self.battlespeed:
            bsizer_deal_battle = wx.StaticBoxSizer(self.box_deal_battle, wx.VERTICAL)
        bsizer_msgs = wx.StaticBoxSizer(self.box_msgs, wx.VERTICAL)

        bsizer_tran.Add(self.ch_tran, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_tran.Add(self.sl_tran, 0, wx.EXPAND, cw.ppis(0))
        bsizer_deal.Add(self.sl_deal, 0, wx.EXPAND, cw.ppis(0))
        if self.battlespeed:
            bsizer_deal_battle.Add(self.sl_deal_battle, 0, wx.EXPAND, cw.ppis(0))
            bsizer_deal_battle.Add(self.cb_use_battlespeed, 0, wx.ALIGN_RIGHT, cw.ppis(0))
        bsizer_msgs.Add(self.sl_msgs, 0, wx.EXPAND, cw.ppis(0))

        sizer.Add(bsizer_tran, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer.Add(bsizer_deal, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        if self.battlespeed:
            sizer.Add(bsizer_deal_battle, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer.Add(bsizer_msgs, 0, wx.EXPAND, cw.ppis(3))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnUseBattleSpeed(self, event: wx.CommandEvent) -> None:
        self.sl_deal_battle.Enable(not self.cb_use_battlespeed.GetValue())

    def apply_speed(self, setting: cw.setting.Setting) -> bool:
        updatemessage = False
        dealspeed = self.sl_deal.GetValue()
        if self.battlespeed:
            dealspeed_battle = self.sl_deal_battle.GetValue()
            use_battlespeed = not self.cb_use_battlespeed.GetValue()
            setting.set_dealspeed(dealspeed, dealspeed_battle, use_battlespeed)
        else:
            setting.set_dealspeed(dealspeed, setting.dealspeed_battle, setting.use_battlespeed)
        value = self.sl_msgs.GetValue()
        if setting.messagespeed != value:
            setting.messagespeed = value
            updatemessage = True
        value = self.ch_tran.GetSelection()
        value = self.transitions[value]
        setting.transition = value
        value = self.sl_tran.GetValue()
        setting.transitionspeed = value
        return updatemessage

    def copy_values(self, speed: "SpeedPanel") -> None:
        self.ch_tran.SetSelection(speed.ch_tran.GetSelection())
        self.sl_tran.SetValue(speed.sl_tran.GetValue())
        self.sl_deal.SetValue(speed.sl_deal.GetValue())
        if self.battlespeed and speed.battlespeed:
            self.sl_deal_battle.SetValue(speed.sl_deal_battle.GetValue())
            self.cb_use_battlespeed.SetValue(speed.cb_use_battlespeed.GetValue())
            self.sl_deal_battle.Enable(speed.sl_deal_battle.IsEnabled())
        self.sl_msgs.SetValue(speed.sl_msgs.GetValue())


class DrawingSettingPanel(wx.Panel):
    def __init__(self, parent: wx.Notebook, for_local: bool,
                 get_localsettings: Optional[Callable[[], cw.setting.LocalSetting]],
                 use_copybase: bool) -> None:
        wx.Panel.__init__(self, parent)
        self._for_local = for_local
        self._get_localsettings = get_localsettings

        if self._for_local:
            self.cb_important = wx.CheckBox(self, -1, "このスキンの描画設定を基本設定よりも優先して使用する")
        else:
            self.cb_important = None
            self.box_gene = wx.StaticBox(self, -1, "詳細")
            self.cb_smoothing_card_up = wx.CheckBox(self, -1, "拡大したカード画像を滑らかにする")
            self.cb_smoothing_card_down = wx.CheckBox(self, -1, "縮小したカード画像を滑らかにする")
            self.cb_smooth_bg = wx.CheckBox(self, -1, "拡大・縮小した背景画像を滑らかにする")
            self.cb_whitecursor = wx.CheckBox(self, -1, "メイン画面で白いカーソルを使用する")

            # 背景切替方式と各種速度
            self.speed = SpeedPanel(self, True)

        # メッセージウィンドウ背景色
        self.box_mwin = wx.StaticBox(self, -1, "メッセージウィンドウ背景")
        self.st_mwin = wx.StaticText(self, -1, "カラー")
        self.cs_mwin = wx.ColourPickerCtrl(self, -1)
        self.st_blwin = wx.StaticText(self, -1, "ログ")
        self.cs_blwin = wx.ColourPickerCtrl(self, -1)
        self.st_mwin2 = wx.StaticText(self, -1, "アルファ値")
        self.sc_mwin = wx.SpinCtrl(self, -1, "", size=(cw.ppis(50+_spin_w_addition), -1))
        self.sc_mwin.SetRange(0, 255)
        # メッセージウィンドウ枠色
        self.box_mframe = wx.StaticBox(self, -1, "メッセージウィンドウ枠")
        self.st_mframe = wx.StaticText(self, -1, "カラー")
        self.cs_mframe = wx.ColourPickerCtrl(self, -1)
        self.st_blframe = wx.StaticText(self, -1, "ログ")
        self.cs_blframe = wx.ColourPickerCtrl(self, -1)
        self.st_mframe2 = wx.StaticText(self, -1, "アルファ値")
        self.sc_mframe = wx.SpinCtrl(self, -1, "", size=(cw.ppis(50+_spin_w_addition), -1))
        self.sc_mframe.SetRange(0, 255)

        # メッセージログカーテン色
        self.box_blcurtain = wx.StaticBox(self, -1, "メッセージログの背景")
        self.st_blcurtain = wx.StaticText(self, -1, "カラー")
        self.cs_blcurtain = wx.ColourPickerCtrl(self, -1)
        self.st_blcurtain2 = wx.StaticText(self, -1, "アルファ値")
        self.sc_blcurtain = wx.SpinCtrl(self, -1, "", size=(cw.ppis(50+_spin_w_addition), -1))
        self.sc_blcurtain.SetRange(0, 255)

        # カーテン色
        self.box_curtain = wx.StaticBox(self, -1, "カーテン(選択モードの背景効果)")
        self.st_curtain = wx.StaticText(self, -1, "カラー")
        self.cs_curtain = wx.ColourPickerCtrl(self, -1)
        self.st_curtain2 = wx.StaticText(self, -1, "アルファ値")
        self.sc_curtain = wx.SpinCtrl(self, -1, "", size=(cw.ppis(50+_spin_w_addition), -1))
        self.sc_curtain.SetRange(0, 255)

        # フルスクリーンの背景
        self.box_fscrback = wx.StaticBox(self, -1, "フルスクリーンの背景")
        choices = ["<背景なし>", "<ファイルから選択>", "ダイアログの壁紙", "スキンのロゴ"]
        self.ch_fscrbacktype = wx.Choice(self, -1, size=(-1, -1), choices=choices)
        self.tx_fscrbackfile = wx.TextCtrl(self, -1, size=(cw.ppis(150), -1))
        tip = "画像ファイル (*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm)|*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm|全てのファイル (*.*)|*.*"
        self.ref_fscrbackfile = cw.util.create_fileselection(
            self,
            target=self.tx_fscrbackfile,
            message="フルスクリーンの背景にするファイルを選択",
            wildcard=tip
        )

        if self._for_local:
            if use_copybase:
                self.copybtn = wx.Button(self, -1, "基本設定をコピー")
            else:
                self.copybtn = None
            self.initbtn = wx.Button(self, -1, "デフォルト")

        self._do_layout()
        self._bind()

    def load(self, setting: Optional[cw.setting.Setting], local: cw.setting.LocalSetting) -> None:
        if self._for_local:
            self.cb_important.SetValue(local.important_draw)
        else:
            assert setting
            self.cb_smooth_bg.SetValue(setting.smoothscale_bg)
            self.cb_smoothing_card_up.SetValue(setting.smoothing_card_up)
            self.cb_smoothing_card_down.SetValue(setting.smoothing_card_down)
            self.cb_whitecursor.SetValue(setting.cursor_type == cw.setting.CURSOR_WHITE)

            self.speed.load(setting)

        self.cs_mwin.SetColour(local.mwincolour)
        self.cs_blwin.SetColour(local.blwincolour)
        self.sc_mwin.SetValue(local.mwincolour[3])
        self.cs_mframe.SetColour(local.mwinframecolour)
        self.cs_blframe.SetColour(local.blwinframecolour)
        self.sc_mframe.SetValue(local.mwinframecolour[3])
        self.cs_blcurtain.SetColour(local.blcurtaincolour)
        self.sc_blcurtain.SetValue(local.blcurtaincolour[3])
        self.cs_curtain.SetColour(local.curtaincolour)
        self.sc_curtain.SetValue(local.curtaincolour[3])

        if local.fullscreenbackgroundtype == 0:
            self.ch_fscrbacktype.SetSelection(0)
            self.tx_fscrbackfile.SetValue("")
        elif local.fullscreenbackgroundtype == 1:
            self.ch_fscrbacktype.SetSelection(1)
            self.tx_fscrbackfile.SetValue(local.fullscreenbackgroundfile)
        elif local.fullscreenbackgroundtype == 2:
            if local.fullscreenbackgroundfile == "Resource/Image/Dialog/CAUTION":
                self.ch_fscrbacktype.SetSelection(2)
                self.tx_fscrbackfile.SetValue("")
            elif local.fullscreenbackgroundfile == "Resource/Image/Dialog/PAD":
                self.ch_fscrbacktype.SetSelection(3)
                self.tx_fscrbackfile.SetValue("")
            else:
                self.ch_fscrbacktype.SetSelection(0)
                self.tx_fscrbackfile.SetValue("")

        self._update_enabled()

    def init_values(self, setting: Optional[cw.setting.Setting], local: cw.setting.LocalSetting) -> None:
        if not self._for_local:
            assert setting
            self.cb_smoothing_card_up.SetValue(setting.smoothing_card_up_init)
            self.cb_smoothing_card_down.SetValue(setting.smoothing_card_down_init)
            self.cb_smooth_bg.SetValue(setting.smoothscale_bg_init)
            self.cb_whitecursor.SetValue(setting.cursor_type_init == cw.setting.CURSOR_WHITE)
            self.speed.sl_deal.SetValue(setting.dealspeed_init)
            self.speed.sl_deal_battle.SetValue(setting.dealspeed_battle_init)
            self.speed.cb_use_battlespeed.SetValue(not setting.use_battlespeed_init)
            self.speed.sl_deal_battle.Enable(setting.use_battlespeed_init)
            self.speed.sl_msgs.SetValue(setting.messagespeed_init)
            self.speed.ch_tran.SetSelection(self.speed.transitions.index(setting.transition_init))
            self.speed.sl_tran.SetValue(setting.transitionspeed_init)
        self.sc_mwin.SetValue(local.mwincolour_init[3])
        self.cs_mwin.SetColour(local.mwincolour_init[:3])
        self.sc_mframe.SetValue(local.mwinframecolour_init[3])
        self.cs_mframe.SetColour(local.mwinframecolour_init[:3])
        self.cs_blwin.SetColour(local.blwincolour_init[:3])
        self.cs_blframe.SetColour(local.blwinframecolour_init[:3])
        self.sc_blcurtain.SetValue(local.blcurtaincolour_init[3])
        self.cs_blcurtain.SetColour(local.blcurtaincolour_init[:3])
        self.sc_curtain.SetValue(local.curtaincolour_init[3])
        self.cs_curtain.SetColour(local.curtaincolour_init[:3])

        if local.fullscreenbackgroundtype_init == 2:
            self.tx_fscrbackfile.SetValue("")
            if local.fullscreenbackgroundfile_init == "Resource/Image/Dialog/CAUTION":
                self.ch_fscrbacktype.Select(2)
            else:
                self.ch_fscrbacktype.Select(3)
        elif local.fullscreenbackgroundtype_init == 1:
            self.tx_fscrbackfile.SetValue(local.fullscreenbackgroundfile_init)
            self.ch_fscrbacktype.Select(1)
        else:
            self.tx_fscrbackfile.SetValue("")
            self.ch_fscrbacktype.Select(0)
        self.tx_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)
        self.ref_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)

    def apply_localsettings(self, local: cw.setting.LocalSetting) -> Tuple[bool, bool, bool]:
        updatemessage = False
        alpha = self.sc_mwin.GetValue()
        colour = self.cs_mwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= local.mwincolour != colour
        local.mwincolour = colour
        alpha = self.sc_mframe.GetValue()
        colour = self.cs_mframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= local.mwinframecolour != colour
        local.mwinframecolour = colour
        # 配色(バックログ)
        alpha = self.sc_mwin.GetValue()
        colour = self.cs_blwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= local.blwincolour != colour
        local.blwincolour = colour
        alpha = self.sc_mframe.GetValue()
        colour = self.cs_blframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= local.blwinframecolour != colour
        local.blwinframecolour = colour

        updatecurtain = False
        # 配色(メッセージログカーテン)
        alpha = self.sc_blcurtain.GetValue()
        colour = self.cs_blcurtain.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatecurtain |= local.blcurtaincolour != colour
        local.blcurtaincolour = colour
        # 配色(選択モードカーテン)
        alpha = self.sc_curtain.GetValue()
        colour = self.cs_curtain.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatecurtain |= local.curtaincolour != colour
        local.curtaincolour = colour

        # フルスクリーンの背景
        value = self.ch_fscrbacktype.GetSelection()
        fullscreenbackgroundfile = local.fullscreenbackgroundfile
        fullscreenbackgroundtype = local.fullscreenbackgroundtype
        if value == 0:
            fullscreenbackgroundfile = ""
            fullscreenbackgroundtype = 0
        elif value == 1:
            fullscreenbackgroundfile = self.tx_fscrbackfile.GetValue()
            fullscreenbackgroundtype = 1
        elif value == 2:
            fullscreenbackgroundfile = "Resource/Image/Dialog/CAUTION"
            fullscreenbackgroundtype = 2
        elif value == 3:
            fullscreenbackgroundfile = "Resource/Image/Dialog/PAD"
            fullscreenbackgroundtype = 2

        updatefullscreen = (fullscreenbackgroundfile != local.fullscreenbackgroundfile) or\
                           (fullscreenbackgroundtype != local.fullscreenbackgroundtype)

        local.fullscreenbackgroundfile = fullscreenbackgroundfile
        local.fullscreenbackgroundtype = fullscreenbackgroundtype

        if self.cb_important and self.cb_important.GetValue() != local.important_draw:
            local.important_draw = self.cb_important.GetValue()
            updatemessage = True
            updatecurtain = True
            updatefullscreen = True

        return updatemessage, updatecurtain, updatefullscreen

    def _bind(self) -> None:
        self.ch_fscrbacktype.Bind(wx.EVT_CHOICE, self.OnFullScreenBackgroundType, id=self.ch_fscrbacktype.GetId())
        if self._for_local:
            self.cb_important.Bind(wx.EVT_CHECKBOX, self.OnImportant)
            if self.copybtn:
                self.copybtn.Bind(wx.EVT_BUTTON, self.OnCopyBase)
            self.initbtn.Bind(wx.EVT_BUTTON, self.OnInitValue)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        if not self._for_local:
            sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        if not self._for_local:
            bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)

            bsizer_gene.Add(self.cb_smoothing_card_up, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
            bsizer_gene.Add(self.cb_smoothing_card_down, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
            bsizer_gene.Add(self.cb_smooth_bg, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
            bsizer_gene.Add(self.cb_whitecursor, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
            bsizer_gene.SetMinSize((_settings_width(), -1))

        bsizer_mwin = wx.BoxSizer(wx.HORIZONTAL)
        if self._for_local:
            bsizer_mwin.Add(self.st_mwin, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
            bsizer_mwin.Add(self.cs_mwin, 0, wx.CENTER | wx.RIGHT, cw.ppis(5))
            bsizer_mwin.Add(self.st_blwin, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
            bsizer_mwin.Add(self.cs_blwin, 0, wx.CENTER, cw.ppis(0))
        else:
            gsizer_mwin = wx.GridBagSizer()
            gsizer_mwin.Add(self.st_mwin, pos=(0, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))
            gsizer_mwin.Add(self.cs_mwin, pos=(0, 1), flag=wx.EXPAND)
            gsizer_mwin.Add(self.st_blwin, pos=(1, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))
            gsizer_mwin.Add(self.cs_blwin, pos=(1, 1), flag=wx.EXPAND)
            bsizer_mwin.Add(gsizer_mwin, 0, wx.CENTER, cw.ppis(0))
        bsizer_mwin.Add(self.st_mwin2, 0, wx.CENTER | wx.LEFT, cw.ppis(5))
        bsizer_mwin.Add(self.sc_mwin, 0, wx.CENTER | wx.LEFT, cw.ppis(3))
        bsizer_mwin2 = wx.StaticBoxSizer(self.box_mwin, wx.HORIZONTAL)
        bsizer_mwin2.Add(bsizer_mwin, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, cw.ppis(3))

        bsizer_mframe = wx.BoxSizer(wx.HORIZONTAL)
        if self._for_local:
            bsizer_mframe.Add(self.st_mframe, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
            bsizer_mframe.Add(self.cs_mframe, 0, wx.CENTER | wx.RIGHT, cw.ppis(5))
            bsizer_mframe.Add(self.st_blframe, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
            bsizer_mframe.Add(self.cs_blframe, 0, wx.CENTER, cw.ppis(0))
        else:
            gsizer_mframe = wx.GridBagSizer()
            gsizer_mframe.Add(self.st_mframe, pos=(0, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))
            gsizer_mframe.Add(self.cs_mframe, pos=(0, 1), flag=wx.EXPAND)
            gsizer_mframe.Add(self.st_blframe, pos=(1, 0), flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(3))
            gsizer_mframe.Add(self.cs_blframe, pos=(1, 1), flag=wx.EXPAND)
            bsizer_mframe.Add(gsizer_mframe, 0, wx.CENTER, cw.ppis(0))
        bsizer_mframe.Add(self.st_mframe2, 0, wx.CENTER | wx.LEFT, cw.ppis(5))
        bsizer_mframe.Add(self.sc_mframe, 0, wx.CENTER | wx.LEFT, cw.ppis(3))
        bsizer_mframe2 = wx.StaticBoxSizer(self.box_mframe, wx.HORIZONTAL)
        bsizer_mframe2.Add(bsizer_mframe, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, cw.ppis(3))

        bsizer_blcurtain = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_blcurtain.Add(self.st_blcurtain, 0, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_blcurtain.Add(self.cs_blcurtain, 0, wx.RIGHT | wx.EXPAND, cw.ppis(5))
        bsizer_blcurtain.Add(self.st_blcurtain2, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_blcurtain.Add(self.sc_blcurtain, 0, wx.CENTER, cw.ppis(0))
        bsizer_blcurtain2 = wx.StaticBoxSizer(self.box_blcurtain, wx.HORIZONTAL)
        bsizer_blcurtain2.Add(bsizer_blcurtain, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, cw.ppis(3))

        bsizer_curtain = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_curtain.Add(self.st_curtain, 0, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_curtain.Add(self.cs_curtain, 0, wx.RIGHT | wx.EXPAND, cw.ppis(5))
        bsizer_curtain.Add(self.st_curtain2, 0, wx.CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_curtain.Add(self.sc_curtain, 0, wx.CENTER, cw.ppis(0))
        bsizer_curtain2 = wx.StaticBoxSizer(self.box_curtain, wx.HORIZONTAL)
        bsizer_curtain2.Add(bsizer_curtain, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, cw.ppis(3))

        bsizer_fscrback = wx.StaticBoxSizer(self.box_fscrback, wx.VERTICAL)
        bsizer_fscrback.Add(self.ch_fscrbacktype, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_fscrbackfile = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_fscrbackfile.Add(self.tx_fscrbackfile, 1, wx.RIGHT | wx.CENTER, cw.ppis(3))
        bsizer_fscrbackfile.Add(self.ref_fscrbackfile, 0, wx.CENTER, cw.ppis(3))
        bsizer_fscrback.Add(bsizer_fscrbackfile, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        if self._for_local:
            sizer_right.Add(self.cb_important, 0, wx.BOTTOM, cw.ppis(5))
        else:
            sizer_left.Add(bsizer_gene, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
            sizer_left.Add(self.speed, 0, wx.EXPAND, cw.ppis(3))

        sizer_right.Add(bsizer_mwin2, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_mframe2, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_blcurtain2, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_curtain2, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_right.Add(bsizer_fscrback, 0, wx.EXPAND, cw.ppis(3))

        if self._for_local:
            sizer_right.AddStretchSpacer(1)
            bsizer_btn = wx.BoxSizer(wx.HORIZONTAL)
            if self.copybtn:
                bsizer_btn.Add(self.copybtn, 0, wx.RIGHT, cw.ppis(3))
            bsizer_btn.Add(self.initbtn, 0, 0, cw.ppis(0))
            sizer_right.Add(bsizer_btn, 0, wx.ALIGN_RIGHT | wx.TOP, cw.ppis(5))

        if self._for_local:
            sizer_h1.Add(sizer_right, 1, wx.EXPAND, cw.ppis(3))
        else:
            sizer_h1.Add(sizer_left, 1, wx.RIGHT | wx.EXPAND, cw.ppis(5))
            sizer_h1.Add(sizer_right, 0, wx.EXPAND, cw.ppis(3))

        sizer.Add(sizer_h1, 1, wx.ALL | wx.EXPAND, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnFullScreenBackgroundType(self, event: wx.CommandEvent) -> None:
        self.tx_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)
        self.ref_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)

    def OnImportant(self, event: wx.CommandEvent) -> None:
        self._update_enabled()

    def _update_enabled(self) -> None:
        enbl = self.cb_important.GetValue() if self.cb_important else True
        self.cs_mwin.Enable(enbl)
        self.cs_blwin.Enable(enbl)
        self.sc_mwin.Enable(enbl)
        self.cs_mframe.Enable(enbl)
        self.cs_blframe.Enable(enbl)
        self.sc_mframe.Enable(enbl)
        self.cs_curtain.Enable(enbl)
        self.sc_curtain.Enable(enbl)
        self.cs_blcurtain.Enable(enbl)
        self.sc_blcurtain.Enable(enbl)
        self.ch_fscrbacktype.Enable(enbl)
        self.tx_fscrbackfile.Enable(enbl and self.ch_fscrbacktype.GetSelection() == 1)
        self.ref_fscrbackfile.Enable(enbl and self.ch_fscrbacktype.GetSelection() == 1)
        if self._for_local:
            if self.copybtn:
                self.copybtn.Enable(enbl)
            self.initbtn.Enable(enbl)

    def OnInitValue(self, event: wx.CommandEvent) -> None:
        local = cw.setting.LocalSetting()
        local.init()
        self.init_values(None, local)

    def OnCopyBase(self, event: wx.CommandEvent) -> None:
        assert self._get_localsettings
        local = self._get_localsettings()
        local.important_draw = True
        self.load(None, local)


class AudioSettingPanel(wx.Panel):
    def __init__(self, parent: wx.Notebook) -> None:
        wx.Panel.__init__(self, parent)

        self.box_gene = wx.StaticBox(self, -1, "詳細")
        # 音楽を再生する
        self.cb_playbgm = wx.CheckBox(
            self, -1, "音楽を再生する")
        # 効果音を再生する
        self.cb_playsound = wx.CheckBox(
            self, -1, "効果音を再生する")

        # 全体音量
        self.box_master = wx.StaticBox(self, -1, "全体音量(右クリック+ホイールでも調節可能)")
        self.sl_master = wx.Slider(
            self, -1, 0, 0, 100, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.sl_master.SetTickFreq(10)

        # 音量
        self.box_music = wx.StaticBox(self, -1, "ミュージック音量")
        self.sl_music = wx.Slider(
            self, -1, 0, 0, 100, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.sl_music.SetTickFreq(10)

        # midi音量
        self.box_midi = wx.StaticBox(self, -1, "MIDIミュージック音量")
        self.sl_midi = wx.Slider(
            self, -1, 0, 0, 100, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.sl_midi.SetTickFreq(10)

        # 効果音音量
        self.box_sound = wx.StaticBox(self, -1, "効果音音量")
        self.sl_sound = wx.Slider(
            self, -1, 0, 0, 100, size=(_settings_width()-cw.ppis(10), -1),
            style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        self.sl_sound.SetTickFreq(10)

        # サウンドフォント
        self.box_soundfont = wx.StaticBox(self, -1, "MIDIサウンドフォント")
        self.btn_addsoundfont = wx.Button(self, -1, "追加...")
        self.btn_rmvsoundfont = wx.Button(self, -1, "削除")
        self.btn_upsoundfont = wx.Button(self, -1, "↑", size=(cw.ppis(25), -1))
        self.btn_downsoundfont = wx.Button(self, -1, "↓", size=(cw.ppis(25), -1))

        self.grid_soundfont = wx.grid.Grid(self, -1, size=(1, 0), style=wx.BORDER)
        self.grid_soundfont.SetDoubleBuffered(True)
        self.grid_soundfont.CreateGrid(0, 3)
        self.grid_soundfont.DisableDragRowSize()
        self.grid_soundfont.SetSelectionMode(wx.grid.Grid.SelectRows)
        self.grid_soundfont.SetRowLabelAlignment(wx.LEFT, wx.CENTER)
        self.grid_soundfont.SetRowLabelSize(cw.ppis(0))
        self.grid_soundfont.SetColLabelValue(0, "使用")
        self.grid_soundfont.SetColSize(0, cw.ppis(40))
        self.grid_soundfont.SetColLabelValue(1, "ファイル")
        self.grid_soundfont.SetColSize(1, cw.ppis(210))
        self.grid_soundfont.SetColLabelValue(2, "音量(%)")
        self.grid_soundfont.SetColSize(2, cw.ppis(50))

        self._do_layout()
        self._bind()

    def load(self, setting: cw.setting.Setting) -> None:
        self.cb_playbgm.SetValue(setting.play_bgm)
        self.cb_playsound.SetValue(setting.play_sound)
        n = int(setting.vol_master * 100)
        self.sl_master.SetValue(n)
        n = int(setting.vol_bgm * 100)
        self.sl_music.SetValue(n)
        n = int(setting.vol_bgm_midi * 100)
        self.sl_midi.SetValue(n)
        n = int(setting.vol_sound * 100)
        self.sl_sound.SetValue(n)
        self._init_soundfont(setting.soundfonts)

    def init_values(self, setting: cw.setting.Setting) -> None:
        self.cb_playbgm.SetValue(setting.play_bgm_init)
        self.cb_playsound.SetValue(setting.play_sound_init)
        self.sl_master.SetValue(int(setting.vol_master_init * 100))
        self.sl_music.SetValue(int(setting.vol_bgm_init * 100))
        self.sl_midi.SetValue(int(setting.vol_bgm_midi_init * 100))
        self.sl_sound.SetValue(int(setting.vol_sound_init * 100))
        self._init_soundfont(setting.soundfonts_init)

    def _init_soundfont(self, soundfonts: List[Tuple[str, bool, int]]) -> None:
        if 0 < self.grid_soundfont.GetNumberRows():
            self.grid_soundfont.DeleteRows(0, self.grid_soundfont.GetNumberRows())
        self.grid_soundfont.AppendRows(len(soundfonts))
        for row, soundfont in enumerate(soundfonts):
            self.set_soundfont(row, soundfont)
        self._select_changed_soundfonts()

    def set_soundfont(self, row: int, soundfont: Tuple[str, bool, int]) -> None:
        sfont, use, volume = soundfont
        self.grid_soundfont.SetCellValue(row, 0, "1" if use else "")
        self.grid_soundfont.SetCellValue(row, 1, sfont)
        self.grid_soundfont.SetCellRenderer(row, 1, cw.util.FilePathRenderer(True, False))
        self.grid_soundfont.SetCellValue(row, 2, str(volume))
        self.grid_soundfont.SetCellEditor(row, 0, wx.grid.GridCellBoolEditor())
        self.grid_soundfont.SetCellRenderer(row, 0, wx.grid.GridCellBoolRenderer())
        self.grid_soundfont.SetCellEditor(row, 2, wx.grid.GridCellNumberEditor(0, 100))
        self.grid_soundfont.SetCellRenderer(row, 2, wx.grid.GridCellNumberRenderer())
        self.grid_soundfont.SetCellAlignment(row, 0, wx.ALIGN_CENTER, 0)
        self.grid_soundfont.SetCellAlignment(row, 1, wx.ALIGN_LEFT, 0)
        self.grid_soundfont.SetCellAlignment(row, 2, wx.ALIGN_CENTER, 0)
        self.grid_soundfont.SetReadOnly(row, 1, True)

    def get_soundfont(self, row: int) -> Tuple[str, bool, int]:
        sfont = self.grid_soundfont.GetCellValue(row, 1)
        use = self.grid_soundfont.GetCellValue(row, 0) != ""
        volume = int(self.grid_soundfont.GetCellValue(row, 2))
        return (sfont, use, volume)

    def _bind(self) -> None:
        self.Bind(wx.EVT_BUTTON, self.OnAddSoundFontBtn, self.btn_addsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveSoundFontBtn, self.btn_rmvsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnUpSoundFontBtn, self.btn_upsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnDownSoundFontBtn, self.btn_downsoundfont)
        self.grid_soundfont.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnGridRangeSelect)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_master = wx.StaticBoxSizer(self.box_master, wx.VERTICAL)
        bsizer_music = wx.StaticBoxSizer(self.box_music, wx.VERTICAL)
        bsizer_midi = wx.StaticBoxSizer(self.box_midi, wx.VERTICAL)
        bsizer_sound = wx.StaticBoxSizer(self.box_sound, wx.VERTICAL)
        bsizer_soundfont = wx.StaticBoxSizer(self.box_soundfont, wx.VERTICAL)

        bsizer_gene.Add(self.cb_playbgm, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_playsound, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.SetMinSize((_settings_width(), -1))

        sizer_soundfontbtns = wx.BoxSizer(wx.HORIZONTAL)
        sizer_soundfontbtns.Add(self.btn_addsoundfont, 0, wx.RIGHT, cw.ppis(3))
        sizer_soundfontbtns.Add(self.btn_rmvsoundfont, 0, wx.RIGHT, cw.ppis(3))
        sizer_soundfontbtns.Add(self.btn_upsoundfont, 0, wx.RIGHT, cw.ppis(3))
        sizer_soundfontbtns.Add(self.btn_downsoundfont, 0, 0, cw.ppis(0))

        bsizer_master.Add(self.sl_master, 0, wx.EXPAND, cw.ppis(0))
        bsizer_music.Add(self.sl_music, 0, wx.EXPAND, cw.ppis(0))
        bsizer_midi.Add(self.sl_midi, 0, wx.EXPAND, cw.ppis(0))
        bsizer_sound.Add(self.sl_sound, 0, wx.EXPAND, cw.ppis(0))
        bsizer_soundfont.Add(sizer_soundfontbtns, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_soundfont.Add(self.grid_soundfont, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, cw.ppis(3))

        sizer_left.Add(bsizer_gene, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_master, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_music, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_midi, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_left.Add(bsizer_sound, 0, wx.EXPAND, cw.ppis(3))

        sizer_right.Add(bsizer_soundfont, 1, wx.EXPAND, cw.ppis(0))

        sizer_h1.Add(sizer_left, 0, wx.RIGHT | wx.EXPAND, cw.ppis(5))
        sizer_h1.Add(sizer_right, 1, wx.EXPAND, cw.ppis(3))

        sizer.Add(sizer_h1, 1, wx.ALL | wx.EXPAND, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnGridRangeSelect(self, event: wx.grid.GridRangeSelectEvent) -> None:
        wx.CallAfter(self._select_changed_soundfonts)

    def _select_changed_soundfonts(self) -> None:
        indexes = self.grid_soundfont.GetSelectedRows()
        indexes.sort()
        lcount = self.grid_soundfont.GetNumberRows()
        self.btn_rmvsoundfont.Enable(bool(indexes))
        self.btn_upsoundfont.Enable(bool(indexes and 0 < indexes[0]))
        self.btn_downsoundfont.Enable(bool(indexes and indexes[-1] + 1 < lcount))

    def OnAddSoundFontBtn(self, event: wx.CommandEvent) -> None:
        dlg = wx.FileDialog(self.GetTopLevelParent(), "MIDIの演奏に使用するサウンドフォント選択",
                            "Data/SoundFont", "", "*.sf2", wx.FD_OPEN | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            exists = set()
            index = -1
            for index in range(self.grid_soundfont.GetNumberRows()):
                soundfont = self.grid_soundfont.GetCellValue(index, 1)
                exists.add(soundfont.lower())

            for fname in dlg.GetFilenames():
                fpath = os.path.join(dlg.GetDirectory(), fname)
                try:
                    rel = cw.util.relpath(fpath, "")
                    if not rel.startswith(".."):
                        fpath = rel
                except Exception:
                    cw.util.print_ex()
                fpath = cw.util.join_paths(fpath)
                if fpath.lower() in exists:
                    continue

                row = self.grid_soundfont.GetNumberRows()
                self.grid_soundfont.AppendRows(1)
                self.set_soundfont(row, (fpath, True, 100))
                self.GetTopLevelParent().applied()
            self._select_changed_soundfonts()
        dlg.Destroy()

    def OnRemoveSoundFontBtn(self, event: wx.CommandEvent) -> None:
        indexes = self.grid_soundfont.GetSelectedRows()
        for index in reversed(sorted(indexes)):
            self.grid_soundfont.DeleteRows(index)
        self._select_changed_soundfonts()
        self.GetTopLevelParent().applied()

    def OnUpSoundFontBtn(self, event: wx.CommandEvent) -> None:
        indexes = self.grid_soundfont.GetSelectedRows()
        indexes.sort()
        if not indexes or indexes[0] < 1:
            return
        self.grid_soundfont.ClearSelection()
        for row in indexes:
            soundfont1 = self.get_soundfont(row-1)
            soundfont2 = self.get_soundfont(row)
            self.set_soundfont(row-1, soundfont2)
            self.set_soundfont(row, soundfont1)
            self.grid_soundfont.SelectRow(row-1, True)
        self._select_changed_soundfonts()
        self.GetTopLevelParent().applied()
        self.grid_soundfont.MakeCellVisible(indexes[0]-1, 0)

    def OnDownSoundFontBtn(self, event: wx.CommandEvent) -> None:
        indexes = self.grid_soundfont.GetSelectedRows()
        indexes.sort()
        if not indexes or self.grid_soundfont.GetNumberRows() <= indexes[-1] + 1:
            return
        self.grid_soundfont.ClearSelection()
        for row in reversed(indexes):
            soundfont1 = self.get_soundfont(row)
            soundfont2 = self.get_soundfont(row+1)
            self.set_soundfont(row, soundfont2)
            self.set_soundfont(row+1, soundfont1)
            self.grid_soundfont.SelectRow(row+1, True)
        self._select_changed_soundfonts()
        self.GetTopLevelParent().applied()
        self.grid_soundfont.MakeCellVisible(indexes[-1]+1, 0)


class ScenarioSettingPanel(wx.Panel):
    def __init__(self, parent: wx.Notebook) -> None:
        wx.Panel.__init__(self, parent)

        # シナリオのオプション
        self.box_gene = wx.StaticBox(self, -1, "詳細")
        self.cb_selectscenariofromtype = wx.CheckBox(self, -1, "シナリオの選択開始位置をスキン毎に変更する")
        self.cb_show_paperandtree = wx.CheckBox(self, -1, "シナリオ選択ダイアログで貼紙と一覧を同時に表示する")
        self.cb_write_playlog = wx.CheckBox(self, -1, "シナリオのプレイログを出力する")
        self.cb_can_installscenariofromdrop = wx.CheckBox(self, -1, "シナリオ選択ダイアログへシナリオをドロップした時はインストールダイアログを表示する")
        self.cb_delete_sourceafterinstalled = wx.CheckBox(self, -1, "シナリオのインストールに成功したら元ファイルを削除する")
        self.cb_open_lastscenario = wx.CheckBox(
            self, -1, "最後に選んだシナリオをシナリオの選択開始位置にする")

        # スキンタイプ毎の初期フォルダ
        self.box_folderoftype = wx.StaticBox(self, -1, "シナリオフォルダ(スキンタイプ別)")
        self.btn_reffolder = wx.Button(self, -1, "参照...")
        self.btn_removefolder = wx.Button(self, -1, "削除")
        self.btn_upfolder = wx.Button(self, -1, "↑", size=(cw.ppis(25), -1))
        self.btn_downfolder = wx.Button(self, -1, "↓", size=(cw.ppis(25), -1))

        self.btn_constructdb = wx.Button(self, -1, "データベース構築...", size=(-1, -1))

        self.grid_folderoftype = wx.grid.Grid(self, -1, size=(1, 0), style=wx.BORDER)
        self.grid_folderoftype.CreateGrid(0, 2)
        self.grid_folderoftype.SetSelectionMode(wx.grid.Grid.SelectRows)

        self.celleditor = None

        # シナリオエディタ
        self.box_application = wx.StaticBox(self, -1, "外部アプリ")
        self.st_editor = wx.StaticText(self, -1, "エディタ")
        self.tx_editor = wx.TextCtrl(self, -1, size=(-1, -1))
        if sys.platform == "win32":
            wildcard = "実行可能ファイル (*.exe)|*.exe|全てのファイル (*.*)|*.*"
        else:
            wildcard = "全てのファイル (*.*)|*.*"
        self.ref_editor = cw.util.create_fileselection(self,
                                                       target=self.tx_editor,
                                                       message="CardWirthのシナリオエディタを選択",
                                                       wildcard=wildcard)

        # シナリオ選択ダイアログでのファイラー(フォルダ用)
        self.st_filer_dir = wx.StaticText(self, -1, "ファイラー(フォルダ用)")
        self.tx_filer_dir = wx.TextCtrl(self, -1, size=(-1, -1))
        tip = "シナリオの場所を開くためのファイラー(フォルダ用)を選択"
        self.ref_filer_dir = cw.util.create_fileselection(self,
                                                          target=self.tx_filer_dir,
                                                          message=tip,
                                                          wildcard=wildcard)
        # シナリオ選択ダイアログでのファイラー(ファイル用)
        self.st_filer_file = wx.StaticText(self, -1, "ファイラー(ファイル用)")
        self.tx_filer_file = wx.TextCtrl(self, -1, size=(-1, -1))
        tip = "シナリオの場所を開くためのファイラー(ファイル用)を選択"
        self.ref_filer_file = cw.util.create_fileselection(self,
                                                           target=self.tx_filer_file,
                                                           message=tip,
                                                           wildcard=wildcard)

        w, h, _lh = 0, 0, 0
        for obj in (self.st_editor, self.st_filer_dir, self.st_filer_file):
            dc = wx.ClientDC(obj)
            w2, h2, _lh = dc.GetFullMultiLineTextExtent(obj.GetLabel())
            w = max(w, w2)
            h = max(h, h2)
        for obj in (self.st_editor, self.st_filer_dir, self.st_filer_file):
            obj.SetMinSize((w + cw.ppis(15), h))

        self._do_layout()
        self._bind()

    def load(self, setting: cw.setting.Setting) -> None:
        self.cb_selectscenariofromtype.SetValue(setting.selectscenariofromtype)
        self.cb_show_paperandtree.SetValue(setting.show_paperandtree)
        self.cb_write_playlog.SetValue(setting.write_playlog)
        self.cb_can_installscenariofromdrop.SetValue(setting.can_installscenariofromdrop)
        self.cb_delete_sourceafterinstalled.SetValue(setting.delete_sourceafterinstalled)
        self.cb_open_lastscenario.SetValue(setting.open_lastscenario)
        if 0 < self.grid_folderoftype.GetNumberRows():
            self.grid_folderoftype.DeleteRows(0, self.grid_folderoftype.GetNumberRows())
        self.grid_folderoftype.SetColLabelSize(cw.ppis(0))
        self.grid_folderoftype.SetRowLabelSize(cw.ppis(0))
        self.grid_folderoftype.SetColSize(0, cw.ppis(100))
        self.grid_folderoftype.SetColSize(1, cw.ppis(370))
        for row, (skintype, folder) in enumerate(setting.folderoftype):
            self.grid_folderoftype.AppendRows(1)
            self.grid_folderoftype.SetCellValue(row, 0, skintype)
            self.grid_folderoftype.SetCellValue(row, 1, folder)
            # FIXME: 末尾の列にFilePathRendererを設定すると選択表示が1つ上の行になってしまう
            # self.grid_folderoftype.SetCellRenderer(row, 1, cw.util.FilePathRenderer(False, True))
        self.grid_folderoftype.AppendRows(1)
        self.tx_editor.SetValue(setting.editor)
        self.tx_filer_dir.SetValue(setting.filer_dir)
        self.tx_filer_file.SetValue(setting.filer_file)
        self._select_changed_folderoftype()

    def init_values(self, setting: cw.setting.Setting) -> None:
        self.tx_editor.SetValue(setting.editor_init)
        self.cb_selectscenariofromtype.SetValue(setting.selectscenariofromtype_init)
        self.cb_show_paperandtree.SetValue(setting.show_paperandtree_init)
        self.cb_write_playlog.SetValue(setting.write_playlog_init)
        self.cb_can_installscenariofromdrop.SetValue(setting.can_installscenariofromdrop_init)
        self.cb_delete_sourceafterinstalled.SetValue(setting.delete_sourceafterinstalled_init)
        self.cb_open_lastscenario.SetValue(setting.open_lastscenario_init)
        self.tx_filer_dir.SetValue(setting.filer_dir_init)
        self.tx_filer_file.SetValue(setting.filer_file_init)
        self._select_changed_folderoftype()

    def OnGirdSelectCell(self, event: wx.grid.GridEvent) -> None:
        if self.celleditor:
            wx.CallAfter(self._select_changed_folderoftype)
            return

        types = list(self.Parent.Parent.pane_gene.skin.all_skintypes)
        cw.util.sort_by_attr(types)

        colattr = wx.grid.GridCellAttr()
        self.celleditor = wx.grid.GridCellChoiceEditor(types, allowOthers=True)
        colattr.SetEditor(self.celleditor)
        self.grid_folderoftype.SetColAttr(0, colattr)

        wx.CallAfter(self._select_changed_folderoftype)

    def _select_changed_folderoftype(self) -> None:
        row = self.grid_folderoftype.GetGridCursorRow()
        lcount = self.grid_folderoftype.GetNumberRows()
        self.btn_reffolder.Enable(row != -1)
        self.btn_removefolder.Enable(bool(row != -1 and row < lcount-1))
        self.btn_upfolder.Enable(bool(row != -1 and 1 <= row and row < lcount-1))
        self.btn_downfolder.Enable(bool(row != -1 and row + 2 < lcount))

    def _bind(self) -> None:
        self.Bind(wx.EVT_BUTTON, self.OnRefFolderBtn, self.btn_reffolder)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveFolderBtn, self.btn_removefolder)
        self.Bind(wx.EVT_BUTTON, self.OnUpFolderBtn, self.btn_upfolder)
        self.Bind(wx.EVT_BUTTON, self.OnDownFolderBtn, self.btn_downfolder)
        self.Bind(wx.EVT_BUTTON, self.OnConstructDBBtn, self.btn_constructdb)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridCellChange, self.grid_folderoftype)
        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnGirdSelectCell, self.grid_folderoftype)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_folderoftype = wx.StaticBoxSizer(self.box_folderoftype, wx.VERTICAL)

        bsizer_gene.Add(self.cb_selectscenariofromtype, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_open_lastscenario, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_show_paperandtree, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_write_playlog, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_can_installscenariofromdrop, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_delete_sourceafterinstalled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.SetMinSize((_settings_width(), -1))

        sizer_folderbtns = wx.BoxSizer(wx.HORIZONTAL)
        sizer_folderbtns.Add(self.btn_reffolder, 0, wx.RIGHT, cw.ppis(3))
        sizer_folderbtns.Add(self.btn_removefolder, 0, wx.RIGHT, cw.ppis(3))
        sizer_folderbtns.Add(self.btn_upfolder, 0, wx.RIGHT, cw.ppis(3))
        sizer_folderbtns.Add(self.btn_downfolder, 0, wx.RIGHT, cw.ppis(3))
        sizer_folderbtns.Add(cw.ppis((0, 0)), 1, 0, cw.ppis(0))
        sizer_folderbtns.Add(self.btn_constructdb, 0, 0, cw.ppis(0))

        bsizer_folderoftype.Add(sizer_folderbtns, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        bsizer_folderoftype.Add(self.grid_folderoftype, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, cw.ppis(3))

        bsizer_application = wx.StaticBoxSizer(self.box_application, wx.VERTICAL)
        gbsizer_application = wx.GridBagSizer()

        def add_application(ctrl: wx.Control, pos: Tuple[int, int], flag: int) -> None:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(ctrl, 1, wx.ALIGN_CENTER_VERTICAL, 0)
            gbsizer_application.Add(sizer, pos=pos, flag=flag | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border=cw.ppis(2))

        add_application(self.st_editor, pos=(0, 0), flag=wx.RIGHT | wx.BOTTOM)
        add_application(self.tx_editor, pos=(0, 1), flag=wx.RIGHT | wx.BOTTOM)
        add_application(self.ref_editor, pos=(0, 2), flag=wx.BOTTOM)
        add_application(self.st_filer_dir, pos=(1, 0), flag=wx.RIGHT | wx.BOTTOM)
        add_application(self.tx_filer_dir, pos=(1, 1), flag=wx.RIGHT | wx.BOTTOM)
        add_application(self.ref_filer_dir, pos=(1, 2), flag=wx.BOTTOM)
        add_application(self.st_filer_file, pos=(2, 0), flag=wx.RIGHT)
        add_application(self.tx_filer_file, pos=(2, 1), flag=wx.RIGHT)
        add_application(self.ref_filer_file, pos=(2, 2), flag=0)
        gbsizer_application.AddGrowableCol(1)
        bsizer_application.Add(gbsizer_application, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_v1.Add(bsizer_folderoftype, 1, wx.BOTTOM | wx.EXPAND, cw.ppis(3))
        sizer_v1.Add(bsizer_application, 0, wx.EXPAND, cw.ppis(0))

        sizer.Add(sizer_v1, 1, wx.ALL | wx.EXPAND, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnGridCellChange(self, event: wx.grid.GridEvent) -> None:
        self._grid_cell_change(event.Row, event.Col)

    def _grid_cell_change(self, row: int, col: int) -> None:
        if col == 0 and row + 1 == self.grid_folderoftype.GetNumberRows() and\
                self.grid_folderoftype.GetCellValue(row, 0):
            self.grid_folderoftype.AppendRows(1)
            self.grid_folderoftype.SetCellRenderer(row+1, 1, cw.util.FilePathRenderer(False, True))

    def OnRefFolderBtn(self, event: wx.CommandEvent) -> None:
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1:
            return

        skintype = self.grid_folderoftype.GetCellValue(row, 0)
        if not skintype:
            skintype = "(指定無し)"

        dpath = os.path.abspath("Scenario")
        s = "「%s」タイプのスキンでプレイするシナリオのフォルダを選択してください" % (skintype)
        dlg = wx.DirDialog(self.TopLevelParent, s, dpath, style=wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            dpath = dlg.GetPath()
            relpath = cw.util.relpath(dpath, ".")
            if not relpath.startswith(".."):
                dpath = relpath
            self.grid_folderoftype.SetCellValue(row, 1, cw.util.join_paths(dpath))
            if not self.grid_folderoftype.GetCellValue(row, 0):
                self.grid_folderoftype.SetCellValue(row, 0, "MedievalFantasy")
                self._grid_cell_change(row, 0)
            self._select_changed_folderoftype()
            self.GetTopLevelParent().applied()
        dlg.Destroy()

    def OnRemoveFolderBtn(self, event: wx.CommandEvent) -> None:
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or row + 1 == self.grid_folderoftype.GetNumberRows():
            return
        self.grid_folderoftype.DeleteRows(row)
        self._select_changed_folderoftype()
        self.GetTopLevelParent().applied()

    def OnUpFolderBtn(self, event: wx.CommandEvent) -> None:
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or row == 0:
            return
        for col in range(self.grid_folderoftype.GetNumberCols()):
            value1 = self.grid_folderoftype.GetCellValue(row, col)
            value2 = self.grid_folderoftype.GetCellValue(row - 1, col)
            self.grid_folderoftype.SetCellValue(row, col, value2)
            self.grid_folderoftype.SetCellValue(row - 1, col, value1)
            self.grid_folderoftype.SelectRow(row - 1)
            self.GetTopLevelParent().applied()
        self.grid_folderoftype.SetGridCursor(row - 1, self.grid_folderoftype.GetGridCursorCol())
        self._select_changed_folderoftype()
        self.grid_folderoftype.MakeCellVisible(row - 1, 0)

    def OnDownFolderBtn(self, event: wx.CommandEvent) -> None:
        row = self.grid_folderoftype.GetGridCursorRow()
        if row == -1 or self.grid_folderoftype.GetNumberRows() <= row + 2:
            return
        for col in range(self.grid_folderoftype.GetNumberCols()):
            value1 = self.grid_folderoftype.GetCellValue(row, col)
            value2 = self.grid_folderoftype.GetCellValue(row + 1, col)
            self.grid_folderoftype.SetCellValue(row, col, value2)
            self.grid_folderoftype.SetCellValue(row + 1, col, value1)
            self.grid_folderoftype.SelectRow(row + 1)
            self.GetTopLevelParent().applied()
        self.grid_folderoftype.SetGridCursor(row + 1, self.grid_folderoftype.GetGridCursorCol())
        self._select_changed_folderoftype()
        self.grid_folderoftype.MakeCellVisible(row + 1, 0)

    def OnConstructDBBtn(self, event: wx.CommandEvent) -> None:
        from . import editscenariodb

        d: Dict[str, Set[str]] = {}
        for row in range(self.grid_folderoftype.GetNumberRows()):
            skintype = self.grid_folderoftype.GetCellValue(row, 0)
            dpath = self.grid_folderoftype.GetCellValue(row, 1)
            if not dpath:
                continue
            if skintype in d:
                s = d[skintype]
            else:
                s = set()
                d[skintype] = s
            dpath = cw.util.get_linktarget(dpath)
            if os.path.isdir(dpath):
                s.add(dpath)

        if os.path.isdir("Scenario"):
            if cw.cwpy.setting.skintype not in d:
                d[cw.cwpy.setting.skintype] = {"Scenario"}
            elif not d:
                d[""] = {"Scenario"}

        dlg = editscenariodb.ConstructScenarioDB(self.TopLevelParent, dpaths=d)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()


class UISettingPanel(wx.ScrolledWindow):
    def __init__(self, parent: wx.Notebook) -> None:
        wx.ScrolledWindow.__init__(self, parent)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.SetScrollbars(1, 1, 1, 1)
        self.SetScrollRate(1, cw.ppis(25))
        self.SetScrollPageSize(1, cw.ppis(200))

        # 空白時間オプション
        self.box_skip_and_wait = wx.StaticBox(self, -1, "スキップと空白時間")
        self.cb_can_skipwait = wx.CheckBox(
            self, -1, "空白時間をスキップ可能にする")
        self.cb_can_skipanimation = wx.CheckBox(
            self, -1, "アニメーションをスキップ可能にする")
        self.cb_can_skipwait_with_wheel = wx.CheckBox(
            self, -1, "マウスのホイールで空白時間とアニメーションをスキップする")
        self.cb_can_forwardmessage_with_wheel = wx.CheckBox(
            self, -1, "マウスのホイールでメッセージ送りを行う")
        self.cb_wait_usecard = wx.CheckBox(
            self, -1, "カードの使用前に空白時間を入れる")
        self.cb_enlarge_beastcardzoomingratio = wx.CheckBox(
            self, -1, "召喚獣カードの拡大率を大きくする")
        self.cb_autoenter_on_sprite = wx.CheckBox(
            self, -1, "連打状態の時、カードなどの選択を自動的に決定する")

        # 描画オプション
        self.box_card = wx.StaticBox(self, -1, "カード")
        self.cb_quickdeal = wx.CheckBox(
            self, -1, "キャンプモードへ高速で切り替える")
        self.cb_allquickdeal = wx.CheckBox(
            self, -1, "全てのシステムカードを高速表示する")
        self.cb_showallselectedcards = wx.CheckBox(
            self, -1, "戦闘行動を全員分表示する")
        self.cb_show_cardkind = wx.CheckBox(
            self, -1, "カード置場と荷物袋でカードの種類を表示する")
        self.cb_show_premiumicon = wx.CheckBox(
            self, -1, "カードの希少度をアイコンで表示する")

        self.panel_show_statustime = wx.Panel(self, -1)
        self.st_panel_show_statustime = wx.StaticText(self.panel_show_statustime, -1,
                                                      "状態の残り時間:")
        choices = ["イベント中でなければ表示", "常に表示", "表示しない"]
        self.ch_show_statustime = wx.Choice(self.panel_show_statustime, -1, choices=choices)
        bsizer_show_statustime = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_show_statustime.Add(self.st_panel_show_statustime, 0, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_show_statustime.Add(self.ch_show_statustime, 0, wx.ALIGN_CENTER, cw.ppis(0))
        self.panel_show_statustime.SetSizer(bsizer_show_statustime)
        self.panel_show_statustime.SetSize(bsizer_show_statustime.CalcMin())

        # インタフェースオプション
        self.box_control = wx.StaticBox(self, -1, "操作")
        # self.cb_spend_noeffectcard = wx.CheckBox(
        #     self, -1, u"意味の無いカード使用で使用回数を消費する")
        self.cb_show_personal_cards = wx.CheckBox(
            self, -1, "荷物袋にあるカードのキャラクターごとの私有を許可する")
        self.cb_showbackpackcard = wx.CheckBox(
            self, -1, "荷物袋のカードを一時的に取り出して使えるようにする")
        self.cb_showbackpackcardatend = wx.CheckBox(
            self, -1, "荷物袋カードを最後に配置する")
        self.cb_revertcardpocket = wx.CheckBox(
            self, -1, "レベル調節で手放したカードを自動的に戻す")
        self.cb_showroundautostartbutton = wx.CheckBox(
            self, -1, "バトルで自動的に行動を開始できるようにする")
        self.cb_showautobuttoninentrydialog = wx.CheckBox(
            self, -1, "新規登録ダイアログに自動ボタンを表示する")
        self.cb_protect_staredcard = wx.CheckBox(
            self, -1, "スターつきのカードの売却や破棄を禁止する")
        self.cb_protect_premiercard = wx.CheckBox(
            self, -1, "プレミアカードの売却や破棄を禁止する")

        self.panel_confirm_dumpcard = wx.Panel(self, -1)
        self.st_confirm_dumpcard = wx.StaticText(self.panel_confirm_dumpcard, -1,
                                                 "カードの売却と破棄の確認ダイアログ:")
        choices = ["常に表示", "「送り先」の使用時のみ表示", "表示しない"]
        self.ch_confirm_dumpcard = wx.Choice(self.panel_confirm_dumpcard, -1, choices=choices)
        bsizer_confirm_dumpcard = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_confirm_dumpcard.Add(self.st_confirm_dumpcard, 0, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_confirm_dumpcard.Add(self.ch_confirm_dumpcard, 0, wx.ALIGN_CENTER, cw.ppis(0))
        self.panel_confirm_dumpcard.SetSizer(bsizer_confirm_dumpcard)
        self.panel_confirm_dumpcard.SetSize(bsizer_confirm_dumpcard.CalcMin())

        self.cb_can_clicksidesofcardcontrol = wx.CheckBox(
            self, -1, "カード選択ダイアログの背景クリックで左右移動を行う")
        self.cb_showlogwithwheelup = wx.CheckBox(
            self, -1, "マウスホイールを上に回すとログを表示")

        self.panel_radius_notdetectmovement = wx.Panel(self, -1)

        self.st_panel_radius_notdetectmovement = wx.StaticText(
            self.panel_radius_notdetectmovement, -1,
            "マウスホイールでのカードの選択中にカーソルの小さな動きを無視する:"
        )
        self.sc_radius_notdetectmovement = wx.SpinCtrl(self.panel_radius_notdetectmovement, -1, "",
                                                       size=(cw.ppis(50+_spin_w_addition), -1))
        self.sc_radius_notdetectmovement.SetRange(0, 50)
        self.st_panel_radius_notdetectmovement_2 = wx.StaticText(self.panel_radius_notdetectmovement, -1,
                                                                 "ピクセルまで")
        bsizer_radius_notdetectmovement = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_radius_notdetectmovement.Add(self.st_panel_radius_notdetectmovement, 0, wx.ALIGN_CENTER | wx.RIGHT,
                                            cw.ppis(3))
        bsizer_radius_notdetectmovement.Add(self.sc_radius_notdetectmovement, 0, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_radius_notdetectmovement.Add(self.st_panel_radius_notdetectmovement_2, 0, wx.ALIGN_CENTER, cw.ppis(0))
        self.panel_radius_notdetectmovement.SetSizer(bsizer_radius_notdetectmovement)
        self.panel_radius_notdetectmovement.SetSize(bsizer_radius_notdetectmovement.CalcMin())

        # 通知オプション
        self.box_confirm_and_description = wx.StaticBox(self, -1, "通知と解説")
        # ステータスバーのボタンの解説を表示する
        self.cb_show_btndesc = wx.CheckBox(
            self, -1, "ステータスバーのボタンの解説を表示する")
        # イベント中にステータスバーの色を変える
        self.cb_statusbarmask = wx.CheckBox(
            self, -1, "イベント中にステータスバーの色を変える")
        # 通知のあるステータスボタンを点滅させる
        self.cb_blink_statusbutton = wx.CheckBox(
            self, -1, "通知のあるステータスボタンを点滅させる")
        # 所持金が増減した時に所持金欄を点滅させる
        self.cb_blink_partymoney = wx.CheckBox(
            self, -1, "所持金が増減した時に所持金欄を点滅させる")

        # セーブとロードオプション
        self.box_save_and_load = wx.StaticBox(self, -1, "セーブとロード")

        self.panel_confirm_beforesaving = wx.Panel(self, -1)
        self.st_confirm_beforesaving = wx.StaticText(self.panel_confirm_beforesaving, -1,
                                                     "セーブ前の確認ダイアログ:")
        choices = ["常に表示", "拠点にいる時だけ表示", "表示しない"]
        self.ch_confirm_beforesaving = wx.Choice(self.panel_confirm_beforesaving, -1, choices=choices)
        bsizer_confirm_beforesaving = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_confirm_beforesaving.Add(self.st_confirm_beforesaving, 0, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(3))
        bsizer_confirm_beforesaving.Add(self.ch_confirm_beforesaving, 0, wx.ALIGN_CENTER, cw.ppis(0))
        self.panel_confirm_beforesaving.SetSizer(bsizer_confirm_beforesaving)
        self.panel_confirm_beforesaving.SetSize(bsizer_confirm_beforesaving.CalcMin())

        self.cb_showsavedmessage = wx.CheckBox(
            self, -1, "セーブ完了時に確認ダイアログを表示")
        self.cb_cautionbeforesaving = wx.CheckBox(
            self, -1, "保存せずに終了しようとしたら警告する")

        # ダイアログオプション
        self.box_dialog = wx.StaticBox(self, -1, "ダイアログ")
        self.cb_show_advancedsettings = wx.CheckBox(
            self, -1, "最初から詳細モードで設定を行う")
        self.cb_show_addctrlbtn = wx.CheckBox(
            self, -1, "絞り込み等の表示切替ボタンを表示する(非表示時はCtrl+Fで切替可能)")
        self.cb_show_experiencebar = wx.CheckBox(
            self, -1, "キャラクター情報に次のレベルアップまでの割合を表示する")
        self.cb_confirmbeforeusingcard = wx.CheckBox(
            self, -1, "カード使用時に確認ダイアログを表示")
        self.cb_noticeimpossibleaction = wx.CheckBox(
            self, -1, "不可能な行動を選択した時に警告を表示")

        self._do_layout()
        self._bind()

    def load(self, setting: cw.setting.Setting) -> None:
        self.cb_can_skipwait.SetValue(setting.can_skipwait)
        self.cb_can_skipanimation.SetValue(setting.can_skipanimation)
        self.cb_can_skipwait_with_wheel.SetValue(setting.can_skipwait_with_wheel)
        self.cb_can_forwardmessage_with_wheel.SetValue(setting.can_forwardmessage_with_wheel)
        self.cb_wait_usecard.SetValue(setting.wait_usecard)
        self.cb_enlarge_beastcardzoomingratio.SetValue(setting.enlarge_beastcardzoomingratio)
        self.cb_autoenter_on_sprite.SetValue(setting.autoenter_on_sprite)

        self.cb_quickdeal.SetValue(setting.quickdeal)
        self.cb_allquickdeal.SetValue(setting.all_quickdeal)
        self.cb_showallselectedcards.SetValue(setting.show_allselectedcards)
        if setting.show_statustime == "NotEventTime":
            self.ch_show_statustime.SetSelection(0)
        elif setting.show_statustime == "True":
            self.ch_show_statustime.SetSelection(1)
        else:
            self.ch_show_statustime.SetSelection(2)
        self.cb_show_cardkind.SetValue(setting.show_cardkind)
        self.cb_show_premiumicon.SetValue(setting.show_premiumicon)

        # self.cb_spend_noeffectcard.SetValue(setting.spend_noeffectcard)
        self.cb_show_personal_cards.SetValue(setting.show_personal_cards)
        self.cb_showbackpackcard.SetValue(setting.show_backpackcard)
        self.cb_showbackpackcardatend.SetValue(setting.show_backpackcardatend)
        self.cb_can_clicksidesofcardcontrol.SetValue(setting.can_clicksidesofcardcontrol)
        self.cb_revertcardpocket.SetValue(setting.revert_cardpocket)
        self.cb_showlogwithwheelup.SetValue(setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG)
        self.cb_showroundautostartbutton.SetValue(setting.show_roundautostartbutton)
        self.cb_showautobuttoninentrydialog.SetValue(setting.show_autobuttoninentrydialog)
        self.cb_protect_staredcard.SetValue(setting.protect_staredcard)
        self.cb_protect_premiercard.SetValue(setting.protect_premiercard)

        if setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_SENDTO:
            self.ch_confirm_dumpcard.SetSelection(1)
        elif setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_NO:
            self.ch_confirm_dumpcard.SetSelection(2)
        else:
            self.ch_confirm_dumpcard.SetSelection(0)

        self.sc_radius_notdetectmovement.SetValue(setting.radius_notdetectmovement)

        self.cb_show_btndesc.SetValue(setting.show_btndesc)
        self.cb_statusbarmask.SetValue(setting.statusbarmask)
        self.cb_blink_statusbutton.SetValue(setting.blink_statusbutton)
        self.cb_blink_partymoney.SetValue(setting.blink_partymoney)

        if setting.confirm_beforesaving == cw.setting.CONFIRM_BEFORESAVING_BASE:
            self.ch_confirm_beforesaving.SetSelection(1)
        elif setting.confirm_beforesaving == cw.setting.CONFIRM_BEFORESAVING_NO:
            self.ch_confirm_beforesaving.SetSelection(2)
        else:
            self.ch_confirm_beforesaving.SetSelection(0)
        self.cb_cautionbeforesaving.SetValue(setting.caution_beforesaving)
        self.cb_showsavedmessage.SetValue(setting.show_savedmessage)

        self.cb_show_advancedsettings.SetValue(setting.show_advancedsettings)
        self.cb_show_addctrlbtn.SetValue(setting.show_addctrlbtn)
        self.cb_show_experiencebar.SetValue(setting.show_experiencebar)
        self.cb_confirmbeforeusingcard.SetValue(setting.confirm_beforeusingcard)
        self.cb_noticeimpossibleaction.SetValue(setting.noticeimpossibleaction)

    def init_values(self, setting: cw.setting.Setting) -> None:
        self.cb_can_skipwait.SetValue(setting.can_skipwait_init)
        self.cb_can_skipanimation.SetValue(setting.can_skipanimation_init)
        self.cb_can_skipwait_with_wheel.SetValue(setting.can_skipwait_with_wheel_init)
        self.cb_can_forwardmessage_with_wheel.SetValue(setting.can_forwardmessage_with_wheel_init)
        self.cb_wait_usecard.SetValue(setting.wait_usecard_init)
        self.cb_enlarge_beastcardzoomingratio.SetValue(setting.enlarge_beastcardzoomingratio_init)
        self.cb_autoenter_on_sprite.SetValue(setting.autoenter_on_sprite_init)

        self.cb_quickdeal.SetValue(setting.quickdeal_init)
        self.cb_allquickdeal.SetValue(setting.all_quickdeal_init)
        self.cb_showallselectedcards.SetValue(setting.show_allselectedcards_init)
        if setting.show_statustime_init == "NotEventTime":
            self.ch_show_statustime.SetSelection(0)
        elif setting.show_statustime_init == "True":
            self.ch_show_statustime.SetSelection(1)
        else:
            self.ch_show_statustime.SetSelection(2)
        self.cb_show_cardkind.SetValue(setting.show_cardkind_init)
        self.cb_show_premiumicon.SetValue(setting.show_premiumicon_init)
        self.cb_showroundautostartbutton.SetValue(setting.show_roundautostartbutton_init)
        self.cb_showautobuttoninentrydialog.SetValue(setting.show_autobuttoninentrydialog_init)
        self.cb_protect_staredcard.SetValue(setting.protect_staredcard_init)
        self.cb_protect_premiercard.SetValue(setting.protect_premiercard_init)
        # self.cb_spend_noeffectcard.SetValue(setting.spend_noeffectcard_init)

        if cw.setting.CONFIRM_DUMPCARD_SENDTO == setting.confirm_dumpcard_init:
            self.ch_confirm_dumpcard.SetSelection(1)
        elif cw.setting.CONFIRM_DUMPCARD_NO == setting.confirm_dumpcard_init:
            self.ch_confirm_dumpcard.SetSelection(2)
        else:
            self.ch_confirm_dumpcard.SetSelection(0)

        self.sc_radius_notdetectmovement.SetValue(setting.radius_notdetectmovement_init)

        self.cb_show_btndesc.SetValue(setting.show_btndesc_init)
        self.cb_statusbarmask.SetValue(setting.statusbarmask_init)
        self.cb_blink_statusbutton.SetValue(setting.blink_statusbutton_init)
        self.cb_blink_partymoney.SetValue(setting.blink_partymoney_init)

        self.cb_show_advancedsettings.SetValue(setting.show_advancedsettings_init)
        self.cb_show_addctrlbtn.SetValue(setting.show_addctrlbtn_init)
        self.cb_show_experiencebar.SetValue(setting.show_experiencebar_init)

        if cw.setting.CONFIRM_BEFORESAVING_BASE == setting.confirm_beforesaving_init:
            self.ch_confirm_beforesaving.SetSelection(1)
        elif not cw.util.str2bool(setting.confirm_beforesaving_init):
            self.ch_confirm_beforesaving.SetSelection(2)
        else:
            self.ch_confirm_beforesaving.SetSelection(0)
        self.cb_showsavedmessage.SetValue(setting.show_savedmessage_init)
        self.cb_cautionbeforesaving.SetValue(setting.caution_beforesaving_init)

        self.cb_show_personal_cards.SetValue(setting.show_personal_cards_init)
        self.cb_showbackpackcard.SetValue(setting.show_backpackcard_init)
        self.cb_showbackpackcardatend.SetValue(setting.show_backpackcardatend_init)
        self.cb_can_clicksidesofcardcontrol.SetValue(setting.can_clicksidesofcardcontrol_init)
        self.cb_revertcardpocket.SetValue(setting.revert_cardpocket_init)
        self.cb_showlogwithwheelup.SetValue(setting.wheelup_operation_init == cw.setting.WHEEL_SHOWLOG)
        self.cb_confirmbeforeusingcard.SetValue(setting.confirm_beforeusingcard_init)
        self.cb_noticeimpossibleaction.SetValue(setting.noticeimpossibleaction_init)

    def OnQuickDeal(self, event: wx.CommandEvent) -> None:
        if not self.cb_quickdeal.GetValue():
            self.cb_allquickdeal.SetValue(False)

    def OnAllQuickDeal(self, event: wx.CommandEvent) -> None:
        if self.cb_allquickdeal.GetValue():
            self.cb_quickdeal.SetValue(True)

    def _bind(self) -> None:
        self.Bind(wx.EVT_CHECKBOX, self.OnQuickDeal, self.cb_quickdeal)
        self.Bind(wx.EVT_CHECKBOX, self.OnAllQuickDeal, self.cb_allquickdeal)

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)

        bsizer_skip_and_wait = wx.StaticBoxSizer(self.box_skip_and_wait, wx.VERTICAL)
        bsizer_skip_and_wait.Add(self.cb_can_skipwait, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_can_skipanimation, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_can_skipwait_with_wheel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_can_forwardmessage_with_wheel, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_wait_usecard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_enlarge_beastcardzoomingratio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_skip_and_wait.Add(self.cb_autoenter_on_sprite, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_skip_and_wait, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_card = wx.StaticBoxSizer(self.box_card, wx.VERTICAL)
        bsizer_card.Add(self.cb_quickdeal, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_card.Add(self.cb_allquickdeal, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_card.Add(self.cb_showallselectedcards, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_card.Add(self.cb_show_cardkind, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_card.Add(self.cb_show_premiumicon, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_card.Add(self.panel_show_statustime, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_card, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_control = wx.StaticBoxSizer(self.box_control, wx.VERTICAL)
        # bsizer_control.Add(self.cb_spend_noeffectcard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_show_personal_cards, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_showbackpackcard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_showbackpackcardatend, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_revertcardpocket, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_showroundautostartbutton, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_showautobuttoninentrydialog, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_protect_staredcard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_protect_premiercard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.panel_confirm_dumpcard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_can_clicksidesofcardcontrol, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.cb_showlogwithwheelup, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_control.Add(self.panel_radius_notdetectmovement, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_control, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_confirm_and_description = wx.StaticBoxSizer(self.box_confirm_and_description, wx.VERTICAL)
        bsizer_confirm_and_description.Add(self.cb_show_btndesc, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_confirm_and_description.Add(self.cb_statusbarmask, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_confirm_and_description.Add(self.cb_blink_statusbutton, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_confirm_and_description.Add(self.cb_blink_partymoney, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_confirm_and_description, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_save_and_load = wx.StaticBoxSizer(self.box_save_and_load, wx.VERTICAL)
        bsizer_save_and_load.Add(self.panel_confirm_beforesaving, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_save_and_load.Add(self.cb_showsavedmessage, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_save_and_load.Add(self.cb_cautionbeforesaving, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_save_and_load, 0, wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_dialog = wx.StaticBoxSizer(self.box_dialog, wx.VERTICAL)
        bsizer_dialog.Add(self.cb_show_advancedsettings, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_dialog.Add(self.cb_show_addctrlbtn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_dialog.Add(self.cb_show_experiencebar, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_dialog.Add(self.cb_confirmbeforeusingcard, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_dialog.Add(self.cb_noticeimpossibleaction, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        sizer_2.Add(bsizer_dialog, 0, wx.EXPAND, cw.ppis(3))

        sizer.Add(sizer_2, 1, wx.ALL | wx.EXPAND, cw.ppis(10))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


class FontSettingPanel(wx.Panel):
    def __init__(self, parent: wx.Notebook, for_local: bool,
                 get_localsettings: Optional[Callable[[], cw.setting.LocalSetting]],
                 use_copybase: bool) -> None:
        wx.Panel.__init__(self, parent)
        self.SetDoubleBuffered(True)
        self._for_local = for_local
        self._get_localsettings = get_localsettings if get_localsettings else lambda: cw.cwpy.setting.local
        self.msg_exfonttypes = {"fw_symbol", "fw_number", "fw_latin", "hiragana", "katakana", "hw_katakana",
                                "greek_and_cyrillic", "jis_kanji_1", "jis_kanji_2", "etc_kanji", "symbol",
                                "number", "latin"}
        self.typenames = {"inherit": "指定しない",
                          "gothic": "等幅ゴシック",
                          "uigothic": "UI用",
                          "mincho": "等幅明朝",
                          "pmincho": "可変幅明朝",
                          "pgothic": "可変幅ゴシック",
                          "button": "ボタン",
                          "combo": "コンボボックス",
                          "slider": "スライダ",
                          "spin": "スピナ",
                          "tree": "ツリー",
                          "list": "リスト",
                          "tab": "タブ",
                          "menu": "メニュー",
                          "scenario": "貼紙見出し",
                          "targetlevel": "対象レベル",
                          "paneltitle": "パネル見出し1",
                          "paneltitle2": "パネル見出し2",
                          "dlgmsg": "ダイアログテキスト1",
                          "dlgmsg2": "ダイアログテキスト2",
                          "dlgtitle": "英文見出し1",
                          "dlgtitle2": "英文見出し2",
                          "createtitle": "登録見出し",
                          "inputname": "名前入力欄",
                          "datadesc": "データ解説文",
                          "charaparam": "キャラクター見出し1",
                          "charaparam2": "キャラクター見出し2",
                          "charadesc": "キャラクター解説文",
                          "characre": "キャラクター登録",
                          "dlglist": "ダイアログリスト",
                          "uselimit": "カード残り回数",
                          "cardname": "カード名",
                          "ccardname": "キャストカード名",
                          "level": "カードレベル",
                          "price": "カード価格",
                          "numcards": "カード枚数",
                          "message": "メッセージ",
                          "fw_symbol": " - 全角記号",
                          "fw_number": " - 全角数字",
                          "fw_latin": " - 全角英字",
                          "hiragana": " - ひらがな",
                          "katakana": " - カタカナ",
                          "hw_katakana": " - 半角カナ",
                          "greek_and_cyrillic": " - ギリシャ・キリル",
                          "jis_kanji_1": " - JIS第1水準漢字",
                          "jis_kanji_2": " - JIS第2水準漢字",
                          "etc_kanji": " - 外字",
                          "symbol": " - 半角記号",
                          "number": " - 半角数字",
                          "latin": " - 半角英字",
                          "selectionbar": "選択肢",
                          "logpage": "メッセージログ頁",
                          "sbarpanel": "ステータスパネル",
                          "sbarprogress": "進行状況・音量バー",
                          "sbarbtn": "ステータスボタン",
                          "sbardesctitle": "ボタン解説の表題",
                          "sbardesc": "ボタン解説",
                          "statusnum": "状態値",
                          "screenshot": "撮影情報",
                          }

        self.bases = ("gothic", "pgothic", "mincho", "pmincho", "uigothic")
        self.types = ("cardname", "ccardname", "level", "message",
                      "fw_symbol", "fw_number", "fw_latin", "hiragana", "katakana", "hw_katakana",
                      "greek_and_cyrillic", "jis_kanji_1", "jis_kanji_2", "etc_kanji", "symbol",
                      "number", "latin",
                      "selectionbar", "logpage", "uselimit", "price", "numcards", "statusnum",
                      "sbarpanel", "sbarprogress", "sbarbtn", "sbardesctitle", "sbardesc", "screenshot",
                      "scenario", "targetlevel", "paneltitle", "paneltitle2", "dlgmsg", "dlgmsg2", "dlgtitle",
                      "dlgtitle2", "createtitle", "dlglist", "inputname", "datadesc", "charadesc", "charaparam",
                      "charaparam2", "characre", "button", "combo", "slider", "spin", "tree", "list", "tab",
                      "menu")

        # フォント配列のロード
        facenames = list(wx.FontEnumerator().GetFacenames())
        faceset = set(facenames)
        cw.util.sort_by_attr(facenames)
        self.str_default = "[標準フォント]"  # デフォルトフォント名
        self._fontface_array = [self.str_default]
        self._has_default = [True] * len(self.bases)
        self._types: List[str] = []
        for base in self.bases:
            self._types.append("[%s]" % (self.typenames[base]))
        for name in facenames:
            if not name.startswith("@"):
                self._fontface_array.append(name)
                self._types.append(name)
        self._types_with_inherit = ["[%s]" % (self.typenames["inherit"])]
        self._types_with_inherit.extend(self._types)

        if self._for_local:
            self.cb_important = wx.CheckBox(self, -1, "このスキンのフォント設定を基本設定よりも優先して使用する")
        else:
            self.cb_important = None

        # フォント表示サンプル
        self.box_example = wx.StaticBox(self, -1, "表示例")
        if cw.cwpy:
            s = cw.cwpy.setting.fontexampleformat
            pixelsize = cw.cwpy.setting.fontexamplepixelsize
        else:
            s = cw.setting.FONT_EXAMPLE_FORMAT_INIT
            pixelsize = cw.setting.FONT_EXAMPLE_PIXEL_SIZE_INIT
        ln = 2
        self._example_panel = wx.Panel(self, -1, size=cw.ppis((100, 24*ln+11)), style=wx.NO_BORDER)
        self.st_example = wx.StaticText(self._example_panel, -1, style=wx.ALIGN_CENTER)
        self.st_example.SetDoubleBuffered(True)

        self.box_edit_example = wx.StaticBox(self, -1, "表示例のカスタマイズ")
        self.tx_example = wx.TextCtrl(self, -1, s, size=(-1, -1))
        self.tx_example.SetToolTip("%fontface% = フォント名\n\\% = %\n\\n = 改行\n\\\\ = \\")
        self.sc_example = wx.SpinCtrl(self, -1, "", size=(cw.ppis(50+_spin_w_addition), -1), min=8, max=32)
        self.sc_example.SetValue(pixelsize)
        self.btn_init_example = wx.Button(self, -1, "初期化", size=(cw.ppis(50), -1))

        # 描画オプション
        self.box_gene = wx.StaticBox(self, -1, "詳細")
        self.cb_bordering_cardname = wx.CheckBox(self, -1, "カード名を縁取りする")
        self.cb_decorationfont = wx.CheckBox(self, -1, "メッセージで装飾フォントを使用する")
        self.cb_fontsmoothingmessage = wx.CheckBox(self, -1, "メッセージの文字を滑らかにする")
        self.cb_fontsmoothingcardname = wx.CheckBox(self, -1, "カード名の文字を滑らかにする")
        self.cb_fontsmoothingstatusbar = wx.CheckBox(self, -1, "ステータスバーの文字を滑らかにする")

        def create_grid(grid: wx.grid.Grid, seq: Sequence[str], faces: Callable[[str], Iterable[str]], cols: int,
                        rowlblsize: int) -> List[wx.grid.GridCellChoiceEditor]:
            grid.CreateGrid(len(seq), cols)
            grid.DisableDragRowSize()
            grid.SetSelectionMode(wx.grid.Grid.SelectRows)
            grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)
            grid.SetRowLabelSize(rowlblsize)
            grid.SetColLabelValue(0, "フォント名")
            grid.SetColSize(0, cw.ppis(150))
            editors = []
            for i, name in enumerate(seq):
                editor = wx.grid.GridCellChoiceEditor(faces(name))
                grid.SetCellEditor(i, 0, editor)
                editors.append(editor)
            return editors

        # 基本フォント
        self.box_base = wx.StaticBox(self, -1, "基本フォント")
        self.base = wx.grid.Grid(self, -1, size=(-1, -1), style=wx.BORDER)
        self.base.SetDoubleBuffered(True)

        def has_defaultfont(name: str) -> bool:
            if name == "gothic":
                fname = "IPAゴシック"
            elif name == "pgothic":
                fname = "IPA Pゴシック"
            elif name == "uigothic":
                fname = "IPA UIゴシック"
            elif name == "mincho":
                fname = "IPA明朝"
            elif name == "pmincho":
                fname = "IPA P明朝"
            else:
                return False
            return fname in faceset

        def faces_from_basefont(name: str) -> Iterable[str]:
            if has_defaultfont(name):
                return self._fontface_array
            else:
                self._has_default[self.bases.index(name)] = False
                return self._fontface_array[1:]
        self.choicebases = create_grid(self.base, self.bases, faces_from_basefont, 1, cw.ppis(100))
        self.base.SetMinSize(self.base.GetBestSize())

        # 役割別フォント
        self.box_type = wx.StaticBox(self, -1, "役割別フォント")
        self.type = wx.grid.Grid(self, -1, size=(1, 0), style=wx.BORDER)
        self.type.SetDoubleBuffered(True)

        def get_choices(ftype: str) -> List[str]:
            if ftype in self.msg_exfonttypes:
                return self._types_with_inherit
            else:
                return self._types
        self.choicetypes = create_grid(self.type, self.types, get_choices, 5, cw.ppis(120))

        self.type.SetColLabelValue(1, "サイズ\n(ピクセル)")
        self.type.SetColSize(1, cw.ppis(80))
        self.type.SetColLabelValue(2, "太字\n(通常)")
        self.type.SetColSize(2, cw.ppis(70))
        self.type.SetColLabelValue(3, "太字\n(拡大)")
        self.type.SetColSize(3, cw.ppis(70))
        self.type.SetColLabelValue(4, "斜体")
        self.type.SetColSize(4, cw.ppis(70))
        local = cw.setting.LocalSetting()
        local.init()
        for i, name in enumerate(self.types):
            if name in self.msg_exfonttypes:
                _deffonttype, _defface, defpixels, defbold, defbold_upscr, defitalic = local.msg_exfonts_init[name]
            else:
                _deffonttype, _defface, defpixels, defbold, defbold_upscr, defitalic = local.fonttypes_init[name]
            if 0 < defpixels:
                self.type.SetCellEditor(i, 1, wx.grid.GridCellNumberEditor(1, 99))
                self.type.SetCellRenderer(i, 1, wx.grid.GridCellNumberRenderer())
            else:
                self.type.GetOrCreateCellAttr(i, 1).SetReadOnly(True)
            self.type.SetCellAlignment(i, 1, wx.ALIGN_CENTER, 0)
            if defbold is not None:
                self.type.SetCellEditor(i, 2, wx.grid.GridCellBoolEditor())
                self.type.SetCellRenderer(i, 2, wx.grid.GridCellBoolRenderer())
            else:
                self.type.GetOrCreateCellAttr(i, 2).SetReadOnly(True)
            self.type.SetCellAlignment(i, 2, wx.ALIGN_CENTER, 0)
            if defbold_upscr is not None:
                self.type.SetCellEditor(i, 3, wx.grid.GridCellBoolEditor())
                self.type.SetCellRenderer(i, 3, wx.grid.GridCellBoolRenderer())
            else:
                self.type.GetOrCreateCellAttr(i, 3).SetReadOnly(True)
            self.type.SetCellAlignment(i, 3, wx.ALIGN_CENTER, 0)
            if defitalic is not None:
                self.type.SetCellEditor(i, 4, wx.grid.GridCellBoolEditor())
                self.type.SetCellRenderer(i, 4, wx.grid.GridCellBoolRenderer())
            else:
                self.type.GetOrCreateCellAttr(i, 4).SetReadOnly(True)
            self.type.SetCellAlignment(i, 4, wx.ALIGN_CENTER, 0)

        if self._for_local:
            if use_copybase:
                self.copybtn = wx.Button(self, -1, "基本設定をコピー")
            else:
                self.copybtn = None
            self.initbtn = wx.Button(self, -1, "デフォルト")

        self._last_face = self.get_basefontface(self.bases[0])

        self._do_layout()
        self._bind()

    def load(self, setting: Optional[cw.setting.Setting], local: cw.setting.LocalSetting) -> None:
        if self._for_local:
            self.cb_important.SetValue(local.important_font)
        if setting:
            self.tx_example.SetValue(setting.fontexampleformat)
            self.sc_example.SetValue(setting.fontexamplepixelsize)
        self.cb_bordering_cardname.SetValue(local.bordering_cardname)
        self.cb_decorationfont.SetValue(local.decorationfont)
        self.cb_fontsmoothingmessage.SetValue(local.fontsmoothing_message)
        self.cb_fontsmoothingcardname.SetValue(local.fontsmoothing_cardname)
        self.cb_fontsmoothingstatusbar.SetValue(local.fontsmoothing_statusbar)

        def create_grid(grid: wx.grid.Grid, seq: Iterable[str]) -> None:
            for i, name in enumerate(seq):
                grid.SetRowLabelValue(i, self.typenames[name])

        create_grid(self.base, self.bases)
        for i, name, in enumerate(self.bases):
            str_font = local.basefont[name]
            if not str_font:
                str_font = self.str_default if self._has_default[i] else "**フォントが見つかりません**"
            self.base.SetCellValue(i, 0, str_font)

        create_grid(self.type, self.types)

        self.type.SetColLabelValue(1, "サイズ\n(ピクセル)")
        self.type.SetColSize(1, cw.ppis(80))
        self.type.SetColLabelValue(2, "太字\n(通常)")
        self.type.SetColSize(2, cw.ppis(70))
        self.type.SetColLabelValue(3, "太字\n(拡大)")
        self.type.SetColSize(3, cw.ppis(70))
        self.type.SetColLabelValue(4, "斜体")
        self.type.SetColSize(4, cw.ppis(70))
        dc = wx.ClientDC(self.type)
        self.type.SetColLabelSize(max(self.type.GetColLabelSize(), dc.GetTextExtent("#\n#")[1] * 2))

        for i, name, in enumerate(self.bases):
            str_font = local.basefont[name]
            if not str_font:
                str_font = self.str_default if self._has_default[i] else "**フォントが見つかりません**"
            self.base.SetCellValue(i, 0, str_font)

        for i, name in enumerate(self.types):
            if name in self.msg_exfonttypes:
                _deffonttype, _defface, defpixels, defbold, defbold_upscr, defitalic = local.msg_exfonts_init[name]
                fonttype, face, pixels, bold, bold_upscr, italic = local.msg_exfonts[name]
            else:
                _deffonttype, _defface, defpixels, defbold, defbold_upscr, defitalic = local.fonttypes_init[name]
                fonttype, face, pixels, bold, bold_upscr, italic = local.fonttypes[name]
            if fonttype:
                self.type.SetCellValue(i, 0, "[%s]" % (self.typenames[fonttype]))
            else:
                self.type.SetCellValue(i, 0, face)

            if 0 < defpixels:
                self.type.SetCellValue(i, 1, str(pixels))
            else:
                self.type.SetCellValue(i, 1, "-")
            if defbold is not None:
                self.type.SetCellValue(i, 2, "1" if bold else "")
            else:
                self.type.SetCellValue(i, 2, "-")

            if defbold_upscr is not None:
                self.type.SetCellValue(i, 3, "1" if bold_upscr else "")
            else:
                self.type.SetCellValue(i, 3, "-")
            if defitalic is not None:
                self.type.SetCellValue(i, 4, "1" if italic else "")
            else:
                self.type.SetCellValue(i, 4, "-")

            self._update_rowcolour(fonttype, i)

        self._select_base(self.base.GetGridCursorRow())

        self._last_face = self.get_basefontface(self.bases[0])
        self.update_example()
        self._update_enabled()
        self.Layout()

    def update_example(self) -> None:
        s = self.tx_example.GetValue()
        pixelsize = self.sc_example.GetValue()
        if cw.cwpy:
            cw.cwpy.setting.fontexampleformat = s
            cw.cwpy.setting.fontexamplepixelsize = pixelsize
        font = wx.Font(wx.Size(0, pixelsize), family=wx.DEFAULT, style=wx.FONTSTYLE_NORMAL,
                       weight=wx.FONTWEIGHT_NORMAL, faceName=self._last_face)
        self.st_example.SetFont(font)
        s = cw.util.format_title(s, {"fontface": self._last_face}, use_lf=True)
        self.st_example.SetLabel(s)
        self._example_panel.Layout()

    def _update_rowcolour(self, fonttype: str, row: int) -> None:
        if fonttype == "inherit":
            for col in range(1, 5):
                self.type.SetCellBackgroundColour(row, col, self.type.LabelBackgroundColour)
        else:
            colour = self.type.GetCellBackgroundColour(row, 0)
            for col in range(1, 5):
                self.type.SetCellBackgroundColour(row, col, colour)

    def init_values(self, setting: Optional[cw.setting.Setting], local: cw.setting.LocalSetting) -> None:
        if setting:
            self.tx_example.SetValue(setting.fontexampleformat_init)
            self.sc_example.SetValue(setting.fontexamplepixelsize_init)

        for i, basename in enumerate(self.bases):
            name = local.basefont_init[basename]
            if not name:
                name = self.str_default if self._has_default[i] else "**フォントが見つかりません**"
            self.base.SetCellValue(i, 0, name)
        for i, typename in enumerate(self.types):
            if typename in self.msg_exfonttypes:
                fonttype, name, pixels, bold, bold_upscr, italic = local.msg_exfonts_init[typename]
            else:
                fonttype, name, pixels, bold, bold_upscr, italic = local.fonttypes_init[typename]
            if fonttype:
                name = "[%s]" % (self.typenames[fonttype])
            self.type.SetCellValue(i, 0, name)
            self.type.SetCellValue(i, 1, str(pixels) if 0 < pixels else "-")
            self.type.SetCellValue(i, 2, ("1" if bold else "") if bold is not None else "-")
            self.type.SetCellValue(i, 3, ("1" if bold_upscr else "") if bold_upscr is not None else "-")
            self.type.SetCellValue(i, 4, ("1" if italic else "") if italic is not None else "-")
            self._update_rowcolour(fonttype, i)

        self.cb_bordering_cardname.SetValue(local.bordering_cardname_init)
        self.cb_decorationfont.SetValue(local.decorationfont_init)
        self.cb_fontsmoothingmessage.SetValue(local.fontsmoothing_message_init)
        self.cb_fontsmoothingcardname.SetValue(local.fontsmoothing_cardname_init)
        self.cb_fontsmoothingstatusbar.SetValue(local.fontsmoothing_statusbar_init)

        self.update_example()

    def apply_localsettings(self, local: cw.setting.LocalSetting) -> Tuple[bool, bool, bool, bool]:
        updatecardimg = False  # キャラクターカードイメージの更新が必要か
        updatemcardimg = False  # メニューカードイメージの更新が必要か
        updatemessage = False  # メッセージの更新が必要か
        flag_fontupdate = False  # フォントの変更があるか

        value = self.cb_bordering_cardname.GetValue()
        if local.bordering_cardname != value:
            local.bordering_cardname = value
            updatecardimg = True
            updatemcardimg = True
        value = self.cb_decorationfont.GetValue()
        if value != local.decorationfont:
            local.decorationfont = value
            updatemessage = True
        value = self.cb_fontsmoothingmessage.GetValue()
        if value != local.fontsmoothing_message:
            local.fontsmoothing_message = value
            updatemessage = True
        value = self.cb_fontsmoothingcardname.GetValue()
        if value != local.fontsmoothing_cardname:
            local.fontsmoothing_cardname = value
            flag_fontupdate = True
        value = self.cb_fontsmoothingstatusbar.GetValue()
        if value != local.fontsmoothing_statusbar:
            local.fontsmoothing_statusbar = value
            flag_fontupdate = True

        basetable = {}
        basefont = {}
        for i, basename in enumerate(self.bases):
            value = self.base.GetCellValue(i, 0)
            if value == self.str_default or value == "**フォントが見つかりません**":
                value = ""
            basefont[basename] = value
            basetable["[%s]" % (self.typenames[basename])] = basename
        basetable_with_inherit = basetable.copy()
        basetable_with_inherit["[%s]" % (self.typenames["inherit"])] = "inherit"
        fonttypes: Dict[str, Tuple[str, str, int, bool, bool, bool]] = {}
        msg_exfonts: Dict[str, Tuple[str, str, int, bool, bool, bool]] = {}
        for i, typename in enumerate(self.types):
            value = self.type.GetCellValue(i, 0)
            pixels = self.type.GetCellValue(i, 1)
            try:
                if pixels != "-":
                    pixels = int(pixels)
                else:
                    pixels = -1
            except Exception:
                pixels = -1
            bold = self.type.GetCellValue(i, 2)
            if bold in ("1", ""):
                bold = bold == "1"
            else:
                bold = None
            bold_upscr = self.type.GetCellValue(i, 3)
            if bold_upscr in ("1", ""):
                bold_upscr = bold_upscr == "1"
            else:
                bold_upscr = None
            italic = self.type.GetCellValue(i, 4)
            if italic in ("1", ""):
                italic = italic == "1"
            else:
                italic = None
            if typename in self.msg_exfonttypes:
                table = msg_exfonts
                fonttype = basetable_with_inherit.get(value, "")
            else:
                table = fonttypes
                fonttype = basetable.get(value, "")
            if fonttype:
                table[typename] = (fonttype, "", pixels, bold, bold_upscr, italic)
            else:
                table[typename] = ("", value, pixels, bold, bold_upscr, italic)

        # フォント変更チェック
        if basefont != local.basefont:
            local.basefont = basefont
            flag_fontupdate = True
        if fonttypes != local.fonttypes:
            local.fonttypes = fonttypes
            flag_fontupdate = True
        if msg_exfonts != local.msg_exfonts:
            local.msg_exfonts = msg_exfonts
            flag_fontupdate = True

        if self.cb_important and self.cb_important.GetValue() != local.important_font:
            local.important_font = self.cb_important.GetValue()
            flag_fontupdate = True

        return flag_fontupdate, updatecardimg, updatemcardimg, updatemessage

    def _bind(self) -> None:
        self.tx_example.Bind(wx.EVT_TEXT, self.OnExampleText)
        self.sc_example.Bind(wx.EVT_SPINCTRL, self.OnExampleText)
        self.btn_init_example.Bind(wx.EVT_BUTTON, self.OnInitExample)
        self.base.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectFontBase)
        self.base.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnCellChangeBase)
        self.base.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnEditorCreatedBase)
        self.type.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectFontType)
        self.type.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnCellChangeType)
        self.type.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnEditorCreatedType)
        if self._for_local:
            self.cb_important.Bind(wx.EVT_CHECKBOX, self.OnImportant)
            if self.copybtn:
                self.copybtn.Bind(wx.EVT_BUTTON, self.OnCopyBase)
            self.initbtn.Bind(wx.EVT_BUTTON, self.OnInitValue)

    def _select_base(self, i: int) -> None:
        if 0 <= i:
            self._last_face = self.get_basefontface(self.bases[i])
            self.update_example()

    def OnExampleText(self, event: wx.CommandEvent) -> None:
        self.update_example()

    def OnInitExample(self, event: wx.CommandEvent) -> None:
        self.tx_example.SetValue(cw.setting.FONT_EXAMPLE_FORMAT_INIT)
        self.sc_example.SetValue(cw.setting.FONT_EXAMPLE_PIXEL_SIZE_INIT)
        self.update_example()

    def OnCellChangeBase(self, event: wx.grid.GridEvent) -> None:
        self._select_base(self.base.GetGridCursorRow())

    def OnSelectFontBase(self, event: wx.grid.GridEvent) -> None:
        def func(self: FontSettingPanel) -> None:
            if self:
                self._select_base(self.base.GetGridCursorRow())
        wx.CallAfter(func, self)
        event.Skip()

    def OnEditorCreatedBase(self, event: wx.grid.GridEvent) -> None:
        for editor in self.choicebases:
            if editor.GetControl():
                editor.GetControl().Bind(wx.EVT_COMBOBOX, self.OnCellChangeBase)

    def get_basefontface(self, fonttype: str) -> str:
        editors = [choice for choice in self.choicebases if choice.GetControl() and choice.GetControl().IsShown()]
        if editors:
            face: str = editors[0].GetControl().GetValue()
        else:
            face = self.base.GetCellValue(self.bases.index(fonttype), 0)
        if face == self.str_default:
            if cw.cwpy:
                d = cw.cwpy.rsrc.fontnames_init
            else:
                d = {"gothic": "IPAゴシック",
                     "uigothic": "IPA UIゴシック",
                     "mincho": "IPA明朝",
                     "pmincho": "IPA P明朝",
                     "pgothic": "IPA Pゴシック"}

            face = d.get(fonttype, "")

        return face

    def _select_type(self, i: int) -> None:
        if 0 <= i:
            self._last_face = self.get_typefontface(self.types[i])
            self.update_example()

    def OnCellChangeType(self, event: wx.grid.GridEvent) -> None:
        i = self.type.GetGridCursorRow()
        self._select_type(i)
        value = self.type.GetCellValue(i, self.type.GetGridCursorCol())
        self._update_rowcolour("inherit" if ("[%s]" % self.typenames["inherit"]) == value else "", i)

    def OnSelectFontType(self, event: wx.grid.GridEvent) -> None:
        def func(self: FontSettingPanel) -> None:
            if self:
                self._select_type(self.type.GetGridCursorRow())
        wx.CallAfter(func, self)
        event.Skip()

    def OnEditorCreatedType(self, event: wx.grid.GridEvent) -> None:
        for editor in self.choicetypes:
            ctrl = editor.GetControl()
            if ctrl:
                ctrl.Bind(wx.EVT_COMBOBOX, self.OnCellChangeType)

    def get_typefontface(self, fonttype: str, refeditors: bool = True) -> str:
        if refeditors:
            editors = [choice for choice in self.choicetypes if choice.GetControl() and choice.GetControl().IsShown()]
        else:
            editors = []
        if editors:
            face: str = editors[0].GetControl().GetValue()
        else:
            face = self.type.GetCellValue(self.types.index(fonttype), 0)
        for basename in self.bases:
            if "[%s]" % self.typenames[basename] == face:
                face = self.get_basefontface(basename)
                break
        else:
            if "[%s]" % self.typenames["inherit"] == face:
                face = self.get_typefontface("message", False)
        return face

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        bsizer_top = wx.BoxSizer(wx.HORIZONTAL)

        bsizer_left = wx.BoxSizer(wx.VERTICAL)

        bsizer_example = wx.StaticBoxSizer(self.box_example, wx.VERTICAL)
        bsizer_example2 = wx.BoxSizer(wx.VERTICAL)
        bsizer_example2.Add(self.st_example, 1, wx.ALIGN_CENTER, cw.ppis(0))
        self._example_panel.SetSizer(bsizer_example2)
        bsizer_example.Add(self._example_panel, 1, wx.EXPAND | wx.ALL, cw.ppis(3))

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_gene.Add(self.cb_bordering_cardname, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_decorationfont, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(3))
        bsizer_gene.Add(self.cb_fontsmoothingmessage, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, cw.ppis(3))
        bsizer_gene.Add(self.cb_fontsmoothingcardname, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, cw.ppis(3))
        bsizer_gene.Add(self.cb_fontsmoothingstatusbar, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, cw.ppis(3))

        bsizer_left.Add(bsizer_example, 1, wx.EXPAND | wx.BOTTOM, cw.ppis(3))
        bsizer_left.Add(bsizer_gene, 0, wx.EXPAND, cw.ppis(3))

        bsizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_edit_example = wx.StaticBoxSizer(self.box_edit_example, wx.VERTICAL)
        bsizer_edit_example2 = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_edit_example2.Add(self.tx_example, 1, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(2))
        bsizer_edit_example2.Add(self.sc_example, 0, wx.ALIGN_CENTER | wx.RIGHT, cw.ppis(2))
        bsizer_edit_example2.Add(self.btn_init_example, 0, wx.ALIGN_CENTER, cw.ppis(0))
        bsizer_edit_example.Add(bsizer_edit_example2, 1, wx.EXPAND | wx.ALL, cw.ppis(3))

        bsizer_base = wx.StaticBoxSizer(self.box_base, wx.VERTICAL)
        bsizer_base.Add(self.base, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        bsizer_right.Add(bsizer_edit_example, 1, wx.EXPAND | wx.BOTTOM, cw.ppis(3))
        bsizer_right.Add(bsizer_base, 0, wx.EXPAND, cw.ppis(3))

        bsizer_top.Add(bsizer_left, 1, wx.EXPAND | wx.RIGHT, cw.ppis(5))
        bsizer_top.Add(bsizer_right, 1, wx.EXPAND, cw.ppis(3))

        bsizer_type = wx.StaticBoxSizer(self.box_type, wx.VERTICAL)
        bsizer_type.Add(self.type, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, cw.ppis(3))

        if self.cb_important:
            sizer_v1.Add(self.cb_important, 0, wx.BOTTOM, cw.ppis(5))
        sizer_v1.Add(bsizer_top, 0, wx.EXPAND | wx.BOTTOM, cw.ppis(3))
        sizer_v1.Add(bsizer_type, 1, wx.EXPAND, cw.ppis(0))

        if self._for_local:
            sizer_v1.AddStretchSpacer(0)
            bsizer_btn = wx.BoxSizer(wx.HORIZONTAL)
            if self.copybtn:
                bsizer_btn.Add(self.copybtn, 0, wx.RIGHT, cw.ppis(3))
            bsizer_btn.Add(self.initbtn, 0, 0, cw.ppis(0))
            sizer_v1.Add(bsizer_btn, 0, wx.ALIGN_RIGHT | wx.TOP, cw.ppis(5))

        sizer.Add(sizer_v1, 1, wx.ALL | wx.EXPAND, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnImportant(self, event: wx.CommandEvent) -> None:
        self._update_enabled()

    def _update_enabled(self) -> None:
        enbl = self.cb_important.GetValue() if self.cb_important else True
        self.base.Enable(enbl)
        self.type.Enable(enbl)
        self.tx_example.Enable(enbl)
        self.sc_example.Enable(enbl)
        self.btn_init_example.Enable(enbl)
        self.cb_bordering_cardname.Enable(enbl)
        self.cb_decorationfont.Enable(enbl)
        self.cb_fontsmoothingmessage.Enable(enbl)
        self.cb_fontsmoothingcardname.Enable(enbl)
        self.cb_fontsmoothingstatusbar.Enable(enbl)
        if self._for_local:
            if self.copybtn:
                self.copybtn.Enable(enbl)
            self.initbtn.Enable(enbl)

    def OnInitValue(self, event: wx.CommandEvent) -> None:
        local = cw.setting.LocalSetting()
        local.init()
        self.init_values(None, local)

    def OnCopyBase(self, event: wx.CommandEvent) -> None:
        local = self._get_localsettings()
        local.init()
        local.important_font = True
        self.load(None, local)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
