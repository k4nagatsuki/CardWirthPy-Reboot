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
from xml.etree.cElementTree import ElementTree
from xml.etree.ElementTree import _ElementInterface

import pygame

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
        self.data = None
        self.name = ""
        self.author = ""
        self.tempdir = ""
        self.scedir = ""
        self._init_xmlpaths()
        self._init_sparea_mcards()
        self.events = None
        self.deletedpaths = set()
        self.lostadventurers = set()
        self.gossips = {}
        self.compstamps = {}
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

        for key, value in self.areas.iteritems():
            if key in cw.AREAS_TRADE:
                mcards = cw.cwpy.set_mcards(self.get_mcarddata(key, battlestatus=False), False, addgroup=False, setautospread=False)
                d[key] = mcards

        self.sparea_mcards = d

    def get_versionhint(self, frompos=0):
        """現在有効になっている互換性マークを返す(常に無し)。"""
        return ""

    def update_scale(self):
        for key, mcards in self.sparea_mcards.iteritems():
            for mcard in mcards:
                mcard.update_scale()

    def start(self):
        pass

    def end(self):
        pass

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
            musicpath = self.load_log("Data/Temp/ScenarioLog/ScenarioLog.xml", False)
            return True, musicpath
        else:
            self.create_log()
            return False, None

    def remove_log(self):
        cw.util.remove("Data/Temp/ScenarioLog")
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        cw.cwpy.ydata.deletedpaths.add(path)

    def load_log(self, path, recording):
        etree = xml2etree(path)

        for e in etree.getfind("Gossips"):
            if e.get("value") == "True":
                self.gossips[e.text] = True
            elif e.get("value") == "False":
                self.gossips[e.text] = False

        for e in etree.getfind("CompleteStamps"):
            if e.get("value") == "True":
                self.compstamps[e.text] = True
            elif e.get("value") == "False":
                self.compstamps[e.text] = False

    def change_data(self, id):
        if cw.cwpy.is_battlestatus():
            path = self.battles[id][1]
        else:
            path = self.areas[id][1]

        self.data = xml2etree(path)
        if isinstance(self, ScenarioData):
            self.versionhint[cw.HINT_AREA] = self.data.getattr("Property", "versionHint", "")
        cw.cwpy.event.refresh_areaname()
        self.events = cw.event.EventEngine(self.data.getfind("Events"))

    def start_event(self, keynum=None, keycodes=[]):
        cw.cwpy.statusbar.change(False)
        self.events.start(keynum=keynum, keycodes=keycodes)
        if not cw.cwpy.is_dealing() and not cw.cwpy.battle:
            cw.cwpy.statusbar.change()
            cw.cwpy.disposition_pcards()
            if not (pygame.event.peek(pygame.locals.USEREVENT)):
                cw.cwpy.show_party()

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

    def get_mcarddata(self, id=None, battlestatus=None):
        """spreadtypeの値("Custom", "Auto")と
        メニューカードのElementのリストをタプルで返す。
        id: 取得対象のエリア。不指定の場合は現在のエリア。
        """
        if not isinstance(battlestatus, bool):
            battlestatus = cw.cwpy.is_battlestatus()

        if id is None:
            data = self.data
        elif battlestatus:
            path = self.battles[id][1]
            data = xml2etree(path)
        else:
            path = self.areas[id][1]
            data = xml2etree(path)

        e = data.find("MenuCards")
        if e is None:
            e = data.find("EnemyCards")

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
        self.data = None
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
        # メッセージのバックログ
        self.backlog = []

        # 各段階の互換性マーク
        self.versionhint = [
            "", # メッセージ表示時の話者(キャストまたはカード)
            "", # 使用中のカード
            "", # エリア・バトル・パッケージ
            "", # シナリオ本体
        ]

        if cw.cwpy.classicdata:
            self.versionhint[cw.HINT_SCENARIO] = cw.cwpy.classicdata.versionhint

    def get_versionhint(self, frompos=0):
        """現在有効になっている互換性マークを返す。"""
        for hint in self.versionhint[frompos:]:
            if hint:
                return hint
        return ""

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
                    image = cw.s(cw.util.load_image(path, True))
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
                    wdata, filedata = cw.cwpy.classicdata.load_file(path, nameonly=True)
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

    def update_scale(self):
        # 特殊文字の画像パスの集合(正規表現)
        SystemData.update_scale(self)

        r_specialchar = re.compile(r"font_(.)[.].*$")
        for dpath, dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                # "font_*.*"のファイルパスの画像を特殊文字に指定
                if r_specialchar.match(fname.lower()):
                    m = r_specialchar.match(fname.lower())
                    path = cw.util.join_paths(dpath, fname)
                    image = cw.s(cw.util.load_image(path, True))
                    name = "#%s" % (m.group(1))
                    cw.cwpy.rsrc.specialchars[name] = (image, True)
                    cw.cwpy.rsrc.specialchars_is_changed = True

    def _init_flags(self):
        """
        summary.xmlで定義されているフラグを初期化。
        """
        self.flags = {}

        for e in self.summary.getfind("Flags"):
            value = e.getbool(".", "default")
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
            value = e.getint(".", "default")
            name = e.gettext("Name", "")
            valuenames = [e.gettext("Value" + str(n), "") for n in xrange(10)]
            self.steps[name] = Step(value, name, valuenames)

    def reset_variables(self):
        """すべての状態変数を初期化する。"""
        for e in self.summary.find("Steps"):
            value = e.getint(".", "default")
            name = e.gettext("Name", "")
            self.steps[name].set(value)

        for e in self.summary.getfind("Flags"):
            value = e.getbool(".", "default")
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

        cw.cwpy.ydata.party.set_lastscenario([])

        # ロストした冒険者を削除
        for path in self.lostadventurers:
            if not path.lower().startswith("yado"):
                path = cw.util.join_yadodir(path)
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

            # 移動済みの荷物袋カードを削除
            for header in cw.cwpy.ydata.party.backpack_moved:
                if header.moved == 2:
                    # 素材も含めて完全削除
                    cw.cwpy.remove_xml(header)
                else:
                    # どこかで所有しているので素材は消さない
                    header.contain_xml()

    def f9(self):
        """
        シナリオ強制終了。俗に言うファッ○ユー。
        """
        self._playing = False
        cw.cwpy.exec_func(cw.cwpy.f9)

    def create_log(self):
        # log
        cw.xmlcreater.create_scenariolog(self, "Data/Temp/ScenarioLog/ScenarioLog.xml", False)
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

        # 荷物袋内のカード群(ファイルパスのみ)
        element = cw.data.make_element("BackpackFiles")
        yadodir = cw.cwpy.ydata.party.get_yadodir()
        tempdir = cw.cwpy.ydata.party.get_tempdir()
        for header in cw.cwpy.ydata.party.backpack:
            if header.fpath.lower().startswith("yado"):
                fpath = os.path.relpath(header.fpath, yadodir)
            else:
                fpath = os.path.relpath(header.fpath, tempdir)
            fpath = cw.util.join_paths(fpath)
            element.append(cw.data.make_element("File", fpath))
        path = "Data/Temp/ScenarioLog/Backpack.xml"
        etree = cw.data.xml2etree(element=element)
        etree.write(path)

        # create_zip
        path = os.path.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith(cw.cwpy.yadodir):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip("Data/Temp/ScenarioLog", path)
        cw.cwpy.ydata.deletedpaths.discard(path)

    def load_log(self, path, recording):
        etree = xml2etree(path)
        if not recording:
            cw.cwpy.debug = etree.getbool("Property/Debug")

            if not cw.cwpy.debug == cw.cwpy.setting.debug:
                cw.cwpy.statusbar.change()

                if not cw.cwpy.debug and cw.cwpy.is_showingdebugger():
                    cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)

        for e in etree.getfind("Flags"):
            if e.text in self.flags:
                self.flags[e.text].value = e.getbool(".", "value")

        for e in etree.getfind("Steps"):
            if e.text in self.steps:
                self.steps[e.text].value = e.getint(".", "value")

        if not recording:
            for e in etree.getfind("Gossips"):
                if e.get("value") == "True":
                    self.gossips[e.text] = True
                elif e.get("value") == "False":
                    self.gossips[e.text] = False

            for e in etree.getfind("CompleteStamps"):
                if e.get("value") == "True":
                    self.compstamps[e.text] = True
                elif e.get("value") == "False":
                    self.compstamps[e.text] = False

        self.infocards = []
        for e in etree.getfind("InfoCards"):
            if int(e.text) in self.infos:
                path = self.infos[int(e.text)][1]
                e = xml2element(path, "Property")
                header = cw.header.InfoCardHeader(e)
                self.infocards.append(header)

        self.friendcards = []
        for e in etree.getfind("CastCards"):
            if e.tag == "FriendCard":
                # IDのみ。変換直後の宿でこの状態になる
                fcard = cw.sprite.card.FriendCard(castid=int(e.text))
                self.friendcards.append(fcard)
            else:
                data = xml2etree(element=e)
                fcard = cw.sprite.card.FriendCard(data=data)
                self.friendcards.append(fcard)

        if not recording:
            for e in etree.getfind("DeletedFiles"):
                self.deletedpaths.add(e.text)

            for e in etree.getfind("LostAdventurers"):
                self.lostadventurers.add(e.text)

        e = etree.getfind("BgImages")
        elements = cw.cwpy.sdata.get_bgdata(e)
        ttype = ("Default", "Default")
        cw.cwpy.background.load(elements, False, False, ttype)
        self.startid = cw.cwpy.areaid = etree.getint("Property/AreaId")
        return etree.gettext("Property/MusicPath", "")

    def update_log(self):
        cw.xmlcreater.create_scenariolog(self, "Data/Temp/ScenarioLog/ScenarioLog.xml", False)
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
        if self.value <> value:
            cw.cwpy.ydata.changed()
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
        if self.value <> value:
            cw.cwpy.ydata.changed()
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

    def add(self, path, forceyado=False):
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        if not forceyado and cw.cwpy.is_playingscenario():
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
    def __init__(self, yadodir, tempdir, loadparty=True):
        # 宿データのあるディレクトリ
        self.yadodir = yadodir
        self.tempdir = tempdir

        if not os.path.isdir(self.tempdir):
            os.makedirs(self.tempdir)

        # セーブが必要な状況であればTrue
        self._changed = False

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

        dataversion = self.environment.getattr(".", "dataVersion", 0)
        if dataversion < 1:
            self.update_version()
            self.environment.edit(".", "1", "dataVersion")
            self.environment.write()

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
        self.sort_standbys()

        # アルバム(AdventurerHeader)
        self.album = self.yadodb.get_album()

        # カード置場(CardHeader)
        self.storehouse = self.yadodb.get_cards()
        self.sort_storehouse()

        self.yadodb.close()

        # 現在選択中のパーティをセット
        if loadparty:
            self.party = None
            pname = self.environment.gettext("Property/NowSelectingParty", "")

            if pname:
                path = cw.util.join_paths(self.yadodir, pname)
                seq = [header for header in self.partys if path == header.fpath]

                if seq:
                    self.load_party(seq[0])
                else:
                    self.load_party(None)

            else:
                self.load_party(None)

    def update_version(self):
        """古いバージョンの宿データであれば更新する。
        """
        nowparty = self.environment.gettext("Property/NowSelectingParty", "")
        ppath = cw.util.join_paths(self.yadodir, "Party")
        for fpath in os.listdir(ppath):
            fpath = cw.util.join_paths(ppath, fpath)
            if os.path.isdir(fpath) or not fpath.lower().endswith(".xml"):
                continue

            # パーティデータが1つのファイルであれば
            # ディレクトリ方式に変換する

            # 変換後のディレクトリ
            dpath = os.path.splitext(fpath)[0]
            dpath = cw.binary.util.check_duplicate(dpath)
            os.makedirs(dpath)

            if nowparty == os.path.splitext(os.path.basename(fpath))[0]:
                pname = cw.util.join_paths("Party", os.path.basename(dpath), "Party.xml")
                self.environment.edit("Property/NowSelectingParty", pname)

            # データベース
            carddb = cw.yadodb.YadoDB(dpath, cw.yadodb.PARTY)
            order = 0

            # シナリオログ
            wslpath = os.path.splitext(fpath)[0] + ".wsl"
            haswsl = os.path.isfile(wslpath)
            if haswsl:
                cw.util.decompress_zip(wslpath, "Data/Temp", "ScenarioLog")

                # 荷物袋内のカード群(ファイルパスのみ)
                files = cw.data.make_element("BackpackFiles")
                party = xml2etree(cw.util.join_paths("Data/Temp/ScenarioLog/Party", os.path.basename(fpath)))
                for e in party.getfind("Backpack"):
                    # まだ所持しているカードとシナリオ内で
                    # 失われたカードを判別できないので、
                    # ログの荷物袋のカードは一旦全て削除済みと
                    # マークしておき、現行の荷物袋のカードは
                    # 新規入手状態にする
                    carddata = CWPyElementTree(element=e)
                    name = carddata.gettext("Property/Name", "")
                    carddata.edit("Property", "2", "moved")
                    carddata.fpath = cw.binary.util.check_filename(name + ".xml")
                    carddata.fpath = cw.util.join_paths(dpath, e.tag, carddata.fpath)
                    carddata.fpath = cw.binary.util.check_duplicate(carddata.fpath)
                    carddata.write(path=carddata.fpath)

                    header = cw.header.CardHeader(carddata=e)
                    header.fpath = carddata.fpath
                    carddb.insert_cardheader(header, commit=False, cardorder=order)
                    order += 1

                    path = os.path.relpath(carddata.fpath, dpath)
                    path = cw.util.join_paths(path)
                    files.append(cw.data.make_element("File", path))

                # 新フォーマットの荷物袋ログ
                path = "Data/Temp/ScenarioLog/Backpack.xml"
                etree = CWPyElementTree(element=files)
                etree.write(path)

                party.getroot().remove(party.find("Backpack"))
                party.write()
                shutil.move(party.fpath, "Data/Temp/ScenarioLog/Party/Party.xml")

                wslpath2 = cw.util.join_paths(dpath, "Party.wsl")
                cw.util.compress_zip("Data/Temp/ScenarioLog", wslpath2)
                shutil.rmtree("Data/Temp/ScenarioLog")

            # 現状のパーティデータ
            data = xml2etree(fpath)
            # Backpack要素を分解してディレクトリに保存
            for e in data.getfind("Backpack"):
                carddata = CWPyElementTree(element=e)
                name = carddata.gettext("Property/Name", "")
                carddata.fpath = cw.binary.util.check_filename(name + ".xml")
                carddata.fpath = cw.util.join_paths(dpath, e.tag, carddata.fpath)
                carddata.fpath = cw.binary.util.check_duplicate(carddata.fpath)

                header = cw.header.CardHeader(carddata=e)

                if haswsl and not carddata.getbool(".", "scenariocard", False):
                    # シナリオログ側のコメントを参照
                    carddata.edit(".", "True", "scenariocard")
                    header.scenariocard = True

                    # 元々scenariocardでない場合は
                    # ImagePathの指す先をバイナリ化しておく
                    for e2 in carddata.getiterator():
                        if e2.tag == "ImagePath" and e2.text and not cw.binary.image.path_is_code(e2.text):
                            path = cw.util.join_paths(self.yadodir, e2.text)
                            if os.path.isfile(path):
                                with open(path, "rb") as f:
                                    imagedata = f.read()
                                e2.text = cw.binary.image.data_to_code(imagedata)
                                header.imgpath = e2.text

                carddata.write(path=carddata.fpath)

                header.fpath = carddata.fpath
                carddb.insert_cardheader(header, commit=False, cardorder=order)
                order += 1

            carddb.commit()
            carddb.close()

            # パーティの基本データを書き込み
            data.remove(".", data.find("Backpack"))
            data.write(path=cw.util.join_paths(dpath, "Party.xml"))

            # 旧データを除去
            if haswsl:
                os.remove(wslpath)
            os.remove(fpath)

    def changed(self):
        """データの変化を通知する。"""
        self._changed = True

    def is_changed(self):
        return self._changed

    def load_party(self, header=None):
        """
        header: PartyHeader
        引数のパーティー名のデータを読み込む。
        パーティー名がNoneの場合はパーティーデータは空になる
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # パーティデータが変更されている場合はxmlをTempに吐き出す
        if self.party:
            self.party.write()
            if self.party.members:
                self.add_party(self.party)

        if header:
            self.party = Party(header)
            if self.party.lastscenario:
                cw.cwpy.setting.lastscenario = self.party.lastscenario
            if header.fpath.lower().startswith("yado"):
                name = os.path.relpath(header.fpath, self.yadodir)
            else:
                name = os.path.relpath(header.fpath, self.tempdir)
            name = cw.util.join_paths(name)
            self.environment.edit("Property/NowSelectingParty", name)

            if header in self.partys:
                self.partys.remove(header)

        else:
            self.party = None
            self.environment.edit("Property/NowSelectingParty", "")

    def add_standbys(self, path, sort=True):
        cw.cwpy.ydata.changed()
        header = self.create_advheader(path)
        header.order = cw.util.new_order(self.standbys)
        self.standbys.append(header)
        if sort:
            self.sort_standbys()
        return header

    def add_album(self, path):
        cw.cwpy.ydata.changed()
        header = self.create_advheader(path, True)
        self.album.append(header)
        cw.util.sort_by_attr(self.album, "name")
        return header

    def add_party(self, party):
        cw.cwpy.ydata.changed()
        fpath = party.path
        header = self.create_partyheader(fpath)
        header.data = party # 保存時まで記憶しておく
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
            element = xml2element(path, "Property")

        return cw.header.PartyHeader(element)

    def create_party(self, header, chgarea=True):
        """新しくパーティを作る。
        header: AdventurerHeader
        """
        cw.cwpy.ydata.changed()
        path = cw.xmlcreater.create_party(header)
        header = self.create_partyheader(cw.util.join_paths(path, "Party.xml"))
        cw.cwpy.load_party(header, chgarea=chgarea)

    def sort_standbys(self):
        if cw.cwpy.setting.sort_standbys == "Level":
            cw.util.sort_by_attr(self.standbys, "level")
        elif cw.cwpy.setting.sort_standbys == "Name":
            cw.util.sort_by_attr(self.standbys, "name")
        else:
            cw.util.sort_by_attr(self.standbys, "order")

    def sort_storehouse(self):
        if cw.cwpy.setting.sort_storehouse == "Level":
            cw.util.sort_by_attr(self.storehouse, "level")
        elif cw.cwpy.setting.sort_storehouse == "Name":
            cw.util.sort_by_attr(self.storehouse, "name")
        elif cw.cwpy.setting.sort_storehouse == "Type":
            cw.util.sort_by_attr(self.storehouse, "type_id")
        elif cw.cwpy.setting.sort_storehouse == "Price":
            cw.util.sort_by_attr(self.storehouse, "price")
        else:
            cw.util.sort_by_attr(self.storehouse, "order")

    def save(self):
        """宿データをセーブする。"""
        # カード置場の順序を記憶しておく
        cardorder = {}
        for i, header in enumerate(self.storehouse):
            if header.fpath.lower().startswith("yado"):
                fpath = os.path.relpath(header.fpath, self.yadodir)
            else:
                fpath = os.path.relpath(header.fpath, self.tempdir)
            fpath = cw.util.join_paths(fpath)
            cardorder[fpath] = header.order
        # 宿帳の順序を記憶しておく
        adventurerorder = {}
        for i, header in enumerate(self.standbys):
            if header.fpath.lower().startswith("yado"):
                fpath = os.path.relpath(header.fpath, self.yadodir)
            else:
                fpath = os.path.relpath(header.fpath, self.tempdir)
            fpath = cw.util.join_paths(fpath)
            adventurerorder[fpath] = header.order

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

        # 各パーティの荷物袋のデータを保存する
        def update_backpack(party):
            # カード置場の順序を記憶しておく
            cardorder = {}
            ppath = os.path.dirname(party.path)
            yadodir = party.get_yadodir()
            tempdir = party.get_tempdir()
            for i, header in enumerate(party.backpack):
                if header.fpath.lower().startswith("yado"):
                    fpath = os.path.relpath(header.fpath, yadodir)
                else:
                    fpath = os.path.relpath(header.fpath, tempdir)
                    header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
                fpath = cw.util.join_paths(fpath)
                cardorder[fpath] = header.order
            carddb = cw.yadodb.YadoDB(ppath, mode=cw.yadodb.PARTY)
            carddb.update(cardorder=cardorder)
            carddb.close()
        if self.party:
            update_backpack(self.party)
        for party in self.partys:
            if party.data:
                update_backpack(party.data)
                party.data = None

        # カードデータベースを更新
        yadodb = cw.yadodb.YadoDB(self.yadodir)
        yadodb.update(cardorder=cardorder, adventurerorder=adventurerorder)
        yadodb.close()

        cw.cwpy.clear_selection()
        self._changed = False

    #---------------------------------------------------------------------------
    # ゴシップ・シナリオ終了印用メソッド
    #---------------------------------------------------------------------------

    def get_gossips(self):
        """ゴシップ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("Gossips") if e.text])

    def get_compstamps(self):
        """冒険済みシナリオ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("CompleteStamps") if e.text])

    def get_gossiplist(self):
        """ゴシップ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("Gossips") if e.text]

    def get_compstamplist(self):
        """冒険済みシナリオ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("CompleteStamps") if e.text]

    def has_compstamp(self, name):
        """冒険済みシナリオかどうかbool値で返す。
        name: シナリオ名。
        """
        for e in self.environment.getfind("CompleteStamps"):
            if e.text and e.text == name:
                return True

        return False

    def has_gossip(self, name):
        """ゴシップを所持しているかどうかbool値で返す。
        name: ゴシップ名
        """
        for e in self.environment.getfind("Gossips"):
            if e.text and e.text == name:
                return True

        return False

    def set_compstamp(self, name):
        """冒険済みシナリオ印をセットする。シナリオプレイ中に取得した
        シナリオ印はScenarioDataのリストに登録する。
        name: シナリオ名
        """
        if not self.has_compstamp(name):
            cw.cwpy.ydata.changed()
            e = make_element("CompleteStamp", name)
            self.environment.append("CompleteStamps", e)

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
            cw.cwpy.ydata.changed()
            e = make_element("Gossip", name)
            self.environment.append("Gossips", e)

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
        elements = [e for e in self.environment.getfind("CompleteStamps")
                                                            if e.text == name]

        for e in elements:
            cw.cwpy.ydata.changed()
            self.environment.remove("CompleteStamps", e)

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
        elements = [e for e in self.environment.getfind("Gossips")
                                                            if e.text == name]

        for e in elements:
            cw.cwpy.ydata.changed()
            self.environment.remove("Gossips", e)

        if cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.gossips.get(name) is True:
                cw.cwpy.sdata.gossips.pop(name)
            else:
                cw.cwpy.sdata.gossips[name] = False

    def clear_compstamps(self):
        """冒険済みシナリオ印を全て削除する。"""

        for e in self.environment.getfind("CompleteStamps"):
            cw.cwpy.ydata.changed()
            self.environment.remove("CompleteStamps", e)

            if cw.cwpy.is_playingscenario():
                name = e.text
                if cw.cwpy.sdata.compstamps.get(name) is True:
                    cw.cwpy.sdata.compstamps.pop(name)
                else:
                    cw.cwpy.sdata.compstamps[name] = False

    def clear_gossips(self):
        """ゴシップを全て削除する。"""

        for e in self.environment.getfind("Gossips"):
            cw.cwpy.ydata.changed()
            self.environment.remove("Gossips", e)

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
        if value <> 0:
            cw.cwpy.ydata.changed()
            self.money += value
            self.money = cw.util.numwrap(self.money, 0, 9999999)
            self.environment.edit("Property/Cashbox", str(self.money))
            cw.cwpy.has_inputevent = True

    #---------------------------------------------------------------------------
    # パーティ連れ込み
    #---------------------------------------------------------------------------

    def join_npcs(self):
        """
        シナリオのNPCを宿に連れ込む。
        """
        for fcard in cw.cwpy.get_fcards():
            cw.cwpy.ydata.changed()
            fcard.set_fullrecovery()

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
            for nature in cw.cwpy.setting.natures:
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
                for e in data.getfind("%ss" % (cardtype)):
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
            e = data.getfind("Property")
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
            self.add_standbys(path, sort=False)
        self.sort_standbys()

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
    def __init__(self, header, partyinfoonly=True):
        path = header.fpath

        # True時は、エリア移動中にPlayerCardスプライトを新規作成する
        self._loading = True

        self.members = []
        if not header.data:
            self.backpack = []
            self.backpack_moved = []
        self.path = path

        # パーティデータ(CWPyElementTree)
        self.data = yadoxml2etree(path)
        # パーティ名
        self.name = self.data.gettext("Property/Name")
        # パーティ所持金
        self.money = self.data.getint("Property/Money", 0)

        # 現在プレイ中のシナリオ
        self.lastscenario = []
        for e in self.data.getfind("Property/LastScenario", raiseerror=False):
            self.lastscenario.append(e.text)

        self.partyinfoonly = partyinfoonly
        if partyinfoonly:
            # 選択中パーティのメンバー(CWPyElementTree)
            paths = self.get_memberpaths()
            self.members = [yadoxml2etree(path) for path in paths]
            # 選択中のパーティの荷物袋(CardHeader)
            if header.data:
                # header.dataがある場合は保存前
                self.backpack = header.data.backpack
                self.backpack_moved = header.data.backpack_moved
            else:
                dpath = os.path.dirname(self.path)
                carddb = cw.yadodb.YadoDB(dpath, mode=cw.yadodb.PARTY)
                carddb.update()
                for header in carddb.get_cards():
                    if header.moved == 0:
                        self.backpack.append(header)
                    else:
                        self.backpack_moved.append(header)
                carddb.close()
            self.sort_backpack()

    def sort_backpack(self):
        if cw.cwpy.setting.sort_backpack == "Level":
            cw.util.sort_by_attr(self.backpack, "level")
        elif cw.cwpy.setting.sort_backpack == "Name":
            cw.util.sort_by_attr(self.backpack, "name")
        elif cw.cwpy.setting.sort_backpack == "Type":
            cw.util.sort_by_attr(self.backpack, "type_id")
        elif cw.cwpy.setting.sort_backpack == "Price":
            cw.util.sort_by_attr(self.backpack, "price")
        else:
            cw.util.sort_by_attr(self.backpack, "order")

    def get_backpackkeycodes(self, skill=True, item=True, beast=True):
        """荷物袋内のキーコード一覧を返す。"""
        s = set()
        for header in self.backpack:
            if not skill and header.type == "SkillCard":
                continue
            elif not item and header.type == "ItemCard":
                continue
            elif not beast and header.type == "BeastCard":
                continue
            s.update(header.keycodes)

        s.discard("")
        return s

    def has_keycode(self, keycode, skill=True, item=True, beast=True):
        """指定されたキーコードを所持しているか。"""
        for header in self.backpack:
            if not skill and header.type == "SkillCard":
                continue
            elif not item and header.type == "ItemCard":
                continue
            elif not beast and header.type == "BeastCard":
                continue

            if keycode in header.keycodes:
                return True

        return False

    def get_relpath(self):
        ppath = os.path.dirname(self.path)
        if ppath.lower().startswith("yado"):
            relpath = os.path.relpath(ppath, cw.cwpy.yadodir)
        else:
            relpath = os.path.relpath(ppath, cw.cwpy.tempdir)
        return cw.util.join_paths(relpath)

    def get_yadodir(self):
        return cw.util.join_paths(cw.cwpy.yadodir, self.get_relpath())

    def get_tempdir(self):
        return cw.util.join_paths(cw.cwpy.tempdir, self.get_relpath())

    def is_loading(self):
        """membersのデータを元にPlayerCardインスタンスを
        生成していなかったら、Trueを返す。
        """
        return self._loading

    def reload(self):
        cw.cwpy.ydata.changed()
        header = cw.header.PartyHeader(data=self.data.find("Property"))
        header.data = self
        self.__init__(header)

    def add(self, header, data=None):
        """
        メンバーを追加する。引数はAdventurerHeader。
        """
        pcardsnum = len(self.members)

        # パーティ人数が6人だったら処理中断
        if pcardsnum >= 6:
            return

        cw.cwpy.ydata.changed()
        s = os.path.basename(header.fpath)
        s = os.path.splitext(s)[0]
        e = self.data.make_element("Member", s)
        self.data.append("Property/Members", e)
        if not data:
            data = yadoxml2etree(header.fpath)
        self.members.append(data)
        pos_noscale = (9 + 95 * pcardsnum + 9 * pcardsnum, 285)
        pcard = cw.sprite.card.PlayerCard(data, pos_noscale=pos_noscale, status="deal")
        cw.animation.animate_sprite(pcard, "deal")

    def remove(self, pcard):
        """
        メンバーを削除する。引数はPlayerCard。
        """
        cw.cwpy.ydata.changed()
        pcard.remove_numbercoupon()
        self.members.remove(pcard.data)
        cw.cwpy.pcardgrp.remove(pcard)
        self.data.getfind("Property/Members").clear()

        for index, pcard in enumerate(cw.cwpy.get_pcards()):
            s = os.path.basename(pcard.data.fpath)
            s = os.path.splitext(s)[0]
            e = self.data.make_element("Member", s)
            self.data.append("Property/Members", e)

    def set_name(self, name):
        """
        パーティ名を変更する。
        """
        if not self.name == name:
            cw.cwpy.ydata.changed()
            self.name = name
            self.data.edit("Property/Name", name)

    def set_money(self, value):
        """
        パーティの所持金を変更する。
        """
        if value <> 0:
            cw.cwpy.ydata.changed()
            self.money += value
            self.money = cw.util.numwrap(self.money, 0, 9999999)
            self.data.edit("Property/Money", str(self.money))
            cw.cwpy.has_inputevent = True

    def set_numbercoupon(self):
        """
        番号クーポンを配布する。
        """
        names = [cw.cwpy.msgs["number_1_coupon"], u"＿２", u"＿３", u"＿４", u"＿５", u"＿６"]

        for index, pcard in enumerate(cw.cwpy.get_pcards()):
            pcard.remove_numbercoupon()
            pcard.set_coupon(names[index], 0)
            pcard.set_coupon(u"＠ＭＰ３", 0) # 1.29

    def remove_numbercoupon(self):
        """
        番号クーポンを除去する。
        """
        for pcard in cw.cwpy.get_pcards():
            pcard.remove_numbercoupon()

    def write(self):
        self.data.write_xml()

        for member in self.members:
            member.write_xml()

    def lost(self):
        cw.cwpy.ydata.changed()
        for pcard in cw.cwpy.get_pcards():
            pcard.lost()

        cw.cwpy.remove_xml(self)

    def get_coupontable(self):
        """
        パーティ全体が所持しているクーポンの
        所持数テーブルを返す。
        """
        d = {}

        for member in self.members:
            for e in member.getfind("Property/Coupons"):
                if e.text in d:
                    d[e.text] += 1
                else:
                    d[e.text] = 1

        return d

    def get_coupons(self):
        """
        パーティ全体が所持しているクーポンをセット型で返す。
        """
        seq = []

        for member in self.members:
            for e in member.getfind("Property/Coupons"):
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

        for e in self.data.getfind("Property/Members"):
            if e.text:
                path = cw.util.join_yadodir(cw.util.join_paths("Adventurer",  e.text + ".xml"))
                if not os.path.isfile(path):
                    # Windowsがファイル名を変えるため前後のスペースを除く
                    path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", e.text.strip() + ".xml"))

                seq.append(path)

        return seq

    def set_lastscenario(self, lastscenario):
        """
        プレイ中シナリオへの経路を記録する。
        """
        self.lastscenario = lastscenario
        e = self.data.find("Property/LastScenario")
        if e is None:
            e = make_element("LastScenario")
            self.data.append("Property", e)

        e.clear()
        for path in lastscenario:
            e.append(make_element("Path", path))

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

    def hasfind(self, path, attr=""):
        e = self.find(path)

        if attr:
            return bool(e is not None and attr in e.attrib)
        else:
            return bool(e is not None)

    def getfind(self, path, raiseerror=True):
        e = self.find(path)

        if e is None:
            if raiseerror:
                self._raiseerror(path)
            return []

        return e

    def gettext(self, path, default=None):
        e = self.find(path)

        if e is None:
            text = default
        else:
            text = e.text or default

        if text is None:
            self._raiseerror(path)

        return text

    def getattr(self, path, attr, default=None):
        e = self.find(path)

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

        with open(path, "wb") as f:
            f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
            ElementTree.write(self, f, "utf-8")

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
            self.find(path).set(attrname, value)
        else:
            self.find(path).text = value

        self.is_edited = True

    def append(self, path, element):
        self.find(path).append(element)
        self.is_edited = True

    def insert(self, path, element, index):
        """パスのエレメントの指定位置にelementを挿入。
        indexがNoneの場合はappend()の挙動。
        """
        self.find(path).insert(index, element)
        self.is_edited = True

    def remove(self, path, element=None, attrname=None):
        """パスのエレメントからelementを削除した後、
        CWPyElementTreeのインスタンスで返す。
        """
        if attrname:
            e = self.find(path)
            e.get(attrname) # 属性の辞書を生成させる
            del e.attrib[attrname]
        else:
            self.find(path).remove(element)
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

    # キャッシュからデータを取得
    if usecache and path in cw.cwpy.sdata.cache:
        cachedata = cw.cwpy.sdata.cache[path]
        if cachedata.mtime <= mtime:
            data = cachedata.data
            if tag:
                data = data.find(tag)
            if nocache:
                # 変更されてもよいデータを返す
                return copydata(data)
            return data

    data = None
    versionhint = ""
    if not file and cw.cwpy and cw.cwpy.classicdata:
        # クラシックなシナリオのファイルだった場合は変換する
        lpath = path.lower()
        if lpath.endswith(".wsm") or lpath.endswith(".wid"):
            cdata, filedata = cw.cwpy.classicdata.load_file(path)
            data = cdata.get_data()

            # 互換性マーク付与
            if cw.cwpy.classicdata.hasmodeini:
                # mode.ini優先
                versionhint = cw.cwpy.classicdata.versionhint
            else:
                versionhint = cw.cwpy.sct.get_versionhint(filedata=filedata)
                if not versionhint:
                    # 個別のファイルの情報が無い場合はシナリオの情報を使う
                    versionhint = cw.cwpy.classicdata.versionhint

    if data is None:
        if not usecache and tag and not versionhint:
            parser = SimpleXmlParser(path, tag, file, targetonly=True)
            return parser.parse()
        else:
            parser = SimpleXmlParser(path, "", file)
            data = parser.parse()

    basedata = data
    if tag:
        data = data.find(tag)

    if usecache:
        # キャッシュにデータを保存
        cachedata = CacheData(basedata, mtime)
        cw.cwpy.sdata.cache[path] = cachedata
        if nocache:
            data = copydata(data)

    if versionhint:
        prop = data.find("Property")
        if not prop is None:
            prop.set("versionHint", versionhint)

    return data

class CacheData(object):
    def __init__(self, data, mtime):
        self.data = data
        self.mtime = mtime

def copydata(data):
    if data.tag in ("Motions", "Events"):
        # 不変
        return data

    e = make_element(data.tag, data.text, copy.deepcopy(data.attrib), data.tail)
    for child in data:
        e.append(copydata(child))

    return e

class EndTargetTagException(Exception):
    pass

class SimpleXmlParser(object):
    def __init__(self, fpath, targettag="", file=None, targetonly=False):
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
        self.targetonly = targetonly
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
        if self.targetonly and self.targettag == name:
            raise EndTargetTagException()

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
            with open(self.fpath, "rb") as f:
                self.parse_file(f)

        return self.root

    def parse_file(self, file):
        try:
            self._parse_file(file)
        except EndTargetTagException, ex:
            pass
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
