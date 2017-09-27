#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bisect

import cw


class BattleError(Exception):
    pass

class BattleAreaChangeError(BattleError):
    pass

class BattleStartBattleError(BattleError):
    pass

class BattleWinError(BattleError):
    pass

class BattleDefeatError(BattleError):
    pass

class BattleEngine(object):
    def __init__(self):
        """
        戦闘関係のデータ・処理をまとめたクラス。
        初期化時に自動的にready()を実行する。
        """
        # PlayerCard・FriendCardの戦闘用デッキを構築
        for pcard in cw.cwpy.get_pcards():
            pcard.deck.set(pcard, draw=False)

        for fcard in cw.cwpy.get_fcards():
            fcard.deck.set(fcard, draw=False)

        self.priorityacts = []

        # ラウンド数
        self.round = 0
        # 戦闘参加メンバ
        self.members = []
        # 戦闘開始の準備完了フラグ
        self._ready = False
        # 戦闘行動中フラグ
        self._running = False
        # 前回のラウンドで逃走を試みた場合
        self._ranaway = False
        # 表示中の敵の数
        self.numenemy = 0
        if cw.cwpy.is_autospread():
            self.numenemy = len(cw.cwpy.get_mcards("flagtrue"))
        # ラウンドイベント中か
        self.in_roundevent = False

        cw.cwpy.battle = self

        try:
            cw.cwpy.advlog.start_battle(self)

            # バトル開始イベント(1.50)
            # このイベントの終了時点では勝利・敗北は発生しない
            cw.cwpy.sdata.start_event(keynum=5)

            # 行動準備
            self.ready()

        except BattleStartBattleError:
            self.end(False, startnextbattle=True)
        except BattleAreaChangeError:
            self.end(False)
        except BattleWinError:
            self.win(runevent=False)
        except BattleDefeatError:
            self.defeat(runevent=False)

    def is_running(self):
        return self._running

    def is_ready(self):
        return self._ready

    def is_battlestarting(self):
        return not (self.is_running() or self.is_ready())

    def start(self):
        try:
            self.run()
        except BattleStartBattleError:
            self.end(False, startnextbattle=True)
        except BattleAreaChangeError:
            self.end(False)
        except BattleWinError:
            self.win()
        except BattleDefeatError:
            self.defeat()

    def process_exception(self, ex):
        """イベントの強制実行等で発生したバトル例外を処理する。"""
        if isinstance(ex, BattleStartBattleError):
            self.end(False, startnextbattle=True)
        elif isinstance(ex, BattleAreaChangeError):
            self.end(False)
        elif isinstance(ex, BattleWinError):
            self.win()
        elif isinstance(ex, BattleDefeatError):
            self.defeat()
        else:
            assert False

    def run(self):
        """戦闘行動を開始する。1ラウンド分の処理。"""
        cw.cwpy.clear_selection()
        cw.cwpy.clear_fcardsprites()

        if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
            self.end(f9=True)
            return

        self._running = True
        self._ready = False

        # デバッグ操作などで状態が変わっている可能性があるため
        # 勝利・敗北チェック
        if self.check_defeat():
            raise BattleDefeatError()
        elif self.check_win():
            raise BattleWinError()

        cw.cwpy.advlog.start_round(self.round)

        # ラウンドイベントスタート
        self.in_roundevent = True
        try:
            cw.cwpy.sdata.start_event(keynum=-self.round)
        finally:
            self.in_roundevent = False

        if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
            self.end(f9=True)
            return

        # イベント結果の勝利・敗北チェック
        if self.check_defeat():
            raise BattleDefeatError()
        elif self.check_win():
            raise BattleWinError()

        clip = cw.cwpy.update_statusimgs(is_runningevent=True)
        if clip:
            cw.cwpy.draw(clip=clip)

        # 戦闘行動ループ
        for member in self.members:
            member.actionend = False
        for member in self.members:
            if member.actionend:
                continue
            cw.cwpy.input()
            cw.cwpy.eventhandler.run()
            member.action()
            if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
                self.end(f9=True)
                return
            if not self._running:
                return

            # 勝利チェック
            if self.check_win():
                raise BattleWinError()

        # 行動内容のクリア
        for member in self.members:
            member.deck.clear_used()
            member.clear_action()

        if not cw.cwpy.is_playingscenario() or cw.cwpy.sdata.in_f9:
            self.end(f9=True)
            return

        cw.cwpy.input()
        cw.cwpy.eventhandler.run()

        # 時間経過
        cw.cwpy.elapse_time()

        # 勝利・敗北チェック
        if self.check_defeat():
            raise BattleDefeatError()
        elif self.check_win():
            raise BattleWinError()

        ran = self._ranaway
        self._running = False
        self._ranaway = False

        # 2ラウンド目移行は自動で行動開始可能
        # ただし逃走を試みた時は自動で行動開始はしたくないはずなので開始しない
        if cw.cwpy.setting.show_roundautostartbutton and cw.cwpy.sdata.autostart_round and not ran:
            self.ready(redraw=False)
            cw.cwpy.exec_func(self.start)
        else:
            # 次ターン準備
            self.ready()

    def end(self, areachange=True, f9=False, startnextbattle=False):
        """勝利・敗北以外の戦闘終了処理。
        戦闘エリアを解除する。
        """
        # 対象選択中であれば中止
        cw.cwpy.clean_specials()

        # 行動内容のクリア
        for member in cw.cwpy.get_pcards():
            member.clear_action()

        is_battlestarting = self.is_battlestarting()
        self._running = False
        self._ready = True

        if f9:
            cw.cwpy.sdata.pre_battleareadata = None
        else:
            if not startnextbattle:
                cw.cwpy.advlog.end_battle(self)

            cw.cwpy.clear_battlearea(areachange=areachange, startnextbattle=startnextbattle, is_battlestarting=is_battlestarting)

    def ready(self, redraw=True):
        """戦闘行動の準備を行う。
        1ラウンド終了するたびに自動的に呼ばれる。
        """
        self.round += 1
        self.round = cw.util.numwrap(self.round, 1, 999999)
        # 戦闘参加メンバセット・行動順にソート・手札自動選択
        self.priorityacts = []
        self.set_members()
        # 山札からカードをドロー
        for member in self.members:
            member.deck.draw(member)
        self.set_actionorder()
        self.set_action()

        if cw.cwpy.is_autospread():
            ecards = cw.cwpy.get_mcards("flagtrue")
            if self.numenemy <> len(ecards):
                self.numenemy = len(ecards)
                cw.cwpy.set_autospread(ecards, 6, False, anime=True)
        cw.cwpy.show_party()
        cw.cwpy.disposition_pcards()
        if cw.cwpy.is_debugmode() and cw.cwpy.setting.show_fcardsinbattle:
            cw.cwpy.add_fcardsprites(status="normal", alpha=192)
        if redraw:
            self._ready = True
            cw.cwpy.statusbar.change()
            cw.cwpy.clear_selection()
            cw.cwpy.draw()

    def update_debug(self):
        # 敵の状態の暴露・非暴露切り替え
        for sprite in cw.cwpy.get_mcards():
            sprite.update_scale()

        # 同行NPCの表示切り替え
        if self.is_ready():
            self.update_showfcards()

    def update_showfcards(self):
        cw.cwpy.clear_fcardsprites()
        if cw.cwpy.is_debugmode() and\
                cw.cwpy.setting.show_fcardsinbattle and\
                self.is_ready():
            cw.cwpy.add_fcardsprites(status="normal", alpha=192)

    def runaway(self):
        """逃走処理。逃走イベントが存在する場合は、
        逃走イベント優先。
        """
        cw.cwpy.clear_fcardsprites()
        self.clear_playersaction()
        event = cw.cwpy.sdata.events.check_keynum(2)
        self._ranaway = True

        cw.cwpy.advlog.start_runaway()

        if event:
            # 逃走イベント開始
            try:
                cw.cwpy.clear_selection()
                cw.cwpy.clear_fcardsprites()
                self._ready = False
                self._running = True
                cw.cwpy.sdata.start_event(keynum=2)
            except BattleStartBattleError:
                self.end(False, startnextbattle=True)
            except BattleAreaChangeError:
                self.end(False)
            except BattleDefeatError:
                self.defeat()
            except BattleError:
                self.start()
            else:
                self.start()

        else:
            # 判定値を算出
            ecards = cw.cwpy.get_ecards("active")
            level = sum([ecard.level for ecard in ecards])
            level = level / len(ecards) if ecards else 0
            vocation = ("agl", "trickish")
            enemybonus = len(ecards) + 3
            # パーティ全員で敏捷・狡猾の行為判定
            # 半分以上が判定成功したら、逃走成功
            pcards = cw.cwpy.get_pcards("active")
            success = [pcard.decide_outcome(level, vocation, enemybonus)
                                                        for pcard in pcards].count(True)

            # 逃走成功・失敗時の処理
            if pcards and success > len(pcards) / 2:
                cw.cwpy.advlog.runaway(True)
                # 行動内容のクリア
                for member in self.members:
                    member.clear_action()
                cw.cwpy.play_sound("run")
                self.end()
                cw.cwpy.statusbar.change(True)
            else:
                cw.cwpy.advlog.runaway(False)
                cw.cwpy.play_sound("error")
                self.start()

    def win(self, runevent=True):
        """勝利処理。勝利イベント終了後も戦闘が続行していたら、
        強制的に戦闘エリアから離脱する。
        """
        # 行動内容のクリア
        for member in cw.cwpy.get_pcards():
            member.clear_action()
        assert cw.cwpy.is_battlestatus()

        is_battlestarting = self.is_battlestarting()
        cw.cwpy.hide_cards(True)
        cw.cwpy.cardgrp.remove(cw.cwpy.mcards)
        cw.cwpy.mcards = []
        cw.cwpy.file_updates.clear()

        if runevent:
            eventkeynum = 1
        else:
            eventkeynum = 0

        cw.cwpy.advlog.end_battle(self)

        # 勝利イベント実行時は元のエリアに戻る
        cw.cwpy.clear_battlearea(True, eventkeynum=eventkeynum, is_battlestarting=is_battlestarting)

    def defeat(self, runevent=True):
        """敗北処理。敗北イベント後、
        パーティが全滅状態だったら、ゲームオーバ画面に遷移。
        """
        # 行動内容のクリア
        for member in self.members:
            member.clear_action()

        is_battlestarting = self.is_battlestarting()
        self._running = False
        if runevent and not cw.cwpy.is_forcegameover():
            event = cw.cwpy.sdata.events.check_keynum(3)
        else:
            event = None

        cw.cwpy.advlog.end_battle(self)

        if event:
            cw.cwpy.hide_cards(True)
            cw.cwpy.cardgrp.remove(cw.cwpy.mcards)
            cw.cwpy.mcards = []
            cw.cwpy.file_updates.clear()
            cw.cwpy._gameover = False

            # 戦闘前のエリアに戻り、敗北イベント開始
            cw.cwpy.clear_battlearea(True, eventkeynum=3, is_battlestarting=is_battlestarting)

        else:
            cw.cwpy.set_gameover()

    def check_win(self):
        flag = True

        for ecard in cw.cwpy.get_ecards():
            if ecard.is_alive():
                flag = False

        return flag

    def check_defeat(self):
        flag = True

        for pcard in cw.cwpy.get_pcards():
            if pcard.is_alive():
                flag = False

        return flag

    def set_members(self):
        """戦闘参加メンバを設定する。
        行動可能でないものは除外。
        """
        members = cw.cwpy.get_pcards("unreversed")
        members.extend(cw.cwpy.get_ecards("unreversed"))
        members.extend(cw.cwpy.get_fcards())
        self.members = members

    def set_actionorder(self):
        """行動順を決める値を算出し、
        その値をもとに並び替えした戦闘参加メンバを設定する。
        """
        if not self.members:
            return

        member = self.members[0]
        members = [(-member.decide_actionorder(), 0, member)]
        for i, member in enumerate(self.members[1:], 1):
            o = (-member.decide_actionorder(), -i, member)
            bisect.insort(members, o)

        assert len(members) == len(self.members)
        self.members = map(lambda o: o[2], members)

    def set_action(self):
        """戦闘参加メンバ全員、行動自動選択。"""
        for member in self.members:
            member.decide_action()

    def clear_playersaction(self):
        """PlayerCard, FriendCardの行動をクリアする。"""
        for pcard in cw.cwpy.get_pcards():
            pcard.clear_action()

        for fcard in cw.cwpy.get_fcards():
            fcard.clear_action()

def main():
    pass

if __name__ == "__main__":
    main()
