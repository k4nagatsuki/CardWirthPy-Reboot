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
        wx.Dialog.__init__(self, parent, -1, u"不足データの補填",
                            style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU)
        self.ccard = ccard
        self.sex = u"＿♂"
        self.age = u"＿子供"
        # 画像
        bmp = cw.util.load_wxbmp(ccard.imgpath, True)
        self.bmp = wx.StaticBitmap(self, -1, bmp)
        # 各種テキスト
        s = u"次の冒険者には必要なデータが不足しています。次の項目\n"
        s += u"を入力し、決定ボタンを押してください。"
        self.text_message = wx.StaticText(self, -1, s)
        self.box = wx.StaticBox(self, -1)
        self.text_name = wx.StaticText(self, -1, ccard.name)
        font = cw.cwpy.rsrc.get_wxfont()
        self.text_name.SetFont(font)
        self.text_caution = wx.StaticText(self, -1, "Caution!")
        self.text_caution.SetForegroundColour(wx.RED)
        font = cw.cwpy.rsrc.get_wxfont(size=14, style=wx.ITALIC)
        self.text_caution.SetFont(font)
        # ラジオボックス
        seq = (u"男性", u"女性")
        self.rb_sex = wx.RadioBox(self, -1, u"性別",
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        seq = (u"子供", u"若者", u"大人", u"老人")
        self.rb_age = wx.RadioBox(self, -1, u"年齢",
                        choices=seq, style=wx.RA_SPECIFY_ROWS, majorDimension=2)
        # OKボタン
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (120, 30), u"決定")
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

        if s == u"男性":
            self.sex = u"＿♂"
        else:
            self.sex = u"＿♀"

    def OnClickRbAge(self, event):
        s = event.GetString()

        if s == u"子供":
            self.age = u"＿子供"
        elif s == u"若者":
            self.age = u"＿若者"
        elif s == u"大人":
            self.age = u"＿大人"
        else:
            self.age = u"＿老人"

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
        if sex == u"＿♂":
            self.set_coupon(sex, 0)
            self.str += 1
            self.aggressive += 0.5
        elif sex == u"＿♀":
            self.set_coupon(sex, 0)
            self.dex += 1
            self.cautious += 0.5

    def set_age(self, age):
        if age == u"＿子供":
            self.set_coupon(u"＿子供", 0)
            self.level = 1
            self.dex += 1
            self.agl += 1
            self.str -= 1
            self.vit -= 1
            self.cheerful += 0.5
            self.cautious -= 0.5
        elif age == u"＿若者":
            self.set_coupon(age, 0)
            self.level = 1
        elif age == u"＿大人":
            self.set_coupon(age, 0)
            self.set_coupon(u"熟練", 2)
            self.level = 2
            self.vit -= 1
            self.aggressive -= 0.5
            self.cautious += 0.5
        elif age == u"＿老人":
            self.set_coupon(age, 0)
            self.set_coupon(u"老獪", 4)
            self.level = 2
            self.dex -= 1
            self.agl -= 1
            self.int += 1
            self.str -= 1
            self.vit -= 1
            self.min += 1
            self.aggressive -= 0.5
            self.brave -= 0.5
            self.cautious += 0.5
            self.trickish += 0.5

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
            self.set_coupon(u"父：" + father.name, 0)
        else:
            fgene = cw.header.Gene()
            fgene.set_randombit()

        if mother:
            self.has_parents = True
            mother.made_baby()
            mgene = mother.gene
            mgene = mgene.rotate_right()
            self.set_coupon(u"母：" + mother.name, 0)
        else:
            mgene = cw.header.Gene()
            mgene.set_randombit()

        self.gene = fgene.fusion(mgene)

    def set_talent(self, talent):
        if not self.gene:
            self.set_parents()

        oldtalent = talent
        n = self.gene.count_bits()

        if n == 10:
            talent = u"＿神仙型"
            self.gene.reverse()
        elif n >= 8:
            talent = u"＿英雄型"
            self.gene.reverse()
        elif n >= 6:
            if talent in (u"＿標準型", u"＿万能型"):
                talent = u"＿英明型"
            elif talent in (u"＿勇将型", u"＿豪傑型"):
                talent = u"＿無双型"
            else:
                talent = u"＿天才型"

            self.gene.reverse()
        elif n == 0 and self.has_parents:
            talent = u"＿凡庸型"

        self.set_coupon(talent, 0)
        self.gene.set_talentbit(talent, oldtalent)

        if talent == u"＿標準型":
            self.min += 1
            self.aggressive -= 0.5
            self.cautious += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿万能型":
            self.dex += 1
            self.agl += 1
            self.min -= 1
            self.cheerful += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿勇将型":
            self.dex -= 1
            self.int -= 1
            self.str += 2
            self.brave += 1
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿豪傑型":
            self.dex -= 2
            self.agl -= 1
            self.int -= 2
            self.str += 3
            self.vit += 1
            self.min -= 1
            self.aggressive += 0.5
            self.brave += 0.5
            self.cautious -= 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿知将型":
            self.int += 2
            self.str -= 1
            self.vit -= 1
            self.cautious += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿策士型":
            self.agl -= 1
            self.int += 3
            self.str -= 2
            self.vit -= 2
            self.cautious += 0.5
            self.trickish += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿英明型":
            self.dex += 1
            self.agl += 1
            self.int += 1
            self.str += 1
            self.vit += 1
            self.min += 1
            self.cautious += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿無双型":
            self.agl += 1
            self.str += 3
            self.vit += 2
            self.aggressive += 0.5
            self.brave += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿天才型":
            self.dex += 1
            self.int += 3
            self.min += 2
            self.cautious += 0.5
            self.trickish += 0.5
            self.set_coupon(u"＠レベル上限", 10)
        elif talent == u"＿凡庸型":
            self.dex -= 2
            self.agl -= 2
            self.int -= 2
            self.str -= 2
            self.vit -= 2
            self.min -= 2
            self.brave -= 0.5
            self.cautious += 0.5
            self.set_coupon(u"＠レベル上限", 12)
        elif talent == u"＿英雄型":
            self.dex += 1
            self.agl += 1
            self.int += 2
            self.str += 2
            self.vit += 1
            self.min += 2
            self.cheerful += 0.5
            self.brave += 0.5
            self.trickish -= 0.5
            self.set_coupon(u"＠レベル上限", 12)
        elif talent == u"＿神仙型":
            self.dex += 2
            self.agl += 2
            self.int += 2
            self.str += 2
            self.vit += 2
            self.min += 2
            self.set_coupon(u"＠レベル上限", 15)

    def set_attrbutes(self, attrs):
        for attr in attrs:
            self.set_attribute(attr)

    def set_attribute(self, attr):
        if attr == u"＿秀麗":
            self.vit -= 1
            self.cheerful += 0.5
        elif attr == u"＿醜悪":
            self.vit += 1
            self.cheerful -= 0.5
        elif attr == u"＿高貴の出":
            self.aggressive -= 0.5
            self.brave += 0.5
        elif attr == u"＿下賎の出":
            self.cautious -= 0.5
            self.trickish += 0.5
        elif attr == u"＿都会育ち":
            self.int += 1
            self.vit -= 1
            self.cheerful -= 0.5
            self.trickish += 0.5
        elif attr == u"＿田舎育ち":
            self.agl -= 1
            self.vit += 1
            self.trickish -= 0.5
        elif attr == u"＿裕福":
            self.min -= 1
            self.aggressive -= 0.5
            self.trickish -= 0.5
        elif attr == u"＿貧乏":
            self.min += 1
            self.aggressive += 0.5
            self.brave -= 0.5
        elif attr == u"＿厚き信仰":
            self.int -= 1
            self.min += 1
            self.brave += 0.5
            self.trickish -= 0.5
        elif attr == u"＿不心得者":
            self.cautious += 0.5
            self.trickish += 0.5
        elif attr == u"＿誠実":
            self.brave += 0.5
            self.trickish -= 0.5
        elif attr == u"＿不実":
            self.brave -= 0.5
            self.trickish += 0.5
        elif attr == u"＿冷静沈着":
            self.agl -= 1
            self.int += 1
            self.cautious += 0.5
            self.trickish += 0.5
        elif attr == u"＿猪突猛進":
            self.agl += 1
            self.min -= 1
            self.cautious -= 0.5
        elif attr == u"＿貪欲":
            self.vit += 1
            self.min -= 1
            self.aggressive += 0.5
            self.brave -= 0.5
            self.cautious -= 0.5
        elif attr == u"＿無欲":
            self.aggressive -= 0.5
        elif attr == u"＿献身的":
            self.vit -= 1
            self.min += 1
            self.aggressive -= 0.5
        elif attr == u"＿利己的":
            self.dex -= 1
            self.agl += 1
            self.aggressive += 0.5
            self.cheerful -= 0.5
            self.trickish += 0.5
        elif attr == u"＿秩序派":
            self.aggressive += 0.5
            self.trickish -= 0.5
        elif attr == u"＿混沌派":
            self.str += 1
            self.min -= 1
            self.aggressive += 0.5
            self.trickish += 0.5
        elif attr == u"＿進取派":
            self.agl += 1
            self.vit -= 1
            self.brave += 0.5
            self.cautious -= 0.5
        elif attr == u"＿保守派":
            self.str -= 1
            self.min += 1
            self.aggressive -= 0.5
            self.cautious += 0.5
        elif attr == u"＿神経質":
            self.agl += 1
            self.str -= 1
            self.cheerful -= 0.5
            self.cautious += 0.5
        elif attr == u"＿鈍感":
            self.int -= 1
            self.vit += 1
        elif attr == u"＿好奇心旺盛":
            self.dex += 1
            self.vit -= 1
        elif attr == u"＿無頓着":
            self.agl -= 1
            self.min += 1
            self.cheerful -= 0.5
        elif attr == u"＿過激":
            self.str += 1
            self.vit -= 1
            self.aggressive += 0.5
            self.cautious -= 0.5
        elif attr == u"＿穏健":
            self.aggressive -= 0.5
            self.cautious += 0.5
        elif attr == u"＿楽観的":
            self.dex += 1
            self.agl -= 1
            self.brave += 0.5
            self.cautious -= 0.5
        elif attr == u"＿悲観的":
            self.int += 1
            self.min -= 1
            self.brave -= 0.5
            self.cautious += 0.5
        elif attr == u"＿勤勉":
            self.dex -= 1
            self.vit += 1
        elif attr == u"＿遊び人":
            self.dex += 1
            self.int -= 1
            self.cheerful += 0.5
            self.trickish += 0.5
        elif attr == u"＿陽気":
            self.cheerful += 0.5
        elif attr == u"＿内気":
            self.brave -= 0.5
        elif attr == u"＿派手":
            self.agl += 1
            self.int -= 1
            self.cheerful += 0.5
            self.cautious -= 0.5
        elif attr == u"＿地味":
            self.str -= 1
            self.vit += 1
            self.brave -= 0.5
        elif attr == u"＿高慢":
            self.dex -= 1
            self.min += 1
            self.aggressive += 0.5
            self.cheerful -= 0.5
        elif attr == u"＿謙虚":
            self.dex -= 1
            self.int += 1
            self.cautious += 0.5
        elif attr == u"＿上品":
            self.int += 1
            self.str -= 1
            self.aggressive -= 0.5
            self.cheerful += 0.5
        elif attr == u"＿粗野":
            self.int -= 1
            self.str += 1
            self.aggressive += 0.5
            self.cheerful -= 0.5
        elif attr == u"＿武骨":
            self.dex -= 1
            self.str += 1
            self.cheerful -= 0.5
            self.brave += 0.5
        elif attr == u"＿繊細":
            self.dex += 1
            self.str -= 1
            self.brave -= 0.5
            self.cautious += 0.5
        elif attr == u"＿硬派":
            self.agl -= 1
            self.str += 1
            self.brave += 0.5
            self.trickish -= 0.5
        elif attr == u"＿軟派":
            self.dex += 1
            self.min -= 1
            self.cheerful += 0.5
            self.brave -= 0.5
        elif attr == u"＿お人好し":
            self.cheerful += 0.5
            self.trickish -= 0.5
        elif attr == u"＿ひねくれ者":
            self.cheerful -= 0.5
        elif attr == u"＿名誉こそ命":
            self.brave += 0.5
            self.cautious -= 0.5
            self.trickish -= 0.5
        elif attr == u"＿愛に生きる":
            self.aggressive -= 0.5
        else:
            return

        self.set_coupon(attr, 0)

    def set_desc(self, talent, attrs):
        seq = [u"　" * 8 + talent[1:] + "\n\n"]

        for index, attr in enumerate(attrs):
            s = attr[1:]
            n = index % 3 if index else 0

            if n == 2:
                s += "\n"
            else:
                s += u"　" * (7 - len(s))

            seq.append(s)

        self.description = cw.util.encodewrap("".join(seq))

    def set_specialcoupon(self):
        self.set_coupon(u"＠レベル原点", self.level)
        self.set_coupon(u"＠ＥＰ", 0)
        self.set_coupon(u"＠Ｇ" + self.gene.get_str(), 0)

    def set_life(self):
        self.life = (self.vit / 2 + 4) * (self.level + 1) + self.min / 2
        self.maxlife = self.life

    def set_wrapability(self):
        """
        能力値の切り上げ・切り捨て。
        """
        self.dex = cw.util.numwrap(self.dex, 1, self.maxdex)
        self.agl = cw.util.numwrap(self.agl, 1, self.maxagl)
        self.int = cw.util.numwrap(self.int, 1, self.maxint)
        self.str = cw.util.numwrap(self.str, 1, self.maxstr)
        self.vit = cw.util.numwrap(self.vit, 1, self.maxvit)
        self.min = cw.util.numwrap(self.min, 1, self.maxmin)
        self.aggressive = cw.util.numwrap(self.aggressive, -5, 5)
        self.cheerful = cw.util.numwrap(self.cheerful, -5, 5)
        self.brave = cw.util.numwrap(self.brave, -5, 5)
        self.cautious = cw.util.numwrap(self.cautious, -5, 5)
        self.trickish = cw.util.numwrap(self.trickish, -5, 5)
        self.avoid = cw.util.numwrap(self.avoid, -10, 10)
        self.resist = cw.util.numwrap(self.resist, -10, 10)
        self.defense = cw.util.numwrap(self.defense, -10, 10)

class AdventurerCreater(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"冒険者の登録",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.header = None
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), u"中止")
        self.postbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), u"登録")
        self.nextbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), u"次へ>>")
        self.prevbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1,
                                                            (85, 24), u"<<戻る")
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
            cw.cwpy.sounds[u"システム・クリック"].play()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)
            return

        cw.cwpy.sounds[u"システム・シグナル"].play()
        s = u"キャラクターを放棄します\nよろしいですか？"
        dlg = cw.dialog.message.YesNoMessage(self, u"メッセージ", s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def OnClickNextBtn(self, event):
        nextpage = self.page.get_next()

        if nextpage:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            self.page.Freeze()
            self.page = nextpage
            self.page.Thaw()
            self.enable_btn()

    def OnClickPrevBtn(self, event):
        prevpage = self.page.get_prev()

        if prevpage:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            self.page.Freeze()
            self.page = prevpage
            self.page.Thaw()
            self.enable_btn()

    def OnClickPostBtn(self, event):
        cw.cwpy.sounds[u"システム・シグナル"].play()
        s = u"%sを登録します。\nよろしいですか？" % (self.page1.name)
        dlg = cw.dialog.message.YesNoMessage(self, u"メッセージ", s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            self.create_adventurer()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

        dlg.Destroy()

    def create_adventurer(self):
        data = AdventurerData()
        s = self.page1.name
        data.set_name(s)
        s = self.page1.age
        data.set_age(s)
        s = self.page1.sex
        data.set_sex(s)
        s = self.page1.imgpath
        data.set_image(s)
        race = self.page2.get_race()
        data.set_race(race)
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
        data.set_wrapability()
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
            rect, method = value

            if rect.collidepoint(mousepos):
                method(key)

    def draw_clickabletext(self, dc, s, pos, name, method, setname=None):
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
            self.clickables[name] = pygame.Rect(pos, size), method

    def draw_clickablebmp(self, dc, bmp, pos, name, method, mask=True):
        size = bmp.GetSize()
        dc.DrawBitmap(bmp, pos[0], pos[1], True)

        if not name in self.clickables:
            # クリックしにくいのでサイズ拡大
            size = size[0] + 20, size[1] + 20
            pos = pos[0] - 10, pos[1] - 10
            self.clickables[name] = pygame.Rect(pos, size), method

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
        self.sex = u"＿♂"
        self.age = u"＿若者"
        self.imgpath = ""
        self.set_imgpaths()
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
        s = "Welcome to Adventurer's Inn."
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # Name
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = "Name"
        dc.DrawText(s, 160, 72)
        # Sex
        s = "Sex"
        dc.DrawText(s, 85, 125)
        # Age
        s = "Age"
        dc.DrawText(s, 85, 175)
        # Male
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=9)
        dc.SetFont(font)
        s = "Male"
        pos = (90, 145)
        self.draw_clickabletext(dc, s, pos, u"＿♂", self.set_sex, self.sex)
        # Female
        s = "Female"
        pos = (155, 145)
        self.draw_clickabletext(dc, s, pos, u"＿♀", self.set_sex, self.sex)
        # Child
        s = "Child"
        pos = (90, 195)
        self.draw_clickabletext(dc, s, pos, u"＿子供", self.set_age, self.age)
        # Adult
        s = "Adult"
        pos = (90, 215)
        self.draw_clickabletext(dc, s, pos, u"＿大人", self.set_age, self.age)
        # Young
        s = "Young"
        pos = (155, 195)
        self.draw_clickabletext(dc, s, pos, u"＿若者", self.set_age, self.age)
        # Old
        s = "Old"
        pos = (155, 215)
        self.draw_clickabletext(dc, s, pos, u"＿老人", self.set_age, self.age)
        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (250, 170)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (365, 170)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg)
        # image
        bmp = cw.util.load_wxbmp(self.imgpath, True)
        dc.DrawBitmap(bmp, 275, 130, True)

    def set_sex(self, name):
        if not self.sex == name:
            cw.cwpy.sounds[u"システム・クリック"].play()
            self.sex = name
            self.set_imgpaths()
            self.draw(True)

    def set_age(self, name):
        if not self.age == name:
            cw.cwpy.sounds[u"システム・クリック"].play()
            self.age = name
            self.set_imgpaths()
            self.draw(True)

    def set_nextimg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.imgpaths.index(self.imgpath) + 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_previmg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.imgpaths.index(self.imgpath) - 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_imgpaths(self):
        if self.sex == u"＿♂":
            sex = "Male"
        else:
            sex = "Female"

        if self.age == u"＿子供":
            age = "CHD"
        elif self.age == u"＿若者":
            age = "YNG"
        elif self.age == u"＿大人":
            age = "ADT"
        else:
            age = "OLD"

        dpath = sex + "-" + age
        dpath = cw.util.join_paths(cw.cwpy.skindir, u"Face", dpath)
        self.imgpaths = []

        for name in os.listdir(dpath):
            path = cw.util.join_paths(dpath, name)

            if os.path.isfile(path):
                self.imgpaths.append(path)

        if self.imgpaths:
            self.imgpath = self.imgpaths[0]

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
        s = s = u"種 族"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 新規冒険者の種族を決定します。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = u"新規冒険者の種族を決定します。"
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
        s = s = u"血 縁"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 親となる条件を満たしている冒険者が宿にいます。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = u"親となる条件を満たしている冒険者が宿にいます。"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 60)
        # Father
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, style=wx.ITALIC)
        font.SetUnderlined(True)
        dc.SetFont(font)
        s = "Father"
        dc.DrawText(s, 110, 92)
        # Mother
        s = "Mother"
        dc.DrawText(s, 285, 92)
        # PrevFather
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (70, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevFather", self.set_prevfather)
        # NextFather
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (190, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextFather", self.set_nextfather)
        # PrevMother
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (250, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevMother", self.set_prevmother)
        # NextMother
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (370, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextMother", self.set_nextmother)

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
            s = u"一般男性"

        cw.util.draw_center(dc, s, (140, 220))

        # 母親名前
        if self.mother:
            s = self.mother.name
        else:
            s = u"一般女性"

        cw.util.draw_center(dc, s, (315, 220))
        # 父親消費EP
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)

        if self.father:
            if self.father.album:
                ep = 10
            elif self.father.age == u"＿若者":
                ep = 40
            elif self.father.age == u"＿大人":
                ep = 30
            elif self.father.age == u"＿老人":
                ep = 20

            s = u"消費EP:%d (残%d)" % (ep, self.father.ep - ep)
            cw.util.draw_center(dc, s, (140, 240))

        # 母親消費EP
        if self.mother:
            if self.mother.album:
                ep = 10
            elif self.mother.age == u"＿若者":
                ep = 40
            elif self.mother.age == u"＿大人":
                ep = 30
            elif self.mother.age == u"＿老人":
                ep = 20

            s = u"消費EP:%d (残%d)" % (ep, self.mother.ep - ep)
            cw.util.draw_center(dc, s, (315, 240))

    def set_nextfather(self, name):
        if self.fathers:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.fathers.index(self.father) + 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_prevfather(self, name):
        if self.fathers:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.fathers.index(self.father) - 1

            try:
                self.father = self.fathers[index]
            except:
                self.father = self.fathers[0]

            self.draw(True)

    def set_nextmother(self, name):
        if self.mothers:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.mothers.index(self.mother) + 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def set_prevmother(self, name):
        if self.mothers:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.mothers.index(self.mother) - 1

            try:
                self.mother = self.mothers[index]
            except:
                self.mother = self.mothers[0]

            self.draw(True)

    def set_parents(self):
        def append_header(self, header):
            if header.sex == u"＿♂":
                self.fathers.append(header)
            else:
                self.mothers.append(header)

        self.fathers = [None]
        self.mothers = [None]

        if not cw.cwpy.ydata:
            return

        for header in cw.cwpy.ydata.standbys:
            if header.age == u"＿若者" and header.ep >= 40:
                append_header(self, header)
            elif header.age == u"＿大人" and header.ep >= 30:
                append_header(self, header)
            elif header.age == u"＿老人" and header.ep >= 20:
                append_header(self, header)

        for header in cw.cwpy.ydata.album:
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
        self.talent = u"＿標準型"
        self._bind()

    def draw(self, update=False):
        dc = AdventurerCreaterPage.draw(self, update)
        cwidth = self.GetClientSize()[0]
        # 素質
        dc.SetTextForeground(wx.BLACK)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=14, style=wx.ITALIC)
        dc.SetFont(font)
        s = s = u"素 質"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 35)
        # 新規冒険者の傾向を選択して下さい。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = u"新規冒険者の傾向を選択して下さい。"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 60)
        # 標準型解説
        s = u"凡庸なる暮らしの中で培わ\nれた強い意志"
        dc.DrawLabel(s, (68, 110, 145, 35))
        # 勇将型解説
        s = u"攻守のバランスに優れる"
        dc.DrawLabel(s, (68, 165, 145, 35))
        # 知将型解説
        s = u"智に裏付けされた実力"
        dc.DrawLabel(s, (68, 220, 145, 35))
        # 万能型解説
        s = u"あらゆる分野をそつなくこな\nす機敏さ"
        dc.DrawLabel(s, (258, 110, 145, 35))
        # 豪傑型解説
        s = u"腕力、耐久力に優れた生ま\nれながらの戦士"
        dc.DrawLabel(s, (258, 165, 145, 35))
        # 策士型解説
        s = u"類希な知性を持つ天才型"
        dc.DrawLabel(s, (258, 220, 145, 35))
        # 標準型
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)
        s = u"標準型"
        pos = (65, 92)
        self.draw_clickabletext(dc, s, pos, u"＿標準型", self.set_talent, self.talent)
        # 勇将型
        s = u"勇将型"
        pos = (65, 147)
        self.draw_clickabletext(dc, s, pos, u"＿勇将型", self.set_talent, self.talent)
        # 知将型
        s = u"知将型"
        pos = (65, 202)
        self.draw_clickabletext(dc, s, pos, u"＿知将型", self.set_talent, self.talent)
        # 万能型
        s = u"万能型"
        pos = (255, 92)
        self.draw_clickabletext(dc, s, pos, u"＿万能型", self.set_talent, self.talent)
        # 豪傑型
        s = u"豪傑型"
        pos = (255, 147)
        self.draw_clickabletext(dc, s, pos, u"＿豪傑型", self.set_talent, self.talent)
        # 策士型
        s = u"策士型"
        pos = (255, 202)
        self.draw_clickabletext(dc, s, pos, u"＿策士型", self.set_talent, self.talent)

    def set_talent(self, name):
        if not self.talent == name:
            cw.cwpy.sounds[u"システム・クリック"].play()
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
        s = s = u"特 性"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 20)
        # 新規冒険者の生まれや性格などの個性を決定します。
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10, weight=wx.NORMAL)
        dc.SetFont(font)
        s = u"新規冒険者の生まれや性格などの個性を決定します。"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 45)
        # 特性
        colour = wx.Colour(128, 128, 128)
        dc.SetTextForeground(colour)
        font = cw.cwpy.rsrc.get_wxfont("uigothic", size=10)
        dc.SetFont(font)

        seq =  ((u"秀麗", u"醜悪"),
                (u"高貴の出", u"下賎の出"),
                (u"都会育ち", u"田舎育ち"),
                (u"裕福", u"貧乏"),
                (u"厚き信仰", u"不心得者"),
                (u"誠実", u"不実"),
                (u"冷静沈着", u"猪突猛進"),
                (u"貪欲", u"無欲"),
                (u"献身的", u"利己的"),
                (u"秩序派", u"混沌派"),
                (u"進取派", u"保守派"),
                (u"神経質", u"鈍感"),
                (u"好奇心旺盛", u"無頓着"),
                (u"過激", u"穏健"),
                (u"楽観的", u"悲観的"),
                (u"勤勉", u"遊び人"),
                (u"陽気", u"内気"),
                (u"派手", u"地味"),
                (u"高慢", u"謙虚"),
                (u"上品", u"粗野"),
                (u"武骨", u"繊細"),
                (u"硬派", u"軟派"),
                (u"お人好し", u"ひねくれ者"),
                (u"名誉こそ命", u"愛に生きる"))

        for index, coupons in enumerate(seq):
            column = index / 12 if index else 0
            pos = (67 + column * 172, 64 + (index - column * 12) * 16)
            s = coupons[0]
            name = (u"＿" + s, coupons)
            self.draw_clickabletext(dc, s, pos, name, self.set_coupon)
            pos = pos[0] + 86, pos[1]
            s = coupons[1]
            name = (u"＿" + s, coupons)
            self.draw_clickabletext(dc, s, pos, name, self.set_coupon)

    def draw_clickabletext(self, dc, s, pos, name, method, setname=None):
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
            self.clickables[name] = pygame.Rect(pos, size), method

    def set_coupon(self, name):
        name, coupons = name

        if self.couponsdata.get(coupons, "") == name:
            self.couponsdata[coupons] = ""
        else:
            self.couponsdata[coupons] = name

        cw.cwpy.sounds[u"システム・クリック"].play()
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
        wx.Dialog.__init__(self, parent, -1, u"宿の登録", size=(318, 180),
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.SetClientSize((312, 156))
        self.textctrl = wx.TextCtrl(self, size=(175, 24))
        self.textctrl.SetMaxLength(18)
        font = cw.cwpy.rsrc.get_wxfont("mincho", size=12)
        self.textctrl.SetFont(font)
        self.textctrl.SetValue(u"新規宿")
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                            (100, 30), u"登録")
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), u"中止")
        self._do_layout()
        self._bind()

    def create_yado(self):
        yadodir = cw.util.join_paths("Yado", self.textctrl.GetValue())
        os.makedirs(yadodir)
        dnames = ("Adventurer", "Album", "BeastCard", "ItemCard",
                                            "Material", "Party", "SkillCard")

        for dname in dnames:
            path = cw.util.join_paths(yadodir, dname)
            os.makedirs(path)

        cw.xmlcreater.create_environment(yadodir)

    def OnOk(self, event):
        name = self.textctrl.GetValue().strip()

        if not name:
            cw.cwpy.sounds[u"システム・エラー"].play()
            s = u"宿名が入力されていません。"
            dlg = cw.dialog.message.Message(self, u"メッセージ", s)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return
        elif cw.util.check_dischar(name):
            cw.cwpy.sounds[u"システム・エラー"].play()
            s = u"名称に不正な文字が使用されています。\n名前を変更してください。"
            dlg = cw.dialog.message.Message(self, u"メッセージ", s)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return
        elif os.path.isdir(cw.util.join_paths("Yado", name)):
            cw.cwpy.sounds[u"システム・エラー"].play()
            s = u"同名の冒険者の宿が既に存在しています。\n名前を変更してください。"
            dlg = cw.dialog.message.Message(self, u"メッセージ", s)
            cw.cwpy.frame.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        self.create_yado()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"システム・クリック"].play()
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
        s = u"新しい冒険者の宿を登録します。"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, 10)
        font = cw.cwpy.rsrc.get_wxfont("uigothic", weight=wx.NORMAL)
        dc.SetFont(font)
        s = u"登録する冒険者の宿の名称を入力して下さい。"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (csize[0]-w)/2, 30)

    def _bind(self):
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
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"冒険者のデザイン",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        # buttonlist
        self.buttonlist = []

        self.ccard = cw.cwpy.selection

        # toppanel
        self.toppanel = DesignPanel(self)

        # btn
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                            (100, 30), u"決定")
        self.buttonlist.append(self.okbtn)
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        (100, 30), u"中止")
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
        cw.cwpy.sounds[u"システム・収穫"].play()

        cw.animation.animate_sprite(self.ccard, "hide")
        self.ccard.set_name(self.toppanel.namectrl.GetValue())
        self.ccard.cardimg.set_nameimg(self.ccard.get_name())
        self.ccard.set_description(self.toppanel.descctrl.GetValue())
        if self.toppanel.imgpath.startswith(cw.util.join_paths(cw.cwpy.skindir, u"Face")):
            self.ccard.set_image(self.toppanel.imgpath)
            self.ccard.cardimg.set_faceimg(cw.util.join_yadodir(self.ccard.get_imagepath()))
        self.ccard.update_image()
        cw.animation.animate_sprite(self.ccard, "deal")

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"システム・クリック"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

class DesignPanel(AdventurerCreaterPage):
    def __init__(self, parent):
        AdventurerCreaterPage.__init__(self, parent, size=(400, 370), freeze=False)
        self.SetMinSize((400, 370))

        self.ccard = cw.cwpy.selection

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

        self.set_imgpaths()
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
        s = "Resident Registration."
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 15)

        # Name
        s = "Name"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 45)
        # Image
        s = "Image"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 95)
        # Comment
        s = "Comment"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (cwidth - w) / 2, 220)

        # PrevImage
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        pos = (135, 150)
        self.draw_clickablebmp(dc, bmp, pos, "PrevImage", self.set_previmg)
        # NextImage
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        pos = (260, 150)
        self.draw_clickablebmp(dc, bmp, pos, "NextImage", self.set_nextimg)
        # image
        bmp = cw.util.load_wxbmp(self.imgpath, True)
        dc.DrawBitmap(bmp, (cwidth - 74) / 2, 116, True)

    def set_nextimg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.imgpaths.index(self.imgpath) + 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_previmg(self, name):
        if self.imgpaths:
            cw.cwpy.sounds[u"システム・改ページ"].play()
            index = self.imgpaths.index(self.imgpath) - 1

            try:
                self.imgpath = self.imgpaths[index]
            except:
                self.imgpath = self.imgpaths[0]

            self.draw(True)

    def set_imgpaths(self):
        if self.sex == u"＿♂":
            sex = "Male"
        else:
            sex = "Female"

        if self.age == u"＿子供":
            age = "CHD"
        elif self.age == u"＿若者":
            age = "YNG"
        elif self.age == u"＿大人":
            age = "ADT"
        else:
            age = "OLD"

        dpath = sex + "-" + age
        dpath = cw.util.join_paths(cw.cwpy.skindir, u"Face", dpath)
        if self.imgpath == "":
            self.imgpaths = []
        else:
            self.imgpaths = [self.imgpath]

        for name in os.listdir(dpath):
            path = cw.util.join_paths(dpath, name)

            if os.path.isfile(path):
                self.imgpaths.append(path)

        if self.imgpaths:
            self.imgpath = self.imgpaths[0]

def main():
    pass

if __name__ == "__main__":
    main()
