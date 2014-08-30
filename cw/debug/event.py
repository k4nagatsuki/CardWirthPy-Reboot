#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import itertools
import wx

import cw

#-------------------------------------------------------------------------------
#  実行イベント選択ダイアログ
#-------------------------------------------------------------------------------

class EventListDialog(wx.Dialog):
    def __init__(self, parent, currentfpath):
        wx.Dialog.__init__(self, parent, -1, u"実行するイベントの選択",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.events = EventList(self, (250, 300), currentfpath)
        self.showallcards = wx.CheckBox(self, -1, u"表示フラグがオフのカードも表示する")
        self.showallcards.SetValue(False)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["cancel"])

        self._changed_selection()

        self._bind()
        self._do_layout()

    def _do_layout(self):
        sizer = wx.GridBagSizer()

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.events, 1, flag=wx.EXPAND)
        sizer_left.Add(self.showallcards, 0, flag=wx.EXPAND|wx.TOP, border=5)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=5)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=5)
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def _bind(self):
        self.Bind(wx.EVT_CHECKBOX, self.OnShowAllCards, self.showallcards)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.events.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.events.Bind(wx.EVT_LEFT_DCLICK, self.OnOkBtn)

    def _changed_selection(self):
        if self.events.get_selectedevent():
            self.okbtn.Enable()
        else:
            self.okbtn.Disable()

    def OnTreeSelChanged(self, event):
        self._changed_selection()

    def OnShowAllCards(self, event):
        self.events.set_showallcards(self.showallcards.GetValue())
        self._changed_selection()

    def OnOkBtn(self, event):
        if self.events.get_selectedevent():
            cw.cwpy.sounds["signal"].play()
            self.EndModal(wx.ID_OK)

class EventList(wx.TreeCtrl):
    """シナリオに含まれるイベントをリストし、
    選択できるようにする。
    """

    def __init__(self, parent, size, currentfpath):
        """イベントリストのインスタンスを生成する。
        currentfpath: 最初から選択状態にするエリア等のファイルパス。
        """
        wx.TreeCtrl.__init__(self, parent, -1, size=size, style=wx.TR_SINGLE|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE)
        self.SetFont(cw.cwpy.rsrc.get_wxfont("tree", pixelsize=14, weight=wx.NORMAL))
        self._showallcards = False
        self.imglist = wx.ImageList(16, 16)
        imgidx_area = self.imglist.Add(cw.cwpy.rsrc.debugs["AREA"])
        imgidx_battle = self.imglist.Add(cw.cwpy.rsrc.debugs["BATTLE"])
        imgidx_package = self.imglist.Add(cw.cwpy.rsrc.debugs["PACK"])
        imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL"])
        imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM"])
        imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST"])
        self.imgidx_menucard = self.imglist.Add(cw.cwpy.rsrc.debugs["CARD"])
        self.imgidx_event = self.imglist.Add(cw.cwpy.rsrc.debugs["EVENT"])
        self.imgidx_ignition = self.imglist.Add(cw.cwpy.rsrc.debugs["IGNITION"])
        self.imgidx_keycode = self.imglist.Add(cw.cwpy.rsrc.debugs["KEYCODE"])
        self.imgidx_round = self.imglist.Add(cw.cwpy.rsrc.debugs["ROUND"])
        self.SetImageList(self.imglist)
        self.root = self.AddRoot(cw.cwpy.sdata.name)

        def append_item(d, imgidx):
            keys = d.keys()
            keys.sort()
            for id in keys:
                if id < 0:
                    continue
                a = d[id]
                name, path = a
                item = self.AppendItem(self.root, name, imgidx)
                self.SetItemPyData(item, (name, path, False))
                if os.path.normcase(currentfpath) == os.path.normcase(path):
                    self._expand_item(item)
                    self.Expand(item)
                    self.SelectItem(item, True)
                else:
                    self.AppendItem(item, u"読込中...")

        append_item(cw.cwpy.sdata.areas, imgidx_area)
        append_item(cw.cwpy.sdata.battles, imgidx_battle)
        append_item(cw.cwpy.sdata.packs, imgidx_package)
        append_item(cw.cwpy.sdata.skills, imgidx_skill)
        append_item(cw.cwpy.sdata.items, imgidx_item)
        append_item(cw.cwpy.sdata.beasts, imgidx_beast)

        selitem = self.GetSelection()
        if selitem:
            self.ScrollTo(selitem)

        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded)

    def OnTreeItemExpanded(self, event):
        self._expand_item(event.GetItem())

    def _expand_item(self, selitem):
        # エリア・バトル・パッケージ・カードに含まれる
        # イベント情報をツリーに追加する
        paritem = self.GetItemParent(selitem)
        if paritem <> self.root:
            return
        name, path, expanded = self.GetItemPyData(selitem)
        if expanded:
            return

        self.DeleteChildren(selitem)
        def append(parent, data, tag):
            e = cw.event.Event(data)
            if len(e.treekeys) == 0:
                return
            item = self.AppendItem(parent, e.treekeys[0], self.imgidx_event)
            self.SetItemPyData(item, e)
            for keynum in e.keynums:
                if keynum < 0: continue
                if tag == "Area":
                    if keynum == 1:
                        name = u"到着"
                    else:
                        continue
                elif tag == "Battle":
                    if keynum == 1:
                        name = u"勝利"
                    elif keynum == 2:
                        name = u"逃走"
                    elif keynum == 3:
                        name = u"敗北"
                    elif keynum == 4:
                        name = u"毎ラウンド"
                    elif keynum == 5:
                        name = u"バトル開始"
                    else:
                        continue
                elif tag in ("MenuCard", "LargeMenuCard"):
                    if keynum == 1:
                        name = u"クリック"
                    else:
                        continue
                elif tag == "EnemyCard":
                    if keynum == 1:
                        name = u"死亡"
                    else:
                        continue
                else:
                    continue
                child = self.AppendItem(item, name, self.imgidx_ignition)
                self.SetItemPyData(child, e)
            for keycode in e.keycodes:
                if keycode == "MatchingType=All": continue
                name = keycode
                child = self.AppendItem(item, name, self.imgidx_keycode)
                self.SetItemPyData(child, e)
            for keynum in e.keynums:
                if 0 <= keynum: continue
                name = u"ラウンド %s" % (-keynum)
                child = self.AppendItem(item, name, self.imgidx_round)
                self.SetItemPyData(child, e)

        data = cw.data.xml2etree(path)
        for ee in data.getfind("Events"):
            append(selitem, ee, data.getroot().tag)

        for ce in itertools.chain(data.getfind("MenuCards", False), data.getfind("EnemyCards", False)):
            if self._showallcards or cw.sprite.card.CWPyCard.is_flagtrue_static(ce):
                item = self.AppendItem(selitem, ce.gettext("Property/Name", u""), self.imgidx_menucard)
                for ee in ce.getfind("Events"):
                    append(item, ee, ce.tag)
                self.Expand(item)

        self.SetItemPyData(selitem, (name, path, True))

    def set_showallcards(self, value):
        """フラグがオフのカードをリストに表示するか設定する。
        value: Trueの場合はフラグがオフのカードも
               含めてすべてのカードを表示する。
        """
        if self._showallcards <> value:
            self._showallcards = value
            item, cookie = self.GetFirstChild(self.root)
            while item.IsOk():
                name, path, expanded = self.GetItemPyData(item)
                self.SetItemPyData(item, (name, path, False))
                if self.IsExpanded(item):
                    self._expand_item(item)
                else:
                    if expanded:
                        self.DeleteChildren(item)
                        self.AppendItem(item, u"読込中...")
                item, cookie = self.GetNextChild(self.root, cookie)

    def get_selectedevent(self):
        """選択中のイベントを返す。"""
        selitem = self.GetSelection()
        if not selitem:
            return None
        data = self.GetItemPyData(selitem)
        if isinstance(data, cw.event.Event):
            return data
        else:
            return None

    def get_currentfpath(self):
        """選択中のイベントが属するファイルのパスを返す。"""
        selitem = self.GetSelection()
        if not selitem:
            return
        parent = self.GetItemParent(selitem)
        while parent <> self.root:
            selitem = parent
            parent = self.GetItemParent(selitem)

        name, path, expanded = self.GetItemPyData(selitem)
        return path
