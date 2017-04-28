#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


#-------------------------------------------------------------------------------
#  状態編集ダイアログ
#-------------------------------------------------------------------------------

class StatusEditDialog(wx.Dialog):

    def __init__(self, parent, mlist, selected=-1):
        wx.Dialog.__init__(self, parent, -1, u"キャラクターの状態の編集",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = True
        self.SetDoubleBuffered(True)

        self.pcards = mlist

        self.statuses = []
        self.statuses_backup = []
        for pcard in self.pcards:
            self.statuses.append(Status(pcard))
            self.statuses_backup.append(Status(pcard))

        self.life      = StatusButton(self, 0, self._is_dead, size=cw.ppis((45, 45)))
        self.poison    = StatusButton(self, 1, self._is_dead, size=cw.ppis((45, 45)))
        self.paralyze  = StatusButton(self, 2, self._is_dead, size=cw.ppis((45, 45)))
        self.mentality = StatusButton(self, 3, self._is_dead, size=cw.ppis((45, 60)))
        self.bind      = StatusButton(self, 4, self._is_dead, size=cw.ppis((45, 45)))
        self.silence   = StatusButton(self, 5, self._is_dead, size=cw.ppis((45, 45)))
        self.faceup    = StatusButton(self, 6, self._is_dead, size=cw.ppis((45, 45)))
        self.antimagic = StatusButton(self, 7, self._is_dead, size=cw.ppis((45, 45)))
        self.action    = StatusButton(self, 8, self._is_dead, size=cw.ppis((45, 60)))
        self.avoid     = StatusButton(self, 9, self._is_dead, size=cw.ppis((45, 60)))
        self.resist    = StatusButton(self, 10, self._is_dead, size=cw.ppis((45, 60)))
        self.defense   = StatusButton(self, 11, self._is_dead, size=cw.ppis((45, 60)))
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
        bmp = cw.cwpy.rsrc.buttons["LSMALL_dbg"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)
        # smallright
        bmp = cw.cwpy.rsrc.buttons["RSMALL_dbg"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, cw.ppis((20, 20)), bmp=bmp)

        # 全快
        self.rcvbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"全快")
        # 復旧
        self.restorebtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), name=u"復旧")

        # 決定
        self.okbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, -1, (-1, -1), cw.cwpy.msgs["entry_decide"])
        # 中止
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton_dbg(self, wx.ID_CANCEL, (-1, -1), cw.cwpy.msgs["entry_cancel"])

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
        sizer_status = wx.GridBagSizer()
        sizer_status.Add(self.life, pos=(0, 0), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.poison, pos=(0, 1), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.paralyze, pos=(0, 2), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.mentality, pos=(1, 0), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.bind, pos=(2, 0), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.silence, pos=(2, 1), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.faceup, pos=(2, 2), flag=wx.RIGHT|wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.antimagic, pos=(2, 3), flag=wx.BOTTOM, border=cw.ppis(5))
        sizer_status.Add(self.action, pos=(3, 0), flag=wx.RIGHT, border=cw.ppis(5))
        sizer_status.Add(self.avoid, pos=(3, 1), flag=wx.RIGHT, border=cw.ppis(5))
        sizer_status.Add(self.resist, pos=(3, 2), flag=wx.RIGHT, border=cw.ppis(5))
        sizer_status.Add(self.defense, pos=(3, 3))

        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_combo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_combo.Add(self.leftbtn, 0, wx.EXPAND)
        sizer_combo.Add(self.target, 1, wx.LEFT|wx.RIGHT|wx.EXPAND, border=cw.ppis(5))
        sizer_combo.Add(self.rightbtn, 0, wx.EXPAND)
        sizer_left.Add(sizer_combo, 0, flag=wx.BOTTOM|wx.EXPAND, border=cw.ppis(5))
        sizer_left.Add(sizer_status, 1, flag=wx.EXPAND)

        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_right.Add(self.rcvbtn, 0, wx.EXPAND)
        sizer_right.Add(self.restorebtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))
        sizer_right.AddStretchSpacer(1)
        sizer_right.Add(self.okbtn, 0, wx.EXPAND)
        sizer_right.Add(self.cnclbtn, 0, wx.EXPAND|wx.TOP, border=cw.ppis(5))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sizer_left, 1, flag=wx.EXPAND|wx.ALL, border=cw.ppis(5))
        sizer.Add(sizer_right, 0, flag=wx.EXPAND|wx.RIGHT|wx.TOP|wx.BOTTOM, border=cw.ppis(5))

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
        def func(pcards, oldactive, updates):
            for i in updates:
                pcard = pcards[i]
                cw.cwpy.play_sound("harvest")
                battlespeed = cw.cwpy.is_battlestatus()
                if pcard.status == "hidden":
                    pcard.update_image()
                    waitrate = (cw.cwpy.setting.get_dealspeed(battlespeed)+1) * 2
                    cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                else:
                    cw.animation.animate_sprite(pcard, "hide", battlespeed=battlespeed)
                    pcard.update_image()
                    cw.animation.animate_sprite(pcard, "deal", battlespeed=battlespeed)

                if cw.cwpy.is_battlestatus() and oldactive[i] <> pcard.is_active():
                    # アクティブ状態が変わったので
                    # 行動の再選択か、キャンセルを行う
                    if pcard.is_active():
                        pcard.deck.set(pcard)
                        pcard.decide_action()
                    else:
                        pcard.clear_action()
                        cw.cwpy.clear_inusecardimg(pcard)

            if not updates:
                cw.cwpy.play_sound("harvest")

        updates = []
        oldactive = []
        for i, status in enumerate(self.statuses):
            pcard = self.pcards[i]
            oldactive.append(pcard.is_active())

            if status.put_status(pcard):
                updates.append(i)

        cw.cwpy.exec_func(func, self.pcards, oldactive, updates)

        self.EndModal(wx.ID_OK)

    def OnLife(self, event):
        value = 100
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.life, (i == 0), 100)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"現生命点(%)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.life = dlg.value
            self._update_status()

    def OnPoison(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.poison, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"毒性値(中毒)", value, 0, 40)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.poison = dlg.value
            self._update_status()

    def OnParalyze(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.paralyze, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"毒性値(麻痺)", value, 0, 40)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.paralyze = dlg.value
            self._update_status()

    def OnMentality(self, event):
        value = "Normal"
        duration = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.mentality, (i == 0), "Normal")
            duration = self._value(value, status.mentality_dur, (i == 0), 0)

        STATUSES = [
            ("Normal",   u"正常", cw.cwpy.rsrc.wxstatuses["MIND0"]),
            ("Sleep",    u"眠り", cw.cwpy.rsrc.wxstatuses["MIND1"]),
            ("Confuse",  u"混乱", cw.cwpy.rsrc.wxstatuses["MIND2"]),
            ("Overheat", u"激昂", cw.cwpy.rsrc.wxstatuses["MIND3"]),
            ("Brave",    u"勇敢", cw.cwpy.rsrc.wxstatuses["MIND4"]),
            ("Panic",    u"恐慌", cw.cwpy.rsrc.wxstatuses["MIND5"]),
        ]

        seq = []
        selected = 0
        for i, stdata in enumerate(STATUSES):
            seq.append((stdata[1], stdata[2]))
            if stdata[0] == value:
                selected = i

        dlg = cw.dialog.edit.NumberComboEditDialog(self, u"精神状態",
                                                   u"精神状態", seq, selected,
                                                   u"継続時間", duration, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.mentality = STATUSES[dlg.selected][0]
                status.mentality_dur = dlg.value
            self._update_status()

    def OnBind(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.bind, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"継続時間(呪縛)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.bind = dlg.value
            self._update_status()

    def OnSilence(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.silence, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"継続時間(沈黙)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.silence = dlg.value
            self._update_status()

    def OnFaceUp(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.faceup, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"継続時間(暴露)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.faceup = dlg.value
            self._update_status()

    def OnAntiMagic(self, event):
        value = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.antimagic, (i == 0), 0)

        dlg = cw.dialog.edit.NumberEditDialog(self, u"継続時間(魔法無効)", value, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.antimagic = dlg.value
            self._update_status()

    def OnAction(self, event):
        value = 0
        duration = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.enhance_act, (i == 0), 0)
            duration = self._value(duration, status.enhance_act_dur, (i == 0), 0)

        dlg = cw.dialog.edit.Number2EditDialog(self, u"行動力修正",
                                               u"修正値", value, -10, 10,
                                               u"継続時間", duration, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.enhance_act = dlg.value1
                status.enhance_act_dur = dlg.value2
            self._update_status()

    def OnAvoid(self, event):
        value = 0
        duration = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.enhance_avo, (i == 0), 0)
            duration = self._value(duration, status.enhance_avo_dur, (i == 0), 0)

        dlg = cw.dialog.edit.Number2EditDialog(self, u"回避力修正",
                                               u"修正値", value, -10, 10,
                                               u"継続時間", duration, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.enhance_avo = dlg.value1
                status.enhance_avo_dur = dlg.value2
            self._update_status()

    def OnResist(self, event):
        value = 0
        duration = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.enhance_res, (i == 0), 0)
            duration = self._value(duration, status.enhance_res_dur, (i == 0), 0)

        dlg = cw.dialog.edit.Number2EditDialog(self, u"抵抗力修正",
                                               u"修正値", value, -10, 10,
                                               u"継続時間", duration, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.enhance_res = dlg.value1
                status.enhance_res_dur = dlg.value2
            self._update_status()

    def OnDefense(self, event):
        value = 0
        duration = 0
        for i, status in enumerate(self._get_statuses()):
            value = self._value(value, status.enhance_def, (i == 0), 0)
            duration = self._value(duration, status.enhance_def_dur, (i == 0), 0)

        dlg = cw.dialog.edit.Number2EditDialog(self, u"防御力修正",
                                               u"修正値", value, -10, 10,
                                               u"継続時間", duration, 0, 100)
        cw.cwpy.frame.move_dlg(dlg)
        if dlg.ShowModal() == wx.ID_OK:
            for status in self._get_statuses():
                status.enhance_def = dlg.value1
                status.enhance_def_dur = dlg.value2
            self._update_status()

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
            self.life = int(100 * pcard.life / pcard.maxlife)
            if self.life == 0 and 0 < pcard.life:
                # 1点でもライフがある場合は最小で1%にする
                self.life = 1
        else:
            self.life = pcard.life
        # 精神状態
        self.mentality = pcard.mentality
        if self.mentality <> "Normal":
            self.mentality_dur = pcard.mentality_dur
        else:
            self.mentality_dur = 0
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
        if self.enhance_act <> 0:
            self.enhance_act_dur = pcard.enhance_act_dur
        else:
            self.enhance_act_dur = 0
        # 回避力強化値
        self.enhance_avo = pcard.enhance_avo
        if self.enhance_avo <> 0:
            self.enhance_avo_dur = pcard.enhance_avo_dur
        else:
            self.enhance_avo_dur = 0
        # 抵抗力強化値
        self.enhance_res = pcard.enhance_res
        if self.enhance_res <> 0:
            self.enhance_res_dur = pcard.enhance_res_dur
        else:
            self.enhance_res_dur = 0
        # 防御力強化値
        self.enhance_def = pcard.enhance_def
        if self.enhance_def <> 0:
            self.enhance_def_dur = pcard.enhance_def_dur
        else:
            self.enhance_def_dur = 0

    def is_dead(self):
        return self.life == 0 or 0 < self.paralyze

    def put_status(self, pcard):
        update = False
        s = Status(pcard)

        if s.life <> self.life:
            life = int(pcard.maxlife / 100.0 * self.life) - pcard.life
            if pcard.life + life <= 0 and 0 < self.life:
                # 0%でない場合は最小値を1にする
                life = 1 - pcard.life
            pcard.set_life(life)
            update = True

        if self.mentality <> s.mentality or\
                self.mentality_dur <> s.mentality_dur:
            pcard.set_mentality(self.mentality, self.mentality_dur)
            update = True

        if self.paralyze <> s.paralyze:
            pcard.set_paralyze(self.paralyze - pcard.paralyze)
            update = True

        if self.poison <> s.poison:
            pcard.set_poison(self.poison - pcard.poison)
            update = True

        if self.bind <> s.bind:
            pcard.set_bind(self.bind)
            update = True

        if self.silence <> s.silence:
            pcard.set_silence(self.silence)
            update = True

        if self.faceup <> s.faceup:
            pcard.set_faceup(self.faceup)
            update = True

        if self.antimagic <> s.antimagic:
            pcard.set_antimagic(self.antimagic)
            update = True

        if self.enhance_act <> s.enhance_act or\
                self.enhance_act_dur <> s.enhance_act_dur:
            pcard.set_enhance_act(self.enhance_act, self.enhance_act_dur)
            update = True

        if self.enhance_avo <> s.enhance_avo or\
                self.enhance_avo_dur <> s.enhance_avo_dur:
            pcard.set_enhance_avo(self.enhance_avo, self.enhance_avo_dur)
            update = True

        if self.enhance_res <> s.enhance_res or\
                self.enhance_res_dur <> s.enhance_res_dur:
            pcard.set_enhance_res(self.enhance_res, self.enhance_res_dur)
            update = True

        if self.enhance_def <> s.enhance_def or\
                self.enhance_def_dur <> s.enhance_def_dur:
            pcard.set_enhance_def(self.enhance_def, self.enhance_def_dur)
            update = True

        return update

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
            image = cw.cwpy.rsrc.wxstatuses["LIFE_dbg"]
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
            image = cw.cwpy.rsrc.wxstatuses["BODY0_dbg"]
        elif self.mode == 2:
            # 麻痺
            image = cw.cwpy.rsrc.wxstatuses["BODY1_dbg"]
        elif self.mode == 3:
            # 精神状態
            if self.value is None or self.value == "Normal":
                # 正常
                image = cw.cwpy.rsrc.wxstatuses["MIND0_dbg"]
            elif self.value == "Sleep":
                # 眠り
                image = cw.cwpy.rsrc.wxstatuses["MIND1_dbg"]
                self.text1 = u"眠り"
            elif self.value == "Confuse":
                # 混乱
                image = cw.cwpy.rsrc.wxstatuses["MIND2_dbg"]
                self.text1 = u"混乱"
            elif self.value == "Overheat":
                # 激高
                image = cw.cwpy.rsrc.wxstatuses["MIND3_dbg"]
                self.text1 = u"激昂"
            elif self.value == "Brave":
                # 勇猛
                image = cw.cwpy.rsrc.wxstatuses["MIND4_dbg"]
                self.text1 = u"勇猛"
            elif self.value == "Panic":
                # 恐慌
                image = cw.cwpy.rsrc.wxstatuses["MIND5_dbg"]
                self.text1 = u"恐慌"

            if not self.duration is None and 0 < self.duration:
                self.text2 = "%sr" % (self.duration)
                if not self.value is None and not self.is_dead():
                    enable = True
        elif self.mode == 4:
            # 呪縛
            image = cw.cwpy.rsrc.wxstatuses["MAGIC0_dbg"]
        elif self.mode == 5:
            # 沈黙
            image = cw.cwpy.rsrc.wxstatuses["MAGIC1_dbg"]
        elif self.mode == 6:
            # 暴露
            image = cw.cwpy.rsrc.wxstatuses["MAGIC2_dbg"]
        elif self.mode == 7:
            # 魔法無効
            image = cw.cwpy.rsrc.wxstatuses["MAGIC3_dbg"]
        elif self.mode == 8:
            # 行動力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.wxstatuses["UP0_dbg"]
            else:
                image = cw.cwpy.rsrc.wxstatuses["DOWN0_dbg"]
        elif self.mode == 9:
            # 回避力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.wxstatuses["UP1_dbg"]
            else:
                image = cw.cwpy.rsrc.wxstatuses["DOWN1_dbg"]
        elif self.mode == 10:
            # 抵抗力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.wxstatuses["UP2_dbg"]
            else:
                image = cw.cwpy.rsrc.wxstatuses["DOWN2_dbg"]
        elif self.mode == 11:
            # 防御力
            if self.value is None or self.value >= 0:
                image = cw.cwpy.rsrc.wxstatuses["UP3_dbg"]
            else:
                image = cw.cwpy.rsrc.wxstatuses["DOWN3_dbg"]
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
                if 0 != self.value and 0 < self.duration and not self.is_dead():
                    enable = True

            colour = wx.Colour(192, 192, 192)
            if not self.value is None:
                if 10 <= self.value:
                    colour = wx.Colour(255, 0, 0)
                elif 7 <= self.value:
                    colour = wx.Colour(175, 0, 0)
                elif 4 <= self.value:
                    colour = wx.Colour(127, 0, 0)
                elif 1 <= self.value:
                    colour = wx.Colour(79, 0, 0)
                elif -10 >= self.value:
                    colour = wx.Colour(0, 0, 51)
                elif -7 >= self.value:
                    colour = wx.Colour(0, 0, 85)
                elif -4 >= self.value:
                    colour = wx.Colour(0, 0, 136)
                elif -1 >= self.value:
                    colour = wx.Colour(0, 0, 187)

        self.image = image

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
            bdc.DrawBitmap(self.image, 0, 0, True)
            bdc.EndDrawing()
            self.image = canvas

        # 半透明化
        w = self.image.GetWidth()
        h = self.image.GetHeight()
        image = cw.util.convert_to_image(self.image)
        if not enable:
            image.SetAlphaData(chr(128) * (w*h))
        self.image = image.ConvertToBitmap()

        csize = self.GetClientSize()

        canvas = wx.EmptyBitmap(csize[0], csize[1])

        dc = wx.MemoryDC(canvas)
        dc.BeginDrawing()
        colour = self.GetBackgroundColour()
        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour))
        dc.DrawRectangle(0, 0, canvas.GetWidth(), canvas.GetHeight())
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("button", pointsize=9))

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

def main():
    pass

if __name__ == "__main__":
    main()
