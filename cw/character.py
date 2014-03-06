#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import math
import pygame

import cw


class Character(object):
    def __init__(self, data=None):
        if not data is None:
            self.data = data
        self.reversed = False

        # 名前
        self.name = self.data.gettext("Property/Name", "")
        # レベル
        self.level = self.data.getint("Property/Level")
        # 各種所持カードのリスト
        self.cardpocket = self.get_cardpocket()
        # 現在ライフ・最大ライフ
        self.life = self.data.getint("Property/Life")
        self.maxlife = self.data.getint("Property/Life", "max")
        # 精神状態
        self.mentality = self.data.gettext("Property/Status/Mentality")
        self.mentality_dur = self.data.getint("Property/Status/Mentality",
                                                                    "duration")
        # 麻痺値
        self.paralyze = self.data.getint("Property/Status/Paralyze")
        # 中毒値
        self.poison = self.data.getint("Property/Status/Poison")
        # 束縛時間値
        self.bind = self.data.getint("Property/Status/Bind", "duration")
        # 沈黙時間値
        self.silence = self.data.getint("Property/Status/Silence", "duration")
        # 暴露時間値
        self.faceup = self.data.getint("Property/Status/FaceUp", "duration")
        # 魔法無効時間値
        self.antimagic = self.data.getint("Property/Status/AntiMagic",
                                                                    "duration")
        # 行動力強化値
        self.enhance_act = self.data.getint("Property/Enhance/Action")
        self.enhance_act_dur = self.data.getint("Property/Enhance/Action",
                                                                    "duration")
        # 回避力強化値
        self.enhance_avo = self.data.getint("Property/Enhance/Avoid")
        self.enhance_avo_dur = self.data.getint("Property/Enhance/Avoid",
                                                                    "duration")
        # 抵抗力強化値
        self.enhance_res = self.data.getint("Property/Enhance/Resist")
        self.enhance_res_dur = self.data.getint("Property/Enhance/Resist",
                                                                    "duration")
        # 防御力強化値
        self.enhance_def = self.data.getint("Property/Enhance/Defense")
        self.enhance_def_dur = self.data.getint("Property/Enhance/Defense",
                                                                    "duration")
        # 各種能力値
        e = self.data.getfind("Property/Ability/Physical")
        self.physical = copy.copy(e.attrib)
        e = self.data.getfind("Property/Ability/Mental")
        self.mental = copy.copy(e.attrib)
        e = self.data.getfind("Property/Ability/Enhance")
        self.enhance = copy.copy(e.attrib)

        for d in (self.physical, self.mental, self.enhance):
            for key, value in d.iteritems():
                d[key] = float(value)

        # 特性
        e = self.data.getfind("Property/Feature/Type")
        self.feature = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/NoEffect")
        self.noeffect = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/Resist")
        self.resist = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/Weakness")
        self.weakness = copy.copy(e.attrib)

        for d in (self.feature, self.noeffect, self.resist, self.weakness):
            for key, value in d.iteritems():
                d[key] = cw.util.str2bool(value)

        # デッキ
        self.deck = cw.deck.Deck(self)
        # 戦闘行動(Target, CardHeader)
        self.actiondata = None
        self.actionautoselected = False
        # 行動順位を決定する数値
        self.actionorder = 0

        # クーポン一覧
        self.coupons = {}
        for e in self.data.getfind("Property/Coupons"):
             self.coupons[e.text] = int(e.get("value")), e
        # 時限クーポンのデータのリスト(name, flag_countable)
        self.timedcoupons = self.get_timedcoupons()

        # 対象消去されたか否か
        self._vanished = False
        # 互換性マーク
        self.versionhint = self.data.getattr("Property", "versionHint", "")

        # 状態の正規化
        self.cardimg = None
        if self.is_unconscious():
            self.set_unconsciousstatus()

        # 適性検査用のCardHeader。
        self.test_aptitude = None

        self.reversed = False

    def get_imagepath(self):
        return self.data.gettext("Property/ImagePath", "")

    def set_image(self, path):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        e = self.data.find("Property/ImagePath")
        if self.get_imagepath():
            dpath = cw.util.join_paths(cw.cwpy.yadodir, os.path.dirname(self.get_imagepath()))
            cw.cwpy.ydata.deletedpaths.add(dpath)
        newpath = cw.xmlcreater.write_castimagepath(self.get_name(), path)
        self.data.edit("Property/ImagePath", newpath)

    def get_name(self):
        return self.data.gettext("Property/Name", "")

    def set_name(self, name):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        e = self.data.find("Property/Name")
        e.text = name
        self.name = name

    def get_description(self):
        return cw.util.decodewrap(self.data.gettext("Property/Description", ""))

    def set_description(self, desc):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        e = self.data.find("Property/Description")
        e.text = cw.util.encodewrap(desc)

    def set_physical(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        e = self.data.find("Property/Ability/Physical")
        e.set(name, str(int(value)))
        self.physical[name] = float(value)

    def set_mental(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        e = self.data.find("Property/Ability/Mental")
        e.set(name, str(value))
        self.mental[name] = float(value)

    def get_cardpocket(self):
        flag = bool(self.data.getroot().tag == "CastCard")
        maxnums = self.get_cardpocketspace()
        paths = ("SkillCards", "ItemCards", "BeastCards")
        cardpocket = []

        for maxn, path in zip(maxnums, paths):
            headers = []

            for e in self.data.getfind(path):
                header = cw.header.CardHeader(owner=self, carddata=e,
                                                            from_scenario=flag)
                headers.append(header)

            # 最大所持数を越えたカードは消去
            for header in headers[maxn:]:
                self.data.remove(path, header.carddata)

            cardpocket.append(headers[:maxn])

        return tuple(cardpocket)

    def get_keycodes(self, skill=True, item=True, beast=True):
        """所持カードのキーコード一覧を返す。"""
        s = set()
        seq = []
        if skill:
            seq.append(self.get_pocketcards(cw.POCKET_SKILL))
        if item:
            seq.append(self.get_pocketcards(cw.POCKET_ITEM))
        if beast:
            seq.append(self.get_pocketcards(cw.POCKET_BEAST))

        for header in seq:
            s.update(header.get_keycodes())

        s.discard("")
        return s

    def has_keycode(self, keycode, skill=True, item=True, beast=True):
        """指定されたキーコードを所持しているか。"""
        seq = []
        if skill:
            for header in self.get_pocketcards(cw.POCKET_SKILL):
                if keycode in header.get_keycodes():
                    return True
        if item:
            for header in self.get_pocketcards(cw.POCKET_ITEM):
                if keycode in header.get_keycodes():
                    return True
        if beast:
            for header in self.get_pocketcards(cw.POCKET_BEAST):
                if keycode in header.get_keycodes():
                    return True

        return False

    def lost(self):
        """
        対象消去やゲームオーバー時に呼ばれる。
        Playerクラスでオーバーライト。
        """
        pass

    #---------------------------------------------------------------------------
    #　状態チェック用
    #---------------------------------------------------------------------------

    def is_normal(self):
        """
        通常の精神状態かどうかをbool値で返す。
        """
        return bool(self.mentality == "Normal")

    def is_panic(self):
        """
        恐慌状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Panic")

    def is_brave(self):
        """
        勇敢状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Brave")

    def is_overheat(self):
        """
        激昂状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Overheat")

    def is_confuse(self):
        """
        混乱状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Confuse")

    def is_sleep(self):
        """
        睡眠状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Sleep")

    def is_paralyze(self):
        """
        麻痺または石化状態かどうかをbool値で返す
        """
        return bool(self.paralyze > 0)

    def is_poison(self):
        """
        中毒状態かどうかをbool値で返す
        """
        return bool(self.poison > 0)

    def is_bind(self):
        """
        呪縛状態かどうかをbool値で返す
        """
        return bool(self.bind > 0)

    def is_silence(self):
        """
        沈黙状態かどうかをbool値で返す。
        """
        return bool(self.silence > 0)

    def is_faceup(self):
        """
        暴露状態かどうかをbool値で返す。
        """
        return bool(self.faceup > 0)

    def is_antimagic(self):
        """
        魔法無効状態かどうかをbool値で返す。
        """
        return bool(self.antimagic > 0)

    def is_petrified(self):
        """
        石化状態かどうかをbool値で返す
        """
        return bool(self.paralyze > 20)

    def is_unconscious(self):
        """
        意識不明状態かどうかをbool値で返す
        """
        return bool(self.life <= 0)

    def is_heavyinjured(self):
        """
        重傷状態かどうかをbool値で返す
        """
        return bool(self.get_lifeper() < 20 and not self.is_unconscious())

    def is_injured(self):
        """
        軽傷状態かどうかをbool値で返す
        """
        return bool(self.get_lifeper() < 100 and not self.is_heavyinjured() and not self.is_unconscious())

    def is_injuredall(self):
        """
        負傷状態かどうかをbool値で返す
        """
        return bool(self.get_lifeper() < 100)

    def is_inactive(self):
        """
        行動不可状態かどうかをbool値で返す
        """
        b = self.is_sleep()
        b |= self.is_paralyze()
        b |= self.is_bind()
        b |= self.is_unconscious()
        b |= self.is_reversed()
        return b

    def is_active(self):
        """
        行動可能状態かどうかをbool値で返す
        """
        return not self.is_inactive()

    def is_dead(self):
        """
        非生存状態かどうかをbool値で返す
        """
        b = self.is_paralyze()
        b |= self.is_unconscious()
        b |= self.is_reversed()
        return b

    def is_alive(self):
        """
        生存状態かどうかをbool値で返す
        """
        return not self.is_dead()

    def is_fine(self):
        """
        健康状態かどうかをbool値で返す
        """
        return not self.is_injuredall() and not self.is_unconscious()

    def is_analyzable(self):
        """
        各種データが暴露可能かどうかbool値で返す。
        EnemyCardのための処理。
        デバッグフラグがTrueだったら問答無用で暴露する。
        """
        if isinstance(self, Enemy):
            return cw.cwpy.debug or self.is_faceup()
        else:
            return True

    def is_avoidable(self):
        """
        回避判定可能かどうかbool値で返す。
        """
        return self.is_active()

    def is_resistable(self):
        """
        抵抗判定可能かどうかbool値で返す。
        呪縛状態でも抵抗できる。
        """
        b = self.is_sleep()
        b |= self.is_paralyze()
        b |= self.is_unconscious()
        return not b

    def is_reversed(self):
        """
        隠蔽状態かどうかbool値で返す。
        """
        return self.reversed

    def is_vanished(self):
        return self._vanished

    def has_beast(self):
        """
        付帯召喚じゃない召喚獣カードの所持数を返す。
        """
        return len([h for h in self.get_pocketcards(cw.POCKET_BEAST) if not h.attachment])

    def is_enhanced_act(self):
        return self.enhance_act <> 0 and 0 < self.enhance_act_dur

    def is_enhanced_res(self):
        return self.enhance_res <> 0 and 0 < self.enhance_res_dur

    def is_enhanced_avo(self):
        return self.enhance_avo <> 0 and 0 < self.enhance_avo_dur

    def is_enhanced_def(self):
        return self.enhance_def <> 0 and 0 < self.enhance_def_dur

    def is_upaction(self):
        return self.enhance_act > 0 and 0 < self.enhance_act_dur

    def is_upresist(self):
        return self.enhance_res > 0 and 0 < self.enhance_res_dur

    def is_upavoid(self):
        return self.enhance_avo > 0 and 0 < self.enhance_avo_dur

    def is_updefense(self):
        return self.enhance_def > 0 and 0 < self.enhance_def_dur

    def is_downaction(self):
        return self.enhance_act < 0 and 0 < self.enhance_act_dur

    def is_downresist(self):
        return self.enhance_res < 0 and 0 < self.enhance_res_dur

    def is_downavoid(self):
        return self.enhance_avo < 0 and 0 < self.enhance_avo_dur

    def is_downdefense(self):
        return self.enhance_def < 0 and 0 < self.enhance_def_dur

    #---------------------------------------------------------------------------
    #　カード操作
    #---------------------------------------------------------------------------

    def use_card(self, targets, header):
        """targetsにカードを使用する。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if not isinstance(targets, list):
            targets = [targets]

        data = header.carddata
        # 他の使用中カード削除
        cw.cwpy.clear_inusecardimg()
        # TargetArrow削除
        cw.cwpy.clear_targetarrow()
        # 効果音ファイルのパスを取得
        soundpath = data.gettext("Property/SoundPath", "")

        # 使用アニメーション
        if header.type == "BeastCard":
            cw.cwpy.set_inusecardimg(self, header, "hidden", center=True)
            inusecardimg = cw.cwpy.get_inusecardimg()
            cw.animation.animate_sprite(inusecardimg, "deal")
            cw.animation.animate_sprite(inusecardimg, "zoomin")
            # 効果音を鳴らす
            cw.cwpy.play_sound(soundpath, header)
            waitrate = cw.cwpy.setting.dealspeed
            cw.cwpy.wait_frame(waitrate)
            cw.animation.animate_sprite(inusecardimg, "zoomout")
            cw.animation.animate_sprite(inusecardimg, "hide")
        elif isinstance(self, cw.character.Friend):
            self.set_pos_noscale(center_noscale=(316, 142))
            self.status == "hidden"
            # NPC表示
            # 互換動作: 1.20以前はメニューカードがプレイヤーカードの上に描画されるため、
            #           NPCもメニューカードのグループで描画する必要がある
            if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
                grp = cw.cwpy.mcardgrp
            else:
                grp = cw.cwpy.pcardgrp
            grp.add(self)
            cw.animation.animate_sprite(self, "deal")
            cw.animation.animate_sprite(self, "zoomin")
            # カード表示
            cw.cwpy.set_inusecardimg(self, header, center=True, spritegrp=grp)
            inusecardimg = cw.cwpy.get_inusecardimg()
            # 表示中に効果音を鳴らす
            cw.cwpy.play_sound(soundpath, header)
            cw.cwpy.draw()
            waitrate = cw.cwpy.setting.dealspeed
            cw.cwpy.wait_frame(waitrate)
            # カード消去
            cw.cwpy.clear_inusecardimg(self)
            # NPC消去
            cw.animation.animate_sprite(self, "hide")
            grp.remove(self)
        else:
            cw.cwpy.set_inusecardimg(self, header)
            cw.animation.animate_sprite(self, "zoomin")
            # 効果音を鳴らす
            cw.cwpy.play_sound(soundpath, header)


        # 宿へ取り込んだ特殊文字の使用時イベントでの表示に備える
        specialchars = cw.cwpy.rsrc.specialchars
        specialchars_is_changed = cw.cwpy.rsrc.specialchars_is_changed
        e_mates = header.carddata.find("Property/Materials")
        if cw.cwpy.is_playingscenario() and not e_mates is None:
            specialchars = specialchars.copy()
            dpath = cw.util.join_yadodir(e_mates.text)
            if os.path.isdir(dpath):
                for fname in os.listdir(dpath):
                    cw.cwpy.sdata.eat_spchar(dpath, fname)

        try:
            # カードイベント開始
            e = data.find("Events/Event")
            cw.event.CardEvent(e, header, self, targets).start()
        finally:
            # 特殊文字を元に戻す
            cw.cwpy.rsrc.specialchars = specialchars
            cw.cwpy.rsrc.specialchars_is_changed = specialchars_is_changed

    def throwaway_card(self, header, from_event=True):
        """
        引数のheaderのカードを破棄処理する。
        """
        if cw.cwpy.ydata:
            cw.cwpy.trade("TRASHBOX", header=header, from_event=from_event)
        else:
            if header.type == "SkillCard":
                index = 0
            elif header.type == "ItemCard" :
                index = 1
            elif header.type == "BeastCard":
                index = 2
            self.cardpocket[index].remove(header)

    #---------------------------------------------------------------------------
    #　戦闘行動関係
    #---------------------------------------------------------------------------

    def action(self):
        """設定している戦闘行動を行う。
        BattleEngineからのみ呼ばれる。
        """
        if self.actiondata:
            targets, header, beasts = self.actiondata

            # 召喚獣カードの使用
            if isinstance(self, cw.sprite.card.FriendCard):
                ishidden = self._vanished
            else:
                ishidden = self.status == "hidden"

            if self.is_alive() and not ishidden and self.status <> "reversed":
                for targets_b, header_b in beasts[:]:
                    inarr = False
                    for targets_c, header_c in self.actiondata[2]:
                        if header_c == header_b:
                            inarr = True
                            break
                    if not inarr:
                        # カードの効果で召喚獣カードが
                        # いなくなっている場合
                        continue

                    self.use_card(targets_b, header_b)

                    # 戦闘勝利チェック
                    if cw.cwpy.battle.check_win():
                        raise cw.battle.BattleWinError()

                    if isinstance(self, cw.sprite.card.FriendCard):
                        ishidden = self._vanished
                    else:
                        ishidden = self.status == "hidden"

                    # カードの効果で行動が変わっている可能性がある
                    if not self.actiondata or ishidden or self.status == "reversed":
                        break

            # 手札カードの使用
            if self.is_alive() and not ishidden and self.status <> "reversed" and self.actiondata:
                targets, header, beasts = self.actiondata
                if header and self.is_active() and not ishidden and self.status <> "reversed":
                    self.deck.use(header)
                    self.use_card(targets, header)

    def set_action(self, target, header, beasts=[], auto=False):
        """
        戦闘行動を設定。
        auto: 自動手札選択から設定されたかどうか。
        """
        if auto:
            self.clear_action()
            self.actiondata = (target, header, beasts)
            self.actionautoselected = auto
        else:
            if self.actiondata:
                beasts = self.actiondata[2]

            self.clear_action()
            self.actiondata = (target, header, beasts)
            self.actionautoselected = auto
            cw.cwpy.sounds["page"].play()
            assert cw.cwpy.pre_dialogs
            if cw.cwpy.pre_dialogs:
                cw.cwpy.pre_dialogs.pop()

        if cw.cwpy.battle and target:
            seq = []
            if header:
                seq.append((target, header))
            seq.extend(beasts)

            for target, h in seq:
                for e in h.carddata.getfind("Motions"):
                    t = e.get("type", "")
                    if t:
                        cw.cwpy.battle.priorityacts.append((t, target, self))

    def adjust_action(self):
        """
        現在の状態に合わせて一部戦闘行動を解除する。
        行動不能であれば自律的な行動は行えず、
        麻痺・死亡状態であれば召喚獣も動けない。
        """
        if self.actiondata:
            if self.is_dead():
                self.clear_action()
            elif self.is_inactive():
                target, header, beasts = self.actiondata
                self.set_action(None, None, beasts, True)

        if self.is_inactive():
            self.deck.throwaway()

    def clear_action(self):
        self.actiondata = None
        self.actionautoselected = False
        if cw.cwpy.battle:
            for key, target, user in cw.cwpy.battle.priorityacts[:]:
                if user == self:
                    cw.cwpy.battle.priorityacts.remove((key, target, user))

    #---------------------------------------------------------------------------
    #　判定用
    #---------------------------------------------------------------------------

    def decide_outcome(self, level, vocation, thresholdbonus=4, enhance=0, subbonus=0):
        """
        行為判定を行う。成功ならTrue。失敗ならFalseを返す。
        level: 判定レベル。
        vocation: 適性データ。(身体適性名, 精神適性名)のタプル。
        thresholdbonus: アクション元の適性値+行動力強化値。効果コンテントだと4。
        enhance: 回避・抵抗判定の場合はボーナス値。
        subbonus: 各種判定のサブボーナス(現在は成功率修正のみ)。
        """
        dice = cw.cwpy.dice.roll(2)
        if dice == 12:
            return True
        elif dice == 2:
            return False

        udice = cw.cwpy.dice.roll(2)
        tdice = cw.cwpy.dice.roll(2)

        thresholdbonus = int(thresholdbonus)
        bonus = int(self.get_vocation_val(vocation) + enhance)
        uvalue = (thresholdbonus+1) / 2 + level + subbonus + udice
        tvalue = (bonus+1) / 2 + self.level + tdice
        return uvalue < tvalue

    def decide_misfire(self, level):
        """
        カードの不発判定を行う。成功ならTrue。失敗ならFalseを返す。
        level: 判定レベル(カードの技能レベル)。
        """
        dice = cw.cwpy.dice.roll(2)
        threshold = level - self.level - 1

        if dice == 12:
            flag = True
        elif dice >= threshold:
            flag = True
        else:
            flag = False

        return flag

    #---------------------------------------------------------------------------
    #　戦闘行動設定関連
    #---------------------------------------------------------------------------

    def decide_actionorder(self):
        """
        行動順位を判定する数値をself.actionorderに設定。
        敏捷度と大胆性で判定。レベル・行動力は関係なし。
        """
        vocation_val = int(self.get_vocation_val(("agl", "uncautious")) + 4)
        n = vocation_val / 2
        n2 = vocation_val % 2 * 5
        value = cw.cwpy.dice.roll(n, 10)

        if n2:
            value += cw.cwpy.dice.roll(1, n2)

        self.actionorder = value
        return value

    def decide_action(self):
        """
        自動手札選択。
        """
        self.clear_action()
        if self.is_dead() or not cw.cwpy.status == "ScenarioBattle":
            return

        # 召喚獣カード
        beasts = []

        for header in self.get_pocketcards(cw.POCKET_BEAST):
            if header.is_autoselectable():
                targets, effectivetargets, highprioritys = header.get_targets()

                if highprioritys:
                    efftargets = highprioritys
                elif effectivetargets:
                    efftargets = effectivetargets
                else:
                    efftargets = []

                if efftargets:
                    if not header.allrange and len(targets) > 1:
                        targets = [cw.cwpy.dice.choice(efftargets)]

                    beasts.append((targets, header))

        # 行動不能時は召喚獣のみ
        if self.is_inactive():
            self.set_action(None, None, beasts, True)
            return

        # 使用するカード
        headers = []
        highs = []

        for header in self.deck.hand:
            if header.is_autoselectable():
                targets, effectivetargets, highprioritys = header.get_targets()

                if highprioritys:
                    highs.append((highprioritys, header))
                elif effectivetargets or header.target == "None":
                    if not header.allrange:
                        targets = effectivetargets

                    headers.append((targets, header))

        if highs:
            targets, header = self.decide_usecard(highs)
        else:
            targets, header = self.decide_usecard(headers)

        if header and not header.allrange and len(targets) > 1:
            targets = [cw.cwpy.dice.choice(targets)]

        # 行動設定
        self.set_action(targets, header, beasts, True)

    def decide_usecard(self, headers):
        seq = []

        for index, t in enumerate(headers):
            targets, header = t

            # カード交換のソートキーは4固定
            if header.type == "ActionCard" and header.id == 0:
                sortkey = 4
            else:
                sortkey = header.get_vocation_val(self)

            seq.append((sortkey, len(targets), index, (targets, header)))

        seq.sort(reverse=True)
        seq2 = []

        for index, i in enumerate(seq):
            for cnt in xrange(len(seq) - index):
                seq2.append(i)

        if not seq2:
            return None, None

        return cw.cwpy.dice.choice(seq2)[3]

    #---------------------------------------------------------------------------
    #　状態取得用
    #---------------------------------------------------------------------------

    def get_pocketcards(self, index):
        """
        所持しているカードを返す。
        index: カードの種類。
        """
        return self.cardpocket[index]

    def get_cardpocketspace(self):
        """
        最大所持カード枚数を
        (スキルカード, アイテムカード, 召喚獣カード)のタプルで返す
        """
        maxskillnum = self.level / 2 + self.level % 2 + 2
        maxskillnum = cw.util.numwrap(maxskillnum, 1, 10)
        maxbeastnum = (self.level + 2) / 4

        if (self.level + 2) % 4:
            maxbeastnum += 1

        maxbeastnum = cw.util.numwrap(maxbeastnum, 1, 10)
        return (maxskillnum, maxskillnum, maxbeastnum)

    def get_lifeper(self):
        """
        ライフのパーセンテージを返す。
        """
        return 100 * self.life / self.maxlife

    def get_bonus(self, vocation):
        """
        適性値と行動力強化値を合計した、行為判定用のボーナス値を返す。
        vocation: 適性データ。(身体適性名, 精神適性名)のタプル。
        """
        return self.get_vocation_val(vocation) + self.get_enhance_act()

    def get_vocation_val(self, vocation):
        """
        適性値(身体適性値 + 精神適性値)を返す。
        引数のvocationは(身体適性名, 精神適性名)のタプル。
        """
        vocation = (vocation[0].lower(), vocation[1].lower())
        physical = vocation[0]
        mental = vocation[1].replace("un", "", 1)
        physical = self.physical.get(physical)
        mental = self.mental.get(mental)

        if vocation[1].find("un") > -1:
            mental = -mental

        return physical + mental

    def get_enhance_act(self):
        """
        行動力強化値を返す。行動力は効果コンテントによる強化値だけ。
        """
        return cw.util.numwrap(self.enhance_act, -10, 10)

    def get_enhance_def(self):
        """
        現在かけられている全ての防御力強化値の合計を返す。
        デフォルト強化値 + 効果コンテント強化値 + カード所持強化値 + カード使用強化値。
        単体で+10の修正がない場合は、合計値が+10を越えていても+9を返す。
        """
        val1 = self.enhance.get("defense")
        val1 = cw.util.numwrap(val1, -10, 10)
        val2 = self.enhance_def
        val2 = cw.util.numwrap(val2, -10, 10)

        val3 = 0
        b = False

        for header in self.get_pocketcards(cw.POCKET_ITEM) + self.get_pocketcards(cw.POCKET_BEAST):
            avoid, resist, defense = header.get_enhance_val()

            if defense >= 10:
                b = True

            val3 += defense

        if b:
            val3 = cw.util.numwrap(val3, -10, 10)
        else:
            val3 = cw.util.numwrap(val3, -10, 9)

        val4 = 0
        if self.actiondata and self.actiondata[1]:
            header = self.actiondata[1]
            avoid, resist, defense = header.get_enhance_val_used()
            val4 += defense
        val4 = cw.util.numwrap(val4, -10, 10)

        value = 0
        b = False

        for n in (val1, val2, val3, val4):
            if n == 10:
                b = True

            value += n

        if b:
            value = cw.util.numwrap(value, -10, 10)
        else:
            value = cw.util.numwrap(value, -10, 9)

        return value

    def get_enhance_res(self):
        """
        現在かけられている全ての抵抗力強化値の合計を返す。
        デフォルト強化値 + 効果コンテント強化値 + カード所持強化値 + カード使用強化値。
        """
        val1 = self.enhance.get("resist")
        val1 = cw.util.numwrap(val1, -10, 10)
        val2 = self.enhance_res
        val2 = cw.util.numwrap(val2, -10, 10)

        val3 = 0
        for header in self.get_pocketcards(cw.POCKET_ITEM) + self.get_pocketcards(cw.POCKET_BEAST):
            avoid, resist, defense = header.get_enhance_val()
            val3 += resist
        val3 = cw.util.numwrap(val3, -10, 10)

        val4 = 0
        if self.actiondata and self.actiondata[1]:
            header = self.actiondata[1]
            avoid, resist, defense = header.get_enhance_val_used()
            val4 += resist
        val4 = cw.util.numwrap(val4, -10, 10)

        value = val1 + val2 + val3 + val4
        value = cw.util.numwrap(value, -10, 10)
        return value

    def get_enhance_avo(self):
        """
        現在かけられている全ての回避力強化値の合計を返す。
        デフォルト強化値 + 効果コンテント強化値 + カード所持強化値 + カード使用強化値。
        """
        val1 = self.enhance.get("avoid")
        val1 = cw.util.numwrap(val1, -10, 10)
        val2 = self.enhance_avo
        val2 = cw.util.numwrap(val2, -10, 10)

        val3 = 0
        for header in self.get_pocketcards(cw.POCKET_ITEM) + self.get_pocketcards(cw.POCKET_BEAST):
            avoid, resist, defense = header.get_enhance_val()
            val3 += avoid
        val3 = cw.util.numwrap(val3, -10, 10)

        val4 = 0
        if self.actiondata and self.actiondata[1]:
            header = self.actiondata[1]
            avoid, resist, defense = header.get_enhance_val_used()
            val4 += avoid
        val4 = cw.util.numwrap(val4, -10, 10)

        value = val1 + val2 + val3 + val4
        value = cw.util.numwrap(value, -10, 10)
        return value

    #---------------------------------------------------------------------------
    #　クーポン関連
    #---------------------------------------------------------------------------

    def get_coupons(self):
        """
        所有クーポンをセット型で返す。
        """
        return set(self.coupons.keys())

    def get_couponvalue(self, name, raiseerror=True):
        """
        クーポンの値を返す。
        """
        if raiseerror:
            return self.coupons[name][0]
        else:
            data = self.coupons.get(name, None)
            if data:
                return data[0]
            else:
                return None

    def has_coupon(self, coupon):
        """
        引数のクーポンを所持しているかbool値で返す。
        """
        return coupon in self.coupons

    def get_couponsvalue(self):
        """
        全ての所持クーポンの点数を合計した値を返す。
        """
        cnt = 0

        for coupon, data in self.coupons.iteritems():
            if coupon and not coupon.startswith(u"＠"):
                value = data[0]
                cnt += value

        return cnt

    def get_specialcoupons(self):
        """
        "＠"で始まる特殊クーポンの
        辞書(key=クーポン名, value=クーポン得点)を返す。
        """
        d = {}

        for coupon, data in self.coupons.iteritems():
            if coupon and coupon.startswith(u"＠"):
                value = data[0]
                d[coupon] = value

        return d

    def get_sex(self):
        for coupon in cw.cwpy.setting.sexcoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.sexcoupons[0]

    def set_sex(self, sex):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self.get_sex()
        if old:
            self.remove_coupon(old)
        self.set_coupon(sex, 0)

    def get_age(self):
        for coupon in cw.cwpy.setting.periodcoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.periodcoupons[0]

    def set_age(self, age):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self.get_age()
        if old:
            self.remove_coupon(old)
        self.set_coupon(age, 0)

    def get_talent(self):
        for coupon in cw.cwpy.setting.naturecoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.naturecoupons[0]

    def set_talent(self, talent):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self.get_talent()
        if old:
            self.remove_coupon(old)
        self.set_coupon(talent, 0)

    def get_makings(self):
        """
        所持する特徴クーポンをセット型で返す。
        """
        makings = set()
        for making in cw.cwpy.setting.makingcoupons:
            if making in self.coupons:
                makings.add(making)
        return makings

    def set_makings(self, makings):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for coupon in cw.cwpy.setting.makingcoupons:
            if coupon in self.coupons:
                self.remove_coupon(coupon)
        for coupon in makings:
            self.set_coupon(coupon, 0)

    def get_race(self):
        for race in cw.cwpy.setting.races:
            if self.has_coupon(u"＠Ｒ" + race.name):
                return race
        return cw.cwpy.setting.unknown_race

    def count_timedcoupon(self, value=-1):
        """
        時限クーポンの点数を減らす。
        value: 減らす数。
        """
        if self.timedcoupons:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.data.is_edited = True

            for coupon in list(self.timedcoupons):
                oldvalue, e = self.coupons[coupon]
                if oldvalue == 0:
                    continue

                n = oldvalue + value
                n = cw.util.numwrap(n, 0, 999)

                if n > 0:
                    e.set("value", str(n))
                    self.coupons[coupon] = n, e
                else:
                    self.remove_coupon(coupon)

    def set_coupon(self, name, value):
        """
        クーポンを付与する。同名のクーポンがあったら上書き。
        時限クーポン("："or"；"で始まるクーポン)はtimedcouponsに登録する。
        name: クーポン名。
        value: クーポン点数。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        value = int(value)
        value = cw.util.numwrap(value, -999, 999)
        removed = self._remove_coupon(name, False)
        e = self.data.make_element("Coupon", name, {"value" : str(value)})
        self.data.append("Property/Coupons", e)
        self.coupons[name] = value, e

        # 時限クーポン
        if name.startswith(u"：") or name.startswith(u"；"):
            self.timedcoupons.add(name)

        # 隠蔽クーポン
        if name == u"：Ｒ" and not self.is_reversed():
            if not removed:
                cw.animation.animate_sprite(self, "reverse")
            self.reversed = True

        # 隠蔽クーポンがあるため
        self.adjust_action()

    def get_timedcoupons(self):
        """
        時限クーポンのデータをまとめたsetを返す。
        """
        s = set()

        for coupon, data in self.coupons.iteritems():
            if coupon.startswith(u"：") or coupon.startswith(u"；"):
                s.add(coupon)

        return s

    def remove_coupon(self, name):
        """
        同じ名前のクーポンを全て剥奪する。
        name: クーポン名。
        """
        return self._remove_coupon(name, True)

    def _remove_coupon(self, name, update):
        if not name in self.coupons:
            return False
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        value, e = self.coupons[name]
        self.data.remove("Property/Coupons", e)
        del self.coupons[name]

        # 時限クーポン
        if name in self.timedcoupons:
            self.timedcoupons.remove(name)

        # 隠蔽クーポン
        if name == u"：Ｒ" and self.is_reversed():
            if update:
                cw.animation.animate_sprite(self, "reverse")
            self.reversed = False

        return True

    def remove_timedcoupons(self, battleonly=False):
        """
        時限クーポンを削除する。イメージは更新しない。
        battleonly: Trueの場合は"；"の時限クーポンのみ削除。
        """
        for name in set(self.timedcoupons):
            if not battleonly or name.startswith(u"；"):
                self._remove_coupon(name, False)

    def remove_numbercoupon(self):
        """
        "＿１"等の番号クーポンを削除。
        """
        # u"＠ＭＰ３"はCardWirth 1.29以降で配布されるクーポン
        names = [cw.cwpy.msgs["number_1_coupon"], u"＿１", u"＿２", u"＿３", u"＿４", u"＿５", u"＿６", u"＠ＭＰ３"]

        for name in names:
            self.remove_coupon(name)

    #---------------------------------------------------------------------------
    #　レベル変更用
    #---------------------------------------------------------------------------

    def get_limitlevel(self):
        """レベルの調節範囲の最大値を返す。"""
        l = self.get_couponvalue(u"＠レベル原点", raiseerror=False)
        if not l is None:
            return max(self.level, l)
        else:
            return self.level

    def check_level(self):
        coupons = self.get_specialcoupons()
        level = coupons[u"＠レベル原点"]

        if u"＠レベル上限" in coupons:
            limit = coupons[u"＠レベル上限"]
        elif u"＠本来の上限" in coupons:
            limit = coupons[u"＠本来の上限"]
            self.set_coupon(u"＠レベル上限", limit)
        else:
            limit = 10
            self.set_coupon(u"＠レベル上限", 10)

        # 解の公式で現在の経験点で到達できるレベルを算出
        cnt = max(1, self.get_couponsvalue())
        olevel = int((-1 + math.sqrt(1 + 4 * cnt)) / 2.0) + 1
        olevel = min(limit, olevel)

        return olevel - level

    def set_level(self, value, regulate=False, debugedit=False, backpack_party=None):
        """レベルを設定する。
        regulate: レベルを調節する場合はTrue。
        backpack_party: レベルが下がって手札を持ちきれなくなった際、
                        このパーティの荷物袋へ入れる。
                        Noneの場合はアクティブなパーティの荷物袋か
                        カード置場へ入る。
        """
        if regulate:
            # 調節前のレベル
            limit = self.get_limitlevel()
            value = min(value, limit)

        # レベル
        uplevel = value - self.level
        if uplevel == 0:
            return

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.level = value
        self.data.edit("Property/Level", str(self.level))
        # 最大HPとHP
        vit = self.physical.get("vit")

        if vit < 1:
            vit = 1

        minval = self.physical.get("min")

        if minval < 1:
            minval = 1

        maxlife = (vit / 2 + 4) * (self.level + 1) + minval / 2
        self.maxlife += maxlife - self.maxlife
        self.data.edit("Property/Life", str(self.maxlife), "max")
        self.set_life(self.maxlife)

        if not regulate:
            # レベル原点・EPクーポン操作
            for e in self.data.find("Property/Coupons"):
                if not e.text:
                    continue

                if e.text == u"＠レベル原点":
                    e.attrib["value"] = str(self.level)
                    self.coupons[e.text] = self.level, e
                elif e.text == u"＠ＥＰ":
                    value = e.getint(".", "value", 0) + uplevel * 10
                    e.attrib["value"] = str(value)
                    self.coupons[e.text] = value, e

        if uplevel < 0:
            # 所持可能上限を越えたカードを、荷物袋ないしカード置き場へ移動
            if backpack_party or isinstance(self, cw.sprite.card.PlayerCard):
                targettype = "BACKPACK"
            else:
                targettype = "STOREHOUSE"
            targettype_original = targettype
            for index in range(3):
                n = len(self.cardpocket[index])
                maxn = self.get_cardpocketspace()[index]
                while n > maxn:
                    header = self.cardpocket[index][-1]
                    if index == cw.POCKET_BEAST and not header.attachment:
                        targettype = "TRASHBOX"
                    else:
                        targettype = targettype_original
                    if regulate and targettype <> "TRASHBOX":
                        self.add_cardpocketmemory(header)
                    cw.cwpy.trade(targettype=targettype, header=header, from_event=True, party=backpack_party)
                    n -= 1
            for header in self.cardpocket[0]:
                header.get_uselimit(reset=True)
        elif 0 < uplevel:
            # レベル調節で手放したカードを戻す
            self.revert_cardpocket(backpack_party)

    def add_cardpocketmemory(self, header):
        """レベル調節前に所持していたカードを記憶する。"""
        memories = self.data.find("./CardMemories")
        if memories is None:
            memories = cw.data.make_element("CardMemories")
            self.data.append(".", memories)
        e = cw.data.make_element("CardMemory")
        e.append(cw.data.make_element("Type", header.type))
        e.append(cw.data.make_element("Name", header.name))
        e.append(cw.data.make_element("Description", header.desc))
        e.append(cw.data.make_element("Scenario", header.scenario))
        e.append(cw.data.make_element("Author", header.author))
        if type <> "BeastCard":
            e.append(cw.data.make_element("Hold", str(header.hold)))
        if header.type <> "SkillCard":
            e.append(cw.data.make_element("UseLimit", str(header.uselimit)))
        memories.append(e)

    def revert_cardpocket(self, backpack_party=None):
        """記憶していたカードを検索し、
        見つかったら再び所持する。"""
        if not cw.cwpy.setting.revert_cardpocket:
            return

        if not backpack_party:
            backpack_party = cw.cwpy.ydata.party

        seq = []
        if backpack_party:
            seq.extend(backpack_party.backpack)
            if not backpack_party.is_adventuring():
                seq.extend(cw.cwpy.ydata.storehouse)
        else:
            seq.extend(cw.cwpy.ydata.storehouse)

        maxn = self.get_cardpocketspace()
        n = [
             len(self.get_pocketcards(cw.POCKET_SKILL)),
             len(self.get_pocketcards(cw.POCKET_ITEM)),
             len(self.get_pocketcards(cw.POCKET_BEAST)),
        ]
        for e in reversed(self.data.getfind("./CardMemories", False)[:]):
            type = e.gettext("./Type")
            name = e.gettext("./Name", "")
            desc = e.gettext("./Description", "")
            scenario = e.gettext("./Scenario", "")
            author = e.gettext("./Author", "")
            if type == "SkillCard":
                index = cw.POCKET_SKILL
                uselimit = -1
            elif type == "ItemCard":
                index = cw.POCKET_ITEM
                uselimit = e.getint("./UseLimit", -1)
            elif type == "BeastCard":
                index = cw.POCKET_BEAST
                uselimit = e.getint("./UseLimit", -1)

            if n[index] < maxn[index]:
                for header in seq:
                    if header.type == type and\
                            header.name == name and\
                            header.desc == desc and\
                            header.scenario == scenario and\
                            header.author == author and\
                            (uselimit == -1 or uselimit == header.uselimit):
                        n[index] += 1
                        cw.cwpy.trade("PLAYERCARD", target=self, header=header, from_event=True, party=backpack_party)
                        seq.remove(header)
                        if type <> "BeastCard":
                            hold = e.getbool("./Hold", False)
                            header.set_hold(hold)
                        break
                # 記憶に残すのは持ちきれなかった場合のみ
                # 持ちきれる場合はカードが見つからなくても
                # 記憶から除去する
                self.data.remove("./CardMemories", e)

    #---------------------------------------------------------------------------
    #　状態変更用
    #---------------------------------------------------------------------------

    def set_unconsciousstatus(self):
        """
        意識不明に伴う状態回復。
        強化値もすべて0、付帯召喚以外の召喚獣カードも消去。
        毒と麻痺は残る。
        """
        self.set_mentality("Normal", 0)
        self.set_bind(0)
        self.set_silence(0)
        self.set_faceup(0)
        self.set_antimagic(0)
        self.set_enhance_act(0, 0)
        self.set_enhance_avo(0, 0)
        self.set_enhance_res(0, 0)
        self.set_enhance_def(0, 0)
        self.set_beast(vanish=True)

    def set_fullrecovery(self):
        """
        完全回復処理。HP＆精神力＆状態異常回復。
        強化値もすべて0、付帯召喚以外の召喚獣カードも消去。
        """
        self.set_life(self.maxlife)
        self.set_paralyze(-40)
        self.set_poison(-40)
        self.set_mentality("Normal", 0)
        self.set_bind(0)
        self.set_silence(0)
        self.set_faceup(0)
        self.set_antimagic(0)
        self.set_enhance_act(0, 0)
        self.set_enhance_avo(0, 0)
        self.set_enhance_res(0, 0)
        self.set_enhance_def(0, 0)
        self.set_skillpower(True)
        self.set_beast(vanish=True)

        # 行動を再選択する
        if cw.cwpy.is_battlestatus():
            self.deck.set(self)
            self.decide_action()

    def set_life(self, value):
        """
        現在ライフに引数nの値を足す(nが負だと引き算でダメージ)。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.life += value
        self.life = cw.util.numwrap(self.life, 0, self.maxlife)
        self.data.edit("Property/Life", str(int(self.life)))
        self.adjust_action()
        if self.is_unconscious():
            self.set_unconsciousstatus()

    def set_paralyze(self, value):
        """
        麻痺値を操作する。
        麻痺値は0～40の範囲を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.paralyze += value
        self.paralyze = cw.util.numwrap(self.paralyze, 0, 40)
        self.data.edit("Property/Status/Paralyze", str(self.paralyze))
        self.adjust_action()

    def set_poison(self, value):
        """
        中毒値を操作する。
        中毒値は0～40の範囲を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.poison += value
        self.poison = cw.util.numwrap(self.poison, 0, 40)
        self.data.edit("Property/Status/Poison", str(self.poison))

    def set_mentality(self, name, value, overwrite=True):
        """
        精神状態とその継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            name = "Normal"
            value = 0
        value = cw.util.numwrap(value, 0, 999)
        if name == "Normal":
            value = 0
        elif value == 0:
            name = "Normal"

        if not overwrite and name == self.mentality and name <> "Normal":
            # 長い方の効果時間を優先
            self.mentality_dur = max(self.mentality_dur, value)
        else:
            self.mentality = name
            self.mentality_dur = value

        path = "Property/Status/Mentality"
        self.data.edit(path, self.mentality)
        self.data.edit(path, str(self.mentality_dur), "duration")
        self.adjust_action()

    def set_bind(self, value, overwrite=True):
        """
        束縛状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.bind = value
        else:
            self.bind = max(self.bind, value)
        self.bind = cw.util.numwrap(self.bind, 0, 999)
        self.data.edit("Property/Status/Bind", str(self.bind), "duration")
        self.adjust_action()

    def set_silence(self, value, overwrite=True):
        """
        沈黙状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.silence = value
        else:
            self.silence = max(self.silence, value)
        self.silence = cw.util.numwrap(self.silence, 0, 999)
        self.data.edit("Property/Status/Silence", str(self.silence), "duration")

    def set_faceup(self, value, overwrite=True):
        """
        暴露状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.faceup = value
        else:
            self.faceup = max(self.faceup, value)
        self.faceup = cw.util.numwrap(self.faceup, 0, 999)
        self.data.edit("Property/Status/FaceUp", str(self.faceup), "duration")

    def set_antimagic(self, value, overwrite=True):
        """
        魔法無効状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.antimagic = value
        else:
            self.antimagic = max(self.antimagic, value)
        self.antimagic = cw.util.numwrap(self.antimagic, 0, 999)
        self.data.edit("Property/Status/AntiMagic", str(self.antimagic), "duration")

    def set_vanish(self):
        """
        対象消去を行う。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if not self.is_vanished():
            self._vanished = True
            cw.animation.animate_sprite(self, "delete")
            self.lost()

    def set_enhance_act(self, value, duration):
        """
        行動力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_act = value
        self.enhance_act = cw.util.numwrap(self.enhance_act, -10, 10)
        self.enhance_act_dur = duration
        self.enhance_act_dur = cw.util.numwrap(self.enhance_act_dur, 0, 999)
        path = "Property/Enhance/Action"
        self.data.edit(path, str(self.enhance_act))
        self.data.edit(path, str(self.enhance_act_dur), "duration")

    def set_enhance_avo(self, value, duration):
        """
        回避力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_avo = value
        self.enhance_avo = cw.util.numwrap(self.enhance_avo, -10, 10)
        self.enhance_avo_dur = duration
        self.enhance_avo_dur = cw.util.numwrap(self.enhance_avo_dur, 0, 999)
        path = "Property/Enhance/Avoid"
        self.data.edit(path, str(self.enhance_avo))
        self.data.edit(path, str(self.enhance_avo_dur), "duration")

    def set_enhance_res(self, value, duration):
        """
        抵抗力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_res = value
        self.enhance_res = cw.util.numwrap(self.enhance_res, -10, 10)
        self.enhance_res_dur = duration
        self.enhance_res_dur = cw.util.numwrap(self.enhance_res_dur, 0, 999)
        path = "Property/Enhance/Resist"
        self.data.edit(path, str(self.enhance_res))
        self.data.edit(path, str(self.enhance_res_dur), "duration")

    def set_enhance_def(self, value, duration):
        """
        抵抗力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_def = value
        self.enhance_def = cw.util.numwrap(self.enhance_def, -10, 10)
        self.enhance_def_dur = duration
        self.enhance_def_dur = cw.util.numwrap(self.enhance_def_dur, 0, 999)
        path = "Property/Enhance/Defense"
        self.data.edit(path, str(self.enhance_def))
        self.data.edit(path, str(self.enhance_def_dur), "duration")

    def set_skillpower(self, recovery=True):
        """
        精神力(スキルの使用回数)を操作する。
        recoveryがTrueだったら、最大値まで回復。
        Falseだったら、0にする。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for header in self.get_pocketcards(cw.POCKET_SKILL):
            if recovery:
                header.set_uselimit(999)
            else:
                header.set_uselimit(-999)

        if recovery:
            if cw.cwpy.is_battlestatus():
                self.deck.get_skillpower(self)
        else:
            if cw.cwpy.is_battlestatus():
                self.deck.lose_skillpower(self)

    def set_beast(self, element=None, vanish=False):
        """召喚獣を召喚する。付帯召喚設定は強制的にクリアされる。
        vanish: 召喚獣を消去するかどうか。
        """
        idx = cw.POCKET_BEAST

        eff = False
        if vanish:
            for header in self.get_pocketcards(idx)[::-1]:
                if not header.attachment:
                    self.throwaway_card(header)
                    eff = True

        elif self.can_addbeast():
            if self.is_unconscious():
                return eff
            etree = cw.data.xml2etree(element=element, nocache=True)
            cw.content.get_card(etree, self, True)
            eff = True
        return eff

    def can_addbeast(self):
        if self.is_unconscious():
            return False
        idx = cw.POCKET_BEAST
        return len(self.get_pocketcards(idx)) < self.get_cardpocketspace()[idx]

    def set_timeelapse(self, time=1):
        """時間経過。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # 時限クーポン処理
        self.count_timedcoupon()
        oldalive = self.is_alive()
        flag = False

        # 中毒
        if self.is_poison() and not self.is_unconscious():
            self.set_poison(-time)

            if not self.is_poison():
                flag = True
            else:
                cw.cwpy.sounds["dump"].play()
                value = 1 * self.poison
                n = value / 5
                n2 = value % 5 * 2
                value = cw.cwpy.dice.roll(n, 10)

                if n2:
                    value += cw.cwpy.dice.roll(1, n2)

                self.set_life(-value)

                if self.status <> "reversed" and self.status <> "hidden":
                    cw.animation.animate_sprite(self, "lateralvibe")
                self.update_image()

        # 麻痺
        if self.is_paralyze() and not self.is_petrified():
            self.set_paralyze(-time)
            flag |= not self.is_paralyze()

        # 束縛
        if self.is_bind():
            value = self.bind - time
            self.set_bind(value)
            flag |= not self.is_bind()

        # 沈黙
        if self.is_silence():
            value = self.silence - time
            self.set_silence(value)
            flag |= not self.is_silence()

        # 暴露
        if self.is_faceup():
            value = self.faceup - time
            self.set_faceup(value)
            flag |= not self.is_faceup()

        # 魔法無効化
        if self.is_antimagic():
            value = self.antimagic - time
            self.set_antimagic(value)
            flag |= not self.is_antimagic()

        # 精神状態
        if self.mentality_dur > 0:
            value = self.mentality_dur - time

            if value > 0:
                self.set_mentality(self.mentality, value)
            else:
                self.set_mentality("Normal", 0)
                flag = True

        # 行動力
        if self.enhance_act_dur > 0:
            value = self.enhance_act_dur - time

            if value > 0:
                self.set_enhance_act(self.enhance_act, value)
            else:
                self.set_enhance_act(0, 0)
                flag = True

        # 回避力
        if self.enhance_avo_dur > 0:
            value = self.enhance_avo_dur - time

            if value > 0:
                self.set_enhance_avo(self.enhance_avo, value)
            else:
                self.set_enhance_avo(0, 0)
                flag = True

        # 抵抗力
        if self.enhance_res_dur > 0:
            value = self.enhance_res_dur - time

            if value > 0:
                self.set_enhance_res(self.enhance_res, value)
            else:
                self.set_enhance_res(0, 0)
                flag = True

        # 防御力
        if self.enhance_def_dur > 0:
            value = self.enhance_def_dur - time

            if value > 0:
                self.set_enhance_def(self.enhance_def, value)
            else:
                self.set_enhance_def(0, 0)
                flag = True

        # 中毒効果で死亡していたら、ステータスを元に戻す
        if self.is_unconscious():
            self.set_unconsciousstatus()

        # 敵が中毒効果で死亡していたら、死亡イベント開始
        if isinstance(self, Enemy) and self.is_dead() and oldalive:
            self.events.start(1)

        # 画像更新
        if flag:
            if self.status <> "reversed" and self.status <> "hidden":
                cw.animation.animate_sprite(self, "hide")
                self.update_image()
                cw.animation.animate_sprite(self, "deal")
            else:
                self.update_image()

class Player(Character):
    def lost(self):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.remove_numbercoupon()
        self.data.edit("Property", "True", "lost")
        self.data.write_xml()
        if cw.cwpy.is_playingscenario():
            if self.data.fpath.lower().startswith("yado"):
                fpath = os.path.relpath(self.data.fpath, cw.cwpy.ydata.yadodir)
            else:
                fpath = os.path.relpath(self.data.fpath, cw.cwpy.ydata.tempdir)
            fpath = cw.util.join_paths(fpath)
            cw.cwpy.sdata.lostadventurers.add(fpath)
        cw.cwpy.pcardgrp.remove(self)

class Enemy(Character):
    def is_dead(self):
        """
        敵は隠蔽状態であれば死亡と見做す。
        """
        b = Character.is_dead(self)
        b |= self.status == "hidden"
        return b

class Friend(Character):
    pass

class AlbumPage(object):
    def __init__(self, data):
        self.data = data
        self.name = self.data.gettext("Property/Name", "")
        self.level = self.data.getint("Property/Level")

    def get_specialcoupons(self):
        """
        "＠"で始まる特殊クーポンの
        辞書(key=クーポン名, value=クーポン得点)を返す。
        """
        d = {}

        for e in self.data.getfind("Property/Coupons"):
            coupon = e.text
            if coupon and coupon.startswith(u"＠"):
                d[coupon] = int(e.get("value", "0"))

        return d

def main():
    pass

if __name__ == "__main__":
    main()

