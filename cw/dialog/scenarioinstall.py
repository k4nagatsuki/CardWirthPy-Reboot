#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import os
import sys
import shutil
import threading
import time
import wx

import cw

from typing import Dict, Iterable, List, Optional, Set, Tuple, Union


# ------------------------------------------------------------------------------
# シナリオフォルダ選択ダイアログ
# ------------------------------------------------------------------------------

class SelectScenarioDirectory(wx.Dialog):
    """
    シナリオフォルダ選択ダイアログ。
    """
    def __init__(self, parent: wx.TopLevelWindow, title: str, text: str, db: cw.scenariodb.Scenariodb, skintype: str,
                 scedir: str) -> None:
        # ダイアログボックス作成
        wx.Dialog.__init__(self, parent, -1, title, size=cw.wins((420, 400)),
                           style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.MINIMIZE_BOX)
        self.cwpy_debug = False
        self.SetDoubleBuffered(True)
        self.db = db
        self.skintype = skintype
        self.scedir = scedir
        self.path = ""

        # メッセージ
        self.text = text

        # フォルダの作成
        bmp = cw.cwpy.rsrc.dialogs["CREATE_DIRECTORY"]
        self.createdirbtn = cw.cwpy.rsrc.create_wxbutton(self, -1, (cw.wins(24), cw.wins(24)), bmp=bmp)
        self.createdirbtn.SetToolTip(wx.ToolTip(cw.cwpy.msgs["create_directory"]))

        # フォルダ選択用ツリー
        self.tree = wx.TreeCtrl(self, -1, size=(-1, -1),
                                style=wx.BORDER | wx.TR_SINGLE | wx.TR_DEFAULT_STYLE)
        self.tree.SetFont(cw.cwpy.rsrc.get_wxfont("tree", pixelsize=cw.wins(15)-1))
        self.tree.SetDoubleBuffered(True)
        self.tree.imglist = wx.ImageList(cw.wins(16), cw.wins(16))
        self._imgidx_dir = self.tree.imglist.Add(cw.cwpy.rsrc.dialogs["DIRECTORY"])
        name = os.path.basename(scedir)
        if sys.platform == "win32" and name.lower().endswith(".lnk"):
            name = cw.util.splitext(name)[0]
        self.tree.root = self.tree.AddRoot(name, self._imgidx_dir)
        self.tree.SetItemData(self.tree.root, scedir)
        self.tree.SetImageList(self.tree.imglist)
        self.tree.SelectItem(self.tree.root)

        # 前回の選択を復元する
        dirstack = cw.cwpy.setting.installed_dir.get(scedir, [])
        if not dirstack and os.path.normcase("A") == os.path.normcase("a"):
            # 大文字・小文字を区別しないファイルシステム
            for key, value in cw.cwpy.setting.installed_dir.items():
                if os.path.normcase(key) == os.path.normcase(scedir):
                    dirstack = value
                    break
        self._create_treeitems(self.tree.root, dirstack)
        self.tree.Expand(self.tree.root)

        # ボタン
        self.create_buttons()

        # layout
        self._resize()
        self._do_layout()
        # bind
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnTreeItemCollapsed)
        self.createdirbtn.Bind(wx.EVT_BUTTON, self.OnCreateDirBtn)

        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        for child in self.GetChildren():
            child.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnResize)

    def create_buttons(self) -> None:
        # OK・キャンセルボタン
        self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_OK, cw.wins((120, 30)), cw.cwpy.msgs["ok"])
        self.nobtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, cw.wins((120, 30)), cw.cwpy.msgs["cancel"])
        self.buttons = (self.yesbtn, self.nobtn)

        self.yesbtn.Bind(wx.EVT_BUTTON, self.OnOk)
        self.nobtn.Bind(wx.EVT_BUTTON, self.OnCancel)

    def _do_layout(self) -> None:
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.AddStretchSpacer(1)
        sizer_2.Add((cw.wins(0), self._textheight + cw.wins(24)), 0, 0, 0)
        if self.createdirbtn.GetContainingSizer():
            self.createdirbtn.GetContainingSizer().Detach(self.createdirbtn)
        sizer_2.Add(self.createdirbtn, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, cw.wins(10))
        sizer_1.Add(sizer_2, 0, wx.EXPAND, wx.LEFT | wx.RIGHT, cw.wins(10))

        if self.tree.GetContainingSizer():
            self.tree.GetContainingSizer().Detach(self.tree)
        sizer_1.Add(self.tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, cw.wins(8))

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3.AddStretchSpacer(1)
        for i, button in enumerate(self.buttons):
            if button.GetContainingSizer():
                button.GetContainingSizer().Detach(button)
            sizer_3.Add(button, 0, 0, 0)
            sizer_3.AddStretchSpacer(1)

        sizer_1.Add(sizer_3, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, cw.wins(12))

        self.SetSizer(sizer_1)
        self.Layout()

    def _create_treeitems(self, treeitem: wx.TreeItemId, dirstack: Optional[List[str]] = None) -> None:
        """treeitemが示すディレクトリのサブディレクトリを読み込む。
        シナリオフォルダは除外される。
        """
        if dirstack is None:
            dirstack = []
        self.tree.Freeze()
        self.tree.DeleteChildren(treeitem)
        dpath = self.tree.GetItemData(treeitem)
        selected = None

        for dname in get_dpaths(dpath):
            name = os.path.basename(dname)
            image = self._imgidx_dir
            if sys.platform == "win32" and name.lower().endswith(".lnk"):
                name = cw.util.splitext(name)[0]
            item = self.tree.AppendItem(treeitem, name, image)
            self.tree.SetItemData(item, dname)
            if dirstack and os.path.normcase(os.path.basename(dname)) == os.path.normcase(dirstack[0]):
                if 1 < len(dirstack):
                    self._create_treeitems(item, dirstack[1:])
                    self.tree.Expand(item)
                    continue
                self.tree.SelectItem(item)
                selected = item
            self.tree.AppendItem(item, "読込中...")
        self.tree.Thaw()
        if selected:
            cw.cwpy.frame.exec_func(self.tree.ScrollTo, selected)

    def OnTreeItemExpanded(self, event: wx.TreeEvent) -> None:
        selitem = event.GetItem()
        self._create_treeitems(selitem)

    def OnTreeItemCollapsed(self, event: wx.TreeEvent) -> None:
        if not self.tree.IsShown():
            return
        item = event.GetItem()
        self.tree.DeleteChildren(item)
        self.tree.AppendItem(item, "読込中...")

    def OnOk(self, event: wx.CommandEvent) -> None:
        selitem = self.tree.GetSelection()
        if not selitem.IsOk():
            return
        dstpath = self.tree.GetItemData(selitem)
        if not dstpath:
            return
        self.path = dstpath
        self.dirstack = self.get_dirstack(selitem)
        cw.cwpy.setting.installed_dir[self.scedir] = self.get_dirstack(selitem)
        self.SetReturnCode(wx.ID_OK)
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
        self.ProcessEvent(btnevent)

    def OnCancel(self, event: wx.CommandEvent) -> None:
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnResize(self, event: wx.SizeEvent) -> None:
        if not self.tree.IsShown():
            return

        self._resize()

        self._do_layout()
        self.Refresh()

    def _resize(self) -> None:
        """
        テキストの折り返し位置を計算する。
        """
        dc = wx.ClientDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        csize = self.GetClientSize()
        btnw = self.createdirbtn.GetSize()[0]
        self._wrapped_text = cw.util.wordwrap(self.text, csize[0]-cw.wins(20)-btnw-cw.wins(10),
                                              lambda s: dc.GetTextExtent(s)[0])
        _w, self._textheight, _lineheight = dc.GetFullMultiLineTextExtent(self._wrapped_text)

    def OnPaint(self, evt: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # massage
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        dc.DrawLabel(self._wrapped_text, (cw.wins(10), cw.wins(12), csize[0], self._textheight), wx.ALIGN_LEFT)

    def OnCreateDirBtn(self, event: wx.CommandEvent) -> None:
        selitem = self.tree.GetSelection()
        if not selitem.IsOk():
            return
        dpath = self.tree.GetItemData(selitem)
        if not dpath:
            return

        dpath = create_dir(self, dpath)
        if dpath:
            cw.cwpy.play_sound("harvest")
            self._create_treeitems(selitem)
            self.tree.Expand(selitem)
            dpath = cw.util.get_keypath(dpath)

            item, cookie = self.tree.GetFirstChild(selitem)
            while item.IsOk():
                dpath2 = self.tree.GetItemData(item)
                dpath2 = cw.util.get_keypath(dpath2)
                if dpath == dpath2:
                    self.tree.SelectItem(item)
                    if not self.tree.IsVisible(item):
                        self.tree.ScrollTo(item)
                    break

                item, cookie = self.tree.GetNextChild(selitem, cookie)

    def get_dirstack(self, paritem: wx.TreeItemId) -> List[str]:
        """指定されたアイテムまでの経路を返す。
        """
        dirstack = []
        while paritem and paritem.IsOk():
            selpath = self.tree.GetItemData(paritem)
            selpath = os.path.basename(selpath)
            dirstack.append(selpath)
            paritem = self.tree.GetItemParent(paritem)

        dirstack.reverse()
        return dirstack[1:]


# ------------------------------------------------------------------------------
# シナリオインストールダイアログ
# ------------------------------------------------------------------------------

class ScenarioInstall(SelectScenarioDirectory):
    """
    シナリオインストールダイアログ。
    """
    def __init__(self, parent: wx.TopLevelWindow, db: cw.scenariodb.Scenariodb,
                 headers: Dict[Tuple[str, str], List[cw.header.ScenarioHeader]],
                 notscenariofiles: Dict[Tuple[str, str], List[str]], skintype: str, scedir: str) -> None:
        headers_seq = functools.reduce(lambda a, b: a + b, iter(headers.values()))
        assert 0 < len(headers_seq)

        # メッセージ
        if 1 < len(headers_seq):
            s = "%s本のシナリオのインストール先を選択してください。" % (len(headers_seq))
        else:
            name = headers_seq[0].name
            if headers_seq[0].author:
                name += "(%s)" % headers_seq[0].author
            s = "「%s」のインストール先を選択してください。" % (name)

        self.headers = headers
        self.notscenariofiles = notscenariofiles

        # ダイアログボックス作成
        SelectScenarioDirectory.__init__(self, parent, "シナリオのインストール", s,
                                         db, skintype, scedir)

    def create_buttons(self) -> None:
        headers_seq = functools.reduce(lambda a, b: a + b, iter(self.headers.values()))
        assert 0 < len(headers_seq)

        # インストール・キャンセルボタン
        self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_OK, cw.wins((120, 30)), "インストール")
        self.yesbtn.SetToolTip(create_installdesc(headers_seq))
        self.nobtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, cw.wins((120, 30)), cw.cwpy.msgs["cancel"])
        self.buttons = (self.yesbtn, self.nobtn)

        self.yesbtn.Bind(wx.EVT_BUTTON, self.OnInstallBtn)
        self.nobtn.Bind(wx.EVT_BUTTON, self.OnCancel)

    def OnInstallBtn(self, event: wx.CommandEvent) -> None:
        from . import message

        selitem = self.tree.GetSelection()
        if not selitem.IsOk():
            return
        dstpath = self.tree.GetItemData(selitem)
        if not dstpath:
            return

        failed, paths, _filepaths, cancelled = install_scenario(self, self.headers, self.notscenariofiles, self.scedir,
                                                                dstpath, self.db, self.skintype)

        if paths:
            if 1 < len(paths):
                s = "%s本のシナリオをインストールしました。" % (len(paths))
            else:
                header = self.db.search_path(paths[0])
                if not header:
                    return
                name = header.name
                if header.author:
                    name += "(%s)" % header.author
                s = "「%s」をインストールしました。" % (name)

            cw.cwpy.play_sound("harvest")
            dlg = message.Message(self, cw.cwpy.msgs["message"], s, mode=2)
            self.Parent.move_dlg(dlg)
            dlg.ShowModal()
            dlg.Destroy()

        if cancelled:
            return

        cw.cwpy.setting.installed_dir[self.scedir] = self.get_dirstack(selitem)

        self.Close()


def get_dpaths(dpath: str) -> List[str]:
    """
    クラシックなシナリオ以外のフォルダの一覧を返す。
    (ショートカット類も含む)
    """
    seq = []

    try:
        dpath2 = cw.util.get_linktarget(dpath)
        if os.path.isdir(dpath2):
            for dname in os.listdir(dpath2):
                path = cw.util.join_paths(dpath2, dname)
                if is_listitem(path) and not cw.scenariodb.is_scenario(path):
                    seq.append(path)
    except Exception:
        cw.util.print_ex()

    cw.util.sort_by_filename(seq)
    return seq


def is_listitem(path: str) -> bool:
    """
    指定されたパスがシナリオ選択ダイアログで選択可能ならTrueを返す。
    """
    path = cw.util.get_linktarget(path)
    return os.path.isdir(path) or cw.scenariodb.is_scenario(path)


def to_scenarioheaders(paths: List[str], db: cw.scenariodb.Scenariodb, skintype: str,
                       link: bool) -> Tuple[Dict[Tuple[str, str], List[cw.header.ScenarioHeader]],
                                            Dict[Tuple[str, str], List[str]]]:
    """
    pathsをcw.header.ScenarioHeaderに変換する。
    パスがシナリオか否かの判定にシナリオDBを使用する。
    """
    headers: Dict[Tuple[str, str], List[cw.header.ScenarioHeader]] = {}
    notscenariofiles: Dict[Tuple[str, str], List[str]] = {}
    if not paths:
        return headers, notscenariofiles

    exists = set()

    if os.path.isfile(paths[0]) and cw.util.splitext(paths[0])[1].lower() in (".xml", ".wsm"):
        paths = [os.path.dirname(paths[0])]

    allparent = os.path.dirname(paths[0])

    for path in paths:
        def recurse(parent: str, path: str, notscenariofiles2: Dict[Tuple[str, str], List[str]]) -> bool:
            # pathまたはサブディレクトリにシナリオを持つ場合はTrueを返す

            if not link and sys.platform == "win32" and path.lower().endswith(".lnk"):
                # ショートカットはショートカット先が削除される等の事故を起すので除外する
                return False

            hparent = cw.util.relpath(parent, allparent)
            if hparent.startswith(".." + os.path.sep):
                hparent = ""
            parentinfo = (parent, hparent)

            if cw.scenariodb.is_scenario(path):
                header = db.search_path(path, skintype=skintype)
                if header and not (header.name, header.author) in exists:
                    seq = headers.get(parentinfo, [])
                    if not seq:
                        headers[parentinfo] = seq
                    seq.append(header)
                    exists.add((header.name, header.author))
                    return True
            elif os.path.exists(path):
                copyfile = False
                if os.path.isdir(path):
                    haschildren = False
                    for fname in os.listdir(path):
                        copyfile |= recurse(path, cw.util.join_paths(path, fname), notscenariofiles2)
                        haschildren = True
                    if haschildren:
                        # 空ディレクトリ以外は下の階層のファイル・ディレクトリの
                        # コピー時に親ディレクトリが生成される処理に任せる
                        return copyfile

                # ファイルまたはディレクトリをインストール対象として記憶する
                s = notscenariofiles2.get(parentinfo, None)
                if s is None:
                    s = []
                    notscenariofiles2[parentinfo] = s
                s.append(path)
                return copyfile

            return False

        notscenariofiles2 = {}
        if recurse(allparent, path, notscenariofiles2):
            for key, value in notscenariofiles2.items():
                s = notscenariofiles.get(key, None)
                if s is None:
                    notscenariofiles[key] = value
                else:
                    s.extend(value)

    return headers, notscenariofiles


def create_dir(parentdialog: ScenarioInstall, dpath: str) -> str:
    cw.cwpy.play_sound("signal")
    name = os.path.basename(dpath)
    if sys.platform == "win32" and name.lower().endswith(".lnk"):
        name = cw.util.splitext(name)[0]
    dpath = cw.util.get_linktarget(dpath)

    s = "%sに作成する新しいフォルダの名前を入力してください。" % (name)
    dname = cw.util.join_paths(dpath, "新規フォルダ")
    dname = cw.util.dupcheck_plus(dname, yado=False)
    dname = os.path.basename(dname)
    dlg = cw.dialog.edit.InputTextDialog(parentdialog, "新規フォルダ",
                                         msg=s,
                                         text=dname)
    cw.cwpy.frame.move_dlg(dlg)
    if dlg.ShowModal() == wx.ID_OK:
        dpath = cw.util.join_paths(dpath, dlg.text)
        dlg.Destroy()
        dpath = cw.util.dupcheck_plus(dpath, yado=False)
        os.makedirs(dpath)
        return dpath
    else:
        dlg.Destroy()
        return ""


def install_scenario(parentdialog: ScenarioInstall, headers: Dict[Tuple[str, str], List[cw.header.ScenarioHeader]],
                     notscenariofiles: Dict[Tuple[str, str], List[str]], scedir: str, dstpath: str,
                     db: cw.scenariodb.Scenariodb,
                     skintype: str) -> Tuple[Optional[cw.header.ScenarioHeader],
                                             List[Union[cw.header.ScenarioHeader,
                                                        str,
                                                        "cw.dialog.scenarioselect.FindResult"]],
                                             List[str], bool]:
    """
    headersをインストールする。
    進捗ダイアログが表示される。
    """
    dstpath = cw.util.get_linktarget(dstpath)

    if not cw.cwpy.setting.install_notscenariofiles:
        notscenariofiles: Dict[Tuple[str, str], List[str]] = {}

    # インストール済みの情報が見つかったシナリオ
    db_exists: Dict[str, List[cw.header.ScenarioHeader]] = {}
    links: List[str] = []  # ショートカットファイルのリスト

    headers_len = 0
    for headers_seq in headers.values():
        headers_len += len(headers_seq)
        for header in headers_seq:
            fpath = header.get_fpath()

            header2 = db.find_scenario(header.name, header.author, skintype=skintype,
                                       ignore_dpath=header.dpath, ignore_fname=header.fname)
            seq = []
            for header3 in header2:
                fpath = header3.get_fpath()
                if sys.platform == "win32" and fpath.lower().endswith(".lnk") and os.path.isfile(fpath):
                    links.append(fpath)
                    continue
                seq.append(header3)
            if seq:
                db_exists[header.get_fpath()] = seq

    for files_seq in notscenariofiles.values():
        headers_len += len(files_seq)

    if db_exists:
        dlg = OverwriteScenarioDialog(parentdialog, scedir, db_exists)
        cw.cwpy.frame.move_dlg(dlg)
        ret = dlg.ShowModal()
        dlg.Destroy()
        if ret != wx.ID_OK:
            return True, [], [], True
        else:
            db_repls = dlg.db_repls
    else:
        db_repls = {}

    # プログレスダイアログ表示
    dlg = cw.dialog.progress.ProgressDialog(parentdialog, "シナリオのインストール",
                                            "", maximum=headers_len, cancelable=True)

    class InstallThread(threading.Thread):
        def __init__(self, headers: Dict[Tuple[str, str], List[cw.header.ScenarioHeader]],
                     notscenariofiles: Dict[Tuple[str, str], List[str]], dstpath: str,
                     db_repls: Dict[str, List[str]]) -> None:
            threading.Thread.__init__(self)
            self.headers = headers
            self.notscenariofiles = notscenariofiles
            self.dstpath = dstpath
            self.db_repls = db_repls
            self.num = 0
            self.msg = ""
            self.failed = None
            self.updates: Set[str] = set()
            self.paths: List[Union[cw.header.ScenarioHeader, str, cw.dialog.scenarioselect.FindResult]] = []
            self.filepaths: List[str] = []
            self.repl_links: Dict[str, str] = {}

        def run(self) -> None:
            dstpath = cw.util.get_keypath(self.dstpath)
            allret: List[Optional[int]] = [None]
            for (_parent, relparent), headers_seq in self.headers.items():
                self._install(relparent, headers_seq, dstpath, allret)
            for (_parent, relparent), files_seq in self.notscenariofiles.items():
                self._install_files(relparent, files_seq, dstpath, allret)

            if cw.cwpy.setting.delete_sourceafterinstalled:
                # 不要になったインストール元のディレクトリを削除
                for parent, relparent in self.headers.keys():
                    if not (relparent in ("", ".") or relparent.startswith(".." + os.path.sep)):
                        cw.util.remove_emptydir(parent)

        def _confirm_overwrite(self, dlg: cw.dialog.progress.ProgressDialog, s: str,
                               allret: List[Optional[int]]) -> int:
            from . import message

            def func() -> int:
                choices = (
                    ("置換", wx.ID_YES, cw.wins(80)),
                    ("名前変更", wx.ID_DUPLICATE, cw.wins(80)),
                    ("スキップ", wx.ID_NO, cw.wins(80)),
                    ("中止", wx.ID_CANCEL, cw.wins(80)),
                )
                dlg2 = message.Message(dlg, cw.cwpy.msgs["message"], s, mode=3, choices=choices)
                cw.cwpy.frame.move_dlg(dlg2)
                ret = dlg2.ShowModal()
                dlg2.Destroy()
                if wx.GetKeyState(wx.WXK_SHIFT):
                    allret[0] = ret

                return ret

            if allret[0] is None:
                ret = cw.cwpy.frame.sync_exec(func)
            else:
                ret = allret[0]
            return ret

        def _install(self, parent: str, headers_seq: Iterable[cw.header.ScenarioHeader], dstpath: str,
                     allret: List[Optional[int]]) -> None:
            if parent == ".":
                parent = ""
            for header in headers_seq:
                if dlg.cancel:
                    break
                try:
                    self.msg = "「%s」をコピーしています..." % (header.name)
                    fpath = header.get_fpath()
                    repls = self.db_repls.get(fpath, [])
                    rmpaths = []
                    if repls:
                        # DBに登録されている既存のシナリオを置換
                        dst = cw.util.join_paths(os.path.dirname(repls[0]), os.path.basename(fpath))
                        rmpaths = list(repls)
                    else:
                        # 指定箇所にインストール
                        dst = cw.util.join_paths(self.dstpath, parent, os.path.basename(fpath))
                        if dstpath != cw.util.get_keypath(header.dpath):
                            if os.path.exists(dst):
                                s = "%s はすでに存在します。置換しますか？" % (os.path.basename(dst))
                                ret = self._confirm_overwrite(dlg, s, allret)
                                if ret == wx.ID_YES:
                                    rmpaths.append(dst)
                                elif ret == wx.ID_NO:
                                    self.num += 1
                                    continue
                                elif ret == wx.ID_CANCEL:
                                    break
                                else:
                                    dst = cw.util.dupcheck_plus(dst, yado=False)

                    normpath1 = cw.util.get_keypath(fpath)
                    normpath2 = cw.util.get_keypath(dst)
                    dstisfile = os.path.isfile(fpath)

                    if normpath1 != normpath2:
                        update_scenariolog(normpath1, dst, dstisfile)
                        for rmpath in rmpaths:
                            cw.util.remove(rmpath, trashbox=True)
                        dstdir = os.path.dirname(dst)
                        if not os.path.isdir(dstdir):
                            os.makedirs(dstdir)
                        if cw.cwpy.setting.delete_sourceafterinstalled:
                            try:
                                shutil.move(fpath, dst)
                            except Exception:
                                # FIXME: フォルダがロックされていて削除できない場合がある
                                cw.util.print_ex()
                                if os.path.isdir(fpath):
                                    for dpath2, dnames, fnames in os.walk(fpath):
                                        if fnames:
                                            raise
                                    else:
                                        cw.util.remove(fpath, trashbox=True)
                                else:
                                    raise
                        elif os.path.isfile(fpath):
                            shutil.copy2(fpath, dst)
                        else:
                            shutil.copytree(fpath, dst)
                        update_scenariolog2(normpath1, dst, dstisfile)

                    elif repls:
                        for rmpath in repls:
                            cw.util.remove(rmpath, trashbox=True)

                    for path in repls:
                        normpath3 = cw.util.get_keypath(path)
                        update_scenariolog(normpath3, dst, dstisfile)
                        self.repl_links[normpath3] = dst

                    self.updates.add(os.path.dirname(dst))
                    self.repl_links[normpath1] = dst

                    self.paths.append(dst)
                    self.num += 1
                except Exception:
                    cw.util.print_ex(file=sys.stderr)
                    self.failed = header
                    break

        def _install_files(self, parent: str, files_seq: Iterable[str], dstpath: str,
                           allret: List[Optional[int]]) -> None:
            if parent == ".":
                parent = ""
            for fpath in files_seq:
                if dlg.cancel:
                    break
                try:
                    repl_links = {}
                    rmpaths = []
                    self.msg = "ファイル「%s」をコピーしています..." % (os.path.basename(fpath))

                    # ファイルをコピー
                    dst = cw.util.join_paths(self.dstpath, parent, os.path.basename(fpath))
                    normpath1 = cw.util.get_keypath(fpath)
                    normpath2 = cw.util.get_keypath(dst)
                    if normpath1 != normpath2:
                        if os.path.exists(dst):
                            s = "%s はすでに存在します。置換しますか？" % (os.path.basename(dst))
                            ret = self._confirm_overwrite(dlg, s, allret)
                            if ret == wx.ID_YES:
                                rmpaths.append(dst)
                            elif ret == wx.ID_NO:
                                self.num += 1
                                continue
                            elif ret == wx.ID_CANCEL:
                                break
                            else:
                                dst = cw.util.dupcheck_plus(dst, yado=False)

                            if ret == wx.ID_YES:
                                rmpaths.append(dst)
                            elif ret == wx.ID_NO:
                                self.num += 1
                                continue
                            elif ret == wx.ID_CANCEL:
                                break
                            else:
                                dst = cw.util.dupcheck_plus(dst, yado=False)

                    for rmpath in rmpaths:
                        cw.util.remove(rmpath, trashbox=True)
                    dstdir = os.path.dirname(dst)
                    if not os.path.isdir(dstdir):
                        os.makedirs(dstdir)
                    if cw.cwpy.setting.delete_sourceafterinstalled:
                        try:
                            shutil.move(fpath, dst)
                        except Exception:
                            # FIXME: フォルダがロックされていて削除できない場合がある
                            cw.util.print_ex()
                            if os.path.isdir(fpath):
                                for dpath2, dnames, fnames in os.walk(fpath):
                                    if fnames:
                                        raise
                                else:
                                    cw.util.remove(fpath, trashbox=True)
                            else:
                                raise
                    elif os.path.isfile(fpath):
                        shutil.copy2(fpath, dst)
                    else:
                        shutil.copytree(fpath, dst)

                    self.updates.add(os.path.dirname(dst))
                    self.filepaths.append(dst)
                    self.num += 1
                except Exception:
                    cw.util.print_ex(file=sys.stderr)
                    self.failed = header
                    break

    thread = InstallThread(headers, notscenariofiles, dstpath, db_repls)
    thread.start()

    def progress() -> None:
        while thread.is_alive():
            wx.CallAfter(dlg.UpdateProgress, thread.num, thread.msg)
            time.sleep(0.001)
        wx.CallAfter(dlg.Destroy)

    thread2 = threading.Thread(target=progress)
    thread2.start()
    cw.cwpy.frame.move_dlg(dlg)
    dlg.ShowModal()

    if thread.failed:
        s = "「%s」のインストールに失敗しました。" % (thread.failed.name)
        dlg = cw.dialog.message.ErrorMessage(parentdialog, s)
        cw.cwpy.frame.move_dlg(dlg)
        dlg.ShowModal()
        dlg.Destroy()

    # ショートカットの張り替え
    for fpath in links:
        try:
            oldtarget = cw.util.get_linktarget(fpath)
            normpath = cw.util.get_keypath(oldtarget)
            newtarget = thread.repl_links.get(normpath, None)
            if newtarget:
                cw.util.set_linktarget(fpath, newtarget)
        except Exception:
            cw.util.print_ex(file=sys.stderr)

    if not thread.failed and thread.paths:
        for dpath in thread.updates:
            db.update(dpath, skintype=skintype)

    return thread.failed, thread.paths, thread.filepaths, False


def update_scenariolog(normpath: str, dst: str, dstisfile: bool) -> None:
    """
    インストールに伴うシナリオの移動を追跡する。
    """
    normpath2 = cw.util.get_keypath(dst)
    if normpath == normpath2:
        return

    # 最終シナリオ
    normpath2 = cw.util.get_keypath(cw.cwpy.setting.lastscenariopath)
    if normpath == normpath2:
        cw.cwpy.setting.lastscenario = []
        cw.cwpy.setting.lastscenariopath = dst

    for i in range(0, len(cw.cwpy.setting.lastfindresult)):
        normpath3 = cw.util.get_keypath(cw.cwpy.setting.lastfindresult[i])
        if normpath == normpath3:
            cw.cwpy.setting.lastfindresult[i] = dst

    # カード編集ダイアログのブックマーク
    for i, (bookmarkpath, name) in enumerate(cw.cwpy.setting.bookmarks_for_cardedit[:]):
        fname = os.path.basename(bookmarkpath)
        lfname = fname.lower()
        if lfname in ("summary.wsm", "summary.xml"):
            bookmarkpath = os.path.dirname(bookmarkpath)
        normpath2 = cw.util.get_keypath(bookmarkpath)
        if normpath == normpath2:
            cw.cwpy.setting.bookmarks_for_cardedit[i] = ((dst, name))

    if not cw.cwpy.ydata:
        return

    # 宿のブックマーク
    for i, (bookmark, bookmarkpath) in enumerate(cw.cwpy.ydata.bookmarks[:]):
        fname = os.path.basename(bookmarkpath)
        lfname = fname.lower()
        if lfname in ("summary.wsm", "summary.xml"):
            bookmarkpath = os.path.dirname(bookmarkpath)
        normpath2 = cw.util.get_keypath(bookmarkpath)
        if normpath == normpath2:
            cw.cwpy.ydata.changed()
            cw.cwpy.ydata.bookmarks[i] = (([], dst))

    # メッセージログ
    if cw.cwpy.is_playingscenario():
        cw.cwpy.sdata.update_scenariopath(normpath, dst, dstisfile)
    if not dstisfile:
        cw.sprite.message.update_scenariopath_for_log(normpath, dst)

    # パーティのプレイ中情報
    for header in cw.cwpy.ydata.partys:
        dpath = os.path.dirname(header.fpath)
        wsl = cw.util.splitext(header.fpath)[0] + ".wsl"
        wsl = cw.util.get_yadofilepath(wsl)
        if not os.path.isfile(wsl):
            continue

        tempdir = cw.util.join_paths(cw.tempdir, "ScenarioLogTemp")
        dstdir = cw.util.decompress_zip(wsl, tempdir)
        fpath = cw.util.join_paths(dstdir, "ScenarioLog.xml")
        try:
            etree = cw.data.xml2etree(fpath)
            e = etree.find("Property/WsnPath")
            if e is not None:
                normpath2 = cw.util.get_keypath(e.text)
                if normpath2 == normpath:
                    cw.cwpy.ydata.changed()
                    etree.edit("Property/WsnPath", dst)
                    etree.write_file()

                    if wsl.startswith(cw.cwpy.yadodir):
                        wsl = wsl.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
                    cw.util.compress_zip(dstdir, wsl, unicodefilename=True)
        finally:
            cw.util.remove(tempdir)

    # パーティの最終シナリオ
    if cw.cwpy.ydata.party:
        normpath2 = cw.util.get_keypath(cw.cwpy.ydata.party.lastscenariopath)
        if normpath == normpath2:
            cw.cwpy.ydata.party.lastscenario = []
            cw.cwpy.ydata.party.lastscenariopath = dst

    if dstisfile:
        # 圧縮シナリオの展開履歴
        cw.cwpy.ydata.recenthistory.update_scenariopath(normpath, dst)
    elif cw.cwpy.ydata.party:
        # カードイメージ
        for header in cw.cwpy.ydata.party.get_allcardheaders():
            if not header.scenariocard:
                continue
            header.update_scenariopath(normpath, dst)  # 次の表示で再初期化

    cw.fsync.sync()


def update_scenariolog2(normpath: str, dst: str, dstisfile: bool) -> None:
    """
    インストールに伴うシナリオの移動を追跡する。
    移動後の処理。
    """
    if not dstisfile and cw.cwpy.is_playingscenario():
        # 特殊文字の更新
        cw.cwpy.sdata.update_scenariopath2(normpath, dst, dstisfile)

    cw.fsync.sync()


class OverwriteScenarioDialog(wx.Dialog):
    """
    インストールして上書きするシナリオを選択するダイアログ
    """
    def __init__(self, parent: ScenarioInstall, scedir: str,
                 db_exists: Dict[str, List[cw.header.ScenarioHeader]]) -> None:
        wx.Dialog.__init__(self, parent, -1, "シナリオ置換対象の選択",
                           style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.MINIMIZE_BOX,
                           size=cw.wins((500, 400)))
        self.cwpy_debug = False
        self.db_exists = db_exists
        self.scedir = scedir
        self.keys = []
        self.db_repls = {}

        # メッセージ
        if 1 < len(self.db_exists):
            s = "%s本のシナリオがすでにインストール済みです。" % (len(self.db_exists))
        else:
            header2 = list(self.db_exists.values())[0]
            sname = header2[0].name if header2[0].name else "(無名のシナリオ)"
            if header2[0].author:
                sname += "(%s)" % header2[0].author
            s = "インストール済みの「%s」がシナリオデータベース上に見つかりました。" % (sname)
        s += "以前インストールしたシナリオを置換する場合は、置換対象をチェックしてください。"
        if any([1 < len(headers) for headers in iter(db_exists.values())]):
            s += "\n同一のシナリオを複数チェックした場合は、最初の1件が置換され、残りは削除されます。"
        self.text = s

        font = cw.cwpy.rsrc.get_wxfont("combo", pixelsize=cw.wins(14))
        self.datalist = cw.util.CheckableListCtrl(self, -1, size=cw.wins((400, 400)),
                                                  style=wx.LC_REPORT | wx.VSCROLL | wx.HSCROLL,
                                                  system=False)
        self.datalist.SetFont(font)

        index2 = 0
        for fpath in sorted(self.db_exists.keys()):
            self.keys.append(fpath)
            headers = self.db_exists[fpath]
            for index, header in enumerate(headers):
                sname = header.name if header.name else "(無名のシナリオ)"
                if header.author:
                    sname += "(%s)" % header.author
                fpath = header.get_fpath()
                rel = cw.util.relpath(fpath, os.path.abspath("."))
                if cw.util.join_paths(rel).startswith("../"):
                    rel = header.get_fpath()
                self.datalist.InsertItem(index2, "%s - %s" % (sname, cw.util.join_paths(rel)))
                self.datalist.CheckItem(index2, (index == 0))
                index2 += 1

        self.okbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_OK, cw.wins((100, 30)), cw.cwpy.msgs["decide"])
        self.cnclbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, cw.wins((100, 30)), cw.cwpy.msgs["cancel"])

        # layout
        self._resize()
        self._do_layout()
        # bind
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.okbtn)
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        for child in self.GetChildren():
            child.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnResize)

    def OnResize(self, event: wx.SizeEvent) -> None:
        if not self.datalist.IsShown():
            return

        self._resize()

        self._do_layout()
        self.Refresh()

    def _resize(self) -> None:
        """
        テキストの折り返し位置を計算する。
        """
        dc = wx.ClientDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        csize = self.GetClientSize()
        self._wrapped_text = cw.util.wordwrap(self.text, csize[0]-cw.wins(20), lambda s: dc.GetTextExtent(s)[0])
        _w, self._textheight, _lineheight = dc.GetFullMultiLineTextExtent(self._wrapped_text)

    def OnOk(self, event: wx.CommandEvent) -> None:
        cw.cwpy.play_sound("click")
        self.db_repls = {}
        index = 0
        for fpath in self.keys:
            headers = self.db_exists[fpath]
            repls = []
            for header in headers:
                checked = self.datalist.IsItemChecked(index)
                if checked:
                    repls.append(header.get_fpath())
                index += 1
            if repls:
                self.db_repls[fpath] = repls
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event: wx.CommandEvent) -> None:
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnPaint(self, evt: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self)
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        csize = self.GetClientSize()
        cw.util.fill_bitmap(dc, bmp, csize)
        # massage
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        dc.DrawLabel(self._wrapped_text, (cw.wins(10), cw.wins(12), csize[0], self._textheight), wx.ALIGN_LEFT)

    def _do_layout(self) -> None:
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add((cw.wins(0), self._textheight + cw.wins(24)), 0, 0, 0)
        csize = self.GetClientSize()

        if self.datalist.GetContainingSizer():
            self.datalist.GetContainingSizer().Detach(self.datalist)
        sizer_1.Add(self.datalist, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, cw.wins(8))

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.AddStretchSpacer(1)
        for i, button in enumerate((self.okbtn, self.cnclbtn)):
            if button.GetContainingSizer():
                button.GetContainingSizer().Detach(button)
            sizer_2.Add(button, 0, 0, 0)
            sizer_2.AddStretchSpacer(1)

        sizer_1.Add(sizer_2, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, cw.wins(12))

        self.SetSizer(sizer_1)
        self.Layout()


def create_installdesc(headers_seq: List[cw.header.ScenarioHeader]) -> str:
    if 1 < len(headers_seq):
        name = "%s本のシナリオ" % (len(headers_seq))
    else:
        name = headers_seq[0].name if headers_seq[0].name else "(無名のシナリオ)"
        if headers_seq[0].author:
            name += "(%s)" % headers_seq[0].author
        name = "「%s」" % name
    if cw.cwpy.setting.delete_sourceafterinstalled:
        desc = "%sをコピーし、シナリオデータベースに登録します。\n" % (name) + \
               "インストール完了後のファイルを削除したい場合は、詳細設定の" + \
               "[シナリオ] > [詳細] > [シナリオのインストールに成功したら元ファイルを削除する]で" + \
               "設定を変更します。"
    else:
        desc = "%sを移動し、シナリオデータベースに登録します。\n" % (name) + \
               "インストール完了後のファイルを削除したくない場合は、詳細設定の" + \
               "[シナリオ] > [詳細] > [シナリオのインストールに成功したら元ファイルを削除する]で" + \
               "設定を変更します。"
    return desc


def main() -> None:
    pass


if __name__ == "__main__":
    main()
