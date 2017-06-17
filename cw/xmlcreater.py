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

def create_party(headers, moneyamount=0, pname=None, is_suspendlevelup=False):
    """
    新しくパーティを作る。
    headers: 初期メンバーのファイル名(拡張子無し)のlist。
    """
    if pname is None:
        pname = cw.cwpy.msgs["default_party_name"] % (headers[0].name)

    d = {"name" : cw.binary.util.repl_escapechar(pname),
         "money" : str(moneyamount),
         "suspend_levelup": str(is_suspendlevelup),
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
         "suspend_levelup": str(party.is_suspendlevelup),
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
    prop = cw.header.GetProperty(u"Data/SkinBase/Skin.xml")
    cashbox = int(prop.properties.get(u"InitialCash", "4000"))
    try:
        fpath = cw.util.join_paths(u"Data/Skin", skindirname, u"Skin.xml")
        prop = cw.header.GetProperty(fpath)
        skintype = prop.properties.get(u"Type", skintype)
        cashbox = int(prop.properties.get(u"InitialCash", str(cashbox)))
    except:
        cw.util.print_ex()

    d = {"name" : cw.binary.util.repl_escapechar(name),
         "skinname" : cw.binary.util.repl_escapechar(skindirname),
         "skintype" : cw.binary.util.repl_escapechar(skintype),
         "cashbox" : str(cashbox),
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
    element = cw.data.make_element("Settings", attrs={"dataVersion": "3"})

    create_localsettings(element, setting.local)

    # 最初から詳細モードで設定を行う
    if setting.show_advancedsettings <> setting.show_advancedsettings_init:
        e = cw.data.make_element("ShowAdvancedSettings", str(setting.show_advancedsettings))
        element.append(e)
    # シナリオエディタ
    if setting.editor <> setting.editor_init:
        e = cw.data.make_element("ScenarioEditor", setting.editor)
        element.append(e)
    # 起動時の動作
    if setting.startupscene <> setting.startupscene_init:
        e = cw.data.make_element("StartupScene", setting.startupscene)
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
    # シナリオの終了時にデバッグ情報を表示する
    if setting.show_debuglogdialog <> setting.show_debuglogdialog_init:
        e = cw.data.make_element("ShowDebugLogDialog", str(setting.show_debuglogdialog))
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
    # 召喚獣カードの拡大率を大きくする
    if setting.enlarge_beastcardzoomingratio <> setting.enlarge_beastcardzoomingratio_init:
        e = cw.data.make_element("EnlargeBeastCardZoomingRatio", str(setting.enlarge_beastcardzoomingratio))
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
        if setting.sort_yado <> setting.sort_yado_init:
            e.set("yado", setting.sort_yado)
        if setting.sort_standbys <> setting.sort_standbys_init:
            e.set("standbys", setting.sort_standbys)
        if setting.sort_cards <> setting.sort_cards_init:
            e.set("cards", setting.sort_cards)
        if setting.sort_cardswithstar <> setting.sort_cardswithstar_init:
            e.set("cardswithstar", str(setting.sort_cardswithstar))
        if e.attrib:
            element.append(e)
        # 拠点絞込条件
        if setting.yado_narrowtype <> setting.yado_narrowtype_init:
            e = cw.data.make_element("YadoNarrowType", str(setting.yado_narrowtype))
            element.append(e)
        # 宿帳絞込条件
        if setting.standbys_narrowtype <> setting.standbys_narrowtype_init:
            e = cw.data.make_element("StandbysNarrowType", str(setting.standbys_narrowtype))
            element.append(e)
        # パーティ絞込条件
        if setting.parties_narrowtype <> setting.parties_narrowtype_init:
            e = cw.data.make_element("PartiesNarrowType", str(setting.parties_narrowtype))
            element.append(e)
        # カード絞込条件
        if setting.card_narrowtype <> setting.card_narrowtype_init:
            e = cw.data.make_element("CardNarrowType", str(setting.card_narrowtype))
            element.append(e)
        # 情報カード絞込条件
        if setting.infoview_narrowtype <> setting.infoview_narrowtype_init:
            e = cw.data.make_element("InfoViewNarrowType", str(setting.infoview_narrowtype))
            element.append(e)
    # メッセージログ最大数
    if setting.backlogmax <> setting.backlogmax_init:
        e = cw.data.make_element("MessageLogMax", str(setting.backlogmax))
        element.append(e)
    # メッセージログ表示形式
    if setting.messagelog_type <> setting.messagelog_type_init:
        e = cw.data.make_element("MessageLogType", setting.messagelog_type)
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
        e = cw.data.make_element("ConfirmBeforeSaving", setting.confirm_beforesaving)
        element.append(e)
    # セーブ完了時に確認ダイアログを表示
    if setting.show_savedmessage <> setting.show_savedmessage_init:
        e = cw.data.make_element("ShowSavedMessage", str(setting.show_savedmessage))
        element.append(e)
    # カードの売却と破棄で確認ダイアログを表示
    if setting.confirm_dumpcard <> setting.confirm_dumpcard_init:
        e = cw.data.make_element("ConfirmBeforeDumpCard", setting.confirm_dumpcard)
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
        e = cw.data.make_element("ShowStatusTime", setting.show_statustime)
        element.append(e)
    # 不可能な行動を選択した時に警告を表示
    if setting.noticeimpossibleaction <> setting.noticeimpossibleaction_init:
        e = cw.data.make_element("NoticeImpossibleAction", str(setting.noticeimpossibleaction))
        element.append(e)

    # パーティ結成時の持出金額
    if setting.initmoneyamount <> setting.initmoneyamount_init or setting.initmoneyisinitialcash <> setting.initmoneyisinitialcash_init:
        attrs = {}
        if setting.initmoneyisinitialcash <> setting.initmoneyisinitialcash_init:
            attrs["sameasbase"] = str(setting.initmoneyisinitialcash)
        e = cw.data.make_element("InitialMoneyAmount", str(setting.initmoneyamount), attrs=attrs)
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
    # スクリーンショット情報の背景イメージ
    if setting.ssinfobackimage <> setting.ssinfobackimage_init:
        e = cw.data.make_element("ScreenShotInformationBackgroundImage", setting.ssinfobackimage)
        element.append(e)

    # スクリーンショットのファイル名
    if setting.ssfnameformat <> setting.ssfnameformat_init:
        e = cw.data.make_element("ScreenShotFileNameFormat", setting.ssfnameformat)
        element.append(e)
    # 所持カード撮影情報のファイル名
    if setting.cardssfnameformat <> setting.cardssfnameformat_init:
        e = cw.data.make_element("ScreenShotOfCardsFileNameFormat", setting.cardssfnameformat)
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

    # プレイログの表示内容
    if setting.playlogformat <> setting.playlogformat_init:
        e = cw.data.make_element("PlayLogFormat", setting.playlogformat)
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

    # マウスのホイールで空白時間とアニメーションをスキップする
    if setting.can_skipwait_with_wheel <> setting.can_skipwait_with_wheel_init:
        e = cw.data.make_element("CanSkipWaitWithWheel", str(setting.can_skipwait_with_wheel))
        element.append(e)
    # マウスのホイールでメッセージ送りを行う
    if setting.can_forwardmessage_with_wheel <> setting.can_forwardmessage_with_wheel_init:
        e = cw.data.make_element("CanForwardMessageWithWheel", str(setting.can_forwardmessage_with_wheel))
        element.append(e)

    # マウスの左ボタンを押し続けた時は連打状態にする
    if setting.can_repeatlclick <> setting.can_repeatlclick_init:
        e = cw.data.make_element("CanRepeatLClick", str(setting.can_repeatlclick))
        element.append(e)
    # 方向キーやホイールの選択中にマウスカーソルの移動を検知しない半径
    if setting.radius_notdetectmovement <> setting.radius_notdetectmovement_init:
        e = cw.data.make_element("RadiusForNotDetectingCursorMovement", str(setting.radius_notdetectmovement))
        element.append(e)
    # カーソルタイプ
    if setting.cursor_type <> setting.cursor_type_init:
        e = cw.data.make_element("CursorType", setting.cursor_type)
        element.append(e)
    # 連打状態の時、カードなどの選択を自動的に決定する
    if setting.autoenter_on_sprite <> setting.autoenter_on_sprite_init:
        e = cw.data.make_element("AutoEnterOnSprite", str(setting.autoenter_on_sprite))
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

    # マウスホイールによる全体音量の増減量
    if setting.volume_increment <> setting.volume_increment_init:
        e = cw.data.make_element("VolumeIncrement", setting.volume_increment)
        element.append(e)

    # シナリオのプレイログを出力する
    if setting.write_playlog <> setting.write_playlog_init:
        e = cw.data.make_element("WritePlayLog", str(setting.write_playlog))
        element.append(e)

    #  最後に選んだシナリオを開始地点にする
    if setting.open_lastscenario <> setting.open_lastscenario_init:
        e = cw.data.make_element("OpenLastScenario", str(setting.open_lastscenario))
        element.append(e)

    # ドロップによるシナリオのインストールを可能にする
    if setting.can_installscenariofromdrop <> setting.can_installscenariofromdrop_init:
        e = cw.data.make_element("CanInstallScenarioFromDrop", str(setting.can_installscenariofromdrop))
        element.append(e)

    #  シナリオのインストールに成功したら元ファイルを削除する
    if setting.delete_sourceafterinstalled <> setting.delete_sourceafterinstalled_init:
        e = cw.data.make_element("DeleteSourceAfterInstalled", str(setting.delete_sourceafterinstalled))
        element.append(e)

    # アップデートに伴うファイルの自動移動・削除を行う
    if setting.auto_update_files <> setting.auto_update_files_init:
        e = cw.data.make_element("AutoUpdateFiles", str(setting.auto_update_files))
        element.append(e)

    if writeplayingdata:
        # シナリオのインストール先(スキンタイプ毎)
        if setting.installed_dir:
            e = cw.data.make_element("InstalledPaths")
            for rootdir, dirstack in setting.installed_dir.iteritems():
                if not os.path.isdir(rootdir):
                    continue
                e_path = cw.data.make_element("InstalledPath", attrs={"root": rootdir})
                for dname in dirstack:
                    e_dir = cw.data.make_element("Path", dname)
                    e_path.append(e_dir)
                e.append(e_path)
            if len(e):
                element.append(e)

        # カード編集ダイアログのブックマーク
        if setting.bookmarks_for_cardedit:
            e = cw.data.make_element("BookmarksForCardEditor")
            for bookmarkpath, scname in setting.bookmarks_for_cardedit:
                e_bookmark = cw.data.make_element("Bookmark", bookmarkpath, attrs={"name": scname})
                e.append(e_bookmark)
            element.append(e)

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

        # 絞り込み・整列などのコントロールの表示有無
        attrs = {}
        if setting.show_additional_yado or setting.show_additional_yado_init:
            attrs["yado"] = str(setting.show_additional_yado)
        if setting.show_additional_player or setting.show_additional_player_init:
            attrs["player"] = str(setting.show_additional_player)
        if setting.show_additional_party or setting.show_additional_party_init:
            attrs["party"] = str(setting.show_additional_party)
        if setting.show_additional_scenario or setting.show_additional_scenario_init:
            attrs["scenario"] = str(setting.show_additional_scenario)
        if setting.show_additional_card or setting.show_additional_card_init:
            attrs["card"] = str(setting.show_additional_card)
        if attrs or setting.show_addctrlbtn <> setting.show_addctrlbtn_init:
            e = cw.data.make_element("ShowAdditionalControls", "" if setting.show_addctrlbtn else "Hidden", attrs=attrs)
            element.append(e)

    # フォントサンプルのフォーマット
    if setting.fontexampleformat <> setting.fontexampleformat_init:
        e = cw.data.make_element("FontExampleFormat", setting.fontexampleformat)
        element.append(e)

    # ファイル書き込み
    path = fpath
    etree = cw.data.xml2etree(element=element)
    etree.write(path)
    return path

def create_localsettings(element, local):
    if local.important_draw <> local.important_draw_init:
        element.set("importantdrawing", str(local.important_draw))
    if local.important_font <> local.important_font_init:
        element.set("importantfont", str(local.important_font))

    # メッセージウィンドウの色と透明度
    if local.mwincolour <> local.mwincolour_init:
        d = {"red": str(local.mwincolour[0]),
             "green": str(local.mwincolour[1]),
             "blue": str(local.mwincolour[2]),
             "alpha": str(local.mwincolour[3])
             }
        e = cw.data.make_element("MessageWindowColor", "", d)
        element.append(e)
    if local.mwinframecolour <> local.mwinframecolour_init:
        d = {"red": str(local.mwinframecolour[0]),
             "green": str(local.mwinframecolour[1]),
             "blue": str(local.mwinframecolour[2]),
             "alpha": str(local.mwinframecolour[3])
             }
        e = cw.data.make_element("MessageWindowFrameColor", "", d)
        element.append(e)
    # バックログウィンドウの色と透明度
    if local.blwincolour <> local.blwincolour_init:
        d = {"red": str(local.blwincolour[0]),
             "green": str(local.blwincolour[1]),
             "blue": str(local.blwincolour[2]),
             "alpha": str(local.blwincolour[3])
             }
        e = cw.data.make_element("MessageLogWindowColor", "", d)
        element.append(e)
    if local.blwinframecolour <> local.blwinframecolour_init:
        d = {"red": str(local.blwinframecolour[0]),
             "green": str(local.blwinframecolour[1]),
             "blue": str(local.blwinframecolour[2]),
             "alpha": str(local.blwinframecolour[3])
             }
        e = cw.data.make_element("MessageLogWindowFrameColor", "", d)
        element.append(e)
    # メッセージログカーテン色
    if local.blcurtaincolour <> local.blcurtaincolour_init:
        d = {"red": str(local.blcurtaincolour[0]),
             "green": str(local.blcurtaincolour[1]),
             "blue": str(local.blcurtaincolour[2]),
             "alpha": str(local.blcurtaincolour[3])
             }
        e = cw.data.make_element("MessageLogCurtainColor", "", d)
        element.append(e)
    # カーテン色
    if local.curtaincolour <> local.curtaincolour_init:
        d = {"red": str(local.curtaincolour[0]),
             "green": str(local.curtaincolour[1]),
             "blue": str(local.curtaincolour[2]),
             "alpha": str(local.curtaincolour[3])
             }
        e = cw.data.make_element("CurtainColor", "", d)
        element.append(e)

    # フルスクリーン時の背景タイプ(0:無し,1:ファイル指定,2:スキン)
    if local.fullscreenbackgroundtype <> local.fullscreenbackgroundtype_init:
        e = cw.data.make_element("FullScreenBackgroundType", str(local.fullscreenbackgroundtype))
        element.append(e)
    if local.fullscreenbackgroundfile <> local.fullscreenbackgroundfile_init:
        e = cw.data.make_element("FullScreenBackgroundFile", local.fullscreenbackgroundfile)
        element.append(e)

    # カード名を縁取りする
    if local.bordering_cardname <> local.bordering_cardname_init:
        e = cw.data.make_element("BorderingCardName", str(local.bordering_cardname))
        element.append(e)
    # メッセージで装飾フォントを使用する
    if local.decorationfont <> local.decorationfont_init:
        e = cw.data.make_element("DecorationFont", str(local.decorationfont))
        element.append(e)
    # メッセージの文字を滑らかにする
    if local.fontsmoothing_message <> local.fontsmoothing_message_init:
        e = cw.data.make_element("FontSmoothingMessage", str(local.fontsmoothing_message))
        element.append(e)
    # カード名の文字を滑らかにする
    if local.fontsmoothing_cardname <> local.fontsmoothing_cardname_init:
        e = cw.data.make_element("FontSmoothingCardName", str(local.fontsmoothing_cardname))
        element.append(e)
    # ステータスバーの文字を滑らかにする
    if local.fontsmoothing_statusbar <> local.fontsmoothing_statusbar_init:
        e = cw.data.make_element("FontSmoothingStatusBar", str(local.fontsmoothing_statusbar))
        element.append(e)

    # 基本フォント(空白時デフォルト)
    if local.basefont["gothic"] <> local.basefont_init["gothic"]:
        e = cw.data.make_element("FontGothic", local.basefont["gothic"])
        element.append(e)
    if local.basefont["uigothic"] <> local.basefont_init["uigothic"]:
        e = cw.data.make_element("FontUIGothic", local.basefont["uigothic"])
        element.append(e)
    if local.basefont["mincho"] <> local.basefont_init["mincho"]:
        e = cw.data.make_element("FontMincho", local.basefont["mincho"])
        element.append(e)
    if local.basefont["pmincho"] <> local.basefont_init["pmincho"]:
        e = cw.data.make_element("FontPMincho", local.basefont["pmincho"])
        element.append(e)
    if local.basefont["pgothic"] <> local.basefont_init["pgothic"]:
        e = cw.data.make_element("FontPGothic", local.basefont["pgothic"])
        element.append(e)

    # 役割別フォント
    e = cw.data.make_element("Fonts")
    for key, value in local.fonttypes.iteritems():
        if value <> local.fonttypes_init[key]:
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

    can_loaded_scaledimage = etree.getbool(".", "scaledimage", False)
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
    name = name if name else "noname"
    fname = cw.util.repl_dischar(name)
    dstdir = cw.util.join_paths(cw.cwpy.yadodir, "Material/Album")
    cw.cwpy.copy_materials(element, dstdir, from_scenario=False,
                           can_loaded_scaledimage=can_loaded_scaledimage)
    if can_loaded_scaledimage:
        etree.edit(".", str(can_loaded_scaledimage), "scaledimage")
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
    infos = write_castimagepath(advname, paths, True)
    imgpaths = map(lambda info: cw.binary.xmltemplate.get_xmltext("ImagePath",
                    {"path":cw.binary.util.repl_escapechar(info.path),
                     "postype": info.postype,
                     "indent": "   "}), infos)
    d["imgpaths"] = "\n" + "\n".join(imgpaths)
    d["scaledimage"] = str(True)

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

def write_castimagepath(name, paths, can_loaded_scaledimage):
    """
    キャストの新しい画像を記憶し、記憶後のパスを返す。
    """
    seq = []
    if not name:
        name = "noname"
    for info in paths:
        path = info.path
        if os.path.isfile(path):
            dpath = cw.util.join_paths(cw.cwpy.tempdir, "Material/Adventurer", name)
            dpath = cw.util.dupcheck_plus(dpath)
            ext = cw.util.splitext(os.path.basename(path))[1]
            dstpath = cw.util.join_paths(dpath, name + ext)

            if not os.path.isdir(dpath):
                os.makedirs(dpath)

            cw.util.copy_scaledimagepaths(path, dstpath, can_loaded_scaledimage)
            seq.append(cw.image.ImageInfo(dstpath.replace(cw.cwpy.tempdir + "/", ""), base=info))
    return seq

def create_scenariolog(sdata, path, recording, logfilepath):
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
    if cw.cwpy.setting.write_playlog:
        e = cw.data.make_element("LogFile", logfilepath)
        e_prop.append(e)

    if cw.cwpy.areaid >= 0:
        areaid = cw.cwpy.areaid
    elif cw.cwpy.pre_areaids:
        areaid = cw.cwpy.pre_areaids[0][0]
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
            fpath, inusecard, scaledimage, mask, smoothing, size, pos, flag, visible, layer, cellname = d
            attrs = {"mask": str(mask), "visible": str(visible)}
            if cellname:
                attrs["cellname"] = cellname
            if smoothing <> "Default":
                attrs["smoothing"] = smoothing
            e_bgimg = cw.data.make_element("BgImage", attrs=attrs)

            if inusecard:
                e = cw.data.make_element("ImagePath", fpath, attrs={"inusecard":str(inusecard),
                                                                     "scaledimage": str(scaledimage)})
            else:
                e = cw.data.make_element("ImagePath", fpath)
            e_bgimg.append(e)

        elif bgtype == cw.sprite.background.BG_TEXT:
            text, namelist, face, tsize, color, bold, italic, underline, strike, vertical,\
                btype, bcolor, bwidth, loaded, size, pos, flag, visible, layer, cellname = d
            attrs = {"visible": str(visible),
                     "loaded": str(loaded)}
            if cellname:
                attrs["cellname"] = cellname
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

            if namelist:
                e = cw.data.make_element("Names")
                for item in namelist:
                    e_name = cw.data.make_element("Name", item.name)
                    if isinstance(item.data, cw.data.YadoData):
                        e_name.set("type", "Yado")
                    elif isinstance(item.data, cw.data.Party):
                        e_name.set("type", "Party")
                    elif isinstance(item.data, cw.character.Player) and item.data in cw.cwpy.get_pcards():
                        e_name.set("type", "Player")
                        e_name.set("number", str(cw.cwpy.get_pcards().index(item.data)+1))
                    e.append(e_name)
                e_bgimg.append(e)

        elif bgtype == cw.sprite.background.BG_COLOR:
            blend, color1, gradient, color2, size, pos, flag, visible, layer, cellname = d
            attrs = {"visible": str(visible)}
            if cellname:
                attrs["cellname"] = cellname
            e_bgimg = cw.data.make_element("ColorCell", attrs=attrs)

            e = cw.data.make_element("BlendMode", blend)
            e_bgimg.append(e)
            e = make_colorelement("Color", color1)
            e_bgimg.append(e)

            if gradient <> "None":
                e = cw.data.make_element("Gradient", attrs={"direction": gradient})
                e.append(make_colorelement("EndColor", color2))
                e_bgimg.append(e)

        elif bgtype == cw.sprite.background.BG_PC:
            pcnumber, expand, smoothing, size, pos, flag, visible, layer, cellname = d
            attrs = {"visible": str(visible),
                     "expand": str(expand)}
            if cellname:
                attrs["cellname"] = cellname
            if smoothing <> "Default":
                attrs["smoothing"] = smoothing
            e_bgimg = cw.data.make_element("PCCell", attrs=attrs)

            e = cw.data.make_element("PCNumber", str(pcnumber))
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
