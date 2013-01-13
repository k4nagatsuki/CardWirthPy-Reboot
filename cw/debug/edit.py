#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wx.lib.mixins.listctrl as listmix

import cw

#-------------------------------------------------------------------------------
#  状態編集ダイアログ
#-------------------------------------------------------------------------------

class StatusEditDialog(wx.Dialog):

    def __init__(self, parent, selected=-1):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの状態の編集",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.SetDoubleBuffered(True)

        self.pcards = cw.cwpy.get_pcards()

        self.statuses = []
        self.statuses_backup = []
        for pcard in self.pcards:
            self.statuses.append(Status(pcard))
            self.statuses_backup.append(Status(pcard))

        self.life      = StatusButton(self, 0, self._is_dead, size=(45, 45))
        self.poison    = StatusButton(self, 1, self._is_dead, size=(45, 45))
        self.paralyze  = StatusButton(self, 2, self._is_dead, size=(45, 45))
        self.mentality = StatusButton(self, 3, self._is_dead, size=(45, 60))
        self.bind      = StatusButton(self, 4, self._is_dead, size=(45, 45))
        self.silence   = StatusButton(self, 5, self._is_dead, size=(45, 45))
        self.faceup    = StatusButton(self, 6, self._is_dead, size=(45, 45))
        self.antimagic = StatusButton(self, 7, self._is_dead, size=(45, 45))
        self.action    = StatusButton(self, 8, self._is_dead, size=(45, 60))
        self.avoid     = StatusButton(self, 9, self._is_dead, size=(45, 60))
        self.resist    = StatusButton(self, 10, self._is_dead, size=(45, 60))
        self.defense   = StatusButton(self, 11, self._is_dead, size=(45, 60))
        self.statusbtns = [self.life, self.poison, self.paralyze,
                           self.mentality, self.bind, self.silence,
                           self.faceup, self.antimagic, self.action,
                           self.avoid, self.resist, self.defense]

        # 対象者
        self.targets = [u"全員"]
        for pcard in self.pcards:
            self.targets.append(pcard.get_name())
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(max(selected, -1) + 1)
        # smallleft
        bmp = cw.cwpy.rsrc.buttons["LSMALL"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (20, 20), bmp=bmp)

        # 全快
        self.rcvbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"全快")
        # 復旧
        self.restorebtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), name=u"復旧")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

        self._bind()
        self._do_layout()

        self._select_target()

    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.OnSelectTarget, self.target)
        self.Bind(wx.EVT_BUTTON, self.OnLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnFullRecovery, self.rcvbtn)
        self.Bind(wx.EVT_BUTTON, self.OnRestore, self.restorebtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)

        self.Bind(wx.EVT_BUTTON, self.OnLife, self.life)
        self.Bind(wx.EVT_BUTTON, self.OnPoison, self.poison)
        self.Bind(wx.EVT_BUTTON, self.OnParalyze, self.paralyze)
        self.Bind(wx.EVT_BUTTON, self.OnMentality, self.mentality)
        self.Bind(wx.EVT_BUTTON, self.OnBind, self.bind)
        self.Bind(wx.EVT_BUTTON, self.OnSilence, self.silence)
        self.Bind(wx.EVT_BUTTON, self.OnFaceUp, self.faceup)
        self.Bind(wx.EVT_BUTTON, self.OnAntiMagic, self.antimagic)
        self.Bind(wx.EVT_BUTTON, self.OnAction, self.action)
        self.Bind(wx.EVT_BUTTON, self.OnAvoid, self.avoid)
        self.Bind(wx.EVT_BUTTON, self.OnResist, self.resist)
        self.Bind(wx.EVT_BUTTON, self.OnDefense, self.defense)

    def _do_layout(self):
        sizer = wx.GridBagSizer()

        sizer_status = wx.GridBagSizer()
        sizer_status.Add(self.life, pos=(0, 0), flag=wx.ALL, border=5)
        sizer_status.Add(self.poison, pos=(0, 1), flag=wx.ALL, border=5)
        sizer_status.Add(self.paralyze, pos=(0, 2), flag=wx.ALL, border=5)
        sizer_status.Add(self.mentality, pos=(1, 0), flag=wx.ALL, border=5)
        sizer_status.Add(self.bind, pos=(2, 0), flag=wx.ALL, border=5)
        sizer_status.Add(self.silence, pos=(2, 1), flag=wx.ALL, border=5)
        sizer_status.Add(self.faceup, pos=(2, 2), flag=wx.ALL, border=5)
        sizer_status.Add(self.antimagic, pos=(2, 3), flag=wx.ALL, border=5)
        sizer_status.Add(self.action, pos=(3, 0), flag=wx.ALL, border=5)
        sizer_status.Add(self.avoid, pos=(3, 1), flag=wx.ALL, border=5)
        sizer_status.Add(self.resist, pos=(3, 2), flag=wx.ALL, border=5)
        sizer_status.Add(self.defense, pos=(3, 3), flag=wx.ALL, border=5)

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
        sizer_left.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=5)
        sizer_left.Add(sizer_status, 1, flag=wx.EXPAND)

        sizer.Add(sizer_left, pos=(0, 0), span=(5, 1), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(2)

        sizer.Add(self.rcvbtn, pos=(0, 1), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.restorebtn, pos=(1, 1), flag=wx.RIGHT, border=5)
        sizer.SetEmptyCellSize((0, 170))
        sizer.Add(self.okbtn, pos=(3, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.cnclbtn, pos=(4, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    @staticmethod
    def _value(oldvalue, newvalue, force=True, defvalue=None):
        if not force and oldvalue <> newvalue:
            return defvalue
        return newvalue

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

    def OnFullRecovery(self, event):
        for status in self._get_statuses():
            status.life = 100
            status.mentality = "Normal"
            status.mentality_dur = 0
            status.paralyze = 0
            status.poison = 0
            status.bind = 0
            status.silence = 0
            status.faceup = 0
            status.antimagic = 0
            status.enhance_act = 0
            status.enhance_act_dur = 0
            status.enhance_avo = 0
            status.enhance_avo_dur = 0
            status.enhance_res = 0
            status.enhance_res_dur = 0
            status.enhance_def = 0
            status.enhance_def_dur = 0
        self._update_status()

    def OnRestore(self, event):
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            for i, status in enumerate(self.statuses_backup):
                self.statuses[i] = Status(status)
        else:
            # 誰か一人
            self.statuses[cindex-1] = Status(self.statuses_backup[cindex-1])
        self._update_status()

    def OnOkBtn(self, event):
        pass # TODO

    def OnLife(self, event):
        value = 100
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.life, (i == 0), 100)

        dlg = cw.dialog.edit.NumberEditor(self, u"現生命点(%)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.life = dlg.value
            self._update_status()

    def OnPoison(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.poison, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"毒性値(中毒)", value, 0, 40)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.poison = dlg.value
            self._update_status()

    def OnParalyze(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.paralyze, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"毒性値(麻痺)", value, 0, 40)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.paralyze = dlg.value
            self._update_status()

    def OnMentality(self, event):
        pass # TODO

    def OnBind(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.bind, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"継続時間(呪縛)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.bind = dlg.value
            self._update_status()

    def OnSilence(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.silence, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"継続時間(沈黙)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.silence = dlg.value
            self._update_status()

    def OnFaceUp(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.faceup, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"継続時間(暴露)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.faceup = dlg.value
            self._update_status()

    def OnAntiMagic(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.antimagic, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditor(self, u"継続時間(魔法無効)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.antimagic = dlg.value
            self._update_status()

    def OnAction(self, event):
        pass # TODO

    def OnAvoid(self, event):
        pass # TODO

    def OnResist(self, event):
        pass # TODO

    def OnDefense(self, event):
        pass # TODO

    def _select_target(self):
        self._update_status()

    def _is_dead(self):
        for status in self._get_statuses():
            if not status.is_dead():
                return False
        return True

    def _update_status(self):
        for i, status in enumerate(self._get_statuses()):
            force = (i == 0)
            self.life.value         = self._value(self.life.value, status.life, force)
            self.poison.value       = self._value(self.poison.value, status.poison, force)
            self.paralyze.value     = self._value(self.paralyze.value, status.paralyze, force)
            self.mentality.value    = self._value(self.mentality.value, status.mentality, force, "Normal")
            self.mentality.duration = self._value(self.mentality.duration, status.mentality_dur, force)
            self.bind.duration      = self._value(self.bind.duration, status.bind, force)
            self.silence.duration   = self._value(self.silence.duration, status.silence, force)
            self.faceup.duration    = self._value(self.faceup.duration, status.faceup, force)
            self.antimagic.duration = self._value(self.antimagic.duration, status.antimagic, force)
            self.action.value       = self._value(self.action.value, status.enhance_act, force)
            self.action.duration    = self._value(self.action.duration, status.enhance_act_dur, force)
            self.avoid.value        = self._value(self.avoid.value, status.enhance_avo, force)
            self.avoid.duration     = self._value(self.avoid.duration, status.enhance_avo_dur, force)
            self.resist.value       = self._value(self.resist.value, status.enhance_res, force)
            self.resist.duration    = self._value(self.resist.duration, status.enhance_res_dur, force)
            self.defense.value      = self._value(self.defense.value, status.enhance_def, force)
            self.defense.duration   = self._value(self.defense.duration, status.enhance_def_dur, force)

        for btn in self.statusbtns:
            btn.draw(True)

    def _get_statuses(self):
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            return self.statuses
        else:
            # 誰か一人
            return [self.statuses[cindex-1]]

class Status(object):
    def __init__(self, pcard):
        # 現在ライフ・最大ライフ
        if hasattr(pcard, "maxlife"):
            self.life = 100 * pcard.life / pcard.maxlife
        else:
            self.life = pcard.life
        # 精神状態
        self.mentality = pcard.mentality
        self.mentality_dur = pcard.mentality_dur
        # 麻痺値
        self.paralyze = pcard.paralyze
        # 中毒値
        self.poison = pcard.poison
        # 束縛時間値
        self.bind = pcard.bind
        # 沈黙時間値
        self.silence = pcard.silence
        # 暴露時間値
        self.faceup = pcard.faceup
        # 魔法無効時間値
        self.antimagic = pcard.antimagic
        # 行動力強化値
        self.enhance_act = pcard.enhance_act
        self.enhance_act_dur = pcard.enhance_act_dur
        # 回避力強化値
        self.enhance_avo = pcard.enhance_avo
        self.enhance_avo_dur = pcard.enhance_avo_dur
        # 抵抗力強化値
        self.enhance_res = pcard.enhance_res
        self.enhance_res_dur = pcard.enhance_res_dur
        # 防御力強化値
        self.enhance_def = pcard.enhance_def
        self.enhance_def_dur = pcard.enhance_def_dur

    def is_dead(self):
        return self.life == 0 or 0 < self.paralyze

class StatusButton(wx.BitmapButton):

    def __init__(self, parent, mode, is_dead, size):
        """
        mode: 0=ライフ, 1=中毒, 2=麻痺, 3=精神状態,
              4=呪縛, 5=沈黙, 6=暴露, 7=魔法無効,
              8=行動力, 9=回避力, 10=抵抗力, 11=防御力
        is_dead: 死亡状態かを返す関数
        """
        wx.BitmapButton.__init__(self, parent, -1, size=size)

        self.mode = mode
        self.is_dead = is_dead

        if self.mode == 3:
            self.value = "Normal"
        else:
            self.value = 0
        self.duration = 0

    def draw(self, update=False):

        if not update:
            return

        image = None
        self.text1 = ""
        self.text2 = ""
        colour = None
        enable = False
        if self.mode == 0:
            # ライフ
            image = cw.cwpy.rsrc.statuses["LIFE"]
            if not self.value is None:
                self.text1 = "%s%%" % (self.value)
                if 0 >= self.value:
                    colour = wx.Colour(0, 0, 128)
                elif 20 > self.value:
                    colour = wx.Colour(127, 0, 0)
                elif 100 > self.value:
                    colour = wx.Colour(0, 153, 187)
                else:
                    colour = wx.Colour(192, 192, 192)
            else:
                colour = wx.Colour(192, 192, 192)
            enable = True

        elif self.mode == 1:
            # 中毒
            image = cw.cwpy.rsrc.statuses["BODY0"]
        elif self.mode == 2:
            # 麻痺
            image = cw.cwpy.rsrc.statuses["BODY1"]
        elif self.mode == 3:
            # 精神状態
            if self.value is None or self.value == "Normal":
                # 正常
                image = cw.cwpy.rsrc.statuses["MIND0"]
            elif self.value == "Sleep":
                # 眠り
                image = cw.cwpy.rsrc.statuses["MIND1"]
                self.text1 = u"眠り"
            elif self.value == "Confuse":
                # 混乱
                image = cw.cwpy.rsrc.statuses["MIND2"]
                self.text1 = u"混乱"
            elif self.value == "Overheat":
                # 激高
                image = cw.cwpy.rsrc.statuses["MIND3"]
                self.text1 = u"激高"
            elif self.value == "Brave":
                # 勇猛
                image = cw.cwpy.rsrc.statuses["MIND4"]
                self.text1 = u"勇猛"
            elif self.value == "Panic":
                # 恐慌
                image = cw.cwpy.rsrc.statuses["MIND5"]
                self.text1 = u"恐慌"

            if not self.duration is None and 0 < self.duration:
                self.text2 = "%sr"
                if not self.value is None and not self.is_dead():
                    enable = True
        elif self.mode == 4:
            # 呪縛
            image = cw.cwpy.rsrc.statuses["MAGIC0"]
        elif self.mode == 5:
            # 沈黙
            image = cw.cwpy.rsrc.statuses["MAGIC1"]
        elif self.mode == 6:
            # 暴露
            image = cw.cwpy.rsrc.statuses["MAGIC2"]
        elif self.mode == 7:
            # 魔法無効
            image = cw.cwpy.rsrc.statuses["MAGIC3"]
        elif self.mode == 8:
            # 行動力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.statuses["UP0"]
            else:
                image = cw.cwpy.rsrc.statuses["DOWN0"]
        elif self.mode == 9:
            # 回避力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.statuses["UP1"]
            else:
                image = cw.cwpy.rsrc.statuses["DOWN1"]
        elif self.mode == 10:
            # 抵抗力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.statuses["UP2"]
            else:
                image = cw.cwpy.rsrc.statuses["DOWN2"]
        elif self.mode == 11:
            # 防御力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.statuses["UP3"]
            else:
                image = cw.cwpy.rsrc.statuses["DOWN3"]
        assert not image is None, self.mode

        if self.mode == 1 or self.mode == 2:
            # 肉体ステータス
            if not self.value is None and 0 < self.value:
                self.text1 = "Lv%s" % (self.value)
                enable = True

        if self.mode == 4 or self.mode == 5 or self.mode == 6 or self.mode == 7:
            # 魔法効果
            if not self.duration is None and 0 < self.duration:
                self.text1 = "%sr" % (self.duration)
                if 0 < self.duration and not self.is_dead():
                    enable = True

        elif self.mode == 8 or self.mode == 9 or self.mode == 10 or self.mode == 11:
            # 能力ボーナス・ペナルティ
            if not self.value is None:
                if self.value > 0:
                    self.text1 = "+%s" % (self.value)
                elif 0 > self.value:
                    self.text1 = "%s" % (self.value)

            if not self.duration is None and 0 < self.duration:
                self.text2 = "%sr" % (self.duration)

            if not self.value is None and not self.duration is None:
                if 0 < self.value and 0 < self.duration and not self.is_dead():
                    enable = True

            colour = wx.Colour(192, 192, 192)
            if not self.value is None:
                if 7 <= self.value:
                    colour = wx.Colour(175, 0, 0)
                elif 4 <= self.value:
                    colour = wx.Colour(127, 0, 0)
                elif 1 <= self.value:
                    colour = wx.Colour(79, 0, 0)
                elif -7 >= self.value:
                    colour = wx.Colour(0, 0, 85)
                elif -4 >= self.value:
                    colour = wx.Colour(0, 0, 160)
                elif -1 >= self.value:
                    colour = wx.Colour(0, 0, 187)

        self.image = cw.image.conv2wxbmp(image)

        if colour:
            # 背景色の変更
            w = self.image.GetWidth()
            h = self.image.GetHeight()
            canvas = wx.EmptyBitmapRGBA(w, h)
            bdc = wx.MemoryDC(canvas)
            bdc.BeginDrawing()
            bdc.SetPen(wx.Pen(colour))
            bdc.SetBrush(wx.Brush(colour))
            bdc.DrawRectangle(0, 0, w, h)
            bdc.DrawBitmap(self.image, 0, 0)
            bdc.EndDrawing()
            self.image = canvas

        # 半透明化
        # FIXME: ここでSetAlphaData()を呼ばなければ
        #        色がおかしくなるため、enable=Trueの
        #        時も設定を行なっている
        w = self.image.GetWidth()
        h = self.image.GetHeight()
        image = self.image.ConvertToImage()
        if not enable:
            image.SetAlphaData(chr(128) * (w*h))
        else:
            image.SetAlphaData(chr(255) * (w*h))
        self.image = image.ConvertToBitmap()

        csize = self.GetClientSize()

        canvas = wx.EmptyBitmap(csize[0], csize[1])

        dc = wx.MemoryDC(canvas)
        dc.BeginDrawing()
        colour = self.GetBackgroundColour()
        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour))
        dc.DrawRectangle(0, 0, canvas.GetWidth(), canvas.GetHeight())
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("gothic", size=8))

        SPACER = 4
        height = self.image.GetHeight()
        if self.text1:
            size1 = dc.GetTextExtent(self.text1)
            height += SPACER + size1[1]
        if self.text2:
            size2 = dc.GetTextExtent(self.text2)
            height += SPACER + size2[1]

        y = (csize[1] - height) / 2

        x = (csize[0] - self.image.GetWidth()) / 2
        dc.DrawBitmap(self.image, x, y)
        y += self.image.GetHeight() + SPACER

        if self.text1:
            x = (csize[0] - size1[0]) / 2
            dc.DrawText(self.text1, x, y)
            y += size1[1] + SPACER
        if self.text2:
            x = (csize[0] - size2[0]) / 2
            dc.DrawText(self.text2, x, y)
            y += size2[1] + SPACER

        dc.EndDrawing()

        canvas = canvas.ConvertToImage()
        canvas.SetMaskColour(colour[0], colour[1], colour[2])

        self.SetBitmapLabel(canvas.ConvertToBitmap())

#-------------------------------------------------------------------------------
#  クーポン情報編集ダイアログ
#-------------------------------------------------------------------------------

class CouponEditDialog(wx.Dialog):

    def __init__(self, parent, selected=-1):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの経歴の編集",
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)

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
            list = []
            for e in pcard.data.getfind("Property/Coupons"):
                name = e.text
                if name.startswith(u"＠") or name in self.syscoupons:
                    continue
                value = e.get("value")
                list.append((name, int(value)))
            list.reverse()
            self.coupons.append(list)

        # リスト
        self.values = EditableListCtrl(self, -1, size=(250, -1), style=wx.LC_REPORT|wx.MULTIPLE)
        self.values.imglist = wx.ImageList(14, 14)
        self.values.imgidx_2 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS3"])
        self.values.imgidx_1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS2"])
        self.values.imgidx_0 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS1"])
        self.values.imgidx_m1 = self.values.imglist.Add(cw.cwpy.rsrc.dialogs["STATUS0"])
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"名称")
        self.values.InsertColumn(1, u"得点")
        self.values.SetColumnWidth(0, 170)
        self.values.SetColumnWidth(1, 50)
        self.values.setResizeColumn(0)

        # 対象者
        self.targets = [u"全員"]
        for pcard in self.pcards:
            self.targets.append(pcard.get_name())
        self.target = wx.ComboBox(self, -1, choices=self.targets, style=wx.CB_READONLY)
        self.target.Select(max(selected, -1) + 1)
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
        self.total = wx.StaticText(self, -1, "", style=wx.ALIGN_RIGHT)

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
        self.Bind(wx.EVT_BUTTON, self.OnUpBtn, self.upbtn)
        self.Bind(wx.EVT_BUTTON, self.OnDownBtn, self.downbtn)
        self.Bind(wx.EVT_BUTTON, self.OnOkBtn, self.okbtn)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit, self.values)

    def _do_layout(self):
        sizer = wx.GridBagSizer()

        sizer_values = wx.BoxSizer(wx.VERTICAL)
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
        sizer_values.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=5)
        sizer_values.Add(self.values, 1, flag=wx.EXPAND)
        sizer_values.Add(self.total, 0, flag=wx.EXPAND|wx.TOP, border=5)

        sizer.Add(sizer_values, pos=(0, 0), span=(8, 1), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(5)

        sizer.Add(self.addbtn, pos=(0, 1), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.rmvbtn, pos=(1, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.valbtn, pos=(2, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.upbtn, pos=(3, 1), flag=wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=5)
        sizer.Add(self.downbtn, pos=(4, 1), flag=wx.RIGHT|wx.EXPAND, border=5)
        sizer.SetEmptyCellSize((0, 150))
        sizer.Add(self.okbtn, pos=(6, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.cnclbtn, pos=(7, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)

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
        self._item_selected()

    def OnAddBtn(self, event):
        names = set()
        for i in range(self.values.GetItemCount()):
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
            for list in self.coupons:
                list.insert(0, (name, 0))
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
            for list in self.coupons:
                for i, coupon in enumerate(list):
                    if coupon[0] == name:
                        list.pop(i)
                        break
        else:
            # 誰か一人
            self.coupons[cindex-1].pop(index)
        self.values.DeleteItem(index)

    def OnValueBtn(self, event):
        value = None
        index = self.values.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index <= -1:
            return
        value = int(self.values.GetItem(index, 1).GetText())

        dlg = cw.dialog.edit.NumberEditor(self, u"得点の設定", value, -9, 9)
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
        list = self.coupons[cindex-1]
        list[index1], list[index2] = list[index2], list[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        def set_item(index):
            self.values.SetStringItem(index, 0, list[index][0])
            self.values.SetStringItem(index, 1, str(list[index][1]))
            self.values.SetItemImage(index, self._get_valueimage(list[index][1]))
        set_item(index1)
        set_item(index2)

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
        cw.cwpy.sounds["harvest"].play()
        for i, pcard in enumerate(self.pcards):
            list = self.coupons[i]
            # システムクーポン以外を一旦除去
            for name in pcard.get_coupons():
                if not (name.startswith(u"＠") or name in self.syscoupons):
                    cdata.remove_coupon(name)
            # クーポン追加
            list.reverse()
            for coupon in list:
                pcard.set_coupon(coupon[0], coupon[1])
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

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
        total = 0
        if index == 0:
            coupons = set()
            for list in self.coupons:
                for coupon in list:
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

    def _item_selected(self):
        indexes = self.get_selectedindexes()
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

        index = -1
        total = 0
        while True:
            index = self.values.GetNextItem(index, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if index <= -1:
                break
            total += int(self.values.GetItem(index, 1).GetText())

        if indexes:
            self.total.SetLabel(u"選択中の合計: %s点" % (total))
        else:
            self.total.SetLabel(u"合計: %s点" % (total))
        self.Layout()

    def _set_name(self, index, oldname, newname):
        self.values.SetStringItem(index, 0, newname)
        cindex = self.target.GetSelection()
        if cindex == 0:
            # 全員
            for list in self.coupons:
                for i, coupon in enumerate(list):
                    if coupon[0] == oldname:
                        list = (newname, coupon[1])
                        break
        else:
            # 誰か一人
            list = self.coupons[cindex-1]
            list[index] = (newname, list[index][1])

    def _set_value(self, index, value):
        self.values.SetStringItem(index, 1, str(value))
        self.values.SetItemImage(index, self._get_valueimage(value))
        cindex = self.target.GetSelection()
        name = self.values.GetItem(index, 0).GetText()
        if cindex == 0:
            # 全員
            for list in self.coupons:
                for i, coupon in enumerate(list):
                    if coupon[0] == name:
                        list[i] = (name, value)
                        break
        else:
            # 誰か一人
            self.coupons[cindex-1][index] = (name, value)

#-------------------------------------------------------------------------------
#  ゴシップ・終了印情報編集ダイアログ
#-------------------------------------------------------------------------------

class ListEditDialog(wx.Dialog):

    def __init__(self, parent, title, list, image):
        wx.Dialog.__init__(self, parent, -1, title,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.list = list

        # リスト
        self.values = EditableListCtrl(self, -1, size=(250, -1), style=wx.LC_REPORT|wx.MULTIPLE|wx.LC_NO_HEADER)
        self.values.imglist = wx.ImageList(image.GetWidth(), image.GetHeight())
        self.values.imgidx = self.values.imglist.Add(image)
        self.values.SetImageList(self.values.imglist, wx.IMAGE_LIST_SMALL)
        self.values.InsertColumn(0, u"")
        self.values.SetColumnWidth(0, 170)
        self.values.setResizeColumn(0)

        # 追加
        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_ADD, (-1, -1), name=u"追加")
        # 削除
        self.rmvbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_REMOVE, (-1, -1), name=u"削除")
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
        sizer = wx.GridBagSizer()

        sizer.Add(self.values, pos=(0, 0), span=(7, 1), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(4)

        sizer.Add(self.addbtn, pos=(0, 1), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.rmvbtn, pos=(1, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.upbtn, pos=(2, 1), flag=wx.RIGHT|wx.BOTTOM|wx.EXPAND, border=5)
        sizer.Add(self.downbtn, pos=(3, 1), flag=wx.RIGHT|wx.EXPAND, border=5)
        sizer.SetEmptyCellSize((0, 150))
        sizer.Add(self.okbtn, pos=(5, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)
        sizer.Add(self.cnclbtn, pos=(6, 1), flag=wx.RIGHT|wx.BOTTOM, border=5)

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
        self.list[index1], self.list[index2] = self.list[index2], self.list[index1]

        mask = wx.LIST_STATE_SELECTED
        temp = self.values.GetItemState(index1, mask)
        self.values.SetItemState(index1, self.values.GetItemState(index2, mask), mask)
        self.values.SetItemState(index2, temp, mask)
        self.values.SetStringItem(index1, 0, self.list[index1])
        self.values.SetStringItem(index2, 0, self.list[index2])

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
        if not indexes:
            self.rmvbtn.Enable(False)
            self.upbtn.Enable(False)
            self.downbtn.Enable(False)
        else:
            self.rmvbtn.Enable(True)
            self.upbtn.Enable(0 < indexes[0])
            self.downbtn.Enable(indexes[-1] + 1 < self.values.GetItemCount())

class GossipEditDialog(ListEditDialog):
    def __init__(self, parent):
        ListEditDialog.__init__(self, parent, u"ゴシップの編集",
            cw.cwpy.ydata.get_gossiplist(), cw.cwpy.rsrc.debugs["GOSSIP"])

    def OnOkBtn(self, event):
        cw.cwpy.sounds["harvest"].play()
        cw.cwpy.ydata.clear_gossips()
        for name in self.list:
            cw.cwpy.ydata.set_gossip(name)
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()

class CompStampEditDialog(ListEditDialog):
    def __init__(self, parent):
        ListEditDialog.__init__(self, parent, u"終了印の編集",
            cw.cwpy.ydata.get_compstamplist(), cw.cwpy.rsrc.debugs["COMPSTAMP"])

    def OnOkBtn(self, event):
        cw.cwpy.sounds["harvest"].play()
        cw.cwpy.ydata.clear_compstamps()
        for name in self.list:
            cw.cwpy.ydata.set_compstamp(name)
        self.SetReturnCode(wx.ID_OK)
        self.Destroy()


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, id, size, style):
        wx.ListCtrl.__init__(self, parent, id, size=size, style=style)
        listmix.TextEditMixin.__init__(self)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

    def OpenEditor(self, row, col):
        # FIXME: 直接呼び出すとcol_locsが生成されないバグ
        self.col_locs = [0]
        loc = 0
        for n in range(self.GetColumnCount()):
            loc = loc + self.GetColumnWidth(n)
            self.col_locs.append(loc)
        listmix.TextEditMixin.OpenEditor(self, row, col)
