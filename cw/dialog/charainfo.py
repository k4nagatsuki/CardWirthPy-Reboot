#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import wx
import pygame

import cw
import cardinfo


#-------------------------------------------------------------------------------
#　キャラクター情報ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CharaInfo(wx.Dialog):
    """
    キャラクター情報ダイアログ
    """
    def __init__(self, parent):
        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, u"キャラクター情報", size=(300, 355),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.csize = self.GetClientSize()
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (85, 24), u"閉じる")
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, (30, 30), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, (30, 30), bmp=bmp)
        # notebook
        self.notebook = wx.Notebook(self, -1, size=(300, 220), style=wx.BK_BOTTOM)
        self.notebook.SetFont(cw.cwpy.rsrc.get_wxfont("btnfont"))
        # 解説
        self.descpanel = DescPanel(self.notebook, self.ccard)
        self.notebook.AddPage(self.descpanel, u"解説")
        # 経歴
        self.historypanel = HistoryPanel(self.notebook, self.ccard)
        self.notebook.AddPage(self.historypanel, u"経歴")
        # 編集
        self.editpanel = EditPanel(self.notebook, self.ccard)
        self.notebook.AddPage(self.editpanel, u"編集")

        # 各種所持カード
        if self.ccard.data.hasfind("/SkillCards"):
            # 技能
            self.skillpanel = SkillPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.skillpanel, u"技能")
            # アイテム
            self.itempanel = ItemPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.itempanel, u"ｱｲﾃﾑ")
            # 召喚獣
            self.beastpanel = BeastPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.beastpanel, u"召喚")

        # toppanel
        self.toppanel = TopPanel(self, self.ccard)
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
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"システム・クリック"].play()
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
                self.ccard = cw.character.Character(data)

            self.Parent.OnClickLeftBtn(event)
        else:
            cw.cwpy.sounds[u"システム・改ページ"].play()
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
                self.ccard = cw.character.Character(data)

            self.Parent.OnClickRightBtn(event)
        else:
            cw.cwpy.sounds[u"システム・改ページ"].play()
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
        cw.cwpy.sounds[u"システム・クリック"].play()

    def draw(self, update):
        win = self.notebook.GetCurrentPage()
        dc = wx.ClientDC(win)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        for header in win.headers:
            s = header.name

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, header.subrect.left, header.subrect.top)
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, header.subrect.left, header.subrect.top)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        margin = (self.csize[0] - 145) / 2 + (self.csize[0] - 145) % 2
        margin2 = (self.csize[0] - 145) / 2
        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.TOP, 3)
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
    def __init__(self, parent, headers, index):
        self.list = headers
        self.index = index
        header = self.list[self.index]
        data = cw.data.yadoxml2etree(header.fpath)

        if data.getroot().tag == "Album":
            self.ccard = cw.character.AlbumPage(data)
        else:
            self.ccard = cw.character.Character(data)

        CharaInfo.__init__(self, parent)

class ActiveCharaInfo(CharaInfo):
    def __init__(self, parent):
        self.ccard = cw.cwpy.selection

        if isinstance(cw.cwpy.selection, cw.character.Player):
            self.list = cw.cwpy.get_pcards("unreversed")
        elif isinstance(cw.cwpy.selection, cw.character.Enemy):
            self.list = cw.cwpy.get_ecards("unreversed")
        else:
            self.list = cw.cwpy.get_fcards()

        self.index = self.list.index(cw.cwpy.selection)
        CharaInfo.__init__(self, parent)

class TopPanel(wx.Panel):
    """
    顔画像などを描画するパネル
    """
    def __init__(self, parent, ccard):
        wx.Panel.__init__(self, parent, -1, size=(300, 100))
        self.csize = self.GetClientSize()
        self.ccard = ccard
        self.yadodir = cw.cwpy.yadodir
        # bmp
        self.wing = cw.cwpy.rsrc.dialogs["STATUS"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        # クーポンにある各種変数取得
        ages = set((u"＿老人", u"＿大人", u"＿若者", u"＿子供"))
        sexs = set((u"＿♀", u"＿♂"))
        self.sex = u"♂"
        self.age = u"若者"
        self.ep = "0"

        for coupon in self.ccard.data.getfind("/Property/Coupons"):
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
        cw.util.draw_height(dc, self.wing, 25)
        # カード画像
        path = self.ccard.data.gettext("/Property/ImagePath", "")

        if isinstance(cw.cwpy.selection, (cw.character.Enemy,
                                            cw.character.Friend)):
            path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
        else:
            path = cw.util.join_yadodir(path)

        bmp = cw.util.load_wxbmp(path, True)
        cw.util.draw_height(dc, bmp, 5)
        # レベル
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=10))
        s = "Level: " + str(self.ccard.level)
        dc.DrawText(s, 5, 5)
        # EP
        s = "EP: " + self.ep
        dc.DrawText(s, 8, 82)
        # 名前
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=11))
        s = self.ccard.name
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 295 - w, 3)
        # 年代
        s = self.age + self.sex
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 295 - w, 80)
        dc.EndDrawing()

class DescPanel(wx.Panel):
    """
    解説文を描画するパネル。
    """
    def __init__(self, parent, ccard):
        wx.Panel.__init__(self, parent, -1, size=(292, 200), style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        # 解説文
        self.text = self.ccard.data.gettext("/Property/Description", "")
        self.text = cw.util.txtwrap(self.text, 4)

        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)
            self.PrepareDC(dc)

        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)
        # 解説文
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
        dc.DrawLabel(self.text, (24, 10, 200, 120))
        dc.EndDrawing()

class HistoryPanel(wx.ScrolledWindow):
    """
    クーポンを描画するスクロールウィンドウ。
    """
    def __init__(self, parent, ccard):
        wx.ScrolledWindow.__init__(self, parent, -1, size=(292, 200), style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.SetScrollRate(10, 10)
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

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer, wx.BUFFER_VIRTUAL_AREA)

    def draw(self, update=False):
        # クーポンリスト
        coupons = []

        for coupon in self.ccard.data.getfind("/Property/Coupons"):
            if coupon.text and not coupon.text.startswith(u"＠"):
                if cw.cwpy.debug or not coupon.text.startswith(u"＿"):
                    coupons.append((coupon.text, int(coupon.get("value"))))

        coupons.reverse()
        # maxheght計算
        h = self.gold.GetSize()[1]
        maxheight = (h + 5) * len(coupons) + 8
        self.SetVirtualSize((-1, maxheight))

        # create buffer
        csize = self.GetClientSize()
        height = maxheight + 10 if maxheight + 10 > csize[1] else csize[1]
        self.buffer = wx.EmptyBitmap(csize[0], height)
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        # 背景の透かし
        for cnt in xrange(maxheight / csize[1] + 1):
            height = ((csize[1] - 132) / 2) + csize[1] * cnt
            dc.DrawBitmap(self.watermark, (csize[0]-226) / 2, height, True)

        # クーポン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        for index, coupon in enumerate(coupons):
            height = 8 + (h + 5) * index
            text, value = coupon
            dc.DrawText(text, 32, height)

            if value > 1:
                dc.DrawBitmap(self.gold, 12, height - 1, True)
            elif value == 1:
                dc.DrawBitmap(self.silver, 12, height - 1, True)
            elif value == 0:
                dc.DrawBitmap(self.bronze, 12, height - 1, True)
            else:
                dc.DrawBitmap(self.black, 12, height - 1, True)

        if update:
            self.Scroll(0, 0)
            self.Refresh()

class EditPanel(wx.Panel):
    def __init__(self, parent, ccard):
        wx.Panel.__init__(self, parent, -1, size=(292, 200), style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

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
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)
        # 編集ボタン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
        s = u"デザインを変更する"
        dc.DrawText(s, 32, 8)
        s = u"レベルを調節する"
        dc.DrawText(s, 32, 25)
        # 編集アイコン
        bmp = cw.cwpy.rsrc.dialogs["STATUS12"]
        dc.DrawBitmap(bmp, 12, 7, True)
        dc.DrawBitmap(bmp, 12, 24, True)
        dc.EndDrawing()

class SkillPanel(wx.Panel):
    def __init__(self, parent, ccard):
        wx.Panel.__init__(self, parent, -1, size=(292, 200), style=wx.SUNKEN_BORDER)
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
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        for header in self.headers:
            del header.subrect

    def OnRightUp(self, event):
        for header in self.headers:
            if header.subrect.collidepoint(event.GetPosition()):
                cw.cwpy.sounds[u"システム・クリック"].play()
                dlg = cardinfo.YadoCardInfo(self.Parent.Parent, self.headers, header)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
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
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
                s = header.name
                dc.DrawText(s, header.subrect.left, header.subrect.top)

    def OnMove(self, event):
        dc = wx.ClientDC(self)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
        mousepos = event.GetPosition()

        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    dc.SetTextForeground(wx.RED)
                    dc.DrawText(header.name, header.subrect.left, header.subrect.top)
                    dc.SetTextForeground(wx.WHITE)
            elif header.negaflag:
                header.negaflag = False
                dc.DrawText(header.name, header.subrect.left, header.subrect.top)

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
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)
        # 所持スキル
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        if not self.headers:
            self.headers = self.ccard.cardpocket[0]

        for index, header in enumerate(self.headers):
            if index < 5:
                pos = 30, 30+17*index
            else:
                pos = 170, 30+17*(index-5)

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
            header.subrect = pygame.Rect(pos, size)
            # 適正値
            key = "HAND%s" % (header.get_vocation_level())
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+85, pos[1]-1, True)
            # 使用回数
            key = "HAND%s" % (header.get_uselimit_level() + 5)
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+100, pos[1]-1, True)

            # ホールド
            if header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                dc.DrawBitmap(bmp, pos[0]-20, pos[1]-1, True)
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
                dc.DrawBitmap(bmp, pos[0]-20, pos[1]-1, True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= level / 2 + 2 if level % 2 == 0 else level / 2 + 3
        maxn = maxn if maxn <= 10 else 10
        s = u"カード枚数 " + str(n) + " / " + str(maxn)
        dc.DrawText(s, 10, 10)
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
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)
        # 所持アイテム
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        if not self.headers:
            self.headers = self.ccard.cardpocket[1]

        for index, header in enumerate(self.headers):
            if index < 5:
                pos = 30, 30+17*index
            else:
                pos = 170, 30+17*(index-5)

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
            header.subrect = pygame.Rect(pos, size)
            # ホールド
            if header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                dc.DrawBitmap(bmp, pos[0]-20, pos[1]-1, True)
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
                dc.DrawBitmap(bmp, pos[0]-20, pos[1]-1, True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= level / 2 + 2 if level % 2 == 0 else level / 2 + 3
        maxn = maxn if maxn <= 10 else 10
        s = u"カード枚数 " + str(n) + " / " + str(maxn)
        dc.DrawText(s, 10, 10)
        dc.EndDrawing()

class BeastPanel(SkillPanel):
    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        self.PrepareDC(dc)
        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)
        # 所持召喚獣
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        if not self.headers:
            self.headers = self.ccard.cardpocket[2]

        # 召喚獣アイコン
        for index, header in enumerate(self.headers):
            if index < 5:
                pos = 30, 30+17*index
            else:
                pos = 170, 30+17*(index-5)

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
            header.subrect = pygame.Rect(pos, size)

            # 召喚獣アイコン
            if header.attachment:
                bmp = cw.cwpy.rsrc.dialogs["STATUS10"]
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS11"]

            dc.DrawBitmap(bmp, pos[0]-20, pos[1]-1, True)

        # カード枚数
        level = self.ccard.level
        n = len(self.headers)
        maxn= (level + 2) / 4 if (level + 2) % 4 == 0 else (level + 2) / 4 + 1
        maxn = maxn if maxn <= 10 else 10
        s = u"カード枚数 " + str(n) + " / " + str(maxn)
        dc.DrawText(s, 10, 10)
        dc.EndDrawing()

def main():
    pass

if __name__ == "__main__":
    main()
