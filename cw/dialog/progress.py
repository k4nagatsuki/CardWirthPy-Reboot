#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


#-------------------------------------------------------------------------------
# 進捗表示ダイアログ
#-------------------------------------------------------------------------------

class ProgressDialog(wx.Dialog):
    def __init__(self, parent, title, message, maximum=100, minimum=0, cancelable=False, width_noscale=300):
        wx.Dialog.__init__(self, parent, -1, title,
                           style=wx.DEFAULT_DIALOG_STYLE)
        self.cwpy_debug = False
        self.SetClientSize(cw.wins((width_noscale, 60)))
        self.EnableCloseButton(cancelable)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.text = message
        self.minimum = minimum
        self.maximum = maximum
        self.cancel = False
        self.gauge = wx.Gauge(self, -1, range=self.maximum-self.minimum,
                              size=(-1, cw.wins(20)),
                              style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)

        if cancelable:
            self.btn_cncl = cw.cwpy.rsrc.create_wxbutton(self, -1, cw.wins((80, 30)), u"中止")
            self.SetClientSize((cw.wins(width_noscale+20), cw.wins(60)+self.btn_cncl.GetBestSize()[1]+cw.wins(4)))
        else:
            self.btn_cncl = None

        # layout
        self._do_layout()
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        if self.btn_cncl:
            self.Bind(wx.EVT_BUTTON, self.OnClickCancelBtn, self.btn_cncl)

    def Update(self, value, message):
        value -= self.minimum
        if value <> self.gauge.GetValue() or self.text <> message:
            self.gauge.SetValue(value-self.minimum)
            self.text = message
            self.Refresh()

    def OnPaint(self, event):
        csize = self.GetClientSize()
        wxbmp = wx.EmptyBitmap(csize[0], csize[1])
        dc = wx.MemoryDC(wxbmp)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        cw.util.fill_bitmap(dc, bmp, csize)
        # massage
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14)))
        dc.DrawLabel(self.text, (cw.wins(10), cw.wins(36), csize[0]-cw.wins(20), cw.wins(50)), wx.ALIGN_RIGHT)

        dc.SelectObject(wx.NullBitmap)
        dc2 = wx.PaintDC(self)
        dc2.DrawBitmap(wxbmp, 0, 0)

    def OnClickCancelBtn(self, event):
        self.cancel = True

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)
        sizer_1.Add(self.gauge, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, cw.wins(10))

        if self.btn_cncl:
            sizer_1.Add(cw.wins((0, 24)), 0, 0, cw.wins(0))
            sizer_1.Add(self.btn_cncl, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT, cw.wins(10))
        else:
            sizer_1.Add(cw.wins((0, 30)), 0, 0, cw.wins(0))

        self.SetSizer(sizer_1)
        self.Layout()

#-------------------------------------------------------------------------------
# 進捗表示ダイアログ(デバッガ・設定ダイアログ変換用)
#-------------------------------------------------------------------------------

class SysProgressDialog(wx.Dialog):
    def __init__(self, parent, title, message, maximum=100, minimum=0, cancelable=False, width=380):
        wx.Dialog.__init__(self, parent, -1, title,
                           style=wx.DEFAULT_DIALOG_STYLE)
        self.cwpy_debug = False
        self.SetClientSize(cw.ppis((width+20, 80)))
        self.EnableCloseButton(cancelable)
        self.SetDoubleBuffered(True)
        self.cancel = False
        self.text = message
        self.minimum = minimum
        self.maximum = maximum
        self.gauge = wx.Gauge(self, -1, range=self.maximum-self.minimum,
                              size=(-1, cw.ppis(20)),
                              style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        self.message = wx.StaticText(self, -1, self.text,
                                     size=(-1, -1),
                                     style=wx.ALIGN_RIGHT)
        self.message.SetDoubleBuffered(True)

        if cancelable:
            self.btn_cncl = wx.Button(self, -1, u"中止")
            self.SetClientSize((cw.ppis(width+20), cw.ppis(60)+self.btn_cncl.GetBestSize()[1]+cw.ppis(5)))
        else:
            self.btn_cncl = None

        # bind
        self._bind()
        # layout
        self._do_layout()

    def Update(self, value, message):
        value -= self.minimum
        if value <> self.gauge.GetValue() or self.text <> message:
            self.gauge.SetValue(value-self.minimum)
            self.text = message
            self.message.SetLabel(self.text)

    def OnClickCancelBtn(self, event):
        self.cancel = True

    def _bind(self):
        if self.btn_cncl:
            self.Bind(wx.EVT_BUTTON, self.OnClickCancelBtn, self.btn_cncl)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_1.Add(cw.ppis((0, 10)), 0, 0, cw.ppis(0))
        sizer_1.Add(self.gauge, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, cw.ppis(10))
        sizer_1.Add(cw.ppis((0, 4)), 0, 0, cw.ppis(0))
        sizer_1.Add(self.message, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, cw.ppis(10))

        if self.btn_cncl:
            sizer_1.Add(cw.ppis((0, 5)), 0, 0, cw.ppis(0))
            sizer_1.Add(self.btn_cncl, 0, wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT, cw.ppis(10))
        else:
            sizer_1.Add(cw.ppis((0, 30)), 0, 0, cw.ppis(0))

        self.SetSizer(sizer_1)
        self.Layout()
