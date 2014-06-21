#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pygame
from pygame.locals import MOUSEBUTTONDOWN, MOUSEBUTTONUP, KEYDOWN, KEYUP, K_RETURN

import cw


class EventContentBase(object):
    def __init__(self, data):
        self.data = data

    def action(self):
        return 0

    def can_action(self):
        return True

    def get_status(self):
        return self.data.tag + self.data.get("type", "")

    def get_childname(self, child):
        return child.get("name", "")

    def get_transitiontype(self):
        """トランジション効果のデータのタプル((効果名, 速度))を返す。
        ChangeBgImage, ChangeArea, Redisplayコンテント参照。
        """
        tname = self.data.get("transition", "Default")
        tspeed = self.data.get("transitionspeed", "Default")

        try:
            tspeed = int(tspeed)
        except:
            pass

        return (tname, tspeed)

#-------------------------------------------------------------------------------
# Branch系コンテント
#-------------------------------------------------------------------------------

class BranchContent(EventContentBase):
    def branch_cards(self, cardtype):
        """カード所持分岐。最初の所持者を選択する。
        cardtype: "SkillCard" or "BeastCard" or "ItemCard"
        """
        # 各種属性値取得
        id = self.data.getint(".", "id", 0)
        num = self.data.getint(".", "number", 0)
        scope = self.data.get("targets")

        # 対象カードのxmlファイルのパス
        if cardtype == "SkillCard":
            table = cw.cwpy.sdata.skills
            pocketidx = cw.POCKET_SKILL
        elif cardtype == "ItemCard":
            table = cw.cwpy.sdata.items
            pocketidx = cw.POCKET_ITEM
        elif cardtype == "BeastCard":
            table = cw.cwpy.sdata.beasts
            pocketidx = cw.POCKET_BEAST
        else:
            raise ValueError(cardtype + " is invalid cardtype")

        if not id in table:
            # 存在しないカードは常に所持していない
            return self.get_boolean_index(False)

        path = table[id][1]

        # 対象カードデータ取得
        e = cw.data.xml2element(path, "Property")
        cardname = e.gettext("Name", "noname")
        carddesc = e.gettext("Description", "")

        # 対象範囲修正
        if scope == "Random":
            scope = "Party"
            someone = True
        elif scope == "Party":
            someone = False
        else:
            someone = True

        # 所持判定
        targets = cw.cwpy.event.get_targetscope(scope)
        flag = False
        selectedmember = None
        cardnum = 0

        for target in targets:
            # 対象カード所持判定
            if isinstance(target, list):
                targetheaders = target
            else:
                targetheaders = target.get_pocketcards(pocketidx)

            headers = []

            for h in targetheaders:
                if h.name == cardname and h.desc == carddesc:
                    headers.append(h)

            # 判定結果
            flag = bool(len(headers) >= num)
            cardnum += len(headers)

            if flag and someone:
                # 所持者を選択メンバに設定
                if not isinstance(target, list):
                    selectedmember = target

                break
            elif not flag and not someone:
                # 最後に判定した者を選択メンバに設定
                if not isinstance(target, list):
                    selectedmember = target

                break

        # パーティ全体での所持数判定
        if scope == "PartyAndBackpack":
            flag = bool(cardnum >= num)

        # 選択設定
        if not scope == "Selected":
            if selectedmember:
                cw.cwpy.event.set_selectedmember(selectedmember)
            elif not someone:
                selectedmember = cw.cwpy.event.get_targetmember("Random")
                cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(flag)

    def get_boolean_index(self, flag):
        idx_true = cw.IDX_TREEEND
        idx_false = cw.IDX_TREEEND

        index = 0
        for chld in self.data:
            if chld.tag == "Contents":
                for e in chld:
                    # フラグ判定コンテントの場合、
                    # 対応フラグがTrueの場合のみ実行対象に
                    if e.tag == "Check":
                        type = e.get("type")
                        if type == "Flag":
                            if cw.content.CheckFlagContent(e).action() <> 0:
                                continue
                        elif type == "Step":
                            if cw.content.CheckStepContent(e).action() <> 0:
                                continue

                    name = e.get("name")

                    if idx_true < 0 and name == u"○":
                        idx_true = index
                    elif idx_false < 0 and name == u"×":
                        idx_false = index
                    index += 1
                break

        if flag:
            index = idx_true
        else:
            index = idx_false

        return index

    def get_value_index(self, value):
        value = str(value)
        idx_value = cw.IDX_TREEEND
        idx_default = cw.IDX_TREEEND  # 「その他」の分岐

        index = 0
        for chld in self.data:
            if chld.tag == "Contents":
                for e in chld:
                    # フラグ判定コンテントの場合、
                    # 対応フラグがTrueの場合のみ実行対象に
                    if e.tag == "Check":
                        type = e.get("type")
                        if type == "Flag":
                            if cw.content.CheckFlagContent(e).action() <> 0:
                                continue
                        elif type == "Step":
                            if cw.content.CheckStepContent(e).action() <> 0:
                                continue

                    name = e.get("name")

                    if idx_value < 0 and name == value:
                        idx_value = index
                    elif idx_default < 0 and name == "Default":
                        idx_default = index
                    index += 1
                break

        if idx_value is not cw.IDX_TREEEND:
            index = idx_value
        else:
            index = idx_default

        return index

    def get_compare_index(self, cmp):
        idx_lt = cw.IDX_TREEEND
        idx_eq = cw.IDX_TREEEND
        idx_gt = cw.IDX_TREEEND

        index = 0
        for chld in self.data:
            if chld.tag == "Contents":
                for e in chld:
                    # フラグ判定コンテントの場合、
                    # 対応フラグがTrueの場合のみ実行対象に
                    if e.tag == "Check":
                        type = e.get("type")
                        if type == "Flag":
                            if cw.content.CheckFlagContent(e).action() <> 0:
                                continue
                        elif type == "Step":
                            if cw.content.CheckStepContent(e).action() <> 0:
                                continue

                    name = e.get("name")

                    if idx_lt < 0 and name == u"<":
                        idx_lt = index
                    elif idx_eq < 0 and name == u"=":
                        idx_eq = index
                    elif idx_gt < 0 and name == u">":
                        idx_gt = index
                    index += 1
                break

        if cmp < 0:
            index = idx_lt
        elif cmp == 0:
            index = idx_eq
        else:
            assert cmp > 0
            index = idx_gt

        return index

    textdict = {
        # 対象範囲
        "selected" : u"選択中メンバが",
        "random" : u"誰か一人が",
        "party" : u"パーティ全員が",
        "backpack" : u"荷物袋の中に",
        "partyandbackpack" : u"パーティ全体で",
        "field" : u"フィールド全体で",
        # 対象メンバ
        "random" : u"ランダムメンバ",
        "selected" : u"選択中メンバ",
        "unselected" : u"選択外メンバ",
        "inusecard" : u"使用中カード",
        "party" : u"パーティ全体",
        "enemy" : u"敵全体",
        "npc" : u"同行キャスト全体",
        # 身体能力
        "dex" : u"器用度",
        "agl" : u"敏捷度",
        "int" : u"知力",
        "str" : u"筋力",
        "vit" : u"生命力",
        "min" : u"精神力",
        # 精神能力
        "aggressive" : u"好戦性",
        "unaggressive" : u"平和性",
        "cheerful" : u"社交性",
        "uncheerful" : u"内向性",
        "brave" : u"勇猛性",
        "unbrave" : u"臆病性",
        "cautious" : u"慎重性",
        "uncautious" : u"大胆性",
        "trickish" : u"狡猾性",
        "untrickish" : u"正直性",
        # ステータス
        "active" : u"行動可能",
        "inactive" : u"行動不可",
        "alive" : u"生存",
        "dead" : u"非生存",
        "fine" : u"健康",
        "injured" : u"負傷",
        "heavyinjured" : u"重傷",
        "unconscious" : u"意識不明",
        "poison" : u"中毒",
        "sleep" : u"眠り",
        "bind" : u"呪縛",
        "paralyze" : u"麻痺／石化",
        "confuse" : u"混乱", # 1.30
        "overheat" : u"激昂", # 1.30
        "brave" : u"勇敢", # 1.30
        "panic" : u"恐慌", # 1.30
        "silence" : u"沈黙", # 1.50
        "faceup" : u"暴露", # 1.50
        "antimagic" : u"魔法無効化", # 1.50
        "upaction" : u"行動力上昇", # 1.50
        "upavoid" : u"回避力上昇", # 1.50
        "upresist" : u"抵抗力上昇", # 1.50
        "updefense" : u"防御力上昇", # 1.50
        "downaction" : u"行動力低下", # 1.50
        "downavoid" : u"回避力低下", # 1.50
        "downresist" : u"抵抗力低下", # 1.50
        "downdefense" : u"防御力低下", # 1.50
        # カード種別
        "all" : u"全てのカード", # 1.50
        "skill" : u"特殊技能カード", # 1.50
        "item" : u"アイテムカード", # 1.50
        "beast" : u"召喚獣カード", # 1.50
    }

class BranchSkillContent(BranchContent):
    def action(self):
        """スキル所持分岐コンテント。"""
        return self.branch_cards("SkillCard")

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.skills:
            return u"特殊技能カード『%s』所持分岐" % (cw.cwpy.sdata.skills[id][0])
        else:
            return u"特殊技能カードが指定されていません"

    def get_childname(self, child):
        id = self.data.getint(".", "id", 0)
        scope = self.data.get("targets")

        if id in cw.cwpy.sdata.skills:
            s = self.textdict.get(scope.lower(), "")
            s2 = cw.cwpy.sdata.skills[id][0]

            if child.get("name", "") == u"○":
                s = u"%s『%s』を所有している" % (s, s2)
            else:
                s = u"%s『%s』を所有していない" % (s, s2)

        else:
            s = u"特殊技能カードが指定されていません"

        return s

class BranchItemContent(BranchContent):
    def action(self):
        """スキル所持分岐コンテント。"""
        return self.branch_cards("ItemCard")

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.items:
            return u"アイテムカード『%s』所持分岐" % (cw.cwpy.sdata.items[id][0])
        else:
            return u"アイテムカードが指定されていません"

    def get_childname(self, child):
        id = self.data.getint(".", "id", 0)
        scope = self.data.get("targets")

        if id in cw.cwpy.sdata.items:
            s = self.textdict.get(scope.lower(), "")
            s2 = cw.cwpy.sdata.items[id][0]

            if child.get("name", "") == u"○":
                s = u"%s『%s』を所有している" % (s, s2)
            else:
                s = u"%s『%s』を所有していない" % (s, s2)

        else:
            s = u"アイテムカードが指定されていません"

        return s

class BranchBeastContent(BranchContent):
    def action(self):
        """スキル所持分岐コンテント。"""
        return self.branch_cards("BeastCard")

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.beasts:
            return u"召喚獣カード『%s』所持分岐" % (cw.cwpy.sdata.beasts[id][0])
        else:
            return u"召喚獣カードが指定されていません"

    def get_childname(self, child):
        id = self.data.getint(".", "id", 0)
        scope = self.data.get("targets")

        if id in cw.cwpy.sdata.beasts:
            s = self.textdict.get(scope.lower(), "")
            s2 = cw.cwpy.sdata.beasts[id][0]

            if child.get("name", "") == u"○":
                s = u"%s『%s』を所有している" % (s, s2)
            else:
                s = u"%s『%s』を所有していない" % (s, s2)

        else:
            s = u"召喚獣カードが指定されていません"

        return s

class BranchCastContent(BranchContent):
    def action(self):
        """キャスト存在分岐コンテント。"""
        id = self.data.getint(".", "id", 0)
        flag = bool([i for i in cw.cwpy.sdata.friendcards if i.id == id])
        return self.get_boolean_index(flag)

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.casts:
            return u"キャスト『%s』存在分岐" % (cw.cwpy.sdata.casts[id][0])
        else:
            return u"キャストが指定されていません"

    def get_childname(self, child):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.casts:
            s = cw.cwpy.sdata.casts[id][0]
        else:
            s = u"指定無し"

        if child.get("name", "") == u"○":
            return u"キャスト『%s』が加わっている" % (s)
        else:
            return u"キャスト『%s』が加わっていない" % (s)

class BranchInfoContent(BranchContent):
    def action(self):
        """情報所持分岐コンテント。"""
        id = self.data.getint(".", "id", 0)
        flag = bool([h for h in cw.cwpy.sdata.infocards if h.id == id])
        return self.get_boolean_index(flag)

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.infos:
            return u"情報カード『%s』存在分岐" % (cw.cwpy.sdata.infos[id][0])
        else:
            return u"情報カードが指定されていません"

    def get_childname(self, child):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.infos:
            s = cw.cwpy.sdata.infos[id][0]
        else:
            s = u"指定無し"

        if child.get("name", "") == u"○":
            return u"情報カード『%s』を所持している" % (s)
        else:
            return u"情報カード『%s』を所持していない" % (s)

class BranchIsBattleContent(BranchContent):
    def action(self):
        """バトル判定分岐コンテント。"""
        flag = bool(cw.cwpy.battle)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"戦闘判定コンテント"

    def get_childname(self, child):
        if child.get("name", "") == u"○":
            return u"イベント発生時の状況が戦闘中"
        else:
            return u"イベント発生時の状況が戦闘以外"

class BranchBattleContent(BranchContent):
    def action(self):
        """バトル分岐コンテント。"""
        if cw.cwpy.battle:
            value = str(cw.cwpy.areaid)
        elif cw.cwpy.winevent_areaid:
            value = str(cw.cwpy.winevent_areaid)
        else:
            value = None

        return self.get_value_index(value)

    def get_status(self):
        return u"バトル分岐コンテント"

    def get_childname(self, child):
        try:
            id = int(child.get("name", ""))
        except:
            id = "Default"

        if id == "Default":
            s = u"その他"
        elif id in cw.cwpy.sdata.battles:
            s = cw.cwpy.sdata.battles[id][0]
        else:
            s = u"指定無し"

        return u"バトル = " + s

class BranchAreaContent(BranchContent):
    def action(self):
        """エリア分岐コンテント。"""
        if cw.cwpy.battle:
            areaid, bgmpath, battlebgmpath = cw.cwpy.pre_battleareadata
            value = str(areaid)
        else:
            value = str(cw.cwpy.areaid)

        return self.get_value_index(value)

    def get_status(self):
        return u"エリア分岐コンテント"

    def get_childname(self, child):
        try:
            id = int(child.get("name", ""))
        except:
            id = "Default"

        if id == "Default":
            s = u"その他"
        elif id in cw.cwpy.sdata.areas:
            s = cw.cwpy.sdata.areas[id][0]
        else:
            s = u"指定無し"

        return u"エリア = " + s

class BranchStatusContent(BranchContent):
    def action(self):
        """状態分岐コンテント。"""
        targetm = self.data.get("targetm")
        status = self.data.get("status")

        # 互換動作: 1.20では状態判定分岐のうち、呪縛・睡眠・中毒・麻痺がずれて判定される
        #           (呪縛→睡眠、睡眠→中毒、中毒→麻痺、麻痺→呪縛)
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint()):
            if status == "Poison":
                status = "Sleep"
            elif status == "Sleep":
                status = "Bind"
            elif status == "Bind":
                status = "Paralyze"
            elif status == "Paralyze":
                status = "Poison"

        methodname = "is_%s" % status.lower()

        # 対象範囲修正
        someone = True

        if targetm == "Random":
            targetm = "Party"
        elif targetm == "Party":
            someone = False

        # 対象メンバ取得
        targets = cw.cwpy.event.get_targetmember(targetm)

        if targets is None:
            # 対象が存在しない場合は無条件に失敗
            return self.get_boolean_index(False)

        if not isinstance(targets, list):
            targets = [targets]

        # 能力判定
        flag = True if targets else False
        selectedmember = None

        for target in targets:
            if hasattr(target, methodname):
                b = getattr(target, methodname)()

                if b and someone:
                    selectedmember = target
                    flag = True
                    break
                elif not b:
                    flag = False

                    if not someone:
                        selectedmember = target
                        break

        # 選択設定
        if not targetm == "Selected":
            if not selectedmember:
                selectedmember = cw.cwpy.event.get_targetmember("Random")

            cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(flag)

    def get_status(self):
        return u"状態分岐コンテント"

    def get_childname(self, child):
        s = self.textdict.get(self.data.get("targetm", "").lower(), "")
        s2 = self.textdict.get(self.data.get("status", "").lower(), "")

        if child.get("name", "") == u"○":
            return u"%sが【%s】の判定に成功" % (s, s2)
        else:
            return u"%sが【%s】の判定に失敗" % (s, s2)

class BranchGossipContent(BranchContent):
    def action(self):
        """ゴシップ分岐コンテント。"""
        gossip = self.data.get("gossip", "")
        flag = cw.cwpy.ydata.has_gossip(gossip)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"ゴシップ分岐コンテント"

    def get_childname(self, child):
        s = self.data.get("gossip", "")

        if child.get("name", "") == u"○":
            return u"ゴシップ『%s』が宿屋にある" % (s)
        else:
            return u"ゴシップ『%s』が宿屋にない" % (s)

class BranchCompleteStampContent(BranchContent):
    def action(self):
        """終了シナリオ分岐コンテント。"""
        scenario = self.data.get("scenario", "")
        flag = cw.cwpy.ydata.has_compstamp(scenario)
        return self.get_boolean_index(flag)

    def get_status(self):
        scenario = self.data.get("scenario", "")

        if scenario:
            return u"終了シナリオ『%s』分岐" % (scenario)
        else:
            return u"終了シナリオが指定されていません"

    def get_childname(self, child):
        s = self.data.get("scenario", "")

        if child.get("name", "") == u"○":
            return u"シナリオ『%s』が終了済である" % (s)
        else:
            return u"シナリオ『%s』が終了済ではない" % (s)

class BranchPartyNumberContent(BranchContent):
    def action(self):
        """パーティ人数分岐コンテント。"""
        value = self.data.getint(".", "value", 0)
        flag = bool(len(cw.cwpy.get_pcards()) >= value)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"人数 = " + self.data.get("value", "0")

    def get_childname(self, child):
        s = self.data.get("value", "0")

        if child.get("name", "") == u"○":
            return u"パーティ人数が%s人以上" % (s)
        else:
            return u"パーティ人数が%s人未満" % (s)

class BranchLevelContent(BranchContent):
    def action(self):
        """レベル分岐コンテント。"""
        average = self.data.getbool(".", "average", False)
        value = self.data.getint(".", "value", 0)

        if average:
            pcards = cw.cwpy.get_pcards("unreversed")
            level = sum([pcard.level for pcard in pcards]) / len(pcards)
        else:
            pcard = cw.cwpy.event.get_targetmember("Selected")
            level = pcard.level

        flag = bool(level >= value)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"レベル分岐コンテント"

    def get_childname(self, child):
        if self.data.getbool(".", "average", False):
            s = u"全員の平均値"
        else:
            s = u"選択中のキャラ"

        if child.get("name", "") == u"○":
            return u"%sがレベル%s以上" % (s, self.data.get("value", ""))
        else:
            return u"%sがレベル%s未満" % (s, self.data.get("value", ""))

class BranchCouponContent(BranchContent):
    def action(self):
        """称号存在分岐コンテント。"""
        coupon = self.data.get("coupon")
        scope = self.data.get("targets")

        # 対象範囲修正
        if scope == "Random":
            scope = "Party"
            someone = True
            unreversed = False
        elif scope == "Party":
            someone = False
            unreversed = True
        elif scope == "Field":
            scope = "FieldCasts"
            someone = True
            unreversed = True
        else:
            someone = True
            unreversed = False

        # 互換動作: 1.20では選択中のメンバがいない状態で
        #           選択中のメンバでの所持判定を行うと
        #           「誰か一人」のように動作する
        if not cw.cwpy.event.has_selectedmember() and scope == "Selected":
            if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint()):
                scope = "Party"

        # 所持判定
        targets = cw.cwpy.event.get_targetscope(scope, unreversed)
        flag = False
        selectedmember = None

        # BUG: CW1.28～1.50のバグ？：判定対象がないと否応なくTrue？
        # 選択メンバで分岐した際に限り、全員隠蔽 = 選択メンバがいないと常に失敗
        # FIXME: 確実な仕様求ム
        if len(targets) == 0:
            return self.get_boolean_index(scope <> "Selected")

        for target in targets:
            if not isinstance(target, list):
                flag = target.has_coupon(coupon)

                if flag and someone:
                    selectedmember = target
                    break
                elif not flag and not someone:
                    selectedmember = target
                    break

        # 選択設定
        if not scope == "Selected":
            if not selectedmember:
                selectedmember = cw.cwpy.event.get_targetmember("Random")

            cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(flag)

    def get_status(self):
        coupon = self.data.get("coupon", "")

        if coupon:
            return u"称号『%s』分岐" % (coupon)
        else:
            return u"称号が指定されていません"

    def get_childname(self, child):
        s = self.data.get("coupon", "")

        if child.get("name", "") == u"○":
            return u"称号『%s』を所有している" % (s)
        else:
            return u"称号『%s』を所有していない" % (s)

class BranchSelectContent(BranchContent):
    def action(self):
        """メンバ選択分岐コンテント。"""
        targetall = self.data.getbool(".", "targetall", True)
        random = self.data.getbool(".", "random", True)

        if targetall:
            pcards = cw.cwpy.get_pcards("unreversed")
        else:
            pcards = cw.cwpy.get_pcards("active")

        index = -1
        if pcards:
            if random:
                pcard = cw.cwpy.dice.choice(pcards)
                cw.cwpy.event.set_selectedmember(pcard)
                index = 0
            else:
                if pcards:
                    mwin = cw.sprite.message.MemberSelectWindow(pcards)
                    index = cw.cwpy.show_message(mwin)

        flag = bool(index == 0)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"選択分岐コンテント"

    def get_childname(self, child):
        if self.data.getbool(".", "targetall", True):
            s = u"パーティ全員から "
        else:
            s = u"動けるメンバから "

        if self.data.getbool(".", "random", True):
            s += u"ランダムで "
        else:
            s += u"手動で "

        if child.get("name", "") == u"○":
            s += u"キャラクターを選択"
        else:
            s += u"の選択をキャンセル"

        return s

class BranchMoneyContent(BranchContent):
    def action(self):
        """所持金存在分岐コンテント。"""
        money = self.data.getint(".", "value", 0)
        flag = bool(cw.cwpy.ydata.party.money >= money)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"金額 = " + self.data.get("value", "0")

    def get_childname(self, child):
        if child.get("name", "") == u"○":
            return self.data.get("value", "0") + u" sp以上所持している"
        else:
            return self.data.get("value", "0") + u" sp以上所持していない"

class BranchFlagContent(BranchContent):
    def action(self):
        """フラグ分岐コンテント。"""
        flag = self.data.get("flag")

        if flag in cw.cwpy.sdata.flags:
            flag = cw.cwpy.sdata.flags[flag]
            index = self.get_boolean_index(flag)
        elif len(self.data.getfind("Contents")):
            # フラグが存在しない場合は
            # 常に最初の子コンテントが選ばれる
            index = 0
        else:
            index = cw.IDX_TREEEND

        return index

    def get_status(self):
        flag = self.data.get("flag")

        if flag in cw.cwpy.sdata.flags:
            return u"フラグ『%s』分岐" % (cw.cwpy.sdata.flags[flag].name)
        else:
            return u"フラグが指定されていません"

    def get_childname(self, child):
        flag = self.data.get("flag")

        if flag in cw.cwpy.sdata.flags:
            if child.get("name", "") == u"○":
                valuename = cw.cwpy.sdata.flags[flag].get_valuename(True)
            else:
                valuename = cw.cwpy.sdata.flags[flag].get_valuename(False)

            return "%s = %s" % (flag, valuename)
        else:
            return u"フラグが指定されていません"

class BranchStepContent(BranchContent):
    def action(self):
        """ステップ上下分岐コンテント。"""
        step = self.data.get("step")
        value = self.data.getint(".", "value", 0)

        if step in cw.cwpy.sdata.steps:
            flag = bool(cw.cwpy.sdata.steps[step].value >= value)
            index = self.get_boolean_index(flag)
        elif len(self.data.getfind("Contents")):
            # ステップｓが存在しない場合は
            # 常に最初の子コンテントが選ばれる
            index = 0
        else:
            index = cw.IDX_TREEEND

        return index

    def get_status(self):
        step = self.data.get("step")

        if step:
            return u"ステップ『%s』分岐" % (step)
        else:
            return u"ステップが指定されていません"

    def get_childname(self, child):
        step = self.data.get("step")
        value = self.data.getint(".", "value", 0)

        if step in cw.cwpy.sdata.steps:
            valuename = cw.cwpy.sdata.steps[step].get_valuename(value)

            if child.get("name", "") == u"○":
                return u"ステップ『%s』が『%s』以上" % (step, valuename)
            else:
                return u"ステップ『%s』が『%s』未満" % (step, valuename)

        else:
            return u"ステップが指定されていません"

class BranchMultiStepContent(BranchContent):
    def action(self):
        """ステップ多岐分岐コンテント。"""
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            value = str(cw.cwpy.sdata.steps[step].value)
            index = self.get_value_index(value)
        elif len(self.data.getfind("Contents")):
            # ステップｓが存在しない場合は
            # 常に最初の子コンテントが選ばれる
            index = 0
        else:
            index = cw.IDX_TREEEND

        return index

    def get_status(self):
        step = self.data.get("step")

        if step:
            return u"ステップ『%s』多岐分岐" % (step)
        else:
            return u"ステップが指定されていません"

    def get_childname(self, child):
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            try:
                value = int(child.get("name", "Default"))
            except:
                value = "Default"

            if value == "Default":
                valuename = u"その他"
            else:
                valuename = cw.cwpy.sdata.steps[step].get_valuename(value)

            return "%s = %s" % (step, valuename)
        else:
            return u"ステップが指定されていません"

class BranchRandomContent(BranchContent):
    def action(self):
        """ランダム分岐コンテント。"""
        value = self.data.getint(".", "value", 0)
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.28", cw.cwpy.sdata.get_versionhint()):
            # 互換動作: 1.28以前のバグで、確率分岐の値が+1になる
            flag = bool(cw.cwpy.dice.roll(1, 100) <= value+1)
        else:
            flag = bool(cw.cwpy.dice.roll(1, 100) <= value)
        return self.get_boolean_index(flag)

    def get_status(self):
        return u"確率 = %s％" % (self.data.get("value", "0"))

    def get_childname(self, child):
        if child.get("name", "") == u"○":
            return self.data.get("value", "") + u" %成功"
        else:
            return self.data.get("value", "") + u" %失敗"

class BranchAbilityContent(BranchContent):
    def action(self):
        """能力判定分岐コンテント。"""
        level = self.data.getint(".", "value", 0)
        vocation = self.data.get("physical"), self.data.get("mental")
        targetm = self.data.get("targetm")

        # 対象範囲修正
        if targetm.endswith("Sleep"):
            targetm = targetm.replace("Sleep", "")
            sleep = True
        else:
            sleep = False

        if targetm == "Random":
            targetm = "Party"
            someone = True
        elif targetm == "Party":
            someone = False
        else:
            someone = True

        # 対象メンバ取得
        targets = cw.cwpy.event.get_targetmember(targetm)

        if not isinstance(targets, list):
            if targets is None:
                targets = []
            else:
                targets = [targets]

        # 死亡・睡眠者は判定から排除
        targets = [target for target in targets
                    if target.is_alive() and (sleep or not target.is_sleep())]

        # 能力判定
        flag = False
        selectedmember = None

        for target in targets:
            flag = target.decide_outcome(level, vocation, enhance=target.get_enhance_act())

            if flag and someone:
                selectedmember = target
                break
            elif not flag and not someone:
                selectedmember = target
                break

        # 選択設定
        if not targetm == "Selected":
            if not selectedmember:
                selectedmember = cw.cwpy.event.get_targetmember("Random")

            cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(flag)

    def get_status(self):
        return u"判定分岐コンテント"

    def get_childname(self, child):
        level = self.data.get("value", "0")
        physical = self.textdict.get(self.data.get("physical").lower())
        mental = self.textdict.get(self.data.get("mental").lower())
        s = u"レベル%sで %sと %sで行う" % (level, physical, mental)

        if child.get("name", "") == u"○":
            s += u"判定に成功"
        else:
            s += u"判定に失敗"

        return s

class BranchRandomSelectContent(BranchContent):
    def action(self):
        """ランダム選択分岐コンテント(1.30)。"""
        minlevel = int(self.data.get("minLevel", "0"))
        maxlevel = int(self.data.get("maxLevel", "0"))
        status = self.data.get("status", "")
        ranges = self.get_castranges()

        if status:
            methodname = "is_%s" % status.lower()

        # 対象メンバ取得
        targets = []
        for scope in ("Party", "Enemy", "Npc"): # 順序はPC→敵→同行NPCに固定
            if scope in ranges:
                targets.extend(cw.cwpy.event.get_targetscope(scope, False))

        # レベル・状態判定
        targets2 = []
        selectedmember = None
        for target in targets:
            if status and not (hasattr(target, methodname) and getattr(target, methodname)()):
                continue
            if 0 < minlevel and target.level < minlevel:
                continue
            if 0 < maxlevel and maxlevel < target.level:
                continue

            targets2.append(target)

        selectedmember = cw.cwpy.dice.choice(targets2)

        # 選択設定
        if selectedmember:
            cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(not selectedmember is None)

    def get_castranges(self):
        ranges = set()
        for e in self.data.getfind("CastRanges"):
            ranges.add(e.gettext(".", ""))
        return ranges

    def get_status(self):
        return u"ランダム選択分岐コンテント"

    def get_childname(self, child):
        minlevel = int(self.data.get("minLevel", "0"))
        maxlevel = int(self.data.get("maxLevel", "0"))
        status = self.data.get("status", "")
        ranges = self.get_castranges()
        if "Party" in ranges and "Enemy" in ranges and "Npc" in ranges:
            s = self.textdict.get("field")
        else:
            s = ""
            for scope in ranges:
                if s:
                    s += u"と"
                s += self.textdict.get(scope.lower(), u"不明な範囲")

        s2 = ""
        if 0 < minlevel:
            s2 += u"レベルが%s～%s" % (minlevel, maxlevel)

        if status:
            if s2:
                s2 += u"で"
            s2 += u"【%s】" % (self.textdict.get(self.data.get("status", "").lower(), ""))

        if child.get("name", "") == u"○":
            return u"%sから%sのキャラクターの選択に成功" % (s, s2)
        else:
            return u"%sから%sのキャラクターの選択に失敗" % (s, s2)

class BranchKeyCodeContent(BranchContent):
    def action(self):
        """キーコード所持分岐コンテント(1.30)。"""
        targetkc = self.data.get("targetkc", "Selected")
        type = self.data.get("effectCardType", "All")
        keycode = self.data.get("keyCode", "")

        # 対象メンバ取得
        targets = []
        if targetkc == "Selected":
            targets.append(cw.cwpy.event.get_targetmember(targetkc))
        elif targetkc == "Random":
            targets.extend(cw.cwpy.event.get_targetmember("Party"))
            cw.cwpy.dice.shuffle(targets)
        elif targetkc == "Backpack":
            targets.append(cw.cwpy.ydata.party)
        elif targetkc == "PartyAndBackpack":
            targets.extend(cw.cwpy.event.get_targetmember("Party"))
            cw.cwpy.dice.shuffle(targets)
            targets.append(cw.cwpy.ydata.party)

        # 対象カード種別
        skill = False
        item = False
        beast = False
        if type == "All":
            skill = True
            item = True
            beast = True
        elif type == "Skill":
            skill = True
        elif type == "Item":
            item = True
        elif type == "Beast":
            beast = True

        # キーコード所持判定
        selectedmember = None
        flag = False
        for target in targets:
            if target.has_keycode(keycode, skill, item, beast):
                if isinstance(target, cw.character.Character):
                    selectedmember = target
                flag = True
                break

        # 選択設定
        if selectedmember:
            cw.cwpy.event.set_selectedmember(selectedmember)

        return self.get_boolean_index(flag)

    def get_status(self):
        return u"キーコード所持分岐コンテント"

    def get_childname(self, child):
        targetkc = self.data.get("targetkc", "Selected")
        type = self.data.get("effectCardType", "All")
        keycode = self.data.get("keyCode", "")

        s = self.textdict.get(targetkc.lower(), "")
        s2 = self.textdict.get(type.lower(), "")
        s3 = keycode

        if child.get("name", "") == u"○":
            return u"%sの%sからキーコード『%s』の発見に成功" % (s, s2, s3)
        else:
            return u"%sの%sからキーコード『%s』の発見に失敗" % (s, s2, s3)

class BranchRoundContent(BranchContent):
    def action(self):
        """ラウンド分岐コンテント(1.50)。"""
        round1 = int(self.data.get("round", "1"))
        comparison = self.data.get("comparison")

        flag = False
        if cw.cwpy.is_battlestatus():
            round2 = cw.cwpy.battle.round
            if comparison == "=":
                flag = (round1 == round2)
            elif comparison == "<":
                flag = (round1 < round2)
            elif comparison == ">":
                flag = (round1 > round2)

        return self.get_boolean_index(flag)

    def get_status(self):
        return u"ラウンド分岐コンテント"

    def get_childname(self, child):
        round = int(self.data.get("round", "1"))
        comparison = self.data.get("comparison")

        if child.get("name", "") == u"○":
            return u"%s %s 現在のバトルラウンドである" % (round, comparison)
        else:
            return u"%s %s 現在のバトルラウンドでない" % (round, comparison)

#-------------------------------------------------------------------------------
# Call系コンテント
#-------------------------------------------------------------------------------

class CallStartContent(EventContentBase):
    def action(self):
        """スタートコールコンテント。
        別のスタートコンテントのツリーイベントをコールする。
        """
        startname = self.data.get("call")
        event = cw.cwpy.event.get_event()
        trees = cw.cwpy.event.get_trees()

        if startname in trees:
            event = cw.cwpy.event.get_event()
            if event.nowrunningcontents or 0 < len(self.data.find("Contents")):
                if cw.LIMIT_RECURSE <= cw.cwpy.event.get_currentstack():
                    s = u"イベントの呼び出しが%s層を超えたので処理を中止します。スタートやパッケージのコールによってイベントが無限ループになっていないか確認してください。" % (cw.LIMIT_RECURSE)
                    cw.cwpy.call_modaldlg("ERROR", text=s)
                    raise cw.event.EffectBreakError()
                event.nowrunningcontents.append((None, event.cur_content, None))
            event.cur_content = trees[startname]

        return 0

    def get_status(self):
        startname = self.data.get("call")

        if startname:
            return u"スタートコンテント『%s』のコール" % (startname)
        else:
            return u"スタートコンテントが指定されていません"

class CallPackageContent(EventContentBase):
    def action(self):
        """パッケージコールコンテント。
        パッケージのツリーイベントをコールする。
        """
        id = self.data.getint(".", "call", 0)
        event = cw.cwpy.event.get_event()
        call_package(id, event.nowrunningcontents or 0 < len(self.data.find("Contents")))
        return 0

    def get_status(self):
        id = self.data.getint(".", "call", 0)

        if id and id in cw.cwpy.sdata.packs:
            return u"パッケージ『%s』コール" % (cw.cwpy.sdata.packs[id][0])
        else:
            return u"パッケージが指定されていません"

def call_package(id, call):
    """パッケージを実行する。
    call: コールならTrue、リンクならFalse。
    """
    if not (id and id in cw.cwpy.sdata.packs):
        return

    if not id in cw.cwpy.event.nowrunningpacks:
        path = cw.cwpy.sdata.packs[id][1]
        data = cw.data.xml2etree(path)
        versionhint = data.getattr("Property", "versionHint", "")
        e = data.find("Events/Event")
        if e is None:
            return 0
        cw.cwpy.event.nowrunningpacks[id] = e, versionhint
    else:
        e, versionhint = cw.cwpy.event.nowrunningpacks[id]

    packevent = cw.event.Event(e)
    if packevent.starttree is None:
        return

    if not cw.cwpy.event.get_event():
        # 実行中のイベントが無い場合は直接実行する
        cw.cwpy.event.append_event(packevent)
        cw.cwpy.event.get_event().start()
        return

    event = cw.cwpy.event.get_event()
    versionhint_base = cw.cwpy.sdata.versionhint[cw.HINT_AREA]
    if call:
        event.nowrunningcontents.append((packevent, event.cur_content, versionhint_base))
        cw.cwpy.event.append_event(packevent)
    else:
        cw.cwpy.event.replace_event(packevent)
        event = cw.cwpy.event.get_event()
    event.cur_content = packevent.starttree
    if cw.cwpy.is_playingscenario():
        cw.cwpy.sdata.versionhint[cw.HINT_AREA] = versionhint

#-------------------------------------------------------------------------------
# Change系コンテント
#-------------------------------------------------------------------------------

class ChangeBgImageContent(EventContentBase):
    def action(self):
        """背景変更コンテント。"""
        e = self.data.getfind("BgImages")
        elements = cw.cwpy.sdata.get_bgdata(e)
        bginhrt = cw.cwpy.sdata.check_bginhrt(elements)
        ttype = self.get_transitiontype()
        cw.cwpy.background.load(elements, bginhrt, True, ttype)
        # フレームを進める
        cw.cwpy.draw()
        cw.cwpy.tick_clock(framerate=30)
        cw.cwpy.input()
        cw.cwpy.eventhandler.run()
        while pygame.event.peek(pygame.locals.USEREVENT):
            # ユーザ操作によりスケール変更のイベントが発生する可能性があるため
            # 後続のイベントへ進む前に全て消化
            cw.cwpy.input()
            cw.cwpy.eventhandler.run()
        return 0

    def get_status(self):
        elements = self.data.getfind("BgImages").getchildren()

        if elements:
            path = elements[0].gettext("ImagePath", "")
        else:
            path = ""

        return u"背景ファイル = 【%s】" % (path)

class ChangeAreaContent(EventContentBase):
    def action(self):
        """エリア変更コンテント。"""
        id = self.data.getint(".", "id", 0)
        ttype = self.get_transitiontype()

        if id and id in cw.cwpy.sdata.areas:
            cw.cwpy.exec_func(cw.cwpy.change_area, id, ttype=ttype)
            cw.cwpy._dealing = True
            raise cw.event.AreaChangeError()
        else:
            raise cw.event.EffectBreakError()

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.areas:
            return u"エリア『%s』へ移動" % (cw.cwpy.sdata.areas[id][0])
        else:
            return u"エリアが指定されていません"

#-------------------------------------------------------------------------------
# Check系コンテント
#-------------------------------------------------------------------------------

class CheckFlagContent(EventContentBase):
    def action(self):
        """フラグ判定コンテント。"""
        flag = self.data.get("flag")

        if cw.cwpy.sdata.flags.get(flag, False):
            return 0
        else:
            return cw.IDX_TREEEND

    def get_status(self):
        flag = self.data.get("flag")

        if flag:
            return u"フラグ『%s』の値で判定" % (flag)
        else:
            return u"フラグが指定されていません"

class CheckStepContent(EventContentBase):
    def action(self):
        """ステップ判定コンテント(1.50)。"""
        step = self.data.get("step")
        value1 = self.data.getint(".", "value", 0)
        comparison = self.data.get("comparison")

        if step in cw.cwpy.sdata.steps:
            value2 = cw.cwpy.sdata.steps[step].value
            if comparison == "=":
                if value1 == value2:
                    return 0
            elif comparison == "<>":
                if value1 <> value2:
                    return 0
            elif comparison == "<":
                if value1 < value2:
                    return 0
            elif comparison == ">":
                if value1 > value2:
                    return 0

        return cw.IDX_TREEEND

    def get_status(self):
        step = self.data.get("step")
        value1 = self.data.getint(".", "value", 0)
        comparison = self.data.get("comparison")

        if step:
            return u"%s %s ステップ『%s』" % (value1, comparison, step)
        else:
            return u"ステップが指定されていません"

#-------------------------------------------------------------------------------
# Effect系コンテント
#-------------------------------------------------------------------------------

class EffectContent(EventContentBase):
    def action(self):
        """効果コンテント。"""
        # 各種データ取得
        d = {}
        d["level"] = self.data.getint(".", "level", 0)
        d["successrate"] = self.data.getint(".", "successrate", 0)
        d["effecttype"] = self.data.get("effecttype", "Physic")
        d["resisttype"] = self.data.get("resisttype", "Avoid")
        d["soundpath"] = self.data.get("sound", "")
        d["visualeffect"] = self.data.get("visual", "None")

        # Effectインスタンス作成
        motions = self.data.getfind("Motions").getchildren()
        eff = cw.effectmotion.Effect(motions, d)

        # 対象メンバ取得
        targetm = self.data.get("targetm", "Selected")
        target = cw.cwpy.event.get_targetmember(targetm)

        # 対象メンバに効果モーションを適用
        if isinstance(target, list):
            for member in target:
                eff.apply(member, event=True)

        else:
            eff.apply(target, event=True)

        if cw.cwpy.is_gameover():
            # 効果中断。引き続き
            # ゲームオーバーイベントが発生する。
            raise cw.event.EffectBreakError()

        return 0

    def get_status(self):
        return u"効果コンテント"

class EffectBreakContent(EventContentBase):
    def action(self):
        """効果中断コンテント。"""
        raise cw.event.EffectBreakError()

    def get_status(self):
        return u"効果中断コンテント"

#-------------------------------------------------------------------------------
# Elapse系コンテント
#-------------------------------------------------------------------------------

class ElapseTimeContent(EventContentBase):
    def action(self):
        """ターン数経過コンテント。"""
        cw.cwpy.elapse_time()
        return 0

    def get_status(self):
        return u"ターン数経過コンテント"

#-------------------------------------------------------------------------------
# End系コンテント
#-------------------------------------------------------------------------------

class EndContent(EventContentBase):
    def action(self):
        """シナリオ終了コンテント。
        宿画面に遷移する。completeがTrueだったら済み印をつける。
        """
        complete = self.data.getbool(".", "complete", False)

        if cw.cwpy.battle and cw.cwpy.battle.is_running:
            # バトルを強制終了
            cw.cwpy.battle.end(False, True)

        # 使用時イベント等ではズームインしている
        # PCがいる可能性があるのでズームアウト
        for pcard in cw.cwpy.get_pcards():
            if pcard.zoomimgs:
                cw.animation.animate_sprite(pcard, "zoomout")
        cw.cwpy.clear_inusecardimg()
        cw.cwpy.clear_guardcardimg()

        # メニューカード全て非表示
        cw.cwpy.hide_cards(True)

        # 時限クーポン削除
        for pcard in cw.cwpy.get_pcards():
            pcard.remove_timedcoupons()

        for fcard in cw.cwpy.get_fcards():
            fcard.remove_timedcoupons()

        # パーティ表示
        cw.cwpy.show_party()

        # 終了印の処理
        if complete:
            elements = [e for e in
                        cw.cwpy.ydata.environment.getfind("CompleteStamps")
                                            if e.text == cw.cwpy.sdata.name]
            # 同名の終了印がなかったら終了印追加
            if not elements:
                name = "CompleteStamp"
                text = cw.cwpy.sdata.name
                e = cw.cwpy.ydata.environment.make_element(name, text)
                cw.cwpy.ydata.environment.append("CompleteStamps", e)

        # NPCの連れ込み
        cw.cwpy.ydata.join_npcs()

        # レベルアップと回復処理
        cw.cwpy.check_level(fromscenario=True)

        # 特殊文字の辞書が変更されていたら、元に戻す
        if cw.cwpy.rsrc.specialchars_is_changed:
            cw.cwpy.rsrc.specialchars = cw.cwpy.rsrc.get_specialchars()

        cw.cwpy.sdata.end()
        cw.cwpy.ydata.party.write()

        # BGMストップ
        cw.cwpy.music.stop()

        # 宿画面に遷移
        cw.cwpy.exec_func(cw.cwpy.set_yado)
        cw.cwpy._dealing = True
        raise cw.event.ScenarioEndError()

    def get_status(self):
        complete = self.data.getbool(".", "complete", False)

        if complete:
            return u"済印をつけて終了"
        else:
            return u"済印をつけずに終了"

class EndBadEndContent(EventContentBase):
    def action(self):
        """シナリオ終了コンテント。
        ゲームオーバ画面に遷移する。
        """
        cw.cwpy.exec_func(cw.cwpy.set_gameover)
        raise cw.event.ScenarioBadEndError()

    def get_status(self):
        return u"ゲームオーバー"

#-------------------------------------------------------------------------------
# Get系コンテント
#-------------------------------------------------------------------------------

class GetContent(EventContentBase):
    def get_cards(self, cardtype):
        """対象範囲のインスタンスに設定枚数のカードを配布する。
        cardtype: "SkillCard" or "ItemCard" or "BeastCard"
        """
        # 各種属性値取得
        id = self.data.getint(".", "id", 0)
        num = self.data.getint(".", "number", 0)
        scope = self.data.get("targets")

        # 適用範囲が"フィールド全体"or"全体(荷物袋含む)"の場合、"荷物袋"に変更
        if scope in ("Field", "PartyAndBackpack"):
            scope = "Backpack"

        # 対象カードのxmlファイルのパス
        if cardtype == "SkillCard":
            path = cw.cwpy.sdata.skills.get(id, ("", ""))[1]
        elif cardtype == "ItemCard":
            path = cw.cwpy.sdata.items.get(id, ("", ""))[1]
        elif cardtype == "BeastCard":
            path = cw.cwpy.sdata.beasts.get(id, ("", ""))[1]
        else:
            raise ValueError("%s is invalid cardtype" % cardtype)

        if not path:
            return

        for cnt in xrange(num):
            for target in cw.cwpy.event.get_targetscope(scope):
                etree = cw.data.xml2etree(path, nocache=True)
                get_card(etree, target, from_getcontent=True)

def get_card(etree, target, notscenariocard=False, toindex=-1, insertorder=-1, party=None, copymaterialfrom="", fromdebugger=False, from_getcontent=False):
    """対象インスタンスにカードを配布する。cwpy.trade()参照。
    etree: ElementTree or Element
    target: Character or list(Backpack, Storehouse)
    summon: 召喚かどうか。付帯召喚設定は強制的にクリアされる。
    """
    # 対象カード名取得
    name = etree.gettext("Property/Name", "noname")
    name = cw.util.repl_dischar(name)

    # シナリオ取得フラグ
    if notscenariocard:
        from_scenario = False
    else:
        from_scenario = True
        etree.getroot().attrib["scenariocard"] = "True"

    # 召喚獣カードの場合、付帯属性を操作する
    # 召喚獣獲得コンテントないしデバッガからの配布であれば、必ず付帯能力に
    if etree.getroot().tag == "BeastCard":
        if not notscenariocard or fromdebugger:
            s = "True"
        else:
            if etree.gettext("Property/UseLimit") == "0":
                etree.edit("Property/UseLimit", "1")

            s = "False"

        if etree.hasfind("Property/Attachment"):
            etree.edit("Property/Attachment", s)
        else:
            e = etree.make_element("Attachment", s)
            etree.append("Property", e)

    # カード移動操作
    if cw.cwpy.ydata.storehouse is target:
        targettype = "STOREHOUSE"
    elif isinstance(target, list):
        targettype = "BACKPACK"
    else:
        targettype = "PLAYERCARD"

    header = cw.header.CardHeader(carddata=etree.getroot(),
                                    owner=None, from_scenario=from_scenario)

    if copymaterialfrom:
        if from_scenario:
            # F9時に破棄しなければならないので
            # ImagePathの取り込みに留める
            for e2 in etree.getiterator():
                if e2.tag == "ImagePath" and e2.text and not cw.binary.image.path_is_code(e2.text):
                    path = cw.util.join_paths(copymaterialfrom, e2.text)
                    if os.path.isfile(path):
                        with open(path, "rb") as f:
                            imagedata = f.read()
                        e2.text = cw.binary.image.data_to_code(imagedata)
                        header.imgpath = e2.text
        else:
            # 素材ファイルコピー
            dstdir = cw.util.join_paths(cw.cwpy.ydata.yadodir,
                                        "Material", header.type, name)
            dstdir = cw.util.dupcheck_plus(dstdir)
            cw.cwpy.copy_materials(etree, dstdir, True, copymaterialfrom)
            header.imgpath = etree.gettext("Property/ImagePath", header.imgpath)

    cw.cwpy.trade(targettype, target, header=header, from_event=True, toindex=toindex, insertorder=insertorder, sort=False, party=party, from_getcontent=from_getcontent)

class GetSkillContent(GetContent):
    def action(self):
        """スキル取得コンテント。"""
        self.get_cards("SkillCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.skills:
            return u"特殊技能カード『%s』取得" % (cw.cwpy.sdata.skills[id][0])
        else:
            return u"特殊技能カードが指定されていません"

class GetItemContent(GetContent):
    def action(self):
        """アイテム取得コンテント。"""
        self.get_cards("ItemCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.items:
            return u"アイテムカード『%s』取得" % (cw.cwpy.sdata.items[id][0])
        else:
            return u"アイテムカードが指定されていません"

class GetBeastContent(GetContent):
    def action(self):
        """召喚獣取得コンテント。"""
        self.get_cards("BeastCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.beasts:
            return u"召喚獣カード『%s』取得" % (cw.cwpy.sdata.beasts[id][0])
        else:
            return u"召喚獣カードが指定されていません"

class GetCastContent(GetContent):
    def action(self):
        """キャスト加入コンテント。"""
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.casts:
            fcards = [i for i in cw.cwpy.sdata.friendcards if i.id == id]

            if not fcards and len(cw.cwpy.sdata.friendcards) < 6:
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                fcard = cw.sprite.card.FriendCard(id)
                cw.cwpy.sdata.friendcards.append(fcard)
                if cw.cwpy.is_battlestatus() and fcard.is_alive():
                    # 即戦闘に参加する
                    cw.cwpy.battle.members.append(fcard)
                    fcard.decide_action()

        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.casts:
            return u"キャストカード『%s』加入" % (cw.cwpy.sdata.casts[id][0])
        else:
            return u"キャストカードが指定されていません"

class GetInfoContent(GetContent):
    def action(self):
        """情報入手コンテント。"""
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.infos:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            headers = [h for h in cw.cwpy.sdata.infocards if h.id == id]

            if headers:
                header = headers[0]
                cw.cwpy.sdata.infocards.remove(header)
            else:
                path = cw.cwpy.sdata.infos[id][1]
                e = cw.data.xml2element(path, "Property")
                header = cw.header.InfoCardHeader(e)

            cw.cwpy.sdata.infocards.insert(0, header)

        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id and id in cw.cwpy.sdata.infos:
            return u"情報カード『%s』入手" % (cw.cwpy.sdata.infos[id][0])
        else:
            return u"情報カードが指定されていません"

class GetMoneyContent(GetContent):
    def action(self):
        """所持金取得コンテント"""
        value = self.data.getint(".", "value", 0)
        cw.cwpy.ydata.party.set_money(value)
        return 0

    def get_status(self):
        value = self.data.get("value", "0")
        return u"%ssp取得" % (value)

class GetCompleteStampContent(GetContent):
    def action(self):
        """終了シナリオ印取得コンテント。"""
        scenario = self.data.get("scenario")

        if scenario:
            cw.cwpy.ydata.set_compstamp(scenario)

        return 0

    def get_status(self):
        scenario = self.data.get("scenario")

        if scenario:
            return u"終了済みシナリオ『%s』追加" % (scenario)
        else:
            return u"終了済みシナリオが指定されていません"

class GetGossipContent(GetContent):
    def action(self):
        """ゴシップ取得コンテント。"""
        gossip = self.data.get("gossip")

        if gossip:
            cw.cwpy.ydata.set_gossip(gossip)

        return 0

    def get_status(self):
        gossip = self.data.get("gossip")

        if gossip:
            return u"ゴシップ『%s』取得" % (gossip)
        else:
            return u"ゴシップが指定されていません"

class GetCouponContent(GetContent):
    def action(self):
        """称号付与コンテント。"""
        coupon = self.data.get("coupon")
        value = self.data.get("value")
        scope = self.data.get("targets")

        # "＠"で始まるクーポンは付与しない
        if coupon and not coupon.startswith(u"＠"):
            targets = cw.cwpy.event.get_targetscope(scope, False)

            for target in targets:
                if isinstance(target, cw.character.Character):
                    target.set_coupon(coupon, value)

        return 0

    def get_status(self):
        coupon = self.data.get("coupon")

        if coupon:
            return u"称号『%s』付与" % (coupon)
        else:
            return u"称号が指定されていません"

#-------------------------------------------------------------------------------
# hide系コンテント
#-------------------------------------------------------------------------------

class HidePartyContent(EventContentBase):
    def action(self):
        """パーティ非表示コンテント。"""
        cw.cwpy.hide_party()
        return 0

    def get_status(self):
        return u"パーティ非表示コンテント"

#-------------------------------------------------------------------------------
# Link系コンテント
#-------------------------------------------------------------------------------

class LinkStartContent(EventContentBase):
    def action(self):
        """別のスタートコンテントのツリーイベントに移動する。"""
        startname = self.data.get("link")
        event = cw.cwpy.event.get_event()
        trees = cw.cwpy.event.get_trees()

        if startname in trees:
            event.cur_content = trees[startname]

        return 0

    def get_status(self):
        startname = self.data.get("link")

        if startname:
            return u"スタートコンテント『%s』へのリンク" % (startname)
        else:
            return u"スタートコンテントが指定されていません"

class LinkPackageContent(EventContentBase):
    def action(self):
        """パッケージのツリーイベントに移動する。"""
        id = self.data.getint(".", "link", 0)
        event = cw.cwpy.event.get_event()
        call_package(id, not event.nowrunningcontents is None)
        return 0

    def get_status(self):
        id = self.data.getint(".", "link", 0)

        if id in cw.cwpy.sdata.packs:
            return u"パッケージビュー『%s』" % (cw.cwpy.sdata.packs[id][0])
        else:
            return u"パッケージが指定されていません"

#-------------------------------------------------------------------------------
# Lose系コンテント
#-------------------------------------------------------------------------------

class LoseContent(EventContentBase):
    def lose_cards(self, cardtype):
        """対象範囲のインスタンスに設定枚数のカードを削除する。
        numが0の場合は全対象カード削除。
        cardtype: "SkillCard" or "ItemCard" or "BeastCard"
        """
        # 各種属性値取得
        id = self.data.getint(".", "id", 0)
        num = self.data.getint(".", "number", 0)
        scope = self.data.get("targets")

        # 対象カードのxmlファイルのパス
        if cardtype == "SkillCard":
            path = cw.cwpy.sdata.skills.get(id, ("", ""))[1]
            index = cw.POCKET_SKILL
        elif cardtype == "ItemCard":
            path = cw.cwpy.sdata.items.get(id, ("", ""))[1]
            index = cw.POCKET_ITEM
        elif cardtype == "BeastCard":
            path = cw.cwpy.sdata.beasts.get(id, ("", ""))[1]
            index = cw.POCKET_BEAST
        else:
            raise ValueError("%s is invalid cardtype" % cardtype)

        if not path:
            return

        # 対象カードデータ取得
        e = cw.data.xml2element(path, "Property")
        name = e.gettext("Name", "")
        desc = e.gettext("Description", "")
        if num == 0:
            num = 0x7fffffff

        for target in cw.cwpy.event.get_targetscope(scope):
            ccard = target
            if isinstance(target, cw.character.Character):
                target = target.get_pocketcards(index)

            headers, losenum = self.lose_card(name, desc, target, num)
            num -= losenum
            if num <= 0:
                break

    def lose_card(self, name, desc, target, num):
        headers = []

        for h in target:
            if h.name == name and h.desc == desc:
                headers.append(h)

        # カード削除(numが0の場合は全て削除)
        lose = False
        if headers:
            if num == 0:
                num = len(headers)
            else:
                num = cw.util.numwrap(num, 1, len(headers))

            for header in headers[:num]:
                cw.cwpy.trade("TRASHBOX", header=header, from_event=True, sort=False)
                lose = True
        else:
            num = 0

        return headers, num

class LoseSkillContent(LoseContent):
    def action(self):
        """スキル喪失コンテント。"""
        self.lose_cards("SkillCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.skills:
            name = cw.cwpy.sdata.skills[id][0]
            return u"特殊技能カード『%s』喪失" % (name)
        else:
            return u"特殊技能カードが指定されていません"

class LoseItemContent(LoseContent):
    def action(self):
        """アイテム喪失コンテント。"""
        self.lose_cards("ItemCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.items:
            name = cw.cwpy.sdata.items[id][0]
            return u"アイテムカード『%s』喪失" % (name)
        else:
            return u"アイテムカードが指定されていません"

class LoseBeastContent(LoseContent):
    def action(self):
        """召喚獣喪失コンテント。"""
        self.lose_cards("BeastCard")
        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.beasts:
            name = cw.cwpy.sdata.beasts[id][0]
            return u"召喚獣カード『%s』喪失" % (name)
        else:
            return u"召喚獣カードが指定されていません"

class LoseCastContent(LoseContent):
    def action(self):
        """キャスト離脱コンテント。"""
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.casts:
            fcards = [i for i in cw.cwpy.sdata.friendcards if i.id == id]

            if fcards:
                if cw.cwpy.ydata:
                    cw.cwpy.ydata.changed()
                if cw.cwpy.is_battlestatus() and fcards[0] in cw.cwpy.battle.members:
                    cw.cwpy.battle.members.remove(fcards[0])
                    fcards[0].clear_action()
                cw.cwpy.sdata.friendcards.remove(fcards[0])

        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.casts:
            name = cw.cwpy.sdata.casts[id][0]
            return u"キャストカード『%s』離脱" % (name)
        else:
            return u"キャストカードが指定されていません"

class LoseInfoContent(LoseContent):
    def action(self):
        """情報喪失コンテント。"""
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.infos:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            headers = [h for h in cw.cwpy.sdata.infocards if h.id == id]

            if headers:
                cw.cwpy.sdata.infocards.remove(headers[0])

        return 0

    def get_status(self):
        id = self.data.getint(".", "id", 0)

        if id in cw.cwpy.sdata.infos:
            name = cw.cwpy.sdata.infos[id][0]
            return u"情報カード『%s』喪失" % (name)
        else:
            return u"情報カードが指定されていません"

class LoseMoneyContent(LoseContent):
    def action(self):
        """所持金減少コンテント。"""
        value = self.data.getint(".", "value", 0)
        cw.cwpy.ydata.party.set_money(-value)
        return 0

    def get_status(self):
        value = self.data.get("value", "0")
        return u"%ssp減少" % (value)

class LoseCompleteStampContent(LoseContent):
    def action(self):
        """終了シナリオ削除。"""
        scenario = self.data.get("scenario", "")

        if scenario:
            cw.cwpy.ydata.remove_compstamp(scenario)

        return 0

    def get_status(self):
        scenario = self.data.get("scenario", "")

        if scenario:
            return u"終了済みシナリオ『%s』削除" % (scenario)
        else:
            return u"終了シナリオが指定されていません"

class LoseGossipContent(LoseContent):
    def action(self):
        """ゴシップ削除コンテント。"""
        gossip = self.data.get("gossip", "")

        if gossip:
            cw.cwpy.ydata.remove_gossip(gossip)

        return 0

    def get_status(self):
        gossip = self.data.get("gossip", "")

        if gossip:
            return u"ゴシップ『%s』削除" % (gossip)
        else:
            return u"ゴシップが指定されていません"

class LoseCouponContent(LoseContent):
    def action(self):
        """称号剥奪コンテント。"""
        coupon = self.data.get("coupon")
        scope = self.data.get("targets")

        # "＠"で始まるクーポンは剥奪しない
        if coupon and not coupon.startswith(u"＠"):
            targets = cw.cwpy.event.get_targetscope(scope, False)

            for target in targets:
                if isinstance(target, cw.character.Character):
                    target.remove_coupon(coupon)

        return 0

    def get_status(self):
        coupon = self.data.get("coupon")

        if coupon:
            return u"称号『%s』剥奪" % (coupon)
        else:
            return u"称号が指定されていません"

#-------------------------------------------------------------------------------
# Play系コンテント
#-------------------------------------------------------------------------------

class PlayBgmContent(EventContentBase):
    def action(self):
        """BGMコンテント。"""
        path = self.data.get("path", "")
        cw.cwpy.music.play(path)
        return 0

    def get_status(self):
        path = self.data.get("path", "")

        if path:
            return u"BGMを【%s】へ変更" % (path)
        else:
            return u"BGMが指定されていません"

class PlaySoundContent(EventContentBase):
    def action(self):
        """効果音コンテント。"""
        path = self.data.get("path", "")
        cw.cwpy.play_sound(path)
        return 0

    def get_status(self):
        path = self.data.get("path", "")

        if path:
            return u"効果音【%s】を鳴らす" % (path)
        else:
            return u"効果音が指定されていません"

#-------------------------------------------------------------------------------
# Redisplay系コンテント
#-------------------------------------------------------------------------------

class RedisplayContent(EventContentBase):
    def action(self):
        """画面再構築コンテント。"""
        ttype = self.get_transitiontype()
        cw.cwpy.background.reload(True, ttype)
        # フレームを進める
        cw.cwpy.draw()
        cw.cwpy.tick_clock(framerate=30)
        cw.cwpy.input()
        cw.cwpy.eventhandler.run()
        while pygame.event.peek(pygame.locals.USEREVENT):
            # ユーザ操作によりスケール変更のイベントが発生する可能性があるため
            # 後続のイベントへ進む前に全て消化
            cw.cwpy.input()
            cw.cwpy.eventhandler.run()
        return 0

    def get_status(self):
        return u"画面再構築コンテント"

#-------------------------------------------------------------------------------
# Reverse系コンテント
#-------------------------------------------------------------------------------

class ReverseFlagContent(EventContentBase):
    def action(self):
        """フラグ反転コンテント。"""
        flag = self.data.get("flag")

        if flag in cw.cwpy.sdata.flags:
            flag = cw.cwpy.sdata.flags[flag]
            flag.reverse()
            flag.redraw_cards()

        return 0

    def get_status(self):
        flag = self.data.get("flag")

        if flag in cw.cwpy.sdata.flags:
            return u"フラグ『%s』の値を反転" % (flag)
        else:
            return u"フラグが指定されていません"

#-------------------------------------------------------------------------------
# Set系コンテント
#-------------------------------------------------------------------------------

class SetFlagContent(EventContentBase):
    def action(self):
        """フラグ変更コンテント。"""
        flag = self.data.get("flag")
        value = self.data.getbool(".", "value", False)

        if flag in cw.cwpy.sdata.flags:
            flag = cw.cwpy.sdata.flags[flag]
            flag.set(value)
            flag.redraw_cards()

        return 0

    def get_status(self):
        flag = self.data.get("flag")
        value = self.data.getbool(".", "value", False)

        if flag in cw.cwpy.sdata.flags:
            s = cw.cwpy.sdata.flags[flag].get_valuename(value)
            return u"フラグ『%s』を【%s】に変更" % (flag, s)
        else:
            return u"フラグが指定されていません"

class SetStepContent(EventContentBase):
    def action(self):
        """ステップ変更コンテント。"""
        step = self.data.get("step")
        value = self.data.getint(".", "value", 0)

        if step in cw.cwpy.sdata.steps:
            cw.cwpy.sdata.steps[step].set(value)

        return 0

    def get_status(self):
        step = self.data.get("step")
        value = self.data.getint(".", "value", 0)

        if step in cw.cwpy.sdata.steps:
            s = cw.cwpy.sdata.steps[step].get_valuename(value)
            return u"ステップ『%s』を【%s】に変更" % (step, s)
        else:
            return u"ステップが指定されていません"

class SetStepUpContent(EventContentBase):
    def action(self):
        """ステップ増加コンテント。"""
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            cw.cwpy.sdata.steps[step].up()

        return 0

    def get_status(self):
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            return u"ステップ『%s』の値を1増加" % (step)
        else:
            return u"ステップが指定されていません"

class SetStepDownContent(EventContentBase):
    def action(self):
        """ステップ減少コンテント。"""
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            cw.cwpy.sdata.steps[step].down()

        return 0

    def get_status(self):
        step = self.data.get("step")

        if step in cw.cwpy.sdata.steps:
            return u"ステップ『%s』の値を1現象" % (step)
        else:
            return u"ステップが指定されていません"

#-------------------------------------------------------------------------------
# Show系コンテント
#-------------------------------------------------------------------------------

class ShowPartyContent(EventContentBase):
    def action(self):
        """パーティ表示コンテント。"""
        cw.cwpy.show_party()
        return 0

    def get_status(self):
        return u"パーティ表示コンテント"

#-------------------------------------------------------------------------------
# Start系コンテント
#-------------------------------------------------------------------------------

class StartContent(EventContentBase):
    """スタートコンテント"""
    def get_status(self):
        return u"スタートコンテント: " + self.data.get("name", "")

class StartBattleContent(StartContent):
    def action(self):
        """
        バトル開始コンテント。
        """
        areaid = self.data.getint(".", "id", 0)

        if areaid in cw.cwpy.sdata.battles:
            cw.cwpy.exec_func(cw.cwpy.change_battlearea, areaid)
            cw.cwpy._dealing = True
            raise cw.event.StartBattleError()
        else:
            return 0

    def get_status(self):
        areaid = self.data.getint(".", "id", 0)

        if areaid in cw.cwpy.sdata.battles:
            return u"バトルビュー『%s』" % (cw.cwpy.sdata.areas[areaid][0])
        else:
            return u"バトルエリアが指定されていません"

#-------------------------------------------------------------------------------
# Talk系コンテント
#-------------------------------------------------------------------------------

class TalkContent(EventContentBase):
    def get_selections_and_indexes(self):
        """メッセージウィンドウの選択肢データ(index, name)のリストを返す。"""
        seq = []

        index = 0
        for e in self.data.getfind("Contents"):
            name = e.get("name")

            if name:
                # フラグ判定コンテントの場合、対応フラグがTrueだったら選択肢追加
                if e.tag == "Check":
                    type = e.get("type")
                    if type == "Flag":
                        if CheckFlagContent(e).action() == 0:
                            seq.append((index, name))
                            index += 1
                    elif type == "Step":
                        if CheckStepContent(e).action() == 0:
                            seq.append((index, name))
                            index += 1

                else:
                    seq.append((index, name))
                    index += 1
            else:
                # 選択できないが後続コンテントとしては存在する
                index += 1

        if not seq:
            seq = [(0, cw.cwpy.msgs["ok"])]

        return seq

class TalkMessageContent(TalkContent):
    def action(self):
        """メッセージコンテント。"""
        # テキスト取得
        text = self.data.gettext("Text", "")
        # 選択肢取得
        names = self.get_selections_and_indexes()
        # 画像パス取得
        imgpath = self.data.get("path", "")
        talkeriscard = False

        # ランダム
        if imgpath.endswith("??Random"):
            talker = cw.cwpy.event.get_targetmember("Random")
        # 選択中メンバ
        elif imgpath.endswith("??Selected"):
            talker = cw.cwpy.event.get_targetmember("Selected")
        # 選択外メンバ
        elif imgpath.endswith("??Unselected"):
            talker = cw.cwpy.event.get_targetmember("Unselected")

            # 選択外メンバがいなかったらスキップ
            if not talker:
                return 0

        # 使用中カード
        elif imgpath.endswith("??Card"):
            talker = cw.cwpy.event.get_targetmember("Inusecard")
            talkeriscard = True

            # 使用中カードがなかったらスキップ
            if not talker:
                return 0

        # その他
        else:
            talker = None

        if talker:
            imgpath = talker.imgpath
            if talkeriscard:
                if not cw.binary.image.path_is_code(imgpath) and\
                        (not hasattr(talker, "scenariocard") or not talker.scenariocard):
                    imgpath = cw.util.join_yadodir(imgpath)
        elif imgpath:
            inusepath = cw.util.get_inusecardmaterialpath(imgpath)
            if os.path.isfile(inusepath):
                imgpath = inusepath
            elif cw.cwpy.is_playingscenario() and not cw.cwpy.areaid < 0:
                imgpath = cw.util.join_paths(cw.cwpy.sdata.scedir, imgpath)
            else:
                imgpath = cw.util.join_paths(cw.cwpy.skindir, imgpath)

        # MessageWindow表示
        if text:
            mwin = cw.sprite.message.MessageWindow(text, names, imgpath, talker)
            index = cw.cwpy.show_message(mwin)
        # テキストが存在せず、選択肢が複数存在する場合はSelectWindowを表示する
        elif len(names) > 1:
            mwin = cw.sprite.message.SelectWindow(names)
            index = cw.cwpy.show_message(mwin)
        # それ以外
        else:
            index = 0

        return index

    def can_action(self):
        """メッセージや選択肢を表示可能であればTrueを返す。
        Falseが返される状況の場合、メッセージは飛ばされる。
        """
        # 画像パス取得
        imgpath = self.data.get("path", "")

        # 選択外メンバ
        if imgpath.endswith("??Unselected"):
            talker = cw.cwpy.event.get_targetmember("Unselected")
            # 選択外メンバがいなかったらスキップ
            if not talker:
                return False
        # 使用中カード
        elif imgpath.endswith("??Card"):
            talker = cw.cwpy.event.get_targetmember("Inusecard")
            # 使用中カードがなかったらスキップ
            if not talker:
                return False

        # テキスト取得
        text = self.data.gettext("Text", "")
        # 選択肢取得
        names = self.get_selections_and_indexes()

        # テキストが存在せず、選択肢も無い場合はスキップ
        if not text and len(names) <= 1:
            return False

        return True

    def get_status(self):
        imgpath = self.data.get("path", "")

        if imgpath.endswith("??Random"):
            s = u"[ランダム] "
        elif imgpath.endswith("??Selected"):
            s = u"[選択中] "
        elif imgpath.endswith("??Unselected"):
            s = u"[選択外] "
        elif imgpath.endswith("??Card"):
            s = u"[カード] "
        else:
            s = ""

        return s + self.data.gettext("Text", "").replace("\\n", "")

class TalkDialogContent(TalkContent):
    def action(self):
        """台詞コンテント。"""
        # 選択肢取得
        names = self.get_selections_and_indexes()
        # 対象メンバ取得
        targetm = self.data.get("targetm", "")
        if targetm == "Valued":
            talker = self.get_valuedmember()
        else:
            talker = cw.cwpy.event.get_targetmember(targetm)

        # 対象メンバが存在しなかったら処理中止
        if not talker or isinstance(talker, list):
            return 0

        # 画像パス
        imgpath = talker.imgpath
        # 対象メンバの所持クーポンの集合
        coupons = talker.get_coupons()
        # ダイアログリスト
        dialogs = self.get_dialogs()

        # 対象メンバが必須クーポンを所持していたら、
        # その必須クーポンに対応するテキストを優先して表示させる
        dialogtext = self.get_dialogtext(dialogs, coupons)

        # MessageWindow表示
        if dialogtext:
            mwin = cw.sprite.message.MessageWindow(dialogtext, names, imgpath, talker)
            index = cw.cwpy.show_message(mwin)
        # テキストが存在せず、選択肢が複数存在する場合はSelectWindowを表示
        elif len(names) > 1:
            mwin = cw.sprite.message.SelectWindow(names)
            index = cw.cwpy.show_message(mwin)
        else:
            index = 0

        return index

    def get_valuedmember(self):
        """評価値が最大になるメンバを返す(1.50)。"""
        values = {}
        initvalue = self.data.getint(".", "initialValue", 0)
        maxvalue = 0
        for pcard in cw.cwpy.get_pcards("unreversed"):
            if not pcard.is_active():
                continue
            value = initvalue
            for e in self.data.getfind("Coupons"):
                if pcard.has_coupon(e.text):
                    value += e.getint(".", "value", 0)
            values[pcard] = value
            maxvalue = max(value, maxvalue)

        if maxvalue <= 0:
            return []

        seq = []
        for pcard, value in values.iteritems():
            if value == maxvalue:
                seq.append(pcard)
        return cw.cwpy.dice.choice(seq)

    def can_action(self):
        """台詞を表示可能であればTrueを返す。
        Falseが返される状況の場合、台詞は飛ばされる。
        """
        # 対象メンバ取得
        targetm = self.data.get("targetm", "")
        if targetm == "Valued":
            talker = self.get_valuedmember()
        else:
            talker = cw.cwpy.event.get_targetmember(targetm)

        # 対象メンバが存在しなかったらスキップ
        if not talker or isinstance(talker, list):
            return False

        # 選択肢取得
        names = self.get_selections_and_indexes()
        # 対象メンバの所持クーポンの集合
        coupons = talker.get_coupons()
        # ダイアログリスト
        dialogs = self.get_dialogs()

        # 対象メンバが必須クーポンを所持していたら、
        # その必須クーポンに対応するテキストを優先して表示させる
        dialogtext = self.get_dialogtext(dialogs, coupons)

        # テキストが存在せず、選択肢も無い場合はスキップ
        if not dialogtext and len(names) <= 1:
            return False

        return True

    def get_dialogs(self):
        dialogs = []
        for e in self.data.getfind("Dialogs"):
            rcs = e.gettext("RequiredCoupons", "")
            rclist = cw.util.decodetextlist(rcs) if rcs else []
            req_coupons = []
            for rc in rclist:
                if rc:
                    req_coupons.append(rc)
            text = e.gettext("Text", "")
            dialogs.append((req_coupons, text))
        return dialogs

    def get_dialogtext(self, dialogs, coupons):
        dialogtext = ""
        for req_coupons, text in dialogs:
            hasallcoupons = True
            for req_coupon in req_coupons:
                if not req_coupon in coupons:
                    hasallcoupons = False
                    break

            if hasallcoupons:
                dialogtext = text

            if not req_coupons:
                dialogtext = text

            if dialogtext:
                break
        return dialogtext

    def get_status(self):
        try:
            return self.data.getfind("Dialogs")[0].gettext("Text").replace("\\n", "")
        except:
            return ""

#-------------------------------------------------------------------------------
# Wait系コンテント
#-------------------------------------------------------------------------------

class WaitContent(EventContentBase):
    def action(self):
        """時間経過コンテント。
        cnt * 0.1秒 の時間待機する。
        """
        # 最新の画面を描画してから時間待機する
        cw.cwpy.draw()
        value = self.data.getint(".", "value", 0)

        tick = pygame.time.get_ticks() + (value * 100)
        cw.cwpy.event.breakwait = False
        while cw.cwpy.is_running() and pygame.time.get_ticks() < tick:
            keyin = cw.cwpy.keyevent.get_pressed()

            # リターンキー長押し, マウスボタンアップ, キーダウンで処理中断
            if keyin[K_RETURN] > cw.cwpy.keyevent.threshold or cw.cwpy.event.breakwait:
                break

            cw.cwpy.event.refresh_activeitem()
            cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
            cw.cwpy.draw()
            breakflag = pygame.event.peek((MOUSEBUTTONUP, KEYUP))
            cw.cwpy.input()
            cw.cwpy.eventhandler.run()
            if breakflag:
                break

            cw.cwpy.wait_frame(1)

        return 0

    def get_status(self):
        return u"時間経過コンテント"

#-------------------------------------------------------------------------------
# 代入コンテント (1.30～)
#-------------------------------------------------------------------------------

class SubstituteStepContent(EventContentBase):
    def action(self):
        """ステップ代入コンテント。"""
        fromstep = self.data.get("from")
        tostep = self.data.get("to")

        if fromstep in cw.cwpy.sdata.steps and tostep in cw.cwpy.sdata.steps:
            cw.cwpy.sdata.steps[tostep].set(cw.cwpy.sdata.steps[fromstep].value)
        elif fromstep == "??Random":
            if tostep in cw.cwpy.sdata.steps:
                sides = len(cw.cwpy.sdata.steps[tostep].valuenames)
                cw.cwpy.sdata.steps[tostep].set(cw.cwpy.dice.roll(1, sides)-1)

        return 0

    def get_status(self):
        fromstep = self.data.get("from")
        tostep = self.data.get("to")

        if fromstep in cw.cwpy.sdata.steps and tostep in cw.cwpy.sdata.steps:
            return u"ステップ『%s』の値を『%s』へ代入" % (fromstep, tostep)
        elif fromstep == "??Random" and tostep in cw.cwpy.sdata.steps:
            return u"ランダム値を『%s』へ代入" % (tostep)
        else:
            return u"ステップが指定されていません"

class SubstituteFlagContent(EventContentBase):
    def action(self):
        """フラグ代入コンテント。"""
        fromflag = self.data.get("from")
        toflag = self.data.get("to")

        if fromflag in cw.cwpy.sdata.flags and toflag in cw.cwpy.sdata.flags:
            cw.cwpy.sdata.flags[toflag].set(cw.cwpy.sdata.flags[fromflag].value)
        elif fromflag == "??Random":
            if toflag in cw.cwpy.sdata.flags:
                if cw.cwpy.dice.roll(1, 2) == 1:
                    cw.cwpy.sdata.flags[toflag].set(True)
                else:
                    cw.cwpy.sdata.flags[toflag].set(False)

        return 0

    def get_status(self):
        fromflag = self.data.get("from")
        toflag = self.data.get("to")

        if fromflag in cw.cwpy.sdata.flags and toflag in cw.cwpy.sdata.flags:
            return u"フラグ『%s』の値を『%s』へ代入" % (fromflag, toflag)
        elif fromflag == "??Random" and toflag in cw.cwpy.sdata.flags:
            return u"ランダム値を『%s』へ代入" % (toflag)
        else:
            return u"フラグが指定されていません"

#-------------------------------------------------------------------------------
# 比較分岐コンテント (1.30～)
#-------------------------------------------------------------------------------

class BranchStepValueContent(BranchContent):
    def action(self):
        """ステップ比較分岐コンテント。"""
        fromstep = self.data.get("from")
        tostep = self.data.get("to")

        if fromstep in cw.cwpy.sdata.steps and tostep in cw.cwpy.sdata.steps:
            value = cmp(cw.cwpy.sdata.steps[fromstep].value, cw.cwpy.sdata.steps[tostep].value)
            index = self.get_compare_index(value)
        else:
            index = cw.IDX_TREEEND

        return index

    def get_status(self):
        fromstep = self.data.get("from")
        tostep = self.data.get("to")

        if fromstep in cw.cwpy.sdata.steps and tostep in cw.cwpy.sdata.steps:
            return u"ステップ『%s』と『%s』を比較" % (fromstep, tostep)
        else:
            return u"ステップが指定されていません"

    def get_childname(self, child):
        fromstep = self.data.get("from")
        tostep = self.data.get("to")

        if fromstep in cw.cwpy.sdata.steps and tostep in cw.cwpy.sdata.steps:
            if child.get("name", "") == ">":
                return u"ステップ『%s』が『%s』より大きい" % (fromstep, tostep)
            elif child.get("name", "") == "=":
                return u"ステップ『%s』が『%s』と等しい" % (fromstep, tostep)
            else:
                return u"ステップ『%s』が『%s』より小さい" % (fromstep, tostep)

        else:
            return u"ステップが指定されていません"

class BranchFlagValueContent(BranchContent):
    def action(self):
        """フラグ比較分岐コンテント。"""
        fromflag = self.data.get("from")
        toflag = self.data.get("to")

        if fromflag in cw.cwpy.sdata.flags and toflag in cw.cwpy.sdata.flags:
            value = cw.cwpy.sdata.flags[fromflag].value == cw.cwpy.sdata.flags[toflag].value
            index = self.get_boolean_index(value)
        else:
            index = cw.IDX_TREEEND

        return index

    def get_status(self):
        fromflag = self.data.get("from")
        toflag = self.data.get("to")

        if fromflag in cw.cwpy.sdata.flags and toflag in cw.cwpy.sdata.flags:
            return u"フラグ『%s』と『%s』を比較" % (fromflag, toflag)
        else:
            return u"フラグが指定されていません"

    def get_childname(self, child):
        fromflag = self.data.get("from")
        toflag = self.data.get("to")

        if fromflag in cw.cwpy.sdata.flags and toflag in cw.cwpy.sdata.flags:
            if child.get("name", "") == u"○":
                return u"フラグ『%s』が『%s』と同値" % (fromflag, toflag)
            else:
                return u"フラグ『%s』が『%s』と異なる" % (fromflag, toflag)

        else:
            return u"フラグが指定されていません"

#-------------------------------------------------------------------------------
# 特殊コンテント
#-------------------------------------------------------------------------------

methoddict = {
    "MoveToYado": "set_yado",
    "MoveToTitle": "set_title",
    "Exit": "quit",
    "ShowDialog": "call_dlg",
    "MoveCard": "trade",
    "ChangeToSpecialArea": "change_specialarea",
    "LoadParty": "load_party",
    "InterruptAdventure": "interrupt_adventure",
    "DissolveParty": "dissolve_party",
    "Load": "reload_yado"}

class PostEventContent(EventContentBase):

    def action(self):
        """CWPyのメソッド実行用コンテント。
        シナリオでは使えない(スキン専用)。
        """
        if not cw.cwpy.is_playingscenario() or cw.cwpy.areaid <= 0:
            command = self.data.get("command")
            arg = self.data.get("arg")
            PostEventContent.do_action(command, arg)

        return cw.IDX_TREEEND

    @staticmethod
    def do_action(command, arg):
        try:
            arg = int(arg)
        except:
            pass

        if command in methoddict:
            methodname = methoddict[command]
            method = getattr(cw.cwpy, methodname)

            if methodname == "call_dlg":
                cw.cwpy.lock_menucards = True

            if arg:
                cw.cwpy.exec_func(method, arg)
            else:
                cw.cwpy.exec_func(method)

#-------------------------------------------------------------------------------
# コンテント取得用関数
#-------------------------------------------------------------------------------

def get_content(data):
    """対応するEventContentインスタンスを返す。
    data: Element
    """
    classname = data.tag + data.get("type", "") + "Content"

    try:
        return globals()[classname](data)
    except:
        print "NoContent: ", classname
        return None

def main():
    pass

if __name__ == "__main__":
    main()

