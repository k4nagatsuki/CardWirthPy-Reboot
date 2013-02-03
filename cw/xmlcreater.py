#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

import cw
import cw.binary.xmltemplate


def _create_xml(name, path, d):
    s = cw.binary.xmltemplate.get_xmltext(name, d)
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + s
    dpath = os.path.dirname(path)

    if dpath and not os.path.isdir(dpath):
        os.makedirs(dpath)

    f = open(path, "wb")
    f.write(s.encode("utf-8"))
    f.close()

def create_party(header):
    """
    新しくパーティを作る。
    header: AdventurerHeader
    """
    pname = cw.cwpy.msgs["default_party_name"] % (header.name)

    d = {"name" : pname,
         "money" : "0",
         "backpack" : "",
         "indent": ""}

    s = os.path.basename(header.fpath)
    s = os.path.splitext(s)[0]
    d['members'] = "\n   <Member>%s</Member>" % (s)
    fname = cw.util.repl_dischar(pname)
    path = cw.util.join_paths(cw.cwpy.yadodir, "Party", fname + ".xml")
    path = cw.util.dupcheck_plus(path)
    path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
    _create_xml("Party", path, d)
    return path

def create_environment(name, dpath):
    """
    dpath: "Environment.xml"を作成する宿のディレクトリパス。
    宿のデータを納める"Environment.xml"を作る。
    """
    d = {"name" : name,
         "skintype" : cw.cwpy.setting.skintype,
         "cashbox" : "4000",
         "selectingparty" : "",
         "nowadventuring" : "False",
         "completestamps" : "",
         "gossips" : "",
         "indent": ""}

    path = cw.util.join_paths(dpath, "Environment.xml")
    _create_xml("Environment", path, d)
    return path

def create_settings(setting):
    """Settings.xmlを新しく作る。
    _create_xmlは不使用。
    setting: Settingインスタンス。
    """
    element = cw.data.make_element("Settings")
    # 最後に選択した宿
    e = cw.data.make_element("LastYado", setting.lastyado)
    element.append(e)
    # デバッグモードかどうか
    e = cw.data.make_element("DebugMode", str(setting.debug))
    element.append(e)
    # スキン
    e = cw.data.make_element("Skin", setting.skindirname)
    element.append(e)
    # 音楽のボリューム(0～1.0)
    n = int(setting.vol_bgm * 100)
    n2 = int(setting.vol_midi * 100)
    e = cw.data.make_element("BgmVolume", str(n), {"midi": str(n2)})
    element.append(e)
    # 効果音のボリューム(0～1.0)
    n = int(setting.vol_sound * 100)
    e = cw.data.make_element("SoundVolume", str(n))
    element.append(e)
    # メッセージスピード(数字が小さいほど速い)(0～100)
    e = cw.data.make_element("MessageSpeed", str(setting.messagespeed))
    element.append(e)
    # メッセージウィンドウの色と透明度
    d = {"red": str(setting.mwincolour[0]),
         "green": str(setting.mwincolour[1]),
         "blue": str(setting.mwincolour[2]),
         "alpha": str(setting.mwincolour[3])
         }
    e = cw.data.make_element("MessageWindowColor", "", d)
    element.append(e)
    d = {"red": str(setting.mwinframecolour[0]),
         "green": str(setting.mwinframecolour[1]),
         "blue": str(setting.mwinframecolour[2]),
         "alpha": str(setting.mwinframecolour[3])
         }
    e = cw.data.make_element("MessageWindowFrameColor", "", d)
    element.append(e)
    # カードの表示スピード(数字が小さいほど速い)(1～100)
    e = cw.data.make_element("CardDealingSpeed", str(setting.dealspeed - 1))
    element.append(e)
    # トランジション効果の種類
    e = cw.data.make_element("Transition", setting.transition,
                                {"speed": str(setting.transitionspeed)})
    element.append(e)
    # 背景のスムーススケーリング
    e = cw.data.make_element("SmoothScaling", str(setting.smoothscale_bg))
    element.append(e)

    # シナリオ履歴
    if not hasattr(setting, "recenthistory"):
        e = cw.data.make_element("RecentHistory", "", {"limit": "5"})
        element.append(e)
    else:
        e_history = cw.data.make_element("RecentHistory", "",
                                    {"limit": str(setting.recenthistory.limit)})
        element.append(e_history)

        for path, md5, temppath in setting.recenthistory.scelist:
            e_sce = cw.data.make_element("Scenario", "", {"md5": str(md5)})
            e = cw.data.make_element("WsnPath", path)
            e_sce.append(e)
            e = cw.data.make_element("TempPath", temppath)
            e_sce.append(e)
            e_history.append(e_sce)

    # ファイル書き込み
    path = "Settings.xml"
    etree = cw.data.xml2etree(element=element)
    etree.write(path)
    return path

def create_albumpage(path, lost=False):
    """
    path: 冒険者XMLファイルのパス。
    lost: Trueなら「旅の中、帰らぬ人となる…」クーポン。
    _create_xmlは不使用。
    """
    etree = cw.data.yadoxml2etree(path)
    # AlbumのElementTree作成
    element = etree.make_element("Album")
    pelement = etree.make_element("Property")

    sets = set(["Name", "ImagePath", "Description", "Level",
                "Ability", "Coupons"])

    for e in etree.getfind("/Property"):
        if e.tag in sets:
            pelement.append(e)

    element.append(pelement)
    etree = cw.data.xml2etree(element=element)

    # クーポン
    if lost:
        s = cw.cwpy.msgs["lost_coupon_1"]
    else:
        s = cw.cwpy.msgs["lost_coupon_2"]

    element = etree.make_element("Coupon", s, {"value": "0"})
    etree.append("/Property/Coupons", element)
    # 画像コピー
    name = etree.gettext("/Property/Name", "noname")
    fname = cw.util.repl_dischar(name)
    dstdir = cw.util.join_paths(cw.cwpy.tempdir, "Material/Album")
    cw.cwpy.copy_materials(etree, dstdir, from_scenario=False)
    # ファイル書き込み
    path = cw.util.join_paths(cw.cwpy.tempdir, "Album", fname + ".xml")
    path = cw.util.dupcheck_plus(path)
    etree.write(path)
    return path

def create_adventurer(data):
    """
    data: AdventurerData。
    冒険者のXMLを新しく作成する。
    _create_xmlは不使用。
    """
    def get_coupon(name, value):
        d = {"name": name, "value": value, "indent": "   "}
        s = cw.binary.xmltemplate.get_xmltext("Coupon", d)
        return s

    d = data.get_d()
    # クーポン
    coupons = [get_coupon(name, value) for name, value in data.coupons]
    d["coupons"] = "\n" + "\n".join(coupons)
    # 画像パス
    path = d["imgpath"]
    name = cw.util.repl_dischar(d["name"])

    d["imgpath"] = write_castimagepath(name, path)

    # XML作成
    path = cw.util.join_paths(cw.cwpy.tempdir, "Adventurer", name + ".xml")
    path = cw.util.dupcheck_plus(path)
    _create_xml("Adventurer", path, d)
    return path

def write_castimagepath(name, path):
    """
    キャストの新しい画像を記憶し、記憶後のパスを返す。
    """
    if os.path.isfile(path):
        dpath = cw.util.join_paths(cw.cwpy.tempdir, "Material/Adventurer", name)
        dpath = cw.util.dupcheck_plus(dpath)
        ext = os.path.splitext(os.path.basename(path))[1]
        dstpath = cw.util.join_paths(dpath, name + ext)

        if not os.path.isdir(dpath):
            os.makedirs(dpath)

        shutil.copy2(path, dstpath)
        return dstpath.replace(cw.cwpy.tempdir + "/", "")
    else:
        return ""


def create_scenariolog(sdata):
    """
    シナリオのプレイデータを記録したXMLファイルを作成する。
    """
    element = cw.data.make_element("ScenarioLog")
    # Property
    e_prop = cw.data.make_element("Property")
    element.append(e_prop)
    e = cw.data.make_element("Name", sdata.name)
    e_prop.append(e)
    e = cw.data.make_element("WsnPath", sdata.fpath)
    e_prop.append(e)

    if cw.cwpy.areaid > 0:
        areaid = cw.cwpy.areaid
    else:
        areaid = cw.cwpy.pre_areaids[0]

    e = cw.data.make_element("Debug", str(cw.cwpy.debug))
    e_prop.append(e)
    e = cw.data.make_element("AreaId", str(areaid))
    e_prop.append(e)

    if cw.cwpy.music.path.startswith(cw.cwpy.skindir):
        path = cw.cwpy.music.path.replace(cw.cwpy.skindir + "/", "", 1)
    else:
        path = cw.cwpy.music.path.replace(sdata.scedir + "/", "", 1)

    e = cw.data.make_element("MusicPath", path)
    e_prop.append(e)
    e = cw.data.make_element("Yado", cw.cwpy.ydata.name)
    e_prop.append(e)
    e = cw.data.make_element("Party", cw.cwpy.ydata.party.name)
    e_prop.append(e)
    # bgimages
    e_bgimgs = cw.data.make_element("BgImages")
    element.append(e_bgimgs)

    for path, mask, size, pos, flag, visible in cw.cwpy.background.bgs:
        e_bgimg  = cw.data.make_element("BgImage", attrs={"mask": str(mask)})

        if path.startswith(cw.cwpy.skindir):
            path = path.replace(cw.cwpy.skindir + "/", "", 1)
        else:
            path = path.replace(sdata.scedir + "/", "", 1)

        e = cw.data.make_element("ImagePath", path)
        e_bgimg.append(e)
        e = cw.data.make_element("Flag", flag)
        e_bgimg.append(e)
        e = cw.data.make_element("Location",
                        attrs={"left": str(pos[0]), "top": str(pos[1])})
        e_bgimg.append(e)
        e = cw.data.make_element("Size",
                        attrs={"width": str(size[0]), "height": str(size[1])})
        e_bgimg.append(e)
        e_bgimgs.append(e_bgimg)

    # flag
    e_flag = cw.data.make_element("Flags")
    element.append(e_flag)

    for name, flag in sdata.flags.iteritems():
        e = cw.data.make_element("Flag", name, {"value": str(flag.value)})
        e_flag.append(e)

    # step
    e_step = cw.data.make_element("Steps")
    element.append(e_step)

    for name, step in sdata.steps.iteritems():
        e = cw.data.make_element("Step", name, {"value": str(step.value)})
        e_step.append(e)

    # gossip
    e_gossip = cw.data.make_element("Gossips")
    element.append(e_gossip)

    for key, value in sdata.gossips.iteritems():
        e = cw.data.make_element("Gossip", key, {"value": str(value)})
        e_gossip.append(e)

    # completestamps
    e_compstamp = cw.data.make_element("CompleteStamps")
    element.append(e_compstamp)

    for key, value in sdata.compstamps.iteritems():
        e = cw.data.make_element("CompleteStamp", key, {"value": str(value)})
        e_compstamp.append(e)

    # InfoCard
    e_info = cw.data.make_element("InfoCards")
    element.append(e_info)

    for header in sdata.infocards:
        e = cw.data.make_element("InfoCard", str(header.id))
        e_info.append(e)

    # FriendCard
    e_cast = cw.data.make_element("CastCards")
    element.append(e_cast)

    for fcard in sdata.friendcards:
        e_cast.append(fcard.data.getroot())

    # DeletedFile
    e_del = cw.data.make_element("DeletedFiles")
    element.append(e_del)

    for path in sdata.deletedpaths:
        e = cw.data.make_element("DeletedFile", path)
        e_del.append(e)

    # LostAdventurer
    e_lost = cw.data.make_element("LostAdventurers")
    element.append(e_lost)

    for path in sdata.lostadventurers:
        e = cw.data.make_element("LostAdventurer", path)
        e_lost.append(e)

    # ファイル書き込み
    path = "Data/Temp/ScenarioLog/ScenarioLog.xml"
    etree = cw.data.xml2etree(element=element)
    etree.write(path)
    return path

def main():
    pass

if __name__ == "__main__":
    main()
