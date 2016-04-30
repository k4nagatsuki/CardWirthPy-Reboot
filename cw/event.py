#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import pygame.locals

import cw
from cw.character import Enemy


class EventInterface(object):
    def __init__(self):
        # イベントの選択メンバ(Character)
        self._selectedmember = None
        # イベントの使用中カード(CardHeader)
        self._inusecard = None
        # 現在起動中のイベントのリスト(Event)
        self._nowrunningevents = []
        # 現在起動中のパッケージイベントの辞書(EventEngine, keyはID)
        self.nowrunningpacks = {}
        # デバッガで表示する呼出履歴
        self.stackinfo = []
        # デバッガのイベントコントロールバー用変数
        self._paused = False
        self._stoped = False
        self._step = False
        self._targetstack = -2
        self.breakwait = False

        # イベント実行中に操作を受け付けるためのタイマ
        self.eventtimer = 1

        # カードイベントの実行中はTrue
        self.in_cardevent = False
        # カードの効果実行中はTrue
        self.in_cardeffectmotion = False
        # 使用時イベントの実行中はTrue
        self.in_inusecardevent = False

    def get_selectedmembername(self):
        """選択中メンバの名前を返す。"""
        try:
            return self._selectedmember.name
        except:
            return u"選択メンバ未定"

    def pop_event(self):
        event = self._nowrunningevents.pop()
        return event

    def remove_event(self, event):
        self._nowrunningevents.remove(event)

    def append_event(self, event):
        if cw.LIMIT_RECURSE <= self.get_currentstack():
            s = u"イベントの呼び出しが%s層を超えたので処理を中止します。スタートやパッケージのコールによってイベントが無限ループになっていないか確認してください。" % (cw.LIMIT_RECURSE)
            cw.cwpy.call_modaldlg("ERROR", text=s)
            raise cw.event.EffectBreakError()

        self._nowrunningevents.append(event)

    def replace_event(self, event, versionhint_base=None):
        """パッケージへのリンクによって
        実行中のイベントを置換する。
        """
        self._nowrunningevents[-1].copy_from(event, versionhint_base)

    def clear_events(self):
        self._nowrunningevents = []
        self.stackinfo = []
        self.refresh_stackinfo()

    def get_event(self):
        """現在起動中のEventを返す。"""
        if self._nowrunningevents:
            return self._nowrunningevents[0]
        else:
            return None

    def get_events(self):
        return self._nowrunningevents

    def get_currentstack(self):
        if not self._nowrunningevents:
            return 0
        return len(self._nowrunningevents) - 1 + len(self.get_event().nowrunningcontents)

    def get_trees(self):
        if self._nowrunningevents:
            return self._nowrunningevents[-1].trees
        else:
            return None

    def get_treekeys(self):
        if self._nowrunningevents:
            return self._nowrunningevents[-1].treekeys
        else:
            return []

    def get_nowrunningevent(self):
        if self._nowrunningevents:
            return self._nowrunningevents[-1]
        return None

    def get_packageid(self):
        """実行中のパッケージIDを返す。"""
        event = self.get_nowrunningevent()
        if event:
            return event.packageid
        else:
            return 0

    def clear(self):
        self.set_inusecard(None)
        self.in_inusecardevent = False
        self.clear_events()
        self.nowrunningpacks = {}
        self._stoped = False
        self.breakwait = False
        self._targetstack = -2
        self.refresh_tools()
        self.refresh_activeitem()

    def set_inusecard(self, header):
        """使用中カードを変更する。
        header: CardHeader or None
        """
        self._inusecard = header

    def set_selectedmember(self, ccard):
        """選択メンバを変更する。
        ccard: Character or None
        """
        self._selectedmember = ccard
        self.refresh_selectedmembername()

    def get_targetscope(self, scope, unreversed=True, cards=True):
        """
        コンテントの適用範囲を返す関数。
        すべてリストで返す。
        """
        mode = "unreversed" if unreversed else ""

        seq = []
        # 選択中メンバ
        if scope == "Selected":
            ccard = self.get_selectedmember()
            if ccard:
                seq.append(ccard)
        # ランダムメンバ
        elif scope == "Random":
            ccard = self.get_randommember()
            if ccard:
                seq.append(ccard)
        # パーティ全体
        elif scope == "Party":
            seq = cw.cwpy.get_pcards(mode)
        # 荷物袋
        elif scope == "Backpack":
            seq = [cw.cwpy.ydata.party.backpack]
        # パーティ全体と荷物袋
        elif scope == "PartyAndBackpack":
            seq = cw.cwpy.get_pcards(mode)
            seq.extend([cw.cwpy.ydata.party.backpack])
        # フィールド全体
        elif scope == "Field":
            # 同行キャストは対象外
            seq.extend(cw.cwpy.get_pcards(mode))
            seq.extend([cw.cwpy.ydata.party.backpack])
            seq.extend(cw.cwpy.get_ecards(mode))
        # 敵全体(1.30～)
        elif scope == "Enemy":
            seq = cw.cwpy.get_ecards(mode)
        # 同行NPC全体(1.30～)
        elif scope == "Npc":
            seq = cw.cwpy.get_fcards(mode)
        # フィールド全体(キャストのみ)
        elif scope == "FieldCasts":
            # 同行キャストは対象外
            seq.extend(cw.cwpy.get_pcards(mode))
            seq.extend(cw.cwpy.get_ecards(mode))
        else:
            raise ValueError(scope + " is invalid value.")

        return seq

    def get_targetmember(self, targetm, unreversed=True):
        """コンテントの適用メンバを返す関数。
        該当するCharacterインスタンスまたはCardHeaderインスタンスを返す。
        targetm: Random or Selected or Unselected or Inusecard or Party
        unreversed: Bool値。
        """
        mode = "unreversed" if unreversed else ""

        # ランダムメンバ
        if targetm == "Random":
            target = self.get_randommember()
        # 選択中メンバ
        elif targetm == "Selected":
            target = self.get_selectedmember()
        # 選択外メンバ
        elif targetm == "Unselected":
            target = self.get_unselectedmember()
        # 使用中カード
        elif targetm == "Inusecard":
            target = self.get_inusecard()
        # パーティ全体(※リストで返す)
        elif targetm == "Party":
            target = cw.cwpy.get_pcards(mode)
        # パーティ先頭
        elif targetm == "First":
            target = self.get_firstmember(mode)
        else:
            raise ValueError(targetm + " is invalid value.")

        return target

    def get_randommember(self):
        """ランダムでPlayerCardインスタンスを返す。
        行動可能状態のもの優先。
        """
        pcards = cw.cwpy.get_pcards("active")

        if not pcards:
            pcards = cw.cwpy.get_pcards("unreversed")

        return cw.cwpy.dice.choice(pcards)

    def has_selectedmember(self):
        """選択メンバが存在する場合はTrueを返す。"""
        return bool(self._selectedmember and\
           not (isinstance(self._selectedmember, cw.character.Character) and\
                self._selectedmember.is_vanished()))

    def get_selectedmember(self):
        """選択中のPlayerCardインスタンスを返す。
        存在しなかったらランダムで選択して返す。
        """
        if not self.has_selectedmember():
            self.set_selectedmember(self.get_randommember())

        card = self._selectedmember
        return card

    def clear_selectedmember(self):
        """選択中のメンバをクリアする。"""
        self._selectedmember = None
        self.refresh_selectedmembername()

    def get_unselectedmember(self):
        """選択外のPlayerCardインスタンスを返す。"""
        if not self.has_selectedmember():
            return self.get_randommember()

        selectedmember = self.get_selectedmember()

        pcards = cw.cwpy.get_pcards("active")
        pcards = [pcard for pcard in pcards if not pcard == selectedmember]

        if not pcards:
            pcards = cw.cwpy.get_pcards("unreversed")
            pcards = [pcard for pcard in pcards if not pcard == selectedmember]

        return cw.cwpy.dice.choice(pcards)

    def get_firstmember(self, mode):
        """先頭のPlayerCardインスタンスを返す。
        """
        pcards = cw.cwpy.get_pcards(mode)
        return pcards[0] if pcards else None

    def get_inusecard(self):
        """使用カード(CardHeaderインスタンス)を返す。"""
        card = self._inusecard
        return card

    #---------------------------------------------------------------------------
    # デバッガ更新用メソッド
    #---------------------------------------------------------------------------

    def refresh_tools(self):
        """デバッガのツールが使用可能かどうかを更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.refresh_tools
            cw.cwpy.frame.exec_func(func)

    def refresh_showpartytools(self):
        """デバッガのツールのうち、パーティ表示に関するものを更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.refresh_showpartytools
            cw.cwpy.frame.exec_func(func)

    def refresh_variablelist(self):
        """デバッガの状態変数のリストを更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.view_var.refresh_variablelist
            cw.cwpy.frame.exec_func(func)

    def refresh_variable(self, variable):
        """デバッガの状態変数の値を更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.view_var.refresh_variable
            cw.cwpy.frame.exec_func(func, variable)

    def refresh_selectedmembername(self):
        """デバッガの選択メンバツールバーの表示を更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.refresh_selectedmembername
            cw.cwpy.frame.exec_func(func)

    def refresh_areaname(self):
        """デバッガのエリアツールバーの表示を更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.refresh_areaname
            cw.cwpy.frame.exec_func(func)

    def refresh_activeitem(self):
        """デバッガのイベントツリーの実行中コンテントを更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            self._debugger_processing = True
            def func():
                dbg.view_tree.refresh_tree()
                dbg.view_tree.refresh_activeitem()
                self._debugger_processing = False
            cw.cwpy.frame.exec_func(func)

            while self._debugger_processing:
                pass

    def refresh_stackinfo(self):
        """デバッガの呼び出し履歴を更新する。"""
        dbg = cw.cwpy.frame.debugger
        if cw.cwpy.is_showingdebugger():
            func = dbg.refresh_stackinfo
            cw.cwpy.frame.exec_func(func)

    def wait(self):
        """デバッガのイベントコントロールバーで指定した分だけ、
        イベントの実行を待機する。
        """
        event = self.get_event()
        if not event:
            return

        cur_content = event.cur_content
        if not cur_content is None and cur_content.tag == "ContentsLine":
            cur_content = cur_content[event.line_index]

        if cw.cwpy.is_showingdebugger() and\
                 cw.cwpy.is_playingscenario() and 0 <= cw.cwpy.areaid:
            if not self._paused and cw.cwpy.sdata.breakpoints and cur_content.get_cwxpath() in cw.cwpy.sdata.breakpoints:
                # ブレークポイント到達
                self._paused = True
                def func():
                    cw.cwpy.frame.debugger.pause(True)
                cw.cwpy.frame.exec_func(func)

        if self._stoped:
            raise EffectBreakError()

        if cur_content.tag == "Talk":
            # メッセージの場合は表示後に待機するので
            # ここでは待ち合わせない
            return

        # 一部のイベント実行
        if pygame.event.peek(pygame.locals.USEREVENT) or (self.eventtimer % 1000 == 0 and pygame.event.peek()):
            cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
            cw.cwpy.input()
            cw.cwpy.eventhandler.run()
            self.eventtimer = 1
        else:
            self.eventtimer += 1

        if self._stoped:
            raise EffectBreakError()

        if cw.cwpy.is_showingdebugger() and\
                 cw.cwpy.is_playingscenario() and 0 <= cw.cwpy.areaid:
            cnt = 0

            if self._step:
                # ステップ実行中
                self._paused = True

            tick = pygame.time.get_ticks()
            tick += cw.cwpy.frame.debugger.sc_waittime.GetValue() * 100
            while cw.cwpy.is_running and cw.cwpy.is_showingdebugger() and\
                        pygame.time.get_ticks() < tick and not self._stoped:
                if not self.get_event().force_nextcontent is None:
                    break
                if cnt == 0:
                    self.refresh_tools()
                    self.refresh_activeitem()
                cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
                cw.cwpy.input()
                cw.cwpy.eventhandler.run()
                cw.cwpy.wait_frame(1, False)
                cnt += 1

            cnt = 0
            while cw.cwpy.is_running and cw.cwpy.is_showingdebugger() and\
                                            self._paused and not self._stoped:
                if -1 <= self._targetstack and self._targetstack < self.get_currentstack():
                    break
                if not self.get_event().force_nextcontent is None:
                    break
                if cnt == 0:
                    self.refresh_tools()
                    self.refresh_activeitem()
                cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
                cw.cwpy.input()
                cw.cwpy.eventhandler.run()
                cw.cwpy.wait_frame(1, False)
                cnt += 1

        if self._stoped:
            raise EffectBreakError()

    def set_curcontent(self, content, event=None):
        """次に実行するイベントコンテントを強制的に差し替える。
        イベント実行中でなければ、イベントを開始する。
        content: 次に実行するイベントコンテント。現在実行中のイベント
                 またはeventに属していなければならない。
        event: contentが属するイベント。
               現在イベントが実行中であれば無視される。
        """
        if self.get_nowrunningevent():
            if not event is None and not self.get_nowrunningevent() is event:
                return
            event = self.get_nowrunningevent()
            while event.parent:
                event = event.parent
            if content.cwxparent.tag == "ContentsLine":
                event.force_nextcontent = content.cwxparent
                event.force_nextcontent_index = content.cwxparent.index(content)
            else:
                event.force_nextcontent = content
                event.force_nextcontent_index = 0
            mwin = cw.cwpy.get_messagewindow()
            if mwin:
                mwin.result = 0
            else:
                event.skip_action = True
                self.refresh_activeitem()
        else:
            if content.cwxparent.tag == "ContentsLine":
                event.force_nextcontent = content.cwxparent
                event.force_nextcontent_index = content.cwxparent.index(content)
            else:
                event.force_nextcontent = content
                event.force_nextcontent_index = 0
            try:
                event.start()
            except cw.battle.BattleError, ex:
                if cw.cwpy.is_battlestatus():
                    cw.cwpy.battle.process_exception(ex)

    def set_stepexec(self, step):
        self._step = step

    def is_stepexec(self):
        return self._step

    def set_stoped(self, stoped):
        self._stoped = stoped

    def is_stoped(self):
        return self._stoped

    def is_paused(self):
        return self._paused

class EventEngine(object):
    def __init__(self, data):
        """引数のEventsElementからEventインスタンスのリストを生成。
        data: Area, BattleのElementTree
        """
        self.events = [Event(e) for e in data.getchildren()]

    def start(self, keynum=None, keycodes=[][:], isinsideevent=False, successevent=False):
        """発火条件に適合するイベント
        (リストのindexが若いほど優先順位が高い)を起動させる。
        keynum: 発火キーナンバー。
        keycodes: 発火キーコードのリスト。
        isinsideevent: 一連のイベント処理の内側にあるイベントであればTrue。
        Trueの場合はイベントフロー例外をキャッチせず伝播させる。
        """
        if keycodes:
            event = self.check_keycodes(keycodes, successevent=successevent)
        else:
            event = self.check_keynum(keynum)

        if event:
            event.clear()
            isinsideevent |= bool(cw.cwpy.event.get_event())
            if not isinsideevent:
                # メニューカードの選択を記憶
                last_selected = None
                if 0 <= cw.cwpy.index:
                    selection = cw.cwpy.list[cw.cwpy.index]
                    if isinstance(selection, cw.sprite.card.MenuCard):
                        last_selected = selection

                # メニューカードの反転表示を解除する
                if isinstance(cw.cwpy.selection, cw.sprite.card.MenuCard):
                    cw.cwpy.clear_selection()

            # イベント実行
            if isinsideevent:
                event.run()
            else:
                event.start()

            # メニューカードの選択を復元
            if not isinsideevent:
                cw.cwpy.list = cw.cwpy.get_mcards("visible")
                cw.cwpy.index = -1
                if last_selected and last_selected in cw.cwpy.list:
                    index = cw.cwpy.list.index(last_selected)
                    if 0 <= index:
                        cw.cwpy.index = index
            return True
        else:
            return False

    def check_keycodes(self, keycodes, successevent=False):
        kcset = set(keycodes)
        kcset.discard("")
        for event in self.events:
            igkeycodes = event.keycodes
            matching = event.keycode_matching
            # 互換動作: 1.30以前では"MatchingType=All"は普通のキーコード
            if matching == "And" and cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_AREA)):
                array = ["MatchingType=All"]
                array.extend(igkeycodes)
                igkeycodes = array
                matching = "Or"

            if matching == "And":
                match = True
                for keycode in igkeycodes:
                    if keycode and not self.check_keycode(keycode, kcset, successevent=successevent):
                        match = False
                        break
                if match:
                    return event
            else:
                for keycode in igkeycodes:
                    if keycode and self.check_keycode(keycode, kcset, successevent=successevent):
                        return event

        return None

    def check_keycode(self, keycode, keycodes, successevent=False):
        # 互換動作: 1.30以前では"！"で始まっていても普通のキーコード
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_AREA)):
            return keycode in keycodes
        else:
            if keycode.startswith(u"！"):
                if successevent:
                    return False
                return not keycode[1:] in keycodes
            else:
                return keycode in keycodes

    def check_keynum(self, keynum):
        for event in self.events:
            if keynum in event.keynums:
                return event
            if keynum < 0 and 4 in event.keynums:
                # ラウンド発火条件の場合は
                # 毎ラウンド発火もチェックする(1.50)
                return event

        return None

class EventError(Exception):
    pass

class AreaChangeError(EventError):
    pass

class StartBattleError(AreaChangeError):
    pass

class ScenarioEndError(EventError):
    pass

class ScenarioBadEndError(EventError):
    pass

class EffectBreakError(EventError):
    pass

class Event(object):
    def __init__(self, event):
        self.parent = None
        self.base = None
        self.inusecard = None
        # 次の子コンテンツインデックス。Contentの戻り値で設定される。
        self.index = 0
        # イベント実行中に発生したエラー
        self.error = None
        # コンテンツツリーの辞書(keyはスタートコンテントのname)
        self.trees = {}
        self.treekeys = []
        self.starttree = self.cur_content = None
        # ContentsLine実行中の時の実行位置
        self.line_index = 0
        # (パッケージ, 呼出前のcur_content, 呼出前のversionhint)
        # パッケージがNoneならスタートの呼び出し
        self.nowrunningcontents = []
        # 発火条件(数字)
        self.keynums = []
        # 発火キーコード(文字列)
        self.keycodes = []
        # キーコード発火条件("Or":どれか一つが存在する, "And":全て存在する)
        self.keycode_matching = "Or"
        # 終了時実行関数。F9用
        self.exit_func = None
        # パッケージイベントであればパッケージIDを設定
        self.packageid = 0
        # 実行後に互換性情報を書き戻す必要があれば設定
        self._versionhint_base = None

        if event is not None:
            if event.hasfind("Ignitions//Number"):
                s = event.gettext("Ignitions//Number", "")
                self.keynums = [int(i) for i in cw.util.decodetextlist(s) if i]

            if event.hasfind("Ignitions//KeyCodes"):
                s = event.gettext("Ignitions//KeyCodes", "")
                self.keycodes = [i for i in cw.util.decodetextlist(s) if i]
            # 1.50
            self.keycode_matching = event.getattr("Ignitions", "keyCodeMatchingType", "Or")

            for content in event.getfind("Contents"):
                if content.tag == "ContentsLine":
                    name = content[0].get("name", "")
                else:
                    name = content.get("name", "")

                if not name in self.trees:
                    self.trees[name] = content
                    self.treekeys.append(name)

                # 一番上にあるツリーをまず最初に実行するツリーに設定
                if self.starttree is None:
                    self.starttree = self.cur_content = content

        # 強制的に実行する次コンテント
        self.force_nextcontent = None
        self.force_nextcontent_index = -1
        self.skip_action = False

    def copy_from(self, event, versionhint_base=None):
        """実行中の処理をパッケージのイベントに差し替えるため、
        eventの情報をこのEventへコピーする。
        """
        # イベント終了時に元に戻すため、元のデータを保存
        if not self.base:
            self.base = Event(None)
            self.base._copy_from(self)
        self._copy_from(event)
        if not self._versionhint_base:
            self._versionhint_base = versionhint_base

    def _copy_from(self, event):
        self.trees = event.trees
        self.treekeys = event.treekeys
        self.starttree = event.starttree

    def start(self):
        try:
            showbuttons = not cw.cwpy.is_playingscenario() or\
                cw.cwpy.areaid in cw.AREAS_SP
            cw.cwpy.statusbar.change(showbuttons)

            cw.cwpy.event.stackinfo = []
            cw.cwpy.event.stackinfo.append(self)
            cw.cwpy.event.refresh_stackinfo()
            self.run()

        except EventError, err:
            self.error = err
            self.stop()

        self.end()

        if self.exit_func:
            cw.cwpy.exec_func(self.exit_func)

    def stop(self):
        """イベント強制中断処理。
        起動中のイベントを全て中断させる。"""
        # イベントの前に開いていたダイアログをクリア
        if not isinstance(self.error, EffectBreakError):
            cw.cwpy.pre_dialogs = []

        # 起動中のイベントは全てクリア
        for event in cw.cwpy.event.get_events():
            if event.base:
                event._copy_from(event.base)
                event.base = None
            cw.cwpy.event.remove_event(event)
            event.clear()

    def run(self, perf=False):
        """イベント実行。子コンテンツを順番に実行する。
        実行対象のイベントコンテント・イベントツリーは
        このイベントに属すものではない事がある。
        例えばパッケージのコール中は、実行の流れをrun()
        からは出さないまま、実行するイベントツリーのみを
        当該パッケージのものに置換する。
        これは不自然だが、際限の無い再帰を避けるために
        必要な処置である。
        """
        cw.cwpy.event.append_event(self)

        try:
            while True:
                self.index = 0
                nextcontents = self.get_nextcontents()

                while cw.cwpy.is_running() and nextcontents and not self.index < 0:
                    if len(nextcontents) <= self.index:
                        # デバッガによって処理フローが変わった場合
                        self.index = 0
                    self.cur_content = nextcontents[self.index]
                    cw.cwpy.event.wait()
                    self.action()
                    nextcontents = self.get_nextcontents()

                # コールコンテントを呼んでいた場合、呼んだところから再開
                if self.nowrunningcontents:
                    packevent, self.cur_content, self.line_index, versionhint = self.nowrunningcontents.pop()
                    cw.cwpy.event.stackinfo.pop()
                    cw.cwpy.event.refresh_stackinfo()
                    if packevent:
                        packevent.run_exit()
                        cw.cwpy.sdata.set_versionhint(cw.HINT_AREA, versionhint)
                else:
                    self.run_exit()
                    break
        finally:
            # イベント中断時は互換性情報のみ書き戻す
            if self.nowrunningcontents:
                packevent, self.cur_content, self.line_index, versionhint = self.nowrunningcontents[0]
                if packevent:
                    cw.cwpy.sdata.set_versionhint(cw.HINT_AREA, versionhint)

    def run_exit(self):
        if self.base:
            self._copy_from(self.base)
            self.base = None

        cw.cwpy.event.pop_event()
        self.clear()

    def end(self):
        """共通終了処理。"""
        if self.base:
            self._copy_from(self.base)
            self.clear()
            self.base = None
            if cw.cwpy.sdata and not self._versionhint_base is None:
                versionlevel, versionhint = self._versionhint_base
                cw.cwpy.sdata.set_versionhint(versionlevel, versionhint)
            self._versionhint_base = None

        if not (isinstance(self.error, AreaChangeError) or\
                isinstance(self.error, ScenarioBadEndError)) and\
                cw.cwpy.status <> "Title":
            if not cw.cwpy.is_gameover() and not cw.cwpy.event.is_stoped():
                cw.cwpy.show_party()
                cw.cwpy.disposition_pcards()
                cw.cwpy.background.reload_jpdcimage = False

        if not isinstance(self.error, AreaChangeError):
            # BUG: CardWirthでは全滅時は選択メンバがクリアされない
            if not (cw.cwpy.is_battlestatus() and cw.cwpy.is_gameover()):
                cw.cwpy.event.set_selectedmember(None)

        cw.cwpy.event.clear()

        # イベント中にカード移動が発生していた場合に備えてソート
        if cw.cwpy.ydata and cw.cwpy.ydata.party:
            cw.cwpy.ydata.party.sort_backpack()
            for header in cw.cwpy.ydata.party.backpack:
                # 書き込みを遅延しているカードは書き込み実施
                header.do_write()

        cw.cwpy.update_mcardlist()

        # 戦闘中か否か
        if cw.cwpy.is_battlestatus():
            # 敗北処理
            if cw.cwpy.is_gameover():
                # 互換動作: 1.15では戦闘中でもゲームオーバーになる。
                #           それより前のバージョンは不明だが1.15と同じように振る舞うと想定。
                if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.15", cw.cwpy.sdata.get_versionhint()):
                    raise cw.battle.BattleDefeatError()
                else:
                    # 1.20以降は一旦ゲームオーバーが取り消されて敗北イベントになる
                    cw.cwpy.set_gameoverstatus(False)
                    raise cw.battle.BattleDefeatError()
            # 別の戦闘を開始する場合は、戦闘終了
            elif isinstance(self.error, StartBattleError):
                raise cw.battle.BattleStartBattleError()
            # エリア移動が起こったら、戦闘終了
            elif isinstance(self.error, AreaChangeError):
                raise cw.battle.BattleAreaChangeError()

        # ゲームオーバ
        elif cw.cwpy.is_gameover() and cw.cwpy.is_playingscenario() and not cw.cwpy.sdata.in_f9:
            cw.cwpy.set_gameover()

    def clear(self):
        self.index = 0
        self.cur_content = self.starttree
        self.line_index = 0
        self.nowrunningcontents = []

    def action(self):
        if cw.cwpy.event.is_stoped():
            raise EffectBreakError()

        if self.skip_action:
            self.skip_action = False
            return
        """self.cur_contentを実行。"""
        if self.cur_content.tag == "ContentsLine":
            cur_content = self.cur_content[self.line_index]
        else:
            cur_content = self.cur_content

        content = cw.content.get_content(cur_content)
        # cw.util.t_start()
        if content:
            self.index = content.action()
        else:
            self.index = 0
        # cw.util.td_end(content.data.tag + content.data.get("type", ""))

        if (cur_content.tag == "Effect") or\
            (cur_content.tag == "Set" and cur_content.get("type") == "Coupon") or\
            (cur_content.tag == "Elapse" and cur_content.get("type") == "Time"):
            self.check_gameover()

        if cw.cwpy.event.is_stoped() or cw.cwpy.sdata.in_f9:
            raise EffectBreakError()

    def get_nextcontents(self):
        """self.cur_contentの子コンテントのリストを返す。"""
        if not self.force_nextcontent is None:
            content = self.force_nextcontent
            self.force_nextcontent = None
            self.line_index = self.force_nextcontent_index
            self.force_nextcontent_index = -1
            return [content]

        elif self.cur_content is None:
            self.line_index = 0
            return None

        else:
            isline = self.cur_content.tag == "ContentsLine"
            if isline:
                cur_content = self.cur_content[self.line_index]
                self.line_index += 1
            else:
                cur_content = self.cur_content
                self.line_index = 0

            if cur_content.nextelements is None:
                if isline and self.line_index < len(self.cur_content):
                    element = None
                else:
                    element = cur_content.find("Contents")
                cur_content.nextelements = []
                cur_content.needcheck = False

                if not element is None and len(element):
                    seq = []
                    for ee in element:
                        if ee.tag == "ContentsLine":
                            e = ee[0]
                        else:
                            e = ee

                        # フラグ判定コンテントの場合、
                        # 対応フラグがTrueの場合のみ実行対象に
                        if e.tag == "Check":
                            cur_content.needcheck = True
                            if cw.content.get_content(e).action() == 0:
                                seq.append(ee)
                        else:
                            seq.append(ee)
                        cur_content.nextelements.append(ee)
                    self.line_index = 0
                    return seq

                elif isline and self.line_index < len(self.cur_content):
                    e = self.cur_content[self.line_index]
                    cur_content.nextelements.append(e)
                    if e.tag == "Check":
                        cur_content.needcheck = True
                        if cw.content.get_content(e).action() == 0:
                            return [self.cur_content]
                    else:
                        return [self.cur_content]

                    return None

                else:
                    self.line_index = 0
                    return None

            elif cur_content.needcheck:
                if isline and self.line_index < len(self.cur_content):
                    e = self.cur_content[self.line_index]
                    if e.tag <> "Check" or cw.content.get_content(e).action() == 0:
                        return [self.cur_content]
                    else:
                        self.line_index = 0
                        return None
                else:
                    seq = []
                    for ee in cur_content.nextelements:
                        if ee.tag == "ContentsLine":
                            e = ee[0]
                        else:
                            e = ee

                        if e.tag <> "Check" or cw.content.get_content(e).action() == 0:
                            seq.append(ee)
                    self.line_index = 0
                    return seq
            else:
                if isline and self.line_index < len(self.cur_content):
                    return [self.cur_content]
                else:
                    self.line_index = 0
                    return cur_content.nextelements

    def check_gameover(self):
        """ゲームオーバーチェック。"""
        if cw.cwpy.is_playingscenario():
            flag = True

            for pcard in cw.cwpy.get_pcards():
                if not pcard.is_paralyze() and not pcard.is_unconscious():
                    flag = False
                    break

            if flag:
                cw.cwpy.set_gameoverstatus(flag, force=False)

class CardEvent(Event):
    def __init__(self, event, inusecard, user, targets):
        Event.__init__(self, event)
        self.inusecard = inusecard
        self.user = user
        self.targets = targets
        self.waited = False

    def start(self):
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, self.inusecard.versionhint)

        cw.cwpy.event.set_inusecard(self.inusecard)

        data = self.inusecard.carddata
        if self.inusecard.type == "SkillCard":
            level = data.getint("Property/Level", 0)
        else:
            level = 0

        # 沈黙時のスペルカード発動キャンセル・魔法無効判定・カード不発判定
        spellcard = data.getbool("Property/EffectType", "spell", False)
        magiccard = data.gettext("Property/EffectType", "None") in ("Magic", "PhysicalMagic")
        flag = bool(spellcard and self.user.is_silence())
        flag |= bool(magiccard and self.user.is_antimagic() and data.tag <> "BeastCard")
        flag |= bool(0 < level and not self.user.decide_misfire(level))

        if flag:
            cw.cwpy.play_sound("confuse", True)
            battlespeed = cw.cwpy.is_battlestatus()
            cw.animation.animate_sprite(self.user, "axialvibe", battlespeed=battlespeed)
            cw.animation.animate_sprite(self.user, "hide", battlespeed=battlespeed)
            cw.cwpy.clear_inusecardimg(self.user)
            cw.animation.animate_sprite(self.user, "deal", battlespeed=battlespeed)
            self.end()
        else:
            # 使用可能なのでイベント実行
            cw.cwpy.event.set_selectedmember(self.user)
            Event.start(self)

    def run_exit(self):
        """イベント実行の最後に行う終了処理。
        カード効果発動・効果中断コンテントに対応。
        """
        # イベント終了
        cw.cwpy.event.in_cardevent = True
        try:
            Event.run_exit(self)

            if cw.cwpy.is_playingscenario():
                cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

            # エリアのキーコードイベント
            if isinstance(self.user, cw.sprite.card.PlayerCard):
                self.run_areaevent()

            # カード効果
            cw.cwpy.event.in_cardeffectmotion = True
            try:
                self.effect_cardmotion()
            finally:
                cw.cwpy.event.in_cardeffectmotion = False

        finally:
            cw.cwpy.event.in_cardevent = False

    def end(self):
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

        # カードの使用回数減らす(シナリオ終了後に回数減らさないよう条件付き)
        if not isinstance(self.error, ScenarioEndError):
            self.inusecard.set_uselimit(-1)

        # effect_cardmotionでウェイトをとってない場合はここでとる
        if not self.waited:
            waitrate = (cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1) * 2
            cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

        # InuseCardImage削除
        cw.cwpy.clear_inusecardimg(self.user)

        # 効果中断等でターゲット色反転が解除されない場合があるため
        for target in self.targets:
            target.clear_cardtarget()

        # ズームアウトアニメーション
        if self.user.zoomimgs:
            cw.animation.animate_sprite(self.user, "zoomout")

        # 互換性マークを削除
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

        # 通常イベントの終了処理
        Event.end(self)

        # 特殊エリア解除・カード選択ダイアログを開く
        cw.cwpy.clear_specialarea()

    def run_areaevent(self):
        keycodes = self.inusecard.get_keycodes()
        cw.cwpy.event.set_selectedmember(self.user)
        in_inusecardevent = cw.cwpy.event.in_inusecardevent
        cw.cwpy.event.in_inusecardevent = False
        cw.cwpy.sdata.events.start(keycodes=keycodes, isinsideevent=True)
        cw.cwpy.event.in_inusecardevent = in_inusecardevent

    def run_enemyevent(self, target, can_unconscious):
        if isinstance(target, Enemy) and (can_unconscious or not (target.is_unconscious() or target.is_vanished())):
            keycodes = self.inusecard.get_keycodes()
            cw.cwpy.event.set_selectedmember(self.user)
            in_inusecardevent = cw.cwpy.event.in_inusecardevent
            cw.cwpy.event.in_inusecardevent = False
            target.events.start(keycodes=keycodes, isinsideevent=True)
            cw.cwpy.event.in_inusecardevent = in_inusecardevent

    def run_deadevent(self, target):
        if cw.cwpy.msgs["runaway_keycode"] in self.inusecard.get_keycodes(with_name=False):
            # キーコード「逃走」付きのカードは死亡イベントを発生させない
            # (ただしカード名キーコードは除く)
            return False
        if isinstance(target, Enemy) and ((target.is_dead() and not target.status == "hidden") or target.is_vanished()):
            cw.cwpy.event.set_selectedmember(self.user)
            in_inusecardevent = cw.cwpy.event.in_inusecardevent
            cw.cwpy.event.in_inusecardevent = False
            r = target.events.start(1, isinsideevent=True)
            cw.cwpy.event.in_inusecardevent = in_inusecardevent
            return r
        else:
            return False

    def run_menucardevent(self, target):
        """
        MenuCardインスタンスのキーコードイベントを発動させる。
        """
        # MenuCardのキーコードイベント発動。発動しなかったら、無効音。
        keycodes = self.inusecard.get_keycodes()
        event = target.events.check_keycodes(keycodes)
        if event:
            lock = cw.cwpy.lock_menucards
            cw.cwpy.lock_menucards = False
            in_inusecardevent = cw.cwpy.event.in_inusecardevent
            cw.cwpy.event.in_inusecardevent = False
            target.events.start(keycodes=keycodes)
            cw.cwpy.event.in_inusecardevent = in_inusecardevent
            cw.cwpy.lock_menucards = lock
            self.error = event.error
        else:
            cw.cwpy.play_sound("ineffective", True)

    def run_successevent(self, target, successflag, can_unconscious):
        if isinstance(target, Enemy):
            keycodes = []
            for keycode in self.inusecard.get_keycodes():
                if keycode:
                    if successflag:
                        keycodes.append(keycode + u"○")
                    else:
                        keycodes.append(keycode + u"×")

            cw.cwpy.event.set_selectedmember(self.user)
            in_inusecardevent = cw.cwpy.event.in_inusecardevent
            cw.cwpy.event.in_inusecardevent = False
            target.events.start(keycodes=keycodes, isinsideevent=True, successevent=True)
            cw.cwpy.event.in_inusecardevent = in_inusecardevent

    def effect_cardmotion(self):
        """カード効果発動。イベント実行の最後に行う。"""
        # ターゲットが存在しない場合は処理中断
        if not self.targets:
            return

        # 各種データ取得
        data = self.inusecard.carddata
        d = {}.copy()
        d["user"] = self.user
        d["inusecard"] = self.inusecard
        d["successrate"] = data.getint("Property/SuccessRate", 0)
        d["effecttype"] = data.gettext("Property/EffectType", "Physic")
        d["resisttype"] = data.gettext("Property/ResistType", "Avoid")
        d["soundpath"] = data.gettext("Property/SoundPath2", "")
        d["volume"] = data.getint("Property/SoundPath2", "volume", 100)
        d["loopcount"] = data.getint("Property/SoundPath2", "loopcount", 1)
        d["channel"] = data.getint("Property/SoundPath2", "channel", 0)
        d["fadein"] = data.getint("Property/SoundPath2", "fadein", 0)
        d["visualeffect"] = data.gettext("Property/VisualEffect", "None")
        d["target"] = data.gettext("Property/Target", "None")

        # Effectインスタンス作成
        motions = data.getfind("Motions").getchildren()
        eff = cw.effectmotion.Effect(motions, d, battlespeed=cw.cwpy.is_battlestatus())

        # ターゲット色反転＆ウェイト
        skipped = False
        if len(self.targets) == 1:
            if eff.check_enabledtarget(self.targets[0], False):
                self.targets[0].set_cardtarget()
                cw.cwpy.draw()
                waitrate = (cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1) * 2
                skipped = cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                targets = self.targets
            else:
                targets = []
        else:
            path = data.gettext("Property/SoundPath", "")
            volume = data.getint("Property/SoundPath", "volume", 100)
            loopcount = data.getint("Property/SoundPath", "loopcount", 1)
            channel = data.getint("Property/SoundPath", "channel", 0)
            fade = data.getint("Property/SoundPath", "fadein", 0)
            targets = []

            for target in self.targets:
                if eff.check_enabledtarget(target, False):
                    target.set_cardtarget()
                    cw.cwpy.draw()
                    cw.cwpy.play_sound_with(path, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)
                    waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1
                    skipped = cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                    targets.append(target)

        if not skipped and cw.cwpy.setting.wait_usecard:
            waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())
            cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

        self.waited = True

        # 対象メンバに効果モーションを適用
        for target in targets:
            if not isinstance(target, cw.sprite.card.MenuCard) and\
                    target.is_unconscious() and\
                    not eff.has_motions(cw.effectmotion.CAN_UNCONSCIOUS):
                # 意識不明者に有効な効果が含まれていない場合は
                # イベント発火判定を含め何もしない
                continue
            if target.status == "hidden" and\
                    not isinstance(target, cw.sprite.card.FriendCard):
                # 非表示の場合は何もしない
                continue
            if not isinstance(target, cw.sprite.card.MenuCard) and\
                    target.is_vanished():
                continue

            unconscious_flag = eff.has_motions(cw.effectmotion.CAN_UNCONSCIOUS) and\
                not isinstance(target, cw.sprite.card.MenuCard) and\
                target.is_unconscious()
            paralyze_flag = not isinstance(target, cw.sprite.card.MenuCard) and\
                target.is_paralyze()

            if isinstance(target, Enemy) and (not target.is_unconscious() or unconscious_flag):
                self.run_enemyevent(target, unconscious_flag)
                target.clear_cardtarget()

                success = eff.apply(target)

                # 最初から意識不明・麻痺なら死亡イベント発生なし
                if not unconscious_flag and not paralyze_flag:
                    deadevent = self.run_deadevent(target)
                else:
                    deadevent = False

                # 成功・失敗キーコードイベントより死亡イベントを優先
                if not deadevent:
                    if success:
                        self.run_successevent(target, True, unconscious_flag)
                    else:
                        self.run_successevent(target, False, unconscious_flag)
                        cw.cwpy.draw()

            else:
                target.clear_cardtarget()

                if isinstance(target, cw.sprite.card.MenuCard):
                    cw.cwpy.play_sound_with(eff.soundpath)
                    eff.animate(target)
                    self.run_menucardevent(target)
                elif d["target"] <> "None":
                    eff.apply(target)
                cw.cwpy.draw()

        if not isinstance(self.error, AreaChangeError):
            # 通常のカード効果は全滅時でも選択メンバをクリアする
            cw.cwpy.event.set_selectedmember(None)
        self.check_gameover()

def main():
    pass

if __name__ == "__main__":
    main()
