#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
from cw.character import Character


# 意識不明の対象に有効な効果。
CAN_UNCONSCIOUS = (
    "Heal",
    "Paralyze",
    "DisParalyze",
    "Poison",
    "DisPoison",
    "GetSkillPower",
    "LoseSkillPower",
    "VanishTarget"
)

def is_noeffect(element, target):
    """
    属性の相性が無効ならTrueを返す。
    """
    if element == "Health" and target.feature.get("undead"):
        return True
    elif element == "Mind" and target.feature.get("automaton"):
        return True
    elif element == "Miracle":
        if target.feature.get("unholy"):
            return False
        else:
            return True

    elif element == "Magic":
        if target.feature.get("constructure"):
            return False
        else:
            return True

    elif element == "Fire" and target.resist.get("fire"):
        return True
    elif element == "Ice" and target.resist.get("ice"):
        return True
    else:
        return False

def check_noeffect(effecttype, target):
    noeffect_wpn = target.noeffect.get("weapon")
    noeffect_mgc = target.noeffect.get("magic")
    antimagic = target.is_antimagic()

    # 物理属性
    if effecttype == "Physic":
        if noeffect_wpn:
            return True

    # 魔法属性
    elif effecttype == "Magic":
        if noeffect_mgc or antimagic:
            return True

    # 魔法的物理属性
    elif effecttype == "MagicalPhysic":
        if noeffect_wpn and noeffect_mgc or antimagic:
            return True

    # 物理的魔法属性
    elif effecttype == "PhysicalMagic":
        if noeffect_wpn or noeffect_mgc or antimagic:
            return True

    return False

class Effect(object):
    def __init__(self, motions, d):
        self.user = d.get("user", None)
        self.inusecard = d.get("inusecard", None)
        self.level = d.get("level", 0)
        self.successrate = d.get("successrate", 0)
        self.effecttype = d.get("effecttype", "Physic")
        self.resisttype = d.get("resisttype", "Avoid")
        self.soundpath = d.get("soundpath", "Avoid")
        self.visualeffect = d.get("visualeffect", "None")

        if self.user and self.inusecard:
            self.motions = [EffectMotion(e, self.user, self.inusecard)
                                                            for e in motions]
        else:
            self.motions = [EffectMotion(e, targetlevel=self.level)
                                                            for e in motions]

    def apply(self, target, event=False):
        if isinstance(target, Character) and self.check_enabledtarget(target):
            return self.apply_charactercard(target, event=event)
        elif isinstance(target, cw.sprite.card.MenuCard):
            return self.apply_menucard(target)
        else:
            return False

    def apply_menucard(self, target):
        """
        MenuCardインスタンスのキーコードイベントを発動させる。
        """
        cw.cwpy.play_sound(self.soundpath)
        self.animate(target)
        # MenuCardのキーコードイベント発動。発動しなかったら、無効音。
        keycodes = self.inusecard.keycodes
        event = target.events.check_keycodes(keycodes)

        if event:
            target.events.start(keycodes=keycodes)
            return True
        else:
            cw.cwpy.sounds["ineffective"].play()
            return False

    def apply_charactercard(self, target, event=False):
        """
        Characterインスタンスに効果モーションを適用する。
        """
        # 各種判定処理
        allmissed = self.successrate <= -5
        allsuccess = self.successrate >= 5
        success_res = False
        success_avo = False
        if allmissed:
            # 完全失敗
            noeffect = self.check_noeffect(target)
            success_res = self.resisttype == "Resist"
            success_avo = self.resisttype == "Avoid"
        elif allsuccess:
            # 完全成功(無効だけは判定)
            noeffect = self.check_noeffect(target)
            if noeffect:
                success_res = self.resisttype == "Resist"
                success_avo = self.resisttype == "Avoid"
        else:
            # 無効・回避・抵抗判定
            noeffect = self.check_noeffect(target)
            if noeffect:
                success_res = self.resisttype == "Resist"
                success_avo = self.resisttype == "Avoid"
            else:
                success_res = self.check_resist(target)
                success_avo = self.check_avoid(target)

        # ダメージ効果の有無
        countdamage = self.count_motion("damage") + self.count_motion("absorb")
        hasdamage = 0 < countdamage

        # 回避または抵抗で消耗するカード
        # 成功・不成功に関係なく消耗する
        # 絶対成功の場合のみは消耗無し
        consume = set()
        guardcard = None # 一時表示するカード

        # 使用カードは消耗しない(表示のみ)
        if not allsuccess:
            if target.actiondata and target.actiondata[1]:
                header = target.actiondata[1]
                avoid, resist, defense = header.get_enhance_val_used()
                if (0 <> avoid and self.resisttype == "Avoid") or\
                   (0 <> resist and self.resisttype == "Resist"):
                    guardcard = header

        # 所有ボーナス(アイテムは消耗しない)
        cards = target.cardpocket[cw.POCKET_BEAST]
        if not allsuccess:
            for header in cards:
                avoid, resist, defense = header.get_enhance_val()
                if (0 <> avoid and self.resisttype == "Avoid") or\
                   (0 <> resist and self.resisttype == "Resist"):
                    if not guardcard:
                        guardcard = header
                    if not allsuccess:
                        consume.add(header)

            # ボーナス・ペナルティの発動したカードを一時表示する
            guardcardimg = None
            if not event and guardcard:
                cw.cwpy.sounds["equipment"].play()
                cw.cwpy.set_guardcardimg(target, guardcard)
                cw.cwpy.draw()
                cw.cwpy.wait_frame(12)
                cw.cwpy.clear_guardcardimg()
                cw.cwpy.draw()

            # 回避・抵抗段階での消耗
            for header in consume:
                header.set_uselimit(-1)

        consume.clear()

        # 音鳴らす
        if not success_avo:
            cw.cwpy.play_sound(self.soundpath)

        if success_avo:
            cw.cwpy.sounds["avoid"].play()
            cw.cwpy.wait_frame(12)
            return False
        elif noeffect or (success_res and not hasdamage):
            cw.cwpy.sounds["ineffective"].play()
            self.animate(target, True)
            return False

        # 効果モーションを発動
        effectual = False
        for motion in self.motions:
            effectual |= motion.apply(target, success_res)

        if not effectual:
            # 効果無し
            cw.cwpy.sounds["ineffective"].play()

        # ダメージ軽減によるカード消耗
        if hasdamage:
            for header in cards:
                avoid, resist, defense = header.get_enhance_val()
                if 0 <> defense:
                    consume.add(header)

        for header in consume:
            header.set_uselimit(-countdamage)

        # アニメーション・画像更新(対象消去されていなかったら)
        if not target.is_vanished():
            # 死亡していたら、ステータスを元に戻す
            if target.is_unconscious():
                target.set_unconsciousstatus()

            self.animate(target, True)

        return True

    def check_noeffect(self, target):
        return check_noeffect(self.effecttype, target)

    def check_avoid(self, target):
        if self.resisttype == "Avoid" and target.is_avoidable():
            if self.user and self.inusecard:
                uservocation = self.inusecard.vocation
                userbonus =  self.user.get_bonus(uservocation)
            else:
                userbonus = 4

            vocation = ("agl", "cautious")
            subbonus = target.get_enhance_avo() - self.successrate
            level = self.user.level if self.user else self.level
            return target.decide_outcome(level, vocation, userbonus, subbonus)

        return False

    def check_resist(self, target):
        if self.resisttype == "Resist" and target.is_resistable():
            if self.user and self.inusecard:
                uservocation = self.inusecard.vocation
                userbonus =  self.user.get_bonus(uservocation)
            else:
                userbonus = 4

            vocation = ("min", "brave")
            subbonus = target.get_enhance_res() - self.successrate
            level = self.user.level if self.user else self.level
            return target.decide_outcome(level, vocation, userbonus, subbonus)

        return False

    def animate(self, target, update_image=False):
        """
        targetにtypenameの効果アニメーションを実行する。
        update_imageがTrueだったら、アニメ後にtargetの画像を更新する。
        """
        # 隠れているカードやFriendCardはアニメーションさせない
        if isinstance(target, cw.character.Friend) or target.status == "hidden":
            if update_image:
                target.update_image()
                cw.cwpy.draw()

            if self.soundpath:
                cw.cwpy.wait_frame(12)

        # 横振動(地震)
        elif self.visualeffect == "Horizontal":
            cw.animation.animate_sprite(target, "lateralvibe")

            if update_image:
                target.update_image()

        # 縦振動(振動)
        elif self.visualeffect == "Vertical":
            cw.animation.animate_sprite(target, "axialvibe")

            if update_image:
                target.update_image()
        # 反転
        elif self.visualeffect == "Reverse":
            cw.animation.animate_sprite(target, "hide")

            if update_image:
                target.update_image()

            cw.animation.animate_sprite(target, "deal")
        # アニメーションなし
        else:
            if update_image:
                target.update_image()
                cw.cwpy.draw()

            if self.soundpath:
                cw.cwpy.wait_frame(12)

    def check_enabledtarget(self, target):
        """
        表示されていないか(敵のみ)、対象消去されているか、
        もしくは意識不明で回復モーションが入ってない場合は
        有効なターゲットではない。
        """
        if target.status == "hidden" and not isinstance(target, cw.sprite.card.PlayerCard):
            return False
        elif isinstance(target, Character):
            flag  = bool(not target.is_vanished())
            flag &= bool(not target.is_unconscious() or self.has_motions(CAN_UNCONSCIOUS))
            return flag
        else:
            return True

    def has_motions(self, motiontypes):
        for motiontype in motiontypes:
            if self.has_motion(motiontype):
                return True
        return False

    def has_motion(self, motiontype):
        """
        motiontypeで指定したEffectMotionインスタンスを所持しているかどうか。
        """
        motiontype = motiontype.lower()

        for motion in self.motions:
            if motion.type.lower() == motiontype:
                return True

        return False

    def count_motion(self, motiontype):
        """
        motiontypeで指定したEffectMotionインスタンスｎ所持数。
        """
        motiontype = motiontype.lower()

        count = 0
        for motion in self.motions:
            if motion.type.lower() == motiontype:
                count += 1

        return count

#-------------------------------------------------------------------------------
# 効果モーションクラス
#-------------------------------------------------------------------------------

class EffectMotion(object):
    def __init__(self, data, user=None, header=None, targetlevel=0):
        """
        効果モーションインスタンスを生成。MotionElementと
        user(PlayerCard, EnemyCard)とheader(CardHeader)を引数に取る。
        """
        # 効果の種類
        self.type = data.get("type")
        # 効果属性
        self.element = data.get("element", None)
        # 効果値の種類
        self.damagetype = data.get("damagetype", None)
        # 効果値
        self.value = int(data.get("value", "0"))
        # 効果時間値
        self.duration = int(data.get("duration", "0"))

        # 召喚獣
        if data.hasfind("Beasts"):
            self.beasts = [e for e in data.getfind("Beasts")]
        else:
            self.beasts = []

        # 使用者(PlayerCard, EnemyCard)
        self.user = user
        # 使用カード(CardHeader)
        self.cardheader = header
        # 使用者の適正値(効果コンテントの場合は"4")
        self.vocation_val = header.get_vocation_val() if header else 4
        # 使用者の適正レベル(効果コンテントの場合は"1")
        self.vocation_level = header.get_vocation_level() if header else 1
        # 使用者のレベルもしくは効果コンテントの対象レベル
        self.level = user.level if user else targetlevel

        # 使用者の行動力修正(技能カード以外は全て"0")
        if header and header.type == "SkillCard":
            self.enhance_act = user.get_enhance_act()
        else:
            self.enhance_act = 0

    def is_effectcontent(self):
        return not bool(self.cardheader)

    def calc_effectvalue(self, target):
        """
        効果値から実数値を計算して返す。
        効果値が0の場合は実数値も0を返す。
        """
        value = self.value

        # 弱点属性だったら効果値+10
        if self.is_weakness(target):
            value += 10

        # ダメージタイプが"Max"の場合、最大HPを実数値として返す
        if self.damagetype == "Max":
            return target.maxlife
        # 効果値0以下の場合、0を実数値として返す
        elif value <= 0:
            return 0

        # レベル比の効果値を計算(レベル比じゃない場合はそのままの効果値)
        if not self.is_effectcontent() and self.damagetype == "LevelRatio":
            bonus = self.vocation_val + self.enhance_act
            bonus = bonus / 2 + bonus % 2
            value = value * (self.level + bonus)
            value = value / 2 + value % 2

        # 効果値から実数値を計算
        if not self.is_effectcontent():
            n = value / 5
            value = cw.cwpy.dice.roll(n, 10)
            n = value % 5 * 2

            if n:
                value += cw.cwpy.dice.roll(1, n)

        # 最低でも1ダメージとする
        if value <= 0:
            value = 1

        return value

    def calc_durationvalue(self):
        """
        効果時間値から適性レベルに合わせた実数値を計算して返す。
        効果コンテントの場合は計算せず効果時間値をそのまま返す。
        """
        if self.is_effectcontent():
            return self.duration
        elif self.vocation_level == 0:
            return self.duration * 50 / 100
        elif self.vocation_level == 1:
            return self.duration * 80 / 100
        elif self.vocation_level == 2:
            return self.duration
        elif self.vocation_level == 3:
            return self.duration * 120 / 100
        elif self.vocation_level == 4:
            return self.duration * 150 / 100
        else:
            return self.duration

    def calc_defensedvalue(self, value, target):
        """
        効果実数値に防御修正を加える。
        """
        if value == 0:
            return 0
        enhance_def = target.get_enhance_def()
        return max(1, (value * (10 - enhance_def)) / 10)

    def is_noeffect(self, target):
        """
        属性の相性が無効ならTrueを返す。
        """
        return is_noeffect(self.element, target)

    def is_weakness(self, target):
        """
        炎冷属性の弱点ならTrueを返す。
        """
        if self.element == "Fire" and target.weakness.get("fire"):
            return True
        elif self.element == "Ice" and target.weakness.get("ice"):
            return True
        else:
            return False

    def apply(self, target, success_res):
        """
        target(PlayerCard, EnemyCard)に
        効果モーションを適用する。
        """
        # 無効属性だったら処理中止
        if self.is_noeffect(target):
            return False

        # 意識不明だったら一部効果の処理中止
        if target.is_unconscious() and not self.type in CAN_UNCONSCIOUS:
            return False

        methodname = self.type.lower() + "_motion"
        method = getattr(self, methodname, None)

        if method:
            return method(target, success_res)
        return False

    #-----------------------------------------------------------------------
    #「生命力」関連効果
    #-----------------------------------------------------------------------
    def heal_motion(self, target, success_res):
        """
        回復。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)
        target.set_life(value)
        return 0 < value

    def damage_motion(self, target, success_res):
        """
        ダメージ。抵抗成功で半減。
        """
        value = self.calc_effectvalue(target)

        # 抵抗に成功したらダメージ値半減
        if success_res:
            # 切り上げ
            value = int(value / 2.0 + 0.5)

        # 防御修正
        self.calc_defensedvalue(value, target)
        target.set_life(-value)

        # 睡眠解除
        if target.is_sleep():
            target.set_mentality("Normal", 0)
        return 0 < value

    def absorb_motion(self, target, success_res):
        """
        吸収。
        """
        value = self.calc_effectvalue(target)

        # 抵抗に成功したらダメージ値半減
        if success_res:
            # 切り上げ
            value = int(value / 2.0 + 0.5)

        # 防御修正
        self.calc_defensedvalue(value, target)
        target.set_life(-value)

        # 与えたダメージ分、使用者回復
        if self.user:
            self.user.set_life(value)
        return 0 < value

    #-----------------------------------------------------------------------
    #「肉体」関連効果
    #-----------------------------------------------------------------------
    def paralyze_motion(self, target, success_res):
        """
        麻痺状態。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_paralyze(value)
        return 0 < value

    def disparalyze_motion(self, target, success_res):
        """
        麻痺解除。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_paralyze(-value)
        return 0 < value

    def poison_motion(self, target, success_res):
        """
        中毒状態。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_poison(value)
        return 0 < value

    def dispoison_motion(self, target, success_res):
        """
        中毒解除。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_poison(-value)
        return 0 < value

    #-----------------------------------------------------------------------
    #「技能」関連効果
    #-----------------------------------------------------------------------
    def getskillpower_motion(self, target, success_res):
        """
        精神力回復。抵抗成功で無効化。
        """
        target.set_skillpower(True)
        return True

    def loseskillpower_motion(self, target, success_res):
        """
        精神力不能。抵抗成功で無効化。
        """
        target.set_skillpower(False)
        return True

    #-----------------------------------------------------------------------
    #「精神」関連効果
    #-----------------------------------------------------------------------
    def mentality(self, target, success_res):
        """
        精神状態変更(睡眠・混乱・激昂・勇敢・恐慌・正常)。
        """
        if self.type.title() == "Normal":
            duration = 0
        else:
            duration = self.calc_durationvalue()
        eff = target.mentality <> self.type.title() and duration <> target.mentality_dur
        target.set_mentality(self.type.title(), duration)
        return eff

    def sleep_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    def confuse_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    def overheat_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    def brave_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    def panic_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    def normal_motion(self, *args, **kwargs):
        return self.mentality(*args, **kwargs)

    #-----------------------------------------------------------------------
    #「魔法」関連効果
    #-----------------------------------------------------------------------
    def bind_motion(self, target, success_res):
        """
        束縛状態。
        """
        duration = self.calc_durationvalue()
        target.set_bind(duration)
        return 0 < duration

    def disbind_motion(self, target, success_res):
        """
        束縛解除。
        """
        duration = target.bind
        target.set_bind(0)
        return 0 < duration

    def silence_motion(self, target, success_res):
        """
        沈黙状態。
        """
        duration = self.calc_durationvalue()
        target.set_silence(duration)
        return 0 < duration

    def dissilence_motion(self, target, success_res):
        """
        沈黙解除。
        """
        duration = target.silence
        target.set_silence(0)
        return 0 < duration

    def faceup_motion(self, target, success_res):
        """
        暴露状態。
        """
        duration = self.calc_durationvalue()
        target.set_faceup(duration)
        return 0 < duration

    def facedown_motion(self, target, success_res):
        """
        暴露解除。
        """
        duration = target.faceup
        target.set_faceup(0)
        return 0 < duration

    def antimagic_motion(self, target, success_res):
        """
        魔法無効化状態。
        """
        duration = self.calc_durationvalue()
        target.set_antimagic(duration)
        return 0 < duration

    def disantimagic_motion(self, target, success_res):
        """
        魔法無効化解除。
        """
        duration = target.antimagic
        target.set_antimagic(0)
        return 0 < duration

    #-----------------------------------------------------------------------
    #「能力」関連効果
    #-----------------------------------------------------------------------
    def enhanceaction_motion(self, target, success_res):
        """
        行動力変化。
        """
        if self.value <> 0:
            duration = self.calc_durationvalue()
        else:
            duration = 0
        eff = target.enhance_act <> self.value and target.enhance_act_dur <> duration
        target.set_enhance_act(self.value, duration)
        return eff

    def enhanceavoid_motion(self, target, success_res):
        """
        回避力変化。
        """
        if self.value <> 0:
            duration = self.calc_durationvalue()
        else:
            duration = 0
        eff = target.enhance_avo <> self.value and target.enhance_avo_dur <> duration
        target.set_enhance_avo(self.value, duration)
        return eff

    def enhanceresist_motion(self, target, success_res):
        """
        抵抗力変化。
        """
        if self.value <> 0:
            duration = self.calc_durationvalue()
        else:
            duration = 0
        eff = target.enhance_res <> self.value and target.enhance_res_dur <> duration
        target.set_enhance_res(self.value, duration)
        return eff

    def enhancedefense_motion(self, target, success_res):
        """
        防御力変化。
        """
        if self.value <> 0:
            duration = self.calc_durationvalue()
        else:
            duration = 0
        eff = target.enhance_def <> self.value and target.enhance_def_dur <> duration
        target.set_enhance_def(self.value, duration)
        return eff

    #-----------------------------------------------------------------------
    #「消滅」関連効果
    #-----------------------------------------------------------------------
    def vanishtarget_motion(self, target, success_res):
        """
        対象消去。
        """
        target.set_vanish()
        return True

    def vanishcard_motion(self, target, success_res):
        """
        カード消去。
        """
        if cw.cwpy.battle:
            target.deck.throwaway(target)
            return True
        return False

    def vanishbeast_motion(self, target, success_res):
        """
        召喚獣消去。
        """
        return target.set_beast(vanish=True)

    #-----------------------------------------------------------------------
    #「カード」関連効果
    #-----------------------------------------------------------------------
    def dealattackcard_motion(self, target, success_res):
        """
        通常攻撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(1)
            return True
        return False

    def dealpowerfulattackcard_motion(self, target, success_res):
        """
        渾身の一撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(2)
            return True
        return False

    def dealcriticalattackcard_motion(self, target, success_res):
        """
        会心の一撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(3)
            return True
        return False

    def dealfeintcard_motion(self, target, success_res):
        """
        フェイント配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(4)
            return True
        return False

    def dealdefensecard_motion(self, target, success_res):
        """
        防御配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(5)
            return True
        return False

    def dealdistancecard_motion(self, target, success_res):
        """
        見切り配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(6)
            return True
        return False

    def dealconfusecard_motion(self, target, success_res):
        """
        混乱配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(-1)
            return True
        return False

    def dealskillcard_motion(self, target, success_res):
        """
        特殊技能配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard()
            return True
        return False

    #-----------------------------------------------------------------------
    #「召喚」関連効果
    #-----------------------------------------------------------------------
    def summonbeast_motion(self, target, success_res):
        """
        召喚獣召喚。
        """
        eff = False
        for e in self.beasts:
            eff |= target.set_beast(e)
        return eff

#-------------------------------------------------------------------------------
# 有効な効果モーションのチェック用関数
#-------------------------------------------------------------------------------

def get_effectivetargets(header, targets):
    """カード効果が有効なターゲットのリストをフィルタリングして返す。
    header: CardHeader
    targets: Characters
    """
    motions = header.carddata.getfind("Motions").getchildren()
    sets = set()

    def narrow(targets):
        targets2 = []
        for target in targets:
            if not header.is_noeffect(target):
                targets2.append(target)
        return targets2

    for motion in motions:
        s = motion.get("type", "").lower()

        if s in checkingmethod_dict:
            method, flag = checkingmethod_dict[s]
            sets.update([t for t in targets if getattr(t, method)() == flag])
        else:
            return narrow(targets)

    return narrow(sets)

# key: モーション名, value: チェック用メソッド名の辞書
checkingmethod_dict = {"heal" : ("is_injured", True),
                       "dispoison" : ("is_poison", True),
                       "disparalyze" : ("is_paralyze", True),
##                       "sleep" : ("is_sleep", False),
##                       "confuse" : ("is_confuse", False),
##                       "overheat" : ("is_overheat", False),
##                       "brave" : ("is_brave", False),
##                       "panic" : ("is_panic", False),
                       "normal" : ("is_normal", False),
                       "disbind" : ("is_bind", True),
                       "dissilence" : ("is_silence", True),
                       "facedown" : ("is_faceup", True),
                       "disantimagic" : ("is_antimagic", True),
                       }

def main():
    pass

if __name__ == "__main__":
    main()
