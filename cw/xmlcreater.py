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

def create_party(headers, moneyamount=0, pname=None):
    """
    新しくパーティを作る。
    headers: 初期メンバーのファイル名(拡張子無し)のlist。
    """
    if pname is None:
        pname = cw.cwpy.msgs["default_party_name"] % (headers[0].name)

    d = {"name" : cw.binary.util.repl_escapechar(pname),
         "money" : str(moneyamount),
         "backpack" : "",
         "indent": ""}

    members = []
    for header in headers:
        s = os.path.basename(header.fpath)
        s = cw.util.splitext(s)[0]
        s = cw.binary.util.repl_escapechar(s)
        members.append("\n   <Member>%s</Member>" % (s))
    d["members"] = "".join(members)
    dname = cw.util.repl_dischar(pname)
    path = cw.util.join_paths(cw.cwpy.yadodir, "Party", dname)
    path = cw.util.dupcheck_plus(path)
    path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
    _create_xml("Party", cw.util.join_paths(path, "Party.xml"), d)
    return path

def create_partyrecord(party):
    d = {"name" : cw.binary.util.repl_escapechar(party.name),
         "money" : str(party.money),
         "members" : "",
         "backpack": "",
         "indent": ""}

    members = []
    for member in party.members:
        s = os.path.basename(member.fpath)
        s = cw.util.splitext(s)[0]
        s = cw.binary.util.repl_escapechar(s)
        s2 = cw.binary.util.repl_escapechar(member.gettext("Property/Name", ""))
        members.append("\n   <Member name=\"%s\">%s</Member>" % (s2, s))
    d["members"] = "".join(members)

    backpack = []
    for header in party.backpack:
        d2 = {"name" : cw.binary.util.repl_escapechar(header.name),
              "desc" : cw.binary.util.repl_escapechar(header.desc),
              "author" : cw.binary.util.repl_escapechar(header.author),
              "scenario" : cw.binary.util.repl_escapechar(header.scenario),
              "uselimit" : str(header.uselimit),
              "indent" : ""}
        s = cw.binary.xmltemplate.get_xmltext("CardRecord", d2)
        backpack.append("\n   %s" % (s))
    d["backpack"] = "".join(backpack)

    fname = cw.util.repl_dischar(party.name) + ".xml"
    path = cw.util.join_paths(cw.cwpy.yadodir, "PartyRecord", fname)
    path = cw.util.dupcheck_plus(path)
    path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
    _create_xml("PartyRecord", path, d)
    return path

def create_environment(name, dpath, skindirname):
    """
    dpath: "Environment.xml"を作成する宿のディレクトリパス。
    宿のデータを納める"Environment.xml"を作る。
    """
    skintype = u"MedievalFantasy"
    try:
        fpath = cw.util.join_paths(u"Data/Skin", skindirname, u"Skin.xml")
        skintype = cw.header.GetProperty(fpath).properties.get(u"Type", skintype)
    except:
        cw.util.print_ex()

    d = {"name" : cw.binary.util.repl_escapechar(name),
         "skinname" : cw.binary.util.repl_escapechar(skindirname),
         "skintype" : cw.binary.util.repl_escapechar(skintype),
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
    # 描画倍率
    e = cw.data.make_element("ExpandDrawing", str(setting.expanddrawing))
    element.append(e)
    # 拡大モード
    e = cw.data.make_element("ExpandMode", str(setting.expandmode),
                             attrs={"expanded": str(setting.is_expanded),
                                    "smooth":str(setting.smoothexpand)})
    element.append(e)
    # デバッグモードかどうか
    e = cw.data.make_element("DebugMode", str(setting.debug))
    element.append(e)
    # デバッグ時はレベル上昇しない
    e = cw.data.make_element("NoLevelUpInDebugMode", str(setting.no_levelup_in_debugmode))
    element.append(e)
    # スキン
    e = cw.data.make_element("Skin", setting.skindirname)
    element.append(e)
    # 音楽を再生する
    e = cw.data.make_element("PlayBgm", str(setting.play_bgm))
    element.append(e)
    # 効果音を再生する
    e = cw.data.make_element("PlaySound", str(setting.play_sound))
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
    # MIDIサウンドフォント
    e = cw.data.make_element("SoundFonts")
    for soundfont, use in setting.soundfonts:
        e_soundfont = cw.data.make_element("SoundFont", soundfont, {"enabled": str(use)})
        e.append(e_soundfont)
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
    # メッセージログカーテン色
    d = {"red": str(setting.blcurtaincolour[0]),
         "green": str(setting.blcurtaincolour[1]),
         "blue": str(setting.blcurtaincolour[2]),
         "alpha": str(setting.blcurtaincolour[3])
         }
    e = cw.data.make_element("MessageLogCurtainColor", "", d)
    element.append(e)
    # カーテン色
    d = {"red": str(setting.curtaincolour[0]),
         "green": str(setting.curtaincolour[1]),
         "blue": str(setting.curtaincolour[2]),
         "alpha": str(setting.curtaincolour[3])
         }
    e = cw.data.make_element("CurtainColor", "", d)
    element.append(e)
    # カードの表示スピード(数字が小さいほど速い)(1～100)
    e = cw.data.make_element("CardDealingSpeed", str(setting.dealspeed))
    element.append(e)
    # トランジション効果の種類
    e = cw.data.make_element("Transition", setting.transition,
                                {"speed": str(setting.transitionspeed)})
    element.append(e)
    # 背景のスムーススケーリング
    e = cw.data.make_element("SmoothScaling", str(setting.smoothscale_bg))
    element.append(e)
    # 保存せずに終了しようとしたら警告
    e = cw.data.make_element("CautionBeforeSaving", str(setting.caution_beforesaving))
    element.append(e)
    # 拠点ごとにスキンを記憶
    e = cw.data.make_element("StoreSkinOnEachBase", str(setting.store_skinoneachbase))
    element.append(e)
    # レベル調節で手放したカードを自動的に戻す
    e = cw.data.make_element("RevertCardPocket", str(setting.revert_cardpocket))
    element.append(e)
    # キャンプ等に高速で切り替える
    e = cw.data.make_element("QuickDeal", str(setting.quickdeal))
    element.append(e)
    # 全てのシステムカードを高速表示する
    e = cw.data.make_element("AllQuickDeal", str(setting.all_quickdeal))
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

    # スキンによってシナリオの選択開始位置を変更する
    e = cw.data.make_element("SelectScenarioFromType", str(setting.selectscenariofromtype))
    element.append(e)
    # 適正レベル以外のシナリオを表示する
    e = cw.data.make_element("ShowUnfitnessScenario", str(setting.show_unfitnessscenario))
    element.append(e)
    # 隠蔽シナリオを表示する
    e = cw.data.make_element("ShowCompletedScenario", str(setting.show_completedscenario))
    element.append(e)
    # 終了済シナリオを表示する
    e = cw.data.make_element("ShowInvisibleScenario", str(setting.show_invisiblescenario))
    element.append(e)
    # マウスホイールを上回転させた時の挙動
    e = cw.data.make_element("WheelUpOperation", setting.wheelup_operation)
    element.append(e)
    # 戦闘行動を全員分表示する
    e = cw.data.make_element("ShowAllSelectedCards", str(setting.show_allselectedcards))
    element.append(e)
    # カード使用時に確認ダイアログを表示
    e = cw.data.make_element("ConfirmBeforeUsingCard", str(setting.confirm_beforeusingcard))
    element.append(e)
    # セーブ前に確認ダイアログを表示
    e = cw.data.make_element("ConfirmBeforeSaving", str(setting.confirm_beforesaving))
    element.append(e)
    # セーブ完了時に確認ダイアログを表示
    e = cw.data.make_element("ShowSavedMessage", str(setting.show_savedmessage))
    element.append(e)
    # 荷物袋のカードを一時的に取り出して使えるようにする
    e = cw.data.make_element("ShowBackpackCard", str(setting.show_backpackcard))
    element.append(e)
    # 各種ステータスの残り時間を表示する
    e = cw.data.make_element("ShowStatusTime", str(setting.show_statustime))
    element.append(e)
    # カードを選択できない時はダイアログを開かない
    e = cw.data.make_element("OpenHandViewAlways", str(setting.openhandviewalways))
    element.append(e)
    # 不可能な行動を選択した時に警告を表示
    e = cw.data.make_element("NoticeImpossibleAction", str(setting.noticeimpossibleaction))
    element.append(e)

    # パーティ結成時の持出金額
    e = cw.data.make_element("InitialMoneyAmount", str(setting.initmoneyamount))
    element.append(e)

    # 解散時、自動的にパーティ情報を記録する
    e = cw.data.make_element("AutoSavePartyRecord", str(setting.autosave_partyrecord))
    element.append(e)
    # 自動記録時、同名のパーティ記録へ上書きする
    e = cw.data.make_element("OverwritePartyRecord", str(setting.overwrite_partyrecord))
    element.append(e)

    # シナリオフォルダ(スキンタイプ別)
    e = cw.data.make_element("ScenarioFolderOfSkinType")
    for type, folder in setting.folderoftype:
        e_folder = cw.data.make_element("Folder", folder, {"skintype": type})
        e.append(e_folder)
    element.append(e)

    # フルスクリーン時の背景タイプ(0:無し,1:ファイル指定,2:スキン)
    e = cw.data.make_element("FullScreenBackgroundType", str(setting.fullscreenbackgroundtype))
    element.append(e)
    e = cw.data.make_element("FullScreenBackgroundFile", setting.fullscreenbackgroundfile)
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

    # シナリオ絞込・整列条件
    e = cw.data.make_element("ScenarioNarrowType", str(setting.scenario_narrowtype))
    element.append(e)
    e = cw.data.make_element("ScenarioSortType", str(setting.scenario_sorttype))
    element.append(e)

    # スクリーンショット情報
    e = cw.data.make_element("ScreenShotInformationFormat", setting.ssinfoformat)
    element.append(e)
    # スクリーンショット情報の色
    d = {"red": str(setting.ssinfofontcolor[0]),
         "green": str(setting.ssinfofontcolor[1]),
         "blue": str(setting.ssinfofontcolor[2])
         }
    e = cw.data.make_element("ScreenShotInformationFontColor", "", d)
    element.append(e)
    d = {"red": str(setting.ssinfobackcolor[0]),
         "green": str(setting.ssinfobackcolor[1]),
         "blue": str(setting.ssinfobackcolor[2])
         }
    e = cw.data.make_element("ScreenShotInformationBackgroundColor", "", d)
    element.append(e)

    # タイトルバーの表示内容
    e = cw.data.make_element("TitleFormat", setting.titleformat)
    element.append(e)

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
        ce = etree.make_element("Coupon", s, {"value": "0"})
        etree.append("Property/Coupons", ce)

    # 画像コピー
    name = etree.gettext("Property/Name", "noname")
    fname = cw.util.repl_dischar(name)
    dstdir = cw.util.join_paths(cw.cwpy.yadodir, "Material/Album")
    cw.cwpy.copy_materials(element, dstdir, from_scenario=False)
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
    d = data.get_d()
    # 画像パス
    path = d["imgpath"]
    advname = cw.util.repl_dischar(d["name"])
    d["imgpath"] = write_castimagepath(advname, path)

    for key, value in d.items():
        d[key] = cw.binary.util.repl_escapechar(value)

    # クーポン
    def get_coupon(name, value):
        d = {"name": cw.binary.util.repl_escapechar(name), "value": value, "indent": "   "}
        s = cw.binary.xmltemplate.get_xmltext("Coupon", d)
        return s
    coupons = [get_coupon(name, value) for name, value in data.coupons]
    d["coupons"] = "\n" + "\n".join(coupons)

    # XML作成
    path = cw.util.join_paths(cw.cwpy.tempdir, "Adventurer", advname + ".xml")
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
        ext = cw.util.splitext(os.path.basename(path))[1]
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
    elif cw.cwpy.pre_areaids:
        areaid = cw.cwpy.pre_areaids[0]
    else:
        areaid = 0

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

    def make_colorelement(name, color):
        e = cw.data.make_element(name, attrs={"r": str(color[0]),
                                                 "g": str(color[1]),
                                                 "b": str(color[2])})
        if 4 <= len(color):
            e.set("a", str(color[3]))
        else:
            e.set("a", "255")
        return e

    for type, d in cw.cwpy.background.bgs:
        if type == cw.sprite.background.BG_IMAGE:
            fpath, inusecard, mask, size, pos, flag, visible = d
            e_bgimg = cw.data.make_element("BgImage", attrs={"mask": str(mask)})

            if inusecard:
                e = cw.data.make_element("ImagePath", fpath, attrs={"inusecard":str(inusecard)})
            else:
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
