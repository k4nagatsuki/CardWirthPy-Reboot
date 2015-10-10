#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

    areaid = cw.cwpy.areaid
    musicpaths = cw.cwpy.sdata.load_log(path, True)

    # BGM
    for i, (musicpath, inusecard) in enumerate(musicpaths):
        if i < len(cw.cwpy.music):
            cw.cwpy.music[i].play(musicpath, inusecard)

    # キャンプ画面を開いている場合はエリア再表示
    func = cw.cwpy.change_area
    if areaid == cw.AREA_CAMP:
        cw.cwpy.pre_areaids[-1] = cw.cwpy.areaid
        cw.cwpy.exec_func(func, cw.AREA_CAMP, False, bginhrt=True)
    else:
        cw.cwpy.exec_func(func, cw.cwpy.areaid, False, bginhrt=True)

def main():
    pass

if __name__ == "__main__":
    main()
