#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw
import select
import message

#-------------------------------------------------------------------------------
#　パーティの記録
#-------------------------------------------------------------------------------

class SelectPartyRecord(select.Select):
    """
    パーティ記録・再結成ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        select.Select.__init__(self, parent, cw.cwpy.msgs["select_party_record"])
        # パーティ情報
        self.list = cw.cwpy.ydata.partyrecord[:]
        self.list.append(None)
        self.restorable = [None]*len(self.list)
        self.index = 0
        self.names = []
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=cw.wins((460, 280)))
        # restore
        self.restorebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((75, 24)), cw.cwpy.msgs["party_restore"])
        self.buttonlist.append(self.restorebtn)
        # save
        self.savebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((75, 24)), cw.cwpy.msgs["party_save"])
        self.buttonlist.append(self.savebtn)
        # delete
        self.deletebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, cw.wins((75, 24)), cw.cwpy.msgs["delete"])
        self.buttonlist.append(self.deletebtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, cw.wins((75, 24)), cw.cwpy.msgs["close"])
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickSaveBtn, self.savebtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRestoreBtn, self.restorebtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDeleteBtn, self.deletebtn)

        self.draw(True)

    def OnSelect(self, event):
        if not self.list[self.index] or not self.restorebtn.IsEnabled():
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.restorebtn.GetId())
        self.ProcessEvent(btnevent)

    def OnClickSaveBtn(self, event):
        """パーティの記録。"""
        if self.Parent.is_processing():
            return
        header = self.list[self.index]
        cw.cwpy.play_sound("signal")
        if header:
            s = cw.cwpy.msgs["overwrite_party_record"] % (header.name)
        else:
            s = cw.cwpy.msgs["save_party_record"]
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        def func(panel, header, index):
            cw.cwpy.play_sound("harvest")
            partyrecord = cw.cwpy.get_partyrecord()
            if header:
                header = cw.cwpy.ydata.set_partyrecord(index, partyrecord)
            else:
                header = cw.cwpy.ydata.add_partyrecord(partyrecord)
            def func(panel, header):
                if panel:
                    panel.list = cw.cwpy.ydata.partyrecord[:]
                    panel.list.append(None)
                    panel.restorable = [None]*len(panel.list)
                    panel.index = panel.list.index(header)
                    panel.draw(True)
            cw.cwpy.frame.exec_func(func, panel, header)
        cw.cwpy.exec_func(func, self, header, self.index)

    def OnClickRestoreBtn(self, event):
        """パーティの再結成。"""
        if self.Parent._processing:
            return
        header = self.list[self.index]
        assert bool(header)

        if cw.cwpy.ydata.party:
            cw.cwpy.play_sound("signal")
            s = cw.cwpy.msgs["restore_party"] % (header.name)
            dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
            cw.cwpy.frame.move_dlg(dlg)

            if not dlg.ShowModal() == wx.ID_OK:
                dlg.Destroy()
                return

        def func(header, panel, parent, selected):
            cw.cwpy.play_sound("harvest")
            updatelist = bool(cw.cwpy.ydata.party)
            if updatelist:
                cw.cwpy.save_partyrecord()
            cw.cwpy.ydata.restore_party(header)
            def func(panel, parent, selected, updatelist):
                if panel and updatelist:
                    header = panel.list[panel.index]
                    panel.list = cw.cwpy.ydata.partyrecord[:]
                    panel.list.append(None)
                    panel.restorable = [None]*len(panel.list)
                    if header in panel.list:
                        panel.index = panel.list.index(header)
                if panel:
                    panel.draw(True)
                if parent:
                    parent.update_standbys(selected)
                    parent._processing = False
            cw.cwpy.frame.exec_func(func, panel, parent, selected, updatelist)
        self.Parent._processing = True
        cw.cwpy.exec_func(func, header, self, self.Parent, self.Parent.get_selected())

    def OnClickDeleteBtn(self, event):
        """パーティ記録の削除。"""
        if self.Parent.is_processing():
            return
        header = self.list[self.index]
        assert bool(header)

        cw.cwpy.play_sound("signal")
        s = cw.cwpy.msgs["delete_party_record"] % (header.name)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        cw.cwpy.play_sound("dump")
        def func(header):
            cw.cwpy.ydata.remove_partyrecord(header)
        cw.cwpy.exec_func(func, header)
        self.list.remove(header)
        self.index = max(0, min(self.index, len(self.list)-2))
        if 1 < len(self.list) or cw.cwpy.ydata.party:
            def func(panel):
                def func(panel):
                    panel.restorable = [None]*len(panel.list)
                    panel.draw(True)
                cw.cwpy.frame.exec_func(func, panel)
            cw.cwpy.exec_func(func, self)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

    def can_clickcenter(self):
        return self.restorebtn.IsEnabled()

    def can_clickside(self):
        return 1 < len(self.list)

    def enable_btn(self):
        assert len(self.list)
        self.left2btn.Enable(1 < len(self.list))
        self.leftbtn.Enable(1 < len(self.list))
        self.rightbtn.Enable(1 < len(self.list))
        self.right2btn.Enable(1 < len(self.list))

        self._update_restorable()
        self.savebtn.Enable(bool(cw.cwpy.ydata.party))
        self.restorebtn.Enable(bool(self.list[self.index] and self.restorable[self.index][0]))
        self.deletebtn.Enable(bool(self.list[self.index]))
        buttonlist = filter(lambda button: button.IsEnabled(), self.buttonlist)
        if buttonlist:
            buttonlist[0].SetFocus()

    def _update_restorable(self):
        header = self.list[self.index]
        if not header:
            return
        restorable = self.restorable[self.index]
        if restorable:
            return

        can = False
        members = {}
        cards = []

        for member in header.members:
            c = cw.cwpy.ydata.can_restore(member)
            can |= c
            members[member] = c

        e = cw.data.yadoxml2etree(header.fpath, tag="BackpackRecord")
        removed = set()
        for i, ce in enumerate(e.getfind(".")):
            if ce.tag <> "CardRecord":
                continue
            if 4 * 6 <= i:
                break
            name = ce.getattr(".", "name", "")
            desc = ce.getattr(".", "desc", "")
            flag = False
            if not flag:
                for cheader in cw.cwpy.ydata.storehouse:
                    if cheader.name == name and cheader.desc == desc and\
                            not cheader in removed:
                        flag = True
                        removed.add(cheader)
                        break
            if not flag and cw.cwpy.ydata.party:
                for cheader in cw.cwpy.ydata.party.backpack:
                    if cheader.name == name and cheader.desc == desc and\
                            not cheader in removed:
                        flag = True
                        removed.add(cheader)
                        break
            cards.append(flag)

        restorable = (can, members, cards)

        self.restorable[self.index] = restorable

    def draw(self, update=False):
        assert len(self.list)

        dc = select.Select.draw(self, update)
        # 背景
        path = "Table/Book"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        bmp = cw.wins(cw.util.load_wxbmp(path, can_loaded_scaledimage=True))
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        header = self.list[self.index]
        self._update_restorable()
        restorable = self.restorable[self.index]
        if restorable:
            _can, members, cards = restorable
        else:
            _can = False
            members = {}
            cards = None
        # 見出し
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
        s = cw.cwpy.msgs["adventurers_team_record"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(25))
        # 所持金
        if header:
            s = cw.cwpy.msgs["adventurers_money"] % (header.money)
        else:
            s = cw.cwpy.msgs["adventurers_money"] % (u"---")
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(60))

        # メンバ名
        if update:
            if header:
                self.names = header.get_membernames()
            else:
                self.names = []
        if len(self.names) > 3:
            n = (3, len(self.names) - 3)
        else:
            n = (len(self.names), 0)

        w = cw.wins(95)

        for index, s in enumerate(self.names):
            if members.get(header.members[index], False):
                dc.SetTextForeground((0, 0, 0))
            else:
                dc.SetTextForeground((128, 128, 128))

            s = cw.util.abbr_longstr(dc, s, cw.wins(95))
            if index < 3:
                dc.DrawLabel(s, wx.Rect((bmpw-w*n[0])/2+w*index, cw.wins(85), w, cw.wins(15)), wx.ALIGN_CENTER)
            else:
                dc.DrawLabel(s, wx.Rect((bmpw-w*n[1])/2+w*(index-3), cw.wins(105), w, cw.wins(15)), wx.ALIGN_CENTER)

        # パーティ名
        dc.SetTextForeground((0, 0, 0))
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(20)))
        if header:
            s = header.name
        else:
            s = cw.cwpy.msgs["new_party_record"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(40))

        # 所持カード
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(16)))
        s = cw.cwpy.msgs["backpack_record"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(130))

        if header:
            llen = min(4, len(header.backpack))
        else:
            llen = 4
        hlen = 6
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlglist", pixelsize=cw.wins(14)))
        if header:
            backpacklist = header.backpack
            if llen*hlen < len(backpacklist):
                backpacklist = backpacklist[:llen*hlen-1]
                backpacklist.append(cw.cwpy.msgs["history_etc"])
            w = cw.wins(84)
            y = cw.wins(150)
            for index, s in enumerate(backpacklist):
                if cards and cards[index]:
                    dc.SetTextForeground((0, 0, 0))
                else:
                    dc.SetTextForeground((128, 128, 128))
                s = cw.util.abbr_longstr(dc, s, cw.wins(84))
                ypos = y + cw.wins(16) * int(index/llen)
                xpos = index % llen
                dc.DrawLabel(s, wx.Rect((bmpw-w*llen)/2+w*xpos+cw.wins(10), ypos, w, cw.wins(15)), wx.ALIGN_LEFT)

        # ページ番号
        dc.SetTextForeground((0, 0, 0))
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgtitle", pixelsize=cw.wins(14)))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, cw.wins(250))

        if update:
            self.enable_btn()

