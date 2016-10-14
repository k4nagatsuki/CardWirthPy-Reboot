#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw

#-------------------------------------------------------------------------------
#  デバッグ情報ダイアログ
#-------------------------------------------------------------------------------

class DebugLogDialog(wx.Dialog):

    def __init__(self, parent, sname, debuglog):
        """集計したデバッグ情報をリッチテキストで表示する。"""
        wx.Dialog.__init__(self, parent, -1, u"「%s」のプレイ結果" % (sname),
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = True
        self.plain_text = [u"「%s」のプレイ結果" % (sname), u"========================================", ""]

        self.text = cw.util.CWPyRichTextCtrl(self, -1, size=cw.ppis((400, 380)))
        self.text.SetEditable(False)

        # 連れ込み
        for name in debuglog.friend:
            s = u"「%s」を宿帳に登録します。" % (name)
            self.text.WriteBitmap(cw.cwpy.rsrc.debugs["FRIEND"])
            self.text.WriteText(s)
            self.text.Newline()
            self.plain_text.append(s)

        # 所持金
        if self.text.GetValue():
            self.text.Newline()
            self.plain_text.append(u"")

        if debuglog.money[0] < debuglog.money[1]:
            v = debuglog.money[1] - debuglog.money[0]
            v1 = cw.cwpy.msgs["currency"] % (v)
            v2 = cw.cwpy.msgs["currency"] % (debuglog.money[0])
            v3 = cw.cwpy.msgs["currency"] % (debuglog.money[1])
            self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_GET_MONEY"])
            s = u"所持金が %s 増加しています: %s → %s" % (v1, v2, v3)
        elif debuglog.money[1] < debuglog.money[0]:
            v = debuglog.money[0] - debuglog.money[1]
            v1 = cw.cwpy.msgs["currency"] % (v)
            v2 = cw.cwpy.msgs["currency"] % (debuglog.money[0])
            v3 = cw.cwpy.msgs["currency"] % (debuglog.money[1])
            self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_LOSE_MONEY"])
            s = u"所持金が %s 減少しています: %s → %s" % (v1, v2, v3)
        else:
            s = u"所持金に変更はありません。"
        self.text.WriteText(s)
        self.text.Newline()
        self.plain_text.append(s)

        # ゴシップ
        if debuglog.gossip:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for gossip in cw.util.sorted_by_attr(filter(lambda a: a[1], debuglog.gossip)):
                self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_GET_GOSSIP"])
                s = u"ゴシップ「%s」を追加しました。" % (gossip[0])
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)
            for gossip in cw.util.sorted_by_attr(filter(lambda a: not a[1], debuglog.gossip)):
                self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_LOSE_GOSSIP"])
                s = u"ゴシップ「%s」を削除しました。" % (gossip[0])
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)

        # 終了印
        if debuglog.compstamp:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for compstamp in cw.util.sorted_by_attr(filter(lambda a: a[1], debuglog.compstamp)):
                self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_GET_COMPLETESTAMP"])
                s = u"終了印「%s」を追加しました。" % (compstamp[0])
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)
            for compstamp in cw.util.sorted_by_attr(filter(lambda a: not a[1], debuglog.compstamp)):
                self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_LOSE_COMPLETESTAMP"])
                s = u"終了印「%s」を削除しました。" % (compstamp[0])
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)

        # 獲得カード
        if debuglog.got_card:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for type in ("SkillCard", "ItemCard", "BeastCard"):
                for key in cw.util.sorted_by_attr(filter(lambda a: a[0] == type, debuglog.got_card.iterkeys())):
                    _type, name, _desc, premium = key
                    num = debuglog.got_card[key]
                    if type == "SkillCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_GET_SKILL"]
                        typename = u"特殊技能"
                    elif type == "ItemCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_GET_ITEM"]
                        typename = u"アイテム"
                    elif type == "BeastCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_GET_BEAST"]
                        typename = u"召喚獣"
                    else:
                        assert False
                    self.text.WriteBitmap(bmp)
                    if premium == "Normal":
                        s = u"%s「%s」を%s枚獲得しました。" % (typename, name, num)
                        self.text.WriteText(s)
                        self.text.Newline()
                        self.plain_text.append(s)
                    else:
                        if premium == "Premium":
                            picon = cw.cwpy.rsrc.dialogs["PREMIER_ICON_dbg"]
                            ptext = u"プレミア"
                        elif premium == "Rare":
                            picon = cw.cwpy.rsrc.dialogs["RARE_ICON_dbg"]
                            ptext = u"レア"
                        else:
                            assert False
                        self.text.WriteText(u"%s「%s" % (typename, name))
                        self.text.WriteBitmap(picon)
                        self.text.WriteText(u"」を%s枚獲得しました。" % (num))
                        self.text.Newline()

                        s = u"%s「%s(%s)」を%s枚獲得しました。" % (typename, name, ptext, num)
                        self.plain_text.append(s)

        # 喪失カード
        if debuglog.lost_card:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for type in ("SkillCard", "ItemCard", "BeastCard"):
                for key in cw.util.sorted_by_attr(filter(lambda a: a[0] == type, debuglog.lost_card.iterkeys())):
                    _type, name, _desc, _premium = key
                    num = debuglog.lost_card[key]
                    if type == "SkillCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_LOSE_SKILL"]
                        typename = u"特殊技能"
                    elif type == "ItemCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_LOSE_ITEM"]
                        typename = u"アイテム"
                    elif type == "BeastCard":
                        bmp = cw.cwpy.rsrc.debugs["EVT_LOSE_BEAST"]
                        typename = u"召喚獣"
                    else:
                        assert False
                    self.text.WriteBitmap(bmp)
                    s = u"%s「%s」を%s枚喪失しました。" % (typename, name, num)
                    self.text.WriteText(s)
                    self.text.Newline()
                    self.plain_text.append(s)

        # PCの消去・称号の変更
        if debuglog.lost_player or debuglog.player:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for name, album in debuglog.lost_player:
                if album:
                    s = u"%s は消去され、アルバムに掲載されました。" % (name)
                else:
                    s = u"%s は消去されました(アルバム不掲載)。" % (name)
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)

            for name, got_coupons, lost_coupons in debuglog.player:
                got_coupons = filter(lambda a: not a[0].startswith(u"＠"), got_coupons)
                lost_coupons = filter(lambda a: not a[0].startswith(u"＠"), lost_coupons)
                if got_coupons or lost_coupons:
                    s = u"%s の称号が以下のように変更されています。" % (name)
                    self.text.WriteText(s)
                    self.text.Newline()
                    self.plain_text.append(s)
                    self.text.BeginLeftIndent(cw.ppis(50))
                    for coupon, value in got_coupons:
                        if value < 0:
                            bmp = cw.cwpy.rsrc.debugs["COUPON_MINUS"]
                            value = str(value)
                        elif value == 0:
                            bmp = cw.cwpy.rsrc.debugs["COUPON_ZERO"]
                            value = "+%s" % (value)
                        elif value == 1:
                            bmp = cw.cwpy.rsrc.debugs["COUPON_PLUS"]
                            value = "+%s" % (value)
                        else:
                            bmp = cw.cwpy.rsrc.debugs["COUPON"]
                            value = "+%s" % (value)
                        self.text.WriteBitmap(bmp)
                        s = u"「%s(%s)」を獲得" % (coupon, value)
                        self.text.WriteText(s)
                        self.text.Newline()
                        self.plain_text.append("    * " + s)
                    for coupon, _value in lost_coupons:
                        self.text.WriteBitmap(cw.cwpy.rsrc.debugs["EVT_LOSE_COUPON"])
                        s = u"「%s」を喪失" % (coupon)
                        self.text.WriteText(s)
                        self.text.Newline()
                        self.plain_text.append("    * " + s)
                    self.text.EndLeftIndent()
                else:
                    s = u"%s の称号に変更はありません。" % (name)
                    self.text.WriteText(s)
                    self.text.Newline()
                    self.plain_text.append(s)

        # JPDCイメージ
        if debuglog.jpdc_image:
            if self.text.GetValue():
                self.text.Newline()
                self.plain_text.append(u"")
            for fname in debuglog.jpdc_image:
                self.text.WriteBitmap(cw.cwpy.rsrc.debugs["JPDCIMAGE"])
                s = u"JPDCイメージ「%s」を保存しました。" % (fname)
                self.text.WriteText(s)
                self.text.Newline()
                self.plain_text.append(s)

        self.writetext = wx.CheckBox(self, -1, u"「DebugInfo.txt」に保存する")
        self.writetext.SetValue(True)

        self.plain_text.append(u"")
        self.plain_text = u"\n".join(self.plain_text)

        # 決定
        self.okbtn = wx.Button(self, wx.ID_OK, u"&OK")

        self._bind()
        self._do_layout()

    def _bind(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.okbtn)

    def OnClose(self, event):
        if self.writetext.GetValue():
            try:
                with open(u"DebugInfo.txt", "w") as f:
                    f.write(self.plain_text.encode("utf-8"))
                    f.close()
            except:
                cw.util.print_ex()
        self.Destroy()

    def _do_layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.writetext, 0, wx.ALIGN_CENTER|wx.RIGHT, border=cw.ppis(5))
        hsizer.AddStretchSpacer(1)
        hsizer.Add(self.okbtn, 0, wx.ALIGN_CENTER)

        sizer.Add(self.text, 1, wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(cw.ppis((0, 5)), 0, 0, 0)
        sizer.Add(hsizer, 0, wx.EXPAND|wx.RIGHT|wx.LEFT|wx.BOTTOM, border=cw.ppis(5))
        sizer.Add(cw.ppis((0, 10)), 0, 0, 0)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

class DebugLog(object):
    def __init__(self):
        """シナリオプレイ結果を通知するために各種情報をまとめる。"""
        self.friend = []
        self.lost_player = []
        self.player = []
        self.got_card = {}
        self.lost_card = {}
        self.money = (0, 0)
        self.compstamp = []
        self.gossip = []
        self.jpdc_image = []

    def add_friend(self, fcard):
        """連れ込む同行キャストの情報を追加する。"""
        self.friend.append(fcard.name)

    def add_lostplayer(self, ccard):
        """対象消去されたPCの情報を追加する。"""
        self.lost_player.append((ccard.name, not ccard.has_coupon(u"＿消滅予約")))

    def add_player(self, pcard, got_coupons, lost_coupons):
        """PCの情報を追加する。"""
        self.player.append((pcard.name, got_coupons, lost_coupons))

    def set_money(self, before, after):
        """所持金の情報を設定する。"""
        self.money = (before, after)

    def add_gotcard(self, type, name, desc, scenario, author, premium):
        """入手したカードの情報を追加する。"""
        key = (type, name, desc, premium)
        self.got_card[key] = self.got_card.get(key, 0) + 1

    def add_lostcard(self, type, name, desc, scenario, author, premium):
        """喪失したカードの情報を追加する。"""
        key = (type, name, desc, premium)
        self.lost_card[key] = self.lost_card.get(key, 0) + 1

    def add_compstamp(self, compstamp, get):
        """終了印の情報を追加する。"""
        self.compstamp.append((compstamp, get))

    def add_gossip(self, gossip, get):
        """ゴシップの情報を追加する。"""
        self.gossip.append((gossip, get))

    def add_jpdcimage(self, fname):
        """保存されたJPDCイメージの情報を追加する。"""
        self.jpdc_image.append(fname)
