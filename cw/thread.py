#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import itertools
import time
import datetime
import threading
import traceback
import shutil
import re
import math
import wx
import pygame
from pygame.locals import MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP, USEREVENT

import cw
from cw.util import synclock

# build_exe.pyによって作られる一時モジュール
# cw.versioninfoからビルド時間の情報を得る
try:
    import versioninfo
except ImportError:
    versioninfo = None


class CWPyRunningError(Exception):
    pass

class _Singleton(object):
    """継承専用クラス"""
    def __new__(cls, *args, **kwargs):
        if cls is _Singleton:
            raise NotImplementedError("Can not create _Singleton instance.")
        else:
            instance = object.__new__(cls)
            cls.__new__ = classmethod(lambda cls, *args, **kwargs: instance)
            return cls.__new__(cls, *args, **kwargs)

class CWPy(_Singleton, threading.Thread):
    def __init__(self, setting, frame=None):
        if frame and not hasattr(self, "frame"):
            threading.Thread.__init__(self)
            self.rsrc = None
            self.frame = frame   # 親フレーム
            # 互換性データベース
            self.sct = cw.setting.ScenarioCompatibilityTable()
            # バージョン判定等で使用するシステムクーポン
            self.syscoupons = cw.setting.SystemCoupons()
            self.ydata = None
            self._running = False
            self.init_pygame(setting)

    def init_pygame(self, setting):
        """使用変数等はここ参照。"""
        self.setting = setting  # 設定
        self.status = "Title"
        self.update_titlebar()
        self.expand_mode = setting.expandmode # 画面拡大条件
        self.is_processing = False # シナリオ読込中か
        self.is_debuggerprocessing = False # デバッガの処理が進行中か(宿の再ロードなど)
        self.is_decompressing = False # アーカイブ展開中か

        self.update_scaling = False # 画面スケール変更中か

        # pygame初期化
        fullscreen = self.setting.is_expanded and self.setting.expandmode == "FullScreen"
        self.scr, self.scr_draw, self.scr_fullscreen, self.clock = cw.util.init(cw.SIZE_GAME, "", fullscreen, self.setting.soundfonts,
                                                                                fullscreensize=self.frame.get_displaysize())
        if fullscreen:
            self.set_fullscreen(True)
        # 背景
        self.background = None
        # ステータスバー
        self.statusbar = None
        # キー入力捕捉用インスタンス(キー入力は全てwx側で捕捉)
        self.keyevent = cw.eventrelay.KeyEventRelay()
        # Diceインスタンス(いろいろなランダム処理に使う)
        self.dice = cw.dice.Dice()
        # 宿データ
        self.ydata = None
        # シナリオデータorシステムデータ
        self.sdata = None
        # 選択中宿のパス
        self.yadodir = ""
        self.tempdir = ""
        # BattleEngineインスタンス
        self.battle = None
        # 勝利時イベント時エリアID
        self.winevent_areaid = None
        # メインループ中に各種入力イベントがあったかどうかフラグ
        self.has_inputevent = False
        # アニメーションカットフラグ
        self.cut_animation = False
        # 入力があるまでメニューカード表示を待つ
        self.wait_showcards = False
        # ダイアログ表示階層
        self._showingdlg = 0
        # カーテンスプライト表示中フラグ
        self._curtained = False
        # カードの選択可否
        self.is_pcardsselectable = False
        self.is_mcardsselectable = True
        # 現在カードの表示・非表示アニメ中フラグ
        self._dealing = False
        # カード自動配置フラグ
        self._autospread = True
        # ゲームオーバフラグ(イベント終了処理時にチェック)
        self._gameover = False
        self._forcegameover = False
        # 現在選択中スプライト(SelectableSprite)
        self.selection = None
        # Trueの間は選択中のスプライトのクリックを行えない
        self.lock_menucards = False
        # 選択中のメンバ以外の戦闘行動が表示されている時はTrue
        self._show_allselectedcards = False
        # パーティカード表示中フラグ
        self.is_showparty = False
        # バックログ表示中フラグ
        self._is_showingbacklog = False
        # カード操作用データ(CardHeader)
        self.selectedheader = None
        # デバッグモードかどうか
        self.debug = self.setting.debug
        # 選択中スキンのディレクトリ
        self.skindir = self.setting.skindir
        # 宿ロード直後であればTrue
        self._clear_changed = False
        # MusicInterfaceインスタンス
        self.music = [None] * cw.bassplayer.MAX_BGM_CHANNELS
        for i in xrange(cw.bassplayer.MAX_BGM_CHANNELS):
            self.music[i] = cw.util.MusicInterface(i, int(self.setting.vol_master*100))
        # 最後に再生した効果音(システム・シナリオの2種)
        self.lastsound_scenario = [None] * cw.bassplayer.MAX_SOUND_CHANNELS
        self.lastsound_system = None
        # EventInterfaceインスタンス
        self.event = cw.event.EventInterface()
        # Spriteグループ
        self.cardgrp = pygame.sprite.LayeredDirty()
        self.pcards = []
        self.mcards = []
        self.pricesprites = []
        self.curtains = []
        self.topgrp = pygame.sprite.LayeredDirty()
        self.backloggrp = pygame.sprite.LayeredDirty()
        self.sbargrp = pygame.sprite.LayeredDirty()
        # 使用中カード
        self.inusecards = []
        self.guardcards = []
        # 一時的に荷物袋から取り出して使用中のカード
        self.card_takenouttemporarily = None
        # エリアID
        self.areaid = 1
        # 特殊エリア移動前に保持しておく各種データ
        self.pre_areaids = []
        self.pre_mcards = []
        self.pre_dialogs = []
        # 各種入力イベント
        self.mousein = (0, 0, 0)
        self.mousepos = (-1, -1)
        self.wxmousepos = (-1, -1)
        self.mousemotion = False
        self.keyin = ()
        self.events = []
        # list, index(キーボードでのカード選択に使う)
        self.list = []
        self.index = -1
        # 方向キーやマウスホイールで選択が変更された瞬間のカーソルの位置
        self.wheelmode_cursorpos = (-1, -1)
        # メニューカードのフラグごとの辞書
        self._mcardtable = {}
        # イベント終了時にメニューカードのリストを
        # 更新する必要がある場合はTrue
        self._after_update_mcardlist = False
        # クラシックなシナリオの再生中であればそのデータ
        self.classicdata = None
        # イベントハンドラ
        self.eventhandler = cw.eventhandler.EventHandler()
        self._log_handler = None # メッセージログ表示中のハンドラ
        # 設定ダイアログのタブ位置
        self.settingtab = 0
        # 保存用のパーティ記録
        # 解散エリアに入った時点で生成される
        self._stored_partyrecord = None
        # 対象消去によってメンバの位置を再計算する必要があるか
        self._need_disposition = False
        # シナリオごとのブレークポイント情報
        self.breakpoint_table = {}
        self._load_breakpoints()
        # アニメーション中のスプライト
        self.animations = set()

        # JPDC撮影などで表示内容が変化するべきスプライト
        self.file_updates = set()
        # 背景の更新が発生しているか
        self.file_updates_bg = False

        # シナリオ選択ダイアログで選択されたシナリオ
        self.selectedscenario = None

        # アーカイヴを展開中のシナリオ
        self.expanding = u""
        # 展開の進捗情報
        self.expanding_min = 0
        self.expanding_max = 100
        self.expanding_cur = 0
        # 現在のカーソル名
        self.cursor = ""
        self.change_cursor(force=True)

        # テキストログ
        self.advlog = cw.advlog.AdventurerLogger()

        # 遅延再描画を行う場合はTrue
        self._lazy_draw = False
        # 次の描画処理で再描画するべき領域
        self._lazy_clip = None

        # 時間経過処理中か
        self._elapse_time = False
        # 強制ロード処理中か
        self._reloading = False

        # ゲーム状態を"Title"にセット
        self.exec_func(self.startup, loadyado=True)

    def set_fullscreen(self, fullscreen):
        """wx側ウィンドウのフルスクリーンモードを切り替える。"""
        def func():
            if self.frame.IsFullScreen() == fullscreen:
                return
            if sys.platform == "win32":
                self.frame.ShowFullScreen(fullscreen)
            else:
                self.frame.SetMaxSize((-1, -1))
                self.frame.SetMinSize((-1, -1))
                self.frame.ShowFullScreen(fullscreen)
                if fullscreen:
                    dsize = self.frame.get_displaysize()
                    self.frame.SetClientSize(dsize)
                    self.frame.panel.SetSize(dsize)
                    self.frame.SetMaxSize(self.frame.GetBestSize())
                    self.frame.SetMinSize(self.frame.GetBestSize())
                else:
                    self.frame.SetClientSize(cw.wins(cw.SIZE_GAME))
                    self.frame.panel.SetSize(cw.wins(cw.SIZE_GAME))
                    self.frame.SetMaxSize(self.frame.GetBestSize())
                    self.frame.SetMinSize(self.frame.GetBestSize())

        self.frame.exec_func(func)

    def set_clientsize(self, size):
        """wx側ウィンドウの表示域サイズを設定する。"""
        def func():
            if sys.platform <> "win32":
                self.frame.SetMaxSize((-1, -1))
                self.frame.SetMinSize((-1, -1))
            self.frame.SetClientSize(size)
            self.frame.panel.SetSize(size)
            if sys.platform <> "win32":
                if self.frame.IsFullScreen():
                    dsize = self.frame.get_displaysize()
                    self.frame.SetMaxSize(dsize)
                    self.frame.SetMinSize(dsize)
                else:
                    self.frame.SetMaxSize(self.frame.GetBestSize())
                    self.frame.SetMinSize(self.frame.GetBestSize())
                self.exec_func(self.draw)

        self.frame.exec_func(func)

    def _load_breakpoints(self):
        """シナリオごとのブレークポイント情報をロードする。
        """
        if not os.path.isfile("Breakpoints.xml"):
            return

        data = cw.data.xml2element("Breakpoints.xml")
        for e_sc in data:
            if e_sc.tag <> "Breakpoints":
                continue

            scenario = e_sc.get("scenario", "")
            author = e_sc.get("author", "")
            key = (scenario, author)
            bps = set()
            for e in e_sc:
                if e.tag <> "Breakpoint":
                    continue
                if e.text:
                    bps.add(e.text)
            self.breakpoint_table[key] = bps

    def _save_breakpoints(self):
        """シナリオごとのブレークポイント情報を保存する。
        """
        if isinstance(self.sdata, cw.data.ScenarioData):
            self.sdata.save_breakpoints()

        element = cw.data.make_element("AllBreakpoints")

        for key, bps in self.breakpoint_table.iteritems():
            scenario, author = key
            e_sc = cw.data.make_element("Breakpoints", attrs={"scenario":scenario,
                                                             "author":author})
            for bp in bps:
                if bp:
                    e = cw.data.make_element("Breakpoint", bp)
                    e_sc.append(e)
            if len(e_sc):
                element.append(e_sc)

        path = "Breakpoints.xml"
        if len(element):
            etree = cw.data.xml2etree(element=element)
            etree.write(path)
        elif os.path.isfile(path):
            cw.util.remove(path)

    def _init_resources(self):
        try:
            """スキンが関わるリソースの初期化"""
            self.init_fullscreenparams()

            # リソース(辞書)
            if self.rsrc:
                self.rsrc.dispose()
            rsrc = self.rsrc
            self.rsrc = None
            self.rsrc = cw.setting.Resource(self.setting)
            # システム効果音(辞書)
            self.sounds = self.rsrc.sounds
            # その他のスキン付属効果音(辞書)
            self.skinsounds = self.rsrc.skinsounds
            # システムメッセージ(辞書)
            self.msgs = self.rsrc.msgs
            # アクションカードのデータ(CardHeader)
            # スケールのみの変更ではリセットしない
            if rsrc:
                self.rsrc.actioncards = rsrc.actioncards
                self.rsrc.backpackcards = rsrc.backpackcards
            else:
                self.rsrc.actioncards = self.rsrc.get_actioncards()
                self.rsrc.backpackcards = self.rsrc.get_backpackcards()
            # 背景スプライト
            if not self.background:
                self.background = cw.sprite.background.BackGround()
            self._update_clip()
            # ステータスバースプライト
            if not self.statusbar:
                self.statusbar = cw.sprite.statusbar.StatusBar()
                # ステータスバークリップ
                self.sbargrp.set_clip(self.statusbar.rect)
            # FPS描画用フォント
            self.fpsfont = pygame.font.Font(self.rsrc.fontpaths["gothic"], cw.s(14))
            self.fpsfont.set_bold(True)

            self.update_fullscreenbackground()

            return True
        except cw.setting.NoFontError:
            def func():
                s = (u"CardWirthPyの実行に必要なフォントがありません。\n"
                     u"Data/Font以下にIPAフォントをインストールしてください。")
                wx.MessageBox(s, u"メッセージ", wx.OK|wx.ICON_ERROR, cw.cwpy.frame)
                cw.cwpy.frame.Destroy()
            cw.cwpy.frame.exec_func(func)
            return False

    def init_sounds(self):
        """スキン付属の効果音を再読込する。"""
        self.rsrc.init_sounds()
        # システム効果音(辞書)
        self.sounds = self.rsrc.sounds
        # その他のスキン付属効果音(辞書)
        self.skinsounds = self.rsrc.skinsounds

    def _update_clip(self):
        clip = pygame.Rect(cw.s((0, 0)), cw.s(cw.SIZE_AREA))
        self.cardgrp.set_clip(clip)
        self.topgrp.set_clip(clip)
        self.backloggrp.set_clip(clip)

    def update_skin(self, skindirname, changearea=True, restartop=True, afterfunc=None):
        self.file_updates.clear()
        if self.status == "Title" and restartop:
            changearea = False
            self.cardgrp.remove(self.mcards)
            self.background.bgs = []
        elif self.status == "GameOver":
            changearea = False

        changed = self.ydata and self.ydata.is_changed()
        scedir = self.setting.get_scedir()
        oldskindirname = self.setting.skindirname
        self.setting.skindirname = skindirname
        self.setting.init_skin()
        if self.ydata:
            self.ydata.set_skinname(skindirname, self.setting.skintype)
        self.skindir = self.setting.skindir
        oldskindir = cw.util.join_paths("Data/Skin", oldskindirname)
        newskindir = cw.util.join_paths("Data/Skin", skindirname)
        self.background.update_skin(oldskindir, newskindir)
        def repl_cardimg(sprite):
            if hasattr(sprite, "cardimg"):
                for path in sprite.cardimg.paths:
                    if path.path.startswith(oldskindir):
                        path.path = path.path.replace(oldskindir, newskindir)
        for sprite in self.get_pcards():
            repl_cardimg(sprite)

        if self.sdata:
            self.sdata.update_skin()

        if not self.is_battlestatus() and changearea and not (self.status == "Title" and self.topgrp.sprites()):
            for sprite in self.mcards[:]:
                if not isinstance(sprite, cw.sprite.card.FriendCard):
                    self.cardgrp.remove(sprite)
                    self.mcards.remove(sprite)
            if self.is_playingscenario():
                self.sdata.change_data(self.areaid, data=self.sdata.data)
            else:
                self.sdata.change_data(self.areaid, data=None)
            self.set_mcards(self.sdata.get_mcarddata(data=self.sdata.data), False, True, setautospread=True)
            self.deal_cards()
            if self.is_playingscenario():
                self.background.reload(doanime=False, ttype=("None", "None"), redraw=False)
            else:
                self.background.load(self.sdata.get_bgdata(), False, ("None", "None"), redraw=False)
            if not self.is_playingscenario():
                self.sdata.start_event(keynum=1)

        self.clear_selection()
        if self.rsrc:
            self.rsrc.dispose()
        self.rsrc = None

        def func():
            assert self.rsrc
            if afterfunc:
                afterfunc()

            if self.is_battlestatus() and self.battle:
                for ccard in self.get_pcards("unreversed"):
                    ccard.deck.set(ccard)
                    if self.battle.is_ready():
                        ccard.decide_action()
                for ccard in self.get_ecards("unreversed"):
                    ccard.deck.set(ccard)
                    if self.battle.is_ready():
                        ccard.decide_action()
                for ccard in self.get_fcards():
                    ccard.deck.set(ccard)
                    if self.battle.is_ready():
                        ccard.decide_action()

            self.update_titlebar()

            if scedir <> self.setting.get_scedir():
                self.setting.lastscenario = []
                self.setting.lastscenariopath = u""

            if self.ydata:
                self.ydata._changed = changed

            if self.status == "Title" and restartop:
                # タイトル画面にいる場合はロゴ表示前まで戻す
                if self.topgrp.sprites():
                    # アニメーション中なら中止してから戻す
                    self.exec_func(self.startup, loadyado=False)
                    raise cw.event.EffectBreakError()
                else:
                    self.startup(loadyado=False)
            else:
                for music in self.music:
                    music.play(music.path, updatepredata=False)

        self.update_scale(cw.UP_WIN, changearea, rsrconly=True, afterfunc=func)

    def update_yadoinitial(self):
        if not self.ydata or self.ydata.party or self.is_playingscenario():
            return
        if self.ydata.is_empty() and not self.ydata.is_changed():
            if self.areaid == 1:
                self.change_area(3)
        else:
            if self.areaid == 3:
                self.change_area(1)

    def update_titlebar(self):
        """タイトルバー文字列を更新する。"""
        self.set_titlebar(self.create_title())

    def create_title(self):
        """タイトルバー文字列を生成する。"""
        s = self.setting.titleformat
        d = self.get_titledic()
        return cw.util.format_title(s, d)

    def get_titledic(self, with_datetime=False, for_fname=False):
        """タイトルバー文字列生成用の情報を辞書で取得する。"""
        vstr = []
        for v in cw.APP_VERSION:
            vstr.append(str(v))
        vstr = u".".join(vstr)

        d = { "application":cw.APP_NAME, "skin":self.setting.skinname, "version":vstr }

        if versioninfo:
            d["build"] = versioninfo.build_datetime

        if self.ydata:
            d["yado"] = self.ydata.name
            if self.ydata.party:
                d["party"] = self.ydata.party.name

        if self.status.startswith("Scenario"):
            d["scenario"] = self.sdata.name
            d["author"] = self.sdata.author
            d["path"] = self.sdata.fpath
            d["file"] = os.path.basename(self.sdata.fpath)
            versionhint = self.sdata.get_versionhint()
            d["compatibility"] = self.sct.to_basehint(versionhint)

        if with_datetime:
            date = datetime.datetime.today()
            d["date"] = date.strftime("%Y-%m-%d")
            d["year"] = date.strftime("%Y")
            d["month"] = date.strftime("%m")
            d["day"] = date.strftime("%d")
            d["time"] = date.strftime("%H:%M:%S")
            d["hour"] = date.strftime("%H")
            d["minute"] = date.strftime("%M")
            d["second"] = date.strftime("%S")
            d["millisecond"] = date.strftime("%f")[:3]

        if for_fname:
            d2 = {}
            for key, value in d.iteritems():
                value = value.replace(" ", "_")
                value = value.replace(":", ".")
                d2[key] = cw.binary.util.check_filename(value).strip()
            return (d, d2)
        else:
            return d

    def update_scale(self, scale, changearea=True, rsrconly=False, udpatedrawsize=True,
                     displaysize=None, afterfunc=None):
        """画面の表示倍率を変更する。
        scale: 倍率。1は拡大しない。2で縦横2倍サイズの表示になる。
        """
        fullscreen = self.is_expanded() and self.setting.expandmode == "FullScreen"
        if displaysize is None and fullscreen:
            def func():
                dsize = self.frame.get_displaysize()
                def func():
                    self.update_scale(scale, changearea, rsrconly, udpatedrawsize, dsize)
                    if afterfunc:
                        afterfunc()
                self.exec_func(func)
            self.frame.exec_func(func)
            return

        self.update_scaling = True

        if self.ydata:
            changed = self.ydata.is_changed()
        else:
            changed = False

        resizewin = False
        if not rsrconly:
            cw.UP_SCR = scale
            flags = 0
            if fullscreen:
                dsize = displaysize
                self.scr_fullscreen = pygame.display.set_mode((dsize[0], dsize[1]), flags)
                self.scr = pygame.Surface(cw.s(cw.SIZE_GAME)).convert()
                self.scr_draw = self.scr
            else:
                self.scr_fullscreen = None
                self.scr = pygame.display.set_mode(cw.wins(cw.SIZE_GAME), flags)
                if cw.UP_SCR == cw.UP_WIN:
                    self.scr_draw = self.scr
                else:
                    self.scr_draw = pygame.Surface(cw.s(cw.SIZE_GAME)).convert()
                resizewin = True

        if udpatedrawsize:
            self._init_resources()

            self.statusbar.update_scale()
            self.sbargrp.set_clip(self.statusbar.rect)
            if self.sdata:
                self.sdata.update_scale()
                if self.pre_mcards:
                    mcarddata = self.sdata.get_mcarddata(self.pre_areaids[-1][0], self.pre_areaids[-1][1])
                    self.pre_mcards[-1] = self.set_mcards(mcarddata, False, False)
            self._update_clip()

            cw.sprite.message.MessageWindow.clear_selections()
            for sprite in self.cardgrp.sprites():
                if sprite.is_initialized() and not isinstance(sprite, (cw.sprite.background.BackGround,
                                                                       cw.sprite.background.BgCell))\
                                           and not isinstance(sprite, cw.sprite.background.Curtain):
                    sprite.update_scale()
            for sprite in self.topgrp.sprites():
                sprite.update_scale()
            for sprite in self.backloggrp.sprites():
                sprite.update_scale()
            for sprite in self.get_fcards():
                sprite.update_scale()

            for sprite in self.cardgrp.sprites():
                if sprite.is_initialized() and isinstance(sprite, (cw.sprite.background.BackGround,
                                                                   cw.sprite.background.BgCell))\
                                           and not isinstance(sprite, cw.sprite.background.Curtain):
                    sprite.update_scale()
            for sprite in self.cardgrp.sprites():
                if isinstance(sprite, cw.sprite.background.Curtain) and\
                        isinstance(sprite.target, cw.sprite.card.CWPyCard):
                    sprite.update_scale()

            self._update_clip()
            for music in self.music:
                music.update_scale()
        else:
            self.init_fullscreenparams()
            self.update_fullscreenbackground()
            cw.cwpy.frame.exec_func(self.rsrc.update_winscale)

        if self.ydata:
            self.ydata._changed = changed

        self.clear_selection()
        self.mousepos = (-1, -1)

        if not self.is_showingdlg():
            # 一度マウスポインタを画面外へ出さないと
            # フォーカスを失うことがある
            pos = pygame.mouse.get_pos()
            pygame.mouse.set_pos([-1, -1])
            pygame.mouse.set_pos(pos)
        self.change_cursor(self.cursor, force=True)

        self.update_scaling = False
        if udpatedrawsize and not self.background.reload_jpdcimage and self.background.has_jpdcimage:
            self.background.reload(False, ttype=(None, None))

        if afterfunc:
            afterfunc()

        if changearea:
            def func():
                self.update()
                self.draw()
            self.exec_func(func)

        if not rsrconly and not (self.setting.expandmode == "FullScreen" and self.is_expanded()):
            def func():
                self.set_clientsize(cw.wins(cw.SIZE_GAME))
            self.exec_func(func)

    def update_messagestyle(self):
        """メッセージの描画形式の変更を反映する。"""
        cw.sprite.message.MessageWindow.clear_selections()
        for sprite in itertools.chain(self.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE),
                                      self.cardgrp.get_sprites_from_layer(cw.LAYER_SPMESSAGE)):
            sprite.update_scale()
        if self._log_handler:
            self._log_handler.update_sprites(clearcache=True)

    def update_vocation120(self, vocation120):
        """適性表示を1.20に合わせる設定を変更する。"""
        if self.setting.vocation120 <> vocation120:
            self.setting.vocation120 = vocation120
            for sprite in self.cardgrp.sprites():
                if isinstance(sprite, cw.sprite.background.InuseCardImage) or\
                        (isinstance(sprite, cw.character.Character) and sprite.is_initialized() and sprite.test_aptitude):
                    sprite.update_scale()

    def update_curtainstyle(self):
        """カーテンの描画形式の変更を反映する。"""
        for sprite in itertools.chain(self.cardgrp.sprites(),
                                      self.backloggrp.sprites(),
                                      self.sbargrp.sprites()):
            if isinstance(sprite, cw.sprite.message.BacklogCurtain):
                sprite.color = self.setting.blcurtaincolour
                sprite.update_scale()
            elif isinstance(sprite, cw.sprite.background.Curtain):
                sprite.color = self.setting.curtaincolour
                sprite.update_scale()

    def set_debug(self, debug):
        self.setting.debug = debug
        self.setting.debug_saved = debug
        self.debug = debug
        self.statusbar.change(not self.is_runningevent())

        if self.is_battlestatus():
            if self.battle:
                self.battle.update_debug()
            else:
                for sprite in self.get_mcards():
                    sprite.update_scale()

        if not debug and self.is_showingdebugger():
            self.frame.exec_func(self.frame.debugger.Close)

        if not self.is_decompressing:
            cw.data.redraw_cards(debug)
        self.clear_selection()
        self.draw()

    def update_infocard(self):
        """デバッガ等から所有情報カードの変更を
        行った際に呼び出される。
        """
        self.sdata.notice_infoview = True
        showbuttons = not self.is_playingscenario() or\
            (not self.areaid in cw.AREAS_TRADE and self.areaid in cw.AREAS_SP)
        if self.is_battlestatus() and not self.battle.is_ready():
            showbuttons = False
        self.statusbar.change(showbuttons)

        if self.areaid == cw.AREA_CAMP and self.is_playingscenario():
            cw.data.redraw_cards(cw.cwpy.sdata.has_infocards())

    def run(self):
        try:
            try:
                self._run()
            except CWPyRunningError:
                self.quit()
            except wx.PyDeadObjectError:
                pass

            self._quit()
        except:
            self.is_processing = False
            self._running = False
            # エラーログを出力
            exc_type, exc_value, exc_traceback = sys.exc_info()
            vstr = []
            for v in cw.APP_VERSION:
                vstr.append(str(v))
            sys.stderr.write("Version : %s" % ".".join(vstr))
            if versioninfo:
                sys.stderr.write(" / %s" % (versioninfo.build_datetime))
            sys.stderr.write("\n")
            d = datetime.datetime.today()
            sys.stderr.write(d.strftime("DateTime: %Y-%m-%d %H:%M:%S\n"))
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
            sys.stderr.write("\n")
        finally:
            cw.util.clear_mutex()

    def _run(self):
        self._running = True

        while self._running:
            self.main_loop(True)

    def main_loop(self, update):
        if pygame.event.peek(USEREVENT):
            self.input()              # 各種入力イベント取得
            self.eventhandler.run()   # イベントを消化
        else:
            self.tick_clock()         # FPS調整
            self.input()              # 各種入力イベント取得
            self.eventhandler.run()   # イベントハンドラ
            if not pygame.event.peek(USEREVENT):
                if update:
                    self.update()         # スプライトの更新
                self.draw(True)           # スプライトの描画

        if not self.is_runningevent() and self._clear_changed:
            if self.ydata:
                self.ydata._changed = False
            self._clear_changed = False

    def quit(self):
        # トップフレームから閉じて終了。cw.frame.OnDestroy参照。
        event = wx.PyCommandEvent(wx.wxEVT_DESTROY)
        self.frame.AddPendingEvent(event)

    def quit2(self):
        self.ydata = None
        event = wx.PyCommandEvent(wx.wxEVT_CLOSE_WINDOW)
        self.frame.AddPendingEvent(event)

    def _quit(self):
        self.advlog.end_scenario(False, False)
        for music in self.music:
            music.stop()
        for i in xrange(len(self.lastsound_scenario)):
            if self.lastsound_scenario[i]:
                self.lastsound_scenario[i].stop(True)
                self.lastsound_scenario[i] = None
        if self.lastsound_system:
            self.lastsound_system.stop(False)
            self.lastsound_system = None
        pygame.quit()
        cw.util.remove_temp()
        self._save_breakpoints()
        self.setting.write()
        if self.rsrc:
            self.rsrc.clear_systemfonttable()

    def tick_clock(self, framerate=0):
        if framerate:
            self.clock.tick(framerate)
        else:
            self.clock.tick(self.setting.fps)

    def wait_frame(self, count, canskip):
        """countフレーム分待機する。"""
        self.event.eventtimer = 0
        skip = False
        for _i in xrange(count):
            if canskip:
                # リターンキー長押し, マウスボタンアップ, キーダウンで処理中断
                if self.keyevent.is_keyin(pygame.locals.K_RETURN) or self.keyevent.is_mousein():
                    skip = True
                    break

                sel = self.selection
                self.sbargrp.update(cw.cwpy.scr_draw)
                if sel <> self.selection:
                    cw.cwpy.draw(clip=self.statusbar.rect)
                breakflag = self.get_breakflag(handle_wheel=cw.cwpy.setting.can_skipwait_with_wheel)
                self.input(inputonly=True)
                self.eventhandler.run()
                if breakflag:
                    skip = True
                    break

            self.tick_clock()
        return skip

    def get_breakflag(self, handle_wheel=True):
        """待機時間を飛ばすべき入力がある場合にTrueを返す。"""
        if self.is_playingscenario() and self.sdata.in_f9:
            return True
        breakflag = False
        self.keyevent.peek_mousestate()
        events = pygame.event.get((pygame.locals.MOUSEBUTTONUP, pygame.locals.KEYUP))
        for e in events:
            if e.type in (pygame.locals.MOUSEBUTTONUP, pygame.locals.MOUSEBUTTONDOWN) and hasattr(e, "button"):
                if not handle_wheel and e.button in (4, 5):
                    # ホイールによる空白時間スキップ無効の設定
                    continue
                breakflag = True
            elif e.type == pygame.locals.KEYUP:
                if not e.key in (pygame.locals.K_F1, pygame.locals.K_F2, pygame.locals.K_F3, pygame.locals.K_F4,
                                 pygame.locals.K_F5, pygame.locals.K_F6, pygame.locals.K_F7, pygame.locals.K_F8,
                                 pygame.locals.K_F9, pygame.locals.K_F10, pygame.locals.K_F11, pygame.locals.K_F12,
                                 pygame.locals.K_F13, pygame.locals.K_F14, pygame.locals.K_F15):
                    breakflag = True
            cw.thread.post_pygameevent(e)
        return breakflag

    def get_nextevent(self):
        # BUG: 稀にbuttonのないMOUSEBUTTONUPが発生するらしい(環境による？)
        #      そのため、buttonのないマウスイベントやkeyのないキーイベントが
        #      発生していないかここでチェックし、そうしたイベントを無視する
        while True:
            if self.events:
                e = self.events[0]
                self.events = self.events[1:]
                # ---
                if e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP) and not hasattr(e, "button"):
                    continue
                elif e.type in (KEYDOWN, KEYUP) and not hasattr(e, "key"):
                    continue
                # ---
                return e
            else:
                return None

    def clear_inputevents(self):
        self.keyevent.peek_mousestate()
        pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
        events = []
        for e in self.events:
            if not e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP):
                events.append(e)
        self.events = events

    def input(self, eventclear=False, inputonly=False, noinput=False):
        if eventclear:
            self.clear_inputevents()
            return

        self.keyevent.peek_mousestate()
        self.proc_animation()

        if not self.is_showingdlg():
            if sys.platform == "win32":
                self.mousein = pygame.mouse.get_pressed()
            mousepos = self.mousepos
            if self.update_mousepos():
                # カーソルの移動を検出
                mousemotion2 = self.mousepos <> mousepos
                if self.wheelmode_cursorpos <> (-1, -1) and self.mousepos <> (-1, -1) and mousepos <> (-1, -1):
                    # 方向キーやホイールで選択を変更中は、マウスが多少ぶれても移動を検出しないようにする
                    # (元々の位置からの半径で検出)
                    ax, ay = self.wheelmode_cursorpos
                    bx, by = self.mousepos
                    self.mousemotion = self.setting.radius_notdetectmovement < abs(math.hypot(ax-bx, ay-by))
                    if self.mousemotion:
                        self.wheelmode_cursorpos = (-1, -1)
                else:
                    self.mousemotion = mousemotion2
                    self.wheelmode_cursorpos = (-1, -1)

            if self.mousemotion:
                for i in xrange(len(self.keyevent.mousein)):
                    if not self.keyevent.mousein[i] in (0, -1):
                        # マウスポインタが動いた場合は連打開始までの待ち時間を延期する
                        # (-1はすでに連打状態)
                        self.keyevent.mousein[i] = pygame.time.get_ticks()

            if self.setting.show_allselectedcards and not self.is_runningevent() and self.is_battlestatus() and self.battle.is_ready():
                # パーティ領域より上へマウスカーソルが行ったら戦闘行動表示をクリア
                if mousemotion2 and self._in_partyarea(mousepos) <> self._in_partyarea(self.mousepos):
                    self._show_allselectedcards = True
                    self.change_selection(self.selection)
                    self.draw()

            self.keyin = self.keyevent.get_pressed()

        if inputonly:
            seq = []
            for e in self.events:
                if e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP):
                    seq.append(e)
                else:
                    cw.thread.post_pygameevent(e)
            events = pygame.event.get((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
            if events:
                events = [events[-1]]
            seq.extend(events)
            del self.events[:]
            self.events.extend(seq)
        else:
            if noinput:
                seq = []
                for e in self.events:
                    if not e.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP):
                        seq.append(e)
                del self.events[:]
                self.events.extend(seq)
                pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
            self.events.extend(pygame.event.get())

    def _in_partyarea(self, mousepos):
        return cw.s(290-5) <= mousepos[1] and mousepos[1] < cw.s(cw.SIZE_AREA[1])

    def update_mousepos(self):
        if sys.platform <> "win32":
            self.mousepos = self.wxmousepos
            return True
        if pygame.mouse.get_focused() or sys.platform <> "win32":
            if self.scr_fullscreen:
                mousepos = pygame.mouse.get_pos()
                x = int((mousepos[0] - self.scr_pos[0]) / self.scr_scale)
                y = int((mousepos[1] - self.scr_pos[1]) / self.scr_scale)
                self.mousepos = (x, y)
            else:
                self.mousepos = cw.mwin2scr_s(pygame.mouse.get_pos())
        else:
            self.mousepos = (-1, -1)
        return True

    def update(self):
        # 状態の補正
        if not self.statusbar.showbuttons:
            # 通常エリアで操作可能な状態であればステータスバーのボタンを表示
            if not self.is_runningevent() and not self.areaid in cw.AREAS_TRADE and not self.selectedheader:
                self.statusbar.change()
                self.draw()

        if self.lock_menucards:
            # 操作可能であればメニューカードのロックを解除
            if not self.is_runningevent() and not self.is_showingdlg():
                self.lock_menucards = False

        cw.cwpy.frame.check_killlist()

        # 一時カードはダイアログを開き直す直前に荷物袋へ戻すが、
        # 戦闘突入等でダイアログを開き直せなかった場合はここで戻す
        self.return_takenoutcard()
        # JPDC撮影などで更新されたメニューカードと背景を更新する
        self.fix_updated_file()
        # パーティが非表示であれば表示する
        if not self.is_runningevent():
            if not self.is_showparty:
                self.show_party()

            clip = None
            if not cw.cwpy.sdata.infocards_beforeevent is None:
                for _i in filter(lambda i: not i in cw.cwpy.sdata.infocards_beforeevent,
                                 cw.cwpy.sdata.get_infocards(False)):
                    # イベント開始前には持っていなかった情報カードを入手している
                    cw.cwpy.sdata.notice_infoview = True
                    cw.cwpy.statusbar.change()
                    clip = pygame.Rect(cw.cwpy.statusbar.rect)
                    break

                clip = self.update_statusimgs(False, clip=clip)

                cw.cwpy.sdata.infocards_beforeevent = None

            if self._need_disposition:
                self.disposition_pcards()
                self.draw()
            elif clip:
                self.draw(clip=clip)

            self._reloading = False

        self.update_groups()

    def update_statusimgs(self, is_runningevent, clip=None):
        """
        キャラクターのステータス時間の表示の更新が必要であれば更新する。
        """
        if cw.cwpy.setting.show_statustime == "NotEventTime":
            clip = pygame.Rect(cw.cwpy.statusbar.rect)
            for ccard in itertools.chain(cw.cwpy.get_pcards("unreversed"), cw.cwpy.get_ecards("unreversed")):
                if ccard.is_analyzable():
                    clip2 = ccard.update_image(update_statusimg=True, is_runningevent=is_runningevent)
                    if clip2:
                        if clip:
                            clip.union_ip(clip2)
                        else:
                            clip = pygame.Rect(clip2)
        return clip

    def update_groups(self):
        self.cardgrp.update(self.scr_draw)
        self.topgrp.update(self.scr_draw)
        self.sbargrp.update(self.scr_draw)

    def return_takenoutcard(self, checkevent=True):
        # 一時的に荷物袋から出したカードを戻す(消滅していなければ)
        if self.card_takenouttemporarily and not self.selectedheader and (not checkevent or not self.is_runningevent()) and not self.is_battlestatus():
            if self.card_takenouttemporarily.get_owner():
                self.clear_inusecardimg(self.card_takenouttemporarily.get_owner())
                cw.cwpy.trade("BACKPACK", header=self.card_takenouttemporarily, from_event=False, parentdialog=None, sound=False, call_predlg=False, sort=True)
            cw.cwpy.card_takenouttemporarily = None

    def fix_updated_file(self):
        # JPDC撮影などで更新されたメニューカードと背景を更新する
        if not self.is_playingscenario() or self.is_runningevent():
            return

        if self.background.pc_cache:
            self.background.pc_cache.clear()

        if self.is_curtained():
            self.background.reload_jpdcimage = True
            return
        if self.file_updates_bg:
            self.background.reload(False)
            self.file_updates_bg = False
        elif not self.background.reload_jpdcimage and self.background.has_jpdcimage:
            self.background.reload(False, ttype=(None, None))
        self.background.reload_jpdcimage = True

        if self.file_updates:
            for mcard in self.get_mcards("visible"):
                if mcard in self.file_updates:
                    cw.animation.animate_sprite(mcard, "hide")
                    mcard.update_image()
                    cw.animation.animate_sprite(mcard, "deal")
            assert not self.file_updates # deal処理内で除去されるはず

    def proc_animation(self):
        removes = set()
        for sprite in self.animations:
            if sprite.status <> sprite.anitype:
                removes.add(sprite)
                continue # アニメーション終了

            clip = pygame.Rect(sprite.rect)
            ticks = pygame.time.get_ticks()
            if ticks < sprite.start_animation:
                sprite.start_animation = ticks
            frame = int((ticks - sprite.start_animation) / 1000.0 * 60.0)
            if frame <= sprite.frame:
                continue # フレーム進行無し
            sprite.frame = frame
            method = getattr(sprite, "update_" + sprite.status, None)
            if method:
                method()
            else:
                removes.add(sprite)
                continue # アニメーション中止
            clip.union_ip(sprite.rect)
            self.draw(clip=clip)
            if sprite.status <> sprite.anitype:
                removes.add(sprite) # アニメーション終了

        for sprite in removes:
            self.stop_animation(sprite)

    def stop_animation(self, sprite):
        if sprite in self.animations:
            sprite.anitype = ""
            sprite.start_animation = 0
            sprite.frame = 0
            self.animations.remove(sprite)

    def draw_to(self, scr, draw_desc):
        dirty_rects = cw.sprite.background.layered_draw_ex(self.cardgrp, scr)

        dirty_rects.extend(self.topgrp.draw(scr))
        dirty_rects.extend(self.backloggrp.draw(scr))
        for music in self.music:
            if music.movie_scr:
                scr.blit(music.movie_scr, (0, 0))
        clip2 = scr.get_clip()
        scr.set_clip(None)
        dirty_rects.extend(self.statusbar.layered_draw_ex(self.sbargrp, scr, draw_desc))
        scr.set_clip(clip2)

        # FPS描画
        if self.setting.showfps:
            sur = self.fpsfont.render(str(int(self.clock.get_fps())), False, (0, 255, 255))
            pos = cw.s((600, 5))
            dirty_rects.append(scr.blit(sur, pos))

        return dirty_rects

    def lazy_draw(self):
        if self._lazy_draw:
            self.draw()

    def set_lazydraw(self):
        self._lazy_draw = True

    def add_lazydraw(self, clip):
        if self._lazy_clip:
            self._lazy_clip.union_ip(clip)
        else:
            self._lazy_clip = pygame.Rect(clip)

    def draw(self, mainloop=False, clip=None):
        if not clip:
            self._lazy_draw = False
        if self.has_inputevent or not mainloop:
            # SpriteGroup描画
            # FIXME: 描画領域を絞り込むと時々カードの描画中に
            #        次に表示される背景が映り込んでしまう
            if clip:
                if self._lazy_clip:
                    clip = self._lazy_clip.union_ip(clip)
                self.scr_draw.set_clip(clip)
                self.cardgrp.set_clip(clip)
                self.topgrp.set_clip(clip)
                self.backloggrp.set_clip(clip)
                self.sbargrp.set_clip(clip)
            self._lazy_clip = None

            dirty_rects = self.draw_to(self.scr_draw, True)

            if not self.setting.smoothexpand or cw.UP_SCR % cw.UP_WIN == 0 or cw.UP_WIN % cw.UP_SCR == 0:
                scale = pygame.transform.scale
            else:
                scale = cw.image.smoothscale

            def update_clip(scale):
                clx = int(clip.left * scale) - 2
                cly = int(clip.top * scale) - 2
                clw = int(clip.width * scale) + 5
                clh = int(clip.height * scale) + 5
                return pygame.Rect(clx, cly, clw, clh)

            # 画面更新
            if self.scr_fullscreen:
                scr = scale(self.scr_draw, self.scr_size)
                if clip:
                    clip2 = update_clip(self.scr_scale)
                    clip3 = pygame.Rect(clip2.left + self.scr_pos[0], clip2.top + self.scr_pos[1], clip2.width, clip2.height)
                    self.scr_fullscreen.blit(scr, clip3.topleft, clip2)
                    pygame.display.update(clip3)
                else:
                    self.scr_fullscreen.blit(scr, self.scr_pos)
                    pygame.display.update()
            elif self.scr_draw <> self.scr:
                scr = scale(self.scr_draw, self.scr.get_size())
                if clip:
                    clip2 = update_clip(float(cw.UP_WIN) / cw.UP_SCR)
                    self.scr.blit(scr, clip2.topleft, clip2)
                    pygame.display.update(clip2)
                else:
                    self.scr.blit(scr, (0, 0))
                    pygame.display.update()
            else:
                if clip:
                    pygame.display.update(clip)
                else:
                    pygame.display.update(dirty_rects)

            pos = cw.s((0, 0))
            size = cw.s(cw.SIZE_AREA)
            self.scr_draw.set_clip(pygame.Rect(pos, size))
            self._update_clip()
            size = cw.s(cw.SIZE_GAME)
            self.sbargrp.set_clip(pygame.Rect(pos, size))

            self.event.eventtimer = 0

    def init_fullscreenparams(self):
        """フルスクリーン表示用のパラメータを計算する。"""
        if self.scr_fullscreen:
            fsize = self.scr_fullscreen.get_size()
            ssize = cw.s(cw.SIZE_GAME)
            a = float(fsize[0]) / ssize[0]
            b = float(fsize[1]) / ssize[1]
            scale = min(a, b)
            size = (int(ssize[0] * scale), int(ssize[1] * scale))
            x = (fsize[0] - size[0]) / 2
            y = (fsize[1] - size[1]) / 2
            self.scr_size = size
            self.scr_scale = scale
            self.scr_pos = (x, y)

            ssize = cw.SIZE_GAME
            a = float(fsize[0]) / ssize[0]
            b = float(fsize[1]) / ssize[1]
            scale = min(a, b)
            # FIXME: シナリオ選択ダイアログの縦幅が画面解像度を
            #        超えてしまうので若干小さめにする
            cw.UP_WIN = scale * 0.9
            cw.UP_WIN_M = scale

        else:
            self.scr_size = self.scr.get_size()
            self.scr_scale = 1.0
            self.scr_pos = (0, 0)

    def update_fullscreenbackground(self):
        if self.scr_fullscreen:
            # 壁紙
            if self.setting.fullscreenbackgroundtype == 0:
                self.scr_fullscreen.fill((0, 0, 0))
                fname = u""
            elif self.setting.fullscreenbackgroundtype == 1:
                self.scr_fullscreen.fill((255, 255, 255))
                fname = self.setting.fullscreenbackgroundfile
            elif self.setting.fullscreenbackgroundtype == 2:
                self.scr_fullscreen.fill((255, 255, 255))
                fname = self.setting.fullscreenbackgroundfile
                fname = cw.util.find_resource(cw.util.join_paths(self.skindir, fname), self.rsrc.ext_img)

            if fname:
                back = cw.util.load_image(fname, can_loaded_scaledimage=True)
                if back.get_width():
                    if self.setting.fullscreenbackgroundtype == 2:
                        back = cw.wins(back)
                    padsize = back.get_size()
                    fsize = self.scr_fullscreen.get_size()
                    for x in xrange(0, fsize[0], padsize[0]):
                        for y in xrange(0, fsize[1], padsize[1]):
                            self.scr_fullscreen.blit(back, (x, y))

            width = 16
            x = self.scr_pos[0] - width/2-1
            y = self.scr_pos[1] - width/2-1
            w = self.scr_size[0] + width+1
            h = self.scr_size[1] + width+1
            sur = pygame.Surface((w, h)).convert_alpha()
            sur.fill((255, 255, 255, 192))
            self.scr_fullscreen.blit(sur, (x, y))

    def change_cursor(self, name="arrow", force=False):
        """マウスカーソルを変更する。
        name: 変更するマウスカーソルの名前。
        (arrow, diamond, broken_x, tri_left, tri_right, mouse)"""
        if not force and self.cursor == name:
            return

        self.cursor = name

        if isinstance(self.selection, cw.sprite.statusbar.StatusBarButton):
            name = "arrow"

        if name == "arrow":
            if 2 <= cw.dpi_level:
                # 48x48
                s = (
                  "###                                             ",
                  "####                                            ",
                  "##.##                                           ",
                  "##..##                                          ",
                  "##...##                                         ",
                  "##....##                                        ",
                  "##.....##                                       ",
                  "##......##                                      ",
                  "##.......##                                     ",
                  "##........##                                    ",
                  "##.........##                                   ",
                  "##..........##                                  ",
                  "##...........##                                 ",
                  "##............##                                ",
                  "##.............##                               ",
                  "##..............##                              ",
                  "##...............##                             ",
                  "##................##                            ",
                  "##.................##                           ",
                  "##..................##                          ",
                  "##...................##                         ",
                  "##....................##                        ",
                  "##...........############                       ",
                  "##...........#############                      ",
                  "##.......##...##                                ",
                  "##......###...##                                ",
                  "##.....#####...##                               ",
                  "##....### ##...##                               ",
                  "##...###   ##...##                              ",
                  "##..###    ##...##                              ",
                  "##.###      ##...##                             ",
                  "#####       ##...##                             ",
                  "####         ##...##                            ",
                  "###          ##...##                            ",
                  "##            ##...##                           ",
                  "              ##..###                           ",
                  "               #####                            ",
                  "               ###                              ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",
                  "                                                ",)
            else:
                # 24x24
                s = (
                  "##                      ",
                  "#.#                     ",
                  "#..#                    ",
                  "#...#                   ",
                  "#....#                  ",
                  "#.....#                 ",
                  "#......#                ",
                  "#.......#               ",
                  "#........#              ",
                  "#.........#             ",
                  "#..........#            ",
                  "#......#####            ",
                  "#...#..#                ",
                  "#.####..#               ",
                  "##   #..#               ",
                  "      #..#              ",
                  "      #..#              ",
                  "       #.#              ",
                  "       ##               ",
                  "                        ",
                  "                        ",
                  "                        ",
                  "                        ",
                  "                        ",)

            if self.setting.cursor_type == cw.setting.CURSOR_WHITE:
                cursor = pygame.cursors.compile(s, "#", ".", "o")
            else:
                cursor = pygame.cursors.compile(s, ".", "#", "o")
            pygame.mouse.set_cursor((len(s[0]), len(s)), (0, 0), *cursor)
            #pygame.mouse.set_cursor(*pygame.cursors.arrow)
        elif name == "diamond":
            pygame.mouse.set_cursor(*pygame.cursors.diamond)
        elif name == "broken_x":
            pygame.mouse.set_cursor(*pygame.cursors.broken_x)
        elif name == "tri_left":
            pygame.mouse.set_cursor(*pygame.cursors.tri_left)
        elif name == "tri_right":
            pygame.mouse.set_cursor(*pygame.cursors.tri_right)
        elif name == "mouse":
            if 2 <= cw.dpi_level:
                # 48x48
                s = (
                  "          ##..##  ####################          ",
                  "          ##..##  ####################          ",
                  "          ##..##  ##................##          ",
                  "          ##..##  ##................##          ",
                  "          ##..##  ##........##......##          ",
                  "          ##..##  ##.......###......##          ",
                  "     ################.....###.......##          ",
                  "   ####################...##........##          ",
                  "  ####......##......####............##          ",
                  " ###........##........###...........##          ",
                  " ##.........##.........##...#####...##          ",
                  "###.........##.........###..#####...##          ",
                  "##..........##..........##..........##          ",
                  "##..........##..........##..........##          ",
                  "##..........##..........##..#####...##          ",
                  "##..........##..........##..#####...##          ",
                  "##..........##..........##..........##          ",
                  "##..........##..........##..........##          ",
                  "##..........##..........##..........##          ",
                  "##..........##..........##..........##          ",
                  "##########################..........##          ",
                  "############..############..........##          ",
                  "##......................##..........##          ",
                  "##......................##..........##          ",
                  "##......................##..........##          ",
                  "##......................##..........##          ",
                  "##......................##..........##          ",
                  "##......................##..........##          ",
                  "##......................##############          ",
                  "##......................##############          ",
                  "##......................##                      ",
                  "##......................##                      ",
                  "###....................###                      ",
                  " ##....................##                       ",
                  " ###..................###                       ",
                  "  ###................###                        ",
                  "    ###################   ###### ####   #####   ",
                  "   ####################  ############  ######   ",
                  "  ##.....###..##  ##..####.....###..# ##..##    ",
                  " ##.......##..##  ##..###.......##..###..##     ",
                  "##...#######..##  ##..##...#######..##..##      ",
                  "##..########..##  ##..##..########.....##       ",
                  "##..########..######..##..########..##..##      ",
                  "##...#######..######..##...#######..###..##     ",
                  " ##.......##......##..###.......##..# ##..##    ",
                  "  ##.....###......##..####.....###..#  ##..##   ",
                  "   ####################  ############   #####   ",
                  "    ###### ############   ###### ####    ####   ",)
                point = (14, 14)
            else:
                # 24x24
                s = (
                  "     #.# ##########     ",
                  "     #.# #........#     ",
                  "     #.# #....#...#     ",
                  "  #########..#....#     ",
                  " #....#....#......#     ",
                  "#.....#.....#.##..#     ",
                  "#.....#.....#.....#     ",
                  "#.....#.....#.##..#     ",
                  "#.....#.....#.....#     ",
                  "#.....#.....#.....#     ",
                  "######.######.....#     ",
                  "#...........#.....#     ",
                  "#...........#.....#     ",
                  "#...........#.....#     ",
                  "#...........#######     ",
                  "#...........#           ",
                  "#...........#           ",
                  " #.........#            ",
                  "  ########## ### #  #   ",
                  " #...#.# #.##...#.##.#  ",
                  "#.####.# #.#.####...#   ",
                  "#.####.###.#.####.#.#   ",
                  " #...#...#.##...#.##.#  ",
                  "  #########  ### #  #   ",)
                point = (7, 7)

            if self.setting.cursor_type == cw.setting.CURSOR_WHITE:
                cursor = pygame.cursors.compile(s, "#", ".", "o")
            else:
                cursor = pygame.cursors.compile(s, ".", "#", "o")
            pygame.mouse.set_cursor((len(s[0]), len(s)), point, *cursor)

        if not force:
            # FIXME: 一度マウスポインタを移動しないと変更されない
            pos = pygame.mouse.get_pos()
            x = pos[0] - 1 if 0 < pos[0] else pos[0] + 1
            y = pos[1] - 1 if 0 < pos[1] else pos[1] + 1
            pygame.mouse.set_pos(x, y)
            pygame.mouse.set_pos(pos)

    def call_dlg(self, name, **kwargs):
        """ダイアログを開く。
        name: ダイアログ名。cw.frame参照。
        """
        stack = self._showingdlg
        self.lock_menucards = True
        self.input(eventclear=True)
        self._showingdlg += 1
        self.statusbar.clear_volumebar()
        if isinstance(self.selection, cw.sprite.statusbar.StatusBarButton):
            # 表示が乱れる場合があるので
            # ステータスバーのボタンからフォーカスを外しておく
            self.mousepos = (-1, -1)
        self.keyevent.clear() # キー入力初期化
        event = wx.PyCommandEvent(self.frame.dlgeventtypes[name])
        event.args = kwargs
        if threading.currentThread() == self:
            self.draw()
            def func():
                self.frame.app.SetCallFilterEvent(True)
            self.frame.exec_func(func)
            self.frame.AddPendingEvent(event)
            if sys.platform == "win32":
                while self.is_running() and self.frame.IsEnabled() and stack < self._showingdlg:
                    pass
        else:
            self.frame.app.SetCallFilterEvent(True)
            self.frame.ProcessEvent(event)

    def call_modaldlg(self, name, **kwargs):
        """ダイアログを開き、閉じるまで待機する。
        name: ダイアログ名。cw.frame参照。
        """
        stack = self._showingdlg
        self.call_dlg(name, **kwargs)

        if threading.currentThread() == self:
            while self.is_running() and stack < self._showingdlg:
                self.main_loop(False)

    def call_predlg(self):
        """直前に開いていたダイアログを再び開く。"""
        self.return_takenoutcard(checkevent=False)
        if self.pre_dialogs:
            pre_info = self.pre_dialogs[-1]
            callname = pre_info[0]

            if 0 <= self.areaid and self.is_playingscenario() and callname in ("CARDPOCKET", "CARDPOCKETB"):
                # ゲームオーバーになった場合は開かない
                if cw.cwpy.is_gameover():
                    self.pre_dialogs.pop()
                    return

                # 手札カードダイアログの選択者が行動不能か
                # 対象消去されている場合は開かない
                index2 = pre_info[1]
                if isinstance(index2, cw.character.Character) and\
                        (index2.is_vanished() or ((not index2.is_active() and not self.areaid in cw.AREAS_TRADE))):
                    self.pre_dialogs.pop()
                    self.lock_menucards = False
                    return

            self.update_statusimgs(is_runningevent=False)
            self.call_modaldlg(callname)

        else:
            self.lock_menucards = False

    def kill_showingdlg(self):
        self._showingdlg -= 1
        if self._showingdlg <= 0:
            self.frame.app.SetCallFilterEvent(False)
            if not self.is_runningevent():
                self.exec_func(self.clear_selection)

    def exec_func(self, func, *args, **kwargs):
        """CWPyスレッドで指定したファンクションを実行する。
        func: 実行したいファンクションオブジェクト。
        """
        event = pygame.event.Event(pygame.USEREVENT, func=func, args=args,
                                                                kwargs=kwargs)
        post_pygameevent(event)

    def sync_exec(self, func, *args, **kwargs):
        """CWPyスレッドで指定したファンクションを実行し、
        終了を待ち合わせる。ファンクションの戻り値を返す。
        func: 実行したいファンクションオブジェクト。
        """
        if threading.currentThread() == self:
            return func(*args, **kwargs)
        else:
            result = [None]
            class Running(object):
                def __init__(self):
                    self.isrun = True
            running = Running()
            def func2(running, result, func, *args, **kwargs):
                result[0] = func(*args, **kwargs)
                running.isrun = False
            self.exec_func(func2, running, result, func, *args, **kwargs)
            while running.isrun and self.frame.IsEnabled() and self.is_running():
                time.sleep(0.001)
            return result[0]

    def set_expanded(self, flag, expandmode="", force=False, displaysize=None):
        """拡大表示する。すでに拡大表示されている場合は解除する。
        flag: Trueなら拡大表示、Falseなら解除。
        """
        if not force and self.is_expanded() == flag:
            return

        if not expandmode:
            expandmode = self.expand_mode if self.is_expanded() else self.setting.expandmode

        if displaysize is None and expandmode == "FullScreen" and flag:
            def func():
                dsize = self.frame.get_displaysize()
                self.exec_func(self.set_expanded, flag, expandmode, force, dsize)
            self.frame.exec_func(func)
            return

        updatedrawsize = force or self.setting.expanddrawing <> 1

        if expandmode == "None":
            if force:
                self.set_fullscreen(False)
                self.expand_mode = "None"
                self.setting.is_expanded = False
                cw.UP_WIN = 1
                cw.UP_WIN_M = cw.UP_WIN
                self.update_scale(1, True, False, updatedrawsize)
                self.clear_inputevents()
            else:
                return

        elif expandmode == "FullScreen":
            # フルスクリーン
            if self.is_showingdebugger() and flag:
                self.play_sound("error")
                s = u"デバッガ表示中はフルスクリーン化できません。"
                self.call_modaldlg("MESSAGE", text=s)
            else:
                pos = pygame.mouse.get_pos()
                pygame.mouse.set_pos([-1, -1])

                self.setting.is_expanded = flag
                if flag:
                    assert not displaysize is None
                    self.expand_mode = expandmode
                    dsize = displaysize
                    self.scr_fullscreen = pygame.display.set_mode((dsize[0], dsize[1]), 0)
                    self.scr = pygame.Surface(cw.s(cw.SIZE_GAME)).convert()
                    self.scr_draw = self.scr
                    self.set_fullscreen(True)
                    self.update_scale(self.setting.expanddrawing, True, False, updatedrawsize)
                else:
                    cw.UP_WIN = 1
                    cw.UP_WIN_M = cw.UP_WIN
                    self.expand_mode = "None"
                    self.scr_fullscreen = None
                    self.scr = pygame.display.set_mode(cw.wins(cw.SIZE_GAME), 0)
                    self.scr_draw = self.scr
                    self.set_fullscreen(False)
                    self.update_scale(1, True, False, updatedrawsize)

                while not self.frame.IsFullScreen() == flag:
                    pass

                # 一度マウスポインタを画面外へ出さないと
                # フォーカスを失うことがある
                pygame.mouse.set_pos(pos)
                self.clear_inputevents()

        else:
            # 拡大
            try:
                def func():
                    self.set_fullscreen(False)
                self.frame.exec_func(func)
                scale = float(expandmode)
                scale = max(scale, 0.5)
                self.setting.is_expanded = flag
                if flag:
                    self.expand_mode = expandmode
                    cw.UP_WIN = scale
                    cw.UP_WIN_M = cw.UP_WIN
                    self.update_scale(self.setting.expanddrawing, True, False, updatedrawsize)
                else:
                    self.expand_mode = "None"
                    cw.UP_WIN = 1
                    cw.UP_WIN_M = cw.UP_WIN
                    self.update_scale(1, True, False, updatedrawsize)
                self.clear_inputevents()

            except Exception:
                cw.util.print_ex()

        self.has_inputevent = True

    def show_message(self, mwin):
        """MessageWindowを表示し、次コンテントのindexを返す。
        mwin: MessageWindowインスタンス。
        """
        eventhandler = cw.eventhandler.EventHandlerForMessageWindow(mwin)
        self.clear_selection()
        locks = self.lock_menucards
        self.lock_menucards = False

        if self.is_showingdebugger() and self.event and self.event.is_stepexec():
            self.event.refresh_tools()

        self.event.refresh_activeitem()
        self.input()
        while self.is_running() and mwin.result is None:
            self.update()

            if mwin.result is None:
                self.input()
                self.draw(not mwin.is_drawing or self.has_inputevent)

            self.tick_clock()
            self.input()
            eventhandler.run()

        self.clear_selection()
        self.lock_menucards = locks

        # バックログの保存
        if self.is_playingscenario() and self.setting.backlogmax and isinstance(mwin.result, int) and\
                not isinstance(mwin, cw.sprite.message.MemberSelectWindow):
            if self.setting.backlogmax <= len(self.sdata.backlog):
                self.sdata.backlog.pop(0)
            self.sdata.backlog.append(cw.sprite.message.BacklogData(mwin))

        self.advlog.show_message(mwin)

        self.statusbar.change(False)

        # cwpylist, index 初期化
        self.list = self.get_mcards("visible")
        self.index = -1
        # スプライト削除
        seq = []
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_MESSAGE))
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_SPMESSAGE))
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_1))
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_1))
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_2))
        seq.extend(self.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_2))
        seq.extend(self.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE))

        # 互換性マーク削除
        if self.is_playingscenario():
            self.sdata.set_versionhint(cw.HINT_MESSAGE, None)

        # 次のアニメーションの前に再描画を行う
        for sprite in seq:
            self.add_lazydraw(sprite.rect)
        self.set_lazydraw()

        # メッセージ表示中にシナリオ強制終了(F9)などを行った場合、
        # イベント強制終了用のエラーを送出する。
        if isinstance(mwin.result, Exception):
            raise mwin.result
        else:
            return mwin.result

    def has_backlog(self):
        """表示可能なメッセージログがあるか。"""
        return bool(self.sdata.backlog)

    def show_backlog(self, n=0):
        """直近から過去に遡ってn回目のメッセージを表示する。
        n: 遡る量。0なら最後に閉じたメッセージ。
        もっとも古いメッセージよりも大きな値の場合は
        もっとも古いメッセージを表示する。
        """
        if not self.has_backlog():
            return

        length = len(self.sdata.backlog)
        if length <= n:
            n = length - 1
        index = length - 1 - n

        eventhandler = cw.eventhandler.EventHandlerForBacklog(self.sdata.backlog, index)
        cursor = self.cursor
        self.change_cursor()
        self._log_handler = eventhandler
        try:
            while self.is_running() and eventhandler.is_showing() and\
                    cw.cwpy.sdata.is_playing and self._is_showingbacklog:
                self.sbargrp.update(self.scr_draw)
                if self.has_inputevent:
                    self.draw()
                self.tick_clock()
                self.input()
                eventhandler.run()
                if len(self.sdata.backlog) < length:
                    # 最大数の設定変更によりログ数が減った場合
                    if not self.sdata.backlog:
                        break
                    eventhandler.index -= length - len(self.sdata.backlog)
                    length = len(self.sdata.backlog)
                    if eventhandler.index < 0:
                        eventhandler.index = 0
                    eventhandler.update_sprites()
        finally:
            self._log_handler = None
            self.change_cursor(cursor)
            # 表示終了
            eventhandler.exit_backlog(playsound=False)

    def set_backlogmax(self, backlogmax):
        """メッセージログの最大数を設定する。
        """
        self.setting.backlogmax = backlogmax
        if not self.has_backlog():
            return
        if backlogmax < len(self.sdata.backlog):
            del self.sdata.backlog[0:len(self.sdata.backlog)-backlogmax]

    def set_titlebar(self, s):
        """タイトルバーテキストを設定する。
        s: タイトルバーテキスト。
        """
        self.frame.exec_func(self.frame.SetTitle, s)

    def get_yesnoresult(self):
        """call_yesno()の戻り値を取得する。"""
        return self._yesnoresult

#-------------------------------------------------------------------------------
# ゲーム状態遷移用メソッド
#-------------------------------------------------------------------------------

    def set_status(self, name):
        isbattle = "ScenarioBattle" in (name, self.status)
        quickhide = (self.setting.all_quickdeal and not isbattle)
        self.status = name
        self.hide_cards(True, quickhide=quickhide)
        self.pre_areaids = []
        self.pre_dialogs = []
        self.pre_mcards = []

    def startup(self, loadyado=True):
        """起動時のアニメーションを表示してから
        タイトル画面へ遷移する。"""
        resdir = cw.util.join_paths(cw.cwpy.skindir, u"Resource/Image/Other")
        seq = []
        for event in self.events:
            if event.type == pygame.locals.USEREVENT:
                seq.append(event)
        self.events = seq
        self.cut_animation = False
        self.wait_showcards = False

        # 必要なスプライトの読み込み
        if not self._init_resources():
            self._running = False
            return

        for music in self.music:
            music.stop()

        optyado = cw.OPTIONS.yado
        cw.OPTIONS.yado = ""
        if not optyado and self.setting.startupscene == cw.setting.OPEN_LAST_BASE and loadyado:
            optyado = self.setting.lastyado
            cw.OPTIONS.party = ""
            cw.OPTIONS.scenario = ""

        if optyado:
            if os.path.isabs(optyado):
                optyado = cw.util.relpath(optyado, u"Yado")
            optyado = cw.util.join_paths(u"Yado", optyado)
            env = cw.util.join_paths(optyado, "Environment.xml")
            if os.path.isfile(env):
                self.set_status("Title")
                self._init_attrs()
                if self.load_yado(optyado):
                    return
                else:
                    name = cw.header.GetName(env).name
                    s = u"「%s」は他の起動で使用中です。" % (name)
                    self.call_modaldlg("MESSAGE", text=s)

        # 起動オプションでの宿の指定に失敗した場合は
        # これらのオプションは無効
        cw.OPTIONS.party = ""
        cw.OPTIONS.scenario = ""

        self.sdata = cw.data.SystemData()
        self.statusbar.change()

        try:
            fpath = cw.util.join_paths(self.skindir, u"Resource/Xml/Animation/Opening.xml")
            anime = cw.sprite.animationcell.AnimationCell(fpath, cw.SIZE_AREA, (0, 0), self.topgrp, "title")
            self.draw()
            cw.animation.animate_sprite(anime, "animation", clearevent=False)

            # スプライトを解除する
            self.topgrp.remove_sprites_of_layer("title")

            if self.cut_animation:
                ttype = ("Default", "Default")
                self.cut_animation = False
            else:
                ttype = ("None", "None")
                self.wait_showcards = True
            self.set_title(ttype=ttype)

        except cw.event.EffectBreakError:
            # 他のスキンへの切り替えなどで中止
            self.topgrp.remove_sprites_of_layer("title")

    def set_title(self, init=True, ttype=("Default", "Default")):
        """タイトル画面へ遷移。"""
        del self.pre_dialogs[:]
        del self.pre_areaids[:]
        self.set_status("Title")
        self._init_attrs()
        self.update_titlebar()
        self.statusbar.change()
        self.change_area(1, ttype=ttype)

    def _init_attrs(self):
        for i in xrange(len(self.lastsound_scenario)):
            if self.lastsound_scenario[i]:
                self.lastsound_scenario[i].stop(True)
                self.lastsound_scenario[i] = None
        cw.util.remove_temp()
        self.yadodir = ""
        self.tempdir = ""
        self.setting.scenario_narrow = ""
        self.setting.lastscenario = []
        self.setting.lastscenariopath = ""
        self.ydata = None
        self.sdata = cw.data.SystemData()
        cw.tempdir = cw.tempdir_init
        cw.util.release_mutex()

    def set_yado(self):
        """宿画面へ遷移。"""
        self.set_status("Yado")
        msglog = self.sdata.backlog
        self.sdata = cw.data.SystemData()
        self.sdata.backlog = msglog
        self.update_titlebar()
        # 冒険の中断やF9時のためにカーテン消去
        self.clear_curtain()
        self.statusbar.change()

        if self.ydata.party:
            # パーティを選択中
            areaid = 2
            self.ydata.party.remove_numbercoupon()
            for pcard in self.get_pcards():
                pcard.clear_action()

            # 全員対象消去による戦闘の敗北から
            # シナリオクリアへ直結した場合の処置
            if not self.ydata.party.members:
                self.dissolve_party()
                areaid = 1

        elif not self.ydata.is_empty() or self.ydata.is_changed():
            # パーティを選択中でない
            areaid = 1
        else:
            # 初期状態
            areaid = 3

        def change_area():
            self.change_area(areaid)
            self.is_pcardsselectable = self.ydata and self.ydata.party

        if self.ydata.skindirname <> cw.cwpy.setting.skindirname:
            self.update_skin(self.ydata.skindirname, changearea=False, afterfunc=change_area)
        else:
            change_area()

    def start_scenario(self):
        """
        シナリオ選択ダイアログで選択されたシナリオがあればスタートする。
        """
        if self.selectedscenario:
            self.set_scenario(self.selectedscenario, manualstart=True)
            self.selectedscenario = None

    def set_scenario(self, header=None, lastscenario=[][:], lastscenariopath="",
                     resume=False, manualstart=False):
        """シナリオ画面へ遷移。
        header: ScenarioHeader
        """
        if self.battle:
            # バトルエリア解除の時
            self.is_processing = True
        self.set_status("Scenario")
        self.battle = None

        if self.ydata.skindirname <> cw.cwpy.setting.skindirname:
            def func():
                self._set_scenario_impl(header, lastscenario, lastscenariopath, resume, manualstart)
            self.update_skin(self.ydata.skindirname, changearea=False, afterfunc=func)
        else:
            self._set_scenario_impl(header, lastscenario, lastscenariopath, resume, manualstart)

    def _set_scenario_impl(self, header, lastscenario, lastscenariopath, resume, manualstart):
        if header and not isinstance(self.sdata, cw.data.ScenarioData):
            def load_failure(showerror):
                # 読込失敗(帰還)
                self.is_processing = False
                if showerror:
                    s = u"シナリオの読み込みに失敗しました。"
                    self.call_modaldlg("ERROR", text=s)
                if isinstance(self.sdata, cw.data.ScenarioData):
                    self.sdata.end()
                self.set_yado()
                if self.is_showingdebugger() and self.event:
                    self.event.refresh_variablelist()
            try:
                self.sdata = cw.data.ScenarioData(header)
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                self.statusbar.change(False)
                loaded, musicpaths = self.sdata.set_log()
                self.sdata.start()
                self.update_titlebar()
                areaid = self.sdata.startid
                if lastscenario or lastscenariopath:
                    self.ydata.party.set_lastscenario(lastscenario, lastscenariopath)

                if not loaded:
                    self.ydata.party.set_numbercoupon()

                def func(loaded, musicpaths, areaid):
                    self.is_processing = False
                    quickdeal = resume and self.setting.all_quickdeal
                    try:
                        name = self.sdata.get_areaname(self.sdata.startid)
                        if name is None:
                            if resume:
                                # 再開時に読込失敗
                                load_failure(True)
                                return
                            # 開始エリアが存在しない(帰還)
                            s = u"シナリオに開始エリアが設定されていません。"
                            self.call_modaldlg("ERROR", text=s)
                            self.check_level(True)
                            self.sdata.end()
                            self.set_yado()
                            return

                        if manualstart:
                            dataversion = self.sdata.summary.getattr(".", "dataVersion", "")
                            if not dataversion in cw.SUPPORTED_WSN:
                                s = u"対応していないWSNバージョン(%s)のシナリオです。\n正常に動作しない可能性がありますが、開始しますか？" % (dataversion)
                                self.call_modaldlg("YESNO", text=s)
                                if self.get_yesnoresult() <> wx.ID_OK:
                                    self.sdata.end()
                                    self.set_yado()
                                    return

                        if not resume:
                            for pcard in self.get_pcards():
                                pcard.set_fullrecovery()
                                pcard.update_image()

                        if musicpaths:
                            for i, (musicpath, _subvolume, _loopcount, inusecard) in enumerate(musicpaths):
                                music = self.music[i]
                                if music.path <> music.get_path(musicpath, inusecard):
                                    music.stop()

                        self.change_area(areaid, not loaded, loaded, quickdeal=quickdeal, doanime=not resume)

                        if musicpaths:
                            for i, (musicpath, subvolume, loopcount, inusecard) in enumerate(musicpaths):
                                music = self.music[i]
                                music.play(musicpath, subvolume=subvolume, loopcount=loopcount, inusecard=inusecard)

                        if self.is_showingdebugger() and self.event:
                            self.event.refresh_variablelist()

                        if not self.setting.lastscenariopath:
                            self.setting.lastscenariopath = header.get_fpath()

                    except:
                        # 読込失敗(帰還)
                        cw.util.print_ex()
                        self.exec_func(load_failure, True)
                self.clear_inputevents()
                self.exec_func(func, loaded, musicpaths, areaid)
            except cw.event.EffectBreakError:
                # 手動で中止
                if not self.is_runningstatus():
                    return
                self.exec_func(load_failure, False)
            except:
                if not self.is_runningstatus():
                    return
                # 読込失敗(帰還)
                cw.util.print_ex()
                self.exec_func(load_failure, True)
        elif self.is_processing:
            self.statusbar.change(False)
            self.is_processing = False

        self.is_pcardsselectable = self.ydata and self.ydata.party

    def set_battle(self):
        """シナリオ戦闘画面へ遷移。"""
        self.set_status("ScenarioBattle")

    def set_gameover(self):
        """ゲームオーバー画面へ遷移。"""
        cw.cwpy.sdata.in_endprocess = True

        cw.cwpy.advlog.gameover()
        self.set_status("GameOver")
        del self.pre_dialogs[:]
        del self.pre_areaids[:]
        self._gameover = False
        self._forcegameover = False
        self.battle = None
        self.card_takenouttemporarily = None
        self.clear_inputevents()
        pygame.event.clear()
        self.hide_party()
        if self._need_disposition:
            self.disposition_pcards()
        self.ydata.party.lost()
        del self.sdata.friendcards[:]
        self.sdata.end()

        for music in self.music:
            music.stop()
        for i in xrange(len(self.lastsound_scenario)):
            if self.lastsound_scenario[i]:
                self.lastsound_scenario[i].stop(True)
                self.lastsound_scenario[i] = None

        self.ydata.load_party(None)
        msglog = self.sdata.backlog
        self.sdata = cw.data.SystemData()
        self.sdata.backlog = msglog
        self.update_titlebar()
        self.statusbar.change()
        self.change_area(1, nocheckvisible=True)

    def set_gameoverstatus(self, gameover, force=True):
        """パーティの状態に係わらず
        現状のゲームオーバー状態を設定する。
        """
        self._gameover = gameover
        if force:
            self._forcegameover = gameover

    def f9(self, load_failure=False):
        """cw.data.ScenarioDataのf9()から呼び出され、
        緊急避難処理の続きを行う。
        """
        if load_failure == False and not self.is_playingscenario():
            return
        if self.sdata.in_endprocess:
            return

        self.clean_specials()
        def func():
            if cw.cwpy.is_runningevent():
                self.exec_func(self._f9impl)
                raise cw.event.EffectBreakError()
            else:
                self._f9impl()
        self.exec_func(func)

    def _f9impl(self, startotherscenario=False):
        if self.sdata.in_endprocess:
            return

        self.sdata.in_endprocess = True

        cw.cwpy.advlog.f9()
        self.sdata.is_playing = False
        self.statusbar.change(False)
        self.pre_dialogs = []

        self.clear_inusecardimg()
        self.clear_guardcardimg()
        self.statusbar.change(False)
        self.draw(clip=self.statusbar.rect)
        self.return_takenoutcard(checkevent=False)

        # 対象選択画面でF9しても、中止ボタンを宿まで持ち越さないように
        self.selectedheader = None

        # 特殊文字の辞書が変更されていたら、元に戻す
        if self.rsrc.specialchars_is_changed:
            self.rsrc.specialchars = self.rsrc.get_specialchars()

        # battle
        if self.battle and self.battle.is_running:
            # バトルを強制終了
            self.battle.end(True, True)
            self.battle = None

        # party copy
        fname = os.path.basename(self.ydata.party.data.fpath)
        dname = os.path.basename(os.path.dirname(self.ydata.party.data.fpath))
        path = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party", fname)
        dstpath = cw.util.join_paths(self.ydata.tempdir, "Party", dname, fname)
        dpath = os.path.dirname(dstpath)

        if not os.path.isdir(dpath):
            os.makedirs(dpath)

        shutil.copy2(path, dstpath)
        # member copy
        dpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members")

        for name in os.listdir(dpath):
            path = cw.util.join_paths(dpath, name)

            if os.path.isfile(path) and path.endswith(".xml"):
                dstpath = cw.util.join_paths(self.ydata.tempdir,
                                                        "Adventurer", name)

                dstdir = os.path.dirname(dstpath)

                if not os.path.isdir(dstdir):
                    os.makedirs(dstdir)

                shutil.copy2(path, dstpath)

        # ゴシップ復元を無効にするモード(互換動作)でなければ
        # 追加されたゴシップを削除し、削除されたゴシップを追加し直す
        if not cw.cwpy.sct.disable_gossiprestration(self.sdata.get_versionhint(cw.HINT_SCENARIO)):
            # gossips
            for key, value in self.sdata.gossips.iteritems():
                if value:
                    self.ydata.remove_gossip(key)
                else:
                    self.ydata.set_gossip(key)

        # 終了印復元を無効にするモード(互換動作)でなければ
        # 追加された終了印を削除し、削除された終了印を追加し直す
        if not cw.cwpy.sct.disable_compstamprestration(self.sdata.get_versionhint(cw.HINT_SCENARIO)):
            # completestamps
            for key, value in self.sdata.compstamps.iteritems():
                if value:
                    self.ydata.remove_compstamp(key)
                else:
                    self.ydata.set_compstamp(key)

        # scenario
        self.ydata.party.set_lastscenario([], u"")

        # members
        self.ydata.party.data = cw.data.yadoxml2etree(self.ydata.party.data.fpath)
        self.ydata.party.reload()

        # 荷物袋のデータを戻す
        path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Backpack.xml")
        etree = cw.data.xml2etree(path)
        backpacktable = {}
        yadodir = self.ydata.party.get_yadodir()
        tempdir = self.ydata.party.get_tempdir()

        for header in itertools.chain(self.ydata.party.backpack, self.ydata.party.backpack_moved):
            if header.scenariocard:
                header.contain_xml()
                header.remove_importedmaterials()
                continue

            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, tempdir)
            fpath = cw.util.join_paths(fpath)
            backpacktable[fpath] = header

        self.ydata.party.backpack = []
        self.ydata.party.backpack_moved = []

        for i, e in enumerate(etree.getfind(".")):
            try:
                header = backpacktable[e.text]
                del backpacktable[e.text]
                if header.moved <> 0:
                    # 削除フラグを除去
                    # 荷物袋から移動された場合は使用されている
                    # 可能性があるので上書き
                    if header.carddata is None:
                        etree = cw.data.yadoxml2etree(header.fpath)
                        etree.remove("Property", attrname="moved")
                        etree.write_xml()
                    else:
                        etree = cw.data.yadoxml2etree(path=header.fpath)
                        etree.remove("Property", attrname="moved")
                        header2 = cw.header.CardHeader(carddata=etree.getroot())
                        header2.fpath = header.fpath
                        header2.write()
                        header = header2
                    header.moved = 0
                self.ydata.party.backpack.append(header)
                header.order = i
                header.set_owner("BACKPACK")
                # 荷物袋にある場合はcarddata無し、特殊技能の使用回数無し
                header.carddata = None
                if header.type == "SkillCard":
                    header.maxuselimit = 0
                    header.uselimit = 0
            except Exception:
                cw.util.print_ex()

        # 一度荷物袋から取り出されてから戻された
        # カードはbackpacktableに残る
        for fpath, header in backpacktable.iteritems():
            cw.cwpy.ydata.deletedpaths.add(header.fpath)

        if not self.areaid >= 0:
            self.areaid = self.pre_areaids[0][0]

        # スプライトを作り直す
        pcards = self.get_pcards()
        showparty = bool(self.pcards)
        if showparty:
            for music in self.music:
                music.stop()

        logpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face/Log.xml")
        if os.path.isfile(logpath):
            elog = cw.data.xml2etree(logpath)
        else:
            elog = None

        for idx, data in enumerate(self.ydata.party.members):
            if idx < len(pcards):
                pcard = pcards[idx]
                self.cardgrp.remove(pcard)
                self.pcards.remove(pcard)

            pos_noscale = (95 * idx + 9 * (idx + 1), 285)
            pcard = cw.sprite.card.PlayerCard(data, pos_noscale=pos_noscale, status="normal", index=idx)

            # カード画像が変更されているPCは戻す
            if not elog is None:
                name = os.path.splitext(os.path.basename(data.fpath))[0]

                for eimg in elog.getfind(".", raiseerror=False):
                    if eimg.get("member", "") == name:
                        prop = data.find("Property")
                        for ename in ("ImagePath", "ImagePaths"):
                            e = prop.find(ename)
                            if not e is None:
                                prop.remove(e)

                        if eimg.tag == "ImagePath":
                            # 旧バージョン(～0.12.3)
                            fname = eimg.get("path", "")
                            if fname:
                                face = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face", fname)
                            else:
                                face = ""
                            # 変更後のイメージを削除するためにここで再設定する
                            # (set_images()内で削除される)
                            prop.append(cw.data.make_element("ImagePath", eimg.text))
                            if os.path.isfile(face):
                                postype = eimg.get("positiontype", "Default")
                                pcard.set_images([cw.image.ImageInfo(face, postype=postype)])
                            else:
                                pcard.set_images([])
                        elif eimg.tag == "ImagePaths":
                            # 新バージョン(複数イメージ対応後)
                            seq = cw.image.get_imageinfos(eimg)
                            for info in seq:
                                info.path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face", info.path)
                            # 変更後のイメージを削除するためにここで再設定する
                            # (set_images()内で削除される)
                            e = cw.data.make_element("ImagePaths")
                            prop.append(e)
                            for e2 in eimg:
                                if e2.tag == "NewImagePath":
                                    e.append(cw.data.make_element("ImagePath", e2.text))
                            pcard.set_images(seq)
                        break

            pcard.set_pos_noscale(pos_noscale)
            pcard.set_fullrecovery()
            pcard.update_image()

        self.sdata.remove_log(None)

        self.ydata.party._loading = False

        if not self.is_showparty:
            self._show_party()

        for music in self.music:
            music.stop()
        for i in xrange(len(self.lastsound_scenario)):
            if self.lastsound_scenario[i]:
                self.lastsound_scenario[i].stop(True)
                self.lastsound_scenario[i] = None
        if self.lastsound_system:
            self.lastsound_system.stop(False)
            self.lastsound_system = None

        if not startotherscenario:
            self.set_yado()

    def reload_yado(self):
        """現在の宿をロード。"""
        # イベントを中止
        self.event._stoped = True
        self.event.breakwait = True
        self.lock_menucards = True
        self._reloading = True
        del self.pre_dialogs[:]
        del self.pre_areaids[:]

        def return_title():
            def func():
                for i in xrange(len(self.lastsound_scenario)):
                    if self.lastsound_scenario[i]:
                        self.lastsound_scenario[i].stop(True)
                        self.lastsound_scenario[i] = None
                self.set_status("Title")
                self.sdata = cw.data.SystemData()
                cw.util.remove_temp()
                self.load_yado(self.yadodir, createmutex=False)
                def func():
                    def func():
                        self.is_debuggerprocessing = False
                        if self.is_showingdebugger() and self.event:
                            self.event.refresh_tools()
                    self.frame.exec_func(func)
                    self.lock_menucards = False
                self.exec_func(func)
            self.exec_func(func)

        def init_resources():
            self.event.clear()
            self._init_resources()

            self.frame.exec_func(return_title)

        def end_scenario():
            # シナリオを強制終了
            if self.is_playingscenario():
                self.sdata.end()

            self.exec_func(init_resources)

            if self.is_decompressing:
                raise cw.event.EffectBreakError()

        def func1():
            if self.is_showingmessage():
                mwin = self.get_messagewindow()
                mwin.result = cw.event.EffectBreakError()
                self.event._stoped = True
            elif self.is_runningevent():
                self.event._stoped = True
            self.sdata.is_playing = False

            # バトルを強制終了
            if self.battle and self.battle.is_running:
                self.battle.end(True, True)

            self.exec_func(end_scenario)

        self.exec_func(func1)

    def load_yado(self, yadodir, createmutex=True):
        """指定されたディレクトリの宿をロード。"""
        try:
            return self._load_yado(yadodir, createmutex)
        except Exception, ex:
            cw.util.print_ex(file=sys.stderr)
            cw.tempdir = cw.tempdir_init
            self.yadodir = ""
            self.tempdir = ""
            self.setting.scenario_narrow = ""
            self.setting.lastscenario = []
            self.setting.lastscenariopath = ""
            self.ydata = None
            self.sdata = cw.data.SystemData()
            raise ex

    def _load_yado(self, yadodir, createmutex):
        if createmutex:
            if cw.util.create_mutex(u"Yado"):
                if cw.util.create_mutex(yadodir):
                    try:
                        cw.tempdir = cw.util.join_paths(u"Data/Temp/Local", yadodir)
                        return self._load_yado2(yadodir)
                    finally:
                        cw.util.release_mutex(-2)
                else:
                    cw.util.release_mutex()
                    cw.cwpy.play_sound("error")
                    return False
            else:
                cw.cwpy.play_sound("error")
                return False
        else:
            return self._load_yado2(yadodir)

    def _load_yado2(self, yadodir):
        del self.pre_dialogs[:]
        del self.pre_areaids[:]

        optscenario = cw.OPTIONS.scenario
        cw.OPTIONS.scenario = ""

        yadodirname = os.path.basename(yadodir)
        self.yadodir = yadodir.replace("\\", "/")
        self.tempdir = self.yadodir.replace("Yado", cw.util.join_paths(cw.tempdir, u"Yado"), 1)
        for music in self.music:
            music.stop()
        for i in xrange(len(self.lastsound_scenario)):
            if self.lastsound_scenario[i]:
                self.lastsound_scenario[i].stop(True)
                self.lastsound_scenario[i] = None
        self.ydata = cw.data.YadoData(self.yadodir, self.tempdir)
        self.setting.lastyado = yadodirname

        if self.ydata.party:
            header = self.ydata.party.get_sceheader()

            if optscenario:
                if os.path.isabs(optscenario):
                    scedir = optscenario
                else:
                    scedir = cw.cwpy.setting.get_scedir()
                    scedir = cw.util.join_paths(scedir, optscenario)
                db = cw.scenariodb.Scenariodb()
                header2 = db.search_path(scedir)
                db.close()
                if header2:
                    if header:
                        scepath1 = header.get_fpath()
                        scepath1 = os.path.normcase(os.path.normpath(os.path.abspath(scepath1)))
                        scepath2 = header2.get_fpath()
                        scepath2 = os.path.normcase(os.path.normpath(os.path.abspath(scepath2)))
                        if header and scepath1 <> scepath2:
                            self.sdata.set_log()
                            self.ydata.party.lastscenario = []
                            self.ydata.party.lastscenariopath = optscenario
                            self.setting.lastscenario = []
                            self.setting.lastscenariopath = optscenario
                            self._f9impl(startotherscenario=True)
                    else:
                        for idx, data in enumerate(self.ydata.party.members):
                            pos_noscale = (95 * idx + 9 * (idx + 1), 285)
                            pcard = cw.sprite.card.PlayerCard(data, pos_noscale=pos_noscale, status="normal", index=idx)
                            pcard.set_pos_noscale(pos_noscale)
                            pcard.set_fullrecovery()
                            pcard.update_image()
                        self.ydata.party._loading = False
                        self.ydata.party.lastscenario = []
                        self.ydata.party.lastscenariopath = optscenario
                        self.setting.lastscenario = []
                        self.setting.lastscenariopath = optscenario
                        self._show_party()
                    header = header2

            # シナリオプレイ途中から再開
            if header:
                self.exec_func(self.set_scenario, header, resume=True)
            # シナリオロードに失敗
            elif self.ydata.party.is_adventuring():
                self.play_sound("error")
                s = (cw.cwpy.msgs["load_scenario_failure"])
                self.call_modaldlg("YESNO", text=s)

                if self.get_yesnoresult() == wx.ID_OK:
                    self.exec_func(self.sdata.set_log)
                    self.exec_func(self.f9, True)
                else:
                    self.exec_func(self.ydata.load_party, None)
                    self.exec_func(self.set_yado)
            else:
                self.exec_func(self.set_yado)

            if self.is_showingdebugger():
                func = self.frame.debugger.refresh_tools
                self.frame.exec_func(func)

        else:
            self.exec_func(self.set_yado)

        self._clear_changed = True
        return True

#-------------------------------------------------------------------------------
# エリアチェンジ関係メソッド
#-------------------------------------------------------------------------------

    def deal_cards(self, quickdeal=False, updatelist=True, flag="", startbattle=False):
        """hidden状態のMenuCard(対応フラグがFalseだったら表示しない)と
        PlayerCardを全て表示する。
        quickdeal: 全カードを同時に表示する。
        """
        if not (self.setting.quickdeal or self.setting.all_quickdeal):
            quickdeal = False
        self._dealing = True

        if self.is_autospread():
            mcardsinv = self.get_mcards("invisible")
        else:
            mcardsinv = self.get_mcards("invisible", flag=flag)

        # エネミーカードは初期化されていない場合がある
        for mcard in mcardsinv[:]:
            if isinstance(mcard, cw.sprite.card.EnemyCard):
                if mcard.is_flagtrue():
                    if not mcard.initialize():
                        mcardsinv.remove(mcard)

        # カード自動配置の配置位置を再設定する
        if self.is_autospread():
            mcards = self.get_mcards("flagtrue")
            flag = bool(self.areaid == cw.AREA_CAMP and self.sdata.friendcards)
            if self.is_battlestatus():
                self.set_autospread(mcards, 6, flag, anime=False)
            else:
                self.set_autospread(mcards, 7, flag, anime=False)

        deals = []
        for mcard in mcardsinv:
            if mcard.is_flagtrue():
                if quickdeal:
                    deals.append(mcard)
                else:
                    cw.animation.animate_sprite(mcard, "deal")
                    if self.is_playingscenario() and self.sdata.in_f9:
                        # カード描画中にF9された場合はここへ来る
                        return

        if deals and quickdeal:
            cw.animation.animate_sprites(deals, "deal")

        # list, indexセット
        if updatelist:
            self._update_mcardlist()
        else:
            self._after_update_mcardlist = True

        self.input(True)
        self._dealing = False
        self.wait_showcards = False

    def hide_cards(self, hideall=False, hideparty=True, quickhide=False, updatelist=True, flag=""):
        """
        カードを非表示にする(表示中だったカードはhidden状態になる)。
        各カードのhidecards()の最後に呼ばれる。
        hideallがTrueだった場合、全てのカードを非表示にする。
        """
        if not (self.setting.quickdeal or self.setting.all_quickdeal):
            quickhide = False
        self._dealing = True
        if updatelist:
            # 選択を解除する
            self.clear_selection()

        # メニューカードを下げる
        if self.is_autospread():
            mcards = self.get_mcards("visible")
        else:
            mcards = self.get_mcards("visible", flag=flag)
        hide = False
        for mcard in mcards:
            if hideall or not mcard.is_flagtrue():
                if mcard.inusecardimg:
                    self.clear_inusecardimg(mcard)
                if quickhide:
                    hide = True
                else:
                    cw.animation.animate_sprite(mcard, "hide")
                if isinstance(mcard, cw.character.Character):
                    mcard.clear_action()
        if hide:
            cw.animation.animate_sprites(mcards, "hide")

        # プレイヤカードを下げる
        if self.ydata and hideparty:
            if not self.ydata.party or self.ydata.party.is_loading():
                self.draw(clip=self.statusbar.rect)
                self.hide_party()

        # list, indexセット
        if updatelist:
            self._update_mcardlist()
        else:
            self._after_update_mcardlist = True

        self.input(True)
        self._dealing = False

    def vanished_card(self, mcard):
        """mcardの対象消去を通知する。"""
        if isinstance(mcard, (cw.sprite.card.MenuCard, cw.sprite.card.EnemyCard)) and mcard.flag:
            seq = self._mcardtable.get(mcard.flag, [])
            if seq and mcard in seq:
                seq.remove(mcard)
                if not seq:
                    del self._mcardtable[mcard.flag]

        if isinstance(mcard, cw.sprite.card.PlayerCard):
            self._need_disposition = True

    def update_mcardlist(self):
        """必要であればメニューカードのリストを更新する。
        """
        if self._after_update_mcardlist:
            self._update_mcardlist()

    def _update_mcardlist(self):
        self._mcardtable = {}
        mcards = self.get_mcards()
        visible = []
        for mcard in mcards:
            if mcard.status <> "hidden":
                visible.append(mcard)
            if mcard.flag:
                seq = self._mcardtable.get(mcard.flag, [])
                seq.append(mcard)
                if len(seq) == 1:
                    self._mcardtable[mcard.flag] = seq
        if not self.is_showingmessage():
            self.list = visible
            self.index = -1

    def update_pcimage(self, pcnumber, deal):
        if not self.file_updates_bg or deal:
            for bgtype, d in self.background.bgs:
                if bgtype == cw.sprite.background.BG_PC:
                    bgpcnumber = d[0]
                    if bgpcnumber == pcnumber:
                        if deal:
                            self.background.reload(False)
                        else:
                            self.file_updates_bg = True
                        break

        updates = []
        pcards = self.get_pcards()
        pcard = pcards[pcnumber-1] if pcnumber-1 < len(pcards) else None
        for mcard in self.get_mcards():
            if not mcard.is_initialized():
                continue
            imgpaths = []
            can_loaded_scaledimages = []
            can_loaded_scaledimage = pcard.data.getbool(".", "scaledimage", False) if pcard else True
            update = False
            for i, info in enumerate(mcard.cardimg.paths):
                # PC画像を更新
                if info.pcnumber == pcnumber:
                    if pcard:
                        for base in pcard.imgpaths:
                            imgpaths.append(cw.image.ImageInfo(base.path, pcnumber, info.base, basecardtype="LargeCard"))
                            can_loaded_scaledimages.append(can_loaded_scaledimage)
                    else:
                        imgpaths.append(cw.image.ImageInfo(pcnumber=pcnumber, base=info.base, basecardtype="LargeCard"))
                        can_loaded_scaledimages.append(False)
                    update = True
                else:
                    imgpaths.append(info)
                    if isinstance(mcard.cardimg.can_loaded_scaledimage, (list, tuple)):
                        can_loaded_scaledimages.append(mcard.cardimg.can_loaded_scaledimage[i])
                    else:
                        assert isinstance(mcard.cardimg.can_loaded_scaledimage, bool)
                        can_loaded_scaledimages.append(mcard.cardimg.can_loaded_scaledimage)
            if not update:
                continue
            mcard.cardimg.paths = imgpaths
            mcard.cardimg.can_loaded_scaledimage = can_loaded_scaledimages
            mcard.cardimg.clear_cache()
            updates.append(mcard)
        if deal:
            if cw.cwpy.setting.all_quickdeal:
                cw.animation.animate_sprites(updates, "hide")
                for mcard in updates:
                    mcard.update_image()
                cw.animation.animate_sprites(updates, "deal")
            else:
                for mcard in updates:
                    cw.animation.animate_sprite(mcard, "hide")
                    mcard.cardimg.clear_cache()
                    mcard.update_image()
                    cw.animation.animate_sprite(mcard, "deal")
        return updates

    def show_party(self):
        """非表示のPlayerCardを再表示にする。"""
        pcards = [i for i in self.get_pcards() if i.status == "hidden"]

        if pcards:
            seq = []
            for pcard in pcards:
                if pcard.inusecardimg and not pcard.inusecardimg.center:
                    seq.append(pcard.inusecardimg)
            cw.animation.animate_sprites(pcards + seq, "shiftup")

        self._show_party()

    def _show_party(self):
        self.is_showparty = True
        self.input(True)
        self.event.refresh_showpartytools()

    def hide_party(self):
        """PlayerCardを非表示にする。"""
        pcards = [i for i in self.get_pcards() if not i.status == "hidden"]

        if pcards:
            seq = []
            for pcard in pcards:
                if pcard.inusecardimg and not pcard.inusecardimg.center:
                    seq.append(pcard.inusecardimg)
            cw.animation.animate_sprites(pcards + seq, "shiftdown")

        self.is_showparty = False
        self.selection = None
        self.input(True)
        self.event.refresh_showpartytools()

    def set_pcards(self):
        # プレイヤカードスプライト作成
        if self.ydata and self.ydata.party and not self.get_pcards():
            for idx, e in enumerate(self.ydata.party.members):
                pos_noscale = 95 * idx + 9 * (idx + 1), 285
                cw.sprite.card.PlayerCard(e, pos_noscale=pos_noscale, index=idx)

            # 番号クーポン設定
            self.ydata.party._loading = False

    def set_sprites(self, dealanime=True,
                    bginhrt=False, ttype=("Default", "Default"),
                    doanime=True, data=None,
                    nocheckvisible=False):
        """エリアにスプライトをセットする。
        bginhrt: Trueの時は背景継承。
        """
        # メニューカードスプライトグループの中身を削除
        self.cardgrp.remove(self.mcards)
        self.mcards = []
        self.file_updates.clear()

        # プレイヤカードスプライトグループの中身を削除
        if self.ydata:
            if not self.ydata.party or self.ydata.party.is_loading():
                self.cardgrp.remove(self.pcards)
                self.pcards = []

        # 背景スプライト作成
        if not bginhrt:
            self.background.load(self.sdata.get_bgdata(), doanime, ttype, nocheckvisible=nocheckvisible)

        # 特殊エリア(キャンプ・メンバー解散)だったら背景にカーテンを追加。
        if self.areaid in (cw.AREA_CAMP, cw.AREA_BREAKUP):
            self.set_curtain(curtain_all=True)

        # メニューカードスプライト作成
        self.set_mcards(self.sdata.get_mcarddata(data=data), dealanime)

        # プレイヤカードスプライト作成
        self.set_pcards()

        # キャンプ画面のときはFriendCardもスプライトグループに追加
        if self.areaid == cw.AREA_CAMP:
            self.add_fcardsprites(status="hidden")

    def add_fcardsprites(self, status, alpha=None):
        """cardgrpに同行NPCのスプライトを追加する。"""
        seq = list(enumerate(self.get_fcards()))
        for index, fcard in reversed(seq):
            index = 5 - index
            pos = (95 * index + 9 * (index + 1), 5)
            fcard.set_pos_noscale(pos)
            fcard.status = status
            fcard.set_alpha(alpha)
            if fcard.status == "hidden":
                fcard.clear_image()
                fcard.layer = (cw.LAYER_FCARDS_T, cw.LTYPE_FCARDS, fcard.index, 0)
                self.cardgrp.add(fcard, layer=fcard.layer)
                self.mcards.append(fcard)
            else:
                fcard.layer = (cw.LAYER_FCARDS_T, cw.LTYPE_FCARDS, fcard.index, 0)
                self.cardgrp.add(fcard, layer=fcard.layer)
                self.mcards.append(fcard)
                if not alpha is None:
                    fcard.update_image()
                fcard.deal()
        self.list = self.get_mcards("visible")
        self.index = -1

    def clear_fcardsprites(self):
        """cardgrpから同行NPCのスプライトを取り除く。"""
        fcards = []
        for fcard in self.mcards[:]:
            if isinstance(fcard, cw.character.Friend):
                fcard.set_alpha(None)
                fcard.hide()
                fcards.append(fcard)
                self.mcards.remove(fcard)
        self.cardgrp.remove(fcards)
        self.list = self.get_mcards("visible")
        self.index = -1

    def set_autospread(self, mcards, maxcol, campwithfriend=False, anime=False):
        """自動整列設定時のメニューカードの配置位置を設定する。
        mcards: MenuCard or EnemyCardのリスト。
        maxcol: この値を超えると改行する。
        campwithfriend: キャンプ画面時＆FriendCardが存在しているかどうか。
        anime: カードを一旦消去してから再配置するならTrue。
        """
        def get_size_noscale(mcard):
            assert hasattr(mcard, "cardimg")

            if isinstance(mcard.cardimg, cw.image.CharacterCardImage) or\
               isinstance(mcard.cardimg, cw.image.LargeCardImage):
                return cw.setting.get_resourcesize("CardBg/LARGE")
            elif isinstance(mcard.cardimg, cw.image.CardImage):
                return cw.setting.get_resourcesize("CardBg/NORMAL")
            else:
                assert False

        def set_mcardpos_noscale(mcards, (maxw, maxh), y):
            n = maxw + 5
            x = (632 - n * len(mcards) + 5) / 2

            for mcard in mcards:
                w, h = get_size_noscale(mcard)
                mcard.set_pos_noscale((x + maxw - w, y + maxh - h))
                x += n

        maxw = 0
        maxh = 0

        for mcard in mcards:
            w, h = get_size_noscale(mcard)

            maxw = max(w, maxw)
            maxh = max(h, maxh)

            if anime:
                cw.animation.animate_sprite(mcard, "hide")

        n = len(mcards)

        if campwithfriend:
            y = (145 - maxh) / 2 + 140 - 2
            set_mcardpos_noscale(mcards, (maxw, maxh), y)
        elif n <= maxcol:
            y = (285 - maxh) / 2 - 2
            set_mcardpos_noscale(mcards, (maxw, maxh), y)
        else:
            y = (285 - 10 - maxh * 2) / 2
            y2 = y + maxh + 5
            p = n / 2 + n % 2
            set_mcardpos_noscale(mcards[:p], (maxw, maxh), y)
            set_mcardpos_noscale(mcards[p:], (maxw, maxh), y2)

        if anime:
            for mcard in mcards:
                cw.animation.animate_sprite(mcard, "deal")

        if self.battle:
            self.battle.numenemy = len(cw.cwpy.get_mcards("flagtrue"))

    def set_mcards(self, (stype, elements), dealanime=True, addgroup=True, setautospread=True):
        """メニューカードスプライトを構成する。
        生成されたカードのlistを返す。
        (stype, elements): (spreadtype, MenuCardElementのリスト)のタプル
        dealanime: True時はカードを最初から表示している。
        addgroup: True時は現在の画面に即時反映する。
        """
        # カードの並びがAutoの時
        if stype == "Auto":
            autospread = True
        else:
            autospread = False

        if setautospread:
            self._autospread = autospread

        status = "hidden" if dealanime else "normal"
        seq = []

        for i, e in enumerate(elements):
            if stype == "Auto":
                pos_noscale = (0, 0)
            else:
                left = e.getint("Property/Location", "left")
                top = e.getint("Property/Location", "top")
                pos_noscale = (left, top)

            status2 = status
            if status2 <> "hidden":
                if not cw.sprite.card.CWPyCard.is_flagtrue_static(e):
                    status2 = "hidden"

            if e.tag == "EnemyCard":
                if self.sdata.get_castname(e.getint("Property/Id", -1)) is None:
                    continue
                mcard = cw.sprite.card.EnemyCard(e, pos_noscale, status2, addgroup, i)
            else:
                mcard = cw.sprite.card.MenuCard(e, pos_noscale, status2, addgroup, i)

            if not mcard.is_flagtrue():
                mcard.status = "hidden"

            seq.append(mcard)

        return seq

    def disposition_pcards(self):
        """プレイヤーカードの位置を補正する。
        対象消去が発生した場合や解散直後に適用。
        """
        if self.ydata and self.ydata.party:
            # キャンセル可能な対象消去状態だったメンバを完全に消去する(互換動作)
            for pcard in self.ydata.party.vanished_pcards:
                pcard.commit_vanish()
            self.ydata.party.vanished_pcards = []

        for index, pcard in enumerate(self.get_pcards()):
            x = 9 + 95 * index + 9 * index
            y = pcard._pos_noscale[1]
            pcard.get_baserect()[0] = cw.s(x)
            y2 = pcard.rect.top
            size = pcard.rect.size
            baserect = pcard.get_baserect()
            if pcard.rect.size == (0, 0):
                pcard.rect.size = baserect.size
            pcard.rect.center = baserect.center
            pcard.rect.top = y2
            pcard.cardimg.rect[0] = cw.s(x)
            pcard._pos_noscale = (x, y)
            pcard.rect.size = size
            for i, t in enumerate(pcard.zoomimgs):
                img, rect = t
                rect.center = pcard.rect.center
                pcard.zoomimgs[i] = (img, rect)
        self._need_disposition = False

    def change_area(self, areaid, eventstarting=True,
                          bginhrt=False, ttype=("Default", "Default"),
                          quickdeal=False, specialarea=False, startbattle=False,
                          doanime=True, data=None, nocheckvisible=False,
                          clear_curtain=False):
        """ゲームエリアチェンジ。
        eventstarting: Falseならエリアイベントは起動しない。
        bginhrt: 背景継承を行うかどうかのbool値。
        ttype: トランジション効果のデータのタプル((効果名, 速度))
        """
        if self.ydata and not self.is_playingscenario():
            oldchanged = self.ydata.is_changed()
        else:
            oldchanged = True

        # 宿にいる時は常に高速切替有効
        if self.setting.all_quickdeal and not self.is_playingscenario():
            quickdeal = True

        # デバッガ等で強制的にエリア移動するときは特殊エリアを解除する
        if not specialarea:
            self.clean_specials()

        # 背景継承を行うかどうかのbool値
        bginhrt |= bool(self.areaid < 0 and self.areaid <> cw.AREA_BREAKUP)
        oldareaid = self.areaid
        self.areaid = areaid
        if not self.sdata.change_data(areaid, data=data):
            raise cw.event.EffectBreakError()
        bginhrt |= bool(self.areaid < 0)
        if self.sdata.in_f9:
            self.hide_cards(True, quickhide=quickdeal)
        else:
            self.hide_cards(True, quickhide=quickdeal)
            if clear_curtain:
                self.clear_curtain()
            self.set_sprites(bginhrt=bginhrt, ttype=ttype, doanime=doanime, data=data,
                             nocheckvisible=nocheckvisible)

        if not self.is_playingscenario() and not self.is_showparty:
            # 宿にいる場合は常に全回復状態にする
            for pcard in self.get_pcards():
                pcard.set_fullrecovery()
                pcard.update_image()

        if not self.is_playingscenario():
            self.disposition_pcards()

        if 0 <= oldareaid and self.ydata and self.is_playingscenario():
            self.ydata.changed()

        # エリアイベントを開始(特殊エリアからの帰還だったら開始しない)
        if eventstarting and oldareaid >= 0:
            if not self.wait_showcards:
                self.deal_cards(quickdeal=quickdeal, startbattle=startbattle)
            else:
                self.draw()

            if self.is_playingscenario() and self.sdata.in_f9:
                # カード描画中にF9された場合はここへ来る
                return

            if self.areaid >= 0 and self.status == "Scenario":
                self.elapse_time()

            if self._need_disposition:
                self.disposition_pcards()
                self.draw()

            self.sdata.start_event(keynum=1)
        elif not self.sdata.in_f9:
            self.deal_cards(quickdeal=quickdeal, startbattle=startbattle)
            if not startbattle and not pygame.event.peek(pygame.locals.USEREVENT):
                self.show_party()

            if self._need_disposition:
                self.disposition_pcards()
                self.draw()

        if self.ydata and not self.is_playingscenario():
            self.ydata._changed = oldchanged

    def change_battlearea(self, areaid):
        """
        指定するIDの戦闘を開始する。
        """
        data = self.sdata.get_resdata(True, areaid)
        if data is None:
            raise cw.event.EffectBreakError()

        # 対象選択中であれば中止
        self.lock_menucards = True
        self.clean_specials()

        self.play_sound("battle", from_scenario=True, material_override=True)
        self.statusbar.change(False, encounter=True)

        path = data.gettext("Property/MusicPath", "")
        volume = data.getint("Property/MusicPath", "volume", 100)
        loopcount = data.getint("Property/MusicPath", "loopcount", 0)
        channel = data.getint("Property/MusicPath", "channel", 0)
        fade = data.getint("Property/MusicPath", "fadein", 0)

        music = self.music[channel]

        # 戦闘開始アニメーション
        sprite = cw.sprite.background.BattleCardImage()
        cw.animation.animate_sprite(sprite, "battlestart")
        oldareaid = self.areaid
        oldbgmpath = (music.path, music.subvolume, music.loopcount, channel)
        if self.sdata.pre_battleareadata:
            oldareaid = self.sdata.pre_battleareadata[0]
            oldbgmpath = self.sdata.pre_battleareadata[1]

        # 戦闘音楽を流す
        music.play(path, subvolume=volume, loopcount=loopcount, fade=fade)

        self.set_battle()
        self.change_area(areaid, False, bginhrt=True, ttype=("None", "Default"), startbattle=True)
        cw.animation.animate_sprite(sprite, "hide")
        sprite.remove(cw.cwpy.cardgrp)

        self.sdata.pre_battleareadata = (oldareaid, oldbgmpath, (music.path, music.subvolume, music.loopcount, music.channel))
        cw.battle.BattleEngine()
        self.lock_menucards = False

    def clear_battlearea(self, areachange=True, eventkeynum=0, startnextbattle=False, is_battlestarting=False):
        """戦闘状態を解除して戦闘前のエリアに戻る。
        areachangeがFalseだったら、戦闘前のエリアには戻らない
        (戦闘イベントで、エリア移動コンテント等が発動した時用)。
        """
        if not cw.cwpy.is_playingscenario():
            cw.cwpy.battle = None
            return

        if self.status == "ScenarioBattle":
            if isinstance(self.event.get_selectedmember(), cw.character.Enemy):
                self.event.clear_selectedmember()

            # 勝利イベントを保持しておく
            battleevents = self.sdata.events
            if eventkeynum:
                self.winevent_areaid = self.areaid

            cw.cwpy.battle = None

            for pcard in self.get_pcards():
                pcard.deck.clear(pcard)
                pcard.remove_timedcoupons(True)

            for fcard in self.get_fcards():
                fcard.deck.clear(fcard)
                fcard.remove_timedcoupons(True)

            areaid, bgmpath, _battlebgmpath = self.sdata.pre_battleareadata
            if not startnextbattle:
                self.sdata.pre_battleareadata = None
            self.set_scenario()

            # BGMを最後に指定されたものに戻す
            self.music[bgmpath[3]].play(bgmpath[0], subvolume=bgmpath[1], loopcount=bgmpath[2])

            # 一部ステータスは回復
            for pcard in self.get_pcards():
                if pcard.is_bind() or pcard.mentality <> "Normal":
                    if pcard.status == "hidden":
                        pcard.set_bind(0)
                        pcard.set_mentality("Normal", 0)
                        pcard.update_image()
                    else:
                        self.play_sound("harvest")
                        pcard.set_bind(0)
                        pcard.set_mentality("Normal", 0)
                        cw.animation.animate_sprite(pcard, "hide", battlespeed=True)
                        pcard.update_image()
                        cw.animation.animate_sprite(pcard, "deal", battlespeed=True)

            if (areachange or (startnextbattle and not is_battlestarting)) and not eventkeynum == 3 and not cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint()):
                # 勝利・逃走成功時に時間経過
                # 戦闘中のエリア移動・敗北イベント・1.20以下は時間経過しない
                self.elapse_time()
                if self.is_gameover():
                    self.set_gameover()
                    return

            # NPCの状態を回復
            self.sdata.fullrecovery_fcards()

            if areachange:
                # 戦闘前のエリアに戻る
                self.change_area(areaid, False, ttype=("None", "Default"), bginhrt=True)

            if eventkeynum:
                # 勝利イベント開始
                self.event.clear_selectedmember()
                battleevents.start(keynum=eventkeynum)
                self.winevent_areaid = None

    def change_specialarea(self, areaid):
        """特殊エリア(エリアIDが負の数)に移動する。"""
        updatestatusbar = True
        if areaid < 0:
            self.pre_areaids.append((self.areaid, self.sdata.data))

            # パーティ解散・キャンプエリア移動の場合はエリアチェンジ
            if areaid in (cw.AREA_BREAKUP, cw.AREA_CAMP):
                if cw.cwpy.ydata:
                    changed = cw.cwpy.ydata.is_changed()
                self.change_area(areaid, quickdeal=True, specialarea=True)
                if cw.cwpy.ydata:
                    cw.cwpy.ydata._changed = changed
                if areaid == cw.AREA_BREAKUP:
                    self._store_partyrecord()
                    self.create_poschangearrow()
            else:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.pre_mcards.append(self.get_mcards())
                self.cardgrp.remove(self.mcards)
                self.mcards = []
                self.file_updates.clear()
                for mcard in self.sdata.sparea_mcards[areaid]:
                    self.cardgrp.add(mcard, layer=mcard.layer)
                    self.mcards.append(mcard)
                # 特殊エリアのカードはデバッグモードによって
                # 表示が切り替わる場合がある
                for mcard in self.sdata.sparea_mcards[areaid]:
                    if mcard.debug_only and not self.is_debugmode():
                        mcard.hide()
                    else:
                        mcard.deal()
                if self.is_autospread():
                    mcards = self.get_mcards("flagtrue")
                    self.set_autospread(mcards, 6, False, anime=False)

                if self.areaid in cw.AREAS_TRADE:
                    for mcard in self.get_mcards("visible"):
                        if mcard.command == "MoveCard" and mcard.arg == "PAWNSHOP":
                            poc = cw.sprite.background.PriceOfCard(mcard, None, self.cardgrp)
                            self.pricesprites.append(poc)

                self.list = self.get_mcards("visible")
                self.index = -1
                self.set_curtain(curtain_all=True)
            self.lock_menucards = False

        # ターゲット選択エリア
        elif self.selectedheader:
            self.clear_fcardsprites()
            self.clear_selection()
            header = self.selectedheader
            owner = header.get_owner()
            cardtarget = header.target
            if isinstance(owner, cw.sprite.card.EnemyCard):
                # 敵の行動を選択する時はターゲットの敵味方を入れ替える
                if cardtarget == "Enemy":
                    cardtarget = "Party"
                elif cardtarget == "Party":
                    cardtarget = "Enemy"

            if cardtarget in ("Both", "Enemy", "Party"):
                if self.status == "Scenario":
                    self.set_curtain(target=cardtarget)
                elif self.is_battlestatus():
                    if header.allrange:
                        if cardtarget == "Party":
                            targets = self.get_pcards("unreversed")
                        elif cardtarget == "Enemy":
                            targets = self.get_ecards("unreversed")
                        else:
                            targets = self.get_pcards("unreversed")
                            targets.extend(self.get_ecards("unreversed"))

                        owner.set_action(targets, header)
                        self.clear_specialarea()
                    else:
                        self.set_curtain(target=cardtarget)

                self.lock_menucards = False

            elif cardtarget in ("User", "None"):
                if self.status == "Scenario":
                    if cw.cwpy.setting.confirm_beforeusingcard:
                        owner.image = owner.get_selectedimage()
                    def func(owner):
                        if cw.cwpy.setting.confirm_beforeusingcard:
                            self.change_selection(owner)
                        self.call_modaldlg("USECARD")
                    self.exec_func(func, owner)
                elif self.is_battlestatus():
                    owner.set_action(owner, header)
                    self.clear_specialarea()
                    self.lock_menucards = False
                updatestatusbar = False

            else:
                self.lock_menucards = False

        if updatestatusbar:
            self.exec_func(self.statusbar.change, True)
        self.disposition_pcards()

    def clear_specialarea(self, redraw=True):
        """特殊エリアに移動する前のエリアに戻る。
        areaidが-3(パーティ解散)の場合はエリアチェンジする。
        """
        if redraw:
            self.clear_inusecardimg()
            self.clear_guardcardimg()
        self._stored_partyrecord = None
        targetselectionarea = False
        callpredlg = False

        oldareaid = self.areaid
        if self.areaid < 0:
            self.selectedheader = None
            areaid, data = self.pre_areaids.pop()

            if areaid == cw.AREA_CAMP:
                # キャンプ解除でスキルカードの使用回数消滅を確定
                self.sdata.uselimit_table.clear()

            # キャンプ時以外であればカーテン解除
            clear_curtain = areaid <> cw.AREA_CAMP

            # パーティ解散エリア解除の場合
            if self.areaid == cw.AREA_BREAKUP:
                self.topgrp.empty() # TODO: layer
                for i, pcard in enumerate(self.get_pcards()):
                    pcard.index = i
                    pcard.layer = (pcard.layer[0], pcard.layer[1], i, pcard.layer[3])
                    self.cardgrp.change_layer(pcard, pcard.layer)
                self.disposition_pcards()

            # カード移動操作エリアを解除の場合
            if oldareaid in cw.AREAS_TRADE:
                self.areaid = areaid
                self.sdata.change_data(areaid, data=data)
                self.cardgrp.remove(self.mcards)
                self.mcards = []
                self.cardgrp.remove(self.pricesprites)
                self.pricesprites = []
                self.file_updates.clear()
                if clear_curtain:
                    self.clear_curtain()
                for mcard in self.pre_mcards.pop():
                    self.cardgrp.add(mcard, layer=mcard.layer)
                    self.mcards.append(mcard)
                self.deal_cards()
                self.list = self.get_mcards("visible")
                self.index = -1
            else:
                if cw.cwpy.ydata:
                    changed = cw.cwpy.ydata.is_changed()
                self.change_area(areaid, data=data, quickdeal=True, specialarea=True,
                                 clear_curtain=clear_curtain)
                if cw.cwpy.ydata:
                    cw.cwpy.ydata._changed = changed
        elif self.is_battlestatus():
            self.clear_curtain()
            self.selectedheader = None
            if self.battle.is_ready():
                self.battle.update_showfcards()
            callpredlg = True
        else:
            # ターゲット選択エリアを解除の場合
            self.selectedheader = None
            targetselectionarea = True
            if self.is_curtained():
                self.clear_curtain()
            if self.pre_dialogs:
                callpredlg = True

        def func():
            showbuttons = not self.is_playingscenario() or\
                (not self.areaid in cw.AREAS_TRADE and self.areaid in cw.AREAS_SP) or\
                oldareaid == cw.AREA_CAMP or\
                (targetselectionarea and not self.is_runningevent()) or\
                (self.is_battlestatus() and self.battle.is_ready())
            self.statusbar.change(showbuttons)
            self.draw()
        self.exec_func(func)

        self.disposition_pcards()
        if not callpredlg:
            self.change_selection(self.selection)

        if oldareaid <> cw.AREA_CAMP and redraw:
            self.draw()

        if callpredlg:
            self.call_predlg()

    def clean_specials(self):
        """デバッガやF9で強制的なエリア移動等を発生させる時、
        特殊エリアにいたりバックログを開いていたりした場合は
        クリアして通常状態へ戻す。
        """
        if self.is_showingbacklog():
            self._is_showingbacklog = False
        if self.is_curtained():
            self.pre_dialogs = []
            if self.areaid in cw.AREAS_TRADE:
                self.topgrp.empty()
            self.clear_specialarea()

    def check_level(self, fromscenario):
        """PCの経験点を確認し、条件を満たしていれば
        レベルアップ・ダウン処理を行う。
        fromscenarioがTrueであれば同時に完全回復も行う。
        """
        for pcard in self.get_pcards():
            pcard.adjust_level(fromscenario)

    def create_poschangearrow(self):
        """パーティ解散エリアにメンバ位置入替用の
        クリック可能スプライトを配置する。
        """
        if self.areaid <> cw.AREA_BREAKUP:
            return

        if 0 <= self.index and isinstance(self.selection, cw.sprite.background.ClickableSprite):
            index = self.index
            self.clear_selection()
        else:
            index = -1

        self.topgrp.empty() # TODO: layer

        def get_image():
            return self.rsrc.pygamedialogs["REPLACE_POSITION"]

        def get_selimage():
            bmp = self.rsrc.pygamedialogs["REPLACE_POSITION"].convert_alpha()
            return cw.imageretouch.add_lightness(bmp, 64)

        bmp = self.rsrc.pygamedialogs["REPLACE_POSITION_noscale"]
        w, h = bmp.get_size()
        scr_scale = bmp.scr_scale if hasattr(bmp, "scr_scale") else 1
        w //= scr_scale
        h //= scr_scale
        size_noscale = (w, h)
        pcards = self.get_pcards()

        class Replace(object):
            def __init__(self, outer, i):
                self.outer = outer
                self.index1 = i
                self.index2 = i+1

            def replace(self):
                self.outer.replace_pcardorder(self.index1, self.index2)

        seq = []
        for i, pcard in enumerate(pcards[0:-1]):
            replace = Replace(self, i)
            pos_noscale = pcard.get_pos_noscale()
            x_noscale = pos_noscale[0] + 95+9/2 - size_noscale[0]/2
            y_noscale = pos_noscale[1] - size_noscale[1] - 5
            sprite = cw.sprite.background.ClickableSprite(get_image, get_selimage,
                                                          (x_noscale, y_noscale),
                                                          self.topgrp, replace.replace)
            seq.append(sprite)

        if index <> -1:
            self.index = index
            self.list = seq
            self.change_selection(self.list[index])

        self.draw(clip=cw.s(pygame.Rect((0, 0), cw.SIZE_AREA)))

    def replace_pcardorder(self, index1, index2):
        """パーティメンバの位置を入れ替える。"""
        if not (self.ydata and self.ydata.party):
            return
        self.ydata.party.replace_order(index1, index2)
        self.create_poschangearrow()

    def show_numberofcards(self, type):
        """カードの所持枚数とカード交換スプライトを表示する。"""
        if type == "SkillCard":
            cardtype = cw.POCKET_SKILL
        elif type == "ItemCard":
            cardtype = cw.POCKET_ITEM
        elif type == "BeastCard":
            cardtype = cw.POCKET_BEAST
        for pcard in self.get_pcards("unreversed"):
            cw.sprite.background.NumberOfCards(pcard, cardtype, self.topgrp)

        # カード交換用スプライト
        def get_image():
            return self.rsrc.pygamedialogs["REPLACE_CARDS"]
        def get_selimage():
            bmp = self.rsrc.pygamedialogs["REPLACE_CARDS"].convert_alpha()
            return cw.imageretouch.add_lightness(bmp, 64)
        bmp = self.rsrc.pygamedialogs["REPLACE_CARDS_noscale"]
        w, h = bmp.get_size()
        scr_scale = bmp.scr_scale if hasattr(bmp, "scr_scale") else 1
        w //= scr_scale
        h //= scr_scale
        size_noscale = (w, h)
        pcards = self.get_pcards()

        class ReplaceCards(object):
            def __init__(self, outer, pcard):
                self.outer = outer
                self.pcard = pcard

            def replace_cards(self):
                self.outer.change_selection(self.pcard)
                self.outer.call_modaldlg("CARDPOCKET_REPLACE")

        seq = []
        for pcard in pcards:
            if pcard.is_reversed():
                continue
            if type == "BeastCard":
                if not filter(lambda c: c.attachment, pcard.get_pocketcards(cardtype)):
                    continue
            else:
                if not pcard.get_pocketcards(cardtype):
                    continue

            replace = ReplaceCards(self, pcard)
            pos_noscale = pcard.get_pos_noscale()
            x_noscale = pos_noscale[0] + cw.setting.get_resourcesize("CardBg/LARGE")[0] - size_noscale[0] - 2
            y_noscale = pos_noscale[1] - size_noscale[1] - 2
            sprite = cw.sprite.background.ClickableSprite(get_image, get_selimage,
                                                          (x_noscale, y_noscale),
                                                          self.topgrp, replace.replace_cards)
            seq.append(sprite)

    def clear_numberofcards(self):
        """所持枚数表示を消去する。"""
        self.topgrp.empty() # TODO: layer

#-------------------------------------------------------------------------------
# 選択操作用メソッド
#-------------------------------------------------------------------------------

    def clear_selection(self):
        """全ての選択状態を解除する。"""
        self.change_selection(None)

        cw.cwpy.update_mousepos()
        cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)

    def change_selection(self, sprite):
        """引数のスプライトを選択状態にする。
        sprite: SelectableSprite
        """
        self.has_inputevent = True
        sbarbtn1 = isinstance(self.selection, cw.sprite.statusbar.StatusBarButton)
        sbarbtn2 = isinstance(sprite, cw.sprite.statusbar.StatusBarButton)

        # 現在全員の戦闘行動を表示中か
        show_allselectedcards = self._show_allselectedcards
        if sprite and not isinstance(sprite, cw.sprite.background.Curtain):
            # 特定の誰かが選択された場合は表示を更新
            show_allselectedcards = False
        elif not self._in_partyarea(self.mousepos):
            # パーティ領域より上へマウスカーソルが行ったら表示をクリア
            show_allselectedcards = False

        if self.selection:
            self.selection.image = self.selection.get_unselectedimage()

        # カードイベント中にtargetarrow, inusecardimgを消さないため
        if not self.is_runningevent():
            self.clear_targetarrow()
            self.clear_inusecardimg()

        if sprite:
            sprite.image = sprite.get_selectedimage()
        else:
            self.index = -1

        self.selection = sprite

        if (not self.is_runningevent()\
                and isinstance(sprite, cw.character.Character)\
                and (not self.selectedheader or self.is_battlestatus())\
                and sprite.is_analyzable())\
                or show_allselectedcards:
            seq = itertools.chain(self.get_pcards("unreversed"),
                                  self.get_ecards("unreversed"),
                                  self.get_fcards("unreversed"))
        elif not self.is_runningevent() and self.selectedheader and self.selectedheader.get_owner():
            seq = [self.selectedheader.get_owner()]
        else:
            seq = []

        for sprite in seq:
            if not self.selectedheader or sprite <> self.selectedheader.get_owner():
                if not (isinstance(sprite, cw.character.Character)\
                        and sprite.actiondata\
                        and sprite.is_analyzable()\
                        and sprite.status <> "hidden"):
                    continue

            selowner = self.selectedheader and self.selectedheader.get_owner() == sprite

            if cw.cwpy.ydata.party and cw.cwpy.ydata.party.backpack == sprite:
                mcards = self.get_mcards("visible")
                for mcard in mcards:
                    if isinstance(mcard, cw.sprite.card.MenuCard) and mcard.is_backpack():
                        sprite = mcard
                        break
                else:
                    continue
            elif cw.cwpy.ydata.storehouse == sprite:
                mcards = self.get_mcards("visible")
                for mcard in mcards:
                    if isinstance(mcard, cw.sprite.card.MenuCard) and mcard.is_storehouse():
                        sprite = mcard
                        break
                else:
                    continue

            self.clear_inusecardimg(sprite)

            if selowner:
                header = self.selectedheader
                targets = []
            elif sprite.actiondata:
                targets, header, _beasts = sprite.actiondata
            else:
                targets = []
                header = None

            if header:
                if self.selection == sprite and not selowner:
                    self.set_inusecardimg(sprite, header, fore=True)
                    if header.target == "None":
                        self.set_targetarrow([sprite])
                    elif targets:
                        self.set_targetarrow(targets)
                elif self.setting.show_allselectedcards or selowner:
                    alpha = cw.cwpy.setting.get_inusecardalpha(sprite)
                    self.set_inusecardimg(sprite, header, alpha=alpha)

                if self.setting.show_allselectedcards and isinstance(sprite, cw.sprite.card.PlayerCard):
                    show_allselectedcards = True

        self._show_allselectedcards = show_allselectedcards

        # ステータスボタン上であれば必ず矢印カーソルとする
        if bool(sbarbtn1) <> bool(sbarbtn2):
            self.change_cursor(self.cursor, force=True)

    def set_inusecardimg(self, owner, header, status="normal", center=False, alpha=255, fore=False):
        """PlayerCardの前に使用中カードの画像を表示。"""
        if center or (not owner.inusecardimg and self.background.rect.colliderect(owner.rect) and owner.status <> "hidden"):
            inusecard = cw.sprite.background.InuseCardImage(owner, header, status, center, alpha=alpha, fore=fore)
            owner.inusecardimg = inusecard
            self.inusecards.append(inusecard)
        return owner.inusecardimg

    def clear_inusecardimg(self, user=None):
        """PlayerCardの前の使用中カードの画像を削除。"""
        self._show_allselectedcards = False
        if user:
            if user.inusecardimg:
                user.inusecardimg.group.remove(user.inusecardimg) # TODO: layer
                self.inusecards.remove(user.inusecardimg)
                self.add_lazydraw(user.inusecardimg.rect)
                user.inusecardimg = None
        else:
            for card in self.get_pcards():
                card.inusecardimg = None
            for card in self.get_mcards():
                card.inusecardimg = None

            for card in self.inusecards:
                card.group.remove(card) # TODO: layer
                self.add_lazydraw(card.rect)
            self.inusecards = []

    def clear_inusecardimgfromheader(self, header):
        """表示中の使用中カードの中にheaderのものが
        含まれていた場合は削除。
        """
        for card in list(self.inusecards):
            if card.header == header:
                if card.user:
                    self.clear_inusecardimg(card.user)
                    if card.user.status <> "hidden":
                        cw.animation.animate_sprite(card.user, "hide")
                        cw.animation.animate_sprite(card.user, "deal")
                else:
                    card.group.remove(card) # TODO: layer
                    self.inusecards.remove(card)
                    self.add_lazydraw(card.rect)

    def set_guardcardimg(self, owner, header):
        """PlayerCardの前に回避・抵抗ボーナスカードの画像を表示。"""
        if not self.get_guardcardimg() and self.background.rect.colliderect(owner.rect) and owner.status <> "hidden":
            card = cw.sprite.background.InuseCardImage(owner, header, status="normal", center=False)
            self.guardcards.append(card)

    def clear_guardcardimg(self):
        """PlayerCardの前の回避・抵抗ボーナスカードの画像を削除。"""
        for card in self.guardcards:
            card.group.remove(card)
        self.guardcards = []

    def set_targetarrow(self, targets):
        """targets(PlayerCard, MenuCard, CastCard)の前に
        対象選択の指矢印の画像を表示。
        """
        if not self.cardgrp.get_sprites_from_layer(cw.LAYER_TARGET_ARROW):
            if not isinstance(targets, (list, tuple)):
                if targets.status <> "hidden":
                    cw.sprite.background.TargetArrow(targets)
            else:
                for target in targets:
                    if target.status <> "hidden":
                        cw.sprite.background.TargetArrow(target)

    def clear_targetarrow(self):
        """対象選択の指矢印の画像を削除。"""
        self.cardgrp.remove_sprites_of_layer(cw.LAYER_TARGET_ARROW)

    def update_selectablelist(self):
        """状況に応じて矢印キーで選択対象となる
        カードのリストを更新する。"""
        if self.is_pcardsselectable:
            if self.is_debugmode() and not self.selectedheader:
                self.list = self.get_pcards()
            else:
                self.list = self.get_pcards("unreversed")
        elif self.is_mcardsselectable:
            self.list = self.get_mcards("visible")
        else:
            self.list = []
        self.index = -1

    def set_curtain(self, target="Both", curtain_all=False):
        """Curtainスプライトをセットする。"""
        if not self.is_curtained():
            self.is_pcardsselectable = target in ("Both", "Party")
            self.is_mcardsselectable = not self.is_battlestatus() or\
                                       target in ("Both", "Enemy")
            self.update_selectablelist()

            # カード上のカーテン
            if not self.is_pcardsselectable:
                cards = self.get_pcards()
                for card in cards:
                    cw.sprite.background.Curtain(card, self.cardgrp)
            if not self.is_mcardsselectable:
                cards = self.get_mcards("visible")
                for card in cards:
                    cw.sprite.background.Curtain(card, self.cardgrp)

            # 背景上のカーテン
            self.background.set_curtain(curtain_all=curtain_all)

            self._curtained = True

            self.draw()

    def clear_curtain(self):
        """Curtainスプライトを解除する。"""
        if self.is_curtained():
            self.background.clear_curtain()
            self.cardgrp.remove(self.curtains)
            self.curtains = []
            self._curtained = False
            self.is_pcardsselectable = self.ydata and self.ydata.party
            self.is_mcardsselectable = True
            self.draw()

    def cancel_cardcontrol(self):
        """カードの移動や使用の対象選択をキャンセルする。"""
        if self.is_curtained():
            self.play_sound("click", )

            if self.areaid in cw.AREAS_TRADE:
                # カード移動選択エリアだったら、事前に開いていたダイアログを開く
                self.selectedheader = None
                self.call_predlg()
            else:
                # それ以外だったら特殊エリアをクリアする
                self.clear_specialarea(redraw=False)

    def is_lockmenucards(self, sprite):
        """メニューカードをクリック出来ない状態か。"""
        if isinstance(sprite, (cw.sprite.statusbar.StatusBarButton, cw.sprite.animationcell.AnimationCell)) and\
                sprite.selectable_on_event:
            return False
        return self.lock_menucards or\
               self.is_showingdlg() or\
               pygame.event.peek(pygame.locals.USEREVENT) or\
               self.is_showingbacklog()

#-------------------------------------------------------------------------------
# プレイ用メソッド
#-------------------------------------------------------------------------------

    def elapse_time(self, playeronly=False, fromevent=False):
        """時間経過。"""
        cw.cwpy.advlog.start_timeelapse()
        self._elapse_time = True

        ccards = self.get_pcards("unreversed")
        if not playeronly:
            ccards.extend(self.get_ecards("unreversed"))
            ccards.extend(self.get_fcards())

        try:
            for ccard in ccards:
                try:
                    if fromevent:
                        if cw.cwpy.event.has_selectedmember():
                            selmember = cw.cwpy.event.get_selectedmember()
                            cw.cwpy.event.set_selectedmember(None)
                        else:
                            selmember = None

                    ccard.set_timeelapse(fromevent=fromevent)

                    if fromevent:
                        cw.cwpy.event.set_selectedmember(selmember)

                except cw.event.EffectBreakError:
                    if fromevent:
                        raise
                    else:
                        # 時間経過コンテント以外で時間経過が起きている場合、
                        # 効果中断されても以降のキャラクターの処理は継続
                        pass
        finally:
            self._elapse_time = False

    def interrupt_adventure(self):
        """冒険の中断。宿画面に遷移する。"""
        if self.status == "Scenario":
            self.sdata.update_log()
            for music in self.music:
                music.stop()
            cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
            self.ydata.load_party(None)

            if not self.areaid >= 0:
                self.areaid, _data = self.pre_areaids[0]

            self.set_yado()

    def load_party(self, header=None, chgarea=True, newparty=False, loadsprites=True):
        """パーティデータをロードする。
        header: PartyHeader。指定しない場合はパーティデータを空にする。
        """
        self.ydata.load_party(header)

        if chgarea:
            if header:
                areaid = 2
            else:
                areaid = 1
            self.change_area(areaid, bginhrt=False)
        elif newparty:
            self.cardgrp.remove(self.pcards)
            self.pcards = []
            if loadsprites:
                for i, e in enumerate(self.ydata.party.members):
                    pos_noscale = (9 + 95 * i + 9 * i, 285)
                    pcard = cw.sprite.card.PlayerCard(e, pos_noscale=pos_noscale, index=i)
                self.show_party()
        else:
            self.cardgrp.remove(self.pcards)
            self.pcards = []
            if loadsprites:
                e = self.ydata.party.members[0]
                pcardsnum = len(self.ydata.party.members) - 1
                pos_noscale = (9 + 95 * pcardsnum + 9 * pcardsnum, 285)
                pcard = cw.sprite.card.PlayerCard(e, pos_noscale=pos_noscale, index=pcardsnum)
                pcard.set_pos_noscale(pos_noscale)
                cw.animation.animate_sprite(pcard, "deal")

        self.is_pcardsselectable = self.ydata and self.ydata.party

    def dissolve_party(self, pcard=None, cleararea=True):
        """現在選択中のパーティからpcardを削除する。
        pcardがない場合はパーティ全体を解散する。
        """
        breakuparea = (self.areaid == cw.AREA_BREAKUP)

        if pcard:
            if not breakuparea:
                return
            self.play_sound("page")
            pcard.remove_numbercoupon()
            pcards = self.get_pcards()
            index = pcards.index(pcard)
            arrows = self.topgrp.sprites()
            sprites = [pcard]
            if index < len(arrows):
                sprites.append(arrows[index])
            elif 0 < index and index == len(arrows):
                sprites.append(arrows[-1])
            cw.animation.animate_sprites(sprites, "delete")
            if breakuparea and pcards:
                self.create_poschangearrow()
            pcard.data.write_xml()
            self.ydata.add_standbys(pcard.data.fpath)

            if not self.get_pcards():
                self.dissolve_party()

        else:
            pcards = self.get_pcards()
            seq = list(pcards)
            if breakuparea:
                seq.extend(self.topgrp.sprites())
            cw.animation.animate_sprites(seq, "hide")
            if breakuparea:
                self.topgrp.empty() # TODO: layer

            for pcard in pcards:
                pcard.remove_numbercoupon()
                self.cardgrp.remove(pcard)
                pcard.data.write_xml()
            self.pcards = []

            p_money = int(self.ydata.party.data.find("Property/Money").text)
            p_members = [member.fpath for member in self.ydata.party.members]
            p_backpack = self.ydata.party.backpack[:]
            p_backpack.reverse()
            for header in p_backpack:
                self.trade("STOREHOUSE", header=header, from_event=True, sort=False)
            self.ydata.sort_storehouse()

            self.ydata.deletedpaths.add(os.path.dirname(self.ydata.party.data.fpath))
            self.ydata.party.members = []
            self.ydata.load_party(None)
            self.ydata.environment.edit("Property/NowSelectingParty", "")
            self.ydata.set_money(p_money)

            for path in reversed(p_members):
                self.ydata.add_standbys(path, sort=False)
            self.ydata.sort_standbys()

            if breakuparea:
                self._save_partyrecord()
                if cleararea:
                    self.pre_areaids[-1] = (1, None)
                    self.clear_specialarea()

    def get_partyrecord(self):
        """現在のパーティ情報の記録を生成して返す。"""
        assert bool(self.ydata.party)
        class StoredParty(object):
            def __init__(self, party):
                self.fpath = ""
                self.name = party.name
                self.money = party.money
                self.members = party.members[:]
                self.backpack = party.backpack[:]
                self.is_suspendlevelup = party.is_suspendlevelup
                cw.util.sort_by_attr(self.backpack, "order")
        return StoredParty(self.ydata.party)

    def _store_partyrecord(self):
        """解散操作前にパーティ情報を記録する。"""
        self._stored_partyrecord = self.get_partyrecord()

    def _save_partyrecord(self):
        """解散時にパーティ情報をファイルへ記録する。"""
        if not self._stored_partyrecord:
            return
        if not self.setting.autosave_partyrecord:
            return

        if self.setting.overwrite_partyrecord:
            self.ydata.replace_partyrecord(self._stored_partyrecord)
        else:
            self.ydata.add_partyrecord(self._stored_partyrecord)

    def save_partyrecord(self):
        """現在のパーティ情報を記録する。"""
        if not self.setting.autosave_partyrecord:
            return
        if not (self.ydata and self.ydata.party):
            return

        partyrecord = self.get_partyrecord()
        if self.setting.overwrite_partyrecord:
            self.ydata.replace_partyrecord(partyrecord)
        else:
            self.ydata.add_partyrecord(partyrecord)

    def play_sound(self, name, from_scenario=False, subvolume=100, loopcount=1, channel=0, fade=0, material_override=False):
        if channel < 0 or cw.bassplayer.MAX_SOUND_CHANNELS <= channel:
            return
        if self <> threading.currentThread():
            self.exec_func(self.play_sound, name, from_scenario, subvolume, loopcount, channel, fade)
            return

        if material_override:
            # シナリオ側でスキン付属効果音を上書きする
            sound = self.sounds[name]
            path = os.path.basename(sound.get_path())
            path = os.path.splitext(path)[0]
            path = cw.util.join_paths(self.sdata.scedir, path)
            path = os.path.basename(cw.util.find_resource(path, cw.M_SND))
            inusecard = self.event.get_inusecard()
            if self._play_sound_with(path, from_scenario, inusecard=inusecard, subvolume=subvolume, loopcount=loopcount, channel=channel, fade=fade):
                return

        self.sounds[name].play(from_scenario, subvolume=subvolume, loopcount=loopcount, channel=channel, fade=fade)

    def _play_sound_with(self, path, from_scenario, inusecard=None, subvolume=100, loopcount=1, channel=0, fade=0):
        if not path:
            return False
        inusesoundpath = cw.util.get_inusecardmaterialpath(path, cw.M_SND, inusecard)
        if os.path.isfile(inusesoundpath):
            path = inusesoundpath
        else:
            path = cw.util.get_materialpath(path, cw.M_SND, system=self.areaid < 0)
        if os.path.isfile(path):
            cw.util.load_sound(path).play(from_scenario, subvolume=subvolume, loopcount=loopcount, channel=channel, fade=fade)
            return True
        return False

    def play_sound_with(self, path, inusecard=None, subvolume=100, loopcount=1, channel=0, fade=0):
        """効果音を再生する。
        シナリオ効果音・スキン効果音を適宜使い分ける。
        """
        if not path:
            return
        if channel < 0 or cw.bassplayer.MAX_SOUND_CHANNELS <= channel:
            return
        if self._play_sound_with(path, True, inusecard, subvolume=subvolume, loopcount=loopcount, channel=channel, fade=fade):
            return

        name = cw.util.splitext(os.path.basename(path))[0]

        if name in self.skinsounds:
            self.skinsounds[name].play(True, subvolume=subvolume, loopcount=loopcount, channel=channel, fade=fade)

    def has_sound(self, path):
        if not path:
            return False

        path = cw.util.get_materialpath(path, cw.M_SND, system=self.areaid < 0)

        if os.path.isfile(path):
            return True
        else:
            name = cw.util.splitext(os.path.basename(path))[0]
            return name in self.skinsounds

#-------------------------------------------------------------------------------
# データ編集・操作用メソッド。
#-------------------------------------------------------------------------------

    def trade(self, targettype, target=None, header=None,\
              from_event=False, parentdialog=None, toindex=-1,\
              insertorder=-1, sort=True, sound=True, party=None,\
              from_getcontent=False, call_predlg=True,\
              clearinusecard=True, update_image=True):
        """
        カードの移動操作を行う。
        Getコンテントからこのメソッドを操作する場合は、
        ownerはNoneにする。
        """
        # カード移動操作用データを読み込む
        if self.selectedheader and not header:
            assert self.selectedheader
            header = self.selectedheader

        if not party:
            party = self.ydata.party

        if party:
            is_playingscenario = party.is_adventuring()
        else:
            is_playingscenario = self.is_playingscenario()

        if header.is_backpackheader() and party:
            owner = party.backpack
        else:
            owner = header.get_owner()

        # 荷物袋<=>カード置場のため
        # ファイルの移動だけで済む場合
        move = (targettype in ("BACKPACK", "STOREHOUSE")) and\
            ((owner == self.ydata.storehouse) or (party and owner == party.backpack)) and\
            (not is_playingscenario)

        # カード置場・荷物袋内での位置の移動の場合
        toself = (targettype == "BACKPACK" and party and owner == party.backpack) or\
                 (targettype == "STOREHOUSE" and owner == self.ydata.storehouse)

        if not toself and not targettype in ("PAWNSHOP", "TRASHBOX"):
            header.do_write()

        # 移動先を設定。
        if targettype == "PLAYERCARD":
            target = target
        elif targettype == "BACKPACK":
            target = party.backpack
        elif targettype == "STOREHOUSE":
            target = self.ydata.storehouse
        elif targettype in ("PAWNSHOP", "TRASHBOX"):

            # プレミアカードは売却・破棄できない(イベントからの呼出以外)
            if not self.debug and self.setting.protect_premiercard and\
                    header.premium == "Premium" and not from_event:
                if targettype == "PAWNSHOP":
                    s = self.msgs["error_sell_premier_card"]
                    self.call_modaldlg("NOTICE", text=s, parentdialog=parentdialog)
                elif targettype == "TRASHBOX":
                    s = self.msgs["error_dump_premier_card"] % (header.name)
                    self.call_modaldlg("NOTICE", text=s, parentdialog=parentdialog)

                return

            # スターつきのカードは売却・破棄できない(イベントからの呼出以外)
            if self.setting.protect_staredcard and header.star and not from_event:
                if targettype == "PAWNSHOP":
                    s = self.msgs["error_sell_stared_card"]
                    self.call_modaldlg("NOTICE", text=s, parentdialog=parentdialog)
                elif targettype == "TRASHBOX":
                    s = self.msgs["error_dump_stared_card"]
                    self.call_modaldlg("NOTICE", text=s, parentdialog=parentdialog)

                return

            if targettype == "PAWNSHOP":
                price = header.sellingprice
                if not from_event and (self.setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_ALWAYS or\
                                        (self.setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_SENDTO and parentdialog)):
                    if sound:
                        cw.cwpy.play_sound("page")
                    s = cw.cwpy.msgs["confirm_sell"] % (header.name, price)
                    self.call_modaldlg("YESNO", text=s, parentdialog=parentdialog)
                    if self.get_yesnoresult() <> wx.ID_OK:
                        return
            else:
                if not from_event and (self.setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_ALWAYS or\
                                        (self.setting.confirm_dumpcard == cw.setting.CONFIRM_DUMPCARD_SENDTO and parentdialog)):
                    if sound:
                        cw.cwpy.play_sound("page")
                    s = cw.cwpy.msgs["confirm_dump"] % (header.name)
                    self.call_modaldlg("YESNO", text=s, parentdialog=parentdialog)
                    if self.get_yesnoresult() <> wx.ID_OK:
                        return

            target = None
        else:
            raise ValueError("Targettype in trade method is incorrect.")

        # 手札カードダイアログ用のインデックスを取得する
        if header.type == "SkillCard":
            index = 0
        elif header.type == "ItemCard" :
            index = 1
        elif header.type == "BeastCard":
            index = 2
        else:
            raise ValueError("CARDPOCKET Index in trade method is incorrect.")

        # もし移動先がPlayerCardだったら、手札の枚数判定を行う
        if targettype == "PLAYERCARD" and target <> owner:
            n = len(target.cardpocket[index])
            maxn = target.get_cardpocketspace()[index]

            # 手札が一杯だったときの処理
            if n + 1 > maxn:
                if from_event:
                    # 互換動作: 1.20以前では手札が一杯でも荷物袋に入らない
                    if not (from_getcontent and cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA))):
                        self.trade("BACKPACK", header=header, from_event=True, sort=sort, party=party,
                                   from_getcontent=from_getcontent)

                else:
                    s = cw.cwpy.msgs["error_hand_be_full"] % target.name
                    self.call_modaldlg("NOTICE", text=s, parentdialog=parentdialog)

                return

        # 音を鳴らす
        if not from_event:
            if targettype == "TRASHBOX":
                self.play_sound("dump")
            elif targettype == "PAWNSHOP":
                self.play_sound("signal")
            elif sound:
                self.play_sound("page")

        # 宿状態の変化を通知
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        #-----------------------------------------------------------------------
        # 移動元からデータを削除
        #-----------------------------------------------------------------------

        hold = header.hold
        fromplayer = isinstance(owner, cw.character.Player)

        # 移動元がCharacterだった場合
        if isinstance(owner, cw.character.Character):
            assert not move
            # 移動元のCardHolderからCardHeaderを削除
            owner.cardpocket[index].remove(header)
            # 移動元からカードのエレメントを削除
            path = "%ss" % header.type
            owner.data.remove(path, header.carddata)
            # 戦闘中だった場合はデッキからも削除
            owner.deck.remove(owner, header)
            if target <> owner and clearinusecard and not self.areaid in cw.AREAS_TRADE:
                self.clear_inusecardimgfromheader(header)

            # 行動予定に入っていればキャンセル
            action = owner.actiondata
            if action:
                targets, aheader, beasts = action
                if aheader and aheader.ref_original() == header.ref_original():
                    aheader = None
                    targets = None
                beasts2 = []
                for targets_b, beast in beasts:
                    if beast.ref_original() <> header.ref_original():
                        beasts2.append((targets_b, beast))
                owner.set_action(targets, aheader, beasts2, True)

            # スキルの場合は使用回数を0にする
            if header.type == "SkillCard" and owner <> target:
                if self.is_playingscenario() and not from_event and self.areaid == cw.AREA_TRADE3 and\
                        isinstance(owner, cw.character.Player) and header.uselimit and\
                        not (owner, header) in self.sdata.uselimit_table:
                    # キャンプ中は元々の使用回数を記憶しておき、
                    # 元の所有者の手許に戻ったら使用回数を復元する
                    self.sdata.uselimit_table[(owner, header)] = header.uselimit
                header.maxuselimit = 0
                header.uselimit = 0
                header.carddata.getfind("Property/UseLimit").text = "0"

            # ホールドをFalseに
            header.hold = False

            if not header.type == "BeastCard":
                header.carddata.getfind("Property/Hold").text = "False"

            header.set_owner(None)

        # 移動元が荷物袋だった場合
        elif party and owner == party.backpack:
            # 移動元のリストからCardHeaderを削除
            owner.remove(header)

            if toself:
                # 荷物袋内の位置のみ変更
                pass
            elif header.scenariocard:
                # シナリオで入手したカードはそのまま削除してよい
                header.contain_xml(load=not targettype in ("PAWNSHOP", "TRASHBOX"))
            else:
                if is_playingscenario:
                    if not header.carddata:
                        e = cw.data.yadoxml2etree(header.fpath)
                        header.carddata = e.getroot()
                    # シナリオプレイ中であれば削除フラグを立てて削除を保留
                    # (F9時に復旧する必要があるため)
                    if targettype in ("PAWNSHOP", "TRASHBOX"):
                        # 移動先がゴミ箱・下取りだったら完全削除予約
                        moved = 2
                    else:
                        # どこかに残る場合
                        moved = 1

                    etree = cw.data.xml2etree(element=header.carddata)
                    etree.edit("Property", str(moved), "moved")
                    etree.write_xml()
                    header.moved = moved
                    header2 = cw.header.CardHeader(carddata=header.carddata)
                    header2.fpath = header.fpath
                    party.backpack_moved.append(header2)
                    header.fpath = ""
                elif move:
                    # ファイルの移動のみ
                    self.ydata.deletedpaths.add(header.fpath, header.scenariocard)
                else:
                    # 宿にいる場合はそのまま削除する
                    header.contain_xml()

        # 移動元がカード置場だった場合
        elif owner == self.ydata.storehouse:
            # 移動元のリストからCardHeaderを削除
            owner.remove(header)
            if toself:
                # カード置場内の位置のみ変更
                pass
            elif move:
                # ファイルの移動のみ
                self.ydata.deletedpaths.add(header.fpath, header.scenariocard)
            else:
                header.contain_xml()

        # 移動元が存在しない場合(get or loseコンテンツから呼んだ場合)
        else:
            assert not move
            header.contain_xml()

        if header == self.selectedheader:
            self.clear_inusecardimg()

        #-----------------------------------------------------------------------
        # ファイル削除
        #-----------------------------------------------------------------------

        # 移動先がゴミ箱・下取りだったら
        if targettype in ("PAWNSHOP", "TRASHBOX"):
            assert not move
            # 付帯以外の召喚獣カードの場合
            if header.type == "BeastCard" and not header.attachment and\
                    isinstance(owner, cw.character.Character):
                if update_image:
                    owner.update_image()
            # シナリオで取得したカードじゃない場合、XMLの削除
            elif not header.scenariocard and header.moved == 0:
                self.remove_xml(header)
                if fromplayer and is_playingscenario:
                    # PCによってシナリオへ持ち込まれたカードを破棄する際は
                    # デバッグログに出すために記録しておく
                    # (荷物袋からの破棄・移動はbackpack_movedに入るため不要)
                    dcpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party/Deleted" + header.type)
                    if not os.path.isdir(dcpath):
                        os.makedirs(dcpath)
                    dfpath = cw.util.join_paths(dcpath, cw.util.repl_dischar(header.name) + ".xml")
                    dfpath = cw.util.dupcheck_plus(dfpath, yado=False)
                    etree = cw.data.xml2etree(element=header.carddata)
                    etree.write(dfpath)
            elif not header.scenariocard and header.moved == 1:
                # 荷物袋からPCへ移動してそこから除去した場合
                assert not header.carddata is None
                header.contain_xml()
                etree = cw.data.xml2etree(element=header.carddata)
                etree.edit("Property", "2", "moved")
                header.moved = 2
                header.set_owner("BACKPACK")
                header.write(party=party)
                header.set_owner(None)
                self.ydata.party.backpack_moved.append(header)

        #-----------------------------------------------------------------------
        # 移動先にデータを追加する
        #-----------------------------------------------------------------------

        # 移動先がPlayerCardだった場合
        if targettype == "PLAYERCARD":
            assert not move
            # cardpocketにCardHeaderを追加
            header.set_owner(target)
            header.set_hold(hold)
            # 使用回数を設定
            header.get_uselimit()
            if header.type == "SkillCard":
                if from_event:
                    header.set_uselimit(header.maxuselimit)
                elif self.is_playingscenario() and self.areaid == cw.AREA_TRADE3 and\
                        (target, header) in self.sdata.uselimit_table:
                    uselimit = self.sdata.uselimit_table[(target, header)]
                    header.set_uselimit(uselimit-header.uselimit)
            # カードのエレメントを追加
            path = "%ss" % header.type
            if toindex == -1:
                target.cardpocket[index].append(header)
                target.data.append(path, header.carddata)
            else:
                target.cardpocket[index].insert(toindex, header)
                target.data.find(path).insert(toindex, header.carddata)
            # ～1.1まではDBにwsnversion列が無いため、
            # header.wsnversionがNoneの場合がある
            header.wsnversion = header.carddata.getattr(".", "dataVersion", "")

            # 戦闘中の場合、Deckの手札・山札に追加
            if cw.cwpy.is_battlestatus():
                target.deck.add(target, header)

        # 移動先が荷物袋だった場合
        elif targettype == "BACKPACK":
            # 移動先のリストにCardHeaderを追加
            if toindex == -1:
                header.order = cw.util.new_order(target, mode=1)
                target.insert(0, header)
            else:
                if insertorder == -1:
                    header.order = cw.util.new_order(target, mode=1)
                else:
                    header.order = insertorder
                target.insert(toindex, header)
            header.set_owner("BACKPACK")
            if sort:
                party.sort_backpack()

        # 移動先がカード置場だった場合
        elif targettype == "STOREHOUSE":
            # 移動先のリストにCardHeaderを追加
            if toindex == -1:
                header.order = cw.util.new_order(target, mode=1)
                target.insert(0, header)
            else:
                if insertorder == -1:
                    header.order = cw.util.new_order(target, mode=1)
                else:
                    header.order = insertorder
                target.insert(toindex, header)
            header.set_owner("STOREHOUSE")
            if sort:
                self.ydata.sort_storehouse()

        # 下取りに出した場合
        elif targettype == "PAWNSHOP":
            assert not move
            # パーティの所持金または金庫に下取金を追加
            if party:
                self.exec_func(party.set_money, price, blink=True)
            else:
                self.exec_func(self.ydata.set_money, price, blink=True)
            self.exec_func(self.draw)

        if targettype in ("BACKPACK", "STOREHOUSE") and not toself:
            # 移動先が荷物袋かカード置場だったら
            if move:
                header.write(party, move=True)
                header.carddata = None
            else:
                header.fpath = ""
                etree = cw.data.xml2etree(element=header.carddata)
                if not from_getcontent:
                    # 削除フラグを除去
                    if etree.getint("Property", "moved", 0) <> 0:
                        etree.remove("Property", attrname="moved")
                        header.moved = 0
                header.write(party, from_getcontent=from_getcontent)
                header.carddata = None

        if header == self.selectedheader:
            self.selectedheader = None

        # カード選択ダイアログを再び開く(イベントから呼ばれたのでなかったら)
        if not from_event and call_predlg:
            self.call_predlg()

    def remove_xml(self, target):
        """xmlファイルを削除する。
        target: AdventurerHeader, PlayerCard, CardHeader, XMLFilePathを想定。
        """
        if isinstance(target, cw.character.Player):
            self.ydata.deletedpaths.add(target.data.fpath)
            self.remove_materials(target.data.find("Property"))
        elif isinstance(target, cw.header.AdventurerHeader):
            self.ydata.deletedpaths.add(target.fpath)
            data = cw.data.yadoxml2element(target.fpath, "Property")
            self.remove_materials(data)
        elif isinstance(target, cw.header.CardHeader):
            if target.fpath:
                self.ydata.deletedpaths.add(target.fpath)

            if target.carddata is not None:
                data = target.carddata
            else:
                data = cw.data.yadoxml2element(target.fpath)

            self.remove_materials(data)
        elif isinstance(target, cw.data.Party):
            self.ydata.deletedpaths.add(target.data.fpath)
            self.remove_materials(target.data)
        elif isinstance(target, (str, unicode)):
            if target.endswith(".xml"):
                self.ydata.deletedpaths.add(target)
                data = cw.data.yadoxml2element(target)
                self.remove_materials(data)

    def remove_materials(self, data):
        """XMLElementに記されている
        素材ファイルを削除予定リストに追加する。
        """
        e = data.find("Property/Materials")
        if not e is None:
            path = cw.util.join_paths(self.yadodir, e.text)
            temppath = cw.util.join_paths(self.tempdir, e.text)
            if os.path.isdir(path):
                self.ydata.deletedpaths.add(path)
            if os.path.isdir(temppath):
                self.ydata.deletedpaths.add(temppath)
        else:
            # Property/Materialsが無かった頃の互換動作
            for e in data.iter():
                if e.tag == "ImagePath" and e.text and not cw.binary.image.path_is_code(e.text):
                    path = cw.util.join_paths(self.yadodir, e.text)
                    temppath = cw.util.join_paths(self.tempdir, e.text)

                    if os.path.isfile(path):
                        self.ydata.deletedpaths.add(path)

                    if os.path.isfile(temppath):
                        self.ydata.deletedpaths.add(temppath)

    def copy_materials(self, data, dstdir, from_scenario=True, scedir="",
                       yadodir=None, toyado=None, adventurer=False,
                       imgpaths=None, importimage=False, can_loaded_scaledimage=False):
        """
        from_scenario: Trueの場合は開いているシナリオから、
                       Falseの場合は開いている宿からコピーする
        XMLElementに記されている
        素材ファイルをdstdirにコピーする。
        """
        orig_scedir = scedir
        if isinstance(data, cw.data.CWPyElementTree):
            data = data.getroot()

        if imgpaths is None:
            imgpaths = {}

        r_specialfont = re.compile("#.") # 特殊文字(#)
        if data.tag == "Property":
            prop = data
        else:
            prop = data.find("Property")

        if toyado:
            yadodir2 = toyado
            dstdir2 = dstdir.replace(toyado + "/", "", 1)
        else:
            yadodir2 = self.yadodir
            dstdir2 = dstdir.replace(yadodir2 + "/", "", 1)

        if adventurer:
            mdir = ""
            emp = None
        else:
            emp = prop.find("Materials")
            if emp is None:
                mdir = ""
                e = cw.data.make_element("Materials", dstdir2)
                prop.append(e)
            else:
                if not scedir:
                    scedir = cw.util.join_yadodir(emp.text)
                mdir = emp.text
                if mdir in imgpaths:
                    emp.text = imgpaths[mdir]
                else:
                    emp.text = dstdir2
                    imgpaths[mdir] = dstdir2

        if yadodir and mdir:
            from_scenario = True
            scedir = cw.util.join_paths(yadodir, mdir)

        if not scedir and from_scenario:
            scedir = self.sdata.scedir

        for e in data.iter():
            e.content = None # イベントコンテントのキャッシュは削除しておく
            if e.tag == "ImagePath" and importimage:
                # ImagePathはcarddata無しでの表示に必要となるので取り込んでおく
                if e.text and not cw.binary.image.path_is_code(e.text):
                    path = cw.util.join_paths(orig_scedir, e.text)
                    if os.path.isfile(path):
                        with open(path, "rb") as f:
                            imagedata = f.read()
                            f.close()
                        e.text = cw.binary.image.data_to_code(imagedata)
            elif e.tag in ("ImagePath", "SoundPath", "SoundPath2"):
                path = e.text
                if path:
                    if yadodir and mdir:
                        path = cw.util.relpath(path, mdir)
                    def set_material(text):
                        e.text = text
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, path, set_material, yadodir, toyado,
                                        can_loaded_scaledimage=can_loaded_scaledimage)
            elif e.tag in ("Play", "Talk"):
                path = e.getattr(".", "path", "")
                if path:
                    if yadodir and mdir:
                        path = cw.util.relpath(path, mdir)
                    def set_material(text):
                        e.attrib["path"] = text
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, path, set_material, yadodir, toyado,
                                        can_loaded_scaledimage=can_loaded_scaledimage)
            elif e.tag == "Text" and e.text:
                for spchar in r_specialfont.findall(e.text):
                    c = "font_" + spchar[1:]
                    def set_material(text):
                        pass
                    for ext in cw.EXTS_IMG:
                        self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, c + ext, set_material, yadodir, toyado,
                                            can_loaded_scaledimage=can_loaded_scaledimage)

            elif e.tag == "Effect":
                path = e.getattr(".", "sound", "")
                if path:
                    if yadodir and mdir:
                        path = cw.util.relpath(path, mdir)
                    def set_material(text):
                        e.attrib["sound"] = text
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, path, set_material, yadodir, toyado,
                                        can_loaded_scaledimage=can_loaded_scaledimage)

            elif not e is data and e.tag == "BeastCard" and from_scenario:
                self.sdata.copy_carddata(e, dstdir, from_scenario, scedir, imgpaths)

    def _copy_material(self, data, dstdir, from_scenario, scedir, imgpaths, e, materialpath, set_material, yadodir, toyado,
                       can_loaded_scaledimage):
        pisc = not e is None and e.tag == "ImagePath" and cw.binary.image.path_is_code(materialpath)
        if pisc:
            imgpath = materialpath
        else:
            if from_scenario:
                if not scedir:
                    scedir = self.sdata.scedir
                imgpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/TempFile", materialpath)
                if not os.path.isfile(imgpath):
                    imgpath = cw.util.join_paths(scedir, materialpath)
            elif yadodir:
                imgpath = cw.util.join_paths(yadodir, materialpath)
            else:
                imgpath = cw.util.join_yadodir(materialpath)
            if not yadodir:
                imgpath = cw.util.get_materialpathfromskin(imgpath, cw.M_IMG)

            # 吉里吉里形式音声ループ情報
            sli = imgpath + u".sli"
            if not os.path.isfile(sli):
                sli = None

        if not (pisc or os.path.isfile(imgpath)):
            return

        # Jpy1から参照しているイメージを再帰的にコピーする
        if from_scenario and cw.util.splitext(imgpath)[1].lower() == ".jpy1":
            try:
                config = cw.effectbooster.EffectBoosterConfig(imgpath, "init")
                for section in config.sections():
                    jpy1innnerfile = config.get(section, "filename", "")
                    if not jpy1innnerfile:
                        continue
                    dirtype = config.get_int(section, "dirtype", 1)
                    innerfpath = cw.effectbooster.get_filepath_s(config.path, imgpath, jpy1innnerfile, dirtype)
                    if not innerfpath.startswith(scedir + "/"):
                        continue
                    innerfpath = innerfpath.replace(scedir + "/", "", 1)
                    def func(text):
                        pass
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, None, innerfpath, func, yadodir, toyado,
                                        can_loaded_scaledimage=can_loaded_scaledimage)

            except Exception:
                cw.util.print_ex()

        # 重複チェック。既に処理しているimgpathかどうか
        keypath = imgpath
        if yadodir:
            keypath = cw.util.relpath(keypath, yadodir)
        if not pisc and keypath in imgpaths:
            # ElementTree編集
            set_material(imgpaths[keypath])
        else:
            # 対象画像のコピー先を作成
            if pisc:
                idata = cw.binary.image.code_to_data(imgpath)
                ext = cw.util.get_imageext(idata)
                dname = cw.util.repl_dischar(data.gettext("Property/Name", "simage")) + ext
            elif from_scenario:
                dname = materialpath
            else:
                dname = os.path.basename(imgpath)
            imgdst = cw.util.join_paths(dstdir, dname)
            imgdst = cw.util.dupcheck_plus(imgdst, yado=not yadodir)

            if not yadodir and imgdst.startswith("Yado"):
                imgdst = imgdst.replace(self.yadodir, self.tempdir, 1)

            # 対象画像コピー
            if not os.path.isdir(os.path.dirname(imgdst)):
                os.makedirs(os.path.dirname(imgdst))

            if pisc:
                imgdst = cw.util.dupcheck_plus(imgdst, False)
                with open(imgdst, "wb") as f:
                    f.write(idata)
                    f.flush()
                    f.close()
            else:
                cw.util.copy_scaledimagepaths(imgpath, imgdst, can_loaded_scaledimage)
                if sli:
                    shutil.copy2(sli, imgdst + u".sli")
            # ElementTree編集
            if yadodir:
                materialpath = imgdst.replace(toyado + "/", "", 1)
            else:
                materialpath = imgdst.replace(self.tempdir + "/", "", 1)
            set_material(materialpath)
            if not pisc:
                # 重複して処理しないよう辞書に登録
                imgpaths[keypath] = materialpath

#-------------------------------------------------------------------------------
# 状態取得用メソッド
#-------------------------------------------------------------------------------

    def is_running(self):
        """CWPyスレッドがアクティブかどうかbool値を返す。
        アクティブでない場合は、CWPyRunningErrorを投げて、
        CWPyスレッドを終了させる。
        """
        if not self._running:
            if threading.currentThread() == self:
                raise CWPyRunningError()

        return self._running

    def is_runningstatus(self):
        return self._running

    def is_playingscenario(self):
        return bool(isinstance(self.sdata, cw.data.ScenarioData)\
                    and self.sdata.is_playing and self.ydata and self.ydata.party)

    def is_runningevent(self):
        return self.event.get_event() or\
            self.event.get_effectevent() or\
            pygame.event.peek(USEREVENT) or\
            (self.is_battlestatus() and not (self.battle and self.battle.is_ready())) or\
            self.is_decompressing or self._elapse_time

    def is_reloading(self):
        return self._reloading

    def is_statusbarmask(self):
        return cw.cwpy.setting.statusbarmask and cw.cwpy.is_playingscenario() and\
               not self.is_processing and self.ydata and self.ydata.party and not self.ydata.party.is_loading()

    def is_showingdlg(self):
        return 0 < self._showingdlg

    def is_expanded(self):
        return self.setting.is_expanded

    def is_curtained(self):
        return self._curtained

    def is_dealing(self):
        return self._dealing

    def is_autospread(self):
        return self._autospread

    def is_gameover(self):
        if self.is_playingscenario() and not self._forcegameover:
            self._gameover = True
            pcards = self.get_pcards("unreversed")
            for pcard in pcards:
                if pcard.is_alive():
                    self._gameover = False
                    break
            self._gameover |= not bool(pcards)

        return self._gameover

    def is_forcegameover(self):
        return self._forcegameover

    def is_showingmessage(self):
        return bool(self.get_messagewindow())

    def is_showingdebugger(self):
        return bool(self.frame.debugger)

    def is_showingbacklog(self):
        return self._is_showingbacklog

    def is_debugmode(self):
        return self.debug

    def is_battlestatus(self):
        """現在のCWPyのステータスが、シナリオバトル中かどうか返す。
        if cw.cwpy.battle:と使い分ける。
        """
        return cw.cwpy.is_playingscenario() and self.status == "ScenarioBattle"

#-------------------------------------------------------------------------------
# 各種スプライト取得用メソッド
#-------------------------------------------------------------------------------

    def get_inusecardimg(self):
        """InuseCardImageインスタンスを返す(使用カード)。"""
        if self.inusecards:
            return self.inusecards[0]
        else:
            return None

    def get_guardcardimg(self):
        """InuseCardImageインスタンスを返す(防御・回避ボーナスカード)。"""
        if self.guardcards:
            return self.guardcards[0]
        else:
            return None

    def get_messagewindow(self):
        """MessageWindow or SelectWindowインスタンスを返す。"""
        sprites = self.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE)
        if sprites:
            return sprites[0]
        sprites = self.cardgrp.get_sprites_from_layer(cw.LAYER_SPMESSAGE)
        if sprites:
            return sprites[0]
        return None

    def get_mcards(self, mode="", flag=""):
        """MenuCardインスタンスのリストを返す。
        mode: "visible" or "invisible" or "visiblemenucards" or "flagtrue"
        """
        if mode == "visible":
            mcards = [m for m in self.get_mcards(flag=flag) if not m.status == "hidden"]
        elif mode == "invisible":
            mcards = [m for m in self.get_mcards(flag=flag) if m.status == "hidden"]
        elif mode == "visiblemenucards":
            mcards = [m for m in self.get_mcards(flag=flag) if not m.status == "hidden"
                                and isinstance(m, cw.sprite.card.MenuCard)]
        elif mode == "flagtrue":
            mcards = [m for m in self.get_mcards(flag=flag)
                            if not isinstance(m, cw.character.Friend)
                                    and m.is_flagtrue()]
        elif flag:
            mcards = self._mcardtable.get(flag, [])
        else:
            mcards = self.mcards
            if self.is_battlestatus() and self.battle and self.battle.is_running():
                # 戦闘行動中はNPCを除外(一時的に表示されている可能性があるため)
                mcards = [m for m in mcards
                          if not isinstance(m, (cw.character.Friend, cw.sprite.background.InuseCardImage))]
            else:
                mcards = [m for m in mcards
                          if not isinstance(m, cw.sprite.background.InuseCardImage)]

        return mcards

    def get_ecards(self, mode=""):
        """現在表示中のEnemyCardインスタンスのリストを返す。
        mode: "unreversed" or "active"
        """
        if not self.is_battlestatus():
            return []

        ecards = self.get_mcards("visible")

        if mode == "unreversed":
            ecards = [ecard for ecard in ecards if not ecard.is_reversed()]
        elif mode == "active":
            ecards = [ecard for ecard in ecards if ecard.is_active()]

        ecards = filter(lambda ecard: isinstance(ecard, cw.character.Enemy), ecards)

        return ecards

    def get_pcards(self, mode=""):
        """PlayerCardインスタンスのリストを返す。
        mode: "unreversed" or "active"
        """
        if mode == "unreversed":
            pcards = [pcard for pcard in self.get_pcards() if not pcard.is_reversed()]
        elif mode == "active":
            pcards = [pcard for pcard in self.get_pcards() if pcard.is_active()]
        else:
            pcards = self.pcards
            pcards = [m for m in pcards
                      if not isinstance(m, (cw.character.Friend, cw.sprite.background.InuseCardImage))]

        return pcards

    def get_fcards(self, mode=""):
        """FriendCardインスタンスのリストを返す。
        シナリオプレイ中以外は空のリストを返す。
        mode: "unreversed" or "active"
        """
        if not self.is_playingscenario():
            return []

        fcards = self.sdata.friendcards
        if mode == "unreversed":
            fcards = [fcard for fcard in fcards if not fcard.is_reversed()]
        elif mode == "active":
            fcards = [fcard for fcard in fcards if fcard.is_active()]

        return fcards


_mutex_postevent = threading.Lock()

@synclock(_mutex_postevent)
def post_pygameevent(event):
    """pygameイベントをキューへ投入する。
    投入に失敗した場合は一度だけ入力イベントを
    クリアしてからの再投入を試みる。
    """
    try:
        pygame.event.post(event)
    except:
        # 入力イベントが輻輳している場合はクリアする
        cw.cwpy.clear_inputevents()
        pygame.event.post(event)


class ShowMenuCards(object):
    def __init__(self, cwpy):
        self.cwpy = cwpy
        self.rect = pygame.Rect(cw.s((0, 0)), cw.s(cw.SIZE_AREA))

    def lclick_event(self):
        cw.cwpy.wait_showcards = False

    def rclick_event(self):
        cw.cwpy.wait_showcards = False

def main():
    pass

if __name__ == "__main__":
    main()
