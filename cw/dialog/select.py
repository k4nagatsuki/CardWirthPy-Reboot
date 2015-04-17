#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import threading
import shutil
import subprocess
import wx

import cw
import message
import charainfo
import text

from cw.util import synclock


_lockupdatescenario = threading.Lock()

#-------------------------------------------------------------------------------
#　選択ダイアログ スーパークラス
#-------------------------------------------------------------------------------

class Select(wx.Dialog):
    def __init__(self, parent, name):
        wx.Dialog.__init__(self, parent, -1, name,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self._processing = False
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # buttonlist
        self.buttonlist = []
        # leftjump
        bmp = cw.cwpy.rsrc.buttons["LJUMP"]
        self.left2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp)
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.wins((30, 30)), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.wins((30, 30)), bmp=bmp)
        # rightjump
        bmp = cw.cwpy.rsrc.buttons["RJUMP"]
        self.right2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp)
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
            (wx.ACCEL_CTRL|wx.ACCEL_ALT, wx.WXK_LEFT, self.left2keyid),
            (wx.ACCEL_CTRL|wx.ACCEL_ALT, wx.WXK_RIGHT, self.right2keyid),
        ]
        self.accels = seq
        cw.util.set_acceleratortable(self, seq)

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeft2Btn, self.left2btn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRight2Btn, self.right2btn)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        def empty(event):
            pass
        self.toppanel.Bind(wx.EVT_ERASE_BACKGROUND, empty)
        self.toppanel.Bind(wx.EVT_MIDDLE_DOWN, self.OnMouseDown)
        self.toppanel.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.toppanel.Bind(wx.EVT_MIDDLE_UP, self.OnSelectBase)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnSelectBase)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMotion)

        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            buttonlist[0].SetFocus()

    def OnPrevButton(self, event):
        focus = wx.Window.FindFocus()
        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            if focus in buttonlist:
                index = buttonlist.index(focus)
                buttonlist[index-1].SetFocus()
            else:
                buttonlist[-1].SetFocus()

    def OnNextButton(self, event):
        focus = wx.Window.FindFocus()
        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            if focus in buttonlist:
                index = buttonlist.index(focus)
                buttonlist[(index+1) % len(buttonlist)].SetFocus()
            else:
                buttonlist[0].SetFocus()

    def OnMotion(self, evt):
        self._update_mousepos()

    def _update_mousepos(self):
        if not self.can_clickside():
            if self.can_clickcenter():
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            else:
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])
            self.clickmode = 0
            return

        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        if x < rect.x + rect.width / 4 and self.leftbtn.IsEnabled():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_BACK"])
            self.clickmode = wx.LEFT
        elif rect.x + rect.width / 4 * 3 < x and self.rightbtn.IsEnabled():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FORE"])
            self.clickmode = wx.RIGHT
        else:
            if self.can_clickcenter():
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            else:
                self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])
            self.clickmode = 0

    def OnClickLeftBtn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.index_changed()

    def OnClickLeft2Btn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        elif self.index - 10 < 0:
            self.index = 0
        else:
            self.index -= 10

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.index_changed()

    def OnClickRightBtn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.index_changed()

    def OnClickRight2Btn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        elif self.index + 10 > len(self.list) -1:
            self.index = len(self.list) -1
        else:
            self.index += 10

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.index_changed()

    def index_changed(self):
        pass

    def OnMouseWheel(self, event):
        if not self.list or len(self.list) == 1:
            return

        if event.GetWheelRotation() > 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
            self.ProcessEvent(btnevent)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
            self.ProcessEvent(btnevent)

    def OnMouseDown(self, event):
        self._downbutton = event.GetButton()

    def OnSelectBase(self, event):
        if self._processing:
            return
        if self._downbutton <> event.GetButton():
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

    def OnSelect(self, event):
        if not self.list:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if not self.toppanel.IsShown():
            return None

        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetSize())
        else:
            dc = wx.BufferedPaintDC(self.toppanel)

        return dc

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        sizer_panel.Add(self.left2btn, 0, 0, 0)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)

        # button間のマージン値を求める
        width = self.toppanel.GetClientSize()[0] - cw.wins(6)
        btnwidth = cw.wins(120) + self.buttonlist[0].GetSize()[0] * len(self.buttonlist)
        margin = (width - btnwidth) / (len(self.buttonlist)+1)

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_panel.Add((margin, 0), 0, 0, 0)
            sizer_panel.Add(button, 0, wx.TOP|wx.BOTTOM, cw.wins(3))

        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        sizer_panel.Add(self.right2btn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.toppanel, 1, wx.EXPAND, 0)
        self._add_topsizer()

        sizer_1.Add(self.topsizer, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _add_topsizer(self):
        pass

    def _disable_btn(self):
        self.left2btn.Disable()
        self.leftbtn.Disable()
        self.rightbtn.Disable()
        self.right2btn.Disable()

        for btn in self.buttonlist:
            btn.Disable()

    def _enable_btn(self):
        self.left2btn.Enable()
        self.leftbtn.Enable()
        self.rightbtn.Enable()
        self.right2btn.Enable()

        for btn in self.buttonlist:
            btn.Enable()

    def can_clickcenter(self):
        """パネルの中央部分をクリックで決定可能ならTrue。"""
        return True

    def can_clickside(self):
        """パネルの左右クリックでページ切替可能ならTrue。"""
        return True

    def _init_narrowpanel(self, choices, narrowtext, narrowtype, tworows=False):
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15), weight=wx.NORMAL)
        if tworows:
            self.keyword_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_keyword"])
            self.keyword_label.SetFont(font)
        else:
            self.narrow_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_condition"])
            self.narrow_label.SetFont(font)
        self.narrow = wx.TextCtrl(self, -1, size=(cw.wins(0), -1))
        self.narrow.SetFont(font)
        self.narrow.SetValue(narrowtext)
        if tworows:
            self.narrow_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["narrow_condition2"])
            self.narrow_label.SetFont(font)
        cfont = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14), weight=wx.NORMAL)
        self.narrow_type = wx.Choice(self, -1, size=(-1, -1), choices=choices)
        self.narrow_type.SetFont(cfont)
        self.narrow_type.SetSelection(narrowtype)

        self.narrow.Bind(wx.EVT_TEXT, self.OnNarrowCondition)
        self.narrow_type.Bind(wx.EVT_CHOICE, self.OnNarrowCondition)

    def OnNarrowCondition(self, event):
        if self._processing:
            return
        cw.cwpy.sounds["page"].play()
        # 日本語入力で一度に何度もイベントが発生する
        # 事があるので絞り込み実施を遅延する
        self._reserved_narrowconditin = True
        if wx.Window.FindFocus() <> self.narrow:
            self.toppanel.SetFocus()
        def func():
            if not self._reserved_narrowconditin:
                return
            self._on_narrowcondition()
            self._reserved_narrowconditin = False
        wx.CallAfter(func)

    def _on_narrowcondition(self):
        pass

#-------------------------------------------------------------------------------
#　宿選択ダイアログ
#-------------------------------------------------------------------------------

class YadoSelect(Select):
    """
    宿選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, cw.cwpy.msgs["select_base_title"])
        # 宿情報
        self.names, self.list, self.list2, self.skins, self.classic, self.isshortcuts = self.get_yadolist()
        self.index = 0
        for index, name in enumerate(self.names):
            if cw.cwpy.setting.lastyado == name:
                self.index = index
                break
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((400, 370)))
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, cw.wins((50, 24)), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.okbtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["new"])
        self.buttonlist.append(self.newbtn)
        # extend
        self.extbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), u"変換")
        self.buttonlist.append(self.extbtn)
        # extension
        self.exbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["extension"])
        self.buttonlist.append(self.exbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((50, 24)), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)
        # enable bottun
        self.enable_btn()
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExtBtn, self.extbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExBtn, self.exbtn)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)

    def index_changed(self):
        Select.index_changed(self)
        self.enable_btn()
        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            buttonlist[0].SetFocus()

    def can_clickcenter(self):
        return (self.okbtn.IsEnabled() or (self.list and self.classic[self.index])) and os.path.isdir(self.list[self.index])

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.extbtn.Enable()
            self.newbtn.Enable()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

        if self.list and (self.classic[self.index] or cw.util.exists_mutex(self.list[self.index]) or not os.path.isdir(self.list[self.index])):
            self.okbtn.Disable()

    def OnSelect(self, event):
        if not self.list:
            return

        if self.classic[self.index]:
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.extbtn.GetId())
            self.ProcessEvent(event)
        elif self.okbtn.IsEnabled():
            Select.OnSelect(self, event)

    def OnDropFiles(self, event):
        if cw.util.create_mutex(cw.tempdir_init):
            try:
                paths = event.GetFiles()

                for path in paths:
                    self.conv_yado(path)
                    time.sleep(0.3)
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def OnClickExBtn(self, event):
        """
        拡張。
        """
        cw.cwpy.sounds["click"].play()
        yname = self.names[self.index]
        title = cw.cwpy.msgs["extension_title"] % (yname)
        classic = self.classic[self.index]
        hasmutexlocal = not cw.util.exists_mutex(self.list[self.index]) and os.path.isdir(self.list[self.index])
        cantransfer = bool(1 < self.classic.count(False) and os.path.isdir(self.list[self.index]))
        if cantransfer:
            for i, path in enumerate(self.list):
                if not self.classic[i] and cw.util.exists_mutex(path):
                    cantransfer = False
                    break

        items = [
            (cw.cwpy.msgs["rename"], cw.cwpy.msgs["rename_base_description"], self.rename_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["copy"], cw.cwpy.msgs["copy_base_description"], self.copy_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["transfer"], cw.cwpy.msgs["transfer_base_description"], self.trasnfer_yadodata, cantransfer),
            (u"逆変換", u"選択中の拠点データをCardWirth用のデータに逆変換します。", self.unconv_yado, not classic and hasmutexlocal),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_base_description"], self.delete_yado, hasmutexlocal),
        ]
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def rename_yado(self):
        """
        宿改名。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex(self.list[self.index]):
            try:
                cw.cwpy.sounds["click"].play()
                path = self.list[self.index]
                dlg = cw.dialog.edit.YadoEditDialog(self, path)
                cw.cwpy.frame.move_dlg(dlg)

                if dlg.ShowModal() == wx.ID_OK:
                    cw.cwpy.sounds["harvest"].play()
                    cw.util.remove(cw.util.join_paths(u"Data/Temp/Local", path))
                    self.update_list(dlg.yadodir)

                dlg.Destroy()
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def copy_yado(self):
        """
        宿複製。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex(self.list[self.index]):
            try:
                cw.cwpy.sounds["signal"].play()
                path = self.list[self.index]
                yname = self.names[self.index]
                s = cw.cwpy.msgs["copy_base"] % (yname)
                dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                cw.cwpy.frame.move_dlg(dlg)

                if dlg.ShowModal() == wx.ID_OK:
                    env = cw.util.join_paths(path, "Environment.xml")
                    data = cw.data.xml2etree(env)
                    name = data.gettext("Property/Name", os.path.basename(path))
                    name = u"コピー - %s" % (name)
                    if not data.find("Property/Name") is None:
                        data.edit("Property/Name", name)
                    else:
                        e = data.make_element("Name", name)
                        data.insert("Property", e, 0)

                    newpath = cw.binary.util.check_filename(name)
                    newpath = cw.util.join_paths(os.path.dirname(path), newpath)
                    newpath = cw.binary.util.check_duplicate(newpath)
                    shutil.copytree(path, newpath)
                    env = cw.util.join_paths(newpath, "Environment.xml")
                    data.write(env)
                    cw.cwpy.sounds["harvest"].play()
                    self.update_list(newpath)

                dlg.Destroy()
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def trasnfer_yadodata(self):
        """
        宿のデータのコピー。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex(cw.tempdir_init):
            try:
                mutexes = 0
                for path in self.list:
                    if cw.util.create_mutex(path):
                        mutexes += 1
                    else:
                        break
                draw = False
                try:
                    if mutexes <> len(self.list):
                        cw.cwpy.sounds["error"].play()
                        return
                    path = self.list[self.index]
                    dirs = []
                    names = []
                    for i, dname in enumerate(self.list):
                        if not self.classic[i]:
                            dirs.append(dname)
                            names.append(self.names[i])
                    if names:
                        cw.cwpy.sounds["click"].play()
                        dlg = cw.dialog.transfer.TransferYadoDataDialog(self, dirs, names, path)
                        cw.cwpy.frame.move_dlg(dlg)
                        if dlg.ShowModal() == wx.ID_OK:
                            self.names, self.list, self.list2, self.skins, self.classic, self.isshortcuts = self.get_yadolist()
                            self.index = self.list.index(path)
                            draw = True
                        dlg.Destroy()
                finally:
                    for i in xrange(mutexes):
                        cw.util.release_mutex()
                if draw:
                    self.draw(True)
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def delete_yado(self):
        """
        宿削除。
        """
        if not os.path.isdir(self.list[self.index]):
            return
        if cw.util.create_mutex(self.list[self.index]):
            try:
                cw.cwpy.sounds["signal"].play()
                path = self.list[self.index]
                if self.isshortcuts[self.index]:
                    yname = u"%sへのショートカット" % (self.names[self.index])
                else:
                    yname = self.names[self.index]
                s = cw.cwpy.msgs["delete_base"] % (yname)
                dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
                cw.cwpy.frame.move_dlg(dlg)

                if dlg.ShowModal() == wx.ID_OK:
                    if self.isshortcuts[self.index]:
                        cw.util.remove(self.isshortcuts[self.index])
                    else:
                        cw.util.remove(path)
                    if not self.classic[self.index]:
                        cw.util.remove(cw.util.join_paths(u"Data/Temp/Local", path))
                    cw.cwpy.sounds["dump"].play()
                    self.update_list()

                dlg.Destroy()
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def OnClickNewBtn(self, event):
        """
        宿新規作成。
        """
        cw.cwpy.sounds["click"].play()
        dlg = cw.dialog.create.YadoCreater(self)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["harvest"].play()
            self.update_list(dlg.yadodir)

        dlg.Destroy()

    def OnClickExtBtn(self, evt):
        """
        CardWirthの宿データを変換。
        """
        if cw.util.create_mutex(cw.tempdir_init):
            try:
                if self.list and self.classic[self.index]:
                    self._convert_current()
                    return
                # ディレクトリ選択ダイアログ
                s = (u"CardWirthの宿のデータをCardWirthPy用に変換します。" +
                      u"\n変換する宿のフォルダを選択してください。")
                dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
                dlg.SetPath(os.getcwdu())

                if dlg.ShowModal() == wx.ID_OK:
                    path = dlg.GetPath()
                    dlg.Destroy()
                    self.conv_yado(path)
                else:
                    dlg.Destroy()
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.sounds["error"].play()

    def _convert_current(self):
        if not (self.list and self.classic[self.index]):
            return
        yname = self.names[self.index]
        s = u"%sをCardWirthPy用に変換します。\nよろしいですか？" % yname
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.Parent.move_dlg(dlg)
        cw.cwpy.sounds["click"].play()
        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            path = self.list[self.index]
            self.conv_yado(path, ok=True, moveconverted=True, deletepath=self.isshortcuts[self.index])
        else:
            dlg.Destroy()

    def draw(self, update=False):
        dc = Select.draw(self, update)

        if self.list:
            skindir = self.skins[self.index]
        else:
            skindir = cw.cwpy.skindir

        # 背景
        path = "Table/Bill"
        path = cw.util.find_resource(cw.util.join_paths(skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins((cw.util.load_wxbmp(path), cw.SIZE_BILL))
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        if self.classic[self.index]:
            # 変換が必要な場合
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16)))
            dc.SetTextForeground(wx.RED)
            s = u"変換が必要です"
            w = dc.GetTextExtent(s)[0]
            if self.isshortcuts[self.index]:
                dc.DrawText(s, (bmpw-w)/2, cw.wins(12))
            else:
                dc.DrawText(s, (bmpw-w)/2, cw.wins(20))

        # 宿画像
        path = "Resource/Image/Card/COMMAND0"
        path = cw.util.find_resource(cw.util.join_paths(skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))
        dc.DrawBitmap(bmp, (bmpw-cw.wins(74))/2, cw.wins(70), True)
        # 宿名前
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(22)))
        s = self.names[self.index]
        w = dc.GetTextExtent(s)[0]
        if self.isshortcuts[self.index]:
            dc.DrawText(s, (bmpw-w)/2, cw.wins(30))
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(12)))
            s = u"ショートカット"
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(56))
        else:
            dc.DrawText(s, (bmpw-w)/2, cw.wins(40))
        # ページ番号
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(340))
        # Adventurers
        s = cw.cwpy.msgs["adventurers"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(175))

        # 所属冒険者
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
        for idx, name in enumerate(self.list2[self.index]):
            name = cw.util.abbr_longstr(dc, name, cw.wins(90))
            x = (bmpw - cw.wins(270)) / 2 + ((idx % 3) * cw.wins(95))
            y = cw.wins(200) + (idx / 3) * cw.wins(16)
            dc.DrawText(name, x, y)

        if cw.util.exists_mutex(self.list[self.index]):
            fpath = cw.util.find_resource(cw.util.join_paths(skindir, "Resource/Image/Dialog/PLAYING"), cw.M_IMG)
            if os.path.isfile(fpath):
                bmp = cw.wins((cw.util.load_wxbmp(fpath, True), cw.setting.SIZE_RESOURCES["Dialog/PLAYING"]))
            else:
                bmp = cw.cwpy.rsrc.dialogs["PLAYING"]
            w = bmp.GetSize()[0]
            dc.DrawBitmap(bmp, (bmpw-w)/2, cw.wins(152), True)

    def conv_yado(self, path, ok=False, moveconverted=False, deletepath=""):
        """
        CardWirthの宿データを変換。
        """
        # カードワースの宿か確認
        if not os.path.exists(cw.util.join_paths(path, "Environment.wyd")):
            s = u"CardWirthの宿のディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        if not ok:
            cw.cwpy.sounds["click"].play()
            s = os.path.basename(path) + u" を変換します。\nよろしいですか？"
            dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            self.Parent.move_dlg(dlg)

            if not dlg.ShowModal() == wx.ID_OK:
                dlg.Destroy()
                return

            dlg.Destroy()

        # 宿データ
        cwdata = cw.binary.cwyado.CWYado(
            path, "Yado", cw.cwpy.setting.skintype)

        # 変換可能なデータかどうか確認
        if not cwdata.is_convertible():
            s = u"CardWirth ver1.28以降の宿しか変換できません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            cwdata.name + u" 変換", "", maximum=100,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(cwdata)
        thread.start()

        while not thread.complete:
            dlg.Update(cwdata.curnum, cwdata.message)
            wx.MilliSleep(1)

        dlg.Destroy()
        yadodir = thread.path

        # エラーログ表示
        if cwdata.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # 変換完了ダイアログ
        cw.cwpy.sounds["harvest"].play()
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

        if deletepath:
            cw.util.remove(deletepath)
        elif moveconverted:
            if not os.path.isdir(u"ConvertedYado"):
                os.makedirs(u"ConvertedYado")
            topath = cw.util.join_paths(u"ConvertedYado", os.path.basename(path))
            topath = cw.binary.util.check_duplicate(topath)
            shutil.move(path, topath)

        cw.cwpy.sounds["page"].play()
        self.update_list(yadodir)

    def unconv_yado(self):
        """
        CardWirthの宿データへ逆変換。
        """
        yadodir = self.list[self.index]
        yadoname = self.names[self.index]

        # 変換確認ダイアログ
        cw.cwpy.sounds["click"].play()
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
        except:
            cw.util.print_ex()
            s = u"フォルダ %s を生成できません。" % (dstpath)
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        cw.cwpy.setting.unconvert_targetfolder = dstpath

        # 宿データ
        cw.cwpy.yadodir = cw.util.join_paths(yadodir)
        cw.cwpy.tempdir = cw.cwpy.yadodir.replace("Yado", cw.util.join_paths(cw.tempdir, u"Yado"), 1)
        try:
            ydata = cw.data.YadoData(cw.cwpy.yadodir, cw.cwpy.tempdir, loadparty=False)

            # コンバータ
            unconv = cw.binary.cwyado.UnconvCWYado(ydata, dstpath, targetengine)

            # プログレスダイアログ表示
            dlg = wx.ProgressDialog(
                u"%s 逆変換" % (yadoname), "", maximum=unconv.maxnum,
                parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
                wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
            thread = cw.binary.ConvertingThread(unconv)
            thread.start()

            while not thread.complete:
                dlg.Update(unconv.curnum, unconv.message)
                wx.MilliSleep(1)

            dlg.Destroy()
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
        cw.cwpy.sounds["harvest"].play()
        s = u"データの逆変換が完了しました。\n%s" % (unconv.dir)
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_list(self, yadodir=""):
        """
        登録されている宿のリストを更新して、
        引数のnameの宿までページを移動する。
        """
        self.names, self.list, self.list2, self.skins, self.classic, self.isshortcuts = self.get_yadolist()

        try:
            self.index = self.list.index(yadodir)
        except:
            self.index = 0

        self.draw(True)
        self.enable_btn()

    def get_yadolist(self):
        """Yadoにある宿のpathリストと冒険者リストを返す。"""
        names = []
        yadodirs = []
        skins = []
        classic = []
        isshortcuts = []

        if not os.path.exists(u"Yado"):
            os.makedirs(u"Yado")

        for dname in os.listdir(u"Yado"):
            path  = cw.util.join_paths(u"Yado", dname, u"Environment.xml")

            if os.path.isfile(path):
                prop = cw.header.GetProperty(path)
                name = prop.properties.get(u"Name", u"")
                if not name:
                    name = os.path.basename(dname)
                names.append(name)

                if cw.cwpy.setting.store_skinoneachbase:
                    skin = prop.properties.get(u"Skin", u"Classic")
                    skin = cw.util.join_paths(u"Data/Skin", skin)
                    skinxml = cw.util.join_paths(skin, u"Skin.xml")
                    if os.path.isfile(skinxml):
                        skins.append(skin)
                    else:
                        skins.append(cw.cwpy.skindir)
                else:
                    skins.append(cw.cwpy.skindir)

                path  = cw.util.join_paths(u"Yado", dname)
                yadodirs.append(path)
                classic.append(False)
                isshortcuts.append("")
                continue

            path = cw.util.join_paths(u"Yado", dname)
            path2 = cw.util.get_linktarget(path)
            isshortcut = path2 <> path
            if isshortcut:
                path = path2
            path = cw.util.join_paths(path, u"Environment.wyd")
            if os.path.isfile(path):
                # クラシックな宿
                name = os.path.basename(path2)
                names.append(name)
                skins.append(cw.cwpy.skindir)
                yadodirs.append(path2)
                classic.append(True)
                if isshortcut:
                    isshortcuts.append(cw.util.join_paths(u"Yado", dname))
                else:
                    isshortcuts.append("")
                continue

        advnames = []

        for i, yadodir in enumerate(yadodirs):
            seq = []

            if classic[i]:
                # クラシックな宿
                for fname in os.listdir(yadodir):
                    try:
                        ext = os.path.splitext(fname)[1].lower()
                        if ext == ".wch":
                            fpath = cw.util.join_paths(yadodir, fname)
                            with cw.binary.cwfile.CWFile(fpath, "rb") as f:
                                adv = cw.binary.adventurer.Adventurer(None, f, nameonly=True)
                            seq.append(adv.name)
                        elif ext == ".wpl":
                            fpath = cw.util.join_paths(yadodir, fname)
                            with cw.binary.cwfile.CWFile(fpath, "rb") as f:
                                party = cw.binary.party.Party(None, f)
                            for member in party.memberslist:
                                seq.append(member)
                        if 25 <= len(seq):
                            seq = seq[:23]
                            seq.append(cw.cwpy.msgs["scenario_etc"])
                            break
                    except:
                        cw.util.print_ex()

            else:
                yadodb = cw.yadodb.YadoDB(yadodir)
                standbys = yadodb.get_standbynames(25)
                if len(standbys) == 0:
                    yadodb.update(cards=False, adventurers=True, parties=False)
                    standbys = yadodb.get_standbynames(25)

                if 25 <= len(standbys):
                    seq = standbys[:23]
                    seq.append(cw.cwpy.msgs["scenario_etc"])
                else:
                    seq = standbys
                yadodb.close()

            advnames.append(seq)

        return names, yadodirs, advnames, skins, classic, isshortcuts

#-------------------------------------------------------------------------------
#　一覧表示可能な選択ダイアログ(抽象クラス)
#-------------------------------------------------------------------------------

class MultiViewSelect(Select):
    def __init__(self, parent, title, enterid, views=10):
        # ダイアログボックス作成
        Select.__init__(self, parent, title)
        self._processing = False
        self._views = views
        self._enterid = enterid
        self.views = 1

    def can_clickside(self):
        return self.views <= 1

    def OnLeftDClick(self, event):
        # 一覧表示の場合はダブルクリックで決定
        if self._processing:
            return
        if self.views <= 1 or not self.list:
            return
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self._enterid)
        self.ProcessEvent(btnevent)

    def OnMouseWheel(self, event):
        if self._processing:
            return
        if not self.list or len(self.list) == 1:
            return

        count = self.views
        if len(self.list) <= self.views:
            count = 1

        if event.GetWheelRotation() > 0:
            self.index = cw.util.number_normalization(self.index - count, 0, self.get_pagecount() * self.views)
        else:
            self.index = cw.util.number_normalization(self.index + count, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickLeftBtn(self, evt):
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() <> self.leftbtn or len(self.list) <= self.views:
            Select.OnClickLeftBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index - self.views, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickLeft2Btn(self, evt):
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() <> self.left2btn or len(self.list) <= self.views:
            Select.OnClickLeft2Btn(self, evt)
            return
        if self.get_page() == 0:
            self.index = len(self.list) - 1
        elif self.index - self.views * self._views < 0:
            self.index = 0
        else:
            self.index = self.index - self.views * self._views
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRightBtn(self, evt):
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() <> self.rightbtn or len(self.list) <= self.views:
            Select.OnClickRightBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index + self.views, 0, self.get_pagecount() * self.views)
        if len(self.list) <= self.index:
            self.index = len(self.list) - 1
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRight2Btn(self, evt):
        if self._processing:
            return
        if self.views == 1 or evt.GetEventObject() <> self.right2btn or len(self.list) <= self.views:
            Select.OnClickRight2Btn(self, evt)
            return
        if self.get_page() == self.get_pagecount()-1:
            self.index = 0
        elif len(self.list) <= self.index + self.views * self._views:
            self.index = len(self.list) - 1
        else:
            self.index = self.index + self.views * self._views
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnSelect(self, event):
        if self._processing:
            return
        if self.views == 1:
            # 一件だけ表示している場合は決定
            if not self.list:
                return

            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self._enterid)
            self.ProcessEvent(btnevent)
        else:
            # 複数表示中はマウスポインタ直下を選択
            mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
            size = self.toppanel.GetSize()
            rw = size[0] / (self.views / 2)
            rh = size[1] / 2
            sindex = (mousepos[0] / rw) + ((mousepos[1] / rh) * (self.views / 2))
            page = self.get_page()
            index = page * self.views + sindex
            if self.index <> index:
                cw.cwpy.sounds["click"].play()
                self.index = min(index, len(self.list)-1)
                self.enable_btn()
                self.draw(True)

    def OnClickViewBtn(self, event):
        if self._processing:
            return
        cw.cwpy.sounds["equipment"].play()
        self.change_view()
        self.draw(True)

    def change_view(self):
        if self.views == 1:
            self.views = self._views
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_one"])
        else:
            self.views = 1
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_list"])

    def get_page(self):
        return self.index / self.views

    def get_pagecount(self):
        return (len(self.list) + self.views - 1) / self.views


#-------------------------------------------------------------------------------
#　パーティ選択ダイアログ
#-------------------------------------------------------------------------------

class PartySelect(MultiViewSelect):
    """
    パーティ選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        MultiViewSelect.__init__(self, parent, cw.cwpy.msgs["resume_adventure"], wx.ID_OK, 8)
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
        self.names = []
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
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
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)), cw.cwpy.msgs["member_list"])
        self.buttonlist.append(self.viewbtn)
        # partyrecord
        self.partyrecordbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((width, 24)), cw.cwpy.msgs["party_record"])
        self.buttonlist.append(self.partyrecordbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((width, 24)), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)
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
        self.toppanel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        self.draw(True)

    def OnClickInfoBtn(self, event):
        header = self.list[self.index]
        party = cw.data.Party(header, True)

        dlg = cw.dialog.edit.PartyEditor(self.Parent, party)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            party.data.write_xml()
            header = cw.cwpy.ydata.create_partyheader(element=party.data.find("Property"))
            self.list[self.index] = header
            cw.cwpy.ydata.partys[self.index] = header
            self.draw(True)

    def OnClickEditBtn(self, event):
        partyheader = self.list[self.index]
        def redrawfunc():
            def func():
                header = self.list[self.index]
                header = cw.cwpy.ydata.create_partyheader(header.fpath)
                header.data = partyheader.data
                self.list[self.index] = header
                cw.cwpy.ydata.partys[self.index] = header
                cw.cwpy.frame.exec_func(self.draw, True)
            cw.cwpy.exec_func(func)

        dlg = cw.dialog.charainfo.StandbyPartyCharaInfo(self.Parent, partyheader, redrawfunc)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def OnClickPartyRecordBtn(self, event):
        if self._processing:
            return
        cw.cwpy.sounds["click"].play()
        dlg = cw.dialog.partyrecord.SelectPartyRecord(self)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        if not (1 < len(dlg.list) or cw.cwpy.ydata.party):
            self.partyrecordbtn.Disable()
        dlg.Destroy()

    def get_selected(self):
        if self.list:
            return self.list[self.index]
        else:
            return None

    def update_standbys(self, selected):
        pass

    def can_clickcenter(self):
        return self.okbtn.IsEnabled()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            if cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord:
                self.partyrecordbtn.Enable()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

        if not (cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord):
            self.partyrecordbtn.Disable()

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins((cw.util.load_wxbmp(path), cw.SIZE_BOOK))
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        def get_image(header):
            sceheader = header.get_sceheader()

            if sceheader:
                bmp = sceheader.get_wxbmp()
            else:
                path = "Resource/Image/Card/COMMAND0"
                path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
                bmp = cw.wins((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))

            paths = header.get_memberpaths()
            bmp2 = None
            if paths:
                fpath = paths[0]
                fpath = cw.util.get_yadofilepath(fpath)
                if os.path.isfile(fpath):
                    fpath = cw.header.GetProperty(fpath).properties.get("ImagePath", "")
                    fpath = cw.util.join_yadodir(fpath)
                    if os.path.isfile(fpath):
                        bmp2 = cw.wins((cw.util.load_wxbmp(fpath, True), cw.SIZE_CARDIMAGE))
                        w = bmp2.GetWidth() // 2
                        h = bmp2.GetHeight() // 2
                        if w and h:
                            img = bmp2.ConvertToImage()
                            img = img.Rescale(w, h, wx.IMAGE_QUALITY_NORMAL)
                            bmp2 = img.ConvertToBitmap()
                        else:
                            bmp2 = None
            return bmp, bmp2, sceheader

        if self.views == 1:
            # 単独表示
            header = self.list[self.index]
            # 見出し
            dc.SetTextForeground(wx.BLACK)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["adventurers_team"]
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(25))
            # 所持金
            s = cw.cwpy.msgs["adventurers_money"] % (header.money)
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(60))

            # メンバ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
            if update:
                self.names = header.get_membernames()
            if len(header.members) > 3:
                n = (3, len(self.names) - 3)
            else:
                n = (len(self.names), 0)

            w = cw.wins(90)

            for index, s in enumerate(self.names):
                s = cw.util.abbr_longstr(dc, s, cw.wins(90))
                if index < 3:
                    dc.DrawLabel(s, wx.Rect((bmpw-w*n[0])/2+w*index, cw.wins(85), w, cw.wins(15)), wx.ALIGN_CENTER)
                else:
                    dc.DrawLabel(s, wx.Rect((bmpw-w*n[1])/2+w*(index-3), cw.wins(105), w, cw.wins(15)), wx.ALIGN_CENTER)

            # パーティ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(20)))
            s = header.name
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(40))
            # シナリオ・宿画像
            bmp, bmp2, sceheader = get_image(header)
            dc.DrawBitmap(bmp, (bmpw-cw.wins(74))/2, cw.wins(125), True)
            if bmp2:
                # パーティの先頭メンバを小さく表示する
                px = bmpw/2
                py = cw.wins(125+47)
                pw = cw.wins(cw.SIZE_CARDIMAGE[0])
                ph = cw.wins(cw.SIZE_CARDIMAGE[1])
                dc.SetClippingRect(wx.Rect(px, py, pw, ph))
                dc.DrawBitmap(bmp2, px, py, True)
                dc.DestroyClippingRegion()

            # シナリオ・宿名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))

            if sceheader:
                s = sceheader.name
            else:
                s = cw.cwpy.ydata.name

            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(225))
            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
            s = s + "/" + str(len(self.list))
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(250))

        else:
            # 一覧表示
            page = self.get_page()

            sindex = page * self.views
            seq = self.list[sindex:sindex+self.views]
            x = 0
            y = 0
            size = self.toppanel.GetSize()
            rw = size[0] / (self.views / 2)
            rh = size[1] / 2
            dc.SetTextForeground(wx.BLACK)
            for i, header in enumerate(seq):
                # 宿・シナリオイメージ
                bmp, bmp2, sceheader = get_image(header)
                ix = x + (rw - cw.wins(72)) / 2
                iy = y + 5
                dc.SetClippingRect((ix, iy, cw.wins(74), cw.wins(94)))
                dc.DrawBitmap(bmp, ix, iy, True)
                if bmp2:
                    # パーティの先頭メンバを小さく表示する
                    px = ix + cw.wins(37)
                    py = iy + cw.wins(47)
                    pw = cw.wins(cw.SIZE_CARDIMAGE[0])
                    ph = cw.wins(cw.SIZE_CARDIMAGE[1])
                    dc.SetClippingRect(wx.Rect(px, py, pw, ph))
                    dc.DrawBitmap(bmp2, px, py, True)
                    dc.DestroyClippingRegion()
                dc.DestroyClippingRegion()

                # パーティ名
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = header.name
                s = cw.util.abbr_longstr(dc, s, rw)
                w = dc.GetTextExtent(s)[0]
                cw.util.draw_witharound(dc, s, x + (rw - w) / 2, y + cw.wins(105))

                # シナリオ・宿名
                if sceheader:
                    s = sceheader.name
                    s = cw.util.abbr_longstr(dc, s, rw)
                    w = dc.GetTextExtent(s)[0]
                    cw.util.draw_witharound(dc, s, x + (rw - w) / 2, y + cw.wins(120))

                # 選択マーク
                if sindex + i == self.index:
                    bmp = cw.cwpy.rsrc.wxstatuses["TARGET"]
                    dc.DrawBitmap(bmp, ix + cw.wins(58), iy + cw.wins(80), True)

                if self.views / 2 == i + 1:
                    x = 0
                    y += rh
                else:
                    x += rw

            # ページ番号
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
            s = str(page+1) if page > 0 else str(-page + 1)
            s = s + "/" + str(self.get_pagecount())
            cw.util.draw_witharound(dc, s, cw.wins(5), cw.wins(5))

#-------------------------------------------------------------------------------
#　冒険者選択ダイアログ
#-------------------------------------------------------------------------------

class PlayerSelect(MultiViewSelect):
    """
    冒険者選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        MultiViewSelect.__init__(self, parent, cw.cwpy.msgs["select_member_title"], wx.ID_ADD, 10)
        # 冒険者情報
        self.list = []
        self.isalbum = False
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        self.toppanel.SetMinSize(cw.wins((460, 280)))

        # 絞込条件
        choices = [cw.cwpy.msgs["sort_name"],
                   cw.cwpy.msgs["description"],
                   cw.cwpy.msgs["history"],
                   cw.cwpy.msgs["character_attribute"],
                   cw.cwpy.msgs["sort_level"]]
        self._init_narrowpanel(choices, u"", cw.cwpy.setting.standbys_narrowtype)

        # sort
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15), weight=wx.NORMAL)
        self.sort_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["sort_title"])
        self.sort_label.SetFont(font)
        self.sort = wx.Choice(self, size=cw.wins((75, 20)))
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14), weight=wx.NORMAL))
        self.sort.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        self.sort.Append(cw.cwpy.msgs["sort_no"])
        self.sort.Append(cw.cwpy.msgs["sort_name"])
        self.sort.Append(cw.cwpy.msgs["sort_level"])
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
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((50, 24)), cw.cwpy.msgs["member_list"])
        self.buttonlist.append(self.viewbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((50, 24)), cw.cwpy.msgs["close"])
        self.buttonlist.append(self.closebtn)

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

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(cw.wins((383, 0)), 0)
        sizer.Add(self.sort, 0, wx.TOP, cw.wins(2))
        self.toppanel.SetSizer(sizer)
        self.toppanel.Layout()

        seq = self.accels
        self.sortkeydown = []
        for i in xrange(0, 9):
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
        cw.util.set_acceleratortable(self, seq)

    def _add_topsizer(self):
        nsizer = wx.BoxSizer(wx.HORIZONTAL)

        nsizer.Add(self.narrow_label, 0, wx.LEFT|wx.RIGHT|wx.CENTER, cw.wins(2))
        nsizer.Add(self.narrow, 1, wx.CENTER, 0)
        nsizer.Add(self.narrow_type, 0, wx.CENTER|wx.EXPAND, cw.wins(3))

        nsizer.Add(self.sort_label, 0, wx.LEFT|wx.RIGHT|wx.CENTER, cw.wins(3))
        nsizer.Add(self.sort, 0, wx.CENTER|wx.EXPAND, 0)

        self.topsizer.Add(nsizer, 0, wx.EXPAND, 0)

    def _on_narrowcondition(self):
        cw.cwpy.setting.standbys_narrowtype = self.narrow_type.GetSelection()
        self.update_narrowcondition()
        self.draw(True)

    def update_narrowcondition(self):
        if 0 <= self.index and self.index < len(self.list):
            selected = self.list[self.index]
        else:
            selected = None

        if self.isalbum:
            self.list = cw.cwpy.ydata.album[:]
        else:
            self.list = cw.cwpy.ydata.standbys[:]

        narrow = self.narrow.GetValue().lower()
        donarrow = bool(narrow)
        ntype = self.narrow_type.GetSelection()

        if donarrow and ntype == 4:
            # レベル
            try:
                narrow = int(narrow)
            except:
                donarrow = False

        if donarrow:

            hiddens = set([u"＿", u"＠"])
            attrs = set(cw.cwpy.setting.periodnames)
            attrs.update(cw.cwpy.setting.sexnames)
            attrs.update(cw.cwpy.setting.naturenames)
            attrs.update(cw.cwpy.setting.makingnames)

            seq = []
            for header in self.list:
                if ntype == 0:
                    # 名前
                    if not narrow in header.name.lower():
                        continue

                elif ntype == 1:
                    # 解説
                    if not narrow in header.desc.lower():
                        continue

                elif ntype == 2:
                    # 経歴
                    for coupon in header.history:
                        if coupon:
                            if cw.cwpy.is_debugmode():
                                if coupon[0] == u"＿" and coupon[1:] in attrs:
                                    continue
                            else:
                                if coupon[0] in hiddens:
                                    continue

                            if narrow in coupon.lower():
                                break
                    else:
                        continue

                elif ntype == 3:
                    # 特性
                    for coupon in header.history:
                        if coupon and coupon[0] == u"＿":
                            coupon = coupon[1:]
                            if coupon in attrs:
                                if narrow in coupon.lower():
                                    break
                    else:
                        continue

                elif ntype == 4:
                    # レベル
                    if header.level <> narrow:
                        continue

                seq.append(header)
            self.list = seq

        if selected in self.list:
            self.index = self.list.index(selected)
        elif self.list:
            self.index %= len(self.list)
        else:
            self.index = 0
        self.enable_btn()

    def OnNumberKeyDown(self, event):
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

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.newbtn.Enable()
            self.closebtn.Enable()
            self.exbtn.Enable()
            self.viewbtn.Enable()
        elif len(self.list) <= self.views:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
            if not self.list:
                self.index = 0
        else:
            self._enable_btn()

        # 冒険者が6人だったら追加ボタン無効化
        if len(cw.cwpy.get_pcards()) == 6:
            self.addbtn.Disable()

    def OnSort(self, event):
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

        if cw.cwpy.setting.sort_standbys <> sorttype:
            cw.cwpy.sounds["page"].play()
            cw.cwpy.setting.sort_standbys = sorttype
            cw.cwpy.ydata.sort_standbys()
            self.update_narrowcondition()
            self.draw(True)
        self.left2btn.SetFocus()

    def can_clickcenter(self):
        return self.addbtn.IsEnabled()

    def OnLeftDClick(self, event):
        # 一覧表示の場合はダブルクリックで編入
        if self._processing:
            return
        if len(cw.cwpy.get_pcards()) == 6:
            return
        MultiViewSelect.OnLeftDClick(self, event)

    def OnMouseWheel(self, event):
        if self._processing:
            return

        if change_combo(self.narrow_type, event):
            return
        elif change_combo(self.sort, event):
            return
        else:
            MultiViewSelect.OnMouseWheel(self, event)

    def OnSelect(self, event):
        if self._processing:
            return
        if self.views == 1:
            # 一人だけ表示している場合は編入
            if not self.list or len(cw.cwpy.get_pcards()) == 6:
                return

        MultiViewSelect.OnSelect(self, event)

    def OnClickNewBtn(self, event):
        if self._processing:
            return
        cw.cwpy.sounds["click"].play()
        if cw.cwpy.setting.debug:
            dlg = cw.debug.charaedit.CharacterEditDialog(self, create=True)
            cw.cwpy.frame.move_dlg(dlg)
        else:
            dlg = cw.dialog.create.AdventurerCreater(self)
            cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["page"].play()
            header = cw.cwpy.ydata.add_standbys(dlg.fpath)
            # リスト更新
            self.update_narrowcondition()
            if header in self.list:
                self.index = self.list.index(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def get_selected(self):
        if self.list:
            return self.list[self.index]
        else:
            return None

    def update_standbys(self, selected):
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

    def OnClickAddBtn(self, event):
        if self._processing:
            return
        self._processing = True

        header = self.list[self.index]

        def func(panel, header, index):
            if PlayerSelect._add(header):
                def func(panel):
                    if panel:
                        panel._processing = False
                        self.update_narrowcondition()
                        if len(panel.list):
                            panel.index %= len(panel.list)
                        else:
                            panel.index = 0
                        panel.enable_btn()
                        panel.draw(True)
                cw.cwpy.frame.exec_func(func, panel)
            else:
                def func(panel):
                    if panel:
                        panel._processing = False
                cw.cwpy.frame.exec_func(func, panel)
        cw.cwpy.exec_func(func, self, header, self.index)

    @staticmethod
    def _add(header):
        assert threading.currentThread() == cw.cwpy
        if cw.cwpy.ydata.party:
            if len(cw.cwpy.ydata.party.members) < 6:
                cw.cwpy.sounds["harvest"].play()
                cw.cwpy.ydata.standbys.remove(header)
                cw.cwpy.ydata.party.add(header)
                return True
            else:
                # 追加できなかった
                return False
        else:
            cw.cwpy.sounds["harvest"].play()
            cw.cwpy.ydata.standbys.remove(header)
            cw.cwpy.ydata.create_party(header, chgarea=False)
            return True

    def OnClickExBtn(self, event):
        """
        拡張。
        """
        if self._processing:
            return
        cw.cwpy.sounds["click"].play()
        if self.list:
            name = self.list[self.index].name
            title = cw.cwpy.msgs["extension_title"] % (name)
        else:
            title = cw.cwpy.msgs["extension"]
        items = [
            (cw.cwpy.msgs["grow"], cw.cwpy.msgs["grow_adventurer_description"], self.grow_adventurer, bool(self.list)),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_adventurer_description"], self.delete_adventurer, bool(self.list)),
            (cw.cwpy.msgs["select_party_record"], cw.cwpy.msgs["select_party_record_description"], self.select_partyrecord, bool(cw.cwpy.ydata.party or cw.cwpy.ydata.partyrecord)),
            (cw.cwpy.msgs["random_character"], cw.cwpy.msgs["random_character_description"], self.create_randomadventurer, True),
            (cw.cwpy.msgs["random_team"], cw.cwpy.msgs["random_team_description"], self.random_team, bool(cw.cwpy.ydata.standbys and self.addbtn.IsEnabled()))
        ]
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def grow_adventurer(self):
        """冒険者を成長させる。
        """
        header = self.list[self.index]
        age = header.age
        index = cw.cwpy.setting.periodcoupons.index(age)

        if index < 0:
            # 年代が不正。スキンが違う場合は発生しうる
            cw.cwpy.sounds["error"].play()
            return

        if index == len(cw.cwpy.setting.periodcoupons) - 1:
            nextage= None
            s = cw.cwpy.msgs["confirm_die"] % (header.name)
        else:
            nextage= cw.cwpy.setting.periodcoupons[index + 1]
            s = cw.cwpy.msgs["confirm_grow"] % (header.name, age[1:], nextage[1:])

        cw.cwpy.sounds["signal"].play()
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            cw.cwpy.sounds["harvest"].play()
            if nextage:
                header.grow()
            else:
                s = cw.cwpy.msgs["die_message"] % (header.name)
                dlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s, 2)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()

                if not header.leavenoalbum:
                    path = cw.xmlcreater.create_albumpage(header.fpath)
                    cw.cwpy.ydata.add_album(path)
                for partyrecord in cw.cwpy.ydata.partyrecord:
                    partyrecord.vanish_member(header.fpath)
                cw.cwpy.ydata.remove_emptypartyrecord()
                cw.cwpy.remove_xml(header)
                cw.cwpy.ydata.standbys.remove(header)
                self.update_narrowcondition()
                if len(self.list):
                    self.index %= len(self.list)
                else:
                    self.index = 0
                self.enable_btn()

            self.draw(True)
        else:
            dlg.Destroy()

    def delete_adventurer(self):
        """冒険者を削除する。
        """
        cw.cwpy.sounds["signal"].play()
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["dump"].play()
            self._delete_adventurer(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def _delete_adventurer(self, header):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # 手札カードを移動させる
        data = cw.data.yadoxml2etree(header.fpath)
        ccard = cw.character.Character(data)
        for pocket in ccard.cardpocket:
            for card in pocket:
                cw.cwpy.trade("STOREHOUSE", header=card, from_event=True, sort=False)
        cw.cwpy.ydata.sort_storehouse()

        # レベル3以上・"＿消滅予約"を持ってない場合、アルバムに残す
        if header.level >= 3 and not header.leavenoalbum:
            path = cw.xmlcreater.create_albumpage(header.fpath, nocoupon=True)
            cw.cwpy.ydata.add_album(path)

        for partyrecord in cw.cwpy.ydata.partyrecord:
            partyrecord.vanish_member(header.fpath)
        cw.cwpy.ydata.remove_emptypartyrecord()
        cw.cwpy.remove_xml(header)
        cw.cwpy.ydata.standbys.remove(header)
        self.update_narrowcondition()
        if len(self.list):
            self.index %= len(self.list)
        else:
            self.index = 0

    def select_partyrecord(self):
        """編成記録ダイアログを開く。
        """
        cw.cwpy.sounds["click"].play()
        dlg = cw.dialog.partyrecord.SelectPartyRecord(self)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def random_team(self):
        """ランダムな編成のチームを組む。
        """
        if self._processing:
            return
        self._processing = True

        def func(panel):
            class Pocket(object):
                def __init__(self, header, point):
                    self.header = header
                    self.point = point

            while cw.cwpy.ydata.standbys and (not cw.cwpy.ydata.party or\
                                              len(cw.cwpy.ydata.party.members) < 6):
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                if not cw.cwpy.ydata.party:
                    PlayerSelect._add(cw.cwpy.dice.choice(cw.cwpy.ydata.standbys))
                else:
                    seq = self.calc_needs(cw.cwpy.ydata.standbys)
                    seq2 = []
                    for need, header in cw.cwpy.dice.shuffle(seq):
                        point = cw.cwpy.dice.roll(1, need)
                        seq2.append(Pocket(header, point))
                    cw.util.sort_by_attr(seq2, "point")
                    PlayerSelect._add(seq2[0].header)

            def func(panel):
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

    def create_randomadventurer(self):
        """ランダムな特性を持つキャラクターを生成する。
        """
        if self._processing:
            return
        self._processing = True
        cw.cwpy.sounds["signal"].play()
        info = cw.debug.charaedit.CharaInfo(None)
        info.set_randomfeatures()
        fpath = info.create_adventurer(setlevel=False)
        header = cw.cwpy.ydata.add_standbys(fpath)

        # リスト更新
        self.narrow.SetValue(u"")
        self.update_narrowcondition()
        if header in self.list:
            self.index = self.list.index(header)
        chgviews = self.views <> 1
        if chgviews:
            self.change_view()
        self.draw(True)

        # *Names.txtファイルがある時は初期名を決める
        sex = header.get_sex()
        randomname = cw.dialog.create.get_randomname(sex)

        dlg = cw.dialog.edit.InputTextDialog(self, cw.cwpy.msgs["naming"],
                                             cw.cwpy.msgs["naming_random_character"],
                                             text=randomname,
                                             maxlength=14)
        self.Parent.move_dlg(dlg, point=(cw.wins(130), cw.wins(0)))
        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            cw.cwpy.sounds["harvest"].play()
            data = cw.data.yadoxml2etree(header.fpath)
            ccard = cw.character.Character(data)
            ccard.set_name(dlg.text)
            ccard.data.is_edited = True
            ccard.data.write_xml()
            header.name = dlg.text
        else:
            cw.cwpy.sounds["dump"].play()
            self._delete_adventurer(header)

        dlg.Destroy()

        if chgviews:
            self.change_view()
        self.draw(True)
        self.enable_btn()

        self._processing = False

    def OnClickInfoBtn(self, event):
        if self._processing:
            return
        cw.cwpy.sounds["click"].play()
        dlg = charainfo.StandbyCharaInfo(self, self.list, self.index, self.update_character)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_character(self):
        def func():
            header = self.list[self.index]
            header = cw.cwpy.ydata.create_advheader(header.fpath)
            if self.isalbum:
                cw.cwpy.ydata.album[self.index] = header
            else:
                cw.cwpy.ydata.standbys[self.index] = header
            self.update_narrowcondition()
            self.list[self.index] = header
            cw.cwpy.frame.exec_func(self.draw, True)
        cw.cwpy.exec_func(func)

    def calc_needs(self, mlist):
        """mlist内のメンバに対して、現在のパーティの構成から
        パーティにおける必要度を計算する。
        レベルが近く、同型のメンバが少ないほど必要度が高くなる。
        """
        if cw.cwpy.ydata.party:
            talents = set(cw.cwpy.setting.naturecoupons)
            types = {}
            level = 0.0
            seq = []
            for member in cw.cwpy.get_pcards():
                level += member.level
                talent = member.get_talent()
                val = types.get(talent, 0)
                val += 1
                types[talent] = val
            level /= len(cw.cwpy.ydata.party.members)

            for header in mlist:
                # 同型のメンバの数だけ必要度を下げる
                need = 10
                talent = cw.cwpy.setting.naturecoupons[0]
                for coupon in header.history:
                    if coupon in talents:
                        talent = coupon
                        break
                val = types.get(talent, 0)
                for _i in xrange(val):
                    need *= 2

                # レベルが離れているほど必要度を下げる
                val = level - header.level
                if val < 0:
                    val = -val
                for _i in xrange(int(val+0.5)):
                    need *= 4
                seq.append((int(need), header))
            return seq
        else:
            return [(10, header) for header in mlist]

    def draw(self, update=False):
        dc = MultiViewSelect.draw(self, update)
        # 背景
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins((cw.util.load_wxbmp(path), cw.SIZE_BOOK))
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        if self.list:
            if self.views == 1:
                header = self.list[self.index % len(self.list)]
                # Level
                dc.SetTextForeground(wx.BLACK)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_level"]
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(65), cw.wins(45))
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(31)))
                s = str(header.level)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(110), cw.wins(31))
                # Name
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_class"]
                dc.DrawText(s, cw.wins(110) + w + cw.wins(5), cw.wins(45))
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(24)))
                s = header.name
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(125) - w / 2, cw.wins(62))
                # Image
                path = cw.util.join_yadodir(header.imgpath)
                bmp = cw.wins((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))
                dc.SetClippingRect(cw.wins((88, 90, 74, 94)))
                dc.DrawBitmap(bmp, cw.wins(88), cw.wins(90), True)
                dc.DestroyClippingRegion()
                # Age
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = cw.cwpy.msgs["character_age"] % (header.get_age())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(127) - w / 2, cw.wins(195))
                # Sex
                s = cw.cwpy.msgs["character_sex"] % (header.get_sex())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(127) - w / 2, cw.wins(210))
                # EP
                s = cw.cwpy.msgs["character_ep"] % (header.ep)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(127) - w / 2, cw.wins(225))

                # クーポン(新しい順から9つ)
                hiddens = set([u"＿", u"＠"])
                s = cw.cwpy.msgs["character_history"]
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, cw.wins(320) - w / 2, cw.wins(65))
                history = []
                for s in header.history:
                    if s and not s[0] in hiddens:
                        history.append(s)
                        if 9 < len(history):
                            history[-1] = cw.cwpy.msgs["history_etc"]
                            break
                for index, s in enumerate(history):
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, cw.wins(320) - w / 2, cw.wins(95) + cw.wins(14) * index)

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
                s = s + "/" + str(len(self.list))
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)/2, cw.wins(250))
            else:
                page = self.get_page()

                sindex = page * self.views
                seq = self.list[sindex:sindex+self.views]
                x = 0
                y = 0
                size = self.toppanel.GetSize()
                rw = size[0] / (self.views / 2)
                rh = size[1] / 2
                dc.SetTextForeground(wx.BLACK)
                for i, header in enumerate(seq):
                    # Image
                    path = cw.util.join_yadodir(header.imgpath)
                    bmp = cw.wins((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))
                    ix = x + (rw - cw.wins(72)) / 2
                    iy = y + 5
                    dc.SetClippingRect((ix, iy, cw.wins(74), cw.wins(94)))
                    dc.DrawBitmap(bmp, ix, iy, True)
                    dc.DestroyClippingRegion()

                    # Name
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    s = header.name
                    s = cw.util.abbr_longstr(dc, s, rw)
                    w = dc.GetTextExtent(s)[0]
                    cw.util.draw_witharound(dc, s, x + (rw - w) / 2, y + cw.wins(105))
                    # Level
                    space = cw.wins(5)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    s1 = cw.cwpy.msgs["character_level"]
                    w1, h1 = dc.GetTextExtent(s1)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))
                    s2 = str(header.level)
                    w2, h2 = dc.GetTextExtent(s2)
                    sx = x + (rw - (w1+cw.wins(5)+w2+space)) / 2
                    sy = y + cw.wins(120)
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                    cw.util.draw_witharound(dc, s1, sx, sy + (h2-h1))
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))
                    cw.util.draw_witharound(dc, s2, sx + w1 + space + cw.wins(5), sy)
                    # Selected
                    if sindex + i == self.index:
                        bmp = cw.cwpy.rsrc.wxstatuses["TARGET"]
                        dc.DrawBitmap(bmp, ix + cw.wins(58), iy + cw.wins(80), True)

                    if self.views / 2 == i + 1:
                        x = 0
                        y += rh
                    else:
                        x += rw

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
                s = str(page+1) if page > 0 else str(-page + 1)
                s = s + "/" + str(self.get_pagecount())
                cw.util.draw_witharound(dc, s, cw.wins(5), cw.wins(5))

#-------------------------------------------------------------------------------
#　アルバムダイアログ
#-------------------------------------------------------------------------------

class Album(PlayerSelect):
    """
    アルバムダイアログ。
    冒険者選択ダイアログを継承している。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, cw.cwpy.msgs["album"])
        # 冒険者情報
        self.list = cw.cwpy.ydata.album
        self.isalbum = True
        self.index = 0
        self.views = 1
        self.sort = None
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_PROPERTIES, cw.wins((90, 24)), cw.cwpy.msgs["information"])
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

    def can_clickcenter(self):
        return False

    def OnMouseWheel(self, event):
        Select.OnMouseWheel(self, event)

    def _add_topsizer(self):
        pass

    def update_narrowcondition(self):
        pass

    def OnClickDelBtn(self, event):
        cw.cwpy.sounds["signal"].play()
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character_in_album"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["dump"].play()
            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.album.remove(header)
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

    def OnSelect(self, event):
        pass

def change_combo(combo, event):
    if combo and combo.GetRect().Contains(event.GetPosition()):
        index = combo.GetSelection()
        count = combo.GetCount()
        if event.GetWheelRotation() > 0:
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

#-------------------------------------------------------------------------------
#　貼り紙選択ダイアログ
#-------------------------------------------------------------------------------

class ScenarioSelect(Select):
    """
    貼り紙選択ダイアログ。
    """
    def __init__(self, parent, db):
        # ダイアログボックス作成
        Select.__init__(self, parent, cw.cwpy.msgs["select_scenario_title"])
        # ディレクトリとシナリオリストの対応
        self.scetable = {}
        # シナリオディレクトリ
        self.scedir = cw.cwpy.setting.get_scedir()
        # 現在開いているディレクトリ
        self.nowdir = self.scedir
        # 開いたディレクトリの階層
        self.dirstack = []
        # シナリオデータベース
        self.db = db
        # nowdirにあるScenarioHeaderのリスト
        self.db.update(self.nowdir, skintype=cw.cwpy.setting.skintype)
        headers = self.db.search_dpath(self.nowdir, create=True, skintype=cw.cwpy.setting.skintype)
        # nowdirにあるディレクトリリスト
        dpaths = self.get_dpaths(self.nowdir)
        # nowdirがディレクトリだった場合の内容リスト
        self.names = []
        self.updatenames_thr = None
        # クリアシナリオ名の集合
        self.stamps = cw.cwpy.ydata.get_compstamps()
        # パーティの所持しているクーポンの集合
        self.coupons = cw.cwpy.ydata.party.get_coupontable()
        # 現在進行中のシナリオパスの集合
        self.nowplayingpaths = cw.cwpy.ydata.get_nowplayingpaths()

        # 検索結果
        self.find_result = None

        # 絞込条件
        choices = (cw.cwpy.msgs["title"],
                   cw.cwpy.msgs["description"],
                   cw.cwpy.msgs["author"],
                   cw.cwpy.msgs["target_level"])
        self._init_narrowpanel(choices, cw.cwpy.setting.scenario_narrow,
                               cw.cwpy.setting.scenario_narrowtype, tworows=True)

        # 整列条件
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15), weight=wx.NORMAL)
        self.sort_label = wx.StaticText(self, -1, label=cw.cwpy.msgs["sort_title2"])
        self.sort_label.SetFont(font)
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14), weight=wx.NORMAL)
        choices = (cw.cwpy.msgs["target_level"],
                   cw.cwpy.msgs["title"],
                   cw.cwpy.msgs["author"],
                   cw.cwpy.msgs["modified_date"])
        self.sort = wx.Choice(self, -1, size=(-1, -1), choices=choices)
        self.sort.SetFont(font)
        self.sort.SetSelection(cw.cwpy.setting.scenario_sorttype)

        # 選択リスト
        self.list = dpaths + headers
        self.scetable[self.nowdir] = self.list
        self.list = self._narrow_scenario(self.list)
        self.index = 0

        # 検索
        bmp = cw.wins(cw.cwpy.rsrc.debugs["FIND_SCENARIO2"])
        self.find = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, cw.wins(32)), bmp=bmp)
        self.find.SetToolTip(wx.ToolTip(cw.cwpy.msgs["find_scenario"]))

        # ブックマーク
        bmp = cw.wins(cw.cwpy.rsrc.debugs["BOOKMARK2"])
        self.bookmark = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, cw.wins(32)), bmp=bmp)
        self.bookmark.SetToolTip(wx.ToolTip(cw.cwpy.msgs["bookmark"]))

        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((400, 370)))

        # ツリー表示用のビュー
        self.tree = wx.TreeCtrl(self, -1, size=cw.wins((400, 370)),
            style=wx.BORDER|wx.TR_SINGLE|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE)
        self.tree.SetDoubleBuffered(True)
        self.tree.SetFont(cw.cwpy.rsrc.get_wxfont("tree", pixelsize=cw.wins(15)-1, weight=wx.NORMAL))
        self.tree.Hide()
        self.tree.imglist = wx.ImageList(cw.wins(16), cw.wins(16))
        self.tree.imgidx_summary = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY"]))
        self.tree.imgidx_complete = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_COMPLETE"]))
        self.tree.imgidx_playing = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_PLAYING"]))
        self.tree.imgidx_invisible = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_INVISIBLE"]))
        self.tree.imgidx_dir = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["DIRECTORY"]))
        self.tree.imgidx_findresult = self.tree.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["FIND_SCENARIO"]))
        self.tree.root = self.tree.AddRoot(self.scedir)
        self.tree.SetItemPyData(self.tree.root, (0, self.scedir))
        self.tree.SetImageList(self.tree.imglist)
        self.tree.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

        # ok
        self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_YES, cw.wins((55, 24)), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.yesbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((55, 24)), cw.cwpy.msgs["description"])
        self.buttonlist.append(self.infobtn)
        # view
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((55, 24)), cw.cwpy.msgs["scenario_tree"])
        self.buttonlist.append(self.viewbtn)
        # convert
        ##self.convbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((55, 24)), u"変換")
        ##self.buttonlist.append(self.convbtn)
        # close
        self.nobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_NO, cw.wins((55, 24)), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.nobtn)
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # リストが空だったらボタンを無効化
        self.enable_btn()
        # 選択状態を記憶
        self._update_saveddirstack()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.Bind(wx.EVT_BUTTON, self.OnClickYesBtn, self.yesbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNoBtn, self.nobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        ##self.Bind(wx.EVT_BUTTON, self.OnClickConvBtn, self.convbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnTreeItemCollapsed)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.tree.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

        self.sort.Bind(wx.EVT_CHOICE, self.OnNarrowCondition)
        self.find.Bind(wx.EVT_BUTTON, self.OnFind)
        self.bookmark.Bind(wx.EVT_BUTTON, self.OnBookmark)

        self.draw(True)

        self.bookmarkmenu = None

        seq = self.accels
        upkey = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnUpKeyDown, id=upkey)
        seq.append((wx.ACCEL_NORMAL, wx.WXK_UP, upkey))
        downkey = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnDownKeyDown, id=downkey)
        seq.append((wx.ACCEL_NORMAL, wx.WXK_DOWN, downkey))

        bookmarkkey = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnBookmark2, id=bookmarkkey)
        seq.append((wx.ACCEL_CTRL, ord('b'), bookmarkkey))

        self.narrowkeydown = []
        self.sortkeydown = []
        for i in xrange(0, 9):
            narrowkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=narrowkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, narrowkeydown))
            self.narrowkeydown.append(narrowkeydown)
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_ALT, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
        cw.util.set_acceleratortable(self, seq)

    def OnMouseWheel(self, event):
        if self._processing:
            return

        if change_combo(self.narrow_type, event):
            return
        elif change_combo(self.sort, event):
            return
        else:
            Select.OnMouseWheel(self, event)

    def OnUpKeyDown(self, event):
        self.narrow.SetFocus()

    def OnDownKeyDown(self, event):
        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            buttonlist[0].SetFocus()

    def OnNumberKeyDown(self, event):
        """
        数値キー'1'～'9'までの押下を処理する。
        絞込条件の変更またはソート条件の変更を行う。
        """
        if self._processing:
            return

        eid = event.GetId()
        if eid in self.narrowkeydown:
            index = self.narrowkeydown.index(eid)
            if index < self.narrow_type.GetCount():
                self.narrow_type.SetSelection(index)
                self.OnNarrowCondition(event)
        if eid in self.sortkeydown:
            index = self.sortkeydown.index(eid)
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                self.OnNarrowCondition(event)

    def _add_topsizer(self):
        self.topsizer.Add(self.tree, 1, wx.EXPAND, 0)

        nsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer1.Add(self.keyword_label, 0, wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, cw.wins(1))
        vsizer1.Add(self.narrow, 0, wx.EXPAND, 0)
        nsizer.Add(vsizer1, 1, wx.CENTER|wx.EXPAND|wx.RIGHT, cw.wins(1))

        vsizer2 = wx.BoxSizer(wx.VERTICAL)
        vsizer2.Add(self.narrow_label, 0, wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, cw.wins(1))
        vsizer2.Add(self.narrow_type, 0, wx.EXPAND, 0)
        nsizer.Add(vsizer2, 0, wx.CENTER|wx.EXPAND|wx.RIGHT, cw.wins(1))

        vsizer3 = wx.BoxSizer(wx.VERTICAL)
        vsizer3.Add(self.sort_label, 0, wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, cw.wins(1))
        vsizer3.Add(self.sort, 0, wx.EXPAND, 0)
        nsizer.Add(vsizer3, 0, wx.CENTER|wx.EXPAND|wx.RIGHT, cw.wins(1))

        nsizer.Add(self.find, 0, wx.CENTER|wx.EXPAND, 0)
        nsizer.Add(self.bookmark, 0, wx.CENTER|wx.EXPAND, 0)

        self.topsizer.Add(nsizer, 0, wx.EXPAND, 0)

    def OnFind(self, event):
        value = self.narrow.GetValue()
        if not value:
            cw.cwpy.sounds["error"].play()
            return
        narrow = self.narrow_type.GetSelection()
        if narrow == 0:
            ftype = cw.scenariodb.DATA_TITLE
        elif narrow == 1:
            ftype = cw.scenariodb.DATA_DESC
        elif narrow == 2:
            ftype = cw.scenariodb.DATA_AUTHOR
        elif narrow == 3:
            ftype = cw.scenariodb.DATA_LEVEL
            try:
                value = int(value)
            except:
                cw.cwpy.sounds["error"].play()
                return
        else:
            assert False
        headers = self.db.find_headers(ftype, value, skintype=cw.cwpy.setting.skintype)
        cw.cwpy.sounds["harvest"].play()
        self._set_findresult(headers, False)

        if not (self.tree and self.tree.IsShown() and self.tree.IsShownOnScreen()):
            self.draw(True)

    def _set_findresult(self, headers, selfirstheader):
        list = self.scetable[self.scedir]
        if list and isinstance(list[0], FindResult):
            findresult = list[0]
        else:
            findresult = FindResult()
            list.insert(0, findresult)
            self.find_result = findresult
            self.scetable[self.scedir] = list
        self.scetable[findresult] = headers[:]
        findresult.headers = self._sort_headers(headers)

        # 検索結果ディレクトリを表示する
        if self.tree and self.tree.IsShown() and self.tree.IsShownOnScreen():
            item, cookie = self.tree.GetFirstChild(self.tree.root)
            if item and item.IsOk():
                data = self.tree.GetItemPyData(item)
                if data and isinstance(data[1], FindResult):
                    self.tree.Delete(item)
            item = self._create_findresultitem(0, self.tree.root, findresult)
            parent = item
            self.tree.Expand(item)
            item = self.tree.GetNextSibling(item)
            while item and item.IsOk():
                data = self.tree.GetItemPyData(item)
                if data:
                    index, header = data
                    self.tree.SetItemPyData(item, (index+1, header))
                item = self.tree.GetNextSibling(item)
            if headers and selfirstheader:
                item, cookie = self.tree.GetFirstChild(parent)
                self.tree.SelectItem(item)
                list = self.scetable[self.find_result]
            else:
                self.tree.SelectItem(parent)
            self._tree_selchanged()
        else:
            if headers and selfirstheader:
                self.nowdir = self.find_result
                list = self.scetable[self.find_result]
            else:
                self.nowdir = self.scedir

        self.list = self._narrow_scenario(list)
        self.index = 0
        if headers and selfirstheader:
            self.dirstack = [(self.scedir, "/find_result")]

    def OnBookmark(self, event):
        # ブックマークメニューを生成して表示する
        cw.cwpy.sounds["page"].play()
        if not self.bookmarkmenu:
            self.create_bookmarkmenu()
        self._add_bookmark.Enable(not self._is_specialselected())
        self.bookmark.PopupMenu(self.bookmarkmenu)

    def OnBookmark2(self, event):
        cw.cwpy.sounds["page"].play()
        if not self.bookmarkmenu:
            self.create_bookmarkmenu()
        size = self.bookmark.GetSize()
        self._add_bookmark.Enable(not self._is_specialselected())
        self.bookmark.PopupMenuXY(self.bookmarkmenu, size[0] / 2, size[1] / 2)

    def _is_specialselected(self):
        return not self.list or isinstance(self.list[self.index], FindResult)

    def create_bookmarkmenu(self):
        if self.bookmarkmenu:
            self.bookmarkmenu.Destroy()
        menu = wx.Menu()
        self.bookmarkmenu = menu
        icon_add = cw.wins(cw.cwpy.rsrc.debugs["BOOKMARK"])
        icon_arrange = cw.wins(cw.cwpy.rsrc.debugs["ARRANGE_BOOKMARK"])
        icon_summary = cw.wins(cw.cwpy.rsrc.debugs["SUMMARY"])
        icon_complete = cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_COMPLETE"])
        icon_playing = cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_PLAYING"])
        icon_invisible = cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_INVISIBLE"])
        icon_dir = cw.wins(cw.cwpy.rsrc.debugs["DIRECTORY"])

        font = cw.cwpy.rsrc.get_wxfont("menu", pixelsize=cw.wins(13), weight=wx.NORMAL)

        self._add_bookmark = wx.MenuItem(menu, -1, cw.cwpy.msgs["add_bookmark"])
        self._add_bookmark.SetBitmap(icon_add)
        self._add_bookmark.SetFont(font)
        menu.AppendItem(self._add_bookmark)
        menu.Bind(wx.EVT_MENU, self.OnAddBookmark, self._add_bookmark)

        arrange = wx.MenuItem(menu, -1, cw.cwpy.msgs["arrange_bookmark"])
        arrange.SetBitmap(icon_arrange)
        arrange.SetFont(font)
        menu.AppendItem(arrange)
        menu.Bind(wx.EVT_MENU, self.OnArrangeBookmark, arrange)

        # ブックマークを開くためのユーティリティクラス
        class OpenBookmark(object):
            def __init__(self, outer, bookmark, bookmarkpath):
                self.outer = outer
                self.bookmark = bookmark
                self.bookmarkpath = bookmarkpath

            def OnOpen(self, event):
                cw.cwpy.sounds["equipment"].play()
                if self.outer.narrow.GetValue():
                    self.outer.narrow.SetValue("")
                    self.outer.update_narrowcondition()
                self.outer.set_selected(self.bookmark, self.bookmarkpath, opendir=True)

        if cw.cwpy.ydata.bookmarks:
            menu.AppendSeparator()
            for bookmark, bookmarkpath in cw.cwpy.ydata.bookmarks:
                if bookmark:
                    path = self.scedir
                    for p in bookmark:
                        if p.startswith("/"):
                            path = bookmarkpath
                            p = os.path.basename(path)
                            break
                        path = cw.util.join_paths(path, p)
                        if not os.path.exists(path):
                            path = bookmarkpath
                            p = os.path.basename(path)
                            break
                        path = cw.util.get_linktarget(path)
                else:
                    path = bookmarkpath
                    p = os.path.basename(path)

                path = cw.util.get_linktarget(path)
                if self.is_scenario(path):
                    header = self.db.search_path(path, skintype=cw.cwpy.setting.skintype)
                elif os.path.isdir(path):
                    header = None
                else:
                    header = None
                    if bookmark and bookmark[-1]:
                        p = bookmark[-1]
                    elif bookmarkpath:
                        p = os.path.basename(bookmarkpath)
                    else:
                        p = u""

                if header:
                    item = wx.MenuItem(menu, -1, header.name.replace("&", "&&"))
                    item.SetFont(font)
                    if self.is_playing(header):
                        item.SetBitmap(icon_playing)
                    elif self.is_complete(header):
                        item.SetBitmap(icon_complete)
                    elif self.is_invisible(header):
                        item.SetBitmap(icon_invisible)
                    else:
                        item.SetBitmap(icon_summary)
                else:
                    if not p:
                        p = u"[フォルダが見つかりません]"
                    elif sys.platform == "win32":
                        sp = os.path.splitext(p)
                        if sp[1].lower() == ".lnk":
                            p = sp[0]
                    item = wx.MenuItem(menu, -1, p.replace("&", "&&"))
                    item.SetFont(font)
                    item.SetBitmap(icon_dir)

                openbookmark = OpenBookmark(self, bookmark, bookmarkpath)
                menu.AppendItem(item)
                menu.Bind(wx.EVT_MENU, openbookmark.OnOpen, item)

    def OnAddBookmark(self, event):
        self._update_saveddirstack()
        header = self.list[self.index]
        if isinstance(header, FindResult):
            return
        cw.cwpy.sounds["signal"].play()
        if isinstance(header, cw.header.ScenarioHeader):
            name = header.name
        else:
            name = os.path.basename(header)
            if sys.platform == "win32":
                sp = os.path.splitext(name)
                if sp[1].lower() == ".lnk":
                    name = sp[0]
        s = cw.cwpy.msgs["add_bookmark_message"] % (name)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return
        dlg.Destroy()

        def func(panel, selected, selectedpath):
            cw.cwpy.ydata.add_bookmark(selected, selectedpath)
            cw.cwpy.sounds["harvest"].play()
            def func(panel):
                if panel:
                    panel.bookmarkmenu = None
            cw.cwpy.frame.exec_func(func, panel)
        sel, selpath = self.get_selected()
        cw.cwpy.exec_func(func, self, sel, selpath)

    def OnArrangeBookmark(self, event):
        cw.cwpy.sounds["click"].play()
        dlg = cw.dialog.etc.BookmarkDialog(self, self.scedir, self.db)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        def func(panel):
            def func(panel):
                if panel:
                    panel.bookmarkmenu = None
            cw.cwpy.frame.exec_func(func, panel)
        cw.cwpy.exec_func(func, self)

    def OnLeftDClick(self, event):
        if not (self.tree.HitTest(event.GetPosition())[1] & wx.TREE_HITTEST_ONITEM):
            return

        selitem = self.tree.GetSelection()
        if not selitem:
            return
        data = self.tree.GetItemPyData(selitem)
        if not data:
            return
        _index, pathorheader = data
        if isinstance(pathorheader, cw.header.ScenarioHeader):
            if self.viewbtn.Enabled:
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.viewbtn.GetId())
                self.ProcessEvent(btnevent)
        else:
            if self.tree.IsExpanded(selitem):
                cw.cwpy.sounds["page"].play()
                self.tree.Collapse(selitem)
            else:
                cw.cwpy.sounds["equipment"].play()
                self.tree.Expand(selitem)

    def OnKeyUp(self, event):
        if event.GetKeyCode() <> wx.WXK_RETURN:
            return

        selitem = self.tree.GetSelection()
        if not selitem:
            return
        data = self.tree.GetItemPyData(selitem)
        if not data:
            return
        _index, pathorheader = data
        if isinstance(pathorheader, cw.header.ScenarioHeader):
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
            self.ProcessEvent(btnevent)

    def can_clickcenter(self):
        return self.yesbtn.IsEnabled()

    def get_selected(self):
        """
        現在選択されているシナリオを経路形式
        (ディレクトリ・ファイル名の配列)で返す。
        """
        seq = []
        if not self.list:
            return seq, u""

        spdir = False
        for _dpath, selname in self._saved_dirstack:
            if selname.startswith("/"):
                seq = []
                spdir = True
                break
            seq.append(selname)

        sel = self._saved_list[self._saved_index]
        if isinstance(sel, cw.header.ScenarioHeader):
            if not spdir:
                seq.append(sel.fname)
            return seq, os.path.abspath(sel.get_fpath())
        elif isinstance(sel, FindResult):
            return [], u""
        else:
            if not spdir:
                seq.append(os.path.basename(sel))
            return seq, os.path.abspath(sel)

    def _get_nowlist(self, nowdir=None):
        if nowdir is None:
            nowdir = self.nowdir
        if isinstance(nowdir, FindResult):
            return nowdir.headers
        seq = []
        if nowdir == self.scedir and self.find_result:
            seq.append(self.find_result)
        seq.extend(self.db.search_dpath(nowdir, skintype=cw.cwpy.setting.skintype))
        seq.extend(self.get_dpaths(nowdir))
        return seq

    def set_selected(self, spaths, fullpath, opendir=False):
        """
        シナリオを経路形式(ディレクトリ・ファイル名の配列)で
        設定する。
        """
        processing = self._processing
        self._processing = True

        exists_spaths = bool(spaths)
        spath = self.scedir
        for path in spaths:
            if path.startswith("/"):
                exists_spaths = False
                break
            spath = cw.util.join_paths(spath, path)
            spath = cw.util.get_linktarget(spath)
            if not os.path.exists(spath):
                exists_spaths = False
                break

        selfullpath = False
        if not exists_spaths:
            # 経路をたどれないがフルパスがある場合(検索結果として表示)
            if self.is_scenario(fullpath):
                header = self.db.search_path(fullpath)
                if header:
                    self._set_findresult([header], True)
                    selfullpath = True
                else:
                    exists_spaths = False
            elif os.path.isdir(fullpath):
                self._set_findresult([fullpath], True)
                selfullpath = True
            else:
                exists_spaths = False

        if not selfullpath and (not spaths or not exists_spaths):
            # 対象が存在しない場合(初期ディレクトリを選択)
            self.nowdir = self.scedir
            self.index = 0
            self.dirstack = []
            self.list = self._get_nowlist()
            self.scetable[self.nowdir] = self.list
            self.list = self._narrow_scenario(self.list)

        elif not selfullpath:
            # 経路をたどれる場合
            parent = self.scedir
            self.dirstack = []
            exists = True
            treeitem = self.tree.root
            for fname in spaths[:-1]:
                if fname.startswith("/"):
                    break
                parent2 = cw.util.join_paths(parent, fname)
                if os.path.exists(parent2):
                    self.dirstack.append((parent, fname))
                    parent = cw.util.get_linktarget(parent2)
                    if self.tree.IsShown():
                        item, cookie = self.tree.GetFirstChild(treeitem)
                        while item.IsOk():
                            data = self.tree.GetItemPyData(item)
                            assert not data is None
                            index, header = data
                            if not isinstance(header, cw.header.ScenarioHeader) and\
                                    os.path.normcase(os.path.basename(header)) ==\
                                    os.path.normcase(fname):
                                treeitem = item
                                if not self.tree.IsExpanded(item) or\
                                        not self.tree.GetItemPyData(self.tree.GetFirstChild(item)[0]):
                                    self.tree.Expand(item)
                                    self.create_treeitems(item)
                                break
                            item, cookie = self.tree.GetNextChild(treeitem, cookie)
                else:
                    exists = False
                    break
            self.nowdir = parent
            self.list = self._get_nowlist()
            self.scetable[self.nowdir] = self.list
            self.list = self._narrow_scenario(self.list)
            self.index = 0

            if exists:
                fname = os.path.normcase(spaths[-1])
                for index, sel in enumerate(self.list):
                    if isinstance(sel, cw.header.ScenarioHeader):
                        name = sel.fname
                    else:
                        name = os.path.basename(sel)
                    if os.path.normcase(name) == fname:
                        self.index = index
                        if self.tree.IsShown():
                            item, cookie = self.tree.GetFirstChild(treeitem)
                            i = 0
                            while item.IsOk() and i <> index:
                                item, cookie = self.tree.GetNextChild(treeitem, cookie)
                                i += 1
                            assert item.IsOk()
                            self.tree.SelectItem(item)
                            if not isinstance(sel, cw.header.ScenarioHeader):
                                self.tree.Expand(item)
                                self.create_treeitems(item)
                        break

        self._processing = processing
        self.draw(True)
        self.enable_btn()
        if self.list:
            self._enable_btn2(self.list[self.index])
        self._update_saveddirstack()

    def _update_saveddirstack(self):
        if len(self.dirstack) == 1 and self.dirstack[0][0].startswith("/"):
            return
        self._saved_dirstack = self.dirstack[:]
        self._saved_list = self.list[:]
        self._saved_index = self.index

    def index_changed(self):
        self._update_saveddirstack()

    def OnDropFiles(self, event):
        paths = event.GetFiles()

        for path in paths:
            self.conv_scenario(path)
            time.sleep(0.3)

    def OnClickInfoBtn(self, event):
        cw.cwpy.sounds["click"].play()
        dlg = text.Readme(self, cw.cwpy.msgs["description"], self.texts)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def OnClickConvBtn(self, evt):
        # ディレクトリ選択ダイアログ
        s = (u"カードワースのシナリオデータをカードワースパイ用に変換します。" +
             u"\n変換するシナリオのディレクトリを選択してください。")
        dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
        dlg.SetPath(os.getcwdu())

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.conv_scenario(path)
        else:
            dlg.Destroy()

    def OnClickYesBtn(self, event):
        if self.yesbtn.GetLabel() == cw.cwpy.msgs["see"]:
            assert not self.tree.IsShown()
            cw.cwpy.sounds["equipment"].play()
            if isinstance(self.list[self.index], FindResult):
                self.dirstack.append((self.nowdir, "/find_result"))
                self.nowdir = self.list[self.index]
            else:
                self.dirstack.append((self.nowdir, os.path.basename(self.list[self.index])))
                self.nowdir = cw.util.get_linktarget(self.list[self.index])
            self._update_saveddirstack()
            self.list = self._get_nowlist()
            self.scetable[self.nowdir] = self.list
            self.list = self._narrow_scenario(self.list)
            self.index = 0
            self.enable_btn()
            self.draw(True)
        elif self.yesbtn.GetLabel() == cw.cwpy.msgs["decide"]:
            self._update_saveddirstack()
            cw.cwpy.sounds["signal"].play()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

    def OnClickNoBtn(self, event):
        if self.nobtn.GetLabel() == cw.cwpy.msgs["return"]:
            assert not self.tree.IsShown()
            cw.cwpy.sounds["equipment"].play()
            self.nowdir, selname = self.dirstack.pop()
            self.list = self._get_nowlist()
            self.scetable[self.nowdir] = self.list
            self.list = self._narrow_scenario(self.list)
            self.index = 0
            if not selname.startswith("/"):
                selname = os.path.normcase(selname)
                for index, name in enumerate(self.list):
                    if not isinstance(name, (cw.header.ScenarioHeader, FindResult)):
                        name = os.path.normcase(os.path.basename(name))
                        if selname == name:
                            self.index = index

            self.enable_btn()

            self.draw(True)
        elif self.nobtn.GetLabel() == cw.cwpy.msgs["entry_cancel"]:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

    def OnClickViewBtn(self, event):
        cw.cwpy.sounds["equipment"].play()
        if self.tree.IsShown():
            self.tree.Hide()
            self.toppanel.Show()
            self.draw(True)
        else:
            self.show_tree()
            self.toppanel.Hide()
            self.tree.Show()
            self.tree.SetFocus()

        self.enable_btn()

    def OnSelect(self, event):
        if not self.list or not self.yesbtn.Enabled:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        if self.nobtn.GetLabel() == cw.cwpy.msgs["entry_cancel"]:
            cw.cwpy.sounds["click"].play()

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_NO)
        self.ProcessEvent(btnevent)

    def OnDestroy(self, event):
        self.db.close()
        if self.bookmarkmenu:
            self.bookmarkmenu.Destroy()

    def _on_narrowcondition(self):
        #cw.cwpy.setting.scenario_narrow = self.narrow.GetValue()
        cw.cwpy.setting.scenario_narrowtype = self.narrow_type.GetSelection()
        cw.cwpy.setting.scenario_sorttype = self.sort.GetSelection()
        self.update_narrowcondition()

    def draw(self, update=False):
        self._draw_impl(update)

    def _draw_impl(self, update=False, dc=None):
        if update:
            self.enable_btn()

        if self.tree.IsShown():
            self.select_treeitem(self.index)
            return

        if not dc:
            dc = Select.draw(self, update)

        # 背景
        path = "Table/Bill"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins((cw.util.load_wxbmp(path), cw.SIZE_BILL))
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        # ページ番号
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
        s = str(self.index+1) if self.list else str(0)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        cw.util.draw_witharound(dc, s, bmpw-w-cw.wins(10), cw.wins(10))

        if not isinstance(self.list[self.index], cw.header.ScenarioHeader):
            dpath = self.list[self.index]

            if update:
                if isinstance(dpath, FindResult):
                    self.names = dpath.headers
                else:
                    if self.updatenames_thr:
                        self.updatenames_thr.quit = True
                        self.updatenames_thr = None
                    self.names = [u"読込中..."]
                    self.updatenames_thr = UpdateNamesThread(self, dpath, self.dirstack[:],
                                                             startdir=dpath, expandedset=set(),
                                                             skintype=cw.cwpy.setting.skintype)
                    self.updatenames_thr.start()

            # Folder.bmpチェック
            if isinstance(dpath, FindResult):
                scan_folder_bmp = ""
            else:
                scan_folder_bmp = os.path.join(cw.util.get_linktarget(dpath), u"Folder.bmp")
            if scan_folder_bmp and os.path.isfile(scan_folder_bmp):
                # Folder.bmp表示
                folder_bmp = cw.util.load_wxbmp(scan_folder_bmp, True)
                cw.util.draw_center(dc, cw.wins(folder_bmp), cw.wins((200, 60)), True)

            else:
                # ディレクトリ名
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(22)))
                if isinstance(dpath, FindResult):
                    s = cw.cwpy.msgs["find_result"]
                else:
                    s = os.path.basename(dpath)
                    if s.lower().endswith(".lnk"):
                        s = s[0:-len(".lnk")]
                dc.DrawText(s, cw.wins(135), cw.wins(65))
                # フォルダ画像
                bmp = cw.cwpy.rsrc.dialogs["FOLDER"]
                dc.DrawBitmap(bmp, cw.wins(65), cw.wins(30), True)

                if not isinstance(dpath, FindResult):
                    if sys.platform == "win32" and dpath.lower().endswith(".lnk"):
                        # リンクシンボル
                        bmp = cw.cwpy.rsrc.dialogs["LINK"]
                        dc.DrawBitmap(bmp, cw.wins(63), cw.wins(65), False)

            # contents
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(16)))
            s = cw.cwpy.msgs["contents"]
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(110))
            # 中身
            font = cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14), adjustsize=True)
            font2 = cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(12))

            names = self._narrow_scenario(self.names)
            if len(names) > 13:
                names = names[0:12]
                names.append(cw.cwpy.msgs["history_etc"])

            y = cw.wins(130)
            for name in names:
                addition = ""
                if isinstance(name, cw.header.ScenarioHeader):
                    header = name
                    name = name.name
                    if self.sort.GetSelection() == 2:
                        # 整列条件: 作者名
                        if header.author:
                            addition = u"(%s)" % (header.author)
                    elif self.sort.GetSelection() == 3:
                        # 整列条件: 更新日時
                        addition = u"[%s]" % (self._formatted_mtime(header.mtime, False))
                    elif header.levelmin or header.levelmax:
                        levelmin = str(header.levelmin) if header.levelmin else " "
                        levelmax = str(header.levelmax) if header.levelmax else " "
                        if levelmin == levelmax:
                            addition = u"[%s]" % (levelmin)
                        else:
                            addition = u"[%s～%s]" % (levelmin, levelmax)
                    if self.is_playing(header) or self.is_complete(header) or self.is_invisible(header):
                        dc.SetTextForeground((128, 128, 128))
                    else:
                        dc.SetTextForeground((0, 0, 0))
                else:
                    if isinstance(dpath, FindResult):
                        name = u"[%s]" % (os.path.basename(name))
                    dc.SetTextForeground((0, 0, 0))

                dc.SetFont(font)
                size = dc.GetTextExtent(name)
                space = cw.wins(3)
                if addition:
                    dc.SetFont(font2)
                    size2 = dc.GetTextExtent(addition)
                    x = (bmpw - (size[0]+space+size2[0])) / 2
                    x += cw.wins(10) # 左に寄って見えるので若干右寄りにする
                else:
                    x = (bmpw - size[0]) / 2

                dc.SetFont(font)
                dc.DrawText(name, x, y)

                if addition:
                    dc.SetFont(font2)
                    dc.SetTextForeground((128, 128, 128))
                    x2 = x + space + size[0]
                    y2 = y + ((size[1] - size2[1]) / 2) + 1
                    dc.DrawText(addition, x2, y2)

                y += cw.wins(15)

            self._enable_btn2(dpath, dc=dc)
        else:
            header = self.list[self.index]

            # 見出し画像
            if header.image:
                bmp = header.get_wxbmp()
                w = bmp.GetSize()[0]
                # 左上位置固定(互換性維持)
                dc.DrawBitmap(bmp, cw.wins(163), cw.wins(70), True)

            # シナリオ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(22)))
            s = header.name
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, cw.wins(35))
            # 解説文
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
            s = header.desc
            y = cw.wins(180)
            for l in s.splitlines():
                dc.DrawText(l, cw.wins(65), y)
                y += cw.wins(15)
            # 対象レベル
            dc.SetTextForeground(wx.Colour(0, 128, 128, 255))
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle",
                                            style=wx.FONTSTYLE_ITALIC, pixelsize=cw.wins(16)))
            levelmax = str(header.levelmax) if header.levelmax else ""
            levelmin = str(header.levelmin) if header.levelmin else ""

            if levelmax or levelmin:
                if levelmin == levelmax:
                    s = cw.cwpy.msgs["target_level_1"] % (levelmin)
                else:
                    s = cw.cwpy.msgs["target_level_2"] % (levelmin, levelmax)

                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)/2, cw.wins(15))

            self._enable_btn2(header, dc=dc)

        if update:
            fc = wx.Window.FindFocus()
            if fc <> self.narrow:
                buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
                if buttonlist:
                    buttonlist[0].SetFocus()

    def _enable_btn2(self, header, dc=None):
        bmpw = self.toppanel.GetClientSize()[0]
        if isinstance(header, cw.header.ScenarioHeader):
            # 進行中チェック
            if self.is_playing(header):
                if dc:
                    bmp = cw.cwpy.rsrc.dialogs["PLAYING"]
                    w = bmp.GetSize()[0]
                    dc.DrawBitmap(bmp, (bmpw-w)/2, cw.wins(152), True)
            # 済み印存在チェック
            elif self.is_complete(header):
                if dc:
                    bmp = cw.cwpy.rsrc.dialogs["COMPLETE"]
                    w = bmp.GetSize()[0]
                    dc.DrawBitmap(bmp, (bmpw-w)/2, cw.wins(175), True)
            # クーポン存在チェック
            elif self.is_invisible(header):
                if dc:
                    bmp = cw.cwpy.rsrc.dialogs["INVISIBLE"]
                    w = bmp.GetSize()[0]
                    dc.DrawBitmap(bmp, (bmpw-w)/2, cw.wins(100), True)

    def is_playing(self, header):
        return header.get_fpath() in self.nowplayingpaths

    def is_complete(self, header):
        return header.name in self.stamps

    def is_invisible(self, header):
        if not header.coupons:
            return False

        num = 0

        for coupon in header.coupons.splitlines():
            if coupon:
                num += self.coupons.get(coupon, 0)

        return num < header.couponsnum

    def update_narrowcondition(self):
        self._processing = True
        selected = self.list[self.index] if self.list else None
        if self.tree.IsShown():
            def recurse(parent):
                index, nowdir = self.tree.GetItemPyData(parent)
                if not nowdir in self.scetable:
                    return

                item, cookie = self.tree.GetFirstChild(parent)
                delitems = []
                while item.IsOk():
                    data = self.tree.GetItemPyData(item)
                    if not data is None:
                        index, header = data
                        if isinstance(header, cw.header.ScenarioHeader):
                            delitems.append(item)
                        elif isinstance(header, FindResult) or self.tree.IsExpanded(item):
                            recurse(item)
                    item, cookie = self.tree.GetNextChild(item, cookie)
                for item in delitems:
                    self.tree.Delete(item)

                for index, header in enumerate(self._narrow_scenario(self.scetable[nowdir])):
                    if isinstance(header, cw.header.ScenarioHeader):
                        item = self.create_treeitem(index, parent, header)
                        if isinstance(selected, cw.header.ScenarioHeader) and\
                                selected.dpath == header.dpath and selected.fname == header.fname:
                            self.tree.SelectItem(item)

            recurse(self.tree.root)
            # スクロースしないほうが操作性がよい
            #item = self.tree.GetSelection()
            #if item and not self.tree.IsVisible(item):
            #    self.tree.ScrollTo(item)
        else:
            self.list = self.scetable[self.nowdir]
            self.list = self._narrow_scenario(self.list)

        self._processing = False

        # 選択のやり直し
        if selected and selected in self.list:
            self.index = self.list.index(selected)
            if not self.tree.IsShown():
                dc = wx.ClientDC(self.toppanel)
                dc = wx.BufferedDC(dc)
                self._draw_impl(False, dc)
        else:
            self.index = max(0, min(self.index, len(self.list)-1))
            if not self.tree.IsShown():
                self.draw(True)

        self._update_saveddirstack()

    def create_treeitems(self, treeitem):
        self.tree.DeleteChildren(treeitem)
        index, nowdir = self.tree.GetItemPyData(treeitem)
        itemlist = []
        dpaths = []

        if not nowdir in self.scetable:
            self.scetable[nowdir] = self._get_nowlist(nowdir)

        for index, header in enumerate(self._narrow_scenario(self.scetable[nowdir])):
            if isinstance(header, cw.header.ScenarioHeader):
                item = self.create_treeitem(index, treeitem, header)
                itemlist.append(item)
            elif isinstance(header, FindResult):
                item = self._create_findresultitem(index, treeitem, header)
                itemlist.append(item)
                dpaths.append("/find_result")
            else:
                dpath = header
                name = os.path.basename(dpath)
                image = self.tree.imgidx_dir
                if sys.platform == "win32" and name.lower().endswith(".lnk"):
                    name = cw.util.splitext(name)[0]
                item = self.tree.AppendItem(treeitem, name, image)
                self.tree.SetItemPyData(item, (index, dpath))
                child = self.tree.AppendItem(item, u"読込中...")
                self.tree.SetItemPyData(child, None)
                self.tree.Collapse(item)
                itemlist.append(item)
                dpaths.append(dpath)

        if not treeitem is self.tree.root:
            self.tree.Expand(treeitem)

        return itemlist, dpaths

    def _create_findresultitem(self, index, treeitem, findresult):
        image = self.tree.imgidx_findresult
        item = self.tree.InsertItemBefore(treeitem, index, cw.cwpy.msgs["find_result"], image)
        self.tree.SetItemPyData(item, (index, findresult))
        if findresult.headers:
            self.create_treeitems(item)
        else:
            child = self.tree.AppendItem(item, cw.cwpy.msgs["find_notfound"])
            self.tree.SetItemPyData(child, None)
        return item

    def _formatted_mtime(self, mtime, showtime):
        d = datetime.datetime.fromtimestamp(mtime)
        if showtime:
            return d.strftime("%Y-%m-%d %H:%M")
        else:
            return d.strftime("%Y-%m-%d")

    def create_treeitem(self, index, treeitem, header):
        name = header.name
        image = self.tree.imgidx_summary
        if self.is_playing(header):
            image = self.tree.imgidx_playing
        elif self.is_complete(header):
            image = self.tree.imgidx_complete
        elif self.is_invisible(header):
            image = self.tree.imgidx_invisible
        if header.levelmin <> 0 or header.levelmax <> 0:
            if header.levelmin == header.levelmax:
                name = u"[    %2d] %s" % (header.levelmin, name)
            else:
                levelmin = str(header.levelmin) if header.levelmin else ""
                levelmax = str(header.levelmax) if header.levelmax else ""
                name = u"[%2s～%2s] %s" % (levelmin, levelmax, name)

        if self.sort.GetSelection() == 3:
            # 日時による整列中
            name = u"%s (%s)" % (name, self._formatted_mtime(header.mtime, True))
        elif self.sort.GetSelection() == 2 and header.author:
            # 作者名による整列中
            name = u"%s (%s)" % (name, header.author)

        item = self.tree.AppendItem(treeitem, name, image)
        self.tree.SetItemPyData(item, (index, header))
        return item

    def show_tree(self):
        # ツリーを初期化する
        self.tree.DeleteChildren(self.tree.root)

        treeitem = self.tree.root
        itemlist = []
        dirstack = self.dirstack[:]
        while True:
            itemlist, dpaths = self.create_treeitems(treeitem)

            if dirstack:
                _pardir, selname = dirstack.pop(0)
                index = -1
                for i, dpath in enumerate(dpaths):
                    if dpath.startswith("/"):
                        if dpath == selname:
                            index = i
                            break
                    elif os.path.normcase(selname) == os.path.normcase(os.path.basename(dpath)):
                        index = i
                        break
                if index == -1:
                    break
                treeitem = itemlist[index]
                self.tree.DeleteChildren(treeitem)
            else:
                if itemlist:
                    treeitem = itemlist[self.index]
                    self.tree.SelectItem(treeitem)
                else:
                    self.tree.SelectItem(treeitem)
                    self._tree_selchanged()

                # 検索結果ディレクトリを選択中であれば展開する
                data = self.tree.GetItemPyData(treeitem)
                if data and isinstance(data[1], FindResult):
                    self.tree.Expand(treeitem)
                break

    def OnTreeItemExpanded(self, event):
        if self._processing:
            return

        selitem = event.GetItem()
        data = self.tree.GetItemPyData(selitem)
        if data is None or isinstance(data[1], FindResult):
            return
        _index, dpath = data
        self._expandeditem(selitem, startdir=dpath, expandedset=set())

    def _expandeditem(self, selitem, startdir, expandedset):
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        if self._processing:
            return

        data = self.tree.GetItemPyData(selitem)
        if data and isinstance(data[1], FindResult):
            # 検索結果に対しては何もしない
            return

        item, _cookie = self.tree.GetFirstChild(selitem)
        data = self.tree.GetItemPyData(item)
        if not data is None:
            # 読込済み
            return

        _index, dpath = self.tree.GetItemPyData(selitem)
        ndpath = cw.util.get_linktarget(dpath)
        ndpath = os.path.abspath(ndpath)
        ndpath = os.path.normpath(ndpath)
        ndpath = os.path.normcase(ndpath)
        if ndpath in expandedset:
            return
        expandedset.add(ndpath)

        if self.updatenames_thr:
            self.updatenames_thr.quit = True
            self.updatenames_thr = None
        self.names = [u"読込中..."]
        paritem = self.tree.GetItemParent(selitem)
        dirstack = self.get_dirstack(paritem)
        self.updatenames_thr = UpdateNamesThread(self, dpath, dirstack,
                                                 startdir=startdir, expandedset=expandedset,
                                                 skintype=cw.cwpy.setting.skintype)
        self.updatenames_thr.start()

    def OnTreeItemCollapsed(self, event):
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        # 一旦リストをクリアして次に開いた時に再読込を行う
        item = event.GetItem()
        data = self.tree.GetItemPyData(item)
        if data and isinstance(data[1], FindResult):
            # 検索結果はクリアしない
            return
        self.tree.DeleteChildren(item)
        child = self.tree.AppendItem(item, u"読込中...")
        self.tree.SetItemPyData(child, None)
        self.tree.Collapse(item)

    def OnTreeSelChanged(self, event):
        if self._processing:
            return
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        self._tree_selchanged()

    def _tree_selchanged(self):
        selitem = self.tree.GetSelection()
        paritem = self.tree.GetItemParent(selitem)

        if self.tree.GetItemPyData(selitem) is None:
            # "読込中..."なので一つ上の階層を選択
            selitem = paritem
            paritem = self.tree.GetItemParent(selitem)

        _index, self.nowdir = self.tree.GetItemPyData(paritem)
        self.index, _pathorheader = self.tree.GetItemPyData(selitem)

        self.list = self._get_nowlist()
        self.scetable[self.nowdir] = self.list
        self.list = self._narrow_scenario(self.list)

        self.dirstack = self.get_dirstack(paritem)
        self._update_saveddirstack()

        self.enable_btn()

    def get_dirstack(self, paritem):
        dirstack = []
        while paritem:
            _i, parpath = self.tree.GetItemPyData(paritem)
            _i, selpath = self.tree.GetItemPyData(paritem)
            if isinstance(parpath, FindResult):
                parpath = self.scedir
            else:
                parpath = os.path.dirname(parpath)
            if isinstance(selpath, FindResult):
                selpath = "/find_result"
            else:
                selpath = os.path.basename(selpath)
            dirstack.insert(0, (parpath, selpath))

            paritem = self.tree.GetItemParent(paritem)
        return dirstack[1:]

    def select_treeitem(self, index):
        item = self.tree.GetSelection()
        item = self.tree.GetItemParent(item)
        item, cookie = self.tree.GetFirstChild(item)
        i = 0
        while item.IsOk():
            if i == index:
                self.tree.SelectItem(item)
                self.index = index
                break
            item, cookie = self.tree.GetNextChild(item, cookie)
            i += 1

    def updated_names(self, dpath, dirstack, startdir, expandedset):
        if not self.tree.IsShown():
            self.Refresh()
            return

        if not self.tree.IsShownOnScreen():
            return

        # dpathからツリーアイテムを検索
        parent = self.tree.root
        item = None
        dirstack.append(("", dpath))
        while dirstack:
            item, cookie = self.tree.GetFirstChild(parent)
            if not item.IsOk():
                break

            parent = None
            while item.IsOk():
                _i, data = self.tree.GetItemPyData(item)
                if not data:
                    break
                if isinstance(data, (cw.header.ScenarioHeader, FindResult)):
                    if dirstack[0][1] == "/find_result":
                        parent = item
                        dirstack.pop(0)
                        break
                else:
                    name = os.path.normcase(os.path.basename(data))
                    if name == os.path.normcase(os.path.basename(dirstack[0][1])):
                        parent = item
                        dirstack.pop(0)
                        break
                item, cookie = self.tree.GetNextChild(item, cookie)

            if not parent:
                break

        if item and item.IsOk():
            # ディレクトリの内容を表示
            self.create_treeitems(item)

        # 次のディレクトリを展開する
        ##baseitem = item
        ##
        ##def expand(item):
        ##    data = self.tree.GetItemPyData(item)
        ##    if not data is None:
        ##        index, header = data
        ##        if not isinstance(header, (cw.header.ScenarioHeader, FindResult)):
        ##            ndpath = cw.util.get_linktarget(header)
        ##            ndpath = os.path.abspath(ndpath)
        ##            ndpath = os.path.normpath(ndpath)
        ##            ndpath = os.path.normcase(ndpath)
        ##            if ndpath in expandedset:
        ##                return False
        ##
        ##            processing = self._processing
        ##            self._processing = True
        ##            self.tree.Expand(item)
        ##            self._processing = processing
        ##            self._expandeditem(item, startdir, expandedset)
        ##            return True
        ##    return False
        ##
        ### サブディレクトリを優先して展開
        ##item, cookie = self.tree.GetFirstChild(baseitem)
        ##while item.IsOk():
        ##    if expand(item):
        ##        return
        ##    item, cookie = self.tree.GetNextChild(item, cookie)
        ##
        ### サブディレクトリがない場合は次のアイテムを選択
        ### それもない場合は上位ディレクトリへ遡る
        ##while baseitem and baseitem.IsOk():
        ##    data = self.tree.GetItemPyData(baseitem)
        ##    if data and data[1] == startdir:
        ##        return
        ##
        ##    item = self.tree.GetNextSibling(baseitem)
        ##    if item and item.IsOk():
        ##        if expand(item):
        ##            return
        ##    # 一つ上へ辿って次のフォルダを探す
        ##    baseitem = self.tree.GetItemParent(baseitem)

    def _narrow_scenario(self, headers):
        """設定に応じて表示しないシナリオを除去する。"""
        if not cw.cwpy.setting.show_unfitnessscenario:
            pcards = cw.cwpy.get_pcards("unreversed")
            level = sum([pcard.level for pcard in pcards]) / len(pcards)

        dseq = []
        seq = []
        narrow = self.narrow.GetValue().lower()
        donarrow = bool(narrow)
        ntype = self.narrow_type.GetSelection()
        if ntype == 3 and donarrow:
            # レベル
            try:
                narrow = int(narrow)
            except:
                narrow = ""
        for header in headers:
            if isinstance(header, cw.header.ScenarioHeader):
                if not cw.cwpy.setting.show_unfitnessscenario and not (ntype == 3 and donarrow) and\
                        ((header.levelmin <> 0 and level < header.levelmin) or\
                         (header.levelmax <> 0 and header.levelmax < level)):
                    continue
                if not cw.cwpy.setting.show_completedscenario and self.is_complete(header):
                    continue
                if not cw.cwpy.setting.show_invisiblescenario and self.is_invisible(header):
                    continue

                if donarrow:
                    if ntype == 0:
                        # タイトルで絞り込み
                        if not narrow in header.name.lower():
                            continue
                    elif ntype == 1:
                        # 解説で絞り込み
                        if not narrow in header.desc.lower():
                            continue
                    elif ntype == 2:
                        # 作者名で絞り込み
                        if not narrow in header.author.lower():
                            continue
                    elif ntype == 3:
                        # 対象レベルで絞り込み
                        if not (header.levelmin <= narrow <= header.levelmax):
                            continue
                    else:
                        assert False
                seq.append(header)
            else:
                dseq.append(header)

        return dseq + self._sort_headers(seq)

    def _sort_headers(self, seq):
        sort = self.sort.GetSelection()
        if sort == 0:
            # 対象レベル。最初からソート済み
            pass
        elif sort == 1:
            # タイトル
            cw.util.sort_by_attr(seq, "name")
        elif sort == 2:
            # 作者名
            cw.util.sort_by_attr(seq, "author")
        elif sort == 3:
            # 更新日時
            cw.util.sort_by_attr(seq, "mtime")
            seq.reverse()
        return seq

    def enable_btn(self):
        if self._processing:
            return
        # リストが空だったらボタンを無効化
        if not self.list:
            self.yesbtn.Enable(False)
            self.infobtn.Enable(False)
            self.viewbtn.Enable(bool(self.dirstack))
            self.nobtn.Enable()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
            self.SetTitle(u"貼紙を見る")
            return

        self.texts = self.get_texts()
        if len(self.list) == 1:
            self.infobtn.Enable(bool(self.texts))
            self.viewbtn.Enable()
            self.nobtn.Enable()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self.infobtn.Enable(bool(self.texts))
            self.viewbtn.Enable()
            self.nobtn.Enable()
            self.rightbtn.Enable()
            self.right2btn.Enable()
            self.leftbtn.Enable()
            self.left2btn.Enable()

        selected = self.list[self.index]

        # 状況によってボタンのテキストを更新
        if self.tree.IsShown():
            self.viewbtn.SetLabel(cw.cwpy.msgs["scenario_one"])
        else:
            self.viewbtn.SetLabel(cw.cwpy.msgs["scenario_tree"])

        if not self.list or isinstance(selected, cw.header.ScenarioHeader) or self.tree.IsShown():
            self.yesbtn.SetLabel(cw.cwpy.msgs["decide"])
        else:
            self.yesbtn.SetLabel(cw.cwpy.msgs["see"])

        if self.dirstack and not self.tree.IsShown():
            self.nobtn.SetLabel(cw.cwpy.msgs["return"])
        else:
            self.nobtn.SetLabel(cw.cwpy.msgs["entry_cancel"])

        enable = True
        if not self.list:
            enable = False
        elif isinstance(selected, cw.header.ScenarioHeader):
            # 進行中チェック
            if self.is_playing(selected):
                if not cw.cwpy.debug:
                    enable = False
            # 済み印存在チェック
            elif self.is_complete(selected):
                if not cw.cwpy.debug:
                    enable = False
            # クーポン存在チェック
            elif self.is_invisible(selected):
                if not cw.cwpy.debug:
                    enable = False
        elif isinstance(selected, FindResult):
            if self.tree.IsShown():
                enable = False
        else:
            dpath = selected
            if self.tree.IsShown() or not os.path.isdir(cw.util.get_linktarget(dpath)):
                enable = False
        self.yesbtn.Enable(enable)

        # 選択中のファイル名またはディレクトリ名を表示
        if isinstance(selected, cw.header.ScenarioHeader):
            fname = selected.fname
            author = selected.author
        elif isinstance(selected, FindResult):
            fname = cw.cwpy.msgs["find_result"]
            author = ""
        else:
            fname = os.path.basename(selected)
            author = ""
        if sys.platform == "win32" and cw.util.splitext(fname)[1].lower() == ".lnk":
            fname = cw.util.splitext(fname)[0]
        name = u"貼紙を見る [ %s ]" % (fname)
        if author:
            name = u"%s (%s)" % (name, author)
        self.SetTitle(name)

    def get_dpaths(self, dpath):
        """
        クラシックなシナリオ以外のフォルダの一覧を返す。
        (ショートカット類も含む)
        """
        seq = []

        try:
            dpath2 = cw.util.get_linktarget(dpath)
            for dname in os.listdir(dpath2):
                path = cw.util.join_paths(dpath2, dname)
                if self.is_listitem(path) and not self.is_scenario(path):
                    seq.append(path)
        except Exception:
            cw.util.print_ex()

        return seq

    def is_listitem(self, path):
        """
        指定されたパスが選択可能ならTrueを返す。
        """
        return os.path.isdir(path) or\
            (sys.platform == "win32" and path.lower().endswith(".lnk")) or\
            self.is_scenario(path)

    def is_scenario(self, path):
        """
        指定されたパスがシナリオならTrueを返す。
        """
        return cw.scenariodb.is_scenario(path)

    def get_texts(self):
        """
        選択中シナリオに同梱されている
        テキストファイルのファイル名とデータのリストを返す。
        """
        if not self.list:
            return []

        seq = []
        if isinstance(self.list[self.index], cw.header.ScenarioHeader):
            header = self.list[self.index]
            path = header.get_fpath()
            path = cw.util.get_linktarget(path)
            if os.path.isfile(path):
                # 圧縮ファイル内から取得
                if path.lower().endswith(".cab"):
                    dpath = cw.util.join_paths(cw.tempdir, u"Cab")
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    s = "expand \"%s\" -f:%s \"%s\"" % (path, "*.txt", dpath)
                    try:
                        encoding = sys.getfilesystemencoding()
                        if subprocess.call(s.encode(encoding), shell=True) == 0:
                            for dpath2, _dnames, fnames in os.walk(dpath):
                                for fname in fnames:
                                    fname = cw.util.decode_zipname(fname)
                                    if fname.lower().endswith(".txt"):
                                        dpath2 = cw.util.decode_zipname(dpath2)
                                        with open(cw.util.join_paths(dpath2, fname), "r") as f:
                                            content = f.read()
                                        seq.append(text.ReadmeData(fname, content))
                    finally:
                        for fpath in os.listdir(dpath):
                            fpath = cw.util.decode_zipname(fpath)
                            fpath = cw.util.join_paths(dpath, fpath)
                            cw.util.remove(fpath)

                else:
                    with cw.util.zip_file(path, "r") as z:
                        names = [name for name in z.namelist() if name.lower().endswith(".txt")]

                        for name in names:
                            data = z.read(name)
                            name = os.path.basename(name)
                            name = cw.util.decode_zipname(name)
                            seq.append(text.ReadmeData(name, data))

            else:

                # フォルダ内から取得
                paths = []
                for dpath, _dnames, fnames in os.walk(path):
                    for fname in fnames:
                        if fname.lower().endswith(".txt"):
                            paths.append(cw.util.join_paths(dpath, fname))

                for fpath in paths:
                    with open(fpath, "r") as f:
                        data = f.read()
                    name = cw.util.relpath(fpath, path)
                    name = cw.util.join_paths(name)
                    seq.append(text.ReadmeData(name, data))

        elif not isinstance(self.list[self.index], FindResult):
            dpath = cw.util.get_linktarget(self.list[self.index])
            for fname in os.listdir(dpath):
                if os.path.splitext(fname)[1].lower().endswith(".txt"):
                    fpath = cw.util.join_paths(dpath, fname)
                    with open(fpath, "r") as f:
                        data = f.read()
                    seq.append(text.ReadmeData(fname, data))

        return seq

    def conv_scenario(self, path):
        """
        CardWirthのシナリオデータを変換。
        """
        # CardWirthのシナリオデータか確認
        if not os.path.isfile(cw.util.join_paths(path, "Summary.wsm")):

            s = u"カードワースのシナリオのディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        cw.cwpy.sounds["click"].play()
        s = os.path.basename(path) + u"　を変換します。\nよろしいですか？"
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        dlg.Destroy()
        # シナリオデータ
        cwdata = cw.binary.cwscenario.CWScenario(
            path, cw.util.join_paths(cw.tempdir, u"OldScenario"), cw.cwpy.setting.skintype,
            materialdir="Material", image_export=True)

        # 変換可能なデータか確認
        if not cwdata.is_convertible():
            s = u"CardWirth ver1.20以上対応の\nシナリオしか変換できません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 宿データ読み込み
        cwdata.load()
        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            cwdata.name + u" 変換", "", maximum=cwdata.maxnum,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(cwdata)
        thread.start()

        while not thread.complete:
            dlg.Update(cwdata.curnum, cwdata.message)
            wx.MilliSleep(1)

        dlg.Destroy()
        temppath = thread.path

        # エラーログ表示
        if cwdata.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # zip圧縮
        zpath = os.path.basename(temppath) + ".wsn"
        zpath = cw.util.join_paths(self.nowdir, zpath)
        zpath = cw.util.dupcheck_plus(zpath, False)
        cw.util.compress_zip(temppath, zpath, unicodefilename=True)
        cw.cwpy.sounds["harvest"].play()
        # 変換完了ダイアログ
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        # tempを削除
        cw.util.remove(temppath)
        # 更新処理
        self.db.insert_scenario(zpath, skintype=cw.cwpy.setting.skintype)
        self.list = self._get_nowlist()
        self.scetable[self.nowdir] = self.list
        self.list = self._narrow_scenario(self.list)
        self.index = 0

        # 変換したシナリオのインデックスを取得
        header = None
        for index, lheader in enumerate(self.list):
            if not hasattr(lheader, "fname"):
                continue

            if os.path.basename(zpath) == lheader.fname:
                self.index = index
                header = lheader
                break

        # ツリー表示中の場合は追加
        if self.tree.IsShown() and header:
            name = header.name
            image = self.tree.imgidx_summary
            if self.is_playing(header):
                image = self.tree.imgidx_playing
            elif self.is_complete(header):
                image = self.tree.imgidx_complete
            elif self.is_invisible(header):
                image = self.tree.imgidx_invisible
            parent = self.tree.GetSelection()
            prev = None
            i = 0
            item, cookie = self.tree.GetFirstItem(parent)
            while item.IsOk():
                if i == self.index:
                    prev = item
                    break
                item, cookie = self.tree.GetNextItem(item, cookie)
                i += 1
            if prev:
                item = self.tree.InsertItem(parent, prev, name, image)
            else:
                item = self.tree.AppendItem(parent, name, image)
            self.tree.SelectItem(item)
            self.tree.SetItemPyData(item, (self.index, header))

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.enable_btn()

class FindResult(object):
    def __init__(self):
        self.headers = []

class UpdateNamesThread(threading.Thread):

    def __init__(self, dlg, dpath, dirstack, startdir, expandedset, skintype):
        threading.Thread.__init__(self)
        self.dlg = dlg
        self.nowdir = dlg.nowdir
        self.dpath = dpath
        self.dirstack = dirstack
        self.dpaths = dlg.get_dpaths(dpath)
        self.quit = False
        self.startdir = startdir
        self.expandedset = expandedset
        self.skintype = skintype

    def run(self):
        """ScenarioSelectで現在表示中のディレクトリ内の
        シナリオ・ディレクトリのリストを生成する。
        """
        self._start()

    @synclock(_lockupdatescenario)
    def _start(self):
        if self.quit: return
        # dpathの中にあるシナリオをDBに登録
        db = cw.scenariodb.Scenariodb()
        db.update(self.dpath, skintype=self.skintype)
        if self.quit: return
        # dpathの中にあるシナリオ名のリスト
        headers = db.search_dpath(self.dpath, skintype=self.skintype)
        # dpathの中にあるディレクトリ名のリスト
        dnames = []

        if self.quit: return
        for path in self.dpaths:
            if path.lower().endswith(".lnk"):
                path = path[0:-len(".lnk")]
            dname = u"[%s]" % (os.path.basename(path))
            dnames.append(dname)
        def func():
            if self.dlg:
                if self.dlg.nowdir == self.nowdir:
                    self.dlg.names = dnames + headers
                if self.quit: return
                wx.CallAfter(self.dlg.updated_names, self.dpath, self.dirstack, self.startdir, self.expandedset)
                self.dlg.updatenames_thr = None
        cw.cwpy.frame.exec_func(func)

def main():
    pass

if __name__ == "__main__":
    main()
