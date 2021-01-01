#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import base

import cw

from typing import Dict, Optional, Union


class EffectMotion(base.CWBinaryBase):
    """効果モーションのデータ。
    効果コンテントやスキル・アイテム・召喚獣カード等で使う。
    """
    from . import skill
    from . import item
    from . import beast
    from . import content

    def __init__(self, parent: Union["skill.SkillCard", "item.ItemCard", "beast.BeastCard", "content.Content"],
                 f: "cw.binary.cwfile.CWFile", yadodata: bool = False, dataversion: int = 4) -> None:
        from . import beast

        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.tabtype = f.byte()

        if 2 < dataversion:
            # 不明なバイト列(8,5,0,0,0)。読み飛ばし。
            for _cnt in range(5):
                _ = f.byte()

        self.element = f.byte()

        # 大分類が召喚の場合は、byteを読み込まない。
        if self.tabtype == 8:
            self.type = 0
        else:
            self.type = f.byte()

        # 初期化
        self.properties: Dict[str, Union[str, int]] = {}
        self.beasts = None

        # 生命力, 肉体
        if self.tabtype in (0, 1):
            s = self.conv_effectmotion_damagetype(f.byte())
            self.properties["damagetype"] = s
            self.properties["value"] = f.dword()
        # 精神, 魔法
        elif self.tabtype in (3, 4):
            if 2 < dataversion:
                self.properties["duration"] = f.dword()
            else:
                self.properties["duration"] = 10
        # 能力
        elif self.tabtype == 5:
            self.properties["value"] = f.dword()
            if 2 < dataversion:
                self.properties["duration"] = f.dword()
            else:
                self.properties["duration"] = 10
        # 技能, 消滅, カード
        elif self.tabtype in (2, 6, 7):
            pass
        # 召喚(BeastCardインスタンスを生成)
        elif self.tabtype == 8:
            beasts_num = f.dword()
            self.beasts = [beast.BeastCard(self, f, summoneffect=True)
                           for _cnt in range(beasts_num)]
        else:
            raise ValueError(self.fpath)

        self.data: Optional[cw.data.CWPyElement] = None

    def get_data(self) -> "cw.data.CWPyElement":
        if self.data is None:
            self.data = cw.data.make_element("Motion")
            self.data.set("type", self.conv_effectmotion_type(self.tabtype, self.type))
            self.data.set("element", self.conv_effectmotion_element(self.element))
            for key, value in self.properties.items():
                if isinstance(value, str):
                    self.data.set(key, value)
                else:
                    self.data.set(key, str(value))
            if self.beasts:
                e = cw.data.make_element("Beasts")
                for beastcard in self.beasts:
                    e.append(beastcard.get_data())
                self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f: "cw.binary.cwfile.CWFileWriter", data: "cw.data.CWPyElement") -> None:
        from . import beast

        tabtype, mtype = base.CWBinaryBase.unconv_effectmotion_type(data.get("type"), f)
        element = base.CWBinaryBase.unconv_effectmotion_element(data.get("element"))

        f.write_byte(tabtype)

        # 不明なバイト列
        f.write_byte(8)
        f.write_byte(5)
        f.write_byte(0)
        f.write_byte(0)
        f.write_byte(0)

        f.write_byte(element)

        # 大分類が召喚の場合は、typeを飛ばす
        if tabtype != 8:
            f.write_byte(mtype)

        # 生命力, 肉体
        if tabtype in (0, 1):
            f.write_byte(base.CWBinaryBase.unconv_effectmotion_damagetype(data.get("damagetype")))
            f.write_dword(int(data.get("value", "0")))
        # 精神, 魔法
        elif tabtype in (3, 4):
            f.write_dword(int(data.get("duration", "10")))
        # 能力
        elif tabtype == 5:
            f.write_dword(int(data.get("value", "0")))
            f.write_dword(int(data.get("duration", "10")))
        # 技能
        elif tabtype == 2:
            if not data.get("damagetype", "Max") in ("", "Max"):
                f.check_wsnversion("1", "技能使用回数回復・喪失量の指定")
        # 消滅, カード
        elif tabtype in (6, 7):
            pass
        # 召喚(BeastCardインスタンスを生成)
        elif tabtype == 8:
            beasts = data.find("Beasts")
            if beasts is None:
                f.write_dword(0)
            else:
                f.write_dword(len(beasts))
                for card in beasts:
                    beast.BeastCard.unconv(f, card, False)
        else:
            raise ValueError(tabtype)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
