#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import itertools
import threading
import shutil

import wx

import cw


class TransferYadoDataDialog(wx.Dialog):
    """
    宿のデータの転送を行う。
    """
    def __init__(self, parent, yadodirs, yadonames, selected):
        wx.Dialog.__init__(self, parent, -1, cw.cwpy.msgs["transfer_title"],
                           style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.RESIZE_BORDER)
        self.cwpy_debug = False

        self.yadodirs = yadodirs
        self.yadonames = yadonames
        if selected in yadodirs:
            index2 = yadodirs.index(selected)
        else:
            index2 = 0
        self.index = 1 if index2 == 0 else 0

        # 転送元
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(16))
        self.fromyado = wx.Choice(self, -1, choices=yadonames)
        self.fromyado.SetSelection(self.index)
        self.fromyado.SetFont(font)
        # 転送先
        self.toyado = wx.Choice(self, -1, choices=yadonames)
        self.toyado.SetSelection(index2)
        self.toyado.SetFont(font)

        # 転送可能なデータリスト
        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.datalist = cw.util.CheckableListCtrl(self, -1, size=cw.wins((300, 300)),
                                                  style=wx.MULTIPLE|wx.VSCROLL|wx.HSCROLL,
                                                  colpos=1, system=False)
        self.datalist.SetFont(font)
        self.imglist = self.datalist.imglist
        assert self.imglist.ImageCount == 2
        self.imgidx_bookmark = self.imglist.Add(cw.cwpy.rsrc.dialogs["BOOKMARK"])
        self.imgidx_party = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["MEMBER"]))
        self.imgidx_standby = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_CAST"]))
        self.imgidx_skill = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_SKILL"]))
        self.imgidx_item = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_ITEM"]))
        self.imgidx_beast = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_BEAST"]))
        self.imgidx_gossip = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_GOSSIP"]))
        self.imgidx_completestamp = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["EVT_GET_COMPLETESTAMP"]))
        self.imgidx_money = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["MONEY"]))
        self.imgidx_album = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["CARD"]))
        self.imgidx_partyrecord = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["SELECTION"]))
        self.imgidx_savedjpdcimage = self.imglist.Add(cw.wins(cw.cwpy.rsrc.debugs_noscale["JPDCIMAGE"]))
        self.datalist.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)

        def func(index, flag):
            self.datalist.DefaultOnCheckItem(index, flag)
            self._enable_btn()
        self.datalist.OnCheckItem = func

        self.datalist.InsertImageStringItem(0, u"", 0)
        rect = self.datalist.GetItemRect(0, wx.LIST_RECT_LABEL)
        self.datalist.SetColumnWidth(0, rect.x)
        self.datalist.DeleteAllItems()

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL,
                                                        cw.wins((100, 30)), cw.cwpy.msgs["entry_cancel"])
        self._do_layout()
        self._bind()

        self._update_list()

    def _update_list(self):
        # 選択中の転送元にある転送可能なデータの一覧を表示
        i = 0
        self.data = []
        self.datalist.DeleteAllItems()

        yadodir = self.yadodirs[self.index]
        data = cw.data.xml2etree(cw.util.join_paths(yadodir, u"Environment.xml"))
        bookmark = data.find("Bookmarks")
        if not bookmark is None:
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["bookmark"])
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_bookmark)
            self.datalist.CheckItem(i, False)
            self.data.append(bookmark)
            i += 1

        cashbox = data.getint("Property/Cashbox", 0)
        if cashbox:
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["currency"] % (cashbox))
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_money)
            self.datalist.CheckItem(i, False)
            self.data.append(cashbox)
            i += 1

        gossips = data.find("Gossips")
        if not gossips is None and len(gossips):
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["gossip"])
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_gossip)
            self.datalist.CheckItem(i, False)
            self.data.append(gossips)
            i += 1

        completestamp = data.find("CompleteStamps")
        if not completestamp is None and len(completestamp):
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["complete_stamp"])
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_completestamp)
            self.datalist.CheckItem(i, False)
            self.data.append(completestamp)
            i += 1

        yadodb = cw.yadodb.YadoDB(yadodir)
        parties = yadodb.get_parties()
        standbys = yadodb.get_standbys()
        album = yadodb.get_album()
        cards = yadodb.get_cards()
        partyrecord = yadodb.get_partyrecord()
        savedjpdcimage = yadodb.get_savedjpdcimage()
        yadodb.close()

        partymembers = set()

        if album:
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["album"])
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_album)
            self.datalist.CheckItem(i, False)
            self.data.append(album)
            i += 1

        if partyrecord:
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["select_party_record"])
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_partyrecord)
            self.datalist.CheckItem(i, False)
            self.data.append(partyrecord)
            i += 1

        keys = savedjpdcimage.keys()
        for key in cw.util.sorted_by_attr(keys):
            header = savedjpdcimage[key]
            self.datalist.InsertStringItem(i, u"")
            if header.scenarioauthor:
                s = u"JPDC - %s(%s)" % (header.scenarioname, header.scenarioauthor)
            else:
                s = u"JPDC - %s" % (header.scenarioname)
            self.datalist.SetStringItem(i, 1, s)
            self.datalist.SetItemColumnImage(i, 1, self.imgidx_savedjpdcimage)
            self.datalist.CheckItem(i, False)
            self.data.append(header)
            i += 1

        for header in itertools.chain(parties, standbys, cards):
            if isinstance(header, cw.header.PartyHeader):
                image = self.imgidx_party
                for member in header.members:
                    partymembers.add(member)
            elif isinstance(header, cw.header.AdventurerHeader):
                if os.path.splitext(os.path.basename(header.fpath))[0] in partymembers:
                    continue
                image = self.imgidx_standby
            elif isinstance(header, cw.header.CardHeader):
                if header.type == "SkillCard":
                    image = self.imgidx_skill
                elif header.type == "ItemCard":
                    image = self.imgidx_item
                elif header.type == "BeastCard":
                    image = self.imgidx_beast
                else:
                    assert False
            else:
                assert False
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, header.name)
            self.datalist.SetItemColumnImage(i, 1, image)
            self.datalist.CheckItem(i, False)
            self.data.append(header)
            i += 1

        if not self.data:
            self.datalist.InsertStringItem(i, u"")
            self.datalist.SetStringItem(i, 1, cw.cwpy.msgs["transfer_no_item"])

        self._enable_btn()

    def _enable_btn(self):
        btn = self.fromyado.GetSelection() <> self.toyado.GetSelection()
        if btn:
            btn = False
            for index in xrange(self.datalist.GetItemCount()):
                if self.datalist.IsChecked(index):
                    btn = True
                    break
        self.okbtn.Enable(btn)
        self.datalist.Enable(bool(self.data))

    def OnFromYado(self, event):
        cw.cwpy.play_sound("page")
        index = self.fromyado.GetSelection()
        if index == self.index:
            return
        self.index = index
        self._update_list()

    def OnToYado(self, event):
        self._enable_btn()

    def OnOk(self, event):
        # 転送を実行する
        index1 = self.fromyado.GetSelection()
        index2 = self.toyado.GetSelection()
        if index1 == index2:
            return
        cw.cwpy.play_sound("signal")
        name1 = self.yadonames[index1]
        name2 = self.yadonames[index2]
        seq = []
        for i in xrange(self.datalist.GetItemCount()):
            if self.datalist.IsChecked(i):
                seq.append(self.data[i])
        s = cw.cwpy.msgs["confirm_transfer"] % (name1, len(seq), name2)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        result = dlg.ShowModal()
        dlg.Destroy()
        if result <> wx.ID_OK:
            return

        fromyado = self.yadodirs[index1]
        toyado = self.yadodirs[index2]

        # 進捗状態を進めるアイテムの数
        counter = 0
        for data in seq:
            if isinstance(data, cw.data.CWPyElement) and\
                    data.tag in ("Bookmarks", "Gossips", "CompleteStamps"):
                # ブックマーク・ゴシップ・終了印
                counter += 1
            elif isinstance(data, int):
                # 資金
                counter += 1
            elif isinstance(data, list):
                # アルバム・編成記録
                counter += len(data)
            elif isinstance(data, cw.header.PartyHeader):
                # パーティデータ・メンバ・荷物袋のカード
                counter += 1 # 全体情報
                counter += 1 # 冒険中情報
                counter += len(data.members)
                for cardtype in (u"SkillCard", u"ItemCard", u"BeastCard"):
                    dpath = cw.util.join_paths(os.path.dirname(data.fpath), cardtype)
                    if os.path.isdir(dpath):
                        counter += len(os.listdir(dpath))
            elif isinstance(data, cw.header.AdventurerHeader):
                # プレイヤーカード
                counter += 1
            elif isinstance(data, cw.header.CardHeader):
                # 手札
                counter += 1
            elif isinstance(data, cw.header.SavedJPDCImageHeader):
                # 保存されたJPDCイメージ
                counter += 1
            else:
                assert False

        class TransferThread(threading.Thread):
            def __init__(self, outer):
                threading.Thread.__init__(self)
                self.outer = outer

                def _skindir_to_scedir(skindir):
                    scedir = u"Scenario"
                    if skindir:
                        skindir = cw.util.join_paths(u"Data/Skin", skindir)
                        fpath = cw.util.join_paths(skindir, u"Skin.xml")
                        if os.path.isfile(fpath):
                            prop = cw.header.GetProperty(fpath)
                            skintype = prop.properties.get("Type", "")
                            if skintype:
                                for type, folder in cw.cwpy.setting.folderoftype:
                                    if type == skintype:
                                        scedir = folder
                                        break
                    return scedir

                prop = cw.header.GetProperty(cw.util.join_paths(fromyado, u"Environment.xml"))
                skindir = prop.properties.get("Skin", "")
                self.fromscedir = _skindir_to_scedir(skindir)
                self.environment = cw.data.xml2etree(cw.util.join_paths(toyado, u"Environment.xml"))
                self.toscedir = _skindir_to_scedir(self.environment.gettext("Property/Skin", u""))
                self.imgpaths = {}
                self.membertable = {}
                self.num = 0
                self.msg = u""

            def run(self):
                seq2 = []
                yadodb = cw.yadodb.YadoDB(toyado)
                savedjpdcimage = yadodb.get_savedjpdcimage()
                try:
                    for data in seq:
                        if isinstance(data, cw.data.CWPyElement):
                            if data.tag == "Bookmarks":
                                name = cw.cwpy.msgs["bookmark"]
                            elif data.tag == "Gossips":
                                name = cw.cwpy.msgs["gossip"]
                            elif data.tag == "CompleteStamps":
                                name = cw.cwpy.msgs["complete_stamp"]
                            else:
                                assert False
                        elif isinstance(data, int):
                            name = cw.cwpy.msgs["currency"] % (data)
                        elif isinstance(data, list):
                            if isinstance(data[0], cw.header.AdventurerHeader) and data[0].album:
                                name = cw.cwpy.msgs["album"] % (data)
                            elif isinstance(data[0], cw.header.PartyRecordHeader):
                                seq2.append(data) # 編成記録はAdventurerHeaderよりも遅延させる
                                continue
                            else:
                                assert False
                        elif isinstance(data, cw.header.SavedJPDCImageHeader):
                            # 保存されたJPDCイメージ
                            if data.scenarioauthor:
                                name = u"JPDC - %s(%s)" % (data.scenarioname, data.scenarioauthor)
                            else:
                                name = u"JPDC - %s" % (data.scenarioname)
                        else:
                            name = data.name
                        self.msg = cw.cwpy.msgs["transfer_processing"] % (name)

                        if isinstance(data, cw.data.CWPyElement):
                            if data.tag == "Bookmarks":
                                # ブックマーク
                                self.outer.transfer_bookmark(self.fromscedir, self.toscedir, fromyado, toyado, data, self)
                            elif data.tag == "Gossips":
                                # ゴシップ
                                self.outer.transfer_gossip(fromyado, toyado, data, self)
                            elif data.tag == "CompleteStamps":
                                # 終了印
                                self.outer.transfer_completestamp(fromyado, toyado, data, self)
                        elif isinstance(data, int):
                            # 資金
                            money = self.environment.getint("Property/Cashbox", 0) + data
                            money = cw.util.numwrap(money, 0, 9999999)
                            self.environment.edit("Property/Cashbox", str(money))
                            self.num += 1
                        elif isinstance(data, list):
                            # アルバム
                            self.outer.transfer_album(fromyado, toyado, data, yadodb, self)
                        elif isinstance(data, cw.header.PartyHeader):
                            # パーティ
                            self.outer.transfer_party(fromyado, toyado, data, yadodb, self)
                        elif isinstance(data, cw.header.AdventurerHeader):
                            # プレイヤーカード
                            self.outer.transfer_adventurer(fromyado, toyado, data, yadodb, self)
                        elif isinstance(data, cw.header.CardHeader):
                            # 手札
                            self.outer.transfer_card(fromyado, toyado, data, yadodb, self)
                        elif isinstance(data, cw.header.SavedJPDCImageHeader):
                            # 保存されたJPDCイメージ
                            self.outer.transfer_savedjpdcimage(fromyado, toyado, data, yadodb, savedjpdcimage, self)
                        else:
                            assert False

                    for data in seq2:
                        if isinstance(data, list):
                            if isinstance(data[0], cw.header.PartyRecordHeader):
                                # 編成記録
                                name = cw.cwpy.msgs["select_party_record"]
                                self.msg = cw.cwpy.msgs["transfer_processing"] % (name)
                                self.outer.transfer_partyrecord(fromyado, toyado, data, yadodb, self)
                            else:
                                assert False
                        else:
                            assert False

                    yadodb.commit()

                    if self.environment.is_edited:
                        self.environment.write()
                finally:
                    yadodb.close()

        thread = TransferThread(self)
        thread.start()

        # プログレスダイアログ表示
        dlg = cw.dialog.progress.ProgressDialog(self, cw.cwpy.msgs["transfer_data"],
                                                "", maximum=counter)
        def progress():
            while thread.is_alive():
                wx.CallAfter(dlg.Update, thread.num, thread.msg)
                time.sleep(0.001)
            wx.CallAfter(dlg.Destroy)
        thread2 = threading.Thread(target=progress)
        thread2.start()
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()

        cw.cwpy.play_sound("harvest")
        s = cw.cwpy.msgs["transfer_success"]
        dlg = cw.dialog.message.Message(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        result = dlg.ShowModal()
        dlg.Destroy()

        self.EndModal(wx.ID_OK)

    def transfer_bookmark(self, fromscedir, toscedir, fromyado, toyado, be, counter):
        # ブックマークを転送する
        # ただし転送先にすでに存在するアイテムは転送しない
        targetbookmarks = set()
        data = counter.environment
        bookmark = data.find("Bookmarks")
        if bookmark is None:
            bookmark = cw.data.make_element("Bookmarks", u"")
            data.getroot().append(bookmark)
        else:
            for e in bookmark:
                paths = []
                for pe in e:
                    paths.append(pe.text)
                path = e.get("path", None)
                if path is None:
                    # 0.12.2以前はフルパスがない
                    path = cw.data.find_scefullpath(toscedir, paths)
                    e.set("path", path)
                if path:
                    path = os.path.abspath(path)
                    path = os.path.normpath(path)
                    path = os.path.normcase(path)
                paths = "/".join(paths)
                targetbookmarks.add((paths, path))

        for e in be:
            paths = []
            for pe in e:
                paths.append(pe.text)
            path = e.get("path", None)
            if path is None:
                # 0.12.2以前はフルパスがない
                path = cw.data.find_scefullpath(fromscedir, paths)
                e.set("path", path)
            if path:
                path = os.path.abspath(path)
                path = os.path.normpath(path)
                path = os.path.normcase(path)
            paths = "/".join(paths)
            if not (paths, path) in targetbookmarks:
                bookmark.append(e)
                targetbookmarks.add((paths, path))

        data.is_edited = True
        counter.num += 1

    def transfer_gossip(self, fromyado, toyado, ge, counter):
        # ゴシップを転送する
        # ただし転送先にすでに存在するアイテムは転送しない
        self.transfer_elementlist(fromyado, toyado, ge, counter, "Gossips")

    def transfer_completestamp(self, fromyado, toyado, ce, counter):
        # 終了印を転送する
        # ただし転送先にすでに存在するアイテムは転送しない
        self.transfer_elementlist(fromyado, toyado, ce, counter, "CompleteStamps")

    def transfer_elementlist(self, fromyado, toyado, ee, counter, tag):
        exists = set()
        edata = counter.environment.find(tag)
        for e in edata:
            exists.add(e.text)

        for e in ee:
            if not e.text in exists:
                edata.append(e)
                exists.add(e.text)

        counter.environment.is_edited = True
        counter.num += 1

    def transfer_party(self, fromyado, toyado, header, yadodb, counter):
        # パーティを転送する
        pdata = cw.data.xml2etree(header.fpath)
        for i, fpath in enumerate(header.get_memberpaths(fromyado)):
            # パーティメンバーの転送
            data = cw.data.xml2etree(fpath)
            name1 = os.path.splitext(os.path.basename(fpath))[0]
            fpath = self.transfer_adventurer(fromyado, toyado, data, yadodb, counter=counter)
            name = os.path.splitext(os.path.basename(fpath))[0]
            pdata.find("Property/Members/Member[%s]" % (i+1)).text = name
            counter.membertable[name1] = name

        # パーティデータの転送
        dpath = os.path.dirname(header.fpath)
        dstdir = dpath.replace(fromyado + "/", toyado + "/", 1)
        dstdir = cw.util.dupcheck_plus(dstdir, yado=False)
        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        pdata.fpath = cw.util.join_paths(dstdir, u"Party.xml")
        pdata.write()
        counter.num += 1

        # 荷物袋の転送
        carddb = cw.yadodb.YadoDB(dpath, cw.yadodb.PARTY)
        cards = carddb.get_cards()
        carddb.close()

        carddb = cw.yadodb.YadoDB(dstdir, cw.yadodb.PARTY)
        for i, cardheader in enumerate(cards):
            fpath = cardheader.fpath
            cardtype = cardheader.type
            basename = os.path.basename(fpath)
            e = cw.data.xml2etree(fpath)
            e.fpath = u""
            self.transfer_card(fromyado, toyado, e, None, counter=counter)
            e.fpath = cw.util.join_paths(dstdir, cardtype, basename)
            e.fpath = cw.util.dupcheck_plus(e.fpath, yado=False)
            e.write()
            carddb.insert_card(e.fpath, commit=False, cardorder=i)
            counter.num += 1
        carddb.commit()
        carddb.close()

        wsl = os.path.splitext(header.fpath)[0] + ".wsl"
        if os.path.isfile(wsl):
            # 冒険中情報
            cw.util.decompress_zip(wsl, cw.tempdir, "ScenarioLog")

            fname = cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml")
            etree = cw.data.xml2etree(fname)
            e = etree.find("Property/MusicPath")
            if not e is None:
                if e.getbool(".", "inusecard", False):
                    e.text = counter.imgpaths.get(e.text, e.text)
            e = etree.find("Property/MusicPaths")
            if not e is None:
                for e2 in e:
                    if e2.getbool(".", "inusecard", False):
                        e2.text = counter.imgpaths.get(e2.text, e2.text)
            for e in etree.getfind("BgImages"):
                if e.getbool("ImagePath", "inusecard", False):
                    e = e.find("ImagePath")
                    e.text = counter.imgpaths.get(e.text, e.text)
            etree.write()

            fname = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face/Log.xml")
            if os.path.isfile(fname):
                etree = cw.data.xml2etree(fname)
                for e in etree.getfind("."):
                    member = e.get("member", "")
                    e.set("member", counter.membertable.get(member, member))
                    if e.tag == "ImagePath":
                        # 旧バージョン(～0.12.3)
                        e.text = counter.imgpaths.get(e.text, e.text)
                    elif e.tag == "ImagePaths":
                        # 新バージョン(複数イメージ対応後)
                        for e2 in e:
                            e2.text = counter.imgpaths.get(e2.text, e2.text)
                etree.write()

            dname = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party")
            etree = None
            for p in os.listdir(dname):
                if p.lower().endswith(".xml"):
                    etree = cw.data.xml2etree(cw.util.join_paths(dname, p))
                    break
            for e in etree.getfind("Property/Members"):
                e.text = counter.membertable[e.text]
            etree.write()

            dname = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members")
            dname2 = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members2")
            if not os.path.isdir(dname2):
                os.makedirs(dname2)
            for p in os.listdir(dname):
                if not p.lower().endswith(".xml"):
                    continue
                e = cw.data.xml2etree(cw.util.join_paths(dname, p))
                p2 = counter.membertable[os.path.splitext(p)[0]] + ".xml"
                e.fpath = cw.util.join_paths(dname2, p2)
                self.transfer_adventurer(fromyado, toyado, e, None, counter=counter, overwrite=True)
            cw.util.remove(dname)
            shutil.move(dname2, dname)

            wsl = cw.util.join_paths(dstdir, u"Party.wsl")
            cw.util.compress_zip(cw.util.join_paths(cw.tempdir, u"ScenarioLog"), wsl, unicodefilename=True)
            cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
        counter.num += 1

        # 宿DBへ追加
        fpath = cw.util.join_paths(dstdir, os.path.basename(header.fpath))
        yadodb.insert_party(fpath)

    def transfer_album(self, fromyado, toyado, album, yadodb, counter):
        # アルバムの転送
        for header in album:
            data = cw.data.xml2etree(header.fpath)
            cname = data.gettext("Property/Name", "")
            dstdir = cw.util.join_paths(toyado, u"Material", u"Album", cname if cname else "noname")
            can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(data.find("Property"), dstdir, from_scenario=False, scedir="", yadodir=fromyado,
                                   toyado=toyado, adventurer=True, imgpaths=counter.imgpaths,
                                   can_loaded_scaledimage=can_loaded_scaledimage)
            data.fpath = data.fpath.replace(fromyado + "/", toyado + "/", 1)
            data.fpath = cw.util.dupcheck_plus(data.fpath, yado=False)
            data.write()
            if yadodb:
                yadodb.insert_adventurer(data.fpath, album=True, commit=False)
            counter.num += 1

    def transfer_adventurer(self, fromyado, toyado, data, yadodb, counter, overwrite=False):
        # 冒険者の転送
        if isinstance(data, cw.header.AdventurerHeader):
            data = cw.data.xml2etree(data.fpath)
        cname = data.gettext("Property/Name", "")
        dstdir = cw.util.join_paths(toyado, u"Material", u"Adventurer", cname if cname else "noname")
        dstdir = cw.util.dupcheck_plus(dstdir, yado=False)
        can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
        cw.cwpy.copy_materials(data.find("Property"), dstdir, from_scenario=False, scedir="", yadodir=fromyado,
                               toyado=toyado, adventurer=True, imgpaths=counter.imgpaths,
                               can_loaded_scaledimage=can_loaded_scaledimage)
        if not overwrite:
            data.fpath = data.fpath.replace(fromyado + "/", toyado + "/", 1)
            data.fpath = cw.util.dupcheck_plus(data.fpath, yado=False)

        for e in itertools.chain(data.getfind("SkillCards"),
                                 data.getfind("ItemCards"),
                                 data.getfind("BeastCards")):
            e.fpath = u""
            self.transfer_card(fromyado, toyado, cw.data.xml2etree(element=e), yadodb=None, counter=counter)

        data.write()
        if yadodb:
            yadodb.insert_adventurer(data.fpath, album=False, commit=False)
        if not overwrite:
            counter.num += 1
        return data.fpath

    def transfer_card(self, fromyado, toyado, data, yadodb, counter):
        # 個別のカードの転送
        if isinstance(data, cw.header.CardHeader):
            data = cw.data.xml2etree(data.fpath)
        e = data.find("Property/Materials")
        if e is None:
            cname = data.gettext("Property/Name", "")
            dstdir = cw.util.join_paths(toyado, u"Material", data.getroot().tag, data.gettext("Property/Name", cname if cname else "noname"))
        else:
            dstdir = cw.util.join_paths(toyado, e.text if e.text else "noname")
        dstdir = cw.util.dupcheck_plus(dstdir, yado=False)
        if not data.getbool(".", "scenariocard", False):
            can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(data, dstdir, from_scenario=False, scedir="", yadodir=fromyado, toyado=toyado,
                                   imgpaths=counter.imgpaths, can_loaded_scaledimage=can_loaded_scaledimage)
        if data.fpath:
            data.fpath = data.fpath.replace(fromyado + "/", toyado + "/", 1)
            data.fpath = cw.util.dupcheck_plus(data.fpath, yado=False)
            data.write()
        if yadodb:
            yadodb.insert_card(data.fpath, commit=False)
            counter.num += 1

    def transfer_partyrecord(self, fromyado, toyado, partyrecord, yadodb, counter):
        # 編成記録の転送
        for header in partyrecord:
            data = cw.data.xml2etree(header.fpath)

            for e in data.find("Property/Members"):
                e.text = counter.membertable.get(e.text, e.text)

            data.fpath = data.fpath.replace(fromyado + "/", toyado + "/", 1)
            data.fpath = cw.util.dupcheck_plus(data.fpath, yado=False)
            data.write()
            if yadodb:
                yadodb.insert_partyrecord(data.fpath, commit=False)
            counter.num += 1

    def transfer_savedjpdcimage(self, fromyado, toyado, header, yadodb, table, counter):
        # 保存されたJPDCイメージの転送
        key = (header.scenarioname, header.scenarioauthor)
        savejpdcdir = cw.util.join_paths(toyado, u"SavedJPDCImage")

        fromdir = cw.util.join_paths(fromyado, u"SavedJPDCImage", header.dpath)
        todir = cw.util.join_paths(savejpdcdir, header.dpath)
        todir = cw.util.dupcheck_plus(todir, yado=False)

        dpath = os.path.dirname(todir)
        if not os.path.isdir(dpath):
            os.makedirs(dpath)
        shutil.copytree(fromdir, todir)

        toheader = table.get(key, None)
        if toheader:
            dpath = cw.util.join_paths(toyado, u"SavedJPDCImage", toheader.dpath)
            cw.util.remove(dpath)
            if yadodb:
                fpath = cw.util.join_paths(u"SavedJPDCImage", toheader.dpath, u"SavedJPDCImage.xml")
                yadodb.delete_savedjpdcimage(fpath, commit=False)

        header.dpath = cw.util.relpath(todir, savejpdcdir)
        header.fpath = cw.util.join_paths(todir, u"SavedJPDCImage.xml")

        data = cw.data.xml2etree(cw.util.join_paths(fromdir, u"SavedJPDCImage.xml"))
        data.edit("Materials", header.dpath, "dpath")
        data.fpath = cw.util.join_paths(todir, u"SavedJPDCImage.xml")
        data.write()

        if yadodb:
            yadodb.insert_savedjpdcimageheader(header, commit=False)

        counter.num += 1

    def OnCancel(self, event):
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)

        font = cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(16))
        dc.SetFont(font)

        # 転送元
        s = cw.cwpy.msgs["transfer_from_base"]
        _tw, th = dc.GetTextExtent(s)
        _x, y, _w, h = self.fromyado.GetRect()
        x = cw.wins(5)
        y += (h-th) / 2
        dc.DrawText(s, x, y)

        # 転送先
        s = cw.cwpy.msgs["transfer_to_base"]
        _tw, th = dc.GetTextExtent(s)
        x, y, _w, h = self.toyado.GetRect()
        x = cw.wins(5)
        y += (h-th) / 2
        dc.DrawText(s, x, y)

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.fromyado.Bind(wx.EVT_CHOICE, self.OnFromYado)
        self.toyado.Bind(wx.EVT_CHOICE, self.OnToYado)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h2 = wx.BoxSizer(wx.HORIZONTAL)

        dc = wx.ClientDC(self)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg2", pixelsize=cw.wins(16))
        dc.SetFont(font)
        w = dc.GetMultiLineTextExtent(cw.cwpy.msgs["transfer_from_base"])[0]
        w = max(w, dc.GetMultiLineTextExtent(cw.cwpy.msgs["transfer_to_base"])[0])
        w += cw.wins(3)

        sizer_h1.Add((w, cw.wins(0)), 0, wx.RIGHT, cw.wins(3))
        sizer_h1.Add(self.fromyado, 0, 0, 0)
        sizer_h2.Add((w, cw.wins(0)), 0, wx.RIGHT, cw.wins(3))
        sizer_h2.Add(self.toyado, 0, 0, 0)

        sizer_2.Add(sizer_h1, 0, wx.EXPAND|wx.BOTTOM, cw.wins(5))
        sizer_2.Add(sizer_h2, 0, wx.EXPAND|wx.BOTTOM, cw.wins(5))

        sizer_2.Add(self.datalist, 1, wx.EXPAND, cw.wins(5))

        sizer_1.Add(sizer_2, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, cw.wins(5))

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_2.Add(self.okbtn, 0, wx.LEFT|wx.RIGHT, cw.wins(5))
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT|wx.RIGHT, cw.wins(5))
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, cw.wins(10))

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

def main():
    pass

if __name__ == "__main__":
    main()
