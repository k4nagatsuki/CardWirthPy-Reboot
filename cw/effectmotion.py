#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def check_noeffect(effecttype, target, ignore_antimagic=False):
    noeffect_wpn = target.noeffect.get("weapon")
    noeffect_mgc = target.noeffect.get("magic")
    antimagic = target.is_antimagic() if not ignore_antimagic else False

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
        if noeffect_wpn and noeffect_mgc:
            return True

    # 物理的魔法属性
    elif effecttype == "PhysicalMagic":
        if noeffect_wpn or noeffect_mgc or antimagic:
            return True

    return False

class Effect(object):
    def __init__(self, motions, d, battlespeed=False):
        self.user = d.get("user", None)
        self.inusecard = d.get("inusecard", None)
        self.level = d.get("level", 0)
        self.successrate = d.get("successrate", 0)
        self.effecttype = d.get("effecttype", "Physic")
        self.resisttype = d.get("resisttype", "Avoid")
        self.soundpath = d.get("soundpath", "")
        self.volume = d.get("volume", 100)
        self.loopcount = d.get("loopcount", 1)
        self.channel = d.get("channel", 0)
        self.fade = d.get("fadein", 0)
        self.visualeffect = d.get("visualeffect", "None")
        self.battlespeed = battlespeed

        # 選択メンバの能力参照(Wsn.2)
        self.refability = d.get("refability", False)
        if self.refability:
            physical = d.get("physical", "Dex")
            mental = d.get("mental", "Aggressive")
            self.vocation = (physical.lower(), mental.lower())
        else:
            self.vocation = None

        # 行動力修正の影響を受けるか
        # アクションカードまたは特殊技能の場合のみ
        self.is_enhance_act = self.inusecard and self.inusecard.type in ("ActionCard", "SkillCard")

        if self.user and self.inusecard:
            self.motions = [EffectMotion(e, self.user, self.inusecard, refability=self.refability, vocation=self.vocation)
                                                            for e in motions]
        else:
            self.motions = [EffectMotion(e, targetlevel=self.level, refability=self.refability, vocation=self.vocation)
                                                            for e in motions]

    def update_status(self):
        if self.refability:
            ccard = cw.cwpy.event.get_selectedmember()
            self._level = ccard.level if ccard else 0
        else:
            self._level = cw.util.numwrap(self.user.level if self.user else self.level, -65536, 65536)
        for motion in self.motions:
            motion.update_status()

    def get_level(self):
        """使用者のレベルもしくは効果コンテントの対象レベル。"""
        return self._level

    def apply(self, target, event=False):
        if isinstance(target, Character) and self.check_enabledtarget(target, event):
            return self.apply_charactercard(target, event=event)
        else:
            return False

    def apply_charactercard(self, target, event=False):
        """
        Characterインスタンスに効果モーションを適用する。
        """
        # 反転状態だったら処理中止
        if not event and target.is_reversed():
            return

        if target.is_unconscious() and not self.has_motions(CAN_UNCONSCIOUS):
            return

        # 各種判定処理
        allmissed = self.successrate <= -5
        allsuccess = self.successrate >= 5
        success_res = False
        success_avo = False

        # 吸収後のエフェクトを発生させるか
        # 判定するために記憶しておく
        if self.user:
            userlife = self.user.life
        else:
            userlife = 0

        if allmissed:
            # 完全失敗(回避抵抗不可時だけは絶対成功)
            noeffect = self.check_noeffect(target)
            success_res = self.resisttype == "Resist" and target.is_resistable()
            success_avo = self.resisttype == "Avoid" and target.is_avoidable()
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

        if not success_res and self.resisttype == "Resist" and not target.is_resistable(use_enhance=False):
            allsuccess = True
        if not success_avo and self.resisttype == "Avoid" and not target.is_avoidable(use_enhance=False):
            allsuccess = True

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
            elif target.deck and target.deck.get_used():
                header = target.deck.get_used()
            else:
                header = None
            if header:
                avoid, resist, defense = header.get_enhance_val_used()
                if (0 <> avoid and self.resisttype == "Avoid") or\
                   (0 <> resist and self.resisttype == "Resist"):
                    guardcard = header

        # 所有ボーナス(アイテムは消耗しない)
        cards = target.get_pocketcards(cw.POCKET_BEAST)
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
            if guardcard:
                cw.cwpy.play_sound("equipment", True)
                cw.cwpy.set_guardcardimg(target, guardcard)
                cw.cwpy.draw()
                waitrate = (cw.cwpy.setting.get_dealspeed(self.battlespeed)+1) * 2
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
                cw.cwpy.clear_guardcardimg()
                cw.cwpy.draw()

            # 回避・抵抗段階での消耗
            for header in consume:
                header.set_uselimit(-1)

        consume.clear()

        # 音鳴らす
        if not success_avo:
            cw.cwpy.play_sound_with(self.soundpath, subvolume=self.volume, loopcount=self.loopcount,
                                    channel=self.channel, fade=self.fade)

        resisted = False
        if success_avo:
            cw.cwpy.play_sound("avoid", True)
            cw.cwpy.draw()
            cw.cwpy.wait_frame(1, cw.cwpy.setting.can_skipanimation)
            if self.motions:
                if noeffect:
                    cw.cwpy.advlog.effect_failed(target)
                else:
                    cw.cwpy.advlog.avoid(target)
            return False
        elif noeffect or (success_res and not hasdamage):
            cw.cwpy.play_sound("ineffective", True)
            self.animate(target, True)
            if self.motions:
                cw.cwpy.advlog.noeffect(target)
            return False

        # 効果モーションを発動
        effectual = False
        for motion in self.motions:
            effectual |= motion.apply(target, success_res)

            if motion.type.lower() in ("damage", "absorb") and motion.can_apply(target):
                # ダメージ軽減によるカード消耗
                consume.clear()
                for header in cards:
                    avoid, resist, defense = header.get_enhance_val()
                    if 0 <> defense:
                        consume.add(header)

                for header in consume:
                    header.set_uselimit(-1)

        if not effectual:
            # 効果無し
            cw.cwpy.play_sound("ineffective", True)
            if self.motions:
                cw.cwpy.advlog.effect_failed(target)

        # アニメーション・画像更新(対象消去されていなかったら)
        if not target.is_vanished():
            # 死亡していたら、ステータスを元に戻す
            if target.is_unconscious():
                target.set_unconsciousstatus()

            self.animate(target, True)

        # 吸収効果があったら、使用者のカードを回転させて更新する。
        if self.user and self.count_motion("absorb")\
                     and userlife < self.user.life:
            cw.cwpy.play_sound("bind", True)
            cw.animation.animate_sprite(self.user, "hide", battlespeed=self.battlespeed)
            self.user.update_image()
            cw.animation.animate_sprite(self.user, "deal", battlespeed=self.battlespeed)

        return True

    def check_noeffect(self, target):
        return check_noeffect(self.effecttype, target)

    def check_avoid(self, target):
        if self.resisttype == "Avoid" and target.is_avoidable():
            targetbonus = target.get_enhance_avo()
            if 10 <= targetbonus:
                return True
            elif targetbonus <= -10:
                return False

            if self.refability:
                ccard = cw.cwpy.event.get_selectedmember()
                userbonus = ccard.get_bonus(self.vocation, enhance_act=True)
            elif self.user and self.inusecard:
                uservocation = self.inusecard.vocation
                userbonus = self.user.get_bonus(uservocation, enhance_act=self.is_enhance_act)
            else:
                userbonus = 6

            vocation = ("agl", "cautious")
            level = self.user.level if self.user else self.get_level()
            return target.decide_outcome(level, vocation, userbonus, targetbonus, self.successrate)

        return False

    def check_resist(self, target):
        if self.resisttype == "Resist" and target.is_resistable():
            targetbonus = target.get_enhance_res()
            if 10 <= targetbonus:
                return True
            elif targetbonus <= -10:
                return False

            if self.refability:
                ccard = cw.cwpy.event.get_selectedmember()
                userbonus = ccard.get_bonus(self.vocation, enhance_act=True)
            elif self.user and self.inusecard:
                uservocation = self.inusecard.vocation
                userbonus =  self.user.get_bonus(uservocation, enhance_act=self.is_enhance_act)
            else:
                userbonus = 6

            vocation = ("min", "brave")
            level = self.user.level if self.user else self.get_level()
            return target.decide_outcome(level, vocation, userbonus, targetbonus, self.successrate)

        return False

    def animate(self, target, update_image=False):
        """
        targetにtypenameの効果アニメーションを実行する。
        update_imageがTrueだったら、アニメ後にtargetの画像を更新する。
        """
        battlespeed = self.battlespeed
        # 隠れているカードやFriendCardはアニメーションさせない
        if target.status == "hidden":
            if update_image:
                target.update_image()
                cw.cwpy.draw(clip=target.rect)

            if self.soundpath and cw.cwpy.has_sound(self.soundpath):
                waitrate = (cw.cwpy.setting.get_dealspeed(battlespeed)+1) * 2
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

        # 横振動(地震)
        elif self.visualeffect == "Horizontal":
            cw.animation.animate_sprite(target, "lateralvibe", battlespeed=battlespeed)

            if update_image:
                target.update_image()
                cw.cwpy.draw(clip=target.rect)

        # 縦振動(振動)
        elif self.visualeffect == "Vertical":
            cw.animation.animate_sprite(target, "axialvibe", battlespeed=battlespeed)

            if update_image:
                target.update_image()
                cw.cwpy.draw(clip=target.rect)
        # 反転
        elif self.visualeffect == "Reverse":
            target.hide_inusecardimg = False
            cw.animation.animate_sprite(target, "hide", battlespeed=battlespeed)
            target.hide_inusecardimg = True

            if update_image:
                target.update_image()

            cw.animation.animate_sprite(target, "deal", battlespeed=battlespeed)
        # アニメーションなし
        else:
            if update_image:
                target.update_image()
                cw.cwpy.draw(clip=target.rect)
            cw.cwpy.wait_frame(1, cw.cwpy.setting.can_skipanimation)

    def check_enabledtarget(self, target, event=False):
        """
        表示されていないか(敵のみ)、対象消去されている場合、
        反転している場合(イベント除く)は有効なターゲットではない。
        """
        if target.status == "hidden" and\
                not isinstance(target, cw.sprite.card.PlayerCard) and\
                not isinstance(target, cw.sprite.card.FriendCard):
            return False
        elif isinstance(target, Character):
            flag = bool(not target.is_vanished())
            flag &= event or not target.is_reversed()
            if flag and self.motions:
                # 回復等が含まれていない場合、意識不明の対象は対象外に
                flag = False
                for eff in self.motions:
                    if target.is_unconscious() and not eff.type in CAN_UNCONSCIOUS:
                        continue
                    flag = True
                    break
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
    def __init__(self, data, user=None, header=None, targetlevel=0, refability=False, vocation=None):
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
        self.beasts = data.getfind("Beasts", raiseerror=False)

        # 使用者(PlayerCard, EnemyCard)
        self.user = user
        # 行動力修正の影響を受けるか
        # アクションカードまたは特殊技能の場合のみ
        self.is_enhance_act = header and header.type in ("ActionCard", "SkillCard")
        # 使用カード(CardHeader)
        self.cardheader = header
        # 選択メンバの能力参照(Wsn.2)
        self.refability = refability
        if refability:
            self._vocation = vocation
        else:
            # 使用者のレベルもしくは効果コンテントの対象レベル
            self._targetlevel = targetlevel
            self.update_status()

    def update_status(self):
        if self.refability:
            self._enhance_act = 0
            ccard = cw.cwpy.event.get_selectedmember()
            self._vocation_val = get_vocation_val(ccard, self._vocation, enhance_act=True) if ccard else 6
            self._vocation_level = get_vocation_level(ccard, self._vocation, enhance_act=True) if ccard else 2
            self._level = ccard.level if ccard else 0
        else:
            # 使用者の行動力修正
            self._enhance_act = self.user.get_enhance_act() if self.is_enhance_act else 0
            # 使用者の適性値(効果コンテントの場合は"6")
            self._vocation_val = self.cardheader.get_vocation_val(self.user) if self.cardheader else 6
            # 使用者の適性レベル(効果コンテントの場合は"2")
            # スキルカードの場合は行動力修正の影響を受ける
            self._vocation_level = self.cardheader.get_vocation_level(self.user, enhance_act=self.is_enhance_act) if self.cardheader else 2
            # 使用者のレベルもしくは効果コンテントの対象レベル
            self._level = cw.util.numwrap(self.user.level if self.user else self._targetlevel, -65536, 65536)

    def get_vocation_val(self):
        """成功率や効果値の計算に使用する適性値を返す。"""
        return self._vocation_val

    def get_vocation_level(self):
        """成功率や効果値の計算に使用するレベルを返す。"""
        return self._vocation_level

    def get_enhance_act(self):
        """使用者の行動力修正(技能カード以外は全て"0")。"""
        return self._enhance_act

    def get_level(self):
        """使用者のレベルもしくは効果コンテントの対象レベル。"""
        return self._level

    def is_effectcontent(self):
        return not bool(self.cardheader)

    def calc_skillpowervalue(self):
        # 固定値(Wsn.1)
        value = self.value
        if self.damagetype == "Fixed":
            return value

        # それ以外は最大値処理
        return 999

    def calc_effectvalue(self, target, physical=False):
        """
        効果値から実数値を計算して返す。
        効果値が0の場合は実数値も0を返す。
        """
        value = self.value
        minvalue = 1 if self.type in ("Heal", "Damage", "Absorb") else 0

        # 固定値(Wsn.1)
        if self.damagetype == "Fixed":
            return max(minvalue, value)

        # ダメージタイプが"Max"の場合、最大HPを実数値として返す
        if self.damagetype == "Max":
            return target.maxlife
        elif value <= 0:
            # 効果値0以下の場合、0を実数値として返す
            # (ダメージ・回復・吸収を除く)
            return minvalue

        # レベル比の効果値を計算(レベル比じゃない場合はそのままの効果値)
        if self.damagetype == "LevelRatio":
            bonus = self.get_vocation_val() + self.get_enhance_act()
            bonus = bonus // 2 + bonus % 2
            value = value * (self.get_level() + bonus)
            value = value // 2 + value % 2

        # 弱点属性だったら効果値+10
        if self.is_weakness(target):
            value += 10

        # 中毒・麻痺なら効果値のまま返す
        if physical:
            # 最低でも0とする
            if value < minvalue:
                value = minvalue
            return value

        # 効果値から実数値を計算
        n = value // 5
        out_value = cw.cwpy.dice.roll(n, 10)-1
        n = value % 5 * 2

        if 0 < value and n:
            out_value += cw.cwpy.dice.roll(1, n)

        # 最低でも1ダメージとする
        if out_value < minvalue:
            out_value = minvalue

        return out_value

    def calc_durationvalue(self, target, enhance):
        """
        効果時間値から適性レベルに合わせた実数値を計算して返す。
        効果コンテントの場合も計算する。
        """
        if enhance and self.duration <= 0:
            minvalue = 0
        else:
            minvalue = 1

        # 弱点属性だったら適性レベル+1のボーナス
        vocation_level = self.get_vocation_level()
        if self.is_weakness(target):
            vocation_level += 1

        if vocation_level <= 0:
            return cw.util.numwrap(self.duration * 50 / 100, minvalue, 999)
        elif vocation_level == 1:
            return cw.util.numwrap(self.duration * 80 / 100, minvalue, 999)
        elif vocation_level == 2:
            return cw.util.numwrap(self.duration, minvalue, 999)
        elif vocation_level == 3:
            return cw.util.numwrap(self.duration * 120 / 100, minvalue, 999)
        elif vocation_level >= 4:
            return cw.util.numwrap(self.duration * 150 / 100, minvalue, 999)
        else:
            assert False

    def calc_defensedvalue(self, value, target):
        """
        効果実数値に防御修正を加える。
        """
        if value == 0:
            return 0
        enhance_def = target.get_enhance_def()
        if 10 <= enhance_def:
            return 0
        elif enhance_def <= -10:
            return value * 4
        return max(1, (value * (100 - enhance_def * 10)) / 100)

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

    def can_apply(self, target):
        """
        実際に効果を適用しようとした時に無効であればFalseを返す。
        """
        # 無効属性だったら処理中止
        if self.is_noeffect(target):
            return False

        # 意識不明だったら一部効果の処理中止
        if target.is_unconscious() and not self.type in CAN_UNCONSCIOUS:
            return False

        return True

    def apply(self, target, success_res):
        """
        target(PlayerCard, EnemyCard)に
        効果モーションを適用する。
        """
        if not self.can_apply(target):
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
        if success_res:
            return False
        value = self.calc_effectvalue(target)
        oldlife = target.life
        origvalue = value
        value = target.set_life(value)
        if 0 < value:
            cw.cwpy.advlog.heal_motion(target, origvalue, target.life, oldlife)
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
        if self.damagetype <> "Fixed":
            # 互換動作: 1.20以前は最大値ダメージも防御修正による影響を受ける
            if cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
                value = self.calc_defensedvalue(value, target)
            else:
                if self.damagetype <> "Max":
                    value = self.calc_defensedvalue(value, target)

        oldlife = target.life
        origvalue = value
        target.set_life(-value)

        # 睡眠解除
        dissleep = target.is_sleep()
        if dissleep:
            target.set_mentality("Normal", 0)
        if 0 < value:
            cw.cwpy.advlog.damage_motion(target, origvalue, target.life, oldlife, dissleep)
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
        if self.damagetype <> "Fixed":
            # 互換動作: 1.20以前は最大値ダメージも防御修正による影響を受ける
            if cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(cw.HINT_CARD)):
                value = self.calc_defensedvalue(value, target)
            else:
                if self.damagetype <> "Max":
                    value = self.calc_defensedvalue(value, target)

        oldlife = target.life
        origvalue = value
        value = -(target.set_life(-value))

        # 睡眠解除
        dissleep = target.is_sleep()
        if dissleep:
            target.set_mentality("Normal", 0)

        # 与えたダメージ分、使用者回復
        if self.user:
            oldulife = self.user.life
            self.user.set_life(value)
            ulife = self.user.life
        else:
            ulife = 0
            oldulife = 0
        if 0 < value:
            cw.cwpy.advlog.absorb_motion(self.user, value, ulife, oldulife, target, origvalue, target.life, oldlife, dissleep)
        return 0 < value

    #-----------------------------------------------------------------------
    #「肉体」関連効果
    #-----------------------------------------------------------------------
    def paralyze_motion(self, target, success_res):
        """
        麻痺状態。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_effectvalue(target, physical=True)

        if self.damagetype == "Max":
            value = 40

        oldvalue = target.paralyze
        target.set_paralyze(value)
        if 0 < value:
            cw.cwpy.advlog.paralyze_motion(target, target.paralyze, oldvalue)
        return 0 < value

    def disparalyze_motion(self, target, success_res):
        """
        麻痺解除。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_effectvalue(target, physical=True)

        if self.damagetype == "Max":
            value = 40

        oldvalue = target.paralyze
        value = target.set_paralyze(-value)
        if value < 0:
            cw.cwpy.advlog.disparalyze_motion(target, target.paralyze, oldvalue)
        return value < 0

    def poison_motion(self, target, success_res):
        """
        中毒状態。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_effectvalue(target, physical=True)

        if self.damagetype == "Max":
            value = 40

        oldvalue = target.poison
        target.set_poison(value)
        if 0 < value:
            cw.cwpy.advlog.poison_motion(target, target.poison, oldvalue)
        return 0 < value

    def dispoison_motion(self, target, success_res):
        """
        中毒解除。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_effectvalue(target, physical=True)

        if self.damagetype == "Max":
            value = 40

        oldvalue = target.poison
        value = target.set_poison(-value)
        if value < 0:
            cw.cwpy.advlog.dispoison_motion(target, target.poison, oldvalue)
        return value < 0

    #-----------------------------------------------------------------------
    #「技能」関連効果
    #-----------------------------------------------------------------------
    def getskillpower_motion(self, target, success_res):
        """
        精神力回復。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_skillpowervalue()
        target.set_skillpower(value)
        cw.cwpy.advlog.getskillpower_motion(target, value)
        return True

    def loseskillpower_motion(self, target, success_res):
        """
        精神力不能。抵抗成功で無効化。
        """
        if success_res:
            return False
        value = self.calc_skillpowervalue()
        target.set_skillpower(-value)
        cw.cwpy.advlog.loseskillpower_motion(target, value)
        return True

    #-----------------------------------------------------------------------
    #「精神」関連効果
    #-----------------------------------------------------------------------
    def mentality(self, target, success_res):
        """
        精神状態変更(睡眠・混乱・激昂・勇敢・恐慌・正常)。
        """
        if success_res:
            return False
        if target.reversed:
            # 隠蔽中は、ダメージによる睡眠解除を除いて
            # 精神状態の変化は無い
            return False
        oldmentality = target.mentality
        oldduration = target.mentality_dur
        if self.type.title() == "Normal":
            duration = 0
            eff = target.mentality <> "Normal"
            target.set_mentality(self.type.title(), duration)
        else:
            duration = self.calc_durationvalue(target, False)
            if duration == 0:
                eff = target.mentality <> "Normal"
                target.set_mentality("Normal", duration)
            else:
                eff = target.mentality <> self.type.title() or target.mentality_dur < duration
                target.set_mentality(self.type.title(), duration, overwrite=False)
        if eff:
            cw.cwpy.advlog.mentality_motion(target, self.type.title(), duration, oldmentality, oldduration)
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
        if success_res:
            return False
        duration = self.calc_durationvalue(target, False)
        eff = target.bind < duration
        oldvalue = target.bind
        target.set_bind(duration, overwrite=False)
        if eff:
            cw.cwpy.advlog.bind_motion(target, target.bind, oldvalue)
        return eff

    def disbind_motion(self, target, success_res):
        """
        束縛解除。
        """
        if success_res:
            return False
        duration = target.bind
        oldvalue = duration
        target.set_bind(0)
        if 0 < duration:
            cw.cwpy.advlog.disbind_motion(target, target.bind, oldvalue)
        return 0 < duration

    def silence_motion(self, target, success_res):
        """
        沈黙状態。
        """
        if success_res:
            return False
        duration = self.calc_durationvalue(target, False)
        eff = target.silence < duration
        oldvalue = target.silence
        target.set_silence(duration, overwrite=False)
        if eff:
            cw.cwpy.advlog.silence_motion(target, target.silence, oldvalue)
        return eff

    def dissilence_motion(self, target, success_res):
        """
        沈黙解除。
        """
        if success_res:
            return False
        duration = target.silence
        oldvalue = duration
        target.set_silence(0)
        if 0 < duration:
            cw.cwpy.advlog.dissilence_motion(target, target.silence, oldvalue)
        return 0 < duration

    def faceup_motion(self, target, success_res):
        """
        暴露状態。
        """
        if success_res:
            return False
        duration = self.calc_durationvalue(target, False)
        eff = target.faceup < duration
        oldvalue = target.faceup
        target.set_faceup(duration, overwrite=False)
        if eff:
            cw.cwpy.advlog.faceup_motion(target, target.faceup, oldvalue)
        return eff

    def facedown_motion(self, target, success_res):
        """
        暴露解除。
        """
        if success_res:
            return False
        duration = target.faceup
        oldvalue = duration
        target.set_faceup(0)
        if 0 < duration:
            cw.cwpy.advlog.facedown_motion(target, target.faceup, oldvalue)
        return 0 < duration

    def antimagic_motion(self, target, success_res):
        """
        魔法無効化状態。
        """
        if success_res:
            return False
        duration = self.calc_durationvalue(target, False)
        eff = target.antimagic < duration
        oldvalue = target.antimagic
        target.set_antimagic(duration, overwrite=False)
        if eff:
            cw.cwpy.advlog.antimagic_motion(target, target.antimagic, oldvalue)
        return eff

    def disantimagic_motion(self, target, success_res):
        """
        魔法無効化解除。
        """
        if success_res:
            return False
        duration = target.antimagic
        oldvalue = duration
        target.set_antimagic(0)
        if 0 < duration:
            cw.cwpy.advlog.disantimagic_motion(target, target.antimagic, oldvalue)
        return 0 < duration

    #-----------------------------------------------------------------------
    #「能力」関連効果
    #-----------------------------------------------------------------------
    def enhanceaction_motion(self, target, success_res):
        """
        行動力変化。
        """
        if success_res:
            return False
        value = cw.util.numwrap(self.value, -10, 10)
        if value <> 0:
            duration = self.calc_durationvalue(target, True)
        else:
            duration = 0
        oldvalue = target.enhance_act
        eff = target.enhance_act <> value or target.enhance_act_dur < duration
        if eff:
            target.set_enhance_act(value, duration)
            cw.cwpy.advlog.enhanceaction_motion(target, target.enhance_act, oldvalue)
        return eff

    def enhanceavoid_motion(self, target, success_res):
        """
        回避力変化。
        """
        if success_res:
            return False
        value = cw.util.numwrap(self.value, -10, 10)
        if value <> 0:
            duration = self.calc_durationvalue(target, True)
        else:
            duration = 0
        oldvalue = target.enhance_avo
        eff = target.enhance_avo <> value or target.enhance_avo_dur < duration
        if eff:
            target.set_enhance_avo(value, duration)
            cw.cwpy.advlog.enhanceavoid_motion(target, target.enhance_avo, oldvalue)
        return eff

    def enhanceresist_motion(self, target, success_res):
        """
        抵抗力変化。
        """
        if success_res:
            return False
        value = cw.util.numwrap(self.value, -10, 10)
        if value <> 0:
            duration = self.calc_durationvalue(target, True)
        else:
            duration = 0
        oldvalue = target.enhance_res
        eff = target.enhance_res <> value or target.enhance_res_dur < duration
        if eff:
            target.set_enhance_res(value, duration)
            cw.cwpy.advlog.enhanceresist_motion(target, target.enhance_res, oldvalue)
        return eff

    def enhancedefense_motion(self, target, success_res):
        """
        防御力変化。
        """
        if success_res:
            return False
        value = cw.util.numwrap(self.value, -10, 10)
        if value <> 0:
            duration = self.calc_durationvalue(target, True)
        else:
            duration = 0
        oldvalue = target.enhance_def
        eff = target.enhance_def <> value or target.enhance_def_dur < duration
        if eff:
            target.set_enhance_def(value, duration)
            cw.cwpy.advlog.enhancedefense_motion(target, target.enhance_def, oldvalue)
        return eff

    #-----------------------------------------------------------------------
    #「消滅」関連効果
    #-----------------------------------------------------------------------
    def vanishtarget_motion(self, target, success_res):
        """
        対象消去。
        """
        if success_res:
            return False
        target.set_vanish(battlespeed=self.cardheader and cw.cwpy.is_battlestatus())
        if self.cardheader:
            runaway = cw.cwpy.msgs["runaway_keycode"] in self.cardheader.get_keycodes(with_name=False)
        else:
            runaway = False
        cw.cwpy.advlog.vanishtarget_motion(target, runaway)
        return True

    def vanishcard_motion(self, target, success_res):
        """
        カード消去。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.vanishcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.throwaway()
            return True
        return False

    def vanishbeast_motion(self, target, success_res):
        """
        召喚獣消去。
        """
        if success_res:
            return False
        eff = target.set_beast(vanish=True)
        if eff:
            cw.cwpy.advlog.vanishbeast_motion(target)
        return eff

    #-----------------------------------------------------------------------
    #「カード」関連効果
    #-----------------------------------------------------------------------
    def dealattackcard_motion(self, target, success_res):
        """
        通常攻撃配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealattackcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(1)
            return True
        return False

    def dealpowerfulattackcard_motion(self, target, success_res):
        """
        渾身の一撃配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealpowerfulattackcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(2)
            return True
        return False

    def dealcriticalattackcard_motion(self, target, success_res):
        """
        会心の一撃配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealcriticalattackcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(3)
            return True
        return False

    def dealfeintcard_motion(self, target, success_res):
        """
        フェイント配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealfeintcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(4)
            return True
        return False

    def dealdefensecard_motion(self, target, success_res):
        """
        防御配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealdefensecard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(5)
            return True
        return False

    def dealdistancecard_motion(self, target, success_res):
        """
        見切り配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealdistancecard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(6)
            return True
        return False

    def dealconfusecard_motion(self, target, success_res):
        """
        混乱配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealconfusecard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard(-1)
            return True
        return False

    def dealskillcard_motion(self, target, success_res):
        """
        特殊技能配布。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        if cw.cwpy.battle:
            cw.cwpy.advlog.dealskillcard_motion(target, target.is_inactive(), cw.cwpy.is_battlestatus())
            target.deck.set_nextcard()
            return True
        return False

    def cancelaction_motion(self, target, success_res):
        """
        行動キャンセル(1.50)。
        """
        if success_res:
            return False
        if target.is_inactive():
            return False
        cw.cwpy.advlog.cancelaction_motion(target, cw.cwpy.is_battlestatus())
        if target.actiondata:
            target.clear_action()
            return True
        return True

    #-----------------------------------------------------------------------
    #「召喚」関連効果
    #-----------------------------------------------------------------------
    def summonbeast_motion(self, target, success_res):
        """
        召喚獣召喚。
        """
        if success_res:
            return False
        eff = False
        for e in self.beasts:
            e2 = cw.cwpy.sdata.get_carddata(e)
            if e2 is None:
                continue
            cwxpath = e2.get_cwxpath()
            if e2 is e:
                e = cw.data.copydata(e)
            else:
                e = e2
            if cwxpath:
                e.attrib["cwxpath"] = cwxpath
            self.duration = e.getint("Property/UseLimit")
            recycle = cw.cwpy.msgs["recycle_keycode"] in cw.util.decodetextlist(e.gettext("Property/KeyCodes", u""))
            duration = self.calc_durationvalue(target, recycle)
            e.find("Property/UseLimit").text = str(duration)
            header = self.cardheader
            if not header and (cw.cwpy.event.in_inusecardevent or cw.cwpy.event.in_cardeffectmotion):
                # 使用時イベント中の効果コンテントからの実行の時
                header = cw.cwpy.event.get_inusecard()
            if target.set_beast(e, is_scenariocard=not header or (header.scenariocard and not header.carddata.gettext("Property/Materials", ""))):
                cw.cwpy.advlog.summonbeast_motion(target, e2)
                eff = True

        return eff

    #-----------------------------------------------------------------------
    #「効果無し」効果
    #-----------------------------------------------------------------------
    def noeffect_motion(self, target, success_res):
        return True


def get_vocation_val(ccard, vocation, enhance_act=False):
    """
    適性値(身体特性+精神特性の合計値)を返す。
    enhance_act : 行動力を加味する場合、True
    """
    physical = vocation[0]
    mental = vocation[1].replace("un", "", 1)
    physical = ccard.data.getint("Property/Ability/Physical", physical, 0)
    mental = ccard.data.getint("Property/Ability/Mental", mental, 0)

    if vocation[1].startswith("un"):
        mental = -mental

    if int(mental) <> mental:
        if mental < 0:
            mental += 0.5
        else:
            mental -= 0.5
        mental = int(mental)

    if enhance_act:
        n = physical + mental + ccard.data.getint("Property/Enhance/Action")
    else:
        n = physical + mental

    return cw.util.numwrap(n, -65536, 65536)

def get_vocation_level(ccard, vocation, enhance_act=False):
    """
    適性値の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
    enhance_act : 行動力を加味する場合、True
    """
    value = get_vocation_val(ccard, vocation, enhance_act)

    if cw.cwpy.setting.vocation120:
        # スキンによる互換機能
        # 1.20相当の適性計算を行う
        if value < 3:
            value = 0
        elif value < 7:
            value = 1
        elif value < 11:
            value = 2
        elif value < 15:
            value = 3
        else:
            value = 4
    else:
        if value < 3:
            value = 0
        elif value < 9:
            value = 1
        elif value < 15:
            value = 2
        elif value < 21:
            value = 3
        else:
            value = 4

    return value

#-------------------------------------------------------------------------------
# 有効な効果モーションのチェック用関数
#-------------------------------------------------------------------------------

def get_effectivetargets(header, targets):
    """
    カード効果が有効なターゲットのリストを返す。
    header: CardHeader
    targets: Characters
    """
    effecttype = header.carddata.gettext("Property/EffectType", "")
    motions = header.carddata.getfind("Motions").getchildren()

    ignore_antimagic = header.type == "BeastCard" or\
                       header.penalty or\
                       not isinstance(header.get_owner(), cw.character.Player)

    sets = set()

    for t in targets:
        if check_noeffect(effecttype, t, ignore_antimagic=ignore_antimagic):
            continue
        # カード効果を上から順に見ていき、対象の存在する効果があれば
        # その効果の対象群を返す
        for motion in motions:
            if t.is_effective(motion):
                sets.add(t)
                break

    return list(sets)

# key: モーション名, value: チェック用メソッド名の辞書
bonus_dict = {"Heal" : ("get_targetingbonus", True),
              }

def main():
    pass

if __name__ == "__main__":
    main()
