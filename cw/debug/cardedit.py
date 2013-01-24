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
        self.datalist = []
        self.target_table = {}

        self.cardsbox = wx.StaticBox(self, -1, u"カードの選択")
        self.dealtargbox = wx.StaticBox(self, -1, u"配付先")
        self.methodbox = wx.StaticBox(self, -1, u"照合方法")
        self.targetsbox = wx.StaticBox(self, -1, u"処理対象")

        self.scenario = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"(シナリオ未選択)")

        self.imglist = wx.ImageList(14, 14)
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS8"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS9"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS10"])

        self.cards = wx.ListCtrl(self, -1, size=(200, 250),
            style=wx.LC_REPORT)
        self.cards.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.cards.InsertColumn(0, "ID")
        self.cards.InsertColumn(1, u"カード名")
        self.cards.InsertColumn(2, u"解説")
        self.cards.SetColumnWidth(0, 40)
        self.cards.SetColumnWidth(1, 85)
        self.cards.SetColumnWidth(2, 110)

        self.dealtarg = wx.combo.BitmapComboBox(self, -1, style=wx.CB_READONLY)
        bmp = cw.cwpy.rsrc.buttons["SACK"]
        self.dealtarg.Append(u"荷物袋", bmp)
        bmp = cw.cwpy.rsrc.buttons["CAST"]
        for member in cw.cwpy.get_pcards():
            self.dealtarg.Append(member.name, bmp)
        self.dealtarg.SetSelection(0)

        self.dtlbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"情報")
        self.dealbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"配付")
        self.findbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"検索")
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
        self.status = wx.StaticText(self, -1, label=u"対象はありません", style=wx.ST_NO_AUTORESIZE)

        self.root = self.targets.AddRoot(u"")

        self.mname.SetValue(True)
        self.mdesc.SetValue(True)

        self._bind()
        self._do_layout()

        self._update_cards()
        self._update_enable()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnScenario, self.scenario);
        self.Bind(wx.EVT_BUTTON, self.OnDetailBtn, self.dtlbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDealBtn, self.dealbtn);
        self.Bind(wx.EVT_BUTTON, self.OnFindBtn, self.findbtn);
        self.Bind(wx.EVT_BUTTON, self.OnUpdateBtn, self.updbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDeleteBtn, self.delbtn);
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnCardSelected, self.cards)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnCardSelected, self.cards)

    def _do_layout(self):
        sizer_cards = wx.StaticBoxSizer(self.cardsbox, wx.VERTICAL)
        sizer_cards.Add(self.scenario, 0, wx.EXPAND|wx.ALL, 5)
        sizer_cards.Add(self.cards, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_dealtarg = wx.StaticBoxSizer(self.dealtargbox, wx.HORIZONTAL)
        sizer_dealtarg.Add(self.dealtarg, 1, wx.ALL, 5)

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(sizer_cards, 1, wx.EXPAND|wx.ALL, 5)
        sizer_left.Add(sizer_dealtarg, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_method = wx.StaticBoxSizer(self.methodbox, wx.HORIZONTAL)
        sizer_checks = wx.BoxSizer(wx.HORIZONTAL)
        sizer_checks.Add(self.mname, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mdesc, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mscenario, 1, wx.RIGHT, 5)
        sizer_checks.Add(self.mauthor, 1)
        sizer_method.Add(sizer_checks, 1, wx.EXPAND|wx.ALL, 5)

        sizer_targets = wx.StaticBoxSizer(self.targetsbox, wx.VERTICAL)
        sizer_targets.Add(self.targets, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, 5)
        sizer_targets.Add(self.status, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        sizer_middle.Add(sizer_targets, 1, wx.EXPAND|wx.BOTTOM, 5)
        sizer_middle.Add(sizer_method, 0, wx.EXPAND)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.dtlbtn, 0, wx.EXPAND)
        sizer_right.Add(self.dealbtn, 0, wx.EXPAND|wx.TOP, border=5)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.findbtn, 0, wx.EXPAND|wx.TOP, border=5)
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

    def OnDetailBtn(self, event):
        if 0 == self.cards.GetItemCount():
            return
        index = self.cards.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index <= -1:
            index = 0
        for i, header in enumerate(self.list):
            header.negaflag = (i == index)
        self.draw(True)
        dlg = cw.dialog.cardinfo.YadoCardInfo(self, self.list, self.list[index])
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def draw(self, update):
        for i, header in enumerate(self.list):
            if header.negaflag:
                self.cards.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            else:
                self.cards.SetItemState(i, 0, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)

    def OnDealBtn(self, event):
        cindex = self.dealtarg.GetSelection()
        if cindex == 0:
            target = self.party.backpack
        else:
            target = self.party.members[cindex-1]

        index = -1
        count = 0
        while True:
            index = self.cards.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            cw.content.get_card(self.datalist[index], target)
            count += 1

        if 0 < count:
            cw.cwpy.sounds["harvest"].play()

    def OnFindBtn(self, event):
        self.targets.DeleteChildren(self.root)
        roots = {}
        items = {}
        self.target_table = {}

        cards = self._selected_cards()

        def get_item(table, key, parent, name, image):
            if key in table:
                return table[key]
            else:
                item = self.targets.AppendItem(parent, name, 1, image=image)
                item.Check(True)
                table[key] = item
                if not parent is self.root:
                    self.targets.Expand(parent)
                return item

        def add_target(item, matcher, owner, data):
            item.Check(True)
            self.targets.Expand(item.GetParent())
            if matcher in self.target_table:
                self.target_table[matcher].append((item, owner, data))
            else:
                list = [(item, owner, data)]
                self.target_table[matcher] = list

        if cw.cwpy.ydata.party:
            for member in cw.cwpy.get_pcards():
                self.status.SetLabel(u"%sの手札カードを検索中..." % (member.name))
                for elements in [member.data.getfind("SkillCards"), member.data.getfind("ItemCards"), member.data.getfind("BeastCards")]:
                    for data in elements:
                        matcher = self._get_matcher(data)
                        if matcher in cards:
                            image = self.timgidx_party
                            name = cw.cwpy.ydata.party.name
                            root = get_item(roots, cw.cwpy.ydata.party, self.root, name, image)

                            image = self.timgidx_member
                            name = member.name
                            item = get_item(items, member, root, name, image)

                            image = self._get_imgidx(data)
                            name = data.gettext("Property/Name")
                            item = self.targets.AppendItem(item, name, 1, image=image)
                            add_target(item, matcher, member, data)

            for header in cw.cwpy.ydata.party.backpack:
                self.status.SetLabel(u"荷物袋を検索中...")
                matcher = self._get_matcher(header)
                if matcher in cards:
                    image = self.timgidx_backpack
                    name = u"荷物袋"
                    root = get_item(roots, "BACKPACK", self.root, name, image)

                    image = self._get_imgidx(header)
                    item = self.targets.AppendItem(root, header.name, 1, image=image)
                    add_target(item, matcher, cw.cwpy.ydata.party.backpack, header)

        for header in cw.cwpy.ydata.storehouse:
            self.status.SetLabel(u"カード置場を検索中...")
            matcher = self._get_matcher(header)
            if matcher in cards:
                image = self.timgidx_storehouse
                name = u"カード置場"
                root = get_item(roots, "STOREHOUSE", self.root, name, image)

                image = self._get_imgidx(header)
                item = self.targets.AppendItem(root, header.name, 1, image=image)
                add_target(item, matcher, cw.cwpy.ydata.storehouse, header)

        for header in cw.cwpy.ydata.standbys:
            member = cw.data.yadoxml2etree(header.fpath)
            self.status.SetLabel(u"%sの手札カードを検索中..." % (header.name))
            for elements in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                for data in elements:
                    matcher = self._get_matcher(data)
                    if matcher in cards:
                        image = self.timgidx_yado
                        name = u"待機中のメンバー"
                        root = get_item(roots, "STANDBYS", self.root, name, image)

                        image = self.timgidx_member
                        name = header.name
                        item = get_item(items, header, root, name, image)

                        image = self._get_imgidx(data)
                        name = data.gettext("Property/Name")
                        item = self.targets.AppendItem(item, name, 1, image=image)
                        add_target(item, matcher, member, data)

        for partyheader in cw.cwpy.ydata.partys:
            party = cw.data.Party(partyheader.fpath)
            self.status.SetLabel(u"%sの手札カードを検索中..." % (party.name))
            for index, member in enumerate(party.members):
                for elements in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                    for data in elements:
                        matcher = self._get_matcher(data)
                        if matcher in cards:
                            image = self.timgidx_party
                            name = partyheader.name
                            root = get_item(roots, (partyheader, 0), self.root, name, image)

                            image = self.timgidx_member
                            name = member.gettext("Property/Name")
                            item = get_item(items, (partyheader, index), root, name, image)

                            image = self._get_imgidx(data)
                            name = data.gettext("Property/Name")
                            item = self.targets.AppendItem(item, name, 1, image=image)
                            add_target(item, matcher, member, data)

            self.status.SetLabel(u"%sの荷物袋を検索中..." % (party.name))
            for data in party.backpack:
                matcher = self._get_matcher(data)
                if matcher in cards:
                    image = self.timgidx_backpack
                    name = u"%sの荷物袋" % (partyheader.name)
                    item = get_item(roots, (partyheader, -1), self.root, name, image)

                    image = self._get_imgidx(data)
                    name = data.gettext("Property/Name")
                    item = self.targets.AppendItem(item, name, 1, image=image)
                    add_target(item, matcher, backpack, data)

        count = 0
        for array in self.target_table.values():
            count += len(array)
        self.status.SetLabel(u"%s件のカードが見つかりました。" % (count))

        cw.cwpy.sounds["signal"].play()

    def OnUpdateBtn(self, event):
        pass # TODO

    def OnDeleteBtn(self, event):
        pass # TODO

    def OnCardSelected(self, event):
        self._update_enable()

    def _get_matcher(self, data):
        name = ""
        desc = ""
        scenario = ""
        author = ""

        if isinstance(data, cw.header.CardHeader):
            header = data
            if self.mname.GetValue():
                name = header.name
            if self.mdesc.GetValue():
                desc = header.desc
            if self.mscenario.GetValue():
                scenario = header.scenario
            if self.mauthor.GetValue():
                author = header.author
        else:
            e = data.find("Property")
            if self.mname.GetValue():
                name = e.gettext("Name", "")
            if self.mdesc.GetValue():
                desc = e.gettext("Description", "")
            if self.mscenario.GetValue():
                scenario = e.gettext("Scenario", "")
            if self.mauthor.GetValue():
                author = e.gettext("Author", "")

        return (name, desc, scenario, author)

    def _get_imgidx(self, data):
        type = ""
        if isinstance(data, cw.header.CardHeader):
            header = data
            type = header.type
        else:
            type = data.tag

        if type == "SkillCard":
            return self.imgidx_skill
        elif type == "ItemCard":
            return self.imgidx_item
        elif type == "BeastCard":
            return self.imgidx_beast

        return None

    def _selected_cards(self):
        cards = set()
        index = -1
        while (True):
            index = self.cards.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            cards.add(self._get_matcher(self.list[index]))

        return cards

    def _update_cards(self):
        self.cards.DeleteAllItems()
        self.list = []
        self.datalist = []

        if not self.scdata:
            self.scenario.SetLabel(u"(シナリオ未選択)")
            return

        self.scenario.SetLabel(self.scdata.name)

        def append_cards(table, image):
            for id in table.keys():
                index = self.cards.GetItemCount()
                data = cw.data.xml2etree(table[id][1])
                header = cw.header.CardHeader(data=data.find("Property"))
                header.negaflag = False
                self.cards.InsertStringItem(index, str(header.id))
                self.cards.SetStringItem(index, 1, header.name)
                self.cards.SetStringItem(index, 2, header.desc.replace("\\n", ""))
                self.cards.SetItemImage(index, image, image)
                self.list.append(header)
                self.datalist.append(data)

        append_cards(self.scdata.skills, self.imgidx_skill)
        append_cards(self.scdata.items, self.imgidx_item)
        append_cards(self.scdata.beasts, self.imgidx_beast)

    def _update_enable(self):
        selected = -1 < self.cards.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        hascard = self.root.HasChildren()

        self.dtlbtn.Enable(0 < len(self.list))
        self.findbtn.Enable(selected)
        self.updbtn.Enable(hascard)
        self.delbtn.Enable(hascard)
        self.dealbtn.Enable(selected)

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
