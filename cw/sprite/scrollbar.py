#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
import base


class ScrollBar(base.CWPySprite):

    def __init__(self, scrpos_noscale, scrsize_noscale, visible):
        base.CWPySprite.__init__(self)
        self.visible = visible
        self.width = 0
        self._skipcount = 0

        self.lazypos_noscale = None
        self.lazyscroll_func = None

        self.scrsize_noscale = scrsize_noscale
        self.scrpos_noscale = scrpos_noscale

        self.update_scale()

    def scroll_to_mousepos(self, lazy):
        """左クリックイベント。"""
        y = cw.cwpy.mousepos[1]/cw.UP_SCR

        l = float(self.scrsize_noscale) / cw.SIZE_AREA[1]
        y *= l
        y -= cw.SIZE_AREA[1]/2.0
        y = int(y)
        if lazy:
            self.lazypos_noscale = y
            if self.status <> "lazyscroll":
                self._skipcount = 0
                cw.animation.start_animation(self, "lazyscroll")
        elif self.status == "lazyscroll":
            self.lazypos_noscale = y
        else:
            self.lazypos_noscale = None
            self.set_pos(y, lazy=False)

    def update_scale(self):
        self.width = cw.s(8)
        self.image = pygame.Surface((self.width, cw.s(cw.SIZE_AREA[1]))).convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(cw.SIZE_AREA[0])-self.width, cw.s(0)
        self.image.fill((0, 0, 0, 0), rect=pygame.Rect(0, 0, self.rect.width, self.rect.height))
        self.set_params(self.scrpos_noscale, self.scrsize_noscale)

    def update_lazyscroll(self):
        scrframe = 10

        if self.lazypos_noscale is None:
            return

        if scrframe <= self.frame:
            self.status = self.old_status
            self.frame = 0
            self.set_pos(self.lazypos_noscale, lazy=False)
            self.lazypos_noscale = None
            if self.lazyscroll_func:
                self.lazyscroll_func()
            return

        self._skipcount += 1
        if 0 < self._skipcount:
            self._skipcount = 0
            pos = int(self.scrpos_noscale - (self.scrpos_noscale-self.lazypos_noscale)/float(scrframe-self.frame))
            if pos <> self.scrpos_noscale:
                self.set_params(pos, self.scrsize_noscale)
                if self.lazyscroll_func:
                    self.lazyscroll_func()

    def set_pos(self, scrpos_noscale, lazy):
        if lazy:
            self.lazypos_noscale = scrpos_noscale
            if self.status <> "lazyscroll":
                self._skipcount = 0
                cw.animation.start_animation(self, "lazyscroll")
        else:
            self.lazypos_noscale = None
            self.set_params(scrpos_noscale, self.scrsize_noscale)

    def get_pos(self):
        if self.lazypos_noscale is None:
            return self.scrpos_noscale
        else:
            return self.lazypos_noscale

    def set_params(self, scrpos_noscale, scrsize_noscale):
        minsize = cw.s(4)
        hwidth = self.width-cw.s(8)
        self.scrsize_noscale = max(cw.SIZE_AREA[1], scrsize_noscale)
        self.scrpos_noscale = min(self.scrsize_noscale-cw.SIZE_AREA[1], max(0, scrpos_noscale))
        if not self.visible:
            return

        l = float(cw.SIZE_AREA[1]) / self.scrsize_noscale
        scrpos = cw.s(self.scrpos_noscale) * l
        scrsize = min(cw.s(self.scrsize_noscale), self.rect.height) * l
        if scrsize < minsize:
            posper = scrpos / float(self.rect.height-scrsize)
            scrsize = minsize
            sizen = cw.s(cw.SIZE_AREA[1]) - scrsize
            scrpos = sizen * posper

        scrpos = int(round(scrpos))
        scrsize = int(round(scrsize))

        self.image.fill((0, 0, 0, 128), rect=pygame.Rect(hwidth, 0, self.width-hwidth, self.rect.height))
        if 0 < scrsize:
            rect = pygame.Rect(hwidth, scrpos, self.width-hwidth, scrsize)
            self.image.fill((255, 255, 255, 224), rect)
