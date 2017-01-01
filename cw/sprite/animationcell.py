#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import pygame
import pygame.locals

import cw
import base


class AnimationCell(base.SelectableSprite):
    def __init__(self, path, size_noscale, pos_noscale, spritegrp, layer):
        """
        XMLの定義によってアニメーションを表示するセル。
        """
        base.SelectableSprite.__init__(self)
        self.selectable_on_event = True
        self.status = "normal"
        data = cw.data.xml2element(path)

        self.animation_table = {}
        self.refs = []
        self.cache = {}

        self.size_noscale = size_noscale
        self.pos_noscale = pos_noscale

        # アニメーションパーツのグループ
        self.animations = _AnimationPart(self, data, 0)
        # アニメーションの終端時間
        self.end_frame = 0
        for anime in self._iter_animes(self.animations):
            self.end_frame = max(anime.startframe + anime.spawn + anime.duration, self.end_frame)

        self.update_scale()

        spritegrp.add(self, layer=layer)

    def _iter_animes(self, anime):
        """
        グループ内のものを含めた全ての_AnimationPartを返す。
        """
        if anime.type == "Group":
            for sub in anime.parts:
                for a in self._iter_animes(sub):
                    yield a
        else:
            yield anime

    def update_scale(self):
        for anime in self._iter_animes(self.animations):
            anime.load_cell()

        # 他セルの位置とサイズを参照するものは全て読み込んだ後にここで再計算する
        for anime in self.refs:
            if not isinstance(anime.pos_noscale[0], int):
                a = anime.pos_noscale[0][len("Ref:"):]
                anime.pos_noscale = (self.animation_table[a].pos_noscale[0], anime.pos_noscale[1])
            if not isinstance(anime.pos_noscale[1], int):
                a = anime.pos_noscale[1][len("Ref:"):]
                anime.pos_noscale = (anime.pos_noscale[0], self.animation_table[a].pos_noscale[1])
            if not isinstance(anime.size_noscale[0], int):
                a = anime.size_noscale[0][len("Ref:"):]
                anime.size_noscale = (self.animation_table[a].size_noscale[0], anime.size_noscale[1])
            if not isinstance(anime.size_noscale[1], int):
                a = anime.size_noscale[1][len("Ref:"):]
                anime.size_noscale = (anime.size_noscale[0], self.animation_table[a].size_noscale[1])

        del self.refs[:]

        self.rect = pygame.Rect(cw.s(self.pos_noscale), cw.s(self.size_noscale))
        self.image = pygame.Surface(self.rect.size).convert()
        for anime in self._iter_animes(self.animations):
            anime.update_scale()

    def quit(self):
        """アニメーションを終了する。"""
        self.status = "normal"
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.frame = 0

    def update(self, scr):
        if cw.cwpy.selection <> self:
            # 他の選択がなされていない場合は常にAnimationCellを選択状態にする
            self.update_selection()
        if not cw.cwpy.selection:
            cw.cwpy.change_selection(self)
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        if cw.cwpy.selection <> self:
            # 他の選択がなされていない場合は常にAnimationCellを選択状態にする
            self.update_selection()
        if not cw.cwpy.selection:
            cw.cwpy.change_selection(self)

    def lclick_event(self):
        """
        左クリックイベント。
        アニメーションを飛ばす。
        """
        cw.cwpy.cut_animation = True

    def rclick_event(self):
        """
        右クリックイベント。
        アニメーションを飛ばす。
        """
        cw.cwpy.cut_animation = True

    def update_animation(self):
        if self.end_frame <= self.frame or self.skipped or cw.cwpy.cut_animation:
            self.quit()
            return

        self.image.fill((0, 0, 0))
        for anime in self._iter_animes(self.animations):
            anime.update_image()
            if anime.image and 0 < anime.rect[2] and 0 < anime.rect[3]:
                self.image.blit(anime.image, anime.rect)

        self.frame = self.get_frame()
        if self.end_frame <= self.frame or self.skipped or cw.cwpy.cut_animation:
            self.quit()

class _AnimationPart(object):
    def __init__(self, parent, data, startframe):
        """
        複合アニメーションのパーツ。
        個々のパーツか、並列・直列に実行するグループを表す。
        """
        self.parent = parent
        self.startframe = startframe
        if data.tag == "Animations":
            # グループ
            self.type = "Group"
            self.parallel = data.getattr(".", "parallel", False) # 並列に実行するか
            self.parts = []
            startframe = self.startframe
            for a in data.find("."):
                anime = _AnimationPart(parent, a, startframe)
                self.parts.append(anime)
                if not self.parallel:
                    startframe += anime.spawn + anime.duration

        elif data.tag == "Animation":
            # アニメーションするパーツ
            self.type = "Part"
            self.id = data.getattr(".", "id", "")
            if self.id:
                self.parent.animation_table[self.id] = self

            self.imgpath = data.gettext("ImagePath", "")
            if self.imgpath:
                self.imgpath = cw.util.join_paths(cw.cwpy.skindir, self.imgpath)
                self.imgpath = cw.util.get_materialpathfromskin(self.imgpath, cw.M_IMG)
            left = data.getattr("Location", "left", "0")
            top = data.getattr("Location", "top", "0")
            width = data.getattr("Size", "width", "Original")
            height = data.getattr("Size", "height", "Original")

            self._rect_str = (left, top, width, height)
            self._fill_color = data.getint("Fill", "r", 0), data.getint("Fill", "g", 0), data.getint("Fill", "b", 0)
            self.mask = data.getbool("Mask", False)

            self.animation_type = data.gettext("AnimationType", "None") # アニメーションのタイプ
            self.animation_frame = data.getint("AnimationType", "frame", 20) # アニメーションにかかる時間
            self.repeat_count = data.getint("Repeat", 1) # 繰り返し回数
            self.repeat_interval = data.getint("Repeat", "interval", 0) # 繰り返しのインターバル
            self.spawn = data.getint("Spawn", 0) # 出現時間
            self.duration = data.getint("Duration", 20) # 存在期間

            if self.animation_type == "Rotate":
                self.dealing_scales = map(lambda i: int(math.sin(math.radians(180.0 * i / self.animation_frame)) * 100),
                                          xrange(self.animation_frame))

            self.image = pygame.Surface((0, 0)).convert()
            self.rect = pygame.Rect(0, 0, 0, 0)

        else:
            raise Exception("Invalid animation: %s" % (data.tag))

    def load_cell(self):
        left, top, width, height = self._rect_str

        if self.imgpath:
            # 画像ファイル
            key = (os.path.normcase(os.path.normpath(os.path.abspath(self.imgpath))), cw.UP_SCR)
            self.image_noscale = self.parent.cache.get(key, None)
            if not self.image_noscale:
                self.image_noscale = cw.util.load_image(self.imgpath, self.mask, can_loaded_scaledimage=True)
                self.parent.cache[key] = self.image_noscale
            self.fill_color = None
            scr_scale = self.image_noscale.scr_scale if hasattr(self.image_noscale, "scr_scale") else 1
            if width == "Original":
                width = self.image_noscale.get_width() if self.image_noscale.get_width() else self.parent.size_noscale[0]
                width //= scr_scale
            if height == "Original":
                height = self.image_noscale.get_height() if self.image_noscale.get_height() else \
                self.parent.size_noscale[1]
                height //= scr_scale

        else:
            # 塗り潰し
            self.image_noscale = pygame.Surface((4, 4)).convert()
            self.image_noscale.fill(self._fill_color)
            self.mask = False
            if width == "Original":
                width = self.parent.size_noscale[0]
            if height == "Original":
                height = self.parent.size_noscale[1]

        self._has_alpha = (self.image_noscale.get_flags() & pygame.locals.SRCALPHA) <> 0

        if width == "Max":
            width = self.parent.size_noscale[0]
        if height == "Max":
            height = self.parent.size_noscale[1]

        if left == "Center":
            left = (self.parent.size_noscale[0] - width) // 2
        if top == "Center":
            top = (self.parent.size_noscale[1] - height) // 2

        ref = False
        if not isinstance(left, int) and left.startswith("Ref:"):
            ref = True
        else:
            left = int(left)
        if not isinstance(top, int) and top.startswith("Ref:"):
            ref = True
        else:
            top = int(top)
        if not isinstance(width, int) and width.startswith("Ref:"):
            ref = True
        else:
            width = int(width)
        if not isinstance(height, int) and height.startswith("Ref:"):
            ref = True
        else:
            height = int(height)

        if ref:
            self.parent.refs.append(self)

        self.pos_noscale = (left, top)
        self.size_noscale = (width, height)

    def update_scale(self):
        if self.image_noscale.get_width():
            w, h = self.image_noscale.get_size()
            scr_scale = self.image_noscale.scr_scale if hasattr(self.image_noscale, "scr_scale") else 1
            w //= scr_scale
            h //= scr_scale
            size = (w, h)
            if size <> self.size_noscale:
                size = cw.s(self.size_noscale)
                if cw.cwpy.setting.smoothscale_bg and self.imgpath:
                    self._image = cw.image.smoothscale(self.image_noscale, size)
                else:
                    self._image = pygame.transform.scale(self.image_noscale, size)
            else:
                self._image = cw.s(self.image_noscale)
        else:
            self._image = self.image_noscale

        self.update_image()

    def clear_image(self):
        if self.image.get_width():
            self.image = pygame.Surface((0, 0)).convert()
        self.rect = pygame.Rect(0, 0, 0, 0)

    def update_image(self):
        """
        現在のフレームに応じてイメージを更新する。
        パーツが出現中の時間でなければ、イメージをクリアする。
        """
        frame = self.parent.frame - self.startframe - self.spawn
        if frame < 0 or self.duration <= frame or not self._image.get_width():
            self.clear_image()
            return

        if self.animation_frame:
            if 1 < self.repeat_count:
                aframe = self.animation_frame + self.repeat_interval
            else:
                aframe = self.animation_frame
            repeat = frame // aframe
            if 1 < self.repeat_count and self.repeat_count <= repeat:
                self.clear_image()
                return

            if 1 < self.repeat_count:
                frame = frame % aframe
                if self.animation_frame <= frame:
                    self.clear_image()
                    return
        else:
            frame = 0

        pos = cw.s(self.pos_noscale)
        size = cw.s(self.size_noscale)

        if self.animation_type == "Spawn":
            # アニメーション無しで出現
            self.image = self._image
            self.rect = pygame.Rect(pos, size)

        elif self.animation_type in ("FadeIn", "FadeOut"):
            # フェードインしながら出現・フェードアウトしながら消滅
            self.rect = pygame.Rect(pos, size)
            alpha = min(255, (frame*255) // self.animation_frame)
            if self.animation_type == "FadeOut":
                alpha = 255 - alpha

            if not self._has_alpha and 255 < alpha:
                alpha = None

            if self._has_alpha:
                self.image = self._image.copy()
                self.image.fill((255, 255, 255, alpha), special_flags=pygame.locals.BLEND_RGBA_MULT)
            else:
                self.image = self._image
                if self.image.get_alpha() <> alpha:
                    self.image.set_alpha(alpha)

        elif self.animation_type == "Rotate":
            # カードのように回転
            width = size[0]
            size = (size[0]*self.dealing_scales[frame] // 100, size[1])
            pos = (pos[0] + (width-size[0])//2, pos[1])
            self.rect = pygame.Rect(pos, size)
            if self._image.get_size() == size:
                self.image = self._image
            else:
                self.image = cw.image.smoothscale(self._image, size)

        else:
            raise Exception("Invalid AnimationType: %s" % (self.animation_type))


def main():
    pass

if __name__ == "__main__":
    main()
