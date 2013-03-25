#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wx.combo
import wx.lib.buttons
import pygame.time

import cw
import cardinfo
import message

#-------------------------------------------------------------------------------
# カード操作ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CardControl(wx.Dialog):
    def __init__(self, parent, name, sendto, sort):
        # ダイアログ作成
        wx.Dialog.__init__(self, parent, -1, "%s - %s" % (cw.cwpy.msgs["card_control"], name),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (90, 24), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (30, 30), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (30, 30), bmp=bmp)
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(500, 255))
        self.toppanel.SetBackgroundColour(self.bgcolour)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, (20, 20), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn2 = cw.cwpy.rsrc.create_wxbutton(self.toppanel, -1, (20, 20), bmp=bmp)
        # sort
        self.sort = wx.combo.BitmapComboBox(self.toppanel, size=(60, 20), style=wx.CB_READONLY)
        self.sort.Append(cw.cwpy.msgs["sort_no"])
        self.sort.Append(cw.cwpy.msgs["sort_name"])
        self.sort.Append(cw.cwpy.msgs["sort_level"])
        self.sort.Append(cw.cwpy.msgs["sort_type"])
        self.sort.Append(cw.cwpy.msgs["sort_price"])
        if not sort:
            self.sort.Freeze()
        # sendto
        self.combo = wx.combo.BitmapComboBox(self.toppanel, size=(110, 20), style=wx.CB_READONLY)
        if not sendto:
            self.leftbtn2.Hide()
            self.rightbtn2.Hide()
            self.combo.Hide()
        # focus
        self.panel.SetFocusIgnoringChildren()

        self._proc = False

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn2, self.leftbtn2)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn2, self.rightbtn2)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_COMBOBOX, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_MOTION, self.OnMove)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.toppanel.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.toppanel.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)

        self.leftkeyid = wx.NewId()
        self.rightkeyid = wx.NewId()
        self.upid = wx.NewId()
        self.downid = wx.NewId()
        self.returnkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.rightkeyid)
        self.Bind(wx.EVT_MENU, self.OnKeyDown, id=self.returnkeyid)
        self.Bind(wx.EVT_MENU, self.OnUp, id=self.upid)
        self.Bind(wx.EVT_MENU, self.OnDown, id=self.downid)
        accel = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, self.leftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.rightkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_UP, self.upid),
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, self.downid),
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, self.returnkeyid),
        ])
        self.SetAcceleratorTable(accel)

    def _do_layout(self, sizer_leftbar):
        """
        引数に子クラスで設定したsizer_leftbarが必要
        """
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_toppanel = wx.GridBagSizer(1, 1)
        sizer_topbar = wx.BoxSizer(wx.HORIZONTAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)
        # トップバー
        sortsize = self.sort.GetSize()
        combosize = self.combo.GetSize()
        sizer_topbar.SetMinSize(combosize)
        sizer_topbar.Add((500-combosize[0]-60-sortsize[0]-40, 0), 0, 0, 0)
        sizer_topbar.Add(self.sort, 0, 0, 0)
        sizer_topbar.Add((60, 0), 0, 0, 0)
        sizer_topbar.Add(self.leftbtn2, 0, 0, 0)
        sizer_topbar.Add(self.combo, 0, 0, 0)
        sizer_topbar.Add(self.rightbtn2, 0, 0, 0)
        # トップパネルにトップバーとレフトバーを設定
        sizer_toppanel.Add(sizer_topbar, (0,0), (1,2), wx.EXPAND)
        sizer_toppanel.Add(sizer_leftbar, (1,0), (1,1), wx.EXPAND)
        sizer_toppanel.Add((420, 235), (1,1), (1,1), wx.EXPAND)
        self.toppanel.SetSizer(sizer_toppanel)
        # ボタンバー
        width = self.toppanel.GetClientSize()[0] - 6
        margin = (width - 60 - self.closebtn.GetSize()[0]) / 2
        margin2 = margin + ((width - 60 - self.closebtn.GetSize()[0]) % 2)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_panel.Add((margin2, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)
        # トップパネルとボタンバーのサイザーを設定
        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def OnSort(self, event):
        pass

    def OnUp(self, event):
        pass

    def OnDown(self, event):
        pass

    def OnKeyDown(self, event):
        if self._proc:
            return

        dc = wx.ClientDC(self.toppanel)
        id = event.GetId()

        list = None
        if id == self.returnkeyid:
            for header in self.get_headers():
                if header.negaflag:
                    cw.cwpy.sounds["click"].play()
                    self.animate_click(header)
                    self.lclick_event(header)
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

        if c1:
            c1.negaflag = False
            self.draw_card(dc, c1, True)
        if c2:
            c2.negaflag = True
            self.draw_card(dc, c2, True)

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

        for header in self.get_headers():
            if header.rect.collidepoint(event.GetPosition()):
                cw.cwpy.sounds["click"].play()
                self.animate_click(header)
                self.lclick_event(header)
                return

    def OnRightUp(self, event):
        if self._proc:
            return

        cw.cwpy.sounds["click"].play()

        for header in self.get_headers():
            if header.rect.collidepoint(event.GetPosition()):
                self.animate_click(header)
                dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                return

        # キャンセルボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnMove(self, event):
        dc = wx.ClientDC(self.toppanel)
        mousepos = event.GetPosition()

        for header in self.get_headers():
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
            for header in self.get_headers():
                if header.negaflag:
                    header.negaflag = False
                    dc = wx.ClientDC(self.toppanel)
                    self.draw_card(dc, header)

    def OnPaint(self, event):
        self.draw()

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

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetSize())
        else:
            dc = wx.PaintDC(self.toppanel)

        # 背景色
        dc.SetBrush(wx.Brush(self.bgcolour))
        dc.DrawRectangle(0, 0, 505, 260)
        # 背景の透かし
        bmp = cw.cwpy.rsrc.dialogs["PAD"]
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, (500-size[0])/2, (255-size[1])/2, True)
        # ライン
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DHIGHLIGHT)
        dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
        dc.DrawLine(1, 20, 499, 20)
        colour = wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DSHADOW)
        dc.SetPen(wx.Pen(colour, 1, wx.SOLID))
        dc.DrawLine(1, 21, 499, 21)
        # 移動モード見出し
        dc.SetTextForeground(wx.LIGHT_GREY)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=11))
        if self.callname == "INFOVIEW" or\
            (self.callname == "CARDPOCKET" and isinstance(self.selection, cw.character.Friend)) or\
            (self.callname == "HANDVIEW" and not cw.cwpy.debug and isinstance(self.selection, (cw.character.Enemy, cw.character.Friend))):
            s = cw.cwpy.msgs["mode_show"]
        elif cw.cwpy.areaid in cw.AREAS_TRADE:
            s = cw.cwpy.msgs["mode_move"]
        elif self.callname == "HANDVIEW":
            s = cw.cwpy.msgs["mode_battle"]
        else:
            s = cw.cwpy.msgs["mode_use"]
        dc.DrawText(s, 8, 2)
        if not self.sort.IsFrozen():
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=10))
            s = cw.cwpy.msgs["sort_title"]
            dc.DrawText(s, 190, 3)
        if self.combo.IsShown():
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=10))
            s = cw.cwpy.msgs["send_to"]
            dc.DrawText(s, 300, 3)
        return dc

    def draw_cards(self, dc, update, mode):
        poslist = get_poslist(len(self.get_headers()), mode)

        for pos, header in zip(poslist, self.get_headers()):
            header.rect.topleft = pos
            self.draw_card(dc, header)

    def draw_card(self, dc, header, fromkeyevent=False):
        if not fromkeyevent and self.IsActive():
            mousepos = self.ScreenToClient(wx.GetMousePosition())
            if header.rect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
            elif header.negaflag:
                header.negaflag = False

        pos = header.rect.topleft
        bmp = header.get_cardwxbmp()

        if header.clickedflag:
            image = bmp.ConvertToImage()
            size = image.GetSize()
            image = image.Rescale(size[0]/10*9, size[1]/10*9)
            bmp = image.ConvertToBitmap()
            pos = (pos[0]+4, pos[1]+5)

        dc.DrawBitmap(bmp, pos[0], pos[1], False)

    def set_cardpos(self, mode):
        poslist = get_poslist(len(self.get_headers()), mode)

        for pos, header in zip(poslist, self.get_headers()):
            header.rect.topleft = pos

    def get_headers(self):
        pass

    def animate_click(self, header):
        # クリックアニメーション。4フレーム分。
        header.clickedflag = True
        self.draw(True)
        cw.cwpy.wait_frame(4)
        header.clickedflag = False
        dc = wx.ClientDC(self.toppanel)
        self.draw_card(dc, header)
        header.negaflag = False

    def lclick_event(self, header):
        if self._proc:
            return

        owner = header.get_owner()

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
                        self.draw(True)
                    self._proc = False
                    cw.cwpy.frame.exec_func(func)
                self._proc = True
                cw.cwpy.exec_func(func, header)
                return

        # カード所持者がPlayerCardじゃない場合はカード情報を表示
        if isinstance(self.selection, cw.character.Friend) or\
                (not cw.cwpy.debug and isinstance(owner, (cw.character.Enemy, cw.character.Friend))):
            dlg = cardinfo.YadoCardInfo(self, self.get_headers(), header)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 付帯召喚じゃない召喚獣の破棄確認
        if cw.cwpy.areaid in cw.AREAS_TRADE and\
                        header.type == "BeastCard" and not header.attachment:
            s = cw.cwpy.msgs["confirm_dump"] % (header.name)
            dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            self.Parent.move_dlg(dlg)

            if dlg.ShowModal() == wx.ID_OK:
                cw.cwpy.sounds["dump"].play()
                owner.throwaway_card(header)

            dlg.Destroy()
            self.draw(True)
            return
        elif not cw.cwpy.areaid in cw.AREAS_TRADE and isinstance(owner, cw.character.Character):
            # 行動不能だったら処理中止
            if owner.is_inactive():
                s = cw.cwpy.msgs["inactive"] % owner.name
                dlg = message.ErrorMessage(self, s)
                self.Parent.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                return

            # 使用回数が0以下だったら処理中止
            if header.uselimit <= 0 and not header.type == "BeastCard":
                if not header.type == "ItemCard" or not header.maxuselimit == 0:
                    cw.cwpy.sounds["error"].play()
                    return

            # 戦闘中にペナルティカードを行動選択していたら処理中止
            if cw.cwpy.battle and owner.actiondata and not cw.cwpy.debug:
                headerp = owner.actiondata[1]

                if headerp and headerp.penalty:
                    s = cw.cwpy.msgs["selected_penalty"]
                    dlg = message.ErrorMessage(self, s)
                    self.Parent.move_dlg(dlg)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return

        # カード操作用データ(移動元データ, CardHeader)を設定
        cw.cwpy.selectedheader = header
        # 能力適性表示
        for pcard in cw.cwpy.get_pcards("unreversed"):
            pcard.test_aptitude = header
            pcard.update_image()
        # 開いていたダイアログの情報
        indexes = (self.index, self.index2, self.index3, self.combo.GetSelection())
        cw.cwpy.pre_dialogs.append((self.callname, indexes, self.GetPosition()))
       	# OKボタンイベント
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

#-------------------------------------------------------------------------------
#　カード倉庫or荷物袋or手札カードダイアログ
#-------------------------------------------------------------------------------

class CardHolder(CardControl):
    def __init__(self, parent, callname):
        # タイプ判別
        self.callname = callname

        # 適性表示を除去
        for pcard in cw.cwpy.get_pcards():
            if pcard.test_aptitude:
                pcard.test_aptitude = None
                pcard.update_image()

        # タイプ別初期化(キャストの手札の場合はindex復元後)
        if self.callname == "BACKPACK":
            name = cw.cwpy.msgs["cards_backpack"]
            self.selection = None
            self.list2 = cw.cwpy.get_pcards("unreversed")
            self.bgcolour = wx.Colour(0, 0, 128)
            self.list = cw.cwpy.ydata.party.backpack
            sendto = True
        elif self.callname == "STOREHOUSE":
            name = cw.cwpy.msgs["cards_storehouse"]
            self.selection = None
            self.list2 = cw.cwpy.get_pcards("unreversed")
            self.bgcolour = wx.Colour(0, 69, 0)
            self.list = cw.cwpy.ydata.storehouse
            sendto = True
        elif self.callname == "INFOVIEW":
            name = cw.cwpy.msgs["info_card"]
            self.bgcolour = wx.Colour(0, 0, 128)
            self.list = cw.cwpy.sdata.infocards
            sendto = False

        # 前に開いていたときのindex値と位置があったら取得する
        if cw.cwpy.pre_dialogs:
            pre_info = cw.cwpy.pre_dialogs.pop()
            self.pre_pos = pre_info[2]
            indexs = pre_info[1]
            self.index2 = indexs[1]
            self.index3 = indexs[2]
            self.index_combo = indexs[3]

            if self.callname == "CARDPOCKET":
                self.index = 0
                self.list2 = cw.cwpy.get_pcards("unreversed")
                self.selection = self.index2
            else:
                # カード移動でページ数が減っていたらself.indexを-1
                if len(self.list) % 10 == 0 and len(self.list) / 10 == indexs[0]:
                    self.index = indexs[0] - 1
                else:
                    self.index = indexs[0]

        else:
            self.index = 0
            self.index3 = cw.cwpy.lastcardpocket
            self.index_combo = 0
            if self.callname == "CARDPOCKET":
                self.selection = cw.cwpy.selection
                if isinstance(self.selection, cw.character.Player):
                    # パーティの手札カード(リバースメンバを除く)
                    self.list2 = cw.cwpy.get_pcards("unreversed")
                else:
                    # NPCの手札カード
                    self.list2 = cw.cwpy.get_fcards()
                self.index2 = self.selection
            else:
                self.index2 = cw.cwpy.lastcardpocket

        if self.callname == "CARDPOCKET":
            name =  cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.bgcolour = wx.Colour(0, 0, 128)
            sendto = (not cw.cwpy.is_playingscenario()\
                        or cw.cwpy.areaid == cw.AREA_CAMP)\
                        and isinstance(self.selection, cw.character.Player)
            # self.index3(0:スキル, 1:アイテム, 2:召喚獣)。トグルボタンで切り替える
            self.list = self.selection.cardpocket[self.index3]

        # 左右ボタンでの移動先の有無(情報カードは左右移動無し)
        if self.callname <> "INFOVIEW":
            # キャストの手札
            self._can_open_cardpocket = cw.cwpy.ydata.party and 0 < len(cw.cwpy.ydata.party.members)
            # 荷物袋
            self._can_open_backpack = self._can_open_cardpocket and sendto
            # カード置場
            self._can_open_storehouse = not cw.cwpy.is_playingscenario()

        # ダイアログ作成
        sort = self.callname in ("STOREHOUSE", "BACKPACK")
        CardControl.__init__(self, parent, name, sendto, sort)

        # キャストの手札カード用のコントロール
        # 情報カードダイアログの場合は切り替えが無いため不要
        if self.callname <> "INFOVIEW":
            # skill
            self.skillbtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=(70, 50))
            bmp = cw.cwpy.rsrc.buttons["SKILL"]
            self.skillbtn.SetBitmapLabel(bmp, False)
            self.skillbtn.SetBitmapSelected(bmp)
            # item
            self.itembtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=(70, 50))
            bmp = cw.cwpy.rsrc.buttons["ITEM"]
            self.itembtn.SetBitmapLabel(bmp, False)
            self.itembtn.SetBitmapSelected(bmp)
            # beast
            self.beastbtn = wx.lib.buttons.GenBitmapToggleButton(self.toppanel, -1, None, size=(70, 50))
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
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_UP, (70, 40), bmp=bmp)
        # down
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self.toppanel, wx.ID_DOWN, (70, 40), bmp=bmp)

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
        # 使用モードでパーティが一人だけの場合は左右ボタンを無効化
        if (self.callname == "INFOVIEW")\
                or (not cw.cwpy.ydata.party)\
                or (not sendto and len(cw.cwpy.ydata.party.members) == 1):
            self.rightbtn.Disable()
            self.leftbtn.Disable()

        if self.callname == "CARDPOCKET":
            # キャストの手札カード

            # 最初に開くページのカードのposを設定
            self.set_cardpos(2)
            # 選択中カード色反転
            self.Parent.change_selection(self.selection)

        else:
            # カード置き場、荷物袋、情報カード

            # 最初に開くページのカードのposを設定
            self.set_cardpos(1)
            if self.callname <> "INFOVIEW":
                # 選択中カード色反転
                self.Parent.change_selection(self.selection)

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
            margin = (235-150)/2
            margin2 = margin + (235-150)%2
            self._sizer_leftbar.Add((0, margin), 0, 0, 0)
            self._sizer_leftbar.Add(self.skillbtn, 0, wx.LEFT, 6)
            self._sizer_leftbar.Add(self.itembtn, 0, wx.LEFT, 6)
            self._sizer_leftbar.Add(self.beastbtn, 0, wx.LEFT, 6)
            self._sizer_leftbar.Add((0, margin2), 0, 0, 0)

            self.skillbtn.Show()
            self.itembtn.Show()
            self.beastbtn.Show()
            self.upbtn.Hide()
            self.downbtn.Hide()
        else:
            # カード置き場、荷物袋、情報カード
            self._sizer_leftbar.Add((0, 15), 0, 0, 0)
            self._sizer_leftbar.Add(self.upbtn, 0, wx.LEFT, 6)
            self._sizer_leftbar.Add((0, 235-110), 0, 0, 0)
            self._sizer_leftbar.Add(self.downbtn, 0, wx.LEFT, 6)
            self._sizer_leftbar.Add((0, 15), 0, 0, 0)

            self.upbtn.Show()
            self.downbtn.Show()
            if self.callname <> "INFOVIEW":
                self.skillbtn.Hide()
                self.itembtn.Hide()
                self.beastbtn.Hide()

        self._sizer_leftbar.Layout()

        # ソート条件
        if self.callname == "STOREHOUSE":
            if self.sort.IsFrozen():
                self.sort.Thaw()
            sorttype = cw.cwpy.setting.sort_storehouse
        elif self.callname == "BACKPACK":
            if self.sort.IsFrozen():
                self.sort.Thaw()
            sorttype = cw.cwpy.setting.sort_backpack
        else:
            if not self.sort.IsFrozen():
                self.sort.Freeze()
            sorttype = None

        if not self.sort.IsFrozen():
            if sorttype == "Name":
                self.sort.Select(1)
            elif sorttype == "Level":
                self.sort.Select(2)
            elif sorttype == "Type":
                self.sort.Select(3)
            else:
                self.sort.Select(0)

    def _do_layout(self):
        self._sizer_leftbar = wx.BoxSizer(wx.VERTICAL)

        self._re_layout()

        CardControl._do_layout(self, self._sizer_leftbar)

    def OnDestroy(self, event):
        if self.callname == "CARDPOCKET" or self.callname == "BACKPACK" or self.callname == "STOREHOUSE":
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
        if self.callname == "BACKPACK":
            if cw.cwpy.setting.sort_backpack <> sorttype:
                cw.cwpy.sounds["page"].play()
                cw.cwpy.setting.sort_backpack = sorttype
                cw.cwpy.ydata.party.sort_backpack()
                self.draw(True)
        elif self.callname == "STOREHOUSE":
            if cw.cwpy.setting.sort_storehouse <> sorttype:
                cw.cwpy.sounds["page"].play()
                cw.cwpy.setting.sort_storehouse = sorttype
                cw.cwpy.ydata.sort_storehouse()
                self.draw(True)

    def OnClickLeftBtn(self, event):
        cw.cwpy.sounds["page"].play()
        old_callname = self.callname

        if self.callname == "CARDPOCKET":
            if self.index2 is self.list2[0]:
                if self._can_open_backpack:
                    # 荷物袋 ← 左端
                    self.index = 0
                    self.callname = "BACKPACK"
                    self._change_callname(old_callname)
                else:
                    # 右端 ← 左端
                    self.index2 = self.list2[-1]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
            else:
                # 一つ左のメンバ
                self.index2 = self.list2[self.list2.index(self.index2) - 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
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

        self.draw(True)

    def _change_callname(self, old_callname):
        if self.callname == old_callname:
            return

        if self.callname == "CARDPOCKET":
            self.bgcolour = wx.Colour(0, 0, 128)
            self.toppanel.SetBackgroundColour(self.bgcolour)
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
        self._re_layout()

        if self.callname == "CARDPOCKET" or len(self.list) <= 10:
            self.upbtn.Disable()
            self.downbtn.Disable()
        else:
            self.upbtn.Enable()
            self.downbtn.Enable()

    def OnClickRightBtn(self, event):
        cw.cwpy.sounds["page"].play()
        old_callname = self.callname

        if self.callname == "CARDPOCKET":
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
                    self.index2 = self.list2[0]
                    self.selection = self.index2
                    self.Parent.change_selection(self.selection)
            else:
                # 一つ右のメンバ
                self.index2 = self.list2[self.list2.index(self.index2) + 1]
                self.selection = self.index2
                self.Parent.change_selection(self.selection)
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

        self.draw(True)

    def OnClickToggleBtn(self, event):
        cw.cwpy.sounds["click"].play()

        l = [self.skillbtn, self.itembtn, self.beastbtn]

        for index, btn in enumerate(l):
            if btn == event.GetEventObject():
                self.index3 = index
                btn.SetToggle(True)
            else:
                btn.SetToggle(False)

        self.draw(True)

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

        self.draw(True)

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

        self.draw(True)

    def OnMouseWheel(self, event):
        mousepos = event.GetPosition()
        lpos = self._sizer_leftbar.GetPosition()
        lsize = self._sizer_leftbar.GetSize()
        lwidth = lsize[0] + lpos[0] * 2;
        if not self.sort.IsFrozen() and self.sort.GetRect().Contains(mousepos):
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

    def draw(self, update=False):
        if 0 < self.index and (len(self.list)+9) / 10 <= self.index:
            # 現ページのカードの移動などで
            # 最大ページを超えてしまった場合
            self.index -= 1

        dc = CardControl.draw(self, update)
        if self.callname == "CARDPOCKET":
            # キャストの手札カード

            # 所持カード数
            num = len(self.selection.cardpocket[self.index3])
            maxnum = self.selection.get_cardpocketspace()[self.index3]
            s = "Cap " + str(num) + "/" + str(maxnum)
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, 40-w/2, 220)

            # カード描画
            if update:
                self.list = self.selection.cardpocket[self.index3]
                s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
                self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))

            self.draw_cards(dc, update, 2)
        else:
            # カード置き場、荷物袋、情報カード

            # ページ番号
            s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
            s += "/" + str((len(self.list)+9)/10) if len(self.list) > 0 else "/1"
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, 40-w/2, 180)

            # イメージ
            if self.callname == "BACKPACK":
                path = "Resource/Image/Card/COMMAND7" + cw.cwpy.rsrc.ext_img
            elif self.callname == "STOREHOUSE":
                path = "Resource/Image/Card/COMMAND5" + cw.cwpy.rsrc.ext_img
            elif self.callname == "INFOVIEW":
                path = "Resource/Image/Card/COMMAND8" + cw.cwpy.rsrc.ext_img
            path = cw.util.join_paths(cw.cwpy.skindir, path)
            bmp = cw.util.load_wxbmp(path, True)
            dc.DrawBitmap(bmp, 3, 85, True)

            # カード描画
            self.draw_cards(dc, update, 1)

    def get_headers(self):
        li = self.index * 10
        list = self.list[li:li + 10]
        return list

#-------------------------------------------------------------------------------
#　戦闘手札カードダイアログ
#-------------------------------------------------------------------------------

class HandView(CardControl):
    def __init__(self, parent):
        self.callname = "HANDVIEW"
        self.owner = cw.cwpy.selection

        # カードリスト
        if cw.cwpy.pre_dialogs:
            self.list2 = cw.cwpy.get_pcards("unreversed")
        elif isinstance(cw.cwpy.selection, cw.character.Player):
            self.list2 = cw.cwpy.get_pcards("unreversed")
        else:
            self.list2 = cw.cwpy.get_mcards()

        # 前に開いていたときのindex値があったら取得する
        if cw.cwpy.pre_dialogs:
            pre_info = cw.cwpy.pre_dialogs.pop()
            self.pre_pos = pre_info[2]
            indexs = pre_info[1]
            self.index = indexs[0]
            self.index2 = indexs[1]
            self.index3 = indexs[2]
            self.index_combo = indexs[3]
            self.selection = self.list2[self.index2]
        else:
            self.selection = cw.cwpy.selection
            self.index = 0
            self.index2 = self.list2.index(self.selection)
            self.index3 = 0
            self.index_combo = 0

        # 手札リスト
        self.list = self.selection.deck.hand
        # ダイアログ作成
        name = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
        self.bgcolour = wx.Colour(0, 0, 128)
        CardControl.__init__(self, parent, name, False, False)
        # 最初に開くページのカードのposを設定
        self.set_cardpos(3)
        # 選択中カード色反転
        self.Parent.change_selection(self.selection)
        # layout
        self._do_layout()
        # bind
        self._bind()

    def _bind(self):
        CardControl._bind(self)

    def OnClickLeftBtn(self, event):
        cw.cwpy.sounds["page"].play()

        if self.index2 == 0:
            self.index2 = len(self.list2) -1
        else:
            self.index2 -= 1

        self.selection = self.list2[self.index2]
        self.Parent.change_selection(self.selection)
        self.draw(True)

    def OnClickRightBtn(self, event):
        cw.cwpy.sounds["page"].play()

        if self.index2 == len(self.list2) -1:
            self.index2 = 0
        else:
            self.index2 += 1

        self.selection = self.list2[self.index2]
        self.Parent.change_selection(self.selection)
        self.draw(True)

    def draw(self, update=False):
        dc = CardControl.draw(self, update)

        # カード描画
        if update:
            self.list = self.selection.deck.hand
            s = cw.cwpy.msgs["cards_hand"] % (self.selection.name)
            self.SetTitle("%s - %s" % (cw.cwpy.msgs["card_control"], s))

        self.draw_cards(dc, update, 3)

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
        CardHolder.__init__(self, parent, "INFOVIEW")

def get_poslist(num, mode=1):
    """
    カード描画に使うpositionのリストを返す。
    mode=1は荷物袋・カード置場用。
    mode=2は所持カード用。
    mode=3は戦闘カード用。
    """
    if mode == 1:
        # 描画エリアサイズ
        w, h = 425, 230
        # 左,上の余白
        leftm = 80

        poslist = []

        for cnt in xrange(num):
            if cnt < 5:
                poslist.append((leftm+84*cnt, 25))
            else:
                poslist.append((leftm+84*(cnt-5), 140))

    elif mode == 2:
        # 描画エリアサイズ
        w, h = 425, 230
        # 左,上の余白
        leftm = 80

        if num < 5:
            x = (w - 83 * num) / 2 + leftm
            y = 77
            poslist = [(x + (83 * cnt), y) for cnt in xrange(num)]
        else:
            row1, row2 = num / 2 + num % 2, num / 2
            x = (w - 83 * row1) / 2 + leftm
            y = 27
            row1list = [(x + (83 * cnt), y) for cnt in xrange(row1)]
            x = (w - 83 * row2) / 2 + leftm
            y = 141
            row2list = [(x + (83 * cnt), y) for cnt in xrange(row2)]
            poslist = row1list + row2list

    elif mode == 3:
        # 描画エリアサイズ
        w, h = 505, 230

        if num < 6:
            x = (w - 83 * num) / 2
            y = 77
            poslist = [(x + (83 * cnt), y) for cnt in xrange(num)]
        else:
            row1, row2 = num / 2 + num % 2, num / 2
            x = (w - 83 * row1) / 2
            y = 27
            row1list = [(x + (83 * cnt), y) for cnt in xrange(row1)]
            x = (w - 83 * row2) / 2
            y = 141
            row2list = [(x + (83 * cnt), y) for cnt in xrange(row2)]
            poslist = row1list + row2list

    return poslist

def main():
    pass

if __name__ == "__main__":
    main()
