#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


class BattleCommand(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["select_battle_action"])
        # 行動開始
        path = "Resource/Image/Card/BATTLE" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["start_action"]).get_wxbmp()
        self.btn_start = wx.BitmapButton(self, -1, bitmap=bmp,
                                            style=wx.NO_BORDER|wx.BU_AUTODRAW)
        # 逃げる
        path = "Resource/Image/Card/ACTION9" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["runaway"]).get_wxbmp()
        self.btn_runaway = wx.BitmapButton(self, -1, bitmap=bmp,
                                            style=wx.NO_BORDER|wx.BU_AUTODRAW)
        # キャンセル
        path = "Resource/Image/Card/COMMAND1" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.image.CardImage(path, "NORMAL", cw.cwpy.msgs["cancel"]).get_wxbmp()
        self.btn_cancel = wx.BitmapButton(self, wx.ID_CANCEL, bitmap=bmp,
                                            style=wx.NO_BORDER|wx.BU_AUTODRAW)
        self._do_layout()
        self._bind()

    def _do_layout(self):
        sz = wx.BoxSizer(wx.VERTICAL)
        sz_h1 = wx.BoxSizer(wx.HORIZONTAL)

        sz_h1.Add(self.btn_start, 0, wx.CENTER, 0)
        sz_h1.Add(self.btn_runaway, 0, wx.CENTER|wx.LEFT, 5)
        sz_h1.Add(self.btn_cancel, 0, wx.CENTER|wx.LEFT, 5)

        sz.Add(sz_h1, 0, wx.ALL, 5)
        self.SetSizer(sz)
        sz.Fit(self)
        self.Layout()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_BUTTON, self.OnStart, self.btn_start)
        self.Bind(wx.EVT_BUTTON, self.OnRunaway, self.btn_runaway)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.btn_start.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.btn_cancel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.btn_runaway.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def OnStart(self, event):
        if cw.cwpy.battle and cw.cwpy.battle.is_ready():
            cw.cwpy.exec_func(cw.cwpy.battle.start)

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnRunaway(self, event):
        s = cw.cwpy.msgs["confirm_runaway"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            if cw.cwpy.battle:
                cw.cwpy.exec_func(cw.cwpy.battle.runaway)

            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint (self, event):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

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
        sizer.Add(self.btn_ok, 0, wx.CENTER|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
