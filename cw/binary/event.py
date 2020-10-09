#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import base

import cw

from typing import Optional, Sequence, Union


class Event(base.CWBinaryBase):
    """イベント発火条件付のイベントデータのクラス。"""
    from . import area
    from . import battle

    def __init__(self, parent: Union[area.Area, area.MenuCard, battle.Battle, battle.EnemyCard],
                 f: "cw.binary.cwfile.CWFile", yadodata: bool = False) -> None:
        from . import content

        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        contents_num = f.dword()
        self.contents = [content.Content(self, f, 0)
                         for _cnt in range(contents_num)]
        ignitions_num = f.dword()
        self.ignitions = [f.dword() for _cnt in range(ignitions_num)]
        self.keycodes = f.string(True)

        self.data: Optional[cw.data.CWPyElement] = None

    def get_data(self) -> "cw.data.CWPyElement":
        if self.data is None:
            self.data = cw.data.make_element("Event")
            e = cw.data.make_element("Ignitions")
            number = cw.util.encodetextlist([str(i) for i in self.ignitions]) if self.ignitions else ""
            e.append(cw.data.make_element("Number", number))
            keycodes = cw.util.decodetextlist(self.keycodes)
            if keycodes and keycodes[0] == "MatchingType=All":
                # 1.50
                matching = "And"
                keycodes = keycodes[1:]
            else:
                matching = "Or"
            e.set("keyCodeMatchingType", matching)
            e.append(cw.data.make_element("KeyCodes", cw.util.encodetextlist(keycodes)))
            self.data.append(e)
            e = cw.data.make_element("Contents")
            for content in self.contents:
                e.append(content.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f: "cw.binary.cwfile.CWFileWriter", data: "cw.data.CWPyElement") -> None:
        contents: Sequence[cw.data.CWPyElement] = []
        ignitions: List[int] = []
        keycodes = ""

        for e in data:
            if e.tag == "Ignitions":
                matching = e.get("keyCodeMatchingType", "Or")
                for ig in e:
                    if ig.tag == "Number":
                        for num in cw.util.decodetextlist(ig.text):
                            ignitionnum = int(num)
                            if ignitionnum == 4:
                                f.check_version(1.50, "毎ラウンド発火条件")
                            elif ignitionnum == 5:
                                f.check_version(1.50, "バトル開始発火条件")
                            elif ignitionnum == 6:
                                f.check_wsnversion("4", "ラウンド終了発火条件")
                            ignitions.append(ignitionnum)
                    elif ig.tag == "KeyCodes":
                        if matching == "And":
                            f.check_version(1.50, "キーコード全てに一致で発火")
                            array = ["MatchingType=All"]
                            array.extend(cw.util.decodetextlist(ig.text))
                            keycodes = cw.util.encodetextlist(array)
                        else:
                            keycodes = ig.text
            elif e.tag == "Contents":
                contents = e

        f.write_dword(len(contents))
        for content in contents:
            content.Content.unconv(f, content)
        f.write_dword(len(ignitions))
        for ignition in ignitions:
            f.write_dword(ignition)
        f.write_string(keycodes, True)


class SimpleEvent(base.CWBinaryBase):
    """イベント発火条件なしのイベントデータのクラス。
    カードイベント・パッケージ等で使う。
    """
    from . import package
    from . import skill
    from . import item
    from . import beast

    def __init__(self, parent: Union[package.Package, skill.SkillCard, item.ItemCard, beast.BeastCard],
                 f: "cw.binary.cwfile.CWFile", yadodata: bool = False) -> None:
        from . import content

        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        contents_num = f.dword()
        self.contents = [content.Content(self, f, 0)
                         for _cnt in range(contents_num)]

        self.data = None

    def get_data(self) -> "cw.data.CWPyElement":
        if self.data is None:
            self.data = cw.data.make_element("Event")
            e = cw.data.make_element("Contents")
            for content in self.contents:
                e.append(content.get_data())
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f: "cw.binary.cwfile.CWFileWriter", data: "cw.data.CWPyElement") -> None:
        from . import content

        contents = []

        for e in data:
            if e.tag == "Contents":
                contents = e

        f.write_dword(len(contents))
        for ct in contents:
            content.Content.unconv(f, ct)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
