#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
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
        self.setting = setting  # 設定
        if frame and not hasattr(self, "frame"):
            threading.Thread.__init__(self)
            self.frame = frame   # 親フレーム
            self._running = False
            self._init_pygame()

    def _init_pygame(self):
        """使用変数等はここ参照。"""
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
        # クラシックなシナリオの再生中であればそのデータ
        self.classicdata = None
        # イベントハンドラ
        self.eventhandler = cw.eventhandler.EventHandler()
        # ゲーム状態を"Title"にセット
        self.exec_func(self.set_title)

    def _init_resources(self):
        """スキンが関わるリソースの初期化"""
        # リソース(辞書)
        self.rsrc = cw.setting.Resource(self.setting)
        # システム効果音(辞書)
        self.sounds = self.rsrc.sounds
        # その他のスキン付属効果音(辞書)
        self.skinsounds = self.rsrc.skinsounds
        # アクションカードのデータ(CardHeader)
        self.rsrc.actioncards = self.rsrc.get_actioncards()
        # 背景スプライト
        self.background = cw.sprite.background.BackGround()
        self.bggrp.set_clip(self.background.rect)
        self.mcardgrp.set_clip(self.background.rect)
        self.pcardgrp.set_clip(self.background.rect)
        self.topgrp.set_clip(self.background.rect)
        # ステータスバースプライト
        self.statusbar = cw.sprite.statusbar.StatusBar()
        # ステータスバークリップ
        self.sbargrp.set_clip(self.statusbar.rect)

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

    def tick_clock(self, speedrate=1):
        self.clock.tick(int(self.setting.fps * speedrate))

    def input(self, eventclear=False):
        self.mousein = pygame.mouse.get_pressed()
        mousepos = pygame.mouse.get_pos()
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

    def draw(self, mainloop=False):
        if self.has_inputevent or not mainloop:
            # SpriteGroup描画
            dirty_rects = self.bggrp.draw(self.scr)
            dirty_rects.extend(self.mcardgrp.draw(self.scr))
            dirty_rects.extend(self.pcardgrp.draw(self.scr))
            dirty_rects.extend(self.topgrp.draw(self.scr))
            dirty_rects.extend(self.sbargrp.draw(self.scr))
            # 画面更新
            pygame.display.update(dirty_rects)

    def call_dlg(self, name, **kwargs):
        """ダイアログを開く。
        name: ダイアログ名。cw.frame参照。
        """
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

        while self.is_running() and mwin.result is None:
            self.update()

            if mwin.result is None:
                self.draw(not mwin.is_drawing or self.has_inputevent)

            self.tick_clock()
            self.input()
            eventhandler.run()

        # cwpylist, index 初期化
        self.list = self.get_mcards("visible")
        self.index = -1
        self.clear_selection()
        # スプライト削除
        self.pcardgrp.remove_sprites_of_layer("selectionbar")
        self.pcardgrp.remove_sprites_of_layer("message")

        # メッセージ表示中にシナリオ強制終了(F9)などを行った場合、
        # イベント強制終了用のエラーを送出する。
        if isinstance(mwin.result, Exception):
            raise mwin.result
        else:
            return mwin.result

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

    def set_title(self):
        """タイトル画面へ遷移。"""
        self._init_resources()
        self.set_status("Title")
        cw.util.remove_temp()
        self.yadodir = ""
        self.tempdir = ""
        self.ydata = None
        self.sdata = cw.data.SystemData()
        s = "%s %s" % (cw.APP_NAME, self.setting.skinname)
        self.set_titlebar(s)
        self.statusbar.change()
        self.change_area(1)

    def set_yado(self):
        """宿画面へ遷移。"""
        self.set_status("Yado")
        self.sdata = cw.data.SystemData()
        s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
        s += os.path.basename(self.yadodir)
        self.set_titlebar(s)
        self.statusbar.change()

        if self.ydata.party:
            areaid = 2
        else:
            areaid = 1

        self.change_area(areaid)

    def set_scenario(self, header=None):
        """シナリオ画面へ遷移。
        header: ScenarioHeader
        """
        self.set_status("Scenario")
        self.battle = None
        self.statusbar.change()

        if header and not isinstance(self.sdata, cw.data.ScenarioData):
            self.sdata = cw.data.ScenarioData(header)
            loaded, musicpath = self.sdata.set_log()
            self.sdata.start()
            s = "%s %s - " % (cw.APP_NAME, self.setting.skinname)
            s += "%s %s" % (os.path.basename(self.yadodir), self.sdata.name)
            self.set_titlebar(s)
            areaid = self.sdata.startid

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

#-------------------------------------------------------------------------------
# エリアチェンジ関係メソッド
#-------------------------------------------------------------------------------

    def deal_cards(self):
        """hidden状態のMenuCard(対応フラグがFalseだったら表示しない)と
        PlayerCardを全て表示する。
        """
        self._dealing = True

        # カード自動配置の配置位置を再設定する
        if self.is_autospread():
            mcards = self.get_mcards("flagtrue")
            flag = bool(self.areaid == cw.AREA_CAMP and self.sdata.friendcards)
            self.set_autospread(mcards, flag)

        for mcard in self.get_mcards("invisible"):
            if self.sdata.flags.get(mcard.flag, True):
                cw.animation.animate_sprite(mcard, "deal")

        # list, indexセット
        if not self.is_showingmessage():
            self.list = self.get_mcards("visible")
            self.index = -1

        self.input(True)
        self._dealing = False

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

        self.input(True)

    def hide_party(self):
        """PlayerCardを非表示にする。"""
        pcards = [i for i in self.get_pcards() if not i.status == "hidden"]

        if pcards:
            cw.animation.animate_sprites(pcards, "shiftdown")

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

        # エリアイベントを開始(特殊エリアからの帰還だったら開始しない)
        if eventstarting and oldareaid > 0:
            self.deal_cards()

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
        self.sounds[u"battle"].play()
        # 戦闘開始アニメーション
        sprite = cw.sprite.background.BattleCardImage()
        cw.animation.animate_sprite(sprite, "battlestart")
        sprite.remove(cw.cwpy.pcardgrp)
        self.set_battle()
        oldareaid = self.areaid
        oldbgmpath = self.music.path
        self.change_area(areaid, False, ttype=("None", "Default"))
        # 戦闘音楽を流す
        path = self.sdata.data.gettext("/Property/MusicPath", "")
        self.music.play(path)

        if self.pre_battleareadata:
            oldareaid = self.pre_battleareadata[0]
            oldbgmpath = self.pre_battleareadata[1]

        self.pre_battleareadata = (oldareaid, oldbgmpath, self.music.path)
        self.battle = cw.battle.BattleEngine()

    def clear_battlearea(self, areachange=True):
        """戦闘状態を解除して戦闘前のエリアに戻る。
        areachangeがFalseだったら、戦闘前のエリアには戻らない
        (戦闘イベントで、エリア移動コンテント等が発動した時用)。
        """
        if self.status == "ScenarioBattle":
            areaid, bgmpath, battlebgmpath = self.pre_battleareadata
            self.pre_battleareadata = None
            self.set_scenario()

            if self.music.path == battlebgmpath:
                if areachange:
                    self.music.stop()
                    self.change_area(areaid, False, ttype=("None", "Default"))
                    self.music._play(bgmpath)
                else:
                    self.music._play(bgmpath)

            elif areachange:
                self.change_area(areaid, False, ttype=("None", "Default"))

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
        elif areaid == cw.AREA_SELECT and self.selectedheader:
            self.pre_areaids.append(self.areaid)
            self.areaid = areaid
            header = self.selectedheader
            owner = header.get_owner()

            if header.target in ("Both", "Enemy", "Party"):
                if self.status == "Scenario":
                    self.set_curtain(target=header.target)
                elif self.is_battlestatus():
                    if header.allrange:
                        if header.target == "Party":
                            targets = self.get_pcards("unreversed")
                        elif header.target == "Enemy":
                            targets = self.get_ecards("unreversed")
                        else:
                            targets = self.get_pcards("unreversed")
                            targets.extend(self.get_ecards("unreversed"))

                        owner.set_action(targets, header)
                        self.clear_specialarea()
                    else:
                        self.set_curtain(target=header.target)

            elif header.target == "User":
                if self.status == "Scenario":
                    self.change_selection(owner)
                    self.call_dlg("USECARD")
                elif self.is_battlestatus():
                    owner.set_action(owner, header)
                    self.clear_specialarea()

            elif header.target == "None":
                if self.is_battlestatus():
                    owner.set_action(owner, header)
                    self.clear_specialarea()

    def clear_specialarea(self):
        """特殊エリアに移動する前のエリアに戻る。
        areaidが-3(パーティ解散)の場合はエリアチェンジする。
        """
        if self.areaid <= 0:
            self.clear_curtain()
            self.selectedheader = None
            oldareaid = self.areaid
            areaid = self.pre_areaids.pop()

            # ターゲット選択エリアを解除の場合
            if oldareaid == cw.AREA_SELECT:
                self.areaid = areaid
                self.call_predlg()
            # カード移動操作エリアを解除の場合
            elif oldareaid in cw.AREAS_TRADE:
                self.areaid = areaid
                self.sdata.change_data(areaid)
                self.mcardgrp.remove_sprites_of_layer(0)
                self.mcardgrp.add(self.pre_mcards.pop())
                self.list = self.get_mcards("visible")
                self.index = -1
            else:
                self.change_area(areaid)

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
            if not self.areaid == cw.AREA_SELECT:
                targets, header, beasts = self.selection.actiondata
                self.set_inusecardimg(sprite, header)

                if header.target == "None":
                    self.set_targetarrow([sprite])
                else:
                    self.set_targetarrow(targets)

    def set_inusecardimg(self, owner, header, status="normal", center=False):
        """PlayerCardの前に使用中カードの画像を表示。"""
        if not self.get_inusecardimg():
            cw.sprite.background.InuseCardImage(owner, header, status, center)

    def clear_inusecardimg(self):
        """PlayerCardの前の使用中カードの画像を削除。"""
        self.pcardgrp.remove_sprites_of_layer("inusecard")

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

    def load_party(self, header=None):
        """パーティデータをロードする。
        header: PartyHeader。指定しない場合はパーティデータを空にする。
        """
        self.ydata.load_party(header)

        if header:
            areaid = 2
        else:
            areaid = 1

        self.change_area(areaid)

    def dissolve_party(self, pcard=None):
        """現在選択中のパーティからpcardを削除する。
        pcardがない場合はパーティ全体を解散する。
        """
        if not self.areaid == cw.AREA_BREAKUP:
            return

        if pcard:
            self.sounds[u"page"].play()
            cw.animation.animate_sprite(pcard, "delete")
            pcard.data.write_xml()
            self.ydata.add_standbys(pcard.data.fpath)

            if not self.get_pcards():
                self.dissolve_party()

        else:
            for pcard in self.get_pcards():
                pcard.remove_numbercoupon()

            p_money = int(self.ydata.party.data.find("Property/Money").text)
            p_members = [member.fpath for member in self.ydata.party.members]
            p_backpack = self.ydata.party.backpack
            self.ydata.deletedpaths.add(self.ydata.party.data.fpath)
            self.ydata.load_party(None)
            self.ydata.environment.edit("/Property/NowSelectingParty", "")
            self.ydata.set_money(p_money)

            for path in p_members:
                header = self.ydata.create_advheader(path)
                self.ydata.standbys.append(header)

            self.ydata.stopstandbysthread()
            cw.util.sort_by_attr(self.ydata.standbys, "name")

            cw.cwpy.ydata.stopstorehousethread()
            for header in p_backpack:
                header.set_owner("STOREHOUSE")
                self.ydata.storehouse.insert(0, header)

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

#-------------------------------------------------------------------------------
# データ編集・操作用メソッド。
#-------------------------------------------------------------------------------

    def trade(self, targettype, target=None, header=None, from_event=False, parentdialog=None):
        """
        カードの移動操作を行う。
        Getコンテントからこのメソッドを操作する場合は、
        ownerはNoneにする。
        """
        # カード移動操作用データを読み込む
        if self.selectedheader and not header:
            header = self.selectedheader

        owner = header.get_owner()

        # 移動先を設定。
        if targettype == "PLAYERCARD":
            target = target
        elif targettype == "BACKPACK":
            cw.cwpy.ydata.stopbackpackthread()
            target = self.ydata.party.backpack
        elif targettype == "STOREHOUSE":
            cw.cwpy.ydata.stopstorehousethread()
            target = self.ydata.storehouse
        elif targettype in ("PAWNSHOP", "TRASHBOX"):
            if targettype == "PAWNSHOP":
                if header.type == "SkillCard":
                    price = 200 + header.level * 100
                elif header.type == "ItemCard":
                    price = header.price * header.uselimit
                    if header.maxuselimit:
                        price /=  header.maxuselimit
                elif header.type == "BeastCard":
                    price = 500
                if not from_event:
                    s = u"%sを売却します。売り値は%dspです。よろしいですか？" % (header.name, price)
                    self.call_modaldlg("YESNO", text=s, parentdialog=parentdialog)
                    if self.get_yesnoresult() <> wx.ID_OK:
                        return
            else:
                if not from_event:
                    s = u"%sを捨てます。よろしいですか？" % (header.name)
                    self.call_modaldlg("YESNO", text=s, parentdialog=parentdialog)
                    if self.get_yesnoresult() <> wx.ID_OK:
                        return

            # プレミアカードは売却・破棄処理できない(イベントからの呼出以外)
            if header.premium == "Premium" and not from_event:
                if targettype == "PAWNSHOP":
                    self.sounds[u"error"].play()
                    s = u"プレミアカードは売却できません。"
                    self.call_dlg("MESSAGE", text=s, parentdialog=parentdialog)
                elif targettype == "TRASHBOX":
                    self.sounds[u"error"].play()
                    s = u"プレミアカードは破棄できません。"
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
                        self.trade("BACKPACK", header=header, from_event=True)

                else:
                    self.sounds[u"error"].play()
                    s = u"%sの手札は既に一杯です。" % target.name
                    self.call_dlg("MESSAGE", text=s, parentdialog=parentdialog)

                return

        # 音を鳴らす
        if not from_event:
            if targettype == "TRASHBOX":
                self.sounds[u"dump"].play()
            elif targettype == "PAWNSHOP":
                self.sounds[u"signal"].play()
            else:
                self.sounds[u"page"].play()

        #-----------------------------------------------------------------------
        # 移動元からデータを削除
        #-----------------------------------------------------------------------

        # 移動元がCharacterだった場合
        if isinstance(owner, cw.character.Character):
            # 移動元のCardHolderからCardHeaderを削除
            owner.cardpocket[index].remove(header)
            # 移動元からカードのエレメントを削除
            path = "/%ss" % header.type
            owner.data.remove(path, header.carddata)
            # 戦闘中だった場合はデッキからも削除
            owner.deck.remove(owner, header)

            # スキルの場合は使用回数は必ず0にする
            if header.type == "SkillCard":
                header.maxuselimit = 0
                header.uselimit = 0
                header.carddata.getfind("Property/UseLimit").text = "0"

            # ホールドをFalseに
            header.hold = False

            if not header.type == "BeastCard":
                header.carddata.getfind("Property/Hold").text = "False"

            # 移動先がカード置場だったら
            if targettype == "STOREHOUSE":
                header.write()

        # 移動元が荷物袋だった場合
        elif self.ydata.party and owner == self.ydata.party.backpack:
            # 移動元のリストからCardHeaderを削除
            owner.remove(header)
            # PartyデータのBackpackからカードデータを削除
            self.ydata.party.data.remove("/Backpack", header.carddata)

            # 移動先がカード置場だったら
            if targettype == "STOREHOUSE":
                header.write()

        # 移動元がカード置場だった場合
        elif owner == self.ydata.storehouse:
            # 移動元のリストからCardHeaderを削除
            owner.remove(header)

            # 移動先がPlayerCard・荷物袋だったら
            if targettype in ("PLAYERCARD", "BACKPACK"):
                header.contain_xml()

        # 移動元が存在しない場合(get or loseコンテンツから呼んだ場合)
        else:
            # 移動先がPlayerCard・荷物袋だったら
            if targettype in ("PLAYERCARD", "BACKPACK"):
                header.contain_xml()
            # 移動先がカード置場だったら
            elif targettype == "STOREHOUSE":
                header.write()

        #-----------------------------------------------------------------------
        # ファイル削除
        #-----------------------------------------------------------------------

        # 移動先がゴミ箱・下取りだったら
        if targettype in ("PAWNSHOP", "TRASHBOX"):
            # 付帯以外の召喚獣カードの場合
            if header.type == "BeastCard" and not header.attachment:
                owner.update_image()
            # シナリオで取得したカードじゃない場合、XMLの削除
            elif not header.scenariocard:
                self.remove_xml(header)

        #-----------------------------------------------------------------------
        # 移動先にデータを追加する
        #-----------------------------------------------------------------------

        # 移動先がPlayerCardだった場合
        if targettype == "PLAYERCARD":
            # cardpocketにCardHeaderを追加
            header.set_owner(target)
            target.cardpocket[index].append(header)
            # 使用回数を設定
            header.get_uselimit()
            # カードのエレメントを追加
            path = "/%ss" % header.type
            target.data.append(path, header.carddata)

            # 戦闘中の場合、Deckの手札・山札に追加
            if self.battle:
                target.deck.add(target, header)

        # 移動先が荷物袋だった場合
        elif targettype == "BACKPACK":
            # PartyデータのBackpackにカードデータを書き込む
            if targettype == "BACKPACK":
                self.ydata.party.data.insert("/Backpack", header.carddata, 0)

            # 移動先のリストにCardHeaderを追加
            target.insert(0, header)
            header.set_owner("BACKPACK")

        # 移動先がカード置場だった場合
        elif targettype in ("BACKPACK", "STOREHOUSE"):
            # 移動先のリストにCardHeaderを追加
            target.insert(0, header)
            header.set_owner("STOREHOUSE")
            header.carddata = None

        # 下取りに出した場合
        elif targettype == "PAWNSHOP":
            # パーティの所持金または金庫に下取金を追加
            if self.ydata.party:
                self.ydata.party.set_money(price)
            else:
                self.ydata.set_money(price)

        # カード移動操作用データを削除
        self.selectedheader = None

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

    def copy_materials(self, data, dstdir, from_scenario=True):
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
                        imgpath = cw.util.join_paths(self.sdata.scedir, e.text)
                    else:
                        imgpath = cw.util.join_yadodir(e.text)

                if not (pisc or os.path.isfile(imgpath)):
                    e.text = ""
                    continue

                # 重複チェック。既に処理しているimgpathかどうか
                if imgpath in imgpaths:
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
                        f = open(imgdst, 'wb')
                        f.write(idata)
                        f.close()
                    else:
                        shutil.copy2(imgpath, imgdst)
                    # ElementTree編集
                    e.text = imgdst.replace(self.tempdir + "/", "", 1)
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
            self._gameover |= not bool(self.get_pcards("unreversed"))

        return self._gameover

    def is_showingmessage(self):
        return bool(self.get_messagewindow())

    def is_showingdebugger(self):
        return bool(self.frame.debugger)

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
        """InuseCardImageインスタンスを返す。"""
        try:
            return self.pcardgrp.get_sprites_from_layer("inusecard")[0]
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

def main():
    pass

if __name__ == "__main__":
    main()
