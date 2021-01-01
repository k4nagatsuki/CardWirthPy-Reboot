#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import copy

from typing import List, Optional, Sequence, TypeVar

_T = TypeVar("_T")


class Dice(object):
    def roll(self, times: int = 1, sided: int = 6) -> int:
        if sided <= 1:
            return times

        n = 0

        for _i in range(times):
            # BUG: random.randrange()は著しく遅い
            # n += random.randrange(1, sided + 1)

            # random.uniform(1, sided+1)は多少速いが
            # 次のコードよりは遅い
            n += int(random.random() * sided) + 1

        return n

    def choice(self, seq: Sequence[_T]) -> Optional[_T]:
        if seq:
            return random.choice(seq)
        else:
            return None

    def choice_exists(self, seq: Sequence[_T]) -> _T:
        assert seq
        return random.choice(seq)

    def shuffle(self, seq: List[_T]) -> List[_T]:
        seq2 = copy.copy(seq)
        random.shuffle(seq2)
        return seq2

    def pop(self, seq: List[_T]) -> Optional[_T]:
        item = self.choice(seq)

        if item:
            seq.remove(item)

        return item


def main() -> None:
    pass


if __name__ == "__main__":
    main()
