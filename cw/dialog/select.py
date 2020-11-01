#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import threading
import shutil
import itertools
import wx
import wx.lib.buttons

import cw
import cw.binary.cwfile
import cw.binary.environment
import cw.binary.party
import cw.binary.adventurer

from typing import Callable, Dict, Iterable, List, Generic, Optional, Sequence, Tuple, TypeVar, Union

_T = TypeVar("_T")


# ------------------------------------------------------------------------------
# 選択ダイアログ スーパークラス
# ------------------------------------------------------------------------------

class Select(wx.Dialog, Generic[_T]):
    list: List[_T]
    index: int
    toppanel: wx.Panel

    def __init__(self, parent: wx.TopLevelWindow, name: str) -> None:
        wx.Dialog.__init__(self, parent, -1, name,
                           style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.MINIMIZE_BOX)
        self.cwpy_debug = False
        self._processing = False
        self.list = []

        self.additionals: List[wx.Control] = []
        self.addctrlbtn: Optional[wx.lib.buttons.ThemedGenBitmapToggleButton] = None

        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # buttonlist
        self.buttonlist: List[wx.Button] = []
        # leftjump
        bmp = cw.cwpy.rsrc.buttons["LJUMP"]
        self.left2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp, chain=True)
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.wins((30, 30)), bmp=bmp, chain=True)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.wins((30, 30)), bmp=bmp, chain=True)
        # rightjump
        bmp = cw.cwpy.rsrc.buttons["RJUMP"]
        self.right2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp, chain=True)
        # focus
        self.panel.SetFocusIgnoringChildren()
        # ダブルクリックとマウスアップを競合させないため
        # toppanelの上でマウスダウンしてからアップで
        # 初めてOnSelectBase()が呼ばれるようにする
        self._downbutton = -1

        self.previd = wx.NewId()
        self.nextid = wx.NewId()
        self.leftkeyid = wx.NewId()
        self.rightkeyid = wx.NewId()
        self.left2keyid = wx.NewId()
        self.right2keyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnPrevButton, id=self.previd)
        self.Bind(wx.EVT_MENU, self.OnNextButton, id=self.nextid)
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightkeyid)
        self.Bind(wx.EVT_MENU, self.OnClickLeft2Btn, id=self.left2keyid)
        self.Bind(wx.EVT_MENU, self.OnClickRight2Btn, id=self.right2keyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.previd),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.nextid),
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.leftkeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.rightkeyid),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_LEFT, self.left2keyid),
            (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_RIGHT, self.right2keyid),
        ]
        self.accels = seq

        debugid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnDebugMode, id=debugid)
        seq.append((wx.ACCEL_CTRL, ord('D'), debugid))

        cw.util.set_acceleratortable(self, seq)

    def _bind(self) -> None:
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeft2Btn, self.left2btn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRight2Btn, self.right2btn)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

        def empty(event: wx.EraseEvent) -> None:
            pass
        self.toppanel.Bind(wx.EVT_ERASE_BACKGROUND, empty)
        self.toppanel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMouseDown)
        self.toppanel.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.toppanel.Bind(wx.EVT_MIDDLE_UP, self.OnSelectBase)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnSelectBase)

        def recurse(ctrl: wx.Control) -> None:
            if not isinstance(ctrl, (wx.TextCtrl, wx.SpinCtrl)):
                ctrl.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
            for child in ctrl.GetChildren():
                recurse(child)
        recurse(self)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint2)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMotion)

        buttonlist = [button for button in self.buttonlist if button.IsEnabled()]
        if buttonlist:
            buttonlist[0].SetFocus()

    def is_processing(self) -> bool:
        return self._processing

    def OnPrevButton(self, event: wx.CommandEvent) -> None:
        focus = wx.Window.FindFocus()
        buttonlist = [button for button in self.buttonlist if button.IsEnabled()]
        if buttonlist:
            if focus in buttonlist:
                index = buttonlist.index(focus)
                buttonlist[index-1].SetFocus()
            else:
                buttonlist[-1].SetFocus()

    def OnNextButton(self, event: wx.CommandEvent) -> None:
        focus = wx.Window.FindFocus()
        buttonlist = [button for button in self.buttonlist if button.IsEnabled()]
        if buttonlist:
            if focus in buttonlist:
                index = buttonlist.index(focus)
                buttonlist[(index+1) % len(buttonlist)].SetFocus()
            else:
                buttonlist[0].SetFocus()

    def OnDebugMode(self, event: wx.CommandEvent) -> None:
        pass

    def OnMotion(self, evt: wx.MouseEvent) -> None:
        self._update_mousepos()

    def _update_mousepos(self) -> None:
        if not self.can_clickside():
            if self.can_clickcenter():
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            else:
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])
            self.clickmode = 0
            return

        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        if x < rect.x + rect.width // 4 and self.leftbtn.IsEnabled():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_BACK"])
            self.clickmode = wx.LEFT
        elif rect.x + rect.width // 4 * 3 < x and self.rightbtn.IsEnabled():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FORE"])
            self.clickmode = wx.RIGHT
        else:
            if self.can_clickcenter():
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            else:
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])
            self.clickmode = 0

    def OnClickLeftBtn(self, evt: wx.PyCommandEvent) -> None:
        if len(self.list) <= 1:
            return
        if self.index == 0:
            self.index = len(self.list) - 1
        else:
            self.index -= 1

        cw.cwpy.play_sound("page")
        self.draw(True)
        self.index_changed()

    def OnClickLeft2Btn(self, evt: wx.PyCommandEvent) -> None:
        if len(self.list) <= 1:
            return
        if self.index == 0:
            self.index = len(self.list) - 1
        elif self.index - 10 < 0:
            self.index = 0
        else:
            self.index -= 10

        cw.cwpy.play_sound("page")
        self.draw(True)
        self.index_changed()

    def OnClickRightBtn(self, evt: wx.PyCommandEvent) -> None:
        if len(self.list) <= 1:
            return
        if self.index == len(self.list) - 1:
            self.index = 0
        else:
            self.index += 1

        cw.cwpy.play_sound("page")
        self.draw(True)
        self.index_changed()

    def OnClickRight2Btn(self, evt: wx.PyCommandEvent) -> None:
        if len(self.list) <= 1:
            return
        if self.index == len(self.list) - 1:
            self.index = 0
        elif self.index + 10 > len(self.list) - 1:
            self.index = len(self.list) - 1
        else:
            self.index += 10

        cw.cwpy.play_sound("page")
        self.draw(True)
        self.index_changed()

    def index_changed(self) -> None:
        pass

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        if not self.list or len(self.list) == 1:
            return

        if cw.util.get_wheelrotation(event) > 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
            self.ProcessEvent(btnevent)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
            self.ProcessEvent(btnevent)

    def OnMouseDown(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        self._downbutton = event.GetButton()

    def OnSelectBase(self, event: wx.MouseEvent) -> None:
        if self._processing:
            return
        if self._downbutton != event.GetButton():
            self._downbutton = -1
            return
        self._downbutton = -1

        self._update_mousepos()
        if self.clickmode == wx.LEFT and self.leftbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn.GetId())
            self.ProcessEvent(btnevent)
        elif self.clickmode == wx.RIGHT and self.rightbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn.GetId())
            self.ProcessEvent(btnevent)
        else:
            self.OnSelect(event)

    def OnSelect(self, event: wx.Event) -> None:
        if not self.list:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event: wx.MouseEvent) -> None:
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint2(self, event: wx.PaintEvent) -> None:
        self.draw()

    def draw2(self, update: bool = False) -> Tuple[wx.MemoryDC, wx.Bitmap]:
        if not self.toppanel.IsShown():
            return None, None
        dest = wx.Bitmap(self.toppanel.GetClientSize())
        dc = wx.MemoryDC(dest)
        dc.Clear()
        return dc, dest

    def draw(self, update: bool = False) -> None:
        if not self.toppanel.IsShown():
            return

        dc, dest = self.draw2(update)
        self.draw3(dc, dest, update)

    def draw3(self, dc: wx.MemoryDC, dest: wx.Bitmap, update: bool) -> None:
        dc.SelectObject(wx.NullBitmap)
        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetClientSize())
        else:
            dc = wx.BufferedPaintDC(self.toppanel)
        dc.DrawBitmap(dest, cw.wins(0), cw.wins(0))

    def _do_layout(self) -> None:
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer_1)
        self.set_panelsizer()

        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.topsizer, 1, wx.EXPAND, 0)
        self.topsizer.Add(self.toppanel, 1, wx.EXPAND, 0)
        self._add_topsizer()

        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        sizer_1.Fit(self)
        self.Layout()

    def _add_topsizer(self) -> None:
        pass

    def set_panelsizer(self) -> None:
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        self.panel.SetSizer(sizer_panel)

        sizer_panel.Add(self.left2btn, 0, 0, 0)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_panel.AddStretchSpacer(1)
            sizer_panel.Add(button, 0, wx.TOP | wx.BOTTOM, cw.wins(3))

        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        sizer_panel.Add(self.right2btn, 0, 0, 0)

    def _disable_btn(self, enables: Optional[Iterable[wx.Control]] = None) -> None:
        if enables is None:
            enables = []
        lrbtns = (self.rightbtn, self.right2btn, self.leftbtn, self.left2btn)
        for btn in itertools.chain(self.buttonlist, lrbtns):
            if btn in enables:
                btn.Enable()
            else:
                btn.Disable()

    def _enable_btn(self, disables: Optional[Iterable[wx.Control]] = None) -> None:
        if disables is None:
            disables = []
        lrbtns = (self.rightbtn, self.right2btn, self.leftbtn, self.left2btn)
        for btn in itertools.chain(self.buttonlist, lrbtns):
            if btn in disables:
                btn.Disable()
            else:
                btn.Enable()

    def can_clickcenter(self) -> bool:
        """パネルの中央部分をクリックで決定可能ならTrue。"""
        return True

    def can_clickside(self) -> bool:
        """パネルの左右クリックでページ切替可能ならTrue。"""
        return True

    def _init_narrowpanel(self, choices: Iterable[str], narrowtext: str, narrowtype: int,
                          tworows: bool = False) -> None:
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        if tworows:
            self.keyword_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_keyword"])
            self.keyword_label.SetFont(font)
            self.narrow = wx.TextCtrl(self, -1, size=(cw.wins(0), -1), style=wx.TE_PROCESS_ENTER)
        else:
            self.narrow_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_condition"])
            self.narrow_label.SetFont(font)
            self.narrow = wx.TextCtrl(self, -1, size=(cw.wins(0), -1), style=wx.TE_PROCESS_ENTER)
        self.narrow.SetFont(font)
        self.narrow.SetValue(narrowtext)
        if tworows:
            self.narrow_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_condition2"])
            self.narrow_label.SetFont(font)
        cfont = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.narrow_type = wx.Choice(self, -1, size=(-1, self.narrow.GetBestSize()[1]), choices=choices)
        self.narrow_type.SetFont(cfont)
        self.narrow_type.SetSelection(narrowtype)

        self.narrow.Bind(wx.EVT_TEXT, self.OnNarrowCondition)
        self.narrow.Bind(wx.EVT_TEXT_ENTER, self.OnFind)
        self.narrow_type.Bind(wx.EVT_CHOICE, self.OnNarrowCondition)

    def OnFind(self, event: wx.CommandEvent) -> None:
        pass

    def OnNarrowCondition(self, event: wx.CommandEvent) -> None:
        if self._processing:
            return
        cw.cwpy.play_sound("page")
        # 日本語入力で一度に何度もイベントが発生する
        # 事があるので絞り込み実施を遅延する
        self._reserved_narrowconditin = True
        if wx.Window.FindFocus() != self.narrow:
            self.toppanel.SetFocus()

        def func() -> None:
            if not self._reserved_narrowconditin:
                return
            self._on_narrowcondition()
            self._reserved_narrowconditin = False
        wx.CallAfter(func)

    def _on_narrowcondition(self) -> None:
        pass

    def create_addctrlbtn(self, parent: wx.Panel, bg: wx.Bitmap, show: bool) -> None:
        """追加的なコントロールの表示切替を行うボタンを生成する。
        parent: ボタンの親コントロール。
        bg: ボタンの背景色の基準となるwx.Bitmap。
        show: 表示の初期状態。
        """
        if self.addctrlbtn:
            self.addctrlbtn.Destroy()
        self.addctrlbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(parent, -1, None, size=cw.wins((24, 24)))
        self.addctrlbtn.SetToolTip(cw.cwpy.msgs["show_additional_controls"])
        if not cw.cwpy.setting.show_addctrlbtn:
            self.addctrlbtn.Hide()
        self.addctrlbtn.SetToggle(show)
        img = cw.util.convert_to_image(bg)
        x, y = max(0, img.GetWidth()-12), 0
        r, g, b = img.GetRed(x, y), img.GetGreen(x, y), img.GetBlue(x, y)
        colour = wx.Colour(r, g, b)
        self.addctrlbtn.SetBackgroundColour(colour)
        self.Bind(wx.EVT_BUTTON, self.OnAdditionalControls, self.addctrlbtn)
        self.addctrlbtn.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def update_additionals(self) -> None:
        """表示状態の切り替え時に呼び出される。"""
        assert self.addctrlbtn
        show = self.addctrlbtn.GetToggle()
        self.update_additionals_impl(show, self.additionals)

    def update_additionals_impl(self, show: bool, additionals: List[wx.Control]) -> None:
        """表示状態の切り替え時に呼び出される。"""
        for ctrl in additionals:
            if isinstance(ctrl, tuple):
                ctrl, forceshow = ctrl
                ctrl.Show(show or forceshow())
            else:
                ctrl.Show(show)
        if show:
            bmp = cw.cwpy.rsrc.dialogs["HIDE_CONTROLS"]
        else:
            bmp = cw.cwpy.rsrc.dialogs["SHOW_CONTROLS"]
        assert self.addctrlbtn
        self.addctrlbtn.SetBitmapFocus(bmp)
        self.addctrlbtn.SetBitmapLabel(bmp)
        self.addctrlbtn.SetBitmapSelected(bmp)

    def append_addctrlaccelerator(self, seq: List[Tuple[int, int, int]]) -> None:
        """アクセラレータキーリストseqに追加的コントロール
        表示切替のショートカットキー`Ctrl+F`を追加する。
        """
        addctrl = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnToggleAdditionalControls, id=addctrl)
        seq.append((wx.ACCEL_CTRL, ord('F'), addctrl))

    def OnToggleAdditionalControls(self, event: wx.CommandEvent) -> None:
        assert self.addctrlbtn
        self.addctrlbtn.SetToggle(not self.addctrlbtn.GetToggle())
        self._additional_controls()

    def OnAdditionalControls(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._additional_controls()

    def _additional_controls(self) -> None:
        cw.cwpy.play_sound("equipment")
        self.Freeze()
        self.update_additionals()
        self.update_narrowcondition()

        self._do_layout()
        self.toppanel.Refresh()
        self.panel.Refresh()
        self.Refresh()
        self.Thaw()

    def update_narrowcondition(self) -> None:
        pass


# ------------------------------------------------------------------------------
# 一覧表示可能な選択ダイアログ(抽象クラス)
# ------------------------------------------------------------------------------

class MultiViewSelect(Generic[_T], Select[_T]):
    def __init__(self, parent: wx.TopLevelWindow, title: str, enterid: int, views: int = 10, show_multi: bool = False,
                 lines: int = 2) -> None:
        # ダイアログボックス作成
        Select.__init__(self, parent, title)
        self.viewbtn: Optional[wx.Button] = None
        self._processing = False
        self._views = views
        self._lines = lines
        self._enterid = enterid
        self.views = views if show_multi else 1

    def can_clickside(self) -> bool:
        return self.views <= 1

    def OnLeftDClick(self, event: wx.MouseEvent) -> None:
        # 一覧表示の場合はダブルクリックで決定
        if self._processing:
            return
        if 1 < self.views and self.list and self.can_clickcenter() and self.clickmode == 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self._enterid)
            self.ProcessEvent(btnevent)
        elif self.can_clickside() and self.clickmode == wx.LEFT:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn.GetId())
            self.ProcessEvent(btnevent)
        elif self.can_clickside() and self.clickmode == wx.RIGHT:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        if self._processing:
            return
        if not self.list or len(self.list) == 1:
            return

        count = self.views
        if len(self.list) <= self.views:
            count = 1
            if cw.util.get_wheelrotation(event) > 0:
                self.index = cw.util.number_normalization(self.index - count, 0, len(self.list))
            else:
                self.index = cw.util.number_normalization(self.index + count, 0, len(self.list))
        else:
            if cw.util.get_wheelrotation(event) > 0:
                self.index = cw.util.number_normalization(self.index - count, 0, self.get_pagecount() * self.views)
            else:
                self.index = cw.util.number_normalization(self.index + count, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        self.index_changed()
        cw.cwpy.play_sound("page")
        self.draw(True)

    def OnClickLeftBtn(self, evt: wx.PyCommandEvent) -> None:
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() != self.leftbtn or len(self.list) <= self.views:
            Select.OnClickLeftBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index - self.views, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        self.index_changed()
        cw.cwpy.play_sound("page")
        self.draw(True)

    def OnClickLeft2Btn(self, evt: wx.PyCommandEvent) -> None:
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() != self.left2btn or len(self.list) <= self.views:
            Select.OnClickLeft2Btn(self, evt)
            return
        if self.get_page() == 0:
            self.index = len(self.list) - 1
        elif self.index - self.views * self._views < 0:
            self.index = 0
        else:
            self.index = self.index - self.views * self._views
        self.index_changed()
        cw.cwpy.play_sound("page")
        self.draw(True)

    def OnClickRightBtn(self, evt: wx.PyCommandEvent) -> None:
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() != self.rightbtn or len(self.list) <= self.views:
            Select.OnClickRightBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index + self.views, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        self.index_changed()
        cw.cwpy.play_sound("page")
        self.draw(True)

    def OnClickRight2Btn(self, evt: wx.PyCommandEvent) -> None:
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() != self.right2btn or len(self.list) <= self.views:
            Select.OnClickRight2Btn(self, evt)
            return
        if self.get_page() == self.get_pagecount()-1:
            self.index = 0
        elif len(self.list) <= self.index + self.views * self._views:
            self.index = len(self.list) - 1
        else:
            self.index = self.index + self.views * self._views
        self.index_changed()
        cw.cwpy.play_sound("page")
        self.draw(True)

    def OnSelect(self, event: wx.Event) -> None:
        if self._processing:
            return

        if not self.list:
            return

        if self.views == 1:
            # 一件だけ表示している場合は決定
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self._enterid)
            self.ProcessEvent(btnevent)
        else:
            # 複数表示中はマウスポインタ直下を選択
            mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
            size = self.toppanel.GetSize()
            rw = size[0] // (self.views // self._lines)
            rh = size[1] // self._lines
            sindex = (mousepos[0] // rw) + ((mousepos[1] // rh) * (self.views // self._lines))
            page = self.get_page()
            index = page * self.views + sindex
            index = min(index, len(self.list)-1)
            if self.index != index:
                self.index = index
                cw.cwpy.play_sound("click")
                self.index_changed()
                self.enable_btn()
                self.draw(True)

    def OnClickViewBtn(self, event: wx.CommandEvent) -> None:
        if self._processing:
            return
        cw.cwpy.play_sound("equipment")
        self.change_view()
        self.draw(True)
        self.enable_btn()

    def change_view(self) -> None:
        assert self.viewbtn
        if self.views == 1:
            self.views = self._views
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_one"])
            self.save_views(True)
        else:
            self.views = 1
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_list"])
            self.save_views(False)

    def enable_btn(self) -> None:
        pass

    def get_page(self) -> int:
        return self.index // self.views

    def get_pagecount(self) -> int:
        return (len(self.list) + self.views - 1) // self.views

    def save_views(self, multi: bool) -> None:
        pass


# ------------------------------------------------------------------------------
# 宿選択ダイアログ
# ------------------------------------------------------------------------------

_okid = wx.NewId()


class YadoSelect(MultiViewSelect[str]):
    """
    宿選択ダイアログ。
    """
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログボックス作成
        MultiViewSelect.__init__(self, parent, cw.cwpy.msgs["select_base_title"], _okid, 6,
                                 cw.cwpy.setting.show_multiplebases, lines=3)
        self._lastbillskindir: Optional[str] = None
        self._bg = None

        # 宿情報
        self._names, self._list, self._list2, self._skins, self._classic, self._isshortcuts, self._imgpaths =\
            self.get_yadolist()
        self.index = 0
        for index, path in enumerate(self._list):
            if cw.cwpy.setting.lastyado == os.path.basename(path):
                self.index = index
                break
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((400, 370)))
        self.toppanel.SetMinSize(cw.wins((400, 370)))

        # 絞込条件
        choices = (cw.cwpy.msgs["all"],
                   cw.cwpy.msgs["sort_name"],
                   cw.cwpy.msgs["member_name"],
                   cw.cwpy.msgs["skin"])
        self._init_narrowpanel(choices, "", cw.cwpy.setting.yado_narrowtype)

        # sort
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        self.sort_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["sort_title"])
        self.sort_label.SetFont(font)
        choices2 = (cw.cwpy.msgs["sort_no"],
                    cw.cwpy.msgs["sort_name"],
                    cw.cwpy.msgs["skin"])
        self.sort = wx.Choice(self, size=(-1, self.narrow.GetBestSize()[1]), choices=choices2)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        if cw.cwpy.setting.sort_yado == "Name":
            self.sort.Select(1)
        elif cw.cwpy.setting.sort_yado == "Skin":
            self.sort.Select(2)
        else:
            self.sort.Select(0)

        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, _okid, cw.wins((50, 24)), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.okbtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["new"])
        self.buttonlist.append(self.newbtn)
        # extension
        self.exbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["extension"])
        self.buttonlist.append(self.exbtn)
        # view
        s = cw.cwpy.msgs["member_list"] if self.views == 1 else cw.cwpy.msgs["member_one"]
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), s)
        self.buttonlist.append(self.viewbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((50, 24)),
                                                     cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)
        # enable bottun
        self.enable_btn()
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)

        # additionals
        self.create_addctrlbtn(self.toppanel, self._get_bg(), cw.cwpy.setting.show_additional_yado)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(self.addctrlbtn, 0, wx.ALIGN_TOP, 0)
        self.toppanel.SetSizer(sizer)

        self.additionals.append(self.narrow_label)
        self.additionals.append(self.narrow)
        self.additionals.append(self.narrow_type)
        self.additionals.append(self.sort_label)
        self.additionals.append(self.sort)
        self.update_additionals()

        self.list = self._list
        self.update_narrowcondition()

        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnOk, id=self.okbtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExBtn, self.exbtn)
        self.Bind(wx.EVT_CHOICE, self.OnSort, self.sort)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.toppanel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        seq = self.accels
        self.sortkeydown = []
        for i in range(0, 9):
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
            self.append_addctrlaccelerator(seq)
        cw.util.set_acceleratortable(self, seq)

    def update_additionals(self) -> None:
        Select.update_additionals(self)
        assert self.addctrlbtn
        cw.cwpy.setting.show_additional_yado = self.addctrlbtn.GetToggle()

    def _add_topsizer(self) -> None:
        nsizer = wx.BoxSizer(wx.HORIZONTAL)

        nsizer.Add(self.narrow_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(2))
        nsizer.Add(self.narrow, 1, wx.CENTER, 0)
        nsizer.Add(self.narrow_type, 0, wx.CENTER | wx.EXPAND, cw.wins(3))

        nsizer.Add(self.sort_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(3))
        nsizer.Add(self.sort, 0, wx.CENTER | wx.EXPAND, 0)

        self.topsizer.Add(nsizer, 0, wx.EXPAND, 0)

    def _on_narrowcondition(self) -> None:
        cw.cwpy.setting.yado_narrowtype = self.narrow_type.GetSelection()
        self.update_narrowcondition()
        self.draw(True)

    def update_narrowcondition(self) -> None:
        if 0 <= self.index and self.index < len(self.list):
            selected: Optional[str] = self.list[self.index]
        else:
            selected = None

        objs = self._list_to_obj()

        narrow = self.narrow.GetValue().lower()
        donarrow = self.narrow.IsShown() and bool(narrow)

        if donarrow:
            _NARROW_ALL = 0
            _NARROW_NAME = 1
            _NARROW_MEMBER = 2
            _NARROW_SKIN = 3

            ntype = self.narrow_type.GetSelection()

            ntypes = set()
            if ntype == _NARROW_ALL:
                ntypes.add(_NARROW_NAME)
                ntypes.add(_NARROW_MEMBER)
                ntypes.add(_NARROW_SKIN)
            else:
                ntypes.add(ntype)

            seq = []
            for obj in objs:
                def has_advname() -> bool:
                    for advname in obj.advnames:
                        if narrow in advname.lower():
                            return True
                    return False

                if (_NARROW_NAME in ntypes and narrow in obj.name.lower()) or \
                        (_NARROW_MEMBER in ntypes and has_advname()) or \
                        (_NARROW_SKIN in ntypes and narrow in obj.skin.lower()):
                    seq.append(obj)
            objs = seq

        self._sort_objs(objs)
        self._obj_to_list(objs)

        if selected in self.list:
            self.index = self.list.index(selected)
        elif self.list:
            self.index %= len(self.list)
        else:
            self.index = 0
        self.enable_btn()

    def _get_bg(self) -> wx.Bitmap:
        if self._bg:
            return self._bg
        path = "Table/Bill"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self._bg = cw.util.load_wxbmp(path, can_loaded_scaledimage=True)
        return self._bg

    def OnNumberKeyDown(self, event: wx.KeyEvent) -> None:
        """
        数値キー'1'～'9'までの押下を処理する。
        PlayerSelectではソート条件の変更を行う。
        """
        if self._processing:
            return

        if self.sort.IsShown():
            index = self.sortkeydown.index(event.GetId())
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.sort.GetId())
                self.ProcessEvent(event)

    def OnSort(self, event: wx.CommandEvent) -> None:
        if self._processing:
            return

        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "Skin"
        else:
            sorttype = "None"

        if cw.cwpy.setting.sort_yado != sorttype:
            cw.cwpy.play_sound("page")
            cw.cwpy.setting.sort_yado = sorttype
            self.update_narrowcondition()
            self.draw(True)

    def _sort_objs(self, objs: List["_YadoObj"]) -> None:
        sorttype = cw.cwpy.setting.sort_yado
        if sorttype == "Name":
            cw.util.sort_by_attr(objs, "name", "skin", "order", "yadodirname")
        elif sorttype == "Skin":
            cw.util.sort_by_attr(objs, "skin", "name", "order", "yadodirname")
        else:
            cw.util.sort_by_attr(objs, "order", "name", "skin", "yadodirname")

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        if self._processing:
            return

        if change_combo(self.narrow_type, event):
            return
        elif change_combo(self.sort, event):
            return
        else:
            MultiViewSelect.OnMouseWheel(self, event)

    def _list_to_obj(self) -> List["_YadoObj"]:
        seq = []
        for t in zip(self._names, self._list, self._list2, self._skins, self._classic, self._isshortcuts,
                     self._imgpaths):
            seq.append(_YadoObj(*t))
        return seq

    def _obj_to_list(self, objs: List["_YadoObj"]) -> None:
        self.names = []
        self.list = []
        self.list2 = []
        self.skins = []
        self.classic = []
        self.isshortcuts = []
        self.imgpaths = []
        for obj in objs:
            self.names.append(obj.name)
            self.list.append(obj.yadodir)
            self.list2.append(obj.advnames)
            self.skins.append(obj.skin)
            self.classic.append(obj.classic)
            self.isshortcuts.append(obj.isshortcut)
            self.imgpaths.append(obj.imgpaths)

    def save_views(self, multi: bool) -> None:
        cw.cwpy.setting.show_multiplebases = multi

    def index_changed(self) -> None:
        MultiViewSelect.index_changed(self)
        self.enable_btn()
        buttonlist = [button for button in self.buttonlist if button.IsEnabled()]
        if buttonlist:
            buttonlist[0].SetFocus()

    def can_clickcenter(self) -> bool:
        return not (self.views == 1 and self._list and not self.okbtn.IsEnabled()) and\
                ((self.list and self._list and os.path.isdir(self.list[self.index])) or
                 (self.newbtn.IsEnabled() and not self._list))

    def enable_btn(self) -> None:
        # リストが空だったらボタンを無効化
        if not self.list:
            self.okbtn.SetLabel(cw.cwpy.msgs["decide"])
            self._disable_btn((self.exbtn, self.newbtn, self.closebtn))
            return

        if self.classic[self.index]:
            self.okbtn.SetLabel("変換")
        else:
            self.okbtn.SetLabel(cw.cwpy.msgs["decide"])

        if len(self.list) <= 1:
            self._enable_btn((self.rightbtn, self.right2btn, self.leftbtn, self.left2btn))
        else:
            self._enable_btn()

        if self.list and (cw.util.exists_mutex(self.list[self.index]) or not os.path.isdir(self.list[self.index])):
            self.okbtn.Disable()

    def OnSelect(self, event: wx.Event) -> None:
        if self._list:
            MultiViewSelect.OnSelect(self, event)
        elif self.newbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.newbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnOk(self, event: wx.PyCommandEvent) -> None:
        if not self.list:
            return
        if not self.okbtn.IsEnabled():
            return

        if self.classic[self.index]:
            self._convert_current()
        else:
            self.EndModal(wx.ID_OK)

    def OnDropFiles(self, event: wx.DropFilesEvent) -> None:
        paths = event.GetFiles()

        for path in paths:
            self.conv_yado(path)
            time.sleep(0.3)

    def OnClickExBtn(self, event: wx.CommandEvent) -> None:
        """
        拡張。
        """
        cw.cwpy.play_sound("click")
        if self.list:
            yname = self.names[self.index]
            title = cw.cwpy.msgs["extension_title"] % (yname)
            classic = self.classic[self.index]
            hasmutexlocal = not cw.util.exists_mutex(self.list[self.index]) and os.path.isdir(self.list[self.index])
            cantransfer = bool(1 < self.classic.count(False) and os.path.isdir(self.list[self.index]))
        else:
            title = cw.cwpy.msgs["extension_title_2"]
            classic = False
            hasmutexlocal = False
            cantransfer = False
        if cantransfer:
            for i, path in enumerate(self.list):
                if not self.classic[i] and cw.util.exists_mutex(path):
                    cantransfer = False
                    break

        items = [
            (cw.cwpy.msgs["settings"], cw.cwpy.msgs["edit_base_description"],
             self.rename_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["copy"], cw.cwpy.msgs["copy_base_description"],
             self.copy_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["transfer"], cw.cwpy.msgs["transfer_base_description"],
             self.trasnfer_yadodata, cantransfer),
            ("変換", "CardWirth用の宿データをCardWirthPy用の拠点データに変換します。",
             self._conv_yado, not cw.util.exists_mutex(cw.tempdir_init)),
            ("逆変換", "選択中の拠点データをCardWirth用のデータに逆変換します。",
             self.unconv_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_base_description"],
             self.delete_yado, hasmutexlocal),
        ]
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def rename_yado(self) -> None:
        """
        宿改名。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        cw.cwpy.play_sound("click")
        path = self.list[self.index]
        dlg = cw.dialog.create.YadoCreater(self, path)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            assert dlg.yadodir is not None
            self.update_list(dlg.yadodir, clear_narrowcondition=True)

        dlg.Destroy()

    def copy_yado(self) -> None:
        """
        宿複製。
        """
        from . import message

        if not os.path.isdir(self.list[self.index]):
            return
        cw.cwpy.play_sound("signal")
        path = self.list[self.index]
        yname = self.names[self.index]
        s = cw.cwpy.msgs["copy_base"] % (yname)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.util.create_mutex("Yado"):
                try:
                    if cw.util.create_mutex(self.list[self.index]):
                        cw.util.release_mutex()
                        env = cw.util.join_paths(path, "Environment.xml")
                        data = cw.data.xml2etree(env)
                        name = data.gettext("Property/Name", os.path.basename(path))
                        name = "コピー - %s" % (name)
                        if not data.find("Property/Name") is None:
                            data.edit("Property/Name", name)
                        else:
                            e = data.make_element("Name", name)
                            data.insert("Property", e, 0)

                        newpath = cw.binary.util.check_filename(name)
                        newpath = cw.util.join_paths(os.path.dirname(path), newpath)
                        newpath = cw.binary.util.check_duplicate(newpath)
                        self.TopLevelParent.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
                        shutil.copytree(path, newpath)
                        env = cw.util.join_paths(newpath, "Environment.xml")
                        data.write_file(env)
                        cw.cwpy.play_sound("harvest")
                        cw.cwpy.setting.insert_yadoorder(os.path.basename(newpath))
                        self.update_list(newpath)
                        self.TopLevelParent.SetCursor(wx.NullCursor)
                    else:
                        cw.cwpy.play_sound("error")
                finally:
                    cw.util.release_mutex()
            else:
                cw.cwpy.play_sound("error")

        dlg.Destroy()

    def trasnfer_yadodata(self) -> None:
        """
        宿のデータのコピー。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex("Yado"):
            try:
                mutexes = 0
                for path in self.list:
                    if cw.util.create_mutex(path):
                        mutexes += 1
                    else:
                        break
                draw = False
                try:
                    if mutexes != len(self.list):
                        cw.cwpy.play_sound("error")
                        return
                finally:
                    for i in range(mutexes):
                        cw.util.release_mutex()

                path = self.list[self.index]
                dirs = []
                names = []
                for i, dname in enumerate(self.list):
                    if not self.classic[i]:
                        dirs.append(dname)
                        names.append(self.names[i])
                if names:
                    cw.cwpy.play_sound("click")
                    dlg = cw.dialog.transfer.TransferYadoDataDialog(self, dirs, names, path)
                    cw.cwpy.frame.move_dlg(dlg)
                    if dlg.ShowModal() == wx.ID_OK:
                        self.update_list(path)
                    dlg.Destroy()
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.play_sound("error")

    def delete_yado(self) -> None:
        """
        宿削除。
        """
        from . import message

        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex("Yado"):
            try:
                if cw.util.create_mutex(self.list[self.index]):
                    cw.util.release_mutex()
                    cw.cwpy.play_sound("signal")
                    path = self.list[self.index]
                    dname = os.path.basename(path)
                    yname = self.names[self.index]
                    if self.isshortcuts[self.index]:
                        s = cw.cwpy.msgs["delete_base_shortcut"] % (yname)
                    else:
                        s = cw.cwpy.msgs["delete_base"] % (yname)
                    dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                    cw.cwpy.frame.move_dlg(dlg)

                    if dlg.ShowModal() == wx.ID_OK:
                        isshortcut = self.isshortcuts[self.index]
                        if not isshortcut:
                            self.TopLevelParent.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
                        if isshortcut:
                            cw.util.remove(self.isshortcuts[self.index])
                        else:
                            cw.util.remove(path, trashbox=True)
                        if not self.classic[self.index]:
                            cw.util.remove(cw.util.join_paths("Data/Temp/Local", path))
                        cw.cwpy.play_sound("dump")
                        cw.cwpy.setting.yado_order.pop(dname, None)
                        if self.index+1 < len(self.list):
                            self.update_list(self.list[self.index+1])
                        elif 0 < self.index:
                            self.update_list(self.list[self.index-1])
                        else:
                            self.update_list()
                        if not isshortcut:
                            self.TopLevelParent.SetCursor(wx.NullCursor)

                    dlg.Destroy()
                else:
                    cw.cwpy.play_sound("error")
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.play_sound("error")

    def OnClickNewBtn(self, event: wx.CommandEvent) -> None:
        """
        宿新規作成。
        """
        cw.cwpy.play_sound("click")
        dlg = cw.dialog.create.YadoCreater(self)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.play_sound("harvest")
            assert dlg.yadodir is not None
            cw.cwpy.setting.insert_yadoorder(os.path.basename(dlg.yadodir))
            self.update_list(dlg.yadodir, clear_narrowcondition=True)

        dlg.Destroy()

    def _conv_yado(self) -> None:
        """
        CardWirthの宿データを変換。
        """
        # ディレクトリ選択ダイアログ
        s = ("CardWirthの宿のデータをCardWirthPy用に変換します。" +
             "\n変換する宿のフォルダを選択してください")
        dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
        dlg.SetPath(os.getcwd())

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.conv_yado(path)
        else:
            dlg.Destroy()

    def _convert_current(self) -> None:
        from . import message

        if not (self.list and self.classic[self.index]):
            return
        yname = self.names[self.index]
        s = "「%s」をCardWirthPy用に変換します。\nよろしいですか？" % yname
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.Parent.move_dlg(dlg)
        cw.cwpy.play_sound("click")
        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            path = self.list[self.index]
            self.conv_yado(path, ok=True, moveconverted=True, deletepath=self.isshortcuts[self.index])
        else:
            dlg.Destroy()

    def draw(self, update: bool = False) -> None:
        dc, dest = self.draw2(update)

        if self.views != 1 and self._lastbillskindir is not None:
            skindir = self._lastbillskindir
        elif self.list and self.views == 1:
            skindir = self.skins[self.index]
            self._lastbillskindir = skindir
        else:
            skindir = cw.cwpy.skindir

        # 背景
        path = "Table/Bill"
        path = cw.util.find_resource(cw.util.join_paths(skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins(cw.util.load_wxbmp(path, can_loaded_scaledimage=True))
        bmpw, bmph = self.toppanel.GetClientSize()
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            self.draw3(dc, dest, update)
            return

        def get_playingbmp() -> wx.Bitmap:
            fpath = cw.util.find_resource(cw.util.join_paths(skindir, "Resource/Image/Dialog/PLAYING_YADO"), cw.M_IMG)
            if os.path.isfile(fpath):
                return cw.wins(cw.util.load_wxbmp(fpath, True, can_loaded_scaledimage=True))
            else:
                fpath = cw.util.find_resource(cw.util.join_paths(skindir, "Resource/Image/Dialog/PLAYING"), cw.M_IMG)
                if os.path.isfile(fpath):
                    return cw.wins(cw.util.load_wxbmp(fpath, True, can_loaded_scaledimage=True))
                elif "PLAYING_YADO" in cw.cwpy.rsrc.dialogs:
                    return cw.cwpy.rsrc.dialogs["PLAYING_YADO"]
                else:
                    return cw.cwpy.rsrc.dialogs["PLAYING"]

        cardw, cardh = cw.wins(cw.SIZE_CARDIMAGE)
        if self.views == 1:
            # 単独表示
            if self.classic[self.index]:
                # 変換が必要な場合
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16)))
                dc.SetTextForeground(wx.RED)
                s = "変換が必要です"
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)//2, cw.wins(20))

            # 宿画像
            imgx = (bmpw-cardw) // 2
            imgy = cw.wins(70)
            imgpaths = self.imgpaths[self.index]
            if imgpaths:
                dc.SetClippingRegion(wx.Rect(imgx, imgy, cardw, cardh))
                for info in imgpaths:
                    if not info.path:
                        continue
                    path = cw.util.join_paths(self.list[self.index], info.path)
                    bmp_noscale = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True)
                    bmp = cw.wins(bmp_noscale)
                    baserect = info.calc_basecardposition_wx(bmp.GetSize(), noscale=False,
                                                             basecardtype="Bill",
                                                             cardpostype="NotCard")
                    dc.DrawBitmap(bmp, imgx + baserect.x, imgy + baserect.y, True)
                dc.DestroyClippingRegion()
            else:
                path = "Resource/Image/Card/COMMAND0"
                path = cw.util.find_resource(cw.util.join_paths(skindir, path), cw.cwpy.rsrc.ext_img)
                bmp = cw.wins(cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True))
                dc.DrawBitmap(bmp, imgx, imgy, True)
            if self.isshortcuts[self.index]:
                bmp = cw.cwpy.rsrc.dialogs["LINK"]
                dc.DrawBitmap(bmp, (bmpw-cw.wins(74))//2-cw.wins(3), cw.wins(135), True)

            # 宿名前
            dc.SetTextForeground(wx.BLACK)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("scenario", pixelsize=cw.wins(21)))
            s = self.names[self.index]
            w = dc.GetTextExtent(s)[0]

            # 宿名
            w = dc.GetTextExtent(s)[0]
            maxwidth = bmpw - cw.wins(5)*2
            if maxwidth < w:
                cw.util.draw_witharound(dc, s, cw.wins(5), cw.wins(40), maxwidth=maxwidth)
            else:
                cw.util.draw_witharound(dc, s, (bmpw-w)//2, cw.wins(40))

            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(15)))
            s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
            s = s + "/" + str(len(self.list))
            w = dc.GetTextExtent(s)[0]
            cw.util.draw_witharound(dc, s, (bmpw-w)//2, cw.wins(338))
            # Adventurers
            s = cw.cwpy.msgs["adventurers"]
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)//2, cw.wins(175))

            # 所属冒険者
            maxwidth = cw.wins(90)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
            for idx, name in enumerate(self.list2[self.index]):
                if 24 <= idx:
                    break
                if 23 == idx:
                    if 24 < len(self.list2[self.index]):
                        name = cw.cwpy.msgs["scenario_etc"]
                x = (bmpw - cw.wins(270)) // 2 + ((idx % 3) * cw.wins(95))
                y = cw.wins(200) + (idx // 3) * cw.wins(16)
                cw.util.draw_adjusted(dc, name, x, y, maxwidth=maxwidth)

            # 使用中マーク
            if cw.util.exists_mutex(self.list[self.index]):
                bmp = get_playingbmp()
                w, h = bmp.GetSize()
                dc.DrawBitmap(bmp, (bmpw-w)//2, (bmph-h)//2, True)
        else:
            # 一覧表示
            pindex = self.views * self.get_page()
            x = 0
            y = 0
            aw = bmpw // 2
            ah = bmph // 3
            for index in range(pindex, min(pindex+self.views, len(self.list))):
                skindir = self.skins[index]

                # 宿画像
                imgpaths = self.imgpaths[index]
                imgx = cw.wins(5)+x
                imgy = cw.wins(20)+y
                if imgpaths:
                    dc.SetClippingRegion(wx.Rect(imgx, imgy, cardw, cardh))
                    for info in imgpaths:
                        if not info.path:
                            continue
                        path = cw.util.join_paths(self.list[index], info.path)
                        bmp_noscale = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True)
                        bmp = cw.wins(bmp_noscale)
                        baserect = info.calc_basecardposition_wx(bmp.GetSize(), noscale=False,
                                                                 basecardtype="Bill",
                                                                 cardpostype="NotCard")
                        dc.DrawBitmap(bmp, imgx + baserect.x, imgy + baserect.y, True)
                    dc.DestroyClippingRegion()
                else:
                    path = "Resource/Image/Card/COMMAND0"
                    path = cw.util.find_resource(cw.util.join_paths(skindir, path), cw.cwpy.rsrc.ext_img)
                    bmp = cw.wins(cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True))
                    dc.DrawBitmap(bmp, imgx, imgy, True)
                if self.isshortcuts[index]:
                    bmp = cw.cwpy.rsrc.dialogs["LINK"]
                    dc.DrawBitmap(bmp, cw.wins(2)+x, cw.wins(85)+y, True)

                # 宿名前
                dc.SetTextForeground(wx.BLACK)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("scenario", pixelsize=cw.wins(17)))
                s = self.names[index]
                maxwidth = bmpw//2 - cw.wins(3)*2
                cw.util.draw_antialiasedtext(dc, s, x + cw.wins(3), cw.wins(3)+y, False,
                                             maxwidth, 0, bordering=True, scaledown=False, align=wx.ALIGN_CENTER)

                yy = cw.wins(25)
                amax = 6
                if self.classic[index]:
                    # 変換が必要な場合
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14)))
                    dc.SetTextForeground(wx.RED)
                    s = "変換が必要です"
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, cw.wins(84)+x, cw.wins(22)+y)
                    yy += cw.wins(15)
                    amax -= 1

                # 所属冒険者
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
                maxwidth = aw - cw.wins(84) - cw.wins(2)
                for idx, name in enumerate(self.list2[index]):
                    cw.util.draw_witharound(dc, name, cw.wins(84)+x, yy+y, maxwidth=maxwidth)
                    yy += cw.wins(15)
                    if amax-2 <= idx and amax < len(self.list2[index]):
                        name = cw.cwpy.msgs["scenario_etc"]
                        cw.util.draw_witharound(dc, name, cw.wins(84)+x, yy+y)
                        break

                if (index-pindex) % 2 == 1:
                    x = 0
                    y += ah
                else:
                    x += aw

            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(13)))
            s = "%s/%s" % (self.get_page()+1, self.get_pagecount())
            w = dc.GetTextExtent(s)[0]
            cw.util.draw_witharound(dc, s, (bmpw-w)//2, cw.wins(355))

            # 使用中マーク
            x = 0
            y = 0
            for index in range(pindex, min(pindex+self.views, len(self.list))):
                skindir = self.skins[index]

                if cw.util.exists_mutex(self.list[index]):
                    bmp = get_playingbmp()
                    w, h = bmp.GetSize()
                    dc.DrawBitmap(bmp, (aw-w)//2+x, (ah-h)//2+y, True)
                if (index-pindex) % 2 == 1:
                    x = 0
                    y += ah
                else:
                    x += aw

            # Selected
            x = 0
            y = 0
            for index in range(pindex, min(pindex+self.views, len(self.list))):
                if index == self.index:
                    bmp = cw.cwpy.rsrc.wxstatuses["TARGET"]
                    dc.DrawBitmap(bmp, cw.wins(180)-bmp.GetWidth()+x, cw.wins(102)-bmp.GetHeight()+y, True)
                if (index-pindex) % 2 == 1:
                    x = 0
                    y += ah
                else:
                    x += aw

        self.draw3(dc, dest, update)

    def conv_yado(self, path: str, ok: bool = False, moveconverted: bool = False, deletepath: str = "") -> None:
        """
        CardWirthの宿データを変換。
        """
        from . import message

        # カードワースの宿か確認
        if not os.path.exists(cw.util.join_paths(path, "Environment.wyd")):
            s = "CardWirthの宿のディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        if not ok:
            cw.cwpy.play_sound("click")
            s = os.path.basename(path) + " を変換します。\nよろしいですか？"
            dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            self.Parent.move_dlg(dlg)

            if not dlg.ShowModal() == wx.ID_OK:
                dlg.Destroy()
                return

            dlg.Destroy()

        # 宿データ
        cwdata = cw.binary.cwyado.CWYado(path, "Yado", cw.cwpy.setting.skintype)

        # 変換可能なデータかどうか確認
        if not cwdata.is_convertible():
            s = "CardWirth ver.1.20-1.50の宿しか変換できません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        if cw.util.create_mutex("Yado"):
            try:
                thread = cw.binary.ConvertingThread(cwdata)
                thread.start()

                # プログレスダイアログ表示
                dlg = cw.dialog.progress.ProgressDialog(self, cwdata.name + "の変換", "",
                                                        maximum=100)

                def progress() -> None:
                    while not thread.complete:
                        wx.CallAfter(dlg.UpdateProgress, cwdata.curnum, cwdata.message)
                        time.sleep(0.001)
                    wx.CallAfter(dlg.Destroy)
                thread2 = threading.Thread(target=progress)
                thread2.start()
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()

                yadodir = thread.path

                # エラーログ表示
                if cwdata.errorlog:
                    dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
                    self.Parent.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()

                # 変換完了ダイアログ
                cw.cwpy.play_sound("harvest")
                s = "データの変換が完了しました。"
                dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()

                if deletepath:
                    cw.util.remove(deletepath)
                elif moveconverted:
                    if not os.path.isdir("ConvertedYado"):
                        os.makedirs("ConvertedYado")
                    topath = cw.util.join_paths("ConvertedYado", os.path.basename(path))
                    topath = cw.binary.util.check_duplicate(topath)
                    shutil.move(path, topath)

                cw.cwpy.play_sound("page")
                cw.cwpy.setting.insert_yadoorder(os.path.basename(yadodir))
                self.update_list(yadodir, clear_narrowcondition=True)
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.play_sound("error")

    def unconv_yado(self) -> None:
        """
        CardWirthの宿データへ逆変換。
        """
        from . import message

        yadodir = self.list[self.index]
        yadoname = self.names[self.index]

        # 変換確認ダイアログ
        cw.cwpy.play_sound("click")
        dlg = cw.dialog.etc.ConvertYadoDialog(self, yadoname)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        targetengine = dlg.targetengine
        dstpath = dlg.dstpath
        dlg.Destroy()

        try:
            if not os.path.isdir(dstpath):
                os.makedirs(dstpath)
        except Exception:
            cw.util.print_ex()
            s = "フォルダ %s を生成できません。" % (dstpath)
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        cw.cwpy.setting.unconvert_targetfolder = dstpath

        # 宿データ
        cw.cwpy.yadodir = cw.util.join_paths(yadodir)
        cw.cwpy.tempdir = cw.cwpy.yadodir.replace("Yado", cw.util.join_paths(cw.tempdir, "Yado"), 1)
        try:
            ydata = cw.data.YadoData(cw.cwpy.yadodir, cw.cwpy.tempdir, loadparty=False)

            # コンバータ
            unconv = cw.binary.cwyado.UnconvCWYado(ydata, dstpath, targetengine)

            thread = cw.binary.ConvertingThread(unconv)
            thread.start()

            # プログレスダイアログ表示
            dlg = cw.dialog.progress.ProgressDialog(self, "%sの逆変換" % (yadoname), "",
                                                    maximum=unconv.maxnum)

            def progress() -> None:
                while not thread.complete:
                    wx.CallAfter(dlg.UpdateProgress, unconv.curnum, unconv.message)
                    time.sleep(0.001)
                wx.CallAfter(dlg.Destroy)
            thread2 = threading.Thread(target=progress)
            thread2.start()
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
        finally:
            cw.cwpy.yadodir = ""
            cw.cwpy.tempdir = ""

        # エラーログ表示
        if unconv.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, unconv.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # 変換完了ダイアログ
        cw.cwpy.play_sound("harvest")
        s = "データの逆変換が完了しました。\n%s" % (unconv.dir)
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_list(self, yadodir: str = "", clear_narrowcondition: bool = False) -> None:
        """
        登録されている宿のリストを更新して、
        引数のnameの宿までページを移動する。
        """
        if clear_narrowcondition:
            self._processing = True
            self.narrow.SetValue("")
            self._processing = False
        self._names, self._list, self._list2, self._skins, self._classic, self._isshortcuts, self._imgpaths =\
            self.get_yadolist()
        self.list = self._list

        if yadodir:
            self.index = self.list.index(yadodir)

        self.update_narrowcondition()

        self.draw(True)
        self.enable_btn()

    def get_yadolist(self) -> Tuple[List[str], List[str], List[List[str]], List[str], List[bool], List[str],
                                    List[List[cw.image.ImageInfo]]]:
        """Yadoにある宿のpathリストと冒険者リストを返す。"""
        cw.fsync.sync()
        names = []
        yadodirs = []
        skins = []
        classic = []
        isshortcuts = []
        imgpaths = []

        skin_support: Dict[str, bool] = {}

        if not os.path.exists("Yado"):
            os.makedirs("Yado")

        for dname in os.listdir("Yado"):
            path = cw.util.join_paths("Yado", dname, "Environment.xml")

            if os.path.isfile(path):
                prop = cw.header.GetProperty(path)
                name = prop.properties.get("Name", "")
                if not name:
                    name = os.path.basename(dname)
                names.append(name)

                skin = prop.properties.get("Skin", "Classic")
                skin = cw.util.join_paths("Data/Skin", skin)
                skinxml = cw.util.join_paths(skin, "Skin.xml")

                if skinxml in skin_support:
                    supported_skin = skin_support[skinxml]
                else:
                    if not os.path.isfile(skinxml):
                        supported_skin = False
                    else:
                        supported_skin = cw.header.GetProperty(skinxml).attrs.get(None, {}).get("dataVersion", "0")\
                                         in cw.SUPPORTED_SKIN
                    skin_support[skinxml] = supported_skin

                if supported_skin:
                    skins.append(skin)
                else:
                    skins.append(cw.cwpy.skindir)

                path = cw.util.join_paths("Yado", dname)
                yadodirs.append(path)
                classic.append(False)
                isshortcuts.append("")
                imgpaths.append(cw.image.get_imageinfos_p(prop))
                continue

            path = cw.util.join_paths("Yado", dname)
            path2 = cw.util.get_linktarget(path)
            isshortcut = path2 != path
            if isshortcut:
                path = path2
            path = cw.util.join_paths(path, "Environment.wyd")
            if os.path.isfile(path):
                # クラシックな宿
                name = os.path.basename(path2)
                names.append(name)
                skins.append(cw.cwpy.skindir)
                yadodirs.append(path2)
                classic.append(True)
                if isshortcut:
                    isshortcuts.append(cw.util.join_paths("Yado", dname))
                else:
                    isshortcuts.append("")
                imgpaths.append([])
                continue

        advnames = []

        for i, yadodir in enumerate(yadodirs):
            seq = []

            if classic[i]:
                # クラシックな宿
                try:
                    wydpath = cw.util.join_paths(yadodir, "Environment.wyd")
                    if not os.path.isfile(wydpath):
                        advnames.append(["*読込失敗*"])
                        continue

                    with cw.binary.cwfile.CWFile(wydpath, "rb") as f:
                        wyd = cw.binary.environment.Environment(None, f, True, versiononly=True)
                        f.close()
                    if 13 <= wyd.dataversion_int:
                        # 1.50まで
                        advnames.append(["*読込失敗*"])
                        continue

                    # 1.20のアルバムデータは時間がかかる可能性があるため
                    # リストに表示しない
                    for fname in os.listdir(yadodir):
                        ext = cw.util.splitext(fname)[1].lower()
                        if ext == ".wch":
                            fpath = cw.util.join_paths(yadodir, fname)
                            if wyd.dataversion_int <= 8:
                                # 1.20
                                with cw.binary.cwfile.CWFile(fpath, "rb") as f:
                                    f.string()
                                    name = f.string()
                                    f.close()
                                seq.append(name)
                            else:
                                # 1.28以降
                                with cw.binary.cwfile.CWFile(fpath, "rb") as f:
                                    adv = cw.binary.adventurer.Adventurer(None, f, nameonly=True)
                                    f.close()
                                seq.append(adv.name)
                        elif ext == ".wpl":
                            fpath = cw.util.join_paths(yadodir, fname)
                            with cw.binary.cwfile.CWFile(fpath, "rb") as f:
                                party = cw.binary.party.Party(None, f, dataversion=wyd.dataversion_int)
                                f.close()
                            for member in party.memberslist:
                                seq.append(member)
                except Exception:
                    cw.util.print_ex()

            else:
                yadodb = cw.yadodb.YadoDB(yadodir)
                standbys = yadodb.get_standbynames()
                if len(standbys) == 0:
                    yadodb.update(cards=False, adventurers=True, parties=False)
                    standbys = yadodb.get_standbynames()

                seq = standbys
                yadodb.close()

            advnames.append(seq)

        return names, yadodirs, advnames, skins, classic, isshortcuts, imgpaths


class _YadoObj(object):
    def __init__(self, name: str, yadodir: str, advnames: List[str], skin: str, classic: bool, isshortcut: str,
                 imgpaths: List[cw.image.ImageInfo]) -> None:
        self.name = name
        self.yadodir = yadodir
        self.advnames = advnames
        self.skin = skin
        self.classic = classic
        self.isshortcut = isshortcut
        if isshortcut:
            self.yadodirname = os.path.basename(isshortcut)
        else:
            self.yadodirname = os.path.basename(yadodir)
        self.imgpaths = imgpaths
        self.order = cw.cwpy.setting.yado_order.get(self.yadodirname, 0x7fffffff)


# ------------------------------------------------------------------------------
# パーティ選択ダイアログ
# ------------------------------------------------------------------------------

class PartySelect(MultiViewSelect[cw.header.PartyHeader]):
    """
    パーティ選択ダイアログ。
    """
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログボックス作成
        MultiViewSelect.__init__(self, parent, cw.cwpy.msgs["resume_adventure"], wx.ID_OK, 8,
                                 cw.cwpy.setting.show_multipleparties)
        assert cw.cwpy.ydata
        self._bg = None
        # パーティ情報
        self.list = cw.cwpy.ydata.partys
        self.index = 0
        if cw.cwpy.ydata.lastparty:
            # 前回選択されていたパーティ
            lastparty = cw.util.get_yadofilepath(cw.cwpy.ydata.lastparty).lower()
            for i, header in enumerate(self.list):
                if cw.util.get_yadofilepath(header.fpath).lower() == lastparty:
                    self.index = i
                    break
        self.names: List[str] = []
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        self.toppanel.SetMinSize(cw.wins((460, 280)))

        # 絞込条件
        choices = (cw.cwpy.msgs["all"],
                   cw.cwpy.msgs["narrow_party_name"],
                   cw.cwpy.msgs["member_name"],
                   cw.cwpy.msgs["description"],
                   cw.cwpy.msgs["history"],
                   cw.cwpy.msgs["character_attribute"],
                   cw.cwpy.msgs["sort_level"])
        self._init_narrowpanel(choices, "", cw.cwpy.setting.parties_narrowtype)

        # sort
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        self.sort_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["sort_title"])
        self.sort_label.SetFont(font)
        choices2 = (cw.cwpy.msgs["sort_no"],
                    cw.cwpy.msgs["sort_name"],
                    cw.cwpy.msgs["highest_level"],
                    cw.cwpy.msgs["average_level"],
                    cw.cwpy.msgs["money"])
        self.sort = wx.Choice(self, size=(-1, self.narrow.GetBestSize()[1]), choices=choices2)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        if cw.cwpy.setting.sort_parties == "Name":
            self.sort.Select(1)
        elif cw.cwpy.setting.sort_parties == "HighestLevel":
            self.sort.Select(2)
        elif cw.cwpy.setting.sort_parties == "AverageLevel":
            self.sort.Select(3)
        elif cw.cwpy.setting.sort_parties == "Money":
            self.sort.Select(4)
        else:
            self.sort.Select(0)

        width = 50
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, cw.wins((width, 24)), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.okbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)), cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # edit
        self.editbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)), cw.cwpy.msgs["members"])
        self.buttonlist.append(self.editbtn)
        # view
        s = cw.cwpy.msgs["member_list"] if self.views == 1 else cw.cwpy.msgs["member_one"]
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)), s)
        self.buttonlist.append(self.viewbtn)
        # partyrecord
        self.partyrecordbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)),
                                                           cw.cwpy.msgs["party_record"])
        self.buttonlist.append(self.partyrecordbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((width, 24)),
                                                     cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)

        # additionals
        self.create_addctrlbtn(self.toppanel, self._get_bg(), cw.cwpy.setting.show_additional_party)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(self.addctrlbtn, 0, wx.ALIGN_TOP, 0)
        self.toppanel.SetSizer(sizer)

        self.additionals.append(self.narrow_label)
        self.additionals.append(self.narrow)
        self.additionals.append(self.narrow_type)
        self.additionals.append(self.sort_label)
        self.additionals.append(self.sort)
        self.update_additionals()

        self.update_narrowcondition()

        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickEditBtn, self.editbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickPartyRecordBtn, self.partyrecordbtn)
        self.Bind(wx.EVT_CHOICE, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        seq = self.accels
        self.sortkeydown = []
        for i in range(0, 9):
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
            self.append_addctrlaccelerator(seq)
        cw.util.set_acceleratortable(self, seq)

        self.draw(True)

    def save_views(self, multi: bool) -> None:
        cw.cwpy.setting.show_multipleparties = multi

    def update_additionals(self) -> None:
        Select.update_additionals(self)
        assert self.addctrlbtn
        cw.cwpy.setting.show_additional_party = self.addctrlbtn.GetToggle()

    def _add_topsizer(self) -> None:
        nsizer = wx.BoxSizer(wx.HORIZONTAL)

        nsizer.Add(self.narrow_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(2))
        nsizer.Add(self.narrow, 1, wx.CENTER, 0)
        nsizer.Add(self.narrow_type, 0, wx.CENTER | wx.EXPAND, cw.wins(3))

        nsizer.Add(self.sort_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(3))
        nsizer.Add(self.sort, 0, wx.CENTER | wx.EXPAND, 0)

        self.topsizer.Add(nsizer, 0, wx.EXPAND, 0)

    def _on_narrowcondition(self) -> None:
        cw.cwpy.setting.parties_narrowtype = self.narrow_type.GetSelection()
        self.update_narrowcondition()
        self.draw(True)

    def OnDebugMode(self, event: wx.CommandEvent) -> None:
        def func(self: PartySelect) -> None:
            cw.cwpy.play_sound("page")
            value = not cw.cwpy.is_debugmode()
            cw.cwpy.set_debug(value)

            def func(self: PartySelect) -> None:
                if not self:
                    return
                self.update_debug()
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def update_debug(self) -> None:
        self._on_narrowcondition()

    def update_narrowcondition(self) -> None:
        assert cw.cwpy.ydata
        if 0 <= self.index and self.index < len(self.list):
            selected: Optional[cw.header.PartyHeader] = self.list[self.index]
        else:
            selected = None

        self.list = cw.cwpy.ydata.partys[:]

        narrow = self.narrow.GetValue().lower()
        donarrow = self.narrow.IsShown() and bool(narrow)
        ntype = self.narrow_type.GetSelection()

        if donarrow:
            hiddens = {"＿", "＠"}
            attrs = set(cw.cwpy.setting.periodnames)
            attrs.update(cw.cwpy.setting.sexnames)
            attrs.update(cw.cwpy.setting.naturenames)
            attrs.update(cw.cwpy.setting.makingnames)

            _NARROW_ALL = 0
            _NARROW_NAME = 1
            _NARROW_MEMBER = 2
            _NARROW_DESC = 3
            _NARROW_HISTORY = 4
            _NARROW_FEATURES = 5
            _NARROW_LEVEL = 6

            if ntype in (_NARROW_LEVEL, _NARROW_ALL):
                # レベル
                try:
                    intnarrow: Optional[int] = int(narrow)
                except Exception:
                    intnarrow = None

            ntypes = set()
            if ntype == _NARROW_ALL:
                ntypes.add(_NARROW_NAME)
                ntypes.add(_NARROW_MEMBER)
                ntypes.add(_NARROW_DESC)
                ntypes.add(_NARROW_HISTORY)
                ntypes.add(_NARROW_FEATURES)
                ntypes.add(_NARROW_LEVEL)
            else:
                ntypes.add(ntype)

            seq = []
            for header in self.list:
                def has_membername() -> bool:
                    for mname in header.get_membernames():
                        if narrow in mname.lower():
                            return True
                    return False

                def has_memberdesc() -> bool:
                    for mdesc in header.get_memberdescs():
                        if narrow in mdesc.lower():
                            return True
                    return False

                def has_memberhistory() -> bool:
                    for coupons in header.get_membercoupons():
                        for coupon in coupons:
                            if coupon:
                                if cw.cwpy.is_debugmode():
                                    if coupon[0] == "＿" and coupon[1:] in attrs:
                                        continue
                                else:
                                    if coupon[0] in hiddens:
                                        continue

                                if narrow in coupon.lower():
                                    return True
                    return False

                def has_memberfeatures() -> bool:
                    for coupons in header.get_membercoupons():
                        for coupon in coupons:
                            if coupon and coupon[0] == "＿":
                                coupon = coupon[1:]
                                if coupon in attrs:
                                    if narrow in coupon.lower():
                                        return True
                    return False

                def has_memberlevel() -> bool:
                    if intnarrow is None:
                        return False
                    maxlevel = max(*header.get_memberlevels())
                    minlevel = min(*header.get_memberlevels())
                    return (minlevel <= intnarrow <= maxlevel)

                if (_NARROW_NAME in ntypes and narrow in header.name.lower()) or\
                        (_NARROW_MEMBER in ntypes and has_membername()) or \
                        (_NARROW_DESC in ntypes and has_memberdesc()) or \
                        (_NARROW_HISTORY in ntypes and has_memberhistory()) or \
                        (_NARROW_FEATURES in ntypes and has_memberfeatures()) or \
                        (_NARROW_LEVEL in ntypes and has_memberlevel()):
                    seq.append(header)

            self.list = seq

        if selected in self.list:
            self.index = self.list.index(selected)
        elif self.list:
            self.index %= len(self.list)
        else:
            self.index = 0
        self.enable_btn()

    def _get_bg(self) -> wx.Bitmap:
        if self._bg:
            return self._bg
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self._bg = cw.util.load_wxbmp(path, can_loaded_scaledimage=True)
        return self._bg

    def OnNumberKeyDown(self, event: wx.KeyEvent) -> None:
        """
        数値キー'1'～'9'までの押下を処理する。
        PlayerSelectではソート条件の変更を行う。
        """
        if self._processing:
            return

        if self.sort.IsShown():
            index = self.sortkeydown.index(event.GetId())
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.sort.GetId())
                self.ProcessEvent(event)

    def OnSort(self, event: wx.CommandEvent) -> None:
        assert cw.cwpy.ydata
        if self._processing:
            return

        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "HighestLevel"
        elif index == 3:
            sorttype = "AverageLevel"
        elif index == 4:
            sorttype = "Money"
        else:
            sorttype = "None"

        if cw.cwpy.setting.sort_parties != sorttype:
            cw.cwpy.play_sound("page")
            cw.cwpy.setting.sort_parties = sorttype
            cw.cwpy.ydata.sort_parties()
            self.update_narrowcondition()
            self.draw(True)

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        if self._processing:
            return

        if change_combo(self.narrow_type, event):
            return
        elif change_combo(self.sort, event):
            return
        else:
            MultiViewSelect.OnMouseWheel(self, event)

    def OnClickInfoBtn(self, event: wx.CommandEvent) -> None:
        assert cw.cwpy.ydata
        if not self.list:
            return
        cw.cwpy.play_sound("click")
        header = self.list[self.index]
        party = cw.data.Party(header, True)

        dlg = cw.dialog.edit.PartyEditor(self.Parent, party)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            header = cw.cwpy.ydata.create_partyheader(element=party.data.find("Property"))
            header.data = party
            self.list[self.index] = header
            cw.cwpy.ydata.partys[self.index] = header
            self.draw(True)
        dlg.Destroy()

    def OnClickEditBtn(self, event: wx.CommandEvent) -> None:
        if not self.list:
            return
        partyheader = self.list[self.index]

        def redrawfunc() -> None:
            def func() -> None:
                assert cw.cwpy.ydata
                header = self.list[self.index]
                header = cw.cwpy.ydata.create_partyheader(header.fpath)
                header.data = partyheader.data
                self.list[self.index] = header
                cw.cwpy.ydata.partys[self.index] = header
                cw.cwpy.frame.exec_func(self.draw, True)
            cw.cwpy.exec_func(func)

        cw.cwpy.play_sound("click")
        dlg = cw.dialog.charainfo.StandbyPartyCharaInfo(self.Parent, partyheader, redrawfunc)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def OnClickPartyRecordBtn(self, event: wx.CommandEvent) -> None:
        assert cw.cwpy.ydata
        if self._processing:
            return
        cw.cwpy.play_sound("click")
        dlg = cw.dialog.partyrecord.SelectPartyRecord(self)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        if not (1 < len(dlg.list) or cw.cwpy.ydata.party):
            self.partyrecordbtn.Disable()
        dlg.Destroy()

    def get_selected(self) -> Optional[cw.header.PartyHeader]:
        if self.list:
            return self.list[self.index]
        else:
            return None

    def update_standbys(self, selected: cw.header.PartyHeader) -> None:
        pass

    def can_clickcenter(self) -> bool:
        return self.okbtn.IsEnabled()

    def enable_btn(self) -> None:
        # リストが空だったらボタンを無効化
        assert cw.cwpy.ydata
        if not self.list:
            enables = set()
            if cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord:
                enables.add(self.partyrecordbtn)
            enables.add(self.closebtn)
            self._disable_btn(enables)
        elif len(self.list) == 1:
            self._enable_btn((self.rightbtn, self.right2btn, self.leftbtn, self.left2btn))
        else:
            self._enable_btn()

        if not (cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord):
            self.partyrecordbtn.Disable()

    def draw(self, update: bool = False) -> None:
        assert cw.cwpy.ydata
        dc, dest = self.draw2(update)
        # 背景
        bmp = cw.wins(self._get_bg())
        bmpw = self.toppanel.GetClientSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            self.draw3(dc, dest, update)
            return

        # bmp, bmp_noscale, bmp2, sceheader, imgpaths
        def get_image(header: cw.header.PartyHeader) -> Tuple[List[wx.Bitmap],
                                                              List[wx.Bitmap],
                                                              List[wx.Bitmap],
                                                              Optional[cw.header.ScenarioHeader],
                                                              List[cw.image.ImageInfo]]:
            assert cw.cwpy.ydata
            sceheader = header.get_sceheader()

            if sceheader:
                bmp, bmp_noscale, imgpaths = sceheader.get_wxbmps()
            else:
                if cw.cwpy.ydata.imgpaths:
                    imgpaths = []
                    bmp = []
                    bmp_noscale = []
                    imgpaths = []
                    for info in cw.cwpy.ydata.imgpaths:
                        if not info.path:
                            continue
                        fpath = cw.util.join_paths(cw.cwpy.ydata.yadodir, info.path)
                        bmp_noscale2 = cw.util.load_wxbmp(fpath, True, can_loaded_scaledimage=True)
                        bmp2 = cw.wins(bmp_noscale2)
                        bmp.append(bmp2)
                        bmp_noscale.append(None)
                        imgpaths.append(info)
                        pass
                else:
                    path = "Resource/Image/Card/COMMAND0"
                    path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
                    bmp_noscale = [cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True)]
                    bmp = [cw.wins(bmp_noscale[0])]
                    imgpaths = [cw.image.ImageInfo(path=path)]

            paths = header.get_memberpaths()
            bmp2 = []
            if paths:
                fpath = paths[0]
                fpath = cw.util.get_yadofilepath(fpath)
                if os.path.isfile(fpath):
                    prop = cw.header.GetProperty(fpath)
                    paths2 = cw.image.get_imageinfos_p(prop)
                    for info in paths2:
                        info.path = cw.util.join_yadodir(info.path)
                    can_loaded_scaledimage = cw.util.str2bool(prop.attrs[None].get("scaledimage", "False"))
                    for info in paths2:
                        fpath = info.path
                        if os.path.isfile(fpath):
                            bmp3 = cw.util.load_wxbmp(fpath, True, can_loaded_scaledimage=can_loaded_scaledimage)
                            bmp4 = cw.wins(bmp3)
                            w = bmp4.GetWidth() // 2
                            h = bmp4.GetHeight() // 2
                            if w and h:
                                bmpdepthis1 = hasattr(bmp4, "bmpdepthis1")
                                maskcolour = bmp4.maskcolour if hasattr(bmp4, "maskcolour") else None
                                if bmpdepthis1:
                                    img = cw.util.convert_to_image(bmp4)
                                else:
                                    img = bmp4.ConvertToImage()
                                img = img.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
                                bmp4 = img.ConvertToBitmap()
                                if bmpdepthis1:
                                    bmp4.bmpdepthis1 = bmpdepthis1
                                if maskcolour:
                                    bmp4.maskcolour = maskcolour
                                bmp2.append((bmp3, bmp4, info))
            return bmp, bmp_noscale, bmp2, sceheader, imgpaths

        if self.views == 1:
            # 単独表示
            header = self.list[self.index]
            # 見出し
            dc.SetTextForeground(wx.BLACK)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["adventurers_team"]
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)//2, cw.wins(25))
            # 所持金
            s = cw.cwpy.msgs["adventurers_money"] % (header.money)
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)//2, cw.wins(60))

            # メンバ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
            if update:
                self.names = header.get_membernames()
            if len(header.members) > 3:
                n = (3, len(self.names) - 3)
            else:
                n = (len(self.names), 0)

            w = cw.wins(90)
            maxwidth = w - cw.wins(3)*2

            for index, s in enumerate(self.names):
                if index < 3:
                    cw.util.draw_adjusted(dc, s, (bmpw-w*n[0])//2+w*index, cw.wins(85), maxwidth=maxwidth,
                                          align=wx.ALIGN_CENTER)
                else:
                    cw.util.draw_adjusted(dc, s, (bmpw-w*n[1])//2+w*(index-3), cw.wins(105), maxwidth=maxwidth,
                                          align=wx.ALIGN_CENTER)

            # パーティ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(20)))
            s = header.name
            maxwidth = bmpw - cw.wins(5)*2
            cw.util.draw_adjusted(dc, s, cw.wins(5), cw.wins(40), maxwidth=maxwidth, align=wx.ALIGN_CENTER)
            # シナリオ・宿画像
            bmp, bmp_noscale, bmp2, sceheader, imgpaths = get_image(header)
            ix = (bmpw-cw.wins(74))//2
            iy = cw.wins(125)
            dc.SetClippingRegion(ix, iy, cw.wins(cw.SIZE_CARDIMAGE[0]), cw.wins(cw.SIZE_CARDIMAGE[1]))
            for b, bns, info in zip(bmp, bmp_noscale, imgpaths):
                baserect = info.calc_basecardposition_wx(b.GetSize(), noscale=False,
                                                         basecardtype="Bill",
                                                         cardpostype="NotCard")
                if bns is None:
                    dc.DrawBitmap(b, ix+baserect.x, iy+baserect.y, True)
                else:
                    cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, b, ix+baserect.x, iy+baserect.y, True,
                                                           bitsizekey=bns)
            dc.DestroyClippingRegion()
            # パーティの先頭メンバを小さく表示する
            px = bmpw//2
            py = cw.wins(125+47)
            pw = cw.wins(cw.SIZE_CARDIMAGE[0])
            ph = cw.wins(cw.SIZE_CARDIMAGE[1])
            dc.SetClippingRegion(px, py, pw//2, ph//2)
            for bmp3, bmp4, info in bmp2:
                iw, ih = bmp3.GetSize()
                scr_scale = bmp3.scr_scale if hasattr(bmp3, "scr_scale") else 1
                iw //= scr_scale
                ih //= scr_scale
                baserect = info.calc_basecardposition_wx((iw, ih), noscale=True,
                                                         basecardtype="LargeCard",
                                                         cardpostype="NotCard")
                baserect = cw.wins(baserect)
                baserect.x //= 2
                baserect.y //= 2
                cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, bmp4, px+baserect.x, py+baserect.y, True,
                                                       bitsizekey=bmp3)
            dc.DestroyClippingRegion()

            # シナリオ・宿名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))

            if sceheader:
                s = sceheader.name
            else:
                s = cw.cwpy.ydata.name

            maxwidth = bmpw - cw.wins(5)*2
            cw.util.draw_adjusted(dc, s, cw.wins(5), cw.wins(225), maxwidth=maxwidth, align=wx.ALIGN_CENTER)
            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
            s = s + "/" + str(len(self.list))
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)//2, cw.wins(250))

        else:
            # 一覧表示
            page = self.get_page()

            sindex = page * self.views
            seq = self.list[sindex:sindex+self.views]
            x = 0
            y = 0
            size = self.toppanel.GetSize()
            rw = size[0] // (self.views // 2)
            rh = size[1] // 2
            dc.SetTextForeground(wx.BLACK)
            for i, header in enumerate(seq):
                # 宿・シナリオイメージ
                bmp, bmp_noscale, bmp2, sceheader, imgpaths = get_image(header)
                ix = x + (rw - cw.wins(72)) // 2
                iy = y + cw.s(5)
                dc.SetClippingRegion(ix, iy, cw.wins(cw.SIZE_CARDIMAGE[0]), cw.wins(cw.SIZE_CARDIMAGE[1]))
                for b, bns, info in zip(bmp, bmp_noscale, imgpaths):
                    baserect = info.calc_basecardposition_wx(b.GetSize(), noscale=False,
                                                             basecardtype="Bill",
                                                             cardpostype="NotCard")
                    if bns is None:
                        dc.DrawBitmap(b, ix+baserect.x, iy+baserect.y, True)
                    else:
                        cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, b, ix+baserect.x, iy+baserect.y, True,
                                                               bitsizekey=bns)
                dc.DestroyClippingRegion()
                # パーティの先頭メンバを小さく表示する
                px = ix + cw.wins(37)
                py = iy + cw.wins(47)
                pw = cw.wins(cw.SIZE_CARDIMAGE[0])
                ph = cw.wins(cw.SIZE_CARDIMAGE[1])
                dc.SetClippingRegion(px, py, pw//2, ph//2)
                for bmp3, bmp4, info in bmp2:
                    iw, ih = bmp3.GetSize()
                    scr_scale = bmp3.scr_scale if hasattr(bmp3, "scr_scale") else 1
                    iw //= scr_scale
                    ih //= scr_scale
                    baserect = info.calc_basecardposition_wx((iw, ih), noscale=True,
                                                             basecardtype="LargeCard",
                                                             cardpostype="NotCard")
                    baserect = cw.wins(baserect)
                    baserect.x //= 2
                    baserect.y //= 2
                    cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, bmp4, px+baserect.x, py+baserect.y, True,
                                                           bitsizekey=bmp3)
                dc.DestroyClippingRegion()

                # パーティ名
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = header.name
                maxwidth = rw - cw.wins(3) * 2
                cw.util.draw_witharound(dc, s, x + cw.wins(3), y + cw.wins(105), maxwidth=rw, align=wx.ALIGN_CENTER)

                # シナリオ・宿名
                if sceheader:
                    s = sceheader.name
                    cw.util.draw_witharound(dc, s, x + cw.wins(3), y + cw.wins(120), maxwidth=rw, align=wx.ALIGN_CENTER)

                # 選択マーク
                if sindex + i == self.index:
                    bmp = cw.cwpy.rsrc.wxstatuses["TARGET"]
                    dc.DrawBitmap(bmp, ix + cw.wins(90) - bmp.GetWidth(), iy + cw.wins(102) - bmp.GetHeight(), True)

                if self.views // 2 == i + 1:
                    x = 0
                    y += rh
                else:
                    x += rw

            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = str(page+1) if page > 0 else str(-page + 1)
            s = s + "/" + str(self.get_pagecount())
            cw.util.draw_witharound(dc, s, cw.wins(5), cw.wins(5))

        self.draw3(dc, dest, update)


# ------------------------------------------------------------------------------
# 冒険者選択ダイアログ
# ------------------------------------------------------------------------------

class PlayerSelect(MultiViewSelect[cw.header.AdventurerHeader]):
    """
    冒険者選択ダイアログ。
    """
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログボックス作成
        MultiViewSelect.__init__(self, parent, cw.cwpy.msgs["select_member_title"], wx.ID_ADD, 10,
                                 cw.cwpy.setting.show_multipleplayers)
        self._bg = None

        # 冒険者情報
        self.list = []
        self.isalbum = False
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        self.toppanel.SetMinSize(cw.wins((460, 280)))

        # 絞込条件
        choices = (cw.cwpy.msgs["all"],
                   cw.cwpy.msgs["sort_name"],
                   cw.cwpy.msgs["description"],
                   cw.cwpy.msgs["history"],
                   cw.cwpy.msgs["character_attribute"],
                   cw.cwpy.msgs["sort_level"])
        self._init_narrowpanel(choices, "", cw.cwpy.setting.standbys_narrowtype)

        # sort
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        self.sort_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["sort_title"])
        self.sort_label.SetFont(font)
        choices2 = (cw.cwpy.msgs["sort_no"],
                    cw.cwpy.msgs["sort_name"],
                    cw.cwpy.msgs["sort_level"])
        self.sort = wx.Choice(self, size=(-1, self.narrow.GetBestSize()[1]), choices=choices2)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        if cw.cwpy.setting.sort_standbys == "Name":
            self.sort.Select(1)
        elif cw.cwpy.setting.sort_standbys == "Level":
            self.sort.Select(2)
        else:
            self.sort.Select(0)

        # add
        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_ADD, cw.wins((50, 24)), cw.cwpy.msgs["add_member"])
        self.buttonlist.append(self.addbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["new"])
        self.buttonlist.append(self.newbtn)
        # extension
        self.exbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["extension"])
        self.buttonlist.append(self.exbtn)
        # view
        s = cw.cwpy.msgs["member_list"] if self.views == 1 else cw.cwpy.msgs["member_one"]
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), s)
        self.buttonlist.append(self.viewbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((50, 24)), cw.cwpy.msgs["close"])
        self.buttonlist.append(self.closebtn)

        # additionals
        self.create_addctrlbtn(self.toppanel, self._get_bg(), cw.cwpy.setting.show_additional_player)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(self.addctrlbtn, 0, wx.ALIGN_TOP, 0)
        self.toppanel.SetSizer(sizer)

        self.additionals.append(self.narrow_label)
        self.additionals.append(self.narrow)
        self.additionals.append(self.narrow_type)
        self.additionals.append(self.sort_label)
        self.additionals.append(self.sort)
        self.update_additionals()

        self.update_narrowcondition()

        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickAddBtn, self.addbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExBtn, self.exbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        self.Bind(wx.EVT_CHOICE, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        seq = self.accels
        self.sortkeydown = []
        for i in range(0, 9):
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
            self.append_addctrlaccelerator(seq)
        cw.util.set_acceleratortable(self, seq)

    def save_views(self, multi: bool) -> None:
        cw.cwpy.setting.show_multipleplayers = multi

    def update_additionals(self) -> None:
        Select.update_additionals(self)
        assert self.addctrlbtn
        cw.cwpy.setting.show_additional_player = self.addctrlbtn.GetToggle()

    def _add_topsizer(self) -> None:
        nsizer = wx.BoxSizer(wx.HORIZONTAL)

        nsizer.Add(self.narrow_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(2))
        nsizer.Add(self.narrow, 1, wx.CENTER, 0)
        nsizer.Add(self.narrow_type, 0, wx.CENTER | wx.EXPAND, cw.wins(3))

        nsizer.Add(self.sort_label, 0, wx.LEFT | wx.RIGHT | wx.CENTER, cw.wins(3))
        nsizer.Add(self.sort, 0, wx.CENTER | wx.EXPAND, 0)

        self.topsizer.Add(nsizer, 0, wx.EXPAND, 0)

    def OnDebugMode(self, event: wx.CommandEvent) -> None:
        def func(self: PlayerSelect) -> None:
            cw.cwpy.play_sound("page")
            value = not cw.cwpy.is_debugmode()
            cw.cwpy.set_debug(value)

            def func(self: PlayerSelect) -> None:
                if not self:
                    return
                self.update_debug()
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def update_debug(self) -> None:
        self._on_narrowcondition()

    def _on_narrowcondition(self) -> None:
        if self.narrow_type:
            cw.cwpy.setting.standbys_narrowtype = self.narrow_type.GetSelection()
            self.update_narrowcondition()
            self.draw(True)

    def update_narrowcondition(self) -> None:
        assert cw.cwpy.ydata
        if 0 <= self.index and self.index < len(self.list):
            selected: Optional[cw.header.AdventurerHeader] = self.list[self.index]
        else:
            selected = None

        if self.isalbum:
            self.list = cw.cwpy.ydata.album[:]
        else:
            self.list = cw.cwpy.ydata.standbys[:]

        narrow = self.narrow.GetValue().lower()
        donarrow = self.narrow.IsShown() and bool(narrow)

        if donarrow:
            hiddens = {"＿", "＠"}
            attrs = set(cw.cwpy.setting.periodnames)
            attrs.update(cw.cwpy.setting.sexnames)
            attrs.update(cw.cwpy.setting.naturenames)
            attrs.update(cw.cwpy.setting.makingnames)

            _NARROW_ALL = 0
            _NARROW_NAME = 1
            _NARROW_DESC = 2
            _NARROW_HISTORY = 3
            _NARROW_FEATURES = 4
            _NARROW_LEVEL = 5

            ntype = self.narrow_type.GetSelection()

            if ntype in (_NARROW_LEVEL, _NARROW_ALL):
                # レベル
                try:
                    intnarrow: Optional[int] = int(narrow)
                except Exception:
                    intnarrow = None

            ntypes = set()
            if ntype == _NARROW_ALL:
                ntypes.add(_NARROW_NAME)
                ntypes.add(_NARROW_DESC)
                ntypes.add(_NARROW_HISTORY)
                ntypes.add(_NARROW_FEATURES)
                ntypes.add(_NARROW_LEVEL)
            else:
                ntypes.add(ntype)

            seq = []
            for header in self.list:
                def has_history() -> bool:
                    for coupon in header.history:
                        if coupon:
                            if cw.cwpy.is_debugmode():
                                if coupon[0] == "＿" and coupon[1:] in attrs:
                                    continue
                            else:
                                if coupon[0] in hiddens:
                                    continue

                            if narrow in coupon.lower():
                                return True
                    return False

                def has_features() -> bool:
                    for coupon in header.history:
                        if coupon and coupon[0] == "＿":
                            coupon = coupon[1:]
                            if coupon in attrs:
                                if narrow in coupon.lower():
                                    return True
                    return False

                if (_NARROW_NAME in ntypes and narrow in header.name.lower()) or\
                        (_NARROW_DESC in ntypes and narrow in header.desc.lower()) or\
                        (_NARROW_HISTORY in ntypes and has_history()) or\
                        (_NARROW_FEATURES in ntypes and has_features()) or\
                        (_NARROW_LEVEL in ntypes and intnarrow is not None and header.level == intnarrow):
                    seq.append(header)

            self.list = seq

        if selected in self.list:
            self.index = self.list.index(selected)
        elif self.list:
            self.index %= len(self.list)
        else:
            self.index = 0
        self.enable_btn()

    def OnNumberKeyDown(self, event: wx.KeyEvent) -> None:
        """
        数値キー'1'～'9'までの押下を処理する。
        PlayerSelectではソート条件の変更を行う。
        """
        if self._processing:
            return

        if self.sort.IsShown():
            index = self.sortkeydown.index(event.GetId())
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.sort.GetId())
                self.ProcessEvent(event)

    def enable_btn(self) -> None:
        # リストが空だったらボタンを無効化
        disables = set()
        # 冒険者が6人だったら追加ボタン無効化
        if len(cw.cwpy.get_pcards()) == 6:
            disables.add(self.addbtn)

        if not self.list:
            self._disable_btn((self.newbtn, self.closebtn, self.exbtn, self.viewbtn))
        elif len(self.list) <= self.views:
            disables.update((self.rightbtn, self.right2btn, self.leftbtn, self.left2btn))
            self._enable_btn(disables)
            if not self.list:
                self.index = 0
        else:
            self._enable_btn(disables)

    def OnSort(self, event: wx.CommandEvent) -> None:
        assert cw.cwpy.ydata
        if self._processing:
            return
        if self.isalbum:
            return

        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "Level"
        else:
            sorttype = "None"

        if cw.cwpy.setting.sort_standbys != sorttype:
            cw.cwpy.play_sound("page")
            cw.cwpy.setting.sort_standbys = sorttype
            cw.cwpy.ydata.sort_standbys()
            self.update_narrowcondition()
            self.draw(True)

    def can_clickcenter(self) -> bool:
        assert cw.cwpy.ydata
        return self.addbtn.IsEnabled() or not cw.cwpy.ydata.standbys

    def OnLeftDClick(self, event: wx.MouseEvent) -> None:
        # 一覧表示の場合はダブルクリックで編入
        if self._processing:
            return
        if len(cw.cwpy.get_pcards()) == 6:
            return
        MultiViewSelect.OnLeftDClick(self, event)

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        if self._processing:
            return

        if change_combo(self.narrow_type, event):
            return
        elif change_combo(self.sort, event):
            return
        else:
            MultiViewSelect.OnMouseWheel(self, event)

    def OnSelect(self, event: wx.Event) -> None:
        assert cw.cwpy.ydata
        if self._processing:
            return

        if self.addbtn.IsEnabled():
            if self.views == 1:
                # 一人だけ表示している場合は編入
                if not self.list or len(cw.cwpy.get_pcards()) == 6:
                    return
        elif not cw.cwpy.ydata.standbys and self.newbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.newbtn.GetId())
            self.ProcessEvent(btnevent)
            return

        MultiViewSelect.OnSelect(self, event)

    def OnClickNewBtn(self, event: wx.CommandEvent) -> None:
        if self._processing:
            return
        cw.cwpy.play_sound("click")
        if cw.cwpy.setting.debug:
            title = cw.cwpy.msgs["select_creator"]
            items = [
                (cw.cwpy.msgs["create_normal"], cw.cwpy.msgs["create_normal_description"], self._create_normal, True),
                (cw.cwpy.msgs["create_debug"], cw.cwpy.msgs["create_debug_description"], self._create_debug, True),
            ]
            dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            self._create_normal()

    def _create_normal(self) -> None:
        dlg = cw.dialog.create.AdventurerCreater(self)
        cw.cwpy.frame.move_dlg(dlg)
        self._create_common(dlg)

    def _create_debug(self) -> None:
        dlg = cw.debug.charaedit.CharacterEditDialog(self, create=True)
        cw.cwpy.frame.move_dlg(dlg)
        self._create_common(dlg)

    def _create_common(self, dlg: Union["cw.dialog.create.AdventurerCreater",
                                        cw.debug.charaedit.CharacterEditDialog]) -> None:
        assert cw.cwpy.ydata
        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.play_sound("page")
            header = cw.cwpy.ydata.add_standbys(dlg.fpath)
            # リスト更新
            self.update_narrowcondition()
            if header in self.list:
                self.index = self.list.index(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def get_selected(self) -> Optional[cw.header.AdventurerHeader]:
        if self.list:
            return self.list[self.index]
        else:
            return None

    def update_standbys(self, selected: cw.header.AdventurerHeader) -> None:
        self.update_narrowcondition()

        if selected and selected in self.list:
            self.index = self.list.index(selected)
        else:
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
        self.enable_btn()
        self.draw(True)

    def OnClickAddBtn(self, event: wx.PyCommandEvent) -> None:
        if self._processing:
            return
        self._processing = True

        if not self.list:
            return

        header = self.list[self.index]

        def func(self: PlayerSelect, header: cw.header.AdventurerHeader, index: int) -> None:
            if PlayerSelect._add(header):
                def func(self: PlayerSelect) -> None:
                    if self:
                        self._processing = False
                        self.update_narrowcondition()
                        if len(self.list):
                            self.index %= len(self.list)
                        else:
                            self.index = 0
                        self.enable_btn()
                        self.draw(True)
                        self._update_mousepos()
                cw.cwpy.frame.exec_func(func, self)
            else:
                def func(self: PlayerSelect) -> None:
                    if self:
                        self._processing = False
                cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self, header, self.index)

    @staticmethod
    def _add(header: cw.header.AdventurerHeader) -> bool:
        assert threading.currentThread() == cw.cwpy
        assert cw.cwpy.ydata
        if cw.cwpy.ydata.party:
            if len(cw.cwpy.ydata.party.members) < 6:
                cw.cwpy.play_sound("harvest")
                cw.cwpy.ydata.standbys.remove(header)
                cw.cwpy.ydata.party.add(header)
                if cw.cwpy.areaid == cw.AREA_BREAKUP:
                    cw.cwpy.create_poschangearrow()
                return True
            else:
                # 追加できなかった
                return False
        else:
            cw.cwpy.play_sound("harvest")
            cw.cwpy.ydata.standbys.remove(header)
            cw.cwpy.ydata.create_party(header, chgarea=False)
            return True

    def OnClickExBtn(self, event: wx.CommandEvent) -> None:
        """
        拡張。
        """
        assert cw.cwpy.ydata
        if self._processing:
            return
        cw.cwpy.play_sound("click")
        if self.list:
            name = self.list[self.index].name
            title = cw.cwpy.msgs["extension_title"] % (name)
        else:
            title = cw.cwpy.msgs["extension_title_2"]
        items: Sequence[Union[Tuple[str, str, Callable[[], None], bool],
                              Tuple[str, str, Callable[[], None]]]] = (
            (cw.cwpy.msgs["grow"], cw.cwpy.msgs["grow_adventurer_description"],
             self.grow_adventurer, bool(self.list)),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_adventurer_description"],
             self.delete_adventurer, bool(self.list)),
            (cw.cwpy.msgs["select_party_record"], cw.cwpy.msgs["select_party_record_description"],
             self.select_partyrecord, bool(cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord)),
            (cw.cwpy.msgs["random_character"], cw.cwpy.msgs["random_character_description"],
             self.create_randomadventurer, True),
            (cw.cwpy.msgs["random_team"], cw.cwpy.msgs["random_team_description"],
             self.random_team, bool(cw.cwpy.ydata.standbys and self.addbtn.IsEnabled()))
        )
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def grow_adventurer(self) -> None:
        """冒険者を成長させる。
        """
        assert cw.cwpy.ydata
        header = self.list[self.index]
        age = header.age
        index = cw.cwpy.setting.periodcoupons.index(age)

        if index < 0:
            # 年代が不正。スキンが違う場合は発生しうる
            cw.cwpy.play_sound("error")
            return

        if index == len(cw.cwpy.setting.periodcoupons) - 1:
            nextage = None
            s = cw.cwpy.msgs["confirm_die"] % (header.name)
        else:
            nextage = cw.cwpy.setting.periodcoupons[index + 1]
            s = cw.cwpy.msgs["confirm_grow"] % (header.name, age[1:], nextage[1:])

        cw.cwpy.play_sound("signal")
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            cw.cwpy.play_sound("harvest")
            if nextage:
                header.grow()
            else:
                s = cw.cwpy.msgs["die_message"] % (header.name)
                dlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s, 2)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()

                self._move_allcards(header)
                if not header.leavenoalbum:
                    path = cw.xmlcreater.create_albumpage(header.fpath)
                    cw.cwpy.ydata.add_album(path)
                for partyrecord in cw.cwpy.ydata.partyrecord:
                    partyrecord.vanish_member(header.fpath)
                cw.cwpy.ydata.remove_emptypartyrecord()
                cw.cwpy.remove_xml(header)
                cw.cwpy.ydata.standbys.remove(header)
                for partyrecord in cw.cwpy.ydata.partyrecord:
                    partyrecord.vanish_member(header.fpath)
                cw.cwpy.ydata.remove_emptypartyrecord()
                self.update_narrowcondition()
                if len(self.list):
                    self.index %= len(self.list)
                else:
                    self.index = 0
                self.enable_btn()

            self.draw(True)
        else:
            dlg.Destroy()

    def delete_adventurer(self) -> None:
        """冒険者を削除する。
        """
        cw.cwpy.play_sound("signal")
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.play_sound("dump")
            self._delete_adventurer(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def _move_allcards(self, header: cw.header.AdventurerHeader) -> None:
        # 全ての手札カードをカード置場へ移動する
        assert cw.cwpy.ydata
        data = cw.data.yadoxml2etree(header.fpath)
        ccard = cw.character.Character(data)
        for pocket in ccard.cardpocket:
            for card in pocket[:]:
                cw.cwpy.trade("STOREHOUSE", header=card, from_event=True, sort=False)
        cw.cwpy.ydata.sort_storehouse()

    def _delete_adventurer(self, header: cw.header.AdventurerHeader) -> None:
        assert cw.cwpy.ydata
        cw.cwpy.ydata.changed()
        self._move_allcards(header)

        # レベル3以上・"＿消滅予約"を持ってない場合、アルバムに残す
        if header.level >= 3 and not header.leavenoalbum:
            path = cw.xmlcreater.create_albumpage(header.fpath, nocoupon=True)
            cw.cwpy.ydata.add_album(path)

        for partyrecord in cw.cwpy.ydata.partyrecord:
            partyrecord.vanish_member(header.fpath)
        cw.cwpy.ydata.remove_emptypartyrecord()
        cw.cwpy.remove_xml(header)
        cw.cwpy.ydata.standbys.remove(header)
        for partyrecord in cw.cwpy.ydata.partyrecord:
            partyrecord.vanish_member(header.fpath)
        cw.cwpy.ydata.remove_emptypartyrecord()
        self.update_narrowcondition()
        if len(self.list):
            self.index %= len(self.list)
        else:
            self.index = 0

    def select_partyrecord(self) -> None:
        """編成記録ダイアログを開く。
        """
        cw.cwpy.play_sound("click")
        dlg = cw.dialog.partyrecord.SelectPartyRecord(self)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def random_team(self) -> None:
        """ランダムな編成のチームを組む。
        """
        if self._processing:
            return
        self._processing = True

        def func(panel: PartySelect) -> None:
            class Pocket(object):
                def __init__(self, header: cw.header.AdventurerHeader, point: int) -> None:
                    self.header = header
                    self.point = point
            assert cw.cwpy.ydata

            while cw.cwpy.ydata.standbys and (not cw.cwpy.ydata.party or
                                              len(cw.cwpy.ydata.party.members) < 6):
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                if not cw.cwpy.ydata.party:
                    PlayerSelect._add(cw.cwpy.dice.choice_exists(cw.cwpy.ydata.standbys))
                else:
                    seq = self.calc_needs(cw.cwpy.ydata.standbys)
                    seq2 = []
                    for need, header in cw.cwpy.dice.shuffle(seq):
                        point = cw.cwpy.dice.roll(1, need)
                        seq2.append(Pocket(header, point))
                    cw.util.sort_by_attr(seq2, "point")
                    PlayerSelect._add(seq2[0].header)

            def func(panel: PartySelect) -> None:
                if panel:
                    panel._processing = False
                    panel.update_narrowcondition()
                    if len(panel.list):
                        panel.index %= len(panel.list)
                    else:
                        panel.index = 0
                    panel.enable_btn()
                    panel.draw(True)
            cw.cwpy.frame.exec_func(func, panel)
        cw.cwpy.exec_func(func, self)

    def create_randomadventurer(self) -> None:
        """ランダムな特性を持つキャラクターを生成する。
        """
        assert cw.cwpy.ydata
        if self._processing:
            return
        self._processing = True
        cw.cwpy.play_sound("signal")
        info = cw.debug.charaedit.CharaInfo(None, debug_coupon=False)
        info.set_randomfeatures()
        fpath = info.create_adventurer(setlevel=False)
        header = cw.cwpy.ydata.add_standbys(fpath)

        # リスト更新
        self.narrow.SetValue("")
        self.update_narrowcondition()
        if header in self.list:
            self.index = self.list.index(header)
        chgviews = self.views != 1
        if chgviews:
            self.change_view()
        self.draw(True)

        # *Names.txtファイルがある時は初期名を決める
        sex = header.get_sex()
        randomname = cw.dialog.create.get_randomname(sex)

        def random_name() -> str:
            return cw.dialog.create.get_randomname(sex)
        addition = cw.cwpy.msgs["auto"] if cw.cwpy.setting.show_autobuttoninentrydialog else ""
        addition_func = random_name if cw.cwpy.setting.show_autobuttoninentrydialog else None

        dlg = cw.dialog.edit.InputTextDialog(self, cw.cwpy.msgs["naming"],
                                             cw.cwpy.msgs["naming_random_character"],
                                             text=randomname,
                                             maxlength=14,
                                             addition=addition,
                                             addition_func=addition_func)
        self.Parent.move_dlg(dlg, point=(cw.wins(130), cw.wins(0)))
        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            cw.cwpy.play_sound("harvest")
            data = cw.data.yadoxml2etree(header.fpath)
            ccard = cw.character.Character(data)
            ccard.set_name(dlg.text)
            ccard.data.is_edited = True
            ccard.data.write_xml()
            header.name = dlg.text
        else:
            cw.cwpy.play_sound("dump")
            self._delete_adventurer(header)

        dlg.Destroy()

        if chgviews:
            self.change_view()
        self.draw(True)
        self.enable_btn()

        self._processing = False

    def OnClickInfoBtn(self, event: wx.CommandEvent) -> None:
        from . import charainfo

        if self._processing:
            return
        cw.cwpy.play_sound("click")
        header = self.list[self.index]
        assert isinstance(header, cw.header.AdventurerHeader)
        data = cw.data.yadoxml2etree(header.fpath)
        if data.getroot().tag == "Album":
            album = cw.character.AlbumPage(data)
            dlg = charainfo.StandbyCharaInfo[cw.character.AlbumPage](self, self.list, album, self.index,
                                                                     self.update_character)
        else:
            ccard = cw.character.Player(data)
            dlg = charainfo.StandbyCharaInfo[cw.character.Player](self, self.list, ccard, self.index,
                                                                  self.update_character)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_character(self) -> None:
        def func() -> None:
            assert cw.cwpy.ydata
            header = self.list[self.index]
            order = header.order
            if self.isalbum:
                index = cw.cwpy.ydata.album.index(header)
                header = cw.cwpy.ydata.create_advheader(header.fpath)
                header.order = order
                cw.cwpy.ydata.album[index] = header
            else:
                index = cw.cwpy.ydata.standbys.index(header)
                header = cw.cwpy.ydata.create_advheader(header.fpath)
                header.order = order
                cw.cwpy.ydata.standbys[index] = header
            self.list[self.index] = header
            self.update_narrowcondition()
            cw.cwpy.frame.exec_func(self.draw, True)
        cw.cwpy.exec_func(func)

    def calc_needs(self, mlist: Sequence[cw.header.AdventurerHeader]) -> List[Tuple[int, cw.header.AdventurerHeader]]:
        """mlist内のメンバに対して、現在のパーティの構成から
        パーティにおける必要度を計算する。
        レベルが近く、同型のメンバが少ないほど必要度が高くなる。
        """
        assert cw.cwpy.ydata
        if cw.cwpy.ydata.party:
            talents = set(cw.cwpy.setting.naturecoupons)
            types: Dict[str, int] = {}
            level = 0.0
            seq = []
            for member in cw.cwpy.get_pcards():
                level += member.level
                talent = member.get_talent()
                val = types.get(talent, 0)
                val += 1
                types[talent] = val
            level //= len(cw.cwpy.ydata.party.members)

            for header in mlist:
                # 同型のメンバの数だけ必要度を下げる
                need = 10
                talent = cw.cwpy.setting.naturecoupons[0]
                for coupon in header.history:
                    if coupon in talents:
                        talent = coupon
                        break
                val = types.get(talent, 0)
                for _i in range(val):
                    need *= 2

                # レベルが離れているほど必要度を下げる
                val = level - header.level
                if val < 0:
                    val = -val
                for _i in range(int(val+0.5)):
                    need *= 4
                seq.append((int(need), header))
            return seq
        else:
            return [(10, header) for header in mlist]

    def _get_bg(self) -> wx.Bitmap:
        if self._bg:
            return self._bg
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        self._bg = cw.util.load_wxbmp(path, can_loaded_scaledimage=True)
        return self._bg

    def draw(self, update: bool = False) -> None:
        dc, dest = self.draw2(update)
        # 背景
        bmp = cw.wins(self._get_bg())
        bmpw = self.toppanel.GetClientSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        if self.list:
            if self.views == 1:
                PROFILE_LINES = 4
                if 0 < PROFILE_LINES:
                    xpos = cw.wins(8)
                else:
                    xpos = cw.wins(15)

                header = self.list[self.index % len(self.list)]
                # Level
                dc.SetTextForeground(wx.BLACK)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_level"]
                w = dc.GetTextExtent(s)[0]
                if header.level < 10:
                    dc.DrawText(s, cw.wins(44)+xpos, cw.wins(42))
                    w = w + 5
                else:
                    dc.DrawText(s, cw.wins(39)+xpos, cw.wins(42))
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(25)))
                s = str(header.level)
                y = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(45)+xpos + w, cw.wins(34))
                w = w + y
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_class"]
                dc.DrawText(s, cw.wins(50)+xpos + w, cw.wins(42))
                # Name
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(22)))
                s = header.name
                maxwidth = cw.wins(140) - cw.wins(5)*2
                cw.util.draw_adjusted(dc, s, xpos + cw.wins(45), cw.wins(67), maxwidth=maxwidth,
                                      align=wx.ALIGN_CENTER)
                # Image
                dc.SetClippingRegion(cw.wins(73)+xpos, cw.wins(90), cw.wins(74), cw.wins(94))
                attr = cw.header.GetRootAttribute(header.fpath).attrs.get("scaledimage", "False")
                can_loaded_scaledimage = cw.util.str2bool(attr)
                for info in header.imgpaths:
                    path = cw.util.join_yadodir(info.path)
                    bmp = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                    bmp2 = cw.wins(bmp)

                    baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                             basecardtype="LargeCard",
                                                             cardpostype="NotCard")

                    cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, bmp2, cw.wins(73)+xpos+baserect.x,
                                                           cw.wins(90)+baserect.y, True, bitsizekey=bmp)
                dc.DestroyClippingRegion()
                # Age
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_age"] % (header.get_age())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(112)+xpos - w // 2, cw.wins(195))
                # Sex
                s = cw.cwpy.msgs["character_sex"] % (header.get_sex())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(112)+xpos - w // 2, cw.wins(210))
                # EP
                s = cw.cwpy.msgs["character_ep"] % (header.ep)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(112)+xpos - w // 2, cw.wins(225))

                # 解説
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
                cpos = cw.wins(190) + dc.GetTextExtent("#"*36)[0]*0.85//2
                if 0 < PROFILE_LINES:
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(14)))
                    s = cw.cwpy.msgs["character_profile"]
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, cpos - w // 2, cw.wins(42))
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
                    desc: List[str] = []
                    for s in cw.util.txtwrap(header.desc, 4).rstrip().splitlines():
                        if PROFILE_LINES < len(desc):
                            desc[-1] = cw.util.abbr_longstr_with_count(desc[-1]+"...", 37)
                            break
                        desc.append(s)
                    for index, s in enumerate(desc):
                        cw.util.draw_antialiasedtext(dc, s, cw.wins(190), cw.wins(63) + cw.wins(14) * index,
                                                     False, cw.wins(315), cw.wins(0), scaledown=False,
                                                     width_coeff=0.85, quality=wx.IMAGE_QUALITY_BILINEAR)

                    hist_tpos = cw.wins(65+PROFILE_LINES*14) + cw.wins(27)
                    hist_pos = hist_tpos+cw.wins(21)
                    hist_num = 8 - PROFILE_LINES
                else:
                    hist_tpos = cw.wins(65)
                    hist_pos = cw.wins(95)
                    hist_num = 9

                # クーポン(新しい順から9つ)
                hiddens = {"＿", "＠"}
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_history"]
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cpos - w // 2, hist_tpos)

                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
                history: List[str] = []
                for s in header.history:
                    if s and not s[0] in hiddens:
                        if hist_num < len(history):
                            history[-1] = cw.cwpy.msgs["history_etc"]
                            break
                        history.append(s)
                for index, s in enumerate(history):
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, cpos - w // 2, hist_pos + cw.wins(14) * index)

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
                s = s + "/" + str(len(self.list))
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)//2, cw.wins(250))
            else:
                page = self.get_page()

                sindex = page * self.views
                seq = self.list[sindex:sindex+self.views]
                x = 0
                y = 0
                size = self.toppanel.GetSize()
                rw = size[0] // (self.views // 2)
                rh = size[1] // 2
                dc.SetTextForeground(wx.BLACK)
                for i, header in enumerate(seq):
                    # Image
                    ix = x + (rw - cw.wins(72)) // 2
                    iy = y + 5
                    dc.SetClippingRegion(ix, iy, cw.wins(74), cw.wins(94))
                    attr = cw.header.GetRootAttribute(header.fpath).attrs.get("scaledimage", "False")
                    can_loaded_scaledimage = cw.util.str2bool(attr)
                    for info in header.imgpaths:
                        path = cw.util.join_yadodir(info.path)
                        bmp = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                        bmp2 = cw.wins(bmp)
                        baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                                 basecardtype="LargeCard",
                                                                 cardpostype="NotCard")
                        cw.imageretouch.wxblit_2bitbmp_to_card(dc, dest, bmp2, ix+baserect.x, iy+baserect.y, True,
                                                               bitsizekey=bmp)
                    dc.DestroyClippingRegion()

                    # Name
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    s = header.name
                    maxwidth = rw - cw.wins(3)*2
                    cw.util.draw_witharound(dc, s, x+cw.wins(3), y + cw.wins(105), maxwidth=maxwidth,
                                            align=wx.ALIGN_CENTER)
                    # Level
                    space = cw.wins(5)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    s1 = cw.cwpy.msgs["character_level"]
                    w1, h1 = dc.GetTextExtent(s1)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))
                    s2 = str(header.level)
                    w2, h2 = dc.GetTextExtent(s2)
                    sx = x + (rw - (w1+cw.wins(5)+w2+space)) // 2
                    sy = y + cw.wins(120)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    cw.util.draw_witharound(dc, s1, sx, sy + (h2-h1))
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))
                    cw.util.draw_witharound(dc, s2, sx + w1 + space + cw.wins(5), sy)
                    # Selected
                    if sindex + i == self.index:
                        bmp = cw.cwpy.rsrc.wxstatuses["TARGET"]
                        dc.DrawBitmap(bmp, ix + cw.wins(80) - bmp.GetWidth(), iy + cw.wins(102) - bmp.GetHeight(), True)

                    if self.views // 2 == i + 1:
                        x = 0
                        y += rh
                    else:
                        x += rw

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = str(page+1) if page > 0 else str(-page + 1)
                s = s + "/" + str(self.get_pagecount())
                cw.util.draw_witharound(dc, s, cw.wins(5), cw.wins(5))

        self.draw3(dc, dest, update)


# ------------------------------------------------------------------------------
# アルバムダイアログ
# ------------------------------------------------------------------------------

class Album(PlayerSelect):
    """
    アルバムダイアログ。
    冒険者選択ダイアログを継承している。
    """
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログボックス作成
        Select.__init__(self, parent, cw.cwpy.msgs["album"])
        assert cw.cwpy.ydata
        self._bg = None
        # 冒険者情報
        self.list = cw.cwpy.ydata.album
        self.isalbum = True
        self.index = 0
        self.views = 1
        self.sort = None
        self.narrow_type = None
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_PROPERTIES, cw.wins((90, 24)),
                                                    cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # delete
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DELETE, cw.wins((90, 24)), cw.cwpy.msgs["delete"])
        self.buttonlist.append(self.delbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((90, 24)), cw.cwpy.msgs["close"])
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDelBtn, self.delbtn)

    def can_clickcenter(self) -> bool:
        return False

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        Select.OnMouseWheel(self, event)

    def _add_topsizer(self) -> None:
        pass

    def update_narrowcondition(self) -> None:
        pass

    def OnClickDelBtn(self, event: wx.CommandEvent) -> None:
        assert cw.cwpy.ydata
        cw.cwpy.play_sound("signal")
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character_in_album"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.play_sound("dump")
            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.album.remove(header)
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def enable_btn(self) -> None:
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn((self.closebtn,))
        elif len(self.list) == 1:
            self._enable_btn((self.rightbtn, self.right2btn, self.leftbtn, self.left2btn))
        else:
            self._enable_btn()

    def OnSelect(self, event: wx.Event) -> None:
        pass


def change_combo(combo: wx.Choice, event: wx.MouseEvent) -> bool:
    if combo and combo.IsShown() and combo.GetRect().Contains(event.GetPosition()):
        index = combo.GetSelection()
        count = combo.GetCount()
        if cw.util.get_wheelrotation(event) > 0:
            if index <= 0:
                index = count - 1
            else:
                index -= 1
        else:
            if count <= index + 1:
                index = 0
            else:
                index += 1
        combo.Select(index)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, combo.GetId())
        combo.ProcessEvent(btnevent)
        return True
    else:
        return False


def main() -> None:
    pass


if __name__ == "__main__":
    main()
