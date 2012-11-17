#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


#-------------------------------------------------------------------------------
#　パーティ情報変更ダイアログ
#-------------------------------------------------------------------------------

class PartyEditor(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"パーティ情報",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.party = cw.cwpy.ydata.party

        # パーティ名入力ボックス
        self.textctrl = wx.TextCtrl(self, size=(240, 24))
        self.textctrl.SetMaxLength(18)
        self.textctrl.SetValue(self.party.name)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=12)
        self.textctrl.SetFont(font)

        # 所持金パネル。
        if cw.cwpy.is_playingscenario():
            self.panel = MoneyViewPanel(self)
        else:
            self.panel = MoneyEditPanel(self)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                            (100, 30), u"決定")
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), u"中止")
        if cw.cwpy.is_playingscenario():
            self.okbtn.Disable()

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.panel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, 20)

        sizer_v1.Add((0, 18), 0, wx.CENTER, 0)
        sizer_v1.Add(self.textctrl, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add((0, 18), 0, wx.CENTER|wx.TOP, 10)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, 10)

        sizer.Add(sizer_v1, 0, wx.ALL, 15)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnOk(self, event):
        cw.cwpy.sounds[u"システム・収穫"].play()
        name = self.textctrl.GetValue()

        if not name == self.party.name:
            cw.cwpy.ydata.party.set_name(name)

        if not self.panel.value == self.party.money:
            pmoney = self.panel.value - self.party.money
            ymoney = self.party.money - self.panel.value
            cw.cwpy.ydata.set_money(ymoney)
            cw.cwpy.ydata.party.set_money(pmoney)
            cw.cwpy.exec_func(cw.cwpy.draw, True)

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"システム・クリック"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint (self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # text
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic"))
        s = u"パーティの呼称"
        left = (dc.GetSize()[0] - dc.GetTextExtent(s)[0]) / 2
        dc.DrawText(s, left, 15)
        s = u"パーティの所持金"
        left = (dc.GetSize()[0] - dc.GetTextExtent(s)[0]) / 2
        dc.DrawText(s, left, 73)

class MoneyEditPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
        self.party = cw.cwpy.ydata.party
        self.value = self.party.money
        maxvalue = self.party.money + cw.cwpy.ydata.money
        minvalue = 0
        # パーティ所持金変更スライダ
        self.slider = wx.Slider(self, -1, self.value, minvalue, maxvalue,
            size=(165, -1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        n = maxvalue / 10 if maxvalue else 0
        self.slider.SetTickFreq(n, 1)
        # パーティ所持金変更スピン
        self.spinctrl = wx.SpinCtrl(self, -1, "", size=(88, -1))
        self.spinctrl.SetRange(minvalue, maxvalue)
        self.spinctrl.SetValue(self.value)
        # 宿金庫変更スピン
        self.spinctrl2 = wx.SpinCtrl(self, -1, "", size=(88, -1))
        self.spinctrl2.SetRange(minvalue, maxvalue)
        self.spinctrl2.SetValue(cw.cwpy.ydata.money)
        # bmp
        bmp = cw.cwpy.rsrc.dialogs["MONEYP"]
        self.bmp_pmoney = wx.StaticBitmap(self, -1, bmp)
        bmp = cw.cwpy.rsrc.dialogs["MONEYY"]
        self.bmp_ymoney = wx.StaticBitmap(self, -1, bmp)
        # text
        self.text_party = wx.StaticText(self, -1, u"パーティの所持金")
        font = cw.cwpy.rsrc.get_wxfont(size=8, weight=wx.NORMAL)
        self.text_party.SetFont(font)
        self.text_yado = wx.StaticText(self, -1, u"宿の金庫")
        self.text_yado.SetFont(font)
        self._do_layout()
        self._bind()

    def _bind(self):
        self.spinctrl.Bind(wx.EVT_SPINCTRL, self.OnSpinCtrl)
        self.spinctrl2.Bind(wx.EVT_SPINCTRL, self.OnSpinCtrl2)
        self.slider.Bind(wx.EVT_SLIDER, self.OnSlider)

    def OnSlider(self, event):
        value = self.slider.GetValue()
        self.spinctrl.SetValue(value)
        self.spinctrl2.SetValue(self.spinctrl2.GetMax() - value)
        self.value = value

    def OnSpinCtrl(self, event):
        value = self.spinctrl.GetValue()
        self.slider.SetValue(value)
        self.spinctrl2.SetValue(self.spinctrl2.GetMax() - value)
        self.value = value

    def OnSpinCtrl2(self, event):
        value = self.spinctrl.GetMax() - self.spinctrl2.GetValue()
        self.slider.SetValue(value)
        self.spinctrl.SetValue(value)
        self.value = value

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_h2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v2 = wx.BoxSizer(wx.VERTICAL)
        sizer_v3 = wx.BoxSizer(wx.VERTICAL)

        sizer_v3.Add(self.text_yado, 0, wx.CENTER|wx.TOP, 3)
        sizer_v3.Add(self.spinctrl2, 0, wx.CENTER, 0)

        sizer_v2.Add(self.text_party, 0, wx.CENTER, 0)
        sizer_v2.Add(self.spinctrl, 0, wx.CENTER, 0)

        sizer_h3.Add(self.bmp_ymoney, 0, wx.CENTER, 0)
        sizer_h3.Add(sizer_v3, 0, wx.CENTER|wx.LEFT, 5)

        sizer_h2.Add(self.bmp_pmoney, 0, wx.CENTER, 0)
        sizer_h2.Add(sizer_v2, 0, wx.CENTER|wx.LEFT, 5)

        sizer_v1.Add(sizer_h2, 0, wx.CENTER, 0)
        sizer_v1.Add(sizer_h3, 0, wx.CENTER, 0)

        sizer_h1.Add(self.slider, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v1, 0, wx.CENTER|wx.LEFT, 5)

        sizer.Add(sizer_h1, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class MoneyViewPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
        self.value = cw.cwpy.ydata.party.money
        # bmp
        bmp = cw.cwpy.rsrc.dialogs["MONEYP"]
        self.bmp_pmoney = wx.StaticBitmap(self, -1, bmp)
        # text
        self.text_pmoney = wx.StaticText(self, -1, str(self.value),
                                        size=(88, -1), style=wx.SUNKEN_BORDER)
        self.text_pmoney.SetBackgroundColour(wx.WHITE)
        self.text_party = wx.StaticText(self, -1, u"パーティの所持金")
        font = cw.cwpy.rsrc.get_wxfont(size=8, weight=wx.NORMAL)
        self.text_party.SetFont(font)
        self._do_layout()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        sizer_v1.Add(self.text_party, 0, wx.CENTER, 0)
        sizer_v1.Add(self.text_pmoney, 0, wx.CENTER, 0)

        sizer_h1.Add(self.bmp_pmoney, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v1, 0, wx.CENTER|wx.LEFT, 5)

        sizer.Add(sizer_h1, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
