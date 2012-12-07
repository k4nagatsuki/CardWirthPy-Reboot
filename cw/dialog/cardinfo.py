#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw

#-------------------------------------------------------------------------------
#　カード情報ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CardInfo(wx.Dialog):
    """
    カード情報ダイアログ　スーパークラス
    """
    def __init__(self, parent):
        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, u"カード情報", size=(380, 200),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.csize = self.GetClientSize()
        # panel
        self.toppanel = wx.Panel(self, -1, size=(380, 138))
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (85, 24), u"閉じる")
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, (30, 30), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, (30, 30), bmp=bmp)

        # ボタン無効化
        if len(self.list) == 1:
            self.leftbtn.Disable()
            self.rightbtn.Disable()

        # layout
        self.__do_layout()
        # bind
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)
        # focus
        self.panel.SetFocusIgnoringChildren()

    def OnMouseWheel(self, event):
        if len(self.list) == 1:
            return

        if event.GetWheelRotation() > 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
            self.ProcessEvent(btnevent)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
            self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            cw.cwpy.sounds[u"page"].play()
            dc = wx.ClientDC(self.toppanel)
            self.selection = self.list[self.index]
        else:
            dc = wx.PaintDC(self.toppanel)

        # カード画像
        bmp = self.selection.cardimg.get_wxbmp()

        if isinstance(self.selection.cardimg, cw.image.LargeCardImage):
            dc.DrawBitmap(bmp, 7, 4, False)
        else:
            dc.DrawBitmap(bmp, 14, 14, False)

        # 説明文を囲うボックス
        cw.util.draw_box(dc, (113, 9), (258, 120))
        # カード名
        s = self.selection.name
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=9)
        dc.SetFont(font)
        size = dc.GetTextExtent(s)
        dc.SetPen(wx.Pen((255, 255, 255), 1, wx.TRANSPARENT))
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_MENU)
        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(122, 5, size[0], size[1])
        dc.DrawText(s, 122, 5)
        # 説明文
        s = cw.util.txtwrap(self.selection.desc, 1)

        if s.count("\n") > 7:
            s = "\n".join(s.split("\n")[0:8])

        font = cw.cwpy.rsrc.get_wxfont("gothic", size=9, weight=wx.NORMAL)
        dc.SetFont(font)
        dc.DrawLabel(s, (125, 22, 200, 110))

        # シナリオ・作者名
        scenario = self.selection.scenario
        author = self.selection.author
        author = "(" + author + ")" if author else ""
        s = scenario + author

        if s:
            font = cw.cwpy.rsrc.get_wxfont("uigothic", size=8,
                                                            weight=wx.NORMAL)
            dc.SetFont(font)
            size = dc.GetTextExtent(s)
            dc.DrawRectangle(365-size[0], 125, size[0], size[1])
            dc.DrawText(s, 365-size[0], 125)

        if update:
            self.toppanel.Refresh()
            self.toppanel.Update()

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        margin = (self.csize[0] - 145) / 2
        margin2 = margin + (self.csize[0] - 145) % 2
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_panel.Add((margin2, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 1, 0, 0)
        sizer_1.Add(self.panel, 0, 0, 0)
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
        self.list = cw.cwpy.get_mcards("visiblemenucards")
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
    def __init__(self, parent, list, selection):
        # カード情報
        self.selection = selection
        self.list = list
        self.index = self.list.index(selection)
        # ダイアログ作成
        CardInfo.__init__(self, parent)

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
