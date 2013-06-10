#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import wx
import pygame

import cw
import cw.dialog.edit
import cardinfo


#-------------------------------------------------------------------------------
#　キャラクター情報ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CharaInfo(wx.Dialog):
    """
    キャラクター情報ダイアログ
    """
    def __init__(self, parent, redrawfunc, editable):
        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["character_information"], size=cw.s((300, 355)),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.csize = self.GetClientSize()
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.s((85, 24)), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.s((30, 30)), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.s((30, 30)), bmp=bmp)
        # notebook
        self.notebook = wx.Notebook(self, -1, size=cw.s((300, 220)), style=wx.BK_BOTTOM)
        self.notebook.SetFont(cw.cwpy.rsrc.get_wxfont("btnfont"))
        # 解説
        self.descpanel = DescPanel(self.notebook, self.ccard, editable)
        self.notebook.AddPage(self.descpanel, cw.cwpy.msgs["description"])
        # 経歴
        self.historypanel = HistoryPanel(self.notebook, self.ccard, editable)
        self.notebook.AddPage(self.historypanel, cw.cwpy.msgs["history"])
        # 編集または状態
        if self.is_playingscenario:
            self.editpanel = StatusPanel(self.notebook, self.list, self.ccard, editable)
            self.notebook.AddPage(self.editpanel, cw.cwpy.msgs["status"])
        elif editable:
            self.editpanel = EditPanel(self.notebook, self.list, self.ccard)
            self.notebook.AddPage(self.editpanel, cw.cwpy.msgs["edit"])

        # 各種所持カード
        if self.ccard.data.hasfind("SkillCards"):
            # 技能
            self.skillpanel = SkillPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.skillpanel, cw.cwpy.msgs["skills"])
            # アイテム
            self.itempanel = ItemPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.itempanel, cw.cwpy.msgs["items"])
            # 召喚獣
            self.beastpanel = BeastPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.beastpanel, cw.cwpy.msgs["beasts"])

        # toppanel
        self.toppanel = TopPanel(self, self.ccard, redrawfunc)
        # layout
        self._do_layout()
        # bind
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def OnMouseWheel(self, event):
        if self.notebook.GetRect().Contains(event.GetPosition()):
            index = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
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
            self.notebook.SetSelection(index)
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, self.notebook.GetId())
            self.ProcessEvent(btnevent)
        else:
            if event.GetWheelRotation() > 0:
                if self.leftbtn.IsEnabled():
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
                    self.ProcessEvent(btnevent)
            else:
                if self.rightbtn.IsEnabled():
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
                    self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnDestroy(self, event):
        if isinstance(self, StandbyCharaInfo):
            self.ccard.data.write_xml()

    def OnClickLeftBtn(self, event):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        if isinstance(self, StandbyCharaInfo):
            self.ccard.data.write_xml()
            header = self.list[self.index]
            data = cw.data.yadoxml2etree(header.fpath)

            if data.getroot().tag == "Album":
                self.ccard = cw.character.AlbumPage(data)
            else:
                self.ccard = cw.character.Player(data)

            if isinstance(self, StandbyPartyCharaInfo):
                cw.cwpy.sounds["page"].play()
            else:
                self.Parent.OnClickLeftBtn(event)
        else:
            cw.cwpy.sounds["page"].play()
            self.ccard = self.list[self.index]
            self.Parent.change_selection(self.list[self.index])

        self.toppanel.ccard = self.ccard
        self.toppanel.draw(True)

        for win in self.notebook.GetChildren():
            win.ccard = self.ccard
            win.headers = []
            win.draw(True)

    def OnClickRightBtn(self, event):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        if isinstance(self, StandbyCharaInfo):
            self.ccard.data.write_xml()
            header = self.list[self.index]
            data = cw.data.yadoxml2etree(header.fpath)

            if data.getroot().tag == "Album":
                self.ccard = cw.character.AlbumPage(data)
            else:
                self.ccard = cw.character.Player(data)

            if isinstance(self, StandbyPartyCharaInfo):
                cw.cwpy.sounds["page"].play()
            else:
                self.Parent.OnClickRightBtn(event)
        else:
            cw.cwpy.sounds["page"].play()
            self.ccard = self.list[self.index]
            self.Parent.change_selection(self.list[self.index])

        self.toppanel.ccard = self.ccard
        self.toppanel.draw(True)

        for win in self.notebook.GetChildren():
            win.ccard = self.ccard
            win.headers = []
            win.draw(True)

    def OnPageChanged(self, event):
        pass

    def OnPageChanging(self, event):
        cw.cwpy.sounds["click"].play()

    def draw(self, update):
        win = self.notebook.GetCurrentPage()
        dc = wx.ClientDC(win)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))

        for header in win.headers:
            s = header.name

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, header.textpos[0], header.textpos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, header.textpos[0], header.textpos[1])

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        margin = (self.csize[0] - cw.s(145)) / 2 + (self.csize[0] - cw.s(145)) % 2
        margin2 = (self.csize[0] - cw.s(145)) / 2
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.TOP, cw.s(3))
        sizer_panel.Add((margin2, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 0, 0, 0)
        sizer_1.Add(self.notebook, 0, 0, 0)
        sizer_1.Add(self.panel, 0, 0, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

class StandbyCharaInfo(CharaInfo):
    def __init__(self, parent, headers, index, redrawfunc, is_playingscenario=False):
        self.is_playingscenario = is_playingscenario
        self.list = headers
        self.index = index
        header = self.list[self.index]
        data = cw.data.yadoxml2etree(header.fpath)

        if data.getroot().tag == "Album":
            self.ccard = cw.character.AlbumPage(data)
            editable = False
        else:
            self.ccard = cw.character.Player(data)
            editable = True

        CharaInfo.__init__(self, parent, redrawfunc, editable)

class StandbyPartyCharaInfo(StandbyCharaInfo):
    def __init__(self, parent, partyheader, redrawfunc):
        party = cw.data.Party(partyheader, True)
        headers = []
        for memberpath in party.get_memberpaths():
            headers.append(cw.cwpy.ydata.create_advheader(memberpath))

        StandbyCharaInfo.__init__(self, parent, headers, 0, redrawfunc, partyheader.is_adventuring())

class ActiveCharaInfo(CharaInfo):
    def __init__(self, parent):
        self.is_playingscenario = cw.cwpy.is_playingscenario()
        self.ccard = cw.cwpy.selection

        if isinstance(cw.cwpy.selection, cw.character.Player):
            if cw.cwpy.is_debugmode():
                self.list = cw.cwpy.get_pcards()
            else:
                self.list = cw.cwpy.get_pcards("unreversed")
        elif isinstance(cw.cwpy.selection, cw.character.Enemy):
            if cw.cwpy.is_debugmode():
                self.list = cw.cwpy.get_ecards()
            else:
                self.list = cw.cwpy.get_ecards("unreversed")
        else:
            self.list = cw.cwpy.get_fcards()

        self.index = self.list.index(cw.cwpy.selection)
        CharaInfo.__init__(self, parent, None, True)

class TopPanel(wx.Panel):
    """
    顔画像などを描画するパネル
    """
    def __init__(self, parent, ccard, redrawfunc):
        wx.Panel.__init__(self, parent, -1, size=cw.s((300, 100)))
        self.SetDoubleBuffered(True)
        self.csize = self.GetClientSize()
        self.ccard = ccard
        self.redrawfunc = redrawfunc
        self.yadodir = cw.cwpy.yadodir
        # bmp
        self.wing = cw.cwpy.rsrc.dialogs["STATUS"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        # クーポンにある各種変数取得
        if not (isinstance(self.ccard, cw.sprite.card.EnemyCard) or\
                isinstance(self.ccard, cw.sprite.card.FriendCard)):
            ages = set(cw.cwpy.setting.periodcoupons)
            sexs = set(cw.cwpy.setting.sexcoupons)
            self.sex = cw.cwpy.setting.sexes[0].name
            self.age = cw.cwpy.setting.periods[0].name
            self.ep = "0"

            for coupon in self.ccard.data.getfind("Property/Coupons"):
                if coupon.text in ages:
                    self.age = coupon.text.replace(u"＿", "", 1)
                elif coupon.text in sexs:
                    self.sex = coupon.text.replace(u"＿", "", 1)
                elif coupon.text == u"＠ＥＰ":
                    self.ep = coupon.get("value")

        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)
            self.PrepareDC(dc)

        dc.BeginDrawing()
        # カード画像の後ろにある羽みたいなの
        cw.util.draw_height(dc, self.wing, cw.s(25))
        # カード画像
        path = self.ccard.data.gettext("Property/ImagePath", "")
        if not cw.binary.image.path_is_code(path):
            if isinstance(cw.cwpy.selection, (cw.character.Enemy,
                                                cw.character.Friend)):
                path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
            else:
                path = cw.util.join_yadodir(path)

        bmp = cw.s((cw.util.load_wxbmp(path, True), cw.SIZE_CARDIMAGE))
        x = (dc.GetSize()[0] - cw.s(74)) / 2
        dc.DrawBitmap(bmp, x, cw.s(5), True)
        # レベル
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=cw.s(10)))
        coupons = self.ccard.get_specialcoupons()
        if u"＠レベル原点" in coupons and self.ccard.level <> coupons[u"＠レベル原点"]:
            s = "Level: %d / %d" % (self.ccard.level, coupons[u"＠レベル原点"])
        else:
            s = "Level: %d" % (self.ccard.level)
            if u"＠レベル上限" in coupons and coupons[u"＠レベル上限"] <= self.ccard.level:
                # max
                dc.SetTextForeground(wx.RED)
                dc.DrawText("max", cw.s(25), cw.s(20))

        dc.SetTextForeground(wx.BLACK)
        dc.DrawText(s, cw.s(5), cw.s(5))
        # 名前
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=cw.s(11)))
        s = self.ccard.name
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, cw.s(295) - w, cw.s(3))

        if not (isinstance(self.ccard, cw.sprite.card.EnemyCard) or\
                isinstance(self.ccard, cw.sprite.card.FriendCard)):
            # EP
            s = "EP: " + self.ep
            dc.DrawText(s, cw.s(8), cw.s(82))
            # 年代
            s = self.age + self.sex
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, cw.s(295) - w, cw.s(80))
            dc.EndDrawing()

        # 親ウィンドウの再描画を行える場合は呼び出し
        if self.redrawfunc:
            self.redrawfunc()

class DescPanel(wx.Panel):
    """
    解説文を描画するパネル。
    """
    def __init__(self, parent, ccard, editable):
        wx.Panel.__init__(self, parent, -1, size=cw.s((292, 200)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

        if cw.cwpy.debug and editable and isinstance(ccard, cw.sprite.card.PlayerCard):
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def OnLeftUp(self, event):
        cw.cwpy.sounds["click"].play()
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.charaedit.CharacterEditDialog(parent, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            self.Parent.Parent.toppanel.draw(True)
            self.draw(True)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        # 解説文
        self.text = self.ccard.data.gettext("Property/Description", "")
        self.text = cw.util.txtwrap(self.text, 4)

        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)
            self.PrepareDC(dc)

        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)
        # 解説文
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(9)))
        dc.DrawLabel(self.text, cw.s((24, 10, 200, 120)))
        dc.EndDrawing()

class HistoryPanel(wx.ScrolledWindow):
    """
    クーポンを描画するスクロールウィンドウ。
    """
    def __init__(self, parent, ccard, editable):
        wx.ScrolledWindow.__init__(self, parent, -1, size=cw.s((292, 200)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.csize = self.GetClientSize()
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.SetScrollRate(cw.s(10), cw.s(10))
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.gold = cw.cwpy.rsrc.dialogs["STATUS3"]
        self.silver = cw.cwpy.rsrc.dialogs["STATUS2"]
        self.bronze = cw.cwpy.rsrc.dialogs["STATUS1"]
        self.black = cw.cwpy.rsrc.dialogs["STATUS0"]
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)
        # create buffer
        self.draw()

        if cw.cwpy.debug and editable and isinstance(ccard, cw.sprite.card.PlayerCard):
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def OnLeftUp(self, event):
        cw.cwpy.sounds["click"].play()
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.edit.CouponEditDialog(parent, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            def func(panel):
                def func(panel):
                    try:
                        panel.draw(True)
                        panel.Parent.Parent.toppanel.draw(True)
                    except:
                        pass
                cw.cwpy.frame.exec_func(func, panel)
            cw.cwpy.exec_func(func, self)


    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def draw(self, update=False):
        # クーポンリスト
        coupons = []

        for coupon in self.ccard.data.getfind("Property/Coupons"):
            if coupon.text and not coupon.text.startswith(u"＠"):
                if cw.cwpy.debug or (not coupon.text.startswith(u"＿") and\
                                     not coupon.text.startswith(u"：") and\
                                     not coupon.text.startswith(u"；")):
                    coupons.append((coupon.text, int(coupon.get("value"))))

        coupons.reverse()
        # maxheght計算
        h = self.gold.GetSize()[1]
        maxheight = (h + cw.s(5)) * len(coupons) + cw.s(8)
        maxwidth = 0

        # create buffer
        csize = self.csize
        height = maxheight + cw.s(10) if maxheight + cw.s(10) > csize[1] else csize[1]
        self.buffer = wx.EmptyBitmap(csize[0], height)
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        # 背景の透かし
        for cnt in xrange(maxheight / csize[1] + 1):
            height = ((csize[1] - cw.s(132)) / 2) + csize[1] * cnt
            dc.DrawBitmap(self.watermark, (csize[0]-cw.s(226)) / 2, height, True)

        # クーポン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))

        for index, coupon in enumerate(coupons):
            height = cw.s(8) + (h + cw.s(5)) * index
            text, value = coupon
            maxwidth = max(dc.GetTextExtent(text)[0], maxwidth)
            dc.DrawText(text, cw.s(32), height)

            if value > 1:
                dc.DrawBitmap(self.gold, cw.s(12), height - cw.s(1), True)
            elif value == 1:
                dc.DrawBitmap(self.silver, cw.s(12), height - cw.s(1), True)
            elif value == 0:
                dc.DrawBitmap(self.bronze, cw.s(12), height - cw.s(1), True)
            else:
                dc.DrawBitmap(self.black, cw.s(12), height - cw.s(1), True)
        maxwidth += cw.s(32)
        self.SetVirtualSize((maxwidth, maxheight))

        if update:
            self.Scroll(0, 0)
            self.Refresh()

class EditButton():
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.negaflag = False

class EditPanel(wx.Panel):
    def __init__(self, parent, list, ccard):
        wx.Panel.__init__(self, parent, -1, size=cw.s((292, 200)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.list = list
        self.ccard = ccard
        # ボタン
        self.headers = []
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

    def OnLeftUp(self, event):
        for header in self.headers:
            if header.subrect.collidepoint(event.GetPosition()):
                header.negaflag = False
                if header.type == 0:
                    # デザインを変更する
                    cw.cwpy.sounds["click"].play()
                    dlg = cw.dialog.create.AdventurerDesignDialog(self.Parent.Parent, self.ccard)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        self.Parent.Parent.toppanel.draw(True)
                        self.Parent.Parent.descpanel.draw(True)
                    dlg.Destroy()
                else:
                    # レベルを調節する
                    cw.cwpy.sounds["click"].play()
                    list = self.get_charalist()
                    selected = list.index(self.ccard)
                    dlg = cw.dialog.edit.LevelEditDialog(self.Parent.Parent, list=list, selected=selected)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        self.update_charalist(list)
                        self.Parent.Parent.toppanel.draw(True)
                    dlg.Destroy()
                self.draw(True)
                return

    def get_charalist(self):
        """編集用のcw.character.Playerのリストを取得する。"""
        if isinstance(self.Parent.Parent, StandbyPartyCharaInfo):
            seq = []
            for header in self.list:
                if self.ccard.data.fpath == header.fpath:
                    seq.append(self.ccard)
                else:
                    data = cw.data.yadoxml2etree(header.fpath)
                    ccard = cw.character.Player(data)
                    seq.append(ccard)
            return seq
        elif isinstance(self.Parent.Parent, StandbyCharaInfo):
            return [self.ccard]
        else:
            return self.list

    def update_charalist(self, list):
        """編集結果をヘッダ等に反映する。"""
        def func(parent, headers, list):
            if isinstance(parent, StandbyPartyCharaInfo):
                for i, header in enumerate(headers):
                    ccard = list[i]
                    ccard.data.write_xml()
                    header.level = ccard.level
            elif isinstance(parent, StandbyCharaInfo):
                ccard = list[0]
                ccard.data.write_xml()
                headers[parent.index].level = ccard.level
        cw.cwpy.exec_func(func, self.Parent.Parent, self.list, list)

    def OnPaint(self, event):
        self.draw()

    def OnLeave(self, event):
        if not self.Parent.Parent.IsActive():
            return

        for header in self.headers:
            if header.negaflag:
                header.negaflag = False
                dc = wx.ClientDC(self)
                dc.SetTextForeground(wx.WHITE)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])

    def OnMove(self, event):
        dc = wx.ClientDC(self)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))
        mousepos = event.GetPosition()

        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    dc.SetTextForeground(wx.RED)
                    dc.DrawText(header.name, header.textpos[0], header.textpos[1])
                    dc.SetTextForeground(wx.WHITE)
            elif header.negaflag:
                header.negaflag = False
                dc.DrawText(header.name, header.textpos[0], header.textpos[1])

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)

        # 編集ボタン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))
        # 編集アイコン
        bmp = cw.cwpy.rsrc.dialogs["STATUS12"]
        # 編集項目名
        height = cw.s(8)
        if not self.headers:
            self.headers = (EditButton(cw.cwpy.msgs["edit_design"], 0), EditButton(cw.cwpy.msgs["regulate_level"], 1))
        for header in self.headers:
            if header.negaflag:
                dc.SetTextForeground(wx.RED)
            else:
                dc.SetTextForeground(wx.WHITE)
            size = dc.GetTextExtent(header.name)
            dc.DrawBitmap(bmp, cw.s(12), height - cw.s(1), True)
            dc.DrawText(header.name, cw.s(32), height)
            header.textpos = (cw.s(32), height)
            header.subrect = pygame.Rect(cw.s(12), height - cw.s(1), cw.s(20) + size[0], bmp.Height)
            height += cw.s(17)

class StatusPanel(wx.ScrolledWindow):
    def __init__(self, parent, list, ccard, editable):
        wx.ScrolledWindow.__init__(self, parent, -1, size=cw.s((292, 200)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.SetScrollRate(cw.s(10), cw.s(10))
        self.csize = self.GetClientSize()
        self.list = list
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

        if cw.cwpy.debug and editable and not isinstance(self.Parent.Parent, StandbyPartyCharaInfo):
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def OnLeftUp(self, event):
        cw.cwpy.sounds["click"].play()
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.statusedit.StatusEditDialog(parent, list=self.list, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            self.draw(True)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)

        # 状態
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))

        height = cw.s(8)

        # 生命力の割合
        bmp = cw.image.conv2wxbmp(cw.cwpy.rsrc.statuses["LIFE"], maskpos=cw.s((1, 1)))
        if self.ccard.is_unconscious():
            colour = wx.Colour(0, 0, 128)
            msg = u"意識不明"
        elif self.ccard.is_heavyinjured():
            colour = wx.Colour(127, 0, 0)
            msg = u"重症"
        elif self.ccard.is_injured():
            colour = wx.Colour(0, 153, 187)
            msg = u"負傷"
        else:
            colour = wx.Colour(192, 192, 192)
            msg = u"正常"

        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(cw.s(12), height - cw.s(1), bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, cw.s(12), height - cw.s(1), True)
        dc.DrawText(msg, cw.s(32), height)
        height += cw.s(17)

        # 肉体状態異常
        if self.ccard.is_poison():
            height = self._draw_status(dc, u"中毒 (%s)" % (self.ccard.poison), "BODY0", height)
        if self.ccard.is_paralyze():
            if self.ccard.is_petrified():
                height = self._draw_status(dc, u"石化 (%s)" % (self.ccard.paralyze), "BODY1", height)
            else:
                height = self._draw_status(dc, u"麻痺 (%s)" % (self.ccard.paralyze), "BODY1", height)

        # 精神状態異常
        if self.ccard.is_sleep():
            height = self._draw_status(dc, u"眠り状態 (%s)" % (self.ccard.mentality_dur), "MIND1", height)
        if self.ccard.is_confuse():
            height = self._draw_status(dc, u"混乱状態 (%s)" % (self.ccard.mentality_dur), "MIND2", height)
        if self.ccard.is_overheat():
            height = self._draw_status(dc, u"激高状態 (%s)" % (self.ccard.mentality_dur), "MIND3", height)
        if self.ccard.is_brave():
            height = self._draw_status(dc, u"勇敢状態 (%s)" % (self.ccard.mentality_dur), "MIND4", height)
        if self.ccard.is_panic():
            height = self._draw_status(dc, u"恐慌状態 (%s)" % (self.ccard.mentality_dur), "MIND5", height)

        # 魔法的状態異常
        if self.ccard.is_bind():
            height = self._draw_status(dc, u"呪縛状態 (%s)" % (self.ccard.bind), "MAGIC0", height)
        if self.ccard.is_silence():
            height = self._draw_status(dc, u"沈黙状態 (%s)" % (self.ccard.silence), "MAGIC1", height)
        if self.ccard.is_faceup():
            height = self._draw_status(dc, u"暴露状態 (%s)" % (self.ccard.faceup), "MAGIC2", height)
        if self.ccard.is_antimagic():
            height = self._draw_status(dc, u"完全魔法防御状態 (%s)" % (self.ccard.antimagic), "MAGIC3", height)

        # 能力ボーナス・ペナルティ
        height = self._draw_enhance(dc, u"行動力", self.ccard.enhance_act,
                                    self.ccard.enhance_act_dur, "UP0", "DOWN0", height)
        height = self._draw_enhance(dc, u"回避力", self.ccard.enhance_avo,
                                    self.ccard.enhance_avo_dur, "UP1", "DOWN1", height)
        height = self._draw_enhance(dc, u"抵抗力", self.ccard.enhance_res,
                                    self.ccard.enhance_res_dur, "UP2", "DOWN2", height)
        height = self._draw_enhance(dc, u"防御力", self.ccard.enhance_def,
                                    self.ccard.enhance_def_dur, "UP3", "DOWN3", height)

        self.SetVirtualSize((-1, height - cw.s(17) + cw.s(8)))
        if update:
            self.Scroll(0, 0)
            self.Refresh()

    def _draw_status(self, dc, msg, imgname, height):
        bmp = cw.image.conv2wxbmp(cw.cwpy.rsrc.statuses[imgname])
        dc.DrawBitmap(bmp, cw.s(12), height - cw.s(1))
        dc.DrawText(msg, cw.s(32), height)
        return height + cw.s(17)

    def _draw_enhance(self, dc, enhname, value, dur, enhimage, pnlimage, height):
        if 0 == value:
            return height
        if 10 <= value:
            colour = wx.Colour(255, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = u"%s最大ボーナス (%d)" % (enhname, dur)
        elif 7 <= value:
            colour = wx.Colour(175, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = u"%s大ボーナス (%d)" % (enhname, dur)
        elif 4 <= value:
            colour = wx.Colour(127, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = u"%s中ボーナス (%d)" % (enhname, dur)
        elif 1 <= value:
            colour = wx.Colour(79, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = u"%s小ボーナス (%d)" % (enhname, dur)
        elif -10 >= value:
            colour = wx.Colour(0, 0, 51)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = u"%s最大ペナルティ (%d)" % (enhname, dur)
        elif -7 >= value:
            colour = wx.Colour(0, 0, 85)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = u"%s大ペナルティ (%d)" % (enhname, dur)
        elif -4 >= value:
            colour = wx.Colour(0, 0, 136)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = u"%s中ペナルティ (%d)" % (enhname, dur)
        elif -1 >= value:
            colour = wx.Colour(0, 0, 187)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = u"%s小ペナルティ (%d)" % (enhname, dur)
        bmp = cw.image.conv2wxbmp(bmp, maskpos=cw.s((1, 1)))
        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(cw.s(12), height - cw.s(1), bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, cw.s(12), height - cw.s(1))
        dc.DrawText(msg, cw.s(32), height)
        return height + cw.s(17)

class SkillPanel(wx.Panel):
    def __init__(self, parent, ccard):
        wx.Panel.__init__(self, parent, -1, size=cw.s((292, 200)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.ccard = ccard
        # headers
        self.headers = []
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        for header in self.headers:
            del header.textpos
            del header.subrect

    def OnLeftUp(self, event):
        if not cw.cwpy.debug and not isinstance(self.ccard, cw.character.Player):
            # ホールド不可
            self._open_cardinfo(event.GetPosition())
            return

        for header in self.headers:
            if header.subrect.collidepoint(event.GetPosition()):
                # ホールド状態切り替え(召喚獣以外)
                dc = wx.ClientDC(self)
                if header.penalty:
                    cw.cwpy.sounds["error"].play()
                    return
                cw.cwpy.sounds["click"].play()
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                header.hold = not header.hold
                if isinstance(self.ccard, cw.character.Player):
                    etree = cw.data.CWPyElementTree(element=header.carddata)
                    etree.edit("Property/Hold", str(header.hold))
                    self.ccard.data.is_edited = True
                if header.hold:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                else:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
                dc.DrawBitmap(bmp, header.subrect.left, header.subrect.top, True)
                return

    def _open_cardinfo(self, mousepos):
        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                header.negaflag = False
                cw.cwpy.sounds["click"].play()
                dlg = cardinfo.YadoCardInfo(self.Parent.Parent, self.headers, header)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                for header in self.headers:
                    header.negaflag = False
                self.draw(True)
                return True
        return False

    def OnRightUp(self, event):
        if self._open_cardinfo(event.GetPosition()):
            return
        self.Parent.Parent.OnCancel(event)

    def OnLeave(self, event):
        if not self.Parent.Parent.IsActive():
            return

        for header in self.headers:
            if header.negaflag:
                header.negaflag = False
                dc = wx.ClientDC(self)
                dc.SetTextForeground(wx.WHITE)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])

    def OnMove(self, event):
        dc = wx.ClientDC(self)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))
        mousepos = event.GetPosition()

        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    dc.SetTextForeground(wx.RED)
                    dc.DrawText(header.name, header.textpos[0], header.textpos[1])
                    dc.SetTextForeground(wx.WHITE)
            elif header.negaflag:
                header.negaflag = False
                dc.DrawText(header.name, header.textpos[0], header.textpos[1])

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)
        # 所持スキル
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))

        if not self.headers:
            self.headers = self.ccard.cardpocket[cw.POCKET_SKILL]

        for index, header in enumerate(self.headers):
            if index < 5:
                pos = cw.s((30, 30+17*index))
            else:
                pos = cw.s((170, 30+17*(index-5)))

            # カード名
            s = header.name
            size = dc.GetTextExtent(s)

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, pos[0], pos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, pos[0], pos[1])

            # rect
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - cw.s(20), pos[1] - cw.s(1), size[0] + cw.s(20), size[1] + cw.s(2))
            # 適性値
            key = "HAND%s" % (header.get_vocation_level(self.ccard))
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+cw.s(85), pos[1]-cw.s(1), True)
            # 使用回数
            key = "HAND%s" % (header.get_uselimit_level() + 5)
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+cw.s(100), pos[1]-cw.s(1), True)

            # ホールドまたはペナルティ
            if header.penalty:
                bmp = cw.cwpy.rsrc.dialogs["STATUS7"]
            elif header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
            dc.DrawBitmap(bmp, pos[0]-cw.s(20), pos[1]-cw.s(1), True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= level / 2 + 2 if level % 2 == 0 else level / 2 + 3
        maxn = maxn if maxn <= 10 else 10
        s = cw.cwpy.msgs["card_number"] % (n, maxn)
        dc.DrawText(s, cw.s(10), cw.s(10))
        dc.EndDrawing()

class ItemPanel(SkillPanel):
    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)
        # 所持アイテム
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))

        if not self.headers:
            self.headers = self.ccard.cardpocket[cw.POCKET_ITEM]

        for index, header in enumerate(self.headers):
            if index < 5:
                pos = cw.s((30, 30+17*index))
            else:
                pos = cw.s((170, 30+17*(index-5)))

            # カード名
            s = header.name
            size = dc.GetTextExtent(s)
            if header.uselimit:
                s += "(%d)" % header.uselimit

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, pos[0], pos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, pos[0], pos[1])

            # rect
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - cw.s(20), pos[1] - cw.s(1), size[0] + cw.s(20), size[1] + cw.s(2))
            # ホールドまたはペナルティ
            if header.penalty:
                bmp = cw.cwpy.rsrc.dialogs["STATUS7"]
            elif header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
            dc.DrawBitmap(bmp, pos[0]-cw.s(20), pos[1]-cw.s(1), True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= level / 2 + 2 if level % 2 == 0 else level / 2 + 3
        maxn = maxn if maxn <= 10 else 10
        s = cw.cwpy.msgs["card_number"] % (n, maxn)
        dc.DrawText(s, cw.s(10), cw.s(10))
        dc.EndDrawing()

class BeastPanel(SkillPanel):
    def OnLeftUp(self, event):
        # ホールド不可
        self._open_cardinfo(event.GetPosition())

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-cw.s(226))/2, (self.csize[1]-cw.s(132))/2, True)
        # 所持召喚獣
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=cw.s(10)))

        if not self.headers:
            self.headers = self.ccard.cardpocket[cw.POCKET_BEAST]

        # 召喚獣アイコン
        for index, header in enumerate(self.headers):
            if index < 5:
                pos = cw.s((30, 30+17*index))
            else:
                pos = cw.s((170, 30+17*(index-5)))

            # カード名
            s = header.name
            size = dc.GetTextExtent(s)
            if header.uselimit:
                s += "(%d)" % header.uselimit

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, pos[0], pos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, pos[0], pos[1])

            # rect
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - cw.s(20), pos[1] - cw.s(1), size[0] + cw.s(20), size[1] + cw.s(2))

            # 召喚獣アイコン
            if header.attachment:
                bmp = cw.cwpy.rsrc.dialogs["STATUS10"]
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS11"]

            dc.DrawBitmap(bmp, pos[0]-cw.s(20), pos[1]-cw.s(1), True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= (level + 2) / 4 if (level + 2) % 4 == 0 else (level + 2) / 4 + 1
        maxn = maxn if maxn <= 10 else 10
        s = cw.cwpy.msgs["card_number"] % (n, maxn)
        dc.DrawText(s, cw.s(10), cw.s(10))
        dc.EndDrawing()

def main():
    pass

if __name__ == "__main__":
    main()
