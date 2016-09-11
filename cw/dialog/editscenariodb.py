#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import wx

import cw


#-------------------------------------------------------------------------------
#  シナリオDB構築ダイアログ
#-------------------------------------------------------------------------------

class ConstructScenarioDB(wx.Dialog):

    def __init__(self, parent, dpaths):
        """シナリオ検索の始点から見つかる全てのシナリオを
        シナリオDBに登録する。
        """
        wx.Dialog.__init__(self, parent, -1, u"シナリオデータベースの構築",
                style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX)
        self.cwpy_debug = True
        self.dpaths = dpaths
        self._message = u"フォルダの一覧を作成しています..."
        self._curnum = 0
        self._complete = False
        self._cancel = False
        self._clear = False

        self.text = wx.StaticText(self, -1, u"シナリオフォルダを起点として発見できる全てのシナリオを\nシナリオデータベースに登録します。\nデータベースに登録されたシナリオはシナリオ選択ダイアログで\n高速に表示できる他、検索で発見できるようになります。\nシナリオデータベースの構築を開始しますか？")

        self.clear = wx.CheckBox(self, -1, u"構築前にデータベースを初期化する")

        # btn
        self.okbtn = wx.Button(self, -1, u"構築開始...")
        self.cnclbtn = wx.Button(self, wx.ID_CANCEL, u"キャンセル")

        self._do_layout()
        self._bind()

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnClickOkBtn, self.okbtn)

    def _do_layout(self):
        sizer_top = wx.BoxSizer(wx.VERTICAL)
        sizer_top.Add(self.text, 0, wx.BOTTOM, cw.ppis(10))
        sizer_top.Add(self.clear, 0, wx.ALIGN_RIGHT, cw.ppis(0))

        sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_btn.Add(self.okbtn, 1, 0, cw.ppis(0))
        sizer_btn.Add(cw.ppis((10, 0)), 0, 0, cw.ppis(0))
        sizer_btn.Add(self.cnclbtn, 1, 0, cw.ppis(0))

        sizer_v1 = wx.BoxSizer(wx.VERTICAL)
        sizer_v1.Add(sizer_top, 0, 0, cw.ppis(0))
        sizer_v1.Add(sizer_btn, 0, wx.ALIGN_RIGHT|wx.TOP, cw.ppis(10))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_v1, 0, wx.ALL, cw.ppis(10))
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def construct_scenariodb(self):
        self._message = u"フォルダの一覧を作成しています..."
        self._curnum = 0

        while not cw.scenariodb.ScenariodbUpdatingThread.is_finished():
            pass

        d = {}
        count = 0
        for i, (skintype, dpaths) in enumerate(self.dpaths.iteritems()):
            if self._cancel:
                break
            self._message = u"フォルダの一覧を作成しています... (%s/%s)" % (i+1, len(self.dpaths))
            if skintype in d:
                s = d[skintype]
            else:
                s = set()
                d[skintype] = s
            for dpath in dpaths:
                if self._cancel:
                    break
                s2 = cw.scenariodb.find_alldirectories(dpath, lambda: self._cancel)
                count += len(s2)
                s.update(s2)
            self._curnum += 1

        db = cw.scenariodb.Scenariodb()
        if self._clear and not self._cancel:
            db.delete_all(commit=False)

        completed = 0
        for skintype, dpaths in d.iteritems():
            if self._cancel:
                break
            for dpath in dpaths:
                if self._cancel:
                    break
                self._message = u"シナリオを登録しています... (%s/%s)" % (completed+1, count)
                db.update(dpath=dpath, skintype=skintype, commit=False)
                completed += 1
                self._curnum = len(self.dpaths) + int((float(completed)/count)*100)

        if not self._cancel:
            db.commit()

            self._message = u"データベース内の空領域を再編成しています..."
            db.vacuum()

        db.close()
        self._curnum = 100+len(self.dpaths)+1
        self._complete = True

    def OnClickOkBtn(self, event):
        # プログレスダイアログ表示
        dlg = cw.dialog.progress.SysProgressDialog(self,
            u"シナリオデータベースの構築", u"",
            maximum=100+len(self.dpaths)+1,
            cancelable=True)
        cw.cwpy.frame.move_dlg(dlg)

        self._message = u"フォルダの一覧を作成しています..."
        self._curnum = 0
        self._complete = False
        self._cancel = False
        self._clear = self.clear.IsChecked()

        thread = threading.Thread(target=self.construct_scenariodb)
        thread.start()

        def progress():
            while not self._complete and not dlg.cancel:
                self._cancel = dlg.cancel
                wx.CallAfter(dlg.Update, self._curnum, self._message)
                time.sleep(0.001)
            self._cancel = dlg.cancel
            wx.CallAfter(dlg.Destroy)
        thread2 = threading.Thread(target=progress)
        thread2.start()
        dlg.ShowModal()

        thread.join()
        thread2.join()

        if not self._cancel:
            s = u"データベースの構築が完了しました。"
            wx.MessageBox(s, u"メッセージ", wx.OK|wx.ICON_INFORMATION, self)
            self.Destroy()
