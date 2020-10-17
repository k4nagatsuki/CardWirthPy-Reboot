#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from . import base

import cw

from typing import Optional, Union

_120gene = re.compile(r"\A＠Ｇ[01]{10}-[0-9]+\Z")


class Coupon(base.CWBinaryBase):
    """クーポンデータ。"""
    from . import adventurer
    from . import album
    from . import cast
    from . import content

    def __init__(self, parent: Union[album.Album, adventurer.Adventurer, cast.CastCard, content.Content],
                 f: "cw.binary.cwfile.CWFile", yadodata: bool = False, dataversion: int = 5) -> None:
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        if f:
            self.name = f.string()
            self.value = f.dword()
            if dataversion <= 4:
                if _120gene.match(self.name):
                    self.value = int(self.name[13:])
                    self.name = self.name[:12]
        else:
            self.name = ""
            self.value = 0

        self.data: Optional[cw.data.CWPyElement] = None

    def get_data(self) -> "cw.data.CWPyElement":
        if self.data is None:
            self.data = cw.data.make_element("Coupon", self.name)
            self.data.set("value", str(self.value))
        return self.data

    @staticmethod
    def unconv(f: "cw.binary.cwfile.CWFileWriter", data: "cw.data.CWPyElement") -> None:
        name = data.text
        value = int(data.get("value"))

        f.write_string(name)
        f.write_dword(value)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
