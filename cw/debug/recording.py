#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree
import wx

import cw


def save(path):
    """シナリオの実行状況を保存する。
    """
    if not cw.cwpy.is_playingscenario():
        return

    element = cw.data.make_element("DebugState")

    # シナリオ名(不使用)
    e_scenario = cw.data.make_element("Scenario", cw.cwpy.sdata.name)
    element.append(e_scenario)

    # 変数の状態
    e_flags = cw.data.make_element("FlagValues")
    for name, flag in cw.cwpy.sdata.flags.items():
        e_flag = cw.data.make_element("FlagValue")
        e_flag.set("name", flag.name)
        e_flag.set("value", str(flag.value))
        e_flags.append(e_flag)
    element.append(e_flags)
    e_steps = cw.data.make_element("StepValues")
    for name, step in cw.cwpy.sdata.steps.items():
        e_step = cw.data.make_element("StepValue")
        e_step.set("name", step.name)
        e_step.set("value", str(step.value))
        e_steps.append(e_step)
    element.append(e_steps)

    # 同行NPCの有無
    e_friends = cw.data.make_element("Friends")
    for fcard in cw.cwpy.sdata.friendcards:
        e_friend = cw.data.make_element("Friend")
        e_friend.set("id", str(fcard.id))
        e_friends.append(e_friend)
    element.append(e_friends)

    # 背景とセル
    e_bgimgs = cw.cwpy.background.get_data()
    element.append(e_bgimgs)

    # BGM
    e_bgm = cw.data.make_element("Bgm", cw.cwpy.music.path)
    element.append(e_bgm)

    # ファイル書き込み
    etree = cw.data.xml2etree(element=element)
    etree.write(path)
    return path

def load(path):
    """シナリオの実行状況を復元する。
    """
    if not cw.cwpy.is_playingscenario():
        return

    data = cw.data.xml2etree(path)

    # BGM
    cw.cwpy.music.play(data.gettext("Bgm", ""))

    # 背景とセル
    cw.cwpy.background.load(data.getfind("BgImages"), bginhrt=False)

    # 変数の状態
    for flag in data.getfind("FlagValues"):
        name = flag.get("name")
        value = bool(flag.get("value"))
        if name in cw.cwpy.sdata.flags:
            flag = cw.cwpy.sdata.flags[name]
            if flag.value <> value:
                flag.set(value)
                flag.redraw_cards()
    for step in data.getfind("StepValues"):
        name = step.get("name")
        value = int(step.get("value"))
        if name in cw.cwpy.sdata.steps:
            cw.cwpy.sdata.steps[name].set(value)

    # 同行NPCの有無
    cw.cwpy.sdata.friendcards = []
    for friend in data.getfind("Friends"):
        id = int(friend.get("id"))
        if id in cw.cwpy.sdata.casts:
            fcard = cw.sprite.card.FriendCard(id)
            cw.cwpy.sdata.friendcards.append(fcard)

    # キャンプ画面を開いている場合はエリア再表示
    if cw.cwpy.areaid == cw.AREA_CAMP:
        func = cw.cwpy.change_area
        cw.cwpy.exec_func(func, cw.AREA_CAMP, False)

    cw.cwpy.draw()

def main():
    pass

if __name__ == "__main__":
    main()
