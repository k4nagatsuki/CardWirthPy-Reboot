#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import copy
import time
import shutil
import threading
import StringIO
import xml.parsers.expat
from xml.etree.ElementTree import ElementTree, _ElementInterface

import cw
import cw.scenariodb

#-------------------------------------------------------------------------------
#　システムデータ
#-------------------------------------------------------------------------------

class SystemData(object):
    def __init__(self):
        """
        引数のゲームの状態遷移の情報によって読み込むxmlを変える。
        """
        cw.cwpy.debug = cw.cwpy.setting.debug
        self.name = ""
        self.author = ""
        self.tempdir = ""
        self.scedir = ""
        self._init_xmlpaths()
        self._init_sparea_mcards()
        self.data = None
        self.events = None
        self.deletedpaths = set()
        self.lostadventurers = set()
        self.gossips = {}
        self.comstamps = {}
        self.friendcards = []
        self.infocards = []
        self.flags = {}
        self.steps = {}
        self.labels = {}
        # refresh debugger
        self._init_debugger()

    def _init_debugger(self):
        cw.cwpy.event.refresh_variablelist()

    def _init_xmlpaths(self):
        self.areas = {}
        self.battles = {}
        self.packs = {}
        self.casts = {}
        self.infos = {}
        self.items = {}
        self.skills = {}
        self.beasts = {}
        dpath = cw.util.join_paths(cw.cwpy.skindir,
                                            u"Resource/Xml", cw.cwpy.status)

        for fname in os.listdir(dpath):
            path = cw.util.join_paths(dpath, fname)

            if os.path.isfile(path) and fname.endswith(".xml"):
                e = xml2element(path, "Property")
                id = e.getint("Id")
                name = e.gettext("Name")
                self.areas[id] = (name, path)

    def _init_sparea_mcards(self):
        """
        カード移動操作エリアのメニューカードを作成する。
        エリア移動時のタイムラグをなくすための操作。
        """
        d = {}
        areaid = cw.cwpy.areaid

        for key, value in self.areas.iteritems():
            if key in cw.AREAS_TRADE:
                cw.cwpy.areaid = key
                self.data = xml2etree(value[1])
                cw.cwpy.mcardgrp.empty()
                cw.cwpy.set_mcards(self.get_mcarddata(), False)
                mcards = cw.cwpy.mcardgrp.remove_sprites_of_layer(0)

                if cw.cwpy.is_autospread():
                    cw.cwpy.set_autospread(mcards)

                d[key] = mcards

        self.sparea_mcards = d
        cw.cwpy.areaid = areaid
        self.data = None

    def start(self):
        pass

    def end(self):
        pass

    def change_data(self, id):
        if cw.cwpy.is_battlestatus():
            path = self.battles[id][1]
        else:
            path = self.areas[id][1]

        self.data = xml2etree(path)
        cw.cwpy.event.refresh_areaname()
        self.events = cw.event.EventEngine(self.data.getfind("Events"))

    def start_event(self, keynum=None, keycodes=[]):
        cw.cwpy.statusbar.change(False)
        self.events.start(keynum=keynum, keycodes=keycodes)
        if not cw.cwpy.is_dealing() and not cw.cwpy.battle:
            cw.cwpy.statusbar.change()

    def check_bginhrt(self, elements=[]):
        """
        現在のエリアが背景継承かどうかをbool値で返す。
        最初の背景画像のpathが空だったら背景継承で削除しない。
        """
        if not elements and self.data:
            elements = self.get_bgdata()

        return not bool(not self.data or\
                            elements and elements[0].getfind("ImagePath").text)

    def get_areaname(self):
        """現在滞在中のエリアの名前を返す"""
        if cw.cwpy.is_battlestatus():
            return self.battles[cw.cwpy.areaid][0]
        else:
            return self.areas[cw.cwpy.areaid][0]

    def get_bgdata(self, e=None):
        """背景のElementのリストを返す。
        e: BgImagesのElement。
        """
        if e is None:
            e = self.data.find("BgImages")

        if e is not None:
            return e.getchildren()
        else:
            return []

    def get_mcarddata(self):
        """spreadtypeの値("Custom", "Auto")と
        メニューカードのElementのリストをタプルで返す。
        """
        e = self.data.find("MenuCards")
        if e is None:
            e = self.data.find("EnemyCards")

        if e is not None:
            stype = e.get("spreadtype", "Auto")
            elements = e.getchildren()
        else:
            stype = "Custom"
            elements = []

        return stype, elements

#-------------------------------------------------------------------------------
#　シナリオデータ
#-------------------------------------------------------------------------------

class ScenarioData(SystemData):
    def __init__(self, header, cardonly=False):
        self._playing = True
        self.fpath = header.get_fpath()
        self.name = header.name
        self.author = header.author
        self.startid = header.startid
        if not cardonly:
            cw.cwpy.areaid = self.startid
        if os.path.isfile(self.fpath):
            # zip解凍・解凍したディレクトリを登録
            self.tempdir = cw.cwpy.recenthistory.check(self.fpath)
            if self.tempdir:
                cw.cwpy.recenthistory.moveend(self.fpath)
            else:
                self.tempdir = u"Data/Temp/Scenario"
                if self.fpath.lower().endswith(".cab"):
                    self.tempdir = cw.util.decompress_cab(self.fpath, self.tempdir, avoiddup=True)
                else:
                    self.tempdir = cw.util.decompress_zip(self.fpath, self.tempdir, avoiddup=True)
                cw.cwpy.recenthistory.append(self.fpath, self.tempdir)
        else:
            # 展開済みシナリオ
            self.tempdir = self.fpath

        if cw.scenariodb.TYPE_CLASSIC == header.type:
            cw.cwpy.classicdata = cw.binary.cwscenario.CWScenario(
                self.tempdir, "Data/Temp/OldScenario", cw.cwpy.setting.skintype,
                materialdir="", image_export=False)

        # 各種xmlファイルのパスを設定
        self._init_xmlpaths()

        if cardonly:
            return

        # 特殊エリアのメニューカードを作成
        self._init_sparea_mcards()
        # エリアデータ初期化
        self.data = None
        self.events = None
        # シナリオプレイ中に削除されたファイルパスの集合
        self.deletedpaths = set()
        # ロストした冒険者のXMLファイルパスの集合
        self.lostadventurers = set()
        # シナリオプレイ中に追加・削除した終了印・ゴシップの辞書
        # key: 終了印・ゴシップ名
        # value: Trueなら追加。Falseなら削除。
        self.gossips = {}
        self.compstamps = {}
        # FriendCardのリスト
        self.friendcards = []
        # 情報カードのリスト(InfoCardHeader)
        self.infocards = []
        # flag set
        self._init_flags()
        # step set
        self._init_steps()
        # refresh debugger
        self._init_debugger()

        # ロードしたデータファイルのキャッシュ
        self.cache = {}

    def reload(self):
        flagvals = {}
        stepvals = {}
        for name, flag in self.flags.items():
            flagvals[name] = flag.value
        for name, step in self.steps.items():
            stepvals[name] = step.value
        self.cache = {}
        self._init_xmlpaths()
        self._init_flags()
        self._init_steps()

        for name, value in flagvals.items():
            if name in self.flags:
                flag = self.flags[name]
                if flag.value <> value:
                    flag.value = value
                    flag.redraw_cards()
        for name, value in stepvals.items():
            if name in self.steps:
                self.steps[name].value = value

        self._init_debugger()

    def _init_xmlpaths(self):
        """
        シナリオで使用されるXMLファイルのパスを辞書登録。
        また、"Summary.xml"のあるフォルダをシナリオディレクトリに設定する。
        """
        # 解凍したシナリオのディレクトリ
        self.scedir = ""
        # summary(CWPyElementTree)
        self.summary = None
        # 各xmlの(name, path)の辞書(IDがkey)
        self.areas = {}
        self.battles = {}
        self.packs = {}
        self.casts = {}
        self.infos = {}
        self.items = {}
        self.skills = {}
        self.beasts = {}

        # 特殊文字の画像パスの集合(正規表現)
        r_specialchar = re.compile(r"font_(.)[.].*$")

        for dpath, dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                # "font_*.*"のファイルパスの画像を特殊文字に指定
                if r_specialchar.match(fname.lower()):
                    m = r_specialchar.match(fname.lower())
                    path = cw.util.join_paths(dpath, fname)
                    image = cw.util.load_image(path, True)
                    name = "#%s" % (m.group(1))
                    cw.cwpy.rsrc.specialchars[name] = (image, True)
                    cw.cwpy.rsrc.specialchars_is_changed = True
                    continue
                else:
                    lf = fname.lower()
                    if not (lf.endswith(".xml") or lf.endswith(".wsm") or lf.endswith(".wid")):
                        # シナリオファイル以外はここで処理終わり
                        continue
                    if (lf.endswith(".wsm") or lf.endswith(".wid")) and dpath <> self.tempdir:
                        # クラシックなシナリオはディレクトリ直下のみ読み込む
                        continue

                path = cw.util.join_paths(dpath, fname)

                if (fname == "Summary.xml" or fname == "Summary.wsm") and not self.summary:
                    self.scedir = dpath.replace("\\", "/")
                    self.summary = xml2etree(path)
                    continue

                if lf.endswith(".xml"):
                    # wsnシナリオの基本要素一覧情報
                    e = xml2element(path, "Property")
                    id = e.getint("Id")
                    name = e.gettext("Name", "")
                else:
                    # クラシックなシナリオの基本要素一覧情報
                    wdata = cw.cwpy.classicdata.load_file(path, nameonly=True)
                    id = wdata.id
                    name = wdata.name

                if dpath.endswith("Area") or fname.startswith("Area"):
                    self.areas[id] = (name, path)
                elif dpath.endswith("Battle") or fname.startswith("Battle"):
                    self.battles[id] = (name, path)
                elif dpath.endswith("Package") or fname.startswith("Package"):
                    self.packs[id] = (name, path)
                elif dpath.endswith("CastCard") or fname.startswith("Mate"):
                    self.casts[id] = (name, path)
                elif dpath.endswith("InfoCard") or fname.startswith("Info"):
                    self.infos[id] = (name, path)
                elif dpath.endswith("ItemCard") or fname.startswith("Item"):
                    self.items[id] = (name, path)
                elif dpath.endswith("SkillCard") or fname.startswith("Skill"):
                    self.skills[id] = (name, path)
                elif dpath.endswith("BeastCard") or fname.startswith("Beast"):
                    self.beasts[id] = (name, path)

        if not self.summary:
            raise ValueError("Summary file is not found.")

        # 特殊エリアのxmlファイルのパスを設定
        dpath = cw.util.join_paths(cw.cwpy.skindir, u"Resource/Xml/Scenario")

        for fname in os.listdir(dpath):
            path = cw.util.join_paths(dpath, fname)

            if os.path.isfile(path) and fname.endswith(".xml"):
                e = xml2element(path, "Property")
                id = e.getint("Id")
                name = e.gettext("Name")
                self.areas[id] = (name, path)

    def _init_flags(self):
        """
        summary.xmlで定義されているフラグを初期化。
        """
        self.flags = {}

        for e in self.summary.getfind("Flags"):
            value = e.getbool("", "default")
            name = e.gettext("Name", "")
            truename = e.gettext("True", "")
            falsename = e.gettext("False", "")
            self.flags[name] = Flag(value, name, truename, falsename)

    def _init_steps(self):
        """
        summary.xmlで定義されているステップを初期化。
        """
        self.steps = {}

        for e in self.summary.getfind("Steps"):
            value = e.getint("", "default")
            name = e.gettext("Name", "")
            valuenames = [e.gettext("Value" + str(n), "") for n in xrange(10)]
            self.steps[name] = Step(value, name, valuenames)

    def reset_variables(self):
        """すべての状態変数を初期化する。"""
        for e in self.summary.find2("/Steps"):
            value = e.getint("", "default")
            name = e.gettext("Name", "")
            self.steps[name].set(value)

        for e in self.summary.getfind("/Flags"):
            value = e.getbool("", "default")
            name = e.gettext("Name", "")
            self.flags[name].set(value)
            self.flags[name].redraw_cards()

    def start(self):
        """
        シナリオの開始時の共通処理をまとめたもの。
        荷物袋のカード画像の更新を行う。
        """
        self._playing = True

        for header in cw.cwpy.ydata.party.get_allcardheaders():
            header.set_scenariostart()

    def end(self):
        """
        シナリオの正規終了時の共通処理をまとめたもの。
        冒険の中断時やF9時には呼ばない。
        """
        self._playing = False

        # ロストした冒険者を削除
        for path in self.lostadventurers:
            ccard = cw.character.Character(yadoxml2etree(path))

            # "＿消滅予約"を持ってない場合、アルバムに残す
            if not ccard.has_coupon(u"＿消滅予約"):
                path = cw.xmlcreater.create_albumpage(ccard.data.fpath, True)
                cw.cwpy.ydata.add_album(path)

            cw.cwpy.remove_xml(ccard.data.fpath)

        self.remove_log()
        cw.cwpy.ydata.deletedpaths.update(self.deletedpaths)

        # シナリオ取得カードの正規取得処理などを行う
        if cw.cwpy.ydata.party:
            for header in cw.cwpy.ydata.party.get_allcardheaders():
                header.set_scenarioend()

    def f9(self):
        """
        シナリオ強制終了。俗に言うファッ○ユー。
        """
        self._playing = False
        # battle
        if cw.cwpy.battle and cw.cwpy.battle.is_running:
            # バトルを強制終了
            cw.cwpy.exec_func(cw.cwpy.battle.end)
        # party copy
        fname = os.path.basename(cw.cwpy.ydata.party.data.fpath)
        path = cw.util.join_paths("Data/Temp/ScenarioLog/Party", fname)
        dstpath = cw.util.join_paths(cw.cwpy.ydata.tempdir, "Party", fname)
        dpath = os.path.dirname(dstpath)

        if not os.path.isdir(dpath):
            os.makedirs(dpath)

        shutil.copy2(path, dstpath)
        # member copy
        dpath = u"Data/Temp/ScenarioLog/Members"

        for name in os.listdir(dpath):
            path = cw.util.join_paths(dpath, name)

            if os.path.isfile(path) and path.endswith(".xml"):
                dstpath = cw.util.join_paths(cw.cwpy.ydata.tempdir,
                                                        "Adventurer", name)

                dstdir = os.path.dirname(dstpath)

                if not os.path.isdir(dstdir):
                    os.makedirs(dstdir)

                shutil.copy2(path, dstpath)

        # gossips
        for key, value in self.gossips.iteritems():
            if value:
                cw.cwpy.ydata.remove_gossip(key)
            else:
                cw.cwpy.ydata.set_gossip(key)

        # completestamps
        for key, value in self.compstamps.iteritems():
            if value:
                cw.cwpy.ydata.remove_compstamp(key)
            else:
                cw.cwpy.ydata.set_compstamp(key)

        self.remove_log()
        cw.cwpy.ydata.party.reload()

        if not cw.cwpy.areaid > 0:
            cw.cwpy.areaid = cw.cwpy.pre_areaids[0]

        cw.cwpy.music.stop()
        cw.cwpy.exec_func(cw.cwpy.f9)

    def set_log(self):
        """
        wslファイルの読み込みまたは新規作成を行う。
        読み込みを行った場合はTrue、新規作成を行った場合はFalseを返す。
        """
        cw.util.remove("Data/Temp/ScenarioLog")
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path:
            cw.util.decompress_zip(path, "Data/Temp", "ScenarioLog")
            musicpath = self.load_log()
            return True, musicpath
        else:
            self.create_log()
            return False, None

    def create_log(self):
        # log
        cw.xmlcreater.create_scenariolog(self)
        # Party and members xml update
        cw.cwpy.ydata.party.write()
        # party
        os.makedirs("Data/Temp/ScenarioLog/Party")
        path = cw.util.get_yadofilepath(cw.cwpy.ydata.party.data.fpath)
        dstpath = cw.util.join_paths("Data/Temp/ScenarioLog/Party",
                                                    os.path.basename(path))
        shutil.copy2(path, dstpath)
        # member
        os.makedirs("Data/Temp/ScenarioLog/Members")

        for data in cw.cwpy.ydata.party.members:
            path = cw.util.get_yadofilepath(data.fpath)
            dstpath = cw.util.join_paths("Data/Temp/ScenarioLog/Members",
                                                    os.path.basename(path))
            shutil.copy2(path, dstpath)

        # create_zip
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith(cw.cwpy.yadodir):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip("Data/Temp/ScenarioLog", path)
        cw.cwpy.ydata.deletedpaths.discard(path)

    def remove_log(self):
        cw.util.remove("Data/Temp/ScenarioLog")
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        cw.cwpy.ydata.deletedpaths.add(path)

    def load_log(self):
        path = "Data/Temp/ScenarioLog/ScenarioLog.xml"
        etree = xml2etree(path)
        cw.cwpy.debug = etree.getbool("/Property/Debug")

        if not cw.cwpy.debug == cw.cwpy.setting.debug:
            cw.cwpy.statusbar.change()

            if not cw.cwpy.debug and cw.cwpy.is_showingdebugger():
                cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)

        for e in etree.getfind("/Flags"):
            self.flags[e.text].value = e.getbool("", "value")

        for e in etree.getfind("/Steps"):
            self.steps[e.text].value = e.getint("", "value")

        for e in etree.getfind("/Gossips"):
            if e.get("value") == "True":
                self.gossips[e.text] = True
            elif e.get("value") == "False":
                self.gossips[e.text] = False

        for e in etree.getfind("/CompleteStamps"):
            if e.get("value") == "True":
                self.compstamps[e.text] = True
            elif e.get("value") == "False":
                self.compstamps[e.text] = False

        for e in etree.getfind("/InfoCards"):
            if int(e.text) in self.infos:
                path = self.infos[int(e.text)][1]
                e = xml2element(path, "Property")
                header = cw.header.InfoCardHeader(e)
                self.infocards.insert(0, header)

        for e in etree.getfind("/CastCards"):
            data = xml2etree(element=e)
            fcard = cw.sprite.card.FriendCard(data=data)
            self.friendcards.append(fcard)

        for e in etree.getfind("/DeletedFiles"):
            self.deletedpaths.add(e.text)

        for e in etree.getfind("/LostAdventurers"):
            self.lostadventurers.add(e.text)

        e = etree.getfind("BgImages")
        elements = cw.cwpy.sdata.get_bgdata(e)
        ttype = ("Default", "Default")
        cw.cwpy.background.load(elements, False, ttype)
        self.startid = cw.cwpy.areaid = etree.getint("/Property/AreaId")
        return etree.gettext("/Property/MusicPath", "")

    def update_log(self):
        cw.xmlcreater.create_scenariolog(self)
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith("Yado"):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip("Data/Temp/ScenarioLog", path)

class Flag(object):
    def __init__(self, value, name, truename, falsename):
        self.value = value
        self.name = name
        self.truename = truename
        self.falsename = falsename

    def __nonzero__(self):
        return self.value

    def redraw_cards(self):
        """対応するメニューカードの再描画処理"""
        if cw.cwpy.is_autospread():
            drawflag = False

            for mcard in cw.cwpy.get_mcards():
                mcardflag = cw.cwpy.sdata.flags.get(mcard.flag, True)

                if mcardflag and mcard.status == "hidden":
                    drawflag = True
                elif not mcardflag and not mcard.status == "hidden":
                    drawflag = True

            if drawflag:
                cw.cwpy.hide_cards(True)
                cw.cwpy.deal_cards()

        elif self.value:
            cw.cwpy.deal_cards()
        else:
            cw.cwpy.hide_cards()

    def set(self, value):
        self.value = value
        cw.cwpy.event.refresh_variable(self)

    def reverse(self):
        self.set(not self.value)

    def get_valuename(self, value=None):
        if value is None:
            value = self.value

        if value:
            return self.truename
        else:
            return self.falsename

class Step(object):
    def __init__(self, value, name, valuenames):
        self.value = value
        self.name = name
        self.valuenames = valuenames

    def set(self, value):
        value = cw.util.numwrap(value, 0, 9)
        self.value = value
        cw.cwpy.event.refresh_variable(self)

    def up(self):
        if not self.value >= 9:
            self.set(self.value + 1)

    def down(self):
        if not self.value <= 0:
            self.set(self.value - 1)

    def get_valuename(self, value=None):
        if value is None:
            value = self.value

        return self.valuenames[value]

#-------------------------------------------------------------------------------
#　宿データ
#-------------------------------------------------------------------------------

class YadoDeletedPathSet(set):
    def __init__(self, yadodir, tempdir):
        self.yadodir = yadodir
        self.tempdir = tempdir
        set.__init__(self)

    def __contains__(self, path):
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        return set.__contains__(self, path)

    def add(self, path):
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.deletedpaths.add(path)
        else:
            set.add(self, path)

    def remove(self, path):
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        set.remove(self, path)

    def discard(self, path):
        if path in self:
            self.remove(path)

class YadoData(object):
    def __init__(self):
        # 宿データのあるディレクトリ
        self.yadodir = cw.cwpy.yadodir
        self.tempdir = cw.cwpy.tempdir

        if not os.path.isdir(self.tempdir):
            os.makedirs(self.tempdir)

        # セーブ時に削除する予定のファイルパスの集合
        self.deletedpaths = YadoDeletedPathSet(self.yadodir, self.tempdir)
        # Environment(CWPyElementTree)
        path = cw.util.join_paths(self.yadodir, "Environment.xml")
        self.environment = yadoxml2etree(path)
        e = self.environment.find("Property/Name")
        if not e is None:
            self.name = e.text
        else:
            # データのバージョンが古い場合はProperty/Nameが無い
            self.name = os.path.basename(self.yadodir)
            e = make_element("Name", self.name)
            self.environment.insert("Property", e, 0)
        # 宿の金庫
        self.money = int(self.environment.getroot().find("Property/Cashbox").text)

        self.yadodb = cw.yadodb.YadoDB(self.yadodir)
        self.yadodb.update()

        # パーティリスト(PartyHeader)
        self.partys = self.yadodb.get_parties()
        partypaths = set()
        for party in self.partys:
            for fpath in party.get_memberpaths():
                partypaths.add(fpath)

        # 待機中冒険者(AdventurerHeader)
        self.standbys = []
        for standby in self.yadodb.get_standbys():
            if not standby.fpath in partypaths:
                self.standbys.append(standby)

        # アルバム(AdventurerHeader)
        self.album = self.yadodb.get_album()

        # カード置場(CardHeader)
        self.storehouse = self.yadodb.get_cards()

        self.yadodb.close()

        # 現在選択中のパーティをセット
        self.party = None
        pname = self.environment.gettext("Property/NowSelectingParty", "")

        if pname:
            path = cw.util.join_paths(self.yadodir, "Party", pname + ".xml")
            seq = [header for header in self.partys if path == header.fpath]

            if seq:
                self.load_party(seq[0])
            else:
                self.load_party(None)

        else:
            self.load_party(None)

    def load_party(self, header=None):
        """
        header: PartyHeader
        引数のパーティー名のデータを読み込む。
        パーティー名がNoneの場合はパーティーデータは空になる
        """
        # パーティデータが変更されている場合はxmlをTempに吐き出す
        if self.party:
            self.party.write()
            if self.party.members:
                self.add_party(self.party.data.fpath)

        if header:
            self.party = Party(header.fpath)
            name = os.path.basename(header.fpath)
            name = os.path.splitext(name)[0]
            self.environment.edit("/Property/NowSelectingParty", name)

            if header in self.partys:
                self.partys.remove(header)

        else:
            self.party = None
            self.environment.edit("/Property/NowSelectingParty", "")

    def add_standbys(self, path):
        header = self.create_advheader(path)
        self.standbys.append(header)
        cw.util.sort_by_attr(self.standbys, "name")
        return header

    def add_album(self, path):
        header = self.create_advheader(path, True)
        self.album.append(header)
        cw.util.sort_by_attr(self.album, "name")
        return header

    def add_party(self, path):
        header = self.create_partyheader(path)
        self.partys.append(header)
        cw.util.sort_by_attr(self.partys, "name")
        return header

    def create_advheader(self, path="", album=False, element=None):
        """
        path: xmlのパス。
        album: Trueならアルバム用のAdventurerHeaderを作成。
        element: PropertyタグのElement。
        """
        if not element:
            element = yadoxml2element(path, "Property")

        return cw.header.AdventurerHeader(element, album)

    def create_cardheader(self, path="", element=None, owner=None):
        """
        path: xmlのパス。
        element: PropertyタグのElement。
        """
        if element is None:
            element = yadoxml2element(path, "Property")

        return cw.header.CardHeader(element, owner=owner)

    def create_partyheader(self, path="", element=None):
        """
        path: xmlのパス。
        element: PropertyタグのElement。
        """
        if element is None:
            element = yadoxml2element(path, "Property")

        return cw.header.PartyHeader(element)

    def create_party(self, header, chgarea=True):
        """新しくパーティを作る。
        header: AdventurerHeader
        """
        path = cw.xmlcreater.create_party(header)
        header = self.create_partyheader(path)
        cw.cwpy.load_party(header, chgarea=chgarea)

    def save(self):
        """宿データをセーブする。"""
        # カード置場の順序を記憶しておく
        cardorder = {}
        for i, header in enumerate(self.storehouse):
            if header.fpath.startswith(self.tempdir):
                fpath = os.path.relpath(header.fpath, self.tempdir)
            else:
                fpath = os.path.relpath(header.fpath, self.yadodir)
            fpath = cw.util.join_paths(fpath)
            cardorder[fpath] = i

        # ScenarioLog更新
        if cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.update_log()

        # environment.xml書き出し
        self.environment.write_xml()

        # party.xmlと冒険者のxmlファイル書き出し
        if self.party:
            self.party.write()

        # TEMPのファイルを移動
        for dpath, dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                path = cw.util.join_paths(dpath, fname)
                dstpath = path.replace(self.tempdir, self.yadodir, 1)

                if not os.path.isdir(os.path.dirname(dstpath)):
                    os.makedirs(os.path.dirname(dstpath))

                shutil.copy2(path, dstpath)

        # 削除予定のファイル削除
        # Materialディレクトリにある空のフォルダも削除
        materialdir = cw.util.join_paths(self.yadodir, "Material")

        for path in self.deletedpaths:
            cw.util.remove(path)
            dpath = os.path.dirname(path)

            if dpath.startswith(materialdir) and os.path.isdir(dpath)\
                                                    and not os.listdir(dpath):
                cw.util.remove(dpath)

        self.deletedpaths.clear()
        # 宿のtempフォルダを空にする
        cw.util.remove(self.tempdir)

        # カードデータベースを更新
        yadodb = cw.yadodb.YadoDB(self.yadodir)
        yadodb.update(cardorder=cardorder)
        yadodb.close()

    #---------------------------------------------------------------------------
    # ゴシップ・シナリオ終了印用メソッド
    #---------------------------------------------------------------------------

    def get_gossips(self):
        """ゴシップ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("Gossips")])

    def get_compstamps(self):
        """冒険済みシナリオ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("CompleteStamps")])

    def get_gossiplist(self):
        """ゴシップ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("Gossips")]

    def get_compstamplist(self):
        """冒険済みシナリオ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("CompleteStamps")]

    def has_compstamp(self, name):
        """冒険済みシナリオかどうかbool値で返す。
        name: シナリオ名。
        """
        for e in self.environment.getfind("CompleteStamps"):
            if e.text == name:
                return True

        return False

    def has_gossip(self, name):
        """ゴシップを所持しているかどうかbool値で返す。
        name: ゴシップ名
        """
        for e in self.environment.getfind("Gossips"):
            if e.text == name:
                return True

        return False

    def set_compstamp(self, name):
        """冒険済みシナリオ印をセットする。シナリオプレイ中に取得した
        シナリオ印はScenarioDataのリストに登録する。
        name: シナリオ名
        """
        if not self.has_compstamp(name):
            e = make_element("CompleteStamp", name)
            self.environment.append("/CompleteStamps", e)

            if cw.cwpy.is_playingscenario():
                if cw.cwpy.sdata.compstamps.get(name) is False:
                    cw.cwpy.sdata.compstamps.pop(name)
                else:
                    cw.cwpy.sdata.compstamps[name] = True

    def set_gossip(self, name):
        """ゴシップをセットする。シナリオプレイ中に取得した
        ゴシップはScenarioDataのリストに登録する。
        name: ゴシップ名
        """
        if not self.has_gossip(name):
            e = make_element("Gossip", name)
            self.environment.append("/Gossips", e)

            if cw.cwpy.is_playingscenario():
                if cw.cwpy.sdata.gossips.get(name) is False:
                    cw.cwpy.sdata.gossips.pop(name)
                else:
                    cw.cwpy.sdata.gossips[name] = True

    def remove_compstamp(self, name):
        """冒険済みシナリオ印を削除する。シナリオプレイ中に削除した
        シナリオ印はScenarioDataのリストから解除する。
        name: シナリオ名
        """
        elements = [e for e in self.environment.getfind("/CompleteStamps")
                                                            if e.text == name]

        for e in elements:
            self.environment.remove("/CompleteStamps", e)

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.compstamps.get(name) is True:
                cw.cwpy.sdata.compstamps.pop(name)
            else:
                cw.cwpy.sdata.compstamps[name] = False

    def remove_gossip(self, name):
        """ゴシップを削除する。シナリオプレイ中に削除した
        ゴシップはScenarioDataのリストから解除する。
        name: ゴシップ名
        """
        elements = [e for e in self.environment.getfind("/Gossips")
                                                            if e.text == name]

        for e in elements:
            self.environment.remove("/Gossips", e)

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.gossips.get(name) is True:
                cw.cwpy.sdata.gossips.pop(name)
            else:
                cw.cwpy.sdata.gossips[name] = False

    def clear_compstamps(self):
        """冒険済みシナリオ印を全て削除する。"""

        for e in self.environment.getfind("/CompleteStamps"):
            self.environment.remove("/CompleteStamps", e)

            if cw.cwpy.is_playingscenario():
                name = e.text
                if cw.cwpy.sdata.compstamps.get(name) is True:
                    cw.cwpy.sdata.compstamps.pop(name)
                else:
                    cw.cwpy.sdata.compstamps[name] = False

    def clear_gossips(self):
        """ゴシップを全て削除する。"""

        for e in self.environment.getfind("/Gossips"):
            self.environment.remove("/Gossips", e)

            if cw.cwpy.is_playingscenario():
                name = e.text
                if cw.cwpy.sdata.gossips.get(name) is True:
                    cw.cwpy.sdata.gossips.pop(name)
                else:
                    cw.cwpy.sdata.gossips[name] = False

    def set_money(self, value):
        """金庫に入っている金額を変更する。
        現在の所持金にvalue値をプラスするので注意。
        """
        self.money += value
        self.money = cw.util.numwrap(self.money, 0, 9999999)
        self.environment.edit("/Property/Cashbox", str(self.money))
        cw.cwpy.has_inputevent = True

    #---------------------------------------------------------------------------
    # パーティ連れ込み
    #---------------------------------------------------------------------------

    def join_npcs(self):
        """
        シナリオのNPCを宿に連れ込む。
        """
        for fcard in cw.cwpy.get_fcards():
            # 必須クーポンを所持していなかったら補填
            if not fcard.get_age() or not fcard.get_sex():
                cw.cwpy.sounds["signal"].play()
                cw.cwpy.call_modaldlg("DATACOMP", ccard=fcard)

            # システムクーポン
            fcard.set_coupon(u"＿" + fcard.name, 0)
            fcard.set_coupon(u"＠レベル原点", fcard.level)
            fcard.set_coupon(u"＠ＥＰ", 0)
            talent = fcard.get_talent()

            value = 10
            for nature in cw.cwpy.setting.nature:
                if u"＿" + nature.name == talent:
                    value = nature.levelmax
                    break

            fcard.set_coupon(u"＠本来の上限", value)
            gene = cw.header.Gene()
            gene.set_talentbit(talent)
            fcard.set_coupon(u"＠Ｇ" + gene.get_str(), 0)
            data = fcard.data

            # 所持カードの素材ファイルコピー
            for cardtype in ("SkillCard", "ItemCard", "BeastCard"):
                for e in data.getfind("/%ss" % (cardtype)):
                    # 対象カード名取得
                    name = e.gettext("Property/Name", "noname")
                    name = cw.util.repl_dischar(name)
                    # 素材ファイルコピー
                    dstdir = cw.util.join_paths(self.yadodir,
                                                    "Material", cardtype, name)
                    dstdir = cw.util.dupcheck_plus(dstdir)
                    cw.cwpy.copy_materials(e, dstdir)

            # カード画像コピー
            name = cw.util.repl_dischar(fcard.name)
            e = data.getfind("/Property")
            dstdir = cw.util.join_paths(self.yadodir,
                                                "Material", "Adventurer", name)
            dstdir = cw.util.dupcheck_plus(dstdir)
            cw.cwpy.copy_materials(e, dstdir)
            # xmlファイル書き込み
            data.getroot().tag = "Adventurer"
            path = cw.util.join_paths(self.tempdir, "Adventurer", name + ".xml")
            path = cw.util.dupcheck_plus(path)
            data.write(path)
            # 待機中冒険者のリストに追加
            self.add_standbys(path)

    #---------------------------------------------------------------------------
    # ここからpathリスト取得用メソッド
    #---------------------------------------------------------------------------

    def get_nowplayingpaths(self):
        """wslファイルを読み込んで、
        現在プレイ中のシナリオパスの集合を返す。
        """
        seq = []

        for dpath in (self.yadodir, self.tempdir):
            dpath = cw.util.join_paths(dpath, u"Party")

            if os.path.isdir(dpath):
                for name in os.listdir(dpath):
                    path = cw.util.join_paths(dpath, name)

                    if name.endswith(".wsl") and os.path.isfile(path)\
                                        and not path in self.deletedpaths:
                        e = cw.util.get_elementfromzip(path, "ScenarioLog.xml",
                                                                    "Property")
                        path = e.gettext("WsnPath")
                        seq.append(path)

        return set(seq)

    def get_partypaths(self):
        """パーティーのxmlファイルのpathリストを返す。"""
        seq = []
        dpath = cw.util.join_paths(self.yadodir, "Party")

        for fname in os.listdir(dpath):
            fpath = cw.util.join_paths(dpath, fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                seq.append(fpath)

        return seq

    def get_storehousepaths(self):
        """BeastCard, ItemCard, SkillCardのディレクトリにあるカードの
        xmlのpathリストを返す。
        """
        seq = []

        for dname in ("BeastCard", "ItemCard", "SkillCard"):
            for fname in os.listdir(cw.util.join_paths(self.yadodir, dname)):
                fpath = cw.util.join_paths(self.yadodir, dname, fname)

                if os.path.isfile(fpath) and fname.endswith(".xml"):
                    seq.append(fpath)

        return seq

    def get_standbypaths(self):
        """パーティーに所属していない待機中冒険者のxmlのpathリストを返す。"""
        seq = []

        for header in self.partys:
            paths = header.get_memberpaths()
            seq.extend(paths)

        members = set(seq)
        seq = []

        for fname in os.listdir(cw.util.join_paths(self.yadodir, "Adventurer")):
            fpath = cw.util.join_paths(self.yadodir, "Adventurer", fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                if not fpath in members:
                    seq.append(fpath)

        return seq

    def get_albumpaths(self):
        """アルバムにある冒険者のxmlのpathリストを返す。"""
        seq = []

        for fname in os.listdir(cw.util.join_paths(self.yadodir, "Album")):
            fpath = cw.util.join_paths(self.yadodir, "Album", fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                seq.append(fpath)

        return seq

class Party(object):
    def __init__(self, path, partyinfoonly=True):
        # True時は、エリア移動中にPlayerCardスプライトを新規作成する
        self._loading = True
        # パーティデータ(CWPyElementTree)
        self.data = yadoxml2etree(path)
        # パーティ名
        self.name = self.data.gettext("Property/Name")
        # パーティ所持金
        self.money = self.data.getint("Property/Money", 0)

        self.partyinfoonly = partyinfoonly
        if not partyinfoonly:
            self.members = []
            self.backpack = []
        else:
            # 選択中パーティのメンバー(CWPyElementTree)
            paths = self.get_memberpaths()
            self.members = [yadoxml2etree(path) for path in paths]
            # 選択中のパーティの荷物袋(CardHeader)
            self.backpack = []
            for e in self.data.getfind("Backpack"):
                header = cw.header.CardHeader(carddata=e, owner="BACKPACK")
                self.backpack.append(header)

    def is_loading(self):
        """membersのデータを元にPlayerCardインスタンスを
        生成していなかったら、Trueを返す。
        """
        return self._loading

    def reload(self):
        self.__init__(self.data.fpath)

    def add(self, header, data=None):
        """
        メンバーを追加する。引数はAdventurerHeader。
        """
        pcardsnum = len(self.members)

        # パーティ人数が6人だったら処理中断
        if pcardsnum >= 6:
            return

        s = os.path.basename(header.fpath)
        s = os.path.splitext(s)[0]
        e = self.data.make_element("Member", s)
        self.data.append("/Property/Members", e)
        if not data:
            data = yadoxml2etree(header.fpath)
        self.members.append(data)
        pos = (9 + 95 * pcardsnum + 9 * pcardsnum, 285)
        pcard = cw.sprite.card.PlayerCard(data, pos, status="deal")
        cw.animation.animate_sprite(pcard, "deal")
        self.set_numbercoupon()

    def remove(self, pcard):
        """
        メンバーを削除する。引数はPlayerCard。
        """
        pcard.remove_numbercoupon()
        self.members.remove(pcard.data)
        cw.cwpy.pcardgrp.remove(pcard)
        self.data.getfind("/Property/Members").clear()

        for index, pcard in enumerate(cw.cwpy.get_pcards()):
            s = os.path.basename(pcard.data.fpath)
            s = os.path.splitext(s)[0]
            e = self.data.make_element("Member", s)
            self.data.append("/Property/Members", e)

        self.set_numbercoupon()

    def set_name(self, name):
        """
        パーティ名を変更する。
        """
        if not self.name == name:
            cw.cwpy.ydata.deletedpaths.add(self.data.fpath)
            self.name = name
            self.data.edit("/Property/Name", name)
            fname = cw.util.repl_dischar(name) + ".xml"
            path = cw.util.join_paths(cw.cwpy.ydata.tempdir, "Party", fname)
            path = cw.util.dupcheck_plus(path)
            self.data.write(path)
            if self is cw.cwpy.ydata.party:
                self.data = yadoxml2etree(path)
                pname = os.path.basename(path)
                pname = os.path.splitext(pname)[0]
                cw.cwpy.ydata.environment.edit("/Property/NowSelectingParty", pname)

    def set_money(self, value):
        """
        パーティの所持金を変更する。
        """
        self.money += value
        self.money = cw.util.numwrap(self.money, 0, 9999999)
        self.data.edit("/Property/Money", str(self.money))
        cw.cwpy.has_inputevent = True

    def set_numbercoupon(self):
        """
        番号クーポンを配布する。
        """
        names = [cw.cwpy.msgs["number_1_coupon"], u"＿２", u"＿３", u"＿４", u"＿５", u"＿６"]

        for index, pcard in enumerate(cw.cwpy.get_pcards()):
            pcard.remove_numbercoupon()
            pcard.set_coupon(names[index], 0)

    def write(self):
        self.data.write_xml()

        for member in self.members:
            member.write_xml()

    def lost(self):
        for pcard in cw.cwpy.get_pcards():
            pcard.lost()

        cw.cwpy.remove_xml(self)

    def get_coupons(self):
        """
        パーティ全体が所持しているクーポンをセット型で返す。
        """
        seq = []

        for member in self.members:
            for e in member.getfind("/Property/Coupons"):
                seq.append(e.text)

        return set(seq)

    def get_allcardheaders(self):
        seq = []
        seq.extend(self.backpack)

        for pcard in cw.cwpy.get_pcards():
            for headers in pcard.cardpocket:
                seq.extend(headers)

        return seq

    def is_adventuring(self):
        path = os.path.splitext(self.data.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def remove_adventuring(self):
        path = os.path.splitext(self.data.fpath)[0] + ".wsl"
        cw.cwpy.ydata.deletedpaths.add(path)

    def get_sceheader(self):
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        path = os.path.splitext(self.data.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path:
            e = cw.util.get_elementfromzip(path, "ScenarioLog.xml", "Property")
            path = e.gettext("WsnPath", "")
            db = cw.scenariodb.Scenariodb()
            sceheader = db.search_path(path)
            db.close()
            return sceheader
        else:
            return None

    def get_memberpaths(self):
        """
        現在選択中のパーティのメンバーのxmlのpathリストを返す。
        """
        seq = []

        for e in self.data.getfind("/Property/Members"):
            if e.text:
                path = cw.util.join_yadodir(cw.util.join_paths("Adventurer",  e.text + ".xml"))
                if not os.path.isfile(path):
                    # Windowsがファイル名を変えるため前後のスペースを除く
                    path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", e.text.strip() + ".xml"))

                seq.append(path)

        return seq

    def get_backpackpaths(self):
        """
        現在選択中のパーティの荷物袋にあるカードのxmlのpathリストを返す。
        """
        elements = self.data.find("Backpack").getchildren()
        seq = [cw.util.join_paths(cw.cwpy.yadodir,
                                            e.tag, e.text + ".xml")
                                                    for e in elements if e.text]
        return seq

#-------------------------------------------------------------------------------
#  CWPyElement
#-------------------------------------------------------------------------------

class _CWPyElementInterface(object):
    def _raiseerror(self, path, attr=""):
        if hasattr(self, "tag"):
            tag = self.tag + "/" + path
        elif hasattr(self, "getroot"):
            tag = self.getroot().tag + "/" + path
        else:
            tag = path

        s = 'Invalid XML! (file="%s", tag="%s", attr="%s")'
        s = s % (self.fpath, tag, attr)
        raise ValueError(s.encode("utf-8"))

    def find2(self, path):
        """
        ElementTreeの仕様変更に対応するためのラッパメソッド。
        """
        if path == "":
            return self
        elif path.startswith("/"):
            return self.getroot().find(path[1:])
        else:
            return self.find(path)

    def hasfind(self, path, attr=""):
        e = self.find2(path)

        if attr:
            return bool(e is not None and attr in e.attrib)
        else:
            return bool(e is not None)

    def getfind(self, path, raiseerror=True):
        e = self.find2(path)

        if e is None:
            if raiseerror:
                self._raiseerror(path)
            return []

        return e

    def gettext(self, path, default=None):
        e = self.find2(path)

        if e is None:
            text = default
        else:
            text = e.text or default

        if text is None:
            self._raiseerror(path)

        return text

    def getattr(self, path, attr, default=None):
        e = self.find2(path)

        if e is None:
            text = default
        else:
            text = e.get(attr, default)

        if text is None:
            self._raiseerror(path, attr)

        return text

    def getbool(self, path, attr=None, default=None):
        if isinstance(attr, bool):
            default = attr
            attr = ""
            s = self.gettext(path, default)
        elif attr:
            s = self.getattr(path, attr, default)
        else:
            s = self.gettext(path, default)

        try:
            return cw.util.str2bool(s)
        except:
            self._raiseerror(path, attr)

    def getint(self, path, attr=None, default=None):
        if isinstance(attr, int):
            default = attr
            attr = ""
            s = self.gettext(path, default)
        elif attr:
            s = self.getattr(path, attr, default)
        else:
            s = self.gettext(path, default)

        try:
            return int(float(s))
        except:
            self._raiseerror(path, attr)

    def getfloat(self, path, attr=None, default=None):
        if isinstance(attr, float):
            default = attr
            attr = ""
            s = self.gettext(path, default)
        elif attr:
            s = self.getattr(path, attr, default)
        else:
            s = self.gettext(path, default)

        try:
            return float(s)
        except:
            self._raiseerror(path, attr)

    def make_element(self, *args, **kwargs):
        return make_element(*args, **kwargs)

class CWPyElement(_ElementInterface, _CWPyElementInterface):
    pass

#-------------------------------------------------------------------------------
#  CWPyElementTree
#-------------------------------------------------------------------------------

class CWPyElementTree(ElementTree, _CWPyElementInterface):
    def __init__(self, fpath="", element=None):
        if element is None:
            element = xml2element(fpath)

        ElementTree.__init__(self, element=element)
        self.fpath = element.fpath if hasattr(element, "fpath") else ""
        self.is_edited = False

    def write(self, path=""):
        if not path:
            path = self.fpath

        # インデント整形
        self.form_element(self.getroot())
        # 書き込み
        dpath = os.path.dirname(path)

        if dpath and not os.path.isdir(dpath):
            os.makedirs(dpath)

        f = open(path, "wb")
        f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        ElementTree.write(self, f, "utf-8")
        f.close()

    def write_xml(self, nocheck_edited=False):
        """エレメントが編集されていたら、
        "Data/Temp/Yado"にxmlファイルを保存。
        """
        if self.is_edited or nocheck_edited:
            if not self.fpath.startswith(cw.cwpy.tempdir):
                fpath = self.fpath.replace(cw.cwpy.yadodir,
                                                        cw.cwpy.tempdir, 1)
                self.fpath = fpath

            self.write(self.fpath)
            self.is_edited = False

    def edit(self, path, value, attrname=None):
        """パスのエレメントを編集。"""
        if not isinstance(value, (str, unicode)):
            try:
                value = str(value)
            except:
                t = (self.fpath, path, value, attr)
                print u"エレメント編集失敗 (%s, %s, %s, %s)" % t
                return

        if attrname:
            self.find2(path).set(attrname, value)
        else:
            self.find2(path).text = value

        self.is_edited = True

    def append(self, path, element):
        self.find2(path).append(element)
        self.is_edited = True

    def insert(self, path, element, index):
        """パスのエレメントの指定位置にelementを挿入。
        indexがNoneの場合はappend()の挙動。
        """
        self.find2(path).insert(index, element)
        self.is_edited = True

    def remove(self, path, element):
        """パスのエレメントからelementを削除した後、
        CWPyElementTreeのインスタンスで返す。
        """
        self.find2(path).remove(element)
        self.is_edited = True

    def form_element(self, element, depth=0):
        """elementのインデントを整形"""
        i = "\n" + " " * depth

        if len(element):
            if not element.text or not element.text.strip():
                element.text = i + " "

            if not element.tail or not element.tail.strip():
                element.tail = i if depth else None

            for element in element:
                self.form_element(element, depth + 1)

            if not element.tail or not element.tail.strip():
                element.tail = i

        else:
            if not element.text:
                element.text = None

            if not element.tail or not element.tail.strip():
                element.tail = i if depth else None

#-------------------------------------------------------------------------------
# xmlパーサ
#-------------------------------------------------------------------------------

def make_element(name, text="", attrs={}, tail=""):
    element = CWPyElement(name, attrs)
    element.text = text
    element.tail = tail
    return element

def yadoxml2etree(path, tag=""):
    element = yadoxml2element(path, tag)
    return CWPyElementTree(element=element)

def yadoxml2element(path, tag=""):
    if path.startswith("Yado"):
        temppath = path.replace("Yado", "Data/Temp/Yado", 1)
    elif path.startswith("Data/Temp/Yado"):
        temppath = path
        path = path.replace("Data/Temp/Yado", "Yado", 1)
    else:
        raise ValueError("%s is not YadoXMLFile." % path)

    if os.path.isfile(temppath):
        return xml2element(temppath, tag)
    elif os.path.isfile(path):
        return xml2element(path, tag)
    else:
        raise ValueError("%s is not found." % path)

def xml2etree(path="", tag="", file=None, element=None, nocache=False):
    if element is None:
        element = xml2element(path, tag, file, nocache=nocache)

    return CWPyElementTree(element=element)

def xml2element(path="", tag="", file=None, nocache=False):
    usecache = path and cw.cwpy and cw.cwpy.sdata and\
               isinstance(cw.cwpy.sdata, cw.data.ScenarioData) and\
               path.startswith(cw.cwpy.sdata.tempdir)
    if usecache:
        mtime = os.path.getmtime(path)
    if usecache and path in cw.cwpy.sdata.cache:
        cachedata = cw.cwpy.sdata.cache[path]
        if cachedata.mtime <= mtime and cachedata.tag == tag:
            if nocache:
                return copy.deepcopy(cachedata.data)
            return cachedata.data

    if not file and cw.cwpy and cw.cwpy.classicdata:
        # クラシックなシナリオのファイルだった場合は変換する
        lpath = path.lower()
        if lpath.endswith(".wsm") or lpath.endswith(".wid"):
            cdata = cw.cwpy.classicdata.load_file(path)
            xml = cdata.get_xmltext(0)
            file = StringIO.StringIO(xml)

    parser = SimpleXmlParser(path, tag, file)
    data = parser.parse()
    if usecache:
        cachedata = CacheData(data, tag, mtime)
        cw.cwpy.sdata.cache[path] = cachedata
        if nocache:
            data = copy.deepcopy(data)
    return data

class CacheData(object):
    def __init__(self, data, tag, mtime):
        self.data = data
        self.tag = tag
        self.mtime = mtime

class SimpleXmlParser(object):
    def __init__(self, fpath, targettag="", file=None):
        """
        targettag: 読み込むタグのロケーションパス。絶対パスは使えない。
            "Property/Name"という風にタグごとに"/"で区切って指定する。
            targettagが空の場合は、全てのデータを読み込む。
        """
        self.root = None
        self.node_stack = []
        self.fpath = fpath.replace("\\", "/")
        self.file = file
        self.targettag = targettag.strip("/")
        self.parsetags = []
        self.currenttags = []
        self._persed = False

    def start_element(self, name, attrs):
        """要素の開始。"""
        self.currenttags.append(name)

        if not self._persed and self.get_currentpath() == self.targettag:
            self.parsetags.append(name)

        if self.parsetags:
            element = CWPyElement(name, attrs)
            element.fpath = self.fpath

            if self.node_stack:
                parent = self.node_stack[-1]
                parent.append(element)
            else:
                element.attrib = attrs
                self.root = element

            self.node_stack.append(element)

    def end_element(self, name):
        """要素の終了。"""
        if self.parsetags:
            self.node_stack.pop(-1)

        if not self._persed and self.get_currentpath() == self.targettag:
            self.parsetags.pop(-1)

            if not self.parsetags:
                self._persed = True

        self.currenttags.pop(-1)

    def char_data(self, data):
        """文字データ"""
        if self.parsetags:
            if data.strip():
                element = self.node_stack[-1]

                if element.text:
                    element.text += data
                else:
                    element.text = data

    def parse(self):
        if hasattr(self.file, "read"):
            self.parse_file(self.file)
        else:
            f = open(self.fpath, "rb")
            self.parse_file(f)
            f.close()

        return self.root

    def parse_file(self, file):
        try:
            self._parse_file(file)
        except xml.parsers.expat.ExpatError, err:
            # エラーになったファイルのパスを付け加える
            s = u". file: " + self.fpath
            err.args = (err.args[0] + s.encode(u"utf-8"), )
            raise err

    def _parse_file(self, file):
        parser = xml.parsers.expat.ParserCreate()
        parser.buffer_text = 1
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.char_data

        fdata = file.read()
        parser.Parse(fdata, 1)

    def get_currentpath(self):
        if len(self.currenttags) > 1:
            return "/".join(self.currenttags[1:])
        else:
            return ""

def main():
    pass

if __name__ == "__main__":
    main()
