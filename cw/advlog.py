#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import queue
import time
import threading

import cw

from typing import Callable, List, Tuple, Union, Optional

VOID = 0
INITIAL = 1
SYSTEM = 2
MESSAGE = 3
MOTION = 4
MOTION_IN_BATTLE = 5
ELAPSE_TIME = 6
SEPARATOR = 7


class AdventurerLogger(object):

    def __init__(self) -> None:
        self._logger = None
        self._enable = False
        self._last_logtype = VOID

    def start_scenario(self) -> None:
        self.resume_scenario("")

        lines = []
        author = " (%s)" % (cw.cwpy.sdata.author) if cw.cwpy.sdata.author else ""
        s = "== シナリオ [ %s ]%s 開始 ==" % (cw.cwpy.sdata.name, author)
        lines.append(cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))

        lines.append("")
        s = "[ %s ] - %s" % (cw.cwpy.ydata.party.name, cw.cwpy.ydata.name)
        lines.append(s)
        lines.append("")
        for pcard in cw.cwpy.get_pcards():
            lines.append(pcard.name)
            limitlevel = pcard.get_limitlevel()
            if limitlevel != pcard.level:
                lines.append("  Level %s / %s" % (pcard.level, limitlevel))
            else:
                lines.append("  Level %s" % (pcard.level))
            for pocket, pname in ((cw.POCKET_SKILL, "Skill"),
                                  (cw.POCKET_ITEM, "Item"),
                                  (cw.POCKET_BEAST, "Beast"),
                                  (cw.POCKET_PERSONAL, "Personal")):
                if pocket == cw.POCKET_PERSONAL:
                    if not cw.cwpy.setting.show_personal_cards:
                        continue
                    cards = pcard.personal_pocket
                else:
                    cards = pcard.cardpocket[pocket]
                if cards:
                    cnames = []
                    for header in cards:
                        cnames.append(header.name)
                    if cw.cwpy.setting.show_personal_cards:
                        lines.append("  %-8s: %s" % (pname, ", ".join(cnames)))
                    else:
                        lines.append("  %-5s: %s" % (pname, ", ".join(cnames)))

        lines.append("")
        lines.append("=" * cw.LOG_SEPARATOR_LEN_MIDDLE)

        self._put(INITIAL, lines, lambda lines: "\n".join(lines))

    def resume_scenario(self, logfilepath: str) -> None:
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

    def enable(self, enable: bool) -> None:
        if self._enable != enable:
            self._enable = enable
            if self._logger:
                self._logger.queue.put_nowait(enable)
            if cw.cwpy.is_playingscenario():
                if enable:
                    self.resume_scenario("")
                else:
                    self.end_scenario(False, False)

    def end_scenario(self, end: bool, completestamp: bool) -> None:
        if self._logger:
            if end:
                if completestamp:
                    self._put(SYSTEM, "== 済印をつけてシナリオを終了 ==",
                              lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
                else:
                    self._put(SYSTEM, "== 済印をつけずにシナリオを終了 ==",
                              lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
            else:
                self._put_logtype(VOID)
            self._logger.queue.put_nowait(None)
        self._logger = None
        self._last_logtype = VOID

    def gameover(self) -> None:
        self._put(0, "== ゲームオーバー ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def f9(self) -> None:
        self._put(0, "== 緊急避難 ==", lambda s: cw.util.ljustify(s, cw.LOG_SEPARATOR_LEN_LONG, '='))
        self.end_scenario(False, False)

    def _put_logtype(self, logtype: int) -> None:
        if self._enable:
            if self._last_logtype != VOID:
                if self._last_logtype == MESSAGE and logtype != MESSAGE:
                    # メッセージが途切れた所で区切り線を出力する
                    self._logger.queue.put_nowait(("-" * cw.LOG_SEPARATOR_LEN_SHORT, None))
                    if logtype not in (VOID, SEPARATOR):
                        self._logger.queue.put_nowait(("", None))
                elif (self._last_logtype != logtype or logtype == SYSTEM) and logtype not in (VOID, SEPARATOR):
                    # 空行を出力する
                    self._logger.queue.put_nowait(("", None))
            self._last_logtype = logtype
        else:
            self._last_logtype = VOID

    def _put(self, logtype: int, data: Optional[str], func: Optional[Callable] = None, usecard: bool = False) -> None:
        if logtype in (MOTION, MOTION_IN_BATTLE) and not usecard:
            if not (cw.cwpy.event.in_cardeffectmotion or cw.cwpy.event.in_inusecardevent):
                # カード効果以外の効果はあえて出力しない
                return

        if self._logger:
            self._put_logtype(logtype)
            if data is None and func is None:
                self._logger.queue.put_nowait(("", lambda s: None))
            else:
                self._logger.queue.put_nowait((data, func))
            self._last_logtype = logtype

    def show_message(self, mwin: Optional[str]) -> None:
        self._put(MESSAGE, mwin, lambda mwin: cw.sprite.message.get_messagelogtext((mwin,), lastline=False))

    def separator(self) -> None:
        self._put(VOID, "")

    def start_timeelapse(self) -> None:
        if self._enable and self._last_logtype == ELAPSE_TIME:
            self._put(ELAPSE_TIME, "")

    def click_menucard(self, mcard: cw.character.Character) -> None:
        def click_menucard(name: str) -> str:
            if name:
                s = "==< %s >==" % (name)
            else:
                s = "=="
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, '=')

        self._put(SYSTEM, mcard.name, click_menucard)

    def rename_party(self, newname: str, oldname: str) -> None:
        self._put(SYSTEM, newname, lambda name: "パーティ名を[ %s ]に変更" % (name))

    def start_battle(self, battle: cw.battle.BattleEngine) -> None:
        self._put(SYSTEM, None, lambda dummy: cw.util.rjustify("==[ バトル開始 ]==",
                                                               cw.LOG_SEPARATOR_LEN_LONG,
                                                               '='))

    def end_battle(self, battle: cw.battle.BattleEngine) -> None:
        self._put(SYSTEM, None, lambda dummy: cw.util.rjustify("==[ バトル終了 ]==",
                                                               cw.LOG_SEPARATOR_LEN_LONG,
                                                               '='))

    def start_runaway(self) -> None:
        self._put(SYSTEM, "<<<< 逃走 >>>>")

    def runaway(self, success: bool) -> None:
        def runaway(params: Tuple[str, bool]) -> str:
            (pname, success) = params
            if success:
                return "%sは逃走した。" % (pname)
            else:
                return "%sは逃走を試みたが、失敗した。" % (pname)
        self._put(SYSTEM, (cw.cwpy.ydata.party.name, success), runaway)

    def start_round(self, roundval: int) -> None:
        self._put(SYSTEM, roundval, lambda roundval: "<<<< ラウンド %s >>>>" % (roundval))

    def _motion_type(self) -> None:
        return MOTION_IN_BATTLE if cw.cwpy.is_battlestatus() else MOTION

    def use_card(self, ccard: cw.character.Character, header: cw.header.CardHeader,
                 targets: Union[cw.character.Character, List[cw.character.Character]]) -> None:
        def use_card(params: Tuple[str, str, bool, str, str, bool]) -> str:
            (castname, cardname, isbeast, targetname, targettype, is_battlestatus) = params
            if is_battlestatus:
                if isbeast:
                    return "%sの< %s >が発動。" % (castname, cardname)
                else:
                    return "%sは< %s >を使用。" % (castname, cardname)
            elif targetname is not None and targettype not in ("User", "None"):
                s = "==%sが< %s >を< %s >に使用==" % (castname, cardname, targetname)
            else:
                s = "==%sが< %s >を使用==" % (castname, cardname)
            return cw.util.rjustify(s, cw.LOG_SEPARATOR_LEN_MIDDLE, '=')

        castname = ccard.name
        cardname = header.name
        isbeast = header.type == "BeastCard"
        if isinstance(targets, list) and len(targets) == 1:
            targets = targets[0]
        targetname = targets.name if targets and not isinstance(targets, list) else None
        targettype = header.target
        is_battlestatus = cw.cwpy.is_battlestatus()
        if is_battlestatus:
            self._put(self._motion_type(), (castname, cardname, isbeast, targetname, targettype, is_battlestatus),
                      use_card,
                      usecard=True)
        else:
            self._put(SYSTEM, (castname, cardname, isbeast, targetname, targettype, is_battlestatus), use_card,
                      usecard=True)

    def wrap_effectmotion(self, s: str, in_cardeffectmotion: bool) -> str:
        if in_cardeffectmotion:
            s = "  " + s
        return s

    def in_cardeffectmotion(self) -> bool:
        return cw.cwpy.event.in_cardeffectmotion and cw.cwpy.is_battlestatus()

    def avoid(self, target: cw.character.Character) -> None:
        def avoid(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは回避した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), avoid)

    def noeffect(self, target: cw.character.Character) -> None:
        def noeffect(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは抵抗した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), noeffect)

    def effect_failed(self, target: cw.character.Character, ismenucard: bool = False) -> None:
        def effect_failed(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sには効果がなかった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        if ismenucard:
            self._put(SYSTEM, (target.name, self.in_cardeffectmotion()), effect_failed)
        else:
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), effect_failed)

    def _get_lifestatus(self, life: int, maxlife: int) -> int:
        if life <= 0:
            return 0
        elif cw.character.Character.calc_heavyinjured(life, maxlife):
            return 1
        elif cw.character.Character.calc_injured(life, maxlife):
            return 2
        else:
            return 3

    def heal_motion(self, target: cw.character.Character, value: int, newlife: int, oldlife: int) -> None:
        if newlife == oldlife:
            return

        def heal_motion(params: Tuple[str, int, int, int, int, bool]) -> str:
            (name, value, newlife, oldlife, maxlife, in_cardeffectmotion) = params
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if value < 20:
                vs = "小回復"
            elif value < 40:
                vs = "中回復"
            else:
                vs = "大回復"
            if newstatus == oldstatus:
                s = "%sは%s。" % (name, vs)
            else:
                if newstatus == 0:
                    s = "%sは%sし、意識不明状態になった。" % (name, vs)
                elif newstatus == 1:
                    s = "%sは%sし、重傷状態になった。" % (name, vs)
                elif newstatus == 2:
                    s = "%sは%sし、負傷状態になった。" % (name, vs)
                elif newstatus == 3:
                    s = "%sは%sし、健康になった。" % (name, vs)
                else:
                    assert False

            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, newlife, oldlife, target.maxlife,
                                        self.in_cardeffectmotion()), heal_motion)

    def damage_motion(self, target: cw.character.Character, value: int, newlife: int, oldlife: int,
                      dissleep: bool) -> None:
        if newlife == oldlife:
            return

        def damage_motion(params: Tuple[str, int, int, int, int, bool]) -> str:
            (name, value, newlife, oldlife, maxlife, in_cardeffectmotion) = params
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if value < 20:
                vs = "小ダメージ"
            elif value < 40:
                vs = "中ダメージ"
            else:
                vs = "大ダメージ"
            if newstatus == oldstatus:
                s = "%sに%s。" % (name, vs)
            else:
                if newstatus == 0:
                    s = "%sに%s。%sは倒れた。" % (name, vs, name)
                elif newstatus == 1:
                    s = "%sに%s。%sは重傷を負った。" % (name, vs, name)
                elif newstatus == 2:
                    s = "%sに%s。%sは負傷した。" % (name, vs, name)
                elif newstatus == 3:
                    s = "%sに%s。%sは健康になった。" % (name, vs, name)
                else:
                    assert False

            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, newlife, oldlife, target.maxlife,
                                        self.in_cardeffectmotion()), damage_motion)
        if dissleep:
            def dissleep(params: Tuple[str, bool]) -> str:
                (name, in_cardeffectmotion) = params
                s = "%sは目を覚ました。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), dissleep)

    def absorb_motion(self, user: cw.character.Character, healvalue: int, newulife: int, oldulife: int,
                      target: cw.character.Character, value: int, newlife: int, oldlife: int, dissleep: bool) -> None:
        self.damage_motion(target, value, newlife, oldlife, dissleep)
        if user:
            self.heal_motion(user, healvalue, newulife, oldulife)

    def paralyze_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return

        def paralyze_motion(params: Tuple[str, int, int, bool]) -> str:
            (name, newvalue, oldvalue, in_cardeffectmotion) = params
            oldp = cw.character.Character.calc_petrified(oldvalue)
            newp = cw.character.Character.calc_petrified(newvalue)
            if oldvalue <= 0 and 0 < newvalue:
                if newp:
                    s = "%sは石化した。" % (name)
                else:
                    s = "%sは麻痺した。" % (name)
            elif newvalue <= 0 and 0 < oldvalue:
                if oldp:
                    s = "%sの石化が解けた。" % (name)
                else:
                    s = "%sの麻痺は回復した。" % (name)
            elif oldvalue < newvalue:
                if oldp and newp:
                    s = "%sの石化が強化された。" % (name)
                elif not oldp and newp:
                    s = "%sは石化した。" % (name)
                else:
                    assert not oldp and not newp
                    s = "%sの麻痺は悪化した。" % (name)
            else:
                assert newvalue < oldvalue
                if oldp and newp:
                    s = "%sの石化は緩和された。" % (name)
                elif oldp and not newp:
                    s = "%sの石化が解けて麻痺状態になった。" % (name)
                else:
                    assert not oldp and not newp
                    s = "%sの麻痺は緩和された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, newvalue, oldvalue, self.in_cardeffectmotion()), paralyze_motion)

    def disparalyze_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        self.paralyze_motion(target, newvalue, oldvalue)

    def poison_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return

        def poison_motion(params: Tuple[str, int, int, bool]) -> str:
            (name, newvalue, oldvalue, in_cardeffectmotion) = params
            if oldvalue <= 0 and 0 < newvalue:
                s = "%sは中毒した。" % (name)
            elif newvalue <= 0 and 0 < oldvalue:
                s = "%sの中毒は回復した。" % (name)
            elif oldvalue < newvalue:
                s = "%sの中毒は悪化した。" % (name)
            else:
                assert newvalue < oldvalue
                s = "%sの中毒は緩和された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, newvalue, oldvalue, self.in_cardeffectmotion()), poison_motion)

    def dispoison_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        self.poison_motion(target, newvalue, oldvalue)

    def getskillpower_motion(self, target: cw.character.Character, value: int) -> None:
        if value <= 0:
            return

        def getskillpower_motion(params: Tuple[str, int, bool]) -> str:
            (name, value, in_cardeffectmotion) = params
            if 9 <= value:
                s = "%sの精神力は完全に回復した。" % (name)
            else:
                s = "%sの精神力は回復した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, self.in_cardeffectmotion()), getskillpower_motion)

    def loseskillpower_motion(self, target: cw.character.Character, value: int) -> None:
        if value <= 0:
            return

        def loseskillpower_motion(params: Tuple[str, int, bool]) -> str:
            (name, value, in_cardeffectmotion) = params
            if 9 <= value:
                s = "%sは精神力を完全に喪失した。" % (name)
            else:
                s = "%sは精神力を喪失した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, value, self.in_cardeffectmotion()), loseskillpower_motion)

    def mentality_motion(self, target: cw.character.Character, mentality: str, duration: int, oldmentality: str,
                         oldduration: int) -> None:
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

        def mentality_motion(params: Tuple[str, str, int, str, int, bool]) -> str:
            (name, mentality, duration, oldmentality, oldduration, in_cardeffectmotion) = params
            if mentality == "Normal":
                if oldmentality == "Sleep":
                    s = "%sは目を覚ました。" % (name)
                else:
                    s = "%sの精神は正常化した。" % (name)
            else:
                if mentality == "Panic":
                    s = "%sは恐慌状態になった。" % (name)
                elif mentality == "Brave":
                    s = "%sは勇敢になった。" % (name)
                elif mentality == "Overheat":
                    s = "%sは激昂した。" % (name)
                elif mentality == "Confuse":
                    s = "%sは混乱した。" % (name)
                elif mentality == "Sleep":
                    if oldmentality == "Sleep":
                        s = "%sは眠っている。" % (name)
                    else:
                        s = "%sは眠った。" % (name)
                else:
                    assert False
            return self.wrap_effectmotion(s, in_cardeffectmotion)

        self._put(self._motion_type(), (target.name, mentality, duration, oldmentality, oldduration,
                                        self.in_cardeffectmotion()), mentality_motion)

    def bind_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def bind_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは呪縛された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), bind_motion)

    def disbind_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def disbind_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの呪縛は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), disbind_motion)

    def silence_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def silence_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは沈黙した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), silence_motion)

    def dissilence_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def dissilence_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの沈黙は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), dissilence_motion)

    def faceup_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def faceup_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは暴露された。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), faceup_motion)

    def facedown_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def facedown_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの暴露は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), facedown_motion)

    def antimagic_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def antimagic_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sは魔法無効化状態になった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), antimagic_motion)

    def disantimagic_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        def disantimagic_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの魔法無効化状態は解けた。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), disantimagic_motion)

    def _enhanceaction_motion(self, params: Tuple[str, str, int, bool]) -> str:
        (enhname, name, newvalue, in_cardeffectmotion) = params
        if 10 <= newvalue:
            s = "%sの%sは最大まで強化された。" % (name, enhname)
        elif 7 <= newvalue:
            s = "%sの%sは大幅に強化された。" % (name, enhname)
        elif 4 <= newvalue:
            s = "%sの%sは強化された。" % (name, enhname)
        elif 1 <= newvalue:
            s = "%sの%sはわずかに強化された。" % (name, enhname)
        elif newvalue <= -10:
            s = "%sの%sは最低まで減少した。" % (name, enhname)
        elif newvalue <= -7:
            s = "%sの%sは大幅に低下した。" % (name, enhname)
        elif newvalue <= -4:
            s = "%sの%sは低下した。" % (name, enhname)
        elif newvalue <= -1:
            s = "%sの%sはわずかに低下した。" % (name, enhname)
        else:
            s = "%sの%sは通常状態に戻った。" % (name, enhname)
        return self.wrap_effectmotion(s, in_cardeffectmotion)

    def enhanceaction_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), ("行動力", target.name, newvalue, self.in_cardeffectmotion()),
                  self._enhanceaction_motion)

    def enhanceavoid_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), ("回避力", target.name, newvalue, self.in_cardeffectmotion()),
                  self._enhanceaction_motion)

    def enhanceresist_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), ("抵抗力", target.name, newvalue, self.in_cardeffectmotion()),
                  self._enhanceaction_motion)

    def enhancedefense_motion(self, target: cw.character.Character, newvalue: int, oldvalue: int) -> None:
        if newvalue == oldvalue:
            return
        self._put(self._motion_type(), ("防御力", target.name, newvalue, self.in_cardeffectmotion()),
                  self._enhanceaction_motion)

    def vanishtarget_motion(self, target: cw.character.Character, runaway: bool) -> None:
        def vanishtarget_motion(params: Tuple[str, bool, bool]) -> str:
            (name, runaway, in_cardeffectmotion) = params
            if runaway:
                s = "%sは姿を消した。" % (name)
            else:
                s = "%sは消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, runaway, self.in_cardeffectmotion()), vanishtarget_motion)

    def vanishcard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        if not is_inactive and is_battlestatus:
            def vanishcard_motion(params: Tuple[str, bool]) -> str:
                (name, in_cardeffectmotion) = params
                s = "%sの手札は破棄された。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), vanishcard_motion)

    def vanishbeast_motion(self, target: cw.character.Character) -> None:
        def vanishbeast_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの召喚獣は消滅した。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), vanishbeast_motion)

    def _deal_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool,
                     resid: int) -> None:
        if not is_inactive and is_battlestatus and resid in cw.cwpy.rsrc.actioncards:
            def deal_motion(params: Tuple[str, str, bool]) -> str:
                (name, cardname, in_cardeffectmotion) = params
                s = "%sに< %s >が配付された。" % (name, cardname)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
            header = cw.cwpy.rsrc.actioncards[resid]
            self._put(self._motion_type(), (target.name, header.name, self.in_cardeffectmotion()), deal_motion)

    def dealattackcard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 1)

    def dealpowerfulattackcard_motion(self, target: cw.character.Character, is_inactive: bool,
                                      is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 2)

    def dealcriticalattackcard_motion(self, target: cw.character.Character, is_inactive: bool,
                                      is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 3)

    def dealfeintcard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 4)

    def dealdefensecard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 5)

    def dealdistancecard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, 6)

    def dealconfusecard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        self._deal_motion(target, is_inactive, is_battlestatus, -1)

    def dealskillcard_motion(self, target: cw.character.Character, is_inactive: bool, is_battlestatus: bool) -> None:
        def dealskillcard_motion(params: Tuple[str, bool, bool, bool]) -> str:
            (name, is_inactive, is_battlestatus, in_cardeffectmotion) = params
            if not is_inactive and is_battlestatus:
                s = "%sに特殊技能カードが配付された。" % (name)
                return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, is_inactive, is_battlestatus, self.in_cardeffectmotion()),
                  dealskillcard_motion)

    def cancelaction_motion(self, target: cw.character.Character, is_battlestatus: bool) -> None:
        def cancelaction_motion(params: Tuple[str, bool]) -> str:
            (name, in_cardeffectmotion) = params
            s = "%sの行動は止まった。" % (name)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, self.in_cardeffectmotion()), cancelaction_motion)

    def summonbeast_motion(self, target: cw.character.Character, beastdata: cw.data.CWPyElement) -> None:
        def summonbeast_motion(params: Tuple[str, cw.data.CWPyElement, bool]) -> str:
            (name, beastdata, in_cardeffectmotion) = params
            cardname = beastdata.gettext("Property/Name")
            s = "%sに召喚獣< %s >が付与された。" % (name, cardname)
            return self.wrap_effectmotion(s, in_cardeffectmotion)
        self._put(self._motion_type(), (target.name, beastdata, self.in_cardeffectmotion()), summonbeast_motion)

    def poison_damage(self, ccard: cw.character.Character, value: int, newlife: int, oldlife: int) -> None:
        if newlife == oldlife:
            return

        def poison_damage(params: Tuple[str, int, int, int, int]) -> str:
            (name, value, newlife, oldlife, maxlife) = params
            newstatus = self._get_lifestatus(newlife, maxlife)
            oldstatus = self._get_lifestatus(oldlife, maxlife)
            if newstatus == oldstatus:
                s = "%sは毒のダメージを受けた。" % (name)
            else:
                if newstatus == 0:
                    s = "%sは毒で倒れた。" % (name)
                elif newstatus == 1:
                    s = "%sは毒で重傷を負った。" % (name)
                elif newstatus == 2:
                    s = "%sは毒で負傷した。" % (name)
                elif newstatus == 3:
                    s = "%sは毒で健康になった。" % (name)
                else:
                    assert False

            return s

        self._put(ELAPSE_TIME, (ccard.name, value, newlife, oldlife, ccard.maxlife), poison_damage)

    def recover_poison(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの毒は抜けた。" % (name))

    def recover_paralyze(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの麻痺は回復した。" % (name))

    def recover_bind(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの呪縛は解けた。" % (name))

    def recover_silence(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの沈黙は解けた。" % (name))

    def recover_faceup(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの暴露は解けた。" % (name))

    def recover_antimagic(self, ccard: cw.character.Character) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの魔法無効化状態は切れた。" % (name))

    def recover_mentality(self, ccard: cw.character.Character, mentality: str) -> None:
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの精神は正常化した。" % (name))

    def recover_enhance_act(self, ccard: cw.character.Character):
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの行動力は通常状態に戻った。" % (name))

    def recover_enhance_avo(self, ccard: cw.character.Character):
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの回避力は通常状態に戻った。" % (name))

    def recover_enhance_res(self, ccard: cw.character.Character):
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの抵抗力は通常状態に戻った。" % (name))

    def recover_enhance_def(self, ccard: cw.character.Character):
        self._put(ELAPSE_TIME, ccard.name, lambda name: "%sの防御力は通常状態に戻った。" % (name))

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

    def __init__(self, fpath: str, enable: bool) -> None:
        threading.Thread.__init__(self)
        self.fpath = fpath
        self.queue = queue.Queue()
        self.enable = enable

    def run(self) -> None:
        f = None
        try:
            ret = '\n'
            lastwrite = time.process_time()
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
                                f = open(self.fpath, "a", encoding="utf-8")
                                f.seek(0, os.SEEK_END)
                                if first and 0 < f.tell():
                                    f.write(ret)
                                first = False
                            except Exception:
                                cw.util.print_ex(file=sys.stderr)
                                break
                        f.write(s)
                        f.write(ret)
                        f.flush()
                        lastwrite = time.process_time()
                time.sleep(0.015)

                if f and 10 < time.process_time() - lastwrite:
                    # 10秒以上書き込みがなければ一旦クローズする
                    f.close()
                    f = None
        finally:
            if f:
                f.close()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
