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
        # 編集または状態
        if cw.cwpy.is_playingscenario():
            self.editpanel = StatusPanel(self.notebook, self.ccard)
            self.notebook.AddPage(self.editpanel, u"状態")
        else:
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
        ages = set(cw.cwpy.setting.periodcoupons)
        sexs = set(cw.cwpy.setting.sexcoupons)
        self.sex = cw.cwpy.setting.sexes[0].name
        self.age = cw.cwpy.setting.periods[0].name
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
        coupons = self.ccard.get_specialcoupons()
        if u"＠レベル原点" in coupons and self.ccard.level <> coupons[u"＠レベル原点"]:
            s = "Level: %d / %d" % (self.ccard.level, coupons[u"＠レベル原点"])
        else:
            s = "Level: %d" % (self.ccard.level)
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
        self.csize = self.GetClientSize()
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
        csize = self.csize
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

class EditButton():
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.negaflag = False

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
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

    def OnLeftUp(self, event):
        for header in self.headers:
            if header.subrect.collidepoint(event.GetPosition()):
                if header.type == 0:
                    # デザインを変更する
                    cw.cwpy.sounds[u"システム・クリック"].play()
                    dlg = cw.dialog.create.AdventurerDesignDialog(self.Parent.Parent)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        self.Parent.Parent.toppanel.draw(True)
                        self.Parent.Parent.descpanel.draw(True)
                    dlg.Destroy()
                else:
                    # レベルを調節する
                    cw.cwpy.sounds[u"システム・クリック"].play()
                    dlg = cw.dialog.edit.LevelEditor(self.Parent.Parent)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        self.Parent.Parent.toppanel.draw(True)
                    dlg.Destroy()
                return

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
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])

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
        dc.DrawBitmap(self.watermark, (self.csize[0]-226)/2, (self.csize[1]-132)/2, True)

        self.headers = (EditButton(u"デザインを変更する", 0), EditButton(u"レベルを調節する", 1))

        # 編集ボタン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
        # 編集アイコン
        bmp = cw.cwpy.rsrc.dialogs["STATUS12"]
        # 編集項目名
        height = 8
        for header in self.headers:
            size = dc.GetTextExtent(header.name)
            dc.DrawBitmap(bmp, 12, height - 1, True)
            dc.DrawText(header.name, 32, height)
            header.textpos = (32, height)
            header.subrect = pygame.Rect(12, height - 1, 20 + size[0], bmp.Height)
            height += 17

class StatusPanel(wx.ScrolledWindow):
    def __init__(self, parent, ccard):
        wx.ScrolledWindow.__init__(self, parent, -1, size=(292, 200), style=wx.SUNKEN_BORDER)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.SetScrollRate(10, 10)
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

        # 状態
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))

        height = 8

        # 生命力の割合
        bmp = cw.cwpy.rsrc.statuses["LIFE"]
        if self.ccard.is_unconscious():
            colour = wx.Colour(0, 0, 128)
            msg = "意識不明"
        elif self.ccard.is_heavyinjured():
            colour = wx.Colour(127, 0, 0)
            msg = "重症"
        elif self.ccard.is_injured():
            colour = wx.Colour(0, 153, 187)
            msg = "負傷"
        else:
            colour = wx.Colour(192, 192, 192)
            msg = "正常"

        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(12, height - 1, bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, 12, height - 1, True)
        dc.DrawText(msg, 32, height)
        height += 17

        # 肉体状態異常
        if self.ccard.is_poison():
            height = self._draw_status(dc, "中毒 (%s)" % (self.ccard.poison), "BODY0", height)
        if self.ccard.is_paralyze():
            if self.ccard.is_petrified():
                height = self._draw_status(dc, "石化 (%s)" % (self.ccard.paralyze), "BODY1", height)
            else:
                height = self._draw_status(dc, "麻痺 (%s)" % (self.ccard.paralyze), "BODY1", height)

        # 精神状態異常
        if self.ccard.is_sleep():
            height = self._draw_status(dc, "眠り状態 (%s)" % (self.ccard.mentality_dur), "MIND1", height)
        if self.ccard.is_confuse():
            height = self._draw_status(dc, "混乱状態 (%s)" % (self.ccard.mentality_dur), "MIND2", height)
        if self.ccard.is_overheat():
            height = self._draw_status(dc, "激高状態 (%s)" % (self.ccard.mentality_dur), "MIND3", height)
        if self.ccard.is_brave():
            height = self._draw_status(dc, "勇敢状態 (%s)" % (self.ccard.mentality_dur), "MIND4", height)
        if self.ccard.is_panic():
            height = self._draw_status(dc, "恐慌状態 (%s)" % (self.ccard.mentality_dur), "MIND5", height)

        # 魔法的状態異常
        if self.ccard.is_bind():
            height = self._draw_status(dc, "呪縛状態 (%s)" % (self.ccard.bind), "MAGIC0", height)
        if self.ccard.is_silence():
            height = self._draw_status(dc, "沈黙状態 (%s)" % (self.ccard.silence), "MAGIC1", height)
        if self.ccard.is_faceup():
            height = self._draw_status(dc, "暴露状態 (%s)" % (self.ccard.faceup), "MAGIC2", height)
        if self.ccard.is_antimagic():
            height = self._draw_status(dc, "完全魔法防御状態 (%s)" % (self.ccard.antimagic), "MAGIC3", height)

        # 能力ボーナス・ペナルティ
        height = self._draw_enhance(dc, "行動力", self.ccard.enhance_act,
                                    self.ccard.enhance_act_dur, "UP0", "DOWN0", height)
        height = self._draw_enhance(dc, "回避力", self.ccard.enhance_avo,
                                    self.ccard.enhance_avo_dur, "UP1", "DOWN1", height)
        height = self._draw_enhance(dc, "抵抗力", self.ccard.enhance_res,
                                    self.ccard.enhance_res_dur, "UP2", "DOWN2", height)
        height = self._draw_enhance(dc, "防御力", self.ccard.enhance_def,
                                    self.ccard.enhance_def_dur, "UP3", "DOWN3", height)

        self.SetVirtualSize((-1, height - 17 + 8))
        if update:
            self.Scroll(0, 0)
            self.Refresh()

    def _draw_status(self, dc, msg, imgname, height):
        bmp = cw.image.conv2wxbmp(cw.cwpy.rsrc.statuses[imgname])
        dc.DrawBitmap(bmp, 12, height - 1)
        dc.DrawText(msg, 32, height)
        return height + 17

    def _draw_enhance(self, dc, enhname, value, dur, enhimage, pnlimage, height):
        if 0 == value:
            return height
        if 7 <= value:
            colour = wx.Colour(175, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = "%s大ボーナス (%d)" % (enhname, dur)
        elif 4 <= value:
            colour = wx.Colour(127, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = "%s中ボーナス (%d)" % (enhname, dur)
        elif 1 <= value:
            colour = wx.Colour(79, 0, 0)
            bmp = cw.cwpy.rsrc.statuses[enhimage]
            msg = "%s小ボーナス (%d)" % (enhname, dur)
        elif -7 >= value:
            colour = wx.Colour(0, 0, 85)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = "%s大ペナルティ (%d)" % (enhname, dur)
        elif -4 >= value:
            colour = wx.Colour(0, 0, 160)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = "%s中ペナルティ (%d)" % (enhname, dur)
        elif -1 >= value:
            colour = wx.Colour(0, 0, 187)
            bmp = cw.cwpy.rsrc.statuses[pnlimage]
            msg = "%s小ペナルティ (%d)" % (enhname, dur)
        bmp = cw.image.conv2wxbmp(bmp, maskpos=(1, 1))
        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(12, height - 1, bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, 12, height - 1)
        dc.DrawText(msg, 32, height)
        return height + 17

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
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        for header in self.headers:
            del header.textpos
            del header.subrect

    def OnLeftUp(self, event):
        for header in self.headers:
            if header.subrect.collidepoint(event.GetPosition()):
                # ホールド状態切り替え(召喚獣以外)
                dc = wx.ClientDC(self)
                if u"ペナルティ" in header.keycodes:
                    cw.cwpy.sounds[u"システム・エラー"].play()
                    return
                cw.cwpy.sounds[u"システム・クリック"].play()
                header.hold = not header.hold
                if header.hold:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                else:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
                dc.DrawBitmap(bmp, header.subrect.left, header.subrect.top, True)
                return

    def _open_cardinfo(self, mousepos):
        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                cw.cwpy.sounds[u"システム・クリック"].play()
                dlg = cardinfo.YadoCardInfo(self.Parent.Parent, self.headers, header)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
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
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=9))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])

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
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - 20, pos[1] - 1, size[0] + 20, size[1] + 2)
            # 適正値
            key = "HAND%s" % (header.get_vocation_level())
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+85, pos[1]-1, True)
            # 使用回数
            key = "HAND%s" % (header.get_uselimit_level() + 5)
            bmp = cw.cwpy.rsrc.wxstones[key]
            dc.DrawBitmap(bmp, pos[0]+100, pos[1]-1, True)

            # ホールドまたはペナルティ
            if u"ペナルティ" in header.keycodes:
                bmp = cw.cwpy.rsrc.dialogs["STATUS7"]
            elif header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
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
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - 20, pos[1] - 1, size[0] + 20, size[1] + 2)
            # ホールドまたはペナルティ
            if u"ペナルティ" in header.keycodes:
                bmp = cw.cwpy.rsrc.dialogs["STATUS7"]
            elif header.hold:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
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
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - 20, pos[1] - 1, size[0] + 20, size[1] + 2)

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
