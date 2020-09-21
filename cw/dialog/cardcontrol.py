#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import os
import sys
import wx
import wx.adv
import wx.lib.buttons
import wx.lib.intctrl

import cw

from typing import Callable, Optional, Tuple, List, Union

# カード操作ダイアログのモード
CCMODE_SHOW = 0  # 閲覧モード
CCMODE_MOVE = 1  # 移動モード
CCMODE_BATTLE = 2  # 戦闘行動選択モード
CCMODE_USE = 3  # 使用モード
CCMODE_REPLACE = 4  # 交換モード


# ------------------------------------------------------------------------------
# カード操作ダイアログ　スーパークラス
# ------------------------------------------------------------------------------

class CardControl(wx.Dialog):
    callname: str
    bgcolour: wx.Colour
    list: List[cw.header.CardHeader]
    selection: Union["cw.sprite.card.PlayerCard", "cw.sprite.card.EnemyCard", "cw.sprite.card.FriendCard"]

    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログ作成
        wx.Dialog.__init__(self, parent, -1, "", style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.MINIMIZE_BOX)
        self.cwpy_debug = False
        if not hasattr(self, "selection"):
            self.selection = None
        self.SetDoubleBuffered(True)
        self.additionals = []
        self.change_bgs = []
        self.smallctrls = []
        self._redraw = True
        self._cancel_animation = True
        self._replcardholder: Optional[ReplCardHolder] = None

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
        self.replace_arrow = cw.cwpy.rsrc.dialogs["REPLACE_POSITION"]
        self.replace_arrow_light = cw.imageretouch.add_lightness_for_wxbmp(cw.cwpy.rsrc.dialogs["REPLACE_POSITION"], 64)

        choices = [cw.cwpy.msgs["sort_no"],
                   cw.cwpy.msgs["sort_name"],
                   cw.cwpy.msgs["sort_level"],
                   cw.cwpy.msgs["sort_type"],
                   cw.cwpy.msgs["sort_price"],
                   cw.cwpy.msgs["scenario_name"],
                   cw.cwpy.msgs["author"],
                   cw.cwpy.msgs["sort_aptitude"]]
        self.sort = wx.ComboBox(self.toppanel, -1, size=cw.wins((75, 24)), choices=choices, style=wx.CB_READONLY)
        self.sort.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        self.sortwithstar = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
        self.sortwithstar.SetToolTip(cw.cwpy.msgs["sort_with_star"])
        self.editstar = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
        self.editstar.SetToolTip(cw.cwpy.msgs["edit_star"])

        def can_sort():
            return self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB")
        self.additionals.append((self.sort, can_sort))
        self.additionals.append((self.sortwithstar, can_sort))
        self.change_bgs.append(self.sortwithstar)
        self.change_bgs.append(self.editstar)

        self.show: List[Optional[wx.lib.buttons.ThemedGenBitmapToggleButton]] = [None] * 3
        self._typeicon_e: List[Optional[wx.Bitmap]] = [None] * 3
        self._typeicon_d: List[Optional[wx.Bitmap]] = [None] * 3
        show = (cw.cwpy.msgs["show_object"])
        for cardtype, bmp, msg in ((cw.POCKET_SKILL, cw.cwpy.rsrc.dialogs["STATUS8"],
                                    (show % cw.cwpy.msgs["skillcard"])),
                                   (cw.POCKET_ITEM, cw.cwpy.rsrc.dialogs["STATUS9"],
                                    (show % cw.cwpy.msgs["itemcard"])),
                                   (cw.POCKET_BEAST, cw.cwpy.rsrc.dialogs["STATUS10"],
                                    (show % cw.cwpy.msgs["beastcard"]))):
            btn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None, size=cw.wins((24, 24)))
            self._typeicon_e[cardtype] = bmp
            dbmp = cw.imageretouch.to_disabledimage(bmp, maskpos=(bmp.GetWidth()-1, 0))
            self._typeicon_d[cardtype] = dbmp
            if not cw.cwpy.setting.show_cardtype[cardtype]:
                bmp = dbmp
            btn.SetBitmapFocus(bmp)
            btn.SetBitmapLabel(bmp, False)
            btn.SetBitmapSelected(bmp)
            btn.SetToolTip(msg)
            self.show[cardtype] = btn
            self.additionals.append((btn, lambda: self.callname in ("BACKPACK", "STOREHOUSE")))
            self.change_bgs.append(btn)

        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 24)), bmp=bmp, chain=True)

        # sendto
        self.combo = cw.util.CWPyBitmapComboBox(self.toppanel, size=cw.wins((100, 24)),
                                                style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self.combo.SetFont(cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14)))
        self.combo.SetPopupMaxHeight(cw.wins(14*20))
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((20, 24)), bmp=bmp, chain=True)

        # 追加的コントロールの表示切替
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET", "CARDPOCKETB", "INFOVIEW"):
            self.addctrlbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None,
                                                                         size=cw.wins((24, 24)))
            self.addctrlbtn.SetToolTip(cw.cwpy.msgs["show_additional_controls"])
            self.change_bgs.append(self.addctrlbtn)
        else:
            self.addctrlbtn = None

        # 絞込条件
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15))
        self.narrow = wx.TextCtrl(self.toppanel, -1, size=cw.wins((100, 20)))
        self.narrow.SetFont(font)
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.narrow_type = wx.ComboBox(self.toppanel, -1, size=cw.wins((90, 20)), choices=(), style=wx.CB_READONLY)
        self.narrow_type.SetFont(font)

        self.additionals.append((self.narrow, self._can_narrow))
        self.additionals.append((self.narrow_type, self._can_narrow))

    def reconstruct(self, callname: str, name: str, sendto: bool, sort: bool, areaid: Optional[int]) -> None:
        self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], name))
        self._quit = False
        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        if self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
            s = cw.cwpy.msgs["entry_cancel"]
        else:
            s = cw.cwpy.msgs["close"]
        self.closebtn.SetLabel(s)

        self._laststar = None
        self._lastrepls = None
        self.editstar.SetToggle(cw.cwpy.setting.edit_star)
        self._update_sortwithstar()
        self._update_editstar()

        if self.addctrlbtn:
            self.addctrlbtn.SetToggle(cw.cwpy.setting.show_additional_card)

        self.sort.Show(sort and cw.cwpy.setting.show_additional_card)
        self.sortwithstar.Show(sort and cw.cwpy.setting.show_additional_card)

        self.editstar.Show(sort)

        for cardtype, btn in enumerate(self.show):
            if cw.cwpy.setting.show_cardtype[cardtype]:
                btn.SetToggle(True)
            else:
                btn.SetToggle(False)
            btn.Show(self.callname in ("BACKPACK", "STOREHOUSE") and cw.cwpy.setting.show_additional_card)

        self.leftbtn2.Show(sendto)
        self.rightbtn2.Show(sendto)
        self.combo.Show(sendto)

        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET", "CARDPOCKETB", "INFOVIEW"):
            self.addctrlbtn.Show(cw.cwpy.setting.show_addctrlbtn)

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
        self.narrow_type.SetItems(choices)
        if self.callname == "INFOVIEW":
            narrow_sel = cw.cwpy.setting.infoview_narrowtype
        else:
            narrow_sel = cw.cwpy.setting.card_narrowtype
        if narrow_sel < self.narrow_type.GetCount():
            self.narrow_type.SetSelection(narrow_sel)
        else:
            self.narrow_type.SetSelection(1)
        self.narrow.SetValue(cw.cwpy.setting.card_narrow)

        self.narrow.Show(self._can_narrow() and cw.cwpy.setting.show_additional_card)
        self.narrow_type.Show(self._can_narrow() and cw.cwpy.setting.show_additional_card)

        self._drawlist = {}
        self._leftmarks = []
        self._after_event = None
        self._starclickedflag = False
        self._replclickedflag = False
        self._animate_frame = 0
        self._price_sheet = None

        self._proc = False

        if self.addctrlbtn:
            self.update_additionals()

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

        self.draw_cards()

        self.toppanel.SetFocusIgnoringChildren()

    def _bind(self) -> None:
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
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=self.closebtn.GetId())
        self.Bind(wx.EVT_CLOSE, self.OnClose)

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
        for i in range(0, 9):
            narrowkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=narrowkeydown)
            seq.append((wx.ACCEL_CTRL, ord('1')+i, narrowkeydown))
            self.narrowkeydown.append(narrowkeydown)
            sortkeydown = wx.NewId()
            self.Bind(wx.EVT_MENU, self.OnNumberKeyDown, id=sortkeydown)
            seq.append((wx.ACCEL_ALT, ord('1')+i, sortkeydown))
            self.sortkeydown.append(sortkeydown)

        debugid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnDebugMode, id=debugid)
        seq.append((wx.ACCEL_CTRL, ord('D'), debugid))

        cw.util.set_acceleratortable(self, seq)

    def _can_narrow(self) -> bool:
        return self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW")

    def OnNumberKeyDown(self, event):
        """
        数値キー'1'～'9'までの押下を処理する。
        CardControlではソート条件の変更を行う。
        """
        self._cancel_animation = True
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

    def _do_layout(self) -> None:
        """
        引数に子クラスで設定したsizer_leftbarが必要
        """
        cwidth = cw.wins(520)
        cheight = cw.wins(285)

        # 表示有無を切り替えた時に多少綺麗に再配置されるように、
        # 非表示のコントロールは画面外へ出しておく
        for ctrl in self.toppanel.GetChildren():
            if not ctrl.IsShown() and 0 <= ctrl.GetSize()[0]:
                ctrl.SetPosition((cwidth, cw.wins(0)))

        # toppanelはSizerを使わず自前で座標を計算
        if self.callname == "CARDPOCKET":
            assert isinstance(self, CardHolder)
            # キャストの手札カード
            x = cw.wins(10)
            if self.is_showpersonal():
                y = cw.wins(37)
            else:
                y = cw.wins(64)
            self.skillbtn.SetPosition((x, y))
            y += self.skillbtn.GetSize()[1]
            self.itembtn.SetPosition((x, y))
            y += self.itembtn.GetSize()[1]
            self.beastbtn.SetPosition((x, y))
            if self.is_showpersonal():
                y += self.beastbtn.GetSize()[1]
                self.personalbtn.SetPosition((x, y))
        elif self.callname not in ("HANDVIEW", "CARDPOCKET_REPLACE"):
            # カード置き場、荷物袋、情報カード
            assert isinstance(self, (CardHolder, InfoView))
            x = cw.wins(10)
            if cw.cwpy.setting.show_addctrlbtn:
                y = cw.wins(40)
            else:
                y = cw.wins(50)
            self.upbtn.SetSize(cw.wins((70, 40)))
            self.upbtn.SetPosition((x, y))
            y += self.upbtn.GetSize()[1]
            y += cw.wins(240-110)
            self.downbtn.SetSize(cw.wins((70, 40)))
            self.downbtn.SetPosition((x, y))

            # ページ番号入力欄
            psize = (cw.wins(34), self.page.GetSize()[1])
            dc = wx.ClientDC(self)
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(14)))
            rect = self.upbtn.GetRect()
            top = rect[1] + rect[3]
            btm = self.downbtn.GetPosition()[1]
            h = dc.GetTextExtent("#")[1] + cw.wins(1) + cw.wins(cw.SIZE_CARDIMAGE[1])
            y = top + (btm-top-h)//2
            y += cw.wins(cw.SIZE_CARDIMAGE[1])+cw.wins(1)
            te = dc.GetTextExtent("/")
            sx = cw.wins(40)-te[0]//2+cw.wins(7)
            y += te[1] // 2
            y -= psize[1]//2
            self.page.SetSize(psize)
            self.page.SetPosition((sx-psize[0], y))

        # 絞込条件
        if self.narrow.IsShown():
            y = cheight - cw.wins(5)
            y -= cw.wins(20)
            x = cwidth - cw.wins(5)
            x -= cw.wins(90)
            self.narrow_type.SetSize(cw.wins((90, 20)))
            yc = y + (cw.wins(20)-self.narrow_type.GetSize()[1]) // 2
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
            yc = y + (cw.wins(24)-self.combo.GetSize()[1]) // 2
            self.combo.SetPosition((x, yc))

            x -= cw.wins(20)
            self.leftbtn2.SetPosition((x, y))
            self.leftbtn2.SetSize(cw.wins((20, 24)))
            x -= cw.wins(50)

        if self.callname in ("BACKPACK", "STOREHOUSE"):
            for cardtype in (cw.POCKET_BEAST, cw.POCKET_ITEM, cw.POCKET_SKILL):
                shown = False
                btn = self.show[cardtype]
                assert isinstance(btn, wx.Control)
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
            yc = y + (cw.wins(24)-self.sort.GetSize()[1]) // 2
            self.sort.SetPosition((x, yc))

        # 追加的コントロールの表示
        if self.addctrlbtn:
            w, h = self.addctrlbtn.GetSize()
            self.addctrlbtn.SetPosition((cw.wins(2), cheight-h-cw.wins(2)))

        # ボタンバー
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer_1)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        self.panel.SetSizer(sizer_panel)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.closebtn, 0, wx.TOP | wx.BOTTOM, cw.wins(3))
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        # トップパネルとボタンバーのサイザーを設定
        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        sizer_1.Fit(self)
        self.Layout()

    def OnClickLeftBtn(self, event):
        pass

    def OnClickRightBtn(self, event):
        pass

    def OnDebugMode(self, event):
        def func(self):
            cw.cwpy.play_sound("page")
            value = not cw.cwpy.is_debugmode()
            cw.cwpy.set_debug(value)

            def func(self):
                if not self:
                    return
                self.update_debug()
            cw.cwpy.frame.exec_func(func, self)
        cw.cwpy.exec_func(func, self)

    def update_debug(self):
        if self.callname != "INFOVIEW":
            if cw.cwpy.is_debugmode():
                i = self.narrow_type.FindString(cw.cwpy.msgs["key_code"])
                if i == -1:
                    self.narrow_type.Append(cw.cwpy.msgs["key_code"])
            else:
                i = self.narrow_type.FindString(cw.cwpy.msgs["key_code"])
                if i != -1:
                    if self.narrow_type.GetSelection() == i:
                        self.narrow_type.SetSelection(0)
                        self.update_narrowcondition()
                    self.narrow_type.Delete(i)

    def update_additionals(self) -> None:
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

    def OnClose(self, event: wx.CloseEvent) -> None:
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnToggleAdditionalControls(self, event):
        if not self.addctrlbtn or self.callname not in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            return
        self.addctrlbtn.SetToggle(not self.addctrlbtn.GetToggle())
        self._additional_controls()

    def OnAdditionalControls(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._additional_controls()

    def _additional_controls(self) -> None:
        self._cancel_animation = True
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

    def OnNarrowCondition(self, event: wx.CommandEvent) -> None:
        if not self.IsShown():
            return
        self._cancel_animation = True
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

    def OnSendTo(self, event: wx.CommandEvent) -> None:
        cw.cwpy.play_sound("page")
        cw.cwpy.setting.last_sendto = self.combo.GetSelection()
        self.toppanel.SetFocusIgnoringChildren()
        if self.callname in ("BACKPACK", "CARDPOCKETB", "STOREHOUSE") and cw.cwpy.setting.sort_cards == "Aptitude":
            self._update_sortattr()
        else:
            self.draw_cards()

    def update_narrowcondition(self):
        self.draw_cards()

    def OnSort(self, event):
        pass

    def OnSortWithStar(self, event):
        pass

    def OnEditStar(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        cw.cwpy.play_sound("page")
        self._cancel_animation = True
        self._update_editstar()
        self._on_move(mousepos=self.toppanel.ScreenToClient(wx.GetMousePosition()))
        self.Refresh()

    def OnShowSkill(self, event):
        pass

    def OnShowItem(self, event):
        pass

    def OnShowBeast(self, event):
        pass

    def _update_sortwithstar(self) -> None:
        pass

    def _update_editstar(self) -> None:
        pass

    def OnUp(self, event):
        pass

    def OnDown(self, event):
        pass

    def OnKeyDown(self, event):
        if self._proc:
            return

        eid = event.GetId()
        self._cancel_animation = True

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
            if c1.negaflag:
                c1.negaflag = False
                self.draw_card(c1, True)
        if c2:
            if not c2.negaflag:
                c2.negaflag = True
                self.draw_card(c2, True)

        self.update_cardpocketinfo_with(c2)

    def update_cardpocketinfo_with(self, header: Optional[cw.header.CardHeader]) -> None:
        pass

    def _can_sideclick(self) -> bool:
        if not cw.cwpy.setting.can_clicksidesofcardcontrol:
            return False
        scrpos = wx.GetMousePosition()
        mousepos = self.toppanel.ScreenToClient(scrpos)
        for header in self.get_headers():
            if header.wxrect.collidepoint(mousepos):
                return False
        return self._cursor_in_ctrlsarea(mousepos)

    def _cursor_in_ctrlsarea(self, mousepos: wx.Point) -> bool:
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

    def _is_cursorinleft(self) -> bool:
        if not self._can_sideclick():
            return False
        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        return x < rect.x + rect.width // 4 and self.leftbtn.IsEnabled()

    def _is_cursorinright(self) -> bool:
        if not self._can_sideclick():
            return False
        rect = self.toppanel.GetClientRect()
        x, _y = self.toppanel.ScreenToClient(wx.GetMousePosition())
        return rect.x + rect.width // 4 * 3 < x and self.rightbtn.IsEnabled()

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        self._cancel_animation = True
        if cw.util.get_wheelrotation(event) > 0:
            if self.leftbtn.IsEnabled():
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.leftbtn.GetId())
                self.ProcessEvent(btnevent)
        else:
            if self.rightbtn.IsEnabled():
                btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.rightbtn.GetId())
                self.ProcessEvent(btnevent)

    def OnLeftUp(self, event: wx.MouseEvent) -> None:
        if self._proc:
            return

        self._cancel_animation = True
        mousepos = event.GetPosition()
        headers = self.get_headers()

        if headers:
            bheaders = self.get_beforepageheaders()
            for header in itertools.chain(bheaders[-1:] if bheaders else [], headers):
                rect, _x, _y = self._get_replsrect(header)
                if self._can_repls() and rect.Contains(mousepos):
                    cw.cwpy.play_sound("click")

                    def func():
                        i = self.list.index(header)
                        self._replace_position(header, self.list[i+1])
                    self.animate_replsclick(header, func)
                    return

        for header in headers:
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

    def _update_sortattr(self, draw=True):
        pass

    def _replace_position(self, header1: cw.header.CardHeader, header2: cw.header.CardHeader) -> None:
        bheaders = self.get_beforepageheaders()
        if bheaders and bheaders[-1] is header1:
            # 前ページの末尾にある場合
            header1, header2 = header2, header1

        index1 = self.list.index(header1)
        index2 = self.list.index(header2)
        h2shown = header2 in self.get_headers()

        def func():
            cw.cwpy.ydata.changed()
            header1.wxrect, header2.wxrect = header2.wxrect, header1.wxrect
            header1.negaflag, header2.negaflag = header2.negaflag, header1.negaflag
            header1.order, header2.order = header2.order, header1.order
            self.list[index1] = header2
            self.list[index2] = header1
            self._replace_position_impl(header1, header2)
            self.animate_deal(header2, header1 if h2shown else None, lambda: None)
            header1.deal_per = 100
            header2.deal_per = 100
            self.set_cardpos(self.get_posmode())
            self._on_move(mousepos=self.toppanel.ScreenToClient(wx.GetMousePosition()))
            self.Refresh()
        self.animate_hide(header1, header2 if h2shown else None, func)

    def _replace_position_impl(self, header1, header2):
        pass

    def OnRightUp(self, event: wx.MouseEvent) -> None:
        if self._proc:
            return

        self._cancel_animation = True
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

    def OnRightUp2(self, event: wx.MouseEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("click")
        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.closebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnMove(self, event: wx.MouseEvent) -> None:
        if self._proc:
            return
        mousepos = event.GetPosition()
        self._on_move(mousepos=mousepos)

    def _on_move(self, mousepos: wx.Point) -> None:
        self.set_cardpos()

        if not self.IsShown():
            return

        laststar = None
        lastrepls = None

        bheaders = self.get_beforepageheaders()
        if bheaders and self._can_repls():
            rect, _x, _y = self._get_replsrect(bheaders[-1])
            if rect.Contains(mousepos):
                lastrepls = bheaders[-1]

        for header in self.get_headers():
            rect, _x, _y = self._get_replsrect(header)
            if self._can_repls() and rect.Contains(mousepos):
                lastrepls = header
            rect, _x, _y = self._get_starrect(header)
            if not lastrepls and self.editstar.GetToggle() and rect.Contains(mousepos):
                laststar = header

        selected = None
        updated = False
        outofall = True  # 枚数のちらつきを抑えるため隙間の部分にカーソルが行った時は枚数情報を更新しないようにする
        for header in self.get_headers():
            lrect = wx.Rect(header.wxrect[0]-cw.wins(2), header.wxrect[1]-+cw.wins(2),
                            header.wxrect[2]+cw.wins(4), header.wxrect[3]+cw.wins(4))
            if lrect.Contains(mousepos):
                outofall = False
            draw = False
            if not lastrepls and not laststar and header.wxrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    draw = True
                    selected = header
                    updated = True

            elif header.negaflag:
                header.negaflag = False
                draw = True
                updated = True

            if draw:
                self.draw_card(header, fromkeyevent=True)

        if (selected and updated) or outofall:
            self.update_cardpocketinfo_with(selected)

        if lastrepls != self._lastrepls:
            if lastrepls:
                self.toppanel.RefreshRect(rect=self._get_replsrect(lastrepls)[0])
            if self._lastrepls:
                self.toppanel.RefreshRect(rect=self._get_replsrect(self._lastrepls)[0])
        if laststar != self._laststar:
            if laststar:
                self.toppanel.RefreshRect(rect=self._get_starrect(laststar)[0])
            if self._laststar:
                self.toppanel.RefreshRect(rect=self._get_starrect(self._laststar)[0])

        self._laststar = laststar
        self._lastrepls = lastrepls

        if self._laststar or self._lastrepls:
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])
        elif self._is_cursorinleft():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_BACK"])
        elif self._is_cursorinright():
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FORE"])
        else:
            self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])

    def OnEnter(self, event: wx.MouseEvent) -> None:
        self.OnMove(event)

    def OnLeave(self, event: wx.MouseEvent) -> None:
        if self.IsActive():
            self.set_cardpos()

            for header in self.get_headers():
                if header.negaflag:
                    header.negaflag = False
                    self.draw_card(header)
        self.toppanel.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_ARROW"])

    def OnClickLeftBtn2(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if index == 0:
            self.combo.Select(count - 1)
        else:
            self.combo.Select(index - 1)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.combo.GetId())
        self.combo.ProcessEvent(btnevent)

    def OnClickRightBtn2(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        count = len(self.combo.GetItems())
        index = self.combo.GetSelection()
        if count <= index + 1:
            self.combo.Select(0)
        else:
            self.combo.Select(index + 1)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.combo.GetId())
        self.combo.ProcessEvent(btnevent)

    def OnPaint2(self, event: wx.PaintEvent) -> None:
        if not self._redraw:
            return
        self.set_cardpos()
        tsize = self.toppanel.GetClientSize()

        basebmp = cw.util.empty_bitmap(tsize[0], tsize[1])
        dc = wx.MemoryDC(basebmp)
        dc.SetClippingRegion(*self.toppanel.GetUpdateClientRect())
        bcolor = self.toppanel.GetBackgroundColour()
        dc.SetBrush(wx.Brush(bcolor))
        dc.SetPen(wx.Pen(bcolor))
        dc.DrawRectangle(cw.wins(0), cw.wins(0), tsize[0], tsize[1])

        # 背景の透かし
        bmp = cw.cwpy.rsrc.dialogs["PAD"]
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, (tsize[0]-size[0])//2, (tsize[1]-size[1])//2, True)
        # ライン
        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHIGHLIGHT)
        dc.SetPen(wx.Pen(colour, cw.wins(1), wx.SOLID))
        dc.DrawLine(cw.wins(0), cw.wins(25), cw.wins(520), cw.wins(25))
        colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)
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
            assert isinstance(self, ReplCardHolder)
            s = cw.cwpy.msgs["mode_replace"] % (self.target.name)
        else:
            s = cw.cwpy.msgs["mode_use"]
        fh = dc.GetTextExtent("#")[1]
        fy = (cw.wins(24)-fh) // 2
        dc.DrawText(s, cw.wins(8), fy)

        dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
        fh = dc.GetTextExtent("#")[1]
        fy = (cw.wins(24)-fh) // 2
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
            dc.DrawText(s, pos[0]-te[0]-cw.wins(3), (size[1]-te[1])//2 + pos[1])

        assert isinstance(self, (CardHolder, HandView, ReplCardHolder))
        price = (self.combo and self.combo.IsShown() and self.combo.GetSelection() == self._combo_shelf) or\
                (self.sort and self.sort.IsShown() and cw.cwpy.setting.sort_cards == "Price")
        if price:
            pixelsize = cw.cwpy.setting.fonttypes["price"][2]
            font2x = cw.cwpy.rsrc.get_wxfont("price", pixelsize=cw.wins(pixelsize)*2, adjustsizewx3=False)
            dc.SetFont(font2x)

            padw = cw.wins(2)
            padh = cw.wins(2)
            margw = cw.wins(2)
            margh = cw.wins(2)

            if not self._price_sheet:
                _pw, ph = dc.GetTextExtent("0")
                wxsize = cw.wins(cw.setting.SIZE_RESOURCES["CardBg/ACTION"])
                psw = wxsize[0] - margw*2 - padw*2
                psh = ph//2+padh*2

                data = bytearray([255] * (psw*psh*3))
                alpha = bytearray([160] * (psw*psh))

                self._price_sheet = wx.Bitmap.FromBufferAndAlpha(psw, psh, data, alpha)

        # カードの描画
        mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
        for header, data in self._drawlist.items():
            bmp, usemask = data
            if not bmp:
                continue
            x = header.wxrect.left
            y = header.wxrect.top
            w = bmp.GetWidth()
            h = bmp.GetHeight()
            x += (header.wxrect.width-w) // 2
            y += (header.wxrect.height-h) // 2
            dc.DrawBitmap(bmp, x, y, usemask)

            def draw_price():
                if price:
                    s = "%s" % (header.sellingprice if header.can_selling() else "---")
                    pw, ph = dc.GetTextExtent(s)
                    pw //= 2
                    ph //= 2
                    maxwidth = w - (padw*2 + margw*2)
                    py = y + h - ph - (margh + padh*2)

                    dc.DrawBitmap(self._price_sheet, x+padw+margw, py-padh)

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
                        if header.deal_per != 100:
                            w, h = bmp.GetSize()
                            w2 = w * header.deal_per // 100
                            if 0 < w2:
                                bmp = bmp.ConvertToImage().Rescale(w2, h).ConvertToBitmap()
                                dc.DrawBitmap(bmp, x, y, True)
                        elif self._starclickedflag:
                            w, h = bmp.GetSize()
                            w2, h2 = int(w*0.9), int(h*0.9)
                            bmp = bmp.ConvertToImage().Rescale(w2, h2).ConvertToBitmap()
                            dc.DrawBitmap(bmp, x + (w-w2)//2, y + (h-h2)//2, True)
                        else:
                            dc.DrawBitmap(bmp, x, y, True)

            if cw.cwpy.setting.edit_star:
                # スターの編集中は価格より上に表示
                draw_price()
                draw_star()
            else:
                draw_star()
                draw_price()

        if self._can_repls():
            # 位置入替用矢印
            bheaders = self.get_beforepageheaders()
            for header in itertools.chain(bheaders[-1:] if bheaders else [], self.get_headers()):
                rect, x, y = self._get_replsrect(header)
                if rect.Width == 0:
                    continue
                if self._replclickedflag:
                    bmp = self.replace_arrow
                    w, h = bmp.GetSize()
                    w2, h2 = int(w * 0.9), int(h * 0.9)
                    bmp = bmp.ConvertToImage().Rescale(w2, h2).ConvertToBitmap()
                    if rect.Contains(mousepos):
                        bmp = cw.imageretouch.add_lightness_for_wxbmp(bmp, 64)
                    dc.DrawBitmap(bmp, x + (w - w2) // 2, y + (h - h2) // 2, True)
                else:
                    if rect.Contains(mousepos):
                        bmp = self.replace_arrow_light
                    else:
                        bmp = self.replace_arrow
                    dc.DrawBitmap(bmp, x, y, True)

        # カード枚数のフォント設定
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(17)))

        # カード置場・荷物袋・情報カードマーク
        if self._leftmarks:
            rect = self.upbtn.GetRect()
            top = rect[1] + rect[3]
            btm = self.downbtn.GetPosition()[1]
            for leftmark in self._leftmarks:
                h = dc.GetTextExtent("#")[1] + cw.wins(1) + leftmark.GetHeight()
                y = top + (btm-top-h)//2
                x = rect.X + rect.Width // 2 - leftmark.GetWidth() // 2
                dc.DrawBitmap(leftmark, x, y, True)

        if self.callname == "CARDPOCKET":
            # 所持カード数
            if cw.cwpy.setting.last_cardpocket == cw.POCKET_PERSONAL:
                num = len(self.selection.personal_pocket)
                maxnum = self.selection.get_personalpocketspace()
            else:
                num = len(self.selection.cardpocket[cw.cwpy.setting.last_cardpocket])
                maxnum = self.selection.get_cardpocketspace()[cw.cwpy.setting.last_cardpocket]
            s = "Cap " + str(num) + "/" + str(maxnum)
            w = dc.GetTextExtent(s)[0]
            if self.is_showpersonal():
                rect = self.personalbtn.GetRect()
            else:
                rect = self.beastbtn.GetRect()
            y = rect[1] + rect[3] + cw.wins(5)
            dc.DrawText(s, cw.wins(45)-w//2, y)
        elif self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
            # カード置き場、荷物袋、情報カード
            if self._leftmarks:
                # ページ番号
                maxpage = (len(self.list)+9)//10 if len(self.list) > 0 else 1
                s = "/"
                sw = dc.GetTextExtent(s)[0]
                w = sw
                sx = cw.wins(40)-w//2+cw.wins(7)
                sy = y+max([wxbmp.GetHeight() for wxbmp in self._leftmarks])+cw.wins(1)
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

    def _draw_additionals(self, dc: wx.DC) -> None:
        pass

    def _show_star(self, header: cw.header.CardHeader) -> bool:
        if self.callname not in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "CARDPOCKET"):
            return False
        if self.callname == "CARDPOCKET" and not isinstance(header.get_owner(), cw.character.Player):
            return False
        if header not in self._drawlist:
            return False
        return True

    def _get_starrect(self, header: cw.header.CardHeader) -> Tuple[wx.Rect, int, int]:
        if not self._show_star(header):
            return wx.Rect(0, 0, 0, 0), 0, 0
        bmp, _usemask = self._drawlist[header]
        if not bmp:
            return wx.Rect(0, 0, 0, 0), 0, 0
        x = float(header.wxrect.left)
        y = float(header.wxrect.top)
        w = bmp.GetWidth()
        h = bmp.GetHeight()
        x += (header.wxrect.width-w) / 2.0
        y += (header.wxrect.height-h) / 2.0
        sw = (self.star.GetWidth()*header.deal_per/100.0)
        sh = self.star.GetHeight()
        x = x+w - sw - (cw.wins(5)*header.deal_per/100.0)
        y = y+h - sh - cw.wins(5)
        x = int(x)
        y = int(y)

        if self.callname == "CARDPOCKET":
            if header.type == "SkillCard" and not (self.is_showpersonal() and
                                                   header.personal_owner):
                # 使用回数と適性丸
                y -= cw.wins(32)
            else:
                # 適性丸
                y -= cw.wins(16)

        if cw.cwpy.setting.show_cardkind and (self.callname in ("STOREHOUSE", "BACKPACK") or
                                              (self.is_showpersonal() and header.personal_owner)):
            # 種類アイコン
            y -= cw.wins(16)
        if self.callname == "CARDPOCKETB":
            # 適性丸
            y -= cw.wins(16)

        if self.callname in ("STOREHOUSE", "BACKPACK"):
            assert isinstance(self, CardHolder)
            sendto = self.combo.GetSelection()
            if sendto in self._combo_cast:
                y -= cw.wins(16)

        return wx.Rect(x-cw.wins(5), y-cw.wins(5), sw+cw.wins(10), sh+cw.wins(10)), x, y

    def _can_repls(self) -> bool:
        if self.callname == "HANDVIEW":
            return False  # 当面は戦闘行動選択ビューでは入替不可とする
        if self.sort.GetSelection() != 0 or not self.editstar.GetToggle():
            return False
        if self.callname == "INFOVIEW":
            return False
        return True

    def _get_replsrect(self, header: cw.header.CardHeader) -> Tuple[wx.Rect, int, int]:
        if not self._can_repls():
            return wx.Rect(0, 0, 0, 0), 0, 0

        if header not in self.get_headers():
            bheaders = self.get_beforepageheaders()
            # 前のページの末尾にある？
            in_beforepage = bheaders and bheaders[-1] is header
            if not in_beforepage:
                return wx.Rect(0, 0, 0, 0), 0, 0
        else:
            in_beforepage = False

        headers = self.list
        # 全リストの末尾にある？
        if not headers or headers[-1] is header:
            return wx.Rect(0, 0, 0, 0), 0, 0

        if self.callname == "HANDVIEW":
            header2 = headers[headers.index(header)+1]
            if header2.type != header.type:
                return wx.Rect(0, 0, 0, 0), 0, 0

        if self.sortwithstar and self.sortwithstar.GetToggle():
            header2 = headers[headers.index(header)+1]
            if header2.star != header.star:
                return wx.Rect(0, 0, 0, 0), 0, 0

        bmp = self.replace_arrow
        if in_beforepage:
            assert headers
            x = int(headers[0].wxrect.left - (get_spacer_x(self.get_posmode()) / 2.0) - bmp.GetWidth() / 2.0)
            y = headers[0].wxrect.top + cw.wins(20)
        else:
            x = int(header.wxrect.right + (get_spacer_x(self.get_posmode()) / 2.0) - bmp.GetWidth() / 2.0)
            y = header.wxrect.top + cw.wins(20)
        return wx.Rect(x, y, bmp.GetWidth(), bmp.GetHeight()), x, y

    def draw(self, update: bool = True) -> None:
        if update:
            self.draw_cards(update)
        self.toppanel.Refresh()

    def get_mode(self) -> int:
        if self.callname == "INFOVIEW" or\
            (self.callname == "CARDPOCKET" and isinstance(self.selection, cw.character.Friend)) or\
            (self.callname == "HANDVIEW" and not cw.cwpy.is_debugmode() and
             isinstance(self.selection, (cw.character.Enemy, cw.character.Friend))):
            return CCMODE_SHOW
        elif self.callname == "CARDPOCKET_REPLACE":
            return CCMODE_REPLACE
        elif self.areaid in cw.AREAS_TRADE:
            return CCMODE_MOVE
        elif self.callname == "HANDVIEW":
            return CCMODE_BATTLE
        else:
            return CCMODE_USE

    def draw_cards(self, update: bool = True, mode: int = -1) -> None:
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

    def _get_test_aptitude(self) -> Optional["cw.sprite.card.PlayerCard"]:
        assert isinstance(self, (CardHolder, HandView, ReplCardHolder))
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET"):
            sendto = self.combo.GetSelection()
            if sendto in self._combo_cast:
                return self.list2[self._combo_cast[sendto]]
            elif sendto in self._combo_personal:
                return self.list2[self._combo_personal[sendto]]
        elif self.callname == "CARDPOCKETB":
            return self.selection
        return None

    def draw_card(self, header: cw.header.CardHeader, fromkeyevent: bool = False) -> None:
        if not fromkeyevent and self.IsActive() and self.IsShown():
            selected = None
            updated = False

            mousepos = self.ScreenToClient(wx.GetMousePosition())
            if header.wxrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    selected = header
                    updated = True
            elif header.negaflag:
                header.negaflag = False
                updated = True

            if updated:
                self.update_cardpocketinfo_with(selected)

        test_aptitude = self._get_test_aptitude()

        bmp = header.get_cardwxbmp(test_aptitude=test_aptitude)
        if header.clickedflag:
            bmp = header.cardimg.get_wxclickedbmp(header, bmp, test_aptitude=test_aptitude)
        elif header.deal_per == 0:
            bmp = None
        elif header.deal_per != 100:
            bmp = header.cardimg.get_wxdealingbmp(header, bmp, n=header.deal_per, test_aptitude=test_aptitude)
        self._drawlist[header] = (bmp, False)
        self.toppanel.RefreshRect(rect=wx.Rect(*header.wxrect))

    def get_posmode(self) -> int:
        if self.callname in ("INFOVIEW", "BACKPACK", "STOREHOUSE", "CARDPOCKETB"):
            return 1
        elif self.callname == "CARDPOCKET":
            return 2
        elif self.callname in ("HANDVIEW", "CARDPOCKET_REPLACE"):
            return 3
        else:
            assert False, self.callname

    def set_cardpos(self, mode: int = -1) -> None:
        if mode == -1:
            mode = self.get_posmode()

        headers = self.get_headers()
        poslist = get_poslist(len(headers), mode)

        for pos, header in zip(poslist, headers):
            header.wxrect.topleft = pos

    def is_showpersonal(self) -> bool:
        return False

    def get_headers(self):
        pass

    def get_beforepageheaders(self) -> List[cw.header.CardHeader]:
        return []

    def animate_click(self, header: cw.header.CardHeader, func: Callable[[], None]) -> None:
        # クリックアニメーション。4フレーム分。
        if self._proc:
            return
        self._proc = True
        self._cancel_animation = False

        self.set_cardpos()

        cw.cwpy.frame.start_wait()
        header.clickedflag = True
        self.draw_card(header, fromkeyevent=True)

        def func2():
            if not self or self._cancel_animation:
                header.clickedflag = False
                self._proc = False
                return
            cw.cwpy.frame.wait_frame(4)
            header.clickedflag = False
            self.draw_card(header, fromkeyevent=True)
            header.negaflag = False

            def func3():
                if not self or self._cancel_animation:
                    header.clickedflag = False
                    self._proc = False
                    return
                self._proc = False
                func()
            self._after_event = func3
        self._after_event = func2

    def animate_starclick(self, header: cw.header.CardHeader, func: Callable[[], None]) -> None:
        # スターのクリックアニメーション。4フレーム分。
        if self._proc:
            return
        self._proc = True
        self._cancel_animation = False

        cw.cwpy.frame.start_wait()
        self._starclickedflag = True
        self.draw_card(header, fromkeyevent=True)

        def func2():
            if not self or self._cancel_animation:
                self._starclickedflag = False
                self._proc = False
                return
            cw.cwpy.frame.wait_frame(4)
            self._starclickedflag = False
            self.draw_card(header, fromkeyevent=True)
            header.negaflag = False

            def func3():
                if not self or self._cancel_animation:
                    self._starclickedflag = False
                    self._proc = False
                    return
                self._proc = False
                func()
            self._after_event = func3
        self._after_event = func2

    def animate_replsclick(self, header: cw.header.CardHeader, func: Callable[[], None]) -> None:
        # 位置入替矢印のクリックアニメーション。4フレーム分。
        if self._proc:
            return
        self._proc = True
        self._cancel_animation = False

        cw.cwpy.frame.start_wait()
        self._replclickedflag = True
        self.RefreshRect(rect=self._get_replsrect(header)[0])

        def func2():
            if not self or self._cancel_animation:
                self._replclickedflag = False
                self._proc = False
                return
            cw.cwpy.frame.wait_frame(4)
            self._replclickedflag = False
            self.RefreshRect(rect=self._get_replsrect(header)[0])

            def func3():
                if not self or self._cancel_animation:
                    self._replclickedflag = False
                    self._proc = False
                    return
                self._proc = False
                func()
            self._after_event = func3
        self._after_event = func2

    def _animate_dealhide(self, header1: cw.header.CardHeader, header2: cw.header.CardHeader, func: Callable[[], None],
                          dealing_scales: List[int], lastscale: int) -> None:
        if self._proc:
            return
        self._proc = True
        self._cancel_animation = False

        self._animate_frame = 0

        def func2():
            if not self or self._cancel_animation:
                header1.deal_per = 100
                if header2:
                    header2.deal_per = 100
                self._proc = False
                return
            if self._animate_frame + 1 < len(dealing_scales):
                cw.cwpy.frame.wait_frame(1)
                self._animate_frame += 1
                n = dealing_scales[self._animate_frame]
                header1.deal_per = n
                if header2:
                    header2.deal_per = n
                self.draw_card(header1, fromkeyevent=True)
                if header2:
                    self.draw_card(header2, fromkeyevent=True)
                self._after_event = func2
            else:
                header1.deal_per = lastscale
                if header2:
                    header2.deal_per = lastscale
                self.draw_card(header1, fromkeyevent=True)
                if header2:
                    self.draw_card(header2, fromkeyevent=True)

                def func3():
                    if not self or self._cancel_animation:
                        header1.deal_per = 100
                        if header2:
                            header2.deal_per = 100
                        self._proc = False
                        return
                    self._proc = False
                    self._animate_frame = 0
                    func()
                self._after_event = func3

        cw.cwpy.frame.start_wait()
        if dealing_scales:
            n = dealing_scales[self._animate_frame]
            header1.deal_per = n
            if header2:
                header2.deal_per = n
            self.draw_card(header1, fromkeyevent=True)
            if header2:
                self.draw_card(header2, fromkeyevent=True)
            self._after_event = func2
        else:
            func2()

    def animate_hide(self, header1: cw.header.CardHeader, header2: cw.header.CardHeader,
                     func: Callable[[], None]) -> None:
        self._animate_dealhide(header1, header2, func, cw.cwpy.setting.dealing_scales, 0)

    def animate_deal(self, header1: cw.header.CardHeader, header2: cw.header.CardHeader,
                     func: Callable[[], None]) -> None:
        self._animate_dealhide(header1, header2, func, cw.cwpy.setting.dealing_scales[::-1], 100)

    def lclick_event(self, header: cw.header.CardHeader) -> None:
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
        if self.areaid in cw.AREAS_TRADE and header.type == "BeastCard" and not header.attachment:
            s = cw.cwpy.msgs["confirm_dump"] % (header.name)
            dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            cw.cwpy.frame.move_dlg(dlg)

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
        elif self.areaid not in cw.AREAS_TRADE and isinstance(owner, cw.character.Character):
            if not self.check_using(owner, header):
                self.draw_cards()
                return
        if self.is_showpersonal() and self.callname == "CARDPOCKET" and self.areaid in cw.AREAS_TRADE and\
                self.selection.reversed:
            assert isinstance(self, CardHolder)
            if not self.personalbtn.GetToggle():
                s = cw.cwpy.msgs["can_not_trade_reversed"]
                self.show_errordialog(s)
                return

        if self.combo.IsShown():
            index = self.combo.GetSelection()
            if index != self._combo_manual:
                def func(header):
                    assert isinstance(self, CardHolder)
                    if index == self._combo_storehouse:
                        cw.cwpy.trade("STOREHOUSE", header=header, from_event=False, parentdialog=self, sound=False,
                                      sort=True)
                    elif index == self._combo_backpack:
                        cw.cwpy.trade("BACKPACK", header=header, from_event=False, parentdialog=self, sound=False,
                                      sort=True)
                    elif index in self._combo_cast:
                        target = self.list2[self._combo_cast[index]]
                        cw.cwpy.trade("PLAYERCARD", header=header, target=target, from_event=False, parentdialog=self,
                                      sound=False)
                        cw.cwpy.frame.exec_func(self._update_cardpocketinfo, self._cardpocketinfo, force=True)
                    elif index in self._combo_personal:
                        if header.personal_owner:
                            header.personal_owner.remove_personalpocket(header)
                        cw.cwpy.trade("BACKPACK", header=header, from_event=False, parentdialog=self, sound=False,
                                      sort=False)
                        target = self.list2[self._combo_personal[index]]
                        target.add_personalpocket(header)
                        cw.cwpy.ydata.party.sort_backpack()
                        cw.cwpy.frame.exec_func(self._update_cardpocketinfo, self._cardpocketinfo, force=True)
                    elif index == self._combo_shelf:
                        cw.cwpy.trade("PAWNSHOP", header=header, from_event=False, parentdialog=self, sound=False)
                    elif index == self._combo_trush:
                        cw.cwpy.trade("TRASHBOX", header=header, from_event=False, parentdialog=self, sound=False)

                    def func():
                        self._proc = False
                        self.update_narrowcondition()
                    cw.cwpy.frame.exec_func(func)

                if cw.cwpy.setting.replacecard_when_sendfullcardpocket and (index in self._combo_cast or
                                                                            index in self._combo_personal):
                    dlg = None
                    if index in self._combo_cast:
                        target = self.list2[self._combo_cast[index]]
                        if header.type == "SkillCard":
                            pocket = cw.POCKET_SKILL
                        elif header.type == "ItemCard":
                            pocket = cw.POCKET_ITEM
                        elif header.type == "BeastCard":
                            pocket = cw.POCKET_BEAST
                        if target.get_cardpocketspace()[pocket] <= len(target.cardpocket[pocket]) and\
                                target is not header.get_owner():
                            if not self._replcardholder:
                                self._replcardholder = cw.dialog.cardcontrol.ReplCardHolder(self)
                            self._replcardholder.reconstruct_replcardholder(target, header, personal=False)
                            dlg = self._replcardholder

                    elif index in self._combo_personal:
                        target = self.list2[self._combo_personal[index]]
                        if target.get_personalpocketspace() <= len(target.personal_pocket) and\
                                target is not header.personal_owner:
                            if not self._replcardholder:
                                self._replcardholder = cw.dialog.cardcontrol.ReplCardHolder(self)
                            self._replcardholder.reconstruct_replcardholder(target, header, personal=False)
                            dlg = self._replcardholder

                    if dlg:
                        cw.cwpy.frame.move_dlg(dlg)
                        dlg.ShowModal()
                        dlg.Destroy()

                        def func(self):
                            def func(self):
                                if self:
                                    self.update_narrowcondition()
                                    self.draw_cards(True)
                            cw.cwpy.frame.exec_func(func, self)
                        cw.cwpy.exec_func(func, self)
                        return

                self._proc = True
                cw.cwpy.exec_func(func, header)
                return

        # カード所持者がPlayerCardじゃない場合はカード情報を表示
        if (isinstance(self.selection, cw.character.Friend) and not cw.cwpy.is_battlestatus()) or\
                (not cw.cwpy.is_debugmode() and isinstance(owner, (cw.character.Enemy, cw.character.Friend))):
            self.rclick_event(header)
            return

        # 開いていたダイアログの情報
        def append_predialogs(callname, index2, pos):
            cw.cwpy.pre_dialogs.append((callname, index2, pos, cw.UP_WIN))
        cw.cwpy.exec_func(append_predialogs, self.callname, self.index2, self.GetPosition())

        # カード操作用データ(移動元データ, CardHeader)を設定
        cw.cwpy.selectedheader = header

        def func():
            cw.cwpy.update_tradecards()
            cw.cwpy.set_testaptitude(cw.cwpy.selectedheader)
            cw.cwpy.update_selectablelist()
        cw.cwpy.exec_func(func)
        # OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def rclick_event(self, header: Union[cw.header.CardHeader, cw.header.InfoCardHeader]) -> None:
        from . import cardinfo

        dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        mousepos = self.ScreenToClient(wx.GetMousePosition())
        self._on_move(mousepos)
        self.toppanel.SetFocusIgnoringChildren()

    def after_message(self):
        self.toppanel.SetFocusIgnoringChildren()

    def show_errordialog(self, s):
        from . import message

        cw.cwpy.play_sound("error")
        if cw.cwpy.setting.noticeimpossibleaction:
            dlg = message.Message(self, cw.cwpy.msgs["message"], s)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            self.toppanel.SetFocusIgnoringChildren()

    def check_using(self,
                    owner: Union["cw.sprite.card.EnemyCard", "cw.sprite.card.PlayerCard", "cw.sprite.card.FriendCard"],
                    header: cw.header.CardHeader) -> bool:
        assert isinstance(self, (CardHolder, HandView))

        # 隠蔽中は使用不可
        if owner.reversed:
            s = cw.cwpy.msgs["reversed"] % owner.name
            self.show_errordialog(s)
            return False

        # 行動不能だったら使用不可
        if owner.is_inactive():
            s = cw.cwpy.msgs["inactive"] % owner.name
            self.show_errordialog(s)
            return False

        # 特殊技能カードは私有枠からは使用不可
        if self.is_showpersonal() and self.personalbtn.GetToggle() and header.type == "SkillCard":
            s = cw.cwpy.msgs["use_failed_personal_skill_card"]
            self.show_errordialog(s)
            return False

        # 使用回数が0以下だったら処理中止
        if header.uselimit <= 0:
            if header.type not in ("ItemCard", "BeastCard") or header.recycle or not header.maxuselimit == 0:
                cw.cwpy.play_sound("error")
                return False

        # 一時的に取り出そうとしている時、カード枠が足りなければ処理中止
        if self.is_showpersonal() and self.personalbtn.GetToggle() and header.is_backpackheader():
            if header.type == "ItemCard":
                pocket = cw.POCKET_ITEM
            elif header.type == "BeastCard":
                pocket = cw.POCKET_BEAST
            else:
                assert False
            if self.selection.get_cardpocketspace()[pocket] <= len(self.selection.cardpocket[pocket]):
                s = cw.cwpy.msgs["use_failed_hand_be_full"] % self.selection.get_showingname()
                self.show_errordialog(s)
                return False

        # 戦闘中にペナルティカードを行動選択していたら処理中止
        if owner.is_autoselectedpenalty() and not cw.cwpy.is_debugmode():
            s = cw.cwpy.msgs["selected_penalty"]
            self.show_errordialog(s)
            return False

        # 召喚獣の発動条件を満たしていなければ処理中止(Wsn.3)
        if header.type == "BeastCard" and not header.is_activewithstatus(owner):
            s = cw.cwpy.msgs["beast_invocation_failed"]
            self.show_errordialog(s)
            return False

        return True

    def OnOk(self, event: wx.PyCommandEvent) -> None:
        if self._quit:
            return
        self._quit = True
        self._cancel_animation = True

        if hasattr(self, "touchtools"):
            self.touchtools.Hide()
        self.Show(False)

        if self.callname in ("CARDPOCKET", "CARDPOCKETB", "HANDVIEW"):
            # カードの対象を選択する
            target_selection = cw.cwpy.is_playingscenario() and cw.cwpy.areaid >= 0
            if target_selection:
                cw.cwpy.exec_func(cw.cwpy.change_specialarea, cw.cwpy.areaid)

        if self.Parent is cw.cwpy.frame:
            cw.cwpy.frame.kill_dlg(None)

    def OnCancel(self, event: wx.PyCommandEvent) -> None:
        if self._quit:
            return
        self._quit = True
        self._cancel_animation = True

        if hasattr(self, "touchtools"):
            self.touchtools.Hide()
        self.Show(False)
        self.list = []
        self.list2 = []
        self.selection = None

        if self.Parent is cw.cwpy.frame:
            if self.callname not in ("CARDPOCKET_REPLACE", "INFOVIEW"):
                def func():
                    if cw.cwpy.areaid in cw.AREAS_TRADE:
                        cw.cwpy.clear_specialarea(redraw=False)
                cw.cwpy.exec_func(func)
            cw.cwpy.frame.kill_dlg(None)


# ------------------------------------------------------------------------------
# カード倉庫or荷物袋or手札カードダイアログ
# ------------------------------------------------------------------------------

class CardHolder(CardControl):
    def __init__(self, parent: wx.TopLevelWindow, callname: str) -> None:
        # タイプ判別
        self.callname = callname

        # ダイアログ作成
        CardControl.__init__(self, parent)

        # キャストの手札カード用のコントロール
        # 情報カードダイアログの場合は切り替えが無いため不要
        if self.callname != "INFOVIEW":
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
            if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKET", "CARDPOCKETB"):
                # 私有
                self.personalbtn = wx.lib.buttons.ThemedGenBitmapToggleButton(self.toppanel, -1, None,
                                                                              size=cw.wins((74, 54)))
                bmp = cw.cwpy.rsrc.buttons["PERSONAL"]
                self.personalbtn.SetBitmapLabel(bmp, False)
                self.personalbtn.SetBitmapSelected(bmp)
            else:
                self.personalbtn = None
            # cw.cwpy.setting.last_cardpocketの値からトグルをセットする
            for index, btn in enumerate((self.skillbtn, self.itembtn, self.beastbtn, self.personalbtn)):
                if btn:
                    btn.SetToggle(cw.cwpy.setting.last_cardpocket == index)
                    self.change_bgs.append(btn)

        # カード置き場、荷物袋、情報カード用のコントロール
        # up
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_UP, cw.wins((70, 40)), bmp=bmp, chain=True)
        # ページ指定
        self.page = wx.lib.intctrl.IntCtrl(self.toppanel, -1, style=wx.TE_RIGHT, size=cw.wins((-1, 22)))
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(17))
        self.page.SetFont(font)
        self.page.SetValue(1)
        self.page.SetMin(1)
        self.page.SetMax(1)
        self.page.SetLimited(True)
        self.page.SetNoneAllowed(False)
        self.smallctrls.append(self.page)
        self.additionals.append((self.page, lambda: self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB",
                                                                      "INFOVIEW")))
        # down
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_DOWN, cw.wins((70, 40)), bmp=bmp, chain=True)

        # bind
        self._bind()

    def reconstruct_cardholder(self, callname: str, selection: Optional["cw.sprite.card.CWPyCard"],
                               pre_info: Optional[Tuple[str, Optional[int], wx.Point, Union[int, float]]] = None,
                               areaid: Optional[int] = None) -> None:
        self.callname = callname
        self.selection = None

        if self.callname == "CARDPOCKETB" and not cw.cwpy.sdata.party_environment_backpack:
            # 荷物袋から一時的に取り出してカードを使用した際に発火したイベントで荷物袋が禁止された
            self.callname = "CARDPOCKET"

        # 移動先関係
        self._combo_storehouse = -1
        self._combo_backpack = -1
        self._combo_cast = {}
        self._combo_personal = {}
        self._combo_shelf = -1
        self._combo_trush = -1

        if areaid is None:
            self.areaid = cw.cwpy.areaid
        else:
            self.areaid = areaid

        if self.areaid in cw.AREAS_TRADE:
            if cw.cwpy.setting.show_personal_cards and isinstance(selection, cw.character.Player):
                status = ""
            else:
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
                cw.cwpy.add_lazydraw(clip=pcard.rect)
            for poc in cw.cwpy.pricesprites:
                poc.set_header(None)
        cw.cwpy.exec_func(func)

        # タイプ別初期化(キャストの手札の場合はindex復元後)
        if self.callname == "BACKPACK":
            name = cw.cwpy.msgs["cards_backpack"]
            self.list2 = cw.cwpy.get_pcards(status)
            self.bgcolour = wx.Colour(0, 0, 128)
            if self.areaid in cw.AREAS_TRADE:
                r, g, b = cw.cwpy.setting.trademode_cardholder_color
                self.bgcolour = wx.Colour(r, g, b)
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
            if cw.UP_WIN != pre_info[3]:
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
            for i in range(len(cw.cwpy.setting.show_cardtype)):
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
            name = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.bgcolour = wx.Colour(0, 0, 128)
            if self.areaid in cw.AREAS_TRADE:
                r, g, b = cw.cwpy.setting.trademode_cardholder_color
                self.bgcolour = wx.Colour(r, g, b)
            isplayer = isinstance(self.selection, cw.character.Player)
            sendto = (not cw.cwpy.is_playingscenario() or
                      self.areaid == cw.AREA_CAMP or self.areaid in cw.AREAS_TRADE) and isplayer
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
        if self.callname == "INFOVIEW":
            self._can_open_cardpocket = False
            self._can_open_backpack = False
            self._can_open_storehouse = False
        else:
            # キャストの手札
            self._can_open_cardpocket = cw.cwpy.ydata.party and 0 < len(cw.cwpy.ydata.party.members)
            # 荷物袋
            self._can_open_backpack = self._can_open_cardpocket and sendto and cw.cwpy.sdata.party_environment_backpack
            # カード置場
            self._can_open_storehouse = not cw.cwpy.is_playingscenario()

        # ダイアログ作成
        sort = self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB")
        CardControl.reconstruct(self, callname, name, sendto=sendto, sort=sort, areaid=areaid)
        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])

        self.list = self._narrow(self.list)
        # カード移動等でページ数が減っていた場合はself.indexを補正
        if self.callname != "CARDPOCKET" and 0 < self.index:
            if (len(self.list)+9) // 10 <= self.index:
                self.index = (len(self.list)+9) // 10 - 1
                if self.index < 0:
                    self.index = 0
        self.draw_cards()

        # キャストの手札カード用のコントロール
        # 情報カードダイアログの場合は切り替えが無いため不要
        if self.callname != "INFOVIEW":
            if cw.cwpy.setting.show_personal_cards and (isinstance(self.selection, cw.character.Player) or
                                                        self.callname in ("STOREHOUSE", "BACKPACK")):
                self.personalbtn.Show(cw.cwpy.sdata.party_environment_backpack)
            else:
                if cw.cwpy.setting.last_cardpocket == cw.POCKET_BEAST:
                    cw.cwpy.setting.last_cardpocket = cw.POCKET_SKILL
                self.personalbtn.Hide()

        self._proc_page = False
        self._enable_updown()

        # 移動先選択コンボボックス(情報カードの場合は無し)
        self._cardpocketinfo = -1
        if sendto:
            self.combo.Clear()
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
                    if castdata.reversed:
                        continue
                    self._combo_cast[len(self.combo.GetItems())] = index
                    self.combo.Append(castdata.name, bmp)
                    index += 1

                bmp = cw.cwpy.rsrc.buttons["CAST_PERSONAL"]
                index = 0
                for castdata in self.list2:
                    self._combo_personal[len(self.combo.GetItems())] = index
                    s = "%s(%s/%s)" % (cw.cwpy.msgs["send_to_personal"] % castdata.name,
                                       len(castdata.personal_pocket),
                                       castdata.get_personalpocketspace())
                    self.combo.Append(s, bmp)
                    index += 1
                self._cardpocketinfo = -1

                if self.callname == "CARDPOCKET":
                    self._update_cardpocketinfo(cw.cwpy.setting.last_cardpocket)
            if not cw.cwpy.is_playingscenario():
                bmp = cw.cwpy.rsrc.buttons["SHELF"]
                self._combo_shelf = len(self.combo.GetItems())
                self.combo.Append(cw.cwpy.msgs["send_to_shelf"], bmp)
            if not cw.cwpy.is_playingscenario() or cw.cwpy.is_debugmode():
                self._combo_trush = len(self.combo.GetItems())
                bmp = cw.cwpy.rsrc.buttons["TRUSH"]
                self.combo.Append(cw.cwpy.msgs["send_to_trush"], bmp)
            self.combo.Select(cw.cwpy.setting.last_sendto)
        else:
            self.combo.Clear()

        self._sendto = sendto

        # パーティが組まれていない(カード置き場のみ)か、
        # 使用モードや閲覧モードで対象が一人だけの場合は
        # 左右ボタンを無効化
        if (self.callname == "INFOVIEW")\
                or (not cw.cwpy.ydata.party)\
                or (not sendto and len(self.list2) == 1):
            self.rightbtn.Disable()
            self.leftbtn.Disable()
        else:
            self.rightbtn.Enable()
            self.leftbtn.Enable()

        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 選択中カード色反転
            self.Parent.change_selection(self.selection)

        else:
            # カード置き場、荷物袋、情報カード
            if self.callname != "INFOVIEW":
                # 選択中カード色反転
                self.Parent.change_selection(self.selection)

        self._show_controls()

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

        # layout
        self._do_layout()

    def _bind(self) -> None:
        CardControl._bind(self)

        if self.callname != "INFOVIEW":
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.skillbtn)
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.itembtn)
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.beastbtn)
            self.Bind(wx.EVT_BUTTON, self.OnClickToggleBtn, self.personalbtn)

        self.Bind(wx.EVT_BUTTON, self.OnClickUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDownBtn, self.downbtn)

        self.page.Bind(wx.lib.intctrl.EVT_INT, self.OnPageNum)
        self.page.Bind(wx.EVT_SET_FOCUS, self.OnPageSetFocus)

    def update_debug(self):
        CardControl.update_debug(self)
        if self._sendto and cw.cwpy.is_playingscenario():
            s = cw.cwpy.msgs["send_to_trush"]
            if cw.cwpy.is_debugmode():
                i = self.combo.FindString(s)
                if i == -1:
                    self._combo_trush = len(self.combo.GetItems())
                    bmp = cw.cwpy.rsrc.buttons["TRUSH"]
                    self.combo.Append(s, bmp)
            else:
                i = self.combo.FindString(s)
                if i != -1:
                    if self.combo.GetSelection() == i:
                        self.combo.Select(0)
                        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.combo.GetId())
                        self.combo.ProcessEvent(btnevent)
                        cw.cwpy.setting.last_sendto = self.combo.GetSelection()
                        self.toppanel.SetFocusIgnoringChildren()
                        self.draw_cards()
                    self.combo.Delete(i)

    def _load_index(self) -> None:
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

    def _store_index(self) -> None:
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

    def OnPageSetFocus(self, event: wx.FocusEvent) -> None:
        def func():
            self.page.SetSelection(0, len(str(self.page.GetValue())))
        cw.cwpy.frame.exec_func(func)
        event.Skip()

    def OnSort(self, event: wx.CommandEvent) -> None:
        self._cancel_animation = True
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
        elif index == 7:
            sorttype = "Aptitude"
        else:
            sorttype = "None"
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_cards != sorttype:
                cw.cwpy.play_sound("page")
                cw.cwpy.setting.sort_cards = sorttype
                self._update_sortattr()

    def OnSortWithStar(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("page")
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB"):
            if cw.cwpy.setting.sort_cardswithstar:
                cw.cwpy.setting.sort_cardswithstar = False
                self._update_sortattr()
            else:
                cw.cwpy.setting.sort_cardswithstar = True
                self._update_sortattr()

        self._update_sortwithstar()

    def _update_sortwithstar(self) -> None:
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

    def _update_editstar(self) -> None:
        bmp = cw.cwpy.rsrc.dialogs["ARRANGE_BOOKMARK"]
        cw.cwpy.setting.edit_star = self.editstar.GetToggle()
        if not cw.cwpy.setting.edit_star:
            bmp = cw.imageretouch.to_disabledimage(bmp)

        self.editstar.SetBitmapFocus(bmp)
        self.editstar.SetBitmapLabel(bmp)
        self.editstar.SetBitmapSelected(bmp)

    def _update_sortattr(self, draw: bool = True) -> bool:
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            assert cw.cwpy.ydata.party is not None
            cw.cwpy.ydata.party.sort_backpack(test_aptitude=self._get_test_aptitude())
            if self.callname == "CARDPOCKETB":
                self._set_backpacklist()
            else:
                self.list = self._narrow(cw.cwpy.ydata.party.backpack)
            if draw:
                self.draw_cards()
            return True
        elif self.callname == "STOREHOUSE":
            assert cw.cwpy.ydata is not None
            cw.cwpy.ydata.sort_storehouse(test_aptitude=self._get_test_aptitude())
            self.list = self._narrow(cw.cwpy.ydata.storehouse)
            if draw:
                self.draw_cards()
            return True
        else:
            return False

    def OnShowSkill(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._on_show(cw.POCKET_SKILL)

    def OnShowItem(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._on_show(cw.POCKET_ITEM)

    def OnShowBeast(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._on_show(cw.POCKET_BEAST)

    def _on_show(self, cardtype: int) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("page")
        btn = self.show[cardtype]
        assert isinstance(btn, wx.lib.buttons.ThemedGenBitmapToggleButton)
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

    def OnClickLeftBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
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
                    if self.callname != old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ左のメンバ
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) - 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname != old_callname:
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

    def OnClickRightBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
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
                    if self.callname != old_callname:
                        self._change_callname(old_callname)
            else:
                # 一つ右のメンバ
                self.callname = "CARDPOCKET"
                self.index2 = self.list2[self.list2.index(self.index2) + 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
                if self.callname != old_callname:
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

    def OnClose(self, event: wx.CloseEvent) -> None:
        self._clear_flags()
        CardControl.OnCancel(self, event)

    def OnCancel(self, event: wx.PyCommandEvent) -> None:
        self._clear_flags()
        if self.callname == "CARDPOCKETB":
            cw.cwpy.play_sound("page")
            old_callname = self.callname
            self.callname = "CARDPOCKET"
            self._change_callname(old_callname)
            self.draw_cards()
        else:
            CardControl.OnCancel(self, event)

    def _clear_flags(self) -> None:
        self._cancel_animation = True
        for header in self._fulllist:
            header.negaflag = False
            header.clickedflag = False

    def _change_callname(self, old_callname: str) -> None:
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

        if self.callname in ("CARDPOCKET", "CARDPOCKETB", "BACKPACK") and self.areaid in cw.AREAS_TRADE:
            r, g, b = cw.cwpy.setting.trademode_cardholder_color
            self.bgcolour = wx.Colour(r, g, b)

        for ctrl in self.change_bgs:
            ctrl.SetBackgroundColour(self.bgcolour)

        self.Parent.change_selection(self.selection)
        if self.callname != old_callname:
            self._show_controls()
            self._do_layout()

        self._enable_updown()

        if self.callname == "CARDPOCKETB":
            self.closebtn.SetLabel(cw.cwpy.msgs["return"])
        else:
            self.closebtn.SetLabel(cw.cwpy.msgs["close"])

        self._update_cardpocketinfo(cw.cwpy.setting.last_cardpocket)

        self.Thaw()

    def _update_cardpocketinfo(self, pocket: int, force: bool = False) -> None:
        if self._can_open_cardpocket and (pocket != self._cardpocketinfo or force):
            self._cardpocketinfo = pocket
            updated = False
            for icombo in range(self.combo.GetCount()):
                if icombo in self._combo_cast:
                    index = self._combo_cast[icombo]
                    castdata = self.list2[index]
                    if pocket in (-1, cw.POCKET_PERSONAL):
                        s = castdata.name
                    else:
                        s = "%s(%s/%s)" % (castdata.name, len(castdata.cardpocket[pocket]),
                                           castdata.get_cardpocketspace()[pocket])
                    if self.combo.GetString(icombo) != s:
                        self.combo.SetString(icombo, s)
                        updated = True
                elif icombo in self._combo_personal:
                    index = self._combo_personal[icombo]
                    castdata = self.list2[index]
                    s = "%s(%s/%s)" % (cw.cwpy.msgs["send_to_personal"] % castdata.name,
                                       len(castdata.personal_pocket),
                                       castdata.get_personalpocketspace())
                    if self.combo.GetString(icombo) != s:
                        self.combo.SetString(icombo, s)
                        updated = True
            if updated:
                self.combo.Refresh()

    def update_cardpocketinfo_with(self, header: Optional[cw.header.CardHeader]) -> None:
        if not self._can_open_cardpocket:
            return
        if self.callname == "CARDPOCKET":
            return
        if header:
            if header.type == "SkillCard":
                pocket = cw.POCKET_SKILL
            elif header.type == "ItemCard":
                pocket = cw.POCKET_ITEM
            elif header.type == "BeastCard":
                pocket = cw.POCKET_BEAST
            else:
                assert False
        else:
            pocket = -1
        if pocket != self._cardpocketinfo:
            self._update_cardpocketinfo(pocket)

    def _enable_updown(self) -> None:
        # リストが空か1ページ分しかなかったら上下ボタンを無効化
        if self.callname == "CARDPOCKET" or len(self.list) <= 10:
            self.upbtn.Disable()
            self.downbtn.Disable()
        else:
            self.upbtn.Enable()
            self.downbtn.Enable()

    def _show_controls(self) -> None:
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            self.skillbtn.Show()
            self.itembtn.Show()
            self.beastbtn.Show()
            if self.is_showpersonal():
                self.personalbtn.Show()
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
            if self.callname != "INFOVIEW":
                self.skillbtn.Hide()
                self.itembtn.Hide()
                self.beastbtn.Hide()
                self.personalbtn.Hide()

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
            assert isinstance(btn, wx.Control)
            btn.Show(self.callname in ("BACKPACK", "STOREHOUSE") and cw.cwpy.setting.show_additional_card)

        # 追加的コントロールの表示有無
        if self.addctrlbtn:
            self.addctrlbtn.Show(cw.cwpy.setting.show_addctrlbtn and self.callname in ("STOREHOUSE", "BACKPACK",
                                                                                       "CARDPOCKETB", "INFOVIEW"))

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
        elif sorttype == "Aptitude":
            self.sort.Select(7)
        else:
            self.sort.Select(0)

    def _update_page(self) -> None:
        index = self.index
        maxval = (len(self.list)+9)//10 if len(self.list) > 0 else 1
        index = min(index, maxval-1)
        page = index+1
        self._on_pagenum(page)
        self.index = index
        self._proc_page = True
        self.page.SetMax(maxval)
        self.page.SetValue(page)
        self._proc_page = False

    def _set_backpacklist(self, narrow: bool = True) -> None:
        if cw.cwpy.setting.last_cardpocket == cw.POCKET_SKILL:
            cardtype = "SkillCard"
        elif cw.cwpy.setting.last_cardpocket == cw.POCKET_ITEM:
            cardtype = "ItemCard"
        else:
            assert cw.cwpy.setting.last_cardpocket == cw.POCKET_BEAST
            cardtype = "BeastCard"
        self.list = [header for header in cw.cwpy.ydata.party.backpack if header.type == cardtype and
                     not (self.is_showpersonal() and header.personal_owner)]
        if narrow:
            self.list = self._narrow(self.list)

    def lclick_event(self, header: cw.header.CardHeader) -> None:
        header.negaflag = False
        owner = self.selection

        if self.callname == "CARDPOCKET" and self.get_mode() == CCMODE_MOVE and owner.reversed and\
                not self.personalbtn.GetToggle():
            s = cw.cwpy.msgs["move_failed_reversed"] % owner.name
            self.show_errordialog(s)

        elif self.callname == "CARDPOCKETB" or (self.callname == "CARDPOCKET" and
                                                self.personalbtn.GetToggle() and self.get_mode() == CCMODE_USE):
            if not self.check_using(owner, header):
                self.draw_cards()
                return

            # 一時的に取り出す
            cw.cwpy.card_takenouttemporarily = header
            if header.personal_owner:
                cw.cwpy.card_takenouttemporarily_personal_owner = header.personal_owner
                cw.cwpy.card_takenouttemporarily_personal_index = header.personal_owner.personal_pocket.index(header)
            cw.cwpy.trade("PLAYERCARD", header=header, target=owner, from_event=False, parentdialog=self, sound=False,
                          call_predlg=False)
            CardControl.lclick_event(self, header)

        elif header.type == "UseCardInBackpack":
            if owner.is_inactive():
                s = cw.cwpy.msgs["inactive"] % owner.name
                self.show_errordialog(s)
                self.draw_cards()
                return
            old_callname = self.callname
            self.callname = "CARDPOCKETB"
            self._change_callname(old_callname)
            self.draw_cards()

        else:
            CardControl.lclick_event(self, header)

    def OnClickToggleBtn(self, event: wx.lib.buttons.GenButtonEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("click")

        seq = (self.skillbtn, self.itembtn, self.beastbtn, self.personalbtn)
        for index, btn in enumerate(seq):
            if btn == event.GetEventObject():
                cw.cwpy.setting.last_cardpocket = index
                btn.SetToggle(True)
            else:
                btn.SetToggle(False)

        self.draw_cards()
        self._update_cardpocketinfo(cw.cwpy.setting.last_cardpocket)

    def OnUp(self, event):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 特殊技能、アイテム、召喚獣を切り替え
            self._cancel_animation = True
            seq = [self.skillbtn, self.itembtn, self.beastbtn]
            if self.personalbtn.IsShown():
                seq.append(self.personalbtn)
            btn = seq[cw.cwpy.setting.last_cardpocket - 1]\
                if not cw.cwpy.setting.last_cardpocket == 0 else seq[len(seq) - 1]
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
            btnevent.SetEventObject(btn)
            self.ProcessEvent(btnevent)
        elif self.upbtn.IsShown() and self.upbtn.IsEnabled():
            self._cancel_animation = True
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.upbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnDown(self, event):
        if self.callname == "CARDPOCKET":
            # キャストの手札カード
            # 特殊技能、アイテム、召喚獣を切り替え
            self._cancel_animation = True
            seq = [self.skillbtn, self.itembtn, self.beastbtn]
            if self.personalbtn.IsShown():
                seq.append(self.personalbtn)
            btn = seq[cw.cwpy.setting.last_cardpocket + 1]\
                if not cw.cwpy.setting.last_cardpocket == len(seq) - 1 else seq[0]
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
            btnevent.SetEventObject(btn)
            self.ProcessEvent(btnevent)
        elif self.upbtn.IsShown() and self.downbtn.IsEnabled():
            self._cancel_animation = True
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.downbtn.GetId())
            self.ProcessEvent(btnevent)

    def OnClickUpBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("click")
        negaindex = -1

        for index, header in enumerate(self.get_headers()):
            if header.negaflag:
                header.negaflag = False
                negaindex = index

        n = (len(self.list)+9)//10 if len(self.list) > 0 else 1

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

    def OnClickDownBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("click")
        negaindex = -1

        for index, header in enumerate(self.get_headers()):
            if header.negaflag:
                header.negaflag = False
                negaindex = index

        n = (len(self.list)+9)//10 if len(self.list) > 0 else 1

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

    def OnPageNum(self, event: wx.lib.intctrl.IntUpdatedEvent) -> None:
        if self._proc_page:
            return
        if self.page.GetValue() < self.page.GetMin():
            return
        if self.page.GetMax() < self.page.GetValue():
            return
        index = self.page.GetValue()-1
        if self.index != index:
            self._cancel_animation = True
            cw.cwpy.play_sound("page")
            self._on_pagenum(index+1)

    def _on_pagenum(self, page: int) -> None:
        index = page-1
        negaindex = -1
        if not negaindex == -1:
            for index, header in enumerate(self.get_headers()):
                if index == negaindex:
                    header.negaflag = True
        self.index = index
        self.draw_cards()

    def OnMouseWheel(self, event: wx.MouseEvent) -> None:
        if cw.util.has_modalchild(self):
            return

        self._cancel_animation = True
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
                seq = [self.skillbtn, self.itembtn, self.beastbtn]
                if self.personalbtn.IsShown():
                    seq.append(self.personalbtn)
                if cw.util.get_wheelrotation(event) > 0:
                    btn = seq[cw.cwpy.setting.last_cardpocket - 1]\
                        if not cw.cwpy.setting.last_cardpocket == 0 else seq[len(seq) - 1]
                else:
                    btn = seq[cw.cwpy.setting.last_cardpocket + 1]\
                        if not cw.cwpy.setting.last_cardpocket == len(seq) - 1 else seq[0]
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

    def draw_cards(self, update: bool = True, mode: int = -1) -> None:
        if self.callname in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            if (len(self.list)+9) // 10 <= self.index:
                self.index = (len(self.list)+9) // 10 - 1
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

    def _init_cardpocketlist(self) -> None:
        if self.callname != "CARDPOCKET":
            return

        if cw.cwpy.setting.last_cardpocket == cw.POCKET_PERSONAL and not (cw.cwpy.setting.show_personal_cards and
                                                                          cw.cwpy.sdata.party_environment_backpack):
            cw.cwpy.setting.last_cardpocket = cw.POCKET_SKILL
        if cw.cwpy.setting.last_cardpocket == cw.POCKET_PERSONAL and cw.cwpy.setting.show_personal_cards and\
                isinstance(self.selection, cw.character.Player):
            self.list = self.selection.personal_pocket[:]
        else:
            self.list = self.selection.cardpocket[cw.cwpy.setting.last_cardpocket][:]
            if cw.cwpy.sdata.party_environment_backpack and cw.cwpy.setting.show_backpackcard and\
                    cw.cwpy.setting.last_cardpocket != cw.POCKET_SKILL and self.get_mode() == CCMODE_USE:
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

    def get_headers(self) -> List[cw.header.CardHeader]:
        li = self.index * 10
        clist = self.list[li:li + 10]
        return clist

    def is_showpersonal(self) -> bool:
        return cw.cwpy.setting.show_personal_cards and cw.cwpy.sdata.party_environment_backpack and\
               (isinstance(self.selection, cw.character.Player) or self.callname in ("BACKPACK", "STOREHOUSE"))

    def get_beforepageheaders(self) -> List[cw.header.CardHeader]:
        if 0 < self.index:
            index = self.index-1
            li = index * 10
            clist = self.list[li:li + 10]
        else:
            clist = []
        return clist

    def _narrow(self, clist: List[cw.header.CardHeader]) -> List[cw.header.CardHeader]:
        self._fulllist = clist
        if self.callname not in ("STOREHOUSE", "BACKPACK", "CARDPOCKETB", "INFOVIEW"):
            return self._fulllist
        if cw.cwpy.setting.show_additional_card:
            narrow = self.narrow.GetValue().lower()
        else:
            narrow = ""
        ntype = self.narrow_type.GetSelection()

        show = [True] * 3
        if self.callname in ("STOREHOUSE", "BACKPACK"):
            for cardtype, btn in enumerate(self.show):
                assert isinstance(btn, wx.lib.buttons.ThemedGenBitmapToggleButton)
                show[cardtype] = btn.GetToggle()

        if not narrow and all(show):
            if self.callname == "BACKPACK" and self.is_showpersonal():
                return list(filter(lambda header: not header.personal_owner, self._fulllist))
            else:
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
                if self.callname != "CARDPOCKET" and self.is_showpersonal() and header.personal_owner:
                    continue
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

    def update_narrowcondition(self) -> None:
        if not self._update_sortattr(draw=False):
            self.list = self._narrow(self._fulllist)
        self._update_page()
        self.draw_cards()

    def _replace_position_impl(self, header1: cw.header.CardHeader, header2: cw.header.CardHeader) -> None:
        if self.callname in ("BACKPACK", "CARDPOCKETB"):
            seq = cw.cwpy.ydata.party.backpack
        elif self.callname == "STOREHOUSE":
            seq = cw.cwpy.ydata.storehouse
        elif self.callname == "CARDPOCKET":
            if self.personalbtn.GetToggle():
                self.selection.replace_personalcardposition(header1, header2)
            else:
                seq = self.selection.cardpocket[cw.cwpy.setting.last_cardpocket]
                self.selection.replace_cardposition(cw.cwpy.setting.last_cardpocket, header1, header2)
            return
        else:
            assert False, self.callname
        if seq is self.list:
            return
        index1 = seq.index(header1)
        index2 = seq.index(header2)
        seq[index2] = header1
        seq[index1] = header2


# ------------------------------------------------------------------------------
# 戦闘手札カードダイアログ
# ------------------------------------------------------------------------------

class HandView(CardControl):
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        self.callname = "HANDVIEW"

        # ダイアログ作成
        CardControl.__init__(self, parent)

        # 手札再配布
        bmp = cw.cwpy.rsrc.dialogs["HAND"]
        self.redeal = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, cw.wins((24, 24)), bmp=bmp)
        self.redeal.SetToolTip(cw.cwpy.msgs["re_deal"])

        # layout
        self._do_layout()
        # bind
        self._bind()

    def reconstruct_handview(self, selection: "cw.sprite.card.CWPyCard",
                             pre_info: Optional[Tuple[str, Optional[int], wx.Point, Union[int, float]]] = None) -> None:
        self.owner = selection

        # カードリスト
        self._update_cardlist(selection)

        # 前に開いていたときのindex値があったら取得する
        self.index = 0
        if pre_info:
            self.pre_pos = pre_info[2]
            self.index2 = pre_info[1]
            if cw.UP_WIN != pre_info[3]:
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
        CardControl.reconstruct(self, self.callname, name, False, False, None)
        # 選択中カード色反転
        self.Parent.change_selection(self.selection)

        # 手札再配布
        self.redeal.Show(cw.cwpy.is_debugmode())

        # 使用モードでパーティが一人だけの場合は左右ボタンを無効化
        if len(self.list2) == 1:
            self.rightbtn.Disable()
            self.leftbtn.Disable()

    def _do_layout(self) -> None:
        CardControl._do_layout(self)
        if self.redeal:
            cwidth = cw.wins(520)
            x = cwidth - cw.wins(5)
            y = cw.wins(0)
            x -= cw.wins(24)
            self.redeal.SetPosition((x, y))
            self.redeal.SetSize(cw.wins((24, 24)))

    def _bind(self) -> None:
        CardControl._bind(self)
        if self.redeal:
            self.Bind(wx.EVT_BUTTON, self.OnReDeal, self.redeal)

    def update_debug(self):
        if not cw.cwpy.is_debugmode():
            if isinstance(self.selection, cw.character.Friend):
                self.Close()
                return
            if self.selection.is_autoselectedpenalty():
                self.Close()
                return
        self._update_cardlist(self.selection)
        CardControl.update_debug(self)
        if self._update_enemylist(self.selection):
            self.redeal.Show(cw.cwpy.is_debugmode())
            self.rightbtn.Enable(len(self.list2) != 1)
            self.leftbtn.Enable(len(self.list2) != 1)
            self.Refresh()

    def _update_cardlist(self, selection: cw.character.Character) -> None:
        status = "active"
        if isinstance(selection, cw.character.Player):
            self.list2 = cw.cwpy.get_pcards(status)
        elif isinstance(selection, cw.character.Friend):
            self.list2 = cw.cwpy.get_fcards(status)
        else:  # EnemyCard
            self._update_enemylist(selection)

        if status == "active" and not cw.cwpy.is_debugmode() and isinstance(self.owner, cw.sprite.card.PlayerCard):
            self.list2 = [pcard for pcard in self.list2 if not pcard.is_autoselectedpenalty()]
        self.list2 = [pcard for pcard in self.list2 if pcard.deck.hand]

    def _update_enemylist(self, selection: "cw.sprite.card.EnemyCard") -> bool:
        if isinstance(selection, cw.character.Enemy):
            if cw.cwpy.is_debugmode():
                self.list2 = cw.cwpy.get_ecards("active")
            else:
                self.list2 = []
                for card in cw.cwpy.get_ecards("active"):
                    if card.is_analyzable():
                        self.list2.append(card)
            if selection not in self.list2:
                self.Close()
                return False
        return True

    def OnReDeal(self, event):
        self._cancel_animation = True
        if self.selection.is_inactive():
            cw.cwpy.play_sound("error")
            return
        cw.cwpy.play_sound("dump")

        self.selection.deck.throwaway()
        self.selection.deck.draw(self.selection)

        self.list = self.selection.deck.hand
        for header in self.list:
            header.negaflag = False
        self.draw_cards(update=True)

    def OnClickLeftBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[0]:
            self.index2 = self.list2[-1]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) - 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def OnClickRightBtn(self, event: wx.PyCommandEvent) -> None:
        self._cancel_animation = True
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[-1]:
            self.index2 = self.list2[0]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) + 1]

        self.selection = self.index2
        self.Parent.change_selection(self.selection)
        self.draw_cards()

    def draw_cards(self, update: bool = True, mode: int = -1) -> None:
        if self.selection:
            self.list = self.selection.deck.hand
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))
        CardControl.draw_cards(self, update, mode)

    def get_headers(self) -> List[cw.header.CardHeader]:
        return self.list

    def _draw_additionals(self, dc: wx.DC) -> None:
        if self.redeal and self.redeal.IsShown():
            fh = dc.GetTextExtent("#")[1]
            fy = (cw.wins(24) - fh) // 2
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14)))
            s = cw.cwpy.msgs["re_deal_label"]
            x = self.redeal.GetPosition()[0] - dc.GetTextExtent(s)[0] - cw.wins(2)
            dc.DrawText(s, x, fy)


# ------------------------------------------------------------------------------
# カード交換ダイアログ
# ------------------------------------------------------------------------------

class ReplCardHolder(CardControl):
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        self.callname = "CARDPOCKET_REPLACE"

        # ダイアログ作成
        CardControl.__init__(self, parent)

        # layout
        self._do_layout()
        # bind
        self._bind()

    def reconstruct_replcardholder(self, selection: "cw.sprite.card.PlayerCard", target: "cw.header.CardHeader",
                                   personal: bool):
        self.owner = selection
        self.target = target
        self.personal = personal

        if target.type == "SkillCard":
            self.cardtype = cw.POCKET_SKILL
        elif target.type == "ItemCard":
            self.cardtype = cw.POCKET_ITEM
        elif target.type == "BeastCard":
            self.cardtype = cw.POCKET_BEAST

        # カードリスト
        status = "" if personal else "unreversed"
        self.list2 = cw.cwpy.get_pcards(status)
        if personal:
            self.list2 = [pcard for pcard in self.list2 if pcard.personal_pocket]
        else:
            self.list2 = [pcard for pcard in self.list2 if pcard.cardpocket[self.cardtype]]

        # 前に開いていたときのindex値があったら取得する
        self.index = 0
        self.selection = selection
        self.index2 = self.selection

        # 手札リスト
        if personal:
            self.list = self.selection.personal_pocket
        else:
            self.list = self.selection.cardpocket[self.cardtype]

        # ダイアログ作成
        if personal:
            name = cw.cwpy.msgs["personal_cards"] % (self.selection.name)
        else:
            name = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
        r, g, b = cw.cwpy.setting.trademode_cardholder_color
        self.bgcolour = wx.Colour(r, g, b)
        CardControl.reconstruct(self, self.callname, name, False, False, None)
        # 選択中カード色反転
        if self.Parent is cw.cwpy.frame:
            self.Parent.change_selection(self.selection)

        # 使用モードでパーティが一人だけの場合は左右ボタンを無効化
        if len(self.list2) == 1:
            self.rightbtn.Disable()
            self.leftbtn.Disable()

    def _bind(self) -> None:
        CardControl._bind(self)

    def OnClickLeftBtn(self, event):
        self._cancel_animation = True
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[0]:
            self.index2 = self.list2[-1]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) - 1]

        self.selection = self.index2
        if self.Parent is cw.cwpy.frame:
            self.Parent.change_selection(self.selection)
        self.draw_cards()

    def OnClickRightBtn(self, event):
        self._cancel_animation = True
        cw.cwpy.play_sound("page")

        if self.index2 == self.list2[-1]:
            self.index2 = self.list2[0]
        else:
            self.index2 = self.list2[self.list2.index(self.index2) + 1]

        self.selection = self.index2
        if self.Parent is cw.cwpy.frame:
            self.Parent.change_selection(self.selection)
        self.draw_cards()

    def draw_cards(self, update: bool = True, mode: int = -1) -> None:
        if self.selection:
            if self.personal:
                self.list = self.selection.personal_pocket
                s = cw.cwpy.msgs["personal_cards"] % (self.selection.name)
            else:
                self.list = self.selection.cardpocket[self.cardtype]
                s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))
        CardControl.draw_cards(self, update, mode)

    def get_headers(self) -> List[cw.header.CardHeader]:
        if self.cardtype == cw.POCKET_BEAST and not self.personal:
            return [c for c in self.list if c.attachment]
        return self.list

    def lclick_event(self, header: cw.header.CardHeader) -> None:
        if self._proc:
            return
        header.negaflag = False
        self.toppanel.SetFocusIgnoringChildren()

        def func(target, header, index, selection, personal, call_predlg):
            owner = target.get_owner()
            personal_owner = target.personal_owner
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
                fromindex = owner.cardpocket[self.cardtype].index(target)
                cw.cwpy.trade(targettype="BACKPACK", header=target, from_event=False, sound=False,
                              sort=False, call_predlg=False)
            elif personal_owner:
                fromindex = -1
                personal_index = personal_owner.personal_pocket.index(target)
                personal_owner.remove_personalpocket(target)
            else:
                fromindex = index

            insertorder = target.order
            if header.personal_owner:
                header.personal_owner.remove_personalpocket(header)
            cw.cwpy.trade(targettype=fromtype, target=owner, header=header, toindex=fromindex, insertorder=insertorder,
                          from_event=False, sound=False, sort=False, call_predlg=False)
            if personal_owner:
                assert fromtype == "BACKPACK"
                personal_owner.add_personalpocket(header, personal_index)
            if personal:
                cw.cwpy.trade(targettype="BACKPACK", header=target,
                              from_event=False, sound=False, sort=False, call_predlg=False)
                selection.add_personalpocket(target, index)
            else:
                cw.cwpy.trade(targettype="PLAYERCARD", target=selection, header=target, toindex=index,
                              from_event=False, sound=False, sort=True, call_predlg=False)
            if personal_owner or personal:
                cw.cwpy.ydata.party.sort_backpack()
            if call_predlg:
                cw.cwpy.exec_func(cw.cwpy.call_predlg)

        if header.type != self.target.type and (isinstance(header.get_owner(), cw.character.Player) or
                                                isinstance(self.target.get_owner(), cw.character.Player)):
            s = cw.cwpy.msgs["replace_failed_different_card_type"]
            self.show_errordialog(s)
            self.draw_cards()
            return

        index = self.list.index(header)
        call_predlg = self.Parent is cw.cwpy.frame
        cw.cwpy.exec_func(func, self.target, header, index, self.selection, self.personal, call_predlg)

        # OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def _replace_position_impl(self, header1, header2):
        self.owner.replace_cardposition(self.cardtype, header1, header2)


# ------------------------------------------------------------------------------
# 情報カードダイアログ
# ------------------------------------------------------------------------------

class InfoView(CardHolder):
    def __init__(self, parent: wx.TopLevelWindow) -> None:
        # ダイアログ作成
        CardHolder.__init__(self, parent, "INFOVIEW")

    def reconstruct_infoview(self):
        CardHolder.reconstruct_cardholder(self, "INFOVIEW", None)

    def is_showpersonal(self):
        return False

    def OnLeftUp(self, event: wx.MouseEvent) -> None:
        self.OnRightUp(event)


def get_spacer_x(mode: int) -> int:
    """
    カード間の隙間の幅を返す。
    """
    if mode == 1:
        return cw.wins(4)
    else:
        return cw.wins(3)


def get_poslist(num: int, mode: int = 1) -> List[Tuple[int, int]]:
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

        for cnt in range(num):
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
            x = (w - cw.wins(83) * num) // 2 + leftm
            y = cw.wins(95)
            poslist = [(x + (cw.wins(83) * cnt), y) for cnt in range(num)]
        else:
            row1, row2 = num // 2 + num % 2, num // 2
            x = (w - cw.wins(83) * row1) // 2 + leftm
            y = cw.wins(40)
            row1list = [(x + (cw.wins(83) * cnt), y) for cnt in range(row1)]
            x = (w - cw.wins(83) * row2) // 2 + leftm
            y = cw.wins(160)
            row2list = [(x + (cw.wins(83) * cnt), y) for cnt in range(row2)]
            poslist = row1list + row2list

    return poslist


def main():
    pass


if __name__ == "__main__":
    main()
