#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import itertools
import wx.grid
import pygame

import cw


SETTINGS_WIDTH = 250

class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"設定")
        self.cwpy_debug = True
        self.note = wx.Notebook(self)
        self.pane_gene = GeneralSettingPanel(self.note)
        self.pane_draw = DrawingSettingPanel(self.note)
        self.pane_sound = AudioSettingPanel(self.note)
        self.pane_font = FontSettingPanel(self.note)
        self.pane_scenario = ScenarioSettingPanel(self.note)
        self.pane_ui = UISettingPanel(self.note)
        self.note.AddPage(self.pane_gene, u"一般")
        self.note.AddPage(self.pane_draw, u"描画")
        self.note.AddPage(self.pane_sound, u"音声")
        self.note.AddPage(self.pane_font, u"フォント")
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
            self.pane_gene.cb_nolevelup.SetValue(cw.cwpy.setting.no_levelup_in_debugmode_init)
            self.pane_gene.cb_storeskinoneachbase.SetValue(cw.cwpy.setting.store_skinoneachbase_init)
            self.pane_gene.sc_backlogmax.SetValue(cw.cwpy.setting.backlogmax_init)
            if cw.cwpy.setting.expandmode_init == "FullScreen":
                self.pane_gene.cb_fullscreen.SetValue(True)
            else:
                self.pane_gene.ch_expanddrawing.SetSelection(int(cw.cwpy.setting.expandmode_init)-1)
                self.pane_gene.cb_fullscreen.SetValue(False)
            self.pane_gene.makeExpandInfo()
            self.pane_gene.cb_smoothexpand.SetValue(cw.cwpy.setting.smoothexpand_init)
            self.pane_gene.sc_initmoneyamount.SetValue(cw.cwpy.setting.initmoneyamount_init)
            self.pane_gene.cb_autosavepartyrecord.SetValue(cw.cwpy.setting.autosave_partyrecord_init)
            self.pane_gene.cb_overwritepartyrecord.SetValue(cw.cwpy.setting.overwrite_partyrecord_init)
            self.pane_gene.cb_overwritepartyrecord.Enable(self.pane_gene.cb_autosavepartyrecord.GetValue())
            self.pane_gene.tx_ssinfoformat.SetValue(cw.cwpy.setting.ssinfoformat_init)
            self.pane_gene.ch_ssinfocolor.Select(1 if cw.cwpy.setting.ssinfofontcolor_init[:3] == (255, 255, 255) else 0)
            self.pane_gene.cb_showexperiencebar.SetValue(cw.cwpy.setting.show_experiencebar_init)
        elif selpane == 1:
            self.pane_draw.cb_smooth_bg.SetValue(cw.cwpy.setting.smoothscale_bg_init)
            self.pane_draw.cb_statusbarmask.SetValue(cw.cwpy.setting.statusbarmask_init)
            self.pane_draw.cb_decorationfont.SetValue(cw.cwpy.setting.decorationfont_init)
            self.pane_draw.sl_deal.SetValue(cw.cwpy.setting.dealspeed_init)
            self.pane_draw.sl_msgs.SetValue(cw.cwpy.setting.messagespeed_init)
            self.pane_draw.ch_tran.SetSelection(self.pane_draw.transitions.index(cw.cwpy.setting.transition_init))
            self.pane_draw.sl_tran.SetValue(cw.cwpy.setting.transitionspeed_init)
            self.pane_draw.sc_mwin.SetValue(cw.cwpy.setting.mwincolour_init[3])
            self.pane_draw.cs_mwin.SetColour(cw.cwpy.setting.mwincolour_init[:3])
            self.pane_draw.sc_mframe.SetValue(cw.cwpy.setting.mwinframecolour_init[3])
            self.pane_draw.cs_mframe.SetColour(cw.cwpy.setting.mwinframecolour_init[:3])
            self.pane_draw.cs_blwin.SetColour(cw.cwpy.setting.blwincolour_init[:3])
            self.pane_draw.cs_blframe.SetColour(cw.cwpy.setting.blwinframecolour_init[:3])
            self.pane_draw.sc_blcurtain.SetValue(cw.cwpy.setting.blcurtaincolour_init[3])
            self.pane_draw.cs_blcurtain.SetColour(cw.cwpy.setting.blcurtaincolour_init[:3])
            self.pane_draw.sc_curtain.SetValue(cw.cwpy.setting.curtaincolour_init[3])
            self.pane_draw.cs_curtain.SetColour(cw.cwpy.setting.curtaincolour_init[:3])

            if cw.cwpy.setting.fullscreenbackgroundtype_init == 2:
                self.pane_draw.tx_fscrbackfile.SetValue("")
                if cw.cwpy.setting.fullscreenbackgroundfile_init == u"Resource/Image/Dialog/CAUTION":
                    self.pane_draw.ch_fscrbacktype.Select(2)
                else:
                    self.pane_draw.ch_fscrbacktype.Select(3)
            elif cw.cwpy.setting.fullscreenbackgroundtype_init == 1:
                self.pane_draw.tx_fscrbackfile.SetValue(cw.cwpy.setting.fullscreenbackgroundfile_init)
                self.pane_draw.ch_fscrbacktype.Select(1)
            else:
                self.pane_draw.tx_fscrbackfile.SetValue("")
                self.pane_draw.ch_fscrbacktype.Select(0)
            self.pane_draw.tx_fscrbackfile.Enable(self.pane_draw.ch_fscrbacktype.GetSelection() == 1)
            self.pane_draw.ref_fscrbackfile.Enable(self.pane_draw.ch_fscrbacktype.GetSelection() == 1)
        elif selpane == 2:
            self.pane_sound.cb_playbgm.SetValue(cw.cwpy.setting.play_bgm_init)
            self.pane_sound.cb_playsound.SetValue(cw.cwpy.setting.play_sound_init)
            self.pane_sound.sl_sound.SetValue(int(cw.cwpy.setting.vol_sound_init*100))
            self.pane_sound.sl_midi.SetValue(int(cw.cwpy.setting.vol_midi_init*100))
            self.pane_sound.sl_music.SetValue(int(cw.cwpy.setting.vol_bgm_init*100))
            self.pane_sound.list_soundfont.DeleteAllItems()
            for index, soundfont in enumerate(cw.cwpy.setting.soundfonts_init):
                sfont, use = soundfont
                self.pane_sound.list_soundfont.InsertStringItem(index, sfont)
                self.pane_sound.list_soundfont.CheckItem(index, use)
        elif selpane == 3:
            for i, basename in enumerate(self.pane_font.bases):
                name = cw.cwpy.setting.basefont_init[basename]
                if not name:
                    name = u"[デフォルト]"
                self.pane_font.base.SetCellValue(i, 0, name)
            for i, typename in enumerate(self.pane_font.types):
                fonttype, name, pixels, bold, bold_upscr, italic = cw.cwpy.setting.fonttypes_init[typename]
                if fonttype:
                    name = u"[%s]" % (self.pane_font.typenames[fonttype])
                self.pane_font.type.SetCellValue(i, 0, name)
                self.pane_font.type.SetCellValue(i, 1, str(pixels) if 0 < pixels else u"-")
                self.pane_font.type.SetCellValue(i, 2, (u"1" if bold else u"") if not bold is None else u"-")
                self.pane_font.type.SetCellValue(i, 3, (u"1" if bold_upscr else u"") if not bold_upscr is None else u"-")
                self.pane_font.type.SetCellValue(i, 4, (u"1" if italic else u"") if not italic is None else u"-")
            self.pane_font.cb_fontsmoothingcardname.SetValue(cw.cwpy.setting.fontsmoothing_cardname_init)
            self.pane_font.cb_fontsmoothingstatusbar.SetValue(cw.cwpy.setting.fontsmoothing_statusbar_init)
        elif selpane == 4:
            # スキン毎のシナリオ開始位置の設定は変更しない
            self.pane_scenario.tx_editor.SetValue(cw.cwpy.setting.editor_init)
            self.pane_scenario.cb_selectscenariofromtype.SetValue(cw.cwpy.setting.selectscenariofromtype_init)
            self.pane_scenario.cb_showunfitnessscenario.SetValue(cw.cwpy.setting.show_unfitnessscenario_init)
            self.pane_scenario.cb_showcompletedscenario.SetValue(cw.cwpy.setting.show_completedscenario_init)
            self.pane_scenario.cb_showinvisiblescenario.SetValue(cw.cwpy.setting.show_invisiblescenario_init)
        elif selpane == 5:
            self.pane_ui.cb_can_skipwait.SetValue(cw.cwpy.setting.can_skipwait_init)
            self.pane_ui.cb_can_skipanimation.SetValue(cw.cwpy.setting.can_skipanimation_init)
            self.pane_ui.cb_can_repeatlclick.SetValue(cw.cwpy.setting.can_repeatlclick_init)

            self.pane_ui.cb_quickdeal.SetValue(cw.cwpy.setting.quickdeal_init)
            self.pane_ui.cb_allquickdeal.SetValue(cw.cwpy.setting.all_quickdeal_init)
            self.pane_ui.cb_showallselectedcards.SetValue(cw.cwpy.setting.show_allselectedcards_init)
            self.pane_ui.cb_showstatustime.SetValue(cw.cwpy.setting.show_statustime_init)
            self.pane_ui.cb_showroundautostartbutton.SetValue(cw.cwpy.setting.show_roundautostartbutton_init)
            self.pane_ui.cb_showautobuttoninentrydialog.SetValue(cw.cwpy.setting.show_autobuttoninentrydialog_init)

            self.pane_ui.cb_cautionbeforesaving.SetValue(cw.cwpy.setting.caution_beforesaving_init)
            self.pane_ui.cb_showbackpackcard.SetValue(cw.cwpy.setting.show_backpackcard_init)
            self.pane_ui.cb_revertcardpocket.SetValue(cw.cwpy.setting.revert_cardpocket_init)
            self.pane_ui.cb_openhandviewalways.SetValue(cw.cwpy.setting.openhandviewalways_init)
            self.pane_ui.cb_showlogwithwheelup.SetValue(cw.cwpy.setting.wheelup_operation_init == cw.setting.WHEEL_SHOWLOG)
            self.pane_ui.cb_confirmbeforeusingcard.SetValue(cw.cwpy.setting.confirm_beforeusingcard_init)
            self.pane_ui.cb_showsavedmessage.SetValue(cw.cwpy.setting.show_savedmessage_init)
            self.pane_ui.cb_confirmbeforesaving.SetValue(cw.cwpy.setting.confirm_beforesaving_init)
            self.pane_ui.cb_noticeimpossibleaction.SetValue(cw.cwpy.setting.noticeimpossibleaction_init)

    def OnOk(self, event):
        # 設定変更前はレベル上昇が可能な状態だったか
        can_levelup = not (cw.cwpy.is_debugmode() and cw.cwpy.setting.no_levelup_in_debugmode)
        updatecardimg = False # カードイメージの更新が必要か
        updatestatusbar = False # ステータスバーの更新が必要か

        # フォント
        flag_fontupdate = False
        basetable = {}
        basefont = {}
        for i, basename in enumerate(self.pane_font.bases):
            value = self.pane_font.base.GetCellValue(i, 0)
            if value == u"[デフォルト]":
                value = u""
            basefont[basename] = value
            basetable[u"[%s]" % (self.pane_font.typenames[basename])] = basename
        fonttypes = {}
        for i, typename in enumerate(self.pane_font.types):
            value = self.pane_font.type.GetCellValue(i, 0)
            pixels = self.pane_font.type.GetCellValue(i, 1)
            try:
                if pixels <> u"-":
                    pixels = int(pixels)
                else:
                    pixels = -1
            except:
                pixels = -1
            bold = self.pane_font.type.GetCellValue(i, 2)
            if bold in (u"1", u""):
                bold = bold == u"1"
            else:
                bold = None
            bold_upscr = self.pane_font.type.GetCellValue(i, 3)
            if bold_upscr in (u"1", u""):
                bold_upscr = bold_upscr == u"1"
            else:
                bold_upscr = None
            italic = self.pane_font.type.GetCellValue(i, 4)
            if italic in (u"1", u""):
                italic = italic == u"1"
            else:
                italic = None
            fonttype = basetable.get(value, "")
            if fonttype:
                fonttypes[typename] = (fonttype, u"", pixels, bold, bold_upscr, italic)
            else:
                fonttypes[typename] = (u"", value, pixels, bold, bold_upscr, italic)

        value = self.pane_font.cb_fontsmoothingcardname.GetValue()
        if value <> cw.cwpy.setting.fontsmoothing_cardname:
            cw.cwpy.setting.fontsmoothing_cardname = value
            flag_fontupdate = True
        value = self.pane_font.cb_fontsmoothingstatusbar.GetValue()
        if value <> cw.cwpy.setting.fontsmoothing_statusbar:
            cw.cwpy.setting.fontsmoothing_statusbar = value
            flag_fontupdate = True

        # フォント変更チェック
        if basefont <> cw.cwpy.setting.basefont:
            cw.cwpy.setting.basefont = basefont
            flag_fontupdate = True
        if fonttypes <> cw.cwpy.setting.fonttypes:
            cw.cwpy.setting.fonttypes = fonttypes
            flag_fontupdate = True

        # 一般
        value = self.pane_gene.cb_debug.GetValue()
        if not value == cw.cwpy.setting.debug:
            cw.cwpy.exec_func(cw.cwpy.set_debug, value)

        value = self.pane_gene.cb_nolevelup.GetValue()
        cw.cwpy.setting.no_levelup_in_debugmode = value
        value = self.pane_gene.cb_showexperiencebar.GetValue()
        cw.cwpy.setting.show_experiencebar = value
        value = self.pane_gene.cb_storeskinoneachbase.GetValue()
        cw.cwpy.setting.store_skinoneachbase = value
        value = self.pane_gene.sc_initmoneyamount.GetValue()
        cw.cwpy.setting.initmoneyamount = value
        value = self.pane_gene.cb_autosavepartyrecord.GetValue()
        cw.cwpy.setting.autosave_partyrecord = value
        value = self.pane_gene.cb_overwritepartyrecord.GetValue()
        cw.cwpy.setting.overwrite_partyrecord = value
        value = self.pane_gene.tx_ssinfoformat.GetValue()
        cw.cwpy.setting.ssinfoformat = value
        value = self.pane_gene.ch_ssinfocolor.GetSelection()
        if value == 1:
            cw.cwpy.setting.ssinfofontcolor = (255, 255, 255)
            cw.cwpy.setting.ssinfobackcolor = (0, 0, 0)
        else:
            cw.cwpy.setting.ssinfofontcolor = (0, 0, 0)
            cw.cwpy.setting.ssinfobackcolor = (255, 255, 255)
        value = self.pane_gene.sc_backlogmax.GetValue()
        if value <> cw.cwpy.setting.backlogmax:
            def func(backlogmax):
                cw.cwpy.set_backlogmax(backlogmax)
            cw.cwpy.exec_func(func, value)
            updatestatusbar = True

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
                    cw.cwpy.set_expanded(True, value, force=True)
                cw.cwpy.exec_func(func, value)
            else:
                cw.cwpy.setting.expandmode = value
                cw.cwpy.setting.expanddrawing = expanddrawing

        # 描画
        updatemessage = False
        updatebg = False
        value = self.pane_draw.cb_smooth_bg.GetValue()
        if cw.cwpy.setting.smoothscale_bg <> value:
            updatebg = True
            cw.cwpy.setting.smoothscale_bg = value
        value = self.pane_draw.cb_statusbarmask.GetValue()
        if value <> cw.cwpy.setting.statusbarmask:
            cw.cwpy.setting.statusbarmask = value
            updatestatusbar = True
        value = self.pane_draw.cb_decorationfont.GetValue()
        if value <> cw.cwpy.setting.decorationfont:
            cw.cwpy.setting.decorationfont = value
            updatemessage = True
        value = self.pane_draw.sl_deal.GetValue()
        cw.cwpy.setting.set_dealspeed(value)
        value = self.pane_draw.sl_msgs.GetValue()
        cw.cwpy.setting.messagespeed = value
        value = self.pane_draw.ch_tran.GetSelection()
        value = self.pane_draw.transitions[value]
        cw.cwpy.setting.transition = value
        value = self.pane_draw.sl_tran.GetValue()
        cw.cwpy.setting.transitionspeed = value
        value = self.pane_draw.ch_fscrbacktype.GetSelection()
        if value == 0:
            cw.cwpy.setting.fullscreenbackgroundfile = u""
            cw.cwpy.setting.fullscreenbackgroundtype = 0
        elif value == 1:
            cw.cwpy.setting.fullscreenbackgroundfile = self.pane_draw.tx_fscrbackfile.GetValue()
            cw.cwpy.setting.fullscreenbackgroundtype = 1
        elif value == 2:
            cw.cwpy.setting.fullscreenbackgroundfile = u"Resource/Image/Dialog/CAUTION"
            cw.cwpy.setting.fullscreenbackgroundtype = 2
        elif value == 3:
            cw.cwpy.setting.fullscreenbackgroundfile = u"Resource/Image/Dialog/PAD"
            cw.cwpy.setting.fullscreenbackgroundtype = 2
        def func1():
            cw.cwpy.update_fullscreenbackground()
        cw.cwpy.exec_func(func1)

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
        for index in xrange(self.pane_sound.list_soundfont.GetItemCount()):
            soundfont = self.pane_sound.list_soundfont.GetItemText(index)
            use = self.pane_sound.list_soundfont.IsChecked(index)
            soundfonts.append((soundfont, use))
        if cw.cwpy.setting.soundfonts <> soundfonts:
            sfonts1 = [sfont[0] for sfont in soundfonts if sfont[1]]
            sfonts2 = [sfont[0] for sfont in cw.cwpy.setting.soundfonts if sfont[1]]
            cw.cwpy.setting.soundfonts = soundfonts
            if sfonts1 <> sfonts2:
                def func():
                    if cw.bassplayer.is_alivable():
                        cw.bassplayer.dispose_bass()
                    if pygame.mixer.get_init():
                        pygame.mixer.quit()

                    if sfonts1:
                        cw.bassplayer.init_bass(sfonts1)
                    else:
                        cw.util.sdlmixer_init()

                    if bool(sfonts1) <> bool(sfonts2):
                        cw.cwpy.init_sounds()
                    cw.cwpy.music.play(cw.cwpy.music.path, updatepredata=False, restart=True)

                cw.cwpy.exec_func(func)

        # 配色(メッセージ)
        alpha = self.pane_draw.sc_mwin.GetValue()
        colour = self.pane_draw.cs_mwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        cw.cwpy.setting.mwincolour = colour
        updatemessage |= cw.cwpy.setting.mwincolour <> colour
        alpha = self.pane_draw.sc_mframe.GetValue()
        colour = self.pane_draw.cs_mframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= cw.cwpy.setting.mwinframecolour <> colour
        cw.cwpy.setting.mwinframecolour = colour
        # 配色(バックログ)
        alpha = self.pane_draw.sc_mwin.GetValue()
        colour = self.pane_draw.cs_blwin.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= cw.cwpy.setting.blwincolour <> colour
        cw.cwpy.setting.blwincolour = colour
        alpha = self.pane_draw.sc_mframe.GetValue()
        colour = self.pane_draw.cs_blframe.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatemessage |= cw.cwpy.setting.blwinframecolour <> colour
        cw.cwpy.setting.blwinframecolour = colour
        if updatemessage:
            cw.cwpy.exec_func(cw.cwpy.update_messagestyle)

        updatecurtain = False
        # 配色(メッセージログカーテン)
        alpha = self.pane_draw.sc_blcurtain.GetValue()
        colour = self.pane_draw.cs_blcurtain.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatecurtain |= cw.cwpy.setting.blcurtaincolour <> colour
        cw.cwpy.setting.blcurtaincolour = colour
        # 配色(選択モードカーテン)
        alpha = self.pane_draw.sc_curtain.GetValue()
        colour = self.pane_draw.cs_curtain.GetColour()
        colour = (colour[0], colour[1], colour[2], alpha)
        updatecurtain |= cw.cwpy.setting.curtaincolour <> colour
        cw.cwpy.setting.curtaincolour = colour
        if updatecurtain:
            cw.cwpy.exec_func(cw.cwpy.update_curtainstyle)

        # スキン
        skin = self.pane_gene.ch_skin.GetSelection()
        skin = self.pane_gene.skins[skin]
        if flag_fontupdate or cw.cwpy.setting.skindirname <> skin:
            cw.cwpy.exec_func(cw.cwpy.update_skin, skin, restartop=cw.cwpy.setting.skindirname <> skin)
            updatebg = False

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
        value = self.pane_scenario.tx_editor.GetValue()
        cw.cwpy.setting.editor = value
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
        value = self.pane_ui.cb_can_skipwait.GetValue()
        cw.cwpy.setting.can_skipwait = value
        value = self.pane_ui.cb_can_skipanimation.GetValue()
        cw.cwpy.setting.can_skipanimation = value
        value = self.pane_ui.cb_can_repeatlclick.GetValue()
        cw.cwpy.setting.can_repeatlclick = value

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
        value = self.pane_ui.cb_openhandviewalways.GetValue()
        cw.cwpy.setting.openhandviewalways = value
        value = self.pane_ui.cb_confirmbeforesaving.GetValue()
        cw.cwpy.setting.confirm_beforesaving = value
        value = self.pane_ui.cb_showsavedmessage.GetValue()
        cw.cwpy.setting.show_savedmessage = value
        value = self.pane_ui.cb_confirmbeforeusingcard.GetValue()
        cw.cwpy.setting.confirm_beforeusingcard = value
        value = self.pane_ui.cb_noticeimpossibleaction.GetValue()
        cw.cwpy.setting.noticeimpossibleaction = value
        value = self.pane_ui.cb_showroundautostartbutton.GetValue()
        if cw.cwpy.setting.show_roundautostartbutton <> value:
            cw.cwpy.setting.show_roundautostartbutton = value
            updatestatusbar = True
            if not cw.cwpy.setting.show_roundautostartbutton:
                def func():
                    if cw.cwpy.is_playingscenario():
                        cw.cwpy.sdata.autostart_round = False
                cw.cwpy.exec_func(func)
        value = self.pane_ui.cb_showautobuttoninentrydialog.GetValue()
        cw.cwpy.setting.show_autobuttoninentrydialog = value

        # 背景の更新
        if updatebg:
            def func():
                if cw.cwpy.is_playingscenario():
                    cw.cwpy.sdata.resource_cache = {}
                cw.cwpy.background.reload()
            cw.cwpy.exec_func(func)

        # イメージの更新
        if updatecardimg:
            def func():
                for ccard in itertools.chain(cw.cwpy.get_pcards("unreversed"),\
                                             cw.cwpy.get_ecards("unreversed"),\
                                             cw.cwpy.get_fcards("unreversed")):
                    ccard.update_image()
            cw.cwpy.exec_func(func)

        # ステータスバーの更新
        if updatestatusbar:
            def func():
                cw.cwpy.statusbar.change(cw.cwpy.statusbar.showbuttons)
            cw.cwpy.exec_func(func)

        if cw.cwpy.is_showingdebugger() and cw.cwpy.frame.debugger:
            cw.cwpy.frame.debugger.refresh_tools()

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
        self.box_gene = wx.StaticBox(self, -1, u"詳細")
        self.cb_debug = wx.CheckBox(self, -1, u"デバッグモードでプレイする")
        self.cb_debug.SetValue(cw.cwpy.debug)
        self.cb_nolevelup = wx.CheckBox(
            self, -1, u"デバッグ中はレベル上昇を停止する")
        self.cb_nolevelup.SetValue(cw.cwpy.setting.no_levelup_in_debugmode)
        self.cb_showexperiencebar = wx.CheckBox(
            self, -1, u"次のレベルアップまでの割合を表示する")
        self.cb_showexperiencebar.SetValue(cw.cwpy.setting.show_experiencebar)

        # 基本的なオプション
        self.cb_storeskinoneachbase = wx.CheckBox(
            self, -1, u"拠点ごとにスキンを記憶する")
        self.cb_storeskinoneachbase.SetValue(cw.cwpy.setting.store_skinoneachbase)
        self.st_backlogmax = wx.StaticText(self, -1, u"メッセージログの最大数:")
        self.sc_backlogmax = wx.SpinCtrl(self, -1, size=(80, -1), max=9999, min=0)
        self.sc_backlogmax.SetValue(cw.cwpy.setting.backlogmax)

        # スキン
        self.box_skin = wx.StaticBox(self, -1, u"スキン",)
        self.ch_skin = wx.Choice(self, -1, size=(-1, -1))
        self.st_skin = wx.StaticText(self, -1, u"")

        self.btn_convertskin = wx.Button(self, -1, u"自動生成...")
        self.btn_editskin = wx.Button(self, -1, u"編集...")
        self.btn_deleteskin = wx.Button(self, -1, u"削除")

        self.update_skins(cw.cwpy.setting.skindirname)

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
        nmax = x if x < y else y
        if nmax < 10:
            nmax = 10
        if nmax < n:
            n = nmax

        self.ch_expanddrawing = wx.ComboBox(self, -1, style=wx.CB_DROPDOWN|wx.CB_READONLY)
        i = 0
        val = 1
        while True:
            self.ch_expanddrawing.Append(u"%s倍" % (val))
            if cw.cwpy.setting.expanddrawing == val:
                self.ch_expanddrawing.Select(i)
            i += 1
            val *= 2
            if nmax < val*10:
                break
        if self.ch_expanddrawing.GetSelection() == -1:
            self.ch_expanddrawing.Select(0)

        self.sl_expand = wx.Slider(
            self, -1, n, 10, nmax, size=(120, -1),
            style=wx.SL_HORIZONTAL)
        self.st_expand = wx.StaticText(self, -1)
        self.cb_fullscreen = wx.CheckBox(self, -1, u"フルスクリーン")
        self.cb_fullscreen.SetValue(cw.cwpy.setting.expandmode == "FullScreen")

        self.makeExpandInfo()

        self.ln_expand = wx.StaticLine(self, -1, style=wx.HORIZONTAL)
        self.cb_smoothexpand = wx.CheckBox(self, -1,
                                           u"拡大後の画面を滑らかにする")
        self.cb_smoothexpand.SetValue(cw.cwpy.setting.smoothexpand)

        # 持出金額
        self.box_party = wx.StaticBox(self, -1, u"パーティ")
        self.st_initmoneyamount = wx.StaticText(self, -1, u"結成時の持出金額:")
        self.sc_initmoneyamount = wx.SpinCtrl(self, -1, "", size=(80, -1), min=0, max=999999)
        self.sc_initmoneyamount.SetValue(cw.cwpy.setting.initmoneyamount)

        self.cb_autosavepartyrecord = wx.CheckBox(
            self, -1, u"解散時、自動的にパーティ情報を記録する")
        self.cb_autosavepartyrecord.SetValue(cw.cwpy.setting.autosave_partyrecord)
        self.cb_overwritepartyrecord = wx.CheckBox(
            self, -1, u"自動記録時、同名のパーティ記録へ上書きする")
        self.cb_overwritepartyrecord.SetValue(cw.cwpy.setting.overwrite_partyrecord)
        self.cb_overwritepartyrecord.Enable(cw.cwpy.setting.autosave_partyrecord)

        # スクリーンショット情報
        self.box_ss = wx.StaticBox(self, -1, u"スクリーンショット情報(画像上部に表示)")
        self.tx_ssinfoformat = wx.TextCtrl(self, -1, size=(150, -1))
        self.tx_ssinfoformat.SetValue(cw.cwpy.setting.ssinfoformat)
        # スクリーンショット情報の色
        choices = [u"黒文字", u"白文字"]
        self.ch_ssinfocolor = wx.Choice(self, -1, size=(-1, -1), choices=choices)
        if cw.cwpy.setting.ssinfofontcolor[:3] == (255, 255, 255):
            self.ch_ssinfocolor.Select(1)
        else:
            self.ch_ssinfocolor.Select(0)

        self.st_ssinfodesc = wx.StaticText(self, -1,
                                           u"次の各情報を表示できます:\n" +
                                           u" %application% = ソフト名, %skin% = スキン名,\n" +
                                           u" %yado% = 拠点名, %party% = パーティ名,\n" +
                                           u" %scenario% = シナリオ名, %author% = 作者名,\n" +
                                           u" %date% = 日付, %time% = 時刻")

        self._do_layout()
        self._bind()

    def _bind(self):
        ##self.cb_debug.Bind(wx.EVT_CHECKBOX, self.OnDebugCheck)
        self.ch_skin.Bind(wx.EVT_CHOICE, self.OnSkinChoice)
        self.sl_expand.Bind(wx.EVT_SLIDER, self.OnExpandChange)
        self.cb_fullscreen.Bind(wx.EVT_CHECKBOX, self.OnExpandChange)
        self.cb_autosavepartyrecord.Bind(wx.EVT_CHECKBOX, self.OnAutoSavePartyRecord)
        self.btn_convertskin.Bind(wx.EVT_BUTTON, self.OnConvertSkin)
        self.btn_editskin.Bind(wx.EVT_BUTTON, self.OnEditSkin)
        self.btn_deleteskin.Bind(wx.EVT_BUTTON, self.OnDeleteSkin)

    ##def OnDebugCheck(self, event):
    ##    if cw.cwpy.is_playingscenario():
    ##        self.cb_debug.SetValue(not self.cb_debug.GetValue())
    ##        dlg = cw.dialog.message.Message(
    ##            self.Parent.Parent, cw.cwpy.msgs["message"],
    ##            u"シナリオプレイ中はデバッグモードの切替はできません。")
    ##        cw.cwpy.frame.move_dlg(dlg)
    ##        cw.cwpy.sounds["error"].play()
    ##        dlg.ShowModal()

    def update_skins(self, skindirname):
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
                    classictext = e.getbool("ClassicStyleText", True)
                    vocation120 = e.getbool("CW120VocationLevel", False)
                    self.skin_summarys[name] = (skintype, skinname, author, desc, classictext, vocation120)
                except Exception:
                    # エラーのあるスキンは無視
                    cw.util.print_ex()

        self.ch_skin.SetItems(self.skins)
        n = self.skins.index(skindirname)
        self.ch_skin.SetSelection(n)
        self._choice_skin()

    def OnSkinChoice(self, event):
        self._choice_skin()

    def _choice_skin(self):
        skin = self.skins[self.ch_skin.GetSelection()]
        s = u"種別: %s\n名前: %s\n作者: %s\n" + u"-" * 45 + u"\n%s"
        skintype, skinname, author, desc, _classictext, _vocation120 = self.skin_summarys[skin]
        desc = cw.util.txtwrap(desc, 1)
        self.st_skin.SetLabel(s % (skintype, skinname, author, desc))
        self.btn_deleteskin.Enable(cw.cwpy.setting.skindirname <> skin)

    def OnConvertSkin(self, event):
        dlg = cw.dialog.skin.SkinConversionDialog(self.TopLevelParent, exe=u"", from_settings=True)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        if dlg.successful:
            self.update_skins(dlg.skindirname)
        dlg.Destroy()

    def OnEditSkin(self, event):
        skin = self.skins[self.ch_skin.GetSelection()]
        skinsummary = self.skin_summarys[skin]
        dlg = cw.dialog.skin.SkinEditDialog(self.TopLevelParent, skin, skinsummary)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.skin_summarys[skin] = dlg.skinsummary
            self._choice_skin()
        dlg.Destroy()

    def OnDeleteSkin(self, event):
        skin = self.skins[self.ch_skin.GetSelection()]
        if cw.cwpy.setting.skindirname == skin:
            return
        s = u"スキンを削除すると元に戻すことはできません。\n%sを削除しますか？" % (skin)
        dlg = cw.dialog.message.YesNoMessage(self.TopLevelParent, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)
        cw.cwpy.sounds["signal"].play()
        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["dump"].play()
            dpath = cw.util.join_paths(u"Data/Skin", skin)
            cw.util.remove(dpath)
            self.update_skins(cw.cwpy.setting.skindirname)

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

    def OnAutoSavePartyRecord(self, event):
        self.cb_overwritepartyrecord.Enable(self.cb_autosavepartyrecord.GetValue())

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_skin = wx.StaticBoxSizer(self.box_skin, wx.VERTICAL)
        bsizer_expandmode = wx.StaticBoxSizer(self.box_expandmode, wx.VERTICAL)
        bsizer_expandmode_draw = wx.BoxSizer(wx.HORIZONTAL)

        bsizer_gene.Add(self.cb_debug, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_nolevelup, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_showexperiencebar, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_storeskinoneachbase, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_backlogmax = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_backlogmax.Add(self.st_backlogmax, 0, wx.RIGHT|wx.CENTER, 3)
        bsizer_backlogmax.Add(self.sc_backlogmax, 0, wx.CENTER, 3)
        bsizer_gene.Add(bsizer_backlogmax)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_skinbtn = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_skinbtn.Add(self.btn_convertskin, 0, wx.RIGHT, 3)
        bsizer_skinbtn.Add(self.btn_editskin, 0, wx.RIGHT, 3)
        bsizer_skinbtn.Add(self.btn_deleteskin, 0, 0, 3)

        bsizer_skin.Add(self.ch_skin, 0, wx.CENTER, 0)
        bsizer_skin.Add(self.st_skin, 1, wx.CENTER|wx.ALL, 3)
        bsizer_skin.Add(bsizer_skinbtn, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_skin.SetMinSize((SETTINGS_WIDTH, 180))

        bsizer_expandmode_draw.Add(self.st_expandscr, 0, wx.RIGHT|wx.CENTER, 3)
        bsizer_expandmode_draw.Add(self.ch_expanddrawing, 0, wx.CENTER|wx.RIGHT, 10)
        bsizer_expandmode_draw.Add(self.st_expandwin, 0, wx.CENTER, 0)
        bsizer_expandmode_draw.Add(self.st_expand, 0, wx.CENTER, 0)
        bsizer_expandmode.Add(bsizer_expandmode_draw, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(self.sl_expand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(self.cb_fullscreen, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.ALIGN_RIGHT, 3)
        bsizer_expandmode.Add(self.ln_expand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)
        bsizer_expandmode.Add(self.cb_smoothexpand, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_expandmode.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_party = wx.StaticBoxSizer(self.box_party, wx.VERTICAL)
        bsizer_partymoney = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_partymoney.Add(self.st_initmoneyamount, 0, wx.RIGHT|wx.CENTER, 3)
        bsizer_partymoney.Add(self.sc_initmoneyamount, 0, wx.CENTER, 3)
        bsizer_party.Add(bsizer_partymoney, 0, wx.ALL, 3)
        bsizer_party.Add(self.cb_autosavepartyrecord, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_party.Add(self.cb_overwritepartyrecord, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)

        bsizer_ss = wx.StaticBoxSizer(self.box_ss, wx.VERTICAL)
        bsizer_ssl = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_ssl.Add(self.tx_ssinfoformat, 1, wx.RIGHT|wx.CENTER, 3)
        bsizer_ssl.Add(self.ch_ssinfocolor, 0, wx.CENTER, 3)
        bsizer_ss.Add(bsizer_ssl, 0, wx.ALL|wx.EXPAND, 3)
        bsizer_ss.Add(self.st_ssinfodesc, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)

        sizer_left.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_skin, 1, wx.EXPAND, 3)

        sizer_right.Add(bsizer_expandmode, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_right.Add(bsizer_party, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_right.Add(bsizer_ss, 0, wx.EXPAND, 0)

        sizer_h1.Add(sizer_left, 0, wx.RIGHT|wx.EXPAND, 5)
        sizer_h1.Add(sizer_right, 1, wx.EXPAND, 3)

        sizer.Add(sizer_h1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class DrawingSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.box_gene = wx.StaticBox(self, -1, u"詳細")
        # 背景拡大縮小補正
        self.cb_smooth_bg = wx.CheckBox(
            self, -1, u"拡大縮小した背景画像を滑らかにする")
        self.cb_smooth_bg.SetValue(cw.cwpy.setting.smoothscale_bg)
        # イベント中にステータスバーの色を変える
        self.cb_statusbarmask = wx.CheckBox(
            self, -1, u"イベント中にステータスバーの色を変える")
        self.cb_statusbarmask.SetValue(cw.cwpy.setting.statusbarmask)
        # メッセージで装飾フォントを使用する
        self.cb_decorationfont = wx.CheckBox(
            self, -1, u"メッセージで装飾フォントを使用する")
        self.cb_decorationfont.SetValue(cw.cwpy.setting.decorationfont)
        # トランジション効果
        self.box_tran = wx.StaticBox(
            self, -1, u"背景の切り替え方式(速い⇔遅い)")
        self.transitions = [
            "None", "Blinds", "PixelDissolve", "Fade"]
        self.choices_tran = [
            u"アニメーションなし", u"短冊(スレッド)式", u"ドット置換(シェーブ)式",
            u"色置換(フェード)式"]
        self.ch_tran = wx.Choice(
            self, -1, size=(-1, -1), choices=self.choices_tran)
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
            self, -1, cw.cwpy.setting.dealspeed, 0, 10, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_deal.SetTickFreq(1, 1)
        # メッセージ表示速度
        self.box_msgs = wx.StaticBox(
            self, -1, u"メッセージ表示速度(速い⇔遅い)")
        self.sl_msgs = wx.Slider(
            self, -1, cw.cwpy.setting.messagespeed, 0, 10, size=(SETTINGS_WIDTH-10, -1),
            style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS)
        self.sl_msgs.SetTickFreq(1, 1)

        # フルスクリーンの背景
        self.box_fscrback = wx.StaticBox(self, -1, u"フルスクリーンの背景")
        choices = [u"<背景なし>", u"<ファイルから選択>", u"ダイアログの壁紙", u"スキンのロゴ"]
        self.ch_fscrbacktype = wx.Choice(self, -1, size=(-1, -1), choices=choices)
        self.tx_fscrbackfile = wx.TextCtrl(self, -1, size=(150, -1))
        self.ref_fscrbackfile = cw.util.create_fileselection(self,
            target=self.tx_fscrbackfile,
            message=u"フルスクリーンの背景にするファイルを選択",
            wildcard=u"画像ファイル (*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm)|*.jpg;*.png;*.gif;*.bmp;*.tiff;*.xpm|全てのファイル (*.*)|*.*")

        if cw.cwpy.setting.fullscreenbackgroundtype == 0:
            self.ch_fscrbacktype.SetSelection(0)
            self.tx_fscrbackfile.SetValue(u"")
        elif cw.cwpy.setting.fullscreenbackgroundtype == 1:
            self.ch_fscrbacktype.SetSelection(1)
            self.tx_fscrbackfile.SetValue(cw.cwpy.setting.fullscreenbackgroundfile)
        elif cw.cwpy.setting.fullscreenbackgroundtype == 2:
            if cw.cwpy.setting.fullscreenbackgroundfile == u"Resource/Image/Dialog/CAUTION":
                self.ch_fscrbacktype.SetSelection(2)
                self.tx_fscrbackfile.SetValue(u"")
            elif cw.cwpy.setting.fullscreenbackgroundfile == u"Resource/Image/Dialog/PAD":
                self.ch_fscrbacktype.SetSelection(3)
                self.tx_fscrbackfile.SetValue(u"")
            else:
                self.ch_fscrbacktype.SetSelection(0)
                self.tx_fscrbackfile.SetValue(u"")

        self.tx_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)
        self.ref_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)

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

        # メッセージログカーテン色
        self.box_blcurtain = wx.StaticBox(self, -1, u"メッセージログの背景")
        self.st_blcurtain = wx.StaticText(self, -1, u"カラー")
        self.cs_blcurtain = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.blcurtaincolour)
        self.st_blcurtain2 = wx.StaticText(self, -1, u"アルファ値")
        self.sc_blcurtain = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.sc_blcurtain.SetRange(0, 255)
        self.sc_blcurtain.SetValue(cw.cwpy.setting.blcurtaincolour[3])

        # カーテン色
        self.box_curtain = wx.StaticBox(self, -1, u"カーテン(選択モードの背景効果)")
        self.st_curtain = wx.StaticText(self, -1, u"カラー")
        self.cs_curtain = wx.ColourPickerCtrl(
            self, -1, col=cw.cwpy.setting.curtaincolour)
        self.st_curtain2 = wx.StaticText(self, -1, u"アルファ値")
        self.sc_curtain = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.sc_curtain.SetRange(0, 255)
        self.sc_curtain.SetValue(cw.cwpy.setting.curtaincolour[3])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.ch_fscrbacktype.Bind(wx.EVT_CHOICE, self.OnFullScreenBackgroundType, id=self.ch_fscrbacktype.GetId())

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_tran = wx.StaticBoxSizer(self.box_tran, wx.VERTICAL)
        bsizer_deal = wx.StaticBoxSizer(self.box_deal, wx.VERTICAL)
        bsizer_msgs = wx.StaticBoxSizer(self.box_msgs, wx.VERTICAL)

        bsizer_gene.Add(self.cb_smooth_bg, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_statusbarmask, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_decorationfont, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))
        bsizer_tran.Add(self.ch_tran, 0, wx.ALL, 3)
        bsizer_tran.Add(self.sl_tran, 0, wx.EXPAND, 0)
        bsizer_deal.Add(self.sl_deal, 0, wx.EXPAND, 0)
        bsizer_msgs.Add(self.sl_msgs, 0, wx.EXPAND, 0)

        bsizer_mwin = wx.StaticBoxSizer(self.box_mwin, wx.HORIZONTAL)
        gsizer_mwin = wx.GridBagSizer()
        gsizer_mwin.Add(self.st_mwin, pos=(0, 0), flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=3)
        gsizer_mwin.Add(self.cs_mwin, pos=(0, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        gsizer_mwin.Add(self.st_blwin, pos=(1, 0), flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=3)
        gsizer_mwin.Add(self.cs_blwin, pos=(1, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        bsizer_mwin.Add(gsizer_mwin, 0, wx.CENTER|wx.LEFT, 5)
        bsizer_mwin.Add(self.st_mwin2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mwin.Add(self.sc_mwin, 0, wx.CENTER|wx.RIGHT, 3)

        bsizer_mframe = wx.StaticBoxSizer(self.box_mframe, wx.HORIZONTAL)
        gsizer_mframe = wx.GridBagSizer()
        gsizer_mframe.Add(self.st_mframe, pos=(0, 0), flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=3)
        gsizer_mframe.Add(self.cs_mframe, pos=(0, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        gsizer_mframe.Add(self.st_blframe, pos=(1, 0), flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=3)
        gsizer_mframe.Add(self.cs_blframe, pos=(1, 1), flag=wx.RIGHT|wx.EXPAND, border=3)
        bsizer_mframe.Add(gsizer_mframe, 0, wx.CENTER|wx.LEFT, 3)
        bsizer_mframe.Add(self.st_mframe2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_mframe.Add(self.sc_mframe, 0, wx.CENTER|wx.RIGHT, 3)

        bsizer_blcurtain = wx.StaticBoxSizer(self.box_blcurtain, wx.HORIZONTAL)
        bsizer_blcurtain.Add(self.st_blcurtain, 0, wx.LEFT|wx.RIGHT|wx.CENTER, 3)
        bsizer_blcurtain.Add(self.cs_blcurtain, 0, wx.RIGHT|wx.EXPAND, 3)
        bsizer_blcurtain.Add(self.st_blcurtain2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_blcurtain.Add(self.sc_blcurtain, 0, wx.CENTER|wx.RIGHT, 3)

        bsizer_curtain = wx.StaticBoxSizer(self.box_curtain, wx.HORIZONTAL)
        bsizer_curtain.Add(self.st_curtain, 0, wx.LEFT|wx.RIGHT|wx.CENTER, 3)
        bsizer_curtain.Add(self.cs_curtain, 0, wx.RIGHT|wx.EXPAND, 3)
        bsizer_curtain.Add(self.st_curtain2, 0, wx.CENTER|wx.LEFT|wx.RIGHT, 3)
        bsizer_curtain.Add(self.sc_curtain, 0, wx.CENTER|wx.RIGHT, 3)

        bsizer_fscrback = wx.StaticBoxSizer(self.box_fscrback, wx.VERTICAL)
        bsizer_fscrback.Add(self.ch_fscrbacktype, 0, wx.ALL, 3)
        bsizer_fscrbackfile = wx.BoxSizer(wx.HORIZONTAL)
        bsizer_fscrbackfile.Add(self.tx_fscrbackfile, 1, wx.RIGHT|wx.CENTER, 3)
        bsizer_fscrbackfile.Add(self.ref_fscrbackfile, 0, wx.CENTER, 3)
        bsizer_fscrback.Add(bsizer_fscrbackfile, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.EXPAND, 3)

        sizer_left.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_tran, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_deal, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_msgs, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_fscrback, 0, wx.EXPAND, 3)

        sizer_right.Add(bsizer_mwin, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_right.Add(bsizer_mframe, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_right.Add(bsizer_blcurtain, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_right.Add(bsizer_curtain, 0, wx.EXPAND, 3)

        sizer_h1.Add(sizer_left, 1, wx.RIGHT|wx.EXPAND, 5)
        sizer_h1.Add(sizer_right, 0, wx.EXPAND, 3)

        sizer.Add(sizer_h1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnFullScreenBackgroundType(self, event):
        self.tx_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)
        self.ref_fscrbackfile.Enable(self.ch_fscrbacktype.GetSelection() == 1)

class AudioSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.box_gene = wx.StaticBox(self, -1, u"詳細")
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
        self.list_soundfont = cw.util.CheckableListCtrl(self, -1, size=(SETTINGS_WIDTH, -1), style=wx.MULTIPLE|wx.VSCROLL|wx.HSCROLL)
        for index, soundfont in enumerate(cw.cwpy.setting.soundfonts):
            sfont, use = soundfont
            self.list_soundfont.InsertStringItem(index, sfont)
            self.list_soundfont.CheckItem(index, use)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnAddSoundFontBtn, self.btn_addsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveSoundFontBtn, self.btn_rmvsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnUpSoundFontBtn, self.btn_upsoundfont)
        self.Bind(wx.EVT_BUTTON, self.OnDownSoundFontBtn, self.btn_downsoundfont)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_music = wx.StaticBoxSizer(self.box_music, wx.VERTICAL)
        bsizer_midi = wx.StaticBoxSizer(self.box_midi, wx.VERTICAL)
        bsizer_sound = wx.StaticBoxSizer(self.box_sound, wx.VERTICAL)
        bsizer_soundfont = wx.StaticBoxSizer(self.box_soundfont, wx.VERTICAL)

        bsizer_gene.Add(self.cb_playbgm, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_playsound, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_soundfontbtns = wx.BoxSizer(wx.HORIZONTAL)
        sizer_soundfontbtns.Add(self.btn_addsoundfont, 0, wx.RIGHT, 3)
        sizer_soundfontbtns.Add(self.btn_rmvsoundfont, 0, wx.RIGHT, 3)
        sizer_soundfontbtns.Add(self.btn_upsoundfont, 0, wx.RIGHT, 3)
        sizer_soundfontbtns.Add(self.btn_downsoundfont, 0, 0, 0)

        bsizer_music.Add(self.sl_music, 0, wx.EXPAND, 0)
        bsizer_midi.Add(self.sl_midi, 0, wx.EXPAND, 0)
        bsizer_sound.Add(self.sl_sound, 0, wx.EXPAND, 0)
        bsizer_soundfont.Add(sizer_soundfontbtns, 0, wx.ALL, 3)
        bsizer_soundfont.Add(self.list_soundfont, 1, wx.EXPAND|wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)

        sizer_left.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_music, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_midi, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_left.Add(bsizer_sound, 0, wx.EXPAND, 3)

        sizer_right.Add(bsizer_soundfont, 1, wx.EXPAND, 0)

        sizer_h1.Add(sizer_left, 0, wx.RIGHT|wx.EXPAND, 5)
        sizer_h1.Add(sizer_right, 1, wx.EXPAND, 3)

        sizer.Add(sizer_h1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnAddSoundFontBtn(self, event):
        dlg = wx.FileDialog(self.GetTopLevelParent(), u"MIDIの演奏に使用するサウンドフォント選択", u"Data/SoundFont", "", "*.sf2", wx.FD_OPEN|wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            exists = set()
            index = -1
            for index in xrange(self.list_soundfont.GetItemCount()):
                soundfont = self.list_soundfont.GetItemText(index)
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
                index = self.list_soundfont.GetItemCount()
                self.list_soundfont.InsertStringItem(index, fpath)
                self.list_soundfont.CheckItem(index, True)

    def OnRemoveSoundFontBtn(self, event):
        while True:
            index = self.list_soundfont.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index < 0:
                break
            self.list_soundfont.DeleteItem(index)

    def OnUpSoundFontBtn(self, event):
        index = -1
        while True:
            index = self.list_soundfont.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= 0:
                break
            item = self.list_soundfont.GetItemText(index)
            use = self.list_soundfont.IsChecked(index)
            self.list_soundfont.DeleteItem(index)
            self.list_soundfont.InsertStringItem(index - 1, item)
            self.list_soundfont.CheckItem(index - 1, use)
            self.list_soundfont.Select(index - 1)

    def OnDownSoundFontBtn(self, event):
        indexes = []
        index = -1
        while True:
            index = self.list_soundfont.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index < 0:
                break
            indexes.append(index)

        if not indexes or self.list_soundfont.GetItemCount() <= indexes[-1] + 1:
            return

        indexes.reverse()
        for index in indexes:
            item = self.list_soundfont.GetItemText(index)
            use = self.list_soundfont.IsChecked(index)
            self.list_soundfont.DeleteItem(index)
            self.list_soundfont.InsertStringItem(index + 1, item)
            self.list_soundfont.CheckItem(index + 1, use)
            self.list_soundfont.Select(index + 1)

class ScenarioSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # シナリオのオプション
        self.box_gene = wx.StaticBox(self, -1, u"詳細")
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
        self.grid_folderoftype.SetColSize(1, 370)

        types = set()
        for t in self.Parent.Parent.pane_gene.skin_summarys.itervalues():
            skintype, _skinname, _author, _desc, _classictext, _vocation120 = t
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

        # シナリオエディタ
        self.box_debug = wx.StaticBox(self, -1, u"デバッグ")
        self.st_editor = wx.StaticText(self, -1, u"エディタ")
        self.tx_editor = wx.TextCtrl(self, -1, size=(150, -1))
        self.tx_editor.SetValue(cw.cwpy.setting.editor)
        if sys.platform == "win32":
            wildcard = u"実行可能ファイル (*.exe)|*.exe|全てのファイル (*.*)|*.*"
        else:
            wildcard = u"全てのファイル (*.*)|*.*"
        self.ref_editor = cw.util.create_fileselection(self,
            target=self.tx_editor,
            message=u"CardWirthのシナリオエディタを選択",
            wildcard=wildcard)

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
        sizer_folderbtns.Add(self.btn_reffolder, 0, wx.RIGHT, 3)
        sizer_folderbtns.Add(self.btn_removefolder, 0, wx.RIGHT, 3)
        sizer_folderbtns.Add(self.btn_upfolder, 0, wx.RIGHT, 3)
        sizer_folderbtns.Add(self.btn_downfolder, 0, 0, 0)

        bsizer_folderoftype.Add(sizer_folderbtns, 0, wx.ALL, 3)
        bsizer_folderoftype.Add(self.grid_folderoftype, 1, wx.EXPAND|wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)

        bsizer_editor = wx.StaticBoxSizer(self.box_debug, wx.HORIZONTAL)
        bsizer_editor.Add(self.st_editor, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 3)
        bsizer_editor.Add(self.tx_editor, 1, wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 3)
        bsizer_editor.Add(self.ref_editor, 0, wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 3)

        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 3)
        sizer_v1.Add(bsizer_folderoftype, 1, wx.BOTTOM|wx.EXPAND, 3)
        sizer_v1.Add(bsizer_editor, 0, wx.EXPAND, 0)

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

        skintype = self.grid_folderoftype.GetCellValue(row, 0)
        if not skintype:
            skintype = u"(指定無し)"

        dpath = os.path.abspath("Scenario")
        dlg = wx.DirDialog(self.TopLevelParent, u"「%s」タイプのスキンでプレイするシナリオのフォルダを選択してください。" % (skintype), dpath, style=wx.DD_DIR_MUST_EXIST)
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

class UISettingPanel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent)
        self.SetScrollbars(1, 10, 1, 1)

        # 空白時間オプション
        self.box_wait = wx.StaticBox(self, -1, u"スキップ")
        self.cb_can_skipwait = wx.CheckBox(
            self, -1, u"空白時間をスキップ可能にする")
        self.cb_can_skipwait.SetValue(cw.cwpy.setting.can_skipwait)
        self.cb_can_skipanimation = wx.CheckBox(
            self, -1, u"アニメーションをスキップ可能にする")
        self.cb_can_skipanimation.SetValue(cw.cwpy.setting.can_skipanimation)
        self.cb_can_repeatlclick = wx.CheckBox(
            self, -1, u"マウスの左ボタンを押し続けた時は連打状態にする")
        self.cb_can_repeatlclick.SetValue(cw.cwpy.setting.can_repeatlclick)

        # 描画オプション
        self.box_draw = wx.StaticBox(self, -1, u"カード")
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
        self.box_gene = wx.StaticBox(self, -1, u"操作")
        self.cb_showbackpackcard = wx.CheckBox(
            self, -1, u"荷物袋のカードを一時的に取り出して使えるようにする")
        self.cb_showbackpackcard.SetValue(cw.cwpy.setting.show_backpackcard)
        self.cb_revertcardpocket = wx.CheckBox(
            self, -1, u"レベル調節で手放したカードを自動的に戻す")
        self.cb_revertcardpocket.SetValue(cw.cwpy.setting.revert_cardpocket)
        self.cb_openhandviewalways = wx.CheckBox(
            self, -1, u"行動不能でも行動選択ダイアログを開く")
        self.cb_openhandviewalways.SetValue(cw.cwpy.setting.openhandviewalways)
        self.cb_showlogwithwheelup = wx.CheckBox(
            self, -1, u"マウスホイールを上に回すとログを表示")
        self.cb_showlogwithwheelup.SetValue(cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG)
        self.cb_showroundautostartbutton = wx.CheckBox(
            self, -1, u"バトルで自動的に行動を開始できるようにする")
        self.cb_showroundautostartbutton.SetValue(cw.cwpy.setting.show_roundautostartbutton)
        self.cb_showautobuttoninentrydialog = wx.CheckBox(
            self, -1, u"新規登録ダイアログに自動ボタンを表示する")
        self.cb_showautobuttoninentrydialog.SetValue(cw.cwpy.setting.show_autobuttoninentrydialog)

        # ダイアログオプション
        self.box_dlg = wx.StaticBox(self, -1, u"ダイアログ")
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
        self.cb_noticeimpossibleaction = wx.CheckBox(
            self, -1, u"不可能な行動を選択した時に警告を表示")
        self.cb_noticeimpossibleaction.SetValue(cw.cwpy.setting.noticeimpossibleaction)

        self._do_layout()
        self._bind()

    def OnQuickDeal(self, event):
        if not self.cb_quickdeal.GetValue():
            self.cb_allquickdeal.SetValue(False)

    def OnAllQuickDeal(self, event):
        if self.cb_allquickdeal.GetValue():
            self.cb_quickdeal.SetValue(True)

    def _bind(self):
        self.Bind(wx.EVT_CHECKBOX, self.OnQuickDeal, self.cb_quickdeal)
        self.Bind(wx.EVT_CHECKBOX, self.OnAllQuickDeal, self.cb_allquickdeal)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        bsizer_wait = wx.StaticBoxSizer(self.box_wait, wx.VERTICAL)
        bsizer_draw = wx.StaticBoxSizer(self.box_draw, wx.VERTICAL)
        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_dlg = wx.StaticBoxSizer(self.box_dlg, wx.VERTICAL)

        bsizer_wait.Add(self.cb_can_skipwait, 0, wx.ALL, 3)
        bsizer_wait.Add(self.cb_can_skipanimation, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_wait.Add(self.cb_can_repeatlclick, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_wait.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_draw.Add(self.cb_quickdeal, 0, wx.ALL, 3)
        bsizer_draw.Add(self.cb_allquickdeal, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.Add(self.cb_showallselectedcards, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.Add(self.cb_showstatustime, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_draw.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_gene.Add(self.cb_showbackpackcard, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_revertcardpocket, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_openhandviewalways, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_showlogwithwheelup, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_showroundautostartbutton, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.Add(self.cb_showautobuttoninentrydialog, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_gene.SetMinSize((SETTINGS_WIDTH, -1))

        bsizer_dlg.Add(self.cb_cautionbeforesaving, 0, wx.ALL, 3)
        bsizer_dlg.Add(self.cb_confirmbeforesaving, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.Add(self.cb_showsavedmessage, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.Add(self.cb_confirmbeforeusingcard, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.Add(self.cb_noticeimpossibleaction, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        bsizer_dlg.SetMinSize((SETTINGS_WIDTH, -1))

        sizer_v1.Add(bsizer_wait, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_draw, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_gene, 0, wx.BOTTOM|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_dlg, 0, wx.EXPAND, 0)
        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class FontSettingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.typenames = {"gothic"       : u"等幅ゴシック",
                          "uigothic"     : u"UI用",
                          "mincho"       : u"等幅明朝",
                          "pmincho"      : u"可変幅明朝",
                          "pgothic"      : u"可変幅ゴシック",
                          "button"       : u"ボタン",
                          "combo"        : u"コンボボックス",
                          "slider"       : u"スライダ",
                          "spin"         : u"スピナ",
                          "tree"         : u"ツリー",
                          "list"         : u"リスト",
                          "tab"          : u"タブ",
                          "menu"         : u"メニュー",
                          "paneltitle"   : u"パネル見出し",
                          "dlgmsg"       : u"ダイアログメッセージ",
                          "dlgtitle"     : u"ダイアログ見出し",
                          "inputname"    : u"名前入力欄",
                          "datadesc"     : u"データ解説文",
                          "charadesc"    : u"キャラクター解説文",
                          "dlglist"      : u"ダイアログリスト",
                          "uselimit"     : u"カード使用回数",
                          "cardname"     : u"カード名",
                          "ccardname"     : u"キャストカード名",
                          "level"        : u"カードレベル",
                          "message"      : u"メッセージ",
                          "selectionbar" : u"選択肢",
                          "logpage"      : u"メッセージログ頁",
                          "sbarpanel"    : u"ステータスパネル",
                          "sbarbtn"      : u"ステータスボタン",
                          "statusnum"    : u"状態値",
                          "screenshot"   : u"撮影情報",
                          }

        self.bases = ("gothic", "pgothic", "mincho", "pmincho", "uigothic")
        self.types = ("button", "combo", "slider", "spin", "tree", "list", "tab", "menu",
                      "paneltitle", "dlgmsg", "dlgtitle", "inputname", "datadesc", "charadesc",
                      "dlglist", "uselimit", "cardname", "ccardname", "level", "message", "selectionbar",
                      "logpage", "sbarpanel", "sbarbtn", "statusnum", "screenshot")

        # フォント配列のロード
        facenames = list(wx.FontEnumerator().GetFacenames())
        facenames.sort()
        str_default = u"[デフォルト]" # デフォルトフォント名
        fontface_array = [str_default]
        types = []
        for base in self.bases:
            types.append(u"[%s]" % (self.typenames[base]))
        for name in facenames:
            if not name.startswith(u"@"):
                fontface_array.append(name)
                types.append(name)

        # フォント表示サンプル
        self.box_example = wx.StaticBox(self, -1, u"表示例")
        self.st_example = wx.StaticText(self, -1, size=(100, 30), style=wx.ALIGN_CENTER)
        self.st_example.SetDoubleBuffered(True)

        # 描画オプション
        self.box_gene = wx.StaticBox(self, -1, u"詳細")
        self.cb_fontsmoothingcardname = wx.CheckBox(self, -1, u"カード名の文字を滑らかにする")
        self.cb_fontsmoothingcardname.SetValue(cw.cwpy.setting.fontsmoothing_cardname)
        self.cb_fontsmoothingstatusbar = wx.CheckBox(self, -1, u"ステータスバーの文字を滑らかにする")
        self.cb_fontsmoothingstatusbar.SetValue(cw.cwpy.setting.fontsmoothing_statusbar)

        def create_grid(seq, faces, editor, cols):
            grid = wx.grid.Grid(self, -1, size=(1, 0), style=wx.BORDER)
            grid.SetDoubleBuffered(True)
            grid.CreateGrid(len(seq), cols)
            grid.DisableDragRowSize()
            grid.SetSelectionMode(wx.grid.Grid.SelectRows)
            grid.SetRowLabelAlignment(wx.LEFT, wx.CENTER)
            grid.SetRowLabelSize(100)
            grid.SetColLabelValue(0, u"フォント名")
            grid.SetColSize(0, 150)
            for i, name in enumerate(seq):
                grid.SetRowLabelValue(i, self.typenames[name])
                grid.SetCellEditor(i, 0, editor)
            return grid

        # 基本フォント
        self.box_base = wx.StaticBox(self, -1, u"基本フォント")
        self.choicebase = wx.grid.GridCellChoiceEditor(fontface_array)
        self.base = create_grid(self.bases, fontface_array, self.choicebase, 1)
        for i, name, in enumerate(self.bases):
            str_font = cw.cwpy.setting.basefont[name]
            if not str_font:
                str_font = str_default
            self.base.SetCellValue(i, 0, str_font)

        # 役割別フォント
        self.box_type = wx.StaticBox(self, -1, u"役割別フォント")
        self.choicetype = wx.grid.GridCellChoiceEditor(types)
        self.type = create_grid(self.types, types, self.choicetype, 5)
        self.type.SetColLabelValue(1, u"サイズ")
        self.type.SetColSize(1, 80)
        self.type.SetColLabelValue(2, u"太字\n(通常)")
        self.type.SetColSize(2, 70)
        self.type.SetColLabelValue(3, u"太字\n(拡大)")
        self.type.SetColSize(3, 70)
        self.type.SetColLabelValue(4, u"斜体")
        self.type.SetColSize(4, 70)
        boolrenderer = wx.grid.GridCellBoolRenderer()
        numberrenderer = wx.grid.GridCellNumberRenderer()
        for i, name in enumerate(self.types):
            _deffonttype, _defface, defpixels, defbold, defbold_upscr, defitalic = cw.cwpy.setting.fonttypes_init[name]
            fonttype, face, pixels, bold, bold_upscr, italic = cw.cwpy.setting.fonttypes[name]
            if fonttype:
                self.type.SetCellValue(i, 0, u"[%s]" % (self.typenames[fonttype]))
            else:
                self.type.SetCellValue(i, 0, face)
            if 0 < defpixels:
                epixels = wx.grid.GridCellNumberEditor(1, 99)
                self.type.SetCellEditor(i, 1, epixels)
                self.type.SetCellValue(i, 1, str(pixels))
                self.type.SetCellRenderer(i, 1, numberrenderer)
            else:
                self.type.SetCellValue(i, 1, u"-")
                self.type.GetOrCreateCellAttr(i, 1).SetReadOnly(True)
            self.type.SetCellAlignment(i, 1, wx.ALIGN_CENTER, 0)
            if not defbold is None:
                ebold = wx.grid.GridCellBoolEditor()
                self.type.SetCellEditor(i, 2, ebold)
                self.type.SetCellValue(i, 2, u"1" if bold else u"")
                self.type.SetCellRenderer(i, 2, boolrenderer)
            else:
                self.type.SetCellValue(i, 2, u"-")
                self.type.GetOrCreateCellAttr(i, 2).SetReadOnly(True)
            self.type.SetCellAlignment(i, 2, wx.ALIGN_CENTER, 0)
            if not defbold_upscr is None:
                ebold_upscr = wx.grid.GridCellBoolEditor()
                self.type.SetCellEditor(i, 3, ebold_upscr)
                self.type.SetCellValue(i, 3, u"1" if bold_upscr else u"")
                self.type.SetCellRenderer(i, 3, boolrenderer)
            else:
                self.type.SetCellValue(i, 3, u"-")
                self.type.GetOrCreateCellAttr(i, 3).SetReadOnly(True)
            self.type.SetCellAlignment(i, 3, wx.ALIGN_CENTER, 0)
            if not defitalic is None:
                eitalic = wx.grid.GridCellBoolEditor()
                self.type.SetCellEditor(i, 4, eitalic)
                self.type.SetCellValue(i, 4, u"1" if italic else u"")
                self.type.SetCellRenderer(i, 4, boolrenderer)
            else:
                self.type.SetCellValue(i, 4, u"-")
                self.type.GetOrCreateCellAttr(i, 4).SetReadOnly(True)
            self.type.SetCellAlignment(i, 4, wx.ALIGN_CENTER, 0)

        self.st_example.SetLabel(self.get_basefontface(self.bases[0]))
        font = wx.Font(18, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
                       face=self.st_example.GetLabel())
        self.st_example.SetFont(font)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.base.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectFontBase)
        self.base.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChangeBase)
        self.base.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnEditorCreatedBase)
        self.type.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectFontType)
        self.type.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChangeType)
        self.type.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnEditorCreatedType)

    def _select_base(self, i):
        if 0 <= i:
            self.st_example.SetLabel(self.get_basefontface(self.bases[i]))
            font = wx.Font(18, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
                           face=self.st_example.GetLabel())
            self.st_example.SetFont(font)
            self.Layout()

    def OnCellChangeBase(self, event):
        self._select_base(self.base.GetGridCursorRow())

    def OnSelectFontBase(self, event):
        self._select_base(event.TopRow)
        event.Skip()

    def OnEditorCreatedBase(self, event):
        self.choicebase.GetControl().Bind(wx.EVT_COMBOBOX, self.OnCellChangeBase)

    def get_basefontface(self, fonttype):
        ctrl = self.choicebase.GetControl()
        if ctrl and ctrl.IsShown():
            face = ctrl.GetValue()
        else:
            face = self.base.GetCellValue(self.bases.index(fonttype), 0)
        if face == u"[デフォルト]":
            face = cw.cwpy.rsrc.fontnames_init[fonttype]
        return face

    def _select_type(self, i):
        if 0 <= i:
            self.st_example.SetLabel(self.get_typefontface(self.types[i]))
            font = wx.Font(18, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
                           face=self.st_example.GetLabel())
            self.st_example.SetFont(font)
            self.Layout()

    def OnCellChangeType(self, event):
        self._select_type(self.type.GetGridCursorRow())

    def OnSelectFontType(self, event):
        self._select_type(event.TopRow)
        event.Skip()

    def OnEditorCreatedType(self, event):
        ctrl = self.choicetype.GetControl()
        if ctrl:
           self.choicetype.GetControl().Bind(wx.EVT_COMBOBOX, self.OnCellChangeType)

    def get_typefontface(self, fonttype):
        ctrl = self.choicetype.GetControl()
        if ctrl and ctrl.IsShown():
            face = ctrl.GetValue()
        else:
            face = self.type.GetCellValue(self.types.index(fonttype), 0)
        for basename in self.bases:
            if u"[%s]" % self.typenames[basename] == face:
                face = self.get_basefontface(basename)
                break
        return face

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.HORIZONTAL)

        bsizer_left = wx.BoxSizer(wx.VERTICAL)

        bsizer_example = wx.StaticBoxSizer(self.box_example, wx.VERTICAL)
        bsizer_example.Add(self.st_example, 1, wx.ALL|wx.EXPAND, 3)

        bsizer_gene = wx.StaticBoxSizer(self.box_gene, wx.VERTICAL)
        bsizer_gene.Add(self.cb_fontsmoothingcardname, 0, wx.ALL, 3)
        bsizer_gene.Add(self.cb_fontsmoothingstatusbar, 0, wx.LEFT|wx.BOTTOM|wx.RIGHT, 3)

        bsizer_base = wx.StaticBoxSizer(self.box_base, wx.VERTICAL)
        bsizer_base.Add(self.base, 1, wx.ALL|wx.EXPAND, 3)

        bsizer_left.Add(bsizer_example, 0, wx.EXPAND|wx.BOTTOM, 3)
        bsizer_left.Add(bsizer_gene, 0, wx.EXPAND|wx.BOTTOM, 3)
        bsizer_left.Add(bsizer_base, 1, wx.EXPAND, 3)

        bsizer_type = wx.StaticBoxSizer(self.box_type, wx.VERTICAL)
        bsizer_type.Add(self.type, 1, wx.ALL|wx.EXPAND, 3)

        sizer_v1.Add(bsizer_left, 1, wx.RIGHT|wx.EXPAND, 5)
        sizer_v1.Add(bsizer_type, 1, wx.EXPAND, 5)
        sizer.Add(sizer_v1, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
