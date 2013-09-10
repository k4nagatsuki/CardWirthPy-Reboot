#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

import cw


def save(path):
    """シナリオの実行状況を保存する。
    """
    if not cw.cwpy.is_playingscenario():
        return

    cw.xmlcreater.create_scenariolog(cw.cwpy.sdata, path, True)
    return path

def load(path):
    """シナリオの実行状況を復元する。
    """
    if not cw.cwpy.is_playingscenario():
        return

    musicpath = cw.cwpy.sdata.load_log(path, True)

    # BGM
    cw.cwpy.music.play(musicpath)

    # キャンプ画面を開いている場合はエリア再表示
    func = cw.cwpy.change_area
    if cw.cwpy.areaid == cw.AREA_CAMP:
        cw.cwpy.exec_func(func, cw.AREA_CAMP, False, bginhrt=True)
    else:
        cw.cwpy.exec_func(func, cw.cwpy.areaid, False, bginhrt=True)

def main():
    pass

if __name__ == "__main__":
    main()
