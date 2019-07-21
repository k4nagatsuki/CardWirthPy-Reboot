#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import bisect
import sys
import time

import pygame
from pygame.locals import K_RETURN, K_ESCAPE, K_BACKSPACE, K_BACKSLASH, K_LEFT, K_RIGHT, K_UP, K_DOWN,\
                          K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8, K_F9,\
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
            if not self.check_puressedbutton(event):
                continue

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
                elif event.key == K_ESCAPE or event.key == K_BACKSPACE or event.key == K_BACKSLASH:
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
                # F8キー
                elif event.key == K_F8:
                    self.f8key_event()
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

            elif event.type == MOUSEBUTTONDOWN:
                # 左ボタン押下イベント
                if event.button == 1:
                    self.ldown_event()

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
            elif event.type in (USEREVENT, cw.FORCE_USEREVENT) and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError as ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    @staticmethod
    def is_skiptrigger(self, event):
        if event.type in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
            return event.button in (1, 3)
        if event.type in (KEYDOWN, KEYUP):
            return event.key == K_RETURN

    def clear_touchmenu(self):
        if cw.cwpy.pointed_tile:
            return

        if cw.cwpy.statusbar and\
                not isinstance(cw.cwpy.selection, cw.sprite.touchbutton.TouchButton) and\
                cw.cwpy.statusbar.touchmenu is not cw.cwpy.selection:
            cw.cwpy.statusbar.hide_touchbuttons(redraw=True)

    def check_puressedbutton(self, event):
        cw.cwpy.wheelmode_cursorpos = (-1, -1)

        if event.type not in (USEREVENT, cw.FORCE_USEREVENT):
            self.clear_touchmenu()

        if event.type not in (MOUSEBUTTONDOWN, MOUSEBUTTONUP):
            return True

        # フリック操作
        # フリック開始位置で右クリックイベントを発生させる
        if cw.cwpy.setting.enabled_right_flick and event.button == 1:
            selection = cw.cwpy.selection
            pos = pygame.mouse.get_pos()
            if not cw.cwpy.scr_fullscreen and pos[0] == cw.scr2mwin_s(cw.s(cw.SIZE_AREA[0]))-1 and\
                    not pygame.mouse.get_focused():
                # FIXME: カーソルが画面外に出ているとpos[0]が右端の位置になってしまう。
                #        wx側の機能を使うわけにもいかないので、苦肉の策として
                #        画面外にカーソルが出ていたらフリック距離分だけ移動した状態と見なす。
                pos = (cw.cwpy.keyevent.flick_start_pos[0]+cw.ppis(cw.cwpy.setting.flick_distance), pos[1])

            if event.type == MOUSEBUTTONDOWN:
                cw.cwpy.keyevent.flick_status = cw.frame.FLICK_START
                cw.cwpy.keyevent.flick_sprite = selection
                cw.cwpy.keyevent.flick_start_pos = pos
                cw.cwpy.keyevent.flick_start_time = time.process_time()
            elif cw.cwpy.keyevent.flick_status == cw.frame.FLICK_START and event.type == MOUSEBUTTONUP:
                xmove = cw.ppis(pos[0] - cw.cwpy.keyevent.flick_start_pos[0])
                ymove = cw.ppis(pos[1] - cw.cwpy.keyevent.flick_start_pos[1])
                dur = time.process_time() - cw.cwpy.keyevent.flick_start_time
                flick = False
                if cw.ppis(cw.cwpy.setting.flick_distance) <= xmove and dur <= cw.cwpy.setting.flick_time_msec/1000.0:
                    cw.cwpy.has_inputevent = False
                    cw.cwpy.change_selection(cw.cwpy.keyevent.flick_sprite)
                    if cw.cwpy.scr_fullscreen:
                        mousepos = cw.cwpy.keyevent.flick_start_pos
                        x = int((mousepos[0] - cw.cwpy.scr_pos[0]) / cw.cwpy.scr_scale)
                        y = int((mousepos[1] - cw.cwpy.scr_pos[1]) / cw.cwpy.scr_scale)
                        cw.cwpy.mousepos = (x, y)
                    else:
                        cw.cwpy.mousepos = cw.mwin2scr_s(cw.cwpy.keyevent.flick_start_pos)
                    flick = True

                cw.cwpy.keyevent.flick_status = cw.frame.FLICK_NONE
                cw.cwpy.keyevent.flick_sprite = None
                cw.cwpy.keyevent.flick_start_pos = (-1, -1)
                cw.cwpy.keyevent.flick_start_time = 0

                if flick:
                    self.rclick_event(flick=True)
                    return False

        button = event.button - 1
        if 0 <= button and button < len(cw.cwpy.keyevent.mousein):
            if event.type == MOUSEBUTTONDOWN:
                cw.cwpy.keyevent.mousein[button] = pygame.time.get_ticks()
            elif event.type == MOUSEBUTTONUP and not hasattr(event, "ignoreup"):
                cw.cwpy.keyevent.mousein[button] = 0

        return True

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
        return cw.cwpy.is_decompressing or not (cw.cwpy.is_showingdlg() or pygame.event.peek(pygame.locals.USEREVENT))

    def can_input_sys(self):
        return not cw.cwpy.is_showingdlg()

    def is_processing(self):
        return cw.cwpy.is_processing and not cw.cwpy.is_decompressing

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。カードのフォーカスを変更する。
        """
        if cw.cwpy.is_showingdlg():
            return
        if cw.cwpy.is_runningevent() or self.is_processing() or\
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
                cw.cwpy.wheelmode_cursorpos = cw.cwpy.mousepos

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
                cw.cwpy.wheelmode_cursorpos = cw.cwpy.mousepos

    def _update_selection(self, is_runningevent):
        # マウスポインタの移動を検知する前にクリックイベントが
        # 発生する可能性があるので、キーボード等で選択された
        # 状態でなければ、選択状態を更新しておく

        if cw.cwpy.pointed_tile:
            return cw.cwpy.pointed_tile

        if cw.cwpy.index == -1 and not is_runningevent and not self.is_processing():
            cw.cwpy.update_mousepos()
            cw.cwpy.update_groups((cw.cwpy.cardgrp, cw.cwpy.topgrp, cw.cwpy.sbargrp))
        return cw.cwpy.selection

    def ldown_event(self):
        """
        マウス左ボタン押下イベント。
        """
        if cw.cwpy.is_showingdlg():
            return

        selection = self._update_selection(is_runningevent=cw.cwpy.is_runningevent())

        if (cw.cwpy.is_runningevent() and
                not (selection and selection.is_statusctrl and
                     selection.selectable_on_event)) or\
                self.is_processing():
            return

        if selection:
            if cw.cwpy.is_lockmenucards(selection):
                return
            cw.cwpy.has_inputevent = True
            selection.ldown_event()

    def lclick_event(self):
        """
        左クリックイベント。
        """
        if cw.cwpy.is_showingdlg():
            return

        selection = self._update_selection(is_runningevent=cw.cwpy.is_runningevent())

        if (cw.cwpy.is_runningevent() and
                not (selection and selection.is_statusctrl and
                     selection.selectable_on_event)) or\
                self.is_processing():
            return

        if selection:
            if cw.cwpy.is_lockmenucards(selection):
                return
            cw.cwpy.has_inputevent = True
            selection.lclick_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards(quickdeal=cw.cwpy.setting.all_quickdeal)

    def rclick_event(self, flick=False):
        """
        右クリックイベント。
        """
        if not flick and cw.cwpy.statusbar.clear_volumebar():
            return

        if cw.cwpy.is_showingdlg():
            return

        if flick:
            selection = cw.cwpy.selection
        else:
            selection = self._update_selection(is_runningevent=cw.cwpy.is_runningevent())

        if (cw.cwpy.is_runningevent() and
                not (selection and selection.is_statusctrl and
                     selection.selectable_on_event)) or\
                self.is_processing():
            return

        if selection:
            if cw.cwpy.is_lockmenucards(selection):
                return
            cw.cwpy.has_inputevent = True
            selection.rclick_event()
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
        cw.cwpy.statusbar.hide_touchbuttons()
        if not cw.cwpy.is_runningevent():

            # 選択エリアの時、キャンセル
            if ((cw.cwpy.is_curtained() and cw.cwpy.areaid != cw.AREA_CAMP) or cw.cwpy.selectedheader) and\
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

            # スキン固有のエリアにいる時
            elif cw.cwpy.status == "Yado" and cw.SKIN_AREAS_MIN <= cw.cwpy.areaid <= cw.SKIN_AREAS_MAX:
                act = cw.cwpy.sdata.data.gettext("Property/BackgroundAction", "")
                if act == "ReturnTitle":
                    cw.cwpy.play_sound("click")
                    cw.cwpy.call_modaldlg("RETURNTITLE")
                elif act == "ReturnSystemArea":
                    cw.cwpy.play_sound("click")
                    e_ba = cw.cwpy.sdata.data.find("Property/BackgroundAction")
                    assert e_ba is not None
                    ttype = cw.content.EventContentBase.get_transitiontype_static(e_ba)
                    if cw.cwpy.ydata.party:
                        cw.cwpy.change_area(2, ttype=ttype)
                    else:
                        cw.cwpy.change_area(1, ttype=ttype)
                elif act == "Close":
                    cw.cwpy.play_sound("click")
                    cw.cwpy.call_modaldlg("CLOSE")
                elif act == "ChangeArea":
                    resid = cw.cwpy.sdata.data.getint("Property/BackgroundAction", "id", 0)
                    if resid and cw.content.check_areaid(resid) and cw.cwpy.sdata.get_areaname(resid) is not None:
                        e_ba = cw.cwpy.sdata.data.find("Property/BackgroundAction")
                        assert e_ba is not None
                        ttype = cw.content.EventContentBase.get_transitiontype_static(e_ba)
                        cw.cwpy.change_area(resid, ttype=ttype)
                        return
                    cw.cwpy.play_sound("error")
                else:
                    cw.cwpy.play_sound("error")
                return

            # パーティの宿滞在時、冒険の中断
            elif cw.cwpy.status == "Yado" and not cw.cwpy.is_dealing():
                cw.cwpy.has_inputevent = True
                cw.cwpy.play_sound("click")

                if cw.cwpy.areaid in (1, 3):
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
        F1キーイベント。
        コンパイル済みヘルプファイルCardWirthPy.chm
        またはオンラインヘルプを開く。
        """
        def func():
            if not cw.cwpy.frame:
                return
            cw.cwpy.play_sound("click")

            if sys.platform == "win32":
                chm = cw.util.join_paths(os.path.dirname(cw.exepath), "CardWirthPy.chm")
                if os.path.isfile(chm):
                    try:
                        import win32help
                        win32help.HtmlHelp(cw.cwpy.frame.GetHandle(), chm, win32help.HH_DISPLAY_TOC)
                        return
                    except Exception:
                        cw.util.print_ex()

            etree = cw.data.xml2etree("Data/Sites.xml")
            url = etree.getattr("OnlineHelp", "url")
            if url:
                cw.util.open_url(cw.cwpy.frame, url)
        cw.cwpy.frame.exec_func(func)

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
        すでに開いている場合は閉じる(スクロール可能な時)か
        遡る(1件ずつ表示している時)。
        """
        if cw.cwpy.is_showingdlg():
            return
        if cw.cwpy.is_showingbacklog():
            if cw.cwpy.setting.is_logscrollable():
                event = pygame.event.Event(KEYDOWN, key=K_ESCAPE)
                cw.thread.post_pygameevent(event)
            else:
                event = pygame.event.Event(KEYDOWN, key=K_UP)
                cw.thread.post_pygameevent(event)
        elif cw.cwpy.has_backlog():
            cw.cwpy.play_sound("page")
            cw.cwpy.show_backlog()

        # PCの山札内のカード数を表示する
#        for pcard in cw.cwpy.get_pcards():
#            print "%s --------" % (pcard.name)
#            d = {}
#            for h in pcard.deck.talon:
#                d[h.name] = d.get(h.name, 0) + 1
#            for name, count in d.iteritems():
#                print "  %s: %s" % (name, count)
#        for ecard in cw.cwpy.get_ecards():
#            for h in ecard.deck.talon:
#                print h.name, ecard.name
#
#        print "*"*20
#        import timeit
#        s = ("import cw;" +
#             "image = cw.util.load_image("ACTION0.png");" +
#             "cw.imageretouch.to_negative_for_card(image)")
#        timer = timeit.Timer(s)
#        print timer.timeit(5000)
#        # 回収された循環参照や回収不能オブジェクトが表示される
#        import gc
#        gc.set_debug(gc.DEBUG_LEAK)
#        gc.disable()
#        gc.collect()

    def f6key_event(self):
        """
        F6キーイベント。
        情報カードビューを表示する。
        デバッグ戦闘中は同行キャストの表示有無を切り替える。
        """
        if not self.can_input():
            return
        if self.is_processing():
            return

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.is_runningevent():
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
        elif cw.cwpy.setting.show_debuglogdialog and cw.cwpy.is_debugmode() and cw.cwpy.sdata.debuglog:
            # 前回終了したシナリオのデバッグログ
            cw.cwpy.play_sound("click")

            def func(debuglog):
                dlg = cw.debug.logging.DebugLogDialog(cw.cwpy.frame, debuglog)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
            cw.cwpy.frame.exec_func(func, cw.cwpy.sdata.debuglog)

    def f7key_event(self):
        """
        F7キーイベント。
        バトルの自動行動のオン・オフを切り替える。
        """
        if not self.can_input_sys():
            return
        if cw.cwpy.setting.show_roundautostartbutton and cw.cwpy.is_playingscenario() and cw.cwpy.is_battlestatus():
            cw.cwpy.play_sound("page")
            cw.cwpy.sdata.autostart_round = not cw.cwpy.sdata.autostart_round
            cw.cwpy.statusbar.change(showbuttons=cw.cwpy.statusbar.showbuttons)

    def f8key_event(self):
        """
        F8キーイベント。シナリオの添付テキストを開く。
        """
        if not self.can_input_sys():
            return
        if not cw.cwpy.is_playingscenario() and not (cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata):
            return
        cw.fsync.sync()
        sdata = cw.cwpy.ydata.losted_sdata if cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata else cw.cwpy.sdata
        if sdata.instructions:
            cw.cwpy.call_modaldlg("INSTRUCTIONS")
        else:
            cw.cwpy.play_sound("error")

    def f9key_event(self):
        """
        F9キーイベント。緊急避難。
        """
        if not self.can_input_sys():
            return
        cw.fsync.sync()

        if EventHandler.can_f9():
            cw.cwpy.has_inputevent = True
            cw.cwpy.play_sound("signal")
            cw.cwpy.call_modaldlg("F9")

    @staticmethod
    def can_f9():
        if cw.cwpy.is_decompressing:
            # アーカイブの展開をキャンセルする場合
            return True

        # 開始済みのシナリオから離脱する場合
        sdata = cw.cwpy.ydata.losted_sdata if cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata else cw.cwpy.sdata
        is_playingscenario = cw.cwpy.is_playingscenario() or (cw.cwpy.ydata and cw.cwpy.ydata.losted_sdata)
        if is_playingscenario and not sdata.in_endprocess and not sdata.in_f9 and\
                not cw.cwpy.is_showingdlg() and not pygame.event.peek(pygame.locals.USEREVENT):
            fname = os.path.basename(cw.cwpy.ydata.party.data.fpath)
            path = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party", fname)
            return os.path.isfile(path)

    def returnkey_event(self):
        """
        リターンキーイベント。
        """
        if not self.can_input():
            return
        if (cw.cwpy.is_runningevent() or self.is_processing()) and\
                not (cw.cwpy.selection and cw.cwpy.selection.is_statusctrl and
                     cw.cwpy.selection.selectable_on_event):
            return

        if cw.cwpy.selection:
            if cw.cwpy.is_lockmenucards(cw.cwpy.selection):
                return
            cw.cwpy.has_inputevent = True
            if not cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]:
                cw.cwpy.selection.lclick_event()
            else:
                cw.cwpy.selection.rclick_event()

        elif cw.cwpy.wait_showcards:
            # メニューカードの表示を待っている場合は表示
            cw.cwpy.deal_cards()

    def printkey_event(self):
        """
        PrintScreenキーイベント。
        """
        if not self.can_input_sys():
            return

        self.capture_screenshot()

    def keydown_event(self, key):
        """その他のKEYDOWNイベント。"""
        if not self.can_input_sys():
            return False

        ctrldown = cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]

        if ctrldown and key == ord('D'):
            if not cw.cwpy.is_showingdlg():
                cw.cwpy.play_sound("page")
                cw.cwpy.set_debug(not cw.cwpy.is_debugmode())
                return False
        return True

    def keyup_event(self, key):
        """その他のKEYUPイベント。"""
        if not self.can_input_sys():
            return False

        ctrldown = cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]

        if ctrldown and key == ord('P'):
            self.capture_screenshot()
            return False
        return True

    def capture_screenshot(self):
        shiftdown = cw.cwpy.keyevent.keyin[pygame.K_LSHIFT] or cw.cwpy.keyevent.keyin[pygame.K_RSHIFT]
        if shiftdown:
            cw.util.card_screenshot()
        else:
            cw.util.screenshot()
        return

    def change_volume(self, val):
        if val != 0 and cw.cwpy.mousein[2]:
            # 右クリック+ホイール。音量の変更
            for music in cw.cwpy.music:
                volume = music.mastervolume + val * cw.cwpy.setting.volume_increment
                volume = cw.util.numwrap(volume, 0, 100)
                music.set_mastervolume(volume)
                cw.cwpy.setting.vol_master = volume / 100.0
            for sound in cw.cwpy.lastsound_scenario:
                if sound:
                    volume = sound.mastervolume + val * cw.cwpy.setting.volume_increment
                    sound.set_mastervolume(True, volume)
            if cw.cwpy.lastsound_system:
                volume = cw.cwpy.lastsound_system.mastervolume + val * cw.cwpy.setting.volume_increment
                cw.cwpy.lastsound_system.set_mastervolume(False, volume)
            cw.cwpy.statusbar.update_volumebar()
            return True
        return False

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        """
        if not self.can_input_sys():
            return

        if self.change_volume(-y):
            return

        if not self.can_input():
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
        # 左方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_LEFT):
            self.dirkey_event(x=-1)
        # 右方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_RIGHT):
            self.dirkey_event(x=1)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein() and autoenter_on_sprite:
            self.returnkey_event(True)

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            if not self.check_puressedbutton(event):
                continue

            if event.type == KEYDOWN:
                # 上方向キー
                if event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # 左方向キー
                if event.key == K_LEFT:
                    self.dirkey_event(x=-1)
                # 右方向キー
                elif event.key == K_RIGHT:
                    self.dirkey_event(x=1)
                # Shiftキー
                elif event.key == K_RSHIFT or event.key == K_LSHIFT:
                    self.shiftkey_event(True)
                # ESCAPEキー
                elif event.key == K_ESCAPE or event.key == K_BACKSPACE or event.key == K_BACKSLASH:
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
                # F8キー
                elif event.key == K_F8:
                    self.f8key_event()
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
                if event.button == 3 and cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                    # 右クリックイベント
                    self.shiftkey_event(True)
                elif event.button == 1:
                    # 左ボタン押下イベント
                    self.ldown_event()

            elif event.type == MOUSEBUTTONUP:
                # マウスボタン押下(文字描画中のみ)
                if self.mwin.is_drawing and\
                        not (cw.cwpy.selection and cw.cwpy.selection.selectable_on_event) and\
                        not (event.button == 4 and cw.cwpy.setting.wheelup_operation == cw.setting.WHEEL_SHOWLOG):
                    self.mouse_event(event.button)
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
            elif event.type in (USEREVENT, cw.FORCE_USEREVENT) and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError as ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def mouse_event(self, button):
        """
        全てのマウスボタン押下イベント。
        文字全て描画。
        """
        if self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True
            self.mwin.draw_all()
        elif button == 1:
            EventHandler.ldown_event(self)

    def ldown_event(self):
        if cw.cwpy.setting.enabled_right_flick and\
                cw.cwpy.statusbar.rect.collidepoint(cw.cwpy.mousepos) and\
                not self._update_selection(is_runningevent=self.mwin.is_drawing):
            self.shiftkey_event(True)
        else:
            EventHandler.ldown_event(self)

    def lclick_event(self):
        """
        左クリックイベント。
        """
        if not self._has_message():
            self.shiftkey_event(False)
            return

        if not self.can_input():
            return

        selection = self._update_selection(is_runningevent=self.mwin.is_drawing)

        if selection:
            if selection.rect.collidepoint(cw.cwpy.mousepos) or\
                    isinstance(selection, cw.sprite.message.SelectionBar):
                cw.cwpy.has_inputevent = True
                selection.lclick_event()

        elif cw.cwpy.list and (len(cw.cwpy.list) == 1 or cw.cwpy.index >= 0) and\
                self._has_message():
            if cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                sbar = cw.cwpy.list[cw.cwpy.index]
                if isinstance(sbar, cw.sprite.message.SelectionBar):
                    sbar.lclick_event(skip=True)

    def _has_message(self):
        return cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_MESSAGE) or \
               cw.cwpy.cardgrp.get_sprites_from_layer(cw.LAYER_SPMESSAGE)

    def mclick_event(self):
        """
        ミドルクリックイベント。
        """
        if not self.can_input():
            return

        selection = self._update_selection(is_runningevent=self.mwin.is_drawing)

        if selection and len(cw.cwpy.list) > 1:
            cw.cwpy.has_inputevent = True
            selection.lclick_event(skip=True)

    def rclick_event(self, flick=False):
        """
        右クリックイベント。
        """
        if not flick and cw.cwpy.statusbar.clear_volumebar():
            if not self._has_message():
                self.shiftkey_event(False)
            return

        if not self.can_input():
            return

        if flick:
            selection = cw.cwpy.selection
        else:
            selection = self._update_selection(is_runningevent=self.mwin.is_drawing)

        if selection:
            if selection.rect.collidepoint(cw.cwpy.mousepos):
                cw.cwpy.has_inputevent = True
                selection.rclick_event()
        elif not self._has_message():
            self.shiftkey_event(False)

    def f4key_event(self):
        """
        F4キーイベント。
        """
        if not self.can_input():
            return
        hidden = not self._has_message()

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
            if isinstance(sbar, cw.sprite.message.SelectionBar):
                sbar.lclick_event(skip=True)
        elif isinstance(cw.cwpy.selection, cw.sprite.message.SelectionBar):
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.selection
            if isinstance(sbar, cw.sprite.message.SelectionBar):
                sbar.lclick_event(skip=True)
        elif not pushing and cw.cwpy.index >= 0:
            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            if isinstance(sbar, cw.sprite.message.SelectionBar):
                sbar.lclick_event(skip=True)

    def dirkey_event(self, x=0, y=0, pushing=False, sidechange=False):
        """
        方向キーイベント。選択肢バーをフォーカスする。
        """
        if not self.can_input():
            return
        if not self.mwin.is_drawing:
            cw.cwpy.has_inputevent = True

            if 0 <= cw.cwpy.index and cw.cwpy.index < len(self.mwin.selections):
                if y:
                    maxrow = (len(self.mwin.selections)+self.mwin.columns-1) // self.mwin.columns
                    if 0 < y:
                        cw.cwpy.index += self.mwin.columns
                        if len(self.mwin.selections) <= cw.cwpy.index:
                            cw.cwpy.index = (cw.cwpy.index+1) % (maxrow*self.mwin.columns) % self.mwin.columns
                    elif y < 0:
                        cw.cwpy.index -= self.mwin.columns
                        if cw.cwpy.index < 0:
                            cw.cwpy.index += maxrow*self.mwin.columns+self.mwin.columns - 1
                            if len(self.mwin.selections) <= cw.cwpy.index:
                                cw.cwpy.index -= self.mwin.columns
                            if len(self.mwin.selections) <= cw.cwpy.index:
                                cw.cwpy.index -= self.mwin.columns

                else:
                    cw.cwpy.index = self.calc_index(x)

            else:
                cw.cwpy.index = 0

            sbar = cw.cwpy.list[cw.cwpy.index]
            cw.cwpy.change_selection(sbar)
            cw.cwpy.wheelmode_cursorpos = cw.cwpy.mousepos

    def keydown_event(self, key):
        """その他のKEYDOWNイベント。"""
        if not EventHandler.keydown_event(self, key):
            return

        if not self.can_input():
            return False

        ctrldown = cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]

        if ctrldown and key == ord('C') and self.can_copytext():
            self.copy_text()
            return False
        return True

    def can_copytext(self):
        return not self.mwin.is_drawing

    def copy_text(self):
        cw.cwpy.play_sound("equipment")
        s = cw.sprite.message.get_messagelogtext((self.mwin,))
        cw.cwpy.frame.exec_func(cw.util.to_clipboard, s)

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

            if not cw.cwpy.setting.can_forwardmessage_with_wheel:
                # ホイールによるメッセージ送り無効の設定
                return

            cw.cwpy.has_inputevent = True
            sbar = cw.cwpy.list[cw.cwpy.index]
            if isinstance(sbar, cw.sprite.message.SelectionBar):
                sbar.lclick_event(skip=True)

        elif cw.cwpy.list:
            cw.cwpy.has_inputevent = True
            self.dirkey_event(x=y)

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
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SPMESSAGE)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_1)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_1)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SELECTIONBAR_2)
                cw.cwpy.cardgrp.remove_sprites_of_layer(cw.LAYER_SPSELECTIONBAR_2)
                cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE)
                if redraw:
                    cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)
                    cw.cwpy.add_lazydraw(clip=cw.cwpy.statusbar.rect)
        else:
            if not self._has_message():
                if cw.cwpy.background.curtain_all or cw.cwpy.areaid in cw.AREAS_SP:
                    layer = cw.LAYER_SPMESSAGE
                    sellayer = cw.LAYER_SELECTIONBAR_1
                else:
                    layer = cw.LAYER_MESSAGE
                    sellayer = cw.LAYER_SELECTIONBAR_1
                cw.cwpy.cardgrp.add(self.mwin, layer=layer)
                for sbar in self.mwin.selections:
                    cw.cwpy.cardgrp.add(sbar, layer=sellayer)
                    if cw.s(cw.SIZE_AREA[1]) <= sbar.rect.bottom:
                        cw.cwpy.sbargrp.add(sbar, layer=cw.sprite.statusbar.LAYER_MESSAGE)
                if redraw:
                    cw.cwpy.add_lazydraw(clip=cw.cwpy.background.rect)
                    cw.cwpy.add_lazydraw(clip=cw.cwpy.statusbar.rect)


class EventHandlerForBacklog(EventHandler):
    def __init__(self, backlog, index):
        """バックログ表示中のイベントハンドラ。
        """
        self.backlog_all = backlog
        self.index = index
        self._scrollnum_noscale = cw.SIZE_AREA[1] // 4
        self._space_noscale = 5
        self._upscr = cw.UP_SCR

        self._messagelog_type = cw.cwpy.setting.messagelog_type

        self._lock_menucards = cw.cwpy.lock_menucards
        cw.cwpy._is_showingbacklog = True
        cw.cwpy.clear_selection()
        cw.cwpy.lock_menucards = False

        self._in_scroll = False

        self._sbarbar = None
        self._update_posdata(init=True)

        self.stw = cw.sprite.base.StopTheWorld(pygame.time.get_ticks(), 0)

    def _update_posdata(self, init):
        sbarbar = cw.cwpy.sbargrp.get_sprites_from_layer(cw.sprite.statusbar.LAYER_MESSAGE)
        if self._sbarbar and sbarbar:
            # ステータスバー上にはみ出した選択肢が一時的に非表示にされ、
            # かつ画面スケールが変更された時には、選択肢が新規生成され
            # 非表示化中の選択肢は不要になるので破棄する
            self._sbarbar = None

        self._clear_sprites()

        self.backlog = self.backlog_all

        # 各ログの位置
        if self.backlog and cw.cwpy.setting.is_logscrollable():
            self._height_noscale = [self.backlog[0].get_height_noscale()]
            self._pos_noscale = [self.backlog[0].rect_noscale[1]]
            self._bottom_noscale = [self._pos_noscale[0]+self._height_noscale[0]]
            if 1 < len(self.backlog):
                for i, log in enumerate(self.backlog[1:]):
                    self._height_noscale.append(log.get_height_noscale())
                    self._pos_noscale.append(self._pos_noscale[i]+self._height_noscale[i]+self._space_noscale)
                    self._bottom_noscale.append(self._pos_noscale[i+1]+self._height_noscale[i+1])
            # 最後の1件の下のスペースを加えてスクロールサイズとする
            h = self._height_noscale[-1]
            scrsize_noscale = self._pos_noscale[-1]+h
            if cw.cwpy.setting.messagelog_type == cw.setting.LOG_COMPRESS:
                scrsize_noscale += self._pos_noscale[0]
            else:
                scrsize_noscale += cw.SIZE_AREA[1]-(h+self.backlog[-1].rect_noscale[1])
                scrsize_noscale = max(scrsize_noscale, self._bottom_noscale[-1]+cw.s(5))
        else:
            self._height_noscale = []
            self._pos_noscale = []
            self._bottom_noscale = []
            scrsize_noscale = 0

        self._curtain = cw.sprite.message.BacklogCurtain(cw.cwpy.backloggrp, cw.LAYER_LOG_CURTAIN, cw.SIZE_AREA, (0, 0))
        if sbarbar:
            # 現在の仕様ではステータスバー上にはみ出る選択肢は1件まで
            assert len(sbarbar) == 1
            if cw.cwpy.setting.is_logscrollable():
                # スクロールする時はステータスバー上の選択肢を一時的に非表示化する
                self._sbarbar = sbarbar[0]
                cw.cwpy.sbargrp.remove(self._sbarbar)
            else:
                # 1件ずつ表示する時はステータスバー上の選択肢にもカーテンをかける
                sbarbar = sbarbar[0]
                self._curtain2 = cw.sprite.message.BacklogCurtain(cw.cwpy.sbargrp,
                                                                  cw.sprite.statusbar.LAYER_MESSAGE_LOG_CURTAIN,
                                                                  sbarbar.size_noscale, sbarbar.pos_noscale)
                self._sbarbar = None
        else:
            self._curtain2 = None
            self._sbarbar = None

        if init:
            self._scrollbar = cw.sprite.scrollbar.ScrollBar(scrsize_noscale-cw.SIZE_AREA[1], scrsize_noscale,
                                                            visible=cw.cwpy.setting.is_logscrollable())
            self._scrollbar.lazyscroll_func = self.update_sprites
            self.index = min(self.index, self._get_maxpage()-1)
            self._page = cw.sprite.message.BacklogPage(self.index+1, self._get_maxpage(), cw.cwpy.backloggrp)
        else:
            self._scrollbar = cw.sprite.scrollbar.ScrollBar(self._scrollbar.scrpos_noscale, scrsize_noscale,
                                                            visible=cw.cwpy.setting.is_logscrollable())
            self._scrollbar.lazyscroll_func = self.update_sprites
            self._page = cw.sprite.message.BacklogPage(self.index+1, self._get_maxpage(), cw.cwpy.backloggrp)
        cw.cwpy.backloggrp.add(self._scrollbar, layer=cw.LAYER_LOG_SCROLLBAR)

        self._mwins = [None] * len(self.backlog)
        self.mwin = None

        cw.cwpy.statusbar.change(not cw.cwpy.is_runningevent())

        self.update_sprites()

    def run(self):
        cw.cwpy.has_inputevent = False

        self._check_updatesettings()

        # リターンキー押しっぱなし
        if cw.cwpy.keyevent.is_keyin(K_RETURN):
            self.returnkey_event(True)
        # 上方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_UP):
            self.dirkey_event(y=-1)
        # 下方向キー押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(K_DOWN):
            self.dirkey_event(y=1)
        # ページアップ押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(pygame.locals.K_PAGEUP):
            self.keydown_event(pygame.locals.K_PAGEUP)
        # ページダウン押しっぱなし
        elif cw.cwpy.keyevent.is_keyin(pygame.locals.K_PAGEDOWN):
            self.keydown_event(pygame.locals.K_PAGEDOWN)
        # 左クリック押しっぱなし
        elif cw.cwpy.keyevent.is_mousein():
            self.returnkey_event(True)

        if self._in_scroll:
            self.ldown_event()

        exception = None

        while True:
            event = cw.cwpy.get_nextevent()
            if not event:
                break
            if not self.check_puressedbutton(event):
                continue

            if event.type == KEYDOWN:
                # 上方向キー
                if event.key == K_UP:
                    self.dirkey_event(y=-1)
                # 下方向キー
                elif event.key == K_DOWN:
                    self.dirkey_event(y=1)
                # ESCAPEキー
                elif event.key == K_ESCAPE or event.key == K_BACKSPACE or event.key == K_BACKSLASH:
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
                # F8キー
                elif event.key == K_F8:
                    self.f8key_event()
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

            elif event.type == MOUSEBUTTONDOWN:
                # 左クリック
                if event.button == 1:
                    self.ldown_event()

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
            elif event.type in (USEREVENT, cw.FORCE_USEREVENT) and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                    if not cw.cwpy.is_showingbacklog():
                        self.exit_backlog(False)
                except cw.event.EventError as ex:
                    # 全てのイベントを確実に実行するため
                    # 例外はここでキャッチしておき、最後に投げる
                    exception = ex

        if exception:
            raise exception

    def ldown_event(self):
        selection = self._update_selection(is_runningevent=cw.cwpy.is_runningevent())
        if selection:
            EventHandler.ldown_event(self)
        elif cw.cwpy.setting.is_logscrollable():
            if self._in_scroll or cw.cwpy.background.rect.collidepoint(cw.cwpy.mousepos):
                lazy = not self._in_scroll
                self._scrollbar.scroll_to_mousepos(lazy)
                if not lazy:
                    self.update_sprites()
                self._in_scroll = True

    def lclick_event(self):
        """
        左クリックイベント。
        バックログを進める。
        """
        if cw.cwpy.setting.is_logscrollable():
            self._in_scroll = False

        self._update_selection(is_runningevent=False)

        self.returnkey_event()

    def mclick_event(self):
        """
        ミドルクリックイベント。
        バックログを進める。
        """
        self.lclick_event()

    def rclick_event(self, flick=False):
        """
        右クリックイベント。
        バックログ終了。
        """
        if not flick and cw.cwpy.statusbar.clear_volumebar():
            return

        if not self.can_input():
            return

        if flick:
            selection = cw.cwpy.selection
        else:
            selection = self._update_selection(is_runningevent=False)

        if selection:
            cw.cwpy.has_inputevent = True
            selection.rclick_event()
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

        if not cw.cwpy.setting.is_logscrollable():
            self._wheel_event(y=1, key=True)

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
            self._wheel_event(y=y, key=True)
        elif y < 0:
            # バックログを遡る
            self._wheel_event(y=y, key=True)
        elif 0 < x:
            # バックログを進める
            self._wheel_event(y=x, key=True)
        elif x < 0:
            # バックログを遡る
            self._wheel_event(y=x, key=True)

    def wheel_event(self, y=0):
        """
        ホイールイベント。
        メッセージログを進めたり戻したりする。
        """
        self._wheel_event(y, key=False)

    def _wheel_event(self, y=0, key=False):
        if not self.can_input():
            return
        if cw.cwpy.has_inputevent:
            return

        if self.change_volume(-y):
            return

        if cw.cwpy.setting.is_logscrollable():
            if not key and 0 < y and self._scrollbar.scrpos_noscale == self._scrollbar.scrsize_noscale-cw.SIZE_AREA[1]:
                self.exit_backlog()
                return
            self._scrollbar.set_pos(self._scrollbar.get_pos()+self._scrollnum_noscale*y, lazy=True)

        else:
            if 0 < y:
                # ログを進める
                if len(self.backlog) <= self.index + 1:
                    # ログ終了
                    self.exit_backlog()
                    return
                cw.cwpy.play_sound("page")
                self.index += 1

                self.update_sprites()
            else:
                # ログを遡る
                if self.index <= 0:
                    cw.cwpy.play_sound("error")
                    return
                cw.cwpy.play_sound("page")
                self.index -= 1

                self.update_sprites()

    def _check_updatesettings(self):
        if self._upscr != cw.UP_SCR or self._messagelog_type != cw.cwpy.setting.messagelog_type:
            self._upscr = cw.UP_SCR
            self._messagelog_type = cw.cwpy.setting.messagelog_type
            self._update_posdata(init=False)

    def is_showing(self):
        self._check_updatesettings()
        if cw.cwpy.setting.is_logscrollable():
            return bool(self.backlog)
        else:
            return self.mwin is not None

    def _clear_sprites(self):
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_CURTAIN)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_BAR)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_PAGE)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_SCROLLBAR)
        cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE_LOG_CURTAIN)
        cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE_LOG)
        if self._sbarbar:
            cw.cwpy.sbargrp.add(self._sbarbar, layer=cw.sprite.statusbar.LAYER_MESSAGE)
            self._sbarbar = None

    def exit_backlog(self, playsound=True):
        if playsound:
            cw.cwpy.play_sound("click")
        # バックログ終了
        self._clear_sprites()
        self.mwin = None
        cw.cwpy._is_showingbacklog = False
        if cw.cwpy.lock_menucards:
            cw.cwpy.lock_menucards = self._lock_menucards

        # ステータスボタンを除き、ログ表示中はアニメーションを止める
        # (開始時間をずらして調節する)
        for sprite in cw.cwpy.cardgrp.sprites():
            if sprite.start_animation and not (cw.cwpy.selection and cw.cwpy.selection.is_statusctrl):
                elapse = pygame.time.get_ticks() - self.stw.start_ticks
                if 0 < elapse:
                    sprite.start_animation += elapse

        # 背景スプライト削除
        cw.cwpy.statusbar.change(not cw.cwpy.is_runningevent())
        cw.cwpy.add_lazydraw(clip=cw.s(pygame.Rect((0, 0), cw.SIZE_GAME)))

    def keydown_event(self, key):
        """その他のKEYDOWNイベント。"""
        if not EventHandler.keydown_event(self, key):
            return

        ctrldown = cw.cwpy.keyevent.keyin[pygame.K_LCTRL] or cw.cwpy.keyevent.keyin[pygame.K_RCTRL]
        if ctrldown and key == ord('C') and self.can_copytext():
            self.copy_text()
            return False

        if not cw.cwpy.setting.is_logscrollable():
            return True

        if key == pygame.locals.K_PAGEUP:
            self._scrollbar.set_pos(self._scrollbar.get_pos()-cw.SIZE_AREA[1]*80//100, lazy=True)
        elif key == pygame.locals.K_PAGEDOWN:
            self._scrollbar.set_pos(self._scrollbar.get_pos()+cw.SIZE_AREA[1]*80//100, lazy=True)
        elif key == pygame.locals.K_HOME:
            self._scrollbar.set_pos(0, lazy=True)
        elif key == pygame.locals.K_END:
            self._scrollbar.set_pos(self._scrollbar.scrsize_noscale-cw.SIZE_AREA[1], lazy=True)

        return False

    def can_copytext(self):
        return self.can_input()

    def copy_text(self):
        cw.cwpy.play_sound("equipment")
        s = cw.sprite.message.get_messagelogtext(self.backlog_all)
        cw.cwpy.frame.exec_func(cw.util.to_clipboard, s)

    def _get_maxpage(self):
        if not self.backlog:
            return 1

        if cw.cwpy.setting.is_logscrollable():
            bottom = self._scrollbar.scrsize_noscale
            btop = bottom - cw.SIZE_AREA[1]
            page = len(self.backlog)
            while 0 < page and btop <= self._pos_noscale[page-1]:
                page -= 1
            return page+1
        else:
            return len(self.backlog)

    def update_sprites(self, clearcache=False):
        if not cw.cwpy.is_showingbacklog():
            return
        if clearcache:
            self._update_posdata(init=False)
            return
        # スプライト削除
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG)
        cw.cwpy.backloggrp.remove_sprites_of_layer(cw.LAYER_LOG_BAR)
        cw.cwpy.sbargrp.remove_sprites_of_layer(cw.sprite.statusbar.LAYER_MESSAGE_LOG)
        if cw.cwpy.setting.is_logscrollable():
            self.mwin = None
            # 表示範囲
            top = self._scrollbar.scrpos_noscale
            bottom = top + cw.SIZE_AREA[1]
            f = bisect.bisect_right(self._bottom_noscale, top)
            topos = min(len(self.backlog)-1, bisect.bisect_left(self._pos_noscale, bottom))
            for i in range(f, topos+1):
                # まだ表示されていないスプライトがあれば追加
                if not self._mwins[i]:
                    self._mwins[i] = self.backlog[i].create_message()
                m = self._mwins[i]

                # 範囲内のスプライトを表示
                m.rect_noscale.top = self._pos_noscale[i]-top
                m.rect.top = cw.s(m.rect_noscale.top)
                cw.cwpy.backloggrp.add(m, layer=cw.LAYER_LOG)
                for j, sbar in enumerate(m.selections):
                    sbar.rect_noscale.height = sbar.size_noscale[1]
                    sbar.rect.height = cw.s(sbar.rect_noscale.height)
                    sbar.rect_noscale.top = m.rect_noscale.bottom + (j // m.columns * sbar.rect_noscale.height)
                    sbar.rect.top = cw.s(sbar.rect_noscale.top)
                    cw.cwpy.backloggrp.add(sbar, layer=cw.LAYER_LOG_BAR)
            # ページ表示の更新
            f2 = bisect.bisect_left(self._pos_noscale, top)
            if f2 != self.index:
                self.index = f2
                self._page.update_page(self.index+1, self._get_maxpage())
        else:
            # 次のログ
            self.mwin = self.backlog[self.index].create_message()
            self._page.update_page(self.index+1, self._get_maxpage())
        cw.cwpy.add_lazydraw(clip=cw.s(pygame.Rect((0, 0), cw.SIZE_GAME)))


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
            if not self.check_puressedbutton(event):
                continue

            if event.type == KEYDOWN:
                # ESCAPEキー
                if event.key == K_ESCAPE or event.key == K_BACKSPACE or event.key == K_BACKSLASH:
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
                # F8キー
                elif event.key == K_F8:
                    self.f8key_event()
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

            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    # 左ボタン押下イベント
                    self.ldown_event()

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
            elif event.type in (USEREVENT, cw.FORCE_USEREVENT) and hasattr(event, "func"):
                try:
                    self.executing_event(event)
                except cw.event.EventError as ex:
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

    def rclick_event(self, flick=False):
        """
        右クリックイベント。
        """
        if not flick and cw.cwpy.statusbar.clear_volumebar():
            return

        if not self.can_input():
            return

        if flick:
            selection = cw.cwpy.selection
        else:
            selection = self._update_selection(is_runningevent=False)

        if selection:
            cw.cwpy.has_inputevent = True
            selection.lclick_event()
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

        if cw.cwpy.setting.can_skipwait_with_wheel:
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
        if cw.cwpy.setting.expanddrawing != 1:
            raise cw.effectbooster.ScreenRescale()


def main():
    pass


if __name__ == "__main__":
    main()
