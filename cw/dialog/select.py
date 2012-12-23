#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import threading
import zipfile
import StringIO
import wx

import cw
import cw.binary
import message
import charainfo
import text

from cw.util import synclock

_lockupdatescenario = threading.Lock()

#-------------------------------------------------------------------------------
#　選択ダイアログ スーパークラス
#-------------------------------------------------------------------------------

class Select(wx.Dialog):
    def __init__(self, parent, name):
        wx.Dialog.__init__(self, parent, -1, name,
                style=wx.CAPTION|wx.DIALOG_MODAL|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        # panel
        self.panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
        # buttonlist
        self.buttonlist = []
        # leftjump
        bmp = cw.cwpy.rsrc.buttons["LJUMP"]
        self.left2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (30, 30), bmp=bmp)
        # left
        bmp = cw.cwpy.rsrc.buttons["LMOVE"]
        self.leftbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_UP, (30, 30), bmp=bmp)
        # right
        bmp = cw.cwpy.rsrc.buttons["RMOVE"]
        self.rightbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DOWN, (30, 30), bmp=bmp)
        # rightjump
        bmp = cw.cwpy.rsrc.buttons["RJUMP"]
        self.right2btn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (30, 30), bmp=bmp)
        # focus
        self.panel.SetFocusIgnoringChildren()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickLeftBtn, self.leftbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickLeft2Btn, self.left2btn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRightBtn, self.rightbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickRight2Btn, self.right2btn)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.toppanel.Bind(wx.EVT_MIDDLE_UP, self.OnSelect)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnSelect)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnClickLeftBtn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)

    def OnClickLeft2Btn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        elif self.index - 10 < 0:
            self.index = 0
        else:
            self.index -= 10

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)

    def OnClickRightBtn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)

    def OnClickRight2Btn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        elif self.index + 10 > len(self.list) -1:
            self.index = len(self.list) -1
        else:
            self.index += 10

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)

    def OnMouseWheel(self, event):
        if not self.list or len(self.list) == 1:
            return

        if event.GetWheelRotation() > 0:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_UP)
            self.ProcessEvent(btnevent)
        else:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_DOWN)
            self.ProcessEvent(btnevent)

    def OnSelect(self, event):
        if not self.list:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        cw.cwpy.sounds[u"click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetSize())
        else:
            dc = wx.PaintDC(self.toppanel)

        return dc

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_panel = wx.BoxSizer(wx.HORIZONTAL)

        sizer_panel.Add(self.left2btn, 0, 0, 0)
        sizer_panel.Add(self.leftbtn, 0, 0, 0)

        # button間のマージン値を求める
        width = self.toppanel.GetClientSize()[0] - 6
        btnwidth = 120 + self.buttonlist[0].GetSize()[0] * len(self.buttonlist)
        margin = (width - btnwidth) / (len(self.buttonlist)+1)
        margin2 = margin + (width - btnwidth) % (len(self.buttonlist)+1)

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_panel.Add((margin, 0), 0, 0, 0)
            sizer_panel.Add(button, 0, wx.TOP|wx.BOTTOM, 3)

        sizer_panel.Add((margin2, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        sizer_panel.Add(self.right2btn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        sizer_1.Add(self.toppanel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.panel, 0, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def _disable_btn(self):
        self.left2btn.Disable()
        self.leftbtn.Disable()
        self.rightbtn.Disable()
        self.right2btn.Disable()

        for btn in self.buttonlist:
            btn.Disable()

    def _enable_btn(self):
        self.left2btn.Enable()
        self.leftbtn.Enable()
        self.rightbtn.Enable()
        self.right2btn.Enable()

        for btn in self.buttonlist:
            btn.Enable()

#-------------------------------------------------------------------------------
#　宿選択ダイアログ
#-------------------------------------------------------------------------------

class YadoSelect(Select):
    """
    宿選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, u"宿の選択")
        # 宿情報
        self.list, self.list2 = self.get_yadolist()
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(400, 370))
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, (50, 24), u"決定")
        self.buttonlist.append(self.okbtn)
        # extend
        self.extbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"変換")
        self.buttonlist.append(self.extbtn)
        # delete
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"削除")
        self.buttonlist.append(self.delbtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"新規")
        self.buttonlist.append(self.newbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (50, 24), u"中止")
        self.buttonlist.append(self.closebtn)
        # enable bottun
        self.enable_btn()
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickDelBtn, self.delbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExtBtn, self.extbtn)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.extbtn.Enable()
            self.newbtn.Enable()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

    def OnDropFiles(self, event):
        paths = event.GetFiles()

        for path in paths:
            self.conv_yado(path)
            time.sleep(0.3)

    def OnClickDelBtn(self, event):
        """
        宿削除。
        """
        cw.cwpy.sounds[u"signal"].play()
        path = self.list[self.index]
        yname = os.path.basename(path)
        s = u"宿「%s」を破棄します。\nよろしいですか？" % (yname)
        dlg = message.YesNoMessage(self, u"メッセージ", s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.util.remove(path)
            self.update_list()

        dlg.Destroy()

    def OnClickNewBtn(self, event):
        """
        宿新規作成。
        """
        dlg = cw.dialog.create.YadoCreater(self)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            yname = dlg.textctrl.GetValue()
            self.update_list(yname)

        dlg.Destroy()

    def OnClickExtBtn(self, evt):
        """
        CardWirthの宿データを変換。
        """
        # ディレクトリ選択ダイアログ
        s = (u"カードワースの宿のデータをカードワースパイ用に変換します。" +
              u"\n変換する宿のディレクトリを選択してください。")
        dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
        dlg.SetPath(os.getcwdu())

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.conv_yado(path)
        else:
            dlg.Destroy()

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Bill" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        # 宿画像
        path = "Resource/Image/Card/COMMAND0" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path, True)
        dc.DrawBitmap(bmp, (bmpw-74)/2, 70, True)
        # 宿名前
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=16))
        s = os.path.split(self.list[self.index])[1]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 40)
        # ページ番号
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 340)
        # Adventurers
        s = "Adventurers"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 175)

        # 所属冒険者
        for idx, name in enumerate(self.list2[self.index]):
            x = (bmpw - 250) / 2 + ((idx % 3) * 95)
            y = 200 + (idx / 3) * 16
            dc.DrawText(name, x, y)

    def conv_yado(self, path):
        """
        CardWirthの宿データを変換。
        """
        # カードワースの宿か確認
        if not os.path.exists(cw.util.join_paths(path, "Environment.wyd")):
            s = u"カードワースの宿のディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        cw.cwpy.sounds[u"click"].play()
        s = os.path.basename(path) + u" を変換します。\nよろしいですか？"
        dlg = message.YesNoMessage(self, u"メッセージ", s)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        dlg.Destroy()
        # 宿データ
        cwdata = cw.binary.cwyado.CWYado(
            path, "Yado", cw.cwpy.setting.skintype)

        # 変換可能なデータかどうか確認
        if not cwdata.is_convertible():
            s = u"CardWirth ver1.28以降の宿しか変換できません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 宿データ読み込み
        cwdata.load()
        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            cwdata.name + u" 変換", "", maximum=cwdata.maxnum,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(cwdata)
        thread.start()

        while not thread.complete:
            dlg.Update(cwdata.curnum, cwdata.message)
            wx.MilliSleep(1)

        dlg.Destroy()
        yname = os.path.basename(thread.path)

        # エラーログ表示
        if cwdata.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # 変換完了ダイアログ
        cw.cwpy.sounds[u"harvest"].play()
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, u"メッセージ", s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        self.update_list(yname)

    def update_list(self, name=""):
        """
        登録されている宿のリストを更新して、
        引数のnameの宿までページを移動する。
        """
        self.list, self.list2 = self.get_yadolist()
        path = cw.util.join_paths("Yado", name)

        try:
            self.index = self.list.index(path)
        except:
            self.index = 0

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)
        self.enable_btn()

    def get_yadolist(self):
        """Yadoにある宿のpathリストと冒険者リストを返す。"""
        yadodirs = []

        if not os.path.exists(u"Yado"):
            os.makedirs(u"Yado")

        for dname in os.listdir(u"Yado"):
            path  = cw.util.join_paths(u"Yado", dname, "Environment.xml")

            if os.path.isfile(path):
                path  = cw.util.join_paths(u"Yado", dname)
                yadodirs.append(path)

        advnames = []

        for path in yadodirs:
            dpath = cw.util.join_paths(path, u"Adventurer")
            seq = []

            for idx, fname in enumerate(os.listdir(dpath)):
                if fname.endswith(".xml"):
                    if idx < 23:
                        name = os.path.splitext(fname)[0].replace("(2)", "")
                        seq.append(name)
                    elif idx == 23:
                        seq.append(u"その他．．．")
                        break

            advnames.append(seq)

        return yadodirs, advnames

#-------------------------------------------------------------------------------
#　パーティ選択ダイアログ
#-------------------------------------------------------------------------------

class PartySelect(Select):
    """
    パーティ選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, u"冒険の再開")
        # パーティ情報
        self.list = cw.cwpy.ydata.partys
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, (75, 24), u"決定")
        self.buttonlist.append(self.okbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (75, 24), u"情報")
        self.buttonlist.append(self.infobtn)
        # edit
        self.editbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (75, 24), u"構成")
        self.buttonlist.append(self.editbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (75, 24), u"中止")
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Book" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        header = self.list[self.index]
        # 見出し
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
        s = "Adventurer's Team"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 25)
        # 所持金
        s = "Money " + str(header.money) + " sp"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 60)

        # メンバ名
        if len(header.members) > 3:
            n = (3, len(header.members) - 3)
        else:
            n = (len(header.members), 0)

        w = 90

        for index, s in enumerate(header.members):
            if index < 3:
                dc.DrawLabel(s, wx.Rect((bmpw-w*n[0])/2+w*index, 85, w, 15), wx.ALIGN_CENTER)
            else:
                dc.DrawLabel(s, wx.Rect((bmpw-w*n[1])/2+w*(index-3), 105, w, 15), wx.ALIGN_CENTER)

        # パーティ名
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=13))
        s = header.name
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 40)
        # シナリオ・宿画像
        sceheader = header.get_sceheader()

        if sceheader:
            bmp = sceheader.get_wxbmp()
        else:
            path = "Resource/Image/Card/COMMAND0" + cw.cwpy.rsrc.ext_img
            path = cw.util.join_paths(cw.cwpy.skindir, path)
            bmp = cw.util.load_wxbmp(path, True)

        dc.DrawBitmap(bmp, (bmpw-74)/2, 125, True)

        # シナリオ・宿名
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=11))

        if sceheader:
            s = sceheader.name
        else:
            s = cw.cwpy.ydata.name

        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 225)
        # ページ番号
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 250)

#-------------------------------------------------------------------------------
#　冒険者選択ダイアログ
#-------------------------------------------------------------------------------

class PlayerSelect(Select):
    """
    冒険者選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, u"宿帳を開く")
        # 冒険者情報
        self.list = cw.cwpy.ydata.standbys
        self.isalbum = False
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        # add
        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_ADD, (50, 24), u"編入")
        self.buttonlist.append(self.addbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"情報")
        self.buttonlist.append(self.infobtn)
        # extend
        self.extbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"拡張")
        self.buttonlist.append(self.extbtn)
        # delete
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"削除")
        self.buttonlist.append(self.delbtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"新規")
        self.buttonlist.append(self.newbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (50, 24), u"閉じる")
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickAddBtn, self.addbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDelBtn, self.delbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.newbtn.Enable()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
            self.index = 0
        else:
            self._enable_btn()

        # 冒険者が6人だったら追加ボタン無効化
        if len(cw.cwpy.get_pcards()) == 6:
            self.addbtn.Disable()

    def OnSelect(self, event):
        if not self.list or len(cw.cwpy.get_pcards()) == 6:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ADD)
        self.ProcessEvent(btnevent)

    def OnClickNewBtn(self, event):
        cw.cwpy.sounds[u"click"].play()
        dlg = cw.dialog.create.AdventurerCreater(self)
        cw.cwpy.frame.move_dlg(dlg, point=(20, 20))

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds[u"page"].play()
            header = cw.cwpy.ydata.add_standbys(dlg.fpath)
            # リスト更新
            self.list = cw.cwpy.ydata.standbys
            self.index = self.list.index(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def OnClickDelBtn(self, event):
        cw.cwpy.sounds[u"signal"].play()
        header = self.list[self.index]
        s = u"冒険者%sを削除します。\nよろしいですか？" % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, u"メッセージ", s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds[u"dump"].play()

            # レベル3以上・"＿消滅予約"を持ってない場合、アルバムに残す
            if header.level >= 3 and not header.leavenoalbum:
                path = cw.xmlcreater.create_albumpage(header.fpath)
                cw.cwpy.ydata.add_album(path)

            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.stopstandbysthread()
            cw.cwpy.ydata.standbys.remove(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def OnClickAddBtn(self, event):
        # カード表示中の場合は処理中止
        if cw.cwpy.is_dealing():
            return
        # 冒険者が6人だったら追加ボタン無効化
        elif len(cw.cwpy.get_pcards()) == 5:
            self.addbtn.Disable()

        cw.cwpy.sounds[u"harvest"].play()
        header = self.list[self.index]
        cw.cwpy.ydata.stopstandbysthread()
        cw.cwpy.ydata.standbys.remove(header)

        if cw.cwpy.ydata.party:
            cw.cwpy.exec_func(cw.cwpy.ydata.party.add, header)
        else:
            cw.cwpy.exec_func(cw.cwpy.ydata.create_party, header)

        self.enable_btn()
        self.draw(True)

    def OnClickInfoBtn(self, event):
        cw.cwpy.sounds[u"click"].play()
        dlg = charainfo.StandbyCharaInfo(self, self.list, self.index)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Book" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        header = self.list[self.index]
        if not isinstance(header, cw.header.AdventurerHeader):
            # まだヘッダが生成されていない場合
            header = cw.cwpy.ydata.create_advheader(header, self.isalbum)
            self.list[self.index] = header
            if self.isalbum:
                cw.cwpy.ydata.album[self.index] = header
            else:
                cw.cwpy.ydata.standbys[self.index] = header
        # Level
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = "Level"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 65, 45)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=22))
        s = str(header.level)
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 102, 31)
        # Name
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = "Adventurer"
        dc.DrawText(s, 102 + w + 5, 45)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=18))
        s = header.name
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 125 - w / 2, 62)
        # Image
        path = cw.util.join_yadodir(header.imgpath)
        bmp = cw.util.load_wxbmp(path, True)
        dc.DrawBitmap(bmp, 88, 90, True)
        # Age
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
        s = "Age:" + header.get_age()
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 127 - w / 2, 195)
        # Sex
        s = "Sex:" + header.get_sex()
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 127 - w / 2, 210)
        # EP
        s = "EP:" + str(header.ep)
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 127 - w / 2, 225)
        # クーポン(新しい順から7つ)
        s = u"【History】"
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, 320 - w / 2, 65)

        for index, s in enumerate(header.history):
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, 320 - w / 2, 95 + 15 * index)

        # ページ番号
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 250)

#-------------------------------------------------------------------------------
#　アルバムダイアログ
#-------------------------------------------------------------------------------

class Album(PlayerSelect):
    """
    アルバムダイアログ。
    冒険者選択ダイアログを継承している。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, u"アルバム")
        # 冒険者情報
        self.list = cw.cwpy.ydata.album
        self.isalbum = True
        self.index = 0
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_PROPERTIES, (90, 24), u"情報")
        self.buttonlist.append(self.infobtn)
        # delete
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DELETE, (90, 24), u"削除")
        self.buttonlist.append(self.delbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (90, 24), u"閉じる")
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickDelBtn, self.delbtn)

    def OnClickDelBtn(self, event):
        cw.cwpy.sounds[u"signal"].play()
        header = self.list[self.index]
        s = u"%sを抹消します。\nよろしいですか？" % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, u"メッセージ", s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds[u"dump"].play()
            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.stopalbumthread()
            cw.cwpy.ydata.album.remove(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.closebtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

    def OnSelect(self, event):
        pass


#-------------------------------------------------------------------------------
#　貼り紙選択ダイアログ
#-------------------------------------------------------------------------------

class ScenarioSelect(Select):
    """
    貼り紙選択ダイアログ。
    """
    def __init__(self, parent, db):
        # ダイアログボックス作成
        Select.__init__(self, parent, u"貼紙を見る")
        # シナリオディレクトリ
        self.scedir = u"Scenario"
        # 現在開いているディレクトリ
        self.nowdir = self.scedir
        # 開いたディレクトリの階層
        self.dirstack = []
        # シナリオデータベース
        self.db = db
        # nowdirにあるScenarioHeaderのリスト
        headers = self.db.search_dpath(self.nowdir)
        # nowdirにあるディレクトリリスト
        dpaths = self.get_dpaths(self.nowdir)
        # 冒険者情報
        self.list = dpaths + headers
        self.index = 0
        # nowdirがディレクトリだった場合の内容リスト
        self.names = []
        self.updatenames_thr = None
        # クリアシナリオ名の集合
        self.stamps = cw.cwpy.ydata.get_compstamps()
        # パーティの所持しているクーポンの集合
        self.coupons = cw.cwpy.ydata.party.get_coupons()
        # 現在進行中のシナリオパスの集合
        self.nowplayingpaths = cw.cwpy.ydata.get_nowplayingpaths()
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(400, 370))
        # ok
        if not self.list:
            s = u"決定"
        elif isinstance(self.list[self.index], cw.header.ScenarioHeader):
            s = u"決定"
        else:
            s = u"見る"

        self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_YES, (55, 24), s)
        self.buttonlist.append(self.yesbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (55, 24), u"解説")
        self.buttonlist.append(self.infobtn)
        # convert
        self.convbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (55, 24), u"変換")
        self.buttonlist.append(self.convbtn)
        # close
        self.nobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_NO, (55, 24), u"中止")
        self.buttonlist.append(self.nobtn)
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # リストが空だったらボタンを無効化
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.Bind(wx.EVT_BUTTON, self.OnClickYesBtn, self.yesbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNoBtn, self.nobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickConvBtn, self.convbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.draw(True)

    def OnDropFiles(self, event):
        paths = event.GetFiles()

        for path in paths:
            self.conv_scenario(path)
            time.sleep(0.3)

    def OnClickInfoBtn(self, event):
        cw.cwpy.sounds[u"click"].play()
        dlg = text.Readme(self, u"解説", self.get_texts())
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def OnClickConvBtn(self, evt):
        # ディレクトリ選択ダイアログ
        s = (u"カードワースのシナリオデータをカードワースパイ用に変換します。" +
             u"\n変換するシナリオのディレクトリを選択してください。")
        dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
        dlg.SetPath(os.getcwdu())

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            self.conv_scenario(path)
        else:
            dlg.Destroy()

    def OnClickYesBtn(self, event):
        if self.yesbtn.GetLabel() == u"見る":
            cw.cwpy.sounds[u"equipment"].play()
            self.dirstack.append(self.nowdir)
            self.nowdir = cw.util.get_linktarget(self.list[self.index])
            headers =  self.db.search_dpath(self.nowdir)
            dpaths = self.get_dpaths(self.nowdir)
            self.list = dpaths + headers if headers else dpaths
            self.index = 0
            self.nobtn.SetLabel(u"戻る")
            self.enable_btn()
            self.draw(True)
        elif self.yesbtn.GetLabel() == u"決定":
            cw.cwpy.sounds[u"signal"].play()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

    def OnClickNoBtn(self, event):
        if self.nobtn.GetLabel() == u"戻る":
            cw.cwpy.sounds[u"equipment"].play()
            self.nowdir = self.dirstack.pop()
            headers =  self.db.search_dpath(self.nowdir)
            dpaths = self.get_dpaths(self.nowdir)
            self.list = dpaths + headers if headers else dpaths
            self.index = 0
            self.enable_btn()

            if self.nowdir == self.scedir:
                self.nobtn.SetLabel(u"中止")

            self.draw(True)
        elif self.nobtn.GetLabel() == u"中止":
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

    def OnSelect(self, event):
        if not self.list or not self.yesbtn.Enabled:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        if self.nobtn.GetLabel() == u"中止":
            cw.cwpy.sounds[u"click"].play()

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_NO)
        self.ProcessEvent(btnevent)

    def OnDestroy(self, event):
        self.db.close()

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Bill" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # リストが空だったら描画終了
        if not self.list:
            return

        # ページ番号
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=9))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 340)

        if not isinstance(self.list[self.index], cw.header.ScenarioHeader):
            dpath = self.list[self.index]

            if update:
                if self.updatenames_thr:
                    self.updatenames_thr.quit = True
                    self.updatenames_thr = None
                self.names = [u"読込中..."]
                self.updatenames_thr = UpdateNamesThread(self, dpath)
                self.updatenames_thr.start()

            # ボタンのテキストを変える
            self.yesbtn.SetLabel(u"見る")

            # ディレクトリ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=16))
            s = os.path.basename(dpath)
            if s.lower().endswith(".lnk"):
                s = s[0:-len(".lnk")]
            dc.DrawText(s, 135, 65)
            # フォルダ画像
            bmp = cw.cwpy.rsrc.dialogs["FOLDER"]
            dc.DrawBitmap(bmp, 65, 30, True)

            if sys.platform == "win32" and dpath.lower().endswith(".lnk"):
                # リンクシンボル
                bmp = cw.cwpy.rsrc.dialogs["LINK"]
                dc.DrawBitmap(bmp, 63, 65, False)

            # contents
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=9))
            s = "Contents"
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, 110)
            # 中身
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))

            names = self.names
            if len(names) > 13:
                names = names[0:12]
                names.append("etc...")

            s = "\n".join(names)
            dc.DrawLabel(s, wx.Rect(bmpw/2, 130, 1, 1), wx.ALIGN_CENTER_HORIZONTAL)
            self.yesbtn.Enable()
        else:
            header = self.list[self.index]
            # ボタンのテキストを変える
            self.yesbtn.SetLabel(u"決定")

            # 見出し画像
            if header.image:
                bmp = header.get_wxbmp()
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 65, True)

            # シナリオ名
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=16))
            s = header.name
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, 35)
            # 解説文
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
            s = header.desc
            y = 175
            for l in s.splitlines():
                dc.DrawText(l, 65, y)
#                dc.DrawLabel(s, wx.Rect(65, 175, 1, 1), wx.ALIGN_LEFT)
                y += 15
            # 対象レベル
            dc.SetTextForeground(wx.Colour(0, 128, 128, 255))
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho",
                                            style=wx.FONTSTYLE_ITALIC, size=10))
            levelmax = str(header.levelmax) if header.levelmax else ""
            levelmin = str(header.levelmin) if header.levelmin else ""

            if levelmax or levelmin:
                if levelmin == levelmax:
                    s = u"対象レベル %s" % (levelmin)
                else:
                    s = u"対象レベル %s～%s" % (levelmin, levelmax)

                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)/2, 15)

            self.yesbtn.Enable()

            # 進行中チェック
            if header.get_fpath() in self.nowplayingpaths:
                bmp = cw.cwpy.rsrc.dialogs["PLAYING"]
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 152, True)
                self.yesbtn.Disable()
            # 済み印存在チェック
            elif not cw.cwpy.debug and header.name in self.stamps:
                bmp = cw.cwpy.rsrc.dialogs["COMPLETE"]
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 175, True)
                self.yesbtn.Disable()
            # クーポン存在チェック
            elif not cw.cwpy.debug:
                num = 0

                for coupon in header.coupons.split("\n"):
                    if coupon and coupon in self.coupons:
                        num += 1

                if num < header.couponsnum:
                    bmp = cw.cwpy.rsrc.dialogs["INVISIBLE"]
                    w = bmp.GetSize()[0]
                    dc.DrawBitmap(bmp, (bmpw-w)/2, 100, True)
                    self.yesbtn.Disable()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.convbtn.Enable()
            self.nobtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

    def get_dpaths(self, dpath):
        """
        クラシックなシナリオ以外のフォルダの一覧を返す。
        (ショートカット類も含む)
        """
        seq = []

        dir = cw.util.get_linktarget(dpath)
        for dname in os.listdir(dir):
            path = cw.util.join_paths(dir, dname)

            if os.path.isdir(path):
                spath = cw.util.join_paths(path, "Summary.wsm")
                if not os.path.exists(spath):
                    seq.append(path)
            elif os.path.islink(path):
                seq.append(path)
            elif sys.platform == "win32" and path.lower().endswith(".lnk"):
                seq.append(path)

        return seq

    def get_texts(self):
        """
        選択中シナリオに同梱されている
        テキストファイルのファイル名とデータのリストを返す。
        """
        seq = []
        seq2 = []
        if isinstance(self.list[self.index], cw.header.ScenarioHeader):
            header = self.list[self.index]
            path = cw.util.join_paths(header.dpath, header.fname)
            if os.path.isfile(path):
                # 圧縮ファイル内から取得
                z = zipfile.ZipFile(path, "r")
                names = [name for name in z.namelist() if name.lower().endswith(".txt")]

                for name in names:
                    data = z.read(name)
                    seq2.append(data)
                    name = os.path.basename(name)
                    name = cw.util.decode_zipname(name)
                    seq.append(name)

                z.close()

            else:

                # フォルダ内から取得
                names = []
                for dpath, dnames, fnames in os.walk(path):
                    for fname in fnames:
                        if fname.lower().endswith(".txt"):
                            names.append(fname)

                for name in names:
                    f = open(cw.util.join_paths(path, name), "r")
                    data = f.read()
                    f.close()
                    seq2.append(data)
                    name = os.path.basename(name)
                    seq.append(name)

        return seq, seq2

    def conv_scenario(self, path):
        """
        CardWirthのシナリオデータを変換。
        """
        # CardWirthのシナリオデータか確認
        if not os.path.exists(cw.util.join_paths(path, "Summary.wsm")):

            s = u"カードワースのシナリオのディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        cw.cwpy.sounds[u"click"].play()
        s = os.path.basename(path) + u"　を変換します。\nよろしいですか？"
        dlg = message.YesNoMessage(self, u"メッセージ", s)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        dlg.Destroy()
        # シナリオデータ
        cwdata = cw.binary.cwscenario.CWScenario(
            path, "Data/Temp/OldScenario", cw.cwpy.setting.skintype,
            materialdir="Material", image_export=True)

        # 変換可能なデータか確認
        if not cwdata.is_convertible():
            s = u"CardWirth ver1.20以上対応の\nシナリオしか変換できません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 宿データ読み込み
        cwdata.load()
        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            cwdata.name + u" 変換", "", maximum=cwdata.maxnum,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(cwdata)
        thread.start()

        while not thread.complete:
            dlg.Update(cwdata.curnum, cwdata.message)
            wx.MilliSleep(1)

        dlg.Destroy()
        temppath = thread.path

        # エラーログ表示
        if cwdata.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # zip圧縮
        zpath = os.path.basename(temppath) + ".wsn"
        zpath = cw.util.join_paths(self.nowdir, zpath)
        zpath = cw.util.dupcheck_plus(zpath, False)
        cw.util.compress_zip(temppath, zpath)
        cw.cwpy.sounds[u"harvest"].play()
        # 変換完了ダイアログ
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, u"メッセージ", s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        # tempを削除
        cw.util.remove(temppath)
        # 更新処理
        self.db.insert_scenario(zpath)
        headers = self.db.search_dpath(self.nowdir)
        dpaths = self.get_dpaths(self.nowdir)
        self.list = dpaths + headers if headers else dpaths
        self.index = 0

        # 変換したシナリオのインデックスを取得
        for index, header in enumerate(self.list):
            if not hasattr(header, "fname"):
                continue

            if os.path.basename(zpath) == header.fname:
                self.index = index

        cw.cwpy.sounds[u"page"].play()
        self.draw(True)
        self.enable_btn()

class UpdateNamesThread(threading.Thread):

    def __init__(self, dlg, dpath):
        threading.Thread.__init__(self)
        self.dlg = dlg
        self.dpath = dpath
        self.dpaths = dlg.get_dpaths(dpath)
        self.quit = False

    def run(self):
        """ScenarioSelectで現在表示中のディレクトリ内の
        シナリオ・ディレクトリのリストを生成する。
        """
        self._start()

    @synclock(_lockupdatescenario)
    def _start(self):
        if self.quit: return
        # dpathの中にあるシナリオをDBに登録
        db = cw.scenariodb.Scenariodb()
        db.update(self.dpath)
        if self.quit: return
        # dpathの中にあるシナリオ名のリスト
        headers = db.search_dpath(self.dpath)
        hnames = [header.name for header in headers] if headers else []
        # dpathの中にあるディレクトリ名のリスト
        dnames = []

        if self.quit: return
        for path in self.dpaths:
            if path.lower().endswith(".lnk"):
                path = path[0:-len(".lnk")]
            dname = "[%s]" % os.path.basename(path)
            dnames.append(dname)
        self.dlg.names = dnames + hnames
        if self.quit: return
        wx.CallAfter(self.dlg.Refresh)
        self.dlg.updatenames_thr = None

def main():
    pass

if __name__ == "__main__":
    main()
