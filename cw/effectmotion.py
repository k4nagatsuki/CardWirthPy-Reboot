#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame

import cw
from cw.character import Character


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

    def apply(self, target):
        if isinstance(target, Character) and self.check_enabledtarget(target):
            return self.apply_charactercard(target)
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
            cw.cwpy.sounds[u"システム・無効"].play()
            return False

    def apply_charactercard(self, target):
        """
        Characterインスタンスに効果モーションを適用する。
        """
        # 各種判定処理
        if self.successrate <= -5:
            # 完全失敗
            allmissed = True
            noeffect = False
            success_res = False
            success_avo = False
        elif self.successrate >= 5:
            # 完全成功(無効だけは判定)
            allmissed = False
            noeffect = self.check_noeffect(target)
            success_res = False
            success_avo = False
        else:
            # 無効・回避・抵抗判定
            allmissed = False
            noeffect = self.check_noeffect(target)
            success_res = self.check_resist(target)
            success_avo = self.check_avoid(target)

        # 音鳴らす
        if not allmissed:
            if noeffect or (success_res and not self.has_motion("damage")\
                                        and not self.has_motion("absorb")):
                cw.cwpy.sounds[u"システム・無効"].play()
                pygame.time.wait(cw.cwpy.setting.frametime * 12)
                return False
            elif success_avo:
                cw.cwpy.sounds[u"システム・回避"].play()
                pygame.time.wait(cw.cwpy.setting.frametime * 12)
                return False

        cw.cwpy.play_sound(self.soundpath)

        # 効果モーションを発動
        if not allmissed:
            for motion in self.motions:
                motion.apply(target, success_res)

        # アニメーション・画像更新(対象消去されていなかったら)
        if not target.is_vanished():
            # 死亡していたら、ステータスを元に戻す
            if target.is_dead():
                target.set_normalstatus()

            self.animate(target, True)

        if allmissed:
            return False
        else:
            return True

    def check_noeffect(self, target):
        noeffect_wpn = target.noeffect.get("weapon")
        noeffect_mgc = target.noeffect.get("magic")
        antimagic = target.is_antimagic()

        # 物理属性
        if self.effecttype == "Physic":
            if noeffect_wpn:
                return True

        # 魔法属性
        elif self.effecttype == "Magic":
            if noeffect_mgc or antimagic:
                return True

        # 魔法的物理属性
        elif self.effecttype == 'MagicalPhysic':
            if noeffect_wpn and noeffect_mgc or antimagic:
                return True

        # 物理的魔法属性
        elif self.effecttype == 'PhysicalMagic':
            if noeffect_wpn or noeffect_mgc or antimagic:
                return True

        return False

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
        # FriendCardはアニメーションさせない
        if isinstance(target, cw.character.Friend):
            if update_image:
                target.update_image()
                cw.cwpy.draw()

            if self.soundpath:
                pygame.time.wait(cw.cwpy.setting.frametime * 12)

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
                pygame.time.wait(cw.cwpy.setting.frametime * 12)

    def check_enabledtarget(self, target):
        """
        対象消去されているかもしくは
        意識不明で回復モーションが入ってない場合は
        有効なターゲットではない。
        """
        if isinstance(target, Character):
            flag  = bool(not target.is_vanished())
            flag &= bool(not target.is_unconscious() or self.has_motion("Heal"))
            return flag
        else:
            return True

    def has_motion(self, motiontype):
        """
        motiontypeで指定したEffectMotionインスタンスを所持しているかどうか。
        """
        motiontype = motiontype.lower()

        for motion in self.motions:
            if motion.type.lower() == motiontype:
                return True

        return False

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
        enhance_def = target.get_enhance_def()
        return (value * (10 - enhance_def)) / 10

    def is_noeffect(self, target):
        """
        属性の相性が無効ならTrueを返す。
        """
        if self.element == "Health" and target.feature.get("undead"):
            return True
        elif self.element == "Mind" and target.feature.get("automaton"):
            return True
        elif self.element == "Miracle":
            if target.feature.get("unholy"):
                return False
            else:
                return True

        elif self.element == "Magic":
            if target.feature.get("constructure"):
                return False
            else:
                return True

        elif self.element == "Fire" and target.resist.get("fire"):
            return True
        elif self.element == "Ice" and target.resist.get("ice"):
            return True
        else:
            return False

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
            return

        # 意識不明だったら回復以外の処理中止
        if target.is_unconscious() and not self.type == "Heal":
            return

        methodname = self.type.lower() + "_motion"
        method = getattr(self, methodname, None)

        if method:
            method(target, success_res)

    #-----------------------------------------------------------------------
    #「生命力」関連効果
    #-----------------------------------------------------------------------
    def heal_motion(self, target, success_res):
        """
        回復。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)
        target.set_life(value)

    def damage_motion(self, target, success_res):
        """
        ダメージ。抵抗成功で半減。
        """
        value = self.calc_effectvalue(target)

        # 抵抗に成功したらダメージ値半減
        if success_res:
            value = value / 2

        # 防御修正
        self.calc_defensedvalue(value, target)
        target.set_life(-value)

        # 睡眠解除
        if target.is_sleep():
            target.set_mentality("Normal", 0)

    def absorb_motion(self, target, success_res):
        """
        吸収。
        """
        value = self.calc_effectvalue(target)

        # 抵抗に成功したらダメージ値半減
        if success_res:
            value = value / 2

        # 防御修正
        self.calc_defensedvalue(value, target)
        target.set_life(-value)

        # 与えたダメージ分、使用者回復
        if self.user:
            self.user.set_life(value)

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

    def disparalyze_motion(self, target, success_res):
        """
        麻痺解除。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_paralyze(-value)

    def poison_motion(self, target, success_res):
        """
        中毒状態。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_poison(value)
        return True

    def dispoison_motion(self, target, success_res):
        """
        中毒解除。抵抗成功で無効化。
        """
        value = self.calc_effectvalue(target)

        if self.damagetype == "Max":
            value = 40

        target.set_poison(-value)

    #-----------------------------------------------------------------------
    #「技能」関連効果
    #-----------------------------------------------------------------------
    def getskillpower_motion(self, target, success_res):
        """
        精神力回復。抵抗成功で無効化。
        """
        target.set_skillpower(True)

    def loseskillpower_motion(self, target, success_res):
        """
        精神力不能。抵抗成功で無効化。
        """
        target.set_skillpower(False)

    #-----------------------------------------------------------------------
    #「精神」関連効果
    #-----------------------------------------------------------------------
    def mentality(self, target, success_res):
        """
        精神状態変更(睡眠・混乱・激昂・勇敢・恐慌・正常)。
        """
        duration = self.calc_durationvalue()
        target.set_mentality(self.type.title(), duration)

    def sleep_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    def confuse_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    def overheat_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    def brave_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    def panic_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    def normal_motion(self, *args, **kwargs):
        self.mentality(*args, **kwargs)

    #-----------------------------------------------------------------------
    #「魔法」関連効果
    #-----------------------------------------------------------------------
    def bind_motion(self, target, success_res):
        """
        束縛状態。
        """
        duration = self.calc_durationvalue()
        target.set_bind(duration)

    def disbind_motion(self, target, success_res):
        """
        束縛解除。
        """
        target.set_bind(0)

    def silence_motion(self, target, success_res):
        """
        沈黙状態。
        """
        duration = self.calc_durationvalue()
        target.set_silence(duration)

    def dissilence_motion(self, target, success_res):
        """
        沈黙解除。
        """
        target.set_silence(0)

    def faceup_motion(self, target, success_res):
        """
        暴露状態。
        """
        duration = self.calc_durationvalue()
        target.set_faceup(duration)

    def facedown_motion(self, target, success_res):
        """
        暴露解除。
        """
        target.set_faceup(0)

    def antimagic_motion(self, target, success_res):
        """
        魔法無効化状態。
        """
        duration = self.calc_durationvalue()
        target.set_antimagic(duration)

    def disantimagic_motion(self, target, success_res):
        """
        魔法無効化解除。
        """
        target.set_antimagic(0)

    #-----------------------------------------------------------------------
    #「能力」関連効果
    #-----------------------------------------------------------------------
    def enhanceaction_motion(self, target, success_res):
        """
        行動力変化。
        """
        duration = self.calc_durationvalue()
        target.set_enhance_act(self.value, duration)

    def enhanceavoid_motion(self, target, success_res):
        """
        回避力変化。
        """
        duration = self.calc_durationvalue()
        target.set_enhance_avo(self.value, duration)

    def enhanceresist_motion(self, target, success_res):
        """
        抵抗力変化。
        """
        duration = self.calc_durationvalue()
        target.set_enhance_res(self.value, duration)

    def enhancedefense_motion(self, target, success_res):
        """
        防御力変化。
        """
        duration = self.calc_durationvalue()
        target.set_enhance_def(self.value, duration)

    #-----------------------------------------------------------------------
    #「消滅」関連効果
    #-----------------------------------------------------------------------
    def vanishtarget_motion(self, target, success_res):
        """
        対象消去。
        """
        target.set_vanish()

    def vanishcard_motion(self, target, success_res):
        """
        カード消去。
        """
        if cw.cwpy.battle:
            target.deck.throwaway(target)

    def vanishbeast_motion(self, target, success_res):
        """
        召喚獣消去。
        """
        target.set_beast(vanish=True)

    #-----------------------------------------------------------------------
    #「カード」関連効果
    #-----------------------------------------------------------------------
    def dealattackcard_motion(self, target, success_res):
        """
        通常攻撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(1)

    def dealpowerfulattackcard_motion(self, target, success_res):
        """
        渾身の一撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(2)

    def dealcriticalattackcard_motion(self, target, success_res):
        """
        会心の一撃配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(3)

    def dealfeintcard_motion(self, target, success_res):
        """
        フェイント配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(4)

    def dealdefensecard_motion(self, target, success_res):
        """
        防御配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(5)

    def dealdistancecard_motion(self, target, success_res):
        """
        見切り配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(6)

    def dealconfusecard_motion(self, target, success_res):
        """
        混乱配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard(-1)

    def dealskillcard_motion(self, target, success_res):
        """
        特殊技能配布。
        """
        if cw.cwpy.battle:
            target.deck.set_nextcard()

    #-----------------------------------------------------------------------
    #「召喚」関連効果
    #-----------------------------------------------------------------------
    def summonbeast_motion(self, target, success_res):
        """
        召喚獣召喚。
        """
        for e in self.beasts:
            target.set_beast(e)

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

    for motion in motions:
        s = motion.get("type", "").lower()

        if s in checkingmethod_dict:
            method, flag = checkingmethod_dict[s]
            sets.update([t for t in targets if getattr(t, method)() == flag])
        else:
            return targets

    return list(sets)

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
