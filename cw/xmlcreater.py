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

    with open(path, "wb") as f:
        f.write(s.encode("utf-8"))

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
    d["members"] = "\n   <Member>%s</Member>" % (s)
    dname = cw.util.repl_dischar(pname)
    path = cw.util.join_paths(cw.cwpy.yadodir, "Party", dname)
    path = cw.util.dupcheck_plus(path)
    path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
    _create_xml("Party", cw.util.join_paths(path, "Party.xml"), d)
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
    # 拡大モード
    e = cw.data.make_element("ExpandMode", str(setting.expandmode),
                             attrs={"expanded": str(setting.is_expanded)})
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
    # バックログウィンドウの色と透明度
    d = {"red": str(setting.blwincolour[0]),
         "green": str(setting.blwincolour[1]),
         "blue": str(setting.blwincolour[2]),
         "alpha": str(setting.blwincolour[3])
         }
    e = cw.data.make_element("MessageLogWindowColor", "", d)
    element.append(e)
    d = {"red": str(setting.blwinframecolour[0]),
         "green": str(setting.blwinframecolour[1]),
         "blue": str(setting.blwinframecolour[2]),
         "alpha": str(setting.blwinframecolour[3])
         }
    e = cw.data.make_element("MessageLogWindowFrameColor", "", d)
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
    # ソート基準
    e = cw.data.make_element("SortKey")
    e.set("standbys", setting.sort_standbys)
    e.set("storehouse", setting.sort_storehouse)
    e.set("backpack", setting.sort_backpack)
    element.append(e)
    # バックログ最大数
    e = cw.data.make_element("MessageLogMax", str(setting.backlogmax))
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

def create_albumpage(path, lost=False, nocoupon=False):
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

    for e in etree.getfind("Property"):
        if e.tag in sets:
            pelement.append(e)

    element.append(pelement)
    etree = cw.data.xml2etree(element=element)

    # クーポン
    if not nocoupon:
        if lost:
            s = cw.cwpy.msgs["lost_coupon_1"]
        else:
            s = cw.cwpy.msgs["lost_coupon_2"]
        element = etree.make_element("Coupon", s, {"value": "0"})
        etree.append("Property/Coupons", element)

    # 画像コピー
    name = etree.gettext("Property/Name", "noname")
    fname = cw.util.repl_dischar(name)
    dstdir = cw.util.join_paths(cw.cwpy.yadodir, "Material/Album")
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

def create_scenariolog(sdata, path, recording):
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

    if not recording:
        e = cw.data.make_element("Debug", str(cw.cwpy.debug))
        e_prop.append(e)
    e = cw.data.make_element("AreaId", str(areaid))
    e_prop.append(e)

    if cw.cwpy.music.path.startswith(cw.cwpy.skindir):
        fpath = cw.cwpy.music.path.replace(cw.cwpy.skindir + "/", "", 1)
    else:
        fpath = cw.cwpy.music.path.replace(sdata.scedir + "/", "", 1)

    e = cw.data.make_element("MusicPath", fpath)
    e_prop.append(e)
    e = cw.data.make_element("Yado", cw.cwpy.ydata.name)
    e_prop.append(e)
    e = cw.data.make_element("Party", cw.cwpy.ydata.party.name)
    e_prop.append(e)
    # bgimages
    e_bgimgs = cw.data.make_element("BgImages")
    element.append(e_bgimgs)

    def make_colorelement(color):
        e = cw.data.make_element("Color", attrs={"r": str(color[0]),
                                                 "g": str(color[1]),
                                                 "b": str(color[2])})
        if 4 <= len(color):
            e.set("a", color[3])
        else:
            e.set("a", "255")
        return e

    for type, d in cw.cwpy.background.bgs:
        if type == cw.sprite.background.BG_IMAGE:
            fpath, mask, size, pos, flag, visible = d
            e_bgimg = cw.data.make_element("BgImage", attrs={"mask": str(mask)})

            if fpath.startswith(cw.cwpy.skindir):
                fpath = fpath.replace(cw.cwpy.skindir + "/", "", 1)
            else:
                fpath = fpath.replace(sdata.scedir + "/", "", 1)

            e = cw.data.make_element("ImagePath", fpath)
            e_bgimg.append(e)

        elif type == cw.sprite.background.BG_TEXT:
            text, face, tsize, color, bold, italic, underline, strike, vertical,\
                btype, bcolor, bwidth, size, pos, flag, visible = d
            e_bgimg = cw.data.make_element("TextCell")

            e = cw.data.make_element("Text", text)
            e_bgimg.append(e)
            e = cw.data.make_element("Font", face, attrs={"size": str(tsize),
                                                          "bold": str(bold),
                                                          "italic": str(italic),
                                                          "underline": str(underline),
                                                          "strike": str(strike)})
            e_bgimg.append(e)
            e = cw.data.make_element("Vertical", str(vertical))
            e_bgimg.append(e)
            e = make_colorelement("Color", color)
            e_bgimg.append(e)

            if btype <> "None":
                e = cw.data.make_element("Bordering", attrs={"type": btype,
                                                             "width": str(bwidth)})
                e.append(make_colorelement("Color", bcolor))
                e_bgimg.append(e)

        elif type == cw.sprite.background.BG_COLOR:
            blend, color1, gradient, color2, size, pos, flag, visible = d
            e_bgimg = cw.data.make_element("ColorCell")

            e = cw.data.make_element("BlendMode", blend)
            e_bgimg.append(e)
            e = make_colorelement("Color", color1)
            e_bgimg.append(e)

            if gradient <> "None":
                e = cw.data.make_element("Gradient", attrs={"direction": gradient})
                e.append(make_colorelement("EndColor", color2))
                e_bgimg.append(e)

        else:
            assert False

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

    if not recording:
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

    if not recording:
        # DeletedFile
        e_del = cw.data.make_element("DeletedFiles")
        element.append(e_del)

        for fpath in sdata.deletedpaths:
            e = cw.data.make_element("DeletedFile", fpath)
            e_del.append(e)

        # LostAdventurer
        e_lost = cw.data.make_element("LostAdventurers")
        element.append(e_lost)

        for fpath in sdata.lostadventurers:
            e = cw.data.make_element("LostAdventurer", fpath)
            e_lost.append(e)

    # ファイル書き込み
    etree = cw.data.xml2etree(element=element)
    etree.write(path)
    return path

def main():
    pass

if __name__ == "__main__":
    main()
