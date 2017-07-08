#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import itertools
import threading
import subprocess
import wx
import wx.aui
import wx.lib.mixins.listctrl

import cw
from cw.util import synclock

mutex = threading.Lock()


# ID
ID_COMPSTAMP = wx.NewId()
ID_GOSSIP = wx.NewId()
ID_SAVEDJPDCIMAGE = wx.NewId()
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
ID_EDITOR = wx.NewId()
ID_BREAKPOINT = wx.NewId()
ID_SHOW_STACK_TRACE = wx.NewId()
ID_CLEAR_BREAKPOINT = wx.NewId()
ID_QUIT_DEBUG_MODE = wx.NewId()
ID_INIT_VARIABLES = wx.NewId()


class Debugger(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self, parent, -1, u"CardWirthPy Debugger", size=wx.DefaultSize,
            style=wx.CLIP_CHILDREN|wx.CAPTION|wx.RESIZE_BOX|
            wx.RESIZE_BORDER|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU)
        self.cwpy_debug = True
        self.SetClientSize((cw.ppis(635), cw.cwpy.frame.GetClientSize()[1]))
        # set icon
        cw.cwpy.frame.set_icon(self)
        # aui manager
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        # create status bar
        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)
        self.statusbar.SetStatusWidths([-1])

        # 最後に強制実行したイベントが属するファイルパス
        self._currentfpath = ""
        # 最後にイベントを強制実行した時、隠蔽カードを表示していたか
        self._showhiddencards = False
        # 完全回復が予約されているがまだ実施されていない時はTrue
        self._recovering = False

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

        self.mi_editor = wx.MenuItem(file_menu, ID_EDITOR, u"エディタで開く(&O)\tCtrl+E",
                         u"シナリオをエディタで開きます。")
        self.mi_editor.SetBitmap(rsrc["EDITOR"])
        file_menu.AppendItem(self.mi_editor)
        file_menu.AppendSeparator()
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
        file_menu.AppendSeparator()
        self.mi_quit_debugmode = wx.MenuItem(file_menu, ID_QUIT_DEBUG_MODE, u"デバッグモードの終了(&Q)\tCtrl+D",
                         u"デバッガを閉じてデバッグモードを終了します。")
        self.mi_quit_debugmode.SetBitmap(rsrc["QUIT_DEBUG_MODE"])
        file_menu.AppendItem(self.mi_quit_debugmode)

        self.mi_comp = wx.MenuItem(edit_menu, ID_COMPSTAMP, u"終了印(&O)",
                         u"終了印リストを編集します。")
        self.mi_comp.SetBitmap(rsrc["COMPSTAMP"])
        edit_menu.AppendItem(self.mi_comp)
        self.mi_gossip = wx.MenuItem(edit_menu, ID_GOSSIP, u"ゴシップ(&G)",
                         u"ゴシップリストを編集します。")
        self.mi_gossip.SetBitmap(rsrc["GOSSIP"])
        edit_menu.AppendItem(self.mi_gossip)
        self.mi_savedjpdcimage = wx.MenuItem(edit_menu, ID_SAVEDJPDCIMAGE, u"保存済みJPDCイメージ(&G)",
                         u"保存されたJPDCイメージを整理します。")
        self.mi_savedjpdcimage.SetBitmap(rsrc["JPDCIMAGE"])
        edit_menu.AppendItem(self.mi_savedjpdcimage)
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

        self.mi_update = wx.MenuItem(scenario_menu, ID_UPDATE, u"再読込(&R)\tCtrl+F5",
                         u"最新の情報に更新します。")
        self.mi_update.SetBitmap(rsrc["UPDATE"])
        scenario_menu.AppendItem(self.mi_update)
        scenario_menu.AppendSeparator()
        self.mi_redisplay = wx.MenuItem(scenario_menu, ID_REDISPLAY, u"背景更新(&D)\tCtrl+I",
                         u"背景を更新します。")
        self.mi_redisplay.SetBitmap(rsrc["EVT_REDISPLAY"])
        scenario_menu.AppendItem(self.mi_redisplay)
        scenario_menu.AppendSeparator()
        self.mi_area = wx.MenuItem(scenario_menu, ID_AREA, u"エリア(&A)",
                         u"エリアを選択して場面を変更します。")
        self.mi_area.SetBitmap(rsrc["AREA"])
        self._mi_area_index = scenario_menu.GetMenuItemCount()
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
        scenario_menu.AppendSeparator()
        self.mi_initvars = wx.MenuItem(scenario_menu, ID_INIT_VARIABLES, u"状態変数の初期化(&V)")
        self.mi_initvars.SetBitmap(rsrc["INIT_VARIABLES"])
        scenario_menu.AppendItem(self.mi_initvars)

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
        run_menu.AppendSeparator()
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
        self.mi_breakpoint = wx.MenuItem(run_menu, ID_BREAKPOINT, u"ブレークポイントの切替(&W)\tCtrl+B",
                         u"ブレークポイントを設定、または解除します。")
        self.mi_breakpoint.SetBitmap(rsrc["BREAKPOINT"])
        run_menu.AppendItem(self.mi_breakpoint)
        self.mi_clear_breakpoint = wx.MenuItem(run_menu, ID_CLEAR_BREAKPOINT, u"ブレークポイントの整理(&C)",
                         u"シナリオごとのブレークポイントをクリアします。")
        self.mi_clear_breakpoint.SetBitmap(rsrc["CLEAR_BREAKPOINT"])
        run_menu.AppendItem(self.mi_clear_breakpoint)
        run_menu.AppendSeparator()
        self.mi_showstacktrace = wx.MenuItem(run_menu, ID_SHOW_STACK_TRACE, u"呼び出し履歴の表示(&S)\tCtrl+T",
                         u"呼び出し履歴を表示します。", kind=wx.ITEM_CHECK)
        bmp = rsrc["STACK_TRACE"]
        self.mi_showstacktrace.SetBitmaps(bmp, bmp)
        run_menu.AppendItem(self.mi_showstacktrace)
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
        self.tb1.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
        self.tl_comp = self.tb1.AddLabelTool(
            ID_COMPSTAMP, u"終了印", rsrc["COMPSTAMP"],
            shortHelp=u"終了印リストを編集します。")
        self.tl_gossip = self.tb1.AddLabelTool(
            ID_GOSSIP, u"ゴシップ", rsrc["GOSSIP"],
            shortHelp=u"ゴシップリストを編集します。")
        self.tl_savedjpdcimage = self.tb1.AddLabelTool(
            ID_SAVEDJPDCIMAGE, u"保存済みJPDCイメージ", rsrc["JPDCIMAGE"],
            shortHelp=u"保存されたJPDCイメージを整理します。")
        self.tl_money = self.tb1.AddLabelTool(
            ID_MONEY, u"所持金", rsrc["MONEY"],
            shortHelp=u"所持金を変更します。")
        self.tl_card = self.tb1.AddLabelTool(
            ID_CARD, u"手札配布", rsrc["CARD"],
            shortHelp=u"手札カードを配布します。")
        self.tb1.AddSeparator()
        self.tb1.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
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
        self.tb2.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
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
        self.tb2.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
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
        self.tb2.AddSeparator()
        self.tl_editor = self.tb2.AddLabelTool(
            ID_EDITOR, u"エディタで開く", rsrc["EDITOR"],
            shortHelp=u"シナリオをエディタで開きます。")
        self.tb2.Realize()

        # create event control bar
        self.tb_event = wx.ToolBar(self, -1, style=wx.TB_FLAT|wx.TB_NODIVIDER)
        self.tb_event.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))

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
        self.tl_breakpoint = self.tb_event.AddLabelTool(
            ID_BREAKPOINT, u"ブレークポイントの切替", rsrc["BREAKPOINT"],
            shortHelp=u"ブレークポイントを設定、または解除します。")
        self.tl_clear_breakpoint = self.tb_event.AddLabelTool(
            ID_CLEAR_BREAKPOINT, u"ブレークポイントの整理", rsrc["CLEAR_BREAKPOINT"],
            shortHelp=u"シナリオごとのブレークポイントをクリアします。")
        self.tb_event.AddSeparator()
        self.tl_showstacktrace = self.tb_event.AddCheckLabelTool(
            ID_SHOW_STACK_TRACE, u"呼び出し履歴の表示", rsrc["STACK_TRACE"],
            shortHelp=u"呼び出し履歴を表示します。")
        self.tb_event.AddSeparator()
        self.sc_waittime = wx.SpinCtrl(
            self.tb_event, -1, u"イベント待機時間", size=(cw.ppis(40), cw.ppis(20)))
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
        self.tb_area.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
        self.tl_area = self.tb_area.AddLabelTool(
            ID_AREA, u"エリア", rsrc["AREA"],
            shortHelp=u"エリアを選択して場面を変更します。")

        # _battletoolでボタンの切り替えを判別
        self.tl_area._battletool = False

        self.tb_area.AddSeparator()
        self.st_area = wx.StaticText(
            self.tb_area, -1, cw.cwpy.sdata.get_currentareaname(), size=(cw.ppis(200), -1))
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
        self.tb_select.SetToolBitmapSize(wx.Size(cw.ppis(20), cw.ppis(20)))
        self.tl_select = self.tb_select.AddLabelTool(
            ID_SELECTION, u"選択メンバ",
            rsrc["SELECTION"], shortHelp=u"選択中のキャラクターを変更します。")
        self.tb_select.AddSeparator()
        self.st_select = wx.StaticText(
            self.tb_select, -1, cw.cwpy.event.get_selectedmembername(),
            size=(cw.ppis(100), -1))
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
        self.view_tree = EventView(self)

        self.view_stacktrace = None

        # add pane
        self._mgr.AddPane(
            self.view_var,
            wx.aui.AuiPaneInfo().Name("list_var").MinSize((cw.ppis(200), -1)).
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
        self._refresh_areaname(force=True)
        self._refresh_pausetool()
        # bind
        self._bind()

    def refresh_all(self):
        self.view_tree.refresh_tree()
        self.view_tree.refresh_activeitem()
        self._refresh_tools()
        self._refresh_areaname(force=True)
        self._refresh_pausetool()

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
        self.Bind(wx.EVT_MENU, self.OnShowStackTraceTool, id=ID_SHOW_STACK_TRACE)
        self.Bind(wx.EVT_MENU, self.OnBreakpointTool, id=ID_BREAKPOINT)
        self.Bind(wx.EVT_MENU, self.OnClearBreakpointTool, id=ID_CLEAR_BREAKPOINT)
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
        self.Bind(wx.EVT_MENU, self.OnSavedJPDCImageTool, id=ID_SAVEDJPDCIMAGE)
        self.Bind(wx.EVT_MENU, self.OnMoneyTool, id=ID_MONEY)
        self.Bind(wx.EVT_MENU, self.OnCardTool, id=ID_CARD)
        self.Bind(wx.EVT_MENU, self.OnRoundTool, id=ID_ROUND)
        self.Bind(wx.EVT_MENU, self.OnMemberTool, id=ID_MEMBER)
        self.Bind(wx.EVT_MENU, self.OnCouponTool, id=ID_COUPON)
        self.Bind(wx.EVT_MENU, self.OnStatusTool, id=ID_STATUS)
        self.Bind(wx.EVT_MENU, self.OnStartEventTool, id=ID_STARTEVENT)
        self.Bind(wx.EVT_MENU, self.OnEditorTool, id=ID_EDITOR)
        self.Bind(wx.EVT_MENU, self.OnQuitDebugMode, id=ID_QUIT_DEBUG_MODE)
        self.Bind(wx.EVT_MENU, self.OnInitVariables, id=ID_INIT_VARIABLES)

        # F1～F9キーをメイン画面へ転送
        self.f1keyid = wx.NewId()
        self.f2keyid = wx.NewId()
        self.f3keyid = wx.NewId()
        self.f4keyid = wx.NewId()
        self.f5keyid = wx.NewId()
        self.f6keyid = wx.NewId()
        self.f7keyid = wx.NewId()
        self.f8keyid = wx.NewId()
        self.f9keyid = wx.NewId()
        self.ctrl_d_keyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnF1KeyDown, id=self.f1keyid)
        self.Bind(wx.EVT_MENU, self.OnF2KeyDown, id=self.f2keyid)
        self.Bind(wx.EVT_MENU, self.OnF3KeyDown, id=self.f3keyid)
        self.Bind(wx.EVT_MENU, self.OnF4KeyDown, id=self.f4keyid)
        self.Bind(wx.EVT_MENU, self.OnF5KeyDown, id=self.f5keyid)
        self.Bind(wx.EVT_MENU, self.OnF6KeyDown, id=self.f6keyid)
        self.Bind(wx.EVT_MENU, self.OnF7KeyDown, id=self.f7keyid)
        self.Bind(wx.EVT_MENU, self.OnF8KeyDown, id=self.f8keyid)
        self.Bind(wx.EVT_MENU, self.OnF9KeyDown, id=self.f9keyid)
        self.Bind(wx.EVT_MENU, self.OnQuitDebugMode, id=self.ctrl_d_keyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_F1, self.f1keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F2, self.f2keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F3, self.f3keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F4, self.f4keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F5, self.f5keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F6, self.f6keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F7, self.f7keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F8, self.f8keyid),
            (wx.ACCEL_NORMAL, wx.WXK_F9, self.f9keyid),
            (wx.ACCEL_CTRL, ord('D'), self.ctrl_d_keyid),
        ]
        cw.util.set_acceleratortable(self, seq)

    def OnF1KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F1)
        cw.cwpy.keyevent.keyup(wx.WXK_F1)
    def OnF2KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F2)
        cw.cwpy.keyevent.keyup(wx.WXK_F2)
    def OnF3KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F3)
        cw.cwpy.keyevent.keyup(wx.WXK_F3)
    def OnF4KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F4)
        cw.cwpy.keyevent.keyup(wx.WXK_F4)
    def OnF5KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F5)
        cw.cwpy.keyevent.keyup(wx.WXK_F5)
    def OnF6KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F6)
        cw.cwpy.keyevent.keyup(wx.WXK_F6)
    def OnF7KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F7)
        cw.cwpy.keyevent.keyup(wx.WXK_F7)
    def OnF8KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F8)
        cw.cwpy.keyevent.keyup(wx.WXK_F8)
    def OnF9KeyDown(self, event):
        cw.cwpy.keyevent.keydown(wx.WXK_F9)
        cw.cwpy.keyevent.keyup(wx.WXK_F9)

    @synclock(mutex)
    def OnClose(self, event):
        cw.cwpy.exec_func(cw.cwpy.statusbar.change, cw.cwpy.statusbar.showbuttons)
        self.Destroy()
        cw.cwpy.frame.debugger = None

    @synclock(mutex)
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
            cw.cwpy.is_debuggerprocessing = True
            self.refresh_tools()
            def func():
                cw.cwpy.play_sound("click")
                try:
                    cw.cwpy.sdata.reload()
                    if 0 <= cw.cwpy.areaid and not cw.cwpy.selectedheader:
                        # キャンプ等
                        cw.cwpy.change_area(cw.cwpy.areaid, False, True)

                    if cw.cwpy.battle:
                        # バトル中
                        cw.cwpy.battle.ready()
                        cw.cwpy.battle.round -= 1
                    cw.cwpy.play_sound("signal")
                except cw.event.EffectBreakError:
                    pass
            cw.cwpy.exec_func(func)

    def OnRedisplayTool(self, event):
        def func():
            cw.cwpy.play_sound("harvest")
            cw.cwpy.background.reload()
        cw.cwpy.exec_func(func)

    def OnGossipTool(self, event):
        dlg = cw.debug.edit.GossipEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        cw.cwpy.exec_func(cw.cwpy.update_yadoinitial)

    def OnSavedJPDCImageTool(self, event):
        def func(self):
            if not cw.cwpy.ydata:
                return
            savedjpdcimage = cw.cwpy.ydata.savedjpdcimage.copy()
            def func(self):
                if not self:
                    return
                dlg = cw.debug.edit.SavedJPDCImageEditDialog(self, savedjpdcimage)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def OnMoneyTool(self, event):
        if not cw.cwpy.ydata.party:
            return
        dlg = cw.dialog.edit.NumberEditDialog(self, u"所持金の変更",
                                              cw.cwpy.ydata.party.money, 0, 9999999)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            def func(value):
                cw.cwpy.ydata.party.set_money(value - cw.cwpy.ydata.party.money, blink=True)
                cw.cwpy.draw()
            cw.cwpy.exec_func(func, dlg.value)

    def OnCardTool(self, event):
        dlg = cw.debug.cardedit.CardEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        cw.cwpy.exec_func(cw.cwpy.update_yadoinitial)

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

    def OnEditorTool(self, event):
        if not cw.cwpy.setting.editor:
            return
        def func(self, content):
            if not cw.cwpy.is_playingscenario():
                return
            fpath = cw.cwpy.sdata.fpath
            if not fpath:
                return
            if os.path.isdir(fpath):
                # WirthBuilderはSummary.wsmのパスを渡さないとシナリオを開けない
                wsm = cw.util.join_paths(fpath, "Summary.wsm")
                if os.path.isfile(wsm):
                    fpath = wsm
            # WirthBuilderは'/'区切りのパスを受け付けない
            fpath = os.path.normpath(fpath)

            editor = cw.cwpy.setting.editor
            if not editor:
                return

            # エディタ起動
            encoding = sys.getfilesystemencoding()
            editor = editor.encode(encoding)
            fpath = fpath.encode(encoding)
            seq = [editor, fpath]
            cwxpath = ""
            packid = 0

            if not content is None:
                cwxpath = content.get_cwxpath()
                if not cwxpath and cw.cwpy.is_runningevent():
                    packid = cw.cwpy.event.get_packageid()
            elif cw.cwpy.is_runningevent():
                event = cw.cwpy.event.get_event()
                if event and not event.cur_content is None:
                    cur_content = event.cur_content
                    if cur_content.tag == "ContentsLine":
                        cur_content = cur_content[event.line_index]
                    cwxpath = cur_content.get_cwxpath()

                if not cwxpath:
                    # パッケージ処理中でなければ0が返る
                    packid = cw.cwpy.event.get_packageid()

            if cwxpath:
                seq.append(cwxpath.encode(encoding))
            elif packid:
                # 古いバージョンのCWXEditorでは
                # -a -b -pオプションつきの起動で
                # 同一のシナリオが複数開かれてしまう
                seq.append(("package:id:%s" % (packid)).encode(encoding))
            elif cw.cwpy.is_battlestatus():
                seq.append(("battle:id:%s" % (cw.cwpy.areaid)).encode(encoding))
            elif 0 <= cw.cwpy.areaid:
                seq.append(("area:id:%s" % (cw.cwpy.areaid)).encode(encoding))
            elif cw.cwpy.pre_areaids:
                seq.append(("area:id:%s" % (cw.cwpy.pre_areaids[0][0])).encode(encoding))

            def func(self, seq):
                if not self:
                    return

                try:
                    subprocess.Popen(seq, close_fds=True)
                except:
                    s = u"「%s」の実行に失敗しました。設定の [シナリオ] > [外部アプリ] > [エディタ] に適切なエディタを指定してください。" % (os.path.basename(cw.cwpy.setting.editor))
                    dlg = cw.dialog.message.ErrorMessage(self, s)
                    cw.cwpy.frame.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()

            cw.cwpy.frame.exec_func(func, self, seq)

        if not self.view_tree.selectionitem is None:
            content = self.view_tree.selectionitem.content
        elif not self.view_tree.activeitem is None:
            content = self.view_tree.activeitem.content
        else:
            content = None

        cw.cwpy.exec_func(func, self, content)

    def OnShowStackTraceTool(self, event):
        if self.view_stacktrace:
            self._mgr.ClosePane(self._mgr.GetPane(self.view_stacktrace))
            self._mgr.Update()
            return
        # create stack trace view
        self.view_stacktrace = StackTraceView(self)
        self._mgr.AddPane(
            self.view_stacktrace,
            wx.aui.AuiPaneInfo().Name("view_stacktrace").MinSize((-1, cw.ppis(10))).
            Bottom().CloseButton(True).MaximizeButton(True).
            Caption(u"呼び出し履歴").DestroyOnClose())
        self.view_stacktrace.refresh_stackinfo()
        self._mgr.Update()

        def OnDestroy(event):
            self.view_stacktrace = None
            if cw.cwpy.frame.debugger:
                self.mi_showstacktrace.Check(False)
                if self.tl_showstacktrace.IsToggled():
                    self.tl_showstacktrace.Toggle()
                    self.tb_event.Realize()
        self.view_stacktrace.Bind(wx.EVT_WINDOW_DESTROY, OnDestroy)

        self.mi_showstacktrace.Check(True)
        if not self.tl_showstacktrace.IsToggled():
            self.tl_showstacktrace.Toggle()
            self.tb_event.Realize()

    def append_stackinfo_cwpy(self, item):
        assert threading.currentThread() is cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        if self.view_stacktrace:
            self.view_stacktrace.append_stackinfo_cwpy(item)

    def pop_stackinfo_cwpy(self):
        assert threading.currentThread() is cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        if self.view_stacktrace:
            self.view_stacktrace.pop_stackinfo_cwpy()

    def replace_stackinfo_cwpy(self, index, item):
        assert threading.currentThread() is cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        if self.view_stacktrace:
            self.view_stacktrace.replace_stackinfo_cwpy(index, item)

    def clear_stackinfo_cwpy(self):
        assert threading.currentThread() is cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        if self.view_stacktrace:
            self.view_stacktrace.clear_stackinfo_cwpy()

    def refresh_stackinfo(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        if self.view_stacktrace:
            self.view_stacktrace.refresh_stackinfo()

    def OnQuitDebugMode(self, event):
        def func():
            cw.cwpy.play_sound("page")
            cw.cwpy.set_debug(False)
            cw.cwpy.draw()
        cw.cwpy.exec_func(func)

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

        fpath = cw.binary.util.check_filename(cw.cwpy.sdata.name)
        fpath += ".wstx"
        dlg = wx.FileDialog(self, u"状態の復元", "", fpath,
                        u"CardWirthPyシナリオ状態ファイル (*.wstx)|*.wstx|すべてのファイル (*.*)|*.*",
                        wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            def func(path):
                cw.cwpy.clean_specials()
                cw.debug.recording.load(path)
                def func():
                    self.view_var.refresh_variablelist()
                cw.cwpy.frame.exec_func(func)
            cw.cwpy.exec_func(func, path)

    def OnLoadYadoTool(self, event):
        cw.cwpy.is_debuggerprocessing = True
        self.refresh_tools()
        def func():
            cw.cwpy.clean_specials()
            cw.cwpy.exec_func(cw.cwpy.reload_yado)
        cw.cwpy.exec_func(func)

    def OnCompStampTool(self, event):
        dlg = cw.debug.edit.CompStampEditDialog(self)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        cw.cwpy.exec_func(cw.cwpy.update_yadoinitial)

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
        if cw.cwpy.is_playingscenario() and not self._recovering:
            self._recovering = True
            def recovery_all(self):
                pcards = cw.cwpy.get_pcards("unreversed")
                for pcard in pcards:
                    cw.cwpy.play_sound("harvest")
                    battlespeed = cw.cwpy.is_battlestatus()
                    if pcard.status == "hidden":
                        pcard.set_fullrecovery(decideaction=False)
                        pcard.update_image()
                        waitrate = (cw.cwpy.setting.get_dealspeed(battlespeed)+1) * 2
                        cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                    else:
                        cw.animation.animate_sprite(pcard, "hide", battlespeed=battlespeed)
                        pcard.set_fullrecovery(decideaction=False)
                        pcard.update_image()
                        cw.animation.animate_sprite(pcard, "deal", battlespeed=battlespeed)
                if cw.cwpy.is_battlestatus() and cw.cwpy.battle.is_ready():
                    for pcard in pcards:
                        if pcard.is_active():
                            pcard.deck.set(pcard)
                            pcard.decide_action()

                def func(self):
                    if self:
                        self._recovering = False
                cw.cwpy.frame.exec_func(func, self)

            cw.cwpy.exec_func(recovery_all, self)

    def OnInfoTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = []
            ids = cw.cwpy.sdata.get_infoids()
            cw.util.sort_by_attr(ids)
            for resid in ids:
                name = cw.cwpy.sdata.get_infoname(resid)
                fpath = cw.cwpy.sdata.get_infofpath(resid)
                if not name is None:
                    seq.append((resid, u"%s: %s" % (resid, name), fpath))
            infoids = set(cw.cwpy.sdata.get_infocards(order=False))
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
                hasids = set()
                for index in dlg.GetSelections():
                    resid = seq[index][0]
                    fpath = cw.cwpy.sdata.get_infofpath(resid)
                    if fpath is None:
                        s = u"%s の読込に失敗しました。" % (os.path.basename(seq[index][2]))
                        cw.cwpy.call_modaldlg("ERROR", text=s)
                        continue

                    hasids.add(resid)

                    if not resid in infoids:
                        cw.cwpy.sdata.append_infocard(resid)

                for resid in infoids:
                    if not resid in hasids:
                        cw.cwpy.sdata.remove_infocard(resid)

                infoids = set(cw.cwpy.sdata.get_infocards(order=False))
                if infoids <> oldids:
                    cw.cwpy.exec_func(cw.cwpy.update_infocard)

            dlg.Destroy()

    def OnFriendTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = []
            ids = cw.cwpy.sdata.get_castids()
            cw.util.sort_by_attr(ids)
            for resid in ids:
                name = cw.cwpy.sdata.get_castname(resid)
                if not name is None:
                    seq.append((resid, u"%s: %s" % (resid, name)))

            cw.util.sort_by_attr(seq)
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
                    def func(friendids, seq, indices):
                        for index in indices:
                            key = seq[index][0]

                            if key in friendids:
                                friendids.remove(key)
                            else:
                                e = cw.cwpy.sdata.get_castdata(key, nocache=True)
                                if not e is None:
                                    fcard = cw.sprite.card.FriendCard(data=e)
                                    cw.cwpy.sdata.friendcards.append(fcard)
                                    if cw.cwpy.is_battlestatus() and cw.cwpy.battle.is_ready() and fcard.is_active():
                                        fcard.deck.set(fcard)
                                        fcard.decide_action()

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
                            cw.cwpy.statusbar.change()
                        cw.cwpy.draw()
                    cw.cwpy.exec_func(func, friendids, seq, dlg.GetSelections())

            dlg.Destroy()

    def OnBattleTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = []
            ids = cw.cwpy.sdata.get_battleids()
            cw.util.sort_by_attr(ids)
            for resid in ids:
                name = cw.cwpy.sdata.get_battlename(resid)
                if not name is None:
                    seq.append((resid, u"%s: %s" % (resid, name)))

            choices = [s for key, s in seq]
            dlg = wx.SingleChoiceDialog(
                self, u"開始するバトルを選択してください。",
                u"バトルの選択", choices)

            if dlg.ShowModal() == wx.ID_OK:
                cw.cwpy.exec_func(cw.cwpy.clean_specials)
                def func(resid):
                    try:
                        cw.cwpy.change_battlearea(resid)
                    except cw.event.EffectBreakError, ex:
                        cw.util.print_ex()
                cw.cwpy.exec_func(func, seq[dlg.GetSelection()][0])

            dlg.Destroy()

    def OnPackageTool(self, event):
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_runningevent():
            seq = []
            ids = cw.cwpy.sdata.get_packageids()
            cw.util.sort_by_attr(ids)
            for resid in ids:
                name = cw.cwpy.sdata.get_packagename(resid)
                if not name is None:
                    seq.append((resid, u"%s: %s" % (resid, name)))

            choices = [s for key, s in seq]
            dlg = wx.SingleChoiceDialog(
                self, u"実行するパッケージを選択してください。",
                u"パッケージの選択", choices)

            if dlg.ShowModal() == wx.ID_OK:
                cw.cwpy.exec_func(cw.cwpy.clean_specials)
                resid = seq[dlg.GetSelection()][0]

                def func(resid):
                    try:
                        cw.content.call_package(resid, False)
                    except cw.battle.BattleError, ex:
                        if cw.cwpy.is_battlestatus():
                            cw.cwpy.battle.process_exception(ex)
                    except cw.event.EffectBreakError, ex:
                        cw.util.print_ex()
                cw.cwpy.exec_func(func, resid)

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
                seq = []
                ids = cw.cwpy.sdata.get_areaids()
                cw.util.sort_by_attr(ids)
                for resid in ids:
                    if resid < 0:
                        continue
                    name = cw.cwpy.sdata.get_areaname(resid)
                    if not name is None:
                        seq.append((resid, u"%s: %s" % (resid, name)))

                choices = []
                if cw.cwpy.sdata and cw.cwpy.is_battlestatus():
                    areaid = cw.cwpy.sdata.pre_battleareadata[0]
                elif cw.cwpy.areaid == cw.AREA_CAMP:
                    areaid = cw.cwpy.pre_areaids[-1][0]
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
                    def func(resid):
                        try:
                            cw.cwpy.change_area(resid)
                        except cw.event.EffectBreakError, ex:
                            cw.util.print_ex()
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
            index = dlg.GetSelection()
            if 0 < index:
                path = choices[index]
            else:
                path = ""
            def func(path):
                if not cw.cwpy.is_playingscenario():
                    path = cw.util.get_materialpathfromskin(path, cw.M_MSC)
                for music in cw.cwpy.music:
                    music.stop()
                cw.cwpy.music[0].play(path)
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
                if not self._currentfpath:
                    self._currentfpath = ""
                self._showhiddencards = dlg.showhiddencards
                def func(start):
                    try:
                        start()
                    except cw.battle.BattleError, ex:
                        if cw.cwpy.is_battlestatus():
                            cw.cwpy.battle.process_exception(ex)
                if dlg.start_event:
                    cw.cwpy.exec_func(func, dlg.events.get_selectedevent().start)
                else:
                    self.view_tree.set_event(dlg.events.get_selectedevent())
            dlg.Destroy()

    def OnStepReturnTool(self, event):
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = cw.cwpy.event.get_currentstack() - 1
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.play_sound("click", True)
            mwin.result = 0

    def OnStepOverTool(self, event):
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = cw.cwpy.event.get_currentstack()
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.play_sound("click", True)
            mwin.result = 0

    def OnStepInTool(self, event):
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = -2
        cw.cwpy.event._step = True
        cw.cwpy.event._paused = False
        mwin = cw.cwpy.get_messagewindow()
        if mwin:
            # メッセージウィンドウ表示中の場合で処理を分ける
            cw.cwpy.play_sound("click", True)
            mwin.result = 0

    def OnPauseTool(self, event):
        self.pause(not cw.cwpy.event._paused)

    def pause(self, paused):
        assert threading.currentThread() <> cw.cwpy
        # メッセージウィンドウ表示中の場合は一時停止できない
        cw.cwpy.event.breakwait = True
        cw.cwpy.event._targetstack = -2
        cw.cwpy.event._paused = paused
        cw.cwpy.event._step = False

        step = bool(cw.cwpy.event._paused and cw.cwpy.is_runningevent())

        enabled = {}.copy()
        enabled[self.mi_stepreturn.GetId()] = (self.mi_stepreturn, self.tl_stepreturn, step)
        enabled[self.mi_stepover.GetId()] = (self.mi_stepover, self.tl_stepover, step)
        enabled[self.mi_stepin.GetId()] = (self.mi_stepin, self.tl_stepin, step)
        for mi, tl, enable in enabled.itervalues():
            if tl.IsEnabled() <> enable:
                mi.Enable(enable)
                tl.Enable(enable)

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
        if cw.cwpy.event.is_paused():
            bmp = cw.cwpy.rsrc.debugs["EVTCTRL_PLAY"]
            text = u"イベント実行再開(&P)\tF10"
            helptext = u"イベント実行を再開します。"
        else:
            bmp = cw.cwpy.rsrc.debugs["EVTCTRL_PAUSE"]
            text = u"イベント一時停止(&P)\tF10"
            helptext = u"イベントを一時停止します。"
        self.mi_pause.SetText(text)
        self.tl_pause.SetBitmap1(bmp)
        self.tl_pause.SetShortHelp(helptext)

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

        enabled = {}.copy()
        enabled[self.mi_stepreturn.GetId()] = (self.mi_stepreturn, self.tl_stepreturn, False)
        enabled[self.mi_stepover.GetId()] = (self.mi_stepover, self.tl_stepover, False)
        enabled[self.mi_stepin.GetId()] = (self.mi_stepin, self.tl_stepin, False)
        update = False
        for mi, tl, enable in enabled.itervalues():
            if tl.IsEnabled() <> enable:
                mi.Enable(enable)
                tl.Enable(enable)
                update = True

        if update:
            self.tb_event.Realize()

        def func(self):
            def func(self):
                if self:
                    self._refresh_areaname()
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def OnBreakpointTool(self, event):
        self.view_tree.switch_breakpoint()

    def refresh_breakpointtool(self):
        enable = bool(self.view_tree.selectionitem)
        if cw.cwpy.frame.debugger.mi_breakpoint.IsEnabled() <> enable:
            cw.cwpy.frame.debugger.mi_breakpoint.Enable(enable)
            cw.cwpy.frame.debugger.tl_breakpoint.Enable(enable)
            cw.cwpy.frame.debugger.tb_event.Realize()

    def OnClearBreakpointTool(self, event):
        def func(self):
            if not cw.cwpy.sdata:
                return
            cw.cwpy.sdata.save_breakpoints()
            breakpoint_table = cw.cwpy.breakpoint_table.copy()
            def func(self):
                if not self:
                    return
                dlg = cw.debug.edit.BreakpointEditDialog(self, breakpoint_table)
                cw.cwpy.frame.move_dlg(dlg)
                if dlg.ShowModal() == wx.ID_OK:
                    def func(self):
                        if cw.cwpy.is_playingscenario():
                            key = (cw.cwpy.sdata.name, cw.cwpy.sdata.author)
                            cw.cwpy.sdata.breakpoints = cw.cwpy.breakpoint_table.get(key, set())
                            def func(self):
                                if self:
                                    self.view_tree.Refresh()
                                    self.refresh_clearbreakpointtool()
                            cw.cwpy.frame.exec_func(func, self)
                    cw.cwpy.exec_func(func, self)

            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def refresh_clearbreakpointtool(self):
        enable = bool(cw.cwpy.breakpoint_table or cw.cwpy.sdata.breakpoints)
        if cw.cwpy.frame.debugger.mi_clear_breakpoint.IsEnabled() <> enable:
            cw.cwpy.frame.debugger.mi_clear_breakpoint.Enable(enable)
            cw.cwpy.frame.debugger.tl_clear_breakpoint.Enable(enable)
            cw.cwpy.frame.debugger.tb_event.Realize()

    def OnInitVariables(self, event):
        self.view_var.init_variables()

    def refresh_areaname(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_areaname()

    def _refresh_areaname(self, force=False):
        assert threading.currentThread() <> cw.cwpy
        s = cw.cwpy.sdata.get_currentareaname()
        if sys.platform.startswith("linux"):
            dc = wx.ClientDC(self)
        else:
            dc = wx.ClientDC(self.st_area)
        sep = s.rfind("\\")
        w = self.st_area.GetClientSize()[0]
        if sep == -1:
            s2 = cw.util.abbr_longstr(dc, s, w)
        else:
            # 「フォルダ名\エリア名」のような名前は
            # 「フォ...\エリア名」のように略す
            left = s[:sep]
            right = s[sep:]
            lw = w - dc.GetTextExtent(right)[0]
            left = cw.util.abbr_longstr(dc, left, lw)
            s2 = left + right
            s2 = cw.util.abbr_longstr(dc, s2, w)
        self.st_area.SetLabel(s2)
        if s == s2:
            self.st_area.SetToolTipString("")
        else:
            self.st_area.SetToolTipString(s)

        # ツールボタンの表示を切り替えるかどうか
        if force or cw.cwpy.is_battlestatus() <> self.tl_area._battletool:
            if cw.cwpy.is_battlestatus():
                bmp = cw.cwpy.rsrc.debugs["BATTLECANCEL"]
                if self.mi_area.GetBitmap() <> bmp:
                    scenario_menu = self.mi_area.GetMenu()
                    scenario_menu.RemoveItem(self.mi_area)
                    self.mi_area = wx.MenuItem(scenario_menu, ID_AREA, u"戦闘中断(&A)",
                             u"戦闘を中断します。")
                    self.mi_area.SetBitmap(bmp)
                    scenario_menu.InsertItem(self._mi_area_index, self.mi_area)

                    self.tl_area.SetBitmap1(bmp)
                    self.tl_area.SetShortHelp(u"戦闘を中断します。")
                    self.tl_area._battletool = True
                    self.tb_area.Realize()
            else:
                bmp = cw.cwpy.rsrc.debugs["AREA"]
                if self.mi_area.GetBitmap() <> bmp:
                    scenario_menu = self.mi_area.GetMenu()
                    scenario_menu.RemoveItem(self.mi_area)
                    self.mi_area = wx.MenuItem(scenario_menu, ID_AREA, u"エリア(&A)",
                             u"エリアを選択して場面を変更します。")
                    self.mi_area.SetBitmap(bmp)
                    scenario_menu.InsertItem(self._mi_area_index, self.mi_area)

                    self.tl_area.SetBitmap1(bmp)
                    self.tl_area.SetShortHelp(u"エリアを選択して場面を変更します。")
                    self.tl_area._battletool = False
                    self.tb_area.Realize()

    def refresh_selectedmembername(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        s = cw.cwpy.event.get_selectedmembername()
        if sys.platform.startswith("linux"):
            dc = wx.ClientDC(self)
        else:
            dc = wx.ClientDC(self.st_select)
        s2 = cw.util.abbr_longstr(dc, s, self.st_select.GetClientSize()[0])
        self.st_select.SetLabel(s2)
        if s == s2:
            self.st_select.SetToolTipString("")
        else:
            self.st_select.SetToolTipString(s)

    def refresh_tools(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_tools()

    def _refresh_tools(self):
        assert threading.currentThread() <> cw.cwpy

        def func(self):
            ydata = bool(cw.cwpy.ydata)
            party = bool(cw.cwpy.ydata and cw.cwpy.ydata.party)
            savedjpdcimage = bool(ydata and cw.cwpy.ydata.savedjpdcimage)
            event_paused = cw.cwpy.event.is_paused()
            event_step = cw.cwpy.event.is_stepexec()
            battle = bool(cw.cwpy.battle)
            battle_is_running = cw.cwpy.battle and cw.cwpy.battle.is_running()
            is_showparty = cw.cwpy.is_showparty
            is_battlestatus = cw.cwpy.is_battlestatus()
            is_showingmessage = cw.cwpy.is_showingmessage()
            is_runningevent = cw.cwpy.is_runningevent()
            is_playingscenario = cw.cwpy.is_playingscenario()
            breakpoints = cw.cwpy.sdata.breakpoints.copy()
            def func(self):
                if not self:
                    return

                enabled = {}.copy()

                enabled[self.mi_comp.GetId()] = (self.mi_comp, self.tl_comp, False)
                enabled[self.mi_gossip.GetId()] = (self.mi_gossip, self.tl_gossip, False)
                enabled[self.mi_savedjpdcimage.GetId()] = (self.mi_savedjpdcimage, self.tl_savedjpdcimage, False)
                enabled[self.mi_money.GetId()] = (self.mi_money, self.tl_money, False)
                enabled[self.mi_card.GetId()] = (self.mi_card, self.tl_card, False)
                enabled[self.mi_member.GetId()] = (self.mi_member, self.tl_member, False)
                enabled[self.mi_coupon.GetId()] = (self.mi_coupon, self.tl_coupon, False)
                enabled[self.mi_status.GetId()] = (self.mi_status, self.tl_status, False)
                enabled[self.mi_recovery.GetId()] = (self.mi_recovery, self.tl_recovery, False)
                enabled[self.mi_break.GetId()] = (self.mi_break, self.tl_break, False)
                enabled[self.mi_editor.GetId()] = (self.mi_editor, self.tl_editor, False)
                enabled[self.mi_update.GetId()] = (self.mi_update, self.tl_update, False)
                enabled[self.mi_redisplay.GetId()] = (self.mi_redisplay, self.tl_redisplay, False)
                enabled[self.mi_battle.GetId()] = (self.mi_battle, self.tl_battle, False)
                enabled[self.mi_pack.GetId()] = (self.mi_pack, self.tl_pack, False)
                enabled[self.mi_friend.GetId()] = (self.mi_friend, self.tl_friend, False)
                enabled[self.mi_info.GetId()] = (self.mi_info, self.tl_info, False)
                enabled[self.mi_round.GetId()] = (self.mi_round, self.tl_round, False)
                enabled[self.mi_save.GetId()] = (self.mi_save, self.tl_save, False)
                enabled[self.mi_load.GetId()] = (self.mi_load, self.tl_load, False)
                enabled[self.mi_loadyado.GetId()] = (self.mi_loadyado, self.tl_loadyado, False)
                enabled[self.mi_reset.GetId()] = (self.mi_reset, self.tl_reset, False)
                enabled[self.mi_stepreturn.GetId()] = (self.mi_stepreturn, self.tl_stepreturn, False)
                enabled[self.mi_stepover.GetId()] = (self.mi_stepover, self.tl_stepover, False)
                enabled[self.mi_stepin.GetId()] = (self.mi_stepin, self.tl_stepin, False)
                enabled[self.mi_pause.GetId()] = (self.mi_pause, self.tl_pause, False)
                enabled[self.mi_stop.GetId()] = (self.mi_stop, self.tl_stop, False)
                enabled[self.mi_select.GetId()] = (self.mi_select, self.tl_select, False)
                enabled[self.mi_showparty.GetId()] = (self.mi_showparty, self.tl_showparty, False)
                enabled[self.mi_hideparty.GetId()] = (self.mi_hideparty, self.tl_hideparty, False)
                enabled[self.mi_area.GetId()] = (self.mi_area, self.tl_area, False)
                enabled[self.mi_startevent.GetId()] = (self.mi_startevent, self.tl_startevent, False)
                enabled[self.mi_breakpoint.GetId()] = (self.mi_breakpoint, self.tl_breakpoint, False)
                enabled[self.mi_clear_breakpoint.GetId()] = (self.mi_clear_breakpoint, self.tl_clear_breakpoint, False)
                enabled[self.mi_bgm.GetId()] = (self.mi_bgm, self.tl_bgm, True)
                enabled[self.mi_initvars.GetId()] = ((self.mi_initvars, self.view_var.mi_initvars), None, False)

                if ydata:
                    enabled[self.mi_comp.GetId()] = (self.mi_comp, self.tl_comp, True)
                    enabled[self.mi_gossip.GetId()] = (self.mi_gossip, self.tl_gossip, True)
                    if savedjpdcimage:
                        enabled[self.mi_savedjpdcimage.GetId()] = (self.mi_savedjpdcimage, self.tl_savedjpdcimage, True)
                    enabled[self.mi_money.GetId()] = (self.mi_money, self.tl_money, True)
                    enabled[self.mi_card.GetId()] = (self.mi_card, self.tl_card, True)
                    if party:
                        enabled[self.mi_member.GetId()] = (self.mi_member, self.tl_member, True)
                        enabled[self.mi_coupon.GetId()] = (self.mi_coupon, self.tl_coupon, True)
                    enabled[self.mi_loadyado.GetId()] = (self.mi_loadyado, self.tl_loadyado, True)

                if is_playingscenario:
                    enabled[self.mi_pause.GetId()] = (self.mi_pause, self.tl_pause, True)
                    enabled[self.mi_status.GetId()] = (self.mi_status, self.tl_status, True)
                    enabled[self.mi_recovery.GetId()] = (self.mi_recovery, self.tl_recovery, True)
                    enabled[self.mi_redisplay.GetId()] = (self.mi_redisplay, self.tl_redisplay, True)
                    if cw.cwpy.setting.editor:
                        enabled[self.mi_editor.GetId()] = (self.mi_editor, self.tl_editor, True)
                    if is_runningevent:
                        enabled[self.mi_select.GetId()] = (self.mi_select, self.tl_select, True)
                        if is_showparty:
                            enabled[self.mi_hideparty.GetId()] = (self.mi_hideparty, self.tl_hideparty, True)
                        else:
                            enabled[self.mi_showparty.GetId()] = (self.mi_showparty, self.tl_showparty, True)
                        enabled[self.mi_stop.GetId()] = (self.mi_stop, self.tl_stop, True)
                    else:
                        if not is_battlestatus:
                            enabled[self.mi_break.GetId()] = (self.mi_break, self.tl_break, True)
                            enabled[self.mi_save.GetId()] = (self.mi_save, self.tl_save, True)
                            enabled[self.mi_load.GetId()] = (self.mi_load, self.tl_load, True)
                        else:
                            enabled[self.mi_round.GetId()] = (self.mi_round, self.tl_round, True)

                        if not battle or not battle_is_running:
                            enabled[self.mi_update.GetId()] = (self.mi_update, self.tl_update, True)
                            enabled[self.mi_battle.GetId()] = (self.mi_battle, self.tl_battle, True)
                            enabled[self.mi_pack.GetId()] = (self.mi_pack,self.tl_pack, True)
                            enabled[self.mi_friend.GetId()] = (self.mi_friend, self.tl_friend, True)
                            enabled[self.mi_info.GetId()] = (self.mi_info, self.tl_info, True)
                            enabled[self.mi_reset.GetId()] = (self.mi_reset, self.tl_reset, True)
                            enabled[self.mi_area.GetId()] = (self.mi_area, self.tl_area, True)
                            enabled[self.mi_startevent.GetId()] = (self.mi_startevent, self.tl_startevent, True)
                    enabled[self.mi_initvars.GetId()] = ((self.mi_initvars, self.view_var.mi_initvars), None, True)

                else:
                    enabled[self.mi_pause.GetId()] = (self.mi_pause, self.tl_pause, True)

                step = bool((event_paused or\
                             (event_step and is_showingmessage)) and\
                            is_runningevent)
                enabled[self.mi_stepreturn.GetId()] = (self.mi_stepreturn, self.tl_stepreturn, step)
                enabled[self.mi_stepover.GetId()] = (self.mi_stepover, self.tl_stepover, step)
                enabled[self.mi_stepin.GetId()] = (self.mi_stepin, self.tl_stepin, step)

                if self.view_tree.selectionitem:
                    enabled[self.mi_breakpoint.GetId()] = (self.mi_breakpoint, self.tl_breakpoint, True)

                if breakpoints or cw.cwpy.breakpoint_table:
                    enabled[self.mi_clear_breakpoint.GetId()] = (self.mi_clear_breakpoint, self.tl_clear_breakpoint, True)

                bars = set()
                for mi, tl, enable in enabled.itervalues():
                    if cw.cwpy.is_debuggerprocessing:
                        enable = False
                    if isinstance(mi, wx.MenuItem):
                        if mi.IsEnabled() <> enable:
                            mi.Enable(enable)
                    else:
                        for mi2 in mi:
                            if mi2.IsEnabled() <> enable:
                                mi2.Enable(enable)
                    if tl and tl.IsEnabled() <> enable:
                        tl.Enable(enable)
                        bars.add(tl.GetToolBar())

                for bar in bars:
                    bar.Realize()
            cw.cwpy.frame.exec_func(func, self)

        cw.cwpy.exec_func(func, self)

    def refresh_showpartytools(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        self._refresh_showpartytools()

    def _refresh_showpartytools(self):
        assert threading.currentThread() <> cw.cwpy
        enabled = {}.copy()

        enabled[self.mi_showparty.GetId()] = (self.mi_showparty, self.tl_showparty, False)
        enabled[self.mi_hideparty.GetId()] = (self.mi_hideparty, self.tl_hideparty, False)

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.is_runningevent():
                if cw.cwpy.is_showparty:
                    enabled[self.mi_hideparty.GetId()] = (self.mi_hideparty, self.tl_hideparty, True)
                else:
                    enabled[self.mi_showparty.GetId()] = (self.mi_showparty, self.tl_showparty, True)

        update = False
        for mi, tl, enable in enabled.itervalues():
            if tl.IsEnabled() <> enable:
                mi.Enable(enable)
                tl.Enable(enable)
                update = True

        if update:
            self.tb_select.Realize()

class VariableListCtrl(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(
            self, parent, -1, style=wx.LC_REPORT|wx.BORDER_NONE|
            wx.LC_SORT_ASCENDING|wx.LC_VIRTUAL)
        self.list = []
        self.imglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
        self.imgidx_flag = self.imglist.Add(cw.cwpy.rsrc.debugs["FLAG"])
        self.imgidx_step = self.imglist.Add(cw.cwpy.rsrc.debugs["STEP"])
        self.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, u"名称")
        self.InsertColumn(1, u"現在値")
        self.SetColumnWidth(0, cw.ppis(120))
        self.SetColumnWidth(1, cw.ppis(80))

        self.popup_menu = wx.Menu()
        self.mi_initvars = wx.MenuItem(self.popup_menu, ID_INIT_VARIABLES, u"状態変数の初期化(&V)")
        self.mi_initvars.SetBitmap(cw.cwpy.rsrc.debugs["INIT_VARIABLES"])
        self.popup_menu.AppendItem(self.mi_initvars)

        self._refresh_variablelist()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        self.Bind(wx.EVT_MENU, self.OnInitVariables, id=ID_INIT_VARIABLES)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    def OnContextMenu(self, event):
        self.PopupMenu(self.popup_menu)

    def OnInitVariables(self, event):
        self.init_variables()

    def init_variables(self):
        def func():
            if not cw.cwpy.is_playingscenario():
                return
            update = False
            for var in cw.cwpy.sdata.flags.itervalues():
                if var.value <> var.defaultvalue:
                    var.set(var.defaultvalue, updatedebugger=False)
                    var.redraw_cards()
                    update = True
            for var in cw.cwpy.sdata.steps.itervalues():
                if var.value <> var.defaultvalue:
                    var.set(var.defaultvalue, updatedebugger=False)
                    update = True
            cw.cwpy.play_sound("signal")
            if update:
                cw.cwpy.event.refresh_variablelist()
        cw.cwpy.exec_func(func)

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
                    def func(item, value):
                        item.set(value)
                        item.redraw_cards()
                    cw.cwpy.exec_func(func, item, not bool(dlg.GetSelection()))
                elif isinstance(item, cw.data.Step):
                    def func(item, value):
                        item.set(value)
                    cw.cwpy.exec_func(func, item, dlg.GetSelection())

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

        def func(self):
            if cw.cwpy.is_playingscenario():
                vlist = cw.cwpy.sdata.steps.values()
                cw.util.sort_by_attr(vlist, "name")
                seq = cw.cwpy.sdata.flags.values()
                cw.util.sort_by_attr(seq, "name")
                vlist.extend(seq)
                def func(self, vlist):
                    if self:
                        self.list = vlist
                        self.SetItemCount(len(vlist))
                        self.Refresh()
                cw.cwpy.frame.exec_func(func, self, vlist)
            else:
                def func(self):
                    if self:
                        self.Refresh()
                cw.cwpy.frame.exec_func(func, self)

        cw.cwpy.exec_func(func, self)

class EventView(wx.ScrolledWindow):
    def __init__(self, parent):
        """イベントツリーを垂直表示するビュー。"""
        wx.ScrolledWindow.__init__(self, parent, -1)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.WHITE)

        # 左側の垂直バーの幅
        self._linenumwidth = cw.ppis(20)
        self.leftbarwidth = cw.ppis(24) + self._linenumwidth

        # 現在実行中のイベントツリーとイベント
        self.current_event = None
        self.current_tree = None
        self.current_content = None
        # 現在実行中のContent(item)
        self.activeitem = None
        # itemの辞書(keyはコンテントデータ)
        self.items = {}
        self.itemlist = []
        self.selectionitem = None
        self.selectionindex = -1
        self.refresh_tree()
        self.refresh_activeitem()
        self.processing = False
        self.maxwidth, self.maxheight = self.GetClientSize()
        self.scrollrate_x = 1
        self.scrollrate_y = 1
        self.lineheight = 1
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

    def AcceptsFocus(self):
        return True

    def AcceptsFocusFromKeyboard(self):
        return True

    def OnSetFocus(self, event):
        pass

    def OnKillFocus(self, event):
        pass

    def OnPaint(self, event):
        if not cw.cwpy.rsrc:
            return

        dc = wx.PaintDC(self)

        if sys.platform <> "win32" or 6 <= sys.getwindowsversion().major:
            try:
                dc = wx.GCDC(dc)
            except:
                pass

        if sys.platform.startswith("linux"):
            # FIXME: なぜか文字化けするので
            #        DPIも反映されない
            font = wx.Font(cw.ppis(12), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            dc.SetFont(font)

        csize = self.GetClientSize()
        csize = (csize[0]+self.leftbarwidth, csize[1])

        # ブレークポイント表示欄
        linepen = wx.Pen(wx.Colour(128, 128, 128))
        dc.SetPen(linepen)
        dc.SetBrush(wx.Brush(wx.Colour(240, 240, 240)))
        dc.DrawRectangle(-1, -1, self.leftbarwidth+2, csize[1]+cw.ppis(2))

        if not self.itemlist:
            dc.DrawText(u"ここに実行中のイベントツリーが表示されます。", self.leftbarwidth+cw.ppis(10), cw.ppis(5))
            hint = u"ヒント:"
            ts = dc.GetTextExtent(hint)
            tx = self.leftbarwidth+cw.ppis(10)
            ty = cw.ppis(10)+ts[1]
            dc.DrawText(hint, tx, ty)
            ts = dc.GetTextExtent(hint)
            dc.DrawText(u"ダブルクリックかEnterキー押下で任意の", tx+ts[0]+cw.ppis(5), ty)
            dc.DrawText(u"イベントコンテントを実行できます。", tx+ts[0]+cw.ppis(5), ty+ts[1])
            return

        selpen = wx.Pen(wx.Colour(255, 128, 128))
        selbrush = wx.Brush(wx.Colour(255, 240, 240))
        actpen =wx.Pen(wx.Colour(255, 192, 192))
        actbrush =wx.Brush(wx.Colour(255, 192, 192))
        bppen = wx.Pen(wx.Colour(128, 0, 0))
        bpbrush = wx.Brush(wx.Colour(128, 0, 0))
        bpbackbrush = wx.Brush(wx.Colour(255, 240, 232))

        x, y = self.GetViewStart()
        xtop = x * self.scrollrate_x
        ytop = y * self.scrollrate_y
        y = self.get_index((0, ytop))
        last = self.get_item((0, ytop + csize[1]))
        if not last:
            last = self.itemlist[-1]

        linenum = y + 1
        for item in self.itemlist[y:]:
            # 行番号
            dc.DestroyClippingRegion()
            dc.SetTextForeground(wx.Colour(64, 64, 64))
            linestr = u"%s" % (linenum)
            ts = dc.GetTextExtent(linestr)
            dc.DrawText(linestr, self.leftbarwidth-cw.ppis(6*2+5+5)-ts[0], item.pos[1]-ytop+(self.lineheight-ts[1])/2)

            clippingrect = wx.Rect(self.leftbarwidth + 1, 0,
                                   csize[0] - self.leftbarwidth + 1, csize[1])
            dc.SetClippingRect(clippingrect)

            # イベントコンテントを結ぶ線
            if item.parent is None and item <> self.itemlist[0]:
                dc.SetPen(linepen)
                dc.DrawLine(self.leftbarwidth + 1, item.pos[1]-ytop, csize[0], item.pos[1]-ytop)

            if item.cwxpath in cw.cwpy.sdata.breakpoints:
                dc.DestroyClippingRegion()
                dc.SetPen(bppen)
                dc.SetBrush(bpbrush)
                circlesize = cw.ppis(6)
                dc.DrawCircle(self.leftbarwidth-circlesize-cw.ppis(5), item.pos[1]-ytop+self.lineheight/2, circlesize)
                dc.SetClippingRect(clippingrect)
                dc.SetPen(wx.TRANSPARENT_PEN)
                dc.SetBrush(bpbackbrush)
                dc.DrawRectangle(self.leftbarwidth + 1, item.pos[1]-ytop, csize[0], self.lineheight)

            if item == self.activeitem:
                dc.SetPen(actpen)
                dc.SetBrush(actbrush)
                dc.DrawRectangle(self.leftbarwidth + 1, item.pos[1]-ytop, csize[0], self.lineheight)
            else:
                dc.SetBrush(selbrush)
            if item == self.selectionitem:
                dc.SetPen(wx.TRANSPARENT_PEN)
                dc.DrawRectangle(self.leftbarwidth + 1, item.pos[1]-ytop, csize[0], self.lineheight)
                dc.SetPen(selpen)
                dc.DrawLine(self.leftbarwidth + 1, item.pos[1]-ytop, csize[0], item.pos[1]-ytop)
                dc.DrawLine(self.leftbarwidth + 1, item.pos[1]-ytop+self.lineheight-1, csize[0], item.pos[1]-ytop+self.lineheight-1)

            linenum += 1

            if last == item:
                break

        pen = wx.Pen(wx.Colour(192, 192, 192), width=cw.ppis(4))
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        iw = cw.cwpy.rsrc.debugs["EVT_START"].GetWidth()
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        circles = []
        for i, item in enumerate(self.itemlist):
            if item.nextlen == 0:
                if i < y:
                    continue
            else:
                child = item.nextdata[-1]
                if child.tag == "ContentsLine":
                    child = child[0]
                if self.items[child].pos[1] < ytop:
                    continue
            ix, iy = item.pos
            ix -= xtop
            iy -= ytop
            cx = ix + iw/2 + self.leftbarwidth
            cy = iy + self.lineheight/2
            if item.nextlen == 0:
                bottom = cy+self.lineheight-cw.ppis(4)
                dc.DrawLine(cx, cy, cx, bottom)
                dc.DrawLine(cx-cw.ppis(5), bottom, cx+cw.ppis(5), bottom)
            else:
                for child in item.nextdata:
                    if child.tag == "ContentsLine":
                        child = child[0]
                    child = self.items[child]
                    if child.pos[0] == item.pos[0]:
                        bottom = child.pos[1]-ytop + self.lineheight/2
                        dc.DrawLine(cx, cy, cx, bottom)
                    else:
                        bottom = child.pos[1]-ytop-self.lineheight/2
                        if cy < bottom:
                            dc.DrawLine(cx, cy, cx, bottom)
                            circles.append((cx, bottom+cw.ppis(2)))
                        dc.DrawArc(cx, bottom, cx+iw, bottom+self.lineheight, cx+iw, bottom)

            if last == item:
                break

        dc.SetBrush(wx.WHITE_BRUSH)
        for cx, cy in circles:
            dc.DrawCircle(cx, cy, cw.ppis(6))

        yg = (self.lineheight - dc.GetTextExtent("#")[1]) / 2
        for item in self.itemlist[y:]:
            if item.image:
                dc.DrawBitmap(item.image, item.pos[0]-xtop+self.leftbarwidth, item.pos[1]-ytop, True)
            s = item.text
            if item == self.activeitem:
                dc.SetTextForeground(wx.RED)
                s += u" // ACTIVE!"
            else:
                dc.SetTextForeground(wx.BLACK)
            if item.image:
                imgwidth = item.image.GetWidth()
            else:
                imgwidth = 0
            dc.DrawText(s,
                        item.pos[0]+imgwidth+cw.ppis(2)-xtop+self.leftbarwidth,
                        item.pos[1]-ytop+yg)

            if last == item:
                break

    def get_item(self, pos):
        index = self.get_index(pos)
        if index == -1:
            return None
        else:
            return self.itemlist[index]

    def get_index(self, pos):
        y = pos[1]
        index = -1
        seq = self.itemlist
        ii = 0
        i = len(seq) / 2
        while 0 <= i and i < len(seq):
            if seq[i].is_contains(pos):
                index = i
                break
            elif y < seq[i].pos[1]:
                seq = seq[:i]
                i = len(seq) / 2
            elif seq[i].pos[1] + seq[i].height <= y:
                seq = seq[i+1:]
                ii += i + 1
                i = len(seq) / 2
        return index + ii

    def set_selectionitem(self, item):
        enable = bool(self.selectionitem)
        self.selectionitem = item
        if cw.cwpy.frame.debugger:
            cw.cwpy.frame.debugger.refresh_breakpointtool()

    def switch_breakpoint(self, item=None):
        if item is None:
            item = self.selectionitem
        if not item:
            return

        if item.cwxpath in cw.cwpy.sdata.breakpoints:
            cw.cwpy.sdata.breakpoints.remove(item.cwxpath)
        else:
            cw.cwpy.sdata.breakpoints.add(item.cwxpath)
        self.Refresh()
        if cw.cwpy.frame.debugger:
            cw.cwpy.frame.debugger.refresh_clearbreakpointtool()

    def OnLeftDown(self, event):
        self.SetFocus()
        x, y = self.GetViewStart()
        xtop = x * self.scrollrate_x
        ytop = y * self.scrollrate_y

        if event.GetX() < self.leftbarwidth:
            # ブレークポイント切替
            item = self.get_item((event.GetX()+xtop, event.GetY()+ytop))
            if item:
                self.switch_breakpoint(item)
            return

        index = self.get_index((event.GetX()+xtop, event.GetY()+ytop))
        if index <> -1:
            item = self.itemlist[index]
            content = cw.content.get_content(item.content)
            self.set_selectionitem(item)
            self.selectionindex = index
            self.Parent.statusbar.SetStatusText(content.get_status(), 0)
            self.Refresh()

    def OnDClick(self, event):
        self.SetFocus()
        x, y = self.GetViewStart()
        if event.GetX() < self.leftbarwidth:
            return
        xtop = x * self.scrollrate_x
        ytop = y * self.scrollrate_y
        item = self.get_item((event.GetX()+xtop, event.GetY()+ytop))
        if not item:
            return

        self.set_activeitem(item)

    def set_activeitem(self, item):
        # スタートコンテントの場合は次のコンテントへ遷移
        data = item.content
        if item.parent is None:
            e = item.nextdata
            if not len(e):
                return
            data = e[0]

        if not data is None:
            cw.cwpy.exec_func(cw.cwpy.event.set_curcontent, data, self.current_event)

    def OnKeyDown(self, event):
        if not self.itemlist:
            return
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_LEFT, wx.WXK_UP):
            if self.selectionitem:
                index = self.selectionindex
                if 0 < index:
                    self.set_selectionitem(self.itemlist[index-1])
                    self.selectionindex = index-1
                    self.show_item(self.selectionitem)
                    self.Refresh()
            else:
                self.set_selectionitem(self.itemlist[0])
                self.selectionindex = 0
                self.show_item(self.selectionitem)
                self.Refresh()

        elif keycode in (wx.WXK_RIGHT, wx.WXK_DOWN):
            if self.selectionitem:
                index = self.selectionindex
                if index+1 < len(self.itemlist):
                    self.set_selectionitem(self.itemlist[index+1])
                    self.selectionindex = index+1
                    self.show_item(self.selectionitem)
                    self.Refresh()
            else:
                self.set_selectionitem(self.itemlist[0])
                self.selectionindex = 0
                self.show_item(self.selectionitem)
                self.Refresh()

        if self.selectionitem and keycode in (wx.WXK_LEFT, wx.WXK_UP, wx.WXK_RIGHT, wx.WXK_DOWN):
            content = cw.content.get_content(self.selectionitem.content)
            self.Parent.statusbar.SetStatusText(content.get_status(), 0)

    def OnKeyUp(self, event):
        if not self.itemlist:
            return
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_RETURN, wx.WXK_SPACE):
            if not self.selectionitem:
                return
            if self.selectionitem == self.activeitem:
                return
            self.set_activeitem(self.selectionitem)

    def show_item(self, item):
        x, y = self.GetViewStart()
        _w, h = self.GetClientSize()
        _xtop = x * self.scrollrate_x
        ytop = y * self.scrollrate_y
        if item.pos[1] + item.height < ytop:
            ytop = item.pos[1]
            y = ytop / self.scrollrate_y
            self.Scroll(x, y)
        elif ytop + h <= item.pos[1] + item.height:
            y = (item.pos[1] + item.height) / self.scrollrate_y
            y -= h / self.scrollrate_y
            self.Scroll(x, y)

    def refresh_activeitem(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        processing = self.processing
        self.processing = True

        def func(self):
            event = cw.cwpy.event.get_event()
            nowrunning= cw.cwpy.event.get_nowrunningevent()
            cur_content = event.cur_content if event else None
            if not cur_content is None and cur_content.tag == "ContentsLine":
                cur_content = cur_content[event.line_index]

            def func(self, nowrunning, event, cur_content):
                if not self:
                    return

                if event and cur_content in self.items:
                    if self.current_content == cur_content:
                        self.processing = processing
                        return
                    self.current_content = cur_content
                    self.activeitem = self.items[cur_content]
                    self.show_item(self.activeitem)
                    s = cw.content.get_content(self.current_content).get_status()
                    self.Parent.statusbar.SetStatusText(s, 0)
                else:
                    self.current_content = None
                    self.Parent.statusbar.SetStatusText(u"", 0)
                self.Refresh()
                if self.Parent.view_stacktrace:
                    self.Parent.view_stacktrace.refresh_activeitem(nowrunning, cur_content)
                self.processing = processing

            cw.cwpy.frame.exec_func(func, self, nowrunning, event, cur_content)

        cw.cwpy.exec_func(func, self)

    def refresh_tree(self):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        processing = self.processing
        self.processing = True

        def func(self):
            nowrunning = cw.cwpy.event.get_nowrunningevent()
            if not cw.cwpy.is_playingscenario() or cw.cwpy.areaid < 0:
                nowrunning = None

            trees = nowrunning.trees if not nowrunning is None else None

            def func(self, nowrunning, trees):
                if not self:
                    return

                self._refresh_tree(nowrunning, trees)
                self.processing = processing

            cw.cwpy.frame.exec_func(func, self, nowrunning, trees)

        cw.cwpy.exec_func(func, self)

    def set_event(self, event, selection=None):
        assert threading.currentThread() <> cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return
        processing = self.processing
        self.processing = True

        def func(self, event):
            trees = event.trees if not event is None else None

            def func(self, event, trees):
                if not self:
                    return

                self._refresh_tree(event, trees)
                if not selection is None:
                    item = self.items.get(selection, None)
                    if item:
                        self.set_selectionitem(item)
                        self.show_item(item)
                        self.Refresh()
                self.processing = processing

            cw.cwpy.frame.exec_func(func, self, event, trees)

        cw.cwpy.exec_func(func, self, event)

    def _refresh_tree(self, nowrunning, trees):
        if nowrunning is None:
            self._linenumwidth = cw.ppis(20)
            self.leftbarwidth = cw.ppis(24) + self._linenumwidth
            self.items = {}
            self.itemlist = []
            self.activeitem = None
            self.set_selectionitem(None)
            self.selectionindex = -1
            self.current_event = None
            self.current_tree = None
            self.current_content = None
            self.SetVirtualSize((1, 1))
            self.Refresh()
            return

        self.maxwidth, self.maxheight = 0, 0
        icon = cw.cwpy.rsrc.debugs["EVT_START"]
        dc = wx.ClientDC(self)
        actw, self.lineheight = dc.GetTextExtent(" // ACTIVE!")
        shiftx = icon.GetWidth()
        self.lineheight = max(icon.GetHeight() + cw.ppis(2), self.lineheight)
        if self.current_tree <> trees:
            trees = nowrunning.trees
            self.current_event = nowrunning
            self.current_tree = trees
            self.Parent.statusbar.SetStatusText(u"", 0)
            self.activeitem = None
            self.set_selectionitem(None)
            self.selectionindex = -1
            self.items = {}
            self.itemlist = []

            if self.current_tree:
                for name in nowrunning.treekeys:
                    tree = trees[name]
                    self.create_item(None, tree, shiftx, dc)

            if self.itemlist:
                item = self.itemlist[-1]
                self.maxheight = item.pos[1] + item.height

                # 行番号表示幅を計算(最小=self._linenumwidth)
                maxline = len(self.itemlist)
                nw = 0
                for i in xrange(0, 10):
                    nw = max(nw, dc.GetTextExtent("%s" % (i))[0])
                linew = max(self._linenumwidth, len("%s" % (maxline))*nw+cw.ppis(5))
            else:
                linew = self._linenumwidth
            self.leftbarwidth = cw.ppis(24) + linew

            self.maxwidth += actw

            self.SetVirtualSize((self.maxwidth, self.maxheight))
            self.scrollrate_x = shiftx
            self.scrollrate_y = self.lineheight
            self.SetScrollRate(self.scrollrate_x, self.scrollrate_y)
            self.Scroll(0, 0)
            self.Refresh()

    def create_item(self, parentitem, contents, shiftx, dc):
        assert threading.currentThread() <> cw.cwpy

        def update_pos():
            if parentitem:
                parent = parentitem.content
                x = parentitem.pos[0]
                if parentitem.is_branch():
                    x += shiftx
            else:
                parent = None
                x = cw.ppis(0)

            if self.itemlist:
                item = self.itemlist[-1]
                pos = (x, item.pos[1] + item.height)
            else:
                pos = cw.ppis((0, 0))
            return parent, x, pos

        isline = contents.tag == "ContentsLine"
        if not isline:
            contents = (contents,)

        for i, content in enumerate(contents):
            parent, x, pos = update_pos()
            if isline and i+1 < len(contents):
                nextdata = (contents[i+1],)
            else:
                nextdata = content.find("Contents")
                if nextdata is None:
                    nextdata = ()
            item = EventViewItem(parent, content, nextdata, pos, self.lineheight, dc)
            assert content.tag <> "ContentsLine"
            self.items[content] = item
            self.itemlist.append(item)
            self.maxwidth = max(item.pos[0] + item.width, self.maxwidth)
            if not (isline and i+1 < len(contents)):
                for e in item.nextdata:
                    self.create_item(item, e, shiftx, dc)

            parentitem = item


class EventViewItem(object):
    def __init__(self, parent, content, nextdata, pos, lineheight, dc):
        assert threading.currentThread() <> cw.cwpy
        self.parent = parent
        self.content = content
        self.cwxpath = content.get_cwxpath()
        self.pos = pos
        s = u""
        if not self.parent is None:
            parent = cw.content.get_content(self.parent)
            if parent:
                s = parent.get_childname(self.content)
        else:
            s = self.content.get("name", "")
        self.text = s
        self.image = get_contenticon(self.content)
        self.nextdata = nextdata
        self.nextlen = len(self.nextdata)

        if self.nextlen:
            self.height = lineheight
        else:
            self.height = lineheight * 2

        if self.image:
            self.width = self.image.GetWidth()
        else:
            self.width = cw.ppis(0)
        if self.text:
            self.width += cw.ppis(2)
            self.width += dc.GetTextExtent(self.text)[0]

    def is_branch(self):
        return 2 <= self.nextlen or\
            self.content.tag == "Branch" or\
            self.parent is None

    def is_contains(self, pos):
        return self.pos[1] <= pos[1] and pos[1] < self.pos[1] + self.height


def get_contenticon(content):
    s = "EVT_" + content.tag.upper()
    if "type" in content.attrib:
        s += "_" + content.get("type").upper()
    return cw.cwpy.rsrc.debugs.get(s, None)


class StackTraceView(wx.ListCtrl, wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, size=(-1, cw.ppis(80)),
                             style=wx.LC_REPORT|wx.LC_NO_HEADER)
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)
        self.list = []
        self.imglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
        self.imgidx_area = self.imglist.Add(cw.cwpy.rsrc.debugs["AREA"])
        self.imgidx_battle = self.imglist.Add(cw.cwpy.rsrc.debugs["BATTLE"])
        self.imgidx_package = self.imglist.Add(cw.cwpy.rsrc.debugs["PACK"])
        self.imgidx_card = self.imglist.Add(cw.cwpy.rsrc.debugs["CARD"])
        self.imgidx_event = self.imglist.Add(cw.cwpy.rsrc.debugs["EVENT"])
        self.imgidx_link_start = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_LINK_START"])
        self.imgidx_call_start = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_CALL_START"])
        self.imgidx_link_package = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_LINK_PACKAGE"])
        self.imgidx_call_package = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_CALL_PACKAGE"])
        self.imgidx_effect = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_EFFECT"])
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST"])
        self.imgidx_contents = {}
        self._has_curcontent = False
        self.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.InsertColumn(0, u"呼び出し履歴")
        self.SetColumnWidth(0, cw.ppis(400))
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)

    def OnDClick(self, event):
        if not cw.cwpy.event.is_paused() and not cw.cwpy.is_showingmessage():
            return
        if self.GetSelectedItemCount() == 1:
            item = self.list[self.GetFirstSelected()]
            evt, cur_content = item
            self.Parent.view_tree.set_event(evt, selection=cur_content)

    def refresh_stackinfo(self):
        assert cw.cwpy <> threading.currentThread()
        def func(self):
            def func(self, nowrunning, cur_content, stackinfo):
                if not self:
                    return
                self.DeleteAllItems()
                del self.list[:]
                if not stackinfo:
                    return

                for evt in stackinfo:
                    name, icon, data = self._get_item(evt)
                    if not data:
                        continue
                    self.InsertImageStringItem(self.GetItemCount(), name, icon)
                    self.list.append(data)

                if cur_content is None:
                    self._has_curcontent = False
                else:
                    name, icon = self._get_info(cur_content)
                    self.InsertImageStringItem(self.GetItemCount(), name, icon)
                    self.list.append((nowrunning, cur_content))
                    self._has_curcontent = True

            nowrunning = cw.cwpy.event.get_nowrunningevent()
            event = cw.cwpy.event.get_event()
            if event:
                e = event.cur_content
                if not e is None and e.tag == "ContentsLine":
                    e = e[event.line_index]
            else:
                e = None
            cw.cwpy.frame.exec_func(func, self, nowrunning, e, cw.cwpy.event.stackinfo[:cw.cwpy.event.stackinfo_len])
        cw.cwpy.exec_func(func, self)

    def _get_item(self, evt):
        if isinstance(evt, cw.event.Event):
            e = evt.starttree
            if e is None:
                return None, None, None
            icon = None
            while not e.cwxparent is None:
                e = e.cwxparent
                if e.tag == "Area":
                    icon = self.imgidx_area
                elif e.tag == "Battle":
                    icon = self.imgidx_battle
                elif e.tag == "Package":
                    icon = self.imgidx_package
                elif e.tag == "SkillCard":
                    icon = self.imgidx_skill
                elif e.tag == "ItemCard":
                    icon = self.imgidx_item
                elif e.tag == "BeastCard":
                    icon = self.imgidx_beast
                elif e.tag in ("MenuCard", "LargeMenuCard", "EnemyCard"):
                    icon = self.imgidx_card
                else:
                    continue
                break
            if icon is None:
                return None, None, None
            if e.tag == "EnemyCard":
                resid = e.getint("Property/Id", 0)
                enemy = cw.cwpy.sdata.get_castname(resid)
                if enemy is None:
                    name = u"(未設定)"
                else:
                    name = enemy[0] if enemy[0] else u"(名称なし)"
            else:
                name = e.gettext("Property/Name", u"(名称なし)")
            name += u" (%s)" % (evt.treekeys[0] if evt.treekeys[0] else u"イベント名なし")
            e = evt.starttree
            if not e is None and e.tag == "ContentsLine":
                e = e[0]
            return name, icon, (evt, e)
        else:
            assert isinstance(evt, tuple), str(evt)
            evt2, e, line_index = evt
            if not e is None and e.tag == "ContentsLine":
                e = e[line_index]
            ctype = e.getattr(".", "type", "")
            if e.tag == "Call" and ctype == "Start":
                icon = self.imgidx_call_start
            elif e.tag == "Link" and ctype == "Start":
                icon = self.imgidx_link_start
            elif e.tag == "Call" and ctype == "Package":
                icon = self.imgidx_call_package
            elif e.tag == "Link" and ctype == "Package":
                icon = self.imgidx_link_package
            elif e.tag == "Effect" and ctype == "":
                icon = self.imgidx_effect
            else:
                assert False, e.tag + ctype
            name = cw.content.get_content(e).get_status()
            return name, icon, (evt2, e)

    def _get_info(self, cur_content):
        name = cw.content.get_content(cur_content).get_status()
        cname = cur_content.tag + cur_content.getattr(".", "type", "")
        if cname in self.imgidx_contents:
            icon = self.imgidx_contents[cname]
        else:
            bmp = get_contenticon(cur_content)
            icon = self.imglist.Add(bmp)
            self.imgidx_contents[cname] = icon
        return name, icon

    def append_stackinfo_cwpy(self, item):
        assert threading.currentThread() is cw.cwpy
        if cw.cwpy.frame.debugger is None:
            return

        def func(self, item):
            if not self:
                return
            index = self.GetItemCount()
            name, icon, data = self._get_item(item)
            if not data:
                return
            if self._has_curcontent:
                self.list.append(self.list[-1])
                self.list[-2] = data
                index -= 1
            else:
                self.list.append(data)
            self.InsertImageStringItem(index, name, icon)

        cw.cwpy.frame.exec_func(func, self, item)

    def pop_stackinfo_cwpy(self):
        assert threading.currentThread() is cw.cwpy

        def func(self):
            if not self:
                return
            index = self.GetItemCount()-1
            if self._has_curcontent:
                self.list[-2] = self.list[-1]
                self.list.pop()
                index -= 1
            else:
                self.list.pop()
            self.DeleteItem(index)
        cw.cwpy.frame.exec_func(func, self)

    def replace_stackinfo_cwpy(self, index, item):
        assert threading.currentThread() is cw.cwpy

        def func(self, index, item):
            if not self:
                return
            name, icon, data = self._get_item(item)
            if not data:
                return
            self.SetItemText(index, name)
            self.SetItemImage(index, icon)
            self.list[index] = data
        cw.cwpy.frame.exec_func(func, self, cw.cwpy.event.stackinfo_len+index, item)

    def clear_stackinfo_cwpy(self):
        assert threading.currentThread() is cw.cwpy

        def func(self):
            if not self:
                return
            self.DeleteAllItems()
            del self.list[:]
            self._has_curcontent = False
        cw.cwpy.frame.exec_func(func, self)

    def refresh_activeitem(self, nowrunning, cur_content):
        assert cw.cwpy <> threading.currentThread()
        if cur_content is None:
            return
        name, icon = self._get_info(cur_content)
        if self._has_curcontent:
            self.SetItemText(self.GetItemCount()-1, name)
            self.SetItemImage(self.GetItemCount()-1, icon)
            self.list[-1] = (nowrunning, cur_content)
        else:
            self.InsertImageStringItem(self.GetItemCount(), name, icon)
            self.list.append((nowrunning, cur_content))
            self._has_curcontent = True


def main():
    pass

if __name__ == "__main__":
    main()
