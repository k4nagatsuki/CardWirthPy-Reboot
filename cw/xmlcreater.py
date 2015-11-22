#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

import cw


def _create_xml(name, path, d):
    s = cw.binary.xmltemplate.get_xmltext(name, d)
    s = '<?xml version="1.0" encoding="UTF-8"?>\n' + s
    dpath = os.path.dirname(path)

    if dpath and not os.path.isdir(dpath):
        os.makedirs(dpath)

    with open(path, "wb") as f:
        f.write(s.encode("utf-8"))
        f.flush()
        f.close()

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

def create_environment(name, dpath, skindirname, is_autoloadparty):
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
         "indent": "",
         "is_autoloadparty": str(is_autoloadparty)}

    path = cw.util.join_paths(dpath, "Environment.xml")
    _create_xml("Environment", path, d)
    return path

def create_settings(setting, writeplayingdata=True, fpath="Settings.xml"):
    """Settings.xmlを新しく作る。
    _create_xmlは不使用。
    setting: Settingインスタンス。
    writeplayingdata: デバッグ状態やスキンの選択状態などを保存するか。
    fpath: 保存先のファイルパス。
    """
    element = cw.data.make_element("Settings")
    # 最初から詳細モードで設定を行う
    if setting.show_advancedsettings <> setting.show_advancedsettings_init:
        e = cw.data.make_element("ShowAdvancedSettings", str(setting.show_advancedsettings))
        element.append(e)
    # シナリオエディタ
    if setting.editor <> setting.editor_init:
        e = cw.data.make_element("ScenarioEditor", setting.editor)
        element.append(e)
    if writeplayingdata:
        # 最後に選択した宿
        if setting.lastyado <> setting.lastyado_init:
            e = cw.data.make_element("LastYado", setting.lastyado)
            element.append(e)
        # ウィンドウ位置
        if setting.window_position <> setting.window_position_init:
            e = cw.data.make_element("WindowPosition", attrs={"left":str(setting.window_position[0]),
                                                                "top":str(setting.window_position[1])})
            element.append(e)
    # 拡大モード
    if writeplayingdata:
        if setting.expanddrawing <> setting.expanddrawing_init or\
                setting.expandmode <> setting.expandmode_init or\
                setting.is_expanded <> setting.is_expanded_init or\
                setting.smoothexpand <> setting.smoothexpand_init:
            # 描画倍率
            e = cw.data.make_element("ExpandDrawing", str(setting.expanddrawing))
            element.append(e)
            # 表示倍率
            e = cw.data.make_element("ExpandMode", str(setting.expandmode),
                                     attrs={"expanded": str(setting.is_expanded),
                                            "smooth":str(setting.smoothexpand)})
            element.append(e)
    else:
        if setting.expanddrawing <> setting.expanddrawing_init or\
                setting.expandmode <> setting.expandmode_init or\
                setting.smoothexpand <> setting.smoothexpand_init:
            # 描画倍率
            e = cw.data.make_element("ExpandDrawing", str(setting.expanddrawing))
            element.append(e)
            # 表示倍率
            e = cw.data.make_element("ExpandMode", str(setting.expandmode),
                                     attrs={"smooth":str(setting.smoothexpand)})
            element.append(e)
    if writeplayingdata:
        # デバッグモードかどうか
        if setting.debug_saved <> setting.debug_init:
            e = cw.data.make_element("DebugMode", str(setting.debug_saved))
            element.append(e)
    # デバッグ時はレベル上昇しない
    if setting.no_levelup_in_debugmode <> setting.no_levelup_in_debugmode_init:
        e = cw.data.make_element("NoLevelUpInDebugMode", str(setting.no_levelup_in_debugmode))
        element.append(e)
    if writeplayingdata:
        # スキン
        if setting.skindirname <> setting.skindirname_init:
            e = cw.data.make_element("Skin", setting.skindirname)
            element.append(e)
    # 音楽を再生する
    if setting.play_bgm <> setting.play_bgm_init:
        e = cw.data.make_element("PlayBgm", str(setting.play_bgm))
        element.append(e)
    # 効果音を再生する
    if setting.play_sound <> setting.play_sound_init:
        e = cw.data.make_element("PlaySound", str(setting.play_sound))
        element.append(e)
    # 音声全体のボリューム(0～1.0)
    if setting.vol_master <> setting.vol_master_init:
        n = int(setting.vol_master * 100)
        e = cw.data.make_element("MasterVolume", str(n))
        element.append(e)
    # 音楽のボリューム(0～1.0)
    if setting.vol_bgm <> setting.vol_bgm_init or\
            setting.vol_midi <> setting.vol_midi_init:
        n = int(setting.vol_bgm * 100)
        n2 = int(setting.vol_midi * 100)
        e = cw.data.make_element("BgmVolume", str(n), {"midi": str(n2)})
        element.append(e)
    # 効果音のボリューム(0～1.0)
    if setting.vol_sound <> setting.vol_sound_init:
        n = int(setting.vol_sound * 100)
        e = cw.data.make_element("SoundVolume", str(n))
        element.append(e)
    # MIDIサウンドフォント
    if setting.soundfonts <> setting.soundfonts_init:
        e = cw.data.make_element("SoundFonts")
        for soundfont, use in setting.soundfonts:
            e_soundfont = cw.data.make_element("SoundFont", soundfont, {"enabled": str(use)})
            e.append(e_soundfont)
        element.append(e)
    # メッセージスピード(数字が小さいほど速い)(0～100)
    if setting.messagespeed <> setting.messagespeed_init:
        e = cw.data.make_element("MessageSpeed", str(setting.messagespeed))
        element.append(e)
    # メッセージで装飾フォントを使用する
    if setting.decorationfont <> setting.decorationfont_init:
        e = cw.data.make_element("DecorationFont", str(setting.decorationfont))
        element.append(e)
    # メッセージウィンドウの色と透明度
    if setting.mwincolour <> setting.mwincolour_init:
        d = {"red": str(setting.mwincolour[0]),
             "green": str(setting.mwincolour[1]),
             "blue": str(setting.mwincolour[2]),
             "alpha": str(setting.mwincolour[3])
             }
        e = cw.data.make_element("MessageWindowColor", "", d)
        element.append(e)
    if setting.mwinframecolour <> setting.mwinframecolour_init:
        d = {"red": str(setting.mwinframecolour[0]),
             "green": str(setting.mwinframecolour[1]),
             "blue": str(setting.mwinframecolour[2]),
             "alpha": str(setting.mwinframecolour[3])
             }
        e = cw.data.make_element("MessageWindowFrameColor", "", d)
        element.append(e)
    # バックログウィンドウの色と透明度
    if setting.blwincolour <> setting.blwincolour_init:
        d = {"red": str(setting.blwincolour[0]),
             "green": str(setting.blwincolour[1]),
             "blue": str(setting.blwincolour[2]),
             "alpha": str(setting.blwincolour[3])
             }
        e = cw.data.make_element("MessageLogWindowColor", "", d)
        element.append(e)
    if setting.blwinframecolour <> setting.blwinframecolour_init:
        d = {"red": str(setting.blwinframecolour[0]),
             "green": str(setting.blwinframecolour[1]),
             "blue": str(setting.blwinframecolour[2]),
             "alpha": str(setting.blwinframecolour[3])
             }
        e = cw.data.make_element("MessageLogWindowFrameColor", "", d)
        element.append(e)
    # メッセージログカーテン色
    if setting.blcurtaincolour <> setting.blcurtaincolour_init:
        d = {"red": str(setting.blcurtaincolour[0]),
             "green": str(setting.blcurtaincolour[1]),
             "blue": str(setting.blcurtaincolour[2]),
             "alpha": str(setting.blcurtaincolour[3])
             }
        e = cw.data.make_element("MessageLogCurtainColor", "", d)
        element.append(e)
    # カーテン色
    if setting.curtaincolour <> setting.curtaincolour_init:
        d = {"red": str(setting.curtaincolour[0]),
             "green": str(setting.curtaincolour[1]),
             "blue": str(setting.curtaincolour[2]),
             "alpha": str(setting.curtaincolour[3])
             }
        e = cw.data.make_element("CurtainColor", "", d)
        element.append(e)
    # カードの表示スピード(数字が小さいほど速い)(1～100)
    if setting.dealspeed <> setting.dealspeed_init:
        e = cw.data.make_element("CardDealingSpeed", str(setting.dealspeed))
        element.append(e)
    # 戦闘行動の表示スピード(数字が小さいほど速い)(1～100)
    if setting.dealspeed_battle <> setting.dealspeed_battle_init or setting.use_battlespeed <> setting.use_battlespeed_init:
        e = cw.data.make_element("CardDealingSpeedInBattle", str(setting.dealspeed_battle),
                                 attrs={"enabled":str(setting.use_battlespeed)})
        element.append(e)
    # カードの使用前に空白時間を入れる
    if setting.wait_usecard <> setting.wait_usecard_init:
        e = cw.data.make_element("WaitUseCard", str(setting.wait_usecard))
        element.append(e)
    # トランジション効果の種類
    if setting.transition <> setting.transition_init or\
            setting.transitionspeed <> setting.transitionspeed_init:
        e = cw.data.make_element("Transition", setting.transition,
                                    {"speed": str(setting.transitionspeed)})
        element.append(e)
    # 背景のスムーススケーリング
    attrs = {}
    if setting.smoothscale_bg <> setting.smoothscale_bg_init:
        attrs["bg"] = str(setting.smoothscale_bg)
    if setting.smoothing_card_up <> setting.smoothing_card_up_init:
        attrs["upcard"] = str(setting.smoothing_card_up)
    if setting.smoothing_card_down <> setting.smoothing_card_down_init:
        attrs["downcard"] = str(setting.smoothing_card_down)
    if attrs:
        e = cw.data.make_element("SmoothScaling", u"", attrs=attrs)
        element.append(e)
    # 保存せずに終了しようとしたら警告
    if setting.caution_beforesaving <> setting.caution_beforesaving_init:
        e = cw.data.make_element("CautionBeforeSaving", str(setting.caution_beforesaving))
        element.append(e)
    # 拠点ごとにスキンを記憶
    if setting.store_skinoneachbase <> setting.store_skinoneachbase_init:
        e = cw.data.make_element("StoreSkinOnEachBase", str(setting.store_skinoneachbase))
        element.append(e)
    # レベル調節で手放したカードを自動的に戻す
    if setting.revert_cardpocket <> setting.revert_cardpocket_init:
        e = cw.data.make_element("RevertCardPocket", str(setting.revert_cardpocket))
        element.append(e)
    # キャンプ等に高速で切り替える
    if setting.quickdeal <> setting.quickdeal_init:
        e = cw.data.make_element("QuickDeal", str(setting.quickdeal))
        element.append(e)
    # 全てのシステムカードを高速表示する
    if setting.all_quickdeal <> setting.all_quickdeal_init:
        e = cw.data.make_element("AllQuickDeal", str(setting.all_quickdeal))
        element.append(e)
    if writeplayingdata:
        # ソート基準
        e = cw.data.make_element("SortKey")
        if setting.sort_standbys <> setting.sort_standbys_init:
            e.set("standbys", setting.sort_standbys)
        if setting.sort_cards <> setting.sort_cards_init:
            e.set("cards", setting.sort_cards)
        if setting.sort_cardswithstar <> setting.sort_cardswithstar_init:
            e.set("cardswithstar", str(setting.sort_cardswithstar))
        if e.attrib:
            element.append(e)
        # 宿帳絞込条件
        if setting.standbys_narrowtype <> setting.standbys_narrowtype_init:
            e = cw.data.make_element("StandbysNarrowType", str(setting.standbys_narrowtype))
            element.append(e)
        # カード絞込条件
        if setting.card_narrowtype <> setting.card_narrowtype_init:
            e = cw.data.make_element("CardNarrowType", str(setting.card_narrowtype))
            element.append(e)
        # 情報カード絞込条件
        if setting.infoview_narrowtype <> setting.infoview_narrowtype_init:
            e = cw.data.make_element("InfoViewNarrowType", str(setting.infoview_narrowtype))
            element.append(e)
    # バックログ最大数
    if setting.backlogmax <> setting.backlogmax_init:
        e = cw.data.make_element("MessageLogMax", str(setting.backlogmax))
        element.append(e)

    # スキンによってシナリオの選択開始位置を変更する
    if setting.selectscenariofromtype <> setting.selectscenariofromtype_init:
        e = cw.data.make_element("SelectScenarioFromType", str(setting.selectscenariofromtype))
        element.append(e)
    # 適正レベル以外のシナリオを表示する
    if setting.show_unfitnessscenario <> setting.show_unfitnessscenario_init:
        e = cw.data.make_element("ShowUnfitnessScenario", str(setting.show_unfitnessscenario))
        element.append(e)
    # 隠蔽シナリオを表示する
    if setting.show_completedscenario <> setting.show_completedscenario_init:
        e = cw.data.make_element("ShowCompletedScenario", str(setting.show_completedscenario))
        element.append(e)
    # 終了済シナリオを表示する
    if setting.show_invisiblescenario <> setting.show_invisiblescenario_init:
        e = cw.data.make_element("ShowInvisibleScenario", str(setting.show_invisiblescenario))
        element.append(e)
    # マウスホイールを上回転させた時の挙動
    if setting.wheelup_operation <> setting.wheelup_operation_init:
        e = cw.data.make_element("WheelUpOperation", setting.wheelup_operation)
        element.append(e)
    # 戦闘行動を全員分表示する
    if setting.show_allselectedcards <> setting.show_allselectedcards_init:
        e = cw.data.make_element("ShowAllSelectedCards", str(setting.show_allselectedcards))
        element.append(e)
    # カード使用時に確認ダイアログを表示
    if setting.confirm_beforeusingcard <> setting.confirm_beforeusingcard_init:
        e = cw.data.make_element("ConfirmBeforeUsingCard", str(setting.confirm_beforeusingcard))
        element.append(e)
    # セーブ前に確認ダイアログを表示
    if setting.confirm_beforesaving <> setting.confirm_beforesaving_init:
        e = cw.data.make_element("ConfirmBeforeSaving", str(setting.confirm_beforesaving))
        element.append(e)
    # セーブ完了時に確認ダイアログを表示
    if setting.show_savedmessage <> setting.show_savedmessage_init:
        e = cw.data.make_element("ShowSavedMessage", str(setting.show_savedmessage))
        element.append(e)
    # 荷物袋のカードを一時的に取り出して使えるようにする
    if setting.show_backpackcard <> setting.show_backpackcard_init:
        e = cw.data.make_element("ShowBackpackCard", str(setting.show_backpackcard))
        element.append(e)
    # 荷物袋カードを最後に配置する
    if setting.show_backpackcardatend <> setting.show_backpackcardatend_init:
        e = cw.data.make_element("ShowBackpackCardAtEnd", str(setting.show_backpackcardatend))
        element.append(e)
    # 各種ステータスの残り時間を表示する
    if setting.show_statustime <> setting.show_statustime_init:
        e = cw.data.make_element("ShowStatusTime", str(setting.show_statustime))
        element.append(e)
    # カードを選択できない時はダイアログを開かない
    if setting.openhandviewalways <> setting.openhandviewalways_init:
        e = cw.data.make_element("OpenHandViewAlways", str(setting.openhandviewalways))
        element.append(e)
    # 不可能な行動を選択した時に警告を表示
    if setting.noticeimpossibleaction <> setting.noticeimpossibleaction_init:
        e = cw.data.make_element("NoticeImpossibleAction", str(setting.noticeimpossibleaction))
        element.append(e)

    # パーティ結成時の持出金額
    if setting.initmoneyamount <> setting.initmoneyamount_init:
        e = cw.data.make_element("InitialMoneyAmount", str(setting.initmoneyamount))
        element.append(e)

    # 解散時、自動的にパーティ情報を記録する
    if setting.autosave_partyrecord <> setting.autosave_partyrecord_init:
        e = cw.data.make_element("AutoSavePartyRecord", str(setting.autosave_partyrecord))
        element.append(e)
    # 自動記録時、同名のパーティ記録へ上書きする
    if setting.overwrite_partyrecord <> setting.overwrite_partyrecord_init:
        e = cw.data.make_element("OverwritePartyRecord", str(setting.overwrite_partyrecord))
        element.append(e)

    # シナリオフォルダ(スキンタイプ別)
    if setting.folderoftype <> setting.folderoftype_init:
        e = cw.data.make_element("ScenarioFolderOfSkinType")
        for skintype, folder in setting.folderoftype:
            e_folder = cw.data.make_element("Folder", folder, {"skintype": skintype})
            e.append(e_folder)
        element.append(e)

    # フルスクリーン時の背景タイプ(0:無し,1:ファイル指定,2:スキン)
    if setting.fullscreenbackgroundtype <> setting.fullscreenbackgroundtype_init:
        e = cw.data.make_element("FullScreenBackgroundType", str(setting.fullscreenbackgroundtype))
        element.append(e)
    if setting.fullscreenbackgroundfile <> setting.fullscreenbackgroundfile_init:
        e = cw.data.make_element("FullScreenBackgroundFile", setting.fullscreenbackgroundfile)
        element.append(e)

    # 基本フォント(空白時デフォルト)
    if setting.basefont["gothic"] <> setting.basefont_init["gothic"]:
        e = cw.data.make_element("FontGothic", setting.basefont["gothic"])
        element.append(e)
    if setting.basefont["uigothic"] <> setting.basefont_init["uigothic"]:
        e = cw.data.make_element("FontUIGothic", setting.basefont["uigothic"])
        element.append(e)
    if setting.basefont["mincho"] <> setting.basefont_init["mincho"]:
        e = cw.data.make_element("FontMincho", setting.basefont["mincho"])
        element.append(e)
    if setting.basefont["pmincho"] <> setting.basefont_init["pmincho"]:
        e = cw.data.make_element("FontPMincho", setting.basefont["pmincho"])
        element.append(e)
    if setting.basefont["pgothic"] <> setting.basefont_init["pgothic"]:
        e = cw.data.make_element("FontPGothic", setting.basefont["pgothic"])
        element.append(e)

    # 役割別フォント
    e = cw.data.make_element("Fonts")
    for key, value in setting.fonttypes.iteritems():
        if setting.fonttypes[key] <> setting.fonttypes_init[key]:
            fonttype, name, pixels, bold, bold_upscr, italic = value
            attrs = {"key": key}.copy()
            if fonttype:
                attrs["type"] = fonttype
            if 0 < pixels:
                attrs["pixels"] = str(pixels)
            if not bold is None:
                attrs["bold"] = str(bold)
            if not bold_upscr is None:
                attrs["expandedbold"] = str(bold_upscr)
            if not italic is None:
                attrs["italic"] = str(italic)
            fe = cw.data.make_element("Font", name, attrs=attrs)
            e.append(fe)
    if len(e):
        element.append(e)

    # カード名の文字を滑らかにする
    if setting.fontsmoothing_cardname <> setting.fontsmoothing_cardname_init:
        e = cw.data.make_element("FontSmoothingCardName", str(setting.fontsmoothing_cardname))
        element.append(e)
    # ステータスバーの文字を滑らかにする
    if setting.fontsmoothing_statusbar <> setting.fontsmoothing_statusbar_init:
        e = cw.data.make_element("FontSmoothingStatusBar", str(setting.fontsmoothing_statusbar))
        element.append(e)

    if writeplayingdata:
        # シナリオ絞込・整列条件
        if setting.scenario_narrowtype <> setting.scenario_narrowtype_init:
            e = cw.data.make_element("ScenarioNarrowType", str(setting.scenario_narrowtype))
            element.append(e)
        if setting.scenario_sorttype <> setting.scenario_sorttype_init:
            e = cw.data.make_element("ScenarioSortType", str(setting.scenario_sorttype))
            element.append(e)

    # スクリーンショット情報
    if setting.ssinfoformat <> setting.ssinfoformat_init:
        e = cw.data.make_element("ScreenShotInformationFormat", setting.ssinfoformat)
        element.append(e)
    # スクリーンショット情報の色
    if setting.ssinfofontcolor <> setting.ssinfofontcolor_init:
        d = {"red": str(setting.ssinfofontcolor[0]),
             "green": str(setting.ssinfofontcolor[1]),
             "blue": str(setting.ssinfofontcolor[2])
             }
        e = cw.data.make_element("ScreenShotInformationFontColor", "", d)
        element.append(e)
    if setting.ssinfobackcolor <> setting.ssinfobackcolor_init:
        d = {"red": str(setting.ssinfobackcolor[0]),
             "green": str(setting.ssinfobackcolor[1]),
             "blue": str(setting.ssinfobackcolor[2])
             }
        e = cw.data.make_element("ScreenShotInformationBackgroundColor", "", d)
        element.append(e)

    # イベント中にステータスバーの色を変える
    if setting.statusbarmask <> setting.statusbarmask_init:
        e = cw.data.make_element("StatusBarMask", str(setting.statusbarmask))
        element.append(e)

    # 次のレベルアップまでの割合を表示する
    if setting.show_experiencebar <> setting.show_experiencebar_init:
        e = cw.data.make_element("ShowExperienceBar", str(setting.show_experiencebar))
        element.append(e)

    # バトルラウンドを自動開始可能にする
    if setting.show_roundautostartbutton <> setting.show_roundautostartbutton_init:
        e = cw.data.make_element("ShowRoundAutoStartButton", str(setting.show_roundautostartbutton))
        element.append(e)

    # 新規登録ダイアログに自動ボタンを表示する
    if setting.show_autobuttoninentrydialog <> setting.show_autobuttoninentrydialog_init:
        e = cw.data.make_element("ShowAutoButtonInEntryDialog", str(setting.show_autobuttoninentrydialog))
        element.append(e)

    # タイトルバーの表示内容
    if setting.titleformat <> setting.titleformat_init:
        e = cw.data.make_element("TitleFormat", setting.titleformat)
        element.append(e)

    if writeplayingdata:
        # 逆変換先ディレクトリ
        if setting.unconvert_targetfolder <> setting.unconvert_targetfolder_init:
            e = cw.data.make_element("UnconvertTargetFolder", setting.unconvert_targetfolder)
            element.append(e)

    # 空白時間をスキップ可能にする
    if setting.can_skipwait <> setting.can_skipwait_init:
        e = cw.data.make_element("CanSkipWait", str(setting.can_skipwait))
        element.append(e)
    # アニメーションをスキップ可能にする
    if setting.can_skipanimation <> setting.can_skipanimation_init:
        e = cw.data.make_element("CanSkipAnimation", str(setting.can_skipanimation))
        element.append(e)
    # マウスの左ボタンを押し続けた時は連打状態にする
    if setting.can_repeatlclick <> setting.can_repeatlclick_init:
        e = cw.data.make_element("CanRepeatLClick", str(setting.can_repeatlclick))
        element.append(e)
    # カーソルタイプ
    if setting.cursor_type <> setting.cursor_type_init:
        e = cw.data.make_element("CursorType", setting.cursor_type)
        element.append(e)
    # 連打状態の時、カードなどの選択を自動的に決定する
    if setting.autoenter_on_sprite <> setting.autoenter_on_sprite_init:
        e = cw.data.make_element("AutoEnterOnSprite", str(setting.autoenter_on_sprite))
        element.append(e)
    # カード名を縁取りする
    if setting.bordering_cardname <> setting.bordering_cardname_init:
        e = cw.data.make_element("BorderingCardName", str(setting.bordering_cardname))
        element.append(e)
    # 通知のあるステータスボタンを点滅させる
    if setting.blink_statusbutton <> setting.blink_statusbutton_init:
        e = cw.data.make_element("BlinkStatusButton", str(setting.blink_statusbutton))
        element.append(e)
    # 所持金が増減した時に所持金欄を点滅させる
    if setting.blink_partymoney <> setting.blink_partymoney_init:
        e = cw.data.make_element("BlinkPartyMoney", str(setting.blink_partymoney))
        element.append(e)
    # ステータスバーのボタンの解説を表示する
    if setting.show_btndesc <> setting.show_btndesc_init:
        e = cw.data.make_element("ShowButtonDescription", str(setting.show_btndesc))
        element.append(e)
    # スターつきのカードの売却や破棄を禁止する
    if setting.protect_staredcard <> setting.protect_staredcard_init:
        e = cw.data.make_element("ProtectStaredCard", str(setting.protect_staredcard))
        element.append(e)
    # プレミアカードの売却や破棄を禁止する
    if setting.protect_premiercard <> setting.protect_premiercard_init:
        e = cw.data.make_element("ProtectPremierCard", str(setting.protect_premiercard))
        element.append(e)
    # カード置場と荷物袋でカードの種類を表示する
    if setting.show_cardkind <> setting.show_cardkind_init:
        e = cw.data.make_element("ShowCardKind", str(setting.show_cardkind))
        element.append(e)
    # カードの希少度をアイコンで表示する
    if setting.show_premiumicon <> setting.show_premiumicon_init:
        e = cw.data.make_element("ShowPremiumIcon", str(setting.show_premiumicon))
        element.append(e)
    # カード選択ダイアログの背景クリックで左右移動を行う
    if setting.can_clicksidesofcardcontrol <> setting.can_clicksidesofcardcontrol_init:
        e = cw.data.make_element("CanClickSidesOfCardControl", str(setting.can_clicksidesofcardcontrol))
        element.append(e)
    # シナリオ選択ダイアログで貼紙と一覧を同時に表示する
    if setting.show_paperandtree <> setting.show_paperandtree_init:
        e = cw.data.make_element("ShowPaperAndTree", str(setting.show_paperandtree))
        element.append(e)
    # シナリオ選択ダイアログでのファイラー
    if setting.filer_dir <> setting.filer_dir_init:
        e = cw.data.make_element("FilerDirectory", setting.filer_dir)
        element.append(e)
    if setting.filer_file <> setting.filer_file_init:
        e = cw.data.make_element("FilerFile", setting.filer_file)
        element.append(e)

    # 圧縮されたシナリオの展開データ保存数
    if setting.recenthistory_limit <> setting.recenthistory_limit_init:
        e = cw.data.make_element("RecentHistoryLimit", setting.recenthistory_limit)
        element.append(e)

    if writeplayingdata:
        # 一覧表示
        attrs = {}
        if setting.show_multiplebases or setting.show_multiplebases_init:
            attrs["base"] = str(setting.show_multiplebases)
        if setting.show_multipleparties or setting.show_multipleparties_init:
            attrs["party"] = str(setting.show_multipleparties)
        if setting.show_multipleplayers or setting.show_multipleplayers_init:
            attrs["player"] = str(setting.show_multipleplayers)
        if setting.show_scenariotree or setting.show_scenariotree_init:
            attrs["scenario"] = str(setting.show_scenariotree)
        if attrs:
            e = cw.data.make_element("ShowMultipleItems", "", attrs=attrs)
            element.append(e)

    # ファイル書き込み
    path = fpath
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

    sets = set(["Name", "ImagePath", "ImagePaths", "Description", "Level",
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

    for key, value in d.items():
        d[key] = cw.binary.util.repl_escapechar(value)

    # 画像パス
    paths = data.imgpaths
    advname = cw.util.repl_dischar(d["name"])
    infos = write_castimagepath(advname, paths)
    imgpaths = map(lambda info: cw.binary.xmltemplate.get_xmltext("ImagePath",
                    {"path":cw.binary.util.repl_escapechar(info.path), "indent": "   "}), infos)
    d["imgpaths"] = "\n" + "\n".join(imgpaths)

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

def write_castimagepath(name, paths):
    """
    キャストの新しい画像を記憶し、記憶後のパスを返す。
    """
    seq = []
    for info in paths:
        path = info.path
        if os.path.isfile(path):
            dpath = cw.util.join_paths(cw.cwpy.tempdir, "Material/Adventurer", name)
            dpath = cw.util.dupcheck_plus(dpath)
            ext = cw.util.splitext(os.path.basename(path))[1]
            dstpath = cw.util.join_paths(dpath, name + ext)

            if not os.path.isdir(dpath):
                os.makedirs(dpath)

            shutil.copy2(path, dstpath)
            seq.append(cw.image.ImageInfo(dstpath.replace(cw.cwpy.tempdir + "/", ""), base=info))
    return seq

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
    e = cw.data.make_element("RoundAutoStart", str(sdata.autostart_round))
    e_prop.append(e)
    e = cw.data.make_element("NoticeInfoView", str(sdata.notice_infoview))
    e_prop.append(e)

    if cw.cwpy.areaid >= 0:
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

    e_music = cw.data.make_element("MusicPaths")
    for i, music in enumerate(cw.cwpy.music):
        if music.path.startswith(cw.cwpy.skindir):
            fpath = music.path.replace(cw.cwpy.skindir + "/", "", 1)
        else:
            fpath = music.path.replace(sdata.scedir + "/", "", 1)
        e = cw.data.make_element("MusicPath", fpath, attrs={"channel": str(music.channel),
                                                            "volume": str(music.subvolume),
                                                            "loopcount": str(music.loopcount),
                                                            "inusecard": str(music.inusecard)})
        e_music.append(e)
    e_prop.append(e_music)
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

    for bgtype, d in cw.cwpy.background.bgs:
        if bgtype == cw.sprite.background.BG_IMAGE:
            fpath, inusecard, mask, size, pos, flag, visible, layer = d
            attrs = {"mask": str(mask), "visible": str(visible)}
            e_bgimg = cw.data.make_element("BgImage", attrs=attrs)

            if inusecard:
                e = cw.data.make_element("ImagePath", fpath, attrs={"inusecard":str(inusecard)})
            else:
                e = cw.data.make_element("ImagePath", fpath)
            e_bgimg.append(e)

        elif bgtype == cw.sprite.background.BG_TEXT:
            text, face, tsize, color, bold, italic, underline, strike, vertical,\
                btype, bcolor, bwidth, loaded, size, pos, flag, visible, layer = d
            attrs = {"visible": str(visible),
                     "loaded": str(loaded)}
            e_bgimg = cw.data.make_element("TextCell", attrs=attrs)

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

        elif bgtype == cw.sprite.background.BG_COLOR:
            blend, color1, gradient, color2, size, pos, flag, visible, layer = d
            attrs = {"visible": str(visible)}
            e_bgimg = cw.data.make_element("ColorCell", attrs=attrs)

            e = cw.data.make_element("BlendMode", blend)
            e_bgimg.append(e)
            e = make_colorelement("Color", color1)
            e_bgimg.append(e)

            if gradient <> "None":
                e = cw.data.make_element("Gradient", attrs={"direction": gradient})
                e.append(make_colorelement("EndColor", color2))
                e_bgimg.append(e)

        else:
            assert bgtype == cw.sprite.background.BG_SEPARATOR
            e_bgimg = cw.data.make_element("Redisplay")
            e_bgimgs.append(e_bgimg)
            continue

        e = cw.data.make_element("Flag", flag)
        e_bgimg.append(e)
        e = cw.data.make_element("Location",
                        attrs={"left": str(pos[0]), "top": str(pos[1])})
        e_bgimg.append(e)
        e = cw.data.make_element("Size",
                        attrs={"width": str(size[0]), "height": str(size[1])})
        e_bgimg.append(e)
        if layer <> cw.LAYER_BACKGROUND:
            e = cw.data.make_element("Layer", str(layer))
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

    for resid in sdata.get_infocards(order=True):
        e = cw.data.make_element("InfoCard", str(resid))
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
