#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import itertools

import wx
import wx.combo
import wx.lib.buttons
import pygame.time

import cw
import cardinfo
import message

# カード操作ダイアログのモード
CCMODE_SHOW   = 0 # 閲覧モード
CCMODE_MOVE   = 1 # 移動モード
CCMODE_BATTLE = 2 # 戦闘行動選択モード
CCMODE_USE    = 3 # 使用モード

#-------------------------------------------------------------------------------
# カード操作ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CardControl(wx.Dialog):
    def __init__(self, parent, name, sendto, sort, areaid=None):
        # ダイアログ作成
        wx.Dialog.__init__(self, parent, -1, "%s - %s" % (cw.cwpy.msgs["card_control"], name),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)

        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((90, 24)), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp)
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((500, 255)))
        self.toppanel.SetBackgroundColour(self.bgcolour)
        self.toppanel.SetDoubleBuffered(True)

        self._sizer_topbar = wx.BoxSizer(wx.HORIZONTAL)

        # sort
        self.star = cw.wins(cw.cwpy.rsrc.debugs["BOOKMARK"])
        self.nostar = cw.wins(cw.cwpy.rsrc.debugs["BOOKMARK_EMPTY"])
        self.starlight = cw.wins(cw.cwpy.rsrc.debugs["BOOKMARK_LIGHTUP"])
        self._laststar = None

        self.sort = wx.combo.BitmapComboBox(self.toppanel, size=cw.wins((75, 20)), style=wx.CB_READONLY)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14), weight=wx.NORMAL))
        self.sort.Append(cw.cwpy.msgs["sort_no"])
        self.sort.Append(cw.cwpy.msgs["sort_name"])
        self.sort.Append(cw.cwpy.msgs["sort_level"])
        self.sort.Append(cw.cwpy.msgs["sort_type"])
        self.sort.Append(cw.cwpy.msgs["sort_price"])
        self.sortwithstar = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 20)), bmp=self.star)
        self.sortwithstar.SetToolTipString(cw.cwpy.msgs["sort_with_star"])
        self._update_sortwithstar()
        if not sort:
            self.sort.Freeze()
            self.sort.Hide()
            self.sortwithstar.Freeze()
            self.sortwithstar.Hide()

        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 20)), bmp=bmp)
        # sendto
        self.combo = wx.combo.BitmapComboBox(self.toppanel, size=cw.wins((115, 20)), style=wx.CB_READONLY)
        self.combo.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14), weight=wx.NORMAL))
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 20)), bmp=bmp)
        if not sendto:
            self.leftbtn2.Hide()
            self.rightbtn2.Hide()
            self.combo.Hide()
        # focus
        self.panel.SetFocusIgnoringChildren()
        self.toppanel.SetFocusIgnoringChildren()

        self._drawlist = {}
        self._leftmark = None
        self._after_event = None

        self._proc = False

        self.draw_cards()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.closebtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn2, self.leftbtn2)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn2, self.rightbtn2)
        self.Bind(wx.EVT_BUTTON, self.OnSortWithStar, self.sortwithstar)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_COMBOBOX, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMove)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.toppanel.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.toppanel.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)
        self.panel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp2)
        for child in itertools.chain(self.toppanel.GetChildren(), self.panel.GetChildren()):
            child.Bind(wx.EVT_RIGHT_UP, self.OnRightUp2)

        self.leftkeyid = wx.NewId()
        self.rightkeyid = wx.NewId()
        self.upid = wx.NewId()
        self.downid = wx.NewId()
        self.returnkeyid = wx.NewId()
        self.leftpagekeyid = wx.NewId()
        self.rightpagekeyid = wx.NewId()
        self.uptargkeyid = wx.NewId()
        self.downtargkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.rightkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.returnkeyid)
        self.Bind(wx.EVT_MENU, self.OnUp, id=self.upid)
        self.Bind(wx.EVT_MENU, self.OnDown, id=self.downid)
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn2, id=self.uptargkeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn2, id=self.downtargkeyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.leftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.rightkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_UP, self.upid),
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, self.downid),
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, self.returnkeyid),
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.leftpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.rightpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_UP, self.uptargkeyid),
            (wx.ACCEL_CTRL, wx.WXK_DOWN, self.downtargkeyid),
        ]
        self.sortkeydown = []
        for i in xrange(0, 9):
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_NORMAL, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
        accel = wx.AcceleratorTable(seq)
        self.SetAcceleratorTable(accel)

    def OnNumberKeyDown(self, event):
        """
        数値キー'1'～'9'までの押下を処理する。
        CardControlではソート条件の変更を行う。
        """
        if self.sort.IsShown():
            index = self.sortkeydown.index(event.GetId())
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                event = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.sort.GetId())
                self.ProcessEvent(event)

    def _do_layout(self, sizer_leftbar):
        """
        引数に子クラスで設定したsizer_leftbarが必要
        """
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_toppanel = wx.GridBagSizer(1, 1)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        # トップバー
        self._re_layout_topbar()
        # トップパネルにトップバーとレフトバーを設定
        sizer_toppanel.Add(self._sizer_topbar, (0,0), (1,2), wx.EXPAND)
        sizer_toppanel.Add(sizer_leftbar, (1,0), (1,1), wx.EXPAND)
        sizer_toppanel.Add(cw.wins((420, 235)), (1,1), (1,1), wx.EXPAND)
        self.toppanel.SetSizer(sizer_toppanel)
        # ボタンバー
        width = self.toppanel.GetClientSize()[0] - cw.wins(6)
        margin = (width - cw.wins(60) - self.closebtn.GetSize()[0]) / 2
        margin2 = margin + ((width - cw.wins(60) - self.closebtn.GetSize()[0]) % 2)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((margin2, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)
        # トップパネルとボタンバーのサイザーを設定
        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _re_layout_topbar(self):
        sortsize = self.sort.GetSize()[0], cw.wins(20)
        starsize = self.sortwithstar.GetSize()
        combosize = self.combo.GetSize()[0], cw.wins(20)
        self._sizer_topbar.Clear()
        self._sizer_topbar.SetMinSize(combosize)
        if self.combo.IsShown():
            self._sizer_topbar.Add((cw.wins(500)-combosize[0]-cw.wins(65)-starsize[0]-sortsize[0]-cw.wins(40), 0), 0, 0, 0)
            if self.sort.IsShown():
                self._sizer_topbar.Add(self.sort, 0, 0, 0)
                self._sizer_topbar.Add(self.sortwithstar, 0, 0, 0)
            else:
                self._sizer_topbar.Add(self.sort.GetSize(), 0, 0, 0)
                self._sizer_topbar.Add(self.sortwithstar.GetSize(), 0, 0, 0)
            self._sizer_topbar.Add(cw.wins((60, 0)), 0, 0, 0)
            self._sizer_topbar.Add(self.leftbtn2, 0, 0, 0)
            self._sizer_topbar.Add(self.combo, 0, 0, 0)
            self._sizer_topbar.Add(self.rightbtn2, 0, 0, 0)
        else:
            self._sizer_topbar.Add((cw.wins(500)-starsize[0]-sortsize[0], 0), 0, 0, 0)
            self._sizer_topbar.Add(self.sort, 0, 0, 0)
            self._sizer_topbar.Add(self.sortwithstar, 0, 0, 0)

    def OnSort(self, event):
        pass

    def OnSortWithStar(self, event):
        pass

    def _update_sortwithstar(self):
        pass

    def OnUp(self, event):
        pass

    def OnDown(self, event):
        pass

    def OnKeyDown(self, event):
        if self._proc:
            return

        id = event.GetId()

        list = None
        if id == self.returnkeyid:
            for header in self.get_headers():
                if header.negaflag:
                    cw.cwpy.sounds["click"].play()
                    def func():
                        self.lclick_event(header)
                    self.animate_click(header, func)
                    return
        elif id == self.leftkeyid:
            list = self.get_headers()[:]
            list.reverse()
        elif id == self.rightkeyid:
            list = self.get_headers()

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

        self.set_cardpos()

        if c1:
            c1.negaflag = False
            self.draw_card(c1, True)
        if c2:
            c2.negaflag = True
            self.draw_card(c2, True)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            if self.leftbtn.IsEnabled():
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn.GetId())
                self.ProcessEvent(btnevent)
        else:
            if self.rightbtn.IsEnabled():
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn.GetId())
                self.ProcessEvent(btnevent)

    def OnLeftUp(self, event):
        if self._proc:
            return

        mousepos = event.GetPosition()
        for header in self.get_headers():
            if header.wxrect.collidepoint(mousepos):
                rect, x, y = self._get_starrect(header)
                if rect.Contains(mousepos):
                    cw.cwpy.sounds["page"].play()
                    if header.star:
                        header.set_star(0)
                    else:
                        header.set_star(1)
                    if self.callname == "STOREHOUSE":
                        if cw.cwpy.setting.sort_storehousewithstar:
                            self._update_sortattr()
                    elif self.callname in ("BACKPACK", "CARDPOCKETB"):
                        if cw.cwpy.setting.sort_backpackwithstar:
                            self._update_sortattr()
                    return
                else:
                    cw.cwpy.sounds["click"].play()
                    def func():
                        self.lclick_event(header)
                    self.animate_click(header, func)
                    return

    def _update_sortattr(self):
        pass

    def OnRightUp(self, event):
        if self._proc:
            return

        cw.cwpy.sounds["click"].play()

        for header in self.get_headers():
            if header.wxrect.collidepoint(event.GetPosition()):
                def func():
                    dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
                    self.Parent.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()
                self.animate_click(header, func)
                return

        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnRightUp2(self, event):
        cw.cwpy.sounds["click"].play()
        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnMove(self, event):
        mousepos = event.GetPosition()

        self.set_cardpos()

        if not self.IsShown():
            return

        laststar = None
        for header in self.get_headers():
            draw = False
            if header.wxrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    draw = True

            elif header.negaflag:
                header.negaflag = False
                draw = True

            rect, x, y = self._get_starrect(header)
            if rect.Contains(mousepos):
                laststar = header
            draw |= laststar <> self._laststar

            if draw:
                self.draw_card(header)

        self._laststar = laststar

    def OnEnter(self, event):
        self.OnMove(event)

    def OnLeave(self, event):
        if self.IsActive():
            self.set_cardpos()

            for header in self.get_headers():
                if header.negaflag:
                    header.negaflag = False
                    self.draw_card(header)

    def OnClickLeftBtn2(self, event):
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if index == 0:
            self.combo.SetSelection(count - 1)
        else:
            self.combo.SetSelection(index - 1)

    def OnClickRightBtn2(self, event):
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if count <= index + 1:
            self.combo.SetSelection(0)
        else:
            self.combo.SetSelection(index + 1)

    def OnPaint(self, event):
        self.set_cardpos()

        dc = wx.PaintDC(self.toppanel)

        # 背景色
        dc.SetBrush(wx.Brush(self.bgcolour))
        dc.DrawRectangle(0, 0, cw.wins(505), cw.wins(260))
        # 背景の透かし
        bmp = cw.cwpy.rsrc.dialogs["PAD"]
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, (cw.wins(500)-size[0])/2, (cw.wins(255)-size[1])/2, True)
        # ライン
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHIGHLIGHT)
        dc.SetPen(wx.Pen(colour, cw.wins(1), wx.SOLID))
        dc.DrawLine(cw.wins(1), cw.wins(20), cw.wins(499), cw.wins(20))
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DSHADOW)
        dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
        dc.DrawLine(cw.wins(1), cw.wins(21), cw.wins(499), cw.wins(21))
        # モード見出し
        dc.SetTextForeground(wx.LIGHT_GREY)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15)))
        mode = self.get_mode()
        if mode == CCMODE_SHOW:
            s = cw.cwpy.msgs["mode_show"]
        elif mode == CCMODE_MOVE:
            s = cw.cwpy.msgs["mode_move"]
        elif mode == CCMODE_BATTLE:
            s = cw.cwpy.msgs["mode_battle"]
        else:
            s = cw.cwpy.msgs["mode_use"]
        dc.DrawText(s, cw.wins(8), cw.wins(2))
        if self.sort.IsShown():
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["sort_title"]
            if self.combo.IsShown():
                dc.DrawText(s, cw.wins(150), cw.wins(3))
            else:
                dc.DrawText(s, cw.wins(365), cw.wins(3))
        if self.combo.IsShown():
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["send_to"]
            dc.DrawText(s, cw.wins(295), cw.wins(3))
        # カード枚数のフォント設定
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))

        # カードの描画
        mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
        for header, data in self._drawlist.iteritems():
            bmp, usemask = data
            x = header.wxrect.left
            y = header.wxrect.top
            w = bmp.GetWidth()
            h = bmp.GetHeight()
            x += (header.wxrect.width-w) / 2
            y += (header.wxrect.height-h) / 2
            dc.DrawBitmap(bmp, x, y, usemask)
            if self.callname in ("BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
                rect, x, y = self._get_starrect(header)
                if rect.Contains(mousepos):
                    bmp = self.starlight
                elif header.star:
                    bmp = self.star
                elif header.negaflag:
                    bmp = self.nostar
                else:
                    bmp = None

                if bmp:
                    dc.DrawBitmap(bmp, x, y, True)

        # カード置場・荷物袋・情報カードマーク
        if self._leftmark:
            dc.DrawBitmap(self._leftmark, cw.wins(3), cw.wins(85), True)

        if self.callname == "CARDPOCKET":
            # 所持カード数
            num = len(self.selection.cardpocket[self.index3])
            maxnum = self.selection.get_cardpocketspace()[self.index3]
            s = "Cap " + str(num) + "/" + str(maxnum)
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, cw.wins(40)-w/2, cw.wins(220))
        elif self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
             # カード置き場、荷物袋、情報カード
             # ページ番号
             s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
             s += "/" + str((len(self.list)+9)/10) if len(self.list) > 0 else "/1"
             w = dc.GetTextExtent(s)[0]
             dc.DrawText(s, cw.wins(40)-w/2, cw.wins(180))

        # 保留中のイベントを実施
        if self._after_event:
            cw.cwpy.frame.exec_func(self._after_event)
            self._after_event = None

    def _get_starrect(self, header):
        if not self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            return wx.Rect(0, 0, 0, 0), 0, 0
        x = header.wxrect.left
        y = header.wxrect.top
        bmp, usemask = self._drawlist[header]
        w = bmp.GetWidth()
        h = bmp.GetHeight()
        x += (header.wxrect.width-w) / 2
        y += (header.wxrect.height-h) / 2
        sw = self.star.GetWidth()
        sh = self.star.GetHeight()
        x = x+w - sw - cw.wins(5)
        y = y+h - sh - cw.wins(5)
        return wx.Rect(x-cw.wins(4), y-cw.wins(4), sw+cw.wins(8), sh+cw.wins(8)), x, y

    def draw(self, update=True):
        if update:
            self.draw_cards(update)
        self.toppanel.Refresh()

    def get_mode(self):
        if self.callname == "INFOVIEW" or\
            (self.callname == "CARDPOCKET" and isinstance(self.selection, cw.character.Friend)) or\
            (self.callname == "HANDVIEW" and not cw.cwpy.debug and isinstance(self.selection, (cw.character.Enemy, cw.character.Friend))):
            return CCMODE_SHOW
        elif self.areaid in cw.AREAS_TRADE:
            return CCMODE_MOVE
        elif self.callname == "HANDVIEW":
            return CCMODE_BATTLE
        else:
            return CCMODE_USE

    def draw_cards(self, update=True, mode=-1):
        self._drawlist = {}
        if mode == -1:
            if self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
                mode = 1
            elif self.callname == "CARDPOCKET":
                mode = 2
            elif self.callname == "HANDVIEW":
                mode = 3
            else:
                assert False, self.callname

        self.set_cardpos()

        for header in self.get_headers():
            self.draw_card(header)
        self.toppanel.Refresh()

    def draw_card(self, header, fromkeyevent=False):
        if not fromkeyevent and self.IsActive() and self.IsShown():
            mousepos = self.ScreenToClient(wx.GetMousePosition())
            if header.wxrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
            elif header.negaflag:
                header.negaflag = False

        bmp = header.get_cardwxbmp()
        if header.clickedflag:
            image = bmp.ConvertToImage()
            size = image.GetSize()
            image = image.Rescale(size[0]/10*9, size[1]/10*9)
            bmp = image.ConvertToBitmap()
        self._drawlist[header] = (bmp, False)
        self.toppanel.Refresh(rect=header.wxrect)

    def set_cardpos(self, mode=-1):
        if mode == -1:
            if self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
                mode = 1
            elif self.callname == "CARDPOCKET":
                mode = 2
            elif self.callname == "HANDVIEW":
                mode = 3
            else:
                assert False, self.callname

        headers = self.get_headers()
        poslist = get_poslist(len(headers), mode)

        for pos, header in zip(poslist, headers):
            header.wxrect.topleft = pos

    def get_headers(self):
        pass

    def animate_click(self, header, func):
        # クリックアニメーション。4フレーム分。
        if self._proc:
            return
        self._proc = True

        self.set_cardpos()

        header.clickedflag = True
        self.draw_card(header, fromkeyevent=True)
        def func2():
            cw.cwpy.wait_frame(4)
            header.clickedflag = False
            self.draw_card(header, fromkeyevent=True)
            header.negaflag = False
            def func3():
                self._proc = False
                func()
            self._after_event = func3
        self._after_event = func2

    def lclick_event(self, header):
        if self._proc:
            return
        header.negaflag = False

        if header in cw.cwpy.sdata.infocards:
            dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return
        else:
            owner = header.get_owner()

        # 付帯召喚じゃない召喚獣の破棄確認
        if self.areaid in cw.AREAS_TRADE and\
                        header.type == "BeastCard" and not header.attachment:
            s = cw.cwpy.msgs["confirm_dump"] % (header.name)
            dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            self.Parent.move_dlg(dlg)

            if dlg.ShowModal() == wx.ID_OK:
                cw.cwpy.sounds["dump"].play()
                if isinstance(owner, cw.character.Character):
                    owner.throwaway_card(header)
                else:
                # デバッガから配布した召喚獣を、荷物袋から処分する場合
                    cw.cwpy.trade("TRASHBOX", header=header, from_event=True)

            dlg.Destroy()
            self.draw_cards()
            return
        elif not self.areaid in cw.AREAS_TRADE and isinstance(owner, cw.character.Character):
            if not self.check_using(owner, header):
                self.draw_cards()
                return

        if self.combo.IsShown():
            index = self.combo.GetSelection()
            if index <> self._combo_manual:
                def func(header):
                    if index == self._combo_storehouse:
                        cw.cwpy.trade("STOREHOUSE", header=header, from_event=False, parentdialog=self, sound=False)
                    elif index == self._combo_backpack:
                        cw.cwpy.trade("BACKPACK", header=header, from_event=False, parentdialog=self, sound=False)
                    elif index in self._combo_cast:
                        target = self.list2[self._combo_cast[index]]
                        cw.cwpy.trade("PLAYERCARD", header=header, target=target, from_event=False, parentdialog=self, sound=False)
                    elif index == self._combo_shelf:
                        cw.cwpy.trade("PAWNSHOP", header=header, from_event=False, parentdialog=self, sound=False)
                        cw.cwpy.draw(True)
                    elif index == self._combo_trush:
                        cw.cwpy.trade("TRASHBOX", header=header, from_event=False, parentdialog=self, sound=False)
                    def func():
                        self._proc = False
                        self.draw_cards()
                    cw.cwpy.frame.exec_func(func)
                self._proc = True
                cw.cwpy.exec_func(func, header)
                return

        # カード所持者がPlayerCardじゃない場合はカード情報を表示
        if (isinstance(self.selection, cw.character.Friend) and not cw.cwpy.is_battlestatus()) or\
                (not cw.cwpy.debug and isinstance(owner, (cw.character.Enemy, cw.character.Friend))):
            dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 開いていたダイアログの情報
        indexes = (self.index, self.index2, self.index3, self.combo.GetSelection())
        def append_predialogs(callname, indexes, pos):
            cw.cwpy.pre_dialogs.append((callname, indexes, pos, cw.UP_WIN))
        cw.cwpy.exec_func(append_predialogs, self.callname, indexes, self.GetPosition())

        # カード操作用データ(移動元データ, CardHeader)を設定
        cw.cwpy.selectedheader = header
        cw.cwpy.exec_func(cw.cwpy.update_selectablelist)
        if self.areaid in cw.AREAS_TRADE:
            def test_aptitude(header):
                # 能力適性表示
                for pcard in cw.cwpy.get_pcards("unreversed"):
                    pcard.test_aptitude = header
                    pcard.update_image()
            cw.cwpy.exec_func(test_aptitude, header)
        # OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def check_using(self, owner, header):
        # 行動不能だったら使用不可
        if owner.is_inactive():
            if cw.cwpy.setting.noticeimpossibleaction:
                s = cw.cwpy.msgs["inactive"] % owner.name
                dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                cw.cwpy.sounds["error"].play()
            return False

        # 使用回数が0以下だったら処理中止
        if header.uselimit <= 0 and not header.type == "BeastCard":
            if not header.type == "ItemCard" or not header.maxuselimit == 0:
                cw.cwpy.sounds["error"].play()
                return False

        # 戦闘中にペナルティカードを行動選択していたら処理中止
        if owner.is_autoselectedpenalty() and not cw.cwpy.debug:
            if cw.cwpy.setting.noticeimpossibleaction:
                s = cw.cwpy.msgs["selected_penalty"]
                dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                cw.cwpy.sounds["error"].play()
            return False

        return True

#-------------------------------------------------------------------------------
#　カード倉庫or荷物袋or手札カードダイアログ
#-------------------------------------------------------------------------------

class CardHolder(CardControl):
    def __init__(self, parent, callname, selection, pre_info=None, areaid=None):
        # タイプ判別
        self.callname = callname
        self.selection = None

        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        if cw.cwpy.setting.openhandviewalways or self.areaid in cw.AREAS_TRADE:
            status = "unreversed"
        else:
            status = "active"

        # 適性表示を除去
        def func():
            for pcard in cw.cwpy.get_pcards():
                if pcard.test_aptitude:
                    pcard.test_aptitude = None
                    pcard.update_image()
            cw.cwpy.draw()
        cw.cwpy.exec_func(func)

        # タイプ別初期化(キャストの手札の場合はindex復元後)
        if self.callname == "BACKPACK":
            name = cw.cwpy.msgs["cards_backpack"]
            self.list2 = cw.cwpy.get_pcards(status)
            self.bgcolour = wx.Colour(0, 0, 128)
            self.list = cw.cwpy.ydata.party.backpack
            sendto = True
        elif self.callname == "STOREHOUSE":
            name = cw.cwpy.msgs["cards_storehouse"]
            self.list2 = cw.cwpy.get_pcards(status)
            self.bgcolour = wx.Colour(0, 69, 0)
            self.list = cw.cwpy.ydata.storehouse
            sendto = True
        elif self.callname == "INFOVIEW":
            name = cw.cwpy.msgs["info_card"]
            self.bgcolour = wx.Colour(0, 0, 128)
            self.list = cw.cwpy.sdata.infocards
            sendto = False

        # 前に開いていたときのindex値と位置があったら取得する
        if pre_info:
            self.pre_pos = pre_info[2]
            indexs = pre_info[1]
            self.index2 = indexs[1]
            self.index3 = indexs[2]
            self.index_combo = indexs[3]
            if cw.UP_WIN <> pre_info[3]:
                self.pre_pos = None

            if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
                self.index = 0
                self.list2 = cw.cwpy.get_pcards(status)
                self.selection = self.index2

            else:
                self.index = indexs[0]

        else:
            self.index = 0
            self.index3 = cw.cwpy.lastcardpocket
            self.index_combo = 0
            if self.callname == "CARDPOCKET":
                self.selection = selection
                if isinstance(self.selection, cw.character.Player):
                    # パーティの手札カード(リバースメンバを除く)
                    self.list2 = cw.cwpy.get_pcards(status)
                else:
                    # NPCの手札カード
                    self.list2 = cw.cwpy.get_fcards()
                self.index2 = self.selection
            else:
                self.index2 = cw.cwpy.lastcardpocket

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            name =  cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.bgcolour = wx.Colour(0, 0, 128)
            sendto = (not cw.cwpy.is_playingscenario()\
                        or self.areaid == cw.AREA_CAMP or self.areaid in cw.AREAS_TRADE)\
                        and isinstance(self.selection, cw.character.Player)
            # self.index3(0:スキル, 1:アイテム, 2:召喚獣)。トグルボタンで切り替える
            if self.callname == "CARDPOCKET":
                self._init_cardpocketlist()
            else:
                assert self.callname == "CARDPOCKETB"
                self._set_backpacklist()

        # カード移動等でページ数が減っていた場合はself.indexを補正
        if self.callname <> "CARDPOCKET" and 0 < self.index:
            if (len(self.list)+9) / 10 <= self.index:
                self.index = (len(self.list)+9) / 10 - 1

        # 左右ボタンでの移動先の有無(情報カードは左右移動無し)
        if self.callname <> "INFOVIEW":
            # キャストの手札
            self._can_open_cardpocket = cw.cwpy.ydata.party and 0 < len(cw.cwpy.ydata.party.members)
            # 荷物袋
            self._can_open_backpack = self._can_open_cardpocket and sendto
            # カード置場
            self._can_open_storehouse = not cw.cwpy.is_playingscenario()

        # ダイアログ作成
        sort = self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB")
        CardControl.__init__(self, parent, name, sendto, sort, areaid=areaid)
        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])

        # キャストの手札カード用のコントロール
        # 情報カードダイアログの場合は切り替えが無いため不要
        if self.callname <> "INFOVIEW":
            # skill
            self.skillbtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((70, 50)))
            bmp = cw.cwpy.rsrc.buttons["SKILL"]
            self.skillbtn.SetBitmapLabel(bmp, False)
            self.skillbtn.SetBitmapSelected(bmp)
            # item
            self.itembtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((70, 50)))
            bmp = cw.cwpy.rsrc.buttons["ITEM"]
            self.itembtn.SetBitmapLabel(bmp, False)
            self.itembtn.SetBitmapSelected(bmp)
            # beast
            self.beastbtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((70, 50)))
            bmp = cw.cwpy.rsrc.buttons["BEAST"]
            self.beastbtn.SetBitmapLabel(bmp, False)
            self.beastbtn.SetBitmapSelected(bmp)
            # self.index3の値からトグルをセットする
            for index, btn in enumerate((self.skillbtn, self.itembtn, self.beastbtn)):
                if self.index3 == index:
                    btn.SetToggle(True)
                else:
                    btn.SetToggle(False)

        # カード置き場、荷物袋、情報カード用のコントロール
        # up
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_UP, cw.wins((70, 40)), bmp=bmp)
        # down
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_DOWN, cw.wins((70, 40)), bmp=bmp)

        # リストが空か1ページ分しかなかったら上下ボタンを無効化
        if len(self.list) <= 10:
            self.upbtn.Disable()
            self.downbtn.Disable()

        # 移動先選択コンボボックス(情報カードの場合は無し)
        self._combo_storehouse = -1
        self._combo_backpack = -1
        self._combo_cast = {}
        self._combo_shelf = -1
        self._combo_trush = -1
        if sendto:
            bmp = cw.cwpy.rsrc.buttons["ARROW"]
            self._combo_manual = len(self.combo.GetItems())
            self.combo.Append(cw.cwpy.msgs["send_to_manual"], bmp)
            if self._can_open_storehouse:
                bmp = cw.cwpy.rsrc.buttons["DECK"]
                self._combo_storehouse = len(self.combo.GetItems())
                self.combo.Append(cw.cwpy.msgs["send_to_storehouse"], bmp)
            if self._can_open_backpack:
                bmp = cw.cwpy.rsrc.buttons["SACK"]
                self._combo_backpack = len(self.combo.GetItems())
                self.combo.Append(cw.cwpy.msgs["send_to_backpack"], bmp)
            if self._can_open_cardpocket:
                bmp = cw.cwpy.rsrc.buttons["CAST"]
                index = 0
                for castdata in self.list2:
                    self._combo_cast[len(self.combo.GetItems())] = index
                    self.combo.Append(castdata.name, bmp)
                    index += 1
            if not cw.cwpy.is_playingscenario():
                bmp = cw.cwpy.rsrc.buttons["SHELF"]
                self._combo_shelf = len(self.combo.GetItems())
                self.combo.Append(cw.cwpy.msgs["send_to_shelf"], bmp)
            if not cw.cwpy.is_playingscenario() or cw.cwpy.is_debugmode():
                self._combo_trush = len(self.combo.GetItems())
                bmp = cw.cwpy.rsrc.buttons["TRUSH"]
                self.combo.Append(cw.cwpy.msgs["send_to_trush"], bmp)
            self.combo.Select(self.index_combo)

        # パーティが組まれていない(カード置き場のみ)か、
        # 使用モードや閲覧モードで対象が一人だけの場合は
        # 左右ボタンを無効化
        if (self.callname == "INFOVIEW")\
                or (not cw.cwpy.ydata.party)\
                or (not sendto and len(self.list2) == 1):
            self.rightbtn.Disable()
            self.leftbtn.Disable()

        if self.callname == "CARDPOCKET":
            # キャストの手札カード

            # 選択中カード色反転
            self.Parent.change_selection(self.selection)

        else:
            # カード置き場、荷物袋、情報カード

            if self.callname <> "INFOVIEW":
                # 選択中カード色反転
                self.Parent.change_selection(self.selection)

        cw.cwpy.exec_func(cw.cwpy.draw)

        # layout
        self._do_layout()
        # bind
        self._bind()

    def _bind(self):
        CardControl._bind(self)

        if self.callname <> "INFOVIEW":
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.skillbtn)
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.itembtn)
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.beastbtn)

        self.Bind(wx.EVT_BUTTON, self.OnClickUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDownBtn, self.downbtn)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def _re_layout(self):
        # レフトバー
        self._sizer_leftbar.Clear()
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            margin = cw.wins((235-150))/2
            margin2 = margin + cw.wins((235-150))%2
            self._sizer_leftbar.Add((0, margin), 0, 0, 0)
            self._sizer_leftbar.Add(self.skillbtn, 0, wx.LEFT, cw.wins(6))
            self._sizer_leftbar.Add(self.itembtn, 0, wx.LEFT, cw.wins(6))
            self._sizer_leftbar.Add(self.beastbtn, 0, wx.LEFT, cw.wins(6))
            self._sizer_leftbar.Add((0, margin2), 0, 0, 0)

            self.skillbtn.Show()
            self.itembtn.Show()
            self.beastbtn.Show()
            self.upbtn.Hide()
            self.downbtn.Hide()
        else:
            # カード置き場、荷物袋、情報カード
            self._sizer_leftbar.Add(cw.wins((0, 15)), 0, 0, 0)
            self._sizer_leftbar.Add(self.upbtn, 0, wx.LEFT, cw.wins(6))
            self._sizer_leftbar.Add(cw.wins((0, 235-110)), 0, 0, 0)
            self._sizer_leftbar.Add(self.downbtn, 0, wx.LEFT, cw.wins(6))
            self._sizer_leftbar.Add(cw.wins((0, 15)), 0, 0, 0)

            self.upbtn.Show()
            self.downbtn.Show()
            if self.callname <> "INFOVIEW":
                self.skillbtn.Hide()
                self.itembtn.Hide()
                self.beastbtn.Hide()

        # ソート条件
        if self.callname == "STOREHOUSE":
            if not self.sort.IsShown():
                self.sort.Thaw()
                self.sort.Show()
                self.sortwithstar.Thaw()
                self.sortwithstar.Show()
            self._update_sortwithstar()
            sorttype = cw.cwpy.setting.sort_storehouse
        elif self.callname in ("BACKPACK", "CARDPOCKETB"):
            if not self.sort.IsShown():
                self.sort.Thaw()
                self.sort.Show()
                self.sortwithstar.Thaw()
                self.sortwithstar.Show()
            self._update_sortwithstar()
            sorttype = cw.cwpy.setting.sort_backpack
        else:
            if self.sort.IsShown():
                self.sort.Freeze()
                self.sort.Hide()
                self.sortwithstar.Freeze()
                self.sortwithstar.Hide()
            sorttype = None

        if self.sort.IsShown():
            if sorttype == "Name":
                self.sort.Select(1)
            elif sorttype == "Level":
                self.sort.Select(2)
            elif sorttype == "Type":
                self.sort.Select(3)
            else:
                self.sort.Select(0)

        self._re_layout_topbar()

        self._sizer_topbar.Layout()
        self._sizer_leftbar.Layout()
        self.Layout()

    def _do_layout(self):
        self._sizer_leftbar = wx.BoxSizer(wx.VERTICAL)

        self._re_layout()

        CardControl._do_layout(self, self._sizer_leftbar)

    def OnDestroy(self, event):
        for header in self.list:
            header.negaflag = False
        if self.callname in ("CARDPOCKET", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
            cw.cwpy.lastcardpocket = self.index3

    def OnSort(self, event):
        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "Level"
        elif index == 3:
            sorttype = "Type"
        elif index == 4:
            sorttype = "Price"
        else:
            sorttype = "None"
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_backpack <> sorttype:
                cw.cwpy.sounds["page"].play()
                cw.cwpy.setting.sort_backpack = sorttype
                self._update_sortattr()
        elif self.callname == "STOREHOUSE":
            if cw.cwpy.setting.sort_storehouse <> sorttype:
                cw.cwpy.sounds["page"].play()
                cw.cwpy.setting.sort_storehouse = sorttype
                self._update_sortattr()

    def OnSortWithStar(self, event):
        cw.cwpy.sounds["page"].play()
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_backpackwithstar:
                cw.cwpy.setting.sort_backpackwithstar = False
                self._update_sortattr()
            else:
                cw.cwpy.setting.sort_backpackwithstar = True
                self._update_sortattr()
        elif self.callname == "STOREHOUSE":
            if cw.cwpy.setting.sort_storehousewithstar:
                cw.cwpy.setting.sort_storehousewithstar = False
                self._update_sortattr()
            else:
                cw.cwpy.setting.sort_storehousewithstar = True
                self._update_sortattr()

        self._update_sortwithstar()

    def _update_sortwithstar(self):
        bmp = self.star
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            if not cw.cwpy.setting.sort_backpackwithstar:
                bmp = self.nostar
        elif self.callname == "STOREHOUSE":
            if not cw.cwpy.setting.sort_storehousewithstar:
                bmp = self.nostar
        else:
            return
        self.sortwithstar.SetBitmapFocus(bmp)
        self.sortwithstar.SetBitmapHover(bmp)
        self.sortwithstar.SetBitmapLabel(bmp)
        self.sortwithstar.SetBitmapSelected(bmp)

    def _update_sortattr(self):
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            cw.cwpy.ydata.party.sort_backpack()
            if self.callname == "CARDPOCKETB":
                self._set_backpacklist()
            self.draw_cards()
        elif self.callname == "STOREHOUSE":
            cw.cwpy.ydata.sort_storehouse()
            self.draw_cards()

    def OnClickLeftBtn(self, event):
        cw.cwpy.sounds["page"].play()
        old_callname = self.callname

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            if self.index2 is self.list2[0]:
                if self._can_open_backpack:
                    # 荷物袋 ← 左端
                    self.index = 0
                    self.callname = "BACKPACK"
                    self._change_callname(old_callname)
                else:
                    # 右端 ← 左端
                    self.index = 0
                    self.callname = "CARDPOCKET"
                    self.index2 = self.list2[-1]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
                    if self.callname <> old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ左のメンバ
                self.index = 0
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) - 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname <> old_callname:
                    self._change_callname(old_callname)
        else:
            self.index = 0
            if self.callname == "BACKPACK" and self._can_open_storehouse:
                # カード置き場 ← 荷物袋
                self.callname = "STOREHOUSE"
                self._change_callname(old_callname)
            else:
                # パーティの手札 ← カード置き場
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[-1]
                self.selection = self.index2
                self._change_callname(old_callname)

        self.draw_cards()

    def OnClickRightBtn(self, event):
        cw.cwpy.sounds["page"].play()
        old_callname = self.callname

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            if self.index2 is self.list2[-1]:
                if self._can_open_storehouse:
                    # 右端 → カード置き場
                    self.index = 0
                    self.callname = "STOREHOUSE"
                    self._change_callname(old_callname)
                elif self._can_open_backpack:
                    # 右端 → 荷物袋
                    self.index = 0
                    self.callname = "BACKPACK"
                    self._change_callname(old_callname)
                else:
                    # 右端 → 左端
                    self.index = 0
                    self.callname = "CARDPOCKET"
                    self.index2 = self.list2[0]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
                    if self.callname <> old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ右のメンバ
                self.index = 0
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) + 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname <> old_callname:
                    self._change_callname(old_callname)
        else:
            self.index = 0
            if self.callname == "STOREHOUSE":
                # カード置き場 → 荷物袋
                self.callname = "BACKPACK"
                self._change_callname(old_callname)
            else:
                # 荷物袋 → パーティの手札
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[0]
                self.selection = self.index2
                self._change_callname(old_callname)

        self.draw_cards()

    def OnCancel(self, event):
        if self.callname == "CARDPOCKETB":
            cw.cwpy.sounds["page"].play()
            old_callname = self.callname
            self.index = 0
            self.callname = "CARDPOCKET"
            self._change_callname(old_callname)
            self.draw_cards()
        else:
            CardControl.OnCancel(self, event)

    def _change_callname(self, old_callname):
        if self.callname == "CARDPOCKET":
            self.bgcolour = wx.Colour(0, 0, 128)
            self.toppanel.SetBackgroundColour(self.bgcolour)
        elif self.callname == "CARDPOCKETB":
            self.bgcolour = wx.Colour(0, 0, 128)
            self.toppanel.SetBackgroundColour(self.bgcolour)
            self._set_backpacklist()
        else:
            if self.callname == "BACKPACK":
                self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], cw.cwpy.msgs["cards_backpack"]))
                self.bgcolour = wx.Colour(0, 0, 128)
                self.toppanel.SetBackgroundColour(self.bgcolour)
                self.list = cw.cwpy.ydata.party.backpack
            elif self.callname == "STOREHOUSE":
                self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], cw.cwpy.msgs["cards_storehouse"]))
                self.bgcolour = wx.Colour(0, 69, 0)
                self.toppanel.SetBackgroundColour(self.bgcolour)
                self.list = cw.cwpy.ydata.storehouse
            self.selection = None

        self.Parent.change_selection(self.selection)
        if self.callname <> old_callname:
            self._re_layout()

        if self.callname == "CARDPOCKET" or len(self.list) <= 10:
            self.upbtn.Disable()
            self.downbtn.Disable()
        else:
            self.upbtn.Enable()
            self.downbtn.Enable()
        self.Layout()

        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])
        else:
            self.closebtn.SetLabel(cw.cwpy.msgs["close"])

    def _set_backpacklist(self):
        if self.index3 == cw.POCKET_SKILL:
            type = "SkillCard"
        elif self.index3 == cw.POCKET_ITEM:
            type = "ItemCard"
        else:
            assert self.index3 == cw.POCKET_BEAST
            type = "BeastCard"
        self.list = filter(lambda header: header.type == type, cw.cwpy.ydata.party.backpack)

    def lclick_event(self, header):
        header.negaflag = False
        owner = self.selection
        if self.callname == "CARDPOCKETB":
            if not self.check_using(owner, header):
                self.draw_cards()
                return

            # 一時的に取り出す
            cw.cwpy.card_takenouttemporarily = header
            cw.cwpy.trade("PLAYERCARD", header=header, target=owner, from_event=False, parentdialog=self, sound=False, call_predlg=False)
            CardControl.lclick_event(self, header)

        elif header.type == "UseCardInBackpack":
            if owner.is_inactive():
                if cw.cwpy.setting.noticeimpossibleaction:
                    s = cw.cwpy.msgs["inactive"] % owner.name
                    dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                    self.Parent.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()
                else:
                    cw.cwpy.sounds["error"].play()
                self.draw_cards()
                return
            old_callname = self.callname
            self.index = 0
            self.callname = "CARDPOCKETB"
            self._change_callname(old_callname)
            self.draw_cards()

        else:
            CardControl.lclick_event(self, header)

    def OnClickToggleBtn(self, event):
        cw.cwpy.sounds["click"].play()

        l = [self.skillbtn, self.itembtn, self.beastbtn]

        for index, btn in enumerate(l):
            if btn == event.GetEventObject():
                self.index3 = index
                btn.SetToggle(True)
            else:
                btn.SetToggle(False)

        self.draw_cards()

    def OnUp(self, event):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 特殊技能、アイテム、召喚獣を切り替え
            l = [self.skillbtn, self.itembtn, self.beastbtn]
            btn = l[self.index3 - 1] if not self.index3 == 0 else l[len(l) -1]
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
            btnevent.SetEventObject(btn)
            self.ProcessEvent(btnevent)
        elif self.upbtn.IsShown() and self.upbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.upbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnDown(self, event):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 特殊技能、アイテム、召喚獣を切り替え
            l = [self.skillbtn, self.itembtn, self.beastbtn]
            btn = l[self.index3 + 1] if not self.index3 == len(l) -1 else l[0]
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
            btnevent.SetEventObject(btn)
            self.ProcessEvent(btnevent)
        elif self.upbtn.IsShown() and self.downbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.downbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnClickUpBtn(self, event):
        cw.cwpy.sounds["click"].play()
        negaindex = -1

        for index, header in enumerate(self.get_headers()):
            if header.negaflag:
                header.negaflag = False
                negaindex = index

        n = (len(self.list)+9)/10 if len(self.list) > 0 else 1

        if self.index == 0:
            self.index = n - 1
        else:
            self.index -= 1

        if not negaindex == -1:
            for index, header in enumerate(self.get_headers()):
                if index == negaindex:
                    header.negaflag = True

        self.draw_cards()

    def OnClickDownBtn(self, event):
        cw.cwpy.sounds["click"].play()
        negaindex = -1

        for index, header in enumerate(self.get_headers()):
            if header.negaflag:
                header.negaflag = False
                negaindex = index

        n = (len(self.list)+9)/10 if len(self.list) > 0 else 1

        if self.index == n - 1:
            self.index = 0
        else:
            self.index += 1

        if not negaindex == -1:
            for index, header in enumerate(self.get_headers()):
                if index == negaindex:
                    header.negaflag = True

        self.draw_cards()

    def OnMouseWheel(self, event):
        mousepos = event.GetPosition()
        lpos = self._sizer_leftbar.GetPosition()
        lsize = self._sizer_leftbar.GetSize()
        lwidth = lsize[0] + lpos[0] * 2;
        if self.sort.IsShown() and self.sort.GetRect().Contains(mousepos):
            index = self.sort.GetSelection()
            count = self.sort.GetCount()
            if event.GetWheelRotation() > 0:
                if index <= 0:
                    index = count - 1
                else:
                    index -= 1
            else:
                if count <= index + 1:
                    index = 0
                else:
                    index += 1
            self.sort.Select(index)
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.sort.GetId())
            self.ProcessEvent(btnevent)
            return
        elif self.combo.IsShown() and self.combo.GetRect().Contains(mousepos):
            if event.GetWheelRotation() > 0:
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn2.GetId())
                self.ProcessEvent(btnevent)
            else:
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn2.GetId())
                self.ProcessEvent(btnevent)
            return
        elif mousepos[0] < lwidth or self.callname == "INFOVIEW":
            if self.callname == "CARDPOCKET":
                # キャストの手札カード
                # 特殊技能、アイテム、召喚獣を切り替え
                l = [self.skillbtn, self.itembtn, self.beastbtn]
                if event.GetWheelRotation() > 0:
                    btn = l[self.index3 - 1] if not self.index3 == 0 else l[len(l) -1]
                else:
                    btn = l[self.index3 + 1] if not self.index3 == len(l) -1 else l[0]
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
                btnevent.SetEventObject(btn)
                self.ProcessEvent(btnevent)
                return
            else:
                # カード置き場、荷物袋、情報カード
                # ページを切り替え
                if self.list and len(self.list) > 10:
                    if event.GetWheelRotation() > 0:
                        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
                    else:
                        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
                    self.ProcessEvent(btnevent)
                    return

        CardControl.OnMouseWheel(self, event)

    def draw_cards(self, update=True, mode=-1):
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            if (len(self.list)+9) / 10 <= self.index:
                self.index = (len(self.list)+9) / 10 - 1
        if self.selection:
            self._init_cardpocketlist()
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))

        if self.callname == "CARDPOCKET":
            self._leftmark = None
        else:
            # カード置場・荷物袋・情報カードマーク
            if self.callname == "BACKPACK":
                path = "Resource/Image/Card/COMMAND7" + cw.cwpy.rsrc.ext_img
            elif self.callname == "STOREHOUSE":
                path = "Resource/Image/Card/COMMAND5" + cw.cwpy.rsrc.ext_img
            elif self.callname == "INFOVIEW":
                path = "Resource/Image/Card/COMMAND8" + cw.cwpy.rsrc.ext_img
            elif self.callname == "CARDPOCKETB":
                path = cw.cwpy.rsrc.backpackcards["ItemCard"].imgpath
            path = cw.util.join_paths(cw.cwpy.skindir, path)
            self._leftmark = cw.wins((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))

        CardControl.draw_cards(self, update, mode)

    def _init_cardpocketlist(self):
        if self.callname <> "CARDPOCKET":
            return

        self.list = self.selection.cardpocket[self.index3][:]
        if cw.cwpy.setting.show_backpackcard and self.index3 <> cw.POCKET_SKILL and self.get_mode() == CCMODE_USE:
            space = self.selection.get_cardpocketspace()[self.index3]
            if len(self.list) < space:
                type = ""
                if self.index3 == cw.POCKET_ITEM:
                    type = "ItemCard"
                elif self.index3 == cw.POCKET_BEAST:
                    type = "BeastCard"
                if type:
                    for header in cw.cwpy.ydata.party.backpack:
                        # 荷物袋に存在する場合のみ選択肢「荷物袋」を表示
                        if header.type == type:
                            self.list.insert(0, cw.cwpy.rsrc.backpackcards[type])
                            break

    def get_headers(self):
        li = self.index * 10
        list = self.list[li:li + 10]
        return list

#-------------------------------------------------------------------------------
#　戦闘手札カードダイアログ
#-------------------------------------------------------------------------------

class HandView(CardControl):
    def __init__(self, parent, selection, pre_info=None):
        self.callname = "HANDVIEW"
        self.owner = selection

        # カードリスト
        if cw.cwpy.setting.openhandviewalways:
            status = "unreversed"
        else:
            status = "active"
        if isinstance(selection, cw.character.Player):
            self.list2 = cw.cwpy.get_pcards(status)
        elif isinstance(selection, cw.character.Friend):
            self.list2 = cw.cwpy.get_fcards(status)
        else: # EnemyCard
            if cw.cwpy.is_debugmode():
                self.list2 = cw.cwpy.get_ecards(status)
            else:
                self.list2 = []
                for card in cw.cwpy.get_ecards(status):
                    if card.is_analyzable():
                        self.list2.append(card)

        if status == "active" and not cw.cwpy.debug and isinstance(self.owner, cw.sprite.card.PlayerCard):
            self.list2 = filter(lambda pcard: not pcard.is_autoselectedpenalty(), self.list2)

        # 前に開いていたときのindex値があったら取得する
        if pre_info:
            self.pre_pos = pre_info[2]
            indexs = pre_info[1]
            self.index = indexs[0]
            self.index2 = indexs[1]
            self.index3 = indexs[2]
            self.index_combo = indexs[3]
            if cw.UP_WIN <> pre_info[3]:
                self.pre_pos = None
            self.selection = self.index2
        else:
            self.selection = selection
            self.index = 0
            self.index2 = self.selection
            self.index3 = 0
            self.index_combo = 0

        # 手札リスト
        self.list = self.selection.deck.hand
        for header in self.list:
            header.negaflag = False
        # ダイアログ作成
        name = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
        self.bgcolour = wx.Colour(0, 0, 128)
        CardControl.__init__(self, parent, name, False, False)
        # 選択中カード色反転
        self.Parent.change_selection(self.selection)

        # 使用モードでパーティが一人だけの場合は左右ボタンを無効化
        if len(self.list2) == 1:
            self.rightbtn.Disable()
            self.leftbtn.Disable()

        # layout
        self._do_layout()
        # bind
        self._bind()

    def _bind(self):
        CardControl._bind(self)

    def OnClickLeftBtn(self, event):
        cw.cwpy.sounds["page"].play()

        if self.index2 == self.list2[0]:
            self.index2 = self.list2[-1]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) - 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def OnClickRightBtn(self, event):
        cw.cwpy.sounds["page"].play()

        if self.index2 == self.list2[-1]:
            self.index2 = self.list2[0]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) + 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def draw_cards(self, update=True, mode=-1):
        if self.selection:
            self.list = self.selection.deck.hand
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))
        CardControl.draw_cards(self, update, mode)

    def get_headers(self):
        return self.list

    def _do_layout(self):
        sizer_leftbar = wx.BoxSizer(wx.VERTICAL)
        CardControl._do_layout(self, sizer_leftbar)

#-------------------------------------------------------------------------------
#　情報カードダイアログ
#-------------------------------------------------------------------------------

class InfoView(CardHolder):
    def __init__(self, parent):
        # ダイアログ作成
        CardHolder.__init__(self, parent, "INFOVIEW", None)
        def func():
            if cw.cwpy.sdata.notice_infoview:
                cw.cwpy.sdata.notice_infoview = False
                cw.cwpy.statusbar.change()
                cw.cwpy.draw()
        cw.cwpy.exec_func(func)

    def OnLeftUp(self, event):
        self.OnRightUp(event)

def get_poslist(num, mode=1):
    """
    カード描画に使うpositionのリストを返す。
    mode=1は荷物袋・カード置場用。
    mode=2は所持カード用。
    mode=3は戦闘カード用。
    """
    if mode == 1:
        # 描画エリアサイズ
        w, h = cw.wins((425, 230))
        # 左,上の余白
        leftm = cw.wins(80)

        poslist = []

        for cnt in xrange(num):
            if cnt < 5:
                poslist.append((leftm+cw.wins(84)*cnt, cw.wins(25)))
            else:
                poslist.append((leftm+cw.wins(84)*(cnt-5), cw.wins(140)))

    elif mode == 2:
        # 描画エリアサイズ
        w, h = cw.wins((425, 230))
        # 左,上の余白
        leftm = cw.wins(80)

        if num < 5:
            x = (w - cw.wins(83) * num) / 2 + leftm
            y = cw.wins(77)
            poslist = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(num)]
        else:
            row1, row2 = num / 2 + num % 2, num / 2
            x = (w - cw.wins(83) * row1) / 2 + leftm
            y = cw.wins(27)
            row1list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row1)]
            x = (w - cw.wins(83) * row2) / 2 + leftm
            y = cw.wins(141)
            row2list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row2)]
            poslist = row1list + row2list

    elif mode == 3:
        # 描画エリアサイズ
        w, h = cw.wins((505, 230))

        if num < 6:
            x = (w - cw.wins(83) * num) / 2
            y = cw.wins(77)
            poslist = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(num)]
        else:
            row1, row2 = num / 2 + num % 2, num / 2
            x = (w - cw.wins(83) * row1) / 2
            y = cw.wins(27)
            row1list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row1)]
            x = (w - cw.wins(83) * row2) / 2
            y = cw.wins(141)
            row2list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row2)]
            poslist = row1list + row2list

    return poslist

def main():
    pass

if __name__ == "__main__":
    main()
