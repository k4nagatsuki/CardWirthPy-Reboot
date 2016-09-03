#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import threading
import Queue

import cw

INITIAL = 0
SYSTEM = 1
MESSAGE = 2
ROUND = 3
MOTION = 4
ELAPSE_TIME = 5


class AdventurerLogger(object):

    def __init__(self):
        self._logger = None
        self._enable = False
        self._last_logtype = 0

    def start_scenario(self):
        self.resume_scenario()

        lines = []
        s = u"== シナリオ [ %s ] 開始 ==" % (cw.cwpy.sdata.name)
        lines.append(cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))

        lines.append(u"")
        s = u"[ %s ] - %s" % (cw.cwpy.ydata.party.name, cw.cwpy.ydata.name)
        lines.append(s)
        lines.append(u"")
        for pcard in cw.cwpy.get_pcards():
            lines.append(pcard.name)
            lines.append(u"  Level %s" % (pcard.level))
            for pocket, pname in ((cw.POCKET_SKILL, "Skill"),
                                  (cw.POCKET_ITEM, "Item"),
                                  (cw.POCKET_BEAST, "Beast")):
                cards = pcard.get_cardpocket()[pocket]
                if cards:
                    cnames = []
                    for header in cards:
                        cnames.append(header.name)
                    lines.append("  %-5s: %s" % (pname, u", ".join(cnames)))

        self._put(INITIAL, lines, lambda lines: u"\n".join(lines))

    def resume_scenario(self):
        self.end_scenario(False, False)
        # ファイル名を生成。
        # 複数のシナリオのログを1つに収めてしまいたい場合も
        # あるはずなので、重複チェックはせず、
        # 同一ファイル名の場合は意図的に上書きする。
        titledic, titledicfn = cw.cwpy.get_titledic(with_datetime=True, for_fname=True)
        logfilepath = cw.util.format_title(cw.cwpy.setting.playlogformat, titledicfn)

        # プレイログ作成開始
        self._enable = cw.cwpy.setting.write_playlog
        self._logger = Logger(logfilepath, self._enable)
        self._logger.start()

    def enable(self, enable):
        if self._enable <> enable:
            self._enable = enable
            if self._logger:
                self._logger.queue.put_nowait(enable)
            if cw.cwpy.is_playingscenario():
                if enable:
                    self.resume_scenario()
                else:
                    self.end_scenario(False, False)

    def end_scenario(self, end, completestamp):
        if self._logger:
            if end:
                if completestamp:
                    self._put(SYSTEM, u"== 済印をつけてシナリオを終了 ==", lambda s: cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))
                else:
                    self._put(SYSTEM, u"== 済印をつけずにシナリオを終了 ==", lambda s: cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))
            self._logger.queue.put_nowait(None)
        self._logger = None

    def gameover(self):
        self._put(0, u"== ゲームオーバー ==", lambda s: cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def f9(self):
        self._put(0, u"== 緊急避難 ==", lambda s: cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def _put_logtype(self, logtype):
        if self._enable:
            if self._last_logtype == MESSAGE and logtype <> MESSAGE:
                # メッセージが途切れた所で区切り線を出力する
                self._logger.queue.put_nowait((u"-" * cw.LOG_SEPARATOR_LEN_SHORT, None))
                self._logger.queue.put_nowait((u"", None))
            elif self._last_logtype <> logtype or logtype == SYSTEM:
                # 空行を出力する
                self._logger.queue.put_nowait((u"", None))
            self._last_logtype = logtype
        else:
            self._last_logtype = INITIAL

    def _put(self, logtype, data, func=None):
        if self._logger:
            self._put_logtype(logtype)
            self._logger.queue.put_nowait((data, func))
            self._last_logtype = logtype

    def show_message(self, mwin):
        self._put(MESSAGE, mwin, lambda mwin: cw.sprite.message.get_messagelogtext((mwin,), lastline=False))

    def click_menucard(self, mcard):
        def func(name):
            if name:
                s = u"==< %s >==" % (name)
            else:
                s = u"=="
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, u'=')

        self._put(SYSTEM, mcard.name, func)

    def start_battle(self, battle):
        self._put(SYSTEM, None, lambda dummy: cw.util.rjustify(u"==[ バトルスタート ]==",
                                                          cw.LOG_SEPARATOR_LEN_LONG,
                                                          u'='))

    def runaway(self, success):
        def func(pname, success):
            if success:
                return u"%sは逃走した。" % (pname)
            else:
                return u"%sは逃走を試みたが、失敗した。" % (pname)
        self._put(MOTION, (cw.cwpy.ydata.party.name, success), func)

    def start_round(self, round):
        self._put(ROUND, round, lambda round: u"<<<< ラウンド %s >>>>" % (round))

    def use_card(self, ccard, header, targets):
        def func((castname, cardname, isbeast, targetname, is_battlestatus)):
            if is_battlestatus:
                if isbeast:
                    return u"%sの< %s >が発動。" % (castname, cardname)
                else:
                    return u"%sは< %s >を使用。" % (castname, cardname)
            elif targetname:
                s = u"==%sが< %s >を< %s >に使用==" % (castname, cardname, targetname)
            else:
                s = u"==%sが< %s >を使用==" % (castname, cardname)
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, u'=')

        castname = ccard.name
        cardname = header.name
        isbeast = header.type == "BeastCard"
        if isinstance(targets, list) and len(targets) == 1:
            targets = targets[0]
        targetname = (targets.name if targets.name else u"無名カード")\
            if targets and not isinstance(targets, list) else None
        is_battlestatus = cw.cwpy.is_battlestatus()
        if is_battlestatus:
            self._put(MOTION, (castname, cardname, isbeast, targetname, is_battlestatus), func)
        else:
            self._put(SYSTEM, (castname, cardname, isbeast, targetname, is_battlestatus), func)

    def wrap_effectmotion(self, s, in_cardeffectmotion):
        if in_cardeffectmotion:
            s = u"  " + s
        return s

    def avoid(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sは回避した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def resist(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sは抵抗した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def noeffect(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sには効果がない。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def effect_failed(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sには効果がなかった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def _get_lifestatus(self, life, maxlife):
        if life <= 0:
            return 0
        elif cw.character.Character.calc_heavyinjured(life, maxlife):
            return 1
        elif cw.character.Character.calc_injured(life, maxlife):
            return 2
        else:
            return 3

    def heal_motion(self, target, value, newlife, oldlife):
        if newlife == oldlife:
            return

        def func((name, value, newlife, oldlife, maxlife, in_cardeffectmotion)):
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if value < 20:
                vs = u"小回復"
            elif value < 40:
                vs = u"中回復"
            else:
                vs = u"大回復"
            if newstatus == oldstatus:
                s = u"%sは%s。" % (name, vs)
            else:
                if newstatus == 0:
                    s = u"%sは%sし、意識不明状態になった。" % (name, vs)
                elif newstatus == 1:
                    s = u"%sは%sし、重傷状態になった。" % (name, vs)
                elif newstatus == 2:
                    s = u"%sは%sし、負傷状態になった。" % (name, vs)
                elif newstatus == 3:
                    s = u"%sは%sし、健康になった。" % (name, vs)
                else:
                    assert False

            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, value, newlife, oldlife, target.maxlife, cw.cwpy.event.in_cardeffectmotion), func)

    def damage_motion(self, target, value, newlife, oldlife, dissleep):
        if newlife == oldlife:
            return

        def func((name, value, newlife, oldlife, maxlife, in_cardeffectmotion)):
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if value < 20:
                vs = u"小ダメージ"
            elif value < 40:
                vs = u"中ダメージ"
            else:
                vs = u"大ダメージ"
            if newstatus == oldstatus:
                s = u"%sに%s。" % (name, vs)
            else:
                if newstatus == 0:
                    s = u"%sに%s。%sは倒れた。" % (name, vs, name)
                elif newstatus == 1:
                    s = u"%sに%s。%sは重傷を負った。" % (name, vs, name)
                elif newstatus == 2:
                    s = u"%sに%s。%sは負傷した。" % (name, vs, name)
                elif newstatus == 3:
                    s = u"%sに%s。%sは健康になった。" % (name, vs, name)
                else:
                    assert False

            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, value, newlife, oldlife, target.maxlife, cw.cwpy.event.in_cardeffectmotion), func)
        if dissleep:
            def func2((name, in_cardeffectmotion)):
                s = u"%sは目を覚ました。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func2)

    def absorb_motion(self, user, healvalue, newulife, oldulife, target, value, newlife, oldlife, dissleep):
        self.damage_motion(target, value, newlife, oldlife, dissleep)
        if user:
            self.heal_motion(user, healvalue, newulife, oldulife)

    def paralyze_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return

        def func((name, newvalue, oldvalue, in_cardeffectmotion)):
            oldp = cw.character.Character.calc_petrified(oldvalue)
            newp = cw.character.Character.calc_petrified(newvalue)
            if oldvalue <= 0 and 0 < newvalue:
                if newp:
                    s = u"%sは石化した。" % (name)
                else:
                    s = u"%sは麻痺した。" % (name)
            elif newvalue <= 0 and 0 < oldvalue:
                if oldp:
                    s = u"%sの石化が解けた。" % (name)
                else:
                    s = u"%sの麻痺は回復した。" % (name)
            elif oldvalue < newvalue:
                if oldp and newp:
                    s = u"%sの石化が強化された。" % (name)
                elif not oldp and newp:
                    s = u"%sは石化した。" % (name)
                else:
                    assert not oldp and not newp
                    s = u"%sの麻痺は悪化した。" % (name)
            else:
                assert newvalue < oldvalue
                if oldp and newp:
                    s = u"%sの石化は緩和された。" % (name)
                elif oldp and not newp:
                    s = u"%sの石化が解けて麻痺状態になった。" % (name)
                else:
                    assert not oldp and not newp
                    s = u"%sの麻痺は緩和された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, newvalue, oldvalue, cw.cwpy.event.in_cardeffectmotion), func)

    def disparalyze_motion(self, target, newvalue, oldvalue):
        self.paralyze_motion(target, newvalue, oldvalue)

    def poison_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return

        def func((name, newvalue, oldvalue, in_cardeffectmotion)):
            if oldvalue <= 0 and 0 < newvalue:
                s = u"%sは中毒した。" % (name)
            elif newvalue <= 0 and 0 < oldvalue:
                s = u"%sの中毒は回復した。" % (name)
            elif oldvalue < newvalue:
                s = u"%sの中毒は悪化した。" % (name)
            else:
                assert newvalue < oldvalue
                s = u"%sの中毒は緩和された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, newvalue, oldvalue, cw.cwpy.event.in_cardeffectmotion), func)

    def dispoison_motion(self, target, newvalue, oldvalue):
        self.poison_motion(target, newvalue, oldvalue)

    def getskillpower_motion(self, target, value):
        if value <= 0:
            return

        def func((name, value, in_cardeffectmotion)):
            if 9 <= value:
                s = u"%sの精神力は完全に回復した。" % (name)
            else:
                s = u"%sの精神力は回復した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, value, cw.cwpy.event.in_cardeffectmotion), func)

    def loseskillpower_motion(self, target, value):
        if value <= 0:
            return

        def func((name, value, in_cardeffectmotion)):
            if 9 <= value:
                s = u"%sは精神力を完全に喪失した。" % (name)
            else:
                s = u"%sは精神力を喪失した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, value, cw.cwpy.event.in_cardeffectmotion), func)

    def mentality_motion(self, target, mentality, duration, oldmentality, oldduration):
        if mentality == "Normal":
            duration = 0
        elif duration == 0:
            mentality = "Normal"
        if oldmentality == "Normal":
            oldduration = 0
        elif oldduration == 0:
            oldmentality = "Normal"
        if oldmentality == mentality and oldmentality == oldduration:
            return

        def func((name, mentality, duration, oldmentality, oldduration, in_cardeffectmotion)):
            if mentality == "Normal":
                s = u"%sの精神は正常化した。" % (name)
            else:
                if mentality == "Panic":
                    s = u"%sは恐慌状態になった。" % (name)
                elif mentality == "Brave":
                    s = u"%sは勇敢になった。" % (name)
                elif mentality == "Overheat":
                    s = u"%sは激昂した。" % (name)
                elif mentality == "Confuse":
                    s = u"%sは混乱した。" % (name)
                elif mentality == "Sleep":
                    if oldmentality == "Sleep":
                        s = u"%sは眠っている。" % (name)
                    else:
                        s = u"%sは眠った。" % (name)
                else:
                    assert False
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(MOTION, (target.name, mentality, duration, oldmentality, oldduration, cw.cwpy.event.in_cardeffectmotion), func)

    def bind_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sを呪縛した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def disbind_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sの呪縛は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def silence_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sを沈黙した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def dissilence_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sの沈黙は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def faceup_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sを暴露された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def facedown_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sを暴露は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def antimagic_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sは魔法無効化状態になった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def disantimagic_motion(self, target, newvalue, oldvalue):
        def func((name, in_cardeffectmotion)):
            s = u"%sは魔法無効化状態は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def _enhanceaction_motion(self, (enhname, name, newvalue, in_cardeffectmotion)):
        if 10 <= newvalue:
            s = u"%sの%sは最高まで強化された。" % (name, enhname)
        elif 7 <= newvalue:
            s = u"%sの%sは大きく強化された。" % (name, enhname)
        elif 4 <= newvalue:
            s = u"%sの%sは強化された。" % (name, enhname)
        elif 1 <= newvalue:
            s = u"%sの%sはわずかに強化された。" % (name, enhname)
        elif newvalue <= -10:
            s = u"%sの%sは最低まで減少した。" % (name, enhname)
        elif newvalue <= -7:
            s = u"%sの%sは大きく低下した。" % (name, enhname)
        elif newvalue <= -4:
            s = u"%sの%sは低下した。" % (name, enhname)
        elif newvalue <= -1:
            s = u"%sの%sはわずかに低下した。" % (name, enhname)
        else:
            s = u"%sの%sは通常状態に戻った。" % (name, enhname)
        return self.wrap_effectmotion(s, in_cardeffectmotion)

    def enhanceaction_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(MOTION, (u"行動力", target.name, newvalue, cw.cwpy.event.in_cardeffectmotion), self._enhanceaction_motion)

    def enhanceavoid_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(MOTION, (u"回避力", target.name, newvalue, cw.cwpy.event.in_cardeffectmotion), self._enhanceaction_motion)

    def enhanceresist_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(MOTION, (u"抵抗力", target.name, newvalue, cw.cwpy.event.in_cardeffectmotion), self._enhanceaction_motion)

    def enhancedefense_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(MOTION, (u"行動力", target.name, newvalue, cw.cwpy.event.in_cardeffectmotion), self._enhanceaction_motion)

    def vanishtarget_motion(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sは消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def vanishcard_motion(self, target, is_inactive, is_battlestatus):
        if is_inactive and is_battlestatus:
            def func((name, in_cardeffectmotion)):
                s = u"%sの手札は破棄された。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def vanishbeast_motion(self, target):
        def func((name, in_cardeffectmotion)):
            s = u"%sの召喚獣は消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def _deal_motion(self, target, is_inactive, is_battlestatus, resid):
        if is_inactive and is_battlestatus and resid in cw.cwpy.rsrc.actioncards:
            def func((name, cardname, in_cardeffectmotion)):
                s = u"%sに[%s]が配付された。" % (name, cardname)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            header = cw.cwpy.rsrc.actioncards[resid]
            self._put(MOTION, (target.name, header.name, cw.cwpy.event.in_cardeffectmotion), func)

    def dealattackcard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 1)

    def dealpowerfulattackcard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 2)

    def dealcriticalattackcard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 3)

    def dealfeintcard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 4)

    def dealdefensecard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 5)

    def dealdistancecard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, 6)

    def dealconfusecard_motion(self, target, is_inactive, is_battlestatus):
        self._deal_motion(target, is_inactive, is_battlestatus, -1)

    def dealskillcard_motion(self, target, is_inactive, is_battlestatus):
        def func((name, in_cardeffectmotion)):
            s = u"%sに特殊技能カードが配付された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def cancelaction_motion(self, target, is_battlestatus):
        def func((name, in_cardeffectmotion)):
            s = u"%sの行動は止まった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, cw.cwpy.event.in_cardeffectmotion), func)

    def summonbeast_motion(self, target, header):
        def func((name, cardname, in_cardeffectmotion)):
            s = u"%sは召喚獣[%s]を得た。" % (name, cardname)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(MOTION, (target.name, header.name, cw.cwpy.event.in_cardeffectmotion), func)

    def poison_damage(self, ccard, value, newlife, oldlife):
        if newlife == oldlife:
            return

        def func((name, value, newlife, oldlife, maxlife)):
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if newstatus == oldstatus:
                s = u"%sは毒のダメージを受けた。" % (name)
            else:
                if newstatus == 0:
                    s = u"%sは毒で倒れた。" % (name)
                elif newstatus == 1:
                    s = u"%sは毒で重傷になった。" % (name)
                elif newstatus == 2:
                    s = u"%sは毒で負傷した。" % (name)
                elif newstatus == 3:
                    s = u"%sは毒で健康になった。" % (name)
                else:
                    assert False

            return s

        self._put(ELAPSE_TIME, (ccard.name, value, newlife, oldlife, ccard.maxlife), func)

    def recover_poison(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの毒は抜けた。" % (name))

    def recover_paralyze(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの麻痺は解けた。" % (name))

    def recover_bind(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの呪縛は解けた。" % (name))

    def recover_silence(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの沈黙は解けた。" % (name))

    def recover_faceup(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの暴露は解けた。" % (name))

    def recover_antimagic(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの魔法無効化状態は切れた。" % (name))

    def recover_mentality(self, ccard, mentality):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの精神は正常化した。" % (name))

    def recover_enhance_act(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの行動力は通常状態に戻った。" % (name))

    def recover_enhance_avo(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの回避力は通常状態に戻った。" % (name))

    def recover_enhance_res(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの抵抗力は通常状態に戻った。" % (name))

    def recover_enhance_def(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの防御力は通常状態に戻った。" % (name))

    # 以下は当面出力しない事にする。
    #  * 各種カード入手・喪失(使用回数が尽きた場合も)
    #  * NPC同行・同行解除
    #  * BGM・効果音の再生


class Logger(threading.Thread):

    def __init__(self, fpath, enable):
        threading.Thread.__init__(self)
        self.fpath = fpath
        self.queue = Queue.Queue()
        self.enable = enable

    def run(self):
        f = None
        try:
            ret = '\n'.encode("utf-8")
            while True:
                if not self.queue.empty():
                    t = self.queue.get_nowait()
                    if t is None:
                        break

                    if isinstance(t, bool):
                        self.enable = t
                        continue

                    if self.enable:
                        data, func = t
                        if func:
                            s = func(data)
                        else:
                            s = data
                        if s is None:
                            continue
                        if not f:
                            dpath = os.path.dirname(self.fpath)
                            if not os.path.isdir(dpath):
                                os.makedirs(dpath)
                            f = open(self.fpath, "a")
                        f.write(s.encode("utf-8"))
                        f.write(ret)
                        f.flush()
                time.sleep(0.015)
        finally:
            if f:
                f.close()


def main():
    pass

if __name__ == "__main__":
    main()
