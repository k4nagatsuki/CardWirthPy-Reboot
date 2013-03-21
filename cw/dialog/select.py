#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import threading
import zipfile
import StringIO
import shutil
import subprocess
import wx

import cw
import cw.binary
import message
import charainfo
import text

from cw.util import synclock
from wx._controls import EVT_TREE_ITEM_EXPANDED


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
        def empty(event):
            pass
        self.toppanel.Bind(wx.EVT_ERASE_BACKGROUND, empty)
        self.toppanel.Bind(wx.EVT_MIDDLE_UP, self.OnSelect)
        self.toppanel.Bind(wx.EVT_LEFT_UP, self.OnSelect)
        self.toppanel.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.toppanel.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnClickLeftBtn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        else:
            self.index -= 1

        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickLeft2Btn(self, evt):
        if self.index == 0:
            self.index = len(self.list) -1
        elif self.index - 10 < 0:
            self.index = 0
        else:
            self.index -= 10

        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRightBtn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        else:
            self.index += 1

        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRight2Btn(self, evt):
        if self.index == len(self.list) -1:
            self.index = 0
        elif self.index + 10 > len(self.list) -1:
            self.index = len(self.list) -1
        else:
            self.index += 10

        cw.cwpy.sounds["page"].play()
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
        cw.cwpy.sounds["click"].play()
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        self.draw()

    def draw(self, update=False):
        if not self.toppanel.IsShown():
            return None

        if update:
            dc = wx.ClientDC(self.toppanel)
            dc = wx.BufferedDC(dc, self.toppanel.GetSize())
        else:
            dc = wx.BufferedPaintDC(self.toppanel)

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

        # sizer_panelにbuttonを設定
        for button in self.buttonlist:
            sizer_panel.Add((margin, 0), 0, 0, 0)
            sizer_panel.Add(button, 0, wx.TOP|wx.BOTTOM, 3)

        sizer_panel.Add((margin, 0), 0, 0, 0)
        sizer_panel.Add(self.rightbtn, 0, 0, 0)
        sizer_panel.Add(self.right2btn, 0, 0, 0)
        self.panel.SetSizer(sizer_panel)

        self.topsizer = wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.toppanel, 1, wx.EXPAND, 0)

        sizer_1.Add(self.topsizer, 1, wx.EXPAND, 0)
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
        Select.__init__(self, parent, cw.cwpy.msgs["select_base_title"])
        # 宿情報
        self.names, self.list, self.list2 = self.get_yadolist()
        self.index = 0
        for index, name in enumerate(self.names):
            if cw.cwpy.setting.lastyado == name:
                self.index = index
                break
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(400, 370))
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, (50, 24), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.okbtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["new"])
        self.buttonlist.append(self.newbtn)
        # extend
        self.extbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), u"変換")
        self.buttonlist.append(self.extbtn)
        # extension
        self.exbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["extension"])
        self.buttonlist.append(self.exbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (50, 24), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)
        # enable bottun
        self.enable_btn()
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExtBtn, self.extbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExBtn, self.exbtn)
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

    def OnClickExBtn(self, event):
        """
        拡張。
        """
        cw.cwpy.sounds["click"].play()
        yname = self.names[self.index]
        title = cw.cwpy.msgs["extension_title"] % (yname)
        items = [
            (cw.cwpy.msgs["rename"], cw.cwpy.msgs["rename_base_description"], self.rename_yado),
            (cw.cwpy.msgs["copy"], cw.cwpy.msgs["copy_base_description"], self.copy_yado),
            (u"逆変換", u"選択中の拠点データをCardWirth用のデータに逆変換します。", self.unconv_yado),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_base_description"], self.delete_yado),
        ]
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def rename_yado(self):
        """
        宿改名。
        """
        cw.cwpy.sounds["click"].play()
        path = self.list[self.index]
        dlg = cw.dialog.edit.YadoEditDialog(self, path)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["harvest"].play()
            self.update_list(dlg.yadodir)

        dlg.Destroy()

    def copy_yado(self):
        """
        宿複製。
        """
        cw.cwpy.sounds["signal"].play()
        path = self.list[self.index]
        yname = self.names[self.index]
        s = cw.cwpy.msgs["copy_base"] % (yname)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            env = cw.util.join_paths(path, "Environment.xml")
            data = cw.data.xml2etree(env)
            name = data.gettext("Property/Name", os.path.basename(path))
            name = u"コピー - %s" % (name)
            if not data.find("Property/Name") is None:
                data.edit("Property/Name", name)
            else:
                e = data.make_element("Name", name)
                data.insert("Property", e, 0)

            newpath = cw.binary.util.check_filename(name)
            newpath = cw.util.join_paths(os.path.dirname(path), newpath)
            newpath = cw.binary.util.check_duplicate(newpath)
            shutil.copytree(path, newpath)
            env = cw.util.join_paths(newpath, "Environment.xml")
            data.write(env)
            cw.cwpy.sounds["harvest"].play()
            self.update_list(newpath)

        dlg.Destroy()

    def delete_yado(self):
        """
        宿削除。
        """
        cw.cwpy.sounds["signal"].play()
        path = self.list[self.index]
        yname = self.names[self.index]
        s = cw.cwpy.msgs["delete_base"] % (yname)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.util.remove(path)
            cw.cwpy.sounds["dump"].play()
            self.update_list()

        dlg.Destroy()

    def OnClickNewBtn(self, event):
        """
        宿新規作成。
        """
        dlg = cw.dialog.create.YadoCreater(self)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["harvest"].play()
            self.update_list(dlg.yadodir)

        dlg.Destroy()

    def OnClickExtBtn(self, evt):
        """
        CardWirthの宿データを変換。
        """
        # ディレクトリ選択ダイアログ
        s = (u"CardWirthの宿のデータをCardWirthPy用に変換します。" +
              u"\n変換する宿のフォルダを選択してください。")
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
        s = self.names[self.index]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 40)
        # ページ番号
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
        s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
        s = s + "/" + str(len(self.list))
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 340)
        # Adventurers
        s = cw.cwpy.msgs["adventurers"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 175)

        # 所属冒険者
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
        for idx, name in enumerate(self.list2[self.index]):
            x = (bmpw - 270) / 2 + ((idx % 3) * 95)
            y = 200 + (idx / 3) * 16
            dc.DrawText(name, x, y)

    def conv_yado(self, path):
        """
        CardWirthの宿データを変換。
        """
        # カードワースの宿か確認
        if not os.path.exists(cw.util.join_paths(path, "Environment.wyd")):
            s = u"CardWirthの宿のディレクトリではありません。"
            dlg = message.ErrorMessage(self, s)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        cw.cwpy.sounds["click"].play()
        s = os.path.basename(path) + u" を変換します。\nよろしいですか？"
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
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

        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            cwdata.name + u" 変換", "", maximum=100,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(cwdata)
        thread.start()

        while not thread.complete:
            dlg.Update(cwdata.curnum, cwdata.message)
            wx.MilliSleep(1)

        dlg.Destroy()
        yadodir = thread.path

        # エラーログ表示
        if cwdata.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, cwdata.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # 変換完了ダイアログ
        cw.cwpy.sounds["harvest"].play()
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()
        cw.cwpy.sounds["page"].play()
        self.update_list(yadodir)

    def unconv_yado(self):
        """
        CardWirthの宿データへ逆変換。
        """
        yadodir = self.list[self.index]
        yadoname = self.names[self.index]

        # ディレクトリ選択ダイアログ
        s = (u"この拠点のデータをCardWirth用に逆変換します。" +
              u"\n変換先のフォルダを選択してください。")
        dlg = wx.DirDialog(self, s, style=wx.DD_DIR_MUST_EXIST)
        dlg.SetPath(os.getcwdu())

        if dlg.ShowModal() == wx.ID_OK:
            dstpath = dlg.GetPath()
            dlg.Destroy()
        else:
            dlg.Destroy()
            return

        # 変換確認ダイアログ
        cw.cwpy.sounds["click"].play()
        s = u"%s を逆変換し、\n新規作成したフォルダへ格納します。\nよろしいですか？" % (yadoname)
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        self.Parent.move_dlg(dlg)

        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return

        dlg.Destroy()

        # 宿データ
        cw.cwpy.yadodir = cw.util.join_paths(yadodir)
        cw.cwpy.tempdir = cw.cwpy.yadodir.replace("Yado", "Data/Temp/Yado", 1)
        ydata = cw.data.YadoData(cw.cwpy.yadodir, cw.cwpy.tempdir, loadparty=False)

        # コンバータ
        unconv = cw.binary.cwyado.UnconvCWYado(ydata, dstpath)

        # プログレスダイアログ表示
        dlg = wx.ProgressDialog(
            u"%s 逆変換" % (yadoname), "", maximum=unconv.maxnum,
            parent=self, style=wx.PD_APP_MODAL|wx.PD_AUTO_HIDE|
            wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME)
        thread = cw.binary.ConvertingThread(unconv)
        thread.start()

        while not thread.complete:
            dlg.Update(unconv.curnum, unconv.message)
            wx.MilliSleep(1)

        cw.cwpy.yadodir = ""
        cw.cwpy.tempdir = ""
        dlg.Destroy()

        # エラーログ表示
        if unconv.errorlog:
            dlg = cw.dialog.etc.ErrorLogDialog(self, unconv.errorlog)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        # 変換完了ダイアログ
        cw.cwpy.sounds["harvest"].play()
        s = u"データの逆変換が完了しました。\n%s" % (unconv.dir)
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_list(self, yadodir=""):
        """
        登録されている宿のリストを更新して、
        引数のnameの宿までページを移動する。
        """
        self.names, self.list, self.list2 = self.get_yadolist()

        try:
            self.index = self.list.index(yadodir)
        except:
            self.index = 0

        self.draw(True)
        self.enable_btn()

    def get_yadolist(self):
        """Yadoにある宿のpathリストと冒険者リストを返す。"""
        names = []
        yadodirs = []

        if not os.path.exists(u"Yado"):
            os.makedirs(u"Yado")

        for dname in os.listdir(u"Yado"):
            path  = cw.util.join_paths(u"Yado", dname, "Environment.xml")

            if os.path.isfile(path):
                name = cw.header.GetName(path).name
                if not name:
                    name = os.path.basename(dname)
                names.append(name)
                path  = cw.util.join_paths(u"Yado", dname)
                yadodirs.append(path)

        advnames = []

        for yadodir in yadodirs:
            seq = []

            yadodb = cw.yadodb.YadoDB(yadodir)
            standbys = yadodb.get_standbynames(25)
            if len(standbys) == 0:
                yadodb.update(cards=False, adventurers=True, parties=False)
                standbys = yadodb.get_standbynames(25)

            if 25 <= len(standbys):
                seq = standbys[:23]
                seq.append(cw.cwpy.msgs["scenario_etc"])
            else:
                seq = standbys

            yadodb.close()
            advnames.append(seq)

        return names, yadodirs, advnames

#-------------------------------------------------------------------------------
#　パーティ選択ダイアログ
#-------------------------------------------------------------------------------

class PartySelect(Select):
    """
    パーティ選択ダイアログ。
    """
    def __init__(self, parent):
        # ダイアログボックス作成
        Select.__init__(self, parent, cw.cwpy.msgs["resume_adventure"])
        # パーティ情報
        self.list = cw.cwpy.ydata.partys
        self.index = 0
        self.names = []
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        # ok
        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_OK, (75, 24), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.okbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (75, 24), cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # edit
        self.editbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (75, 24), cw.cwpy.msgs["members"])
        self.buttonlist.append(self.editbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (75, 24), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickEditBtn, self.editbtn)

        self.draw(True)

    def OnClickInfoBtn(self, event):
        header = self.list[self.index]
        party = cw.data.Party(header, True)

        dlg = cw.dialog.edit.PartyEditor(self.Parent, party)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            party.data.write_xml()
            header = cw.cwpy.ydata.create_partyheader(element=party.data.find("Property"))
            self.list[self.index] = header
            cw.cwpy.ydata.partys[self.index] = header
            self.draw(True)

    def OnClickEditBtn(self, event):
        def redrawfunc():
            header = self.list[self.index]
            header = cw.cwpy.ydata.create_partyheader(header.fpath)
            self.list[self.index] = header
            cw.cwpy.ydata.partys[self.index] = header
            self.draw(True)
        header = self.list[self.index]
        party = cw.data.Party(header, True)
        headers = []
        for memberpath in party.get_memberpaths():
            headers.append(cw.cwpy.ydata.create_advheader(memberpath))

        dlg = cw.dialog.charainfo.StandbyCharaInfo(self.Parent, headers, 0, redrawfunc)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

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
        s = cw.cwpy.msgs["adventurers_team"]
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 25)
        # 所持金
        s = cw.cwpy.msgs["adventurers_money"] % (header.money)
        w = dc.GetTextExtent(s)[0]
        dc.DrawText(s, (bmpw-w)/2, 60)

        # メンバ名
        if update:
            self.names = header.get_membernames()
        if len(header.members) > 3:
            n = (3, len(self.names) - 3)
        else:
            n = (len(self.names), 0)

        w = 90

        for index, s in enumerate(self.names):
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
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
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
        Select.__init__(self, parent, cw.cwpy.msgs["select_member_title"])
        # 冒険者情報
        self.list = cw.cwpy.ydata.standbys
        self.isalbum = False
        self.index = 0
        self.views = 1
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        self.toppanel.SetMinSize((460, 280))

        # sort
        self.sort = wx.combo.BitmapComboBox(self.toppanel, size=(60, 20), style=wx.CB_READONLY)
        self.sort.Append(cw.cwpy.msgs["sort_no"])
        self.sort.Append(cw.cwpy.msgs["sort_name"])
        self.sort.Append(cw.cwpy.msgs["sort_level"])
        if cw.cwpy.setting.sort_standbys == "Name":
            self.sort.Select(1)
        elif cw.cwpy.setting.sort_standbys == "Level":
            self.sort.Select(2)
        else:
            self.sort.Select(0)

        # add
        self.addbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_ADD, (50, 24), cw.cwpy.msgs["add_member"])
        self.buttonlist.append(self.addbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # new
        self.newbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["new"])
        self.buttonlist.append(self.newbtn)
        # extension
        self.exbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["extension"])
        self.buttonlist.append(self.exbtn)
        # view
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (50, 24), cw.cwpy.msgs["member_list"])
        self.buttonlist.append(self.viewbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (50, 24), cw.cwpy.msgs["close"])
        self.buttonlist.append(self.closebtn)
        # enable btn
        self.enable_btn()
        # layout
        self._do_layout()
        # bind
        self._bind()
        self.Bind(wx.EVT_BUTTON, self.OnClickAddBtn, self.addbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNewBtn, self.newbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickExBtn, self.exbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        self.Bind(wx.EVT_COMBOBOX, self.OnSort, self.sort)
        self.toppanel.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add((398, 0), 0)
        sizer.Add(self.sort, 0, wx.TOP, 2)
        self.toppanel.SetSizer(sizer)
        self.toppanel.Layout()

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            self.newbtn.Enable()
            self.closebtn.Enable()
        elif len(self.list) <= self.views:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
            if not self.list:
                self.index = 0
        else:
            self._enable_btn()

        # 冒険者が6人だったら追加ボタン無効化
        if len(cw.cwpy.get_pcards()) == 6:
            self.addbtn.Disable()

    def OnSort(self, event):
        if self.isalbum:
            return

        index = self.sort.GetSelection()
        if index == 1:
            sorttype = "Name"
        elif index == 2:
            sorttype = "Level"
        else:
            sorttype = "None"

        if cw.cwpy.setting.sort_standbys <> sorttype:
            cw.cwpy.sounds["page"].play()
            cw.cwpy.setting.sort_standbys = sorttype
            cw.cwpy.ydata.sort_standbys()
            self.draw(True)

    def OnLeftDClick(self, event):
        # 一覧表示の場合はダブルクリックで編入
        if not self.list or len(cw.cwpy.get_pcards()) == 6:
            return
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ADD)
        self.ProcessEvent(btnevent)

    def OnMouseWheel(self, event):
        if self.sort and self.sort.GetRect().Contains(event.GetPosition()):
            index = self.sort.GetSelection()
            count = self.sort.GetCount()
            if event.GetWheelRotation() > 0:
                if index <= 0:
                    index = count - 1
                else:
                    index -= 1
            else:
                if count <= index + 1:
                    index = 0
                else:
                    index += 1
            self.sort.Select(index)
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_COMBOBOX_SELECTED, self.sort.GetId())
            self.ProcessEvent(btnevent)
            return
        if not self.list or len(self.list) == 1:
            return

        count = self.views
        if len(self.list) <= self.views:
            count = 1

        if event.GetWheelRotation() > 0:
            self.index = cw.util.number_normalization(self.index - count, 0, len(self.list))
        else:
            self.index = cw.util.number_normalization(self.index + count, 0, len(self.list))
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickLeftBtn(self, evt):
        if self.views == 1 or evt.GetEventObject() <> self.leftbtn or len(self.list) <= self.views:
            Select.OnClickLeftBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index - self.views, 0, len(self.list))
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickLeft2Btn(self, evt):
        if self.views == 1 or evt.GetEventObject() <> self.left2btn or len(self.list) <= self.views:
            Select.OnClickLeft2Btn(self, evt)
            return
        if self.get_page() == 0:
            self.index = len(self.list) - 1
        elif self.index - self.views * 10 < 0:
            self.index = 0
        else:
            self.index = self.index - self.views * 10
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRightBtn(self, evt):
        if self.views == 1 or evt.GetEventObject() <> self.rightbtn or len(self.list) <= self.views:
            Select.OnClickRightBtn(self, evt)
            return
        self.index = cw.util.number_normalization(self.index + self.views, 0, len(self.list))
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnClickRight2Btn(self, evt):
        if self.views == 1 or evt.GetEventObject() <> self.right2btn or len(self.list) <= self.views:
            Select.OnClickRight2Btn(self, evt)
            return
        if self.get_page() == self.get_pagecount()-1:
            self.index = 0
        elif len(self.list) <= self.index + self.views * 10:
            self.index = len(self.list) - 1
        else:
            self.index = self.index + self.views * 10
        cw.cwpy.sounds["page"].play()
        self.draw(True)

    def OnSelect(self, event):
        if self.views == 1:
            # 一人だけ表示している場合は編入
            if not self.list or len(cw.cwpy.get_pcards()) == 6:
                return

            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_ADD)
            self.ProcessEvent(btnevent)
        else:
            # 複数表示中はマウスポインタ直下を選択
            mousepos = self.toppanel.ScreenToClient(wx.GetMousePosition())
            size = self.toppanel.GetSize()
            rw = size[0] / (self.views / 2)
            rh = size[1] / 2
            sindex = (mousepos[0] / rw) + ((mousepos[1] / rh) * (self.views / 2))
            page = self.get_page()
            index = page * self.views + sindex
            if self.index <> index:
                cw.cwpy.sounds["click"].play()
                self.index = min(index, len(self.list)-1)
                self.enable_btn()
                self.draw(True)

    def OnClickNewBtn(self, event):
        cw.cwpy.sounds["click"].play()
        if cw.cwpy.setting.debug:
            dlg = cw.debug.charaedit.CharacterEditDialog(self, create=True)
            cw.cwpy.frame.move_dlg(dlg)
        else:
            dlg = cw.dialog.create.AdventurerCreater(self)
            cw.cwpy.frame.move_dlg(dlg, point=(20, 20))

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["page"].play()
            header = cw.cwpy.ydata.add_standbys(dlg.fpath)
            # リスト更新
            self.list = cw.cwpy.ydata.standbys
            self.index = self.list.index(header)
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def OnClickAddBtn(self, event):
        # カード表示中の場合は処理中止
        if cw.cwpy.is_dealing():
            return

        cw.cwpy.sounds["harvest"].play()
        header = self.list[self.index]
        cw.cwpy.ydata.standbys.remove(header)

        def func(header):
            if cw.cwpy.ydata.party:
                if len(cw.cwpy.ydata.party.members) < 6:
                    cw.cwpy.ydata.party.add(header)
                else:
                    # 追加できなかった
                    cw.cwpy.ydata.standbys.insert(self.index, header)
                    return
            else:
                cw.cwpy.ydata.create_party(header, chgarea=False)
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
            def func():
                self.enable_btn()
                self.draw(True)
            cw.cwpy.frame.exec_func(func)
        cw.cwpy.exec_func(func, header)

    def OnClickExBtn(self, event):
        """
        拡張。
        """
        cw.cwpy.sounds["click"].play()
        name = self.list[self.index].name
        title = cw.cwpy.msgs["extension_title"] % (name)
        items = [
            (cw.cwpy.msgs["grow"], cw.cwpy.msgs["grow_adventurer_description"], self.grow_adventurer),
            (cw.cwpy.msgs["delete"], cw.cwpy.msgs["delete_adventurer_description"], self.delete_adventurer),
        ]
        dlg = cw.dialog.etc.ExtensionDialog(self, title, items)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def grow_adventurer(self):
        header = self.list[self.index]
        age = header.age
        index = cw.cwpy.setting.periodcoupons.index(age)

        if index < 0:
            # 年代が不正。スキンが違う場合は発生しうる
            cw.cwpy.sounds["error"].play()
            return

        if index == len(cw.cwpy.setting.periodcoupons) - 1:
            nextage= None
            s = cw.cwpy.msgs["confirm_die"] % (header.name)
        else:
            nextage= cw.cwpy.setting.periodcoupons[index + 1]
            s = cw.cwpy.msgs["confirm_grow"] % (header.name, age[1:], nextage[1:])

        cw.cwpy.sounds["signal"].play()
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            cw.cwpy.sounds["harvest"].play()
            if nextage:
                header.grow()
            else:
                s = cw.cwpy.msgs["die_message"] % (header.name)
                dlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s, 2)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()

                if not header.leavenoalbum:
                    path = cw.xmlcreater.create_albumpage(header.fpath)
                    cw.cwpy.ydata.add_album(path)
                cw.cwpy.remove_xml(header)
                cw.cwpy.ydata.standbys.remove(header)
                if len(self.list):
                    self.index %= len(self.list)
                else:
                    self.index = 0
                self.enable_btn()

            self.draw(True)
        else:
            dlg.Destroy()

    def delete_adventurer(self):
        cw.cwpy.sounds["signal"].play()
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["dump"].play()
            # 手札カードを移動させる
            data = cw.data.yadoxml2etree(header.fpath)
            ccard = cw.character.Character(data)
            for pocket in ccard.cardpocket:
                for card in pocket:
                    cw.cwpy.trade("STOREHOUSE", header=card, from_event=True, sort=False)
            cw.cwpy.ydata.sort_storehouse()

            # レベル3以上・"＿消滅予約"を持ってない場合、アルバムに残す
            if header.level >= 3 and not header.leavenoalbum:
                path = cw.xmlcreater.create_albumpage(header.fpath, nocoupon=True)
                cw.cwpy.ydata.add_album(path)

            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.standbys.remove(header)
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
            self.enable_btn()
            self.draw(True)

        dlg.Destroy()

    def OnClickInfoBtn(self, event):
        cw.cwpy.sounds["click"].play()
        dlg = charainfo.StandbyCharaInfo(self, self.list, self.index, self.update_character)
        self.Parent.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    def update_character(self):
        header = self.list[self.index]
        header = cw.cwpy.ydata.create_advheader(header.fpath)
        cw.cwpy.ydata.standbys[self.index] = header
        self.list[self.index] = header
        self.draw(True)

    def OnClickViewBtn(self, event):
        cw.cwpy.sounds["equipment"].play()
        if self.views == 1:
            self.views = 10
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_one"])
        else:
            self.views = 1
            self.viewbtn.SetLabel(cw.cwpy.msgs["member_list"])
        self.draw(True)

    def get_page(self):
        return self.index / self.views

    def get_pagecount(self):
        return (len(self.list) + self.views - 1) / self.views

    def draw(self, update=False):
        dc = Select.draw(self, update)
        # 背景
        path = "Table/Book" + cw.cwpy.rsrc.ext_img
        path = cw.util.join_paths(cw.cwpy.skindir, path)
        bmp = cw.util.load_wxbmp(path)
        bmpw = bmp.GetSize()[0]
        dc.DrawBitmap(bmp, 0, 0, False)

        # 縁取りしながら描画
        def drawwitharound(dc, s, x, y):
            for xv in xrange(x-1, x+2):
                for yv in xrange(y-1, y+2):
                    if x <> xv or y <> yv:
                        dc.SetTextForeground(wx.WHITE)
                        dc.DrawText(s, xv, yv)
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(s, x, y)

        if self.list:
            if self.views == 1:
                header = self.list[self.index % len(self.list)]
                # Level
                dc.SetTextForeground(wx.BLACK)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
                s = cw.cwpy.msgs["character_level"]
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 65, 45)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=22))
                s = str(header.level)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 110, 31)
                # Name
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
                s = cw.cwpy.msgs["character_class"]
                dc.DrawText(s, 110 + w + 5, 45)
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
                s = cw.cwpy.msgs["character_age"] % (header.get_age())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 127 - w / 2, 195)
                # Sex
                s = cw.cwpy.msgs["character_sex"] % (header.get_sex())
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 127 - w / 2, 210)
                # EP
                s = cw.cwpy.msgs["character_ep"] % (header.ep)
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 127 - w / 2, 225)

                # クーポン(新しい順から7つ)
                s = cw.cwpy.msgs["character_history"]
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, 320 - w / 2, 65)
                for index, s in enumerate(header.history):
                    w = dc.GetTextExtent(s)[0]
                    dc.DrawText(s, 320 - w / 2, 95 + 15 * index)

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
                s = str(self.index+1) if self.index > 0 else str(-self.index + 1)
                s = s + "/" + str(len(self.list))
                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)/2, 250)
            else:
                page = self.get_page()

                sindex = page * self.views
                list = self.list[sindex:sindex+self.views]
                x = 0
                y = 0
                size = self.toppanel.GetSize()
                rw = size[0] / (self.views / 2)
                rh = size[1] / 2
                dc.SetTextForeground(wx.BLACK)
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
                for i, header in enumerate(list):
                    # Image
                    path = cw.util.join_yadodir(header.imgpath)
                    bmp = cw.util.load_wxbmp(path, True)
                    ix = x + (rw - 72) / 2
                    iy = y + 5
                    dc.DrawBitmap(bmp, ix, iy, True)

                    # Name
                    s = header.name
                    w = dc.GetTextExtent(s)[0]
                    drawwitharound(dc, s, x + (rw - w) / 2, y + 105)
                    # Level
                    s1 = cw.cwpy.msgs["character_level"]
                    w1 = dc.GetTextExtent(s1)[0]
                    s2 = str(header.level)
                    w2 = dc.GetTextExtent(s2)[0]
                    sx = x + (rw - (w1+5+w2)) / 2
                    sy = y + 120
                    drawwitharound(dc, s1, sx, sy)
                    drawwitharound(dc, s2, sx + w1 + 5, sy)
                    # Selected
                    if sindex + i == self.index:
                        bmp = cw.image.conv2wxbmp(cw.cwpy.rsrc.statuses["TARGET"])
                        dc.DrawBitmap(bmp, ix + 58, iy + 80)

                    if self.views / 2 == i + 1:
                        x = 0
                        y += rh
                    else:
                        x += rw

                # ページ番号
                dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
                s = str(page+1) if page > 0 else str(-page + 1)
                s = s + "/" + str(self.get_pagecount())
                drawwitharound(dc, s, 5, 5)

        # 整列
        if self.sort:
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("uigothic", size=10))
            s = cw.cwpy.msgs["sort_title"]
            drawwitharound(dc, s, 358, 5)

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
        Select.__init__(self, parent, cw.cwpy.msgs["album"])
        # 冒険者情報
        self.list = cw.cwpy.ydata.album
        self.isalbum = True
        self.index = 0
        self.views = 1
        self.sort = None
        # toppanel
        self.toppanel = wx.Panel(self, -1, size=(460, 280))
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_PROPERTIES, (90, 24), cw.cwpy.msgs["information"])
        self.buttonlist.append(self.infobtn)
        # delete
        self.delbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_DELETE, (90, 24), cw.cwpy.msgs["delete"])
        self.buttonlist.append(self.delbtn)
        # close
        self.closebtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_CANCEL, (90, 24), cw.cwpy.msgs["close"])
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
        cw.cwpy.sounds["signal"].play()
        header = self.list[self.index]
        s = cw.cwpy.msgs["confirm_delete_character_in_album"] % (header.name)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        if dlg.ShowModal() == wx.ID_OK:
            cw.cwpy.sounds["dump"].play()
            cw.cwpy.remove_xml(header)
            cw.cwpy.ydata.album.remove(header)
            if len(self.list):
                self.index %= len(self.list)
            else:
                self.index = 0
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
        Select.__init__(self, parent, cw.cwpy.msgs["select_scenario_title"])
        # シナリオディレクトリ
        self.scedir = u"Scenario"
        # 現在開いているディレクトリ
        self.nowdir = self.scedir
        # 開いたディレクトリの階層
        self.dirstack = []
        # シナリオデータベース
        self.db = db
        # nowdirにあるScenarioHeaderのリスト
        self.db.update()
        headers = self.db.search_dpath(self.nowdir)
        # nowdirにあるディレクトリリスト
        dpaths = self.get_dpaths(self.nowdir)
        # 選択リスト
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

        # ツリー表示用のビュー
        self.tree = wx.TreeCtrl(self, -1, size=(400, 370),
            style=wx.BORDER|wx.TR_SINGLE|wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE)
        self.tree.Hide()
        self.tree.imglist = wx.ImageList(16, 16)
        self.tree.imgidx_summary = self.tree.imglist.Add(cw.cwpy.rsrc.debugs["SUMMARY"])
        self.tree.imgidx_complete = self.tree.imglist.Add(cw.cwpy.rsrc.debugs["SUMMARY_COMPLETE"])
        self.tree.imgidx_playing = self.tree.imglist.Add(cw.cwpy.rsrc.debugs["SUMMARY_PLAYING"])
        self.tree.imgidx_invisible = self.tree.imglist.Add(cw.cwpy.rsrc.debugs["SUMMARY_INVISIBLE"])
        self.tree.imgidx_dir = self.tree.imglist.Add(cw.cwpy.rsrc.debugs["DIRECTORY"])
        self.tree.root = self.tree.AddRoot(self.scedir)
        self.tree.SetItemPyData(self.tree.root, (0, self.scedir))
        self.tree.SetImageList(self.tree.imglist)
        self.tree.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

        # ok
        self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_YES, (55, 24), cw.cwpy.msgs["decide"])
        self.buttonlist.append(self.yesbtn)
        # info
        self.infobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (55, 24), cw.cwpy.msgs["description"])
        self.buttonlist.append(self.infobtn)
        # view
        self.viewbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (55, 24), cw.cwpy.msgs["scenario_tree"])
        self.buttonlist.append(self.viewbtn)
        # convert
        ##self.convbtn = cw.cwpy.rsrc.create_wxbutton(self.panel, -1, (55, 24), u"変換")
        ##self.buttonlist.append(self.convbtn)
        # close
        self.nobtn = cw.cwpy.rsrc.create_wxbutton(self.panel, wx.ID_NO, (55, 24), cw.cwpy.msgs["entry_cancel"])
        self.buttonlist.append(self.nobtn)
        # ドロップファイル機能ON
        self.DragAcceptFiles(True)
        # リストが空だったらボタンを無効化
        self.enable_btn()
        # layout
        self._do_layout()
        self.topsizer.Add(self.tree, 1, wx.EXPAND, 0)
        # bind
        self._bind()
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_DROP_FILES, self.OnDropFiles)
        self.Bind(wx.EVT_BUTTON, self.OnClickYesBtn, self.yesbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickNoBtn, self.nobtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickViewBtn, self.viewbtn)
        ##self.Bind(wx.EVT_BUTTON, self.OnClickConvBtn, self.convbtn)
        self.Bind(wx.EVT_BUTTON, self.OnClickInfoBtn, self.infobtn)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnTreeItemCollapsed)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelChanged)
        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.tree.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.draw(True)

    def OnLeftDClick(self, event):
        selitem = self.tree.GetSelection()
        if not selitem:
            return
        data = self.tree.GetItemPyData(selitem)
        if not data:
            return
        index, pathorheader = data
        if isinstance(pathorheader, cw.header.ScenarioHeader):
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
            self.ProcessEvent(btnevent)
        else:
            if self.tree.IsExpanded(selitem):
                cw.cwpy.sounds["page"].play()
                self.tree.Collapse(selitem)
            else:
                cw.cwpy.sounds["equipment"].play()
                self.tree.Expand(selitem)

    def OnKeyUp(self, event):
        if event.GetKeyCode() <> wx.WXK_RETURN:
            return

        selitem = self.tree.GetSelection()
        if not selitem:
            return
        data = self.tree.GetItemPyData(selitem)
        if not data:
            return
        index, pathorheader = data
        if isinstance(pathorheader, cw.header.ScenarioHeader):
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
            self.ProcessEvent(btnevent)

    def get_selected(self):
        """
        現在選択されているシナリオを経路形式
        (ディレクトリ・ファイル名の配列)で返す。
        """
        seq = []
        if not self.list:
            return seq

        for dpath, selname in self.dirstack:
            seq.append(selname)
        sel = self.list[self.index]
        if isinstance(sel, cw.header.ScenarioHeader):
            seq.append(sel.fname)
        else:
            seq.append(os.path.basename(sel))
        return seq

    def set_selected(self, spaths):
        """
        シナリオを経路形式(ディレクトリ・ファイル名の配列)で
        設定する。
        """
        if not spaths:
            self.nowdir = self.scedir
            self.index = 0
            self.dirstack = []
            dpaths = self.get_dpaths(self.nowdir)
            headers = self.db.search_dpath(self.nowdir)
            self.list = dpaths + headers
        else:
            parent = self.scedir
            self.dirstack = []
            for fname in spaths[:-1]:
                self.dirstack.append((parent, fname))
                parent = cw.util.join_paths(parent, fname)
                parent = cw.util.get_linktarget(parent)
            self.nowdir = parent
            dpaths = self.get_dpaths(self.nowdir)
            headers = self.db.search_dpath(self.nowdir)
            self.list = dpaths + headers
            self.index = 0

            fname = os.path.normcase(spaths[-1])
            for index, sel in enumerate(self.list):
                if isinstance(sel, cw.header.ScenarioHeader):
                    name = sel.fname
                else:
                    name = os.path.basename(sel)
                if os.path.normcase(name) == fname:
                    self.index = index
                    break

        self.draw(True)
        self.enable_btn()

    def OnDropFiles(self, event):
        paths = event.GetFiles()

        for path in paths:
            self.conv_scenario(path)
            time.sleep(0.3)

    def OnClickInfoBtn(self, event):
        cw.cwpy.sounds["click"].play()
        dlg = text.Readme(self, cw.cwpy.msgs["description"], self.get_texts())
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
        if self.yesbtn.GetLabel() == cw.cwpy.msgs["see"]:
            assert not self.tree.IsShown()
            cw.cwpy.sounds["equipment"].play()
            self.dirstack.append((self.nowdir, os.path.basename(self.list[self.index])))
            self.nowdir = cw.util.get_linktarget(self.list[self.index])
            headers =  self.db.search_dpath(self.nowdir)
            dpaths = self.get_dpaths(self.nowdir)
            self.list = dpaths + headers if headers else dpaths
            self.index = 0
            self.enable_btn()
            self.draw(True)
        elif self.yesbtn.GetLabel() == cw.cwpy.msgs["decide"]:
            cw.cwpy.sounds["signal"].play()
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            self.ProcessEvent(btnevent)

    def OnClickNoBtn(self, event):
        if self.nobtn.GetLabel() == cw.cwpy.msgs["return"]:
            assert not self.tree.IsShown()
            cw.cwpy.sounds["equipment"].play()
            self.nowdir, selname = self.dirstack.pop()
            headers =  self.db.search_dpath(self.nowdir)
            dpaths = self.get_dpaths(self.nowdir)
            self.list = dpaths + headers if headers else dpaths
            self.index = 0
            selname = os.path.normcase(selname)
            for index, name in enumerate(self.list):
                if not isinstance(name, cw.header.ScenarioHeader):
                    name = os.path.normcase(os.path.basename(name))
                    if selname == name:
                        self.index = index

            self.enable_btn()

            self.draw(True)
        elif self.nobtn.GetLabel() == cw.cwpy.msgs["entry_cancel"]:
            btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
            self.ProcessEvent(btnevent)

    def OnClickViewBtn(self, event):
        cw.cwpy.sounds["equipment"].play()
        if self.tree.IsShown():
            self.tree.Hide()
            self.toppanel.Show()
        else:
            self.show_tree()
            self.toppanel.Hide()
            self.tree.Show()

        self.enable_btn()

    def OnSelect(self, event):
        if not self.list or not self.yesbtn.Enabled:
            return

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event):
        if self.nobtn.GetLabel() == cw.cwpy.msgs["entry_cancel"]:
            cw.cwpy.sounds["click"].play()

        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_NO)
        self.ProcessEvent(btnevent)

    def OnDestroy(self, event):
        self.db.close()

    def draw(self, update=False):
        if update:
            self.enable_btn()

        if self.tree.IsShown():
            self.select_treeitem(self.index)
            return

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
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))
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
                self.updatenames_thr = UpdateNamesThread(self, dpath, self.dirstack[:])
                self.updatenames_thr.start()

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
            s = cw.cwpy.msgs["contents"]
            w = dc.GetTextExtent(s)[0]
            dc.DrawText(s, (bmpw-w)/2, 110)
            # 中身
            dc.SetFont(cw.cwpy.rsrc.get_wxfont("mincho", size=10))

            names = self.names
            if len(names) > 13:
                names = names[0:12]
                names.append(cw.cwpy.msgs["history_etc"])

            y = 130
            for name in names:
                if isinstance(name, cw.header.ScenarioHeader):
                    header = name
                    name = name.name
                    if self.is_playing(header) or self.is_complete(header) or self.is_invisible(header):
                        dc.SetTextForeground((128, 128, 128))
                    else:
                        dc.SetTextForeground((0, 0, 0))
                else:
                    dc.SetTextForeground((0, 0, 0))
                size = dc.GetTextExtent(name)
                x = (bmpw - size[0]) / 2
                dc.DrawText(name, x, y)
                y += 15
            self.yesbtn.Enable()
        else:
            header = self.list[self.index]

            # 見出し画像
            if header.image:
                bmp = header.get_wxbmp()
                w = bmp.GetSize()[0]
                # 左上位置固定(互換性維持)
                dc.DrawBitmap(bmp, 163, 65, True)

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
                    s = cw.cwpy.msgs["target_level_1"] % (levelmin)
                else:
                    s = cw.cwpy.msgs["target_level_2"] % (levelmin, levelmax)

                w = dc.GetTextExtent(s)[0]
                dc.DrawText(s, (bmpw-w)/2, 15)

            self.yesbtn.Enable()

            # 進行中チェック
            if self.is_playing(header):
                bmp = cw.cwpy.rsrc.dialogs["PLAYING"]
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 152, True)
                if not cw.cwpy.debug:
                    self.yesbtn.Disable()
            # 済み印存在チェック
            elif self.is_complete(header):
                bmp = cw.cwpy.rsrc.dialogs["COMPLETE"]
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 175, True)
                if not cw.cwpy.debug:
                    self.yesbtn.Disable()
            # クーポン存在チェック
            elif self.is_invisible(header):
                bmp = cw.cwpy.rsrc.dialogs["INVISIBLE"]
                w = bmp.GetSize()[0]
                dc.DrawBitmap(bmp, (bmpw-w)/2, 100, True)
                if not cw.cwpy.debug:
                    self.yesbtn.Disable()

    def is_playing(self, header):
        return header.get_fpath() in self.nowplayingpaths

    def is_complete(self, header):
        return header.name in self.stamps

    def is_invisible(self, header):
        num = 0

        for coupon in header.coupons.splitlines():
            if coupon and coupon in self.coupons:
                num += 1

        return num < header.couponsnum

    def create_treeitems(self, treeitem):
        self.tree.DeleteChildren(treeitem)
        i, nowdir = self.tree.GetItemPyData(treeitem)
        itemlist = []
        dpaths = self.get_dpaths(nowdir)
        index = 0
        for dpath in dpaths:
            name = os.path.basename(dpath)
            image = self.tree.imgidx_dir
            if sys.platform == "win32" and name.lower().endswith(".lnk"):
                name = os.path.splitext(name)[0]
            item = self.tree.AppendItem(treeitem, name, image)
            self.tree.SetItemPyData(item, (index, dpath))
            child = self.tree.AppendItem(item, u"読込中...")
            self.tree.SetItemPyData(child, None)
            self.tree.Collapse(item)
            itemlist.append(item)
            index += 1

        for header in self.db.search_dpath(nowdir):
            name = header.name
            image = self.tree.imgidx_summary
            if self.is_playing(header):
                image = self.tree.imgidx_playing
            elif self.is_complete(header):
                image = self.tree.imgidx_complete
            elif self.is_invisible(header):
                image = self.tree.imgidx_invisible
            item = self.tree.AppendItem(treeitem, name, image)
            self.tree.SetItemPyData(item, (index, header))
            itemlist.append(item)
            index += 1

        if not treeitem is self.tree.root:
            self.tree.Expand(treeitem)

        return itemlist, dpaths

    def show_tree(self):
        # ツリーを初期化する
        self.tree.DeleteChildren(self.tree.root)

        nowdir = self.scedir
        treeitem = self.tree.root
        itemlist = []
        dirstack = self.dirstack[:]
        while True:
            itemlist, dpaths = self.create_treeitems(treeitem)

            if dirstack:
                pardir, selname = dirstack.pop(0)
                index = -1
                for i, dpath in enumerate(dpaths):
                    if os.path.normcase(selname) == os.path.normcase(os.path.basename(dpath)):
                        index = i
                        break
                if index == -1:
                    break
                nowdir = cw.util.join_paths(pardir, selname)
                treeitem = itemlist[index]
                self.tree.DeleteChildren(treeitem)
            else:
                self.tree.SelectItem(itemlist[self.index])
                break

    def OnTreeItemExpanded(self, event):
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        selitem = event.GetItem()
        item, cookie = self.tree.GetFirstChild(selitem)
        data = self.tree.GetItemPyData(item)
        if not data is None:
            # 読込済み
            return

        if self.updatenames_thr:
            self.updatenames_thr.quit = True
            self.updatenames_thr = None
        self.names = [u"読込中..."]
        index, dpath = self.tree.GetItemPyData(selitem)
        paritem = self.tree.GetItemParent(selitem)
        dirstack = self.get_dirstack(paritem)
        self.updatenames_thr = UpdateNamesThread(self, dpath, dirstack)
        self.updatenames_thr.start()

    def OnTreeItemCollapsed(self, event):
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        # 一旦リストをクリアして次に開いた時に再読込を行う
        item = event.GetItem()
        self.tree.DeleteChildren(item)
        child = self.tree.AppendItem(item, u"読込中...")
        self.tree.SetItemPyData(child, None)
        self.tree.Collapse(item)

    def OnTreeSelChanged(self, event):
        if not (self.tree.IsShown() and self.tree.IsShownOnScreen()):
            return
        selitem = self.tree.GetSelection()
        paritem = self.tree.GetItemParent(selitem)

        if self.tree.GetItemPyData(selitem) is None:
            # "読込中..."なので一つ上の階層を選択
            selitem = paritem
            paritem = self.tree.GetItemParent(selitem)

        index, self.nowdir = self.tree.GetItemPyData(paritem)
        self.index, pathorheader = self.tree.GetItemPyData(selitem)

        dpaths = self.get_dpaths(self.nowdir)
        headers = self.db.search_dpath(self.nowdir)
        self.list = dpaths + headers

        self.dirstack = self.get_dirstack(paritem)

        self.enable_btn()

    def get_dirstack(self, paritem):
        dirstack = []
        while paritem:
            i, parpath = self.tree.GetItemPyData(paritem)
            i, selpath = self.tree.GetItemPyData(paritem)
            parpath = os.path.dirname(parpath)
            selpath = os.path.basename(selpath)
            dirstack.insert(0, (parpath, selpath))

            selitem = paritem
            paritem = self.tree.GetItemParent(paritem)
        return dirstack[1:]

    def select_treeitem(self, index):
        item = self.tree.GetSelection()
        item = self.tree.GetItemParent(item)
        item, cookie = self.tree.GetFirstChild(item)
        i = 0
        while item.IsOk():
            if i == index:
                self.tree.SelectItem(item)
                self.index = index
                break
            item, cookie = self.tree.GetNextChild(item, cookie)
            i += 1

    def updated_names(self, dpath, dirstack):
        if not self.tree.IsShown():
            self.Refresh()
            return

        if not self.tree.IsShownOnScreen():
            return

        # dpathからツリーアイテムを検索
        parent = self.tree.root
        item = None
        dirstack.append(("", dpath))
        while dirstack:
            item, cookie = self.tree.GetFirstChild(parent)
            if not item.IsOk():
                break

            parent = None
            while item.IsOk():
                i, data = self.tree.GetItemPyData(item)
                if not data:
                    break
                if not isinstance(data, cw.header.ScenarioHeader):
                    name = os.path.normcase(os.path.basename(data))
                    if name == os.path.normcase(os.path.basename(dirstack[0][1])):
                        parent = item
                        dirstack.pop(0)
                        break
                item, cookie = self.tree.GetNextChild(item, cookie)

            if not parent:
                break

        if item and item.IsOk():
            # ディレクトリの内容を表示
            self.create_treeitems(item)

    def enable_btn(self):
        # リストが空だったらボタンを無効化
        if not self.list:
            self._disable_btn()
            ##self.convbtn.Enable()
            self.nobtn.Enable()
        elif len(self.list) == 1:
            self._enable_btn()
            self.rightbtn.Disable()
            self.right2btn.Disable()
            self.leftbtn.Disable()
            self.left2btn.Disable()
        else:
            self._enable_btn()

        # ツリー表示中かつディレクトリ選択中なら決定ボタン無効化
        if self.list and self.tree.IsShown() and\
                not isinstance(self.list[self.index], cw.header.ScenarioHeader):
            self.yesbtn.Disable()

        # 状況によってボタンのテキストを更新
        if self.tree.IsShown():
            self.viewbtn.SetLabel(cw.cwpy.msgs["scenario_one"])
        else:
            self.viewbtn.SetLabel(cw.cwpy.msgs["scenario_tree"])

        if not self.list or isinstance(self.list[self.index], cw.header.ScenarioHeader) or self.tree.IsShown():
            self.yesbtn.SetLabel(cw.cwpy.msgs["decide"])
        else:
            self.yesbtn.SetLabel(cw.cwpy.msgs["see"])

        if self.dirstack and not self.tree.IsShown():
            self.nobtn.SetLabel(cw.cwpy.msgs["return"])
        else:
            self.nobtn.SetLabel(cw.cwpy.msgs["entry_cancel"])

    def get_dpaths(self, dpath):
        """
        クラシックなシナリオ以外のフォルダの一覧を返す。
        (ショートカット類も含む)
        """
        seq = []

        dir = cw.util.get_linktarget(dpath)
        for dname in os.listdir(dir):
            path = cw.util.join_paths(dir, dname)
            if self.is_listitem(path) and not self.is_scenario(path):
                seq.append(path)

        return seq

    def is_listitem(self, path):
        """
        指定されたパスが選択可能ならTrueを返す。
        """
        return os.path.isdir(path) or\
            (sys.platform == "win32" and path.lower().endswith(".lnk")) or\
            self.is_scenario(path)

    def is_scenario(self, path):
        """
        指定されたパスがシナリオならTrueを返す。
        """
        if os.path.isdir(path):
            spath = cw.util.join_paths(path, "Summary.wsm")
            return os.path.exists(spath)
        else:
            lpath = path.lower()
            return lpath.endswith(".wsn") or lpath.endswith(".zip") or lpath.endswith(".cab")

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
                if path.lower().endswith(".cab"):
                    dpath = "Data/Temp/Cab"
                    if not os.path.isdir(dpath):
                        os.makedirs(dpath)
                    s = "expand %s -f:%s %s" % (path, "*.txt", dpath)
                    try:
                        encoding = sys.getfilesystemencoding()
                        if subprocess.call(s.encode(encoding), shell=True) == 0:
                            for dpath2, dnames, fnames in os.walk(dpath):
                                for fname in fnames:
                                    if fname.lower().endswith(".txt"):
                                        dpath2 = cw.util.decode_zipname(dpath2)
                                        f = open(cw.util.join_paths(dpath2, fname), "r")
                                        seq2.append(f.read())
                                        f.close()
                                        seq.append(fname)
                    finally:
                        for file in os.listdir(dpath):
                            file = cw.util.decode_zipname(file)
                            file = cw.util.join_paths(dpath, file)
                            if os.path.isdir(file):
                                shutil.rmtree(file)
                            else:
                                os.remove(file)

                else:
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
                paths = []
                for dpath, dnames, fnames in os.walk(path):
                    for fname in fnames:
                        if fname.lower().endswith(".txt"):
                            paths.append(cw.util.join_paths(dpath, fname))

                for fpath in paths:
                    f = open(fpath, "r")
                    data = f.read()
                    f.close()
                    seq2.append(data)
                    name = os.path.relpath(fpath, path)
                    name = cw.util.join_paths(name)
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
        cw.cwpy.sounds["click"].play()
        s = os.path.basename(path) + u"　を変換します。\nよろしいですか？"
        dlg = message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
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
        cw.cwpy.sounds["harvest"].play()
        # 変換完了ダイアログ
        s = u"データの変換が完了しました。"
        dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
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
        header = None
        for index, lheader in enumerate(self.list):
            if not hasattr(lheader, "fname"):
                continue

            if os.path.basename(zpath) == lheader.fname:
                self.index = index
                header = lheader
                break

        # ツリー表示中の場合は追加
        if self.tree.IsShown() and header:
            name = header.name
            image = self.tree.imgidx_summary
            if self.is_playing(header):
                image = self.tree.imgidx_playing
            elif self.is_complete(header):
                image = self.tree.imgidx_complete
            elif self.is_invisible(header):
                image = self.tree.imgidx_invisible
            parent = self.tree.GetSelection()
            prev = None
            i = 0
            item, cookie = self.tree.GetFirstItem(parent)
            while item.IsOk():
                if i == self.index:
                    prev = item
                    break
                item, cookie = self.tree.GetNextItem(item, cookie)
                i += 1
            if prev:
                item = self.tree.InsertItem(parent, prev, name, image)
            else:
                item = self.tree.AppendItem(parent, name, image)
            self.tree.SelectItem(item)
            self.tree.SetItemPyData(item, (self.index, header))

        cw.cwpy.sounds["page"].play()
        self.draw(True)
        self.enable_btn()

class UpdateNamesThread(threading.Thread):

    def __init__(self, dlg, dpath, dirstack):
        threading.Thread.__init__(self)
        self.dlg = dlg
        self.dpath = dpath
        self.dirstack = dirstack
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
        # dpathの中にあるディレクトリ名のリスト
        dnames = []

        if self.quit: return
        for path in self.dpaths:
            if path.lower().endswith(".lnk"):
                path = path[0:-len(".lnk")]
            dname = "[%s]" % os.path.basename(path)
            dnames.append(dname)
        self.dlg.names = dnames + headers
        if self.quit: return
        wx.CallAfter(self.dlg.updated_names, self.dpath, self.dirstack)
        self.dlg.updatenames_thr = None

def main():
    pass

if __name__ == "__main__":
    main()
