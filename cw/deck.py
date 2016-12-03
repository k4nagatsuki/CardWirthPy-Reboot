#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw

import itertools


class Deck(object):
    def __init__(self, ccard):
        # 手札
        self.hand = []
        # 山札
        self.talon = []
        # 定められた次のドローカード
        self.nextcards = []
        # 手札が破棄されたか
        self._throwaway = False
        # BUG: CardWirth 1.50では使用済みの手札はカード消去効果を受けたり
        #      行動不能になっても手札に残る事が分かっているので、
        #      挙動を合わせるためここに保存しておく。
        self._used = None

    def get_hand(self, ccard):
        """ccardの手札に存在すると仮定されるカードのlistを返す。"""
        if self.is_throwed() or not ccard.is_active():
            seq = []
        else:
            seq = self.hand[:]
        if self._used:
            seq.append(self._used)
        return seq

    def get_used(self):
        """使用後の残存カードを返す。"""
        return self._used

    def clear_used(self):
        """使用後の残存カードをクリアする。"""
        self._used = None

    def get_actioncards(self, ccard):
        seq = []

        for resid, header in cw.cwpy.rsrc.actioncards.iteritems():
            if resid == 7 and not ccard.escape:
                continue # 逃走しない
            if resid > 0:
                for _cnt in xrange(header.uselimit):
                    seq.append(header)

        return seq

    def get_skillcards(self, ccard, handcounts={}.copy()):
        seq = []

        for header in ccard.get_pocketcards(cw.POCKET_SKILL):
            uselimit, _maxn = header.get_uselimit()

            for _cnt in xrange(uselimit - handcounts.get(header, 0)):
                seq.append(header)

        return seq

    def set_nextcard(self, resid=0):
        """山札の一番上に指定したIDのアクションカードを置く。
        IDを指定しなかった場合(0の場合)は、スキルカードを置く。
        """
        self.nextcards.insert(0, resid)

    def _set_nextcard(self, resid, brave=False):
        # アクションカード
        if resid and resid in cw.cwpy.rsrc.actioncards:
            header = cw.cwpy.rsrc.actioncards[resid]
        # スキルカード
        else:
            for header in self.talon:
                if header.type == "SkillCard":
                    break

            else:
                if brave:
                    # スキルカードが尽き、かつ勇敢ならば、配布されるカードとして攻撃系を指定
                    header = cw.cwpy.rsrc.actioncards[cw.cwpy.dice.roll(1, 3)]
                else:
                    return

        # 山札の一番上へカードを置く
        if not resid < 0 and header in self.talon:
            self.talon.remove(header)
        self.talon.append(header)

    def shuffle(self):
        self.talon = cw.cwpy.dice.shuffle(self.talon)

    def shuffle_bottom(self):
        try:
            talon = cw.cwpy.dice.shuffle(self.talon[:-20])
            talon.extend(self.talon[-20:])
            self.talon = talon
        except:
            pass

    def get_handmaxnum(self, ccard):
        n = (ccard.level + 1) // 2 + 4
        n = cw.util.numwrap(n, 5, 12)
        return n

    def set(self, ccard, draw=True):
        self.clear(ccard)
        self.talon.extend(self.get_actioncards(ccard))
        self.talon.extend(self.get_skillcards(ccard))
        self.shuffle()
        self.set_hand(ccard)
        if draw:
            self.draw(ccard)

    def set_hand(self, ccard):
        hand = [h for h in self.hand if h.type == "SkillCard" or
                                        h.type == "ActionCard" and h.id > 0]
        # 手札構築
        self.hand = []
        # カード交換カードを手札に加える
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
                header = header.ref_original()
                self.talon.insert(0, header)
                flag = True
            elif header.type == "ActionCard" and header.id > 0:
                header = cw.cwpy.rsrc.actioncards[header.id]
                self.talon.insert(0, header)
                flag = True

        if flag:
            self.shuffle_bottom()

    def add(self, ccard, header):
        if header.type == "ItemCard":
            self.set_hand(ccard)
        elif header.type == "SkillCard":
            uselimit, _maxn = header.get_uselimit()

            for _cnt in xrange(uselimit):
                self.talon.append(header)

            self.shuffle()

    def remove(self, ccard, header):
        if cw.cwpy.battle:
            self.hand = [h for h in self.hand
                                if not h.ref_original == header.ref_original]
            self.talon = [h for h in self.talon
                                if not h.ref_original == header.ref_original]

    def get_skillpower(self, ccard):
        # 一旦山札から全てのスキルを取り除く
        talon = []
        for header in self.talon:
            if header.type <> "SkillCard":
                talon.append(header)
        self.talon = talon

        # 現在手札にある分と配付予約にある分をカウントする
        handcounts = {}
        for header in self.hand:
            header = header.ref_original()
            count = handcounts.get(header, 0)
            count += 1
            handcounts[header] = count

        # 山札に改めて追加
        self.talon.extend(self.get_skillcards(ccard, handcounts))
        self.shuffle()

        self._update_skillpower(ccard)

    def lose_skillpower(self, ccard, losevalue):
        # 現在handにある分は除去しなくてよい
        talon = []
        skilltable = {}

        def remove_skill(header, seq):
            if header.type == "SkillCard":
                orig = header.ref_original()
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
            hand = []
            for header in self.hand:
                remove_skill(header, hand)
            self.hand = hand

        self._update_skillpower(ccard)

    def _update_skillpower(self, ccard):
        # 手札と山札にある数によってスキルカードの使用回数を更新する
        handcounts = {}
        for header in itertools.chain(self.hand, self.talon):
            if header.type == "SkillCard":
                header = header.ref_original()
                count = handcounts.get(header, 0)
                count += 1
                handcounts[header] = count

        for header in ccard.get_pocketcards(cw.POCKET_SKILL):
            count = handcounts.get(header, 0)
            header.set_uselimit(count - header.uselimit)

        for header in itertools.chain(self.hand, self.talon):
            if header.type == "SkillCard":
                count = handcounts.get(header.ref_original(), 0)
                header.uselimit = count

    def update_skillcardimage(self, header):
        for header2 in self.hand:
            if header2.ref_original() is header:
                header2.uselimit = header.uselimit

    def clear(self, ccard):
        self.talon = []
        self.hand = []
        self.nextcards = []
        self._throwaway = False
        self._used = None
        ccard.clear_action()

    def throwaway(self):
        """手札消去効果を適用する。"""
        self._throwaway = True

    def is_throwed(self):
        """手札が消去されているか。"""
        return self._throwaway

    def _remove(self, header):
        self.hand.remove(header)
        if header.type == "SkillCard":
            header = header.ref_original()
            self.talon.append(header)
        elif header.type == "ActionCard" and header.id > 0:
            header = cw.cwpy.rsrc.actioncards[header.id]
            self.talon.append(header)

    def draw(self, ccard):
        self._used = None
        maxn = self.get_handmaxnum(ccard)
        if self._throwaway:
            # 現在の手札を山札に戻す
            for header in self.hand[1::]:
                self._remove(header)
            self.shuffle()

            self.hand = []
            # カード交換は常に残す
            header = cw.cwpy.rsrc.actioncards[0].copy()
            header.set_owner(ccard)
            self.hand.append(header)
            # アイテムカードを手札に加える
            self.hand.extend(ccard.get_pocketcards(cw.POCKET_ITEM))
            self._throwaway = False

        while len(self.hand) < maxn:
            if self.nextcards:
                self._set_nextcard(self.nextcards.pop(), ccard.is_brave())
            else:
                self.check_mind(ccard)

            header = self.talon.pop()
            header_copy = header.copy()

            if header.type == "ActionCard":
                header_copy.set_owner(ccard)

            self.hand.append(header_copy)

        while maxn < len(self.hand):
            self._remove(self.hand[-1])

    def check_mind(self, ccard):
        """
        特殊な精神状態の場合、次にドローするカードを変更。
        """
        if ccard.is_panic():
            if ccard.escape:
                n = cw.cwpy.dice.roll(1, 3) + 4
            else:
                n = cw.cwpy.dice.roll(1, 2) + 4
            self._set_nextcard(n)
        elif ccard.is_brave():
            n = cw.cwpy.dice.roll(1, 4) - 1
            self._set_nextcard(n, brave=True)
        elif ccard.is_overheat():
            self._set_nextcard(2)
        elif ccard.is_confuse():
            # 混乱時、混乱カードは2/3の確率で配布とする。
            if cw.cwpy.dice.roll(1, 3)>1:
                self._set_nextcard(-1)

    def use(self, header):
        """headerを使用する。
        アイテムカードまたはカード交換は手札に残る。
        スキルカードは1枚消失する。
        アクションカードは山札に戻る。
        """
        self._used = header
        if header in self.hand and not header.type == "ItemCard" and\
                not (header.type == "ActionCard" and header.id == 0):
            self.hand.remove(header)
            if header.type == "ActionCard" and 0 <= header.id:
                self.talon.insert(0, header)

def main():
    pass

if __name__ == "__main__":
    main()

