#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import wx

import cw


#-------------------------------------------------------------------------------
#  選択カード変更ダイアログ
#-------------------------------------------------------------------------------

class SelectedCardDialog(wx.Dialog):
    def __init__(self, parent, ccards, selectedcard):
        wx.Dialog.__init__(self, parent, -1, "選択カードの変更",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER|wx.MINIMIZE_BOX)
        self.cwpy_debug = True
        self._selectedcard = selectedcard

        self.cards = wx.TreeCtrl(self, size=cw.ppis((250, 300)),
                                 style=wx.TR_SINGLE|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE)

        self.imglist = wx.ImageList(cw.ppis(16), cw.ppis(16))
        imgidx_sack = self.imglist.Add(cw.cwpy.rsrc.debugs["SACK"])
        imgidx_cast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_CAST"])
        imgidx_action = self.imglist.Add(cw.cwpy.rsrc.debugs["CARD"])
        imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_SKILL"])
        imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_ITEM"])
        imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs["EVT_GET_BEAST"])
        self.cards.SetImageList(self.imglist)
        root = self.cards.AddRoot("")

        for i, (ccardname, hand) in enumerate(ccards):
            item = self.cards.AppendItem(root, ccardname, imgidx_cast if 0 < i else imgidx_sack)
            for header in hand:
                if header.type == "ActionCard":
                    icon = imgidx_action
                elif header.type == "SkillCard":
                    icon = imgidx_skill
                elif header.type == "ItemCard":
                    icon = imgidx_item
                elif header.type == "BeastCard":
                    icon = imgidx_beast
                else:
                    assert False, header.type
                citem = self.cards.AppendItem(item, header.name, icon)
                self.cards.SetItemData(citem, header)
                if header == self._selectedcard:
                    self.cards.SelectItem(citem)
            if 0 < i:
                self.cards.Expand(item)

            if not self.cards.GetSelection():
                self.cards.SelectItem(item)

        selitem = self.cards.GetSelection()
        if selitem:
            self.cards.ScrollTo(selitem)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_OK, (-1, -1), cw.cwpy.msgs["decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["cancel"])

        self._changed_selection()

        self._bind()
        self._do_layout()

    def _do_layout(self):
        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.BOTTOM|wx.EXPAND, cw.ppis(5))
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.cards, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def _bind(self):
        self.cards.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.cards.Bind(wx.EVT_LEFT_DCLICK, self.OnTreeDClick)

    def _changed_selection(self):
        selitem = self.cards.GetSelection()
        if selitem:
            header = self.cards.GetItemData(selitem)
        else:
            header = None

        if isinstance(header, cw.header.CardHeader):
            self._selectedcard = header
            self.okbtn.Enable()
        else:
            self._selectedcard = None
            self.okbtn.Disable()

    def OnTreeSelChanged(self, event):
        if not self:
            return
        self._changed_selection()

    def OnTreeDClick(self, event):
        selitem = self.cards.GetSelection()
        if selitem:
            header = self.cards.GetItemData(selitem)
            if header:
                self.EndModal(wx.ID_OK)

    def OnOkBtn(self, event):
        self.EndModal(wx.ID_OK)

    def get_selectedcard(self):
        return self._selectedcard
