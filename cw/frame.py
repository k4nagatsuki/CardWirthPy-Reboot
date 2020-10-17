#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import shutil
import threading
import wx
import wx.richtext
import pygame
import pygame.locals

import cw
import cw.debug.debugger
from cw.util import synclock

import typing
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

_killlist_mutex = threading.Lock()


class Frame(wx.Frame):
    def __init__(self, app: "MyApp", skindirname: str = "") -> None:
        self.app = app
        self.filter_event = None
        self._clock = 0.0

        # 設定
        self._setting = cw.setting.Setting()
        self._setting.init_settings()
        if self._setting.is_expanded:
            try:
                cw.UP_WIN = float(self._setting.expandmode)
            except Exception:
                cw.UP_WIN = 1.0
            try:
                cw.UP_SCR = float(self._setting.expanddrawing)
            except Exception:
                cw.UP_SCR = 1.0
        else:
            cw.UP_WIN = 1.0
            cw.UP_SCR = 1.0
        cw.UP_WIN_M = cw.UP_WIN

        self.is_iconized = False
        self.kill_list: List[wx.Dialog] = []
        self.db = None

        self._cardholder: Optional[cw.dialog.cardcontrol.SelectCard] = None
        self._handview: Optional[cw.dialog.cardcontrol.HandView] = None
        self._infoview: Optional[cw.dialog.cardcontrol.InfoView] = None
        self._replcardholder: Optional[cw.dialog.cardcontrol.ReplCardHolder] = None

        # トップフレーム
        self.style = wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER
        if sys.platform == "win32":
            wx.Frame.__init__(self, None, -1, cw.APP_NAME, style=self.style)
            self.SetClientSize(cw.wins(cw.SIZE_GAME))

        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        pixels = font.GetPixelSize()[1]
        cw.dpi_level = int(pixels / 12.0 / (1.0 / 72) / 96)

        self.thread = threading.currentThread()
        self._skindirname = skindirname

        def set_bounds() -> None:
            setfullscreensize = False
            if sys.platform != "win32":
                if self._setting.is_expanded and self._setting.expandmode == "FullScreen":
                    setfullscreensize = True
                else:
                    self.SetClientSize(cw.wins(cw.SIZE_GAME))

                if not setfullscreensize:
                    self.SetMinSize(self.GetBestSize())
                    self.SetMaxSize(self.GetBestSize())

            def adjust_position() -> None:
                if not (self._setting.window_position[0] is None and self._setting.window_position[1] is None):
                    pos = self.GetPosition()
                    if not self._setting.window_position[0] is None:
                        pos = (self._setting.window_position[0], pos[1])
                    if not self._setting.window_position[1] is None:
                        pos = (pos[0], self._setting.window_position[1])
                    self.SetPosition(pos)
                    cw.util.adjust_position(self)

            adjust_position()

            if setfullscreensize:
                self.SetClientSize(self.get_displaysize())

            # 拡大後のウィンドウがモニタに収まらない場合は縮小状態に戻す
            d = wx.Display.GetFromWindow(self)
            if d == wx.NOT_FOUND:
                d = 0
            drect = wx.Display(d).GetClientArea()
            wsize = self.GetBestSize()
            if self._setting.is_expanded and (drect[2] < wsize[0] or drect[3] < wsize[1]):
                self._setting.is_expanded = False
                cw.UP_WIN = 1.0
                cw.UP_WIN_M = cw.UP_WIN
                cw.UP_SCR = 1.0
                self.SetClientSize(cw.wins(cw.SIZE_GAME))
                if sys.platform != "win32":
                    self.SetMinSize(self.GetBestSize())
                    self.SetMaxSize(self.GetBestSize())
                self.panel.SetSize(cw.wins(cw.SIZE_GAME))
                adjust_position()

        if sys.platform == "win32":
            self.panel = wx.Panel(self, -1, size=cw.wins(cw.SIZE_GAME), style=wx.NO_BORDER)
            set_bounds()
            self._start_wx()
        else:
            # Xではウィンドウが表示されるまでウィンドウハンドルが取れない
            wx.Frame.__init__(self, None, -1, cw.APP_NAME)
            self.panel = wx.Panel(self, -1, size=cw.wins(cw.SIZE_GAME), style=wx.NO_BORDER)
            self.panel.SetDoubleBuffered(False)
            set_bounds()
            self.Show()
            self._retry_count = 0
            wx.CallLater(100, self._start_wx)

    def _start_wx(self) -> None:
        # SDLを描画するパネル
        if sys.platform != "win32" and not self.panel.GetHandle():
            if self._retry_count < 100:
                self._retry_count += 1
                wx.CallLater(100, self._start_wx)
            else:
                wx.MessageBox("CardWirthPyの起動に失敗しました。\nパネルのハンドルが取得できません。", "エラー - CardWirthPy",
                              style=wx.OK | wx.CENTRE | wx.ICON_ERROR, parent=self)
                self.Destroy()
            return

        os.environ["SDL_WINDOWID"] = str(self.panel.GetHandle())
        if sys.platform == "win32":
            os.environ["SDL_VIDEODRIVER"] = "windib"
#            os.environ["SDL_AUDIODRIVER"] = "waveout"

        # debbuger
        self.debugger = None
        # アイコン
        self.set_icon(self)
        # bind
        self._bind()
        if self._skindirname:
            self._setting.skindirname = self._skindirname
            self._setting.write()
            self._setting.init_settings()
        if self._setting.auto_update_files:
            # アップデートに伴うファイルの整理
            cw.update.update_files("Data", "Data", ["../Scenario/"])
        # 起動直後のスレッド数を記憶
        self.initialThreadCount = 0
        for thr in threading.enumerate():
            if not thr.daemon:
                self.initialThreadCount += 1
        # CWPyサブスレッド
        cw.cwpy.init(self._setting, self)
        cw.cwpy.start()
        # データベースファイル更新をサブスレッドで実行
        folder = self._setting.get_scedir()
        dbupdater = cw.scenariodb.ScenariodbUpdatingThread(self._setting, vacuum=True, dpath=folder,
                                                           skintype=self._setting.skintype)
        dbupdater.start()

        # スキン自動生成のためのドロップ受付
        self.DragAcceptFiles(True)

    def set_icon(self, win: wx.TopLevelWindow) -> None:
        if sys.platform == "win32":
            icon = wx.Icon(sys.executable, wx.BITMAP_TYPE_ICO)
            win.SetIcon(icon)

    def get_displaysize(self) -> wx.Size:
        d = wx.Display.GetFromWindow(self)
        if d == wx.NOT_FOUND:
            d = 0
        return wx.Display(d).GetGeometry().GetSize()

    def update_dialogparams(self) -> None:
        if self._cardholder:
            self._cardholder.Destroy()
            self._cardholder = None
        if self._handview:
            self._handview.Destroy()
            self._handview = None
        if self._infoview:
            self._infoview.Destroy()
            self._infoview = None
        if self._replcardholder:
            self._replcardholder.Destroy()
            self._replcardholder = None

        # レスポンスをよくするため、各ダイアログを事前に生成しておく
        def func(self: Frame) -> None:
            if not cw.cwpy.rsrc:
                return
            rsrc = cw.cwpy.rsrc

            @synclock(cw.thread.init_rsrc)
            def func1(self: Frame) -> None:
                if not self or rsrc is not cw.cwpy.rsrc:
                    return
                if not self._cardholder:
                    self._cardholder = cw.dialog.cardcontrol.SelectCard(self, "CARDPOCKET")
            cw.cwpy.frame.exec_func(func1, self)

            @synclock(cw.thread.init_rsrc)
            def func2(self: Frame) -> None:
                if not self or rsrc is not cw.cwpy.rsrc:
                    return
                if not self._handview:
                    self._handview = cw.dialog.cardcontrol.HandView(self)
            cw.cwpy.frame.exec_func(func2, self)

            @synclock(cw.thread.init_rsrc)
            def func3(self: Frame) -> None:
                if not self or rsrc is not cw.cwpy.rsrc:
                    return
                if not self._infoview:
                    self._infoview = cw.dialog.cardcontrol.InfoView(self)
            cw.cwpy.frame.exec_func(func3, self)

            @synclock(cw.thread.init_rsrc)
            def func4(self: Frame) -> None:
                if not self or rsrc is not cw.cwpy.rsrc:
                    return
                if not self._replcardholder:
                    self._replcardholder = cw.dialog.cardcontrol.ReplCardHolder(self)
            cw.cwpy.frame.exec_func(func4, self)

        cw.cwpy.exec_func(func, self)

    def _bind(self) -> None:
        self.Bind(wx.EVT_CLOSE, self.OnCloseFromFrame)
        self.Bind(wx.EVT_ICONIZE, self.OnIconize)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.Bind(wx.EVT_MOVE, self.OnMove)

        if sys.platform == "win32":
            self.panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
            self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        else:
            # Windowsではこれらのイベントはpygame側で取れる
            self.panel.Bind(wx.EVT_MOTION, self.OnMotion)
            self.panel.Bind(wx.EVT_LEAVE_WINDOW, self.OnMotion)
            self.panel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
            self.panel.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
            self.panel.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUp)
            self.panel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
            self.panel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
            self.panel.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
            self.panel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
            self.panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            self.panel.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

            # BUG: 以降の処理はwxPythonのバグでFrameがフォーカスを
            #      上手く取れない事への対策
            self._keybind = True

            def panel_setfocus(event: wx.FocusEvent) -> None:
                if not self._keybind:
                    self._keybind = True
                    self.panel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
                    self.panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            self.panel.Bind(wx.EVT_SET_FOCUS, panel_setfocus)

            def panel_killfocus(event: wx.FocusEvent) -> None:
                if self._keybind:
                    self._keybind = False
                    self.panel.Unbind(wx.EVT_KEY_UP, handler=self.OnKeyUp)
                    self.panel.Unbind(wx.EVT_KEY_DOWN, handler=self.OnKeyDown)
            self.panel.Bind(wx.EVT_KILL_FOCUS, panel_killfocus)

            def activate(event: wx.ActivateEvent) -> None:
                if not self._keybind:
                    self._keybind = True
                    self.panel.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
                    self.panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
            self.Bind(wx.EVT_ACTIVATE, activate)

        def activate_app(event: wx.ActivateEvent) -> None:
            if not cw.cwpy:
                return
            if not cw.cwpy.sdata:
                return
            if not cw.cwpy.is_running():
                return

            if event.GetActive():
                def func() -> None:
                    if cw.cwpy.sdata:
                        cw.cwpy.sdata.resume_timekeeper()
                cw.cwpy.force_exec_func(func)
            else:
                def func() -> None:
                    if cw.cwpy.sdata:
                        cw.cwpy.sdata.sleep_timekeeper()
                cw.cwpy.force_exec_func(func)

        self.app.Bind(wx.EVT_ACTIVATE_APP, activate_app)

        self._bind_customevent()

    def _bind_customevent(self) -> None:
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
            "PARTYRECORD",  # 編成記録ダイアログ
            "BACKPACK",  # 荷物袋ダイアログ
            "STOREHOUSE",  # カード置場ダイアログ
            "CARDPOCKET",  # プレイヤ所持カードダイアログ
            "CARDPOCKETB",  # プレイヤ所持カードダイアログ(荷物袋から使用)
            "CARDPOCKET_REPLACE",  # プレイヤ所持カードダイアログ(カード交換用)
            "HANDVIEW",  # 戦闘手札カードダイアログ
            "INFOVIEW",  # 情報カードダイアログ
            "CHARAINFO",  # キャラクタ情報ダイアログ
            "RETURNTITLE",  # タイトルに戻るダイアログ
            "SAVE",  # セーブダイアログ
            "SAVED_MESSAGE",  # セーブ完了通知ダイアログ
            "LOAD",  # ロード確認ダイアログ
            "USECARD",   # カード使用ダイアログ
            "RUNAWAY",   # 逃走確認ダイアログ
            "ERROR",  # エラーダイアログ
            "NOTICE",  # 通知ダイアログ
            "MESSAGE",   # メッセージダイアログ
            "YESNO",   # 確認ダイアログ
            "DATACOMP",   # 不足データの補填ダイアログ
            "PARTYEDIT",   # パーティ情報ダイアログ
            "BATTLECOMMAND",  # 行動選択ダイアログ
            "SETTINGS",  # 設定ダイアログ
            "INSTRUCTIONS",  # 添付テキストダイアログ
            "F9",  # 緊急避難ダイアログ
            )
        self.dlgeventtypes = {}

        for eventname in dlgeventnames:
            eventtype = wx.NewEventType()
            event = wx.PyEventBinder(eventtype, 0)
            self.dlgeventtypes[eventname] = eventtype
            self.Bind(event, getattr(self, "On" + eventname))

    def tick_clock(self, framerate: int = 0) -> None:
        if not framerate:
            framerate = cw.cwpy.setting.fps
        t = 1.0 / framerate
        t = max(0, t - (time.time() - self._clock))
        time.sleep(t)
        self._clock = time.time()

    def wait_frame(self, count: int) -> None:
        for _i in range(count):
            self.tick_clock()

    def start_wait(self) -> None:
        self._clock = time.time()

    @synclock(cw.debug.debugger.mutex)
    def show_debugger(self, refreshtree) -> None:
        """デバッガ開く。"""
        if cw.cwpy.is_debugmode() and not self.debugger:
            dlg = cw.debug.debugger.Debugger(self)
            # メインフレームの真横に表示
            dlg.SetSize((cw.ppis(710), self.GetSize()[1]))
            w = dlg.GetSize()[0]
            w -= (w - self.GetSize()[0]) // 2
            w -= 10  # BUG: ウィンドウの位置ずれが発生する。wxPython 4.0.1
            self.move_dlg(dlg, (w, cw.ppis(0)))
            self.debugger = dlg

            if refreshtree:
                dlg.refresh_all()

            def func() -> None:
                cw.cwpy.statusbar.change(cw.cwpy.statusbar.showbuttons)
            cw.cwpy.exec_func(func)
            dlg.Show()

    def close_debugger(self) -> None:
        """デバッガ閉じる。"""
        if self.debugger:
            self.debugger.Close()
            assert self.debugger is None

            def func() -> None:
                cw.cwpy.event.waittime = 0
            cw.cwpy.force_exec_func(func)
            cw.cwpy.exec_func(cw.cwpy.statusbar.change, cw.cwpy.statusbar.showbuttons)

    def exec_func(self, func: Callable[..., None], *args, **kwargs) -> None:
        """wxPythonスレッドで指定したファンクションを実行する。
        func: 実行したいファンクションオブジェクト。
        """
        if not self:
            return
        event = wx.PyCommandEvent(self._EVTTYPE_EXECFUNC)
        event.func = func
        event.args = args
        event.kwargs = kwargs
        self.AddPendingEvent(event)

    def sync_exec(self, func: Callable[..., typing.Any], *args, **kwargs) -> typing.Any:
        """wxPythonスレッドで指定したファンクションを実行し、
        終了を待ち合わせる。ファンクションの戻り値を返す。
        func: 実行したいファンクションオブジェクト。
        """
        if self.thread == threading.currentThread():
            return func(*args, **kwargs)
        else:
            if not self:
                return
            self._sync_result = None
            self._sync_running = True

            def func2(*args, **kwargs) -> None:
                try:
                    self._sync_result = func(*args, **kwargs)
                finally:
                    self._sync_running = False
            event = wx.PyCommandEvent(self._EVTTYPE_EXECFUNC)
            event.func = func2
            event.args = args
            event.kwargs = kwargs
            self.AddPendingEvent(event)
            while cw.cwpy.is_running() and self._sync_running:
                time.sleep(0.001)
            return self._sync_result

    def OnEXECFUNC(self, event: wx.PyCommandEvent) -> None:
        try:
            func = event.func
        except Exception:
            print("failed to execute function on main thread.")
            return

        func(*event.args, **event.kwargs)

    def OnSetFocus(self, event: wx.FocusEvent) -> None:
        """SDL描画パネルがフォーカスされたときに呼ばれ、
        トップフレームにフォーカスを戻す。wx側がキー入力イベントを取得するため、
        ゲーム中は常にトップフレームがフォーカスされていなければならない。
        """
        self.SetFocus()
        self.update_keystate()
        self._update_mousepressed()

    def update_keystate(self) -> None:
        if wx.GetKeyState(wx.WXK_CONTROL):
            if not cw.cwpy.keyevent.is_keyin(pygame.locals.K_LCTRL):
                cw.cwpy.keyevent.keydown(wx.WXK_CONTROL)
        else:
            if cw.cwpy.keyevent.is_keyin(pygame.locals.K_LCTRL):
                cw.cwpy.keyevent.keyup(wx.WXK_CONTROL)

    def _update_mousepressed(self) -> None:
        if sys.platform != "win32":
            if self.IsActive():
                state = wx.GetMouseState()
                ld = state.LeftIsDown()
                m = state.MiddleIsDown()
                r = state.RightIsDown()
                cw.cwpy.mousein = (ld, m, r)
            else:
                cw.cwpy.mousein = (0, 0, 0)

    def OnKillFocus(self, event: wx.FocusEvent) -> None:
        self._update_mousepressed()
        cw.cwpy.keyevent.clear()

    def OnKeyUp(self, event: wx.KeyEvent) -> None:
        keycode = event.GetKeyCode()
        if keycode != wx.WXK_CONTROL:
            self.update_keystate()
        if keycode == ord('P') and event.ControlDown():
            keycode = wx.WXK_SNAPSHOT
        cw.cwpy.keyevent.keyup(keycode)

    def OnKeyDown(self, event: wx.KeyEvent) -> None:
        keycode = event.GetKeyCode()
        if sys.platform == "win32" and keycode == wx.WXK_F4 and event.AltDown():
            return  # WindowsではAlt+F4はウィンドウを閉じる操作
        if keycode != wx.WXK_CONTROL:
            self.update_keystate()

        if self.debugger:
            # デバッガのメニューのアクセラレータキーに
            # 一致するものがあれば、そのメニューを実行する
            def recurse(menu: wx.Menu, debugger: cw.debug.debugger.Debugger) -> bool:
                for item in menu.GetMenuItems():
                    if not item.IsEnabled():
                        continue
                    sub = item.GetSubMenu()
                    if sub:
                        if recurse(sub, debugger):
                            return True
                        continue
                    accel = item.GetAccel()
                    if not accel:
                        continue
                    if accel.GetKeyCode() == keycode and event.GetModifiers() == accel.GetFlags():
                        e = wx.PyCommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, item.GetId())
                        debugger.ProcessEvent(e)
                        return True
                return False
            bar = self.debugger.GetMenuBar()
            for menu, label in bar.GetMenus():
                if recurse(menu, self.debugger):
                    return

        cw.cwpy.keyevent.keydown(keycode)

    def OnMotion(self, event: wx.MouseEvent) -> None:
        if not (self.IsActive() or (self.debugger and self.debugger.IsActive())):
            pos = (-1, -1)
        else:
            pos = cw.mwin2scr_s((event.GetX()-cw.cwpy.scr_pos[0], event.GetY()-cw.cwpy.scr_pos[1]))
        cw.cwpy.wxmousepos = pos

    def OnLeftUp(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=1)
        cw.thread.post_pygameevent(evt)

    def OnLeftDown(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONDOWN, button=1)
        cw.thread.post_pygameevent(evt)

    def OnMiddleUp(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=2)
        cw.thread.post_pygameevent(evt)

    def OnMiddleDown(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONDOWN, button=2)
        cw.thread.post_pygameevent(evt)

    def OnRightUp(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=3)
        cw.thread.post_pygameevent(evt)

    def OnRightDown(self, event: wx.MouseEvent) -> None:
        self._update_mousepressed()
        evt = pygame.event.Event(pygame.locals.MOUSEBUTTONDOWN, button=3)
        cw.thread.post_pygameevent(evt)

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        self._update_mousepressed()
        if cw.util.get_wheelrotation(event) > 0:
            evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=4)
        else:
            evt = pygame.event.Event(pygame.locals.MOUSEBUTTONUP, button=5)

        cw.thread.post_pygameevent(evt)

    def OnDropFiles(self, event: wx.DropFilesEvent) -> None:
        if cw.cwpy.is_showingdlg():
            return
        paths = event.GetFiles()

        for path in paths:
            # スキンの自動生成
            if path.lower().endswith(".exe"):
                try:
                    dlg = cw.dialog.skin.SkinConversionDialog(self, path)
                    self.move_dlg(dlg)
                    cw.cwpy.add_showingdlg()
                    dlg.ShowModal()
                    if dlg.select_skin:
                        cw.cwpy.exec_func(cw.cwpy.update_skin, dlg.skindirname, switch_skin=True)
                    self.kill_dlg(dlg)
                    break
                except Exception:
                    cw.util.print_ex()
        else:
            # スキンのインストール
            if cw.dialog.skininstall.install_skin(paths, self):
                return

            # シナリオのインストール
            if cw.cwpy.is_decompressing:
                cw.cwpy.play_sound("error")
                return
            db = self.open_scenariodb()
            if not db:
                return
            headers, notscenariofiles = cw.dialog.scenarioinstall.to_scenarioheaders(paths, db,
                                                                                     cw.cwpy.setting.skintype,
                                                                                     link=False)
            if not headers:
                return
            cw.cwpy.play_sound("signal")
            scedir = cw.cwpy.setting.get_scedir()
            dlg = cw.dialog.scenarioinstall.ScenarioInstall(self, db, headers, notscenariofiles,
                                                            cw.cwpy.setting.skintype, scedir)
            self.move_dlg(dlg)
            cw.cwpy.add_showingdlg()
            dlg.ShowModal()
            self.kill_dlg(dlg)

    def OnDestroy(self, event: wx.WindowDestroyEvent) -> None:
        cw.cwpy._running = False

        while True:
            count = 0
            for thr in threading.enumerate():
                if not thr.daemon:
                    count += 1
            if count <= self.initialThreadCount:
                break

        cw.util.t_print()

    def OnIconize(self, event: wx.IconizeEvent) -> None:
        """最小化イベント。最小化したときBGMの音も消す。"""
        self.is_iconized = event.IsIconized()
        if self.is_iconized:
            def func() -> None:
                if not cw.cwpy:
                    return
                if cw.cwpy.sdata:
                    cw.cwpy.sdata.sleep_timekeeper()
                if cw.cwpy.setting.stop_the_world_with_iconized:
                    cw.bassplayer.pause()
                else:
                    for music in cw.cwpy.music:
                        music.set_mastervolume(0)
                    for sound in cw.cwpy.lastsound_scenario:
                        if sound:
                            sound.set_mastervolume(True, 0)
                    if cw.cwpy.lastsound_system:
                        cw.cwpy.lastsound_system.set_mastervolume(False, 0)
            cw.cwpy.force_exec_func(func)
        else:
            def func() -> None:
                if not cw.cwpy:
                    return
                if cw.cwpy.sdata:
                    cw.cwpy.sdata.resume_timekeeper()
                cw.bassplayer.start()
                volume = int(cw.cwpy.setting.vol_master*100)
                for music in cw.cwpy.music:
                    music.set_mastervolume(volume)
                for sound in cw.cwpy.lastsound_scenario:
                    if sound:
                        sound.set_mastervolume(True, volume)
                if cw.cwpy.lastsound_system:
                    cw.cwpy.lastsound_system.set_mastervolume(False, volume)
                cw.cwpy.add_lazydraw(clip=cw.s(pygame.Rect((0, 0), cw.SIZE_GAME)))
            cw.cwpy.force_exec_func(func)
            if self.debugger:
                self.debugger.Iconize(False)

    def OnCloseFromFrame(self, event: wx.CloseEvent) -> None:
        # Escapeキー以外で閉じようとした
        if cw.cwpy.ydata and cw.cwpy.ydata.is_changed():
            self.OnCLOSE(event)
        else:
            self.Hide()
            cw.quit_app = True
            if self.debugger:
                self.debugger.Close()
            self.Destroy()

    def OnMove(self, event: wx.MoveEvent) -> None:
        # ウィンドウの移動またはサイズ変更(フルスクリーン化等)
        if not self.IsFullScreen() and not self.IsMaximized():
            if cw.cwpy and cw.cwpy.setting:
                cw.cwpy.setting.window_position = self.GetPosition()

    def OnCLOSE(self, event: wx.CloseEvent) -> None:
        while cw.cwpy.is_processing and not cw.cwpy.is_decompressing:
            pass

        if (cw.cwpy.setting.caution_beforesaving and cw.cwpy.ydata and cw.cwpy.ydata.is_changed()) or\
                cw.cwpy.is_runningevent():
            if cw.cwpy.ydata and cw.cwpy.ydata.is_changed():
                s = cw.cwpy.msgs["confirm_quit_changed"]
            else:
                s = cw.cwpy.msgs["confirm_quit"]
            dlg: Optional[wx.Dialog] = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            assert dlg
            self.move_dlg(dlg)
            result = dlg.ShowModal()
        else:
            result = wx.ID_OK
            dlg = None

        self.kill_dlg(dlg)
        if result == wx.ID_OK:
            self.Hide()
            cw.quit_app = True
            if self.debugger:
                self.debugger.Close()
            self.Destroy()

    def OnSETTINGS(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.settings.SettingsDialog(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnMENUCARDINFO(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.cardinfo.MenuCardInfo(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnYADOSELECT(self, event: wx.PyCommandEvent) -> None:
        if not cw.cwpy.rsrc:
            return
        dlg = cw.dialog.select.YadoSelect(self)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            yadodir = dlg.list[dlg.index]
            try:
                cw.cwpy.load_yado(yadodir)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                cw.cwpy.play_sound("error")
                return

        self.kill_dlg(dlg)

    def OnPARTYSELECT(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.select.PartySelect(self)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            header = dlg.list[dlg.index]
            sceheader = header.get_sceheader()

            # シナリオプレイ途中から再開
            if sceheader:
                def func() -> None:
                    assert cw.cwpy.ydata
                    cw.cwpy.ydata.load_party(header)
                    cw.cwpy.set_scenario(sceheader, resume=True)
                cw.cwpy.exec_func(func)
            # シナリオロードに失敗
            elif header.is_adventuring():
                cw.cwpy.play_sound("error")
                s = (cw.cwpy.msgs["load_scenario_failure"])
                mdlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                self.move_dlg(mdlg)

                if mdlg.ShowModal() == wx.ID_OK:
                    def func() -> None:
                        cw.cwpy.load_party(header, chgarea=False, newparty=False, loadsprites=False)
                        cw.cwpy.sdata.set_log()
                        cw.cwpy.f9(True)
                    cw.cwpy.exec_func(func)

                mdlg.Destroy()
            else:
                cw.cwpy.exec_func(cw.cwpy.load_party, header)

            debugger = cw.cwpy.is_showingdebugger()
            if debugger:
                func = debugger.refresh_tools
                cw.cwpy.frame.exec_func(func)

        self.kill_dlg(dlg)

    def OnPLAYERSELECT(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.select.PlayerSelect(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

        def func() -> None:
            assert cw.cwpy.ydata
            if cw.cwpy.ydata.party:
                areaid = 2
            elif not cw.cwpy.ydata.is_empty() or cw.cwpy.ydata.is_changed():
                areaid = 1
            else:
                areaid = 3

            if areaid != cw.cwpy.areaid:
                if cw.cwpy.ydata.party:
                    cw.cwpy.ydata.party._loading = False
                if cw.cwpy.areaid in (1, 2, 3):
                    cw.cwpy.change_area(areaid)

        cw.cwpy.exec_func(func)

    def open_scenariodb(self) -> Optional[cw.scenariodb.Scenariodb]:
        # Scenariodb更新用のサブスレッドの処理が終わるまで待機
        while not cw.scenariodb.ScenariodbUpdatingThread.is_finished():
            pass

        if not os.path.isdir("Scenario"):
            os.makedirs("Scenario")

        try:
            self.db = cw.scenariodb.Scenariodb()
            return self.db
        except Exception:
            s = ("シナリオデータベースへの接続に失敗しました。\n"
                 "しばらくしてからもう一度やり直してください。")
            self._on_error(s, self, False)
            return None

    def OnSCENARIOSELECT(self, event: wx.PyCommandEvent) -> None:
        db = self.open_scenariodb()
        if not db:
            return

        dlg = cw.dialog.scenarioselect.ScenarioSelect(self, db, cw.cwpy.setting.lastscenario,
                                                      cw.cwpy.setting.lastscenariopath,
                                                      cw.cwpy.setting.lastfindresult)
        self.move_dlg(dlg)

        dlg.ShowModal()

    def ok_scenarioselect(self, dlg: "cw.dialog.scenarioselect.ScenarioSelect") -> None:
        header = dlg.list[dlg.index]
        sel, selpath = dlg.get_selected()
        cw.cwpy.setting.lastscenario, cw.cwpy.setting.lastscenariopath = dlg.get_selected()

        def func(header: cw.header.ScenarioHeader, sel: List[str], selpath: str) -> None:
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            cw.cwpy.selectedscenario = header
            cw.cwpy.ydata.party.set_lastscenario(sel, selpath)
            cw.cwpy.ydata.party.set_numbercoupon()
            cw.cwpy.change_area(4)
        cw.cwpy.exec_func(func, header, sel, selpath)

        # FIXME: linuxでたまに操作不能になる
        #        Windowsでも環境によって落ちる事がある
        #        kill_dlgを遅延させる事で問題を回避する
        # self.kill_dlg(None)
        # self.append_killlist(dlg)

        # wxPython 4.0.1にアップデートしたので様子見
        self.kill_dlg(dlg)

    @synclock(_killlist_mutex)
    def append_killlist(self, dlg: wx.Dialog) -> None:
        if hasattr(dlg, "touchtools"):
            dlg.touchtools.Destroy()
        self.kill_list.append(dlg)

    @synclock(_killlist_mutex)
    def check_killlist(self) -> None:
        assert threading.currentThread() is cw.cwpy
        if self.kill_list and not cw.cwpy.lock_menucards:
            # FIXME: ダイアログの遅延Kill。
            #        一部環境でたまにシナリオ選択後にハングアップするため。
            if not cw.cwpy.is_runningevent() and not cw.cwpy.is_showingdlg():
                def func() -> None:
                    for dlg in self.kill_list:
                        dlg.Destroy()
                    del self.kill_list[:]
                self.exec_func(func)

    def OnALBUM(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.select.Album(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnPARTYRECORD(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.partyrecord.SelectPartyRecord(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnBACKPACK(self, event: wx.PyCommandEvent) -> None:
        selection, preinfo = self._get_cardcontrolparams()
        areaid = self.change_cardcontrolarea()
        if not self._cardholder:
            self._cardholder = cw.dialog.cardcontrol.SelectCard(self, "BACKPACK")
        self._cardholder.reconstruct_cardholder("BACKPACK", selection, preinfo, areaid=areaid)
        self.move_dlg(self._cardholder, (0, cw.ppis(-63)))

        self._cardholder.ShowModal()

    def OnSTOREHOUSE(self, event: wx.PyCommandEvent) -> None:
        selection, preinfo = self._get_cardcontrolparams()
        areaid = self.change_cardcontrolarea()
        if not self._cardholder:
            self._cardholder = cw.dialog.cardcontrol.SelectCard(self, "STOREHOUSE")
        self._cardholder.reconstruct_cardholder("STOREHOUSE", selection, preinfo, areaid=areaid)
        self.move_dlg(self._cardholder, (0, cw.ppis(-63)))

        self._cardholder.ShowModal()

    def OnCARDPOCKETB(self, event: wx.PyCommandEvent) -> None:
        self._cardpocket_impl("CARDPOCKETB")

    def OnCARDPOCKET(self, event: wx.PyCommandEvent) -> None:
        self._cardpocket_impl("CARDPOCKET")

    def _cardpocket_impl(self, callname: str) -> None:
        selection, preinfo = self._get_cardcontrolparams()
        if isinstance(selection, (cw.character.Enemy, cw.character.Friend)):
            areaid = cw.cwpy.areaid
        else:
            areaid = self.change_cardcontrolarea()
        if not self._cardholder:
            self._cardholder = cw.dialog.cardcontrol.SelectCard(self, callname)
        self._cardholder.reconstruct_cardholder(callname, selection, preinfo, areaid=areaid)
        self.move_dlg(self._cardholder, (0, cw.ppis(-63)))

        self._cardholder.ShowModal()

    def OnHANDVIEW(self, event: wx.PyCommandEvent) -> None:
        selection, preinfo = self._get_cardcontrolparams()
        if not self._handview:
            self._handview = cw.dialog.cardcontrol.HandView(self)
        self._handview.reconstruct_handview(selection, preinfo)
        self.move_dlg(self._handview, (0, cw.ppis(-63)))

        self._handview.ShowModal()

    def OnCARDPOCKET_REPLACE(self, event: wx.PyCommandEvent) -> None:
        selection = cw.cwpy.selection
        target = cw.cwpy.selectedheader
        if selection and target:
            personal = event.args.get("personal_cards", None)
            if not self._replcardholder:
                self._replcardholder = cw.dialog.cardcontrol.ReplCardHolder(self)
            self._replcardholder.reconstruct_replcardholder(selection, target, personal=personal)
            self.move_dlg(self._replcardholder, (0, cw.ppis(-63)))
            self._replcardholder.ShowModal()
        else:
            self.kill_dlg(None)

    def _get_cardcontrolparams(self) -> Tuple["cw.sprite.card.CWPyCard",
                                              Optional[Tuple[str, "cw.sprite.card.CWPyCard", Tuple[int, int], float]]]:
        if cw.cwpy.pre_dialogs:
            preinfo: Optional[Tuple[str, cw.sprite.card.CWPyCard, Tuple[int, int], float]] = cw.cwpy.pre_dialogs.pop()
            assert preinfo
            selection = preinfo[1]
        else:
            assert cw.cwpy.selection
            selection = cw.cwpy.selection
            preinfo = None
        return selection, preinfo

    def OnINFOVIEW(self, event: wx.PyCommandEvent) -> None:
        def func() -> None:
            if cw.cwpy.sdata.notice_infoview:
                cw.cwpy.sdata.notice_infoview = False
                cw.cwpy.statusbar.change()
        cw.cwpy.exec_func(func)

        if not self._infoview:
            self._infoview = cw.dialog.cardcontrol.InfoView(self)
        self._infoview.reconstruct_infoview()
        self.move_dlg(self._infoview, (0, cw.ppis(-63)))
        self._infoview.ShowModal()

    def OnCHARAINFO(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.charainfo.ActiveCharaInfo(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnRETURNTITLE(self, event: wx.PyCommandEvent) -> None:
        if cw.cwpy.setting.caution_beforesaving and cw.cwpy.ydata and cw.cwpy.ydata.is_changed():
            s = (cw.cwpy.msgs["confirm_go_title"])
            dlg: Optional[wx.Dialog] = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            assert dlg
            self.move_dlg(dlg)
            result = dlg.ShowModal()
        else:
            dlg = None
            result = wx.ID_OK

        if result == wx.ID_OK:
            cw.cwpy.exec_func(cw.cwpy.set_title)

        self.kill_dlg(dlg)

    def OnSAVE(self, event: wx.PyCommandEvent) -> None:
        is_playingscenario = cw.cwpy.is_playingscenario()

        if (cw.cwpy.setting.confirm_beforesaving == cw.setting.CONFIRM_BEFORESAVING_BASE and
            not is_playingscenario) or\
                cw.cwpy.setting.confirm_beforesaving not in (cw.setting.CONFIRM_BEFORESAVING_NO,
                                                             cw.setting.CONFIRM_BEFORESAVING_BASE):
            s = cw.cwpy.msgs["confirm_save"]
            dlg: Optional[wx.Dialog] = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            assert dlg
            self.move_dlg(dlg)
            save = (dlg.ShowModal() == wx.ID_OK)
        else:
            dlg = None
            save = True

        if save:
            self.kill_dlg(dlg, lockmenucard=True)

            def func() -> None:
                assert cw.cwpy.ydata
                cw.cwpy.ydata.save()
                cw.cwpy.play_sound("signal")
                if cw.cwpy.setting.show_savedmessage:
                    s = cw.cwpy.msgs["saved"]
                    cw.cwpy.call_modaldlg("SAVED_MESSAGE", text=s)
                else:
                    self._saved()
            cw.cwpy.exec_func(func)
        else:
            self.kill_dlg(dlg)

    def OnSAVED_MESSAGE(self, event: wx.PyCommandEvent) -> None:
        self.OnMESSAGE(event)

        def func() -> None:
            self._saved()
        cw.cwpy.exec_func(func)

    def _saved(self) -> None:
        if cw.cwpy.is_playingscenario():
            return
        assert cw.cwpy.ydata

        if cw.cwpy.ydata.party:
            areaid = 2
        elif not cw.cwpy.ydata.is_empty() or cw.cwpy.ydata.is_changed():
            areaid = 1
        else:
            areaid = 3

        if areaid != cw.cwpy.areaid:
            if cw.cwpy.ydata.party:
                cw.cwpy.ydata.party._loading = False
            cw.cwpy.change_area(areaid)

    def OnLOAD(self, event: wx.PyCommandEvent) -> None:
        s = cw.cwpy.msgs["confirm_load"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.exec_func(cw.cwpy.reload_yado)
        self.kill_dlg(dlg)

    def OnRUNAWAY(self, event: wx.PyCommandEvent) -> None:
        s = cw.cwpy.msgs["confirm_runaway"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.battle:
                cw.cwpy.exec_func(cw.cwpy.battle.runaway)

        self.kill_dlg(dlg, redraw=False)

    def OnUSECARD(self, event: wx.PyCommandEvent) -> None:
        header = cw.cwpy.selectedheader
        assert header
        owner = header.get_owner()
        assert isinstance(owner, (cw.sprite.card.PlayerCard, cw.sprite.card.EnemyCard, cw.sprite.card.FriendCard))

        if header.allrange and (header.target == "Party" or header.target == "Both") and\
                isinstance(cw.cwpy.selection, cw.sprite.card.PlayerCard):
            # 味方全員が対象
            cw.cwpy.clear_selection()
            targets = cw.cwpy.get_pcards("unreversed")
        elif header.target == "User":
            targets = [owner]
        elif header.target == "None":
            targets = []
        else:
            assert isinstance(cw.cwpy.selection, cw.sprite.card.CWPyCard)
            targets = [cw.cwpy.selection]

        cw.cwpy.exec_func(cw.cwpy.clear_curtain)

        def func(owner: Union[cw.sprite.card.PlayerCard, cw.sprite.card.EnemyCard, cw.sprite.card.FriendCard],
                 header: cw.header.CardHeader, targets: Iterable[cw.sprite.card.CWPyCard]) -> None:
            alpha = cw.cwpy.setting.get_inusecardalpha(owner)
            cw.cwpy.set_inusecardimg(owner, header, alpha=alpha, fore=True)
            if not cw.cwpy.setting.confirm_beforeusingcard or header.target == "None":
                cw.cwpy.clear_targetarrow()
            else:
                cw.cwpy.set_targetarrow(targets)

        if cw.cwpy.setting.confirm_beforeusingcard:
            cw.cwpy.exec_func(func, owner, header, targets)
            s = cw.cwpy.msgs["confirm_use_card"] % header.name
            dlg: Optional[wx.Dialog] = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            assert dlg
            self.move_dlg(dlg)
            use = (dlg.ShowModal() == wx.ID_OK)
        else:
            dlg = None
            use = True

        if use:
            cw.cwpy.exec_func(owner.use_card, targets, header)
        else:
            cw.cwpy.exec_func(cw.cwpy.clear_inusecardimg, owner)
            cw.cwpy.exec_func(cw.cwpy.clear_targetarrow)
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea)

        self.kill_dlg(dlg, lockmenucard=True)

    def OnDATACOMP(self, event: wx.PyCommandEvent) -> None:
        ccard = event.args.get("ccard", None)
        dlg = cw.dialog.create.AdventurerDataComp(self, ccard)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnPARTYEDIT(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.edit.PartyEditor(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnBATTLECOMMAND(self, event: wx.PyCommandEvent) -> None:
        dlg = cw.dialog.etc.BattleCommand(self)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnINSTRUCTIONS(self, event: wx.PyCommandEvent) -> None:
        seq = []
        sdata = cw.cwpy.ydata.losted_sdata if cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata else cw.cwpy.sdata
        for fpath in sdata.instructions:
            with open(fpath, "rb") as f:
                content = f.read()
                f.close()
            fname = os.path.basename(fpath)
            seq.append(cw.dialog.text.ReadmeData(fname, content))

        cw.cwpy.play_sound("click")
        dlg = cw.dialog.text.Readme(self, cw.cwpy.msgs["description"], seq)
        self.move_dlg(dlg)
        dlg.ShowModal()
        self.kill_dlg(dlg)

    def OnF9(self, event: wx.PyCommandEvent) -> None:
        s = (cw.cwpy.msgs["f9_message"])
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            def func() -> None:
                if cw.cwpy.is_decompressing:
                    if cw.cwpy.is_playingscenario():
                        # リロード中
                        cw.cwpy.exec_func(func)
                    raise cw.event.EffectBreakError()

                if cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata:
                    cw.cwpy.sdata = cw.cwpy.ydata.losted_sdata
                    cw.cwpy.ydata.losted_sdata = None
                assert isinstance(cw.cwpy.sdata, cw.data.ScenarioData)
                cw.cwpy.sdata.in_f9 = True
                if cw.cwpy.pre_dialogs:
                    cw.cwpy.pre_dialogs.pop()

                if cw.cwpy.is_showingmessage():
                    mwin = cw.cwpy.get_messagewindow()
                    assert mwin
                    mwin.result = cw.event.EffectBreakError()
                    cw.cwpy.exec_func(cw.cwpy.sdata.f9)
                else:
                    def stop() -> None:
                        assert isinstance(cw.cwpy.sdata, cw.data.ScenarioData)
                        if cw.cwpy.is_runningevent() and cw.cwpy.event.get_event():
                            # イベント中断
                            cw.cwpy.event.exit_func = cw.cwpy.sdata.f9
                            raise cw.event.EffectBreakError()
                        else:
                            cw.cwpy.exec_func(cw.cwpy.sdata.f9)
                    cw.cwpy.exec_func(stop)
            cw.cwpy.exec_func(func)

        self.kill_dlg(dlg)

    def OnERROR(self, event: wx.PyCommandEvent) -> None:
        text: str = event.args.get("text", "")
        parent: Optional[wx.TopLevelWindow] = event.args.get("parentdialog", self)
        shutdown: bool = event.args.get("shutdown", False)
        self._on_error(text, parent, shutdown)

    def _on_error(self, text: str, parent: Optional[wx.TopLevelWindow], shutdown: bool) -> None:
        if not parent:
            parent = self
        dlg = cw.dialog.message.ErrorMessage(parent, text)
        self.move_dlg(dlg)
        dlg.ShowModal()
        if hasattr(parent, "after_message"):
            parent.after_message()

        if shutdown:
            cw.quit_app = True
            if self.debugger:
                self.debugger.Close()
            self.Destroy()
        else:
            self.kill_dlg(dlg)

    def OnNOTICE(self, event: wx.PyCommandEvent) -> None:
        cw.cwpy.play_sound("error")
        if cw.cwpy.setting.noticeimpossibleaction:
            text = event.args.get("text", "")
            parent = event.args.get("parentdialog", self)
            if not parent:
                parent = self
            dlg: Optional[wx.Dialog] = cw.dialog.message.Message(parent, cw.cwpy.msgs["message"], text)
            assert dlg
            self.move_dlg(dlg)
            dlg.ShowModal()
            if hasattr(parent, "after_message"):
                parent.after_message()
        else:
            dlg = None

        self.kill_dlg(dlg)

    def OnMESSAGE(self, event: wx.PyCommandEvent) -> None:
        text = event.args.get("text", "")
        parent = event.args.get("parentdialog", self)
        if not parent:
            parent = self
        dlg = cw.dialog.message.Message(parent, cw.cwpy.msgs["message"], text)
        self.move_dlg(dlg)
        dlg.ShowModal()
        if hasattr(parent, "after_message"):
            parent.after_message()
        self.kill_dlg(dlg)

    def OnYESNO(self, event: wx.PyCommandEvent) -> None:
        text = event.args.get("text", "")
        parent = event.args.get("parentdialog", self)
        if not parent:
            parent = self
        dlg = cw.dialog.message.YesNoMessage(parent, cw.cwpy.msgs["message"], text)
        self.move_dlg(dlg)
        cw.cwpy._yesnoresult = dlg.ShowModal()
        if hasattr(parent, "after_message"):
            parent.after_message()
        self.kill_dlg(dlg)

    def move_dlg(self, dlg: wx.Dialog, point: Tuple[int, int] = (0, 0)) -> None:
        """引数のダイアログをゲーム画面中央に移動させる。
        dlg: wx.Window
        point: 中央以外の位置に移動させたい場合、指定する。
        """
        if sys.platform == "win32" and self.IsIconized():
            self.Iconize(False)

        if hasattr(dlg, "pre_pos") and dlg.pre_pos:
            dlg.SetPosition(dlg.pre_pos)

        else:
            if self.IsFullScreen() and dlg.Parent == self:
                d = wx.Display.GetFromWindow(self)
                if d == wx.NOT_FOUND:
                    d = 0
                carea = wx.Display(d).GetGeometry()
                x = carea[0] + (carea[2] - dlg.GetSize()[0]) // 2
                y = carea[1] + (carea[3] - dlg.GetSize()[1]) // 2
            else:
                x = (dlg.Parent.GetSize()[0] - dlg.GetSize()[0]) // 2
                y = (dlg.Parent.GetSize()[1] - dlg.GetSize()[1]) // 2
                x += dlg.Parent.GetPosition()[0]
                y += dlg.Parent.GetPosition()[1]

            # pointの数値だけ中央から移動
            x += int(point[0] * cw.cwpy.scr_scale)
            y += int(point[1] * cw.cwpy.scr_scale)

            dlg.SetPosition((x, y))

        # モニタ内に収める
        cw.util.adjust_position(dlg)
        cw.dialog.etc.show_touchtools(dlg)

        def OnIconize(event: wx.IconizeEvent) -> None:
            self.Iconize(event.IsIconized())
            event.Skip(False)
        dlg.Bind(wx.EVT_ICONIZE, OnIconize)

    def kill_dlg(self, dlg: Optional[wx.Dialog] = None, lockmenucard: bool = False, redraw: bool = True) -> None:
        if dlg:
            dlg.Destroy()

        def func(lockmenucard: bool, redraw: bool) -> None:
            # (-1, -1)にすると次のマウス移動判定で
            # cw.cwpy.mousemotionがFalseになるため、
            # 異なる値を設定する
            cw.cwpy.mousepos = (-2, -2)
            if redraw and not cw.cwpy.is_updating_skin:
                cw.cwpy.add_lazydraw(clip=cw.s(pygame.Rect((0, 0), cw.SIZE_GAME)))
            if not lockmenucard:
                cw.cwpy.lock_menucards = False
        cw.cwpy.kill_showingdlg()

        # キーやマウスボタンの押下状態をpygame側へ伝える
        if wx.GetKeyState(wx.WXK_RETURN):
            cw.cwpy.keyevent.nokeyupevent = True
        state = wx.GetMouseState()
        if state.LeftIsDown():
            cw.cwpy.keyevent.mouse_buttondown[0] = True
        if state.MiddleIsDown():
            cw.cwpy.keyevent.mouse_buttondown[1] = True
        if state.RightIsDown():
            cw.cwpy.keyevent.mouse_buttondown[2] = True

        cw.cwpy.exec_func(func, lockmenucard, redraw)

    def can_screenshot(self) -> bool:
        """スクリーンショットの撮影が可能か。
        """
        if not cw.cwpy.is_showingdlg():
            return True

        fc = wx.Window.FindFocus()
        while fc and fc.GetTopLevelParent():
            top = fc.GetTopLevelParent()
            if hasattr(top, "cwpy_debug") and top.cwpy_debug:
                return False
            fc = fc.GetParent()
        return True

    def find_activedialog(self) -> Optional[wx.Dialog]:
        if cw.cwpy.is_showingdlg():
            return wx.GetActiveWindow()
        else:
            return None

    def save_screenshot(self) -> bool:
        """スクリーンショットを撮影する。
        """
        if cw.cwpy.is_showingdlg():
            fc = wx.Window.FindFocus()
            while fc and fc.GetTopLevelParent():
                top = fc.GetTopLevelParent()
                if hasattr(top, "cwpy_debug") and top.cwpy_debug:
                    return False
                fc = fc.GetParent()

            # ダイアログを表示中の場合
            def func(self: Frame) -> None:
                cw.cwpy.play_sound("screenshot")
                titledic = cw.cwpy.get_titledic(with_datetime=True, for_fname=True)
                assert isinstance(titledic, tuple)
                image, y = cw.util.create_screenshot(titledic[0])
                w, h = image.get_size()
                if (image.get_flags() & pygame.locals.SRCALPHA) or image.get_colorkey() or sys.platform != "win32":
                    # linuxでは画像が壊れるので常にこちら
                    buf = pygame.image.tostring(image, "RGBA")
                    alpha = True
                    colorkey = None
                else:
                    buf = pygame.image.tostring(image, "RGB")
                    alpha = False

                    if image.get_colorkey():
                        colorkey = image.get_colorkey()
                    else:
                        colorkey = None

                def func(w: int, h: int, alpha: bool, buf: bytes, colorkey: Tuple[int, int, int, int],
                         titledicfn: Dict[str, str], y: int, fore: Tuple[int, int, int],
                         back: Tuple[int, int, int]) -> None:
                    if alpha:
                        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)
                    else:
                        bmp = wx.Bitmap.FromBuffer(w, h, buf)
                    self._put_dlgscreenshots(bmp, y, fore, back)
                    if colorkey:
                        r, g, b, a = colorkey
                        bmp.SetMaskColour(wx.Colour(r, g, b))
                    filename = cw.util.create_screenshotfilename(titledicfn)
                    try:
                        dpath = os.path.dirname(filename)
                        if os.path.isdir(dpath):
                            fpath = cw.util.dupcheck_plus(filename, yado=False)
                        else:
                            os.makedirs(dpath)
                        bmp.SaveFile(filename, wx.BITMAP_TYPE_PNG)
                    except Exception:
                        cw.util.print_ex()
                        s = "スクリーンショットの保存に失敗しました。\n%s" % (filename)
                        cw.cwpy.call_modaldlg("ERROR", text=s)

                fore = cw.cwpy.setting.ssinfofontcolor
                back = cw.cwpy.setting.ssinfobackcolor
                self.exec_func(func, w, h, alpha, buf, colorkey, titledic[1], y, fore, back)

            cw.cwpy.exec_func(func, self)
            return True
        else:
            # ダイアログを表示中でない場合は
            # pygame側のイベントハンドラに任せる
            return False

    def _put_dlgscreenshots(self, bmp: wx.Bitmap, y: int, fore: Tuple[int, int, int],
                            back: Tuple[int, int, int]) -> None:
        w, h = bmp.GetSize()
        mem = wx.MemoryDC(bmp)
        h -= y
        # タイトルバー以外の領域に描画する
        mem.SetClippingRegion(0, y, w, h)
        mem.SetBrush(wx.Brush(back))
        mem.SetPen(wx.Pen(back))
        frect = self.GetRect()

        def recurse(win: wx.TopLevelWindow) -> None:
            for child in win.GetChildren():
                if not child.IsShown():
                    continue
                if not hasattr(child, "cwpy_debug"):
                    continue
                if child.IsTopLevel() and not child.IsIconized() and\
                        not child.cwpy_debug and not isinstance(child, cw.dialog.etc.TouchTools):
                    # ダイアログを描画
                    dc = wx.ClientDC(child)
                    rect = child.GetClientRect()
                    ww = rect[2]
                    wh = rect[3]
                    bmp = cw.util.empty_bitmap(ww, wh)
                    mem2 = wx.MemoryDC(bmp)
                    mem2.Blit(0, 0, ww, wh, dc, 0, 0)
                    del dc
                    mem2.SelectObject(wx.NullBitmap)
                    del mem2

                    # サイズを適正に変換
                    img = cw.util.convert_to_image(bmp)
                    img = cw.mwin2scr_s(img)
                    bmp = img.ConvertToBitmap()

                    # 位置を調節
                    crect = child.GetRect()
                    crect.X -= frect.X
                    crect.Y -= frect.Y
                    centerx = (crect.X + crect.Width / 2.0) / frect.Width
                    centery = (crect.Y + crect.Height / 2.0) / frect.Height

                    # 全体スクリーンショットへ描画
                    pixelsize = int(cw.cwpy.setting.fonttypes["screenshot"][2] * 0.8)
                    font = cw.cwpy.rsrc.get_wxfont("screenshot", pixelsize=cw.s(pixelsize)*2, adjustsizewx3=False)
                    mem.SetFont(font)
                    title = child.GetTitle()
                    white = fore[:3] == (255, 255, 255)
                    quality = wx.IMAGE_QUALITY_HIGH

                    # 位置の決定(画面外には出さない)
                    ww, wh = bmp.GetSize()
                    wh += cw.s(pixelsize+2) + 2
                    xx = (w * centerx) - (ww // 2)
                    yy = (h * centery) - (wh // 2) + y
                    if w <= xx + (ww+2):
                        xx = w - (ww+2)
                    if h <= yy+y + (wh+2):
                        yy = h+y - (wh+2)
                    if xx < 2:
                        xx = 2
                    if yy < 2+y:
                        yy = 2+y

                    rx, ry, rw, rh = xx - 2, yy - 2, ww + 4, bmp.GetHeight() + 4 + cw.s(pixelsize + 2) + 2
                    mem.DrawRectangle(rx, ry, rw, rh)
                    mem.SetClippingRegion(rx, ry, rw, rh)
                    if cw.cwpy.setting.ssinfobackimage and os.path.isfile(cw.cwpy.setting.ssinfobackimage):
                        backimage = cw.util.load_wxbmp(cw.cwpy.setting.ssinfobackimage, False)
                        cw.util.fill_bitmap(mem, cw.s(backimage), csize=(rw, rh), cpos=(rx, ry))
                    else:
                        fpath = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir,
                                                                         "Resource/Image/Other/SCREENSHOT_HEADER"),
                                                      cw.M_IMG)
                        if fpath:
                            backimage = cw.util.load_wxbmp(fpath, False)
                            cw.util.fill_bitmap(mem, cw.s(backimage), csize=(rw, rh), cpos=(rx, ry))
                    mem.DestroyClippingRegion()
                    mem.DrawBitmap(bmp, xx, yy + cw.s(pixelsize + 2) + 2, False)

                    cw.util.draw_antialiasedtext(mem, title, int(xx + cw.s(5)), int(yy + 1),
                                                 white, ww, cw.s(5),
                                                 quality=quality, bordering=True, alpha=80)
                    recurse(child)
        recurse(self)
        mem.SelectObject(wx.NullBitmap)

    def change_selection(self, selection: Optional["cw.sprite.card.CWPyCard"]) -> None:
        """選択カードを変更し、色反転させる。
        selection: SelectableSprite
        """
        if selection:
            cw.cwpy.exec_func(cw.cwpy.change_selection, selection)
        else:
            cw.cwpy.exec_func(cw.cwpy.clear_selection)

    def change_cardcontrolarea(self) -> int:
        """カード移動操作を行う特殊エリアに移動。"""
        if cw.cwpy.areaid in cw.AREAS_TRADE:
            return cw.cwpy.areaid
        elif cw.cwpy.status == "Yado":
            def func(areaid: int) -> None:
                def func(areaid: int) -> None:
                    cw.cwpy.change_specialarea(areaid)
                    cw.cwpy.statusbar.change()
                cw.cwpy.exec_func(func, areaid)
            assert cw.cwpy.ydata
            areaid = cw.AREA_TRADE2 if cw.cwpy.ydata.party else cw.AREA_TRADE1
            cw.cwpy.frame.exec_func(func, areaid)
            return areaid
        elif cw.cwpy.is_playingscenario() and cw.cwpy.areaid == cw.AREA_CAMP:
            def func2() -> None:
                def func() -> None:
                    cw.cwpy.change_specialarea(cw.AREA_TRADE3)
                    cw.cwpy.statusbar.change()
                cw.cwpy.exec_func(func)
            cw.cwpy.frame.exec_func(func2)
            return cw.AREA_TRADE3
        return cw.cwpy.areaid

    def GetClientPosition(self) -> Tuple[int, int]:
        size = self.GetSize()
        csize = self.GetClientSize()
        pos = self.GetPosition()
        return (size[0] - csize[0]) + pos[0], (size[1] - csize[1]) + pos[1]


FLICK_NONE = 0
FLICK_START = 1


class NoFlick(object):
    pass


class MyApp(wx.App):

    def __init__(self) -> None:
        wx.App.__init__(self, 0)
        self.flick_status = FLICK_NONE
        self.flick_window = None
        self.flick_start_pos = (-1, -1)
        self.flick_start_time = 0.0

    def OnInit(self) -> bool:
        wx.Log.SetLogLevel(wx.LOG_Error)
        self.SetAppName(cw.APP_NAME)
        self.SetVendorName("")
        skincount = get_skincount()[0]
        exe = ""
        if len(cw.SKIN_CONV_ARGS) > 0 and cw.SKIN_CONV_ARGS[0].lower().endswith(".exe"):
            exe = cw.SKIN_CONV_ARGS[0]
        if skincount == 0 or exe:
            # スキンの自動生成
            try:
                facenames = set(wx.FontEnumerator().GetFacenames())
                fontpaths = cw.setting.Resource.get_fontpaths_s("Data/Font", facenames)
                cw.setting.Resource.install_defaultfonts(fontpaths, facenames, {})
                self.skindlg = cw.dialog.skin.SkinConversionDialog(None, exe)
                self.SetTopWindow(self.skindlg)
                self.skindlg.Bind(wx.EVT_CLOSE, self.OnCloseSkinDialog, self.skindlg)
                self.skindlg.Show()
            except cw.setting.NoFontError as ex:
                s = ("CardWirthPyの実行に必要なフォントがありません。\n"
                     "Data/Font以下にIPAフォントをインストールしてください。")
                wx.MessageBox(s, "メッセージ", wx.OK | wx.ICON_ERROR, None)
            except Exception:
                cw.util.print_ex()
        else:
            # 通常起動
            frame = Frame(self)
            self.SetTopWindow(frame)
            frame.Show()
        return True

    def OnCloseSkinDialog(self, event: wx.CloseEvent) -> None:
        # スキンが1つでもあればそのまま起動する
        self.skindlg.Destroy()
        skincount = get_skincount()[0]

        if 0 < skincount:
            if self.skindlg.select_skin:
                frame = Frame(self, self.skindlg.skindirname)
            else:
                frame = Frame(self)
            self.SetTopWindow(frame)
            frame.Show()

    def FilterEvent(self, event: wx.Event) -> int:
        if not event:
            return -1

        # BUG: wx._core.PyAssertionError: C++ assertion "GetEventHandler() == this"
        #      failed at ..\..\src\common\wincmn.cpp(478) in wxWindowBase::~wxWindowBase():
        #      any pushed event handlers must have been removed
        #      wxPython 3.0.2.0
        try:
            event.GetEventObject()

            if cw.cwpy and not cw.cwpy.is_runningstatus():
                return -1

            if not (cw.cwpy and cw.cwpy.frame):
                return -1
        except Exception:
            cw.util.print_ex()
            return -1

        if cw.cwpy.frame.filter_event:
            if not event.GetEventObject():
                return -1

            if cw.cwpy.frame.filter_event(event):
                return True

        if not cw.cwpy.is_showingdlg():
            return -1

        if sys.platform != "win32" and isinstance(event, wx.UpdateUIEvent):
            touchtools = event.GetEventObject()
            if isinstance(touchtools, cw.dialog.etc.TouchTools):
                if touchtools.on_motion():
                    return True
            return -1

        if not isinstance(event, (wx.KeyEvent, wx.MouseEvent)):
            return -1

        if not event.GetEventObject():
            return -1

        # ダイアログ上でのフリック操作
        # フリック開始位置で右クリックを発生させる
        if cw.cwpy and cw.cwpy.setting.enabled_right_flick and isinstance(event, wx.MouseEvent):

            def end_flick() -> int:
                mousepos = wx.GetMousePosition()
                xmove = cw.ppis(mousepos[0] - self.flick_start_pos[0])
                ymove = cw.ppis(mousepos[1] - self.flick_start_pos[1])
                dur = time.process_time() - self.flick_start_time
                exit_value = -1
                if self.flick_window and self.flick_window.IsShown() and self.flick_window.IsEnabled() and\
                        cw.ppis(cw.cwpy.setting.flick_distance) <= xmove and\
                        dur <= cw.cwpy.setting.flick_time_msec/1000.0:
                    event2 = wx.PyCommandEvent(wx.wxEVT_RIGHT_UP, wx.ID_UP)
                    event2.GetPosition = lambda: self.flick_window.ScreenToClient(self.flick_start_pos)
                    self.flick_window.ProcessEvent(event2)
                    exit_value = True

                self.flick_status = FLICK_NONE
                self.flick_window = None
                self.flick_start_pos = (-1, -1)
                self.flick_start_time = 0.0
                return exit_value

            if event.GetEventType() == wx.EVT_LEFT_DOWN.typeId:
                window = event.GetEventObject()
                if isinstance(window, wx.Window):
                    if isinstance(window, (NoFlick, wx.Slider, wx.TextCtrl, wx.richtext.RichTextCtrl)):
                        return -1
                    self.flick_status = FLICK_START
                    self.flick_window = window
                    self.flick_start_pos = wx.GetMousePosition()
                    self.flick_start_time = time.process_time()

                    # 画面外にマウスポインタが出ていった時に
                    # マウスボタンアップを検知できないので
                    # 1フレームごとにマウスボタンの状態を確認し、
                    # フリック中かつボタンが押されていなければ
                    # フリックイベントを発生させる。
                    def watch_mousebutton() -> None:
                        if self.flick_status != FLICK_START:
                            return
                        dur = time.process_time() - self.flick_start_time
                        if cw.cwpy.setting.flick_time_msec / 1000.0 <= dur:
                            return
                        if not wx.GetMouseState().LeftIsDown():
                            end_flick()
                        else:
                            wx.CallLater(cw.cwpy.setting.frametime, watch_mousebutton)
                    wx.CallLater(cw.cwpy.setting.frametime, watch_mousebutton)

            elif self.flick_status == FLICK_START and event.GetEventType() == wx.EVT_LEFT_UP.typeId:
                return end_flick()

        if cw.cwpy and cw.cwpy.setting.enabled_right_flick and isinstance(event, wx.MouseEvent):
            if self.flick_status == FLICK_START and event.GetEventType() == wx.EVT_MOTION.typeId:
                # フリックの制限時間が経過済みでない場合はポインタ移動イベントをキャンセルする
                dur = time.process_time() - self.flick_start_time
                if dur < cw.cwpy.setting.flick_time_msec/1000.0:
                    return True

        # スクリーンショットの撮影
        if isinstance(event, wx.KeyEvent) and\
                event.GetEventType() == wx.EVT_KEY_UP.typeId:
            if (wx.WXK_SNAPSHOT == event.GetKeyCode() or
                (ord('P') == event.GetKeyCode() and event.ControlDown())) and\
                 cw.cwpy.frame.can_screenshot():
                if event.ShiftDown():
                    cw.cwpy.force_exec_func(cw.util.card_screenshot)
                else:
                    cw.cwpy.frame.save_screenshot()
                event.Skip()
                return True
            if ord('D') == event.GetKeyCode() and event.ControlDown():
                def func(updatedebug_on_dlg: bool) -> None:
                    if updatedebug_on_dlg:
                        cw.cwpy.play_sound("page")
                        cw.cwpy.set_debug(not cw.cwpy.is_debugmode())
                    elif not cw.cwpy.is_showingdlg():
                        cw.cwpy.set_debug(not cw.cwpy.is_debugmode())
                dlg = cw.cwpy.frame.find_activedialog()
                updatedebug_on_dlg = dlg and not hasattr(dlg, "update_debug")
                cw.cwpy.force_exec_func(func, updatedebug_on_dlg)
                event.Skip()
                return True
        return -1


def get_skincount() -> Tuple[int, int]:
    skincount = 0
    unknown_ver = 0
    if os.path.isdir("Data/Skin"):
        for name in os.listdir("Data/Skin"):
            skinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml")
            if os.path.isfile(skinpath):
                prop = cw.header.GetProperty(skinpath)
                skinversion = prop.attrs.get(None, {}).get("dataVersion", "0")
                if skinversion in cw.SUPPORTED_SKIN:
                    skincount += 1
                else:
                    unknown_ver += 1
            else:
                # FIXME: 消せなかったスキンの削除。
                #        cw.dialog.skininstall#install_skinを参照。
                rmskinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml_removed")
                if os.path.isfile(rmskinpath):
                    try:
                        shutil.move(rmskinpath, skinpath)
                        try:
                            cw.util.remove(cw.util.join_paths("Data/Skin", name), trashbox=True)
                        except Exception:
                            cw.util.print_ex(file=sys.stderr)
                        if os.path.isfile(skinpath):
                            # 依然として消せない
                            shutil.move(skinpath, rmskinpath)
                    except Exception:
                        cw.util.print_ex(file=sys.stderr)

    return skincount, unknown_ver


def main() -> None:
    pass


if __name__ == "__main__":
    main()
