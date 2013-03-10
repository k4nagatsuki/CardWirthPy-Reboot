#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import threading
import shutil
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
            self.frame = frame   # 親フレーム
            self._running = False
            self.init_pygame(setting)

    def init_pygame(self, setting):
        """使用変数等はここ参照。"""
        self.setting = setting  # 設定

        # pygame初期化
        self.scr, self.clock = cw.util.init(cw.SIZE_SCR)
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
        # メインループ中に各種入力イベントがあったかどうかフラグ
        self.has_inputevent = False
        # アニメーションカットフラグ
        self.cut_animation = False
        # 入力があるまでメニューカード表示を待つ
        self.wait_showcards = False
        # ダイアログ表示中フラグ
        self._showingdlg = False
        # フルスクリーンフラグ
        self._fullscreen = False
        # カーテンスプライト表示中フラグ
        self._curtained = False
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
            self.rsrc = cw.setting.Resource(self.setting)
            # システム効果音(辞書)
            self.sounds = self.rsrc.sounds
            # その他のスキン付属効果音(辞書)
            self.skinsounds = self.rsrc.skinsounds
            # システムメッセージ(辞書)
            self.msgs = self.rsrc.msgs
            # アクションカードのデータ(CardHeader)
            self.rsrc.actioncards = self.rsrc.get_actioncards()
            # 背景スプライト
            self.background = cw.sprite.background.BackGround()
            self.bggrp.set_clip(self.background.rect)
            self.mcardgrp.set_clip(self.background.rect)
            self.pcardgrp.set_clip(self.background.rect)
            self.topgrp.set_clip(self.background.rect)
            self.backloggrp.set_clip(self.background.rect)
            # ステータスバースプライト
            self.statusbar = cw.sprite.statusbar.StatusBar()
            # ステータスバークリップ
            self.sbargrp.set_clip(self.statusbar.rect)
            # FPS描画用フォント
            self.fpsfont = pygame.font.Font(self.rsrc.fontpaths["gothic"], 14)
            self.fpsfont.set_bold(True)

        except cw.setting.NoFontError, ex:
            def func():
                s = (u"CardWirthPyの実行に必要なフォントがありません。\n"
                     u"Data/Font以下にIPAフォントをインストールしてください。")
                wx.MessageBox(s, u"メッセージ", wx.OK|wx.ICON_ERROR, cw.cwpy.frame)
                cw.cwpy.frame.Destroy()
            cw.cwpy.frame.exec_func(func)

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
            self.tick_clock()         # FPS調整
            self.input()              # 各種入力イベント取得
            self.eventhandler.run()   # イベントハンドラ
            self.update()             # スプライトの更新
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
        for i in xrange(count):
            self.tick_clock()

    def input(self, eventclear=False):
        self.mousein = pygame.mouse.get_pressed()
        if pygame.mouse.get_focused():
            mousepos = pygame.mouse.get_pos()
        else:
            mousepos = (-1, -1)
        self.mousemotion = False if self.mousepos == mousepos else True
        self.mousepos = mousepos
        self.keyin = self.keyevent.get_pressed()

        if eventclear:
            pygame.event.clear((MOUSEBUTTONUP, KEYDOWN))
        else:
            self.events = pygame.event.get()

    def update(self):
        self.bggrp.update(self.scr)
        self.mcardgrp.update(self.scr)
        self.pcardgrp.update(self.scr)
        self.sbargrp.update(self.scr)
        if not self.statusbar.showbuttons:
            if not self.is_runningevent() and not self.areaid in cw.AREAS_TRADE:
                self.statusbar.change()

    def draw(self, mainloop=False):
        if self.has_inputevent or not mainloop:
            # SpriteGroup描画
            dirty_rects = self.bggrp.draw(self.scr)
            dirty_rects.extend(self.mcardgrp.draw(self.scr))
            dirty_rects.extend(self.pcardgrp.draw(self.scr))
            dirty_rects.extend(self.topgrp.draw(self.scr))
            dirty_rects.extend(self.backloggrp.draw(self.scr))
            dirty_rects.extend(self.sbargrp.draw(self.scr))

            # FPS描画
            if self.setting.showfps:
                sur = self.fpsfont.render(str(int(self.clock.get_fps())), False, (0, 255, 255))
                pos = (600, 5)
                dirty_rects.append(self.scr.blit(sur, pos))

            # 画面更新
            pygame.display.update(dirty_rects)

    def call_dlg(self, name, **kwargs):
        """ダイアログを開く。
        name: ダイアログ名。cw.frame参照。
        """
        self.lock_menucards = True
        self._showingdlg = True
        self.keyevent.clear() # キー入力初期化
        event = wx.PyCommandEvent(self.frame.dlgeventtypes[name])
        event.args = kwargs
        if threading.currentThread() == self:
            self.frame.AddPendingEvent(event)
            while self.is_running() and self.frame.IsEnabled():
                pass
        else:
            self.frame.ProcessEvent(event)
        self.lock_menucards = False

    def call_modaldlg(self, name, **kwargs):
        """ダイアログを開き、閉じるまで待機する。
        name: ダイアログ名。cw.frame参照。
        """
        self.call_dlg(name, **kwargs)

        if threading.currentThread() == self:
            while self.is_running() and self.is_showingdlg():
                pass

    def call_predlg(self):
        """直前に開いていたダイアログを再び開く。"""
        if self.pre_dialogs:
            callname = self.pre_dialogs[-1][0]
            self.call_dlg(callname)

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
            self.exec_func(func2, result, func, args, kwargs)
            while isrun and self.frame.IsEnabled() and self.is_running():
                time.sleep(0.001)
            return result[0]

    def set_fullscreen(self, flag):
        """フルスクリーン化したり解除したり。
        flag: Trueならフルスクリーン、Falseなら解除。
        """
        if self.is_fullscreen() == flag:
            return

        if flag:
            self.scr = pygame.display.set_mode(cw.SIZE_SCR, FULLSCREEN)
            func = self.frame.ShowFullScreen
            self.frame.exec_func(func, True, wx.FULLSCREEN_ALL)
        else:
            self.scr = pygame.display.set_mode(cw.SIZE_SCR, 0)
            func = self.frame.ShowFullScreen
            self.frame.exec_func(func, False, self.frame.style)

        while not self.frame.IsFullScreen() == flag:
            pass

        self._fullscreen = flag
        self.has_inputevent = True

    def show_message(self, mwin):
        """MessageWindowを表示し、次コンテントのindexを返す。
        mwin: MessageWindowインスタンス。
        """
        eventhandler = cw.eventhandler.EventHandlerForMessageWindow(mwin)
        self.clear_selection()

        while self.is_running() and mwin.result is None:
            self.update()

            if mwin.result is None:
                self.draw(not mwin.is_drawing or self.has_inputevent)

            self.tick_clock()
            self.input()
            eventhandler.run()
        self.clear_selection()

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
        self.pcardgrp.remove_sprites_of_layer("selectionbar")
        self.pcardgrp.remove_sprites_of_layer("message")

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

        self.topgrp.add(cw.sprite.message.BacklogCurtain(self.topgrp))
        eventhandler = cw.eventhandler.EventHandlerForBacklog(self.sdata.backlog, index)
        self.clear_selection()
        self.statusbar.change(False)

        while self.is_running() and eventhandler.mwin:
            self.topgrp.update(self.scr)
            self.sbargrp.update(self.scr)
            self.draw()
            self.tick_clock()
            self.input()
            eventhandler.run()

        # 背景スプライト削除
        self.topgrp.remove_sprites_of_layer("curtain")
        self.draw()

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
        self.pre_battleareadata = None
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

        cw.cwpy.bggrp.add(card1, layer="title")
        cw.cwpy.bggrp.add(card2, layer="title")
        cw.cwpy.bggrp.add(cell1, layer="title")
        cw.cwpy.bggrp.add(cell2, layer="title")
        cw.cwpy.bggrp.add(cell3, layer="title")
        cw.cwpy.bggrp.add(white, layer="title")

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
        self.bggrp.remove_sprites_of_layer("title")

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
        self.statusbar.change()

        if self.ydata.party:
            areaid = 2
        else:
            areaid = 1

        self.change_area(areaid)

    def set_scenario(self, header=None, lastscenario=[]):
        """シナリオ画面へ遷移。
        header: ScenarioHeader
        """
        self.set_status("Scenario")
        self.battle = None
        self.statusbar.change(False)

        if header and not isinstance(self.sdata, cw.data.ScenarioData):
            self.sdata = cw.data.ScenarioData(header)
            loaded, musicpath = self.sdata.set_log()
            self.sdata.start()
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += "%s %s" % (self.ydata.name, self.sdata.name)
            self.set_titlebar(s)
            areaid = self.sdata.startid
            if lastscenario:
                self.ydata.party.set_lastscenario(lastscenario)

            if musicpath is None or\
                            self.music.path == self.music.get_path(musicpath):
                self.change_area(areaid, not loaded, loaded)
            else:
                self.music.stop()
                self.change_area(areaid, not loaded, loaded)
                self.music.play(musicpath)

    def set_battle(self):
        """シナリオ戦闘画面へ遷移。"""
        self.set_status("ScenarioBattle")
        self.statusbar.change()

    def set_gameover(self):
        """ゲームオーバー画面へ遷移。"""
        self.set_status("GameOver")
        self._gameover = False
        self.battle = None
        pygame.event.clear()
        self.sdata.end()
        self.ydata.party.lost()
        self.ydata.load_party(None)
        self.sdata = cw.data.SystemData()
        s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
        s += os.path.basename(self.yadodir)
        self.set_titlebar(s)
        self.statusbar.change()
        self.change_area(1)

    def f9(self):
        """cw.data.ScenarioDataのf9()から呼び出され、
        緊急非難処理の続きを行う。
        """
        # スプライトを作り直す
        for idx, pcard in enumerate(self.get_pcards()):
            self.sounds["harvest"].play()
            cw.animation.animate_sprite(pcard, "hide")
            self.pcardgrp.remove(pcard)

            data = self.ydata.party.members[idx]
            pos = (95 * idx + 9 * (idx + 1), 285)
            pcard = cw.sprite.card.PlayerCard(data, pos)
            pcard.rect.topleft = pos
            pcard._rect.topleft = pos
            pcard.set_fullrecovery()

            cw.animation.animate_sprite(pcard, "deal")

        # 番号クーポン設定
        self.ydata.party.set_numbercoupon()
        self.ydata.party._loading = False

        self.set_yado()

    def reload_yado(self):
        """現在の宿をロード。"""
        self._init_resources()
        self.set_status("Title")
        cw.util.remove_temp()
        self.load_yado(self.yadodir)

    def load_yado(self, yadodir):
        """指定されたディレクトリの宿をロード。"""
        self.yadodir = yadodir.replace("\\", "/")
        self.tempdir = self.yadodir.replace("Yado",
                                                    "Data/Temp/Yado", 1)
        self.music.stop()
        self.ydata = cw.data.YadoData()
        self.setting.lastyado = self.ydata.name

        if self.ydata.party:
            header = self.ydata.party.get_sceheader()

            # シナリオプレイ途中から再開
            if header:
                self.exec_func(self.set_scenario, header)
            # シナリオロードに失敗
            elif self.ydata.party.is_adventuring():
                self.exec_func(self.ydata.load_party, None)
                self.exec_func(self.set_yado)
            else:
                self.exec_func(self.set_yado)

            if self.is_showingdebugger():
                func = self.frame.debugger.refresh_tools
                self.exec_func(func)

        else:
            self.exec_func(self.set_yado)

#-------------------------------------------------------------------------------
# エリアチェンジ関係メソッド
#-------------------------------------------------------------------------------

    def deal_cards(self):
        """hidden状態のMenuCard(対応フラグがFalseだったら表示しない)と
        PlayerCardを全て表示する。
        """
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
            self.set_autospread(mcards, flag)

        for mcard in mcardsinv:
            if self.sdata.flags.get(mcard.flag, True):
                cw.animation.animate_sprite(mcard, "deal")

        # list, indexセット
        if not self.is_showingmessage():
            self.list = self.get_mcards("visible")
            self.index = -1

        self.input(True)
        self._dealing = False
        self.wait_showcards = False

    def hide_cards(self, hideall=False):
        """
        カードを非表示にする(表示中だったカードはhidden状態になる)。
        各カードのhidecards()の最後に呼ばれる。
        hideallがTrueだった場合、全てのカードを非表示にする。
        """
        self._dealing = True
        # 選択を解除する
        self.clear_selection()

        # メニューカードを下げる
        for mcard in self.get_mcards("visible"):
            if hideall or not self.sdata.flags.get(mcard.flag, True):
                if mcard.inusecardimg:
                    self.clear_inusecardimg(mcard)
                cw.animation.animate_sprite(mcard, "hide")

        # プレイヤカードを下げる
        if self.ydata:
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

    def hide_party(self):
        """PlayerCardを非表示にする。"""
        pcards = [i for i in self.get_pcards() if not i.status == "hidden"]

        if pcards:
            self.clear_inusecardimg()
            cw.animation.animate_sprites(pcards, "shiftdown")

        self.is_showparty = False
        self.input(True)

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
            self.background.load(self.sdata.get_bgdata(), bginhrt, ttype)

        # 特殊エリア(メンバー解散)だったら背景にカーテンを追加。
        if self.areaid == cw.AREA_BREAKUP:
            self.set_curtain()

        # メニューカードスプライト作成
        self.set_mcards(self.sdata.get_mcarddata(), dealanime)

        # プレイヤカードスプライト作成
        if self.ydata and self.ydata.party and not self.get_pcards():
            for idx, e in enumerate(self.ydata.party.members):
                pos = (95 * idx + 9 * (idx + 1), 285)
                cw.sprite.card.PlayerCard(e, pos)

            # 番号クーポン設定
            self.ydata.party.set_numbercoupon()
            self.ydata.party._loading = False

        # キャンプ画面のときはFriendCardもスプライトグループに追加
        if self.areaid == cw.AREA_CAMP:
            for index, fcard in enumerate(self.get_fcards()):
                index = 5 - index
                pos = (95 * index + 9 * (index + 1), 5)
                fcard.set_pos(pos)
                fcard.clear_image()
                fcard.status = "hidden"
                self.mcardgrp.add(fcard)

    def set_autospread(self, mcards, campwithfriend=False):
        """自動整列設定時のメニューカードの配置位置を設定する。
        mcards: MenuCard or EnemyCardのリスト。
        campwithfriend: キャンプ画面時＆FriendCardが存在しているかどうか。
        """
        def set_mcardpos(mcards, (maxw, maxh), y):
            n = maxw + 5
            x = (632 - n * len(mcards) - 5) / 2

            for mcard in mcards:
                w, h = mcard._rect.size
                mcard.set_pos((x + maxw - w, y + maxh - h))
                x += n

        maxw = 0
        maxh = 0

        for mcard in mcards:
            w, h = mcard._rect.size

            if w > maxw:
                maxw = w

            if h > maxh:
                maxh = h

        n = len(mcards)

        if campwithfriend:
            y = (145 - maxh) / 2 + 140 - 2
            set_mcardpos(mcards, (maxw, maxh), y)
        elif n < 8:
            y = (285 - maxh) / 2 - 2
            set_mcardpos(mcards, (maxw, maxh), y)
        else:
            y = (285 - maxh * 2) / 2
            y2 = y + maxh + 5
            set_mcardpos(mcards[:n / 2 + n % 2], (maxw, maxh), y)
            set_mcardpos(mcards[n / 2:], (maxw, maxh), y2)

    def set_mcards(self, (stype, elements), dealanime=True):
        """メニューカードスプライトを構成する。
        (stype, elements): (spreadtype, MenuCardElementのリスト)のタプル
        dealanime: True時はカードを最初から表示している。
        """
        # カードの並びがAutoの時
        if stype == "Auto":
            self._autospread = True
        else:
            self._autospread = False

        status = "hidden" if dealanime else "normal"

        for index, e in enumerate(elements):
            if stype == "Auto":
                pos = (0, 0)
            else:
                left = e.getint("Property/Location", "left")
                top = e.getint("Property/Location", "top")
                pos = (left, top)

            if e.tag == "EnemyCard":
                cw.sprite.card.EnemyCard(e, pos, status)
            else:
                cw.sprite.card.MenuCard(e, pos, status)

    def change_area(self, areaid, eventstarting=True,
                          bginhrt=False, ttype=("Default", "Default")):
        """ゲームエリアチェンジ。
        eventstarting: Falseならエリアイベントは起動しない。
        bginhrt: 背景継承を行うかどうかのbool値。
        ttype: トランジション効果のデータのタプル((効果名, 速度))
        """
        # 背景継承を行うかどうかのbool値
        bginhrt |= bool(self.areaid < 0 and self.sdata.check_bginhrt())
        oldareaid = self.areaid
        self.areaid = areaid
        self.sdata.change_data(areaid)
        bginhrt |= bool(self.areaid < 0 and self.sdata.check_bginhrt())
        cw.cwpy.hide_cards(True)
        self.set_sprites(bginhrt=bginhrt, ttype=ttype)

        if not self.is_playingscenario() and not self.is_showparty:
            # 宿にいる場合は常に全回復状態にする
            for pcard in self.get_pcards():
                pcard.set_fullrecovery()
                pcard.update_image()

        if self.is_showparty:
            for index, pcard in enumerate(self.get_pcards()):
                # 解散直後などは位置が揃っていないので再設定
                pos = (9 + 95 * index + 9 * index, 285)
                pcard.rect.topleft = pos
                pcard._rect.topleft = pos

        # エリアイベントを開始(特殊エリアからの帰還だったら開始しない)
        if eventstarting and oldareaid > 0:
            if not self.wait_showcards:
                self.deal_cards()
            else:
                self.draw()

            if self.areaid > 0 and self.status == "Scenario":
                self.elapse_time()

            self.sdata.start_event(keynum=1)
        else:
            self.deal_cards()
            self.show_party()

    def change_battlearea(self, areaid):
        """
        指定するIDの戦闘を開始する。
        """
        self.lock_menucards = True
        self.sounds["battle"].play()
        # 戦闘開始アニメーション
        sprite = cw.sprite.background.BattleCardImage()
        cw.animation.animate_sprite(sprite, "battlestart")
        sprite.remove(cw.cwpy.pcardgrp)
        self.set_battle()
        oldareaid = self.areaid
        oldbgmpath = self.music.path
        self.change_area(areaid, False, ttype=("None", "Default"))
        # 戦闘音楽を流す
        path = self.sdata.data.gettext("Property/MusicPath", "")
        self.music.play(path)

        if self.pre_battleareadata:
            oldareaid = self.pre_battleareadata[0]
            oldbgmpath = self.pre_battleareadata[1]

        self.pre_battleareadata = (oldareaid, oldbgmpath, self.music.path)
        self.battle = cw.battle.BattleEngine()
        self.lock_menucards = False

    def clear_battlearea(self, areachange=True, win=False):
        """戦闘状態を解除して戦闘前のエリアに戻る。
        areachangeがFalseだったら、戦闘前のエリアには戻らない
        (戦闘イベントで、エリア移動コンテント等が発動した時用)。
        """
        if self.status == "ScenarioBattle":
            # 勝利イベントを保持しておく
            battleevents = self.sdata.events

            for pcard in self.get_pcards():
                pcard.deck.clear(pcard)

                if not pcard.is_reversed():
                    pcard.remove_timedcoupons(True)

            for fcard in self.get_fcards():
                fcard.deck.clear(fcard)

                if not fcard.is_reversed():
                    fcard.remove_timedcoupons(True)

            areaid, bgmpath, battlebgmpath = self.pre_battleareadata
            self.pre_battleareadata = None
            self.set_scenario()

            # BGMを最後に指定されたものに戻す
            self.music.play(bgmpath)

            if areachange:
                # 戦闘前のエリアに戻る
                self.change_area(areaid, False, ttype=("None", "Default"), bginhrt=True)

            if win:
                # 勝利イベント開始
                battleevents.start(keynum=1)

    def change_specialarea(self, areaid):
        """特殊エリア(エリアIDが負の数)に移動する。"""
        if areaid < 0:
            self.pre_areaids.append(self.areaid)

            # パーティ解散・キャンプエリア移動の場合はエリアチェンジ
            if areaid in (cw.AREA_BREAKUP, cw.AREA_CAMP):
                self.change_area(areaid)
            else:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.pre_mcards.append(self.mcardgrp.remove_sprites_of_layer(0))
                self.mcardgrp.add(self.sdata.sparea_mcards[areaid])
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
                    self.call_dlg("USECARD")
                elif self.is_battlestatus():
                    owner.set_action(owner, header)
                    self.clear_specialarea()

        showbuttons = not self.is_playingscenario() or\
            (not self.areaid in cw.AREAS_TRADE and self.areaid in cw.AREAS_SP)
        self.statusbar.change(showbuttons)

    def clear_specialarea(self):
        """特殊エリアに移動する前のエリアに戻る。
        areaidが-3(パーティ解散)の場合はエリアチェンジする。
        """
        if self.areaid <= 0:
            self.clear_curtain()
            self.selectedheader = None
            oldareaid = self.areaid
            areaid = self.pre_areaids.pop()

            # カード移動操作エリアを解除の場合
            if oldareaid in cw.AREAS_TRADE:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.mcardgrp.remove_sprites_of_layer(0)
                self.mcardgrp.add(self.pre_mcards.pop())
                self.list = self.get_mcards("visible")
                self.index = -1
            else:
                self.change_area(areaid)
        elif self.is_battlestatus():
            self.clear_curtain()
            self.selectedheader = None
            self.call_predlg()
        elif self.selectedheader and self.pre_dialogs:
            # ターゲット選択エリアを解除の場合
            self.clear_curtain()
            self.selectedheader = None
            self.call_predlg()
        elif self.selectedheader:
            self.selectedheader = None

        showbuttons = not self.is_playingscenario() or\
            (not self.areaid in cw.AREAS_TRADE and self.areaid in cw.AREAS_SP)
        self.statusbar.change(showbuttons)

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

    def set_inusecardimg(self, owner, header, status="normal", center=False):
        """PlayerCardの前に使用中カードの画像を表示。"""
        if not self.get_inusecardimg():
            inusecard = cw.sprite.background.InuseCardImage(owner, header, status, center)
            owner.inusecardimg = inusecard

    def clear_inusecardimg(self, user=None):
        """PlayerCardの前の使用中カードの画像を削除。"""
        if user:
            if user.inusecardimg:
                self.pcardgrp.remove(user.inusecardimg)
        else:
            self.pcardgrp.remove_sprites_of_layer("inusecard")

    def set_guardcardimg(self, owner, header):
        """PlayerCardの前に回避・抵抗ボーナスカードの画像を表示。"""
        if not self.get_guardcardimg():
            cw.sprite.background.InuseCardImage(owner, header, status="normal", center=False, layer="guardcard")

    def clear_guardcardimg(self):
        """PlayerCardの前の回避・抵抗ボーナスカードの画像を削除。"""
        self.pcardgrp.remove_sprites_of_layer("guardcard")

    def set_targetarrow(self, targets):
        """targets(PlayerCard, MenuCard, CastCard)の前に
        対象選択の指矢印の画像を表示。
        """
        if not self.pcardgrp.get_sprites_from_layer("targetarrow"):
            if not isinstance(targets, (list, tuple)):
                cw.sprite.background.TargetArrow(targets)
            else:
                for target in targets:
                    cw.sprite.background.TargetArrow(target)

    def clear_targetarrow(self):
        """対象選択の指矢印の画像を削除。"""
        self.pcardgrp.remove_sprites_of_layer("targetarrow")

    def set_curtain(self, target="Both"):
        """Curtainスプライトをセットする。"""
        if not self.is_curtained():
            size, pos = (632, 284), (0, 0)
            size2, pos2 = (632, 136), (0, 284)
            curtain = cw.sprite.background.Curtain

            if self.areaid < 0 or target == "Both":
                curtain(self.bggrp, size=size, pos=pos)
                curtain(self.bggrp, size=size2, pos=pos2)
            elif self.is_playingscenario():
                if target == "Party":
                    if self.battle:
                        curtain(self.pcardgrp, size=size, pos=pos)
                    else:
                        curtain(self.bggrp, size=size, pos=pos)

                    curtain(self.bggrp, size=size2, pos=pos2)
                elif target == "Enemy":
                    curtain(self.bggrp, size=size, pos=pos)
                    curtain(self.pcardgrp, size=size2, pos=pos2)

            self._curtained = True

    def clear_curtain(self):
        """Curtainスプライトを解除する。"""
        if self.is_curtained():
            self.bggrp.remove_sprites_of_layer("curtain")
            self.mcardgrp.remove_sprites_of_layer("curtain")
            self.pcardgrp.remove_sprites_of_layer("curtain")
            self._curtained = False

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
            pos = (9 + 95 * pcardsnum + 9 * pcardsnum, 285)
            pcard = cw.sprite.card.PlayerCard(e, pos)
            pcard.rect.topleft = pos
            pcard._rect.topleft = pos
            cw.animation.animate_sprite(pcard, "deal")

    def dissolve_party(self, pcard=None):
        """現在選択中のパーティからpcardを削除する。
        pcardがない場合はパーティ全体を解散する。
        """
        if not self.areaid == cw.AREA_BREAKUP:
            return

        if pcard:
            self.sounds["page"].play()
            cw.animation.animate_sprite(pcard, "delete")
            pcard.data.write_xml()
            self.ydata.add_standbys(pcard.data.fpath)

            if not self.get_pcards():
                self.dissolve_party()

        else:
            for pcard in self.get_pcards():
                pcard.remove_numbercoupon()
                cw.animation.animate_sprite(pcard, "hide")

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

    def play_sound(self, path):
        """効果音を再生する。
        シナリオ効果音・スキン効果音を適宜使い分ける。
        """
        if self.is_playingscenario() and not self.areaid < 0:
            path = cw.util.join_paths(self.sdata.scedir, path)
        else:
            path = cw.util.join_paths(self.skindir, path)

        if os.path.isfile(path):
            cw.util.load_sound(path).play(True)
        else:
            name = os.path.splitext(os.path.basename(path))[0]

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
            name = os.path.splitext(os.path.basename(path))[0]
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

        # 移動先を設定。
        if targettype == "PLAYERCARD":
            target = target
        elif targettype == "BACKPACK":
            target = party.backpack
        elif targettype == "STOREHOUSE":
            target = self.ydata.storehouse
        elif targettype in ("PAWNSHOP", "TRASHBOX"):
            if targettype == "PAWNSHOP":
                if header.type == "SkillCard":
                    price = header.price / 2
                elif header.type == "ItemCard":
                    if header.maxuselimit == 0:
                        price = header.price / 2
                    else:
                        # 使用回数がある場合は使うほど売値が減る
                        price = header.price / 2 * header.uselimit
                        if header.maxuselimit:
                            price /=  header.maxuselimit
                elif header.type == "BeastCard":
                    price = header.price / 2
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

            # プレミアカードは売却・破棄処理できない(イベントからの呼出以外)
            if header.premium == "Premium" and not from_event:
                if targettype == "PAWNSHOP":
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_sell_premier_card"]
                    self.call_dlg("MESSAGE", text=s, parentdialog=parentdialog)
                elif targettype == "TRASHBOX":
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_dump_premier_card"] % (header.name)
                    self.call_dlg("MESSAGE", text=s, parentdialog=parentdialog)

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
                        self.trade("BACKPACK", header=header, from_event=True, sort=sort)

                else:
                    self.sounds["error"].play()
                    s = cw.cwpy.msgs["error_hand_be_full"] % target.name
                    self.call_dlg("MESSAGE", text=s, parentdialog=parentdialog)

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

        # 移動元がCharacterだった場合
        if isinstance(owner, cw.character.Character):
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

            if header.scenariocard:
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
                else:
                    # 宿にいる場合はそのまま削除する
                    header.contain_xml()

        # 移動元がカード置場だった場合
        elif owner == self.ydata.storehouse:
            # 移動元のリストからCardHeaderを削除
            owner.remove(header)
            header.contain_xml()

        # 移動元が存在しない場合(get or loseコンテンツから呼んだ場合)
        else:
            header.contain_xml()

        #-----------------------------------------------------------------------
        # ファイル削除
        #-----------------------------------------------------------------------

        # 移動先がゴミ箱・下取りだったら
        if targettype in ("PAWNSHOP", "TRASHBOX"):
            # 付帯以外の召喚獣カードの場合
            if header.type == "BeastCard" and not header.attachment:
                owner.update_image()
            # シナリオで取得したカードじゃない場合、XMLの削除
            elif not header.scenariocard and header.moved == 0:
                self.remove_xml(header)

        #-----------------------------------------------------------------------
        # 移動先にデータを追加する
        #-----------------------------------------------------------------------

        # 移動先がPlayerCardだった場合
        if targettype == "PLAYERCARD":
            # cardpocketにCardHeaderを追加
            header.set_owner(target)
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
            # パーティの所持金または金庫に下取金を追加
            if party:
                party.set_money(price)
            else:
                self.ydata.set_money(price)

        if targettype in ("BACKPACK", "STOREHOUSE"):
            # 移動先が荷物袋かカード置場だったら
            header.fpath = ""
            etree = cw.data.xml2etree(element=header.carddata)
            if etree.getint("Property", "moved", 0) <> 0:
                etree.remove("Property", attrname="moved")
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
            self.remove_materials(target.data)
        elif isinstance(target, cw.header.AdventurerHeader):
            self.ydata.deletedpaths.add(target.fpath)
            data = cw.data.yadoxml2etree(target.fpath)
            self.remove_materials(data)
        elif isinstance(target, cw.header.CardHeader):
            if target.fpath:
                self.ydata.deletedpaths.add(target.fpath)

            if target.carddata is not None:
                data = target.carddata
            else:
                data = cw.data.yadoxml2etree(target.fpath).getroot()

            self.remove_materials(data)
        elif isinstance(target, cw.data.Party):
            self.ydata.deletedpaths.add(target.data.fpath)
            self.remove_materials(target.data)
        elif isinstance(target, (str, unicode)):
            if target.endswith(".xml"):
                self.ydata.deletedpaths.add(target)
                data = cw.data.yadoxml2etree(target)
                self.remove_materials(data)

    def remove_materials(self, data):
        """XMLElementに記されている
        素材ファイルを削除予定リストに追加する。
        """
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
        # 同じimgpathを重複して処理しないための辞書
        imgpaths = {}

        for e in data.getiterator():
            if e.tag == "ImagePath" and e.text:
                pisc = cw.binary.image.path_is_code(e.text)
                if pisc:
                    imgpath = e.text
                else:
                    if from_scenario:
                        if not scedir:
                            scedir = self.sdata.scedir
                        imgpath = cw.util.join_paths(scedir, e.text)
                    else:
                        imgpath = cw.util.join_yadodir(e.text)

                if not (pisc or os.path.isfile(imgpath)):
                    e.text = ""
                    continue

                # 重複チェック。既に処理しているimgpathかどうか
                if not pisc and imgpath in imgpaths:
                    # ElementTree編集
                    e.text = imgpaths[imgpath]
                else:
                    # 対象画像のコピー先を作成
                    if pisc:
                        idata = cw.binary.image.code_to_data(imgpath)
                        ext = cw.util.get_imageext(idata)
                        dname = cw.util.repl_dischar(data.gettext("Property/Name", "simage")) + ext
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
                        f = open(imgdst, "wb")
                        f.write(idata)
                        f.close()
                    else:
                        shutil.copy2(imgpath, imgdst)
                    # ElementTree編集
                    e.text = imgdst.replace(self.tempdir + "/", "", 1)
                    if not pisc:
                        # 重複して処理しないよう辞書に登録
                        imgpaths[imgpath] = e.text

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
                                                    and self.sdata._playing)

    def is_runningevent(self):
        return bool(self.event._nowrunningevents)

    def is_showingdlg(self):
        return self._showingdlg

    def is_fullscreen(self):
        return self._fullscreen

    def is_curtained(self):
        return self._curtained

    def is_dealing(self):
        return self._dealing

    def is_autospread(self):
        return self._autospread

    def is_gameover(self):
        if self.is_playingscenario():
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
        return self.backloggrp.get_sprites_from_layer("backlog")

    def is_debugmode(self):
        return self.debug

    def is_battlestatus(self):
        """現在のCWPyのステータスが、シナリオバトル中かどうか返す。
        if cw.cwpy.battle:と使い分ける。
        """
        return bool(self.status == "ScenarioBattle")

#-------------------------------------------------------------------------------
# 各種スプライト取得用メソッド
#-------------------------------------------------------------------------------

    def get_inusecardimg(self):
        """InuseCardImageインスタンスを返す(仕様カード)。"""
        try:
            return self.pcardgrp.get_sprites_from_layer("inusecard")[0]
        except:
            return None

    def get_guardcardimg(self):
        """InuseCardImageインスタンスを返す(防御・回避ボーナスカード)。"""
        try:
            return self.pcardgrp.get_sprites_from_layer("guardcard")[0]
        except:
            return None

    def get_messagewindow(self):
        """MessageWindow or SelectWindowインスタンスを返す。"""
        try:
            return self.pcardgrp.get_sprites_from_layer("message")[0]
        except:
            return None

    def get_mcards(self, mode=""):
        """MenuCardインスタンスのリストを返す。
        mode: "visible" or "invisible" or "visiblemenucards" or "flagtrue"
        """
        mcards = self.mcardgrp.get_sprites_from_layer(0)

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
                                    and self.sdata.flags.get(m.flag, True)]

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
        pcards = self.pcardgrp.get_sprites_from_layer(0)

        if mode == "unreversed":
            pcards = [pcard for pcard in pcards if not pcard.is_reversed()]
        elif mode == "active":
            pcards = [pcard for pcard in pcards if pcard.is_active()]

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
        self.rect = pygame.Rect((0, 0), cw.SIZE_AREA)

    def lclick_event(self):
        cw.cwpy.wait_showcards = False

    def rclick_event(self):
        cw.cwpy.wait_showcards = False

def main():
    pass

if __name__ == "__main__":
    main()
