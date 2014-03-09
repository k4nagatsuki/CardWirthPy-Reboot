#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import threading
import shutil
import re
import wx
import pygame
from pygame.locals import *

import cw
import cw.binary.image


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
            self.sct = cw.setting.ScenarioCompatibilityTable() # 互換性データベース
            self._running = False
            self.init_pygame(setting)

    def init_pygame(self, setting):
        """使用変数等はここ参照。"""
        self.setting = setting  # 設定
        self.status = "Title"
        self.expand_mode = setting.expandmode

        # pygame初期化
        fullscreen = self.setting.is_expanded and self.setting.expandmode == "FullScreen"
        self.scr, self.scr_fullscreen, self.clock = cw.util.init(cw.SIZE_GAME, "", fullscreen, self.setting.soundfonts)
        if fullscreen:
            func = self.frame.ShowFullScreen
            self.frame.exec_func(func, True)
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
        self.is_pcardsselectable = True
        self.is_mcardsselectable = True
        # 現在カードの表示・非表示アニメ中フラグ
        self._dealing = False
        # カード自動配置フラグ
        self._autospread = True
        # ゲームオーバフラグ(イベント終了処理時にチェック)
        self._gameover = False
        # 現在選択中スプライト(SelectableSprite)
        self.selection = None
        # Trueの間は選択中のスプライトのクリックを行えない
        self.lock_menucards = False
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
        # シナリオ履歴(起動してから開いたシナリオのデータを管理するクラス)
        self.recenthistory = self.setting.recenthistory
        # MusicInterfaceインスタンス
        self.music = cw.util.MusicInterface()
        # EventInterfaceインスタンス
        self.event = cw.event.EventInterface()
        # Spriteグループ
        self.bggrp = pygame.sprite.LayeredDirty()
        self.mcardgrp = pygame.sprite.LayeredDirty()
        self.pcardgrp = pygame.sprite.LayeredDirty()
        self.topgrp = pygame.sprite.LayeredDirty()
        self.backloggrp = pygame.sprite.LayeredDirty()
        self.sbargrp = pygame.sprite.LayeredDirty()
        # 使用中カード
        self.inusecards = []
        self.guardcards = []
        # エリアID
        self.areaid = 1
        # 戦闘エリア移動前のエリアデータ(ID, MusicFullPath, BattleMusicPath)
        self.pre_battleareadata = None
        # 特殊エリア移動前に保持しておく各種データ
        self.pre_areaids = []
        self.pre_mcards = []
        self.pre_dialogs = []
        # 各種入力イベント
        self.mousein = (0, 0, 0)
        self.mousepos = (-1, -1)
        self.mousemotion = False
        self.keyin = ()
        self.events = []
        # list, index(キーボードでのカード選択に使う)
        self.list = []
        self.index = -1
        # カード選択ダイアログで選択中のカード種別
        self.lastcardpocket = 0
        # クラシックなシナリオの再生中であればそのデータ
        self.classicdata = None
        # イベントハンドラ
        self.eventhandler = cw.eventhandler.EventHandler()
        # ゲーム状態を"Title"にセット
        self.exec_func(self.startup)

    def _init_resources(self):
        try:
            """スキンが関わるリソースの初期化"""
            # リソース(辞書)
            rsrc = self.rsrc
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
            else:
                self.rsrc.actioncards = self.rsrc.get_actioncards()
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

            self.init_fullscreenparams()

        except cw.setting.NoFontError, ex:
            def func():
                s = (u"CardWirthPyの実行に必要なフォントがありません。\n"
                     u"Data/Font以下にIPAフォントをインストールしてください。")
                wx.MessageBox(s, u"メッセージ", wx.OK|wx.ICON_ERROR, cw.cwpy.frame)
                cw.cwpy.frame.Destroy()
            cw.cwpy.frame.exec_func(func)

    def _update_clip(self):
        self.bggrp.set_clip(self.background.rect)
        self.mcardgrp.set_clip(self.background.rect)
        self.pcardgrp.set_clip(self.background.rect)
        self.topgrp.set_clip(self.background.rect)
        self.backloggrp.set_clip(self.background.rect)

    def update_skin(self, skindirname, changearea=True):
        if self.status == "Title":
            changearea=False
            self.mcardgrp.empty()
            self.background.bgs = []

        if self.ydata:
            changed = self.ydata.is_changed()
            self.ydata.set_skinname(skindirname)
        oldskindirname = self.setting.skindirname
        self.setting.skindirname = skindirname
        self.setting.init_skin()
        self.skindir = self.setting.skindir
        oldskindir = cw.util.join_paths("Data/Skin", oldskindirname)
        newskindir = cw.util.join_paths("Data/Skin", skindirname)
        self.background.update_skin(oldskindir, newskindir)
        def repl_cardimg(sprite):
            if hasattr(sprite, "cardimg"):
                if sprite.cardimg.path.startswith(oldskindir):
                    sprite.cardimg.path = sprite.cardimg.path.replace(oldskindir, newskindir)
        for sprite in self.pcardgrp.sprites():
            repl_cardimg(sprite)

        if self.sdata:
            self.sdata._init_xmlpaths()
            self.sdata._init_sparea_mcards()

        if not self.is_battlestatus() and changearea:
            for sprite in self.mcardgrp.sprites()[:]:
                if not isinstance(sprite, cw.sprite.card.FriendCard):
                    self.mcardgrp.remove(sprite)
            self.sdata.change_data(self.areaid)
            self.set_mcards(self.sdata.get_mcarddata(), False, True, False)
            self.deal_cards()

        self.rsrc = None
        self.update_scale(cw.UP_SCR, changearea)

        if self.is_battlestatus():
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

        if self.status == "Title":
            s = "%s %s" % (cw.APP_NAME, self.setting.skinname)
        elif self.status == "Yado":
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += self.ydata.name
        elif self.status == "Scenario":
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += "%s %s" % (self.ydata.name, self.sdata.name)
        elif self.status == "GameOver":
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += os.path.basename(self.yadodir)
        else:
            s = "%s %s" % (cw.APP_NAME, self.setting.skinname)
        self.set_titlebar(s)

        if self.ydata:
            self.ydata._changed = changed

        if self.status == "Title":
            # タイトル画面にいる場合はロゴ表示前まで戻す
            self.startup()
        else:
            self.music.play(self.music.path, updatepredata=False)

    def update_scale(self, scale, changearea=True):
        """画面の表示倍率を変更する。
        scale: 倍率。1は拡大しない。2で縦横2倍サイズの表示になる。
        """
        if self.ydata:
            changed = self.ydata.is_changed()
        else:
            changed = False

        if cw.UP_SCR <> scale:
            cw.UP_SCR = scale

            flags = 0
            fullscreen = self.is_expanded() and cw.cwpy.setting.expandmode == "FullScreen"
            if fullscreen:
                rect = wx.DisplaySize()
                self.scr_fullscreen = pygame.display.set_mode((rect[0], rect[1]), flags)
                self.scr = pygame.Surface(cw.s(cw.SIZE_GAME)).convert()
            else:
                self.scr_fullscreen = None
                self.scr = pygame.display.set_mode(cw.s(cw.SIZE_GAME), flags)
            cw.cwpy.frame.exec_func(cw.cwpy.frame.SetClientSize, cw.s(cw.SIZE_GAME))

        self._init_resources()
        def func(scale, changearea, changed):
            self.exec_func(self._update_scale2, scale, changearea, changed)
        self.frame.exec_func(func, scale, changearea, changed)

    def _update_scale2(self, scale, changearea, changed):
        self.statusbar.update_scale()
        self.sbargrp.set_clip(self.statusbar.rect)
        if self.sdata:
            self.sdata.update_scale()
            if self.pre_mcards:
                mcarddata = self.sdata.get_mcarddata(self.pre_areaids[-1])
                self.pre_mcards[-1] = self.set_mcards(mcarddata, False, False)
        for sprite in self.mcardgrp.sprites():
            sprite.update_scale()
        for sprite in self.pcardgrp.sprites():
            sprite.update_scale()
        for sprite in self.bggrp.sprites():
            sprite.update_scale()
        for sprite in self.topgrp.sprites():
            sprite.update_scale()
        for sprite in self.backloggrp.sprites():
            sprite.update_scale()
        for sprite in self.get_fcards():
            sprite.update_scale()
        self._update_clip()

        if self.ydata:
            self.ydata._changed = changed

        # 一度マウスポインタを画面外へ出さないと
        # フォーカスを失うことがある
        pos = pygame.mouse.get_pos()
        pygame.mouse.set_pos([-1, -1])
        pygame.mouse.set_pos(pos)

        if changearea:
            self.update()
            self.draw()

    def set_debug(self, debug):
        self.setting.debug = debug
        self.debug = debug
        self.statusbar.change(not self.is_runningevent())

        if self.is_battlestatus():
            # 敵の状態の暴露・非暴露切り替え
            for sprite in self.get_mcards():
                sprite.update_scale()

        if not debug and self.is_showingdebugger():
            self.sounds["page"].play()
            self.frame.exec_func(self.frame.debugger.Close)

        cw.data.redraw_cards(debug)

    def run(self):
        try:
            self._run()
        except CWPyRunningError:
            self.quit()
        except wx.PyDeadObjectError:
            pass

        self._quit()

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
            if update:
                self.update()         # スプライトの更新
            self.draw(True)           # スプライトの描画

    def quit(self):
        # トップフレームから閉じて終了。cw.frame.OnDestroy参照。
        event = wx.PyCommandEvent(wx.wxEVT_DESTROY)
        self.frame.AddPendingEvent(event)

    def _quit(self):
        pygame.quit()
        cw.util.remove_temp()
        self.setting.write()
        self.rsrc.clear_systemfonttable()

    def tick_clock(self, framerate=0):
        if framerate:
            self.clock.tick(framerate)
        else:
            self.clock.tick(self.setting.fps)

    def wait_frame(self, count):
        self.event.eventtimer = 0
        for i in xrange(count):
            self.tick_clock()

    def input(self, eventclear=False, inputonly=False):
        self.mousein = pygame.mouse.get_pressed()
        mousepos = self.mousepos
        if self.update_mousepos():
            self.mousemotion = False if self.mousepos == mousepos else True
        self.keyin = self.keyevent.get_pressed()

        if eventclear:
            pygame.event.clear((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
        elif inputonly:
            self.events = pygame.event.get((MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP))
            if self.events:
                self.events = [self.events[-1]]
        else:
            self.events = pygame.event.get()

    def update_mousepos(self):
        if sys.platform <> "win32":
            return False
        if pygame.mouse.get_focused():
            if self.scr_fullscreen:
                mousepos = pygame.mouse.get_pos()
                x = int((mousepos[0] - self.scr_pos[0]) / self.scr_scale)
                y = int((mousepos[1] - self.scr_pos[1]) / self.scr_scale)
                self.mousepos = (x, y)
            else:
                self.mousepos = pygame.mouse.get_pos()
        else:
            self.mousepos = (-1, -1)
        return True

    def update(self):
        self.bggrp.update(self.scr)
        # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
        if self.sdata and self.sct.lessthan("1.20", self.sdata.get_versionhint(frompos=cw.HINT_AREA)):
            self.pcardgrp.update(self.scr)
            self.mcardgrp.update(self.scr)
        else:
            self.mcardgrp.update(self.scr)
            self.pcardgrp.update(self.scr)
        self.topgrp.update(self.scr)
        self.sbargrp.update(self.scr)
        if not self.statusbar.showbuttons:
            if not self.is_runningevent() and not self.areaid in cw.AREAS_TRADE and not self.selectedheader:
                self.statusbar.change()

    def draw_cards(self, scr):
        # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画される
        dirty_rects = []
        if self.sdata and self.sct.lessthan("1.20", self.sdata.get_versionhint(frompos=cw.HINT_AREA)):
            dirty_rects.extend(self.pcardgrp.draw(self.scr))
            dirty_rects.extend(self.mcardgrp.draw(self.scr))
        else:
            dirty_rects.extend(self.mcardgrp.draw(self.scr))
            dirty_rects.extend(self.pcardgrp.draw(self.scr))
        return dirty_rects

    def draw(self, mainloop=False, clip=None):
        if self.has_inputevent or not mainloop:
            # FIXME: 描画領域を絞り込むと時々カードの描画中に
            #        次に表示される背景が映り込んでしまう
            clip = None
            # SpriteGroup描画
            self.scr.set_clip(clip)
            self.bggrp.set_clip(clip)
            self.pcardgrp.set_clip(clip)
            self.mcardgrp.set_clip(clip)
            self.topgrp.set_clip(clip)
            self.backloggrp.set_clip(clip)
            self.sbargrp.set_clip(clip)

            dirty_rects = self.bggrp.draw(self.scr)

            dirty_rects.extend(self.draw_cards(self.scr))

            dirty_rects.extend(self.topgrp.draw(self.scr))
            dirty_rects.extend(self.backloggrp.draw(self.scr))
            if self.music.movie_scr:
                self.scr.blit(self.music.movie_scr, (0, 0))
            dirty_rects.extend(self.sbargrp.draw(self.scr))

            # FPS描画
            if self.setting.showfps:
                sur = self.fpsfont.render(str(int(self.clock.get_fps())), False, (0, 255, 255))
                pos = cw.s((600, 5))
                dirty_rects.append(self.scr.blit(sur, pos))

            # 画面更新
            if self.scr_fullscreen:
                if clip:
                    clx = int(clip.left * self.scr_scale) - 2
                    cly = int(clip.top * self.scr_scale) - 2
                    clw = int(clip.width * self.scr_scale) + 5
                    clh = int(clip.height * self.scr_scale) + 5
                    scr = pygame.transform.smoothscale(self.scr, self.scr_size)
                    clip2 = pygame.Rect(clx, cly, clw, clh)
                    clip3 = pygame.Rect(clx + self.scr_pos[0], cly + self.scr_pos[1], clw, clh)
                    self.scr_fullscreen.blit(scr, clip3.topleft, clip2)
                    pygame.display.update(clip3)
                else:
                    scr = pygame.transform.smoothscale(self.scr, self.scr_size)
                    self.scr_fullscreen.blit(scr, self.scr_pos)
                    pygame.display.update()
            else:
                if clip:
                    pygame.display.update(clip)
                else:
                    pygame.display.update(dirty_rects)

            self.scr.set_clip(None)
            self.bggrp.set_clip(None)
            self.pcardgrp.set_clip(None)
            self.mcardgrp.set_clip(None)
            self.topgrp.set_clip(None)
            self.backloggrp.set_clip(None)
            self.sbargrp.set_clip(None)

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

            # 壁紙
            self.scr_fullscreen.fill((255, 255, 255))
            wximg = cw.image.conv2surface(cw.cwpy.rsrc.dialogs["PAD"])
            padsize = wximg.get_size()
            for x in xrange(0, fsize[0], padsize[0]):
                for y in xrange(0, fsize[1], padsize[1]):
                    self.scr_fullscreen.blit(wximg, (x, y))
        else:
            self.scr_size = self.scr.get_size()
            self.scr_scale = 1.0
            self.scr_pos = (0, 0)

    def call_dlg(self, name, **kwargs):
        """ダイアログを開く。
        name: ダイアログ名。cw.frame参照。
        """
        self.lock_menucards = True
        self._showingdlg += 1
        self.keyevent.clear() # キー入力初期化
        event = wx.PyCommandEvent(self.frame.dlgeventtypes[name])
        event.args = kwargs
        if threading.currentThread() == self:
            self.frame.AddPendingEvent(event)
            if sys.platform == "win32":
                while self.is_running() and self.frame.IsEnabled():
                    pass
        else:
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
        if self.pre_dialogs:
            pre_info = self.pre_dialogs[-1]
            callname = pre_info[0]

            if callname == "CARDPOCKET":
                # ゲームオーバーになった場合は開かない
                if cw.cwpy.is_gameover():
                    self.pre_dialogs.pop()
                    return

                # 手札カードダイアログの選択者が
                # 対象消去されている場合は開かない
                indexs = pre_info[1]
                index2 = indexs[1]
                if isinstance(index2, cw.character.Character) and\
                        index2.is_vanished():
                    self.pre_dialogs.pop()
                    return

            self.call_modaldlg(callname)

    def exec_func(self, func, *args, **kwargs):
        """CWPyスレッドで指定したファンクションを実行する。
        func: 実行したいファンクションオブジェクト。
        """
        event = pygame.event.Event(pygame.USEREVENT, func=func, args=args,
                                                                kwargs=kwargs)
        pygame.event.post(event)

    def sync_exec(self, func, *args, **kwargs):
        """CWPyスレッドで指定したファンクションを実行し、
        終了を待ち合わせる。ファンクションの戻り値を返す。
        func: 実行したいファンクションオブジェクト。
        """
        if threading.currentThread() == self:
            return func(*args, **kwargs)
        else:
            result = [None]
            isrun = True
            def func2(result, func, *args, **kwargs):
                result[0] = func(*args, **kwargs)
                isrun = False
            self.exec_func(func2, result, func, *args, **kwargs)
            while isrun and self.frame.IsEnabled() and self.is_running():
                time.sleep(0.001)
            return result[0]

    def set_expanded(self, flag, expandmode=""):
        """拡大表示する。すでに拡大表示されている場合は解除する。
        flag: Trueなら拡大表示、Falseなら解除。
        """
        if self.is_expanded() == flag:
            return

        if not expandmode:
            expandmode = self.expand_mode if self.is_expanded() else self.setting.expandmode

        if expandmode == "None":
            return

        elif expandmode == "FullScreen":
            # フルスクリーン
            if self.is_showingdebugger() and flag:
                self.sounds["error"].play()
                s = u"デバッガ表示中はフルスクリーン化できません。"
                self.call_modaldlg("MESSAGE", text=s)
            else:
                pos = pygame.mouse.get_pos()
                pygame.mouse.set_pos([-1, -1])

                self.setting.is_expanded = flag
                if flag:
                    self.expand_mode = expandmode
                    rect = wx.DisplaySize()
                    self.scr_fullscreen = pygame.display.set_mode((rect[0], rect[1]), 0)
                    self.scr = pygame.Surface(cw.s(cw.SIZE_GAME)).convert()
                    func = self.frame.ShowFullScreen
                    self.frame.exec_func(func, True)
                else:
                    self.expand_mode = "None"
                    self.scr_fullscreen = None
                    self.scr = pygame.display.set_mode(cw.s(cw.SIZE_GAME), 0)
                    func = self.frame.ShowFullScreen
                    self.frame.exec_func(func, False)
                self.init_fullscreenparams()

                while not self.frame.IsFullScreen() == flag:
                    pass

                # 一度マウスポインタを画面外へ出さないと
                # フォーカスを失うことがある
                pygame.mouse.set_pos(pos)

        else:
            # 拡大
            try:
                scale = float(expandmode)
                scale = max(scale, 0.5)
                scale = min(scale, 8)
                self.setting.is_expanded = flag
                if flag:
                    self.expand_mode = expandmode
                    self.update_scale(scale)
                else:
                    self.expand_mode = "None"
                    self.update_scale(1)

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

        while self.is_running() and mwin.result is None:
            self.event.refresh_activeitem()
            self.update()

            if mwin.result is None:
                self.draw(not mwin.is_drawing or self.has_inputevent)

            self.tick_clock()
            self.input()
            eventhandler.run()
        self.clear_selection()
        self.lock_menucards = locks

        # バックログの保存
        if isinstance(mwin.result, int) and\
                isinstance(self.sdata, cw.data.ScenarioData) and\
                not isinstance(mwin, cw.sprite.message.MemberSelectWindow):
            if self.setting.backlogmax <= len(self.sdata.backlog):
                self.sdata.backlog.pop(0)
            self.sdata.backlog.append(cw.sprite.message.BacklogData(mwin))

        # cwpylist, index 初期化
        self.list = self.get_mcards("visible")
        self.index = -1
        # スプライト削除
        self.topgrp.remove_sprites_of_layer("selectionbar")
        self.topgrp.remove_sprites_of_layer("message")

        # 互換性マーク削除
        if self.is_playingscenario():
            self.sdata.versionhint[cw.HINT_MESSAGE] = ""

        # メッセージ表示中にシナリオ強制終了(F9)などを行った場合、
        # イベント強制終了用のエラーを送出する。
        if isinstance(mwin.result, Exception):
            raise mwin.result
        else:
            return mwin.result

    def show_backlog(self, n=0):
        """直近から過去に遡ってn回目のメッセージを表示する。
        n: 遡る量。0なら最後に閉じたメッセージ。
        もっとも古いメッセージよりも大きな値の場合は
        もっとも古いメッセージを表示する。
        """
        if not (isinstance(self.sdata, cw.data.ScenarioData) and self.sdata.backlog):
            return

        if len(self.sdata.backlog) <= n:
            n = len(self.sdata.backlog) - 1
        index = len(self.sdata.backlog) - 1 - n

        eventhandler = cw.eventhandler.EventHandlerForBacklog(self.sdata.backlog, index)
        while self.is_running() and eventhandler.mwin and\
                cw.cwpy.sdata.is_playing and self._is_showingbacklog:
            self.sbargrp.update(self.scr)
            self.draw()
            self.tick_clock()
            self.input()
            eventhandler.run()
        else:
            # 表示終了
            eventhandler.exit_backlog(playsound=False)

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
        self.status = name
        self.hide_cards(True)
        self.pre_areaids = []
        self.pre_dialogs = []
        self.pre_mcards = []

    def startup(self):
        """起動時のアニメーションを表示してから
        タイトル画面へ遷移する。"""
        resdir = cw.util.join_paths(cw.cwpy.skindir, u"Resource/Image/Other")
        self.events = []

        # 必要なスプライトの読み込み
        self._init_resources()
        self.music.stop()
        ext = self.rsrc.ext_img
        path = cw.util.join_paths(resdir, "TITLE_CARD1") + ext
        card1 = cw.sprite.background.TitleCell(path, 1, 120, True)
        path = cw.util.join_paths(resdir, "TITLE_CARD2") + ext
        card2 = cw.sprite.background.TitleCell(path, 1, 120, True)
        path = cw.util.join_paths(resdir, "TITLE_CELL1") + ext
        cell1 = cw.sprite.background.TitleCell(path, 2, 195, False)
        path = cw.util.join_paths(resdir, "TITLE_CELL2") + ext
        cell2 = cw.sprite.background.TitleCell(path, 2, 195, False)
        path = cw.util.join_paths(resdir, "TITLE_CELL3") + ext
        cell3 = cw.sprite.background.TitleCell(path, 2, 160, False)
        white = cw.sprite.background.TitleCell("white", 3, 0, False)
        self.selection = white

        cw.cwpy.topgrp.add(card1, layer="title")
        cw.cwpy.topgrp.add(card2, layer="title")
        cw.cwpy.topgrp.add(cell1, layer="title")
        cw.cwpy.topgrp.add(cell2, layer="title")
        cw.cwpy.topgrp.add(cell3, layer="title")
        cw.cwpy.topgrp.add(white, layer="title")

        self.lock_menucards = False
        cw.animation.animate_sprite(card2, "deal", clearevent=False)
        cw.animation.animate_sprite(card2, "hide", clearevent=False)
        cw.animation.animate_sprite(card1, "deal", clearevent=False)
        cw.animation.animate_sprite(card1, "hide", clearevent=False)
        cw.animation.animate_sprites2([(card2, "deal"), (cell1, "fadein")], clearevent=False)
        cw.animation.animate_sprite(card2, "hide", clearevent=False)
        cw.animation.animate_sprite(card1, "deal", clearevent=False)
        cw.animation.animate_sprites2([(card1, "hide"), (cell1, "vanish"), (cell2, "show")], clearevent=False)
        cw.animation.animate_sprite(card2, "deal", clearevent=False)
        cw.animation.animate_sprite(card2, "hide", clearevent=False)
        cw.animation.animate_sprite(card1, "deal", clearevent=False)
        cw.animation.animate_sprites2([(card1, "hide"), (cell2, "fadeout")], clearevent=False)
        cw.animation.animate_sprite(card2, "deal", clearevent=False)
        cw.animation.animate_sprite(card2, "hide", clearevent=False)
        cw.animation.animate_sprite(card1, "deal", clearevent=False)
        cw.animation.animate_sprite(card1, "hide", clearevent=False)
        cw.animation.animate_sprites2([(card2, "deal"), (cell3, "fadein")], clearevent=False)
        cw.animation.animate_sprite(card2, "hide", clearevent=False)
        cw.animation.animate_sprite(card1, "deal", clearevent=False)
        cw.animation.animate_sprite(card1, "hide", clearevent=False)
        cw.animation.animate_sprite(card2, "deal", clearevent=False)
        cw.animation.animate_sprites2([(card2, "hide"), (white, "fadein2")], clearevent=False)
        for i in xrange(self.setting.fps / 2):
            if self.cut_animation:
                break
            self.tick_clock()
        self.selection = None

        # スプライトを解除する
        self.topgrp.remove_sprites_of_layer("title")

        if self.cut_animation:
            ttype = ("Default", "Default")
            self.cut_animation = False
        else:
            ttype = ("None", "None")
            self.wait_showcards = True
        self.set_title(ttype=ttype)

    def set_title(self, init=True, ttype=("Default", "Default")):
        """タイトル画面へ遷移。"""
        self.set_status("Title")
        cw.util.remove_temp()
        self.yadodir = ""
        self.tempdir = ""
        self.setting.lastscenario = []
        self.ydata = None
        self.sdata = cw.data.SystemData()
        s = "%s %s" % (cw.APP_NAME, self.setting.skinname)
        self.set_titlebar(s)
        self.statusbar.change()
        self.change_area(1, ttype=ttype)

    def set_yado(self):
        """宿画面へ遷移。"""
        self.set_status("Yado")
        self.sdata = cw.data.SystemData()
        s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
        s += self.ydata.name
        self.set_titlebar(s)
        # 冒険の中断やF9時のためにカーテン消去
        self.clear_curtain()
        self.statusbar.change()

        if self.ydata.party:
            areaid = 2
            self.ydata.party.remove_numbercoupon()
        else:
            areaid = 1

        if self.setting.store_skinoneachbase and self.ydata.skinname <> cw.cwpy.setting.skinname:
            self.update_skin(self.ydata.skinname, changearea=False)

        self.change_area(areaid)

    def set_scenario(self, header=None, lastscenario=[]):
        """シナリオ画面へ遷移。
        header: ScenarioHeader
        """
        self.set_status("Scenario")
        self.battle = None
        self.statusbar.change(False)

        if self.setting.store_skinoneachbase and self.ydata.skinname <> cw.cwpy.setting.skinname:
            self.update_skin(self.ydata.skinname, changearea=False)

        if header and not isinstance(self.sdata, cw.data.ScenarioData):
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.sdata = cw.data.ScenarioData(header)
            loaded, musicpath = self.sdata.set_log()
            self.sdata.start()
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += "%s %s" % (self.ydata.name, self.sdata.name)
            self.set_titlebar(s)
            areaid = self.sdata.startid
            if lastscenario:
                self.ydata.party.set_lastscenario(lastscenario)

            if not loaded:
                self.ydata.party.set_numbercoupon()

            def func(loaded, musicpath, areaid):
                if not self.sdata.startid in self.sdata.areas:
                    # 開始エリアが存在しない(帰還)
                    self.check_level(True)
                    self.set_yado()
                elif musicpath is None or\
                                self.music.path == self.music.get_path(musicpath):
                    self.change_area(areaid, not loaded, loaded)
                else:
                    self.music.stop()
                    self.change_area(areaid, not loaded, loaded)
                    self.music.play(musicpath)
            self.exec_func(func, loaded, musicpath, areaid)

    def set_battle(self):
        """シナリオ戦闘画面へ遷移。"""
        self.set_status("ScenarioBattle")

    def set_gameover(self):
        """ゲームオーバー画面へ遷移。"""
        self.set_status("GameOver")
        self._gameover = False
        self.battle = None
        pygame.event.clear()
        self.ydata.party.lost()
        self.sdata.end()
        self.ydata.load_party(None)
        self.sdata = cw.data.SystemData()
        s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
        s += os.path.basename(self.yadodir)
        self.set_titlebar(s)
        self.statusbar.change()
        self.change_area(1)

    def f9(self, load_failure=False):
        """cw.data.ScenarioDataのf9()から呼び出され、
        緊急避難処理の続きを行う。
        """
        if load_failure == False and not self.is_playingscenario():
            return

        self.sdata.is_playing = False
        self.pre_dialogs = []

        self.clear_inusecardimg()
        self.clear_guardcardimg()

        # 対象選択画面でF9しても、中止ボタンを宿まで持ち越さないように
        self.selectedheader = None

        # battle
        if self.battle and self.battle.is_running:
            # バトルを強制終了
            self.battle.end(True, True)

        # party copy
        fname = os.path.basename(self.ydata.party.data.fpath)
        dname = os.path.basename(os.path.dirname(self.ydata.party.data.fpath))
        path = cw.util.join_paths("Data/Temp/ScenarioLog/Party", fname)
        dstpath = cw.util.join_paths(self.ydata.tempdir, "Party", dname, fname)
        dpath = os.path.dirname(dstpath)

        if not os.path.isdir(dpath):
            os.makedirs(dpath)

        shutil.copy2(path, dstpath)
        # member copy
        dpath = u"Data/Temp/ScenarioLog/Members"

        for name in os.listdir(dpath):
            path = cw.util.join_paths(dpath, name)

            if os.path.isfile(path) and path.endswith(".xml"):
                dstpath = cw.util.join_paths(self.ydata.tempdir,
                                                        "Adventurer", name)

                dstdir = os.path.dirname(dstpath)

                if not os.path.isdir(dstdir):
                    os.makedirs(dstdir)

                shutil.copy2(path, dstpath)

        # gossips
        for key, value in self.sdata.gossips.iteritems():
            if value:
                self.ydata.remove_gossip(key)
            else:
                self.ydata.set_gossip(key)

        # completestamps
        for key, value in self.sdata.compstamps.iteritems():
            if value:
                self.ydata.remove_compstamp(key)
            else:
                self.ydata.set_compstamp(key)

        # scenario
        self.ydata.party.set_lastscenario([])

        # members
        self.ydata.party.data = cw.data.yadoxml2etree(self.ydata.party.data.fpath)
        self.ydata.party.reload()

        # 荷物袋のデータを戻す
        path = "Data/Temp/ScenarioLog/Backpack.xml"
        etree = cw.data.xml2etree(path)
        backpacktable = {}
        yadodir = self.ydata.party.get_yadodir()
        tempdir = self.ydata.party.get_tempdir()

        for header in self.ydata.party.backpack + self.ydata.party.backpack_moved:
            if header.scenariocard:
                header.contain_xml()
                continue

            if header.fpath.lower().startswith("yado"):
                fpath = os.path.relpath(header.fpath, yadodir)
            else:
                fpath = os.path.relpath(header.fpath, tempdir)
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
                    if not header.carddata is None:
                        etree = cw.data.xml2etree(element=header.carddata)
                        etree.remove("Property", attrname="moved")
                        header.write()
                    header.moved = 0
                self.ydata.party.backpack.append(header)
                header.order = i
                header.set_owner("BACKPACK")
                # 荷物袋にある場合はcarddata無し、特殊技能の使用回数無し
                header.carddata = None
                if header.type == "SkillCard":
                    header.maxuselimit = 0
                    header.uselimit = 0
            except Exception, ex:
                cw.util.print_ex()

        self.sdata.remove_log()

        if not self.areaid > 0:
            self.areaid = self.pre_areaids[0]

        # スプライトを作り直す
        pcards = self.get_pcards()
        showparty = bool(self.pcardgrp.get_sprites_from_layer(0))
        if showparty:
            self.music.stop()
        for idx, data in enumerate(self.ydata.party.members):
            if showparty:
                self.sounds["harvest"].play()
                if idx < len(pcards):
                    pcard = pcards[idx]
                    cw.animation.animate_sprite(pcard, "hide")
                    self.pcardgrp.remove(pcard)

            pos_noscale = (95 * idx + 9 * (idx + 1), 285)
            pcard = cw.sprite.card.PlayerCard(data, pos_noscale=pos_noscale)
            pcard.set_pos_noscale(pos_noscale)
            pcard.set_fullrecovery()

            if showparty:
                cw.animation.animate_sprite(pcard, "deal")

        self.ydata.party._loading = False

        self.set_yado()

    def reload_yado(self):
        """現在の宿をロード。"""
        # イベントを中止
        self.event._stoped = True
        self.event.breakwait = True
        def func1():
            if self.is_showingmessage():
                mwin = self.get_messagewindow()
                mwin.result = cw.event.EffectBreakError()
            elif self.is_runningevent():
                self.event._stoped = True
            self.sdata.is_playing = False

        def func2():
            # バトルを強制終了
            if self.battle and self.battle.is_running:
                self.battle.end(True, True)

        def func3():
            # シナリオを強制終了
            if self.is_playingscenario():
                self.sdata.end()

        def func4():
            self.event._stoped = False
            self.event.breakwait = False
            self._init_resources()

        def func5():
            def func():
                self.set_status("Title")
                self.sdata = cw.data.SystemData()
                cw.util.remove_temp()
                self.load_yado(self.yadodir)
            self.exec_func(func)

        self.exec_func(func1)
        self.exec_func(func2)
        self.exec_func(func3)
        self.exec_func(func4)
        self.frame.exec_func(func5)

    def load_yado(self, yadodir):
        """指定されたディレクトリの宿をロード。"""
        self.yadodir = yadodir.replace("\\", "/")
        self.tempdir = self.yadodir.replace("Yado",
                                                    "Data/Temp/Yado", 1)
        self.music.stop()
        self.ydata = cw.data.YadoData(self.yadodir, self.tempdir)
        self.setting.lastyado = self.ydata.name

        if self.ydata.party:
            header = self.ydata.party.get_sceheader()

            # シナリオプレイ途中から再開
            if header:
                self.exec_func(self.set_scenario, header)
            # シナリオロードに失敗
            elif self.ydata.party.is_adventuring():
                self.sounds["error"].play()
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

        def clear_changed():
            self.ydata._changed = False
        self.exec_func(clear_changed)

#-------------------------------------------------------------------------------
# エリアチェンジ関係メソッド
#-------------------------------------------------------------------------------

    def deal_cards(self, quickdeal=False):
        """hidden状態のMenuCard(対応フラグがFalseだったら表示しない)と
        PlayerCardを全て表示する。
        quickdeal: 前カードを同時に表示する。
        """
        if not self.setting.quickdeal:
            quickdeal = False
        self._dealing = True

        mcardsinv = self.get_mcards("invisible")

        # エネミーカードは初期化されていない場合がある
        for mcard in mcardsinv:
            if isinstance(mcard, cw.sprite.card.EnemyCard):
                if self.sdata.flags.get(mcard.flag, True):
                    mcard.initialize()

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
            if self.sdata.flags.get(mcard.flag, True) and\
                    (not mcard.debug_only or self.is_debugmode()):
                if quickdeal:
                    deals.append(mcard)
                else:
                    cw.animation.animate_sprite(mcard, "deal")

        if quickdeal:
            cw.animation.animate_sprites(deals, "deal")

        # list, indexセット
        if not self.is_showingmessage():
            self.list = self.get_mcards("visible")
            self.index = -1

        self.input(True)
        self._dealing = False
        self.wait_showcards = False

    def hide_cards(self, hideall=False, hideparty=True, quickhide=False):
        """
        カードを非表示にする(表示中だったカードはhidden状態になる)。
        各カードのhidecards()の最後に呼ばれる。
        hideallがTrueだった場合、全てのカードを非表示にする。
        """
        if not self.setting.quickdeal:
            quickhide = False
        self._dealing = True
        # 選択を解除する
        self.clear_selection()

        # メニューカードを下げる
        mcards = self.get_mcards("visible")
        for mcard in mcards:
            if hideall or\
                    not self.sdata.flags.get(mcard.flag, True) or\
                    (mcard.debug_only and not self.is_debugmode()):
                if mcard.inusecardimg:
                    self.clear_inusecardimg(mcard)
                if not quickhide:
                    cw.animation.animate_sprite(mcard, "hide")
        if quickhide:
            cw.animation.animate_sprites(mcards, "hide")

        # プレイヤカードを下げる
        if self.ydata and hideparty:
            if not self.ydata.party or self.ydata.party.is_loading():
                self.hide_party()

        # list, indexセット
        if not self.is_showingmessage():
            self.list = self.get_mcards("visible")
            self.index = -1

        self.input(True)
        self._dealing = False

    def show_party(self):
        """非表示のPlayerCardを再表示にする。"""
        pcards = [i for i in self.get_pcards() if i.status == "hidden"]

        if pcards:
            cw.animation.animate_sprites(pcards, "shiftup")

        self.is_showparty = True
        self.input(True)
        self.event.refresh_showpartytools()

    def hide_party(self):
        """PlayerCardを非表示にする。"""
        pcards = [i for i in self.get_pcards() if not i.status == "hidden"]

        if pcards:
            self.clear_inusecardimg()
            cw.animation.animate_sprites(pcards, "shiftdown")

        self.is_showparty = False
        self.input(True)
        self.event.refresh_showpartytools()

    def set_sprites(self, dealanime=True,
                                bginhrt=False, ttype=("Default", "Default")):
        """エリアにスプライトをセットする。
        bginhrt: Trueの時は背景継承。
        """
        # メニューカードスプライトグループの中身を削除
        self.mcardgrp.empty()

        # プレイヤカードスプライトグループの中身を削除
        if self.ydata:
            if not self.ydata.party or self.ydata.party.is_loading():
                self.pcardgrp.empty()

        # 背景スプライト作成
        if not bginhrt:
            bginhrt |= self.sdata.check_bginhrt()
            self.background.load(self.sdata.get_bgdata(), bginhrt, True, ttype)

        # 特殊エリア(キャンプ・メンバー解散)だったら背景にカーテンを追加。
        if self.areaid in (cw.AREA_CAMP, cw.AREA_BREAKUP):
            self.set_curtain()

        # メニューカードスプライト作成
        self.set_mcards(self.sdata.get_mcarddata(), dealanime)

        # プレイヤカードスプライト作成
        if self.ydata and self.ydata.party and not self.get_pcards():
            for idx, e in enumerate(self.ydata.party.members):
                pos_noscale = 95 * idx + 9 * (idx + 1), 285
                cw.sprite.card.PlayerCard(e, pos_noscale=pos_noscale)

            # 番号クーポン設定
            self.ydata.party._loading = False

        # キャンプ画面のときはFriendCardもスプライトグループに追加
        if self.areaid == cw.AREA_CAMP:
            for index, fcard in enumerate(self.get_fcards()):
                index = 5 - index
                pos = (95 * index + 9 * (index + 1), 5)
                fcard.set_pos_noscale(pos)
                fcard.clear_image()
                fcard.status = "hidden"
                self.mcardgrp.add(fcard)

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
            y = (285 - maxh * 2) / 2
            y2 = y + maxh + 5
            p = n / 2 + n % 2
            set_mcardpos_noscale(mcards[:p], (maxw, maxh), y)
            set_mcardpos_noscale(mcards[p:], (maxw, maxh), y2)

        if anime:
            for mcard in mcards:
                cw.animation.animate_sprite(mcard, "deal")

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

        for index, e in enumerate(elements):
            if stype == "Auto":
                pos_noscale = (0, 0)
            else:
                left = e.getint("Property/Location", "left")
                top = e.getint("Property/Location", "top")
                pos_noscale = (left, top)

            if e.tag == "EnemyCard":
                mcard = cw.sprite.card.EnemyCard(e, pos_noscale, status, addgroup)
            else:
                mcard = cw.sprite.card.MenuCard(e, pos_noscale, status, addgroup)
            if not self.sdata.flags.get(mcard.flag, True) or (mcard.debug_only and not self.is_debugmode()):
                mcard.status = "hidden"
            seq.append(mcard)
        return seq

    def disposition_pcards(self):
        """プレイヤーカードの位置を補正する。
        対象消去が発生した場合や解散直後に適用。
        """
        for index, pcard in enumerate(self.get_pcards()):
            assert not pcard.zoomimgs
            x = 9 + 95 * index + 9 * index
            y = pcard._pos_noscale[1]
            pcard.rect[0] = cw.s(x)
            pcard._rect[0] = cw.s(x)
            pcard.cardimg.rect[0] = cw.s(x)
            pcard._pos_noscale = (x, y)

    def change_area(self, areaid, eventstarting=True,
                          bginhrt=False, ttype=("Default", "Default"),
                          quickdeal=False, specialarea=False, startbattle=False):
        """ゲームエリアチェンジ。
        eventstarting: Falseならエリアイベントは起動しない。
        bginhrt: 背景継承を行うかどうかのbool値。
        ttype: トランジション効果のデータのタプル((効果名, 速度))
        """
        # デバッガ等で強制的にエリア移動するときは特殊エリアを解除する
        if not specialarea:
            self.clean_specials()

        # 背景継承を行うかどうかのbool値
        bginhrt |= bool(self.areaid < 0 and self.sdata.check_bginhrt())
        oldareaid = self.areaid
        self.areaid = areaid
        self.sdata.change_data(areaid)
        bginhrt |= bool(self.areaid < 0 and self.sdata.check_bginhrt())
        cw.cwpy.hide_cards(True, quickhide=quickdeal)
        self.set_sprites(bginhrt=bginhrt, ttype=ttype)

        if not self.is_playingscenario() and not self.is_showparty:
            # 宿にいる場合は常に全回復状態にする
            for pcard in self.get_pcards():
                pcard.set_fullrecovery()
                pcard.update_image()

        self.disposition_pcards()

        if 0 < oldareaid and self.ydata:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()

        # エリアイベントを開始(特殊エリアからの帰還だったら開始しない)
        if eventstarting and oldareaid > 0:
            if not self.wait_showcards:
                self.deal_cards(quickdeal=quickdeal)
            else:
                self.draw()

            if self.areaid > 0 and self.status == "Scenario":
                self.elapse_time()

            self.sdata.start_event(keynum=1)
        else:
            self.deal_cards(quickdeal=quickdeal)
            if not startbattle and not pygame.event.peek(pygame.locals.USEREVENT):
                self.show_party()

    def change_battlearea(self, areaid):
        """
        指定するIDの戦闘を開始する。
        """
        # 対象選択中であれば中止
        self.clean_specials()

        self.sounds["battle"].play(from_scenario=True)
        self.statusbar.change(False, encounter=True)
        # 戦闘開始アニメーション
        sprite = cw.sprite.background.BattleCardImage()
        cw.animation.animate_sprite(sprite, "battlestart")
        sprite.remove(cw.cwpy.topgrp)
        oldareaid = self.areaid
        oldbgmpath = self.music.path
        if self.pre_battleareadata:
            oldareaid = self.pre_battleareadata[0]
            oldbgmpath = self.pre_battleareadata[1]
        self.set_battle()
        self.change_area(areaid, False, ttype=("None", "Default"), startbattle=True)
        # 戦闘音楽を流す
        path = self.sdata.data.gettext("Property/MusicPath", "")
        self.music.play(path)

        self.pre_battleareadata = (oldareaid, oldbgmpath, self.music.path)
        self.battle = cw.battle.BattleEngine()

    def clear_battlearea(self, areachange=True, eventkeynum=0, startnextbattle=False):
        """戦闘状態を解除して戦闘前のエリアに戻る。
        areachangeがFalseだったら、戦闘前のエリアには戻らない
        (戦闘イベントで、エリア移動コンテント等が発動した時用)。
        """
        if self.status == "ScenarioBattle":
            # 勝利イベントを保持しておく
            battleevents = self.sdata.events
            if eventkeynum:
                self.winevent_areaid = self.areaid

            cw.cwpy.battle = None

            for pcard in self.get_pcards():
                pcard.deck.clear(pcard)

                if not pcard.is_reversed():
                    pcard.remove_timedcoupons(True)

            for fcard in self.get_fcards():
                fcard.deck.clear(fcard)

                if not fcard.is_reversed():
                    fcard.remove_timedcoupons(True)

            areaid, bgmpath, battlebgmpath = self.pre_battleareadata
            if not startnextbattle:
                self.pre_battleareadata = None
            self.set_scenario()

            # BGMを最後に指定されたものに戻す
            self.music.play(bgmpath)

            # 一部ステータスは回復
            for pcard in self.get_pcards():
                if pcard.is_bind() or pcard.mentality <> "Normal":
                    if pcard.status == "hidden" or not pcard.reversed:
                        pcard.set_bind(0)
                        pcard.set_mentality("Normal", 0)
                        pcard.update_image()
                    else:
                        self.sounds["harvest"].play()
                        pcard.set_bind(0)
                        pcard.set_mentality("Normal", 0)
                        cw.animation.animate_sprite(pcard, "hide")
                        pcard.update_image()
                        cw.animation.animate_sprite(pcard, "deal")

            if areachange:
                # 戦闘前のエリアに戻る
                self.change_area(areaid, False, ttype=("None", "Default"), bginhrt=True)

            if eventkeynum:
                # 勝利イベント開始
                battleevents.start(keynum=eventkeynum)
                self.winevent_areaid = None

    def change_specialarea(self, areaid):
        """特殊エリア(エリアIDが負の数)に移動する。"""
        if areaid < 0:
            self.pre_areaids.append(self.areaid)

            # パーティ解散・キャンプエリア移動の場合はエリアチェンジ
            if areaid in (cw.AREA_BREAKUP, cw.AREA_CAMP):
                if cw.cwpy.ydata:
                    changed = cw.cwpy.ydata.is_changed()
                self.change_area(areaid, quickdeal=True, specialarea=True)
                if cw.cwpy.ydata:
                    cw.cwpy.ydata._changed = changed
            else:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.pre_mcards.append(self.get_mcards())
                self.mcardgrp.empty()
                self.mcardgrp.add(self.sdata.sparea_mcards[areaid])
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

                self.list = self.get_mcards("visible")
                self.index = -1
                self.set_curtain()

        # ターゲット選択エリア
        elif self.selectedheader:
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

            elif cardtarget == "User" or cardtarget == "None":
                if self.status == "Scenario":
                    self.change_selection(owner)
                    self.call_modaldlg("USECARD")
                elif self.is_battlestatus():
                    owner.set_action(owner, header)
                    self.clear_specialarea()

        self.statusbar.change(True)
        self.disposition_pcards()

    def clear_specialarea(self):
        """特殊エリアに移動する前のエリアに戻る。
        areaidが-3(パーティ解散)の場合はエリアチェンジする。
        """
        self.clear_inusecardimg()
        self.clear_guardcardimg()

        if self.areaid <= 0:
            self.selectedheader = None
            oldareaid = self.areaid
            areaid = self.pre_areaids.pop()

            # キャンプ時は常にカーテン表示
            if areaid <> cw.AREA_CAMP:
                self.clear_curtain()

            # カード移動操作エリアを解除の場合
            if oldareaid in cw.AREAS_TRADE:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.mcardgrp.remove_sprites_of_layer(0)
                self.mcardgrp.add(self.pre_mcards.pop())
                self.deal_cards()
                self.list = self.get_mcards("visible")
                self.index = -1
            else:
                if cw.cwpy.ydata:
                    changed = cw.cwpy.ydata.is_changed()
                self.change_area(areaid, quickdeal=True, specialarea=True)
                if cw.cwpy.ydata:
                    cw.cwpy.ydata._changed = changed
        elif self.is_battlestatus():
            self.clear_curtain()
            self.selectedheader = None
            self.call_predlg()
        elif self.selectedheader:
            # ターゲット選択エリアを解除の場合
            self.selectedheader = None
            if self.is_curtained():
                self.clear_curtain()
            if self.pre_dialogs:
                self.call_predlg()

        showbuttons = not self.is_playingscenario() or\
            (not self.areaid in cw.AREAS_TRADE and self.areaid in cw.AREAS_SP)
        self.statusbar.change(showbuttons)
        self.disposition_pcards()

    def clean_specials(self):
        """デバッガからの強制的なエリア移動等を発生させる時、
        特殊エリアにいたりバックログを開いていたりした場合は
        クリアして通常状態へ戻す。
        """
        if self.is_showingbacklog():
            self._is_showingbacklog = False
        if self.is_curtained():
            self.pre_dialogs = []
            self.clear_specialarea()

    def check_level(self, fromscenario):
        """PCの経験点を確認し、条件を満たしていれば
        レベルアップ・ダウン処理を行う。
        fromscenarioがTrueであれば同時に完全回復も行う。
        """
        for pcard in self.get_pcards():
            pcard.adjust_level(fromscenario)

#-------------------------------------------------------------------------------
# 選択操作用メソッド
#-------------------------------------------------------------------------------

    def clear_selection(self):
        """全ての選択状態を解除する。"""
        if self.selection:
            self.has_inputevent = True

            # カードイベント中にtargetarrow, inusecardimgを消さないため
            if not self.is_runningevent():
                self.clear_targetarrow()
                self.clear_inusecardimg()

            self.selection.image = self.selection.get_unselectedimage()

        self.selection = None
        self.index = -1

    def change_selection(self, sprite):
        """引数のスプライトを選択状態にする。
        sprite: SelectableSprite
        """
        self.has_inputevent = True

        if self.selection:
            self.selection.image = self.selection.get_unselectedimage()

            # カードイベント中にtargetarrow, inusecardimgを消さないため
            if not self.is_runningevent():
                self.clear_targetarrow()
                self.clear_inusecardimg()

        sprite.image = sprite.get_selectedimage()
        self.selection = sprite

        if isinstance(sprite, cw.character.Character)\
                            and sprite.actiondata and sprite.is_analyzable():
            if not self.selectedheader:
                targets, header, beasts = self.selection.actiondata
                if header:
                    self.set_inusecardimg(sprite, header)

                    if header.target == "None":
                        self.set_targetarrow([sprite])
                    elif targets:
                        self.set_targetarrow(targets)

    def set_inusecardimg(self, owner, header, status="normal", center=False, spritegrp=None):
        """PlayerCardの前に使用中カードの画像を表示。"""
        if not self.get_inusecardimg():
            inusecard = cw.sprite.background.InuseCardImage(owner, header, status, center, spritegrp)
            owner.inusecardimg = inusecard
            self.inusecards.append(inusecard)

    def clear_inusecardimg(self, user=None):
        """PlayerCardの前の使用中カードの画像を削除。"""
        if user:
            if user.inusecardimg:
                user.inusecardimg.group.remove(user.inusecardimg)
                self.inusecards.remove(user.inusecardimg)
                user.inusecardimg = None
        else:
            for card in self.get_pcards():
                card.inusecardimg = None
            for card in self.get_mcards():
                card.inusecardimg = None

            for card in self.inusecards:
                card.group.remove(card)
            self.inusecards = []

    def set_guardcardimg(self, owner, header):
        """PlayerCardの前に回避・抵抗ボーナスカードの画像を表示。"""
        if not self.get_guardcardimg():
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
        if not self.pcardgrp.get_sprites_from_layer("targetarrow") and\
            not self.mcardgrp.get_sprites_from_layer("targetarrow"):
            if not isinstance(targets, (list, tuple)):
                cw.sprite.background.TargetArrow(targets)
            else:
                for target in targets:
                    cw.sprite.background.TargetArrow(target)

    def clear_targetarrow(self):
        """対象選択の指矢印の画像を削除。"""
        self.mcardgrp.remove_sprites_of_layer("targetarrow")
        self.pcardgrp.remove_sprites_of_layer("targetarrow")

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

    def set_curtain(self, target="Both"):
        """Curtainスプライトをセットする。"""
        if not self.is_curtained():
            size_noscale, pos_noscale = (632, 284), (0, 0)
            size_noscale2, pos_noscale2 = (632, 136), (0, 284)
            size_noscale_castcard = (95, 130)

            self.is_pcardsselectable = target in ("Both", "Party")
            self.is_mcardsselectable = not self.is_battlestatus() or\
                                       target in ("Both", "Enemy")
            self.update_selectablelist()

            if self.areaid < 0 or target == "Both":
                cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale,
                                             pos_noscale=pos_noscale)
                cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale2,
                                             pos_noscale=pos_noscale2)
            elif self.is_playingscenario():
                if target == "Party":
                    if self.battle:
                        cw.sprite.background.Curtain(self.mcardgrp, size_noscale=size_noscale,
                                                     pos_noscale=pos_noscale)
                    else:
                        cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale,
                                                     pos_noscale=pos_noscale)

                    if self.battle:
                        cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale2,
                                                     pos_noscale=pos_noscale2)
                        cards = self.get_ecards()
                        rect_area = pygame.Rect(pos_noscale2, size_noscale2)

                        # noscale2と、enemycardとの重なった領域にcurtain描画
                        # curtain どうしが重なるのを防ぐため、この領域をリストに記録
                        rectcliplist = []

                        for card in cards:
                            size = size_noscale_castcard
                            if not card.scale == 100:
                                scale = card.scale / 100.0
                                dummyimage = pygame.Surface(size_noscale_castcard)
                                dummyimage = pygame.transform.rotozoom(dummyimage, 0, scale)
                                size = dummyimage.get_size()

                            (area2_y, ), (card_y, ), (card_h, ) = \
                                    pos_noscale2[1:], card._pos_noscale[1:], size[1:]
                            # pos_noscale2 の領域に enemycard が重なっているか
                            if area2_y < card_y + card_h:
                                rect_card = pygame.Rect(card._pos_noscale, size)
                                clip = rect_area.clip(rect_card)
                                # curtain が重なって濃くならないよう、透過色で塗るrectのリスト
                                cutarealist = []
                                for rectclip in rectcliplist:
                                    if rectclip.colliderect(clip):
                                        cutarealist.append(rectclip.clip(clip))
                                cw.sprite.background.Curtain(self.mcardgrp,size_noscale=clip.size,
                                                            pos_noscale=clip.topleft,
                                                            cutarealist=cutarealist)
                                rectcliplist.append(clip)

                    else:
                        cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale2,
                                                     pos_noscale=pos_noscale2)
                elif target == "Enemy":
                    cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale,
                                                 pos_noscale=pos_noscale)
                    cw.sprite.background.Curtain(self.bggrp, size_noscale=size_noscale2,
                                                 pos_noscale=pos_noscale2)
                    cards = self.get_pcards()
                    for card in cards:
                        cw.sprite.background.Curtain(self.pcardgrp,
                                                     size_noscale=size_noscale_castcard,
                                                     pos_noscale=card._pos_noscale)

            self._curtained = True

    def clear_curtain(self):
        """Curtainスプライトを解除する。"""
        if self.is_curtained():
            self.bggrp.remove_sprites_of_layer("curtain")
            self.mcardgrp.remove_sprites_of_layer("curtain")
            self.pcardgrp.remove_sprites_of_layer("curtain")
            self._curtained = False
            self.is_pcardsselectable = True
            self.is_mcardsselectable = True

    def cancel_cardcontrol(self):
        """カードの移動や使用の対象選択をキャンセルする。"""
        if self.is_curtained():
            self.sounds["click"].play()

            # カード移動選択エリアだったら、事前に開いていたダイアログを開く
            if self.areaid in cw.AREAS_TRADE:
                self.call_predlg()
            # それ以外だったら特殊エリアをクリアする
            else:
                self.clear_specialarea()

#-------------------------------------------------------------------------------
# プレイ用メソッド
#-------------------------------------------------------------------------------

    def elapse_time(self):
        """時間経過。"""
        ccards = self.get_pcards("unreversed")
        ccards.extend(self.get_ecards("unreversed"))
        ccards.extend(self.get_fcards())

        for ccard in ccards:
            ccard.set_timeelapse()

    def interrupt_adventure(self):
        """冒険の中断。宿画面に遷移する。"""
        if self.status == "Scenario":
            self.sdata.update_log()
            self.music.stop()
            cw.util.remove("Data/Temp/ScenarioLog")
            self.ydata.load_party(None)

            if not self.areaid > 0:
                self.areaid = self.pre_areaids[0]

            self.set_yado()

    def load_party(self, header=None, chgarea=True):
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
        else:
            e = self.ydata.party.members[0]
            pcardsnum = len(self.ydata.party.members) - 1
            pos_noscale = (9 + 95 * pcardsnum + 9 * pcardsnum, 285)
            pcard = cw.sprite.card.PlayerCard(e, pos_noscale=pos_noscale)
            pcard.set_pos_noscale(pos_noscale)
            cw.animation.animate_sprite(pcard, "deal")

    def dissolve_party(self, pcard=None):
        """現在選択中のパーティからpcardを削除する。
        pcardがない場合はパーティ全体を解散する。
        """
        if not self.areaid == cw.AREA_BREAKUP:
            return

        if pcard:
            self.sounds["page"].play()
            pcard.remove_numbercoupon()
            cw.animation.animate_sprite(pcard, "delete")
            pcard.data.write_xml()
            self.pcardgrp.remove(pcard)
            self.ydata.add_standbys(pcard.data.fpath)

            if not self.get_pcards():
                self.dissolve_party()

        else:
            for pcard in self.get_pcards():
                pcard.remove_numbercoupon()
                cw.animation.animate_sprite(pcard, "hide")
                self.pcardgrp.remove(pcard)
                pcard.data.write_xml()

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

            order = cw.util.new_order(self.ydata.standbys)
            for path in p_members:
                header = self.ydata.create_advheader(path)
                header.order = order
                order += 1
                self.ydata.standbys.append(header)
            self.ydata.sort_standbys()

            self.pre_areaids[-1] = 1
            self.clear_specialarea()

    def play_sound(self, path, inusecard=None):
        """効果音を再生する。
        シナリオ効果音・スキン効果音を適宜使い分ける。
        """
        inusesoundpath = cw.util.get_inusecardmaterialpath(path, inusecard)
        if os.path.isfile(inusesoundpath):
            path = inusesoundpath
        elif self.is_playingscenario() and not self.areaid < 0:
            path = cw.util.join_paths(self.sdata.scedir, path)
        else:
            path = cw.util.join_paths(self.skindir, path)

        if os.path.isfile(path):
            cw.util.load_sound(path).play(True)
        else:
            name = cw.util.splitext(os.path.basename(path))[0]

            if name in self.skinsounds:
                self.skinsounds[name].play(True)

    def has_sound(self, path):
        if self.is_playingscenario() and not self.areaid < 0:
            path = cw.util.join_paths(self.sdata.scedir, path)
        else:
            path = cw.util.join_paths(self.skindir, path)

        if os.path.isfile(path):
            return True
        else:
            name = cw.util.splitext(os.path.basename(path))[0]
            return name in self.skinsounds

#-------------------------------------------------------------------------------
# データ編集・操作用メソッド。
#-------------------------------------------------------------------------------

    def trade(self, targettype, target=None, header=None, from_event=False, parentdialog=None, toindex=-1, insertorder=-1, sort=False, sound=True, party=None):
        """
        カードの移動操作を行う。
        Getコンテントからこのメソッドを操作する場合は、
        ownerはNoneにする。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # カード移動操作用データを読み込む
        if self.selectedheader and not header:
            assert self.selectedheader
            header = self.selectedheader

        if not party:
            party = self.ydata.party

        if header.is_backpackheader() and party:
            owner = party.backpack
        else:
            owner = header.get_owner()

        # 荷物袋<=>カード置場のため
        # ファイルの移動だけで済む場合
        move = (targettype in ("BACKPACK", "STOREHOUSE")) and\
            ((owner == self.ydata.storehouse) or (party and owner == party.backpack)) and\
            (not self.is_playingscenario())

        # カード置場・荷物袋内での位置の移動の場合
        toself = (targettype == "BACKPACK" and party and owner == party.backpack) or\
                 (targettype == "STOREHOUSE" and owner == self.ydata.storehouse)

        # 移動先を設定。
        if targettype == "PLAYERCARD":
            target = target
        elif targettype == "BACKPACK":
            target = party.backpack
        elif targettype == "STOREHOUSE":
            target = self.ydata.storehouse
        elif targettype in ("PAWNSHOP", "TRASHBOX"):

            # プレミアカードは売却・破棄処理できない(イベントからの呼出以外)
            if not cw.cwpy.debug and header.premium == "Premium" and not from_event:
                if targettype == "PAWNSHOP":
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_sell_premier_card"]
                    self.call_modaldlg("MESSAGE", text=s, parentdialog=parentdialog)
                elif targettype == "TRASHBOX":
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_dump_premier_card"] % (header.name)
                    self.call_modaldlg("MESSAGE", text=s, parentdialog=parentdialog)

                return

            if targettype == "PAWNSHOP":
                def calc_price(header):
                    # 互換動作: 1.30以前ではカードの売値は常に半額
                    if cw.cwpy.sct.lessthan("1.30", header.versionhint):
                        return header.price / 2

                    if header.premium == "Normal":
                        return header.price / 2
                    else:
                        return int(header.price * 0.75)
                if header.type == "SkillCard":
                    price = calc_price(header)
                elif header.type == "ItemCard":
                    if header.maxuselimit == 0:
                        price = calc_price(header)
                    else:
                        # 使用回数がある場合は使うほど売値が減る
                        price = calc_price(header) * header.uselimit
                        if header.maxuselimit:
                            price /=  header.maxuselimit
                elif header.type == "BeastCard":
                    price = calc_price(header)
                if not from_event:
                    if sound:
                        cw.cwpy.sounds["page"].play()
                    s = cw.cwpy.msgs["confirm_sell"] % (header.name, price)
                    self.call_modaldlg("YESNO", text=s, parentdialog=parentdialog)
                    if self.get_yesnoresult() <> wx.ID_OK:
                        return
            else:
                if not from_event:
                    if sound:
                        cw.cwpy.sounds["page"].play()
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
                    if isinstance(target, cw.character.Player):
                        self.trade("BACKPACK", header=header, from_event=True, sort=sort, party=party)

                else:
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_hand_be_full"] % target.name
                    self.call_modaldlg("MESSAGE", text=s, parentdialog=parentdialog)

                return

        # 音を鳴らす
        if not from_event:
            if targettype == "TRASHBOX":
                self.sounds["dump"].play()
            elif targettype == "PAWNSHOP":
                self.sounds["signal"].play()
            elif sound:
                self.sounds["page"].play()

        #-----------------------------------------------------------------------
        # 移動元からデータを削除
        #-----------------------------------------------------------------------

        hold = header.hold

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
                header.contain_xml()
            else:
                if self.is_playingscenario():
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
                    party.backpack_moved.append(header)
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

        #-----------------------------------------------------------------------
        # ファイル削除
        #-----------------------------------------------------------------------

        # 移動先がゴミ箱・下取りだったら
        if targettype in ("PAWNSHOP", "TRASHBOX"):
            assert not move
            # 付帯以外の召喚獣カードの場合
            if header.type == "BeastCard" and not header.attachment and\
                    isinstance(owner, cw.character.Character):
                owner.update_image()
            # シナリオで取得したカードじゃない場合、XMLの削除
            elif not header.scenariocard and header.moved == 0:
                self.remove_xml(header)

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
            if from_event and header.type == "SkillCard":
                header.uselimit = header.maxuselimit
            # カードのエレメントを追加
            path = "%ss" % header.type
            if toindex == -1:
                target.cardpocket[index].append(header)
                target.data.append(path, header.carddata)
            else:
                target.cardpocket[index].insert(toindex, header)
                target.data.find(path).insert(toindex, header.carddata)

            # 戦闘中の場合、Deckの手札・山札に追加
            if self.battle:
                target.deck.add(target, header)

            # 手札の再構築
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
                self.exec_func(party.set_money, price)

            else:
                self.exec_func(self.ydata.set_money, price)

        if targettype in ("BACKPACK", "STOREHOUSE") and not toself:
            # 移動先が荷物袋かカード置場だったら
            if move:
                header.write(party, move=True)
                header.carddata = None
            else:
                header.fpath = ""
                etree = cw.data.xml2etree(element=header.carddata)
                # 削除フラグを除去
                if etree.getint("Property", "moved", 0) <> 0:
                    etree.remove("Property", attrname="moved")
                    header.moved = 0
                header.write(party)
                header.carddata = None

        # カード選択ダイアログを再び開く(イベントから呼ばれたのでなかったら)
        if not from_event:
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
            for e in data.getiterator():
                if e.tag == "ImagePath" and e.text:
                    path = cw.util.join_paths(self.yadodir, e.text)
                    temppath = cw.util.join_paths(self.tempdir, e.text)

                    if os.path.isfile(path):
                        self.ydata.deletedpaths.add(path)

                    if os.path.isfile(temppath):
                        self.ydata.deletedpaths.add(temppath)

    def copy_materials(self, data, dstdir, from_scenario=True, scedir=""):
        """
        from_scenario: Trueの場合は開いているシナリオから、
                       Falseの場合は開いている宿からコピーする
        XMLElementに記されている
        素材ファイルをdstdirにコピーする。
        """
        if isinstance(data, cw.data.CWPyElementTree):
            data = data.getroot()

        # 同じimgpathを重複して処理しないための辞書
        imgpaths = {}
        r_specialfont = re.compile("#.") # 特殊文字(#)
        if data.tag == "Property":
            prop = data
        else:
            prop = data.find("Property")

        e = cw.data.make_element("Materials", dstdir.replace(self.yadodir + "/", "", 1))
        prop.append(e)
        for e in data.getiterator():
            if e.tag in ("ImagePath", "SoundPath", "SoundPath2") and e.text:
                def set_material(text):
                    e.text = text
                self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, e.text, set_material)
            elif e.tag in ("Play", "Talk"):
                path = e.getattr(".", "path", "")
                if path:
                    def set_material(text):
                        e.attrib["path"] = text
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, path, set_material)
            elif e.tag == "Text" and e.text:
                for spchar in r_specialfont.findall(e.text):
                    c = "font_" + spchar[1:]
                    def set_material(text):
                        pass
                    for ext in cw.EXTS_IMG:
                        self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, c + ext, set_material)

            elif e.tag == "Effect":
                path = e.getattr(".", "sound", "")
                if path:
                    def set_material(text):
                        e.attrib["sound"] = text
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, e, path, set_material)

    def _copy_material(self, data, dstdir, from_scenario, scedir, imgpaths, e, materialpath, set_material):
        pisc = not e is None and e.tag == "ImagePath" and cw.binary.image.path_is_code(materialpath)
        if pisc:
            imgpath = materialpath
        else:
            if from_scenario:
                if not scedir:
                    scedir = self.sdata.scedir
                imgpath = cw.util.join_paths(scedir, materialpath)
            else:
                imgpath = cw.util.join_yadodir(materialpath)

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
                    innerfpath = cw.effectbooster.get_filepath_s(imgpath, jpy1innnerfile, dirtype)
                    if not innerfpath.startswith(scedir + "/"):
                        continue
                    innerfpath = innerfpath.replace(scedir + "/", "", 1)
                    def func(text):
                        pass
                    self._copy_material(data, dstdir, from_scenario, scedir, imgpaths, None, innerfpath, func)

            except Exception:
                cw.util.print_ex()

        # 重複チェック。既に処理しているimgpathかどうか
        if not pisc and imgpath in imgpaths:
            # ElementTree編集
            set_material(imgpaths[imgpath])
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
            imgdst = cw.util.dupcheck_plus(imgdst)

            if imgdst.startswith("Yado"):
                imgdst = imgdst.replace(self.yadodir, self.tempdir, 1)

            # 対象画像コピー
            if not os.path.isdir(os.path.dirname(imgdst)):

                os.makedirs(os.path.dirname(imgdst))

            if pisc:
                imgdst = cw.util.dupcheck_plus(imgdst, False)
                with open(imgdst, "wb") as f:
                    f.write(idata)
            else:
                shutil.copy2(imgpath, imgdst)
            # ElementTree編集
            materialpath = imgdst.replace(self.tempdir + "/", "", 1)
            set_material(materialpath)
            if not pisc:
                # 重複して処理しないよう辞書に登録
                imgpaths[imgpath] = materialpath

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

    def is_playingscenario(self):
        return bool(isinstance(self.sdata, cw.data.ScenarioData)\
                                                    and self.sdata.is_playing)

    def is_runningevent(self):
        return self.event.get_event() or\
            self.event.in_cardevent or\
            pygame.event.peek(USEREVENT) or\
            (self.is_battlestatus() and not (self.battle and self.battle.is_ready()))

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
        if self.is_playingscenario():
            self._gameover = True
            pcards = self.get_pcards("unreversed")
            for pcard in pcards:
                if pcard.is_alive():
                    self._gameover = False
                    break
            self._gameover |= not bool(pcards)

        return self._gameover

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
        """InuseCardImageインスタンスを返す(仕様カード)。"""
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
        try:
            return self.topgrp.get_sprites_from_layer("message")[0]
        except:
            return None

    def get_mcards(self, mode=""):
        """MenuCardインスタンスのリストを返す。
        mode: "visible" or "invisible" or "visiblemenucards" or "flagtrue"
        """
        if mode == "visible":
            mcards = [m for m in self.get_mcards() if not m.status == "hidden"]
        elif mode == "invisible":
            mcards = [m for m in self.get_mcards() if m.status == "hidden"]
        elif mode == "visiblemenucards":
            mcards = [m for m in self.get_mcards() if not m.status == "hidden"
                                and isinstance(m, cw.sprite.card.MenuCard)]
        elif mode == "flagtrue":
            mcards = [m for m in self.get_mcards()
                            if not isinstance(m, cw.character.Friend)
                                    and (not m.debug_only or self.is_debugmode())
                                    and self.sdata.flags.get(m.flag, True)]
        else:
            mcards = self.mcardgrp.get_sprites_from_layer(0)
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
            pcards = self.pcardgrp.get_sprites_from_layer(0)
            pcards = [m for m in pcards
                      if not isinstance(m, cw.sprite.background.InuseCardImage)]

        return pcards

    def get_fcards(self, mode=""):
        """FriendCardインスタンスのリストを返す。
        シナリオプレイ中以外は空のリストを返す。
        mode: なし。
        """
        if self.is_playingscenario():
            return self.sdata.friendcards
        else:
            return []

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
