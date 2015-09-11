#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import wx.combo

import cw


#-------------------------------------------------------------------------------
#　パーティ情報変更ダイアログ
#-------------------------------------------------------------------------------

class PartyEditor(wx.Dialog):
    def __init__(self, parent, party=None):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["party_information"],
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        if party:
            self.party = party
        else:
            self.party = cw.cwpy.ydata.party

        # パーティ名入力ボックス
        self.textctrl = wx.TextCtrl(self, size=cw.wins((240, 24)))
        self.textctrl.SetMaxLength(18)
        self.textctrl.SetValue(self.party.name)
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.textctrl.SetFont(font)

        # 所持金パネル。
        if self.party.is_adventuring():
            self.panel = MoneyViewPanel(self, self.party)
        else:
            self.panel = MoneyEditPanel(self, self.party)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

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
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(20))

        sizer_v1.Add(cw.wins((0, 18)), 0, wx.CENTER, 0)
        sizer_v1.Add(self.textctrl, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(cw.wins((0, 18)), 0, wx.CENTER|wx.TOP, cw.wins(10))
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        name = self.textctrl.GetValue()
        money = self.panel.value

        def func(self, party):
            if not name == party.name:
                party.set_name(name)

            if not money == party.money:
                pmoney = money - party.money
                ymoney = party.money - money
                cw.cwpy.ydata.set_money(ymoney, blink=True)
                party.set_money(pmoney, blink=True)
                party.write()
                cw.cwpy.draw(True)
            def func(self):
                if self:
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
                    self.ProcessEvent(btnevent)
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self, self.party)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # text
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14)))
        s = cw.cwpy.msgs["party_name"]
        left = (dc.GetSize()[0] - dc.GetTextExtent(s)[0]) // 2
        dc.DrawText(s, left, cw.wins(15))
        s = cw.cwpy.msgs["party_money"]
        left = (dc.GetSize()[0] - dc.GetTextExtent(s)[0]) // 2
        dc.DrawText(s, left, cw.wins(73))

class MoneyEditPanel(wx.Panel):
    def __init__(self, parent, party):
        wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
        self.party = party
        self.value = self.party.money
        maxvalue = self.party.money + cw.cwpy.ydata.money
        if maxvalue > 9999999:
            minvalue = maxvalue - 9999999
            maxvalue = 9999999
        else:
            minvalue = 0
        # パーティ所持金変更スライダ
        self.slider = SliderWithButton(self, self.value, minvalue, maxvalue, cw.wins(150))
        # パーティ所持金変更スピン
        self.spinctrl = wx.SpinCtrl(self, -1, "", size=(cw.wins(88), -1))
        self.spinctrl.SetFont(cw.cwpy.rsrc.get_wxfont("spin", pixelsize=cw.wins(14)))
        self.spinctrl.SetRange(minvalue, maxvalue)
        self.spinctrl.SetValue(self.value)
        # 宿金庫変更スピン
        self.spinctrl2 = wx.SpinCtrl(self, -1, "", size=(cw.wins(88), -1))
        self.spinctrl2.SetFont(cw.cwpy.rsrc.get_wxfont("spin", pixelsize=cw.wins(14)))
        self.spinctrl2.SetRange(minvalue, maxvalue)
        self.spinctrl2.SetValue(cw.cwpy.ydata.money)
        # bmp
        bmp = cw.cwpy.rsrc.dialogs["MONEYP"]
        self.bmp_pmoney = cw.util.CWPyStaticBitmap(self, -1, bmp)
        bmp = cw.cwpy.rsrc.dialogs["MONEYY"]
        self.bmp_ymoney = cw.util.CWPyStaticBitmap(self, -1, bmp)
        # text
        self.text_party = wx.StaticText(self, -1, cw.cwpy.msgs["party_money"])
        font = cw.cwpy.rsrc.get_wxfont("spin", pixelsize=cw.wins(12))
        self.text_party.SetFont(font)
        self.text_yado = wx.StaticText(self, -1, cw.cwpy.msgs["base_money"])
        self.text_yado.SetFont(font)

        self.spinctrl.Enable(minvalue < maxvalue)
        self.spinctrl2.Enable(minvalue < maxvalue)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.spinctrl.Bind(wx.EVT_SPINCTRL, self.OnSpinCtrl)
        self.spinctrl2.Bind(wx.EVT_SPINCTRL, self.OnSpinCtrl2)
        self.slider.slider.Bind(wx.EVT_SLIDER, self.OnSlider)

    def OnSlider(self, event):
        value = self.slider.slider.GetValue()
        self.spinctrl.SetValue(value)
        self.spinctrl2.SetValue(self.spinctrl2.GetMax() + self.spinctrl2.GetMin() - value)
        self.value = value

    def OnSpinCtrl(self, event):
        value = self.spinctrl.GetValue()
        self.slider.set_value(value)
        self.spinctrl2.SetValue(self.spinctrl2.GetMax() + self.spinctrl2.GetMin() - value)
        self.value = value

    def OnSpinCtrl2(self, event):
        value = self.spinctrl.GetMax() + self.spinctrl.GetMin() - self.spinctrl2.GetValue()
        self.slider.set_value(value)
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

        sizer_v3.Add(self.text_yado, 0, wx.CENTER|wx.TOP, cw.wins(3))
        sizer_v3.Add(self.spinctrl2, 0, wx.CENTER, 0)

        sizer_v2.Add(self.text_party, 0, wx.CENTER, 0)
        sizer_v2.Add(self.spinctrl, 0, wx.CENTER, 0)

        sizer_h3.Add(self.bmp_ymoney, 0, wx.CENTER, 0)
        sizer_h3.Add(sizer_v3, 1, wx.CENTER|wx.LEFT, cw.wins(5))

        sizer_h2.Add(self.bmp_pmoney, 0, wx.CENTER, 0)
        sizer_h2.Add(sizer_v2, 1, wx.CENTER|wx.LEFT, cw.wins(5))

        sizer_v1.Add(sizer_h2, 0, wx.CENTER|wx.EXPAND, 0)
        sizer_v1.Add(sizer_h3, 0, wx.CENTER|wx.EXPAND, 0)

        sizer_h1.Add(self.slider, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v1, 0, wx.CENTER|wx.LEFT, cw.wins(5))

        sizer.Add(sizer_h1, 0, wx.ALL, cw.wins(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class MoneyViewPanel(wx.Panel):
    def __init__(self, parent, party):
        wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
        self.value = party.money
        # bmp
        bmp = cw.cwpy.rsrc.dialogs["MONEYP"]
        self.bmp_pmoney = cw.util.CWPyStaticBitmap(self, -1, bmp)
        # text
        self.text_pmoney = wx.StaticText(self, -1, str(self.value),
                                        size=(cw.wins(88), -1), style=wx.SUNKEN_BORDER)
        self.text_pmoney.SetFont(cw.cwpy.rsrc.get_wxfont("spin", pixelsize=cw.wins(14)))
        self.text_pmoney.SetBackgroundColour(wx.WHITE)
        self.text_party = wx.StaticText(self, -1, cw.cwpy.msgs["party_money"])
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(12))
        self.text_party.SetFont(font)
        self._do_layout()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        sizer_v1.Add(self.text_party, 0, wx.CENTER, 0)
        sizer_v1.Add(self.text_pmoney, 0, wx.CENTER, 0)

        sizer_h1.Add(self.bmp_pmoney, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v1, 0, wx.CENTER|wx.LEFT, cw.wins(5))

        sizer.Add(sizer_h1, 0, wx.ALL, cw.wins(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

#-------------------------------------------------------------------------------
#  汎用ダイアログ
#-------------------------------------------------------------------------------

class NumberEditDialog(wx.Dialog):

    def __init__(self, parent, title, value, minvalue, maxvalue):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.value = value

        # スライダ
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.slider = NumberEditor(self.panel, value, minvalue, maxvalue)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel.Add(self.panel, 1, wx.EXPAND|wx.ALL, cw.wins(5))

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(30))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(sizer_panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        self.value = self.slider.get_value()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class Number2EditDialog(wx.Dialog):

    def __init__(self, parent, title,
                 label1, value1, minvalue1, maxvalue1,
                 label2, value2, minvalue2, maxvalue2):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.value1 = value1
        self.value2 = value2

        # スライダ
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.box1 = wx.StaticBox(self.panel, -1, label1)
        self.box2 = wx.StaticBox(self.panel, -1, label2)

        self.slider1 = NumberEditor(self.panel, value1, minvalue1, maxvalue1)
        self.slider2 = NumberEditor(self.panel, value2, minvalue2, maxvalue2)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box1 = wx.StaticBoxSizer(self.box1, wx.HORIZONTAL)
        sizer_box2 = wx.StaticBoxSizer(self.box2, wx.HORIZONTAL)

        sizer_box1.Add(self.slider1, 1, wx.EXPAND|wx.ALL, cw.wins(5))
        sizer_box2.Add(self.slider2, 1, wx.EXPAND|wx.ALL, cw.wins(5))

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box1, 1, wx.EXPAND|wx.ALL, cw.wins(5))
        sizer_panel.Add(sizer_box2, 1, wx.EXPAND|wx.BOTTOM|wx.ALL, cw.wins(5))
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(30))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        self.value1 = self.slider1.get_value()
        self.value2 = self.slider2.get_value()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class NumberComboEditDialog(wx.Dialog):

    def __init__(self, parent, title,
                 label1, mlist, selected,
                 label2, value, minvalue, maxvalue):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.selected = value
        self.value = value

        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.box1 = wx.StaticBox(self.panel, -1, label1)
        self.box2 = wx.StaticBox(self.panel, -1, label2)

        # コンボボックス
        self.combo = wx.combo.BitmapComboBox(self.panel, -1, style=wx.CB_READONLY)
        for li in mlist:
            if isinstance(li, (str, unicode)):
                self.combo.Append(li)
            else:
                self.combo.Append(li[0], li[1])
        self.combo.Select(selected)

        # スライダ
        self.slider = NumberEditor(self.panel, value, minvalue, maxvalue)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box1 = wx.StaticBoxSizer(self.box1, wx.HORIZONTAL)
        sizer_box2 = wx.StaticBoxSizer(self.box2, wx.HORIZONTAL)

        sizer_box1.Add(self.combo, 1, wx.EXPAND|wx.ALL, cw.wins(5))
        sizer_box2.Add(self.slider, 1, wx.EXPAND|wx.ALL, cw.wins(5))

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box1, 0, wx.EXPAND|wx.ALL, cw.wins(5))
        sizer_panel.Add(sizer_box2, 1, wx.BOTTOM|wx.ALL, cw.wins(5))
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(30))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        self.selected = self.combo.GetSelection()
        self.value = self.slider.get_value()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class SliderWithButton(wx.Panel):
    _repeat_first = 500
    _repeat_second = 20

    """左右ボタンつきのスライダ。"""
    def __init__(self, parent, value, minvalue, maxvalue, sliderwidth):
        wx.Panel.__init__(self, parent, -1)
        self.SetDoubleBuffered(True)

        # スライダ
        self.slider = wx.Slider(self, -1, 0, 0, 1,
            size=(sliderwidth, -1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.slider.SetFont(cw.cwpy.rsrc.get_wxfont("slider", pixelsize=cw.wins(14)))
        self.slider.SetBackgroundStyle(wx.BG_STYLE_COLOUR)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, cw.wins((20, 40)), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, cw.wins((20, 40)), bmp=bmp)

        self.set_min(minvalue)
        self.set_max(maxvalue)
        self.set_value(value)

        self._timer = wx.Timer(self)

        self._do_layout()
        self._bind()

    def set_value(self, value):
        self.slider.SetValue(value)

    def set_max(self, value):
        maxvalue = value
        minvalue = self.slider.GetMin()
        n = (maxvalue - minvalue) / 20.0 if 20 < (maxvalue - minvalue) else 1
        self.slider.SetTickFreq(n, 1)
        self.slider.SetMax(value)
        self._enable()

    def set_min(self, value):
        maxvalue = self.slider.GetMax()
        minvalue = value
        n = (maxvalue - minvalue) / 20.0 if 20 < (maxvalue - minvalue) else 1
        self.slider.SetTickFreq(n, 1)
        self.slider.SetMin(value)
        self._enable()

    def _enable(self):
        maxvalue = self.slider.GetMax()
        minvalue = self.slider.GetMin()
        self.slider.Enable(minvalue < maxvalue)
        self.leftbtn.Enable(minvalue < maxvalue)
        self.rightbtn.Enable(minvalue < maxvalue)

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)
        self.leftbtn.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDownBtn)
        self.rightbtn.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDownBtn)
        self.leftbtn.Bind(wx.EVT_LEFT_UP, self.OnMouseUpBtn)
        self.rightbtn.Bind(wx.EVT_LEFT_UP, self.OnMouseUpBtn)
        self.leftbtn.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocusBtn)
        self.rightbtn.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocusBtn)

    def _do_layout(self):
        sizer_slider = wx.BoxSizer(wx.HORIZONTAL)
        sizer_slider.Add(self.leftbtn, 0, wx.ALIGN_CENTER)
        sizer_slider.Add(self.slider, 1, wx.LEFT|wx.RIGHT, cw.wins(3))
        sizer_slider.Add(self.rightbtn, 0, wx.ALIGN_CENTER)

        self.SetSizer(sizer_slider)
        sizer_slider.Fit(self)
        self.Layout()

    def OnMouseDownBtn(self, event):
        if event.GetId() == self.leftbtn.GetId():
            self._timerfunc = self._on_leftbtn
            self._timerbtn = self.leftbtn
        elif event.GetId() == self.rightbtn.GetId():
            self._timerfunc = self._on_rightbtn
            self._timerbtn = self.rightbtn
        else:
            assert False
        self._timerfunc()
        self.Bind(wx.EVT_TIMER, self.OnTimer1, self._timer)
        self._timer.Start(SliderWithButton._repeat_first, wx.TIMER_ONE_SHOT)
        event.Skip()

    def OnKillFocusBtn(self, event):
        f = wx.Window.FindFocus()
        if f <> self.leftbtn and f <> self.rightbtn:
            self._end()
        event.Skip()

    def OnMouseUpBtn(self, event):
        self._end()
        event.Skip()

    def _end(self):
        self._timer.Stop()
        def func():
            self._timerfunc = None
            self._timerbtn = None
        wx.CallAfter(func)

    def OnTimer1(self, event):
        pos = self.ScreenToClient(wx.GetMousePosition())
        if self._timerbtn.GetRect().Contains(pos):
            self._timerfunc()
        self._timer.Stop()
        self.Bind(wx.EVT_TIMER, self.OnTimer2, self._timer)
        self._timer.Start(SliderWithButton._repeat_second)

    def OnTimer2(self, event):
        pos = self.ScreenToClient(wx.GetMousePosition())
        if self._timerbtn.GetRect().Contains(pos):
            self._timerfunc()

    def OnLeftBtn(self, event):
        if self._timerfunc:
            return
        self._on_leftbtn()

    def OnRightBtn(self, event):
        if self._timerfunc:
            return
        self._on_rightbtn()

    def _on_leftbtn(self):
        value = self.slider.GetValue()
        if self.slider.GetMin() < value:
            self.slider.SetValue(value-1)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_SLIDER_UPDATED, self.slider.GetId())
            event.SetInt(value-1)
            self.slider.ProcessEvent(event)

    def _on_rightbtn(self):
        value = self.slider.GetValue()
        if value < self.slider.GetMax():
            self.slider.SetValue(value+1)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_SLIDER_UPDATED, self.slider.GetId())
            event.SetInt(value+1)
            self.slider.ProcessEvent(event)

class NumberEditor(wx.Panel):
    def __init__(self, parent, value, minvalue, maxvalue):
        wx.Panel.__init__(self, parent, -1)

        # スライダー
        self.slider = SliderWithButton(self, value, minvalue, maxvalue, cw.wins(200))

        # スピン
        self.spinlabel = wx.StaticText(self, -1, u"直接入力:")
        self.spinlabel.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg2", pixelsize=cw.wins(14)))
        self.spinctrl = wx.SpinCtrl(self, -1, "", size=(cw.wins(80), -1))
        self.spinctrl.SetFont(cw.cwpy.rsrc.get_wxfont("spin", pixelsize=cw.wins(14)))
        self.spinctrl.SetRange(minvalue, maxvalue)
        self.spinctrl.SetValue(value)

        self.set_min(minvalue)
        self.set_max(maxvalue)
        self.set_value(value)

        self._do_layout()
        self._bind()

    def get_value(self):
        return self.slider.slider.GetValue()

    def set_value(self, value):
        self.slider.set_value(value)
        self.spinctrl.SetValue(value)

    def set_max(self, value):
        self.slider.set_max(value)
        self.spinctrl.SetRange(self.spinctrl.GetMin(), value)
        self._enable()

    def set_min(self, value):
        self.slider.set_min(value)
        self.spinctrl.SetRange(value, self.spinctrl.GetMax())
        self._enable()

    def _enable(self):
        maxvalue = self.slider.slider.GetMax()
        minvalue = self.slider.slider.GetMin()
        self.spinctrl.Enable(minvalue < maxvalue)

    def _bind(self):
        self.slider.slider.Bind(wx.EVT_SLIDER, self.OnSlider)
        self.spinctrl.Bind(wx.EVT_SPINCTRL, self.OnSpinCtrl)

    def _do_layout(self):
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)

        sizer_v1.Add(self.slider, 1, wx.BOTTOM|wx.EXPAND, cw.wins(5))

        sizer_spinctrl = wx.BoxSizer(wx.HORIZONTAL)
        sizer_spinctrl.Add(self.spinlabel, 0, wx.ALIGN_CENTER|wx.RIGHT, cw.wins(5))
        sizer_spinctrl.Add(self.spinctrl, 0, 0, cw.wins(0))

        sizer_v1.Add(sizer_spinctrl, 0, wx.ALIGN_RIGHT, cw.wins(0))

        self.SetSizer(sizer_v1)
        sizer_v1.Fit(self)
        self.Layout()

    def OnSlider(self, evt):
        self.spinctrl.SetValue(self.slider.slider.GetValue())

    def OnSpinCtrl(self, evt):
        self.slider.slider.SetValue(self.spinctrl.GetValue())

class ComboEditDialog(wx.Dialog):

    def __init__(self, parent, title, label, mlist, selected):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.selected = selected

        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.box = wx.StaticBox(self.panel, -1, label)

        # コンボボックス
        self.combo = wx.combo.BitmapComboBox(self.panel, -1, style=wx.CB_READONLY)
        for li in mlist:
            if isinstance(li, (str, unicode)):
                self.combo.Append(li)
            else:
                self.combo.Append(li[0], li[1])
        self.combo.Select(selected)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box = wx.StaticBoxSizer(self.box, wx.HORIZONTAL)

        sizer_box.Add(self.combo, 1, wx.EXPAND|wx.ALL, cw.wins(5))

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box, 0, wx.EXPAND|wx.ALL, cw.wins(5))
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(20))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        self.selected = self.combo.GetSelection()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class ComboEditDialog2(wx.Dialog):
    def __init__(self, parent, title, message, choices):
        wx.Dialog.__init__(self, parent, -1, title, size=cw.wins((-1, -1)),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.message = cw.util.txtwrap(message, 0, width=40, wrapschars=cw.util.WRAPS_CHARS)

        self.combo = wx.Choice(self, -1, size=cw.wins((200, -1)), choices=choices)
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(16))
        self.combo.SetFont(font)
        self.selected = 0
        self.combo.Select(self.selected)

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

        w = cw.wins(318)
        h = self.okbtn.GetSize()[1] + self.okbtn.GetPosition()[1] + cw.wins(10)
        self.SetClientSize((w, h))

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        self.selected = self.combo.GetSelection()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
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
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15))
        dc.SetFont(font)
        s = self.message
        w, _h, _lineheight = dc.GetMultiLineTextExtent(s)
        dc.DrawText(s, (csize[0]-w)/2, cw.wins(10))

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _do_layout(self):
        dc = wx.ClientDC(self)
        self._textwidth, self._textheight, _lineheight = dc.GetMultiLineTextExtent(self.message)

        csize = cw.wins(318), cw.wins(0)
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add((cw.wins(0), cw.wins(20)+self._textheight), 0, 0, 0)
        margin = (csize[0] - self.combo.GetSize()[0]) / 2
        sizer_1.Add(self.combo, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)

        sizer_1.Add(sizer_2, 0, wx.EXPAND, 0)
        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        self.SetSizer(sizer_1)
        self.Layout()

#-------------------------------------------------------------------------------
#  レベル調節ダイアログ
#-------------------------------------------------------------------------------

class LevelEditDialog(wx.Dialog):
    def __init__(self, parent, mlist, selected, party=None):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["regulate_level_title"],
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)

        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)

        self.list = mlist
        self.party = party

        # 対象者
        self.targets = [u"全員"]
        for ccard in self.list:
            self.targets.append(ccard.get_name())
        self.target = wx.ComboBox(self.panel, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        self.target.Select(max(selected, -1) + 1)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((20, 20)), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((20, 20)), bmp=bmp)

        minvalue = 1
        maxvalue = self.get_maxlevel()

        # スライダ
        self.slider = NumberEditor(self.panel, maxvalue, minvalue, maxvalue)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                      cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])

        self._select_target()

        self._do_layout()
        self._bind()

    def get_selected(self):
        index = self.target.GetSelection()
        if index <= 0:
            return self.list
        else:
            return [self.list[index-1]]

    def get_currentlevel(self):
        level = None

        for ccard in self.get_selected():
            if level is None:
                level = ccard.level
            elif level <> ccard.level:
                level = None
                break

        if level is None:
            return self.get_maxlevel()
        else:
            return level

    def get_maxlevel(self):
        maxvalue = 0
        for ccard in self.get_selected():
            maxvalue = max(maxvalue, ccard.get_limitlevel())

        return maxvalue

    def _select_target(self):
        self.slider.set_max(self.get_maxlevel())
        self.slider.set_value(self.get_currentlevel())

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=cw.wins(5))
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_combo, 0, wx.EXPAND|wx.ALL, cw.wins(5))
        sizer_panel.Add(self.slider, 1, wx.BOTTOM|wx.ALL, cw.wins(5))
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, cw.wins(30))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, cw.wins(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnSelectTarget(self, event):
        self._select_target()

    def OnLeftBtn(self, event):
        index = self.target.GetSelection()
        if index <= 0:
            self.target.SetSelection(len(self.list))
        else:
            self.target.SetSelection(index - 1)
        self._select_target()

    def OnRightBtn(self, event):
        index = self.target.GetSelection()
        if len(self.list) <= index:
            self.target.SetSelection(0)
        else:
            self.target.SetSelection(index + 1)
        self._select_target()

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

    def OnOk(self, event):
        def func(seq, level, party):
            update = False
            for ccard in seq:
                clevel = min(level, ccard.get_limitlevel())
                if ccard.level == clevel:
                    continue

                ccard.set_level(clevel, regulate=True, backpack_party=party)
                ccard.is_edited = True
                if hasattr(ccard, "cardimg") and hasattr(ccard.cardimg, "set_levelimg"):
                    update = True
                    cw.cwpy.play_sound("harvest")
                    cw.animation.animate_sprite(ccard, "hide")
                    ccard.cardimg.set_levelimg(ccard.level)
                    ccard.update_image()
                    cw.animation.animate_sprite(ccard, "deal")

            if not update:
                cw.cwpy.play_sound("harvest")

        selected = self.get_selected()
        level = self.slider.get_value()
        cw.cwpy.exec_func(func, selected, level, self.party)

        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

#-------------------------------------------------------------------------------
# テキスト入力ダイアログ
#-------------------------------------------------------------------------------

class InputTextDialog(wx.Dialog):
    def __init__(self, parent, title, msg, text="", maxlength=0):
        wx.Dialog.__init__(self, parent, -1, title, size=cw.wins((318, 180)),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.SetClientSize(cw.wins((312, 112)))
        self.msg = msg
        self.textctrl = wx.TextCtrl(self, size=cw.wins((175, 24)))
        self.textctrl.SetMaxLength(maxlength)
        self.textctrl.SetValue(text)
        self.textctrl.SelectAll()
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.textctrl.SetFont(font)
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self.okbtn.Enable(bool(text))
        self._do_layout()
        self._bind()

    def OnInput(self, event):
        self.text = self.textctrl.GetValue()

        if self.text:
            self.okbtn.Enable()
        else:
            self.okbtn.Disable()

    def OnOk(self, event):
        self.text = self.textctrl.GetValue()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        self.text = u""
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
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14))
        dc.SetFont(font)
        s = self.msg
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, cw.wins(10))

    def _bind(self):
        self.Bind(wx.EVT_TEXT, self.OnInput, self.textctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _do_layout(self):
        csize = self.GetClientSize()
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(cw.wins((0, 35)), 0, 0, 0)
        margin = (csize[0] - self.textctrl.GetSize()[0]) / 2
        sizer_1.Add(self.textctrl, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add(cw.wins((0, 12)), 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_2.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)

        self.SetSizer(sizer_1)
        self.Layout()

#-------------------------------------------------------------------------------
# 宿情報編集ダイアログ
#-------------------------------------------------------------------------------

class YadoEditDialog(wx.Dialog):
    def __init__(self, parent, yadodir):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["rename_base_title"], size=cw.wins((318, 180)),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.yadodir = yadodir
        self.path = cw.util.join_paths(yadodir, "Environment.xml")
        self.SetClientSize(cw.wins((312, 136)))
        self.textctrl = wx.TextCtrl(self, size=cw.wins((175, 24)))
        self.textctrl.SetMaxLength(18)
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.textctrl.SetFont(font)
        self.name = cw.header.GetName(self.path).name
        if not self.name:
            self.name = os.path.basename(self.yadodir)
        self.textctrl.SetValue(self.name)
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

    def OnInput(self, event):
        name = self.textctrl.GetValue().strip()

        if name:
            self.okbtn.Enable()
        else:
            self.okbtn.Disable()

    def OnOk(self, event):
        cw.cwpy.play_sound("harvest")
        name = self.textctrl.GetValue().strip()
        if name <> self.name:

            # データ上の編集
            data = cw.data.xml2etree(self.path)
            if not data.find("Property/Name") is None:
                data.edit("Property/Name", name)
            else:
                e = data.make_element("Name", name)
                data.insert("Property", e, 0)
            data.write(self.path)

            # ディレクトリの移動
            yadodir = os.path.dirname(self.yadodir)
            dname = cw.binary.util.check_filename(name)
            if os.path.normcase(os.path.basename(self.yadodir)) <> os.path.normcase(dname):
                yadodir = cw.util.join_paths(yadodir, dname)
                yadodir = cw.binary.util.check_duplicate(yadodir)
                try:
                    shutil.move(self.yadodir, yadodir)
                    self.yadodir = yadodir
                except Exception:
                    cw.util.print_ex()

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
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
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14))
        dc.SetFont(font)
        s = cw.cwpy.msgs["rename_base_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, cw.wins(10))

    def _bind(self):
        self.Bind(wx.EVT_TEXT, self.OnInput, self.textctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _do_layout(self):
        csize = self.GetClientSize()
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add(cw.wins((0, 35)), 0, 0, 0)
        margin = (csize[0] - self.textctrl.GetSize()[0]) / 2
        sizer_1.Add(self.textctrl, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add(cw.wins((0, 25)), 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_2.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)

        self.SetSizer(sizer_1)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
