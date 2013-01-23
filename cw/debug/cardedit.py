#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx
import wx.lib.mixins.listctrl
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
        self.scdata = cw.cwpy.sdata
        if self.scdata:
            self.scpath = ""
        else:
            self.scpath = self.scdata.fpath
            if os.path.isdir(self.scpath):
                self.scpath = cw.util.join_paths(self.scpath, "Summary.wsm")

        self.list = []

        self.cardsbox = wx.StaticBox(self, -1, u"カードの選択")
        self.methodbox = wx.StaticBox(self, -1, u"照合方法")
        self.targetsbox = wx.StaticBox(self, -1, u"処理対象")

        self.scenario = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"(シナリオ未選択)")

        self.imglist = wx.ImageList(14, 14)
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS8"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS9"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS10"])

        self.cards = CheckableListCtrl(self, -1, size=(200, 250),
            style=wx.LC_REPORT)
        self.cards.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.cards.InsertColumn(0, "ID")
        self.cards.InsertColumn(1, u"カード名")
        self.cards.InsertColumn(2, u"解説")
        self.cards.SetColumnWidth(0, 40)
        self.cards.SetColumnWidth(1, 80)
        self.cards.SetColumnWidth(2, 110)

        self.dtlbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"情報")
        self.findbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"検索")
        self.dealbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"配付")
        self.updbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"更新")
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"除去")

        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), name=u"閉じる")

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

        self.mname.SetValue(True)
        self.mdesc.SetValue(True)

        self._bind()
        self._do_layout()

        self._update_cards()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnScenario, self.scenario);
        self.Bind(wx.EVT_BUTTON, self.OnDetailBtn, self.dtlbtn);
        self.Bind(wx.EVT_BUTTON, self.OnFindBtn, self.findbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDealBtn, self.dealbtn);
        self.Bind(wx.EVT_BUTTON, self.OnUpdateBtn, self.updbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDeleteBtn, self.delbtn);

    def _do_layout(self):
        sizer_left = wx.StaticBoxSizer(self.cardsbox, wx.VERTICAL)
        sizer_left.Add(self.scenario, 0, wx.EXPAND|wx.ALL, 5)
        sizer_left.Add(self.cards, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_method = wx.StaticBoxSizer(self.methodbox, wx.HORIZONTAL)
        sizer_checks = wx.BoxSizer(wx.HORIZONTAL)
        sizer_checks.Add(self.mname, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mdesc, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mscenario, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mauthor, 1)
        sizer_method.Add(sizer_checks, 1, wx.EXPAND|wx.ALL, 5)

        sizer_targets = wx.StaticBoxSizer(self.targetsbox, wx.VERTICAL)
        sizer_targets.Add(self.targets, 1, wx.EXPAND|wx.ALL, 5)

        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        sizer_middle.Add(sizer_targets, 1, wx.EXPAND|wx.BOTTOM, 5)
        sizer_middle.Add(sizer_method, 0, wx.EXPAND)

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
        sizer.Add(sizer_right, 0, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnScenario(self, event):
        if self.scpath:
            dpath = os.path.dirname(self.scpath)
            fpath = os.path.basename(self.scpath)
        else:
            dpath = ""
            fpath = ""
        dlg = wx.FileDialog(self, u"シナリオの選択", dpath, fpath,
                            "シナリオファイル (*.wsn; *.wsm; *.zip; *.cab)|*.wsn;*.wsm;*.zip;*.cab",
                            wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            fpath = dlg.GetPath()

            scdata = get_scenario(fpath)
            if not scdata:
                return

            self.scpath = fpath
            self.scdata = scdata
            self._update_cards()

    def _update_cards(self):
        self.cards.DeleteAllItems()
        self.list = []

        if not self.scdata:
            self.scenario.SetLabel(u"(シナリオ未選択)")
            return

        self.scenario.SetLabel(self.scdata.name)

        def append_cards(table, image):
            for id in table.keys():
                index = self.cards.GetItemCount()
                data = cw.data.xml2element(table[id][1])
                header = cw.header.CardHeader(carddata=data)
                self.cards.InsertStringItem(index, str(header.id))
                self.cards.SetStringItem(index, 1, header.name)
                self.cards.SetStringItem(index, 2, header.desc.replace("\\n", ""))
                self.cards.SetItemImage(index, image)
                self.list.append(header)

        append_cards(self.scdata.skills, self.imgidx_skill)
        append_cards(self.scdata.items, self.imgidx_item)
        append_cards(self.scdata.beasts, self.imgidx_beast)

    def OnAddBtn(self, event):
        pass # TODO

    def OnRemoveBtn(self, event):
        pass # TODO

    def OnDetailBtn(self, event):
        pass # TODO

    def OnFindBtn(self, event):
        pass # TODO

    def OnDealBtn(self, event):
        pass # TODO

    def OnUpdateBtn(self, event):
        pass # TODO

    def OnDeleteBtn(self, event):
        pass # TODO

def get_scenario(fpath):
    lfpath = fpath.lower()
    if lfpath.endswith(".wsm"):
        t = cw.scenariodb.read_summary(os.path.dirname(fpath))
    else:
        t = cw.scenariodb.read_summary(fpath)
    if not t:
        return None

    header = cw.header.ScenarioHeader(t)
    return cw.data.ScenarioData(header)

class CheckableListCtrl(wx.ListCtrl, wx.lib.mixins.listctrl.CheckListCtrlMixin):
    def __init__(self, parent, id, size, style):
        wx.ListCtrl.__init__(self, parent, id, size=size, style=style)
        wx.lib.mixins.listctrl.CheckListCtrlMixin.__init__(self)
