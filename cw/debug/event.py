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
    def __init__(self, parent, currentfpath, showhiddencards):
        wx.Dialog.__init__(self, parent, -1, u"実行するイベントの選択",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        self.events = EventList(self, cw.ppis((250, 300)), currentfpath, showhiddencards)
        self.showhiddencards = showhiddencards
        self.showallcards = wx.CheckBox(self, -1, u"表示フラグがオフのカードも表示する")
        self.showallcards.SetValue(self.showhiddencards)
        self.start_event = False

        # 開く
        self.openbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["open_event"])
        # 実行
        self.startbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["run_event"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["cancel"])

        self._changed_selection()

        self._bind()
        self._do_layout()

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.events, 1, flag=wx.EXPAND)
        sizer_left.Add(self.showallcards, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.openbtn, 0, wx.EXPAND)
        sizer_right.Add(self.startbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def _bind(self):
        self.Bind(wx.EVT_CHECKBOX, self.OnShowAllCards, self.showallcards)
        self.Bind(wx.EVT_BUTTON, self.OnOpenBtn, self.openbtn)
        self.Bind(wx.EVT_BUTTON, self.OnStartBtn, self.startbtn)
        self.events.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.events.Bind(wx.EVT_LEFT_DCLICK, self.OnOpenBtn)

    def _changed_selection(self):
        if self.events.get_selectedevent():
            self.openbtn.Enable()
            self.startbtn.Enable()
        else:
            self.openbtn.Disable()
            self.startbtn.Disable()

    def OnTreeSelChanged(self, event):
        self._changed_selection()

    def OnShowAllCards(self, event):
        self.showhiddencards = self.showallcards.GetValue()
        self.events.set_showallcards(self.showhiddencards)
        self._changed_selection()

    def OnStartBtn(self, event):
        if self.events.get_selectedevent():
            cw.cwpy.play_sound("signal")
            self.start_event = True
            self.EndModal(wx.ID_OK)

    def OnOpenBtn(self, event):
        if self.events.get_selectedevent():
            cw.cwpy.play_sound("signal")
            self.start_event = False
            self.EndModal(wx.ID_OK)
        elif isinstance(event, wx.MouseEvent):
            selitem = self.events.GetSelection()
            if selitem and selitem.IsOk() and not self.events.IsExpanded(selitem):
                self.events.Expand(selitem)

class EventList(wx.TreeCtrl):
    """シナリオに含まれるイベントをリストし、
    選択できるようにする。
    """

    def __init__(self, parent, size, currentfpath, showhiddencards):
        """イベントリストのインスタンスを生成する。
        currentfpath: 最初から選択状態にするエリア等のファイルパス。
        """
        wx.TreeCtrl.__init__(self, parent, -1, size=size, style=wx.TR_SINGLE|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE)
        self.SetDoubleBuffered(True)
        self._showallcards = showhiddencards
        self.imglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
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
        # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.imgidx_cast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_CAST"])

        self.SetImageList(self.imglist)
        self.root = self.AddRoot(cw.cwpy.sdata.name)

        def append_item(getids, getname, getdata, getfpath, imgidx):
            keys = getids()
            cw.util.sort_by_attr(keys)
            for resid in keys:
                if resid < 0:
                    continue
                name = getname(resid)
                if name is None:
                    continue
                fpath = getfpath(resid)
                if fpath is None:
                    continue
                item = self.AppendItem(self.root, name, imgidx)
                self.SetItemPyData(item, (name, resid, getdata, getfpath, False))
                if os.path.normcase(currentfpath) == os.path.normcase(fpath):
                    self._expand_item(item)
                    self.Expand(item)
                    self.SelectItem(item, True)
                else:
                    self.AppendItem(item, u"読込中...")

        append_item(cw.cwpy.sdata.get_areaids, cw.cwpy.sdata.get_areaname, cw.cwpy.sdata.get_areadata, cw.cwpy.sdata.get_areafpath, imgidx_area)
        append_item(cw.cwpy.sdata.get_battleids, cw.cwpy.sdata.get_battlename, cw.cwpy.sdata.get_battledata, cw.cwpy.sdata.get_battlefpath, imgidx_battle)
        append_item(cw.cwpy.sdata.get_packageids, cw.cwpy.sdata.get_packagename, cw.cwpy.sdata.get_packagedata, cw.cwpy.sdata.get_packagefpath, imgidx_package)
        append_item(cw.cwpy.sdata.get_skillids, cw.cwpy.sdata.get_skillname, cw.cwpy.sdata.get_skilldata, cw.cwpy.sdata.get_skillfpath, imgidx_skill)
        append_item(cw.cwpy.sdata.get_itemids, cw.cwpy.sdata.get_itemname, cw.cwpy.sdata.get_itemdata, cw.cwpy.sdata.get_itemfpath, imgidx_item)
        append_item(cw.cwpy.sdata.get_beastids, cw.cwpy.sdata.get_beastname, cw.cwpy.sdata.get_beastdata, cw.cwpy.sdata.get_beastfpath, imgidx_beast)

        selitem = self.GetSelection()
        if selitem:
            self.ScrollTo(selitem)

        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded)

    def OnTreeItemExpanded(self, event):
        self._expand_item(event.GetItem())

    def _expand_item(self, selitem, virtual=False):
        # エリア・バトル・パッケージ・カードに含まれる
        # イベント情報をツリーに追加する
        paritem = self.GetItemParent(selitem)
        if paritem <> self.root:
            return
        name, resid, getdata, getfpath, expanded = self.GetItemPyData(selitem)
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
                elif tag == ("EnemyCard", "PlayerCardEvents"):
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

        e = getdata(resid)
        if e is None:
            self.AppendItem(selitem, u"読込に失敗しました")
            return
        data = cw.data.xml2etree(element=e)
        for ee in data.getfind("Events"):
            append(selitem, ee, data.getroot().tag)
            if virtual:
                break

        if not virtual:
            # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
            for pe in data.getfind("PlayerCardEvents", False):
                item = self.AppendItem(selitem, u"プレイヤーカード", self.imgidx_menucard)
                for ee in pe:
                    append(item, ee, pe.tag)
                self.Expand(item)

            for ce in itertools.chain(data.getfind("MenuCards", False), data.getfind("EnemyCards", False)):
                if self._showallcards or cw.sprite.card.CWPyCard.is_flagtrue_static(ce):
                    if ce.tag == "EnemyCard":
                        cardid = ce.getint("Property/Id", 0)
                        cardname = cw.cwpy.sdata.get_castname(cardid)
                        if  cardname is None:
                            cardname = u"(未設定)"
                    else:
                        cardname = ce.gettext("Property/Name", u"")
                    item = self.AppendItem(selitem, cardname, self.imgidx_menucard)
                    for ee in ce.getfind("Events"):
                        append(item, ee, ce.tag)
                    self.Expand(item)

        self.SetItemPyData(selitem, (name, resid, getdata, getfpath, not virtual))
        if not self.ItemHasChildren(selitem):
            self.AppendItem(selitem, u"読込中...")

    def set_showallcards(self, value):
        """フラグがオフのカードをリストに表示するか設定する。
        value: Trueの場合はフラグがオフのカードも
               含めてすべてのカードを表示する。
        """
        if self._showallcards <> value:
            self._showallcards = value
            item, cookie = self.GetFirstChild(self.root)
            self.Freeze()
            while item.IsOk():
                name, resid, getdata, getfpath, expanded = self.GetItemPyData(item)
                self.SetItemPyData(item, (name, resid, getdata, getfpath, False))
                if self.IsExpanded(item):
                    self._expand_item(item)
                else:
                    if expanded:
                        self.DeleteChildren(item)
                        self.AppendItem(item, u"読込中...")
                item, cookie = self.GetNextChild(self.root, cookie)
            self.Thaw()

    def get_selectedevent(self):
        """選択中のイベントを返す。"""
        selitem = self.GetSelection()
        if not selitem:
            return None
        data = self.GetItemPyData(selitem)
        if isinstance(data, cw.event.Event):
            return data
        else:
            data = self.GetItemPyData(selitem)
            if not data is None:
                name, resid, getdata, getfpath, expanded = data
                if not expanded:
                    self.Freeze()
                    self._expand_item(selitem, virtual=True)
                    self.Thaw()
            child, _cookie = self.GetFirstChild(selitem)
            if child and child.IsOk():
                data = self.GetItemPyData(child)
                if isinstance(data, cw.event.Event):
                    return data

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

        _name, resid, _getdata, getfpath, _expanded = self.GetItemPyData(selitem)
        return getfpath(resid)
