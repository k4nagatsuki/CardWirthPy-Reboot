#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw

import typing
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


# ------------------------------------------------------------------------------
# メッセージダイアログ
# ------------------------------------------------------------------------------

class Message(wx.Dialog):
    """
    メッセージダイアログ。
    mode=1は「はい」「いいえ」。mode=2は「閉じる」。
    mode=3は、choicesに(テキスト, ID, 幅)のtupleまたはlistを指定する事で任意の選択肢を表示する。
    """
    buttons: Sequence[Union[wx.BitmapButton, wx.Button]]

    def __init__(self, parent: wx.TopLevelWindow, name: str, text: str, mode: int = 2,
                 choices: Optional[Iterable[Union[Tuple[str, int, int, str],
                                                  Tuple[str, int, int],
                                                  Tuple[str, int]]]] = None) -> None:
        wx.Dialog.__init__(self, parent, -1, name, size=cw.wins((355, 120)),
                           style=wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.MINIMIZE_BOX)
        self.cwpy_debug = False
        self.basetext = text
        self.text = cw.util.wordwrap(text, 50)
        self.mode = mode

        dc = wx.ClientDC(self)
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        w, h, _lineheight = dc.GetFullMultiLineTextExtent(self.text)
        self._textheight = h
        dw = cw.wins(349)
        dh = cw.wins(68)
        dw = max(dw, w + cw.wins(10)*2)
        dh = max(dh, h + cw.wins(68))

        self.SetClientSize((dw, dh))

        if self.mode == 1:
            # yes and no
            self.yesbtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_OK, cw.wins((120, 30)), cw.cwpy.msgs["yes"])
            self.nobtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, cw.wins((120, 30)), cw.cwpy.msgs["no"])
            self.buttons = (self.yesbtn, self.nobtn)
        elif self.mode == 2:
            # close
            self.closebtn = cw.cwpy.rsrc.create_wxbutton(self, wx.ID_CANCEL, cw.wins((120, 30)), cw.cwpy.msgs["close"])
            self.buttons = (self.closebtn,)
        elif self.mode == 3:
            # 任意
            self.buttons = []
            assert choices is not None
            for d in choices:
                if len(d) == 4:
                    # BUG: Need more than 3 values to unpack (4 expected) (mypy 0.782)
                    s, sid, width, desc = typing.cast(Tuple[str, int, int, str], d)
                elif len(d) == 3:
                    # BUG: Too many values to unpack (3 expected, 4 provided) (mypy 0.782)
                    s, sid, width = typing.cast(Tuple[str, int, int], d)
                    desc = ""
                else:
                    # BUG: Too many values to unpack (2 expected, 4 provided) (mypy 0.782)
                    s, sid = typing.cast(Tuple[str, int], d)
                    desc = ""
                    width = -1

                button = cw.cwpy.rsrc.create_wxbutton(self, sid, (width, cw.wins(30)), s)
                if desc:
                    button.SetToolTip(desc)
                self.buttons.append(button)
                button.Bind(wx.EVT_BUTTON, self.OnButton)
        else:
            assert False

        # layout
        self._do_layout()
        # bind
        self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        for child in self.GetChildren():
            child.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        copyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnCopyDetail, id=copyid)
        seq = [
            (wx.ACCEL_CTRL, ord('C'), copyid),
        ]
        cw.util.set_acceleratortable(self, seq)

    def OnCopyDetail(self, event: wx.CommandEvent) -> None:
        self.copy_detail()

    def copy_detail(self) -> None:
        cw.cwpy.play_sound("equipment")
        s = ["[Window Title]", self.GetTitle(), "", "[Content]", self.basetext, ""]
        b = []
        for button in self.buttons:
            b.append("[%s]" % button.GetLabelText())
        s.append(" ".join(b))
        cw.util.to_clipboard("\n".join(s))

    def OnCancel(self, event: wx.CommandEvent) -> None:
        cw.cwpy.play_sound("click")
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnButton(self, event: wx.CommandEvent) -> None:
        button = event.GetEventObject()
        self.Close()
        self.SetReturnCode(button.GetId())
        event.Skip()

    def OnPaint(self, evt: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self)
        csize = self.GetClientSize()
        # background
        bmp = cw.cwpy.rsrc.dialogs["CAUTION"]
        # エラー表示にも使用するため、"CAUTION"が存在しない場合も確実に表示する必要がある
        # そのため空ビットマップが返ってくる可能性を考慮しておく
        if 1 < bmp.GetWidth() and 1 < bmp.GetHeight():
            cw.util.fill_bitmap(dc, bmp, csize)
            dc.SetTextForeground(wx.BLACK)
        # massage
        dc.SetFont(cw.cwpy.rsrc.get_wxfont("dlgmsg", pixelsize=cw.wins(15)))
        dc.DrawLabel(self.text, (0, cw.wins(12), csize[0], self._textheight), wx.ALIGN_CENTER)

    def _do_layout(self) -> None:
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add((cw.wins(0), self._textheight + cw.wins(24)), 0, 0, 0)
        csize = self.GetClientSize()

        if self.mode == 1:
            sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
            margin = (csize[0] - self.yesbtn.GetSize()[0] * 2) // 3
            sizer_2.Add(self.yesbtn, 0, wx.LEFT, margin)
            sizer_2.Add(self.nobtn, 0, wx.LEFT | wx.RIGHT, margin)
        elif self.mode == 2:
            sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
            margin = (csize[0] - self.closebtn.GetSize()[0]) // 2
            sizer_2.Add(self.closebtn, 0, wx.LEFT, margin)
        elif self.mode == 3:
            sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
            sizer_2.AddStretchSpacer(1)
            for i, button in enumerate(self.buttons):
                sizer_2.Add(button, 0, 0, 0)
                sizer_2.AddStretchSpacer(1)

        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)

        self.SetSizer(sizer_1)
        self.Layout()


class YesNoMessage(Message):
    def __init__(self, parent: wx.TopLevelWindow, name: str, text: str) -> None:
        Message.__init__(self, parent, name, text, 1)


class YesNoCancelMessage(Message):
    def __init__(self, parent: wx.TopLevelWindow, name: str, text: str) -> None:
        choices = (
            ("はい", wx.ID_YES, cw.wins(105)),
            ("いいえ", wx.ID_NO, cw.wins(105)),
            ("キャンセル", wx.ID_CANCEL, cw.wins(105)),
        )
        Message.__init__(self, parent, name, text, 3, choices=choices)


class ErrorMessage(Message):
    def __init__(self, parent: wx.TopLevelWindow, text: str) -> None:
        cw.cwpy.play_sound("error")
        Message.__init__(self, parent, cw.cwpy.msgs["error_message"], text, 2)


class SysMessage(wx.Dialog):
    """
    システム的な外見のメッセージダイアログ。
    choicesに(テキスト, ID, 幅)のtupleまたはlistを指定する事で任意の選択肢を表示する。
    checkboxesに(キー, テキスト, 初期値)のtupleまたはistを指定する事で追加オプションのチェックボックスを表示する。
    """
    def __init__(self, parent: wx.TopLevelWindow, name: str, text: str,
                 choices: Optional[Iterable[Union[Tuple[str, int, int, str],
                                                  Tuple[str, int, int],
                                                  Tuple[str, int]]]] = None,
                 checkboxes: Optional[Iterable[Tuple[str, str, bool]]] = None) -> None:
        if choices:
            style = wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.MINIMIZE_BOX
        else:
            style = wx.SYSTEM_MENU
        wx.Dialog.__init__(self, parent, -1, name, size=cw.ppis((355, 120)), style=style)
        self.cwpy_debug = True
        self.basetext = text
        dc = wx.ClientDC(self)
        text = cw.util.wordwrap(text, cw.ppis(345), lambda s: dc.GetTextExtent(s)[0])
        self._st_text = wx.StaticText(self, -1, text)

        self._check_table: Dict[str, bool] = {}
        self._checkboxes: List[Tuple[str, wx.CheckBox]] = []
        if checkboxes:
            for key, text, value in checkboxes:
                def func(key: str) -> None:
                    self._check_table[key] = value
                    checkbox = wx.CheckBox(self, -1, text)
                    checkbox.SetValue(value)
                    self._checkboxes.append((key, checkbox))

                    def OnCheck(event: wx.CommandEvent) -> None:
                        self._check_table[key] = checkbox.GetValue()
                    checkbox.Bind(wx.EVT_CHECKBOX, OnCheck)

                func(key)

        self._stl = wx.StaticLine(self, -1)
        self.buttons = []
        if choices:
            for d in choices:
                if len(d) == 4:
                    # BUG: Need more than 3 values to unpack (4 expected) (mypy 0.782)
                    s, sid, width, desc = typing.cast(Tuple[str, int, int, str], d)
                elif len(d) == 3:
                    # BUG: Too many values to unpack (3 expected, 4 provided) (mypy 0.782)
                    s, sid, width = typing.cast(Tuple[str, int, int], d)
                    desc = ""
                else:
                    # BUG: Too many values to unpack (2 expected, 4 provided) (mypy 0.782)
                    s, sid = typing.cast(Tuple[str, int], d)
                    desc = ""
                    width = -1

                button = wx.Button(self, sid, s, size=(width, -1))
                if desc:
                    button.SetToolTip(desc)
                self.buttons.append(button)
                button.Bind(wx.EVT_BUTTON, self.OnButton)

            # bind
            self.Bind(wx.EVT_RIGHT_UP, self.OnCancel)
            for child in self.GetChildren():
                child.Bind(wx.EVT_RIGHT_UP, self.OnCancel)

        # layout
        self._do_layout()

        copyid = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnCopyDetail, id=copyid)
        seq = [
            (wx.ACCEL_CTRL, ord('C'), copyid),
        ]
        cw.util.set_acceleratortable(self, seq)

    def get_check(self, key: str) -> bool:
        return self._check_table[key]

    def OnCopyDetail(self, event: wx.CommandEvent) -> None:
        self.copy_detail()

    def copy_detail(self) -> None:
        s = ["[Window Title]", self.GetTitle(), "", "[Content]", self.basetext]
        if self.buttons:
            b = []
            for button in self.buttons:
                b.append("[%s]" % button.GetLabelText())
            s.append("")
            s.append(" ".join(b))
        cw.util.to_clipboard("\n".join(s))

    def OnCancel(self, event: wx.CommandEvent) -> None:
        btnevent = wx.PyCommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_CANCEL)
        self.ProcessEvent(btnevent)

    def OnButton(self, event: wx.CommandEvent) -> None:
        button = event.GetEventObject()
        self.Close()
        self.SetReturnCode(button.GetId())
        event.Skip()

    def _do_layout(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self._st_text, 0, wx.ALL, cw.ppis(10))

        if self._checkboxes:
            sizer_chk = wx.BoxSizer(wx.VERTICAL)
            for i, (_key, checkbox) in enumerate(self._checkboxes):
                if i == 0:
                    sizer_chk.Add(checkbox, 0, 0, 0)
                else:
                    sizer_chk.Add(checkbox, 0, wx.TOP, cw.ppis(2))
            sizer.Add(sizer_chk, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, cw.ppis(10))

        if self.buttons:
            sizer.Add(self._stl, 0, wx.EXPAND, 0)
            sizer_btn = wx.BoxSizer(wx.HORIZONTAL)
            for i, button in enumerate(self.buttons):
                if i == 0:
                    sizer_btn.Add(button, 0, 0, 0)
                else:
                    sizer_btn.Add(button, 0, wx.LEFT, cw.ppis(10))

            sizer.Add(sizer_btn, 0, wx.ALL | wx.ALIGN_RIGHT, cw.ppis(10))

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
