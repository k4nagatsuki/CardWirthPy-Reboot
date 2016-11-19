#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import threading
import Queue

import cw

VOID = 0
INITIAL = 1
SYSTEM = 2
MESSAGE = 3
MOTION = 4
MOTION_IN_BATTLE = 5
ELAPSE_TIME = 6
SEPARATOR = 7


class AdventurerLogger(object):

    def __init__(self):
        self._logger = None
        self._enable = False
        self._last_logtype = VOID

    def start_scenario(self):
        self.resume_scenario(u"")

        lines = []
        author = u" (%s)" % (cw.cwpy.sdata.author) if cw.cwpy.sdata.author else u""
        s = u"== シナリオ [ %s ]%s 開始 ==" % (cw.cwpy.sdata.name, author)
        lines.append(cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))

        lines.append(u"")
        s = u"[ %s ] - %s" % (cw.cwpy.ydata.party.name, cw.cwpy.ydata.name)
        lines.append(s)
        lines.append(u"")
        for pcard in cw.cwpy.get_pcards():
            lines.append(pcard.name)
            limitlevel = pcard.get_limitlevel()
            if limitlevel <> pcard.level:
                lines.append(u"  Level %s / %s" % (pcard.level, limitlevel))
            else:
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

        lines.append(u"")
        lines.append(u"=" * cw.LOG_SEPARATOR_LEN_MIDDLE)

        self._put(INITIAL, lines, lambda lines: u"\n".join(lines))

    def resume_scenario(self, logfilepath):
        self.end_scenario(False, False)
        # ファイル名を生成。
        # 複数のシナリオのログを1つに収めてしまいたい場合も
        # あるはずなので、重複チェックはせず、
        # 同一ファイル名の場合は意図的に上書きする。
        if not logfilepath:
            titledic, titledicfn = cw.cwpy.get_titledic(with_datetime=True, for_fname=True)
            logfilepath = cw.util.format_title(cw.cwpy.setting.playlogformat, titledicfn)
        self.logfilepath = logfilepath

        # プレイログ作成開始
        self._enable = cw.cwpy.setting.write_playlog
        self._logger = Logger(self.logfilepath, self._enable)
        self._logger.start()

    def enable(self, enable):
        if self._enable <> enable:
            self._enable = enable
            if self._logger:
                self._logger.queue.put_nowait(enable)
            if cw.cwpy.is_playingscenario():
                if enable:
                    self.resume_scenario(u"")
                else:
                    self.end_scenario(False, False)

    def end_scenario(self, end, completestamp):
        if self._logger:
            if end:
                if completestamp:
                    self._put(SYSTEM, u"== 済印をつけてシナリオを終了 ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))
                else:
                    self._put(SYSTEM, u"== 済印をつけずにシナリオを終了 ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, u'='))
            else:
                self._put_logtype(VOID)
            self._logger.queue.put_nowait(None)
        self._logger = None
        self._last_logtype = VOID

    def gameover(self):
        self._put(0, u"== ゲームオーバー ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def f9(self):
        self._put(0, u"== 緊急避難 ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def _put_logtype(self, logtype):
        if self._enable:
            if self._last_logtype <> VOID:
                if self._last_logtype == MESSAGE and logtype <> MESSAGE:
                    # メッセージが途切れた所で区切り線を出力する
                    self._logger.queue.put_nowait((u"-" * cw.LOG_SEPARATOR_LEN_SHORT, None))
                    if not logtype in (VOID, SEPARATOR):
                        self._logger.queue.put_nowait((u"", None))
                elif (self._last_logtype <> logtype or logtype == SYSTEM) and not logtype in (VOID, SEPARATOR):
                    # 空行を出力する
                    self._logger.queue.put_nowait((u"", None))
            self._last_logtype = logtype
        else:
            self._last_logtype = VOID

    def _put(self, logtype, data, func=None, usecard=False):
        if logtype in (MOTION, MOTION_IN_BATTLE) and not usecard:
            if not (cw.cwpy.event.in_cardeffectmotion or cw.cwpy.event.in_inusecardevent):
                # カード効果以外の効果はあえて出力しない
                return

        if self._logger:
            self._put_logtype(logtype)
            if data is None and func is None:
                self._logger.queue.put_nowait((u"", lambda s: None))
            else:
                self._logger.queue.put_nowait((data, func))
            self._last_logtype = logtype

    def show_message(self, mwin):
        self._put(MESSAGE, mwin, lambda mwin: cw.sprite.message.get_messagelogtext((mwin,), lastline=False))

    def separator(self):
        self._put(VOID, u"")

    def start_timeelapse(self):
        if self._enable and self._last_logtype == ELAPSE_TIME:
            self._put(ELAPSE_TIME, u"")

    def click_menucard(self, mcard):
        def click_menucard(name):
            if name:
                s = u"==< %s >==" % (name)
            else:
                s = u"=="
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, u'=')

        self._put(SYSTEM, mcard.name, click_menucard)

    def rename_party(self, newname, oldname):
        self._put(SYSTEM, newname, lambda name: u"パーティ名を[ %s ]に変更" % (name))

    def start_battle(self, battle):
        self._put(SYSTEM, None, lambda dummy: cw.util.rjustify(u"==[ バトル開始 ]==",
                                                          cw.LOG_SEPARATOR_LEN_LONG,
                                                          u'='))

    def end_battle(self, battle):
        self._put(SYSTEM, None, lambda dummy: cw.util.rjustify(u"==[ バトル終了 ]==",
                                                          cw.LOG_SEPARATOR_LEN_LONG,
                                                          u'='))

    def start_runaway(self):
        self._put(SYSTEM, u"<<<< 逃走 >>>>")

    def runaway(self, success):
        def runaway((pname, success)):
            if success:
                return u"%sは逃走した。" % (pname)
            else:
                return u"%sは逃走を試みたが、失敗した。" % (pname)
        self._put(SYSTEM, (cw.cwpy.ydata.party.name, success), runaway)

    def start_round(self, round):
        self._put(SYSTEM, round, lambda round: u"<<<< ラウンド %s >>>>" % (round))

    def _motion_type(self):
        return MOTION_IN_BATTLE if cw.cwpy.is_battlestatus() else MOTION

    def use_card(self, ccard, header, targets):
        def use_card((castname, cardname, isbeast, targetname, targettype, is_battlestatus)):
            if is_battlestatus:
                if isbeast:
                    return u"%sの< %s >が発動。" % (castname, cardname)
                else:
                    return u"%sは< %s >を使用。" % (castname, cardname)
            elif not targetname is None and not targettype in ("User", "None"):
                s = u"==%sが< %s >を< %s >に使用==" % (castname, cardname, targetname)
            else:
                s = u"==%sが< %s >を使用==" % (castname, cardname)
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, u'=')

        castname = ccard.name
        cardname = header.name
        isbeast = header.type == "BeastCard"
        if isinstance(targets, list) and len(targets) == 1:
            targets = targets[0]
        targetname = targets.name if targets and not isinstance(targets, list) else None
        targettype = header.target
        is_battlestatus = cw.cwpy.is_battlestatus()
        if is_battlestatus:
            self._put(self._motion_type(), (castname, cardname, isbeast, targetname, targettype, is_battlestatus), use_card,
                      usecard=True)
        else:
            self._put(SYSTEM, (castname, cardname, isbeast, targetname, targettype, is_battlestatus), use_card,
                      usecard=True)

    def wrap_effectmotion(self, s, in_cardeffectmotion):
        if in_cardeffectmotion:
            s = u"  " + s
        return s

    def in_cardeffectmotion(self):
        return cw.cwpy.event.in_cardeffectmotion and cw.cwpy.is_battlestatus()

    def avoid(self, target):
        def avoid((name, in_cardeffectmotion)):
            s = u"%sは回避した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), avoid)

    def noeffect(self, target):
        def noeffect((name, in_cardeffectmotion)):
            s = u"%sは抵抗した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), noeffect)

    def effect_failed(self, target, ismenucard=False):
        def effect_failed((name, in_cardeffectmotion)):
            s = u"%sには効果がなかった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        if ismenucard:
            self._put(SYSTEM, (target.name, self.in_cardeffectmotion()), effect_failed)
        else:
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), effect_failed)

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

        def heal_motion((name, value, newlife, oldlife, maxlife, in_cardeffectmotion)):
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

        self._put(self._motion_type(), (target.name, value, newlife, oldlife, target.maxlife, self.in_cardeffectmotion()), heal_motion)

    def damage_motion(self, target, value, newlife, oldlife, dissleep):
        if newlife == oldlife:
            return

        def damage_motion((name, value, newlife, oldlife, maxlife, in_cardeffectmotion)):
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

        self._put(self._motion_type(), (target.name, value, newlife, oldlife, target.maxlife, self.in_cardeffectmotion()), damage_motion)
        if dissleep:
            def dissleep((name, in_cardeffectmotion)):
                s = u"%sは目を覚ました。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), dissleep)

    def absorb_motion(self, user, healvalue, newulife, oldulife, target, value, newlife, oldlife, dissleep):
        self.damage_motion(target, value, newlife, oldlife, dissleep)
        if user:
            self.heal_motion(user, healvalue, newulife, oldulife)

    def paralyze_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return

        def paralyze_motion((name, newvalue, oldvalue, in_cardeffectmotion)):
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

        self._put(self._motion_type(), (target.name, newvalue, oldvalue, self.in_cardeffectmotion()), paralyze_motion)

    def disparalyze_motion(self, target, newvalue, oldvalue):
        self.paralyze_motion(target, newvalue, oldvalue)

    def poison_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return

        def poison_motion((name, newvalue, oldvalue, in_cardeffectmotion)):
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

        self._put(self._motion_type(), (target.name, newvalue, oldvalue, self.in_cardeffectmotion()), poison_motion)

    def dispoison_motion(self, target, newvalue, oldvalue):
        self.poison_motion(target, newvalue, oldvalue)

    def getskillpower_motion(self, target, value):
        if value <= 0:
            return

        def getskillpower_motion((name, value, in_cardeffectmotion)):
            if 9 <= value:
                s = u"%sの精神力は完全に回復した。" % (name)
            else:
                s = u"%sの精神力は回復した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, self.in_cardeffectmotion()), getskillpower_motion)

    def loseskillpower_motion(self, target, value):
        if value <= 0:
            return

        def loseskillpower_motion((name, value, in_cardeffectmotion)):
            if 9 <= value:
                s = u"%sは精神力を完全に喪失した。" % (name)
            else:
                s = u"%sは精神力を喪失した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, self.in_cardeffectmotion()), loseskillpower_motion)

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

        def mentality_motion((name, mentality, duration, oldmentality, oldduration, in_cardeffectmotion)):
            if mentality == "Normal":
                if oldmentality == "Sleep":
                    s = u"%sは目を覚ました。" % (name)
                else:
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

        self._put(self._motion_type(), (target.name, mentality, duration, oldmentality, oldduration, self.in_cardeffectmotion()), mentality_motion)

    def bind_motion(self, target, newvalue, oldvalue):
        def bind_motion((name, in_cardeffectmotion)):
            s = u"%sは呪縛された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), bind_motion)

    def disbind_motion(self, target, newvalue, oldvalue):
        def disbind_motion((name, in_cardeffectmotion)):
            s = u"%sの呪縛は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), disbind_motion)

    def silence_motion(self, target, newvalue, oldvalue):
        def silence_motion((name, in_cardeffectmotion)):
            s = u"%sは沈黙した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), silence_motion)

    def dissilence_motion(self, target, newvalue, oldvalue):
        def dissilence_motion((name, in_cardeffectmotion)):
            s = u"%sの沈黙は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), dissilence_motion)

    def faceup_motion(self, target, newvalue, oldvalue):
        def faceup_motion((name, in_cardeffectmotion)):
            s = u"%sは暴露された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), faceup_motion)

    def facedown_motion(self, target, newvalue, oldvalue):
        def facedown_motion((name, in_cardeffectmotion)):
            s = u"%sの暴露は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), facedown_motion)

    def antimagic_motion(self, target, newvalue, oldvalue):
        def antimagic_motion((name, in_cardeffectmotion)):
            s = u"%sは魔法無効化状態になった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), antimagic_motion)

    def disantimagic_motion(self, target, newvalue, oldvalue):
        def disantimagic_motion((name, in_cardeffectmotion)):
            s = u"%sの魔法無効化状態は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), disantimagic_motion)

    def _enhanceaction_motion(self, (enhname, name, newvalue, in_cardeffectmotion)):
        if 10 <= newvalue:
            s = u"%sの%sは最大まで強化された。" % (name, enhname)
        elif 7 <= newvalue:
            s = u"%sの%sは大幅に強化された。" % (name, enhname)
        elif 4 <= newvalue:
            s = u"%sの%sは強化された。" % (name, enhname)
        elif 1 <= newvalue:
            s = u"%sの%sはわずかに強化された。" % (name, enhname)
        elif newvalue <= -10:
            s = u"%sの%sは最低まで減少した。" % (name, enhname)
        elif newvalue <= -7:
            s = u"%sの%sは大幅に低下した。" % (name, enhname)
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
        self._put(self._motion_type(), (u"行動力", target.name, newvalue, self.in_cardeffectmotion()), self._enhanceaction_motion)

    def enhanceavoid_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), (u"回避力", target.name, newvalue, self.in_cardeffectmotion()), self._enhanceaction_motion)

    def enhanceresist_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), (u"抵抗力", target.name, newvalue, self.in_cardeffectmotion()), self._enhanceaction_motion)

    def enhancedefense_motion(self, target, newvalue, oldvalue):
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), (u"防御力", target.name, newvalue, self.in_cardeffectmotion()), self._enhanceaction_motion)

    def vanishtarget_motion(self, target, runaway):
        def vanishtarget_motion((name, runaway, in_cardeffectmotion)):
            if runaway:
                s = u"%sは姿を消した。" % (name)
            else:
                s = u"%sは消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, runaway, self.in_cardeffectmotion()), vanishtarget_motion)

    def vanishcard_motion(self, target, is_inactive, is_battlestatus):
        if not is_inactive and is_battlestatus:
            def vanishcard_motion((name, in_cardeffectmotion)):
                s = u"%sの手札は破棄された。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), vanishcard_motion)

    def vanishbeast_motion(self, target):
        def vanishbeast_motion((name, in_cardeffectmotion)):
            s = u"%sの召喚獣は消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), vanishbeast_motion)

    def _deal_motion(self, target, is_inactive, is_battlestatus, resid):
        if not is_inactive and is_battlestatus and resid in cw.cwpy.rsrc.actioncards:
            def deal_motion((name, cardname, in_cardeffectmotion)):
                s = u"%sに< %s >が配付された。" % (name, cardname)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            header = cw.cwpy.rsrc.actioncards[resid]
            self._put(self._motion_type(), (target.name, header.name, self.in_cardeffectmotion()), deal_motion)

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
        def dealskillcard_motion((name, is_inactive, is_battlestatus, in_cardeffectmotion)):
            if not is_inactive and is_battlestatus:
                s = u"%sに特殊技能カードが配付された。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, is_inactive, is_battlestatus, self.in_cardeffectmotion()), dealskillcard_motion)

    def cancelaction_motion(self, target, is_battlestatus):
        def cancelaction_motion((name, in_cardeffectmotion)):
            s = u"%sの行動は止まった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), cancelaction_motion)

    def summonbeast_motion(self, target, beastdata):
        def summonbeast_motion((name, beastdata, in_cardeffectmotion)):
            cardname = beastdata.gettext("Property/Name")
            s = u"%sに召喚獣< %s >が付与された。" % (name, cardname)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, beastdata, self.in_cardeffectmotion()), summonbeast_motion)

    def poison_damage(self, ccard, value, newlife, oldlife):
        if newlife == oldlife:
            return

        def poison_damage((name, value, newlife, oldlife, maxlife)):
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if newstatus == oldstatus:
                s = u"%sは毒のダメージを受けた。" % (name)
            else:
                if newstatus == 0:
                    s = u"%sは毒で倒れた。" % (name)
                elif newstatus == 1:
                    s = u"%sは毒で重傷を負った。" % (name)
                elif newstatus == 2:
                    s = u"%sは毒で負傷した。" % (name)
                elif newstatus == 3:
                    s = u"%sは毒で健康になった。" % (name)
                else:
                    assert False

            return s

        self._put(ELAPSE_TIME, (ccard.name, value, newlife, oldlife, ccard.maxlife), poison_damage)

    def recover_poison(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの毒は抜けた。" % (name))

    def recover_paralyze(self, ccard):
        self._put(ELAPSE_TIME, ccard.name, lambda name: u"%sの麻痺は回復した。" % (name))

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

    # 以下は当面出力しない(できない)。
    #  * カード効果(使用時イベント含む)以外の効果
    #  * エリア・バトルのカードの配置
    #  * 各種カード入手・喪失(使用回数が尽きた場合も)
    #  * NPC同行・同行解除
    #  * BGM・効果音の再生
    #  * 隠蔽クーポンによる隠蔽・隠蔽解除
    #  * パーティの隠蔽・表示
    #  * 背景周りなど


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
            lastwrite = time.time()
            first = True
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
                            try:
                                dpath = os.path.dirname(self.fpath)
                                if not os.path.isdir(dpath):
                                    os.makedirs(dpath)
                                f = open(self.fpath, "a")
                                f.seek(0, os.SEEK_END)
                                if first and 0 < f.tell():
                                    f.write(ret)
                                lastwrite = time.time()
                                first = False
                            except:
                                cw.util.print_wx(file=sys.stderr)
                                break
                        f.write(s.encode("utf-8"))
                        f.write(ret)
                        f.flush()
                        lastwrite = time.time()
                time.sleep(0.015)

                if f and 10 < time.time() - lastwrite:
                    # 10秒以上書き込みがなければ一旦クローズする
                    f.close()
                    f = None
        finally:
            if f:
                f.close()


def main():
    pass

if __name__ == "__main__":
    main()
