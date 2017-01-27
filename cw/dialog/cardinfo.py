#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import wx

import cw


#-------------------------------------------------------------------------------
#　カード情報ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CardInfo(wx.Dialog):
    """
    カード情報ダイアログ　スーパークラス
    """
    def __init__(self, parent, scedir=""):
        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["card_information"], size=cw.wins((380, 200)),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        self.csize = self.GetClientSize()
        self.scedir = scedir

        # フォントによってダイアログサイズを決定する
        dc = wx.ClientDC(self)
        font = cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(13))
        dc.SetFont(font)
        size = dc.GetTextExtent(u"―"*19)
        self.textwidth = size[0]
        self.textheight = size[1] * 9

        # panel
        size = (self.textwidth+cw.wins(152), self.textheight+cw.wins(42))
        self.toppanel = wx.Panel(self, -1, size=size)
        self.toppanel.SetDoubleBuffered(True)
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((85, 24)), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.wins((30, 30)), bmp=bmp, chain=True)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.wins((30, 30)), bmp=bmp, chain=True)

        # ボタン無効化
        if len(self.list) == 1:
            self.leftbtn.Disable()
            self.rightbtn.Disable()

        # layout
        self._do_layout()
        # bind
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)
        cw.util.add_sideclickhandlers(self.toppanel, self.leftbtn, self.rightbtn)
        # focus
        self.panel.SetFocusIgnoringChildren()

        self.leftpagekeyid = wx.NewId()
        self.rightpagekeyid = wx.NewId()
        copyid = wx.NewId()
        esckeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnCopyDetail, id=copyid)
        self.Bind(wx.EVT_MENU, self.OnCancel, id=esckeyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.leftpagekeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.rightpagekeyid),
            (wx.ACCEL_NORMAL, wx.WXK_BACK, esckeyid),
            (wx.ACCEL_NORMAL, ord('_'), esckeyid),
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.leftpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.rightpagekeyid),
            (wx.ACCEL_CTRL, ord('C'), copyid),
        ]
        cw.util.set_acceleratortable(self, seq)

        if sys.platform <> "win32":
            # BUG: SetBackgroundColour()を呼ばないと色が変わってしまう(Gtk)
            self.toppanel.SetBackgroundColour(self.toppanel.GetBackgroundColour())
            self.SetBackgroundColour(self.GetBackgroundColour())

    def OnCopyDetail(self, event):
        if not self.selection:
            return

        cw.cwpy.play_sound("equipment")
        s = self.get_source()
        if s:
            s = u"[ %s ] %s" % (self.selection.name, s)
        else:
            s = u"[ %s ]" % (self.selection.name)

        lines = []
        lines.append(s)
        lines.append(self.get_desc())
        lines.append(u"")
        cw.util.to_clipboard(u"\n".join(lines))

    def OnMouseWheel(self, event):
        if len(self.list) == 1:
            return

        if cw.util.get_wheelrotation(event) > 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
            self.ProcessEvent(btnevent)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
            self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        self.draw()

    def get_source(self):
        scenario = self.selection.scenario
        author = self.selection.author
        author = u"(" + author + u")" if author else u""
        return scenario + author

    def get_desc(self):
        s = cw.util.txtwrap(self.selection.desc, 1)
        if s.count(u"\n") > 8:
            s = u"\n".join(s.split(u"\n")[0:9])
        return s

    def draw(self, update=False):
        if update:
            cw.cwpy.play_sound("page")
            dc = wx.ClientDC(self.toppanel)
            self.selection = self.list[self.index]
        else:
            dc = wx.PaintDC(self.toppanel)

        # カード画像
        negaflag = self.selection
        self.selection.negaflag = False
        bmp = self.selection.cardimg.get_cardwxbmp(self.selection)
        self.selection.negaflag = negaflag

        cwidth = bmp.GetWidth()
        cheight = bmp.GetHeight()
        x = (cw.wins(113)-cwidth) / 2
        y = (self.toppanel.GetClientSize()[1] - cheight) / 2
        dc.DrawBitmap(bmp, x, y, True)

        # 説明文を囲うボックス
        rectsize = (self.textwidth + cw.wins(30), self.textheight + cw.wins(25))
        cw.util.draw_box(dc, cw.wins((113, 9)), rectsize)
        # カード名
        s = self.selection.name
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14))
        dc.SetFont(font)
        size = dc.GetTextExtent(s)
        dc.SetPen(wx.Pen((255, 255, 255), cw.wins(1), wx.TRANSPARENT))
        colour = self.toppanel.GetBackgroundColour()
        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        y = cw.wins(9) - size[1]/2
        dc.DrawRectangle(cw.wins(122), y, size[0], size[1])
        dc.DrawText(s, cw.wins(122), y)
        # 説明文
        s = self.get_desc()

        font = cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(13))
        dc.SetFont(font)
        dc.DrawLabel(s, cw.wins((127, 19, 200, 110)))

        # シナリオ・作者名
        s = self.get_source()
        if s:
            font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(14))
            dc.SetFont(font)
            size = dc.GetTextExtent(s)
            y = (cw.wins(9)+rectsize[1]) - size[1]/2
            dc.DrawRectangle(cw.wins(113)+rectsize[0]-cw.wins(5)-size[0], y, size[0], size[1])
            dc.DrawText(s, cw.wins(113)+rectsize[0]-cw.wins(5)-size[0], y)

        if update:
            self.toppanel.Refresh()
            self.toppanel.Update()

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((0, 0), 1, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((0, 0), 1, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 1, 0, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
# メニューカード情報ダイアログ
#-------------------------------------------------------------------------------

class MenuCardInfo(CardInfo):
    def __init__(self, parent):
        # カード情報
        self.selection = cw.cwpy.selection
        self.list = filter(lambda mcard: mcard.desc, cw.cwpy.get_mcards("visiblemenucards"))
        self.index = self.list.index(self.selection)
        # ダイアログ作成
        CardInfo.__init__(self, parent)

    def OnClickLeftBtn(self, event):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        self.selection = self.list[self.index]
        self.Parent.change_selection(self.selection)
        self.draw(True)

    def OnClickRightBtn(self, event):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        self.selection = self.list[self.index]
        self.Parent.change_selection(self.selection)
        self.draw(True)

#-------------------------------------------------------------------------------
# 所持カード情報ダイアログ
#-------------------------------------------------------------------------------

class YadoCardInfo(CardInfo):
    def __init__(self, parent, clist, selection, scedir=""):
        # カード情報
        self.selection = selection
        self.list = clist
        self.index = self.list.index(selection)
        # ダイアログ作成
        CardInfo.__init__(self, parent, scedir=scedir)

    def OnClickLeftBtn(self, event):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        self.selection.negaflag = False
        self.selection = self.list[self.index]
        self.selection.negaflag = True
        self.Parent.draw(True)
        self.draw(True)

    def OnClickRightBtn(self, event):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        self.selection.negaflag = False
        self.selection = self.list[self.index]
        self.selection.negaflag = True
        self.Parent.draw(True)
        self.draw(True)

def main():
    pass

if __name__ == "__main__":
    main()
