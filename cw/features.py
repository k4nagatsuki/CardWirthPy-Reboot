#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw


"""特性の定義。性別、年代、素質、特徴に派生する。"""
class Feature(object):
    def __init__(self, data):
        self.data = data
        # 特性名
        self.name = self.data.gettext("Name", "")

        # 器用度修正
        self.dexbonus = self.data.getfloat("Physical", "dex", 0.0)
        # 敏捷度修正
        self.aglbonus = self.data.getfloat("Physical", "agl", 0.0)
        # 知力修正
        self.intbonus = self.data.getfloat("Physical", "int", 0.0)
        # 筋力修正
        self.strbonus = self.data.getfloat("Physical", "str", 0.0)
        # 生命力修正
        self.vitbonus = self.data.getfloat("Physical", "vit", 0.0)
        # 精神力修正
        self.minbonus = self.data.getfloat("Physical", "min", 0.0)

        # 好戦-平和
        self.aggressive = self.data.getfloat("Mental", "aggressive", 0.0)
        # 社交-内向
        self.cheerful   = self.data.getfloat("Mental", "cheerful", 0.0)
        # 勇敢-臆病
        self.brave      = self.data.getfloat("Mental", "brave", 0.0)
        # 慎重-大胆
        self.cautious   = self.data.getfloat("Mental", "cautious", 0.0)
        # 狡猾-正直
        self.trickish   = self.data.getfloat("Mental", "trickish", 0.0)

    def modulate(self, data, physical=True, mental=True):
        """dataの能力値を特性によって調整する。"""
        if physical:
            data.dex += self.dexbonus
            data.agl += self.aglbonus
            data.int += self.intbonus
            data.str += self.strbonus
            data.vit += self.vitbonus
            data.min += self.minbonus
        if mental:
            data.aggressive += self.aggressive
            data.cheerful   += self.cheerful
            data.brave      += self.brave
            data.cautious   += self.cautious
            data.trickish   += self.trickish

    def demodulate(self, data, physical=True, mental=True):
        """modulate()と逆の調整を行う。"""
        if physical:
            data.dex -= self.dexbonus
            data.agl -= self.aglbonus
            data.int -= self.intbonus
            data.str -= self.strbonus
            data.vit -= self.vitbonus
            data.min -= self.minbonus
        if mental:
            data.aggressive -= self.aggressive
            data.cheerful   -= self.cheerful
            data.brave      -= self.brave
            data.cautious   -= self.cautious
            data.trickish   -= self.trickish

"""性別の定義。"""
class Sex(Feature):
    def __init__(self, data):
        Feature.__init__(self, data)

        # 名前の別表現。「Male」「Female」など
        self.subname = self.data.getattr(".", "subName", self.name)

        # 父親になれる性別か
        self.father = self.data.getbool(".", "father", True)
        # 母親になれる性別か
        self.mother = self.data.getbool(".", "mother", True)

"""年代の定義。"""
class Period(Feature):
    def __init__(self, data):
        Feature.__init__(self, data)

        # 名前の別表現。「Child」「Young」など
        self.subname = self.data.getattr(".", "subName", self.name)
        # 略称。「CHDTV」「YNG」など
        self.abbr = self.data.getattr(".", "abbr", self.subname)

        # 子作りした際のEP消費量。0の場合は子作り不可
        self.spendep = self.data.getint(".", "spendEP", 10)
        # 初期レベル
        self.level = self.data.getint(".", "level", 1)
        # 初期クーポン
        self.coupons = [(e.gettext(".", ""), e.getint(".", "value", 0)) for e in data.getfind("Coupons")]

        # キャラクタの作成時、最初から選択されている年代か
        self.firstselect = self.data.getbool(".", "firstSelect", False)

"""素質の定義。"""
class Nature(Feature):
    def __init__(self, data):
        Feature.__init__(self, data)

        # 解説
        self.description = self.data.gettext("Description", "")
        # 特殊型か
        self.special = self.data.getbool(".", "special", False)
        # 遺伝情報
        self.genecount = self.data.getint(".", "geneCount", 0)
        self.genepattern = self.data.getattr(".", "genePattern", "0000000000")
        # 最大レベル
        self.levelmax = self.data.getint(".", "levelMax", 10)
        # 派生元
        self.basenatures = [e.gettext(".", "") for e in data.getfind("BaseNatures")]

"""特徴の定義。"""
class Making(Feature):
    def __init__(self, data):
        Feature.__init__(self, data)

"""デバグ宿で簡易生成を行う際の能力型。"""
class SampleType(Feature):
    def __init__(self, data):
        Feature.__init__(self, data)

def wrap_ability(data):
    """
    能力値の切り上げ・切り捨て。
    """
    data.dex = cw.util.numwrap(data.dex, 1, data.maxdex)
    data.agl = cw.util.numwrap(data.agl, 1, data.maxagl)
    data.int = cw.util.numwrap(data.int, 1, data.maxint)
    data.str = cw.util.numwrap(data.str, 1, data.maxstr)
    data.vit = cw.util.numwrap(data.vit, 1, data.maxvit)
    data.min = cw.util.numwrap(data.min, 1, data.maxmin)
    data.aggressive = int(cw.util.numwrap(data.aggressive, -4, 4))
    data.cheerful = int(cw.util.numwrap(data.cheerful, -4, 4))
    data.brave = int(cw.util.numwrap(data.brave, -4, 4))
    data.cautious = int(cw.util.numwrap(data.cautious, -4, 4))
    data.trickish = int(cw.util.numwrap(data.trickish, -4, 4))
