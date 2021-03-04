#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw

import itertools

from typing import Dict, List, Optional


class Deck(object):
    def __init__(self, ccard: "cw.character.Character") -> None:
        # 手札
        self.hand: List[cw.header.CardHeader] = []
        # 山札
        self.talon: List[cw.header.CardHeader] = []
        # 定められた次のドローカード
        self.nextcards: List[int] = []
        # 手札が破棄されたか
        self._throwaway = False
        # BUG: CardWirth 1.50では使用済みの手札はカード消去効果を受けたり
        #      行動不能になっても手札に残る事が分かっているので、
        #      挙動を合わせるためここに保存しておく。
        self._used: Optional[cw.header.CardHeader] = None

    def get_hand(self, ccard: "cw.character.Character") -> List[cw.header.CardHeader]:
        """ccardの手札に存在すると仮定されるカードのlistを返す。"""
        if self.is_throwed() or not ccard.is_active():
            seq = []
        else:
            seq = self.hand[:]
        if self._used:
            seq.append(self._used)
        return seq

    def get_used(self) -> Optional[cw.header.CardHeader]:
        """使用後の残存カードを返す。"""
        return self._used

    def clear_used(self) -> None:
        """使用後の残存カードをクリアする。"""
        self._used = None

    def get_actioncards(self, ccard: "cw.character.Character") -> List[cw.header.CardHeader]:
        seq = []

        for resid, header in cw.cwpy.rsrc.actioncards.items():
            if 0 < resid and ccard.actions.get(resid, True):
                for _cnt in range(header.uselimit):
                    seq.append(header)

        return seq

    def update_actioncards(self, ccard: "cw.character.Character") -> None:
        hand2 = []
        for i, header in enumerate(self.hand):
            if header.type != "ActionCard":
                hand2.append(header)
                continue
            header2 = cw.cwpy.rsrc.actioncards.get(header.id, None)
            if header2 is None:
                continue
            header3 = header2.copy()
            header3.set_owner(ccard)
            hand2.append(header3)
            if self._used is header:
                self._used = header3
            if ccard.actiondata and ccard.actiondata[1] is header:
                ccard.actiondata = (ccard.actiondata[0], header3, ccard.actiondata[2])

        self.hand = hand2
        self.talon = []
        self.talon.extend(self.get_actioncards(ccard))
        self.talon.extend(self.get_skillcards(ccard))
        self.shuffle()

    def get_skillcards(self, ccard: "cw.character.Character",
                       handcounts: Optional[Dict[cw.header.CardHeader, int]] = None) -> List[cw.header.CardHeader]:
        if handcounts is None:
            handcounts = {}
        seq = []

        for header in ccard.get_pocketcards(cw.POCKET_SKILL):
            uselimit, _maxn = header.get_uselimit()

            for _cnt in range(uselimit - handcounts.get(header, 0)):
                seq.append(header)

        return seq

    def set_nextcard(self, resid: int = 0) -> None:
        """山札の一番上に指定したIDのアクションカードを置く。
        IDを指定しなかった場合(0の場合)は、スキルカードを置く。
        """
        self.nextcards.insert(0, resid)

    def _set_nextcard(self, ccard: "cw.character.Character", resid: int) -> bool:
        # アクションカード
        if resid:
            if resid in cw.cwpy.rsrc.actioncards and ccard.actions.get(resid, True):
                header = cw.cwpy.rsrc.actioncards[resid]
            else:
                return False
        # スキルカード
        else:
            for header in self.talon:
                if header.type == "SkillCard":
                    break

            else:
                return False

        # 山札の一番上へカードを置く
        if not resid < 0 and header in self.talon:
            self.talon.remove(header)
        self.talon.append(header)
        return True

    def shuffle(self) -> None:
        self.talon = cw.cwpy.dice.shuffle(self.talon)

    def get_handmaxnum(self, ccard: "cw.character.Character") -> int:
        n = (ccard.level + 1) // 2 + 4
        n = cw.util.numwrap(n, 5, 12)
        return n

    def set(self, ccard: "cw.character.Character", draw: bool = True) -> None:
        self.clear(ccard)
        self.talon.extend(self.get_actioncards(ccard))
        self.talon.extend(self.get_skillcards(ccard))
        self.shuffle()
        if draw:
            self.set_hand(ccard)
            self.draw(ccard)

    def set_hand(self, ccard: "cw.character.Character") -> None:
        hand = [h for h in self.hand if h.type == "SkillCard" or
                h.type == "ActionCard" and h.id > 0]
        # 手札構築
        self.hand = []
        # カード交換カードを手札に加える
        if ccard.actions.get(0, True):
            header = cw.cwpy.rsrc.actioncards[0].copy()
            header.set_owner(ccard)
            self.hand.append(header)
        # アイテムカードを手札に加える
        self.hand.extend(ccard.get_pocketcards(cw.POCKET_ITEM))
        # アクションカード、技能カードを手札に加える
        maxn = self.get_handmaxnum(ccard)
        index = maxn - len(self.hand)
        self.hand.extend(hand[:index])
        flag = False

        for header in hand[index:]:
            if header.type == "SkillCard":
                orig = header.ref_original()
                assert orig
                self.talon.insert(0, orig)
                flag = True
            elif header.type == "ActionCard" and header.id > 0:
                header = cw.cwpy.rsrc.actioncards[header.id]
                self.talon.insert(0, header)
                flag = True

        if flag:
            self.shuffle()

    def add(self, ccard: "cw.character.Character", header: cw.header.CardHeader, is_replace: bool = False) -> None:
        if header.type == "ItemCard":
            if not is_replace:
                # アイテムカードが1枚でも配付されると
                # 手札は引き直される
                # (削除時は引き直されない)
                self._clear_hand()
            self.set_hand(ccard)
        elif header.type == "SkillCard":
            uselimit, _maxn = header.get_uselimit()

            for _cnt in range(uselimit):
                self.talon.append(header)

            self.shuffle()

    def remove(self, ccard: "cw.character.Character", header: cw.header.CardHeader) -> None:
        if cw.cwpy.battle:
            if header.type == "ActionCard":
                for h in self.hand[:]:
                    if h.id != 0 and h == header:
                        self._remove(h)
            else:
                self.hand = [h for h in self.hand
                             if not h.ref_original == header.ref_original]
                self.talon = [h for h in self.talon
                              if not h.ref_original == header.ref_original]

    def get_skillpower(self, ccard: "cw.character.Character") -> None:
        # 一旦山札から全てのスキルを取り除く
        talon = []
        for header in self.talon:
            if header.type != "SkillCard":
                talon.append(header)
        self.talon = talon

        # 現在手札にある分と配付予約にある分をカウントする
        handcounts: Dict[cw.header.CardHeader, int] = {}
        for header in self.hand:
            orig = header.ref_original()
            assert orig
            count = handcounts.get(orig, 0)
            count += 1
            handcounts[orig] = count

        # 山札に改めて追加
        self.talon.extend(self.get_skillcards(ccard, handcounts))
        self.shuffle()

        self._update_skillpower(ccard)

    def lose_skillpower(self, ccard: "cw.character.Character", losevalue: int) -> None:
        # 現在handにある分は除去しなくてよい
        talon: List[cw.header.CardHeader] = []
        skilltable: Dict[cw.header.CardHeader, int] = {}

        def remove_skill(header: cw.header.CardHeader, seq: List[cw.header.CardHeader]) -> None:
            if header.type == "SkillCard":
                orig = header.ref_original()
                assert orig
                removecount = skilltable.get(orig, 0)
                if removecount < losevalue:
                    skilltable[orig] = removecount + 1
                    return
            seq.append(header)

        for header in self.talon:
            remove_skill(header, talon)
        self.talon = talon
        self.shuffle()
        if self._throwaway:
            # 手札喪失が予約されている場合に限りhandからも除去
            hand: List[cw.header.CardHeader] = []
            for header in self.hand:
                remove_skill(header, hand)
            self.hand = hand

        self._update_skillpower(ccard)

    def _update_skillpower(self, ccard: "cw.character.Character") -> None:
        # 手札と山札にある数によってスキルカードの使用回数を更新する
        handcounts: Dict[cw.header.CardHeader, int] = {}
        for header in itertools.chain(self.hand, self.talon):
            if header.type == "SkillCard":
                orig = header.ref_original()
                assert orig
                count = handcounts.get(orig, 0)
                count += 1
                handcounts[orig] = count

        for header in ccard.get_pocketcards(cw.POCKET_SKILL):
            count = handcounts.get(header, 0)
            header.set_uselimit(count - header.uselimit)

        for header in itertools.chain(self.hand, self.talon):
            if header.type == "SkillCard":
                orig = header.ref_original()
                assert orig
                count = handcounts.get(orig, 0)
                orig.uselimit = count

    def update_skillcardimage(self, header: cw.header.CardHeader) -> None:
        for header2 in self.hand:
            if header2.ref_original() is header:
                header2.uselimit = header.uselimit

    def clear(self, ccard: "cw.character.Character") -> None:
        self.talon = []
        self.hand = []
        self.nextcards = []
        self._throwaway = False
        self._used = None
        ccard.clear_action()

    def throwaway(self) -> None:
        """手札消去効果を適用する。"""
        self._throwaway = True

    def clear_nextcards(self) -> None:
        """配付予約されていたカードをクリアする。"""
        self.nextcards = []

    def is_throwed(self) -> bool:
        """手札が消去されているか。"""
        return self._throwaway

    def _remove(self, header: cw.header.CardHeader) -> None:
        assert header in self.hand
        self.hand.remove(header)
        if header.type == "SkillCard":
            orig = header.ref_original()
            assert orig
            self.talon.append(orig)
        elif header.type == "ActionCard" and header.id > 0:
            header = cw.cwpy.rsrc.actioncards[header.id]
            self.talon.append(header)

    def _clear_hand(self) -> None:
        """現在の手札を山札に戻す。"""
        for header in self.hand[:]:
            if header.type == "ActionCard" and header.id == 0:
                continue  # カード交換
            self._remove(header)
        self.shuffle()

    def draw(self, ccard: "cw.character.Character") -> None:
        self._used = None
        maxn = self.get_handmaxnum(ccard)
        if ccard.is_inactive():
            return

        if self._throwaway or not self.hand:
            # 現在の手札を山札に戻す
            self._clear_hand()

            self.hand = []
            assert isinstance(ccard, cw.sprite.card.CWPyCard)
            if ccard.actions.get(0, True):
                # カード交換は常に残す
                header = cw.cwpy.rsrc.actioncards[0].copy()
                header.set_owner(ccard)
                self.hand.append(header)
            # アイテムカードを手札に加える
            assert isinstance(ccard, cw.character.Character)
            self.hand.extend(ccard.get_pocketcards(cw.POCKET_ITEM))
            self._throwaway = False

        while len(self.hand) < maxn and self.talon:
            if self.nextcards:
                if not self._set_nextcard(ccard, self.nextcards.pop()):
                    self.check_mind(ccard)
            else:
                self.check_mind(ccard)

            header = self.talon.pop()
            header_copy = header.copy()

            if header.type == "ActionCard":
                header_copy.set_owner(ccard)

            self.hand.append(header_copy)

        while maxn < len(self.hand):
            self._remove(self.hand[-1])

    def check_mind(self, ccard: "cw.character.Character") -> None:
        """
        特殊な精神状態の場合、次にドローするカードを変更。
        """
        if ccard.is_panic():
            acts = [5, 6, 7]
        elif ccard.is_brave():
            acts = [0, 1, 2, 3]
        elif ccard.is_overheat():
            acts = [2]
        elif ccard.is_confuse():
            # 混乱時、混乱カードは2/3の確率で配布とする。
            if cw.cwpy.dice.roll(1, 3) > 1:
                acts = [-1]
            else:
                return
        else:
            return
        assert isinstance(ccard, cw.sprite.card.CWPyCard)
        acts = list(filter(lambda cid: cid == 0 or ccard.actions.get(cid, True), acts))
        if acts:
            self._set_nextcard(ccard, cw.cwpy.dice.choice_exists(acts))

    def set_used(self, header: cw.header.CardHeader) -> None:
        """使用したカードをそのラウンド中記憶する。"""
        self._used = header

    def use(self, header: cw.header.CardHeader) -> None:
        """headerを使用する。
        アイテムカードまたはカード交換は手札に残る。
        スキルカードは1枚消失する。
        アクションカードは山札に戻る。
        """
        if header in self.hand and not header.type == "ItemCard" and\
                not (header.type == "ActionCard" and header.id == 0):
            self.hand.remove(header)
            if header.type == "ActionCard" and 0 <= header.id:
                self.talon.insert(0, header)
        elif header.type == "SkillCard" and header not in self.hand:
            # アイテムカード配付等で手札から押し出され、
            # 使用前に山札に戻されている場合がある
            # アクションカードはそのままでよいが特殊技能は必ず消費させる
            orig = header.ref_original()
            if orig is not None and orig in self.talon:
                self.talon.remove(orig)
                self.shuffle()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
