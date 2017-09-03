#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import wx
import pygame

import cw


#-------------------------------------------------------------------------------
#　不足データの補填ダイアログ
#-------------------------------------------------------------------------------

class AdventurerDataComp(wx.Dialog):
    def __init__(self, parent, ccard):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["insufficiency_title"],
                            style=wx.CAPTION|wx.SYSTEM_MENU)
        self.cwpy_debug = False
        self.ccard = ccard
        hassex = self.ccard.has_sex()
        if hassex:
            self.sex = self.ccard.get_sex()
        else:
            self.sex = cw.cwpy.setting.sexcoupons[0]
            self.ccard.set_sex(self.sex)
        hasage = self.ccard.has_age()
        if hasage:
            self.age = self.ccard.get_age()
        else:
            self.age = cw.cwpy.setting.periodcoupons[0]
            self.ccard.set_age(self.age)
        # 画像
        bmps = []
        bmps_noscale = []
        can_loaded_scaledimage = ccard.data.getbool(".", "scaledimage", False)
        for info in ccard.imgpaths:
            bmp = cw.util.load_wxbmp(info.path, True, can_loaded_scaledimage=can_loaded_scaledimage)
            bmps_noscale.append(bmp)
            bmp = cw.wins(bmp)
            bmps.append(bmp)
        self.bmp = cw.util.CWPyStaticBitmap(self, -1, bmps, bmps_noscale, size=cw.wins(cw.SIZE_CARDIMAGE),
                                            infos=ccard.imgpaths, ss=cw.wins)
        # 各種テキスト
        s = cw.cwpy.msgs["insufficiency_message"]
        s = cw.util.txtwrap(s, 0, width=42, wrapschars=cw.util.WRAPS_CHARS)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(14))
        self.text_message = wx.StaticText(self, -1, s)
        self.text_message.SetFont(font)
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(16))
        self.box = wx.StaticBox(self, -1)
        self.box.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(12)))
        self.text_name = wx.StaticText(self, -1, ccard.name)
        self.text_name.SetFont(font)
        self.text_caution = wx.StaticText(self, -1, cw.cwpy.msgs["coution"])
        self.text_caution.SetForegroundColour(wx.RED)
        font = cw.cwpy.rsrc.get_wxfont("dlgtitle2", pixelsize=cw.wins(20))
        self.text_caution.SetFont(font)
        # ラジオボックス
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14))
        seq = cw.cwpy.setting.sexnames
        self.rb_sex = wx.RadioBox(self, -1, cw.cwpy.msgs["sex"],
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        self.rb_sex.SetFont(font)
        seq = cw.cwpy.setting.periodnames
        self.rb_age = wx.RadioBox(self, -1, cw.cwpy.msgs["age"],
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        self.rb_age.SetFont(font)

        # 初期値設定
        for index, coupon in enumerate(cw.cwpy.setting.sexcoupons):
            if self.sex == coupon:
                self.rb_sex.SetSelection(index)
                break
        for index, coupon in enumerate(cw.cwpy.setting.periodcoupons):
            if self.age == coupon:
                self.rb_age.SetSelection(index)
                break

        if hassex:
            self.rb_sex.Disable()
        if hasage:
            self.rb_age.Disable()

        # OKボタン
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, cw.wins((120, 30)), cw.cwpy.msgs["decide"])
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
        sizer_rb.Add(self.rb_age, 0, wx.LEFT, cw.wins(10))

        w = self.rb_age.GetSize()[0] + self.rb_sex.GetSize()[0] + cw.wins(10)
        sizer_box.SetMinSize((w, 0))
        sizer_box.Add(self.text_name, 0, wx.CENTER, 0)

        sizer_v2.Add(sizer_box, 0, 0, 0)
        sizer_v2.Add(sizer_rb, 0, wx.TOP, cw.wins(5))

        sizer_h1.Add(self.bmp, 0, wx.CENTER, 0)
        sizer_h1.Add(sizer_v2, 0, wx.LEFT, cw.wins(10))

        sizer_v1.Add(self.text_caution, 0, wx.CENTER, 0)
        sizer_v1.Add(self.text_message, 0, wx.CENTER|wx.TOP, cw.wins(5))
        sizer_v1.Add(sizer_h1, 0, wx.TOP, cw.wins(5))
        sizer_v1.Add(self.okbtn, 0, wx.CENTER|wx.TOP, cw.wins(10))
        sizer.Add(sizer_v1, 0, wx.ALL, cw.wins(15))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnClickOkBtn(self, event):
        self.ccard.set_sex(self.sex)
        self.ccard.set_age(self.age)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnClickRbSex(self, event):
        s = event.GetString()

        for index, name in enumerate(cw.cwpy.setting.sexnames):
            if name == s:
                self.sex = cw.cwpy.setting.sexcoupons[index]
                break

    def OnClickRbAge(self, event):
        s = event.GetString()

        for index, name in enumerate(cw.cwpy.setting.periodnames):
            if name == s:
                self.age = cw.cwpy.setting.periodcoupons[index]
                break

#-------------------------------------------------------------------------------
# 冒険者の登録ダイアログ
#-------------------------------------------------------------------------------

class AdventurerData(object):
    def __init__(self):
        self.id = "0"
        self.name = ""
        self.imgpaths = []
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
        self.couponnames = {}
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

        if not name in self.couponnames:
            self.couponnames[name] = len(self.coupons)
            self.coupons.append(coupon)
        elif name == u"＠レベル上限":
            # レベル上限に限っては、種族によって
            # 高めに設定されている場合があるので、
            # 最も高いものを使用する
            i = self.couponnames[name]
            self.coupons[i] = coupon

    def set_name(self, name):
        self.name = name

    def set_images(self, paths):
        self.imgpaths = paths

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
                f.modulate(self)
                break

    # デバッグモードでは初期Lvにプレイヤーが設定した値を使用
    def set_level(self, level):
        self.level = level

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

        for name, value in race.coupons:
            self.set_coupon(name, value)

    def set_parents(self, father=None, mother=None):
        if father:
            self.has_parents = True
            father.made_baby()
            fgene = father.gene
            fgene = fgene.rotate_father()
            self.set_coupon(cw.cwpy.msgs["father_coupon"] % (father.name), 0)
        else:
            fgene = cw.header.Gene()
            fgene.set_randombit()

        if mother:
            self.has_parents = True
            if not father is mother:
                mother.made_baby()
            mgene = mother.gene
            mgene = mgene.rotate_mother()
            self.set_coupon(cw.cwpy.msgs["mother_coupon"] % (mother.name), 0)
        else:
            mgene = cw.header.Gene()
            mgene.set_randombit()

        self.gene = fgene.fusion(mgene)

    def set_gene(self, talent):
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
            cw.util.sort_by_attr(sp, "genecount")

            for nature in reversed(sp):
                if nature.genecount == 0:
                    # 遺伝子の1が0個の場合。例えば凡庸型
                    if n == 0:
                        talent = u"＿" + nature.name
                        break
                elif n >= nature.genecount and (0 == len(nature.basenatures)
                                    or talent[1:] in nature.basenatures):
                    # 遺伝子の1が素質の条件個数以上の場合
                    # 特定の素質のみから派生する素質も存在する
                    talent = u"＿" + nature.name
                    self.gene = self.gene.reverse()
                    break

        for nature in cw.cwpy.setting.natures:
               if u"＿" + nature.name == talent:
                   nature.modulate(self)
                   self.set_coupon(u"＠レベル上限", nature.levelmax)
                   break

        self.gene.set_talentbit(talent, oldtalent)
        self.set_coupon(u"＠Ｇ" + self.gene.get_str(), 0)

        return talent

    def set_talent(self, talent):
        self.set_coupon(talent, 0)

    def set_aging(self, age):
        for f in cw.cwpy.setting.periods:
            if age == u"＿" + f.name:
                self.level = f.level
                for coupon in f.coupons:
                    self.set_coupon(coupon[0], coupon[1])
                break

    def set_attributes(self, attrs):
        for attr in cw.cwpy.setting.makings:
            coupon = u"＿" + attr.name
            if coupon in attrs:
                attr.modulate(self)
                self.set_coupon(coupon, 0)

    def set_desc(self, talent, attrs):
        desc = create_description(talent, attrs)
        self.description = cw.util.encodewrap(desc)

    def set_specialcoupon(self):
        self.set_coupon(u"＠ＥＰ", 0)
        self.set_coupon(u"＠レベル原点", self.level)

    def set_life(self):
        self.life = cw.character.calc_maxlife(self.vit, self.min, self.level)
        self.maxlife = self.life

def create_description(talent, attrs):
    seq = [u"　" * 8 + talent[1:] + "\n\n"]

    index = 0
    for making in cw.cwpy.setting.makingcoupons:
        if making in attrs:
            s = making[1:]
            n = index % 3 if index else 0

            if len(attrs) == index + 1:
                pass
            elif n == 2:
                s += "\n"
            else:
                s += u"　" * (7 - len(s))

            seq.append(s)
            index += 1

    return "".join(seq)

class AdventurerCreater(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["entry_title"],
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        self.header = None
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self._init_pages()
        if cw.cwpy.setting.show_autobuttoninentrydialog:
            btnwidth = 75
        else:
            btnwidth = 85
        self.nextbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            cw.wins((btnwidth, 24)), cw.cwpy.msgs["entry_next"])
        if cw.cwpy.setting.show_autobuttoninentrydialog:
            self.autobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                                cw.wins((btnwidth, 24)), cw.cwpy.msgs["auto_selection"])
        else:
            self.autobtn = None
        self.prevbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            cw.wins((btnwidth, 24)), cw.cwpy.msgs["entry_previous"])
        self.postbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            cw.wins((btnwidth, 24)), cw.cwpy.msgs["entry_decide"])
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            cw.wins((btnwidth, 24)), cw.cwpy.msgs["entry_cancel"])
        self.SetEscapeId(self.closebtn.GetId())
        self.enable_btn()
        self.nextbtn.Disable()
        self._do_layout()
        self._bind()

        nupkeyid = wx.NewId()
        self.shifttabkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=nupkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=self.shifttabkeyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_UP, nupkeyid),
            (wx.ACCEL_SHIFT, wx.WXK_TAB, self.shifttabkeyid),
        ]
        cw.util.set_acceleratortable(self.autobtn, seq)
        cw.util.set_acceleratortable(self.prevbtn, seq)

        self.autobtn.MoveBeforeInTabOrder(self.nextbtn)
        self.prevbtn.MoveBeforeInTabOrder(self.autobtn)

    def OnNUpKeyDown(self, event):
        fc = wx.Window.FindFocus()
        if self.page.AcceptsFocusFromKeyboard():
            if (fc is self.autobtn and not self.prevbtn.IsEnabled()) or fc is self.prevbtn:
                self.page.SetFocusIgnoringChildren()
                if event.GetId() <> self.shifttabkeyid:
                    self.page.move_up()
                return
        fc.Navigate(wx.NavigationKeyEvent.IsBackward)

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
        self.page1.Show()
        self.page = self.page1

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        if self.autobtn:
            btncount = 5
            space = 35
        else:
            btncount = 4
            space = 40
        w = self.closebtn.GetSize()[0] * btncount
        margin = (cw.wins(460 - space*2) - w) / 3
        sizer_panel.Add(cw.wins((space, 0)), 0, 0, 0)
        sizer_panel.Add(self.prevbtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((margin, 0), 0, 0, 0)
        if self.autobtn:
            sizer_panel.Add(self.autobtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
            sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.nextbtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.postbtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.closebtn, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
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
        if self.autobtn:
            self.Bind(wx.EVT_BUTTON, self.OnClickAutoBtn, self.autobtn)
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
            cw.cwpy.play_sound("click")
            self.Destroy()
            return

        cw.cwpy.play_sound("signal")
        s = cw.cwpy.msgs["entry_cancel_message"]
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.Destroy()

        dlg.Destroy()

    def OnClickNextBtn(self, event):
        nextpage = self.page.get_next()

        if nextpage:
            cw.cwpy.play_sound("page")
            self.page.Freeze()
            self.page.Hide()
            self.page = nextpage
            self.page.Thaw()
            self.page.Show()
            self.enable_btn()

    def OnClickPrevBtn(self, event):
        prevpage = self.page.get_prev()

        if prevpage:
            cw.cwpy.play_sound("page")
            self.page.Freeze()
            self.page.Hide()
            self.page = prevpage
            self.page.Thaw()
            self.page.Show()
            self.enable_btn()

    def OnClickAutoBtn(self, event):
        cw.cwpy.play_sound("signal")
        self.page.select_autofeatures()

    def OnClickPostBtn(self, event):
        cw.cwpy.play_sound("signal")
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
        #親、＠レベル上限、遺伝情報、性別、年代、（種族）の順
        father = self.page3.father
        mother = self.page3.mother
        data.set_parents(father, mother)
        s = self.page4.talent
        talent = data.set_gene(s)
        s = self.page1.name
        data.set_name(s)
        s = self.page1.sex
        data.set_sex(s)
        s = self.page1.age
        data.set_age(s)
        race = self.page2.get_race()
        data.set_race(race)
        s = self.page1.imgpaths
        data.set_images(s)
        #型と特徴で解説を作る
        data.set_talent(talent)
        coupons = self.page5.get_coupons()
        data.set_attributes(coupons)
        data.set_desc(talent, coupons)
        #最後に熟練・老獪を付与
        s = self.page1.age
        data.set_aging(s)
        data.set_specialcoupon()
        data.set_life()
        cw.features.wrap_ability(data)
        data.avoid = cw.util.numwrap(data.avoid, -10, 10)
        data.resist = cw.util.numwrap(data.resist, -10, 10)
        data.defense = cw.util.numwrap(data.defense, -10, 10)
        self.fpath = cw.xmlcreater.create_adventurer(data)

class AdventurerCreaterPage(wx.Panel):
    def __init__(self, parent, size=None, freeze=True):
        if size is None:
            size = cw.wins((460, 280))
        wx.Panel.__init__(self, parent, size=size)
        self.SetMinSize(size)
        self.next = None
        self.prev = None
        # ツールチップヒント(wx.Rect, テキスト)
        self.tooltips = []
        # key: name, value: (pygame.Rect, 実行するメソッド)の辞書
        self.clickables = {}
        # キー操作で選択しているアイテム(name)
        self.selected_clickable = None
        self.clickable_table = []

        self.imgpathlist = {}
        self.imgdpath = -1
        self.imgdpaths = []
        self.ch_imgdpath = None
        self.sex = ""
        self.age = ""
        self._dropkey = (-1, u"<ドロップされたイメージ>", "/drop_files")

        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

        if freeze:
            self.Freeze()
            self.Hide()

    def OnSetFocus(self, event):
        self.selected_clickable = self._find_nextclickable_h(None)
        self.Refresh()

    def OnKillFocus(self, event):
        self.selected_clickable = None
        self.Refresh()

    def _bind(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint2)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_RIGHT_UP, self.Parent.OnCancel)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)

    def _do_layout(self):
        pass

    def set_normalacceleratortable(self):
        nleftkeyid = wx.NewId()
        nrightkeyid = wx.NewId()
        nupkeyid = wx.NewId()
        ndownkeyid = wx.NewId()
        self.shifttabkeyid = wx.NewId()
        self.tabkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnNLeftKeyDown, id=nleftkeyid)
        self.Bind(wx.EVT_MENU, self.OnNRightKeyDown, id=nrightkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=nupkeyid)
        self.Bind(wx.EVT_MENU, self.OnNDownKeyDown, id=ndownkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=self.shifttabkeyid)
        self.Bind(wx.EVT_MENU, self.OnNDownKeyDown, id=self.tabkeyid)
        seq = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, nleftkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT, nrightkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_UP, nupkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, ndownkeyid),
            (wx.ACCEL_SHIFT, wx.WXK_TAB, self.shifttabkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_TAB, self.tabkeyid),
        ]
        cw.util.set_acceleratortable(self, seq, ignoreleftrightkeys=(wx.TextCtrl, wx.Dialog))

    def AcceptsFocus(self):
        return True

    def AcceptsFocusFromKeyboard(self):
        return True

    def AcceptsFocusRecursively(self):
        return True

    def OnEraseBackground(self, evt):
        """
        画面のちらつき防止。
        """
        pass

    def OnMotion(self, event):
        x, y = event.GetPosition()
        s = u""
        for rect, tooltip in self.tooltips:
            if rect.Contains((x, y)):
                s = tooltip
        if s <> self.GetToolTipString():
            self.SetToolTipString(s)

    def OnNLeftKeyDown(self, event):
        fc = wx.Window.FindFocus()
        if fc is self:
            self.move_left()
            event.Skip()

    def OnNRightKeyDown(self, event):
        fc = wx.Window.FindFocus()
        if fc is self:
            self.move_right()
            event.Skip()

    def OnNUpKeyDown(self, event):
        if wx.Window.FindFocus() is self:
            if (self.selected_clickable and self.is_selectionstart()) or\
                    event.GetId() == self.shifttabkeyid:
                self.Navigate(wx.NavigationKeyEvent.IsBackward)
            else:
                self.move_up()
            event.Skip()

    def OnNDownKeyDown(self, event):
        if wx.Window.FindFocus() is self:
            if self.selected_clickable and self.is_selectionend() or\
                    event.GetId() == self.tabkeyid:
                self.Navigate(wx.NavigationKeyEvent.IsForward)
            else:
                self.move_down()
            event.Skip()

    def move_right(self):
        self.selected_clickable = self._find_nextclickable_h(self.selected_clickable)
        self.Refresh()

    def move_left(self):
        self.selected_clickable = self._find_prevclickable_h(self.selected_clickable)
        self.Refresh()

    def move_down(self):
        self.selected_clickable = self._find_nextclickable_v(self.selected_clickable)
        self.Refresh()

    def move_up(self):
        self.selected_clickable = self._find_prevclickable_v(self.selected_clickable)
        self.Refresh()

    def is_selectionstart(self):
        i, j = self._find_prevclickable_v(self.selected_clickable)
        return (i, j) == self._find_prevclickable_v(None)

    def is_selectionend(self):
        i, j = self._find_nextclickable_v(self.selected_clickable)
        return (i, j) == self._find_nextclickable_v(None)

    def _find_nextclickable_h(self, current):
        if not self.clickable_table:
            return None
        if current is None:
            i, j = len(self.clickable_table)-1, len(self.clickable_table[-1])-1
        else:
            i, j = current
        # 次のNoneでないアイテムを探す
        while True:
            if len(self.clickable_table[i]) <= j+1:
                # 次の行の最初のアイテム
                i = (i+1)%len(self.clickable_table)
                j = 0
            else:
                # 行内の次のアイテム
                j += 1
            if self.clickable_table[i][j]:
                return (i, j)

    def _find_prevclickable_h(self, current):
        if not self.clickable_table:
            return None
        if current is None:
            i, j = 0, 0
        else:
            i, j = current
        # 前のNoneでないアイテムを探す
        while True:
            if j <= 0:
                # 前の行の最後のアイテム
                i -= 1
                if i < 0:
                    i = len(self.clickable_table)-1
                j = len(self.clickable_table[i])-1
            else:
                # 行内の前のアイテム
                j -= 1
            if self.clickable_table[i][j]:
                return (i, j)

    def _find_nextclickable_v(self, current):
        if not self.clickable_table:
            return None
        if current is None:
            i, j = len(self.clickable_table)-1, len(self.clickable_table[-1])-1
        else:
            i, j = current
        # 次のNoneでないアイテムを探す
        while True:
            if len(self.clickable_table) <= i+1:
                # 次の列の最初のアイテム
                i = 0
                j = (j+1)%len(self.clickable_table[i])
            else:
                # 列内の次のアイテム
                i += 1
            if self.clickable_table[i][j]:
                return (i, j)

    def _find_prevclickable_v(self, current):
        if not self.clickable_table:
            return None
        if current is None:
            i, j = 0, 0
        else:
            i, j = current
        # 前のNoneでないアイテムを探す
        while True:
            if i <= 0:
                # 前の列の最後のアイテム
                i = len(self.clickable_table)-1
                j -= 1
                if j < 0:
                    j = len(self.clickable_table[i])-1
            else:
                # 行内の前のアイテム
                i -= 1
            if self.clickable_table[i][j]:
                return (i, j)

    def OnDropFiles(self, event):
        """
        カードイメージのドロップ。
        """
        files = event.GetFiles()

        seq = []
        for fpath in files:
            ext = os.path.splitext(fpath)[1].lower()
            if ext in cw.EXTS_IMG:
                fpath = cw.util.find_noscalepath(fpath)
                seq.append(fpath)

        if not seq:
            cw.cwpy.play_sound("error")
            return

        cw.cwpy.play_sound("equipment")
        key = self._dropkey
        if None in self.imgpathlist:
            index = 1
        else:
            index = 0
        if key in self.imgpathlist:
            self.imgdpaths[index] = key
        else:
            self.imgdpaths.insert(index, key)
        self.imgpathlist[key] = seq

        self._update_imgdpaths()
        self.ch_imgdpath.Select(index)
        self._choice_imgdpath()

    def _choice_imgdpath(self):
        pass

    def OnPaint2(self, event):
        dc = self.draw()
        if self.selected_clickable:
            i, j = self.selected_clickable
            name = self.clickable_table[i][j]
            rect = self.clickables[name][0]
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), 1, wx.DOT))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])

    def OnLeftDown(self, event):
        pass

    def OnLeftUp(self, event):
        mousepos = event.GetPosition()

        for key, value in self.clickables.iteritems():
            rect, method, _wheelmethod = value

            if method and rect.collidepoint(mousepos):
                method(key)
                break

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE and self.selected_clickable:
            i, j = self.selected_clickable
            key = self.clickable_table[i][j]
            _rect, method, _wheelmethod = self.clickables[key]
            method(key)

    def OnMouseWheel(self, event):
        mousepos = event.GetPosition()

        for key, value in self.clickables.iteritems():
            rect, _method, wheelmethod = value

            if wheelmethod and rect.collidepoint(mousepos):
                wheelmethod(key, cw.util.get_wheelrotation(event))

    def draw_clickabletext(self, dc, s, pos, name, method, wheelmethod, setname=None):
        size = dc.GetTextExtent(s)
        dc.DrawText(s, pos[0], pos[1])

        if setname == name:
            bmp = cw.cwpy.rsrc.dialogs["SELECT"]
            top, left = cw.util.get_centerposition(bmp.GetSize(), pos, size)
            dc.DrawBitmap(bmp, top, left, True)

        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + cw.wins(4), size[1] + cw.wins(4)
            pos = pos[0] - cw.wins(2), pos[1] - cw.wins(2)
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def set_clickablearea(self, pos, size, name, method, wheelmethod):
        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + cw.wins(20), size[1] + cw.wins(20)
            pos = pos[0] - cw.wins(10), pos[1] - cw.wins(10)
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def draw_clickablebmp(self, dc, bmp, pos, name, method, wheelmethod, mask=True):
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, pos[0], pos[1], True)

        self.set_clickablearea(pos, size, name, method, wheelmethod)

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

    def set_imgpathlist(self, reset=True):
        self.Freeze()
        drop = self.imgpathlist.get(self._dropkey, None)
        if reset or not self.imgpaths:
            self.imgpathlist = {}
            self.imgdpath = -1
        else:
            self.imgpathlist = {None:[self.imgpaths]}
            self.imgdpath = 0

        if drop:
            self.imgpathlist[self._dropkey] = drop

        adddefaults = reset or not self.imgpaths
        imgpathlist = cw.util.get_facepaths(self.sex, self.age, adddefaults=adddefaults)
        if 1 == len(imgpathlist) and not drop:
            if self.imgpathlist:
                self.imgpathlist[None].extend(imgpathlist.values()[0])
            else:
                self.imgpathlist.update(imgpathlist)
        else:
            self.imgpathlist.update(imgpathlist)

        self.imgdpaths = self.imgpathlist.keys()
        cw.util.sort_by_attr(self.imgdpaths)

        if self.imgpathlist and (reset or not self.imgpaths):
            if None in self.imgpathlist:
                self.imgpaths = _path_to_imageinfo(self.imgpathlist[None][0])
                self.imgdpath = 0
            else:
                key = self.imgdpaths[0]
                self.imgpaths = _path_to_imageinfo(self.imgpathlist[key][0])
                self.imgdpath = 0

        self._update_imgdpaths()
        self.Thaw()

    def _update_imgdpaths(self):
        self.Freeze()
        self.ch_imgdpath.Clear()
        if 1 < len(self.imgpathlist):
            choices = []
            for key in self.imgdpaths:
                if key is None:
                    choices.append(cw.cwpy.msgs["no_change"])
                else:
                    choices.append(key[1])
            self.ch_imgdpath.SetItems(choices)
            self.ch_imgdpath.Select(self.imgdpath)
            self.ch_imgdpath.Show()
        else:
            self.ch_imgdpath.Hide()

        self.ch_imgdpath.SetToolTipString(self.ch_imgdpath.GetLabelText())
        cw.util.adjust_dropdownwidth(self.ch_imgdpath)
        self._do_layout()
        self.Thaw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self)
            dc = wx.BufferedDC(dc, self.GetSize())
        else:
            dc = wx.PaintDC(self)

        # 共通背景
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins(cw.util.load_wxbmp(path, can_loaded_scaledimage=True))
        dc.DrawBitmap(bmp, 0, 0, False)
        return dc

    def select_autofeatures(self):
        pass

def _path_to_imageinfo(path):
    if isinstance(path, (str, unicode)):
        return [cw.image.ImageInfo(path, postype="Center")]
    return path

class NamePage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.SetDoubleBuffered(True)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.DragAcceptFiles(True)
        self.textctrl = wx.TextCtrl(self, size=cw.wins((125, 18)), style=wx.NO_BORDER)
        self.textctrl.SetMaxLength(14)
        self.textctrl.SetFocus()
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.textctrl.SetFont(font)

        if cw.cwpy.setting.show_autobuttoninentrydialog:
            dc = wx.ClientDC(self)
            font = cw.cwpy.rsrc.get_wxfont("button", pixelsize=cw.wins(14))
            dc.SetFont(font)
            s = cw.cwpy.msgs["auto"]
            tw = dc.GetTextExtent(s)[0] + 16
            self.autoname = cw.cwpy.rsrc.create_wxbutton(self, -1, (tw, cw.wins(20)), s)
            self.autoname.SetFont(font)
        else:
            self.autoname = None

        self.ch_imgdpath = wx.Choice(self, size=(cw.wins(140), -1))
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.ch_imgdpath.SetFont(font)

        self.name = ""
        self.input_name = ""
        self.sex = cw.cwpy.setting.sexcoupons[0]
        self.age = cw.cwpy.setting.periodcoupons[0]
        for period in cw.cwpy.setting.periods:
            if period.firstselect:
                self.age = u"＿" + period.name
                break
        self._update_sex()
        self.imgpaths = []
        self.imgdpath = None
        self.set_imgpathlist(True)
        self._bind()
        self._do_layout()

        # FIXME: アクセラレータに設定した上下左右キーがTextCtrl内で
        #        一切効かなくなるので、TextCtrlがフォーカスを得た時点で
        #        左右キーのアクセラレータを取り除いたテーブルに差し替える
        self.upkeyid = wx.NewId()
        self.downkeyid = wx.NewId()
        self.ctrlleftkeyid = wx.NewId()
        self.ctrlrightkeyid = wx.NewId()
        self.nleftkeyid = wx.NewId()
        self.nrightkeyid = wx.NewId()
        self.nupkeyid = wx.NewId()
        self.ndownkeyid = wx.NewId()
        self.shifttabkeyid = wx.NewId()
        self.tabkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnUpKeyDown, id=self.upkeyid)
        self.Bind(wx.EVT_MENU, self.OnDownKeyDown, id=self.downkeyid)
        self.Bind(wx.EVT_MENU, self.OnCtrlLeftKeyDown, id=self.ctrlleftkeyid)
        self.Bind(wx.EVT_MENU, self.OnCtrlRightKeyDown, id=self.ctrlrightkeyid)
        self.Bind(wx.EVT_MENU, self.OnNLeftKeyDown, id=self.nleftkeyid)
        self.Bind(wx.EVT_MENU, self.OnNRightKeyDown, id=self.nrightkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=self.nupkeyid)
        self.Bind(wx.EVT_MENU, self.OnNDownKeyDown, id=self.ndownkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=self.shifttabkeyid)
        self.Bind(wx.EVT_MENU, self.OnNDownKeyDown, id=self.tabkeyid)
        self._set_acceleratortable(False, True)
        def OnTextCtrlSetFocus(event):
            self._set_acceleratortable(False, True)
            event.Skip(True)
        self.textctrl.Bind(wx.EVT_SET_FOCUS, OnTextCtrlSetFocus)
        def OnChoiceSetFocus(event):
            self._set_acceleratortable(True, False)
            event.Skip(True)
        self.ch_imgdpath.Bind(wx.EVT_SET_FOCUS, OnChoiceSetFocus)
        def OnKillFocus(event):
            self._set_acceleratortable(True, True)
            event.Skip(True)
        self.textctrl.Bind(wx.EVT_KILL_FOCUS, OnKillFocus)

    def _set_acceleratortable(self, leftright, updown):
        seq = [
            (wx.ACCEL_CTRL, wx.WXK_UP, self.upkeyid),
            (wx.ACCEL_CTRL, wx.WXK_DOWN, self.downkeyid),
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.ctrlleftkeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.ctrlrightkeyid),
            (wx.ACCEL_SHIFT, wx.WXK_TAB, self.shifttabkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_TAB, self.tabkeyid),
        ]
        if leftright:
            seq.append((wx.ACCEL_NORMAL, wx.WXK_LEFT, self.nleftkeyid))
            seq.append((wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.nrightkeyid))
        if updown:
            seq.append((wx.ACCEL_NORMAL, wx.WXK_UP, self.nupkeyid))
            seq.append((wx.ACCEL_NORMAL, wx.WXK_DOWN, self.ndownkeyid))
        cw.util.set_acceleratortable(self, seq, ignoreleftrightkeys=(wx.TextCtrl, wx.Dialog))

    def _bind(self):
        AdventurerCreaterPage._bind(self)
        self.Bind(wx.EVT_TEXT, self.OnInputText)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        if self.autoname:
            self.Bind(wx.EVT_BUTTON, self.OnAutoName, self.autoname)
        self.ch_imgdpath.Bind(wx.EVT_CHOICE, self.OnChoiceImgDPath)

    def OnCtrlLeftKeyDown(self, event):
        _rect, method, _wheelmethod = self.clickables["PrevImage"]
        method("PrevImage")

    def OnCtrlRightKeyDown(self, event):
        _rect, method, _wheelmethod = self.clickables["NextImage"]
        method("NextImage")

    def OnNDownKeyDown(self, event):
        fc = wx.Window.FindFocus()
        if fc is self.textctrl:
            self.autoname.SetFocus()
        elif fc is self.autoname:
            self.SetFocusIgnoringChildren()
        elif fc is self and ((self.selected_clickable and self.is_selectionend()) or\
                event.GetId() == self.tabkeyid):
            self.Navigate(wx.NavigationKeyEvent.IsForward)
        elif event.GetId() == self.tabkeyid and fc is self.ch_imgdpath:
            self.Navigate(wx.NavigationKeyEvent.IsForward)
        else:
            AdventurerCreaterPage.OnNDownKeyDown(self, event)

    def OnNUpKeyDown(self, event):
        fc = wx.Window.FindFocus()
        if fc is self.autoname:
            self.textctrl.SetFocus()
        elif fc is self.textctrl:
            self.Parent.closebtn.SetFocus()
        elif fc is self and ((self.selected_clickable and self.is_selectionstart()) or \
                 event.GetId() == self.shifttabkeyid):
            self.autoname.SetFocus()
        elif event.GetId() == self.shifttabkeyid and fc is self.ch_imgdpath:
            self.SetFocusIgnoringChildren()
        else:
            AdventurerCreaterPage.OnNUpKeyDown(self, event)

    def OnNLeftKeyDown(self, event):
        if wx.Window.FindFocus() is self.ch_imgdpath:
            _rect, method, _wheelmethod = self.clickables["PrevImage"]
            method("PrevImage")
        else:
            AdventurerCreaterPage.OnNLeftKeyDown(self, event)

    def OnNRightKeyDown(self, event):
        if wx.Window.FindFocus() is self.ch_imgdpath:
            _rect, method, _wheelmethod = self.clickables["NextImage"]
            method("NextImage")
        else:
            AdventurerCreaterPage.OnNRightKeyDown(self, event)

    def OnMouseWheel(self, event):
        if self.ch_imgdpath.GetRect().Contains(event.GetPosition()):
            if cw.util.get_wheelrotation(event) < 0:
                self._up_imgd()
            else:
                self._down_imgd()
        else:
            AdventurerCreaterPage.OnMouseWheel(self, event)

    def OnUpKeyDown(self, event):
        self._up_imgd()

    def _up_imgd(self):
        if self.ch_imgdpath.IsShown():
            index = self.imgdpath
            index -= 1
            if index < 0:
                index = len(self.imgdpaths) - 1
            self.ch_imgdpath.Select(index)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.ch_imgdpath.GetId())
            self.ch_imgdpath.ProcessEvent(event)

    def OnDownKeyDown(self, event):
        self._down_imgd()

    def _down_imgd(self):
        if self.ch_imgdpath.IsShown():
            index = self.imgdpath
            index += 1
            if len(self.imgdpaths) <= index:
                index = 0
            self.ch_imgdpath.Select(index)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.ch_imgdpath.GetId())
            self.ch_imgdpath.ProcessEvent(event)

    def OnInputText(self, event):
        self.name = self.textctrl.GetValue()
        self.input_name = self.name

        if self.name.strip():
            self.Parent.nextbtn.Enable()
        else:
            self.Parent.nextbtn.Disable()

    def OnAutoName(self, event):
        if not self.sex in cw.cwpy.setting.sexcoupons:
            return
        cw.cwpy.play_sound("signal")
        sindex = cw.cwpy.setting.sexcoupons.index(self.sex)
        randomname = get_randomname(cw.cwpy.setting.sexsubnames[sindex])
        if randomname:
            self.textctrl.SetValue(randomname)
            self.input_name = ""

    def OnChoiceImgDPath(self, event):
        index = self.ch_imgdpath.GetSelection()
        if index <> self.imgdpath:
            cw.cwpy.play_sound("page")
            self._choice_imgdpath()

    def _choice_imgdpath(self):
        index = self.ch_imgdpath.GetSelection()
        self.imgdpath = index
        key = self.imgdpaths[index]
        self.imgpaths = _path_to_imageinfo(self.imgpathlist[key][0])
        self.ch_imgdpath.SetToolTipString(self.ch_imgdpath.GetLabelText())
        self.draw(True)

    def _do_layout(self):
        csize = self.GetClientSize()
        w1, _h1 = self.textctrl.GetSize()
        w2, _h2 = self.ch_imgdpath.GetSize()

        self.textctrl.SetPosition(((csize[0]-w1)/2, cw.wins(90)))
        if self.autoname:
            x, y, w, h = self.textctrl.GetRect()
            self.autoname.SetPosition((x+w+cw.wins(1), y-(self.autoname.GetSize()[1]-h)/2))

        x = cw.wins(275) + cw.wins(cw.SIZE_CARDIMAGE[0])/2 - w2/2
        self.ch_imgdpath.SetPosition((x, cw.wins(225)))

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # welcome to the adventurers inn
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle2", pixelsize=cw.wins(20)))
        s = cw.cwpy.msgs["entry_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(35))
        # Name
        font = cw.cwpy.rsrc.get_wxfont("characre", pixelsize=cw.wins(16))
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = cw.cwpy.msgs["entry_name"]
        dc.DrawText(s, cw.wins(160), cw.wins(72))
        # Sex
        s = cw.cwpy.msgs["entry_sex"]
        dc.DrawText(s, cw.wins(85), cw.wins(125))
        # Age
        s = cw.cwpy.msgs["entry_age"]
        dc.DrawText(s, cw.wins(85), cw.wins(175))

        font = cw.cwpy.rsrc.get_wxfont("characre", pixelsize=cw.wins(14))
        dc.SetFont(font)
        xx = [cw.wins(90), cw.wins(155)]

        self.clickable_table = []
        clickableline = [None, None, None, None]

        # 性別
        x = xx[0]
        y = cw.wins(145)
        for sex in cw.cwpy.setting.sexes:
            s = sex.subname
            pos = (x, y)
            self.draw_clickabletext(dc, s, pos, u"＿" + sex.name, self.set_sex, None, self.sex)
            if xx[1] == x:
                x = xx[0]
                y += cw.wins(15)
                clickableline[1] = u"＿" + sex.name
                self.clickable_table.append(clickableline)
                clickableline = [None, None, None, None]
            else:
                x = xx[1]
                clickableline[0] = u"＿" + sex.name
        if any(clickableline):
            self.clickable_table.append(clickableline)

        # 年代
        x = xx[0]
        y = cw.wins(195)
        for period in cw.cwpy.setting.periods:
            s = period.subname
            pos = (x, y)
            self.draw_clickabletext(dc, s, pos, u"＿" + period.name, self.set_age, None, self.age)
            if xx[1] == x:
                x = xx[0]
                y += cw.wins(20)
                clickableline[1] = u"＿" + period.name
                self.clickable_table.append(clickableline)
                clickableline = [None, None, None, None]
            else:
                x = xx[1]
                clickableline[0] = u"＿" + period.name
        if any(clickableline):
            self.clickable_table.append(clickableline)

        x, y = cw.wins(275), cw.wins(130)

        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (x-cw.wins(20)-bmp.GetWidth(), y+(cw.wins(cw.SIZE_CARDIMAGE[1])-bmp.GetHeight())//2)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg, None)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (x+cw.wins(cw.SIZE_CARDIMAGE[0]+20), y+(cw.wins(cw.SIZE_CARDIMAGE[1])-bmp.GetHeight())//2)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg, None)

        # image
        dc.SetClippingRect(wx.Rect(x, y, cw.wins(cw.SIZE_CARDIMAGE[0]), cw.wins(cw.SIZE_CARDIMAGE[1])))
        basecardtype = "LargeCard"
        for info in self.imgpaths:
            bmp = cw.util.load_wxbmp(info.path, True, can_loaded_scaledimage=True)
            bmp2 = cw.wins(bmp)
            baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                     basecardtype=basecardtype,
                                                     cardpostype="NotCard")
            cw.imageretouch.wxblit_2bitbmp_to_card(dc, bmp2, x + baserect.x, y + baserect.y, True, bitsizekey=bmp)
        dc.DestroyClippingRegion()
        self.set_clickablearea(cw.wins((275, 130)), cw.wins(cw.SIZE_CARDIMAGE), "Face", None, self.on_mousewheel)

        self.tooltips = [(wx.Rect(x-cw.wins(5), y-cw.wins(5), cw.wins(cw.SIZE_CARDIMAGE[1]+10), cw.wins(cw.SIZE_CARDIMAGE[1]+10)),
                          cw.cwpy.msgs["can_use_castimage_from_dropped"])]

        self.clickable_table.append([None, None, "PrevImage", "NextImage"])

        return dc

    def set_sex(self, name):
        if not self.sex == name:
            cw.cwpy.play_sound("click")
            self.sex = name
            self.set_imgpathlist(True)
            self.draw(True)
            self._update_sex()

    def _update_sex(self):
        if self.autoname:
            if self.sex in cw.cwpy.setting.sexcoupons:
                sindex = cw.cwpy.setting.sexcoupons.index(self.sex)
                self.autoname.Enable(bool(get_randomname(cw.cwpy.setting.sexsubnames[sindex])))
            else:
                self.autoname.Enable(False)

    def set_age(self, name):
        if not self.age == name:
            cw.cwpy.play_sound("click")
            self.age = name
            self.set_imgpathlist(True)
            self.draw(True)

    def on_mousewheel(self, name, rotate):
        if rotate < 0:
            self.set_previmg(name)
        elif 0 < rotate:
            self.set_nextimg(name)

    def set_nextimg(self, name):
        _set_nextimg(self, name)

    def set_previmg(self, name):
        _set_previmg(self, name)

    def select_autofeatures(self):
        sindex = cw.cwpy.dice.roll(1, len(cw.cwpy.setting.sexcoupons)) - 1
        self.sex = cw.cwpy.setting.sexcoupons[sindex]
        self.age = cw.cwpy.dice.choice(cw.cwpy.setting.periodcoupons)

        if not self.input_name:
            randomname = get_randomname(cw.cwpy.setting.sexsubnames[sindex])
            if randomname:
                self.textctrl.SetValue(randomname)
                self.input_name = ""

        self.set_imgpathlist(True)
        if self.imgdpaths:
            self.imgdpath = cw.cwpy.dice.roll(1, len(self.imgdpaths)) - 1
            self.ch_imgdpath.SetSelection(self.imgdpath)
            key = self.imgdpaths[self.imgdpath]
            self.imgpaths = _path_to_imageinfo(cw.cwpy.dice.choice(self.imgpathlist[key]))
        else:
            self.imgdpath = ""
            self.imgpaths = []
        self.ch_imgdpath.SetToolTipString(self.ch_imgdpath.GetLabelText())

        self.draw(True)

def get_randomname(sex):
    """<Skin>/Name/*Names.txtから性別に基づいてランダムに名前を得る。
    該当ファイルが存在しなかったり、ファイルに名前が登録されていない
    場合は空文字列を返す。
    """
    names = set()
    fnames = [u"CommonNames.txt"]
    if sex:
        fnames.append(sex + u"Names.txt")
    for fname in fnames:
        fpath = cw.util.join_paths(cw.cwpy.skindir, u"Name",  fname)
        names.update(_read_names(fpath))

    if not names:
        # スキン固有の名前リストがない場合は
        # Exampleから取得する
        names.update(_get_randomnamefromexample(sex, cw.cwpy.setting.skintype))

    if names:
        # 同名のメンバーを避ける
        # (とりあえずパーティに所属しているメンバーとは重複可)
        names2 = names.copy()
        for standby in cw.cwpy.ydata.standbys:
            names.discard(standby.name)
        if not names:
            # 候補がなくなってしまったら重複を許可
            names = names2
        return cw.cwpy.dice.choice(list(names))
    else:
        return u""

def _get_randomnamefromexample(sex, skintype):
    """Exampleフォルダにスキンタイプに該当するファイルがあったら
    その内容を取得する。
    """
    names = set()
    exdirpath = u"Data/SkinBase/Name/Example"
    if os.path.isdir(exdirpath):
        fnames = [u"CommonNames.txt"]
        if sex:
            fnames.append(sex + u"Names.txt")
        for fname in fnames:
            if fname in names:
                continue
            sfname = os.path.splitext(fname)[0] + u"_"
            for fname2 in os.listdir(exdirpath):
                if fname2.startswith(sfname):
                    types = os.path.splitext(fname2[len(sfname):])[0]
                    types = types.lower().split("+")
                    if skintype.lower() in types:
                        fpath = cw.util.join_paths(exdirpath, fname2)
                        names.update(_read_names(fpath))

    return names

def _read_names(fpath):
    """fpathから名前のリストを読み込む。
    """
    names = set()
    try:
        if os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                t = f.read()
                t = cw.util.decode_text(t)
                f.close()
            lines = t.splitlines()
            for line in lines:
                line = line.strip()
                if not line.startswith('#'):
                    names.add(line)
    except:
        cw.util.print_ex()

    return names

class RacePage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        choices = [h.name for h in cw.cwpy.setting.races]
        self.race = choices[0]
        self.choice = wx.Choice(self, choices=choices, size=(cw.wins(125), -1))
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.choice.SetFont(font)
        self.choice.SetStringSelection(self.race)
        self._bind()
        self._do_layout()

    def AcceptsFocus(self):
        return False

    def AcceptsFocusFromKeyboard(self):
        return False

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
        sizer_1.Add((csize[0], cw.wins(90)), 0, 0, 0)
        w, h = self.choice.GetSize()
        margin = (csize[0] - w) / 2
        sizer_1.Add(self.choice, 0, wx.RIGHT|wx.LEFT, margin)
        margin = csize[1] - cw.wins(90) - h
        sizer_1.Add((csize[0], margin), 0, 0, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 種族
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("createtitle", pixelsize=cw.wins(20))
        dc.SetFont(font)
        s = cw.cwpy.msgs["race_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(35))
        # 新規冒険者の種族を決定します。
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        dc.SetFont(font)
        s = cw.cwpy.msgs["race_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(60))
        # 説明
        s = self.get_race().desc
        s = cw.util.txtwrap(s, 1)

        if s.count("\n") > 7:
            s = "\n".join(s.split("\n")[0:8])

        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        dc.SetFont(font)
        dc.DrawLabel(s, cw.wins((107, 130, 200, 110)))

        return dc

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

    def select_autofeatures(self):
        index = cw.cwpy.dice.roll(1, self.choice.GetCount()) - 1
        self.choice.SetSelection(index)
        race = self.choice.GetStringSelection()
        self.race = race
        self.draw(True)

class RelationPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.SetDoubleBuffered(True)
        self.set_parents()
        self.father = None
        self.mother = None
        self._bind()

        self.set_normalacceleratortable()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 血縁
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("createtitle", pixelsize=cw.wins(20))
        dc.SetFont(font)
        s = cw.cwpy.msgs["relation_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(35))
        # 親となる条件を満たしている冒険者が宿にいます。
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        dc.SetFont(font)
        s = cw.cwpy.msgs["relation_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(60))
        # Father
        font = cw.cwpy.rsrc.get_wxfont("dlgtitle2", pixelsize=cw.wins(16))
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = cw.cwpy.msgs["father"]
        dc.DrawText(s, cw.wins(110), cw.wins(92))
        # Mother
        s = cw.cwpy.msgs["mother"]
        dc.DrawText(s, cw.wins(285), cw.wins(92))
        if 1 < len(self.fathers):
            # PrevFather
            bmp = cw.cwpy.rsrc.buttons["LMOVE"]
            pos = cw.wins((70, 150))
            self.draw_clickablebmp(dc, bmp, pos, "PrevFather", self.set_prevfather, None)
            # NextFather
            bmp = cw.cwpy.rsrc.buttons["RMOVE"]
            pos = cw.wins((190, 150))
            self.draw_clickablebmp(dc, bmp, pos, "NextFather", self.set_nextfather, None)
        if 1 < len(self.mothers):
            # PrevMother
            bmp = cw.cwpy.rsrc.buttons["LMOVE"]
            pos = cw.wins((250, 150))
            self.draw_clickablebmp(dc, bmp, pos, "PrevMother", self.set_prevmother, None)
            # NextMother
            bmp = cw.cwpy.rsrc.buttons["RMOVE"]
            pos = cw.wins((370, 150))
            self.draw_clickablebmp(dc, bmp, pos, "NextMother", self.set_nextmother, None)

        self.clickable_table = [["PrevFather", "NextFather", "PrevMother", "NextMother"]]

        # 父親画像
        if self.father:
            paths = self.father.get_imgpaths()
            can_loaded_scaledimage = cw.util.str2bool(cw.header.GetRootAttribute(self.father.fpath).attrs.get("scaledimage", "False"))
            basecardtype = "LargeCard"
        else:
            path = "Resource/Image/Card/FATHER"
            path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
            paths = [cw.image.ImageInfo(path)]
            can_loaded_scaledimage = True
            basecardtype = "NormalCard"

        def draw_paths(pos, paths, can_loaded_scaledimage):
            dc.SetClippingRect(wx.Rect(pos[0], pos[1], cw.wins(cw.SIZE_CARDIMAGE[0]), cw.wins(cw.SIZE_CARDIMAGE[1])))
            for info in paths:
                if info.path:
                    bmp = cw.util.load_wxbmp(info.path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                    bmp2 = cw.wins(bmp)
                    baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                             basecardtype=basecardtype,
                                                             cardpostype="NotCard")
                    cw.imageretouch.wxblit_2bitbmp_to_card(dc, bmp2, pos[0]+baserect.x, pos[1]+baserect.y, True, bitsizekey=bmp)
            dc.DestroyClippingRegion()

        pos = cw.wins((100, 110))
        draw_paths(pos, paths, can_loaded_scaledimage)
        self.set_clickablearea(pos, cw.wins(cw.SIZE_CARDIMAGE), "FatherFace", None, self.on_mousewheel)

        # 母親画像
        if self.mother:
            paths = self.mother.get_imgpaths()
            can_loaded_scaledimage = cw.util.str2bool(cw.header.GetRootAttribute(self.mother.fpath).attrs.get("scaledimage", "False"))
            basecardtype = "LargeCard"
        else:
            path = "Resource/Image/Card/MOTHER"
            path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
            paths = [cw.image.ImageInfo(path)]
            can_loaded_scaledimage = True
            basecardtype = "NormalCard"

        pos = cw.wins((275, 110))
        draw_paths(pos, paths, can_loaded_scaledimage)
        self.set_clickablearea(pos, cw.wins(cw.SIZE_CARDIMAGE), "MotherFace", None, self.on_mousewheel)

        # 父親名前
        font = cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(16))
        dc.SetFont(font)

        if self.father:
            s = self.father.name
        else:
            s = cw.cwpy.msgs["general_father"]

        cw.util.draw_center(dc, s, cw.wins((140, 220)))

        # 母親名前
        if self.mother:
            s = self.mother.name
        else:
            s = cw.cwpy.msgs["general_mother"]

        cw.util.draw_center(dc, s, cw.wins((315, 220)))
        # 父親消費EP
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(14))
        dc.SetFont(font)

        if self.father:
            if self.father.album:
                ep = 10
            else:
                for period in cw.cwpy.setting.periods:
                    if self.father.age == u"＿" + period.name:
                        ep = period.spendep
                        break

            s = cw.cwpy.msgs["consumption_ep"] % (ep, self.father.ep)
            cw.util.draw_center(dc, s, cw.wins((140, 240)))

        # 母親消費EP
        if self.mother:
            if self.mother.album:
                ep = 10
            else:
                for period in cw.cwpy.setting.periods:
                    if self.mother.age == u"＿" + period.name:
                        ep = period.spendep
                        break

            s = cw.cwpy.msgs["consumption_ep"] % (ep, self.mother.ep)
            cw.util.draw_center(dc, s, cw.wins((315, 240)))

        return dc

    def set_nextfather(self, name):
        if 1 < len(self.fathers):
            cw.cwpy.play_sound("page")
            index = self.fathers.index(self.father) + 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_prevfather(self, name):
        if 1 < len(self.fathers):
            cw.cwpy.play_sound("page")
            index = self.fathers.index(self.father) - 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_nextmother(self, name):
        if 1 < len(self.mothers):
            cw.cwpy.play_sound("page")
            index = self.mothers.index(self.mother) + 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def set_prevmother(self, name):
        if 1 < len(self.mothers):
            cw.cwpy.play_sound("page")
            index = self.mothers.index(self.mother) - 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def on_mousewheel(self, name, rotate):
        if name == "FatherFace":
            if rotate < 0:
                self.set_prevfather(name)
            elif 0 < rotate:
                self.set_nextfather(name)
        elif name == "MotherFace":
            if rotate < 0:
                self.set_prevmother(name)
            elif 0 < rotate:
                self.set_nextmother(name)

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

        for header in cw.cwpy.ydata.standbys:
            for period in cw.cwpy.setting.periods:
                if period.spendep > 0 and header.age == u"＿" + period.name and header.ep >= period.spendep:
                    append_header(self, header)
                    break

        for header in cw.cwpy.ydata.album:
            if header.ep >= 10:
                append_header(self, header)

    def is_skip(self):
        if len(self.fathers) > 1 or len(self.mothers) > 1:
            return False
        else:
            return True

    def select_autofeatures(self):
        cw.cwpy.play_sound("signal")
        self.father = cw.cwpy.dice.choice(self.fathers)
        self.mother = cw.cwpy.dice.choice(self.mothers)

        self.draw(True)

class TalentPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.SetDoubleBuffered(True)
        self.talent = u"＿" + cw.cwpy.setting.natures[0].name
        self._bind()

        self.set_normalacceleratortable()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 素質
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("createtitle", pixelsize=cw.wins(20))
        dc.SetFont(font)
        s = cw.cwpy.msgs["nature_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(35))
        # 新規冒険者の傾向を選択して下さい。
        font1 = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        font2 = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(15))
        dc.SetFont(font1)
        s = cw.cwpy.msgs["nature_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(60))

        natures = filter(lambda n: not n.special, cw.cwpy.setting.natures)
        xx = [cw.wins(65), cw.wins(255)]
        self.clickable_table = []
        clickableline = [None, None]
        x = xx[0]
        y = cw.wins(87)
        yd = cw.wins(18)
        yp = cw.wins(55)
        w = cw.wins(145)
        if 6 < len(natures):
            y = cw.wins(80)
            yd = cw.wins(15)
            yp = cw.wins(45)
        for nature in natures:
            s = cw.util.txtwrap(nature.description, mode=5)
            dc.SetFont(font1)
            dc.DrawLabel(s, (x + cw.wins(3), y + yd, w, cw.wins(35)))
            dc.SetFont(font2)
            s = nature.name
            pos = (x, y)
            self.draw_clickabletext(dc, s, pos, u"＿" + nature.name, self.set_talent, None, self.talent)

            if x == xx[1]:
                x = xx[0]
                y += yp
                clickableline[1] = u"＿" + nature.name
                self.clickable_table.append(clickableline)
                clickableline = [None, None]
            else:
                clickableline[0] = u"＿" + nature.name
                x = xx[1]
        if any(clickableline):
            self.clickable_table.append(clickableline)

        return dc

    def set_talent(self, name):
        if not self.talent == name:
            cw.cwpy.play_sound("click")
            self.talent = name
            self.draw(True)

    def select_autofeatures(self):
        cw.cwpy.play_sound("signal")
        talents = []
        for talent in cw.cwpy.setting.natures:
            if not talent.special:
                talents.append(u"＿" + talent.name)
        self.talent = cw.cwpy.dice.choice(talents)

        self.draw(True)

class AttrPage(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent)
        self.SetDoubleBuffered(True)
        self.couponsdata = {}
        self._bind()

        self.set_normalacceleratortable()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 特性
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("createtitle", pixelsize=cw.wins(20))
        dc.SetFont(font)
        s = cw.cwpy.msgs["making_title"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(20))
        # 新規冒険者の生まれや性格などの個性を決定します。
        font = cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15))
        dc.SetFont(font)
        s = cw.cwpy.msgs["making_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(43))
        # 特性
        colour = wx.Colour(128, 128, 128)
        dc.SetTextForeground(colour)
        font = cw.cwpy.rsrc.get_wxfont("paneltitle", pixelsize=cw.wins(14))
        dc.SetFont(font)

        self.clickable_table = []
        for _i in xrange((len(cw.cwpy.setting.makings)+3)//4):
            self.clickable_table.append([None, None, None, None])

        yp = cw.wins(192 // ((len(cw.cwpy.setting.makings)+3)//4))
        for index in xrange(0, len(cw.cwpy.setting.makings), 2):
            column = index % 4
            row = index // 4
            pos = cw.wins(67 + column * 86), cw.wins(64) + (index // 4) * yp
            m1 = cw.cwpy.setting.makings[index]
            s = m1.name
            if index + 1 < len(cw.cwpy.setting.makings):
                m2 = cw.cwpy.setting.makings[index + 1]
                coupons = (m1.name, m2.name)
            else:
                coupons = (m1.name)
            name = (u"＿" + s, coupons)
            self.draw_clickabletext(dc, s, pos, name, self.set_coupon, None)
            self.clickable_table[row][column] = name
            if index + 1 < len(cw.cwpy.setting.makings):
                pos = pos[0] + cw.wins(86), pos[1]
                s = m2.name
                name = (u"＿" + s, coupons)
                self.draw_clickabletext(dc, s, pos, name, self.set_coupon, None)
                self.clickable_table[row][column+1] = name

        return dc

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
            size = size[0] + cw.wins(2), size[1] + cw.wins(2)
            pos = pos[0] - cw.wins(1), pos[1] - cw.wins(1)
            self.clickables[name] = pygame.Rect(pos, size), method, wheelmethod

    def set_coupon(self, name):
        name, coupons = name

        if self.couponsdata.get(coupons, "") == name:
            self.couponsdata[coupons] = ""
        else:
            self.couponsdata[coupons] = name

        cw.cwpy.play_sound("click")
        self.draw(True)

    def get_coupons(self):
        return set(value for value in self.couponsdata.itervalues() if value)

    def select_autofeatures(self):
        cw.cwpy.play_sound("signal")
        self.couponsdata = _get_randommakingsandpair()
        self.draw(True)

def _get_randommakingsandpair():
    # どの程度の確率で左右どちらかの特徴が選択されるかの係数
    nv = cw.cwpy.dice.roll(1, 5)

    makings = {}
    mlen = len(cw.cwpy.setting.makingnames)
    for i in xrange(0, mlen, 2):
        if i + 1 < mlen:
            pair = cw.cwpy.setting.makingnames[i:i+2]
        else:
            pair = cw.cwpy.setting.makingnames[i:i+1]
        n = cw.cwpy.dice.roll(1, len(pair) + nv) - 1
        if n < len(pair):
            makings[tuple(pair)] = u"＿" + pair[n]
    return makings

def get_randommakings():
    """ランダムに選ばれた特徴のsetを返す。"""
    makings = _get_randommakingsandpair()
    return set(makings.itervalues())

#-------------------------------------------------------------------------------
# 宿の登録ダイアログ
#-------------------------------------------------------------------------------

class YadoCreater(wx.Dialog):
    def __init__(self, parent, yadodir=None):
        """宿の登録または編集を行う。
        parent: 親ウィンドウ。
        yadodir: 編集対象の宿のディレクトリ。登録の場合はNone。
        """
        self.create = yadodir is None
        self.yadodir = yadodir

        s = cw.cwpy.msgs["create_base_title"] if self.create else cw.cwpy.msgs["edit_base_title"]
        wx.Dialog.__init__(self, parent, -1, s, size=(318, 180),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        self.SetDoubleBuffered(True)

        self.textctrl = wx.TextCtrl(self, size=cw.wins((175, 24)))
        self.textctrl.SetMaxLength(18)
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.textctrl.SetFont(font)

        if self.create:
            self.textctrl.SetValue(cw.cwpy.msgs["new_base"])
            self._msg1 = cw.cwpy.msgs["create_base_message_1"]
            self._msg2 = cw.util.txtwrap(cw.cwpy.msgs["create_base_message_2"], 0, 32)
            skin = cw.cwpy.setting.skindirname
            is_autoloadparty = True
            skintype = u""
        else:
            fpath = cw.util.join_paths(self.yadodir, "Environment.xml")
            self.data = cw.data.xml2etree(fpath)
            self.name = self.data.gettext("Property/Name", "")
            self.textctrl.SetValue(self.name)
            self._msg1 = cw.cwpy.msgs["edit_base_message_1"]
            self._msg2 = cw.util.txtwrap(cw.cwpy.msgs["edit_base_message_2"], 0, 32)
            self.skindirname = self.data.gettext("Property/Skin", cw.cwpy.setting.skindirname)
            skin = self.skindirname
            skinpath = cw.util.join_paths(u"Data/Skin", self.skindirname, "Skin.xml")
            if os.path.isfile(skinpath):
                skintype = cw.header.GetProperty(skinpath).properties.get(u"Type", u"")
            else:
                skintype = self.data.gettext("Property/Type", u"")
            self.is_autoloadparty = self.data.getbool("Property/NowSelectingParty", "autoload", True)
            is_autoloadparty = self.is_autoloadparty

        choices = []
        self.command0s = []
        self.cautions = []
        self.skindirnames = []
        for name in os.listdir(u"Data/Skin"):
            path = cw.util.join_paths(u"Data/Skin", name)
            skinpath = cw.util.join_paths(u"Data/Skin", name, u"Skin.xml")

            if os.path.isdir(path) and os.path.isfile(skinpath):
                try:
                    prop = cw.header.GetProperty(skinpath)
                    if skintype and prop.properties.get("Type", u"") <> skintype:
                        continue
                    choices.append(prop.properties[u"Name"])
                    self.command0s.append([cw.util.find_resource(cw.util.join_paths(path, u"Resource/Image/Card/COMMAND0"), cw.M_IMG), None])
                    self.cautions.append([cw.util.find_resource(cw.util.join_paths(path, u"Resource/Image/Dialog/CAUTION"), cw.M_IMG), None])
                    self.skindirnames.append(name)
                except Exception:
                    # エラーのあるスキンは無視
                    cw.util.print_ex()

        self.skin = wx.Choice(self, size=(cw.wins(150), -1), choices=choices)
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(16))
        self.skin.SetFont(font)
        if skin in self.skindirnames:
            index = self.skindirnames.index(skin)
            self.skin.Select(index)
        elif cw.cwpy.setting.skindirname in self.skindirnames:
            index = self.skindirnames.index(cw.cwpy.setting.skindirname)
            self.skin.Select(index)
        else:
            self.skin.Select(0)

        # パーティのオートロード
        self.autoload_party = cw.util.CWBackCheckBox(self, -1, cw.cwpy.msgs["autoload_party"])
        self.autoload_party.SetToolTipString(cw.cwpy.msgs["autoload_party_description"])
        self.autoload_party.SetFont(cw.cwpy.rsrc.get_wxfont("paneltitle2", pixelsize=cw.wins(15)))
        self.autoload_party.SetValue(is_autoloadparty)
        self.autoload_party.set_background(self._load_caution())

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

    def create_yado(self):
        name = self.textctrl.GetValue().strip()
        skindirname = self.skindirnames[self.skin.GetSelection()]
        is_autoloadparty = self.autoload_party.GetValue()
        self.yadodir = cw.util.join_paths("Yado", cw.binary.util.check_filename(name))
        self.yadodir = cw.binary.util.check_duplicate(self.yadodir)
        os.makedirs(self.yadodir)
        dnames = ("Adventurer", "Album", "BeastCard", "ItemCard",
                                            "Material", "Party", "SkillCard")

        for dname in dnames:
            path = cw.util.join_paths(self.yadodir, dname)
            os.makedirs(path)

        cw.xmlcreater.create_environment(name, self.yadodir, skindirname, is_autoloadparty)

    def edit_yado(self):
        if cw.util.create_mutex(u"Yado"):
            try:
                if cw.util.create_mutex(self.yadodir):
                    cw.cwpy.play_sound("harvest")
                    self._edit_yado_impl()
                    cw.util.rename_file(cw.util.join_paths(self.yadodir, "Environment.xml"),
                                        cw.util.join_paths(self.yadodir, "Environment.xml.tmp"))
                    cw.util.release_mutex()
                    self._move_dir()
                    cw.util.rename_file(cw.util.join_paths(self.yadodir, "Environment.xml.tmp"),
                                        cw.util.join_paths(self.yadodir, "Environment.xml"))
                    btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
                    self.ProcessEvent(btnevent)
                else:
                    cw.cwpy.play_sound("error")
            finally:
                cw.util.release_mutex()
        else:
            cw.cwpy.play_sound("error")

    def _edit_yado_impl(self):
        name = self.textctrl.GetValue().strip()
        skindirname = self.skindirnames[self.skin.GetSelection()]
        is_autoloadparty = self.autoload_party.GetValue()

        if name <> self.name or\
                skindirname <> self.skindirname or\
                is_autoloadparty <> self.is_autoloadparty:
            # データ上の編集
            if not self.data.find("Property/Name") is None:
                self.data.edit("Property/Name", name)
            else:
                e = cw.data.make_element("Name", name)
                self.data.insert("Property", e, 0)

            self.data.edit("Property/Skin", skindirname)
            self.data.edit("Property/NowSelectingParty", str(is_autoloadparty), "autoload")

            self.data.write()

    def _move_dir(self):
        name = self.textctrl.GetValue().strip()
        olddname = os.path.basename(self.yadodir)
        cw.util.remove(cw.util.join_paths(u"Data/Temp/Local", olddname))

        if name <> self.name:
            # ディレクトリの移動
            yadodir = os.path.dirname(self.yadodir)
            olddname = os.path.basename(self.yadodir)
            dname = cw.binary.util.check_filename(name)
            if os.path.normcase(os.path.basename(self.yadodir)) <> os.path.normcase(dname):
                yadodir = cw.util.join_paths(yadodir, dname)
                yadodir = cw.binary.util.check_duplicate(yadodir)
                try:
                    shutil.move(self.yadodir, yadodir)
                    self.yadodir = yadodir
                    if cw.cwpy.setting.lastyado == olddname:
                        cw.cwpy.setting.lastyado = os.path.basename(self.yadodir)
                except Exception:
                    cw.util.print_ex()

    def OnInput(self, event):
        name = self.textctrl.GetValue().strip()

        if name:
            self.okbtn.Enable()
        else:
            self.okbtn.Disable()

    def OnChoice(self, event):
        cw.cwpy.play_sound("page")
        self.autoload_party.set_background(self._load_caution())
        self.Refresh()

    def OnOk(self, event):
        if self.create:
            self.create_yado()
        else:
            self.edit_yado()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def _load_caution(self):
        index = self.skin.GetSelection()
        imgdata = self.cautions[index]
        bmp = imgdata[1]
        if not bmp:
            bmp = cw.wins((cw.util.load_wxbmp(imgdata[0], False, can_loaded_scaledimage=True), cw.setting.SIZE_RESOURCES[u"Dialog/CAUTION"]))
            imgdata[1] = bmp
        return bmp

    def OnPaint2(self, event):
        dc = wx.PaintDC(self)
        # background
        index = self.skin.GetSelection()
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, self._load_caution(), csize)

        # card image
        imgdata = self.command0s[index]
        bmp = imgdata[1]
        if not bmp:
            bmp = cw.wins(cw.util.load_wxbmp(imgdata[0], True, can_loaded_scaledimage=True))
            imgdata[1] = bmp
        bmph = bmp.GetHeight()
        y = (self._inputareaheight-bmph) / 2
        dc.DrawBitmap(bmp, cw.wins(10), y, True)
        bmpw = bmp.GetWidth()

        # text
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)
        s = self._msg1
        y = cw.wins(10)
        dc.DrawText(s, bmpw+cw.wins(20), y)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg2", pixelsize=cw.wins(16))
        dc.SetFont(font)
        _w, h, _lineheight = dc.GetMultiLineTextExtent(s)
        y += h + cw.wins(5)
        s = self._msg2
        dc.DrawText(s, bmpw+cw.wins(20), y)

        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)

        tw1, th1 = dc.GetTextExtent(cw.cwpy.msgs["input_name"])
        tw2, th2 = dc.GetTextExtent(cw.cwpy.msgs["select_skin"])
        tw = max(tw1, tw2)

        s = cw.cwpy.msgs["input_name"]
        x, y, w, h = self.textctrl.GetRect()
        x -= tw + cw.wins(5)
        y += (h-th1) / 2
        dc.DrawText(s, x, y)

        s = cw.cwpy.msgs["select_skin"]
        x, y, w, h = self.skin.GetRect()
        x -= tw + cw.wins(5)
        y += (h-th2) / 2
        dc.DrawText(s, x, y)

    def _bind(self):
        self.Bind(wx.EVT_TEXT, self.OnInput, self.textctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_PAINT, self.OnPaint2)
        self.Bind(wx.EVT_CHOICE, self.OnChoice, self.skin)
        def recurse(ctrl):
            if not isinstance(ctrl, (wx.TextCtrl, wx.SpinCtrl)):
                ctrl.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
            for child in ctrl.GetChildren():
                recurse(child)
        recurse(self)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)

        dc = wx.ClientDC(self)
        cardw = cw.wins(cw.SIZE_CARDIMAGE[0])

        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)
        s = self._msg1
        w1, h1, _lineheight = dc.GetMultiLineTextExtent(s)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg2", pixelsize=cw.wins(16))
        dc.SetFont(font)
        s = self._msg2
        w2, h2, _lineheight = dc.GetMultiLineTextExtent(s)
        mw = max(w1, w2)

        sizer_1.Add((cardw+mw+cw.wins(30), h1+h2+cw.wins(25)), 0, 0, 0)

        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)
        w1, _h = dc.GetTextExtent(cw.cwpy.msgs["input_name"])
        w2, _h = dc.GetTextExtent(cw.cwpy.msgs["select_skin"])
        w = max(w1, w2)

        sizer_2.Add((cw.wins(20)+cardw, cw.wins(0)), 0, 0, 0)
        sizer_2.Add((w+cw.wins(5), cw.wins(0)), 0, 0, 0)
        sizer_2.Add(self.textctrl, 0, 0, 0)
        sizer_2.Add(cw.wins((10, 0)), 0, 0, 0)
        sizer_1.Add(sizer_2, 0, 0, 0)

        sizer_1.Add(cw.wins((0, 5)), 0, 0, 0)

        sizer_3.Add((cw.wins(20)+cardw, cw.wins(0)), 0, 0, 0)
        sizer_3.Add((w+cw.wins(5), cw.wins(0)), 0, 0, 0)
        sizer_3.Add(self.skin, 0, 0, 0)
        sizer_3.Add(cw.wins((10, 00)), 0, 0, 0)
        sizer_1.Add(sizer_3, 0, 0, 0)

        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        sizer_1.Add(self.autoload_party, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_RIGHT, cw.wins(10))

        sizer_1.Add(cw.wins((0, 12)), 0, 0, 0)

        csize = sizer_1.CalcMin()
        self._inputareaheight = csize[1]

        margin = (csize[0] - self.okbtn.GetSize()[0] * 2) / 3
        sizer_4.Add(self.okbtn, 0, wx.LEFT, margin)
        sizer_4.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, margin)
        sizer_1.Add(sizer_4, 1, wx.EXPAND, 0)

        sizer_1.Add(cw.wins((0, 10)), 0, 0, 0)

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.SetClientSize(sizer_1.CalcMin())
        self.Layout()

#-------------------------------------------------------------------------------
# 冒険者のデザインダイアログ
#-------------------------------------------------------------------------------

class AdventurerDesignDialog(wx.Dialog):
    def __init__(self, parent, ccard):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["design_title"],
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = False
        # buttonlist
        self.buttonlist = []

        self.ccard = ccard

        # toppanel
        self.toppanel = DesignPanel(self, self.ccard)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_decide"])
        self.buttonlist.append(self.okbtn)
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
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
        width = cw.wins(400 - 6)
        btnwidth = self.buttonlist[0].GetSize()[0] * len(self.buttonlist)
        margin = (width - btnwidth) / (len(self.buttonlist)+1)
        margin2 = margin + (width - btnwidth) % (len(self.buttonlist)+1)

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_btn.Add((margin, 0), 0, 0, 0)
            sizer_btn.Add(button, 0, wx.TOP|wx.BOTTOM, cw.wins(3))
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
        if self.toppanel.is_changedimgpath():
            self.ccard.set_images(self.toppanel.imgpaths)
        self.ccard.data.is_edited = True
        self.ccard.data.write_xml()

        def func(ccard):
            cw.cwpy.play_sound("harvest")
            if isinstance(ccard, cw.sprite.card.CWPyCard):
                cw.animation.animate_sprite(ccard, "hide")
                ccard.update_image()
                cw.animation.animate_sprite(ccard, "deal")
        cw.cwpy.exec_func(func, self.ccard)

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class DesignPanel(AdventurerCreaterPage):
    def __init__(self, parent, ccard):
        AdventurerCreaterPage.__init__(self, parent, size=cw.wins((400, 370)), freeze=False)
        self.SetMinSize(cw.wins((400, 370)))
        self.SetDoubleBuffered(True)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.DragAcceptFiles(True)

        self.ccard = ccard

        self.namectrl = wx.TextCtrl(self, size=cw.wins((125, 18)), style=wx.NO_BORDER)
        self.namectrl.SetMaxLength(14)
        self.namectrl.SetFocus()
        font = cw.cwpy.rsrc.get_wxfont("inputname", pixelsize=cw.wins(16))
        self.namectrl.SetFont(font)

        self.ch_imgdpath = wx.Choice(self, size=(cw.wins(140), -1))
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.ch_imgdpath.SetFont(font)

        font = cw.cwpy.rsrc.get_wxfont("datadesc", pixelsize=cw.wins(14))
        self.descctrl = wx.TextCtrl(self, style=wx.NO_BORDER|wx.TE_MULTILINE)
        self.descctrl.SetFont(font)

        dc = wx.ClientDC(self)
        dc.SetFont(self.descctrl.GetFont())
        w = dc.GetTextExtent("#")[0] * 39
        dc.Destroy()
        self.descctrl.SetClientSize((w, cw.wins(107)))
        self.descctrl.SetInitialSize(self.descctrl.GetSize())

        self.imgpaths = []
        for info in self.ccard.get_imagepaths():
            self.imgpaths.append(cw.image.ImageInfo(cw.util.join_yadodir(info.path), base=info, basecardtype="LargeCard"))
        self._oldimgpath = self.imgpaths[:]
        self.can_loaded_scaledimage = self.ccard.data.getbool(".", "scaledimage", False)

        self.name = self.ccard.get_name()
        self.desc = self.ccard.get_description()
        self.sex = self.ccard.get_sex()
        self.age = self.ccard.get_age()

        self.namectrl.SetValue(self.name)
        self.namectrl.SetSelection(0, len(self.name))
        self.descctrl.SetValue(cw.util.decodewrap(self.desc))

        self.set_imgpathlist(False)
        self._bind()
        self._do_layout()

        # FIXME: アクセラレータに設定した矢印キーがTextCtrl内で
        #        一切効かなくなるので、TextCtrlがフォーカスを得た時点で
        #        矢印キーのアクセラレータを取り除いたテーブルに差し替える
        self.upkeyid = wx.NewId()
        self.downkeyid = wx.NewId()
        self.ctrlleftkeyid = wx.NewId()
        self.ctrlrightkeyid = wx.NewId()
        self.nleftkeyid = wx.NewId()
        self.nrightkeyid = wx.NewId()
        self.nupkeyid = wx.NewId()
        self.ndownkeyid = wx.NewId()
        self.shifttabkeyid = wx.NewId()
        self.tabkeyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnUpKeyDown, id=self.upkeyid)
        self.Bind(wx.EVT_MENU, self.OnDownKeyDown, id=self.downkeyid)
        self.Bind(wx.EVT_MENU, self.OnCtrlLeftKeyDown, id=self.ctrlleftkeyid)
        self.Bind(wx.EVT_MENU, self.OnCtrlRightKeyDown, id=self.ctrlrightkeyid)
        self.Bind(wx.EVT_MENU, self.OnNLeftKeyDown, id=self.nleftkeyid)
        self.Bind(wx.EVT_MENU, self.OnNRightKeyDown, id=self.nrightkeyid)
        self.Bind(wx.EVT_MENU, self.OnNUpKeyDown, id=self.nupkeyid)
        self.Bind(wx.EVT_MENU, self.OnNDownKeyDown, id=self.ndownkeyid)
        self.Bind(wx.EVT_MENU, self.OnShiftTab, id=self.shifttabkeyid)
        self.Bind(wx.EVT_MENU, self.OnTab, id=self.tabkeyid)
        self._set_acceleratortable(False, True)
        def OnLeftRightSetFocus(event):
            self._set_acceleratortable(False, True)
            event.Skip(True)
        self.namectrl.Bind(wx.EVT_SET_FOCUS, OnLeftRightSetFocus)
        def OnArrowsSetFocus(event):
            self._set_acceleratortable(False, False)
            event.Skip(True)
        self.descctrl.Bind(wx.EVT_SET_FOCUS, OnArrowsSetFocus)
        def OnUpDownSetFocus(event):
            self._set_acceleratortable(True, False)
            event.Skip(True)
        self.ch_imgdpath.Bind(wx.EVT_SET_FOCUS, OnUpDownSetFocus)
        def OnKillFocus(event):
            self._set_acceleratortable(True, True)
            event.Skip(True)
        self.namectrl.Bind(wx.EVT_KILL_FOCUS, OnKillFocus)
        self.descctrl.Bind(wx.EVT_KILL_FOCUS, OnKillFocus)
        self.ch_imgdpath.Bind(wx.EVT_KILL_FOCUS, OnKillFocus)

    def _set_acceleratortable(self, leftright, updown):
        seq = [
            (wx.ACCEL_CTRL, wx.WXK_UP, self.upkeyid),
            (wx.ACCEL_CTRL, wx.WXK_DOWN, self.downkeyid),
            (wx.ACCEL_CTRL, wx.WXK_LEFT, self.ctrlleftkeyid),
            (wx.ACCEL_CTRL, wx.WXK_RIGHT, self.ctrlrightkeyid),
            (wx.ACCEL_SHIFT, wx.WXK_TAB, self.shifttabkeyid),
            (wx.ACCEL_NORMAL, wx.WXK_TAB, self.tabkeyid),
        ]
        if leftright:
            seq.append((wx.ACCEL_NORMAL, wx.WXK_LEFT, self.nleftkeyid))
            seq.append((wx.ACCEL_NORMAL, wx.WXK_RIGHT, self.nrightkeyid))
        if updown:
            seq.append((wx.ACCEL_NORMAL, wx.WXK_UP, self.nupkeyid))
            seq.append((wx.ACCEL_NORMAL, wx.WXK_DOWN, self.ndownkeyid))
        cw.util.set_acceleratortable(self, list(seq), ignoreleftrightkeys=(wx.TextCtrl, wx.Dialog))

    def is_selectionstart(self):
        # 常にFalseを返す事で矢印キーによるフォーカス移動を行わせない
        return False

    def is_selectionend(self):
        # 常にFalseを返す事で矢印キーによるフォーカス移動を行わせない
        return False

    def OnShiftTab(self, event):
        fc = wx.Window.FindFocus()
        if fc is self.descctrl:
            self.SetFocusIgnoringChildren()
        elif fc is self:
            self.namectrl.SetFocus()
        elif fc is self.ch_imgdpath:
            self.SetFocusIgnoringChildren()
        else:
            fc.Navigate(wx.NavigationKeyEvent.IsBackward)

    def OnTab(self, event):
        fc = wx.Window.FindFocus()
        if fc is self.namectrl:
            self.SetFocusIgnoringChildren()
        elif fc is self:
            self.descctrl.SetFocus()
        elif fc is self.ch_imgdpath:
            self.descctrl.SetFocus()
        else:
            fc.Navigate(wx.NavigationKeyEvent.IsForward)

    def OnCtrlLeftKeyDown(self, event):
        _rect, method, _wheelmethod = self.clickables["PrevImage"]
        method("PrevImage")

    def OnCtrlRightKeyDown(self, event):
        _rect, method, _wheelmethod = self.clickables["NextImage"]
        method("NextImage")

    def OnNLeftKeyDown(self, event):
        if wx.Window.FindFocus() is self.ch_imgdpath:
            _rect, method, _wheelmethod = self.clickables["PrevImage"]
            method("PrevImage")
        else:
            AdventurerCreaterPage.OnNLeftKeyDown(self, event)

    def OnNRightKeyDown(self, event):
        if wx.Window.FindFocus() is self.ch_imgdpath:
            _rect, method, _wheelmethod = self.clickables["NextImage"]
            method("NextImage")
        else:
            AdventurerCreaterPage.OnNRightKeyDown(self, event)

    def is_changedimgpath(self):
        return self._oldimgpath <> self.imgpaths

    def _bind(self):
        AdventurerCreaterPage._bind(self)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.namectrl.Bind(wx.EVT_TEXT, self.OnInputName)
        self.ch_imgdpath.Bind(wx.EVT_CHOICE, self.OnChoiceImgDPath)

    def OnMouseWheel(self, event):
        if self.ch_imgdpath.GetRect().Contains(event.GetPosition()):
            if cw.util.get_wheelrotation(event) < 0:
                self._up_imgd()
            else:
                self._down_imgd()
        else:
            AdventurerCreaterPage.OnMouseWheel(self, event)

    def OnUpKeyDown(self, event):
        self._up_imgd()

    def _up_imgd(self):
        if self.ch_imgdpath.IsShown():
            index = self.imgdpath
            index -= 1
            if index < 0:
                index = len(self.imgdpaths) - 1
            self.ch_imgdpath.Select(index)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.ch_imgdpath.GetId())
            self.ch_imgdpath.ProcessEvent(event)

    def OnDownKeyDown(self, event):
        self._down_imgd()

    def _down_imgd(self):
        if self.ch_imgdpath.IsShown():
            index = self.imgdpath
            index += 1
            if len(self.imgdpaths) <= index:
                index = 0
            self.ch_imgdpath.Select(index)
            event = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, self.ch_imgdpath.GetId())
            self.ch_imgdpath.ProcessEvent(event)

    def OnInputName(self, event):
        self.name = self.namectrl.GetValue()

        if self.name.strip():
            self.Parent.okbtn.Enable()
        else:
            self.Parent.okbtn.Disable()

    def OnChoiceImgDPath(self, event):
        index = self.ch_imgdpath.GetSelection()
        if index <> self.imgdpath:
            cw.cwpy.play_sound("page")
            self._choice_imgdpath()

    def _choice_imgdpath(self):
        index = self.ch_imgdpath.GetSelection()
        self.imgdpath = index
        key = self.imgdpaths[index]
        self.imgpaths = _path_to_imageinfo(self.imgpathlist[key][0])
        if self.is_changedimgpath():
            self.can_loaded_scaledimage = True
        else:
            self.can_loaded_scaledimage = self.ccard.data.getbool(".", "scaledimage", False)
        self.ch_imgdpath.SetToolTipString(self.ch_imgdpath.GetLabelText())
        self.draw(True)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.SetMinSize(cw.wins((400, 370)))

        if self.ch_imgdpath.IsShown():
            sizer_1.Add(self.namectrl, 0, wx.TOP|wx.CENTER, cw.wins(55))
            sizer_1.Add(self.ch_imgdpath, 0, wx.TOP|wx.CENTER, cw.wins(133))
            h = self.ch_imgdpath.GetSize()[1]
            sizer_1.Add(self.descctrl, 0, wx.TOP|wx.CENTER, cw.wins(45)-h)
        else:
            sizer_1.Add(self.namectrl, 0, wx.TOP|wx.CENTER, cw.wins(60))
            sizer_1.Add(self.descctrl, 0, wx.TOP|wx.CENTER, cw.wins(158))

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]

        # 背景
        path = "Table/Bill"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins(cw.util.load_wxbmp(path, can_loaded_scaledimage=True))
        dc.DrawBitmap(bmp, 0, 0, False)

        # Resident Registration
        font = cw.cwpy.rsrc.get_wxfont("characre", pixelsize=cw.wins(16))
        dc.SetFont(font)
        dc.SetTextForeground(wx.BLACK)
        s = cw.cwpy.msgs["edit_character_message"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, cw.wins(15))

        if self.ch_imgdpath.IsShown():
            y = cw.wins(40)
            y2 = 111
        else:
            y = cw.wins(45)
            y2 = 116

        # Name
        font = cw.cwpy.rsrc.get_wxfont("characre", pixelsize=cw.wins(14))
        dc.SetFont(font)
        s = cw.cwpy.msgs["entry_name"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, y)
        # Image
        y += cw.wins(50)
        s = cw.cwpy.msgs["entry_image"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, y)
        # Comment
        if self.ch_imgdpath.IsShown():
            y += cw.wins(145)
        else:
            y += cw.wins(125)
        s = cw.cwpy.msgs["entry_comment"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, y)

        x, y = (cwidth - cw.wins(cw.SIZE_CARDIMAGE[0])) / 2, cw.wins(y2)

        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (x-cw.wins(20)-bmp.GetWidth(), y+(cw.wins(cw.SIZE_CARDIMAGE[1])-bmp.GetHeight())//2)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg, None)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (x+cw.wins(cw.SIZE_CARDIMAGE[0]+20), y+(cw.wins(cw.SIZE_CARDIMAGE[1])-bmp.GetHeight())//2)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg, None)
        # image
        dc.SetClippingRect(wx.Rect(x, y, cw.wins(cw.SIZE_CARDIMAGE[0]), cw.wins(cw.SIZE_CARDIMAGE[1])))
        if self.is_changedimgpath():
            can_loaded_scaledimage = True
        else:
            can_loaded_scaledimage = self.can_loaded_scaledimage
        for info in self.imgpaths:
            bmp = cw.util.load_wxbmp(info.path, True, can_loaded_scaledimage=can_loaded_scaledimage)
            bmp2 = cw.wins(bmp)

            baserect = info.calc_basecardposition_wx(bmp2.GetSize(), noscale=False,
                                                     basecardtype="LargeCard",
                                                     cardpostype="NotCard")

            cw.imageretouch.wxblit_2bitbmp_to_card(dc, bmp2, x+baserect.x, y+baserect.y, True, bitsizekey=bmp)
        dc.DestroyClippingRegion()
        self.set_clickablearea((x, y), cw.wins(cw.SIZE_CARDIMAGE), "Face", None, self.on_mousewheel)

        self.tooltips = [(wx.Rect(x-cw.wins(5), y-cw.wins(5), cw.wins(cw.SIZE_CARDIMAGE[0]+10), cw.wins(cw.SIZE_CARDIMAGE[1]+10)),
                          cw.cwpy.msgs["can_use_castimage_from_dropped"])]

        self.clickable_table = [["PrevImage", "NextImage"]]

        return dc

    def on_mousewheel(self, name, rotate):
        if rotate < 0:
            self.set_previmg(name)
        elif 0 < rotate:
            self.set_nextimg(name)

    def set_nextimg(self, name):
        _set_nextimg(self, name)

    def set_previmg(self, name):
        _set_previmg(self, name)

def _index_of(imgpaths, imgpathlist):
    assert isinstance(imgpaths, list)
    if imgpaths in imgpathlist:
        return imgpathlist.index(imgpaths)
    else:
        return imgpathlist.index(imgpaths[0].path)

def _set_nextimg(panel, name):
    if panel.imgpathlist:
        cw.cwpy.play_sound("page")
        key = panel.imgdpaths[panel.imgdpath]
        if key is None and 1 < len(panel.imgdpaths):
            panel.imgdpath = 1
            panel.ch_imgdpath.SetSelection(1)
            key = panel.imgdpaths[1]
            imgpathlist = panel.imgpathlist[key]
            panel.imgpaths = _path_to_imageinfo(imgpathlist[0])
        else:
            imgpathlist = panel.imgpathlist[key]

            index = (_index_of(panel.imgpaths, imgpathlist) + 1) % len(imgpathlist)
            panel.imgpaths = _path_to_imageinfo(imgpathlist[index])

        panel.Refresh()

def _set_previmg(panel, name):
    if panel.imgpathlist:
        cw.cwpy.play_sound("page")
        key = panel.imgdpaths[panel.imgdpath]
        if key is None and 1 < len(panel.imgdpaths):
            panel.imgdpath = 1
            panel.ch_imgdpath.SetSelection(1)
            key = panel.imgdpaths[1]
            imgpathlist = panel.imgpathlist[key]
            panel.imgpaths = _path_to_imageinfo(imgpathlist[0])
        else:
            imgpathlist = panel.imgpathlist[key]

            index = _index_of(panel.imgpaths, imgpathlist) - 1
            panel.imgpaths = _path_to_imageinfo(imgpathlist[index])

        panel.Refresh()

def main():
    pass

if __name__ == "__main__":
    main()
