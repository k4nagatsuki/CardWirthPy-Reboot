#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import threading
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
        if cw.cwpy.is_playingscenario():
            self.scdata = cw.cwpy.sdata
            self.scpath = self.scdata.fpath
            if os.path.isdir(self.scpath):
                self.scpath = cw.util.join_paths(self.scpath, "Summary.wsm")
        else:
            self.scdata = None
            self.scpath = ""

        self._find = False
        self.list = []
        self.datalist = []
        self.target_cards = {}
        self.target_table = {}

        self.cardsbox = wx.StaticBox(self, -1, u"カードの選択")
        self.dealtargbox = wx.StaticBox(self, -1, u"配付先")
        self.methodbox = wx.StaticBox(self, -1, u"照合方法")
        self.targetsbox = wx.StaticBox(self, -1, u"処理対象")

        self.scenario = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"(シナリオ未選択)")

        self.imglist = wx.ImageList(16, 16)
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST"])

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
        self.stopbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"中断")
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
        self.timgidx_skill = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL"])
        self.timgidx_item = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM"])
        self.timgidx_beast = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST"])

        self.targets = wx.lib.agw.customtreectrl.CustomTreeCtrl(self, -1, size=(200, -1),
            style=wx.BORDER|wx.TR_DEFAULT_STYLE,
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

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnScenario, self.scenario);
        self.Bind(wx.EVT_BUTTON, self.OnDetailBtn, self.dtlbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDealBtn, self.dealbtn);
        self.Bind(wx.EVT_BUTTON, self.OnFindBtn, self.findbtn);
        self.Bind(wx.EVT_BUTTON, self.OnStopBtn, self.stopbtn);
        self.Bind(wx.EVT_BUTTON, self.OnUpdateBtn, self.updbtn);
        self.Bind(wx.EVT_BUTTON, self.OnDeleteBtn, self.delbtn);
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)
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
        sizer_right.Add(self.findbtn, 0, wx.EXPAND|wx.TOP, border=20)
        sizer_right.Add(self.stopbtn, 0, wx.EXPAND|wx.TOP, border=5)
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
            target = cw.cwpy.get_pcards()[cindex-1]

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
        self._find = True
        self.target_cards = self._get_cards(True)
        self.target_table = {}
        cards = set(self.target_cards.keys())
        def func(cards):
            roots = {}
            items = {}

            def set_status(text):
                def func(text):
                    if not self._find:
                        return
                    self.status.SetLabel(text)
                wx.CallAfter(func, text)

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

            def add_target(item, matcher, toplevel, owner, data):
                item.Check(True)
                self.targets.Expand(item.GetParent())
                if matcher in self.target_table:
                    self.target_table[matcher][item] = (toplevel, owner, data)
                else:
                    t = {}
                    t[item] = (toplevel, owner, data)
                    self.target_table[matcher] = t

            if cw.cwpy.ydata.party:
                for member in cw.cwpy.get_pcards():
                    if not self._find:
                        break
                    set_status(u"%sの手札カードを検索中..." % (member.name))
                    for cardpocket in [member.cardpocket[0], member.cardpocket[1], member.cardpocket[2]]:
                        for header in cardpocket:
                            matcher = self._get_matcher(header)
                            if matcher in cards:
                                def func(roots, items, matcher, member, cardpocket, header):
                                    if not self._find:
                                        return
                                    image = self.timgidx_party
                                    name = cw.cwpy.ydata.party.name
                                    root = get_item(roots, cw.cwpy.ydata.party, self.root, name, image)

                                    image = self.timgidx_member
                                    name = member.name
                                    item = get_item(items, member, root, name, image)

                                    image = self._get_imgidx(header)
                                    name = header.name
                                    item = self.targets.AppendItem(item, name, 1, image=image)
                                    add_target(item, matcher, member, cardpocket, header)
                                wx.CallAfter(func, roots, items, matcher, member, cardpocket, header)

                set_status(u"荷物袋を検索中...")
                for header in cw.cwpy.ydata.party.backpack:
                    if not self._find:
                        break
                    matcher = self._get_matcher(header)
                    if matcher in cards:
                        def func(roots, items, matcher, header):
                            if not self._find:
                                return
                            image = self.timgidx_backpack
                            name = u"荷物袋"
                            root = get_item(roots, "BACKPACK", self.root, name, image)

                            image = self._get_imgidx(header)
                            item = self.targets.AppendItem(root, header.name, 1, image=image)
                            add_target(item, matcher, None, cw.cwpy.ydata.party.backpack, header)
                        wx.CallAfter(func, roots, items, matcher, header)

            set_status(u"カード置場を検索中...")
            for header in cw.cwpy.ydata.storehouse:
                if not self._find:
                    break
                matcher = self._get_matcher(header)
                if matcher in cards:
                    def func(roots, items, matcher, header):
                        if not self._find:
                            return
                        image = self.timgidx_storehouse
                        name = u"カード置場"
                        root = get_item(roots, "STOREHOUSE", self.root, name, image)

                        image = self._get_imgidx(header)
                        item = self.targets.AppendItem(root, header.name, 1, image=image)
                        add_target(item, matcher, None, cw.cwpy.ydata.storehouse, header)
                    wx.CallAfter(func, roots, items, matcher, header)

            for header in cw.cwpy.ydata.standbys:
                if not self._find:
                    break
                member = cw.data.yadoxml2etree(header.fpath)
                set_status(u"%sの手札カードを検索中..." % (header.name))
                for cardpocket in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                    for data in cardpocket:
                        matcher = self._get_matcher(data)
                        if matcher in cards:
                            def func(roots, items, matcher, member, cardpocket, data):
                                if not self._find:
                                    return
                                image = self.timgidx_yado
                                name = u"待機中のメンバー"
                                root = get_item(roots, "STANDBYS", self.root, name, image)

                                image = self.timgidx_member
                                name = header.name
                                item = get_item(items, header, root, name, image)

                                image = self._get_imgidx(data)
                                name = data.gettext("Property/Name")
                                item = self.targets.AppendItem(item, name, 1, image=image)
                                add_target(item, matcher, member, cardpocket, data)
                            wx.CallAfter(func, roots, items, matcher, member, cardpocket, data)

            for partyheader in cw.cwpy.ydata.partys:
                if not self._find:
                    break
                party = cw.data.Party(partyheader.fpath)
                set_status(u"%sの手札カードを検索中..." % (party.name))
                for index, member in enumerate(party.members):
                    if not self._find:
                        break
                    for cardpocket in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                        for data in cardpocket:
                            matcher = self._get_matcher(data)
                            if matcher in cards:
                                def func(roots, items, matcher, party, member, cardpocket, data):
                                    if not self._find:
                                        return
                                    image = self.timgidx_party
                                    name = partyheader.name
                                    root = get_item(roots, (partyheader, 0), self.root, name, image)

                                    image = self.timgidx_member
                                    name = member.gettext("Property/Name")
                                    item = get_item(items, (partyheader, index), root, name, image)

                                    image = self._get_imgidx(data)
                                    name = data.gettext("Property/Name")
                                    item = self.targets.AppendItem(item, name, 1, image=image)
                                    add_target(item, matcher, party, cardpocket, data)
                                wx.CallAfter(func, roots, items, matcher, party.data, member, cardpocket, data)

                set_status(u"%sの荷物袋を検索中..." % (party.name))
                backpackdata = party.data.find("Backpack")
                for data in party.backpack:
                    if not self._find:
                        break
                    matcher = self._get_matcher(data)
                    if matcher in cards:
                        def func(roots, items, matcher, party, backpackdata, data):
                            if not self._find:
                                return
                            image = self.timgidx_backpack
                            name = u"%sの荷物袋" % (partyheader.name)
                            item = get_item(roots, (partyheader, -1), self.root, name, image)

                            image = self._get_imgidx(data)
                            name = data.gettext("Property/Name")
                            item = self.targets.AppendItem(item, name, 1, image=image)
                            add_target(item, matcher, party, backpackdata, data)
                        wx.CallAfter(func, roots, items, matcher, party.data, backpackdata, data)

            count = 0
            for array in self.target_table.values():
                count += len(array)
            set_status(u"%s件のカードが見つかりました。" % (count))

            cw.cwpy.sounds["signal"].play()
            def update_enable():
                self._find = False
                self._update_enable()
            wx.CallAfter(update_enable)

        threading.Thread(target=func, kwargs={"cards":cards}).start()
        self._update_enable()

    def OnStopBtn(self, event):
        self._find = False

    def OnUpdateBtn(self, event):
        writes = set()
        count = 0
        for matcher, infos in self.target_table.items():
            for item, info in infos.items():
                toplevel = info[0]
                owner = info[1]
                data = info[2]
                if not item.IsChecked():
                    continue
                del infos[item]

                index = list(owner).index(data)
                self._remove(owner, data, index)

                data = copy.deepcopy(self.target_cards[matcher])
                name = data.gettext("Property/Name", "")
                if cw.cwpy.ydata.storehouse is owner:
                    cw.content.get_card(data, owner, summon=False, toindex=index)
                elif cw.cwpy.ydata.party and cw.cwpy.ydata.party.backpack is owner:
                    cw.content.get_card(data, owner, summon=False, toindex=index)
                elif isinstance(toplevel, cw.character.Character):
                    cw.content.get_card(data, toplevel, summon=False, toindex=index)
                else:
                    dstdir = cw.util.join_paths(cw.cwpy.tempdir, "Material", data.getroot().tag, name)
                    cw.cwpy.copy_materials(data, dstdir)
                    owner.insert(index, data.getroot())

                self.targets.SetItemText(item, u"%s[更新]" % (name))
                data = data.getroot()

                if toplevel and not isinstance(toplevel, cw.character.Character):
                    writes.add(toplevel)
                infos[item] = (toplevel, owner, data)
                count += 1

        for data in writes:
            data.write_xml(True)

        self.status.SetLabel(u"%s件のカードを更新しました。" % (count))

        self._update_enable()
        cw.cwpy.sounds["harvest"].play()

    def OnDeleteBtn(self, event):
        writes = set()
        count = 0
        for matcher, infos in self.target_table.items():
            for item, info in infos.items():
                toplevel = info[0]
                owner = info[1]
                data = info[2]
                if not item.IsChecked():
                    continue
                del infos[item]
                if isinstance(data, cw.header.CardHeader):
                    name = data.name
                else:
                    name = data.gettext("Property/Name", "")
                self.targets.SetItemText(item, u"%s[削除済み]" % (name))

                index = list(owner).index(data)
                self._remove(owner, data, index)
                if toplevel and not isinstance(toplevel, cw.character.Character):
                    writes.add(toplevel)
                count += 1

        for data in writes:
            data.write_xml(True)

        self.status.SetLabel(u"%s件のカードを除去しました。" % (count))

        self._update_enable()
        cw.cwpy.sounds["harvest"].play()

    def _remove(self, owner, data, index):
        if isinstance(owner, list):
            header = owner[index]
            cw.cwpy.trade(targettype="TRASHBOX", header=header, from_event=True)
        else:
            cw.cwpy.remove_materials(data)
            owner.remove(data)

    def OnCardSelected(self, event):
        self._update_enable()

    def OnClose(self, event):
        self._find = False
        self.Destroy()

    def _get_matcher(self, data):
        type = ""
        name = ""
        desc = ""
        scenario = ""
        author = ""

        if isinstance(data, cw.header.CardHeader):
            header = data
            type = header.type
            if self.mname.GetValue():
                name = header.name
            if self.mdesc.GetValue():
                desc = header.desc
            if self.mscenario.GetValue():
                scenario = header.scenario
            if self.mauthor.GetValue():
                author = header.author
        else:
            type = data.tag
            e = data.find("Property")
            if self.mname.GetValue():
                name = e.gettext("Name", "")
            if self.mdesc.GetValue():
                desc = e.gettext("Description", "")
            if self.mscenario.GetValue():
                scenario = e.gettext("Scenario", "")
            if self.mauthor.GetValue():
                author = e.gettext("Author", "")

        return (type, name, desc, scenario, author)

    def _get_imgidx(self, data):
        type = ""
        if isinstance(data, cw.header.CardHeader):
            header = data
            type = header.type
        else:
            type = data.tag

        if type == "SkillCard":
            return self.timgidx_skill
        elif type == "ItemCard":
            return self.timgidx_item
        elif type == "BeastCard":
            return self.timgidx_beast

        return None

    def _get_cards(self, selected):
        cards = {}
        index = -1
        if selected:
            state = wx.LIST_STATE_SELECTED
        else:
            state = wx.LIST_STATE_DONTCARE
        while (True):
            index = self.cards.GetNextItem(index, wx.LIST_NEXT_ALL, state)
            if index <= -1:
                break
            cards[self._get_matcher(self.list[index])] = self.datalist[index]

        return cards

    def _update_cards(self):
        self.cards.DeleteAllItems()
        self.targets.DeleteChildren(self.root)
        self.list = []
        self.datalist = []

        if not self.scdata:
            self.scenario.SetLabel(u"(シナリオ未選択)")
            self._update_enable()
            return

        self.scenario.SetLabel(self.scdata.name)

        def append_cards(table, image):
            for id in table.keys():
                index = self.cards.GetItemCount()
                data = cw.data.xml2etree(table[id][1])

                header = cw.header.CardHeader(carddata=data.getroot(), from_scenario=True, scedir=self.scdata.scedir)
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

        self._update_enable()

    def _update_enable(self):
        selected = -1 < self.cards.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)

        self.dtlbtn.Enable(0 < len(self.list))
        self.dealbtn.Enable(selected)

        hascard = False
        for array in self.target_table.values():
            if 0 < len(array):
                hascard = True
                break

        self.findbtn.Enable(selected and not self._find)
        self.stopbtn.Enable(self._find)
        self.updbtn.Enable(hascard and not self._find)
        self.delbtn.Enable(hascard and not self._find)

def get_scenario(fpath):
    lfpath = fpath.lower()
    if lfpath.endswith(".wsm"):
        t = cw.scenariodb.read_summary(os.path.dirname(fpath))
    else:
        t = cw.scenariodb.read_summary(fpath)
    if not t:
        return None

    header = cw.header.ScenarioHeader(t)
    return cw.data.ScenarioData(header, cardonly=True)

class CheckableListCtrl(wx.ListCtrl, wx.lib.mixins.listctrl.CheckListCtrlMixin):
    def __init__(self, parent, id, size, style):
        wx.ListCtrl.__init__(self, parent, id, size=size, style=style)
        wx.lib.mixins.listctrl.CheckListCtrlMixin.__init__(self)

def main():
    pass

if __name__ == "__main__":
    main()
