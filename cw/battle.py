#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw


class BattleError(Exception):
    pass

class BattleAreaChangeError(BattleError):
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
            pcard.deck.set(pcard)

        for fcard in cw.cwpy.get_fcards():
            fcard.deck.set(fcard)

        # ラウンド数
        self.round = 0
        # 戦闘参加メンバ
        self.members = []
        # 戦闘開始の準備完了フラグ
        self._ready = False
        # 戦闘行動中フラグ
        self._running = False
        # 行動準備
        self.ready()

    def is_running(self):
        return self._running

    def is_ready(self):
        return self._ready

    def start(self):
        try:
            self.run()
        except BattleAreaChangeError:
            self.end(False)
        except BattleWinError:
            self.win()
        except BattleDefeatError:
            self.defeat()

    def run(self):
        """戦闘行動を開始する。1ラウンド分の処理。"""
        self._running = True
        self._ready = False

        if self.check_win():
            # デバッグ操作などで敵が全滅したらここへ来る
            for member in self.members:
                member.clear_action()
            raise BattleWinError()

        # ラウンドイベントスタート
        cw.cwpy.sdata.start_event(keynum=-self.round)

        # 戦闘行動ループ
        for member in self.members:
            if member.status == "hidden":
                # イベント中に隠された
                continue

            member.action()

            # 勝利チェック
            if self.check_win():
                for member in self.members:
                    member.clear_action()
                raise BattleWinError()

        # 行動内容のクリア
        for member in self.members:
            member.clear_action()

        # 時間経過
        cw.cwpy.elapse_time()

        # 勝利・敗北チェック
        if self.check_defeat():
            raise BattleDefeatError()
        elif self.check_win():
            raise BattleWinError()

        # 山札からカードをドロー
        for member in self.members:
            member.deck.draw(member)

        self._running = False
        # 次ターン準備
        self.ready()

    def end(self, areachange=True):
        """戦闘終了処理。戦闘エリアを解除する。"""
        # 行動内容のクリア
        for member in self.members:
            member.clear_action()

        self._running = False

        for pcard in cw.cwpy.get_pcards():
            pcard.deck.clear(pcard)

            if not pcard.is_reversed():
                pcard.remove_timedcoupons(True)

        for fcard in cw.cwpy.get_fcards():
            fcard.deck.clear(fcard)

            if not fcard.is_reversed():
                fcard.remove_timedcoupons(True)

        cw.cwpy.clear_battlearea(areachange=areachange)

    def ready(self):
        """戦闘行動の準備を行う。
        1ラウンド終了するたびに自動的に呼ばれる。
        """
        self.round += 1
        self.round = cw.util.numwrap(self.round, 1, 999999)
        # 戦闘参加メンバセット・行動順にソート・手札自動選択
        self.set_members()
        self.set_actionorder()
        self.set_action()
        self._ready = True
        cw.cwpy.statusbar.change()

    def runaway(self):
        """逃走処理。逃走イベントが存在する場合は、
        逃走イベント優先。
        """
        self.clear_playersaction()
        event = cw.cwpy.sdata.events.check_keynum(2)

        if event:
            # 逃走イベント開始
            try:
                cw.cwpy.sdata.start_event(keynum=2)
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
            successes = [pcard.decide_outcome(level, vocation, enemybonus)
                                                        for pcard in pcards]

            # 逃走成功・失敗時の処理
            if pcards and len(successes) > len(pcards) / 2:
                # 行動内容のクリア
                for member in self.members:
                    member.clear_action()
                cw.cwpy.sounds["run"].play()
                self.end()
            else:
                cw.cwpy.sounds["error"].play()
                self.start()

    def win(self):
        """勝利処理。勝利イベント終了後も戦闘が続行していたら、
        強制的に戦闘エリアから離脱する。
        """
        # 行動内容のクリア
        for member in self.members:
            member.clear_action()

        cw.cwpy.hide_cards(True)
        cw.cwpy.mcardgrp.empty()

        areaid, bgmpath, battlebgmpath = cw.cwpy.pre_battleareadata
        if cw.cwpy.music.path <> bgmpath:
            cw.cwpy.music.play(bgmpath)

        # 勝利イベント実行時は元のエリアに戻る(時間経過無し)
        cw.cwpy.change_area(areaid, battlewin=True)

        # 勝利イベント開始
        try:
            cw.cwpy.sdata.start_event(keynum=1)
        except BattleAreaChangeError:
            self.end(False)
        except BattleDefeatError:
            self.defeat()
        except BattleError:
            self.end()
        else:
            self.end()

    def defeat(self):
        """敗北処理。敗北イベント後、
        パーティが全滅状態だったら、ゲームオーバ画面に遷移。
        """
        # 行動内容のクリア
        for member in self.members:
            member.clear_action()

        self._running = False
        event = cw.cwpy.sdata.events.check_keynum(3)

        if event:
            cw.cwpy.hide_cards(True)
            cw.cwpy.mcardgrp.empty()
            cw.cwpy._gameover = False

            # 敗北イベント開始
            try:
                cw.cwpy.sdata.start_event(keynum=3)
            except BattleAreaChangeError:
                self.end(False)
            except BattleDefeatError:
                cw.cwpy.set_gameover()
            except BattleError:
                self.end()
            else:
                self.end()

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
        self.members = [member for member in members if member.is_active()]

    def set_actionorder(self):
        """行動順を決める値を算出し、
        その値をもとに並び替えした戦闘参加メンバを設定する。
        """
        for member in self.members:
            member.decide_actionorder()

        cw.util.sort_by_attr(self.members, "actionorder")
        self.members.reverse()

    def set_action(self):
        """戦闘参加メンバ全員、行動自動選択。"""
        if cw.cwpy.get_ecards("unreversed"):
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
