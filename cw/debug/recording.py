#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cw

from typing import Optional


def save(path: str) -> str:
    """シナリオの実行状況を保存する。
    """
    if not cw.cwpy.is_playingscenario():
        return ""
    assert isinstance(cw.cwpy.sdata, cw.data.ScenarioData)

    cw.xmlcreater.create_scenariolog(cw.cwpy.sdata, path, True, cw.cwpy.advlog.logfilepath)
    return path


def load(path: str) -> None:
    """シナリオの実行状況を復元する。
    """
    if not cw.cwpy.is_playingscenario():
        return

    areaid = cw.cwpy.areaid
    if areaid == cw.AREA_CAMP:
        assert cw.cwpy.pre_areaids[-1]
        resid = cw.cwpy.pre_areaids[-1][0]
    else:
        resid = areaid

    data = cw.cwpy.sdata.get_areadata(resid)
    if data is None:
        return

    musicpaths = cw.cwpy.sdata.load_log(path, True)

    # BGM
    for i, (musicpath, subvolume, loopcount, inusecard, fullpath) in enumerate(musicpaths):
        if i < len(cw.cwpy.music):
            cw.cwpy.music[i].play(musicpath, subvolume=subvolume, loopcount=loopcount, inusecard=inusecard,
                                  fullpath=fullpath)

    # キャンプ画面を開いている場合はエリア再表示
    def func(areaid: int, data: Optional[cw.data.CWPyElement] = None) -> None:
        cw.cwpy.change_area(areaid, False, bginhrt=True, data=data)
    if areaid == cw.AREA_CAMP:
        cw.cwpy.pre_areaids[-1] = (cw.cwpy.areaid, data)
        cw.cwpy.exec_func(func, cw.AREA_CAMP)
    else:
        cw.cwpy.exec_func(func, cw.cwpy.areaid, data)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
