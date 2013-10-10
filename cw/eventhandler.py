#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import pygame
from pygame.locals import *

import cw

class EventHandler(object):
    def run(self):
        cw.cwpy.has_inputevent = False

        # 左方向キー押しっぱなし
        if cw.cwpy.keyin[K_LEFT] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(x=-1)
        # 右方向キー押しっぱなし
        elif cw.cwpy.keyin[K_RIGHT] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(x=1)

        exception = None

        for event in cw.cwpy.events:
            if event.type == KEYDOWN:
                # ESCAPEキー
                if event.key == K_ESCAPE:
                    self.escapekey_event()
                # F1キー
                elif event.key == K_F1:
                    self.f1key_event()
                # F2キー
                elif event.key == K_F2:
                    self.f2key_event()
                # F3キー
                elif event.key == K_F3:
                    self.f3key_event()
                # F4キー
                elif event.key == K_F4:
                    self.f4key_event()
                # F5キー
                elif event.key == K_F5:
                    self.f5key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                # リターンキー
                elif event.key == K_RETURN:
                    self.returnkey_event()
                # 上方向キー
                elif event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # 左方向キー
                elif event.key == K_LEFT:
                    self.dirkey_event(x=-1)
                # 右方向キー
                elif event.key == K_RIGHT:
                    self.dirkey_event(x=1)

            elif event.type == KEYUP:
                # PrintScreenキー
                if event.key == K_PRINT:
                    self.printkey_event()

            elif event.type == MOUSEBUTTONUP:
                # 左クリックイベント
                if event.button == 1:
                    self.lclick_event()

                # 右クリックイベント
                elif event.button == 3:
                    self.rclick_event()

                # マウスホイール上移動
                elif event.button == 4:
                    self.wheel_event(y=-1)

                # マウスホイール下移動
                elif event.button == 5:
                    self.wheel_event(y=1)

            # ユーザイベント
            elif event.type == USEREVENT and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError, ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def calc_index(self, value):
        length = len(cw.cwpy.list)
        index = cw.cwpy.index
        index += value

        if length == 0:
            index = -1
        elif index >= length:
            index = 0
        elif index < 0:
            index = length - 1

        return index

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。カードのフォーカスを変更する。
        """
        if cw.cwpy.is_runningevent() or cw.cwpy.lock_menucards or pygame.event.peek(pygame.locals.USEREVENT):
            return

        cw.cwpy.has_inputevent = True

        if sidechange and cw.cwpy.is_pcardsselectable and cw.cwpy.is_mcardsselectable:
            if x < 0 and cw.cwpy.index == 0:
                x = 0
                y = -1
            elif 0 < x and cw.cwpy.index + 1 == len(cw.cwpy.list):
                x = 0
                y = 1

        if x:
            cw.cwpy.index = self.calc_index(x)

            if not cw.cwpy.index < 0:
                sprite = cw.cwpy.list[cw.cwpy.index]
                cw.cwpy.change_selection(sprite)

        elif y:
            seq = None
            if isinstance(cw.cwpy.selection, cw.sprite.card.PlayerCard):
                if cw.cwpy.is_mcardsselectable:
                    seq = cw.cwpy.get_mcards("visible")
            else:
                if cw.cwpy.is_pcardsselectable:
                    if cw.cwpy.is_debugmode() and not cw.cwpy.selectedheader:
                        seq = cw.cwpy.get_pcards()
                    else:
                        seq = cw.cwpy.get_pcards("unreversed")

            if seq:
                cw.cwpy.list = seq

                if sidechange:
                    if y < 0:
                        cw.cwpy.index = len(cw.cwpy.list) - 1
                    else:
                        cw.cwpy.index = 0
                else:
                    cw.cwpy.index = 0
                sprite = cw.cwpy.list[cw.cwpy.index]
                cw.cwpy.change_selection(sprite)

    def lclick_event(self):
        """
        左クリックイベント。
        """
        if cw.cwpy.is_runningevent() and\
                not isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton):
            return

        if cw.cwpy.selection:
            if cw.cwpy.lock_menucards:
                return
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards()

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.is_runningevent() and\
                not isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton):
            return

        if cw.cwpy.selection:
            if cw.cwpy.lock_menucards:
                return
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.rclick_event()
        elif cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
            # シナリオプレイ時、キャンプモード切替
            if cw.cwpy.status == "Scenario" and not cw.cwpy.is_dealing():
                cw.cwpy.has_inputevent = True
                cw.cwpy.sounds["click"].play()

                if cw.cwpy.areaid == -4:
                    cw.cwpy.clear_specialarea()
                else:
                    cw.cwpy.change_specialarea(-4)

            # パーティの宿滞在時、冒険の中断
            elif cw.cwpy.status == "Yado" and not cw.cwpy.is_dealing():

                cw.cwpy.has_inputevent = True
                cw.cwpy.sounds["click"].play()

                if cw.cwpy.areaid == 1:
                    cw.cwpy.call_dlg("RETURNTITLE")
                if cw.cwpy.areaid == 2:
                    cw.cwpy.exec_func(cw.cwpy.load_party, None)

            # シナリオ戦闘時、戦闘行動選択ダイアログ表示
            elif cw.cwpy.battle and cw.cwpy.battle.is_ready():
                cw.cwpy.sounds["click"].play()
                cw.cwpy.call_dlg("BATTLECOMMAND")

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards()

    def escapekey_event(self):
        """
        ESCAPEキーイベント。終了ダイアログ。
        """
        # メニューカードの表示を待っている場合は表示
        if cw.cwpy.wait_showcards:
            cw.cwpy.deal_cards()
        else:
            cw.cwpy.has_inputevent = True
            cw.cwpy.sounds["click"].play()
            cw.cwpy.call_dlg("CLOSE")

    def f1key_event(self):
        """
        F1キーイベント。ヘルプが無いので何もしない。
        """
        pass

    def f2key_event(self):
        """
        F2キーイベント。設定ダイアログを開く。
        """
        cw.cwpy.has_inputevent = True
        cw.cwpy.sounds["click"].play()
        cw.cwpy.call_dlg("SETTINGS")

    def f3key_event(self):
        """
        F3キーイベント。デバッガを開閉する。
        """
        cw.cwpy.sounds["page"].play()
        if cw.cwpy.setting.expandmode == "FullScreen":
            cw.cwpy.set_expanded(False)

        if cw.cwpy.frame.debugger:
            cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)
        else:
            cw.cwpy.frame.exec_func(cw.cwpy.frame.show_debugger)

    def f4key_event(self):
        """
        F4キーイベント。
        """
        cw.cwpy.set_expanded(not cw.cwpy.is_expanded())

    def f5key_event(self):
        """
        F5キーイベント。バックログを開く。
        すでに開いている場合は遡る。
        """
        cw.cwpy.sounds["page"].play()
        if cw.cwpy.is_showingbacklog():
            event = pygame.event.Event(KEYDOWN, key=K_UP)
            pygame.event.post(event)
        else:
            cw.cwpy.show_backlog()

##        for ecard in cw.cwpy.get_ecards():
##            for h in ecard.deck.talon:
##                print h.name, ecard.name
##
##        print "*"*20
##        import timeit
##        s = ("import cw;" +
##             "image = cw.util.load_image("ACTION0.png");" +
##             "cw.imageretouch.to_negative_for_card(image)")
##        timer = timeit.Timer(s)
##        print timer.timeit(5000)
##        # 回収された循環参照や回収不能オブジェクトが表示される
##        import gc
##        gc.set_debug(gc.DEBUG_LEAK)
##        gc.disable()
##        gc.collect()

    def f9key_event(self):
        """
        F9キーイベント。緊急避難。
        """
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_showingdlg() and not pygame.event.peek():
            fname = os.path.basename(cw.cwpy.ydata.party.data.fpath)
            path = cw.util.join_paths("Data/Temp/ScenarioLog/Party", fname)
            if os.path.isfile(path):
                cw.cwpy.has_inputevent = True
                cw.cwpy.sounds["signal"].play()
                cw.cwpy.call_dlg("F9")

    def returnkey_event(self):
        """
        リターンキーイベント。
        """
        if cw.cwpy.is_runningevent() and\
                not isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton):
            return

        if cw.cwpy.selection:
            if cw.cwpy.lock_menucards:
                return
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards()

    def printkey_event(self):
        """
        PrintScreenキーイベント。
        """
        cw.util.screenshot()

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        self.dirkey_event(x=y, sidechange=True)

    def executing_event(self, event):
        """
        cwpy.exec_func()でポストされたユーザイベント。
        CWPyスレッドで指定のメソッドを実行する。
        """
        cw.cwpy.has_inputevent = True
        func = event.func
        func(*event.args, **event.kwargs)

class EventHandlerForMessageWindow(EventHandler):
    def __init__(self, mwin):
        """メッセージウィンドウ表示中のイベントハンドラ。
        mwin: MessageWindowインスタンス。
        """
        self.mwin = mwin

    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyin[K_RETURN] > cw.cwpy.keyevent.threshold:
            self.returnkey_event(True)
        # 上方向キー押しっぱなし
        elif cw.cwpy.keyin[K_UP] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(y=-1)
        # 下方向キー押しっぱなし
        elif cw.cwpy.keyin[K_DOWN] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(y=1)

        exception = None

        for event in cw.cwpy.events:
            if event.type == KEYDOWN:
                # ESCAPEキー
                if event.key == K_ESCAPE:
                    self.escapekey_event()
                # F1キー
                elif event.key == K_F1:
                    self.f1key_event()
                # F2キー
                elif event.key == K_F2:
                    self.f2key_event()
                # F3キー
                elif event.key == K_F3:
                    self.f3key_event()
                # F4キー
                elif event.key == K_F4:
                    self.f4key_event()
                # F5キー
                elif event.key == K_F5:
                    self.f5key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                # リターンキー
                elif event.key == K_RETURN:
                    self.returnkey_event()
                # 上方向キー
                elif event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # Shiftキー
                elif event.key == K_RSHIFT or event.key == K_LSHIFT:
                    self.shiftkey_event(True)

            elif event.type == KEYUP:
                # PrintScreenキー
                if event.key == K_PRINT:
                    self.printkey_event()
                # Shiftキー
                elif event.key == K_RSHIFT or event.key == K_LSHIFT:
                    self.shiftkey_event(False)

            elif event.type == MOUSEBUTTONDOWN:
                # 右クリックイベント
                if event.button == 3 and cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                    self.shiftkey_event(True)

            elif event.type == MOUSEBUTTONUP:
                # マウスボタン押下(文字描画中のみ)
                if self.mwin.is_drawing and\
                        cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                    self.mouse_event()
                # 左クリック
                elif event.button == 1:
                    self.lclick_event()
                # ミドルクリック
                elif event.button == 2:
                    self.mclick_event()
                # 右クリック
                elif event.button == 3:
                    self.rclick_event()
                # マウスホイール上移動
                elif event.button == 4:
                    self.wheel_event(y=-1)
                # マウスホイール下移動
                elif event.button == 5:
                    self.wheel_event(y=1)

            # ユーザイベント
            elif event.type == USEREVENT and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError, ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def mouse_event(self):
        """
        全てのマウスボタン押下イベント。
        文字全て描画。
        """
        if self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            self.mwin.draw_all()

    def lclick_event(self):
        """
        左クリックイベント。
        """
        if cw.cwpy.selection:
            if cw.cwpy.selection.rect.collidepoint(cw.cwpy.mousepos) or\
                    isinstance(cw.cwpy.selection, cw.sprite.message.SelectionBar):
                cw.cwpy.has_inputevent = True
                cw.cwpy.selection.lclick_event()

        elif cw.cwpy.list and (len(cw.cwpy.list) == 1 or cw.cwpy.index >= 0) and\
                cw.cwpy.topgrp.get_sprites_from_layer("message"):
            if cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                sbar = cw.cwpy.list[cw.cwpy.index]
                if isinstance(sbar, cw.sprite.message.SelectionBar):
                    sbar.lclick_event(skip=True)

    def mclick_event(self):
        """
        ミドルクリックイベント。
        """
        if cw.cwpy.selection and len(cw.cwpy.list) > 1:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event(skip=True)

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.selection:
            if cw.cwpy.selection.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                cw.cwpy.selection.rclick_event()
        elif not cw.cwpy.topgrp.get_sprites_from_layer("message"):
            self.shiftkey_event(False)

    def f4key_event(self):
        """
        F4キーイベント。
        """
        hidden = not cw.cwpy.topgrp.get_sprites_from_layer("message")

        if hidden:
            self.shiftkey_event(False, False)

        EventHandler.f4key_event(self)

        if hidden:
            self.shiftkey_event(True, False)

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        """
        # 文字描画中の時は文字全て描画
        if self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            self.mwin.draw_all()

        # テキスト送り
        elif len(cw.cwpy.list) == 1:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            sbar.lclick_event(skip=True)
        elif not pushing and cw.cwpy.index >= 0:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            sbar.lclick_event(skip=True)

    def dirkey_event(self, x=0, y=0, pushing=False):
        """
        方向キーイベント。選択肢バーをフォーカスする。
        """
        if not self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            cw.cwpy.index = self.calc_index(y)
            sbar = cw.cwpy.list[cw.cwpy.index]
            cw.cwpy.change_selection(sbar)

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        if cw.cwpy.has_inputevent or not cw.cwpy.is_showingmessage():
            return

        if len(cw.cwpy.list) == 1 and y > 0:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            sbar.lclick_event(skip=True)

        elif cw.cwpy.list:
            cw.cwpy.has_inputevent = True
            self.dirkey_event(y=y)

    def shiftkey_event(self, down, redraw=True):
        """
        シフトキーイベント。
        メッセージウィンドウを一時的に非表示にする。
        """
        if down:
            cw.cwpy.clear_selection()
            cw.cwpy.topgrp.remove_sprites_of_layer("message")
            cw.cwpy.topgrp.remove_sprites_of_layer("selectionbar")
            if redraw:
                cw.cwpy.draw()
        else:
            if not cw.cwpy.topgrp.get_sprites_from_layer("message"):
                cw.cwpy.topgrp.add(self.mwin, layer="message")
                for sbar in self.mwin.selections:
                    cw.cwpy.topgrp.add(sbar, layer="selectionbar")
                if redraw:
                    cw.cwpy.draw()

class EventHandlerForBacklog(EventHandler):
    def __init__(self, backlog, index):
        """バックログ表示中のイベントハンドラ。
        """
        self.backlog = backlog
        self.index = index
        self.mwin = self.backlog[self.index].create_message()

        self._curtain = cw.sprite.message.BacklogCurtain(cw.cwpy.backloggrp)
        self._lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy.clear_selection()
        cw.cwpy.statusbar.change(False)
        cw.cwpy.lock_menucards = False
        cw.cwpy._is_showingbacklog = True

    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyin[K_RETURN] > cw.cwpy.keyevent.threshold:
            self.returnkey_event(True)
        # 上方向キー押しっぱなし
        elif cw.cwpy.keyin[K_UP] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(y=-1)
        # 下方向キー押しっぱなし
        elif cw.cwpy.keyin[K_DOWN] > cw.cwpy.keyevent.threshold:
            self.dirkey_event(y=1)

        exception = None

        for event in cw.cwpy.events:
            if event.type == KEYDOWN:
                # ESCAPEキー
                if event.key == K_ESCAPE:
                    self.escapekey_event()
                # F1キー
                elif event.key == K_F1:
                    self.f1key_event()
                # F2キー
                elif event.key == K_F2:
                    self.f2key_event()
                # F3キー
                elif event.key == K_F3:
                    self.f3key_event()
                # F4キー
                elif event.key == K_F4:
                    self.f4key_event()
                # F5キー
                elif event.key == K_F5:
                    self.f5key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                # リターンキー
                elif event.key == K_RETURN:
                    self.returnkey_event()
                # 上方向キー
                elif event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)

            elif event.type == KEYUP:
                # PrintScreenキー
                if event.key == K_PRINT:
                    self.printkey_event()

            elif event.type == MOUSEBUTTONUP:
                # 左クリック
                if event.button == 1:
                    self.lclick_event()
                # ミドルクリック
                elif event.button == 2:
                    self.mclick_event()
                # 右クリック
                elif event.button == 3:
                    self.rclick_event()
                # マウスホイール上移動
                elif event.button == 4:
                    self.wheel_event(y=-1)
                # マウスホイール下移動
                elif event.button == 5:
                    self.wheel_event(y=1)

            # ユーザイベント
            elif event.type == USEREVENT and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                    if not cw.cwpy.is_showingbacklog():
                        self.exit_backlog(False)
                except cw.event.EventError, ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def lclick_event(self):
        """
        左クリックイベント。
        バックログを進める。
        """
        self.returnkey_event()

    def mclick_event(self):
        """
        ミドルクリックイベント。
        バックログを進める。
        """
        self.lclick_event()

    def rclick_event(self):
        """
        右クリックイベント。
        バックログ終了。
        """
        if cw.cwpy.selection:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.rclick_event()
            return
        self.exit_backlog()

    def escapekey_event(self):
        """
        ESCAPEキーイベント。
        バックログ終了。
        """
        self.exit_backlog()

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        バックログを進める。
        """
        if cw.cwpy.selection:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()
            return
        self.wheel_event(y=1)

    def dirkey_event(self, x=0, y=0, pushing=False):
        """
        方向キーイベント。
        バックログを進めたり戻したりする。
        """
        # 縦方向の操作を優先
        if 0 < y:
            # バックログを進める
            self.wheel_event(y=y)
        elif y < 0:
            # バックログを遡る
            self.wheel_event(y=y)
        elif 0 < x:
            # バックログを進める
            self.wheel_event(y=x)
        elif x < 0:
            # バックログを遡る
            self.wheel_event(y=x)

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        バックログを進めたり戻したりする。
        """
        if cw.cwpy.has_inputevent:
            return

        if 0 < y:
            # バックログを進める
            if len(self.backlog) <= self.index + 1:
                # バックログ終了
                self.exit_backlog()
                return

            cw.cwpy.sounds["page"].play()
            self.index += 1

            self.update_sprites()
        else:
            # バックログを遡る
            cw.cwpy.sounds["page"].play()
            if self.index <= 0:
                return
            self.index -= 1

            self.update_sprites()

    def exit_backlog(self, playsound=True):
        if playsound:
            cw.cwpy.sounds["click"].play()
        # バックログ終了
        cw.cwpy.backloggrp.remove_sprites_of_layer("backlogbar")
        cw.cwpy.backloggrp.remove_sprites_of_layer("backlog")
        self.mwin = None
        cw.cwpy._is_showingbacklog = False
        cw.cwpy.lock_menucards = self._lock_menucards

        # 背景スプライト削除
        cw.cwpy.backloggrp.remove(self._curtain)
        cw.cwpy.statusbar.change(not cw.cwpy.is_runningevent())
        cw.cwpy.draw()

    def update_sprites(self):
        # スプライト削除
        cw.cwpy.backloggrp.remove_sprites_of_layer("backlogbar")
        cw.cwpy.backloggrp.remove_sprites_of_layer("backlog")
        # 次のバックログ
        self.mwin = self.backlog[self.index].create_message()

class EventHandlerForEffectBooster(EventHandler):
    def __init__(self):
        """エフェクトブースターのウェイト処理中の
        イベントハンドラ。
        """
        self.running = True

    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyin[K_RETURN] > cw.cwpy.keyevent.threshold:
            self.returnkey_event(True)

        exception = None

        for event in cw.cwpy.events:
            if event.type == KEYDOWN:
                # ESCAPEキー
                if event.key == K_ESCAPE:
                    self.escapekey_event()
                # F1キー
                elif event.key == K_F1:
                    self.f1key_event()
                # F2キー
                elif event.key == K_F2:
                    self.f2key_event()
                # F3キー
                elif event.key == K_F3:
                    self.f3key_event()
                # F4キー
                elif event.key == K_F4:
                    self.f4key_event()
                # F5キー
                elif event.key == K_F5:
                    self.f5key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                # リターンキー
                elif event.key == K_RETURN:
                    self.returnkey_event()

            elif event.type == KEYUP:
                # PrintScreenキー
                if event.key == K_PRINT:
                    self.printkey_event()

            elif event.type == MOUSEBUTTONUP:
                # 左クリック
                if event.button == 1:
                    self.lclick_event()
                # ミドルクリック
                elif event.button == 2:
                    self.mclick_event()
                # 右クリック
                elif event.button == 3:
                    self.rclick_event()

            # ユーザイベント
            elif event.type == USEREVENT and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError, ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.selection:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()
            return

        self.running = False

    def escapekey_event(self):
        """
        ESCAPEキーイベント。
        """
        self.running = False

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        """
        self.running = False

def main():
    pass

if __name__ == "__main__":
    main()

