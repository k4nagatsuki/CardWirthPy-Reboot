#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


#-------------------------------------------------------------------------------
#　パーティ情報変更ダイアログ
#-------------------------------------------------------------------------------

class PartyEditor(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["party_information"],
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
                                                            (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])
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
        cw.cwpy.sounds["harvest"].play()
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
        cw.cwpy.sounds["click"].play()
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
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic"))
        s = cw.cwpy.msgs["party_name"]
        left = (dc.GetSize()[0] - dc.GetTextExtent(s)[0]) / 2
        dc.DrawText(s, left, 15)
        s = cw.cwpy.msgs["party_money"]
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
        self.text_party = wx.StaticText(self, -1, cw.cwpy.msgs["party_money"])
        font = cw.cwpy.rsrc.get_wxfont(size=8, weight=wx.NORMAL)
        self.text_party.SetFont(font)
        self.text_yado = wx.StaticText(self, -1, cw.cwpy.msgs["base_money"])
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
        self.text_party = wx.StaticText(self, -1, cw.cwpy.msgs["party_money"])
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

#-------------------------------------------------------------------------------
#  汎用ダイアログ
#-------------------------------------------------------------------------------

class NumberEditDialog(wx.Dialog):

    def __init__(self, parent, title, value, minvalue, maxvalue):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.value = value

        # スライダ
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.slider = NumberEditor(self.panel, value, minvalue, maxvalue)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel.Add(self.panel, 1, wx.EXPAND|wx.ALL, 5)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, 30)

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(sizer_panel, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, 15)
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
        cw.cwpy.sounds["harvest"].play()
        self.value = self.slider.slider.GetValue()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class Number2EditDialog(wx.Dialog):

    def __init__(self, parent, title,
                 label1, value1, minvalue1, maxvalue1,
                 label2, value2, minvalue2, maxvalue2):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
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
                                                      (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box1 = wx.StaticBoxSizer(self.box1, wx.HORIZONTAL)
        sizer_box2 = wx.StaticBoxSizer(self.box2, wx.HORIZONTAL)

        sizer_box1.Add(self.slider1, 1, wx.EXPAND|wx.ALL, 5)
        sizer_box2.Add(self.slider2, 1, wx.EXPAND|wx.ALL, 5)

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box1, 1, wx.EXPAND|wx.ALL, 5)
        sizer_panel.Add(sizer_box2, 1, wx.EXPAND|wx.BOTTOM|wx.ALL, 5)
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, 30)

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, 15)
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
        cw.cwpy.sounds["harvest"].play()
        self.value1 = self.slider1.slider.GetValue()
        self.value2 = self.slider2.slider.GetValue()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class NumberComboEditDialog(wx.Dialog):

    def __init__(self, parent, title,
                 label1, list, selected,
                 label2, value, minvalue, maxvalue):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.selected = value
        self.value = value

        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.box1 = wx.StaticBox(self.panel, -1, label1)
        self.box2 = wx.StaticBox(self.panel, -1, label2)

        # コンボボックス
        self.combo = wx.combo.BitmapComboBox(self.panel, -1, style=wx.CB_READONLY)
        for li in list:
            if isinstance(li, (str, unicode)):
                self.combo.Append(li)
            else:
                self.combo.Append(li[0], li[1])
        self.combo.Select(selected)

        # スライダ
        self.slider = NumberEditor(self.panel, value, minvalue, maxvalue)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box1 = wx.StaticBoxSizer(self.box1, wx.HORIZONTAL)
        sizer_box2 = wx.StaticBoxSizer(self.box2, wx.HORIZONTAL)

        sizer_box1.Add(self.combo, 1, wx.EXPAND|wx.ALL, 5)
        sizer_box2.Add(self.slider, 1, wx.EXPAND|wx.ALL, 5)

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box1, 0, wx.EXPAND|wx.ALL, 5)
        sizer_panel.Add(sizer_box2, 1, wx.BOTTOM|wx.ALL, 5)
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, 30)

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, 15)
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
        cw.cwpy.sounds["harvest"].play()
        self.selected = self.combo.GetSelection()
        self.value = self.slider.slider.GetValue()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class NumberEditor(wx.Panel):
    def __init__(self, parent, value, minvalue, maxvalue):
        wx.Panel.__init__(self, parent, -1)

        # スライダ
        self.slider = wx.Slider(self, -1, value, minvalue, maxvalue,
            size=(200, -1), style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        self.slider.SetBackgroundStyle(wx.BG_STYLE_COLOUR)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 40), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 40), bmp=bmp)

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.leftbtn, 0, wx.ALIGN_CENTER)
        sizer.Add(self.slider, 1, wx.LEFT|wx.RIGHT|wx.ALL, 5)
        sizer.Add(self.rightbtn, 0, wx.ALIGN_CENTER)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnLeftBtn(self, evt):
        value = self.slider.GetValue()
        if self.slider.GetMin() < value:
            self.slider.SetValue(value-1)

    def OnRightBtn(self, evt):
        value = self.slider.GetValue()
        if value < self.slider.GetMax():
            self.slider.SetValue(value+1)

class ComboEditDialog(wx.Dialog):

    def __init__(self, parent, title, label, list, selected):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.selected = selected

        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.box = wx.StaticBox(self.panel, -1, label)

        # コンボボックス
        self.combo = wx.combo.BitmapComboBox(self.panel, -1, style=wx.CB_READONLY)
        for li in list:
            if isinstance(li, (str, unicode)):
                self.combo.Append(li)
            else:
                self.combo.Append(li[0], li[1])
        self.combo.Select(selected)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                      (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_box = wx.StaticBoxSizer(self.box, wx.HORIZONTAL)

        sizer_box.Add(self.combo, 1, wx.EXPAND|wx.ALL, 5)

        sizer_panel = wx.BoxSizer(wx.VERTICAL)
        sizer_panel.Add(sizer_box, 0, wx.EXPAND|wx.ALL, 5)
        self.panel.SetSizer(sizer_panel)

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 0, 0, 0)
        sizer_btn.Add(self.cnclbtn, 0, wx.LEFT, 20)

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(self.panel, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_btn, 0, wx.CENTER|wx.TOP, 10)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, 15)
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
        cw.cwpy.sounds["harvest"].play()
        self.selected = self.combo.GetSelection()
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

#-------------------------------------------------------------------------------
#  レベル調節ダイアログ
#-------------------------------------------------------------------------------

class LevelEditDialog(NumberEditDialog):
    def __init__(self, parent, ccard):
        if ccard:
            self.ccard = ccard
        else:
            self.ccard = cw.cwpy.selection

        minvalue = 1
        maxvalue = self.ccard.level
        coupons = self.ccard.get_specialcoupons()
        if u"＠レベル原点" in coupons:
            maxvalue = coupons[u"＠レベル原点"]

        NumberEditDialog.__init__(self, parent, cw.cwpy.msgs["regulate_level_title"],
                self.ccard.level, minvalue, maxvalue)

    def OnOk(self, event):
        def func(ccard, level):
            cw.cwpy.sounds["harvest"].play()
            if ccard.level <> level:
                ccard.set_level(level, regulate=True)
                ccard.is_edited = True
            if hasattr(ccard, "cardimg"):
                cw.animation.animate_sprite(ccard, "hide")
                ccard.cardimg.set_levelimg(ccard.level)
                ccard.update_image()
                cw.animation.animate_sprite(ccard, "deal")

        cw.cwpy.exec_func(func, self.ccard, self.slider.slider.GetValue())

        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

def main():
    pass

if __name__ == "__main__":
    main()
