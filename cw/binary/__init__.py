#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

import cwscenario
import cwyado
import xmltemplate
import image
import util


class ConvertingThread(threading.Thread):
    def __init__(self, cwdata):
        threading.Thread.__init__(self)
        self.cwdata = cwdata
        self.path = ""
        self.complete = False

    def run(self):
        self.path = self.cwdata.convert()
        self.complete = True

def main():
    pass

if __name__ == "__main__":
    main()
