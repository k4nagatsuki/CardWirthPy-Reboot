#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wx.lib.mixins.listctrl as listmix

import cw


#-------------------------------------------------------------------------------
#  クーポン情報編集ダイアログ
#-------------------------------------------------------------------------------

class CouponEditDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの経歴の編集",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.list = cw.cwpy.get_pcards()

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

        # リスト
        self.values = wx.ListCtrl(self, -1, size=(250, -1), style=wx.LC_REPORT|wx.MULTIPLE)
#        self.values.imglist = wx.ImageList(16, 16)
#        self.values.imgidx_2 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS3"])
#        self.values.imgidx_1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS2"])
#        self.values.imgidx_0 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS1"])
#        self.values.imgidx_m1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS0"])
#        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"名称")
        self.values.InsertColumn(1, u"得点")
        self.values.SetColumnWidth(0, 170)
        self.values.SetColumnWidth(1, 50)

        # 対象者
        self.targets = [u"全員"]
        for pcard in self.list:
            self.targets.append(pcard.get_name())
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(0)
        self._select_target()
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)

        # 追加
        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_ADD, (-1, -1), name=u"追加")
        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_REMOVE, (-1, -1), name=u"削除")
        # 得点
        self.valbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"得点")
        # 上へ
        bmp = cw.cwpy.rsrc.buttons["UP"]
        self.upbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_UP, (-1, -1), bmp=bmp)
        # 下へ
        bmp = cw.cwpy.rsrc.buttons["DOWN"]
        self.downbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_DOWN, (-1, -1), bmp=bmp)

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        # 合計得点
        # TODO

        self._bind()
        self._do_layout()

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        # TODO

    def _do_layout(self):
        sizer = wx.GridBagSizer()

        sizer_values = wx.BoxSizer(wx.VERTICAL)
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
        sizer_values.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=5)
        sizer_values.Add(self.values, 1, flag=wx.EXPAND)

        sizer.Add(sizer_values, pos=(0, 0), span=(8, 1), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(5)

        sizer.Add(self.addbtn, pos=(0, 1), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.rmvbtn, pos=(1, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.valbtn, pos=(2, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.upbtn, pos=(3, 1), flag=wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=5)
        sizer.Add(self.downbtn, pos=(4, 1), flag=wx.RIGHT|wx.EXPAND, border=5)
        sizer.SetEmptyCellSize((0, 100))
        sizer.Add(self.okbtn, pos=(6, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.cnclbtn, pos=(7, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def OnSelectTarget(self, event):
        self._select_target()

    def _add_coupon(self, name, value):
        if name.startswith(u"＠"):
            return
        if name in self.syscoupons:
            return
        index = self.values.GetItemCount()
        self.values.InsertStringItem(index, name)
        self.values.SetStringItem(index, 1, value)

    def _select_target(self):
        self.values.DeleteAllItems()
        index = self.target.GetSelection()
        if index == 0:
            coupons = set()
            for pcard in self.list:
                for e in pcard.data.getfind("Property/Coupons"):
                    name = e.text
                    if name in coupons:
                        continue
                    coupons.add(name)
                    value = e.get("value")
                    self._add_coupon(name, value)

        else:
            pcard = self.list[index-1]
            for e in pcard.data.getfind("Property/Coupons"):
                name = e.text
                value = e.get("value")
                self._add_coupon(name, value)

class CouponListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    pass


#-------------------------------------------------------------------------------
#  ゴシップ・終了印情報編集ダイアログ
#-------------------------------------------------------------------------------
