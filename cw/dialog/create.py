#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import pygame

import cw

#-------------------------------------------------------------------------------
#　不足データの補填ダイアログ
#-------------------------------------------------------------------------------

class AdventurerDataComp(wx.Dialog):
    def __init__(self, parent, ccard):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["insufficiency_title"],
                            style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU)
        self.ccard = ccard
        self.sex = cw.cwpy.setting.sexcoupons[0]
        self.age = cw.cwpy.setting.periodcoupons[0]
        # 画像
        bmp = cw.util.load_wxbmp(ccard.imgpath, True)
        self.bmp = wx.StaticBitmap(self, -1, bmp)
        # 各種テキスト
        s = cw.cwpy.msgs["insufficiency_message"]
        s = cw.util.txtwrap(s, 0, width=42, wrapschars=cw.util.WRAPS_CHARS)
        self.text_message = wx.StaticText(self, -1, s)
        self.box = wx.StaticBox(self, -1)
        self.text_name = wx.StaticText(self, -1, ccard.name)
        font = cw.cwpy.rsrc.get_wxfont()
        self.text_name.SetFont(font)
        self.text_caution = wx.StaticText(self, -1, cw.cwpy.msgs["coution"])
        self.text_caution.SetForegroundColour(wx.RED)
        font = cw.cwpy.rsrc.get_wxfont(size=14, style=wx.ITALIC)
        self.text_caution.SetFont(font)
        # ラジオボックス
        seq = cw.cwpy.setting.sexnames
        self.rb_sex = wx.RadioBox(self, -1, cw.cwpy.msgs["sex"],
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        seq = cw.cwpy.setting.periodnames
        self.rb_age = wx.RadioBox(self, -1, cw.cwpy.msgs["age"],
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        # OKボタン
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (120, 30), cw.cwpy.msgs["decide"])
        self._do_layout()
        self._bind()

    def _bind(self):
        self.rb_sex.Bind(wx.EVT_RADIOBOX, self.OnClickRbSex)
        self.rb_age.Bind(wx.EVT_RADIOBOX, self.OnClickRbAge)
        self.Bind(wx.EVT_BUTTON, self.OnClickOkBtn, self.okbtn)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_v2 = wx.BoxSizer(wx.VERTICAL)
        sizer_box = wx.StaticBoxSizer(self.box, wx.VERTICAL)
        sizer_rb = wx.BoxSizer(wx.HORIZONTAL)

        sizer_rb.Add(self.rb_sex, 0, 0, 0)
        sizer_rb.Add(self.rb_age, 0, wx.LEFT, 10)

        w = self.rb_age.GetSize()[0] + self.rb_sex.GetSize()[0] + 10
        sizer_box.SetMinSize((w, 0))
        sizer_box.Add(self.text_name, 0, wx.CENTER, 0)

        sizer_v2.Add(sizer_box, 0, 0, 0)
        sizer_v2.Add(sizer_rb, 0, wx.TOP, 5)

        sizer_h1.Add(self.bmp, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v2, 0, wx.LEFT, 10)

        sizer_v1.Add(self.text_caution, 0, wx.CENTER, 0)
        sizer_v1.Add(self.text_message, 0, wx.CENTER|wx.TOP, 5)
        sizer_v1.Add(sizer_h1, 0, wx.TOP, 5)
        sizer_v1.Add(self.okbtn, 0, wx.CENTER|wx.TOP, 10)
        sizer.Add(sizer_v1, 0, wx.ALL, 15)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnClickOkBtn(self, event):
        self.ccard.set_coupon(self.sex, 0)
        self.ccard.set_coupon(self.age, 0)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnClickRbSex(self, event):
        s = event.GetString()

        for index, name in enumerate(cw.cwpy.setting.sexnames):
            self.sex = cw.cwpy.setting.sexcoupons[index]
            break

    def OnClickRbAge(self, event):
        s = event.GetString()

        for index, name in enumerate(cw.cwpy.setting.periodnames):
            self.age = cw.cwpy.setting.periodcoupons[index]
            break

#-------------------------------------------------------------------------------
# 冒険者の登録ダイアログ
#-------------------------------------------------------------------------------

class AdventurerData(object):
    def __init__(self):
        self.id = "0"
        self.name = ""
        self.imgpath = ""
        self.description = ""
        self.level = 1
        self.maxlife = 0
        self.life = 0
        self.undead = False
        self.automaton = False
        self.unholy = False
        self.constructure = False
        self.noeffect_weapon = False
        self.noeffect_magic = False
        self.resist_fire = False
        self.resist_ice = False
        self.weakness_fire = False
        self.weakness_ice = False
        self.dex = 0
        self.agl = 0
        self.int = 0
        self.str = 0
        self.vit = 0
        self.min = 0
        self.aggressive = 0
        self.cheerful = 0
        self.brave = 0
        self.cautious = 0
        self.trickish = 0
        self.avoid = 0
        self.resist = 0
        self.defense = 0
        self.coupons = []
        self.gene = None
        self.has_parents = False
        # 能力限界値
        self.maxdex = 12
        self.maxagl = 12
        self.maxint = 12
        self.maxstr = 12
        self.maxvit = 12
        self.maxmin = 12
        # 編集しない無駄なデータ。XML変換時のために用意。
        self.indent = ""
        self.duration_mentality = 0
        self.mentality = "Normal"
        self.paralyze = 0
        self.poison = 0
        self.bind = 0
        self.silence = 0
        self.faceup = 0
        self.antimagic = 0
        self.duration_enhance_action = 0
        self.enhance_action = 0
        self.duration_enhance_avoid = 0
        self.enhance_avoid = 0
        self.duration_enhance_resist = 0
        self.enhance_resist = 0
        self.duration_enhance_defense = 0
        self.enhance_defense = 0
        self.items = ""
        self.skills = ""
        self.beasts = ""

    def get_d(self):
        d = {}

        for name in dir(self):
            if not name.startswith("_"):
                i = getattr(self, name, None)

                if isinstance(i, (bool, int)):
                    d[name] = str(i)
                elif isinstance(i, float):
                    d[name] = str(int(i))
                elif isinstance(i, (str, unicode)):
                    d[name] = i

        return d

    def set_coupon(self, name, value):
        coupon = (name, value)

        if not coupon in self.coupons:
            self.coupons.append(coupon)

    def set_name(self, name):
        self.name = name
        self.set_coupon(u"＿" + name, 0)

    def set_image(self, path):
        self.imgpath = path

    def set_sex(self, sex):
        for f in cw.cwpy.setting.sexes:
            if sex == u"＿" + f.name:
                self.set_coupon(sex, 0)
                f.modulate(self)
                break

    def set_age(self, age):
        for f in cw.cwpy.setting.periods:
            if age == u"＿" + f.name:
                self.level = f.level
                self.set_coupon(age, 0)
                for coupon in f.coupons:
                    self.set_coupon(coupon[0], coupon[1])
                f.modulate(self)
                break

    def set_race(self, race):
        self.undead |= race.undead
        self.automaton |= race.automaton
        self.unholy |= race.unholy
        self.constructure |= race.constructure
        self.noeffect_weapon |= race.noeffect_weapon
        self.noeffect_magic |= race.noeffect_magic
        self.resist_fire |= race.resist_fire
        self.resist_ice |= race.resist_ice
        self.weakness_fire |= race.weakness_fire
        self.weakness_ice |= race.weakness_ice
        self.dex += race.dex
        self.agl += race.agl
        self.int += race.int
        self.str += race.str
        self.vit += race.vit
        self.min += race.min
        self.aggressive += race.aggressive
        self.cheerful += race.cheerful
        self.brave += race.brave
        self.cautious += race.cautious
        self.trickish += race.trickish
        self.avoid += race.avoid
        self.resist += race.resist
        self.defense += race.defense
        # 能力限界値
        self.maxdex = race.dex + 6
        self.maxagl = race.agl + 6
        self.maxint = race.int + 6
        self.maxstr = race.str + 6
        self.maxvit = race.vit + 6
        self.maxmin = race.min + 6

        if not isinstance(race, cw.header.UnknownRaceHeader):
            self.set_coupon(u"＠Ｒ" + race.name, 0)

        for name, velue in race.coupons:
            self.set_coupon(name, 0)

    def set_parents(self, father=None, mother=None):
        if father:
            self.has_parents = True
            father.made_baby()
            fgene = father.gene
            fgene = fgene.rotate_right()
            self.set_coupon(cw.cwpy.msgs["father_coupon"] % (father.name), 0)
        else:
            fgene = cw.header.Gene()
            fgene.set_randombit()

        if mother:
            self.has_parents = True
            mother.made_baby()
            mgene = mother.gene
            mgene = mgene.rotate_right()
            self.set_coupon(cw.cwpy.msgs["mother_coupon"] % (mother.name), 0)
        else:
            mgene = cw.header.Gene()
            mgene.set_randombit()

        self.gene = fgene.fusion(mgene)

    def set_talent(self, talent):
        if not self.gene:
            self.set_parents()

        oldtalent = talent
        n = self.gene.count_bits()

        # 親がいる場合は特殊型に変化する可能性がある
        if self.has_parents:
            # 特殊型の集合
            sp = []
            for nature in cw.cwpy.setting.natures:
                if nature.special:
                    sp.append(nature)
            sp.sort(cmp=lambda x, y: y.genecount - x.genecount)

            for nature in sp:
                if nature.genecount == 0:
                    # 遺伝子の1が0個の場合。例えば凡庸型
                    if n == 0:
                        talent = u"＿" + nature.name
                elif n >= nature and (0 == len(nature.basenatures)
                                    or talent[len(u"＿"):] in nature.basenatures):
                    # 遺伝子の1が素質の条件個数以上の場合
                    # 特定の素質のみから派生する素質も存在する
                    talent = u"＿" + nature.name
                    self.gene.reverse()

        self.set_coupon(talent, 0)
        self.gene.set_talentbit(talent, oldtalent)

        for nature in cw.cwpy.setting.natures:
            if u"＿" + nature.name == talent:
                nature.modulate(self)
                self.set_coupon(u"＠レベル上限", nature.levelmax)
                break

    def set_attrbutes(self, attrs):
        for attr in attrs:
            self.set_attribute(attr)

    def set_attribute(self, attr):
        for making in cw.cwpy.setting.makings:
            if u"＿" + making.name == attr:
                making.modulate(self)
                break

        self.set_coupon(attr, 0)

    def set_desc(self, talent, attrs):
        desc = create_description(talent, attrs)
        self.description = cw.util.encodewrap(desc)

    def set_specialcoupon(self):
        self.set_coupon(u"＠レベル原点", self.level)
        self.set_coupon(u"＠ＥＰ", 0)
        self.set_coupon(u"＠Ｇ" + self.gene.get_str(), 0)

    def set_life(self):
        self.life = (self.vit / 2 + 4) * (self.level + 1) + self.min / 2
        self.maxlife = self.life

def create_description(talent, attrs):
    seq = [u"　" * 8 + talent[1:] + "\n\n"]

    index = 0
    for making in cw.cwpy.setting.makingcoupons:
        if making in attrs:
            s = making[1:]
            n = index % 3 if index else 0

            if n == 2:
                s += "\n"
            else:
                s += u"　" * (7 - len(s))

            seq.append(s)
            index += 1

    return "".join(seq)

class AdventurerCreater(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["entry_title"],
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.header = None
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), cw.cwpy.msgs["entry_cancel"])
        self.postbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), cw.cwpy.msgs["entry_decide"])
        self.nextbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), cw.cwpy.msgs["entry_next"])
        self.prevbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), cw.cwpy.msgs["entry_previous"])
        self._init_pages()
        self.enable_btn()
        self.nextbtn.Disable()
        self._do_layout()
        self._bind()

    def _init_pages(self):
        self.page1 = NamePage(self)
        self.page2 = RacePage(self)
        self.page3 = RelationPage(self)
        self.page4 = TalentPage(self)
        self.page5 = AttrPage(self)
        self.page1.set_next(self.page2)
        self.page2.set_prev(self.page1)
        self.page2.set_next(self.page3)
        self.page3.set_prev(self.page2)
        self.page3.set_next(self.page4)
        self.page4.set_prev(self.page3)
        self.page4.set_next(self.page5)
        self.page5.set_prev(self.page4)
        self.page1.Thaw()
        self.page = self.page1

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        w = self.closebtn.GetSize()[0] * 4
        margin = (460 - 80 - w) / 3
        sizer_panel.Add((40, 0), 0, 0, 0)
        sizer_panel.Add(self.prevbtn, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.nextbtn, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.postbtn, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, 3)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.page, 0, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickNextBtn, self.nextbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickPrevBtn, self.prevbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickPostBtn, self.postbtn)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.closebtn)

    def enable_btn(self):
        if self.page.get_next():
            self.nextbtn.Enable()
        else:
            self.nextbtn.Disable()

        if self.page.get_prev():
            self.prevbtn.Enable()
        else:
            self.prevbtn.Disable()

        if self.prevbtn.IsEnabled() and not self.nextbtn.IsEnabled():
            self.postbtn.Enable()
        else:
            self.postbtn.Disable()

    def OnCancel(self, event):
        if not self.page1.name:
            cw.cwpy.sounds["click"].play()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)
            return

        cw.cwpy.sounds["signal"].play()
        s = cw.cwpy.msgs["entry_cancel_message"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def OnClickNextBtn(self, event):
        nextpage = self.page.get_next()

        if nextpage:
            cw.cwpy.sounds["page"].play()
            self.page.Freeze()
            self.page = nextpage
            self.page.Thaw()
            self.enable_btn()

    def OnClickPrevBtn(self, event):
        prevpage = self.page.get_prev()

        if prevpage:
            cw.cwpy.sounds["page"].play()
            self.page.Freeze()
            self.page = prevpage
            self.page.Thaw()
            self.enable_btn()

    def OnClickPostBtn(self, event):
        cw.cwpy.sounds["signal"].play()
        s = cw.cwpy.msgs["entry_decide_message"] % (self.page1.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.create_adventurer()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def create_adventurer(self):
        data = AdventurerData()
        race = self.page2.get_race()
        data.set_race(race)
        s = self.page1.name
        data.set_name(s)
        s = self.page1.age
        data.set_age(s)
        s = self.page1.sex
        data.set_sex(s)
        s = self.page1.imgpath
        data.set_image(s)
        father = self.page3.father
        mother = self.page3.mother
        data.set_parents(father, mother)
        s = self.page4.talent
        data.set_talent(s)
        seq = self.page5.get_coupons()
        data.set_attrbutes(seq)
        data.set_desc(s, seq)
        data.set_specialcoupon()
        data.set_life()
        cw.features.wrap_ability(data)
        data.avoid = cw.util.numwrap(data.avoid, -10, 10)
        data.resist = cw.util.numwrap(data.resist, -10, 10)
        data.defense = cw.util.numwrap(data.defense, -10, 10)
        self.fpath = cw.xmlcreater.create_adventurer(data)

class AdventurerCreaterPage(wx.Panel):
    def __init__(self, parent, size=(460, 280), freeze=True):
        wx.Panel.__init__(self, parent, size=size)
        self.next = None
        self.prev = None
        # key: name, value: (pygame.Rect, 実行するメソッド)の辞書
        self.clickables = {}
        if freeze:
            self.Freeze()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.OnCancel)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnEraseBackground(self, evt):
        """
        画面のちらつき防止。
        """
        pass

    def OnPaint(self, event):
        self.draw()

    def OnLeftUp(self, event):
        dc = wx.ClientDC(self)
        mousepos = event.GetPosition()

        for key, value in self.clickables.iteritems():
            rect, method, wheelmethod = value

            if method and rect.collidepoint(mousepos):
                method(key)

    def OnMouseWheel(self, event):
        dc = wx.ClientDC(self)
        mousepos = event.GetPosition()

        for key, value in self.clickables.iteritems():
            rect, method, wheelmethod = value

            if wheelmethod and rect.collidepoint(mousepos):
                wheelmethod(key, event.GetWheelRotation())

    def draw_clickabletext(self, dc, s, pos, name, method, wheelmethod, setname=None):
        size = dc.GetTextExtent(s)
        dc.DrawText(s, pos[0], pos[1])

        if setname == name:
            bmp = cw.cwpy.rsrc.dialogs["SELECT"]
            top, left = cw.util.get_centerposition(bmp.GetSize(), pos, size)
            dc.DrawBitmap(bmp, top, left, True)

        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + 4, size[1] + 4
            pos = pos[0] - 2, pos[1] - 2
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def draw_clickablebmp(self, dc, bmp, pos, name, method, wheelmethod, mask=True):
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, pos[0], pos[1], True)

        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + 20, size[1] + 20
            pos = pos[0] - 10, pos[1] - 10
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def set_next(self, page):
        self.next = page

    def set_prev(self, page):
        self.prev = page

    def get_next(self):
        if self.next and self.next.is_skip():
            return self.next.get_next()
        else:
            return self.next

    def get_prev(self):
        if self.prev and self.prev.is_skip():
            return self.prev.get_prev()
        else:
            return self.prev

    def is_skip(self):
        return False

    def set_imgpaths(self, reset=True):
        if reset or self.imgpath == "":
            self.imgpaths = []
        else:
            self.imgpaths = [self.imgpath]
        self.imgpaths += cw.util.get_facepaths(self.sex, self.age)

        if self.imgpaths:
            self.imgpath = self.imgpaths[0]

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            dc = wx.BufferedDC(dc, self.GetSize())
        else:
            dc = wx.PaintDC(self)

        # 共通背景
        path = "Table/Book" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        dc.DrawBitmap(bmp, 0, 0, False)
        return dc

class NamePage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.textctrl = wx.TextCtrl(self, size=(125, 18), style=wx.NO_BORDER)
        self.textctrl.SetMaxLength(14)
        self.textctrl.SetFocus()
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=11)
        self.textctrl.SetFont(font)
        self.name = ""
        self.sex = cw.cwpy.setting.sexcoupons[0]
        self.age = cw.cwpy.setting.periodcoupons[0]
        for period in cw.cwpy.setting.periods:
            if period.firstselect:
                self.age = u"＿" + period.name
                break
        self.imgpath = ""
        self.set_imgpaths(True)
        self._bind()
        self._do_layout()

    def _bind(self):
        AdventurerCreaterPage._bind(self)
        self.Bind(wx.EVT_TEXT, self.OnInputText)

    def OnInputText(self, event):
        self.name = self.textctrl.GetValue()

        if self.name.strip():
            self.Parent.nextbtn.Enable()
        else:
            self.Parent.nextbtn.Disable()

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        csize = self.GetClientSize()
        sizer_1.Add((csize[0], 90), 0, 0, 0)
        w, h = self.textctrl.GetSize()
        margin = (csize[0] - w) / 2
        sizer_1.Add(self.textctrl, 0, wx.RIGHT|wx.LEFT, margin)
        margin = csize[1] - 90 - h
        sizer_1.Add((csize[0], margin), 0, 0, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # welcome to the adventurers inn
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=14, style=wx.ITALIC))
        s = cw.cwpy.msgs["entry_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # Name
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = cw.cwpy.msgs["entry_name"]
        dc.DrawText(s, 160, 72)
        # Sex
        s = cw.cwpy.msgs["entry_sex"]
        dc.DrawText(s, 85, 125)
        # Age
        s = cw.cwpy.msgs["entry_age"]
        dc.DrawText(s, 85, 175)

        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=9)
        dc.SetFont(font)
        xx = [90, 155]

        # 性別
        x = xx[0]
        y = 145
        for sex in cw.cwpy.setting.sexes:
            s = sex.subname
            pos = (x, y)
            self.draw_clickabletext(dc, s, pos, u"＿" + sex.name, self.set_sex, None, self.sex)
            if xx[1] == x:
                x = xx[0]
                y += 20
            else:
                x = xx[1]

        # 年代
        x = xx[0]
        y = 195
        for period in cw.cwpy.setting.periods:
            s = period.subname
            pos = (x, y)
            self.draw_clickabletext(dc, s, pos, u"＿" + period.name, self.set_age, None, self.age)
            if xx[1] == x:
                x = xx[0]
                y += 20
            else:
                x = xx[1]

        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (250, 170)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg, None)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (365, 170)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg, None)
        # image
        bmp = cw.util.load_wxbmp(self.imgpath, True)
        self.draw_clickablebmp(dc, bmp, (275, 130), "Face", None, self.on_mousewheel, True)

    def set_sex(self, name):
        if not self.sex == name:
            cw.cwpy.sounds["click"].play()
            self.sex = name
            self.set_imgpaths(True)
            self.draw(True)

    def set_age(self, name):
        if not self.age == name:
            cw.cwpy.sounds["click"].play()
            self.age = name
            self.set_imgpaths(True)
            self.draw(True)

    def on_mousewheel(self, name, rotate):
        if rotate < 0:
            self.set_previmg(name)
        elif 0 < rotate:
            self.set_nextimg(name)

    def set_nextimg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds["page"].play()
            index = self.imgpaths.index(self.imgpath) + 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_previmg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds["page"].play()
            index = self.imgpaths.index(self.imgpath) - 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

class RacePage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        choices = [h.name for h in cw.cwpy.setting.races]
        self.race = choices[0]
        self.choice = wx.Choice(self, choices=choices, size=(125, 18))
        self.choice.SetStringSelection(self.race)
        self._bind()
        self._do_layout()

    def _bind(self):
        AdventurerCreaterPage._bind(self)
        self.Bind(wx.EVT_CHOICE, self.OnChoice)

    def OnChoice(self, event):
        race = self.choice.GetStringSelection()

        if not self.race == race:
            self.race = race
            self.draw(True)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        csize = self.GetClientSize()
        sizer_1.Add((csize[0], 90), 0, 0, 0)
        w, h = self.choice.GetSize()
        margin = (csize[0] - w) / 2
        sizer_1.Add(self.choice, 0, wx.RIGHT|wx.LEFT, margin)
        margin = csize[1] - 90 - h
        sizer_1.Add((csize[0], margin), 0, 0, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 種族
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=14, style=wx.ITALIC)
        dc.SetFont(font)
        s = cw.cwpy.msgs["race_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 新規冒険者の種族を決定します。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = cw.cwpy.msgs["race_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 60)
        # 説明
        s = self.get_race().desc
        s = cw.util.txtwrap(s, 1)

        if s.count("\n") > 7:
            s = "\n".join(s.split("\n")[0:8])

        font = cw.cwpy.rsrc.get_wxfont("gothic", size=9, weight=wx.NORMAL)
        dc.SetFont(font)
        dc.DrawLabel(s, (125, 130, 200, 110))

    def get_race(self):
        """
        現在選択中の種族のElementを返す。
        """
        s = self.choice.GetStringSelection()
        index = self.choice.GetStrings().index(s)
        return cw.cwpy.setting.races[index]

    def is_skip(self):
        if len(cw.cwpy.setting.races) > 1:
            return False
        else:
            return True

class RelationPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.set_parents()
        self.father = None
        self.mother = None
        self._bind()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 血縁
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=14, style=wx.ITALIC)
        dc.SetFont(font)
        s = s = cw.cwpy.msgs["relation_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 親となる条件を満たしている冒険者が宿にいます。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = cw.cwpy.msgs["relation_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 60)
        # Father
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, style=wx.ITALIC)
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = cw.cwpy.msgs["father"]
        dc.DrawText(s, 110, 92)
        # Mother
        s = cw.cwpy.msgs["mother"]
        dc.DrawText(s, 285, 92)
        # PrevFather
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (70, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevFather", self.set_prevfather, None)
        # NextFather
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (190, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextFather", self.set_nextfather, None)
        # PrevMother
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (250, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevMother", self.set_prevmother, None)
        # NextMother
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (370, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextMother", self.set_nextmother, None)

        # 父親画像
        if self.father:
            path = self.father.get_imgpath()
        else:
            path = "Resource/Image/Card/FATHER" + cw.cwpy.rsrc.ext_img
            path = cw.util.join_paths(cw.cwpy.skindir, path)

        bmp = cw.util.load_wxbmp(path, True)
        dc.DrawBitmap(bmp, 100, 110, True)

        # 母親画像
        if self.mother:
            path = self.mother.get_imgpath()
        else:
            path = "Resource/Image/Card/MOTHER" + cw.cwpy.rsrc.ext_img
            path = cw.util.join_paths(cw.cwpy.skindir, path)

        bmp = cw.util.load_wxbmp(path, True)
        dc.DrawBitmap(bmp, 275, 110, True)
        # 父親名前
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=11)
        dc.SetFont(font)

        if self.father:
            s = self.father.name
        else:
            s = cw.cwpy.msgs["general_father"]

        cw.util.draw_center(dc, s, (140, 220))

        # 母親名前
        if self.mother:
            s = self.mother.name
        else:
            s = cw.cwpy.msgs["general_mother"]

        cw.util.draw_center(dc, s, (315, 220))
        # 父親消費EP
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)

        if self.father:
            if self.father.album:
                ep = 10
            else:
                for period in cw.cwpy.setting.periods:
                    if self.father.age == u"＿" + period.name:
                        ep = period.spendep
                        break

            s = cw.cwpy.msgs["consumption_ep"] % (ep, self.father.ep - ep)
            cw.util.draw_center(dc, s, (140, 240))

        # 母親消費EP
        if self.mother:
            if self.mother.album:
                ep = 10
            else:
                for period in cw.cwpy.setting.periods:
                    if self.mother.age == u"＿" + period.name:
                        ep = period.spendep
                        break

            s = cw.cwpy.msgs["consumption_ep"] % (ep, self.mother.ep - ep)
            cw.util.draw_center(dc, s, (315, 240))

    def set_nextfather(self, name):
        if self.fathers:
            cw.cwpy.sounds["page"].play()
            index = self.fathers.index(self.father) + 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_prevfather(self, name):
        if self.fathers:
            cw.cwpy.sounds["page"].play()
            index = self.fathers.index(self.father) - 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_nextmother(self, name):
        if self.mothers:
            cw.cwpy.sounds["page"].play()
            index = self.mothers.index(self.mother) + 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def set_prevmother(self, name):
        if self.mothers:
            cw.cwpy.sounds["page"].play()
            index = self.mothers.index(self.mother) - 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def set_parents(self):
        def append_header(self, header):
            for sex in cw.cwpy.setting.sexes:
                if header.sex == u"＿" + sex.name:
                    if sex.father:
                        self.fathers.append(header)
                    if sex.mother:
                        self.mothers.append(header)
                    break

        self.fathers = [None]
        self.mothers = [None]

        if not cw.cwpy.ydata:
            return

        for index, header in enumerate(cw.cwpy.ydata.standbys):
            for period in cw.cwpy.setting.periods:
                if period.spendep > 0 and header.age == u"＿" + period.name and header.ep >= period.spendep:
                    append_header(self, header)
                    break

        for index, header in enumerate(cw.cwpy.ydata.album):
            if header.ep >= 10:
                append_header(self, header)

    def is_skip(self):
        if len(self.fathers) > 1 or len(self.mothers) > 1:
            return False
        else:
            return True

class TalentPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.talent = u"＿" + cw.cwpy.setting.natures[0].name
        self._bind()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 素質
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=14, style=wx.ITALIC)
        dc.SetFont(font)
        s = s = cw.cwpy.msgs["nature_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 新規冒険者の傾向を選択して下さい。
        font1 = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        font2 = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font1)
        s = cw.cwpy.msgs["nature_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 60)
        xx = [65, 255]
        x = xx[0]
        y = 92
        for nature in cw.cwpy.setting.natures:
            if not nature.special:
                s = cw.util.txtwrap(nature.description, mode=5)
                dc.SetFont(font1)
                dc.DrawLabel(s, (x + 3, y + 18, 145, 35))
                dc.SetFont(font2)
                s = nature.name
                pos = (x, y)
                self.draw_clickabletext(dc, s, pos, u"＿" + nature.name, self.set_talent, None, self.talent)

                if x == xx[1]:
                    x = xx[0]
                    y += 55
                else:
                    x = xx[1]

    def set_talent(self, name):
        if not self.talent == name:
            cw.cwpy.sounds["click"].play()
            self.talent = name
            self.draw(True)

class AttrPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.couponsdata = {}
        self._bind()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 特性
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=14, style=wx.ITALIC)
        dc.SetFont(font)
        s = cw.cwpy.msgs["making_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 20)
        # 新規冒険者の生まれや性格などの個性を決定します。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = cw.cwpy.msgs["making_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 45)
        # 特性
        colour = wx.Colour(128, 128, 128)
        dc.SetTextForeground(colour)
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)

        for index in xrange(0, len(cw.cwpy.setting.makings), 2):
            column = index % 4
            pos = (67 + column * 86, 64 + (index / 4) * 16)
            m1 = cw.cwpy.setting.makings[index]
            s = m1.name
            if index + 1 < len(cw.cwpy.setting.makings):
                m2 = cw.cwpy.setting.makings[index + 1]
                coupons = (m1.name, m2.name)
            else:
                coupons = (m1.name)
            name = (u"＿" + s, coupons)
            self.draw_clickabletext(dc, s, pos, name, self.set_coupon, None)
            if index + 1 < len(cw.cwpy.setting.makings):
                pos = pos[0] + 86, pos[1]
                s = m2.name
                name = (u"＿" + s, coupons)
                self.draw_clickabletext(dc, s, pos, name, self.set_coupon, None)

    def draw_clickabletext(self, dc, s, pos, name, method, wheelmethod, setname=None):
        size = dc.GetTextExtent(s)
        dc.DrawText(s, pos[0], pos[1])

        if self.couponsdata.get(name[1], "") == name[0]:
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(s, pos[0], pos[1])
            colour = wx.Colour(128, 128, 128)
            dc.SetTextForeground(colour)
        else:
            dc.DrawText(s, pos[0], pos[1])

        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + 2, size[1] + 2
            pos = pos[0] - 1, pos[1] - 1
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def set_coupon(self, name):
        name, coupons = name

        if self.couponsdata.get(coupons, "") == name:
            self.couponsdata[coupons] = ""
        else:
            self.couponsdata[coupons] = name

        cw.cwpy.sounds["click"].play()
        self.draw(True)

    def get_coupons(self):
        seq = [value for value in self.couponsdata.itervalues() if value]
        seq.sort()
        return seq

#-------------------------------------------------------------------------------
# 宿の登録ダイアログ
#-------------------------------------------------------------------------------

class YadoCreater(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["create_base_title"], size=(318, 180),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.yadodir = ""
        self.SetClientSize((312, 156))
        self.textctrl = wx.TextCtrl(self, size=(175, 24))
        self.textctrl.SetMaxLength(18)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=12)
        self.textctrl.SetFont(font)
        self.textctrl.SetValue(cw.cwpy.msgs["new_base"])
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                            (100, 30), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

    def create_yado(self):
        name = self.textctrl.GetValue().strip()
        self.yadodir = cw.util.join_paths("Yado", cw.binary.util.check_filename(name))
        self.yadodir = cw.binary.util.check_duplicate(self.yadodir)
        os.makedirs(self.yadodir)
        dnames = ("Adventurer", "Album", "BeastCard", "ItemCard",
                                            "Material", "Party", "SkillCard")

        for dname in dnames:
            path = cw.util.join_paths(self.yadodir, dname)
            os.makedirs(path)

        cw.xmlcreater.create_environment(name, self.yadodir)

    def OnInput(self, event):
        name = self.textctrl.GetValue().strip()

        if name:
            self.okbtn.Enable()
        else:
            self.okbtn.Disable()

    def OnOk(self, event):
        name = self.textctrl.GetValue().strip()

        self.create_yado()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # text
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("uigothic")
        dc.SetFont(font)
        s = cw.cwpy.msgs["create_base_message_1"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, 10)
        font = cw.cwpy.rsrc.get_wxfont("uigothic", weight=wx.NORMAL)
        dc.SetFont(font)
        s = cw.cwpy.msgs["create_base_message_2"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, 30)

    def _bind(self):
        self.Bind(wx.EVT_TEXT, self.OnInput, self.textctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def _do_layout(self):
        csize = self.GetClientSize()
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_1.Add((0, 55), 0, 0, 0)
        margin = (csize[0] - self.textctrl.GetSize()[0]) / 2
        sizer_1.Add(self.textctrl, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add((0, 25), 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_2.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)

        self.SetSizer(sizer_1)
        self.Layout()

#-------------------------------------------------------------------------------
# 冒険者のデザインダイアログ
#-------------------------------------------------------------------------------

class AdventurerDesignDialog(wx.Dialog):
    def __init__(self, parent, ccard):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["design_title"],
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        # buttonlist
        self.buttonlist = []

        self.ccard = ccard

        # toppanel
        self.toppanel = DesignPanel(self, self.ccard)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                            (100, 30), cw.cwpy.msgs["entry_decide"])
        self.buttonlist.append(self.okbtn)
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.cnclbtn)

        # layout
        self._do_layout()
        # bind
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)

        # button間のマージン値を求める
        width = 400 - 6
        btnwidth = self.buttonlist[0].GetSize()[0] * len(self.buttonlist)
        margin = (width - btnwidth) / (len(self.buttonlist)+1)
        margin2 = margin + (width - btnwidth) % (len(self.buttonlist)+1)

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_btn.Add((margin, 0), 0, 0, 0)
            sizer_btn.Add(button, 0, wx.TOP|wx.BOTTOM, 3)
        sizer_btn.Add((margin2, 0), 0, 0, 0)

        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_btn, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def OnOk(self, event):
        name = self.toppanel.namectrl.GetValue()
        desc = self.toppanel.descctrl.GetValue()
        self.ccard.set_name(name)
        self.ccard.set_description(desc)
        if self.toppanel.imgpath.startswith(cw.util.join_paths(cw.cwpy.skindir, u"Face")):
            self.ccard.set_image(self.toppanel.imgpath)
        self.ccard.data.is_edited = True
        self.ccard.data.write_xml()

        def func(ccard):
            cw.cwpy.sounds["harvest"].play()
            if isinstance(ccard, cw.sprite.card.CWPyCard):
                cw.animation.animate_sprite(ccard, "hide")
                ccard.update_image()
                cw.animation.animate_sprite(ccard, "deal")
        cw.cwpy.exec_func(func, self.ccard)

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class DesignPanel(AdventurerCreaterPage):
    def __init__(self, parent, ccard):
        AdventurerCreaterPage.__init__(self, parent, size=(400, 370), freeze=False)
        self.SetMinSize((400, 370))

        self.ccard = ccard

        self.namectrl = wx.TextCtrl(self, size=(125, 18), style=wx.NO_BORDER)
        self.namectrl.SetMaxLength(14)
        self.namectrl.SetFocus()
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=11)
        self.namectrl.SetFont(font)

        font = cw.cwpy.rsrc.get_wxfont("gothic", size=9, weight=wx.NORMAL)
        self.descctrl = wx.TextCtrl(self, style=wx.NO_BORDER|wx.TE_MULTILINE)
        self.descctrl.SetFont(font)

        dc = wx.ClientDC(self)
        dc.SetFont(self.descctrl.GetFont())
        w = dc.GetTextExtent("#")[0] * 40
        dc.Destroy()
        self.descctrl.SetClientSize((w, 107))
        self.descctrl.SetInitialSize(self.descctrl.GetSize())

        self.imgpath = self.ccard.get_imagepath()
        if self.imgpath <> "":
            self.imgpath = cw.util.join_yadodir(self.imgpath)

        self.name = self.ccard.get_name()
        self.desc = self.ccard.get_description()
        self.sex = self.ccard.get_sex()
        self.age = self.ccard.get_age()

        self.namectrl.SetValue(self.name)
        self.namectrl.SetSelection(0, len(self.name))
        self.descctrl.SetValue(cw.util.decodewrap(self.desc))

        self.set_imgpaths(False)
        self._bind()
        self._do_layout()

    def _bind(self):
        AdventurerCreaterPage._bind(self)
        self.namectrl.Bind(wx.EVT_TEXT, self.OnInputName)

    def OnInputName(self, event):
        self.name = self.namectrl.GetValue()

        if self.name.strip():
            self.Parent.okbtn.Enable()
        else:
            self.Parent.okbtn.Disable()

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_1.Add(self.namectrl, 0, wx.TOP|wx.CENTER, 60)
        sizer_1.Add(self.descctrl, 0, wx.TOP|wx.CENTER, 158)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)

        # 背景
        path = "Table/Bill" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # Resident Registration
        dc.SetTextForeground(wx.BLACK)
        s = cw.cwpy.msgs["edit_character_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 15)

        # Name
        s = cw.cwpy.msgs["entry_name"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 45)
        # Image
        s = cw.cwpy.msgs["entry_image"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 95)
        # Comment
        s = cw.cwpy.msgs["entry_comment"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 220)

        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (135, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg, None)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (260, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg, None)
        # image
        bmp = cw.util.load_wxbmp(self.imgpath, True)
        self.draw_clickablebmp(dc, bmp, ((cwidth - 74) / 2, 116), "Face", None, self.on_mousewheel, True)

    def on_mousewheel(self, name, rotate):
        if rotate < 0:
            self.set_previmg(name)
        elif 0 < rotate:
            self.set_nextimg(name)

    def set_nextimg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds["page"].play()
            index = self.imgpaths.index(self.imgpath) + 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_previmg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds["page"].play()
            index = self.imgpaths.index(self.imgpath) - 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

def main():
    pass

if __name__ == "__main__":
    main()
