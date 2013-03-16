#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import threading
import wx
import pygame

import cw


class Frame(wx.Frame):
    def __init__(self, skindirname=""):
        # トップフレーム
        self.style = wx.CAPTION|wx.CLOSE_BOX|wx.MINIMIZE_BOX|wx.SYSTEM_MENU\
                                                            |wx.SIMPLE_BORDER
        wx.Frame.__init__(self, None, -1, cw.APP_NAME, style=self.style)
        self.thread = threading.currentThread()
        self.SetClientSize(cw.SIZE_GAME)
        # SDLを描画するパネル
        self.panel = wx.Panel(self, -1, size=cw.SIZE_GAME, style=wx.NO_BORDER)
        os.environ["SDL_WINDOWID"] = str(self.panel.GetHandle())

        if sys.platform == "win32":
            os.environ["SDL_VIDEODRIVER"] = "windib"
##            os.environ["SDL_AUDIODRIVER"] = "waveout"

        # debbuger
        self.debugger = None
        # アイコン
        self.set_icon(self)
        # bind
        self._bind()
        # 設定
        setting = cw.setting.Setting()
        if skindirname:
            setting.skindirname = skindirname
            setting.write()
            setting.init_settings()
        # 起動直後のスレッド数を記憶
        self.initialThreadCount = threading.activeCount()
        # CWPyサブスレッド
        cw.cwpy = cw.thread.CWPy(setting, self)
        cw.cwpy.start()
        # データベースファイル更新をサブスレッドで実行
        dbupdater = cw.scenariodb.ScenariodbUpdatingThread()
        dbupdater.start()

        # スキン自動生成のためのドロップ受付
        self.DragAcceptFiles(True)

    def set_icon(self, win):
        if sys.platform == "win32":
            icon = wx.Icon(sys.executable, wx.BITMAP_TYPE_ICO)
            icon.SetSize(wx.ArtProvider.GetSizeHint(wx.ART_FRAME_ICON))
            win.SetIcon(icon)

    def _bind(self):
        self.Bind(wx.EVT_ICONIZE, self.OnIconize)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self._bind_customevent()

    def _bind_customevent(self):
        """CWPyスレッドからメインスレッドを
        操作するためのカスタムイベントを設定。
        """
        # サブスレッドからのメソッド実行のためのカスタムイベント設定
        self._EVTTYPE_EXECFUNC = wx.NewEventType()
        event = wx.PyEventBinder(self._EVTTYPE_EXECFUNC, 0)
        self.Bind(event, getattr(self, "OnEXECFUNC"))

        # ダイアログ呼び出しのためのカスタムイベント設定
        dlgeventnames = (
            "CLOSE",  # ゲーム終了ダイアログ
            "MENUCARDINFO",  # メニューカード情報ダイアログ
            "YADOSELECT",  # 宿選択ダイアログ
            "PARTYSELECT",  # パーティ選択ダイアログ
            "PLAYERSELECT",  # 冒険者選択ダイアログ
            "SCENARIOSELECT",  # 貼り紙選択ダイアログ
            "ALBUM",  # アルバムダイアログ
            "BACKPACK",  # 荷物袋ダイアログ
            "STOREHOUSE",  # カード置場ダイアログ
            "CARDPOCKET",  # プレイヤ所持カードダイアログ
            "HANDVIEW",  # 戦闘手札カードダイアログ
            "INFOVIEW",  # 情報カードダイアログ
            "CHARAINFO",  # キャラクタ情報ダイアログ
            "RETURNTITLE",  # タイトルに戻るダイアログ
            "SAVE",  # セーブダイアログ
            "USECARD",   # カード使用ダイアログ
            "RUNAWAY",   # 逃走確認ダイアログ
            "ERROR",  # エラーダイアログ
            "MESSAGE",   # メッセージダイアログ
            "YESNO",   # 確認ダイアログ
            "DATACOMP",   # 不足データの補填ダイアログ
            "PARTYEDIT",   # パーティ情報ダイアログ
            "BATTLECOMMAND",  # 行動選択ダイアログ
            "SETTINGS",  # 設定ダイアログ
            "F9",  # 緊急非難ダイアログ
            )
        self.dlgeventtypes = {}

        for eventname in dlgeventnames:
            eventtype = wx.NewEventType()
            event = wx.PyEventBinder(eventtype, 0)
            self.dlgeventtypes[eventname] = eventtype
            self.Bind(event, getattr(self, "On" + eventname))

    def show_debugger(self):
        """デバッガ開く。"""
        if cw.cwpy.debug and not self.debugger:
            # キー入力初期化
            cw.cwpy.keyevent.clear()
            dlg = cw.debug.debugger.Debugger(self)
            # メインフレームの真横に表示
            w = dlg.GetSize()[0]
            w -= (w - self.GetSize()[0]) / 2
            self.move_dlg(dlg, (w, 0))
            dlg.Show()
            self.debugger = dlg

    def close_debugger(self):
        """デバッガ閉じる。"""
        if self.debugger:
            self.debugger.Close()

    def exec_func(self, func, *args, **kwargs):
        """wxPythonスレッドで指定したファンクションを実行する。
        func: 実行したいファンクションオブジェクト。
        """
        event = wx.PyCommandEvent(self._EVTTYPE_EXECFUNC)
        event.func = func
        event.args = args
        event.kwargs = kwargs
        self.AddPendingEvent(event)

    def sync_exec(self, func, *args, **kwargs):
        """wxPythonスレッドで指定したファンクションを実行し、
        終了を待ち合わせる。ファンクションの戻り値を返す。
        func: 実行したいファンクションオブジェクト。
        """
        if self.thread == threading.currentThread():
            return func(*args, **kwargs)
        else:
            cl = wx.CallLater(0, func, args, kwargs)
            while cl.IsRunning() and cw.cwpy.is_running() and self.IsEnabled():
                time.sleep(0.001)
            return cl.GetResult()

    def OnEXECFUNC(self, event):
        try:
            func = event.func
        except:
            print "failed to execute function on main thread."
            return

        func(*event.args, **event.kwargs)

    def OnSetFocus(self, event):
        """SDL描画パネルがフォーカスされたときに呼ばれ、
        トップフレームにフォーカスを戻す。wx側がキー入力イベントを取得するため、
        ゲーム中は常にトップフレームがフォーカスされていなければならない。
        """
        self.SetFocus()

    def OnKeyUp(self, event):
        keycode = event.GetKeyCode()
        cw.cwpy.keyevent.keyup(keycode)

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        cw.cwpy.keyevent.keydown(keycode)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=4)
        else:
            evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=5)

        pygame.event.post(evt)

    def OnDropFiles(self, event):
        paths = event.GetFiles()

        for path in paths:
            if path.lower().endswith(".exe"):
                # スキンの自動生成
                dlg = cw.dialog.skin.SkinConversionDialog(self, path)
                self.move_dlg(dlg)
                def OnClose(event):
                    dlg.Destroy()
                dlg.Bind(wx.EVT_CLOSE, OnClose, dlg)
                dlg.ShowModal()
                if dlg.select_skin:
                    cw.cwpy.setting.skindirname = dlg.skindirname
                    cw.cwpy.setting.write()
                    cw.cwpy.setting.init_settings()
                    cw.cwpy.init_pygame(cw.cwpy.setting)
                break

    def OnDestroy(self, event):
        cw.cwpy._running = False

        while threading.activeCount() > self.initialThreadCount:
            pass

        cw.util.t_print()
        sys.exit()

    def OnIconize(self, event):
        """最小化イベント。最小化したときBGMの音も消す。"""
        if event.Iconized():
            cw.cwpy.music.set_volume(0)
        else:
            cw.cwpy.music.set_volume()

    def OnCLOSE(self, event):
        s = cw.cwpy.msgs["confirm_quit"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.Destroy()
        else:
            self.kill_dlg(dlg)

    def OnSETTINGS(self, event):
        dlg = cw.dialog.settings.SettingsDialog(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnMENUCARDINFO(self, event):
        dlg = cw.dialog.cardinfo.MenuCardInfo(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnYADOSELECT(self, event):
        dlg = cw.dialog.select.YadoSelect(self)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.load_yado(dlg.list[dlg.index])

        self.kill_dlg(dlg)

    def OnPARTYSELECT(self, event):
        dlg = cw.dialog.select.PartySelect(self)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            header = dlg.list[dlg.index]
            sceheader = header.get_sceheader()

            # シナリオプレイ途中から再開
            if sceheader:
                cw.cwpy.exec_func(cw.cwpy.ydata.load_party, header)
                cw.cwpy.exec_func(cw.cwpy.set_scenario, sceheader)
            # シナリオロードに失敗
            elif header.is_adventuring():
                cw.cwpy.sounds["error"].play()
                s = (cw.cwpy.msgs["load_scenario_failure"])
                mdlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                self.move_dlg(mdlg)

                if mdlg.ShowModal() == wx.ID_OK:
                    header.remove_adventuring()
                    cw.cwpy.exec_func(cw.cwpy.load_party, header)

                mdlg.Destroy()
            else:
                cw.cwpy.exec_func(cw.cwpy.load_party, header)

            if cw.cwpy.is_showingdebugger():
                func = cw.cwpy.frame.debugger.refresh_tools
                cw.cwpy.exec_func(func)

        self.kill_dlg(dlg)

    def OnPLAYERSELECT(self, event):
        dlg = cw.dialog.select.PlayerSelect(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

        def func():
            if cw.cwpy.ydata.party:
                areaid = 2
            else:
                areaid = 1
            if areaid <> cw.cwpy.areaid:
                cw.cwpy.ydata.party._loading = False
                cw.cwpy.change_area(areaid)
        cw.cwpy.exec_func(func)

    def OnSCENARIOSELECT(self, event):
        # Scenariodb更新用のサブスレッドの処理が終わるまで待機
        while not cw.scenariodb.ScenariodbUpdatingThread._finished:
            pass

        try:
            db = cw.scenariodb.Scenariodb()
        except:
            s = (u"データベースへの接続に失敗しました。\n"
                 u"しばらくしてからもう一度やり直してください。")
            event.args = {"text":s, "shutdown":False}
            self.OnERROR(event)
            return

        if not os.path.exists(u"Scenario"):
            os.makedirs(u"Scenario")
        dlg = cw.dialog.select.ScenarioSelect(self, db)
        if cw.cwpy.setting.lastscenario:
            dlg.set_selected(cw.cwpy.setting.lastscenario)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            header = dlg.list[dlg.index]
            cw.cwpy.exec_func(cw.cwpy.set_scenario, header, dlg.get_selected())

        # キャンセルしても最後の選択は記憶する
        cw.cwpy.setting.lastscenario = dlg.get_selected()

        self.kill_dlg(dlg)

    def OnALBUM(self, event):
        dlg = cw.dialog.select.Album(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnBACKPACK(self, event):
        self.change_cardcontrolarea()
        dlg = cw.dialog.cardcontrol.CardHolder(self, "BACKPACK")
        self.move_dlg(dlg, (0, -63))

        if not dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg)

    def OnSTOREHOUSE(self, event):
        self.change_cardcontrolarea()
        dlg = cw.dialog.cardcontrol.CardHolder(self, "STOREHOUSE")
        self.move_dlg(dlg, (0, -63))

        if not dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg)

    def OnCARDPOCKET(self, event):
        self.change_cardcontrolarea()
        dlg = cw.dialog.cardcontrol.CardHolder(self, "CARDPOCKET")
        self.move_dlg(dlg, (0, -63))

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.is_playingscenario() and cw.cwpy.areaid > 0:
                cw.cwpy.exec_func(cw.cwpy.change_specialarea, cw.cwpy.areaid)

        else:
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg)

    def OnHANDVIEW(self, event):
        self.change_cardcontrolarea()
        dlg = cw.dialog.cardcontrol.HandView(self)
        self.move_dlg(dlg, (0, -63))

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.is_playingscenario() and cw.cwpy.areaid > 0:
                cw.cwpy.exec_func(cw.cwpy.change_specialarea, cw.cwpy.areaid)

        else:
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg)

    def OnINFOVIEW(self, event):
        dlg = cw.dialog.cardcontrol.InfoView(self)
        self.move_dlg(dlg, (0, -63))
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnCHARAINFO(self, event):
        dlg = cw.dialog.charainfo.ActiveCharaInfo(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnRETURNTITLE(self, event):
        s = (cw.cwpy.msgs["confirm_go_title"])
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.exec_func(cw.cwpy.set_title)

        self.kill_dlg(dlg)

    def OnSAVE(self, event):
        s = cw.cwpy.msgs["confirm_save"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            cw.cwpy.ydata.save()
            cw.cwpy.sounds["signal"].play()
            s = cw.cwpy.msgs["saved"]
            dlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s)
            self.move_dlg(dlg)
            dlg.ShowModal()

        self.kill_dlg(dlg)

    def OnRUNAWAY(self, event):
        s = cw.cwpy.msgs["confirm_runaway"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.battle:
                cw.cwpy.exec_func(cw.cwpy.battle.runaway)

        self.kill_dlg(dlg)

    def OnUSECARD(self, event):
        header = cw.cwpy.selectedheader
        owner = header.get_owner()

        if header.allrange and header.target == "Party":
            cw.cwpy.clear_selection()
            targets = cw.cwpy.get_pcards("unreversed")
        else:
            targets = [cw.cwpy.selection]

        cw.cwpy.exec_func(cw.cwpy.clear_curtain)
        cw.cwpy.exec_func(cw.cwpy.set_inusecardimg, owner, header)
        cw.cwpy.exec_func(cw.cwpy.set_targetarrow, targets)
        s = cw.cwpy.msgs["confirm_use_card"] % header.name
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.exec_func(owner.use_card, targets, header)
            cw.cwpy._runningevent = True
        else:
            cw.cwpy.exec_func(cw.cwpy.clear_inusecardimg, owner)
            cw.cwpy.exec_func(cw.cwpy.clear_targetarrow)
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg)

    def OnDATACOMP(self, event):
        ccard = event.args.get("ccard", None)
        dlg = cw.dialog.create.AdventurerDataComp(self, ccard)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnPARTYEDIT(self, event):
        dlg = cw.dialog.edit.PartyEditor(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnBATTLECOMMAND(self, event):
        dlg = cw.dialog.etc.BattleCommand(self)
        # マウスカーソルの位置に行動開始ボタンがくるよう位置調整
        pos = cw.cwpy.mousepos[0] - 316, cw.cwpy.mousepos[1] - 226
        pos = pos[0] + 95, pos[1] + 25
        self.move_dlg(dlg, pos)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnF9(self, event):
        s = (cw.cwpy.msgs["f9_message"])
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.is_showingmessage():
                mwin = cw.cwpy.get_messagewindow()
                mwin.result = cw.event.EffectBreakError()
                cw.cwpy.exec_func(cw.cwpy.sdata.f9)
            else:
                def stop():
                    if cw.cwpy.is_runningevent():
                        # イベント中断
                        cw.cwpy.event.get_event().exit_func = cw.cwpy.sdata.f9
                        raise cw.event.EffectBreakError()
                    else:
                        cw.cwpy.exec_func(cw.cwpy.sdata.f9)
                cw.cwpy.exec_func(stop)

        self.kill_dlg(dlg)

    def OnERROR(self, event):
        text = event.args.get("text", "")
        shutdown = event.args.get("shutdown", False)
        dlg = cw.dialog.message.ErrorMessage(self, text)
        self.move_dlg(dlg)
        dlg.ShowModal()

        if shutdown:
            self.Destroy()
        else:
            self.kill_dlg(dlg)

    def OnMESSAGE(self, event):
        text = event.args.get("text", "")
        parent = event.args.get("parentdialog", None)
        if not parent:
            parent = self
        dlg = cw.dialog.message.Message(parent, cw.cwpy.msgs["message"], text)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnYESNO(self, event):
        text = event.args.get("text", "")
        parent = event.args.get("parentdialog", None)
        if not parent:
            parent = self
        dlg = cw.dialog.message.YesNoMessage(parent, cw.cwpy.msgs["message"], text)
        self.move_dlg(dlg)
        cw.cwpy._yesnoresult = dlg.ShowModal()
        self.kill_dlg(dlg)

    def move_dlg(self, dlg, point=(0, 0)):
        """引数のダイアログをゲーム画面中央に移動させる。
        dlg: wx.Window
        point: 中央以外の位置に移動させたい場合、指定する。
        """
        if hasattr(dlg, "pre_pos") and dlg.pre_pos:
            dlg.SetPosition(dlg.pre_pos)
            return

        if self.IsFullScreen() and dlg.Parent == self:
            x = (cw.SIZE_GAME[0] - dlg.GetSize()[0]) / 2
            y = (cw.SIZE_GAME[1] - dlg.GetSize()[1]) / 2
        else:
            x = (dlg.Parent.GetSize()[0] - dlg.GetSize()[0]) / 2
            y = (dlg.Parent.GetSize()[1] - dlg.GetSize()[1]) / 2
            x += dlg.Parent.GetPosition()[0]
            y += dlg.Parent.GetPosition()[1]

        # pointの数値だけ中央から移動
        x += point[0]
        y += point[1]
        dlg.MoveXY(x, y)

    def kill_dlg(self, dlg=None):
        if dlg:
            parent = dlg.GetParent()
        else:
            parent = None

        dlg.Destroy()
        cw.cwpy.mousepos = (-1, -1)

        if parent is self:
            cw.cwpy._showingdlg = False

    def change_selection(self, selection):
        """選択カードを変更し、色反転させる。
        selection: SelectableSprite
        """
        if selection:
            cw.cwpy.exec_func(cw.cwpy.change_selection, selection)
        else:
            cw.cwpy.exec_func(cw.cwpy.clear_selection)

    def change_cardcontrolarea(self):
        """カード移動操作を行う特殊エリアに移動。"""
        if cw.cwpy.areaid in cw.AREAS_TRADE:
            return
        elif cw.cwpy.status == "Yado":
            func = cw.cwpy.change_specialarea
            cw.cwpy.exec_func(func, -cw.cwpy.areaid)
        elif cw.cwpy.is_playingscenario() and cw.cwpy.areaid == cw.AREA_CAMP:
            cw.cwpy.exec_func(cw.cwpy.change_specialarea, cw.AREA_TRADE3)

    def GetClientPosition(self):
        size = self.GetSize()
        csize = self.GetClientSize()
        pos = self.GetPosition()
        return (size[0] - csize[0]) + pos[0], (size[1] - csize[1]) + pos[1]

class MyApp(wx.App):
    def OnInit(self):
        self.SetAppName(cw.APP_NAME)
        self.SetVendorName("")
        wx.InitAllImageHandlers()
        skincount = get_skincount()
        exe = u""
        if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".exe"):
            exe = sys.argv[1]
        if skincount == 0 or exe:
            # スキンの自動生成
            self.skindlg = cw.dialog.skin.SkinConversionDialog(None, exe)
            self.SetTopWindow(self.skindlg)
            self.skindlg.Bind(wx.EVT_CLOSE, self.OnCloseSkinDialog, self.skindlg)
            self.skindlg.Show()
        else:
            # 通常起動
            frame = Frame()
            self.SetTopWindow(frame)
            frame.Show()
        return True

    def OnCloseSkinDialog(self, event):
        # スキンが1つでもあればそのまま起動する
        self.skindlg.Destroy()
        skincount = get_skincount()

        if 0 < skincount:
            if self.skindlg.select_skin:
                frame = Frame(self.skindlg.skindirname)
            else:
                frame = Frame()
            self.SetTopWindow(frame)
            frame.Show()

def get_skincount():
    skincount = 0
    if os.path.exists(u"Data/Skin"):
        for name in os.listdir(u"Data/Skin"):
            path = cw.util.join_paths(u"Data/Skin", name)
            skinpath = cw.util.join_paths(u"Data/Skin", name, "Skin.xml")
            if os.path.exists(skinpath):
                skincount += 1
    return skincount

def main():
    pass

if __name__ == "__main__":
    main()
