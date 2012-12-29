#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import wx.aui
import wx.lib.mixins.listctrl as listmix

import cw


# ID
ID_COMPSTAMP = wx.NewId()
ID_GOSSIP = wx.NewId()
ID_MONEY = wx.NewId()
ID_CARD = wx.NewId()
ID_MEMBER = wx.NewId()
ID_COUPON = wx.NewId()
ID_STATUS = wx.NewId()
ID_RECOVERY = wx.NewId()
ID_AREA = wx.NewId()
ID_SELECTION = wx.NewId()
ID_BREAK = wx.NewId()
ID_UPDATE = wx.NewId()
ID_BATTLE = wx.NewId()
ID_PACK = wx.NewId()
ID_FRIEND = wx.NewId()
ID_INFO = wx.NewId()
ID_SAVE = wx.NewId()
ID_LOAD = wx.NewId()
ID_RESET = wx.NewId()
ID_PLAY = wx.NewId()
ID_STEP = wx.NewId()
ID_PAUSE = wx.NewId()
ID_STOP = wx.NewId()


class Debugger(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self, parent, -1, u"CardWirthPy Debugger", size=wx.DefaultSize,
            style=wx.SIMPLE_BORDER|wx.CLIP_CHILDREN|wx.CAPTION|wx.RESIZE_BOX|
            wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        self.SetClientSize((550, 450))
        # set icon
        cw.cwpy.frame.set_icon(self)
        # aui manager
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        # create status bar
        self.statusbar = self.CreateStatusBar(2, wx.ST_SIZEGRIP)
        self.statusbar.SetStatusWidths([0, -1])
        # create menu
        mb = wx.MenuBar()
        file_menu = wx.Menu()
        view_menu = wx.Menu()
        yado_menu = wx.Menu()
        advr_menu = wx.Menu()
        scen_menu = wx.Menu()
        mb.Append(file_menu, u"ファイル")
        mb.Append(view_menu, u"表示")
        mb.Append(yado_menu, u"宿")
        mb.Append(advr_menu, u"冒険者")
        mb.Append(scen_menu, u"シナリオ")
        self.SetMenuBar(mb)
        # create main toolbar
        rsrc = cw.cwpy.rsrc.debugs
        self.tb1 = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb1.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_comp = self.tb1.AddLabelTool(
            ID_COMPSTAMP, u"終了印", rsrc["COMPSTAMP"],
            shortHelp=u"終了印リストを編集します。")
        self.tl_gossip = self.tb1.AddLabelTool(
            ID_GOSSIP, u"ゴシップ", rsrc["GOSSIP"],
            shortHelp=u"ゴシップリストを編集します。")
        self.tl_money = self.tb1.AddLabelTool(
            ID_MONEY, u"所持金", rsrc["MONEY"],
            shortHelp=u"所持金を変更します。")
        self.tl_card = self.tb1.AddLabelTool(
            ID_CARD, u"手札配布", rsrc["CARD"],
            shortHelp=u"手札カードを配布します。")
        self.tb1.AddSeparator()
        self.tb1.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_member = self.tb1.AddLabelTool(
            ID_MEMBER, u"冒険者", rsrc["MEMBER"],
            shortHelp=u"冒険者の情報を編集します。")
        self.tl_coupon = self.tb1.AddLabelTool(
            ID_COUPON, u"経歴", rsrc["COUPON"],
            shortHelp=u"冒険者の経歴を編集します。")
        self.tl_status = self.tb1.AddLabelTool(
            ID_STATUS, u"状態", rsrc["STATUS"],
            shortHelp=u"冒険者の状態を編集します。")
        self.tl_recovery = self.tb1.AddLabelTool(
            ID_RECOVERY, u"全回復", rsrc["RECOVERY"],
            shortHelp=u"全冒険者を全回復させます。")
        self.tb1.Realize()

        # create scenario toolbar
        self.tb2 = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb2.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_break = self.tb2.AddLabelTool(
            ID_BREAK, u"シナリオ中断", rsrc["BREAK"],
            shortHelp=u"シナリオを中断して、冒険者の宿に戻ります。")
        self.tl_update = self.tb2.AddLabelTool(
            ID_UPDATE, "場面更新", rsrc["UPDATE"],
            shortHelp=u"最新の情報に更新します。")
        self.tb2.AddSeparator()
        self.tl_battle = self.tb2.AddLabelTool(
            ID_BATTLE, u"戦闘", rsrc["BATTLE"],
            shortHelp=u"バトルを選択して戦闘を開始します。")
        self.tl_pack = self.tb2.AddLabelTool(
            ID_PACK, u"パッケージ", rsrc["PACK"],
            shortHelp=u"パッケージを選択してイベントを開始します。")
        self.tl_friend = self.tb2.AddLabelTool(
            ID_FRIEND, u"同行者", rsrc["FRIEND"],
            shortHelp=u"同行者カードの取得・破棄を行います。")
        self.tl_info = self.tb2.AddLabelTool(
            ID_INFO, u"情報", rsrc["INFO"],
            shortHelp=u"情報カードの取得・破棄を行います。")
        self.tb2.AddSeparator()
        self.tb2.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_save = self.tb2.AddLabelTool(
            ID_SAVE, u"セーブ", rsrc["SAVE"],
            shortHelp=u"状況を記録します。")
        self.tl_load = self.tb2.AddLabelTool(
            ID_LOAD, u"ロード", rsrc["LOAD"],
            shortHelp=u"状況を再現します。")
        self.tl_reset = self.tb2.AddLabelTool(
            ID_RESET, u"リセット", rsrc["RESET"],
            shortHelp=u"初期状態に戻します。")
        self.tb2.Realize()

        # create event control bar
        self.tb_event = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_event.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_step = self.tb_event.AddLabelTool(
            ID_STEP, u"1コンテント実行", rsrc["EVTCTRL_STEP"],
            shortHelp=u"イベントを1コンテントだけ実行します。")
        self.tl_pause = self.tb_event.AddCheckLabelTool(
            ID_PAUSE, u"イベント一時停止", rsrc["EVTCTRL_PAUSE"],
            shortHelp=u"イベントを一時停止します。")
        self.tl_stop = self.tb_event.AddLabelTool(
            ID_STOP, u"イベント強制終了", rsrc["EVTCTRL_STOP"],
            shortHelp=u"イベントを強制終了します。")
        self.tb_event.AddSeparator()
        self.sc_waittime = wx.SpinCtrl(
            self.tb_event, -1, u"イベント待機時間", size=(40, 20))
        self.sc_waittime.SetRange(0, 99)
        self.sc_waittime.SetValue(0)
        self.tb_event.AddControl(self.sc_waittime)
        st = wx.StaticText(self.tb_event, -1, u" (1=0.1秒)")
        self.tb_event.AddControl(st)
        self.tb_event.Realize()
        # create area toolbar
        self.tb_area = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_area.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_area = self.tb_area.AddLabelTool(
            ID_AREA, "", rsrc["AREA"],
            shortHelp=u"エリアを選択して場面を変更します。")

        # _battletoolでボタンの切り替えを判別
        if cw.cwpy.is_battlestatus():
            self.tl_area.SetBitmap1(rsrc["BATTLECANCEL"])
            self.tl_area.SetShortHelp(u"戦闘を中断します。")
            self.tl_area._battletool = True
        else:
            self.tl_area._battletool = False

        self.tb_area.AddSeparator()
        self.st_area = wx.StaticText(
            self.tb_area, -1, cw.cwpy.sdata.get_areaname(), size=(200, -1))
        self.tb_area.AddControl(self.st_area)
        self.tb_area.Realize()

        # create selection toolbar
        self.tb_select = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_select.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_select = self.tb_select.AddLabelTool(
            ID_SELECTION, "",
            rsrc["SELECTION"], shortHelp=u"選択中のキャラクターを変更します。")
        self.tb_select.AddSeparator()
        self.st_select = wx.StaticText(
            self.tb_select, -1, cw.cwpy.event.get_selectedmembername(),
            size=(200, -1))
        self.tb_select.AddControl(self.st_select)
        self.tb_select.Realize()

        # create variable view
        self.view_var = VariableListCtrl(self)
        # create eventtree view
        self.view_tree = EventTreeCtrl(self)

        # add pane
        self._mgr.AddPane(
            self.view_var,
            wx.aui.AuiPaneInfo().Name("list_var").MinSize((200, -1)).
            Left().CloseButton(True).MaximizeButton(True).
            Caption(u"状態変数"))
        self._mgr.AddPane(
            self.view_tree,
            wx.aui.AuiPaneInfo().Name("view_tree").
            Caption(u"イベント").CenterPane())
        # add toolbar pane
        self._mgr.AddPane(
            self.tb1, wx.aui.AuiPaneInfo().Name("tb1").
            Caption(u"メインツールバー").ToolbarPane().Top().
            LeftDockable(False).RightDockable(False))
        self._mgr.AddPane(
            self.tb2, wx.aui.AuiPaneInfo().Name("tb2").
            Caption(u"シナリオツールバー").ToolbarPane().Top().
            LeftDockable(False).RightDockable(False))
        self._mgr.AddPane(
            self.tb_area, wx.aui.AuiPaneInfo().Name("tb_area").Movable(False).
            Caption(u"エリアバー").ToolbarPane().Top().Row(1).
            LeftDockable(False).RightDockable(False))
        self._mgr.AddPane(
            self.tb_select, wx.aui.AuiPaneInfo().Name("tb_select").
            Caption(u"メンバ選択バー").ToolbarPane().Top().Row(1).
            LeftDockable(False).RightDockable(False))
        self._mgr.AddPane(
            self.tb_event, wx.aui.AuiPaneInfo().Name("tb_event").
            Caption(u"イベントコントロールバー").ToolbarPane().Top().Row(2).
            LeftDockable(False).RightDockable(False))

        self._mgr.Update()
        # ボタン更新
        self.refresh_tools()
        # bind
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_TOOL, self.OnAreaTool, id=ID_AREA)
        self.Bind(wx.EVT_TOOL, self.OnSelectionTool, id=ID_SELECTION)
        self.Bind(wx.EVT_TOOL, self.OnStepTool, id=ID_STEP)
        self.Bind(wx.EVT_TOOL, self.OnPauseTool, id=ID_PAUSE)
        self.Bind(wx.EVT_TOOL, self.OnStopTool, id=ID_STOP)
        self.Bind(wx.EVT_TOOL, self.OnRecoveryTool, id=ID_RECOVERY)
        self.Bind(wx.EVT_TOOL, self.OnPackageTool, id=ID_PACK)
        self.Bind(wx.EVT_TOOL, self.OnBattleTool, id=ID_BATTLE)
        self.Bind(wx.EVT_TOOL, self.OnFriendTool, id=ID_FRIEND)
        self.Bind(wx.EVT_TOOL, self.OnInfoTool, id=ID_INFO)
        self.Bind(wx.EVT_TOOL, self.OnUpdateTool, id=ID_UPDATE)
        self.Bind(wx.EVT_TOOL, self.OnBreakTool, id=ID_BREAK)
        self.Bind(wx.EVT_TOOL, self.OnResetTool, id=ID_RESET)

    def OnClose(self, event):
        cw.cwpy.frame.debugger = None
        self.Destroy()

    def OnDestroy(self, event):
        # デタッチしていたAuiToolBarをメインフレームにドッキングすると
        # Destroyイベントが呼ばれるようなので、それと区別
        if self.IsBeingDeleted():
            cw.cwpy.frame.debugger = None

    def OnResetTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            func = cw.cwpy.sdata.reset_variables
            cw.cwpy.exec_func(func)

    def OnBreakTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent()\
                                        and not cw.cwpy.is_battlestatus():
            func = cw.cwpy.interrupt_adventure
            cw.cwpy.exec_func(func)

    def OnUpdateTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            func = cw.cwpy.change_area
            cw.cwpy.exec_func(func, cw.cwpy.areaid, False, True)

    def OnRecoveryTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            def recovery_all():
                for pcard in cw.cwpy.get_pcards("unreversed"):
                    cw.cwpy.sounds["harvest"].play()
                    cw.animation.animate_sprite(pcard, "hide")
                    pcard.set_fullrecovery()
                    pcard.update_image()
                    cw.animation.animate_sprite(pcard, "deal")

            cw.cwpy.exec_func(recovery_all)

    def OnInfoTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.infos.iteritems() if key > 0]
            seq.sort()
            infoids = set([i.id for i in cw.cwpy.sdata.infocards])
            choices = []
            selections = []

            for index, i in enumerate(seq):
                choices.append(i[1])

                if i[0] in infoids:
                    selections.append(index)

            dlg = wx.MultiChoiceDialog(
                self, u"チェックマークの付け外しで情報カードの" +
                u"取得・破棄ができます",
                u"情報カードの選択", choices)
            dlg.SetSelections(selections)

            if dlg.ShowModal() == wx.ID_OK:
                for index in dlg.GetSelections():
                    key = seq[index][0]

                    if key in infoids:
                        infoids.remove(key)
                    else:
                        path = cw.cwpy.sdata.infos[key][1]
                        e = cw.data.xml2element(path, "Property")
                        header = cw.header.InfoCardHeader(e)
                        cw.cwpy.sdata.infocards.insert(0, header)

                headers = [i for i in cw.cwpy.sdata.infocards
                                                            if i.id in infoids]

                for header in headers:
                    cw.cwpy.sdata.infocards.remove(header)

            dlg.Destroy()

    def OnFriendTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.casts.iteritems() if key > 0]
            seq.sort()
            friendids = set([i.id for i in cw.cwpy.sdata.friendcards])
            choices = []
            selections = []

            for index, i in enumerate(seq):
                choices.append(i[1])

                if i[0] in friendids:
                    selections.append(index)

            dlg = wx.MultiChoiceDialog(
                self, u"チェックマークの付け外しでキャストの" +
                u"加入・離脱ができます",
                u"キャストの選択", choices)
            dlg.SetSelections(selections)

            if dlg.ShowModal() == wx.ID_OK:
                if len(dlg.GetSelections()) > 6:
                    s = u"キャストは6名までしか加入させられません。"
                    mdlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s)
                    mdlg.ShowModal()
                    mdlg.Destroy()
                else:
                    for index in dlg.GetSelections():
                        key = seq[index][0]

                        if key in friendids:
                            friendids.remove(key)
                        else:
                            fcard = cw.sprite.card.FriendCard(key)
                            cw.cwpy.sdata.friendcards.append(fcard)

                    fcards = [i for i in cw.cwpy.sdata.friendcards
                                                        if i.id in friendids]

                    for fcard in fcards:
                        cw.cwpy.sdata.friendcards.remove(fcard)

                    # キャンプ画面を開いている場合はエリア再表示
                    if cw.cwpy.areaid == cw.AREA_CAMP:
                        func = cw.cwpy.change_area
                        cw.cwpy.exec_func(func, cw.AREA_CAMP, False)

            dlg.Destroy()

    def OnBattleTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.battles.iteritems() if key > 0]
            seq.sort()
            choices = [s for key, s in seq]
            dlg = wx.SingleChoiceDialog(
                self, u"開始するバトルを選択してください。",
                u"バトルの選択", choices)

            if dlg.ShowModal() == wx.ID_OK:
                func = cw.cwpy.change_battlearea
                cw.cwpy.exec_func(func, seq[dlg.GetSelection()][0])

            dlg.Destroy()

    def OnPackageTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.packs.iteritems() if key > 0]
            seq.sort()
            choices = [s for key, s in seq]
            dlg = wx.SingleChoiceDialog(
                self, u"実行するパッケージを選択してください。",
                u"パッケージの選択", choices)

            if dlg.ShowModal() == wx.ID_OK:
                id = seq[dlg.GetSelection()][0]
                path = cw.cwpy.sdata.packs[id][1]
                e = cw.data.xml2element(path, "Events")
                event = cw.event.EventEngine(e)

                if event.events:
                    cw.cwpy.event.nowrunningpacks[id] = event
                    func = event.events[0].start
                    cw.cwpy.exec_func(func)

            dlg.Destroy()

    def OnAreaTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            # 戦闘中は戦闘終了
            if cw.cwpy.battle:
                func = cw.cwpy.battle.end
                cw.cwpy.exec_func(func)
            # 非戦闘中はエリア移動
            else:
                seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.areas.iteritems() if key > 0]
                seq.sort()
                choices = [s for key, s in seq]
                dlg = wx.SingleChoiceDialog(
                    self, u"移動するエリアを選択してください。",
                    u"エリアの選択", choices)

                if dlg.ShowModal() == wx.ID_OK:
                    func = cw.cwpy.change_area
                    cw.cwpy.exec_func(func, seq[dlg.GetSelection()][0])

                dlg.Destroy()

    def OnSelectionTool(self, event):
        if cw.cwpy.is_playingscenario() and cw.cwpy.is_runningevent():
            ccards = cw.cwpy.get_pcards()
            ccards.extend(cw.cwpy.get_ecards())
            ccards.extend(cw.cwpy.get_fcards())
            choices = []

            for ccard in ccards:
                if isinstance(ccard, cw.character.Enemy):
                    choices.append("Enemy: " + ccard.name)
                elif isinstance(ccard, cw.character.Friend):
                    choices.append("Friend: " + ccard.name)
                else:
                    choices.append("Player: " + ccard.name)

            dlg = wx.SingleChoiceDialog(
                self, u"キャラクターを選択してください。",
                u"メンバの選択", choices)

            if dlg.ShowModal() == wx.ID_OK:
                cw.cwpy.event.set_selectedmember(ccards[dlg.GetSelection()])

            dlg.Destroy()

    def OnStepTool(self, event):
        if cw.cwpy.is_showingmessage():
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.keyevent.keydown(wx.WXK_RETURN)
        else:
            cw.cwpy.event._step = True
            cw.cwpy.event._paused = False

    def OnPauseTool(self, event):
        # メッセージウィンドウ表示中の場合は一時停止できない
        cw.cwpy.event._paused = self.tl_pause.IsToggled()
        cw.cwpy.event._step = False

        self.tl_step.Enable(cw.cwpy.event._paused and cw.cwpy.is_runningevent())
        self.tb_event.Realize()

    def OnStopTool(self, event):
        cw.cwpy.event._step = False
        if cw.cwpy.is_playingscenario() and cw.cwpy.is_runningevent():
            # メッセージウィンドウ表示中の場合で処理を分ける
            if cw.cwpy.is_showingmessage():
                mwin = cw.cwpy.get_messagewindow()
                mwin.result = cw.event.EffectBreakError()
            else:
                cw.cwpy.event._stoped = True

            # SetToggleが効かないため
            if self.tl_pause.IsToggled():
                self.tl_pause.Toggle()

        self.tl_step.Enable(False)
        self.tb_event.Realize()

    def refresh_areaname(self):
        self.st_area.SetLabel(cw.cwpy.sdata.get_areaname())

        # ツールボタンの表示を切り替えるかどうか
        if cw.cwpy.is_battlestatus() == self.tl_area._battletool:
            self.tb_area.Refresh()
        else:
            if cw.cwpy.is_battlestatus():
                self.tl_area.SetBitmap1(cw.cwpy.rsrc.debugs["BATTLECANCEL"])
                self.tl_area.SetShortHelp(u"戦闘を中断します。")
                self.tl_area._battletool = True
            else:
                self.tl_area.SetBitmap1(cw.cwpy.rsrc.debugs["AREA"])
                self.tl_area.SetShortHelp(u"エリアを選択して場面を変更します。")
                self.tl_area._battletool = False

            self.tb_area.Realize()
            self._mgr.Update()

    def refresh_selectedmembername(self):
        self.st_select.SetLabel(cw.cwpy.event.get_selectedmembername())
        self.tb_select.Refresh()

    def refresh_tools(self):
        self.tl_comp.Enable(False)
        self.tl_gossip.Enable(False)
        self.tl_money.Enable(False)
        self.tl_card.Enable(False)
        self.tl_member.Enable(False)
        self.tl_coupon.Enable(False)
        self.tl_status.Enable(False)
        self.tl_recovery.Enable(False)
        self.tl_break.Enable(False)
        self.tl_update.Enable(False)
        self.tl_battle.Enable(False)
        self.tl_pack.Enable(False)
        self.tl_friend.Enable(False)
        self.tl_info.Enable(False)
        self.tl_save.Enable(False)
        self.tl_load.Enable(False)
        self.tl_reset.Enable(False)
        self.tl_step.Enable(False)
        self.tl_pause.Enable(False)
        self.tl_stop.Enable(False)
        self.tl_select.Enable(False)
        self.tl_area.Enable(False)

        if cw.cwpy.ydata:
            self.tl_comp.Enable(True)
            self.tl_gossip.Enable(True)
            self.tl_money.Enable(True)
            self.tl_card.Enable(True)
            self.tl_member.Enable(True)
            self.tl_coupon.Enable(True)

        if cw.cwpy.is_playingscenario():
            self.tl_pause.Enable(True)
            if cw.cwpy.is_runningevent():
                self.tl_select.Enable(True)
                self.tl_stop.Enable(True)
            else:
                if not cw.cwpy.is_battlestatus():
                    self.tl_break.Enable(True)
                    self.tl_save.Enable(True)
                    self.tl_load.Enable(True)

                if not cw.cwpy.battle or not cw.cwpy.battle.is_running():
                    self.tl_status.Enable(True)
                    self.tl_recovery.Enable(True)
                    self.tl_update.Enable(True)
                    self.tl_battle.Enable(True)
                    self.tl_pack.Enable(True)
                    self.tl_friend.Enable(True)
                    self.tl_info.Enable(True)
                    self.tl_reset.Enable(True)
                    self.tl_area.Enable(True)
        else:
            self.tl_pause.Enable(True)

        self.tl_step.Enable(cw.cwpy.event._paused and cw.cwpy.is_runningevent())

        self.tb1.Realize()
        self.tb2.Realize()
        self.tb_area.Realize()
        self.tb_select.Realize()
        self.tb_event.Realize()
        self._mgr.Update()

class VariableListCtrl(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(
            self, parent, -1, style=wx.LC_REPORT|wx.BORDER_NONE|
            wx.LC_SORT_ASCENDING|wx.LC_VIRTUAL)
        self.list = []
        self.imglist = wx.ImageList(16, 16)
        self.imgidx_flag = self.imglist.Add(cw.cwpy.rsrc.debugs["FLAG"])
        self.imgidx_step = self.imglist.Add(cw.cwpy.rsrc.debugs["STEP"])
        self.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, u"名称")
        self.InsertColumn(1, u"現在値")
        self.SetColumnWidth(0, 120)
        self.SetColumnWidth(1, 80)
        self.refresh_variablelist()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)

    def OnDClick(self, event):
        # On DClick Item
        if self.GetSelectedItemCount() == 1:
            item = self.list[self.GetFirstSelected()]

            if isinstance(item, cw.data.Flag):
                choices = [item.truename, item.falsename]
            elif isinstance(item, cw.data.Step):
                choices = item.valuenames

            s = u"変更したい値を選択してください。"
            dlg = wx.SingleChoiceDialog(self.Parent, s, item.name, choices)

            if dlg.ShowModal() == wx.ID_OK:
                if isinstance(item, cw.data.Flag):
                    item.set(not bool(dlg.GetSelection()))
                    func = item.redraw_cards
                    cw.cwpy.exec_func(func)
                elif isinstance(item, cw.data.Step):
                    item.set(dlg.GetSelection())

            dlg.Destroy()

    def OnGetItemText(self, row, col):
        i = self.list[row]

        if col == 0:
            return i.name
        elif isinstance(i, cw.data.Flag):
            return i.get_valuename()
        elif isinstance(i, cw.data.Step):
            return i.get_valuename()
        else:
            return ""

    def OnGetItemImage(self, row):
        i = self.list[row]

        if isinstance(i, cw.data.Flag):
            return self.imgidx_flag
        elif isinstance(i, cw.data.Step):
            return self.imgidx_step
        else:
            return -1

    def refresh_variable(self, variable):
        """引数のアイテムのデータを更新する。
        item: Flag or Step
        """
        try:
            itemid = self.list.index(variable)
            self.RefreshItem(itemid)
        except:
            self.refresh_variablelist()

    def refresh_variablelist(self):
        self.list = []
        self.SetItemCount(0)

        if cw.cwpy.is_playingscenario():
            self.list = cw.cwpy.sdata.steps.values()
            cw.util.sort_by_attr(self.list, "name")
            seq = cw.cwpy.sdata.flags.values()
            cw.util.sort_by_attr(seq, "name")
            self.list.extend(seq)
            self.SetItemCount(len(self.list))

        self.Refresh()

class EventTreeCtrl(wx.TreeCtrl):
    def __init__(self, parent):
        wx.TreeCtrl.__init__(
            self, parent, style=wx.TR_HIDE_ROOT|wx.TR_NO_BUTTONS)
        # 現在実行中のContent(item)
        self.activeitem = None
        # itemの辞書(keyはコンテントデータ)
        self.items = {}
        self.imglist = wx.ImageList(16, 16)
        self.imgidxs = {}

        for key, value in cw.cwpy.rsrc.debugs.iteritems():
            if key.startswith("EVT_"):
                self.imgidxs[key] = self.imglist.Add(value)

        self.SetImageList(self.imglist)
        self.refresh_tree()
        self.refresh_activeitem()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectionChanged)

    def OnSelectionChanged(self, event):
        try:
            item = self.GetSelection()
            data = self.GetItemPyData(item)
            content = cw.content.get_content(data)
            self.Parent.statusbar.SetStatusText(content.get_status(), 1)
        except:
            pass

    def OnDClick(self, event):
        item = self.GetSelection()

        if item:
            print self.GetItemPyData(item)

    def refresh_activeitem(self):
        self.UnselectAll()
        event = cw.cwpy.event.get_event()

        if event and event.cur_content in self.items:
            if self.activeitem:
                content = self.GetItemPyData(self.activeitem)
                parent = self.GetItemParent(self.activeitem)
                parent = self.GetItemPyData(parent)
                s = self.get_contentname(parent, content)
                self.SetItemText(self.activeitem, s)
                self.SetItemTextColour(self.activeitem, wx.BLACK)

            self.activeitem = self.items[event.cur_content]
            self.SelectItem(self.activeitem)
            s = self.GetItemText(self.activeitem) + u" // ACTIVE!"
            self.SetItemText(self.activeitem, s)
            self.SetItemTextColour(self.activeitem, wx.RED)

    def refresh_tree(self):
        self.Parent.statusbar.SetStatusText("", 1)
        self.activeitem = None
        self.items = {}
        self.DeleteAllItems()
        event = cw.cwpy.event.get_event()

        if event:
            root = self.AddRoot("Event Root")
            self.SetPyData(root, None)

            for name, tree in event.trees.iteritems():
                self.set_content(root, tree, name)

        self.ExpandAll()

    def set_content(self, parentitem, content, name):
        item = self.AppendItem(parentitem, name)
        self.SetPyData(item, content)
        s = "EVT_" + content.tag.upper()

        if "type" in content.attrib:
            s += "_" + content.get("type").upper()

        self.SetItemImage(item, self.imgidxs.get(s, -1), wx.TreeItemIcon_Normal)
        self.items[content] = item
        element = content.find("Contents")

        if element is not None:
            for e in element:
                self.set_content(item, e, self.get_contentname(content, e))

    def get_contentname(self, parent, child):
        """分岐コンテントの子コンテント見出し取得。"""
        content = cw.content.get_content(parent)

        if content:
            return content.get_childname(child)
        else:
            return ""

def main():
    pass

if __name__ == "__main__":
    main()
