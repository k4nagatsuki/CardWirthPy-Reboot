#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import wx
import wx.combo
import wx.lib.agw.customtreectrl

import cw


#-------------------------------------------------------------------------------
#  手札カード情報編集ダイアログ
#-------------------------------------------------------------------------------

class CardEditDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"手札カードの編集",
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.cwpy_debug = True

        self.party = cw.cwpy.ydata.party
        if cw.cwpy.is_playingscenario():
            self.scdata = cw.cwpy.sdata
            self.scpath = self.scdata.fpath
            if os.path.isdir(self.scpath):
                spath = cw.util.join_paths(self.scpath, "Summary.wsm")
                if os.path.isfile(spath):
                    self.scpath = spath
                spath = cw.util.join_paths(self.scpath, "Summary.xml")
                if os.path.isfile(spath):
                    self.scpath = spath
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

        self.scenario = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"(シナリオ未選択)")

        bmp = cw.cwpy.rsrc.dialogs["BOOKMARK_dbg"]
        self.bookmark = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), bmp=bmp)
        self.bookmark.SetToolTip(wx.ToolTip(u"ブックマーク"))
        self.bookmarkmenu = None

        self.imglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL_dbg"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM_dbg"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST_dbg"])

        self.cards = wx.ListCtrl(self, -1, size=cw.ppis((200, 250)),
            style=wx.LC_REPORT)
        self.cards.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.cards.InsertColumn(0, "ID")
        self.cards.InsertColumn(1, u"カード名")
        self.cards.InsertColumn(2, u"解説")
        self.cards.SetColumnWidth(0, cw.ppis(40))
        self.cards.SetColumnWidth(1, cw.ppis(85))
        self.cards.SetColumnWidth(2, cw.ppis(110))

        self.dealtarg = wx.combo.BitmapComboBox(self, -1, style=wx.CB_READONLY)
        self.notcast = 0
        if not (cw.cwpy.ydata.party and\
                cw.cwpy.ydata.party.is_adventuring()):
            bmp = cw.cwpy.rsrc.buttons["DECK_dbg"]
            self.dealtarg.Append(u"カード置場", bmp)
            self.notcast += 1
        if cw.cwpy.ydata.party:
            bmp = cw.cwpy.rsrc.buttons["SACK_dbg"]
            self.dealtarg.Append(u"荷物袋", bmp)
            self.notcast += 1
        bmp = cw.cwpy.rsrc.buttons["CAST_dbg"]
        for member in cw.cwpy.get_pcards():
            self.dealtarg.Append(member.name, bmp)
        # 配付先のデフォルトは荷物袋。なければカード置場
        if cw.cwpy.ydata.party:
            self.dealtarg.SetStringSelection(u"荷物袋")
        else:
            self.dealtarg.SetStringSelection(u"カード置場")

        self.dtlbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"情報")
        self.dealbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"配付")
        self.findbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"検索")
        self.stopbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"中断")
        self.updbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"更新")
        self.delbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"除去")

        self.closebtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), name=u"閉じる")

        self.mname = wx.CheckBox(self, -1, u"カード名")
        self.mdesc = wx.CheckBox(self, -1, u"解説")
        self.mscenario = wx.CheckBox(self, -1, u"シナリオ")
        self.mauthor = wx.CheckBox(self, -1, u"作者")

        self.timglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
        self.timgidx_storehouse = self.timglist.Add(cw.cwpy.rsrc.buttons["DECK_dbg"])
        self.timgidx_backpack = self.timglist.Add(cw.cwpy.rsrc.buttons["SACK_dbg"])
        self.timgidx_party = self.timglist.Add(cw.cwpy.rsrc.debugs["MEMBER_dbg"])
        self.timgidx_yado = self.timglist.Add(cw.cwpy.rsrc.debugs["YADO_dbg"])
        self.timgidx_member = self.timglist.Add(cw.cwpy.rsrc.buttons["CAST_dbg"])
        self.timgidx_skill = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL_dbg"])
        self.timgidx_item = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM_dbg"])
        self.timgidx_beast = self.timglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST_dbg"])

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
        self.Bind(wx.EVT_BUTTON, self.OnScenario, self.scenario)
        self.Bind(wx.EVT_BUTTON, self.OnBookmark, self.bookmark)
        self.Bind(wx.EVT_BUTTON, self.OnDetailBtn, self.dtlbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDealBtn, self.dealbtn)
        self.Bind(wx.EVT_BUTTON, self.OnFindBtn, self.findbtn)
        self.Bind(wx.EVT_BUTTON, self.OnStopBtn, self.stopbtn)
        self.Bind(wx.EVT_BUTTON, self.OnUpdateBtn, self.updbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteBtn, self.delbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnCardSelected, self.cards)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnCardSelected, self.cards)

    def _do_layout(self):
        sizer_cards = wx.StaticBoxSizer(self.cardsbox, wx.VERTICAL)

        sizer_scenario = wx.BoxSizer(wx.HORIZONTAL)
        sizer_scenario.Add(self.scenario, 1, wx.EXPAND, 0)
        sizer_scenario.Add(self.bookmark, 0, wx.EXPAND, 0)

        sizer_cards.Add(sizer_scenario, 0, wx.EXPAND|wx.ALL, cw.ppis(5))
        sizer_cards.Add(self.cards, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, cw.ppis(5))

        sizer_dealtarg = wx.StaticBoxSizer(self.dealtargbox, wx.HORIZONTAL)
        sizer_dealtarg.Add(self.dealtarg, 1, wx.ALL, cw.ppis(5))

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(sizer_cards, 1, wx.EXPAND|wx.ALL, cw.ppis(5))
        sizer_left.Add(sizer_dealtarg, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, cw.ppis(5))

        sizer_method = wx.StaticBoxSizer(self.methodbox, wx.HORIZONTAL)
        sizer_checks = wx.BoxSizer(wx.HORIZONTAL)
        sizer_checks.Add(self.mname, 1, wx.RIGHT, cw.ppis(5))
        sizer_checks.Add(self.mdesc, 1, wx.RIGHT, cw.ppis(5))
        sizer_checks.Add(self.mscenario, 1, wx.RIGHT, cw.ppis(5))
        sizer_checks.Add(self.mauthor, 1)
        sizer_method.Add(sizer_checks, 1, wx.EXPAND|wx.ALL, cw.ppis(5))

        sizer_targets = wx.StaticBoxSizer(self.targetsbox, wx.VERTICAL)
        sizer_targets.Add(self.targets, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, cw.ppis(5))
        sizer_targets.Add(self.status, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, cw.ppis(5))

        sizer_middle = wx.BoxSizer(wx.VERTICAL)
        sizer_middle.Add(sizer_targets, 1, wx.EXPAND|wx.BOTTOM, cw.ppis(5))
        sizer_middle.Add(sizer_method, 0, wx.EXPAND)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.dtlbtn, 0, wx.EXPAND)
        sizer_right.Add(self.dealbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.findbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(20))
        sizer_right.Add(self.stopbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.updbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.delbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.closebtn, 0, wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_middle, 1, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnScenario(self, event):
        """配付や検索の対象となるカードを選択するため、
        シナリオのデータをロードする。
        """
        if self.scpath:
            dpath = os.path.dirname(self.scpath)
            fpath = os.path.basename(self.scpath)
        else:
            dpath = ""
            fpath = ""
        dlg = wx.FileDialog(self, u"シナリオの選択", dpath, fpath,
                            u"シナリオファイル (*.wsn; *.wsm; *.zip; *.lzh; *.cab; Summary.xml)|*.wsn;*.wsm;*.zip;*.lzh;*.cab;Summary.xml",
                            wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            fpath = dlg.GetPath()

            def func(self):
                try:
                    scdata = cw.scenariodb.get_scenario(fpath)
                    if not scdata:
                        def func(self):
                            self.Enable(True)
                        cw.cwpy.frame.exec_func(func, self)
                        return
                except:
                    cw.util.print_ex(file=sys.stderr)
                    def func(self):
                        self.Enable(True)
                    cw.cwpy.frame.exec_func(func, self)
                    return

                def func(self):
                    self.Enable(True)
                    self.scpath = fpath
                    self.scdata = scdata
                    self._update_cards()

                cw.cwpy.frame.exec_func(func, self)

            self.Enable(False)
            cw.cwpy.exec_func(func, self)

    def select_scenario(self, fpath):
        try:
            scdata = cw.scenariodb.get_scenario(fpath)
            if scdata:
                self.scpath = fpath
                self.scdata = scdata
                self._update_cards()
        except:
            cw.util.print_ex(file=sys.stderr)

    def OnBookmark(self, event):
        """ブックマークメニューを生成して表示する。"""
        cw.cwpy.play_sound("page")
        if not self.bookmarkmenu:
            self.create_bookmarkmenu()
        self._add_bookmark.Enable(not self.scdata is None)
        self._arrange_bookmark.Enable(bool(cw.cwpy.setting.bookmarks_for_cardedit))
        self.bookmark.PopupMenu(self.bookmarkmenu)

    def create_bookmarkmenu(self):
        if self.bookmarkmenu:
            self.bookmarkmenu.Destroy()
        menu = wx.Menu()
        self.bookmarkmenu = menu
        icon_add = cw.cwpy.rsrc.dialogs["BOOKMARK_dbg"]
        icon_arrange = cw.cwpy.rsrc.dialogs["ARRANGE_BOOKMARK_dbg"]
        icon_summary = cw.cwpy.rsrc.dialogs["SUMMARY_dbg"]

        self._add_bookmark = wx.MenuItem(menu, -1, u"ブックマークの登録")
        self._add_bookmark.SetBitmap(icon_add)
        menu.AppendItem(self._add_bookmark)
        menu.Bind(wx.EVT_MENU, self.OnAddBookmark, self._add_bookmark)

        self._arrange_bookmark = wx.MenuItem(menu, -1, u"ブックマークの整理")
        self._arrange_bookmark.SetBitmap(icon_arrange)
        menu.AppendItem(self._arrange_bookmark)
        menu.Bind(wx.EVT_MENU, self.OnArrangeBookmark, self._arrange_bookmark)

        # ブックマークを開くためのユーティリティクラス
        class OpenBookmark(object):
            def __init__(self, outer, bookmarkpath):
                self.outer = outer
                self.bookmarkpath = bookmarkpath

            def OnOpen(self, event):
                self.outer.select_scenario(self.bookmarkpath)

        if cw.cwpy.setting.bookmarks_for_cardedit:
            menu.AppendSeparator()
            for bookmarkpath, name in cw.cwpy.setting.bookmarks_for_cardedit:
                fname = os.path.basename(bookmarkpath)
                if fname.lower() in ("summary.xml", "summary.wsm"):
                    fname = os.path.basename(os.path.dirname(bookmarkpath))
                if name:
                    s = "%s(%s)" % (name, fname)
                else:
                    s = fname
                item = wx.MenuItem(menu, -1, s.replace("&", "&&"))
                item.SetBitmap(icon_summary)
                openbookmark = OpenBookmark(self, bookmarkpath)
                menu.AppendItem(item)
                menu.Bind(wx.EVT_MENU, openbookmark.OnOpen, item)

    def OnAddBookmark(self, event):
        if self.scdata:
            cw.cwpy.setting.bookmarks_for_cardedit.append((self.scpath, self.scdata.name))
            self.create_bookmarkmenu()

    def OnArrangeBookmark(self, event):
        dlg = cw.debug.edit.EditBookmarksForCardEditDialog(self, cw.cwpy.setting.bookmarks_for_cardedit)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.setting.bookmarks_for_cardedit = dlg.list
            self.create_bookmarkmenu()
        dlg.Destroy()

    def OnDetailBtn(self, event):
        """カードの情報を表示する。"""
        if 0 == self.cards.GetItemCount():
            return
        index = self.cards.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index <= -1:
            index = 0
        for i, header in enumerate(self.list):
            header.negaflag = (i == index)
        self.draw(True)
        dlg = cw.dialog.cardinfo.YadoCardInfo(self, self.list, self.list[index],
                                              scedir=self.scdata.tempdir)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

    def draw(self, update):
        for i, header in enumerate(self.list):
            if header.negaflag:
                self.cards.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            else:
                self.cards.SetItemState(i, 0, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)

    def OnDealBtn(self, event):
        """選択したカードを配付する。"""
        cname = self.dealtarg.GetStringSelection()
        if cname == u"カード置場":
            target = cw.cwpy.ydata.storehouse
        elif cname == u"荷物袋":
            target = self.party.backpack
        else:
            cindex = self.dealtarg.GetSelection()
            target = cw.cwpy.get_pcards()[cindex-self.notcast]

        index = -1
        count = 0
        while True:
            index = self.cards.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            notscenariocard = not cw.cwpy.is_playingscenario()
            data = cw.data.copydata(self.datalist[index])
            header = self.list[index]
            cw.content.get_card(data, target, notscenariocard=notscenariocard, copymaterialfrom=header.scedir, fromdebugger=True,
                                anotherscenariocard=True)
            count += 1

        if 0 < count:
            cw.cwpy.play_sound("harvest")

    def OnFindBtn(self, event):
        """キャラクター・荷物袋・宿に存在するカードを検索する。"""
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

            def add_target(item, matcher, toplevel, owner, data, insce):
                item.Check(True)
                self.targets.Expand(item.GetParent())
                if matcher in self.target_table:
                    self.target_table[matcher][item] = (toplevel, owner, data, not insce)
                else:
                    t = {}.copy()
                    t[item] = (toplevel, owner, data, not insce)
                    self.target_table[matcher] = t

            if cw.cwpy.ydata.party:
                for member in cw.cwpy.get_pcards():
                    if not self._find:
                        break
                    set_status(u"%sの手札カードを検索中..." % (member.name))
                    for cardpocket in (member.cardpocket[cw.POCKET_SKILL], member.cardpocket[cw.POCKET_ITEM], member.cardpocket[cw.POCKET_BEAST]):
                        for header in cardpocket:
                            matcher = self._get_matcher(header)
                            if matcher in cards:
                                def func(roots, items, matcher, member, header):
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
                                    add_target(item, matcher, member, member, header, cw.cwpy.is_playingscenario())
                                wx.CallAfter(func, roots, items, matcher, member, header)

                set_status(u"荷物袋を検索中...")
                for header in cw.cwpy.ydata.party.backpack:
                    if not self._find:
                        break
                    matcher = self._get_matcher(header)
                    if matcher in cards:
                        def func(roots, items, matcher, header):
                            if not self._find:
                                return
                            party = cw.cwpy.ydata.party

                            image = self.timgidx_backpack
                            name = u"荷物袋"
                            root = get_item(roots, "BACKPACK", self.root, name, image)

                            image = self._get_imgidx(header)
                            item = self.targets.AppendItem(root, header.name, 1, image=image)
                            add_target(item, matcher, None, party, header, cw.cwpy.is_playingscenario())
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
                        add_target(item, matcher, None, cw.cwpy.ydata.storehouse, header, False)
                    wx.CallAfter(func, roots, items, matcher, header)

            for header in cw.cwpy.ydata.standbys:
                if not self._find:
                    break
                member = cw.data.yadoxml2etree(header.fpath)
                set_status(u"%sの手札カードを検索中..." % (header.name))
                pcard = None
                for cardpocket in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                    for data in cardpocket:
                        matcher = self._get_matcher(data)
                        if matcher in cards:
                            def func(roots, items, matcher,  member, pcard, data):
                                if not self._find:
                                    return
                                image = self.timgidx_yado
                                name = u"待機中のメンバー"
                                root = get_item(roots, "STANDBYS", self.root, name, image)

                                image = self.timgidx_member
                                name = pcard.name
                                item = get_item(items, pcard, root, name, image)

                                image = self._get_imgidx(data)
                                name = data.gettext("Property/Name")
                                item = self.targets.AppendItem(item, name, 1, image=image)
                                add_target(item, matcher, member, pcard, data, False)
                            if not pcard:
                                pcard = cw.character.Character(data=member)
                            wx.CallAfter(func, roots, items, matcher, member, pcard, data)

            for partyheader in cw.cwpy.ydata.partys:
                if not self._find:
                    break
                insce = partyheader.is_adventuring()
                party = cw.data.Party(partyheader)
                set_status(u"%sの手札カードを検索中..." % (party.name))
                for index, member in enumerate(party.members):
                    if not self._find:
                        break
                    pcard = None
                    for cardpocket in [member.getfind("SkillCards"), member.getfind("ItemCards"), member.getfind("BeastCards")]:
                        for data in cardpocket:
                            matcher = self._get_matcher(data)
                            if matcher in cards:
                                def func(roots, items, matcher, party, index, pcard, cardpocket, data, insce):
                                    if not self._find:
                                        return
                                    image = self.timgidx_party
                                    name = partyheader.name
                                    root = get_item(roots, (partyheader, 0), self.root, name, image)

                                    image = self.timgidx_member
                                    name = pcard.name
                                    item = get_item(items, (partyheader, index + 1), root, name, image)

                                    image = self._get_imgidx(data)
                                    name = data.gettext("Property/Name")
                                    item = self.targets.AppendItem(item, name, 1, image=image)
                                    add_target(item, matcher, pcard, pcard, data, insce)
                                if not pcard:
                                    pcard = cw.character.Character(data=member)
                                wx.CallAfter(func, roots, items, matcher, party, index, pcard, cardpocket, data, insce)

                set_status(u"%sの荷物袋を検索中..." % (party.name))
                for header in party.backpack:
                    if not self._find:
                        break
                    matcher = self._get_matcher(header)
                    if matcher in cards:
                        def func(roots, items, matcher, partyheader, party, header, insce):
                            if not self._find:
                                return
                            partyheader.data = party

                            image = self.timgidx_backpack
                            name = u"%sの荷物袋" % (party.name)
                            item = get_item(roots, (partyheader, -1), self.root, name, image)

                            image = self._get_imgidx(header)
                            name = header.name
                            item = self.targets.AppendItem(item, name, 1, image=image)
                            add_target(item, matcher, party, party, header, insce)
                        wx.CallAfter(func, roots, items, matcher, partyheader, party, header, insce)

            count = 0
            for array in self.target_table.values():
                count += len(array)
            set_status(u"%s件のカードが見つかりました。" % (count))

            cw.cwpy.play_sound("signal")
            def update_enable():
                self._find = False
                self._update_enable()
            wx.CallAfter(update_enable)

        threading.Thread(target=func, kwargs={"cards":cards}).start()
        self._update_enable()

    def OnStopBtn(self, event):
        """カードの検索を中止する。"""
        self._find = False

    def OnUpdateBtn(self, event):
        """カードの更新。"""
        writes = set()
        count = 0
        for matcher, infos in self.target_table.items():
            for item, info in infos.items():
                toplevel = info[0]
                owner = info[1]
                data = info[2]
                notscenariocard = info[3]
                order = -1
                if not item.IsChecked():
                    continue
                del infos[item]

                index = self._indexof(matcher, owner, data)
                if isinstance(data, cw.header.CardHeader):
                    order = data.order
                header2 = self._remove(owner, data, index)

                header, data = self.target_cards[matcher]
                data = cw.data.copydata(data)
                name = data.gettext("Property/Name", "")
                attachment = header2.attachment if header2.type == "BeastCard" else False
                if cw.cwpy.ydata.storehouse is owner:
                    cw.content.get_card(data, owner, notscenariocard=notscenariocard, toindex=index, insertorder=order, copymaterialfrom=header.scedir, attachment=attachment,
                                        anotherscenariocard=True)
                elif isinstance(owner, cw.data.Party):
                    cw.content.get_card(data, owner.backpack, notscenariocard=notscenariocard, toindex=index, insertorder=order, party=owner, copymaterialfrom=header.scedir, attachment=attachment,
                                        anotherscenariocard=True)
                elif isinstance(owner, cw.character.Character):
                    cw.content.get_card(data, owner, notscenariocard=notscenariocard, toindex=index, insertorder=order, copymaterialfrom=header.scedir, attachment=attachment,
                                        anotherscenariocard=True)
                else:
                    assert False

                self.targets.SetItemText(item, u"%s[更新]" % (name))

                if toplevel:
                    writes.add(toplevel)
                infos[item] = (toplevel, owner, self._get_list(matcher, owner, data)[index], notscenariocard)
                count += 1

        self._write_results(writes)

        self.status.SetLabel(u"%s件のカードを更新しました。" % (count))

        self._update_enable()
        cw.cwpy.play_sound("harvest")

    def OnDeleteBtn(self, event):
        """カードの除去。"""
        writes = set()
        count = 0
        for matcher, infos in self.target_table.items():
            for item, info in infos.items():
                toplevel = info[0]
                owner = info[1]
                data = info[2]
                _notscenariocard = info[3]
                if not item.IsChecked():
                    continue
                del infos[item]
                if isinstance(data, cw.header.CardHeader):
                    name = data.name
                else:
                    name = data.gettext("Property/Name", "")
                self.targets.SetItemText(item, u"%s[削除済み]" % (name))

                index = self._indexof(matcher, owner, data)
                self._remove(owner, data, index)
                if toplevel:
                    writes.add(toplevel)
                count += 1

        self._write_results(writes)

        self.status.SetLabel(u"%s件のカードを除去しました。" % (count))

        self._update_enable()
        cw.cwpy.play_sound("harvest")

    def _get_list(self, matcher, owner, data):
        if isinstance(owner, cw.data.Party):
            o = owner.backpack
        elif isinstance(owner, cw.character.Character):
            if isinstance(data, cw.header.CardHeader):
                if matcher[0] == "SkillCard":
                    o = owner.cardpocket[cw.POCKET_SKILL]
                elif matcher[0] == "ItemCard":
                    o = owner.cardpocket[cw.POCKET_ITEM]
                elif matcher[0] == "BeastCard":
                    o = owner.cardpocket[cw.POCKET_BEAST]
            else:
                if matcher[0] == "SkillCard":
                    o = owner.data.find("SkillCards")
                elif matcher[0] == "ItemCard":
                    o = owner.data.find("ItemCards")
                elif matcher[0] == "BeastCard":
                    o = owner.data.find("BeastCards")
                o = list(o)
        else:
            o = list(owner)
        return o

    def _indexof(self, matcher, owner, data):
        """指定されたマッチング条件のカードを
        ownerがどの位置に持っているかを返す。
        """
        return self._get_list(matcher, owner, data).index(data)

    def _remove(self, owner, data, index):
        """ownerから指定するカードを取り除く。"""
        if isinstance(owner, cw.data.Party):
            header = data
            cw.cwpy.trade(targettype="TRASHBOX", header=header, from_event=True, sort=False, party=owner)
            return header
        elif isinstance(owner, list):
            header = owner[index]
            cw.cwpy.trade(targettype="TRASHBOX", header=header, from_event=True, sort=False)
            return header
        elif isinstance(owner, cw.character.Character):
            if isinstance(data, cw.header.CardHeader):
                header = data
            else:
                if data.tag == "SkillCard":
                    header = owner.cardpocket[cw.POCKET_SKILL][index]
                elif data.tag == "ItemCard":
                    header = owner.cardpocket[cw.POCKET_ITEM][index]
                elif data.tag == "BeastCard":
                    header = owner.cardpocket[cw.POCKET_BEAST][index]
            cw.cwpy.trade(targettype="TRASHBOX", header=header, from_event=True, sort=False)
            return header
        else:
            assert False

    def _write_results(self, writes):
        """カードを配付した結果をファイル出力する。"""
        for data in writes:
            if isinstance(data, cw.data.Party):
                data.write()
            elif isinstance(data, cw.character.Character):
                data.data.write_xml()
            else:
                data.write_xml()

    def OnCardSelected(self, event):
        """カードリストの選択変更時に呼び出される。"""
        self._update_enable()

    def OnClose(self, event):
        """ダイアログを閉じる。"""
        self._find = False
        cw.cwpy.ydata.sort_storehouse()
        if cw.cwpy.ydata.party:
            cw.cwpy.ydata.party.sort_backpack()
        self.Destroy()

    def _get_matcher(self, data):
        """チェックに応じたカードのマッチング条件を返す。
        この戻り値を比較する事でカードの同一性を判断する。
        """
        cardtype = ""
        name = ""
        desc = ""
        scenario = ""
        author = ""

        if isinstance(data, cw.header.CardHeader):
            header = data
            cardtype = header.type
            if self.mname.GetValue():
                name = header.name
            if self.mdesc.GetValue():
                desc = header.desc
            if self.mscenario.GetValue():
                scenario = header.scenario
            if self.mauthor.GetValue():
                author = header.author
        else:
            cardtype = data.tag
            e = data.find("Property")
            if self.mname.GetValue():
                name = e.gettext("Name", "")
            if self.mdesc.GetValue():
                desc = e.gettext("Description", "")
            if self.mscenario.GetValue():
                scenario = e.gettext("Scenario", "")
            if self.mauthor.GetValue():
                author = e.gettext("Author", "")

        return (cardtype, name, desc, scenario, author)

    def _get_imgidx(self, data):
        """カードの種類に応じたアイコンのindexを返す。"""
        cardtype = ""
        if isinstance(data, cw.header.CardHeader):
            header = data
            cardtype = header.type
        else:
            cardtype = data.tag

        if cardtype == "SkillCard":
            return self.timgidx_skill
        elif cardtype == "ItemCard":
            return self.timgidx_item
        elif cardtype == "BeastCard":
            return self.timgidx_beast

        return None

    def _get_cards(self, selected):
        """リスト内で選択中のカードの一覧を返す。"""
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
            cards[self._get_matcher(self.list[index])] = (self.list[index], self.datalist[index])

        return cards

    def _update_cards(self):
        """シナリオ内のカードの一覧を表示する。"""
        self.cards.DeleteAllItems()
        self.targets.DeleteChildren(self.root)
        self.list = []
        self.datalist = []

        if not self.scdata:
            self.scenario.SetLabel(u"(シナリオ未選択)")
            self._update_enable()
            return

        self.scenario.SetLabel(self.scdata.name)

        def append_cards(getids, getdata, image):
            for resid in getids():
                index = self.cards.GetItemCount()
                e = getdata(resid)
                if e is None:
                    continue
                data = cw.data.xml2etree(element=e)

                header = cw.header.CardHeader(carddata=data.getroot(), from_scenario=True, scedir=self.scdata.scedir)
                header.negaflag = False
                self.cards.InsertStringItem(index, str(header.id))
                self.cards.SetStringItem(index, 1, header.name)
                self.cards.SetStringItem(index, 2, header.desc.replace("\\n", ""))
                self.cards.SetItemImage(index, image, image)
                self.list.append(header)
                self.datalist.append(data)

        append_cards(self.scdata.get_skillids, self.scdata.get_skilldata, self.imgidx_skill)
        append_cards(self.scdata.get_itemids, self.scdata.get_itemdata, self.imgidx_item)
        append_cards(self.scdata.get_beastids, self.scdata.get_beastdata, self.imgidx_beast)

        self._update_bookmarkname()
        self._update_enable()

    def _update_bookmarkname(self):
        if self.scpath:
            scpath = os.path.normcase(os.path.normpath(os.path.abspath(self.scpath)))
            for i, (fpath, name) in enumerate(cw.cwpy.setting.bookmarks_for_cardedit):
                scpath2 = os.path.normcase(os.path.normpath(os.path.abspath(fpath)))
                if scpath == scpath2:
                    cw.cwpy.setting.bookmarks_for_cardedit[i] = (fpath, self.scdata.name)

    def _update_enable(self):
        """各ボタンの押下可否を状況に応じて変更する。"""
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

def main():
    pass

if __name__ == "__main__":
    main()
