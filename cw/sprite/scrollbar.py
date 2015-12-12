#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
import base


class ScrollBar(base.CWPySprite):

    def __init__(self, scrpos_noscale, thumb_noscale):
        base.CWPySprite.__init__(self)

        self.scrpos_noscale = scrpos_noscale
        self.thumb_noscale = thumb_noscale

        self.image = pygame.Surface(cw.s((0, 0))).convert()
        self.rect = pygame.Rect(0, 0, 0, 0)

    def update_scale(self):
        width = cw.s(8)
        self.image = pygame.Surface((width, cw.s(cw.SIZE_AREA[1]))).convert_alpha()
        self.image.fill((0, 0, 0, 128))
        self.rect = self.image.get_rect()
        self.rect.topleft = cw.s(cw.SIZE_AREA[0])-width, cw.s(0)
        self.set_params(self.scrpos_noscale, self.thumb_noscale)

    def set_params(self, scrpos_noscale, thumb_noscale):
        self.scrpos_noscale = scrpos_noscale
        self.thumb_noscale = thumb_noscale
        if 0 < self.thumb_noscale:
            rect = pygame.Rect(cw.s(0), cw.s(self.scrpos_noscale), self.rect.width, cw.s(self.thumb_noscale))
            self.image.fill((255, 255, 255, 224), rect)
        else:
            self.clear_image()

    def clear_image(self):
        if 0 < self.rect.width:
            return
        rect = self.rect
        self.image = pygame.Surface(cw.s((0, 0))).convert()
        self.rect = pygame.Rect(0, 0, 0, 0)
        cw.cwpy.draw(clip=rect)
