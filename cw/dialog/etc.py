#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import pygame

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
        accel = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.leftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.rightkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, self.returnkeyid),
        ])
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
            image = bmp.ConvertToImage()
            size = image.GetSize()
            image = image.Rescale(size[0]/10*9, size[1]/10*9)
            bmp = image.ConvertToBitmap()
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
        for name, desc, func in self.items:
            btn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=name)
            self.buttons.append(btn)

        self.panel = wx.Panel(self, -1, style=wx.BORDER)
        self.desc = wx.StaticText(self.panel, -1, size=cw.wins((210, 150)), style=wx.ST_NO_AUTORESIZE)
        self.desc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", pixelsize=cw.wins(14)))

        self.btn_cncl = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["cancel"])
        self._bind()
        self._do_layout()

    def _bind(self):
        for btn in self.buttons:
            btn.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
            btn.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
            self.Bind(wx.EVT_BUTTON, self.OnBotton, btn)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

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

def main():
    pass

if __name__ == "__main__":
    main()
