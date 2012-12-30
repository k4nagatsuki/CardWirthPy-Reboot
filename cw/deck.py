#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw


class Deck(object):
    def __init__(self, ccard):
        # 手札
        self.hand = []
        # 山札
        self.talon = []
        # 定められた次のドローカード
        self.nextcards = []

    @classmethod
    def get_actioncards(cls, ccard):
        seq = []

        for id, header in cw.cwpy.rsrc.actioncards.iteritems():
            if id == 7 and not ccard.escape:
                continue # 逃走しない
            if id > 0:
                for cnt in xrange(header.uselimit):
                    seq.append(header)

        cls.get_actioncards = classmethod(lambda cls, ccard: seq)
        return seq

    def get_skillcards(self, ccard):
        seq = []

        for header in ccard.cardpocket[cw.POCKET_SKILL]:
            uselimit, maxn = header.get_uselimit()

            for cnt in xrange(uselimit):
                seq.append(header)

        return seq

    def set_nextcard(self, id=0):
        """山札の一番上に指定したIDのアクションカードを置く。
        IDを指定しなかった場合(0の場合)は、スキルカードを置く。
        """
        # アクションカード
        if id and id in cw.cwpy.rsrc.actioncards:
            header = cw.cwpy.rsrc.actioncards[id]
        # スキルカード
        else:
            for header in self.talon:
                if header.type == "SkillCard":
                    break

            else:
                return

        # ペナルティカードじゃなかったら、山札からカードを消す
        if not id < 0 and header in self.talon:
            self.talon.remove(header)

        self.nextcards.append(header)

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
        n = (ccard.level + 1) / 2 + 4
        return cw.util.numwrap(n, 5, 12)

    def set(self, ccard):
        self.clear(ccard)
        self.talon.extend(self.get_actioncards(ccard))
        self.talon.extend(self.get_skillcards(ccard))
        self.shuffle()
        self.set_hand(ccard)
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
        self.hand.extend(ccard.cardpocket[cw.POCKET_ITEM])
        # アクションカード、技能カードを手札に加える
        maxn = self.get_handmaxnum(ccard)
        index = maxn - len(self.hand)
        self.hand.extend(hand[:index])
        flag = False

        for header in hand[index:]:
            if header.type == "SkillCard":
                header = header.ref_original()
                self.insert(0, header)
                flag = True
            elif header.type == "ActionCard" and header.id > 0:
                header = cw.cwpy.rsrc.actioncards[header.id]
                self.insert(0, header)
                flag = True

        if flag:
            self.shuffle_bottom()

    def add(self, ccard, header):
        if header.type == "ItemCard":
            self.set_hand(ccard)
        elif header.type == "SkillCard":
            uselimit, maxn = header.get_uselimit()

            for cnt in xrange(uselimit):
                self.talon.append(header)

            self.shuffle()

    def remove(self, ccard, header):
        if cw.cwpy.battle:
            self.hand = [h for h in self.hand
                                if not h.ref_original == header.ref_original]
            self.talon = [h for h in self.talon
                                if not h.ref_original == header.ref_original]
            self.nextcards = [h for h in self.nextcards
                                if not h.ref_original == header.ref_original]

    def clear(self, ccard):
        self.talon = []
        self.hand = []
        self.nextcards = []
        ccard.clear_action()

    def throwaway(self, ccard):
        hand = []

        for header in self.hand[1::]:
            if header.type == "SkillCard":
                header = header.ref_original()
                hand.append(header)
            elif header.type == "ActionCard" and header.id > 0:
                header = cw.cwpy.rsrc.actioncards[header.id]
                hand.append(header)

        self.hand = []
        talon = []
        talon.extend(hand)
        talon.extend(self.talon)
        self.talon = talon
        self.shuffle()
        self.set_hand(ccard)

    def draw(self, ccard):
        maxn = self.get_handmaxnum(ccard)

        while len(self.hand) < maxn:
            if not self.nextcards:
                self.check_mind(ccard)

            if self.nextcards:
                header = self.nextcards.pop()
            else:
                header = self.talon.pop()

            header_copy = header.copy()

            if header.type == "ActionCard":
                if header.id > 0:
                    self.talon.insert(0, header)

                header_copy.set_owner(ccard)

            self.hand.append(header_copy)

    def check_mind(self, ccard):
        """
        特殊な精神状態の場合、次にドローするカードを変更。
        """
        if ccard.is_panic():
            if ccard.escape:
                n = cw.cwpy.dice.roll(1, 4) + 3
            else:
                n = cw.cwpy.dice.roll(1, 3) + 3
            self.set_nextcard(n)
        elif ccard.is_brave():
            n = cw.cwpy.dice.roll(1, 3)
            self.set_nextcard(n)
        elif ccard.is_overheat():
            self.set_nextcard(2)
        elif ccard.is_confuse():
            self.set_nextcard(-1)

def main():
    pass

if __name__ == "__main__":
    main()

