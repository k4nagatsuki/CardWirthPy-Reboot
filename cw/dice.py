#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import copy


class Dice(object):
    def roll(self, times=1, sided=6):
        if sided <= 1:
            return times

        n = 0

        for _i in xrange(times):
            # BUG: random.randrange()は著しく遅い
            #n += random.randrange(1, sided + 1)

            # random.uniform(1, sided+1)は多少速いが
            # 次のコードよりは遅い
            n += int(random.random() * sided) + 1

        return n

    def choice(self, seq):
        if seq:
            return random.choice(seq)
        else:
            return None

    def shuffle(self, seq):
        seq2 = copy.copy(seq)
        random.shuffle(seq2)
        return seq2

    def pop(self, seq):
        item = self.choice(seq)

        if item:
            seq.remove(item)

        return item

def main():
    pass

if __name__ == "__main__":
    main()
