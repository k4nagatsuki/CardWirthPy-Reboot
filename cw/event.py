#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import pygame
import pygame.locals

import cw

from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, Union


class EventInterface(object):
    def __init__(self) -> None:
        # イベントの選択メンバ
        self._selectedmember: Optional[cw.character.Character] = None
        # イベントの使用中カード
        self._inusecard: Optional[cw.header.CardHeader] = None
        # イベントの選択カード(Wsn.3)
        self._selectedcard: Optional[cw.header.CardHeader] = None
        # 現在起動中のイベントのリスト(Event)
        self._nowrunningevents: List[Event] = []
        # 現在起動中のパッケージイベントの辞書(keyはパッケージID)
        self.nowrunningpacks: Dict[int, Tuple[cw.data.CWPyElement, Tuple[str, str, bool, bool, bool]]] = {}
        # デバッガで表示する呼出履歴
        self.stackinfo: List[Optional[Union[Event, Tuple[Event, cw.data.CWPyElement, int]]]] = [None] * 16
        self.stackinfo_len = 0
        # デバッガのイベントコントロールバー用変数
        self.paused = False
        self.stoped = False
        self._step = False
        self._targetstack = -2
        self.breakwait = False
        self.waittime = 0

        # イベント実行中に操作を受け付けるためのタイマ
        self.eventtimer = 1

        # 実行中の効果イベント
        self.effectevent: Optional[Targeting] = None
        # カードの効果実行中はTrue
        self.in_cardeffectmotion = False
        # 使用時イベントの実行中はTrue
        self.in_inusecardevent = False
        # 終了時実行関数。F9用
        self.exit_func: Optional[Callable[[], None]] = None

        # イベントを実行した結果、状況に変化が生じたか
        # カード消費判定に使用される
        self.is_changestate = False

    def get_selectedmembername(self) -> str:
        """選択中メンバの名前を返す。"""
        return self._selectedmember.name if self._selectedmember else "選択メンバ未定"

    def get_selectedcardname(self) -> str:
        """選択カードの名前を返す(Wsn.3)。"""
        return self._selectedcard.name if self._selectedcard else "選択カード未定"

    def get_selectedcardtype(self) -> Optional[str]:
        """選択カードのタイプを返す(Wsn.3)。"""
        return self._selectedcard.type if self._selectedcard else None

    def pop_event(self) -> "Event":
        event = self._nowrunningevents.pop()
        return event

    def remove_event(self, event: "Event") -> None:
        self._nowrunningevents.remove(event)

    def append_event(self, event: "Event") -> None:
        if cw.LIMIT_RECURSE <= self.get_currentstack():
            s = "イベントの呼び出しが%s層を超えたので処理を中止します。スタートやパッケージのコールによってイベントが無限ループになっていないか確認してください。" % (cw.LIMIT_RECURSE)
            cw.cwpy.call_modaldlg("ERROR", text=s)
            raise cw.event.EffectBreakError()

        self._nowrunningevents.append(event)

    def replace_event(self, event: "Event",
                      versionhint_base: Optional[Tuple[int,
                                                       Optional[Tuple[str, str, bool, bool, bool]]]] = None) -> None:
        """パッケージへのリンクによって
        実行中のイベントを置換する。
        """
        self._nowrunningevents[-1].copy_from(event, versionhint_base)

    def clear_events(self) -> None:
        self._nowrunningevents = []
        self.clear_stackinfo()

    def get_event(self) -> Optional["Event"]:
        """現在起動中のEventを返す。"""
        if self._nowrunningevents:
            return self._nowrunningevents[0]
        else:
            return None

    def get_effectevent(self) -> Optional["Targeting"]:
        """カードなどの効果適用イベントが実行中であれば返す。"""
        return self.effectevent

    def get_events(self) -> List["Event"]:
        return self._nowrunningevents

    def get_currentstack(self) -> int:
        if not self._nowrunningevents:
            return 0
        event = self.get_event()
        assert event
        return len(self._nowrunningevents) - 1 + len(event.nowrunningcontents)

    def get_trees(self) -> Optional[Dict[str, cw.data.CWPyElement]]:
        if self._nowrunningevents:
            return self._nowrunningevents[-1].trees
        else:
            return None

    def get_treekeys(self) -> List[str]:
        if self._nowrunningevents:
            return self._nowrunningevents[-1].treekeys
        else:
            return []

    def get_nowrunningevent(self) -> Optional["Event"]:
        if self._nowrunningevents:
            return self._nowrunningevents[-1]
        return None

    def get_packageid(self) -> int:
        """実行中のパッケージIDを返す。"""
        event = self.get_nowrunningevent()
        if event:
            return event.packageid
        else:
            return 0

    def clear(self) -> None:
        self.set_inusecard(None)
        self.in_inusecardevent = False
        self.effectevent = None
        self.clear_events()
        self.nowrunningpacks = {}
        self.stoped = False
        self.breakwait = False
        self._targetstack = -2
        self.refresh_tools()
        self.refresh_activeitem()
        self.exit_func = None

    def set_inusecard(self, header: Optional["cw.header.CardHeader"]) -> None:
        """使用中カードを変更する。
        """
        self._inusecard = header
        self.set_selectedcard(header)

    def set_selectedmember(self, ccard: Optional["cw.character.Character"]) -> None:
        """選択メンバを変更する。
        """
        if self._selectedmember != ccard:
            self._selectedmember = ccard
            self.refresh_selectedmembername()

    def set_selectedcard(self, header: Optional["cw.header.CardHeader"]) -> None:
        """選択カードを変更する(Wsn.3)。"""
        if self._selectedcard != header:
            self._selectedcard = header
            self.refresh_selectedcardname()

    def get_targetscope(self, scope: str, unreversed: bool = True, cards: bool = True,
                        coupon: str = "") -> List[Union["cw.character.Character", List["cw.header.CardHeader"]]]:
        """
        コンテントの適用範囲を返す関数。
        すべてリストで返す。
        """
        mode = "unreversed" if unreversed else ""

        seq: List[Union[cw.character.Character, List[cw.header.CardHeader]]] = []
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
            seq.extend(cw.cwpy.get_pcards(mode))
        # 荷物袋
        elif scope == "Backpack":
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            seq.append(cw.cwpy.ydata.party.backpack)
        # パーティ全体と荷物袋
        elif scope == "PartyAndBackpack":
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            seq.extend(cw.cwpy.get_pcards(mode))
            seq.extend([cw.cwpy.ydata.party.backpack])
        # フィールド全体
        elif scope == "Field":
            # 同行キャストは対象外
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            seq.extend(cw.cwpy.get_pcards(mode))
            seq.extend([cw.cwpy.ydata.party.backpack])
            seq.extend(cw.cwpy.get_ecards(mode))
        # 敵全体(1.30～)
        elif scope == "Enemy":
            seq.extend(cw.cwpy.get_ecards(mode))
        # 同行NPC全体(1.30～)
        elif scope == "Npc":
            seq.extend(cw.cwpy.get_fcards(mode))
        # フィールド全体(キャストのみ)
        elif scope == "FieldCasts":
            # 同行キャストは対象外
            seq.extend(cw.cwpy.get_pcards(mode))
            seq.extend(cw.cwpy.get_ecards(mode))
        # 称号所有者(Wsn.3)
        elif scope == "CouponHolder":
            if coupon:
                for ccard in itertools.chain(cw.cwpy.get_pcards("unreversed"), cw.cwpy.get_ecards("unreversed")):
                    if ccard.has_coupon(coupon):
                        seq.append(ccard)
        else:
            raise ValueError(scope + " is invalid value.")

        return seq

    def get_targetmember(self, targetm: str, unreversed: bool = True,
                         coupon: str = "") -> Union[Optional["cw.character.Character"],
                                                    List["cw.character.Character"],
                                                    Optional["cw.header.CardHeader"]]:
        """コンテントの適用メンバを返す関数。
        該当するCharacterインスタンスまたはCardHeaderインスタンスを返す。
        targetm: Random or Selected or Unselected or Inusecard or Party
        unreversed: Bool値。
        """
        mode = "unreversed" if unreversed else ""
        target: Union[Optional[cw.character.Character], List[cw.character.Character], Optional[cw.header.CardHeader]]

        # ランダムメンバ
        if targetm == "Random":
            target = self.get_randommember()
        # 選択中メンバ
        elif targetm == "Selected":
            target = self.get_selectedmember()
        # 選択外メンバ
        elif targetm == "Unselected":
            target = self.get_unselectedmember()
        # 選択カード(Wsn.2以前は使用中カード)
        elif targetm == "Selectedcard":
            target = self.get_selectedcard()
        # パーティ全体(※リストで返す)
        elif targetm == "Party":
            target = []
            target.extend(cw.cwpy.get_pcards(mode))
        # パーティ先頭
        elif targetm == "First":
            target = self.get_firstmember(mode)
        # 称号所有者
        elif targetm == "CouponHolder":
            if coupon:
                seq = []
                for ccard in itertools.chain(cw.cwpy.get_pcards("unreversed"), cw.cwpy.get_ecards("unreversed")):
                    if ccard.has_coupon(coupon):
                        seq.append(ccard)
                target = seq
            else:
                target = []
        else:
            raise ValueError(targetm + " is invalid value.")

        return target

    def get_randommember(self) -> "cw.character.Character":
        """ランダムでPlayerCardインスタンスを返す。
        行動可能状態のもの優先。
        """
        pcards = cw.cwpy.get_pcards("active")

        if not pcards:
            pcards = cw.cwpy.get_pcards("unreversed")

        return cw.cwpy.dice.choice_exists(pcards)

    def has_selectedmember(self) -> bool:
        """選択メンバが存在する場合はTrueを返す。"""
        return bool(self._selectedmember and not (isinstance(self._selectedmember, cw.character.Character) and
                                                  self._selectedmember.is_vanished()))

    def get_selectedmember(self) -> Optional["cw.character.Character"]:
        """選択中のPlayerCardインスタンスを返す。
        存在しなかったらランダムで選択して返す。
        """
        if not self.has_selectedmember():
            self.set_selectedmember(self.get_randommember())

        card = self._selectedmember
        return card

    def clear_selectedmember(self) -> None:
        """選択中のメンバをクリアする。"""
        if self._selectedmember is not None:
            self._selectedmember = None
            self.refresh_selectedmembername()

    def get_unselectedmember(self) -> "cw.character.Character":
        """選択外のPlayerCardインスタンスを返す。"""
        if not self.has_selectedmember():
            return self.get_randommember()

        selectedmember = self.get_selectedmember()

        pcards = cw.cwpy.get_pcards("active")
        pcards = [pcard for pcard in pcards if not pcard == selectedmember]

        if not pcards:
            pcards = cw.cwpy.get_pcards("unreversed")
            pcards = [pcard for pcard in pcards if not pcard == selectedmember]

        return cw.cwpy.dice.choice_exists(pcards)

    def get_firstmember(self, mode: str) -> Optional["cw.character.Character"]:
        """先頭のPlayerCardインスタンスを返す。
        """
        pcards = cw.cwpy.get_pcards(mode)
        return pcards[0] if pcards else None

    def get_inusecard(self) -> Optional["cw.header.CardHeader"]:
        """使用カード(CardHeaderインスタンス)を返す。"""
        card = self._inusecard
        return card

    def get_selectedcard(self) -> Optional["cw.header.CardHeader"]:
        """選択カード(CardHeaderインスタンス)を返す(Wsn.3)。"""
        card = self._selectedcard
        return card

    def clear_selectedcard(self) -> None:
        """選択中のメンバをクリアする。"""
        if self._selectedcard != self._inusecard:
            self._selectedcard = self._inusecard
            self.refresh_selectedcardname()

    # --------------------------------------------------------------------------
    # デバッガ更新用メソッド
    # --------------------------------------------------------------------------

    def refresh_tools(self) -> None:
        """デバッガのツールが使用可能かどうかを更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.refresh_tools
            cw.cwpy.frame.exec_func(func)

    def refresh_showpartytools(self) -> None:
        """デバッガのツールのうち、パーティ表示に関するものを更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.refresh_showpartytools
            cw.cwpy.frame.exec_func(func)

    def refresh_variablelist(self) -> None:
        """デバッガの状態変数のリストを更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.view_var.refresh_variablelist
            cw.cwpy.frame.exec_func(func)

    def refresh_variable(self, variable: Union[cw.data.Flag, cw.data.Step, cw.data.Variant]) -> None:
        """デバッガの状態変数の値を更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.view_var.refresh_variable
            cw.cwpy.frame.exec_func(func, variable)

    def refresh_selectedmembername(self) -> None:
        """デバッガの選択メンバツールバーの表示を更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.refresh_selectedmembername
            cw.cwpy.frame.exec_func(func)

    def refresh_selectedcardname(self) -> None:
        """デバッガの選択カードツールバーの表示を更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.refresh_selectedcardname
            cw.cwpy.frame.exec_func(func)

    def refresh_areaname(self) -> None:
        """デバッガのエリアツールバーの表示を更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            func = dbg.refresh_areaname
            cw.cwpy.frame.exec_func(func)

    def refresh_activeitem(self) -> None:
        """デバッガのイベントツリーの実行中コンテントを更新する。"""
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            def func() -> None:
                assert dbg
                dbg.view_tree.refresh_tree()
                dbg.view_tree.refresh_activeitem()
            cw.cwpy.frame.exec_func(func)

    def append_stackinfo(self, item: Union["Event", Tuple["Event", cw.data.CWPyElement, int]]) -> None:
        """呼び出し履歴を追加する。"""
        if len(self.stackinfo) <= self.stackinfo_len:
            self.stackinfo.extend([None] * len(self.stackinfo))
        self.stackinfo[self.stackinfo_len] = item
        self.stackinfo_len += 1
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            dbg.append_stackinfo_cwpy(item)

    def pop_stackinfo(self) -> None:
        """呼び出し履歴の末尾を除去する。"""
        self.stackinfo_len -= 1
        self.stackinfo[self.stackinfo_len] = None
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            dbg.pop_stackinfo_cwpy()

    def replace_stackinfo(self, index: int, item: Union["Event", Tuple["Event", cw.data.CWPyElement, int]]) -> None:
        """呼び出し履歴の途中または末尾を置換する。"""
        assert isinstance(cw.cwpy.event.stackinfo[self.stackinfo_len+index], cw.event.Event)
        self.stackinfo[self.stackinfo_len+index] = item
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            dbg.replace_stackinfo_cwpy(index, item)

    def clear_stackinfo(self) -> None:
        """呼び出し履歴をクリアする。"""
        self.stackinfo = [None] * 16
        self.stackinfo_len = 0
        dbg = cw.cwpy.is_showingdebugger()
        if dbg:
            dbg.clear_stackinfo_cwpy()

    def wait(self) -> None:
        """デバッガのイベントコントロールバーで指定した分だけ、
        イベントの実行を待機する。
        """
        event = self.get_event()
        if not event:
            return

        cur_content = event.cur_content
        if cur_content is not None and cur_content.tag == "ContentsLine":
            cur_content = cur_content[event.line_index]
        assert cur_content is not None

        if cw.cwpy.is_showingdebugger() and (cw.cwpy.is_playingscenario() or cw.OPTIONS.getbool("debug_skin")) and\
                0 <= cw.cwpy.areaid:
            if not self.paused and cw.cwpy.sdata.breakpoints and cur_content.get_cwxpath() in cw.cwpy.sdata.breakpoints:
                # ブレークポイント到達
                self.paused = True

                def func() -> None:
                    debugger = cw.cwpy.is_showingdebugger()
                    if debugger:
                        debugger.pause(True)
                cw.cwpy.frame.exec_func(func)

        if self.stoped:
            raise EffectBreakError()

        if cur_content.tag == "Talk":
            # メッセージの場合は表示後に待機するので
            # ここでは待ち合わせない
            return

        # 一部のイベント実行
        if pygame.event.peek((pygame.locals.USEREVENT, cw.FORCE_USEREVENT)) or (self.eventtimer % 1000 == 0 and
                                                                                pygame.event.peek()):
            cw.cwpy.update_groups((cw.cwpy.sbargrp,))
            cw.cwpy.input()
            cw.cwpy.get_eventhandler().run()
            self.eventtimer = 1
        else:
            self.eventtimer += 1

        if self.stoped:
            raise EffectBreakError()

        if cw.cwpy.is_showingdebugger() and\
                (cw.cwpy.is_playingscenario() or cw.OPTIONS.getbool("debug_skin")) and 0 <= cw.cwpy.areaid:
            cnt = 0

            if self._step:
                # ステップ実行中
                self.paused = True

            waittime = self.waittime
            if waittime:
                tick = pygame.time.get_ticks()
                stw = cw.sprite.base.StopTheWorld(tick, waittime * 100)
                while cw.cwpy.is_running and cw.cwpy.is_showingdebugger() and\
                        stw.is_waiting() and not self.stoped:
                    event = self.get_event()
                    assert event
                    if event.force_nextcontent is not None:
                        break
                    if cnt == 0:
                        self.refresh_tools()
                        self.refresh_activeitem()
                    cw.cwpy.update_groups((cw.cwpy.sbargrp,))
                    cw.cwpy.input()
                    cw.cwpy.get_eventhandler().run()
                    cw.cwpy.wait_frame(1, False, stoptheworld=stw)
                    cnt += 1

            cnt = 0
            while cw.cwpy.is_running and cw.cwpy.is_showingdebugger() and\
                    self.paused and not self.stoped:
                if -1 <= self._targetstack and self._targetstack < self.get_currentstack():
                    break
                event = self.get_event()
                assert event
                if event.force_nextcontent is not None:
                    break
                if cnt == 0:
                    self.refresh_tools()
                    self.refresh_activeitem()
                cw.cwpy.update_groups((cw.cwpy.sbargrp,))
                cw.cwpy.input()
                cw.cwpy.get_eventhandler().run()
                cw.cwpy.wait_frame(1, False)
                cnt += 1

        if self.stoped:
            raise EffectBreakError()

    def set_curcontent(self, content: cw.data.CWPyElement, event: Optional["Event"] = None) -> None:
        """次に実行するイベントコンテントを強制的に差し替える。
        イベント実行中でなければ、イベントを開始する。
        content: 次に実行するイベントコンテント。現在実行中のイベント
                 またはeventに属していなければならない。
        event: contentが属するイベント。
               現在イベントが実行中であれば無視される。
        """
        if self.get_nowrunningevent():
            if event is not None and not self.get_nowrunningevent() is event:
                return
            event = self.get_nowrunningevent()
            assert event
            while event.parent:
                event = event.parent
            assert content.cwxparent is not None
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
            assert event
            assert content.cwxparent is not None
            if content.cwxparent.tag == "ContentsLine":
                event.force_nextcontent = content.cwxparent
                event.force_nextcontent_index = content.cwxparent.index(content)
            else:
                event.force_nextcontent = content
                event.force_nextcontent_index = 0
            try:
                event.start()
            except cw.battle.BattleError as ex:
                if cw.cwpy.is_battlestatus():
                    assert cw.cwpy.battle
                    cw.cwpy.battle.process_exception(ex)

    def set_stepexec(self, step: bool) -> None:
        self._step = step

    def is_stepexec(self) -> bool:
        return self._step

    def set_stoped(self, stoped: bool) -> None:
        self.stoped = stoped

    def is_stoped(self) -> bool:
        return self.stoped

    def is_paused(self) -> bool:
        return self.paused


class EventEngine(object):
    def __init__(self, data: Iterable[cw.data.CWPyElement]) -> None:
        """引数のEventsElementからEventインスタンスのリストを生成。
        data: Area, BattleのElementTree
        """
        self.events = [Event(e) for e in data]

    def start(self, keynum: Optional[int] = None, keycodes: Optional[Iterable[str]] = None, isinsideevent: bool = False,
              successevent: bool = False) -> bool:
        """発火条件に適合するイベント
        (リストのindexが若いほど優先順位が高い)を起動させる。
        keynum: 発火キーナンバー。
        keycodes: 発火キーコードのリスト。
        isinsideevent: 一連のイベント処理の内側にあるイベントであればTrue。
        Trueの場合はイベントフロー例外をキャッチせず伝播させる。
        """
        if keynum is None:
            assert keycodes is not None
            evt = self.check_keycodes(keycodes, successevent=successevent)
        else:
            assert keynum is not None
            evt = self.check_keynum(keynum)

        if evt:
            evt.clear()
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
                    rect = cw.cwpy.selection.rect
                    cw.cwpy.clear_selection()
                    cw.cwpy.add_lazydraw(clip=rect)

            # イベント実行
            if isinsideevent:
                evt.run()
            else:
                evt.start()

            # メニューカードの選択を復元
            if not isinsideevent:
                cw.cwpy.list = cw.cwpy.get_mcards("selectable")
                cw.cwpy.index = -1
                if last_selected and last_selected in cw.cwpy.list:
                    index = cw.cwpy.list.index(last_selected)
                    if 0 <= index:
                        cw.cwpy.index = index
            return True
        else:
            return False

    def check_keycodes(self, keycodes: Iterable[str], successevent: bool = False) -> Optional["Event"]:
        kcset = set(keycodes)
        kcset.discard("")
        for event in self.events:
            igkeycodes = event.keycodes
            matching = event.keycode_matching
            # 互換動作: 1.30以前では"MatchingType=All"は普通のキーコード
            if matching == "And" and cw.cwpy.sdata and\
                    cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_AREA)):
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

    def check_keycode(self, keycode: str, keycodes: Set[str], successevent: bool = False) -> bool:
        # 互換動作: 1.30以前では"！"で始まっていても普通のキーコード
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.30", cw.cwpy.sdata.get_versionhint(cw.HINT_AREA)):
            return keycode in keycodes
        else:
            if keycode.startswith("！"):
                if successevent:
                    return False
                return not keycode[1:] in keycodes
            else:
                return keycode in keycodes

    def check_keynum(self, keynum: int) -> Optional["Event"]:
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
    def __init__(self, consumecard: bool = True) -> None:
        EventError.__init__(self)
        self.consumecard = consumecard


class Event(object):
    is_active: bool
    packageid: int
    keycode_matching: str
    line_index: int
    force_nextcontent: Optional[cw.data.CWPyElement]
    force_nextcontent_index: int
    skip_action: bool

    def __init__(self, event: Optional[cw.data.CWPyElement]) -> None:
        self.parent: Optional[Event] = None
        self.base: Optional[Event] = None
        self.inusecard: Optional[cw.header.CardHeader] = None
        if cw.cwpy.is_playingscenario():
            self.scenario = cw.cwpy.sdata.name
            self.author = cw.cwpy.sdata.author
        else:
            self.scenario = ""
            self.author = ""
        # デバッガで表示のみする場合はFalseにする
        self.is_active = True
        # 次の子コンテンツインデックス。Contentの戻り値で設定される。
        self.index = 0
        # イベント実行中に発生したエラー
        self.error: Optional[EventError] = None
        # コンテンツツリーの辞書(keyはスタートコンテントのname)
        self.trees: Dict[str, cw.data.CWPyElement] = {}
        self.treekeys: List[str] = []
        self.starttree: Optional[cw.data.CWPyElement] = None
        self.cur_content: Optional[cw.data.CWPyElement] = None
        # ContentsLine実行中の時の実行位置
        self.line_index = 0
        # (パッケージ, 呼出前のcur_content, 呼出前のversionhint)
        # パッケージがNoneならスタートの呼び出し
        self.nowrunningcontents: List[Tuple[Optional[Event],
                                            cw.data.CWPyElement,
                                            int,
                                            Optional[Tuple[str, str, bool, bool, bool]]]] = []
        # 発火条件(数字)
        self.keynums: List[int] = []
        # 発火キーコード(文字列)
        self.keycodes: List[str] = []
        # キーコード発火条件("Or":どれか一つが存在する, "And":全て存在する)
        self.keycode_matching = "Or"
        # パッケージイベントであればパッケージIDを設定
        self.packageid = 0
        # 実行後に互換性情報を書き戻す必要があれば設定
        self._versionhint_base: Optional[Tuple[int, Optional[Tuple[str, str, bool, bool, bool]]]] = None

        self._stored_specialchars: Optional[cw.setting.ResourceTable[str, Tuple[pygame.Surface, bool]]] = None

        # ローカル変数(Wsn.4)
        self.flags: Dict[str, cw.data.Flag] = {}
        self.steps: Dict[str, cw.data.Step] = {}
        self.variants: Dict[str, cw.data.Variant] = {}

        self._reset_changestate = True

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

                if name not in self.trees:
                    self.trees[name] = content
                    self.treekeys.append(name)

                # 一番上にあるツリーをまず最初に実行するツリーに設定
                if self.starttree is None:
                    self.starttree = self.cur_content = content

        # 強制的に実行する次コンテント
        self.force_nextcontent = None
        self.force_nextcontent_index = -1
        self.skip_action = False

    def copy_from(self, event: "Event",
                  versionhint_base: Optional[Tuple[int, Optional[Tuple[str, str, bool, bool, bool]]]] = None) -> None:
        """実行中の処理をパッケージのイベントに差し替えるため、
        eventの情報をこのEventへコピーする。
        """
        # イベント終了時に元に戻すため、元のデータを保存
        if not self.base:
            self.base = Event(None)
            self.base.copy_from_impl(self)
        self.copy_from_impl(event)
        if not self._versionhint_base:
            self._versionhint_base = versionhint_base

    def copy_from_impl(self, event: "Event") -> None:
        self.trees = event.trees
        self.treekeys = event.treekeys
        self.starttree = event.starttree
        self.scenario = event.scenario
        self.author = event.author
        self.flags = event.flags
        self.steps = event.steps
        self.variants = event.variants

    def store_inusedata(self, selectuser: bool) -> None:
        if selectuser and isinstance(self, CardEvent):
            cw.cwpy.event.set_selectedmember(self.user)
            cw.cwpy.event.set_inusecard(self.inusecard)
        self._stored_in_cardeffectmotion = cw.cwpy.event.in_cardeffectmotion
        cw.cwpy.event.in_cardeffectmotion = False
        self._stored_in_inusecardevent = cw.cwpy.event.in_inusecardevent
        cw.cwpy.event.in_inusecardevent = False
        self._stored_specialchars = cw.cwpy.rsrc.specialchars
        cw.cwpy.rsrc.specialchars = cw.cwpy.sdata.specialchars

    def restore_inusedata(self) -> None:
        cw.cwpy.event.in_cardeffectmotion = self._stored_in_cardeffectmotion
        self._stored_in_cardeffectmotion = False
        cw.cwpy.event.in_inusecardevent = self._stored_in_inusecardevent
        self._stored_in_inusecardevent = False
        assert self._stored_specialchars
        cw.cwpy.rsrc.specialchars = self._stored_specialchars
        self._stored_specialchars = None

    def start(self) -> None:
        try:
            # ステータスバーの色を変更
            showbuttons = not cw.cwpy.is_playingscenario() or\
                cw.cwpy.areaid in cw.AREAS_SP
            cw.cwpy.statusbar.change(showbuttons)

            # ステータスアイコンの数値描画を更新
            clip = pygame.Rect(cw.cwpy.statusbar.rect)
            clip = cw.cwpy.update_statusimgs(is_runningevent=True, clip=clip)

            # イベント開始前の情報カード所持状況を記憶しておく
            if cw.cwpy.sdata.infocards_beforeevent is None:
                cw.cwpy.sdata.infocards_beforeevent = set(cw.cwpy.sdata.get_infocards(False))

            if self._reset_changestate:
                cw.cwpy.event.is_changestate = False
            self.run()

        except EventError as err:
            self.error = err
            eff = cw.cwpy.event.get_effectevent()
            if eff:
                eff.error = err
            self.stop()

        if cw.cwpy.event.exit_func:
            cw.cwpy.exec_func(cw.cwpy.event.exit_func)
            cw.cwpy.event.exit_func = None

        self.end()

    def stop(self) -> None:
        """イベント強制中断処理。
        起動中のイベントを全て中断させる。"""
        # イベントの前に開いていたダイアログをクリア
        if not isinstance(self.error, EffectBreakError):
            cw.cwpy.pre_dialogs = []

        # 起動中のイベントは全てクリア
        for event in cw.cwpy.event.get_events():
            if event.base:
                event.copy_from_impl(event.base)
                event.base = None
            cw.cwpy.event.remove_event(event)
            event.clear()

    def run(self, perf: bool = False, isinside: bool = False) -> None:
        """イベント実行。子コンテンツを順番に実行する。
        実行対象のイベントコンテント・イベントツリーは
        このイベントに属すものではない事がある。
        例えばパッケージのコール中は、実行の流れをrun()
        からは出さないまま、実行するイベントツリーのみを
        当該パッケージのものに置換する。
        これは不自然だが、際限の無い再帰を避けるために
        必要な処置である。
        """
        if not isinside:
            cw.cwpy.event.clear_stackinfo()
            cw.cwpy.event.append_stackinfo(self)

            cw.cwpy.event.append_event(self)
        else:
            insidelevel = cw.cwpy.event.get_currentstack()

        fin = True
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
                    stack = cw.cwpy.event.get_currentstack()
                    packevent, self.cur_content, self.line_index, versionhint = self.nowrunningcontents.pop()
                    cw.cwpy.event.pop_stackinfo()
                    if packevent:
                        packevent.run_exit()
                        cw.cwpy.sdata.set_versionhint(cw.HINT_AREA, versionhint)
                    if isinside and insidelevel == stack:
                        break
                else:
                    self.run_exit()
                    break
            fin = False
        finally:
            # イベント中断時は互換性情報のみ書き戻す
            if fin and self.nowrunningcontents:
                packevent, self.cur_content, self.line_index, versionhint = self.nowrunningcontents[0]
                if packevent:
                    cw.cwpy.sdata.set_versionhint(cw.HINT_AREA, versionhint)

    def run_exit(self) -> None:
        if self.base:
            self.copy_from_impl(self.base)
            self.base = None

        cw.cwpy.event.pop_event()
        self.clear()

    def end(self) -> None:
        """共通終了処理。"""
        if self.base:
            self.copy_from_impl(self.base)
            self.clear()
            self.base = None
            if cw.cwpy.sdata and self._versionhint_base is not None:
                versionlevel, versionhint = self._versionhint_base
                cw.cwpy.sdata.set_versionhint(versionlevel, versionhint)
            self._versionhint_base = None

        if not (isinstance(self.error, AreaChangeError) or
                isinstance(self.error, ScenarioBadEndError)) and\
                cw.cwpy.status not in ("Title", "GameOver"):
            if not cw.cwpy.is_gameover() and not cw.cwpy.event.is_stoped():
                cw.cwpy.show_party()
                if not cw.cwpy.is_updating_skin:
                    cw.cwpy.disposition_pcards()
                cw.cwpy.background.reload_jpdcimage = True

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
            cw.cwpy.fix_updated_file(force=True)

        # ゲームオーバ
        elif cw.cwpy.is_gameover() and cw.cwpy.is_playingscenario() and not cw.cwpy.sdata.in_f9 and 0 <= cw.cwpy.areaid:
            cw.cwpy.set_gameover()

    def get_events(self, target: "cw.sprite.card.CWPyCard") -> Optional[EventEngine]:
        """targetがEnemyであればtarget自身が持つEvents、
        Playerであればエリアのプレイヤーカードイベント(Wsn.2)を返す。
        """
        if isinstance(target, (cw.character.Enemy, cw.sprite.card.MenuCard)):
            return target.events
        elif isinstance(target, cw.character.Player):
            # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
            return cw.cwpy.sdata.playerevents
        else:
            return None

    def ignition_characterevent(self, target: "cw.character.Character", can_unconscious: bool,
                                keycodes: Iterable[str]) -> Optional["Event"]:
        """targetのキーコードイベントが発生可能か。"""
        assert isinstance(target, cw.sprite.card.CWPyCard)
        events = self.get_events(target)
        assert isinstance(target, cw.character.Character)
        if events and (can_unconscious or not (target.is_unconscious() or target.is_vanished())):
            return events.check_keycodes(keycodes)
        else:
            return None

    def ignition_deadevent(self, target: "cw.character.Character", keycodes: Iterable[str]) -> Optional["Event"]:
        """targetの死亡イベントが発生可能であれば該当イベントを返す。"""
        if cw.cwpy.msgs["runaway_keycode"] in keycodes:
            # キーコード「逃走」付きのカードは死亡イベントを発生させない
            # (ただしカード名キーコードは除く)
            return None

        assert isinstance(target, cw.sprite.card.CWPyCard)
        events = self.get_events(target)
        assert isinstance(target, cw.character.Character)
        if events and ((target.is_dead() and not target.status == "hidden") or target.is_vanished()):
            return events.check_keynum(1)
        else:
            return None

    def ignition_menucardevent(self, target: "cw.sprite.card.MenuCard", keycodes: Iterable[str]) -> Optional["Event"]:
        events = self.get_events(target)
        if events:
            return events.check_keycodes(keycodes)
        else:
            return None

    def _keycodes_for_successevent(self, keycodes: Iterable[str], successflag: bool) -> List[str]:
        keycodes2 = []
        for keycode in keycodes:
            # BUG: CardWirthでは空文字列キーコードも成功・失敗判定の対象になる
            if successflag:
                keycodes2.append(keycode + "○")
            else:
                keycodes2.append(keycode + "×")
        return keycodes2

    def ignition_successevent(self, target: "cw.character.Character", successflag: bool,
                              keycodes: Iterable[str]) -> Optional["Event"]:
        """targetのキーコード成功・失敗イベントが発生可能であれば該当イベントを返す。"""
        assert isinstance(target, cw.sprite.card.CWPyCard)
        events = self.get_events(target)
        if events:
            keycodes = self._keycodes_for_successevent(keycodes, successflag)
            return events.check_keycodes(keycodes=keycodes, successevent=True)
        else:
            return None

    def run_scenarioevent(self) -> None:
        """効果コンテントなどの実行中に他のイベントを割り込ませる。"""
        assert cw.cwpy.event
        event = cw.cwpy.event.get_event()
        assert event
        versionhint_base = cw.cwpy.sdata.versionhint[cw.HINT_AREA]
        nowrunning = cw.cwpy.event.get_nowrunningevent()

        assert event.cur_content is not None
        cur: cw.data.CWPyElement = event.cur_content
        event.nowrunningcontents.append((self, cur, event.line_index, versionhint_base))
        cw.cwpy.event.append_event(self)
        self.parent = cw.cwpy.event.get_event()

        item: Tuple[Event, cw.data.CWPyElement, int] = (self, cur, event.line_index)
        cw.cwpy.event.append_stackinfo(item)

        event.cur_content = self.starttree
        event.line_index = 0

        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_AREA, versionhint_base)

        event.store_inusedata(selectuser=True)
        try:
            event.run(isinside=True)
        finally:
            event.restore_inusedata()

    def clear(self) -> None:
        self.index = 0
        self.cur_content = self.starttree
        self.line_index = 0
        self.nowrunningcontents = []

    def action(self) -> None:
        if cw.cwpy.event.is_stoped():
            raise EffectBreakError()

        if self.skip_action:
            self.skip_action = False
            return
        """self.cur_contentを実行。"""
        assert self.cur_content is not None
        if self.cur_content.tag == "ContentsLine":
            cur_content = self.cur_content[self.line_index]
        else:
            cur_content = self.cur_content

        content = cw.content.get_content(cur_content)
        # cw.util.t_start()
        if content:
            try:
                self.index = content.action()
            finally:
                cw.cwpy.event.is_changestate |= content.is_changestate
        else:
            self.index = 0
        # cw.util.td_end(content.data.tag + content.data.get("type", ""))

        if (cur_content.tag == "Effect") or\
                (cur_content.tag == "Set" and cur_content.get("type") == "Coupon") or\
                (cur_content.tag == "Elapse" and cur_content.get("type") == "Time"):
            self.check_gameover()

        if cw.cwpy.event.is_stoped() or cw.cwpy.sdata.in_f9:
            raise EffectBreakError()

    def get_nextcontents(self) -> Optional[List[cw.data.CWPyElement]]:
        """self.cur_contentの子コンテントのリストを返す。"""
        if self.force_nextcontent is not None:
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

                if element is not None and len(element):
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
                    if e.tag != "Check" or cw.content.get_content(e).action() == 0:
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

                        if e.tag != "Check" or cw.content.get_content(e).action() == 0:
                            seq.append(ee)
                    self.line_index = 0
                    return seq
            else:
                if isline and self.line_index < len(self.cur_content):
                    return [self.cur_content]
                else:
                    self.line_index = 0
                    return cur_content.nextelements

    def check_gameover(self) -> None:
        """ゲームオーバーチェック。"""
        if cw.cwpy.is_playingscenario():
            flag = True

            for pcard in cw.cwpy.get_pcards():
                if not pcard.is_paralyze() and not pcard.is_unconscious():
                    flag = False
                    break

            if flag:
                cw.cwpy.set_gameoverstatus(flag, force=False)


class Targeting(object):
    """
    カード等の効果対象の処理を行う。
    """
    def __init__(self,
                 user: Optional[Union["cw.sprite.card.PlayerCard",
                                      "cw.sprite.card.EnemyCard",
                                      "cw.sprite.card.FriendCard"]],
                 targets: List["cw.sprite.card.CWPyCard"],
                 setcardtarget: bool) -> None:
        self.user = user
        self.targets = targets
        self.waited = False
        self._setcardtarget = setcardtarget

        self.coupon_owners: Set[cw.sprite.card.CWPyCard] = set()
        self.mcards: Set[cw.sprite.card.CWPyCard] = set()
        self._target_updated = False
        self._target_index = 0
        self.eff: Optional[cw.effectmotion.Effect] = None

        self.error: Optional[EventError] = None

    def targets_to_coupon(self) -> None:
        self.update_targets()
        self.clear_eventcoupons()
        if self.user:
            self.user.set_coupon("＠使用者", 0)

        for target in self.targets:
            if isinstance(target, cw.character.Character):
                target.set_coupon("＠効果対象", 0)
            else:
                self.mcards.add(target)
            self.coupon_owners.add(target)

        self._target_updated = False
        self._target_index = 0

    def clear_eventcoupons(self) -> None:
        self.update_targets()
        if self.user:
            self.user.remove_coupon("＠使用者")
        for ccard in self.coupon_owners.copy():
            if isinstance(ccard, cw.character.Character):
                ccard.remove_coupon("＠効果対象")
                ccard.remove_coupon("＠効果対象外")
            if self._setcardtarget:
                ccard.clear_cardtarget()
        self.coupon_owners.clear()
        self._target_updated = False

    def in_effectmotionloop(self) -> bool:
        return self.waited

    def update_targets(self) -> None:
        if self._target_updated:
            self.targets = []
            for ccard in itertools.chain(cw.cwpy.get_pcards(),
                                         cw.cwpy.get_mcards("visible"),
                                         cw.cwpy.get_fcards()):
                if isinstance(ccard, cw.character.Character):
                    assert isinstance(ccard, (cw.sprite.card.PlayerCard,
                                              cw.sprite.card.EnemyCard,
                                              cw.sprite.card.FriendCard))
                    if ccard.has_coupon("＠効果対象") and (not self.eff or self.eff.check_enabledtarget(ccard, False)):
                        self.targets.append(ccard)
                        if self._setcardtarget and not ccard.cardtarget and self.in_effectmotionloop():
                            # 反転状態を変更
                            ccard.set_cardtarget()
                            cw.cwpy.add_lazydraw(clip=ccard.rect)
                            cw.cwpy.wait_frame(1, cw.cwpy.setting.can_skipanimation)
                    else:
                        if self._setcardtarget and ccard.cardtarget and self.in_effectmotionloop():
                            # 反転状態を変更
                            ccard.clear_cardtarget()
                            cw.cwpy.add_lazydraw(clip=ccard.rect)
                            cw.cwpy.wait_frame(1, cw.cwpy.setting.can_skipanimation)
                else:
                    # メニューカード
                    if ccard in self.mcards:
                        self.targets.append(ccard)
            self._target_index = 0
        self._target_updated = False

    def get_nexttarget(self) -> Optional["cw.sprite.card.CWPyCard"]:
        self.update_targets()
        if self._target_index < len(self.targets):
            target = self.targets[self._target_index]
            self._target_index += 1
            return target
        else:
            return None

    def add_target(self, ccard: "cw.character.Character") -> None:
        """ccardを効果対象に追加する(Wsn.2)。
        "＠効果対象"はあらかじめ付与しておく事。
        """
        assert ccard.has_coupon_nolock("＠効果対象")
        assert isinstance(ccard, cw.sprite.card.CWPyCard)
        self._target_updated = True
        self.coupon_owners.add(ccard)

    def remove_target(self, ccard: "cw.character.Character") -> None:
        """ccardを効果対象から外す(Wsn.2)。
        "＠効果対象"はあらかじめ外しておく事。
        """
        assert not ccard.has_coupon_nolock("＠効果対象")
        self._target_updated = True


def _get_targetinfo() -> List[str]:
    """
    デバッグ用に各システムクーポン所持者を取得する。
    """
    user = []
    eventtarget = []
    targets = []
    outoftargets = []
    for ccard in itertools.chain(cw.cwpy.get_pcards(), cw.cwpy.get_ecards(), cw.cwpy.get_fcards()):
        if ccard.has_coupon("＠使用者"):
            assert cw.cwpy.event.effectevent and ccard in cw.cwpy.event.effectevent.coupon_owners
            user.append(ccard.name)
        if ccard.has_coupon("＠イベント対象"):
            assert cw.cwpy.event.effectevent and ccard in cw.cwpy.event.effectevent.coupon_owners
            eventtarget.append(ccard.name)
        if ccard.has_coupon("＠効果対象"):
            assert cw.cwpy.event.effectevent and ccard in cw.cwpy.event.effectevent.coupon_owners
            targets.append(ccard.name)
        if ccard.has_coupon("＠効果対象外"):
            assert cw.cwpy.event.effectevent and ccard in cw.cwpy.event.effectevent.coupon_owners
            outoftargets.append(ccard.name)
    seq = []
    seq.append("User          : %s" % ", ".join(user))
    seq.append("Event Target  : %s" % ", ".join(eventtarget))
    seq.append("Targets       : %s" % ", ".join(targets))
    seq.append("Out of Targets: %s" % ", ".join(outoftargets))
    return seq


class CardEvent(Event, Targeting):
    inusecard: "cw.header.CardHeader"

    def __init__(self, event: cw.data.CWPyElement, inusecard: "cw.header.CardHeader",
                 user: Union["cw.sprite.card.PlayerCard", "cw.sprite.card.EnemyCard", "cw.sprite.card.FriendCard"],
                 targets: List["cw.sprite.card.CWPyCard"]) -> None:
        Event.__init__(self, event)
        Targeting.__init__(self, user, targets, True)
        self.inusecard = inusecard
        self._reset_changestate = False
        self.scenario = inusecard.scenario
        self.author = inusecard.author

        # ローカル変数(Wsn.4)
        self.flags = inusecard.flags
        self.steps = inusecard.steps
        self.variants = inusecard.variants

        # パッケージのコールによるイベント差し替えに備えて
        # ローカル変数を別に記憶しておく
        self._flags = self.flags
        self._steps = self.steps
        self._variants = self.variants

    def start(self) -> None:
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, self.inusecard.versionhint)
        cw.cwpy.event.is_changestate = False

        if cw.cwpy.is_battlestatus():
            # バトル中の使用は必ず消費が発生する
            cw.cwpy.event.is_changestate = True

        if cw.cwpy.sdata.is_wsnversion('2', self.inusecard.wsnversion):
            self.targets_to_coupon()  # 対象にシステムクーポンを付与(Wsn.2)

        cw.cwpy.event.set_inusecard(self.inusecard)
        cw.cwpy.event.effectevent = self
        cw.cwpy.event.set_selectedmember(self.user)
        Event.start(self)

    def run_exit(self) -> None:
        """イベント実行の最後に行う終了処理。
        カード効果発動・効果中断コンテントに対応。
        """
        # イベント終了
        try:
            Event.run_exit(self)

            if cw.cwpy.sdata.is_wsnversion('2'):
                self.targets_to_coupon()
            else:
                self.clear_eventcoupons()

            if cw.cwpy.is_playingscenario():
                cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

            cw.cwpy.show_party()

            # エリアのキーコードイベント
            if isinstance(self.user, cw.sprite.card.PlayerCard):
                self.run_areaevent()

            # カード効果
            cw.cwpy.event.in_cardeffectmotion = True
            if not cw.cwpy.is_battlestatus():
                cw.cwpy.update_statusimgs(is_runningevent=False)
            try:
                self.effect_cardmotion()
            finally:
                cw.cwpy.event.in_cardeffectmotion = False

        finally:
            cw.cwpy.event.effectevent = None

    def end(self) -> None:
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

        # カードの使用回数減らす(シナリオ終了後に回数減らさないよう条件付き)
        if not isinstance(self.error, ScenarioEndError) and\
                (cw.cwpy.setting.spend_noeffectcard or cw.cwpy.event.is_changestate):
            if not isinstance(self.error, EffectBreakError) or self.error.consumecard:
                self.inusecard.set_uselimit(-1, animate=True)
        cw.cwpy.event.is_changestate = False

        # ローカル変数を更新する(Wsn.4)
        def save_var(v: Union[cw.data.Flag, cw.data.Step, cw.data.Variant]) -> None:
            if v.initialization == "EventExit":
                v.value = v.defaultvalue
            else:
                v.write_value()
                owner = self.inusecard.get_owner()
                if owner and isinstance(owner, cw.character.Character) and owner.data is not None:
                    owner.data.is_edited = True
            if v.initialization == "Leave" and v.value != v.defaultvalue:
                self.inusecard.set_resetvariables(True)
        self.inusecard.set_resetvariables(False)
        for flag in self._flags.values():
            save_var(flag)
        for step in self._steps.values():
            save_var(step)
        for variant in self._variants.values():
            save_var(variant)

        # effect_cardmotionでウェイトをとってない場合はここでとる
        if not self.waited:
            waitrate = (cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1) * 2
            cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

        # InuseCardImage削除
        cw.cwpy.clear_inusecardimg(self.user)

        # 効果中断等でターゲット色反転が解除されない場合があるため
        for target in self.targets:
            assert isinstance(target, cw.sprite.card.CWPyCard)
            target.clear_cardtarget()

        # ズームアウトアニメーション
        if isinstance(self.user, cw.sprite.card.CWPyCard) and self.user.zoomimgs:
            cw.animation.animate_sprite(self.user, "zoomout", battlespeed=cw.cwpy.is_battlestatus())

        # 互換性マークを削除
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.set_versionhint(cw.HINT_CARD, None)

        # システムクーポン除去(Wsn.2)
        self.clear_eventcoupons()

        # 通常イベントの終了処理
        Event.end(self)

        # 特殊エリア解除・カード選択ダイアログを開く
        cw.cwpy.clear_specialarea()

    def _exit_event(self) -> None:
        if not (isinstance(self.error, AreaChangeError) or
                isinstance(self.error, ScenarioBadEndError)):
            if not cw.cwpy.is_gameover() and not cw.cwpy.event.is_stoped():
                cw.cwpy.show_party()

    def run_areaevent(self) -> None:
        assert cw.cwpy.sdata.events
        keycodes = self.inusecard.get_keycodes()
        self.store_inusedata(selectuser=True)
        cw.cwpy.sdata.events.start(keycodes=keycodes, isinsideevent=True)
        self.restore_inusedata()
        self._exit_event()

    def run_characterevent(self, target: "cw.character.Character", can_unconscious: bool) -> None:
        keycodes = self.inusecard.get_keycodes()
        if self.ignition_characterevent(target, can_unconscious, keycodes):
            self.store_inusedata(selectuser=True)
            assert isinstance(target, cw.sprite.card.CWPyCard)
            events = self.get_events(target)
            assert events
            events.start(keycodes=keycodes, isinsideevent=True)
            self.restore_inusedata()
            self._exit_event()

    def run_deadevent(self, target: "cw.character.Character") -> bool:
        """targetの死亡イベントが発生可能であれば発生させる。"""
        if self.ignition_deadevent(target, self.inusecard.get_keycodes(with_name=False)):
            self.store_inusedata(selectuser=True)
            assert isinstance(target, cw.sprite.card.CWPyCard)
            events = self.get_events(target)
            assert events
            r = events.start(1, isinsideevent=True)
            self.restore_inusedata()
            self._exit_event()
            return bool(r)
        else:
            return False

    def run_menucardevent(self, target: "cw.sprite.card.MenuCard") -> None:
        """
        MenuCardインスタンスのキーコードイベントを発動させる。
        """
        # MenuCardのキーコードイベント発動。発動しなかったら、無効音。
        keycodes = self.inusecard.get_keycodes()
        if self.ignition_menucardevent(target, keycodes):
            lock = cw.cwpy.lock_menucards
            cw.cwpy.lock_menucards = False
            assert isinstance(target, cw.sprite.card.CWPyCard)
            events = self.get_events(target)
            assert events
            try:
                self.store_inusedata(selectuser=True)
                events.start(keycodes=keycodes)
                self.restore_inusedata()
                self._exit_event()
            finally:
                cw.cwpy.lock_menucards = lock
        else:
            cw.cwpy.play_sound("ineffective", True)
            cw.cwpy.advlog.effect_failed(target, ismenucard=True)

    def run_successevent(self, target: "cw.character.Character", successflag: bool) -> None:
        keycodes = self.inusecard.get_keycodes()
        if self.ignition_successevent(target, successflag, keycodes):
            keycodes = self._keycodes_for_successevent(keycodes, successflag)
            self.store_inusedata(selectuser=True)
            assert isinstance(target, cw.sprite.card.CWPyCard)
            events = self.get_events(target)
            assert events
            events.start(keycodes=keycodes, isinsideevent=True, successevent=True)
            self.restore_inusedata()
            self._exit_event()

    def effect_cardmotion(self) -> None:
        """カード効果発動。イベント実行の最後に行う。"""
        self.update_targets()
        # ターゲットが存在しない場合は処理中断
        if not self.targets:
            # 対象無しカードを消費する
            cw.cwpy.event.is_changestate = True
            return

        # 各種データ取得
        data = self.inusecard.carddata
        assert data is not None
        d = cw.effectmotion.EffectParams()
        d.inusecard = self.inusecard
        d["user"] = self.user
        d["absorbto"] = "User"
        d["successrate"] = data.getint("Property/SuccessRate", 0)
        d["effecttype"] = data.gettext("Property/EffectType", "Physic")
        d["resisttype"] = data.gettext("Property/ResistType", "Avoid")
        d["soundpath"] = cw.util.validate_filepath(data.gettext("Property/SoundPath2", ""))
        d["volume"] = data.getint("Property/SoundPath2", "volume", 100)
        d["loopcount"] = data.getint("Property/SoundPath2", "loopcount", 1)
        d["channel"] = data.getint("Property/SoundPath2", "channel", 0)
        d["fadein"] = data.getint("Property/SoundPath2", "fadein", 0)
        d["visualeffect"] = data.gettext("Property/VisualEffect", "None")
        d["target"] = data.gettext("Property/Target", "None")
        d["allrange"] = data.getbool("Property/Target", "allrange", False)

        selectedmember = cw.cwpy.event.get_selectedmember()

        # Effectインスタンス作成
        motions = data.getfind("Motions")
        eff = cw.effectmotion.Effect(motions, d, battlespeed=cw.cwpy.is_battlestatus())
        self.eff = eff
        eff.update_status(selectedmember=selectedmember)

        # ターゲット色反転＆ウェイト
        self.update_targets()
        if not d.get("allrange", False) and len(self.targets) == 1:
            targets = initial_effect(eff, self.targets, d.get("allrange", False), "", 100, 1, 0, 0)
        else:
            path = cw.util.validate_filepath(data.gettext("Property/SoundPath", ""))
            volume = data.getint("Property/SoundPath", "volume", 100)
            loopcount = data.getint("Property/SoundPath", "loopcount", 1)
            channel = data.getint("Property/SoundPath", "channel", 0)
            fade = data.getint("Property/SoundPath", "fadein", 0)
            targets = initial_effect(eff, self.targets, d.get("allrange", False), path, volume, loopcount, channel,
                                     fade)

        self.waited = True

        self.targets = targets
        self._target_index = 0

        # 対象メンバに効果モーションを適用
        def clear_params(target: Union[cw.character.Character, cw.sprite.card.MenuCard]) -> None:
            if isinstance(target, cw.character.Character):
                target.remove_coupon("＠効果対象")
            assert isinstance(target, cw.sprite.card.CWPyCard)
            target.clear_cardtarget()

        while True:
            if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
                break

            target = self.get_nexttarget()
            if not target:
                break

            is_menucard = isinstance(target, cw.sprite.card.MenuCard)
            cw.cwpy.event.is_changestate |= not is_menucard and not isinstance(target, cw.character.Player)

            if not is_menucard and\
                    target.is_unconscious() and\
                    not (eff.has_motions(cw.effectmotion.CAN_UNCONSCIOUS) or
                         eff.has_addablebeast(target) or
                         eff.has_removablebeast(target)):
                # 意識不明者に有効な効果が含まれていない場合は
                # イベント発火判定を含め何もしない
                clear_params(target)
                continue
            if target.status == "hidden" and\
                    not isinstance(target, cw.sprite.card.FriendCard):
                # 非表示の場合は何もしない
                clear_params(target)
                continue
            if not is_menucard and target.is_vanished():
                clear_params(target)
                continue

            unconscious_flag, paralyze_flag = get_effecttargetstatus(target, eff)

            if isinstance(target, cw.character.Character):
                if not (not target.is_unconscious() or unconscious_flag) or d.get("target", "None") == "None":
                    target.remove_coupon("＠効果対象")
                    continue

                if cw.cwpy.sdata.is_wsnversion('2'):
                    # イベント所持者を示すシステムクーポン(Wsn.2)
                    target.set_coupon("＠イベント対象", 0)

                try:
                    self.run_characterevent(target, unconscious_flag)
                    if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
                        break

                    self.update_targets()

                    if cw.cwpy.sdata.is_wsnversion('2') and not target.has_coupon("＠効果対象"):
                        clear_params(target)
                        continue

                    if not eff.check_enabledtarget(target, False):
                        clear_params(target)
                        continue

                    assert isinstance(target, cw.sprite.card.CWPyCard)
                    target.clear_cardtarget()
                    is_dead = target.is_unconscious() or target.is_paralyze()
                    success = eff.apply(target, selectedmember=selectedmember)
                    target.remove_coupon("＠効果対象")

                    # 最初から意識不明・麻痺なら死亡イベント発生なし
                    if not is_dead:
                        deadevent = self.run_deadevent(target)
                        if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
                            break
                    else:
                        deadevent = False

                    # 成功・失敗キーコードイベントより死亡イベントを優先
                    if not deadevent:
                        self.run_successevent(target, success)

                finally:
                    target.remove_coupon("＠イベント対象")

            else:
                assert isinstance(target, cw.sprite.card.MenuCard)

                target.clear_cardtarget()

                cw.cwpy.play_sound_with(eff.soundpath, subvolume=self.eff.volume, loopcount=self.eff.loopcount,
                                        channel=self.eff.channel, fade=self.eff.fade)
                eff.animate(target)
                cw.cwpy.add_lazydraw(clip=target.rect)
                self.mcards.discard(target)
                self.run_menucardevent(target)

        if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
            return

        if not isinstance(self.error, AreaChangeError):
            # 通常のカード効果は全滅時でも選択メンバをクリアする
            cw.cwpy.event.set_selectedmember(None)
        self.check_gameover()


def get_effecttargetstatus(target: "cw.character.Character", eff: cw.effectmotion.Effect) -> Tuple[bool, bool]:
    unconscious_flag = (eff.has_motions(cw.effectmotion.CAN_UNCONSCIOUS) or
                        eff.has_addablebeast(target) or
                        eff.has_removablebeast(target)) and \
                       not isinstance(target, cw.sprite.card.MenuCard) and \
                       target.is_unconscious()
    paralyze_flag = not isinstance(target, cw.sprite.card.MenuCard) and target.is_paralyze()
    return unconscious_flag, paralyze_flag


def initial_effect(eff: cw.effectmotion.Effect, targets: List["cw.sprite.card.CWPyCard"], allrange: bool, path: str,
                   volume: int, loopcount: int, channel: int, fade: int,
                   remove_target: Optional[Callable[["cw.sprite.card.CWPyCard"], None]] = None)\
        -> List["cw.sprite.card.CWPyCard"]:
    """
    カード初期効果のターゲット色反転&初期音声再生&ウェイトを実行する。
    """
    skipped = False
    if not allrange and len(targets) == 1:
        assert len(targets) == 1
        target = targets[0]
        target.set_cardtarget()
        if path:
            cw.cwpy.play_sound_with(path, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)
        if eff.check_enabledtarget(target, False):
            waitrate = (cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus()) + 1) * 2
            skipped = cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
        else:
            waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus()) + 1
            skipped = cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
            target.clear_cardtarget()
            if remove_target:
                remove_target(target)
            targets = []
    else:
        targets2: List[cw.sprite.card.CWPyCard] = []
        for target in targets:
            if eff.check_enabledtarget(target, False):
                target.set_cardtarget()
                if path:
                    cw.cwpy.play_sound_with(path, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus()) + 1
                skipped = cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                targets2.append(target)
            else:
                if remove_target:
                    remove_target(target)
        targets = targets2

    if not skipped and cw.cwpy.setting.wait_usecard:
        waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())
        cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
    return targets


def main() -> None:
    pass


if __name__ == "__main__":
    main()
