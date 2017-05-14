#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import math
import wx
import wx.lib.mixins.listctrl as listmix

import cw


#-------------------------------------------------------------------------------
#  クーポン情報編集ダイアログ
#-------------------------------------------------------------------------------

class CouponEditDialog(wx.Dialog):

    def __init__(self, parent, selected=-1):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの経歴の編集",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True

        self._processing = False

        # システムクーポンは除外する
        self.syscoupons = set()
        for coupon in cw.cwpy.setting.sexcoupons:
            self.syscoupons.add(coupon)
        for coupon in cw.cwpy.setting.periodcoupons:
            self.syscoupons.add(coupon)
        for coupon in cw.cwpy.setting.naturecoupons:
            self.syscoupons.add(coupon)
        for coupon in cw.cwpy.setting.makingcoupons:
            self.syscoupons.add(coupon)
        for coupon in [cw.cwpy.msgs["number_1_coupon"], u"＿２", u"＿３", u"＿４", u"＿５", u"＿６"]:
            self.syscoupons.add(coupon)

        # クーポン一覧
        self.pcards = cw.cwpy.get_pcards()
        self.coupons = []
        for pcard in self.pcards:
            seq = self._get_coupons(pcard)
            seq.reverse()
            self.coupons.append(seq)

        # リスト
        self.values = EditableListCtrl(self, -1, size=cw.ppis((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE)
        self.values.imglist = wx.ImageList(cw.ppis(14), cw.ppis(14))
        self.values.imgidx_2 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS3_dbg"])
        self.values.imgidx_1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS2_dbg"])
        self.values.imgidx_0 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS1_dbg"])
        self.values.imgidx_m1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS0_dbg"])
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"名称")
        self.values.InsertColumn(1, u"得点")
        self.values.SetColumnWidth(0, cw.ppis(170))
        self.values.SetColumnWidth(1, cw.ppis(50))
        self.values.setResizeColumn(0)

        # 対象者
        self.targets = [u"全員"]
        for pcard in self.pcards:
            self.targets.append(pcard.get_name())
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(max(selected, -1) + 1)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL_dbg"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL_dbg"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)

        # 合計得点
        self.total = wx.StaticText(self, -1, "", style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)

        # レベル調節の有無
        self.adjust_level = wx.CheckBox(self, -1, u"得点に合わせてレベルを調節する")

        # 検索
        self.find = FindPanel(self, self.values, self._item_selected)

        # 追加
        self.addbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_ADD, (-1, -1), name=u"追加")
        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_REMOVE, (-1, -1), name=u"削除")
        # 得点
        self.valbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"得点")
        # 全て複製
        self.copybtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"全て複製")
        # 上へ
        bmp = cw.cwpy.rsrc.buttons["UP_dbg"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_UP, (-1, -1), bmp=bmp)
        # 下へ
        bmp = cw.cwpy.rsrc.buttons["DOWN_dbg"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_DOWN, (-1, -1), bmp=bmp)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._select_target()

        self._bind()
        self._do_layout()

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_BUTTON, self.OnAddBtn, self.addbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnValueBtn, self.valbtn)
        self.Bind(wx.EVT_BUTTON, self.OnCopyBtn, self.copybtn)
        self.Bind(wx.EVT_BUTTON, self.OnUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDownBtn, self.downbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit, self.values)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=cw.ppis(3))
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
        sizer_left.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=cw.ppis(3))
        sizer_left.Add(self.values, 1, flag=wx.EXPAND)
        sizer_left.Add(self.total, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(3))
        sizer_left.Add(self.adjust_level, 0, flag=wx.ALIGN_RIGHT|wx.TOP, border=cw.ppis(3))
        sizer_left.Add(self.find, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(3))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.addbtn, 0, wx.EXPAND)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.valbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.copybtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.upbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.downbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnSelectTarget(self, event):
        self._select_target()

    def OnLeftBtn(self, event):
        index = self.target.GetSelection()
        if index <= 0:
            self.target.SetSelection(len(self.pcards))
        else:
            self.target.SetSelection(index - 1)
        self._select_target()

    def OnRightBtn(self, event):
        index = self.target.GetSelection()
        if len(self.pcards) <= index:
            self.target.SetSelection(0)
        else:
            self.target.SetSelection(index + 1)
        self._select_target()

    def OnItemSelected(self, event):
        if self._processing:
            return
        self._item_selected()

    def OnAddBtn(self, event):
        names = set()
        for i in xrange(self.values.GetItemCount()):
            names.add(self.values.GetItem(i, 0).GetText())
        num = 1
        name = ""
        while True:
            name = u"新規項目 (%s)" % (num)
            if not name in names:
                break
            num += 1

        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            for seq in self.coupons:
                seq.insert(0, (name, 0))
        else:
            # 誰か一人
            self.coupons[cindex-1].insert(0, (name, 0))
        self.values.InsertStringItem(0, name)
        self.values.SetStringItem(0, 1, str(0))
        self.values.SetItemImage(0, self._get_valueimage(0))
        self._item_selected()

        self.values.OpenEditor(0, 0)

    def OnRemoveBtn(self, event):
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self._remove_coupon(index)
        self._item_selected()

    def _remove_coupon(self, index):
        name = self.values.GetItem(index, 0).GetText()
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            for seq in self.coupons:
                for i, coupon in enumerate(seq):
                    if coupon[0] == name:
                        seq.pop(i)
                        break
        else:
            # 誰か一人
            self.coupons[cindex-1].pop(index)
        self.values.DeleteItem(index)

    def OnCopyBtn(self, event):
        choices = map(lambda a: a.get_name(), self.pcards)
        dlg = cw.dialog.edit.ComboEditDialog2(self, u"全て複製", u"選択したメンバの全ての称号を編集中の称号に上書きコピーします。\nコピー元を選択してください。", choices)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            index = dlg.selected
            coupons = self.coupons[index]
            cindex = self.target.GetSelection()
            if cindex == 0:
                # 全員
                for i in xrange(len(self.coupons)):
                    self.coupons[i] = coupons[:]
            else:
                # 誰か一人
                self.coupons[cindex-1] = coupons[:]
            self._select_target()

    def OnValueBtn(self, event):
        index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index <= -1:
            return
        value = int(self.values.GetItem(index, 1).GetText())

        dlg = cw.dialog.edit.NumberEditDialog(self, u"得点の設定", value, -9, 9)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            index = -1
            while True:
                index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
                if index <= -1:
                    break
                self._set_value(index, dlg.value)
            self._item_selected()

    def OnUpBtn(self, event):
        if self.target.GetSelection() == 0:
            # 全員を選択中
            return

        index = -1
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= 0:
                break
            self._swap(index, index-1)
        self._item_selected()

    def OnDownBtn(self, event):
        if self.target.GetSelection() == 0:
            # 全員を選択中
            return
        indexes = self.get_selectedindexes()
        if not indexes or self.values.GetItemCount() <= indexes[-1] + 1:
            return

        indexes.reverse()
        for index in indexes:
            self._swap(index, index+1)
        self._item_selected()

    def _swap(self, index1, index2):
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員を選択中
            return
        self._processing = True
        seq = self.coupons[cindex-1]
        seq[index1], seq[index2] = seq[index2], seq[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        def set_item(index):
            self.values.SetStringItem(index, 0, seq[index][0])
            self.values.SetStringItem(index, 1, str(seq[index][1]))
            self.values.SetItemImage(index, self._get_valueimage(seq[index][1]))
        set_item(index1)
        set_item(index2)
        self._processing = False

    def OnEndLabelEdit(self, event):
        index = event.GetIndex()
        col = event.GetColumn()
        if col == 0:
            # 名称
            oldname = self.values.GetItem(index, col).GetText()
            newname = event.GetText()
            if newname and -1 >= self.values.FindItem(-1, newname):
                self._set_name(index, oldname, newname)
            else:
                event.Veto()
        elif col == 1:
            # 得点
            value = event.GetText()
            try:
                value = int(value)
            except:
                event.Veto()
                return
            self._set_value(index, value)
        self._item_selected()

    def OnOkBtn(self, event):
        def func(pcards, coupons, syscoupons, cindex, adjust_level):
            update = False
            for i, pcard in enumerate(pcards):
                replaced = pcard.replace_allcoupons(reversed(coupons[i]), syscoupons)
                # レベル調節
                if adjust_level and (cindex == -1 or i == cindex or replaced) and\
                        isinstance(pcard, cw.sprite.card.PlayerCard):
                    update |= pcard.adjust_level(False)

            if not update:
                cw.cwpy.play_sound("harvest")

        cindex = self.target.GetSelection() - 1
        adjust_level = self.adjust_level.IsChecked()
        cw.cwpy.exec_func(func, self.pcards, self.coupons, self.syscoupons, cindex, adjust_level)
        self.EndModal(wx.ID_OK)

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _get_valueimage(self, value):
        if 2 <= value:
            return self.values.imgidx_2
        elif 1 <= value:
            return self.values.imgidx_1
        elif 0 <= value:
            return self.values.imgidx_0
        else:
            return self.values.imgidx_m1

    def _append_couponlist(self, name, value):
        # リストに称号を追加する
        index = self.values.GetItemCount()
        self.values.InsertStringItem(index, name)
        self.values.SetStringItem(index, 1, str(value))
        self.values.SetItemImage(index, self._get_valueimage(value))

    def _select_target(self):
        # 選択されたキャラクターの称号一覧を表示する
        self.values.DeleteAllItems()
        index = self.target.GetSelection()
        if index == 0:
            coupons = set()
            for seq in self.coupons:
                for coupon in seq:
                    name = coupon[0]
                    if name in coupons:
                        continue
                    coupons.add(name)
                    value = coupon[1]
                    self._append_couponlist(name, value)
        else:
            for coupon in self.coupons[index-1]:
                self._append_couponlist(coupon[0], coupon[1])

        self._item_selected()

    def _get_coupons(self, pcard):
        seq = []
        for e in pcard.data.getfind("Property/Coupons"):
            name = e.text
            if name.startswith(u"＠") or name in self.syscoupons:
                continue
            value = e.get("value")
            seq.append((name, int(value)))
        return seq

    def _item_selected(self):
        indexes = self.get_selectedindexes()
        focus = wx.Window.FindFocus()
        if not indexes:
            self.rmvbtn.Enable(False)
            self.valbtn.Enable(False)
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)
        else:
            self.rmvbtn.Enable(True)
            self.valbtn.Enable(True)
            self.upbtn.Enable(0 < indexes[0])
            self.downbtn.Enable(indexes[-1] + 1 < self.values.GetItemCount())

        if self.target.GetSelection() == 0:
            # 全員を選択中
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)

        self.copybtn.Enable(1 < len(self.pcards))

        index = -1
        total = 0
        if 2 <= len(indexes):
            state = wx.LIST_STATE_SELECTED
        else:
            state = 0

        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, state)
            if index <= -1:
                break
            total += int(self.values.GetItem(index, 1).GetText())

        level = int((-1 + math.sqrt(1 + 4 * max(1, total))) / 2.0) + 1
        nextlevel = level + 1
        nextpoint = nextlevel * (nextlevel-1) - total

        s = u"%s点(レベル%s相当 レベル%sまで%s点)" % (total, level, nextlevel, nextpoint)

        if 2 <= len(indexes):
            self.total.SetLabel(u"選択中の合計: %s" % (s))
        else:
            self.total.SetLabel(u"合計: %s" % (s))

        if focus and focus.GetParent() == self and not focus.IsEnabled():
            self.values.SetFocus()

    def _set_name(self, index, oldname, newname):
        self.values.SetStringItem(index, 0, newname)
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            for seq in self.coupons:
                for i, coupon in enumerate(seq):
                    if coupon[0] == oldname:
                        seq[i] = (newname, coupon[1])
                        break
        else:
            # 誰か一人
            seq = self.coupons[cindex-1]
            seq[index] = (newname, seq[index][1])

    def _set_value(self, index, value):
        self.values.SetStringItem(index, 1, str(value))
        self.values.SetItemImage(index, self._get_valueimage(value))
        cindex = self.target.GetSelection()
        name = self.values.GetItem(index, 0).GetText()
        if cindex == 0:
            # 全員
            for seq in self.coupons:
                for i, coupon in enumerate(seq):
                    if coupon[0] == name:
                        seq[i] = (name, value)
                        break
        else:
            # 誰か一人
            self.coupons[cindex-1][index] = (name, value)

#-------------------------------------------------------------------------------
#  ゴシップ・終了印情報編集ダイアログ
#-------------------------------------------------------------------------------

class ListEditDialog(wx.Dialog):

    def __init__(self, parent, title, mlist, image):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        self.list = mlist

        self._processing = False

        # リスト
        self.values = EditableListCtrl(self, -1, size=cw.ppis((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE|wx.LC_NO_HEADER)
        self.values.imglist = wx.ImageList(image.GetWidth(), image.GetHeight())
        self.values.imgidx = self.values.imglist.Add(image)
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"項目名")
        self.values.SetColumnWidth(0, cw.ppis(170))
        self.values.setResizeColumn(0)

        # 検索
        self.find = FindPanel(self, self.values, self._item_selected)

        # 追加
        self.addbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_ADD, (-1, -1), name=u"追加")
        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_REMOVE, (-1, -1), name=u"削除")
        # 上へ
        bmp = cw.cwpy.rsrc.buttons["UP_dbg"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_UP, (-1, -1), bmp=bmp)
        # 下へ
        bmp = cw.cwpy.rsrc.buttons["DOWN_dbg"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_DOWN, (-1, -1), bmp=bmp)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        for name in self.list:
            index = self.values.GetItemCount()
            self.values.InsertStringItem(index, name)
            self.values.SetItemImage(index, self.values.imgidx)

        self._item_selected()

    def _bind(self):
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_BUTTON, self.OnAddBtn, self.addbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDownBtn, self.downbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit, self.values)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.values, 1, flag=wx.EXPAND)
        sizer_left.Add(self.find, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(3))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.addbtn, 0, wx.EXPAND)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.upbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.downbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnAddBtn(self, event):
        names = set()
        for name in self.list:
            names.add(name)
        num = 1
        name = ""
        while True:
            name = u"新規項目 (%s)" % (num)
            if not name in names:
                break
            num += 1

        self.list.insert(0, name)
        self.values.InsertStringItem(0, name)
        self.values.SetItemImage(0, self.values.imgidx)
        self._item_selected()

        self.values.OpenEditor(0, 0)

    def OnRemoveBtn(self, event):
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self.list.pop(index)
            self.values.DeleteItem(index)
        self._item_selected()

    def OnUpBtn(self, event):
        index = -1
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= 0:
                break
            self._swap(index, index-1)
        self._item_selected()

    def OnDownBtn(self, event):
        indexes = self.get_selectedindexes()
        if not indexes or self.values.GetItemCount() <= indexes[-1] + 1:
            return

        indexes.reverse()
        for index in indexes:
            self._swap(index, index+1)
        self._item_selected()

    def _swap(self, index1, index2):
        self._processing = True
        self.list[index1], self.list[index2] = self.list[index2], self.list[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        self.values.SetStringItem(index1, 0, self.list[index1])
        self.values.SetStringItem(index2, 0, self.list[index2])
        self._processing = False

    def OnEndLabelEdit(self, event):
        index = event.GetIndex()
        newname = event.GetText()
        if newname and -1 >= self.values.FindItem(-1, newname):
            self.values.SetStringItem(index, 0, newname)
            self.list[index] = newname
        else:
            event.Veto()

    def OnOkBtn(self, event):
        pass

    def OnItemSelected(self, event):
        if self._processing:
            return
        self._item_selected()

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _item_selected(self):
        focus = wx.Window.FindFocus()
        indexes = self.get_selectedindexes()
        if not indexes:
            self.rmvbtn.Enable(False)
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)
        else:
            self.rmvbtn.Enable(True)
            self.upbtn.Enable(0 < indexes[0])
            self.downbtn.Enable(indexes[-1] + 1 < self.values.GetItemCount())

        if focus and focus.GetParent() == self and not focus.IsEnabled():
            self.values.SetFocus()

class GossipEditDialog(ListEditDialog):
    def __init__(self, parent):
        ListEditDialog.__init__(self, parent, u"ゴシップの編集",
            cw.cwpy.ydata.get_gossiplist(), cw.cwpy.rsrc.debugs["GOSSIP_dbg"])

    def OnOkBtn(self, event):
        def func(seq):
            cw.cwpy.play_sound("harvest")
            cw.cwpy.ydata.clear_gossips()
            for name in seq:
                cw.cwpy.ydata.set_gossip(name)
        cw.cwpy.exec_func(func, self.list)
        self.EndModal(wx.ID_OK)

class CompStampEditDialog(ListEditDialog):
    def __init__(self, parent):
        ListEditDialog.__init__(self, parent, u"終了印の編集",
            cw.cwpy.ydata.get_compstamplist(), cw.cwpy.rsrc.debugs["COMPSTAMP_dbg"])

    def OnOkBtn(self, event):
        def func(seq):
            cw.cwpy.play_sound("harvest")
            cw.cwpy.ydata.clear_compstamps()
            for name in seq:
                cw.cwpy.ydata.set_compstamp(name)
        cw.cwpy.exec_func(func, self.list)
        self.EndModal(wx.ID_OK)

class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, cid, size, style):
        wx.ListCtrl.__init__(self, parent, cid, size=size, style=style)
        listmix.TextEditMixin.__init__(self)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

    def OpenEditor(self, row, col):
        # FIXME: 直接呼び出すとcol_locsが生成されないバグ
        self.col_locs = [0]
        loc = 0
        for n in xrange(self.GetColumnCount()):
            loc = loc + self.GetColumnWidth(n)
            self.col_locs.append(loc)
        if sys.platform == "win32" and sys.getwindowsversion().major < 6:
            # BUG: Windows XP環境でペーストすると空欄になる状態が発生する
            self.make_editor()
        listmix.TextEditMixin.OpenEditor(self, row, col)

#-------------------------------------------------------------------------------
#  保存済みJPDCイメージ整理ダイアログ
#-------------------------------------------------------------------------------

class SavedJPDCImageEditDialog(wx.Dialog):

    def __init__(self, parent, savedjpdcimage):
        wx.Dialog.__init__(self, parent, -1, u"JPDCイメージを保存したシナリオ",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        keys = savedjpdcimage.iterkeys()
        self.list = list(cw.util.sorted_by_attr(keys))
        self._removed = []

        # リスト
        image = cw.cwpy.rsrc.debugs["JPDCIMAGE_dbg"]
        self.values = AutoWidthListCtrl(self, -1, size=cw.ppis((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE|wx.LC_NO_HEADER|wx.BORDER)
        self.values.imglist = wx.ImageList(image.GetWidth(), image.GetHeight())
        self.values.imgidx = self.values.imglist.Add(image)
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"項目名")
        self.values.SetColumnWidth(0, cw.ppis(170))
        self.values.setResizeColumn(0)

        # 検索
        self.find = FindPanel(self, self.values, self._item_selected)

        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_REMOVE, (-1, -1), name=u"削除")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        for name, author in self.list:
            index = self.values.GetItemCount()
            if author:
                s = u"%s(%s)" % (name, author)
            else:
                s = u"%s" % (name)
            self.values.InsertStringItem(index, s)
            self.values.SetItemImage(index, self.values.imgidx)

        self._item_selected()

    def _bind(self):
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.values, 1, flag=wx.EXPAND)
        sizer_left.Add(self.find, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(3))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnRemoveBtn(self, event):
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self._removed.append(self.list.pop(index))
            self.values.DeleteItem(index)
        self._item_selected()

    def OnOkBtn(self, event):
        def func(removedlist):
            cw.cwpy.play_sound("harvest")
            for removed in removedlist:
                if removed in cw.cwpy.ydata.savedjpdcimage:
                    header = cw.cwpy.ydata.savedjpdcimage[removed]
                    header.remove_all()
                    del cw.cwpy.ydata.savedjpdcimage[removed]
            if cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.exec_func(func, self._removed)
        self.EndModal(wx.ID_OK)

    def OnItemSelected(self, event):
        self._item_selected()

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _item_selected(self):
        indexes = self.get_selectedindexes()
        self.rmvbtn.Enable(bool(indexes))

#-------------------------------------------------------------------------------
#  ブレークポイント整理ダイアログ
#-------------------------------------------------------------------------------

class BreakpointEditDialog(wx.Dialog):

    def __init__(self, parent, breakpoint_table):
        wx.Dialog.__init__(self, parent, -1, u"ブレークポイントを設定したシナリオ",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        keys = breakpoint_table.iterkeys()
        self.list = list(cw.util.sorted_by_attr(keys))
        self._removed = []

        # リスト
        image = cw.cwpy.rsrc.debugs["BREAKPOINT_dbg"]
        self.values = AutoWidthListCtrl(self, -1, size=cw.ppis((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE|wx.LC_NO_HEADER|wx.BORDER)
        self.values.imglist = wx.ImageList(image.GetWidth(), image.GetHeight())
        self.values.imgidx = self.values.imglist.Add(image)
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"項目名")
        self.values.SetColumnWidth(0, cw.ppis(170))
        self.values.setResizeColumn(0)

        # 検索
        self.find = FindPanel(self, self.values, self._item_selected)

        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_REMOVE, (-1, -1), name=u"削除")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        for name, author in self.list:
            index = self.values.GetItemCount()
            if author:
                s = u"%s(%s)" % (name, author)
            else:
                s = u"%s" % (name)
            self.values.InsertStringItem(index, s)
            self.values.SetItemImage(index, self.values.imgidx)

        self._item_selected()

    def _bind(self):
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.values, 1, flag=wx.EXPAND)
        sizer_left.Add(self.find, 0, flag=wx.EXPAND|wx.TOP, border=cw.ppis(3))

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND)
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnRemoveBtn(self, event):
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self._removed.append(self.list.pop(index))
            self.values.DeleteItem(index)
        self._item_selected()

    def OnOkBtn(self, event):
        def func(removedlist):
            cw.cwpy.play_sound("harvest")
            for removed in removedlist:
                if removed in cw.cwpy.breakpoint_table:
                    del cw.cwpy.breakpoint_table[removed]
            if cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.exec_func(func, self._removed)
        self.EndModal(wx.ID_OK)

    def OnItemSelected(self, event):
        self._item_selected()

    def get_removed(self):
        return self._removed

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _item_selected(self):
        indexes = self.get_selectedindexes()
        self.rmvbtn.Enable(bool(indexes))

#-------------------------------------------------------------------------------
#  ダイアログの部品
#-------------------------------------------------------------------------------

class AutoWidthListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, cid, size, style):
        wx.ListCtrl.__init__(self, parent, cid, size=size, style=style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class FindPanel(wx.Panel):
    def __init__(self, parent, values, item_selected, style=0):
        """検索パネル。
        """
        wx.Panel.__init__(self, parent, -1, style=style)
        self.values = values
        self.item_selected = item_selected

        self.title = wx.StaticText(self, -1, u"検索:")
        self.text = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self._color_not_found = wx.Colour(255, 128, 128)
        self._color_found = self.text.GetBackgroundColour()

        # up
        bmp = cw.cwpy.rsrc.buttons["UP_dbg"]
        self.findup = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)
        # down
        bmp = cw.cwpy.rsrc.buttons["DOWN_dbg"]
        self.finddown = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)

        self.findup.Disable()
        self.finddown.Disable()

        self._bind()
        self._do_layout()

    def _bind(self):
        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.text.Bind(wx.EVT_TEXT, self.OnTextChanged)
        self.findup.Bind(wx.EVT_BUTTON, self.OnFindUp)
        self.finddown.Bind(wx.EVT_BUTTON, self.OnFindDown)

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.title, 0, wx.ALIGN_CENTER, 0)
        sizer.Add(self.text, 1, wx.EXPAND, 0)
        sizer.Add(self.findup, 0, wx.EXPAND, 0)
        sizer.Add(self.finddown, 0, wx.EXPAND, 0)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def find_up(self):
        if not self.text.GetValue():
            return
        if not self.values.GetItemCount():
            self.text.SetBackgroundColour(self._color_not_found)
            self.text.Refresh()
            return
        startindex = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if startindex == -1:
            startindex = 0

        for index in xrange(self.values.GetItemCount()):
            self.values.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

        index = startindex
        text = self.text.GetValue().lower()
        while True:
            index -= 1
            if index < 0:
                index = self.values.GetItemCount()-1

            if self.values.GetItemText(index).lower().find(text) <> -1:
                self.values.SetItemState(index, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)
                self.values.EnsureVisible(index)
                self.text.SetBackgroundColour(self._color_found)
                self.text.Refresh()
                break

            if startindex == index:
                # 見つからなかった
                self.text.SetBackgroundColour(self._color_not_found)
                self.text.Refresh()
                break

        self.item_selected()

    def find_down(self):
        if not self.text.GetValue():
            return
        if not self.values.GetItemCount():
            self.text.SetBackgroundColour(self._color_not_found)
            self.text.Refresh()
            return
        startindex = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if startindex == -1:
            startindex = self.values.GetItemCount()-1

        for index in xrange(self.values.GetItemCount()):
            self.values.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

        index = startindex
        text = self.text.GetValue().lower()
        while True:
            index += 1
            if self.values.GetItemCount() <= index:
                index = 0

            if self.values.GetItemText(index).lower().find(text) <> -1:
                self.values.SetItemState(index, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED)
                self.values.EnsureVisible(index)
                self.text.SetBackgroundColour(self._color_found)
                self.text.Refresh()
                break

            if startindex == index:
                # 見つからなかった
                self.text.SetBackgroundColour(self._color_not_found)
                self.text.Refresh()
                break

        self.item_selected()

    def OnFindUp(self, event):
        self.find_up()

    def OnFindDown(self, event):
        self.find_down()

    def OnTextChanged(self, event):
        if self.text.GetValue() == "":
            self.text.SetBackgroundColour(self._color_found)
            self.text.Refresh()
            self.findup.Disable()
            self.finddown.Disable()
        else:
            self.findup.Enable()
            self.finddown.Enable()

    def OnEnter(self, event):
        if wx.GetKeyState(wx.WXK_SHIFT):
            self.find_up()
        else:
            self.find_down()


#-------------------------------------------------------------------------------
#  カード編集ダイアログ用ブックマーク整理ダイアログ
#-------------------------------------------------------------------------------

class EditBookmarksForCardEditDialog(wx.Dialog):

    def __init__(self, parent, bookmarks):
        wx.Dialog.__init__(self, parent, -1, u"ブックマーク",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        self.list = bookmarks[:]
        self._removed = []

        # リスト
        image = cw.cwpy.rsrc.dialogs["SUMMARY_dbg"]
        self.values = wx.ListCtrl(self, -1, size=cw.ppis((250, 300)), style=wx.LC_REPORT|wx.MULTIPLE|wx.BORDER)
        self.values.imglist = wx.ImageList(image.GetWidth(), image.GetHeight())
        self.values.imgidx = self.values.imglist.Add(image)
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"シナリオ名")
        self.values.SetColumnWidth(0, cw.ppis(100))
        self.values.InsertColumn(1, u"場所")
        self.values.SetColumnWidth(1, cw.ppis(150))

        # 名前の更新
        self.updatebtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"名前の更新")
        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_REMOVE, (-1, -1), name=u"削除")
        # 上へ
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_UP, (-1, -1), bmp=bmp)
        # 下へ
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_DOWN, (-1, -1), bmp=bmp)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        for fpath, name in self.list:
            index = self.values.GetItemCount()
            self.values.InsertStringItem(index, name)
            self.values.SetStringItem(index, 1, fpath)
            self.values.SetItemImage(index, self.values.imgidx)

        self._item_selected()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnUpdateBtn, self.updatebtn)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveBtn, self.rmvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDownBtn, self.downbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.values)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.values)

    def _do_layout(self):
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.values, 1, flag=wx.EXPAND)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.updatebtn, 0, wx.EXPAND)
        sizer_right.Add(self.rmvbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.upbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.Add(self.downbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnUpdateBtn(self, event):
        indexes = self.get_selectedindexes()
        if indexes:
            flag = wx.LIST_STATE_SELECTED
        else:
            flag = wx.LIST_STATE_DONTCARE

        self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        index = -1
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, flag)
            if index <= -1:
                break
            try:
                scdata = cw.scenariodb.get_scenario(self.values.GetItem(index, 1).GetText())
                self.values.SetStringItem(index, 0, scdata.name)
                self.list[index] = (self.list[index][0], scdata.name)
            except:
                self.values.SetStringItem(index, 0, u"*読込失敗*")
        self.SetCursor(wx.NullCursor)

    def OnRemoveBtn(self, event):
        while True:
            index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            self.list.pop(index)
            self.values.DeleteItem(index)
        self._item_selected()

    def OnUpBtn(self, event):
        index = -1
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= 0:
                break
            self._swap(index, index-1)
        self._item_selected()

    def OnDownBtn(self, event):
        indexes = self.get_selectedindexes()
        if not indexes or self.values.GetItemCount() <= indexes[-1] + 1:
            return

        indexes.reverse()
        for index in indexes:
            self._swap(index, index+1)
        self._item_selected()

    def _swap(self, index1, index2):
        self.list[index1], self.list[index2] = self.list[index2], self.list[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        def set_item(index, string, image):
            self.values.SetStringItem(index, 0, string[0])
            self.values.SetStringItem(index, 1, string[1])
            self.values.SetItemImage(index, image)
        string1 = self.values.GetItemText(index1), self.values.GetItem(index1, 1).GetText()
        string2 = self.values.GetItemText(index2), self.values.GetItem(index2, 1).GetText()
        image1 = self.values.GetItem(index1).GetImage()
        image2 = self.values.GetItem(index2).GetImage()
        set_item(index1, string2, image2)
        set_item(index2, string1, image1)

    def OnOkBtn(self, event):
        self.EndModal(wx.ID_OK)

    def OnItemSelected(self, event):
        self._item_selected()

    def get_selectedindexes(self):
        index = -1
        indexes = []
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            indexes.append(index)
        return indexes

    def _item_selected(self):
        self.updatebtn.Enable(bool(self.list))

        indexes = self.get_selectedindexes()
        if not indexes:
            self.rmvbtn.Enable(False)
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)
        else:
            self.rmvbtn.Enable(True)
            self.upbtn.Enable(0 < indexes[0])
            self.downbtn.Enable(indexes[-1] + 1 < self.values.GetItemCount())


def main():
    pass

if __name__ == "__main__":
    main()
