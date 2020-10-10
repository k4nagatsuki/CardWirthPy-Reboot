#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from . import cwfile
from . import cwscenario
from . import cwyado
from . import xmltemplate
from . import image
from . import util
from . import event
from . import bgimage
from . import coupon
from . import summary
from . import environment

from typing import Union


class ConvertingThread(threading.Thread):
    def __init__(self, cwdata: Union[cwyado.CWYado, cwyado.UnconvCWYado, cwscenario.CWScenario]) -> None:
        threading.Thread.__init__(self)
        self.cwdata = cwdata
        self.path = ""
        self.complete = False

    def run(self) -> None:
        self.path = self.cwdata.convert()
        self.complete = True


def main() -> None:
    pass


if __name__ == "__main__":
    main()
