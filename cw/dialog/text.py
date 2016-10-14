#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re

import wx
import webbrowser

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

        self.richtextctrl = wx.richtext.RichTextCtrl(self.toppanel, -1, "", size=cw.wins((550, 220)), style=wx.TE_MULTILINE|wx.NO_BORDER)
        self.foreground = self.richtextctrl.GetForegroundColour()
        self._set_text(value)
        self.richtextctrl.SetBackgroundColour(wx.Colour(0, 0, 128))
        font = cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(14))
        self._line_height = font.GetPixelSize()[1]
        self.richtextctrl.SetFont(font)
        self.richtextctrl.SetEditable(False)
        self.richtextctrl.ShowPosition(0)
        # popup menu
        googleid = wx.NewId()
        self.popup_menu = wx.Menu()
        self.mi_copy = wx.MenuItem(self.popup_menu, wx.ID_COPY, u"コピー(&C)")
        self.mi_selectall = wx.MenuItem(self.popup_menu, wx.ID_SELECTALL, u"すべて選択(&A)")
        self.mi_google = wx.MenuItem(self.popup_menu, googleid, u"&Googleで検索")
        self.popup_menu.AppendItem(self.mi_copy)
        self.popup_menu.AppendItem(self.mi_selectall)
        self.popup_menu.AppendSeparator()
        self.popup_menu.AppendItem(self.mi_google)

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
        self.richtextctrl.Bind(wx.EVT_TEXT_URL, self.OnURL)
        self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnSelectAll, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnGoogle, id=googleid)
        self.richtextctrl.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.richtextctrl.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.richtextctrl.Bind(wx.EVT_MOTION, self.OnMotion)
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

        # ZIPアーカイブのファイルエンコーディングと
        # 読み込むテキストファイルのエンコーディングが異なる場合、
        # エラーが出るので
        try:
            # 書き込みテスト FIXME: 書き込みに頼らないスマートな方法
            self.richtextctrl.WriteText(value)

            value2 = value
        except Exception:
            value2 = cw.util.decode_text(value)

        # URLを検索して取り出し、テキストをリストに分割
        def func(text):
            prog = re.compile(r"http(s)?://([\w\-]+\.)+[\w]+(/[\w\-./?%&=~#!]*)?")
            list = []

            url = prog.search(text)

            # TODO: URLクリック等でキャレットがURL上にある場合に
            # テキストを切り替えるとURLリンク設定が全テキストに適用される
            # これは暫定対処の1、しかも冒頭がURLだと無理矢理空白を入れる
            if url and url.start() == 0:
                list.append(" ")

            while url:
                if url.start() > 0:
                    list.append(text[:url.start()])
                list.append(url.group(0))
                text = text[url.end():]

                url = prog.search(text)

            if len(text) > 0:
                list.append(text)

            return list

        # TODO: URLクリック等でキャレットがURL上にある場合に
        # テキストを切り替えるとURLリンク設定が全テキストに適用される
        # これは暫定対処の2、しかも冒頭がURLではない事が前提の操作
        self.richtextctrl.MoveHome()

        self.richtextctrl.Clear()

        for v in func(value2):
            url_flag = True if re.match(r"http(s)?://", v) else False

            if url_flag:
                self.richtextctrl.BeginTextColour((255, 132, 0))
                self.richtextctrl.BeginUnderline()
                self.richtextctrl.BeginURL(v)
            else:
                self.richtextctrl.BeginTextColour(wx.WHITE)

            self.richtextctrl.WriteText(v)

            if url_flag:
                self.richtextctrl.EndURL()
                self.richtextctrl.EndUnderline()
            self.richtextctrl.EndTextColour()

        self.richtextctrl.EndTextColour()
        self.richtextctrl.ShowPosition(0)

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

    def OnMouseWheel(self, event):
        y = self.richtextctrl.GetScrollPos(wx.VERTICAL)

        if sys.platform == "win32":
            import win32gui
            SPI_GETDESKWALLPAPER = 104
            value = win32gui.SystemParametersInfo(SPI_GETDESKWALLPAPER)
            value *= self._line_height
            value /= self.richtextctrl.GetScrollPixelsPerUnit()[1]
        else:
            value = cw.wins(4)

        if event.GetWheelRotation() > 0:
            self.richtextctrl.Scroll(0, y - value)
        else:
            self.richtextctrl.Scroll(0, y + value)
        self.Refresh()

    def OnMotion(self, event):
        # 画面外へのドラッグによるスクロール処理だが、マウス入力の分岐は不要？
        mousey = event.GetPosition()[1]
        y = self.richtextctrl.GetScrollPos(wx.VERTICAL)
        if mousey < cw.wins(0):
            self.richtextctrl.Scroll(0, y - cw.wins(4))
            self.Refresh()
        elif mousey > cw.wins(245):
            self.richtextctrl.Scroll(0, y + cw.wins(4))
            self.Refresh()

        event.Skip()

    def OnContextMenu(self, event):
        self.mi_copy.Enable(self.richtextctrl.HasSelection())
        self.mi_google.Enable(self.richtextctrl.HasSelection())
        self.PopupMenu(self.popup_menu)

    def OnCopy(self, event):
        self.richtextctrl.Copy()

    def OnSelectAll(self, event):
        self.richtextctrl.SelectAll()

    def OnGoogle(self, event):
        self.go_url(u"http://www.google.com/search?q=%s" % self.richtextctrl.GetStringSelection())

    def go_url(self, url):
        try:
            webbrowser.open(url)
        except:
            s = u"「%s」が開けませんでした。インターネットブラウザが正常に関連付けされているか確認して下さい。" % url
            dlg = cw.dialog.message.ErrorMessage(self, s)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

    def OnURL(self, event):
        # 文字列選択中はブラウザ起動しない
        if not self.richtextctrl.HasSelection():
            self.go_url(event.GetString())

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
