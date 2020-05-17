#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
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
                           style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.MINIMIZE_BOX)
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
                                                  style=wx.LC_REPORT | wx.VSCROLL | wx.HSCROLL,
                                                  colpos=0, system=False)
        self.datalist.SetFont(font)
        self.imglist = wx.ImageList(cw.wins(16), cw.wins(16))
        self.datalist.SetImageList(self.imglist, wx.IMAGE_LIST_SMALL)
        self.imgidx_bookmark = self.imglist.Add(cw.cwpy.rsrc.dialogs["BOOKMARK"])
        self.imgidx_party = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["MEMBER"])
        self.imgidx_standby = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_CAST"])
        self.imgidx_skill = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_SKILL"])
        self.imgidx_item = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_ITEM"])
        self.imgidx_beast = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_BEAST"])
        self.imgidx_gossip = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_GOSSIP"])
        self.imgidx_completestamp = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["EVT_GET_COMPLETESTAMP"])
        self.imgidx_money = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["MONEY"])
        self.imgidx_album = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["CARD"])
        self.imgidx_partyrecord = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["SELECTION"])
        self.imgidx_savedjpdcimage = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["JPDCIMAGE"])
        self.imgidx_variables = self.imglist.Add(cw.cwpy.rsrc.debugs_wx["VARIABLES"])

        self.imgidx_bookmark_nc = self.imgidx_bookmark
        self.imgidx_party_nc = self.imgidx_party
        self.imgidx_standby_nc = self.imgidx_standby
        self.imgidx_skill_nc = self.imgidx_skill
        self.imgidx_item_nc = self.imgidx_item
        self.imgidx_beast_nc = self.imgidx_beast
        self.imgidx_gossip_nc = self.imgidx_gossip
        self.imgidx_completestamp_nc = self.imgidx_completestamp
        self.imgidx_money_nc = self.imgidx_money
        self.imgidx_album_nc = self.imgidx_album
        self.imgidx_partyrecord_nc = self.imgidx_partyrecord
        self.imgidx_savedjpdcimage_nc = self.imgidx_savedjpdcimage
        self.imgidx_variables_nc = self.imgidx_variables

        self.imgidx_table_c = {
            self.imgidx_bookmark_nc: self.imgidx_bookmark,
            self.imgidx_party_nc: self.imgidx_party,
            self.imgidx_standby_nc: self.imgidx_standby,
            self.imgidx_skill_nc: self.imgidx_skill,
            self.imgidx_item_nc: self.imgidx_item,
            self.imgidx_beast_nc: self.imgidx_beast,
            self.imgidx_gossip_nc: self.imgidx_gossip,
            self.imgidx_completestamp_nc: self.imgidx_completestamp,
            self.imgidx_money_nc: self.imgidx_money,
            self.imgidx_album_nc: self.imgidx_album,
            self.imgidx_partyrecord_nc: self.imgidx_partyrecord,
            self.imgidx_savedjpdcimage_nc: self.imgidx_savedjpdcimage,
            self.imgidx_variables_nc: self.imgidx_variables
        }
        self.imgidx_table_nc = {}
        for key, value in self.imgidx_table_c.items():
            self.imgidx_table_nc[value] = key

        self.datalist.InsertItem(0, "", 0)
        rect = self.datalist.GetItemRect(0, wx.LIST_RECT_LABEL)
        self.datalist.SetColumnWidth(0, rect.x)
        self.datalist.DeleteAllItems()

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, cw.wins((100, 30)), cw.cwpy.msgs["decide"])
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
        var_fpath = cw.util.join_paths(yadodir, "SkinVariables.xml")
        if os.path.isfile(var_fpath):
            var_data = cw.data.xml2element(var_fpath)
            skin_vars = cw.data.YadoData.get_savedvariables_from(var_data, keymode="Key")
            skins, keytable = cw.data.get_skinkeys()
            keys = []
            for key, (name, author) in keytable.items():
                keys.append((name, author, key))
            for name, author, key in cw.util.sorted_by_attr(keys):
                if key not in skin_vars:
                    continue
                e = skin_vars[key][0]
                self.datalist.InsertItem(i, "")
                if author:
                    s = "スキン「%s(%s)」の状態変数" % (name, author)
                else:
                    s = "スキン「%s」の状態変数" % (name)
                self.datalist.SetItem(i, 0, s)
                self.datalist.SetItemColumnImage(i, 0, self.imgidx_variables_nc)
                self.datalist.CheckItem(i, False)
                self.data.append((key, e, True, name, author))
                i += 1

        data = cw.data.xml2etree(cw.util.join_paths(yadodir, "Environment.xml"))
        bookmark = data.find("Bookmarks")
        if bookmark is not None:
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["bookmark"])
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_bookmark_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(bookmark)
            i += 1

        cashbox = data.getint("Property/Cashbox", 0)
        if cashbox:
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["currency"] % (cashbox))
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_money_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(cashbox)
            i += 1

        gossips = data.find("Gossips")
        if gossips is not None and len(gossips):
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["gossip"])
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_gossip_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(gossips)
            i += 1

        completestamp = data.find("CompleteStamps")
        if completestamp is not None and len(completestamp):
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["complete_stamp"])
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_completestamp_nc)
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

        saved_variables = cw.data.YadoData.get_savedvariables(data)

        partymembers = set()

        if album:
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["album"])
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_album_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(album)
            i += 1

        if partyrecord:
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["select_party_record"])
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_partyrecord_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(partyrecord)
            i += 1

        keys = list(saved_variables.keys())
        for key in cw.util.sorted_by_attr(keys):
            header = saved_variables[key][0]
            self.datalist.InsertItem(i, "")
            if key[1]:
                s = "状態変数 - %s(%s)" % (key[0], key[1])
            else:
                s = "状態変数 - %s" % (key[0])
            self.datalist.SetItem(i, 0, s)
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_variables_nc)
            self.datalist.CheckItem(i, False)
            self.data.append((key, header, False))
            i += 1

        keys = list(savedjpdcimage.keys())
        for key in cw.util.sorted_by_attr(keys):
            header = savedjpdcimage[key]
            self.datalist.InsertItem(i, "")
            if header.scenarioauthor:
                s = "JPDC - %s(%s)" % (header.scenarioname, header.scenarioauthor)
            else:
                s = "JPDC - %s" % (header.scenarioname)
            self.datalist.SetItem(i, 0, s)
            self.datalist.SetItemColumnImage(i, 0, self.imgidx_savedjpdcimage_nc)
            self.datalist.CheckItem(i, False)
            self.data.append(header)
            i += 1

        for header in itertools.chain(parties, standbys, cards):
            if isinstance(header, cw.header.PartyHeader):
                image = self.imgidx_party_nc
                for member in header.members:
                    partymembers.add(member)
            elif isinstance(header, cw.header.AdventurerHeader):
                if os.path.splitext(os.path.basename(header.fpath))[0] in partymembers:
                    continue
                image = self.imgidx_standby_nc
            elif isinstance(header, cw.header.CardHeader):
                if header.type == "SkillCard":
                    image = self.imgidx_skill_nc
                elif header.type == "ItemCard":
                    image = self.imgidx_item_nc
                elif header.type == "BeastCard":
                    image = self.imgidx_beast_nc
                else:
                    assert False
            else:
                assert False
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, header.name)
            self.datalist.SetItemColumnImage(i, 0, image)
            self.datalist.CheckItem(i, False)
            self.data.append(header)
            i += 1

        if not self.data:
            self.datalist.InsertItem(i, "")
            self.datalist.SetItem(i, 0, cw.cwpy.msgs["transfer_no_item"])

        self._enable_btn()

    def _enable_btn(self):
        btn = self.fromyado.GetSelection() != self.toyado.GetSelection()
        if btn:
            btn = False
            for index in range(self.datalist.GetItemCount()):
                if self.datalist.IsItemChecked(index):
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
        cw.fsync.sync()
        index1 = self.fromyado.GetSelection()
        index2 = self.toyado.GetSelection()
        if index1 == index2:
            return
        cw.cwpy.play_sound("signal")
        name1 = self.yadonames[index1]
        name2 = self.yadonames[index2]
        seq = []
        for i in range(self.datalist.GetItemCount()):
            if self.datalist.IsItemChecked(i):
                seq.append(self.data[i])
        s = cw.cwpy.msgs["confirm_transfer"] % (name1, len(seq), name2)
        dlg = cw.dialog.message.YesNoMessage(self, cw.cwpy.msgs["message"], s)
        cw.cwpy.frame.move_dlg(dlg)

        result = dlg.ShowModal()
        dlg.Destroy()
        if result != wx.ID_OK:
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
                counter += 1  # 全体情報
                counter += 1  # 冒険中情報
                counter += len(data.members)
                for cardtype in ("SkillCard", "ItemCard", "BeastCard"):
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
            elif isinstance(data, tuple) and data[1].tag == "Variables":
                # 保存された状態変数(シナリオ・スキン)
                counter += 1
            else:
                assert False

        class TransferThread(threading.Thread):
            def __init__(self, outer):
                threading.Thread.__init__(self)
                self.outer = outer

                def _skindir_to_scedir(skindir):
                    scedir = "Scenario"
                    if skindir:
                        skindir = cw.util.join_paths("Data/Skin", skindir)
                        fpath = cw.util.join_paths(skindir, "Skin.xml")
                        if os.path.isfile(fpath):
                            prop = cw.header.GetProperty(fpath)
                            skintype = prop.properties.get("Type", "")
                            if skintype:
                                for type, folder in cw.cwpy.setting.folderoftype:
                                    if type == skintype:
                                        scedir = folder
                                        break
                    return scedir

                prop = cw.header.GetProperty(cw.util.join_paths(fromyado, "Environment.xml"))
                skindir = prop.properties.get("Skin", "")
                self.fromscedir = _skindir_to_scedir(skindir)
                self.environment = cw.data.xml2etree(cw.util.join_paths(toyado, "Environment.xml"))
                self.skin_vars = None
                self.saved_variables = cw.data.YadoData.get_savedvariables(self.environment)
                self.toscedir = _skindir_to_scedir(self.environment.gettext("Property/Skin", ""))
                self.imgpaths = {}
                self.membertable = {}
                self.num = 0
                self.msg = ""

            def run(self):
                cw.fsync.sync()
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
                                seq2.append(data)  # 編成記録はAdventurerHeaderよりも遅延させる
                                continue
                            else:
                                assert False
                        elif isinstance(data, cw.header.SavedJPDCImageHeader):
                            # 保存されたJPDCイメージ
                            if data.scenarioauthor:
                                name = "JPDC - %s(%s)" % (data.scenarioname, data.scenarioauthor)
                            else:
                                name = "JPDC - %s" % (data.scenarioname)
                        elif isinstance(data, tuple) and data[1].tag == "Variables" and not data[2]:
                            # 保存された状態変数
                            scenario, author = data[0]
                            if author:
                                name = "状態変数 - %s(%s)" % (scenario, author)
                            else:
                                name = "状態変数 - %s" % (scenario)
                        elif isinstance(data, tuple) and data[1].tag == "Variables" and data[2]:
                            # 保存されたスキンの状態変数
                            scenario, author = data[3], data[4]
                            if author:
                                name = "スキン「%s(%s)」の状態変数" % (scenario, author)
                            else:
                                name = "スキン「%s」の状態変数" % (scenario)
                        else:
                            name = data.name
                        self.msg = cw.cwpy.msgs["transfer_processing"] % (name)

                        if isinstance(data, cw.data.CWPyElement):
                            if data.tag == "Bookmarks":
                                # ブックマーク
                                self.outer.transfer_bookmark(self.fromscedir, self.toscedir, fromyado, toyado,
                                                             data, self)
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
                        elif isinstance(data, tuple) and data[1].tag == "Variables" and not data[2]:
                            # 保存された状態変数
                            self.outer.transfer_savedvariables(fromyado, toyado, data, yadodb, data, self)
                        elif isinstance(data, tuple) and data[1].tag == "Variables" and data[2]:
                            # 保存されたスキンの状態変数
                            self.outer.transfer_skinvariables(fromyado, toyado, data, yadodb, data, self)
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
                    if self.skin_vars and self.skin_vars[0].is_edited:
                        self.skin_vars[0].write()
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
            bookmark = cw.data.make_element("Bookmarks", "")
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
                    path = cw.util.get_keypath(path)
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
                path = cw.util.get_keypath(path)
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
            if e.text not in exists:
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
        pdata.fpath = cw.util.join_paths(dstdir, "Party.xml")
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
            e.fpath = ""
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

            fname = cw.util.join_paths(cw.tempdir, "ScenarioLog/ScenarioLog.xml")
            etree = cw.data.xml2etree(fname)
            e = etree.find("Property/MusicPath")
            if e is not None:
                if e.getbool(".", "inusecard", False):
                    e.text = counter.imgpaths.get(e.text, e.text)
            e = etree.find("Property/MusicPaths")
            if e is not None:
                for e2 in e:
                    if e2.getbool(".", "inusecard", False):
                        e2.text = counter.imgpaths.get(e2.text, e2.text)
            for e in etree.getfind("BgImages"):
                if e.getbool("ImagePath", "inusecard", False):
                    e = e.find("ImagePath")
                    e.text = counter.imgpaths.get(e.text, e.text)
            etree.write()

            fname = cw.util.join_paths(cw.tempdir, "ScenarioLog/Face/Log.xml")
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

            dname = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party")
            etree = None
            for p in os.listdir(dname):
                if p.lower().endswith(".xml"):
                    etree = cw.data.xml2etree(cw.util.join_paths(dname, p))
                    break
            for e in etree.getfind("Property/Members"):
                e.text = counter.membertable[e.text]
            etree.write()

            dname = cw.util.join_paths(cw.tempdir, "ScenarioLog/Members")
            dname2 = cw.util.join_paths(cw.tempdir, "ScenarioLog/Members2")
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

            wsl = cw.util.join_paths(dstdir, "Party.wsl")
            cw.util.compress_zip(cw.util.join_paths(cw.tempdir, "ScenarioLog"), wsl, unicodefilename=True)
            cw.util.remove(cw.util.join_paths(cw.tempdir, "ScenarioLog"))
        counter.num += 1

        # 宿DBへ追加
        fpath = cw.util.join_paths(dstdir, os.path.basename(header.fpath))
        yadodb.insert_party(fpath)

    def transfer_album(self, fromyado, toyado, album, yadodb, counter):
        # アルバムの転送
        for header in album:
            data = cw.data.xml2etree(header.fpath)
            cname = data.gettext("Property/Name", "")
            dstdir = cw.util.join_paths(toyado, "Material", "Album", cname if cname else "noname")
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
        assert isinstance(data, (cw.data.CWPyElement, cw.data.CWPyElementTree)), data
        cname = data.gettext("Property/Name", "")
        dstdir = cw.util.join_paths(toyado, "Material", "Adventurer", cname if cname else "noname")
        dstdir = cw.util.dupcheck_plus(dstdir, yado=False)
        can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
        cw.cwpy.copy_materials(data.find("Property"), dstdir, from_scenario=False, scedir="", yadodir=fromyado,
                               toyado=toyado, adventurer=True, imgpaths=counter.imgpaths,
                               can_loaded_scaledimage=can_loaded_scaledimage)
        if not overwrite:
            data.fpath = data.fpath.replace(fromyado + "/", toyado + "/", 1)
            data.fpath = cw.util.dupcheck_plus(data.fpath, yado=False)

        for e in itertools.chain(data.find("SkillCards"),
                                 data.find("ItemCards"),
                                 data.find("BeastCards")):
            assert isinstance(e, cw.data.CWPyElement), e
            e.fpath = ""
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
        assert isinstance(data, (cw.data.CWPyElement, cw.data.CWPyElementTree)), data
        e = data.find("Property/Materials")
        if e is None:
            cname = data.gettext("Property/Name", "")
            dstdir = cw.util.join_paths(toyado, "Material", data.getroot().tag,
                                        data.gettext("Property/Name", cname if cname else "noname"))
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
        savejpdcdir = cw.util.join_paths(toyado, "SavedJPDCImage")

        fromdir = cw.util.join_paths(fromyado, "SavedJPDCImage", header.dpath)
        todir = cw.util.join_paths(savejpdcdir, header.dpath)
        todir = cw.util.dupcheck_plus(todir, yado=False)

        dpath = os.path.dirname(todir)
        if not os.path.isdir(dpath):
            os.makedirs(dpath)
        shutil.copytree(fromdir, todir)

        toheader = table.get(key, None)
        if toheader:
            dpath = cw.util.join_paths(toyado, "SavedJPDCImage", toheader.dpath)
            cw.util.remove(dpath)
            if yadodb:
                fpath = cw.util.join_paths("SavedJPDCImage", toheader.dpath, "SavedJPDCImage.xml")
                yadodb.delete_savedjpdcimage(fpath, commit=False)

        header.dpath = cw.util.relpath(todir, savejpdcdir)
        header.fpath = cw.util.join_paths(todir, "SavedJPDCImage.xml")

        data = cw.data.xml2etree(cw.util.join_paths(fromdir, "SavedJPDCImage.xml"))
        data.edit("Materials", header.dpath, "dpath")
        data.fpath = cw.util.join_paths(todir, "SavedJPDCImage.xml")
        data.write()

        if yadodb:
            yadodb.insert_savedjpdcimageheader(header, commit=False)

        counter.num += 1

    def transfer_savedvariables(self, fromyado, toyado, header, yadodb, d, counter):
        # 保存された状態変数の転送
        # 転送先に同じシナリオの状態変数がある場合は上書きする
        key, e, _type = d
        data = counter.environment.find("SavedVariables")
        if key in counter.saved_variables:
            e_target = counter.saved_variables[key][0]
            e_target.clear()
        else:
            if data is None:
                data = cw.data.make_element("SavedVariables")
                counter.environment.append(".", data)
            e_target = cw.data.make_element("Variables")
            data.append(e_target)
        e_target.set("scenario", key[0])
        e_target.set("author", key[1])
        for e_vars in e:
            e_target.append(e_vars)
        counter.environment.is_edited = True

        counter.num += 1

    def transfer_skinvariables(self, fromyado, toyado, header, yadodb, d, counter):
        # 保存されたスキンの状態変数の転送
        # 転送先に同じスキンの状態変数がある場合は上書きする
        key, e, _type, _name, _author = d
        if counter.skin_vars is None:
            var_fpath = cw.util.join_paths(toyado, "SkinVariables.xml")
            if not os.path.isfile(var_fpath):
                cw.xmlcreater.create_skinvariables(var_fpath)
            e_vars = cw.data.xml2element(var_fpath)
            data = cw.data.xml2etree(element=e_vars)
            counter.skin_vars = (data, cw.data.YadoData.get_savedvariables_from(e_vars, keymode="Key"))
        data, vars = counter.skin_vars

        if key in vars:
            e_target = vars[key][0]
            e_target.clear()
        else:
            e_target = cw.data.make_element("Variables")
            data.append(".", e_target)
        e_target.set("key", key)
        for e_vars in e:
            e_target.append(e_vars)
        data.is_edited = True

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
        y += (h-th) // 2
        dc.DrawText(s, x, y)

        # 転送先
        s = cw.cwpy.msgs["transfer_to_base"]
        _tw, th = dc.GetTextExtent(s)
        x, y, _w, h = self.toyado.GetRect()
        x = cw.wins(5)
        y += (h-th) // 2
        dc.DrawText(s, x, y)

    def _bind(self):
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.fromyado.Bind(wx.EVT_CHOICE, self.OnFromYado)
        self.toyado.Bind(wx.EVT_CHOICE, self.OnToYado)
        self.datalist.Bind(wx.EVT_LIST_ITEM_CHECKED, self.OnListItemChecked)
        self.datalist.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.OnListItemChecked)

    def _do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_h1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h2 = wx.BoxSizer(wx.HORIZONTAL)

        dc = wx.ClientDC(self)
        font = cw.cwpy.rsrc.get_wxfont("dlgmsg2", pixelsize=cw.wins(16))
        dc.SetFont(font)
        w = dc.GetFullMultiLineTextExtent(cw.cwpy.msgs["transfer_from_base"])[0]
        w = max(w, dc.GetFullMultiLineTextExtent(cw.cwpy.msgs["transfer_to_base"])[0])
        w += cw.wins(3)

        sizer_h1.Add((w, cw.wins(0)), 0, wx.RIGHT, cw.wins(3))
        sizer_h1.Add(self.fromyado, 0, 0, 0)
        sizer_h2.Add((w, cw.wins(0)), 0, wx.RIGHT, cw.wins(3))
        sizer_h2.Add(self.toyado, 0, 0, 0)

        sizer_2.Add(sizer_h1, 0, wx.EXPAND | wx.BOTTOM, cw.wins(5))
        sizer_2.Add(sizer_h2, 0, wx.EXPAND | wx.BOTTOM, cw.wins(5))

        sizer_2.Add(self.datalist, 1, wx.EXPAND, cw.wins(5))

        sizer_1.Add(sizer_2, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, cw.wins(5))

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_2.Add(self.okbtn, 0, wx.LEFT | wx.RIGHT, cw.wins(5))
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_2.Add(self.cnclbtn, 0, wx.LEFT | wx.RIGHT, cw.wins(5))
        sizer_2.Add((0, 0), 1, 0, 0)
        sizer_1.Add(sizer_2, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, cw.wins(10))

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

    def OnListItemChecked(self, event):
        self.datalist.OnListItemChecked(event)
        self._enable_btn()


def main():
    pass


if __name__ == "__main__":
    main()
