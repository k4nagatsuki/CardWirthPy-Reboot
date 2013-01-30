#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import wx.aui

import cw


class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"設定")
        self.note = wx.Notebook(self)
        self.pane_gene = GeneralSettingPanel(self.note)
        self.pane_draw = DrawingSettingPanel(self.note)
        self.pane_sound = AudioSettingPanel(self.note)
        self.pane_color = ColorSettingPanel(self.note)
        self.note.AddPage(self.pane_gene, u"一般")
        self.note.AddPage(self.pane_draw, u"描画")
        self.note.AddPage(self.pane_sound, u"オーディオ")
        self.note.AddPage(self.pane_color, u"配色")
        self.btn_ok = wx.Button(self, wx.ID_OK, u"OK")
        self.btn_cncl = wx.Button(self, wx.ID_CANCEL, u"キャンセル")
        self.btn_dflt = wx.Button(self, wx.ID_DEFAULT, u"デフォルト")
        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnDefault, id=wx.ID_DEFAULT)

    def OnDefault(self, event):
        self.pane_draw.cb_smooth_bg.SetValue(False)
        self.pane_draw.sl_deal.SetValue(6)
        self.pane_draw.sl_msgs.SetValue(4)
        self.pane_draw.ch_tran.SetSelection(0)
        self.pane_draw.sl_tran.SetValue(5)
        self.pane_sound.sl_sound.SetValue(100)
        self.pane_sound.sl_midi.SetValue(20)
        self.pane_sound.sl_music.SetValue(100)
        self.pane_color.sc_mwin.SetValue(180)
        self.pane_color.cs_mwin.SetColour((0, 0, 80))
        self.pane_color.sc_mframe.SetValue(255)
        self.pane_color.cs_mframe.SetColour((128, 0, 0))

    def OnOk(self, event):
        # 一般
        value = self.pane_gene.cb_debug.GetValue()

        if not value == cw.cwpy.setting.debug:
            cw.cwpy.setting.debug = value
            cw.cwpy.debug = value
            cw.cwpy.statusbar.change()

            if cw.cwpy.is_showingdebugger():
                cw.cwpy.sounds["page"].play()
                cw.cwpy.frame.debugger.Close()

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
        # 配色
        alpha = self.pane_color.sc_mwin.GetValue()
        colour = self.pane_color.cs_mwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.mwincolour = colour
        alpha = self.pane_color.sc_mframe.GetValue()
        colour = self.pane_color.cs_mframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.mwinframecolour = colour
        # スキン
        skin = self.pane_gene.ch_skin.GetSelection()
        skin = self.pane_gene.skins[skin]

        if cw.cwpy.setting.skindirname == skin:
            self.Close()
        else:
            if cw.cwpy.status == "Title":
                self.Close()
                cw.cwpy.setting.skindirname = skin
                cw.cwpy.setting.write()
                cw.cwpy.setting.init_settings()
                cw.cwpy.init_pygame(cw.cwpy.setting)
            else:
                s = (u"スキンの変更にはゲームの中断が必要です。\n"
                    u"保存されていないデータは全て消えてしまいます。\n"
                    u"タイトル画面へ戻ってよろしいですか？")
                dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                cw.cwpy.frame.move_dlg(dlg)
                cw.cwpy.sounds["signal"].play()

                if dlg.ShowModal() == wx.ID_OK:
                    self.Close()
                    cw.cwpy.setting.skindirname = skin
                    cw.cwpy.setting.write()
                    cw.cwpy.setting.init_settings()
                    cw.cwpy.init_pygame(cw.cwpy.setting)
                else:
                    n = self.pane_gene.skins.index(cw.cwpy.setting.skindirname)
                    self.pane_gene.ch_skin.SetSelection(n)
                    self.pane_gene.OnSkinChoice(None)

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
                except Exception, ex:
                    # エラーのあるスキンは無視
                    print ex

        self.ch_skin = wx.Choice(self, -1, size=(120, -1), choices=self.skins)
        n = self.skins.index(cw.cwpy.setting.skindirname)
        self.ch_skin.SetSelection(n)
        s = u"種別: %s\n名前: %s\n作者: %s\n" + "-" * 45 + "\n%s"
        s = s % self.skin_summarys[cw.cwpy.setting.skindirname]
        self.st_skin = wx.StaticText(self, -1, s)
        self._do_layout()
        self._bind()

    def _bind(self):
        self.cb_debug.Bind(wx.EVT_CHECKBOX, self.OnDebugCheck)
        self.ch_skin.Bind(wx.EVT_CHOICE, self.OnSkinChoice)

    def OnDebugCheck(self, event):
        if cw.cwpy.is_playingscenario():
            self.cb_debug.SetValue(not self.cb_debug.GetValue())
            dlg = cw.dialog.message.Message(
                self.Parent.Parent, cw.cwpy.msgs["message"],
                u"シナリオプレイ中はデバッグモードの切替はできません。")
            cw.cwpy.frame.move_dlg(dlg)
            cw.cwpy.sounds["error"].play()
            dlg.ShowModal()

    def OnSkinChoice(self, event):
        skin = self.skins[self.ch_skin.GetSelection()]
        s = u"種別: %s\n名前: %s\n作者: %s\n" + "-" * 45 + "\n%s"
        self.st_skin.SetLabel(s % self.skin_summarys[skin])

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_skin = wx.StaticBoxSizer(self.box_skin, wx.VERTICAL)

        bsizer_gene.Add(self.cb_debug, 0, wx.ALL, 3)
        bsizer_skin.Add(self.ch_skin, 0, wx.CENTER, 0)
        bsizer_skin.Add(self.st_skin, 0, wx.CENTER|wx.ALL, 3)
        bsizer_skin.SetMinSize((280, 200))

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_skin, 0, 0, 0)
        sizer.Add(sizer_v1, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class DrawingSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # 背景拡大縮小補正
        self.box_gene = wx.StaticBox(self, -1, "")
        self.cb_smooth_bg = wx.CheckBox(
            self, -1, u"拡大縮小した背景画像を滑らかにする")
        self.cb_smooth_bg.SetValue(cw.cwpy.setting.smoothscale_bg)
        # トランジション効果
        self.box_tran = wx.StaticBox(
            self, -1, u"背景の切り替え方式（速い⇔遅い）")
        self.transitions = [
            "None", "Fade", "PixelDissolve", "Blinds"]
        self.choices_tran = [
            u"アニメーションなし", u"フェード式",
            u"ピクセルディゾルブ式", u"ブラインド式"]
        self.ch_tran = wx.Choice(
            self, -1, size=(120, -1), choices=self.choices_tran)
        n = self.transitions.index(cw.cwpy.setting.transition)
        self.ch_tran.SetSelection(n)
        self.sl_tran = wx.Slider(
            self, -1, cw.cwpy.setting.transitionspeed, 0, 10,
            size=(250, -1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_tran.SetTickFreq(1, 1)
        # カード描画速度
        self.box_deal = wx.StaticBox(
            self, -1, u"カード描画速度（速い⇔遅い）")
        self.sl_deal = wx.Slider(
            self, -1, cw.cwpy.setting.dealspeed - 1, 0, 10, size=(250, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_deal.SetTickFreq(1, 1)
        # メッセージ表示速度
        self.box_msgs = wx.StaticBox(
            self, -1, u"メッセージ表示速度（速い⇔遅い）")
        self.sl_msgs = wx.Slider(
            self, -1, cw.cwpy.setting.messagespeed, 0, 10, size=(250, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_msgs.SetTickFreq(1, 1)
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
        bsizer_tran.Add(self.ch_tran, 0, wx.BOTTOM, 5)
        bsizer_tran.Add(self.sl_tran, 0, 0, 0)
        bsizer_deal.Add(self.sl_deal, 0, 0, 0)
        bsizer_msgs.Add(self.sl_msgs, 0, 0, 0)

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_tran, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_deal, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_msgs, 0, wx.BOTTOM, 5)
        sizer.Add(sizer_v1, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class AudioSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # 音量
        self.box_music = wx.StaticBox(self, -1, u"ミュージック音量")
        n = int(cw.cwpy.setting.vol_bgm * 100)
        self.sl_music = wx.Slider(
            self, -1, n, 0, 100, size=(250, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_music.SetTickFreq(10, 1)
        # midi音量
        self.box_midi = wx.StaticBox(self, -1, u"MIDIミュージック音量")
        n = int(cw.cwpy.setting.vol_midi * 100)
        self.sl_midi = wx.Slider(
            self, -1, n, 0, 100, size=(250, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_midi.SetTickFreq(10, 1)
        # 効果音音量
        self.box_sound = wx.StaticBox(self, -1, u"サウンド音量")
        n = int(cw.cwpy.setting.vol_sound * 100)
        self.sl_sound = wx.Slider(
            self, -1, n, 0, 100, size=(250, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.sl_sound.SetTickFreq(10, 1)
        self._do_layout()
        self._bind()

    def _bind(self):
        pass

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_music = wx.StaticBoxSizer(self.box_music, wx.VERTICAL)
        bsizer_midi = wx.StaticBoxSizer(self.box_midi, wx.VERTICAL)
        bsizer_sound = wx.StaticBoxSizer(self.box_sound, wx.VERTICAL)

        bsizer_music.Add(self.sl_music, 0, 0, 0)
        bsizer_midi.Add(self.sl_midi, 0, 0, 0)
        bsizer_sound.Add(self.sl_sound, 0, 0, 0)

        sizer_v1.Add(bsizer_music, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_midi, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_sound, 0, 0, 0)

        sizer.Add(sizer_v1, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class ColorSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # メッセージウィンドウ背景色
        self.box_mwin = wx.StaticBox(self, -1, u"メッセージウィンドウ背景")
        self.st_mwin = wx.StaticText(self, -1, u"カラー:")
        self.cs_mwin = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.mwincolour)
        self.st_mwin2 = wx.StaticText(self, -1, u"アルファ値:")
        self.sc_mwin = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.sc_mwin.SetRange(0, 255)
        self.sc_mwin.SetValue(cw.cwpy.setting.mwincolour[3])
        # メッセージウィンドウ枠色
        self.box_mframe = wx.StaticBox(self, -1, u"メッセージウィンドウ枠")
        self.st_mframe = wx.StaticText(self, -1, u"カラー:")
        self.cs_mframe = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.mwinframecolour)
        self.st_mframe2 = wx.StaticText(self, -1, u"アルファ値:")
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
        bsizer_mwin = wx.StaticBoxSizer(self.box_mwin, wx.HORIZONTAL)
        bsizer_mframe = wx.StaticBoxSizer(self.box_mframe, wx.HORIZONTAL)

        bsizer_mwin.Add(self.st_mwin, 0, wx.CENTER|wx.RIGHT, 3)
        bsizer_mwin.Add(self.cs_mwin, 0, wx.RIGHT, 15)
        bsizer_mwin.Add(self.st_mwin2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mwin.Add(self.sc_mwin, 0, wx.RIGHT, 15)
        bsizer_mframe.Add(self.st_mframe, 0, wx.CENTER|wx.RIGHT, 3)
        bsizer_mframe.Add(self.cs_mframe, 0, wx.RIGHT, 15)
        bsizer_mframe.Add(self.st_mframe2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mframe.Add(self.sc_mframe, 0, wx.RIGHT, 15)

        sizer_v1.Add(bsizer_mwin, 0, wx.BOTTOM, 5)
        sizer_v1.Add(bsizer_mframe, 0, 0, 0)
        sizer.Add(sizer_v1, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
