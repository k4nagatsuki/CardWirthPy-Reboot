#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import base

import cw

from typing import Optional


class Dialog(base.CWBinaryBase):
    """台詞データ"""
    from . import content

    def __init__(self, parent: content.Content, f: cw.binary.cwfile.CWFile, yadodata: bool = False) -> None:
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.coupons = f.string(True)
        self.text = f.string(True)

        self.data: Optional[cw.data.CWPyElement] = None

    def get_data(self) -> cw.data.CWPyElement:
        if self.data is None:
            self.data = cw.data.make_element("Dialog")
            e = cw.data.make_element("RequiredCoupons", self.coupons)
            self.data.append(e)
            e = cw.data.make_element("Text", self.text)
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f: cw.binary.cwfile.CWFileWriter, data: cw.data.CWPyElement) -> None:
        coupons = ""
        text = ""

        for e in data:
            if e.tag == "RequiredCoupons":
                coupons = e.text
            elif e.tag == "Text":
                text = e.text

        f.write_string(coupons, True)
        f.write_string(text, True)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
