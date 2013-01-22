#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wx.lib.agw.customtreectrl

import cw


#-------------------------------------------------------------------------------
#  手札カード情報編集ダイアログ
#-------------------------------------------------------------------------------

class CardEditDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"手札カードの編集",
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.party = cw.cwpy.ydata.party

        self.scenariobox = wx.StaticBox(self, -1, u"シナリオの選択")
        self.cardsbox = wx.StaticBox(self, -1, u"カードの選択")
        self.selcardsbox = wx.StaticBox(self, -1, u"選択済みカード")
        self.methodbox = wx.StaticBox(self, -1, u"照合方法")
        self.targetsbox = wx.StaticBox(self, -1, u"処理対象")

        self.scenario = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"(未選択)")

        self.imglist = wx.ImageList(14, 14)
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS8"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS9"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS10"])

        self.cards = wx.ListCtrl(self, -1, size=(200, 200),
            style=wx.LC_REPORT|wx.LC_VIRTUAL)
        self.cards.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.cards.InsertColumn(0, "ID")
        self.cards.InsertColumn(1, u"カード名")
        self.cards.InsertColumn(2, u"解説")
        self.cards.SetColumnWidth(0, 30)
        self.cards.SetColumnWidth(1, 80)
        self.cards.SetColumnWidth(2, 150)

        self.selcards = wx.ListCtrl(self, -1, size=(200, -1),
            style=wx.LC_REPORT|wx.LC_VIRTUAL)
        self.selcards.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.selcards.InsertColumn(0, u"カード名")
        self.selcards.InsertColumn(1, u"所属シナリオ")
        self.selcards.SetColumnWidth(0, 80)
        self.selcards.SetColumnWidth(1, 120)

        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"追加")
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"除去")

        self.dtlbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"情報")
        self.findbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"検索")
        self.dealbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"配付")
        self.updbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"更新")
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"除去")

        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), name=u"閉じる")

        self.mkind = wx.CheckBox(self, -1, u"種別")
        self.mname = wx.CheckBox(self, -1, u"カード名")
        self.mdesc = wx.CheckBox(self, -1, u"解説")
        self.mscenario = wx.CheckBox(self, -1, u"シナリオ")
        self.mauthor = wx.CheckBox(self, -1, u"作者")

        self.timglist = wx.ImageList(16, 16)
        self.timgidx_storehouse = self.timglist.Add(cw.cwpy.rsrc.buttons["DECK"])
        self.timgidx_backpack = self.timglist.Add(cw.cwpy.rsrc.buttons["SACK"])
        self.timgidx_party = self.timglist.Add(cw.cwpy.rsrc.debugs["MEMBER"])
        self.timgidx_yado = self.timglist.Add(cw.cwpy.rsrc.debugs["YADO"])
        self.timgidx_member = self.timglist.Add(cw.cwpy.rsrc.buttons["CAST"])

        self.targets = wx.lib.agw.customtreectrl.CustomTreeCtrl(self, -1, size=(200, -1),
            style=wx.BORDER,
            agwStyle=wx.TR_NO_BUTTONS|wx.TR_SINGLE|wx.TR_HIDE_ROOT|\
            wx.lib.agw.customtreectrl.TR_AUTO_CHECK_CHILD|\
            wx.lib.agw.customtreectrl.TR_AUTO_CHECK_PARENT)
        self.targets.SetImageList(self.timglist)

        rid = self.targets.AddRoot(u"")

        if self.party:
            self.root_party = self.targets.AppendItem(rid, self.party.name, 1, image=self.timgidx_party)
            self.root_backpack = self.targets.AppendItem(rid, u"荷物袋", 1, image=self.timgidx_backpack)
        self.root_storehouse = self.targets.AppendItem(rid, u"カード置場", 1, image=self.timgidx_storehouse)
        self.root_yado = self.targets.AppendItem(rid, u"待機中のメンバ", 1, image=self.timgidx_yado)

        self._bind()
        self._do_layout()

    def _bind(self):
        pass

    def _do_layout(self):
        sizer_scenario = wx.StaticBoxSizer(self.scenariobox, wx.HORIZONTAL)
        sizer_scenario.Add(self.scenario, 1, wx.ALL, 5)

        sizer_cards = wx.StaticBoxSizer(self.cardsbox, wx.VERTICAL)
        sizer_cards.Add(self.cards, 1, wx.EXPAND|wx.ALL, 5)
        sizer_cards.Add(self.addbtn, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(sizer_scenario, 0, wx.EXPAND|wx.BOTTOM, 5)
        sizer_left.Add(sizer_cards, 1, wx.EXPAND)

        sizer_selcards = wx.StaticBoxSizer(self.selcardsbox, wx.VERTICAL)
        sizer_selcards.Add(self.selcards, 1, wx.EXPAND|wx.ALL, 5)
        sizer_selcards.Add(self.rmvbtn, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_method = wx.StaticBoxSizer(self.methodbox, wx.HORIZONTAL)
        sizer_checks = wx.GridSizer(2, 3)
        sizer_checks.Add(self.mkind, 1, wx.RIGHT|wx.BOTTOM, 5)
        sizer_checks.Add(self.mname, 1, wx.RIGHT|wx.BOTTOM, 5)
        sizer_checks.Add(self.mdesc, 1, wx.BOTTOM, 5)
        sizer_checks.Add(self.mscenario, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mauthor, 1, wx.RIGHT, 5)
        sizer_method.Add(sizer_checks, 1, wx.EXPAND|wx.ALL, 5)

        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        sizer_middle.Add(sizer_selcards, 1, wx.EXPAND|wx.BOTTOM, 5)
        sizer_middle.Add(sizer_method, 0, wx.EXPAND)

        sizer_middle2 = wx.StaticBoxSizer(self.targetsbox, wx.VERTICAL)
        sizer_middle2.Add(self.targets, 1, wx.EXPAND|wx.ALL, 5)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.dtlbtn, 0, wx.EXPAND)
        sizer_right.Add(self.findbtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.Add(self.dealbtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.Add(self.updbtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.Add(self.delbtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.closebtn, 0, wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=5)
        sizer.Add(sizer_middle, 1, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)
        sizer.Add(sizer_middle2, 1, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)
        sizer.Add(sizer_right, 0, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()
