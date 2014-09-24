#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
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
ID_SHOW_PARTY = wx.NewId()
ID_HIDE_PARTY = wx.NewId()
ID_BGM = wx.NewId()
ID_BREAK = wx.NewId()
ID_UPDATE = wx.NewId()
ID_REDISPLAY = wx.NewId()
ID_BATTLE = wx.NewId()
ID_PACK = wx.NewId()
ID_FRIEND = wx.NewId()
ID_INFO = wx.NewId()
ID_SAVE = wx.NewId()
ID_LOAD = wx.NewId()
ID_LOAD_YADO = wx.NewId()
ID_RESET = wx.NewId()
ID_STEPRETURN = wx.NewId()
ID_STEPOVER = wx.NewId()
ID_STEPIN = wx.NewId()
ID_PAUSE = wx.NewId()
ID_STOP = wx.NewId()
ID_ROUND = wx.NewId()
ID_STARTEVENT = wx.NewId()


class Debugger(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self, parent, -1, u"CardWirthPy Debugger", size=wx.DefaultSize,
            style=wx.CLIP_CHILDREN|wx.CAPTION|wx.RESIZE_BOX|
            wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        self.SetClientSize((590, cw.cwpy.frame.GetClientSize()[1]))
        # set icon
        cw.cwpy.frame.set_icon(self)
        # aui manager
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        # create status bar
        self.statusbar = self.CreateStatusBar(2, wx.ST_SIZEGRIP)
        self.statusbar.SetStatusWidths([0, -1])

        # 最後に強制実行したイベントが属するファイルパス
        self._currentfpath = ""
        # 最後にイベントを強制実行した時、隠蔽カードを表示していたか
        self._showhiddencards = False

        rsrc = cw.cwpy.rsrc.debugs

        # create menu
        mb = wx.MenuBar()
        file_menu = wx.Menu()
        edit_menu = wx.Menu()
        scenario_menu = wx.Menu()
        run_menu = wx.Menu()
        mb.Append(file_menu, u"ファイル(&F)")
        mb.Append(edit_menu, u"編集(&E)")
        mb.Append(scenario_menu, u"シナリオ(&S)")
        mb.Append(run_menu, u"実行(&R)")

        self.mi_save = wx.MenuItem(file_menu, ID_SAVE, u"セーブ(&S)\tCtrl+S",
                         u"状況を記録します。")
        self.mi_save.SetBitmap(rsrc["SAVE"])
        file_menu.AppendItem(self.mi_save)
        self.mi_load = wx.MenuItem(file_menu, ID_LOAD, u"ロード(&L)\tCtrl+O",
                         u"状況を再現します。")
        self.mi_load.SetBitmap(rsrc["LOAD"])
        file_menu.AppendItem(self.mi_load)
        file_menu.AppendSeparator()
        self.mi_reset = wx.MenuItem(file_menu, ID_RESET, u"リセット(&R)",
                         u"初期状態に戻します。")
        self.mi_reset.SetBitmap(rsrc["RESET"])
        file_menu.AppendItem(self.mi_reset)
        file_menu.AppendSeparator()
        self.mi_loadyado = wx.MenuItem(file_menu, ID_LOAD_YADO, u"最終セーブに戻す(&R)\tCtrl+L",
                         u"最後にセーブした状態に戻します。")
        self.mi_loadyado.SetBitmap(rsrc["LOAD_YADO"])
        file_menu.AppendItem(self.mi_loadyado)
        file_menu.AppendSeparator()
        self.mi_break = wx.MenuItem(file_menu, ID_BREAK, u"シナリオ中断(&E)\tCtrl+X",
                         u"シナリオを中断して、冒険者の宿に戻ります。")
        self.mi_break.SetBitmap(rsrc["BREAK"])
        file_menu.AppendItem(self.mi_break)

        self.mi_comp = wx.MenuItem(edit_menu, ID_COMPSTAMP, u"終了印(&O)",
                         u"終了印リストを編集します。")
        self.mi_comp.SetBitmap(rsrc["COMPSTAMP"])
        edit_menu.AppendItem(self.mi_comp)
        self.mi_gossip = wx.MenuItem(edit_menu, ID_GOSSIP, u"ゴシップ(&G)",
                         u"ゴシップリストを編集します。")
        self.mi_gossip.SetBitmap(rsrc["GOSSIP"])
        edit_menu.AppendItem(self.mi_gossip)
        self.mi_money = wx.MenuItem(edit_menu, ID_MONEY, u"所持金(&M)",
                         u"所持金を変更します。")
        self.mi_money.SetBitmap(rsrc["MONEY"])
        edit_menu.AppendItem(self.mi_money)
        self.mi_card = wx.MenuItem(edit_menu, ID_CARD, u"手札配布(&D)",
                         u"手札カードを配布します。")
        self.mi_card.SetBitmap(rsrc["CARD"])
        edit_menu.AppendItem(self.mi_card)
        edit_menu.AppendSeparator()
        self.mi_member = wx.MenuItem(edit_menu, ID_MEMBER, u"冒険者(&A)",
                         u"冒険者の情報を編集します。")
        self.mi_member.SetBitmap(rsrc["MEMBER"])
        edit_menu.AppendItem(self.mi_member)
        self.mi_coupon = wx.MenuItem(edit_menu, ID_COUPON, u"経歴(&C)",
                         u"冒険者の経歴を編集します。")
        self.mi_coupon.SetBitmap(rsrc["COUPON"])
        edit_menu.AppendItem(self.mi_coupon)
        self.mi_status = wx.MenuItem(edit_menu, ID_STATUS, u"状態(&S)",
                         u"冒険者の状態を編集します。")
        self.mi_status.SetBitmap(rsrc["STATUS"])
        edit_menu.AppendItem(self.mi_status)
        self.mi_recovery = wx.MenuItem(edit_menu, ID_RECOVERY, u"全回復(&L)\tCtrl+R",
                         u"全冒険者を全回復させます。")
        self.mi_recovery.SetBitmap(rsrc["RECOVERY"])
        edit_menu.AppendItem(self.mi_recovery)

        self.mi_update = wx.MenuItem(scenario_menu, ID_UPDATE, u"再読込(&R)\tF5",
                         u"最新の情報に更新します。")
        self.mi_update.SetBitmap(rsrc["UPDATE"])
        scenario_menu.AppendItem(self.mi_update)
        scenario_menu.AppendSeparator()
        self.mi_redisplay = wx.MenuItem(scenario_menu, ID_REDISPLAY, u"背景更新(&D)\tCtrl+R",
                         u"背景を更新します。")
        self.mi_redisplay.SetBitmap(rsrc["EVT_REDISPLAY"])
        scenario_menu.AppendItem(self.mi_redisplay)
        scenario_menu.AppendSeparator()
        self.mi_area = wx.MenuItem(scenario_menu, ID_AREA, u"エリア(&A)",
                         u"エリアを選択して場面を変更します。")
        self.mi_area.SetBitmap(rsrc["AREA"])
        scenario_menu.AppendItem(self.mi_area)
        self.mi_battle = wx.MenuItem(scenario_menu, ID_BATTLE, u"戦闘(&B)",
                         u"バトルを選択して戦闘を開始します。")
        self.mi_battle.SetBitmap(rsrc["BATTLE"])
        scenario_menu.AppendItem(self.mi_battle)
        self.mi_pack = wx.MenuItem(scenario_menu, ID_PACK, u"パッケージ(&P)",
                         u"パッケージを選択してイベントを開始します。")
        self.mi_pack.SetBitmap(rsrc["PACK"])
        scenario_menu.AppendItem(self.mi_pack)
        scenario_menu.AppendSeparator()
        self.mi_friend = wx.MenuItem(scenario_menu, ID_FRIEND, u"同行者(&F)",
                         u"同行者カードの取得・破棄を行います。")
        self.mi_friend.SetBitmap(rsrc["FRIEND"])
        scenario_menu.AppendItem(self.mi_friend)
        self.mi_info = wx.MenuItem(scenario_menu, ID_INFO, u"情報(&I)",
                         u"情報カードの取得・破棄を行います。")
        self.mi_info.SetBitmap(rsrc["INFO"])
        scenario_menu.AppendItem(self.mi_info)
        scenario_menu.AppendSeparator()
        self.mi_round = wx.MenuItem(scenario_menu, ID_ROUND, u"ラウンド(&T)",
                         u"バトルラウンドを変更します。")
        self.mi_round.SetBitmap(rsrc["ROUND"])
        scenario_menu.AppendItem(self.mi_round)

        self.mi_startevent = wx.MenuItem(run_menu, ID_STARTEVENT, u"イベントの実行(&E)",
                         u"イベントを選択して実行します。")
        self.mi_startevent.SetBitmap(rsrc["EVENT"])
        run_menu.AppendItem(self.mi_startevent)
        run_menu.AppendSeparator()
        self.mi_stepreturn = wx.MenuItem(run_menu, ID_STEPRETURN, u"ステップリターン(&R)\tCtrl+Shift+F11",
                         u"イベントのサブルーチンを抜けます。")
        self.mi_stepreturn.SetBitmap(rsrc["EVTCTRL_STEPRETURN"])
        run_menu.AppendItem(self.mi_stepreturn)
        self.mi_stepover = wx.MenuItem(run_menu, ID_STEPOVER, u"ステップオーバー(&I)\tF11",
                         u"イベントを1コンテントだけ実行します。サブルーチンには入りません。")
        self.mi_stepover.SetBitmap(rsrc["EVTCTRL_STEPOVER"])
        run_menu.AppendItem(self.mi_stepover)
        self.mi_stepin = wx.MenuItem(run_menu, ID_STEPIN, u"ステップイン(&R)\tCtrl+F11",
                         u"イベントを1コンテントだけ実行します。サブルーチンに入ります。")
        self.mi_stepin.SetBitmap(rsrc["EVTCTRL_STEPIN"])
        run_menu.AppendItem(self.mi_stepin)
        self.mi_pause = wx.MenuItem(run_menu, ID_PAUSE, u"イベント一時停止(&P)\tF10",
                         u"イベントを一時停止します。", kind=wx.ITEM_CHECK)
        bmp1 = rsrc["EVTCTRL_PLAY"]
        bmp2 = rsrc["EVTCTRL_PAUSE"]
        self.mi_pause.SetBitmaps(bmp1, bmp2)
        if sys.platform <> "win32":
            self.mi_pause.SetCheckable(False)
        run_menu.AppendItem(self.mi_pause)
        self.mi_stop = wx.MenuItem(run_menu, ID_STOP, u"イベント強制終了(&E)\tF12",
                         u"イベントを強制終了します。")
        self.mi_stop.SetBitmap(rsrc["EVTCTRL_STOP"])
        run_menu.AppendItem(self.mi_stop)
        run_menu.AppendSeparator()
        self.mi_select = wx.MenuItem(run_menu, ID_SELECTION, u"選択メンバ(&S)",
                         u"選択中のキャラクターを変更します。")
        self.mi_select.SetBitmap(rsrc["SELECTION"])
        run_menu.AppendItem(self.mi_select)
        run_menu.AppendSeparator()
        self.mi_showparty = wx.MenuItem(run_menu, ID_SHOW_PARTY, u"パーティ出現(&P)",
                         u"パーティを出現させます。")
        self.mi_showparty.SetBitmap(rsrc["EVT_SHOW_PARTY"])
        run_menu.AppendItem(self.mi_showparty)
        self.mi_hideparty = wx.MenuItem(run_menu, ID_HIDE_PARTY, u"パーティ隠蔽(&H)",
                         u"パーティを隠蔽します。")
        self.mi_hideparty.SetBitmap(rsrc["EVT_HIDE_PARTY"])
        run_menu.AppendItem(self.mi_hideparty)
        run_menu.AppendSeparator()
        self.mi_bgm = wx.MenuItem(run_menu, ID_BGM, u"&BGM変更",
                         u"BGMを変更します。")
        self.mi_bgm.SetBitmap(rsrc["EVT_PLAY_BGM"])
        run_menu.AppendItem(self.mi_bgm)

        self.SetMenuBar(mb)

        # create main toolbar
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
        self.tl_update = self.tb2.AddLabelTool(
            ID_UPDATE, u"再読込", rsrc["UPDATE"],
            shortHelp=u"最新の情報に更新します。")
        self.tb2.AddSeparator()
        self.tl_redisplay = self.tb2.AddLabelTool(
            ID_REDISPLAY, u"背景更新", rsrc["EVT_REDISPLAY"],
            shortHelp=u"背景を更新します。")
        self.tb2.AddSeparator()
        self.tl_friend = self.tb2.AddLabelTool(
            ID_FRIEND, u"同行者", rsrc["FRIEND"],
            shortHelp=u"同行者カードの取得・破棄を行います。")
        self.tl_info = self.tb2.AddLabelTool(
            ID_INFO, u"情報", rsrc["INFO"],
            shortHelp=u"情報カードの取得・破棄を行います。")
        self.tb2.AddSeparator()
        self.tl_round = self.tb2.AddLabelTool(
            ID_ROUND, u"ラウンド", rsrc["ROUND"],
            shortHelp=u"バトルラウンドを変更します。")
        self.tb2.AddSeparator()
        self.tb2.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_save = self.tb2.AddLabelTool(
            ID_SAVE, u"セーブ", rsrc["SAVE"],
            shortHelp=u"状況を記録します。")
        self.tl_load = self.tb2.AddLabelTool(
            ID_LOAD, u"ロード", rsrc["LOAD"],
            shortHelp=u"状況を再現します。")
        self.tb2.AddSeparator()
        self.tl_reset = self.tb2.AddLabelTool(
            ID_RESET, u"リセット", rsrc["RESET"],
            shortHelp=u"初期状態に戻します。")
        self.tb2.AddSeparator()
        self.tl_loadyado = self.tb2.AddLabelTool(
            ID_LOAD_YADO, u"最終セーブに戻す", rsrc["LOAD_YADO"],
            shortHelp=u"最後にセーブした状態に戻します。")
        self.tb2.AddSeparator()
        self.tl_break = self.tb2.AddLabelTool(
            ID_BREAK, u"シナリオ中断", rsrc["BREAK"],
            shortHelp=u"シナリオを中断して、冒険者の宿に戻ります。")
        self.tb2.Realize()

        # create event control bar
        self.tb_event = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_event.SetToolBitmapSize(wx.Size(20, 20))

        self.tl_startevent = self.tb_event.AddLabelTool(
            ID_STARTEVENT, u"イベントの実行", rsrc["EVENT"],
            shortHelp=u"イベントを選択して実行します。")
        self.tb_event.AddSeparator()
        self.tl_stepreturn = self.tb_event.AddLabelTool(
            ID_STEPRETURN, u"ステップリターン", rsrc["EVTCTRL_STEPRETURN"],
            shortHelp=u"イベントのサブルーチンを抜けます。")
        self.tl_stepover = self.tb_event.AddLabelTool(
            ID_STEPOVER, u"ステップオーバー", rsrc["EVTCTRL_STEPOVER"],
            shortHelp=u"イベントを1コンテントだけ実行します。サブルーチンには入りません。")
        self.tl_stepin = self.tb_event.AddLabelTool(
            ID_STEPIN, u"ステップイン", rsrc["EVTCTRL_STEPIN"],
            shortHelp=u"イベントを1コンテントだけ実行します。サブルーチンに入ります。")
        self.tb_event.AddSeparator()
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
        st = wx.StaticText(self.tb_event, -1, u"ウェイト")
        self.tb_event.AddControl(st)
        self.tb_event.AddControl(self.sc_waittime)
        st = wx.StaticText(self.tb_event, -1, u" (1=0.1秒)")
        self.tb_event.AddControl(st)
        self.tb_event.Realize()
        # create area toolbar
        self.tb_area = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_area.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_area = self.tb_area.AddLabelTool(
            ID_AREA, u"エリア", rsrc["AREA"],
            shortHelp=u"エリアを選択して場面を変更します。")

        # _battletoolでボタンの切り替えを判別
        self.tl_area._battletool = cw.cwpy.is_battlestatus()

        self.tb_area.AddSeparator()
        self.st_area = wx.StaticText(
            self.tb_area, -1, cw.cwpy.sdata.get_areaname(), size=(200, -1))
        self.tb_area.AddControl(self.st_area)

        self.tb_area.AddSeparator()
        self.tl_battle = self.tb_area.AddLabelTool(
            ID_BATTLE, u"戦闘", rsrc["BATTLE"],
            shortHelp=u"バトルを選択して戦闘を開始します。")
        self.tl_pack = self.tb_area.AddLabelTool(
            ID_PACK, u"パッケージ", rsrc["PACK"],
            shortHelp=u"パッケージを選択してイベントを開始します。")

        self.tb_area.Realize()

        # create selection toolbar
        self.tb_select = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_select.SetToolBitmapSize(wx.Size(20, 20))
        self.tl_select = self.tb_select.AddLabelTool(
            ID_SELECTION, u"選択メンバ",
            rsrc["SELECTION"], shortHelp=u"選択中のキャラクターを変更します。")
        self.tb_select.AddSeparator()
        self.st_select = wx.StaticText(
            self.tb_select, -1, cw.cwpy.event.get_selectedmembername(),
            size=(100, -1))
        self.tb_select.AddControl(self.st_select)
        self.tb_select.AddSeparator()
        self.tl_showparty = self.tb_select.AddLabelTool(
            ID_SHOW_PARTY, u"パーティ出現",
            rsrc["EVT_SHOW_PARTY"], shortHelp=u"パーティを出現させます。")
        self.tl_hideparty = self.tb_select.AddLabelTool(
            ID_HIDE_PARTY, u"パーティ隠蔽",
            rsrc["EVT_HIDE_PARTY"], shortHelp=u"パーティを隠蔽します。")
        self.tb_select.Realize()
        self.tb_select.AddSeparator()
        self.tl_bgm = self.tb_select.AddLabelTool(
            ID_BGM, u"BGM変更",
            rsrc["EVT_PLAY_BGM"], shortHelp=u"BGMを変更します。")
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
        self._refresh_tools()
        self._refresh_areaname()
        self._refresh_pausetool()
        # bind
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_MENU, self.OnAreaTool, id=ID_AREA)
        self.Bind(wx.EVT_MENU, self.OnSelectionTool, id=ID_SELECTION)
        self.Bind(wx.EVT_MENU, self.OnShowPartyTool, id=ID_SHOW_PARTY)
        self.Bind(wx.EVT_MENU, self.OnHidePartyTool, id=ID_HIDE_PARTY)
        self.Bind(wx.EVT_MENU, self.OnBgmTool, id=ID_BGM)
        self.Bind(wx.EVT_MENU, self.OnStepReturnTool, id=ID_STEPRETURN)
        self.Bind(wx.EVT_MENU, self.OnStepOverTool, id=ID_STEPOVER)
        self.Bind(wx.EVT_MENU, self.OnStepInTool, id=ID_STEPIN)
        self.Bind(wx.EVT_MENU, self.OnPauseTool, id=ID_PAUSE)
        self.Bind(wx.EVT_MENU, self.OnStopTool, id=ID_STOP)
        self.Bind(wx.EVT_MENU, self.OnRecoveryTool, id=ID_RECOVERY)
        self.Bind(wx.EVT_MENU, self.OnPackageTool, id=ID_PACK)
        self.Bind(wx.EVT_MENU, self.OnBattleTool, id=ID_BATTLE)
        self.Bind(wx.EVT_MENU, self.OnFriendTool, id=ID_FRIEND)
        self.Bind(wx.EVT_MENU, self.OnInfoTool, id=ID_INFO)
        self.Bind(wx.EVT_MENU, self.OnUpdateTool, id=ID_UPDATE)
        self.Bind(wx.EVT_MENU, self.OnRedisplayTool, id=ID_REDISPLAY)
        self.Bind(wx.EVT_MENU, self.OnBreakTool, id=ID_BREAK)
        self.Bind(wx.EVT_MENU, self.OnResetTool, id=ID_RESET)
        self.Bind(wx.EVT_MENU, self.OnSaveTool, id=ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnLoadTool, id=ID_LOAD)
        self.Bind(wx.EVT_MENU, self.OnLoadYadoTool, id=ID_LOAD_YADO)
        self.Bind(wx.EVT_MENU, self.OnCompStampTool, id=ID_COMPSTAMP)
        self.Bind(wx.EVT_MENU, self.OnGossipTool, id=ID_GOSSIP)
        self.Bind(wx.EVT_MENU, self.OnMoneyTool, id=ID_MONEY)
        self.Bind(wx.EVT_MENU, self.OnCardTool, id=ID_CARD)
        self.Bind(wx.EVT_MENU, self.OnRoundTool, id=ID_ROUND)
        self.Bind(wx.EVT_MENU, self.OnMemberTool, id=ID_MEMBER)
        self.Bind(wx.EVT_MENU, self.OnCouponTool, id=ID_COUPON)
        self.Bind(wx.EVT_MENU, self.OnStatusTool, id=ID_STATUS)
        self.Bind(wx.EVT_MENU, self.OnStartEventTool, id=ID_STARTEVENT)

        def clear_keyin(event):
            cw.cwpy.exec_func(cw.cwpy.keyevent.clear_keyin, event.GetKeyCode())
        def recurse(c):
            c.Bind(wx.EVT_KEY_UP, clear_keyin)
            for cc in c.GetChildren():
                recurse(cc)
        recurse(self)

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
            def func():
                cw.cwpy.sounds["click"].play()
                cw.cwpy.sdata.reload()
                if 0 <= cw.cwpy.areaid and not cw.cwpy.selectedheader:
                    # キャンプ等
                    cw.cwpy.change_area(cw.cwpy.areaid, False, True)

                if cw.cwpy.battle:
                    # バトル中
                    cw.cwpy.battle.ready()
                    cw.cwpy.battle.round -= 1
                cw.cwpy.sounds["signal"].play()
            cw.cwpy.exec_func(func)

    def OnRedisplayTool(self, event):
        def func():
            cw.cwpy.sounds["harvest"].play()
            cw.cwpy.background.reload()
        cw.cwpy.exec_func(func)

    def OnGossipTool(self, event):
        dlg = cw.debug.edit.GossipEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnMoneyTool(self, event):
        if not cw.cwpy.ydata.party:
            return
        dlg = cw.dialog.edit.NumberEditDialog(self, u"所持金の変更",
                                              cw.cwpy.ydata.party.money, 0, 999999)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            def func(value):
                cw.cwpy.ydata.party.set_money(value - cw.cwpy.ydata.party.money)
                cw.cwpy.draw()
            cw.cwpy.exec_func(func, dlg.value)

    def OnCardTool(self, event):
        dlg = cw.debug.cardedit.CardEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnRoundTool(self, event):
        if not cw.cwpy.is_battlestatus():
            return
        dlg = cw.dialog.edit.NumberEditDialog(self, u"バトルラウンドの変更",
                                              cw.cwpy.battle.round, 1, 1000)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            def func(value):
                cw.cwpy.battle.round = value
                cw.cwpy.statusbar.change()
                cw.cwpy.draw()
            cw.cwpy.exec_func(func, dlg.value)

    def OnSaveTool(self, event):
        if not cw.cwpy.is_playingscenario():
            return

        fpath = cw.binary.util.check_filename(cw.cwpy.sdata.name)
        fpath += ".wstx"
        dlg = wx.FileDialog(self, u"状態の保存", "", fpath,
                        u"CardWirthPyシナリオ状態ファイル (*.wstx)|*.wstx|すべてのファイル (*.*)|*.*",
                        wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            def func(path):
                cw.debug.recording.save(path)
            cw.cwpy.exec_func(func, path)

    def OnLoadTool(self, event):
        if not cw.cwpy.is_playingscenario():
            return

        cw.cwpy.exec_func(cw.cwpy.clean_specials)

        fpath = cw.binary.util.check_filename(cw.cwpy.sdata.name)
        fpath += ".wstx"
        dlg = wx.FileDialog(self, u"状態の復元", "", fpath,
                        u"CardWirthPyシナリオ状態ファイル (*.wstx)|*.wstx|すべてのファイル (*.*)|*.*",
                        wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            def func(path):
                cw.debug.recording.load(path)
                def func():
                    self.view_var.refresh_variablelist()
                cw.cwpy.frame.exec_func(func)
            cw.cwpy.exec_func(func, path)

    def OnLoadYadoTool(self, event):
        cw.cwpy.exec_func(cw.cwpy.clean_specials)
        cw.cwpy.exec_func(cw.cwpy.reload_yado)

    def OnCompStampTool(self, event):
        dlg = cw.debug.edit.CompStampEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnMemberTool(self, event):
        dlg = cw.debug.charaedit.CharacterEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnCouponTool(self, event):
        dlg = cw.debug.edit.CouponEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnStatusTool(self, event):
        dlg = cw.debug.statusedit.StatusEditDialog(self, cw.cwpy.get_pcards())
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def OnRecoveryTool(self, event):
        if cw.cwpy.is_playingscenario():
            def recovery_all():
                for pcard in cw.cwpy.get_pcards("unreversed"):
                    cw.cwpy.sounds["harvest"].play()
                    if pcard.status == "hidden":
                        pcard.set_fullrecovery()
                        pcard.update_image()
                        cw.cwpy.wait_frame(12)
                    else:
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
            oldids = infoids.copy()
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

                infoids = set([i.id for i in cw.cwpy.sdata.infocards])
                if infoids <> oldids:
                    cw.cwpy.exec_func(cw.cwpy.update_infocard)

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

                    def func(friendids):
                        fcards = [i for i in cw.cwpy.sdata.friendcards
                                                            if i.id in friendids]

                        for fcard in fcards:
                            cw.cwpy.sdata.friendcards.remove(fcard)

                        if cw.cwpy.areaid == cw.AREA_CAMP:
                            # キャンプ画面を開いている場合は表示更新
                            cw.cwpy.clear_fcardsprites()
                            cw.cwpy.add_fcardsprites(status="normal")
                        elif cw.cwpy.is_battlestatus():
                            # バトル中は同行キャストの表示更新
                            cw.cwpy.battle.update_showfcards()
                        cw.cwpy.draw()
                    cw.cwpy.exec_func(func, friendids)

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
                cw.cwpy.exec_func(cw.cwpy.clean_specials)
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
                cw.cwpy.exec_func(cw.cwpy.clean_specials)
                id = seq[dlg.GetSelection()][0]
                cw.cwpy.exec_func(cw.content.call_package, id, False)

            dlg.Destroy()

    def OnAreaTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            # 戦闘中は戦闘終了
            if cw.cwpy.battle:
                cw.cwpy.exec_func(cw.cwpy.clean_specials)
                func = cw.cwpy.battle.end
                cw.cwpy.exec_func(func)
            # 非戦闘中はエリア移動
            else:
                seq = [(key, str(key) + ": " + value[0]) for key, value in
                                cw.cwpy.sdata.areas.iteritems() if key > 0]
                seq.sort()
                choices = []
                if cw.cwpy.sdata and cw.cwpy.is_battlestatus():
                    areaid = cw.cwpy.sdata.pre_battleareadata[0]
                else:
                    areaid = cw.cwpy.areaid
                selected = -1
                for key, s in seq:
                    if key == areaid:
                        selected = len(choices)
                    choices.append(s)
                dlg = wx.SingleChoiceDialog(
                    self, u"移動するエリアを選択してください。",
                    u"エリアの選択", choices)
                dlg.SetSelection(selected)

                if dlg.ShowModal() == wx.ID_OK:
                    cw.cwpy.exec_func(cw.cwpy.clean_specials)
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

    def OnShowPartyTool(self, event):
        cw.cwpy.exec_func(cw.cwpy.show_party)

    def OnHidePartyTool(self, event):
        cw.cwpy.exec_func(cw.cwpy.hide_party)

    def OnBgmTool(self, event):
        choices = [u"[BGM停止]"]
        choices.extend(cw.cwpy.sdata.get_bgmpaths())
        dlg = wx.SingleChoiceDialog(
            self, u"再生するBGMを選択してください。",
            u"BGMの選択", choices)

        if dlg.ShowModal() == wx.ID_OK:
            func = cw.cwpy.music.play
            index = dlg.GetSelection()
            if 0 < index:
                path = choices[index]
            else:
                path = ""
            cw.cwpy.exec_func(func, path)

        dlg.Destroy()

    def OnStartEventTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent() and\
                (not cw.cwpy.is_battlestatus() or cw.cwpy.battle.is_ready()):
            if self._currentfpath and os.path.isfile(self._currentfpath):
                currentfpath = self._currentfpath
            elif cw.cwpy.sdata.data:
                currentfpath = cw.cwpy.sdata.data.fpath
            else:
                currentfpath = ""
            dlg = cw.debug.event.EventListDialog(self, currentfpath, self._showhiddencards)
            if dlg.ShowModal() == wx.ID_OK:
                self._currentfpath = dlg.events.get_currentfpath()
                self._showhiddencards = dlg.showhiddencards
                def func(start):
                    try:
                        start()
                    except cw.battle.BattleError, ex:
                        if cw.cwpy.is_battlestatus():
                            cw.cwpy.battle.process_exception(ex)
                cw.cwpy.exec_func(func, dlg.events.get_selectedevent().start)
            dlg.Destroy()

    def OnStepReturnTool(self, event):
        if cw.cwpy.event.get_currentstack() == 0:
            evt = wx.PyCommandEvent(wx.wxEVT_COMMAND_TOOL_CLICKED, ID_PAUSE)
            self.ProcessEvent(evt)
            return
        cw.cwpy.event._targetstack = cw.cwpy.event.get_currentstack() - 1
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.sounds["click"].play(True)
            mwin.result = 0

    def OnStepOverTool(self, event):
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = cw.cwpy.event.get_currentstack()
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.sounds["click"].play(True)
            mwin.result = 0

    def OnStepInTool(self, event):
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = -1
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.sounds["click"].play(True)
            mwin.result = 0

    def OnPauseTool(self, event):
        # メッセージウィンドウ表示中の場合は一時停止できない
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._paused = not cw.cwpy.event._paused
        cw.cwpy.event._step = False

        step = bool(cw.cwpy.event._paused and cw.cwpy.is_runningevent())
        self.mi_stepreturn.Enable(step)
        self.tl_stepreturn.Enable(step)
        self.mi_stepover.Enable(step)
        self.tl_stepover.Enable(step)
        self.mi_stepin.Enable(step)
        self.tl_stepin.Enable(step)

        self.mi_pause.Check(cw.cwpy.event._paused)
        # SetToggleが効かないため
        if self.tl_pause.IsToggled() <> cw.cwpy.event._paused:
            self.tl_pause.Toggle()

        self.refresh_pausetool()

    def refresh_pausetool(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_pausetool()

    def _refresh_pausetool(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.event._paused:
            bmp = cw.cwpy.rsrc.debugs["EVTCTRL_PLAY"]
            text = u"イベント実行再開(&P)\tF10"
            help = u"イベント実行を再開します。"
        else:
            bmp = cw.cwpy.rsrc.debugs["EVTCTRL_PAUSE"]
            text = u"イベント一時停止(&P)\tF10"
            help = u"イベントを一時停止します。"
        self.mi_pause.SetText(text)
        self.tl_pause.SetBitmap1(bmp)
        self.tl_pause.SetShortHelp(help)

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

        self.mi_stepreturn.Enable(False)
        self.tl_stepreturn.Enable(False)
        self.mi_stepover.Enable(False)
        self.tl_stepover.Enable(False)
        self.mi_stepin.Enable(False)
        self.tl_stepin.Enable(False)
        self.tb_event.Realize()

    def refresh_areaname(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_areaname()

    def _refresh_areaname(self):
        assert threading.currentThread() <> cw.cwpy
        self.st_area.SetLabel(cw.cwpy.sdata.get_areaname())

        # ツールボタンの表示を切り替えるかどうか
        if cw.cwpy.is_battlestatus() == self.tl_area._battletool:
            self.tb_area.Refresh()
        else:
            if cw.cwpy.is_battlestatus():
                bmp = cw.cwpy.rsrc.debugs["BATTLECANCEL"]
                self.mi_area.SetBitmap(bmp)
                self.mi_area.SetText(u"戦闘中断(&A)")
                self.tl_area.SetBitmap1(bmp)
                self.tl_area.SetShortHelp(u"戦闘を中断します。")
                self.tl_area._battletool = True
            else:
                bmp = cw.cwpy.rsrc.debugs["AREA"]
                self.mi_area.SetBitmap(bmp)
                self.mi_area.SetText(u"エリア(&A)")
                self.tl_area.SetBitmap1(bmp)
                self.tl_area.SetShortHelp(u"エリアを選択して場面を変更します。")
                self.tl_area._battletool = False

            self.mi_area.GetMenu().UpdateUI()
            self.tb_area.Realize()
            self._mgr.Update()

    def refresh_selectedmembername(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self.st_select.SetLabel(cw.cwpy.event.get_selectedmembername())
        self.tb_select.Refresh()

    def refresh_tools(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_tools()

    def _refresh_tools(self):
        assert threading.currentThread() <> cw.cwpy
        self.mi_comp.Enable(False)
        self.tl_comp.Enable(False)
        self.mi_gossip.Enable(False)
        self.tl_gossip.Enable(False)
        self.mi_money.Enable(False)
        self.tl_money.Enable(False)
        self.mi_card.Enable(False)
        self.tl_card.Enable(False)
        self.mi_member.Enable(False)
        self.tl_member.Enable(False)
        self.mi_coupon.Enable(False)
        self.tl_coupon.Enable(False)
        self.mi_status.Enable(False)
        self.tl_status.Enable(False)
        self.mi_recovery.Enable(False)
        self.tl_recovery.Enable(False)
        self.mi_break.Enable(False)
        self.tl_break.Enable(False)
        self.mi_update.Enable(False)
        self.tl_update.Enable(False)
        self.mi_redisplay.Enable(False)
        self.tl_redisplay.Enable(False)
        self.mi_battle.Enable(False)
        self.tl_battle.Enable(False)
        self.mi_pack.Enable(False)
        self.tl_pack.Enable(False)
        self.mi_friend.Enable(False)
        self.tl_friend.Enable(False)
        self.mi_info.Enable(False)
        self.tl_info.Enable(False)
        self.mi_round.Enable(False)
        self.tl_round.Enable(False)
        self.mi_save.Enable(False)
        self.tl_save.Enable(False)
        self.mi_load.Enable(False)
        self.tl_load.Enable(False)
        self.mi_loadyado.Enable(False)
        self.tl_loadyado.Enable(False)
        self.mi_reset.Enable(False)
        self.tl_reset.Enable(False)
        self.mi_stepreturn.Enable(False)
        self.tl_stepreturn.Enable(False)
        self.mi_stepover.Enable(False)
        self.tl_stepover.Enable(False)
        self.mi_stepin.Enable(False)
        self.tl_stepin.Enable(False)
        self.mi_pause.Enable(False)
        self.tl_pause.Enable(False)
        self.mi_stop.Enable(False)
        self.tl_stop.Enable(False)
        self.mi_select.Enable(False)
        self.tl_select.Enable(False)
        self.mi_showparty.Enable(False)
        self.tl_showparty.Enable(False)
        self.mi_hideparty.Enable(False)
        self.tl_hideparty.Enable(False)
        self.mi_area.Enable(False)
        self.tl_area.Enable(False)
        self.mi_startevent.Enable(False)
        self.tl_startevent.Enable(False)

        self.mi_bgm.Enable(True)
        self.tl_bgm.Enable(True)

        if cw.cwpy.ydata:
            self.mi_comp.Enable(True)
            self.tl_comp.Enable(True)
            self.mi_gossip.Enable(True)
            self.tl_gossip.Enable(True)
            self.mi_money.Enable(True)
            self.tl_money.Enable(True)
            self.mi_card.Enable(True)
            self.tl_card.Enable(True)
            self.mi_member.Enable(True)
            self.tl_member.Enable(True)
            self.mi_coupon.Enable(True)
            self.tl_coupon.Enable(True)
            self.mi_loadyado.Enable(True)
            self.tl_loadyado.Enable(True)

        if cw.cwpy.is_playingscenario():
            self.mi_pause.Enable(True)
            self.tl_pause.Enable(True)
            self.mi_status.Enable(True)
            self.tl_status.Enable(True)
            self.mi_recovery.Enable(True)
            self.tl_recovery.Enable(True)
            self.mi_redisplay.Enable(True)
            self.tl_redisplay.Enable(True)
            if cw.cwpy.is_runningevent():
                self.mi_select.Enable(True)
                self.tl_select.Enable(True)
                if cw.cwpy.is_showparty:
                    self.mi_hideparty.Enable(True)
                    self.tl_hideparty.Enable(True)
                else:
                    self.mi_showparty.Enable(True)
                    self.tl_showparty.Enable(True)
                self.mi_stop.Enable(True)
                self.tl_stop.Enable(True)
            else:
                if not cw.cwpy.is_battlestatus():
                    self.mi_break.Enable(True)
                    self.tl_break.Enable(True)
                    self.mi_save.Enable(True)
                    self.tl_save.Enable(True)
                    self.mi_load.Enable(True)
                    self.tl_load.Enable(True)
                else:
                    self.mi_round.Enable(True)
                    self.tl_round.Enable(True)

                if not cw.cwpy.battle or not cw.cwpy.battle.is_running():
                    self.mi_update.Enable(True)
                    self.tl_update.Enable(True)
                    self.mi_battle.Enable(True)
                    self.tl_battle.Enable(True)
                    self.mi_pack.Enable(True)
                    self.tl_pack.Enable(True)
                    self.mi_friend.Enable(True)
                    self.tl_friend.Enable(True)
                    self.mi_info.Enable(True)
                    self.tl_info.Enable(True)
                    self.mi_reset.Enable(True)
                    self.tl_reset.Enable(True)
                    self.mi_area.Enable(True)
                    self.tl_area.Enable(True)
                    self.mi_startevent.Enable(True)
                    self.tl_startevent.Enable(True)

        else:
            self.mi_pause.Enable(True)
            self.tl_pause.Enable(True)

        step = bool(cw.cwpy.event._paused and cw.cwpy.is_runningevent())
        self.mi_stepreturn.Enable(step)
        self.tl_stepreturn.Enable(step)
        self.mi_stepover.Enable(step)
        self.tl_stepover.Enable(step)
        self.mi_stepin.Enable(step)
        self.tl_stepin.Enable(step)

        self.tb1.Realize()
        self.tb2.Realize()
        self.tb_area.Realize()
        self.tb_select.Realize()
        self.tb_event.Realize()
        self._mgr.Update()

    def refresh_showpartytools(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_showpartytools()

    def _refresh_showpartytools(self):
        assert threading.currentThread() <> cw.cwpy
        self.mi_showparty.Enable(False)
        self.tl_showparty.Enable(False)
        self.mi_hideparty.Enable(False)
        self.tl_hideparty.Enable(False)

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.is_runningevent():
                if cw.cwpy.is_showparty:
                    self.mi_hideparty.Enable(True)
                    self.tl_hideparty.Enable(True)
                else:
                    self.mi_showparty.Enable(True)
                    self.tl_showparty.Enable(True)

        self.tb_select.Realize()
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
        self._refresh_variablelist()
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
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        try:
            itemid = self.list.index(variable)
            self.RefreshItem(itemid)
        except:
            self.refresh_variablelist()

    def refresh_variablelist(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_variablelist()

    def _refresh_variablelist(self):
        assert threading.currentThread() <> cw.cwpy
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
        self.SetDoubleBuffered(True)
        # 現在実行中のイベントツリーとイベント
        self.current_tree = None
        self.current_content = None
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
        self.processing = False
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

        if not item:
            return
        data = self.GetItemPyData(item)
        if data is None:
            return

        # スタートコンテントの場合は次のコンテントへ遷移
        if data.tag == "Start":
            item, cookie = self.GetFirstChild(item)
            if not item.IsOk():
                return
            data = self.GetItemPyData(item)
        if not data is None:
            cw.cwpy.exec_func(cw.cwpy.event.set_curcontent, data)

    def refresh_activeitem(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        processing = self.processing
        self.processing = True
        event = cw.cwpy.event.get_event()

        if event and event.cur_content in self.items:
            if self.current_content == event.cur_content:
                self.processing = processing
                return
            self.current_content = event.cur_content

            self.UnselectAll()
            if self.activeitem:
                content = self.GetItemPyData(self.activeitem)
                parent = self.GetItemParent(self.activeitem)
                parent = self.GetItemPyData(parent)
                if parent is None:
                    self.processing = processing
                    return
                s = self.get_contentname(parent, content)
                self.SetItemText(self.activeitem, s)
                self.SetItemTextColour(self.activeitem, wx.BLACK)

            self.activeitem = self.items[event.cur_content]
            self.SelectItem(self.activeitem)
            s = self.GetItemText(self.activeitem) + u" // ACTIVE!"
            self.SetItemText(self.activeitem, s)
            self.SetItemTextColour(self.activeitem, wx.RED)
        else:
            self.current_content = None
        self.processing = processing

    def refresh_tree(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        processing = self.processing
        self.processing = True

        nowrunning = cw.cwpy.event.get_nowrunningevent()
        if nowrunning is None:
            self.DeleteAllItems()
            self.items = {}
            self.activeitem = None
            self.current_tree = None
            self.current_content = None
            self.processing = processing
            return

        trees = nowrunning.trees
        if self.current_tree <> trees:
            trees = nowrunning.trees
            self.current_tree = trees
            self.Parent.statusbar.SetStatusText("", 1)
            self.activeitem = None
            self.items = {}
            self.DeleteAllItems()

            if self.current_tree:
                root = self.AddRoot("Event Root")
                self.SetPyData(root, None)

                for name in nowrunning.treekeys:
                    tree = trees[name]
                    self.set_content(root, tree, name)

            self.ExpandAll()
        self.processing = processing

    def set_content(self, parentitem, content, name):
        assert threading.currentThread() <> cw.cwpy
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
        assert threading.currentThread() <> cw.cwpy
        content = cw.content.get_content(parent)

        if content:
            return content.get_childname(child)
        else:
            return ""

def main():
    pass

if __name__ == "__main__":
    main()
