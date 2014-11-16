#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import itertools
import threading
import shutil

import wx
import pygame
import wx.lib.mixins.listctrl as listmix

import cw


class BattleCommand(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["select_battle_action"])
        self.list = []

        # 行動開始
        path = "Resource/Image/Card/BATTLE" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        # TODO scaleinfo
        header = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["start_action"])
        w = cw.scr2win_s(header.rect.width)
        h = cw.scr2win_s(header.rect.height)
        header.rect = pygame.Rect(cw.wins(5), cw.wins(5), w, h)
        header.clickedflag = False
        header.lclick_event = self.start
        header.negaflag = False
        self.list.append(header)

        self.toppanel = wx.Panel(self, -1, size=((w+cw.wins(5))*3+cw.wins(5), h+cw.wins(5)*2))

        # 逃げる
        path = "Resource/Image/Card/ACTION9" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        # TODO scaleinfo
        header = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["runaway"])
        header.rect = pygame.Rect((w+cw.wins(5))*1+cw.wins(5), cw.wins(5), w, h)
        header.clickedflag = False
        header.negaflag = False
        header.lclick_event = self.runaway
        self.list.append(header)
        # キャンセル
        path = "Resource/Image/Card/COMMAND1" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        # TODO scaleinfo
        header = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["cancel"])
        header.rect = pygame.Rect((w+cw.wins(5))*2+cw.wins(5), cw.wins(5), w, h)
        header.clickedflag = False
        header.negaflag = False
        header.lclick_event = self.cancel
        self.list.append(header)

        self._do_layout()
        self._bind()

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _bind(self):
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMove)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.toppanel.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)

        self.leftkeyid = wx.NewId()
        self.rightkeyid = wx.NewId()
        self.returnkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.rightkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.returnkeyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.leftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.rightkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, self.returnkeyid),
        ]
        accel = wx.AcceleratorTable(seq)
        self.SetAcceleratorTable(accel)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            e = wx.PyCommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, self.leftkeyid)
            self.ProcessEvent(e)
        else:
            e = wx.PyCommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, self.rightkeyid)
            self.ProcessEvent(e)

    def OnKeyDown(self, event):
        dc = wx.ClientDC(self.toppanel)
        id = event.GetId()

        list = None
        if id == self.returnkeyid:
            for header in self.list:
                if header.negaflag:
                    cw.cwpy.sounds["click"].play()
                    self.animate_click(header)
                    header.lclick_event()
                    return
        elif id == self.leftkeyid:
            list = self.list[:]
            list.reverse()
        elif id == self.rightkeyid:
            list = self.list

        if not list:
            return
        c1 = None
        c2 = list[0]
        for i, header in enumerate(list):
            if header.negaflag:
                if i == len(list)-1:
                    c1 = header
                    c2 = list[0]
                    break
                else:
                    c1 = header
                    c2 = list[i+1]
                    break

        if c1:
            c1.negaflag = False
            self.draw_card(dc, c1, True)
        if c2:
            c2.negaflag = True
            self.draw_card(dc, c2, True)

    def OnLeftUp(self, event):
        for header in self.list:
            if header.rect.collidepoint(event.GetPosition()):
                cw.cwpy.sounds["click"].play()
                self.animate_click(header)
                header.lclick_event()
                return

    def start(self):
        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.exec_func(cw.cwpy.battle.start)

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def runaway(self):
        s = cw.cwpy.msgs["confirm_runaway"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.battle:
                cw.cwpy.exec_func(cw.cwpy.battle.runaway)

            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def cancel(self):
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        self.cancel()

    def OnMove(self, event):
        dc = wx.ClientDC(self.toppanel)
        mousepos = event.GetPosition()

        for header in self.list:
            if header.rect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    self.draw_card(dc, header)

            elif header.negaflag:
                header.negaflag = False
                self.draw_card(dc, header)

    def OnEnter(self, event):
        self.draw(True)

    def OnLeave(self, event):
        if self.IsActive():
            for header in self.list:
                if header.negaflag:
                    header.negaflag = False
                    dc = wx.ClientDC(self.toppanel)
                    self.draw_card(dc, header)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetSize())
        else:
            dc = wx.PaintDC(self.toppanel)

        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.toppanel.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

        for header in self.list:
            self.draw_card(dc, header)

        return dc

    def draw_card(self, dc, header, fromkeyevent=False):
        if not fromkeyevent and self.IsActive():
            mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
            if header.rect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
            elif header.negaflag:
                header.negaflag = False

        pos = header.rect.topleft
        if header.negaflag:
            bmp = header.get_wxnegabmp()
        else:
            bmp = header.get_wxbmp()

        if header.clickedflag:
            bmp = header.get_wxclickedbmp(header, bmp)
            pos = (pos[0]+cw.wins(4), pos[1]+cw.wins(5))

        dc.DrawBitmap(bmp, pos[0], pos[1], False)

    def animate_click(self, header):
        # クリックアニメーション。4フレーム分。
        header.clickedflag = True
        self.draw(True)
        cw.cwpy.wait_frame(4)
        header.clickedflag = False
        dc = wx.ClientDC(self.toppanel)
        self.draw_card(dc, header)
        header.negaflag = False

class ErrorLogDialog(wx.Dialog):
    def __init__(self, parent, log):
        wx.Dialog.__init__(self, parent, -1, u"エラーログ")
        self.tc = wx.TextCtrl(
            self, -1, log, size=(250, 200),
            style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.btn_ok = wx.Button(self, wx.ID_OK, u"OK")
        self._do_layout()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tc, 0, 0, 0)
        sizer.Add(self.btn_ok, 0, wx.CENTER|wx.ALL, cw.wins(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class ExtensionDialog(wx.Dialog):
    """
    解説つきのボタンをいくつか提示し、選択した処理を実行する。
    title: ダイアログのタイトル。
    items: (name, description, func)のlist。
    """
    def __init__(self, parent, title, items):
        wx.Dialog.__init__(self, parent, -1, title)
        self.items = items

        self.buttons = []
        for t in self.items:
            if len(t) == 3:
                name, desc, func = t
                enable = True
            else:
                name, desc, func, enable = t
            btn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, cw.wins(24)), name=name)
            btn.Enable(enable)
            self.buttons.append(btn)

        self.panel = wx.Panel(self, -1, style=wx.BORDER)
        self.desc = wx.StaticText(self.panel, -1, size=cw.wins((210, 150)), style=wx.ST_NO_AUTORESIZE)
        self.desc.SetFont(cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(14)))

        self.btn_cncl = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, cw.wins(24)), cw.cwpy.msgs["cancel"])
        self._bind()
        self._do_layout()

    def _bind(self):
        for btn in self.buttons:
            btn.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
            btn.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
            btn.Bind(wx.EVT_SET_FOCUS, self.OnEnter)
            btn.Bind(wx.EVT_KILL_FOCUS, self.OnLeave)
            self.Bind(wx.EVT_BUTTON, self.OnBotton, btn)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        for ctrl in itertools.chain(self.GetChildren(), self.panel.GetChildren()):
            ctrl.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_buttons = wx.BoxSizer(wx.VERTICAL)
        for btn in self.buttons:
            sizer_buttons.Add(btn, 0, wx.EXPAND|wx.BOTTOM, cw.wins(5))
        sizer_buttons.AddStretchSpacer(1)
        sizer_buttons.Add(self.btn_cncl, 0, wx.EXPAND)

        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel.Add(self.desc, 1, wx.EXPAND|wx.ALL, cw.wins(10))
        self.panel.SetSizer(sizer_panel)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_buttons, 0, wx.EXPAND|wx.ALL, cw.wins(10))
        sizer.Add(self.panel, 1, wx.EXPAND|wx.TOP|wx.RIGHT|wx.BOTTOM, cw.wins(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnEnter(self, event):
        index = self.buttons.index(event.GetEventObject())
        self.desc.SetLabel(self.items[index][1])

    def OnLeave(self, event):
        self.desc.SetLabel("")

    def OnBotton(self, event):
        index = self.buttons.index(event.GetEventObject())
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)
        self.items[index][2]()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class BookmarkDialog(wx.Dialog):
    """
    ブックマークの編集を行う。
    """
    def __init__(self, parent, scedir, db):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["arrange_bookmark"],
                           style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)

        # リスト
        self.values = AutoListCtrl(self, -1, size=cw.wins((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE|wx.LC_NO_HEADER)
        self.values.SetDoubleBuffered(True)
        self.values.imglist = wx.ImageList(cw.wins(16), cw.wins(16))
        self.values.imgidx_summary = self.values.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY"]))
        self.values.imgidx_complete = self.values.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_COMPLETE"]))
        self.values.imgidx_playing = self.values.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_PLAYING"]))
        self.values.imgidx_invisible = self.values.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["SUMMARY_INVISIBLE"]))
        self.values.imgidx_dir = self.values.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs["DIRECTORY"]))
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"")
        self.values.SetColumnWidth(0, cw.wins(250))
        self.values.setResizeColumn(0)
        font = cw.cwpy.rsrc.get_wxfont("list", pixelsize=cw.wins(15), weight=wx.NORMAL)
        self.values.SetFont(font)

        self.bookmark = cw.cwpy.ydata.bookmarks[:]
        for i, bookmark in enumerate(cw.cwpy.ydata.bookmarks):
            path = scedir
            for p in bookmark:
                path = cw.util.join_paths(path, p)
                path = cw.util.get_linktarget(path)
            header = db.get_header(path)
            if header:
                item = self.values.InsertStringItem(i, header.name)
                if self.Parent.is_playing(header):
                    self.values.SetItemImage(item, self.values.imgidx_playing)
                elif self.Parent.is_complete(header):
                    self.values.SetItemImage(item, self.values.imgidx_complete)
                elif self.Parent.is_invisible(header):
                    self.values.SetItemImage(item, self.values.imgidx_invisible)
                else:
                    self.values.SetItemImage(item, self.values.imgidx_summary)
            else:
                if sys.platform == "win32":
                    sp = os.path.splitext(p)
                    if sp[1].lower() == ".lnk":
                        p = sp[0]
                item = self.values.InsertStringItem(i, p)
                self.values.SetItemImage(item, self.values.imgidx_dir)

        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_REMOVE, (cw.wins(70), -1), name=cw.cwpy.msgs["delete"])
        # 上へ
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_UP, (-1, -1), bmp=bmp)
        # 下へ
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_DOWN, (-1, -1), bmp=bmp)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), cw.cwpy.msgs["decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        self._item_selected()
        self.values.resizeLastColumn(-1)

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDownBtn, self.downbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.cnclbtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)
        self.values.Bind(wx.EVT_SIZE, self.OnResize)

        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        for child in self.GetChildren():
            child.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def OnResize(self, event):
        self.values.resizeLastColumn(-1)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        cw.util.fill_bitmap(dc, bmp, self.GetClientSize())

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        self.Destroy()

    def _do_layout(self):
        sizer = wx.GridBagSizer()

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND)
        sizer_right.Add(self.upbtn, 0, wx.EXPAND|wx.TOP, border=cw.wins(5))
        sizer_right.Add(self.downbtn, 0, wx.EXPAND|wx.TOP, border=cw.wins(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.wins(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.values, 1, wx.EXPAND|wx.ALL, border=cw.wins(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.wins(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnRemoveBtn(self, event):
        cw.cwpy.sounds["dump"].play()
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self.values.DeleteItem(index)
            self.bookmark.pop(index)
        self._item_selected()

    def OnUpBtn(self, event):
        index = -1
        cw.cwpy.sounds["page"].play()
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= 0:
                break
            self._swap(index, index-1)
        self._item_selected()

    def OnDownBtn(self, event):
        indexes = self.get_selectedindexes()
        if not indexes or self.values.GetItemCount() <= indexes[-1] + 1:
            return

        cw.cwpy.sounds["page"].play()
        indexes.reverse()
        for index in indexes:
            self._swap(index, index+1)
        self._item_selected()

    def _swap(self, index1, index2):
        self.bookmark[index1], self.bookmark[index2] = self.bookmark[index2], self.bookmark[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        def set_item(index, string, image):
            self.values.SetStringItem(index, 0, string)
            self.values.SetItemImage(index, image)
        string1 = self.values.GetItemText(index1)
        string2 = self.values.GetItemText(index2)
        image1 = self.values.GetItem(index1).GetImage()
        image2 = self.values.GetItem(index2).GetImage()
        set_item(index1, string2, image2)
        set_item(index2, string1, image1)

    def OnItemSelected(self, event):
        self._item_selected()

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _item_selected(self):
        indexes = self.get_selectedindexes()
        if not indexes:
            self.rmvbtn.Enable(False)
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)
        else:
            self.rmvbtn.Enable(True)
            self.upbtn.Enable(0 < indexes[0])
            self.downbtn.Enable(indexes[-1] + 1 < self.values.GetItemCount())

    def OnOkBtn(self, event):
        cw.cwpy.sounds["harvest"].play()
        def func(bookmarks):
            cw.cwpy.ydata.set_bookmarks(bookmarks)
        cw.cwpy.exec_func(func, self.bookmark)
        self.Destroy()

class AutoListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, id, size, style):
        wx.ListCtrl.__init__(self, parent, id, size=size, style=style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class ConvertYadoDialog(wx.Dialog):
    """
    宿の逆変換の設定を行う。
    """
    def __init__(self, parent, yadoname):
        wx.Dialog.__init__(self, parent, -1, u"拠点の逆変換",
                           style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.message = u"%s を逆変換し、\n新規作成したフォルダへ格納します。" % (yadoname)
        dc = wx.ClientDC(self)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16), weight=wx.NORMAL)
        dc.SetFont(font)
        w, h, lh = dc.GetMultiLineTextExtent(self.message)
        self.SetClientSize((w + cw.wins(50), cw.wins(156)))

        self.targetengine = 1.50
        self.dstpath = u"UnconvertedYado"

        self.folder = wx.TextCtrl(self, size=(-1, -1))
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16), weight=wx.NORMAL)
        self.folder.SetFont(font)
        self.folder.SetValue(self.dstpath)

        s = ((u"%s のデータをCardWirth用に逆変換します。" +
              u"\n変換先のフォルダを選択してください。") % (yadoname))
        self.reffolder = cw.util.create_fileselection(self, self.folder, s, dir=True, getbasedir=os.getcwdu, winsize=True)
        font = cw.cwpy.rsrc.get_wxfont("button", pixelsize=cw.wins(14), weight=wx.NORMAL)
        self.reffolder.SetFont(font)

        choices = [u"CardWirth 1.50",
                   u"CardWirth 1.30",
                   u"CardWirth 1.29",
                   u"CardWirth 1.28"]
        self.target = wx.Choice(self, size=(-1, -1), choices=choices)
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(16), weight=wx.NORMAL)
        self.target.SetFont(font)
        self.target.Select(0)

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

    def OnOk(self, event):
        cw.cwpy.sounds["signal"].play()
        self.dstpath = self.folder.GetValue()
        index = self.target.GetSelection()
        if index == 0:
            self.targetengine = 1.50
        elif index == 1:
            self.targetengine = 1.30
        elif index == 2:
            self.targetengine = 1.29
        elif index == 3:
            self.targetengine = 1.28
        else:
            assert False

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # text
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16), weight=wx.NORMAL)
        dc.SetFont(font)
        s = self.message
        w, h, lh = dc.GetMultiLineTextExtent(s)
        dc.DrawLabel(s, ((csize[0]-w)/2, cw.wins(10), w, h))

        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)

        s = u"対象エンジン:"
        tw, th = dc.GetTextExtent(s)
        x, y, w, h = self.target.GetRect()
        x -= tw + cw.wins(5)
        y += (h-th) / 2
        dc.DrawText(s, x, y)

        s = u"生成先:"
        x2, y2, w2, h2 = self.reffolder.GetRect()
        dc.DrawText(s, x, y - h2 - cw.wins(5))

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _do_layout(self):
        csize = self.GetClientSize()
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(cw.wins((0, 50)), 0, 0, 0)

        dc = wx.ClientDC(self)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)
        w, h = dc.GetTextExtent(u"対象エンジン:")
        sizer_3.Add((w, 0), 0, wx.RIGHT|wx.CENTER, cw.wins(5))
        sizer_3.Add(self.target, 1, wx.CENTER, 0)

        sizer_4.Add((w, 0), 0, wx.RIGHT|wx.CENTER, cw.wins(5))
        sizer_4.Add(self.folder, 1, wx.CENTER, 0)
        sizer_4.Add(self.reffolder, 0, wx.CENTER|wx.EXPAND, 0)

        sizer_1.Add(sizer_4, 0, wx.LEFT|wx.RIGHT|wx.EXPAND, cw.wins(10))
        sizer_1.Add(cw.wins((0, 5)), 0, 0, 0)
        sizer_1.Add(sizer_3, 0, wx.LEFT|wx.RIGHT|wx.EXPAND, cw.wins(10))

        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_2.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)

        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
