#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import os
import sys
import wx
import wx.combo
import wx.lib.buttons
import wx.lib.intctrl

import cw
import cardinfo
import message

# カード操作ダイアログのモード
CCMODE_SHOW    = 0 # 閲覧モード
CCMODE_MOVE    = 1 # 移動モード
CCMODE_BATTLE  = 2 # 戦闘行動選択モード
CCMODE_USE     = 3 # 使用モード
CCMODE_REPLACE = 4 # 交換モード

#-------------------------------------------------------------------------------
# カード操作ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CardControl(wx.Dialog):
    def __init__(self, parent, name, sendto, sort, areaid=None, drawcards=True):
        # ダイアログ作成
        wx.Dialog.__init__(self, parent, -1, "%s - %s" % (cw.cwpy.msgs["card_control"], name),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        self.SetDoubleBuffered(True)
        self.additionals = []
        self.change_bgs = []
        self._redraw = True

        self._quit = False

        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        if self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
            s = cw.cwpy.msgs["entry_cancel"]
        else:
            s = cw.cwpy.msgs["close"]
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((90, 24)), s)
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp, chain=True)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((30, 30)), bmp=bmp, chain=True)
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((520, 285)))
        self.toppanel.SetMinSize(cw.wins((520, 285)))
        self.toppanel.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.toppanel.SetDoubleBuffered(True)
        self.change_bgs.append(self.toppanel)

        self._sizer_topbar = wx.BoxSizer(wx.HORIZONTAL)

        # sort
        self.star = cw.cwpy.rsrc.dialogs["BOOKMARK"]
        self.nostar = cw.cwpy.rsrc.dialogs["BOOKMARK_EMPTY"]
        self.starlight = cw.cwpy.rsrc.dialogs["BOOKMARK_LIGHTUP"]
        self._laststar = None

        choices = [cw.cwpy.msgs["sort_no"],
                   cw.cwpy.msgs["sort_name"],
                   cw.cwpy.msgs["sort_level"],
                   cw.cwpy.msgs["sort_type"],
                   cw.cwpy.msgs["sort_price"],
                   cw.cwpy.msgs["scenario_name"],
                   cw.cwpy.msgs["author"]]
        self.sort = wx.ComboBox(self.toppanel, -1, size=cw.wins((75, 24)), choices=choices, style=wx.CB_READONLY)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        self.sortwithstar = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
        self.sortwithstar.SetToolTipString(cw.cwpy.msgs["sort_with_star"])
        self._update_sortwithstar()
        self.editstar = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
        self.editstar.SetToolTipString(cw.cwpy.msgs["edit_star"])
        self.editstar.SetToggle(cw.cwpy.setting.edit_star)
        self._update_editstar()
        if not sort or not cw.cwpy.setting.show_additional_card:
            self.sort.Hide()
            self.sortwithstar.Hide()
        if not sort:
            self.editstar.Hide()
        def can_sort():
            return self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB")
        self.additionals.append((self.sort, can_sort))
        self.additionals.append((self.sortwithstar, can_sort))
        self.change_bgs.append(self.sortwithstar)
        self.change_bgs.append(self.editstar)

        self.show = [None] * 3
        self._typeicon_e = [None] * 3
        self._typeicon_d = [None] * 3
        show = (cw.cwpy.msgs["show_object"])
        for cardtype, bmp, msg in ((cw.POCKET_SKILL, cw.cwpy.rsrc.dialogs["STATUS8"], (show % cw.cwpy.msgs["skillcard"])),
                                   (cw.POCKET_ITEM, cw.cwpy.rsrc.dialogs["STATUS9"], (show % cw.cwpy.msgs["itemcard"])),
                                   (cw.POCKET_BEAST, cw.cwpy.rsrc.dialogs["STATUS10"], (show % cw.cwpy.msgs["beastcard"]))):
            btn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
            self._typeicon_e[cardtype] = bmp
            dbmp = cw.imageretouch.to_disabledimage(bmp, maskpos=(bmp.GetWidth()-1, 0))
            self._typeicon_d[cardtype] = dbmp
            if cw.cwpy.setting.show_cardtype[cardtype]:
                btn.SetToggle(True)
            else:
                bmp = dbmp
                btn.SetToggle(False)
            btn.SetBitmapFocus(bmp)
            btn.SetBitmapLabel(bmp, False)
            btn.SetBitmapSelected(bmp)
            btn.SetToolTipString(msg)
            self.show[cardtype] = btn
            if not self.callname in ("BACKPACK", "STOREHOUSE") or\
                    not cw.cwpy.setting.show_additional_card:
                btn.Hide()
            self.additionals.append((btn, lambda: self.callname in ("BACKPACK", "STOREHOUSE")))
            self.change_bgs.append(btn)

        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 24)), bmp=bmp, chain=True)
        # sendto
        self.combo = wx.combo.BitmapComboBox(self.toppanel, size=cw.wins((100, 24)), style=wx.CB_READONLY)
        self.combo.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 24)), bmp=bmp, chain=True)
        if not sendto:
            self.leftbtn2.Hide()
            self.rightbtn2.Hide()
            self.combo.Hide()

        # 追加的コントロールの表示切替
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET", "CARDPOCKETB", "INFOVIEW"):
            self.addctrlbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
            self.addctrlbtn.SetToolTipString(cw.cwpy.msgs["show_additional_controls"])
            self.addctrlbtn.SetToggle(cw.cwpy.setting.show_additional_card)
            self.change_bgs.append(self.addctrlbtn)
            if not cw.cwpy.setting.show_addctrlbtn:
                self.addctrlbtn.Hide()
        else:
            self.addctrlbtn = None

        # 絞込条件
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15))
        self.narrow = wx.TextCtrl(self.toppanel, -1, size=cw.wins((100, 20)))
        self.narrow.SetValue(cw.cwpy.setting.card_narrow)
        self.narrow.SetFont(font)
        if self.callname == "INFOVIEW":
            choices = (cw.cwpy.msgs["all"],
                       cw.cwpy.msgs["card_name"],
                       cw.cwpy.msgs["description"])
        elif cw.cwpy.is_debugmode():
            choices = (cw.cwpy.msgs["all"],
                       cw.cwpy.msgs["card_name"],
                       cw.cwpy.msgs["description"],
                       cw.cwpy.msgs["scenario_name"],
                       cw.cwpy.msgs["author"],
                       cw.cwpy.msgs["key_code"])
        else:
            choices = (cw.cwpy.msgs["all"],
                       cw.cwpy.msgs["card_name"],
                       cw.cwpy.msgs["description"],
                       cw.cwpy.msgs["scenario_name"],
                       cw.cwpy.msgs["author"])
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.narrow_type = wx.ComboBox(self.toppanel, -1, size=cw.wins((90, 20)), choices=choices, style=wx.CB_READONLY)
        self.narrow_type.SetFont(font)
        if self.callname == "INFOVIEW":
            narrow_sel = cw.cwpy.setting.infoview_narrowtype
        else:
            narrow_sel = cw.cwpy.setting.card_narrowtype
        if narrow_sel < self.narrow_type.GetCount():
            self.narrow_type.SetSelection(narrow_sel)
        else:
            self.narrow_type.SetSelection(1)

        def can_narrow():
            return self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW")

        if not can_narrow() or not cw.cwpy.setting.show_additional_card:
            self.narrow.Hide()
            self.narrow_type.Hide()

        self.additionals.append((self.narrow, can_narrow))
        self.additionals.append((self.narrow_type, can_narrow))

        self._drawlist = {}
        self._leftmarks = []
        self._after_event = None
        self._starclickedflag = False

        self.smallctrls = []

        self._proc = False

        self.toppanel.SetFocusIgnoringChildren()

        if self.addctrlbtn:
            self.update_additionals()

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

        if drawcards:
            self.draw_cards()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn2, self.leftbtn2)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn2, self.rightbtn2)
        self.Bind(wx.EVT_BUTTON, self.OnSortWithStar, self.sortwithstar)
        self.Bind(wx.EVT_BUTTON, self.OnEditStar, self.editstar)
        self.Bind(wx.EVT_BUTTON, self.OnShowSkill, self.show[cw.POCKET_SKILL])
        self.Bind(wx.EVT_BUTTON, self.OnShowItem, self.show[cw.POCKET_ITEM])
        self.Bind(wx.EVT_BUTTON, self.OnShowBeast, self.show[cw.POCKET_BEAST])
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_COMBOBOX, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMove)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.toppanel.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.toppanel.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint2)
        self.panel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp2)
        for child in itertools.chain(self.toppanel.GetChildren(), self.panel.GetChildren()):
            child.Bind(wx.EVT_RIGHT_UP, self.OnRightUp2)
        self.narrow.Bind(wx.EVT_TEXT, self.OnNarrowCondition)
        self.narrow_type.Bind(wx.EVT_COMBOBOX, self.OnNarrowCondition)
        self.combo.Bind(wx.EVT_COMBOBOX, self.OnSendTo)
        if self.addctrlbtn:
            self.Bind(wx.EVT_BUTTON, self.OnAdditionalControls, self.addctrlbtn)

        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=wx.ID_CANCEL)

        self.leftkeyid = wx.NewId()
        self.rightkeyid = wx.NewId()
        self.upid = wx.NewId()
        self.downid = wx.NewId()
        self.returnkeyid = wx.NewId()
        self.leftpagekeyid = wx.NewId()
        self.rightpagekeyid = wx.NewId()
        self.uptargkeyid = wx.NewId()
        self.downtargkeyid = wx.NewId()
        self.infokeyid = wx.NewId()
        addctrl = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.rightkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.returnkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.infokeyid)
        self.Bind(wx.EVT_MENU, self.OnUp, id=self.upid)
        self.Bind(wx.EVT_MENU, self.OnDown, id=self.downid)
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn2, id=self.uptargkeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn2, id=self.downtargkeyid)
        if self.addctrlbtn:
            self.Bind(wx.EVT_MENU, self.OnToggleAdditionalControls, id=addctrl)
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
            (wx.ACCEL_CTRL, wx.WXK_RETURN, self.infokeyid),
        ]
        if self.addctrlbtn:
            seq.append((wx.ACCEL_CTRL, ord('F'), addctrl))
        self.narrowkeydown = []
        self.sortkeydown = []
        for i in xrange(0, 9):
            narrowkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=narrowkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, narrowkeydown))
            self.narrowkeydown.append(narrowkeydown)
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_ALT, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)
        cw.util.set_acceleratortable(self, seq)

    def OnNumberKeyDown(self, event):
        """
        数値キー'1'～'9'までの押下を処理する。
        CardControlではソート条件の変更を行う。
        """
        eid = event.GetId()
        if eid in self.narrowkeydown and self.narrow_type.IsShown():
            index = self.narrowkeydown.index(eid)
            if index < self.narrow_type.GetCount():
                self.narrow_type.SetSelection(index)
                self.OnNarrowCondition(event)
        if eid in self.sortkeydown and self.sort.IsShown():
            index = self.sortkeydown.index(eid)
            if index < self.sort.GetCount():
                self.sort.SetSelection(index)
                event = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.sort.GetId())
                self.ProcessEvent(event)

    def _do_layout(self):
        """
        引数に子クラスで設定したsizer_leftbarが必要
        """
        cwidth = cw.wins(520)
        cheight = cw.wins(285)

        # 表示有無を切り替えた時に多少綺麗に再配置されるように、
        # 非表示のコントロールは画面外へ出しておく
        for ctrl in self.toppanel.GetChildren():
            if not ctrl.IsShown():
                ctrl.SetPosition((cwidth, cw.wins(0)))

        # toppanelはSizerを使わず自前で座標を計算
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            x = cw.wins(10)
            y = cw.wins(64)
            self.skillbtn.SetPosition((x, y))
            y += self.skillbtn.GetSize()[1]
            self.itembtn.SetPosition((x, y))
            y += self.itembtn.GetSize()[1]
            self.beastbtn.SetPosition((x, y))
        elif not self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
            # カード置き場、荷物袋、情報カード
            x = cw.wins(10)
            if cw.cwpy.setting.show_addctrlbtn:
                y = cw.wins(40)
            else:
                y = cw.wins(50)
            self.upbtn.SetPosition((x, y))
            self.upbtn.SetSize(cw.wins((70, 40)))
            y += self.upbtn.GetSize()[1]
            y += cw.wins(240-110)
            self.downbtn.SetPosition((x, y))
            self.downbtn.SetSize(cw.wins((70, 40)))

            # ページ番号入力欄
            psize = (cw.wins(34), self.page.GetSize()[1])
            dc = wx.ClientDC(self)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(14)))
            rect = self.upbtn.GetRect()
            top = rect[1] + rect[3]
            btm = self.downbtn.GetPosition()[1]
            h = dc.GetTextExtent("#")[1] + cw.wins(1) + cw.wins(cw.SIZE_CARDIMAGE[1])
            y = top + (btm-top-h)/2
            y += cw.wins(cw.SIZE_CARDIMAGE[1])+cw.wins(1)
            te = dc.GetTextExtent("/")
            sx = cw.wins(40)-te[0]/2+cw.wins(7)
            y += te[1] / 2
            y -= psize[1]/2
            self.page.SetPosition((sx-psize[0], y))
            self.page.SetSize(psize)

        # 絞込条件
        if self.narrow.IsShown():
            y = cheight - cw.wins(5)
            y -= cw.wins(20)
            x = cwidth - cw.wins(5)
            x -= cw.wins(90)
            self.narrow_type.SetSize(cw.wins((90, 20)))
            yc = y + (cw.wins(20)-self.narrow_type.GetSize()[1]) / 2
            self.narrow_type.SetPosition((x, yc))
            x -= cw.wins(100)
            x -= cw.wins(2)
            self.narrow.SetPosition((x, y))
            self.narrow.SetSize(cw.wins((100, 20)))

        # 移動先
        x = cwidth - cw.wins(5)
        y = cw.wins(0)
        if self.combo.IsShown():
            x -= cw.wins(20)
            self.rightbtn2.SetPosition((x, y))
            self.rightbtn2.SetSize(cw.wins((20, 24)))
            x -= cw.wins(100)
            self.combo.SetSize((cw.wins(100), cw.wins(24)))
            if sys.platform == "win32":
                import win32api
                CB_SETITEMHEIGHT = 0x153
                win32api.SendMessage(self.combo.Handle, CB_SETITEMHEIGHT, -1, cw.wins(24))
            yc = y + (cw.wins(24)-self.combo.GetSize()[1]) / 2
            self.combo.SetPosition((x, yc))

            x -= cw.wins(20)
            self.leftbtn2.SetPosition((x, y))
            self.leftbtn2.SetSize(cw.wins((20, 24)))
            x -= cw.wins(50)

        if self.callname in ("BACKPACK", "STOREHOUSE"):
            for cardtype in (cw.POCKET_BEAST, cw.POCKET_ITEM, cw.POCKET_SKILL):
                shown = False
                btn = self.show[cardtype]
                if not btn.IsShown():
                    continue
                shown = True
                x -= cw.wins(24)
                btn.SetPosition((x, y))
                btn.SetSize(cw.wins((24, 24)))
            if shown:
                x -= cw.wins(5)

        if self.editstar.IsShown():
            x -= cw.wins(24)
            self.editstar.SetPosition((x, y))
            self.editstar.SetSize(cw.wins((24, 24)))
        if self.sort.IsShown():
            x -= cw.wins(24)
            self.sortwithstar.SetPosition((x, y))
            self.sortwithstar.SetSize(cw.wins((24, 24)))
            x -= cw.wins(77)
            self.sort.SetSize(cw.wins((75, 24)))
            yc = y + (cw.wins(24)-self.sort.GetSize()[1]) / 2
            self.sort.SetPosition((x, yc))

        # 追加的コントロールの表示
        if self.addctrlbtn:
            w, h = self.addctrlbtn.GetSize()
            self.addctrlbtn.SetPosition((cw.wins(2), cheight-h-cw.wins(2)))

        # ボタンバー
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)
        # トップパネルとボタンバーのサイザーを設定
        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def update_additionals(self):
        """表示状態の切り替え時に呼び出される。"""
        show = self.addctrlbtn.GetToggle()
        for ctrl, is_shown in self.additionals:
            ctrl.Show(show and is_shown())
        if show:
            bmp = cw.cwpy.rsrc.dialogs["HIDE_CONTROLS"]
        else:
            bmp = cw.cwpy.rsrc.dialogs["SHOW_CONTROLS"]
        self.addctrlbtn.SetBitmapFocus(bmp)
        self.addctrlbtn.SetBitmapLabel(bmp)
        self.addctrlbtn.SetBitmapSelected(bmp)
        cw.cwpy.setting.show_additional_card = show
        self.set_cardpos()

    def OnToggleAdditionalControls(self, event):
        if not self.addctrlbtn or not self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            return
        self.addctrlbtn.SetToggle(not self.addctrlbtn.GetToggle())
        self._additional_controls()

    def OnAdditionalControls(self, event):
        self._additional_controls()

    def _additional_controls(self):
        cw.cwpy.play_sound("equipment")
        self.Freeze()
        self._redraw = False
        self.update_additionals()
        # GTKで表示・非表示状態の反映が遅延する事があるので、
        # 再レイアウト以降の処理を遅延実行する
        def func():
            self._do_layout()
            self._redraw = True
            self.update_narrowcondition()
            self.Thaw()
        cw.cwpy.frame.exec_func(func)

    def OnNarrowCondition(self, event):
        cw.cwpy.play_sound("page")
        # 日本語入力で一度に何度もイベントが発生する
        # 事があるので絞り込み実施を遅延する
        self.narrow.SetFocus()
        self._reserved_narrowconditin = True
        def func():
            if not self._reserved_narrowconditin:
                return
            self._reserved_narrowconditin = False
            cw.cwpy.setting.card_narrow = self.narrow.GetValue()
            cw.cwpy.setting.card_narrowtype = self.narrow_type.GetSelection()
            self.update_narrowcondition()
            self.narrow.SetFocus()
        wx.CallAfter(func)

    def OnSendTo(self, event):
        cw.cwpy.play_sound("page")
        cw.cwpy.setting.last_sendto = self.combo.GetSelection()
        self.toppanel.SetFocusIgnoringChildren()
        self.draw_cards()

    def update_narrowcondition(self):
        self.draw_cards()

    def OnSort(self, event):
        pass

    def OnSortWithStar(self, event):
        pass

    def OnEditStar(self, event):
        cw.cwpy.play_sound("page")
        self._update_editstar()
        self._on_move(mousepos=wx.GetMousePosition())
        self.Refresh()

    def OnShowSkill(self, event):
        pass

    def OnShowItem(self, event):
        pass

    def OnShowBeast(self, event):
        pass

    def _update_sortwithstar(self):
        pass

    def _update_editstar(self):
        pass

    def OnUp(self, event):
        pass

    def OnDown(self, event):
        pass

    def OnKeyDown(self, event):
        if self._proc:
            return

        eid = event.GetId()

        seq = None
        if eid == self.returnkeyid:
            for header in self.get_headers():
                if header.negaflag:
                    cw.cwpy.play_sound("click")
                    def func():
                        self.lclick_event(header)
                    self.animate_click(header, func)
                    return
        elif eid == self.infokeyid:
            for header in self.get_headers():
                if header.negaflag:
                    cw.cwpy.play_sound("click")
                    def func():
                        self.rclick_event(header)
                    self.animate_click(header, func)
                    return
        elif eid == self.leftkeyid:
            seq = self.get_headers()[:]
            seq.reverse()
        elif eid == self.rightkeyid:
            seq = self.get_headers()

        if not seq:
            return
        c1 = None
        c2 = seq[0]
        for i, header in enumerate(seq):
            if header.negaflag:
                if i == len(seq)-1:
                    c1 = header
                    c2 = seq[0]
                    break
                else:
                    c1 = header
                    c2 = seq[i+1]
                    break

        self.set_cardpos()

        if c1:
            c1.negaflag = False
            self.draw_card(c1, True)
        if c2:
            c2.negaflag = True
            self.draw_card(c2, True)

    def _can_sideclick(self):
        if not cw.cwpy.setting.can_clicksidesofcardcontrol:
            return False
        scrpos = wx.GetMousePosition()
        mousepos = self.toppanel.ScreenToClient(scrpos)
        for header in self.get_headers():
            if header.wxrect.collidepoint(mousepos):
                return False
        return self._cursor_in_ctrlsarea(mousepos)

    def _cursor_in_ctrlsarea(self, mousepos):
        for ctrl in self.smallctrls:
            if not (ctrl.IsShown() and ctrl.IsEnabled()):
                continue
            rect = ctrl.GetRect()
            rect.X -= 10
            rect.Y -= 10
            rect.Width += 20
            rect.Height += 20
            if rect.Contains(mousepos):
                return False
        return True

    def _is_cursorinleft(self):
        if not self._can_sideclick():
            return False
        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        return x < rect.x + rect.width / 4 and self.leftbtn.IsEnabled()

    def _is_cursorinright(self):
        if not self._can_sideclick():
            return False
        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        return rect.x + rect.width / 4 * 3 < x and self.rightbtn.IsEnabled()

    def OnMouseWheel(self, event):
        if cw.util.get_wheelrotation(event) > 0:
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
                rect, _x, _y = self._get_starrect(header)
                if self.editstar.GetToggle() and rect.Contains(mousepos):
                    cw.cwpy.play_sound("page")
                    def func():
                        if header.star:
                            header.set_star(0)
                        else:
                            header.set_star(1)
                        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
                            if cw.cwpy.setting.sort_cardswithstar:
                                self._update_sortattr()
                    self.animate_starclick(header, func)
                    return
                else:
                    cw.cwpy.play_sound("click")
                    def func():
                        self.lclick_event(header)
                    self.animate_click(header, func)
                    return

        if self._is_cursorinleft():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn.GetId())
            self.ProcessEvent(btnevent)
        elif self._is_cursorinright():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn.GetId())
            self.ProcessEvent(btnevent)

    def _update_sortattr(self):
        pass

    def OnRightUp(self, event):
        if self._proc:
            return

        cw.cwpy.play_sound("click")

        for header in self.get_headers():
            if header.wxrect.collidepoint(event.GetPosition()):
                def func():
                    self.rclick_event(header)
                self.animate_click(header, func)
                return

        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnRightUp2(self, event):
        cw.cwpy.play_sound("click")
        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnMove(self, event):
        mousepos = event.GetPosition()
        self._on_move(mousepos=mousepos)

    def _on_move(self, mousepos):
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

            rect, _x, _y = self._get_starrect(header)
            if self.editstar.GetToggle() and rect.Contains(mousepos):
                laststar = header
            draw |= laststar <> self._laststar

            if draw:
                self.draw_card(header)

        self._laststar = laststar

        if self._is_cursorinleft():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_BACK"])
        elif self._is_cursorinright():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FORE"])
        else:
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])

    def OnEnter(self, event):
        self.OnMove(event)

    def OnLeave(self, event):
        if self.IsActive():
            self.set_cardpos()

            for header in self.get_headers():
                if header.negaflag:
                    header.negaflag = False
                    self.draw_card(header)
        self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])

    def OnClickLeftBtn2(self, event):
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if index == 0:
            self.combo.SetSelection(count - 1)
        else:
            self.combo.SetSelection(index - 1)
        self.draw_cards()

    def OnClickRightBtn2(self, event):
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if count <= index + 1:
            self.combo.SetSelection(0)
        else:
            self.combo.SetSelection(index + 1)
        self.draw_cards()

    def OnPaint2(self, event):
        if not self._redraw:
            return
        self.set_cardpos()
        tsize = self.toppanel.GetClientSize()

        basebmp = wx.EmptyBitmap(tsize[0], tsize[1])
        dc = wx.MemoryDC(basebmp)
        gcdc = wx.GCDC(dc)
        dc.SetClippingRect(self.toppanel.GetUpdateClientRect())
        bcolor = self.toppanel.GetBackgroundColour()
        dc.SetBrush(wx.Brush(bcolor))
        dc.SetPen(wx.Pen(bcolor))
        dc.DrawRectangle(cw.wins(0), cw.wins(0), tsize[0], tsize[1])

        # 背景の透かし
        bmp = cw.cwpy.rsrc.dialogs["PAD"]
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, (tsize[0]-size[0])/2, (tsize[1]-size[1])/2, True)
        # ライン
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHIGHLIGHT)
        dc.SetPen(wx.Pen(colour, cw.wins(1), wx.SOLID))
        dc.DrawLine(cw.wins(0), cw.wins(25), cw.wins(520), cw.wins(25))
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DSHADOW)
        dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
        dc.DrawLine(cw.wins(0), cw.wins(26), cw.wins(520), cw.wins(26))
        # モード見出し
        dc.SetTextForeground(wx.LIGHT_GREY)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(16)))
        mode = self.get_mode()
        if mode == CCMODE_SHOW:
            s = cw.cwpy.msgs["mode_show"]
        elif mode == CCMODE_MOVE:
            s = cw.cwpy.msgs["mode_move"]
        elif mode == CCMODE_BATTLE:
            s = cw.cwpy.msgs["mode_battle"]
        elif mode == CCMODE_REPLACE:
            s = cw.cwpy.msgs["mode_replace"] % (self.target.name)
        else:
            s = cw.cwpy.msgs["mode_use"]
        fh = dc.GetTextExtent("#")[1]
        fy = (cw.wins(24)-fh) / 2
        dc.DrawText(s, cw.wins(8), fy)

        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
        fh = dc.GetTextExtent("#")[1]
        fy = (cw.wins(24)-fh) / 2
        if self.sort.IsShown():
            s = cw.cwpy.msgs["sort_title"]
            x = self.sort.GetPosition()[0] - dc.GetTextExtent(s)[0] - cw.wins(2)
            dc.DrawText(s, x, fy)
        if self.combo.IsShown():
            s = cw.cwpy.msgs["send_to"]
            x = self.leftbtn2.GetPosition()[0] - dc.GetTextExtent(s)[0] - cw.wins(2)
            dc.DrawText(s, x, fy)

        # 絞込条件
        dc.SetTextForeground(wx.LIGHT_GREY)
        if self.narrow.IsShown():
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["narrow_condition"]
            te = dc.GetTextExtent(s)
            pos = self.narrow.GetPosition()
            size = self.narrow.GetSize()
            dc.DrawText(s, pos[0]-te[0]-cw.wins(3), (size[1]-te[1])/2 + pos[1])

        price = (self.combo and self.combo.IsShown() and self.combo.GetSelection() == self._combo_shelf) or\
                (self.sort and self.sort.IsShown() and cw.cwpy.setting.sort_cards == "Price")
        if price:
            pixelsize = cw.cwpy.setting.fonttypes["price"][2]
            font2x = cw.cwpy.rsrc.get_wxfont("price", pixelsize=cw.wins(pixelsize)*2, adjustsizewx3=False)
            dc.SetFont(font2x)
            gcdc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 160)))
            gcdc.SetPen(wx.TRANSPARENT_PEN)

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

            def draw_price():
                if price:
                    s = u"%s" % (header.sellingprice if header.can_selling() else u"---")
                    padw = cw.wins(2)
                    padh = cw.wins(2)
                    margw = cw.wins(2)
                    margh = cw.wins(2)

                    pw, ph = dc.GetTextExtent(s)
                    pw //= 2
                    ph //= 2
                    maxwidth = w - (padw*2 + margw*2)
                    py = y + h - ph - (margh + padh*2)

                    gcdc.DrawRectangle(x+padw+margw, py-padh, maxwidth, ph+padh*2)

                    px = x + padw+margh + (maxwidth - min(maxwidth, pw)) // 2

                    quality = wx.IMAGE_QUALITY_HIGH
                    cw.util.draw_antialiasedtext(dc, s, px, py, False, maxwidth-padw,
                                                 cw.wins(0), quality=quality, scaledown=True,
                                                 alpha=255, bordering=True)

            def draw_star():
                if self._show_star(header):
                    rect, x, y = self._get_starrect(header)
                    if self.editstar.GetToggle() and rect.Contains(mousepos):
                        bmp = self.starlight
                    elif header.star:
                        bmp = self.star
                    elif self.editstar.GetToggle():
                        bmp = self.nostar
                    else:
                        bmp = None

                    if bmp:
                        if self._starclickedflag:
                            w, h = bmp.GetSize()
                            w2, h2 = int(w*0.9), int(h*0.9)
                            bmp = bmp.ConvertToImage().Rescale(w2, h2).ConvertToBitmap()
                            dc.DrawBitmap(bmp, x + (w-w2)/2, y + (h-h2)/2, True)
                        else:
                            dc.DrawBitmap(bmp, x, y, True)

            if cw.cwpy.setting.edit_star:
                # スターの編集中は価格より上に表示
                draw_price()
                draw_star()
            else:
                draw_star()
                draw_price()

        # カード枚数のフォント設定
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))

        # カード置場・荷物袋・情報カードマーク
        if self._leftmarks:
            rect = self.upbtn.GetRect()
            top = rect[1] + rect[3]
            btm = self.downbtn.GetPosition()[1]
            for leftmark in self._leftmarks:
                h = dc.GetTextExtent("#")[1] + cw.wins(1) + leftmark.GetHeight()
                y = top + (btm-top-h)/2
                x = rect.X + rect.Width / 2 - leftmark.GetWidth() / 2
                dc.DrawBitmap(leftmark, x, y, True)

        if self.callname == "CARDPOCKET":
            # 所持カード数
            num = len(self.selection.cardpocket[cw.cwpy.setting.last_cardpocket])
            maxnum = self.selection.get_cardpocketspace()[cw.cwpy.setting.last_cardpocket]
            s = "Cap " + str(num) + "/" + str(maxnum)
            w = dc.GetTextExtent(s)[0]
            rect = self.beastbtn.GetRect()
            y = rect[1] + rect[3] + cw.wins(5)
            dc.DrawText(s, cw.wins(45)-w/2, y)
        elif self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
            # カード置き場、荷物袋、情報カード
            if self._leftmarks:
                # ページ番号
                maxpage = (len(self.list)+9)/10 if len(self.list) > 0 else 1
                s = "/"
                sw = dc.GetTextExtent(s)[0]
                w = sw
                sx = cw.wins(40)-w/2+cw.wins(7)
                sy = y+max(map(lambda wxbmp: wxbmp.GetHeight(), self._leftmarks))+cw.wins(1)
                dc.DrawText(s, sx, sy)
                s = str(maxpage)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, sx+sw, sy)
                if not cw.cwpy.setting.show_additional_card:
                    s = str(self.index+1)
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, sx-w, sy)

        self._draw_additionals(dc)

        dc.SelectObject(wx.NullBitmap)
        dc = wx.PaintDC(self.toppanel)
        dc.DrawBitmap(basebmp, 0, 0)

        # 保留中のイベントを実施
        if self._after_event:
            cw.cwpy.frame.exec_func(self._after_event)
            self._after_event = None

    def _draw_additionals(self, dc):
        pass

    def _show_star(self, header):
        if not self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "CARDPOCKET"):
            return False
        if self.callname == "CARDPOCKET" and not isinstance(header.get_owner(), cw.character.Player):
            return False
        if not header in self._drawlist:
            return False
        return True

    def _get_starrect(self, header):
        if not self._show_star(header):
            return wx.Rect(0, 0, 0, 0), 0, 0
        x = header.wxrect.left
        y = header.wxrect.top
        bmp, _usemask = self._drawlist[header]
        w = bmp.GetWidth()
        h = bmp.GetHeight()
        x += (header.wxrect.width-w) / 2
        y += (header.wxrect.height-h) / 2
        sw = self.star.GetWidth()
        sh = self.star.GetHeight()
        x = x+w - sw - cw.wins(5)
        y = y+h - sh - cw.wins(5)

        if self.callname == "CARDPOCKET":
            if header.type == "SkillCard":
                y -= cw.wins(32)
            else:
                y -= cw.wins(16)

        if cw.cwpy.setting.show_cardkind and self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            y -= cw.wins(16)

        if self.callname in ("STOREHOUSE", "BACKPACK"):
            sendto = self.combo.GetSelection()
            if sendto in self._combo_cast:
                y -= cw.wins(16)

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
        elif self.callname == "CARDPOCKET_REPLACE":
            return CCMODE_REPLACE
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
            elif self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
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

        test_aptitude = None
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET"):
            sendto = self.combo.GetSelection()
            if sendto in self._combo_cast:
                test_aptitude = self.list2[self._combo_cast[sendto]]

        bmp = header.get_cardwxbmp(test_aptitude=test_aptitude)
        if header.clickedflag:
            bmp = header.cardimg.get_wxclickedbmp(header, bmp, test_aptitude=test_aptitude)
        self._drawlist[header] = (bmp, False)
        self.toppanel.Refresh(rect=header.wxrect)

    def set_cardpos(self, mode=-1):
        if mode == -1:
            if self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
                mode = 1
            elif self.callname == "CARDPOCKET":
                mode = 2
            elif self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
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
            cw.cwpy.frame.wait_frame(4)
            header.clickedflag = False
            self.draw_card(header, fromkeyevent=True)
            header.negaflag = False
            def func3():
                self._proc = False
                func()
            self._after_event = func3
        self._after_event = func2

    def animate_starclick(self, header, func):
        # スターのクリックアニメーション。4フレーム分。
        if self._proc:
            return
        self._proc = True

        self._starclickedflag = True
        self.draw_card(header, fromkeyevent=True)
        def func2():
            cw.cwpy.frame.wait_frame(4)
            self._starclickedflag = False
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
        if self._quit:
            return

        header.negaflag = False
        self.toppanel.SetFocusIgnoringChildren()

        if self.callname == "INFOVIEW":
            self.rclick_event(header)
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
                cw.cwpy.play_sound("dump")
                if isinstance(owner, cw.character.Character):
                    owner.throwaway_card(header)
                else:
                    # デバッガから配布した召喚獣を、荷物袋から処分する場合
                    cw.cwpy.trade("TRASHBOX", header=header, from_event=True)

            dlg.Destroy()
            self.draw_cards()
            self.toppanel.SetFocusIgnoringChildren()
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
                        cw.cwpy.trade("STOREHOUSE", header=header, from_event=False, parentdialog=self, sound=False, sort=True)
                    elif index == self._combo_backpack:
                        cw.cwpy.trade("BACKPACK", header=header, from_event=False, parentdialog=self, sound=False, sort=True)
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
                        self.update_narrowcondition()
                    cw.cwpy.frame.exec_func(func)
                self._proc = True
                cw.cwpy.exec_func(func, header)
                return

        # カード所持者がPlayerCardじゃない場合はカード情報を表示
        if (isinstance(self.selection, cw.character.Friend) and not cw.cwpy.is_battlestatus()) or\
                (not cw.cwpy.debug and isinstance(owner, (cw.character.Enemy, cw.character.Friend))):
            self.rclick_event(header)
            return

        # 開いていたダイアログの情報
        def append_predialogs(callname, index2, pos):
            cw.cwpy.pre_dialogs.append((callname, index2, pos, cw.UP_WIN))
        cw.cwpy.exec_func(append_predialogs, self.callname, self.index2, self.GetPosition())

        # カード操作用データ(移動元データ, CardHeader)を設定
        cw.cwpy.selectedheader = header
        cw.cwpy.exec_func(cw.cwpy.update_selectablelist)
        if self.areaid in cw.AREAS_TRADE:
            def test_aptitude(header):
                # 能力適性表示
                for pcard in cw.cwpy.get_pcards("unreversed"):
                    pcard.test_aptitude = header
                    pcard.update_image()
                # 枚数表示
                cw.cwpy.show_numberofcards(header.type)
                # 売却価格表示
                for poc in cw.cwpy.pricesprites:
                    poc.set_header(header)
            cw.cwpy.exec_func(test_aptitude, header)
        # OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def rclick_event(self, header):
        dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        self.toppanel.SetFocusIgnoringChildren()

    def after_message(self):
        self.toppanel.SetFocusIgnoringChildren()

    def check_using(self, owner, header):
        # 行動不能だったら使用不可
        if owner.is_inactive():
            cw.cwpy.play_sound("error")
            if cw.cwpy.setting.noticeimpossibleaction:
                s = cw.cwpy.msgs["inactive"] % owner.name
                dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                self.toppanel.SetFocusIgnoringChildren()
            return False

        # 使用回数が0以下だったら処理中止
        if header.uselimit <= 0:
            if not header.type in ("ItemCard", "BeastCard") or header.recycle or not header.maxuselimit == 0:
                cw.cwpy.play_sound("error")
                return False

        # 戦闘中にペナルティカードを行動選択していたら処理中止
        if owner.is_autoselectedpenalty() and not cw.cwpy.debug:
            cw.cwpy.play_sound("error")
            if cw.cwpy.setting.noticeimpossibleaction:
                s = cw.cwpy.msgs["selected_penalty"]
                dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                self.toppanel.SetFocusIgnoringChildren()
            return False

        return True

    def OnOk(self, event):
        if self._quit:
            return
        self._quit = True

        self.Enable(False)
        self.Show(False)

        if self.callname in ("CARDPOCKET", "CARDPOCKETB", "HANDVIEW"):
            # カードの対象を選択する
            target_selection = cw.cwpy.is_playingscenario() and cw.cwpy.areaid >= 0
            if target_selection:
                cw.cwpy.exec_func(cw.cwpy.change_specialarea, cw.cwpy.areaid)

        cw.cwpy.frame.kill_dlg(None)
        cw.cwpy.frame.append_killlist(self)

    def OnCancel(self, event):
        if self._quit:
            return
        self._quit = True

        self.Enable(False)
        self.Show(False)

        if not self.callname in ("CARDPOCKET_REPLACE", "INFOVIEW"):
            cw.cwpy.exec_func(cw.cwpy.clear_specialarea, redraw=False)
        cw.cwpy.frame.kill_dlg(None)
        cw.cwpy.frame.append_killlist(self)

#-------------------------------------------------------------------------------
#　カード倉庫or荷物袋or手札カードダイアログ
#-------------------------------------------------------------------------------

class CardHolder(CardControl):
    def __init__(self, parent, callname, selection, pre_info=None, areaid=None):
        # タイプ判別
        self.callname = callname
        self.selection = None

        # 移動先関係
        self._combo_storehouse = -1
        self._combo_backpack = -1
        self._combo_cast = {}
        self._combo_shelf = -1
        self._combo_trush = -1

        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        if self.areaid in cw.AREAS_TRADE:
            status = "unreversed"
        else:
            status = "active"

        # 適性・枚数・価格の表示を除去
        def func():
            for pcard in cw.cwpy.get_pcards():
                if pcard.test_aptitude:
                    pcard.test_aptitude = None
                    pcard.update_image()
                cw.cwpy.clear_numberofcards()
            for poc in cw.cwpy.pricesprites:
                poc.set_header(None)
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
            self.list = cw.cwpy.sdata.get_infocardheaders()
            sendto = False

        # 前に開いていたときのindex値と位置があったら取得する
        if pre_info:
            self.pre_pos = pre_info[2]
            self.index2 = pre_info[1]
            if cw.UP_WIN <> pre_info[3]:
                self.pre_pos = None

            self._load_index()
            if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
                self.list2 = cw.cwpy.get_pcards(status)
                self.selection = self.index2
            if self.callname == "CARDPOCKETB" and cw.cwpy.setting.sort_cards == "None":
                # 整列していない場合は使用されたカードが一番上へ行くため
                # 最上位ページを表示する
                self.index = 0

        else:
            for i in xrange(len(cw.cwpy.setting.show_cardtype)):
                cw.cwpy.setting.show_cardtype[i] = True
                cw.cwpy.setting.last_cardpocketbpage[i] = 0
            cw.cwpy.setting.last_storehousepage = 0
            cw.cwpy.setting.last_backpackpage = 0
            cw.cwpy.setting.last_sendto = 0

            cw.cwpy.setting.card_narrow = ""
            cw.cwpy.setting.edit_star = False

            self._load_index()
            if self.callname == "CARDPOCKET":
                self.selection = selection
                if isinstance(self.selection, cw.character.Player):
                    # パーティの手札カード(リバースメンバを除く)
                    self.list2 = cw.cwpy.get_pcards(status)
                else:
                    # NPCの手札カード
                    self.list2 = cw.cwpy.get_fcards()
            self.index2 = self.selection

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            name =  cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.bgcolour = wx.Colour(0, 0, 128)
            sendto = (not cw.cwpy.is_playingscenario()\
                        or self.areaid == cw.AREA_CAMP or self.areaid in cw.AREAS_TRADE)\
                        and isinstance(self.selection, cw.character.Player)
            # cw.cwpy.setting.last_cardpocket(0:スキル, 1:アイテム, 2:召喚獣)。トグルボタンで切り替える
            if self.callname == "CARDPOCKET":
                self._init_cardpocketlist()
            else:
                assert self.callname == "CARDPOCKETB"
                cspace = self.selection.get_cardpocketspace()[cw.cwpy.setting.last_cardpocket]
                ccount = len(self.selection.cardpocket[cw.cwpy.setting.last_cardpocket])
                if ccount < cspace:
                    # 荷物袋を開く
                    self._set_backpacklist(narrow=False)
                else:
                    # 前回使用時に起きたイベントでスペースが
                    # 一杯になっているなどの場合
                    self.callname = "CARDPOCKET"
                    self._init_cardpocketlist()

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
        CardControl.__init__(self, parent, name, sendto, sort, areaid=areaid, drawcards=False)
        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])

        self.list = self._narrow(self.list)
        # カード移動等でページ数が減っていた場合はself.indexを補正
        if self.callname <> "CARDPOCKET" and 0 < self.index:
            if (len(self.list)+9) / 10 <= self.index:
                self.index = (len(self.list)+9) / 10 - 1
                if self.index < 0:
                    self.index = 0
        self.draw_cards()

        # キャストの手札カード用のコントロール
        # 情報カードダイアログの場合は切り替えが無いため不要
        if self.callname <> "INFOVIEW":
            # skill
            self.skillbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((74, 54)))
            bmp = cw.cwpy.rsrc.buttons["SKILL"]
            self.skillbtn.SetBitmapLabel(bmp, False)
            self.skillbtn.SetBitmapSelected(bmp)
            # item
            self.itembtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((74, 54)))
            bmp = cw.cwpy.rsrc.buttons["ITEM"]
            self.itembtn.SetBitmapLabel(bmp, False)
            self.itembtn.SetBitmapSelected(bmp)
            # beast
            self.beastbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((74, 54)))
            bmp = cw.cwpy.rsrc.buttons["BEAST"]
            self.beastbtn.SetBitmapLabel(bmp, False)
            self.beastbtn.SetBitmapSelected(bmp)
            # cw.cwpy.setting.last_cardpocketの値からトグルをセットする
            for index, btn in enumerate((self.skillbtn, self.itembtn, self.beastbtn)):
                btn.SetToggle(cw.cwpy.setting.last_cardpocket == index)
                self.change_bgs.append(btn)

        # カード置き場、荷物袋、情報カード用のコントロール
        # up
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_UP, cw.wins((70, 40)), bmp=bmp, chain=True)
        # ページ指定
        self.page = wx.lib.intctrl.IntCtrl(self.toppanel, -1, style=wx.TE_RIGHT, size=cw.wins((-1, 22)))
        self._proc_page = False
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(17))
        self.page.SetFont(font)
        self.page.SetValue(1)
        self.page.SetMin(1)
        self.page.SetMax(1)
        self.page.SetLimited(True)
        self.page.SetNoneAllowed(False)
        self.smallctrls.append(self.page)
        self.additionals.append((self.page, lambda: self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW")))
        # down
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_DOWN, cw.wins((70, 40)), bmp=bmp, chain=True)

        self._enable_updown()

        # 移動先選択コンボボックス(情報カードの場合は無し)
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
            self.combo.Select(cw.cwpy.setting.last_sendto)

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

        self._show_controls()

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

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

        self.page.Bind(wx.lib.intctrl.EVT_INT, self.OnPageNum)
        self.page.Bind(wx.EVT_SET_FOCUS, self.OnPageSetFocus)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def _load_index(self):
        if self.callname == "CARDPOCKET":
            self.index = 0
        elif self.callname == "CARDPOCKETB":
            self.index = cw.cwpy.setting.last_cardpocketbpage[cw.cwpy.setting.last_cardpocket]
        elif self.callname == "STOREHOUSE":
            self.index = cw.cwpy.setting.last_storehousepage
        elif self.callname == "BACKPACK":
            self.index = cw.cwpy.setting.last_backpackpage
        elif self.callname == "INFOVIEW":
            self.index = 0
        else:
            assert False

    def _store_index(self):
        if self.callname == "CARDPOCKET":
            pass
        elif self.callname == "CARDPOCKETB":
            cw.cwpy.setting.last_cardpocketbpage[cw.cwpy.setting.last_cardpocket] = self.index
        elif self.callname == "STOREHOUSE":
            cw.cwpy.setting.last_storehousepage = self.index
        elif self.callname == "BACKPACK":
            cw.cwpy.setting.last_backpackpage = self.index
        elif self.callname == "INFOVIEW":
            pass
        else:
            assert False

    def OnPageSetFocus(self, event):
        def func():
            self.page.SetSelection(0, len(str(self.page.GetValue())))
        cw.cwpy.frame.exec_func(func)
        event.Skip()

    def OnDestroy(self, event):
        for header in self._fulllist:
            header.negaflag = False
            header.clickedflag = False

    def OnSort(self, event):
        self.toppanel.SetFocusIgnoringChildren()
        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "Level"
        elif index == 3:
            sorttype = "Type"
        elif index == 4:
            sorttype = "Price"
        elif index == 5:
            sorttype = "Scenario"
        elif index == 6:
            sorttype = "Author"
        else:
            sorttype = "None"
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_cards <> sorttype:
                cw.cwpy.play_sound("page")
                cw.cwpy.setting.sort_cards = sorttype
                self._update_sortattr()

    def OnSortWithStar(self, event):
        cw.cwpy.play_sound("page")
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_cardswithstar:
                cw.cwpy.setting.sort_cardswithstar = False
                self._update_sortattr()
            else:
                cw.cwpy.setting.sort_cardswithstar = True
                self._update_sortattr()

        self._update_sortwithstar()

    def _update_sortwithstar(self):
        bmp = self.star
        toggle = True
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if not cw.cwpy.setting.sort_cardswithstar:
                bmp = self.nostar
                toggle = False
        else:
            return
        self.sortwithstar.SetBitmapFocus(bmp)
        self.sortwithstar.SetBitmapLabel(bmp)
        self.sortwithstar.SetBitmapSelected(bmp)
        self.sortwithstar.SetToggle(toggle)

    def _update_editstar(self):
        bmp = cw.cwpy.rsrc.dialogs["ARRANGE_BOOKMARK"]
        cw.cwpy.setting.edit_star = self.editstar.GetToggle()
        if not cw.cwpy.setting.edit_star:
            bmp = cw.imageretouch.to_disabledimage(bmp)

        self.editstar.SetBitmapFocus(bmp)
        self.editstar.SetBitmapLabel(bmp)
        self.editstar.SetBitmapSelected(bmp)

    def _update_sortattr(self):
        if cw.cwpy.ydata.party:
            cw.cwpy.ydata.party.sort_backpack()
        cw.cwpy.ydata.sort_storehouse()
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            if self.callname == "CARDPOCKETB":
                self._set_backpacklist()
            else:
                self.list = self._narrow(cw.cwpy.ydata.party.backpack)
            self.draw_cards()
        elif self.callname == "STOREHOUSE":
            self.list = self._narrow(cw.cwpy.ydata.storehouse)
            self.draw_cards()

    def OnShowSkill(self, event):
        self._on_show(cw.POCKET_SKILL)

    def OnShowItem(self, event):
        self._on_show(cw.POCKET_ITEM)

    def OnShowBeast(self, event):
        self._on_show(cw.POCKET_BEAST)

    def _on_show(self, cardtype):
        cw.cwpy.play_sound("page")
        btn = self.show[cardtype]
        toggle = btn.GetToggle()
        cw.cwpy.setting.show_cardtype[cardtype] = toggle
        if toggle:
            bmp = self._typeicon_e[cardtype]
        else:
            bmp = self._typeicon_d[cardtype]
        btn.SetBitmapFocus(bmp)
        btn.SetBitmapLabel(bmp)
        btn.SetBitmapSelected(bmp)

        if self.callname in ("BACKPACK"):
            self.list = self._narrow(cw.cwpy.ydata.party.backpack)
        elif self.callname in ("STOREHOUSE"):
            self.list = self._narrow(cw.cwpy.ydata.storehouse)
        else:
            assert False
        self.draw_cards()
        self._enable_updown()
        self._update_page()

    def OnClickLeftBtn(self, event):
        cw.cwpy.play_sound("page")
        self._redraw = False
        old_callname = self.callname

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            if self.index2 is self.list2[0]:
                if self._can_open_backpack:
                    # 荷物袋 ← 左端
                    self.callname = "BACKPACK"
                    self._change_callname(old_callname)
                else:
                    # 右端 ← 左端
                    self.callname = "CARDPOCKET"
                    self.index2 = self.list2[-1]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
                    if self.callname <> old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ左のメンバ
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) - 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname <> old_callname:
                    self._change_callname(old_callname)
        else:
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

        self._redraw = True
        self.draw_cards()

    def OnClickRightBtn(self, event):
        cw.cwpy.play_sound("page")
        self._redraw = False
        old_callname = self.callname

        if self.callname in ("CARDPOCKET", "CARDPOCKETB"):
            if self.index2 is self.list2[-1]:
                if self._can_open_storehouse:
                    # 右端 → カード置き場
                    self.callname = "STOREHOUSE"
                    self._change_callname(old_callname)
                elif self._can_open_backpack:
                    # 右端 → 荷物袋
                    self.callname = "BACKPACK"
                    self._change_callname(old_callname)
                else:
                    # 右端 → 左端
                    self.callname = "CARDPOCKET"
                    self.index2 = self.list2[0]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
                    if self.callname <> old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ右のメンバ
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) + 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname <> old_callname:
                    self._change_callname(old_callname)
        else:
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

        self._redraw = True
        self.draw_cards()

    def OnCancel(self, event):
        if self.callname == "CARDPOCKETB":
            cw.cwpy.play_sound("page")
            old_callname = self.callname
            self.callname = "CARDPOCKET"
            self._change_callname(old_callname)
            self.draw_cards()
        else:
            CardControl.OnCancel(self, event)

    def _change_callname(self, old_callname):
        self.Freeze()
        self._load_index()

        if self.callname == "CARDPOCKET":
            self.bgcolour = wx.Colour(0, 0, 128)
        elif self.callname == "CARDPOCKETB":
            self.bgcolour = wx.Colour(0, 0, 128)
            self._set_backpacklist()
        else:
            if self.callname == "BACKPACK":
                self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], cw.cwpy.msgs["cards_backpack"]))
                self.bgcolour = wx.Colour(0, 0, 128)
                self.list = self._narrow(cw.cwpy.ydata.party.backpack)
            elif self.callname == "STOREHOUSE":
                self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], cw.cwpy.msgs["cards_storehouse"]))
                self.bgcolour = wx.Colour(0, 69, 0)
                self.list = self._narrow(cw.cwpy.ydata.storehouse)
            self.selection = None

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

        self.Parent.change_selection(self.selection)
        if self.callname <> old_callname:
            self._show_controls()
            self._do_layout()

        self._enable_updown()

        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])
        else:
            self.closebtn.SetLabel(cw.cwpy.msgs["close"])
        self.Thaw()

    def _enable_updown(self):
        # リストが空か1ページ分しかなかったら上下ボタンを無効化
        if self.callname == "CARDPOCKET" or len(self.list) <= 10:
            self.upbtn.Disable()
            self.downbtn.Disable()
        else:
            self.upbtn.Enable()
            self.downbtn.Enable()

    def _show_controls(self):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            self.skillbtn.Show()
            self.itembtn.Show()
            self.beastbtn.Show()
            self.upbtn.Hide()
            self.downbtn.Hide()
            self.page.Hide()
        else:
            # カード置き場、荷物袋、情報カード
            self.upbtn.Show()
            self.downbtn.Show()
            if cw.cwpy.setting.show_additional_card:
                self.page.Show()
            else:
                self.page.Hide()
            self._update_page()
            if self.callname <> "INFOVIEW":
                self.skillbtn.Hide()
                self.itembtn.Hide()
                self.beastbtn.Hide()

        # ソート条件
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if not self.sort.IsShown() and cw.cwpy.setting.show_additional_card:
                self.sort.Show()
                self.sortwithstar.Show()
                self.narrow.Show()
                self.narrow_type.Show()
            self._update_sortwithstar()
        else:
            if self.sort.IsShown():
                self.sort.Hide()
                self.sortwithstar.Hide()
                self.narrow.Hide()
                self.narrow_type.Hide()

        # スターの編集
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET", "CARDPOCKETB"):
            self.editstar.Show()
        else:
            self.editstar.Hide()

        # 種別ごと表示有無
        for btn in self.show:
            btn.Show(self.callname in ("BACKPACK", "STOREHOUSE") and cw.cwpy.setting.show_additional_card)

        # 追加的コントロールの表示有無
        if self.addctrlbtn:
            self.addctrlbtn.Show(cw.cwpy.setting.show_addctrlbtn and self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"))

        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            sorttype = cw.cwpy.setting.sort_cards
        else:
            sorttype = None

        if sorttype == "Name":
            self.sort.Select(1)
        elif sorttype == "Level":
            self.sort.Select(2)
        elif sorttype == "Type":
            self.sort.Select(3)
        elif sorttype == "Price":
            self.sort.Select(4)
        elif sorttype == "Scenario":
            self.sort.Select(5)
        elif sorttype == "Author":
            self.sort.Select(6)
        else:
            self.sort.Select(0)

    def _update_page(self):
        index = self.index
        max = (len(self.list)+9)/10 if len(self.list) > 0 else 1
        index = min(index, max-1)
        page = index+1
        self._on_pagenum(page)
        self.index = index
        self._proc_page = True
        self.page.SetMax(max)
        self.page.SetValue(page)
        self._proc_page = False

    def _set_backpacklist(self, narrow=True):
        if cw.cwpy.setting.last_cardpocket == cw.POCKET_SKILL:
            cardtype = "SkillCard"
        elif cw.cwpy.setting.last_cardpocket == cw.POCKET_ITEM:
            cardtype = "ItemCard"
        else:
            assert cw.cwpy.setting.last_cardpocket == cw.POCKET_BEAST
            cardtype = "BeastCard"
        self.list = filter(lambda header: header.type == cardtype, cw.cwpy.ydata.party.backpack)
        if narrow:
            self.list = self._narrow(self.list)

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
                cw.cwpy.play_sound("error")
                if cw.cwpy.setting.noticeimpossibleaction:
                    s = cw.cwpy.msgs["inactive"] % owner.name
                    dlg = message.Message(self, cw.cwpy.msgs["message"], s)
                    self.Parent.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()
                    self.toppanel.SetFocusIgnoringChildren()
                self.draw_cards()
                return
            old_callname = self.callname
            self.callname = "CARDPOCKETB"
            self._change_callname(old_callname)
            self.draw_cards()

        else:
            CardControl.lclick_event(self, header)

    def OnClickToggleBtn(self, event):
        cw.cwpy.play_sound("click")

        l = [self.skillbtn, self.itembtn, self.beastbtn]

        for index, btn in enumerate(l):
            if btn == event.GetEventObject():
                cw.cwpy.setting.last_cardpocket = index
                btn.SetToggle(True)
            else:
                btn.SetToggle(False)

        self.draw_cards()

    def OnUp(self, event):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 特殊技能、アイテム、召喚獣を切り替え
            l = [self.skillbtn, self.itembtn, self.beastbtn]
            btn = l[cw.cwpy.setting.last_cardpocket - 1] if not cw.cwpy.setting.last_cardpocket == 0 else l[len(l) -1]
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
            btn = l[cw.cwpy.setting.last_cardpocket + 1] if not cw.cwpy.setting.last_cardpocket == len(l) -1 else l[0]
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
            btnevent.SetEventObject(btn)
            self.ProcessEvent(btnevent)
        elif self.upbtn.IsShown() and self.downbtn.IsEnabled():
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.downbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnClickUpBtn(self, event):
        cw.cwpy.play_sound("click")
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

        self._proc_page = True
        self.page.SetValue(self.index+1)
        self._proc_page = False
        self._on_pagenum(self.index+1)

        self.draw_cards()

    def OnClickDownBtn(self, event):
        cw.cwpy.play_sound("click")
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

        self._proc_page = True
        self.page.SetValue(self.index+1)
        self._proc_page = False
        self._on_pagenum(self.index+1)

        self.draw_cards()

    def OnPageNum(self, event):
        if self._proc_page:
            return
        if self.page.GetValue() < self.page.GetMin():
            return
        if self.page.GetMax() < self.page.GetValue():
            return
        index = self.page.GetValue()-1
        if self.index <> index:
            cw.cwpy.play_sound("page")
            self._on_pagenum(index+1)

    def _on_pagenum(self, page):
        index = page-1
        negaindex = -1
        if not negaindex == -1:
            for index, header in enumerate(self.get_headers()):
                if index == negaindex:
                    header.negaflag = True
        self.index = index
        self.draw_cards()

    def OnMouseWheel(self, event):
        mousepos = event.GetPosition()
        lwidth = cw.wins(80)
        def selcombo(combo):
            if combo.IsShown() and combo.GetRect().Contains(mousepos):
                index = combo.GetSelection()
                count = combo.GetCount()
                if cw.util.get_wheelrotation(event) > 0:
                    if index <= 0:
                        index = count - 1
                    else:
                        index -= 1
                else:
                    if count <= index + 1:
                        index = 0
                    else:
                        index += 1
                combo.Select(index)
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, combo.GetId())
                combo.ProcessEvent(btnevent)
                return True
            return False
        if selcombo(self.sort):
            return
        elif selcombo(self.narrow_type):
            return
        elif selcombo(self.combo):
            return
        elif mousepos[0] < lwidth or self.callname == "INFOVIEW":
            if self.callname == "CARDPOCKET":
                # キャストの手札カード
                # 特殊技能、アイテム、召喚獣を切り替え
                l = [self.skillbtn, self.itembtn, self.beastbtn]
                if cw.util.get_wheelrotation(event) > 0:
                    btn = l[cw.cwpy.setting.last_cardpocket - 1] if not cw.cwpy.setting.last_cardpocket == 0 else l[len(l) -1]
                else:
                    btn = l[cw.cwpy.setting.last_cardpocket + 1] if not cw.cwpy.setting.last_cardpocket == len(l) -1 else l[0]
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
                btnevent.SetEventObject(btn)
                self.ProcessEvent(btnevent)
                return
            else:
                # カード置き場、荷物袋、情報カード
                # ページを切り替え
                if cw.util.get_wheelrotation(event) > 0:
                    if self.upbtn.IsEnabled():
                        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
                        self.ProcessEvent(btnevent)
                        return
                else:
                    if self.downbtn.IsEnabled():
                        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
                        self.ProcessEvent(btnevent)
                        return

        CardControl.OnMouseWheel(self, event)

    def draw_cards(self, update=True, mode=-1):
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            if (len(self.list)+9) / 10 <= self.index:
                self.index = (len(self.list)+9) / 10 - 1
                if self.index < 0:
                    self.index = 0
        self._store_index()
        if self.selection:
            self._init_cardpocketlist()
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))

        if self.callname == "CARDPOCKET":
            self._leftmarks = []
        else:
            # カード置場・荷物袋・情報カードマーク
            if self.callname == "BACKPACK":
                paths = ["Resource/Image/Card/COMMAND7"]
            elif self.callname == "STOREHOUSE":
                paths = ["Resource/Image/Card/COMMAND5"]
            elif self.callname == "INFOVIEW":
                paths = ["Resource/Image/Card/COMMAND8"]
            elif self.callname == "CARDPOCKETB":
                paths = []
                for info in cw.cwpy.rsrc.backpackcards["ItemCard"].imgpaths:
                    paths.append(os.path.splitext(info.path)[0])
            self._leftmarks = []
            for path in paths:
                path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
                self._leftmarks.append(cw.wins(cw.util.load_wxbmp(path, True, can_loaded_scaledimage=True)))

        CardControl.draw_cards(self, update, mode)

    def _init_cardpocketlist(self):
        if self.callname <> "CARDPOCKET":
            return

        self.list = self.selection.cardpocket[cw.cwpy.setting.last_cardpocket][:]
        if cw.cwpy.setting.show_backpackcard and cw.cwpy.setting.last_cardpocket <> cw.POCKET_SKILL and self.get_mode() == CCMODE_USE:
            space = self.selection.get_cardpocketspace()[cw.cwpy.setting.last_cardpocket]
            if len(self.list) < space:
                cardtype = ""
                if cw.cwpy.setting.last_cardpocket == cw.POCKET_ITEM:
                    cardtype = "ItemCard"
                elif cw.cwpy.setting.last_cardpocket == cw.POCKET_BEAST:
                    cardtype = "BeastCard"
                if cardtype:
                    for header in cw.cwpy.ydata.party.backpack:
                        # 荷物袋に存在する場合のみ選択肢「荷物袋」を表示
                        if header.type == cardtype:
                            # 「荷物袋」の表示順
                            if not cw.cwpy.setting.show_backpackcardatend:
                                self.list.insert(0, cw.cwpy.rsrc.backpackcards[cardtype])
                                break
                            else:
                                self.list.insert(10, cw.cwpy.rsrc.backpackcards[cardtype])
                                break


    def get_headers(self):
        li = self.index * 10
        clist = self.list[li:li + 10]
        return clist

    def _narrow(self, clist):
        self._fulllist = clist
        if not self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            return self._fulllist
        if cw.cwpy.setting.show_additional_card:
            narrow = self.narrow.GetValue().lower()
        else:
            narrow = ""
        ntype = self.narrow_type.GetSelection()

        show = [True] * 3
        if self.callname in ("STOREHOUSE", "BACKPACK"):
            for cardtype, btn in enumerate(self.show):
                show[cardtype] = btn.GetToggle()

        if not narrow and all(show):
            return self._fulllist

        _NARROW_ALL = 0
        _NARROW_NAME = 1
        _NARROW_DESC = 2
        _NARROW_SCENARIO = 3
        _NARROW_AUTHOR = 4
        _NARROW_KEYCODE = 5

        ntypes = set()

        seq = []
        if self.callname == "INFOVIEW":
            if ntype == _NARROW_ALL:
                ntypes.add(_NARROW_NAME)
                ntypes.add(_NARROW_DESC)
            else:
                ntypes.add(ntype)

            for header in self._fulllist:
                if (_NARROW_NAME in ntypes and narrow in header.name.lower()) or \
                        (_NARROW_DESC in ntypes and narrow in header.desc.lower()):
                    seq.append(header)

        else:
            if ntype == _NARROW_ALL:
                ntypes.add(_NARROW_NAME)
                ntypes.add(_NARROW_DESC)
                ntypes.add(_NARROW_SCENARIO)
                ntypes.add(_NARROW_AUTHOR)
                if cw.cwpy.is_debugmode():
                    ntypes.add(_NARROW_KEYCODE)
            else:
                ntypes.add(ntype)

            for header in self._fulllist:
                if header.type == "SkillCard" and not show[cw.POCKET_SKILL]:
                    continue
                if header.type == "ItemCard" and not show[cw.POCKET_ITEM]:
                    continue
                if header.type == "BeastCard" and not show[cw.POCKET_BEAST]:
                    continue

                def match_keycode():
                    if narrow in header.name.lower():
                        # カード名もキーコードになる
                        return True
                    else:
                        for keycode in header.keycodes:
                            if narrow in keycode.lower():
                                return True
                    return False

                if (_NARROW_NAME in ntypes and narrow in header.name.lower()) or\
                        (_NARROW_DESC in ntypes and narrow in header.desc.lower()) or\
                        (_NARROW_SCENARIO in ntypes and narrow in header.scenario.lower()) or\
                        (_NARROW_AUTHOR in ntypes and narrow in header.author.lower()) or\
                        (_NARROW_KEYCODE in ntypes and match_keycode()):
                    seq.append(header)

        return seq

    def update_narrowcondition(self):
        self.list = self._narrow(self._fulllist)
        self._update_page()
        self.draw_cards()

#-------------------------------------------------------------------------------
#　戦闘手札カードダイアログ
#-------------------------------------------------------------------------------

class HandView(CardControl):
    def __init__(self, parent, selection, pre_info=None):
        self.callname = "HANDVIEW"
        self.owner = selection

        # カードリスト
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
        self.index = 0
        if pre_info:
            self.pre_pos = pre_info[2]
            self.index2 = pre_info[1]
            if cw.UP_WIN <> pre_info[3]:
                self.pre_pos = None
            self.selection = self.index2
        else:
            cw.cwpy.setting.card_narrow = ""
            self.selection = selection
            self.index2 = self.selection

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

        # 手札再配布
        if cw.cwpy.is_debugmode():
            bmp = cw.cwpy.rsrc.dialogs["HAND"]
            self.redeal = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((24, 24)), bmp=bmp)
            self.redeal.SetToolTipString(cw.cwpy.msgs["re_deal"])
        else:
            self.redeal = None

        # 使用モードでパーティが一人だけの場合は左右ボタンを無効化
        if len(self.list2) == 1:
            self.rightbtn.Disable()
            self.leftbtn.Disable()

        # layout
        self._do_layout()
        # bind
        self._bind()

    def _do_layout(self):
        CardControl._do_layout(self)
        if self.redeal:
            cwidth = cw.wins(520)
            x = cwidth - cw.wins(5)
            y = cw.wins(0)
            x -= cw.wins(24)
            self.redeal.SetPosition((x, y))
            self.redeal.SetSize(cw.wins((24, 24)))

    def _bind(self):
        CardControl._bind(self)
        if self.redeal:
            self.Bind(wx.EVT_BUTTON, self.OnReDeal, self.redeal)

    def OnReDeal(self, event):
        cw.cwpy.play_sound("dump")

        self.selection.deck.throwaway()
        self.selection.deck.draw(self.selection)

        self.list = self.selection.deck.hand
        for header in self.list:
            header.negaflag = False
        self.draw_cards(update=True)

    def OnClickLeftBtn(self, event):
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[0]:
            self.index2 = self.list2[-1]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) - 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def OnClickRightBtn(self, event):
        cw.cwpy.play_sound("page")

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

    def _draw_additionals(self, dc):
        if self.redeal and self.redeal.IsShown():
            fh = dc.GetTextExtent("#")[1]
            fy = (cw.wins(24) - fh) / 2
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["re_deal_label"]
            x = self.redeal.GetPosition()[0] - dc.GetTextExtent(s)[0] - cw.wins(2)
            dc.DrawText(s, x, fy)


#-------------------------------------------------------------------------------
#　カード交換ダイアログ
#-------------------------------------------------------------------------------

class ReplCardHolder(CardControl):
    def __init__(self, parent, selection, target):
        self.callname = "CARDPOCKET_REPLACE"
        self.owner = selection
        self.target = target

        if target.type == "SkillCard":
            self.cardtype = cw.POCKET_SKILL
        elif target.type == "ItemCard":
            self.cardtype = cw.POCKET_ITEM
        elif target.type == "BeastCard":
            self.cardtype = cw.POCKET_BEAST

        # カードリスト
        status = "unreversed"
        self.list2 = cw.cwpy.get_pcards(status)
        self.list2 = filter(lambda pcard: bool(pcard.cardpocket[self.cardtype]), self.list2)

        # 前に開いていたときのindex値があったら取得する
        self.index = 0
        self.selection = selection
        self.index2 = self.selection

        # 手札リスト
        self.list = self.selection.cardpocket[self.cardtype]
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
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[0]:
            self.index2 = self.list2[-1]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) - 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def OnClickRightBtn(self, event):
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[-1]:
            self.index2 = self.list2[0]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) + 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def draw_cards(self, update=True, mode=-1):
        if self.selection:
            self.list = self.selection.cardpocket[self.cardtype]
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))
        CardControl.draw_cards(self, update, mode)

    def get_headers(self):
        if self.cardtype == cw.POCKET_BEAST:
            return filter(lambda c: c.attachment, self.list)
        return self.list

    def lclick_event(self, header):
        if self._proc:
            return
        header.negaflag = False
        self.toppanel.SetFocusIgnoringChildren()

        def func(target, header, selection):
            owner = target.get_owner()
            if isinstance(owner, cw.character.Player):
                fromtype = "PLAYERCARD"
            elif target.is_backpackheader():
                fromtype = "BACKPACK"
            elif target.is_storehouseheader():
                fromtype = "STOREHOUSE"
            else:
                assert False, owner
            # カードの交換
            if fromtype == "PLAYERCARD":
                # 両方の手札が一杯の可能性があるので一旦荷物袋へ入れる
                cw.cwpy.trade(targettype="BACKPACK", header=target, from_event=False, sound=False, sort=False, call_predlg=False)
            cw.cwpy.trade(targettype=fromtype, target=owner, header=header, from_event=False, sound=False, sort=True, call_predlg=False)
            cw.cwpy.trade(targettype="PLAYERCARD", target=selection, header=target, from_event=False, sound=False, sort=True, call_predlg=False)
            cw.cwpy.exec_func(cw.cwpy.call_predlg)

        cw.cwpy.exec_func(func, self.target, header, self.selection)

        # OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

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
        w, _h = cw.wins((425, 230))
        # 左,上の余白
        leftm = cw.wins(90)

        poslist = []

        if cw.cwpy.setting.show_additional_card:
            y1 = cw.wins(31)
            y2 = cw.wins(145)
        else:
            y1 = cw.wins(39)
            y2 = cw.wins(161)

        for cnt in xrange(num):
            if cnt < 5:
                poslist.append((leftm+cw.wins(84)*cnt, y1))
            else:
                poslist.append((leftm+cw.wins(84)*(cnt-5), y2))

    else:
        if mode == 2:
            # 描画エリアサイズ
            w, _h = cw.wins((425, 230))
            # 折り返し枚数
            numb = 5
            # 左,上の余白
            leftm = cw.wins(88)
        elif mode == 3:
            w, _h = cw.wins((525, 230))
            numb = 6
            leftm = cw.wins(0)

        if num < numb or mode == 3 and num == numb:
            x = (w - cw.wins(83) * num) / 2 + leftm
            y = cw.wins(95)
            poslist = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(num)]
        else:
            row1, row2 = num / 2 + num % 2, num / 2
            x = (w - cw.wins(83) * row1) / 2 + leftm
            y = cw.wins(40)
            row1list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row1)]
            x = (w - cw.wins(83) * row2) / 2 + leftm
            y = cw.wins(160)
            row2list = [(x + (cw.wins(83) * cnt), y) for cnt in xrange(row2)]
            poslist = row1list + row2list

    return poslist

def main():
    pass

if __name__ == "__main__":
    main()
