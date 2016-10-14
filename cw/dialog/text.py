#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re

import wx

import cw


#-------------------------------------------------------------------------------
#　テキストダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class Text(wx.Dialog):
    def __init__(self, parent, name):
        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, name, size=cw.wins((550, 290)),
                            style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = False
        # panel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((550, 245)))
        self.toppanel.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)

        # rich text ctrl
        if self.list2:
            value = self.list2[self.index2]
        else:
            value = ""

        self.richtextctrl = cw.util.CWPyRichTextCtrl(self.toppanel, -1, "", size=cw.wins((550, 220)), style=wx.TE_MULTILINE|wx.NO_BORDER,
                                                     searchmenu=True)
        self.foreground = self.richtextctrl.GetForegroundColour()
        self._set_text(value)
        self.richtextctrl.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.richtextctrl.SetFont(cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(14)))
        self.richtextctrl.SetEditable(False)
        self.richtextctrl.ShowPosition(0)

        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((85, 24)), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.wins((30, 30)), bmp=bmp, chain=True)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.wins((30, 30)), bmp=bmp, chain=True)
        # choice
        self.combo = wx.ComboBox(self.toppanel, size=cw.wins((140, 20)), choices=self.list, style=wx.CB_READONLY)
        self.combo.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        cw.util.adjust_dropdownwidth(self.combo)

        if self.list:
            self.combo.SetSelection(self.index)

        # button enable
        self._enable_btn()
        # layout
        self.__do_layout()
        # bind
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_COMBOBOX, self.OnCombobox)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)

        # FIXME: ウィンドウのリサイズで正しく再描画されない。
        #        挙動が意味不明なので根本的な対処は行えていないが、
        #        以下のようにリサイズイベント中にレイアウトと
        #        再描画を行う事で回避できている。
        def resize(event):
            self.Layout()
            self.Refresh()
        self.Bind(wx.EVT_SIZE, resize)

        self.richtextctrl.Enable(bool(self.list2))
        if self.list2:
            self.richtextctrl.Show()
            self.combo.Enable()
            self.Layout()
        else:
            self.richtextctrl.Hide()
            self.combo.Disable()

        self.leftpagekeyid = wx.NewId()
        self.rightpagekeyid = wx.NewId()
        self.upkeyid = wx.NewId()
        self.downkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnUp, id=self.upkeyid)
        self.Bind(wx.EVT_MENU, self.OnDown, id=self.downkeyid)
        seq = [
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.leftpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.rightpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_UP, self.upkeyid),
            (wx.ACCEL_CTRL, wx.WXK_DOWN, self.downkeyid),
            (wx.ACCEL_CTRL, ord('C'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('A'), wx.ID_SELECTALL),
        ]
        cw.util.set_acceleratortable(self, seq)

    def _set_text(self, value):
        self.richtextctrl.set_text(value, linkurl=True)

    def OnCombobox(self, event):
        self.index = self.combo.GetSelection()
        self.index2 = self.index
        self._set_text(self.list2[self.index2])

    def OnClickLeftBtn(self, event):
        self.Parent.OnClickLeftBtn(event)
        self._enable_btn()
        self.update_lists()

        if self.list2:
            value = self.list2[self.index2]
        else:
            value = ""

        self._set_text(value)
        self.combo.SetItems(self.list)
        cw.util.adjust_dropdownwidth(self.combo)

        if self.list:
            self.combo.SetSelection(self.index)

        # notextfile
        self.toppanel.Update()
        self.richtextctrl.Enable(bool(self.list2))
        if self.list2:
            self.richtextctrl.Show()
            self.combo.Enable()
            self.Layout()
        else:
            self.richtextctrl.Hide()
            self.combo.Disable()

    def OnClickRightBtn(self, event):
        self.Parent.OnClickRightBtn(event)
        self._enable_btn()
        self.update_lists()

        if self.list2:
            value = self.list2[self.index2]
        else:
            value = ""

        self._set_text(value)
        self.combo.SetItems(self.list)
        cw.util.adjust_dropdownwidth(self.combo)

        if self.list:
            self.combo.SetSelection(self.index)

        # notextfile
        self.toppanel.Update()
        self.richtextctrl.Enable(bool(self.list2))
        if self.list2:
            self.richtextctrl.Show()
            self.combo.Enable()
            self.Layout()
        else:
            self.richtextctrl.Hide()
            self.combo.Disable()

    def OnUp(self, event):
        if self.combo.GetCount() <= 1:
            return
        cw.cwpy.play_sound("page")
        index = self.combo.GetSelection()
        if index <= 0:
            self.combo.SetSelection(self.combo.GetCount()-1)
        else:
            self.combo.SetSelection(index-1)
        event = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.combo.GetId())
        self.ProcessEvent(event)

    def OnDown(self, event):
        if self.combo.GetCount() <= 1:
            return
        cw.cwpy.play_sound("page")
        index = self.combo.GetSelection()
        self.combo.SetSelection((index+1) % self.combo.GetCount())
        event = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.combo.GetId())
        self.ProcessEvent(event)

    def OnPaint(self, event):
        dc = wx.PaintDC(self.toppanel)
        csize = self.toppanel.GetSize()
        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 128)))
        dc.DrawRectangle(0, 0, csize[0], csize[1])
        dc.SetTextForeground(wx.LIGHT_GREY)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(16)))
        s = cw.cwpy.msgs["instructions"]
        dc.DrawText(s, cw.wins(5), cw.wins(2))
        s = cw.cwpy.msgs["referencing_file"]
        w = dc.GetTextExtent(s)[0]
        w = w + cw.wins(5) + self.combo.GetSize()[0]
        dc.DrawText(s, self.GetClientSize()[0] - w, cw.wins(2))
        dc.SetBrush(wx.Brush(wx.LIGHT_GREY))
        dc.SetPen(wx.Pen(wx.LIGHT_GREY))
        dc.DrawRectangle(0, self.combo.GetSize()[1], csize[0], cw.wins(2))
        if not self.list2:
            dc.SetTextForeground(wx.LIGHT_GREY)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(20)))
            # 文字
            s = "No Text File"
            size = dc.GetTextExtent(s)
            size2 = self.toppanel.GetSize()
            pos = (size2[0]-size[0])/2, (size2[1]-size[1])/2
            dc.DrawText(s, pos[0], pos[1])
            # ボックス
            size = size[0] + cw.wins(60), size[1] + cw.wins(20)
            pos = pos[0] - cw.wins(30), pos[1] - cw.wins(10)
            cw.util.draw_box(dc, pos, size)

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_toppanel = wx.BoxSizer(wx.VERTICAL)
        sizer_topbar = wx.BoxSizer(wx.HORIZONTAL)

        # トップバー
        sizer_topbar.Add((0, 0), 1, 0, cw.wins(0))
        sizer_topbar.Add(self.combo, 0, 0, cw.wins(0))
        sizer_toppanel.Add(sizer_topbar, 0, wx.EXPAND, cw.wins(0))
        sizer_toppanel.Add(cw.wins((0, 3)), 0, wx.EXPAND, cw.wins(0))
        sizer_toppanel.Add(self.richtextctrl, 1, wx.EXPAND, cw.wins(0))
        self.toppanel.SetSizer(sizer_toppanel)

        sizer_panel.Add(self.leftbtn, 0, 0, cw.wins(0))
        sizer_panel.Add((0, 0), 1, 0, cw.wins(0))
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((0, 0), 1, 0, cw.wins(0))
        sizer_panel.Add(self.rightbtn, 0, 0, cw.wins(0))
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 1, wx.EXPAND, cw.wins(0))
        sizer_1.Add(self.panel, 0, wx.EXPAND, cw.wins(0))
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _enable_btn(self):
        # リストが空だったらボタンを無効化
        if self.Parent.list:
            if len(self.Parent.list) == 1:
                self.rightbtn.Disable()
                self.leftbtn.Disable()
            else:
                self.rightbtn.Enable()
                self.leftbtn.Enable()
                self.closebtn.Enable()
        else:
            self.rightbtn.Disable()
            self.leftbtn.Disable()
            self.closebtn.Disable()

    def upddate_lists(self):
        pass

#-------------------------------------------------------------------------------
#　リードミーダイアログ
#-------------------------------------------------------------------------------

class Readme(Text):
    def __init__(self, parent, name, lists):
        cw.util.sort_by_attr(lists, "noextname")
        self.list = []
        self.index = 0
        self.list2 = []
        self.index2 = 0
        for s in lists:
            self.list.append(s.name)
            self.list2.append(s.content)
        Text.__init__(self, parent, name)

    def update_lists(self):
        lists = self.Parent.get_texts()
        cw.util.sort_by_attr(lists, "noextname")
        self.list = []
        self.index = 0
        self.list2 = []
        self.index2 = 0
        for s in lists:
            self.list.append(s.name)
            self.list2.append(s.content)

        self.index = 0
        self.index2 = 0

class ReadmeData(object):
    def __init__(self, name, content):
        self.name = name
        self.noextname = os.path.splitext(name)[0].lower().split("/")
        self.noextname.reverse()
        self.content = content

def main():
    pass

if __name__ == "__main__":
    main()
