#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import pygame
from pygame.locals import K_RETURN, K_ESCAPE, K_LEFT, K_RIGHT, K_UP, K_DOWN,\
                          K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F9,\
                          K_LSHIFT, K_RSHIFT, K_PRINT, KEYUP, KEYDOWN,\
                          MOUSEBUTTONUP, MOUSEBUTTONDOWN, USEREVENT

import cw

class EventHandler(object):
    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyevent.is_keyin(K_RETURN) and cw.cwpy.setting.autoenter_on_sprite:
            self.returnkey_event()
        # 左方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_LEFT):
            self.dirkey_event(x=-1)
        # 右方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_RIGHT):
            self.dirkey_event(x=1)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein() and cw.cwpy.setting.autoenter_on_sprite:
            self.returnkey_event()

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            self.check_puressedbutton(event)

            if event.type == KEYDOWN:
                # 上方向キー
                if event.key == K_UP:
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
                # ESCAPEキー
                elif event.key == K_ESCAPE:
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
                # F6キー
                elif event.key == K_F6:
                    self.f6key_event()
                # F7キー
                elif event.key == K_F7:
                    self.f7key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                else:
                    self.keydown_event(event.key)

            elif event.type == KEYUP:
                # リターンキー
                if event.key == K_RETURN:
                    self.returnkey_event()
                # PrintScreenキー
                elif event.key == K_PRINT:
                    self.printkey_event()
                else:
                    self.keyup_event(event.key)

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

    def check_puressedbutton(self, event):
        if not event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
            return

        button = event.button - 1
        if 0 <= button and button < len(cw.cwpy.keyevent.mousein):
            if event.type == MOUSEBUTTONDOWN:
                cw.cwpy.keyevent.mousein[button] = pygame.time.get_ticks()
            elif event.type == MOUSEBUTTONUP and not hasattr(event, "ignoreup"):
                cw.cwpy.keyevent.mousein[button] = 0

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

    def can_input(self):
        return not (cw.cwpy.is_showingdlg() or pygame.event.peek(pygame.locals.USEREVENT))

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。カードのフォーカスを変更する。
        """
        if cw.cwpy.is_showingdlg():
            return
        if cw.cwpy.is_runningevent() or cw.cwpy.is_processing or\
                cw.cwpy.is_lockmenucards(None):
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
            def get_mcards():
                seq = []
                if cw.cwpy.is_mcardsselectable:
                    seq = cw.cwpy.get_mcards("visible")
                return seq

            def get_pcards():
                seq = []
                if cw.cwpy.is_pcardsselectable:
                    if cw.cwpy.is_debugmode() and not cw.cwpy.selectedheader:
                        seq = cw.cwpy.get_pcards()
                    else:
                        seq = cw.cwpy.get_pcards("unreversed")
                return seq

            def get_etc():
                seq = []
                for sprite in cw.cwpy.topgrp.sprites():
                    if isinstance(sprite, cw.sprite.background.ClickableSprite):
                        seq.append(sprite)
                return seq

            if not cw.cwpy.selection or isinstance(cw.cwpy.selection,
                                                   cw.sprite.background.Curtain):
                if y < 0:
                    funcs = (get_pcards, get_etc, get_mcards)
                else:
                    funcs = (get_mcards, get_etc, get_pcards)
            elif isinstance(cw.cwpy.selection, cw.sprite.card.PlayerCard):
                if y < 0:
                    funcs = (get_etc, get_mcards)
                else:
                    funcs = (get_mcards, get_etc)
            elif isinstance(cw.cwpy.selection, cw.sprite.background.ClickableSprite):
                if y < 0:
                    funcs = (get_mcards, get_pcards)
                else:
                    funcs = (get_pcards, get_mcards)
            else:
                if y < 0:
                    funcs = (get_pcards, get_etc)
                else:
                    funcs = (get_etc, get_pcards)

            for func in funcs:
                seq = func()
                if seq:
                    break

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
        if cw.cwpy.is_showingdlg():
            return
        if (cw.cwpy.is_runningevent() and\
                not (isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton) and\
                     cw.cwpy.selection.selectable_on_event)) or\
                cw.cwpy.is_processing:
            return

        if cw.cwpy.selection:
            if cw.cwpy.is_lockmenucards(cw.cwpy.selection):
                return
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards(quickdeal=cw.cwpy.setting.all_quickdeal)

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.statusbar.clear_volumebar():
            return

        if cw.cwpy.is_showingdlg():
            return
        if (cw.cwpy.is_runningevent() and\
                not (isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton) and\
                     cw.cwpy.selection.selectable_on_event)) or\
                cw.cwpy.is_processing:
            return

        if cw.cwpy.selection:
            if cw.cwpy.is_lockmenucards(cw.cwpy.selection):
                return
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.rclick_event()
        elif cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
            if cw.cwpy.is_lockmenucards(None):
                return
            self.background_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards()

    def escapekey_event(self):
        """
        ESCAPEキーイベント。終了ダイアログ。
        """
        if cw.cwpy.is_showingdlg():
            return
        if cw.cwpy.is_lockmenucards(None):
            return
        # メニューカードの表示を待っている場合は表示
        if cw.cwpy.wait_showcards:
            cw.cwpy.deal_cards()
        else:
            self.background_event()

    def background_event(self):
        # シナリオプレイ時、キャンプモード切替
        if not cw.cwpy.is_runningevent():

            # 選択エリアの時、キャンセル
            if ((cw.cwpy.is_curtained() and cw.cwpy.areaid <> cw.AREA_CAMP) or cw.cwpy.selectedheader) and\
                    cw.cwpy.statusbar.showbuttons:
                cw.cwpy.cancel_cardcontrol()
                return

            # シナリオプレイ中、テーブル・キャンプモード切替
            elif cw.cwpy.status == "Scenario" and not cw.cwpy.is_dealing():
                cw.cwpy.has_inputevent = True
                cw.cwpy.play_sound("click")

                if cw.cwpy.areaid == -4:
                    cw.cwpy.clear_specialarea()
                else:
                    cw.cwpy.change_specialarea(-4)
                return

            # パーティの宿滞在時、冒険の中断
            elif cw.cwpy.status == "Yado" and not cw.cwpy.is_dealing():
                cw.cwpy.has_inputevent = True
                cw.cwpy.play_sound("click")

                if cw.cwpy.areaid == 1:
                    cw.cwpy.call_modaldlg("RETURNTITLE")
                if cw.cwpy.areaid == 2:
                    cw.cwpy.exec_func(cw.cwpy.load_party, None)
                return

            # シナリオ戦闘時、戦闘行動選択ダイアログ表示
            elif cw.cwpy.is_battlestatus() and cw.cwpy.battle.is_ready():
                cw.cwpy.play_sound("click")
                cw.cwpy.call_modaldlg("BATTLECOMMAND")
                return

        cw.cwpy.play_sound("click")
        cw.cwpy.call_modaldlg("CLOSE")

    def f1key_event(self):
        """
        F1キーイベント。ヘルプが無いので何もしない。
        """
        pass

    def f2key_event(self):
        """
        F2キーイベント。設定ダイアログを開く。
        """
        if cw.cwpy.is_showingdlg():
            return
        cw.cwpy.has_inputevent = True
        cw.cwpy.play_sound("click")
        cw.cwpy.call_modaldlg("SETTINGS")

    def f3key_event(self):
        """
        F3キーイベント。デバッガを開閉する。
        """
        if cw.cwpy.is_showingdlg():
            return
        if not cw.cwpy.is_debugmode():
            return
        cw.cwpy.play_sound("page")
        if cw.cwpy.setting.expandmode == "FullScreen":
            cw.cwpy.set_expanded(False)

        if cw.cwpy.frame.debugger:
            cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)
        else:
            cw.cwpy.keyevent.clear()
            cw.cwpy.frame.exec_func(cw.cwpy.frame.show_debugger, True)

    def f4key_event(self):
        """
        F4キーイベント。
        """
        if cw.cwpy.is_showingdlg():
            return
        cw.cwpy.set_expanded(not cw.cwpy.is_expanded())

    def f5key_event(self):
        """
        F5キーイベント。バックログを開く。
        すでに開いている場合は遡る。
        """
        if cw.cwpy.is_showingdlg():
            return
        if cw.cwpy.is_showingbacklog():
            event = pygame.event.Event(KEYDOWN, key=K_UP)
            pygame.event.post(event)
        elif cw.cwpy.has_backlog():
            cw.cwpy.play_sound("page")
            cw.cwpy.show_backlog()

        # PCの山札内のカード数を表示する
##        for pcard in cw.cwpy.get_pcards():
##            print "%s --------" % (pcard.name)
##            d = {}
##            for h in pcard.deck.talon:
##                d[h.name] = d.get(h.name, 0) + 1
##            for name, count in d.iteritems():
##                print "  %s: %s" % (name, count)
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

    def f6key_event(self):
        """
        F6キーイベント。
        情報カードビューを表示する。
        デバッグ戦闘中は同行キャストの表示有無を切り替える。
        """
        if not self.can_input():
            return
        if not cw.cwpy.is_playingscenario() or cw.cwpy.is_runningevent() or cw.cwpy.is_processing:
            return

        if not cw.cwpy.is_battlestatus() and cw.cwpy.sdata.has_infocards():
            cw.cwpy.play_sound("click")
            cw.content.PostEventContent.do_action("ShowDialog", "INFOVIEW")
        elif cw.cwpy.is_battlestatus() and cw.cwpy.is_debugmode() and\
                cw.cwpy.battle.is_ready() and cw.cwpy.get_fcards():
            cw.cwpy.play_sound("page")
            cw.cwpy.setting.show_fcardsinbattle = not cw.cwpy.setting.show_fcardsinbattle
            cw.cwpy.battle.update_showfcards()
            cw.cwpy.statusbar.change()
            cw.cwpy.draw()

    def f7key_event(self):
        """
        F7キーイベント。
        バトルの自動行動のオン・オフを切り替える。
        """
        if not self.can_input():
            return
        if cw.cwpy.setting.show_roundautostartbutton and cw.cwpy.is_playingscenario() and cw.cwpy.is_battlestatus():
            cw.cwpy.play_sound("page")
            cw.cwpy.sdata.autostart_round = not cw.cwpy.sdata.autostart_round
            cw.cwpy.statusbar.change(showbuttons=cw.cwpy.statusbar.showbuttons)
            cw.cwpy.draw(clip=cw.s(pygame.Rect(cw.RECT_STATUSBAR)))

    def f9key_event(self):
        """
        F9キーイベント。緊急避難。
        """
        if not self.can_input():
            return
        if cw.cwpy.is_playingscenario() and not cw.cwpy.is_showingdlg() and not pygame.event.peek():
            fname = os.path.basename(cw.cwpy.ydata.party.data.fpath)
            path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party", fname)
            if os.path.isfile(path):
                cw.cwpy.has_inputevent = True
                cw.cwpy.play_sound("signal")
                cw.cwpy.call_modaldlg("F9")

    def returnkey_event(self):
        """
        リターンキーイベント。
        """
        if not self.can_input():
            return
        if (cw.cwpy.is_runningevent() or cw.cwpy.is_processing) and\
                not (isinstance(cw.cwpy.selection, cw.sprite.statusbar.StatusBarButton) and\
                     cw.cwpy.selection.selectable_on_event):
            return

        if cw.cwpy.selection:
            if cw.cwpy.is_lockmenucards(cw.cwpy.selection):
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
        if not self.can_input():
            return
        cw.util.screenshot()

    def keydown_event(self, key):
        """その他のKEYDOWNイベント。"""
        if not self.can_input():
            return

    def keyup_event(self, key):
        """その他のKEYUPイベント。"""
        if not self.can_input():
            return

        pressed = pygame.key.get_pressed()
        ctrldown = cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]

        if ctrldown and key == ord('D'):
            if not cw.cwpy.is_showingdlg():
                cw.cwpy.play_sound("page")
                cw.cwpy.set_debug(not cw.cwpy.is_debugmode())
        elif ctrldown and key == ord('P'):
            cw.util.screenshot()

    def change_volume(self, val):
        if val <> 0 and pygame.mouse.get_pressed()[2]:
            # 右クリック+ホイール。音量の変更
            for music in cw.cwpy.music:
                volume = music.mastervolume + val
                volume = cw.util.numwrap(volume, 0, 100)
                music.set_mastervolume(volume)
                cw.cwpy.setting.vol_master = volume / 100.0
            cw.cwpy.statusbar.update_volumebar()
            return True
        return False

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        if not self.can_input():
            return

        if self.change_volume(-y):
            return

        if y < 0 and cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG:
            self.f5key_event()
            return

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
        autoenter_on_sprite = (cw.cwpy.setting.autoenter_on_sprite or len(self.mwin.selections) <= 1)

        # リターンキー押しっぱなし
        if cw.cwpy.keyevent.is_keyin(K_RETURN) and autoenter_on_sprite:
            self.returnkey_event(True)
        # 上方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_UP):
            self.dirkey_event(y=-1)
        # 下方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_DOWN):
            self.dirkey_event(y=1)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein() and autoenter_on_sprite:
            self.returnkey_event(True)

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            self.check_puressedbutton(event)

            if event.type == KEYDOWN:
                # 上方向キー
                if event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # Shiftキー
                elif event.key == K_RSHIFT or event.key == K_LSHIFT:
                    self.shiftkey_event(True)
                # ESCAPEキー
                elif event.key == K_ESCAPE:
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
                # F7キー
                elif event.key == K_F7:
                    self.f7key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                else:
                    self.keydown_event(event.key)

            elif event.type == KEYUP:
                # リターンキー
                if event.key == K_RETURN:
                    self.returnkey_event()
                # PrintScreenキー
                elif event.key == K_PRINT:
                    self.printkey_event()
                # Shiftキー
                elif event.key == K_RSHIFT or event.key == K_LSHIFT:
                    self.shiftkey_event(False)
                else:
                    self.keyup_event(event.key)

            elif event.type == MOUSEBUTTONDOWN:
                # 右クリックイベント
                if event.button == 3 and cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                    self.shiftkey_event(True)

            elif event.type == MOUSEBUTTONUP:
                # マウスボタン押下(文字描画中のみ)
                if self.mwin.is_drawing and\
                        cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos) and\
                        not (event.button == 4 and cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG):
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
        if not self.can_input():
            return
        if cw.cwpy.selection:
            if cw.cwpy.selection.rect.collidepoint(cw.cwpy.mousepos) or\
                    isinstance(cw.cwpy.selection, cw.sprite.message.SelectionBar):
                cw.cwpy.has_inputevent = True
                cw.cwpy.selection.lclick_event()

        elif cw.cwpy.list and (len(cw.cwpy.list) == 1 or cw.cwpy.index >= 0) and\
                cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE):
            if cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                sbar = cw.cwpy.list[cw.cwpy.index]
                if isinstance(sbar, cw.sprite.message.SelectionBar):
                    sbar.lclick_event(skip=True)

    def mclick_event(self):
        """
        ミドルクリックイベント。
        """
        if not self.can_input():
            return
        if cw.cwpy.selection and len(cw.cwpy.list) > 1:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event(skip=True)

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.statusbar.clear_volumebar():
            if not cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE):
                self.shiftkey_event(False)
            return

        if not self.can_input():
            return
        if cw.cwpy.selection:
            if cw.cwpy.selection.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                cw.cwpy.selection.rclick_event()
        elif not cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE):
            self.shiftkey_event(False)

    def f4key_event(self):
        """
        F4キーイベント。
        """
        if not self.can_input():
            return
        hidden = not cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE)

        if hidden:
            self.shiftkey_event(False, False)

        EventHandler.f4key_event(self)

        if hidden:
            self.shiftkey_event(True, False)

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        """
        if not self.can_input():
            return
        # 文字描画中の時は文字全て描画
        if self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            self.mwin.draw_all()

        # テキスト送り
        elif len(cw.cwpy.list) == 1:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            sbar.lclick_event(skip=True)
        elif isinstance(cw.cwpy.selection, cw.sprite.message.SelectionBar):
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.selection
            sbar.lclick_event(skip=True)
        elif not pushing and cw.cwpy.index >= 0:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            sbar.lclick_event(skip=True)

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。選択肢バーをフォーカスする。
        """
        if not self.can_input():
            return
        if not self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            cw.cwpy.index = self.calc_index(y)
            sbar = cw.cwpy.list[cw.cwpy.index]
            cw.cwpy.change_selection(sbar)

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        if not self.can_input():
            return

        if self.change_volume(-y):
            return

        if y < 0 and cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG:
            self.f5key_event()
            return

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
        if not self.can_input():
            return
        if down:
            if self.mwin.is_drawing:
                self.mwin.draw_all()
            else:
                cw.cwpy.clear_selection()
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_MESSAGE)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_1)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_2)
                if redraw:
                    cw.cwpy.draw()
        else:
            if not cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE):
                cw.cwpy.cardgrp.add(self.mwin, layer=cw.LAYER_MESSAGE)
                for sbar in self.mwin.selections:
                    cw.cwpy.cardgrp.add(sbar, layer=cw.LAYER_SELECTIONBAR_1)
                if redraw:
                    cw.cwpy.draw()

class EventHandlerForBacklog(EventHandler):
    def __init__(self, backlog, index):
        """バックログ表示中のイベントハンドラ。
        """
        self.backlog = backlog
        self.index = index
        self.mwin = self.backlog[self.index].create_message()

        self._page = cw.sprite.message.BacklogPage(self.index+1, len(self.backlog), cw.cwpy.backloggrp)
        self._curtain = cw.sprite.message.BacklogCurtain(cw.cwpy.backloggrp)
        self._lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy._is_showingbacklog = True
        cw.cwpy.clear_selection()
        cw.cwpy.statusbar.change(not cw.cwpy.is_runningevent())
        cw.cwpy.lock_menucards = False

    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyevent.is_keyin(K_RETURN):
            self.returnkey_event(True)
        # 上方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_UP):
            self.dirkey_event(y=-1)
        # 下方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_DOWN):
            self.dirkey_event(y=1)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein():
            self.returnkey_event(True)

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            self.check_puressedbutton(event)

            if event.type == KEYDOWN:
                # 上方向キー
                if event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # ESCAPEキー
                elif event.key == K_ESCAPE:
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
                # F7キー
                elif event.key == K_F7:
                    self.f7key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                else:
                    self.keydown_event(event.key)

            elif event.type == KEYUP:
                # リターンキー
                if event.key == K_RETURN:
                    self.returnkey_event()
                # PrintScreenキー
                elif event.key == K_PRINT:
                    self.printkey_event()
                else:
                    self.keyup_event(event.key)

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
        if cw.cwpy.statusbar.clear_volumebar():
            return

        if not self.can_input():
            return
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
        if not self.can_input():
            return
        self.exit_backlog()

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        バックログを進める。
        """
        if not self.can_input():
            return
        if cw.cwpy.selection:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()
            return
        self.wheel_event(y=1)

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。
        バックログを進めたり戻したりする。
        """
        if not self.can_input():
            return
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
        if not self.can_input():
            return
        if cw.cwpy.has_inputevent:
            return

        if self.change_volume(-y):
            return

        if 0 < y:
            # バックログを進める
            if len(self.backlog) <= self.index + 1:
                # バックログ終了
                self.exit_backlog()
                return

            cw.cwpy.play_sound("page")
            self.index += 1

            self.update_sprites()
        else:
            # バックログを遡る
            if self.index <= 0:
                cw.cwpy.play_sound("error")
                return
            cw.cwpy.play_sound("page")
            self.index -= 1

            self.update_sprites()

    def exit_backlog(self, playsound=True):
        if playsound:
            cw.cwpy.play_sound("click")
        # バックログ終了
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_CURTAIN)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_BAR)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_PAGE)
        self.mwin = None
        cw.cwpy._is_showingbacklog = False
        if cw.cwpy.lock_menucards:
            cw.cwpy.lock_menucards = self._lock_menucards

        # 背景スプライト削除
        cw.cwpy.statusbar.change(not cw.cwpy.is_runningevent())
        cw.cwpy.draw()

    def update_sprites(self):
        # スプライト削除
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_BAR)
        # 次のバックログ
        self.mwin = self.backlog[self.index].create_message()
        self._page.update_page(self.index+1, len(self.backlog))

class EventHandlerForEffectBooster(EventHandler):
    def __init__(self):
        """エフェクトブースターのウェイト処理中の
        イベントハンドラ。
        """
        self.running = True

    def run(self):
        cw.cwpy.has_inputevent = False

        # リターンキー押しっぱなし
        if cw.cwpy.keyevent.is_keyin(K_RETURN):
            self.returnkey_event(True)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein():
            self.returnkey_event(True)

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            self.check_puressedbutton(event)

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
                # F7キー
                elif event.key == K_F7:
                    self.f7key_event()
                # F9キー
                elif event.key == K_F9:
                    self.f9key_event()
                else:
                    self.keydown_event(event.key)

            elif event.type == KEYUP:
                # リターンキー
                if event.key == K_RETURN:
                    self.returnkey_event()
                # PrintScreenキー
                elif event.key == K_PRINT:
                    self.printkey_event()
                else:
                    self.keyup_event(event.key)

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
                except cw.event.EventError, ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def mclick_event(self):
        """
        ミドルクリックイベント。
        """
        self.rclick_event()

    def rclick_event(self):
        """
        右クリックイベント。
        """
        if cw.cwpy.statusbar.clear_volumebar():
            return

        if not self.can_input():
            return
        if cw.cwpy.selection:
            cw.cwpy.has_inputevent = True
            cw.cwpy.selection.lclick_event()
            return

        self.running = False

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        if not self.can_input():
            return

        if self.change_volume(-y):
            return

        if y < 0 and cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG:
            self.f5key_event()
            return

        self.running = False

    def escapekey_event(self):
        """
        ESCAPEキーイベント。
        """
        if not self.can_input():
            return
        self.running = False

    def returnkey_event(self, pushing=False):
        """
        リターンキーイベント。
        """
        if not self.can_input():
            return
        self.running = False

    def f4key_event(self):
        """
        F4キーイベント。
        """
        if not self.can_input():
            return
        cw.cwpy.exec_func(EventHandler.f4key_event, self)
        if cw.cwpy.setting.expanddrawing <> 1:
            raise cw.effectbooster.ScreenRescale()

def main():
    pass

if __name__ == "__main__":
    main()

