#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import math
import wx
import pygame

import cw
import cardinfo

import wx.lib.agw.aui as aui

#-------------------------------------------------------------------------------
#　キャラクター情報ダイアログ　スーパークラス
#-------------------------------------------------------------------------------

class CharaInfo(wx.Dialog):
    """
    キャラクター情報ダイアログ
    """
    def __init__(self, parent, redrawfunc, editable, party=None):
        # フォントサイズによってダイアログサイズを決定する
        dc = wx.ClientDC(parent)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        self.width = dc.GetTextExtent(u"―"*20)[0] + cw.wins(20)
        self.width = max(cw.wins(302), self.width)

        # ダイアログボックス
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["character_information"], size=(self.width, cw.wins(355)),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        if sys.platform <> "win32":
            self.SetDoubleBuffered(True)
        self.party = party
        self.csize = self.GetClientSize()
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((85, 24)), cw.cwpy.msgs["close"])
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, cw.wins((30, 30)), bmp=bmp, chain=True)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, cw.wins((30, 30)), bmp=bmp, chain=True)
        # enabled
        if len(self.list) <= 1:
            self.leftbtn.Disable()
            self.rightbtn.Disable()

        # notebook
        self.notebook = wx.lib.agw.aui.auibook.AuiNotebook(self, -1, size=(self.width, cw.wins(203)),
                                                           agwStyle=aui.AUI_NB_BOTTOM|aui.AUI_NB_TAB_FIXED_WIDTH)
        self.notebook.SetMinSize((self.width, cw.wins(199)))
        self.notebook.SetArtProvider(cw.util.CWTabArt())
        self.notebook.SetFont(cw.cwpy.rsrc.get_wxfont("tab", pixelsize=cw.wins(13)))

        cut= self.GetClientSize()[0] / 6 - 1
        self.notebook.SetMinMaxTabWidth(cut, cut)

        self.bottompanel = []

        # 解説
        self.descpanel = DescPanel(self.notebook, self.ccard, editable)
        self.bottompanel.append(self.descpanel)
        self.notebook.AddPage(self.descpanel, cw.cwpy.msgs["description"])
        # 経歴
        self.historypanel = HistoryPanel(self.notebook, self.ccard, editable)
        self.bottompanel.append(self.historypanel)
        self.notebook.AddPage(self.historypanel,  cw.cwpy.msgs["history"])
        # 編集または状態
        if self.is_playingscenario:
            self.editpanel = StatusPanel(self.notebook, self.list, self.ccard, editable)
            self.bottompanel.append(self.editpanel)
            self.notebook.AddPage(self.editpanel, cw.cwpy.msgs["status"])
        elif editable:
            self.editpanel = EditPanel(self.notebook, self.list, self.ccard)
            self.bottompanel.append(self.editpanel)
            self.notebook.AddPage(self.editpanel, cw.cwpy.msgs["edit"])

        # 各種所持カード
        if self.ccard.data.hasfind("SkillCards"):
            # 技能
            self.skillpanel = SkillPanel(self.notebook, self.ccard)
            self.bottompanel.append(self.skillpanel)
            self.notebook.AddPage(self.skillpanel, cw.cwpy.msgs["skills"])
            # アイテム
            self.itempanel = ItemPanel(self.notebook, self.ccard)
            self.bottompanel.append(self.itempanel)
            self.notebook.AddPage(self.itempanel,  cw.cwpy.msgs["items"])
            # 召喚獣
            self.beastpanel = BeastPanel(self.notebook, self.ccard)
            self.bottompanel.append(self.beastpanel)
            self.notebook.AddPage(self.beastpanel, cw.cwpy.msgs["beasts"])

        # toppanel
        self.toppanel = TopPanel(self, self.ccard, redrawfunc)

        # titlepanel
        self.titlepanel = TitlePanel(self, self.notebook)

        # layout
        self._do_layout()
        # bind
        self._bind()
        cw.util.add_sideclickhandlers(self.toppanel, self.leftbtn, self.rightbtn)

        for i in xrange(len(self.bottompanel)):
            tabctrl = self.notebook.FindTab(self.notebook.GetPage(i))[0]
            def onfocus(event):
                self.closebtn.SetFocus()
            tabctrl.Bind(wx.EVT_SET_FOCUS, onfocus)
        for panel in self.bottompanel:
            panel.AcceptsFocus = lambda: False
            panel.AcceptsFocusFromKeyboard = lambda: False
            panel.AcceptsFocusRecursively = lambda: False
            panel.SetFocus = lambda: None
            panel.SetFocusFromKeyboard = lambda: None
            if  3 <= wx.VERSION[0]:
                panel.SetCanFocus(False)
            def onfocus(event):
                self.closebtn.SetFocus()
            panel.Bind(wx.EVT_SET_FOCUS, onfocus)

        self.closebtn.SetFocus()

        self.leftpagekeyid = wx.NewId()
        self.rightpagekeyid = wx.NewId()
        self.upkeyid = wx.NewId()
        self.downkeyid = wx.NewId()
        self.pageupkeyid = wx.NewId()
        self.pagedownkeyid = wx.NewId()
        self.homekeyid = wx.NewId()
        self.endkeyid = wx.NewId()
        self.enter = wx.NewId()
        self.openinfo = wx.NewId()
        copyid = wx.NewId()
        esckeyid = wx.NewId()
        leftkeyid = wx.NewId()
        rightkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnClickLeftBtn, id=self.leftpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnClickRightBtn, id=self.rightpagekeyid)
        self.Bind(wx.EVT_MENU, self.OnUp, id=self.upkeyid)
        self.Bind(wx.EVT_MENU, self.OnDown, id=self.downkeyid)
        self.Bind(wx.EVT_MENU, self.OnPageUp, id=self.pageupkeyid)
        self.Bind(wx.EVT_MENU, self.OnPageDown, id=self.pagedownkeyid)
        self.Bind(wx.EVT_MENU, self.OnHome, id=self.homekeyid)
        self.Bind(wx.EVT_MENU, self.OnEnd, id=self.endkeyid)
        self.Bind(wx.EVT_MENU, self.OnEnter, id=self.enter)
        self.Bind(wx.EVT_MENU, self.OnOpenInfo, id=self.openinfo)
        self.Bind(wx.EVT_MENU, self.OnCopyDetail, id=copyid)
        self.Bind(wx.EVT_MENU, self.OnCancel, id=esckeyid)
        self.Bind(wx.EVT_MENU, self.OnLeftKey, id=leftkeyid)
        self.Bind(wx.EVT_MENU, self.OnRightKey, id=rightkeyid)
        seq = [
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.leftpagekeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.rightpagekeyid),
            (wx.ACCEL_NORMAL, wx.WXK_UP, self.upkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, self.downkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_PAGEUP, self.pageupkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_PAGEDOWN, self.pagedownkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_HOME, self.homekeyid),
            (wx.ACCEL_NORMAL, wx.WXK_END, self.endkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RETURN, self.enter),
            (wx.ACCEL_NORMAL, wx.WXK_BACK, esckeyid),
            (wx.ACCEL_NORMAL, ord('_'), esckeyid),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, self.openinfo),
            (wx.ACCEL_CTRL, ord('C'), copyid),
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, leftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, rightkeyid),
        ]
        cw.util.set_acceleratortable(self, seq)

    def _bind(self):
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        #タブ切替効果音
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def OnCopyDetail(self, event):
        cw.cwpy.play_sound("equipment")
        page = self.notebook.GetPage(self.notebook.GetSelection())
        lines = []
        lines.append(self.toppanel.get_detailtext())
        lines.append(u"-" * 40)
        s = page.get_detailtext()
        if s:
            lines.append(s)
        lines.append(u"")
        cw.util.to_clipboard(u"\n".join(lines))

    def OnEnter(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, CardPanel):
            event = wx.PyCommandEvent(wx.wxEVT_RIGHT_UP, wx.ID_UP)
            page.ProcessEvent(event)
        else:
            event = wx.PyCommandEvent(wx.wxEVT_LEFT_UP, wx.ID_UP)
            page.ProcessEvent(event)

    def OnOpenInfo(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, CardPanel):
            event = wx.PyCommandEvent(wx.wxEVT_LEFT_UP, wx.ID_UP)
            page.ProcessEvent(event)

    def OnUp(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if hasattr(page, "up"):
            page.up()
        elif isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x, y - 1)
            page.Refresh()

    def OnPageUp(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x, y - 10)
            page.Refresh()

    def OnHome(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            page.Scroll(x, 0)
            page.Refresh()

    def OnDown(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if hasattr(page, "down"):
            page.down()
        elif isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x, y + 1)
            page.Refresh()

    def OnPageDown(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x, y + 10)
            page.Refresh()

    def OnLeftKey(self, event):
        event.Skip()
        index = self.notebook.GetSelection()
        page = self.notebook.GetPage(index)
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x - 1, y)
            page.Refresh()
            if x <> page.GetScrollPos(wx.HORIZONTAL):
                return
        self.notebook.SetSelection(index-1 if 0 < index else len(self.bottompanel)-1)

    def OnRightKey(self, event):
        event.Skip()
        index = self.notebook.GetSelection()
        page = self.notebook.GetPage(index)
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            y = page.GetScrollPos(wx.VERTICAL)
            page.Scroll(x + 1, y)
            page.Refresh()
            if x <> page.GetScrollPos(wx.HORIZONTAL):
                return
        self.notebook.SetSelection((index+1) % len(self.bottompanel))

    def OnEnd(self, event):
        page = self.notebook.GetPage(self.notebook.GetSelection())
        if isinstance(page, wx.ScrolledWindow):
            x = page.GetScrollPos(wx.HORIZONTAL)
            page.Scroll(x, page.GetVirtualSize()[1])
            page.Refresh()

    def up(self):
        x = self.GetScrollPos(wx.HORIZONTAL)
        y = self.GetScrollPos(wx.VERTICAL)
        self.Scroll(x, y - 1)
        self.Refresh()

    def down(self):
        x = self.GetScrollPos(wx.HORIZONTAL)
        y = self.GetScrollPos(wx.VERTICAL)
        self.Scroll(x, y + 1)
        self.Refresh()

    def OnMouseWheel(self, event):
        rect = self.GetClientRect()
        # ダイアログの上半分でホイールを回した場合は
        # 表示メンバを交代し、下半分の場合は
        # 情報タブの切り替えを行う
        rect = wx.Rect(rect[0], rect[1], rect[2], rect[3] / 2)
        if rect.Contains(event.GetPosition()) and self.leftbtn.IsEnabled():
            if cw.util.get_wheelrotation(event) > 0:
                if self.leftbtn.IsEnabled():
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
                    self.ProcessEvent(btnevent)
            else:
                if self.rightbtn.IsEnabled():
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
                    self.ProcessEvent(btnevent)
        else:
            index = self.notebook.GetSelection()
            count = self.notebook.GetPageCount()
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
            self.notebook.SetSelection(index)
            #AUIでは不要？
            #btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGED, self.notebook.GetId())
            #self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
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
                cw.cwpy.play_sound("page")
            else:
                self.Parent.OnClickLeftBtn(event)
        else:
            cw.cwpy.play_sound("page")
            self.ccard = self.list[self.index]
            self.Parent.change_selection(self.list[self.index])

        self.toppanel.ccard = self.ccard
        self.toppanel.Refresh()

        for win in self.bottompanel:
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
                cw.cwpy.play_sound("page")
            else:
                self.Parent.OnClickRightBtn(event)
        else:
            cw.cwpy.play_sound("page")
            self.ccard = self.list[self.index]
            self.Parent.change_selection(self.list[self.index])

        self.toppanel.ccard = self.ccard
        self.toppanel.Refresh()

        for win in self.bottompanel:
            win.ccard = self.ccard
            win.headers = []
            win.draw(True)

    def OnPageChanged(self, event):
        pass

    def OnPageChanging(self, event):
        cw.cwpy.play_sound("click")
        self.titlepanel.draw(True)

    def draw(self, update):
        win = self.notebook.GetCurrentPage()
        dc = wx.ClientDC(win)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))

        for header in win.headers:
            s = header.name

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, header.textpos[0], header.textpos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, header.textpos[0], header.textpos[1])
        if update:
            self.Refresh()

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        sizer_panel.Add(self.leftbtn, 0, 0, 0)
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.TOP, cw.wins(3))
        sizer_panel.AddStretchSpacer(1)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 0, 0, 0)
        sizer_1.Add(self.titlepanel, 0, 0, 0)
        sizer_1.Add(self.notebook, 0, 0, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

class StandbyCharaInfo(CharaInfo):
    def __init__(self, parent, headers, index, redrawfunc, is_playingscenario=False, party=None):
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

        CharaInfo.__init__(self, parent, redrawfunc, editable, party=party)

class StandbyPartyCharaInfo(StandbyCharaInfo):
    def __init__(self, parent, partyheader, redrawfunc):
        party = cw.data.Party(partyheader, True)
        partyheader.data = party
        headers = []
        for memberpath in party.get_memberpaths():
            headers.append(cw.cwpy.ydata.create_advheader(memberpath))

        StandbyCharaInfo.__init__(self, parent, headers, 0, redrawfunc, partyheader.is_adventuring(), party=party)

class ActiveCharaInfo(CharaInfo):
    def __init__(self, parent):
        self.is_playingscenario = cw.cwpy.is_playingscenario()
        self.ccard = cw.cwpy.selection

        if isinstance(self.ccard, cw.character.Player):
            if cw.cwpy.is_debugmode():
                self.list = cw.cwpy.get_pcards()
            else:
                self.list = cw.cwpy.get_pcards("unreversed")
        elif isinstance(self.ccard, cw.character.Enemy):
            if cw.cwpy.is_debugmode():
                self.list = cw.cwpy.get_ecards()
            else:
                self.list = []
                for card in cw.cwpy.get_ecards("unreversed"):
                    if card.is_analyzable():
                        self.list.append(card)
        else:
            self.list = cw.cwpy.get_fcards()[:]
            self.list.reverse()

        self.index = self.list.index(self.ccard)
        CharaInfo.__init__(self, parent, None, True)

class TopPanel(wx.Panel):
    """
    顔画像などを描画するパネル
    """
    def __init__(self, parent, ccard, redrawfunc):
        wx.Panel.__init__(self, parent, -1, size=(parent.width, cw.wins(105)))
        self.SetDoubleBuffered(True)
        #カードワース本来の背景値。暗くなりすぎるので保留
        #将来的にはスキンオプション化出来た方が良いかも
        #self.SetBackgroundColour(wx.Colour(192, 192, 192))
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
            self.race = cw.cwpy.setting.unknown_race

            for coupon in self.ccard.data.getfind("Property/Coupons"):
                if coupon.text in ages:
                    self.age = coupon.text.replace(u"＿", "", 1)
                elif coupon.text in sexs:
                    self.sex = coupon.text.replace(u"＿", "", 1)
                elif coupon.text == u"＠ＥＰ":
                    self.ep = coupon.get("value")
                elif coupon.text.startswith(u"＠Ｒ"):
                    for race in cw.cwpy.setting.races:
                        if coupon.text == u"＠Ｒ" + race.name:
                            self.race = race
                            break
        else:
            self.sex = u""
            self.age = u""
            self.ep = u""
            self.race = cw.cwpy.setting.unknown_race

        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        backcolor = self.GetBackgroundColour()

        dc.BeginDrawing()
        # カード画像の後ろにある羽みたいなの
        cw.util.draw_center(dc, self.wing, (self.Parent.width/2, cw.wins(52)))
        # カード画像
        x = (dc.GetSize()[0] - cw.wins(74)) / 2

        infos = cw.image.get_imageinfos(self.ccard.data.find("Property"))
        can_loaded_scaledimage = self.ccard.data.getbool(".", "scaledimage", False)
        setpos = any(map(lambda info: not info.postype in (None, "Default"), infos))

        for info in infos:
            path = info.path
            if isinstance(cw.cwpy.selection, (cw.character.Enemy,
                                                cw.character.Friend)):
                path = cw.util.get_materialpath(path, cw.M_IMG)
            elif not cw.binary.image.path_is_code(path):
                path = cw.util.join_yadodir(path)

            bmp = cw.util.load_wxbmp(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
            bmp2 = cw.wins(bmp)

            if setpos:
                baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                         basecardtype="LargeCard",
                                                         cardpostype="NotCard")
            else:
                baserect = cw.wins(pygame.Rect(0, 0, 0, 0))

            cw.imageretouch.wxblit_2bitbmp_to_card(dc, bmp2, x+baserect.x, cw.wins(5)+baserect.y, True, bitsizekey=bmp)

        # レベル
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam" , pixelsize=cw.wins(16)))
        coupons = self.ccard.get_specialcoupons()
        maxlevel = False
        baselevel = self.ccard.level
        if u"＠レベル原点" in coupons and self.ccard.level <> coupons[u"＠レベル原点"]:
            baselevel = coupons[u"＠レベル原点"]
            s = "Level: %d / %d" % (self.ccard.level, baselevel)
        else:
            s = "Level: %d" % (self.ccard.level)
        if u"＠レベル上限" in coupons and coupons[u"＠レベル上限"] <= baselevel:
            # max
            dc.SetTextForeground(wx.RED)
            if 1 < len(cw.cwpy.setting.races):
                cw.util.draw_witharound_simple(dc, "max", cw.wins(25), cw.wins(17), backcolor)
            else:
                cw.util.draw_witharound_simple(dc, "max", cw.wins(25), cw.wins(20), backcolor)
            maxlevel = True
        dc.SetTextForeground(wx.BLACK)
        cw.util.draw_witharound_simple(dc, s, cw.wins(5), cw.wins(5), backcolor)

        # 次のレベルまで割合バー
        if cw.cwpy.setting.show_experiencebar and isinstance(self.ccard, cw.character.Player) and not maxlevel:
            exp = self.ccard.get_couponsvalue()
            curexp = baselevel * (baselevel-1)
            nextlevel = baselevel + 1
            nextexp = nextlevel * (nextlevel-1)

            prange = nextexp - curexp
            x = cw.wins(5)+1
            y = cw.wins(23)+1
            w = cw.wins(42)-2
            h = cw.wins(5)-2
            hr = max(2, h/3)
            rad = math.radians(45)
            colour = wx.Colour(216, 216, 216)
            dc.SetPen(wx.Pen(colour))
            dc.SetBrush(wx.Brush(colour))
            dc.DrawRectangle(x-1, y-1, w+2, hr)
            dc.SetPen(wx.WHITE_PEN)
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.DrawRectangle(x-1, y-1+hr, w+2, h+2-hr)
            hr -= 1
            dc.SetPen(wx.TRANSPARENT_PEN)
            if exp < curexp:
                lcolor = wx.Colour(192, 32, 32)
                dcolor = wx.Colour(64, 0, 0)
                val = curexp - exp
                w2 = min(w, int(w * (float(val) / prange)))
                dc.SetBrush(wx.Brush(dcolor))
                dc.DrawRectangle(x+w-w2, y, w2, hr)
                dc.SetBrush(wx.Brush(lcolor))
                dc.DrawRectangle(x+w-w2, y+hr, w2, h-hr)
                linecolour = wx.Colour(128, 128, 128)
            else:
                if nextexp <= exp:
                    lcolor = wx.Colour(128, 224, 128)
                    dcolor = wx.Colour(64, 160, 64)
                else:
                    lcolor = wx.Colour(192, 192, 255)
                    dcolor = wx.Colour(128, 128, 192)
                val = exp - curexp
                if 0 < val:
                    w2 = min(w, int(w * (float(val) / prange)))
                    dc.SetBrush(wx.Brush(dcolor))
                    dc.DrawRectangle(x, y, w2, hr)
                    dc.SetBrush(wx.Brush(lcolor))
                    dc.DrawRectangle(x, y+hr, w2, h-hr)
                linecolour = wx.Colour(128, 128, 128)
            gcdc = wx.GCDC(dc)
            gcdc.SetPen(wx.Pen(linecolour))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
            gcdc.DrawRoundedRectangle(x-1, y-1, w+2, h+2, rad)
            gcdc.EndDrawing()

        self.baselevel = baselevel

        # 名前
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam2", pixelsize=cw.wins(16)))
        s = self.ccard.name
        w = dc.GetTextExtent(s)[0]
        width2 = self.Parent.width - cw.wins(5)
        cw.util.draw_witharound_simple(dc, s, width2 - w, cw.wins(3), backcolor)

        if not (isinstance(self.ccard, cw.sprite.card.EnemyCard) or\
                isinstance(self.ccard, cw.sprite.card.FriendCard)):
            if 1 == len(cw.cwpy.setting.races) and isinstance(cw.cwpy.setting.races[0], cw.header.UnknownRaceHeader):
                # EP
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam", pixelsize=cw.wins(14)))
                s = "EP: " + self.ep
                cw.util.draw_witharound_simple(dc, s, cw.wins(8), cw.wins(84), backcolor)
            else:
                # EP
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam", pixelsize=cw.wins(14)))
                s = "EP: " + self.ep
                isalbum = self.ccard.data.getroot().tag == "Album"
                if isalbum or not cw.cwpy.setting.show_experiencebar:
                    cw.util.draw_witharound_simple(dc, s, cw.wins(5), cw.wins(22), backcolor)
                else:
                    cw.util.draw_witharound_simple(dc, s, cw.wins(5), cw.wins(32), backcolor)
                # 種族
                if not isinstance(self.race, cw.header.UnknownRaceHeader):
                    s = self.race.name
                    dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam2", pixelsize=cw.wins(16)))
                    w = dc.GetTextExtent(s)[0]
                    cw.util.draw_witharound_simple(dc, s, cw.wins(5), cw.wins(82), backcolor)
            # 年代
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("charaparam2", pixelsize=cw.wins(16)))
            s = self.age + self.sex
            w = dc.GetTextExtent(s)[0]
            cw.util.draw_witharound_simple(dc, s, width2 - w, cw.wins(82), backcolor)
            dc.EndDrawing()

        # 親ウィンドウの再描画を行える場合は呼び出し
        if self.redrawfunc:
            self.redrawfunc()

        if update:
            self.Refresh()

    def get_detailtext(self):
        lines = []
        level = u"%s" % (self.ccard.level)
        s = u"[ %s ] Level %s" % (self.ccard.name, level)
        if not isinstance(self.race, cw.header.UnknownRaceHeader):
            s += u" / %s" % (self.race.name)
        if self.sex or self.age:
            s += u" / %s%s" % (self.age, self.sex)
        if self.ep:
            s += u" / EP %s" % self.ep
        lines.append(s)

        return u"\n".join(lines)


class TitlePanel(wx.Panel):
    """
    タイトルバーを描画するパネルを作る。
    """
    def __init__(self, parent, notebook):
        wx.Panel.__init__(self, parent, -1, size=(parent.width, cw.wins(24)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.notebook = notebook
        self.is_playingscenario = cw.cwpy.is_playingscenario()

        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.OnCancel)

    def draw(self, update=False):
        self.Refresh()

    def OnPaint(self, event):
        index = self.notebook.GetSelection()
        if index == 0:
            self.text = cw.cwpy.msgs["description"]
        elif index == 1:
            self.text = cw.cwpy.msgs["history"]
        elif index == 2:
            if self.is_playingscenario:
                self.text = cw.cwpy.msgs["status"]
            else:
                self.text = cw.cwpy.msgs["edit"]
        elif index == 3:
            self.text = cw.cwpy.msgs["skillcard"]
        elif index == 4:
            self.text = cw.cwpy.msgs["itemcard"]
        else:
            self.text = cw.cwpy.msgs["beastcard"]

        dc = wx.PaintDC(self)
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        csize = self.GetClientSize()
        te = dc.GetTextExtent(self.text)
        x = (csize[0] - te[0]) / 2
        y = (csize[1] - te[1]) / 2
        dc.DrawText(self.text, x, y)

class DescPanel(wx.ScrolledWindow):
    """
    解説文を描画するパネル。
    """
    def __init__(self, parent, ccard, editable):
        wx.ScrolledWindow.__init__(self, parent, -1, size=(parent.Parent.width-cw.wins(8), cw.wins(173)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.csize = self.GetClientSize()
        self.SetBackgroundColour(wx.Colour(0, 0, 128))

        # エレメントオブジェクト
        self.ccard = ccard
        self.headers = []
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

        if cw.cwpy.debug and editable and isinstance(ccard, cw.sprite.card.PlayerCard):
            self.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.draw(True)

    def OnLeftUp(self, event):
        cw.cwpy.play_sound("click")
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.charaedit.CharacterEditDialog(parent, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            self.Parent.Parent.toppanel.Refresh()
            self.draw(True)
            self.Parent.Parent.historypanel.draw(True)

    def _init_view(self):
        self.text = self.ccard.data.gettext("Property/Description", "")
        self.text = cw.util.txtwrap(self.text, 4)
        dc = wx.ClientDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        maxheight = len(self.text.splitlines())*cw.wins(13)
        maxheight += cw.wins(7)+cw.wins(2)

        self._ratey = cw.wins(13)
        maxheight = (maxheight + self._ratey - 1) // self._ratey * self._ratey
        self.SetScrollRate(cw.wins(10), self._ratey)

        self.SetVirtualSize((-1, maxheight))
        self.Scroll(0, 0)
        self.Refresh()

    def draw(self, update=False):
        if update:
            self._init_view()

    def OnPaint(self, event):
        csize = self.GetClientSize()
        vx, vy = self.GetViewStart()
        vx *= cw.wins(10)
        vy *= self._ratey

        dc = wx.PaintDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        maxwidth = dc.GetTextExtent(u"―"*19)[0]
        x = (csize[0]-maxwidth) / 2

        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-self.watermark.GetWidth())/2, (self.csize[1]-self.watermark.GetHeight())/2, True)

        # 解説文
        dc.SetTextForeground(wx.WHITE)
        x = x-vx
        y = cw.wins(7) - vy
        for line in self.text.splitlines():
            dc.DrawText(line, x, y)
            y += cw.wins(13)

    def get_detailtext(self):
        return self.text


class HistoryPanel(wx.ScrolledWindow):
    """
    クーポンを描画するスクロールウィンドウ。
    """
    def __init__(self, parent, ccard, editable):
        wx.ScrolledWindow.__init__(self, parent, -1, size=(parent.Parent.width-cw.wins(8), cw.wins(173)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.csize = self.GetClientSize()
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.gold = cw.cwpy.rsrc.dialogs["STATUS3"]
        self.silver = cw.cwpy.rsrc.dialogs["STATUS2"]
        self.bronze = cw.cwpy.rsrc.dialogs["STATUS1"]
        self.black = cw.cwpy.rsrc.dialogs["STATUS0"]
        self.gold_s = self._get_bmps("STATUS3")
        self.silver_s = self._get_bmps("STATUS2")
        self.bronze_s = self._get_bmps("STATUS1")
        self.black_s = self._get_bmps("STATUS0")
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)
        # create buffer
        self.draw(True)

        if cw.cwpy.debug and editable and isinstance(ccard, cw.sprite.card.PlayerCard):
            self.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def _get_bmps(self, name):
        bmp = cw.cwpy.rsrc.dialogs[name]
        x, y = cw.wins(0), cw.wins(0)
        w, h = bmp.GetWidth(), bmp.GetHeight()

        img = bmp.ConvertToImage()
        img.SetAlphaData(chr(128) * (w*h))
        bmp = img.ConvertToBitmap()
        wxbmp = wx.EmptyBitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(wxbmp)
        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 255)))
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 255)))
        dc.DrawRectangle(-1, -1, w+2, h+2)
        dc.DrawBitmap(bmp, x, y)
        dc.SelectObject(wx.NullBitmap)
        return wxbmp

    def OnLeftUp(self, event):
        cw.cwpy.play_sound("click")
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.edit.CouponEditDialog(parent, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            def func(panel):
                def func(panel):
                    try:
                        panel.draw(True)
                        panel.Parent.Parent.toppanel.Refresh()
                    except:
                        pass
                cw.cwpy.frame.exec_func(func, panel)
            cw.cwpy.exec_func(func, self)

    def draw(self, update=False):
        if update:
            self._init_view()

    def _init_view(self):
        csize = self.csize

        # クーポンリスト
        self.coupons = []

        isalbum = self.ccard.data.getroot().tag == "Album"

        for coupon in self.ccard.data.getfind("Property/Coupons"):
            if coupon.text and not coupon.text.startswith(u"＠"):
                if isalbum and (coupon.text.startswith(u"：") or coupon.text.startswith(u"；")):
                    continue
                if cw.cwpy.debug or not self.is_hidden(coupon.text):
                    self.coupons.append((coupon.text, int(coupon.get("value"))))
        self.coupons.reverse()

        # maxheght, maxwidth計算
        dc = wx.ClientDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))

        h = self.gold.GetSize()[1]
        maxheight = (h + cw.wins(5)) * len(self.coupons)
        maxwidth = 0
        for coupon in self.coupons:
            maxwidth = max(dc.GetTextExtent(coupon[0])[0] + cw.wins(32)+cw.wins(12), maxwidth)

        if maxwidth <= csize[0]:
            maxwidth = -1
        if maxheight <= csize[1]:
            maxheight = -1

        if maxwidth <> -1:
            maxheight += cw.ppis(5)+cw.wins(2)

        self._ratey = self.gold.GetSize()[1] + cw.wins(5)
        if maxheight <> -1:
            maxheight = (maxheight + self._ratey - 1) // self._ratey * self._ratey
        self.SetScrollRate(cw.wins(10), self._ratey)

        self.SetVirtualSize((maxwidth, maxheight))
        self.Scroll(0, 0)
        self.Refresh()

    def is_hidden(self, coupon):
        return coupon.startswith(u"＿") or\
               coupon.startswith(u"：") or\
               coupon.startswith(u"；")

    def OnPaint(self, event):
        csize = self.GetClientSize()
        vx, vy = self.GetViewStart()
        vx *= cw.wins(10)
        vy *= self._ratey

        dc = wx.PaintDC(self)

        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-self.watermark.GetWidth())/2, (self.csize[1]-self.watermark.GetHeight())/2, True)

        # クーポン
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))

        lineheight = self.gold.GetSize()[1] + cw.wins(5)

        index = int(vy / lineheight)
        y = (index * lineheight) + cw.wins(10) - vy
        coupons = self.coupons[index:]
        gray = wx.Colour(160, 160, 160)
        for index, coupon in enumerate(coupons):
            text, value = coupon

            if self.is_hidden(text):
                dc.SetTextForeground(gray)
                if value > 1:
                    bmp = self.gold_s
                elif value == 1:
                    bmp = self.silver_s
                elif value == 0:
                    bmp = self.bronze_s
                else:
                    bmp = self.black_s
            else:
                dc.SetTextForeground(wx.WHITE)
                if value > 1:
                    bmp = self.gold
                elif value == 1:
                    bmp = self.silver
                elif value == 0:
                    bmp = self.bronze
                else:
                    bmp = self.black

            dc.DrawText(text, cw.wins(32) - vx, y)
            dc.DrawBitmap(bmp, cw.wins(12) - vx, y, True)
            y += lineheight
            if csize[1] <= y:
                break


    def get_detailtext(self):
        lines = []
        for text, value in self.coupons:
            if 0 <= value:
                lines.append(u"%s (+%s)" % (text, value))
            else:
                lines.append(u"%s (%s)" % (text, value))

        return u"\n".join(lines)


class EditButton():
    def __init__(self, name, btype):
        self.name = name
        self.type = btype
        self.negaflag = False

class EditPanel(wx.Panel):
    def __init__(self, parent, mlist, ccard):
        wx.Panel.__init__(self, parent, -1, size=(parent.Parent.width-cw.wins(8), cw.wins(173)), style=wx.SUNKEN_BORDER)
        self._destroy = False
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.list = mlist
        self.ccard = ccard
        self.selected = -1
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
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        self._destroy = True

    def OnLeftUp(self, event):
        for header in self.headers:
            if header.negaflag:
                if header.type == 0:
                    # デザインを変更する
                    cw.cwpy.play_sound("click")
                    dlg = cw.dialog.create.AdventurerDesignDialog(self.Parent.Parent, self.ccard)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        def func(panel):
                            if panel:
                                panel.Parent.Parent.toppanel.Refresh()
                                panel.Parent.Parent.descpanel.draw(True)
                        cw.cwpy.exec_func(cw.cwpy.frame.exec_func, func, self)
                    dlg.Destroy()
                else:
                    # レベルを調節する
                    cw.cwpy.play_sound("click")
                    mlist = self.get_charalist()
                    self.selected = mlist.index(self.ccard)
                    party = self.Parent.Parent.party
                    dlg = cw.dialog.edit.LevelEditDialog(self.Parent.Parent, mlist=mlist, selected=self.selected, party=party)
                    cw.cwpy.frame.move_dlg(dlg)
                    if wx.ID_OK == dlg.ShowModal():
                        def func(panel):
                            if panel:
                                panel.Parent.Parent.toppanel.Refresh()
                        self.update_charalist(mlist)
                        cw.cwpy.exec_func(cw.cwpy.frame.exec_func, func, self)
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

    def update_charalist(self, mlist):
        """編集結果をヘッダ等に反映する。"""
        if isinstance(self.Parent.Parent, StandbyPartyCharaInfo):
            def func(parentheaders, mlist):
                for i, header in enumerate(parentheaders):
                    ccard = mlist[i]
                    ccard.data.write_xml()
                    header.level = ccard.level
            cw.cwpy.exec_func(func, self.list, mlist)
        elif isinstance(self.Parent.Parent, StandbyCharaInfo):
            def func(index, headers, mlist):
                ccard = mlist[0]
                ccard.data.write_xml()
                headers[index].level = ccard.level
            cw.cwpy.exec_func(func, self.Parent.Parent.index, self.list, mlist)

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
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])
        self.Refresh()

    def OnMove(self, event):
        dc = wx.ClientDC(self)
        mousepos = event.GetPosition()

        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    self.draw_header(dc, header)
            elif header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
        self.Refresh()

    def draw_header(self, dc, header):
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        if header.negaflag:
            dc.SetTextForeground(wx.RED)
            dc.DrawText(header.name, header.textpos[0], header.textpos[1])
            dc.SetTextForeground(wx.WHITE)
        else:
            dc.DrawText(header.name, header.textpos[0], header.textpos[1])

    def up(self):
        if not self.headers:
            return
        dc = wx.ClientDC(self)
        for i, header in enumerate(self.headers):
            if header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
                header = self.headers[i-1]
                header.negaflag = True
                self.draw_header(dc, header)
                return
        header = self.headers[-1]
        header.negaflag = True
        self.draw_header(dc, header)

    def down(self):
        if not self.headers:
            return
        dc = wx.ClientDC(self)
        for i, header in enumerate(self.headers):
            if header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
                header = self.headers[(i+1) % len(self.headers)]
                header.negaflag = True
                self.draw_header(dc, header)
                return
        header = self.headers[0]
        header.negaflag = True
        self.draw_header(dc, header)

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-self.watermark.GetWidth())/2, (self.csize[1]-self.watermark.GetHeight())/2, True)

        # 編集ボタン
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))

        # 編集アイコン
        bmp = cw.cwpy.rsrc.dialogs["STATUS12"]

        # 編集項目名
        height = cw.wins(10)
        if not self.headers:
            self.headers = (EditButton(cw.cwpy.msgs["edit_design"], 0), EditButton(cw.cwpy.msgs["regulate_level"], 1))
        for header in self.headers:
            if header.negaflag:
                dc.SetTextForeground(wx.RED)
            else:
                dc.SetTextForeground(wx.WHITE)
            size = dc.GetTextExtent(header.name)
            dc.DrawBitmap(bmp, cw.wins(12), height - cw.wins(1), True)
            dc.DrawText(header.name, cw.wins(32), height)
            header.textpos = (cw.wins(32), height)
            header.subrect = pygame.Rect(cw.wins(12), height - cw.wins(1), cw.wins(20) + size[0], bmp.Height)
            height += cw.wins(17)

        if update:
            self.Refresh()

    def get_detailtext(self):
        return u""


class StatusPanel(wx.ScrolledWindow):
    def __init__(self, parent, mlist, ccard, editable):
        wx.ScrolledWindow.__init__(self, parent, -1, size=(parent.Parent.width-cw.wins(8), cw.wins(173)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        self.list = mlist
        # エレメントオブジェクト
        self.ccard = ccard
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.Parent.OnCancel)

        if cw.cwpy.debug and editable and not isinstance(self.Parent.Parent, StandbyPartyCharaInfo):
            self.SetCursor(cw.cwpy.rsrc.cursors["CURSOR_FINGER"])
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.draw(True)

    def OnLeftUp(self, event):
        cw.cwpy.play_sound("click")
        parent = self.GetTopLevelParent()
        selected = self.Parent.Parent.index
        dlg = cw.debug.statusedit.StatusEditDialog(parent, mlist=self.list, selected=selected)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            self.draw(True)

    def _init_view(self):
        maxheight = cw.wins(0)
        ln = cw.wins(17)
        maxheight += ln
        if self.ccard.is_poison():
            maxheight += ln
        if self.ccard.is_paralyze():
            maxheight += ln
        if self.ccard.mentality_dur and self.ccard.mentality <> "Normal":
            maxheight += ln
        if self.ccard.is_bind():
            maxheight += ln
        if self.ccard.is_silence():
            maxheight += ln
        if self.ccard.is_faceup():
            maxheight += ln
        if self.ccard.is_antimagic():
            maxheight += ln
        if self.ccard.enhance_act and self.ccard.enhance_act_dur:
            maxheight += ln
        if self.ccard.enhance_avo and self.ccard.enhance_avo_dur:
            maxheight += ln
        if self.ccard.enhance_res and self.ccard.enhance_res_dur:
            maxheight += ln
        if self.ccard.enhance_def and self.ccard.enhance_def_dur:
            maxheight += ln

        maxheight+cw.wins(2)

        self._ratey = cw.wins(17)
        maxheight = (maxheight + self._ratey - 1) // self._ratey * self._ratey
        self.SetScrollRate(cw.wins(10), self._ratey)

        self.SetVirtualSize((-1, maxheight))
        self.Scroll(0, 0)
        self.Refresh()

    def draw(self, update=False):
        if update:
            self._init_view()

    def OnPaint(self, event):
        csize = self.GetClientSize()
        vx, vy = self.GetViewStart()
        vx *= cw.wins(10)
        vy *= self._ratey

        dc = wx.PaintDC(self)

        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-self.watermark.GetWidth())/2, (self.csize[1]-self.watermark.GetHeight())/2, True)

        # 状態
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))

        height = cw.wins(8) - vy

        # 生命力の割合
        bmp = cw.cwpy.rsrc.wxstatuses["LIFE"]
        colour, msg = self._get_life()

        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(cw.wins(12), height - cw.wins(1), bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, cw.wins(12), height - cw.wins(1), True)
        dc.DrawText(msg, cw.wins(32), height)
        height += cw.wins(17)

        # 肉体状態異常
        if self.ccard.is_poison():
            height = self._draw_status(dc, self._get_poison(), "BODY0", height)
        if self.ccard.is_paralyze():
            if self.ccard.is_petrified():
                height = self._draw_status(dc, self._get_petrified(), "BODY1", height)
            else:
                height = self._draw_status(dc, self._get_paralyze(), "BODY1", height)

        # 精神状態異常
        s, icon = self._get_mentality()
        if icon:
            height = self._draw_status(dc, s, icon, height)

        # 魔法的状態異常
        if self.ccard.is_bind():
            height = self._draw_status(dc, self._get_bind(), "MAGIC0", height)
        if self.ccard.is_silence():
            height = self._draw_status(dc, self._get_silence(), "MAGIC1", height)
        if self.ccard.is_faceup():
            height = self._draw_status(dc, self._get_faceup(), "MAGIC2", height)
        if self.ccard.is_antimagic():
            height = self._draw_status(dc, self._get_antimagic(), "MAGIC3", height)

        # 能力ボーナス・ペナルティ
        height = self._draw_enhance(dc, cw.cwpy.msgs["enhance_action"], self.ccard.enhance_act,
                                    self.ccard.enhance_act_dur, "UP0", "DOWN0", height)
        height = self._draw_enhance(dc, cw.cwpy.msgs["enhance_avoid"], self.ccard.enhance_avo,
                                    self.ccard.enhance_avo_dur, "UP1", "DOWN1", height)
        height = self._draw_enhance(dc, cw.cwpy.msgs["enhance_resist"], self.ccard.enhance_res,
                                    self.ccard.enhance_res_dur, "UP2", "DOWN2", height)
        height = self._draw_enhance(dc, cw.cwpy.msgs["enhance_defense"], self.ccard.enhance_def,
                                    self.ccard.enhance_def_dur, "UP3", "DOWN3", height)

    def get_detailtext(self):
        lines = []
        _colour, msg = self._get_life()
        lines.append(msg)

        # 肉体状態異常
        if self.ccard.is_poison():
            lines.append(self._get_poison())
        if self.ccard.is_paralyze():
            if self.ccard.is_petrified():
                lines.append(self._get_petrified())
            else:
                lines.append(self._get_paralyze())

        # 精神状態異常
        msg, icon = self._get_mentality()
        if icon:
            lines.append(msg)

        # 魔法的状態異常
        if self.ccard.is_bind():
            lines.append(self._get_bind())
        if self.ccard.is_silence():
            lines.append(self._get_silence())
        if self.ccard.is_faceup():
            lines.append(self._get_faceup())
        if self.ccard.is_antimagic():
            lines.append(self._get_antimagic())

        # 能力ボーナス・ペナルティ
        _colour, _bmp, msg = self._get_enhance(cw.cwpy.msgs["enhance_action"], self.ccard.enhance_act,
                                    self.ccard.enhance_act_dur, "UP0", "DOWN0")
        if msg:
            lines.append(msg)
        _colour, _bmp, msg = self._get_enhance(cw.cwpy.msgs["enhance_avoid"], self.ccard.enhance_avo,
                                    self.ccard.enhance_avo_dur, "UP1", "DOWN1")
        if msg:
            lines.append(msg)
        _colour, _bmp, msg = self._get_enhance(cw.cwpy.msgs["enhance_resist"], self.ccard.enhance_res,
                                    self.ccard.enhance_res_dur, "UP2", "DOWN2")
        if msg:
            lines.append(msg)
        _colour, _bmp, msg = self._get_enhance(cw.cwpy.msgs["enhance_defense"], self.ccard.enhance_def,
                                    self.ccard.enhance_def_dur, "UP3", "DOWN3")
        if msg:
            lines.append(msg)

        return u"\n".join(lines)

    def _get_life(self):
        if self.ccard.is_unconscious():
            colour = wx.Colour(0, 0, 128)
            msg = cw.cwpy.msgs["unconscious"]
        elif self.ccard.is_heavyinjured():
            colour = wx.Colour(127, 0, 0)
            msg = cw.cwpy.msgs["heavy_injured"]
        elif self.ccard.is_injured():
            colour = wx.Colour(0, 153, 187)
            msg = cw.cwpy.msgs["injured"]
        else:
            colour = wx.Colour(192, 192, 192)
            msg = cw.cwpy.msgs["fine"]
        return colour, msg

    def _get_poison(self):
        return u"%s (%s)" % (cw.cwpy.msgs["poison"], cw.cwpy.msgs["intensity"] % self.ccard.poison)

    def _get_paralyze(self):
        return u"%s (%s)" % (cw.cwpy.msgs["paralyze"], cw.cwpy.msgs["intensity"] % self.ccard.paralyze)

    def _get_petrified(self):
        return u"%s (%s)" % (cw.cwpy.msgs["petrified"], cw.cwpy.msgs["intensity"] % self.ccard.paralyze)

    def _get_mentality(self):
        dur = cw.cwpy.msgs["duration"] % self.ccard.mentality_dur
        if self.ccard.is_sleep():
            return u"%s (%s)" % (cw.cwpy.msgs["sleep"], dur), "MIND1"
        elif self.ccard.is_confuse():
            return u"%s (%s)" % (cw.cwpy.msgs["confuse"], dur), "MIND2"
        elif self.ccard.is_overheat():
            return u"%s (%s)" % (cw.cwpy.msgs["overheat"], dur), "MIND3"
        elif self.ccard.is_brave():
            return u"%s (%s)" % (cw.cwpy.msgs["brave"], dur), "MIND4"
        elif self.ccard.is_panic():
            return u"%s (%s)" % (cw.cwpy.msgs["panic"], dur), "MIND5"
        else:
            return u"", ""

    def _get_bind(self):
        return u"%s (%s)" % (cw.cwpy.msgs["bind"], cw.cwpy.msgs["duration"] % self.ccard.bind)

    def _get_silence(self):
        return u"%s (%s)" % (cw.cwpy.msgs["silence"], cw.cwpy.msgs["duration"] % self.ccard.silence)

    def _get_faceup(self):
        return u"%s (%s)" % (cw.cwpy.msgs["faceup"], cw.cwpy.msgs["duration"] % self.ccard.faceup)

    def _get_antimagic(self):
        return u"%s (%s)" % (cw.cwpy.msgs["antimagic"], cw.cwpy.msgs["duration"] % self.ccard.antimagic)

    def _draw_status(self, dc, msg, imgname, height):
        bmp = cw.cwpy.rsrc.wxstatuses[imgname]
        dc.DrawBitmap(bmp, cw.wins(12), height - cw.wins(1))
        dc.DrawText(msg, cw.wins(32), height)
        self.Refresh()
        return height + cw.wins(17)

    def _get_enhance(self, enhname, value, dur, enhimage, pnlimage):
        if 0 == value:
            return None, None, u""

        dur = cw.cwpy.msgs["duration"] % dur

        if 10 <= value:
            colour = wx.Colour(255, 0, 0)
            bmp = cw.cwpy.rsrc.wxstatuses[enhimage]
            msg = (cw.cwpy.msgs["maximum_bonus"] + u" (%s)") % (enhname, dur)
        elif 7 <= value:
            colour = wx.Colour(175, 0, 0)
            bmp = cw.cwpy.rsrc.wxstatuses[enhimage]
            msg = (cw.cwpy.msgs["big_bonus"] + u" (%s)") % (enhname, dur)
        elif 4 <= value:
            colour = wx.Colour(127, 0, 0)
            bmp = cw.cwpy.rsrc.wxstatuses[enhimage]
            msg = (cw.cwpy.msgs["middle_bonus"] + u" (%s)") % (enhname, dur)
        elif 1 <= value:
            colour = wx.Colour(79, 0, 0)
            bmp = cw.cwpy.rsrc.wxstatuses[enhimage]
            msg = (cw.cwpy.msgs["small_bonus"] + u" (%s)") % (enhname, dur)
        elif -10 >= value:
            colour = wx.Colour(0, 0, 51)
            bmp = cw.cwpy.rsrc.wxstatuses[pnlimage]
            msg = (cw.cwpy.msgs["maximum_penalty"] + u" (%s)") % (enhname, dur)
        elif -7 >= value:
            colour = wx.Colour(0, 0, 85)
            bmp = cw.cwpy.rsrc.wxstatuses[pnlimage]
            msg = (cw.cwpy.msgs["big_penalty"] + u" (%s)") % (enhname, dur)
        elif -4 >= value:
            colour = wx.Colour(0, 0, 136)
            bmp = cw.cwpy.rsrc.wxstatuses[pnlimage]
            msg = (cw.cwpy.msgs["middle_penalty"] + u" (%s)") % (enhname, dur)
        elif -1 >= value:
            colour = wx.Colour(0, 0, 187)
            bmp = cw.cwpy.rsrc.wxstatuses[pnlimage]
            msg = (cw.cwpy.msgs["small_penalty"] + u" (%s)") % (enhname, dur)

        return colour, bmp, msg

    def _draw_enhance(self, dc, enhname, value, dur, enhimage, pnlimage, height):
        if 0 == value:
            return height
        colour, bmp, msg = self._get_enhance(enhname, value, dur, enhimage, pnlimage)
        dc.SetBrush(wx.Brush(colour, wx.SOLID))
        dc.DrawRectangle(cw.wins(12), height - cw.wins(1), bmp.Width, bmp.Height)
        dc.DrawBitmap(bmp, cw.wins(12), height - cw.wins(1), True)
        dc.DrawText(msg, cw.wins(32), height)
        self.Refresh()
        return height + cw.wins(17)


class CardPanel(wx.Panel):
    def __init__(self, parent, ccard, pocket):
        wx.Panel.__init__(self, parent, -1, size=(parent.Parent.width-cw.wins(8), cw.wins(173)), style=wx.SUNKEN_BORDER)
        self.SetDoubleBuffered(True)
        self.SetBackgroundColour(wx.Colour(0, 0, 128))
        self.csize = self.GetClientSize()
        # エレメントオブジェクト
        self.ccard = ccard
        # 所持カードの種別
        self.pocket = pocket
        # headers
        self.headers = []
        # bmp
        self.watermark = cw.cwpy.rsrc.dialogs["PAD"]
        # 「全てホールド」の領域
        if self.pocket <> cw.POCKET_BEAST and (cw.cwpy.debug or isinstance(self.ccard, cw.character.Player)):
            self.hold_all = HoldAll()
        else:
            self.hold_all = None
        # bind
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMove)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnDestroy(self, event):
        for header in self.headers:
            if hasattr(header, "textpos"):
                del header.textpos
                del header.subrect

    def OnLeftUp(self, event):
        self._switch_hold()

    def OnKeyUp(self, event):
        if event.GetKeyCode() == wx.WXK_SPACE:
            self._switch_hold()

    def _switch_hold(self):
        if not cw.cwpy.debug and not isinstance(self.ccard, cw.character.Player):
            # ホールド不可
            self._open_cardinfo()
            return

        if self.hold_all and self.hold_all.negaflag:
            cw.cwpy.play_sound("click")
            self.ccard.set_hold_all(self.pocket, not self.ccard.hold_all[self.pocket])
            self.Refresh()
            return

        for header in self.headers:
            if header.negaflag:
                # ホールド状態切り替え(召喚獣以外)
                dc = wx.ClientDC(self)
                if header.penalty:
                    cw.cwpy.play_sound("error")
                    return
                cw.cwpy.play_sound("click")
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                header.set_hold(not header.hold)
                if header.hold:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                else:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
                dc.DrawBitmap(bmp, header.subrect.left, header.subrect.top, True)
                self.Refresh()
                return

    def _open_cardinfo(self):
        for header in self.headers:
            if header.negaflag:
                cw.cwpy.play_sound("click")
                dlg = cardinfo.YadoCardInfo(self.Parent.Parent, self.headers, header)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
                self.draw(True)
                return True
        return False

    def OnRightUp(self, event):
        if self._open_cardinfo():
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
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
                s = header.name
                dc.DrawText(s, header.textpos[0], header.textpos[1])
        self.Refresh()

    def OnMove(self, event):
        dc = wx.ClientDC(self)
        mousepos = event.GetPosition()

        if self.hold_all:
            self.hold_all.negaflag = self.hold_all.subrect.collidepoint(mousepos)

        for header in self.headers:
            if header.subrect.collidepoint(mousepos):
                if not header.negaflag:
                    header.negaflag = True
                    self.draw_header(dc, header)
            elif header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
        self.Refresh()

    def draw_header(self, dc, header):
        if isinstance(header, HoldAll):
            self.Refresh()
            return
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))
        if header.negaflag:
            dc.SetTextForeground(wx.RED)
            dc.DrawText(header.name, header.textpos[0], header.textpos[1])
            dc.SetTextForeground(wx.WHITE)
        else:
            dc.DrawText(header.name, header.textpos[0], header.textpos[1])

    def up(self):
        if not self.headers and not self.hold_all:
            return
        if self.hold_all:
            headers = [self.hold_all]
            headers.extend(self.headers)
        else:
            headers = self.headers

        dc = wx.ClientDC(self)
        for i, header in enumerate(headers):
            if header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
                header = headers[i-1]
                header.negaflag = True
                self.draw_header(dc, header)
                return
        header = headers[-1]
        header.negaflag = True
        self.draw_header(dc, header)

    def down(self):
        if not self.headers and not self.hold_all:
            return
        if self.hold_all:
            headers = [self.hold_all]
            headers.extend(self.headers)
        else:
            headers = self.headers

        dc = wx.ClientDC(self)
        for i, header in enumerate(headers):
            if header.negaflag:
                header.negaflag = False
                self.draw_header(dc, header)
                header = headers[(i+1) % len(headers)]
                header.negaflag = True
                self.draw_header(dc, header)
                return
        header = headers[0]
        header.negaflag = True
        self.draw_header(dc, header)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            self.ClearBackground()
        else:
            dc = wx.PaintDC(self)

        dc.BeginDrawing()
        # 背景の透かし
        dc.DrawBitmap(self.watermark, (self.csize[0]-self.watermark.GetWidth())/2, (self.csize[1]-self.watermark.GetHeight())/2, True)
        # 所持スキル
        dc.SetTextForeground(wx.WHITE)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("charadesc", pixelsize=cw.wins(13)))

        if not self.headers:
            self.headers = self.ccard.cardpocket[self.pocket]

        fw = dc.GetTextExtent(u"―")[0]

        if self.hold_all:
            yp = 20
            s = cw.cwpy.msgs["hold_all"]
            if self.hold_all.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, cw.wins(30), cw.wins(30))
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, cw.wins(30), cw.wins(30))
            if self.ccard.hold_all[self.pocket]:
                bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
            else:
                bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
            dc.DrawBitmap(bmp, cw.wins(10), cw.wins(29), True)
            size = dc.GetTextExtent(s)
            self.hold_all.subrect = pygame.Rect(cw.wins(10), cw.wins(29), size[0] + cw.wins(20), size[1] + cw.wins(2))
        else:
            yp = 0

        for index, header in enumerate(self.headers):
            if index < 5:
                pos = cw.wins((30, 30+yp+17*index))
            else:
                pos = (self.csize[0]/2+cw.wins(30-6), cw.wins(30+yp+17*(index-5)))

            # カード名
            s = header.name
            size = dc.GetTextExtent(s)
            if header.type in ("ItemCard", "BeastCard") and (header.uselimit or header.recycle):
                s += "(%d)" % header.uselimit

            if header.negaflag:
                dc.SetTextForeground(wx.RED)
                dc.DrawText(s, pos[0], pos[1])
                dc.SetTextForeground(wx.WHITE)
            else:
                dc.DrawText(s, pos[0], pos[1])

            # rect
            header.textpos = pos
            header.subrect = pygame.Rect(pos[0] - cw.wins(20), pos[1] - cw.wins(1), size[0] + cw.wins(20), size[1] + cw.wins(2))
            if header.type == "SkillCard":
                # 適性値
                key = "HAND%s" % (header.get_showed_vocation_level(self.ccard))
                bmp = cw.cwpy.rsrc.wxstones[key]
                dc.DrawBitmap(bmp, pos[0]+(fw*6)+cw.wins(1), pos[1]-cw.wins(1), True)
                # 使用回数
                key = "HAND%s" % (header.get_uselimit_level() + 5)
                bmp = cw.cwpy.rsrc.wxstones[key]
                dc.DrawBitmap(bmp, pos[0]+(fw*6 + cw.wins(16)), pos[1]-cw.wins(1), True)

            if header.type == "BeastCard":
                # 召喚獣アイコン
                if header.attachment:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS10"]
                else:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS11"]
            else:
                # ホールドまたはペナルティ
                if header.penalty:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS7"]
                elif header.hold:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS6"]
                else:
                    bmp = cw.cwpy.rsrc.dialogs["STATUS5"]
            dc.DrawBitmap(bmp, pos[0]-cw.wins(20), pos[1]-cw.wins(1), True)

        # カード枚数
        dc.DrawText(self._get_cardnum(), cw.wins(10), cw.wins(10))
        dc.EndDrawing()

        if update:
            self.Refresh()

    def _get_cardnum(self):
        n = len(self.headers)
        maxn = self.ccard.get_cardpocketspace()[self.pocket]
        return cw.cwpy.msgs["card_number"] % (n, maxn)

    def get_detailtext(self):
        lines = []
        if self.ccard.hold_all[self.pocket]:
            lines.append(u"%s <%s>" % (self._get_cardnum(), cw.cwpy.msgs["hold_all"]))
        else:
            lines.append(self._get_cardnum())

        for header in self.headers:
            if header.penalty:
                s = u"X"
            elif header.hold:
                s = u"#"
            elif header.type == u"SkillCard":
                s = u"S"
            elif header.type == u"ItemCard":
                s = u"I"
            elif header.type == u"BeastCard":
                if header.attachment:
                    s = u"A"
                else:
                    s = u"B"

            s = u"[%s] %s" % (s, header.name)
            slen = cw.util.get_strlen(s)
            if slen < 26:
                s += u" " * (26-slen)
            vocation = u"|" * (header.get_showed_vocation_level(self.ccard)+1)
            uselimit = u"|" * header.get_uselimit_level()
            s = u"%s [%s] [%s]" % (s, vocation.ljust(4), uselimit.ljust(4))

            lines.append(s)

        return u"\n".join(lines)

class HoldAll(object):
    def __init__(self):
        self.negaflag = False
        self.subrect = pygame.Rect(0, 0, 0, 0)


class SkillPanel(CardPanel):
    def __init__(self, parent, ccard):
        CardPanel.__init__(self, parent, ccard, cw.POCKET_SKILL)


class ItemPanel(CardPanel):
    def __init__(self, parent, ccard):
        CardPanel.__init__(self, parent, ccard, cw.POCKET_ITEM)


class BeastPanel(SkillPanel):
    def __init__(self, parent, ccard):
        CardPanel.__init__(self, parent, ccard, cw.POCKET_BEAST)

    def OnLeftUp(self, event):
        # ホールド不可
        self._open_cardinfo()


def main():
    pass

if __name__ == "__main__":
    main()
