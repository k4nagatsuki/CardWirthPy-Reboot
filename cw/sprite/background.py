#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import os

import pygame
from pygame.locals import BLEND_ADD, BLEND_SUB, BLEND_MULT, BLEND_RGBA_MULT

import cw
from . import base
from . import card

# ------------------------------------------------------------------------------
# 背景スプライト
# ------------------------------------------------------------------------------

BG_SEPARATOR = -1
BG_IMAGE = 0
BG_TEXT = 1
BG_COLOR = 2
BG_PC = 3


class BackGround(base.CWPySprite):
    def __init__(self):
        base.CWPySprite.__init__(self)
        self.bgs = []
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert()
        self.rect = self.image.get_rect()
        # 画面スケール変更などによってアニメーションを途中まで
        # 再実行するための記憶用変数
        self._in_playing = False
        self._bgs = []
        self._elements = []
        self._doanime = cw.effectbooster.AnimationCounter()
        self._ttype = ("None", "None")
        # 背景不継承の時、完全に削除するセルの位置
        self._inhrt_index = 0
        # 次の背景ロードで強制的に背景不継承とする
        self._force_noinhrt = False
        # spritegroupに追加
        self.layer = (cw.LAYER_BACKGROUND, cw.LTYPE_BACKGROUND, 0, 0)
        cw.cwpy.cardgrp.add(self, layer=self.layer)
        # レイヤ0以外に配置した背景セル
        self.foregrounds = set()
        self.foregroundlist = []
        # 冒険の再開などで背景の状態を変更しないために
        # 直に配置されたJPDCイメージがあれば操作可能になった時点で再読込する
        self.reload_jpdcimage = True
        self.has_jpdcimage = False

        self.use_excache = False

        self.curtained = False
        self._curtains = []
        self.curtain_all = False

        self.pc_cache = {}

    def update_scale(self):
        self.image = pygame.Surface(cw.s(cw.SIZE_AREA)).convert()
        self.rect = self.image.get_rect()
        if self._in_playing:
            # Jpy1アニメーション中の場合は再実行
            bgs = self._bgs
            doanime = self._doanime.get_reloadcounter()
            elements = self._elements
            ttype = self._ttype

            def func():
                # アニメーション前の背景を復元
                self.image.fill((0, 0, 0))
                self.bgs = bgs
                self._reload(doanime=cw.effectbooster.CutAnimation(), ttype=("None", "None"), redraw=False, force=True)
                if elements:
                    # 再実行
                    self.load(elements, doanime=doanime, ttype=ttype)
                else:
                    # 再実行
                    self._reload(doanime=doanime, ttype=ttype, redraw=True, force=False)
                if self.curtained:
                    self.set_curtain(curtain_all=self.curtain_all)
                # 内部状態の復元
                self._bgs = bgs
                self._elements = elements
                self._ttype = ttype
            cw.cwpy.exec_func(func)
        else:
            self.image.fill((0, 0, 0))
            self._reload(doanime=cw.effectbooster.CutAnimation(), ttype=("None", "None"), redraw=False, force=True,
                         nocheckvisible=True)
            if self.curtained:
                self.set_curtain(curtain_all=self.curtain_all)

    def update_skin(self, oldskindir, newskindir):
        pass

    def set_curtain(self, curtain_all):
        self.clear_curtain()
        self.curtained = True
        self._curtains = []
        self.curtain_all = curtain_all
        if curtain_all:
            layer = (cw.LAYER_SPBACKGROUND, cw.LTYPE_BACKGROUND, 0, 0)
            maincurtain = cw.sprite.background.Curtain(self, cw.cwpy.cardgrp, layer=layer)
            self._curtains.append(maincurtain)
            for pcard in cw.cwpy.get_pcards():
                layer, ltype, index, subtype = pcard.layer
                pcard.layer = (layer+cw.LAYER_SP_LAYER, ltype, index, subtype)
                cw.cwpy.cardgrp.change_layer(pcard, pcard.layer)
        else:
            if self.foregrounds:
                # 他のスプライトがすでに配置されている箇所に多重にカーテンがかかってしまうのを
                # 避けるため、カーテンから他スプライトの位置をカットするための情報を作成する
                cutter = pygame.Surface(cw.s(cw.SIZE_AREA)).convert_alpha()
                cutter.fill((0, 0, 0, 0))

                layers = []
                for sprite in reversed(cw.cwpy.cardgrp.sprites()):
                    if isinstance(sprite, cw.sprite.background.Curtain):
                        curtain = sprite
                        rect = sprite.target.rect
                    elif isinstance(sprite, cw.sprite.background.BgCell):
                        if sprite.bgtype == BG_COLOR and sprite.d[-1] in (pygame.locals.BLEND_RGB_ADD,
                                                                          pygame.locals.BLEND_RGB_SUB,
                                                                          pygame.locals.BLEND_RGB_MULT,
                                                                          pygame.locals.BLEND_RGBA_ADD,
                                                                          pygame.locals.BLEND_RGBA_SUB,
                                                                          pygame.locals.BLEND_RGBA_MULT):
                            continue
                        bgcell = sprite
                        rect = bgcell.rect
                        curtain = cw.sprite.background.Curtain(bgcell, cw.cwpy.cardgrp, is_selectable=False,
                                                               initialize=False)
                        self._curtains.append(curtain)
                    else:
                        continue

                    subrect = cutter.get_rect().clip(rect)
                    if 0 < subrect.width and 0 < subrect.height:
                        curtain.cutter = cutter.subsurface(subrect).copy()
                        curtain.cutter_pos = (max(0, -rect.left), max(0, -rect.top))
                        mask = curtain.create_mask()
                        if mask:
                            # 透明部分だけカットする
                            mask.fill((0, 0, 0, 255), special_flags=pygame.locals.BLEND_RGBA_MIN)
                            cutter.blit(mask, rect.topleft, special_flags=pygame.locals.BLEND_RGBA_MAX)
                        else:
                            cutter.fill((0, 0, 0, 255), subrect)

                    curtain.update_scale()

                maincurtain = cw.sprite.background.Curtain(self, cw.cwpy.cardgrp,
                                                           initialize=False)
                self._curtains.append(maincurtain)
                maincurtain.cutter = cutter
                maincurtain.update_scale()
            else:
                maincurtain = cw.sprite.background.Curtain(self, cw.cwpy.cardgrp)
                self._curtains.append(maincurtain)
        cw.cwpy.add_lazydraw(clip=self.rect)

    def clear_curtain(self):
        if not self.curtained:
            return

        self.curtained = False
        if self.curtain_all:
            for pcard in cw.cwpy.get_pcards():
                layer, ltype, index, subtype = pcard.layer
                assert cw.LAYER_SP_LAYER < layer
                pcard.layer = (layer-cw.LAYER_SP_LAYER, ltype, index, subtype)
                cw.cwpy.cardgrp.change_layer(pcard, pcard.layer)
            self.curtain_all = False
        cw.cwpy.cardgrp.remove(self._curtains)
        self._curtains = []
        cw.cwpy.add_lazydraw(clip=self.rect)

    def store_filepath(self, path):
        if not cw.cwpy.is_playingscenario():
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpy1", ".jptx", ".jpdc") or ext in cw.EXTS_SND:
            return
        if not os.path.isfile(path):
            return

        for dpath in (cw.util.join_paths(cw.tempdir, "ScenarioLog/TempFile"), cw.cwpy.sdata.scedir):
            dpath = cw.util.join_paths(dpath)
            if not dpath.endswith("/"):
                dpath += "/"
            if path.startswith(dpath):
                rel = cw.util.relpath(path, dpath)
                cw.cwpy.sdata.background_image_mtime[cw.util.join_paths(rel).lower()] = (rel, os.path.getmtime(path))
                break

    def is_modifiedfile(self):
        if not cw.cwpy.is_playingscenario():
            return False
        cw.fsync.sync()

        for key, (rel, mtime) in cw.cwpy.sdata.background_image_mtime.items():
            for dpath in (cw.util.join_paths(cw.tempdir, "ScenarioLog/TempFile"), cw.cwpy.sdata.scedir):
                fpath = cw.util.join_paths(dpath, rel)
                if os.path.isfile(fpath):
                    if mtime != os.path.getmtime(fpath):
                        return True
                    break
        return False

    def load_surface(self, path, mask, smoothing, size, flag, doanime, visible=True, nocheckvisible=False,
                     can_loaded_scaledimage=True):
        """背景サーフェスを作成。
        path: 背景画像ファイルのパス。
        mask: (0, 0)の色でマスクするか否か。透過画像を使う場合は無視。
        size: 背景のサイズ。
        flag: 背景に対応するフラグ。
        """
        if nocheckvisible:
            if not visible:
                return None, False, False
        else:
            # 対応フラグチェック
            if not cw.cwpy.sdata.flags.get(flag, True):
                return None, False, False
        anime = False
        cachable = True

        try:
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)
            else:
                mtime = 0

            # 画像読み込み
            ext = cw.util.splitext(path)[1].lower()

            if ext != ".jpdc" and cw.cwpy.is_playingscenario() and\
                    (path, mtime, size, mask, smoothing) in cw.cwpy.sdata.resource_cache:
                return cw.cwpy.sdata.resource_cache[(path, mtime, size, mask, smoothing)].copy(), False, False

            if ext == ".jptx":
                image = cw.effectbooster.JptxImage(path, mask).get_image()
            elif ext == ".jpdc":
                image = cw.effectbooster.JpdcImage(mask, path, doanime=doanime).get_image()
                if cw.cwpy.is_processing:
                    # シナリオロード中。ロード後に再撮影する
                    image = pygame.Surface(image.get_size()).convert()
                    image.fill((0, 0, 0))
                    image.set_colorkey((0, 0, 0))
                self.reload_jpdcimage = False
            elif ext == ".jpy1":
                jpy1 = cw.effectbooster.JpyImage(path, mask, doanime=doanime)
                anime = jpy1.is_animated
                cachable = jpy1.is_cacheable
                image = jpy1.get_image()
            else:
                image = cw.util.load_image(path, mask, isback=True, can_loaded_scaledimage=can_loaded_scaledimage,
                                           use_excache=self.use_excache)
        except cw.event.EffectBreakError as ex:
            raise ex
        except cw.effectbooster.ScreenRescale as ex:
            cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)
            self._in_playing = True
            raise ex
        except Exception:
            cw.util.print_ex()
            return None, False, False

        # 指定したサイズに拡大縮小する
        isize = image.get_size()
        if isize not in (size, cw.s((0, 0))):
            # FIXME: 環境によって、高さが1の画像に
            #        pygame.transform.smoothscale()を行うと
            #        稀にアクセス違反になる事がある
            smoothscale_bg = (cw.cwpy.setting.smoothscale_bg and 1 < image.get_height())
            if smoothing != "Default":
                smoothscale_bg = cw.util.str2bool(smoothing)
            if smoothscale_bg and not (float(size[0]) % isize[0] == 0 and float(size[1]) % isize[1] == 0):
                if not (image.get_flags() & pygame.locals.SRCALPHA) and image.get_colorkey():
                    image = image.convert_alpha()
                image = cw.image.smoothscale(image, size)
            else:
                image = pygame.transform.scale(image, size)

        if not anime and cachable and cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.sweep_resourcecache(cw.util.calc_imagesize(image))
            cw.cwpy.sdata.resource_cache[(path, mtime, size, mask, smoothing)] = image

        return image, anime, True

    def clear_background(self):
        self._force_noinhrt = True
        self.pc_cache.clear()

    def load(self, elements, doanime=True, ttype=("Default", "Default"), bginhrt=True,
             nocheckvisible=False, redraw=True):
        """背景画面を構成する。
        elements: BgImageElementのリスト。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        if self._in_playing:
            return False

        cw.fsync.sync()

        if self._force_noinhrt:
            self._force_noinhrt = False
            bginhrt = False

        if not bginhrt:
            self.bgs = []

        oldbgs = list(self.bgs)
        self._bgs = list(oldbgs)
        self._elements = elements

        if not cw.cwpy.update_scaling:
            cw.cwpy.file_updates_bg = False
            self.use_excache = False
            self.pc_cache.clear()
        self.reload_jpdcimage = True

        animated = False
        blitlist = []
        update = False
        forcedraw = False

        if doanime:
            if isinstance(doanime, bool):
                self._doanime = cw.effectbooster.AnimationCounter()
            else:
                self._doanime = doanime
        else:
            self._doanime = cw.effectbooster.CutAnimation()
        self._ttype = ttype

        if not doanime:
            ttype = cw.sprite.transition.get_transition(ttype)

        # 背景継承位置。背景が完全に覆われた時、
        # このindexより以前の背景が削除対象となる
        self._inhrt_index = 0

        bginhrt2 = bginhrt
        inhrt_e = None
        if bginhrt and len(elements) and elements[0].tag == "BgImage":
            e = elements[0]
            left = e.getint("Location", "left")
            top = e.getint("Location", "top")
            pos = (left, top)
            width = e.getint("Size", "width")
            height = e.getint("Size", "height")
            size = (width, height)
            mask = e.getbool(".", "mask", False)
            path = cw.util.validate_filepath(e.gettext("ImagePath", ""))
            flag = e.gettext("Flag", "")
            cellname = e.getattr(".", "cellname", "")
            if pos == (0, 0) and size == cw.SIZE_AREA and not mask and path and not cellname:
                # 最初の1件がイメージセル・0,0,632,420のサイズ・マスクなし・パス名あり
                # (ファイルが実在する必要はない)の時、内部的に背景は継承しない状態になる。
                # CWはこの状態で冒険を中断して再開すると事前に描画されていた背景が消えるが、
                # CWPyでは実際に覆われて描画できなくなったもの以外は残すようにする。
                # 背景継承判定においてレイヤは無視される。
                bginhrt2 = False
                if flag:
                    # フラグは指定されていても無視される(CardWirth 1.28～1.50)
                    e.find("Flag").text = ""

        if bginhrt2:
            # 背景継承
            # フラグの状態が変更されており、再描画を要するか判定する
            bginhrt2 = False
            if not nocheckvisible:
                for bgtype, d in self.bgs:
                    if self._is_flagchanged(bgtype, d):
                        bginhrt2 = True
                        break
        else:
            self.bgs = []
            del self.foregroundlist[:]
            self._inhrt_index = 0

        if bginhrt2:
            # 背景継承
            # フラグ等で状態が変化している可能性があるので再描画
            # JPY1のアニメーションも行う
            ret = self._reload(doanime=doanime, ttype=("None", "None"),
                               redraw=False, force=False, nocheckvisible=False,
                               redisplay=False, beforeload=True)
            if ret is None:
                return False  # 中断
            animated, blitlist, update, forcedraw = ret

        afterseps = False
        if self.bgs and self.bgs[-1][0] != BG_SEPARATOR and bginhrt:
            self.bgs.append((BG_SEPARATOR, None))
        for e in elements:
            if e.tag == "BgImage":
                # 背景画像
                d = self._create_bgdata(e)
                try:
                    animated2, update2, bginhrt2 = self._add_imagecell(blitlist, self.bgs, oldbgs, d, self._doanime,
                                                                       nocheckvisible=nocheckvisible)
                    animated |= animated2
                    bginhrt &= bginhrt2
                    update |= update2
                except cw.effectbooster.ScreenRescale:
                    return False  # 中断

            elif e.tag == "TextCell":
                # テキストセル
                d = self._create_bgdata(e)
                if self._add_textcell(blitlist, self.bgs, oldbgs, d,
                                      nocheckvisible=nocheckvisible):
                    forcedraw = True

            elif e.tag == "ColorCell":
                # カラーセル
                d = self._create_bgdata(e)
                if self._add_colorcell(blitlist, self.bgs, oldbgs, d,
                                       nocheckvisible=nocheckvisible):
                    forcedraw = True

            elif e.tag == "PCCell":
                # PCイメージセル
                d = self._create_bgdata(e)
                if self._add_pccell(blitlist, self.bgs, oldbgs, d,
                                    nocheckvisible=nocheckvisible):
                    forcedraw = True

            elif e.tag == "Redisplay":
                self.bgs.append((BG_SEPARATOR, None))
                if blitlist:
                    blitlist, _ = self._load_after(bginhrt or afterseps, blitlist, doanime, animated, ("None", "None"),
                                                   oldbgs, False, True)
                else:
                    # エフェクトブースターの一時描画で使ったスプライトはすべて削除
                    cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)
                animated = False
                afterseps = True

        update = update or not _equals_bgs(self.bgs, oldbgs, False)
        redraw = redraw and not _equals_bgs(self.bgs, oldbgs, True)

        if update:
            _, transition = self._load_after(bginhrt or afterseps, blitlist, doanime, animated, ttype, oldbgs,
                                             True and redraw, False)
        elif forcedraw:
            _, transition = self._load_after(bginhrt or afterseps, blitlist, doanime, animated, ttype, oldbgs,
                                             False, False)
        else:
            # エフェクトブースターの一時描画で使ったスプライトはすべて削除
            cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)
            transition = False

        if cw.cwpy.ydata and (update or forcedraw):
            cw.cwpy.ydata.changed()

        self._bgs = []
        self._elements = []
        self._doanime = cw.effectbooster.AnimationCounter()
        self._ttype = ("None", "None")
        self._in_playing = False
        return update and redraw and not transition and not animated

    def _create_bgdata(self, e, ignoreeffectbooster=False):
        assert e.tag != "Redisplay"
        left = e.getint("Location", "left")
        top = e.getint("Location", "top")
        pos = (left, top)
        width = e.getint("Size", "width")
        height = e.getint("Size", "height")
        size = (width, height)
        flag = e.gettext("Flag", "")
        layer = e.getint("Layer", cw.LAYER_BACKGROUND)
        visible = e.getattr(".", "visible", "")
        hasvisible = visible != ""
        if visible in ("True", "False"):
            visible = visible == "True"
        else:
            visible = cw.cwpy.sdata.flags.get(flag, True) and size != (0, 0) and\
                self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        cellname = e.getattr(".", "cellname", "")

        def getcolor(e, xpath, r, g, b, a):
            r = e.getint(xpath, "r", r)
            g = e.getint(xpath, "g", g)
            b = e.getint(xpath, "b", b)
            a = e.getint(xpath, "a", a)
            return (r, g, b, a)

        if e.tag == "BgImage":
            # 背景画像
            mask = e.getbool(".", "mask", False)
            smoothing = e.getattr(".", "smoothing", "Default")
            path = cw.util.validate_filepath(e.gettext("ImagePath", ""))
            if ignoreeffectbooster and os.path.splitext(path)[1].lower() in (".jpy1", ".jptx", ".jpdc"):
                # 背景置換コンテントでエフェクトブースターファイルが
                # 完全に無視される(CWNext 1.60との互換動作)
                return None

            # 使用時イベント中なら使用したカードの素材から探す
            if e.getbool("ImagePath", "inusecard", False):
                inusecard = True
                scaledimage = e.getbool("ImagePath", "scaledimage", False)
            else:
                imgpath = cw.util.get_inusecardmaterialpath(path, cw.M_IMG)
                inusecard = os.path.isfile(imgpath)
                scaledimage = cw.cwpy.sdata.can_loaded_scaledimage

            return (path, inusecard, scaledimage, mask, smoothing, size, pos, flag, visible, layer, cellname)

        elif e.tag == "TextCell":
            # テキストセル
            text = e.gettext("Text", "")
            face = e.gettext("Font", "")
            tsize = e.getint("Font", "size", 12)
            color = getcolor(e, "Color", 0, 0, 0, 255)
            bold = e.getbool("Font", "bold", False)
            italic = e.getbool("Font", "italic", False)
            underline = e.getbool("Font", "underline", False)
            strike = e.getbool("Font", "strike", False)
            vertical = e.getbool("Vertical", False)
            antialias = e.getbool("Antialias", False)
            btype = e.getattr("Bordering", "type", "None")
            bcolor = getcolor(e, "Bordering/Color", 255, 255, 255, 255)
            bwidth = e.getint("Bordering", "width", 1)
            if hasvisible:
                # visible属性を持つ場合はシナリオではなくScenarioLogの情報。
                # 0.12.3以前はテキストセルの内容が表示の有無にかかわりなく
                # 最初の出現時点で固定されていたが、0.12.4以降はCardWirthに
                # 合わせて最初の表示時点で固定するように変更した。
                # visibleがあってloadedが無い場合は0.12.3以前の情報で、
                # 内容はすでに固定済みとなっている。
                # ---
                # 2.0以降は、パーティ名などの変更に合わせてでテキストを
                # 更新するため、loadedパラメータは使用せずにNames要素を
                # 使用して表示対象を固定する。
                # loadedは常にFalseになるが、パラメータ自体は互換性のために残す。
                loaded = e.getbool(".", "loaded", True)
            else:
                loaded = e.getbool(".", "loaded", False)
            # テキストセルの更新をどこまで行うか(Wsn.4)
            # Fixedで最初の表示内容に固定(CardWirth 1.50)
            # Variablesで状態変数のみ更新(～CardWirthPy 3.1)
            # Allで全て更新
            # 互換性確保のためパラメータが存在しなかった場合はVariablesにする
            updatetype = e.gettext("UpdateType", "Variables")

            e_names = e.find("Names")
            if e_names is None:
                namelist = None
            else:
                namelist = []
                try:
                    for e_name in e_names:
                        vtype = e_name.getattr(".", "type", "")
                        name = e_name.text if e_name.text else ""
                        if vtype == "Yado":
                            data = cw.cwpy.ydata
                        elif vtype == "Party":
                            data = cw.cwpy.ydata.party if cw.cwpy.ydata else None
                        elif vtype == "Player":
                            number = e_name.getint(".", "number", 0)-1
                            pcards = cw.cwpy.get_pcards()
                            if 0 <= number and number < len(pcards):
                                data = pcards[number]
                            else:
                                data = None
                        elif vtype == "Flag":
                            name2 = e_name.getattr(".", "flag", "")
                            name = cw.util.str2bool(name)
                            if name2 in cw.cwpy.sdata.flags:
                                data = cw.cwpy.sdata.flags[name2]
                            else:
                                data = None
                        elif vtype == "Step":
                            name2 = e_name.getattr(".", "step", "")
                            name = int(name)
                            if name2 in cw.cwpy.sdata.steps:
                                data = cw.cwpy.sdata.steps[name2]
                            else:
                                data = cw.sprite.message.get_spstep(name2)
                        elif vtype == "Variant":
                            name2 = e_name.getattr(".", "variant", "")
                            vtype = e_name.getattr(".", "valuetype")
                            name = cw.data.Variant.value_from_str(vtype, name)
                            if name2 in cw.cwpy.sdata.variants:
                                data = cw.cwpy.sdata.variants[name2]
                            else:
                                data = None
                        elif vtype == "Number":
                            name = int(e_name.text)
                            data = "Number"
                        else:
                            data = None
                        namelist.append(cw.sprite.message.NameListItem(data, name))
                except Exception:
                    namelist = []

            return (text, namelist, face, tsize, color, bold, italic, underline, strike, vertical, antialias,
                    btype, bcolor, bwidth, loaded, updatetype, size, pos, flag, visible, layer, cellname)

        elif e.tag == "ColorCell":
            # カラーセル
            blend = e.gettext("BlendMode", "Normal")
            color1 = getcolor(e, "Color", 255, 255, 255, 255)
            gradient = e.getattr("Gradient", "direction", "None")
            color2 = getcolor(e, "Gradient/EndColor", 0, 0, 0, 255)

            return (blend, color1, gradient, color2, size, pos, flag, visible, layer, cellname)

        elif e.tag == "PCCell":
            # PCイメージセル
            pcnumber = e.getint("PCNumber", 0)
            expand = e.getbool(".", "expand", False)
            smoothing = e.getattr(".", "smoothing", "Default")

            return (pcnumber, expand, smoothing, size, pos, flag, visible, layer, cellname)

        else:
            assert False

    def reload(self, doanime=True, ttype=("Default", "Default"), redraw=True, cellname="", repldata=None,
               movedata=None, ignoreeffectbooster=False, nocheckvisible=False):
        return self._reload(doanime, ttype, redraw, False, redisplay=False, cellname=cellname, repldata=repldata,
                            movedata=movedata, ignoreeffectbooster=ignoreeffectbooster, nocheckvisible=nocheckvisible)

    def _reload(self, doanime=True, ttype=("Default", "Default"), redraw=True, force=False, nocheckvisible=False,
                redisplay=True, beforeload=False, cellname="", repldata=None, movedata=None, ignoreeffectbooster=False):
        """背景画面を再構成する。
        ttype: (トランジションの名前, トランジションの速度)のタプル。
        """
        cw.fsync.sync()

        if cellname:
            # 背景置換または削除。
            # 置換において複数のセルが指定された場合は次のように動く。
            #  1. 指定名称のセルを全て削除する
            #  2. 指定名称の最初のセルがあった位置に置換後セルを全て追加する
            bgs2 = []
            replaced = False
            for bgtype, d in self.bgs:
                if bgtype == BG_IMAGE and ignoreeffectbooster:
                    path = d[0]
                    if os.path.splitext(path)[1].lower() in (".jpy1", ".jptx", ".jpdc"):
                        bgs2.append((bgtype, d))
                        continue

                if cellname == self._get_cellname(bgtype, d):
                    if movedata:
                        d = self._move_bgdata(bgtype, d, movedata)
                        bgs2.append((bgtype, d))

                    elif repldata is not None:
                        for e in repldata:
                            if e.tag == "BgImage":
                                # 背景画像
                                bgtype = BG_IMAGE
                                d = self._create_bgdata(e, ignoreeffectbooster=ignoreeffectbooster)
                                if not d:
                                    continue

                            elif e.tag == "TextCell":
                                # テキストセル
                                bgtype = BG_TEXT
                                d = self._create_bgdata(e)

                            elif e.tag == "ColorCell":
                                # カラーセル
                                bgtype = BG_COLOR
                                d = self._create_bgdata(e)

                            elif e.tag == "PCCell":
                                # PCイメージセル
                                bgtype = BG_PC
                                d = self._create_bgdata(e)

                            bgs2.append((bgtype, d))
                        repldata = None
                    replaced = True
                else:
                    bgs2.append((bgtype, d))

            if not replaced:
                # 指定されたセル名称のセルが無かった
                return False
        else:
            bgs2 = self.bgs

        # 背景再構築
        oldbgs = list(self.bgs)
        bgs = []

        if not cw.cwpy.update_scaling:
            cw.cwpy.file_updates_bg = False
            self.use_excache = False
            self.pc_cache.clear()
        self.reload_jpdcimage = True

        animated = False
        blitlist = []
        bginhrt = True
        update = force
        forcedraw = False
        if not beforeload:
            self._inhrt_index = 0

            self._bgs = list(oldbgs)
            if doanime:
                if isinstance(doanime, bool):
                    self._doanime = cw.effectbooster.AnimationCounter()
                else:
                    self._doanime = doanime
                self._ttype = ("None", "None")
            else:
                self._doanime = cw.effectbooster.CutAnimation()
                self._ttype = ttype

        if not beforeload and not doanime:
            ttype = cw.sprite.transition.get_transition(ttype)

        for bgtype, d in bgs2:
            if bgtype == BG_IMAGE:
                # 背景画像
                try:
                    animated2, update2, bginhrt2 = self._add_imagecell(blitlist, bgs, oldbgs, d, self._doanime,
                                                                       nocheckvisible=nocheckvisible)
                    animated |= animated2
                    update |= update2
                    bginhrt &= bginhrt2
                except cw.effectbooster.ScreenRescale:
                    # 中断
                    if beforeload:
                        return None
                    else:
                        return False

            elif bgtype == BG_TEXT:
                # テキストセル
                if self._add_textcell(blitlist, bgs, oldbgs, d, nocheckvisible=nocheckvisible):
                    forcedraw = True

            elif bgtype == BG_COLOR:
                # カラーセル
                if self._add_colorcell(blitlist, bgs, oldbgs, d, nocheckvisible=nocheckvisible):
                    forcedraw = True

            elif bgtype == BG_PC:
                # PCイメージセル
                if self._add_pccell(blitlist, bgs, oldbgs, d, nocheckvisible=nocheckvisible):
                    forcedraw = True

            else:
                assert bgtype == BG_SEPARATOR
                if (bgs and bgs[-1][0] == BG_SEPARATOR) or not redisplay:
                    continue
                bgs.append((bgtype, d))
                if blitlist:
                    blitlist, _ = self._load_after(True, blitlist, doanime, animated, ("None", "None"), oldbgs,
                                                   False, True)
                else:
                    # エフェクトブースターの一時描画で使ったスプライトはすべて削除
                    cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)
                animated = False

        update = update or not _equals_bgs(self.bgs, bgs, False)
        redraw = redraw and not _equals_bgs(self.bgs, bgs, True)

        if bginhrt and not blitlist:
            update = False

        if doanime:
            # 背景処理する前に、トランジション用スプライト作成
            transitspr = cw.sprite.transition.get_transition(ttype)
        else:
            # アニメーションしない場合は描画前の
            # トランジション用スプライトが生成されている
            transitspr = ttype

        def clear_forgrounds():
            for sprite in self.foregrounds:
                cw.cwpy.cardgrp.remove(sprite)
            self.foregrounds.clear()
            del self.foregroundlist[:]

        transition = False
        if update:
            self.bgs = bgs
            if not beforeload:
                clear_forgrounds()
                _, transition = self._load_after(True, blitlist, doanime, animated, transitspr, oldbgs, redraw, False)
        elif forcedraw:
            if not beforeload:
                clear_forgrounds()
                _, transition = self._load_after(True, blitlist, doanime, animated, transitspr, oldbgs, False, False)
        else:
            if not beforeload:
                # エフェクトブースターの一時描画で使ったスプライトはすべて削除
                cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)

        if beforeload:
            return animated, blitlist, update, forcedraw
        else:
            self._bgs = []
            self._doanime = cw.effectbooster.AnimationCounter()
            self._ttype = ("None", "None")
            self._in_playing = False
            return update and redraw and not transition and not animated

    def _is_flagchanged(self, bgtype, d):
        if bgtype in (BG_IMAGE, BG_TEXT, BG_COLOR, BG_PC):
            visible = d[-3]
            flag = d[-4]
            return bool(visible) != bool(cw.cwpy.sdata.flags.get(flag, True))
        else:
            return False

    def _get_cellname(self, bgtype, d):
        if bgtype in (BG_IMAGE, BG_TEXT, BG_COLOR, BG_PC):
            return d[-1]
        else:
            return ""

    def _move_bgdata(self, bgtype, d, movedata):
        positiontype, x, y, sizetype, width, height = movedata
        pos = d[-5]
        size = d[-6]
        pos = self._calc_possize(positiontype, pos, (x, y), False)
        size = self._calc_possize(sizetype, size, (width, height), True)
        return d[:-6] + (size, pos) + d[-4:]

    def _calc_possize(self, ctype, vals, movevals, miniszero):
        x, y = vals
        mx, my = movevals

        if ctype == "Absolute":
            x = mx
            y = my
        elif ctype == "Relative":
            x += mx
            y += my
        elif ctype == "Percentage":
            x = ((x * mx) + 50) // 100
            y = ((y * my) + 50) // 100

        if miniszero:
            x = max(0, x)
            y = max(0, y)

        return (x, y)

    def _add_imagecell(self, blitlist, bgs, oldbgs, d, doanime, nocheckvisible=False):
        path, inusecard, scaledimage, mask, smoothing, size, pos, flag, visible, layer, cellname = d
        basepath = path
        bginhrt = True

        if inusecard:
            path = cw.util.join_yadodir(path)
            path = cw.util.get_materialpathfromskin(path, cw.M_IMG)
            if not (path.startswith(cw.cwpy.tempdir) or path.startswith(cw.cwpy.yadodir)):
                # カード固有の素材を参照していない場合はフラグを落としておく
                inusecard = False
        else:
            path = cw.util.get_materialpath(path, cw.M_IMG)

        if cw.cwpy.rsrc:
            path = cw.cwpy.rsrc.get_filepath(path)

        if not os.path.isfile(path):
            return False, False, bginhrt

        image, anime, update = self.load_surface(path, mask, smoothing, cw.s(size), flag, doanime=doanime,
                                                 visible=visible,
                                                 nocheckvisible=nocheckvisible, can_loaded_scaledimage=scaledimage)

        ext = os.path.splitext(path)[1].lower()
        if not anime and ext != ".jpdc" and pygame.Rect(pos, size).contains(pygame.Rect((0, 0), cw.SIZE_AREA)) and\
                visible and not mask and not flag:
            if image and not image.get_colorkey() and not (image.get_flags() & pygame.locals.SRCALPHA):
                # 背景を覆ったので非継承の背景を実際に削除する
                if 0 < self._inhrt_index:
                    del bgs[:self._inhrt_index]
                    del blitlist[:-1]
                bginhrt = False
                self._inhrt_index = 0

        if image and image.get_size() != (0, 0):
            self.store_filepath(path)
            d2 = (image, size, pos, 0)
            blitlist.append((BG_IMAGE, d2, flag, layer))
            bgs.append((BG_IMAGE, (basepath, inusecard, scaledimage, mask, smoothing, size, pos, flag, True, layer,
                                   cellname)))
        else:
            if nocheckvisible:
                flagvalue = visible
            else:
                flagvalue = bool(cw.cwpy.sdata.flags.get(flag, True))
            bgs.append((BG_IMAGE, (basepath, inusecard, scaledimage, mask, smoothing, size, pos, flag, flagvalue,
                                   layer, cellname)))
            oldbgs.append((BG_IMAGE, (basepath, inusecard, scaledimage, mask, smoothing, size, pos, flag, flagvalue,
                                      layer, cellname)))

        return anime, update, bginhrt

    def _add_textcell(self, blitlist, bgs, oldbgs, d, nocheckvisible=False):
        text, namelist, face, tsize, color, bold, italic, underline, strike, vertical, antialias,\
            btype, bcolor, bwidth, loaded, updatetype, size, pos, flag, visible, layer, cellname = d
        if not nocheckvisible and updatetype == "All":
            namelist = None
        if not nocheckvisible:
            visible = cw.cwpy.sdata.flags.get(flag, True) and size != (0, 0) and\
                self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        flagvalue = bool(cw.cwpy.sdata.flags.get(flag, True))
        if flagvalue and not loaded:
            # テキストセルは最初の表示で内容が固定される
            text2 = cw.util.decodewrap(text)
            if nocheckvisible:
                in_inusecardevent = cw.cwpy.event.in_inusecardevent
                cw.cwpy.event.in_inusecardevent = False
            text2, namelist = cw.sprite.message.rpl_specialstr(text2, basenamelist=namelist,
                                                               updatetype=updatetype, localvariables=False)
            if nocheckvisible:
                cw.cwpy.event.in_inusecardevent = in_inusecardevent
            # 2.0以降はloadedパラメータは使用しない
            # loaded = True
        else:
            text2 = text
        if nocheckvisible:
            flagvalue = visible
        d = (text, namelist, face, tsize, color, bold, italic, underline, strike, vertical, antialias,
             btype, bcolor, bwidth, loaded, updatetype, size, pos, flag, flagvalue, layer, cellname)
        if visible:
            if btype == "Inline":
                # 縁取り形式2のみは事前にセル生成が可能
                image = cw.image.create_type2textcell(text2, face, cw.s(tsize), color,
                                                      bold, italic, underline, strike, vertical, antialias,
                                                      cw.s(size), bcolor, bwidth)
                bgtype = BG_IMAGE
                d2 = (image, size, pos, 0)
            else:
                # アンチエイリアスの関係で後から描画
                if btype != "Outline":
                    bcolor = None
                bgtype = BG_TEXT
                d2 = (text2, face, tsize, color, bold, italic, underline, strike, vertical, antialias,
                      bcolor, size, pos)

            blitlist.append((bgtype, d2, flag, layer))

            bgs.append((BG_TEXT, d))
        else:
            bgs.append((BG_TEXT, d))
            oldbgs.append((BG_TEXT, d))
        return visible

    def _add_colorcell(self, blitlist, bgs, oldbgs, d, nocheckvisible=False):
        blend, color1, gradient, color2, size, pos, flag, visible, layer, cellname = d
        if not nocheckvisible:
            visible = cw.cwpy.sdata.flags.get(flag, True) and size != (0, 0) and\
                self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        if nocheckvisible:
            flagvalue = visible
        else:
            flagvalue = bool(cw.cwpy.sdata.flags.get(flag, True))
        d = blend, color1, gradient, color2, size, pos, flag, flagvalue, layer, cellname
        if visible:
            image = cw.image.create_colorcell(cw.s(size), color1, gradient, color2)
            if blend == "Add":
                blendflag = BLEND_ADD
            elif blend == "Subtract":
                blendflag = BLEND_SUB
            elif blend == "Multiply":
                if color1[3] != 255 or (gradient in ("LeftToRight", "TopToBottom") and color2[3] != 255):
                    blendflag = BLEND_RGBA_MULT
                else:
                    blendflag = BLEND_MULT
            else:
                blendflag = 0
            d2 = (image, size, pos, blendflag)
            blitlist.append((BG_COLOR, d2, flag, layer))
            bgs.append((BG_COLOR, d))
        else:
            bgs.append((BG_COLOR, d))
            oldbgs.append((BG_COLOR, d))
        return visible

    def _add_pccell(self, blitlist, bgs, oldbgs, d, nocheckvisible=False):
        pcnumber, expand, smoothing, size, pos, flag, visible, layer, cellname = d
        if not nocheckvisible:
            visible = cw.cwpy.sdata.flags.get(flag, True) and size != (0, 0) and\
                self.rect.colliderect(cw.s(pygame.Rect(pos, size)))
        if nocheckvisible:
            flagvalue = visible
        else:
            flagvalue = bool(cw.cwpy.sdata.flags.get(flag, True))
        if visible:
            # PCのイメージを表示
            if pcnumber in self.pc_cache:
                paths, can_loaded_scaledimage = self.pc_cache[pcnumber]
            else:
                pi = pcnumber - 1
                paths, can_loaded_scaledimage = self.put_pccache(pi)

            if expand:
                image = pygame.Surface(cw.s(cw.SIZE_CARDIMAGE)).convert_alpha()
                image.fill((0, 0, 0, 0))

                for path, info in paths:
                    # BUG: CardWirth 1.50以降では、一部のPNGイメージで背景に配置した時は
                    #      マスク設定が効かないのにカードだと効くという状態になるが、
                    #      1.60ではPCイメージとしてそのようなイメージを表示すると、
                    #      マスクされた状態で表示される。従ってマスクの効く・効かないという
                    #      挙動をエミュレートするための`isback`フラグは常にFalseとする。
                    bmp = cw.util.load_image(path, True, isback=False, can_loaded_scaledimage=can_loaded_scaledimage,
                                             use_excache=self.use_excache)
                    iw, ih = bmp.get_size()
                    scr_scale = bmp.scr_scale if hasattr(bmp, "scr_scale") else 1
                    iw //= scr_scale
                    ih //= scr_scale
                    baserect = info.calc_basecardposition((iw, ih), noscale=True,
                                                          basecardtype="LargeCard",
                                                          cardpostype="NotCard")
                    image.blit(cw.s(bmp), (baserect.x, baserect.y))

                smoothscale_bg = cw.cwpy.setting.smoothscale_bg
                if smoothing != "Default":
                    smoothscale_bg = cw.util.str2bool(smoothing)
                if smoothscale_bg:
                    image = cw.image.smoothscale(image, cw.s(size))
                else:
                    image = pygame.transform.scale(image, cw.s(size))
            else:
                image = pygame.Surface(cw.s(size)).convert_alpha()
                image.fill((0, 0, 0, 0))

                for path, info in paths:
                    bmp = cw.util.load_image(path, True, isback=False, can_loaded_scaledimage=can_loaded_scaledimage,
                                             use_excache=self.use_excache)
                    iw, ih = bmp.get_size()
                    scr_scale = bmp.scr_scale if hasattr(bmp, "scr_scale") else 1
                    iw //= scr_scale
                    ih //= scr_scale
                    baserect = info.calc_basecardposition((iw, ih), noscale=True,
                                                          basecardtype="LargeCard",
                                                          cardpostype="NotCard")
                    image.blit(cw.s(bmp), (baserect.x, baserect.y))

            d2 = (image, size, pos, 0)
            blitlist.append((BG_IMAGE, d2, flag, layer))
            bgs.append((BG_PC, (pcnumber, expand, smoothing, size, pos, flag, True, layer, cellname)))
        else:
            bgs.append((BG_PC, d))
            oldbgs.append((BG_PC, d))
        return visible

    def put_pccache(self, pi):
        pcards = cw.cwpy.ydata.party.members
        paths = []
        can_loaded_scaledimage = False
        if 0 <= pi and pi < len(pcards):
            can_loaded_scaledimage = pcards[pi].getbool(".", "scaledimage", False)
            for info2 in cw.image.get_imageinfos(pcards[pi].find("Property")):
                path = info2.path
                if path:
                    path = cw.util.join_yadodir(path)
                    if path:
                        paths.append((path, info2))
        self.pc_cache[pi+1] = (paths, can_loaded_scaledimage)
        return paths, can_loaded_scaledimage

    def _load_after(self, bginhrt, blitlist, doanime, animated, ttype, oldbgs, redraw, redisplay):
        # 背景を更新する(呼び出し時点でエフェクトブースターは実行済み)

        if isinstance(ttype, cw.sprite.transition.Transition):
            # アニメーションしない場合は描画前の
            # トランジション用スプライトが生成されている
            transitspr = ttype
        elif ttype:
            # 背景処理する前に、トランジション用スプライト作成
            transitspr = cw.sprite.transition.get_transition(ttype)
        else:
            transitspr = None

        if not redisplay:
            for sprite in self.foregrounds:
                cw.cwpy.cardgrp.remove(sprite)
            blitlist2 = []
            for t in self.foregroundlist:
                blitlist2.append(t)
            blitlist2.extend(blitlist)
            blitlist = blitlist2
            self.foregrounds.clear()
            del self.foregroundlist[:]

        if not bginhrt:
            self.image.fill((0, 0, 0))

        blitlist2 = []

        for i, t in enumerate(blitlist):
            bgtype, d2, flag, layer = t
            if layer == cw.LAYER_BACKGROUND:
                # 特別なレイヤ指定が無いので本当の背景に描画
                if cw.cwpy.sdata.flags.get(flag, True):
                    _draw_bgcell(self.image, (bgtype, d2))
            else:
                # それよりも手前に描画する場合はスプライトを生成する
                if redisplay:
                    blitlist2.append(t)
                else:
                    sprite = BgCell(bgtype, d2, flag, layer, i)
                    self.foregrounds.add(sprite)
                    self.foregroundlist.append(t)
                    cw.cwpy.cardgrp.add(sprite, layer=sprite.layer)

        # エフェクトブースターの一時描画で使ったスプライトはすべて削除
        cw.cwpy.topgrp.remove_sprites_of_layer(cw.LAYER_JPY_TEMPORAL)

        # トランジション効果で画面入り
        if redraw:
            cw.cwpy.event.refresh_activeitem()
            if (not animated or not doanime) and transitspr and not _equals_bgs(oldbgs, self.bgs, True):
                cw.cwpy.cardgrp.add(transitspr, layer=cw.LAYER_TRANSITION)
                cw.animation.animate_sprite(transitspr, "transition", background=True)
                cw.cwpy.cardgrp.remove(transitspr)
                transition = True
            else:
                cw.cwpy.add_lazydraw(clip=self.rect)
                transition = False
        else:
            cw.cwpy.add_lazydraw(clip=self.rect)
            transition = False

        self.has_jpdcimage = not self.reload_jpdcimage

        return blitlist2, transition


def _equals_bgs(bgs1, bgs2, visibleonly):
    bgs1 = filter(lambda t: t[1], bgs1)
    bgs2 = filter(lambda t: t[1], bgs2)
    if visibleonly:
        bgs1 = filter(lambda t: t[1][-3], bgs1)
        bgs2 = filter(lambda t: t[1][-3], bgs2)

    for t1, t2 in itertools.zip_longest(bgs1, bgs2):
        if t1 is None or t2 is None:
            return False
        bgtype = t1[0]
        if bgtype != t2[0]:
            return False
        l1 = list(t1[1])
        l2 = list(t2[1])
        if bgtype == BG_IMAGE:
            # ファイルパスの拡張子を取り除き、ケースを正規化
            l1[0] = os.path.splitext(l1[0])[0].lower()
            l2[0] = os.path.splitext(l2[0])[0].lower()
        # flag, cellname を取り除く
        l1[-4] = ""
        l2[-4] = ""
        l1[-1] = ""
        l2[-1] = ""
        if l1 != l2:
            return False
    return True


def _draw_bgcell(surface, bgdata, allclip=None):
    bgtype, d = bgdata
    srect = surface.get_rect()
    clip = surface.get_clip()
    if allclip:
        srect = allclip

    if bgtype in (BG_IMAGE, BG_COLOR):
        # 背景画像、カラーセル、縁取り形式2のテキストセル
        image, _size, pos, sflag = d
        rect = image.get_rect()
        rect.topleft = cw.s(pos)
        if srect.colliderect(rect):
            surface.set_clip(srect.clip(rect))
            if sflag in (0, BLEND_MULT):
                surface.blit(image, cw.s(pos), None, sflag)
            elif sflag in (BLEND_ADD, BLEND_SUB, BLEND_RGBA_MULT):
                cw.imageretouch.blend_1_50(surface, cw.s(pos), image, sflag)
            else:
                assert False

    elif bgtype == BG_TEXT:
        # 縁取り形式2以外のテキストセル
        text, face, tsize, color, bold, italic, underline, strike, vertical, antialias,\
            bcolor, size, pos = d
        rect = cw.s(pygame.Rect(pos, size))
        if srect.colliderect(rect):
            surface.set_clip(srect.clip(rect))
            cw.image.draw_textcell(surface, rect, text, face,
                                   cw.s(tsize), color, bold, italic, underline, strike, vertical,
                                   antialias, bcolor)

    else:
        assert False

    surface.set_clip(clip)
    return rect


class BgCell(base.CWPySprite):
    def __init__(self, bgtype, d, flag, layer, index):
        cw.sprite.base.CWPySprite.__init__(self)
        self.bgtype = bgtype
        self.d = d
        self.flag = flag
        self.layer = (layer, cw.LTYPE_BACKGROUND, -1, index)

        if bgtype in (BG_IMAGE, BG_COLOR):
            # 背景画像、カラーセル、縁取り形式2のテキストセル
            image, size, pos, _sflag = d
            self.rect_noscale = pygame.Rect(pos, size)

        elif bgtype == BG_TEXT:
            # 縁取り形式2以外のテキストセル
            _text, _face, _tsize, _color, _bold, _italic, _underline, _strike, _vertical, _antialias,\
                _bcolor, size, pos = d
            self.rect_noscale = pygame.Rect(pos, size)

        self.rect = cw.s(self.rect_noscale)


def layered_draw_ex(layered_updates, surface):
    rects = []
    srect = surface.get_rect()
    clip = surface.get_clip()
    if clip:
        srect = clip

    sprites = layered_updates.sprites()
    for sprite in sprites:
        if isinstance(sprite, BgCell):
            rect = _draw_bgcell(surface, (sprite.bgtype, sprite.d), clip)
            rects.append(rect)
        else:
            if srect.colliderect(sprite.rect):
                surface.set_clip(srect.clip(sprite.rect))
                rect = surface.blit(sprite.image, sprite.rect)
                rects.append(rect)
    surface.set_clip(clip)
    return rects


class Curtain(base.SelectableSprite):
    def __init__(self, target, spritegrp, color=None, layer=None, cut_bgs=False,
                 is_selectable=True, initialize=True):
        """半透明のブルーバックスプライト。右クリックで解除。
        target: 覆い隠す対象。
        spritegrp: 登録するSpriteGroup。
        color: カーテン色(不透明度含む)。
        """
        base.SelectableSprite.__init__(self)
        self.cutter = None
        self.cutter_pos = (0, 0)
        self._is_selectable = is_selectable

        if color:
            self.color = color
        else:
            self.color = cw.cwpy.setting.curtaincolour
        self.target = target
        if initialize:
            self.update_scale()

        # spritegroupに追加
        if layer:
            self.layer = layer
        else:
            self.layer = (target.layer[0], target.layer[1], target.layer[2], 100)
        spritegrp.add(self, layer=self.layer)
        cw.cwpy.curtains.append(self)

    def update_scale(self):
        # 重なった領域・スケール変更
        self.image = pygame.Surface(self.target.rect.size).convert_alpha()
        self.image.fill(self.color)
        self.rect = pygame.Rect(self.target.rect)

        if self.cutter:
            self.image.blit(self.cutter, self.cutter_pos, special_flags=pygame.locals.BLEND_RGBA_SUB)

        mask = self.create_mask()
        if mask:
            mask.fill((0, 0, 0, 255), special_flags=pygame.locals.BLEND_RGBA_MIN)
            mask.fill(self.color[:3] + (0,), special_flags=pygame.locals.BLEND_RGBA_ADD)
            self.image.blit(mask, (0, 0), special_flags=pygame.locals.BLEND_RGBA_MIN)

    def create_mask(self):
        if isinstance(self.target, BgCell):
            if self.target.bgtype == BG_TEXT:
                # 縁取り形式2以外のテキストセル
                text, face, tsize, color, bold, italic, underline, strike, vertical, antialias, bcolor, size, _pos =\
                    self.target.d
                rect = cw.s(pygame.Rect(cw.s((0, 0)), size))
                subimg = pygame.Surface(rect.size).convert_alpha()
                subimg.fill((0, 0, 0, 0))
                cw.image.draw_textcell(subimg, rect, text, face,
                                       cw.s(tsize), color, bold, italic, underline, strike, vertical, antialias, bcolor)
            else:
                subimg = self.target.d[0]
                if (subimg.get_flags() & pygame.locals.SRCALPHA):
                    subimg = subimg.copy()
                else:
                    subimg = subimg.convert_alpha()
        else:
            subimg = self.target.image
            if not (subimg.get_flags() & pygame.locals.SRCALPHA):
                return None
            subimg = subimg.copy()

        return subimg

    def rclick_event(self):
        cw.cwpy.cancel_cardcontrol()

    def is_selection(self):
        if not self._is_selectable:
            return False
        return cw.sprite.base.SelectableSprite.is_selection(self)


class BattleCardImage(card.CWPyCard):
    def __init__(self):
        """戦闘開始時のアニメーションに使うスプライト。
        cw.animation.battlestart を参照。
        """
        card.CWPyCard.__init__(self, "hidden")
        path = "Resource/Image/Card/BATTLE"
        path = cw.util.find_resource(cw.util.join_paths(cw.cwpy.skindir, path), cw.cwpy.rsrc.ext_img)
        cardimg = cw.image.CardImage([cw.image.ImageInfo(path)], "NORMAL", "", can_loaded_scaledimage=True)
        image = cardimg.get_image()
        self.image = self._image = self.image_unzoomed = image
        self.rect = self._rect = self.image.get_rect()
        self.set_pos_noscale(center_noscale=(316, 142))
        self.clear_image()
        # spritegroupに追加
        cw.cwpy.cardgrp.add(self, layer=cw.LAYER_BATTLE_START)

    def update_battlestart(self):
        self.highspeed = True
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (8, 12)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (28, 40)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        cw.animation.animate_sprite(self, "hide")
        self.zoomsize_noscale = (56, 80)
        cw.animation.animate_sprite(self, "zoomin")
        cw.animation.animate_sprite(self, "deal")
        waitrate = (cw.cwpy.setting.get_dealspeed(False)+1) * 4
        cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
        self.highspeed = False

    def update_image(self, update_statusimg=False, is_runningevent=None):
        pass

    def update_selection(self):
        pass


class InuseCardImage(card.CWPyCard):
    def __init__(self, user, header, status="normal", center=False, alpha=None, fore=False):
        """使用中のカード画像スプライト。
        user: Character。
        header: 使用するカードのCardHeader。
        status: すぐ表示したくない場合は"hidden"を指定。
        center: 画面中央に表示するかどうか。
        spritegrp: 追加先のスプライトグループ。Noneの場合は自動選択。
        alpha: 不透明度。0～255。
        fore: 常に手前に表示する場合はTrue。
        """
        card.CWPyCard.__init__(self, status)
        self.status = status
        self.user = user
        self.header = header
        self.center = center
        self.zoomsize_noscale = (48, 66)
        self.alpha = alpha

        self.update_scale()

        # spritegroupに追加
        self.group = cw.cwpy.cardgrp
        if user and not center and not fore:
            if hasattr(user, "layer_t"):
                layer = user.layer_t[0]
                ltype = user.layer_t[1]
            else:
                layer = user.layer[0]
                ltype = user.layer[1]
            self.group.add(self, layer=(layer, ltype, user.index, 1))
        else:
            self.group.add(self, layer=cw.LAYER_FRONT_INUSECARD)

    def update_scale(self):
        self.header.negaflag = False
        image = self.header.get_cardimg()
        self.image = self._image = image
        self.rect = self._rect = image.get_rect()

        if not self.user.scale == 100 and not self.center:
            scale = self.user.scale / 100.0
            self.image = cw.image.zoomcard(self.image, scale)
            self.rect.size = self.image.get_size()

        self.image.set_alpha(self.alpha)

        if self.center:
            self.set_pos_noscale(center_noscale=(316, 142))
        else:
            self.set_pos(center=self.user.rect.center)

        if self.status == "hidden":
            self.clear_image()

    def update_image(self, update_statusimg=False, is_runningevent=None):
        pass

    def update_selection(self):
        pass


class LifeBar(base.CWPySprite):
    def __init__(self, ccard):
        """ccardのライフバーを切り出して単一のスプライトとする。
        ccard: Character。
        """
        assert ccard.is_analyzable() and not ccard.is_unconscious()
        base.CWPySprite.__init__(self)
        self.ccard = ccard

        self.update_scale()

        # spritegroupに追加
        self.group = cw.cwpy.cardgrp
        self.group.add(self, layer=cw.LAYER_FRONT_LIFEBAR)

    def update_scale(self):
        bgname = self.ccard.cardimg.get_cardbgname(self.ccard)
        cardbg = cw.cwpy.rsrc.cardbgs[bgname]
        self.image = pygame.Surface(cardbg.get_size()).convert_alpha()
        self.image.fill((0, 0, 0, 0))
        self.image.blit(self.ccard.cardimg.lifeimg, cw.s((8, 110)))
        self.image = cw.image.zoomcard(self.image, self.ccard.scale / 100.0)
        self._image = self.image
        self.rect = pygame.Rect(self.ccard.rect)
        self._rect = pygame.Rect(self.rect)
        if self.ccard.status == "click":
            self.click()

    def click(self):
        size = (self._rect.w * 9 // 10, self._rect.h * 9 // 10)
        self.image = pygame.transform.scale(self._image, size)
        self.rect = pygame.Rect(self._rect)
        self.rect.size = size
        self.rect.center = self._rect.center

    def declick(self):
        self.image = self._image
        self.rect = self._rect


class TargetArrow(base.CWPySprite):
    def __init__(self, target):
        """ターゲット選択する矢印画像スプライト。
        target: Character。
        """
        base.CWPySprite.__init__(self)
        self.target = target
        self.update_scale()
        # spritegroupに追加
        cw.cwpy.cardgrp.add(self, layer=cw.LAYER_TARGET_ARROW)

    def update_scale(self):
        self.image = cw.cwpy.rsrc.statuses["TARGET"]
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.target.rect.right - cw.s(20), self.target.rect.bottom - cw.s(20))


class Jpy1TemporalSprite(base.CWPySprite):
    def __init__(self, background):
        """エフェクトブースターJpy1の一時描画用スプライト。
        Jpy1の読み込みがすべて終了したら、削除される。
        """
        base.CWPySprite.__init__(self)
        # image, rect作成。
        self.image = background
        self.rect = cw.s(pygame.Rect((0, 0), cw.SIZE_AREA))

        # spritegroupに追加
        cw.cwpy.topgrp.add(self, layer=cw.LAYER_JPY_TEMPORAL)


class ClickableSprite(base.SelectableSprite):
    def __init__(self, getimage, getselimage, pos_noscale, spritegrp, lclickevent=None, rclickevent=None):
        """画面上に配置され、クリック可能なイメージ。
        """
        base.SelectableSprite.__init__(self)
        self._getimage = getimage
        self._getselimage = getselimage
        self._pos_noscale = pos_noscale
        self._lclickevent = lclickevent
        self._rclickevent = rclickevent
        self.update_scale()
        self.status = "normal"
        self.old_status = "normal"
        self.frame = 0

        # キーボードで選択する時のグループ番号
        # 0でメニューカードより後かつPCより前に選択、1でPCより後に選択
        self.clickable_group = 0

        spritegrp.add(self, layer=cw.LAYER_CLICKABLE_SPRITES)
        self.spritegrp = spritegrp

    def update_scale(self):
        self._image = self._getimage()
        self._clickedimage = pygame.transform.rotozoom(self._image, 0, 0.9)
        if self._getselimage:
            self._selimage = self._getselimage()
            self._selclickedimage = pygame.transform.rotozoom(self._selimage, 0, 0.9)
        else:
            self._selimage = cw.imageretouch.to_negative(self._image)
            self._selclickedimage = cw.imageretouch.to_negative(self._clickedimage)

        self.image = self._image
        self._rect = pygame.Rect(cw.s(self._pos_noscale), self._image.get_size())
        self._clickedrect = self._clickedimage.get_rect()
        self._clickedrect.center = self._rect.center
        self.rect = self._rect

    def get_unselectedimage(self):
        if self.status == "click":
            return self._clickedimage
        else:
            return self._image

    def get_selectedimage(self):
        if self.status == "click":
            return self._selclickedimage
        else:
            return self._selimage

    def lclick_event(self):
        """左クリックイベント。"""
        if self._lclickevent:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            self._lclickevent()

    def rclick_event(self):
        """右クリックイベント。"""
        if self._rclickevent:
            cw.cwpy.play_sound("click")
            cw.animation.animate_sprite(self, "click")
            self._rclickevent()

    def update(self, scr):
        method = getattr(self, "update_" + self.status, None)

        if method:
            method()

    def update_normal(self):
        self.update_selection()

    def update_click(self):
        """
        クリック時のアニメーションを呼び出すメソッド。
        """
        if self.frame == 0:
            self.image = self.get_selectedimage()
            self.rect = self._clickedrect
            self.status = "click"
        elif self.frame == 3:
            self.status = self.old_status
            self.image = self.get_selectedimage()
            self.rect = self._rect
            self.frame = 0
            return

        self.frame += 1

    def update_hide(self):
        """
        カードのように横幅を縮めながら非表示にする。
        """
        if self.frame >= len(cw.cwpy.setting.dealing_scales):
            self.status = "hidden"
            self.frame = 0
            return

        n = cw.cwpy.setting.dealing_scales[self.frame]
        rect = self.rect
        size = rect.w * n // 100, rect.h
        if cw.cwpy.selection == self:
            self.image = self.get_selectedimage()
        else:
            self.image = self.get_unselectedimage()

        self.image = pygame.transform.scale(self.image, size)

        # 反転表示中
        if cw.cwpy.selection == self:
            self.image = cw.imageretouch.to_negative_for_card(self.image)

        self.rect = self.image.get_rect(center=rect.center)
        self.frame += 1

    def update_delete(self):
        """
        カードのように横幅を縮めながら非表示にし、
        画面上から除去する。
        """
        self.update_hide()
        if self.status == "hidden":
            self.spritegrp.remove(self)


class NumberOfCards(base.CWPySprite):
    def __init__(self, pcard, cardtype, spritegrp):
        """カード所持枚数を表示するスプライト。
        pcard: カード所持者。
        cardtype: カード種別。
        spritegrp: 登録するSpriteGroup。cw.LAYER_NUMBER_OF_CARDSレイヤに追加される。
        """
        base.CWPySprite.__init__(self)
        self.pcard = pcard
        self.cardtype = cardtype
        self.update_scale()
        # spritegroupに追加
        spritegrp.add(self, layer=cw.LAYER_NUMBER_OF_CARDS)

    def update_scale(self):
        if self.cardtype == cw.POCKET_PERSONAL:
            num = len(self.pcard.personal_pocket)
            cap = self.pcard.get_personalpocketspace()
            font = cw.cwpy.rsrc.fonts["numcards_personal"]
        else:
            num = len(self.pcard.get_pocketcards(self.cardtype))
            cap = self.pcard.get_cardpocketspace()[self.cardtype]
            font = cw.cwpy.rsrc.fonts["numcards"]

        wl = font.size(str(num))[0]
        wm = font.size("/")[0]
        wr = font.size(str(cap))[0]
        wn = max(wl, wr)

        h = font.get_height()
        w = wn*2 + wm
        image = pygame.Surface((w, h)).convert_alpha()
        image.fill((0, 0, 0, 0))

        subimg1 = font.render(str(num), True, (0, 0, 0))
        subimg2 = font.render("/", True, (0, 0, 0))
        subimg3 = font.render(str(cap), True, (0, 0, 0))
        x = (w-subimg2.get_width()) // 2
        image.blit(subimg1, (x-subimg1.get_width(), 0))
        image.blit(subimg2, (x, 0))
        image.blit(subimg3, (x+subimg2.get_width(), 0))

        self.image = pygame.Surface((w+2, h+2)).convert_alpha()
        self.image.fill((0, 0, 0, 0))
        for x in range(3):
            for y in range(3):
                if x != 1 or y != 1:
                    self.image.blit(image, (x, y))
        image.fill((255, 255, 255, 0), special_flags=pygame.locals.BLEND_RGBA_ADD)
        self.image.blit(image, (1, 1))

        self.rect = self.image.get_rect()
        if self.cardtype == cw.POCKET_PERSONAL:
            pw, ph = cw.cwpy.rsrc.pygamedialogs["TO_PERSONAL_POCKET"].get_size()
            self.rect.top = min(self.pcard.rect.bottom - cw.s(12),
                                cw.s(cw.SIZE_AREA[1])-self.rect.height-cw.s(2))
            x = self.pcard.rect.left - cw.s(5)
            x += (pw - self.rect.width) // 2
            self.rect.left = x
        else:
            bmpw = self.pcard.rect.width
            if num:
                bmpw -= cw.cwpy.rsrc.pygamedialogs["REPLACE_CARDS"].get_width()//2
            self.rect.left = self.pcard.rect.left + bmpw//2 - self.rect.width//2
            self.rect.top = self.pcard.rect.top - (h+1) - cw.s(5)


class PriceOfCard(base.CWPySprite):
    def __init__(self, mcard, header, spritegrp):
        """カード価格を表示するスプライト。
        mcard: 「売却」カード。
        header: 対象カード。
        spritegrp: 登録するSpriteGroup。
        """
        base.CWPySprite.__init__(self)
        self.mcard = mcard
        self.header = header
        self.update_scale()
        # spritegroupに追加
        self.layer = (mcard.layer[0], mcard.layer[1], mcard.layer[2], mcard.layer[3]+1)
        spritegrp.add(self, layer=self.layer)

    def set_header(self, header):
        self.header = header
        self.update_scale()

    def update_scale(self):
        if not self.header:
            self.rect = pygame.Rect(0, 0, 0, 0)
            self.image = pygame.Surface(cw.s((0, 0))).convert()
            return

        padw = cw.s(2)
        padh = cw.s(2)
        margw = cw.s(5)
        margh = cw.s(5)

        x, y, w, h = self.mcard.rect
        font = cw.cwpy.rsrc.fonts["price"]
        s = "%s" % (self.header.sellingprice if self.header.can_selling() else "---")

        _pw, ph = font.size_withoutoverhang(s)
        maxwidth = w - margw*2

        py = y + h - ph - (margh+padh*2)

        self.rect = pygame.Rect(x+margw, py, maxwidth, ph+padh*2)
        self.image = pygame.Surface(self.rect.size).convert_alpha()
        self.image.fill((255, 255, 255, 160))

        fore = (0, 0, 0)
        back = (255, 255, 255)
        imgs = []
        for color in (fore, back):
            subimg = font.render(s, True, color)
            if self.rect.width-padw*2 < subimg.get_width():
                size = (self.rect.width-padw*2, subimg.get_height())
                subimg = cw.image.smoothscale(subimg, size)
            imgs.append(subimg)
        subimg, subimg2 = imgs

        px = (self.rect.width-subimg.get_width())//2
        for xx in range(-1, 2):
            for yy in range(-1, 2):
                if xx != x or yy != y:
                    self.image.blit(subimg2, (px+xx, padh+yy))
        self.image.blit(subimg, (px, padh))


def main():
    pass


if __name__ == "__main__":
    main()
